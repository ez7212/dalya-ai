# Claude Code Instructions for Dalya Reviewer Pack

This file applies only inside the `dalya-reviewers/` folder. The installer appends a shorter repo-level section to the root `CLAUDE.md`.

When Eric asks for a Dalya reviewer, read:

1. `dalya-reviewers/shared-context.md`
2. `dalya-reviewers/review-session-rules.md`
3. The requested reviewer's persona/rubric/knowledge files
4. `dalya-reviewers/templates/review-output-template.md`

Do not change code during review unless Eric explicitly asks to implement accepted fixes.

Project-scoped Claude subagent definitions are provided in `dalya-reviewers/tool-adapters/claude-agents/` and are installed to `.claude/agents/` by `install.sh`.
