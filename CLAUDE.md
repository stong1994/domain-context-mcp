# Claude Code Instructions

This project can use the `repo-context` MCP server to preserve durable domain
knowledge.

Use `repo-context` only when the task involves domain knowledge, for example:

- finding or applying durable repo/domain conventions
- deciding which domain owns a reusable learning
- proposing, accepting, rejecting, merging, or renaming domain knowledge
- using previous task/domain context to guide current work
- updating repo profiles, long-lived workflow rules, or knowledge lifecycle docs

Do not call `repo-context` for ordinary one-off code edits, simple debugging,
formatting, local test runs, git operations, or project exploration unless the
user explicitly asks for durable knowledge handling.

When `repo-context` applies:

1. Call `work_begin` before using domain context.
2. Use normal Claude Code file, shell, and git tools for the actual work.
3. Call `work_checkpoint` when you discover a reusable learning candidate.
4. Use `learning_review` only when proposed learning should be accepted or
   rejected.
5. Call `work_finish` before claiming the domain-knowledge work is done.

If the MCP server is unavailable, continue normally and state that
`repo-context` was unavailable only when the unavailable MCP mattered to the
task.
