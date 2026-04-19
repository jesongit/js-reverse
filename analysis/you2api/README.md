# you2api

把 you.com 的对话能力适配为 OpenAI Chat Completions 兼容接口的独立 Python 脚本。

## 当前结论

基于 `https://you.com/` 的真实运行态取证与本地代理实测，当前已确认两层链路：

- 首页输入框不会直接命中最终对话接口，而是先导航到 `/search?q=...&fromSearchBar=true`
- 搜索页首轮问答可通过 `GET /_next/data/<buildId>/<locale>/search.json?q=...&cid=...&tbm=youchat` 驱动
- 页面初始化数据 `__NEXT_DATA__` 中可直接取到 `buildId`、`locale`、`nonce`、登录用户、模型列表、额度与部分配置
- 更深层仍存在 `threadId`、`/api/threads`、`/api/snapshots`、`convertYouChatUpdateStep`、`Youchat SSE Error` 等证据，说明完整多轮会话仍是线程接口加增量事件机制

因此当前最稳的独立交付策略是：

1. 默认适配搜索页首轮问答链路
2. 本地暴露 `/v1/models` 与 `/v1/chat/completions`
3. 将 `search.json` 响应转换为 OpenAI 兼容格式
4. 将多轮 thread/streaming 能力保留为增强模式，而不是默认稳定路径
5. 保留自定义 `YOU_CHAT_ENDPOINT`，便于后续切换到更深层真实线程接口
6. 当前已验证本地 OpenAI 兼容接口可用，且能真实命中 you.com；但匿名 `search.json` 默认返回并不保证直接给出最终自然语言答案
7. 当前环境后续真实复测已被 you.com 风控拦截，错误为 `Account or domain blocked for abuse. Contact Support for resolution`

## 当前脚本能力

脚本文件：[you2api.py](you2api.py)

已支持：

- `GET /v1/models`
- `POST /v1/chat/completions`
- 默认走 `/_next/data/<buildId>/<locale>/search.json`
- 可切换到 `/api/streamingSearch` 或 `/api/streamingSavedChat` 候选链路
- 可通过 `YOU_CHAT_ENDPOINT` 切换到自定义上游接口
- 非流式响应
- 基于完整回答切片的 OpenAI SSE 输出
- 通过环境变量注入 headers、cookies、默认参数
- 响应中附带 `upstream_hint.search_url` 与 `upstream_hint.streaming_url`
- `raw_upstream` 保留 you.com 原始响应，便于继续校正字段提取

## 安装

```bash
cd analysis/you2api
pip install -r requirements.txt
```

## 默认运行方式

如果你要直接复用当前已取证到的首轮问答链路，建议至少补齐这些环境变量：

```bash
export YOU_MODEL_NAME='gpt_5_1_instant'
export YOU_SEARCH_BUILD_ID='1138057'
export YOU_SEARCH_LOCALE='en-US'
export YOU_SEARCH_TBM='youchat'
export YOU_CHAT_MODE='custom'
export YOU_NONCE='从 __NEXT_DATA__ 抓到的 nonce'
export YOU_COOKIES='{"descope":"你的登录态","其他必要 cookie":"值"}'
export YOU_HEADERS='{"accept":"application/json","x-requested-with":"XMLHttpRequest"}'
python you2api.py
```

如果你已经补齐真实 Descope 会话等必要认证条件，并要优先逼近已证据化的多轮真实链路，可切到 streaming 模式：

```bash
export YOU_UPSTREAM_MODE='streaming'
export YOU_CHAT_MODE='custom'
export YOU_SELECTED_AI_MODEL='gpt_5_1_instant'
export YOU_SOURCES='web'
export YOU_CHAT_ID='已有会话 chatId，没有则留空'
export YOU_CONVERSATION_TURN_ID='已有 turn id，没有则留空'
export YOU_QUERY_TRACE_ID='可复用页面里的 queryTraceId'
export YOU_TRACE_ID='可复用页面里的 traceId'
export YOU_HEADERS='{}'
export YOU_COOKIES='{"descope":"你的登录态"}'
python you2api.py
```

当前已静态确认前端通过自定义 `SSE` 类走 `XMLHttpRequest` 发起 `POST`，并流式解析返回的 `event/data` chunk；但额外请求头最小集合仍待运行态继续确认，因此这里不再默认写死 `x-requested-with`。

默认监听：

```text
http://127.0.0.1:8000
```

## 自定义上游接口模式

如果你后续抓到了更深层真实聊天接口，可以直接切换：

```bash
export YOU_CHAT_ENDPOINT='/api/your-real-chat-endpoint'
export YOU_HEADERS='{"content-type":"application/json","accept":"text/event-stream"}'
export YOU_COOKIES='{"your_cookie_name":"your_cookie_value"}'
export YOU_DEFAULT_PAYLOAD='{"chat_mode":"default"}'
python you2api.py
```

设置 `YOU_CHAT_ENDPOINT` 后，脚本将优先走该接口，不再使用 `search.json` 默认链路。

## 调用示例

### 模型列表

```bash
curl http://127.0.0.1:8000/v1/models
```

### 非流式对话

```bash
curl http://127.0.0.1:8000/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "gpt_5_1_instant",
    "stream": false,
    "messages": [
      {"role": "user", "content": "你好"}
    ]
  }'
```

### 流式对话

```bash
curl http://127.0.0.1:8000/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "gpt_5_1_instant",
    "stream": true,
    "messages": [
      {"role": "user", "content": "你好"}
    ]
  }'
```

