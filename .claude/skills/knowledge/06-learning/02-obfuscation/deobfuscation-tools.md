# 反混淆工具

> 来源: [JS逆向终极指南：混淆特征到解密还原](https://juejin.cn/post/7506324201280946212) | [JS逆向完整技能图谱](https://51rexue.cn/blog/50)

## 概述

反混淆工具可以自动化还原混淆代码，提高分析效率。本文介绍常用的在线工具和本地工具。

## 在线反混淆工具

### 1. de4js
- **地址**：https://lelinhtinh.github.io/de4js/
- **功能**：支持多种混淆类型的自动检测和还原
- **支持类型**：
  - eval / with / Function 解包
  - Array 解密
  - JSFuck / AAEncode / JJEncode
  - JSNice（变量名还原）
  - My Obfuscate（部分）
- **使用**：粘贴代码 → 自动检测类型 → 点击对应按钮还原

### 2. JSNice
- **地址**：http://www.jsnice.org/
- **功能**：基于机器学习还原变量名和函数名
- **特点**：通过分析大量开源代码学习命名模式
- **适用**：变量名混淆的代码

### 3. JStillery
- **地址**：https://mindedsecurity.github.io/jstillery/
- **功能**：基于 AST 的 JS 反混淆
- **特点**：能处理部分复杂的混淆模式

### 4. AST Explorer
- **地址**：https://astexplorer.net/
- **功能**：可视化查看 JS 代码的抽象语法树
- **用途**：分析混淆代码结构，辅助编写 AST 还原脚本
- **支持的解析器**：acorn, babel, espree, TypeScript 等

### 5. UnPacker
- **功能**：解包 eval / document.write 包裹的代码
- **使用**：粘贴编码后的代码，自动解包

### 6. jsdec
- **地址**：https://github.com/rxivman/jsdec
- **功能**：类似 de4js 的本地/在线反混淆工具
- **支持**：Obfuscator.io 常见混淆模式

## 本地工具

### 1. Babel 工具链（推荐）
- **核心库**：`@babel/parser`、`@babel/traverse`、`@babel/generator`、`@babel/types`
- **功能**：自定义 AST 转换脚本，精确控制还原过程
- **优势**：灵活、可编程、适合复杂混淆
- → 详见 [AST 反混淆详解](ast-deobfuscation.md)

### 2. babel-plugin-deobfuscate
- Babel 插件形式的反混淆工具
- 支持常见的 Obfuscator.io 混淆模式

### 3. js-beautify
```bash
npm install -g js-beautify
js-beautify input.js -o output.js
```
- 格式化压缩/混淆代码
- 仅格式化，不做逻辑还原

### 4. prettier
```bash
npx prettier --write input.js
```
- 代码格式化工具
- 配合 AST 还原使用

## 混淆类型 → 工具选择

| 混淆类型 | 推荐工具 |
|----------|---------|
| eval / Function 包裹 | de4js、UnPacker |
| JSFuck / AAEncode / JJEncode | de4js |
| 变量名混淆 | JSNice、手动重命名 |
| 字符串加密数组 | AST 脚本（Babel） |
| 控制流平坦化 | AST 脚本（Babel） |
| 死代码注入 | AST 脚本（Babel） |
| Obfuscator.io 全套 | de4js + AST 脚本组合 |

## 关键要点总结

- de4js 是处理简单混淆的首选在线工具
- 复杂混淆（控制流平坦化、自定义加密）必须使用 AST 方式
- AST Explorer 是理解代码结构的重要辅助工具
- 实际逆向中通常是工具 + 手动分析结合
- Babel 工具链是编写自定义还原脚本的核心

## 相关主题
- → [混淆类型详解](obfuscation-types.md)
- → [AST 反混淆详解](ast-deobfuscation.md)
