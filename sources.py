# -*- coding: utf-8 -*-
"""
Gardener -- Cross-Source Federated Index (observe-source adapters)
====================================================================

Read-only adapters that let Gardener pull *searchable text* from
knowledge that lives outside its own database: other tools' markdown
memory files, `.remember` notes, a table in a foreign SQLite database,
or JSONL agent-chat transcripts.

Design (see ROADMAP.md, "Cross-Source federated index"):

  - Observe, don't absorb. Originals are never moved, changed, or
    deleted -- only their text is copied into Gardener's FTS index,
    exactly like observe() already does for files in the home folder.
    Foreign databases are opened strictly read-only.
  - Cite back to the source. Every indexed item carries a
    ``source_ref`` in its ``meta`` (db/file path, table, row id, line
    number, ...) so a search hit can always be traced back to where
    it actually lives.
  - Incremental and idempotent. Unchanged items are skipped on repeat
    refreshes via a per-item fingerprint. JSONL transcripts (which can
    be gigabytes) are tailed from a saved byte offset instead of being
    re-read from scratch on every refresh.

Four adapter kinds, registered in ``ADAPTERS``:

  markdown_dir        A directory (or a glob of directories) of
                       markdown files, one entry per file. Covers
                       tools that keep per-project markdown memories,
                       e.g. Claude Code's ``~/.claude/projects/*/memory``.
                       ``patterns`` (default ``["*.md"]``) can widen
                       this to other file kinds, e.g. ``.txt`` notes.
                       ``extra_tags`` can mark every item from a source
                       for a downstream consumer to filter on (e.g. a
                       rotating registry tagged apart from a rule file),
                       without inventing a second `type` axis.
  remember_files       Small note files matched by a recursive glob
                       (default pattern: ``**/.remember``).
  sqlite_table         A single table in a foreign, read-only SQLite
                       database. Path, table, and a name/content/tags
                       column mapping come entirely from config -- this
                       is how a rinnsal- or BACH-style task/notes table
                       gets indexed without Gardener knowing their schema.
  agent_transcripts    JSONL chat-transcript files. Ships a built-in
                       ``claude_code`` field mapping (Claude Code's own
                       transcript format); any other line-based JSON
                       transcript can be indexed via a generic
                       dotted-path role/text field mapping. Only text
                       turns are indexed -- tool calls/results and
                       internal "thinking" blocks are skipped.

This module has no dependency on gardener.py (and vice versa is only a
thin wiring layer in ``Gardener.observe_source_*``), so adapters stay
independently testable and reusable.
"""
import glob
import hashlib
import json
import os
import platform
import re
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterator, Optional


@dataclass
class SourceItem:
    """One piece of foreign, indexable text found by an adapter.

    ``key`` is only for logging/debugging. ``name`` is the unique
    Gardener entry name the item will be put() under (always prefixed
    ``observed/<source_id>/...``, mirroring the existing observe()
    naming). ``fingerprint`` is an opaque marker; if it is unchanged
    from the last refresh, the caller skips re-writing the entry.
    """
    key: str
    name: str
    content: str
    tags: str
    meta: Dict[str, Any] = field(default_factory=dict)
    fingerprint: str = ""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _path_key(p: Path) -> str:
    """Windows/Unix-stable identity string for a path, for use inside
    entry names. Mirrors observe()'s use of as_posix() for cross-system
    stability, and additionally strips a Windows drive letter so the
    same file yields the same entry name regardless of drive.
    """
    s = p.as_posix()
    s = re.sub(r"^[A-Za-z]:", "", s)
    return s.lstrip("/")


def _safe_key(value: Any) -> str:
    """Keeps a single entry-name path segment readable and slash-free."""
    s = str(value).replace("/", "_").replace("\\", "_").strip()
    return s or "unnamed"


def _dig(d: Any, dotted_path: str) -> Any:
    """Looks up a dotted path like 'message.role' in a nested dict."""
    cur = d
    for part in dotted_path.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur


