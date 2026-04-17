# Skill 与知识库映射

## Skill 章节 → 知识库文件

| Skill 章节 | 知识库文件 | 说明 |
|---|---|---|
| 观察判断流程 | `03-topics/hook-and-boundary-patterns.md` | 边界选择、命中判断流程 |
| 反调试与风险分支处理 | `03-topics/anti-debug-and-risk-branches.md` | 调试摩擦 vs 真实风险分支 |
| 瑞数特定处理 | `04-rs/*.md` | 定位/还原/运行时锚点 |
| 工具完整参数 | `05-project/tool-reference.md` | 23个工具详细参数 |
| 反检测配置 | `05-project/反检测工作记录.md` | 根因分析与修复历史 |
| 最小环境设计 | `02-artifacts/minimal-env-design.md` | 运行时补充节格式 |
| 独立运行交付优先级 | `05-project/independent-delivery-priority.md` | 纯脚本优先、headless 次之 |
| 反模式预警 | `03-topics/anti-patterns.md` | 各阶段常见错误 |

## 知识库索引

### 按阶段使用

| 阶段 | 核心文件 | 按需挂载 |
|---|---|---|
| locate | `01-core/locate-workflow.md` | `03-topics/crypto-entry-locating.md`、`04-rs/rs-collection-and-two-hop-routing.md` |
| recover | `01-core/recover-strategy.md` | `03-topics/wasm-worker-webpack.md`、`03-topics/jsvmp-and-ast.md`、`04-rs/rs-recovery-anchors.md` |
| runtime | `01-core/runtime-diagnosis.md` | `02-artifacts/minimal-env-design.md`、`03-topics/anti-debug-and-risk-branches.md` |
| validation | `01-core/equivalence-and-validation.md` | - |

### 按场景触发

| 场景 | 推荐文件 |
|---|---|
| hook/断点/边界观察 | `03-topics/hook-and-boundary-patterns.md` |
| 签名/token/加密字段定位 | `03-topics/crypto-entry-locating.md` |
| worker/wasm/webpack 分析 | `03-topics/wasm-worker-webpack.md` |
| JSVMP/反混淆/AST变换 | `03-topics/jsvmp-and-ast.md` |
| AST字符串表/bundle解包 | `03-topics/ast-deobfuscation-playbook.md` |
| WebSocket/Protobuf/SSE/心跳 | `03-topics/protocol-and-long-connection.md` |
| 反调试/风险分支 | `03-topics/anti-debug-and-risk-branches.md` |
| 环境模拟/补环境 | `03-environment/*.md` |
| 生命周期状态/重放路由 | `03-topics/sdenv-fit-check-and-routing.md` |
| 错误模式预警 | `03-topics/anti-patterns.md` |

### 产物格式

| 产物 | 文件 |
|---|---|
| 请求链路记录 | `02-artifacts/request-chain-recording.md` |
| 阶段交接协议 | `02-artifacts/stage-handoff-protocol.md` |
| 运行时补充节 | `02-artifacts/minimal-env-design.md` |

### 学习资源

位于 `06-learning/`，供入门学习使用，与专题方法分开：
- `01-basics/` — 基础技能（DevTools、Hook、搜索定位）
- `02-obfuscation/` — 混淆与反混淆
- `03-environment/` — 环境模拟
- `04-algorithms/` — 加密算法
- `05-advanced/` — 高级技术（反调试、指纹、RPC、WASM）
- `06-case-studies/` — 实战案例
- `07-resources/` — 资源（练习平台、工具、学习路径）

## 使用原则

1. **先选阶段，后读参考**：先确定当前阶段，再读该阶段核心参考
2. **最小化挂载**：每次最多读 1 个核心参考 + 1-2 个专题参考
3. **按需触发**：专题参考只在匹配当前阻塞场景时挂载
4. **禁止预先加载**：不提前加载大量参考，只在需要时读取