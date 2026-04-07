# Gardener — Design Document (2026-03-12)

**🇩🇪 [Deutsche Version](KONZEPT.md)**

> Status: Idea phase
> Author: Lukas Geiger + Claude

## Core Idea

An LLM-native operating system based on three pillars:

1. **Text** — Knowledge, instructions, references
2. **Context** — Tasks, memory, chat, state
3. **Execution** — Run code, directly or as blueprint

The only way to access everything: **Search**.

## Architecture

```
┌─────────────────────────────────────────────┐
│              ONE FILE (SQLite + FTS5)            │
│                                              │
│  ┌─────────┐  ┌─────────┐  ┌─────────────┐  │
│  │  TEXT    │  │ CONTEXT │  │    TOOLS    │  │
│  │ Knowledge│  │ Tasks   │  │ Code blocks │  │
│  │ Rules   │  │ Memory  │  │ Blueprints  │  │
│  │ Docs    │  │ Chat    │  │ Executable  │  │
│  │ Wiki    │  │ State   │  │ or template │  │
│  └────┬────┘  └────┬────┘  └──────┬──────┘  │
│       └────────────┼───────────────┘         │
│            ┌───────▼───────┐                 │
│            │    SEARCH     │                 │
│            │   (one API)   │                 │
│            └───────┬───────┘                 │
│            ┌───────▼───────┐                 │
│            │    RESULT     │                 │
│            │  Text: read   │                 │
│            │  Code: execute│                 │
│            │  Both: orient │                 │
│            └───────────────┘                 │
└─────────────────────────────────────────────┘
```

---

## Two Files, One Search

```
gardener.db          # System: Knowledge, tools, blueprints (versionable)
user.db              # User: Memory, tasks, receipts, personal data
```

Invisible to the LLM — SQLite ATTACH makes both transparently searchable:

```sql
ATTACH 'user.db' AS user;
-- find() searches both, the LLM notices no difference
```

| Advantage | Why |
|-----------|-----|
| **Update** | Replace gardener.db, user.db stays |
| **Reset** | Delete user.db = fresh start |
| **Privacy** | user.db never goes to Git |
| **Backup** | Only back up user.db (small, personal) |
| **Multi-User** | Everyone gets their own user.db, same system |

```python
find("taxes")           # searches both
put("my-receipt", ...)  # automatically lands in user.db
run("receipt-scanner")  # comes from gardener.db
```

---

## Filesystem Synchronization (Living Core)

### Core Principle: The Database Is the Truth

Files in the folder are not standalone storage — they are an
**input/output interface** to the human world. The DB is the
living core, the folder is a mirror.

### Input: .absorber/ → Database (Physical Interface)

The human places files in the `.absorber/` folder. On the next
`sync()` they are absorbed and removed from the folder.

```
User places file in the absorber:
  ~/gardener/.absorber/invoice.pdf

Next sync (gardener sync):
  → File is read (text extracted)
  → Entry in user.db: type='document', name='invoice.pdf'
  → File is REMOVED from .absorber/ (it now lives in the house)

User places file in the home folder (not .absorber):
  ~/gardener/documents/contract.docx
  → Only OBSERVED (text read, file stays)
  → No absorbing, no removal
```

**The absorber is the mailbox.** What gets put in disappears
into the house. What lies in the garden is just looked at.

### Output: .output/ (Materialization)

DB contents are NOT automatically materialized as files.
Only on explicit request do files appear in `.output/`.

```python
# LLM creates a report and materializes it
put("tax-report-2025",
    content="# Tax Report 2025\n...",
    type="export",
    meta={"filename": "Tax_Report_2025.pdf"})

materialize("tax-report-2025")
# → ~/gardener/.output/Tax_Report_2025.pdf appears
```

### Sync Modes (config.json)

```json
{
  "mode": "selective"
}
```

| Mode | Behavior |
|------|----------|
| **selective** (Default) | Only `.absorber/` is absorbed, rest observed |
| **always_absorb** | EVERYTHING in the home folder is absorbed + removed |
| **observe_only** | Nothing absorbed, everything just observed |

