# Project Scaffolder (`py-project-init`)

Ein modernes, grafisches Werkzeug (PySide6 / Qt) zur schnellen und konsistenten Initialisierung neuer Programmierprojekte auf Basis flexibler Jinja2-Vorlagen.

---

## 🚀 Funktionen

- **Moderne Qt-Oberfläche (Dark Mode):** Elegantes dunkles Design mit Statusanzeigen, Echtzeit-Validierung und interaktiven Hilfetexten in einer responsiven Scroll-Ansicht.
- **Vollbild- & Fenstermodus:** Nahtloses Umschalten zwischen Standard- und Vollbildansicht jederzeit per Menü (**Ansicht → Vollbildmodus**) oder Taste `F11`.
- **Interaktive Live-Vorschau (Virtuelles Rendern):**
  - Prüft vor dem Schreiben auf die Festplatte den kompletten virtuellen Dateibaum und gerenderte Dateiinhalte.
  - Aufrufbar per Button **👁 Live-Vorschau**, Tastaturkürzel `Strg + P` oder über das Menü **Werkzeuge**.
- **IDE- & Quickstart-Launcher:**
  - Nach erfolgreicher Projekterstellung stehen 1-Klick-Buttons zur Verfügung:
    - **💻 VS Code:** Öffnet das Projekt direkt in Visual Studio Code (`code <zielordner>`).
    - **⚡ Cursor:** Öffnet das Projekt im AI-Editor Cursor (`cursor <zielordner>`).
    - **🖥 Terminal:** Öffnet ein Terminalfenster direkt im Projektordner (Windows Terminal, PowerShell oder Shell).
    - **📂 Explorer:** Öffnet den Zielordner im nativen Dateimanager.
- **Retrofit-Modus für bestehende Repositories:**
  - Bestehende Codebasen können nachträglich mit den standardisierten Git-Hooks und Agent-Konfigurationen ausgestattet werden.
  - Über das Menü **Werkzeuge → Bestehendes Projekt nachrüsten...**.
- **Vorlagen-Ersteller (Template Creator):**
  - Erstellt aus einem bestehenden Projektordner automatisch eine neue, wiederverwendbare Jinja2-Vorlage mit generierter `template.yaml`.
  - Über das Menü **Vorlagen → Neue Vorlage aus bestehendem Projekt erstellen...**.
- **GitLab-Anbindung (optional, auch für selbstgehostete Instanzen):**
  - Legt das Projekt per API auf GitLab an – **inklusive README**, damit GitLab den Default-Branch (`main`) selbst erzeugt. So scheitert der erste Push nicht mehr an „A default branch does not yet exist“, auch nicht mit Developer-Rechten.
  - Der initiale Commit wird lokal auf `origin/main` aufgesetzt, auf den Arbeits-Branch (Standard: `develop`) gepusht und per Merge Request in `main` eingebracht.
  - Ist das Projekt auf GitLab schon vorhanden und leer, werden Default- und Arbeits-Branch direkt gepusht (dafür sind Maintainer-Rechte nötig). Projekte, die schon Commits enthalten, werden nicht angefasst.
  - Das Access Token (Scope `api`) liegt im Windows-Anmeldeinformationsspeicher (`keyring`), nie in den Einstellungen. Alternativ wird `GITLAB_TOKEN` gelesen.
  - Neue Repositories werden mit `git init -b <Default-Branch>` (Standard: `main`) angelegt.
- **Headless CLI-Modus:**
  - Vollständige Steuerung über die Kommandozeile für Scripting und CI/CD ohne GUI-Zwang.
- **System-Tool-Prüfung:** Live-Erkennung verfügbarer CLI-Werkzeuge (`git`, `uv`, `cargo`, `npm`, `go`, `dotnet`) im System-PATH.
- **Echtzeit-Validierung:** Sofortige Prüfung des Projektnamens auf Konventionen (nur Buchstaben, Ziffern, `-` und `_`, muss mit einem Buchstaben beginnen).
- **Optimierte Pipeline (`uv init` → `uv venv` → `git init`):**
  - Deklarative `pre_init`-Hooks in `template.yaml` (z. B. automatisches `uv init` und `uv venv`).
  - Beibehaltung der durch `uv init` erzeugten `.gitignore` kombiniert mit Template-spezifischen Ignore-Einträgen.
  - Sauberes Überschreiben von Dummy-Dateien durch die Jinja2-Vorlagen.
