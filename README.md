# Codex 配置辅助脚本

这组脚本用于清理 Codex 本地运行数据，以及在任务结束时发送桌面通知。Windows 与 Ubuntu 版本的行为保持一致。

> `clean` 会删除 `sessions`、临时目录、日志和本地数据库等运行数据。`auth.json` 与 `config.toml` 始终受保护，但执行前仍建议先使用预览模式确认范围。

## 文件说明

| 系统 | 清理脚本 | 通知脚本 |
| --- | --- | --- |
| Windows | `windows/clean.ps1` | `windows/notify.ps1` |
| Ubuntu | `ubuntu/clean.sh` | `ubuntu/notify.sh` |

文件名 `notify` 沿用仓库现有 Windows 脚本的命名。

## Ubuntu

### 1. 安装依赖并授予执行权限

Ubuntu 通知脚本使用 `notify-send`，并使用 Python 3 解析 Codex 传入的 JSON：

```bash
sudo apt update
sudo apt install -y libnotify-bin python3
chmod +x ubuntu/clean.sh ubuntu/notify.sh
```

### 2. 配置任务完成通知

编辑用户级 `~/.codex/config.toml`，把路径替换为仓库的绝对路径：

```toml
notify = ["bash", "/absolute/path/to/codex-config-ref/ubuntu/notify.sh"]
```

Codex 会把通知事件作为 JSON 参数追加到命令后面。通知脚本会读取任务结果、事件类型和工作目录；无法解析 JSON 时，则直接把参数作为通知正文。

可以先手动测试：

```bash
./ubuntu/notify.sh '{"type":"agent-turn-complete","cwd":"/tmp/demo","last-assistant-message":"任务已经完成"}'
```

可选参数必须写在通知正文之前：

```bash
./ubuntu/notify.sh --title "My Codex" --duration 5000 "测试通知"
```

`--duration` 的单位是毫秒。部分 Ubuntu 桌面环境可能忽略应用指定的显示时长。

### 3. 清理 Codex 运行数据

先预览将要删除的内容：

```bash
./ubuntu/clean.sh --dry-run
```

确认后执行：

```bash
./ubuntu/clean.sh
```

脚本默认清理 `~/.codex`。如果设置了 `CODEX_HOME`，则清理该目录；脚本会拒绝把根目录或用户主目录作为清理目标。

## Windows

### 配置任务完成通知

编辑用户级 `%USERPROFILE%\.codex\config.toml`，把路径替换为脚本的绝对路径。TOML 基本字符串中的反斜杠需要写成双反斜杠：

```toml
notify = ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", "D:\\path\\to\\codex-config-ref\\windows\\notify.ps1"]
```

手动测试：

```powershell
.\windows\notify.ps1 '{"type":"agent-turn-complete","cwd":"C:\\Temp\\demo","last-assistant-message":"任务已经完成"}'
```

### 清理 Codex 运行数据

先使用 PowerShell 的 `-WhatIf` 预览：

```powershell
.\windows\clean.ps1 -WhatIf
```

确认后执行：

```powershell
.\windows\clean.ps1
```

Windows 脚本清理 `%USERPROFILE%\.codex`，并保留 `auth.json` 和 `config.toml`。

## 清理范围

清理脚本会处理以下内容：

- 目录：`sessions`、`.tmp`、`tmp`、`shell_snapshots`、`memories`
- 顶层文件：`log*`、`*.json`、`*.sqlite*`、`*.jsonl`、`*.log`
- 指定文件：`cap_sid`、`.tmp`
- 永久保护：`auth.json`、`config.toml`

通知配置必须放在用户级 `~/.codex/config.toml` 中；Codex 不接受项目级 `.codex/config.toml` 覆盖 `notify`。配置字段说明见 [Codex Configuration Reference](https://developers.openai.com/codex/config-reference)。
