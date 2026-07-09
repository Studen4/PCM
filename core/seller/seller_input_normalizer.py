import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from scraper.ekatalog_parser import parse_search_page

def normalize_seller_input(user_input: str):
    clean_query = user_input.strip()
    if not clean_query:
        return {"status": "error", "message": "Будь ласка, введіть назву товару."}

    # Використовуємо новий парсер для пошуку категорій
    search_data = parse_search_page(clean_query)

    # Перевірка результатів
    if not search_data["categories"]:
        return {
            "status": "not_found",
            "message": f"За запитом '{clean_query}' не знайдено релевантних категорій."
        }

    return {
        "status": "ambiguous",
        "query": clean_query,
        "message": "Знайдено декілька підкатегорій ринку. Потрібно уточнити вибір.",
        "categories": search_data["categories"]
    }
