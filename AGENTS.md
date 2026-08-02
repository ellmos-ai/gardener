# AGENTS.md — Multi-Agent Governance & Operations for Gardener

> **Modul:** `ellmos-ai/gardener`  
> **Kanonischer Quellpfad:** `C:\_Local_DEV\repos\gardener`  
> **Spiegel / Referenz:** `C:\Users\User\OneDrive\.TOPICS\.AI\.MODULES\.MEMORY\gardener`  
> **Zentrales Log- & Registrierungsverfahren:** `C:\Users\User\OneDrive\.SYNC\workstation\antigravity-automations-reference\`

---

## 1. Agenten-Rollen & Systemverbund

Zusammenarbeit im drei Musketiere Systemverbund:
- **Antigravity (Gemini):** High-level Orchestrierung, Berechtigungs- & Task-Kontrolle, Sidecar/Automations-Wartung, FTS5 & Transkript-Observierer.
- **Claude (Claude Code / Desktop):** Refactoring, tiefe Code-Analyse, Skill-Integration & Markdown-Hygiene.
- **Codex (OpenAI / CLI):** Schnelle Hilfsskripte, Standby-Wartung, Testfall-Erweiterung.

---

## 2. Berechtigungen & Automations-Standard

- **Permission Mode:** Default-Berechtigungen auf Projekt-Ebene bevorzugt (Turbo-Mode), damit Hintergrund-Automatisierungen ohne manuelle Nachfragen unterbrechungsfrei durchlaufen.
- **Verhaltensregeln:** Agenten nutzen hohe Rechte eigenverantwortlich, halten sich strikt an Guardrails & Hooks und führen nach Code-Änderungen stets Qualitäts-Gates (`pytest`) aus.

---

## 3. Letter Hooks & Sicherheitsprotokolle

1. **Bootloader Document Traversal (`HOOK-DOC-TRAVERSAL-01`):** Vor Arbeiten stets `AGENTS.md`, `CLAUDE.md`, `README.md`, `DESIGN.md` und `KONZEPT.md` lesen.
2. **Lock Security Protocol (`HOOK-WORKFLOW-HYGIENE-01`):** Strikte Vorab-Prüfung auf `LOCK*.txt` / `LOCK.user*.txt`. Bei Vorhandensein Schreibzugriffe sofort unterbinden (SKIP/READONLY).
3. **Pfad-Autorität (`HOOK-PATH-VALIDATION-01`):** Code-Entwicklung ausschließlich im lokalen Quellordner (`C:\_Local_DEV\repos\gardener`). OneDrive dient nur als Spiegel/Sicherung.
4. **Visuals & Guardrails (`HOOK-BANNER-ASSET-01`):** Keine doppelten Header-Banners oder überschriebene Assets generieren.

---

## 4. Test- & Registrierungsverfahren

- **Test-Suite:** `pytest` im Root ausführen (`tests/`).
- **Zentrales Logging:**
  - Log: `C:\Users\User\OneDrive\.SYNC\workstation\antigravity-automations-reference\ANTIGRAVITY-LOG.txt`
  - Registry: `C:\Users\User\OneDrive\.SYNC\workstation\antigravity-automations-reference\ANTIGRAVITY-REGISTRY.md`
