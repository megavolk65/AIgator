"""
Телеметрия — анонимный ping при запуске (раз в сутки).

Отправляется только номер версии и флаг первого запуска — ни идентификаторов
пользователя, ни данных о системе. Количество пингов за день = количество
активных установок (DAU). Отключается в настройках (telemetry_enabled).
Бэкенд: telemetry_backend/apps_script.js (Google Apps Script + Google Sheet).
"""

import json
import threading
from datetime import date
from urllib.request import Request, urlopen

import config

SETTINGS_PATH = config.get_settings_path()


def _load_settings() -> dict:
    """Загрузить settings.json"""
    try:
        with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_settings(settings: dict):
    """Сохранить settings.json"""
    try:
        with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def _should_ping_today() -> bool:
    """Проверить, был ли уже ping сегодня"""
    settings = _load_settings()
    last_date = settings.get("last_telemetry_date", "")
    return last_date != date.today().isoformat()


def _is_first_launch() -> bool:
    """Первый запуск = ping ещё ни разу не отправлялся"""
    settings = _load_settings()
    return not settings.get("last_telemetry_date")


def _is_enabled() -> bool:
    """Телеметрия включена в настройках (по умолчанию — да)"""
    settings = _load_settings()
    return bool(settings.get("telemetry_enabled", True))


def _mark_ping_sent():
    """Отметить что ping отправлен сегодня"""
    settings = _load_settings()
    settings["last_telemetry_date"] = date.today().isoformat()
    # Подчищаем идентификатор от старых версий (телеметрия анонимна с v1.2.0)
    settings.pop("telemetry_id", None)
    _save_settings(settings)


def _do_ping(first_launch: bool):
    """Отправить ping на webhook (вызывается в фоновом потоке)"""
    try:
        webhook_url = getattr(config, "TELEMETRY_WEBHOOK_URL", "")
        if not webhook_url:
            return

        payload = json.dumps(
            {
                "version": config.APP_VERSION,
                "first_launch": first_launch,
            }
        ).encode("utf-8")

        req = Request(
            webhook_url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        urlopen(req, timeout=10)

        # Отправка успешна — запоминаем дату
        _mark_ping_sent()

    except Exception:
        # Молча игнорируем любые ошибки — телеметрия не должна мешать работе
        pass


def send_startup_ping():
    """
    Отправить ping при запуске (раз в сутки, в фоновом потоке).
    Безопасно вызывать из любого места — ошибки подавляются.
    """
    try:
        if not _is_enabled():
            return
        if not _should_ping_today():
            return

        first_launch = _is_first_launch()
        thread = threading.Thread(
            target=_do_ping, args=(first_launch,), daemon=True
        )
        thread.start()
    except Exception:
        pass
