"""
OAuth PKCE подключение OpenRouter — получение API-ключа в один клик,
без ручного копирования. Документация: https://openrouter.ai/docs/use-cases/oauth-pkce

Флоу:
1. Поднимаем локальный HTTP-сервер на случайном порту (127.0.0.1)
2. Открываем браузер на openrouter.ai/auth с code_challenge (S256)
3. Пользователь логинится и разрешает доступ
4. Браузер возвращается на localhost с кодом
5. Меняем код на API-ключ через POST /api/v1/auth/keys
"""

import base64
import hashlib
import secrets
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs

import requests

AUTH_URL = "https://openrouter.ai/auth"
KEYS_URL = "https://openrouter.ai/api/v1/auth/keys"
MODELS_URL = "https://openrouter.ai/api/v1/models"

# Страница, которую видит пользователь в браузере после подтверждения
_SUCCESS_HTML = """<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>AIgator</title></head>
<body style="background:#1a1a2e;color:#eee;font-family:Segoe UI,sans-serif;
             display:flex;align-items:center;justify-content:center;height:95vh;">
  <div style="text-align:center;">
    <div style="font-size:64px;">🐊</div>
    <h2>Готово! / Done!</h2>
    <p style="color:#aaa;">Ключ получен — можно закрыть эту вкладку<br>
    и вернуться в AIgator.<br><br>
    Key received — close this tab and return to AIgator.</p>
  </div>
</body></html>"""


class _CallbackHandler(BaseHTTPRequestHandler):
    """Принимает редирект от OpenRouter с кодом авторизации"""

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path != "/callback":
            self.send_response(404)
            self.end_headers()
            return

        code = (parse_qs(parsed.query).get("code") or [None])[0]
        self.server.oauth_code = code

        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(_SUCCESS_HTML.encode("utf-8"))

    def log_message(self, *args):
        pass  # без спама в консоль


def perform_oauth(
    timeout_sec: int = 300, stop_event=None, open_browser=webbrowser.open
) -> str:
    """
    Выполнить OAuth PKCE флоу (блокирующий — звать из фонового потока).

    Returns:
        API-ключ OpenRouter (sk-or-v1-...)

    Raises:
        TimeoutError / InterruptedError / requests.HTTPError
    """
    # PKCE: verifier + S256 challenge
    verifier = secrets.token_urlsafe(48)
    challenge = (
        base64.urlsafe_b64encode(hashlib.sha256(verifier.encode("ascii")).digest())
        .decode("ascii")
        .rstrip("=")
    )

    server = HTTPServer(("127.0.0.1", 0), _CallbackHandler)
    server.oauth_code = None
    server.timeout = 1  # handle_request просыпается раз в секунду
    port = server.server_address[1]

    callback_url = f"http://localhost:{port}/callback"
    auth_url = (
        f"{AUTH_URL}?callback_url={callback_url}"
        f"&code_challenge={challenge}&code_challenge_method=S256"
    )

    open_browser(auth_url)

    deadline = time.time() + timeout_sec
    try:
        while server.oauth_code is None and time.time() < deadline:
            if stop_event is not None and stop_event.is_set():
                raise InterruptedError("OAuth отменён")
            server.handle_request()
    finally:
        server.server_close()

    if not server.oauth_code:
        raise TimeoutError("Не дождались подтверждения в браузере")

    # Обмен кода на ключ
    resp = requests.post(
        KEYS_URL,
        json={
            "code": server.oauth_code,
            "code_verifier": verifier,
            "code_challenge_method": "S256",
        },
        timeout=30,
    )
    resp.raise_for_status()
    key = resp.json().get("key")
    if not key:
        raise ValueError(f"OpenRouter вернул ответ без ключа: {resp.text[:200]}")
    return key


# Модели, которые не стоит предлагать новичку по умолчанию
_SKIP_MARKERS = ("safety", "guard", "coder", "code")

# Фоллбэк, если каталог недоступен (актуален на июль 2026, все — vision)
_FALLBACK_MODELS = [
    ("google/gemma-4-31b-it:free", "GOOGLE: Gemma 4 31B (free)"),
    ("google/gemma-4-26b-a4b-it:free", "GOOGLE: Gemma 4 26B A4B (free)"),
    (
        "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free",
        "NVIDIA: Nemotron 3 Nano Omni (free)",
    ),
]


def pick_free_models(max_models: int = 3) -> list:
    """
    Подобрать стартовые бесплатные модели из каталога OpenRouter.
    Приоритет: vision (скриншоты!), большой контекст, известные вендоры.

    Returns:
        [(model_id, display_name), ...]
    """
    try:
        data = requests.get(MODELS_URL, timeout=15).json()["data"]
        free = [
            m
            for m in data
            if str(m.get("id", "")).endswith(":free")
            and not any(s in m["id"] for s in _SKIP_MARKERS)
        ]
        vision = [
            m
            for m in free
            if "image"
            in ((m.get("architecture") or {}).get("input_modalities") or [])
        ]
        text_only = [m for m in free if m not in vision]

        def rank(m):
            provider_bonus = 1 if m["id"].startswith(("google/", "meta-llama/")) else 0
            return (provider_bonus, m.get("context_length") or 0)

        vision.sort(key=rank, reverse=True)
        text_only.sort(key=rank, reverse=True)

        # Скриншоты — ключевая фича: берём только vision-модели,
        # текстовыми добиваем лишь если vision-моделей не хватает
        picked = vision[:max_models]
        if len(picked) < max_models:
            picked += text_only[: max_models - len(picked)]
        result = [(m["id"], m.get("name") or m["id"]) for m in picked[:max_models]]
        return result or list(_FALLBACK_MODELS)
    except Exception:
        return list(_FALLBACK_MODELS)
