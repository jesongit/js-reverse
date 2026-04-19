# you2api worklog

- 时间：2026-04-19
  - 阶段：任务初始化
  - 发现或问题：目标是在 `analysis/you2api` 下基于 `https://you.com/` 分析“对话转 OpenAI API”的可行方案，并要求最终交付可独立运行的 Python 脚本。根据仓库规则，需避免读取 `prompt.md`，且关键过程必须即时记录到当前工作目录的 `WORKLOG.md`。
  - 结论：先通过 js-reverse 工具获取真实页面脚本、网络请求、关键请求头与参数结构，再决定是纯 HTTP 重放还是需要浏览器辅助初始化。
  - 下一步：打开目标站点，采集脚本与请求证据，定位对话接口与鉴权来源。

- 时间：2026-04-19
  - 阶段：前端链路初探
  - 发现或问题：页面为 Next.js/Turbopack，大量脚本已加载；源码检索可见与对话相关的 `threadId`、`/api/threads`、`/api/snapshots` 以及 `Youchat SSE Error` 字样，说明回答链路很可能是线程式对话加 SSE 流式返回，而不是标准 OpenAI 接口。
  - 结论：优先触发一次真实提问，请求级取证关键 endpoint、headers、请求体和 SSE 响应格式，再决定适配层实现。
  - 下一步：提交一条测试消息并在 `/api/` XHR 断点处提取调用信息。

- 时间：2026-04-19
  - 阶段：方案收敛
  - 发现或问题：当前页面未在本次会话中稳定抓到最终提问请求，但源码证据已经明确三点：一是存在线程体系与 `threadId`，二是存在 `Youchat SSE Error` 与 `eventSource` 相关实现，三是存在 `convertYouChatUpdateStep` 对站内流式增量做结构转换。这说明 you.com 前端本身并不是 OpenAI 兼容接口，而是内部线程接口加 SSE 增量事件，再由前端整理成回答步骤。
  - 结论：可交付方案应采用“上游保留 you.com 会话语义，下游输出 OpenAI 兼容响应”的适配器模式。独立 Python 脚本不直接伪造浏览器复杂链路，而是把上游 endpoint、headers、cookies 配置化，允许后续一旦补齐真实请求证据即可直接工作。
  - 下一步：实现 OpenAI 兼容代理脚本，支持 `/v1/models`、`/v1/chat/completions`、非流式与流式输出，并在 README 说明需要补齐的上游真实参数。

- 时间：2026-04-19
  - 阶段：本地自测
  - 发现或问题：`you2api.py` 已通过 `python -m py_compile` 语法校验；在本地用 monkey patch 替代上游请求后，`/v1/models` 与非流式 `/v1/chat/completions` 已能正常返回 OpenAI 兼容 JSON。首次自测因 shell 相对路径不在仓库根目录而失败，已改用绝对路径重跑。
  - 结论：当前交付物可独立启动，代理层接口行为正常；剩余限制仅是未补齐 you.com 真实提问 endpoint 与鉴权参数。
  - 下一步：整理 README 中的使用说明与限制说明，完成交付。

- 时间：2026-04-19
  - 阶段：继续取证真实提问链路
  - 发现或问题：用户要求继续推进，因此需要从“可配置代理”进一步收敛到“带真实上游默认链路”的可运行版本，关键缺口仍是最终提问请求本身未被稳定捕获。
  - 结论：优先通过页面运行态 hook `fetch`、`XMLHttpRequest`、`sendBeacon`、`EventSource`，直接在浏览器侧记录真实提问时发出的 URL、headers、body 与流式端点，而不是继续只依赖静态脚本检索。
  - 下一步：注入网络 hook，重新提交消息并抓取浏览器侧实时证据。

- 时间：2026-04-19
  - 阶段：修正提问触发路径判断
  - 发现或问题：首页 QueryBar 对应源码 `useHandleSubmitQueryNavigateToChatPage`，会先把输入编码进 `/search?q=...&fromSearchBar=true` 再进入真正对话页；当前直接在首页 textarea 上点击按钮并不会稳定触发最终对话请求，因此抓不到上游接口并非单纯 hook 失效。
  - 结论：应改为直接导航到带 `q` 参数的搜索页，或在搜索页继续触发后续增量请求，再抓取真实聊天接口与 SSE 事件。
  - 下一步：打开 `/search?q=请回复ok&fromSearchBar=true`，在结果页重新取证网络请求。

- 时间：2026-04-19
  - 阶段：搜索页真实证据补齐
  - 发现或问题：搜索页已出现关键运行态证据。`__NEXT_DATA__` 明确暴露登录用户、`nonce`、`aiModels`、`youProState`、`uploadFileConfig` 等初始化环境；网络层出现 `GET /_next/data/1138057/en-US/search.json?q=...&cid=...&tbm=youchat`，说明当前未登录全量对话接口前，搜索页本身可由 Next.js data 接口驱动首轮问答。另见 `GET /_next/data/1138057/en-US.json?chatMode=smart_routing`、`GET /_next/data/1138057/en-US/agents/*.json`、`auth.you.com/v1/auth/try-refresh` 与 LaunchDarkly EventSource。
  - 结论：现阶段最稳的“可独立运行”方案应先默认适配 `/_next/data/<buildId>/<locale>/search.json` 这条首轮问答链路，把 `q`、`tbm=youchat`、可选 `cid` 以及页面初始化提取到的 `buildId`、`locale`、`nonce`、cookie 作为主要输入；后续若继续抓到更深层线程接口，再扩展多轮会话支持。
  - 下一步：据此修正 `you2api.py` 默认上游逻辑与 README，优先支持基于 `search.json` 的 OpenAI 兼容首轮对话转换。

- 时间：2026-04-19
  - 阶段：脚本收敛与验证
  - 发现或问题：已将 `you2api.py` 默认链路改为 `GET /_next/data/<buildId>/<locale>/search.json`，同时保留 `YOU_CHAT_ENDPOINT` 覆盖模式；脚本会从 OpenAI `messages` 提取最后一条用户消息映射到 `q`，并支持 `YOU_SEARCH_BUILD_ID`、`YOU_SEARCH_LOCALE`、`YOU_SEARCH_TBM`、`YOU_CHAT_MODE`、`YOU_NONCE`、`YOU_CID`、headers、cookies 等参数。为兼容上游暂未稳定确认的真实流式协议，当前 `stream=true` 采用完整回答切片为 OpenAI SSE 的方式输出。
  - 结论：当前交付物已经从“空壳代理”升级为“带真实默认上游链路的独立脚本”，可直接用于首轮问答转 OpenAI 兼容接口；深层线程多轮会话仍待后续补证。
  - 下一步：如需继续增强，就专注于补抓真实线程接口与 SSE 事件格式。

