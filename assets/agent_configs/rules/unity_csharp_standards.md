# Unity & C# Game Development Richtlinien

1. **Architektur & MonoBehaviour-Entkopplung**:
   - Trenne reine Spiellogik (Plain C# Classes, Services, Models, State Machines) strikt von `MonoBehaviour`-Klassen und Unity-spezifischem Rendering/Physik.
   - Nutze Assembly Definitions (`.asmdef`), um Kompilierzeiten drastisch zu reduzieren, zirkuläre Abhängigkeiten zu verhindern und modulare Test-Assemblies zu ermöglichen.
   - Verwende Dependency Injection oder ein Service-Locator-Muster anstelle harter Singletons mit `FindObjectOfType()`.

2. **Performance & Garbage Collection (GC)**:
   - Vermeide Speicherallokationen (`new`, String-Verkettungen, LINQ) in `Update()`, `FixedUpdate()` und `LateUpdate()`.
   - Cache alle Komponenten-Referenzen (`GetComponent<T>()`) in `Awake()` oder `Start()`.
   - Nutze `NonAlloc`-Varianten bei Physik-Abfragen (z. B. `Physics.RaycastNonAlloc`, `Physics2D.OverlapCircleNonAlloc`) und Objekt-Pooling für häufig instanziierte Entitäten (Projektile, Effekte).

3. **Fenster- und Vollbildmodus (Global Requirement)**:
   - Spiele müssen sowohl im resizable Fenstermodus als auch im Vollbildmodus (Taste `F11` oder `Alt+Enter`) nahtlos funktionieren.
   - Stelle sicher, dass bei Auflösungs- und Vollbildwechseln das Seitenverhältnis (Aspect Ratio) nicht verzerrt wird (mittels sauberem Canvas-Scaler / Pillarboxing oder dynamischer Kameraanpassung).
   - Implementiere eine zentrale Steuerungsklasse (z. B. `ScreenModeController`), welche Auflösung und Bildschirmmodus verwaltet und persistiert.

4. **Integrität von .meta-Dateien**:
   - Jede Datei und jeder Ordner unter `Assets/` und `Packages/` muss zwingend eine gültige, korrespondierende `.meta`-Datei im Git-Repository besitzen.
   - Benenne oder lösche Dateien niemals außerhalb von Unity oder ohne gleichzeitiges Anpassen/Entfernen der zugehörigen `.meta`-Datei, um verlorene Referenzen und GUID-Konflikte zu vermeiden.

5. **Asynchronität, Coroutinen & Game-Loop**:
   - Verwende Coroutinen oder moderne `async`/`await`-Muster (z. B. UniTask) für zeitverzögerte Abläufe, Tweens und asynchrones Asset-Laden.
   - Führe physikalische Berechnungen ausschließlich in `FixedUpdate()` mit `Time.fixedDeltaTime` aus; Rendering- und Input-Logik gehört in `Update()` mit `Time.deltaTime`.

6. **Testing & Code-Qualität**:
   - Strukturiere Tests in `EditMode` (schnelle Unit-Tests ohne Playmode-Overhead) und `PlayMode` (Integrationstests mit Game-Loop und Physik).
   - Verwende das Unity Test Framework (NUnit) zur automatisierten Absicherung kritischer Spiellogik.
