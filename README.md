# Mini Codex

A local-first, terminal-based AI coding agent powered by **Groq**. It inspects a
Python project, diagnoses a bug from real source evidence, prepares a minimal
patch, asks **you** to approve the exact diff, applies the change only on
approval, and then runs the project's tests.

The LLM chooses among registered tools; Python executes them and enforces every
safety rule. No source file is edited without explicit human approval.

## How it works

The agent runs a bounded loop:

```
search_codebase -> search_in_file -> read_file      # gather evidence
        -> propose_edit                             # prepare patch (no write)
        -> request_approval_and_apply               # human decides (y/N)
        -> run_tests                                # verify the fix
        -> final report
```

Tools:

| Tool | Purpose |
| --- | --- |
| `search_codebase` | Find files/lines matching a term across the project. |
| `search_in_file` | Search inside one file (literal or regex) with context. |
| `read_file` | Read an exact line range with line numbers. |
| `propose_edit` | Prepare a minimal patch; **does not modify the file**. |
| `request_approval_and_apply` | Show the diff and apply only if the human approves. |
| `run_tests` | Run the project's predefined `pytest` command (no arbitrary shell). |

## Requirements

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) (recommended) or `pip`
- A Groq API key and a tool-calling model (default `openai/gpt-oss-120b`)

## Setup

### With uv (recommended)

```powershell
# Windows (PowerShell)
uv sync --extra dev
Copy-Item .env.example .env      # then edit .env and add GROQ_API_KEY
```

```bash
# macOS / Linux
uv sync --extra dev
cp .env.example .env             # then edit .env and add GROQ_API_KEY
```

### With pip

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1          # Windows PowerShell
# source .venv/bin/activate           # macOS / Linux
pip install -e ".[dev]"
Copy-Item .env.example .env
```

### Configuration

`.env` (never committed -- see `.gitignore`):

```dotenv
GROQ_API_KEY=your_real_key
GROQ_MODEL=openai/gpt-oss-120b
MAX_AGENT_TURNS=20
MAX_TOOL_CALLS=40
TOOL_TIMEOUT_SECONDS=30
TEST_TIMEOUT_SECONDS=120
```

The loader checks the current directory for `.env`, then walks up through parent
directories, so a key kept at a repository root works from nested folders.
Real environment variables always win over `.env` values.

## Usage

There is a small deliberately-buggy target project in `sample_project/` so you
can try the agent immediately.

```powershell
# Windows
uv run mini-codex --project .\sample_project
```

```bash
# macOS / Linux
uv run mini-codex --project ./sample_project
```

You will be prompted for the issue, e.g.:

```
Describe the issue:
The discount calculation is incorrect. Find the bug and fix it.
```

The agent investigates, shows the diff, and asks:

```
Apply this change? [y/N]:
```

Answer `y` to apply (then it runs the tests) or `n` to reject. Empty input
counts as rejection.

Non-interactive (pass the task on the command line):

```powershell
uv run mini-codex --project .\sample_project --task "cart total omits the last item; fix and test it"
```

Other flags: `--model`, `--max-turns`, `--max-tool-calls`.

If you prefer not to install, a thin launcher exists: `python main.py --project .\sample_project`.

## Safety model

- Every path is resolved and confined to `--project`; traversal and absolute
  paths are rejected, and symlinks that escape the root are refused.
- Secret-like files (`.env`, keys, credentials) and dependency/build folders
  (`.git`, `.venv`, `node_modules`, ...) are never searched or read.
- `propose_edit` requires an exact, **unique** match and never writes the file.
- On approval the source fingerprint is re-checked; stale patches are refused.
- Writes are atomic and a recovery copy is kept in
  `.mini_codex_backups/<task>/`.
- Rejected or unapproved patches leave files byte-for-byte unchanged.
- The test runner uses a fixed `pytest` command with timeouts and bounded
  output; the model cannot supply shell commands.
- Repository content is treated as untrusted; the model cannot approve on the
  user's behalf and cannot read secrets.

## Testing

```bash
uv run pytest                       # full suite (unit, integration, e2e)
uv run pytest sample_project        # show the bugs the agent is meant to fix
```

The suite covers path confinement, secret filtering, patch validation, the
approval and rejection flows, stale/ambiguous patches, the test runner, the
agent loop, and end-to-end repair scenarios driven by a scripted model.

Optional live test against the real Groq API:

```powershell
$env:MINI_CODEX_LIVE=1; uv run pytest -m live
```

## Project layout

```
src/mini_codex/
├── main.py            CLI entry point
├── config.py          env loading + limits
├── agent.py           bounded LLM/tool loop
├── llm.py             Groq client wrapper
├── state.py           task/patch state machine
├── schemas.py         tool argument models + JSON schemas
├── console.py         terminal IO (injectable for tests)
├── context.py         runtime context for tools
├── tools/             the six tools
└── safety/            paths, secrets, patch validation
sample_project/        demo repair target (discount, cart, pricing bugs)
tests/                 unit, integration and end-to-end tests
```

## Known limitations (MVP)

- Python projects only; targets the `pytest` runner.
- One file per patch, applied one at a time with a fresh approval each time.
- Text/code tools only: no image, notebook, or binary handling.
- In-memory task state; no resumable logs or Git history integration.
- Does not guarantee a proposed fix is correct -- it runs the tests and reports
  the real result.
