import os
import time
from google import genai
from google.genai import types
from dotenv import load_dotenv
from seller.seller_prompts import get_business_recommendation_prompt

load_dotenv()

def analyze_business_strategy(user_features, benchmark_product, pricing, gap_summary):
    """
    Викликає ШІ для отримання бізнес-рекомендацій у форматі Markdown.
    """
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        return "⚠️ Помилка: Ключ API (GOOGLE_API_KEY) відсутній у файлі .env"

    client = genai.Client(api_key=api_key)
    prompt = get_business_recommendation_prompt(user_features, benchmark_product, pricing, gap_summary)

    # Максимум 3 спроби
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model='models/gemini-3.1-flash-lite',
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.2, # Трохи креативності для стратегій
                    # response_mime_type ВИДАЛЕНО, щоб дозволити звичайний текст / Markdown
                )
            )
            # Повертаємо чистий текст (строку), як і просили в промпті
            return response.text

        except Exception as e:
            print(f"⚠️ Помилка отримання рекомендацій (спроба {attempt + 1}/{max_retries}): {e}")
            time.sleep(2)

    return "⚠️ Помилка: Не вдалося отримати аналіз від ШІ після кількох спроб."