`selective` is the recommended mode. `always_absorb` turns the system
into a pure store — everything that comes in disappears into the DB.

### Philosophy: Both Worlds Are Real

Files and database are not master and mirror — they are
**two equal realities** kept in sync.

**For the human:**
Files are the human equivalent of books and texts. That's how
we've structured knowledge for centuries. A file is something
tangible — formerly real paper, today an icon in the explorer. What
you see is what you get. When I move a file, I need it elsewhere.
When I delete it, I want it gone and to SEE that.

**For the LLM:**
The database is home. The context window is the format —
text must land here, regardless of its format outside. The LLM
needs no folder structure, no file extensions, no paths. It
needs: searchable text, executable code, and context.

**The difference in purpose:**

| Who | View of the DB |
|-----|---------------|
| LLM | My house. I live and work here. Everything happening outside, I see through my window (Sync IN). |
| User | My storage. I keep things safe here. And I can look inside (DB viewer). |

When the LLM builds something for the human, it must be **materialized**
— as a file, as something tangible. But not everything the LLM
thinks and stores internally needs to become a file.

### Persistence Layers

```
┌─────────────────────────────────────────────────┐
│  LAYER 1: Folder (human reality)                │
│  Files the user sees and touches.                │
│  Move, rename, delete = real.                    │
│  → Sync IN: automatically into DB                │
│  → Sync OUT: only when LLM materializes           │
├─────────────────────────────────────────────────┤
│  LAYER 2: user.db (shared storage)               │
│  For user: safekeeping, archive, security.        │
│  For LLM: context, memory, working memory.        │
│  Access: DB viewer (human) or find() (LLM).       │
│  → Backup: only this file                         │
├─────────────────────────────────────────────────┤
│  LAYER 3: gardener.db (system core)               │
│  Knowledge, tools, blueprints.                    │
│  Survives everything. Respawns deleted files.     │
│  → Versioned, updatable                           │
└─────────────────────────────────────────────────┘
```

### Transporter Buffer (Absorb / Materialize)

Inspired by Star Trek's pattern buffer: files can be beamed between the
physical world (folder) and the database. There are only **two operations**:
Absorb (in) and Materialize (out).

```
ABSORB (File → DB)
  Manual:     absorb("/path/to/file.pdf")
  Physical:   Place file in .absorber/ → sync()
  Mode:       always_absorb → everything is automatically absorbed

MATERIALIZE (DB → File)
  LLM:        materialize("tax-report-2025")
  →           File appears in .output/, ready to open/email
```

**No separate "dematerialize".** Absorb IS dematerialization.
The human places the file in `.absorber/`, it disappears into the DB.
Want it back: `materialize()` places it in `.output/`.

**Rules for storage:**

- **Absorbed files** remain in user.db until explicitly deleted
- **Binary files** (PDF, images): as BLOB + extracted text
- **Large files** (>50MB): only index in DB, file on the heap (blobs/)
- **Thresholds** configurable (default: 1MB inline, 50MB heap)

### Sync Mechanism

```
┌──────────────────┐                    ┌──────────┐
│  .absorber/      │ ──── absorb ────→  │          │
│  (mailbox)       │   (file → DB)     │          │
├──────────────────┤                    │    DB    │
│  .output/        │ ←── materialize ── │  (house) │
│  (output)        │   (DB → file)     │          │
├──────────────────┤                    │          │
│  ~/gardener/     │ ──── observe ───→  │          │
│  (garden)        │   (read only)     │          │
└──────────────────┘                    └──────────┘

Sync points:
  - Manual: gardener sync (recommended)
  - Filesystem watcher (watchdog) for real-time (later)
  - Periodic scan (every X seconds, later)
```

### Self-Healing (Respawn) — Later

Important system documents (knowledge, tools) are stored in gardener.db.
If they are deleted from the folder, they can be re-materialized at any time.
Automatic respawn logic is planned for later.

For now: `materialize("receipt-scanner")` restores a deleted file.
The DB is the truth, not the folder.

### DB Viewer — Ported from BACH

