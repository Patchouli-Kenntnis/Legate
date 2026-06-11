# Legate

Legate is an open-source autonomous coding and file-management agent built on OpenAI's chat models. It runs as an interactive command-line application: you give it a task, and a coordinator agent plans the work, calls tools (file I/O, bash, web search), delegates subtasks to worker subagents, and persists everything so conversations can be resumed later.

## Features

### Coordinator / subagent architecture
A primary agent (the coordinator) receives your task, maintains a plan, and can spawn **subagents** via the `create_subagent` tool. Each subagent runs in its own fresh context with a restricted tool set, completes a focused subtask, and returns only its final result — keeping the coordinator's context lean.

### Planner and notes
The coordinator maintains a shared todo list through the `update_planner` tool: it adds numbered steps, marks them complete or failed, and records free-form **notes** of key findings and decisions. The plan and notes are saved with the conversation and survive context compaction.

### Skills library
Reusable best-practice guides live in `app/skills/` and are cataloged in `SKILLS.toml` (Python debugging, web research, file management, bash scripting, technical writing). The catalog is injected into the system prompt; agents load a skill's full content on demand with the `read_skill` tool.

### Context compression cascade
Long-running tasks no longer die when the context window fills up. Legate applies a layered cascade modeled on Claude Code's design, cheapest layer first:

| Layer | Mechanism | Cost |
|---|---|---|
| 0 | Oversized tool outputs are spilled to disk (`out/`); only a head/tail preview plus the file path stays in context | free |
| 1 | Stale `[STATE]` messages are pruned; old tool outputs are batch-evicted (and archived) when the context crosses the limit | free |
| 2 | If the planner's notes are substantial, they become the compaction summary — no extra model call | free |
| 3 | Otherwise one summarization call produces a structured summary (request, decisions, results, files touched, errors, pending work) | 1 LLM call |

Evicted and compacted messages are archived to `conversations/<id>.archive.jsonl`, and the agent can search them at any time with the `read_history` tool (by substring or iteration range). Compression is batched and threshold-gated so the message prefix stays stable for prompt caching.

### Conversation persistence
Every iteration is saved to `conversations/<id>.json` (messages, agent state, planner, notes). Conversations can be listed, resumed with full state restored, or deleted from the CLI.

### Resource tracking
The agent receives a `[STATE]` message each iteration with its token usage, iteration count, and live context size, and is prompted to budget itself — wrapping up work before limits are hit.

### Built-in tools

| Tool | Available to | Purpose |
|---|---|---|
| `read_file` / `write_file` / `append_file` | all agents | File I/O (large reads are previewed, not dumped) |
| `run_bash` | all agents | Shell commands, 120 s timeout, large output spilled to disk |
| `web_search` | all agents | DuckDuckGo search |
| `read_skill` | all agents | Load a skill guide from the library |
| `create_subagent` | coordinator | Delegate a subtask to a fresh worker agent |
| `update_planner` | coordinator | Manage the plan and record notes |
| `read_history` | coordinator | Search archived (evicted/compacted) history |

## Requirements

- An OpenAI API key
- Python 3.12+ (for running locally), or Docker

## Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd Legate
   ```

2. **Configure the API key** — create a `.env` file in the project root:
   ```
   OPENAI_KEY=your_openai_api_key
   ```

3. **Run locally**
   ```bash
   pip install -r requirements.txt
   python app/main.py
   ```

   **Or run with Docker**
   ```bash
   docker build -t legate .
   docker run --env-file .env -it legate
   ```
   To keep conversations across container runs, mount the conversations directory:
   ```bash
   docker run --env-file .env -v "$(pwd)/conversations:/app/conversations" -it legate
   ```

## Using the CLI

Starting the app shows the main menu:

```
=== Legate ===
[N] New conversation
[L] List conversations
[S] Settings
[Q] Quit
```

### New conversation — `N`
Enter your task as a prompt. The agent loop starts immediately: each iteration prints the model's response, any tool activity, and a state line with token/iteration usage. The loop ends when the agent finishes (responds without tool calls), or when the token budget or iteration limit is reached. Progress is saved continuously, so an interrupted run loses nothing.

### List conversations — `L`
Shows all saved conversations with title, last-updated time, and tokens used. Then:

- **`<number>`** — resume that conversation: its messages, planner state, and notes are restored, and you are prompted for a follow-up message.
- **`D <number>`** — delete a conversation (with confirmation; also removes its history archive).
- **`B`** (or Enter) — back to the main menu.

### Settings — `S`

```
--- Settings ---
[1] Token budget                         150000  (-1 = unlimited)
[2] Max context size (tokens)            120000  (-1 = unlimited)
[3] Max iterations per run               32  (-1 = unlimited)
[4] Recent blocks kept verbatim          3
[5] Tool output spill threshold (chars)  16000
[B] Back
```

Enter a number, then the new value. Settings persist to `settings.json` in the project root and apply to new conversations (the spill threshold and compression knobs also apply immediately).

| Setting | Meaning |
|---|---|
| Token budget | Total token spend allowed per conversation; `-1` = unlimited |
| Max context size | Hard cap on the live context before compression kicks in; `-1` = bounded only by the model's window |
| Max iterations per run | Agent loop iterations per run; `-1` = unlimited |
| Recent blocks kept verbatim | How many recent iterations are never evicted or compacted |
| Spill threshold | Tool outputs larger than this many characters are spilled to disk |

### Quit — `Q`
Exit the program.

## Project layout

```
app/
  main.py            CLI menus (conversations, settings)
  agent.py           Primary and subagent loops
  context.py         Context-compression cascade helpers
  planner.py         Shared todo list + notes
  prompts.py         System prompts (skills catalog injected)
  persist.py         Pydantic models, conversation + archive storage
  settings.py        User settings (settings.json)
  config.py          Models, limits, compression defaults
  tools/             One module per tool (schema + handler)
  skills/            Skill guides + SKILLS.toml catalog
conversations/       Saved conversations and history archives (gitignored)
out/                 Spilled large tool outputs (gitignored)
tests/
  test_context.py    Offline checks for compression, settings, persistence
```

## Running the tests

The offline suite needs no API key:

```bash
python3 tests/test_context.py
```

## License

This project is licensed under the MIT License. See the LICENSE file for details.
