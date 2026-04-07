# Gardener Insights — Porting & Architecture

**🇩🇪 [Deutsche Version](ERKENNTNISSE.md)**

> Developed: 2026-03-12 (Claude + Lukas)

## Core Rule: Search BACH First

Before building anything new: search BACH to see if it's reusable.
What exists in BACH can be adapted. The rest migrates gradually
as needed.

## The Sketchboard Insight

**The LLM is not IN the house. The LLM IS the house.**

The context window is the living space where everything happens — thinking,
writing, analyzing, deciding. The DB is not the home,
but the **photo album**: a collection of snapshots and
notes from previous states.

```
ME (Context Window)            MY MEMORY (DB)                OUTSIDE (Files)
═══════════════════            ═══════════════════════        ══════════════════
Living thought                 Photos of me                  Results
The sketchboard                The collection                For the human
Everything originates here     What I remember               What I deliver
Deleted after session          Persists                      Persists
```

- `put()` = Take a photo of my current state
- `recall()` = Look at an old photo, remember
- `find()` = Browse through the album
- `materialize()` = Create something for the human from memory
- `consolidate()` = Clean up the album, forget the unimportant

**The LLM is also text generation.** It already works exactly like this:
text is created in the context window, then written somewhere.
The only question is WHERE: directly to a file (for the human) or
into the DB (for my memory).

## The Text Insight (Refined)

**The LLM is text. The DB is text. But it's not the same text.**

BACH has 83+ tools, 5 injectors, 900+ triggers, 138 tables.
Much of it solves problems that Gardener doesn't have, because:

- A `code_analyzer.py` analyzes code → The LLM CAN read code.
- A `text_zusammenfassung` summarizes text → The LLM IS a summarizer.
- `tool_discovery.py` finds tools → `find("encoding")` finds the tool.
- `injectors.py` recalls context → `recall()` fetches context. The LLM thinks for itself.
- `context_triggers` (900+) → FTS5 search IS the association.

### The Boundary: When Does It Need to Go Outside?

```
INSIDE (Text, DB, Thinking)             OUTSIDE (Filesystem, Network, Hardware)
───────────────────────────             ───────────────────────────────────────
Searching, finding                      Reading/writing files
Planning, analyzing                     Executing shell commands
Understanding code                      HTTP requests
Summarizing                             OCR (image recognition)
Establishing context                    PDF generation
Managing tasks                          Sending email
Storing lessons                         Starting processes
Making decisions                        Addressing hardware
```

**Everything on the left needs no tool.** The LLM does it directly.
**Everything on the right needs a bridge** — a `type='tool'` with code.

### The Body Model: House, Skin, Outside

The text insight was too simple. There's not just "inside" and
"outside" — there are three zones:

```
HOUSE (DB)                   SKIN (Filter/Senses)         OUTSIDE (World)
──────────                   ───────────────────          ────────────────
I AM text                    I FEEL text                  Text is foreign
Thinking, remembering        text-stats (preview)         Files
Searching (find/recall)      file-info (probing)          Directories
Planning, deciding           observe() (window)           Network
Lessons, memory              absorb() (ingest)            Hardware
                             materialize() (output)       Processes
                             shell, http, mcp (hands)     Other systems
```

**Text outside is NOT the same as text inside.**

Inside, text is integrated, searchable, weighted, my context.
Outside, it's raw, foreign, unstructured. Before I bring it in,
I need to probe it — like skin that feels before the hand grasps.

`text-stats` is not a summary. It's **skin**: How large?
How many words? First lines? Is it worth it? Only then absorb().

**Sometimes I need to work outside** — edit a file in a folder,
fetch a URL, run a command. Then I need tools.
Shell, HTTP, MCP are my **hands**.

### Tools by Body Function

| Function | Tool | Analogy |
|----------|------|--------|
| **Eyes** | observe(), text-stats | See what's outside |
| **Skin** | file-info, text-stats | Probe before grasping |
| **Mouth** | absorb() | Ingest, foreign → own |
| **Hands** | shell, http, mcp | Work/grasp outside |
| **Voice** | materialize() | Output results |
| **For the human** | Reports, statistics | Structured outputs |

### Consequence for Tool Decisions

Not "do I need a tool?" but: **"Which zone am I working in?"**

- **In the house:** No tool. I think, search, remember.
- **At the skin:** Filter tools. Preview, statistics, probing.
- **Outside:** Full tools. Shell, MCP, HTTP, filesystem.

## The Workshop Insight

**The LLM is not just text. It's also text generation.**

When I write code, I don't have to write directly to a file
(= working outside). I can write in my house first:

