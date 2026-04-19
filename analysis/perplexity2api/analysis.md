# Perplexity2API 分析报告

> 目标：`https://www.perplexity.ai` 对话主链路、OpenAI 兼容封装、模型清单、额度接口与邮箱注册链路
> 日期：2026-04-19
> 复杂度定级：L3（真实浏览器取证 + SSE 流式接口 + 模型映射与多接口分层鉴权 + 注册链路混合方案）

---

## 一、最终交付物

| 文件 | 说明 |
|------|------|
| `perplexity2api.py` | 基于网页真实链路发起对话、解析 SSE、维护最小会话信息 |
| `openai_compatible_server.py` | 提供最小 OpenAI 兼容接口与可选 Bearer 鉴权 |
| `perplexity_metadata.py` | 封装模型配置、额度、用户设置等元数据接口 |
| `check_available_models.py` | 基于真实聊天链路批量探测当前账号可用模型 |
| `perplexity_register.py` | Perplexity 邮箱注册研究脚本，支持混合模式收码与验证码提交 |
| `models_catalog.md` | 从前端源码与真实探测整理出的模型目录 |
| `available_models_result.json` | 当前账号扩大范围模型探测原始结果 |
| `events.json` | 对话 SSE 事件样本 |
| `rate_limit_status.json` / `free_queries.json` / `user_settings.json` | 元数据接口抓取结果样本 |

依赖：`requests`，注册链路额外复用仓库内 `utils/qq_mail`。

---

## 二、项目目标与交付边界

### 项目目标

把 Perplexity 网页对话能力封装为可独立运行的 Python 工具，并解决四类问题：

1. **对话代理**：将网页 `perplexity_ask` 链路映射为脚本接口与 OpenAI 兼容接口
2. **模型适配**：梳理网页侧 `model_preference`、默认模式映射和当前账号真实可用模型范围
3. **元数据建模**：确认模型配置、额度、用户设置等外围接口的存在、用途与当前限制
4. **注册链路**：还原邮箱注册前半段、验证码提取与提交链路，并评估纯脚本可行边界

### 当前交付边界

| 能力 | 当前状态 | 说明 |
|------|------|------|
| 单次对话脚本调用 | 已完成 | `perplexity2api.py` 可直接发问并解析 SSE |
| `/v1/chat/completions` 非流式 | 已完成 | 兼容最小 OpenAI 返回结构 |
| `/v1/chat/completions` 流式 | 已完成 | 转发为 OpenAI 风格 SSE chunk |
| `/v1/responses` | 已完成 | 支持字符串或消息数组输入 |
| `/v1/models` | 已完成 | 当前返回最小静态模型列表 |
| 模型批量可用性探测 | 已完成 | 已真实探测 93 个候选模型 |
| 线程详情纯脚本拉取 | 部分完成 | 发问可用，但最小 Cookie 下 `GET /rest/thread/{slug}` 仍会 403 |
| 元数据接口纯脚本稳定拉取 | 部分完成 | 已确认接口存在，部分环境下仍受更强鉴权限制 |
| 纯脚本注册闭环 | 未完成 | 发码阶段仍被 `400 Invalid request body` 阻塞 |
| 最小浏览器参与注册方案 | 已完成 | 浏览器负责发码，脚本负责收码与验证码提交 |

---

## 三、核心对话接口分析

### 1. 对话主接口

```http
POST https://www.perplexity.ai/rest/sse/perplexity_ask?version=2.18&source=default&rum_session_id=<uuid>
accept: text/event-stream
content-type: application/json
```

### 已确认相关接口

```text
POST /rest/sse/perplexity_ask
GET  /rest/thread/{thread_slug}
GET  /rest/sse/perplexity_ask/reconnect/{resume_entry_uuid}
GET  /rest/sse/recent_thread_updates
```

### 关键请求体字段

前端源码显示提交参数由统一构造函数生成，核心字段包括：

| 字段 | 说明 |
|------|------|
| `query_str` | 用户问题文本 |
| `frontend_uuid` | 前端请求唯一标识 |
| `frontend_context_uuid` | 前端上下文标识 |
| `model_preference` | 网页侧真实模型字段 |
| `sources` | 常见值为 `web` |
| `mode` | 当前脚本使用 `concise` |
| `query_source` | 来源标记，默认 `default` |
| `language` | 当前样本为 `zh-CN` |
| `timezone` | 当前样本为 `Asia/Shanghai` |
| `use_schematized_api` | 固定为 `true` |
| `send_back_text_in_streaming_api` | 固定为 `false` |
| `supported_block_use_cases[]` | 前端声明可接受的块类型 |

