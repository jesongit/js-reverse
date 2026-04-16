# 练习平台

> 来源: [JS逆向完整技能图谱](https://51rexue.cn/blog/50) | [JavaScript逆向工程：原理、技术与实践](https://blog.51cto.com/boss/14102684)

## 概述

系统化的练习是掌握 JS 逆向的关键。本文整理了常用的逆向练习平台，从入门到进阶。

## 综合练习平台

### 1. 猿人学（推荐入门）
- **地址**：https://match.yuanrenxue.cn/
- **特点**：
  - 专为 JS 逆向设计的练习平台
  - 题目由易到难，循序渐进
  - 覆盖：Base64、MD5、时间戳、混淆、Cookie、字体反爬、WASM 等
  - 提供排行榜和社区讨论
- **适合**：入门到进阶

### 2. 极验（GeeTest）
- **地址**：https://www.geetest.com/
- **特点**：
  - 验证码安全领域的标杆
  - 提供滑块、点选、文字验证码
  - 滑块逆向的经典练习目标
- **适合**：验证码逆向专项练习

### 3. CTF 平台

#### CTFHub
- **地址**：https://www.ctfhub.com/
- **特点**：综合 CTF 平台，包含 Web 方向的 JS 逆向题

#### Bugku CTF
- **地址**：https://ctf.bugku.com/
- **特点**：入门级 CTF 题目，适合新手

#### 攻防世界
- **地址**：https://adworld.xctf.org.cn/
- **特点**： XCTF 赛事官方平台，题目质量高

## 专项练习

### 混淆还原练习
- **Obfuscator.io**：https://obfuscator.io/ — 自己生成混淆代码练习还原
- **JSFuck**：http://www.jsfuck.com/ — 练习 JSFuck 解码
- **de4js**：https://lelinhtinh.github.io/de4js/ — 对照验证还原结果

### 算法识别练习
- 使用上述平台中涉及加密的题目
- 练习通过魔数快速识别算法类型
- → 参考 [加密算法识别](../04-algorithms/crypto-identification.md)

### 补环境练习
- 选择依赖浏览器环境的题目
- 练习从零搭建 Node.js 补环境
- 逐步补齐 window / document / navigator / Canvas 等

### 反调试练习
- 选择有反调试保护的网站
- 练习绕过无限 debugger、DevTools 检测
- → 参考 [反调试技术](../05-advanced/anti-debugging.md)

## 实战项目建议

### 入门级（1-2 周每个）
1. Base64 编码参数还原
2. 简单 MD5 签名还原
3. 时间戳 + 随机数防重放绕过
4. 简单变量名混淆还原

### 中级（2-4 周每个）
1. AES 加密参数还原（找到 key/iv）
2. RSA 公钥加密还原
3. Obfuscator.io 混淆还原（字符串加密 + 控制流平坦化）
4. Cookie 加密生成逻辑还原

### 高级（1-2 月每个）
1. AST 自动化反混淆脚本编写
2. 补环境框架搭建
3. WASM 加密模块逆向
4. 滑块验证码逆向
5. Akamai / Vercel 盾等商业防护绕过

## 学习建议

1. **循序渐进**：从猿人学第 1 题开始，逐题攻克
2. **先手动后自动**：先手动分析理解原理，再考虑自动化脚本
3. **记录笔记**：每道题记录分析过程和关键步骤
4. **对比验证**：始终与浏览器行为对比验证结果
5. **关注社区**：参考他人思路但不直接抄答案

## 关键要点总结

- 猿人学是最推荐的 JS 逆向专项练习平台
- CTF 平台适合综合安全能力提升
- Obfuscator.io 可自行生成混淆代码练习
- 从入门到高级：编码 → 加密 → 混淆 → 补环境 → WASM
- 记录和总结是提升效率的关键

## 相关主题
- → [工具清单](tools-guide.md)
- → [学习路径](learning-path.md)
