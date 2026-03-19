#!/usr/bin/env python3
"""Runner script for Claude Plotter Phase 3 — Agent H (Plotly + pywebview renderer).

Usage:
    python3 phase3/run_agent_h.py

Requirements:
    pip install claude-agent-sdk

This script launches Agent H autonomously using the Claude Agent SDK.
Agent H will:
  1. Install fastapi, uvicorn, plotly, pywebview
  2. Create 4 Plotly spec builders (bar, grouped_bar, line, scatter)
  3. Create the FastAPI render/event server
  4. Create the pywebview panel wrapper
  5. Wire everything into plotter_barplot_app.py
  6. Run all tests and commit after each step

The agent works on branch: phase3/agent-h
Make sure you've already created and checked out that branch before running.
"""

import anyio
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.resolve()
PROMPT_FILE = Path(__file__).parent / "agent_h.md"
BRANCH = "phase3/agent-h"


async def main():
    try:
        from claude_agent_sdk import query, ClaudeAgentOptions, ResultMessage, SystemMessage
    except ImportError:
        print("ERROR: claude-agent-sdk not installed.")
        print("Install with: pip install claude-agent-sdk")
        sys.exit(1)

    # Verify we're on the right branch
    import subprocess
    result = subprocess.run(
        ["git", "branch", "--show-current"],
        cwd=PROJECT_ROOT, capture_output=True, text=True
    )
    current_branch = result.stdout.strip()
    if current_branch != BRANCH:
        print(f"WARNING: Currently on '{current_branch}', expected '{BRANCH}'")
        print(f"Run: git checkout -b {BRANCH} && git push -u origin {BRANCH}")
        response = input("Continue anyway? (y/N): ").strip().lower()
        if response != "y":
            sys.exit(1)

    print(f"=== Claude Plotter — Agent H (Phase 3) ===")
    print(f"Project: {PROJECT_ROOT}")
    print(f"Branch:  {current_branch}")
    print(f"Prompt:  {PROMPT_FILE}")
    print()

    if not PROMPT_FILE.exists():
        print(f"ERROR: Prompt file not found: {PROMPT_FILE}")
        sys.exit(1)

    prompt = PROMPT_FILE.read_text()

    session_id = None
    turn_count = 0
    last_result = None

    print("Starting Agent H... (this may take 20-40 minutes)")
    print("Commits will appear on branch:", BRANCH)
    print("-" * 60)

    try:
        async for message in query(
            prompt=prompt,
            options=ClaudeAgentOptions(
                cwd=str(PROJECT_ROOT),
                allowed_tools=["Read", "Write", "Edit", "Bash", "Glob", "Grep"],
                permission_mode="bypassPermissions",
                max_turns=120,
                max_budget_usd=15.0,
                model="claude-opus-4-6",
                setting_sources=["project"],
            )
        ):
            from claude_agent_sdk import SystemMessage, ResultMessage, AssistantMessage

            if isinstance(message, SystemMessage) and message.subtype == "init":
                session_id = message.data.get("session_id")
                print(f"[session] {session_id}")

            elif isinstance(message, ResultMessage):
                last_result = message.result
                print("\n" + "=" * 60)
                print("AGENT H COMPLETE")
                print("=" * 60)
                print(last_result)
                print(f"\nStop reason: {message.stop_reason}")

            elif hasattr(message, "content"):
                turn_count += 1
                # Print tool use activity as progress indicator
                for block in getattr(message, "content", []):
                    if hasattr(block, "type"):
                        if block.type == "text" and hasattr(block, "text"):
                            text = block.text.strip()
                            if text:
                                # Print first 200 chars of each agent message
                                preview = text[:200].replace("\n", " ")
                                print(f"[turn {turn_count}] {preview}")
                        elif block.type == "tool_use" and hasattr(block, "name"):
                            tool_input = getattr(block, "input", {})
                            if block.name == "Bash":
                                cmd = str(tool_input.get("command", ""))[:80]
                                print(f"  → Bash: {cmd}")
                            elif block.name in ("Write", "Edit"):
                                path = tool_input.get("file_path", "")
                                print(f"  → {block.name}: {path}")

    except KeyboardInterrupt:
        print("\n\nInterrupted by user.")
        if session_id:
            print(f"Session ID for resuming: {session_id}")
        sys.exit(0)
    except Exception as e:
        print(f"\nERROR: {e}")
        if session_id:
            print(f"Session ID for resuming: {session_id}")
        raise

    print(f"\nTotal turns: {turn_count}")
    if session_id:
        print(f"Session ID: {session_id}")

    # Final git log
    result = subprocess.run(
        ["git", "log", "--oneline", "-15"],
        cwd=PROJECT_ROOT, capture_output=True, text=True
    )
    print("\nRecent commits:")
    print(result.stdout)


if __name__ == "__main__":
    anyio.run(main)
