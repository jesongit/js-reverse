# notion2api worklog

- 时间：2026-04-17
  - 阶段：注册流程接入准备
  - 发现或问题：用户要求在 `projects/notion2api` 中新增 Notion 邮箱注册自动化；现有目录仅覆盖 Notion AI 代理，还没有注册流程脚本；邮箱验证码可复用 `utils/qq_mail/qq_mail_idle.py`，但当前脚本只提供监听类，没有面向 Notion 验证码的现成封装。
  - 结论：先用 js-reverse 抓取 `https://www.notion.so/signup?from=marketing&pathname=%2F` 的真实注册请求链路，再按链路补最小化自动注册实现；同时补一个从 QQ IMAP 拉取并校验目标邮箱的验证码读取函数。
  - 下一步：打开注册页，抓关键请求、表单字段、验证码接口与必要请求头。

- 时间：2026-04-18
  - 阶段：auto_register.py 改为 Playwright 多账号方案
  - 发现或问题：纯 requests/cloudscraper 虽可通过 Cloudflare 基础校验，但实测 `getLoginOptions` 仍被 Notion 服务端拦截并返回 `Login is not allowed`；lza6/notion-2api 仅适用于已有 token_v2 的 AI 请求代理，不覆盖注册链路；用户明确有多账号需求，单一 `.env` 覆盖模式不够用；首次实测 Playwright 注册时，点击继续后 OTP 邮件未在 90 秒内到达，需在点击后增加页面稳定等待，避免邮件发送动作尚未真正落库就开始 IMAP 轮询。
  - 结论：放弃纯 HTTP 注册方案，改用 Playwright 驱动真实浏览器页面；新增 `accounts/<account_id>/state.json|env.json|meta.json` 多账号持久化结构；`auto_register.py` 改为 `register/refresh/export/list` 四个子命令；项目根 `.env` 仅作为当前激活账号导出结果，继续兼容 `main.py` 与 `cli.py`；在点击继续后补 5 秒等待再查邮箱；同时把 IMAP 的 `sent_after` 向前放宽 5 秒，避免服务端发送时间与本地记录时间存在轻微偏差导致漏取最新验证码。
  - 下一步：再次完整验证注册链路，补齐 `spaceId` / `spaceViewId` 提取，确认 OTP、onboarding 与 env 导出全部打通。

- 时间：2026-04-18
  - 阶段：补齐无头运行支持与继续排查空间信息提取
  - 发现或问题：Linux 服务器环境更适合 headless 模式，当前 `register` / `refresh` 需要显式支持 `--headless`；已实测 `refresh --account posase1776444745 --export` 可成功刷新凭证，但 `NOTION_SPACE_ID` 与 `NOTION_SPACE_VIEW_ID` 仍为空，说明仅靠当前 Cookie、localStorage 与 `getSpacesInitial` 提取逻辑还不稳定。
  - 结论：先补齐 `--headless` 参数和调用链，保证脚本可在 Linux 无头环境直接运行；空间信息继续沿真实页面初始化数据与运行态上下文两条路径排查，不再回退到纯 HTTP 猜测方案。
  - 下一步：执行一次无头 `refresh` 验证，并继续补强 `spaceId` / `spaceViewId` 提取来源。

- 时间：2026-04-18
  - 阶段：增强空间信息提取扫描范围
  - 发现或问题：无头 `refresh --account posase1776444745 --export --headless` 已验证可运行，增强后的递归扫描已成功补出 `NOTION_SPACE_ID=dc3b731b-7345-811e-bd2e-0003792c58d5`，但 `NOTION_SPACE_VIEW_ID` 仍为空；进一步排查发现根因不是字段名猜错，而是该账号刷新时仍落在 `/onboarding`，尚未走到会把 `space_view_id` 写入 localStorage 和 `user_root.space_views` 的后续页面。
  - 结论：`refresh` 不能只打开首页提取 env，必须顺手补完残留 onboarding 分支，包括名字页、创建新工作空间、用途页、邀请成员页、方案页和桌面应用跳过页；在流程完成后，`loadUserContent` / `getSpacesInitial` 才能稳定返回 `space_view` 与 `user_root.space_views`。
  - 下一步：把 `refresh` 补成自动推进 onboarding 后再次验证 `space_view_id`。

