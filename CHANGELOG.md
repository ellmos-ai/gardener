# Changelog

## 2026-08-01

- **README language parity:** Synchronized `README_de.md` with the canonical
  English structure and restored byte-identical code blocks across the
  maintained EN/DE pair.
- **Every agent's memory in one search**: the observe-source layer now covers
  the other coding agents on the machine, not just Claude Code. Newly indexed
  (all read-only, originals untouched): Codex/GPT memories and rule file
  (`codex-memories` 4, `codex-rollouts` 256 run summaries, `codex-rules` 1),
  Gemini/Antigravity (`gemini-rules` 4, `gemini-antigravity` 3), Kimi's prompt
  history (`kimi-prompts` 515), and the USMC memory database
  (`usmc-facts` 9, `usmc-lessons` 8, `usmc-working` 95, `usmc-sessions` 4).
  All of it lands as `observed`, never as `memory`/`lesson`: foreign material
  belongs in `find()`, and must not crowd out what `recall()` was curated for.
- **`sqlite_table`: `content` may now name several columns**, joined in order.
  A row whose meaning is split over two text fields was only half searchable
  before — whichever column was not configured simply was not in the index.
  This was live: `bach-lessons` had been indexing `solution` while every
  lesson's `problem` text stayed invisible. Both BACH and USMC lessons are now
  indexed as problem + solution (174 BACH lessons re-indexed).
- **`agent_transcripts`: new `default_role`** for single-role archives that
  carry no role field at all. Without it such a file indexed nothing, because
  an absent role never matches the `roles` filter — which is exactly what a
  bare prompt history looks like. A missing role without `default_role` is
  still skipped rather than indexed under an invented one.
- **Fixed a source pointing at a path that no longer exists**:
  `memoryhooker-docs` still referenced the module's pre-2026-07-26 location.
  A source can go stale silently — it keeps reporting success while indexing
  an empty directory.
- Tests: +4 (multi-column content incl. an unknown-column refusal,
  `default_role`, and the unchanged no-role-no-default guard). Together
  with the search GUI landed the same day, the suite stands at 54.

## 2026-07-31

- **Search GUI for humans (`search_gui.py`, `gardener gui`)**:
  - New dependency-free, read-only web UI over the FTS5 search core:
    search box, type filter, BM25-ranked results with match snippets and
    an entry detail view. Pure standard library (`http.server`), binds to
    127.0.0.1 only, GET endpoints exclusively — no writes against
    `gardener.db`/`user.db` (privacy per design: local, read-only).
  - Follows the BACH `unified_search` pattern (FTS5 `snippet()` markers
    `>>>`/`<<<` rendered as highlighted matches in the browser).
  - `find()` gained an optional `with_snippets=True` parameter returning
    an FTS5 `snippet()` context per hit (LIKE-fallback hits carry no
    snippet; default behaviour unchanged).
  - CLI: new command `gui [--port N] [--no-browser]`; help text and
    translations (`cmd.gui`) added; `pyproject.toml` ships the new
    `search_gui` module.
  - 11 new tests (`tests/test_search_gui.py`): snippet API, index page,
    search/entry/status endpoints, type filter, 404 handling, read-only
    enforcement. Suite verified at 50/50 passing.

## 2026-07-30

- **Multi-Word Query UX Improvement & FTS5 BM25 Ranking**:
  - Implemented automatic FTS5 OR query decomposition (`_build_fts_or_query`) for multi-word queries in `find()` when strict AND search yields 0 results.
  - Multi-word searches (e.g. `"Registry Mitgliedschaft"`) now match documents containing individual terms while automatically ranking documents containing all terms higher via FTS5 BM25 relevance. Preserves explicit quotes (`"..."`) and boolean operators (`AND`, `OR`, `NOT`).
  - Hardened SQLite connection handling across `find()` and `get()` with strict `try...finally: conn.close()` resource protection.
  - Added unit test cases (`test_multi_word_query_ux_or_fallback_and_ranking` and `test_build_fts_or_query_helper`) verifying 39/39 passing tests green.
- **Maintenance & Technical Hygiene**:
  - Updated `llms.txt` `Last-checked` timestamp to `2026-07-30`.
  - Re-verified full test suite execution (39/39 passed) and clean repository working tree.

## 2026-07-25 (later)

- **Documentation clean-up (repo after-care)**:
  - Removed references to internal, non-resolvable directory names from the
    public documents (`ROADMAP.md`, `docs/decisions/knowledge-index.md`,
    `locales/translations.json`). They meant nothing to outside readers.
  - `ROADMAP.md` is English again: the trailing sections had drifted back into
    German and carried internal migration notes. Replaced by a short,
    publicly meaningful "Gardener as a memory module" section, and the German
    counterpart added to `ROADMAP_de.md` — both roadmaps now cover the same
    ground.
  - Architecture tree in both READMEs completed (`sources.py`, `i18n.py`,
    `locales/`, `tests/` were missing); header now states the version instead
    of a stale date.
  - Corrected observe-source test count 15 → 17 in both roadmaps (counted at
    the source); full suite verified at 37 passing.
  - Module manifest `visibility` set to `public` (the repository has been
    public for a while); `_after-care/` added to `.gitignore`.

## 2026-07-25

- **Maintenance & Technical Hygiene**:
  - Added `[tool.pytest.ini_options]` with `pythonpath = "."` in `pyproject.toml` for standard pytest resolution.
  - Updated `llms.txt` Last-checked header to 2026-07-25 and test suite count to 37 passing tests.
  - Added Shields.io status badges and LLM integration note callout to `README.md` and `README_de.md`.
  - Verified 37/37 unit and integration tests passing green.

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