- 时间：2026-04-19
  - 阶段：继续增强多轮链路
  - 发现或问题：用户要求继续推进，因此当前目标从“首轮可用”升级为“尽量逼近真实多轮对话链路”。已知静态证据指向 `threadId`、`/api/threads`、`/api/chatThreads/:id`、`/api/snapshots` 与 `convertYouChatUpdateStep`，下一步要把这些静态证据收敛为可执行请求序列。
  - 结论：优先从已暴露的线程列表、线程详情与搜索页运行态 store 中定位 `chat_id`、当前线程对象、后续提交入口，再决定是否能在当前登录态下重放多轮请求。
  - 下一步：读取页面运行态与相关源码，锁定多轮提交函数和参数结构。

- 时间：2026-04-19
  - 阶段：多轮提交入口定位
  - 发现或问题：已从 `/search` 页面源码定位到真实提交流程。`fetchAnswer -> useStreamingSearch -> getSearchServiceParamsFE` 会把后续问题发往 `/api/streamingSearch` 或 `/api/streamingSavedChat`。URL 查询参数已明确包含：`q`、`page`、`count`、`safeSearch`、`chatId`、`conversationTurnId`、`cachedChatId`、`isNewChat`、`pastChatLength`、`selectedChatMode`、`selectedAiModel`、`sources`、`excluded_urls`、`clarificationResponses`、`queryTraceId`、`traceId`、`project_id`，并固定追加 `enable_editable_workflow=true`、`use_nested_youchat_updates=true`、`enable_agent_clarification_questions=true`。请求方法为 `POST`，payload JSON 至少包含 `query`、`chat`，以及可选 `submittedWorkflowSteps`、`knowledgeBase`。其中 `chat` 并非对象而是字符串化历史数组，内容形如 `[{question,answer}, ...]`。
  - 结论：这已经足够把“真实多轮接口存在且参数构造方式”证据化。当前缺的不是 endpoint，而是浏览器实际发起时附带的 headers、cookies，以及服务端返回的原生 SSE 事件名与数据体样例；但脚本已可据此新增第二条默认上游候选 `/api/streamingSearch`。
  - 下一步：继续提取 `SSE` 封装的事件监听集合与事件名，整理原生增量事件格式。

- 时间：2026-04-19
  - 阶段：多轮候选链路接入脚本
  - 发现或问题：已把 `YOU_UPSTREAM_MODE=streaming` 接入 `you2api.py`。当前会按已取证结构构造 `/api/streamingSearch` 或 `/api/streamingSavedChat` 的 URL 查询参数与 `POST` JSON 体，其中 `messages` 会转换为 `chat` 字符串化历史数组，最后一条用户消息映射为 `query`。同时在 README 补充了多轮链路参数、事件名证据和调用示例。
  - 结论：交付物已从“仅首轮真实默认链路”进一步升级为“可切换到已证据化多轮候选链路”的独立脚本；但当前仍未拿到最小必要请求头、cookies 与原生 SSE 事件数据样例，因此 `stream=true` 仍保留本地切片转发策略。
  - 下一步：运行语法校验并继续补抓真实 SSE 数据体，后续再决定是否改成原生事件透传。

- 时间：2026-04-19
  - 阶段：SSE 封装与请求头静态取证
  - 发现或问题：本轮继续尝试在运行态 hook 抓取真实多轮请求，但当前页面未稳定触发 `/api/streamingSearch`，浏览器日志里仍主要是 `search.json`、`/api/threads` 与周边初始化请求。转为静态源码取证后，已从 `0l4swrkpcp44i.js` 直接确认站内 SSE 并非原生 `EventSource`，而是自定义 `SSE` 类基于 `XMLHttpRequest` 实现流式读取：构造参数支持 `headers`、`payload`、`method`、`withCredentials`，内部通过 `xhr.open`、`setRequestHeader`、`xhr.send(payload)` 发起请求，并在 `readystatechange` 里暴露响应头、在 `progress/load` 阶段按 SSE chunk 解析 `event` 与 `data`。源码片段已明确 `new SSE(url,{method:"POST",payload:JSON.stringify(...)})`；当前截到的调用片段尚未显示显式自定义 headers，因此已证据化的最小请求头仍只有浏览器会自动带上的 `Content-Type` 与站点默认请求头语境，`x-requested-with` 暂无源码直证。
  - 结论：当前最可靠结论是：you.com 多轮链路确实是“XHR POST + text/event-stream 风格响应 + 前端自定义 SSE 解析器”，而不是浏览器 `EventSource`。这支持继续保留脚本里的 streaming 模式，但在拿到真实运行态请求前，不应把额外 headers 写死为确定事实。
  - 下一步：把 README 中关于最小请求头的表述收紧为“待运行态确认”，并继续围绕实际触发多轮提交去抓原生事件数据体样例。

- 时间：2026-04-19
  - 阶段：提交入口运行态校验
  - 发现或问题：已从 `12jp3bkwjs0ws.js` 继续确认搜索页 follow-up 输入框的真实提交流程：`QueryBar onSubmit -> handleSubmitQuery -> fetchStreamingResults`，其中 `fetchStreamingResults` 来自 `useStreamingSearch`。运行态检查也确认 textarea 外层存在 React `form` 且 `onSubmit` 为函数，说明提交入口本身没有判断错；但直接在当前页面调用该 `onSubmit` 后，网络层仍未出现 `/api/streamingSearch`，页面也未新增 hook 日志。这表明当前阻塞点已从“入口未知”收敛为“需要补齐触发所依赖的更高层状态或受当前页面上下文限制”，而不是简单的按钮没点对。
  - 结论：当前又证据化了一层：follow-up 的确走 `fetchStreamingResults/useStreamingSearch`，脚本里选择 `/api/streamingSearch` 作为多轮候选默认链路方向没有偏；但要拿到真实 SSE 数据体，下一步不能只靠 DOM 点击或裸调 form `onSubmit`，而要继续向上定位 `fetchAnswer` 组件实例或直接拦截 `fetchStreamingResults` 调用参数。
  - 下一步：继续从 React/Fiber 或源码入手，直接抓 `fetchStreamingResults` 的调用参数与触发条件，再反推出最小运行态依赖。

