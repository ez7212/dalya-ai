# Installing Dalya Reviewer Agents

## Option A — automatic install

From the root of your Dalya repo:

```bash
unzip dalya-reviewers.zip
bash dalya-reviewers/install.sh
```

Then commit:

```bash
git add dalya-reviewers AGENTS.md CLAUDE.md .claude/agents .codex/agents .codex/config.toml
git commit -m "Add Dalya reviewer agents"
```

## Option B — manual install

1. Put `dalya-reviewers/` in the root of your repo.
2. Copy Claude agents:

```bash
mkdir -p .claude/agents
cp dalya-reviewers/tool-adapters/claude-agents/*.md .claude/agents/
```

3. Copy Codex agents:

```bash
mkdir -p .codex/agents
cp dalya-reviewers/tool-adapters/codex-agents/*.toml .codex/agents/
cp dalya-reviewers/tool-adapters/codex-config.toml .codex/config.toml
```

4. Add the contents of these files to the bottom of your root files:

```text
dalya-reviewers/tool-adapters/root-AGENTS.append.md  -> AGENTS.md
dalya-reviewers/tool-adapters/root-CLAUDE.append.md  -> CLAUDE.md
```

If `AGENTS.md` or `CLAUDE.md` do not exist, create them.

## Test Claude Code setup

Open Claude Code from the repo root and run:

```text
Show me the Dalya reviewer agents you can use. Do not inspect the whole codebase.
```

Then try:

```text
Use the dalya-chatbot-master agent to review the chatbot. Do not change code.
```

## Test Codex setup

Open Codex from the repo root and run:

```text
List active Dalya reviewer instructions and custom agents. Do not inspect the whole codebase.
```

Then try:

```text
Spawn dalya_security_researcher to review auth, RLS, API routes, webhooks, and deployment. Do not change code.
```

## How to update the agents over time

Edit the knowledge packs directly:

```text
dalya-reviewers/chatbot-master/benchmark-notes.md
dalya-reviewers/real-estate-guru/knowledge-pack.md
dalya-reviewers/ux-designer/adoption-playbook.md
dalya-reviewers/security-researcher/security-checklist.md
```

When a reviewer repeatedly misses something, add that lesson to the relevant rubric or knowledge pack. Do not bury too much detail in root `AGENTS.md` or `CLAUDE.md`; keep those files short and point to this folder.
