# Codex Web Harness

一个运行在本机的轻量 Codex Web UI。浏览器通过 WebSocket 连接 Node 桥接服务，Node 再通过 stdio JSON-RPC 与 `codex app-server` 通讯。

Codex 的登录状态、配置和 session 仍由 Codex 自己管理；Web UI 不读取或保存 Codex 凭据。

## 功能

- 加载本机 Codex CLI、VS Code、exec、app-server 和 sub-agent sessions
- 创建、恢复、归档、取消归档、批量操作和删除 session
- 首次对话前选择 workspace；也可以通过环境变量预选
- 从真实 `model/list` 读取模型与 reasoning effort
- 流式显示回答、thinking、命令、工具调用、approval 和文件修改
- 粘贴或选择图片及常见文本/代码附件；图片支持点击预览
- 文件树、文本文件预览与编辑
- 按文件查看 Changes/Diff
- 显示 context window、compact 状态、账号 usage 和实时内存占用
- 支持部署在 `/codex/` 之类的反向代理子路径

## 目录说明

| 路径 | 用途 | 是否手工修改 |
| --- | --- | --- |
| `src/` | React/TSX 前端源码 | 是 |
| `server/` | Node/TypeScript 服务端源码 | 是 |
| `public/` | 原样复制的静态资源 | 是 |
| `scripts/` | Playwright 验证脚本 | 是 |
| `dist/` | Vite 生成的前端生产文件 | 否，可删除重建 |
| `dist-server/` | TypeScript 生成的服务端 JavaScript | 否，可删除重建 |

`server/` 与 `dist-server/` 不是两套源码：

```text
server/*.ts  -- npm run build -->  dist-server/*.js
src/*        -- npm run build -->  dist/*
```

仓库只维护 `src/` 和 `server/`。`dist/`、`dist-server/` 已加入 `.gitignore`，不要直接编辑或提交。当前生成目录被删除是正常的，执行 `npm run build` 会重新创建。

## 环境要求

- Node.js `^20.19.0` 或 `>=22.12.0`
- 已安装且可直接执行的 `codex` CLI
- Codex 已完成登录或配置好可用的认证方式

检查：

```bash
node --version
codex --version
```

## 开发运行

开发模式不需要 `dist/` 或 `dist-server/`：

```bash
cd /home/pldz/local/codex-scripts/web-ui
npm install
npm run dev
```

默认打开：

```text
http://127.0.0.1:8765/
```

前端修改由 Vite 即时加载，后端入口通过 `tsx server/index.ts --dev` 运行。

## 生产运行

生产模式必须先构建：

```bash
cd /home/pldz/local/codex-scripts/web-ui
npm install
npm run build
npm start
```

`npm run build` 会同时生成：

- `dist/`：浏览器静态资源
- `dist-server/`：Node 可执行 JavaScript

`npm start` 只负责启动已有构建，不会自动重新 build。修改 `src/` 或 `server/` 后，需要再次执行 `npm run build`。

`npm start` 实际执行：

```bash
node --max-old-space-size=256 dist-server/index.js
```

如果希望少一个 npm 父进程，也可以在 build 后直接运行上面的 Node 命令。

## 后台运行

项目提供 Linux/macOS shell 与 Windows PowerShell 两个生命周期脚本。它们直接启动 `dist-server/index.js`，关闭启动它们的终端后，Node 和自动创建的 `codex app-server` 仍会继续运行。

使用前必须完成一次生产构建：

```bash
npm run build
```

Linux/macOS：

```bash
./scripts/codex-web.sh start
./scripts/codex-web.sh status
./scripts/codex-web.sh logs
./scripts/codex-web.sh restart
./scripts/codex-web.sh stop
```

PowerShell：

```powershell
.\scripts\codex-web.ps1 start
.\scripts\codex-web.ps1 status
.\scripts\codex-web.ps1 logs
.\scripts\codex-web.ps1 restart
.\scripts\codex-web.ps1 stop
```