- 时间：2026-04-19
  - 阶段：上层 props 与触发条件进一步定位
  - 发现或问题：已继续沿 React Fiber 向上定位到持有 `onChange/onKeyDown/onSubmit/initialValue` 的 QueryBar 组件 props，并在运行态直接调用这一层 `onSubmit({query: textarea.value, omitRepeatedContext: true})`。返回值存在，但网络层仍无 `/api/streamingSearch`，页面也无加载态或 hook 日志。结合源码可进一步确认 `fetchStreamingResults` 内部真实会生成这些运行态参数：`conversationTurnId=uuidv4()`、`traceId=<chatOrPageTraceId>|<conversationTurnId>|<ISOTime>`、`domain=youchat`、`isExpressWorkflowUX=true`、以及根据 chat history 裁剪得到的 `chat` JSON 字符串；但当前页面上下文下，裸调 QueryBar `onSubmit` 仍不足以驱动真实流式请求。
  - 结论：阻塞点已进一步收敛到更高层业务状态，而不是参数结构未知。也就是说，多轮请求的 URL、核心 query 参数、payload 结构和 conversationTurnId/traceId 生成方式已经可以静态复原；当前唯一缺的主要是“什么前置状态会让前端真正放行这次调用”以及成功调用后的原生 SSE 数据样例。
  - 下一步：继续从更高层组件或 store 入手，优先找 `isLoadingAnswer`、chat thread、pageTraceId、chat history 等 gate 条件在当前页的实际取值，判断是哪一层阻止了请求落网。

- 时间：2026-04-19
  - 阶段：gate 条件继续收敛
  - 发现或问题：当前搜索页 URL 仍是 `https://you.com/search?q=请回复ok&fromSearchBar=true`，没有 `cid`；源码中的 `useChatId` 会把 `cid` 解析为 `c0_/c1_/c2_/s_` 前缀会话标识，`getYouChatParameters` 又会在 `isTriggeredChat=true` 时优先取 `trimmedChatId`，否则退回 `pageTraceId`。这说明当前页虽然可显示 follow-up 输入框，但它并不处在“已绑定 user saved chat id”的稳定上下文里，前端多轮链路很可能因此退化到更弱的 pageTrace 语义。运行态也印证了这一点：`__NEXT_DATA__.props.pageProps.pageTraceId` 存在，但页面文本中看不到首轮回答内容，只有布局与输入区域，说明当前会话上下文并未完整挂载到可继续追问的状态。
  - 结论：阻止 `/api/streamingSearch` 落网的 gate 很可能与“当前页没有有效 `cid`/chat thread 上下文，导致 follow-up 组件虽渲染但未进入可提交状态”有关。这比此前的泛化说法更具体：不是随便一个 `/search?q=...` 页都能稳定复用多轮入口，至少还需要已创建的 chat id 或已完成的 chat thread 装载条件。
  - 下一步：优先围绕 `cid`/`chat thread` 继续取证，尝试从 `api/threads`、已加载 thread 列表或页面 store 中拿到一个真实 `c1_...` 会话并切到对应 URL，再重新抓 streaming 请求与 SSE 数据体。

- 时间：2026-04-19
  - 阶段：真实会话提取尝试
  - 发现或问题：本轮继续沿 `api/threads` 与页面运行态追踪。静态源码已确认线程列表确实由 `GET /api/threads?shouldFetchFavorites=...` 拉取，返回对象中存在 `chat_id`；`useChatId` 会把 URL 里的 `c1_xxx` 去前缀得到 `trimmedChatId` 参与后续多轮参数构造。但当前浏览器抓到的 `api/threads` 请求始终停留在 pending，拿不到响应体；页面 DOM 中也没有暴露带 `cid=` 的链接，浅层 React root/state 扫描同样没有直接捞到 `c1_...` 字符串。这说明“会话 id 不可见”不是因为没找对字段，而是当前运行态没有把 thread 数据落到易读位置，或请求本身尚未在这次会话里完成。
  - 结论：目前已经把 `c1` 线索收敛到最小集合：真实会话 id 的来源应是 `api/threads` 响应或加载的 thread store，而不是当前 `/search?q=...` 页面 HTML/URL 本身。也就是说，继续硬扫 DOM 价值已经很低，后续更应该围绕已存在的线程接口响应、切换到已有 chat 详情页、或重新制造一个能稳定完成 thread 装载的页面环境来取证。
  - 下一步：继续优先盯住线程详情与列表接口，一旦拿到任意 `c1_...`，立刻切页复测 `/api/streamingSearch` 与 SSE 事件体。

- 时间：2026-04-19
  - 阶段：借助首页推荐会话切页复测
  - 发现或问题：已从首页推荐卡片对应的 `search.json` 请求里直接拿到一组真实 `c1_...` 会话 URL，并成功切到 `cid=c1_e9233c39-718e-49ec-a4d5-2f5c8b1950e7` 的搜索页。这证明此前关于“需要真实会话上下文”的判断是对的，而且不必强依赖 `api/threads` 响应才能拿到可用 `cid`。但切到真实 `c1` 页后，页面仍只渲染壳层与 follow-up 输入框，看不到历史回答内容；在该页重新注入 hook 并触发表单提交后，依旧没有 `/api/streamingSearch` 请求、没有 XHR hook 日志、也没有 SSE/WS 痕迹。
  - 结论：当前阻塞点进一步收敛为：即便已有真实 `c1`，页面仍未完成让 follow-up 生效所需的完整聊天内容装载或交互初始化，因此“只要有 `cid` 就能直接追问”的假设也不成立。现阶段已能确定多轮前置条件至少包含“真实会话 id”之外的另一层页面/线程加载状态。
  - 下一步：继续围绕真实 `c1` 页本身取证，优先确认历史消息详情接口、chat thread 详情接口或客户端恢复逻辑，找出为什么页面没有把会话正文挂载出来，再据此逼近 streamingSearch 的最终 gate。

- 时间：2026-04-19
  - 阶段：真实 c1 页恢复逻辑继续取证
  - 发现或问题：当前真实 `c1` 页的 `__NEXT_DATA__.query` 已明确包含 `cid=c1_e9233c39-718e-49ec-a4d5-2f5c8b1950e7`，且 `pageTraceId`、登录用户、`nonce`、模型列表都正常存在，说明并是 SSR 参数缺失或未登录导致的空壳页。与此同时，网络侧仍只看到对应 `search.json?cid=c1_...`，没有 `/api/threads/:id`、`/api/chatThreads/:id` 或其他线程详情请求自动发出；源码又确认 `useChatThreadById` 的详情来源其实就是 `GET /api/threads/${trimmedChatId}`。这把问题进一步缩到“搜索页本身未主动触发 thread detail 恢复逻辑”，而不是接口不存在。
  - 结论：当前最有价值的新结论是：真实 `c1` 页缺正文，并非因为 URL、登录态或 page props 不完整，而是因为客户端在当前会话里没有自动走 `GET /api/threads/${trimmedChatId}` 这条详情恢复路径。也就是说，若要把脚本继续逼近多轮真实链路，下一步要重点研究“什么组件或条件会触发 thread detail 加载”，以及搜索页与 thread detail 的职责边界。
  - 下一步：继续沿 `useChatThreadById`、`useChatThread`、`currentChatThread` 的调用链静态定位谁在什么时候请求 `/api/threads/${trimmedChatId}`，必要时再在运行态找触发它的组件或交互。

