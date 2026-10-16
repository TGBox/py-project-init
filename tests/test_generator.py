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

    def test_generate_node_ts_project(self):
        """Verifies that a TypeScript project generates correct package.json scripts and test files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            target_dir = Path(temp_dir) / "ts_app"
            context = {
                "project_name": "ts-app",
                "project_slug": "ts_app",
                "description": "TypeScript test application",
                "author": "TS Tester",
                "author_email": "ts@example.com",
                "license": "MIT",
                "custom_scripts": {
                    "main": "node dist/index.js",
                    "test": "vitest run",
                    "build": "tsc",
                    "format": "prettier --write .",
                    "lint": "eslint .",
                },
                "docker": False,
                "github_actions": True,
                "vscode": True,
                "enable_git_hooks": True,
                "selected_git_hooks": ["pre-push", "post-commit"],
                "enable_agent_configs": True,
                "selected_agent_rules": ["general_guidelines", "typescript_standards"],
                "selected_agent_skills": ["code-review", "test-runner"],
            }

            self.manager.generate(
                target_dir=target_dir,
                template_id="node-ts",
                context=context,
                log_callback=lambda msg: None
            )

            # Check files created
            self.assertTrue((target_dir / "package.json").exists())
            self.assertTrue((target_dir / "tsconfig.json").exists())
            self.assertTrue((target_dir / "src" / "index.ts").exists())
            self.assertTrue((target_dir / "tests" / "index.test.ts").exists())
            self.assertTrue((target_dir / ".git" / "hooks" / "pre-push").exists())

            # Check package.json scripts contain vitest and no pytest
            pkg_content = (target_dir / "package.json").read_text(encoding="utf-8")
            self.assertIn('"test": "vitest run"', pkg_content)
            self.assertNotIn("pytest", pkg_content)

    def test_hyphen_project_naming_and_flat_structure(self):
        """Verifies projects with hyphens retain exact name in commands and use flat src structure."""
        with tempfile.TemporaryDirectory() as temp_dir:
            proj_name = "py-aether-forge"
            target_dir = Path(temp_dir) / proj_name
            context = {
                "project_name": proj_name,
                "project_slug": "py_aether_forge",
                "description": "Aether Forge Project",
                "author": "Aether Dev",
                "author_email": "dev@aether.org",
                "license": "MIT",
                "custom_scripts": {},
                "docker": False,
                "github_actions": False,
                "vscode": False,
                "enable_git_hooks": False,
                "enable_agent_configs": False,
            }

            self.manager.generate(
                target_dir=target_dir,
                template_id="python-cli",
                context=context,
                log_callback=lambda msg: None
            )

            # 1. Target directory has exact hyphenated name
            self.assertEqual(target_dir.name, "py-aether-forge")

            # 2. Structure inside src/ is flat: src/main.py, src/build.py, etc.
            self.assertTrue((target_dir / "src" / "main.py").exists())
            self.assertTrue((target_dir / "src" / "build.py").exists())
            self.assertTrue((target_dir / "src" / "tools.py").exists())

            # 3. No internal folder with swapped characters exists
            self.assertFalse((target_dir / "src" / "py_aether_forge").exists())

            # 4. pyproject.toml contains exact name and commands without character swapping
            pyproject_txt = (target_dir / "pyproject.toml").read_text(encoding="utf-8")
            self.assertIn('name = "py-aether-forge"', pyproject_txt)
            self.assertIn('py-aether-forge = "src.main:main"', pyproject_txt)
            self.assertIn('main = "src.main:main"', pyproject_txt)
            self.assertIn('test = "pytest:main"', pyproject_txt)
            self.assertIn('build = "src.build:main"', pyproject_txt)

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


    def _assert_markdownlint_compliant(self, content: str):
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

    def test_agents_md_markdownlint_compliance(self):
        """Verifies that AGENTS.md complies with Markdownlint rules both on generation and retrofit."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # 1. Retrofit test
            proj_dir = Path(temp_dir) / "test_proj"
            proj_dir.mkdir()
            self.manager.retrofit_agent_configs(proj_dir, ["general_guidelines"], ["code-review"])

            agents_md_path = proj_dir / "AGENTS.md"
            self.assertTrue(agents_md_path.exists())
            self._assert_markdownlint_compliant(agents_md_path.read_text(encoding="utf-8"))

            # 2. New project generation test
            new_proj_dir = Path(temp_dir) / "new_proj"
            context = {
                "project_name": "new_proj",
                "project_slug": "new_proj",
                "description": "Compliance test",
                "author": "Tester",
                "author_email": "tester@example.com",
                "license": "MIT",
                "custom_scripts": {},
                "docker": False,
                "github_actions": False,
                "vscode": False,
                "enable_git_hooks": False,
                "enable_agent_configs": True,
                "selected_agent_rules": ["general_guidelines", "python_standards"],
                "selected_agent_skills": ["code-review"],
            }
            self.manager.generate(new_proj_dir, "python-cli", context, log_callback=lambda msg: None)
            gen_agents_md = new_proj_dir / "AGENTS.md"
            self.assertTrue(gen_agents_md.exists())
            self._assert_markdownlint_compliant(gen_agents_md.read_text(encoding="utf-8"))


    def test_generate_reports_failed_hooks(self):
        """A failing post-create hook must be returned as a problem instead of being swallowed."""
        with tempfile.TemporaryDirectory() as temp_dir:
            tpl_root = Path(temp_dir) / "templates"
            tpl_dir = tpl_root / "broken"
            tpl_dir.mkdir(parents=True)
            (tpl_dir / "template.yaml").write_text(
                'name: "Broken"\n'
                'language: "Python"\n'
                "hooks:\n"
                "  post_create:\n"
                '    - ["git", "--definitely-not-an-option"]\n',
                encoding="utf-8",
            )
            (tpl_dir / "README.md.j2").write_text("# {{ project_name }}\n", encoding="utf-8")

            manager = TemplateManager(tpl_root)
            target_dir = Path(temp_dir) / "out"
            context = {"project_name": "out", "custom_scripts": {}}
            problems = manager.generate(target_dir, "broken", context, log_callback=lambda msg: None)

            self.assertTrue((target_dir / "README.md").exists())
            self.assertEqual(len(problems), 1)
            self.assertIn("git --definitely-not-an-option", problems[0])

    def test_pyproject_scripts_and_sections_whitespace_formatting(self):
        """Verifies that [project.scripts] and [dependency-groups] contain no internal blank lines,
        and have exactly one blank line separating sections."""
        with tempfile.TemporaryDirectory() as temp_dir:
            target_dir = Path(temp_dir) / "py-forts"
            context = {
                "project_name": "py-forts",
                "project_slug": "py_forts",
                "description": "Python Forts Game Clone",
                "author": "Daniel",
                "author_email": "daniel@example.com",
                "license": "MIT",
                "framework": "pyside6",
                "custom_scripts": {},
                "docker": False,
                "github_actions": False,
                "vscode": False,
                "enable_git_hooks": False,
                "enable_agent_configs": False,
            }

            self.manager.generate(target_dir, "python-gui", context, log_callback=lambda msg: None)
            pyproject_gui = (target_dir / "pyproject.toml").read_text(encoding="utf-8")

            # Check [project.scripts] block has no empty lines and exactly one blank line before [dependency-groups]
            expected_gui_block = (
                "[project.scripts]\n"
                'py-forts = "src.main:main"\n'
                'main = "src.main:main"\n'
                'test = "pytest:main"\n'
                'build = "src.build:main"\n'
                'format = "src.tools:format_code"\n'
                'lint = "src.tools:lint_code"\n'
                "\n"
                "[dependency-groups]\n"
                "dev = [\n"
                '    "pytest>=8.0",\n'
                '    "pyinstaller>=6.0",\n'
                '    "ruff>=0.6",\n'
                "]"
            )
            self.assertIn(expected_gui_block, pyproject_gui)
            self.assertIn("]\n\n[project.scripts]\n", pyproject_gui)

            # Check preview also matches exactly
            preview_files = self.manager.preview("python-gui", context)
            self.assertIn(expected_gui_block, preview_files["pyproject.toml"]["content"])

            # Also check python-cli
            preview_cli = self.manager.preview("python-cli", context)
            expected_cli_block = (
                "[project.scripts]\n"
                'py-forts = "src.main:main"\n'
                'main = "src.main:main"\n'
                'test = "pytest:main"\n'
                'build = "src.build:main"\n'
                'format = "src.tools:format_code"\n'
                'lint = "src.tools:lint_code"\n'
                "\n"
                "[dependency-groups]\n"
                "dev = [\n"
                '    "pytest>=8.0",\n'
                '    "pyinstaller>=6.0",\n'
                '    "ruff>=0.6",\n'
                "]"
            )
            self.assertIn(expected_cli_block, preview_cli["pyproject.toml"]["content"])

            # Also check python-fastapi
            preview_fastapi = self.manager.preview("python-fastapi", context)
            expected_fastapi_block = (
                "[project.scripts]\n"
                'py-forts = "src.main:run"\n'
                'main = "src.main:run"\n'
                'test = "pytest:main"\n'
                'format = "src.tools:format_code"\n'
                'lint = "src.tools:lint_code"\n'
                "\n"
                "[dependency-groups]\n"
                "dev = [\n"
                '    "pytest>=8.3.0",\n'
                '    "httpx>=0.27.0",\n'
                '    "ruff>=0.6.0",\n'
                "]"
            )
            self.assertIn(expected_fastapi_block, preview_fastapi["pyproject.toml"]["content"])

if __name__ == "__main__":
    unittest.main()


