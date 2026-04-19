# notion2api

一个基于 Python 的 Notion AI → OpenAI 兼容代理服务。

## 文件说明

- `main.py`：FastAPI 服务入口，暴露 OpenAI 兼容接口
- `notion_client.py`：Notion 请求构造、响应解析、内容清理
- `cli.py`：服务启停管理脚本
- `capture_env.py`：从真实 Notion AI 请求提取凭证并更新 `.env`
- `auto_register.py`：独立运行的 Notion 账号注册、刷新、导出与多账号管理脚本
- `accounts/`：多账号持久化目录
- `.env`：当前激活账号的运行凭证
- `.env.example`：环境变量模板
- `WORKLOG.md`：关键过程、证据、阻塞点与阶段结论记录

## 安装

```bash
pip install -r requirements.txt
playwright install chromium
```

## 启动

```bash
python cli.py start
python cli.py status
python cli.py stop
```

也可以直接运行：

```bash
python main.py
```

## 接口

### 获取模型列表

```bash
curl http://localhost:3000/v1/models \
  -H "Authorization: Bearer sk-notion2api"
```

### 对话

```bash
curl http://localhost:3000/v1/chat/completions \
  -H "Authorization: Bearer sk-notion2api" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "notion-ai",
    "messages": [{"role": "user", "content": "hello"}]
  }'
```

## env 获取与刷新

### 方式一：抓取已登录浏览器中的真实请求

`capture_env.py` 已固化抓取流程，但它依赖 Claude Code / MCP 注入环境下的 `js-reverse` 工具调用能力，不是独立运行脚本。

抓取流程：

1. 确保浏览器已登录 Notion
2. 确保 js-reverse MCP 已连接浏览器
3. 打开 `https://www.notion.so/ai`
4. 运行：

```bash
python capture_env.py
```

它会自动从真实请求中提取：

- `NOTION_TOKEN_V2`
- `NOTION_P_SYNC_SESSION`
- `NOTION_SPACE_ID`
- `NOTION_USER_ID`
- `NOTION_SPACE_VIEW_ID`
- `NOTION_CSRF`
- `NOTION_DEVICE_ID`
- `NOTION_BROWSER_ID`

### 方式二：使用账号目录中的持久化状态刷新

```bash
python auto_register.py refresh --account <account_id>
python auto_register.py refresh --account <account_id> --export
python auto_register.py refresh --account <account_id> --export --headless
```

## 自动注册账号

### 说明

`auto_register.py` 当前采用 **Playwright 多账号方案**，用于稳定完成注册、账号持久化、凭证刷新与 env 导出。

纯 requests/cloudscraper 方案已实测在 `getLoginOptions` 阶段被 Notion 服务端拦截，因此不再作为注册主方案。

### 账号目录结构

```text
accounts/
  <account_id>/
    state.json
    env.json
    meta.json
```

- `state.json`：浏览器持久化状态
- `env.json`：账号对应的 Notion 凭证
- `meta.json`：邮箱、user_id、space_id、更新时间等元信息

### 运行方式

```bash
# 注册一个新账号
python auto_register.py register

# 注册后顺便导出到项目根 .env
python auto_register.py register --export

# Linux / 服务器环境推荐无头运行
python auto_register.py register --export --headless

# 刷新指定账号 env
python auto_register.py refresh --account <account_id>
python auto_register.py refresh --account <account_id> --export
python auto_register.py refresh --account <account_id> --export --headless

# 导出指定账号到项目根 .env
python auto_register.py export --account <account_id>

# 列出现有账号
python auto_register.py list
```

### 技术方案

真实浏览器自动化链路：

1. Playwright 打开 Notion 注册页
2. 输入邮箱并触发 OTP 发送
3. QQ IMAP 拉取验证码
4. 输入验证码并完成登录
5. 处理 onboarding、工作空间选择、用途页、邀请成员页、方案页与桌面应用跳过
6. 从 `context.cookies()`、`localStorage`、初始化接口数据提取 env
7. 按账号写入 `accounts/<account_id>/`
8. 注册完成后自动补一次 `refresh`，确保首次导出尽量拿到完整 `space_view_id`
9. 按需导出到项目根 `.env`