### 关键请求头与 Cookie

当前已确认最小请求头集合：

- `accept: text/event-stream`
- `content-type: application/json`
- `origin: https://www.perplexity.ai`
- `referer: https://www.perplexity.ai/`
- `user-agent: 浏览器 UA`
- `cookie: ...`

当前已验证的最小 Cookie 集：

- `pplx.visitor-id`
- `pplx.session-id`
- `pplx.trackingAllowed`

### 关键结论

1. Perplexity 网页对话主链路基于 **SSE fetch**，不是默认 WebSocket
2. 仅凭最小 Cookie 集即可成功发起新问题
3. 同一最小 Cookie 集下读取线程详情仍会 `403 Forbidden`
4. 因此“发问链路可独立运行”不等于“线程详情、额度接口、用户设置接口也可独立复用”

---

## 四、SSE 响应解析与会话维护

**源码位置**：[perplexity2api.py:144-224](analysis/perplexity2api/perplexity2api.py#L144-L224)

### SSE 解析逻辑

脚本按标准 SSE 规则解析：

1. 逐行读取 `iter_lines()`
2. 识别 `event:` 和 `data:`
3. 按空行切分事件
4. 对 `data` 尝试做 JSON 解析
5. 从事件中提取 `text`、`backend_uuid`、`thread_url_slug` 与 `blocks.markdown.content`

### 会话维护关键字段

| 字段 | 用途 |
|------|------|
| `thread_slug` | 标识会话线程 |
| `entry_uuid` | 当前回答条目标识 |
| `frontend_uuid` | 本次请求前端 UUID |
| `frontend_context_uuid` | 上下文 UUID |
| `resume_entry_uuid` | 断线续流所需字段 |

### 关键结论

1. 最小闭环只需要先保存 `thread_slug + entry_uuid + frontend_uuid + frontend_context_uuid`
2. 若后续只追求“单轮问答转 OpenAI”，线程详情接口不是第一优先级
3. 若后续要做多轮历史还原、Recent Threads 或完整会话浏览，就必须继续补更多登录态材料

---

## 五、OpenAI 兼容层设计

**源码位置**：[openai_compatible_server.py](analysis/perplexity2api/openai_compatible_server.py)

### 已实现接口

| 接口 | 状态 | 说明 |
|------|------|------|
| `GET /v1/models` | 已完成 | 返回最小静态模型列表 |
| `POST /v1/chat/completions` | 已完成 | 支持非流式与流式 |
| `POST /v1/responses` | 已完成 | 兼容 Responses 风格结构 |
| `GET /v1/perplexity/models` | 已完成 | 透传模型配置元数据调用结果 |
| `GET /v1/perplexity/limits` | 已完成 | 汇总额度与用户设置接口结果 |

### messages 转换策略

**源码位置**：[openai_compatible_server.py:32-67](analysis/perplexity2api/openai_compatible_server.py#L32-L67)

- `chat/completions`：把 `messages` 按 `role: content` 折叠为单次 prompt
- `responses`：兼容字符串输入和数组输入，数组内兼容 `input_text` 与 `text`

### 流式实现

**源码位置**：[openai_compatible_server.py:227-290](analysis/perplexity2api/openai_compatible_server.py#L227-L290)

当前实现为最小兼容：

1. 先调用底层 `PerplexityClient.ask()` 拿到完整回答
2. 再包装成 OpenAI 风格 SSE
3. `chat/completions` 输出 role chunk、content chunk、stop chunk
4. `responses` 输出 `response.created`、`response.output_text.delta`、`response.completed`

### 当前限制

1. 当前流式仍是“拿到完整回答后再输出兼容 chunk”，不是底层事件级实时透传
2. `messages` 目前折叠为单条 prompt，没有真正复刻多轮线程续写
3. `/v1/models` 还不是根据当前账号动态探测生成

---

## 六、模型映射与可用模型探测

### 模型映射

**源码位置**：[perplexity2api.py:55-67](analysis/perplexity2api/perplexity2api.py#L55-L67)

当前脚本内置的别名映射包括：

| OpenAI 风格名称 | Perplexity `model_preference` |
|------|------|
| `auto` | `turbo` |
| `gpt-4.1` | `gpt4.1` |
| `gpt-4o` | `gpt4o` |
| `claude-3.7-sonnet` | `claude2` |
| `claude-sonnet-4` | `sonar-reasoning-pro` |
| `r1-1776` | `r1_1776` |
| `o3-mini` | `o3-mini` |
| `grok-2` | `grok-2` |
| `gemini-2.5-pro` | `gemini2.5pro` |

### 默认模型与模式映射

整理自前端源码的当前默认模式：

- `search`: `turbo`
- `research`: `pplx_alpha`
- `study`: `pplx_study`
- `agentic_research`: `pplx_agentic_research`
- `document_review`: `pplx_document_review`
- `browser_agent`: `claude46sonnet`
- `asi`: `pplx_asi`

### 真实可用性探测

**源码位置**：[check_available_models.py](analysis/perplexity2api/check_available_models.py)

探测方式：

1. 基于已验证可用的 `POST /rest/sse/perplexity_ask`
2. 对候选模型逐个发送 `请只回复 OK`
3. 以真实返回成功或失败判断是否可用

### 当前结论

- 已对 93 个候选模型完成真实探测
- 当前样本中 **全部成功，无失败项**
- 覆盖范围包含搜索、推理、Anthropic、OpenAI、Google、xAI、Kimi、ASI、多媒体等类别

更完整模型枚举见 [models_catalog.md](analysis/perplexity2api/models_catalog.md)。

---

## 七、元数据接口与分层鉴权

### 已确认接口

```text
GET /rest/models/config?config_schema=v1&version=2.18&source=default
GET /rest/rate-limit/status?version=2.18&source=default
GET /rest/rate-limit/free-queries?version=2.18&source=default
GET /rest/user/settings?skip_connector_picker_credentials=true&version=2.18&source=default
```

### 当前状态

- 这些接口已由网页真实前端调用
- 目录中已保留 `models_config.json`、`rate_limit_status.json`、`free_queries.json`、`user_settings.json` 等结果样本
- 但在独立 `requests` 环境下，部分接口仍可能返回 `403`

### 关键结论

1. 首个接口可用，不代表整个站点外围接口都能直接复用
2. 对话接口、线程详情接口、额度接口、用户设置接口存在 **分层鉴权**
3. 后续若要做完整 API 化，优先顺序应是：
   - 先收敛最小可用对话链路
   - 再单独补线程详情鉴权
   - 最后再处理额度与配置接口

---

## 八、邮箱注册链路分析

### 已确认的真实链路

当用户在 `https://www.perplexity.ai/onboarding/org/create` 输入邮箱并点击“继续使用电子邮件”后，真实浏览器顺序为：

```text
POST /rest/enterprise/organization/login/details
GET  /api/auth/providers
GET  /api/auth/csrf
POST /api/auth/signin/email
跳转 /auth/verify-request?email=...&redirectUrl=%2Fonboarding%2Forg%2Fcreate&login-source=organization-onboarding
```

### 验证码提交接口

已确认验证码提交不是标准 NextAuth callback，而是：

```http
POST /api/auth/otp-redirect-link
```

关键请求体字段包括：

- `email`
- `otp`
- `redirectUrl`
- `emailLoginMethod: web-otp`
- `loginSource: organization-onboarding`

### 纯脚本方案评估

### 已验证结论

1. 纯 `requests` 获取 `csrf` 会先被 Cloudflare 拦截
2. `cloudscraper` 可以通过首层挑战并拿到真实 `csrfToken`
3. 但 `POST /api/auth/signin/email` 仍持续返回 `400 {"error":"Invalid request body"}`
4. 说明阻塞点已从 Cloudflare 转为 **真实发码请求上下文尚未完整还原**

### 取证过程中的关键判断

- 已尝试源码级字段还原
- 已尝试 query 与 `redirectUrl` 对齐
- 已尝试页面内 fetch hook / XHR hook / 运行时模块 / React Fiber 侧取证
- 真实网络始终稳定出现发码请求，但当前可见范围内无法稳定抓到可直接复用的原始发送上下文

### 当前可交付方案

因此最终采用 **最小浏览器参与混合方案**：

1. 浏览器负责完成当前无法纯脚本稳定复现的 `signin/email` 发码动作
2. Python 脚本负责调用 QQ 邮箱收码逻辑提取 6 位验证码
3. Python 脚本再调用 `POST /api/auth/otp-redirect-link` 提交验证码
4. 最终输出 `redirect_url`

### 关键结论

1. 当前最稳方案不是继续盲猜纯 HTTP body，而是承认运行时上下文差异
2. 浏览器参与范围已被收缩到最小，只保留发码这一段
3. 收码、验证码提取、验证码提交与结果处理已可由独立脚本接管

---

## 九、问题复盘

### 问题 1：误以为 AI 对话站点默认走 WebSocket

**现象**：初期容易优先检查 WebSocket
**原因**：很多 AI 对话站点使用 WS 或 WS + SSE 混合方案
**解决**：真实网络取证后确认主链路是 `POST /rest/sse/perplexity_ask`
**结论**：AI 对话站点必须先看真实 network，不要默认传输层

### 问题 2：把最小 Cookie 成功发问误判为全站登录态完整

**现象**：`perplexity_ask` 可用，但 `thread` 和 `rate-limit` 不可用
**原因**：不同接口分层鉴权
**解决**：把“发问可用”和“线程详情可用”“额度接口可用”拆开验证
**结论**：首个接口打通不代表整站已打通

### 问题 3：过早坚持纯脚本注册闭环

**现象**：`signin/email` 长时间停留在 `400 Invalid request body`
**原因**：真实阻塞点不是表面字段缺失，而是运行时上下文尚未还原
**解决**：在同层证据不足后，及时转为最小浏览器参与方案
**结论**：要优先交付最小稳定闭环，而不是在低收益方向盲挖

### 题 4：把兼容层范围开得过大

**现象**：容易一开始就想完整复刻 OpenAI API
**原因**：需求天然有“通用代理”诱惑
**解决**：先只实现 `/v1/chat/completions`、`/v1/responses`、`/v1/models`
**结论**：先收敛最小可用接口集，再扩展外围能力

---

## 十、工具使用经验与方法论

### 高效取证方法

| 场景 | 工具 | 方法 |
|------|------|------|
| 找对话主链路 | network + initiator | 先抓真实请求，再回源码确认字段语义 |
| 找模型映射 | 前端源码搜索 | 搜 `model_preference`、默认模式、模型常量 |
| 验证模型可用性 | 真实请求脚本 | 不依赖前端展示，直接逐个发最小问题 |
| 判断接口分层鉴权 | requests 对照测试 | 同一 Cookie 分别测 ask / thread / rate-limit |
| 注册链路断点判断 | 浏览器网络 + 页面上下文 | 先确认真实顺序，再决定纯脚本是否继续 |

### 方法论结论

1. **真实网络优先于页面猜测**
2. **AI 站点优先判定传输层与接口分层，不要先入为主**
3. **先做最小可用闭环，再扩展兼容面**
4. **遇到持续 403 / 400 时，要区分是字段缺失、鉴权分层，还是运行时上下文差异**
5. **如果页面 hook 长时间抓不到关键请求，应尽快考虑执行上下文差异，而不是继续同层盲试**

---

## 十一、阶段结论

当前 `analysis/perplexity2api` 已得到以下稳定结论：

1. Perplexity 网页对话主链路可被独立 Python 脚本复用，核心端点为 `POST /rest/sse/perplexity_ask`
2. 已交付最小 OpenAI 兼容服务，覆盖 `/v1/chat/completions`、`/v1/responses`、`/v1/models`
3. 当前账号样本中，扩大后的 93 个候选模型全部真实可用
4. 线程详情、额度、用户设置等外围接口存在分层鉴权，不能因为发问成功就默认全部可用
5. 注册链路当前最稳方案是“浏览器发码 + Python 收码与提交验证码”的混合模式，而不是纯脚本全闭环

后续若继续扩展，最值得投入的方向是：

- 线程详情接口所需附加鉴权材料
- 元数据接口稳定拉取条件
- 底层 SSE 到 OpenAI 流式 delta 的更细粒度映射
- 注册链路发码阶段真实上下文的进一步还原
