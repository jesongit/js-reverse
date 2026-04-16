# 学习路径建议

> 来源: [JS逆向完整技能图谱](https://51rexue.cn/blog/50) | [宇哥JS逆向入门实战课](https://juejin.cn/post/7566809515284824115)

## 概述

本文提供从零开始学习 JS 逆向工程的结构化路径，分阶段规划学习内容和目标。

## 前置知识要求

### JavaScript 基础（1-2 周）
- ES6+ 语法（let/const、箭头函数、解构、Promise/async-await）
- 原型链和继承
- 闭包和作用域
- DOM API 基本操作
- JSON 序列化/反序列化

### HTTP 协议基础（1 周）
- 请求/响应结构（Headers、Body、Status）
- GET vs POST
- Cookie / Session / Token
- HTTPS 原理
- CORS 跨域

### Python 基础（1 周）
- requests 库发送 HTTP 请求
- hashlib / base64 编码解码
- 基本的文件操作和字符串处理

## 第一阶段：基础入门（2-4 周）

### 目标
能够使用浏览器 DevTools 定位简单的加密逻辑，并用 Python 还原。

### 学习内容
1. **浏览器开发者工具**
   - → [浏览器开发者工具](../01-basics/browser-devtools.md)
   - Network 面板抓包分析
   - Sources 面板断点调试
   - Console 执行代码

2. **搜索定位技巧**
   - → [搜索定位技巧](../01-basics/search-locate.md)
   - 全局搜索定位
   - XHR 断点
   - Call Stack 回溯

3. **基础加密识别**
   - → [加密算法识别](../04-algorithms/crypto-identification.md)
   - Base64 编码/解码
   - MD5 / SHA 哈希
   - 简单的 CryptoJS 调用

4. **Python 还原**
   - → [算法还原实战](../04-algorithms/algorithm-reduction.md)
   - 使用 hashlib / base64 库
   - requests 发送请求

### 练习
- 猿人学第 1-5 题
- 简单的 Base64 / MD5 签名还原

---

## 第二阶段：Hook 与反调试（2-4 周）

### 目标
掌握 Hook 技术快速定位加密函数，能绕过常见的反调试手段。

### 学习内容
1. **Hook 技术**
   - → [Hook 技术](../01-basics/hook-techniques.md)
   - JSON.stringify / Cookie Hook
   - Tampermonkey 脚本编写
   - Console 注入

2. **反调试对抗**
   - → [反调试技术](../05-advanced/anti-debugging.md)
   - 无限 debugger 绕过
   - DevTools 检测绕过

### 练习
- 猿人学第 6-10 题
- 有反调试保护的网站分析

---

## 第三阶段：混淆还原（4-6 周）

### 目标
理解常见混淆类型，能使用 AST 工具自动化还原混淆代码。

### 学习内容
1. **混淆类型理解**
   - → [混淆类型详解](../02-obfuscation/obfuscation-types.md)
   - 变量名混淆、字符串加密、控制流平坦化、死代码

2. **反混淆工具**
   - → [反混淆工具](../02-obfuscation/deobfuscation-tools.md)
   - de4js 在线工具
   - js-beautify 格式化

3. **AST 反混淆**
   - → [AST 反混淆详解](../02-obfuscation/ast-deobfuscation.md)
   - Babel 工具链使用
   - 自定义 AST 转换脚本
   - 字符串解密、控制流还原、常量折叠

### 练习
- 猿人学第 11-15 题
- 使用 Obfuscator.io 生成混淆代码并还原
- 编写自己的 AST 反混淆脚本

---

## 第四阶段：补环境与高级技术（4-8 周）

### 目标
掌握补环境技术，能处理 WASM、浏览器指纹等高级场景。

### 学习内容
1. **补环境**
   - → [补环境概念与原理](../03-environment/env-simulation-intro.md)
   - → [补环境实战流程](../03-environment/env-simulation-practice.md)
   - → [补环境进阶](../03-environment/env-simulation-advanced.md)
   - → [补环境框架评测](../03-environment/env-frameworks.md)
   - Proxy 检测、node-inspect 调试
   - Canvas / WebGL / AudioContext 指纹模拟

2. **浏览器指纹**
   - → [浏览器指纹对抗](../05-advanced/browser-fingerprint.md)

3. **WASM 逆向**
   - → [WASM 逆向](../05-advanced/wasm-reverse.md)
   - wasm2wat、Ghidra 反编译

4. **RPC 与无头浏览器**
   - → [RPC 远程过程调用](../05-advanced/rpc-technique.md)
   - → [无头浏览器方案](../05-advanced/headless-browser.md)

### 练习
- 猿人学第 16-20 题
- 搭建自己的补环境框架
- WASM 模块逆向练习

---

## 第五阶段：实战案例（持续）

### 目标
通过真实案例积累经验，形成自己的方法论。

### 学习内容
1. **商业防护分析**
   - → [Akamai AST 反混淆实战](../06-case-studies/akamai-ast-deobfuscation.md)
   - → [Reese84 OB 反混淆实战](../06-case-studies/reese84-ob-deobfuscation.md)
   - → [Vercel 盾 WASM 分析](../06-case-studies/vercel-shield-wasm.md)
   - → [电商平台加密实战](../06-case-studies/ecommerce-encryption.md)

2. **滑块验证码**
   - 极验 / 网易易盾 / 腾讯防水墙

3. **进阶混淆**
   - JScrambler / 自定义 VM 保护

### 持续学习
- 关注 K 哥爬虫、宇哥等公众号/博客的最新案例
- 参与安全社区讨论
- 记录和分析新遇到的防护方案

## 学习资源推荐

| 资源 | 类型 | 说明 |
|------|------|------|
| [K 哥爬虫](https://mp.weixin.qq.com/mp/appmsgalbum?__biz=MzkyMzcxMDM0MQ==&scene=1&album_id=3510743371168022537) | 公众号 | JS 逆向百例系列，覆盖面广 |
| [宇哥 JS 逆向](https://juejin.cn/user/1732486056642830) | 掘金 | 体系化教程，入门友好 |
| [JS 逆向完整技能图谱](https://51rexue.cn/blog/50) | 博客 | 工具和技能一站式清单 |
| [猿人学](https://match.yuanrenxue.cn/) | 练习平台 | 专为 JS 逆向设计 |

## 关键要点总结

- 前置知识：JS 基础 + HTTP 协议 + Python 基础
- 五个阶段：基础入门 → Hook/反调试 → 混淆还原 → 补环境/高级 → 实战
- 每个阶段配合对应难度的练习题
- 循序渐进，先理解原理再追求自动化
- 持续关注社区和新技术，逆向技术更新很快

## 相关主题
- → [练习平台](practice-platforms.md)
- → [工具清单](tools-guide.md)