The DB viewer will be ported from BACH (BACH's GUI server already has
search, browse, edit for SQLite databases). Gardener only needs
a customized view that uses `everything` + `everything_fts`.

---

## Data Model

### Core Table (90% of All Data)

```sql
CREATE TABLE everything (
    id INTEGER PRIMARY KEY,
    type TEXT,        -- 'knowledge', 'tool', 'task', 'memory', 'config',
                      --  'session', 'document', 'export'
    name TEXT,        -- Unique name
    content TEXT,     -- Markdown with optional code blocks
    tags TEXT,        -- Comma-separated, for filtering
    meta TEXT,        -- JSON for structured data
    pinned INTEGER DEFAULT 0,  -- 1 = pinned, survives sync
    updated TEXT      -- Timestamp
);

CREATE VIRTUAL TABLE everything_fts USING fts5(name, content, tags);
```

### Optional Specialized Tables (Only When Structure Is Needed)

```sql
-- Example: When 50 tax receipts need to be compared
CREATE TABLE tax_receipts (
    id INTEGER PRIMARY KEY,
    amount REAL,
    date TEXT,
    category TEXT,
    deductible INTEGER,
    everything_id INTEGER REFERENCES everything(id)
);
```

Specialized tables are only created when meta JSON fields are no longer
sufficient. They always reference back to everything (foreign key).

### Meta Table (Shelf Describes Itself)

```sql
CREATE TABLE shelves (
    name TEXT PRIMARY KEY,    -- 'tax_receipts'
    description TEXT,         -- 'Structured tax receipts'
    schema TEXT,              -- JSON: expected columns + types
    created TEXT
);
```

---

## API — Four Functions

```python
find("taxes")                           # Search (both: gardener.db + user.db)
get("tax-return")                       # Read one entry
put("name", content="...", type="tool") # Write (auto: user.db or gardener.db)
run("receipt-scanner", input={...})     # Execute code block
```

---

## Tool Format

A tool is simultaneously documentation, blueprint, and executable:

```markdown
---
name: receipt-scanner
type: tool
tags: tax, ocr, document
---

# Receipt Scanner

Scans receipts and extracts amount, date, category.

## Code

    ```python
    def execute(input):
        path = input["path"]
        text = ocr_engine.scan(path)
        return {"amount": ..., "date": ..., "category": ...}
    ```
```

---

## LLM Workflow

```
User: "I have an invoice"
LLM:
  1. find("invoice receipt capture")
  2. Result: receipt-scanner (tool), tax-workflow (knowledge)
  3. run("receipt-scanner", input={"path": "..."})
  4. put("receipt-2026-03-12", type="memory", ...)
```

---

## Comparison with BACH

| BACH (138 tables) | Gardener |
|-------------------|---------|
| Handlers in hub/ | Code block in the entry |
| SKILL.md in filesystem | Entry of type tool |
| Help in docs/help/ | Entry of type knowledge |
| Memory in 5 tables | Entry of type memory |
| bach_api with 14 modules | find, get, put, run |
| Files = truth, DB = reflection | Both worlds are real, DB = house |
| CLI + API + GUI | Search + viewer + sync |
| Folder structure is architecture | Folder = garden, DB = house |
| Files always stay files | Files can be dematerialized |

---

## Metaphors

### Bookshelf

- **BACH:** Locked bookshelf with a key. Catalog (DB) describes
  books (files). If you want a book you need the key.

- **Gardener:** Two rooms, one shelf between them. The human sees books
  (files) they can touch. The LLM sees text (DB) that it searches.
  The shelf synchronizes both sides.

### Star Trek Transporter

Files exist in two states:
- **Materialized:** As a file in the folder. Tangible, visible, editable.
- **Dematerialized:** As a pattern in the DB. Invisible, but complete.

The user can switch between both states at any time.
The LLM preferably works with the pattern (DB), materializing only when
the human needs something tangible.

### The Sketchboard Model

The LLM is not IN the house. **The LLM IS the house** — its
context window is the living space where thinking happens, like a
sketchboard that gets written on and wiped clean.

