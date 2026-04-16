# WASM 逆向

> 来源: [JS逆向完整技能图谱](https://51rexue.cn/blog/50) | [Vercel 盾 Worker 执行链 / Wasm 分析](https://blog.51cto.com/u_15619200/14529767)

## 概述

WebAssembly (WASM) 被越来越多地用于前端加密，因为其字节码难以直接阅读。本文介绍 WASM 逆向的工具和方法。

## WASM 基础

### 什么是 WASM
- 二进制指令格式，可在浏览器中高效运行
- 常见扩展名：`.wasm`
- 可由 C/C++/Rust/Go 编译生成
- 通过 `WebAssembly.instantiate()` 加载

### WASM 加密特征
```javascript
// 加载 WASM 模块
fetch('encrypt.wasm')
    .then(response => response.arrayBuffer())
    .then(bytes => WebAssembly.instantiate(bytes, imports))
    .then(module => {
        // 调用 WASM 导出函数
        var result = module.instance.exports.encrypt(data_ptr, data_len);
    });
```

## 逆向工具

### 1. wasm2wat — 反汇编

将 WASM 二进制转换为可读的 WAT（WebAssembly Text Format）：

```bash
# 安装 WABT 工具包
# https://github.com/WebAssembly/wabt

# 反汇编
wasm2wat encrypt.wasm -o encrypt.wat

# 输出示例
(module
  (type (;0;) (func (param i32 i32) (result i32)))
  (func $encrypt (;0;) (type 0) (param i32 i32) (result i32)
    local.get 0
    local.get 1
    i32.add
  )
  (export "encrypt" (func 0))
)
```

### 2. Ghidra — 反编译

Ghidra（NSA 开源工具）支持 WASM 反编译：

1. 安装 Ghidra：https://ghidra-sre.org/
2. 安装 WASM 处理器模块
3. 导入 `.wasm` 文件
4. 自动分析 → 查看反编译的伪 C 代码

**优点**：
- 生成类似 C 的伪代码，比 WAT 更易读
- 支持函数重命名、注释
- 支持交叉引用分析

### 3. Chrome DevTools — 调试

Chrome 85+ 支持直接调试 WASM：

1. Sources 面板 → 找到 WASM 模块
2. 查看 WAT 格式的代码
3. 在 WASM 函数中设置断点
4. 查看局部变量和调用栈

### 4. wasm-objdump — 查看 WASM 结构

```bash
# 查看段信息
wasm-objdump -h encrypt.wasm

# 查看反汇编详情
wasm-objdump -d encrypt.wasm

# 查看导出函数
wasm-objdump -x encrypt.wasm
```

## 逆向流程

### Step 1：定位 WASM 加载

```javascript
// 搜索加载代码
WebAssembly.instantiate
WebAssembly.instantiateStreaming
```

### Step 2：获取 WASM 文件

```javascript
// 方式 1：Network 面板直接下载
// 过滤 .wasm 请求，右键保存

// 方式 2：从 JS 中提取
// 某些场景 WASM 以 Base64 内嵌在 JS 中
var wasmBase64 = "AGFzbQEAAAABBQFgAAF/AwIBAA...";
var wasmBytes = Uint8Array.from(atob(wasmBase64), c => c.charCodeAt(0));
```

### Step 3：分析 WASM 结构

```bash
# 查看导出函数
wasm-objdump -x encrypt.wasm | grep "export"

# 输出示例：
# export [0]: "memory" -> memory
# export [1]: "encrypt" -> function[0]
# export [2]: "decrypt" -> function[1]
# export [3]: "_malloc" -> function[2]
# export [4]: "_free" -> function[3]
```

### Step 4：反编译/反汇编

```bash
# 反汇编为 WAT
wasm2wat encrypt.wasm -o encrypt.wat

# 或使用 Ghidra 获取伪 C 代码
```

### Step 5：分析加密逻辑

WAT 中的常见模式：
```wat
;; i32.add — 加法
;; i32.xor — 异或
;; i32.shl — 左移
;; i32.shr_u — 右移（无符号）
;; i32.rotl — 循环左移
;; i32.rotr — 循环右移
;; memory.load — 内存读取
;; memory.store — 内存写入
```

### Step 6：提取密钥和参数

```javascript
// 在 JS 端查看传入 WASM 的参数
var imports = {
    env: {
        memory: new WebAssembly.Memory({ initial: 256 }),
        _key: 'secret_key_here',  // 密钥可能通过 imports 传入
        table: new WebAssembly.Table({ initial: 0, element: 'anyfunc' })
    }
};

// 或通过 Hook WebAssembly.instantiate 捕获
var originalInstantiate = WebAssembly.instantiate;
WebAssembly.instantiate = function(source, imports) {
    console.log('WASM Imports:', imports);
    return originalInstantiate.call(this, source, imports);
};
```

### Step 7：还原或调用

```python
# 方式 1：Python wasmtime 调用 WASM
import wasmtime

engine = wasmtime.Engine()
store = wasmtime.Store(engine)
module = wasmtime.Module.from_file(engine, 'encrypt.wasm')

# 设置 imports
instance = wasmtime.Instance(store, module, [])

# 调用导出函数
result = instance.exports(store).encrypt(data_ptr, data_len)
```

```python
# 方式 2：Python 重写（简单 WASM）
# 根据 WAT / 伪 C 代码用 Python 重写逻辑
def custom_wasm_encrypt(data):
    result = bytearray()
    for byte in data:
        byte = byte ^ 0x37
        byte = ((byte << 3) | (byte >> 5)) & 0xFF
        result.append(byte)
    return bytes(result)
```

## 高级技巧

### 1. 动态调用（无需完全逆向）
```javascript
// 直接加载 WASM 并调用导出函数
fetch('encrypt.wasm')
    .then(r => r.arrayBuffer())
    .then(bytes => WebAssembly.instantiate(bytes, imports))
    .then(module => {
        const exports = module.instance.exports;
        // 枚举所有导出
        console.log('Exports:', Object.keys(exports));
        // 直接调用
        const result = exports.encrypt(...);
    });
```

### 2. 内存数据提取
```javascript
// 从 WASM 内存中读取数据
const memory = instance.exports.memory;
const view = new Uint8Array(memory.buffer);
// 读取特定偏移处的数据
const data = view.slice(offset, offset + length);
```

## 实战案例：某宝bx-pp参数

**场景**：某宝滑块验证`bx-pp`参数由Wasm模块生成，传统JS逆向无法破解

**流程**：
1. 抓包获取`bx-pp.wasm`文件
2. wasm2wat反编译，定位`bx_pp_generate`函数
3. Chrome DevTools调试，分析内存操作与算法逻辑（自定义哈希+AES）
4. 提取密钥、IV、填充方式
5. Python复现算法，成功生成`bx-pp`参数

## Wasm逆向难点与突破

### 主要难点

| 难点 | 说明 |
|------|------|
| 二进制可读性差 | WASM字节码难以直接阅读理解 |
| 内存操作复杂 | 大量内存读写操作，追踪困难 |
| 无直接调试信息 | 编译后丢失符号信息 |
| 算法高度封装 | 加密逻辑封装在Wasm内部 |

### 突破技巧

- **结合Wat文本与动态调试**：双向验证逻辑，确保分析正确
- **利用Frida Hook内存读写**：直接获取关键数据，无需完全逆向算法
- **参考C/C++源码编译模式**：快速定位常见加密算法实现

### Frida Hook Wasm示例

```javascript
// Frida Hook Wasm函数示例
const module = Process.findModuleByName("target.wasm");
const encrypt_func = module.exports.encrypt;
Interceptor.attach(encrypt_func, {
    onEnter: function(args) {
        console.log("明文:", args[0].readUtf8String());
        console.log("密钥:", args[1].readUtf8String());
    },
    onLeave: function(retval) {
        console.log("密文:", retval.readUtf8String());
    }
});
```

## 关键要点总结

- wasm2wat 是基本的反汇编工具，将二进制转为可读 WAT
- Ghidra 可生成伪 C 代码，大幅提升可读性
- Chrome DevTools 支持直接调试 WASM，设置断点查看变量
- 逆向步骤：定位加载 → 获取文件 → 反编译 → 分析逻辑 → 还原或直接调用
- 简单 WASM 可用 Python 重写，复杂的用 wasmtime 直接调用

## 相关主题
- → [加密算法识别](../04-algorithms/crypto-identification.md)
- → [Vercel 盾实战](../06-case-studies/vercel-shield-wasm.md)
- → [补环境实战](../03-environment/env-simulation-practice.md)
