# Client Integration

This project has been verified through a real MCP stdio client. The dogfood
client starts the installed server command, initializes an MCP session, lists
tools, and runs the full lifecycle.

## Verified Server Command

```text
/absolute/path/to/repo-context-mcp/.venv/bin/repo-context-mcp
```

## Suggested MCP Config

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

## Codex Status

Configure Codex with a stdio MCP server named `repo-context` that runs:

```text
/absolute/path/to/repo-context-mcp/.venv/bin/repo-context-mcp
```

Verify with:

```bash
codex mcp list
codex mcp get repo-context
```

Existing conversations may need a new session or app restart before newly
configured MCP tools appear.

## Claude Code Status

This repo includes Claude Code project files:

```text
.mcp.json
CLAUDE.md
docs/claude-code.md
```

`.mcp.json` registers this server as `repo-context`. `CLAUDE.md` provides the
workflow trigger policy for Claude Code.

Claude Code was not installed in this environment when this document was
updated, so direct `claude mcp list` verification could not be run here. After
installing Claude Code, verify with:

```bash
claude mcp list
claude mcp get repo-context
```

Inside Claude Code, use:

```text
/mcp
```

## Dogfood Command

Temporary ledger:

```bash
.venv/bin/python scripts/dogfood_mcp.py
```

Persistent local ledger:

```bash
.venv/bin/python scripts/dogfood_mcp.py --state-dir ~/.repo-context-mcp
```

## Current Tools

- `domain_context`
- `domain_create`
- `domain_duplicate_groups`
- `domain_link_repo`
- `domain_list`
- `domain_merge`
- `domain_read`
- `domain_rename_directory`
- `domain_resolve`
- `execution_run_check`
- `execution_suggest_checks`
- `knowledge_decide`
- `knowledge_decide_update`
- `task_begin`
- `task_complete`
- `task_current`
- `workspace_discover`
- `workspace_context`
- `knowledge_list`
- `knowledge_propose_update`
- `knowledge_read`
- `knowledge_search`
- `knowledge_propose`
- `knowledge_update_list`
- `knowledge_update_read`
- `learning_review`
- `task_list`
- `task_resume`
- `work_begin`
- `work_checkpoint`
- `work_finish`

## Lifecycle Contract

Preferred workflow contract:

- Call `work_begin` before substantive repo work.
- Call `work_checkpoint` when you have progress, checks, or learning candidates.
- Call `learning_review` to accept/reject proposed learning.
- Call `work_finish` before declaring the task done.

Lower-level tools can still be used as lifecycle gates when a client needs
manual control:

- Call `task_begin` before substantive work.
- Resolve domains with `domain_resolve` or pass a `domain_hint`.
- Use `execution_run_check` for named validation checks.
- Use `knowledge_propose_update` for durable domain learning candidates.
- Use `knowledge_decide_update` before knowledge changes `SKILL.md`.
- Call `task_complete` before declaring the task done.