def _extra_tags_suffix(config: Dict) -> str:
    """Optional static tags appended to every item an adapter yields, via
    config['extra_tags'] (a string or a list of strings).

    This is a source-level concern, distinct from `type` (which observe-
    sources always set to 'observed' -- see gardener.py's observe_sources()).
    A consumer that goes straight to the DB rather than through recall()
    (a memory-injection backend, say) may want to treat two 'observed'
    sources differently -- e.g. keep a rule file findable AND surfaced as
    a hint, while keeping a rotating check-registry findable but NOT
    surfaced, without that distinction living in `type`. `extra_tags` is
    how a source config expresses that without inventing a second type
    axis: tag it, and let the consumer filter on tags.
    """
    extra = config.get("extra_tags") or []
    if isinstance(extra, str):
        extra = [extra]
    cleaned = [str(t).strip() for t in extra if str(t).strip()]
    return ("," + ",".join(cleaned)) if cleaned else ""


# ---------------------------------------------------------------------------
# Adapter: markdown_dir / remember_files (share a file-glob scanner)
# ---------------------------------------------------------------------------

def _iter_text_files(source_id: str, config: Dict, default_patterns,
                      kind_tag: str) -> Iterator[SourceItem]:
    """Shared scanner for markdown_dir and remember_files.

    config:
        path: a directory, OR a glob pattern that expands to one or
              more directories (e.g. '~/.claude/projects/*/memory').
        patterns: list of filename patterns matched within each
              matched directory (default: `default_patterns`;
              '**/...' patterns recurse). Every file matching ANY
              pattern is indexed once, e.g. `["*.md", "*.txt"]` to
              cover both markdown and plain-text notes in one source.
        glob: single filename pattern -- older alias kept for
              backward compatibility, equivalent to `patterns: [glob]`.
              Ignored if `patterns` is also set.
        extra_tags: optional string or list of strings, appended to every
              item's tags (see `_extra_tags_suffix`). Lets a consumer
              distinguish sources by tag beyond the fixed `type='observed'`
              -- e.g. tagging a rule-file source 'policy' (keep it
              surfaced as a hint) versus a rotating registry source
              'register-log' (findable, but a consumer may choose to
              exclude it from what gets surfaced).
    """
    raw_path = str(config.get("path", ""))
    if not raw_path:
        return
    base_pattern = os.path.expanduser(raw_path)
    if "patterns" in config:
        file_patterns = list(config["patterns"])
    elif "glob" in config:
        file_patterns = [config["glob"]]
    else:
        file_patterns = list(default_patterns)

    # glob.glob() on a plain, non-wildcard, existing path simply returns
    # that path -- so this one call covers both a literal directory and
    # a wildcard-directory pattern like '.../*/memory'.
    for base_dir in sorted(glob.glob(base_pattern, recursive=True)):
        bp = Path(base_dir)
        if not bp.is_dir():
            continue
        # Collect matches from every pattern into a set first, then sort
        # once -- so a file matched by two patterns is only indexed once,
        # and ordering stays deterministic across the combined results.
        matched_files = set()
        for file_glob in file_patterns:
            matched_files.update(p for p in bp.glob(file_glob) if p.is_file())
        for file_path in sorted(matched_files):
            try:
                stat = file_path.stat()
                content = file_path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue

            key = _path_key(file_path)
            yield SourceItem(
                key=key,
                name=f"observed/{source_id}/{key}",
                content=content,
                tags=f"{kind_tag},{source_id}{_extra_tags_suffix(config)}",
                meta={
                    "source_ref": {"kind": kind_tag, "path": str(file_path)},
                    "size": stat.st_size,
                    "modified": datetime.fromtimestamp(
                        stat.st_mtime).isoformat(timespec="seconds"),
                },
                fingerprint=f"{stat.st_mtime_ns}:{stat.st_size}",
            )


def scan_markdown_dir(source_id: str, config: Dict) -> Iterator[SourceItem]:
    """A directory (or glob of directories) of markdown memory files.

    By default only `*.md` files are matched; pass `patterns` in config
    (e.g. `patterns=["*.md", "*.txt"]`) to also cover plain-text or
    other file kinds in the same source.
    """
    yield from _iter_text_files(source_id, config, default_patterns=["*.md"],
                                 kind_tag="markdown_dir")


def scan_remember_files(source_id: str, config: Dict) -> Iterator[SourceItem]:
    """`.remember`-style note files anywhere below a root, via glob."""
    yield from _iter_text_files(source_id, config,
                                 default_patterns=["**/.remember"],
                                 kind_tag="remember_files")


