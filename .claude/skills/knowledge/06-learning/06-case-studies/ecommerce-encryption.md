# 电商平台加密参数逆向实战

> 来源: [JavaScript逆向工程：原理、技术与实践](https://blog.51cto.com/boss/14102684) | [JS逆向完整技能图谱](https://51rexue.cn/blog/50)

## 概述

电商平台普遍使用前端加密保护用户数据和接口安全。本文以典型电商场景为例，介绍加密参数（密码加密、请求签名等）的逆向分析流程。

## 常见电商加密场景

### 1. 登录密码加密
```
用户输入密码 → 前端 RSA 公钥加密 → Base64 编码 → POST 到后端
```

### 2. 请求签名（Sign）
```
请求参数按 key 排序 → 拼接为字符串 → 加盐 → MD5/SHA256 → sign 参数
```

### 3. 数据加密传输
```
明文 JSON → AES-CBC 加密 → Base64 编码 → 发送到后端
AES Key 通过 RSA 公钥加密 → 一起发送
```

### 4. Token / Cookie 生成
```
浏览器指纹 + 时间戳 + 服务端种子 → 自定义算法 → 生成 Token
```

## 实战分析流程

### Case：登录接口加密分析

#### Step 1：Network 抓包分析

```
POST /api/login HTTP/1.1
Content-Type: application/json

{
    "username": "user123",
    "password": "encrypted_password_here...",
    "sign": "a1b2c3d4e5f6...",
    "timestamp": 1700000000000,
    "nonce": "abc123"
}
```

观察要点：
- `password` 字段不是明文 → 有前端加密
- `sign` 字段 → 请求签名
- `timestamp` + `nonce` → 防重放

#### Step 2：XHR 断点定位

```
Sources → XHR Breakpoints → 添加 "/api/login"
触发登录 → 断在 fetch/XHR.send 处
```

#### Step 3：Call Stack 回溯

```
Call Stack:
    send         ← 当前位置
    submitLogin  ← 登录提交函数
    encryptData  ← 加密函数 ★
    onClick      ← 按钮点击事件
```

#### Step 4：分析加密函数

```javascript
function encryptData(formData) {
    // 1. RSA 加密密码
    var encrypt = new JSEncrypt();
    encrypt.setPublicKey(rsaPublicKey);
    var encryptedPwd = encrypt.encrypt(formData.password);

    // 2. 生成签名
    var params = {
        username: formData.username,
        password: encryptedPwd,
        timestamp: Date.now(),
        nonce: generateNonce()
    };
    params.sign = generateSign(params);

    return params;
}
```

#### Step 5：分析签名算法

```javascript
function generateSign(params) {
    // 按参数名排序
    var keys = Object.keys(params).sort();
    // 拼接
    var str = keys.map(k => k + '=' + params[k]).join('&');
    // 加盐
    str += '&key=' + secretKey;
    // MD5
    return MD5(str);
}
```

#### Step 6：Python 还原

```python
import hashlib
import time
import json
import requests
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_v1_5
import base64

class EcommerceLogin:
    def __init__(self):
        self.rsa_public_key = """-----BEGIN PUBLIC KEY-----
        MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQC...
        -----END PUBLIC KEY-----"""
        self.secret_key = 'extracted_secret_key'

    def rsa_encrypt(self, data):
        key = RSA.import_key(self.rsa_public_key)
        cipher = PKCS1_v1_5.new(key)
        encrypted = cipher.encrypt(data.encode())
        return base64.b64encode(encrypted).decode()

    def generate_sign(self, params):
        keys = sorted(params.keys())
        str_to_sign = '&'.join(f'{k}={params[k]}' for k in keys)
        str_to_sign += f'&key={self.secret_key}'
        return hashlib.md5(str_to_sign.encode()).hexdigest()

    def login(self, username, password):
        encrypted_pwd = self.rsa_encrypt(password)
        params = {
            'username': username,
            'password': encrypted_pwd,
            'timestamp': str(int(time.time() * 1000)),
            'nonce': self.generate_nonce()
        }
        params['sign'] = self.generate_sign(params)

        response = requests.post(
            'https://example.com/api/login',
            json=params
        )
        return response.json()

    def generate_nonce(self):
        import random, string
        return ''.join(random.choices(string.ascii_letters + string.digits, k=8))
```

## 密钥提取技巧

### RSA 公钥
```javascript
// 搜索特征
"-----BEGIN PUBLIC KEY-----"
"BEGIN RSA PUBLIC KEY"
JSEncrypt
setPublicKey
rsaPublicKey
```

### AES 密钥
```javascript
// 搜索特征
CryptoJS.AES.encrypt
mode: CryptoJS.mode.CBC
iv: CryptoJS.enc.Utf8.parse

// 密钥来源：
// 1. 硬编码在 JS 中
// 2. 从接口获取
// 3. 从 Cookie 中提取
// 4. 动态生成（需要抓取）
```

### 签名密钥（Salt）
```javascript
// 搜索特征
"key="
"secret"
"salt"
"&key=" + someVar
```

## 关键要点总结

- 电商加密通常组合使用：RSA + AES + MD5/SHA256
- 密码加密：RSA 公钥加密（公钥通常硬编码在前端）
- 请求签名：参数排序 + 拼接 + 加盐 + 哈希
- XHR 断点 + Call Stack 回溯是定位加密逻辑的标准方法
- Python 还原时注意对比浏览器结果验证正确性

## 相关主题
- → [加密算法识别](../04-algorithms/crypto-identification.md)
- → [算法还原实战](../04-algorithms/algorithm-reduction.md)
- → [搜索定位技巧](../01-basics/search-locate.md)
