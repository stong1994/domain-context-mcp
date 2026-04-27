# Repo Context MCP

Repo Context MCP is a local tool server for coding agents. It is deliberately
not a CLI agent and does not try to orchestrate a conversation. Codex, Claude, or
another MCP client remains the driver; this server provides the local operating
layer:

- workspace context: repo discovery, repo profiles, git state, suggested checks
- domain knowledge: skill-like `SKILL.md` files with JSON metadata indexes
- knowledge updates: reviewed proposals that update domain knowledge only after acceptance
- execution ledger: validation runs tied to task ids
- task lifecycle: transaction records that make work auditable

The design goal is simple: let the model keep agency, but make context,
execution, and learning durable and reviewable.

## Trigger Model

MCP tools do not wake themselves up. The client or model calls them. This server
is shaped around two trigger classes:

- Soft triggers: cheap lookup tools the model can call when it needs context.
- Hard gates: lifecycle tools that should be required by client policy.

Recommended lifecycle:

```text
work_begin

model works with normal editor and shell tools

work_checkpoint
learning_review
work_finish
```

## Tools

The MCP server exposes these workflow tools for normal agent use:

- `work_begin(user_request, repo_path=None, conversation_id=None, idempotency_key=None, domain_hint=None, knowledge_query=None, knowledge_limit=5)`
- `work_checkpoint(task_id, summary, repo_path=None, run_check_ids=None, knowledge_updates=None, timeout_seconds=120)`
- `work_finish(task_id, summary, repo_path=None, run_check_ids=None, require_clean=False, allow_pending_updates=False, timeout_seconds=120)`
- `learning_review(decisions)`

It also exposes lower-level tools for precise control:

- `task_begin(user_request, repo_path=None, domain_hint=None, conversation_id=None, idempotency_key=None)`
- `task_list(status=None, repo_path=None, conversation_id=None)`
- `task_current(repo_path=None, conversation_id=None, idempotency_key=None)`
- `task_resume(task_id)`
- `task_complete(task_id)`
- `workspace_discover(root, max_depth=4)`
- `workspace_context(repo_path=None)`
- `domain_list(status="active", repo_path=None, tag=None)`
- `domain_read(domain_id)`
- `domain_duplicate_groups(status="active", repo_path=None)`
- `domain_create(name, description, repos=None, tags=None, body=None)`
- `domain_merge(target_domain_id, source_domain_ids, reason=None)`
- `domain_rename_directory(domain_id, new_domain_id=None, use_llm=True)`
- `domain_link_repo(domain_id, repo_path)`
- `domain_context(domain_ids)`
- `domain_resolve(user_request, repo_path=None, domain_hint=None, use_llm=True, create_if_missing=False)`
- `knowledge_list(status=None, scope=None)`
- `knowledge_read(knowledge_id)`
- `knowledge_search(query, scope=None, domain_id=None, status="active")`
- `knowledge_update_list(status=None, domain_id=None)`
- `knowledge_update_read(update_id)`
- `knowledge_propose_update(domain_id, source_task_id, operation, proposal, tags=None)`
- `knowledge_decide_update(update_id, decision, reason=None)`
- `knowledge_propose(kind, scope, title, body, source_task_id=None, domain_id=None, tags=None)`
- `knowledge_decide(knowledge_id, decision, reason=None)`
- `execution_suggest_checks(repo_path=None)`
- `execution_run_check(task_id, check_id, repo_path=None, timeout_seconds=120)`

## Storage

By default, ledgers live in:

```text
~/.repo-context-mcp/
```

Override it with:

```text
REPO_CONTEXT_HOME=/path/to/state
```

Tasks, executions, and update ledgers are stored as small JSON collections.
Domain knowledge is stored under:

```text
~/.repo-context-mcp/domains/<readable-domain-name>/
  SKILL.md
  domain.json
```

New domains use an LLM-generated, human-readable kebab-case directory name when
OpenAI credentials are available, for example `python-mcp-server`. If the LLM is
unavailable, the server falls back to a deterministic slug from the domain name.
`SKILL.md` is the durable knowledge body for humans and agents. `domain.json` is
the machine index.

## Install

See [docs/installation.md](docs/installation.md) for full Codex and Claude Code
setup notes.

