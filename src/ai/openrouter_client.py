"""
OpenRouter AI клиент
Поддержка множества моделей через единый API
"""

import os
import sys
import json
from typing import Optional
import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import config


# URL провайдеров
PROVIDER_URLS = {
    "openrouter": "https://openrouter.ai/api/v1",
    "aitunnel": "https://api.aitunnel.ru/v1"
}


class OpenRouterClient:
    """Клиент для работы с OpenRouter/AITunnel API"""
    
    def __init__(self):
        # Загружаем настройки
        settings = self._load_settings()
        
        self.api_key = settings.get('api_key', '')
        if not self.api_key:
            self.api_key = getattr(config, 'OPENROUTER_API_KEY', '')
        
        # Определяем base_url по провайдеру
        self.api_provider = settings.get('api_provider', 'openrouter')
        self.base_url = PROVIDER_URLS.get(self.api_provider, PROVIDER_URLS['openrouter'])
        
        self.model_name = getattr(config, 'OPENROUTER_MODEL', 'google/gemma-3-27b-it:free:online')
        
        # История сообщений
        self.history = []
        self.current_game_name = None
    
    def _load_settings(self) -> dict:
        """Загрузить настройки из settings.json"""
        try:
            # Определяем базовый путь (для PyInstaller и dev-режима)
            if getattr(sys, 'frozen', False):
                # Запущено как exe (PyInstaller)
                base_path = os.path.dirname(sys.executable)
            else:
                # Запущено из исходников
                base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            
            settings_path = os.path.join(base_path, "settings.json")
            
            with open(settings_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    
    def reload_settings(self):
        """Перезагрузить настройки (при смене провайдера)"""
        settings = self._load_settings()
        self.api_key = settings.get('api_key', '')
        self.api_provider = settings.get('api_provider', 'openrouter')
        self.base_url = PROVIDER_URLS.get(self.api_provider, PROVIDER_URLS['openrouter'])
    
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
            self.history.append({
                "role": "user",
                "content": user_message
            })
            
            # Отправляем запрос
            response = self._make_request(self.history)
            
            # Добавляем ответ в историю
            self.history.append({
                "role": "assistant",
                "content": response
            })
            
            return response
            
        except Exception as e:
            return f"❌ Ошибка OpenRouter: {str(e)}"
    
    def _compress_image(self, image_data: bytes, max_size: int = 1920, quality: int = 85) -> tuple[bytes, str]:
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
        if img.mode in ('RGBA', 'P'):
            img = img.convert('RGB')
        
        # Сохраняем в JPEG
        buffer = BytesIO()
        img.save(buffer, format='JPEG', quality=quality, optimize=True)
        
        return buffer.getvalue(), 'image/jpeg'
    
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
                image_base64 = base64.b64encode(compressed_data).decode('utf-8')
                
                # Формируем сообщение с изображением
                self.history.append({
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{image_base64}"
                            }
                        }
                    ]
                })
                
                # Отправляем запрос
                response = self._make_request(self.history)
                
                # Добавляем ответ
                self.history.append({
                    "role": "assistant",
                    "content": response
                })
                
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
            "HTTP-Referer": "https://github.com/megavolk65/ai-helper",
            "X-Title": "AI Helper"
        }
        
        payload = {
            "model": self.model_name,
            "messages": messages,
            "plugins": [
                {
                    "id": "web",
                    "max_results": 5
                }
            ]
        }
        
        response = requests.post(
            f"{self.base_url}/chat/completions",
            headers=headers,
            json=payload,
            timeout=120
        )
        
        response.raise_for_status()
        result = response.json()
        
        if "choices" in result and len(result["choices"]) > 0:
            return result["choices"][0]["message"]["content"]
        else:
            raise Exception(f"Неожиданный ответ API: {result}")
    
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
                system_text = f"Ты AI-помощник для игры {game_name}. Помогай с прохождением, подсказывай локации, объясняй механики. Используй поиск для актуальной информации."
            else:
                system_text = "Ты универсальный AI-помощник. Отвечай кратко и по делу. Используй поиск для актуальной информации."
            
            if context_info:
                system_text += f"\n\nДополнительный контекст: {context_info}"
            
            # Добавляем системное сообщение
            self.history.append({
                "role": "system",
                "content": system_text
            })
    
    def get_stats(self) -> dict:
        """Получить статистику"""
        return {
            "model": self.model_name,
            "has_search": ":online" in self.model_name,
            "has_vision": "gemma-3" in self.model_name or "vision" in self.model_name,
            "history_length": len(self.history)
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
                "Content-Type": "application/json"
            }
            
            if self.api_provider == "aitunnel":
                # AITunnel: GET /aitunnel/balance
                response = requests.get(
                    f"{self.base_url}/aitunnel/balance",
                    headers=headers,
                    timeout=10
                )
                response.raise_for_status()
                data = response.json()
                # AITunnel возвращает баланс в рублях
                balance = data.get("balance", 0)
                return {"balance": balance, "currency": "₽"}
            else:
                # OpenRouter: GET /credits
                response = requests.get(
                    f"{self.base_url}/credits",
                    headers=headers,
                    timeout=10
                )
                response.raise_for_status()
                data = response.json()
                # OpenRouter: {data: {total_credits, total_usage}}
                credits_data = data.get("data", {})
                total = credits_data.get("total_credits", 0)
                used = credits_data.get("total_usage", 0)
                balance = total - used
                return {"balance": balance, "currency": "$"}
        except:
            return None
    
    def get_provider_name(self) -> str:
        """Получить название провайдера"""
        if self.api_provider == "aitunnel":
            return "AITunnel"
        return "OpenRouter"
