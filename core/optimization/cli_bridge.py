"""
cli_bridge.py
=============
Ізольований системний процес для безпечного запуску Playwright.
Виконує важку логіку та повертає результати у форматі JSON.
"""

import sys
# Примусово встановлюємо UTF-8 для stdout/stderr, щоб уникнути UnicodeEncodeError
sys.stdout.reconfigure(encoding='utf-8')

import argparse
import json
import os
import time

# Налаштування шляхів
current_dir = os.path.dirname(os.path.abspath(__file__))
core_dir = os.path.abspath(os.path.join(current_dir, '..'))
project_root = os.path.abspath(os.path.join(core_dir, '..'))
data_dir = os.path.join(project_root, 'data')

if project_root not in sys.path:
    sys.path.insert(0, project_root)
if core_dir not in sys.path:
    sys.path.insert(0, core_dir)

# Вимикаємо демона, щоб використовувати твій працюючий локальний Playwright
os.environ["USE_DAEMON"] = "False"

# Імпорт робочої бізнес-логіки
from scraper.ekatalog_parser import parse_category_page, parse_compact_grid
from seller.seller_input_normalizer import normalize_seller_input
from seller.seller_ai_analyzer import analyze_product_filters
from seller.seller_analyzer import prepare_quiz_questions, calculate_product_score
from seller.seller_pricing_analyzer import generate_11_points, fetch_market_matrix, find_ideal_product
from seller.seller_pricing import analyze_market_pricing, generate_price_recommendation, _smart_match
from seller.seller_recommendation_analyzer import analyze_niche_segment, summarize_gap_analysis
from seller.seller_ai_recommendation import analyze_business_strategy

# Безпечний імпорт модуля зон
try:
    import importlib.util

    spec = importlib.util.spec_from_file_location("global_zone_checker",
                                                  os.path.join(core_dir, "global", "global_zone_checker.py"))
    gzc = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gzc)
    calculate_price_categories = gzc.calculate_price_categories
except Exception as e:
    print(f"Помилка імпорту global_zone_checker: {e}")
    sys.exit(1)

# Безпечний імпорт зарплати
try:
    from scraper.salary_parser import get_normalized_salary
except ImportError:
    def get_normalized_salary():
        return 18500.0


