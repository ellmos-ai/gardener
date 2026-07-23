# Changelog

## 2026-07-23

- **New (v0.3.0): Cross-source federated index.** `observe()`'s read-only,
  "look outside" principle is extended to knowledge that lives in *other*
  tools, not just Gardener's own home folder. New module `sources.py` with
  four adapter kinds:
  - `markdown_dir` -- a directory (or wildcard glob of directories) of
    markdown files, one entry per file.
  - `remember_files` -- `.remember`-style note files below a root, via
    recursive glob.
  - `sqlite_table` -- a single table in a foreign SQLite database, opened
    strictly read-only (`mode=ro`); path/table/column-mapping come entirely
    from config, so it can index any foreign schema without Gardener
    knowing it in advance. Table and column names are whitelisted against
    the live schema before use in SQL.
  - `agent_transcripts` -- JSONL chat transcripts, indexed line by line,
    text turns only (tool calls/results and "thinking" blocks are
    skipped). Ships a built-in field mapping for Claude Code's own
    transcript format, plus a generic dotted-path role/text mapping for
    other line-based JSON transcripts. Large, growing files are tailed
    from a saved byte offset (`~/.gardener/observe_sources_state.json`) --
    a refresh never re-reads bytes it already indexed.
  - Every indexed entry carries a `source_ref` in `meta` (file/DB path,
    table+row, or transcript line+uuid) so a search hit always cites back
    to where it actually lives. `find()` already searched `gardener.db` +
    `user.db` in one query, so cross-source hits (stored as ordinary
    `observed` entries in `user.db`) show up alongside your own entries
    automatically -- no new search API needed.
  - New `Gardener` methods: `observe_source_add`, `observe_source_remove`,
    `observe_source_list`, `observe_sources`. New CLI: `gardener
    observe-source add/list/remove/refresh`. Configuration lives in
    `config.json` under `observe_sources`; nothing is hardcoded to a
    specific machine, user, or tool.
  - Deliberately out of scope for this release: adapter presets for the
    Codex/Gemini/Kimi transcript formats (only Claude Code ships a
    built-in mapping; other formats route through the generic
    `role_field`/`text_field` mapping) and the v0.2 decay/usage-tracking
    items (unrelated roadmap section, not touched here).
  - Added 15 regression tests with synthetic fixtures (test suite: 19 ->
    34), covering all four adapters, incremental refresh behavior,
    federated search across own + observed entries, and observe-source
    config CRUD across a simulated restart.

- **New (v0.3.1): `patterns` config for `markdown_dir`.** The
  `markdown_dir` observe-source adapter can now match more than one
  filename pattern per directory via an optional `patterns` list in
  config (default `["*.md"]`), e.g. `patterns=["*.md", "*.txt"]` to
  index plain-text notes alongside markdown in the same source. Files
  matching more than one pattern are only indexed once. Backward
  compatible: the older singular `glob` key keeps working unchanged
  for existing configs; `patterns` takes precedence if both are set.
  List-valued config like `patterns` has to go through the Python API
  (`af.observe_source_add(...)`) -- the CLI's plain `key=value` form
  only accepts strings, not JSON.
  - Added 3 regression tests (test suite: 34 -> 37) covering the
    default markdown-only behavior, the new `patterns` list, and the
    legacy single-`glob` backward-compatibility path.

## 2026-07-11

- Release hygiene: `i18n.py` now carries built-in German/English CLI help fallbacks, so non-editable installs that miss `locales/translations.json` still show readable help text instead of raw translation keys.
- Added a regression test that runs `gardener.py` from a wheel-like copy without the `locales/` directory.

## 2026-07-03

