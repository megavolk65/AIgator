"""
Тестовый скрипт для проверки прямого API доступа к YandexGPT
"""

import sys
import os
import requests
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config

def test_direct_api():
    """Тестирование прямого API"""
    print("=== Тест прямого API YandexGPT ===\n")
    
    url = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Api-Key {config.YANDEX_API_KEY}",
        "x-folder-id": config.YANDEX_FOLDER_ID
    }
    
    data = {
        "modelUri": f"gpt://{config.YANDEX_FOLDER_ID}/{config.YANDEX_MODEL}",
        "completionOptions": {
            "stream": False,
            "temperature": config.TEMPERATURE,
            "maxTokens": config.MAX_TOKENS
        },
        "messages": [
            {
                "role": "system",
                "text": "Ты полезный AI-ассистент."
            },
            {
                "role": "user",
                "text": "Привет! Это тестовое сообщение. Ответь коротко."
            }
        ]
    }
    
    print("1. Отправка запроса к API...")
    print(f"URL: {url}")
    print(f"Folder ID: {config.YANDEX_FOLDER_ID}")
    print(f"Model: {config.YANDEX_MODEL}\n")
    
    try:
        response = requests.post(url, headers=headers, json=data)
        
        print(f"Статус: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            answer = result["result"]["alternatives"][0]["message"]["text"]
            print("\n=== Ответ от YandexGPT ===")
            print(answer)
            print("\n✅ Прямой API работает!")
        else:
            print("\n❌ Ошибка:")
            print(response.text)
    
    except Exception as e:
        print(f"\n❌ Исключение: {str(e)}")
    
    print("\n=== Тест завершён ===")

if __name__ == "__main__":
    test_direct_api()
