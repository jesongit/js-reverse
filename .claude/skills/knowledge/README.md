# JS 逆向工程知识库

> 结构化知识库，为 js-reverse skill 提供可查询的参考文档

## 目录结构

### 00-overview/ 概览与入口（新增）

- [Skill 与知识库映射](00-overview/skill映射.md) — skill 章节与知识库文件的对应关系
- [阶段速查](00-overview/阶段速查.md) — 7阶段核心要点速记

### 01-core/ 核心阶段方法

- [Locate 工作流](01-core/locate-workflow.md) — 定位阶段核心方法
- [Recover 策略](01-core/recover-strategy.md) — 还原阶段核心方法
- [Runtime 诊断](01-core/runtime-diagnosis.md) — 运行时适配核心方法
- [等价验证](01-core/equivalence-and-validation.md) — 验证阶段核心方法

### 02-artifacts/ 标准产物格式

- [请求链路记录](02-artifacts/request-chain-recording.md) — 证据记录规范（请求链路.md 格式）
- [阶段交接协议](02-artifacts/stage-handoff-protocol.md) — 阶段切换交接格式
- [最小环境设计](02-artifacts/minimal-env-design.md) — 运行时补充节格式

### 03-topics/ 专题参考（按触发场景）

- [Hook 和边界选择](03-topics/hook-and-boundary-patterns.md) — hook/断点/边界观察
- [加密字段定位](03-topics/crypto-entry-locating.md) — 签名/token/加密字段定位
- [WASM/Worker/Webpack 分析](03-topics/wasm-worker-webpack.md) — worker/wasm/webpack 分析
- [JSVMP 和 AST](03-topics/jsvmp-and-ast.md) — JSVMP/反混淆/AST 变换
- [AST 反混淆 playbook](03-topics/ast-deobfuscation-playbook.md) — 字符串表恢复/bundle 解包
- [协议与长连接](03-topics/protocol-and-long-connection.md) — WebSocket/Protobuf/SSE/心跳协议
- [反调试与风险分支](03-topics/anti-debug-and-risk-branches.md) — 反调试/风险分支
- [SDENV 适配与路由](03-topics/sdenv-fit-check-and-routing.md) — 生命周期状态/重放路由
- [反模式预警](03-topics/anti-patterns.md) — 各阶段常见错误

### 04-rs/ 瑞数专项

- [RS 采集与两跳路由](04-rs/rs-collection-and-two-hop-routing.md) — locate 阶段
- [RS 还原锚点](04-rs/rs-recovery-anchors.md) — recover 阶段
- [RS 运行时与 basearr 适配](04-rs/rs-runtime-and-basearr-fit.md) — runtime 阶段

### 05-project/ 本项目专项

- [工具完整参数](05-project/tool-reference.md) — 23个工具的详细参数说明
- [反检测工作记录](05-project/反检测工作记录.md) — 反检测机制/根因分析/故障排除

### 06-learning/ 入门学习资源

供入门学习使用，与专题方法分开：

| 目录 | 用途 |
|---|---|
| `01-basics/` | 基础技能（DevTools、Hook、搜索定位） |
| `02-obfuscation/` | 混淆与反混淆 |
| `03-environment/` | 环境模拟 |
| `04-algorithms/` | 加密算法 |
| `05-advanced/` | 高级技术（反调试、指纹、RPC、WASM） |
| `06-case-studies/` | 实战案例 |
| `07-resources/` | 资源（练习平台、工具、学习路径） |

## 快速查找

### 按阶段查找

| 阶段 | 核心文件 | 按需挂载 |
|---|---|---|
| locate | `01-core/locate-workflow.md` | `03-topics/crypto-entry-locating.md`、`04-rs/rs-collection-and-two-hop-routing.md` |
| recover | `01-core/recover-strategy.md` | `03-topics/wasm-worker-webpack.md`、`03-topics/jsvmp-and-ast.md`、`04-rs/rs-recovery-anchors.md` |
| runtime | `01-core/runtime-diagnosis.md` | `02-artifacts/minimal-env-design.md`、`03-topics/anti-debug-and-risk-branches.md` |
| validation | `01-core/equivalence-and-validation.md` | - |

### 按场景查找

| 场景 | 推荐阅读 |
|------|---------|
| 找不到加密函数位置 | `01-core/locate-workflow.md` → `03-topics/crypto-entry-locating.md` |
| 遇到混淆代码 | `03-topics/anti-patterns.md` → `03-topics/jsvmp-and-ast.md` → `03-topics/ast-deobfuscation-playbook.md` |
| Node.js 运行报错 | `03-environment/env-simulation-intro.md` → `02-artifacts/minimal-env-design.md` |
| 不认识加密算法 | `06-learning/04-algorithms/crypto-identification.md` |
| 遇到 debugger 断不下来 | `03-topics/anti-debug-and-risk-branches.md` |
| 算法太复杂不想还原 | `06-learning/05-advanced/rpc-technique.md` 或 `06-learning/05-advanced/headless-browser.md` |
| 遇到 .wasm 文件 | `03-topics/wasm-worker-webpack.md` |
| 瑞数风控 | `04-rs/` 系列文件 |
| 不知道学什么 | `06-learning/07-resources/learning-path.md` |

### 关键词索引

- **MD5/SHA/AES/RSA** → `06-learning/04-algorithms/crypto-identification.md`
- **Canvas/WebGL** → `03-environment/env-simulation-advanced.md` | `06-learning/05-advanced/browser-fingerprint.md`
- **debugger** → `03-topics/anti-debug-and-risk-branches.md`
- **Babel** → `06-learning/02-obfuscation/ast-deobfuscation.md`
- **Proxy** → `03-environment/env-simulation-practice.md`
- **Playwright** → `06-learning/05-advanced/headless-browser.md`
- **WebSocket** → `03-topics/protocol-and-long-connection.md`
- **wasm2wat** → `06-learning/05-advanced/wasm-reverse.md`
- **CryptoJS** → `06-learning/04-algorithms/crypto-identification.md` | `06-learning/04-algorithms/algorithm-reduction.md`

## 使用原则

1. **先选阶段，后读参考**：先确定当前阶段，再读该阶段核心参考
2. **最小化挂载**：每次最多读 1 个核心参考 + 1-2 个专题参考
3. **按需触发**：专题参考只在匹配当前阻塞场景时挂载
4. **禁止预先加载**：不提前加载大量参考，只在需要时读取