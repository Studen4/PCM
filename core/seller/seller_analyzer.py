def prepare_quiz_questions(sidebar_filters: dict, ai_weights: dict) -> list:
    questions = []
    factors = ai_weights.get("factors", {})

    for f_name, options in sidebar_filters.items():
        f_name_clean = f_name.strip()
        f_name_lower = f_name_clean.lower()

        # 1. ГЛОБАЛЬНЕ ІГНОРУВАННЯ (за ключовими словами)
        if any(keyword in f_name_lower for keyword in ["ціна", "колір"]):
            continue
        if not options:
            continue

        # 2. СПЕЦІАЛЬНА ОБРОБКА ВИРОБНИКІВ
        # Тільки якщо це назва саме "Виробники" (ігноруємо "Виробник перемикачів" тощо)
        if f_name_lower == "виробники":
            questions.append({
                "type": "input",
                "name": f_name_clean,
                "display_label": "(Основне)",
                "options": []
            })
            continue

        # 3. ЛОГІКА КАТЕГОРИЗАЦІЇ (Main vs Additional)
        # Умова для (Основне): категорія є в аналізі ШІ ТА це не "Інші характеристики"
        is_in_ai = f_name_clean in factors
        is_others = (f_name_clean == "Інші характеристики")

        is_main = is_in_ai and not is_others
        display_label = "(Основне)" if is_main else "(Додаткове)"

        # Отримуємо метадані
        meta = factors.get(f_name_clean, {"importance_coefficient": 0.05})

        questions.append({
            "type": "choice",
            "name": f_name_clean,
            "options": options,
            "display_label": display_label,
            "meta": meta
        })

    return questions


def calculate_product_score(user_answers: dict, ai_weights: dict) -> float:
    """
    Динамічний розрахунок оцінки товару (0.0 - 100.0) на основі відповідей користувача
    та матриці вагових коефіцієнтів від ШІ.
    """
    factors = ai_weights.get("factors") or ai_weights.get("categories") or {}

    total_score = 0.0
    max_possible_score = 0.0

    # 1. Рахуємо суму коефіцієнтів категорій, які реально беруть участь в опитуванні
    for category in user_answers.keys():
        meta = factors.get(category, {"importance_coefficient": 0.05})
        max_possible_score += meta.get("importance_coefficient", 0.05)

    # 2. Розрахунок набраних балів по кожній категорії
    for category, answer in user_answers.items():
        meta = factors.get(category, {"importance_coefficient": 0.05, "options_rank": {}})
        imp = meta.get("importance_coefficient", 0.05)
        options_rank = meta.get("options_rank", {})

        # Якщо відповідь користувача пуста або пропущена — 0 балів за параметр
        if answer == "Не вказано / Інше" or not answer:
            continue

        # КЕЙС А: Абстрактна категорія "Інші характеристики" (Все або нічого)
        if category == "Інші характеристики":
            total_score += imp
            continue

        # КЕЙС Б: Текстове введення виробника (Виробники)
        if category == "Виробники":
            user_brand = str(answer).strip().lower()
            matched_rank_str = None

            for brand_key, rank_val in options_rank.items():
                if brand_key.lower() == user_brand:
                    matched_rank_str = rank_val
                    break

            if not matched_rank_str:
                for brand_key, rank_val in options_rank.items():
                    if "інш" in brand_key.lower() or brand_key.lower() == "n/a":
                        matched_rank_str = rank_val
                        break

            if matched_rank_str:
                try:
                    k = int(matched_rank_str.split("-")[1])
                    max_n = max([int(v.split("-")[1]) for v in options_rank.values() if "-" in v] or [1])
                    step = imp / max_n
                    score_for_brand = imp - (k - 1) * step
                    total_score += max(0.0, score_for_brand)
                except (ValueError, IndexError):
                    total_score += imp if "top-1" in matched_rank_str else (imp * 0.5)
            else:
                total_score += imp * 0.5
            continue

        # КЕЙС В: Стандартні вибори (розумний пошук збігів)
        if options_rank:
            rank_str = options_rank.get(answer)

            # На випадок розбіжностей (наприклад, ШІ написав "75%", а на сайті "75% (компактні...)")
            if not rank_str:
                for opt_key, r_val in options_rank.items():
                    # Перевіряємо взаємне входження рядків один в одного
                    if opt_key.lower() == str(answer).lower() or \
                       (opt_key.lower() in str(answer).lower()) or \
                       (str(answer).lower() in opt_key.lower()):
                        rank_str = r_val
                        break

            # Фолбек на варіант "інші"
            if not rank_str:
                for opt_key, r_val in options_rank.items():
                    if "інш" in opt_key.lower():
                        rank_str = r_val
                        break

            if rank_str:
                if "top-+" in rank_str:
                    total_score += imp
                    continue

                try:
                    k = int(rank_str.split("-")[1])
                    max_n = 1
                    for r_val in options_rank.values():
                        if "-" in r_val and "top-+" not in r_val:
                            try:
                                num = int(r_val.split("-")[1])
                                if num > max_n:
                                    max_n = num
                            except ValueError:
                                pass

                    step = imp / max_n
                    score_for_cat = imp - (k - 1) * step
                    total_score += max(0.0, score_for_cat)
                except (ValueError, IndexError):
                    total_score += imp
            else:
                total_score += imp * 0.5
        else:
            # Якщо мапа рейтингів відсутня взагалі (для додаткових параметрів)
            total_score += imp

    return (total_score / max_possible_score * 100) if max_possible_score > 0 else 0.0


def get_option_rank_string(category: str, answer: str, ai_weights: dict) -> str:
    """Повертає рядок рангу (напр. 'top-1'), який ШІ дав для цієї відповіді."""
    factors = ai_weights.get("factors") or ai_weights.get("categories") or {}
    options_rank = factors.get(category, {}).get("options_rank", {})

    if not answer or answer == "Не вказано / Інше":
        return "Не вказано"

    # Шукаємо точний збіг або за підрядком (для виробників та фолбеків)
    for key, rank in options_rank.items():
        if key.lower() == str(answer).lower() or (category != "Виробники" and key.lower() in str(answer).lower()):
            return rank

    # Шукаємо фолбек на "інші"
    for key, rank in options_rank.items():
        if "інш" in key.lower() or key.lower() == "n/a":
            return rank

    return "top-N (Не знайдено)"
