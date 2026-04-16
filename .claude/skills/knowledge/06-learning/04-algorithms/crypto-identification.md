# 加密算法识别

> 来源: [JS逆向完整技能图谱](https://51rexue.cn/blog/50) | [JavaScript逆向工程：原理、技术与实践](https://blog.51cto.com/boss/14102684)

## 概述

快速识别加密算法类型是逆向分析的关键能力。通过魔数（Magic Number）、输出长度、算法特征等可以快速判断使用的加密方式。

## 常见加密算法速查

### MD5
- **类型**：哈希（不可逆）
- **输出长度**：32 个十六进制字符（128 位）
- **特征**：输出为固定的 32 位 hex 字符串

**魔数（初始化常量）**：
```javascript
// MD5 初始化向量（几乎不会改变）
0x67452301
0xefcdab89
0x98badcfe
0x10325476

// MD5 常量表中的特征值
0x5a827999
0x6ed9eba1
```

**识别代码模式**：
```javascript
// 搜索特征
// 1. 初始化常量
var a = 0x67452301;
var b = 0xefcdab89;
var c = 0x98badcfe;
var d = 0x10325476;

// 2. 调用 CryptoJS
CryptoJS.MD5(data);

// 3. 输出格式
// e10adc3949ba59abbe56e057f20f883e
```

### SHA 系列

| 算法 | 输出长度 | 特征 |
|------|---------|------|
| SHA-1 | 40 hex (160 bit) | 已不安全，但仍常见 |
| SHA-256 | 64 hex (256 bit) | 最常用 |
| SHA-384 | 96 hex (384 bit) | 较少使用 |
| SHA-512 | 128 hex (512 bit) | 高安全需求 |

**SHA-256 魔数**：
```javascript
// SHA-256 初始哈希值（前 8 个素数的平方根小数部分）
0x6a09e667
0xbb67ae85
0x3c6ef372
0xa54ff53a
0x510e527f
0x9b05688c
0x1f83d9ab
0x5be0cd19
```

**识别代码模式**：
```javascript
CryptoJS.SHA1(data);
CryptoJS.SHA256(data);
// 或 forge 库
forge.md.sha256.create();
```

### AES

- **类型**：对称加密
- **模式**：ECB / CBC / CTR / GCM 等
- **密钥长度**：128 / 192 / 256 位

**S-Box（替换盒）**：
```javascript
// AES S-Box 的前几个值，这是最明显的 AES 特征
var SBOX = [
    0x63, 0x7c, 0x77, 0x7b, 0xf2, 0x6b, 0x6f, 0xc5,
    0x30, 0x01, 0x67, 0x2b, 0xfe, 0xd7, 0xab, 0x76,
    // ... 共 256 个值
];
```

**识别代码模式**：
```javascript
// CryptoJS AES
CryptoJS.AES.encrypt(data, key, { mode: CryptoJS.mode.CBC, padding: CryptoJS.pad.Pkcs7 });
CryptoJS.AES.decrypt(ciphertext, key);

// 特征：通常有 key + iv（CBC 模式）
// IV 通常是 16 字节
```

### RSA

- **类型**：非对称加密
- **特征**：公钥加密，私钥解密

**识别特征**：
```javascript
// JSEncrypt 库
var encrypt = new JSEncrypt();
encrypt.setPublicKey(publicKey);
var encrypted = encrypt.encrypt(data);

// forge 库
var publicKey = forge.pki.publicKeyFromPem(pem);
var encrypted = publicKey.encrypt(data);

// 特征：PEM 格式公钥
// "-----BEGIN PUBLIC KEY-----"
// "MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQC..."
```

### Base64

- **类型**：编码（非加密）
- **特征**：输出可能以 `=` 结尾，字符集为 A-Za-z0-9+/
- **长度**：总是 4 的倍数

```javascript
// 识别
btoa(data);        // 编码
atob(data);        // 解码
// 自定义 Base64
var base64chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
```

### HMAC

- **类型**：消息认证码
- **特征**：带密钥的哈希

```javascript
// CryptoJS HMAC
CryptoJS.HmacMD5(data, key);
CryptoJS.HmacSHA256(data, key);

// 识别特征：哈希函数 + 密钥
// 输出长度与底层哈希算法一致
```

## 算法识别流程

```
观察加密输出
    ↓
输出长度？
├── 32 hex → MD5
├── 40 hex → SHA-1
├── 64 hex → SHA-256 或 HMAC-SHA256
├── 可变长度 + "=" 结尾 → Base64（解码后看内容）
├── 可变长度 → AES/RSA（需要进一步分析）
    ↓
搜索代码中的魔数
    ↓
确认算法 → 定位密钥/参数 → 还原
```

## 搜索技巧

```javascript
// 在代码中搜索这些关键词快速定位
"0x67452301"     // MD5
"0x6a09e667"     // SHA-256
"0x63, 0x7c"     // AES S-Box
"BEGIN PUBLIC"   // RSA
"CryptoJS"       // CryptoJS 库
"forge"          // node-forge 库
```

## 关键要点总结

- 魔数是识别算法最直接的方式：MD5 的 `0x67452301`、SHA-256 的 `0x6a09e667`、AES S-Box 的 `0x63, 0x7c`
- 输出长度是快速判断的重要依据
- CryptoJS 是最常见的 JS 加密库，搜索 "CryptoJS" 可快速定位
- Base64 不是加密，经常作为编码层嵌套使用
- HMAC = 哈希 + 密钥，需要同时找到哈希算法和密钥

## 相关主题
- → [算法还原实战](algorithm-reduction.md)
- → [自定义算法分析](custom-algorithms.md)
- → [电商平台加密实战](../06-case-studies/ecommerce-encryption.md)
