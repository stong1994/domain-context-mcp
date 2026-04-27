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
      "command": "${REPO_CONTEXT_MCP_COMMAND:-repo-context-mcp}"
    }
  }
}
```

Claude Code supports environment expansion in `.mcp.json`, so users can override
machine-specific paths without editing the file:

```bash
export REPO_CONTEXT_MCP_COMMAND=/path/to/repo/.venv/bin/repo-context-mcp
export REPO_CONTEXT_HOME="$HOME/.repo-context-mcp"
```

When Claude Code opens this project, it should prompt before trusting the
project-scoped MCP server. Approve it, then use `/mcp` inside Claude Code to
inspect server status.

## CLI Setup Alternative

If you prefer a local, non-versioned Claude Code config, run this from the repo
root after installing the package:

```bash
claude mcp add --transport stdio --scope local \
  --env REPO_CONTEXT_HOME="$HOME/.repo-context-mcp" \
  repo-context -- "$(pwd)/.venv/bin/repo-context-mcp"
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
REPO_CONTEXT_OPENAI_API_KEY
OPENAI_API_KEY
~/.repo-context-mcp/auth.json
```

The saved auth file can be created with:

```bash
printenv OPENAI_API_KEY | .venv/bin/repo-context-auth login --with-api-key
```