- 时间：2026-04-19
  - 阶段：thread detail 触发条件继续收敛
  - 发现或问题：已把 `useChatThread` 与 `useChatThreadById` 的关系再压实一层。`useChatThread` 内部只是 `useChatId -> useChatThreadById(trimmedChatId)` 的薄封装，而 `useChatThreadById` 的触发条件只有 `enabled: !!trimmedChatId`，并无额外 gate。当前真实 `c1` 页运行态也已确认 `trimmedChatId=e9233c39-718e-49ec-a4d5-2f5c8b1950e7` 非空，因此按静态逻辑本应直接请求 `GET /api/threads/${trimmedChatId}`。但实际网络没有该请求，说明问题不在 hook 内部条件，而在于搜索页当前渲染树根本没有进入会消费 `useChatThread` 的那支组件，或者对应动态 chunk 尚未加载执行。
  - 结论：这比之前更进一步：不是“搜索页触发 thread detail 的条件未知”，而是“当前页面虽然带真实 `cid`，但没有渲染到依赖 `useChatThread` 的正文组件树”。换句话说，缺正文的根因更像是搜索页正文区域对应的动态组件没有挂载，而不只是单个请求被拦截。
  - 下一步：继续追 `/search` 页面动态加载的正文组件 `91164 -> 793091` 及其依赖，定位它在什么条件下才会挂载 chat history / currentChatThread 相关子树，再决定是否能从运行态强行触发或在脚本侧直接绕过这层前端 gate。

- 时间：2026-04-19
  - 阶段：正文动态组件挂载条件继续定位
  - 发现或问题：已进一步确认 `/search` 页外层结构。`12jp3bkwjs0ws.js` 中页面默认导出会把 `fetchAnswer` 注入动态组件 `Y=(0,t.default)(()=>e.A(91164),{loadableGenerated:{modules:[793091]}})`，随后渲染为 `$` 布局内的 `<Y fetchAnswer={t} />`。同一文件中 `R()` 明确是 follow-up QueryBar 最终调用的 `handleSubmitQuery`，内部在未命中复制线程弹窗、长度校验和 loading gate 时才会执行 `useStreamingSearch().fetchStreamingResults(...)`。运行态检查当前真实 `c1` 页 `chat-history-container` 仅含 `ChatHistoryContentContainer + NullStateContainer`，文本只有 `Today`；同时 `window.__NEXT_DATA__.props.pageProps` 不含 `cid`，仅有 `pageTraceId`、`user`、`nonce`、`aiModels` 等初始化字段，说明真实 `cid` 已只存在 URL 查询参数与路由层，不在 SSR pageProps 中直接下发给正文区域。静态源码还确认 `useChatThread` 定义位于 `01nxvlk2k1val.js`，但当前外层页面只把 `fetchAnswer` 传给动态正文组件，因此 thread detail 恢复、正文分支切换和实际 follow-up 放行条件都被封装在 `91164 -> 793091` 这支异步模块内部，而不是 `/search` 页壳层本身。
  - 结论：当前最新收敛点是：`/search` 页壳层已经正确装载、follow-up QueryBar 也真实连到 `fetchStreamingResults`，但正文分支是否从 `NullStateContainer` 切到真实会话内容，取决于异步模块 `793091` 内部的状态恢复逻辑；现有证据尚不能证明动态 chunk 未加载，反而更像是它已加载但走到了 chat history 的空状态分支。也就是说，下一步应直接针对 `793091` 及其依赖查找 `NullStateContainer` 被选中的条件，而不是继续停留在外层页面。
  - 下一步：继续定位 `793091` 对应脚本源、锁定 chat history 空状态与正文状态的判定条件，并据此确认为什么真实 `c1` 页没有触发 `/api/threads/${trimmedChatId}`。

- 时间：2026-04-19
  - 阶段：chat history 空状态分支继续取证
  - 发现或问题：已从 `0w-wlpa-61bhy.js` 进一步确认左侧 chat history 相关实现与当前 DOM 命中同一套样式导出：`ChatHistoryContentContainer`、`ChatHistoryGroupTitle`、`NullStateContainer` 都定义在该 chunk 内。运行态再次确认 `chat-history-container` 的实际 HTML 只有 `<ChatHistoryContentContainer><NullStateContainer><h4>Today</h4></NullStateContainer></ChatHistoryContentContainer>`，没有任何 thread item、`youchat-answer`、`chat-top-navigation-current-chat-name` 或会话正文节点。同时同一 chunk 可见 `ButtonDialogChatThreadsSearchOpen`、`SectionSignin`、`SectionHeader` 等完整侧栏能力，说明当前侧栏并非未加载，而是已经正常渲染到“空历史”分支。另一个关键点是：`0w-wlpa-61bhy.js` 中可见 `isCopyThreadModalOpen` 读取，结合 `12jp3bkwjs0ws.js` 可知外层 follow-up 提交前确实会先检查复制线程弹窗路径；但当前页面并未出现复制线程弹窗或登录引导文本，说明阻塞并不表现为显式弹窗覆盖，更像是当前会话数据根本没有注入到 chat history / current thread 对应 store。
  - 结论：目前可以排除“侧栏 chunk 未加载”“被登录引导替换”“被复制线程弹窗直接拦住”这几类更表层解释。最新最强结论是：真实 `c1` 搜索页已经加载了完整 chat layout 侧栏模块，但该模块拿到的 chat history / current thread 数据为空，因此稳定落在 `NullStateContainer` 分支，仅显示 `Today`；这与 `/api/threads/${trimmedChatId}` 没有触发是同一症状的两面。
  - 下一步：继续在 `793091` 及相关 chunk 中追 chat history 数据源、store 注入点和空分支判定条件，确认究竟是 `useChatThread` 未被消费，还是消费它的更内层组件在当前搜索页条件下被短路。

