# Feingranulare Push-Pipeline & Automatisierungs-Optionen

## Problem Statement

Wie können wir Entwicklern beim Initialisieren und Nachrüsten von Projekten die volle, feingranulare Kontrolle über ihren Pre-Push-Lifecycle geben – sodass Tests, automatische Tag-Aktualisierungen auf HEAD, Exe-Builds und Artefakt-Verteilungen in externe Repositories zuverlässig, strikt und rein lokal ausgeführt werden?

---

## Empfohlene Architektur & Richtung

### 1. Reine lokale Ausführung via Git-Hooks (`hooks/pre-push` & `hooks/post-commit`)

- **Keine Cloud- oder CI-Abhängigkeiten**: Die gesamte Pipeline läuft lokal direkt auf dem Rechner des Entwicklers beim Ausführen von `git push`.
- **Zustands- & Konfigurationsspeicherung via `git config`**:
  - `hooks.smarttests`: Smarter Testfilter (nur bei Code-Änderungen).
  - `hooks.testcmd`: Optionaler benutzerdefinierter Testbefehl (Standard: Auto-Detect).
  - `hooks.renewtagonpush`: Wenn `true`, wird vor/bei dem Push geprüft, ob neue Commits seit dem letzten Versions-Tag vorliegen oder HEAD ungetaggt ist. Falls ja, wird der aktuelle Versions-Tag (z. B. `v1.2.3`) per `git tag -f` auf `HEAD` gesetzt und über `git push origin <tag>` mitübertragen.
  - `hooks.buildexe`: Automatischen Exe-Build vor dem Push aktivieren/deaktivieren.
  - `hooks.buildcmd`: Individueller Build-Befehl (z. B. `uv run pyinstaller ProjectScaffolder.spec`). Bleibt das Feld leer, greift die templatebasierte Auto-Erkennung (PyInstaller `.spec`/`main.py`, `cargo build --release`, `dotnet publish`, etc.).
  - `hooks.artifactpattern`: Pfad bzw. Glob zum gebauten Artefakt (Standard: `dist/*.exe`).
  - `hooks.deployartifact`: Artefakt-Deployment ins externe Repo an/aus.
  - `hooks.externalrepo`: URL oder lokaler Pfad des externen Ziel-Repositories.
  - `hooks.externalrepobranch`: Ziel-Branch im externen Repo (Standard: `main`).
  - `hooks.externalrepodir`: Ziel-Unterordner im externen Repo (z. B. `releases/`).

### 2. Strikte Pipeline-Fehlerbehandlung (Fail-Fast)

- **Zero Tolerance**: Schlägt die Testsuite fehl, bricht der Exe-Build mit Fehler ab oder schlägt das Pushen ins externe Artefakt-Repo fehl (z. B. Netzwerk- oder Berechtigungsfehler), wird der `git push` des Hauptprojekts **sofort mit `exit 1` abgebrochen**.
- Dadurch wird garantiert, dass niemals fehlerhafter Code, ungetestete Commits oder nicht-auslieferbare Stände ins Remote-Repository gelangen.

### 3. Technischer Ablauf des Artefakt-Deployments in das externe Repository

- Der Pre-Push-Hook prüft, ob die gebaute Datei im konfigurierten Artefakt-Pfad (z. B. `dist/`) existiert.
- Klonen / Cachen des externen Ziel-Repos in ein temporäres Verzeichnis (bzw. Wiederverwendung eines lokalen Pfads).
- Kopieren des Artefakts in den Ziel-Unterordner, Erstellen eines automatisierten Commits mit aktuellem Quell-Commit-Hash und Tag des Hauptprojekts (`Release vX.Y.Z (source: abc1234)`).
- Pushen des Ziel-Branches in das externe Repository.

### 4. UI-Integration: Einklappbare Detail-Sektion

- **In Hauptansicht (Tab 2: `🌐 Git-Remote, Git-Hooks & Agenten`)** und im **Nachrüsten-Dialog (`RetrofitDialog`)**:
  - Direkt unter den Hook-Checkboxen wird ein einklappbarer Bereich platziert:  
    `▼ Erweiterte Push-Pipeline- & Automatisierungs-Optionen`
  - Strukturierte Optionen mit Checkboxen, erklärenden Tooltips und bedingt aktivierten Eingabefeldern:
    1. **Pre-Push Test-Gate**: Tests vor Push erzwingen, Smarte Testausführung, benutzerdefinierter Testbefehl.
    2. **Versions-Tagging**: Tag bei Push immer auf `HEAD` erneuern & mitpushen (`hooks.renewtagonpush`).
    3. **Exe-Build vor Push**: Checkbox + optionales Freitextfeld für `Build-Befehl` (`hooks.buildcmd`, mit Platzhalter für Auto-Erkennung).
    4. **Externes Artefakt-Repository**: Checkbox + Eingabefelder für `Repo-URL / Pfad` (`hooks.externalrepo`), `Ziel-Branch` (`hooks.externalrepobranch`) und `Artefakt-Muster` (`hooks.artifactpattern`).

### 5. Volle CLI-Parität (`cli.py`)

- Neue Optionen sowohl für `py-project-init` (Neuanlage) als auch für `--retrofit-hooks`:
  - `--renew-tag-on-push`
  - `--build-exe` / `--build-cmd "..."`
  - `--deploy-artifact` / `--external-repo "..."` / `--external-repo-branch "..."` / `--artifact-pattern "..."`

---

## Zu validierende Kernannahmen

- [x] **Bash/POSIX-Kompatibilität unter Windows**: Die neuen Hooks müssen sowohl in Git Bash (Standard für Git unter Windows) als auch in POSIX-Umgebungen fehlerfrei durchlaufen.
- [x] **Push-Schleifen vermeiden**: Das Pushen von Tags oder Commits im externen Repo darf keine unendlichen Git-Hook-Trigger oder Deadlocks auslösen.
- [x] **Performance des Pre-Push-Hooks**: Wenn Tests und Exe-Build lokal vor jedem Push laufen, muss der Entwickler klares, farbiges Konsolen-Feedback mit Statusmeldungen erhalten.

---

## MVP Scope

### Was ist enthalten (In Scope)

- Aktualisierung von `hooks/pre-push` und `hooks/post-commit` um die neuen Konfigurationsflags (`hooks.renewtagonpush`, `hooks.buildexe`, `hooks.buildcmd`, `hooks.deployartifact`, etc.).
- Erweiterung von `generator.py` (`_install_git_hooks` und `retrofit_hooks`), um diese Konfigurationen bei Neuanlage und Nachrüstung in `git config` zu schreiben.
- Erweiterung der UI in Tab 2 (`main_window.py`) und im Nachrüst-Dialog (`RetrofitDialog` in `dialogs.py`) mit der einklappbaren Detail-Sektion.
- Erweiterung der CLI (`cli.py`) mit den entsprechenden Parametern.
- Unit-Tests in `tests/test_generator.py` und `tests/test_cli.py`.

### Nicht im Scope (Not Doing) & Begründung

- **Cloud-CI/CD-Generierung (GitHub Actions / GitLab CI)**: Der Fokus liegt zu 100 % auf lokalen Git-Hooks, um maximale Unabhängigkeit von externen CI-Servern und Plattformen zu wahren.
- **Interaktive GUI-Abfragen während des Pushes**: `git push` läuft im Terminal; alle Entscheidungen werden vorher per Konfiguration festgelegt, statt mitten im Push interaktive Popups aufpoppen zu lassen.
