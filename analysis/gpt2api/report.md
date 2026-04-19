# chatgpt.com 对话链路分析报告

## 说明

本文档仅用于学习前端请求编排、事件流解析与会话状态设计思路，基于本次在浏览器中观察到的真实运行态与前端源码证据，输出高层分析结论。本文档不提供可直接复用的私有接口调用脚本，不提供可操作的最小认证材料复刻步骤，也不提供可直接模拟受保护会话的实现细节。

## 一、分析范围与证据来源

本次分析基于以下证据：

- 访问 `https://chatgpt.com` 后的前端网络请求列表
- 页面加载后的 `localStorage` 键分布
- 前端脚本中与对话链路相关的关键字符串搜索结果
- 用户手动发送一条测试消息后新增的网络请求
- 前端脚本中关于 `text/event-stream`、`chat-requirements`、`model_slug`、`stream_status`、`/f/conversation` 的实现片段

## 二、阶段性核心结论

### 1. 当前聊天主入口已迁移到新的对话路径

早期常见的 `/backend-api/conversation` 已不再是唯一主入口。本次真实发送消息后，核心链路表现为：

- `POST /backend-api/f/conversation/prepare`
- `POST /backend-api/f/conversation`
- `POST /backend-api/sentinel/chat-requirements/prepare`
- `POST /backend-api/sentinel/chat-requirements/finalize`
- `GET /backend-api/conversation/{conversation_id}/stream_status`

这说明当前网页端聊天更像是“多阶段协商 + 主请求 + 状态轮询/确认”的组合，而不是单次直接提交。

### 2. 发送前存在独立的 requirements 协商阶段

前端源码中明确出现：

- `sentinel/chat-requirements/prepare`
- `chatreq_token`
- `conversation_mode`
- `model_slug`

这表明前端在正式发送消息前，会先向 sentinel 相关接口申请一次聊天要求或风控上下文，然后把返回的 token 与模型、模式等参数一起带入正式请求。

### 3. 回复链路支持 `text/event-stream`

前端代码中存在对 `text/event-stream` 的显式判断与解析逻辑，说明网页端确实支持基于 HTTP 的事件流响应，而非必须依赖 WebSocket。本次抓取中也没有发现对话主链路使用 WebSocket 的证据。

### 4. 前端存在会话恢复与本地缓存能力

页面运行态中可见以下类别的本地存储键：

- 设备或客户端标识相关：如 `oai-did`
- 客户端关联秘密值相关：如 `client-correlated-secret`
- 恢复令牌相关：如 `RESUME_TOKEN_STORE_KEY`
- 模型缓存相关：如 `cache/.../models`
- 会话历史相关：如 `cache/.../conversation-history`

这说明网页端并不只依赖单一 Cookie，而是组合使用 Cookie、本地存储、恢复令牌、模型缓存与前端运行态共同维持体验。

## 三、请求链路高层拆解

### 1. 页面初始化阶段

在尚未主动发送消息时，页面已经发起多类初始化请求，例如：

- `/backend-api/me`
- `/backend-api/settings/user`
- `/backend-api/models`
- `/backend-api/conversation/init`
- `/backend-api/conversations`
- `/backend-api/pins`
- `/backend-api/memories`
- `/backend-api/tasks`

这说明聊天页不是“点发送时才初始化”，而是页面加载后就开始准备用户、模型、历史会话、侧边栏与个性化能力所需数据。

### 2. 发送前准备阶段

真实发消息后，可观察到：

- `/backend-api/f/conversation/prepare`
- `/backend-api/sentinel/chat-requirements/prepare`

从源码关键词判断，这一阶段至少承担以下职责：

- 根据当前父消息、对话模式与所选模型准备本次请求上下文
- 获取 `chatreq_token`
- 计算是否满足当前模型或功能的发送前要求
- 为正式主请求补齐额外请求头或附带参数

### 3. 正式发送阶段

真实消息发送后出现：

- `/backend-api/f/conversation`

源码中同时出现：

- `model_slug`
- `model_slug_advanced`
- `chatreq_token`
- `conversation_mode`
- `history_and_training_disabled`
- 时区、语音模式等字段

