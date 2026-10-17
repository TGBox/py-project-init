import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

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
        self.assertIn("python-game", self.manager.templates)
        self.assertIn("python-tui", self.manager.templates)
        self.assertIn("web-frontend", self.manager.templates)
        self.assertIn("web-fullstack", self.manager.templates)
        self.assertIn("go-app", self.manager.templates)
        self.assertIn("dotnet-app", self.manager.templates)
        self.assertIn("rust-cli", self.manager.templates)
        self.assertIn("rust-gui", self.manager.templates)
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
        fastapi_rec = self.manager.get_recommended_agent_configs(
            "python-fastapi", "Python"
        )
        self.assertIn("fastapi_best_practices", fastapi_rec["rules"])

        # PySide6 GUI recommendations
        gui_rec = self.manager.get_recommended_agent_configs("python-gui", "Python")
        self.assertIn("pyside6_gui_conventions", gui_rec["rules"])

        # Python Game recommendations
        game_rec = self.manager.get_recommended_agent_configs("python-game", "Python")
        self.assertIn("game_development_guidelines", game_rec["rules"])

        # Web Frontend recommendations
        web_rec = self.manager.get_recommended_agent_configs(
            "web-frontend", "TypeScript"
        )
        self.assertIn("web_frontend_standards", web_rec["rules"])

        # Go recommendations
        go_rec = self.manager.get_recommended_agent_configs("go-app", "Go")
        self.assertIn("go_standards", go_rec["rules"])

        # .NET C# recommendations
        dotnet_rec = self.manager.get_recommended_agent_configs("dotnet-app", "C#")
        self.assertIn("csharp_standards", dotnet_rec["rules"])

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
                "custom_scripts": {"lint": "ruff check .", "format": "ruff format ."},
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
                log_callback=lambda msg: None,
            )

            # Check git repo was initialized
            self.assertTrue((target_dir / ".git").exists())

            # Check hooks installed
            self.assertTrue((target_dir / ".git" / "hooks" / "pre-commit").exists())
            self.assertTrue((target_dir / ".git" / "hooks" / "post-commit").exists())

            # Check agent configs generated
            self.assertTrue(
                (target_dir / ".agents" / "rules" / "general_guidelines.md").exists()
            )
            self.assertTrue(
                (target_dir / ".agents" / "rules" / "python_standards.md").exists()
            )
            self.assertTrue(
                (
                    target_dir / ".agents" / "skills" / "code-review" / "SKILL.md"
                ).exists()
            )
            self.assertTrue((target_dir / "AGENTS.md").exists())

            # Check pyproject.toml rendered with author, license, and scripts
            pyproject_content = (target_dir / "pyproject.toml").read_text(
                encoding="utf-8"
            )
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
                log_callback=lambda msg: None,
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
                log_callback=lambda msg: None,
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

    def test_preview_python_game_and_tui(self):
        """Verifies template rendering and preview for python-game and python-tui."""
        # 1. python-game with Pygame-ce
        game_ctx = {
            "project_name": "space_invaders",
            "project_slug": "space_invaders",
            "description": "2D Space Shooter",
            "framework": "pygame-ce",
            "github_actions": True,
            "vscode": True,
            "enable_git_hooks": False,
            "enable_agent_configs": True,
            "selected_agent_rules": [
                "general_guidelines",
                "game_development_guidelines",
            ],
            "selected_agent_skills": ["code-review"],
        }
        game_files = self.manager.preview("python-game", game_ctx)
        self.assertIn("pyproject.toml", game_files)
        self.assertIn("src/main.py", game_files)
        self.assertIn("src/settings.py", game_files)
        self.assertIn("tests/test_game.py", game_files)
        self.assertIn(".agents/rules/game_development_guidelines.md", game_files)
        self.assertIn("pygame-ce", game_files["pyproject.toml"]["content"])
        self.assertIn("F11", game_files["src/main.py"]["content"])

        # 2. python-game with Arcade
        game_ctx["framework"] = "arcade"
        arcade_files = self.manager.preview("python-game", game_ctx)
        self.assertIn("arcade", arcade_files["pyproject.toml"]["content"])
        self.assertIn("arcade.Window", arcade_files["src/main.py"]["content"])

        # 3. python-tui
        tui_ctx = {
            "project_name": "system_monitor",
            "project_slug": "system_monitor",
            "description": "Terminal Monitor",
            "github_actions": True,
            "vscode": True,
            "enable_git_hooks": False,
            "enable_agent_configs": False,
        }
        tui_files = self.manager.preview("python-tui", tui_ctx)
        self.assertIn("pyproject.toml", tui_files)
        self.assertIn("src/app.py", tui_files)
        self.assertIn("src/main.py", tui_files)
        self.assertIn("tests/test_app.py", tui_files)
        self.assertIn("textual", tui_files["pyproject.toml"]["content"])
        self.assertIn("SystemMonitorApp", tui_files["src/app.py"]["content"])
        self.assertIn("__test__ = False", tui_files["src/app.py"]["content"])
        self.assertNotIn("font-size", tui_files["src/app.py"]["content"])
        self.assertIn("TestAppLifecycle", tui_files["tests/test_app.py"]["content"])

    def test_preview_web_frontend_and_fullstack(self):
        """Verifies template rendering and preview for web-frontend and web-fullstack."""
        # 1. web-frontend (React)
        react_ctx = {
            "project_name": "dashboard_app",
            "project_slug": "dashboard_app",
            "description": "React Dashboard",
            "framework": "react",
            "github_actions": True,
            "docker": True,
            "enable_git_hooks": False,
            "enable_agent_configs": True,
            "selected_agent_rules": ["web_frontend_standards"],
            "selected_agent_skills": ["code-review"],
        }
        react_files = self.manager.preview("web-frontend", react_ctx)
        self.assertIn("package.json", react_files)
        self.assertIn("src/App.tsx", react_files)
        self.assertIn("src/main.tsx", react_files)
        self.assertIn("src/vite-env.d.ts", react_files)
        self.assertIn("tests/App.test.tsx", react_files)
        self.assertIn("Dockerfile", react_files)
        self.assertIn("nginx.conf", react_files)
        self.assertIn(".agents/rules/web_frontend_standards.md", react_files)
        self.assertIn("react", react_files["package.json"]["content"])
        # Ensure no unused React imports that trigger TS6133
        self.assertNotIn("import React", react_files["src/App.tsx"]["content"])
        self.assertNotIn("import React", react_files["tests/App.test.tsx"]["content"])

        # 2. web-frontend (Vue)
        vue_ctx = dict(react_ctx, framework="vue", docker=False)
        vue_files = self.manager.preview("web-frontend", vue_ctx)
        self.assertIn("src/App.vue", vue_files)
        self.assertIn("src/main.ts", vue_files)
        self.assertIn("src/vite-env.d.ts", vue_files)
        self.assertIn("*.vue", vue_files["src/vite-env.d.ts"]["content"])
        self.assertNotIn("Dockerfile", vue_files)

        # 3. web-fullstack
        fullstack_ctx = {
            "project_name": "saas_platform",
            "project_slug": "saas_platform",
            "description": "Fullstack Platform",
            "docker": True,
            "github_actions": True,
            "vscode": True,
            "enable_git_hooks": False,
            "enable_agent_configs": True,
            "selected_agent_rules": [
                "fastapi_best_practices",
                "web_frontend_standards",
            ],
            "selected_agent_skills": ["code-review"],
        }
        fs_files = self.manager.preview("web-fullstack", fullstack_ctx)
        self.assertIn("docker-compose.yml", fs_files)
        self.assertIn("backend/pyproject.toml", fs_files)
        self.assertIn("backend/src/main.py", fs_files)
        self.assertIn("backend/tests/test_api.py", fs_files)
        self.assertIn("frontend/package.json", fs_files)
        self.assertIn("frontend/src/App.tsx", fs_files)
        self.assertIn("frontend/src/vite-env.d.ts", fs_files)
        self.assertIn("frontend/tests/App.test.tsx", fs_files)
        self.assertIn("frontend/vite.config.ts", fs_files)
        self.assertIn("/api/health", fs_files["backend/src/main.py"]["content"])
        self.assertIn("proxy", fs_files["frontend/vite.config.ts"]["content"])
        # Ensure no unused React imports that trigger TS6133
        self.assertNotIn("import React", fs_files["frontend/src/App.tsx"]["content"])
        self.assertNotIn(
            "import React", fs_files["frontend/tests/App.test.tsx"]["content"]
        )

    def test_preview_go_and_dotnet_app(self):
        """Verifies template rendering and preview for go-app and dotnet-app."""
        # 1. go-app (CLI)
        go_ctx = {
            "project_name": "backup_tool",
            "project_slug": "backup_tool",
            "description": "Go Backup CLI",
            "app_type": "cli",
            "github_actions": True,
            "docker": False,
            "enable_git_hooks": False,
            "enable_agent_configs": True,
            "selected_agent_rules": ["go_standards"],
            "selected_agent_skills": ["code-review"],
        }
        go_files = self.manager.preview("go-app", go_ctx)
        self.assertIn("go.mod", go_files)
        self.assertIn("main.go", go_files)
        self.assertIn("main_test.go", go_files)
        self.assertIn(".agents/rules/go_standards.md", go_files)
        self.assertIn("module backup_tool", go_files["go.mod"]["content"])
        self.assertNotIn("chi", go_files["go.mod"]["content"])

        # 2. go-app (Service)
        go_svc_ctx = dict(go_ctx, app_type="service", docker=True)
        go_svc_files = self.manager.preview("go-app", go_svc_ctx)
        self.assertIn("chi", go_svc_files["go.mod"]["content"])
        self.assertIn("SetupRouter", go_svc_files["main.go"]["content"])
        self.assertIn("Dockerfile", go_svc_files)

        # 3. dotnet-app (Web API)
        dotnet_ctx = {
            "project_name": "InvoiceService",
            "project_slug": "invoice_service",
            "description": "Invoice API",
            "app_type": "webapi",
            "dotnet_version": "net8.0",
            "github_actions": True,
            "docker": True,
            "enable_git_hooks": False,
            "enable_agent_configs": True,
            "selected_agent_rules": ["csharp_standards"],
            "selected_agent_skills": ["code-review"],
        }
        dotnet_files = self.manager.preview("dotnet-app", dotnet_ctx)
        self.assertIn("InvoiceService.sln", dotnet_files)
        self.assertIn("src/InvoiceService.csproj", dotnet_files)
        self.assertIn("src/Program.cs", dotnet_files)
        self.assertIn("tests/InvoiceService.Tests.csproj", dotnet_files)
        self.assertIn("tests/UnitTest1.cs", dotnet_files)
        self.assertIn(".agents/rules/csharp_standards.md", dotnet_files)
        self.assertIn("net8.0", dotnet_files["src/InvoiceService.csproj"]["content"])
        self.assertIn(
            "WebApplication.CreateBuilder", dotnet_files["src/Program.cs"]["content"]
        )
        self.assertIn("using Xunit;", dotnet_files["tests/UnitTest1.cs"]["content"])
        self.assertIn(
            "InvoiceService.csproj", dotnet_files["InvoiceService.sln"]["content"]
        )
        self.assertIn("Dockerfile", dotnet_files)

    def test_retrofit_functionality(self):
        """Verifies retrofitting hooks and agent configs into an existing project."""
        with tempfile.TemporaryDirectory() as temp_dir:
            proj_dir = Path(temp_dir) / "existing_proj"
            proj_dir.mkdir()
            (proj_dir / "app.py").write_text("print('hello')", encoding="utf-8")

            # 1. Retrofit hooks
            self.manager.retrofit_hooks(
                proj_dir, ["pre-commit", "commit-msg"], enable_autotag=True
            )
            self.assertTrue((proj_dir / ".git").exists())
            self.assertTrue((proj_dir / ".git" / "hooks" / "pre-commit").exists())
            self.assertTrue((proj_dir / ".git" / "hooks" / "commit-msg").exists())

            # Check git config for autotag and push.followTags
            autotag_val = subprocess.check_output(
                ["git", "config", "--get", "hooks.autotag"], cwd=proj_dir, text=True
            ).strip()
            self.assertEqual(autotag_val, "true")
            followtags_val = subprocess.check_output(
                ["git", "config", "--get", "push.followTags"], cwd=proj_dir, text=True
            ).strip()
            self.assertEqual(followtags_val, "true")

            # 2. Retrofit agent configs
            self.manager.retrofit_agent_configs(
                proj_dir, ["general_guidelines"], ["code-review"]
            )
            self.assertTrue(
                (proj_dir / ".agents" / "rules" / "general_guidelines.md").exists()
            )
            self.assertTrue((proj_dir / ".agents" / "skills" / "code-review").exists())
            self.assertTrue((proj_dir / "AGENTS.md").exists())

    def test_create_template_from_project(self):
        """Verifies creating a reusable template from an existing folder."""
        with tempfile.TemporaryDirectory() as temp_dir:
            src_dir = Path(temp_dir) / "my_existing_service"
            src_dir.mkdir()
            (src_dir / "README.md").write_text(
                "# my_existing_service\nSome info", encoding="utf-8"
            )
            (src_dir / "pyproject.toml").write_text(
                '[project]\nname = "my_existing_service"\nversion = "0.1.0"',
                encoding="utf-8",
            )
            (src_dir / ".venv").mkdir()  # should be ignored

            out_templates_dir = Path(temp_dir) / "custom_templates"
            out_templates_dir.mkdir()

            tpl_dir = self.manager.create_template_from_project(
                source_dir=src_dir,
                output_dir=out_templates_dir,
                template_name="My Service Template",
                language="Python",
                description="Exported template test",
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
                        f"Heading at line {i + 1} ('{line}') must be followed by a blank line.",
                    )
                # Heading must be preceded by a blank line if not first line
                if i > 0:
                    self.assertEqual(
                        lines[i - 1],
                        "",
                        f"Heading at line {i + 1} ('{line}') must be preceded by a blank line.",
                    )

    def test_agents_md_markdownlint_compliance(self):
        """Verifies that AGENTS.md complies with Markdownlint rules both on generation and retrofit."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # 1. Retrofit test
            proj_dir = Path(temp_dir) / "test_proj"
            proj_dir.mkdir()
            self.manager.retrofit_agent_configs(
                proj_dir, ["general_guidelines"], ["code-review"]
            )

            agents_md_path = proj_dir / "AGENTS.md"
            self.assertTrue(agents_md_path.exists())
            self._assert_markdownlint_compliant(
                agents_md_path.read_text(encoding="utf-8")
            )

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
            self.manager.generate(
                new_proj_dir, "python-cli", context, log_callback=lambda msg: None
            )
            gen_agents_md = new_proj_dir / "AGENTS.md"
            self.assertTrue(gen_agents_md.exists())
            self._assert_markdownlint_compliant(
                gen_agents_md.read_text(encoding="utf-8")
            )

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
            (tpl_dir / "README.md.j2").write_text(
                "# {{ project_name }}\n", encoding="utf-8"
            )

            manager = TemplateManager(tpl_root)
            target_dir = Path(temp_dir) / "out"
            context = {"project_name": "out", "custom_scripts": {}}
            problems = manager.generate(
                target_dir, "broken", context, log_callback=lambda msg: None
            )

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

            self.manager.generate(
                target_dir, "python-gui", context, log_callback=lambda msg: None
            )
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
            self.assertIn(
                expected_gui_block, preview_files["pyproject.toml"]["content"]
            )

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
            self.assertIn(
                expected_fastapi_block, preview_fastapi["pyproject.toml"]["content"]
            )

    @patch("subprocess.run")
    def test_render_all_templates_and_framework_variants(self, mock_subp):
        """Verifies that all templates and framework variants render completely without Jinja2 errors."""
        mock_subp.return_value.returncode = 0
        mock_subp.return_value.stdout = ""
        mock_subp.return_value.stderr = ""

        variants = [
            ("web-frontend", {"framework": "react"}),
            ("web-frontend", {"framework": "vue"}),
            ("web-frontend", {"framework": "svelte"}),
            ("web-fullstack", {}),
            ("python-game", {"framework": "pygame-ce"}),
            ("python-game", {"framework": "arcade"}),
            ("python-tui", {}),
            ("go-app", {"app_type": "cli"}),
            ("go-app", {"app_type": "service"}),
            ("dotnet-app", {"app_type": "webapi", "dotnet_version": "net8.0"}),
            ("dotnet-app", {"app_type": "console", "dotnet_version": "net9.0"}),
            ("dotnet-app", {"app_type": "avalonia", "dotnet_version": "net8.0"}),
            ("python-cli", {}),
            ("python-fastapi", {}),
            ("python-gui", {"framework": "pyside6"}),
            ("rust-cli", {}),
            ("rust-gui", {"framework": "egui"}),
            ("node-ts", {}),
        ]

        for t_id, extra_ctx in variants:
            with tempfile.TemporaryDirectory() as td:
                target = Path(td) / "test_proj"
                ctx = {
                    "project_name": "test-proj",
                    "project_slug": "test_proj",
                    "description": "A test project",
                    "author": "Tester",
                    "author_email": "tester@example.com",
                    "license": "MIT",
                    "custom_scripts": {},
                    "github_actions": True,
                    "docker": True,
                    "vscode": True,
                    "enable_git_hooks": True,
                    "enable_git_tags": True,
                    "selected_git_hooks": ["pre-commit", "commit-msg"],
                    "enable_agent_configs": True,
                    "selected_agent_rules": ["general_guidelines"],
                    "selected_agent_skills": ["code-review"],
                    "default_branch": "main",
                    "gitlab": {"enabled": False},
                }
                ctx.update(extra_ctx)
                self.manager.generate(target, t_id, ctx)
                rendered_files = [
                    str(p.relative_to(target)) for p in target.rglob("*") if p.is_file()
                ]
                self.assertGreater(
                    len(rendered_files),
                    0,
                    f"Template {t_id} ({extra_ctx}) produced no files",
                )

                # Verify absence of unused React imports that trigger TS6133
                for app_tsx in [
                    target / "src" / "App.tsx",
                    target / "frontend" / "src" / "App.tsx",
                ]:
                    if app_tsx.exists():
                        self.assertNotIn(
                            "import React", app_tsx.read_text(encoding="utf-8")
                        )
                for test_tsx in [
                    target / "tests" / "App.test.tsx",
                    target / "frontend" / "tests" / "App.test.tsx",
                ]:
                    if test_tsx.exists():
                        self.assertNotIn(
                            "import React", test_tsx.read_text(encoding="utf-8")
                        )

                # Verify python-tui CSS and test compatibility
                if t_id == "python-tui":
                    app_py = (target / "src" / "app.py").read_text(encoding="utf-8")
                    self.assertNotIn("font-size", app_py)
                    self.assertIn("__test__ = False", app_py)

                # Verify dotnet solution and Xunit imports
                if t_id == "dotnet-app":
                    self.assertTrue((target / "test-proj.sln").exists())
                    unit_test = (target / "tests" / "UnitTest1.cs").read_text(
                        encoding="utf-8"
                    )
                    self.assertIn("using Xunit;", unit_test)


if __name__ == "__main__":
    unittest.main()
