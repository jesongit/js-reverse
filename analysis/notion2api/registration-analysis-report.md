# Notion 邮箱注册链路分析报告

## 文档目标
- 面向 Agent 或后续脚本实现者，提供一份可直接执行的 Notion 邮箱注册分析报告。
- 覆盖内容包括：完整注册链路、页面交互方式、输入框与按钮操作要点、关键请求、营销勾选与用途选择的风险点、登录态与 env 提取思路。
- 本报告基于 [README.md](README.md) 的全过程记录收敛而成，重点保留“可执行”和“容易踩坑”的部分。

## 适用范围
- 目标入口：`https://www.notion.so/signup?from=marketing&pathname=%2F`
- 主要路径：邮箱 OTP 注册 → onboarding → 创建工作空间 → 进入主页
- 当前观察环境：简体中文页面、Web 端、Notion 新版 onboarding 流程

---

## 一、总链路概览

### 1. 主链路
1. 打开注册页。
2. 输入邮箱，点击 `继续`。
3. 前端请求：
   - `POST /api/v3/getLoginOptions`
   - `POST /api/v3/sendTemporaryPassword`
4. 页面进入 `验证码` 步骤。
5. 输入验证码，点击 `继续`。
6. 前端请求：`POST /api/v3/loginWithEmail`
7. 进入 onboarding 档案页：填写名字、处理营销勾选。
8. 点击 `继续`，进入“你想如何使用 Notion？”用途页。
9. 选择用途，如 `用于私人生活`。
10. 点击 `继续`，进入后续引导。
11. 遇到 `加入团队或创建工作空间` 时，点击 `创建新工作空间`。
12. 遇到桌面应用引导时，点击 `暂时跳过`。
13. 进入新工作空间主页，注册链路完成。

### 2. 关键接口顺序
- `getLoginOptions`
- `sendTemporaryPassword`
- `loginWithEmail`
- `saveTransactionsMain` / `saveTransactionsFanout`
- `createSpace`
- `getSpacesInitial`
- `syncRecordValuesMain`
- `syncRecordValuesSpaceInitial`
- `getLifecycleUserProfile`
- `getAssetsJsonV2`

### 3. 关键结论
- Notion 邮箱注册本质上是邮箱 OTP 登录/注册合并链路。
- 注册完成后的可用状态，不是单个 token 决定，而是 Cookie + localStorage + 初始化请求共同决定。
- onboarding 里有多个容易误判的 UI 节点，不能只靠“页面跳转了”就当成操作成功。

---

## 二、页面操作规范

## 2.1 输入框如何输入

### 结论
不要直接使用简单赋值 `input.value = ...` 后点击按钮。Notion 输入框对输入事件敏感，属于受控组件风格，错误操作会导致页面提示 `无效的邮件地址`。

### 推荐方式
对输入框应使用更接近真实输入的方式：
1. 调用 `HTMLInputElement.prototype.value` 的原型 setter。
2. 派发 `input` 事件。
3. 派发 `change` 事件。
4. 必要时使用 `InputEvent` 而不是普通 `Event`。

### 推荐伪代码
```js
const input = document.querySelector('input[type="email"]');
const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
setter.call(input, email);
input.dispatchEvent(new InputEvent('input', { bubbles: true, data: email, inputType: 'insertText' }));
input.dispatchEvent(new Event('change', { bubbles: true }));
```

### 适用对象
- 邮箱输入框
- 验证码输入框
- 名字输入框

### 注意事项
- 如果只是设置 DOM 值但页面不响应，优先怀疑输入事件链不完整。
- 不要第一时间怀疑邮箱格式错误。

---

## 2.2 按钮如何点击

### 结论
按钮不要只靠页面文本全局模糊匹配，因为容器节点常常也带有整块文本，容易点错外层元素。

### 推荐方式
1. 优先匹配 `role="button"` 或真实 `button`。
2. 尽量按“文本完全匹配”或“文本前缀匹配”找最小按钮节点。
3. 使用 `MouseEvent('click')` 模拟点击。

### 推荐伪代码
```js
const btn = Array.from(document.querySelectorAll('[role="button"],button'))
  .find(el => (el.innerText || '').trim() === '继续');
btn.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true, view: window }));
```