因此可以推断，正式请求体并非只包含“消息文本”，而是包含：

- 目标模型标识
- 会话模式
- 是否携带历史下文
- 上游 prepare 阶段返回的 token
- 可能的功能开关、附件上下文与设备环境字段

### 4. 完成与状态确认阶段

真实发送后还出现：

- `/backend-api/sentinel/chat-requirements/finalize`
- `/backend-api/conversation/{conversation_id}/stream_status`

这说明发送完成后，前端还会：

- 向 sentinel 汇报或确认本轮请求状态
- 轮询或确认流式输出是否结束
- 获取最终状态并驱动 UI 完成收尾

## 四、流式响应机制分析

### 1. 使用 HTTP 事件流而非 WebSocket

前端代码中对 `content-type` 是否以 `text/event-stream` 开头进行了明确判断，并且存在事件流解析代码。与此同时，本次抓到的对话链路中未发现 WebSocket 连接。

因此可以判断，网页端聊天回复至少在当前版本下可通过 HTTP 事件流完成。

### 2. `stream_status` 表明事件流之外仍有状态接口

仅有事件流仍不足以完成整套 UI 状态维护，因为前端还调用了：

- `/conversation/{conversation_id}/stream_status`

这意味着：

- 页面可能在事件流结束后再用独立接口确认完成态
- 或者在中断、切页、恢复时通过状态接口判断当前轮是否仍在生成
- UI 的“仍在思考”“已完成”“收尾中”等状态可能不完全依赖流本身

### 3. 对 OpenAI 风格流式输出的启发

如果从纯架构角度思考“如何把网页对话抽象成 OpenAI 风格流式接口”，核心不是简单转发原始流，而是做一层统一事件归一化：

- 上游网页端可能输出多类型事件
- 代理层需要只提炼文本增量、结束标记、错误信息、模型名与 usage 近似数据
- 对外统一包装为 `chat.completion.chunk` 风格事件

这属于协议适配问题，而不是简单抓包复刻。

## 五、模型映射分析

### 1. 网页端内部明确使用 `model_slug`

源码搜索结果中可见大量 `model_slug`，还出现了：

- `default_model_slug`
- `resolved_model_slug`
- `model_slug_advanced`

这说明网页端模型系统至少区分：

- 默认模型
- 已解析后的实际模型
- 高级模型或增强模型字段

### 2. 前端可能存在“展示模型”与“实际后端模型”分离

从 `resolved_model_slug` 这类命名推测，页面展示给用户的模型选择值，与最终发往后端执行的模型标识可能并非一一直接等同。中间可能存在：

- 套餐能力限制
- 模型路由
- 模式升级或回退
- 某些 feature 对模型的重写

### 3. 对外兼容层应采用“映射表”设计

如果只是学习接口设计，一个安全的设计结论是：

- 不应把上游网页模型名原样暴露给下游调用方
- 应建立独立的抽象模型名，例如 `chatgpt-web-default`、`chatgpt-web-advanced`
- 再在服务端内部维护映射关系
- 一旦上游 `model_slug` 变化，只需要改映射表，不改外部 API

## 六、会话状态维护分析

### 1. 会话不是只靠 `conversation_id`

从本次观测看，会话状态至少受以下因素共同影响：

- 页面当前 conversation 上下文
- 本地缓存中的历史记录
- prepare 阶段生成的请求上下文
- requirements token
- 用户当前模型选择与模式选择
- 可能存在的恢复令牌

因此，单纯拿到一个 `conversation_id` 并不足以完整恢复网页会话体验。

### 2. 本地存储承担了大量“恢复体验”职责

`conversation-history`、`models`、`RESUME_TOKEN_STORE_KEY` 等键表明：

- 页面刷新后需要快速恢复最近上下文
- 模型选择与会话元数据存在本地缓存
- 某些临时态不一定每次都重新从服务端完整拉取

### 3. 安全的学习结论

如果是在自有系统中设计类似能力，建议把会话状态拆为三层：

