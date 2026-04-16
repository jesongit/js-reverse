# 浏览器指纹对抗

> 来源: [JS逆向完整技能图谱](https://51rexue.cn/blog/50)

## 概述

浏览器指纹是通过收集浏览器的各种特征信息生成唯一标识的技术。在逆向工程中，需要理解指纹生成机制并能够模拟正确的指纹值。

## 主要指纹类型

### 1. Canvas 指纹

**原理**：
- 在 Canvas 上绘制特定图形和文字
- 调用 `toDataURL()` 导出图片数据
- 不同硬件/驱动/字体渲染会产生不同结果

**检测代码**：
```javascript
function getCanvasFingerprint() {
    var canvas = document.createElement('canvas');
    var ctx = canvas.getContext('2d');
    ctx.textBaseline = 'top';
    ctx.font = '14px Arial';
    ctx.fillStyle = '#f60';
    ctx.fillRect(125, 1, 62, 20);
    ctx.fillStyle = '#069';
    ctx.fillText('BrowserLeaks,com <canvas> 1.0', 2, 15);
    ctx.fillStyle = 'rgba(102, 204, 0, 0.7)';
    ctx.fillText('BrowserLeaks,com <canvas> 1.0', 4, 17);
    return canvas.toDataURL();
}
```

**补环境要点**：
- `toDataURL()` 必须返回固定且合理的 base64 字符串
- 建议从真实浏览器获取指纹值并固定使用
- → 详见 [补环境进阶](../03-environment/env-simulation-advanced.md)

### 2. WebGL 指纹

**原理**：
- 通过 WebGL API 获取 GPU 信息
- 渲染特定场景获取渲染特征

**关键参数**：
```javascript
var gl = canvas.getContext('webgl');
var debugInfo = gl.getExtension('WEBGL_debug_renderer_info');

// GPU 厂商
gl.getParameter(debugInfo.UNMASKED_VENDOR_WEBGL);  // 0x9245
// → "Google Inc. (NVIDIA)"

// GPU 渲染器
gl.getParameter(debugInfo.UNMASKED_RENDERER_WEBGL); // 0x9246
// → "ANGLE (NVIDIA, NVIDIA GeForce GTX 1060 6GB ...)"

// 其他参数
gl.getParameter(gl.VENDOR);     // 0x1F00
gl.getParameter(gl.RENDERER);   // 0x1F01
gl.getParameter(gl.VERSION);    // 0x1F02
```

### 3. AudioContext 指纹

**原理**：
- 使用 Web Audio API 生成音频信号
- 处理后的信号特征因设备而异

**检测代码**：
```javascript
function getAudioFingerprint() {
    var audioCtx = new AudioContext();
    var oscillator = audioCtx.createOscillator();
    oscillator.type = 'triangle';
    oscillator.frequency.value = 10000;

    var compressor = audioCtx.createDynamicsCompressor();
    compressor.threshold.value = -50;
    compressor.knee.value = 40;
    compressor.ratio.value = 12;
    compressor.reduction.value = -20;
    compressor.attack.value = 0;
    compressor.release.value = 0.25;

    oscillator.connect(compressor);
    compressor.connect(audioCtx.destination);
    oscillator.start(0);

    // 渲染后获取频率数据作为指纹
}
```

### 4. 字体指纹

**原理**：
- 通过测量不同字体的文字宽度差异判断已安装字体
- 字体集在不同操作系统上差异明显

**检测方式**：
```javascript
function detectFont(fontName) {
    var baseFonts = ['monospace', 'sans-serif', 'serif'];
    var testString = 'mmmmmmmmmmlli';
    var canvas = document.createElement('canvas');
    var ctx = canvas.getContext('2d');

    var baseWidths = baseFonts.map(function(font) {
        ctx.font = '72px ' + font;
        return ctx.measureText(testString).width;
    });

    ctx.font = '72px ' + fontName + ', ' + baseFonts.join(', ');
    var testWidth = ctx.measureText(testString).width;

    // 如果宽度与基础字体不同，说明字体已安装
    return baseWidths.some(function(w) { return testWidth !== w; });
}
```

### 5. 屏幕指纹

```javascript
// 屏幕信息
screen.width;            // 1920
screen.height;           // 1080
screen.availWidth;       // 1920
screen.availHeight;      // 1040
screen.colorDepth;       // 24
screen.pixelDepth;       // 24

// 窗口信息
window.devicePixelRatio; // 1 (普通屏) 或 2 (Retina)
```

### 6. 浏览器特征指纹

```javascript
// Navigator 信息
navigator.userAgent;
navigator.platform;          // "Win32"
navigator.language;          // "zh-CN"
navigator.hardwareConcurrency; // CPU 核心数
navigator.maxTouchPoints;    // 触控点数
navigator.plugins;           // 插件列表
navigator.mimeTypes;         // MIME 类型

// 时区
Intl.DateTimeFormat().resolvedOptions().timeZone;

// Cookies / LocalStorage 是否可用
navigator.cookieEnabled;
```

## 指纹对抗工具

### 1. 浏览器多开工具
- **AdsPower** / **Multilogin** / **GoLogin**
- 创建独立的浏览器环境，指纹互不影响

### 2. 浏览器扩展
- **Canvas Blocker**：干扰 Canvas 指纹
- **Privacy Badger**：阻止指纹追踪

### 3. Playwright/Puppeteer
```javascript
// 使用 Playwright 绕过指纹检测
const browser = await chromium.launch({
    args: ['--disable-blink-features=AutomationControlled']
});
const page = await browser.newPage();
await page.addInitScript(() => {
    // 修改指纹
    Object.defineProperty(navigator, 'webdriver', { get: () => false });
});
```

## 攻防对抗与避坑

### 常见检测绕过思路

| 检测类型 | 绕过方法 | 说明 |
|---------|---------|------|
| 扩展存在检测 | 组合使用低冲突插件，或采用内核级反检测工具 | 单一插件扰动容易被识别 |
| 特征不一致检测 | 确保所有指纹参数匹配（UA与系统版本、时区与IP地域一致） | 特征冲突是主要破绽 |
| 自动化行为检测 | 加入随机延迟、模拟人类操作轨迹 | 避免高频、规律请求 |
| webdriver检测 | Hook navigator.webdriver 设为false | 绕过Selenium/Puppeteer检测 |

### 指纹伪造与动态轮换

#### 底层注入替换
基于Firefox/Chrome内核深度定制（如Camoufox），在C++层拦截替换Navigator、Canvas、WebGL等API返回值，**不依赖JS注入**，避免被检测。

#### 指纹智能轮换
按会话/请求动态更新指纹参数（UA、分辨率、时区、Canvas哈希），防止固定指纹被标记。

#### 环境一致性伪造
同步匹配IP地域、时区、语言、浏览器版本，避免特征冲突（如美国IP+中文时区）。

### 反检测进阶技巧

- **环境隔离**：每个账号分配独立浏览器实例、独立IP、独立缓存，避免指纹交叉关联
- **行为模拟**：通过脚本模拟人类操作（随机鼠标移动、点击间隔、滚动速度），降低行为异常检测概率
- **特征降噪**：关闭非必要API（如摄像头、麦克风、磁盘访问），减少指纹暴露点
- **对抗检测逻辑**：Hook检测脚本，伪造检测结果，绕过webdriver检测

### 主流工具对比

| 工具类型 | 代表工具 | 核心功能 | 适用场景 |
|----------|----------|----------|----------|
| 反检测浏览器 | Camoufox、候鸟浏览器、AdsPower | 独立指纹环境、内核级伪造、多账号隔离 | 跨境电商、多账号运营、批量爬虫 |
| 反指纹插件 | CanvasBlocker、Chameleon、WebGL Defender | 阻断/扰动Canvas、WebGL、Audio指纹 | 个人隐私保护、轻量反检测 |
| 自动化反检测库 | puppeteer-extra-plugin-stealth | 隐藏webdriver标识、模拟真实插件、补全浏览器特征 | Puppeteer/Playwright爬虫反检测 |

### 避坑要点

- 反检测≠隐身，核心是**降低指纹唯一性**
- 过度伪造会引入新特征，反而更容易被标记
- 指纹参数应保持合理范围，非必要不做过极端配置

## 关键要点总结

- Canvas 指纹最常见，通过 toDataURL 返回值生成
- WebGL 指纹的关键：UNMASKED_VENDOR(0x9245) 和 UNMASKED_RENDERER(0x9246)
- AudioContext 通过 oscillator + compressor 链路生成
- 补环境时所有指纹值应与目标浏览器保持一致
- 可使用浏览器多开工具管理不同指纹配置
- 指纹伪造需注重环境一致性，避免特征冲突
- 行为模拟可有效降低自动化行为检测概率

## 相关主题
- → [补环境进阶](../03-environment/env-simulation-advanced.md)
- → [无头浏览器方案](headless-browser.md)
- → [补环境实战流程](../03-environment/env-simulation-practice.md)
