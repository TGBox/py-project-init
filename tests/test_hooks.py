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


if __name__ == "__main__":
    unittest.main()