- **Security:** `materialize()` sanitizes `filename`/`original_name` from entry meta to their base name. Previously, meta set via `put()` could contain `..` or absolute paths and make `materialize()` write outside the destination directory (path traversal).
- **Security docs:** new "Security Model" section in README/README_de documenting that `run()` and the seeded `shell` tool execute code without a sandbox, and that any layer exposing `put()`/`run()` must bring its own authorization.
- `sync()` in `always_absorb` mode no longer absorbs and deletes its own `config.json` (which silently reset the mode to `selective` on the next start). `config.json` is now part of the shared internal skip list.
- `_is_internal()` compares whole path segments instead of string prefixes: sibling names like `.absorber-notes.txt` or `.outputs/` are no longer wrongly skipped; internal dirs are now also skipped at any nesting depth.
- `observe()`/`sync()` build `observed/...` entry names with POSIX separators (`rel.as_posix()`), so the same file yields the same entry name on Windows and Unix (previously Windows produced `observed/sub\file.txt`, causing duplicates in cross-system setups).
- `absorb()` raises a clean `FileNotFoundError` for directories instead of crashing later in `_hash_file()` with `IsADirectoryError`/`PermissionError`.
- CLI: `stdout`/`stderr` are reconfigured to UTF-8 with replacement errors in `main()`, so umlauts no longer crash on Windows consoles without `PYTHONIOENCODING=utf-8`.
- CLI: `gardener absorb <path>` prints a clean error message for missing or unreadable files instead of an unhandled traceback.
- CLI: renamed the task loop variable that shadowed the i18n translation function `t`.
- Added 6 regression tests for the above (test suite: 13 -> 19).

## 2026-06-22

- Hardened entry deserialization so invalid `meta` JSON is normalized to an empty object instead of leaking as a string and crashing `recall()` sorting.
- Added a regression test for `recall()` on memory entries with invalid `meta` JSON.

## 2026-06-12

- Removed the never-populated `blobs` table from the schema: blob metadata (`blob_path`, `blob_hash`, `size`, `mimetype`, `original_name`) deliberately lives in the entry's `meta` JSON, which is what `absorb()`/`materialize()` and the design docs already use. Deliberate decision, see DESIGN.md/KONZEPT.md.
- `absorb()` now stores `original_name` in `meta` (was only `original_path`), matching what `materialize()` reads and what the design docs document.
- `observe()` now skips the internal runtime dirs `.absorber/`, `.output/`, `.gardener/`, `__pycache__/` via a skip list shared with `sync()` (previously it skipped a stale `export` prefix and indexed absorber/output files).
- Tasks are now sorted by semantic priority (critical > high > normal > low) instead of alphabetical string order.
- `find()` now preserves FTS5 relevance (bm25 rank) for full-text hits; LIKE-fallback results are ordered newest first. Previously the final sort discarded the rank and listed oldest entries first.
- `consolidate()` no longer decays or forgets pinned entries.
- Documentation: corrected the local data directory to `~/.gardener` (env `GARDENER_DATA`) in README, README_de, KONZEPT and DESIGN; the previously documented `AppData/Local/Gardener/` path was never used by the code.
- Added regression tests for all fixes above (test suite: 5 -> 10 tests).
- Added a minimal `pyproject.toml` (distribution `gardener-os`, since `gardener` is taken on PyPI; console script `gardener = gardener:main`, requires-python >=3.10, zero runtime dependencies). Verified with an editable install in a throwaway venv.
- Replaced romanized German umlaut spellings in seeded user-facing knowledge and bridge-tool descriptions with real umlauts.
- Updated German runtime error messages for tool execution failures to use real umlauts.
- Added a regression test that verifies seeded German texts no longer contain the old `ae`/`oe`/`ue` spellings.

## 2026-06-11

- Added README and `llms.txt` discovery context for the canonical `ellmos-ai/gardener` repository path.
- Added audience, preferred search phrases, disambiguation, and `Last-checked: 2026-06-11` metadata to `llms.txt`.
- Fixed `llms.txt` documentation links to use the repository's actual `master` branch.

## 2026-06-06

- Updated the Gardener test workflow to `actions/checkout@v6` and `actions/setup-python@v6`.
- Documented the CI hygiene refresh without changing runtime behavior.
