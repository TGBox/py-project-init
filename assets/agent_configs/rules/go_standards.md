# Go & Modul-Standards

1. **Fehlerbehandlung (Error Handling)**:
   - Fehler sind explizite Rückgabewerte: Prüfe Fehler immer unmittelbar (`if err != nil`).
   - Reiche Fehler mit Kontext an (z. B. `fmt.Errorf("konnte Datei nicht öffnen: %w", err)`).
   - Vermeide `panic()`, außer bei nicht behebbaren Programmierfehlern während der Initialisierung.

2. **Paketstruktur & Interfaces**:
   - Halte Pakete klein und fokussiert (z. B. `cmd/`, `internal/`, `pkg/`).
   - Definiere Interfaces dort, wo sie konsumiert werden, nicht dort, wo sie implementiert werden ("accept interfaces, return structs").

3. **Concurrency & Ressourcen**:
   - Starte Goroutinen nur, wenn deren Lebenszyklus und Abbruchbedingung (z. B. via `context.Context`) klar definiert sind.
   - Schließe Ressourcen (`io.Closer`, `net.Conn`, `os.File`) zuverlässig mit `defer`.

4. **Code-Qualität**:
   - Formatiere Code standardmäßig mit `go fmt`.
   - Halte den Linter `golangci-lint` sauber.
