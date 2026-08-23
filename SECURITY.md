# Security Policy / Sicherheitsrichtlinie

[English](#english) · [Deutsch](#deutsch)

---

<a name="english"></a>
## English

### Security Architecture & Principles

**Gardener OS** (`ellmos-ai/gardener`) is designed as a local-first, database-centric operating system for LLM memory with strict privacy, secret masking, and isolation boundaries:

1. **Local-First & Zero-Egress Memory Substrate**:
   - Gardener runs exclusively on local SQLite databases (`~/.gardener/user.db`, `~/.gardener/system.db`).
   - 100% Offline: zero outbound telemetry, no cloud synchronization, and no network transmission of indexed memories or queries.
2. **Secret Redaction & Token Masking**:
   - Automated regex masking in `sources.py` (`scan_for_secrets()`) inspects agent transcripts, markdown notes, and foreign tables before indexing.
   - API keys, OAuth tokens, bearer tokens, and private keys are masked and reported, preventing secret contamination in search indices.
3. **Read-Only External Observation & Source Isolation**:
   - External data sources (such as BACH knowledge bases, agent transcripts, and external markdown directories) are queried with read-only SQLite attachments (`mode=ro`) and read-only filesystem traversal.
   - Foreign sources can never mutate the primary knowledge substrates.
4. **Path Traversal & Materialization Sanitization**:
   - `materialize()` and `absorb()` sanitize target filenames, rejecting or stripping path traversal sequences (`../`, absolute roots), preventing directory escape.
5. **Unprivileged User-Mode (Non-Elevation)**:
   - Gardener operates entirely within standard user space without requiring administrative or root elevation.
6. **Standard Library Substrate**:
   - The core runtime uses Python standard library modules (`sqlite3`, `pathlib`, `hashlib`, `json`), minimizing supply chain attack surface.

### Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.4.x   | :white_check_mark: |
| < 0.4.0 | :x:                |

### Reporting a Vulnerability

If you discover a security issue or vulnerability in Gardener OS:

1. **Do not create a public GitHub issue.**
2. Report via **GitHub Private Vulnerability Reporting** at [github.com/ellmos-ai/gardener/security/advisories](https://github.com/ellmos-ai/gardener/security/advisories).
3. Or email the maintainers directly:
   - `security@ellmos.ai`
   - `support@lukasgeiger.com`
   - `lukas@open-bricks.org`

**Response SLA:** We acknowledge vulnerability reports within 48 hours and coordinate fixes prior to public disclosure.

---

<a name="deutsch"></a>
## Deutsch

### Sicherheitsarchitektur & Schutzprinzipien

**Gardener OS** (`ellmos-ai/gardener`) ist als lokales, datenbankzentriertes Betriebssystem für LLM-Gedächtnis mit klaren Datenschutz-, Maskierungs- und Isolationsgrenzen aufgebaut:

1. **Local-First- & Zero-Egress-Gedächtnissubstrat**:
   - Gardener arbeitet ausschließlich auf lokalen SQLite-Datenbanken (`~/.gardener/user.db`, `~/.gardener/system.db`).
   - 100% Offline: keinerlei Telemetrie, keine Cloud-Synchronisation und kein Netzwerkabfluss von indizierten Daten oder Suchanfragen.
2. **Geheimnisschutz & Token-Maskierung**:
   - Automatische Regex-Prüfung in `sources.py` (`scan_for_secrets()`) filtert Transkripte, Notizen und Tabellen vor der Indizierung.
   - API-Keys, Bearer-Tokens und private Schlüssel werden maskiert und gemeldet, um Kontaminationen des Volltextindexes zu verhindern.
3. **Schreibgeschützte Quellenbeobachtung & Isolation**:
   - Externe Quellen (wie BACH-Wissensdatenbanken, Agenten-Logs und Markdown-Verzeichnisse) werden strikt schreibgeschützt (`mode=ro`) angebunden.
   - Fremdquellen können das primäre Benutzersubstrat zu keinem Zeitpunkt verändern.
4. **Schutz vor Pfad-Traversal**:
   - `materialize()` und `absorb()` normalisieren und bereinigen Dateinamen; Pfadmanipulationen (`../`, absolute Wurzelpfade) werden neutralisiert, um Directory Escapes zu verhindern.
5. **Unprivilegierter Modus (Non-Elevation)**:
   - Gardener läuft vollständig im regulären Benutzerkontext ohne Administrator- oder Root-Rechte.
6. **Minimale Angriffsfläche durch Standardbibliothek**:
   - Der Kern basiert auf erprobten Modulen der Python-Standardbibliothek (`sqlite3`, `pathlib`, `hashlib`, `json`) ohne unsichere Binärabhängigkeiten.

### Unterstützte Versionen

| Version | Unterstützt        |
| ------- | ------------------ |
| 0.4.x   | :white_check_mark: |
| < 0.4.0 | :x:                |

### Sicherheitslücke melden

Wenn Sie eine Sicherheitslücke oder ein Datenschutzproblem in Gardener OS entdecken:

1. **Erstellen Sie bitte kein öffentliches GitHub-Issue.**
2. Nutzen Sie das **GitHub Private Vulnerability Reporting** unter [github.com/ellmos-ai/gardener/security/advisories](https://github.com/ellmos-ai/gardener/security/advisories).
3. Oder schreiben Sie direkt an die Maintainer:
   - `security@ellmos.ai`
   - `support@lukasgeiger.com`
   - `lukas@open-bricks.org`

**Reaktionszeit (SLA):** Wir bestätigen Meldungen innerhalb von 48 Stunden und koordinieren die Behebung vor der Veröffentlichung.
