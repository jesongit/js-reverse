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

## 九、结论摘要
- Notion 邮箱注册是 OTP 驱动的登录/注册合并链路。
- 自动化核心难点不在接口发现，而在 UI 细节：输入事件、精确按钮点击、多次营销勾选、用途页选中态、旧空间邀请分支。
- 脚本复用时，不应只抓 Cookie，而应使用：
  - Cookie
  - localStorage 空间上下文
  - 初始化请求链路
  三者组合恢复环境。
- 对 Agent 来说，最稳妥的策略是：分步骤推进、关键页停顿确认、每一步都重新验证当前 DOM 状态，而不是依赖上一步的假设。
