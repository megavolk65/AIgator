"""
YandexGPT клиент через REST API с генерацией IAM-токена
"""

import os
import json
import time
import requests
from typing import Optional
import jwt
from datetime import datetime, timedelta, timezone

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import config


class YandexGPTRestClient:
    """Клиент для YandexGPT через REST API"""
    
    def __init__(self):
        self.folder_id = config.YANDEX_FOLDER_ID
        self.model_name = config.YANDEX_MODEL
        self.temperature = config.TEMPERATURE
        self.max_tokens = config.MAX_TOKENS
        
        # Путь к авторизованному ключу
        self.auth_key_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "authorized_key.json"
        )
        
        self._iam_token: Optional[str] = None
        self._token_expires_at: Optional[datetime] = None
        self._service_account_key: Optional[dict] = None
        self._messages: list = []  # История сообщений
        self._system_prompt: str = config.SYSTEM_PROMPT_BASE
        
        self._load_service_account_key()
    
    def _load_service_account_key(self):
        """Загрузить авторизованный ключ"""
        if os.path.exists(self.auth_key_path):
            with open(self.auth_key_path, 'r') as f:
                self._service_account_key = json.load(f)
    
    def _create_jwt(self) -> str:
        """Создать JWT для генерации IAM-токена"""
        if not self._service_account_key:
            raise Exception("Авторизованный ключ не загружен")
        
        now = datetime.now(timezone.utc)
        payload = {
            'aud': 'https://iam.api.cloud.yandex.net/iam/v1/tokens',
            'iss': self._service_account_key['service_account_id'],
            'iat': int(now.timestamp()),
            'exp': int((now + timedelta(hours=1)).timestamp())
        }
        
        return jwt.encode(
            payload,
            self._service_account_key['private_key'],
            algorithm='PS256',
            headers={'kid': self._service_account_key['id']}
        )
    
    def _get_iam_token(self) -> str:
        """Получить IAM-токен"""
        # Проверяем, есть ли актуальный токен
        if (self._iam_token and self._token_expires_at and 
            datetime.now(timezone.utc) < self._token_expires_at - timedelta(minutes=5)):
            return self._iam_token
        
        if not self._service_account_key:
            # Если нет авторизованного ключа, пробуем API-ключ
            if config.YANDEX_API_KEY:
                return f"Api-Key {config.YANDEX_API_KEY}"
            else:
                raise Exception("Нет ни авторизованного ключа, ни API-ключа")
        
        # Генерируем новый IAM-токен
        try:
            signed_token = self._create_jwt()
            
            response = requests.post(
                'https://iam.api.cloud.yandex.net/iam/v1/tokens',
                json={'jwt': signed_token}
            )
            response.raise_for_status()
            
            data = response.json()
            self._iam_token = data['iamToken']
            
            # Токен действует 12 часов, обновляем за 5 минут до истечения
            self._token_expires_at = datetime.now(timezone.utc) + timedelta(hours=11, minutes=55)
            
            return f"Bearer {self._iam_token}"
        
        except Exception as e:
            raise Exception(f"Ошибка генерации IAM-токена: {e}")
    
    def send_message(self, text: str, screenshot_context: str = "") -> str:
        """Отправить сообщение в YandexGPT"""
        try:
            # Получаем токен авторизации
            auth_header = self._get_iam_token()
            
            # Формируем сообщение
            user_message = text
            if screenshot_context:
                user_message = f"[Контекст из скриншота: {screenshot_context}]\n\n{text}"
            
            # Добавляем сообщение пользователя в историю
            self._messages.append({"role": "user", "text": user_message})
            
            # Подготавливаем запрос
            url = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
            headers = {
                "Content-Type": "application/json",
                "Authorization": auth_header,
                "x-folder-id": self.folder_id
            }
            
            # Формируем список сообщений с системным промптом и историей
            messages = [{"role": "system", "text": self._system_prompt}] + self._messages
            
            data = {
                "modelUri": f"gpt://{self.folder_id}/{self.model_name}",
                "completionOptions": {
                    "stream": False,
                    "temperature": self.temperature,
                    "maxTokens": self.max_tokens
                },
                "messages": messages
            }
            
            # Отправляем запрос
            response = requests.post(url, headers=headers, json=data)
            
            if response.status_code == 200:
                result = response.json()
                assistant_message = result["result"]["alternatives"][0]["message"]["text"]
                
                # Добавляем ответ в историю
                self._messages.append({"role": "assistant", "text": assistant_message})
                
                # Ограничиваем историю последними 20 сообщениями
                if len(self._messages) > 20:
                    self._messages = self._messages[-20:]
                
                return assistant_message
            else:
                return f"❌ Ошибка API ({response.status_code}): {response.text}"
                
        except Exception as e:
            return f"❌ Ошибка: {str(e)}"
    
    def clear_history(self):
        """Очистить историю чата"""
        self._messages = []
    
    def update_context(self, game_name: Optional[str] = None, context_info: str = ""):
        """Обновить контекст (системный промпт)"""
        if game_name:
            self._system_prompt = config.SYSTEM_PROMPT_GAME.format(game_name=game_name)
        else:
            self._system_prompt = config.SYSTEM_PROMPT_BASE
        
        if context_info:
            self._system_prompt += f"\n\nДополнительный контекст: {context_info}"
    
    def get_stats(self) -> dict:
        """Получить статистику"""
        return {
            "model": self.model_name,
            "has_iam_token": bool(self._iam_token),
            "token_expires_at": self._token_expires_at.isoformat() if self._token_expires_at else None,
            "has_service_account_key": bool(self._service_account_key)
        }