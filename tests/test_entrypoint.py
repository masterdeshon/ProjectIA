"""Verifica o pacote instalado e sua inicialização sem credenciais."""

import os
import subprocess
import sys
import tempfile
import unittest


class EntryPointTests(unittest.TestCase):
    def run_python(self, *args):
        env = {key: value for key, value in os.environ.items() if not key.startswith("OPENAI_")}
        with tempfile.TemporaryDirectory() as directory:
            return subprocess.run(
                [sys.executable, *args],
                cwd=directory,
                env=env,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=20,
                check=False,
            )

    def test_missing_key_exits_with_help_before_opening_a_window(self):
        result = self.run_python("-m", "projectia")
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("OPENAI_API_KEY", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_importing_application_does_not_start_tk(self):
        result = self.run_python(
            "-c",
            "from unittest.mock import patch\n"
            "with patch('tkinter.Tk', side_effect=AssertionError('Janela inesperada')):\n"
            "    import projectia.gui\n"
            "    import projectia.__main__\n",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
