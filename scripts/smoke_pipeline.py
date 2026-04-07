"""Reusable smoke test for the staged planner pipeline.

Usage examples:
  python scripts/smoke_pipeline.py
  python scripts/smoke_pipeline.py --stages 2
  python scripts/smoke_pipeline.py --prompt "draw a wolf head with mountains"
  python scripts/smoke_pipeline.py --config config.yaml --print-plan
"""

from __future__ import annotations

import argparse
import sys

from sculptor.config import load_config, validate_config
from sculptor.llm_client import LLMClient
from sculptor.planner import StagedPlanner


def build_llm_from_config(config: dict) -> LLMClient:
    llm_cfg = config.get("llm", {})
    return LLMClient(
        api_key=llm_cfg.get("api_key", ""),
        base_url=llm_cfg.get("base_url", "https://api.openai.com/v1"),
        model=llm_cfg.get("model", "gpt-4o"),
        temperature=llm_cfg.get("temperature", 0.7),
        max_tokens=llm_cfg.get("max_tokens", 4096),
        call_delay=llm_cfg.get("call_delay"),
        requests_per_minute=llm_cfg.get("requests_per_minute"),
    )


def run_smoke(config_path: str | None, prompt: str, stages: int, print_plan: bool) -> int:
    config = load_config(config_path)
    issues = validate_config(config)
    if issues:
        for issue in issues:
            print(f"[WARN] {issue}")
        if any("API key" in issue for issue in issues):
            print("[ERROR] Missing API key. Set llm.api_key or OLLAMA_API_KEY/OPENAI_API_KEY.")
            return 1

    llm = build_llm_from_config(config)
    planner = StagedPlanner(llm)

    print(f"[INFO] Model: {config.get('llm', {}).get('model')}")
    print(f"[INFO] Base URL: {config.get('llm', {}).get('base_url')}")

    concept = planner.stage1_ideate(prompt)
    print(f"[OK] Stage 1 complete: {len(concept)} chars")

    if stages >= 2:
        sketch = planner.stage2_sketch()
        print(f"[OK] Stage 2 complete: {sketch.title} ({len(sketch.steps)} steps)")
        if print_plan:
            print(sketch.summary())

    if stages >= 3:
        overall = planner.stage3_overall()
        print(f"[OK] Stage 3 complete: {overall.title} ({len(overall.steps)} steps)")
        if print_plan:
            print(overall.summary())

    if stages >= 4:
        details = planner.stage4_details()
        print(f"[OK] Stage 4 complete: {details.title} ({len(details.steps)} steps)")
        if print_plan:
            print(details.summary())

    print("[DONE] Smoke test completed.")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Smoke test for staged planner pipeline")
    parser.add_argument("--config", "-c", default=None, help="Path to config.yaml")
    parser.add_argument(
        "--prompt",
        default="draw a wolf head with mountain backdrop",
        help="Prompt used for the smoke test",
    )
    parser.add_argument(
        "--stages",
        type=int,
        choices=[1, 2, 3, 4],
        default=2,
        help="How many stages to run (default: 2)",
    )
    parser.add_argument(
        "--print-plan",
        action="store_true",
        help="Print generated plan summaries",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    return run_smoke(
        config_path=args.config,
        prompt=args.prompt,
        stages=args.stages,
        print_plan=args.print_plan,
    )


if __name__ == "__main__":
    sys.exit(main())
