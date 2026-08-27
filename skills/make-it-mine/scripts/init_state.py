#!/usr/bin/env python3
"""Initialize optional Make It Mine learning-state files.

Creates the human-readable map/log and the machine-readable event ledger from
bundled templates. Existing files are never overwritten.
"""

import argparse
from pathlib import Path
import shutil
from typing import Optional


def resolve_state_dir(scope: str = "project", state_dir: Optional[str] = None) -> Path:
    """Resolve a project-scoped or user-scoped state directory."""
    if state_dir:
        return Path(state_dir).expanduser().resolve()
    if scope == "user":
        return (Path.home() / ".make-it-mine").resolve()
    return (Path.cwd() / ".make-it-mine").resolve()


def initialize(state_dir: Path) -> None:
    skill_root = Path(__file__).resolve().parent.parent
    state_dir.mkdir(parents=True, exist_ok=True)

    files = {
        skill_root / "assets" / "CAPABILITY_MAP.md": state_dir / "CAPABILITY_MAP.md",
        skill_root / "assets" / "LEARNING_LOG.md": state_dir / "LEARNING_LOG.md",
    }

    for source, destination in files.items():
        if destination.exists():
            print(f"skip: {destination} already exists")
            continue
        shutil.copyfile(source, destination)
        print(f"created: {destination}")

    events_path = state_dir / "EVENTS.jsonl"
    if not events_path.exists():
        events_path.touch()
        print(f"created: {events_path}")

    print(f"State directory: {state_dir}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Initialize Make It Mine learning-state files.")
    parser.add_argument(
        "--scope",
        choices=("project", "user"),
        default="project",
        help="store state in the current project or user home (default: project)",
    )
    parser.add_argument(
        "--state-dir",
        help="use an explicit state directory instead of --scope",
    )
    args = parser.parse_args()
    target = resolve_state_dir(args.scope, args.state_dir)
    initialize(target)
    if args.scope == "project" and not args.state_dir:
        print("Optional: add '.make-it-mine/' to .gitignore if you want this state to stay personal.")


if __name__ == "__main__":
    main()