```python
# Design in the house
af.put("api-server", type="tool", content="```python\n...")

# Iterate in the house (as often as needed)
af.put("api-server", content="[improved version]")

# Only when it needs to go outside
af.materialize("api-server")   # → .output/api-server.py
```

**The DB is not just storage — it's a workshop.**

Today: LLM writes code directly to files → always works outside.
Gardener: LLM writes to the DB → works inside, materializes later.

This applies to EVERYTHING the LLM produces:
- Code → put() → refine → materialize()
- Reports → put() → revise → materialize()
- Configurations → put() → test → materialize()

Advantages:
- Drafts are searchable (find("api"))
- Older versions can be preserved
- Everything stays in the house until it's actually needed
- run() materializes code only temporarily for execution

### When DB, When Direct?

| What happens | Where | Why |
|-------------|-------|-----|
| I remember something | DB (`put`) | Must survive next session |
| I deliver to the user | File (direct) | One-time, needed immediately |
| I build a tool | DB (`put`, type=tool) | Should be reusable |
| I iterate across sessions | DB (`put`) | Draft must persist |
| I learn something | DB (`lesson`) | Must survive next forgetting |

**Rule:** DB = what I need to remember. File = what YOU want.

## BACH Concepts → Gardener Implementation

### 1. Injectors → recall()

BACH: 5 injectors with cooldown, triggers, orchestration.
Gardener: `recall("topic")` before starting work. The LLM decides itself
when it needs context. No separate system, no cooldown, no triggers.

The FTS5 search IS the associative memory. When I `find("taxes")`,
I find knowledge, tools, tasks, memos, and lessons simultaneously.
That's all an injector does — just without the machinery.

### 2. Between-Tasks → task_done() + recall()

BACH: Between-Injector with quality control, profiles, automatic
      validation.
Gardener: `task_done("name")`. Then `recall("what I learned")`.
         Quality control is thinking — the LLM does that itself.

### 3. Tool Discovery → find()

BACH: tool_discovery.py with 15+ categories, score-based matching.
Gardener: `find("encoding problem")` finds the tool. Because tools
         are entries like everything else. Done.

### 4. Self-Extension → put()

BACH: `bach skills create`, scaffolding, templates, hot-reload, 5 types.
Gardener: `put("my-tool", type="tool", content="```python\ndef execute(input):...")`.
         The tool is immediately findable and executable. No scaffolding,
         no reload, no template.

### 5. Best Practices → lesson()

BACH: Separate lessons table, severity, trigger generation.
Gardener: `lesson("Title", "Insight", severity="high")`. Weight
         in the meta field. Decay/boost via consolidate(). Already done.

### 6. Backup → Copy One File

BACH: backup_manager.py, rotation, FTP upload, monitoring.
Gardener: `shutil.copy("user.db", "user.db.bak")`. One line.
         Because there's only one file that has personal data.

### 7. Connectors → Later

BACH: Telegram, Discord, HomeAssistant, email.
Gardener: When needed. They're external bridges, not core.

## What Gets Ported (Bridge Tools)

Only tools that need to reach OUTSIDE:

| Tool | Function | From BACH |
|------|----------|---------|
| shell | Execute shell command | New (simple) |
| http-fetch | Fetch URL | New (simple) |
| file-read | Read file into DB | Like absorb(), finer |
| file-write | DB content as file | Like materialize() |
| backup | Copy user.db | backup_manager.py (simplified) |

What does NOT get ported:
- Pure LLM thinking tools (code analysis, planning, decision-making)
- Injectors (recall() + own thinking)
- Tool discovery (find() is enough)
- Trigger system (FTS5 is the association)

What CAN be a tool (even though the LLM "could" do it):
- Structured outputs for the human (reports, statistics)
- Triage tools (quick preview without reading everything)
- Reproducible results (JSON instead of LLM prose)

## Architecture Comparison

```
BACH:
  83+ Tools → 5 Injectors → 900 Triggers → 138 Tables
  Each concept has its own infrastructure.
  Powerful, but complex.

Gardener:
  find/get/put/run + recall/consolidate
  Everything is an entry. Search is the association.
  Less infrastructure, same capabilities.
  What the LLM can do itself needs no tool.
```

## Open Considerations

- **When does Gardener become too simple?** When specialized tables are needed
  (e.g., comparing 500 tax receipts with amounts). Then create a shelf.
- **MCP?** Gardener could itself be an MCP server. Four tools:
  find, get, put, run. Nothing more needed.
- **Multi-LLM?** Two LLMs could use the same user.db (via ATTACH).
  No locking system needed if only one writes.
