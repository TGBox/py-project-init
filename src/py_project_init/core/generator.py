import os
import subprocess
from pathlib import Path
import yaml
from jinja2 import Environment, FileSystemLoader

class TemplateManager:
    def __init__(self, templates_dir: Path):
        self.templates_dir = templates_dir
        self.templates: dict[str, dict] = {}
        self.reload_templates()

    def reload_templates(self):
        self.templates.clear()
        if not self.templates_dir.exists():
            return

        for folder in self.templates_dir.iterdir():
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

class ProjectGenerator:
    def __init__(self, template_manager: TemplateManager):
        self.manager = template_manager

    def generate(self, target_dir: Path, template_id: str, context: dict, log_callback=print):
        template_meta = self.manager.templates.get(template_id)
        if not template_meta:
            raise ValueError(f"Template '{template_id}' nicht gefunden.")

        template_path = template_meta["path"]
        env = Environment(loader=FileSystemLoader(template_path))
        target_dir.mkdir(parents=True, exist_ok=True)

        # 1. Dateien & Ordnerstrukturen iterieren und rendern
        for root, dirs, files in os.walk(template_path):
            rel_path = Path(root).relative_to(template_path)
            if "template.yaml" in files:
                files.remove("template.yaml")

            dest_dir = target_dir / Path(env.from_string(str(rel_path)).render(context))
            dest_dir.mkdir(parents=True, exist_ok=True)

            for file in files:
                # Optionale Feature-Dateien ausschließen, falls Option deaktiviert
                if (file.startswith("docker") or "docker" in file) and not context.get("docker", False):
                    continue

                src_file = Path(root) / file
                dest_filename = file[:-3] if file.endswith(".j2") else file
                dest_filename = env.from_string(dest_filename).render(context)
                dest_file = dest_dir / dest_filename

                if file.endswith(".j2"):
                    template = env.get_template(str(Path(rel_path) / file).replace("\\", "/"))
                    dest_file.write_text(template.render(context), encoding="utf-8")
                else:
                    dest_file.write_bytes(src_file.read_bytes())

                log_callback(f"Angelegt: {dest_file.relative_to(target_dir)}")

        # 2. Optionale Post-Create Hooks (z. B. uv sync, npm install, cargo check)
        hooks = template_meta.get("hooks", {}).get("post_create", [])
        for cmd in hooks:
            log_callback(f"Führe Hook aus: {' '.join(cmd)}")
            res = subprocess.run(cmd, cwd=target_dir, capture_output=True, text=True, shell=True)
            if res.returncode != 0:
                log_callback(f"Warnung bei Hook: {res.stderr.strip()}")

        # 3. Git initialisieren und initial committen
        self._init_git(target_dir, log_callback)

    def _init_git(self, target_dir: Path, log_callback):
        log_callback("Initialisiere Git Repository...")
        commands = [
            ["git", "init"],
            ["git", "add", "."],
            ["git", "commit", "-m", "initial commit"]
        ]
        for cmd in commands:
            res = subprocess.run(cmd, cwd=target_dir, capture_output=True, text=True)
            if res.returncode != 0:
                log_callback(f"Git-Meldung: {res.stderr.strip()}")
            else:
                log_callback(f"Erfolg: {' '.join(cmd)}")