# ---------------------------------------------------------------------------
# Adapter: sqlite_table
# ---------------------------------------------------------------------------

def scan_sqlite_table(source_id: str, config: Dict) -> Iterator[SourceItem]:
    """A single table in a foreign SQLite database, opened strictly
    read-only (URI mode=ro -- Gardener never writes to a foreign DB).

    config:
        db_path: path to the foreign .db/.sqlite file
        table:   table name
        columns: {"content": "<col>", "id": "<col>", "name": "<col>",
                  "tags": "<col>"} -- 'content' is required, the rest
                  are optional. Table/column names are whitelisted
                  against the live schema before use in SQL.

                  'content' may also be a LIST of columns, joined with
                  blank lines in the given order. Rows whose meaning is
                  split across several text columns (a lesson's problem
                  AND its solution, say) would otherwise only be half
                  searchable -- whichever column was not chosen simply
                  would not be in the index.
    """
    db_path = os.path.expanduser(str(config.get("db_path", "")))
    table = str(config.get("table", ""))
    columns = config.get("columns") or {}
    if not db_path or not table or "content" not in columns:
        return
    raw_content = columns.get("content")
    content_cols = (list(raw_content) if isinstance(raw_content, (list, tuple))
                    else [raw_content])
    content_cols = [c for c in content_cols if c]
    if not content_cols:
        return
    db_file = Path(db_path)
    if not db_file.is_file():
        return

    uri = f"file:{db_file.as_posix()}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    try:
        valid_tables = {row["name"] for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )}
        if table not in valid_tables:
            return
        valid_columns = {row["name"] for row in
                          conn.execute('PRAGMA table_info("{}")'.format(table))}

        id_col = columns.get("id")
        name_col = columns.get("name")
        tags_col = columns.get("tags")

        select_cols = ["rowid"]
        for col in [id_col, name_col, *content_cols, tags_col]:
            if col and col not in valid_columns:
                # A configured column that doesn't exist is a config
                # error -- refuse rather than silently drop it.
                return
            if col and col not in select_cols:
                select_cols.append(col)

        quoted = ", ".join('"{}"'.format(c) for c in select_cols)
        sql = 'SELECT {} FROM "{}"'.format(quoted, table)
        rows = conn.execute(sql).fetchall()
    finally:
        conn.close()

    # Positional index map, not name-based row[...] access: if `id_col`
    # (or another selected column) is an INTEGER PRIMARY KEY, it is a
    # rowid alias, and SQLite then reports BOTH "rowid" and that column
    # under the alias's name -- row["rowid"] would raise IndexError in
    # that case. Position in `select_cols` is unambiguous regardless.
    col_pos = {c: i for i, c in enumerate(select_cols)}

    for row in rows:
        row_id = row[col_pos[id_col]] if id_col else row[0]
        parts = []
        for col in content_cols:
            value = row[col_pos[col]]
            if value is not None and str(value).strip():
                parts.append(str(value))
        content = "\n\n".join(parts)
        display_name = (row[col_pos[name_col]]
                         if name_col and row[col_pos[name_col]] else str(row_id))
        tags_value = (row[col_pos[tags_col]]
                      if tags_col and row[col_pos[tags_col]] else "")

        fingerprint_source = "|".join(str(row[i]) for i in range(len(select_cols)))
        fingerprint = hashlib.sha256(
            fingerprint_source.encode("utf-8", "replace")
        ).hexdigest()[:16]

        tags = f"sqlite_table,{source_id}"
        if tags_value:
            tags += f",{tags_value}"

        # Gardener's FTS index covers the entry's name/content/tags
        # columns, not arbitrary meta JSON -- so the row's own title
        # (name_col) has to be part of the indexed content to be
        # findable at all, not just carried in meta.title for citation.
        indexed_content = (f"{display_name}\n\n{content}"
                            if name_col and display_name != str(row_id) else content)

        yield SourceItem(
            key=str(row_id),
            name=f"observed/{source_id}/{table}/{_safe_key(row_id)}",
            content=indexed_content,
            tags=tags,
            meta={
                "source_ref": {
                    "kind": "sqlite_table",
                    "db_path": str(db_file),
                    "table": table,
                    "row_id": row_id,
                },
                "title": display_name,
            },
            fingerprint=fingerprint,
        )


