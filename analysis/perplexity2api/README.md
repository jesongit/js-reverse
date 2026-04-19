# perplexity2api

基于 Perplexity 网页真实链路的 Python 验证脚本。

## 当前结论

### 1. 对话转 OpenAI API 的方案

可行方案不是直接命中官方 OpenAI 接口，而是封装 Perplexity 网页聊天链路：

- 提交问题：`POST /rest/sse/perplexity_ask`
- 拉取线程详情：`GET /rest/thread/{thread_slug}`
- 断线续流：`GET /rest/sse/perplexity_ask/reconnect/{resume_entry_uuid}`
- 侧边栏实时更新：`GET /rest/sse/recent_thread_updates`

OpenAI 兼容层建议映射：

- `messages[-1].content` → `query_str`
- `model` → `model_preference`
- `stream=true` → 转发网页 SSE 事件
- `conversation_id` 或自定义 `thread_id` → `thread_slug`
- `response.id` → `entry_uuid`

### 2. 请求构造

前端源码显示提交参数由 `lv(...)` 统一构造，核心字段包括：

- `query_str`
- `frontend_uuid`
- `frontend_context_uuid`
- `model_preference`
- `sources`
- `mode`
- `query_source`
- `language`
- `timezone`
- `use_schematized_api=true`
- `send_back_text_in_streaming_api=false`
- `supported_block_use_cases[]`

请求查询参数至少包括：

- `version=2.18`
- `source=default`
- `rum_session_id=<uuid>`

### 3. 模型映射

网页侧真实字段名为 `model_preference`，脚本内置常见映射：

- `auto` → `turbo`
- `turbo` → `turbo`
- `sonar` → `sonar`
- `gpt-4.1` → `gpt4.1`
- `gpt-4o` → `gpt4o`
- `claude-3.7-sonnet` → `claude2`
- `claude-sonnet-4` → `sonar-reasoning-pro`
- `r1-1776` → `r1_1776`
- `o3-mini` → `o3-mini`
- `grok-2` → `grok-2`
- `gemini-2.5-pro` → `gemini2.5pro`

更完整模型清单见 [models_catalog.md](models_catalog.md)。

当前默认模型：

- `search`: `turbo`
- `research`: `pplx_alpha`
- `study`: `pplx_study`
- `agentic_research`: `pplx_agentic_research`
- `document_review`: `pplx_document_review`
- `browser_agent`: `claude46sonnet`
- `asi`: `pplx_asi`

已从前端源码枚举出的主要模型包括：

- 搜索/对话：`turbo`、`pplx_pro`、`experimental`、`pplx_reasoning`
- OpenAI 系：`gpt4o`、`gpt41`、`gpt51`、`gpt52`、`gpt54`、`gpt54mini`、`gpt53codex`、`o4mini`、`o3`、`o3mini`、`o3pro`
- Anthropic 系：`claude2`、`claude37sonnetthinking`、`claude46sonnet`、`claude46sonnetthinking`、`claude46opus`、`claude46opusthinking`、`claude45haiku`、`claude45sonnet`、`claude45opus`、`claudecode`
- Google 系：`gemini25pro`、`gemini31pro_high`、`gemini30flash`、`gemini30flash_high`、`gemini30pro`
- xAI 系：`grok`、`grok2`、`grok4`、`grok41reasoning`
- Kimi / 其他：`kimik25thinking`、`kimik2thinking`、`r1`、`llama_x_large`、`mistral`
- 多媒体：`nanobananapro`、`nanobanana2`、`gptimage15`、`sora2`、`sora2pro`、`veo31`、`veo31fast`

基于当前账号的扩大范围真实探测结果，以下 93 个模型已验证可用：

