# CLAUDE.md — Local Signpost for Gardener

Lies und befolge [AGENTS.md](AGENTS.md).

## Quick Instructions
- **Primary Dev Location:** `C:\_Local_DEV\repos\gardener`
- **Testing:** `pytest` im Root, ganze Suite (Stand 2026-08-13: 108 tests, 100% green).
  Einzelne Dateien zaehlen weniger — `tests/test_gardener_core.py` allein ist nicht die Suite.
- **Central Reference:** `%USERPROFILE%\OneDrive\.SYNC\workstation\antigravity-automations-reference\`
- **Host Resolution:** Expand `%USERPROFILE%` on the active host. Runtime
  prompts use `sidecar-%COMPUTERNAME%.json` when registered; `sidecar.json`
  remains the laptop default and must not be overwritten from another host.
- **Permission & Safety:** Default / Turbo permission mode allowed for dev/tests. Check `LOCK*.txt` before writing.
