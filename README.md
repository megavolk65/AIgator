[🇬🇧 English](README.md) | [🇷🇺 Русский](README_RU.md)

# <img src="assets/icon_256.png" alt="" width="32"> AIgator

<p align="center">
  <img src="assets/logo.png" alt="AIgator" width="400">
</p>

<p align="center">
  <strong>Universal AI Assistant with Overlay</strong><br>
  Can be called in any application with a hotkey
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11+-blue" alt="Python">
  <img src="https://img.shields.io/badge/License-MIT-green" alt="License">
  <img src="https://img.shields.io/badge/Platform-Windows-lightgrey" alt="Platform">
</p>

## Features

- 🎮 **Universal helper** — works in any application (games, browser, IDE).
- 🌐 **Built-in Browser** — open links from AI responses directly inside the overlay. No more **Alt-Tab** switching!
- 🧠 **Smart Context** — AIgator automatically detects which game or program you are using.
- 📷 **Visual Support** — AIgator "sees" your screen (when a screenshot is attached), allowing for ultra-short queries like "How to pass this?" or "What is this item?".
- ⌨️ **Hotkeys** — quick access from anywhere in the system (`PageUp` / `PageDown`).
- 🔒 **Security** — does not trigger anti-cheats, does not inject into processes.
- 🌍 **Two versions** — international and Russian (works without VPN).
- ⚠️ **Model Quality** — Remember that AI quality depends on the selected model. AI can sometimes "hallucinate". You can verify info via links in the built-in browser.

## Quick Start

1. **Download** and run the application.
2. **Open settings** (⚙️) and select an API provider.
3. **Enter your API key** and add desired models.
4. **Done!** Press `PageUp` to call the overlay or `PageDown` for a screenshot.

### API Providers

#### OpenRouter (International)
- 🌐 **Website:** [openrouter.ai](https://openrouter.ai)
- 🔑 **Get key:** [openrouter.ai/keys](https://openrouter.ai/keys)
- ✅ **Free models:** Models with the `:free` suffix work without payment.

#### AITunnel (For Russia)
- 🌐 **Website:** [aitunnel.ru](https://aitunnel.ru)
- 🔑 **Get key:** In the personal account after registration.
- 💳 **Payment:** Russian cards, rubles.

## Anti-cheat Safety & Display Mode

The application is **safe** to use with any games:
- ✅ Uses standard Windows overlay (like Discord, Steam).
- ✅ Does not inject into game processes or read memory.
- ✅ Screenshots via standard Windows API.

### ⚠️ Important: Display Mode
For the overlay to appear on top of your game, use **Borderless Window** or **Windowed** mode. The overlay will **not** be visible in **Exclusive Fullscreen** mode.

## Installation

### Ready-made Installer
Download `AIgator_Setup_x.x.x.exe` from [Releases](https://github.com/megavolk65/AIgator/releases).

### Build from Source
```bash
git clone https://github.com/megavolk65/AIgator.git
cd AIgator
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

## License
MIT License

## Author
megavolk65 — [GitHub](https://github.com/megavolk65) • [Telegram](https://t.me/megavolk)
