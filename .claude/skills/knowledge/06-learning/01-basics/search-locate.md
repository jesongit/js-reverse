# 搜索定位技巧

> 来源: [JS逆向完整技能图谱](https://51rexue.cn/blog/50) | [JavaScript逆向工程：原理、技术与实践](https://blog.51cto.com/boss/14102684)

## 概述

在逆向分析中，快速定位加密函数的位置是第一步。掌握多种搜索和定位技巧，能大幅提升效率。

## 核心定位方法

### 1. 全局搜索（Ctrl+Shift+F）

在 Sources 面板中全局搜索关键词：

| 搜索目标 | 关键词示例 |
|----------|-----------|
| 接口 URL | `/api/encrypt`、`login` |
| 参数名 | `password`、`token`、`sign` |
| 加密方法特征 | `md5(`、`SHA256`、`AES.encrypt` |
| 编码特征 | `btoa(`、`atob(`、`encodeURIComponent` |
| 关键变量 | `encrypt`、`signature`、`secret` |

### 2. XHR 断点定位

最直接的定位方式：

1. Network 面板找到目标请求
2. Sources → XHR Breakpoints → 添加 URL 关键词
3. 触发请求 → 断在 `XMLHttpRequest.send()` 或 `fetch()` 处
4. 通过 Call Stack 向上回溯

### 3. 调用栈分析（Call Stack）

断点命中后：

1. 从栈顶（当前函数）开始查看
2. 逐层向下（调用者）检查
3. 关注函数名和参数传递
4. 在可疑函数处设置新断点重新触发

### 4. Initiator 发起者追踪

Network 面板中：
- 点击请求 → 查看 Initiator 列
- 显示发起该请求的 JS 文件和行号
- 点击直接跳转到源码位置

### 5. DOM 断点 + 事件断点

当加密结果写入 DOM 时：
- 右键目标元素 → Break on → subtree modifications
- 触发操作 → 断在 DOM 修改处
- 通过调用栈追踪加密函数

### 6. Console 辅助定位

```javascript
// 查看函数定义位置
console.log(someFunction);

// 监控函数调用
console.log(someFunction.toString());

// 查看对象所有属性
console.dir(targetObject);

// 追踪调用栈
function traceCalls() {
    console.trace('called from:');
}
```

### 7. Event Listeners 面板

- Elements 面板 → 选中触发的按钮/元素
- 右侧 Event Listeners 标签
- 查看绑定的事件处理函数
- 点击跳转到源码

## 进阶定位技巧

### 堆快照（Heap Snapshot）

当变量名被混淆，无法直接搜索时：

1. 触发加密前 → 拍摄堆快照
2. 执行加密操作
3. 再拍一次堆快照
4. 比较两次快照，找到新增的对象

### 覆盖率分析（Coverage）

1. Sources → Coverage 面板 → 开始录制
2. 触发加密操作
3. 查看哪些函数被执行（高亮显示）
4. 缩小可疑代码范围

### Performance 面板

1. 开始录制 → 触发加密 → 停止录制
2. 查看函数调用时间线
3. 找到耗时较长的加密函数

## 定位流程总结

```
Network 找到目标请求
    ↓
方式 A：XHR 断点 → 直接定位发送位置
    ↓
方式 B：全局搜索接口URL/参数名
    ↓
Call Stack 回溯调用链
    ↓
在关键函数设断点，重新触发验证
    ↓
确认加密函数位置和参数
```

## 关键要点总结

- XHR 断点是最直接的定位手段
- 全局搜索适合参数名未被混淆的场景
- 调用栈回溯是验证定位结果的标准方法
- 堆快照和覆盖率适合混淆严重的场景
- 多种方法组合使用效果最佳

## 相关主题
- → [浏览器开发者工具](browser-devtools.md)
- → [Hook 技术](hook-techniques.md)
- → [加密算法识别](../04-algorithms/crypto-identification.md)
