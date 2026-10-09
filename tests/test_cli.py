import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from py_project_init.cli import run_cli


class TestCLI(unittest.TestCase):
    def test_list_templates(self):
        """Verifies --list displays all templates."""
        out = io.StringIO()
        with patch("sys.stdout", out):
            code = run_cli(["--list"])
        self.assertEqual(code, 0)
        output = out.getvalue()
        self.assertIn("python-cli", output)
        self.assertIn("node-ts", output)
        self.assertIn("rust-cli", output)

    def test_generate_project_via_cli(self):
        """Verifies generating a project from command line."""
        with tempfile.TemporaryDirectory() as temp_dir:
            out = io.StringIO()
            with patch("sys.stdout", out):
                code = run_cli([
                    "cli_test_app",
                    "-t", "python-cli",
                    "-p", temp_dir,
                    "-a", "CLI Developer",
                    "-e", "dev@example.com",
                    "-l", "MIT",
                ])
            self.assertEqual(code, 0)
            target = Path(temp_dir) / "cli_test_app"
            self.assertTrue(target.is_dir())
            self.assertTrue((target / "pyproject.toml").exists())
            self.assertTrue((target / ".git" / "hooks" / "pre-commit").exists())
            self.assertTrue((target / ".agents" / "rules").exists())

            pyproject_txt = (target / "pyproject.toml").read_text(encoding="utf-8")
            self.assertIn("CLI Developer", pyproject_txt)

    def test_preview_via_cli(self):
        """Verifies --preview flag prints simulated files without writing to disk."""
        with tempfile.TemporaryDirectory() as temp_dir:
            out = io.StringIO()
            with patch("sys.stdout", out):
                code = run_cli([
                    "preview_app",
                    "-t", "python-cli",
                    "-p", temp_dir,
                    "--preview"
                ])
            self.assertEqual(code, 0)
            target = Path(temp_dir) / "preview_app"
            # Since it was preview only, the folder should not exist
            self.assertFalse(target.exists())
            output = out.getvalue()
            self.assertIn("pyproject.toml", output)
            self.assertIn("Vorschau:", output)


if __name__ == "__main__":
    unittest.main()
