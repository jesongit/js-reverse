# 自定义算法分析方法

> 来源: [JS逆向完整技能图谱](https://51rexue.cn/blog/50) | [JavaScript逆向工程：原理、技术与实践](https://blog.51cto.com/boss/14102684)

## 概述

当遇到非标准加密算法（自定义位运算、混淆变换等）时，无法直接使用标准库还原，需要深入分析算法逻辑并选择合适的还原方式。

## 自定义算法特征

### 1. 位运算加密
```javascript
// 大量使用 XOR、位移等位运算
function customEncrypt(data) {
    var result = '';
    for (var i = 0; i < data.length; i++) {
        var charCode = data.charCodeAt(i);
        charCode = charCode ^ 0x37;          // XOR
        charCode = (charCode << 3) | (charCode >> 5);  // 循环左移
        charCode = charCode ^ (i & 0xFF);    // 与索引 XOR
        result += String.fromCharCode(charCode);
    }
    return result;
}
```

### 2. 字符映射表
```javascript
// 自定义字符映射
var map = 'abcdefghijklmnopqrstuvwxyz012345';
function encode(str) {
    var result = '';
    for (var i = 0; i < str.length; i++) {
        var code = str.charCodeAt(i);
        result += map[(code >> 4) & 0x1F];
        result += map[code & 0x1F];
    }
    return result;
}
```

### 3. 混合运算
```javascript
// 加减乘除 + 位运算混合
function hash(data) {
    var h = 0;
    for (var i = 0; i < data.length; i++) {
        h = (h * 31 + data.charCodeAt(i)) & 0xFFFFFFFF;
        h = ((h >> 16) ^ h) * 0x45d9f3b;
        h = ((h >> 16) ^ h) * 0x45d9f3b;
        h = (h >> 16) ^ h;
    }
    return h;
}
```

### 4. 时间戳参与运算
```javascript
// 加密结果与时间相关
function generateSign(params) {
    var timestamp = Date.now();
    var nonce = Math.random().toString(36).substring(2);
    var raw = params + timestamp + nonce + 'secret_salt';
    return {
        sign: customHash(raw),
        timestamp: timestamp,
        nonce: nonce
    };
}
```

## 分析方法

### 方法 1：逐步断点调试
1. 在加密函数入口设置断点
2. 记录输入值
3. 逐步（F10）执行，观察每一步变量变化
4. 记录最终输出值
5. 对比分析变换逻辑

### 方法 2：Console 注入追踪
```javascript
// 包装目标函数，记录输入输出
var originalEncrypt = window.encrypt;
window.encrypt = function() {
    var input = arguments[0];
    var output = originalEncrypt.apply(this, arguments);
    console.log('Input:', JSON.stringify(input));
    console.log('Output:', output);
    return output;
};
```

### 方法 3：扣代码到 Node.js
```javascript
// 将加密函数和相关依赖扣出到单独文件
// 在 Node.js 中测试运行

// 提取的代码
function customEncrypt(data) {
    // ... 从目标网站扣出的代码
}

// 测试
var result = customEncrypt('test_data');
console.log(result);
```

### 方法 4：补环境直接执行
- 对于依赖浏览器环境的自定义算法
- 使用补环境方式在 Node.js 中运行
- → 详见 [补环境实战流程](../03-environment/env-simulation-practice.md)

### 方法 5：Python 翻译
- 对于纯运算的自定义算法
- 逐行翻译 JS 代码为 Python
- 注意位运算的精度差异

```python
# JS 的位运算注意事项
# JS 中位运算结果为 32 位有符号整数
# Python 中需要手动处理

def js_bitwise_and(a, b):
    """模拟 JS 的 & 运算（32位）"""
    return a & b & 0xFFFFFFFF

def js_right_shift(a, n):
    """模拟 JS 的 >> 运算（带符号）"""
    a = a & 0xFFFFFFFF
    if a >= 0x80000000:
        a -= 0x100000000
    return (a >> n) & 0xFFFFFFFF

def js_left_shift(a, n):
    """模拟 JS 的 << 运算"""
    return (a << n) & 0xFFFFFFFF
```

## 还原策略选择

```
自定义算法分析
    ↓
是否依赖浏览器环境？
├── 否 → 是否纯位运算/数学运算？
│        ├── 是 → Python 翻译重写
│        └── 否 → 扣代码到 Node.js 运行
└── 是 → 补环境方案
```

## 关键要点总结

- 自定义算法通常涉及大量位运算、字符映射和混合运算
- 逐步调试 + Console 注入是最直接的分析方法
- 扣代码到 Node.js 是处理复杂自定义算法的实用方案
- Python 翻译时注意 JS 位运算的 32 位整数精度
- 时间戳参与的算法需要同时还原时间参数

## 相关主题
- → [加密算法识别](crypto-identification.md)
- → [算法还原实战](algorithm-reduction.md)
- → [补环境实战流程](../03-environment/env-simulation-practice.md)