### 特别说明
`创建新工作空间` 必须精确点击按钮本身，不要点外层卡片容器。

---

## 2.3 选项如何选择

### 用途页：`工作` / `用于私人生活` / `适用于学校`

#### 结论
这个页面的选中态不稳定，不一定暴露 `aria-pressed`、`aria-checked` 或 className 变化。

#### 正确策略
1. 先定位到精确按钮节点。
2. 点击目标选项，例如 `用于私人生活`。
3. 点击后停留页面，不要立刻继续。
4. 如果需要严格流程控制，由用户确认后再点 `继续`。

#### 风险点
- 页面可能不提供稳定 DOM 选中证据。
- 因此“已点击正确按钮”与“已证明选中态”要分开表达。
- 不应在没有证据时声称选中成功。

### 营销勾选框

#### 结论
`我同意接收 Notion 的推广信息` 不是只出现一次。

#### 已观察到的情况
- 会在档案页出现，默认勾选。
- 某些路径下，在用途页还会再次出现，且可能重新变为默认勾选。
- 也存在某些路径下，用途页不出现该勾选框。

#### 正确策略
每到一个新步骤都重新检查：
1. 是否存在 `input[type="checkbox"]`
2. 当前 `checked` 是否为 `true`
3. 若为 `true`，先取消勾选再继续

#### 推荐伪代码
```js
const checkbox = document.querySelector('input[type="checkbox"]');
if (checkbox && checkbox.checked) {
  checkbox.checked = false;
  checkbox.dispatchEvent(new Event('input', { bubbles: true }));
  checkbox.dispatchEvent(new Event('change', { bubbles: true }));
}
```

### 名字输入
- 优先用邮箱前缀。
- 如果无法继续，可能是名字冲突或前端校验问题。
- 此时应改用随机用户名，不要卡死在固定名字上。

---

## 三、关键页面与动作表

| 阶段 | 页面标志 | 必做动作 | 风险点 |
|---|---|---|---|
| 注册首页 | `工作邮件`、`继续` | 输入邮箱并点击继续 | 简单赋值可能无效 |
| OTP 页 | `验证码`、`输入验证码` | 输入验证码并点击继续 | 页面 URL 可能仍是 login |
| 档案页 | `自定义你的档案` | 填名字，取消营销勾选 | 名字可能冲突导致无法继续 |
| 用途页 | `你想如何使用 Notion？` | 选 `用于私人生活` | 选中态不一定有 DOM 标记 |
| 团队/空间页 | `加入团队或创建工作空间` | 点 `创建新工作空间` | 容易误加入旧空间 |
| 桌面应用引导 | `Notion 桌面应用的速度快 50%` | 点 `暂时跳过` | 否则流程分支转桌面端 |
| 主页 | `欢迎来到 Notion！` 等 | 可视为流程完成 | 页面后续可能回登录页 |

---

## 四、关键请求说明

## 4.1 注册与登录阶段

### `POST /api/v3/getLoginOptions`
- 作用：根据邮箱判断登录选项、账号状态或后续挑战条件。
- 阶段：输入邮箱后立即出现。
- 重要性：高。

### `POST /api/v3/sendTemporaryPassword`
- 作用：触发邮箱 OTP 发送。
- 阶段：输入邮箱并点击继续后。
- 重要性：高。
- 注意：请求出现不等于验证码一定成功送达。

### `POST /api/v3/loginWithEmail`
- 作用：提交邮箱与验证码，建立登录态。
- 阶段：输入 OTP 后点击继续。
- 重要性：高。

## 4.2 onboarding 与建空间阶段

### `POST /api/v3/saveTransactionsMain`
- 作用：保存 onboarding 或空间配置类变更。
- 阶段：档案页、用途页、创建空间过程中反复出现。

### `POST /api/v3/saveTransactionsFanout`
- 作用：事务扇出同步。
- 阶段：空间创建与主页初始化时出现。

### `POST /api/v3/createSpace`
- 作用：创建新工作空间。
- 阶段：选择 `创建新工作空间` 之后。

### `POST /api/v3/getJoinableSpaces`
- 抓包现状：当前账号在 onboarding 首屏已真实抓到。
- 已确认请求：`{ "excludeUnactionableSpaces": false }`
- 已确认响应字段：
  - `results[].id / name / joinabilityStatus / spaceIcon / guestPageIds / totalMemberCount`
  - `results[].createdBy`
  - `results[].topMembersInfo`
  - `results[].subscriptionTier`
