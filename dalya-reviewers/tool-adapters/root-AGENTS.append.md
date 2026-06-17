<!-- DALYA_REVIEWERS_START -->

## Dalya Reviewer Agents

Dalya reviewer instructions live in `dalya-reviewers/`.

When Eric asks for any of these reviewers, treat the relevant files as reviewer instructions and stay in review-only mode unless explicitly asked to implement fixes:

- Chatbot Master: `dalya-reviewers/chatbot-master/`
- Real Estate Guru: `dalya-reviewers/real-estate-guru/`
- UX Designer: `dalya-reviewers/ux-designer/`
- Security Researcher: `dalya-reviewers/security-researcher/`

Always read first:

- `dalya-reviewers/shared-context.md`
- `dalya-reviewers/review-session-rules.md`
- `dalya-reviewers/file-routing.md`
- `dalya-reviewers/templates/review-output-template.md`

Reusable commands live in `dalya-reviewers/commands/`.

Codex project-scoped custom agents are installed in `.codex/agents/`:

- `dalya_chatbot_master`
- `dalya_real_estate_guru`
- `dalya_ux_designer`
- `dalya_security_researcher`

Default behavior: do not modify code during review. Return prioritized findings and Linear-ready tasks.

<!-- DALYA_REVIEWERS_END -->
