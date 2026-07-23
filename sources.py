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
                tags=f"{kind_tag},{source_id}",
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
    """
    db_path = os.path.expanduser(str(config.get("db_path", "")))
    table = str(config.get("table", ""))
    columns = config.get("columns") or {}
    if not db_path or not table or "content" not in columns:
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
        content_col = columns.get("content")
        tags_col = columns.get("tags")

        select_cols = ["rowid"]
        for col in (id_col, name_col, content_col, tags_col):
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
        content = row[col_pos[content_col]] if content_col else ""
        content = "" if content is None else str(content)
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
                           text_block_type: str):
    """Generic dotted-path role/text extraction for JSONL transcript
    formats other than Claude Code's. `text_field` may point at a
    plain string, or a list of blocks (extracts blocks whose 'type'
    equals `text_block_type`, concatenated).
    """
    role = _dig(entry, role_field)
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


def scan_agent_transcripts(source_id: str, config: Dict,
                            state: Optional[Dict] = None) -> Iterator[SourceItem]:
    """JSONL chat-transcript files, indexed line by line, text turns only.

    config:
        path: glob pattern for the JSONL files (e.g.
              '~/.claude/projects/*/**/*.jsonl'); '**' is recursive.
        format: 'claude_code' (default, built-in field mapping) or
              'generic' (uses role_field/text_field below).
        roles: which roles to index (default: ["user", "assistant"]).
        include_sidechain: index Claude Code sub-agent sidechain turns
              too (default: False -- only the main conversation).
        role_field / text_field: dotted paths into each JSON line,
              only used when format == 'generic'
              (default 'message.role' / 'message.content').
        text_block_type: block 'type' to extract when text_field
              resolves to a list of blocks (default 'text').

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
                    else:
                        role, text = _extract_generic_text(
                            entry, role_field, text_field, text_block_type)

                    if role is None or role not in roles:
                        continue

                    item_key = entry.get("uuid") or f"L{line_no}"
                    session = entry.get("sessionId", file_path.stem)
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
                                "uuid": entry.get("uuid"),
                            },
                            "timestamp": entry.get("timestamp", ""),
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
