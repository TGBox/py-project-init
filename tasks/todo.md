# Task List: Erweiterung der Projektvorlagen

## Phase 1: Python-Spezialisierungen (Game & TUI)

### Task 1: Vorlage `python-game` mit Pygame-ce & Arcade anlegen

**Description:** Erstellt den Vorlagenordner `templates/python-game` mit `template.yaml` (Framework-Auswahl: `pygame-ce` und `arcade`), `pyproject.toml.j2`, Quellcode-Struktur (`src/` mit Game-Loop, Asset-Manager, Settings), Asset-Verzeichnissen (`assets/sprites/`, `assets/audio/`), Tests und GitHub Actions CI.

**Acceptance criteria:**

- [ ] `templates/python-game/template.yaml` definiert Framework-Option mit `pygame-ce` (Default) und `arcade`.
- [ ] `pyproject.toml.j2` bindet je nach Auswahl `pygame-ce>=2.5.0` oder `arcade>=3.0.0` ein.
- [ ] Spielbare Einstiegsdatei `src/main.py.j2` mit Game-Loop, Fensterinitialisierung und Event-Handling für das gewählte Framework.
- [ ] Unit-Tests in `tests/test_game.py.j2` für Basis-Logik und Zustände.
- [ ] Pre-Init (`uv init`, `uv venv`) und Post-Create (`uv sync`) Hooks konfiguriert.

**Verification:**

- [ ] Tests pass: `.\.venv\Scripts\python -m unittest tests/test_generator.py`
- [ ] Manuelle Prüfung der generierten Vorlagendateien auf Syntax und Jinja2-Bedingungen

**Dependencies:** Keine
**Files likely touched:**

- `templates/python-game/template.yaml`
- `templates/python-game/pyproject.toml.j2`
- `templates/python-game/README.md.j2`
- `templates/python-game/.gitignore.j2`
- `templates/python-game/src/main.py.j2`
- `templates/python-game/tests/test_game.py.j2`

**Estimated scope:** Medium: 4-6 files

---

### Task 2: Vorlage `python-tui` mit Textual & Rich anlegen

**Description:** Erstellt `templates/python-tui` für interaktive Terminal User Interfaces basierend auf Textual und Rich, inklusive Widget-Komponenten, Screen-Navigation, Keybindings, Tests und CI.

**Acceptance criteria:**

- [ ] `templates/python-tui/template.yaml` mit Optionen für GitHub Actions und VS Code.
- [ ] `pyproject.toml.j2` mit `textual>=0.80.0` und `rich`.
- [ ] `src/app.py.j2` mit einer lauffähigen Textual-App (Header, Footer, Sidebar, Main Content, Tastaturkürzel).
- [ ] Unittests mit `textual.pilot` zum automatisierten Testen von TUI-Interaktionen.

**Verification:**

- [ ] Tests pass: `.\.venv\Scripts\python -m unittest tests/test_generator.py`

**Dependencies:** Keine
**Files likely touched:**

- `templates/python-tui/template.yaml`
- `templates/python-tui/pyproject.toml.j2`
- `templates/python-tui/README.md.j2`
- `templates/python-tui/.gitignore.j2`
- `templates/python-tui/src/app.py.j2`
- `templates/python-tui/tests/test_app.py.j2`

**Estimated scope:** Medium: 4-6 files

---

### Task 3: Generator-, UI-Skripte & Agent-Regeln für Game & TUI integrieren

**Description:** Aktualisiert `TemplateManager`-Tests in `tests/test_generator.py`, erweitert `MainWindow._get_recommended_scripts` um Presets für Game & TUI und ergänzt `manifest.yaml` um Agenten-Regeln für Game-Entwicklung.

**Acceptance criteria:**

- [ ] `_get_recommended_scripts` in `main_window.py` liefert passende Befehle für `python-game` und `python-tui`.
- [ ] `manifest.yaml` enthält optionale/empfohlene Richtlinie `game_development_guidelines`.
- [ ] `tests/test_generator.py` prüft, dass `python-game` und `python-tui` geladen werden.

**Verification:**

- [ ] Tests pass: `.\.venv\Scripts\python -m unittest discover tests`

**Dependencies:** Task 1, Task 2
**Files likely touched:**

- `src/py_project_init/ui/main_window.py`
- `assets/agent_configs/manifest.yaml`
- `assets/agent_configs/rules/game_development_guidelines.md`
- `tests/test_generator.py`

