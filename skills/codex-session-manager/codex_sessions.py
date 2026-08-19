#!/usr/bin/env python3
"""List and manage local Codex sessions with no third-party dependencies."""

from __future__ import annotations

import argparse
import dataclasses
import datetime as dt
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import threading
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Iterable


UUID_RE = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)
SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
WEB_FILE = SCRIPT_DIR / "web" / "index.html"


class SessionError(RuntimeError):
    """Base error for session operations."""


class SessionNotFound(SessionError):
    pass


class SessionConflict(SessionError):
    pass


class CodexCommandError(SessionError):
    pass


@dataclasses.dataclass(frozen=True)
class Session:
    id: str
    title: str
    cwd: str
    updated_at: str
    created_at: str
    archived: bool
    source: Any
    model_provider: str
    cli_version: str
    path: str
    size_bytes: int

    def as_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


class SessionBackend:
    """Read local Codex metadata and delegate mutations to the Codex CLI."""

    def __init__(
        self,
        codex_home: pathlib.Path | None = None,
        codex_binary: str | None = None,
    ) -> None:
        configured_home = os.environ.get("CODEX_HOME")
        self.codex_home = (
            codex_home
            or (pathlib.Path(configured_home).expanduser() if configured_home else None)
            or pathlib.Path.home() / ".codex"
        ).resolve()
        self.codex_binary = codex_binary or os.environ.get("CODEX_BINARY", "codex")

    def _index_entries(self) -> dict[str, dict[str, str]]:
        result: dict[str, dict[str, str]] = {}
        index = self.codex_home / "session_index.jsonl"
        try:
            with index.open(encoding="utf-8") as handle:
                for line in handle:
                    try:
                        item = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    session_id = item.get("id")
                    if not isinstance(session_id, str):
                        continue
                    entry: dict[str, str] = {}
                    title = item.get("thread_name")
                    updated_at = item.get("updated_at")
                    if isinstance(title, str) and title.strip():
                        entry["title"] = title.strip()
                    if isinstance(updated_at, str) and updated_at.strip():
                        entry["updated_at"] = updated_at.strip()
                    if entry:
                        result[session_id.lower()] = entry
        except (FileNotFoundError, OSError):
            pass
        return result

    def _session_files(self) -> Iterable[tuple[pathlib.Path, bool]]:
        roots = (
            (self.codex_home / "sessions", False),
            (self.codex_home / "archived_sessions", True),
        )
        for root, archived in roots:
            if root.is_dir():
                for path in root.rglob("*.jsonl"):
                    if path.is_file():
                        yield path, archived

    @staticmethod
    def _read_metadata(path: pathlib.Path) -> dict[str, Any] | None:
        try:
            with path.open(encoding="utf-8") as handle:
                first_line = handle.readline()
            record = json.loads(first_line)
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            return None
        if record.get("type") != "session_meta":
            return None
        payload = record.get("payload")
        return payload if isinstance(payload, dict) else None

    @staticmethod
    def _iso_timestamp(value: Any, fallback: float) -> str:
        if isinstance(value, str) and value.strip():
            try:
                parsed = dt.datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
                if parsed.tzinfo is None:
                    parsed = parsed.replace(tzinfo=dt.timezone.utc)
                return parsed.astimezone(dt.timezone.utc).isoformat().replace("+00:00", "Z")
            except ValueError:
                pass
        return dt.datetime.fromtimestamp(fallback, dt.timezone.utc).isoformat().replace(
            "+00:00", "Z"
        )

    def _load_session(
        self, path: pathlib.Path, archived: bool, index: dict[str, dict[str, str]]
    ) -> Session | None:
        metadata = self._read_metadata(path)
        if not metadata:
            return None
        raw_id = metadata.get("id") or metadata.get("session_id")
        if not isinstance(raw_id, str) or not UUID_RE.fullmatch(raw_id):
            return None
        stat = path.stat()
        session_id = raw_id.lower()
        index_entry = index.get(session_id, {})
        return Session(
            id=session_id,
            title=index_entry.get("title", session_id),
            cwd=str(metadata.get("cwd") or ""),
            updated_at=self._iso_timestamp(index_entry.get("updated_at"), stat.st_mtime),
            created_at=self._iso_timestamp(metadata.get("timestamp"), stat.st_ctime),
            archived=archived,
            source=metadata.get("source") or metadata.get("thread_source") or "",
            model_provider=str(metadata.get("model_provider") or ""),
            cli_version=str(metadata.get("cli_version") or ""),
            path=str(path),
            size_bytes=stat.st_size,
        )

    def list_sessions(self) -> list[Session]:
        index = self._index_entries()
        sessions: dict[str, Session] = {}
        for path, archived in self._session_files():
            session = self._load_session(path, archived, index)
            if session is None:
                continue
            previous = sessions.get(session.id)
            if previous is None or session.updated_at > previous.updated_at:
                sessions[session.id] = session
        return sorted(sessions.values(), key=lambda item: item.updated_at, reverse=True)

    def inspect_session(self, session_id: str) -> dict[str, Any]:
        normalized = self._validate_id(session_id)
        for session in self.list_sessions():
            if session.id == normalized:
                details = session.as_dict()
                details["event_count"] = self._count_lines(pathlib.Path(session.path))
                return details
        raise SessionNotFound(f"Session not found: {normalized}")

    @staticmethod
    def _count_lines(path: pathlib.Path) -> int:
        try:
            with path.open("rb") as handle:
                return sum(1 for _ in handle)
        except OSError as exc:
            raise SessionError(f"Could not read session file: {exc}") from exc

    @staticmethod
    def _validate_id(session_id: str) -> str:
        normalized = session_id.strip().lower()
        if not UUID_RE.fullmatch(normalized):
            raise SessionError("A full session UUID is required")
        return normalized

    def _existing(self, session_id: str) -> Session:
        normalized = self._validate_id(session_id)
        for session in self.list_sessions():
            if session.id == normalized:
                return session
        raise SessionNotFound(f"Session not found: {normalized}")

    def _run_codex(self, arguments: list[str]) -> None:
        if shutil.which(self.codex_binary) is None:
            raise CodexCommandError(f"Codex CLI executable not found: {self.codex_binary}")
        environment = os.environ.copy()
        environment["CODEX_HOME"] = str(self.codex_home)
        try:
            completed = subprocess.run(
                [self.codex_binary, *arguments],
                capture_output=True,
                text=True,
                check=False,
                timeout=60,
                env=environment,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise CodexCommandError(f"Could not run Codex CLI: {exc}") from exc
        if completed.returncode:
            message = completed.stderr.strip() or completed.stdout.strip()
            raise CodexCommandError(message or f"Codex exited with status {completed.returncode}")

    def delete_session(self, session_id: str) -> dict[str, Any]:
        session = self._existing(session_id)
        self._run_codex(["delete", "--force", session.id])
        return {"id": session.id, "operation": "deleted"}

    def archive_session(self, session_id: str) -> dict[str, Any]:
        session = self._existing(session_id)
        if session.archived:
            raise SessionConflict(f"Session is already archived: {session.id}")
        self._run_codex(["archive", session.id])
        return self.inspect_session(session.id)

    def unarchive_session(self, session_id: str) -> dict[str, Any]:
        session = self._existing(session_id)
        if not session.archived:
            raise SessionConflict(f"Session is not archived: {session.id}")
        self._run_codex(["unarchive", session.id])
        return self.inspect_session(session.id)


def _json_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, indent=2).encode("utf-8")


