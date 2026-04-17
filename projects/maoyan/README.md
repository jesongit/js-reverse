# 猫眼票房逆向分析报告

> 目标：`https://piaofang.maoyan.com/dashboard`
> 日期：2026-04-17
> 复杂度定级：L2（单层壳 - 简单混淆 + 一层 MD5 签名 + 字体反爬）

---

## 一、最终交付物

| 文件 | 说明 |
|------|------|
| `get_box_office.py` | 纯 requests 实现，可直接运行获取票房数据 |

依赖：`requests`、`fonttools`、`Pillow`，无需浏览器自动化。

---

## 二、目标接口分析

### 数据接口

```
GET https://piaofang.maoyan.com/i/api/dashboard-ajax
```

### 请求参数

| 参数 | 来源 | 说明 |
|------|------|------|
| `orderType` | 固定值 `0` | 排序类型 |
| `uuid` | Cookie `_lxsdk_cuid` | 灵犀 SDK 生成的设备标识 |
| `timeStamp` | 毫秒时间戳 | 当前时间 |
| `User-Agent` | `btoa(navigator.userAgent)` | UA 的 Base64 编码 |
| `index` | `Math.floor(Math.random() * 1000 + 1)` | 1-1000 随机数 |
| `channelId` | 固定值 `40009` | 渠道编号 |
| `sVersion` | 固定值 `2` | 版本号 |
| `signKey` | MD5 签名 | 见算法一 |
| `WuKongReady` | 固定值 `h5` | 标记位 |

### 关键请求头

| 头 | 来源 | 说明 |
|----|------|------|
| `uid` | 主页 HTML `<meta name="csrf">` | CSRF 令牌，每次访问主页获取 |
| `mygsig` | `basic_tools_js` 生成 | 反爬签名，见算法二 |
| `m-appkey` | 固定 `fe_com.sankuai.movie.fe.ipro` | 应用标识 |
| `m-traceid` | 随机 19 位数字 | 链路追踪 |

### Cookie

| Cookie | 来源 | 说明 |
|--------|------|------|
| `_lxsdk_cuid` | 客户端生成 | 设备唯一标识 |
| `_lxsdk` | 同 `_lxsdk_cuid` | 灵犀 SDK 标识 |
| `_lx_utm` | 固定值 | 来源追踪 |

---

## 三、逆向算法详解

### 算法一：signKey

**源码位置**：`largeScreenDashboardIndex_ce470ecf.js` → `getQueryKey` 函数

**定位过程**：
1. 搜索 `signKey` 在源码中的赋值位置
2. 发现 `getQueryKey` 函数构建参数对象后做 MD5

**算法**：
```
拼接串 = "method=GET&timeStamp={ts}&User-Agent={btoa(ua)}&index={随机}&channelId=40009&sVersion=2&key=A013F70DB97834C0A5492378BD76C53A"
signKey = MD5(拼接串)
```

**踩坑**：
- `method` 默认值为 `"GET"` 而非 `undefined`（解构赋值时 `_ref.method` 默认 `'GET'`）
- 初步误以为是 `undefined`，导致 MD5 计算结果不匹配
- 通过在 `getQueryKey` 函数设断点，捕获 scope 变量才确认 `r = "GET"`

### 算法二：mygsig

**源码位置**：`basic_tools_js/0.0.67_tool.js` → `getMygsig` 函数（高度混淆）

**定位过程**：
1. 搜索 `mygsig` 请求头来源，发现由 `WuKong_1.0.2.min.js` 拦截 XHR 请求时注入
2. 追踪到 `getMygsig` 函数，在混淆代码中设断点
3. 逐步 step over 捕获每个中间变量

**算法**：
```python
# 1. 解析 URL 查询参数为字典
params = parse_query_string(url)

# 2. 加入 path 字段（URL 路径）
params["path"] = "/i/api/dashboard-ajax"

# 3. 按 key 的 toLowerCase() 排序
sorted_keys = sorted(params.keys(), key=lambda k: k.lower())

# 4. 提取值，用下划线连接
joined = "_".join(str(params[k]) for k in sorted_keys)

# 5. 拼接待哈希串
hash_input = "581409236#" + joined + "$" + 当前时间戳

# 6. MD5 得到 ms1
ms1 = MD5(hash_input)

# 7. 组装 JSON
mygsig = {"m1":"0.0.3", "m2":0, "m3":"0.0.67_tool", "ms1":ms1, "ts":ts, "ts1":页面加载时间戳}
```

**关键混淆字符串解码**（通过 evaluate_script 调用混淆解码函数）：

| 混淆调用 | 实际值 | 含义 |
|----------|--------|------|
| `f(0x335)` | `"581409236#"` | 哈希前缀 |
| `f(0xf3)` | `"path"` | URL路径字段名 |
| `f(0x219)` | `"ms1"` | 签名字段名 |
| `f(0x1bd)` | `"ts1"` | 页面时间戳字段名 |
| `f(0x297)` | `"parseQueryString"` | URL解析方法 |
| `f(0x1a8)` | `"MyH5Guard"` | 全局对象名 |

