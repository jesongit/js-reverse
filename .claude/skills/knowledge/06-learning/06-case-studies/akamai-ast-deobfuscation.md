# Akamai 加密 AST 反混淆实战

> 来源: [AST反混淆处理示例（Akamai 案例）](https://juejin.cn/post/7573193563044692022)

## 概述

Akamai 是全球知名的 CDN 和安全防护服务商，其前端脚本使用高度混淆保护加密逻辑。本文通过 AST 分析 Akamai 的混淆模式，实现自动化反混淆。

## 混淆特征分析

### 四种加密形式

通过 AST 分析，Akamai 的字符串加密表现为四种形式：

#### 形式 1：apply 调用
```javascript
// 混淆代码
_0xfunc['apply'](undefined, [_0xobj, 'key']);

// AST 结构
CallExpression
├── callee: MemberExpression
│   ├── object: Identifier (_0xfunc)
│   └── property: StringLiteral ('apply')
└── arguments: [Identifier(undefined), ArrayExpression]
```

#### 形式 2：call 调用
```javascript
// 混淆代码
_0xfunc['call'](_0xobj, 'key');

// AST 结构
CallExpression
├── callee: MemberExpression
│   ├── object: Identifier (_0xfunc)
│   └── property: StringLiteral ('call')
└── arguments: [Identifier(_0xobj), StringLiteral('key')]
```

#### 形式 3：直接函数调用
```javascript
// 混淆代码
_0xfunc(_0xobj, 'key');

// AST 结构
CallExpression
├── callee: Identifier (_0xfunc)
└── arguments: [Identifier(_0xobj), StringLiteral('key')]
```

#### 形式 4：三元表达式
```javascript
// 混淆代码
condition ? _0xfunc['call'](_0xobj, 'key') : _0xfunc(_0xobj, 'key');

// AST 结构
ConditionalExpression
├── test: ...
├── consequent: CallExpression (形式 2)
└── alternate: CallExpression (形式 3)
```

### 逗号表达式 Trick

Akamai 使用逗号表达式进行变量映射：

```javascript
// 混淆代码中的逗号表达式
return _vars[_0xkey] = value, _vars[_0xkey];

// 等价于：
_vars[_0xkey] = value;
return _vars[_0xkey];
```

**解析**：逗号表达式的返回值是最后一个表达式的值。这里先将值存入全局变量 `_vars`，然后返回。

### 动态映射机制

```javascript
// 全局映射变量
var _vars = {};

// 解密函数将结果存入 _vars
function _0xdecrypt(key) {
    var value = /* 解密逻辑 */;
    _vars[key] = value;
    return value;
}

// 后续通过 _vars 直接访问已解密的值
_vars['some_key'];
```

## AST 反混淆实现

### Step 1：定位解密函数

```javascript
// 搜索特征：apply/call 调用模式 + 逗号表达式
traverse(ast, {
    CallExpression(path) {
        const { callee, arguments: args } = path.node;
        if (t.isMemberExpression(callee) &&
            t.isStringLiteral(callee.property)) {
            const methodName = callee.property.value;
            if (['apply', 'call'].includes(methodName)) {
                // 找到解密函数的调用模式
                console.log('Found pattern:', methodName, 'at', path.node.loc);
            }
        }
    }
});
```

### Step 2：提取映射关系

```javascript
// 执行代码中的解密函数，收集所有键值对
// 在 Node.js 中执行，提取 _vars 对象
function extractMappings(decryptFunc) {
    const vars = {};

    // 遍历所有解密调用
    traverse(ast, {
        CallExpression(path) {
            const key = extractKey(path);
            if (key) {
                const value = decryptFunc(key);
                vars[key] = value;
            }
        }
    });

    return vars;
}
```

### Step 3：替换加密调用

```javascript
// 将解密函数调用替换为明文字符串
const mappings = extractMappings(originalDecrypt);

traverse(ast, {
    CallExpression(path) {
        // 匹配四种加密形式之一
        const key = matchEncryptPattern(path.node);
        if (key && mappings[key] !== undefined) {
            // 替换为明文值
            path.replaceWith(t.stringLiteral(mappings[key]));
        }
    }
});

// 同时替换 _vars 引用
traverse(ast, {
    MemberExpression(path) {
        if (t.isIdentifier(path.node.object, { name: '_vars' })) {
            const key = /* 提取 key */;
            if (mappings[key] !== undefined) {
                path.replaceWith(t.stringLiteral(mappings[key]));
            }
        }
    }
});
```

### Step 4：清理死代码

```javascript
// 删除解密函数定义
// 删除 _vars 全局变量
// 删除无用赋值
traverse(ast, {
    VariableDeclarator(path) {
        if (t.isIdentifier(path.node.id, { name: '_vars' }) ||
            t.isIdentifier(path.node.id, { name: '_0xdecrypt' })) {
            path.remove();
        }
    }
});
```

## 工作流总结

```
获取 Akamai JS 文件
    ↓
AST 解析
    ↓
识别四种加密形式（apply/call/直接/三元）
    ↓
定位解密函数
    ↓
执行解密函数，提取映射表 (_vars)
    ↓
AST 批量替换：加密调用 → 明文字符串
    ↓
清理死代码（解密函数、_vars 变量）
    ↓
生成可读代码
```

## 关键要点总结

- Akamai 的加密表现为四种 AST 形式：apply、call、直接调用、三元表达式
- 逗号表达式 trick 用于将解密结果映射到全局 `_vars`
- 反混淆核心：执行解密函数提取映射表，然后 AST 批量替换
- 需要同时处理函数调用和 `_vars` 直接引用两种方式
- 替换完成后清理解密函数和映射变量

## 相关主题
- → [AST 反混淆详解](../02-obfuscation/ast-deobfuscation.md)
- → [混淆类型详解](../02-obfuscation/obfuscation-types.md)
- → [Reese84 OB 反混淆实战](reese84-ob-deobfuscation.md)
