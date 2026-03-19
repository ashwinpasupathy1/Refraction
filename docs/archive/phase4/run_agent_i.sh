#!/bin/bash
export ANTHROPIC_API_KEY="${ANTHROPIC_API_KEY}"
cd /workspaces/Claude-Prism
echo '=== Agent I (Phase 4 — Deployment Readiness) starting ===' > phase4/agent_i_output.log
echo 'Model: claude-opus-4-6' >> phase4/agent_i_output.log
echo 'Branch: phase4/agent-i' >> phase4/agent_i_output.log
date >> phase4/agent_i_output.log
echo '---' >> phase4/agent_i_output.log
claude --model claude-opus-4-6   --allowedTools 'Read,Write,Edit,Bash,Glob,Grep'   --dangerously-skip-permissions   --max-turns 150   -p "$(cat phase4/agent_i.md)" >> phase4/agent_i_output.log 2>&1
echo '=== Agent I finished ===' >> phase4/agent_i_output.log
date >> phase4/agent_i_output.log
