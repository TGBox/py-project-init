import unittest
import tempfile
import shutil
from pathlib import Path
from py_project_init.core.generator import TemplateManager


class TestTemplateManager(unittest.TestCase):
    def setUp(self):
        self.base_dir = Path(__file__).resolve().parent.parent
        self.templates_dir = self.base_dir / "templates"
        self.manager = TemplateManager(self.templates_dir)

    def test_templates_loaded(self):
        """Ensures all standard templates are loaded."""
        self.assertIn("python-cli", self.manager.templates)
        self.assertIn("python-fastapi", self.manager.templates)
        self.assertIn("python-gui", self.manager.templates)
        self.assertIn("rust-cli", self.manager.templates)
        self.assertIn("node-ts", self.manager.templates)

    def test_get_available_hooks(self):
        """Ensures hooks are discovered with metadata."""
        hooks = self.manager.get_available_hooks()
        hook_ids = [h["id"] for h in hooks]
        self.assertIn("pre-commit", hook_ids)
        self.assertIn("post-commit", hook_ids)

        # Check metadata
        pre_commit = next(h for h in hooks if h["id"] == "pre-commit")
        self.assertTrue(len(pre_commit["name"]) > 0)
        self.assertTrue(len(pre_commit["description"]) > 0)

    def test_get_agent_manifest_and_recommendations(self):
        """Ensures agent rules and skills are discovered and recommended correctly."""
        manifest = self.manager.get_agent_manifest()
        self.assertTrue(len(manifest.get("rules", [])) > 0)
        self.assertTrue(len(manifest.get("skills", [])) > 0)

        # Python CLI recommendations
        py_rec = self.manager.get_recommended_agent_configs("python-cli", "Python")
        self.assertIn("general_guidelines", py_rec["rules"])
        self.assertIn("python_standards", py_rec["rules"])
        self.assertNotIn("fastapi_best_practices", py_rec["rules"])

        # Python FastAPI recommendations
        fastapi_rec = self.manager.get_recommended_agent_configs("python-fastapi", "Python")
        self.assertIn("fastapi_best_practices", fastapi_rec["rules"])

        # PySide6 GUI recommendations
        gui_rec = self.manager.get_recommended_agent_configs("python-gui", "Python")
        self.assertIn("pyside6_gui_conventions", gui_rec["rules"])

    def test_merge_gitignore(self):
        """Verifies intelligent merging of gitignore without duplicates."""
        existing = ".venv/\n__pycache__/\nbuild/\n"
        incoming = "__pycache__\ndist\n.venv\ncustom_secret.env\n"
        merged = self.manager._merge_gitignore(existing, incoming)
        lines = merged.splitlines()

        self.assertIn(".venv/", lines)
        self.assertIn("custom_secret.env", lines)
        # Verify no duplicate entries
        self.assertEqual(lines.count(".venv/"), 1)
        self.assertEqual(lines.count("custom_secret.env"), 1)

    def test_generation_with_hooks_and_agent_configs(self):
        """Performs a real generation test in a temp directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            target_dir = Path(temp_dir) / "test_app"
            context = {
                "project_name": "test_app",
                "project_slug": "test_app",
                "description": "Test project for automated verification",
                "author": "Tester",
                "author_email": "tester@example.com",
                "license": "MIT",
                "custom_scripts": {
                    "lint": "ruff check .",
                    "format": "ruff format ."
                },
                "docker": False,
                "github_actions": True,
                "vscode": True,
                "enable_git_hooks": True,
                "selected_git_hooks": ["pre-commit", "post-commit"],
                "enable_agent_configs": True,
                "selected_agent_rules": ["general_guidelines", "python_standards"],
                "selected_agent_skills": ["code-review"],
            }

            self.manager.generate(
                target_dir=target_dir,
                template_id="python-cli",
                context=context,
                log_callback=lambda msg: None
            )

            # Check git repo was initialized
            self.assertTrue((target_dir / ".git").exists())

            # Check hooks installed
            self.assertTrue((target_dir / ".git" / "hooks" / "pre-commit").exists())
            self.assertTrue((target_dir / ".git" / "hooks" / "post-commit").exists())

            # Check agent configs generated
            self.assertTrue((target_dir / ".agents" / "rules" / "general_guidelines.md").exists())
            self.assertTrue((target_dir / ".agents" / "rules" / "python_standards.md").exists())
            self.assertTrue((target_dir / ".agents" / "skills" / "code-review" / "SKILL.md").exists())
            self.assertTrue((target_dir / "AGENTS.md").exists())

            # Check pyproject.toml rendered with author, license, and scripts
            pyproject_content = (target_dir / "pyproject.toml").read_text(encoding="utf-8")
            self.assertIn("Tester", pyproject_content)
            self.assertIn("tester@example.com", pyproject_content)
            self.assertIn("MIT", pyproject_content)
            self.assertIn('lint = "ruff check ."', pyproject_content)
            self.assertIn('format = "ruff format ."', pyproject_content)


if __name__ == "__main__":
    unittest.main()
