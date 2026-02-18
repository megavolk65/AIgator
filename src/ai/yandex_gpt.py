"""
YandexGPT Client - интеграция с YandexGPT API
"""

import sys
import os
from typing import Optional, List, Dict, Generator
from dataclasses import dataclass, field

# Добавляем корень проекта в path для импорта config
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

try:
    from yandex_cloud_ml_sdk import YCloudML
    YANDEX_SDK_AVAILABLE = True
except ImportError:
    YANDEX_SDK_AVAILABLE = False
    YCloudML = None

import config


@dataclass
class Message:
    """Сообщение в чате"""
    role: str  # "user", "assistant", "system"
    text: str


@dataclass
class ChatHistory:
    """История чата"""
    messages: List[Message] = field(default_factory=list)
    max_messages: int = 20  # Максимум сообщений в истории
    
    def add_message(self, role: str, text: str):
        """Добавить сообщение в историю"""
        self.messages.append(Message(role=role, text=text))
        
        # Ограничиваем историю (оставляем системное сообщение + последние N)
        if len(self.messages) > self.max_messages:
            # Сохраняем первое системное сообщение если есть
            system_msg = None
            if self.messages and self.messages[0].role == "system":
                system_msg = self.messages[0]
                self.messages = self.messages[-(self.max_messages - 1):]
                self.messages.insert(0, system_msg)
            else:
                self.messages = self.messages[-self.max_messages:]
    
    def to_api_format(self) -> List[Dict[str, str]]:
        """Конвертировать в формат API"""
        return [{"role": m.role, "text": m.text} for m in self.messages]
    
    def clear(self):
        """Очистить историю"""
        self.messages = []


class YandexGPTClient:
    """Клиент для работы с YandexGPT"""
    
    def __init__(self):
        self.folder_id = config.YANDEX_FOLDER_ID
        self.api_key = config.YANDEX_API_KEY
        self.model_name = config.YANDEX_MODEL
        self.temperature = config.TEMPERATURE
        self.max_tokens = config.MAX_TOKENS
        
        # Путь к файлу с авторизованным ключом
        self.auth_key_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "authorized_key.json"
        )
        
        self.history = ChatHistory()
        self._sdk: Optional[YCloudML] = None
        self._model = None
        self._initialized = False
        self._error_message: Optional[str] = None
    
    def initialize(self) -> bool:
        """Инициализировать SDK"""
        if not YANDEX_SDK_AVAILABLE:
            self._error_message = "yandex-cloud-ml-sdk не установлен. Выполните: pip install yandex-cloud-ml-sdk"
            return False
        
        if not self.folder_id:
            self._error_message = "Не указан YANDEX_FOLDER_ID в config.py"
            return False
        
        try:
            # Пробуем использовать авторизованный ключ если он существует
            if os.path.exists(self.auth_key_path):
                import json
                with open(self.auth_key_path, 'r') as f:
                    service_account_key = json.load(f)
                
                self._sdk = YCloudML(
                    folder_id=self.folder_id,
                    auth=service_account_key,
                )
            # Иначе используем API-ключ
            elif self.api_key:
                self._sdk = YCloudML(
                    folder_id=self.folder_id,
                    auth=self.api_key,
                )
            else:
                self._error_message = "Не найден authorized_key.json и не указан YANDEX_API_KEY в config.py"
                return False
            
            self._model = self._sdk.models.completions(self.model_name)
            self._model = self._model.configure(
                temperature=self.temperature,
            )
            self._initialized = True
            return True
        except Exception as e:
            self._error_message = f"Ошибка инициализации YandexGPT: {str(e)}"
            return False
    
    @property
    def is_ready(self) -> bool:
        """Готов ли клиент к работе"""
        return self._initialized
    
    @property
    def error_message(self) -> Optional[str]:
        """Сообщение об ошибке"""
        return self._error_message
    
    def set_system_prompt(self, prompt: str):
        """Установить системный промпт"""
        # Удаляем старый системный промпт если есть
        if self.history.messages and self.history.messages[0].role == "system":
            self.history.messages.pop(0)
        
        # Добавляем новый в начало
        self.history.messages.insert(0, Message(role="system", text=prompt))
    
    def update_context(self, game_name: Optional[str] = None, context_info: str = ""):
        """Обновить контекст (системный промпт)"""
        if game_name:
            prompt = config.SYSTEM_PROMPT_GAME.format(game_name=game_name)
        else:
            prompt = config.SYSTEM_PROMPT_BASE
        
        if context_info:
            prompt += f"\n\nДополнительный контекст: {context_info}"
        
        self.set_system_prompt(prompt)
    
    def send_message(self, text: str, screenshot_context: str = "") -> str:
        """
        Отправить сообщение и получить ответ
        
        Args:
            text: Текст сообщения пользователя
            screenshot_context: Контекст из скриншота (если есть)
        
        Returns:
            Ответ от YandexGPT
        """
        if not self._initialized:
            if not self.initialize():
                return f"❌ {self._error_message}"
        
        # Формируем сообщение пользователя
        user_message = text
        if screenshot_context:
            user_message = f"[Контекст из скриншота: {screenshot_context}]\n\n{text}"
        
        # Добавляем в историю
        self.history.add_message("user", user_message)
        
        try:
            # Отправляем запрос
            result = self._model.run(self.history.to_api_format())
            
            # Получаем ответ
            if result and len(result) > 0:
                response_text = result[0].text
            else:
                response_text = "Не удалось получить ответ от модели."
            
            # Добавляем ответ в историю
            self.history.add_message("assistant", response_text)
            
            return response_text
            
        except Exception as e:
            error_msg = f"❌ Ошибка при запросе к YandexGPT: {str(e)}"
            return error_msg
    
    def send_message_stream(self, text: str, screenshot_context: str = "") -> Generator[str, None, None]:
        """
        Отправить сообщение и получить ответ потоком
        
        Args:
            text: Текст сообщения пользователя
            screenshot_context: Контекст из скриншота (если есть)
        
        Yields:
            Части ответа от YandexGPT
        """
        if not self._initialized:
            if not self.initialize():
                yield f"❌ {self._error_message}"
                return
        
        # Формируем сообщение пользователя
        user_message = text
        if screenshot_context:
            user_message = f"[Контекст из скриншота: {screenshot_context}]\n\n{text}"
        
        # Добавляем в историю
        self.history.add_message("user", user_message)
        
        try:
            # Отправляем запрос с потоком
            full_response = ""
            for result in self._model.run_stream(self.history.to_api_format()):
                for alternative in result:
                    if hasattr(alternative, 'text'):
                        chunk = alternative.text
                        full_response = chunk  # run_stream возвращает накопленный текст
                        yield chunk
            
            # Добавляем полный ответ в историю
            self.history.add_message("assistant", full_response)
            
        except Exception as e:
            error_msg = f"❌ Ошибка при запросе к YandexGPT: {str(e)}"
            yield error_msg
    
    def clear_history(self):
        """Очистить историю чата"""
        self.history.clear()
    
    def get_stats(self) -> Dict:
        """Получить статистику"""
        return {
            "messages_count": len(self.history.messages),
            "model": self.model_name,
            "initialized": self._initialized,
        }
