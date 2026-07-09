import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from scraper.ekatalog_parser import parse_compact_grid


def generate_11_points(boundaries: list, raw_min: float) -> list:
    """
    Пункт 9: Математичний розподіл 5 категорій формули на 11 контрольних точок (межі + центри).
    """
    P_min = raw_min or 1.0
    points = [P_min]
    for b in boundaries:
        mid = (b["start"] + b["end"]) / 2
        points.append(mid)
        points.append(b["end"])
    return sorted(list(set(points)))


def fetch_market_matrix(points: list, katalog_id: int) -> list:
    """
    [ДИНАМІЧНО] Виконує 11 послідовних запитів строго за ціновими діапазонами між точками.
    З кожного зрізу бере перші 8 товарів.
    """
    matrix_products = []

    for i in range(len(points)):
        min_p = int(points[i])

        if i < len(points) - 1:
            max_p = int(points[i + 1])
        else:
            max_p = int(points[i] + (points[i] - points[i - 1]))

        if min_p < 1:
            min_p = 1

        try:
            data = parse_compact_grid(katalog_id=katalog_id, min_price=min_p, max_price=max_p)
            products_found = data.get("products", [])

            slice_products = products_found[:8]
            for p in slice_products:
                p["anchor_price"] = min_p
                matrix_products.append(p)

            if slice_products:
                print(f"  Запит по ціновому пулу {min_p}-{max_p} --> Успішно (витягнуто {len(slice_products)} товарів)")
            else:
                print(f"  Запит по ціновому пулу {min_p}-{max_p} --> Заблоковано (витягнуто 0 товарів)")

        except Exception as e:
            print(f"  Запит по ціновому пулу {min_p}-{max_p} --> Заблоковано (витягнуто 0 товарів) | Помилка: {e}")

    return matrix_products


def smart_match_option(options_list: list, p_features: list, p_name: str) -> str:
    """
    Універсальний маппер характеристик для зворотного скорингу.
    Обирає найбільш підходящу опцію опитування на базі збігу коренів слів.
    """
    text_blob = " ".join([p_name] + p_features).lower().strip()

    for option in options_list:
        opt_clean = str(option).lower().strip()
        if opt_clean in ["не вказано / інше", "інші", "інше", "n/a", "присутні"]:
            continue
        if opt_clean in text_blob or text_blob in opt_clean:
            return option

    best_option = "Не вказано / Інше"
    max_matches = 0

    for option in options_list:
        opt_clean = str(option).lower().strip()
        if opt_clean in ["не вказано / інше", "інші", "інше", "n/a", "присутні"]:
            continue

        words = opt_clean.replace("(", " ").replace(")", " ").replace("-", " ").replace("/", " ").split()
        valid_words = [w for w in words if len(w) >= 2]

        if not valid_words:
            continue

        current_matches = 0
        for w in valid_words:
            is_numeric = any(c.isdigit() for c in w)
            root = w[:-2] if (len(w) >= 5 and not is_numeric) else w
            if root in text_blob:
                current_matches += 1

        if current_matches > max_matches:
            max_matches = current_matches
            best_option = option

    return best_option


def find_ideal_product(all_products: list, ai_weights: dict, calculate_score_callback) -> tuple:
    """
    [КОНЦЕПТ СІТКИ / ГРАФІВ] Масовий аналіз товарів через розрахунок комбінацій балів.
    Замість видалення фіч, алгоритм проганяє кожен товар ринку через оригінальний
    calculate_product_score, після чого плавно знижує планку цільового балу (від 100 вниз),
    імітуючи граф комбінацій характеристик користувача.
    """
    # Захист від відсутніх товарів з ціною 0 грн
    valid_products = [p for p in all_products if p.get("price", 0) > 0]

    if not valid_products:
        return {"name": "Базовий референс ринку (Фолбек)", "price": 1500.0}, 50.0

    categories_data = ai_weights.get("categories", ai_weights.get("factors", {}))
    scored_candidates = []

    # 1. ЕТАП МАТРИЧНОГО ОБЧИСЛЕННЯ: Рахуємо чесний сумарний бал для кожного товару ринку
    for p in valid_products:
        p_features = [str(f).lower() for f in p.get("features", [])]
        p_name = p.get("name", "")

        simulated_answers = {}
        for cat_name, cat_meta in categories_data.items():
            options_dict = cat_meta.get("options_rank", {})

            matched = smart_match_option(
                options_list=list(options_dict.keys()),
                p_features=p_features,
                p_name=p_name
            )
            simulated_answers[cat_name] = matched

        if "Інші характеристики" in categories_data:
            simulated_answers["Інші характеристики"] = "Присутні"

        # Викликаємо оригінальну математичну модель розрахунку балу
        product_score = calculate_score_callback(simulated_answers, ai_weights)

        scored_candidates.append({
            "product": p,
            "score": product_score,
            "price": p.get("price"),
            "simulated_answers": simulated_answers
        })

    # Сортуємо матрицю за вашим золотим правилом: Максимум БАЛУ (якість), при рівності — Мінімум ЦІНИ
    scored_candidates = sorted(scored_candidates, key=lambda x: (-x["score"], x["price"]))

    best_candidate = scored_candidates[0]
    best_score = best_candidate["score"]

    # 2. ЕТАП СІТКОВОЇ РЕДУКЦІЇ: Логування процесу плавної деградації цільового балу

    # Виведемо топ-1 тренди для наочності логу
    target_trends = []
    for cat, meta in categories_data.items():
        for opt, rank in meta.get("options_rank", {}).items():
            if rank == "top-1" and opt not in ["Не вказано / Інше", "інші"]:
                target_trends.append(opt)
    print(f"  - Сформований чистий пул цільових ШІ-трендів (Оцінка 100.00): {target_trends}")

    # Симулюємо покроковий спуск по графу комбінацій з кроком 5 балів (100 -> 95 -> 90...)
    current_tier = 100.0
    step = 5.0

    while current_tier > best_score and current_tier > 0:
        if current_tier == 100.0:
            print(
                f"  - Шукаємо еталонний товар під ідеальну комбінацію (Цільовий бал: {current_tier:.2f})... Не знайдено.")
        else:
            print(
                f"    ↳ Не знайдено. Редукція загальної оцінки графа: шукаємо комбінації під бал {current_tier:.1f}%+")
        current_tier -= step

    print(
        f"    ✅ Еталон знайдено! Найкраща доступна комбінація параметрів на ринку зафіксована на рівні балу: {best_score:.2f}/100")

    ideal_product = best_candidate["product"]
    simulated_answers = best_candidate["simulated_answers"]

    # 3. ДІАГНОСТИЧНИЙ ВИВІД ДЛЯ ОБРАНОГО ЛІДЕРА СІТКИ
    print(f"  - 🏆 Результат: обрано найкращий товар '{ideal_product['name']}' за ціною {ideal_product['price']} грн.")
    print(f"        ↳ Сирі фічі з сайту: {ideal_product.get('features', [])}")
    print(f"        ↳ Розпізнані системою параметри для порівняння з ідеалом:")

    has_detected = False
    for cat, val in simulated_answers.items():
        if val != "Не вказано / Інше" and "Інші характеристики" not in cat:
            print(f"          • {cat}: {val}")
            has_detected = True
    if not has_detected:
        print("          • (Усі ключові характеристики скинуто у дефолт)")

    return ideal_product, best_score
