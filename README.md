# Project Scaffolder (`py-project-init`)

Ein modernes, grafisches Werkzeug (PySide6 / Qt) zur schnellen und konsistenten Initialisierung neuer Programmierprojekte auf Basis flexibler Jinja2-Vorlagen.

---

## 🚀 Funktionen

- **Moderne Qt-Oberfläche (Dark Mode):** Elegantes dunkles Design mit Statusanzeigen, Echtzeit-Validierung und interaktiven Hilfetexten.
- **Vollbild- & Fenstermodus:** Nahtloses Umschalten zwischen Standard- und Vollbildansicht jederzeit per Menü (**Ansicht → Vollbildmodus**) oder Taste `F11`.
- **System-Tool-Prüfung:** Live-Erkennung verfügbarer CLI-Werkzeuge (`git`, `uv`, `cargo`, `npm`) im System-PATH.
- **Echtzeit-Validierung:** Sofortige Prüfung des Projektnamens auf Konventionen (nur Buchstaben, Ziffern, `-` und `_`, muss mit einem Buchstaben beginnen).
- **Dynamische Vorlagen-Optionen:**
  - Checkboxen (z. B. GitHub Actions CI, Dockerfile-Support)
  - Dropdown-Auswahl mit Tooltips und verständlichen Erklärungen für fundierte Architekturentscheidungen (z. B. GUI-Framework-Auswahl).
- **Asynchrone Generierung mit Abbruch:** Hintergrund-Ausführung im separaten Thread; kann jederzeit über den **✖ Abbrechen**-Button sicher gestoppt werden.
- **Post-Hooks & Git-Setup:** Automatische Ausführung von Initialisierungs-Hooks (z. B. `uv sync`, `cargo check`) sowie automatischer initialer Git-Commit.
- **Direktzugriff:** Nach erfolgreicher Erstellung kann der Zielordner mit einem Klick im System-Dateimanager (Windows Explorer, macOS Finder, Linux Dateimanager) geöffnet werden.
- **Erweiterbare Vorlagenverwaltung:**
  - Schnell-Reload (`Strg+R` oder **🔄 Neu laden**) ohne Anwendungsneustart
  - Standard-Vorlagenordner direkt per Button im Explorer öffnen
  - Eigene, benutzerdefinierte Vorlagenordner hinzufügen und dauerhaft registrieren
- **Persistente Einstellungen (`QSettings`):** Letzter Speicherpfad, gewählte Vorlage sowie Fensterposition und -größe bleiben zwischen Sitzungen erhalten.

---

## 📦 Enthaltene Vorlagen

| Vorlage | Sprache / Ökosystem | Enthaltene Features & Optionen |
| :--- | :--- | :--- |
| **Python CLI** | Python (uv / pyproject.toml) | Modulares Paket, Einstiegspunkte, Tests mit pytest, optionale GitHub Actions CI & Dockerfile |
| **Python FastAPI** | Python (FastAPI, uv) | REST API mit Pydantic, Healthchecks, optionale GitHub Actions CI & Dockerfile |
| **Python GUI** | Python (Desktop GUI) | Auswahl des GUI-Frameworks (**PySide6**, **PyQt6**, **Tkinter**, **wxPython**, **Kivy**) mit vergleichender Entscheidungshilfe |
| **Rust CLI** | Rust (Cargo) | Projektstruktur mit Cargo.toml, Tests, optionaler GitHub Actions Workflow |
| **Rust GUI** | Rust (Desktop GUI) | Auswahl des GUI-Frameworks (**egui / eframe**, **Iced**, **Tauri**, **Slint**, **GTK4**) mit detaillierten Tooltips |
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

### 3. Anwendung starten

Über den Skript-Einstiegspunkt:

```bash
uv run py-project-init
```

Oder direkt als Python-Modul:

```bash
uv run python -m py_project_init
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
      - value: tkinter
        label: Tkinter
        description: Einfach, im Standardumfang von Python enthalten.
  - id: github_actions
    label: GitHub Actions CI hinzufügen
    type: bool
    default: true

file_conditions:
  - pattern: ".github/"
    when: "github_actions"

hooks:
  post_create:
    - ["uv", "sync"]
```

---

## 🖥️ Tastenkombinationen

| Tastenkombination | Aktion |
| :--- | :--- |
| **F11** | Vollbildmodus umschalten (Vollbild ↔ Fenstermodus) |
| **Strg + O** | Basis-Zielordner auswählen |
| **Strg + R** | Vorlagen neu einlesen |
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
