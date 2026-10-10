import argparse
import sys
from pathlib import Path
from py_project_init.core.generator import TemplateManager


def run_cli(args: list[str] | None = None) -> int:
    """Parses command-line arguments and performs project actions or launches GUI."""
    if args is None:
        args = sys.argv[1:]

    # If no arguments provided or explicitly requested --gui, signal to launch GUI
    if not args or "--gui" in args:
        from py_project_init.ui.main_window import MainWindow
        from PySide6.QtWidgets import QApplication
        app = QApplication.instance() or QApplication(sys.argv[:1])
        window = MainWindow()
        window.show()
        return app.exec()

    parser = argparse.ArgumentParser(
        prog="py-project-init",
        description="Initialisiert neue Softwareprojekte basierend auf Jinja2-Vorlagen oder startet die GUI."
    )
    parser.add_argument("name", nargs="?", help="Name des neuen Projekts (z. B. my-super-service)")
    parser.add_argument("-t", "--template", help="Vorlagen-ID (z. B. python-cli, python-fastapi, node-ts, rust-cli)")
    parser.add_argument("-p", "--path", default=".", help="Basis-Zielverzeichnis (Standard: aktueller Ordner)")
    parser.add_argument("-d", "--description", default="", help="Kurze Projektbeschreibung")
    parser.add_argument("-a", "--author", default="", help="Name des Autors")
    parser.add_argument("-e", "--email", default="", help="E-Mail-Adresse des Autors")
    parser.add_argument("-l", "--license", default="MIT", help="Lizenz (z. B. MIT, Apache-2.0)")
    parser.add_argument("--no-hooks", action="store_true", help="Git-Hooks nicht einbinden")
    parser.add_argument("--no-tags", action="store_true", help="Automatisches Git-Tagging bei Versionserhöhung nicht aktivieren")
    parser.add_argument("--no-agents", action="store_true", help="Agenten-Konfiguration (.agents/) nicht generieren")
    parser.add_argument("--preview", action="store_true", help="Dateivorschau anzeigen, ohne Dateien auf die Festplatte zu schreiben")
    parser.add_argument("--list", action="store_true", help="Alle verfügbaren Projektvorlagen auflisten")
    parser.add_argument("--gui", action="store_true", help="Grafische Benutzeroberfläche (PySide6) starten")
    parser.add_argument("--retrofit-hooks", metavar="DIR", help="Git-Hooks in bestehendem Projektverzeichnis nachrüsten")
    parser.add_argument("--retrofit-agents", metavar="DIR", help="Agenten-Konfiguration in bestehendem Projektverzeichnis nachrüsten")

    parsed = parser.parse_args(args)

    base_dir = Path(__file__).resolve().parent.parent.parent
    templates_dir = base_dir / "templates"
    manager = TemplateManager(templates_dir)

    if parsed.list:
        print("\nVerfügbare Vorlagen:")
        print("------------------------------------------------------------")
        for t_id, meta in manager.templates.items():
            name = meta.get("name", t_id)
            lang = meta.get("language", "Universal")
            desc = meta.get("description", "")
            print(f"  • {t_id:18} [{lang}] {name} - {desc}")
        print("------------------------------------------------------------\n")
        return 0

    if parsed.retrofit_hooks:
        target_path = Path(parsed.retrofit_hooks).resolve()
        if not target_path.is_dir():
            print(f"Fehler: '{target_path}' ist kein gültiges Verzeichnis.", file=sys.stderr)
            return 1
        all_hooks = [h["id"] for h in manager.get_available_hooks()]
        manager.retrofit_hooks(target_path, all_hooks, log_callback=print, enable_autotag=not parsed.no_tags)
        print(f"\n✔ Git-Hooks erfolgreich in '{target_path}' nachgerüstet.")
        return 0

    if parsed.retrofit_agents:
        target_path = Path(parsed.retrofit_agents).resolve()
        if not target_path.is_dir():
            print(f"Fehler: '{target_path}' ist kein gültiges Verzeichnis.", file=sys.stderr)
            return 1
        manifest = manager.get_agent_manifest()
        rule_ids = [r["id"] for r in manifest.get("rules", [])]
        skill_ids = [s["id"] for s in manifest.get("skills", [])]
        manager.retrofit_agent_configs(target_path, rule_ids, skill_ids, log_callback=print)
        print(f"\n✔ Agenten-Konfiguration erfolgreich in '{target_path}' nachgerüstet.")
        return 0

    if not parsed.name:
        parser.print_help()
        return 1

    template_id = parsed.template or "python-cli"
    if template_id not in manager.templates:
        print(f"Fehler: Vorlage '{template_id}' existiert nicht. Siehe --list.", file=sys.stderr)
        return 1

    template_meta = manager.templates[template_id]
    lang = template_meta.get("language", "")
    all_hooks = [h["id"] for h in manager.get_available_hooks()] if not parsed.no_hooks else []
    recommended = manager.get_recommended_agent_configs(template_id, lang)

    context = {
        "project_name": parsed.name,
        "project_slug": parsed.name.lower().replace("-", "_").replace(" ", "_"),
        "description": parsed.description,
        "language": lang,
        "author": parsed.author,
        "author_email": parsed.email,
        "license": parsed.license,
        "custom_scripts": {},
        "docker": False,
        "github_actions": True,
        "vscode": True,
        "enable_git_hooks": not parsed.no_hooks,
        "enable_git_tags": not parsed.no_hooks and not parsed.no_tags,
        "selected_git_hooks": all_hooks,
        "enable_agent_configs": not parsed.no_agents,
        "selected_agent_rules": recommended.get("rules", []),
        "selected_agent_skills": recommended.get("skills", []),
    }

    if parsed.preview:
        files_map = manager.preview(template_id, context)
        print(f"\nVorschau: Zu erstellende Dateien für '{parsed.name}' (Vorlage: {template_id}):")
        print("=" * 60)
        for path_str, info in sorted(files_map.items()):
            kind = "[Ordner]" if info.get("is_dir") else "[Datei]"
            src = info.get("source", "")
            print(f"  {kind:8} {path_str:35} (Quelle: {src})")
        print("=" * 60)
        print("Keine Dateien angelegt (Preview-Modus).\n")
        return 0

    target_dir = Path(parsed.path).resolve() / parsed.name
    if target_dir.exists() and any(target_dir.iterdir()):
        print(f"Fehler: Zielordner '{target_dir}' existiert bereits und ist nicht leer.", file=sys.stderr)
        return 1

    print(f"\nInitialisiere '{parsed.name}' mit Vorlage '{template_id}'...")
    manager.generate(target_dir, template_id, context, log_callback=print)
    print(f"\n✔ Projekt erfolgreich erstellt in:\n  {target_dir}\n")
    return 0
