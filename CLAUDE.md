# Claude Code Instructions

This project uses the `repo-context` MCP server to keep repo work auditable and
to preserve durable domain knowledge.

For repo analysis, code changes, reviews, debugging, validation, tests, or
project improvement:

1. Call `work_begin` before substantive repo inspection or edits.
2. Use normal Claude Code file, shell, and git tools for the actual work.
3. Call `work_checkpoint` after meaningful progress, validation runs, or durable
   learning candidates.
4. Use `learning_review` only when proposed learning should be accepted or
   rejected.
5. Call `work_finish` before claiming the task is done.

Prefer the high-level workflow tools over lower-level task/domain/knowledge
tools unless precise control is needed. If the MCP server is unavailable,
continue normally and state that `repo-context` was unavailable.