- 开发价值：
  - 可直接枚举当前账号可加入空间。
  - `subscriptionTier` 已在这里出现，可作为轻量级订阅层级线索。
  - 做多空间选择、空间探活、候选空间调度时非常有用。

### `POST /api/v3/isUserDomainJoinable`
- 抓包现状：onboarding 首屏已真实抓到。
- 当前响应：`{"isJoinable": true}`
- 开发价值：
  - 判断当前邮箱域名是否可以直接加入某个组织或工作空间体系。
  - 可能影响组织邀请、自动加入和企业套餐入口显示。

### `POST /api/v3/validateUserCanCreateWorkspace`
- 抓包现状：onboarding 首屏已真实抓到。
- 当前响应：`{"canUserCreateSpace": true}`
- 开发价值：
  - 判断账号是否允许新建空间。
  - 可能受风控、地域、邮箱类型、组织策略限制。

### `POST /api/v3/isEmailEducation`
- 抓包现状：onboarding 首屏已真实抓到。
- 当前响应：`{"isEligible": false}`
- 开发价值：
  - 判断教育邮箱资格。
  - 可能影响教育套餐、学生权益与价格实验。

### `POST /api/v3/getGeoIpLocation`
- 抓包现状：onboarding 首屏已真实抓到。
- 已确认响应字段：
  - `countryCodeFromIp`
  - `metroCodeFromIp`
  - `subdivision1ISOCodeFromIp`
  - `subdivision2ISOCodeFromIp`
  - `cityFromIp`
  - `continentCodeFromIp`
  - `timeZone`
- 开发价值：
  - 地域与时区是价格、支付、合规、功能暴露的重要前置条件。
  - 对解释为什么不同 IP/代理环境下套餐入口不同非常关键。

### `POST /api/v3/checkEmailEligibilityForConnectedAppProducts`
- 抓包现状：onboarding 首屏已真实抓到。
- 已确认请求：`{ "email": "..." }`
- 当前响应：`{"eligibleForCalendar": false}`
- 开发价值：
  - 说明 Notion 会单独判断邮箱是否可用于 Connected App Products。
  - 后续可继续观察是否还有 `eligibleForMail`、`eligibleForDrive` 等类似字段。

### `POST /api/v3/getVerifiedEmailDomain`
- 抓包现状：onboarding 首屏已真实抓到。
- 当前响应：`{}`
- 开发价值：
  - 可能用于企业域验证、自动加入组织、商务套餐引导。
  - 需要在企业域邮箱或已验证域账号上继续补抓。

### `POST /api/v3/getDesktopAppRegistration`
- 作用：桌面应用引导相关。
- 阶段：用途页之后。

## 4.3 主页初始化阶段

### 主数据装载
- `getSpacesInitial`
- `syncRecordValuesMain`
- `syncRecordValuesSpaceInitial`
- `getLifecycleUserProfile`
- `getAssetsJsonV2`

### 增强数据
- `getUserNotificationsInitial`
- `getUserSharedPagesInSpace`
- `getSidebarSections`
- `getUserHomePages`
- `getLibraryPage`
- `getTasks`
- `getVisibleUsers`
- `getTeamsV2`
- `getBillingSubscriptionBannerData`
- `getSubscriptionData`

---

## 五、Agent 执行建议

## 5.1 推荐执行顺序
1. 打开注册页。
2. 用原型 setter + input/change 输入邮箱。
3. 精确点 `继续`。
4. 等用户提供验证码。
5. OTP 页输入验证码并提交。
6. 档案页：
   - 名字先用邮箱前缀
   - 若无法继续则随机名
   - 检查并取消营销勾选
7. 用途页：
   - 精确点击 `用于私人生活`
   - 停下等待用户确认
8. 继续后若看到 `加入团队或创建工作空间`：
   - 必须点 `创建新工作空间`
9. 若看到桌面应用引导：
   - 点 `暂时跳过`
10. 进入主页后抓 Cookie + localStorage + 初始化请求。

