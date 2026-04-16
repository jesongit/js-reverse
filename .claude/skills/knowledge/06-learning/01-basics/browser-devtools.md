# 浏览器开发者工具 & 断点调试

> 来源: [JS逆向完整技能图谱](https://51rexue.cn/blog/50) | [JavaScript逆向工程：原理、技术与实践](https://blog.51cto.com/boss/14102684)

## 概述

浏览器开发者工具（DevTools）是 JS 逆向工程中最基础、最重要的工具。熟练掌握断点调试是定位加密逻辑的核心能力。

## 核心面板功能

### Elements（元素面板）
- 查看/编辑 DOM 结构和 CSS 样式
- 实时修改页面元素，观察变化
- 检查事件监听器（Event Listeners 标签）

### Console（控制台面板）
- 执行任意 JS 代码
- 查看对象属性和方法：`console.dir(obj)`
- 监听表达式变化：`monitorEvents(element)`
- 输出调用栈：`console.trace()`

### Network（网络面板）
- 捕获所有 HTTP 请求（XHR / Fetch / Script / Document）
- 查看请求头、响应体、Cookie
- 按 URL / 类型 / 状态码过滤请求
- **关键操作**：右键请求 → "Copy as fetch/cURL" 可直接复现请求

### Sources（源代码面板）
- 查看、搜索、断点调试 JS 源码
- 支持 Pretty Print（`{}`按钮）格式化压缩代码
- Snippets 功能：保存并执行常用脚本
- **核心调试功能**：断点、单步执行、Watch 表达式

### Application（应用面板）
- 查看 / 编辑 Cookie、localStorage、sessionStorage
- 查看 IndexedDB、Cache Storage
- 分析 Service Worker 注册状态

## 五种断点类型

### 1. 普通断点（Breakpoint）
- 在 Sources 面板点击行号设置
- 程序执行到此处暂停

### 2. 条件断点（Conditional Breakpoint）
- 右键行号 → "Add conditional breakpoint"
- 仅当条件为 `true` 时暂停
- 适用于循环中定位特定值：`index === 42`

### 3. XHR 断点（XHR/Fetch Breakpoint）
- Sources 面板右侧 → XHR Breakpoints → 添加 URL 关键词
- 当 XHR/Fetch 请求的 URL 包含关键词时暂停
- **最常用**：输入加密接口的 URL 路径关键词，直接定位发送请求的代码

### 4. DOM 断点（DOM Breakpoint）
- Elements 面板 → 右键元素 → "Break on"
  - subtree modifications：子树修改时断下
  - attribute modifications：属性修改时断下
  - node removal：节点移除时断下
- 适用于 DOM 动态变化的场景

### 5. 事件监听断点（Event Listener Breakpoint）
- Sources 面板右侧 → Event Listener Breakpoints
- 可按事件类型设置：click / keydown / load / timer 等
- 触发指定事件时暂停执行

## 调试操作

| 快捷键 | 操作 | 说明 |
|--------|------|------|
| F8 | 继续/暂停 | 恢复执行或暂停 |
| F10 | Step Over | 单步跳过（不进入函数） |
| F11 | Step Into | 单步进入（进入函数内部） |
| Shift+F11 | Step Out | 跳出当前函数 |
| Ctrl+P | 快速打开文件 | 搜索源文件 |
| Ctrl+Shift+F | 全局搜索 | 在所有源文件中搜索 |
| Ctrl+G | 跳转到行 | 快速定位行号 |

## 调试流程最佳实践

1. **Network 面板定位目标请求** → 找到包含加密参数的接口
2. **XHR 断点** → 输入接口 URL 关键词
3. **触发请求** → 在发送请求处断下
4. **查看 Call Stack** → 从栈顶向下追踪加密逻辑
5. **在关键函数设置断点** → 重新触发，逐步分析
6. **Watch 表达式** → 实时监控关键变量值

## 关键要点总结

- XHR 断点是定位加密逻辑最高效的方式
- 善用条件断点减少无效暂停
- 调试时关注 Call Stack 中的函数调用链
- Sources 面板 Snippets 可保存常用脚本（如 Hook 代码）
- Pretty Print 格式化是阅读压缩代码的第一步

## 相关主题
- → [搜索定位技巧](search-locate.md)
- → [Hook 技术](hook-techniques.md)
- → [反调试对抗](../05-advanced/anti-debugging.md)