- 时间：2026-04-18
  - 阶段：无头 register 全链路回归验证
  - 发现或问题：首次执行 `register --export --headless` 失败在注册首页首个“继续”按钮，报错 `继续按钮点击失败: {'ok': False, 'found': False}`；说明无头模式下注册页首屏按钮文本或节点结构与已登录后的 onboarding 页面并不完全一致，原先的精确文本匹配不够稳。补上英文按钮别名与英文 onboarding 文案兼容后，首屏点击已通过，但第二次重跑又卡在 `sendTemporaryPassword` 之后的 OTP 邮件等待超时，说明无头注册在邮件发送阶段仍存在不稳定性。继续抓真实请求后，先确认一个关键根因：原始 headless 指纹下 `POST /api/v3/getLoginOptions` 直接返回 `400 UserValidationError`，`debugMessage` 为 `Login is not allowed.`，前端同时上报埋点 `login_invalid_email_submitted`；页面文案表现为 `There was a problem logging in.`。随后在 Playwright 中补 `--disable-blink-features=AutomationControlled`、覆盖 `user_agent`、隐藏 `navigator.webdriver`、伪装 `navigator.plugins/languages` 后，再次抓包已确认 `getLoginOptions` 与 `sendTemporaryPassword` 都返回 `200`，页面也成功进入“验证码”步骤；另外单独用同样指纹跑邮箱侧校验，已确认 QQ IMAP 能在约 1 秒内收到 `Your Notion signup code`，证明邮件通路本身正常。最终把 OTP 等待窗口从 90 秒放宽到 120 秒、点击继续后的稳定等待从 5 秒放宽到 8 秒后，`register --export --headless` 已成功完成到账号落盘与 `.env` 导出。进一步实测发现：首次注册导出的 `NOTION_SPACE_VIEW_ID` 仍可能为空，但紧接着对同账号执行一次无头 `refresh` 可以稳定补齐，因此已把 `register` 末尾改为自动调用一次同账号 `refresh`。在此基础上，又把 headless 浏览器启动、上下文创建、页面注入和 onboarding 推进逻辑收敛为共享函数，避免 `register` 与 `refresh` 两套实现继续分叉。
  - 结论：当前无头注册与刷新不但已跑通，而且关键流程已集中到共享逻辑，后续维护成本更低。
  - 下一步：回归验证收敛后的 `refresh --headless` 仍然正常。

- 时间：2026-04-18
  - 阶段：文档职责拆分
  - 发现或问题：随着排障、抓包、风控、实现演进持续追加，`README.md` 已同时承担稳定说明与工作过程记录两类职责，阅读入口和维护边界越来越模糊。
  - 结论：把过程性内容迁移到 `WORKLOG.md`，保留 README 作为稳定说明入口；后续关键节点即时记录写入 `WORKLOG.md`，若变更影响使用方式、安装步骤、命令示例、目录结构、接口或最终行为，再同步更新 README。
  - 下一步：按新职责重构 `README.md`，并在文档中明确 `WORKLOG.md` 的位置和用途。

- 时间：2026-04-18
- 阶段：git 历史敏感信息复核
- 发现或问题：检查 `git log` 后确认账号目录 `projects/notion2api/accounts/` 未进入历史提交，但旧提交 `616d6c7` 的 `utils/qq_mail/qq_mail_idle.py` 中存在真实 QQ 邮箱账号与授权码硬编码，需重写历史清除。
- 结论：需要对包含该文件的历史提交做重写，并在完成后强制推送远端。
- 下一步：执行历史重写，随后再次扫描确认敏感字符串已从全部提交中移除。

- 时间：2026-04-18
  - 阶段：对话流式与 AI 接口扩展分析
  - 发现或问题：当前 `notion_client.py` 的 `stream_chat` 先完整请求 `runInferenceTranscript` 再按 2 字符切块返回，属于伪流式；现有分析报告主要聚焦注册链路，对 AI 会话、额度、订阅、账号信息等接口沉淀不足，不利于后续独立开发。
  - 结论：需改为基于 httpx 流式读取 NDJSON 的真实流式转发，并继续用现有项目与抓包结论补充 AI 相关接口、字段、用途和后续开发建议到分析报告。
  - 下一步：重构 `call_notion_api/stream_chat` 为 `client.stream` 方案，随后补齐 AI 接口分析与 README 稳定说明。

