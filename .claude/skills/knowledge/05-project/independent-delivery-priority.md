# 独立运行交付优先级

适用场景：为站点逆向、参数还原、注册登录、凭证提取等任务交付可运行脚本时，需要明确交付物不能依赖 Claude、MCP、对话上下文或人工调试环境。

## 核心规则

### 1. 最终交付必须独立运行

最终给用户的脚本必须满足：
- 直接在本地 Python / Node 环境运行
- 不依赖 Claude Code、MCP、浏览器 DevTools 会话或额外人工注入步骤
- 所需依赖可以通过 `requirements.txt`、`package.json`、README 安装与执行

禁止把以下内容当成最终交付：
- 只能在 Claude/MCP 会话里运行的抓取脚本
- 依赖调试面板手动断点的半自动流程
- 需要先让 Agent 帮忙注入再运行的脚本

### 2. 方案优先级必须固定

遇到可选实现路径时，必须按以下顺序评估：

1. **纯脚本方案优先**
   - requests/httpx/urllib
   - cloudscraper
   - 直接算法还原
   - 本地环境模拟
   - 纯 HTTP 请求链重放
2. **无头浏览器方案其次**
   - Playwright headless
   - 仅在纯脚本方案失败且真实证据证明需要浏览器上下文时使用
3. **有头浏览器方案最后**
   - 仅在 headless 也失败时才考虑
   - 必须说明失败证据和退化原因

### 3. MCP/浏览器调试只可用于分析，不可作为交付依赖

允许使用浏览器调试、真实请求抓包、MCP 工具辅助定位：
- 确认真实请求链
- 提取关键请求头、参数结构、风控分支
- 证明 headless 与 headed 的差异

但这些能力只能用于**分析和取证**，不能成为最终脚本的运行前提。

### 4. 先验证非浏览器方案，再升级浏览器方案

当用户要“能独立运行”的脚本时，必须先回答并验证：
- 目标链路能否直接通过真实 HTTP 请求重放
- 是否存在浏览器特有状态（Cookie、Storage、前端挑战）
- 是否已出现明确证据说明纯脚本方案不可行

只有在拿到真实证据后，才能升级到 Playwright。

### 5. 浏览器方案内部也要先走 headless

如果必须进入浏览器方案：
- 默认先实现 headless
- 先处理 headless 指纹、自动化特征、user-agent、webdriver 等问题
- 只有当 headless 被真实风控或站点行为明确阻断时，才退到 headed

## 证据化要求

从纯脚本切到浏览器方案时，README 或交接中必须写清：
- 已尝试的纯脚本方案
- 失败的真实证据（接口状态码、风控提示、错误消息、请求差异）
- 为什么这些问题不能仅靠补参数解决
- 为什么 Playwright headless 是当前最小升级

从 headless 切到 headed 时，也必须记录：
- headless 失败的真实证据
- 是否出现 `HeadlessChrome`、`webdriver`、指纹差异
- 为什么继续补 headless 指纹仍不足

## notion2api 提炼结论

`projects/notion2api` 已验证出一条可复用规则：
- 先尝试纯 requests/cloudscraper 注册链
- 若真实接口返回如 `Login is not allowed.` 之类服务端拦截，再升级浏览器方案
- 升级浏览器后优先做 headless，并先修自动化指纹
- 若 headless 指纹修正后已能走通 `getLoginOptions` / `sendTemporaryPassword`，则继续坚持 headless，不轻易退回 headed
- 若某些凭证在首次注册时尚未稳定暴露，可通过脚本内部自动 refresh 补齐，但仍要保持最终脚本独立运行

## 快速检查清单

```text
最终脚本是否离开 Claude/MCP 也能运行？
是否先尝试并验证了纯脚本方案？
是否有真实证据证明纯脚本不可行？
若进入浏览器方案，是否先实现并验证 headless？
若退到 headed，是否记录了 headless 失败证据？
最终 README 是否写清依赖、命令、限制与失败边界？
```