- 时间：2026-04-19
  - 阶段：chat history 数据源继续收敛
  - 发现或问题：已从 `0wyudjv07b8.h.js` 直接确认 `useChatHistory()` 的完整实现。它不是基于当前 URL 的 `cid` 恢复侧栏，而是完全依赖 React Query 拉取两组列表接口：`GET /api/threads?shouldFetchFavorites=false&count=30` 作为 recents，`GET /api/threads?shouldFetchFavorites=true&count=200` 作为 favorites；随后将结果按 `Today / Yesterday / Previous 7 Days / Previous 30 Days / 月份 / 年份` 分组，并在数据为空时走 `NullStateContainer`。运行态网络也已证据化：当前页确实发起了这两条 `/api/threads` 请求，但都持续处于 pending，没有落到 performance resource 条目，也没有可读 initiator 栈。这解释了为什么 chat history 会稳定为空：不是分组逻辑误判，而是列表查询根本没有成功返回。与此同时，`window.__NEXT_DATA__.query.cid` 已确认存在，`pageProps` 中仍没有任何 thread 数据，说明页面不会用 SSR 直接注入侧栏会话列表。
  - 结论：当前最关键的新收敛点是：左侧空状态的直接根因不是组件没渲染，而是 `useChatHistory()` 依赖的两条 `/api/threads` 列表请求都悬而未决；而正文不恢复则还叠加了 `useChatThreadById(trimmedChatId)` 没被实际消费的问题。也就是说，当前真实 `c1` 搜索页同时存在“列表查询 pending、详情查询未触发”两层异常，导致 chat layout 只能呈现有壳无数据的状态。
  - 下一步：继续追 `/api/threads` 为什么在当前页长期 pending，以及哪一层组件或状态让 `useChatThreadById(trimmedChatId)` 没有进入实际消费路径，优先判断两者是否共享同一个更上游 gate。

- 时间：2026-04-19
  - 阶段：半初始化登录态继续取证
  - 发现或问题：本轮继续沿认证层收敛。运行态已确认 `window.__NEXT_DATA__.props.pageProps.user` 包含 `email=test@example.test`、`sub/descope_user_id` 等完整用户信息，但浏览器当前 `document.cookie` 中既没有 `DS` 也没有 `DSR`。静态源码 `0wom~-sg5aj_z.js` 明确导出了 `DESCOPE_SESSION_COOKIE="DS"`、`DESCOPE_SESSION_REFRESH_COOKIE="DSR"`、`BACKEND_AUTH_HEADER_NAME="Authorization"`；另一个 Descope 相关 chunk 也直接读取 `parseCookies()[DESCOPE_SESSION_COOKIE]` 作为登录态监测依据。这说明当前页面确实处在一种“前端已拿到 user 对象，但浏览器侧缺少 Descope 会话 cookie”的半初始化状态，而不是完整后端会话已绪。
  - 结论：当前最像真实根因的解释是：页面通过 SSR 或前置初始化拿到了 user 信息，所以 UI 看起来已登录；但浏览器上下文缺少真实 Descope 会话 cookie，导致依赖后端会话的 `/api/threads` 列表请求长期 pending，thread 详情恢复链路也无法闭环。也就是说，问题可能不在 chat 组件本身，而在“显示已登录”与“具备可调用内部 thread API 的真实会话”之间存在状态断层。
  - 下一步：继续验证这种半初始化登录态是否就是 `/api/threads` 悬挂的共同上游原因，并据此判断最终交付应继续走 `search.json` 稳定链路，还是必须要求补齐真实 Descope 会话后才能逼近多轮线程接口。

- 时间：2026-04-19
  - 阶段：半初始化登录态与线程接口关系再压实
  - 发现或问题：本轮新增三类硬证据。其一，当前真实 `c1` 搜索页网络层只有两条线程列表请求：`GET /api/threads?shouldFetchFavorites=false&count=30` 与 `GET /api/threads?shouldFetchFavorites=true&count=200`，两者都持续为 pending。其二，运行态再次确认当前 URL 已带真实 `cid=c1_e9233c39-718e-49ec-a4d5-2f5c8b1950e7`，`__NEXT_DATA__.props.pageProps.user` 仍完整存在，cookie 中仍无 `DS/DSR`，同时 localStorage 里只看到 `descopeFlowNonce*`、`dls_last_auth`、`dls_last_user_login_id` 等前端痕迹，没有可直接替代后端会话的显式 token。其三，静态源码 `04rkztn9t7q~a.js` 明确存在定时逻辑：周期性 `parseCookies()[DESCOPE_SESSION_COOKIE]`，一旦读不到 `DS` 就会记录 `AuthLogoutClientErrorSession` 指标，说明前端确实把 `DS` 视为真实登录会话是否仍然有效的关键依据，而不是可有可无的附属 cookie。
  - 结论：到这一步可以更强地判断：当前异常不是普通的 UI 空状态，而是“前端拿到 user 对象，但认证层未形成可被内部 thread API 接受的完整会话”。`/api/threads` 长期 pending、真实 `c1` 页正文不恢复、`useChatHistory()` 持续为空，这三件事更像同一个认证断层的并发表现。因此当前最稳交付仍应坚持 `search.json` 首轮链路；若要逼近稳定多轮线程链路，必须把“补齐真实 Descope 会话条件”视为前置要求，而不能再假设仅凭 `cid`、`user`、nonce 或局部 localStorage 就足够。
  - 下一步：继续在源码中追 `/api/threads` 与认证层的直接耦合点，尽量确认它是等待 cookie 刷新、Authorization 注入，还是被上游网关挂起；同时在 README 收紧多轮链路前提描述，避免把当前 streaming/thread 模式表述成默认可直接复现。

