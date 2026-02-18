"""
Тестовый скрипт для проверки API Yandex Cloud
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.ai import YandexGPTClient

def test_api():
    """Тестирование API"""
    print("=== Тест YandexGPT API ===\n")
    
    client = YandexGPTClient()
    
    print("1. Инициализация клиента...")
    if client.initialize():
        print("✅ Клиент успешно инициализирован\n")
    else:
        print(f"❌ Ошибка инициализации: {client.error_message}\n")
        return
    
    print("2. Отправка тестового сообщения...")
    response = client.send_message("Привет! Это тестовое сообщение. Ответь коротко.")
    
    print("\n=== Ответ от YandexGPT ===")
    print(response)
    print("\n=== Тест завершён ===")

if __name__ == "__main__":
    test_api()
