"""
seller_runner.py
================
Тонкий адаптер між seller_test.py і веб-інтерфейсом.

НЕ дублює жодну бізнес-логіку з seller_test.py.
Просто імпортує ті самі функції і оркеструє їх виклик,
повертаючи дані у форматі, зручному для Streamlit-сесії.

Усі важкі обчислення залишаються в оригінальних модулях.
Додано повний трейсинг у консоль та файл global.log.
"""

"""
seller_runner.py
================
Сучасна Subprocess-архітектура (Міст).
Запускає робочу логіку в окремому ізольованому процесі,
гарантуючи відсутність помилок 'broken pipe' у Streamlit.
"""

import os
import sys
import json
import subprocess
import datetime

# Налаштування шляхів
current_dir = os.path.dirname(os.path.abspath(__file__))
core_dir = os.path.abspath(os.path.join(current_dir, '..'))
project_root = os.path.abspath(os.path.join(core_dir, '..'))
data_dir = os.path.join(project_root, 'data')
bridge_path = os.path.join(core_dir, "optimization", "cli_bridge.py")

if project_root not in sys.path: sys.path.append(project_root)
if core_dir not in sys.path: sys.path.append(core_dir)

# Імпортуємо тільки чисту математику, яка не чіпає Playwright
from seller.seller_analyzer import calculate_product_score, get_option_rank_string


def _log_runner(message: str, level: str = "INFO"):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] [{level}] [RUNNER] {message}", flush=True)


def _run_bridge_sync(cmd_args: list) -> dict:
    os.makedirs(data_dir, exist_ok=True)
    out_file = os.path.join(data_dir, "bridge_out.json")
    if os.path.exists(out_file):
        os.remove(out_file)

    cmd = [sys.executable, bridge_path] + cmd_args
    _log_runner(f"🚀 Запуск мосту: {' '.join(cmd)}")

    # Запускаємо процес без capture_output, щоб користувач бачив капчу в консолі
    process = subprocess.run(cmd)

    if os.path.exists(out_file):
        with open(out_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"status": "error", "message": "Брідж-скрипт не повернув результатів."}


def step_search(user_input: str) -> dict:
    _log_runner(f"🟢 [START step_search] Запит: '{user_input}'")
    return _run_bridge_sync(["search", "--query", user_input])


def step_prepare(chosen_katalog_id) -> dict:
    _log_runner(f"🟢 [START step_prepare] ID: {chosen_katalog_id}")
    return _run_bridge_sync(["prepare", "--id", str(chosen_katalog_id)])


# Опитування обчислюється локально (це безпечно, тут немає веб-запитів)
def get_question(quiz_questions: list, idx: int) -> dict | None:
    return quiz_questions[idx] if idx < len(quiz_questions) else None


def score_answer(q_name: str, chosen_val: str, ai_weights: dict) -> dict:
    try:
        factors = ai_weights.get("factors", {})
        imp = factors.get(q_name, {}).get("importance_coefficient", 0.05)
        others_imp = factors.get("Інші характеристики", {}).get("importance_coefficient", 0.05)

        micro_query = {q_name: chosen_val, "Інші характеристики": "Присутні"}
        percentage = calculate_product_score(micro_query, ai_weights)
        gained_points = max(0.0, (percentage / 100.0) * (imp + others_imp) - others_imp)
        rank_str = get_option_rank_string(q_name, chosen_val, ai_weights)

        return {"gained_points": gained_points, "rank_str": rank_str, "imp": imp}
    except Exception as e:
        return {"gained_points": 0.0, "rank_str": "Помилка обчислення", "imp": 0.0}


def finalize_quiz(quiz_questions: list, user_answers: dict, ai_weights: dict) -> float:
    return calculate_product_score(user_answers, ai_weights)


def step_final_processing(app: dict) -> dict:
    _log_runner("🟢 [START step_final_processing]")

    os.makedirs(data_dir, exist_ok=True)
    in_file = os.path.join(data_dir, "bridge_in.json")
    out_file = os.path.join(data_dir, "bridge_out.json")

    # Чистимо старі файли перед запуском
    if os.path.exists(out_file):
        os.remove(out_file)

    with open(in_file, "w", encoding="utf-8") as f:
        json.dump(app, f, ensure_ascii=False)

    cmd = [sys.executable, bridge_path, "final", "--infile", in_file]
    _log_runner(f"🚀 Запуск мосту (потоковий): {' '.join(cmd)}")

    # Використовуємо Popen з параметрами для уникнення UnicodeDecodeError
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding='utf-8',
        errors='replace',  # ЦЕ КРИТИЧНО: замінює нечитабельні байти на '?'
        bufsize=1  # Потоковий вивід (line-buffered)
    )

    # Зчитування виводу
    try:
        for line in iter(process.stdout.readline, ''):
            if line:
                print(line, end='', flush=True)  # Відзеркалюємо лог у головну консоль
                if "[PROGRESS]" in line:
                    yield {"progress": line.split("[PROGRESS]")[1].strip()}
    except Exception as e:
        _log_runner(f"Помилка при зчитуванні потоку: {e}", level="ERROR")
    finally:
        process.stdout.close()  # Закриваємо потік
        try:
            # Даємо процесу 1 секунду, щоб він міг спокійно закрити всі сокети
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            _log_runner("Процес довго закривався, примусове завершення...")
            process.kill()
            process.wait()

    # Читання результату
    if os.path.exists(out_file):
        try:
            with open(out_file, "r", encoding="utf-8") as f:
                yield json.load(f)
        except json.JSONDecodeError as e:
            _log_runner(f"Помилка парсингу JSON: {e}", level="ERROR")
            yield {"status": "error", "message": "Брідж повернув пошкоджений JSON."}
    else:
        yield {"status": "error", "message": "Брідж-скрипт фіналу не створив файл результату."}