- 时间：2026-04-19
  - 阶段：认证层直接耦合点继续定位
  - 发现或问题：本轮已把认证层实现再往前压实。`/api/threads` 与 `/api/threads/${id}` 两处调用本身都只是通过统一 HTTP 客户端 `556631.default.get(...)` 发起，请求侧源码里没有为 thread 接口单独追加特殊参数，说明线程接口是否可用主要取决于更上游的全局认证上下文。另一条关键证据来自 Descope SDK chunk `00x.yl86v~r34.js`：其底层请求构造会从 `DS/DSR` 派生 token，并显式组装 `Authorization: Bearer <token>` 与 `x-descope-sdk-session-id`；刷新逻辑则走 `/v1/auth/try-refresh` 或 `/v1/auth/refresh`，且接受 `externalToken` 参与恢复。这说明站内认证并不是“只有 cookie 就完事”，而是“cookie -> token/refresh -> Authorization/会话头”的链式恢复。当前页面没有 `DS/DSR`，就意味着这条恢复链前半段天然断裂；而 `localStorage` 中现有 `descopeFlowNonce*`、`dls_last_auth` 等痕迹不足以直接替代这条链。
  - 结论：现阶段更合理的判断是：`/api/threads` pending 不是线程接口自己的业务 gate，而是统一认证上下文没恢复完整，导致内部 API 调用缺少可用的 token/Authorization 状态。也就是说，真实多轮链路当前卡住的位置更像“认证恢复没闭环”，而不是“thread 参数结构还不够完整”。因此交付层面继续把 `search.json` 作为默认稳定链路是对的；`streamingSearch`、`streamingSavedChat`、`/api/threads` 相关能力都应明确视为“依赖完整 Descope 会话恢复”的增强模式。
  - 下一步：继续找统一 HTTP 客户端 `556631` 是否存在与认证 store、刷新状态或请求拦截器的直接耦合；若找不到更强反证，就可把“多轮必须补齐真实 Descope 会话”视为当前阶段结论写入 README。

- 时间：2026-04-19
  - 阶段：pending 与失败分支差异继续压实
  - 发现或问题：本轮又补上一条重要侧证。`useChatHistory()` 在 `0wyudjv07b8.h.js` 里对 `GET /api/threads` 的封装非常直接：若请求抛错，只会调用 `frontendLogger.error({message: 'Failed to fetch chat threads (...)'})`，随后返回空数组，让左侧历史列表走正常的“已失败但可回退”路径。但当前真实页面的两条 `/api/threads` 不是 401/403/4xx 后进入 catch，而是长期处于 pending；控制台里也只有大量泛化的资源报错，没有看到与 `Failed to fetch chat threads` 对应的显式前端错误。这说明当前症状并不像“线程列表请求已被业务层明确拒绝”，而更像请求在认证恢复、网关或连接层就被挂住，导致前端连进入失败回退分支的机会都没有。
  - 结论：这进一步支持前面的判断：问题主轴不在 thread 列表组件本身，也不在 `useChatHistory()` 的数据处理，而在更上游的统一请求通道或认证恢复链。换句话说，如果只是普通鉴权失败，前端大概率会落入 catch 后返回空数组；现在之所以一直 pending，更像是统一客户端发出的内部 API 请求在会话未闭环时被挂起。当前默认交付继续坚持 `search.json`，而把 thread/multi-turn 视为“需要完整真实会话”的增强模式，仍然是最稳妥的结论。
  - 下一步：继续尝试定位统一 HTTP 客户端 `556631` 是否有全局请求/响应拦截、重试或等待刷新完成的机制；若能找到，就能把“pending 源于认证恢复等待”再证据化一层。

- 时间：2026-04-19
  - 阶段：统一 HTTP 客户端机制继续取证
  - 发现或问题：本轮已把 `556631` 对应实现再向里展开，确认它本质是站内打包后的 axios 实例。源码可见 `this.interceptors={request:new el,response:new el}`，请求分发前会遍历 `interceptors.request` 与 `interceptors.response`，并支持 `runWhen`、同步/异步执行、取消信号、`withCredentials`、XSRF cookie/header 注入等机制。这至少证明两点：第一，站内统一客户端具备全局挂载请求/响应拦截器的能力，因此 `/api/threads` pending 完全可能是更高层拦截逻辑导致，而不是业务 hook 自身造成；第二，当前看到的 `pending` 不太像 axios 基础适配器的“默认无限等待”副作用，因为适配器层对网络错误、超时、状态码失败都有明确 reject 路径，只有在请求被更上游逻辑延迟放行、等待某个刷新过程，或连接侧长期不回包时，前端才会长时间停在 pending 而不进入 `useChatHistory()` 的 catch。
  - 结论：虽然目前还没直接抓到 you.com 给 `556631` 注册的具体拦截器函数，但证据链已经更完整了：`useChatHistory()` 本身只是普通 query hook，`/api/threads` 本身只是普通 GET，请求底层又是具备全局拦截能力的 axios 实例；因此当前异常更应归因于统一认证/请求通道，而不是 thread 业务层单点逻辑。换句话说，“真实多轮链路要先恢复完整 Descope 会话，再谈 thread/streaming 重放”这个阶段判断继续被强化。
  - 下一步：继续追哪些业务 chunk 对 `556631.interceptors` 做了 `use(...)` 注册，尤其是与 auth refresh、用户初始化、session 恢复相关的调用点；若仍找不到明确注册点，再回头结合运行态对 `/v1/auth/try-refresh` 与内部 API 的先后关系做验证。

- 时间：2026-04-19
  - 阶段：认证恢复等待链路继续压实
  - 发现或问题：本轮运行态又拿到一条关键并行证据。当前页面除两条 `/api/threads` 列表请求一直 pending 外，还同时存在 `POST https://auth.you.com/v1/auth/try-refresh?dcs=f&dcr=f` 处于 pending。结合此前 Descope SDK 源码已确认 `try-refresh` 属于会话恢复入口，且 token/Authorization/x-descope-sdk-session-id 依赖 `DS/DSR -> refresh` 这条链生成，这意味着现场并不是“thread 请求单独挂住”，而是认证恢复请求与 thread 内部 API 请求一起卡住。再结合 `useChatHistory()` 的失败分支不会触发、`/api/threads` 既不成功也不显式报错，当前症状已经非常像“前端在等待 auth refresh 或会话恢复完成，但恢复链本身没有闭环”，从而把依赖同一会话上下文的内部接口整体拖成 pending。
  - 结论：到这一步，`/api/threads pending` 与“半初始化登录态”之间的关系已经更接近闭环：不是单独某个 thread hook 异常，而是认证恢复本身也在 pending，导致需要完整登录会话的内部 API 一起不可用。因此当前交付策略继续维持不变：`search.json` 仍是唯一稳定默认链路；`/api/streamingSearch`、`/api/streamingSavedChat`、`/api/threads` 等多轮能力只能作为“补齐真实 Descope 会话后再尝试”的增强模式。
  - 下一步：继续看 `try-refresh` 与站内登录态初始化顺序，判断是否存在“先等 auth refresh，再放行内部 API”的显式调用链；若证据不足，就可把“真实多轮依赖完整 Descope 会话恢复”作为当前阶段最终判断固定到 README。