- 时间：2026-04-18
  - 阶段：对话流式与 AI 接口扩展完成
  - 发现或问题：`runInferenceTranscript` 返回的是 NDJSON 流，单行事件常携带“当前完整文本快照”而不是固定 token 增量；若直接等完整响应再切块，会破坏真实时序。主页初始化阶段还已出现 `getSubscriptionData`、`getBillingSubscriptionBannerData`、`getLifecycleUserProfile`、`getTeamsV2`、`getUserHomePages` 等账号与订阅相关接口，具备继续抽象余额、调用次数和账号信息接口的价值。
  - 结论：已把 `stream_chat` 改为基于 `httpx.AsyncClient.stream(...).aiter_lines()` 的真实流式实现，并通过前缀差量方式向 OpenAI SSE 输出增量内容；同时已把 AI 对话主接口、模型映射、额度/订阅/账号相关接口线索、后续抓包路径与开发建议补充进分析报告，并在 README 同步稳定说明。
  - 下一步：如需继续推进“剩余额度/调用次数”接口落地，应优先在 AI 页面和 Billing 页面补抓 `getSubscriptionData` 与 `getBillingSubscriptionBannerData` 的真实响应字段。

- 时间：2026-04-18
  - 阶段：继续抓取 AI 与账号相关接口
  - 发现或问题：现有报告中的 `getSubscriptionData`、`getBillingSubscriptionBannerData` 等仍主要基于初始化请求命名推断，缺少真实响应字段；用户要求过程中继续关注其他相关接口，意味着抓包时不能只盯余额和调用次数，还要同步记录模型、权限、空间、用户画像、实验与计费提示等周边接口。
  - 结论：本轮需以 `https://www.notion.so/ai` 与可能的 Billing/Settings 页面为主，结合 js-reverse 实抓请求与响应，并把新增接口线索一并补入分析报告。
  - 下一步：打开 AI 页面，先看最近网络请求，再决定是否下断点或切换页面继续抓取。

- 时间：2026-04-18
  - 阶段：抓包环境阻塞排查
  - 发现或问题：调用 js-reverse 的 `list_network_requests`、`list_console_messages`、`select_page`、`list_breakpoints` 均直接返回 `fetch failed`，说明当前浏览器调试会话或 MCP 到浏览器的连接已失效，暂时无法继续抓真实接口。
  - 结论：先排查 js-reverse 调试环境是否仍连着浏览器，再恢复 AI 页面抓包；在会话恢复前不继续臆测接口字段。
  - 下一步：检查本地仓库中的 js-reverse 使用说明与可恢复方式；若无法自动恢复，再请用户确认浏览器连接状态。

- 时间：2026-04-18
  - 阶段：恢复调试会话后首次检查
  - 发现或问题：js-reverse 已恢复可调用，但当前选中的页面只有 `chrome://omnibox-popup` 与 `chrome://new-tab-page`，尚未打开 Notion 页面，因此还没有任何 `api/v3` 请求可分析。
  - 结论：需要先新开或切到 Notion 相关页面，再触发 AI 与 Billing 相关操作抓真实请求。
  - 下一步：打开 `https://www.notion.so/ai`，检查网络请求并继续扩展接口清单。

- 时间：2026-04-18
  - 阶段：AI 页面初始化接口与源码交叉取证
  - 发现或问题：在 `https://www.notion.so/ai` 首屏初始化中，已实际抓到 `getAppConfig`、`getSpacesInitial`、`getUserAnalyticsSettings`、`getLifecycleUserProfile`、`syncRecordValuesMain`、`syncRecordValuesSpaceInitial`、`getDesktopAppRegistration`、`etClient`；其中 `getAppConfig` 返回 `statsigUser`、大量 `feature_gates/experiments` 与设备指纹信息，可用于判断实验开关与 AI 能力暴露条件；`getSpacesInitial` 与 `syncRecordValuesMain` 可直接拿到账户邮箱、时区、locale、signup_time、domain_type；`getUserAnalyticsSettings` 暴露 `hashed_user_id`、`user_email`、埋点/客服开关；`getDesktopAppRegistration` 返回桌面端注册状态。进一步查前端源码确认：`getSubscriptionData` 不是独立调用，而是与 `getVisibleUsers`、`getSimilarUsers` 并行组合成订阅数据 store，并按 `SubscriptionData:<spaceId>:v2` 缓存；`getTeamsV2` 与 `getUserHomePages` 也都在前端存在真实调用点；`billing_subscription_status` banner 已确认存在，但未直接搜到显式的 `getBillingSubscriptionBannerData` 字面量，说明其可能经由统一 banner / store 封装间接触发。
  - 结论：除了余额/调用次数外，后续账号能力建模至少还应覆盖实验开关、客服埋点开关、用户画像、空间订阅缓存、可见用户、相似用户、团队列表、首页页签与桌面端注册状态。
  - 下一步：把这些已取到的真实字段与源码调用关系补进分析报告，并继续记录哪些接口仍需到 Billing 页面或 AI 实际发送对话后补抓响应。

