# Changelog

## 2026-08-17

`markdown_dir` gained `exclude_patterns`, and BACH's own knowledge base is
now observed alongside its existing `bach-facts`/`bach-lessons`/`bach-working`
memory-table sources.

- **`exclude_patterns` on `markdown_dir`/`remember_files`** drops filenames
  matching an fnmatch pattern back out of what `patterns`/`glob` already
  matched -- e.g. a generated help directory that ships one canonical
  language plus several machine-translated siblings per key, where
  `patterns` alone cannot express "*.txt but not *_en.txt" (fnmatch's
  `[!seq]` only excludes a single character, not a suffix).
- **Six new BACH observe-sources**: `bach-wiki` and `bach-skills`
  (`sqlite_table` against `wiki_articles`/`skills` in `~/.bach/bach.db`,
  read-only), `bach-root-docs`/`bach-system-docs`/`bach-docs`
  (`markdown_dir` over BACH's README/architecture/changelog/roadmap files),
  and `bach-help-de` (BACH's generated per-command help directory, German
  only via the new `exclude_patterns`). BACH itself is never written to.

## 2026-08-16 [0.4.0]

- **Discoverability, README-Design, Badges & Metadata Parity**:
  - Synchronized badges in `README.md` & `README_de.md` across Test Suite (108 passed, 100% green), Version (`0.4.0`), Python (`>=3.10`), License (`MIT`), `ellmos-ai` Ecosystem, `open-bricks` Umbrella, and `llms.txt` Discovery.
  - Added interactive bilingual Mermaid architecture diagrams detailing the `gardener CLI`/Python API/Search GUI layers, Core Engine (FTS5 BM25 search, Materialize & Run execution engine, federated observe engine with secret redaction and cloud-alert gate), Dual-Database Substrate (`gardener.db` system / `user.db` user space), and federated observe sources (`markdown_dir`, `remember_files`, `sqlite_table`, `agent_transcripts`).
  - Added complete sibling tools matrix linking `ellmos-ai`, `dev-bricks`, and `open-bricks` ecosystem modules (`ellmos-core`, `clutch`, `BACH`, `USMC`, `Rinnsal`, `ellmos-controlcenter-mcp`, `ellmos-filecommander-mcp`, `ellmos-codecommander-mcp`, `ellmos-clatcher-mcp`, `n8n-manager-mcp`, `skills`, `DevCenter`, `open-bricks`).
  - Implemented automated metadata and discoverability parity test suite in `tests/test_metadata.py` (5/5 assertions passed).
  - Updated `llms.txt` Last-checked header to `2026-08-16` and test count to 108 passing tests.

## 2026-08-13

`find()` can be restricted to one observe-source, so a small source is no
longer buried by a large one.

- **`--source <id>[,<id>]` / `find(source=...)`** filters on the
  `observed/<source-id>/…` namespace as a `WHERE` condition -- before the
  ranking, and in all three stages of `find()`: exact FTS, the multi-word OR
  fallback, and the LIKE fallback. Wiring it into only the first stage would
  have dropped the filter silently on any multi-word query.
  - Why it was needed: source sizes differ by three orders of magnitude. On
    the reporting machine `codex-sessions` holds 260,623 transcript lines
    against 518 in `usmc-working`, out of 290,902 `observed` entries total.
    BM25 hands the entire first page to the transcripts, so a subject-matter
    search returns nothing usable and reads as "not in the index".
  - A source id matches a whole path segment, so `--source usmc` does not
    pull in `usmc-working`. A leading `observed/` is optional, several ids
    are OR-ed, and `_`/`%` in an id are escaped instead of acting as LIKE
    wildcards.
- **`--source` without a query lists the source**, newest first. FTS5 needs a
  term to match; "show me everything from this source" has none, so that case
  takes a plain `WHERE`/`ORDER BY updated` path instead of returning nothing.
- **`--type` and `--limit` are now reachable from the CLI.** `find()` already
  accepted both; only the command line did not pass them through.
- **The `find` command parses its own flags.** The CLI has no argparse and
  joined everything after `find` into the query, so `--source` would have
  become a search word. `_parse_find_args()` splits options from search terms,
  accepts `--flag value` and `--flag=value`, and reports unknown options and
  missing values instead of silently searching for them.
- Documented in `README.md` and `README_de.md`, including the pre-existing
  workaround for older versions (pass the source id as a search word -- entry
  names are in the full-text index) and the boundary against `extra_tags`,
  which labels a source at registration time rather than narrowing one search.
- Test suite grew from 86 to 108 tests.

Read-only change: no schema migration, no new index, `recall()` untouched, and
existing `find()` callers keep their behaviour (the new parameter is appended
and defaults to `None`). That includes the edge case `find("")` *without* a
source: it still falls through to the LIKE stage, where `%%` matches everything
and the call acts as a browse. Only the combination of an empty query **and** a
source takes the new listing path -- asserted by a test, because guarding the
three search stages on a non-empty query would have turned that browse into an
empty list without anyone noticing.

## 2026-08-05

Fixed: the never-index list missed Windows paths on non-Windows hosts.

- `sources.is_excluded()` split its argument with the host's own path
  rules, so on Linux and macOS a raw `C:\_Local_DEV\CREDENTIALS\x.md`
  arrived as a single segment and never matched `credentials`. Backslashes
  now count as separators everywhere -- the block list fails closed on any
  host. The CI runs on Linux and had been red on exactly these two cases
  since 2026-08-02.

## 2026-08-02 (later)

Secrets are now redacted on the way into the index, a credential found in a
cloud-synced document raises an alert, and archived transcripts are read
straight out of their zip.

- **Secret redaction (`sources.redact_secrets`)**, applied in `scan()` --
  the one gate every adapter's items pass through, so a future adapter
  cannot forget it. The pattern family stays readable
  (`ghp_***REDACTED***`), the value does not survive.
  **Deliberate semantics: an agent that needs the real token must go to
  the source file. The index says where a credential lives, never what it
  is.**
  - 13 families, following the documented formats used by GitHub secret
    scanning, gitleaks and Yelp detect-secrets: Anthropic, OpenAI (legacy
    and project/service/admin keys), GitHub PAT classic + fine-grained,
    AWS access key ids, Slack bot/user/app tokens, Google API keys, GitLab
    PATs, npm tokens, `Authorization: Bearer` headers, and PEM private-key
    blocks.
  - Every pattern anchors on a fixed length, a restricted character class
    and -- where the vendor provides one -- a literal marker (`T3BlbkFJ`,
    the trailing `AA` on Anthropic keys). That anchoring, not the prefix,
    is what keeps prose out: `skalar`, `ghpx_…`, `AKIAA`, `AIzaX`, `npm_install`
    and a bare "Bearer" in a sentence are all left alone (asserted).
  - AWS bodies match `[A-Z0-9]{16}`, not gitleaks' base32 `[A-Z2-7]{16}`:
    the narrower class would let a real key containing 0/1/8/9 through,
    and for a redaction step missing a live secret is the worse error.
  - Deliberately **not** included: entropy heuristics and keyword
    detectors (`password=`). Both are documented high-recall/low-precision
    and would black out hashes, UUIDs and ordinary config prose. A step
    that runs unattended must not guess.
  - Fingerprints stay computed over the original text -- they answer "has
    the source changed", and the source is the unredacted file. Rewriting
    them would invalidate every stored fingerprint and force a full
    re-index.
- **Cloud credential alert.** A signature found in a file under
  `~/OneDrive` (override: `GARDENER_CLOUD_ROOT`) is a security finding in
  its own right -- the value has left the machine. One line per finding is
  appended to `SECURITY-ALERT_TOKEN-IN-ONEDRIVE.md`
  (`GARDENER_CLOUD_ALERT_FILE`) with date, source path and family --
  **never the value and never the surrounding text**, because the alert
  file lives in the very folder it warns about. Idempotent: a finding
  already listed is not appended again. A signature in a *local* transcript
  (`~/.codex`, `~/.claude`) raises no alert -- it never left. Findings are
  also reported in `observe_sources()`' stats and warned about on stderr.
- **Zip archives as a transcript source.** `agent_transcripts` reads JSONL
  members straight out of a `.zip` via `zipfile`; nothing is unpacked to
  disk. `zip_inner` selects members (default `*.jsonl`). Incrementality is
  per archive rather than per byte offset -- an archive is a finished
  thing, so an unchanged (mtime, size) skips the whole file unopened.
  Archives holding no matching member simply yield nothing.
- Refactor: the per-line work of `scan_agent_transcripts` moved into
  `_transcript_item()`, shared by the plain-file and zip paths so the two
  cannot drift apart in how they extract, name and cite a turn.
- Tests: +11 (redaction positives per family, look-alike negatives,
  prefix-stays-readable, redaction reaching the index through both a
  markdown and a transcript source, alert written/idempotent, local path
  raising no alert, zip indexing/incremental-skip/no-matching-member, and
  redaction inside archives). 74 -> 85.

Measured on this machine: retroactive sweep of the existing 284232 entries
found **6** real credentials (4 npm tokens, 2 AWS key ids), all in local
Codex transcripts, all pasted into sessions by hand -- context like
``//registry.npmjs.org/:_authToken=npm_…`` leaves no doubt they were
genuine. All 6 redacted in place; 0 unredacted matches remain. Cloud alert
initial sweep: **0** findings among indexed OneDrive documents.
`gemini-archive` (the Antigravity conversation archives) indexed 3805
entries from 102 `transcript.jsonl` members in 4.3 s; second run 0.2 s.

## 2026-08-02

Every agent provider on the machine is now in one search -- and the three
transcript presets added yesterday are corrected against the formats they
actually claim to read. All three were written from assumption, not from
the files; measured against real transcripts, two indexed nothing at all
and one indexed mostly noise.

- **`codex` preset rewritten.** A Codex rollout carries the same
  conversation twice: `event_msg` (`payload.type` 'user_message' /
  'agent_message', text in a flat `payload.message`) and `response_item`
  (the raw model exchange). The old preset read only the second one --
  duplicating every assistant turn verbatim, pulling injected
  AGENTS.md/skill boilerplate in as "user" text, and missing the clean
  channel entirely. Now only `event_msg` is indexed.
- **`codex` preset also drops sub-agent tool traffic.** When Codex
  delegates, it wraps the sub-agent's tool calls and their output into
  ordinary `agent_message` events prefixed `[external_agent_tool_call:
  Read]` / `[external_agent_tool_result]`. The payload is a verbatim
  file dump, command stderr or diff -- prose everywhere else in this
  module is what gets indexed, and this is not it. Measured on a real
  archive: **49,286 of 309,883 indexed Codex turns (15.9%)** were tool
  traffic.
- **`kimi` preset rewritten.** It looked for a `TurnBegin` wrapper and
  flat top-level `role`/`content` strings; neither exists in a real
  `wire.jsonl`, so the preset returned nothing for every line of every
  file. Kimi's wire log is an event stream: agent prose arrives as
  `context.append_loop_event` -> `content.part` (`part.type='text'`,
  while `'think'` parts are internal reasoning), user turns as
  `context.append_message` with `message.origin.kind='user'`. That
  origin check matters -- roughly two thirds of user-role messages are
  injected reminders, cron firings and hook results.
- **`gemini_antigravity` preset narrowed.** It treated any
  `source == "MODEL"` step as an assistant turn, which also matches
  VIEW_FILE, RUN_COMMAND, LIST_DIRECTORY, GREP_SEARCH and CODE_ACTION --
  file dumps, command output and diffs, i.e. exactly the tool noise the
  Claude Code extractor skips on purpose. Only `PLANNER_RESPONSE` counts
  now.
- **`path` may be a list of glob patterns**, and `agent_transcripts`
  takes **`key_by: 'name'`**. Together they solve transcript rotation:
  Codex moves finished rollouts from `sessions/` to
  `archived_sessions/`, and with a path-keyed state the same file came
  back as a new key, was re-read from offset 0 and landed in the index a
  second time under a second name. One source spanning both directories,
  keyed on the (globally unique) filename, keeps a moved file's identity.
- **Never-index list (`sources.EXCLUDED_PATH_SEGMENTS` /
  `EXCLUDED_FILENAMES` / `EXCLUDED_SUFFIXES`, `sources.is_excluded()`)**,
  enforced per file inside the adapters, so an over-broad or mistyped
  glob cannot pull credentials into the index: `CREDENTIALS/`, `.ssh`,
  `.gnupg`, `.gardener` itself, `node_modules`, `.git`, `.venv`,
  `__pycache__`, and files like `.npmrc`, `.env`, `auth.json`, `*.pem`,
  `*.key`. Segments are matched whole, so a sibling named
  `credentials-howto.md` is not caught. `gardener.py` derives
  `INTERNAL_SKIP_PREFIXES` from that same list -- one list to maintain,
  and what a source adapter refuses to read, the home-folder walk
  refuses too.
- **`observe_sources()` batches its writes.** It used to spend three
  connections per item (a `get`, `put`'s own, and `put`'s return `get`),
  each opening the DB, ATTACHing the sibling and committing -- about 20
  items/s, which is days for a six-figure transcript archive. It now
  holds one connection per source and commits every 2000 items. Same
  upsert, same FTS (trigger-maintained), same per-item fingerprint skip.
- **New sources:** `codex-sessions` (rollouts across `sessions/` +
  `archived_sessions/`), `codex-history` (the flat cross-session prompt
  history), `gemini-transcripts` (one `transcript.jsonl` per `brain/`
  session), `gemini-automations` (the `automation.toml` prompts),
  `kimi-transcripts` (`wire.jsonl` per agent per session).
  `decisions-archive` widened to `*.txt` -- the archived decision files
  are mostly `.txt`, so only the `.md` minority was being indexed.
- Deliberately **not** indexed, with reason: Antigravity's
  `conversations/*.db` (content columns are Protobuf BLOBs, not text),
  `agyhub_summaries_proto.pb` and `annotations/*.pbtxt` (binary/Protobuf),
  `brain/*/.git` (code snapshots, not conversation), and
  `transcript_full.jsonl` (same turns as `transcript.jsonl`, ~1.6x the
  bytes -- indexing both would duplicate every session).
- `rinnsal-tasks` stays registered and returns 0: both
  `~/.rinnsal/rinnsal.db` and `scanner_tasks.db` exist, and their
  `rinnsal_tasks` table is genuinely empty. Nothing to fix.
- Tests: +6 (never-index list across segments/filenames/suffixes, the
  two adapters honouring it, the shared list reaching `gardener.py`,
  Gemini tool-step filtering, and a rotation test that moves a file
  between directories and asserts nothing is re-indexed). Corrected the
  two presets' tests, which had asserted the invented formats, and
  extended the Codex one to cover sub-agent tool traffic. 67 -> 73.

Measured on this machine after the change: 43 sources, `everything`
14293 -> 284232, `user.db` 57 MB -> 529 MB. The bulk is
`codex-sessions` (260597) -- 4663 rollouts across `sessions/` and
`archived_sessions/`, 10.4 GB of raw JSONL. First scan 9.6 min; the
second scan of the same 10.4 GB takes **0.7 s**, because every unchanged
file is skipped on offset+mtime without being opened.

## 2026-08-01 (later)

- **`markdown_dir`/`remember_files`: new `extra_tags`** (string or list),
  appended to every item's tags. `type` is always `observed` for anything
  an observe-source indexes, so a consumer going straight at the DB
  (rather than through `recall()`) has no way to tell a rule file apart
  from a rotating registry without it -- both are `observed` alike.
  `extra_tags` adds a source-level axis for exactly that distinction,
  without inventing a second `type`.
- **12 new observe-sources**, all `markdown_dir`, all read-only:
  - `.SYNC/_policies/library` and `/adoption` (`policy-library` 4,
    `policy-adoption` 4), tagged `policy`.
  - Root-level pipeline steering docs (`CLAUDE.md`, `README.md`,
    `MASTER-REGISTRY.md`, `POLICY-REG.md`, `STATUS_UEBERSICHT*.md`) for
    six pipeline roots (`pipeline-docs-topics` 1, `-ai` 1, `-research` 13,
    `-roblox` 3, `-software` 4, `-umbruch` 2), tagged `pipeline-doc`. Root
    level only, deliberately not recursive -- a pipeline root can hold
    thousands of per-project files below it.
  - Root-level `CHECKS-REG.md` on the four pipeline roots where a plain
    (non-host-suffixed) copy actually exists (`register-log-ai`,
    `-research`, `-roblox`, `-software`, 1 each), tagged `register-log`.
    Deliberately excludes host-suffixed rotation copies
    (`CHECKS-REG-<HOST>-<N>.md`) and the large rotating `CHECKS-LOG*.txt`
    raw logs -- those are exactly the "thousands of files" scope this
    layer has always avoided.
  - `AUTOMATIONS-MEMORY.md` was searched for too, but not newly
    registered: the two canonical copies are already indexed by the
    pre-existing `gemini-rules` and `gemini-antigravity` sources.
  - `everything` count: 14257 -> 14293 (+36), matching the sum of what
    each new source reported indexed.
- **Two disabled-by-default source-config templates for cross-host
  federation** via a separate transit-sync mechanism that mirrors another
  host's databases to read-only `~/.republica/<host>/<namespace>.sqlite` (Republica showcases)
  snapshots: `usmc_replica_source_configs(host)` (facts/lessons/working/
  sessions, the same four-way split as this machine's own `usmc-*`
  sources) and `gardener_replica_source_config(host)` (the foreign
  `everything` table). Both raise for the current machine's own hostname
  -- a replica directory named after the current host is that host's
  replica of *itself*, and indexing it would duplicate every row under a
  second source_id. Neither is registered anywhere by default; arming one
  is a two-line call once a real other-host snapshot exists (see
  `sources.py`'s module note above `usmc_replica_source_configs`).
- Tests: +10 (`extra_tags` on/off/single-string; the two template
  builders' self-host guard and disabled-by-default shape; a disabled
  replica, an enabled-but-absent replica, and an enabled replica against
  a real foreign snapshot are all clean, exception-free paths). Suite:
  54 -> 64.

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

## 2026-08-01 (multi-agent transcripts)

- **Multi-Agent Transcript Format Support**:
  - Added native format extractor presets for **Gemini Antigravity** (`gemini_antigravity`), **Codex** (`codex`), and **Kimi** (`kimi`) in `scan_agent_transcripts` (`sources.py`).
  - Added support for indexing Gemini transcript logs (`~/.gemini/antigravity/brain/*/.system_generated/logs/transcript.jsonl`), Codex session & history JSONLs (`~/.codex/history.jsonl`, `~/.codex/archived_sessions/*.jsonl`), and Kimi wire transcripts (`~/.kimi/sessions/*/*/wire.jsonl`).
  - Extended metadata mapping (`session`, `uuid`, `timestamp`, `step_index`) across all supported agent formats while retaining 100% backward compatibility for `claude_code` and `generic`.
  - Added 3 new unit tests in `test_observe_sources.py` (`test_gemini_antigravity_format_preset`, `test_codex_format_preset`, `test_kimi_format_preset`).
  - Suite nach Integration in den aktuellen Stand: 64 -> 67 grün. (Die Arbeit
    entstand parallel auf einem OneDrive-Checkout gegen einen 42er-Stand und
    wurde am 2026-08-01 im Zuge der Plan-D-Migration hierher übernommen.)

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
