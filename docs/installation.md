# Installation

Repo Context MCP is a local stdio MCP server for coding agents. Install it into
a Python virtual environment, then point your MCP client at the `repo-context-mcp`
command.

## Requirements

- Python 3.10 or newer
- Git
- An MCP client such as Codex or Claude Code

OpenAI credentials are optional. Without them, domain resolution uses deterministic
repo and text matching.

## Install From Source

Clone the repository:

```bash
git clone https://github.com/stong1994/repo-context-mcp.git
cd repo-context-mcp
```

Create a virtual environment and install the package:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -U pip
.venv/bin/python -m pip install -e ".[dev]"
```

Verify the command is available:

```bash
.venv/bin/repo-context-mcp --help
```

For MCP clients that do not inherit your shell `PATH`, use the absolute path to
the virtualenv command:

```bash
$(pwd)/.venv/bin/repo-context-mcp
```

## State Directory

By default, local ledgers are stored under:

```text
~/.repo-context-mcp
```

Override this per client or shell:

```bash
export REPO_CONTEXT_HOME="$HOME/.repo-context-mcp"
```

Older `AGENT_SUBSTRATE_HOME` values are still honored as a migration fallback,
but new installs should use `REPO_CONTEXT_HOME`.

## OpenAI Credentials

OpenAI credentials are used for LLM-assisted domain resolution and readable
domain directory naming.

Preferred environment variable:

```bash
export REPO_CONTEXT_OPENAI_API_KEY="sk-..."
```

Or save the key locally:

```bash
printenv OPENAI_API_KEY | .venv/bin/repo-context-auth login --with-api-key
.venv/bin/repo-context-auth status
```

The saved credential file is written to:

```text
~/.repo-context-mcp/auth.json
```

with `0600` permissions. Older `AGENT_SUBSTRATE_OPENAI_API_KEY` and model
environment variables are still accepted as migration fallbacks.

## Generic MCP Config

Use this config shape for clients that accept JSON MCP server definitions:

```json
{
  "mcpServers": {
    "repo-context": {
      "command": "/absolute/path/to/repo-context-mcp/.venv/bin/repo-context-mcp",
      "env": {
        "REPO_CONTEXT_HOME": "~/.repo-context-mcp"
      }
    }
  }
}
```

If the command is already on the client's `PATH`, `repo-context-mcp` is enough.

## Claude Code

This repo includes a project-scoped `.mcp.json`:

```json
{
  "mcpServers": {
    "repo-context": {
      "type": "stdio",
      "command": "${REPO_CONTEXT_MCP_COMMAND:-repo-context-mcp}"
    }
  }
}
```

If your Claude Code process cannot find `repo-context-mcp`, set:

```bash
export REPO_CONTEXT_MCP_COMMAND="$(pwd)/.venv/bin/repo-context-mcp"
```

Then open the project in Claude Code, approve the project MCP server, and verify:

```text
/mcp
```

Local-only alternative:

```bash
claude mcp add --transport stdio --scope local \
  --env REPO_CONTEXT_HOME="$HOME/.repo-context-mcp" \
  repo-context -- "$(pwd)/.venv/bin/repo-context-mcp"
```

## Codex

Add a stdio MCP server named `repo-context` that runs:

```text
/absolute/path/to/repo-context-mcp/.venv/bin/repo-context-mcp
```

Pass this environment variable if you want an explicit state directory:

```text
REPO_CONTEXT_HOME=~/.repo-context-mcp
```

Codex also needs a small trigger skill or project instruction that tells it when
to call the workflow tools:

```text
work_begin -> work_checkpoint -> learning_review -> work_finish
```

## Verify

Run the test suite:

```bash
.venv/bin/python -m pytest
```

Run the dogfood MCP client:

```bash
.venv/bin/python scripts/dogfood_mcp.py
```

Use the persistent state directory:

```bash
.venv/bin/python scripts/dogfood_mcp.py --state-dir ~/.repo-context-mcp
```