Quick local install:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e ".[dev]"
```

Run tests:

```bash
.venv/bin/python -m pytest
```

Run the MCP server over stdio:

```bash
.venv/bin/repo-context-mcp
```

## OpenAI API

`domain_resolve` and new domain directory naming use the OpenAI Responses API
when an API key is configured. The key lookup order is:

```text
REPO_CONTEXT_OPENAI_API_KEY
OPENAI_API_KEY
~/.repo-context-mcp/auth.json
```

Store a key once with:

```bash
printenv OPENAI_API_KEY | .venv/bin/repo-context-auth login --with-api-key
```

Check status without revealing the secret:

```bash
.venv/bin/repo-context-auth status
```

Remove saved credentials:

```bash
.venv/bin/repo-context-auth logout
```

The saved auth file is written with `0600` permissions. The default model is:

```text
gpt-5.2-codex
```

Override it with:

```text
REPO_CONTEXT_MODEL=<model>
REPO_CONTEXT_REASONING=medium
```

If no API key is configured, domain resolution falls back to deterministic repo
and text matching and returns `llm_used: false`.

## MCP Client Config

Example client config:

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

## Claude Code

Claude Code support is provided through:

- `.mcp.json`: project-scoped MCP config that registers this server as
  `repo-context`
- `CLAUDE.md`: project instructions that tell Claude Code when to call the
  workflow tools
- `docs/claude-code.md`: setup, verification, and secret-handling notes

After installing the project, open this repo with Claude Code and approve the
project MCP server when prompted. Then verify status inside Claude Code:

```text
/mcp
```

Or configure it as a local, non-versioned Claude Code server:

```bash
claude mcp add --transport stdio --scope local \
  --env REPO_CONTEXT_HOME="$HOME/.repo-context-mcp" \
  repo-context -- "$(pwd)/.venv/bin/repo-context-mcp"
```

## Codex Trigger Skill

Codex needs a thin trigger skill or project instruction that nudges repo work
into the Repo Context MCP workflow:

```text
~/.codex/skills/repo-context-workflow/SKILL.md
```

Its description is intentionally short to reduce skills context pressure:

```text
Use when starting any repo/project/code task, including analysis, code changes, reviews, debugging, validation, tests, or project improvement; call Repo Context MCP work_begin first, work_checkpoint for checks/learnings, and work_finish before final response.
```

Important: this README is documentation only. Codex does not read this project
README at startup to decide which tools to use. Startup behavior comes from:

- MCP server config in the Codex config file
- skill metadata such as `~/.codex/skills/repo-context-workflow/SKILL.md`
- any installed plugin skills, such as Superpowers

The trigger skill is what tells Codex to prefer the Repo Context workflow.
The MCP config only makes the tools available.

Expected behavior:

- Repo/project analysis starts with `work_begin`.
- Checks and durable learning candidates go through `work_checkpoint`.
- Accepted/rejected learning goes through `learning_review`.
- Final answers are gated by `work_finish`.

To verify a task used the MCP, look for tool calls such as:

```text
work_begin
work_checkpoint
learning_review
work_finish
```

Or inspect the local ledger:

```bash
ls -lt ~/.repo-context-mcp
```

## Dogfood

Run a real stdio MCP client against the local server:

```bash
.venv/bin/python scripts/dogfood_mcp.py
```

By default, dogfood uses a temporary ledger directory. To write into the normal
local ledger:

```bash
.venv/bin/python scripts/dogfood_mcp.py --state-dir ~/.repo-context-mcp
```

The dogfood flow calls:

```text
list_tools
domain_create
work_begin
work_checkpoint
learning_review
work_finish
```

## Repo Profiles

The server can infer basic repo profiles from files like `package.json`,
`pyproject.toml`, `go.mod`, and `Cargo.toml`.

For stronger control, add:

```text
.repo-context/profile.json
```

Example:

```json
{
  "name": "example-service",
  "summary": "API service for uploads",
  "languages": ["python"],
  "checks": [
    {
      "id": "tests",
      "label": "Unit tests",
      "command": ["pytest"]
    },
    {
      "id": "lint",
      "label": "Ruff lint",
      "command": ["ruff", "check", "."]
    }
  ],
  "conventions": [
    "Prefer repository helpers over ad hoc shell parsing."
  ]
}
```

`execution_run_check` only runs checks from the repo profile. That is an
intentional constraint: validation commands should be named, reviewable, and
recorded instead of arbitrary shell snippets.