## 5.2 Agent 应避免的错误
- 不要把“页面跳转了”当成“上一步一定成功”。
- 不要默认营销勾选只出现一次。
- 不要默认用途页一定暴露选中属性。
- 不要只靠 Cookie 判断 env 足够。
- 不要在已有邀请工作空间时默认加入旧空间。
- 不要把容器节点当成按钮点击目标。

## 5.3 Agent 的停点建议
以下步骤适合停下来等用户确认：
1. 营销勾选取消后。
2. 用途页点中 `用于私人生活` 后。
3. 创建新工作空间前。
4. 桌面应用页准备点 `暂时跳过` 前。

---

## 六、可复用 env 提取建议

## 6.1 一级关键字段
- `notion_user_id`
- `notion_users`
- `csrf`

## 6.2 二级空间上下文
- `spaceId`
- `spaceViewId`
- `lastVisitedRoute`
- `spaceName`

## 6.3 三级辅助字段
- `notion_browser_id`
- `notion_locale`
- `analytics_session`
- sidebar 相关缓存

## 6.4 来源分层
### Cookie
- `notion_user_id`
- `notion_users`
- `csrf`
- `notion_browser_id`
- `notion_locale`

### localStorage
- `spaceIdToShortId`
- `lastVisitedRoute*`
- `notion-sidebar-sidebar-state-*`
- `analytics_session`
- `contextualizedOnboardingStateKeyV2`

### 初始化接口
- `getSpacesInitial`
- `syncRecordValuesMain`
- `syncRecordValuesSpaceInitial`
- `getLifecycleUserProfile`

## 6.5 最小可用 env 结论
真正最小可用 env 不是单字段，而是：
- 身份 Cookie
- 空间上下文 localStorage
- 初始化请求三件套

如果缺少其中一块，容易出现：
- 重新落回登录页
- 进入错误空间
- 侧栏状态异常
- 页面上下文恢复不完整

---

## 七、阻塞与特殊情况

### 1. 名字冲突
现象：档案页点击 `继续` 无反应或停滞。
处理：改用随机用户名。

### 2. 已有旧空间邀请
现象：出现 `加入团队或创建工作空间`，且列表里有旧空间。
处理：明确点击 `创建新工作空间`。

### 3. 页面跳回登录页
现象：明明已进主页，后续又看到 login。
结论：不能仅凭当前页面判断会话是否完全丢失，应同步检查 Cookie 和 localStorage。

### 4. 用途页无稳定选中态
现象：点击 `用于私人生活` 后 DOM 无明显变化。
处理：记录“已命中正确节点并执行点击”，然后让用户决定是否继续。

### 5. 当前页面脚本受限
现象：源码搜索、脚本枚举或运行态读取受 Trusted Types 限制。
处理：切换到脚本可枚举页面，或优先用网络与存储证据替代源码证据。

---

## 八、最简执行模板

```text
1. 打开 signup 页面
2. 用 setter + input/change 输入邮箱
3. 精确点击 继续
4. 等验证码
5. 输入验证码并提交
6. 档案页：名字=邮箱前缀；若失败则随机名；取消营销勾选
7. 点击继续
8. 用途页：点击 用于私人生活；停下等确认
9. 点击继续
10. 若出现 创建新工作空间，则点击它
11. 若出现 暂时跳过，则点击它
12. 进入主页后抓 Cookie + localStorage + 初始化请求
```

---

## 九、AI 对话与账号相关接口扩展分析

## 9.1 对话主接口：`POST /api/v3/runInferenceTranscript`
- 作用：Notion AI 对话主入口，发送 transcript 并返回 `application/x-ndjson` 流。
- 当前项目用途：`main.py` 的 `/v1/chat/completions` 最终都映射到该接口。
- 关键请求头：
  - `accept: application/x-ndjson`
  - `content-type: application/json; charset=utf-8`
  - `cookie: token_v2 / p_sync_session / notion_user_id / csrf / device_id / notion_browser_id`
  - `x-notion-active-user-header`
  - `x-notion-space-id`
  - `notion-client-version`
  - `referer: https://www.notion.so/ai`
- 关键请求体结构：
  - `spaceId`
  - `threadId`
  - `threadParentPointer`
  - `threadType`
  - `transcript[]`
  - `createThread`
  - `debugOverrides`
