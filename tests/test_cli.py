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


    def test_cli_github_and_gitlab_mutually_exclusive(self):
        """Verifies error when both GitLab and GitHub are specified."""
        err = io.StringIO()
        with patch("sys.stderr", err):
            code = run_cli([
                "mutually_exclusive_app",
                "--gitlab-url", "https://gitlab.example.com",
                "--github",
            ])
        self.assertEqual(code, 1)
        self.assertIn("nicht beides gleichzeitig", err.getvalue())

    def test_cli_github_missing_token(self):
        """Verifies error when GitHub is requested but no token is found."""
        err = io.StringIO()
        with patch("py_project_init.cli.load_github_token", return_value=""), patch("sys.stderr", err):
            code = run_cli([
                "github_no_token_app",
                "--github",
            ])
        self.assertEqual(code, 1)
        self.assertIn("Kein GitHub-Token gefunden", err.getvalue())


if __name__ == "__main__":
    unittest.main()