def make_handler(backend: SessionBackend, web_file: pathlib.Path) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        server_version = "CodexSessionManager/1.0"

        def _send(self, status: int, body: bytes, content_type: str) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header(
                "Content-Security-Policy",
                "default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'",
            )
            self.end_headers()
            self.wfile.write(body)

        def _send_json(self, status: int, value: Any) -> None:
            self._send(status, _json_bytes(value), "application/json; charset=utf-8")

        def _parts(self) -> list[str]:
            path = urllib.parse.urlsplit(self.path).path
            return [urllib.parse.unquote(part) for part in path.split("/") if part]

        def _handle_error(self, exc: Exception) -> None:
            if isinstance(exc, SessionNotFound):
                status = 404
            elif isinstance(exc, SessionConflict):
                status = 409
            elif isinstance(exc, CodexCommandError):
                status = 502
            elif isinstance(exc, SessionError):
                status = 400
            else:
                status = 500
            self._send_json(status, {"error": str(exc)})

        def _check_local_host(self) -> None:
            host = self.headers.get("Host", "")
            hostname = urllib.parse.urlsplit(f"//{host}").hostname
            if hostname not in {"127.0.0.1", "localhost"}:
                raise SessionError("Non-local Host header rejected")

        def _check_mutation_origin(self) -> None:
            origin = self.headers.get("Origin")
            if not origin:
                return
            expected = f"http://{self.headers.get('Host', '')}"
            if origin.rstrip("/") != expected:
                raise SessionError("Cross-origin mutation request rejected")

        def do_GET(self) -> None:  # noqa: N802
            try:
                self._check_local_host()
                parts = self._parts()
                if not parts:
                    self._send(200, web_file.read_bytes(), "text/html; charset=utf-8")
                elif parts == ["api", "sessions"]:
                    self._send_json(200, [item.as_dict() for item in backend.list_sessions()])
                elif len(parts) == 3 and parts[:2] == ["api", "sessions"]:
                    self._send_json(200, backend.inspect_session(parts[2]))
                else:
                    self._send_json(404, {"error": "Not found"})
            except Exception as exc:
                self._handle_error(exc)

        def do_DELETE(self) -> None:  # noqa: N802
            try:
                self._check_local_host()
                self._check_mutation_origin()
                parts = self._parts()
                if len(parts) != 3 or parts[:2] != ["api", "sessions"]:
                    self._send_json(404, {"error": "Not found"})
                    return
                self._send_json(200, backend.delete_session(parts[2]))
            except Exception as exc:
                self._handle_error(exc)

        def do_POST(self) -> None:  # noqa: N802
            try:
                self._check_local_host()
                self._check_mutation_origin()
                parts = self._parts()
                if len(parts) != 4 or parts[:2] != ["api", "sessions"]:
                    self._send_json(404, {"error": "Not found"})
                    return
                if parts[3] == "archive":
                    result = backend.archive_session(parts[2])
                elif parts[3] == "unarchive":
                    result = backend.unarchive_session(parts[2])
                else:
                    self._send_json(404, {"error": "Not found"})
                    return
                self._send_json(200, result)
            except Exception as exc:
                self._handle_error(exc)

        def log_message(self, format_string: str, *args: Any) -> None:
            print(f"{self.address_string()} - {format_string % args}", file=sys.stderr)

    return Handler


