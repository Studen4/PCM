import os
from google import genai
from dotenv import load_dotenv

# Завантажуємо ключ
load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")

if not api_key:
    print("❌ Ключ не знайдено в .env")
    exit()

# Ініціалізація клієнта
client = genai.Client(api_key=api_key)

print("🔍 Список доступних моделей:")
try:
    # Отримуємо список всіх доступних моделей
    for model in client.models.list():
        print(f"Model Name: {model.name}")
        # Для зручності виводимо підтримувані методи, якщо є
        if hasattr(model, 'supported_generation_methods'):
            print(f"   Methods: {model.supported_generation_methods}")
except Exception as e:
    print(f"❌ Помилка при отриманні списку моделей: {e}")
