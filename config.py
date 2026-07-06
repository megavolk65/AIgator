"""
AIgator Configuration

Дефолты приложения. Пользовательские настройки (API-ключ, модели, хоткеи)
хранятся в %APPDATA%\\AIgator\\settings.json и имеют приоритет.
"""

# =============================================================================
# OPENROUTER CREDENTIALS
# =============================================================================

# API ключ от OpenRouter
# Получить: https://openrouter.ai/keys
OPENROUTER_API_KEY = ""

# Модель OpenRouter по умолчанию
OPENROUTER_MODEL = "anthropic/claude-haiku-4.5"

# Дефолтные модели для OpenRouter (пусто по умолчанию)
OPENROUTER_MODELS = []

# Дефолтные модели для RouterAI (пусто по умолчанию)
ROUTERAI_MODELS = []


# =============================================================================
# HOTKEYS
# =============================================================================

# Открыть/скрыть оверлей чата
HOTKEY_TOGGLE_OVERLAY = "PageUp"

# Сделать скриншот и прикрепить к сообщению
HOTKEY_SCREENSHOT = "PageDown"

# =============================================================================
# UI SETTINGS
# =============================================================================

# Размеры окна оверлея
OVERLAY_WIDTH = 1000
OVERLAY_HEIGHT = 600

# Прозрачность окна (0.0 - 1.0)
OVERLAY_OPACITY = 0.95

# Позиция окна: "center", "top-right", "bottom-right"
OVERLAY_POSITION = "center"

# =============================================================================
# APP SETTINGS
# =============================================================================

# Название приложения
APP_NAME = "AIgator"

# Версия (импортируется из version.py)
from version import __version__ as APP_VERSION

# Запускать свёрнутым в трей
START_MINIMIZED = True

# =============================================================================
# TELEMETRY
# =============================================================================

# URL Google Apps Script webhook для анонимной телеметрии
TELEMETRY_WEBHOOK_URL = "https://script.google.com/macros/s/AKfycbzMkh8e8AdkQ8vcvzD2TmMM-A3K3zDBD2I_3_gE3afqTrebrrimPyZBTi4WEOy5gXeucQ/exec"

# =============================================================================
# PATHS
# =============================================================================

import os


def get_settings_path():
    """Получить путь к файлу настроек в пользовательской папке APPDATA"""
    app_data = os.getenv("APPDATA")
    if not app_data:
        app_data = os.path.expanduser("~")
    settings_dir = os.path.join(app_data, "AIgator")
    os.makedirs(settings_dir, exist_ok=True)
    return os.path.join(settings_dir, "settings.json")
