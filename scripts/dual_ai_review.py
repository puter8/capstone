# -*- coding: utf-8 -*-
"""Sequential dual-AI review orchestrator for docs/ai-collab/.

Runs Claude Code and Codex CLI non-interactively, one at a time, so both
agents read/write docs/ai-collab/ files without racing each other. Neither
agent is ever invoked in parallel with the other -- that is the one hard
rule this script exists to enforce.

Every subprocess inherits this process's stdout/stderr directly (no
capturing, no summarizing), so the full reasoning of whichever agent is
running streams live to the terminal exactly as it would in an interactive
session.

The task itself is NOT hardcoded here. Each step tells the target agent to
read docs/ai-collab/CONTEXT.md and CURRENT_TASK.md and follow the role
instructions written there. To run a new review cycle, edit CURRENT_TASK.md
and re-run this script -- the script only sequences *who* runs *when* and
*which file* they are allowed to write.

Usage (run from the repository root):
  python scripts/dual_ai_review.py --status
  python scripts/dual_ai_review.py --dry-run
  python scripts/dual_ai_review.py
  python scripts/dual_ai_review.py --step codex_round2
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
COLLAB_DIR = ROOT / "docs" / "ai-collab"
RUN_LOG = COLLAB_DIR / "runs.log"

PENDING_MARKER = "아직 작성 안 됨"

# Bash subcommands each agent may run unattended. Deliberately excludes any
# git command that mutates history or the remote (commit/push/reset/force),
# and excludes rm. Widen only with a specific reason.
CLAUDE_ALLOWED_TOOLS = (
    "Read Write Edit Grep Glob "
    "Bash(python*) Bash(python3*) Bash(pytest*) "
    "Bash(git status*) Bash(git diff*) Bash(git log*)"
)

STEPS = {
    "claude_round1": {
        "agent": "claude",
        "target_file": COLLAB_DIR / "CLAUDE_REVIEW.md",
        "role_hint": (
            "You are Claude Code, Round 1 (independent diagnosis). Read "
            "docs/ai-collab/CONTEXT.md and docs/ai-collab/CURRENT_TASK.md. "
            "Do the Round 1 diagnosis described there using real code/data "
            "(run actual scripts, do not estimate). Write your full findings "
            "to docs/ai-collab/CLAUDE_REVIEW.md only. Do not modify any other "
            "file. Do not commit, push, or reset git state."
        ),
    },
    "codex_round2": {
        "agent": "codex",
        "target_file": COLLAB_DIR / "CODEX_REVIEW.md",
        "role_hint": (
            "You are Codex, Round 2 (adversarial methodological review). Read "
            "docs/ai-collab/CONTEXT.md and docs/ai-collab/CLAUDE_REVIEW.md. "
            "Follow the 'Round 2 지시' in docs/ai-collab/CURRENT_TASK.md: find "
            "weak claims, leakage, missed experiments, or premature "
            "conclusions in Claude's diagnosis. Verify claims against the "
            "actual repository data where possible instead of taking them on "
            "faith. Write your findings to docs/ai-collab/CODEX_REVIEW.md "
            "only. Do not modify any other file. Do not commit, push, or "
            "reset git state."
        ),
    },
    "claude_round3": {
        "agent": "claude",
        "target_file": COLLAB_DIR / "DECISION.md",
        "role_hint": (
            "You are Claude Code, Round 3 (synthesis). Read "
            "docs/ai-collab/CONTEXT.md, CLAUDE_REVIEW.md, and CODEX_REVIEW.md. "
            "Verify Codex's claims against real data/code where checkable "
            "(do not just trust or just dismiss them). Run the minimum "
            "discriminating experiments that are feasible without new human "
            "labeling. Write docs/ai-collab/DECISION.md with exactly these "
            "sections: AGREED, DISAGREED, EVIDENCE NEEDED, ACTION. Do not "
            "modify any other file except DECISION.md. Do not commit, push, "
            "or reset git state."
        ),
    },
}

STEP_ORDER = ["claude_round1", "codex_round2", "claude_round3"]


def file_hash(path: Path) -> str:
    if not path.exists():
        return ""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def step_is_done(step: str) -> bool:
    target = STEPS[step]["target_file"]
    if not target.exists():
        return False
    text = target.read_text(encoding="utf-8")
    return PENDING_MARKER not in text and text.strip() != ""


def build_command(step: str) -> list[str]:
    """Build the argv for a step. The prompt itself is NOT included here --
    it is piped over stdin (see run_step) so that Windows shell quoting
    (cmd.exe, invoked because claude/codex are npm .cmd shims) can never
    corrupt prompt text that contains quotes, parentheses, or Korean text."""
    spec = STEPS[step]
    if spec["agent"] == "claude":
        return [
            "claude",
            "-p",
            "--permission-mode",
            "acceptEdits",
            "--allowedTools",
            CLAUDE_ALLOWED_TOOLS,
            "--verbose",
        ]
    if spec["agent"] == "codex":
        return [
            "codex",
            "exec",
            "--sandbox",
            "workspace-write",
            "-c",
            "approval_policy=never",
            "-C",
            str(ROOT),
            "-",
        ]
    raise ValueError(f"unknown agent for step {step!r}")


def log_run(step: str, command: list[str], exit_code: int, changed: bool) -> None:
    RUN_LOG.parent.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.datetime.now().isoformat(timespec="seconds")
    with RUN_LOG.open("a", encoding="utf-8") as handle:
        handle.write(f"{timestamp}\tstep={step}\texit={exit_code}\tfile_changed={changed}\tcmd={command}\n")


def run_step(step: str, dry_run: bool) -> None:
    target = STEPS[step]["target_file"]
    command = build_command(step)
    prompt = STEPS[step]["role_hint"]
    print(f"\n=== {step} ({STEPS[step]['agent']}) -> {target.relative_to(ROOT)} ===")
    print("command:", " ".join(f'"{c}"' if " " in c else c for c in command))
    print("prompt (piped via stdin):")
    print(prompt)

    if dry_run:
        print("(dry run, not executing)")
        return

    before = file_hash(target)
    # On Windows, npm-installed CLIs (claude, codex) are .cmd shims; CreateProcess
    # cannot exec those directly without going through the shell. shell=True here
    # is safe because `command` is always a fixed list of args we constructed
    # ourselves (never raw user/agent-supplied shell text). The prompt itself
    # goes over stdin, not argv, so shell quoting never touches it.
    use_shell = sys.platform == "win32"
    result = subprocess.run(command, cwd=ROOT, shell=use_shell, input=prompt, text=True, encoding="utf-8")
    after = file_hash(target)
    changed = before != after
    log_run(step, command, result.returncode, changed)

    if result.returncode != 0:
        raise SystemExit(f"{step} failed: {STEPS[step]['agent']} exited with code {result.returncode}")
    if not changed:
        raise SystemExit(
            f"{step} ran but {target.relative_to(ROOT)} did not change. "
            "Refusing to continue to the next step -- check the agent's output above."
        )
    print(f"=== {step} done, {target.relative_to(ROOT)} updated ===")


def print_status() -> None:
    for step in STEP_ORDER:
        target = STEPS[step]["target_file"]
        state = "done" if step_is_done(step) else "pending"
        print(f"{step:16s} [{state:7s}] {target.relative_to(ROOT)}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--step", choices=STEP_ORDER, help="run exactly one step regardless of current state")
    parser.add_argument("--dry-run", action="store_true", help="print the commands that would run, without executing")
    parser.add_argument("--status", action="store_true", help="print which steps are done/pending and exit")
    return parser


def main() -> None:
    args = build_parser().parse_args()

    if args.status:
        print_status()
        return

    if args.step:
        run_step(args.step, args.dry_run)
        return

    for step in STEP_ORDER:
        if step_is_done(step) and not args.dry_run:
            print(f"skip {step}: {STEPS[step]['target_file'].relative_to(ROOT)} already has content")
            continue
        run_step(step, args.dry_run)


if __name__ == "__main__":
    main()