The DB is the **photo album** — snapshots and notes that
survive when the sketchboard is wiped. `put()` takes a
photo of the current thought. `recall()` looks at old photos.

```
ME (Context Window)        MEMORY (DB)               OUTSIDE (World)
The sketchboard            The photo album            Files, folders
Living thought             What I remember            Network, APIs
Everything originates here put() = take photo         Hardware, processes
Deleted after session      recall() = remember
                           find() = browse

                SKIN (Tools in between)
                observe() = Eyes (see what's outside)
                text-stats = Touch (probe before grasping)
                absorb() = Mouth (ingest foreign text)
                materialize() = Voice (output results)
                shell, http = Hands (work outside)
```

**Text outside is not the same as text in the DB.** In the DB
it's integrated, searchable, weighted — part of my memory.
Outside it's raw and foreign. The skin tools help decide
what should go into memory and what can stay outside.

---

## Resolved Design Decisions

### 1. The DB as Workshop (Not Just Storage)

The LLM is not just text — it's also **text generation**. When it
writes code, it doesn't have to write directly to a file (= working
outside). It writes in the house first:

```python
# Design in the house
put("api-server", type="tool", content="```python\ndef execute(input):...")

# Iterate in the house (as often as needed)
put("api-server", content="[improved version]")

# When the code needs to run
run("api-server", input={...})
  → Code is materialized into temporary workspace
  → Executed as normal Python script (no exec())
  → Result back into DB
  → Workspace stays or gets cleaned up

# When the human needs the file
materialize("api-server")  → .output/api-server.py
```

This applies to EVERYTHING the LLM produces — code, reports,
configurations. Everything originates in the house, gets refined there,
and only goes outside when it's needed.

**Advantage:** Drafts are searchable (`find("api")`), revisable
(`put()` overwrites), and stay in context until they're done.

### 2. Sync Conflicts

There are no conflicts, because there are **three different relationships**
between the LLM and files:

**a) Files in front of the house (observe only):**
The user places a Word file in the folder. The LLM sees it through
its window — it only gets the extracted text, not the file itself.
No conflict possible: the file belongs to the user, the LLM just reads along.

```
~/gardener/documents/contract.docx
  → DB gets: name='contract.docx', content=[extracted text],
    meta={"path": "documents/contract.docx", "observed": true}
  → The .docx is NOT copied into the DB
  → User modifies the file → next sync updates the text
```

**b) Pulling files into the house (absorb):**
User says "save that" or LLM needs the file for editing.
The file is absorbed — it now lives IN the DB.

```
User: "Pull in that contract"
  → DB gets: content=[complete content], BLOB=[original file],
    meta={"absorbed": true}
  → File in folder can now be removed (or stays as a copy)
  → Editing happens in the DB or in the workspace
```

**c) Editing files directly in front of the house:**
The LLM edits a file in the folder (like today). The sync
automatically updates what the LLM sees through its window.

```
LLM edits ~/gardener/documents/report.md
  → File changes
  → Sync updates the DB entry
  → No conflict: the file is the truth for observed files
```

**Summary:**
- Observed files: file always wins (LLM only reads)
- Absorbed files: DB always wins (file is just a copy/export)
- No state where both claim to be the truth simultaneously

### 3. SQLite + Cloud Sync (OneDrive Problem)

The database lives **locally** (app folder), not in the cloud sync folder.

```
C:\Users\User\AppData\Local\Gardener\     ← DB lives here (local)
  gardener.db
  user.db
  blobs/                                  ← Large files (heap)

~/gardener/                                ← Folder lives here (OneDrive ok)
  .absorber/                              ← Mailbox (files → DB)
  .output/                                ← Output (DB → files)
  documents/                              ← Observed files
```

The Gardener folder (that the user sees) can live in OneDrive —
no problem, they're just normal files. The DB lives locally, no
cloud sync conflict possible.

If multi-device is desired: a small redirect file in the folder
(`gardener.pointer`) points to the local DB. Or: DB export/import
as sync mechanism (not live sync of the DB itself).

### 4. Large Files (BLOB Problem)

Large files are not stuffed into the DB. Instead: **heap**.

```
User: "Store this 500MB video"

