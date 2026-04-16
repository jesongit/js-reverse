# Hook 技术

> 来源: [JS逆向完整技能图谱](https://51rexue.cn/blog/50) | [JavaScript逆向工程：原理、技术与实践](https://blog.51cto.com/boss/14102684)

## 概述

Hook（钩子）是 JS 逆向中的核心定位技术，通过拦截、修改或监听原生对象的方法和属性，快速定位加密函数的调用位置。

## 核心 Hook 方式

### 1. JSON.stringify / JSON.parse Hook

定位数据序列化/反序列化的位置：

```javascript
// Hook JSON.stringify
(function() {
    const originalStringify = JSON.stringify;
    JSON.stringify = function() {
        console.log('JSON.stringify called with:', arguments);
        console.trace('Call Stack:');
        debugger; // 断点
        return originalStringify.apply(this, arguments);
    };
})();

// Hook JSON.parse
(function() {
    const originalParse = JSON.parse;
    JSON.parse = function() {
        console.log('JSON.parse called with:', arguments[0]);
        console.trace('Call Stack:');
        debugger;
        return originalParse.apply(this, arguments);
    };
})();
```

### 2. Cookie Hook

通过 `Object.defineProperty` 劫持 Cookie 的读写：

```javascript
// Cookie 写入 Hook
(function() {
    const originalDescriptor =
        Object.getOwnPropertyDescriptor(Document.prototype, 'cookie') ||
        Object.getOwnPropertyDescriptor(HTMLDocument.prototype, 'cookie');

    if (originalDescriptor && originalDescriptor.set) {
        Object.defineProperty(document, 'cookie', {
            get: function() {
                return originalDescriptor.get.call(this);
            },
            set: function(value) {
                console.log('Cookie Setting:', value);
                console.trace('Call Stack:');
                debugger;
                originalDescriptor.set.call(this, value);
            }
        });
    }
})();
```

### 3. 定时器 Hook（setInterval / setTimeout）

某些反调试或加密函数通过定时器执行：

```javascript
// Hook setTimeout
(function() {
    const originalSetTimeout = window.setTimeout;
    window.setTimeout = function(fn, delay) {
        console.log('setTimeout called, delay:', delay);
        if (typeof fn === 'function') {
            console.log('Function:', fn.toString().substring(0, 200));
        }
        return originalSetTimeout.apply(this, arguments);
    };
})();
```

### 4. eval Hook

拦截 eval 动态代码执行：

```javascript
(function() {
    const originalEval = window.eval;
    window.eval = function(code) {
        console.log('eval called with:', code.substring(0, 500));
        console.trace();
        debugger;
        return originalEval.call(this, code);
    };
})();
```

### 5. XMLHttpRequest / Fetch Hook

监控所有网络请求：

```javascript
// XHR Hook
(function() {
    const originalOpen = XMLHttpRequest.prototype.open;
    const originalSend = XMLHttpRequest.prototype.send;

    XMLHttpRequest.prototype.open = function(method, url) {
        this._url = url;
        this._method = method;
        console.log('XHR Open:', method, url);
        return originalOpen.apply(this, arguments);
    };

    XMLHttpRequest.prototype.send = function(body) {
        console.log('XHR Send:', this._method, this._url);
        console.log('Body:', body);
        return originalSend.apply(this, arguments);
    };
})();

// Fetch Hook
(function() {
    const originalFetch = window.fetch;
    window.fetch = function() {
        console.log('Fetch:', arguments[0]);
        console.trace();
        return originalFetch.apply(this, arguments);
    };
})();
```

### 6. Console Hook（反调试对抗）

某些网站检测 console 是否打开：

```javascript
// 干扰 console.log 检测
Object.defineProperty(window, 'console', {
    get: function() {
        return {}; // 返回空对象，使检测失效
    }
});
```

## Hook 注入方式

### 方式 1：Console 直接注入
- 在 Sources → Snippets 中创建脚本
- 或直接在 Console 中粘贴执行
- **缺点**：页面刷新后失效

### 方式 2：Tampermonkey 油猴脚本
- 安装 Tampermonkey 浏览器扩展
- 创建用户脚本，设置 `@run-at document-start`
- 确保在页面 JS 执行前注入

```javascript
// ==UserScript==
// @name         JSON Hook
// @namespace    http://tampermonkey.net/
// @version      1.0
// @run-at       document-start
// @match        *://target-site.com/*
// ==/UserScript==

(function() {
    const originalStringify = JSON.stringify;
    JSON.stringify = function() {
        console.log('Hooked JSON.stringify:', arguments);
        return originalStringify.apply(this, arguments);
    };
})();
```

### 方式 3：Fiddler / Charles 代理注入
- 设置代理拦截响应
- 在 HTML 中注入 `<script>` 标签
- **优点**：可注入到任何页面，包括 iframe

### 方式 4：浏览器插件
- 开发自定义 Chrome Extension
- 使用 `content_scripts` + `run_at: "document_start"`
- 最灵活，可配合 DevTools API

## 关键要点总结

- `Object.defineProperty` 是最底层、最可靠的属性 Hook 方式
- 始终保存原始方法引用，Hook 函数内调用原始方法保证正常逻辑
- `@run-at document-start` 确保在页面脚本执行前注入
- `debugger` 语句配合 `console.trace()` 实现断点 + 调用栈
- 多个 Hook 可组合使用，逐步缩小定位范围

## 相关主题
- → [浏览器开发者工具](browser-devtools.md)
- → [搜索定位技巧](search-locate.md)
- → [反调试对抗](../05-advanced/anti-debugging.md)
