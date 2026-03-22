# file-event-hub

A decoupled file change event bus for AI coding assistants.

AI 编码助手改了什么文件？改了哪些行？实时推送到浏览器，带语法高亮地看 diff 和完整文件。

## Problem

用 Claude Code / Cursor / Copilot 等 AI 编码助手工作时，你想知道它改了什么文件，但：

- 终端里翻 diff 不直观
- 想在浏览器里看，但没有现成工具
- SSH 到远程服务器的用户尤其痛苦 —— 没法直接 `code` 打开文件

各家助手都有 hooks（Claude Code 的 PostToolUse、Cline 的 hooks、Windsurf 的 post_write_code...），但它们都是各自为战，没有统一的事件总线和可视化方案。

## Architecture

```
┌─────────────┐     ┌───────────┐     ┌─────────────┐
│  Publisher   │────▶│   Server  │────▶│  Subscriber  │
│  (CC Hook)   │     │  (Event   │     │  (WebUI)     │
│              │     │   Hub)    │     │              │
└─────────────┘     └───────────┘     └─────────────┘
   PostToolUse         HTTP API          Browser
   Edit/Write        + WebSocket        Diff View
                                       File View
```

**Publisher** — Claude Code 的 PostToolUse hook，捕获 Edit/Write 事件，POST 到 Server

**Server** — 轻量 HTTP 服务，接收事件、存储、通过 WebSocket 实时推送给前端

**Subscriber** — WebUI，浏览器中实时展示变更列表、diff 和完整文件内容

## MVP Scope

MVP 阶段专注 Claude Code，把核心链路跑通。

### 1. Hook（Publisher）

Claude Code `PostToolUse` hook 脚本：

- 监听 `Edit` / `Write` 工具调用
- 从 stdin 读取 hook 的 JSON input（含 `tool_name`、`tool_input.file_path` 等）
- 构造事件：`{ file_path, tool, timestamp, old_content?, new_content? }`
- POST 到 Server 的 HTTP API

配置方式：写入用户的 `~/.claude/settings.json` 的 `hooks.PostToolUse`。

### 2. Server（Event Hub）

轻量 HTTP + WebSocket 服务：

- `POST /api/events` — 接收 hook 推送的文件变更事件
- `GET /api/events` — 查询历史事件列表
- `GET /api/files/:path` — 读取文件当前内容（用于完整文件查看）
- `WebSocket /ws` — 实时推送新事件到前端
- 事件存储：MVP 阶段用内存 + JSON 文件即可（无需数据库）

### 3. WebUI（Subscriber）

浏览器端单页应用：

#### 变更列表（左侧/主页）
- 实时更新的文件变更时间线
- 每条显示：文件路径、操作类型（Edit/Write）、时间戳
- 新事件通过 WebSocket 自动出现，无需刷新

#### Diff 视图
- 点击变更条目 → 显示该次修改的 diff
- Side-by-side 或 unified diff 模式
- **语法高亮**（按文件类型）

#### 文件查看
- 点击文件路径 → 查看文件完整内容
- **代码语法高亮渲染**（支持常见语言）
- 显示行号

### Tech Stack（MVP）

| 组件 | 技术选型 | 理由 |
|------|---------|------|
| Hook | Shell script (bash) | 零依赖，CC hook 原生支持 |
| Server | Python (FastAPI) | 轻量、WebSocket 支持好、启动快 |
| WebUI | 单 HTML 文件 (vanilla JS) | 零构建，可直接由 Server 托管 |
| Diff 渲染 | diff2html (CDN) | 成熟的 diff 可视化库 |
| 代码高亮 | highlight.js (CDN) | 支持 190+ 语言，CDN 直接用 |

### Non-Goals (MVP)

- ❌ 跨助手适配（Cursor / Copilot 等留给后续）
- ❌ 认证/权限（本地或内网使用）
- ❌ 持久化存储（重启丢数据 OK）
- ❌ 多用户/多项目隔离

## Usage (Target)

```bash
# 1. 启动 server
file-event-hub serve --port 9120

# 2. 安装 CC hook（自动写入 settings.json）
file-event-hub install-hook

# 3. 浏览器打开
open http://localhost:9120

# 4. 正常用 Claude Code 写代码，WebUI 实时展示变更
```

对于 SSH 用户：server 跑在远程机器上，浏览器访问 `http://remote:9120` 即可。

## Future Vision

MVP 之后的可能方向：

- 多助手适配器（Cline、Windsurf、Cursor hooks）
- 统一事件 schema（跨助手标准化）
- 可插拔 subscriber（VSCode 扩展、GitHub 跳转、Slack 通知...）
- 事件持久化 + 回放
- 文件变更统计 / AI 贡献度分析
