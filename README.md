# js-reverse

一个面向 JavaScript 逆向分析、浏览器调试与独立脚本交付的工作仓库。

仓库同时包含：
- `js-reverse-mcp`：基于 Patchright 的 MCP 调试工具，适合做真实请求取证、发起栈定位、上下文恢复与脚本级逆向分析
- `projects/`：具体逆向项目与独立运行脚本
- `.claude/skills/`：面向 Claude Code 的 js-reverse skill 与知识库
- `utils/`：可复用辅助工具，例如邮箱、MCP 服务等

## 仓库目标

这个仓库不是单一 npm 包或单一 Python 项目，而是一套完整工作台，目标包括：

- 用真实浏览器和调试工具定位 Web 逆向链路
- 对登录态、动态请求体、初始化接口、空间上下文等多源证据做联合取证
- 把定位结果还原成可独立运行的脚本
- 沉淀通用 skill、知识库和项目级方法论
- 在项目目录中保存可复用的实现、说明文档与过程记录

## 目录结构

```text
js-reverse/
├── .claude/                  # Claude Code 配置、skills、知识库
├── projects/                 # 具体逆向项目
│   ├── maoyan/               # 猫眼票房接口逆向
│   └── notion2api/           # Notion AI OpenAI 兼容代理与账号脚本
├── utils/                    # 通用工具
│   ├── js-reverse-mcp/       # MCP 服务源码
│   └── qq_mail/              # QQ 邮箱 IMAP/SMTP 工具
├── CLAUDE.md                 # 本仓库协作规则
└── README.md                 # 根说明文档
```

## 初始化与环境准备

### 1. 克隆仓库后先看什么

建议按这个顺序理解仓库：

1. 看根目录 [README.md](README.md)
2. 看仓库规则 [CLAUDE.md](CLAUDE.md)
3. 根据目标进入具体项目目录，例如：
   - [projects/maoyan/README.md](projects/maoyan/README.md)
   - [projects/notion2api/README.md](projects/notion2api/README.md)
4. 如果要使用浏览器调试能力，再看：
   - [utils/js-reverse-mcp/README.md](utils/js-reverse-mcp/README.md)
   - [.claude/skills/js-reverse.md](.claude/skills/js-reverse.md)

### 2. js-reverse-mcp 的两种使用方式

#### 方式一：直接用 npx

适合直接把 MCP 服务接入 Claude Code、Cursor、Copilot 等客户端，不需要改本地源码。

配置示例：

```json
{
  "mcpServers": {
    "js-reverse": {
      "command": "npx",
      "args": ["js-reverse-mcp"]
    }
  }
}
```

#### 方式二：本地源码方式

适合你要修改 `utils/js-reverse-mcp` 源码、调试工具本身或使用本地构建版本。

初始化命令：

```bash
cd utils/js-reverse-mcp
npm ci
npm run build
```

构建后，本地入口通常是：

```text
utils/js-reverse-mcp/build/src/index.js
```

本地 MCP 配置示例：

```json
{
  "mcpServers": {
    "js-reverse": {
      "command": "node",
      "args": ["/你的绝对路径/js-reverse/utils/js-reverse-mcp/build/src/index.js"]
    }
  }
}
```

如果你修改了 `utils/js-reverse-mcp` 的源码，通常需要重新执行：

```bash
cd utils/js-reverse-mcp
npm run build
```

### 3. Python 项目初始化

不同项目按各自目录说明安装依赖。

#### notion2api

```bash
cd projects/notion2api
pip install -r requirements.txt
playwright install chromium
```

这个项目同时依赖：
- Python 环境
- Playwright Chromium
- `utils/qq_mail` 中的 QQ 邮箱脚本能力

### 4. 哪些目录属于什么用途

| 目录 | 用途 | 是否通常需要初始化 |
|---|---|---|
| `.claude/` | skill、知识库、协作规则 | 否 |
| `projects/maoyan/` | 具体项目与脚本交付 | 视项目而定 |
| `projects/notion2api/` | Python 服务与账号脚本 | 是 |
| `utils/js-reverse-mcp/` | MCP 服务源码 | 如果要本地开发则需要 |
| `utils/qq_mail/` | 邮件辅助工具 | 单独使用时只需 Python 依赖 |

## 核心组成

### 1. MCP 调试工具

位置：[`utils/js-reverse-mcp/`](utils/js-reverse-mcp/)

这是仓库中的浏览器调试基础设施，提供：
- 页面导航、截图、frame 选择
- 脚本搜索、源码读取、源码保存
- 断点、单步、函数追踪
- 请求溯源、XHR 断点、WebSocket 分析
- 运行时注入与求值

