# 补环境概念与原理

> 来源: [JavaScript逆向的补环境入门](https://juejin.cn/post/7547933350213828660) | [JS逆向完整技能图谱](https://51rexue.cn/blog/50)

## 概述

"补环境"是指在 Node.js 等非浏览器环境中运行被保护的 JS 代码时，模拟浏览器提供的环境对象（window、document、navigator 等），使代码能够正常执行并产出正确结果。

## 为什么需要补环境

### 浏览器环境差异
- 浏览器提供大量全局对象：`window`、`document`、`navigator`、`location`、`screen`、`history`
- Node.js 环境中没有这些对象
- 加密代码通常依赖这些对象进行环境检测

### 环境检测机制
网站通过检测浏览器环境特征来判断是否在真实浏览器中运行：

```javascript
// 常见环境检测
typeof window !== 'undefined';           // window 对象检测
navigator.userAgent;                      // UA 检测
document.createElement('canvas');         // DOM 检测
window.chrome;                            // Chrome 特征检测
navigator.plugins.length;                 // 插件检测
screen.width;                             // 屏幕信息
window.outerHeight;                       // 窗口尺寸
```

### 检测失败后果
- 返回错误的加密结果
- 触发反爬虫机制
- 程序直接报错退出

## 补环境 vs 扣代码

| 方式 | 优点 | 缺点 |
|------|------|------|
| **扣代码** | 体积小，精准提取 | 耗时长，容易遗漏依赖 |
| **补环境** | 直接运行整段代码，效率高 | 需要模拟大量环境对象 |
| **纯算法** | 性能最优，无依赖 | 难度最高，需要完全理解算法 |

## 核心补环境对象

### 1. window 对象
```javascript
// Node.js 中创建全局 window
global.window = global;

// 常见需要补的属性
window.self = window;
window.top = window;
window.parent = window;
window.frames = window;
window.outerHeight = 824;
window.outerWidth = 1536;
window.innerWidth = 1536;
window.innerHeight = 824;
```

### 2. document 对象
```javascript
// 基础 document 补齐
const document = {
    createElement: function(tag) { /* ... */ },
    getElementById: function(id) { /* ... */ },
    getElementsByTagName: function(tag) { /* ... */ },
    querySelector: function(sel) { /* ... */ },
    cookie: '',
    referrer: '',
    title: '',
    domain: '',
    URL: '',
    body: {},
    documentElement: {},
    head: {}
};
global.document = document;
```

### 3. navigator 对象
```javascript
const navigator = {
    userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 ...',
    platform: 'Win32',
    language: 'zh-CN',
    languages: ['zh-CN', 'zh', 'en'],
    plugins: { length: 5 },
    cookieEnabled: true,
    hardwareConcurrency: 8,
    maxTouchPoints: 0,
    vendor: 'Google Inc.'
};
global.navigator = navigator;
```

### 4. location 对象
```javascript
const location = {
    href: 'https://www.example.com/page',
    origin: 'https://www.example.com',
    protocol: 'https:',
    host: 'www.example.com',
    hostname: 'www.example.com',
    port: '',
    pathname: '/page',
    search: '',
    hash: ''
};
global.location = location;
```

## 补环境的层次

### 第一层：基础对象
- window / document / navigator / location / screen / history

### 第二层：DOM API
- createElement / appendChild / getAttribute
- Element / HTMLElement / Node 原型链

### 第三层：高级 API
- Canvas 2D Context
- WebGL Context
- AudioContext
- IntersectionObserver
- MutationObserver

### 第四层：指纹对抗
- Canvas 指纹返回值
- WebGL 渲染器信息
- AudioContext 指纹
- 字体列表

## 关键要点总结

- 补环境的本质是让 JS 代码"以为"自己在浏览器中运行
- 核心对象：window / document / navigator / location
- 分层次补齐：基础对象 → DOM API → 高级 API → 指纹对抗
- 与扣代码方式互补，根据场景选择合适方式
- 补环境的质量直接影响加密结果的正确性

## 相关主题
- → [补环境实战流程](env-simulation-practice.md)
- → [补环境进阶](env-simulation-advanced.md)
- → [补环境框架评测](env-frameworks.md)