- Perplexity / 搜索类：`turbo`、`pplx_pro_upgraded`、`pplx_pro`、`experimental`、`pplx_reasoning`、`pplx_sonar_internal_testing`、`pplx_sonar_internal_testing_v2`、`pplx_study`、`pplx_document_review`、`pplx_agentic_research`、`pplx_alpha`、`pplx_beta`、`pplx_business_assistant`、`sonar`
- OpenAI 系：`gpt4o`、`gpt4.1`、`gpt41`、`gpt51`、`gpt52`、`gpt54`、`gpt54mini`、`gpt53codex`、`gpt51_thinking`、`gpt52_thinking`、`gpt54_thinking`、`gpt5`、`gpt5_thinking`、`gpt5_pro`、`o4mini`、`o3`、`o3-mini`、`o3mini`、`o3pro`、`o3pro_research`、`o3pro_labs`、`o3_research`、`o3_labs`、`codex`
- Anthropic 系：`claude2`、`claude37sonnetthinking`、`claude40opus`、`claude41opus`、`claude40opusthinking`、`claude41opusthinking`、`claude46opus`、`claude46opusthinking`、`claude46sonnet`、`claude46sonnetthinking`、`claude45haiku`、`claude45sonnet`、`claude45sonnetthinking`、`claude45opus`、`claude45opusthinking`、`claudecode`
- Google 系：`gemini25pro`、`gemini31pro_high`、`gemini30flash`、`gemini30flash_high`、`gemini`、`gemini2flash`、`gemini30pro`
- xAI 系：`grok`、`grok2`、`grok4`、`grok4nonthinking`、`grok41reasoning`、`grok41nonreasoning`
- Moonshot / Kimi：`kimik25thinking`、`kimik2thinking`、`pplx_asi_kimi`
- 其他：`r1`、`r1_1776`、`llama_x_large`、`mistral`、`pplx_gamma`、`testing_model_c`、`claude_ombre_eap`、`claude_lace_eap`、`pplx_asi_qwen`、`pplx_asi_sonnet`、`pplx_asi_sonnet_thinking`、`pplx_asi_gpt54`、`pplx_asi_opus`、`pplx_asi_opus_thinking`、`pplx_asi_beta`、`pplx_asi`
- 多媒体：`nanobananapro`、`nanobanana2`、`gptimage15`、`sora2`、`sora2pro`、`veo31`、`veo31fast`

探测方法：使用当前用户提供的有效 Cookie，通过真实 `POST /rest/sse/perplexity_ask` 对扩大后的 93 个候选模型逐个发送 `请只回复 OK`，结果全部成功返回。原始结果见 `available_models_result.json`。

### 4. 最小必要 headers 与 cookies

当前已确认最小请求头集合可先按下面尝试：

- `accept: text/event-stream`
- `content-type: application/json`
- `origin: https://www.perplexity.ai`
- `referer: https://www.perplexity.ai/`
- `user-agent: 浏览器 UA`
- `cookie: ...`

当前页面已观察到的关键 cookie：

- `pplx.visitor-id`
- `pplx.session-id`

已验证结论：

- 仅使用 `pplx.visitor-id + pplx.session-id + pplx.trackingAllowed`，可以成功请求 `POST /rest/sse/perplexity_ask`
- 同一最小 cookie 集访问 `GET /rest/thread/{thread_slug}` 会返回 `403 Forbidden`
- 因此“发起新问题”的最小 cookie 集已确认，但“读取完整线程详情”仍需要补充更多登录态材料

页面本地还存在 `pplx-next-auth-session` localStorage 项，但脚本当前仅使用 Cookie 直接重放。

### 5. 会话状态维护

建议保存以下字段：

- `thread_slug`
- `entry_uuid`
- `frontend_uuid`
- `frontend_context_uuid`
- 断线续流时使用 `resume_entry_uuid`
- 取历史消息时调用 `GET /rest/thread/{thread_slug}`

## 安装

```bash
cd analysis/perplexity2api
pip install -r requirements.txt
```

## 注流程分析

### 当前已确认的真实链路

