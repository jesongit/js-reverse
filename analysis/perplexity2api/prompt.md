在工作目录：analysis/perplexity2api 下 使用 js-reverse 分析目标url
目标URL：https://www.perplexity.ai
1. 对话转成 Open API的方案
2. 分析清楚对应的请求构造、所有模型映射,并且通过真实对话测试清楚哪些模型可用
3. 获取真实流式响应和最小必要 headers/cookies
4. 能进行会话状态维护
5. 分析清楚AI对话相关的API，包括但不限于额度之类的
6. 必须交付可独立运行的python脚本，进行验证可行后才能交付

工作目录：analysis/perplexity2api 下 使用 js-reverse 分析目标url 的完整注册流程
目标URL：https://www.perplexity.ai/onboarding/org/create
1. 使用邮箱注册，使用 utils/qq_mail 的配置和脚本实现收码
2. 优先使用纯脚本注册方案，可用 cloudscraper 通过 cloudflare 的教研，必须尝试所有脚本方案不可行，才可用浏览器自动化方案
6. 必须交付可独立运行的python脚本，进行验证可行后才能交付
