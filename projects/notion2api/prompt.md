在notion2api 目录下 使用 js-reverse 帮我实现把网页对话转成 Open API 的功能
目标URL：https://www.notion.so/ai

继续，但是注意下面两点
1. 因为免费账号对话次数有限，我换了个号，你可以继续你的工作
2. 在notion2api 目录拉取了一个 notion-2api 的类似项目，根据他的项目，看看我们的功能没有可以优化或者增强的地方，可以包括他实现或者没实现的


工作目录：projects/notion2api
我已经提前分析了注册流程，你先仔细阅读一下 registration-analysis-report.md
目标url：https://www.notion.so/signup?from=marketing&pathname=%2F
使用 js-reverse 这个 skill，结合上面的分析报告，分析 notion注册流程，增加自动邮箱注册的功能
需要交付可自动注册账号然后获取对应env参数，然后可以提供 API的 python 脚本
邮箱可以使用 posase当前时间戳@pid.im，用户名使用邮箱前缀
需要取消勾选 "我同意接收 Notion 的推广信息"，用途页面选择私人
使用 utils/qq_mail 中的脚本通过 imap 服务器 获取验证码，对应的配置已经写好，可以直接使用


工作目录：projects/notion2api
继续优化 auto_register.py 使其不依赖mcp独立运行