### 关键技术点

- 输入框必须用原型 setter + `InputEvent/change` 事件，直接赋值无效
- 按钮点击需要兼容中英文文案，避免首屏和 onboarding 页结构差异导致误点
- 营销勾选可能重复出现，每个步骤都要重新检查
- 验证码通过 QQ IMAP 搜索 `FROM notion` 邮件，提取最新 6 位数字
- env 提取需要联合 Cookie、localStorage、`getSpacesInitial`、`loadUserContent` 与运行态上下文
- 无头方案必须先处理自动化指纹，否则 `getLoginOptions` 可能被服务端拦截

## 当前状态

目前已验证：

- 服务可启动 / 停止
- `GET /v1/models` 正常
- `POST /v1/chat/completions` 正常，`stream=true` 已改为基于 Notion NDJSON 的真实流式转发
- 可用真实 Notion 凭证完成对话
- 返回文本编码正常
- `auto_register.py register --export --headless` 可完成独立注册
- `auto_register.py refresh --account <account_id> --export --headless` 可补齐 `space_id` / `space_view_id`
- 多账号目录可独立保存和导出

## 对 js-reverse 的沉淀

本项目已沉淀两条可复用规则：

- 当目标是补全 `.env`、Cookie、header、动态请求体时，优先证据永远是真实网络请求，而不是页面脚本可见值
- 最终交付脚本必须优先考虑独立运行方案；方案顺序为：纯脚本 > Playwright 无头 > Playwright 有头

相关知识库：

- `.claude/skills/knowledge/05-project/notion-env-capture-pattern.md`
- `.claude/skills/knowledge/05-project/independent-delivery-priority.md`

## 文档说明

- `README.md`：维护稳定说明、使用方式与当前能力
- `WORKLOG.md`：维护关键过程记录、证据、阻塞点、结论与下一步

## AI 接口补充说明

- 已实抓到可直接用于账号额度与 AI 使用量建模的接口：`getSubscriptionData`、`getAIUsageEligibility`、`getAIUsageEligibilityV2`、`getSubscriptionEntitlements`、`getBillingSubscriptionBannerData`、`getSubscriptionBanner`、`getSpaceBlockUsage`、`getTranscriptionUsage`。
- 当前样本空间已确认：`subscriptionTier=free`、`accountBalance=0`、`AI free spaceLimit=150`、`userLimit=75`、`transcription limit=7200s`。
- 对话主链路使用 `POST /api/v3/runInferenceTranscript`，返回 `application/x-ndjson`，当前代理已按真实流式逐行转发。
- 已沉淀的账号/订阅相关重点接口包括：`getAppConfig`、`getSpacesInitial`、`getUserAnalyticsSettings`、`getLifecycleUserProfile`、`syncRecordValuesMain`、`syncRecordValuesSpaceInitial`、`getJoinableSpaces`、`isUserDomainJoinable`、`validateUserCanCreateWorkspace`、`isEmailEducation`、`getGeoIpLocation`、`checkEmailEligibilityForConnectedAppProducts`、`getVerifiedEmailDomain`、`getDesktopAppRegistration`、`getSubscriptionData`、`getVisibleUsers`、`getSimilarUsers`、`getTeamsV2`、`getUserHomePages`，以及 `billing_subscription_status` banner 链路。
- 详细接口分析、字段用途和后续抓包建议见 [registration-analysis-report.md](registration-analysis-report.md)。

## 注意事项

- Notion 登录态过期后，需要重新抓一次 `.env` 或对账号执行一次 `refresh`
- `notion-client-version` 未来可能需要跟随网页版本调整
- 若 Notion 改了 `runInferenceTranscript` 或注册链路结构，需要重新抓包校准
- `capture_env.py` 仍依赖 MCP 分析环境，不属于独立运行交付脚本
