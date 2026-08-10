# Codex 辅助工具

这个项目提供 Codex 本地运行数据清理、任务完成桌面通知，以及通过 Azure Image Gen 生成图片的 Codex skill。清理和通知脚本同时支持 Windows 与 Ubuntu，且行为保持一致。

> `clean` 会删除 `sessions`、临时目录、日志和本地数据库等运行数据。`auth.json` 与 `config.toml` 始终受保护，但执行前仍建议先使用预览模式确认范围。

## 项目内容

| 类型 | 路径 | 说明 |
| --- | --- | --- |
| Windows 脚本 | `windows/` | 清理 Codex 运行数据并发送桌面通知 |
| Ubuntu 脚本 | `ubuntu/` | 清理 Codex 运行数据并发送桌面通知 |
| Azure Image Gen skill | `skills/azure-image-gen/` | 通过 Azure 图片生成部署创建图片文件 |

文件名 `notify` 沿用仓库现有 Windows 脚本的命名。

## Azure Image Gen skill

`azure-image-gen` 是一个本地 Codex skill，可通过自己的 Azure 图片生成部署创建图片。当内置图片生成工具不可用，或需要使用指定 Azure 资源时，可以调用这个 skill。

### 1. 安装

在 WSL 或 Linux 中，将 skill 复制到本地 skills 目录：

```bash
mkdir -p ~/.agents/skills
cp -R skills/azure-image-gen ~/.agents/skills/
```

### 2. 配置 Azure

设置以下环境变量：

```bash
export AZURE_OPENAI_API_KEY='...'
export AZURE_OPENAI_ENDPOINT='https://YOUR-RESOURCE.openai.azure.com/'
export AZURE_OPENAI_IMAGE_DEPLOYMENT='YOUR-DEPLOYMENT-NAME'
```

API 版本可按需覆盖，默认值为 `preview`：

```bash
export AZURE_OPENAI_IMAGE_API_VERSION='preview'
```

密钥不要写入 Git 仓库、`SKILL.md`、命令参数或 `~/.codex/auth.json`。持久化配置方式见 [`skills/azure-image-gen/references/configuration.md`](skills/azure-image-gen/references/configuration.md)。

### 3. 检查配置

```bash
python3 ~/.agents/skills/azure-image-gen/scripts/azure_image_generate.py --check
```

该命令只检查配置状态，不会输出 API 密钥。

### 4. 在 Codex 中使用

显式调用：

```text
$azure-image-gen 生成一张 1536x1024 的电影感概念图，保存到当前项目。
```

该 skill 也允许隐式调用，因此可以直接向 Codex 提出图片生成请求。详细工作流程和参数约束见 [`skills/azure-image-gen/SKILL.md`](skills/azure-image-gen/SKILL.md)。

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
notify = ["bash", "/absolute/path/to/codex-scripts/ubuntu/notify.sh"]
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
notify = ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", "D:\\path\\to\\codex-scripts\\windows\\notify.ps1"]
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
