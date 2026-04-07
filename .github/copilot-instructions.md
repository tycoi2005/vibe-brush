# Project Guidelines

## Code Style
- Use Python 3.10+ compatible syntax and type hints where practical.
- Keep logging with named loggers (for example `sculptor.cli`, `sculptor.llm`, `sculptor.planner`) and avoid ad-hoc `print` in core package modules.
- Keep changes minimal and localized; preserve existing CLI behavior and stage workflow unless the task requires otherwise.

## Architecture
- This project is a staged 3D-generation pipeline:
  1. Stage 1 (ideas): plain-text concept.
  2. Stage 2 (sketch): rough JSON plan.
  3. Stage 3 (overall): full composition JSON plan.
  4. Stage 4 (details): polish JSON plan.
- Core boundaries:
  - `sculptor/planner.py`: stage orchestration, JSON extraction, session memory.
  - `sculptor/llm_client.py`: OpenAI-compatible LLM calls and request throttling.
  - `sculptor/executor.py`: executes plan actions.
  - `sculptor/openbrush_client.py`: Open Brush HTTP API interaction.

## Build and Test
- Install dependencies: `pip install -r requirements.txt`
- Run interactive CLI: `python -m sculptor.cli`
- Run single prompt: `python -m sculptor.cli --prompt "..."`
- Smoke-test planner without full app flow: `python scripts/smoke_pipeline.py --stages 2`
- Unit tests: `python -m unittest discover`
- Targeted tests:
  - `python -m unittest -v tests/test_config.py`
  - `python -m unittest -v tests/test_llm_client.py`
  - `python -m unittest -v tests/test_planner.py`

## Conventions
- Config sources and precedence are important: explicit `--config` path, then `SCULPTOR_CONFIG`, then local `config.yaml`, then user config path.
- LLM throttling supports two knobs:
  - `llm.call_delay` (explicit seconds)
  - `llm.requests_per_minute` (converted to delay as `60 / rpm`)
  - If both are set, explicit `call_delay` wins.
- Prefer environment variables for credentials (`OLLAMA_API_KEY`, `OPENAI_API_KEY`) rather than hardcoding keys in config files.
- For stage JSON generation reliability, keep outputs compact and valid JSON when editing prompts or planner behavior.

## Security
- Never commit secrets or tokens to tracked files, logs, tests, or examples.
- Do not print full API keys in terminal output, logs, or error messages; only indicate presence/absence.
- Treat any discovered credential in local files as sensitive and recommend rotating it if it may have been exposed.
- Keep `config.example.yaml` credential-free and use environment variables for local runtime keys.
- When adding scripts or tests, avoid network calls that would require embedding credentials in code.

## Reference Docs
- Project setup and usage: [README.md](../README.md)
- Open Brush setup and API prerequisites: [docs/install_openbrush.md](../docs/install_openbrush.md)
- Config options and examples: [config.example.yaml](../config.example.yaml)
- Prompt assets used by stages: [prompts/system.md](../prompts/system.md), [prompts/stage1_ideas.md](../prompts/stage1_ideas.md), [prompts/stage2_sketch.md](../prompts/stage2_sketch.md), [prompts/stage3_overall.md](../prompts/stage3_overall.md), [prompts/stage4_details.md](../prompts/stage4_details.md)
