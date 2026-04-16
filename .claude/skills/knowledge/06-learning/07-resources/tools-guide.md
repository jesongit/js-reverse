# 工具清单

> 来源: [JS逆向完整技能图谱](https://51rexue.cn/blog/50) | [JavaScript逆向工程：原理、技术与实践](https://blog.51cto.com/boss/14102684)

## 概述

JS 逆向工程需要多种工具配合使用。本文按功能分类整理常用工具。

## 抓包工具

### Fiddler
- **用途**：HTTP/HTTPS 抓包、请求修改、断点
- **特点**：
  - Windows 平台
  - 支持脚本扩展（FiddlerScript）
  - 可注入 JS 到响应中
  - AutoResponder 功能重放请求
- **下载**：https://www.telerik.com/fiddler

### Charles
- **用途**：HTTP/HTTPS 抓包、Map/Rewrite
- **特点**：
  - 跨平台（Windows/Mac/Linux）
  - Map Local / Map Remote 功能
  - Rewrite 规则修改请求/响应
  - Throttle 模拟慢速网络
- **下载**：https://www.charlesproxy.com/

### Burp Suite
- **用途**：Web 安全测试、抓包、扫描
- **特点**：
  - 专业安全测试工具
  - Intruder 模块自动化测试
  - Repeater 模块手动重放
  - 插件生态丰富

### mitmproxy
- **用途**：命令行抓包工具
- **特点**：
  - Python 可编程
  - 支持脚本自动化
  - 轻量级，适合 CI/CD 集成
- **安装**：`pip install mitmproxy`

## 浏览器工具

### Chrome DevTools
- 内置开发者工具，逆向核心工具
- → 详见 [浏览器开发者工具](../01-basics/browser-devtools.md)

### Tampermonkey（油猴）
- **用途**：用户脚本管理器
- **特点**：
  - `@run-at document-start` 注入 Hook
  - 管理多脚本
  - 跨站点脚本共享
- **安装**：Chrome Web Store 搜索 "Tampermonkey"

### Chrome 扩展
- **EditThisCookie**：Cookie 编辑管理
- **SwitchyOmega**：代理切换管理
- **JSON Viewer**：JSON 格式化显示

## 反混淆工具

| 工具 | 用途 | 详情 |
|------|------|------|
| de4js | 在线反混淆 | [链接](https://lelinhtinh.github.io/de4js/) |
| AST Explorer | AST 可视化 | [链接](https://astexplorer.net/) |
| JSNice | 变量名还原 | [链接](http://www.jsnice.org/) |
| Babel 工具链 | 自定义 AST 脚本 | `npm install @babel/parser @babel/traverse @babel/generator @babel/types` |
| js-beautify | 代码格式化 | `npm install -g js-beautify` |
| prettier | 代码美化 | `npx prettier --write file.js` |

→ 详见 [反混淆工具](../02-obfuscation/deobfuscation-tools.md)

## 环境模拟工具

| 工具 | 用途 |
|------|------|
| sdenv | 浏览器环境模拟框架 |
| qxVm | VM2 沙箱 + 日志 |
| node-inspect | Node.js 调试 |
| jsdom | DOM 环境模拟 |

→ 详见 [补环境框架评测](../03-environment/env-frameworks.md)

## 自动化工具

### Playwright
```bash
pip install playwright && playwright install
```
- 微软开源，多浏览器支持
- → 详见 [无头浏览器方案](../05-advanced/headless-browser.md)

### Puppeteer
```bash
npm install puppeteer
```
- Google 开源，Chrome 专用

### Selenium
```bash
pip install selenium
```
- 老牌自动化工具，支持多浏览器

## WASM 工具

| 工具 | 用途 |
|------|------|
| wasm2wat | WASM 反汇编为文本格式 |
| wasm-objdump | 查看 WASM 文件结构 |
| Ghidra | 反编译为伪 C 代码 |
| wasmtime | Python 中运行 WASM |

→ 详见 [WASM 逆向](../05-advanced/wasm-reverse.md)

## 加密相关

| 工具/库 | 语言 | 用途 |
|---------|------|------|
| CryptoJS | JS | 前端加密库（最常见） |
| node-forge | JS | RSA/AES/证书 |
| pycryptodome | Python | Python 加密库 |
| hashlib | Python | 哈希算法（内置） |

## 辅助工具

| 工具 | 用途 |
|------|------|
| Postman | API 测试 |
| curl | 命令行 HTTP 请求 |
| jq | JSON 处理 |
| CyberChef | 编码/解码/加密一站式工具 |

## 关键要点总结

- Fiddler/Charles 是日常抓包主力，mitmproxy 适合自动化
- Chrome DevTools + Tampermonkey 是浏览器端的核心组合
- Babel 是自定义 AST 反混淆的唯一选择
- Playwright 是当前推荐的无头浏览器方案
- 工具选择应根据具体场景，不必全部安装

## 相关主题
- → [练习平台](practice-platforms.md)
- → [学习路径](learning-path.md)