- 关键 transcript 节点：
  - `type=config`：模型、线程模式、是否 web search、是否只读等 AI 行为配置
  - `type=context`：`userId`、`spaceId`、`spaceViewId`、timezone、surface
  - `type=user`：用户消息正文
- 响应格式观察：
  - `record-map`：标准 workflow patch 流，最终答案位于 `thread_message.*.value.value.step`
  - `markdown-chat`：Gemini 系列更常见，正文位于 `data.markdown`
- 当前优化结论：必须按 NDJSON 逐行读取并增量转发，不能等完整响应回包后再手工切块，否则只是伪流式。

## 9.2 模型与线程类型关系
- `notion-ai`：不显式传模型，走 Notion 默认模型。
- `gpt-5.2 -> oatmeal-cookie`
- `gpt-5.4 -> oatmeal-cake`
- `sonnet-4.6 -> almond-croissant-high`
- `opus-4.7 -> avocado-froyo-high`
- `gemini-3.1-pro -> galette-medium-thinking`
- `gemini-2.5-pro -> gemini-pro`
- `gemini-2.5-flash -> gemini-flash`
- 额外结论：Gemini 系列需要 `threadType=markdown-chat`，其余当前观察值主要仍是 `workflow`。

## 9.3 流式响应还原建议
- Notion 返回的单行事件并不一定都是“新增 token”，很多时候是“当前完整文本快照”。
- 转 OpenAI SSE 时应：
  1. 逐行解析 NDJSON。
  2. 提取当前完整文本。
  3. 与上次已发送文本做前缀比对。
  4. 只把新增 delta 继续向下游发送。
- 如果遇到文本回退或非前缀更新，优先记录为异常分支，不要继续按固定字符数切块伪造流式。

## 9.4 usage 差量验证结论
- 验证方式：在 `https://www.notion.so/ai` 发送一次真实对话，请求内容为“请只回复数字 1”，页面实际返回 `1`，并确认对应 `runInferenceTranscript` 已成功完成。
- 验证前后重点回看：
  - `POST /api/v3/getAIUsageEligibility`
  - `POST /api/v3/getAIUsageEligibilityV2`
- 当前样本空间：`dc3b731b-7345-811e-bd2e-0003792c58d5`
- 当前观察结果：
  - `getAIUsageEligibility` 仍为 `spaceUsage=0`、`userUsage=0`
  - `getAIUsageEligibilityV2.usage.currentServicePeriod.spaceUsage=0`
  - `getAIUsageEligibilityV2.usage.currentServicePeriod.userUsage=0`
  - `getAIUsageEligibilityV2.usage.lifetime.spaceUsage=0`
  - `getAIUsageEligibilityV2.usage.lifetime.userUsage=0`
  - `totalCreditBalance=0`
  - `creditsInOverage=0`
- 结论：至少在当前免费空间样本下，单次真实 AI 对话后，这两组 usage 接口不会立即同步反映本次调用消耗。
- 开发含义：如果后续要做“剩余额度 / 调用次数”展示，不应假设对话完成后接口会立刻递增；需要预留延迟刷新、异步结算或累计多次后再校验的判断。

## 9.5 账号、订阅、额度相关接口线索
以下内容已经结合 AI 页面真实抓包与前端源码交叉验证。

### `POST /api/v3/getAppConfig`
- 抓包现状：AI 首页已真实抓到完整请求与响应。
- 作用：初始化全局配置、实验开关、设备画像与 Statsig 用户信息。
- 已确认字段：
  - `statsigUser.userID`
  - `statsigUser.custom.locale / country / clientVersion / browserName / os / platform`
  - `statsigUser.custom.userSignupTime / domainType / browserId / stableID / deviceId`
  - `initialValues.feature_gates.*`
- 开发价值：
  - 判断功能是否被实验开关控制。
  - 判断账号是否已进入某些 AI、计费或 onboarding 实验。
  - 可作为“为什么同账号不同空间行为不同”的解释层。

### `POST /api/v3/getSpacesInitial`
- 抓包现状：AI 首页已真实抓到完整响应。
- 作用：初始化用户与空间基础数据。
- 已确认字段：
  - `users.<userId>.notion_user.<userId>.value.value.email`
  - `users.<userId>.user_settings.<userId>.value.value.settings.domain_type`
  - `signup_time`
  - `preferred_locale`
  - `time_zone`
  - `used_desktop_web_app`
