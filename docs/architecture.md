# Architecture

Domain Context MCP is built around a boundary: the model decides what to do,
and this server records the state that should survive the conversation.

## Responsibilities

The MCP server owns:

- repository profiles and suggested checks
- task ids and task lifecycle
- validation execution records
- skill-like domain knowledge files
- proposed and reviewed domain knowledge updates
- local JSON persistence

The model owns:

- conversation
- context assembly
- deciding when a lookup is useful
- editing code
- summarizing what changed
- proposing domain knowledge update candidates

## Hard Gates

Client policy should call these tools only when durable domain knowledge is
involved:

- `work_begin` before using domain context
- `work_checkpoint` while work is in progress, especially when learning candidates appear
- `learning_review` before durable domain knowledge changes
- `work_finish` before the model claims domain-knowledge work is done

Ordinary one-off code edits, simple debugging, formatting, local test runs, git
operations, and general project exploration should proceed without this MCP
unless the user explicitly asks for durable knowledge handling.

The lower-level tools remain available for precise control:

- `task_begin`
- `domain_resolve`
- `execution_run_check`
- `knowledge_propose_update`
- `knowledge_decide_update`
- `task_complete`

The server does not prevent the user or model from using other tools. It gives
the client a small set of auditable checkpoints.

## Task And Domain Model

Task and domain knowledge are separate by design:

```text
Task
  records what happened during one unit of work

Domain
  owns what we know long term

KnowledgeUpdate
  connects a source task to a domain knowledge change
```

Tasks are machine ledgers. Domains are skill-like knowledge units stored as
`SKILL.md` plus `domain.json`.

Domain directories are intended to be readable knowledge handles, not opaque
database ids. New domains ask the LLM for a concise kebab-case directory name
such as `python-mcp-server`; when the API is unavailable, the server falls back
to the same slug format from the domain name. Existing legacy ids such as
`d_python-mcp-server` remain readable for compatibility.

## Knowledge Lifecycle

Knowledge updates move through these states:

```text
proposed -> accepted
proposed -> rejected
```

Accepted updates write into the domain `SKILL.md` and create accepted knowledge
ledger entries. Rejected updates remain in the ledger as evidence but do not
change durable domain knowledge. Accepted knowledge entries can later be
deprecated when they become stale.

## Domain Resolution

`domain_resolve` uses the OpenAI Responses API when `DOMAIN_CONTEXT_OPENAI_API_KEY`,
`REPO_CONTEXT_OPENAI_API_KEY`, `AGENT_SUBSTRATE_OPENAI_API_KEY`, `OPENAI_API_KEY`,
or saved local auth is configured. It sends the user request, repo profile,
domain hint, and domain catalog, then expects structured JSON with
matched domains, confidence, reasons, and optional new-domain suggestions.

If the API is unavailable, the server falls back to repo and text matching while
making that downgrade explicit with `llm_used: false`.

## Execution Model

`execution_run_check` only runs named checks from the repo profile. This gives
validation commands a durable identity and avoids turning the MCP server into a
general shell.

Checks can be inferred, but explicit profiles are preferred for serious repos.

## Workflow Tools

The workflow layer composes lower-level tools so models do not need to remember
the full sequence every time.

`work_begin` creates or reuses a task, resolves domains, returns domain context,
searches relevant knowledge, and suggests named checks.

`work_checkpoint` records a checkpoint, can run named checks, and can propose
domain knowledge updates tied to the task.

`learning_review` accepts or rejects proposed domain knowledge updates in a
batch. Accepted updates write into domain `SKILL.md`.

`work_finish` records a final checkpoint, can run final checks, completes the
task, reports pending updates, and returns a `ready` boolean.
