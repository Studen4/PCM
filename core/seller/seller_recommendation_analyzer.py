import numpy as np


def get_inclusion_category(calc_min: float, calc_max: float, boundaries: list) -> dict:
    """
    Визначає "Коефіцієнт включення" (Inclusion Coefficient).
    Знаходить зону, з якою наш розрахований ціновий діапазон має найбільший перетин.
    """
    best_cat = boundaries[1] if len(boundaries) > 1 else boundaries[0]
    max_overlap = -1.0

    for b in boundaries:
        overlap_min = max(calc_min, b["start"])
        overlap_max = min(calc_max, b["end"])
        overlap = overlap_max - overlap_min

        # Якщо є перетин і він найбільший
        if overlap > max_overlap and overlap > 0:
            max_overlap = overlap
            best_cat = b

    # Якщо товар вилетів за межі (наприклад, надто дорогий), беремо найближчу по центру
    if max_overlap <= 0:
        mid_price = (calc_min + calc_max) / 2
        for b in boundaries:
            if b["start"] <= mid_price <= b["end"]:
                return b

    return best_cat


def _get_rank_value(option_name: str, options_rank: dict) -> int:
    """Парсить числовий ранг з 'top-1', 'top-5' тощо. Чим менше, тим краще."""
    rank_str = str(options_rank.get(option_name, "top-99"))
    if "top-+" in rank_str:
        return len(options_rank)  # Додаткові фічі кидаємо в кінець обов'язкових
    if "top-" in rank_str:
        try:
            return int(rank_str.split("-")[1])
        except:
            return 99
    return 99


def analyze_niche_segment(calculated_min: float, calculated_max: float, boundaries: list,
                          katalog_id: int, user_answers: dict, ai_weights: dict,
                          fetch_grid_callback, smart_match_callback, calculate_score_callback) -> dict:
    """
    Головна функція 13-го пункту. Визначає зону, парсить 24 конкуренти, знаходить лідера та робить % аналіз.
    """
    # 1. Визначаємо категорію
    target_category = get_inclusion_category(calculated_min, calculated_max, boundaries)

    # 2. Робимо точковий запит на товари (сторінка 0) в межах цієї категорії
    grid_result = fetch_grid_callback(katalog_id, target_category["start"], target_category["end"], 0)

    # Виправляємо проблему парсера: дістаємо масив зі словника {"products": [...]}
    competitors = grid_result.get("products", []) if isinstance(grid_result, dict) else grid_result

    # Очищуємо від пустих цін та дублікатів
    valid_competitors = []
    seen = set()
    for c in competitors:
        if c.get("price", 0) > 0 and c["name"] not in seen:
            seen.add(c["name"])
            valid_competitors.append(c)

    if not valid_competitors:
        return {"category": target_category, "main_competitor": None, "comparisons": []}

    # 3. Скоримо конкурентів, щоб знайти Головного Конкурента
    factors = ai_weights.get("factors", {})
    for cand in valid_competitors:
        p_features = [str(f) for f in cand.get("features", [])]
        p_name = cand.get("name", "")

        simulated_answers = {}
        for cat_name, cat_meta in factors.items():
            opts = list(cat_meta.get("options_rank", {}).keys())
            matched = smart_match_callback(opts, p_features, p_name)
            simulated_answers[cat_name] = matched

        cand["simulated_answers"] = simulated_answers
        cand["score"] = calculate_score_callback(simulated_answers, ai_weights)

    # Головний конкурент — це товар з найкращим балансом ціна/якість (максимальний бал у нашій полиці)
    main_competitor = max(valid_competitors, key=lambda x: x["score"])

    # 4. Бенчмаркінг характеристик (з % різницею)
    comparisons = []

    for cat_name, user_opt in user_answers.items():
        if user_opt in ["Не вказано / Інше", "інше"]:
            continue

        cat_meta = factors.get(cat_name, {})
        options_rank = cat_meta.get("options_rank", {})
        if not options_rank:
            continue

        max_possible_rank = len([k for k in options_rank.keys() if "інш" not in k.lower()])
        if max_possible_rank <= 1:
            max_possible_rank = 7  # Заглушка для уникнення ділення на 0

        # --- ВИПРАВЛЕННЯ: НОРМАЛІЗАЦІЯ ВВОДУ КОРИСТУВАЧА ---
        # Використовуємо smart_match_callback, щоб привести ввід користувача до "стандарту" ключів options_rank
        available_options = list(options_rank.keys())
        normalized_user_opt = smart_match_callback(available_options, [user_opt], "User Input")

        # Рахуємо ранг для нормалізованого значення
        our_rank = _get_rank_value(normalized_user_opt, options_rank)
        # ---------------------------------------------------

        mc_opt = main_competitor["simulated_answers"].get(cat_name, "Не вказано / Інше")
        mc_rank = _get_rank_value(mc_opt, options_rank)

        # Рахуємо середнє по ринку
        total_market_rank = 0
        valid_market_count = 0
        for cand in valid_competitors:
            c_opt = cand["simulated_answers"].get(cat_name, "Не вказано / Інше")
            c_rank = _get_rank_value(c_opt, options_rank)
            if c_rank < 99:  # Враховуємо тільки ті, що змогли розпізнати
                total_market_rank += c_rank
                valid_market_count += 1

        if valid_market_count == 0:
            continue

        avg_market_rank = total_market_rank / valid_market_count

        # Відсотки переваги
        vs_market_pct = ((avg_market_rank - our_rank) / max_possible_rank) * 100
        vs_mc_pct = ((mc_rank - our_rank) / max_possible_rank) * 100

        comparisons.append({
            "category": cat_name,
            "our_val": f"{user_opt} (Топ-{our_rank})",  # залишаємо оригінальний текст для звіту
            "mc_val": f"{mc_opt} (Топ-{mc_rank})",
            "avg_market_val": f"Топ-{avg_market_rank:.1f}",
            "vs_market_pct": vs_market_pct,
            "vs_mc_pct": vs_mc_pct
        })

    return {
        "category": target_category,
        "main_competitor": main_competitor,
        "comparisons": comparisons,
        "competitors_count": len(valid_competitors)
    }

def summarize_gap_analysis(comparisons: list, all_factors: list) -> dict:
    """
    Узагальнює результати порівняння з кроку 13 у структуру для звіту.
    """
    if not comparisons:
        return {"avg_vs_market": 0, "avg_vs_mc": 0, "better": [], "equal": [], "worse": [], "missing": all_factors}

    summary = {
        "avg_vs_market": sum(c["vs_market_pct"] for c in comparisons) / len(comparisons),
        "avg_vs_mc": sum(c["vs_mc_pct"] for c in comparisons) / len(comparisons),
        "better": [],
        "equal": [],
        "worse": [],
        "missing": []
    }

    # Групуємо характеристики
    compared_categories = {c["category"] for c in comparisons}
    summary["missing"] = [f for f in all_factors if f not in compared_categories]

    for c in comparisons:
        # Визначаємо статус за головним конкурентом
        if c["vs_mc_pct"] > 0.5: # Поріг 0.5% для врахування
            summary["better"].append(f"{c['category']} (+{c['vs_mc_pct']:.1f}%)")
        elif c["vs_mc_pct"] < -0.5:
            summary["worse"].append(f"{c['category']} ({c['vs_mc_pct']:.1f}%)")
        else:
            summary["equal"].append(f"{c['category']}")

    return summary
