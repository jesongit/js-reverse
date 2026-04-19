# Perplexity models catalog

以下内容基于前端源码常量提取，主要来源于 `spa-shell-3LFiIR7O.js` 中的模型枚举、模式映射和默认配置。

## 1. 当前默认模型

- search: `turbo`
- research: `pplx_alpha`
- study: `pplx_study`
- agentic_research: `pplx_agentic_research`
- document_review: `pplx_document_review`
- browser_agent: `claude46sonnet`
- asi: `pplx_asi`

## 2. 前端明确展示的核心模型配置

| 显示名称 | 模型 ID | 模式 | Provider | 订阅层级 |
|---|---|---|---|---|
| Sonar | `experimental` | `search` | `PERPLEXITY` | `pro` |
| Claude Sonnet 4.6 | `comet_browser_agent_sonnet` | `browser_agent` | `ANTHROPIC` | `pro` |
| Claude Opus 4.7 | `comet_browser_agent_opus` | `browser_agent` | `ANTHROPIC` | `max` |
| Agent | `pplx_asi` | `asi` | `ANTHROPIC` | 未显式标注 |

## 3. 前端枚举中的主要搜索/推理模型

### Perplexity / 搜索类

- `turbo`
- `pplx_pro_upgraded`
- `pplx_pro`
- `experimental`
- `pplx_reasoning`
- `pplx_sonar_internal_testing`
- `pplx_sonar_internal_testing_v2`
- `pplx_study`
- `pplx_document_review`
- `pplx_agentic_research`
- `pplx_alpha`
- `pplx_beta`
- `pplx_business_assistant`

### OpenAI 相关

- `gpt4o`
- `gpt41`
- `gpt51`
- `gpt52`
- `gpt54`
- `gpt54mini`
- `gpt53codex`
- `gpt51_thinking`
- `gpt52_thinking`
- `gpt54_thinking`
- `gpt5`
- `gpt5_thinking`
- `gpt5_pro`
- `o4mini`
- `o3`
- `o3mini`
- `o3pro`
- `o3pro_research`
- `o3pro_labs`
- `o3_research`
- `o3_labs`
- `codex`

### Anthropic 相关

- `claude2`
- `claude37sonnetthinking`
- `claude40opus`
- `claude41opus`
- `claude40opusthinking`
- `claude41opusthinking`
- `claude46opus`
- `claude46opusthinking`
- `claude46sonnet`
- `claude46sonnetthinking`
- `claude45haiku`
- `claude45sonnet`
- `claude45sonnetthinking`
- `claude45opus`
- `claude45opusthinking`
- `claudecode`

### Google 相关

- `gemini25pro`
- `gemini31pro_high`
- `gemini30flash`
- `gemini30flash_high`
- `gemini`
- `gemini2flash`
- `gemini30pro`

### xAI / Grok 相关

- `grok`
- `grok2`
- `grok4`
- `grok4nonthinking`
- `grok41reasoning`
- `grok41nonreasoning`

### Moonshot / Kimi 相关

- `kimik25thinking`
- `kimik2thinking`
- `pplx_asi_kimi`

### 其他模型枚举

- `r1`
- `r1_1776`
- `llama_x_large`
- `mistral`
- `pplx_gamma`
- `testing_model_c`
- `claude_ombre_eap`
- `claude_lace_eap`
- `pplx_asi_qwen`
- `pplx_asi_sonnet`
- `pplx_asi_sonnet_thinking`
- `pplx_asi_gpt54`
- `pplx_asi_opus`
- `pplx_asi_opus_thinking`
- `pplx_asi_beta`

## 4. 多媒体/生成模型枚举

- `nanobananapro`
- `nanobanana2`
- `gptimage15`
- `sora2`
- `sora2pro`
- `veo31`
- `veo31fast`

## 5. 前端本地偏好相关字段

当前页面 localStorage 可见：

- `pplx.local-user-settings.preferredSearchModels-v1`

当前值示例：

```json
{"search":"turbo"}
```

## 6. 当前账号扩大探测结果

基于真实 `POST /rest/sse/perplexity_ask` 链路，对本目录已整理出的 93 个候选模型逐个发送 `请只回复 OK`，当前账号样本中全部成功，无失败项。

原始结果文件：`available_models_result.json`

## 7. 已确认但尚未纯 HTTP 取回的元数据接口

由于直接 requests 会返回 403，当前只确认存在与用途：

- `GET /rest/models/config?config_schema=v1&version=2.18&source=default`
- `GET /rest/rate-limit/status?version=2.18&source=default`
- `GET /rest/rate-limit/free-queries?version=2.18&source=default`
- `GET /rest/user/settings?skip_connector_picker_credentials=true&version=2.18&source=default`

这些接口已由网页真实前端调用，但仍需补足更多登录态材料后，才能稳定在独立脚本中直接取回真实 JSON。
