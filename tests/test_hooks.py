import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from py_project_init.core.generator import TemplateManager


def get_git_bash() -> str:
    """Finds Git's bash executable on Windows, or default bash on Unix."""
    if os.name == "nt":
        candidates = [
            Path(r"C:\Program Files\Git\bin\bash.exe"),
            Path(r"C:\Program Files\Git\usr\bin\bash.exe"),
            Path(r"C:\Program Files (x86)\Git\bin\bash.exe"),
        ]
        for c in candidates:
            if c.exists():
                return str(c)
    return "bash"


class TestGitHooks(unittest.TestCase):
    def setUp(self):
        self.base_dir = Path(__file__).resolve().parent.parent
        self.hooks_dir = self.base_dir / "hooks"
        self.manager = TemplateManager(self.base_dir / "templates", hooks_dir=self.hooks_dir)
        self.bash = get_git_bash()

    def test_all_expected_hooks_discovered(self):
        """Ensures all client-side workflow hooks are present and discovered."""
        expected_hooks = [
            "pre-commit",
            "commit-msg",
            "prepare-commit-msg",
            "post-commit",
            "post-checkout",
            "post-merge",
            "pre-rebase",
            "pre-push",
        ]
        available_hooks = self.manager.get_available_hooks()
        hook_ids = {h["id"] for h in available_hooks}

        for hook in expected_hooks:
            self.assertIn(hook, hook_ids, f"Hook '{hook}' missing from available hooks")

    def test_commit_msg_hook_validation(self):
        """Tests that commit-msg enforces Conventional Commits."""
        hook_path = self.hooks_dir / "commit-msg"
        self.assertTrue(hook_path.exists())

        with tempfile.NamedTemporaryFile("w+", delete=False, encoding="utf-8") as f:
            f.write("bad commit message\n")
            f.flush()
            bad_msg_path = f.name

        with tempfile.NamedTemporaryFile("w+", delete=False, encoding="utf-8") as f:
            f.write("feat(core): implement git hooks integration\n")
            f.flush()
            good_msg_path = f.name

        try:
            # Bad message should fail (exit code 1)
            res_bad = subprocess.run(
                [self.bash, str(hook_path), bad_msg_path],
                capture_output=True,
                text=True
            )
            self.assertNotEqual(res_bad.returncode, 0, "commit-msg should reject non-conventional message")

            # Good message should succeed (exit code 0)
            res_good = subprocess.run(
                [self.bash, str(hook_path), good_msg_path],
                capture_output=True,
                text=True
            )
            self.assertEqual(res_good.returncode, 0, f"commit-msg failed on valid message: {res_good.stderr}")
        finally:
            if os.path.exists(bad_msg_path):
                os.remove(bad_msg_path)
            if os.path.exists(good_msg_path):
                os.remove(good_msg_path)

    def test_prepare_commit_msg_branch_prefix(self):
        """Tests that prepare-commit-msg extracts issue keys from branch names."""
        hook_path = self.hooks_dir / "prepare-commit-msg"
        self.assertTrue(hook_path.exists())

        with tempfile.NamedTemporaryFile("w+", delete=False, encoding="utf-8") as f:
            f.write("initial text\n")
            f.flush()
            msg_path = f.name

        try:
            env = os.environ.copy()
            env["GIT_BRANCH_OVERRIDE"] = "feature/PROJ-456-add-auth"
            res = subprocess.run(
                [self.bash, str(hook_path), msg_path, "message"],
                env=env,
                capture_output=True,
                text=True
            )
            self.assertEqual(res.returncode, 0, f"prepare-commit-msg failed: {res.stderr}")
            with open(msg_path, "r", encoding="utf-8") as f:
                content = f.read()
            self.assertIn("PROJ-456", content)
        finally:
            if os.path.exists(msg_path):
                os.remove(msg_path)

    def test_pre_rebase_protection(self):
        """Tests that pre-rebase blocks rebasing main or master."""
        hook_path = self.hooks_dir / "pre-rebase"
        self.assertTrue(hook_path.exists())

        # Rebasing main should be blocked
        res_main = subprocess.run(
            [self.bash, str(hook_path), "upstream", "main"],
            capture_output=True,
            text=True
        )
        self.assertNotEqual(res_main.returncode, 0)

        # Rebasing feature branch should be allowed
        res_feat = subprocess.run(
            [self.bash, str(hook_path), "upstream", "feature/my-work"],
            capture_output=True,
            text=True
        )
        self.assertEqual(res_feat.returncode, 0, f"pre-rebase failed: {res_feat.stderr}")

    def test_pre_push_protection(self):
        """Tests that pre-push blocks direct pushes to main or master."""
        hook_path = self.hooks_dir / "pre-push"
        self.assertTrue(hook_path.exists())

        env = os.environ.copy()
        env["GIT_PRE_PUSH_SKIP_TESTS"] = "1"

        # Simulating stdin for git pre-push: <local ref> <local sha> <remote ref> <remote sha>
        input_main = "refs/heads/main 123456 refs/heads/main 000000\n"
        res_main = subprocess.run(
            [self.bash, str(hook_path), "origin", "git@github.com:repo.git"],
            input=input_main,
            env=env,
            capture_output=True,
            text=True
        )
        self.assertNotEqual(res_main.returncode, 0)

        input_feat = "refs/heads/feature/abc 123456 refs/heads/feature/abc 000000\n"
        res_feat = subprocess.run(
            [self.bash, str(hook_path), "origin", "git@github.com:repo.git"],
            input=input_feat,
            env=env,
            capture_output=True,
            text=True
        )
        self.assertEqual(res_feat.returncode, 0, f"pre-push failed: {res_feat.stderr}")

    def test_commit_lifecycle_no_premature_bump(self):
        """Verifies that an invalid commit message does not prematurely bump the version in pyproject.toml."""
        import shutil
        with tempfile.TemporaryDirectory() as temp_dir:
            proj = Path(temp_dir)
            # init git repo
            subprocess.run(["git", "init"], cwd=proj, check=True, capture_output=True)
            subprocess.run(["git", "config", "user.name", "Tester"], cwd=proj, check=True)
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=proj, check=True)

            # install hooks
            hooks_dir = proj / ".git" / "hooks"
            shutil.copy2(self.hooks_dir / "pre-commit", hooks_dir / "pre-commit")
            shutil.copy2(self.hooks_dir / "commit-msg", hooks_dir / "commit-msg")
            shutil.copy2(self.hooks_dir / "post-commit", hooks_dir / "post-commit")

            # create pyproject.toml
            pyproject = proj / "pyproject.toml"
            pyproject.write_text('[project]\nname = "test"\nversion = "1.0.0"\n', encoding="utf-8")
            (proj / "app.py").write_text("print('hello')", encoding="utf-8")
            subprocess.run(["git", "add", "."], cwd=proj, check=True)

            # 1. Attempt commit with invalid commit message
            res_bad = subprocess.run(
                ["git", "commit", "-m", "invalid message"],
                cwd=proj,
                capture_output=True,
                text=True
            )
            # Commit should fail
            self.assertNotEqual(res_bad.returncode, 0)

            # Check that pyproject.toml version was NOT bumped!
            content = pyproject.read_text(encoding="utf-8")
            self.assertIn('version = "1.0.0"', content)

            # 2. Commit with valid conventional message in non-interactive mode
            env = os.environ.copy()
            env["GIT_HOOKS_NON_INTERACTIVE"] = "1"
            res_good = subprocess.run(
                ["git", "commit", "-m", "feat(core): initial working feature"],
                cwd=proj,
                env=env,
                capture_output=True,
                text=True
            )
            self.assertEqual(res_good.returncode, 0, f"Valid commit failed: {res_good.stderr}")
            # Changelog should have been generated
            self.assertTrue((proj / "CHANGELOG.md").exists())

    def test_post_commit_interactive_bump(self):
        """Verifies that post-commit correctly bumps version and amends commit when chosen interactively."""
        import shutil
        with tempfile.TemporaryDirectory() as temp_dir:
            proj = Path(temp_dir)
            subprocess.run(["git", "init"], cwd=proj, check=True, capture_output=True)
            subprocess.run(["git", "config", "user.name", "Tester"], cwd=proj, check=True)
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=proj, check=True)

            hooks_dir = proj / ".git" / "hooks"
            shutil.copy2(self.hooks_dir / "pre-commit", hooks_dir / "pre-commit")
            shutil.copy2(self.hooks_dir / "commit-msg", hooks_dir / "commit-msg")
            shutil.copy2(self.hooks_dir / "post-commit", hooks_dir / "post-commit")

            pyproject = proj / "pyproject.toml"
            pyproject.write_text('[project]\nname = "test"\nversion = "1.0.0"\n', encoding="utf-8")
            (proj / "app.py").write_text("print('hello')", encoding="utf-8")
            subprocess.run(["git", "add", "."], cwd=proj, check=True)

            # Commit with interactive simulation: input='2\n' (Minor bump)
            env = os.environ.copy()
            env["GIT_HOOKS_FORCE_INTERACTIVE"] = "1"
            env.pop("GIT_HOOKS_NON_INTERACTIVE", None)
            env.pop("CI", None)

            res = subprocess.run(
                ["git", "commit", "-m", "feat(calc): add calculator"],
                cwd=proj,
                input="2\n",
                env=env,
                capture_output=True,
                text=True
            )
            self.assertEqual(res.returncode, 0, f"Commit failed: {res.stderr}")

            # Verify pyproject.toml was bumped to 1.1.0 in working tree
            content = pyproject.read_text(encoding="utf-8")
            self.assertIn('version = "1.1.0"', content)

            # Verify commit HEAD contains the bumped version
            head_pyproject = subprocess.check_output(
                ["git", "show", "HEAD:pyproject.toml"],
                cwd=proj,
                text=True
            )
            self.assertIn('version = "1.1.0"', head_pyproject)

            # Verify CHANGELOG.md was generated with SemVer v1.1.0
            changelog = (proj / "CHANGELOG.md").read_text(encoding="utf-8")
            self.assertIn("## SemVer v1.1.0", changelog)
            self.assertIn("feat(calc): add calculator", changelog)


if __name__ == "__main__":
    unittest.main()