- 开发价值：
  - 获取账号邮箱、时区、locale、注册时间。
  - 作为 `/v1/account` 的基础账号信息来源之一。

### `POST /api/v3/syncRecordValuesMain`
- 抓包现状：AI 首页已真实抓到请求与响应。
- 当前请求内容：首屏会请求 `notion_user / user_settings / user_root` 三类记录。
- 开发价值：
  - 与 `getSpacesInitial` 类似，但更接近通用 record-map 拉取接口。
  - 后续很多账号、偏好、页面对象都可能继续走这个通道。

### `POST /api/v3/syncRecordValuesSpaceInitial`
- 抓包现状：AI 首页已真实抓到请求与响应。
- 当前请求内容：已观察到请求 `block` 记录。
- 开发价值：
  - 适合补空间级页面、块级上下文。
  - 若 AI 首页或 Billing 页挂在某个 block/页面上，这里可能给出首屏依赖对象。

### `POST /api/v3/getUserAnalyticsSettings`
- 抓包现状：AI 首页已真实抓到完整响应。
- 已确认字段：
  - `user_id`
  - `hashed_user_id`
  - `user_email`
  - `isIntercomEnabled / isZendeskEnabled / isLoggingEnabled / isAmplitudeEnabled / isSprigEnabled`
  - `endpoint: etClient`
- 开发价值：
  - 可判断账号当前启用了哪些客服、埋点与反馈系统。
  - 对排查“同样请求为何账号行为不同”有辅助价值。

### `POST /api/v3/getLifecycleUserProfile`
- 抓包现状：AI 首页已真实抓到，但当前账号响应为 `{"success":true,"userProfile":{}}`。
- 结论：接口真实存在，但字段是否为空取决于账号生命周期阶段或后台画像是否命中。
- 开发价值：
  - 后续仍值得在老账号、付费账号、触发更多页面后继续比对。

### `POST /api/v3/getDesktopAppRegistration`
- 抓包现状：AI 首页已真实抓到完整响应。
- 已确认字段：
  - `isRegistered`
  - `isRegistered30Day`
- 开发价值：
  - 判断账号是否完成桌面端注册/绑定。
  - 可作为 onboarding 或桌面应用引导分支判断依据。

### `POST /api/v3/etClient`
- 抓包现状：AI 首页已真实抓到。
- 作用：前端埋点聚合上报。
- 已确认内容：
  - `visit`、`statsig_config_file_fetch` 等事件
  - 事件中包含 `route_name=ai`、`user_id`、`user_email`、`signup_time`、`preferred_locale`、窗口尺寸、网络质量、`experiments` 等
- 开发价值：
  - 不适合作为业务接口直接依赖，但可反推哪些页面动作、实验和用户状态会影响 AI 入口行为。

### `POST /api/v3/getSubscriptionData`
- 抓包现状：已在进入真实工作空间后抓到完整响应。
- 已确认调用关系：前端会并行请求
  - `getSubscriptionData`
  - `getVisibleUsers`
  - `getSimilarUsers`
  三者组合成订阅数据 store，并缓存到 `SubscriptionData:<spaceId>:v2`。
- 当前实测响应字段：
  - `type: unsubscribed_member`
  - `blockUsage: 34`
  - `hasPaidNonzero: false`
  - `subscriptionTier: free`
  - `accountBalance: 0`
  - `addOns: []`
  - `users / members / joinedMemberIds / spaceUsers`
- 开发价值：
  - 可直接判断套餐层级、是否付费过、账户余额、块使用量。
  - 是空间订阅概况与 AI 权益推导的核心接口之一。

### `POST /api/v3/getVisibleUsers`
- 源码现状：作为 `getSubscriptionData` 并行请求的一部分已确认存在。
- 当前请求特征：`supportsEdgeCache=true`、`earlyReturnForEdgeCache=true`。
- 开发价值：
  - 可用于空间成员可见性、缓存命中策略分析。
  - 说明订阅/权益展示并不只依赖单个订阅接口。

### `POST /api/v3/getSimilarUsers`
- 源码现状：作为 `getSubscriptionData` 并行请求的一部分已确认存在。
- 当前请求特征：`{ userId, spaceId, limit: 100 }`。
- 开发价值：
  - 可能用于推荐、协作提示或订阅相关 UI。
  - 同样会并入订阅数据 store。

