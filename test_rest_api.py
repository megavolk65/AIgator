"""
Тест REST API клиента YandexGPT
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.ai.yandex_gpt_rest import YandexGPTRestClient

def test_rest_api():
    """Тестирование REST API"""
    print("=== Тест YandexGPT REST API ===\n")
    
    client = YandexGPTRestClient()
    
    print("1. Проверка конфигурации...")
    stats = client.get_stats()
    print(f"Модель: {stats['model']}")
    print(f"Авторизованный ключ: {'✅' if stats['has_service_account_key'] else '❌'}")
    print(f"IAM токен: {'✅' if stats['has_iam_token'] else 'будет сгенерирован'}\n")
    
    print("2. Отправка тестового сообщения...")
    response = client.send_message("Привет! Это тестовое сообщение. Ответь коротко.")
    
    print("\n=== Ответ от YandexGPT ===")
    print(response)
    print("\n=== Тест завершён ===")

if __name__ == "__main__":
    test_rest_api()
