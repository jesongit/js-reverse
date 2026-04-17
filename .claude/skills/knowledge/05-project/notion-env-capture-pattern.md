# Notion env 抓取模式

适用场景：在浏览器已登录 Notion 的前提下，需要从真实请求中提取 API 代理所需凭证，并固化为本地配置。

## 核心结论

### 1. 不要优先读 `document.cookie`

当目标是提取 Notion AI 所需认证信息时，不能默认依赖 `document.cookie`。

原因：
- 某些关键凭证不能稳定通过页面脚本读取
- 页面可见 Cookie 与真实请求携带 Cookie 可能不一致
- 前端可读性不是可靠证据，真实网络请求才是最终证据

### 2. 必须抓真实请求头

当出现以下任一情况时，应直接抓真实请求，而不是继续猜：

- `.env` 中旧凭证失效
- 页面脚本拿不到关键 Cookie
- 需要确认真实请求头、Cookie、Body 的最小必需集合
- 需要确认上游接口是否已改版

## 推荐流程

### evidence 阶段

1. 对目标接口下 XHR / Fetch 断点
2. 触发一次最小可复现请求
3. 从真实请求中记录：
   - URL
   - method
   - request headers
   - cookie header
   - request body
   - response body
4. 立即把结论同步到当前工作目录 `README.md`

### 对 Notion AI 的具体模式

目标接口：
- `POST /api/v3/runInferenceTranscript`

优先记录字段：
- `token_v2`
- `p_sync_session`
- `csrf`
- `notion_user_id`
- `device_id`
- `notion_browser_id`
- `x-notion-active-user-header`
- `x-notion-space-id`
- `notion-client-version`
- `notion-audit-log-platform`

## 常见误区

| 误区 | 问题 | 正确做法 |
|---|---|---|
| 先从 `document.cookie` 补 env | 容易漏关键凭证 | 先抓真实请求头 |
| 看到 401 就先改代码 | 误判为实现 bug | 先校验凭证是否失效 |
| 只记录 Cookie，不记录 body/header | 后续难以复现 | 头、Cookie、Body 一起记录 |
| 抓完请求只改代码不写 README | 过程难追溯 | 关键证据必须即时写 README |

## 快速检查清单

```text
是否已有真实请求样本？
是否拿到了完整 cookie header？
是否记录了关键 header？
是否确认 body 中的 spaceId / userId / spaceViewId？
是否把本次证据同步到当前工作目录 README？
```

## 来源

- 来源任务：`projects/notion2api`
- 验证次数：1
- 类型：项目专项到通用模式的提炼
