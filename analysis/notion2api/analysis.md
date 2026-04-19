# Notion2API 分析报告

> 目标：`https://www.notion.so/api/v3/runInferenceTranscript` 及 Notion Web 注册 / 订阅 / AI 使用量相关链路
> 日期：2026-04-19
> 复杂度定级：L3（真实浏览器登录态 + NDJSON 流式接口 + onboarding 多分支 + 订阅 / usage 多接口联合建模）

---

## 一、最终交付物

| 文件 | 说明 |
|------|------|
| `main.py` | FastAPI 服务入口，提供 OpenAI 兼容接口 |
| `notion_client.py` | Notion AI 请求构造、模型映射、NDJSON 解析与流式转发 |
| `auto_register.py` | Playwright 自动注册、刷新、导出、多账号管理 |
| `capture_env.py` | 基于真实浏览器请求抓取 `.env` 所需凭证 |
| `registration-analysis-report.md` | 注册链路专项分析 |

依赖：`fastapi`、`uvicorn`、`httpx`、`python-dotenv`、`playwright`、`sse-starlette`、`requests`。

---

## 二、项目目标与交付边界

### 项目目标

将 Notion AI 封装为 OpenAI 兼容代理，解决以下三个核心问题：

1. **对话代理**：把 `/v1/chat/completions` 映射到 Notion AI 的 `runInferenceTranscript`
2. **登录态获取**：从真实浏览器请求或自动注册流程中提取可用 env
3. **账号维持**：支持多账号落盘、刷新、导出与后续额度分析

### 当前交付边界

| 能力 | 当前状态 | 说明 |
|------|------|------|
| `/v1/models` | 已完成 | 返回项目内置模型映射 |
| `/v1/chat/completions` 非流式 | 已完成 | 兼容 OpenAI 格式 |
| `/v1/chat/completions` 流式 | 已完成 | 基于真实 NDJSON 流转发 |
| 浏览器抓 env | 已完成 | 依赖 js-reverse MCP 环境 |
| 自动注册 | 已完成 | 采用 Playwright 真实浏览器方案 |
| 多账号管理 | 已完成 | `register/refresh/export/list` |
| usage / billing 独立接口 | 未落地 | 目前只完成抓包与字段建模 |

---

## 三、核心接口分析

### 1. AI 对话主接口

```http
POST https://www.notion.so/api/v3/runInferenceTranscript
accept: application/x-ndjson
content-type: application/json; charset=utf-8
```

### 关键请求头

| 头 | 来源 | 说明 |
|----|------|------|
| `cookie` | `.env` / 浏览器登录态 | 包含 `token_v2`、`p_sync_session`、`notion_user_id`、`csrf`、`device_id`、`notion_browser_id` |
| `x-notion-active-user-header` | `NOTION_USER_ID` | 当前用户标识 |
| `x-notion-space-id` | `NOTION_SPACE_ID` | 当前空间 ID |
| `notion-client-version` | 固定网页版本串 | 需跟随网页版本校准 |
| `origin` | 固定 `https://www.notion.so` | 浏览器来源 |
| `referer` | 固定 `https://www.notion.so/ai` | AI 页面来源 |

### 关键 Cookie / env

| 字段 | 说明 |
|------|------|
| `NOTION_TOKEN_V2` | 核心登录凭证 |
| `NOTION_P_SYNC_SESSION` | 会话同步信息 |
| `NOTION_USER_ID` | 当前用户 ID |
| `NOTION_SPACE_ID` | 目标空间 ID |
| `NOTION_SPACE_VIEW_ID` | 空间视图 ID |
| `NOTION_CSRF` | CSRF cookie |
| `NOTION_DEVICE_ID` | 设备标识 |
| `NOTION_BROWSER_ID` | 浏览器标识 |

### 请求体关键结构