- **Modulare Git-Hooks Integration (8 clientseitige Hooks):**
  - Feingranulare Auswahl in der UI für verfügbare Hooks aus dem Ordner `hooks/`:
    - **`pre-commit` (Secret-, Size- & Meta-Scanner):** Blockiert versehentlich gestagte Secrets (`.env`, Private Keys), Dateien >10MB und prüft Unity `.meta`-Dateien-Integrität.
    - **`commit-msg` (Conventional Commits Linter):** Erzwingt standardisierte Commit-Nachrichten (`feat:`, `fix:`, `chore:`, `docs:`, etc.) mit Mindestlänge.
    - **`prepare-commit-msg` (Ticket-ID aus Branch):** Liest Ticket-Schlüssel aus Branch-Namen (z. B. `feature/PROJ-123` → `[PROJ-123]`) und stellt sie der Commit-Nachricht voran.
    - **`post-commit` (SemVer-Bump & Changelog-Generator):** Fragt nach SemVer-Bumps (Python, Node, Rust, Unity), pflegt `CHANGELOG.md` per Amend und setzt Git-Tags.
    - **`post-checkout` (Dependency-Sync & Branch-Check):** Führt `uv sync` oder `npm install` aus, meldet geänderte Unity Packages (`manifest.json`) und warnt vor direkter Arbeit auf `main`.
    - **`post-merge` (Lockfile-Sync & .env-Vergleich):** Synchronisiert Abhängigkeiten nach Merges/Pulls, meldet Unity Package-Updates und warnt vor fehlenden Variablen aus `.env.example`.
    - **`pre-rebase` (Historien-Schutz):** Blockiert versehentliches Rebasen der Haupt-Branches (`main`/`master`).
    - **`pre-push` (Branch-Schutz & Test-Gate):** Blockiert direkte Pushes auf `main`/`master` und führt vor dem Push die Test-Suite aus (pytest, cargo, vitest, dotnet, unity).
  - Automatischer initialer Commit während der Generierung via `--no-verify`.
- **Agenten-Regeln & Skills (.agents/):**
  - Modulare Bibliothek unter `assets/agent_configs/` für Coding-Assistenten.
  - Automatische, sprach- und vorlagenspezifische Empfehlungen für Regeln und Skills (z. B. `unity_csharp_standards` und `unity-meta-checker`).
  - Individuelle An- und Abwahl in der Benutzeroberfläche.
  - Generiert `.agents/rules/`, `.agents/skills/` sowie eine strukturierte `AGENTS.md` im Projektstamm.
- **Erweiterte Metadaten & Benutzerdefinierte Skripte:**
  - Autorenangaben (Name, E-Mail), Lizenzauswahl (MIT, Apache-2.0, GPL-3.0, etc.).
  - Konfigurierbare Skript-Tabelle (z. B. `format = ruff format .`), die direkt in `pyproject.toml` oder `package.json` geschrieben wird.
  - Dauerhafte Speicherung über `QSettings`.
- **Asynchrone Generierung mit Abbruch:** Hintergrund-Ausführung im separaten Thread; kann jederzeit über den **✖ Abbrechen**-Button sicher gestoppt werden.

---

## 📦 Enthaltene Vorlagen

| Vorlage | Sprache / Ökosystem | Enthaltene Features & Optionen |
| :--- | :--- | :--- |
| **Python CLI** | Python (uv / pyproject.toml) | `uv init` + `uv venv` Pipeline, modulares Paket, Tests mit pytest, Ruff, optionale GitHub Actions CI & Dockerfile |
| **Python FastAPI** | Python (FastAPI, uv) | `uv init` + `uv venv` Pipeline, REST API mit Pydantic, Healthchecks, optionale GitHub Actions CI & Dockerfile |
| **Python GUI** | Python (Desktop GUI) | `uv init` + `uv venv` Pipeline, GUI-Framework (**PySide6**, **PyQt6**, **Tkinter**, **wxPython**, **Kivy**) mit vergleichender Entscheidungshilfe |
| **Python Game** | Python (Pygame-ce / Arcade) | `uv init` + `uv venv` Pipeline, Game-Engine (**Pygame-ce** oder **Arcade**), strukturierte Asset-Ordner (`assets/audio`, `assets/sprites`), Fenster- & Vollbildmodus (`F11`), optionale GitHub Actions CI & PyInstaller Build-Workflow |
| **Python TUI** | Python (Textual & Rich) | `uv init` + `uv venv` Pipeline, Terminal-UI mit Textual/Rich, responsive Layouts, Widgets, Theme-Toggle, optionale GitHub Actions CI |
| **Web Frontend** | Web (Vite / TypeScript) | Schneller Vite-Stack, Multi-Framework (**React 19**, **Vue 3**, **Svelte 5**), Vitest Unit-Tests, optionale GitHub Actions CI & Nginx Multi-Stage Dockerfile |
| **Web Fullstack** | Python + Web (FastAPI & Vite) | Sauberes Monorepo mit FastAPI Backend (`api/`) und modernem Vite React Frontend (`frontend/`), Vitest & Pytest, Docker Compose Setup |
| **Rust CLI** | Rust (Cargo) | Projektstruktur mit Cargo.toml, Tests, optionaler GitHub Actions Workflow |
| **Rust GUI** | Rust (Desktop GUI) | Auswahl des GUI-Frameworks (**egui / eframe**, **Iced**, **Tauri**, **Slint**, **GTK4**) mit detaillierten Tooltips |
| **Go Anwendung** | Go (Go 1.23+) | Go Modules (`go.mod`), Architekturtyp (**CLI-Tool** mit Flags oder **REST API Service** mit `go-chi/chi`), Unit-Tests, optionale GitHub Actions CI & Multi-Stage Distroless Dockerfile |
| **.NET C# Anwendung** | C# (.NET 8 / 9) | Moderner .NET-Stack, Projekttyp (**Web API / Minimal API**, **CLI-Konsole** oder **Avalonia XAML Desktop UI** mit Vollbildmodus), xUnit-Tests, optionale GitHub Actions CI & Multi-Stage Dockerfile |
| **Unity C# Game** | C# (Unity Engine) | Saubere Projektstruktur, Unity 6 (LTS) oder 2022.3 LTS, URP oder Built-in, 2D/3D, GameManager, Fenster- & Vollbildmodus (`F11`), Input System, EditMode/PlayMode Tests, Git LFS & `.meta`-Prüfung, optionale GitHub Actions CI |
| **Node/TypeScript** | TypeScript (npm / Node.js) | Modernes TS-Setup, Vitest, optionale GitHub Actions CI & Dockerfile |