def serve(backend: SessionBackend, port: int, should_open: bool) -> None:
    if not WEB_FILE.is_file():
        raise SessionError(f"Web UI not found: {WEB_FILE}")
    server = ThreadingHTTPServer(("127.0.0.1", port), make_handler(backend, WEB_FILE))
    server.daemon_threads = True
    url = f"http://127.0.0.1:{server.server_port}/"
    print(url, flush=True)
    if should_open:
        threading.Timer(0.1, webbrowser.open, args=(url,)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server.", file=sys.stderr)
    finally:
        server.server_close()


def _print_mapping(mapping: dict[str, Any]) -> None:
    width = max(len(key) for key in mapping)
    for key, value in mapping.items():
        print(f"{key:<{width}}  {value}")


def _print_sessions(sessions: list[Session]) -> None:
    if not sessions:
        print("No Codex sessions found.")
        return
    print(f"{'UPDATED':20}  {'STATE':8}  {'TITLE':36}  SESSION ID")
    for item in sessions:
        updated = item.updated_at.replace("T", " ")[:19]
        title = item.title.replace("\n", " ")
        if len(title) > 36:
            title = title[:33] + "..."
        state = "archived" if item.archived else "active"
        print(f"{updated:20}  {state:8}  {title:36}  {item.id}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    list_parser = subparsers.add_parser("list", help="List active and archived sessions")
    list_parser.add_argument("--json", action="store_true", help="Print JSON")

    inspect_parser = subparsers.add_parser("inspect", help="Inspect one session")
    inspect_parser.add_argument("session_id")
    inspect_parser.add_argument("--json", action="store_true", help="Print JSON")

    for command in ("delete", "archive", "unarchive"):
        mutation_parser = subparsers.add_parser(command, help=f"{command.title()} one session")
        mutation_parser.add_argument("session_id")

    web_parser = subparsers.add_parser("web", help="Start the localhost Web UI")
    web_parser.add_argument("--open", action="store_true", help="Open a browser")
    web_parser.add_argument(
        "--port", type=int, default=0, help="Local port; default chooses a free port"
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    backend = SessionBackend()
    try:
        if args.command == "list":
            sessions = backend.list_sessions()
            if args.json:
                print(_json_bytes([item.as_dict() for item in sessions]).decode())
            else:
                _print_sessions(sessions)
        elif args.command == "inspect":
            details = backend.inspect_session(args.session_id)
            if args.json:
                print(_json_bytes(details).decode())
            else:
                _print_mapping(details)
        elif args.command == "delete":
            _print_mapping(backend.delete_session(args.session_id))
        elif args.command == "archive":
            _print_mapping(backend.archive_session(args.session_id))
        elif args.command == "unarchive":
            _print_mapping(backend.unarchive_session(args.session_id))
        elif args.command == "web":
            if not 0 <= args.port <= 65535:
                raise SessionError("Port must be between 0 and 65535")
            serve(backend, args.port, args.open)
    except SessionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
