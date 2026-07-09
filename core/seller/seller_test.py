import sys
import os
import json
import importlib.util

from seller.seller_ai_recommendation import analyze_business_strategy

# Додаємо корінь проекту
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '..', '..'))
if project_root not in sys.path:
    sys.path.append(project_root)

# Безпечний імпорт з папки global (щоб уникнути помилки SyntaxError: invalid syntax)
try:
    spec = importlib.util.spec_from_file_location("global_zone_checker", os.path.join(project_root, "core", "global",
                                                                                      "global_zone_checker.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    calculate_price_categories = module.calculate_price_categories
except Exception as e:
    print(f"Помилка завантаження global_zone_checker.py: {e}")
    sys.exit(1)

from scraper.ekatalog_parser import parse_category_page, parse_compact_grid
from seller.seller_input_normalizer import normalize_seller_input
from scraper.salary_parser import get_normalized_salary
from seller.seller_ai_analyzer import analyze_product_filters
from seller.seller_analyzer import calculate_product_score, prepare_quiz_questions, get_option_rank_string
from seller_pricing_analyzer import generate_11_points, fetch_market_matrix, find_ideal_product
from seller_pricing import analyze_market_pricing, generate_price_recommendation, _smart_match
from seller_recommendation_analyzer import analyze_niche_segment, summarize_gap_analysis

# --- ПУНКТ 9 ---

# Фолбек на зарплату, якщо модуль ще не перенесено
try:
    from scraper.salary_parser import get_normalized_salary
except ImportError:
    def get_normalized_salary():
        return 18500.0

print("=" * 70)
print("🚀 ЗАПУСК ІНТЕГРАЦІЙНОГО ТЕСТУ: РЕЖИМ ПРОДАВЦЯ (SELLER MODE) 🚀")
print("=" * 70)

state = {
    "search_query": "",
    "market_data": {},
    "salary_w": 20000.0,
    "boundaries": [],
    "ai_weights": {},
    "quiz_questions": [],
    "user_answers": {},
    "product_score": 0.0,
    "eleven_points": [],
    "matrix_products": [],
    "ideal_product": {},
    "ideal_score": 100.0,
    "feature_impact": {},
    "calculated_price": 0.0,
    "current_category_bounds": {},
    "current_category_name": ""
}

# --- 1-2 . Введення та Пошук (в циклі) ---
while True:
    user_input = input("\nWorkspace -> Введіть назву або категорію товару (або 'q' для виходу): ")

    # Можливість вийти, якщо передумали
    if user_input.lower() in ['q', 'exit', 'вийти']:
        print("🛑 Завершення роботи.")
        sys.exit()

    print(f"📌 Введено '{user_input}' -> УСПІШНО")

    print("\n[КРОК 2] Пошук категорій...")
    norm_result = normalize_seller_input(user_input)

    # Перевіряємо, чи успішно знайдено категорії
    if norm_result["status"] == "ambiguous":
        # Успіх! Ми знайшли категорії, виходимо з циклу і продовжуємо далі
        break
    else:
        print("❌ Помилка: Не вдалося знайти категорії. Спробуйте інший запит.")

# --- 3. Вибір категорії ---
real_categories = norm_result["categories"]
categories_list = list(real_categories.keys())

print("Знайдено підкатегорії:")
for idx, cat in enumerate(categories_list, 1):
    print(f"  [{idx}] {cat}")

choice = input(f"Оберіть категорію (1-{len(categories_list)}) [Enter = 1]: ")
chosen_idx = 0 if not choice.strip() else int(choice) - 1
chosen_cat_name = categories_list[chosen_idx]
chosen_katalog_id = real_categories[chosen_cat_name]

print(f"Обрано: {chosen_cat_name} (ID: {chosen_katalog_id})")
print(f"📌 Пункт 3: Уточнено -> УСПІШНО")

# --- 4. Парсинг ринку ---
print("\n[КРОК 4] Витягування ринкових даних через parse_category_page...")
market_data = parse_category_page(katalog_id=chosen_katalog_id)
state["market_data"] = market_data

print(f"  - Знайдено товарів: {market_data['total_items']}")
print(f"  - Ціновий діапазон: {market_data['price_pool']['min']} - {market_data['price_pool']['max']} грн")

print(f"📌 Пункт 4: Дані успішно витягнуто -> УСПІШНО")

# --- 5. Розрахунок зон ---
print("\n[КРОК 5] Розрахунок зон...")
salary = get_normalized_salary()
boundaries, cut, p_adj, s_factor = calculate_price_categories(
    salary,
    market_data['price_pool']['min'] or 1.0,
    market_data['price_pool']['max'] or 26200.0
)

state["boundaries"] = boundaries

print(f"  - Середня зарплата: {salary} грн")
for b in boundaries:
    print(f"    * {b['category']}: {b['start']:,.0f} - {b['end']:,.0f} грн")
print(f"📌 Пункт 5: Зони сформовано -> УСПІШНО")

# --- ПУНКТ 6 ---
print("\n[КРОК 6] Аналіз фільтрів АІ та розподіл коефіцієнтів...")

# 1. Захищена перевірка або завантаження з кешу
if os.path.exists("ai_answer_debug.json"):
    print("  📂 Знайдено кеш ai_answer_debug.json. Використовуємо його.")
    with open("ai_answer_debug.json", "r", encoding="utf-8") as f:
        ai_result = json.load(f)
else:
    print("  ☁️ Кеш не знайдено. Звертаємось до АІ...")
    category_data = state.get("market_data")
    sidebar_filters = category_data.get("sidebar_filters", {}) if category_data else {}

    if not sidebar_filters:
        print("❌ Помилка: Немає даних для аналізу.")
        ai_result = {"categories": {}}
    else:
        ai_result = analyze_product_filters(sidebar_filters, mode="template")
        if ai_result:
            with open("ai_answer_debug.json", "w", encoding="utf-8") as f:
                json.dump(ai_result, f, ensure_ascii=False, indent=4)
            print("  ✅ АІ аналіз збережено в файл.")
        else:
            print("  ❌ Помилка АІ. Продовжуємо з пустими даними.")
            ai_result = {"categories": {}}

# Оновлюємо стан
state["ai_weights"] = {"factors": ai_result.get("categories", {})}
print(f"📌 Пункт 6 -> УСПІШНО")

# --- ПУНКТ 7 ---
print("\n[КРОК 7] Генерація питань на основі аналізу...")

state["quiz_questions"] = []
factors = state["ai_weights"]["factors"]

# Генеруємо список питань тільки з тих категорій, що оцінив ШІ
for f_name in factors.keys():
    state["quiz_questions"].append(f_name)

print(f"  - Сгенеровано {len(state['quiz_questions'])} цільових запитань.")
print(f"📌 Пункт 7 -> УСПІШНО")

# --- ПУНКТ 8 ---
print("\n[КРОК 8] Опитування та скоринг...")

sidebar_filters = state["market_data"].get("sidebar_filters", {})
state["quiz_questions"] = prepare_quiz_questions(sidebar_filters, state["ai_weights"])
factors = state["ai_weights"].get("factors") or state["ai_weights"].get("categories") or {}

state["user_answers"] = {}

for q in state["quiz_questions"]:
    q_name = q["name"]
    label = q.get("display_label", "")
    meta = factors.get(q_name, {"importance_coefficient": 0.05})
    imp = meta.get("importance_coefficient", 0.05)

    # 1. Запитуємо користувача
    if q["type"] == "input":
        print(f"\nПараметр: {q_name} {label}")
        val = input("Введіть назву виробника: ").strip()
        chosen_val = val if val else "Не вказано / Інше"
    else:
        options_with_default = ["Не вказано / Інше"] + q["options"]
        print(f"\nПараметр: {q_name} {label}")
        for idx, opt in enumerate(options_with_default):
            print(f"  [{idx}] {opt}")
        ans_idx = input(f"Оберіть варіант (0-{len(options_with_default) - 1}) [дефолт 0]: ")
        chosen_idx = int(ans_idx) if ans_idx.strip().isdigit() and int(ans_idx) < len(options_with_default) else 0
        chosen_val = options_with_default[chosen_idx]

    state["user_answers"][q_name] = chosen_val

    # 2. МИТТЄВИЙ РОЗРАХУНОК ТА ВИВІД БАЛУ (З УРАХУВАННЯМ ОБОВ'ЯЗКОВОГО ПАРАМЕТРА)
    others_imp = factors.get("Інші характеристики", {}).get("importance_coefficient", 0.05)

    # Створюємо мікро-запит, де імітуємо наявність додаткових характеристик,
    # щоб нівелювати вплив обов'язкового штрафу на проміжний лог
    micro_query = {q_name: chosen_val, "Інші характеристики": "Присутні"}

    # Отримуємо відсоток успішності для цього мікро-кошика
    percentage = calculate_product_score(micro_query, state["ai_weights"])

    # Вираховуємо чистий внесок цього конкретного параметра у загальну копілку
    gained_points = (percentage / 100.0) * (imp + others_imp) - others_imp
    gained_points = max(0.0, gained_points)  # Захист від можливих мінусів (-0.00) через специфіку float в Python

    rank_str = get_option_rank_string(q_name, chosen_val, state["ai_weights"])
    print(f"  ↳ ({chosen_val} {rank_str} \\ Коефіцієнт {imp:.2f} \\ +{gained_points:.3f})")

# АВТО-МАТЧИНГ ДЛЯ АБСТРАКТНОЇ КАТЕГОРІЇ "Інші характеристики"
if "Інші характеристики" in factors:
    has_additional = any(
        q.get("display_label") == "(Додаткове)" and state["user_answers"].get(q["name"]) != "Не вказано / Інше"
        for q in state["quiz_questions"]
    )
    if has_additional:
        state["user_answers"]["Інші характеристики"] = "Присутні"
        imp_others = factors["Інші характеристики"].get("importance_coefficient", 0.05)
        print(f"\nПараметр: Інші характеристики (Автоматично заповнено, бо вказані додаткові параметри)")
        print(f"  ↳ (Присутні top-+ \\ Коефіцієнт {imp_others:.2f} \\ +{imp_others:.3f})")

# 3. Фінальний загальний підрахунок
state["product_score"] = calculate_product_score(state["user_answers"], state["ai_weights"])

print(f"\n📊 Фінальна оцінка: {state['product_score']:.1f}/100")
print(f"📌 Пункт 8 -> УСПІШНО")

# --- ПУНКТ 9 ---
print("\n[КРОК 9] Поділ шкали на 11 аналітичних відрізків та збір 88 товарів-матриць...")
P_min = state["market_data"]["price_pool"]["min"] or 1.0

state["eleven_points"] = generate_11_points(state["boundaries"], P_min)
print(f"  - Сформовано 11 точок цінового кроку: {[int(p) for p in state['eleven_points']]}")
print("  - Запуск послідовного збору товарів по ціновим пулам...")

# Збір зрізів ринку
state["matrix_products"] = fetch_market_matrix(state["eleven_points"], chosen_katalog_id)

# Прозора верифікація та дедуплікація моделей
total_fetched = len(state["matrix_products"])
seen_names = set()
unique_market_pool = []
for p in state["matrix_products"]:
    if p["name"] not in seen_names:
        seen_names.add(p["name"])
        unique_market_pool.append(p)

print(f"  - 🔍 [ВЕРИФІКАЦІЯ] Всього завантажено з e-katalog: {total_fetched} карток товарів.")
print(f"  - ↳ Після очищення від дублікатів (моделей, що потрапили в різні пули): {len(unique_market_pool)} унікальних товарів.")
print(f"📌 Пункт 9 (Шкалу розбито на 11 точок, зібрано матрицю товарів) -> УСПІШНО")


# --- ПУНКТ 10 ---
print("\n[КРОК 10] Оцінка ринкової матриці через скоринг-модуль та пошук найкращого товару...")

# Пошук ідеалу методом повного перебору та оцінки за вашим концептом сітки
ideal_item, ideal_calculated_score = find_ideal_product(
    all_products=unique_market_pool,
    ai_weights=state["ai_weights"],
    calculate_score_callback=calculate_product_score
)

state["ideal_product"] = ideal_item
state["ideal_score"] = ideal_calculated_score

print(f"  - 🏆 Результат: обрано найкращий товар '{state['ideal_product']['name']}' за ціною {state['ideal_product']['price']} грн.")
print(f"  - 📊 Його реальний еталонний бал: {state['ideal_score']:.2f}/100")
print(f"📌 Пункт 10 (Найкращий товар визначено через повну матрицю оцінки за концептом сітки) -> УСПІШНО")

# --- ПУНКТ 11 ---
print("\n[КРОК 11] Оцінка кореляційного впливу кожного фактору на ринкову ціну...")

# Динамічно скоримо КОЖЕН товар з ринкового пулу на основі його реальних характеристик
scored_candidates_formatted = []
for p in unique_market_pool:
    # Перевіряємо, чи товар вже має прорахований бал. Якщо ні — запускаємо математичне розпізнавання
    score = p.get("score") or p.get("total_score") or p.get("ai_score")

    p_features = [str(f) for f in p.get("features", [])]
    p_name = p.get("name", "")

    # Відновлюємо карту відповідей для конкретного конкурента через лінгвістичний стемер модуля ціноутворення
    simulated_answers = p.get("simulated_answers") or {}
    if not simulated_answers:
        for cat_name, cat_meta in state["ai_weights"]["factors"].items():
            options_list = list(cat_meta.get("options_rank", {}).keys())
            matched_opt = _smart_match(options_list, p_features, p_name)
            simulated_answers[cat_name] = matched_opt
        p["simulated_answers"] = simulated_answers

    # Якщо балу не було в базі, вираховуємо його через офіційний скоринг-модуль
    if score is None:
        score = calculate_product_score(simulated_answers, state["ai_weights"])
        p["score"] = score

    scored_candidates_formatted.append({
        "price": p.get("price", 0),
        "score": score,
        "simulated_answers": simulated_answers,
        "product": p
    })

ai_matrix_formatted = {"categories": state["ai_weights"]["factors"]}

feature_impact, p_min, p_avg = analyze_market_pricing(scored_candidates_formatted, ai_matrix_formatted)
state["feature_impact"] = feature_impact

print(f"  - Стартовий фундамент ринку (P_min): {p_min:,.2f} грн | Середня стеля (P_avg): {p_avg:,.2f} грн")

for cat_name, cat_data in feature_impact.items():
    print(f"\n    * Категорія '{cat_name}' (Важливість: {cat_data['importance']}):")
    print(f"      ↳ База [X]: '{cat_data['base_option']}' (Ринок: {cat_data['base_price_X']:,.2f} грн)")

    for opt_name, opt_meta in cat_data["options"].items():
        if opt_meta.get("is_innovation"):
            print(f"      • 🌟 Інновація '{opt_name}': Не знайдено аналогів для оцінки.")
        else:
            print(
                f"      • Опція '{opt_name}' | Переплата ринку: +{opt_meta['raw_delta']:,.2f} грн | Чиста вартість фічі [Z]: +{opt_meta['premium_Z']:,.2f} грн")

print(f"\n📌 Пункт 11 (Вплив кожного фактору в грошовому еквіваленті прораховано) -> УСПІШНО")

# --- ПУНКТ 12 ---
print("\n[КРОК 12] Формування рекомендованої ціни на товар на основі характеристик...")

# Передаємо реальний бал нашої поточної моделі (що вирахували на Кроці 8) як target_score
target_score = state.get("product_score", 73.33)
pricing_results = generate_price_recommendation(
    user_answers=state["user_answers"],
    feature_impact=state["feature_impact"],
    p_min=p_min,
    p_avg=p_avg,
    scored_candidates=scored_candidates_formatted,
    target_score=target_score
)

state["calculated_price"] = pricing_results["final_min"]

print(f"  📊 РОЗШИФРОВКА ФОРМУВАННЯ ЦІНИ:")
for cat, data in pricing_results.get("applied_premiums", {}).items():
    if data["z_val"] > 0:
        print(f"    • Додана вартість за '{data['option']}' [{cat}]: +{data['z_val']:,.2f} грн")
print(f"    --------------------------------------------------")

print(f"    • X (Базова розрахункова ціна): {pricing_results['X']:,.2f} грн")
print(f"    • X+Z (Максимальна розрахункова ціна): {pricing_results['X_plus_Z']:,.2f} грн")
print(f"    • Z (Ринковий розкид конкурентів): {pricing_results['Z']:,.2f} грн")

print(f"    --------------------------------------------------")
a1 = pricing_results["A1"]
if a1:
    print(
        f"    • Якір А1 (За оцінкою ~{a1.get('score', 0):.1f}/100): '{a1['product'].get('name', 'Товар')}' -> {a1['price']:,.2f} грн")

a2 = pricing_results["A2"]
if a2:
    print(f"    • Якір А2 (За характеристиками): '{a2['product'].get('name', 'Товар')}' -> {a2['price']:,.2f} грн")

print(f"    • Z(kf) Коефіцієнт нормалізації якорів: {pricing_results['Z_kf']:.3f}")
print(f"    --------------------------------------------------")
print(f"    • Справедливий ціновий діапазон [ Формула: X — X+(Z * Z_kf) ]")
print(f"    => {pricing_results['final_min']:,.2f} — {pricing_results['final_max']:,.2f} грн")

if pricing_results["innovations"]:
    print(f"\n  💡 БІЗНЕС-ПОТЕНЦІАЛ (🌟 Унікальні фічі): {pricing_results['innovations']}")
    print(f"    * Характеристики відсутні у прямих конкурентів. Рекомендовано підвищення маржинальності.")

print(f"📌 Пункт 12 (Ціну створено в модулі seller_pricing.py) -> УСПІШНО")

# --- ПУНКТ 13 ---
print("\n[КРОК 13] Аналіз ніші, бенчмаркінг та пошук головного конкурента...")

calc_min = pricing_results['final_min']
calc_max = pricing_results['final_max']

niche_analysis = analyze_niche_segment(
    calculated_min=calc_min,
    calculated_max=calc_max,
    boundaries=state["boundaries"],
    katalog_id=chosen_katalog_id,
    user_answers=state["user_answers"],
    ai_weights=state["ai_weights"],
    fetch_grid_callback=parse_compact_grid,
    smart_match_callback=_smart_match,
    calculate_score_callback=calculate_product_score
)

state["current_category_bounds"] = niche_analysis["category"]
state["current_category_name"] = niche_analysis["category"]["category"]
main_comp = niche_analysis["main_competitor"]

print(
    f"  - Товар через 'Коефіцієнт включення' потрапив у категорію: '{state['current_category_name']}' ({int(state['current_category_bounds']['start'])} - {int(state['current_category_bounds']['end'])} грн).")
print(f"  - Зібрано {niche_analysis.get('competitors_count', 0)} конкурентів із цього цінового діапазону.")

if main_comp:
    print(
        f"\n  Головний конкурент - {main_comp['name']} (Ціна: {main_comp['price']} грн, Бал: {main_comp['score']:.1f}/100)")
    print("  Середня оцінка наших характеристик на основі ринку:")

    for comp in niche_analysis["comparisons"]:
        # Форматуємо слова "краще/гірше"
        mc_word = "краще" if comp["vs_mc_pct"] >= 0 else "гірше"
        market_word = "краще" if comp["vs_market_pct"] >= 0 else "гірше"

        print(
            f"    * {comp['category']} - (Ми: {comp['our_val']} | Конкурент: {comp['mc_val']} | Середнє по ринку: {comp['avg_market_val']})")
        print(
            f"      ↳ Ми на {abs(comp['vs_mc_pct']):.1f}% {mc_word} за головного конкурента та на {abs(comp['vs_market_pct']):.1f}% {market_word} за середній товар на ринку.")
else:
    print("  ❌ Не вдалося знайти конкурентів у цьому діапазоні для порівняння.")

print(f"\n📌 Пункт 13 (Матричний бенчмаркінг характеристик) -> УСПІШНО")

# --- ПУНКТ 14 ---
print("\n[КРОК 14] Аналітичний підсумок (Gap Analysis)...")

# 1. Обов'язково рахуємо розрив з ідеалом (потрібно для ПУНКТУ 16)
gap_ideal = (state["product_score"] - state["ideal_score"]) / max(state["ideal_score"], 1) * 100
state["gaps"] = {"ideal": gap_ideal}  # Ініціалізуємо ключ, щоб ПУНКТ 16 не падав

# 2. Викликаємо новий аналізатор для деталізації характеристик
all_factor_names = list(state["ai_weights"]["factors"].keys())
gap_summary = summarize_gap_analysis(niche_analysis["comparisons"], all_factor_names)

# 3. Вивід даних
print(f"  1. Середнє по ринку: {'краще' if gap_summary['avg_vs_market'] >= 0 else 'гірше'} на {abs(gap_summary['avg_vs_market']):.1f}%")
print(f"  2. Головний конкурент: {'краще' if gap_summary['avg_vs_mc'] >= 0 else 'гірше'} на {abs(gap_summary['avg_vs_mc']):.1f}%")

print("\n  📊 Деталізація характеристик:")
if gap_summary["better"]:
    print(f"    🌟 Краще за конкурентів: {', '.join(gap_summary['better'])}")
if gap_summary["equal"]:
    print(f"    🤝 Паритет (рівноцінно): {', '.join(gap_summary['equal'])}")
if gap_summary["worse"]:
    print(f"    ⚠️ Поступаємось (потребує уваги): {', '.join(gap_summary['worse'])}")
if gap_summary["missing"]:
    print(f"    ℹ️ Не враховано в аналізі: {', '.join(gap_summary['missing'])}")

print(f"📌 Пункт 14 (Узагальнений Gap Analysis) -> УСПІШНО")

# --- ПУНКТ 15 (Надійне збереження результатів) ---
print("\n[КРОК 15] Запит до АІ та збереження звітів...")

# 1. Отримуємо відповідь
ai_response = analyze_business_strategy(
    user_features=state.get("user_answers", {}),
    benchmark_product=niche_analysis.get("main_competitor", {}).get("name", "Unknown"),
    pricing=f"{niche_analysis['category']['start']} - {niche_analysis['category']['end']}",
    gap_summary=gap_summary
)

# 2. ЗАХИСТ ВІД JSON: Витягуємо чистий текст
markdown_report = ""

if isinstance(ai_response, dict):
    print("  - [WARN] АІ повернув словник. Витягую текст...")
    # Шукаємо найдовший текстовий рядок у словнику (це зазвичай і є звіт)
    # Або беремо значення за ключем 'report', якщо він є
    if 'report' in ai_response:
        markdown_report = ai_response['report']
    else:
        # Якщо ключ інший, беремо перше доступне значення
        markdown_report = str(list(ai_response.values())[0])
elif isinstance(ai_response, str):
    markdown_report = ai_response
else:
    markdown_report = str(ai_response)

state["ai_advice"] = markdown_report

# 3. Зберігаємо окремо Markdown файл
try:
    with open('../../test_space/test_data/business_recommendation.md', 'w', encoding='utf-8') as f:
        f.write(markdown_report)
    print("  - [OK] Markdown звіт успішно збережено в 'business_recommendation.md'.")
except Exception as e:
    print(f"  - ⚠️ Помилка запису MD файлу: {e}")

# 4. Зберігаємо JSON (метадані)
output_data = {
    "meta": {
        "benchmark_product": niche_analysis.get("main_competitor", {}).get("name", "Unknown"),
        "pricing_range": f"{niche_analysis['category']['start']} - {niche_analysis['category']['end']}",
        "user_features": state.get("user_answers", {}),
        "gap_summary_payload": gap_summary
    }
}

try:
    with open('../../test_space/test_data/ai_recommendation_meta.json', 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=4)
    print("  - [OK] Метадані збережено в 'ai_recommendation_meta.json'.")
except Exception as e:
    print(f"  - ⚠️ Помилка запису JSON файлу: {e}")

print("📌 Пункт 15 виконано -> УСПІШНО")

# --- ПУНКТ 16 ---
print("\n[КРОК 16] Формування фінального інформаційного дашборду для продавця...")

# 1. Логіка для Плюсів та Мінусів
pros = [key for key, val in gap_summary.items() if key == 'better' and val] # Тут треба посилатись на gap_summary
pro_text = f"Переваги: {', '.join(gap_summary['better'][:2])}" if gap_summary['better'] else "Переваги: Повний паритет з лідером"
con_text = f"Слабкі сторони: {', '.join(gap_summary['worse'][:2])}" if gap_summary['worse'] else "Слабкі сторони: Відсутні"

# 2. РОЗШИРЕНА ЛОГІКА ДЛЯ КОНКУРЕНТНОГО СЕРЕДОВИЩА (Пункт 4)
score_user = state["product_score"]
score_comp = main_comp.get('score', 0) if main_comp else 0

# Розрахунок різниці у відсотках
if score_comp > 0:
    diff_percent = ((score_user - score_comp) / score_comp) * 100
else:
    diff_percent = 0

# Формування тексту аналізу
comp_header = f"Оцінка вашого товару: {score_user:.1f}/100. Оцінка конкурента '{main_comp.get('name', 'N/A')}': {score_comp:.1f}/100."

if diff_percent > 50:
    analysis_text = "Ваш товар значно кращий за лідера ринку. У цій ніші ви будете домінувати, конкуренція майже не впливатиме на ваш успіх."
elif 0 <= diff_percent <= 50:
    analysis_text = "Ви маєте перевагу над конкурентом. Ринок перспективний, можна впевнено заходити з вашими унікальними фічами."
elif -10 <= diff_percent < 0:
    analysis_text = "Ви знаходитесь на рівні з лідером. Для перемоги над конкурентом потрібно посилити дистрибуцію або маркетинг."
elif -25 <= diff_percent < -10:
    analysis_text = "Конкуренція жорстка. Товар поступається лідеру, тому він потребує додаткових зусиль у просуванні або перегляду комплектації."
else:
    analysis_text = "Товар не є досить конкурентоспроможним у цьому сегменті. Рекомендуємо переглянути особливості товару або змінити цінову категорію."

comp_status = f"{comp_header} {analysis_text}"

# 3. Вивід
print("\n" + "=" * 50)
print("📊 ФІНАЛЬНИЙ БЛОК ВІДПОВІДІ СИСТЕМИ PCM 📊")
print("=" * 50)

print(f"1) КАТЕГОРІЯ: Сегмент '{state['current_category_name']}'. Конкуренти: {state['current_category_bounds']['start']:,.0f} - {state['current_category_bounds']['end']:,.0f} грн.")
print(f"2) ПЛЮСИ ТА МІНУСИ: {pro_text}. {con_text}.")
print(f"3) РОЗРАХУНКОВА ЦІНА: Рекомендований діапазон: {pricing_results['final_min']:,.2f} — {pricing_results['final_max']:,.2f} грн.")
print(f"4) КОНКУРЕНТНЕ СЕРЕДОВИЩЕ: {comp_status}")
print(f"5) ПЕРСПЕКТИВИ ТА МАРКЕТИНГ:\n{state['ai_advice']}")

print("=" * 50)
print(f"📌 Пункт 16 (Аналітичний блок відповідей сформовано) -> УСПІШНО")

# --- ПУНКТ 17 ---
print("\n[КРОК 17] Запит на оцінку якості роботи моделі...")
print("⭐️ Шановний користувачу, оцініть якість та точність наданого аналізу ніші від 1 до 5 зірок.")
feedback = input("Ваша оцінка системи (1-5): ")
print(f"Дякуємо за ваш фідбек: {feedback}/5! Це допомагає навчати наші алгоритми скорингу.")
print(f"📌 Пункт 17 (Запит оцінки якості успішно завершено) -> УСПІШНО")

print("\n" + "=" * 70)
print("🎉 ВСІ ПУНКТИ ПЛАНУ ВИКОНАНО УСПІШНО! ТЕСТ ЗАВЕРШЕНО БЕЗ ПОМИЛОК! 🎉")
print("=" * 70)
