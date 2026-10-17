# Ideation: Erweiterung der Projektvorlagen (Project Templates Expansion)

## Problem Statement

Wie können wir `py-project-init` über Standard-Python- und Rust-Basisprojekte hinaus so erweitern, dass Entwickler für Games, moderne Web-Frontends, Fullstack-Anwendungen, Go-Services, Terminal-UIs und .NET-Apps sofort produktionsreife, standardisierte und AI-agentenfähige Projektgerüste mit einem Klick generieren können?

---

## Evaluierte Richtungen & Konvergenz

### Richtung 1: Python-Spezialisierungen (Game & TUI) – *Höchste Hebelwirkung*

- **Templates:**
  - `python-game`: Multi-Framework (Pygame-ce als empfohlener Standard, Python Arcade als moderne OpenGL-Alternative) mit standardisierter Asset-Ordnerstruktur (`assets/audio`, `assets/sprites`), Game-Loop, Konfiguration und Tests.
  - `python-tui`: Terminal-Anwendungen mit [Textual](https://textual.textualize.io/) & Rich für Dashboards, Dev-Tools und interaktive CLIs im Terminal.
- **Mehrwert:** Extrem hoch. Schließt die Lücke zwischen einfachen CLI-Skripten und vollwertigen interaktiven Python-Anwendungen (direkter Bezug zu bestehenden Gaming- und Tool-Workflows).
- **Tooling:** `uv`, `pytest`, `ruff`, automatische Virtualenv-Initialisierung.

### Richtung 2: Modernes Web & Fullstack – *Modernisierung des Ökosystems*

- **Templates:**
  - `web-frontend`: Multi-Framework Vite-Setup (React 19 / Vue 3 / Svelte 5) mit TypeScript, Tailwind CSS / modernem CSS, Vitest und ESLint/Prettier.
  - `web-fullstack`: FastAPI Backend (`backend/`) + Vite/React TypeScript Frontend (`frontend/`) im sauberen Monorepo-Layout mit Docker Compose Orchestrierung.
- **Mehrwert:** Ersetzt das bisherige, rein serverseitige `node-ts` bzw. das reine API-Template `python-fastapi` durch vollständige End-to-End Applikations-Setups.
- **Tooling:** `npm` / `node`, `uv`, Vitest, Pytest, Docker Compose.

### Richtung 3: Polyglot-Ökosystem (Go & .NET) – *Erweiterung der Sprachpalette*

- **Templates:**
  - `go-app`: Go 1.23+ mit Auswahl zwischen CLI (Cobra / Standard-Flag) und Web-Service (Chi / net/http), inklusive `go.mod`, GitHub Actions CI und Dockerfile.
  - `dotnet-app`: .NET 8/9 C# mit Auswahl zwischen Web API (Minimal APIs), Console CLI und Cross-Platform GUI (Avalonia UI), inklusive xUnit-Testprojekt und Solution-Datei (`.sln`).
- **Mehrwert:** Etabliert `py-project-init` als universellen polyglotten Projekt-Scaffolder.
- **Tooling:** `go mod tidy`, `dotnet restore` / `dotnet new` Muster.

---

## Kernannahmen & Risiken (Stress-Testing)

1. **Externe Toolchains:**
   - *Annahme:* Benutzer haben `go`, `dotnet` oder `node` installiert, wenn sie entsprechende Vorlagen wählen.
   - *Absicherung:* Generator darf nicht hart abstürzen, falls z. B. `dotnet` oder `go` auf dem Zielsystem im Pfad fehlt. Die Post-Create Hooks müssen fehlschlagende Kommandos als Warnung melden, ohne das Dateiscaffolding abzubrechen (bereits robust implementiert im `generator.py`).
2. **Template-Wartbarkeit:**
   - *Annahme:* Multi-Framework-Templates (wie `python-gui` und `rust-gui`) bieten die beste Balance aus Übersichtlichkeit im Dropdown und Anpassbarkeit.
   - *Validierung:* Die Jinja2-Bedingungen (`{% if framework == 'pygame' %}`) sind gut lesbar und verhindern eine Explosion an separaten Vorlagenordnern.
3. **Agent-Kompatibilität:**
   - *Annahme:* Jede neue Sprache/Kategorie benötigt passende `.agents/rules/` und `.agents/skills/`.
   - *Validierung:* Manifest `assets/agent_configs/manifest.yaml` muss um Standards für Go, .NET, Web-Frontend und Game-Dev ergänzt werden.

---

## MVP-Scope (Phasierte Bereitstellung)

### Phase 1 (MVP)

1. **`python-game`**: Multi-Framework Vorlage (Pygame-ce & Arcade) mit Game-Loop, Asset-Pipeline, Tests und CI.
2. **`python-tui`**: Modernes Textual TUI-Projekt mit Widgets, Screens und Keybindings.
3. **`web-frontend`**: Vite + TypeScript Multi-Framework (React, Vue, Svelte) mit Vitest & CI.
4. **Integration in Generator & UI**: Empfohlene Skripte (`_get_recommended_scripts`), Framework-Dropdown-Handling, Test-Abdeckung.

### Phase 2

1. **`web-fullstack`**: Monorepo mit FastAPI + React/Vite und Docker Compose.
2. **`go-app`**: Go CLI / Microservice mit Modulen und Tests.
3. **`dotnet-app`**: .NET 8/9 C# Projekt (Console, Web API, Avalonia).
4. **Agent-Manifest Erweiterung**: C#, Go, Frontend & Game Guidelines in `assets/agent_configs/`.

---

## Not Doing (Bewusste Nicht-Ziele & Begründungen)

- **Keine Legacy-Templates:** Kein Webpack, kein jQuery, kein .NET Framework <= 4.8. Wir unterstützen ausschließlich moderne Stacks (Vite, .NET 8+, Go 1.23+, uv).
- **Keine Cloud-Infrastruktur-Monolithen:** Keine Terraform/Pulumi/Kubernetes-Vorlagen im Basis-Scaffolding; Fokus liegt auf Anwendungs-Code und Entwicklungs-Workflows.
- **Keine proprietären kostenpflichtigen Frameworks:** Fokus auf offene, frei lizenzierte Open-Source-Frameworks.

---

## Offene Fragen

1. Sollen bei `web-frontend` Paketmanager-Optionen wählbar sein (npm vs pnpm vs bun) oder standardmäßig auf `npm` gesetzt werden?
2. Bevorzugst du bei .NET standardmäßig C# mit Top-Level Statements oder klassische `Program`-Klassenstruktur?