如果 Windows 阻止执行本地脚本，可以仅对本次命令放行：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\codex-web.ps1 start
```

脚本继承当前终端中的 `CODEX_WEB_*` 和 `CODEX_WORKSPACE*` 环境变量。例如：

```bash
export CODEX_WEB_BASE_PATH=/codex
export CODEX_WEB_PORT=8765
./scripts/codex-web.sh start
```

```powershell
$env:CODEX_WEB_BASE_PATH = "/codex"
$env:CODEX_WEB_PORT = "8765"
.\scripts\codex-web.ps1 start
```

运行日志和 PID 保存在 `.run/`，该目录不会提交到 Git。`logs` 命令中的 `Ctrl+C` 只会退出日志查看，不会停止服务。

后台脚本能跨终端关闭继续运行，但不会在机器重启后自动恢复。需要开机自动启动时，应使用 systemd、Windows Service 或任务计划程序。

## Workspace 与环境变量

所有变量都是可选的：

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `CODEX_WEB_HOST` | `127.0.0.1` | Node 监听地址 |
| `CODEX_WEB_PORT` | `8765` | Node 监听端口 |
| `CODEX_WEB_BASE_PATH` | `/` | 页面及 WebSocket 的统一子路径 |
| `CODEX_WEB_AUTH` | 未启用 | 可选 Basic Auth，格式为 `username:password` |
| `CODEX_WORKSPACE` | 未预选 | 设置后启动时直接选中该 workspace |
| `CODEX_WORKSPACE_BASE` | 当前用户 home | Workspace picker 可以浏览的根目录 |

不设置 `CODEX_WORKSPACE` 时，页面会先加载全部本地 session；创建新对话时再选择 workspace。这是推荐的默认流程。

子路径部署示例：

```bash
export CODEX_WEB_HOST=127.0.0.1
export CODEX_WEB_PORT=8765
export CODEX_WEB_BASE_PATH=/codex
npm start
```

访问：

```text
http://127.0.0.1:8765/codex/
```

注意：只写 `CODEX_WEB_BASE_PATH=/codex` 而不使用 `export`，后续单独执行的 `npm start` 不会继承这个变量。

## 访问认证

默认不启用认证，行为与此前一致。如需保护整个页面、静态资源和 WebSocket，启动前设置：

```bash
export CODEX_WEB_AUTH='username:password'
./scripts/codex-web.sh restart
```

PowerShell：

```powershell
$env:CODEX_WEB_AUTH = "username:password"
.\scripts\codex-web.ps1 restart
```

浏览器打开页面时会显示用户名/密码登录框。用户名或密码错误时返回 HTTP `401`，WebSocket 也会拒绝连接。

不设置或删除该变量即可关闭认证：

```bash
unset CODEX_WEB_AUTH
./scripts/codex-web.sh restart
```

密码中允许包含额外的冒号，程序只把第一个冒号视为用户名与密码的分隔符。用户名和密码都不能为空；格式错误时服务会拒绝启动。

Basic Auth 只是访问门槛，凭据本身仅做 Base64 编码。通过非本机网络访问时必须使用 Nginx HTTPS，不能直接把 HTTP 服务暴露到公网。

## Nginx

Nginx 可以负责 TLS 和反向代理，但不能替代 Node。Node 仍需要：

- 启动并管理 `codex app-server`
- 在 stdio JSON-RPC 与 WebSocket 之间桥接
- 提供受 workspace 范围保护的文件读写接口

配置示例：

```nginx
location /codex/ {
    proxy_pass http://127.0.0.1:8765/codex/;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
}
```

同时设置：

```bash
export CODEX_WEB_BASE_PATH=/codex
```

页面静态资源和 WebSocket 都会使用同一个 base path。

## 内存说明

Node 只保存 WebSocket 连接、未完成的 JSON-RPC 请求和少量 UI 状态；完整 session 历史仍由 Codex 管理。Settings 关闭时不会持续轮询资源数据，打开后每 2 秒读取一次。

生产验证中的参考值：

- Harness Node RSS：约 76–79 MB
- Codex app-server RSS：约 92–129 MB
- Node V8 heap 上限：256 MB

RSS 包含 V8 之外的 Buffer 和原生内存，因此可能高于当前 heap usage。Codex app-server 是独立子进程，也会单独占用内存。

## 验证

先启动一个生产服务：

```bash
npm run build
CODEX_WEB_PORT=8876 CODEX_WEB_BASE_PATH=/codex npm start
```

运行完整 UI 验证：

```bash
/home/pldz/local/venv/bin/python scripts/verify_ui.py
```

运行真实 Codex 流式验证：

```bash
CODEX_WEB_VERIFY_URL=http://127.0.0.1:8876/codex/ \
/home/pldz/local/venv/bin/python scripts/verify_streaming.py
```

截图输出到 `artifacts/screenshots/`。

开发 UI fixture：

```text
http://127.0.0.1:8765/?demo=1
```

`?demo=1` 不会连接真实 Codex，只用于 UI 开发与截图验证。

## 常见问题

### `Cannot find module dist-server/index.js`

尚未生产构建，先执行：

```bash
npm run build
```

### 浏览器提示模块 MIME 类型是 `text/html`

通常是旧构建或 base path/proxy 不一致：

1. 重新执行 `npm run build`
2. 确认 `CODEX_WEB_BASE_PATH` 与 Nginx location 一致
3. 确认代理了整个 `/codex/`，包括静态资源和 WebSocket

### 新对话无法发送

先在 workspace picker 中选择目录。查看已有 session 不要求预先选择 workspace。

### Account usage 显示 Unavailable

当前 Codex 认证方式没有提供账号 usage/rate-limit 接口。对话、文件和 session 功能仍可正常使用。
