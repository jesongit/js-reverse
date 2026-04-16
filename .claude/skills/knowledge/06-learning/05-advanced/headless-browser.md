# 无头浏览器方案

> 来源: [JS逆向完整技能图谱](https://51rexue.cn/blog/50) | [JavaScript逆向工程：原理、技术与实践](https://blog.51cto.com/boss/14102684)

## 概述

无头浏览器（Headless Browser）是在后台运行、没有可见界面的浏览器，能够执行 JS 并与页面交互。常用于自动化数据采集和绕过 JS 加密。

## 主流工具

### Playwright（推荐）

**优点**：
- 微软开源，维护活跃
- 支持多浏览器（Chromium / Firefox / WebKit）
- API 更现代、功能更完善
- 自动等待机制

**安装**：
```bash
pip install playwright
playwright install chromium
```

**基本使用**：
```python
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto('https://example.com')

    # 执行 JS 并获取结果
    result = page.evaluate('document.title')
    print(result)

    # 获取加密后的数据
    encrypted = page.evaluate('''
        () => {
            return window.encrypt('data');
        }
    ''')

    browser.close()
```

### Puppeteer

**优点**：
- Google 开源，与 Chrome 深度集成
- Node.js 生态
- 社区资源丰富

**安装**：
```bash
npm install puppeteer
```

**基本使用**：
```javascript
const puppeteer = require('puppeteer');

(async () => {
    const browser = await puppeteer.launch({ headless: true });
    const page = await browser.newPage();
    await page.goto('https://example.com');

    // 执行 JS
    const result = await page.evaluate(() => {
        return window.encrypt('data');
    });

    console.log(result);
    await browser.close();
})();
```

## 常用操作

### 1. 页面交互
```python
# 点击
page.click('#login-btn')

# 输入
page.fill('#username', 'user123')

# 等待元素
page.wait_for_selector('.result')

# 等待网络请求
page.wait_for_response('**/api/data')
```

### 2. 拦截和修改请求
```python
def handle_route(route):
    # 拦截请求
    if 'api/encrypt' in route.request.url:
        # 修改请求参数
        route.continue_(post_data='modified_data')
    else:
        route.continue_()

page.route('**/*', handle_route)
```

### 3. 注入脚本
```python
# 在页面加载前注入
page.add_init_script('''
    Object.defineProperty(navigator, 'webdriver', {
        get: () => false
    });
''')

# 在当前页面执行
page.evaluate('''
    window.customFunction = function(data) {
        return encrypt(data);
    };
''')
```

### 4. 获取 Cookie
```python
# 获取所有 Cookie
cookies = page.context.cookies()
for cookie in cookies:
    print(cookie['name'], cookie['value'])
```

## 反检测技巧

### 1. 隐藏 WebDriver 特征
```python
# 方式 1：启动参数
browser = p.chromium.launch(
    args=['--disable-blink-features=AutomationControlled']
)

# 方式 2：注入脚本
page.add_init_script('''
    Object.defineProperty(navigator, 'webdriver', {
        get: () => false
    });
    // 修改 chrome 对象
    window.chrome = {
        runtime: {},
        loadTimes: function() {},
        csi: function() {},
        app: {}
    };
    // 修改 permissions
    const originalQuery = window.navigator.permissions.query;
    window.navigator.permissions.query = (parameters) => (
        parameters.name === 'notifications' ?
            Promise.resolve({ state: Notification.permission }) :
            originalQuery(parameters)
    );
''')
```

### 2. 修改浏览器指纹
```python
page.add_init_script('''
    // 修改 WebGL 指纹
    const getParameter = WebGLRenderingContext.prototype.getParameter;
    WebGLRenderingContext.prototype.getParameter = function(param) {
        if (param === 37445) return 'Google Inc. (NVIDIA)';
        if (param === 37446) return 'ANGLE (NVIDIA, ...) ';
        return getParameter.call(this, param);
    };
''')
```

### 3. 使用 stealth 插件
```bash
pip install playwright-stealth
```
```python
from playwright_stealth import stealth_sync

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    stealth_sync(page)  # 自动注入反检测脚本
    page.goto('https://example.com')
```

## 与 RPC 方案结合

```python
# Playwright + RPC 组合方案
import asyncio
import websockets

async def combined_approach():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        await page.goto('https://target-site.com')

        # 注入 RPC WebSocket 客户端
        await page.evaluate('''
            window.ws = new WebSocket('ws://127.0.0.1:9999');
            window.ws.onmessage = async (event) => {
                const data = JSON.parse(event.data);
                const result = await window.encrypt(data.params);
                window.ws.send(JSON.stringify({id: data.id, result}));
            };
        ''')

        # 保持运行
        await page.wait_for_timeout(3600000)
```

## 关键要点总结

- Playwright 是当前推荐的无头浏览器工具，API 更完善
- `page.evaluate()` 是在页面上下文执行 JS 的核心方法
- 反检测关键：隐藏 webdriver、修改指纹、使用 stealth 插件
- 与 RPC 方案结合可实现全自动化的数据采集
- 无头浏览器资源消耗较大，注意控制并发数

## 相关主题
- → [RPC 远程过程调用](rpc-technique.md)
- → [浏览器指纹对抗](browser-fingerprint.md)
- → [反调试技术](anti-debugging.md)
