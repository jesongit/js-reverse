# JS 逆向脚手架

为 AI Agent 设计的 JavaScript 逆向工程工具集，基于 Chrome DevTools 协议和 Patchright 反检测浏览器。

## 项目结构

```
js-reverse/
├── js-reverse-mcp/          # 核心 MCP 服务器
│   ├── src/                  # 源代码
│   │   ├── tools/            # MCP 工具实现（23个工具）
│   │   ├── formatters/       # 响应格式化
│   │   ├── trace-processing/ # 性能追踪解析
│   │   └── utils/            # 工具函数
│   ├── tests/                # 测试用例
│   └── docs/                 # 技术文档
└── CLAUDE.md                 # Claude Code 使用指南
```

## 快速开始

### 使用 npx（推荐）

在 MCP 客户端配置中添加：

```json
{
  "mcpServers": {
    "js-reverse": {
      "command": "npx",
      "args": ["js-reverse-mcp"]
    }
  }
}
```

### Claude Code

```bash
claude mcp add js-reverse npx js-reverse-mcp
```

## 核心能力

| 类别 | 工具数 | 说明 |
|------|--------|------|
| 页面与导航 | 5 | 新建页面、导航、截图 |
| 脚本分析 | 4 | 列出脚本、搜索代码、保存源码 |
| 断点调试 | 7 | 设置断点、条件断点、单步执行、函数追踪 |
| 网络分析 | 3 | XHR 断点、WebSocket 分析、请求溯源 |
| 执行控制 | 4 | 代码注入、运行时求值、控制台消息 |

## 反检测机制

- **Patchright 引擎**：C++ 层反检测 patch，移除 `navigator.webdriver` 等泄露
- **60+ 隐身启动参数**：移除自动化特征、绕过无头检测
- **CDP 静默导航**：导航时暂不激活调试协议，避免被反爬脚本检测
- **Google Referer 伪装**：自动携带 Google 来源头

已在知乎、Google 等有风控检测的站点验证通过。

## 系统要求

- Node.js v20.19 或更高版本
- Chrome 稳定版

## 详细文档

- [中文文档](js-reverse-mcp/README_zh.md)
- [英文文档](js-reverse-mcp/README.md)
- [工具参考](js-reverse-mcp/docs/tool-reference.md)
- [反检测工作记录](js-reverse-mcp/docs/anti-detection-work.md)

## 许可证

Apache-2.0
