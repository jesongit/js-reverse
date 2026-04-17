# notion2api

一个基于 Python 的 Notion AI → OpenAI 兼容代理服务。

## 文件说明

- `main.py`：FastAPI 服务入口，暴露 OpenAI 兼容接口
- `notion_client.py`：Notion 请求构造、响应解析、内容清理
- `cli.py`：服务启停管理脚本
- `capture_env.py`：从浏览器抓取 Notion AI 请求并更新 `.env`
- `auto_register.py`：自动注册新账号 + 提取 env 参数（需要 js-reverse MCP）
- `.env`：运行所需凭证
- `.env.example`：环境变量模板

## 安装

```bash
pip install -r requirements.txt
```

## 启动

```bash
python cli.py start
python cli.py status
python cli.py stop
```

也可以直接运行：

```bash
python main.py
```

## 接口

### 获取模型列表

```bash
curl http://localhost:3000/v1/models \
  -H "Authorization: Bearer sk-notion2api"
```

### 对话

```bash
curl http://localhost:3000/v1/chat/completions \
  -H "Authorization: Bearer sk-notion2api" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "notion-ai",
    "messages": [{"role": "user", "content": "hello"}]
  }'
```

## 重新获取 env

当 Notion 登录态失效后，可以重新抓取最新凭证。

### 当前实现说明

`capture_env.py` 已固化了抓取流程，但它依赖当 Claude Code / MCP 注入环境下的 `js-reverse` 工具调用能力。

也就是说，这个脚本的目标是把“抓取步骤”固定下来，便于后续复用；如果你在普通 Python 环境直接运行，它不会工作，仍需要在带 MCP 上下文的环境里执行。

### 抓取流程

1. 确保浏览器已登录 Notion
2. 确保 js-reverse MCP 已连接浏览器
3. 打开 `https://www.notion.so/ai`
4. 运行：

```bash
python capture_env.py
```

它会自动：

- 对 `runInferenceTranscript` 下断点
- 触发一次 AI 请求
- 从真实请求头里提取：
  - `NOTION_TOKEN_V2`
  - `NOTION_P_SYNC_SESSION`
  - `NOTION_SPACE_ID`
  - `NOTION_USER_ID`
  - `NOTION_SPACE_VIEW_ID`
  - `NOTION_CSRF`
  - `NOTION_DEVICE_ID`
  - `NOTION_BROWSER_ID`
- 自动写回 `.env`

## 实现过程总结

### 1. 为什么改成 Python

原始版本是 Node.js + Express。

这次改成 Python，主要是因为：

- FastAPI 更适合快速搭 OpenAI 兼容接口
- `httpx` 的异步请求更直观
- 启停、调试、后续脚本化更方便

最终保留了原有核心能力：

- `GET /v1/models`
- `POST /v1/chat/completions`
- 流式 / 非流式输出
- API Key 鉴权
- Notion 请求转发
- NDJSON 响应解析

### 2. 分析 Notion 请求时拿到了什么

真实请求最终确认了以下关键点：

- 接口是 `POST /api/v3/runInferenceTranscript`
- `accept` 必须是 `application/x-ndjson`
- 关键鉴权依赖 Cookie：
  - `token_v2`
  - `p_sync_session`
  - `csrf`
  - `notion_user_id`
  - `device_id`
  - `notion_browser_id`
- 关键请求头：
  - `x-notion-active-user-header`
  - `x-notion-space-id`
  - `notion-client-version`
  - `notion-audit-log-platform`

### 3. 遇到的问题

#### 问题一：`.env` 里的旧凭证失效

最开始服务能跑，但调用 Notion 返回 `401 Unauthorized`。

原因不是 Python 代码逻辑错，而是 `.env` 里的旧 `token_v2` / `p_sync_session` 已失效。

解决方式：

- 用 MCP 在浏览器里触发真实 AI 请求
- 从 `runInferenceTranscript` 请求头里重新提取 Cookie
- 回写 `.env`

#### 问题二：`document.cookie` 拿不到关键凭证

一开始试图直接从页面 JS 拿 Cookie，但拿不到 `token_v2` 和 `p_sync_session`。

原因：

- 这两个值不能稳定通过普通前端脚本读取
- 必须从真实网络请求头抓取

所以最终方案不是“读页面 Cookie”，而是“抓真实请求”。

#### 问题三：Windows 下 Bash / Python 输出乱码

表现是终端中文输出成乱码。

原因：

- 当前环境是 Windows
- bash 与控制台编码不一致
- 输出展示链路按 UTF-8 / 本地编码混用

解决方式：

- 在 `main.py` 和 `cli.py` 中显式把 `stdout/stderr` 重设为 UTF-8

#### 问题四：AI 返回文本出现 `I��m`

服务打通后，第一次真实对话返回了乱码文本，例如：

- `I��m Notion AI`

原因：

- 上游返回内容里有 UTF-8 / Latin-1 误解码现象

解决方式：