DB gets:
  name='vacation-video.mp4'
  type='archive'
  content=[none — too large for text extraction]
  meta={"size": 524288000, "mimetype": "video/mp4",
        "blob_path": "blobs/a7f3b2c1.mp4",
        "original_name": "vacation-video.mp4"}

File lands on the heap:
  AppData/Local/Gardener/blobs/a7f3b2c1.mp4

For the user it looks like the file was pulled into the DB.
It's gone from the folder. Want it back:
  → Rematerialization fetches it from the heap
```

**Thresholds:**
- < 1MB: Directly as BLOB in DB (texts, small images)
- 1-50MB: BLOB in DB, but with warning
- > 50MB: Only index in DB, file on heap
- Configurable per installation

---

## Memory: No Separate Memory System (Design Decision)

### What BACH Has (and Why Gardener Does It Differently)

BACH has 5 cognitive memory types in **separate tables**:
- memory_working (short-term memory)
- memory_sessions (episodic memory)
- memory_facts (semantic memory)
- memory_lessons (procedural memory)
- context_triggers (associative memory)

Plus: consolidation pipeline with 6 stages, daemon jobs, trigger generation,
350+ tracking entries, reclassification, etc.

**Gardener does all of this with the single `everything` table.**

### Gardener Memory = Types + Meta Fields

| BACH Table | Gardener Type | Difference |
|-----------|--------------|------------|
| memory_working | `type='memory'` | Same, but in everything |
| memory_sessions | `type='session'` | Same, but in everything |
| memory_facts | `type='knowledge'` | Facts ARE knowledge |
| memory_lessons | `type='lesson'` | Same, but in everything |
| context_triggers | **the search itself** | FTS5 IS the association |

The trick: **The search IS the associative memory.** When I
`find("taxes")`, I find knowledge, tools, tasks, memos, lessons, and
sessions simultaneously. No trigger table needed.

### Weighting, Decay, and Boost

Instead of a separate `memory_consolidation` table, Gardener uses the
`meta` field:

```json
{
  "weight": 0.8,
  "decay_rate": 0.95,
  "accessed": 5,
  "last_accessed": "2026-03-12T05:30:00",
  "severity": "high"
}
```

- **Decay**: On each consolidation: `weight *= decay_rate`
- **Boost**: On each retrieval via `recall()`: `weight += 0.1`
- **Forget**: Entries with `weight < 0.05` are deleted

### Memory API

```python
af = Gardener()

# Working memory (short-lived, decays fast)
af.memo("Important observation about taxes")

# Lesson (long-lived, decays slowly)
af.lesson("SQLite-WAL", "Always activate WAL mode", severity="high")

# Session report (episodic)
af.session_end("TOPIC: Memory implemented. NEXT: Testing.")

# Remember (searches + boosts weight)
af.recall("taxes")  # Finds memos + lessons + sessions

# Consolidate (= sleep)
af.consolidate()  # Decay + Forget
```

### Consolidation: Sleep Instead of Pipeline

BACH's consolidation has 6 stages, daemon jobs, and multiple workflows.
Gardener has **one method**: `consolidate()`.

```
consolidate() does:
  1. Decay: Reduce weight of all memory entries
  2. Forget: Delete entries below 0.05
  3. Done.