- 时间：2026-04-19
  - 阶段：登录态判定与真实会话再次拆分
  - 发现或问题：本轮继续追初始化顺序后，拿到一条很关键的静态证据：`useSignInToYDC` 的实现只是读取 `useUser()` 返回的 `user`，再用 `!!user` 作为 `isSignedInToYDC`；并不会检查 `DS/DSR`、`try-refresh` 是否完成，或内部 API 是否实际可用。与此同时，`useUser()` 本身来自 Descope hook，经 `massageDescopeUserObject` 后只要能拿到 user object 就会让站内许多功能判定“已登录”。这就解释了为什么当前页面会同时出现两类看似矛盾的现象：一方面 UI、`__NEXT_DATA__`、`useSignInToYDC` 都把用户视为已登录；另一方面真实认证恢复仍卡在 `try-refresh pending`，而 `/api/threads` 等内部接口并没有因此真正可用。另一个补强证据是 Descope SDK 仍会把 `dls_last_user_login_id`、`lastAuth` 等前端记录回填到请求参数中，但这些本地痕迹显然不足以替代缺失的 `DS/DSR` 与刷新后的真实会话。
  - 结论：当前已经可以明确区分两层状态：第一层是“前端显示登录态”，它只要求拿到 user object；第二层是“后端内部 API 可用态”，它还要求完整 Descope 会话恢复成功。you.com 当前卡住的是第二层，而不是第一层，所以页面会呈现一种非常具有迷惑性的半初始化状态：UI 看似已登录，`isSignedInToYDC` 也为真，但 `/api/threads`、多轮 thread/streaming 相关内部接口仍不可用。这个结论进一步巩固了当前交付策略：默认只交付 `search.json` 首轮链路，多轮模式必须视为依赖真实完整会话恢复的增强能力。
  - 下一步：继续检查是否还有使用 `isSignedInToYDC` 作为 gate 的 thread / streaming 相关 hook，确认前端是否因为“误判已登录”而过早放行了某些组件渲染，最终导致页面呈现壳层已开但数据层未恢复的状态。

- 时间：2026-04-19
  - 阶段：thread 与 streaming gate 继续压实
  - 发现或问题：本轮继续沿 thread / streaming 相关 hook 往下追，结果更明确了。`useStreamingSearch` 所在 chunk `0l4swrkpcp44i.js` 内部直接读取 `{isSignedInToYDC:T}=(0,en.useSignInToYDC)()`，并把它用于部分行为与埋点分支，例如 `freemiumQueriesRemaining: !T || d ? void 0 : N`；这说明 streaming 相关模块确实把“前端登录态”当成已知前提的一部分。与此同时，同一个模块又直接依赖 `useChatHistory()`、`useYouProState()`、`useChatId()`、`useChatThread()` 等更深层数据源，而这些数据源最终会落到 `/api/threads`、`/api/user/getYouProState` 等内部接口。也就是说，当前页面并不是 streaming UI 与 thread UI 完全分离，而是“壳层逻辑先基于 `isSignedInToYDC` 放行或切换分支，真实数据层再去碰内部 API”。由于 `isSignedInToYDC` 只要求 `user` 存在，这恰好会制造当前这种表象：组件树与 follow-up 输入框可以先渲染出来，但真正依赖完整会话的线程列表、thread detail、订阅态、cached chat 等数据层仍会卡在未恢复状态。
  - 结论：到这一步，页面为何会出现“UI 壳层已开、追问输入框存在、但正文和线程数据不恢复”的原因已经更清晰了：前端把 `useUser -> isSignedInToYDC` 当作组件层 gate，而不是把“Descope 会话恢复成功”当作 gate；因此组件可以先显示，但底层 thread / streaming 数据请求不保证能成功。这个机制与当前观察到的 `try-refresh pending`、`/api/threads pending`、`NullStateContainer`、无正文恢复现象是相互一致的。
  - 下一步：继续补查 `useYouProState`、`useChatThread`、`useChatHistory` 这几条内部数据链是否都只以 `isSignedInToYDC` 作为 enabled 条件，进一步确认“组件显示 gate”与“真实可用 gate”分离是站内普遍模式，而不是个别 hook 特例。

- 时间：2026-04-19
  - 阶段：核心内部数据链 enabled 条件核对
  - 发现或问题：本轮已把三条核心内部数据链的 gate 条件进一步压实。第一，`useYouProState` 在 `0j262z7dzznpo.js` 中的 query 明确是 `enabled: e`，其中 `e` 就来自 `useSignInToYDC().isSignedInToYDC`。第二，`useChatHistory` 在 `0wyudjv07b8.h.js` 中同样先读取 `{isSignedInToYDC:s}`，再把 recents/favorites 查询都挂到 `enabled: s` 上。第三，`useChatThreadById` 在 `0jf..ndgfpn7b.js` 中的 gate 仅是 `enabled: !!e`，也就是只要有 `trimmedChatId` 就会尝试请求详情，并不要求认证恢复成功。把这三点合在一起，就能解释当前现场的全部矛盾：组件层只要“有 user”或“有 cid”就会放行查询，但这些查询能否真正完成，仍取决于更下游的完整会话恢复；于是页面会同时出现“组件已渲染、查询已发起、但请求长期 pending”的半初始化状态。
  - 结论：现在基本可以把“组件显示 gate”和“真实可用 gate”分离视为站内普遍模式，而不是个别 hook 特例。`useYouProState`、`useChatHistory`、`useStreamingSearch` 都把 `isSignedInToYDC` 当作足够条件；`useChatThreadById` 甚至只看 `cid`。这使得前端非常容易在 `user` 已有但 Descope 会话未闭环时，过早显示已登录壳层并发起内部 API 请求，从而形成当前 `try-refresh pending + /api/threads pending + UI 已开` 的统一现象。对本项目交付而言，这意味着多轮 thread/streaming 方案不能只依赖页面里已有的 `user`、`cid`、nonce 或 localStorage 痕迹，而必须把“真实会话恢复成功”当成前置条件。
  - 下一步：继续补查是否还有直接依赖 `cid` 或 `isSignedInToYDC` 的其他 chat 数据 hook，例如 cached chat、projects、subscriptions 等，以确认当前半初始化现象是否会系统性影响更多内部能力；若模式已足够稳定，也可开始把阶段结论收束为当前任务的最终分析结论。

