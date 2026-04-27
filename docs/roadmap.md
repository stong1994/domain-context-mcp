# Roadmap

## Low Priority

### Lightweight Workspace Boundary

Repo Context MCP currently has repo/workspace context, but not a first-class
workspace entity. That is acceptable for the current scope because durable
domain knowledge is the priority.

Future work may add a lightweight workspace boundary without introducing a heavy
workspace lifecycle:

- `workspace_id`
- `workspace_name`
- `root_path`
- `repos[]`
- `domains[]`
- `created_at` / `updated_at`

Possible tools:

- `workspace_resolve(repo_path=None)`
- `workspace_read(workspace_id)`
- `workspace_list()`
- `workspace_link_repo(workspace_id, repo_path)`

When this exists, `work_begin` can return a workspace object and tasks can record
`workspace_id` while still preserving `repo_path` for compatibility.

Do not prioritize this until domain knowledge lifecycle and client trigger
behavior are stable in real Codex and Claude Code usage.