- 时间：2026-04-18
  - 阶段：继续抓 Billing 与额度链路
  - 发现或问题：AI 首页已确认订阅与 banner 存在，但尚未拿到 `getSubscriptionData` 的真实返回字段，也未定位 banner 数据的直接来源。
  - 结论：本轮切到 Billing/Plans 相关页面继续抓包，优先找剩余额度、调用次数、重置时间、套餐层级与 AI 权益字段，同时继续记录任何账号、空间、团队、支付相关接口。
  - 下一步：从当前已登录页面跳转到 Billing 或 Settings 页，查看新增 `api/v3` 请求与源码调用。

- 时间：2026-04-18
  - 阶段：Billing 页面受重定向阻塞后的补充取证
  - 发现或问题：尝试直接打开 `settings/billing`、`settings/plans` 时，当前账号都会被重定向回 `/onboarding`，导致暂时无法拿到真正的 Billing 请求；但 onboarding 首屏额外暴露了一组账号/域名/建空间资格接口：`getJoinableSpaces` 返回可加入空间列表与 `subscriptionTier`，`isUserDomainJoinable` 返回域名是否可加入，`validateUserCanCreateWorkspace` 返回 `canUserCreateSpace`，`isEmailEducation` 返回教育邮箱资格，`getGeoIpLocation` 返回国家/州/城市/时区，`checkEmailEligibilityForConnectedAppProducts` 返回邮箱是否可用于 Calendar 等连接产品，`getVerifiedEmailDomain` 当前返回空对象。
  - 结论：虽然还没进入 Billing 页面，但已确认 Notion 在 onboarding 前置阶段就会综合校验地域、邮箱类型、域名加入资格、可创建空间能力和可加入空间清单，这些信息会直接影响后续套餐页、组织加入、连接产品与可能的 AI/计费入口暴露。
  - 下一步：先把这批接口补入分析报告；若继续追余额字段，需要先完成该账号 onboarding 或换一个能直接进入工作空间与 Billing 的账号。

- 时间：2026-04-18
  - 阶段：推进当前账号完成 onboarding
  - 发现或问题：用户选择先完成当前账号 onboarding，再回到 Billing 抓真实订阅与额度接口；因此当前优先级从页面抓包切换为稳定推进 onboarding 分支。
  - 结论：需先处理名字页、营销勾选、用途页、创建空间或加入空间、后续跳过页，确保账号进入工作空间主页后再继续 Billing 抓包。
  - 下一步：在当前 `/onboarding` 页面补名字、取消营销勾选并点击继续，逐步推进到工作空间主页。

- 时间：2026-04-18
  - 阶段：onboarding 名字页推进成功
  - 发现或问题：当前账号在名字页使用 `posase_test_headers` 可直接通过；取消营销勾选后点击继续，页面已进入“加入团队或创建工作空间”，并展示 2 个可加入空间与 `创建新工作空间` 选项。
  - 结论：名字页与营销勾选已通过，当前需要决定是加入已有空间还是创建新空间；为尽快进入可访问 Billing 的稳定工作空间，优先加入已有空间更稳。
  - 下一步：点击一个现有工作空间的 `加入`，随后继续检查是否已进入主页或仍需补后续步骤。

- 时间：2026-04-18
  - 阶段：onboarding 进入工作空间成功
  - 发现或问题：在“加入团队或创建工作空间”页，对 `加入` 节点触发完整鼠标事件后，已成功加入 `test1727x的工作空间`，当前页面已进入真实工作空间主页，不再停留在 onboarding。
  - 结论：当前账号已具备继续访问设置与 Billing/Plans 页的前提，下一步可以重新尝试抓真实订阅与额度接口。
  - 下一步：从当前工作空间主页跳转 `settings/billing` 与 `settings/plans`，重点抓 `getSubscriptionData`、banner、usage、credits、quota 相关请求。