### `POST /api/v3/getBillingSubscriptionBannerData`
- 抓包现状：已在进入真实工作空间后抓到完整响应。
- 当前请求：`{ "spaceId": "..." }`
- 当前响应：`{ "bannerData": {} }`
- 结论：接口真实存在，但当前免费空间没有需要展示的 Billing banner。
- 开发价值：
  - 有 banner 时，适合承载升级、欠费、到期、试用提醒等展示数据。
  - 需要在付费、欠费或接近额度上限的空间继续补抓。

### `POST /api/v3/getSubscriptionEntitlements`
- 抓包现状：已在进入真实工作空间后抓到完整响应。
- 当前请求：`{ "spaceId": "..." }`
- 当前响应：`{ "editsBlocked": false }`
- 开发价值：
  - 可判断空间是否被订阅/计费状态限制编辑。
  - 对落地 `/v1/billing` 或 `/v1/account/status` 很有帮助。

### `POST /api/v3/getAIUsageEligibility`
- 抓包现状：已在进入真实工作空间后抓到完整响应。
- 当前响应字段：
  - `isEligible: true`
  - `type: spaceAllowance`
  - `spaceUsage: 0`
  - `spaceLimit: 150`
  - `userUsage: 0`
  - `userLimit: 75`
  - `userPromotionalUsage: 0`
  - `userPromotionalLimit: 0`
  - `researchModeUsage: 0`
- 开发价值：
  - 适合做轻量级“当前是否还能继续用 AI”判断。
  - 字段短平快，适合代理层快速暴露。

### `POST /api/v3/getAIUsageEligibilityV2`
- 抓包现状：已在进入真实工作空间后抓到完整响应。
- 当前响应字段：
  - `usage.currentServicePeriod.spaceUsage / userUsage`
  - `usage.lifetime.spaceUsage / userUsage / userPromotionalUsage`
  - `usage.totalCreditBalance`
  - `usage.creditsInOverage`
  - `limits.purchased.totalLimit`
  - `limits.free.spaceLimit / userLimit / userPromotionalLimit`
  - `basicCredits.*`
  - `premiumCredits.totalCreditBalance / creditsInOverage / overageLimit / perSource.*`
- 当前实测值：
  - `totalCreditBalance=0`
  - `creditsInOverage=0`
  - `free.spaceLimit=150`
  - `free.userLimit=75`
- 开发价值：
  - 这是当前最适合做“剩余额度 / 上限 / 已使用量 / overage”统一建模的接口。
  - 若要做 `/v1/usage`，应优先以它为主数据源。

### `POST /api/v3/getSpaceBlockUsage`
- 抓包现状：已在进入真实工作空间后抓到完整响应。
- 当前响应：`{ "blockUsage": 34 }`
- 开发价值：
  - 可作为空间内容体量或免费空间限制的辅助指标。

### `POST /api/v3/getTranscriptionUsage`
- 抓包现状：已在进入真实工作空间后抓到完整响应。
- 当前响应字段：
  - `type: eligibility`
  - `usage: 0`
  - `unit: seconds`
  - `eligibility: available`
  - `limit: 7200`
- 开发价值：
  - 说明 Notion 对 AI 速记/转录有独立额度体系。
  - 后续若做会议/速记代理，应单独暴露这套 usage。

### `POST /api/v3/getSubscriptionBanner`
- 抓包现状：已在进入真实工作空间后抓到完整响应。
- 当前响应：`{ "bannerIds": [], "dependencies": [...], "recordMap": {"__version__":3} }`
- 开发价值：
  - 适合判断空间当前是否存在订阅提示 banner。
  - 当前免费空间没有 banner，不代表接口无效。

### `POST /api/v3/getTeamsV2`
- 源码现状：已在多个 Sidebar/团队相关脚本中确认真实调用。
- 已确认请求参数线索：
  - `spaceId`
  - `teamTypes`
  - `teamIds`
- 开发价值：
  - 获取团队列表、团队类型与空间归属。
  - 做多空间调度时应纳入账号模型。

