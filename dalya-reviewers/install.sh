#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(pwd)"
PACK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ ! -f "$PACK_DIR/shared-context.md" ]]; then
  echo "Could not find dalya-reviewers/shared-context.md. Run this from your repo root after unzipping dalya-reviewers." >&2
  exit 1
fi

mkdir -p "$ROOT_DIR/.claude/agents" "$ROOT_DIR/.codex/agents"
cp "$PACK_DIR"/tool-adapters/claude-agents/*.md "$ROOT_DIR/.claude/agents/"
cp "$PACK_DIR"/tool-adapters/codex-agents/*.toml "$ROOT_DIR/.codex/agents/"

if [[ ! -f "$ROOT_DIR/.codex/config.toml" ]]; then
  cp "$PACK_DIR/tool-adapters/codex-config.toml" "$ROOT_DIR/.codex/config.toml"
else
  if ! grep -q "^\[agents\]" "$ROOT_DIR/.codex/config.toml"; then
    printf "\n" >> "$ROOT_DIR/.codex/config.toml"
    cat "$PACK_DIR/tool-adapters/codex-config.toml" >> "$ROOT_DIR/.codex/config.toml"
  fi
fi

append_once() {
  local target="$1"
  local source="$2"
  local marker="DALYA_REVIEWERS_START"
  if [[ ! -f "$target" ]]; then
    cp "$source" "$target"
  elif ! grep -q "$marker" "$target"; then
    printf "\n\n" >> "$target"
    cat "$source" >> "$target"
  fi
}

append_once "$ROOT_DIR/AGENTS.md" "$PACK_DIR/tool-adapters/root-AGENTS.append.md"
append_once "$ROOT_DIR/CLAUDE.md" "$PACK_DIR/tool-adapters/root-CLAUDE.append.md"

echo "Installed Dalya reviewer agents."
echo "Created/updated:"
echo "  - AGENTS.md"
echo "  - CLAUDE.md"
echo "  - .claude/agents/"
echo "  - .codex/agents/"
echo "  - .codex/config.toml"
echo ""
echo "Next: restart Claude Code/Codex sessions from the repo root so they reload instructions."
