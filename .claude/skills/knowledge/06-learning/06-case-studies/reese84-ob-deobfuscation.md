# Reese84 OB 混淆处理实战

> 来源: [AST反混淆处理示例（二）](https://juejin.cn/post/7583234966635003938)

## 概述

Reese84 是一种常见的 JS 保护方案，使用 OB（Obfuscator）混淆 + eval 动态加载。本文介绍通过调试定位解密函数、AST 处理字符串拼接的实战方法。

## Reese84 混淆特征

### 1. eval 动态加载
```javascript
// Reese84 使用 eval 加载核心代码
eval(function(p, a, c, k, e, d) {
    // ...
}('packed_code', 62, 500, '...', '|', ...));
```

### 2. OB 混淆结构
```javascript
// 典型 OB 混淆特征
var _0x5a4b = ['string1', 'string2', ...];
(function(_0x3c2d, _0x4e5f) {
    // 数组旋转
    var _0x1a2b = function(i) {
        while (--i) _0x3c2d.push(_0x3c2d.shift());
    };
    _0x1a2b(++_0x4e5f);
})(_0x5a4b, 0x1a2);

// 解密函数
function _0x4c5d(hash, key) {
    // RC4 或自定义解密
    return decrypted_string;
}
```

### 3. 字符串拼接
```javascript
// 混淆后的字符串拼接
var _0x1 = _0x4c5d('0x1', 'abcd');
var _0x2 = _0x4c5d('0x2', 'efgh');
var url = _0x1 + _0x2 + '/api/encrypt';
```

## 逆向流程

### Step 1：获取完整代码

```javascript
// Hook eval 获取解密后的代码
var originalEval = eval;
eval = function(code) {
    console.log('Eval code length:', code.length);
    // 保存到文件分析
    require('fs').writeFileSync('reese84_decrypted.js', code);
    return originalEval.call(this, code);
};
```

### Step 2：定位解密函数

通过调试找到字符串解密函数：

1. 在 OB 混淆的数组旋转函数处设断点
2. 在解密函数 `_0x4c5d` 处设断点
3. 观察输入参数和输出值

```javascript
// 调试解密函数
function _0x4c5d(hash, key) {
    debugger;  // 断点
    var result = /* 解密逻辑 */;
    console.log(hash, key, '->', result);
    return result;
}
```

### Step 3：提取解密映射

```javascript
// 执行解密函数，收集所有映射
var mapping = {};
var originalDecrypt = _0x4c5d;

_0x4c5d = function(hash, key) {
    var value = originalDecrypt(hash, key);
    mapping[hash + '|' + key] = value;
    return value;
};

// 运行主代码，触发所有解密调用
// ...

// 输出映射表
console.log(JSON.stringify(mapping, null, 2));
```

### Step 4：AST 处理字符串拼接

```javascript
// 还原字符串拼接
// "_0x1 + _0x2 + '/api'" → "完整URL"

const parser = require('@babel/parser');
const traverse = require('@babel/traverse').default;
const generate = require('@babel/generator').default;
const t = require('@babel/types');

const ast = parser.parse(code);

// 第一趟：替换解密函数调用为明文字符串
traverse(ast, {
    CallExpression(path) {
        if (t.isIdentifier(path.node.callee, { name: '_0x4c5d' })) {
            const hash = path.node.arguments[0].value;
            const key = path.node.arguments[1].value;
            const realValue = mapping[hash + '|' + key];
            if (realValue) {
                path.replaceWith(t.stringLiteral(realValue));
            }
        }
    }
});

// 第二趟：合并字符串拼接
traverse(ast, {
    BinaryExpression(path) {
        if (path.node.operator !== '+') return;
        const { left, right } = path.node;
        if (t.isStringLiteral(left) && t.isStringLiteral(right)) {
            path.replaceWith(t.stringLiteral(left.value + right.value));
        }
    }
});

// 生成代码
const output = generate(ast);
```

### Step 5：验证还原结果

```javascript
// 对比混淆前后的函数行为
var originalResult = originalCode.encrypt('test');
var restoredResult = restoredCode.encrypt('test');
console.log(originalResult === restoredResult); // 应为 true
```

## 处理 eval 加载的策略

### 策略 A：Hook eval 拦截
```javascript
// 最简单的方式
var _evalCache = [];
var _origEval = window.eval;
window.eval = function(code) {
    _evalCache.push(code);
    return _origEval.call(this, code);
};
```

### 策略 B：手动解包
```javascript
// 对于 packer 类的 eval
// 直接在 Console 中执行解包
eval(function(p,a,c,k,e,d){...}('packed', 62, 500, '...', '|', ...));
// 查看输出
```

### 策略 C：AST 替换 eval 调用
```javascript
// 将 eval(string) 替换为 string 的内容
traverse(ast, {
    CallExpression(path) {
        if (t.isIdentifier(path.node.callee, { name: 'eval' })) {
            if (t.isStringLiteral(path.node.arguments[0])) {
                // 解析字符串内容为 AST
                var innerAst = parser.parse(path.node.arguments[0].value);
                // 替换 eval 调用为解析后的代码
                path.replaceWithMultiple(innerAst.program.body);
            }
        }
    }
});
```

## 关键要点总结

- Reese84 使用 eval 动态加载 + OB 混淆的组合保护
- 第一步是 Hook eval 获取解密后的完整代码
- 定位解密函数后，提取所有 hash→value 映射
- 使用 AST 批量替换解密调用为明文
- 多趟遍历处理：解密函数替换 → 字符串拼接合并 → 代码清理

## 相关主题
- → [Akamai AST 反混淆实战](akamai-ast-deobfuscation.md)
- → [AST 反混淆详解](../02-obfuscation/ast-deobfuscation.md)
- → [混淆类型详解](../02-obfuscation/obfuscation-types.md)