当用户在 [onboarding/org/create](https://www.perplexity.ai/onboarding/org/create) 输入邮箱并点击“继续使用电子邮件”后，真实浏览器网络顺序为：

- `POST /rest/enterprise/organization/login/details?version=2.18&source=default`
- `GET /api/auth/providers?version=2.18&source=default`
- `GET /api/auth/csrf?version=2.18&source=default`
- `POST /api/auth/signin/email?version=2.18&source=default`
- 跳转到 `/auth/verify-request?email=...&redirectUrl=%2Fonboarding%2Forg%2Fcreate&login-source=organization-onboarding`

### 当前脚本进展

已新增独立脚本 [perplexity_register.py](perplexity_register.py)，用于复现注册前半段并接入 QQ 邮箱收码：

```bash
cd analysis/perplexity2api
python perplexity_register.py your_email@example.com --skip-mail
```

等待邮件并尝试提取 6 位验证码：

```bash
cd analysis/perplexity2api
python perplexity_register.py your_email@example.com
```

当前脚本已实现：

- 复现 `login/details -> providers -> csrf -> signin/email` 链路
- 复用 [utils/qq_mail/qq_mail_idle.py](../../utils/qq_mail/qq_mail_idle.py) 中的 `fetch_latest_mail_to(...)` 收码
- 已补入验证码提交接口 `POST /api/auth/otp-redirect-link`
- 输出发码阶段与验证码提交阶段的真实状态码、响应内容与当前 Cookie
- 混合模式已完成真实闭环验证：浏览器发码后，脚本可提取真实邮件中的 6 位验证码并成功提交，返回 `redirect_url`

已修正问题：

- `utils/qq_mail` 现已兼容 `unknown-8bit` 邮件头，避免扫描收件箱时提前异常
- `perplexity_register.py` 在 `--hybrid` 模式下会为 `sent_after` 预留 30 秒回溯窗口，避免验证码邮件先到达却被时间过滤误判为旧邮件

当前限制：

- 纯脚本已成功通过 Cloudflare 首层并获取 `csrfToken`
- 但 `POST /api/auth/signin/email` 仍返回 `400 {"error":"Invalid request body"}`
- 说明发码请求体仍缺少尚未还原的真实字段、编码细节或附加上下文
- 因此当前已验证可交付方案仍是“最小浏览器参与”的混合模式，而不是全纯脚本注册闭环

### 最小浏览器参与方案

在现有可见能力下，更稳的可交付方式是仅让浏览器完成被隔离的发码动作，后续由独立 Python 脚本继续收码并提交验证码：

```bash
cd analysis/perplexity2api
python perplexity_register.py your_email@example.com --hybrid
```

如果当前环境没有可用的 QQ 邮箱 IMAP 配置，可先改为手动输入验证码：

```bash
cd analysis/perplexity2api
python perplexity_register.py your_email@example.com --hybrid --manual-code
```

执行流程：

1. 脚本先验证 `login/details`
2. 终端提示后，你在浏览器中手动点击“继续使用电子邮件”完成发码
3. 默认模式下，脚本调用 QQ 邮箱收码逻辑提取 6 位验证码；若使用 `--manual-code`，则在当前前台终端中手动输入验证码
4. 脚本调用 `POST /api/auth/otp-redirect-link` 提交验证码并输出 `redirect_url`

补充说明：

- `--manual-code` 依赖交互式 stdin，必须在前台终端直接运行，不能放到无交互的后台任务里，否则会因 `input()` 读取不到输入而报 `EOFError`
- 若已正确配置 `QQ_MAIL_IMAP_USER` 与 `QQ_MAIL_IMAP_PASSWORD`，优先使用自动收码模式 `--hybrid`
- 当前最稳的发码方式不是继续猜纯 HTTP body，而是在浏览器真实上下文中复用前端现成 `signIn('email', ...)` 实现；该路径已完成真实取证，并已验证可以成功发出 Perplexity 验证邮件

这是一种“最小浏览器参与”混合方案：

- 浏览器只负责当前无法纯脚本稳定复现的 `signin/email`
- Python 脚本继续负责收码、验证码提取、验证码提交与结果输出
- 当前已完成两轮真实自动闭环验证，能够稳定拿到邮件中的 6 位验证码并返回 `redirect_url`
- 相比整段浏览器自动化，范围更小，也更贴近当前已还原的真实链路

## OpenAI 兼容服务

### 启动服务

```bash
cd analysis/perplexity2api
export PPLX_COOKIE='你的完整浏览器 Cookie'
python openai_compatible_server.py
```

默认监听：`http://127.0.0.1:8012`

可选鉴权：

```bash
export PPLX_OPENAI_API_KEY='test-key'
```

设置后，所有接口都需要：

```text
Authorization: Bearer test-key
```

### 调用 `/v1/chat/completions`

非流式：

```bash
curl http://127.0.0.1:8012/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "turbo",
    "messages": [
      {"role": "user", "content": "你好"}
    ]
  }'
```

流式：

```bash
curl http://127.0.0.1:8012/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "turbo",
    "stream": true,
    "messages": [
      {"role": "user", "content": "你好"}
    ]
  }'
```

当前兼容范围：

- `GET /v1/models`
- `GET /v1/perplexity/models`
- `GET /v1/perplexity/limits`
- `POST /v1/chat/completions`
- `POST /v1/responses`
- 支持 `stream=false/true`
- `messages` 或 `input` 会被拼接成单次 Perplexity 查询
- 支持可选 `Authorization: Bearer <api_key>` 校验

### 调用额度与模型相关接口

```bash
curl http://127.0.0.1:8012/v1/perplexity/models \
  -H 'Authorization: Bearer test-key'

curl http://127.0.0.1:8012/v1/perplexity/limits \
  -H 'Authorization: Bearer test-key'
```

说明：

- 这两个接口是为当前逆向项目补的辅助接口，不属于 OpenAI 官方规范
- `GET /v1/perplexity/models` 透传 `rest/models/config` 的结果或错误
- `GET /v1/perplexity/limits` 聚合 `rest/rate-limit/status`、`rest/rate-limit/free-queries`、`rest/user/settings` 的结果或错误
- 目前在独立 requests 环境下，这几类接口大概率仍会返回 403，因此服务会把错误保留在 JSON 中返回

### 调用 `/v1/responses`

```bash
curl http://127.0.0.1:8012/v1/responses \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "turbo",
    "input": "你好"
  }'
```

## 用法

### 1. 直接发起问题

```bash
python perplexity2api.py "你好" --cookie "你的完整浏览器 Cookie"
```

或：

```bash
export PPLX_COOKIE='你的完整浏览器 Cookie'
python perplexity2api.py "你好"
```

### 2. 保存真实 SSE 事件

```bash
python perplexity2api.py "你好" --dump-events events.json
```

### 3. 保存线程详情

```bash
python perplexity2api.py "你好" --dump-thread thread.json
```

### 4. 只读取已有线程

```bash
python perplexity2api.py "占位" --thread-slug ni-hao-G9tJ5DgsQjSEIXQ6NmEUvw --dump-thread thread.json
```

## 说明

- 该脚本是独立运行脚本，不依赖浏览器自动化。
- 当前实现已按真实网页端点与前端参数结构还原。
- 已完成一次真实请求验证：独立脚本可成功获取 `POST /rest/sse/perplexity_ask` 响应，并拿到真实 `thread_slug` 与 `entry_uuid`。
- 线程详情接口在最小 cookie 集下仍会返回 403，因此如需稳定拉历史消息，需要补充更多会话材料后继续验证。
- 若 Cookie 过期、账号风控或服务端校验额外头部，需用最新浏览器会话重新验证。
- 额度类与模型配置类接口当前已补到服务端和辅助脚本，但在纯 requests 直连下仍可能返回 403，这是当前已确认的限制。
