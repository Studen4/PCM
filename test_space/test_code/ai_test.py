import sys
import os
import json
from datetime import datetime

# --- Налаштування шляхів ---
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '..', '..'))

if project_root not in sys.path:
    sys.path.append(project_root)

core_path = os.path.join(project_root, "core")
if core_path not in sys.path:
    sys.path.append(core_path)

# --- Імпорти робочих модулів ---
try:
    from seller.seller_input_normalizer import normalize_seller_input
    from scraper.ekatalog_parser import parse_category_page
    from seller.seller_ai_analyzer import analyze_product_filters
    from seller.seller_prompts import get_product_analyzer_prompt
except ImportError as e:
    print(f"❌ Помилка імпорту модулів: {e}")
    sys.exit(1)


def run_test():
    print("=" * 70)
    print("🚀 AI PROMPT DEBUGGER (З розширеною діагностикою) 🚀")
    print("=" * 70)

    # КРОК 1. Ввід товару
    user_input = input("\nВведіть назву або категорію товару (або 'q' для виходу): ").strip()
    if user_input.lower() in ['q', 'exit', 'вийти'] or not user_input:
        print("🛑 Завершення роботи.")
        return

    print("\n[КРОК 1-2] Пошук категорій...")
    norm_result = normalize_seller_input(user_input)

    if norm_result.get("status") != "ambiguous":
        print("❌ Помилка: Не вдалося знайти категорії.")
        return

    real_categories = norm_result["categories"]
    categories_list = list(real_categories.keys())

    # КРОК 3. Вибір категорії
    print("\n[КРОК 3] Знайдено підкатегорії:")
    for idx, cat in enumerate(categories_list, 1):
        print(f"  [{idx}] {cat}")

    choice = input(f"Оберіть категорію (1-{len(categories_list)}) [Enter = 1]: ")
    chosen_idx = 0 if not choice.strip() else int(choice) - 1
    chosen_cat_name = categories_list[chosen_idx]
    chosen_katalog_id = real_categories[chosen_cat_name]

    print(f"✅ Обрано: {chosen_cat_name} (ID: {chosen_katalog_id})")

    print("\n⏳ Витягування ринкових даних (parse_category_page)...")
    market_data = parse_category_page(katalog_id=chosen_katalog_id)

    try:
        os.system("taskkill /F /IM node.exe /T >nul 2>&1")
    except:
        pass

    sidebar_filters = market_data.get("sidebar_filters", {}) if market_data else {}
    if not sidebar_filters:
        print("❌ Помилка: Не вдалося витягнути фільтри з сайту.")
        return

    print(f"📊 Знайдено фільтрів для аналізу: {len(sidebar_filters)}")

    # =====================================================================
    # КРОК 4. ДІАГНОСТИКА ТА ЗАПУСК ГЕНЕРАЦІЇ
    # =====================================================================
    print("\n[КРОК 4] 🧠 Перевірка середовища перед запуском ШІ...")

    # Перевірка 1: Чи існує API ключ в системі
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("❌ КРИТИЧНА ПОМИЛКА: GOOGLE_API_KEY не знайдено в .env файлі або змінних оточення!")
        return
    else:
        # Показуємо перші й останні символи ключа для перевірки його валідності
        print(f"🔗 API Ключ знайдено: {api_key[:4]}...{api_key[-4:] if len(api_key) > 4 else ''}")

    # Перевірка 2: Валідація промпту (чи генерується він взагалі, чи не падає через кодування)
    print("📝 Тестуємо генерацію тексту промпту...")
    try:
        test_prompt = get_product_analyzer_prompt(sidebar_filters, mode="template")
        print(f"✅ Промпт успішно сформовано. Довжина тексту промпту: {len(test_prompt)} символів.")
    except Exception as prompt_err:
        print(f"❌ Помилка при генерації промпту в seller_prompts.py: {prompt_err}")
        return

    print("\n🚀 Відправляємо дані в `seller_ai_analyzer.py`. Якщо тут зависне — проблема в циклі try/except або запиті.")
    print("👉 (Слідкуйте, чи з'являться повідомлення '⚠️ Модель зайнята...')")

    ai_result = None
    try:
        # Виклик оригінальної функції
        ai_result = analyze_product_filters(sidebar_filters, mode="template")
    except Exception as e:
        print(f"❌ Критична помилка під час виконання analyze_product_filters: {e}")
        return

    if ai_result is None:
        print("\n❌ AI повернув None. Можливі причини:")
        print("   1. Спрацював ліміт запитів (Quota Exceeded).")
        print("   2. Усі 3 спроби обробки помилки 503 закінчилися невдачею.")
        print("   3. Помилка автентифікації ключа API.")
        return

    print("🟢 ШІ успішно згенерував відповідь!")

    # КРОК 5. Записуємо наш результат в файл
    print("\n[КРОК 5] Збереження результатів...")
    output_dir = os.path.join(project_root, "test_space", "test_data")
    os.makedirs(output_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = "".join(c for c in chosen_cat_name if c.isalnum() or c in (' ', '_', '-')).replace(' ', '_')
    filepath = os.path.join(output_dir, f"ai_debug_{safe_name}_{timestamp}.json")

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(ai_result, f, ensure_ascii=False, indent=4)

    print(f"✅ Готово! Файл для відлагодження промпту збережено у:\n{filepath}")
    print("=" * 70)


if __name__ == "__main__":
    run_test()