# ---------------------------------------------------------------------------
# Adapter: agent_transcripts
# ---------------------------------------------------------------------------

_CLAUDE_CODE_TURN_TYPES = ("user", "assistant")


def _extract_claude_code_text(entry: Dict):
    """Extracts (role, text) from one Claude Code transcript JSONL line,
    or (None, None) if the line carries no indexable text turn (tool
    calls/results, "thinking" blocks, and isMeta wrapper messages are
    all skipped -- only text actually typed/written by user or
    assistant is indexed).
    """
    if entry.get("type") not in _CLAUDE_CODE_TURN_TYPES:
        return None, None
    if entry.get("isMeta"):
        return None, None
    message = entry.get("message")
    if not isinstance(message, dict):
        return None, None
    role = message.get("role")
    content = message.get("content")

    if isinstance(content, str):
        text = content.strip()
    elif isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                block_text = block.get("text", "")
                if isinstance(block_text, str) and block_text.strip():
                    parts.append(block_text)
        text = "\n".join(parts).strip()
    else:
        text = ""

    if not text:
        return None, None
    return role, text


def _extract_generic_text(entry: Dict, role_field: str, text_field: str,
                           text_block_type: str, default_role=None):
    """Generic dotted-path role/text extraction for JSONL transcript
    formats other than Claude Code's. `text_field` may point at a
    plain string, or a list of blocks (extracts blocks whose 'type'
    equals `text_block_type`, concatenated).

    `default_role` covers single-role archives that carry no role field
    at all -- e.g. a plain prompt history where every line is by
    definition the user's. Without it such a file indexes nothing,
    because an absent role never matches the `roles` filter.
    """
    role = _dig(entry, role_field)
    if role is None:
        role = default_role
    raw = _dig(entry, text_field)

    if isinstance(raw, str):
        text = raw.strip()
    elif isinstance(raw, list):
        parts = []
        for block in raw:
            if isinstance(block, dict) and block.get("type") == text_block_type:
                block_text = block.get("text", "")
                if isinstance(block_text, str) and block_text.strip():
                    parts.append(block_text)
        text = "\n".join(parts).strip()
    else:
        text = ""

    if not text:
        return None, None
    return role, text


def _extract_gemini_antigravity_text(entry: Dict):
    """Extracts (role, text) from a Gemini Antigravity transcript JSONL line."""
    if not isinstance(entry, dict):
        return None, None
    tp = entry.get("type")
    src = entry.get("source")

    # User input turn
    if tp == "USER_INPUT" or src == "USER_EXPLICIT":
        role = "user"
        content = entry.get("content")
        if isinstance(content, str):
            text = content.strip()
        else:
            text = ""
        return (role, text) if text else (None, None)

    # Planner / assistant turn
    if tp == "PLANNER_RESPONSE" or src == "MODEL":
        role = "assistant"
        content = entry.get("content")
        if isinstance(content, str) and content.strip():
            text = content.strip()
        else:
            thinking = entry.get("thinking")
            if isinstance(thinking, str) and thinking.strip():
                text = thinking.strip()
            else:
                text = ""
        return (role, text) if text else (None, None)

    return None, None


def _extract_codex_text(entry: Dict):
    """Extracts (role, text) from a Codex history or session JSONL line."""
    if not isinstance(entry, dict):
        return None, None

    # 1. Simple history entry: {"session_id": ..., "ts": ..., "text": ...}
    if "text" in entry and isinstance(entry["text"], str) and "session_id" in entry:
        return "user", entry["text"].strip()

    # 2. Session rollout item: {"payload": {"role": "user"|"assistant", "content": ...}}
    payload = entry.get("payload")
    if isinstance(payload, dict):
        role = payload.get("role")
        if role in ("user", "assistant"):
            content = payload.get("content")
            if isinstance(content, str):
                text = content.strip()
            elif isinstance(content, list):
                parts = []
                for block in content:
                    if isinstance(block, dict):
                        b_type = block.get("type")
                        if b_type in ("input_text", "text", "output_text"):
                            b_text = block.get("text", "")
                            if isinstance(b_text, str) and b_text.strip():
                                parts.append(b_text.strip())
                text = "\n".join(parts).strip()
            else:
                text = ""
            return (role, text) if text else (None, None)

    return None, None


