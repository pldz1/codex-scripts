---
name: codex-session-manager
description: List, inspect, archive, unarchive, and permanently delete local Codex CLI sessions by UUID through a dependency-free Python CLI and localhost Web UI. Use when the user asks to find, review, organize, archive, restore, or delete saved local Codex sessions.
---

# Codex Session Manager

Use `codex_sessions.py` in this skill directory for every session-management operation.

## Workflow

1. List sessions before changing them:

   ```bash
   python3 <skill-dir>/codex_sessions.py list
   python3 <skill-dir>/codex_sessions.py list --json
   ```

2. Resolve the target by its full UUID and inspect it when useful:

   ```bash
   python3 <skill-dir>/codex_sessions.py inspect <SESSION_ID>
   ```

3. Prefer archiving when the user has not explicitly requested permanent deletion:

   ```bash
   python3 <skill-dir>/codex_sessions.py archive <SESSION_ID>
   python3 <skill-dir>/codex_sessions.py unarchive <SESSION_ID>
   ```

4. Run deletion only after the user clearly identifies the session and requests permanent deletion:

   ```bash
   python3 <skill-dir>/codex_sessions.py delete <SESSION_ID>
   ```

5. Start the local UI when the user wants to browse sessions interactively:

   ```bash
   python3 <skill-dir>/codex_sessions.py web --open
   ```

## Safety and behavior

- Treat `delete` as irreversible. Never infer a deletion target from a partial ID.
- Use only full session UUIDs for mutations.
- Read session metadata from `$CODEX_HOME` (default `~/.codex`) without changing Codex's internal files.
- Let the script invoke official `codex archive`, `codex unarchive`, and `codex delete --force` commands for mutations.
- Bind the Web UI only to `127.0.0.1`; do not expose it on the network.
- Report command failures verbatim enough to diagnose them, but do not expose transcript contents unless the user separately asks to read them.
