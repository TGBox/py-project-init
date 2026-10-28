import io
import subprocess
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

            smarttests_val = subprocess.check_output(
                ["git", "config", "--get", "hooks.smarttests"], cwd=target, text=True
            ).strip()
            self.assertEqual(smarttests_val, "true")

    def test_no_smart_tests_flag(self):
        """Verifies --no-smart-tests configures hooks.smarttests to false."""
        with tempfile.TemporaryDirectory() as temp_dir:
            out = io.StringIO()
            with patch("sys.stdout", out):
                code = run_cli([
                    "no_smart_app",
                    "-t", "python-cli",
                    "-p", temp_dir,
                    "--no-smart-tests",
                ])
            self.assertEqual(code, 0)
            target = Path(temp_dir) / "no_smart_app"
            smarttests_val = subprocess.check_output(
                ["git", "config", "--get", "hooks.smarttests"], cwd=target, text=True
            ).strip()
            self.assertEqual(smarttests_val, "false")

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


    def test_cli_push_pipeline_options(self):
        """Verifies generating project with granular push pipeline CLI flags."""
        with tempfile.TemporaryDirectory() as temp_dir:
            out = io.StringIO()
            with patch("sys.stdout", out):
                code = run_cli([
                    "cli_pipeline_app",
                    "-t", "python-cli",
                    "-p", temp_dir,
                    "--renew-tag-on-push",
                    "--test-cmd", "pytest -q",
                    "--build-exe",
                    "--build-cmd", "uv run pyinstaller main.py",
                    "--artifact-pattern", "dist/cli_pipeline_app.exe",
                    "--deploy-artifact",
                    "--external-repo", "https://example.com/repo-artifacts.git",
                    "--external-repo-branch", "release",
                    "--external-repo-dir", "downloads",
                ])
            self.assertEqual(code, 0)
            target = Path(temp_dir) / "cli_pipeline_app"
            self.assertTrue(target.is_dir())

            self.assertEqual(
                subprocess.check_output(["git", "config", "--get", "hooks.renewtagonpush"], cwd=target, text=True).strip(),
                "true"
            )
            self.assertEqual(
                subprocess.check_output(["git", "config", "--get", "hooks.testcmd"], cwd=target, text=True).strip(),
                "pytest -q"
            )
            self.assertEqual(
                subprocess.check_output(["git", "config", "--get", "hooks.buildexe"], cwd=target, text=True).strip(),
                "true"
            )
            self.assertEqual(
                subprocess.check_output(["git", "config", "--get", "hooks.buildcmd"], cwd=target, text=True).strip(),
                "uv run pyinstaller main.py"
            )
            self.assertEqual(
                subprocess.check_output(["git", "config", "--get", "hooks.artifactpattern"], cwd=target, text=True).strip(),
                "dist/cli_pipeline_app.exe"
            )
            self.assertEqual(
                subprocess.check_output(["git", "config", "--get", "hooks.deployartifact"], cwd=target, text=True).strip(),
                "true"
            )
            self.assertEqual(
                subprocess.check_output(["git", "config", "--get", "hooks.externalrepo"], cwd=target, text=True).strip(),
                "https://example.com/repo-artifacts.git"
            )
            self.assertEqual(
                subprocess.check_output(["git", "config", "--get", "hooks.externalrepobranch"], cwd=target, text=True).strip(),
                "release"
            )
            self.assertEqual(
                subprocess.check_output(["git", "config", "--get", "hooks.externalrepodir"], cwd=target, text=True).strip(),
                "downloads"
            )

    def test_cli_retrofit_hooks_with_pipeline_flags(self):
        """Verifies retrofitting existing project with push pipeline CLI flags."""
        with tempfile.TemporaryDirectory() as temp_dir:
            proj = Path(temp_dir) / "my_retrofit_cli_proj"
            proj.mkdir()
            (proj / "main.py").write_text("print('test')", encoding="utf-8")

            out = io.StringIO()
            with patch("sys.stdout", out):
                code = run_cli([
                    "--retrofit-hooks", str(proj),
                    "--renew-tag-on-push",
                    "--build-exe",
                    "--build-cmd", "cargo build --release",
                    "--deploy-artifact",
                    "--external-repo", "git@github.com:myorg/binaries.git",
                ])
            self.assertEqual(code, 0)
            self.assertEqual(
                subprocess.check_output(["git", "config", "--get", "hooks.renewtagonpush"], cwd=proj, text=True).strip(),
                "true"
            )
            self.assertEqual(
                subprocess.check_output(["git", "config", "--get", "hooks.buildexe"], cwd=proj, text=True).strip(),
                "true"
            )
            self.assertEqual(
                subprocess.check_output(["git", "config", "--get", "hooks.buildcmd"], cwd=proj, text=True).strip(),
                "cargo build --release"
            )
            self.assertEqual(
                subprocess.check_output(["git", "config", "--get", "hooks.deployartifact"], cwd=proj, text=True).strip(),
                "true"
            )
            self.assertEqual(
                subprocess.check_output(["git", "config", "--get", "hooks.externalrepo"], cwd=proj, text=True).strip(),
                "git@github.com:myorg/binaries.git"
            )


if __name__ == "__main__":
    unittest.main()
