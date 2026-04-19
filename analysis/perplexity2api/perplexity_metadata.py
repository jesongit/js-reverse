import json
import os
from typing import Any, Dict, Optional

import requests

from perplexity2api import API_VERSION, BASE_URL, DEFAULT_HEADERS


class PerplexityMetadataClient:
    def __init__(self, cookie: str) -> None:
        self.session = requests.Session()
        self.session.headers.update(DEFAULT_HEADERS)
        self.session.headers['cookie'] = cookie.strip()

    def _get(self, path: str, **params: Any) -> Dict[str, Any]:
        query = {'version': API_VERSION, 'source': 'default', **params}
        response = self.session.get(f'{BASE_URL}{path}', params=query, timeout=30)
        response.raise_for_status()
        return response.json()

    def get_rate_limit_status(self) -> Dict[str, Any]:
        return self._get('/rest/rate-limit/status')

    def get_free_queries(self) -> Dict[str, Any]:
        return self._get('/rest/rate-limit/free-queries')

    def get_user_settings(self) -> Dict[str, Any]:
        return self._get('/rest/user/settings', skip_connector_picker_credentials='true')

    def get_models_config(self) -> Dict[str, Any]:
        return self._get('/rest/models/config', config_schema='v1')


def load_cookie() -> str:
    cookie = os.getenv('PPLX_COOKIE', '').strip()
    if cookie:
        return cookie
    raise RuntimeError('缺少 PPLX_COOKIE 环境变量')


def main() -> int:
    client = PerplexityMetadataClient(load_cookie())
    payload = {
        'rate_limit_status': safe_call(client.get_rate_limit_status),
        'free_queries': safe_call(client.get_free_queries),
        'user_settings': safe_call(client.get_user_settings),
        'models_config': safe_call(client.get_models_config),
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def safe_call(func):
    try:
        return {'ok': True, 'data': func()}
    except Exception as exc:
        return {'ok': False, 'error': str(exc)}


if __name__ == '__main__':
    raise SystemExit(main())
