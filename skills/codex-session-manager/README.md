# Codex Session Manager

一个只依赖 Python 标准库的本地 Codex 会话管理工具，提供 CLI 和仅绑定 `127.0.0.1` 的 Web UI。

## 要求

- Python 3.10+
- 已安装且能被当前 Python 进程从 `PATH` 找到的 Codex CLI
- Codex CLI 版本需包含 `archive`、`unarchive`、`delete --force` 子命令

工具从 `$CODEX_HOME` 读取数据；未设置时使用 `~/.codex`。列表和详情只读扫描 `sessions`、`archived_sessions` 及 `session_index.jsonl`，归档和删除则始终调用官方 Codex CLI，不直接修改内部存储。

## CLI

```bash
python3 codex_sessions.py list
python3 codex_sessions.py list --json
python3 codex_sessions.py inspect <SESSION_ID>
python3 codex_sessions.py inspect <SESSION_ID> --json
python3 codex_sessions.py archive <SESSION_ID>
python3 codex_sessions.py unarchive <SESSION_ID>
python3 codex_sessions.py delete <SESSION_ID>
```

所有修改操作都要求完整 UUID。`delete` 会调用 `codex delete --force <SESSION_ID>`，属于不可恢复操作；不确定时应先用 `archive`。

可用 `CODEX_BINARY` 指定其他 Codex 可执行文件：

```bash
CODEX_BINARY=/path/to/codex python3 codex_sessions.py list
```

Windows PowerShell：

```powershell
$env:CODEX_BINARY = "C:\Users\me\.vscode\extensions\openai.chatgpt-<version>-win32-x64\bin\windows-x86_64\codex.exe"
python .\codex_sessions.py list
```

可以在 PowerShell 中用 `Get-Command codex` 检查 PATH；如果结果是 `codex.bat` 或 `codex.cmd`，
但 Python 仍找不到，可以将该文件的完整路径设置给 `CODEX_BINARY`。

## Web UI

```bash
python3 codex_sessions.py web
python3 codex_sessions.py web --open
python3 codex_sessions.py web --port 8765
```

默认自动选择空闲端口，并在标准输出打印 URL。页面支持按标题、cwd、状态和 ID 过滤，并提供 Archive、Unarchive 和 Delete 操作；删除前会再次确认。

HTTP API：

```text
GET    /api/sessions
GET    /api/sessions/<id>
DELETE /api/sessions/<id>
POST   /api/sessions/<id>/archive
POST   /api/sessions/<id>/unarchive
```