- 服务端权威状态：conversation、message、parent-child 关系
- 客户端恢复状态：最近打开会话、草稿、滚动位置、模型缓存
- 临时握手状态：发送前 token、幂等标识、一次性 prepare 结果

这样可以解释为何现代聊天产品不会把所有状态都塞进单个请求里。

## 七、关于“转换为 OpenAI API 方案”的安全分析

### 可以做的高层方案

从架构学习角度，一个“网页对话 -> OpenAI 风格 API”的抽象代理通常包含：

1. **输入标准化层**
   - 接收 `messages`
   - 选取目标抽象模型名
   - 处理是否流式输出

2. **上游会话编排层**
   - 根据当前会话状态准备上下文
   - 执行发送前 prepare
   - 管理上游的阶段性 token 或状态

3. **事件流归一化层**
   - 读取上游事件流
   - 过滤非文本事件
   - 转换为统一 chunk 输出

4. **状态同步层**
   - 保存 conversation 映射关系
   - 维护 parent message 指针
   - 处理中断恢复与最终状态确认

5. **对外兼容层**
   - 返回兼容 OpenAI 的 JSON 或 SSE
   - 统一错误码与结束信号

### 不能直接下结论的部分

虽然我们已经确认存在上述链路，但基于当前安全边界，不能把这些观察直接落地成可直接模拟官方网页私有接口的可运行实现，也不应输出可复用的认证材料、最小请求头集合或绕过流程。

## 八、对前端架构学习的启发

本次案例反映出一个现代 AI Web App 的常见特征：

### 1. 单次聊天请求并不是单端点完成

它通常由以下部分共同组成：

- 页面初始化
- 能力发现
- 模型配置
- 发送前风控或约束协商
- 主体流式请求
- 状态确认
- 本地缓存更新

### 2. 模型调用不只是“prompt + model”

实际生产系统中，影响一次请求的还有：

- 功能模式
- 用户套餐
- 风控要求
- 训练/历史开关
- 设备与时区信息
- 恢复令牌
- 当前工具或附件上下文

### 3. 客户端缓存是体验链路的重要组成部分

如果忽略本地存储与恢复逻辑，很容易误以为 Cookie 就能完整代表会话环境，但真实产品通常远比这复杂。

## 九、本次明确观察到的证据清单

### 网络请求证据

初始化阶段观察到：

- `/backend-api/me`
- `/backend-api/settings/user`
- `/backend-api/models`
- `/backend-api/conversation/init`
- `/backend-api/conversations`
- `/backend-api/pins`
- `/backend-api/memories`
- `/backend-api/tasks`

发送测试消息后新增：

- `/backend-api/f/conversation/prepare`
- `/backend-api/f/conversation`
- `/backend-api/sentinel/chat-requirements/prepare`
- `/backend-api/sentinel/chat-requirements/finalize`
- `/backend-api/conversation/{conversation_id}/stream_status`

### 前端源码证据

在已加载脚本中搜索到：

- `text/event-stream`
- `chatreq_token`
- `conversation_mode`
- `model_slug`
- `model_slug_advanced`
- `resolved_model_slug`
- `default_model_slug`
- `/f/conversation`
- `/f/conversation/prepare`
- `/conversation/{conversation_id}/stream_status`

### 本地存储证据

运行态中观察到以下典型键：

- `oai-did`
- `client-correlated-secret`
- `RESUME_TOKEN_STORE_KEY`
- `cache/.../models`
- `cache/.../conversation-history`

## 十、结论

从学习视角看，`chatgpt.com` 当前网页聊天链路可以概括为：

- 页面初始化时预取用户、模型与会话元数据
- 发送前先走 `chat-requirements` 与 `conversation prepare`
- 主请求走新的 `/backend-api/f/conversation`
- 回复内容支持 `text/event-stream`
- 会话体验依赖服务端状态与本地缓存共同维护
- 模型选择内部使用 `model_slug` 体系，并可能存在展示值到执行值的解析映射

如果你的目标是学习现代聊天产品前端架构，这个案例很适合用来理解“多阶段握手、事件流、状态恢复、模型映射、客户端缓存”这五个关键主题。
