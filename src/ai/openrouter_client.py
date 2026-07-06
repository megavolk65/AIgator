"""
OpenRouter AI клиент
Поддержка множества моделей через единый API
"""

import os
import sys
import json
from typing import Optional
import requests

sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
import config


# URL провайдеров
PROVIDER_URLS = {
    "openrouter": "https://openrouter.ai/api/v1",
    "routerai": "https://routerai.ru/api/v1",
}


class OpenRouterClient:
    """Клиент для работы с OpenRouter/RouterAI API (OpenRouter-совместимые)"""

    def __init__(self):
        # Загружаем настройки
        settings = self._load_settings()

        # Определяем base_url по провайдеру
        self.api_provider = settings.get("api_provider", "openrouter")
        self.base_url = PROVIDER_URLS.get(
            self.api_provider, PROVIDER_URLS["openrouter"]
        )

        self.api_key = self._resolve_api_key(settings, self.api_provider)

        self.model_name = getattr(
            config, "OPENROUTER_MODEL", "google/gemma-3-27b-it:free:online"
        )

        # Веб-поиск (платный плагин — по умолчанию выключен)
        self.web_search = bool(settings.get("web_search", False))

        # История сообщений
        self.history = []
        self.current_game_name = None

    def _load_settings(self) -> dict:
        """Загрузить настройки из settings.json"""
        try:
            settings_path = config.get_settings_path()
            with open(settings_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}

    @staticmethod
    def _resolve_api_key(settings: dict, provider: str) -> str:
        """Ключ провайдера: сначала api_keys[provider], потом легаси api_key"""
        per_provider = settings.get("api_keys") or {}
        key = per_provider.get(provider, "")
        if not key:
            key = settings.get("api_key", "")
        if not key:
            key = getattr(config, "OPENROUTER_API_KEY", "")
        return key

    def reload_settings(self):
        """Перезагрузить настройки (при смене провайдера)"""
        settings = self._load_settings()
        self.api_provider = settings.get("api_provider", "openrouter")
        self.base_url = PROVIDER_URLS.get(
            self.api_provider, PROVIDER_URLS["openrouter"]
        )
        self.api_key = self._resolve_api_key(settings, self.api_provider)
        self.web_search = bool(settings.get("web_search", False))

    def set_web_search(self, enabled: bool):
        """Включить/выключить платный веб-поиск"""
        self.web_search = bool(enabled)

    def send_message(self, text: str, screenshot_context: str = "") -> str:
        """
        Отправить текстовое сообщение

        Args:
            text: Текст сообщения
            screenshot_context: Контекст из скриншота (OCR)

        Returns:
            Ответ от модели
        """
        try:
            # Формируем сообщение
            user_message = text
            if screenshot_context:
                user_message = f"[Контекст с экрана: {screenshot_context}]\n\n{text}"

            # Добавляем в историю
            self.history.append({"role": "user", "content": user_message})

            # Отправляем запрос
            response = self._make_request(self.history)

            # Добавляем ответ в историю
            self.history.append({"role": "assistant", "content": response})

            return response

        except Exception as e:
            return f"❌ Ошибка OpenRouter: {str(e)}"

    def _compress_image(
        self, image_data: bytes, max_size: int = 1920, quality: int = 85
    ) -> tuple[bytes, str]:
        """
        Сжать изображение для отправки

        Args:
            image_data: Исходные байты изображения
            max_size: Максимальный размер по большей стороне
            quality: Качество JPEG (1-100)

        Returns:
            (сжатые байты, mime-тип)
        """
        from PIL import Image
        from io import BytesIO

        # Открываем изображение
        img = Image.open(BytesIO(image_data))

        # Уменьшаем если слишком большое
        if max(img.width, img.height) > max_size:
            ratio = max_size / max(img.width, img.height)
            new_size = (int(img.width * ratio), int(img.height * ratio))
            img = img.resize(new_size, Image.Resampling.LANCZOS)

        # Конвертируем в RGB (для JPEG)
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")

        # Сохраняем в JPEG
        buffer = BytesIO()
        img.save(buffer, format="JPEG", quality=quality, optimize=True)

        return buffer.getvalue(), "image/jpeg"

    def send_request(self, prompt: str, image_data: Optional[bytes] = None) -> str:
        """
        Отправить запрос с возможным изображением

        Args:
            prompt: Текст запроса
            image_data: Байты изображения (PNG/JPEG)

        Returns:
            Ответ от модели
        """
        try:
            if image_data:
                # Сжимаем изображение
                compressed_data, mime_type = self._compress_image(image_data)

                # Конвертируем в base64
                import base64

                image_base64 = base64.b64encode(compressed_data).decode("utf-8")

                # Формируем сообщение с изображением
                self.history.append(
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{mime_type};base64,{image_base64}"
                                },
                            },
                        ],
                    }
                )

                # Отправляем запрос
                response = self._make_request(self.history)

                # Добавляем ответ
                self.history.append({"role": "assistant", "content": response})

                return response
            else:
                # Обычный текстовый запрос
                return self.send_message(prompt)

        except Exception as e:
            return f"❌ Ошибка OpenRouter: {str(e)}"

    def _make_request(self, messages: list) -> str:
        """
        Выполнить HTTP запрос к OpenRouter API

        Args:
            messages: История сообщений

        Returns:
            Ответ от модели
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/megavolk65/AIgator",
            "X-Title": "AIgator",
        }

        payload = {
            "model": self.model_name,
            "messages": messages,
        }

        # Веб-поиск — платный плагин (~$0.02/запрос), только по явному согласию
        if self.web_search:
            payload["plugins"] = [{"id": "web", "max_results": 5}]

        response = requests.post(
            f"{self.base_url}/chat/completions",
            headers=headers,
            json=payload,
            timeout=120,
        )

        response.raise_for_status()
        result = response.json()

        if "choices" in result and len(result["choices"]) > 0:
            message = result["choices"][0]["message"]
            content = message.get("content", "")

            # Ссылки-источники от веб-плагина (annotations -> url_citation)
            sources = self._extract_sources(message)
            if sources:
                from src.localization import t

                content += f"\n\n**{t('sources')}:**\n" + "\n".join(
                    f"- [{title}]({url})" for url, title in sources
                )

            return content
        else:
            raise Exception(f"Неожиданный ответ API: {result}")

    @staticmethod
    def _extract_sources(message: dict) -> list:
        """Достать ссылки на источники из annotations (веб-поиск)"""
        sources = []
        try:
            for ann in message.get("annotations") or []:
                citation = ann.get("url_citation") or {}
                url = citation.get("url")
                title = (citation.get("title") or url or "").strip()
                if url and url not in [u for u, _ in sources]:
                    sources.append((url, title))
        except Exception:
            pass
        return sources[:5]

    def clear_history(self):
        """Очистить историю чата"""
        self.history = []

    def set_model(self, model_id: str):
        """
        Установить модель

        Args:
            model_id: ID модели OpenRouter
        """
        self.model_name = model_id

    def get_model(self) -> str:
        """Получить текущую модель"""
        return self.model_name

    def update_context(self, game_name: Optional[str] = None, context_info: str = ""):
        """
        Обновить контекст (системный промпт)

        Args:
            game_name: Название игры
            context_info: Дополнительная информация
        """
        # Сохраняем текущий контекст
        self.current_game_name = game_name

        # Если история пуста - добавляем системный промпт
        if len(self.history) == 0:
            if game_name:
                system_text = f"Ты AI-помощник для игры {game_name}. Помогай с прохождением, подсказывай локации, объясняй механики."
            else:
                system_text = "Ты универсальный AI-помощник. Отвечай кратко и по делу."

            # Анти-галлюцинации: честность важнее уверенности
            system_text += (
                " Если не уверен в конкретном игровом факте (название предмета,"
                " NPC, локации, шаги квеста) — прямо скажи, что не уверен,"
                " и предложи проверить в вики игры. Никогда не выдумывай"
                " конкретику и не сочиняй URL — ссылки давай только на главные"
                " страницы известных ресурсов."
            )

            if self.web_search:
                system_text += (
                    " Используй веб-поиск для актуальной информации."
                    " В конце ответа приведи ссылки на использованные источники."
                )

            if context_info:
                system_text += f"\n\nДополнительный контекст: {context_info}"

            # Добавляем системное сообщение
            self.history.append({"role": "system", "content": system_text})

    def get_stats(self) -> dict:
        """Получить статистику"""
        return {
            "model": self.model_name,
            "has_search": ":online" in self.model_name,
            "has_vision": "gemma-3" in self.model_name or "vision" in self.model_name,
            "history_length": len(self.history),
        }

    def get_balance(self) -> Optional[dict]:
        """
        Получить баланс аккаунта

        Returns:
            dict с ключами 'balance' и 'currency' или None при ошибке
        """
        if not self.api_key:
            return None

        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }

            # GET /credits.
            # OpenRouter: {data: {total_credits, total_usage}}
            # RouterAI:   {data: {credits}}
            response = requests.get(
                f"{self.base_url}/credits", headers=headers, timeout=10
            )
            response.raise_for_status()
            data = response.json()
            credits_data = data.get("data", {})
            if "credits" in credits_data:
                balance = credits_data.get("credits", 0)
            else:
                total = credits_data.get("total_credits", 0)
                used = credits_data.get("total_usage", 0)
                balance = total - used
            currency = "₽" if self.api_provider == "routerai" else "$"
            return {"balance": balance, "currency": currency}
        except:
            return None

    def get_provider_name(self) -> str:
        """Получить название провайдера"""
        if self.api_provider == "routerai":
            return "RouterAI"
        return "OpenRouter"