### 指定 you.com 参数

搜索链路示例：

```bash
curl http://127.0.0.1:8000/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "gpt_5_1_instant",
    "stream": false,
    "you_cid": "c1_xxx",
    "you_nonce": "页面里的 nonce",
    "you_chat_mode": "custom",
    "messages": [
      {"role": "user", "content": "请回复ok"}
    ]
  }'
```

多轮流式候选链路示例：

```bash
curl http://127.0.0.1:8000/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "gpt_5_1_instant",
    "stream": false,
    "you_upstream_mode": "streaming",
    "you_chat_mode": "custom",
    "you_selected_ai_model": "gpt_5_1_instant",
    "you_chat_id": "chat_xxx",
    "you_conversation_turn_id": "turn_xxx",
    "you_query_trace_id": "trace_query_xxx",
    "you_trace_id": "trace_xxx",
    "messages": [
      {"role": "user", "content": "第一问"},
      {"role": "assistant", "content": "第一答"},
      {"role": "user", "content": "继续详细解释"}
    ]
  }'
```

## 当前限制

- `YOU_UPSTREAM_MODE=streaming` 已能按已取证参数结构构造 `/api/streamingSearch` 或 `/api/streamingSavedChat`，且已静态确认前端实际使用的是基于 `XMLHttpRequest` 的自定义 SSE 封装；但当前真实页面还存在“有 user 无 DS/DSR”的半初始化登录态证据，且运行态可见 `auth.you.com/v1/auth/try-refresh` 与 `/api/threads` 同时 pending，因此多轮模式除参数结构外还依赖完整认证会话，请求头最小集与 cookies 最小集仍未完全收敛
- 当前已做真实最小验证：脚本可实际请求 `search.json` 并返回 OpenAI 兼容 JSON，但匿名首轮查询返回体并不总是直接携带自然语言回答，可能只返回 `pageTraceId`、配置与页面初始化数据；因此默认首轮链路已验证为“真实可达”，但未验证为“匿名稳定出自然语言答案”
- 当前进一步真实复测已被上游风控阻塞，页面直接返回 `Account or domain blocked for abuse. Contact Support for resolution`；因此在当前网络出口或账号上下文下，无法继续完成有效真实问答验证
- 当前最小必要 headers 可先收敛为浏览器默认头加 `Accept: application/json`；若走 streaming 候选链路，再加 `Content-Type: application/json` 与 `Accept: text/event-stream`。额外自定义头当前没有足够运行态证据证明是必需项
- 当前最小必要 cookies 对首轮匿名 `search.json` 不是硬依赖；但若需要稳定多轮会话、thread 恢复或保存会话，必须补齐真实 Descope 会话相关 cookies 与其刷新闭环，至少不能处于“有 user 无 DS/DSR”的半初始化状态
- 当前 OpenAI `stream=true` 仍是把完整回答切片后转成 SSE，不是 you.com 原生增量流透传
- 真实多轮 thread 链路当前更像依赖一条完整的 Descope 认证恢复链：`DS/DSR -> token/refresh -> Authorization/x-descope-sdk-session-id`；若浏览器只呈现“有 user 无 DS/DSR”的半初始化状态，前端 UI 与 `isSignedInToYDC` 仍可能判定为已登录，并提前放出 follow-up 等组件壳层；`useYouProState`、`useChatHistory`、`useProjectsGet`、`useEntitlementsGet` 等查询也会因此被 enabled，但 `/api/threads`、`/api/streamingSearch` 等内部接口不应假定可直接复现
- 当前 streaming/thread 模式应视为“需要完整真实会话条件”的增强能力，而不是默认稳定交付路径
- 若 `buildId`、`locale`、`nonce`、`chatId`、`conversationTurnId` 或 cookies 过期，需要重新从页面更新
- 若后续要支持稳定真实多轮流式透传，仍需继续补抓原生 SSE 事件数据体样例，或先补齐有效 Descope 会话后重新取证

## 已确认的关键证据

- 搜索页 URL 形态：`/search?q=...&fromSearchBar=true`
- 首轮问答数据接口：`/_next/data/1138057/en-US/search.json?q=...&cid=...&tbm=youchat`
- 初始化数据来源：`window.__NEXT_DATA__`
- 页面初始化字段包含：`buildId=1138057`、`locale=en-US`、`nonce`、`aiModels`、`youProState`
- 深层会话相关证据：`threadId`、`/api/threads`、`/api/snapshots`、`convertYouChatUpdateStep`、`Youchat SSE Error`
- 已证据化的多轮提交入口：`POST /api/streamingSearch`、`POST /api/streamingSavedChat`
- 已证据化的查询参数：`q`、`page`、`count`、`safeSearch`、`chatId`、`conversationTurnId`、`cachedChatId`、`isNewChat`、`pastChatLength`、`selectedChatMode`、`selectedAiModel`、`sources`、`queryTraceId`、`traceId`、`project_id`
- 已证据化的固定开关：`enable_editable_workflow=true`、`use_nested_youchat_updates=true`、`enable_agent_clarification_questions=true`
- 已证据化的 SSE 事件名：`thirdPartySearchResults`、`youChatToken`、`youChatUpdate`、`youChatResponse`、`youChatAppRankings`、`relatedSearches`、`youChatRenderedOutput`、`youChatCachedChat`、`youChatIntent`、`abTestSlices`、`youChatClarificationQuestions`、`youChatWorkflowSteps`、`routedMode`、`youChatTitle`、`done`、`error`
