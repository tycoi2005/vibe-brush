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

    def test_stage3_retries_when_first_response_is_truncated_json(self):
        class _TaskChunkLLM:
            def __init__(self):
                self.chat_json_calls = 0
                self.chat_calls = 0

            def chat_json(self, messages, temperature=None, max_tokens=None):
                self.chat_json_calls += 1
                user_text = messages[-1]["content"]
                if "schema: {'tasks'" in messages[0]["content"]:
                    return '{"tasks":[{"name":"subject","goal":"draw subject"},{"name":"lighting","goal":"add light"}]}'
                if "Current Stage 3 task 1/2" in user_text:
                    return '{"title":"Part 1","description":"subject","stage":"overall","steps":[{"action":"set_brush"}]}'
                return '{"title":"Part 2","description":"lighting","stage":"overall","steps":[{"action":"set_color_html"}]}'

            def chat(self, messages, temperature=None, max_tokens=None, response_format=None):
                self.chat_calls += 1
                return '{"title":"Fallback","description":"ok","stage":"overall","steps":[]}'

        planner = StagedPlanner(_TaskChunkLLM())
        planner.session_memory["original_prompt"] = "draw a wolf"
        planner.session_memory["idea"] = "wolf concept"
        planner.session_memory["sketch"] = "rough sketch summary"

        plan = planner.stage3_overall()

        self.assertEqual(plan.title, "Stage 3 Overall Composition")
        self.assertEqual(plan.stage, "overall")
        self.assertEqual(len(plan.steps), 2)
        self.assertEqual(planner.llm.chat_json_calls, 3)

    def test_stage3_uses_fallback_task_list_when_task_generation_fails(self):
        class _FailTaskListLLM:
            def chat_json(self, messages, temperature=None, max_tokens=None):
                user_text = messages[-1]["content"]
                if "schema: {'tasks'" in messages[0]["content"]:
                    raise RuntimeError("task list failed")
                if "Current Stage 3 task" in user_text:
                    return '{"title":"Part","description":"ok","stage":"overall","steps":[]}'
                return '{"title":"Fallback","description":"ok","stage":"overall","steps":[]}'

            def chat(self, messages, temperature=None, max_tokens=None, response_format=None):
                return '{"title":"Fallback","description":"ok","stage":"overall","steps":[]}'

        planner = StagedPlanner(_FailTaskListLLM())
        planner.session_memory["original_prompt"] = "draw a wolf"
        planner.session_memory["idea"] = "wolf concept"
        planner.session_memory["sketch"] = "rough sketch summary"

        plan = planner.stage3_overall()

        self.assertEqual(plan.stage, "overall")
        self.assertEqual(plan.title, "Stage 3 Overall Composition")


if __name__ == "__main__":
    unittest.main()
