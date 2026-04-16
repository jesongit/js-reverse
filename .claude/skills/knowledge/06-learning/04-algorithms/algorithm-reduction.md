# 算法还原实战

> 来源: [JS逆向完整技能图谱](https://51rexue.cn/blog/50) | [JavaScript逆向工程：原理、技术与实践](https://blog.51cto.com/boss/14102684)

## 概述

算法还原是指通过逆向分析 JS 代码，理解加密/签名算法的完整逻辑，并用 Python 等语言重新实现。本文介绍标准的算法还原流程。

## 算法还原流程

### Step 1：定位加密函数

1. 通过 XHR 断点 / Hook 定位发送请求的位置
2. 通过 Call Stack 回溯找到加密函数
3. 确认加密函数的输入和输出

### Step 2：分析加密参数

```
请求中的加密参数：
├── password: RSA(AES(plaintext))
├── sign: MD5(timestamp + nonce + data + secretKey)
├── token: Base64(header.payload.signature)
└── encrypted_data: AES-CBC(data, key, iv)
```

### Step 3：确定加密方式

1. 查看加密函数的调用方式
2. 确定加密库名（CryptoJS / forge / 原生实现）
3. 确定算法类型和参数

### Step 4：提取密钥和参数

```javascript
// 常见密钥来源
// 1. 固定在代码中
var key = '1234567890abcdef';

// 2. 从接口获取
fetch('/api/getKey').then(res => res.json());

// 3. 动态生成
var key = CryptoJS.lib.WordArray.random(16);

// 4. 从 Cookie / localStorage 读取
var key = document.cookie.match(/key=([^;]+)/)[1];
```

### Step 5：用 Python 重新实现

```python
import hashlib
import base64
from Crypto.Cipher import AES
from Crypto.PublicKey import RSA

# MD5 签名
def md5_sign(data, salt=''):
    return hashlib.md5((data + salt).encode()).hexdigest()

# AES-CBC 加密
def aes_encrypt(data, key, iv):
    cipher = AES.new(key.encode(), AES.MODE_CBC, iv.encode())
    # PKCS7 padding
    pad_len = 16 - len(data) % 16
    data += chr(pad_len) * pad_len
    return base64.b64encode(cipher.encrypt(data.encode())).decode()

# RSA 加密
def rsa_encrypt(data, public_key):
    key = RSA.import_key(public_key)
    # 通常使用 PKCS1_v1_5
    from Crypto.Cipher import PKCS1_v1_5
    cipher = PKCS1_v1_5.new(key)
    return base64.b64encode(cipher.encrypt(data.encode())).decode()
```

## CryptoJS与AES加密基础

### AES加密核心参数

| 参数 | 说明 | 常见值 |
|------|------|--------|
| 密钥（Key） | 加密核心，128/192/256位 | 固定值或动态生成 |
| 偏移量（IV） | CBC模式必需，增强加密安全性 | 固定值或随机生成 |
| 模式（Mode） | CBC/ECB/CTR/GCM | CBC最常用 |
| 填充方式（Padding） | PKCS7/ISO10126/ZeroPadding | PKCS7默认 |

### AES/CryptoJS逆向标准化流程

#### 步骤1：定位加密入口（抓包+全局搜索）
- 用Chrome DevTools或Charles/Fiddler抓包，定位含加密参数（encryptData、cipherText、sign）的请求
- 全局搜索关键词：`AES`、`CryptoJS`、`encrypt`、`decrypt`、`Key`、`IV`，定位加密函数
- 分析调用堆栈，找到加密函数入口（如`CryptoJS.AES.encrypt`）

#### 步骤2：代码反混淆与调试
- 若代码被混淆（如Obfuscator、JSFuck），用de4js、js-deobfuscator、AST反混淆工具还原代码结构
- 在加密函数处打断点，单步调试，观察参数传递、密钥/IV生成逻辑

#### 步骤3：提取核心参数与算法
- **密钥（Key）**：硬编码在JS中、通过接口获取、由用户密码派生（如PBKDF2）
- **偏移量（IV）**：固定值、随机生成、与密钥关联生成
- **确认加密模式与填充方式**：CBC+PKCS7是最常见组合

#### 步骤4：算法复现与验证
```python
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
import base64

def aes_encrypt(plaintext, key, iv):
    # 密钥/IV需转为16字节（AES-128）
    key = key.encode('utf-8')[:16]
    iv = iv.encode('utf-8')[:16]
    cipher = AES.new(key, AES.MODE_CBC, iv)
    # PKCS7填充
    padded_plaintext = pad(plaintext.encode('utf-8'), AES.block_size)
    ciphertext = cipher.encrypt(padded_plaintext)
    return base64.b64encode(ciphertext).decode('utf-8')

# 测试
key = "1234567890123456"
iv = "abcdefghijklmnop"
plaintext = "test_data"
print(aes_encrypt(plaintext, key, iv))
```

### 逆向进阶技巧

- **Hook加密函数**：用Tampermonkey、Fiddler AutoResponder注入脚本，Hook `CryptoJS.AES.encrypt`，直接获取明文、密钥、密文
- **补环境运行**：将加密代码复制到Node.js，补全浏览器环境（如window、navigator），直接运行加密函数获取结果
- **对抗密钥动态生成**：分析密钥派生逻辑（如MD5、SHA256、PBKDF2），复现密钥生成流程

### 常见加密逆向误区

| 误区 | 真相 |
|------|------|
| 混淆≠加密 | Base64、URL编码是编码，非加密，可直接解码 |
| 哈希不可逆 | MD5、SHA是哈希算法，无法直接还原明文，仅可通过彩虹表碰撞弱密码 |
| IV固定风险 | CBC模式IV固定会导致相同明文生成相同密文，易被破解，逆向时需重点关注IV生成逻辑 |

## 常见加密组合模式

### 模式 1：前端加密密码
```
原始密码 → RSA 公钥加密 → Base64 编码 → 发送到后端
```

### 模式 2：请求签名
```
请求参数排序 → 拼接 → 加 Salt → MD5/SHA256 → sign 参数
```

### 模式 3：数据加密传输
```
明文数据 → AES 加密（随机 key）→ RSA 加密 key → 一起发送
```

### 模式 4：Token 机制
```
登录 → 获取 token → 后续请求带 token → token 过期刷新
```

## 实战技巧

### 1. 对比验证
```python
# 浏览器中的加密结果
browser_result = "abc123..."

# Python 实现的结果
python_result = your_encrypt("same_input")

# 对比
assert browser_result == python_result, "结果不一致，检查实现"
```

### 2. 逐步调试
```javascript
// 在加密函数的每一步打印中间结果
function encrypt(data) {
    var step1 = preProcess(data);     console.log('step1:', step1);
    var step2 = addSalt(step1);       console.log('step2:', step2);
    var step3 = md5(step2);           console.log('step3:', step3);
    var step4 = base64Encode(step3);  console.log('step4:', step4);
    return step4;
}
```

### 3. 扣代码 vs 重写

| 场景 | 推荐方式 |
|------|---------|
| 标准 MD5/SHA/AES | Python 库重写 |
| 标准 RSA | Python 库重写 |
| 自定义算法 | 扣 JS 代码到 Node 运行 |
| 复杂混淆算法 | 补环境直接执行 |
| 简单运算 | Python 重写 |

## 关键要点总结

- 先定位，再分析，最后重写——标准的逆向三步流程
- 确认加密库名后选择对应的 Python 库
- 密钥来源：固定值 / 接口获取 / 动态生成 / Cookie 读取
- 始终对比浏览器结果和 Python 结果验证正确性
- 标准算法优先用 Python 库重写，自定义算法考虑扣代码

## 相关主题
- → [加密算法识别](crypto-identification.md)
- → [自定义算法分析](custom-algorithms.md)
- → [电商平台加密实战](../06-case-studies/ecommerce-encryption.md)
