import argparse
import sys
from pathlib import Path

from py_project_init.core.generator import TemplateManager
from py_project_init.core.github import load_token as load_github_token
from py_project_init.core.gitlab import load_token as load_gitlab_token


def run_cli(args: list[str] | None = None) -> int:
    """Parses command-line arguments and performs project actions or launches GUI."""
    if sys.stdout and hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, OSError):
            pass
    if sys.stderr and hasattr(sys.stderr, "reconfigure"):
        try:
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, OSError):
            pass

    if args is None:
        args = sys.argv[1:]

    # If no arguments provided or explicitly requested --gui, signal to launch GUI
    if not args or "--gui" in args:
        from PySide6.QtWidgets import QApplication

        from py_project_init.ui.main_window import MainWindow

        app = QApplication.instance() or QApplication(sys.argv[:1])
        window = MainWindow()
        window.show()
        return app.exec()

    parser = argparse.ArgumentParser(
        prog="py-project-init",
        description="Initialisiert neue Softwareprojekte basierend auf Jinja2-Vorlagen oder startet die GUI.",
    )
    parser.add_argument(
        "name", nargs="?", help="Name des neuen Projekts (z. B. my-super-service)"
    )
    parser.add_argument(
        "-t",
        "--template",
        help="Vorlagen-ID (z. B. python-cli, python-fastapi, node-ts, rust-cli)",
    )
    parser.add_argument(
        "-p",
        "--path",
        default=".",
        help="Basis-Zielverzeichnis (Standard: aktueller Ordner)",
    )
    parser.add_argument(
        "-d", "--description", default="", help="Kurze Projektbeschreibung"
    )
    parser.add_argument("-a", "--author", default="", help="Name des Autors")
    parser.add_argument("-e", "--email", default="", help="E-Mail-Adresse des Autors")
    parser.add_argument(
        "-l", "--license", default="MIT", help="Lizenz (z. B. MIT, Apache-2.0)"
    )
    parser.add_argument(
        "--no-hooks", action="store_true", help="Git-Hooks nicht einbinden"
    )
    parser.add_argument(
        "--no-tags",
        action="store_true",
        help="Automatisches Git-Tagging bei Versionserhöhung nicht aktivieren",
    )
    parser.add_argument(
        "--no-smart-tests",
        action="store_true",
        help="Smarte Testausführung im Pre-Push-Hook deaktivieren (stets vollständige Testsuite ausführen)",
    )
    parser.add_argument(
        "--renew-tag-on-push",
        action="store_true",
        help="Tag vor jedem Push automatisch auf HEAD erneuern und mitpushen (hooks.renewtagonpush)",
    )
    parser.add_argument(
        "--test-cmd",
        help="Benutzerdefinierter Testbefehl im Pre-Push-Hook (hooks.testcmd)",
    )
    parser.add_argument(
        "--build-exe",
        action="store_true",
        help="Exe-Build vor jedem Push ausführen (hooks.buildexe)",
    )
    parser.add_argument(
        "--build-cmd",
        help="Build-Befehl für Exe (hooks.buildcmd, Standard: Auto-Erkennung)",
    )
    parser.add_argument(
        "--artifact-pattern",
        default="dist/*.exe",
        help="Artefakt-Muster für Build/Deploy (hooks.artifactpattern, Standard: dist/*.exe)",
    )
    parser.add_argument(
        "--deploy-artifact",
        action="store_true",
        help="Gebautes Artefakt in externes Repository übertragen (hooks.deployartifact)",
    )
    parser.add_argument(
        "--external-repo",
        help="URL oder Pfad des externen Artefakt-Repositories (hooks.externalrepo)",
    )
    parser.add_argument(
        "--external-repo-branch",
        default="main",
        help="Ziel-Branch im externen Artefakt-Repository (hooks.externalrepobranch, Standard: main)",
    )
    parser.add_argument(
        "--external-repo-dir",
        default="releases",
        help="Unterordner im externen Repository (hooks.externalrepodir, Standard: releases)",
    )
    parser.add_argument(
        "--no-agents",
        action="store_true",
        help="Agenten-Konfiguration (.agents/) nicht generieren",
    )
    parser.add_argument(
        "--preview",
        action="store_true",
        help="Dateivorschau anzeigen, ohne Dateien auf die Festplatte zu schreiben",
    )
    parser.add_argument(
        "--list", action="store_true", help="Alle verfügbaren Projektvorlagen auflisten"
    )
    parser.add_argument(
        "--gui",
        action="store_true",
        help="Grafische Benutzeroberfläche (PySide6) starten",
    )
    parser.add_argument(
        "--retrofit-hooks",
        metavar="DIR",
        help="Git-Hooks in bestehendem Projektverzeichnis nachrüsten",
    )
    parser.add_argument(
        "--default-branch",
        default="main",
        help="Name des Default-Branches (Standard: main)",
    )
    parser.add_argument(
        "--gitlab-url",
        help="GitLab-Instanz, z. B. https://gitlab.data-al.de – aktiviert die GitLab-Anbindung. Token aus Windows-Tresor oder Umgebungsvariable GITLAB_TOKEN",
    )
    parser.add_argument(
        "--gitlab-namespace",
        default="",
        help="Gruppe/Namespace, z. B. development (leer = persönlicher Namespace)",
    )
    parser.add_argument(
        "--gitlab-visibility",
        default="private",
        choices=["private", "internal", "public"],
        help="Sichtbarkeit des neuen GitLab-Projekts",
    )
    parser.add_argument(
        "--gitlab-work-branch",
        default="develop",
        help="Branch, auf den der initiale Commit gepusht wird (Standard: develop)",
    )
    parser.add_argument(
        "--gitlab-no-mr",
        action="store_true",
        help="Keinen Merge Request in den Default-Branch anlegen",
    )
    parser.add_argument(
        "--gitlab-ssh",
        action="store_true",
        help="SSH- statt HTTPS-URL als Remote verwenden",
    )
    parser.add_argument(
        "--github",
        action="store_true",
        help="Projekt direkt auf GitHub anlegen und initialen Commit pushen",
    )
    parser.add_argument(
        "--github-url",
        default="https://github.com",
        help="GitHub-Instanz (Standard: https://github.com, abweichend für GitHub Enterprise)",
    )
    parser.add_argument(
        "--github-owner",
        default="",
        help="Organisation oder Benutzername auf GitHub (leer = persönlicher Account)",
    )
    parser.add_argument(
        "--github-visibility",
        default="private",
        choices=["private", "public", "internal"],
        help="Sichtbarkeit des neuen GitHub-Repositories (Standard: private)",
    )
    parser.add_argument(
        "--github-work-branch",
        default="develop",
        help="Branch, auf den der initiale Commit gepusht wird (Standard: develop)",
    )
    parser.add_argument(
        "--github-no-pr",
        action="store_true",
        help="Keinen Pull Request in den Default-Branch anlegen",
    )
    parser.add_argument(
        "--github-ssh",
        action="store_true",
        help="SSH- statt HTTPS-URL als GitHub-Remote verwenden",
    )
    parser.add_argument(
        "--retrofit-agents",
        metavar="DIR",
        help="Agenten-Konfiguration in bestehendem Projektverzeichnis nachrüsten",
    )

    parsed = parser.parse_args(args)

    has_gitlab = bool(parsed.gitlab_url)
    has_github = bool(
        parsed.github
        or "--github-url" in args
        or "--github-owner" in args
        or "--github-ssh" in args
        or "--github-no-pr" in args
    )
    if has_gitlab and has_github:
        print(
            "Fehler: Es kann nur entweder GitLab (--gitlab-url) oder GitHub (--github / --github-*) angegeben werden, nicht beides gleichzeitig.",
            file=sys.stderr,
        )
        return 1

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
            print(
                f"Fehler: '{target_path}' ist kein gültiges Verzeichnis.",
                file=sys.stderr,
            )
            return 1
        all_hooks = [h["id"] for h in manager.get_available_hooks()]
        manager.retrofit_hooks(
            target_path,
            all_hooks,
            log_callback=print,
            enable_autotag=not parsed.no_tags,
            enable_smart_tests=not parsed.no_smart_tests,
            enable_renew_tag_on_push=parsed.renew_tag_on_push,
            test_cmd=parsed.test_cmd,
            enable_build_exe=parsed.build_exe,
            build_cmd=parsed.build_cmd,
            artifact_pattern=parsed.artifact_pattern,
            enable_deploy_artifact=parsed.deploy_artifact,
            external_repo=parsed.external_repo,
            external_repo_branch=parsed.external_repo_branch,
            external_repo_dir=parsed.external_repo_dir,
        )
        print(f"\n✔ Git-Hooks erfolgreich in '{target_path}' nachgerüstet.")
        return 0

    if parsed.retrofit_agents:
        target_path = Path(parsed.retrofit_agents).resolve()
        if not target_path.is_dir():
            print(
                f"Fehler: '{target_path}' ist kein gültiges Verzeichnis.",
                file=sys.stderr,
            )
            return 1
        manifest = manager.get_agent_manifest()
        rule_ids = [r["id"] for r in manifest.get("rules", [])]
        skill_ids = [s["id"] for s in manifest.get("skills", [])]
        manager.retrofit_agent_configs(
            target_path, rule_ids, skill_ids, log_callback=print
        )
        print(f"\n✔ Agenten-Konfiguration erfolgreich in '{target_path}' nachgerüstet.")
        return 0

    if not parsed.name:
        parser.print_help()
        return 1

    template_id = parsed.template or "python-cli"
    if template_id not in manager.templates:
        print(
            f"Fehler: Vorlage '{template_id}' existiert nicht. Siehe --list.",
            file=sys.stderr,
        )
        return 1

    template_meta = manager.templates[template_id]
    lang = template_meta.get("language", "")
    all_hooks = (
        [h["id"] for h in manager.get_available_hooks()] if not parsed.no_hooks else []
    )
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
        "enable_smart_tests": not parsed.no_hooks and not parsed.no_smart_tests,
        "enable_renew_tag_on_push": parsed.renew_tag_on_push,
        "test_cmd": parsed.test_cmd,
        "enable_build_exe": parsed.build_exe,
        "build_cmd": parsed.build_cmd,
        "artifact_pattern": parsed.artifact_pattern,
        "enable_deploy_artifact": parsed.deploy_artifact,
        "external_repo": parsed.external_repo,
        "external_repo_branch": parsed.external_repo_branch,
        "external_repo_dir": parsed.external_repo_dir,
        "selected_git_hooks": all_hooks,
        "enable_agent_configs": not parsed.no_agents,
        "selected_agent_rules": recommended.get("rules", []),
        "selected_agent_skills": recommended.get("skills", []),
        "default_branch": parsed.default_branch,
        "gitlab": {"enabled": False},
        "github": {"enabled": False},
    }

    for opt in template_meta.get("options", []):
        opt_id = opt.get("id")
        if opt_id and opt_id not in context:
            context[opt_id] = opt.get("default")

    if parsed.gitlab_url:
        token = load_gitlab_token(parsed.gitlab_url)
        if not token:
            print(
                "Fehler: Kein GitLab-Token gefunden. Setze GITLAB_TOKEN oder speichere ihn einmal über die GUI.",
                file=sys.stderr,
            )
            return 1
        context["gitlab"] = {
            "enabled": True,
            "url": parsed.gitlab_url,
            "token": token,
            "namespace": parsed.gitlab_namespace,
            "visibility": parsed.gitlab_visibility,
            "work_branch": parsed.gitlab_work_branch,
            "create_mr": not parsed.gitlab_no_mr,
            "use_ssh": parsed.gitlab_ssh,
        }

    if has_github:
        gh_url = parsed.github_url or "https://github.com"
        token = load_github_token(gh_url)
        if not token:
            print(
                "Fehler: Kein GitHub-Token gefunden. Setze GITHUB_TOKEN (oder GH_TOKEN), melde dich per 'gh auth login' an oder speichere das Token über die GUI.",
                file=sys.stderr,
            )
            return 1
        context["github"] = {
            "enabled": True,
            "url": gh_url,
            "token": token,
            "owner": parsed.github_owner,
            "visibility": parsed.github_visibility,
            "work_branch": parsed.github_work_branch,
            "create_pr": not parsed.github_no_pr,
            "use_ssh": parsed.github_ssh,
        }

    if parsed.preview:
        files_map = manager.preview(template_id, context)
        print(
            f"\nVorschau: Zu erstellende Dateien für '{parsed.name}' (Vorlage: {template_id}):"
        )
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
        print(
            f"Fehler: Zielordner '{target_dir}' existiert bereits und ist nicht leer.",
            file=sys.stderr,
        )
        return 1

    print(f"\nInitialisiere '{parsed.name}' mit Vorlage '{template_id}'...")
    problems = manager.generate(target_dir, template_id, context, log_callback=print)
    if problems:
        print(
            f"\n⚠ Projekt angelegt in:\n  {target_dir}\n"
            f"aber {len(problems)} Schritt(e) sind fehlgeschlagen:",
            file=sys.stderr,
        )
        for problem in problems:
            print(f"  ✖ {problem}", file=sys.stderr)
        print(
            "Details zu jedem Fehler stehen weiter oben in der Ausgabe.\n",
            file=sys.stderr,
        )
        return 1
    print(f"\n✔ Projekt erfolgreich erstellt in:\n  {target_dir}\n")
    return 0
