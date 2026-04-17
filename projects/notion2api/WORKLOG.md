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
