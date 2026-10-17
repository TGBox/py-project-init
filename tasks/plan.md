# Implementation Plan: Erweiterung der Projektvorlagen

## Overview

Dieses Vorhaben erweitert `py-project-init` um sechs moderne, hochgradig praxiserprobte Projektvorlagen:

1. `python-game` (Multi-Framework: Pygame-ce & Arcade mit Asset-Struktur und Game-Loop)
2. `python-tui` (Terminal User Interfaces mit Textual & Rich)
3. `web-frontend` (Vite + TypeScript mit React, Vue oder Svelte)
4. `web-fullstack` (FastAPI Backend + Vite/React Frontend Monorepo mit Docker Compose)
5. `go-app` (Go CLI / Microservice mit Modulen, Tests und Docker)
6. `dotnet-app` (.NET 8/9 C# mit Console, Web API oder Avalonia UI)

Alle Vorlagen integrieren sich nahtlos in die bestehende Generator-Architektur (`template.yaml`, Jinja2-Templates, Pre-/Post-Hooks, GitHub Actions CI, Git-Hooks, automatisches Tagging und maßgeschneiderte `.agents/`-Konfigurationen).

## Architecture Decisions

- **Multi-Framework-Pattern (`template.yaml` mit `type: select`):**
  Wie bei `python-gui` und `rust-gui` werden thematisch verwandte Stacks (z. B. Pygame-ce vs. Arcade, React vs. Vue vs. Svelte, Console vs. Web API vs. Avalonia) in einem gemeinsamen Template-Ordner über Jinja2-Bedingungen (`{% if framework == '...' %}`) abgebildet. Dies verhindert redundante Dateien, hält das Vorlagen-Dropdown in der GUI übersichtlich und sorgt für konsistente Projektstrukturen.
- **Konsistente Hook-Strategie:**
  - Python-basierte Templates nutzen `["uv", "init", "--bare"]`, `["uv", "venv"]` als `pre_init` und `["uv", "sync"]` als `post_create`.
  - Node/Web-Templates nutzen `["npm", "install"]` als `post_create`.
  - Go-Templates nutzen `["go", "mod", "tidy"]` als `post_create`.
  - .NET-Templates nutzen `["dotnet", "restore"]` als `post_create`.
  - Sollte ein Tool (wie `go` oder `dotnet`) auf dem System fehlen, fängt der `generator.py` dies sauber ab, ohne das Dateiscaffolding zu beschädigen.
- **Integration in GUI & CLI:**
  - `TemplateManager` lädt Vorlagen automatisch dynamisch.
  - `MainWindow._get_recommended_scripts` wird erweitert, um für `game`, `tui`, `web`, `fullstack`, `go` und `dotnet` sofort die passenden Task-Skripte (z. B. `npm run dev`, `go test ./...`, `dotnet run`) vorzuschlagen.
- **Agenten-Manifest (`assets/agent_configs/manifest.yaml`):**
  Ergänzung stack-spezifischer Regeln für Game-Development, Web-Frontend, Go und C#/.NET.

## Task List

### Phase 1: Python-Spezialisierungen (Game & TUI)

- [x] Task 1: Vorlage `python-game` mit Pygame-ce & Arcade anlegen
- [x] Task 2: Vorlage `python-tui` mit Textual & Rich anlegen
- [x] Task 3: Generator-, UI-Skripte & Agent-Regeln für Game/TUI integrieren

### Checkpoint: Python-Spezialisierungen

- [x] Unittests für Template-Loading und Generierung von `python-game` und `python-tui` erfolgreich
- [x] UI-Skript-Vorschläge (`_get_recommended_scripts`) verifiziert

### Phase 2: Web-Frontend & Fullstack

- [x] Task 4: Vorlage `web-frontend` (Vite, TypeScript, React/Vue/Svelte) anlegen
- [x] Task 5: Vorlage `web-fullstack` (FastAPI + React Monorepo mit Docker Compose) anlegen
- [x] Task 6: UI-Skripte & Agent-Regeln für Frontend/Fullstack integrieren

### Checkpoint: Web & Fullstack

- [x] Unittests für `web-frontend` und `web-fullstack` erfolgreich
- [x] Template-Optionen und File-Conditions im Generator geprüft

### Phase 3: Polyglot-Erweiterung (Go & .NET)

- [x] Task 7: Vorlage `go-app` (Go CLI / Web-Service) anlegen
- [x] Task 8: Vorlage `dotnet-app` (.NET 8/9 C# Console / Web API / Avalonia) anlegen
- [x] Task 9: UI-Skripte, Agent-Regeln & Gesamttests für alle neuen Vorlagen

### Checkpoint: Gesamtsystem & Release-Bereitschaft

- [x] Alle Unittests in `tests/test_generator.py` und `tests/test_ui.py` grün
- [x] PyInstaller Spec (`ProjectScaffolder.spec`) validiert
- [x] Dokumentation & `README.md` aktualisiert

## Risks and Mitigations

| Risk | Impact | Mitigation |
| ------ | -------- | ------------ |
| Fehlende SDKs auf Benutzerrechnern (`go`, `dotnet`, `node`) | Mittel | Hooks im Generator laufen im `check=False`-Modus und protokollieren Ausgaben als Information/Warnung; das Erzeugen der Projektdateien bleibt 100 % funktionsfähig. |
| Komplexität im Jinja2-Templating bei Multi-Framework-Templates | Gering | Modulare Jinja2-Blöcke und strukturierte Unterordner für frameworks-spezifische Einstiegspunkte. |
| Aufblähung der PyInstaller-Builds | Gering | Reine Text-/Template-Dateien; assets/templates bleiben klein und performant im Bundle. |

## Open Questions

- Standard-Paketmanager für `web-frontend`: `npm` als Standard, mit optionalem Switch auf `pnpm` / `bun`? (Vorschlag: `npm` als Default).
