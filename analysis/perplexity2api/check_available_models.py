import json
import os
from typing import List

from perplexity2api import PerplexityClient

CANDIDATES: List[str] = [
    'turbo',
    'pplx_pro_upgraded',
    'pplx_pro',
    'experimental',
    'pplx_reasoning',
    'pplx_sonar_internal_testing',
    'pplx_sonar_internal_testing_v2',
    'pplx_study',
    'pplx_document_review',
    'pplx_agentic_research',
    'pplx_alpha',
    'pplx_beta',
    'pplx_business_assistant',
    'sonar',
    'gpt4o',
    'gpt4.1',
    'gpt41',
    'gpt51',
    'gpt52',
    'gpt54',
    'gpt54mini',
    'gpt53codex',
    'gpt51_thinking',
    'gpt52_thinking',
    'gpt54_thinking',
    'gpt5',
    'gpt5_thinking',
    'gpt5_pro',
    'o4mini',
    'o3',
    'o3-mini',
    'o3mini',
    'o3pro',
    'o3pro_research',
    'o3pro_labs',
    'o3_research',
    'o3_labs',
    'codex',
    'claude2',
    'claude37sonnetthinking',
    'claude40opus',
    'claude41opus',
    'claude40opusthinking',
    'claude41opusthinking',
    'claude46opus',
    'claude46opusthinking',
    'claude46sonnet',
    'claude46sonnetthinking',
    'claude45haiku',
    'claude45sonnet',
    'claude45sonnetthinking',
    'claude45opus',
    'claude45opusthinking',
    'claudecode',
    'gemini25pro',
    'gemini31pro_high',
    'gemini30flash',
    'gemini30flash_high',
    'gemini',
    'gemini2flash',
    'gemini30pro',
    'grok',
    'grok2',
    'grok4',
    'grok4nonthinking',
    'grok41reasoning',
    'grok41nonreasoning',
    'kimik25thinking',
    'kimik2thinking',
    'pplx_asi_kimi',
    'r1',
    'r1_1776',
    'llama_x_large',
    'mistral',
    'pplx_gamma',
    'testing_model_c',
    'claude_ombre_eap',
    'claude_lace_eap',
    'pplx_asi_qwen',
    'pplx_asi_sonnet',
    'pplx_asi_sonnet_thinking',
    'pplx_asi_gpt54',
    'pplx_asi_opus',
    'pplx_asi_opus_thinking',
    'pplx_asi_beta',
    'pplx_asi',
    'nanobananapro',
    'nanobanana2',
    'gptimage15',
    'sora2',
    'sora2pro',
    'veo31',
    'veo31fast',
]


def load_cookie() -> str:
    cookie = os.getenv('PPLX_COOKIE', '').strip()
    if not cookie:
        raise RuntimeError('缺少 PPLX_COOKIE 环境变量')
    return cookie


def main() -> int:
    cookie = load_cookie()
    results = []
    for model in CANDIDATES:
        client = PerplexityClient(cookie=cookie, model=model, timeout=40)
        try:
            result = client.ask('请只回复 OK')
            text = result.final_text
            results.append({
                'model': model,
                'ok': True,
                'thread_slug': result.thread_slug,
                'entry_uuid': result.entry_uuid,
                'preview': text[:200],
            })
        except Exception as exc:
            results.append({
                'model': model,
                'ok': False,
                'error': str(exc),
            })
    print(json.dumps(results, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