- 时间：2026-04-19
  - 阶段：半初始化状态的横向影响继续验证
  - 发现或问题：本轮横向补查后，模式继续复现到更多内部能力。`useProjectsGet` 在 `0w-wlpa-61bhy.js` 中明确是 `let { isSignedInToYDC:a } = useSignInToYDC(); ... enabled:a`；`useEntitlementsGet` 在 `13swef9r84of2.js` 中同样是 `let { isSignedInToYDC:r } = useSignInToYDC(); ... enabled:r`。也就是说，不只是 chat history、you pro state、streamingSearch，这类“前端有 user 就认为可以查内部能力”的模式已经扩散到 projects、entitlements 等其他站内受保护数据。结合前面 `try-refresh pending` 与 `/api/threads pending` 的共现，这说明当前半初始化状态并不是某个 chat 页面特例，而是整站内部能力都会受到同一认证断层影响：组件或 query 会因为 `isSignedInToYDC=true` 被提前放行，但真正依赖后台会话的请求仍可能挂住或不可用。
  - 结论：到这一步，可以更有把握地把当前现象定性为“站内普遍存在的双层登录态模型”：前端展示层只看 `user`，内部能力层还要等真实 Descope 会话恢复完成。当前 you.com 搜索页之所以表现得最明显，是因为 thread/chat 链路对会话恢复更敏感，但问题本质并不只属于 chat。本项目的最终交付判断也因此更稳了：当可稳定独立交付的仍只有 `search.json` 首轮方案；所有依赖内部会话能力的多轮 thread/streaming 方案，都必须带着“需要真实完整 Descope 会话”的前提来使用与说明。
  - 下一步：继续收束这些横向证据，准备把当前阶段结论整理为最终分析结论，并仅在仍有关键缺口时再追更深实现细节。

- 时间：2026-04-19
  - 阶段：阶段性最终结论收束
  - 发现或问题：经过本轮连续取证，当前关键证据已经形成闭环。源码层面，已确认首轮稳定链路是 `/_next/data/<buildId>/<locale>/search.json`，多轮候选链路是 `POST /api/streamingSearch` 或 `POST /api/streamingSavedChat`，且前端用的是基于 `XMLHttpRequest` 的自定义 SSE 封装。认证层面，已确认 `DS/DSR -> token/refresh -> Authorization/x-descope-sdk-session-id` 的恢复链存在，并在运行态看到 `auth.you.com/v1/auth/try-refresh` 与 `/api/threads` 同时 pending。状态层面，已确认 `useSignInToYDC` 只看 `user`，`useYouProState`、`useChatHistory`、`useProjectsGet`、`useEntitlementsGet` 等查询会因此被提前 enabled，而 `useChatThreadById` 甚至只看 `cid`。运行态层面，当前页面同时满足“有 user、无 DS/DSR、有真实 c1、有 follow-up 输入框、无正文恢复、/api/threads pending、try-refresh pending”，这组现象与“半初始化登录态”完全一致。
  - 结论：当前任务的最终分析结论可以定为两部分。其一，`analysis/you2api/you2api.py` 默认走 `search.json` 首轮问答链路是当前最稳、最可独立交付的方案，这也是当前唯一不依赖完整内部会话恢复的稳定路径。其二，站内真实多轮 thread/streaming 能力虽然已被充分证据化，但当前并不能把它当作默认可复现方案，因为它依赖真实完整的 Descope 会话恢复；在仅有 `user`、`cid`、nonce、localStorage 痕迹而缺少 `DS/DSR` 或有效 refresh 闭环时，页面会进入“UI 似乎已登录、组件壳层已放出、内部接口却整体不可用”的半初始化状态。换句话说，当前脚本已成功交付“稳定首轮 + 候选多轮接口适配能力”，但多轮能力必须明确标注为“需要完整真实会话条件”。
  - 下一步：若后续继续推进，应把重点切换到两类新增证据之一：一是拿到真实有效 `DS/DSR` 会话并复测 thread/streaming 全链路；二是直接抓到成功的 `streamingSearch` / `streamingSavedChat` 原生 SSE 数据样例。若没有这两类新增证据，继续深挖前端壳层实现的收益已经明显下降。

- 时间：2026-04-19
  - 阶段：交付前复核与真实验证
  - 发现或问题：用户本轮要求“验证可行后才能交付”，因此仅靠静态分析与本地 mock 不足，需要对现有脚本在真实 you.com 上再做一次最小验证，并复核 README 是否准确说明最小必要 headers、cookies、模型映射与会话状态维护方式。
  - 结论：先对现有脚本做语法与接口自测，再针对真实站点补抓当前页面的 `__NEXT_DATA__`、网络请求与 cookies 证据，最后按验证结果修正文档与脚本。
  - 下一步：执行本地测试与浏览器侧复核。

- 时间：2026-04-19
  - 阶段：真实可用性最小验证
  - 发现或问题：已实际启动 `analysis/you2api/you2api.py` 并调用本地 `/v1/models`、`/v1/chat/completions`。`/v1/models` 正常返回 `gpt_5_1_instant`；对真实 you.com 发起 `hello` 时，默认 `search.json` 链路返回的 `raw_upstream` 中包含 `pageTraceId`、`pageUrl=/search?q=hello&tbm=youchat&chatMode=custom`、`user=null` 等字段，初始提取结果误落到 UUID 样式 `pageTraceId`，而不是自然语言回答。这说明脚本链路可运行、接口兼容层正常，但匿名 `search.json` 的默认结果结构并不总能直接映射成最终回答文本。
  - 结论：现有脚本已通过“真实上游可达 + 本地 OpenAI 兼容接口可用”的最小验证，但还需修正回答提取逻辑，并在 README 中把匿名首轮链路的限制说清楚，避免把当前状态误写成稳定自然语言对话已完全验证。
  - 下一步：检查真实 `raw_upstream` 结构，修正文本提取与文档表述。

- 时间：2026-04-19
  - 阶段：提取逻辑修正与复测
  - 发现或问题：已在 `you2api.py` 的 `_extract_from_data` 中提高 `youChatAnswer` 字段优先级，并补充 README：保留 `raw_upstream` 便于继续校正字段提取，同时明确首轮匿名链路目前仅验证“真实可达”，不等于“稳定自然语言回答”。随后继续复测时，站点直接返回 `Account or domain blocked for abuse. Contact Support for resolution`，说明当前环境对应账号、域名或出口已被 you.com 风控封禁，后续真实问答链路已无法在此上下文继续完成。
  - 结论：当前阻塞已从“字段提取是否准确”升级为“上游环境被封禁”。这意味着我现在无法仅靠继续重试完成有效复测；后续若要继续验证真实首轮或多轮回答，必须先更换可用账号、网络出口或解除风控状态。
  - 下一步：收紧 README 与最终结论，明确说明当前交付已完成静态取证、接口适配与最小真实命中验证，但进一步真实问答复测受上游封禁阻塞。