```

No pipeline, no daemon, no reclassification. When the LLM
retrieves a note often (`recall()`), its weight rises (boost).
When it doesn't, it drops (decay). Just like the real brain.

### What Is Deliberately NOT Adopted

| BACH Feature | Why Not |
|-------------|--------|
| context_triggers (900+) | FTS5 search IS the association |
| Trigger generation | Not needed without trigger table |
| Reclassify | Changing type = simply `put()` with new type |
| Confidence system | Weight is enough, confidence is overengineering |
| Daemon jobs | `consolidate()` at session end is enough |
| 6-stage pipeline | Decay + forget is enough |

### CLI

```bash
gardener memo <text>            Note to working memory
gardener lesson <title> [text]  Store lesson
gardener recall <query>         Remember (with boost)
gardener consolidate            Consolidate memory
gardener session-end <text>     Store session report
```

### Decay Rates by Type

| Type | decay_rate | Meaning |
|------|-----------|---------|
| memory | 0.95 | Decays fast (5% per consolidation) |
| session | 0.97 | Decays medium (3% per consolidation) |
| lesson | 0.99 | Barely decays (1% per consolidation) |
| knowledge | - | Never decays (no decay) |
| tool | - | Never decays (no decay) |

---

## Tasks: No Separate System (Design Decision)

Tasks are **not their own component** — they are entries of type `task` in
the `everything` table. This is intentional and a core principle of Gardener.

### Why No Task System?

A separate task system would contradict the core idea. Gardener has
**one** search and **one** table. When I search for "taxes", I find:
- The knowledge about the tax return (knowledge)
- The receipt scanner (tool)
- The open task "submit tax return" (task)
- The saved last tax assessment (document)

All in one result. A separate task system would destroy this advantage.

### Task API (Convenience Methods)

```python
af = Gardener()

# Create task
af.task("taxes-2025", content="Submit tax return",
        priority="high", due="2026-05-31")

# List tasks
af.tasks()                    # all
af.tasks(status="open")       # open only

# Change status
af.task_status("taxes-2025", "doing")
af.task_done("taxes-2025")

# Also possible directly via put():
af.put("taxes-2025", type="task", content="...",
       meta={"status": "open", "priority": "high"})
```

### CLI

```bash
gardener task <name> [description]     # Create task
gardener tasks [status]                # List tasks
gardener done <name>                   # Mark done
```

### Task Status Values

| Status | Meaning |
|--------|---------|
| open | Not yet started |
| doing | In progress |
| done | Completed |
| blocked | Blocked |
| waiting | Waiting for something/someone |

### Materialization for Humans

Anyone wanting to see tasks as a file materializes them:

```python
# Task overview as file
tasks = af.tasks(status="open")
content = "# Open Tasks\n\n"
for t in tasks:
    m = t.get("meta", {})
    content += f"- [ ] **{t['name']}** ({m.get('priority', 'normal')})\n"
    if t.get("content"):
        content += f"  {t['content']}\n"

af.put("task-overview", content=content, type="export",
       meta={"filename": "tasks.md"})
af.materialize("task-overview")
# → .output/tasks.md appears
```

The truth remains in the DB. The file is just a snapshot for human eyes.

---

## Open Questions (2026-03-12)

### Resolved
- ~~Files vs. database?~~ → DB as core, folder as interface
- ~~One table or dynamic?~~ → One core table + optional specialized tables
- ~~User data separated?~~ → Yes: gardener.db + user.db, transparent via ATTACH
- ~~Git disadvantage?~~ → DB lives locally, folder can be in Git/cloud
- ~~Code sandbox?~~ → Workspace materialization instead of exec()
- ~~Sync conflicts?~~ → Three relationship types: observe / absorb / direct edit
- ~~Cloud sync?~~ → DB local, folder in cloud. No SQLite-over-OneDrive
- ~~Large files?~~ → Heap (local blob folder) + index in DB
- ~~Input/output?~~ → .absorber/ (mailbox) + .output/ (output)
- ~~Sync modes?~~ → config.json: selective / always_absorb / observe_only
- ~~Task system?~~ → No separate system, tasks = type='task' in everything
- ~~Memory system?~~ → No separate system, memory/lessons/sessions = types in everything
- ~~Dematerialize?~~ → Doesn't exist separately, absorb() IS dematerialization
- ~~Consolidation?~~ → Simple: decay + forget, no pipeline
- ~~DB viewer?~~ → Will be ported from BACH
- ~~Specialized tables?~~ → Fill up when porting skills/tools from BACH
- ~~Self-healing?~~ → Later; important data is safe in DB, materialize() is enough

### Open
- How does versioning work within the DB (change history)?
- Is a permissions model needed (who can change what in gardener.db)?
- Evolution of BACH (v4) or standalone project?
- How does Gardener interact with external tools (MCP, APIs, shell)?
- How is the workspace folder managed (cleanup, max size)?
