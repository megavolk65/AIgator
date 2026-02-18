# AI Helper

Универсальный AI-ассистент с оверлеем на базе YandexGPT. Вызывается в любом приложении горячей клавишей. Основной фокус — помощь в играх, но может отвечать на любые вопросы.

![Python](https://img.shields.io/badge/Python-3.11+-blue)
![License](https://img.shields.io/badge/License-MIT-green)

## Возможности

- 🎮 **Универсальный помощник** — работает в любом приложении (игры, браузер, IDE)
- ⌨️ **Горячие клавиши** — быстрый вызов из любой точки системы
- 📷 **Анализ скриншотов** — распознавание текста с экрана через Yandex Vision
- 🖼️ **Отображение картинок** — карты локаций, скриншоты, гайды прямо в чате
- 🎯 **Авто-определение контекста** — понимает какая игра/приложение активно
- 🔒 **Безопасность** — не конфликтует с античитами

## Установка

### Требования

- Windows 10/11
- Python 3.11+
- Аккаунт [Yandex Cloud](https://console.yandex.cloud/)

### Быстрый старт

1. **Клонируйте репозиторий:**
   ```bash
   git clone https://github.com/megavolk65/ai-helper.git
   cd ai-helper
   ```

2. **Создайте виртуальное окружение:**
   ```bash
   python -m venv venv
   venv\Scripts\activate
   ```

3. **Установите зависимости:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Настройте конфигурацию:**
   ```bash
   # Скопируйте примеры конфигурации
   copy config.example.py config.py
   copy authorized_key.example.json authorized_key.json
   ```
   
   Отредактируйте `config.py` и укажите свой `YANDEX_FOLDER_ID`

5. **Запустите:**
   ```bash
   python main.py
   ```

## ⚠️ Безопасность конфигурации

**ВАЖНО!** Файлы `config.py` и `authorized_key.json` содержат секретную информацию и **НЕ ДОЛЖНЫ** попадать в публичный репозиторий!

- ✅ Эти файлы уже добавлены в `.gitignore`
- ✅ Используйте файлы `*.example.*` как шаблоны
- ❌ **НИКОГДА** не коммитьте реальные ключи в git
- ❌ Не делитесь `authorized_key.json` — он содержит приватный ключ RSA!

## Получение доступа к Yandex Cloud

1. Перейдите в [Yandex Cloud Console](https://console.yandex.cloud/)
2. **Привяжите платёжный аккаунт** для активации облака (даётся грант 4000₽)
3. Создайте каталог (или используйте существующий)
4. Скопируйте **Folder ID** из свойств каталога и вставьте в `config.py`
5. Перейдите в **IAM → Сервисные аккаунты**
6. Создайте сервисный аккаунт и назначьте ему роли на уровне **каталога**:
   - `ai.languageModels.user` — для работы с YandexGPT
   - `ai.vision.user` — для анализа скриншотов
   - `viewer` — для доступа к метаданным каталога
7. Создайте **Авторизованный ключ** (Authorized Key) для сервисного аккаунта:
   - Выберите алгоритм **RSA-2048**
   - Скачайте JSON-файл с ключом
   - Сохраните его как `authorized_key.json` в корне проекта

## Горячие клавиши

| Комбинация | Действие |
|------------|----------|
| `Ctrl+Shift+G` | Открыть/скрыть оверлей |
| `Ctrl+Shift+S` | Сделать скриншот |
| `Escape` | Закрыть оверлей |

## Использование

1. Нажмите `Ctrl+Shift+G` чтобы вызвать оверлей
2. Введите вопрос и нажмите Enter
3. Получите ответ от AI

### Со скриншотом

1. Нажмите `Ctrl+Shift+S` чтобы сделать скриншот
2. Оверлей автоматически откроется с прикреплённым скриншотом
3. Введите вопрос — AI увидит контекст с экрана

## Сборка

### Создание EXE

```bash
pip install pyinstaller
pyinstaller build.spec
```

Готовый `AI Helper.exe` будет в папке `dist/`

### Создание инсталятора

1. Установите [Inno Setup](https://jrsoftware.org/isinfo.php)
2. Откройте `installer/setup.iss`
3. Скомпилируйте (Ctrl+F9)

Инсталятор будет в `dist/installer/`

## Структура проекта

```
ai-helper/
├── main.py                 # Точка входа
├── config.py               # Конфигурация
├── requirements.txt        # Зависимости
├── build.spec              # PyInstaller конфиг
├── src/
│   ├── overlay/            # UI оверлея
│   ├── hotkeys/            # Горячие клавиши
│   ├── game_detect/        # Определение игры/приложения
│   ├── screenshot/         # Захват экрана
│   └── ai/                 # Интеграция с YandexGPT/Vision
├── installer/              # Inno Setup скрипты
└── assets/                 # Иконки и ресурсы
```

## Безопасность для античитов

Приложение **безопасно** для использования с любыми играми:

- ✅ Использует стандартное Windows-окно (как Discord, Steam)
- ✅ Не инжектится в процессы игр
- ✅ Не читает память игр
- ✅ Не использует хуки DirectX/Vulkan
- ✅ Скриншоты через стандартный Windows API

## Настройка

Все настройки находятся в `config.py`:

```python
# Горячие клавиши
HOTKEY_TOGGLE_OVERLAY = "ctrl+shift+g"
HOTKEY_SCREENSHOT = "ctrl+shift+s"

# Размер окна
OVERLAY_WIDTH = 500
OVERLAY_HEIGHT = 600

# Модель
YANDEX_MODEL = "yandexgpt-lite"  # или "yandexgpt"
TEMPERATURE = 0.6

# Автозапуск
START_MINIMIZED = True
```

## Лицензия

MIT License

## Автор

MEGAVOLK — [@megavolk65](https://github.com/megavolk65)
