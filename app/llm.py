"""LLM gateway: off, hosted Groq, or a private OpenAI-compatible endpoint.

Only an administrator can configure endpoints, using environment variables.
A private deployment must restrict network egress and isolate the LLM service.
"""
from __future__ import annotations
import os
import httpx


def settings() -> tuple[str, str, dict] | None:
    mode = os.getenv('LLM_PROVIDER', 'auto').strip().lower()
    if mode == 'off':
        return None
    if mode == 'local':
        base = os.getenv('LOCAL_LLM_BASE_URL', 'http://127.0.0.1:11434/v1').strip().rstrip('/')
        if not base.startswith(('http://', 'https://')):
            raise ValueError('LOCAL_LLM_BASE_URL doit commencer par http:// ou https://.')
        token = os.getenv('LOCAL_LLM_API_KEY', '')
        return f'{base}/chat/completions', os.getenv('LOCAL_LLM_MODEL', 'qwen2.5:3b'), (
            {'Authorization': f'Bearer {token}'} if token else {})
    if mode in ('auto', 'groq'):
        token = os.getenv('GROQ_API_KEY', '')
        if token:
            return ('https://api.groq.com/openai/v1/chat/completions',
                    os.getenv('GROQ_MODEL', 'llama-3.3-70b-versatile'),
                    {'Authorization': f'Bearer {token}'})
        return None
    raise ValueError('LLM_PROVIDER attendu : auto, off, groq ou local.')


def generate(system: str, user: str) -> str | None:
    config = settings()
    if config is None:
        return None
    url, model, headers = config
    try:
        with httpx.Client(timeout=25) as client:
            response = client.post(url, headers=headers,
                json={'model': model, 'messages': [
                    {'role': 'system', 'content': system}, {'role': 'user', 'content': user}
                ], 'temperature': 0.1, 'max_tokens': 850})
            response.raise_for_status()
            return response.json()['choices'][0]['message']['content'].strip()
    except (httpx.HTTPError, KeyError, ValueError, IndexError, AttributeError):
        return None
