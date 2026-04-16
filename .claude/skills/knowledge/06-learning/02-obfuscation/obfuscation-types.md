# 混淆类型详解

> 来源: [JS逆向终极指南：混淆特征到解密还原](https://juejin.cn/post/7506324201280946212) | [JavaScript逆向工程：原理、技术与实践](https://blog.51cto.com/boss/14102684)

## 概述

代码混淆是保护 JS 代码的常用手段，理解混淆类型是逆向分析的第一步。本文介绍 5 种常见混淆类型及其特征。

## 1. 变量名混淆（Variable Obfuscation）

### 特征
- 将有意义的变量名替换为无意义字符
- 使用十六进制或 Unicode 编码

### 示例
```javascript
// 混淆前
function encrypt(text, key) {
    return text + key;
}

// 混淆后
function _0x3a2f(_0x1b4c, _0x2d5e) {
    return _0x1b4c + _0x2d5e;
}
```

### 识别特征
- 变量名以 `_0x` 开头
- 十六进制格式的变量名
- 常见于 Obfuscator.io 等工具的输出

## 2. 字符串加密（String Encryption）

### 特征
- 将明文字符串加密为数组或编码
- 运行时解密还原
- 通常配合解密函数使用

### 常见形式

#### 数组 + 旋转（Array Rotation）
```javascript
var _0x4a5b = ['encrypt', 'password', 'token', 'sha256'];
(function(_0x2f3d, _0x4e5f) {
    // 数组旋转函数
    var _0x1a2b = function(i) {
        while (--i) {
            _0x2f3d.push(_0x2f3d.shift());
        }
    };
    _0x1a2b(++_0x4e5f);
})(_0x4a5b, 0x1a2);

// 使用时通过解密函数获取
var str = _0x4a5b[0]; // 实际获取的是旋转后的值
```

#### Base64 编码
```javascript
var _0x = atob('ZW5jcnlwdA=='); // "encrypt"
```

#### RC4 / 自定义加密
```javascript
function _0xdecrypt(key, encrypted) {
    // RC4 或自定义解密逻辑
    return decrypted_string;
}
```

## 3. 控制流平坦化（Control Flow Flattening）

### 特征
- 将代码的正常控制流打乱
- 使用 switch-case + 状态变量重排执行顺序
- 严重影响代码可读性

### 示例
```javascript
// 混淆前
function calc(a, b) {
    var x = a + b;
    var y = x * 2;
    return y + 1;
}

// 控制流平坦化后
function calc(a, b) {
    var _0xstate = '3|1|2|0';
    var arr = _0xstate.split('|');
    var i = 0;
    while (true) {
        switch (arr[i++]) {
            case '0': return y + 1;
            case '1': var x = a + b; continue;
            case '2': var y = x * 2; continue;
            case '3': var y; continue;
        }
        break;
    }
}
```

### 识别特征
- `while(true) { switch }` 结构
- 状态变量通常是字符串 `'|'` 分隔
- 执行顺序被打乱

## 4. 死代码注入（Dead Code Injection）

### 特征
- 插入永远不会执行的代码
- 干扰阅读和分析

### 示例
```javascript
function encrypt(data) {
    if (false) {
        // 死代码：永远不会执行
        var dummy = someFunction();
        console.log(dummy);
    }
    // 实际逻辑
    return realEncrypt(data);
}
```

### 识别特征
- `if (false)` 或 `if (0)` 包裹的代码块
- 未使用的变量声明
- 不可达的 return 语句

## 5. eval 动态执行

### 特征
- 将代码以字符串形式存储
- 运行时通过 eval / Function / setTimeout 执行
- 增加静态分析难度

### 常见形式
```javascript
// eval 执行
eval('function secret() { ... }');

// Function 构造器
new Function('return ' + encoded_code)();

// setTimeout/setInterval 字符串形式
setTimeout('malicious_code()', 100);

// JSFuck 编码
[][(![]+[])[+[]]+([![]]+[][[]])[+!+[]+[+[]]]+...]

// 隐写术
atob('ZnVuY3Rpb24gc2VjcmV0KCkgeyAuLi4gfQ==')
```

## 常见混淆工具识别

| 工具 | 特征 |
|------|------|
| Obfuscator.io | `_0x` 变量名、数组旋转、控制流平坦化 |
| JScrambler | 字符串提取、域名锁定、日期限制 |
| JSFuck | 仅使用 `[]()!+` 六个字符 |
| AAEncode | 使用颜文字字符 |
| JJEncode | 使用 `$` 符号为主 |
| Eval 加密 | 整体包裹在 eval() 或 Function() 中 |

## 关键要点总结

- 变量名混淆最常见但不影响功能，可忽略或使用 IDE 重命名
- 字符串加密通常有对应的解密函数，找到解密函数是关键
- 控制流平坦化通过分析 switch-case 的状态序列可还原执行顺序
- 死代码可安全删除，不影响程序逻辑
- eval 动态执行需要在运行时拦截或替换

## 相关主题
- → [反混淆工具](deobfuscation-tools.md)
- → [AST 反混淆详解](ast-deobfuscation.md)
- → [Akamai AST 反混淆实战](../06-case-studies/akamai-ast-deobfuscation.md)