- 时间：2026-04-18
  - 阶段：Billing 相关真实接口已抓到关键字段
  - 发现或问题：完成 onboarding 并进入工作空间后，首页初始化已稳定拉起 `getBillingSubscriptionBannerData`、`getSubscriptionData`、`getSubscriptionEntitlements`、`getAIUsageEligibility`、`getAIUsageEligibilityV2`、`getSpaceBlockUsage`、`getTranscriptionUsage`、`getSubscriptionBanner` 等真实接口。当前空间 `spaceId=dc3b731b-7345-811e-bd2e-0003792c58d5` 的关键响应为：`getSubscriptionData` 返回 `subscriptionTier=free`、`blockUsage=34`、`accountBalance=0`、`hasPaidNonzero=false`；`getBillingSubscriptionBannerData` 返回 `bannerData={}`；`getSubscriptionEntitlements` 返回 `editsBlocked=false`；`getAIUsageEligibility` 返回 `isEligible=true`、`type=spaceAllowance`、`spaceLimit=150`、`userLimit=75`；`getAIUsageEligibilityV2` 返回更完整 usage/limits 结构，包括 `currentServicePeriod.spaceUsage/userUsage`、`lifetime.*`、`totalCreditBalance=0`、`creditsInOverage=0`、`free.spaceLimit=150`、`free.userLimit=75`；`getTranscriptionUsage` 返回 `eligibility=available`、`usage=0`、`limit=7200` 秒；`getSubscriptionBanner` 返回 `bannerIds=[]`。
  - 结论：剩余额度、调用上限、空间层级与是否可继续使用 AI 已经可以通过 `getAIUsageEligibilityV2 + getAIUsageEligibility + getSubscriptionData` 三个接口稳定建模；banner 相关接口目前为空，说明当前免费空间无升级或告警 banner。
  - 下一步：把这些字段、接口职责和开发建议补进分析报告与 README；若还要继续深挖调用次数，可再观察实际发送几次 AI 对话后的 usage 是否实时增长。

- 时间：2026-04-18
  - 阶段：验证 AI 对话前后 usage 差量
  - 发现或问题：用户明确只需要验证真实对话前后 usage 是否增长，不需要继续整理后续开发方案。
  - 结论：本轮仅抓取一次对话前后的 `getAIUsageEligibility` / `getAIUsageEligibilityV2` / `runInferenceTranscript` 等差量，不扩展额外设计内容。
  - 下一步：先记录当前 usage 基线，再发送一次真实 AI 对话，随后回看相关接口响应是否变化。


- 时间：2026-04-18
  - 阶段：验证 AI 对话前后 usage 差量完成
  - 发现或问题：已在 `https://www.notion.so/ai` 发起一次真实 AI 对话，请求内容为“请只回复数字 1”，页面实际回复为 `1`，并已抓到对应 `runInferenceTranscript`；随后回看同空间 `dc3b731b-7345-811e-bd2e-0003792c58d5` 的 `getAIUsageEligibility` 与 `getAIUsageEligibilityV2`，当前响应仍显示 `spaceUsage=0`、`userUsage=0`，且 `currentServicePeriod`、`lifetime`、`totalCreditBalance`、`creditsInOverage` 也都未变化。
  - 结论：至少在当前免费空间样本下，单次真实 AI 对话完成后，usage 相关接口不会立即按本次请求同步递增；若后续还要做计量验证，需要继续观察延迟刷新、批量累计或务端异步结算。
  - 下一步：把本次差量验证结果补进分析报告，供后续开发按“usage 可能非实时更新”处理。

- 时间：2026-04-19
  - 阶段：整理 notion2api 总分析报告
  - 发现或问题：用户要求参考 `analysis/maoyan/analysis.md` 的结构，在 `analysis/notion2api` 输出统一分析报告；现有材料分散在 `README.md`、`WORKLOG.md`、`registration-analysis-report.md` 与代码中，缺少一份汇总版总报告。
  - 结论：已按“最终交付物、核心接口、算法/链路、问题复盘、工具经验”结构整理 `analysis.md`，集中沉淀 AI 对话代理、env 获取、自动注册、多账号持久化、订阅与 usage 建模结论。
  - 下一步：如用户需要，可继续把该报告与 `README.md` 做进一步去重或补充目录导航。