### `POST /api/v3/getUserHomePages`
- 源码现状：已在首页与 postRender 逻辑中确认真实调用。
- 已确认请求参数线索：
  - `spaceViewId`
  - `spaceId`
- 开发价值：
  - 获取首页页签、home page 布局与默认落地内容。
  - 可辅助识别新账号、空账号与已使用账号的差异。

### 计费 banner 相关链路
- 已确认前端存在 `billing_subscription_status` 内容键和 `BillingSubscriptionBanner` 展示逻辑。
- 但目前尚未直接抓到或搜到显式 `getBillingSubscriptionBannerData` 字面量。
- 暂时结论：
  - 该能力真实存在。
  - 数据源可能被统一 banner store、订阅 store 或延迟加载模块封装。
  - 需要在 Billing 页面或触发升级/额度告警场景时继续抓。

以下接口已经在主页初始化阶段观察到，适合后续继续重点抓包与抽象：

### `POST /api/v3/getSubscriptionData`
- 作用猜测：返回当前空间或账号的订阅方案、套餐状态、权益边界。
- 可用于：判断当前账号是否可用 AI、高级模型是否可选、套餐是否到期。
- 后续重点：确认响应中是否包含 AI 使用次数、套餐周期、试用状态、续费标记。

### `POST /api/v3/getBillingSubscriptionBannerData`
- 作用猜测：返回顶部或侧栏计费 banner 所需数据。
- 可用于：识别剩余额度告警、试用提醒、升级引导文案。
- 后续重点：确认是否能从中直接提取“剩余 credits / 已使用次数 / 重置时间”类字段。

### `POST /api/v3/getLifecycleUserProfile`
- 作用：拉取生命周期与用户画像类信息。
- 可用于：补账号基础信息、用户状态、生命周期阶段、实验分桶信息。
- 后续重点：确认是否含邮箱验证状态、AI 资格、地区、风控标签。

### `POST /api/v3/getTeamsV2`
- 作用：返回团队、空间、成员视图相关信息。
- 可用于：枚举账号下的空间列表，识别默认空间与团队归属。
- 后续重点：结合 `spaceId` 判断额度是按用户还是按空间结算。

### `POST /api/v3/getUserHomePages`
- 作用：返回首页入口页、最近页面、主页布局。
- 可用于：恢复默认落地页与空间上下文。
- 后续重点：辅助判断某账号是否首次进入、是否仍处于 onboarding 后半段。

## 9.5 获取剩余额度、调用次数、账号信息的建议抓包路径
1. 使用已登录且可正常打开 AI 页的账号。
2. 先打开 `https://www.notion.so/ai`。
3. 记录首屏初始化请求，重点关注：
   - `getSubscriptionData`
   - `getBillingSubscriptionBannerData`
   - `getLifecycleUserProfile`
   - `getTeamsV2`
4. 分别执行以下动作再观察差量请求：
   - 打开模型选择器
   - 发送一次 AI 对话
   - 切换工作空间
   - 打开设置里的 Billing / Plans / AI 相关页面
5. 若页面出现“剩余次数不足”“升级套餐”“试用结束”等文案，回看对应 XHR 发起栈，优先锁定真正提供额度字段的接口。

## 9.6 后续开发落地方向
- 若目标是做 `/v1/account`：优先聚合 `getLifecycleUserProfile + getTeamsV2`。
- 若目标是做 `/v1/billing`：优先聚合 `getSubscriptionData + getBillingSubscriptionBannerData`。
- 若目标是做 `/v1/usage`：先从 AI 对话响应 usage 与订阅接口联合推导，再决定是否需要单独抓额外统计接口。
- 若目标是做多空间多账号调度：必须把“用户维度信息”和“空间维度订阅信息”分开建模。

## 十、结论摘要
- Notion 邮箱注册是 OTP 驱动的登录/注册合并链路。
- 自动化核心难点不在接口发现，而在 UI 细节：输入事件、精确按钮点击、多次营销勾选、用途页选中态、旧空间邀请分支。
- 脚本复用时，不应只抓 Cookie，而应使用：
  - Cookie
  - localStorage 空间上下文
  - 初始化请求链路
  三者组合恢复环境。
- 对 Agent 来说，最稳妥的策略是：分步骤推进、关键页停顿确认、每一步都重新验证当前 DOM 状态，而不是依赖上一步的假设。
