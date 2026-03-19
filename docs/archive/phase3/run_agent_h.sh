#!/bin/bash
cd /workspaces/Claude-Prism
export ANTHROPIC_API_KEY="${ANTHROPIC_API_KEY}"
echo '=== Agent H (Phase 3 — Plotly/pywebview) starting ==='
echo 'Model: claude-opus-4-6'
echo 'Branch: phase3/agent-h'
date
echo '---'
claude   --model claude-opus-4-6   --allowedTools 'Read,Write,Edit,Bash,Glob,Grep'   --dangerously-skip-permissions   --max-turns 120   -p "$(cat phase3/agent_h.md)"
echo '=== Agent H done ==='
date
