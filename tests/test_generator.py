import unittest
import tempfile
import shutil
import subprocess
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

    def test_preview_simulation(self):
        """Verifies in-memory preview simulates generation without touching disk."""
        context = {
            "project_name": "preview_project",
            "project_slug": "preview_project",
            "description": "Preview test description",
            "author": "Preview Tester",
            "author_email": "preview@example.com",
            "license": "MIT",
            "custom_scripts": {"start": "python main.py"},
            "docker": False,
            "github_actions": True,
            "vscode": True,
            "enable_git_hooks": True,
            "selected_git_hooks": ["pre-commit", "commit-msg"],
            "enable_agent_configs": True,
            "selected_agent_rules": ["general_guidelines"],
            "selected_agent_skills": ["code-review"],
        }
        files_map = self.manager.preview("python-cli", context)
        self.assertIn("pyproject.toml", files_map)
        self.assertIn(".git/hooks/pre-commit", files_map)
        self.assertIn(".git/hooks/commit-msg", files_map)
        self.assertIn(".agents/rules/general_guidelines.md", files_map)
        self.assertIn("AGENTS.md", files_map)

        # Check rendered content in preview
        pyproject_preview = files_map["pyproject.toml"]["content"]
        self.assertIn("preview_project", pyproject_preview)
        self.assertIn("Preview Tester", pyproject_preview)

    def test_retrofit_functionality(self):
        """Verifies retrofitting hooks and agent configs into an existing project."""
        with tempfile.TemporaryDirectory() as temp_dir:
            proj_dir = Path(temp_dir) / "existing_proj"
            proj_dir.mkdir()
            (proj_dir / "app.py").write_text("print('hello')", encoding="utf-8")

            # 1. Retrofit hooks
            self.manager.retrofit_hooks(proj_dir, ["pre-commit", "commit-msg"], enable_autotag=True)
            self.assertTrue((proj_dir / ".git").exists())
            self.assertTrue((proj_dir / ".git" / "hooks" / "pre-commit").exists())
            self.assertTrue((proj_dir / ".git" / "hooks" / "commit-msg").exists())

            # Check git config for autotag and push.followTags
            autotag_val = subprocess.check_output(
                ["git", "config", "--get", "hooks.autotag"],
                cwd=proj_dir,
                text=True
            ).strip()
            self.assertEqual(autotag_val, "true")
            followtags_val = subprocess.check_output(
                ["git", "config", "--get", "push.followTags"],
                cwd=proj_dir,
                text=True
            ).strip()
            self.assertEqual(followtags_val, "true")

            # 2. Retrofit agent configs
            self.manager.retrofit_agent_configs(proj_dir, ["general_guidelines"], ["code-review"])
            self.assertTrue((proj_dir / ".agents" / "rules" / "general_guidelines.md").exists())
            self.assertTrue((proj_dir / ".agents" / "skills" / "code-review").exists())
            self.assertTrue((proj_dir / "AGENTS.md").exists())

    def test_create_template_from_project(self):
        """Verifies creating a reusable template from an existing folder."""
        with tempfile.TemporaryDirectory() as temp_dir:
            src_dir = Path(temp_dir) / "my_existing_service"
            src_dir.mkdir()
            (src_dir / "README.md").write_text("# my_existing_service\nSome info", encoding="utf-8")
            (src_dir / "pyproject.toml").write_text('[project]\nname = "my_existing_service"\nversion = "0.1.0"', encoding="utf-8")
            (src_dir / ".venv").mkdir()  # should be ignored

            out_templates_dir = Path(temp_dir) / "custom_templates"
            out_templates_dir.mkdir()

            tpl_dir = self.manager.create_template_from_project(
                source_dir=src_dir,
                output_dir=out_templates_dir,
                template_name="My Service Template",
                language="Python",
                description="Exported template test"
            )

            self.assertTrue((tpl_dir / "template.yaml").exists())
            self.assertTrue((tpl_dir / "README.md.j2").exists())
            self.assertTrue((tpl_dir / "pyproject.toml.j2").exists())
            self.assertFalse((tpl_dir / ".venv").exists())  # Ignored

            # Verify placeholder replacement
            readme_j2 = (tpl_dir / "README.md.j2").read_text(encoding="utf-8")
            self.assertIn("{{ project_name }}", readme_j2)


    def test_agents_md_markdownlint_compliance(self):
        """Verifies that AGENTS.md complies with Markdownlint rules (e.g. blank lines after headings)."""
        with tempfile.TemporaryDirectory() as temp_dir:
            proj_dir = Path(temp_dir) / "test_proj"
            proj_dir.mkdir()
            self.manager.retrofit_agent_configs(proj_dir, ["general_guidelines"], ["code-review"])

            agents_md_path = proj_dir / "AGENTS.md"
            self.assertTrue(agents_md_path.exists())
            content = agents_md_path.read_text(encoding="utf-8")

            # Must end with single newline
            self.assertTrue(content.endswith("\n"))
            self.assertFalse(content.endswith("\n\n"))

            lines = content.split("\n")
            for i, line in enumerate(lines):
                if line.startswith("#"):
                    # Heading must be followed by a blank line
                    if i + 1 < len(lines):
                        self.assertEqual(
                            lines[i + 1],
                            "",
                            f"Heading at line {i+1} ('{line}') must be followed by a blank line."
                        )
                    # Heading must be preceded by a blank line if not first line
                    if i > 0:
                        self.assertEqual(
                            lines[i - 1],
                            "",
                            f"Heading at line {i+1} ('{line}') must be preceded by a blank line."
                        )


if __name__ == "__main__":
    unittest.main()