**源码位置**：[notion_client.py:78-152](analysis/notion2api/notion_client.py#L78-L152)

```json
{
  "traceId": "uuid",
  "spaceId": "space_id",
  "transcript": [
    {"type": "config", "value": {...}},
    {"type": "context", "value": {...}},
    {"type": "user", "value": [["user_message"]]}
  ],
  "threadId": "uuid",
  "threadParentPointer": {"table": "space", "id": "space_id", "spaceId": "space_id"},
  "createThread": true,
  "threadType": "workflow 或 markdown-chat",
  "asPatchResponse": true
}
```

### 响应格式

Notion 返回 `application/x-ndjson`，单行事件主要有两类：

| 事件类型 | 来源 | 说明 |
|------|------|------|
| `record-map` | workflow 模式 | 最终文本位于 `thread_message.*.value.value.step` |
| `markdown-chat` | Gemini 相关模式 | 文本位于 `data.markdown` |

**关键结论**：返回流里的文本很多时候是“当前完整文本快照”，不是 token 增量，因此必须做前缀差量计算，不能直接按固定字符切片伪造流式。

---

## 四、模型映射与线程类型

**源码位置**：[notion_client.py:23-45](analysis/notion2api/notion_client.py#L23-L45)、[notion_client.py:48-52](analysis/notion2api/notion_client.py#L48-L52)

### 模型映射表

| OpenAI 风格模型名 | Notion 内部代号 | 线程类型 |
|------|------|------|
| `notion-ai` | `None` | `workflow` |
| `gpt-5.2` | `oatmeal-cookie` | `workflow` |
| `gpt-5.4` | `oatmeal-cake` | `workflow` |
| `sonnet-4.6` | `almond-croissant-high` | `workflow` |
| `sonnet-4.5` | `anthropic-sonnet-alt-no-thinking` | `workflow` |
| `opus-4.7` | `avocado-froyo-high` | `workflow` |
| `haiku-4.5` | `anthropic-haiku-4.5` | `workflow` |
| `gemini-3.1-pro` | `galette-medium-thinking` | `markdown-chat` |
| `gemini-2.5-pro` | `gemini-pro` | `markdown-chat` |
| `gemini-2.5-flash` | `gemini-flash` | `markdown-chat` |

### 关键结论

1. Gemini 系列必须切到 `markdown-chat`
2. 其余模型当前使用 `workflow`
3. `notion-ai` 不显式传模型，由 Notion 自行路由

---

## 五、响应解析与流式实现

### 非流式解析

**源码位置**：[notion_client.py:198-251](analysis/notion2api/notion_client.py#L198-L251)

处理逻辑：

1. 按行拆分 NDJSON
2. 每行交给 `parse_stream_line`
3. 遇到 `record-map` 或 `markdown-chat` 就提取文本、usage、model
4. 最终对文本再执行一次清洗

### 文本清洗

**源码位置**：[notion_client.py:155-177](analysis/notion2api/notion_client.py#L155-L177)

清洗内容包括：

- `<lang ...>` 标签
- `<thinking>` / `<thought>` / `<think>` 思考标签
- Gemini 风格英文思考段
- UTF-8 被按 Latin-1 解码产生的乱码修复

### 真实流式转发

**源码位置**：[notion_client.py:268-325](analysis/notion2api/notion_client.py#L268-L325)、[main.py:177-219](analysis/notion2api/main.py#L177-L219)

核心逻辑：

```python
1. client.stream(...).aiter_lines() 逐行读取
2. 解析当前事件文本
3. 与已发送文本做前缀比较
4. 仅输出新增 delta
5. 最后再补 usage 与 stop 结束事件
```

### 踩坑

- 旧实现是“完整响应 + 每 2 字符切块”，只是伪流式
- NDJSON 中间块不是天然增量，不能直接原样映射到 SSE delta
- 若当前文本不是以上次文本为前缀，需要视为异常分支处理

---

## 六、OpenAI 兼容层设计

**源码位置**：[main.py:101-174](analysis/notion2api/main.py#L101-L174)

### 已实现接口

#### `GET /v1/models`

返回本地 `MODEL_MAP` 的模型列表，`owned_by` 根据前缀推断：

- `gpt*` → `openai`
- `sonnet/opus/haiku*` → `anthropic`
- `gemini*` → `google`
- 其余 → `notion`

#### `POST /v1/chat/completions`

兼容点：

- 支持 OpenAI 风格 `messages`
- 支持 `stream=true`
- 支持 `usage`
- 支持 Bearer API Key 校验

### messages 转换策略

**源码位置**：[main.py:69-83](analysis/notion2api/main.py#L69-L83)

若不是单条 user 消息，则拼接为：

```text
[System]: ...

[User]: ...

[Assistant]: ...
```

### 当前限制

1. 没有真正复刻多轮 thread 续写，只是把 messages 折叠成单条文本
2. 尚未暴露 usage / billing 独立查询接口
3. 错误处理仍偏最小化，主要依赖 Notion 原始返回和 Python 异常

---

## 七、env 获取方案

### 方案一：抓真实浏览器请求

**源码位置**：[capture_env.py:63-113](analysis/notion2api/capture_env.py#L63-L113)

流程：

1. 给 `runInferenceTranscript` 下 XHR 断点
2. 打开 `https://www.notion.so/ai`
3. 自动向输入框写入测试消息并点击发送
4. 抓取暂停时的网络请求
5. 从 request header 中提取 cookie
6. 从 request body 中提取 `spaceId`、`spaceViewId`
7. 写回 `.env`

### 关键结论

- 补全 env 的最高优先级证据是真实网络请求，不是页面脚本可见值
- `capture_env.py` 依赖 MCP 注入环境，不属于独立交付脚本

### 方案二：自动注册后提取

**源码位置**：[auto_register.py:268-449](analysis/notion2api/auto_register.py#L268-L449)

env 来源联合以下几层：

1. `context.cookies()`
2. `localStorage`
3. `getSpacesInitial`
4. `loadUserContent`
5. 运行态 store / 页面 pathname

### 关键结论

只靠 Cookie 不够，`space_id` 与 `space_view_id` 需要结合初始化接口与运行态上下文一起提取。

---

## 八、自动注册链路

### 主入口

**源码位置**：[auto_register.py:477-547](analysis/notion2api/auto_register.py#L477-L547)

### 注册链路

```text
1. 生成邮箱：posase{timestamp}@example.test
2. 打开 signup 页面
3. 输入邮箱并点击继续
4. QQ IMAP 拉取 OTP
5. 输入验证码并提交
6. 推进 onboarding
7. 回到首页提取 env
8. 保存 accounts/<account_id>/
9. 自动再跑一次 refresh，补齐 space_view_id
```

### Playwright 方案为什么成立

**结论来自现有材料与工作日志**：

- 纯 requests / cloudscraper 虽能过基础校验，但 `getLoginOptions` 会被 Notion 服务端拦截
- 真实浏览器链路可稳定通过邮箱登录、onboarding、空间初始化
- 多账号诉求决定不能只维护单一 `.env`

### 自动化关键技术点

#### 输入框注入

**源码位置**：[auto_register.py:128-138](analysis/notion2api/auto_register.py#L128-L138)

必须用原型 setter + `InputEvent/change`，直接赋值不稳定。

#### 按钮点击

**源码位置**：[auto_register.py:141-169](analysis/notion2api/auto_register.py#L141-L169)

按钮匹配同时兼容中英文文案：

- `继续` / `Continue`
- `暂时跳过` / `Skip for now`
- `创建新工作空间` / `Create a new workspace`

#### 营销勾选

**源码位置**：[auto_register.py:172-183](analysis/notion2api/auto_register.py#L172-L183)

营销勾选可能重复出现，必须在多个步骤反复检查并取消。

#### onboarding 推进

**源码位置**：[auto_register.py:218-266](analysis/notion2api/auto_register.py#L218-L266)

当前已覆盖：

- 档案页
- 创建工作空间页
- 用途页
- 邀请成员页
- 方案页
- 桌面应用跳过页

### 无头模式关键点

**源码位置**：[auto_register.py:45-54](analysis/notion2api/auto_register.py#L45-L54)、[auto_register.py:198-215](analysis/notion2api/auto_register.py#L198-L215)

为避免 `getLoginOptions` 被拒，需要：

- `--disable-blink-features=AutomationControlled`
- 覆盖 `user_agent`
- 隐藏 `navigator.webdriver`
- 伪装 `navigator.languages`
- 伪装 `navigator.plugins`

### 踩坑

1. 初期误判为 Cloudflare 问题，实则是 Notion 侧 `Login is not allowed`
2. 首次注册后 `space_view_id` 可能为空，必须追加一次 `refresh`
3. 仅打开首页提取 env 不够，若账号仍停在 onboarding，很多空间字段不会落盘
4. OTP 邮件查询需要在按钮点击后适当等待，否则可能轮询过早

---

## 九、多账号持久化设计

### 目录结构

```text
accounts/
  <account_id>/
    state.json
    env.json
    meta.json
```

### 各文件职责

| 文件 | 说明 |
|------|------|
| `state.json` | Playwright 持久化登录态 |
| `env.json` | 该账号可导出的运行凭证 |
| `meta.json` | 邮箱、user_id、space_id、更新时间等元数据 |

### 子命令

**源码位置**：[auto_register.py:579-612](analysis/notion2api/auto_register.py#L579-L612)

| 命令 | 作用 |
|------|------|
| `register` | 注册新账号 |
| `refresh --account <id>` | 刷新账号 env |
| `export --account <id>` | 导出指定账号到根 `.env` |
| `list` | 列出现有账号 |

### 关键结论

项目根 `.env` 只是“当前激活账号”的导出结果，真正的长期状态在 `accounts/`。

---

## 十、订阅、额度与账号接口分析

### 已确认核心接口

| 接口 | 当前结论 |
|------|------|
| `getSubscriptionData` | 可判断 `subscriptionTier`、`accountBalance`、`blockUsage` |
| `getSubscriptionEntitlements` | 可判断是否 `editsBlocked` |
| `getBillingSubscriptionBannerData` | 当前免费空间为空对象 |
| `getAIUsageEligibility` | 轻量级 AI 可用性与上限接口 |
| `getAIUsageEligibilityV2` | 最适合统一建模 usage / limit / credits |
| `getSpaceBlockUsage` | 返回空间 block 使用量 |
| `getTranscriptionUsage` | 返回独立的转录额度 |
| `getSubscriptionBanner` | 当前空间 bannerIds 为空 |

### 当前样本空间结论

根据现有材料，当前已确认样本空间具备以下值：

| 字段 | 当前值 |
|------|------|
| `subscriptionTier` | `free` |
| `accountBalance` | `0` |
| `AI free spaceLimit` | `150` |
| `AI free userLimit` | `75` |
| `transcription limit` | `7200` 秒 |
| `editsBlocked` | `false` |

### usage 差量验证

已做一次真实 AI 对话前后对比，结果为：

- `getAIUsageEligibility.spaceUsage` 仍为 `0`
- `getAIUsageEligibility.userUsage` 仍为 `0`
- `getAIUsageEligibilityV2.usage.currentServicePeriod` 未变化
- `lifetime`、`totalCreditBalance`、`creditsInOverage` 也未变化

### 关键结论

至少在当前免费空间样本下，**单次真实 AI 对话不会立即让 usage 接口同步递增**。后续如果要做 `/v1/usage`，应按“可能延迟刷新或异步结算”处理，不能假设即时一致。

---

## 十一、问题复盘

### 问题 1：伪流式实现

**现象**：接口虽支持 `stream=true`，但实际是完整响应后再切块输出。  
**原因**：初版直接等 `runInferenceTranscript` 完整返回。  
**解决**：改为 `httpx.AsyncClient.stream(...).aiter_lines()` 逐行读取 NDJSON，并做前缀差量。  

### 问题 2：纯 HTTP 注册被拦截

**现象**：`getLoginOptions` 返回 `Login is not allowed`。  
**原因**：Notion 服务端识别到了非真实浏览器链路。  
**解决**：放弃纯 requests 方案，改用 Playwright 真实浏览器自动化。  

### 问题 3：首次导出缺少 `space_view_id`

**现象**：注册后 env 不完整。  
**原因**：账号仍处在 onboarding 尾部，相关字段尚未落入 localStorage / 初始化接口。  
**解决**：注册后自动追加一次 `refresh`。  

### 问题 4：无头模式风控

**现象**：无头模式注册不稳定或直接失败。  
**原因**：默认 headless 指纹被识别。  
**解决**：补浏览器指纹伪装与启动参数。  

### 问题 5：usage 不实时更新

**现象**：真实对话后额度接口数值不变。  
**原因**：当前推测为服务端异步结算或批量刷新，不是实时扣减。  
**解决**：先记录为产品特性，不在代理层假设同步递增。  

---

## 十二、工具使用经验

### 高效方法

| 场景 | 方法 |
|------|------|
| 找 AI 主接口结构 | 直接读 `notion_client.py` 的请求构造与响应解析 |
| 验证真实 env 来源 | 优先抓网络请求，而不是只读页面脚本变量 |
| 注册链路落地 | 真实浏览器 + IMAP OTP，比纯 HTTP 更稳 |
| 补空间上下文 | 联合 Cookie、localStorage、初始化接口、store |
| 验证 usage | 必须对比对话前后真实接口，不要只看页面文案 |

### 沉淀出的两条规则

1. **当目标是补全 `.env`、Cookie、header、动态请求体时，优先证据永远是真实网络请求。**
2. **最终交付脚本优先级应为：纯脚本 > Playwright 无头 > Playwright 有头；若纯脚本不可行，尽快切换真实浏览器方案，不要长时间卡在伪可行路径上。**

---

## 十三、后续建议

1. 若要新增 `/v1/usage`，优先以 `getAIUsageEligibilityV2` 为主数据源
2. 若要新增 `/v1/account`，优先聚合 `getSpacesInitial`、`getLifecycleUserProfile`、`getTeamsV2`
3. 若要新增 `/v1/billing`，优先聚合 `getSubscriptionData`、`getSubscriptionEntitlements`、`getBillingSubscriptionBannerData`
4. 若 Notion 改动网页版本，优先重新校验 `notion-client-version` 与 `runInferenceTranscript` 请求体结构
5. 若注册链路再变，优先复查 onboarding 分支和 headless 指纹，而不是回退到纯 HTTP 猜测