def _extract_kimi_text(entry: Dict):
    """Extracts (role, text) from a Kimi wire/session JSONL line."""
    if not isinstance(entry, dict):
        return None, None

    # TurnBegin wrapper
    msg = entry.get("message")
    if isinstance(msg, dict):
        m_type = msg.get("type")
        payload = msg.get("payload")
        if m_type == "TurnBegin" and isinstance(payload, dict):
            u_input = payload.get("user_input")
            if isinstance(u_input, str) and u_input.strip():
                return "user", u_input.strip()

    # Direct role/content format
    role = entry.get("role")
    content = entry.get("content")
    if role in ("user", "assistant") and isinstance(content, str) and content.strip():
        return role, content.strip()

    return None, None


def scan_agent_transcripts(source_id: str, config: Dict,
                            state: Optional[Dict] = None) -> Iterator[SourceItem]:
    """JSONL chat-transcript files, indexed line by line, text turns only.

    config:
        path: glob pattern for the JSONL files (e.g.
              '~/.claude/projects/*/**/*.jsonl'); '**' is recursive.
        format: 'claude_code' (default), 'gemini_antigravity', 'codex',
              'kimi', or 'generic' (uses role_field/text_field below).
        roles: which roles to index (default: ["user", "assistant"]).
        include_sidechain: index Claude Code sub-agent sidechain turns
              too (default: False -- only the main conversation).
        role_field / text_field: dotted paths into each JSON line,
              only used when format == 'generic'
              (default 'message.role' / 'message.content').
        text_block_type: block 'type' to extract when text_field
              resolves to a list of blocks (default 'text').
        default_role: role to assume when a line carries no role field
              (format 'generic' only). Needed for single-role archives
              such as a bare prompt history; it must also appear in
              `roles` to be indexed.

    `state` is a mutable dict (file_key -> {offset, mtime, size,
    line_no}) that this function reads AND updates in place so the
    caller can persist it: refreshing a multi-GB transcript only reads
    the bytes appended since the last refresh, never the whole file.
    """
    if state is None:
        state = {}
    raw_path = str(config.get("path", ""))
    if not raw_path:
        return
    path_pattern = os.path.expanduser(raw_path)
    fmt = config.get("format", "claude_code")
    roles = set(config.get("roles", ["user", "assistant"]))
    include_sidechain = bool(config.get("include_sidechain", False))
    role_field = config.get("role_field", "message.role")
    text_field = config.get("text_field", "message.content")
    text_block_type = config.get("text_block_type", "text")
    default_role = config.get("default_role")

    for file_str in sorted(glob.glob(path_pattern, recursive=True)):
        file_path = Path(file_str)
        if not file_path.is_file():
            continue
        try:
            stat = file_path.stat()
        except OSError:
            continue

        file_key = _path_key(file_path)
        prev = state.get(file_key, {})
        start_offset = prev.get("offset", 0)
        if stat.st_size < start_offset:
            start_offset = 0  # file was rotated/truncated -- start over
        if start_offset == stat.st_size and prev.get("mtime") == stat.st_mtime:
            continue  # unchanged since last refresh

        line_no = prev.get("line_no", 0)
        last_good_offset = start_offset
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                f.seek(start_offset)
                while True:
                    raw_line = f.readline()
                    if not raw_line:
                        break
                    if not raw_line.endswith("\n"):
                        # Partial line at EOF (file still being written) --
                        # stop here without advancing past it, so it is
                        # re-read (complete) on the next refresh. Using
                        # readline()+tell() here (not iterating the file
                        # object) is required: interleaving tell() with
                        # `for line in f` is unreliable due to read-ahead
                        # buffering.
                        break
                    last_good_offset = f.tell()
                    line_no += 1
                    line = raw_line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                    except json.JSONDecodeError:
                        continue

                    if fmt == "claude_code":
                        if not include_sidechain and entry.get("isSidechain"):
                            continue
                        role, text = _extract_claude_code_text(entry)
                    elif fmt in ("gemini_antigravity", "antigravity", "gemini"):
                        role, text = _extract_gemini_antigravity_text(entry)
                    elif fmt == "codex":
                        role, text = _extract_codex_text(entry)
                    elif fmt == "kimi":
                        role, text = _extract_kimi_text(entry)
                    else:
                        role, text = _extract_generic_text(
                            entry, role_field, text_field, text_block_type,
                            default_role)

                    if role is None or role not in roles:
                        continue

                    uuid_val = entry.get("uuid") or entry.get("turn_id")
                    if not uuid_val and isinstance(entry.get("payload"), dict):
                        uuid_val = entry["payload"].get("id") or entry["payload"].get("turn_id")
                    item_key = uuid_val if uuid_val else (f"step_{entry['step_index']}" if isinstance(entry, dict) and "step_index" in entry else f"L{line_no}")

                    session_val = entry.get("sessionId") or entry.get("session_id")
                    if not session_val and isinstance(entry.get("payload"), dict):
                        session_val = entry["payload"].get("id")
                    session = str(session_val) if session_val else file_path.stem

                    ts_val = entry.get("timestamp") or entry.get("created_at") or entry.get("ts")
                    if not ts_val and isinstance(entry.get("payload"), dict):
                        ts_val = entry["payload"].get("timestamp") or entry["payload"].get("started_at")
                    timestamp = str(ts_val) if ts_val is not None else ""

                    yield SourceItem(
                        key=f"{file_key}#{item_key}",
                        name=(f"observed/{source_id}/"
                              f"{_safe_key(file_key)}/{_safe_key(item_key)}"),
                        content=text,
                        tags=f"agent_transcript,{source_id},{role}",
                        meta={
                            "source_ref": {
                                "kind": "agent_transcripts",
                                "path": str(file_path),
                                "line": line_no,
                                "role": role,
                                "session": session,
                                "uuid": uuid_val,
                            },
                            "timestamp": timestamp,
                        },
                        fingerprint=hashlib.sha256(
                            text.encode("utf-8", "replace")
                        ).hexdigest()[:16],
                    )
        except OSError:
            continue

        state[file_key] = {
            "offset": last_good_offset,
            "mtime": stat.st_mtime,
            "size": stat.st_size,
            "line_no": line_no,
        }


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

