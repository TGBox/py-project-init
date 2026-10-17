# Web Frontend & Modern UI Best Practices

1. **Komponenten & Modularisierung**:
   - Zerlege Benutzeroberflächen in kleine, fokussierte und wiederverwendbare Komponenten.
   - Trenne Präsentation und UI-Logik von Datenabfragen und globalem State.

2. **Styling & Ästhetik**:
   - Verwende kuratierte, harmonische Farbpaletten (HSL / CSS Variables) und moderne Typografie (z. B. Inter, Roboto).
   - Gestalte responsiv für Desktop, Tablet und Mobile (`min-height: 100vh`, Grid/Flexbox).
   - Implementiere saubere Micro-Animations und Hover-Effekte für ein lebendiges Benutzererlebnis.

3. **Barrierefreiheit (a11y) & Semantik**:
   - Verwende semantische HTML5-Elemente (`<header>`, `<main>`, `<nav>`, `<button>`).
   - Stelle ausreichende Kontraste, sichtbare Focus-States und Tastaturbedienbarkeit sicher.

4. **Testing & Performance**:
   - Schreibe isolierte Komponententests mit Vitest und Testing Library.
   - Vermeide unnötige Re-Renders und optimiere Asset-Größen.
