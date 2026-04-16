# Vercel 盾 Worker 执行链 / WASM 分析

> 来源: [Vercel 盾 / Wasm 逆向](https://blog.51cto.com/u_15619200/14529767) | [JS逆向完整技能图谱](https://51rexue.cn/blog/50)

## 概述

Vercel 盾（Vercel Shield / Vercel WAF）使用 Worker + WASM 的方式执行前端验证逻辑。本文分析其执行链路和逆向方法。

## Vercel 盾架构

```
浏览器加载页面
    ↓
加载 Vercel 盾 JS
    ↓
JS 初始化 → 收集浏览器指纹
    ↓
加载 WASM 模块
    ↓
JS 调用 WASM 加密函数（传入指纹 + 时间戳等参数）
    ↓
WASM 返回加密 Token
    ↓
JS 将 Token 附加到请求中
    ↓
Vercel 后端验证 Token
```

## 逆向分析步骤

### Step 1：定位 Vercel 盾脚本

```javascript
// 在 Network 面板中搜索特征
// - 包含 "_vercel" 或 "shield" 的请求
// - 加载 .wasm 文件的请求
// - 设置特殊 Cookie 的脚本
```

### Step 2：分析 Worker 执行链

Vercel 盾可能使用 Web Worker 执行加密：

```javascript
// 搜索 Worker 创建
new Worker(blob_url);
new Worker('shield-worker.js');

// Hook Worker 监控通信
var originalWorker = window.Worker;
window.Worker = function(url) {
    console.log('Worker created:', url);
    var worker = new originalWorker(url);

    var originalPostMessage = worker.postMessage.bind(worker);
    worker.postMessage = function(data) {
        console.log('Worker <- Main:', data);
        return originalPostMessage(data);
    };

    worker.addEventListener('message', function(e) {
        console.log('Worker -> Main:', e.data);
    });

    return worker;
};
```

### Step 3：提取 WASM 模块

```javascript
// 方式 1：Network 面板过滤 .wasm 文件直接下载

// 方式 2：Hook WebAssembly.instantiate
var originalInstantiate = WebAssembly.instantiate;
WebAssembly.instantiate = function(source, imports) {
    // 保存 WASM 字节码
    if (source instanceof ArrayBuffer) {
        var bytes = new Uint8Array(source);
        console.log('WASM size:', bytes.length, 'bytes');
        // 可在此处保存到文件
    }
    console.log('WASM imports:', JSON.stringify(imports));
    return originalInstantiate.call(this, source, imports).then(function(result) {
        console.log('WASM exports:', Object.keys(result.instance.exports));
        return result;
    });
};
```

### Step 4：分析 WASM 导出函数

```javascript
// 获取 WASM 实例后枚举导出
WebAssembly.instantiate(wasmBytes, imports).then(function(module) {
    var exports = module.instance.exports;
    for (var name in exports) {
        console.log('Export:', name, typeof exports[name]);
        // function 类型的导出是可调用的加密函数
    }
});
```

### Step 5：分析加密参数

```javascript
// Hook WASM 导出函数的调用
// 查看传入参数和返回值

// 方式 1：修改 imports 对象
var originalImports = {
    env: {
        memory: new WebAssembly.Memory({ initial: 256 }),
        // ... 其他 imports
    }
};

// 方式 2：包装导出函数
var instance = /* WASM 实例 */;
var originalEncrypt = instance.exports.encrypt;
instance.exports.encrypt = function(ptr, len) {
    // 读取输入数据
    var memory = new Uint8Array(instance.exports.memory.buffer);
    var inputData = Array.from(memory.slice(ptr, ptr + len));
    console.log('WASM encrypt input:', inputData);

    var resultPtr = originalEncrypt(ptr, len);

    // 读取输出数据
    var outputData = Array.from(memory.slice(resultPtr, resultPtr + 64));
    console.log('WASM encrypt output:', outputData);

    return resultPtr;
};
```

## 常见应对方案

### 方案 1：纯算方案
- 完全逆向 WASM 加密逻辑
- 用 Python 重新实现
- **难度最高，性能最好**

### 方案 2：补环境方案
- 使用 Node.js + 补环境直接运行 JS 部分
- WASM 部分使用 wasmtime 等运行时调用
- **中等难度**

### 方案 3：Worker 执行链方案
- 搭建完整的 Worker + WASM 运行环境
- Node.js 中模拟 Worker 通信
- **适合复杂场景**

### 方案 4：RPC / 无头浏览器方案
- 直接在浏览器中运行，通过 RPC 获取结果
- 或使用 Playwright 自动化
- **最简单，资源消耗最大**
- → 详见 [RPC 方案](../05-advanced/rpc-technique.md) 和 [无头浏览器](../05-advanced/headless-browser.md)

## 关键要点总结

- Vercel 盾使用 JS + Worker + WASM 三层架构
- Hook WebAssembly.instantiate 可获取 WASM 文件和导出信息
- 分析重点是：WASM 导出函数的输入参数和返回值
- 四种应对方案：纯算 > 补环境 > Worker 链 > RPC/无头浏览器
- 选择方案时权衡：难度、性能、稳定性

## 相关主题
- → [WASM 逆向](../05-advanced/wasm-reverse.md)
- → [补环境实战](../03-environment/env-simulation-practice.md)
- → [RPC 远程过程调用](../05-advanced/rpc-technique.md)