更多说明见：
- [`utils/js-reverse-mcp/README.md`](utils/js-reverse-mcp/README.md)
- [`utils/js-reverse-mcp/README_zh.md`](utils/js-reverse-mcp/README_zh.md)

### 2. 项目目录

位置：[`projects/`](projects/)

每个子目录对应一个具体任务或交付物，当前包括：

| 项目 | 说明 | 文档 |
|---|---|---|
| `maoyan` | 猫眼票房接口逆向，最终交付为纯 requests 脚本 | [projects/maoyan/README.md](projects/maoyan/README.md) |
| `notion2api` | Notion AI 代理服务、账号注册、凭证刷新、多账号管理 | [projects/notion2api/README.md](projects/notion2api/README.md) |

### 3. 辅助工具

位置：[`utils/`](utils/)

当前可见的通用工具：

| 工具 | 说明 | 文档 |
|---|---|---|
| `js-reverse-mcp` | 浏览器调试与反检测 MCP 服务 | [utils/js-reverse-mcp/README.md](utils/js-reverse-mcp/README.md) |
| `qq_mail` | QQ 邮箱 IMAP/SMTP 工具，可用于验证码拉取与发信 | [utils/qq_mail/README.md](utils/qq_mail/README.md) |

### 4. Skills 与知识库

位置：[`.claude/skills/`](.claude/skills/)

这里沉淀了：
- `js-reverse` skill
- 阶段化知识库
- 项目专项模式
- 工具参考与交付规则

重点文件：
- [`.claude/skills/js-reverse.md`](.claude/skills/js-reverse.md)
- [`.claude/skills/knowledge/README.md`](.claude/skills/knowledge/README.md)
- [`.claude/skills/knowledge/05-project/notion-env-capture-pattern.md`](.claude/skills/knowledge/05-project/notion-env-capture-pattern.md)
- [`.claude/skills/knowledge/05-project/independent-delivery-priority.md`](.claude/skills/knowledge/05-project/independent-delivery-priority.md)

## 工作方式

### 逆向与交付优先级

本仓库当前明确采用以下交付优先级：

1. **纯脚本方案优先**
   - requests/httpx
   - 算法还原
   - 纯 HTTP 重放
   - 本地环境模拟
2. **Playwright 无头方案其次**
3. **Playwright 有头方案最后**

补充约束：
- 最终交付脚本必须优先保证独立运行
- Claude、MCP、浏览器调试会话只能用于分析和取证
- 不能把 Claude/MCP 作为最终脚本的运行依赖

这套规则来源于 `projects/notion2api` 的实际验证，并已经沉淀进 skill 知识库。

### 文档职责

当前仓库采用双文档结构：

- `README.md`：维护稳定说明、使用方式、目录导航、当前能力
- `WORKLOG.md`：维护关键过程记录、证据、阻塞点、阶段结论、下一步

适用原则：
- 使用方式、安装、命令、目录结构、接口、最终行为变化：更新 `README.md`
- 排障、抓包、试验、阻塞、关键证据、阶段结论：更新 `WORKLOG.md`

示例：
- [projects/notion2api/README.md](projects/notion2api/README.md)
- [projects/notion2api/WORKLOG.md](projects/notion2api/WORKLOG.md)

## 当前项目状态

### maoyan

- 已完成票房接口分析
- 最终交付为纯 requests 脚本
- 无需浏览器自动化即可运行

详见：[projects/maoyan/README.md](projects/maoyan/README.md)

### notion2api

- 已完成 Notion AI 代理服务
- 已支持多账号目录管理
- 已支持 `register / refresh / export / list`
- 已验证 `--headless` 无头注册与刷新链路
- 已实现注册后自动补一次 refresh，以补齐首次导出 env

详见：
- [projects/notion2api/README.md](projects/notion2api/README.md)
- [projects/notion2api/WORKLOG.md](projects/notion2api/WORKLOG.md)

## 环境要求

根据不同子项目，常见依赖包括：

- Node.js v20.19+
- Chrome 稳定版
- Python 3.x
- Playwright Chromium

具体以各子项目 README 为准。

## 入口文档

- 仓库协作规则：[CLAUDE.md](CLAUDE.md)
- MCP 工具说明：[utils/js-reverse-mcp/README.md](utils/js-reverse-mcp/README.md)
- QQ 邮箱工具：[utils/qq_mail/README.md](utils/qq_mail/README.md)
- 猫眼项目：[projects/maoyan/README.md](projects/maoyan/README.md)
- Notion 项目：[projects/notion2api/README.md](projects/notion2api/README.md)
- JS Reverse Skill：[.claude/skills/js-reverse.md](.claude/skills/js-reverse.md)
- 知识库索引：[.claude/skills/knowledge/README.md](.claude/skills/knowledge/README.md)

## 许可证

Apache-2.0
