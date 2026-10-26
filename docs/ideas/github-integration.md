# GitHub-Anbindung (GitHub Integration)

## Problem Statement

Wie können wir Entwicklern ermöglichen, ein neu initialisiertes Projekt nahtlos und vollautomatisch direkt auf GitHub (inkl. Remote-Repository, Initial-Commit, optionalem Arbeits-Branch und Pull Request) anzulegen – mit derselben Zuverlässigkeit, Sicherheit (Windows Credential Store) und Benutzerfreundlichkeit wie bei der bestehenden GitLab-Anbindung?

---

## Empfohlene Architektur & Richtung

### 1. Exklusives Provider-Modell (GitLab vs. GitHub)

- Ein neu initialisiertes Projekt wird entweder ohne Remote, mit GitLab **oder** mit GitHub verknüpft.
- In der GUI (Tab 2) wird die bisherige `GitLab-Anbindung (optional)`-Box durch eine einheitliche **`Git-Remote-Anbindung (optional)`**-Box mit Provider-Umschaltung (`[Kein Remote] | [🦊 GitLab] | [🐙 GitHub]`) ersetzt.
- Der Tab-Titel wird zu **`🌐 Git-Remote, Hooks & Agenten`** aktualisiert.

### 2. API & Authentifizierung (`py_project_init/core/github.py`)

- Schlanker, eigenständiger REST-Client auf Basis der Python-Standardbibliothek (`urllib.request`) – **keine neuen externen Abhängigkeiten**.
- Authentifizierung per Personal Access Token (PAT).
- Sichere Token-Speicherung im Windows-Anmeldeinformationsspeicher via `keyring` (Service: `py-project-init-github`).
- Kaskadierendes Laden des Tokens:
  1. Windows Credential Manager (`keyring`)
  2. Umgebungsvariablen (`GITHUB_TOKEN`, `GH_TOKEN`)
  3. Automatisches Auslesen via lokaler GitHub CLI (`gh auth token`), falls installiert und angemeldet.

### 3. Ziel-Instanzen & Repository-Owner

- Standardmäßig `https://github.com` (API: `https://api.github.com`).
- Volle Unterstützung für GitHub Enterprise Server durch konfigurierbare Basis-URL (z. B. `https://github.mycompany.com`).
- Flexibler Owner: Bleibt das Feld leer, wird das Repository im persönlichen Benutzer-Account angelegt (`POST /user/repos`). Wird ein Name angegeben, wird es unter der entsprechenden Organisation erstellt (`POST /orgs/{org}/repos`).
- Einstellbare Sichtbarkeit: `private` (Standard), `public` oder `internal`.

### 4. Branching, Initialer Commit & Pull Request

- Analog zu GitLab: Das Repository wird initial mit Default-Branch (`main`) angelegt.
- Der lokale Arbeits-Branch (`develop` als Standard) wird ausgecheckt, der Projekt-Commit platziert und nach `origin/develop` gepusht.
- Anschließend wird vollautomatisch ein Pull Request von `develop` nach `main` geöffnet (`POST /repos/{owner}/{repo}/pulls`).
- Ist der Arbeits-Branch identisch mit dem Default-Branch oder ist die PR-Option deaktiviert, erfolgt der Push direkt auf `main`.

### 5. Protokoll & CLI-Interface (`cli.py`)

- Standardmäßig HTTPS mit Option auf SSH (`--github-ssh` bzw. Checkbox in der GUI).
- Saubere CLI-Parameter:
  - `--github`: Aktiviert GitHub (Standard: github.com)
  - `--github-url`: Eigene GitHub (Enterprise) Instanz
  - `--github-owner`: Organisation oder Benutzername
  - `--github-visibility`: `private`, `public`, `internal`
  - `--github-work-branch`: Standard `develop`
  - `--github-no-pr`: Keinen PR erstellen
  - `--github-ssh`: SSH-URL für `origin` verwenden
- Gegenseitiger Ausschluss: Die gleichzeitige Angabe von `--gitlab-url` und `--github` wird in der CLI mit einer verständlichen Fehlermeldung abgefangen.

---

## Zu validierende Kernannahmen

- [x] **Keine externen Abhängigkeiten:** Python stdlib (`urllib.request`) genügt vollkommen für REST-Aufrufe.
- [x] **Windows Credential Store:** Funktioniert nahtlos über das bereits im Projekt vorhandene `keyring`-Paket.
- [x] **Git-Remote-Handling:** Lokales Branching und Pushing verhält sich konsistent zum bewährten GitLab-Ablauf.

---

## MVP Scope

1. **`src/py_project_init/core/github.py`:**
   - `GitHubClient` (stdlib `urllib.request`), `GitHubError`.
   - Endpunkte: `current_user()`, `get_repo()`, `create_repo()`, `create_pull_request()`.
   - Token-Funktionen: `load_token()`, `save_token()`, `delete_token()` (inkl. `gh auth token` Fallback).
2. **`src/py_project_init/core/generator.py`:**
   - `_prepare_github_remote()` und `_push_to_github()`.
   - Factory-Hook `github_client_factory` für einfaches Testen.
   - Integration in `generate()`.
3. **`src/py_project_init/cli.py`:**
   - Neue Argumente (`--github`, `--github-*`) und Validierung.
4. **`src/py_project_init/ui/main_window.py`:**
   - Einheitliche Remote-Box in Tab 2 mit Provider-Auswahl (Kein Remote / GitLab / GitHub).
   - Dynamische Einblendung der Formulare.
   - Verbindungstest-Button für GitHub, Token-Speicherung im Windows-Tresor, Zusammenfassung (`🐙 GitHub`).
5. **Tests & Dokumentation:**
   - `tests/test_github.py` mit Bare-Repo-Mocks und HTTP-Simulation.
   - Aktualisierung von `README.md`, `CHANGELOG.md` und `tasks/todo.md`.

---

## Nicht im Scope („Not Doing“)

- Keine Drittanbieter-Bibliotheken wie `PyGithub` oder `requests`.
- Keine gleichzeitige Verknüpfung mit mehreren Remote-Plattformen im selben Initialisierungsschritt.
- Keine Verwaltung von GitHub Actions Secrets oder Webhooks bei der Repo-Erstellung.
