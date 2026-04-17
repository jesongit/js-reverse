# qq_mail

一个基于 QQ 邮箱的 IMAP / SMTP 辅助工具目录，当前主要提供：

- IMAP IDLE 实时监听新邮件
- 按收件人轮询查询最新邮件
- 通过 QQ SMTP 发送邮件
- 用于验证码拉取、自测通知、注册流程邮件读取

当前核心脚本：
- `qq_mail_idle.py`

## 适用场景

- 自动化注册流程中的邮箱验证码拉取
- 等待指定收件地址收到最新邮件
- 本地调试 IMAP/SMTP 是否可用
- 简单发信通知

## 依赖安装

如果由其他项目统一安装依赖，可直接复用对应 `requirements.txt`。

单独使用时，至少需要：

```bash
pip install imaplib2
```

推荐在仓库根目录 `.env` 中配置：

```env
QQ_MAIL_IMAP_USER=your_qq_mail@qq.com
QQ_MAIL_IMAP_PASSWORD=your_authorization_code
QQ_MAIL_SMTP_USER=your_qq_mail@qq.com
QQ_MAIL_SMTP_PASSWORD=your_authorization_code
```

脚本启动时会优先加载仓库根目录 `.env`，也支持直接从系统环境变量读取。

## 配置说明

当前脚本优先从环境变量读取 QQ 邮箱连接参数：

- `QQ_MAIL_IMAP_HOST`
- `QQ_MAIL_IMAP_PORT`
- `QQ_MAIL_IMAP_USER`
- `QQ_MAIL_IMAP_PASSWORD`
- `QQ_MAIL_SMTP_HOST`
- `QQ_MAIL_SMTP_PORT`
- `QQ_MAIL_SMTP_PORT_FB`
- `QQ_MAIL_SMTP_USER`
- `QQ_MAIL_SMTP_PASSWORD`

未提供时，会退回到脚本中的默认主机和端口，但账号与授权码应通过环境变量提供。

推荐至少配置：

- `QQ_MAIL_IMAP_USER`
- `QQ_MAIL_IMAP_PASSWORD`

并确保 QQ 邮箱已开启 IMAP / SMTP，使用授权码而不是登录密码。

## 核心能力

### 1. IDLE 实时监听

`QQMailIDLE` 使用 `imaplib2` 的 IDLE 模式监听收件箱新邮件，适合长时间等待新邮件到达的场景。

示例：

```python
from qq_mail_idle import QQMailIDLE


def on_new_mail(sender, subject, body):
    print(sender, subject, body[:100])


listener = QQMailIDLE()
listener.subscribe(on_new_mail)
listener.start()
input("按回车停止...")
listener.stop()
```

### 2. 按收件人查询最新邮件

`fetch_latest_mail_to()` 适合验证码场景，会轮询 INBOX，返回发给指定邮箱地址的最新符合条件的一封邮件。

示例：

```python
from qq_mail_idle import fetch_latest_mail_to

mail = fetch_latest_mail_to(
    to_addr="example@pid.im",
    sent_after=None,
    sender_filter="notion",
    timeout=90,
    poll_interval=3,
)

print(mail)
```

返回字段：

- `sender`
- `subject`
- `body`
- `date`
- `ts`

### 3. 发送邮件

`send_email()` 会优先尝试 587 STARTTLS，失败后再尝试 465 SSL。

示例：

```python
from qq_mail_idle import send_email

send_email("target@example.com", "测试主题", "测试正文")
```

## 自测

```bash
python utils/qq_mail/qq_mail_idle.py --test
```

该命令会：

1. 启动 IDLE 监听
2. 向当前配置邮箱发送一封测试邮件
3. 等待并验证是否成功收到

## 与项目的关系

当前仓库中，`projects/notion2api/auto_register.py` 已复用 `fetch_latest_mail_to()` 拉取 Notion 注册验证码。

如果后续还有其他项目需要邮箱验证码能力，优先复用这个目录下的脚本，而不是重新实现一套 IMAP 逻辑。

## 注意事项

- 当前脚本包含真实邮箱账号和授权码配置，使用前应注意本地环境安全
- 邮件较多时，历史未读邮件可能干扰判断，验证码场景应配合 `to_addr`、`sent_after`、`sender_filter` 一起过滤
- 如果要长期复用，后续更适合把账号配置迁移到环境变量，而不是继续硬编码在脚本里
