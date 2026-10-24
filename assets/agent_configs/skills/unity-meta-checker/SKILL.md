---
name: unity-meta-checker
description: Prüft Unity-Projekte auf fehlende oder verwaiste .meta-Dateien, GUID-Integrität und Assembly-Definitionen.
---

# Unity Meta-File & Asset Checker Skill

Dieser Skill stellt die Integrität von Unity-Projekten für Git-Repositories und CI/CD sicher.

## Ablauf & Prüfschritte

1. **Dateistruktur unter `Assets/` und `Packages/` scannen**:
   - Durchlaufe alle Ordner und Dateien in `Assets/` und `Packages/`.
   - Ignoriere vom Gitignore ausgeschlossene Verzeichnisse (z. B. `Library/`, `Temp/`, `Logs/`, `Build/`).

2. **Fehlende .meta-Dateien identifizieren**:
   - Prüfe für jede Datei und jeden Unterordner, ob eine entsprechende `<Name>.meta`-Datei existiert.
   - Falls ein Asset ohne `.meta`-Datei gestagt oder committet wurde, melde dies sofort als kritischen Fehler, da Unity sonst beim Öffnen neue GUIDs generiert und Prefab-/Szenen-Referenzen brechen.

3. **Verwaiste (Dangling) .meta-Dateien finden**:
   - Prüfe für jede `.meta`-Datei, ob die zugrundeliegende Datei bzw. der Ordner noch existiert.
   - Wurde ein Asset gelöscht oder umbenannt, muss auch die alte `.meta`-Datei entfernt bzw. umbenannt werden.

4. **Assembly Definitionen (.asmdef) prüfen**:
   - Prüfe, ob Skripte in logische Module mit `.asmdef`-Dateien unterteilt sind.
   - Stelle sicher, dass Test-Ordner (`EditMode`, `PlayMode`) separate Test-Assemblies mit `UNITY_INCLUDE_TESTS` definieren.

5. **Lösungsmaßnahmen**:
   - Fehlende `.meta`-Dateien aus Git wiederherstellen (`git checkout`) oder über Unity im Editor generieren lassen.
   - Verwaiste `.meta`-Dateien löschen (`git rm`).
