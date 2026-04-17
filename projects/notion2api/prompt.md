在notion2api 目录下 使用 js-reverse 帮我实现把网页对话转成 Open API 的功能
目标URL：https://www.notion.so/ai

继续，但是注意下面两点
1. 因为免费账号对话次数有限，我换了个号，你可以继续你的工作
2. 在notion2api 目录拉取了一个 notion-2api 的类似项目，根据他的项目，看看我们的功能没有可以优化或者增强的地方，可以包括他实现或者没实现的


工作目录：notion2api
目标url：https://www.notion.so/signup?from=marketing&pathname=%2F
使用 js-reverse 分析 notion注册流程，增加自动注册的功能，你如果有更好的建议可以告诉我，
需要交付可自动注册账号然后获取对应env参数，然后可以提供 API的 python 脚本
邮箱可以使用 notion+时间戳+@pid.im(比如 notion123@pid.im)
使用 utils/qq_mail 中的脚本通过 imap 服务器 获取验证码，对应的配置已经写好，可以直接使用
使用邮箱注册，过程中需要取消勾选 "我同意接收 Notion 的推广信息"