def _save_output(data):
    os.makedirs(data_dir, exist_ok=True)
    out_file = os.path.join(data_dir, "bridge_out.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


def handle_search(query):
    try:
        result = normalize_seller_input(query)
        # Форматуємо під UI
        if result.get("status") == "ambiguous" and "categories" in result:
            _save_output({"status": "ok", "categories": result["categories"]})
        elif result.get("status") == "ok" and result.get("categories"):
            _save_output({"status": "ok", "categories": result["categories"]})
        elif "category_id" in result:
            cat_name = result.get("category_name") or query
            _save_output({"status": "ok", "categories": {cat_name: result["category_id"]}})
        elif result.get("categories"):
            _save_output({"status": "ok", "categories": result["categories"]})
        else:
            _save_output({"status": "error", "message": "Категорії не знайдено."})
    except Exception as e:
        _save_output({"status": "error", "message": str(e)})


def handle_prepare(katalog_id):
    try:
        # 1. Парсинг ринку
        market_data = parse_category_page(katalog_id)

        # --- БЕЗПЕЧНЕ ЗАКРИТТЯ ---
        try:
            os.system("taskkill /F /IM node.exe /T >nul 2>&1")
        except:
            pass

        # Перевірка
        if not market_data or not market_data.get("sidebar_filters"):
            print(f"[ERROR] Парсинг не повернув фільтрів для ID {katalog_id}", flush=True)
            _save_output({"status": "error", "message": "Не вдалося отримати дані ринку."})
            return

        # 2. Розрахунок
        sidebar_filters = market_data.get("sidebar_filters", {})
        salary = get_normalized_salary()
        p_min = market_data['price_pool']['min'] or 1.0
        p_max = market_data['price_pool']['max'] or 26200.0
        boundaries, _, _, _ = calculate_price_categories(salary, p_min, p_max)

        # 3. ЛОГІКА AI ANALYST
        cache_path = os.path.join(project_root, "core", "seller", "ai_answer_debug.json")
        print(f"\n[КРОК 6] Аналіз, отримано фільтрів: {len(sidebar_filters)}", flush=True)
        print(f"[DEBUG] ПОВНИЙ ШЛЯХ до файлу: {os.path.abspath(cache_path)}", flush=True)

        if os.path.exists(cache_path):
            with open(cache_path, "r", encoding="utf-8") as f:
                ai_result = json.load(f)
        else:
            ai_result = analyze_product_filters(sidebar_filters, mode="template")
            if ai_result:
                with open(cache_path, "w", encoding="utf-8") as f:
                    json.dump(ai_result, f, ensure_ascii=False, indent=4)
            else:
                ai_result = {"categories": {}}

        ai_weights = {"factors": ai_result.get("categories", {})}

        # --- ЖОРСТКИЙ ДЕБАГ ---
        print(f"[DEBUG] Ключі в sidebar_filters (з сайту): {list(sidebar_filters.keys())}", flush=True)
        print(f"[DEBUG] Ключі в ai_weights (з кешу): {list(ai_weights['factors'].keys())}", flush=True)

        # 4. Підготовка квізу
        quiz_questions = prepare_quiz_questions(sidebar_filters, ai_weights)

        print(f"[DEBUG] Сгенеровано питань: {len(quiz_questions)}", flush=True)

        _save_output({
            "status": "ok",
            "market_data": market_data,
            "boundaries": boundaries,
            "ai_weights": ai_weights,
            "quiz_questions": quiz_questions
        })

    except Exception as e:
        print(f"[CRITICAL] Помилка в handle_prepare: {e}", flush=True)
        _save_output({"status": "error", "message": str(e)})


def handle_final(in_file):
    try:
        with open(in_file, "r", encoding="utf-8") as f:
            app = json.load(f)

        katalog_id = app.get("chosen_katalog_id")
        P_min = app["market_data"]["price_pool"]["min"] or 1.0

        print("[PROGRESS] Крок 9 — Збір матриці товарів...", flush=True)
        eleven_pts = generate_11_points(app["boundaries"], P_min)
        matrix_raw = fetch_market_matrix(eleven_pts, katalog_id)

        seen, unique_pool = set(), []
        for p in (matrix_raw or []):
            if isinstance(p, dict) and "name" in p and p["name"] not in seen:
                seen.add(p["name"])
                unique_pool.append(p)
        print(f"[PROGRESS] Крок 9 — Зібрано {len(unique_pool)} унікальних товарів [OK]", flush=True)

        ideal_item, ideal_score = find_ideal_product(unique_pool, app["ai_weights"], calculate_product_score)
        print(f"[PROGRESS] Крок 10 — Як еталон визначено: «{ideal_item.get('name', '?')}» [OK]", flush=True)

        scored_candidates = []
        for p in unique_pool:
            score = p.get("score")
            sim_ans = p.get("simulated_answers") or {}
            if not sim_ans:
                for cat_name, cat_meta in app["ai_weights"]["factors"].items():
                    sim_ans[cat_name] = _smart_match(list(cat_meta.get("options_rank", {}).keys()),
                                                     [str(f) for f in p.get("features", [])], p.get("name", ""))
                p["simulated_answers"] = sim_ans
            if score is None:
                score = calculate_product_score(sim_ans, app["ai_weights"])
                p["score"] = score
            scored_candidates.append(
                {"price": p.get("price", 0), "score": score, "simulated_answers": sim_ans, "product": p})

        ai_matrix_fmt = {"categories": app["ai_weights"]["factors"]}
        feature_impact, p_min_mkt, p_avg_mkt = analyze_market_pricing(scored_candidates, ai_matrix_fmt)
        print("[PROGRESS] Крок 11 — Вплив факторів прораховано [OK]", flush=True)

        pricing_results = generate_price_recommendation(app["user_answers"], feature_impact, p_min_mkt, p_avg_mkt,
                                                        scored_candidates, app["product_score"])
        print(f"[PROGRESS] Крок 12 — Сформована ціна: {pricing_results['final_min']:,.0f}–{pricing_results['final_max']:,.0f} грн [OK]", flush=True)

        niche_analysis = analyze_niche_segment(pricing_results['final_min'], pricing_results['final_max'],
                                               app["boundaries"], katalog_id, app["user_answers"], app["ai_weights"],
                                               parse_compact_grid, _smart_match, calculate_product_score)
        main_comp = niche_analysis["main_competitor"]
        print(f"[PROGRESS] Крок 13 — Головний конкурент: «{main_comp.get('name', '?') if main_comp else 'не знайдено'}» [OK]", flush=True)

        gap_summary = summarize_gap_analysis(niche_analysis["comparisons"], list(app["ai_weights"]["factors"].keys()))
        print("[PROGRESS] Крок 14 — Аналіз ринку завершено [OK]", flush=True)

        ai_response = analyze_business_strategy(app["user_answers"],
                                                main_comp.get("name", "Unknown") if main_comp else "Unknown",
                                                f"{niche_analysis['category']['start']} - {niche_analysis['category']['end']}",
                                                gap_summary)
        ai_advice = ai_response.get('report', str(list(ai_response.values())[0])) if isinstance(ai_response, dict) else str(ai_response)
        print("[PROGRESS] Крок 15 — Бізнес-стратегію згенеровано [OK]", flush=True)

        _save_output({
            "status": "done",
            "ideal_score": ideal_score,
            "feature_impact": feature_impact,
            "pricing_results": pricing_results,
            "current_category_bounds": niche_analysis["category"],
            "current_category_name": niche_analysis["category"]["category"],
            "main_comp": main_comp,
            "gap_summary": gap_summary,
            "ai_advice": ai_advice,
        })

    except Exception as e:
        print(f"[ERROR] Критична помилка у фінальній обробці: {e}", flush=True)
        _save_output({"status": "error", "message": str(e)})

    finally:
        # Гарантоване закриття браузера
        print("[PROGRESS] Завершення сесії, очищення ресурсів браузера...", flush=True)
        try:
            from scraper.ekatalog_parser_new import close_browser
            close_browser()
        except ImportError:
            pass
        except Exception as e:
            print(f"[WARNING] Помилка при закритті браузера: {e}", flush=True)

        # КРИТИЧНО: Пауза перед виходом для flush виводу та закриття сокетів
        time.sleep(0.5)
        print("[PROGRESS] Ресурси очищено. Вихід.", flush=True)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("step", choices=["search", "prepare", "final"])
    parser.add_argument("--query", type=str, default="")
    parser.add_argument("--id", type=int, default=0)
    parser.add_argument("--infile", type=str, default="")
    args = parser.parse_args()

    if args.step == "search":
        handle_search(args.query)
    elif args.step == "prepare":
        handle_prepare(args.id)
    elif args.step == "final":
        handle_final(args.infile)
