# Claude Code Integration

Claude Code can use this server over stdio through its MCP support.

## Project Config

This repo includes a project-scoped Claude Code MCP config:

```text
.mcp.json
```

It registers the server as `domain-context`:

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

Claude Code supports environment expansion in `.mcp.json`, so users can override
machine-specific paths without editing the file:

```bash
export DOMAIN_CONTEXT_MCP_COMMAND=/path/to/repo/.venv/bin/domain-context-mcp
export DOMAIN_CONTEXT_HOME="$HOME/.domain-context-mcp"
```

When Claude Code opens this project, it should prompt before trusting the
project-scoped MCP server. Approve it, then use `/mcp` inside Claude Code to
inspect server status.

## CLI Setup Alternative

If you prefer a local, non-versioned Claude Code config, run this from the repo
root after installing the package:

```bash
claude mcp add --transport stdio --scope local \
  --env DOMAIN_CONTEXT_HOME="$HOME/.domain-context-mcp" \
  domain-context -- "$(pwd)/.venv/bin/domain-context-mcp"
```

Use these commands to verify:

```bash
claude mcp list
claude mcp get domain-context
```

Inside an interactive Claude Code session:

```text
/mcp
```

## Trigger Instructions

Claude Code reads `CLAUDE.md` as project guidance. This repo's `CLAUDE.md`
instructs Claude to use the workflow tools only when durable domain knowledge is
involved:

```text
work_begin -> work_checkpoint -> learning_review -> work_finish
```

MCP config only makes tools available. `CLAUDE.md` is the trigger policy that
nudges Claude Code to call them during domain-knowledge work.

## Secret Handling

Do not put OpenAI or Anthropic API keys into `.mcp.json`. Configure OpenAI access
through one of these local-only mechanisms:

```text
DOMAIN_CONTEXT_OPENAI_API_KEY
OPENAI_API_KEY
~/.domain-context-mcp/auth.json
```

The saved auth file can be created with:

```bash
printenv OPENAI_API_KEY | .venv/bin/domain-context-auth login --with-api-key
```
