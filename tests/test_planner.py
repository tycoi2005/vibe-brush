import unittest

from sculptor.planner import StagedPlanner


class _FakeLLM:
    def __init__(self):
        self.chat_json_calls = 0
        self.chat_calls = 0

    def chat_json(self, messages, temperature=None, max_tokens=None):
        self.chat_json_calls += 1
        # Simulate the observed failure mode: empty JSON-stage response.
        return ""

    def chat(self, messages, temperature=None, max_tokens=None, response_format=None):
        self.chat_calls += 1
        return '{"title":"Sketch","description":"ok","stage":"sketch","steps":[]}'


class PlannerFallbackTests(unittest.TestCase):
    def test_stage2_retries_when_json_mode_returns_empty(self):
        planner = StagedPlanner(_FakeLLM())
        planner.session_memory["original_prompt"] = "draw a wolf"
        planner.session_memory["idea"] = "wolf concept"

        plan = planner.stage2_sketch()

        self.assertEqual(plan.title, "Sketch")
        self.assertEqual(plan.stage, "sketch")
        self.assertEqual(len(plan.steps), 0)
        self.assertEqual(planner.llm.chat_json_calls, 1)
        self.assertEqual(planner.llm.chat_calls, 1)


if __name__ == "__main__":
    unittest.main()