ADAPTERS = {
    "markdown_dir": scan_markdown_dir,
    "remember_files": scan_remember_files,
    "sqlite_table": scan_sqlite_table,
    "agent_transcripts": scan_agent_transcripts,
}

VALID_KINDS = tuple(ADAPTERS)


def scan(source_id: str, config: Dict,
         state: Optional[Dict] = None) -> Iterator[SourceItem]:
    """Dispatches to the adapter named by config['kind'].

    `state` is only meaningful for (and only mutated by) adapters that
    need incremental byte-offset tracking; currently agent_transcripts.
    Other adapters ignore it -- they already skip unchanged items via
    per-item fingerprints (mtime+size, or a content hash).
    """
    kind = config.get("kind")
    adapter = ADAPTERS.get(kind)
    if adapter is None:
        raise ValueError(
            f"Unbekannte observe-source kind: {kind!r} "
            f"(gueltig: {', '.join(VALID_KINDS)})"
        )
    if kind == "agent_transcripts":
        yield from adapter(source_id, config, state=state)
    else:
        yield from adapter(source_id, config)


# ---------------------------------------------------------------------------
# Replica source templates (cross-host federation via Republica showcases)
# ---------------------------------------------------------------------------
#
# A separate transit-sync mechanism (outside this module) mirrors another
# host's USMC/Gardener databases into read-only snapshot files at
# ``~/.republica/<source-host>/<namespace>.sqlite`` (Republica showcases). These are
# ordinary foreign SQLite databases once they exist -- `sqlite_table`
# above is already the right adapter for them; nothing new needed to be
# built to READ one.
#
# What *is* new here: the standard config for one such replica, built
# from a host name, analogous to this machine's own usmc-facts /
# usmc-lessons / usmc-working / usmc-sessions sources (see the module's
# runtime config) -- just pointed at the replica snapshot instead of the
# local ``~/.usmc/usmc_memory.db``.
#
# Self-replica trap: a replica directory is named after the SOURCE host,
# and that same directory name equals the CURRENT host when the transit
# sync has (as designed) also mirrored this machine's own databases back
# to itself for verification. Indexing that one would feed a host's own
# user.db back into itself -- every entry appearing a second time under a
# new source_id. Both builders below refuse to build a config for the
# current host; the caller supplies a real *other* host's name.
#
# To arm a replica once a genuine other-host snapshot exists:
#
#   import sources
#   for source_id, cfg in sources.usmc_replica_source_configs("<OTHER-HOST>").items():
#       af.observe_source_add(source_id, "sqlite_table", **{**cfg, "enabled": True})
#
# Until that call is made, nothing runs: this module registers no source
# by itself, and the generated config's own ``enabled: False`` keeps it
# off even if a caller adds it as-is. Should a replica directory not
# exist yet (or vanish later, e.g. a stale sync), scan_sqlite_table's own
# ``db_file.is_file()`` guard (above) makes a refresh against it a silent
# no-op -- 0 indexed, 0 skipped, never an exception. That guard is what
# makes this safe to register ahead of the replica actually appearing.

