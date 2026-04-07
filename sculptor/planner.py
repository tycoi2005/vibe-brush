"""Planner: Converts user prompts into structured art plans via LLM.

Takes a natural language description and produces a JSON art plan
that the executor can translate into Open Brush API commands.
"""

import json
import logging
import re
from pathlib import Path
from typing import Any

from .llm_client import LLMClient

log = logging.getLogger("sculptor.planner")

# Load system prompt from file
PROMPTS_DIR = Path(__file__).parent.parent / "prompts"


def _load_prompt(name: str) -> str:
    """Load a prompt template from the prompts directory."""
    path = PROMPTS_DIR / f"{name}.md"
    if not path.exists():
        raise FileNotFoundError(f"Prompt template not found: {path}")
    return path.read_text()


def _extract_json(text: str) -> dict[str, Any]:
    """Extract a JSON object from LLM response text.

    Handles common formats:
    - Pure JSON
    - JSON wrapped in ```json ... ``` markdown fences
    - JSON preceded/followed by prose text
    - Empty or missing response
    """
    if not text or not text.strip():
        raise ValueError("LLM returned an empty response. The model may not support this request.")

    text = text.strip()
    log.debug("Raw LLM response (%d chars): %s", len(text), text[:300])

    # 1. Try direct parse first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 2. Try extracting from markdown code fences: ```json ... ``` or ``` ... ```
    fence_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?\s*```", text, re.DOTALL)
    if fence_match:
        try:
            extracted = fence_match.group(1).strip()
            log.debug("Extracted from code fence: %s", extracted[:200])
            return json.loads(extracted)
        except json.JSONDecodeError:
            pass

    # 3. Try finding a JSON object by matching outermost { ... }
    brace_start = text.find("{")
    if brace_start != -1:
        # Find matching closing brace by counting depth
        depth = 0
        for i in range(brace_start, len(text)):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    candidate = text[brace_start : i + 1]
                    try:
                        log.debug("Extracted by brace matching: %s", candidate[:200])
                        return json.loads(candidate)
                    except json.JSONDecodeError:
                        break

    # Nothing worked
    raise ValueError(
        f"Could not extract JSON from LLM response.\n"
        f"Response ({len(text)} chars): {text[:500]}"
    )


class ArtPlan:
    """Represents a structured art plan from the LLM."""

    def __init__(self, data: dict[str, Any]):
        self.title: str = data.get("title", "Untitled")
        self.description: str = data.get("description", "")
        self.steps: list[dict[str, Any]] = data.get("steps", [])
        self.raw = data

    def __repr__(self):
        return f"ArtPlan(title='{self.title}', steps={len(self.steps)})"

    def summary(self) -> str:
        """Return a human-readable summary of the plan."""
        lines = [
            f"🎨 {self.title}",
            f"   {self.description}",
            f"   Steps: {len(self.steps)}",
        ]

        # Count action types
        action_counts: dict[str, int] = {}
        for step in self.steps:
            action = step.get("action", "unknown")
            action_counts[action] = action_counts.get(action, 0) + 1

        for action, count in action_counts.items():
            lines.append(f"   - {action}: {count}x")

        return "\n".join(lines)


class Planner:
    """Converts user prompts into structured art plans using an LLM."""

    def __init__(self, llm: LLMClient):
        self.llm = llm
        self.system_prompt = _load_prompt("system")
        self.conversation_history: list[dict[str, str]] = []
        log.info("Planner initialized, system prompt loaded (%d chars)", len(self.system_prompt))

    def plan(self, user_prompt: str) -> ArtPlan:
        """Generate an art plan from a user prompt.

        Args:
            user_prompt: Natural language description of desired art.

        Returns:
            ArtPlan with structured steps.

        Raises:
            ValueError: If LLM response is not valid JSON or missing required fields.
        """
        log.info("Planning for prompt: %s", user_prompt[:120])

        messages = [
            {"role": "system", "content": self.system_prompt},
            *self.conversation_history,
            {"role": "user", "content": user_prompt},
        ]
        log.debug("Sending %d messages to LLM (%d history)", len(messages), len(self.conversation_history))

        response = self.llm.chat(messages, temperature=0.7)
        log.info("LLM response received (%d chars)", len(response) if response else 0)
        log.debug("LLM response: %s", response[:500] if response else "(empty)")

        # Parse JSON from response — handle various LLM output formats
        data = _extract_json(response)
        log.info("Parsed art plan: title=%s, steps=%d", data.get("title"), len(data.get("steps", [])))

        if "steps" not in data:
            raise ValueError(f"LLM response missing 'steps' field: {data}")

        # Store in conversation history for context
        self.conversation_history.append({"role": "user", "content": user_prompt})
        self.conversation_history.append({"role": "assistant", "content": response})

        # Keep history manageable (last 10 exchanges)
        if len(self.conversation_history) > 20:
            self.conversation_history = self.conversation_history[-20:]

        return ArtPlan(data)

    def refine(self, feedback: str) -> ArtPlan:
        """Refine the last art plan based on user feedback.

        Args:
            feedback: User's feedback on what to change.

        Returns:
            Updated ArtPlan.
        """
        log.info("Refining with feedback: %s", feedback[:120])
        refinement_prompt = (
            f"The user wants to modify the artwork. Their feedback: {feedback}\n\n"
            "Please output a complete updated JSON art plan incorporating their changes. "
            "Keep what was good and modify what they asked for."
        )
        return self.plan(refinement_prompt)

    def reset_history(self):
        """Clear conversation history."""
        self.conversation_history.clear()
        log.info("Conversation history cleared")
