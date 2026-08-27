#!/usr/bin/env python3
"""Inspect, export, import, and merge Make It Mine learning state.

Markdown is kept as the human-readable view. EVENTS.jsonl is an append-only,
machine-readable ledger used for stable IDs, export, and conflict-aware merge.
The script intentionally has no third-party dependencies.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import uuid
import zipfile
from collections import Counter
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from init_state import initialize, resolve_state_dir


FORMAT_NAME = "make-it-mine-bundle"
FORMAT_VERSION = 1
ENTRY_PATTERN = re.compile(r"^###\s+(\d{4}-\d{2}-\d{2})\s+—\s+(.+?)\s*$")
EVENT_MARKER_PATTERN = re.compile(r"<!--\s*make-it-mine:event:([^\s]+)\s*-->")
MAP_ROW_PATTERN = re.compile(r"^\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|")


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def generated_event_id(event_date: str, topic: str, context: str = "") -> str:
    payload = f"{event_date}\n{topic}\n{context}".encode("utf-8")
    return "legacy-" + hashlib.sha256(payload).hexdigest()[:20]


def normalize_event(raw: Dict[str, Any]) -> Dict[str, Any]:
    event = dict(raw)
    event_date = str(event.get("date", "")).strip()
    topic = str(event.get("topic", "")).strip()
    if not event_date or not topic:
        raise ValueError("event requires non-empty date and topic")
    date.fromisoformat(event_date)
    event["schema_version"] = int(event.get("schema_version", FORMAT_VERSION))
    event["date"] = event_date
    event["topic"] = topic
    context = str(event.get("context", ""))
    event["id"] = str(event.get("id") or generated_event_id(event_date, topic, context))
    event.setdefault("status", "unverified")
    return event


def semantic_fingerprint(event: Dict[str, Any]) -> str:
    comparable = dict(event)
    source_status = comparable.pop("source_status", None)
    comparable.pop("provenance", None)
    comparable.pop("fingerprint", None)
    if source_status is not None:
        comparable["status"] = source_status
    return hashlib.sha256(canonical_json(comparable).encode("utf-8")).hexdigest()


def state_location(args: argparse.Namespace) -> Path:
    return resolve_state_dir(args.scope, args.state_dir)


def require_state(args: argparse.Namespace) -> Path:
    directory = state_location(args)
    if not directory.is_dir():
        raise SystemExit(
            f"Learning state not found: {directory}\n"
            f"Run: python {Path(__file__).resolve()} init --scope {args.scope}"
        )
    return directory


def parse_event_lines(text: str, source: str = "EVENTS.jsonl") -> List[Dict[str, Any]]:
    events: List[Dict[str, Any]] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            raw = json.loads(line)
            if not isinstance(raw, dict):
                raise ValueError("event must be a JSON object")
            events.append(normalize_event(raw))
        except (json.JSONDecodeError, TypeError, ValueError) as error:
            raise ValueError(f"invalid {source} line {line_number}: {error}") from error
    return events


def markdown_events(text: str, source: str = "LEARNING_LOG.md") -> List[Dict[str, Any]]:
    events: List[Dict[str, Any]] = []
    seen: Counter = Counter()
    lines = text.splitlines()
    for index, line in enumerate(lines):
        match = ENTRY_PATTERN.match(line.strip())
        if not match:
            continue
        event_date, topic = match.groups()
        seen[(event_date, topic)] += 1
        suffix = f"-{seen[(event_date, topic)]}" if seen[(event_date, topic)] > 1 else ""
        marker = None
        for following_line in lines[index + 1 : index + 5]:
            marker_match = EVENT_MARKER_PATTERN.search(following_line)
            if marker_match:
                marker = marker_match.group(1)
                break
        event = normalize_event(
            {
                "id": marker or generated_event_id(event_date, topic + suffix),
                "date": event_date,
                "topic": topic,
                "status": "unverified",
                "provenance": {"kind": "markdown", "source": source},
            }
        )
        events.append(event)
    return events


def read_ledger(directory: Path) -> List[Dict[str, Any]]:
    ledger_path = directory / "EVENTS.jsonl"
    events: List[Dict[str, Any]] = []
    if ledger_path.exists():
        events.extend(parse_event_lines(ledger_path.read_text(encoding="utf-8")))

    known_ids = {event["id"] for event in events}
    log_path = directory / "LEARNING_LOG.md"
    if log_path.exists():
        for event in markdown_events(log_path.read_text(encoding="utf-8")):
            if event["id"] not in known_ids:
                events.append(event)
                known_ids.add(event["id"])
    return events


def event_lines(events: Iterable[Dict[str, Any]]) -> str:
    rendered = [canonical_json(normalize_event(event)) for event in events]
    return "\n".join(rendered) + ("\n" if rendered else "")


def ledger_events(directory: Path) -> List[Dict[str, Any]]:
    ledger_path = directory / "EVENTS.jsonl"
    if not ledger_path.exists():
        return []
    return parse_event_lines(ledger_path.read_text(encoding="utf-8"))


def materialize_legacy_events(directory: Path) -> List[Dict[str, Any]]:
    all_events = read_ledger(directory)
    existing = {event["id"] for event in ledger_events(directory)}
    missing = [event for event in all_events if event["id"] not in existing]
    if missing:
        ledger_path = directory / "EVENTS.jsonl"
        with ledger_path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(event_lines(missing))
    return all_events


def filtered_events(args: argparse.Namespace) -> List[Dict[str, Any]]:
    events = read_ledger(require_state(args))
    if args.since:
        events = [event for event in events if date.fromisoformat(event["date"]) >= args.since]
    if args.until:
        events = [event for event in events if date.fromisoformat(event["date"]) <= args.until]
    return sorted(events, key=lambda event: (event["date"], event["topic"]), reverse=True)


def show_list(args: argparse.Namespace) -> None:
    events = filtered_events(args)
    print(f"Learning entries: {len(events)}")
    for event in events:
        status = event.get("status", "unverified")
        print(f"{event['date']}  [{status}] {event['topic']}  ({event['id']})")


def show_stats(args: argparse.Namespace) -> None:
    directory = require_state(args)
    events = filtered_events(args)
    by_date = Counter(event["date"] for event in events)
    by_month = Counter(event["date"][:7] for event in events)
    by_status = Counter(event.get("status", "unverified") for event in events)

    print(f"Learning entries: {len(events)}")
    print(f"Active days: {len(by_date)}")
    print("By date:")
    for key, count in sorted(by_date.items(), reverse=True):
        print(f"  {key}: {count}")
    if not by_date:
        print("  none")
    print("By month:")
    for key, count in sorted(by_month.items(), reverse=True):
        print(f"  {key}: {count}")
    if not by_month:
        print("  none")
    print("Event status:")
    for key, count in sorted(by_status.items()):
        print(f"  {key}: {count}")

    levels = Counter()
    map_path = directory / "CAPABILITY_MAP.md"
    if map_path.exists():
        for line in map_path.read_text(encoding="utf-8").splitlines():
            match = MAP_ROW_PATTERN.match(line.strip())
            if not match or match.group(1).strip() == "Domain":
                continue
            if all(set(field.strip()) <= {"-"} for field in match.groups()):
                continue
            levels[match.group(3).strip()] += 1
    print("Capability levels:")
    if levels:
        for key, count in sorted(levels.items()):
            print(f"  {key}: {count}")
    else:
        print("  none")


def show_map(args: argparse.Namespace) -> None:
    directory = require_state(args)
    map_path = directory / "CAPABILITY_MAP.md"
    if not map_path.exists():
        print("Capability map is missing.")
        return
    print(map_path.read_text(encoding="utf-8"), end="")


def show_paths(args: argparse.Namespace) -> None:
    directory = require_state(args)
    print(f"state: {directory}")
    print(f"map:   {directory / 'CAPABILITY_MAP.md'}")
    print(f"log:   {directory / 'LEARNING_LOG.md'}")
    print(f"data:  {directory / 'EVENTS.jsonl'}")


def show_conflicts(args: argparse.Namespace) -> None:
    directory = require_state(args)
    conflicts_path = directory / "MERGE_CONFLICTS.jsonl"
    if not conflicts_path.exists() or not conflicts_path.read_text(encoding="utf-8").strip():
        print("Merge conflicts: 0")
        return
    conflicts = parse_event_lines(conflicts_path.read_text(encoding="utf-8"), "MERGE_CONFLICTS.jsonl")
    print(f"Merge conflicts: {len(conflicts)}")
    for conflict in conflicts:
        print(f"{conflict.get('date', '?')}  {conflict.get('topic', conflict.get('id', '?'))}")


def source_from_path(input_path: Path) -> Tuple[List[Dict[str, Any]], Dict[str, bytes], Dict[str, Any], str]:
    if input_path.is_dir():
        events = read_ledger(input_path)
        artifacts: Dict[str, bytes] = {}
        for name in ("CAPABILITY_MAP.md", "LEARNING_LOG.md"):
            path = input_path / name
            if path.exists():
                artifacts[name] = path.read_bytes()
        return events, artifacts, {}, str(input_path)

    if not input_path.exists():
        raise SystemExit(f"Import source not found: {input_path}")
    if not zipfile.is_zipfile(input_path):
        raise SystemExit("Import source must be a learning bundle .zip or a state directory")

    with zipfile.ZipFile(input_path, "r") as bundle:
        names = set(bundle.namelist())
        manifest: Dict[str, Any] = {}
        if "manifest.json" in names:
            manifest = json.loads(bundle.read("manifest.json").decode("utf-8"))
            if manifest.get("format") != FORMAT_NAME:
                raise SystemExit("Unsupported learning bundle format")
        if "EVENTS.jsonl" in names:
            events = parse_event_lines(bundle.read("EVENTS.jsonl").decode("utf-8"), "EVENTS.jsonl")
        elif "LEARNING_LOG.md" in names:
            events = markdown_events(bundle.read("LEARNING_LOG.md").decode("utf-8"))
        else:
            raise SystemExit("Learning bundle has no EVENTS.jsonl or LEARNING_LOG.md")
        artifacts = {
            name: bundle.read(name)
            for name in ("CAPABILITY_MAP.md", "LEARNING_LOG.md")
            if name in names
        }
    return events, artifacts, manifest, str(input_path)


def render_log_entry(event: Dict[str, Any]) -> str:
    marker = f"<!-- make-it-mine:event:{event['id']} -->"
    lines = [
        f"### {event['date']} — {event['topic']}",
        marker,
        "",
        f"**Status:** {event.get('status', 'unverified')}",
    ]
    if event.get("source_status"):
        lines.append(f"**Original status:** {event['source_status']}")
    if event.get("provenance"):
        source = event["provenance"].get("source", "unknown")
        lines.append(f"**Imported from:** {source}")
    for field, label in (
        ("context", "Context"),
        ("owned_judgment", "Owned judgment gained"),
        ("owned_decisions", "Owned decisions"),
        ("assisted_decisions", "Borrowed / assisted decisions"),
        ("capability_evidence", "Capability evidence"),
        ("transfer_question", "Transfer question"),
        ("next_growth_target", "Next growth target"),
    ):
        value = event.get(field)
        if not value:
            continue
        lines.extend(["", f"**{label}:**"])
        values = value if isinstance(value, list) else [value]
        lines.extend(f"- {item}" for item in values)
    return "\n".join(lines) + "\n"


def append_log_entries(directory: Path, events: Iterable[Dict[str, Any]]) -> None:
    log_path = directory / "LEARNING_LOG.md"
    if log_path.exists():
        existing_text = log_path.read_text(encoding="utf-8")
    else:
        existing_text = "# Learning Log\n\n"

    additions: List[str] = []
    for event in events:
        marker = f"<!-- make-it-mine:event:{event['id']} -->"
        if marker not in existing_text:
            additions.append(render_log_entry(event))
    if additions:
        separator = "\n" if not existing_text.endswith("\n\n") else ""
        log_path.write_text(existing_text + separator + "\n".join(additions), encoding="utf-8")


def write_conflicts(directory: Path, conflicts: Iterable[Dict[str, Any]]) -> None:
    conflicts = list(conflicts)
    if not conflicts:
        return
    path = directory / "MERGE_CONFLICTS.jsonl"
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        for conflict in conflicts:
            handle.write(canonical_json(conflict) + "\n")


def save_import_artifacts(
    directory: Path,
    artifacts: Dict[str, bytes],
    manifest: Dict[str, Any],
    source_label: str,
) -> Optional[Path]:
    if not artifacts:
        return None
    bundle_id = str(manifest.get("bundle_id") or hashlib.sha256(source_label.encode("utf-8")).hexdigest()[:16])
    safe_id = re.sub(r"[^A-Za-z0-9._-]", "-", bundle_id)
    import_dir = directory / "imports" / safe_id
    import_dir.mkdir(parents=True, exist_ok=True)
    for name, content in artifacts.items():
        destination = import_dir / name
        if not destination.exists():
            destination.write_bytes(content)
    return import_dir


def merge_source(args: argparse.Namespace) -> None:
    target = state_location(args)
    if not target.exists():
        initialize(target)
    source_path = Path(args.input).expanduser().resolve()
    incoming, artifacts, manifest, source_label = source_from_path(source_path)
    target_events = materialize_legacy_events(target)
    by_id = {event["id"]: event for event in target_events}
    additions: List[Dict[str, Any]] = []
    conflicts: List[Dict[str, Any]] = []
    skipped = 0
    imported_at = utc_now()

    for raw in incoming:
        source_event = normalize_event(raw)
        event_id = source_event["id"]
        if event_id in by_id:
            if semantic_fingerprint(by_id[event_id]) == semantic_fingerprint(source_event):
                skipped += 1
            else:
                conflicts.append(
                    {
                        "schema_version": FORMAT_VERSION,
                        "id": event_id,
                        "date": source_event["date"],
                        "topic": source_event["topic"],
                        "status": "conflict",
                        "created_at": imported_at,
                        "source": source_label,
                        "existing": by_id[event_id],
                        "incoming": source_event,
                    }
                )
            continue

        imported_event = dict(source_event)
        imported_event["source_status"] = imported_event.get("status", "unverified")
        imported_event["status"] = "imported"
        imported_event["provenance"] = {
            "kind": "import",
            "source": source_label,
            "imported_at": imported_at,
        }
        additions.append(imported_event)
        by_id[event_id] = imported_event

    if args.dry_run:
        print(f"Would import: {len(additions)}")
        print(f"Would skip: {skipped}")
        print(f"Would conflict: {len(conflicts)}")
        return

    if additions:
        ledger_path = target / "EVENTS.jsonl"
        with ledger_path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(event_lines(additions))
        append_log_entries(target, additions)
    write_conflicts(target, conflicts)
    artifact_dir = save_import_artifacts(target, artifacts, manifest, source_label)
    print(f"Imported: {len(additions)}")
    print(f"Skipped duplicates: {skipped}")
    print(f"Conflicts: {len(conflicts)}")
    if artifact_dir:
        print(f"Source snapshots: {artifact_dir}")
    if conflicts:
        print(f"Review: {target / 'MERGE_CONFLICTS.jsonl'}")


def export_bundle(args: argparse.Namespace) -> None:
    directory = require_state(args)
    events = materialize_legacy_events(directory)
    output = Path(args.output).expanduser().resolve()
    if output.exists() and not args.force:
        raise SystemExit(f"Output already exists; use --force to replace it: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    manifest = {
        "format": FORMAT_NAME,
        "version": FORMAT_VERSION,
        "bundle_id": uuid.uuid4().hex,
        "exported_at": utc_now(),
        "event_count": len(events),
        "source_state": str(directory),
    }
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
        bundle.writestr("manifest.json", canonical_json(manifest) + "\n")
        bundle.writestr("EVENTS.jsonl", event_lines(events))
        for name in ("CAPABILITY_MAP.md", "LEARNING_LOG.md", "MERGE_CONFLICTS.jsonl"):
            path = directory / name
            if path.exists():
                bundle.write(path, name)
    print(f"Exported: {output}")
    print(f"Events: {len(events)}")


def add_location_args(parser: argparse.ArgumentParser, default_scope: str = "user") -> None:
    parser.add_argument(
        "--scope",
        choices=("project", "user"),
        default=default_scope,
        help=f"state scope (default: {default_scope})",
    )
    parser.add_argument("--state-dir", help="explicit state directory")


def add_date_filters(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--since", type=parse_date, help="include entries on/after YYYY-MM-DD")
    parser.add_argument("--until", type=parse_date, help="include entries on/before YYYY-MM-DD")


def parse_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("date must use YYYY-MM-DD") from error


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="make-it-mine", description="Manage Make It Mine learning state.")
    commands = parser.add_subparsers(dest="command", required=True)

    init = commands.add_parser("init", help="create state files without overwriting existing files")
    add_location_args(init)
    init.set_defaults(handler=lambda args: initialize(state_location(args)))

    show = commands.add_parser("show", help="show learning state")
    show_commands = show.add_subparsers(dest="show_command", required=True)

    list_command = show_commands.add_parser("list", help="list dated learning entries")
    add_location_args(list_command)
    add_date_filters(list_command)
    list_command.set_defaults(handler=show_list)

    stats_command = show_commands.add_parser("stats", help="show date, status, and capability statistics")
    add_location_args(stats_command)
    add_date_filters(stats_command)
    stats_command.set_defaults(handler=show_stats)

    map_command = show_commands.add_parser("map", help="print the capability map")
    add_location_args(map_command)
    map_command.set_defaults(handler=show_map)

    paths_command = show_commands.add_parser("paths", help="show state file paths")
    add_location_args(paths_command)
    paths_command.set_defaults(handler=show_paths)

    conflicts_command = show_commands.add_parser("conflicts", help="list unresolved merge conflicts")
    add_location_args(conflicts_command)
    conflicts_command.set_defaults(handler=show_conflicts)

    export = commands.add_parser("export", help="export a portable learning bundle")
    add_location_args(export)
    export.add_argument("--output", required=True, help="output .zip path")
    export.add_argument("--force", action="store_true", help="replace an existing output file")
    export.set_defaults(handler=export_bundle)

    for name, help_text in (
        ("import", "import and merge a learning bundle or state directory"),
        ("merge", "alias for import; merge by stable event ID"),
    ):
        merge = commands.add_parser(name, help=help_text)
        add_location_args(merge)
        merge.add_argument("--input", required=True, help="learning bundle .zip or state directory")
        merge.add_argument("--dry-run", action="store_true", help="report changes without writing files")
        merge.set_defaults(handler=merge_source)

    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        args.handler(args)
    except BrokenPipeError:
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
