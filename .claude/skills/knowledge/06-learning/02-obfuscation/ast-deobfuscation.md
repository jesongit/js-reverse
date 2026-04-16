# AST 反混淆详解

> 来源: [JavaScript AST反混淆完全指南](https://juejin.cn/post/7506324201280946212) | [AST反混淆实战系列](https://juejin.cn/post/7573193563044692022)

## 概述

AST（Abstract Syntax Tree，抽象语法树）反混淆是处理复杂混淆最强大的方法。通过 Babel 工具链，可以精确地分析和转换代码结构，自动化还原混淆逻辑。

## AST 基础概念

### 什么是 AST
- 源代码的树形结构表示
- 每个节点（Node）表示代码中的一个构造（变量、函数、表达式等）
- 通过遍历和修改节点实现代码转换

### AST 节点类型（常用）
| 类型 | 说明 | 示例 |
|------|------|------|
| Program | 程序根节点 | 整个文件 |
| FunctionDeclaration | 函数声明 | `function foo() {}` |
| VariableDeclaration | 变量声明 | `var x = 1;` |
| CallExpression | 函数调用 | `foo()` |
| MemberExpression | 成员访问 | `obj.prop` |
| StringLiteral | 字符串字面量 | `"hello"` |
| NumericLiteral | 数字字面量 | `42` |
| BinaryExpression | 二元运算 | `a + b` |
| ConditionalExpression | 三元表达式 | `a ? b : c` |
| SwitchStatement | switch 语句 | `switch(x) {}` |
| ReturnStatement | return 语句 | `return x;` |

## Babel 工具链

### 核心模块

```bash
npm install @babel/parser @babel/traverse @babel/generator @babel/types
```

| 模块 | 功能 |
|------|------|
| `@babel/parser` | 解析代码为 AST |
| `@babel/traverse` | 遍历和操作 AST 节点 |
| `@babel/generator` | 从 AST 生成代码 |
| `@babel/types` | 判断/创建 AST 节点 |

### 基本工作流

```javascript
const parser = require('@babel/parser');
const traverse = require('@babel/traverse').default;
const generate = require('@babel/generator').default;
const t = require('@babel/types');

// 1. 解析代码为 AST
const ast = parser.parse(jsCode);

// 2. 遍历并修改 AST
traverse(ast, {
    // 访问器（Visitor）
    StringLiteral(path) {
        // 处理字符串字面量节点
    }
});

// 3. 生成还原后的代码
const output = generate(ast, { comments: false });
console.log(output.code);
```

## @babel/traverse 详细用法

### 访问者模式（Visitor）

```javascript
traverse(ast, {
    // 进入节点时调用
    FunctionDeclaration: {
        enter(path) {
            console.log('进入函数:', path.node.id.name);
        },
        exit(path) {
            console.log('退出函数:', path.node.id.name);
        }
    },
    // 简写形式（等同于 enter）
    CallExpression(path) {
        console.log('函数调用:', path.node.callee);
    }
});
```

### Path 对象常用方法

#### 节点操作
```javascript
// 替换当前节点
path.replaceWith(t.stringLiteral('replacement'));

// 替换为多个节点
path.replaceWithMultiple([
    t.expressionStatement(t.stringLiteral('a')),
    t.expressionStatement(t.stringLiteral('b'))
]);

// 删除当前节点
path.remove();

// 在当前节点前插入
path.insertBefore(t.expressionStatement(t.stringLiteral('before')));

// 在当前节点后插入
path.insertAfter(t.expressionStatement(t.stringLiteral('after')));
```

#### 作用域操作
```javascript
// 声明变量（自动处理 var/let/const）
path.scope.generateUidIdentifier('temp'); // 生成唯一变量名
path.scope.push({ id: t.identifier('myVar'), init: t.numericLiteral(0) });

// 检查绑定
path.scope.hasBinding('variableName');
path.scope.getBinding('variableName');

// 重命名变量
path.scope.rename('oldName', 'newName');

// 获取父级作用域
path.scope.parent;
```

#### 路径导航
```javascript
path.parentPath;     // 父路径
path.container;      // 包含当前节点的数组
path.key;            // 在容器中的索引
path.listKey;        // 容器的键名
path.node;           // 当前 AST 节点
path.type;           // 节点类型
```

## 常见反混淆场景

### 1. 字符串解密还原

```javascript
// 目标：将 _0xdecrypt('0x1a') 替换为实际字符串值
traverse(ast, {
    CallExpression(path) {
        const { callee, arguments: args } = path.node;
        // 匹配解密函数调用
        if (t.isIdentifier(callee, { name: '_0xdecrypt' })
            && args.length === 1
            && t.isStringLiteral(args[0])) {
            // 执行解密获取真实值
            const realValue = decrypt(args[0].value);
            path.replaceWith(t.stringLiteral(realValue));
        }
    }
});
```

### 2. 控制流平坦化还原

```javascript
// 目标：将 while-switch 结构还原为顺序执行
traverse(ast, {
    WhileStatement(path) {
        // 检测 while(true) { switch } 模式
        if (!t.isBooleanLiteral(path.node.test, { value: true })) return;
        const switchNode = path.node.body.body[0];
        if (!t.isSwitchStatement(switchNode)) return;

        // 提取执行顺序
        // 从分发器（discriminator）获取顺序数组
        const orderArr = extractOrder(switchNode.discriminant);

        // 按 orderArr 顺序重组 case 块
        const cases = switchNode.cases;
        const orderedBody = [];
        for (const idx of orderArr) {
            const caseBlock = cases.find(c =>
                t.isNumericLiteral(c.test, { value: idx })
            );
            // 提取 case body，去掉 continue/break
            for (const stmt of caseBlock.consequent) {
                if (!t.isContinueStatement(stmt) && !t.isBreakStatement(stmt)) {
                    orderedBody.push(stmt);
                }
            }
        }

        // 替换整个 while 块
        path.replaceWithMultiple(orderedBody);
    }
});
```

### 3. 常量折叠（Constant Folding）

```javascript
// 目标：计算可确定的常量表达式
// "hello" + " " + "world" → "hello world"
// 1 + 2 + 3 → 6
traverse(ast, {
    BinaryExpression(path) {
        const { left, right, operator } = path.node;
        if (t.isStringLiteral(left) && t.isStringLiteral(right) && operator === '+') {
            path.replaceWith(t.stringLiteral(left.value + right.value));
        }
        if (t.isNumericLiteral(left) && t.isNumericLiteral(right)) {
            let result;
            switch (operator) {
                case '+': result = left.value + right.value; break;
                case '-': result = left.value - right.value; break;
                case '*': result = left.value * right.value; break;
                case '/': result = left.value / right.value; break;
            }
            if (result !== undefined) {
                path.replaceWith(t.numericLiteral(result));
            }
        }
    }
});
```

### 4. 死代码删除

```javascript
// 删除 if(false) / if(0) 包裹的代码块
traverse(ast, {
    IfStatement(path) {
        const { test, consequent } = path.node;
        if (t.isBooleanLiteral(test, { value: false })
            || t.isNumericLiteral(test, { value: 0 })) {
            // 如果有 alternate（else 分支），保留 alternate
            if (path.node.alternate) {
                path.replaceWith(path.node.alternate);
            } else {
                path.remove();
            }
        }
    }
});
```

### 5. 对象属性简化

```javascript
// _0xobj['a'] → _0xobj.a （可读性提升）
traverse(ast, {
    MemberExpression(path) {
        const { property, computed } = path.node;
        if (computed && t.isStringLiteral(property)) {
            // 检查是否为合法标识符
            if (/^[a-zA-Z_$][a-zA-Z0-9_$]*$/.test(property.value)) {
                path.node.computed = false;
                path.node.property = t.identifier(property.value);
            }
        }
    }
});
```

## 性能优化

### 选择性遍历
```javascript
// 只遍历特定类型，减少不必要的访问
traverse(ast, {
    // 只进入 Function，跳过其他
    Function: {
        enter(path) { /* ... */ },
        noScope: true  // 不创建作用域（性能提升）
    }
});
```

### 缓存与批处理
```javascript
// 多次遍历合并为一次
// 先收集需要处理的节点，统一处理
const nodesToProcess = [];
traverse(ast, {
    CallExpression(path) {
        if (shouldProcess(path)) {
            nodesToProcess.push(path);
        }
    }
});
nodesToProcess.forEach(path => processNode(path));
```

### 多趟遍历策略
```javascript
// 第一趟：字符串解密
traverse(ast, stringDecryptVisitor);
// 第二趟：常量折叠
traverse(ast, constantFoldVisitor);
// 第三趟：控制流还原
traverse(ast, controlFlowVisitor);
// 第四趟：死代码删除
traverse(ast, deadCodeVisitor);
// 第五趟：代码美化
traverse(ast, cleanupVisitor);
```

## 关键要点总结

- Babel 是 AST 反混淆的核心工具链：parse → traverse → generate
- Path 对象提供了丰富的节点操作方法（replaceWith/remove/insertBefore 等）
- 作用域操作（hasBinding/getBinding/rename）处理变量名还原
- 反混淆通常需要多趟遍历，按依赖顺序执行
- 先处理字符串解密，再处理控制流，最后清理死代码
- 性能优化：选择性遍历、缓存、批量处理

## 相关主题
- → [混淆类型详解](obfuscation-types.md)
- → [反混淆工具](deobfuscation-tools.md)
- → [Akamai AST 反混淆实战](../06-case-studies/akamai-ast-deobfuscation.md)
- → [Reese84 OB 反混淆实战](../06-case-studies/reese84-ob-deobfuscation.md)