- 在 `notion_client.py` 中增加乱码修复逻辑
- 在 `clean_content()` 收尾阶段修复 mojibake

#### 问题五：管理脚本健康检查失败

最初 `cli.py` 启动后会误判失败。

原因包括：

- 健康检查没带 API Key
- Windows 下 PID 存活判断不可靠
- 3000 端口残留占用会干扰测试

解决方式：

- 健康检查时自动带上 `.env` 中的 API Key
- Windows 改为 `tasklist` 检查进程
- 清理残留端口后重新验证

## 当前状态

目前已验证：

- 服务可启动 / 停止
- `GET /v1/models` 正常
- `POST /v1/chat/completions` 正常
- 可用真实 Notion 凭证完成对话
- 返回文本编码正常

## 后续注意事项

- Notion 登录态过期后，需要重新抓一次 `.env`
- `notion-client-version` 未来可能需要跟随网页版本调整
- 如果 Notion 改了 `runInferenceTranscript` 的请求结构，需要重新抓包校准

## 对 js-reverse 的反向优化沉淀

这次任务进一步确认了一个可复用结论：

- 当目标是补全 `.env`、Cookie、header、动态请求体时，**优先级最高的证据永远是真实网络请求**，而不是页面脚本可见值
- 对于 Notion 这类站点，`document.cookie` 不能作为完整凭证来源
- 一旦页面读不到关键 Cookie，应该立刻切换到“断请求 → 抓真实请求头 → 回填配置”的路径

这部分已经沉淀到 js-reverse 知识库：

- `.claude/skills/knowledge/05-project/notion-env-capture-pattern.md`

## 自动注册账号

### 说明

`auto_register.py` 可全自动完成注册 + env 提取，需在 Claude Code MCP 上下文中运行（依赖 js-reverse MCP 和 QQ IMAP）。

### 注册流程

1. 生成邮箱 `posase{时间戳}@pid.im`
2. 打开注册页，输入邮箱，触发 OTP 发送
3. 通过 QQ IMAP 拉取最新 Notion 验证码邮件
4. 输入验证码完成登录
5. 档案页：填写名字（邮箱前缀），取消"我同意接收推广信息"勾选
6. 若出现团队邀请页，明确选"创建新工作空间"
7. 用途页：选择"用于私人生活"，取消营销勾选
8. 跳过桌面应用引导
9. 进入主页后提取 Cookie + localStorage + 初始化接口数据，写入 `.env`

### 关键技术点

- **输入框**：必须用原型 setter + InputEvent/change 事件，直接赋值无效
- **按钮**：精确匹配 `innerText`，避免点击外层容器节点
- **营销勾选**：每个步骤都重新检查，可能多次出现
- **验证码**：通过 IMAP 搜索 `FROM notion` 邮件，取最新 6 位数字
- **env 提取**：从 Cookie（token_v2、p_sync_session、csrf 等）+ localStorage（spaceViewId）组合提取

### 已验证的注册账号

| 邮箱 | user_id | space_id | 注册时间 |
|------|---------|----------|--------|
| posase1776420539@pid.im | 345d872b-594c-8183-a2da-00028ac58b7a | 06a1a9d7-3098-81af-b185-0003f22ba7d8 | 2026-04-17 |

## 工作记录

- 时间：2026-04-17
  - 阶段：注册流程接入准备
  - 发现或问题：用户要求在 `projects/notion2api` 中新增 Notion 邮箱注册自动化；现有目录仅覆盖 Notion AI 代理，还没有注册流程脚本；邮箱验证码可复用 `utils/qq_mail/qq_mail_idle.py`，但当前脚本只提供监听类，没有面向 Notion 验证码的现成封装。
  - 结论：先用 js-reverse 抓取 `https://www.notion.so/signup?from=marketing&pathname=%2F` 的真实注册请求链路，再按链路补最小化自动注册实现；同时补一个从 QQ IMAP 拉取并校验目标邮箱的验证码读取函数。
  - 下一步：打开注册页，抓关键请求、表单字段、验证码接口与必要请求头。

- 时间：2026-04-17
  - 阶段：注册流程自动化实现完成
  - 发现或问题：
    1. IMAP IDLE 监听在收件箱历史邮件多时会把旧验证码（528576）误报为新码，需通过发件人过滤锁定 Notion 邮件
    2. Trusted Types 限制导致部分页面 evaluate_script 报错，需在新 Tab 打开注册页绕过
    3. 验证码邮件正文极简，仅 6 位数字，无标题等辅助字段
    4. onboarding 出现已有工作空间邀请（test1727x），必须精确点"创建新工作空间"
    5. token_v2 / p_sync_session 必须从真实网络请求头提取，document.cookie 无法读取
  - 结论：完成 auto_register.py 脚本，固化完整注册流程（邮箱生成→OTP→档案→工作空间→用途→跳过引导→env 提取→写入 .env）；当前 .env 已更新为新注册账号的有效凭证
  - 下一步：验证新凭证是否可调用 Notion AI API