import unittest
from unittest.mock import patch

from sculptor.llm_client import LLMClient


class _FakeOpenAI:
    def __init__(self, *args, **kwargs):
        pass


class LLMClientThrottleTests(unittest.TestCase):
    @patch("sculptor.llm_client.OpenAI", _FakeOpenAI)
    def test_resolve_call_delay_prefers_explicit_delay(self):
        delay = LLMClient._resolve_call_delay(call_delay=3.0, requests_per_minute=5)
        self.assertEqual(delay, 3.0)

    @patch("sculptor.llm_client.OpenAI", _FakeOpenAI)
    def test_resolve_call_delay_from_requests_per_minute(self):
        delay = LLMClient._resolve_call_delay(call_delay=None, requests_per_minute=5)
        self.assertEqual(delay, 12.0)

    @patch("sculptor.llm_client.OpenAI", _FakeOpenAI)
    def test_resolve_call_delay_disabled_when_values_not_positive(self):
        self.assertIsNone(LLMClient._resolve_call_delay(call_delay=None, requests_per_minute=None))
        self.assertIsNone(LLMClient._resolve_call_delay(call_delay=0, requests_per_minute=0))

    @patch("sculptor.llm_client.OpenAI", _FakeOpenAI)
    @patch("sculptor.llm_client.time.sleep")
    @patch("sculptor.llm_client.time.monotonic", side_effect=[100.0, 100.1, 104.0])
    def test_throttle_waits_for_remaining_delay(self, mock_monotonic, mock_sleep):
        client = LLMClient(api_key="x", call_delay=5.0)

        client._throttle_calls()  # first call starts at 100.0
        client._throttle_calls()  # second call at 100.1 should sleep ~4.9

        mock_sleep.assert_called_once()
        slept_for = mock_sleep.call_args[0][0]
        self.assertAlmostEqual(slept_for, 4.9, places=3)


if __name__ == "__main__":
    unittest.main()
