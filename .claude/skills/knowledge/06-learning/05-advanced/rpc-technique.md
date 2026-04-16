# RPC 远程过程调用方案

> 来源: [JS逆向完整技能图谱](https://51rexue.cn/blog/50)

## 概述

RPC（Remote Procedure Call）方案是一种"不还原算法"的逆向思路——直接在浏览器中执行加密函数，通过 WebSocket 将加密结果传回 Python 端。

## 原理

```
Python 端                    浏览器端
   |                            |
   |--- WebSocket 连接 -------->|
   |                            |
   |--- 发送待加密数据 -------->|
   |                            | 调用页面中的加密函数
   |                            | 获得加密结果
   |<-- 返回加密结果 ----------|
   |                            |
   | 使用结果发送 HTTP 请求     |
```

## 实现步骤

### Step 1：浏览器端注入 WebSocket 客户端

```javascript
// 在浏览器 Console 或 Tampermonkey 中注入
var ws = new WebSocket('ws://127.0.0.1:9999');

ws.onopen = function() {
    console.log('RPC WebSocket 已连接');
};

ws.onmessage = function(event) {
    var data = JSON.parse(event.data);
    var result;

    // 调用页面中的加密函数
    if (data.action === 'encrypt') {
        result = window.encrypt(data.params);  // 目标加密函数
    }
    if (data.action === 'sign') {
        result = window.generateSign(data.params);
    }

    // 返回结果
    ws.send(JSON.stringify({
        id: data.id,
        result: result
    }));
};
```

### Step 2：Python 端 WebSocket 服务

```python
import asyncio
import websockets
import json
import requests

class RPCServer:
    def __init__(self, port=9999):
        self.port = port
        self.clients = set()
        self.request_id = 0
        self.pending = {}

    async def handler(self, websocket, path):
        self.clients.add(websocket)
        try:
            async for message in websocket:
                data = json.loads(message)
                req_id = data.get('id')
                if req_id in self.pending:
                    self.pending[req_id].set_result(data['result'])
        finally:
            self.clients.remove(websocket)

    async def call(self, action, params):
        if not self.clients:
            raise Exception("没有浏览器客户端连接")

        self.request_id += 1
        req_id = self.request_id
        future = asyncio.get_event_loop().create_future()
        self.pending[req_id] = future

        client = list(self.clients)[0]
        await client.send(json.dumps({
            'id': req_id,
            'action': action,
            'params': params
        }))

        return await asyncio.wait_for(future, timeout=30)

    async def start(self):
        async with websockets.serve(self.handler, '0.0.0.0', self.port):
            print(f'RPC Server running on ws://0.0.0.0:{self.port}')
            await asyncio.Future()  # 永久运行

# 使用示例
async def main():
    rpc = RPCServer(9999)
    server_task = asyncio.create_task(rpc.start())

    # 等待浏览器连接
    await asyncio.sleep(5)

    # 调用浏览器中的加密函数
    encrypted = await rpc.call('encrypt', {'data': 'hello world'})
    print(f'加密结果: {encrypted}')

    # 使用加密结果发送请求
    response = requests.post('https://example.com/api', data={
        'encrypted_data': encrypted
    })
    print(response.text)

asyncio.run(main())
```

### Step 3：注入方式

#### 方式 A：Console 直接注入
- 打开目标网站 → F12 Console → 粘贴 WebSocket 客户端代码

#### 方式 B：Tampermonkey 注入
```javascript
// ==UserScript==
// @name         RPC Client
// @namespace    rpc
// @version      1.0
// @run-at       document-end
// @match        *://target-site.com/*
// ==/UserScript==

(function() {
    var ws = new WebSocket('ws://127.0.0.1:9999');
    ws.onmessage = function(event) {
        var data = JSON.parse(event.data);
        var result = window[data.action](data.params);
        ws.send(JSON.stringify({ id: data.id, result: result }));
    };
})();
```

#### 方式 C：Playwright 自动注入
```python
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        await page.goto('https://target-site.com')

        # 注入 RPC 客户端
        await page.evaluate('''
            window.rpcWs = new WebSocket('ws://127.0.0.1:9999');
            window.rpcWs.onmessage = function(event) {
                var data = JSON.parse(event.data);
                var result = window[data.action](data.params);
                window.rpcWs.send(JSON.stringify({id: data.id, result: result}));
            };
        ''')

        # 保持页面运行
        await page.wait_for_timeout(600000)
```

## 主流RPC实现方案

### 1. Sekiro（最常用）

**原理**：基于gRPC的JS桥接工具，在浏览器注入服务端，本地通过RPC调用浏览器内的JS函数

**适用场景**：复杂JS加密、环境强检测、多账号批量逆向

**核心步骤**：
1. 启动Sekiro服务端
2. 浏览器注入Sekiro客户端，暴露加密函数
3. 本地Python/Java通过RPC调用加密函数，获取结果

### 2. Chrome DevTools Protocol（CDP）

**原理**：通过Chrome远程调试协议，调用`Runtime.callFunctionOn`，直接执行浏览器内的JS函数

**适用场景**：Puppeteer/Playwright爬虫集成、轻量RPC调用

**示例（Python+pyppeteer）**：
```python
import asyncio
from pyppeteer import launch

async def rpc_call_encrypt():
    browser = await launch(headless=False)
    page = await browser.newPage()
    # 注入加密函数（或调用页面已有函数）
    await page.evaluate('''
        function encrypt(data) {
            return CryptoJS.AES.encrypt(data, 'key').toString();
        }
    ''')
    # RPC调用加密函数
    result = await page.evaluate('encrypt("test_data")')
    print("加密结果:", result)
    await browser.close()

asyncio.run(rpc_call_encrypt())
```

### 3. Frida（移动端+Web端通用）

**原理**：Hook浏览器/客户端进程，暴露加密函数为RPC接口，支持多语言调用

**适用场景**：移动端APP逆向、Web端深度Hook、复杂环境检测绕过

## RPC核心技巧

- **链路级伪造**：浏览器仅保留"环境壳"，将核心加密函数通过gRPC/JSON-RPC暴露，降低浏览器负载
- **函数级粒化**：抽取V8内联函数为独立句柄，一次注入、多次复用，提升调用效率
- **零拷贝传输**：用SharedArrayBuffer+WebAssembly共享内存，减少数据传输耗时（<1ms）
- **热插拔调试**：RPC服务端嵌入采样工具，运行时热替换JS补丁，无需重启浏览器

## RPC vs 传统逆向对比

| 方案 | 优势 | 劣势 | 适用场景 |
|------|------|------|----------|
| RPC调用 | 结果100%匹配、环境一致、开发快、易维护 | 需启动浏览器、资源消耗较高 | 复杂加密、环境强检测、批量任务 |
| 抠代码 | 无浏览器依赖、速度快 | 易出错、需补环境、维护成本高 | 简单加密、无环境检测 |
| 补环境 | 无需浏览器、灵活 | 环境补全复杂、易被检测 | 中等复杂度加密、轻量检测 |

## 优缺点

| 优点 | 缺点 |
|------|------|
| 不需要还原加密算法 | 依赖浏览器，资源消耗大 |
| 结果 100% 正确 | 浏览器不能关闭 |
| 无视混淆和反调试 | 并发能力受限于浏览器 |
| 实现简单快速 | 网络延迟影响速度 |

## 适用场景

- 加密算法极其复杂，还原成本高
- 快速验证可行性（POC）
- 对并发要求不高的场景
- 补环境和扣代码都失败的兜底方案

## 关键要点总结

- RPC 是"不逆向"的逆向——直接借用浏览器执行加密
- 核心组件：浏览器端 WebSocket 客户端 + Python 端 WebSocket 服务
- 注入方式：Console / Tampermonkey / Playwright
- 适合复杂加密场景，不适合高并发需求
- 可与 Playwright 结合实现全自动化

## 相关主题
- → [无头浏览器方案](headless-browser.md)
- → [算法还原实战](../04-algorithms/algorithm-reduction.md)
