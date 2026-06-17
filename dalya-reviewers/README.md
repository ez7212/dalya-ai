# Dalya Reviewer Agents

This package gives Dalya four reviewer agents that work in both Claude Code and Codex:

1. **Chatbot Master** — production chatbot/conversation-quality reviewer.
2. **Real Estate Guru** — Dubai secondary-market resale operator and sales realism reviewer.
3. **UX Designer** — dashboard adoption, onboarding, behavior-change, and daily-use reviewer.
4. **Security Researcher** — Supabase, API, auth, RLS, deployment, webhook, and AI security reviewer.

The files are intentionally plain Markdown/TOML so the system is easy to edit, version, and run from either tool. `file-routing.md` maps each reviewer to the concrete backend, frontend, test, report, and product-context files they should inspect first.

## Folder structure

```text
dalya-reviewers/
  README.md
  INSTALL.md
  install.sh
  shared-context.md
  review-session-rules.md
  file-routing.md
  commands/
    review-all.md
    review-chatbot.md
    review-dashboard.md
    review-security.md
    review-current-branch.md
  chatbot-master/
    persona.md
    benchmark-notes.md
    eval-cases.md
    review-rubric.md
  real-estate-guru/
    persona.md
    knowledge-pack.md
    transaction-reference.md
    review-rubric.md
  ux-designer/
    persona.md
    adoption-playbook.md
    review-rubric.md
  security-researcher/
    persona.md
    security-checklist.md
    review-rubric.md
  templates/
    review-output-template.md
    linear-task-template.md
  tool-adapters/
    root-AGENTS.append.md
    root-CLAUDE.append.md
    claude-agents/*.md
    codex-agents/*.toml
```

After running `install.sh`, the repo will also have:

```text
AGENTS.md                 # Codex repo instructions, or appended section if it already exists
CLAUDE.md                 # Claude Code repo instructions, or appended section if it already exists
.codex/agents/*.toml      # Codex project-scoped custom agents
.claude/agents/*.md       # Claude Code project-scoped subagents
```

## How to run reviews

### Claude Code

```text
Use the dalya-chatbot-master and dalya-real-estate-guru agents to review the current chatbot implementation. Do not change code. Return P0/P1/P2 findings and Linear-ready tasks.
```

```text
Use the dalya-ux-designer agent to review the dashboard and onboarding path. Do not change code. Focus on whether a Dubai agent would use this daily.
```

```text
Use the dalya-security-researcher agent to review Supabase, RLS, API routes, webhooks, auth, deployment, logs, and AI context retrieval. Do not change code.
```

### Codex

```text
Spawn dalya_chatbot_master and dalya_real_estate_guru to review the current chatbot. Wait for both. Do not change code. Consolidate findings into P0/P1/P2 plus Linear-ready tasks.
```

```text
Spawn dalya_ux_designer to review the dashboard and onboarding. Do not change code. Focus on daily-use adoption and agent behavior change.
```

```text
Spawn dalya_security_researcher to review backend/database/API/security. Do not change code. Rank findings Critical/High/Medium/Low.
```

## Recommended cadence

- **Every chatbot change:** Chatbot Master + Real Estate Guru.
- **Every dashboard/workflow change:** UX Designer + Real Estate Guru.
- **Before each demo:** all four reviewers.
- **Before each deploy:** Security Researcher.
- **After each accepted review:** convert findings into Linear tasks, then implement separately.

## Important operating rule

These reviewers default to **review-only**. They should not edit code unless you explicitly say: `implement the accepted fixes`.
