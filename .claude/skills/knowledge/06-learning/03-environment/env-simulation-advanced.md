# 补环境进阶

> 来源: [JS逆向完整技能图谱](https://51rexue.cn/blog/50) | [JavaScript逆向的补环境入门](https://juejin.cn/post/7547933350213828660)

## 概述

进阶补环境涉及浏览器指纹相关的复杂 API 模拟，包括 Canvas、WebGL、AudioContext 等。这些 API 的返回值通常被用于环境检测和指纹生成。

## Canvas 指纹模拟

### Canvas 指纹原理
- 通过 `document.createElement('canvas')` 创建画布
- 绘制特定图形/文字
- 调用 `toDataURL()` 生成唯一指纹
- 不同硬件/驱动/字体渲染会产生不同结果

### Canvas 环境补齐

```javascript
// Canvas 元素模拟
function createCanvas() {
    const canvas = {
        tagName: 'CANVAS',
        width: 300,
        height: 150,
        style: {},
        getContext: function(type) {
            if (type === '2d') return createCanvas2DContext();
            if (type === 'webgl' || type === 'experimental-webgl') return createWebGLContext();
            return null;
        },
        toDataURL: function(type) {
            // 返回固定的 Canvas 指纹数据
            return 'data:image/png;base64,iVBORw0KGgo...';
        },
        toBlob: function(callback, type, quality) {
            callback(new Blob([''], { type: 'image/png' }));
        },
        addEventListener: function() {},
        removeEventListener: function() {}
    };
    return canvas;
}

// Canvas 2D 上下文
function createCanvas2DContext() {
    return {
        canvas: null,
        fillStyle: '#000000',
        strokeStyle: '#000000',
        font: '10px sans-serif',
        textAlign: 'start',
        textBaseline: 'alphabetic',
        globalAlpha: 1,
        globalCompositeOperation: 'source-over',
        fillRect: function() {},
        strokeRect: function() {},
        fillText: function(text, x, y) {},
        strokeText: function(text, x, y) {},
        measureText: function(text) {
            return { width: text.length * 6 };
        },
        beginPath: function() {},
        closePath: function() {},
        moveTo: function() {},
        lineTo: function() {},
        arc: function() {},
        rect: function() {},
        fill: function() {},
        stroke: function() {},
        save: function() {},
        restore: function() {},
        drawImage: function() {},
        createLinearGradient: function() {
            return { addColorStop: function() {} };
        },
        createRadialGradient: function() {
            return { addColorStop: function() {} };
        },
        getImageData: function(x, y, w, h) {
            return { data: new Uint8ClampedArray(w * h * 4) };
        },
        putImageData: function() {},
        isPointInPath: function() { return false; }
    };
}
```

## WebGL 指纹模拟

### WebGL 参数
```javascript
function createWebGLContext() {
    const params = {
        VERSION: 0x1F02,           // 'WebGL 1.0'
        SHADING_LANGUAGE_VERSION: 0x8B8C,
        VENDOR: 0x1F00,            // 'Google Inc. (NVIDIA)'
        RENDERER: 0x1F01,          // 'ANGLE (NVIDIA, ...) '
        MAX_TEXTURE_SIZE: 0x0D33,
        MAX_RENDERBUFFER_SIZE: 0x84E8,
        MAX_VIEWPORT_DIMS: 0x0D3A,
        MAX_CUBE_MAP_TEXTURE_SIZE: 0x851C,
        ALIASED_LINE_WIDTH_RANGE: 0x846E,
        ALIASED_POINT_SIZE_RANGE: 0x846D
    };

    return {
        getParameter: function(pname) {
            switch (pname) {
                case 0x1F02: return 'WebGL 1.0 (OpenGL ES 2.0 Chromium)';
                case 0x8B8C: return 'WebGL GLSL ES 1.0 (OpenGL ES GLSL ES 1.0 Chromium)';
                case 0x1F00: return 'Google Inc. (NVIDIA)';
                case 0x1F01: return 'ANGLE (NVIDIA, NVIDIA GeForce GTX 1060 6GB Direct3D11 vs_5_0 ps_5_0, D3D11)';
                case 0x1F03: return 'WebGL 1.0';
                case 0x0D33: return 16384;
                case 0x84E8: return 16384;
                case 0x0D3A: return new Int32Array([16384, 16384]);
                case 0x851C: return 16384;
                case 0x846E: return new Float32Array([1, 1]);
                case 0x846D: return new Float32Array([1, 1024]);
                case 0x9245: return 'extensions';  // UNMASKED_VENDOR
                case 0x9246: return 'Google Inc. (NVIDIA)'; // UNMASKED_RENDERER
                default: return null;
            }
        },
        getExtension: function(name) {
            if (name === 'WEBGL_debug_renderer_info') {
                return { UNMASKED_VENDOR_WEBGL: 0x9245, UNMASKED_RENDERER_WEBGL: 0x9246 };
            }
            if (name === 'EXT_texture_filter_anisotropic') {
                return { MAX_TEXTURE_MAX_ANISOTROPY_EXT: 0x84FF };
            }
            return {};
        },
        getSupportedExtensions: function() {
            return [
                'ANGLE_instanced_arrays', 'EXT_blend_minmax',
                'EXT_texture_filter_anisotropic', 'OES_texture_float',
                'WEBGL_debug_renderer_info', 'WEBGL_lose_context'
            ];
        },
        createBuffer: function() { return {}; },
        bindBuffer: function() {},
        bufferData: function() {},
        createProgram: function() { return {}; },
        createShader: function() { return {}; },
        shaderSource: function() {},
        compileShader: function() {},
        attachShader: function() {},
        linkProgram: function() {},
        getProgramParameter: function() { return true; },
        getShaderParameter: function() { return true; },
        useProgram: function() {},
        getAttribLocation: function() { return 0; },
        getUniformLocation: function() { return {}; },
        enableVertexAttribArray: function() {},
        vertexAttribPointer: function() {},
        uniform1f: function() {},
        drawArrays: function() {},
        clearColor: function() {},
        viewport: function() {},
        enable: function() {},
        disable: function() {},
        blendFunc: function() {},
        getContextAttributes: function() {
            return { alpha: true, antialias: true, depth: true, stencil: false };
        }
    };
}
```

### 重要 WebGL 常量
| 常量名 | 值 | 说明 |
|--------|-----|------|
| VENDOR | 0x1F00 | GPU 厂商 |
| RENDERER | 0x1F01 | GPU 渲染器 |
| VERSION | 0x1F02 | WebGL 版本 |
| UNMASKED_VENDOR | 0x9245 | 真实厂商（debug 扩展） |
| UNMASKED_RENDERER | 0x9246 | 真实渲染器（debug 扩展） |

## AudioContext 指纹模拟

```javascript
// AudioContext 模拟
global.AudioContext = function() {
    return {
        createOscillator: function() {
            return {
                type: 'triangle',
                frequency: { value: 10000, setValueAtTime: function() {} },
                connect: function() { return this; },
                start: function() {},
                stop: function() {},
                disconnect: function() {}
            };
        },
        createDynamicsCompressor: function() {
            return {
                threshold: { value: -50 },
                knee: { value: 40 },
                ratio: { value: 12 },
                reduction: { value: 0 },
                attack: { value: 0.003 },
                release: { value: 0.25 },
                connect: function() { return this; },
                disconnect: function() {}
            };
        },
        createAnalyser: function() {
            return {
                fftSize: 2048,
                frequencyBinCount: 1024,
                getFloatFrequencyData: function(arr) {
                    for (let i = 0; i < arr.length; i++) arr[i] = -100 + i * 0.1;
                },
                connect: function() { return this; },
                disconnect: function() {}
            };
        },
        createGain: function() {
            return {
                gain: { value: 1, setValueAtTime: function() {} },
                connect: function() { return this; },
                disconnect: function() {}
            };
        },
        createScriptProcessor: function(bufferSize) {
            return {
                onaudioprocess: null,
                connect: function() { return this; },
                disconnect: function() {}
            };
        },
        destination: {},
        sampleRate: 44100,
        state: 'running',
        currentTime: 0,
        close: function() { return Promise.resolve(); }
    };
};
global.OfflineAudioContext = global.AudioContext;
global.webkitAudioContext = global.AudioContext;
```

## 字体指纹模拟

```javascript
// 字体检测通常通过测量文字宽度判断
// 补法：返回标准宽度
function createFontMeasureContext() {
    const ctx = createCanvas2DContext();
    const originalMeasureText = ctx.measureText;

    ctx.measureText = function(text) {
        // 返回常见字体的标准宽度
        const widths = {
            'mmmmmmmmmmlli': { width: 84.5 },
            'monospace': { width: 120 }
        };
        return widths[text] || { width: text.length * 6 };
    };
    return ctx;
}
```

## 关键要点总结

- Canvas 指纹通过 toDataURL 返回值模拟，需确保值固定且合理
- WebGL 的关键参数：VENDOR(0x1F00)、RENDERER(0x1F01)、UNMASKED_VENDOR(0x9245)、UNMASKED_RENDERER(0x9246)
- AudioContext 指纹需完整模拟 oscillator + compressor + analyser 链路
- 所有模拟值应与目标浏览器的实际返回值一致
- 使用 Proxy 检测遗漏的属性访问

## 相关主题
- → [补环境概念与原理](env-simulation-intro.md)
- → [补环境实战流程](env-simulation-practice.md)
- → [浏览器指纹对抗](../05-advanced/browser-fingerprint.md)
