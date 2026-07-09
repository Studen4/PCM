import numpy as np


def _smart_match(options_list: list, p_features: list, p_name: str) -> str:
    """
    Локальний лінгвістичний стемер для модуля ціноутворення.
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


def analyze_market_pricing(scored_candidates: list, ai_matrix: dict) -> tuple:
    """
    [КРОК 11] Оцінка кореляційного впливу кожного фактору на ринкову ціну.
    """
    feature_impact = {}
    categories_data = ai_matrix.get("categories", {})

    all_prices = [cand["price"] for cand in scored_candidates if cand.get("price", 0) > 0]
    if not all_prices:
        return {}, 0.0, 0.0

    p_min = min(all_prices)
    p_avg = sum(all_prices) / len(all_prices)

    for cat_name, cat_meta in categories_data.items():
        importance = cat_meta.get("importance_coefficient", 0.05)
        options_rank = cat_meta.get("options_rank", {})

        option_prices = {opt: [] for opt in options_rank.keys()}

        for cand in scored_candidates:
            prod = cand.get("product", cand)
            p_features = [str(f) for f in prod.get("features", [])]
            p_name = prod.get("name", "")

            matched_opt = _smart_match(list(options_rank.keys()), p_features, p_name)

            if matched_opt != "Не вказано / Інше" and matched_opt in option_prices:
                option_prices[matched_opt].append(cand["price"])

        option_averages = {opt: sum(prs) / len(prs) for opt, prs in option_prices.items() if prs}

        def parse_rank(opt_name):
            rank_str = options_rank.get(opt_name, "top-99")
            if "top-" in str(rank_str):
                try:
                    return int(str(rank_str).split("-")[1])
                except:
                    return 99
            return 99

        sorted_opts_by_rank = sorted(options_rank.keys(), key=parse_rank, reverse=True)

        base_opt = None
        for opt in sorted_opts_by_rank:
            if opt in option_averages:
                base_opt = opt
                break

        p_base = option_averages[base_opt] if base_opt else p_min

        feature_impact[cat_name] = {
            "importance": importance,
            "base_option": base_opt or "інше",
            "base_price_X": p_base,
            "options": {},
            "unique_innovations": []
        }

        for opt in options_rank.keys():
            if opt in ["інші", "інше"]:
                continue

            if opt in option_averages:
                p_high = option_averages[opt]
                delta_p = p_high - p_base

                if delta_p > 0:
                    z_premium = delta_p * importance
                else:
                    delta_p = 0.0
                    z_premium = 0.0

                feature_impact[cat_name]["options"][opt] = {
                    "raw_delta": delta_p,
                    "premium_Z": z_premium,
                    "avg_market_price": p_high,
                    "is_innovation": False
                }
            else:
                feature_impact[cat_name]["unique_innovations"].append(opt)
                feature_impact[cat_name]["options"][opt] = {
                    "premium_Z": 0.0,
                    "is_innovation": True
                }

    return feature_impact, p_min, p_avg


def generate_price_recommendation(user_answers: dict, feature_impact: dict, p_min: float, p_avg: float,
                                  scored_candidates: list, target_score: float) -> dict:
    """
    [КРОК 12] Формування структури рекомендованої ціни на основі характеристик та ринкових якорів.
    """
    total_premium_Z = 0.0
    unique_innovations_detected = []
    applied_premiums = {}

    for cat_name, user_opt in user_answers.items():
        if cat_name in feature_impact:
            cat_data = feature_impact[cat_name]
            if user_opt in cat_data["options"]:
                opt_data = cat_data["options"][user_opt]
                if opt_data.get("is_innovation", False):
                    unique_innovations_detected.append(f"{cat_name}: {user_opt}")
                else:
                    z_val = opt_data["premium_Z"]
                    total_premium_Z += z_val
                    applied_premiums[cat_name] = {"option": user_opt, "z_val": z_val}

    # 1. Змінні вашої формули
    X_base = p_min + total_premium_Z
    X_max = p_avg + total_premium_Z
    Z_spread = X_max - X_base  # Це різниця між стелею і базою (фактично p_avg - p_min)

    if Z_spread <= 0:
        Z_spread = 1.0  # Захист від ділення на нуль

    # 2. Пошук якорів A1 та A2
    valid_cands = [c for c in scored_candidates if c.get("price", 0) > 0 and c.get("score", 0) > 0]

    a1_anchor = None
    a2_anchor = None

    if valid_cands:
        # А1: Схожий за оцінкою (найближчий бал)
        a1_anchor = min(valid_cands, key=lambda c: abs(c.get('score', 0) - target_score))

        # А2: Схожий за характеристиками (максимум збігів)
        def count_matches(cand):
            matches = 0
            # Спробуємо знайти розпізнані параметри, або беремо сирі
            c_ans = cand.get("product", {}).get("recognized_specs", {})
            if not c_ans:
                c_ans = cand.get("simulated_answers", {})
            for k, v in user_answers.items():
                if v != "Не вказано / Інше" and c_ans.get(k) == v:
                    matches += 1
            return matches

        a2_candidate = max(valid_cands, key=count_matches)
        # Використовуємо А2 тільки якщо це інший товар
        if a2_candidate and a1_anchor and a2_candidate['product']['name'] != a1_anchor['product']['name']:
            a2_anchor = a2_candidate

    a1_price = a1_anchor["price"] if a1_anchor else 0.0
    a2_price = a2_anchor["price"] if a2_anchor else 0.0

    # 3. Ваша формула нормалізації: Z(kf) = ((A1/Z + A2/Z)) / A(n)
    sum_ratios = 0.0
    a_n = 0

    if a1_anchor:
        sum_ratios += (a1_price / Z_spread)
        a_n += 1
    if a2_anchor:
        sum_ratios += (a2_price / Z_spread)
        a_n += 1

    if a_n > 0:
        Z_kf = sum_ratios / a_n
    else:
        Z_kf = 1.0  # Якщо якорів немає

    # Фінальний розрахунок: X + (Z_kf * Z)
    final_max_price = X_base + (Z_spread * Z_kf)

    return {
        "X": X_base,
        "X_plus_Z": X_max,
        "Z": Z_spread,
        "A1": a1_anchor,
        "A2": a2_anchor,
        "Z_kf": Z_kf,
        "final_min": X_base,
        "final_max": final_max_price,
        "total_premium": total_premium_Z,
        "innovations": unique_innovations_detected,
        "applied_premiums": applied_premiums
    }