---

## 🛠 Voraussetzungen

- **Python:** Version `>= 3.14`
- **Paketmanager:** [uv](https://docs.astral.sh/uv/) (empfohlen) oder `pip`
- **Versionsverwaltung:** `git` (für automatische Repository-Initialisierung)

---

## 📥 Installation & Start

### 1. Repository klonen

```bash
git clone https://github.com/DaniBani/py-project-init.git
cd py-project-init
```

### 2. Abhängigkeiten synchronisieren

Mit `uv`:

```bash
uv sync
```

### 3. Anwendung starten (GUI oder CLI)

**Grafische Oberfläche starten:**

```bash
uv run py-project-init
# oder explizit:
uv run py-project-init --gui
```

**Headless CLI-Modus (Kommandozeile):**

```bash
# Verfügbare Vorlagen auflisten
uv run py-project-init --list

# Virtuelle Vorschau generieren (ohne Dateien zu schreiben)
uv run py-project-init mein-projekt -t python-cli --preview

# Projekt direkt via CLI initialisieren
uv run py-project-init mein-service -t python-fastapi -p /pfad/zu/projekten

# Projekt direkt auf GitLab anlegen (Token aus Windows-Tresor oder $env:GITLAB_TOKEN)
uv run py-project-init cloud-net -t python-fastapi --gitlab-url https://gitlab.data-al.de --gitlab-namespace development

# Projekt mit Autor und Lizenz initialisieren
uv run py-project-init my-tool -t rust-cli --author "Max Mustermann" --email "max@example.com" --license MIT
```

---

## 📁 Struktur einer Vorlage

Jede Vorlage liegt in einem Unterordner von `templates/` (oder einem benutzerdefinierten Vorlagen-Ordner) und besitzt eine `template.yaml`:

```text
templates/
└── meine-vorlage/
    ├── template.yaml         # Metadaten, Optionen, Hooks & Bedingungen
    ├── README.md.j2          # Jinja2-Template
    └── src/
        └── main.py.j2
```

### Beispiel `template.yaml`

```yaml
name: Meine Vorlage
language: Python
description: Eine kurze Beschreibung der Vorlage für die Benutzeroberfläche.

options:
  - id: gui_framework
    label: GUI Framework
    type: select
    default: pyside6
    choices:
      - value: pyside6
        label: PySide6 (Qt)
        description: Offizielles Qt-Binding für moderne Desktop-Anwendungen.
  - id: github_actions
    label: GitHub Actions CI hinzufügen
    type: bool
    default: true

file_conditions:
  - pattern: ".github/"
    when: "github_actions"

hooks:
  pre_init:
    - ["uv", "init"]
    - ["uv", "venv"]
  post_create:
    - ["uv", "sync"]
```

---

## 🖥️ Tastenkombinationen

| Tastenkombination | Aktion |
| :--- | :--- |
| **F11** | Vollbildmodus umschalten (Vollbild ↔ Fenstermodus) |
| **Strg + P** | Virtuelle Live-Vorschau öffnen |
| **Strg + O** | Basis-Zielordner auswählen |
| **Strg + R** | Vorlagen & Assets neu einlesen |
| **Strg + L** | Protokollfenster (Log) leeren |
| **Strg + Q** | Anwendung beenden |

---

## 🔨 Eigenständige EXE erstellen (PyInstaller)

Das Projekt enthält eine vorgefertigte Konfigurationsdatei `ProjectScaffolder.spec`:

```bash
uv run pyinstaller ProjectScaffolder.spec
```

Die fertige ausführbare Datei befindet sich anschließend im Verzeichnis `dist/`.

---

## 📄 Lizenz

Dieses Projekt ist lizenziert unter der MIT-Lizenz.
