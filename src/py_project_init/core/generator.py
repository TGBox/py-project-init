import subprocess
from pathlib import Path
import yaml
from jinja2 import Environment, FileSystemLoader


class TemplateManager:
    def __init__(self, templates_dir: Path, custom_dirs: list[Path] | None = None):
        self.templates_dirs: list[Path] = [templates_dir]
        if custom_dirs:
            for d in custom_dirs:
                if d not in self.templates_dirs:
                    self.templates_dirs.append(d)
        self.templates: dict[str, dict] = {}
        self.reload_templates()

    def add_custom_dir(self, custom_dir: Path):
        """Fügt einen weiteren Ordner mit Vorlagen hinzu."""
        if custom_dir not in self.templates_dirs:
            self.templates_dirs.append(custom_dir)
            self.reload_templates()

    def reload_templates(self):
        """Lädt alle Vorlagen aus allen konfigurierten Verzeichnissen neu."""
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

        file_conditions: list[dict] = template_meta.get("file_conditions", [])

        # 1. Dateien & Ordnerstrukturen iterieren und rendern (Path.walk ab Python 3.12)
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
                    dest_file.write_text(template.render(context), encoding="utf-8")
                else:
                    dest_file.write_bytes(src_file.read_bytes())

                log_callback(f"Angelegt: {dest_file.relative_to(target_dir)}")

        # 2. Optionale Post-Create Hooks
        hooks = template_meta.get("hooks", {}).get("post_create", [])
        for cmd in hooks:
            check_cancel()
            log_callback(f"Fuehre Hook aus: {' '.join(cmd)}")
            res = subprocess.run(cmd, cwd=target_dir, capture_output=True, text=True, shell=True)
            if res.returncode != 0:
                log_callback(f"Warnung bei Hook: {res.stderr.strip()}")
            elif res.stdout.strip():
                log_callback(res.stdout.strip())

        # 3. Git initialisieren und initial committen
        check_cancel()
        self._init_git(target_dir, log_callback, is_cancelled=is_cancelled)

    def _should_include(self, rel_path: Path, filename: str, conditions: list[dict], context: dict) -> bool:
        """Gibt False zurueck wenn eine `when:`-Bedingung nicht erfuellt ist."""
        full_rel = str(rel_path / filename).replace("\\", "/")
        for entry in conditions:
            pattern = entry.get("pattern", "")
            ctx_key = entry.get("when", "")
            if full_rel.startswith(pattern):
                if not context.get(ctx_key, False):
                    return False
        return True

    def _init_git(self, target_dir: Path, log_callback, is_cancelled=None):
        log_callback("Initialisiere Git Repository...")
        commands = [
            ["git", "init"],
            ["git", "add", "."],
            ["git", "commit", "-m", "initial commit"]
        ]
        for cmd in commands:
            if is_cancelled and is_cancelled():
                raise InterruptedError("Initialisierung durch Benutzer abgebrochen.")
            res = subprocess.run(cmd, cwd=target_dir, capture_output=True, text=True)
            if res.returncode != 0:
                log_callback(f"Git-Meldung: {res.stderr.strip()}")
            else:
                log_callback(f"Erfolg: {' '.join(cmd)}")


# Backward compatibility alias
ProjectGenerator = TemplateManager