def _current_host() -> str:
    """Best-effort current hostname, for the self-replica guard below.
    Prefers the Windows env var (set on every login shell); falls back to
    $HOSTNAME (Unix) and finally platform.node() if neither is set.
    """
    return (os.environ.get("COMPUTERNAME") or os.environ.get("HOSTNAME")
            or platform.node() or "")


def _replica_db_path(host: str, namespace: str, replicas_root=None) -> str:
    root = Path(replicas_root) if replicas_root else Path(
        os.path.expanduser("~/.republica"))
    return str(root / host / namespace)


def usmc_replica_source_configs(host: str, replicas_root=None) -> Dict[str, Dict]:
    """Standard sqlite_table configs for one host's replicated USMC
    database (facts/lessons/working/sessions) -- the four-table split
    mirrors this machine's own usmc-* sources exactly, just against
    ``<replicas_root>/<host>/usmc.sqlite`` instead of the local DB.
    Every returned config carries ``enabled: False``; the caller decides
    whether and when to arm it (see module docstring above).

    Raises ValueError if `host` is empty or names the CURRENT machine --
    see the self-replica trap explained above.
    """
    if not host or host == _current_host():
        raise ValueError(
            f"refusing to build a replica source config for the current "
            f"host ({host!r}) -- its own USMC replica of itself would "
            f"duplicate every fact/lesson/session under a second source_id"
        )
    db_path = _replica_db_path(host, "usmc.sqlite", replicas_root)
    base = {"db_path": db_path, "enabled": False}
    slug = host.lower()
    return {
        f"replica-{slug}-usmc-facts": {
            **base, "table": "usmc_facts",
            "columns": {"id": "id", "name": "key", "content": "value",
                        "tags": "category"},
        },
        f"replica-{slug}-usmc-lessons": {
            **base, "table": "usmc_lessons",
            "columns": {"id": "id", "name": "title",
                        "content": ["problem", "solution"], "tags": "category"},
        },
        f"replica-{slug}-usmc-working": {
            **base, "table": "usmc_working",
            "columns": {"id": "id", "content": "content", "tags": "tags"},
        },
        f"replica-{slug}-usmc-sessions": {
            **base, "table": "usmc_sessions",
            "columns": {"id": "id", "name": "current_task",
                        "content": "handoff_notes"},
        },
    }


def gardener_replica_source_config(host: str, replicas_root=None) -> Dict[str, Dict]:
    """Standard sqlite_table config for one host's replicated Gardener
    ``user.db`` (its single ``everything`` table), read like any other
    foreign source -- true federation: everything that host observed or
    put() becomes findable here too, under its own source_id.

    Same self-replica guard as `usmc_replica_source_configs`, and for the
    same reason it matters more here: this DB's ``everything`` table
    already contains every entry this module itself indexes (including
    everything from other observe-sources), so indexing your own host's
    replica of itself would double the entire database under one new
    name instead of duplicating a handful of rows.
    """
    if not host or host == _current_host():
        raise ValueError(
            f"refusing to build a replica source config for the current "
            f"host ({host!r}) -- its own user.db replica of itself would "
            f"duplicate the whole database under a second source_id"
        )
    db_path = _replica_db_path(host, "gardener-user.sqlite", replicas_root)
    return {
        f"replica-{host.lower()}-gardener": {
            "db_path": db_path, "enabled": False, "table": "everything",
            "columns": {"id": "id", "name": "name", "content": "content",
                        "tags": "tags"},
        },
    }
