import os
import json
import time  # Додайте цей імпорт
from google import genai
from google.genai import types
from dotenv import load_dotenv
from seller.seller_prompts import get_product_analyzer_prompt

load_dotenv()


def analyze_product_filters(filters_data, mode="template", user_choices=None):
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        return None

    client = genai.Client(api_key=api_key)
    prompt = get_product_analyzer_prompt(filters_data, mode, user_choices)

    # Максимум 3 спроби
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model='models/gemini-3.5-flash',
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.0,
                    response_mime_type="application/json"
                )
            )
            return json.loads(response.text)

        except Exception as e:
            error_str = str(e)
            if "503" in error_str:
                print(f"⚠️ Модель зайнята (спроба {attempt + 1}/{max_retries}). Чекаємо 3 секунди...")
                time.sleep(3)  # Чекаємо перед наступною спробою
            else:
                print(f"❌ Критична помилка аналізу: {e}")
                break  # Якщо інша помилка - виходимо

    return None
