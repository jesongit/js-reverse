# 反调试技术

> 来源: [JS逆向完整技能图谱](https://51rexue.cn/blog/50) | [JavaScript逆向工程：原理、技术与实践](https://blog.51cto.com/boss/14102684)

## 概述

反调试技术是网站用来检测和阻止开发者工具调试的手段。了解这些技术才能有效绕过，顺利进行逆向分析。

## 常见反调试手段

### 1. 无限 debugger

最常见的反调试方式：

```javascript
// 方式 1：直接 debugger 语句
(function() {
    setInterval(function() {
        debugger;
    }, 100);
})();

// 方式 2：Function 构造器
setInterval(function() {
    (function() { return false; })['constructor']('debugger')['call']();
}, 100);

// 方式 3：eval
setInterval('debugger', 100);
```

**绕过方法**：

方法 A：Sources 面板 → 右键 debugger 行 → "Never pause here"

方法 B：Hook 定时器
```javascript
// 清除所有定时器
for (var i = 1; i < 99999; i++) {
    clearInterval(i);
    clearTimeout(i);
}

// Hook setInterval 阻止新的 debugger
var originalSetInterval = window.setInterval;
window.setInterval = function(fn, delay) {
    if (fn.toString().indexOf('debugger') !== -1) {
        return; // 不执行包含 debugger 的定时器
    }
    return originalSetInterval.apply(this, arguments);
};
```

方法 C：禁用所有断点（Deactivate breakpoints）后让代码跑过 debugger

### 2. DevTools 检测

#### console.log 检测
```javascript
// 网站检测方式
var element = new Image();
Object.defineProperty(element, 'id', {
    get: function() {
        // DevTools 打开时会触发 getter
        console.log('DevTools detected!');
    }
});
console.log(element);
```

#### 窗口尺寸检测
```javascript
// 检测 DevTools 是否打开（通过窗口大小差异）
setInterval(function() {
    var widthThreshold = window.outerWidth - window.innerWidth > 160;
    var heightThreshold = window.outerHeight - window.innerHeight > 160;
    if (widthThreshold || heightThreshold) {
        console.log('DevTools detected!');
        document.body.innerHTML = ''; // 清空页面
    }
}, 1000);
```

#### console 检测
```javascript
// 检测 console 是否被使用
var devtools = /./;
devtools.toString = function() {
    this.isOpened = true;
};
console.log('%c', devtools);
if (devtools.isOpened) {
    // DevTools 已打开
}
```

**绕过方法**：
```javascript
// 重写检测函数
Object.defineProperty(window, 'outerHeight', { get: () => window.innerHeight });
Object.defineProperty(window, 'outerWidth', { get: () => window.innerWidth });
```

### 3. 时间差检测

```javascript
// 网站检测方式
var start = performance.now();
debugger;  // 如果 DevTools 打开，这里会暂停，时间差会很大
var end = performance.now();
if (end - start > 100) {
    console.log('Debugger detected!');
    // 触发反调试措施
}
```

**绕过方法**：
```javascript
// Hook performance.now
var originalNow = performance.now.bind(performance);
performance.now = function() {
    return originalNow(); // 始终返回正常时间
};
```

### 4. 代码完整性检测

```javascript
// 检测代码是否被修改
function checkIntegrity() {
    var originalCode = checkIntegrity.toString();
    if (originalCode !== expectedCode) {
        // 代码被修改（可能被断点/Hook）
        document.body.innerHTML = '';
    }
}
```

### 5. 堆栈追踪检测

```javascript
// 检测调用栈深度（调试时栈会更深）
function checkCallStack() {
    var stack = new Error().stack;
    if (stack.split('\n').length > expectedDepth) {
        // 可能在调试中
    }
}
```

### 6. 禁用右键和快捷键

```javascript
// 禁用 F12 和右键
document.oncontextmenu = function() { return false; };
document.onkeydown = function(e) {
    if (e.keyCode === 123) { return false; }  // F12
    if (e.ctrlKey && e.shiftKey && e.keyCode === 73) { return false; }  // Ctrl+Shift+I
};
```

**绕过**：直接使用浏览器菜单打开 DevTools，或使用快捷键前先禁用事件监听。

## 通用绕过策略

### 策略 1：注入优先
在 Sources → Snippets 中准备绕过脚本，在页面加载前执行。

### 策略 2：Tampermonkey
```javascript
// ==UserScript==
// @name         Anti-Debug Bypass
// @run-at       document-start
// @match        *://*/*
// ==/UserScript==

// Hook Function 构造器
var originalFunction = Function.prototype.constructor;
Function.prototype.constructor = function() {
    if (arguments[0] === 'debugger') {
        return function() {};
    }
    return originalFunction.apply(this, arguments);
};
```

### 策略 3：浏览器扩展
使用 Chrome 扩展如 "Anti-Redirect"、"Tampermonkey" 等在页面加载前注入绕过代码。

## 关键要点总结

- 无限 debugger 最常见，用 "Never pause here" 或 Hook 定时器绕过
- DevTools 检测通过窗口尺寸/console 行为判断，Hook 对应属性绕过
- 时间差检测通过 performance.now() 判断，Hook now() 方法绕过
- 所有绕过应在 `document-start` 阶段注入
- Tampermonkey 是最通用的注入方案

## 相关主题
- → [Hook 技术](../01-basics/hook-techniques.md)
- → [浏览器开发者工具](../01-basics/browser-devtools.md)
