# Rust & Cargo Richtlinien

1. **Code-Qualität**:
   - `cargo clippy` muss ohne Warnungen durchlaufen.
   - Code mit `cargo fmt` formatieren.

2. **Fehlerbehandlung**:
   - Verwende `thiserror` für Library-Fehler und `anyhow` für App-Fehler.
   - Vermeide `unwrap()` in Produktionspfaden; nutze `?`, `unwrap_or_default()` oder explizites Pattern Matching.
