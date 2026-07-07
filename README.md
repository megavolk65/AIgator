[🇬🇧 English](README.md) | [🇷🇺 Русский](README_RU.md)

# <img src="assets/icon_256.png" alt="" width="32"> AIgator

<p align="center">
  <img src="assets/logo.png" alt="AIgator" width="400">
</p>

<p align="center">
  <strong>AI assistant overlay for games</strong><br>
  Press a hotkey in any game — ask a question, attach a screenshot, get an answer. No Alt-Tab.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11+-blue" alt="Python">
  <img src="https://img.shields.io/badge/License-MIT-green" alt="License">
  <img src="https://img.shields.io/badge/Platform-Windows-lightgrey" alt="Platform">
</p>

## Quick Start

1. **Download** `AIgator_Setup_x.x.x.exe` from [Releases](https://github.com/megavolk65/AIgator/releases) and run it.
2. On first launch the **setup wizard** opens. Pick your path:
   - 🆓 **Try for free** — click *Connect OpenRouter*, sign in with Google, done.
     Free models that understand screenshots are added automatically.
     Their quality may be modest — or may be all you need.
   - 💳 **Paid models** — the same one-click connection, then top up your
     [OpenRouter balance](https://openrouter.ai/credits) to unlock the full model catalog.
3. In a game, press **PageUp** — the overlay appears. **PageDown** — take a screenshot and ask about it.

## What it can do

- 🎮 Works on top of any game or app (borderless / windowed mode)
- 📷 Understands screenshots: *"How do I beat this boss?"*, *"What is this item?"*
- 🧠 Detects which game you're playing — no need to mention it in your question
- ⚡ Streaming answers — text appears as it's generated
- 🌐 Built-in browser: open links from answers without leaving the game
- 🔎 Optional web search with source links (paid, ~$0.02 per question — off by default)
- 🔒 Anti-cheat safe: standard Windows overlay, no injection, no memory reading
- ⚠️ AI can still get game facts wrong — enable web search or check the sources
  in the built-in browser when it matters

## Hotkeys

| Key | Action |
|---|---|
| `PageUp` | Show / hide the overlay |
| `PageDown` | Screenshot + attach to your question |
| `Esc` | Hide the overlay |

Hotkeys can be changed in settings (⚙).

> ⚠️ **Exclusive fullscreen:** the overlay cannot appear on top of the game.
> Use **Borderless** or **Windowed** display mode.

## Privacy

Once a day the app sends an anonymous ping: the app version and a first-launch flag —
**nothing else**. No identifiers, no personal data, no chat content.
You can turn it off in settings. The backend source is public:
[`telemetry_backend/apps_script.js`](telemetry_backend/apps_script.js).

<details>
<summary><strong>Anti-cheat safety details</strong></summary>

- Standard Windows overlay window — same approach as Discord or Steam overlays
- No injection into game processes, no reading of game memory
- Screenshots via the standard Windows API
- Global hotkeys via `RegisterHotKey` (no keyboard hooks)
</details>

<details>
<summary><strong>Build from source</strong></summary>

```bash
git clone https://github.com/megavolk65/AIgator.git
cd AIgator
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python main.py
```
</details>

## License

MIT License

## Author

megavolk65 — [GitHub](https://github.com/megavolk65) • [Telegram](https://t.me/megavolk)
Feedback: [@aigator_feedback_bot](https://t.me/aigator_feedback_bot)
