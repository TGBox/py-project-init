import re
import shutil
import subprocess
from pathlib import Path
import yaml
from jinja2 import Environment, FileSystemLoader


class TemplateManager:
    def __init__(
        self,
        templates_dir: Path,
        custom_dirs: list[Path] | None = None,
        hooks_dir: Path | None = None,
        agent_configs_dir: Path | None = None,
    ):
        self.templates_dirs: list[Path] = [templates_dir]
        if custom_dirs:
            for d in custom_dirs:
                if d not in self.templates_dirs:
                    self.templates_dirs.append(d)

        base_dir = templates_dir.parent
        self.hooks_dir: Path = hooks_dir or (base_dir / "hooks")
        # Fallback to tmp/ if hooks/ does not exist yet
        if not self.hooks_dir.exists() and (base_dir / "tmp").exists():
            self.hooks_dir = base_dir / "tmp"

        self.agent_configs_dir: Path = agent_configs_dir or (base_dir / "assets" / "agent_configs")

        self.templates: dict[str, dict] = {}
        self.reload_templates()

    def add_custom_dir(self, custom_dir: Path):
        """Adds another directory containing templates."""
        if custom_dir not in self.templates_dirs:
            self.templates_dirs.append(custom_dir)
            self.reload_templates()

    def reload_templates(self):
        """Reloads all templates from all configured directories."""
        self.templates.clear()
        for base_dir in self.templates_dirs:
            if not base_dir.exists():
                continue
            for folder in base_dir.iterdir():
                yaml_file = folder / "template.yaml"
                if folder.is_dir() and yaml_file.exists():
                    try:
                        with open(yaml_file, "r", encoding="utf-8") as f:
                            config = yaml.safe_load(f) or {}
                            config["id"] = folder.name
                            config["path"] = folder
                            self.templates[folder.name] = config
                    except Exception as e:
                        print(f"Fehler beim Laden von {yaml_file}: {e}")

    def get_available_hooks(self) -> list[dict]:
        """Discovers available git hooks from hooks directory."""
        hooks = []
        if not self.hooks_dir.exists():
            return hooks

        meta_file = self.hooks_dir / "hooks.yaml"
        metadata: dict[str, dict] = {}
        if meta_file.exists():
            try:
                with open(meta_file, "r", encoding="utf-8") as f:
                    metadata = yaml.safe_load(f) or {}
            except Exception as e:
                print(f"Fehler beim Laden von {meta_file}: {e}")

        # Scan files in hooks_dir
        for file in self.hooks_dir.iterdir():
            if file.is_file() and not file.name.endswith((".yaml", ".yml", ".md", ".txt")):
                hook_id = file.name
                meta = metadata.get(hook_id, {})
                hooks.append({
                    "id": hook_id,
                    "name": meta.get("name", hook_id),
                    "description": meta.get("description", f"Git Hook Skript '{hook_id}'"),
                    "default": meta.get("default", True),
                    "path": file,
                })
        return hooks

    def get_agent_manifest(self) -> dict:
        """Loads available agent rules and skills manifest."""
        manifest_file = self.agent_configs_dir / "manifest.yaml"
        if not manifest_file.exists():
            return {"rules": [], "skills": []}

        try:
            with open(manifest_file, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {"rules": [], "skills": []}
        except Exception as e:
            print(f"Fehler beim Laden von {manifest_file}: {e}")
            return {"rules": [], "skills": []}

    def get_recommended_agent_configs(self, template_id: str, language: str) -> dict[str, list[str]]:
        """Calculates recommended rules and skills for the given template."""
        manifest = self.get_agent_manifest()
        recommended_rules: list[str] = []
        recommended_skills: list[str] = []

        for rule in manifest.get("rules", []):
            rule_id = rule.get("id")
            rule_langs = rule.get("languages", ["all"])
            rule_templates = rule.get("templates", [])

            matches_lang = "all" in rule_langs or language in rule_langs
            matches_tpl = not rule_templates or template_id in rule_templates

            if matches_lang and matches_tpl and rule.get("default", True):
                recommended_rules.append(rule_id)

        for skill in manifest.get("skills", []):
            skill_id = skill.get("id")
            skill_langs = skill.get("languages", ["all"])
            skill_templates = skill.get("templates", [])

            matches_lang = "all" in skill_langs or language in skill_langs
            matches_tpl = not skill_templates or template_id in skill_templates

            if matches_lang and matches_tpl and skill.get("default", True):
                recommended_skills.append(skill_id)

        return {"rules": recommended_rules, "skills": recommended_skills}

    def generate(self, target_dir: Path, template_id: str, context: dict, log_callback=print, is_cancelled=None):
        def check_cancel():
            if is_cancelled and is_cancelled():
                raise InterruptedError("Initialisierung durch Benutzer abgebrochen.")

        template_meta = self.templates.get(template_id)
        if not template_meta:
            raise ValueError(f"Template '{template_id}' nicht gefunden.")

        template_path: Path = template_meta["path"]
        env = Environment(loader=FileSystemLoader(template_path))
        target_dir.mkdir(parents=True, exist_ok=True)

        # 1. Optionale Pre-Init Hooks (z.B. uv init, uv venv)
        pre_init_hooks = template_meta.get("hooks", {}).get("pre_init", [])
        for cmd in pre_init_hooks:
            check_cancel()
            log_callback(f"Führe Pre-Init Schritt aus: {' '.join(cmd)}")
            res = subprocess.run(cmd, cwd=target_dir, capture_output=True, text=True, shell=True)
            if res.returncode != 0:
                log_callback(f"Warnung bei Pre-Init: {res.stderr.strip() or res.stdout.strip()}")
            elif res.stdout.strip():
                log_callback(res.stdout.strip())

        # 2. Git Repository initialisieren
        check_cancel()
        self._init_git_repo(target_dir, log_callback)

        # 3. Git Hooks einrichten (falls ausgewählt)
        if context.get("enable_git_hooks", False):
            check_cancel()
            selected_hooks = context.get("selected_git_hooks", [])
            self._install_git_hooks(target_dir, selected_hooks, log_callback)

        # 4. Agenten-Konfiguration (.agents/ & AGENTS.md)
        if context.get("enable_agent_configs", False):
            check_cancel()
            selected_rules = context.get("selected_agent_rules", [])
            selected_skills = context.get("selected_agent_skills", [])
            self._install_agent_configs(target_dir, selected_rules, selected_skills, log_callback)

        # 5. Dateien & Ordnerstrukturen rendern
        file_conditions: list[dict] = template_meta.get("file_conditions", [])
        for root, dirs, files in template_path.walk():
            check_cancel()
            rel_path = root.relative_to(template_path)
            if "template.yaml" in files:
                files.remove("template.yaml")

            dest_dir = target_dir / Path(env.from_string(str(rel_path)).render(context))
            dest_dir.mkdir(parents=True, exist_ok=True)

            for file in files:
                check_cancel()
                if not self._should_include(rel_path, file, file_conditions, context):
                    continue

                src_file = root / file
                dest_filename = file[:-3] if file.endswith(".j2") else file
                dest_filename = env.from_string(dest_filename).render(context)
                dest_file = dest_dir / dest_filename

                if file.endswith(".j2"):
                    template = env.get_template(str(rel_path / file).replace("\\", "/"))
                    rendered_content = template.render(context)

                    # Smart .gitignore merge
                    if dest_filename == ".gitignore" and dest_file.exists():
                        merged = self._merge_gitignore(dest_file.read_text(encoding="utf-8"), rendered_content)
                        dest_file.write_text(merged, encoding="utf-8")
                        log_callback("Aktualisiert (zusammengeführt): .gitignore")
                    else:
                        dest_file.write_text(rendered_content, encoding="utf-8")
                        log_callback(f"Angelegt: {dest_file.relative_to(target_dir)}")
                else:
                    if dest_filename == ".gitignore" and dest_file.exists():
                        merged = self._merge_gitignore(dest_file.read_text(encoding="utf-8"), src_file.read_text(encoding="utf-8"))
                        dest_file.write_text(merged, encoding="utf-8")
                        log_callback("Aktualisiert (zusammengeführt): .gitignore")
                    else:
                        dest_file.write_bytes(src_file.read_bytes())
                        log_callback(f"Angelegt: {dest_file.relative_to(target_dir)}")

        # Clean up unwanted uv skeleton files if overridden by template
        uv_dummy_hello = target_dir / "hello.py"
        if uv_dummy_hello.exists() and (target_dir / "src").exists():
            try:
                uv_dummy_hello.unlink()
                log_callback("Bereinigt: Temporäres hello.py von uv init entfernt.")
            except OSError:
                pass

        # 6. Optionale Post-Create Hooks (z.B. uv sync, npm install, cargo check)
        hooks = template_meta.get("hooks", {}).get("post_create", [])
        for cmd in hooks:
            check_cancel()
            log_callback(f"Führe Hook aus: {' '.join(cmd)}")
            res = subprocess.run(cmd, cwd=target_dir, capture_output=True, text=True, shell=True)
            if res.returncode != 0:
                log_callback(f"Warnung bei Hook: {res.stderr.strip()}")
            elif res.stdout.strip():
                log_callback(res.stdout.strip())

        # 7. Initialer Commit mit --no-verify
        check_cancel()
        self._commit_initial(target_dir, log_callback, is_cancelled=is_cancelled)

    def _should_include(self, rel_path: Path, filename: str, conditions: list[dict], context: dict) -> bool:
        """Returns False if a when-condition is not met."""
        full_rel = str(rel_path / filename).replace("\\", "/")
        for entry in conditions:
            pattern = entry.get("pattern", "")
            ctx_key = entry.get("when", "")
            if full_rel.startswith(pattern):
                if not context.get(ctx_key, False):
                    return False
        return True

    def _merge_gitignore(self, existing_text: str, incoming_text: str) -> str:
        """Merges two gitignore contents while avoiding duplicate lines."""
        existing_lines = existing_text.splitlines()
        incoming_lines = incoming_text.splitlines()
        existing_set = {line.strip() for line in existing_lines if line.strip()}

        merged = list(existing_lines)
        for line in incoming_lines:
            stripped = line.strip()
            if stripped and stripped not in existing_set:
                merged.append(line)
                existing_set.add(stripped)
        return "\n".join(merged) + "\n"

    def _init_git_repo(self, target_dir: Path, log_callback):
        """Initializes git repository if not already present."""
        if not (target_dir / ".git").exists():
            log_callback("Initialisiere Git Repository...")
            res = subprocess.run(["git", "init"], cwd=target_dir, capture_output=True, text=True)
            if res.returncode != 0:
                log_callback(f"Git-Meldung: {res.stderr.strip() or res.stdout.strip()}")
            else:
                log_callback("Erfolg: git init")

    def _install_git_hooks(self, target_dir: Path, selected_hooks: list[str], log_callback):
        """Copies selected git hooks to .git/hooks/ and sets executable permissions."""
        git_hooks_dir = target_dir / ".git" / "hooks"
        git_hooks_dir.mkdir(parents=True, exist_ok=True)

        for hook_id in selected_hooks:
            src = self.hooks_dir / hook_id
            if src.is_file():
                dst = git_hooks_dir / hook_id
                shutil.copy2(src, dst)
                try:
                    # Grant execute permissions (POSIX / Git Bash)
                    dst.chmod(dst.stat().st_mode | 0o755)
                except OSError:
                    pass
                log_callback(f"Git-Hook installiert: {hook_id}")

    def _install_agent_configs(
        self,
        target_dir: Path,
        selected_rules: list[str],
        selected_skills: list[str],
        log_callback
    ):
        """Copies chosen rules and skills into .agents/ and generates AGENTS.md."""
        agents_dir = target_dir / ".agents"
        rules_dir = agents_dir / "rules"
        skills_dir = agents_dir / "skills"
        rules_dir.mkdir(parents=True, exist_ok=True)
        skills_dir.mkdir(parents=True, exist_ok=True)

        manifest = self.get_agent_manifest()
        active_rules_info: list[dict] = []
        active_skills_info: list[dict] = []

        # Copy rules
        for rule in manifest.get("rules", []):
            if rule.get("id") in selected_rules:
                rel_file = rule.get("file")
                src_file = self.agent_configs_dir / rel_file
                if src_file.is_file():
                    dst_file = rules_dir / src_file.name
                    shutil.copy2(src_file, dst_file)
                    active_rules_info.append(rule)
                    log_callback(f"Agent-Regel hinzugefügt: {rule.get('name')}")

        # Copy skills
        for skill in manifest.get("skills", []):
            if skill.get("id") in selected_skills:
                rel_folder = skill.get("folder")
                src_folder = self.agent_configs_dir / rel_folder
                if src_folder.is_dir():
                    dst_folder = skills_dir / src_folder.name
                    if dst_folder.exists():
                        shutil.rmtree(dst_folder)
                    shutil.copytree(src_folder, dst_folder)
                    active_skills_info.append(skill)
                    log_callback(f"Agent-Skill hinzugefügt: {skill.get('name')}")

        # Generate AGENTS.md in project root
        agents_md_lines = [
            "# Agent Workspace Configuration",
            "",
            "Dieses Projekt enthält projektspezifische Richtlinien und Skills für Coding-Agenten im Verzeichnis `.agents/`.",
            "",
            "## Aktive Regeln (`.agents/rules/`)",
        ]
        if active_rules_info:
            for r in active_rules_info:
                agents_md_lines.append(f"- **{r.get('name')}**: {r.get('description')}")
        else:
            agents_md_lines.append("- Keine spezifischen Regeln ausgewählt.")

        agents_md_lines.extend([
            "",
            "## Aktive Skills (`.agents/skills/`)",
        ])
        if active_skills_info:
            for s in active_skills_info:
                agents_md_lines.append(f"- **{s.get('name')}**: {s.get('description')}")
        else:
            agents_md_lines.append("- Keine spezifischen Skills ausgewählt.")

        agents_md_lines.extend([
            "",
            "## Richtlinien für KI-Agenten",
            "1. Lies vor größeren Änderungen die anwendbaren Regeln in `.agents/rules/`.",
            "2. Verwende die Skills in `.agents/skills/` für automatisierte Workflows wie Reviews und Tests.",
            "3. Behalte die Projektstruktur sauber und folge den etablierten Konventionen.",
            ""
        ])

        (target_dir / "AGENTS.md").write_text("\n".join(agents_md_lines), encoding="utf-8")
        log_callback("AGENTS.md im Projektstamm generiert.")

    def preview(self, template_id: str, context: dict) -> dict[str, dict]:
        """Generates an in-memory simulation of the resulting project structure and files."""
        template_meta = self.templates.get(template_id)
        if not template_meta:
            raise ValueError(f"Template '{template_id}' nicht gefunden.")

        template_path: Path = template_meta["path"]
        env = Environment(loader=FileSystemLoader(template_path))
        file_conditions: list[dict] = template_meta.get("file_conditions", [])
        files_map: dict[str, dict] = {}

        # 1. Pre-init generated items
        pre_init_hooks = template_meta.get("hooks", {}).get("pre_init", [])
        has_uv_init = any("uv" in cmd and "init" in cmd for cmd in pre_init_hooks)
        has_uv_venv = any("uv" in cmd and "venv" in cmd for cmd in pre_init_hooks)

        if has_uv_venv:
            files_map[".venv"] = {"is_dir": True, "content": None, "source": "uv venv"}
        if has_uv_init:
            files_map[".python-version"] = {"is_dir": False, "content": "3.12\n", "source": "uv init"}
            files_map[".gitignore"] = {
                "is_dir": False,
                "content": ".venv/\n__pycache__/\n*.pyc\n.ruff_cache/\n.pytest_cache/\ndist/\nbuild/\n",
                "source": "uv init"
            }

        # 2. Git repository & hooks
        files_map[".git"] = {"is_dir": True, "content": None, "source": "git init"}
        if context.get("enable_git_hooks", False):
            files_map[".git/hooks"] = {"is_dir": True, "content": None, "source": "git hooks"}
            for hook_id in context.get("selected_git_hooks", []):
                hook_file = self.hooks_dir / hook_id
                hook_content = hook_file.read_text(encoding="utf-8") if hook_file.is_file() else "# Hook script"
                files_map[f".git/hooks/{hook_id}"] = {
                    "is_dir": False,
                    "content": hook_content,
                    "source": f"Hook '{hook_id}'"
                }

        # 3. Agent configs
        if context.get("enable_agent_configs", False):
            files_map[".agents"] = {"is_dir": True, "content": None, "source": "Agenten-Setup"}
            files_map[".agents/rules"] = {"is_dir": True, "content": None, "source": "Agenten-Regeln"}
            files_map[".agents/skills"] = {"is_dir": True, "content": None, "source": "Agenten-Skills"}

            manifest = self.get_agent_manifest()
            selected_rules = context.get("selected_agent_rules", [])
            active_rules_info: list[dict] = []
            for rule in manifest.get("rules", []):
                if rule.get("id") in selected_rules:
                    src_file = self.agent_configs_dir / rule.get("file", "")
                    content = src_file.read_text(encoding="utf-8") if src_file.is_file() else ""
                    files_map[f".agents/rules/{src_file.name}"] = {
                        "is_dir": False,
                        "content": content,
                        "source": f"Regel: {rule.get('name')}"
                    }
                    active_rules_info.append(rule)

            selected_skills = context.get("selected_agent_skills", [])
            active_skills_info: list[dict] = []
            for skill in manifest.get("skills", []):
                if skill.get("id") in selected_skills:
                    s_folder = skill.get("folder", "")
                    src_skill_file = self.agent_configs_dir / s_folder / "SKILL.md"
                    content = src_skill_file.read_text(encoding="utf-8") if src_skill_file.is_file() else ""
                    files_map[f".agents/skills/{Path(s_folder).name}/SKILL.md"] = {
                        "is_dir": False,
                        "content": content,
                        "source": f"Skill: {skill.get('name')}"
                    }
                    active_skills_info.append(skill)

            # AGENTS.md
            agents_md_lines = [
                "# Agent Workspace Configuration",
                "",
                f"Dieses Projekt ('{context.get('project_name', '')}') enthält projektspezifische Richtlinien und Skills in `.agents/`.",
                "",
                "## Aktive Regeln",
            ]
            for r in active_rules_info:
                agents_md_lines.append(f"- **{r.get('name')}**: {r.get('description')}")
            agents_md_lines.extend(["", "## Aktive Skills"])
            for s in active_skills_info:
                agents_md_lines.append(f"- **{s.get('name')}**: {s.get('description')}")
            files_map["AGENTS.md"] = {
                "is_dir": False,
                "content": "\n".join(agents_md_lines) + "\n",
                "source": "AGENTS.md"
            }

        # 4. Template files
        for root, dirs, files in template_path.walk():
            rel_path = root.relative_to(template_path)
            if "template.yaml" in files:
                files.remove("template.yaml")

            rendered_dir_str = env.from_string(str(rel_path)).render(context).replace("\\", "/")
            if rendered_dir_str and rendered_dir_str != ".":
                files_map[rendered_dir_str] = {"is_dir": True, "content": None, "source": "Template"}

            for file in files:
                if not self._should_include(rel_path, file, file_conditions, context):
                    continue

                dest_filename = file[:-3] if file.endswith(".j2") else file
                dest_filename = env.from_string(dest_filename).render(context)
                full_rel_path = (Path(rendered_dir_str) / dest_filename).as_posix() if rendered_dir_str and rendered_dir_str != "." else dest_filename

                if file.endswith(".j2"):
                    try:
                        template = env.get_template(str(rel_path / file).replace("\\", "/"))
                        rendered_content = template.render(context)
                    except Exception as e:
                        rendered_content = f"# Fehler beim Rendern: {e}"

                    if dest_filename == ".gitignore" and ".gitignore" in files_map:
                        rendered_content = self._merge_gitignore(files_map[".gitignore"]["content"] or "", rendered_content)

                    files_map[full_rel_path] = {
                        "is_dir": False,
                        "content": rendered_content,
                        "source": f"Template ({file})"
                    }
                else:
                    src_file = root / file
                    try:
                        content = src_file.read_text(encoding="utf-8")
                    except UnicodeDecodeError:
                        content = f"[Binärdatei: {src_file.stat().st_size} Bytes]"

                    if dest_filename == ".gitignore" and ".gitignore" in files_map:
                        content = self._merge_gitignore(files_map[".gitignore"]["content"] or "", content)

                    files_map[full_rel_path] = {
                        "is_dir": False,
                        "content": content,
                        "source": f"Template ({file})"
                    }

        return files_map

    def retrofit_hooks(self, target_dir: Path, selected_hooks: list[str], log_callback=print):
        """Retrofits git hooks into an existing project folder."""
        self._init_git_repo(target_dir, log_callback)
        self._install_git_hooks(target_dir, selected_hooks, log_callback)

    def retrofit_agent_configs(
        self,
        target_dir: Path,
        selected_rules: list[str],
        selected_skills: list[str],
        log_callback=print
    ):
        """Retrofits agent rules, skills, and AGENTS.md into an existing project folder."""
        self._install_agent_configs(target_dir, selected_rules, selected_skills, log_callback)

    def create_template_from_project(
        self,
        source_dir: Path,
        output_dir: Path,
        template_name: str,
        language: str,
        description: str,
        log_callback=print
    ) -> Path:
        """Derives a new reusable template from an existing project folder."""
        if not source_dir.is_dir():
            raise ValueError(f"Quellverzeichnis '{source_dir}' existiert nicht.")

        slug = re.sub(r"[^a-zA-Z0-9_-]", "-", template_name.lower().strip())
        target_tpl_dir = output_dir / slug
        target_tpl_dir.mkdir(parents=True, exist_ok=True)

        ignored_names = {
            ".git", ".venv", "venv", "__pycache__", "node_modules",
            "target", "dist", "build", ".idea", ".vscode"
        }

        source_name = source_dir.name
        log_callback(f"Kopiere Projektdateien von '{source_dir}' nach '{target_tpl_dir}'...")

        for root, dirs, files in source_dir.walk():
            dirs[:] = [d for d in dirs if d not in ignored_names]
            rel_root = root.relative_to(source_dir)
            dest_root = target_tpl_dir / rel_root
            dest_root.mkdir(parents=True, exist_ok=True)

            for file in files:
                if file in {".DS_Store", "Thumbs.db"}:
                    continue
                src_file = root / file
                dest_file = dest_root / file

                try:
                    text = src_file.read_text(encoding="utf-8")
                    param_text = text.replace(source_name, "{{ project_name }}")
                    param_text = param_text.replace(source_name.lower().replace("-", "_"), "{{ project_slug }}")

                    if file in {"pyproject.toml", "package.json", "Cargo.toml", "README.md"}:
                        dest_file = dest_root / f"{file}.j2"

                    dest_file.write_text(param_text, encoding="utf-8")
                except UnicodeDecodeError:
                    shutil.copy2(src_file, dest_file)

        tpl_config = {
            "name": template_name,
            "language": language or "Universal",
            "description": description or f"Vorlage basierend auf {source_name}",
            "options": [
                {"id": "github_actions", "label": "CI-Workflow einbinden", "default": True}
            ],
            "hooks": {}
        }
        lang_lower = language.lower()
        if lang_lower == "python":
            tpl_config["hooks"] = {
                "pre_init": [["uv", "init"], ["uv", "venv"]],
                "post_create": [["uv", "sync"]]
            }
        elif lang_lower in {"rust", "cargo"}:
            tpl_config["hooks"] = {
                "post_create": [["cargo", "check"]]
            }
        elif lang_lower in {"typescript", "javascript", "node"}:
            tpl_config["hooks"] = {
                "post_create": [["npm", "install"]]
            }

        with open(target_tpl_dir / "template.yaml", "w", encoding="utf-8") as f:
            yaml.safe_dump(tpl_config, f, allow_unicode=True, sort_keys=False)

        log_callback(f"Vorlage '{template_name}' erfolgreich in '{target_tpl_dir}' erstellt.")
        self.reload_templates()
        return target_tpl_dir

    def _commit_initial(self, target_dir: Path, log_callback, is_cancelled=None):
        """Stages all files and creates initial commit using --no-verify."""
        log_callback("Erstelle initialen Git Commit...")
        commands = [
            ["git", "add", "."],
            ["git", "commit", "-m", "initial commit", "--no-verify"]
        ]
        for cmd in commands:
            if is_cancelled and is_cancelled():
                raise InterruptedError("Initialisierung durch Benutzer abgebrochen.")
            res = subprocess.run(cmd, cwd=target_dir, capture_output=True, text=True)
            if res.returncode != 0:
                log_callback(f"Git-Meldung: {res.stderr.strip() or res.stdout.strip()}")
            else:
                log_callback(f"Erfolg: {' '.join(cmd)}")


# Backward compatibility alias
ProjectGenerator = TemplateManager