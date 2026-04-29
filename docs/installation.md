# Installation

Domain Context MCP is a local stdio MCP server for coding agents. Install it into
a Python virtual environment, then point your MCP client at the `domain-context-mcp`
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
git clone https://github.com/stong1994/domain-context-mcp.git
cd domain-context-mcp
```

Create a virtual environment and install the package:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -U pip
.venv/bin/python -m pip install -e ".[dev]"
```

Verify the command is available:

```bash
.venv/bin/domain-context-mcp --help
```

For MCP clients that do not inherit your shell `PATH`, use the absolute path to
the virtualenv command:

```bash
$(pwd)/.venv/bin/domain-context-mcp
```

## State Directory

By default, local ledgers are stored under:

```text
~/.domain-context-mcp
```

Override this per client or shell:

```bash
export DOMAIN_CONTEXT_HOME="$HOME/.domain-context-mcp"
```

Older `REPO_CONTEXT_HOME` and `AGENT_SUBSTRATE_HOME` values are still honored as
migration fallbacks, but new installs should use `DOMAIN_CONTEXT_HOME`.

## OpenAI Credentials

OpenAI credentials are used for LLM-assisted domain resolution and readable
domain directory naming.

Preferred environment variable:

```bash
export DOMAIN_CONTEXT_OPENAI_API_KEY="sk-..."
```

Or save the key locally:

```bash
printenv OPENAI_API_KEY | .venv/bin/domain-context-auth login --with-api-key
.venv/bin/domain-context-auth status
```

The saved credential file is written to:

```text
~/.domain-context-mcp/auth.json
```

with `0600` permissions. Older `REPO_CONTEXT_*` and `AGENT_SUBSTRATE_*`
environment variables are still accepted as migration fallbacks.

## Generic MCP Config

Use this config shape for clients that accept JSON MCP server definitions:

```json
{
  "mcpServers": {
    "domain-context": {
      "command": "/absolute/path/to/domain-context-mcp/.venv/bin/domain-context-mcp",
      "env": {
        "DOMAIN_CONTEXT_HOME": "~/.domain-context-mcp"
      }
    }
  }
}
```

If the command is already on the client's `PATH`, `domain-context-mcp` is enough.

## Claude Code

This repo includes a project-scoped `.mcp.json`:

```json
{
  "mcpServers": {
    "domain-context": {
      "type": "stdio",
      "command": "${DOMAIN_CONTEXT_MCP_COMMAND:-domain-context-mcp}"
    }
  }
}
```

If your Claude Code process cannot find `domain-context-mcp`, set:

```bash
export DOMAIN_CONTEXT_MCP_COMMAND="$(pwd)/.venv/bin/domain-context-mcp"
```

Then open the project in Claude Code, approve the project MCP server, and verify:

```text
/mcp
```

Local-only alternative:

```bash
claude mcp add --transport stdio --scope local \
  --env DOMAIN_CONTEXT_HOME="$HOME/.domain-context-mcp" \
  domain-context -- "$(pwd)/.venv/bin/domain-context-mcp"
```

## Codex

Add a stdio MCP server named `domain-context` that runs:

```text
/absolute/path/to/domain-context-mcp/.venv/bin/domain-context-mcp
```

Pass this environment variable if you want an explicit state directory:

```text
DOMAIN_CONTEXT_HOME=~/.domain-context-mcp
```

Codex also needs a small trigger skill or project instruction that tells it to
call the workflow tools only when durable domain knowledge is involved:

```text
work_begin -> work_checkpoint -> learning_review -> work_finish
```

Do not trigger Domain Context MCP for ordinary one-off code edits, local test runs,
simple debugging, git operations, or general project exploration unless the user
explicitly asks for durable knowledge handling.

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
.venv/bin/python scripts/dogfood_mcp.py --state-dir ~/.domain-context-mcp
```
