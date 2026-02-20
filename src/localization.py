"""
Мультиязычная локализация
"""

from typing import Dict

# Словарь переводов
TRANSLATIONS: Dict[str, Dict[str, str]] = {
    # === Название программы ===
    "app_name": {
        "ru": "AI Помощник",
        "en": "AI Helper"
    },
    
    # === Главное окно ===
    "not_detected": {
        "ru": "Не определено",
        "en": "Not detected"
    },
    "enter_question": {
        "ru": "Введите вопрос...",
        "en": "Enter your question..."
    },
    "send": {
        "ru": "Отправить",
        "en": "Send"
    },
    "clear_chat": {
        "ru": "Очистить чат",
        "en": "Clear chat"
    },
    "model": {
        "ru": "Модель:",
        "en": "Model:"
    },
    "ask_question": {
        "ru": "Задай вопрос...",
        "en": "Ask a question..."
    },
    "screenshot_attached": {
        "ru": "📷 Скриншот прикреплён",
        "en": "📷 Screenshot attached"
    },
    "screenshot_preview": {
        "ru": "📷 Превью скриншота:",
        "en": "📷 Screenshot preview:"
    },
    "with_screenshot": {
        "ru": "📷 [Со скриншотом]",
        "en": "📷 [With screenshot]"
    },
    "you": {
        "ru": "Вы",
        "en": "You"
    },
    "ai_not_initialized": {
        "ru": "❌ AI клиент не инициализирован. Проверьте config.py",
        "en": "❌ AI client not initialized. Check config.py"
    },
    "error": {
        "ru": "❌ Ошибка:",
        "en": "❌ Error:"
    },
    "refresh_context": {
        "ru": "Обновить активное окно",
        "en": "Refresh active window"
    },
    "take_screenshot": {
        "ru": "Сделать скриншот",
        "en": "Take screenshot"
    },
    
    # === Настройки ===
    "settings": {
        "ru": "Настройки",
        "en": "Settings"
    },
    "api_key": {
        "ru": "API ключ:",
        "en": "API key:"
    },
    "show_hide": {
        "ru": "Показать/скрыть",
        "en": "Show/hide"
    },
    "models": {
        "ru": "Модели",
        "en": "Models"
    },
    "models_catalog": {
        "ru": "🔗 Каталог моделей",
        "en": "🔗 Models catalog"
    },
    "add": {
        "ru": "➕ Добавить",
        "en": "➕ Add"
    },
    "hotkeys": {
        "ru": "Горячие клавиши",
        "en": "Hotkeys"
    },
    "open_close": {
        "ru": "Открыть/закрыть:",
        "en": "Open/close:"
    },
    "screenshot": {
        "ru": "Скриншот:",
        "en": "Screenshot:"
    },
    "autostart": {
        "ru": "Запускать при старте Windows",
        "en": "Start with Windows"
    },
    "cancel": {
        "ru": "Отмена",
        "en": "Cancel"
    },
    "save": {
        "ru": "Сохранить",
        "en": "Save"
    },
    "add_model": {
        "ru": "Добавить модель",
        "en": "Add model"
    },
    "model_id_prompt": {
        "ru": "Model ID (например: google/gemini-3-pro-preview):",
        "en": "Model ID (e.g.: google/gemini-3-pro-preview):"
    },
    "display_name_prompt": {
        "ru": "Название для отображения:",
        "en": "Display name:"
    },
    "api_key_error": {
        "ru": "Некорректный API ключ",
        "en": "Invalid API key"
    },
    "setup_required": {
        "ru": "⚙️ Откройте настройки и укажите API ключ",
        "en": "⚙️ Open settings and enter your API key"
    },
    "api_provider": {
        "ru": "API провайдер",
        "en": "API Provider"
    },
    "provider_openrouter": {
        "ru": "OpenRouter (международный)",
        "en": "OpenRouter (international)"
    },
    "provider_aitunnel": {
        "ru": "AITunnel (оплата в рублях)",
        "en": "AITunnel (payment in rubles)"
    },
    
    # === Трей ===
    "show": {
        "ru": "Показать",
        "en": "Show"
    },
    "exit": {
        "ru": "Выход",
        "en": "Exit"
    },
    "started_press_key": {
        "ru": "Запущен! Нажмите {key} для вызова",
        "en": "Started! Press {key} to open"
    },
    "settings_applied": {
        "ru": "✅ Настройки применены",
        "en": "✅ Settings applied"
    },
    "screenshot_taken": {
        "ru": "📷 Скриншот сделан и прикреплён к сообщению",
        "en": "📷 Screenshot taken and attached"
    },
    "screenshot_error": {
        "ru": "❌ Ошибка создания скриншота",
        "en": "❌ Screenshot error"
    },
    "autostart_error": {
        "ru": "Ошибка настройки автозапуска:",
        "en": "Autostart configuration error:"
    },
    
    # === Браузер ===
    "view": {
        "ru": "Просмотр",
        "en": "View"
    },
    "open_in_browser": {
        "ru": "Открыть в браузере",
        "en": "Open in browser"
    },
    
    # === Обратная связь ===
    "send_feedback": {
        "ru": "Отправить отзыв",
        "en": "Send feedback"
    },
}


class Localization:
    """Менеджер локализации"""
    
    _instance = None
    _language = "ru"
    _listeners = []
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    @classmethod
    def get(cls, key: str, **kwargs) -> str:
        """Получить перевод по ключу"""
        if key not in TRANSLATIONS:
            return key
        
        text = TRANSLATIONS[key].get(cls._language, TRANSLATIONS[key].get("ru", key))
        
        # Подстановка параметров
        if kwargs:
            text = text.format(**kwargs)
        
        return text
    
    @classmethod
    def set_language(cls, lang: str):
        """Установить язык"""
        if lang in ("ru", "en"):
            cls._language = lang
            # Уведомляем слушателей
            for listener in cls._listeners:
                try:
                    listener()
                except:
                    pass
    
    @classmethod
    def get_language(cls) -> str:
        """Получить текущий язык"""
        return cls._language
    
    @classmethod
    def toggle_language(cls):
        """Переключить язык"""
        cls.set_language("en" if cls._language == "ru" else "ru")
    
    @classmethod
    def add_listener(cls, callback):
        """Добавить слушателя смены языка"""
        if callback not in cls._listeners:
            cls._listeners.append(callback)
    
    @classmethod
    def remove_listener(cls, callback):
        """Удалить слушателя"""
        if callback in cls._listeners:
            cls._listeners.remove(callback)


# Короткий алиас
def t(key: str, **kwargs) -> str:
    """Короткая функция для получения перевода"""
    return Localization.get(key, **kwargs)
