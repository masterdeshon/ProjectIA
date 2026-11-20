"""Configuração local sem consultar credenciais do usuário."""

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from projectia.config import ConfigurationError, Settings, load_settings


class ConfigurationTests(unittest.TestCase):
    def test_missing_or_blank_key_is_rejected(self):
        for value in (None, "", " \n\t "):
            with self.subTest(value=value):
                env = {} if value is None else {"OPENAI_API_KEY": value}
                with self.assertRaises(ConfigurationError):
                    load_settings(environ=env)

    def test_environment_is_trimmed_and_default_model_is_used(self):
        settings = load_settings(environ={"OPENAI_API_KEY": "  unit-test-key  "})
        self.assertEqual(settings.api_key, "unit-test-key")
        self.assertEqual(settings.model, "gpt-4.1-mini")
        self.assertNotIn(settings.api_key, repr(settings))

    def test_custom_model_and_blank_model_fallback(self):
        for model, expected in (("  another-model  ", "another-model"), (" ", "gpt-4.1-mini")):
            with self.subTest(model=model):
                settings = load_settings(
                    environ={"OPENAI_API_KEY": "unit-test-key", "OPENAI_MODEL": model}
                )
                self.assertEqual(settings.model, expected)

    def test_dotenv_loads_values_but_environment_takes_precedence(self):
        with tempfile.TemporaryDirectory() as directory:
            dotenv = Path(directory) / ".env"
            dotenv.write_text(
                "OPENAI_API_KEY=file-test-key\nOPENAI_MODEL=file-model\n", encoding="utf-8"
            )
            with patch.dict(os.environ, {}, clear=True):
                settings = load_settings(dotenv_path=dotenv)
                self.assertEqual(settings.api_key, "file-test-key")
                self.assertEqual(settings.model, "file-model")
            with patch.dict(os.environ, {"OPENAI_API_KEY": "environment-test-key"}, clear=True):
                settings = load_settings(dotenv_path=dotenv)
                self.assertEqual(settings.api_key, "environment-test-key")
                self.assertEqual(settings.model, "file-model")

    def test_missing_explicit_file_does_not_search_parent_dotenv(self):
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory)
            (parent / ".env").write_text("OPENAI_API_KEY=parent-test-key\n", encoding="utf-8")
            child = parent / "child"
            child.mkdir()
            with patch.dict(os.environ, {}, clear=True), self.assertRaises(ConfigurationError):
                load_settings(dotenv_path=child / ".env")

    def test_invalid_numeric_settings_are_rejected(self):
        for kwargs in ({"max_output_tokens": 0}, {"timeout_seconds": 0}, {"max_retries": -1}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ConfigurationError):
                Settings(api_key="unit-test-key", **kwargs)
