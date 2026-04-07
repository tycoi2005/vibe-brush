"""Staged Planner: Converts user prompts into a 4-stage sculpting pipeline.

Pipeline:
  Stage 1 — IDEAS:   Concept brief (plain text, no JSON)
  Stage 2 — SKETCH:  Rough blocking with structural primitives
  Stage 3 — OVERALL: Full composition drawing
  Stage 4 — DETAILS: Polish pass — particles, glow, textures

Each stage result is stored in session_memory and injected as context
into all subsequent stages so the agent remembers what it planned.
"""

import json
import logging
import re
from pathlib import Path
from typing import Any

from .llm_client import LLMClient

log = logging.getLogger("sculptor.planner")

PROMPTS_DIR = Path(__file__).parent.parent / "prompts"


def _load_prompt(name: str) -> str:
    """Load a prompt template from the prompts directory."""
    path = PROMPTS_DIR / f"{name}.md"
    if not path.exists():
        raise FileNotFoundError(f"Prompt template not found: {path}")
    return path.read_text()


def _extract_json(text: str) -> dict[str, Any]:
    """Extract a JSON object from LLM response text.

    Handles:
    - Pure JSON
    - JSON wrapped in ```json ... ``` markdown fences
    - JSON preceded/followed by prose text
    """
    if not text or not text.strip():
        raise ValueError("LLM returned an empty response.")

    text = text.strip()
    log.debug("Raw LLM response (%d chars): %s", len(text), text[:300])

    # 1. Try direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        log.debug("Direct JSON parse failed: %s (line=%s col=%s)", e.msg, e.lineno, e.colno)

    # 2. Try markdown code fences
    fence_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?\s*```", text, re.DOTALL)
    if fence_match:
        try:
            return json.loads(fence_match.group(1).strip())
        except json.JSONDecodeError as e:
            log.debug("Fence JSON parse failed: %s (line=%s col=%s)", e.msg, e.lineno, e.colno)

    # 3. Try outermost { ... } brace matching
    brace_start = text.find("{")
    if brace_start != -1:
        depth = 0
        for i in range(brace_start, len(text)):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    candidate = text[brace_start: i + 1]
                    try:
                        return json.loads(candidate)
                    except json.JSONDecodeError as e:
                        log.debug("Brace-matched JSON parse failed: %s (line=%s col=%s)", e.msg, e.lineno, e.colno)
                        break

    log.debug("Failed JSON response tail: %s", text[-300:])

    raise ValueError(
        f"Could not extract JSON from LLM response.\n"
        f"Response ({len(text)} chars): {text[:500]}"
    )


class ArtPlan:
    """Represents a structured art plan from the LLM."""

    def __init__(self, data: dict[str, Any]):
        self.title: str = data.get("title", "Untitled")
        self.description: str = data.get("description", "")
        self.stage: str = data.get("stage", "unknown")
        self.steps: list[dict[str, Any]] = data.get("steps", [])
        # Optional spatial layout declared by the LLM
        self.spatial_layout: list[dict[str, Any]] = data.get("spatial_layout", [])
        self.raw = data

    def __repr__(self):
        return f"ArtPlan(stage='{self.stage}', title='{self.title}', steps={len(self.steps)})"

    def summary(self) -> str:
        """Return a human-readable summary of the plan."""
        lines = [
            f"🎨 [{self.stage.upper()}] {self.title}",
            f"   {self.description}",
            f"   Steps: {len(self.steps)}",
        ]
        action_counts: dict[str, int] = {}
        for step in self.steps:
            action = step.get("action", "unknown")
            action_counts[action] = action_counts.get(action, 0) + 1
        for action, count in action_counts.items():
            lines.append(f"   - {action}: {count}x")
        return "\n".join(lines)

    def step_summary(self) -> str:
        """Short summary for injection into next stage context."""
        action_counts: dict[str, int] = {}
        for step in self.steps:
            action = step.get("action", "unknown")
            action_counts[action] = action_counts.get(action, 0) + 1
        actions_str = ", ".join(f"{a}×{c}" for a, c in action_counts.items())
        return (
            f"Title: {self.title}\n"
            f"Description: {self.description}\n"
            f"Steps ({len(self.steps)} total): {actions_str}"
        )


class StagedPlanner:
    """4-stage creative pipeline for Open Brush sculpting.

    Stages:
      1. IDEAS   — concept brief (text)
      2. SKETCH  — rough 3D blocking (JSON plan)
      3. OVERALL — full composition drawing (JSON plan)
      4. DETAILS — polish pass: particles, glow, textures (JSON plan)

    Session memory is preserved across stages so each stage builds
    on the accumulated context of all previous stages.
    """

    def __init__(self, llm: LLMClient):
        self.llm = llm
        self._prompts = {
            "stage1": _load_prompt("stage1_ideas"),
            "stage2": _load_prompt("stage2_sketch"),
            "stage3": _load_prompt("stage3_overall"),
            "stage4": _load_prompt("stage4_details"),
        }
        # Session memory — persists within a session, reset on /new or /reset
        self.session_memory: dict[str, Any] = {}
        # Flat conversation history for backward compat with /refine
        self.conversation_history: list[dict[str, str]] = []
        log.info("StagedPlanner initialized")

    # ── Internal helpers ───────────────────────────────────────────────────

    def _chat(self, system_prompt: str, user_content: str, temperature: float = 0.7) -> str:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ]
        log.debug("LLM call: %d chars system, %d chars user", len(system_prompt), len(user_content))
        return self.llm.chat(messages, temperature=temperature)

    def _generate_plan_data(self, stage_label: str, system_prompt: str, user_content: str, temperature: float = 0.7) -> dict[str, Any]:
        """Generate and parse a stage JSON plan with retries for truncated outputs."""
        log.debug("%s JSON generation start: %d chars system, %d chars user", stage_label, len(system_prompt), len(user_content))

        attempts: list[tuple[str, str, float, bool]] = [
            ("json_mode", user_content, temperature, True),
            (
                "plain_json_retry",
                (
                    f"{user_content}\n\n"
                    "IMPORTANT: Return ONLY a valid JSON object. "
                    "No markdown fences. No explanation."
                ),
                max(0.2, temperature - 0.1),
                False,
            ),
            (
                "compact_json_retry",
                (
                    f"{user_content}\n\n"
                    "IMPORTANT: Return ONLY compact valid JSON with the schema title/description/stage/steps. "
                    "Keep descriptions short to avoid truncation. No markdown fences."
                ),
                0.2,
                False,
            ),
        ]

        last_error: Exception | None = None
        for idx, (attempt_name, attempt_user, attempt_temp, use_json_mode) in enumerate(attempts, start=1):
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": attempt_user},
            ]
            log.info("%s attempt %d/%d: %s", stage_label, idx, len(attempts), attempt_name)
            try:
                if use_json_mode:
                    response = self.llm.chat_json(messages, temperature=attempt_temp)
                else:
                    response = self.llm.chat(messages, temperature=attempt_temp)

                if not response or not response.strip():
                    last_error = ValueError("LLM returned an empty response.")
                    log.warning("%s attempt %d returned empty response", stage_label, idx)
                    continue

                try:
                    return _extract_json(response)
                except ValueError as e:
                    last_error = e
                    log.warning(
                        "%s attempt %d JSON parse failed (%d chars): %s",
                        stage_label,
                        idx,
                        len(response),
                        e,
                    )
            except Exception as e:
                last_error = e
                log.warning("%s attempt %d request failed: %s", stage_label, idx, e)

        assert last_error is not None
        raise last_error

    def _generate_stage3_tasks(self, user_content: str) -> list[dict[str, str]]:
        """Create a compact Stage 3 task list before generating full steps."""
        system = (
            "You are planning Stage 3 drawing work. "
            "Return ONLY valid JSON with this schema: "
            "{'tasks':[{'name':'...','goal':'...'}]}. "
            "Create 3 to 6 tasks, concise and non-overlapping."
        )
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user_content},
        ]

        try:
            raw = self.llm.chat_json(messages, temperature=0.3)
            data = _extract_json(raw)
            tasks = data.get("tasks", []) if isinstance(data, dict) else []
            normalized: list[dict[str, str]] = []
            for task in tasks:
                if not isinstance(task, dict):
                    continue
                name = str(task.get("name", "")).strip()
                goal = str(task.get("goal", "")).strip()
                if not name:
                    continue
                normalized.append({"name": name, "goal": goal or name})
            if normalized:
                return normalized[:6]
        except Exception as e:
            log.warning("Stage 3 task-list generation failed, using fallback tasks: %s", e)

        return [
            {"name": "composition", "goal": "Lay out major forms and layers"},
            {"name": "subject", "goal": "Draw the main subject with clear silhouette"},
            {"name": "supporting", "goal": "Add supporting forms and depth layers"},
            {"name": "lighting", "goal": "Apply key colors and lighting accents"},
        ]

    def _generate_stage3_task_plan(
        self,
        base_user_content: str,
        task: dict[str, str],
        task_index: int,
        total_tasks: int,
    ) -> dict[str, Any]:
        """Generate one smaller Stage 3 partial plan for a specific task."""
        task_user_content = (
            f"{base_user_content}\n\n"
            f"Current Stage 3 task {task_index}/{total_tasks}: {task['name']}\n"
            f"Goal: {task['goal']}\n\n"
            "IMPORTANT constraints for this partial output:\n"
            "- Return only the steps needed for THIS task, not the entire artwork.\n"
            "- Keep output concise. Target 8 to 20 steps max.\n"
            "- Return ONLY valid JSON for one 'overall' plan object."
        )
        return self._generate_plan_data(
            stage_label=f"Stage 3 Task {task_index}",
            system_prompt=self._prompts["stage3"],
            user_content=task_user_content,
            temperature=0.6,
        )

    def _build_memory_context(self, include: list[str]) -> str:
        """Build a context string from session memory for stage injection."""
        parts = []
        if "idea" in include and "idea" in self.session_memory:
            parts.append("=== STAGE 1 — CONCEPT BRIEF ===\n" + self.session_memory["idea"])
        if "sketch" in include and "sketch" in self.session_memory:
            parts.append("=== STAGE 2 — ROUGH SKETCH SUMMARY ===\n" + self.session_memory["sketch"])
        if "overall" in include and "overall" in self.session_memory:
            parts.append("=== STAGE 3 — OVERALL DRAWING SUMMARY ===\n" + self.session_memory["overall"])
        # Always inject spatial registry if it has entries
        if self.session_memory.get("spatial_registry"):
            registry_lines = []
            for name, entry in self.session_memory["spatial_registry"].items():
                pos = entry.get("position", [0, 0, 0])
                facing = entry.get("facing", "none")
                size = entry.get("size", "?")
                layer = entry.get("layer", 0)
                stage = entry.get("stage", "?")
                registry_lines.append(
                    f"  - {name}: pos={pos}, facing={facing}, size={size}, layer={layer} [placed in {stage}]"
                )
            parts.append(
                "=== SPATIAL REGISTRY (what is placed where in 3D space) ===\n"
                + "\n".join(registry_lines)
            )
        return "\n\n".join(parts)

    def _merge_spatial_layout(self, plan: ArtPlan, stage_name: str):
        """Merge a plan's spatial_layout entries into the persistent spatial registry."""
        registry = self.session_memory.setdefault("spatial_registry", {})
        for item in plan.spatial_layout:
            name = item.get("name")
            if not name:
                continue
            registry[name] = {
                "position": item.get("position", [0, 0, 0]),
                "facing": item.get("facing", "none"),
                "size": item.get("size", "unknown"),
                "layer": item.get("layer", 0),
                "stage": stage_name,
            }
        log.debug("Spatial registry now has %d items", len(registry))

    # ── 4-Stage pipeline ───────────────────────────────────────────────────

    def stage1_ideate(self, user_prompt: str) -> str:
        """Stage 1: Generate concept brief (plain text)."""
        log.info("Stage 1 — Ideas for: %s", user_prompt[:80])
        response = self._chat(self._prompts["stage1"], user_prompt, temperature=0.85)
        self.session_memory["idea"] = response
        self.session_memory["original_prompt"] = user_prompt
        log.info("Stage 1 complete (%d chars)", len(response))
        return response

    def stage2_sketch(self) -> ArtPlan:
        """Stage 2: Generate rough blocking plan."""
        log.info("Stage 2 — Sketch/blocking")
        context = self._build_memory_context(include=["idea"])
        user_content = (
            f"Original request: {self.session_memory.get('original_prompt', '')}\n\n"
            f"{context}\n\n"
            "Now produce the Stage 2 rough blocking JSON plan."
        )
        data = self._generate_plan_data("Stage 2", self._prompts["stage2"], user_content, temperature=0.6)
        plan = ArtPlan(data)
        self._merge_spatial_layout(plan, stage_name="sketch")
        self.session_memory["sketch"] = plan.step_summary()
        log.info("Stage 2 complete: %s (%d steps)", plan.title, len(plan.steps))
        return plan

    def stage3_overall(self) -> ArtPlan:
        """Stage 3: Generate full composition drawing plan."""
        log.info("Stage 3 — Overall drawing")
        context = self._build_memory_context(include=["idea", "sketch"])
        user_content = (
            f"Original request: {self.session_memory.get('original_prompt', '')}\n\n"
            f"{context}\n\n"
            "Now produce the Stage 3 overall drawing JSON plan. "
            "Build ON TOP of the sketch — do NOT clear the canvas."
        )
        tasks = self._generate_stage3_tasks(user_content)
        log.info("Stage 3 task list generated: %d tasks", len(tasks))

        merged_steps: list[dict[str, Any]] = []
        description_parts: list[str] = []
        for idx, task in enumerate(tasks, start=1):
            log.info("Stage 3 executing task %d/%d: %s", idx, len(tasks), task["name"])
            partial = self._generate_stage3_task_plan(user_content, task, idx, len(tasks))
            partial_steps = partial.get("steps", []) if isinstance(partial, dict) else []
            if isinstance(partial_steps, list):
                merged_steps.extend(partial_steps)
            partial_desc = str(partial.get("description", "")).strip() if isinstance(partial, dict) else ""
            if partial_desc:
                description_parts.append(partial_desc)

        data = {
            "title": "Stage 3 Overall Composition",
            "description": "; ".join(description_parts[:3]) or "Combined Stage 3 plan from task chunks",
            "stage": "overall",
            "steps": merged_steps,
        }
        plan = ArtPlan(data)
        self._merge_spatial_layout(plan, stage_name="overall")
        self.session_memory["overall"] = plan.step_summary()
        log.info("Stage 3 complete: %s (%d steps)", plan.title, len(plan.steps))
        return plan

    def stage4_details(self) -> ArtPlan:
        """Stage 4: Generate polish/detail pass plan."""
        log.info("Stage 4 — Detail pass")
        context = self._build_memory_context(include=["idea", "sketch", "overall"])
        user_content = (
            f"Original request: {self.session_memory.get('original_prompt', '')}\n\n"
            f"{context}\n\n"
            "Now produce the Stage 4 detail and polish JSON plan. "
            "Add finishing touches — DO NOT redraw or clear anything."
        )
        data = self._generate_plan_data("Stage 4", self._prompts["stage4"], user_content, temperature=0.75)
        plan = ArtPlan(data)
        self._merge_spatial_layout(plan, stage_name="details")
        self.session_memory["details"] = plan.step_summary()
        log.info("Stage 4 complete: %s (%d steps)", plan.title, len(plan.steps))
        return plan

    def run_pipeline(self, user_prompt: str) -> tuple[str, ArtPlan, ArtPlan, ArtPlan]:
        """Run all 4 stages in sequence. Returns (concept, sketch, overall, details)."""
        concept = self.stage1_ideate(user_prompt)
        sketch = self.stage2_sketch()
        overall = self.stage3_overall()
        details = self.stage4_details()
        # Store full history for /refine compatibility
        self.conversation_history.append({"role": "user", "content": user_prompt})
        self.conversation_history.append({"role": "assistant", "content": concept})
        if len(self.conversation_history) > 20:
            self.conversation_history = self.conversation_history[-20:]
        return concept, sketch, overall, details

    # ── Refinement (single-shot, for /refine command) ──────────────────────

    def refine(self, feedback: str) -> ArtPlan:
        """Refine the last artwork with a single-shot LLM call.

        Uses full session memory as context so the LLM knows what drew.
        """
        log.info("Refining with feedback: %s", feedback[:80])
        system = _load_prompt("stage3_overall")  # reuse overall drawing prompt
        context = self._build_memory_context(include=["idea", "sketch", "overall", "details"])
        user_content = (
            f"The user wants to refine the current artwork.\n"
            f"Feedback: {feedback}\n\n"
            f"Previous session context:\n{context}\n\n"
            "Produce a JSON plan with ONLY the changes/additions needed. "
            "Do NOT redraw existing elements unless the feedback requires it."
        )
        response = self._chat(system, user_content, temperature=0.7)
        data = _extract_json(response)
        plan = ArtPlan(data)
        # Update overall summary with refinement
        self.session_memory["overall"] = plan.step_summary() + " [refined]"
        return plan

    def reset_history(self):
        """Clear all session memory and conversation history."""
        self.session_memory.clear()
        self.conversation_history.clear()
        log.info("Session memory and conversation history cleared")

    # ── Backward-compat alias ──────────────────────────────────────────────

    def plan(self, user_prompt: str) -> ArtPlan:
        """Backward-compatible single-stage plan (runs full pipeline, returns details plan)."""
        _, _, _, details = self.run_pipeline(user_prompt)
        return details