**Estimated scope:** Small: 3-4 files

---

## Checkpoint: Python-Spezialisierungen

- [ ] Alle Unittests laufen erfolgreich durch (`Ran X tests ... OK`)
- [ ] `python-game` und `python-tui` erscheinen in der Template-Liste und generieren sauberen Code
- [ ] Review mit Entwickler vor Beginn von Phase 2

---

## Phase 2: Web-Frontend & Fullstack

### Task 4: Vorlage `web-frontend` (Vite, TypeScript, React/Vue/Svelte) anlegen

**Description:** Erstellt `templates/web-frontend` als Multi-Framework Web-Setup mit Vite 6+, TypeScript, Vitest, ESLint, Prettier und Framework-Auswahl (React, Vue, Svelte).

**Acceptance criteria:**

- [ ] `templates/web-frontend/template.yaml` mit Select-Option für Framework (`react`, `vue`, `svelte`).
- [ ] `package.json.j2` mit passenden Skripten (`dev`, `build`, `test`, `lint`) und Abhängigkeiten.
- [ ] `vite.config.ts.j2`, `tsconfig.json` und Basiskomponenten für das ausgewählte Framework.
- [ ] CI-Workflow für Typecheck, Lint und Vitest.
- [ ] Post-Create Hook mit `["npm", "install"]`.

**Verification:**

- [ ] Tests pass: `.\.venv\Scripts\python -m unittest tests/test_generator.py`

**Dependencies:** Keine
**Files likely touched:**

- `templates/web-frontend/template.yaml`
- `templates/web-frontend/package.json.j2`
- `templates/web-frontend/vite.config.ts.j2`
- `templates/web-frontend/tsconfig.json`
- `templates/web-frontend/src/`
- `templates/web-frontend/tests/`

**Estimated scope:** Medium: 5-7 files

---

### Task 5: Vorlage `web-fullstack` (FastAPI + React Monorepo mit Docker Compose) anlegen

**Description:** Erstellt `templates/web-fullstack` mit getrenntem `backend/` (FastAPI, uv, Ruff, Pytest) und `frontend/` (Vite + React + TypeScript), inklusive `docker-compose.yml.j2` für gleichzeitigen Start.

**Acceptance criteria:**

- [ ] `backend/` mit vollwertigem FastAPI-Projekt und `pyproject.toml.j2`.
- [ ] `frontend/` mit Vite + React + TypeScript und `package.json.j2`.
- [ ] `docker-compose.yml.j2` verbindet Backend (Port 8000) und Frontend (Port 5173).
- [ ] Pre-Init und Post-Create Hooks für beide Teilbereiche.

**Verification:**

- [ ] Tests pass: `.\.venv\Scripts\python -m unittest tests/test_generator.py`

**Dependencies:** Task 4
**Files likely touched:**

- `templates/web-fullstack/template.yaml`
- `templates/web-fullstack/docker-compose.yml.j2`
- `templates/web-fullstack/backend/`
- `templates/web-fullstack/frontend/`

**Estimated scope:** Medium: 6-8 files

---

### Task 6: UI-Skripte & Agent-Regeln für Frontend & Fullstack integrieren

**Description:** Bindet `web-frontend` und `web-fullstack` in die Empfehlungslogik der GUI ein (`_get_recommended_scripts`) und fügt Web-Frontend-Regeln in das Agenten-Manifest ein.

**Acceptance criteria:**

- [ ] `_get_recommended_scripts` liefert `npm run dev`, `npm run build`, `vitest run` für Web-Templates.
- [ ] Agenten-Manifest erhält `web_frontend_standards.md` für TypeScript/Vite/React.
- [ ] Generator-Tests prüfen fehlerfreies Parsen beider Vorlagen.

**Verification:**

- [ ] Tests pass: `.\.venv\Scripts\python -m unittest discover tests`

**Dependencies:** Task 4, Task 5
**Files likely touched:**

- `src/py_project_init/ui/main_window.py`
- `assets/agent_configs/manifest.yaml`
- `assets/agent_configs/rules/web_frontend_standards.md`
- `tests/test_generator.py`

**Estimated scope:** Small: 3-4 files

---

## Checkpoint: Web & Fullstack

- [ ] Alle Unittests laufen fehlerfrei durch
- [ ] Web-Frontend und Fullstack-Templates in CLI und GUI wählbar
- [ ] Review vor Beginn von Phase 3

