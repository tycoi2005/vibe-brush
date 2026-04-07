import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import yaml

from sculptor.config import load_config


class ConfigThrottleTests(unittest.TestCase):
    def test_load_config_reads_requests_per_minute(self):
        with tempfile.TemporaryDirectory() as td:
            cfg_path = Path(td) / "config.yaml"
            cfg_path.write_text(
                yaml.safe_dump(
                    {
                        "llm": {
                            "api_key": "k",
                            "requests_per_minute": 5,
                        }
                    }
                ),
                encoding="utf-8",
            )

            cfg = load_config(cfg_path)
            self.assertEqual(cfg["llm"]["requests_per_minute"], 5)

    def test_env_override_requests_per_minute(self):
        with patch.dict(os.environ, {"OPENAI_REQUESTS_PER_MINUTE": "5"}, clear=False):
            cfg = load_config("/tmp/non-existent-config.yaml")
            self.assertEqual(cfg["llm"]["requests_per_minute"], 5.0)

    def test_env_override_ollama_api_key(self):
        with patch.dict(os.environ, {"OLLAMA_API_KEY": "ollama-key"}, clear=False):
            cfg = load_config("/tmp/non-existent-config.yaml")
            self.assertEqual(cfg["llm"]["api_key"], "ollama-key")


if __name__ == "__main__":
    unittest.main()
