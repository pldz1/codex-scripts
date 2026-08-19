# Skills

> 最后更新：2026-08-20

## Codex Session Manager

[`codex-session-manager/`](codex-session-manager/) 提供无第三方依赖的 Python CLI 和本地 Web UI，用完整 UUID 列出、检查、归档、恢复或删除 Codex 会话。

```bash
python3 codex-session-manager/codex_sessions.py list
python3 codex-session-manager/codex_sessions.py web --open
```

详情及删除安全说明见 [`codex-session-manager/README.md`](codex-session-manager/README.md)。

## Azure GPT-Image-2 Codex skill

本仓库提供 [`azure-image-gen/`](azure-image-gen/) skill，通过用户自己的 Azure OpenAI GPT-Image-2 部署生成图片文件。

### 安装

在 WSL/Linux 中将 skill 复制到 Codex skill 目录：

```bash
mkdir -p ~/.agents/skills
cp -R skills/azure-image-gen ~/.agents/skills/
```

仓库当前没有 `install.sh` 或预打包压缩包；复制完成后即可使用。

### 配置

设置以下环境变量（密钥不要写入仓库、命令参数或 `auth.json`）：

```bash
export AZURE_OPENAI_API_KEY='...'
export AZURE_OPENAI_ENDPOINT='https://YOUR-RESOURCE.openai.azure.com/'
export AZURE_OPENAI_IMAGE_DEPLOYMENT='YOUR-DEPLOYMENT-NAME'
export AZURE_OPENAI_IMAGE_API_VERSION='preview'  # 可选
```

持久化配置和权限建议见 [`azure-image-gen/references/configuration.md`](azure-image-gen/references/configuration.md)。

### 检查与生成

```bash
python3 ~/.agents/skills/azure-image-gen/scripts/azure_image_generate.py --check
python3 ~/.agents/skills/azure-image-gen/scripts/azure_image_generate.py \
  --size 1024x1024 --quality high --format png --output-dir ./generated-images <<'PROMPT'
A cinematic concept image of ...
PROMPT
```

也可以在 Codex 中显式调用：

```text
$azure-image-gen 生成一张 1536x1024 的电影感概念图，保存到当前项目。
```

完整工作流、尺寸限制和错误处理见 [`azure-image-gen/SKILL.md`](azure-image-gen/SKILL.md)。