**踩坑**：
- 初步分析时遗漏了 `path` 字段，mygsig 中的参数对象必须包含 `path`（URL路径），否则服务器返回 403
- `ts`（哈希后缀时间戳）和 mygsig JSON 中的 `ts` 必须是同一个值，不能两次调用 `time.time()`
- 必须添加 `sec-ch-ua` 等浏览器特征头

### 算法三：字体反爬解码

**机制**：
- 响应中 `boxSplitUnit.num` 字段包含 HTML 实体编码的 PUA 字符（如 `&#xe3df;`）
- 响应中 `fontStyle` 包含动态 woff 字体 URL
- 字体将 10 个 PUA 编码映射到 0-9 数字的字形
- 每次请求字体不同（PUA 编码变化），但字形形状一致

**解码方案（Pillow 像素匹配）**：
1. 下载 woff 字体
2. 用 Arial 渲染 0-9 作为参考模板
3. 用自定义字体渲染每个 PUA 字符
4. 贪心匹配：按像素相似度降序分配，每个 PUA 只匹配一个数字

**踩坑**：
- 起初用 fonttools 的面积/轮廓数特征匹配，只能识别部分数字（如区分出 8 和 0，但无法区分 1/2/3 等）
- 用 Canvas 在浏览器中匹配时，如果参考数字也用自定义字体渲染，会导致自引用问题（两个字符都匹配到 8）
- 最终方案：用系统字体 Arial 渲染参考 + 贪心分配，解决了自引用和部分匹配问题

---

## 四、完整游客态链路

```
1. 生成 _lxsdk_cuid 格式 UUID
2. 设置 Cookie: _lxsdk_cuid, _lxsdk, _lx_utm
3. GET 主页 → 提取 <meta name="csrf"> content 作为 uid
4. 计算 signKey = MD5(固定参数拼接串)
5. 构建查询参数（含 signKey）
6. 计算 mygsig = MD5(参数值排序拼接 + 前缀 + 时间戳)
7. 发送 GET /i/api/dashboard-ajax（带 uid、mygsig、sec-ch-ua 等头）
8. 解码响应中的字体反爬
```

---

## 五、问题复盘

### 问题 1：method 默认值误判

**现象**：signKey MD5 计算结果与浏览器不一致
**原因**：`getQueryKey` 中 `method` 的解构默认值是 `'GET'`，不是 `undefined`
**解决**：设断点在 `getQueryKey` 入口，检查 scope 变量确认 `r = "GET"`
**耗时**：约 30 分钟

### 问题 2：mygsig 缺少 path 字段

**现象**：纯 requests 请求始终返回 403
**原因**：mygsig 的哈希输入中需要包含 URL 的 `path` 字段，而不仅仅是查询参数
**解决**：通过 step over 逐步追踪 getMygsig 内部变量，发现合并对象中包含 `path` 键
**耗时**：约 1 小时（包括排查各种其他可能原因）

### 问题 3：字体解码不完整

**现象**：用面积/轮廓数方法只能识别 8、0、小数点等少数字符
**原因**：面积法不足以区分所有数字（如 2 和 3 的面积可能接近）
**解决**：改为 Pillow 渲染 + 像素匹配法，用 Arial 参考模板做贪心匹配
**耗时**：约 40 分钟

### 问题 4：先尝试 Playwright 方案绕过

**现象**：遇到 403 后直接转向 Playwright
**原因**：mygsig 混淆度高，初期判断逆向成本太高
**教训**：应该先坚持逆向核心算法再考虑备选方案。混淆不等于复杂，核心逻辑可能很简单（本例就是 MD5）

---

## 六、工具使用经验

### 高效定位技巧

| 场景 | 工具 | 方法 |
|------|------|------|
| 找签名函数 | `search_in_sources` | 搜索 signKey/mygsig 等关键字 |
| 确认算法 | `set_breakpoint_on_text` + `get_paused_info` | 断点捕获 scope 变量 |
| 追踪混淆代码 | `step`(over/into) + `evaluate_script` | 逐步执行并读取中间值 |
| 解码混淆字符串 | `evaluate_script` | 调用混淆解码函数 f(0xNNN) 获取明文 |
| 验证算法 | Python 直接计算 | 对比浏览器捕获值与 Python 计算结果 |

### 效率提升建议

1. **先搜索关键字定位函数**，再设断点确认细节
2. **混淆代码的解码函数是关键**，获取到 `_0x4a6326(0xNNN)` 对应的明文值后，算法逻辑就清晰了
3. **Python 验证要趁早**，每次逆向一个算法就立即用 Python 验证，不要累积到最后
4. **403 时优先排查算法正确性**，而非立即转向浏览器自动化

---

## 七、对本项目 skill 的优化建议

详见 skill 文件更新。
