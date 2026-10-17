# C# & .NET Best Practices

1. **Typsicherheit & Nullable Reference Types**:
   - Aktiviere `<Nullable>enable</Nullable>` in allen Projekten und behandle Compiler-Warnungen bzgl. Nullability explizit.
   - Nutze moderne C#-Features wie Pattern Matching, Records für unveränderliche Daten und Primary Constructors.

2. **Asynchronität (Async/Await)**:
   - Führe alle I/O-Operationen asynchron mit `async`/`await` aus.
   - Reiche `CancellationToken` konsequent durch asynchrone Aufrufketten weiter.
   - Verwende niemals `.Result` oder `.Wait()`, um Deadlocks im Synchronisationskontext zu vermeiden.

3. **Architektur & Dependency Injection**:
   - Nutze das eingebaute `Microsoft.Extensions.DependencyInjection` zur sauberen Entkopplung von Services und Repositories.
   - Halte Controllers bzw. Minimal API Endpoints schlank und delegiere Geschäftslogik an Service-Klassen.

4. **Testing**:
   - Schreibe isolierte Unittests mit xUnit und FluentAssertions oder Standard-Asserts.
   - Mocke externe Abhängigkeiten über Interfaces.
