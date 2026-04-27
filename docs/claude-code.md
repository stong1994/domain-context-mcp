# Claude Code Integration

Claude Code can use this server over stdio through its MCP support.

## Project Config

This repo includes a project-scoped Claude Code MCP config:

```text
.mcp.json
```

It registers the server as `repo-context`:

```json
{
  "mcpServers": {
    "repo-context": {
      "type": "stdio",
      "command": "${REPO_CONTEXT_MCP_COMMAND:-/Users/stong/Project/Github/agent-substrate-mcp/.venv/bin/agent-substrate-mcp}",
      "env": {
        "AGENT_SUBSTRATE_HOME": "${AGENT_SUBSTRATE_HOME:-/Users/stong/.agent-substrate-mcp}"
      }
    }
  }
}
```

Claude Code supports environment expansion in `.mcp.json`, so users can override
machine-specific paths without editing the file:

```bash
export REPO_CONTEXT_MCP_COMMAND=/path/to/repo/.venv/bin/agent-substrate-mcp
export AGENT_SUBSTRATE_HOME="$HOME/.agent-substrate-mcp"
```

When Claude Code opens this project, it should prompt before trusting the
project-scoped MCP server. Approve it, then use `/mcp` inside Claude Code to
inspect server status.

## CLI Setup Alternative

If you prefer a local, non-versioned Claude Code config, run this from the repo
root after installing the package:

```bash
claude mcp add --transport stdio --scope local \
  --env AGENT_SUBSTRATE_HOME="$HOME/.agent-substrate-mcp" \
  repo-context -- "$(pwd)/.venv/bin/agent-substrate-mcp"
```

Use these commands to verify:

```bash
claude mcp list
claude mcp get repo-context
```

Inside an interactive Claude Code session:

```text
/mcp
```

## Trigger Instructions

Claude Code reads `CLAUDE.md` as project guidance. This repo's `CLAUDE.md`
instructs Claude to use the workflow tools:

```text
work_begin -> work_checkpoint -> learning_review -> work_finish
```

MCP config only makes tools available. `CLAUDE.md` is the trigger policy that
nudges Claude Code to call them during repo work.

## Secret Handling

Do not put OpenAI or Anthropic API keys into `.mcp.json`. Configure OpenAI access
through one of these local-only mechanisms:

```text
AGENT_SUBSTRATE_OPENAI_API_KEY
OPENAI_API_KEY
~/.agent-substrate-mcp/auth.json
```

The saved auth file can be created with:

```bash
printenv OPENAI_API_KEY | .venv/bin/agent-substrate-auth login --with-api-key
```
