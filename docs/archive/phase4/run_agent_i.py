#!/usr/bin/env python3
"""Runner script for Claude Plotter Phase 4 — Agent I (Deployment Readiness).

Usage:
    python3 phase4/run_agent_i.py

Requirements:
    pip install claude-agent-sdk

PREREQUISITES:
    Phase 3 (Agent H) must be merged into master before running this script.

This script launches Agent I autonomously using the Claude Agent SDK.
Agent I will:
  1. Upgrade plotter_server.py with auth, /spec, /chart-types endpoints
  2. Scaffold a React SPA in plotter_web/
  3. Create the PlotterChart TypeScript component
  4. Build the React SPA and wire it into FastAPI static file serving
  5. Create Dockerfile and requirements files
  6. Create plotter_web_server.py standalone web entry point
  7. Update CLAUDE.md and README.md
  8. Run all tests and commit after each step

The agent works on branch: phase4/agent-i
Make sure you've already created and checked out that branch before running.
"""

import anyio
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.resolve()
PROMPT_FILE = Path(__file__).parent / "agent_i.md"
BRANCH = "phase4/agent-i"


def check_prerequisites():
    """Verify Phase 3 is complete before starting Phase 4."""
    spec_bar = PROJECT_ROOT / "plotter_spec_bar.py"
    server = PROJECT_ROOT / "plotter_server.py"

    missing = []
    if not spec_bar.exists():
        missing.append("plotter_spec_bar.py (Phase 3 spec builder)")
    if not server.exists():
        missing.append("plotter_server.py (Phase 3 FastAPI server)")

    if missing:
        print("ERROR: Phase 3 prerequisites not found:")
        for m in missing:
            print(f"  - {m}")
        print()
        print("Phase 4 requires Phase 3 (Agent H) to be complete and merged.")
        print("Run phase3/run_agent_h.py first, then merge to master.")
        return False
    return True


async def main():
    try:
        from claude_agent_sdk import query, ClaudeAgentOptions, ResultMessage, SystemMessage
    except ImportError:
        print("ERROR: claude-agent-sdk not installed.")
        print("Install with: pip install claude-agent-sdk")
        sys.exit(1)

    # Check prerequisites
    if not check_prerequisites():
        response = input("\nPhase 3 prerequisites missing. Continue anyway? (y/N): ").strip().lower()
        if response != "y":
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

    print(f"=== Claude Plotter — Agent I (Phase 4) ===")
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

    print("Starting Agent I... (this may take 30-60 minutes)")
    print("Commits will appear on branch:", BRANCH)
    print("NOTE: React SPA build requires Node.js + npm")
    print("-" * 60)

    try:
        async for message in query(
            prompt=prompt,
            options=ClaudeAgentOptions(
                cwd=str(PROJECT_ROOT),
                allowed_tools=["Read", "Write", "Edit", "Bash", "Glob", "Grep"],
                permission_mode="bypassPermissions",
                max_turns=150,
                max_budget_usd=20.0,
                model="claude-opus-4-6",
                setting_sources=["project"],
            )
        ):
            from claude_agent_sdk import SystemMessage, ResultMessage, AssistantMessage

            if isinstance(message, SystemMessage) and message.subtype == "init":
                session_id = message.data.get("session_id")
                print(f"[session] {session_id}")

            elif isinstance(message, ResultMessage):
                print("\n" + "=" * 60)
                print("AGENT I COMPLETE")
                print("=" * 60)
                print(message.result)
                print(f"\nStop reason: {message.stop_reason}")

            elif hasattr(message, "content"):
                turn_count += 1
                for block in getattr(message, "content", []):
                    if hasattr(block, "type"):
                        if block.type == "text" and hasattr(block, "text"):
                            text = block.text.strip()
                            if text:
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
        ["git", "log", "--oneline", "-20"],
        cwd=PROJECT_ROOT, capture_output=True, text=True
    )
    print("\nRecent commits:")
    print(result.stdout)


if __name__ == "__main__":
    anyio.run(main)
