# 补环境实战流程

> 来源: [JavaScript逆向的补环境入门](https://juejin.cn/post/7547933350213828660) | [JS逆向完整技能图谱](https://51rexue.cn/blog/50)

## 概述

补环境实战中，需要逐步发现缺失的环境对象并补齐。本文介绍使用 Proxy 检测、node-inspect 调试等工具的具体操作流程。

## 工具准备

### node-inspect 调试工具

```bash
# 安装
npm install -g node-inspect

# 启动调试
node inspect your_script.js
```

常用调试命令：
| 命令 | 说明 |
|------|------|
| `c` / `cont` | 继续执行 |
| `n` / `next` | 单步跳过 |
| `s` / `step` | 单步进入 |
| `o` / `out` | 跳出函数 |
| `sb('file.js', line)` | 设置断点 |
| `repl` | 进入交互模式，可执行表达式 |
| `.exit` | 退出调试 |

### MDN Web Docs
- **地址**：https://developer.mozilla.org/zh-CN/
- **用途**：查阅浏览器 API 的标准行为和返回值
- 补环境时需要参考 MDN 确保模拟行为一致

## Proxy 环境检测

使用 Proxy 自动检测被访问但未定义的属性：

```javascript
// 创建 Proxy 检测器
function createProxy(target, name = 'window') {
    return new Proxy(target, {
        get(target, prop) {
            if (prop in target) {
                return target[prop];
            }
            console.log(`[检测] ${name}.${String(prop)} 被访问，但未定义`);
            console.trace('访问位置:');
            return undefined;
        },
        set(target, prop, value) {
            console.log(`[检测] ${name}.${String(prop)} 被设置为:`, value);
            target[prop] = value;
            return true;
        }
    });
}

// 应用到全局对象
global.window = createProxy({}, 'window');
global.document = createProxy({}, 'document');
global.navigator = createProxy({}, 'navigator');
```

## 实战补环境流程

### Step 1：搭建基础框架

```javascript
// env.js - 基础环境文件

// 1. 基础 window
const window = {
    self: null,
    top: null,
    parent: null,
    frames: null,
    outerHeight: 824,
    outerWidth: 1536,
    innerWidth: 1536,
    innerHeight: 716,
    screenX: 0,
    screenY: 0,
    chrome: {},
    setTimeout: setTimeout,
    setInterval: setInterval,
    clearTimeout: clearTimeout,
    clearInterval: clearInterval,
    atob: function(str) { return Buffer.from(str, 'base64').toString(); },
    btoa: function(str) { return Buffer.from(str).toString('base64'); }
};
window.self = window;
window.top = window;
window.parent = window;
window.frames = window;
global.window = window;

// 2. document
const document = {
    createElement: function(tag) { return { tagName: tag.toUpperCase(), style: {} }; },
    getElementById: function() { return null; },
    getElementsByTagName: function() { return []; },
    querySelector: function() { return null; },
    querySelectorAll: function() { return []; },
    cookie: '',
    referrer: '',
    title: '',
    domain: '',
    URL: 'https://www.example.com/',
    body: { appendChild: function() {} },
    documentElement: { style: {} },
    head: {},
    readyState: 'complete'
};
global.document = document;

// 3. navigator
global.navigator = {
    userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    platform: 'Win32',
    language: 'zh-CN',
    languages: ['zh-CN', 'zh', 'en'],
    plugins: { length: 5 },
    cookieEnabled: true,
    hardwareConcurrency: 8,
    maxTouchPoints: 0,
    vendor: 'Google Inc.',
    appVersion: '5.0 (Windows NT 10.0; Win64; x64)',
    appName: 'Netscape',
    product: 'Gecko',
    productSub: '20030107'
};

// 4. location
global.location = {
    href: 'https://www.example.com/',
    origin: 'https://www.example.com',
    protocol: 'https:',
    host: 'www.example.com',
    hostname: 'www.example.com',
    port: '',
    pathname: '/',
    search: '',
    hash: ''
};

// 5. screen
global.screen = {
    width: 1920,
    height: 1080,
    availWidth: 1920,
    availHeight: 1040,
    colorDepth: 24,
    pixelDepth: 24
};
```

### Step 2：运行目标 JS 并收集报错

```bash
node target.js
# 或使用调试模式
node inspect target.js
```

常见报错类型：
```
TypeError: Cannot read property 'xxx' of undefined
ReferenceError: xxx is not defined
TypeError: xxx is not a function
```

### Step 3：根据报错逐步补齐

```
报错: Cannot read property 'userAgent' of undefined
原因: navigator 未定义
修复: 添加 navigator 对象

报错: document.createElement is not a function
原因: createElement 方法未正确模拟
修复: 补充 createElement 实现

报错: Cannot read property 'toDataURL' of null
原因: Canvas 2D Context 未模拟
修复: 添加 Canvas 环境补齐
```

### Step 4：验证结果正确性

```javascript
// 对比浏览器执行结果和 Node.js 执行结果
const browserResult = '...'; // 浏览器中获取的加密结果
const nodeResult = encrypt(params); // Node.js 中执行结果
console.log(browserResult === nodeResult); // 应为 true
```

## 常见坑点

### 1. toString 检测
```javascript
// 网站检测函数是否被修改
navigator.userAgent.toString();  // 期望 "Mozilla/5.0..."
String(navigator.userAgent);      // 同上

// 正确补法
Object.defineProperty(navigator, 'userAgent', {
    value: 'Mozilla/5.0 ...',
    writable: false,
    configurable: true
});
```

### 2. 原型链检测
```javascript
// 检测对象的原型链
document.createElement('div') instanceof HTMLElement; // 需要完整的原型链
```

### 3. 属性描述符检测
```javascript
// 检测属性是否为原生
Object.getOwnPropertyDescriptor(window, 'chrome');
// 需要正确的 configurable/writable/enumerable 设置
```

### 4. 顺序依赖
- 某些环境对象的初始化有先后顺序
- 通常顺序：window → document → navigator → location → screen

## 关键要点总结

- 使用 Proxy 自动检测缺失的环境属性
- 从报错信息出发，逐步补齐
- 参考 MDN 确保模拟行为的正确性
- 注意 toString、原型链、属性描述符等高级检测
- 补完后对比浏览器和 Node.js 的输出验证正确性

## 相关主题
- → [补环境概念与原理](env-simulation-intro.md)
- → [补环境进阶](env-simulation-advanced.md)
- → [补环境框架评测](env-frameworks.md)