---

## Phase 3: Polyglot-Erweiterung (Go & .NET)

### Task 7: Vorlage `go-app` (Go CLI / Web-Service) anlegen

**Description:** Erstellt `templates/go-app` für Go 1.23+ mit Auswahl zwischen CLI (`cobra` / Standard-Flag) und REST-Webservice (`chi`), inklusive `go.mod.j2`, Dockerfile und GitHub Actions.

**Acceptance criteria:**

- [ ] `templates/go-app/template.yaml` mit Framework/Typ-Auswahl (`cli` vs `service`).
- [ ] `go.mod.j2` mit Modulpfad basierend auf Projektname/GitLab-Namespace.
- [ ] `main.go.j2` und Paketstruktur mit Unittests (`*_test.go`).
- [ ] Post-Create Hook: `["go", "mod", "tidy"]`.

**Verification:**

- [ ] Tests pass: `.\.venv\Scripts\python -m unittest tests/test_generator.py`

**Dependencies:** Keine
**Files likely touched:**

- `templates/go-app/template.yaml`
- `templates/go-app/go.mod.j2`
- `templates/go-app/main.go.j2`
- `templates/go-app/main_test.go.j2`
- `templates/go-app/README.md.j2`

**Estimated scope:** Medium: 4-6 files

---

### Task 8: Vorlage `dotnet-app` (.NET 8/9 C# Console / Web API / Avalonia) anlegen

**Description:** Erstellt `templates/dotnet-app` für moderne C# .NET Entwicklung mit Auswahl zwischen `webapi` (Minimal APIs), `console` und `avalonia` (Cross-Platform UI), inklusive `.csproj.j2`, xUnit-Tests und `.sln`.

**Acceptance criteria:**

- [ ] `templates/dotnet-app/template.yaml` mit Select-Option für App-Typ (`webapi`, `console`, `avalonia`).
- [ ] `.csproj.j2` mit Zielframework `net8.0` / `net9.0`.
- [ ] `Program.cs.j2` mit modernem, idiomatischer C#-Code für den gewählten Typ.
- [ ] Testprojekt mit xUnit.
- [ ] Post-Create Hook: `["dotnet", "restore"]`.

**Verification:**

- [ ] Tests pass: `.\.venv\Scripts\python -m unittest tests/test_generator.py`

**Dependencies:** Keine
**Files likely touched:**

- `templates/dotnet-app/template.yaml`
- `templates/dotnet-app/Project.csproj.j2`
- `templates/dotnet-app/Program.cs.j2`
- `templates/dotnet-app/README.md.j2`

**Estimated scope:** Medium: 4-6 files

---

### Task 9: UI-Skripte, Agent-Regeln & Gesamttests für alle neuen Vorlagen

**Description:** Vervollständigt Skript-Empfehlungen für Go (`go run .`, `go test ./...`) und .NET (`dotnet run`, `dotnet test`), hinterlegt Agenten-Regeln für Go und C# und führt Gesamttests aller 12 Vorlagen durch.

**Acceptance criteria:**

- [ ] `_get_recommended_scripts` unterstützt `go` und `dotnet`.
- [ ] `manifest.yaml` bindet `go_standards.md` und `csharp_standards.md` ein.
- [ ] `test_templates_loaded` in `tests/test_generator.py` deckt alle Vorlagen ab.
- [ ] `README.md` dokumentiert alle neuen Vorlagen mit ihren Optionen.

**Verification:**

- [ ] Tests pass: `.\.venv\Scripts\python -m unittest discover tests`

**Dependencies:** Task 7, Task 8
**Files likely touched:**

- `src/py_project_init/ui/main_window.py`
- `assets/agent_configs/manifest.yaml`
- `assets/agent_configs/rules/go_standards.md`
- `assets/agent_configs/rules/csharp_standards.md`
- `tests/test_generator.py`
- `README.md`

**Estimated scope:** Medium: 5-6 files

---

## Checkpoint: Gesamtsystem & Release-Bereitschaft

- [ ] Komplette Test-Suite fehlerfrei (`python -m unittest discover tests`)
- [ ] Alle 12 Vorlagen werden in GUI und CLI einwandfrei erkannt und vorgeschlagen
- [ ] `git status` sauber, bereit für Implementierung oder Feature-Branches
