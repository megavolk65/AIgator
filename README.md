<p align="center">
  <img src="assets/icon_256.png" alt="AI Helper" width="128">
</p>

# AI Helper

<p align="center">
  <img src="assets/logo.png" alt="AI Helper" width="400">
</p>

<p align="center">
  <strong>Универсальный AI-ассистент с оверлеем</strong><br>
  Вызывается в любом приложении горячей клавишей
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11+-blue" alt="Python">
  <img src="https://img.shields.io/badge/License-MIT-green" alt="License">
  <img src="https://img.shields.io/badge/Platform-Windows-lightgrey" alt="Platform">
</p>

## Возможности

- 🎮 **Универсальный помощник** — работает в любом приложении (игры, браузер, IDE)
- 🧠 **Любые модели** — работает с любыми LLM, совместимыми с OpenAI API (GPT, Claude, Gemini, Qwen и др.)
- ⌨️ **Горячие клавиши** — быстрый вызов из любой точки системы
- 📷 **Анализ скриншотов** — AI видит что на экране (Vision модели)
- 🎯 **Контекст приложения** — AI знает из какой игры/программы вы задаёте вопрос
- 🔒 **Безопасность** — не вызывает срабатывания античитов
- 🌍 **Две версии** — международная и русская (работает без VPN и зарубежных карт)

## Быстрый старт

1. Скачайте и запустите приложение
2. Откройте настройки (⚙️) и выберите API провайдер
3. Введите API ключ
4. Добавьте модели
5. Готово!

## API провайдеры

### OpenRouter (международный)

- 🌐 **Сайт:** [openrouter.ai](https://openrouter.ai)
- 🔑 **Получить ключ:** [openrouter.ai/keys](https://openrouter.ai/keys)
- 💳 **Оплата:** международные карты
- ✅ **Бесплатные модели:** Да! Модели с суффиксом `:free` работают без оплаты

**Бесплатные модели с Vision:**
- `qwen/qwen3-vl-30b-a3b-instruct:free`
- `nvidia/nemotron-nano-12b-v2-vl:free`

### AITunnel (для России)

- 🌐 **Сайт:** [aitunnel.ru](https://aitunnel.ru)
- 🔑 **Получить ключ:** в личном кабинете после регистрации
- 💳 **Оплата:** российские карты, рубли
- ⚠️ **Бесплатных моделей нет**

**Дешёвые модели с Vision:**
- `gemini-2.5-flash-lite-preview`
- `gpt-5-nano`

## Горячие клавиши

Настраиваются в настройках. По умолчанию:

- `Insert` — Открыть/скрыть оверлей
- `Home` — Сделать скриншот
- `Escape` — Закрыть оверлей

## Использование

1. Нажмите горячую клавишу чтобы вызвать оверлей
2. Введите вопрос и нажмите Enter
3. Получите ответ от AI

### Со скриншотом

1. Нажмите клавишу скриншота или кнопку 📷 в оверлее
2. Скриншот прикрепится к сообщению
3. Введите вопрос — AI увидит что на экране

## Безопасность для античитов

Приложение **безопасно** для использования с любыми играми:

- ✅ Использует стандартное Windows-окно (как Discord, Steam)
- ✅ Не инжектится в процессы игр
- ✅ Не читает память игр
- ✅ Не использует хуки DirectX/Vulkan
- ✅ Скриншоты через стандартный Windows API

## Установка

### Готовый установщик

Скачайте `AI_Helper_Setup_x.x.x.exe` из [Releases](https://github.com/megavolk65/ai-helper/releases)

### Сборка из исходников

```bash
git clone https://github.com/megavolk65/ai-helper.git
cd ai-helper
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

### Создание EXE и установщика

```bash
pip install pyinstaller
pyinstaller build.spec
# Затем скомпилировать installer/setup.iss через Inno Setup
```

## Лицензия

MIT License

## Автор

megavolk65 — [GitHub](https://github.com/megavolk65) • [Telegram](https://t.me/megavolk)
