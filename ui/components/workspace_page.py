"""
workspace_page.py
=================
Чистий UI-шар. Жодної бізнес-логіки тут немає —
все делегується в seller_runner.py, який, у свою чергу,
використовує ті самі функції що й seller_test.py.

Стани (seller_stage):
  waiting_input       → користувач вводить назву товару
  category_select     → показуємо знайдені категорії кнопками
  captcha_verification→ потрібна капча від e-katalog або демон офлайн
  pre_quiz_processing → збираємо ринкові дані (кроки 4-7)
  quiz                → покрокове опитування (крок 8)
  final_processing    → важкі обчислення (кроки 9-15)
  results             → показуємо результати (крок 16)
"""

import os
import base64
import json
from datetime import datetime
import markdown
import streamlit as st

# Адаптер — єдина точка входу до бізнес-логіки
import core.seller.seller_runner as runner


# ══════════════════════════════════════════════════════════════════════════
# ХЕЛПЕРИ
# ══════════════════════════════════════════════════════════════════════════

def _get_b64(path: str) -> str:
    if os.path.exists(path):
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    return ""

def _on_submit():
    text = st.session_state.get("ws_input", "").strip()
    if not text:
        return
    st.session_state.app_state["search_query"] = text

    with st.spinner("Шукаємо категорії..."):
        result = runner.step_search(text)

    if result["status"] == "ok":
        st.session_state.app_state["found_categories"] = result["categories"]
        st.session_state.show_all_categories = False
        st.session_state.seller_stage = "category_select"
        st.session_state.trigger_rerun = True  # Встановлюємо прапорець
    elif result.get("status") == "captcha" or "captcha" in str(result.get("message", "")).lower():
        st.session_state.captcha_data = {
            "return_stage": "waiting_input",
            "message": result.get("message", "captcha_needed")
        }
        st.session_state.seller_stage = "captcha_verification"
        st.session_state.trigger_rerun = True  # Встановлюємо прапорець
    else:
        st.warning(f"❌ {result['message']}")

def _reset_session():
    """Повністю скидає стан воркспейсу для нового аналізу."""
    for key in ("seller_stage", "app_state", "current_question_idx",
                "show_all_categories", "rating_submitted", "captcha_data",
                "processing_log", "processing_done"):
        st.session_state.pop(key, None)


def _save_rating(stars: int):
    project_root = st.session_state.get("_project_root", ".")
    file_path = os.path.join(project_root, "data", "rate_results.json")
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    data = []
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError:
            pass
    data.append({
        "User": st.session_state.get("user_role", "Seller"),
        "Rating": stars + 1,
        "Date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    })
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


def _console_log(steps, done=False):
    """Генерує HTML консолі прогресу."""
    rows = "".join(f"<div class='sh-row'>&#x2705; {s}</div>" for s in steps)
    spinner = "" if done else "<div class='sh-row sh-blink'>&#x23F3; Обробка даних...</div>"
    return (
        "<style>"
        ".sh-console{background:#0d1117;border:1px solid #30363d;border-radius:8px;"
        "padding:16px 20px;font-family:'Courier New',monospace;font-size:13px;"
        "color:#3fb950;line-height:1.8;margin-bottom:20px;}"
        ".sh-row{margin:0;}"
        ".sh-blink{color:#f0a030;animation:blink 1.4s ease-in-out infinite;}"
        "@keyframes blink{50%{opacity:0.2;}}"
        "</style>"
        f"<div class='sh-console'>{rows}{spinner}</div>"
    )


# ══════════════════════════════════════════════════════════════════════════
# ГОЛОВНА ФУНКЦІЯ
# ══════════════════════════════════════════════════════════════════════════

def render_workspace_page(navigate_to):

    if st.session_state.get("trigger_rerun", False):
        st.session_state.trigger_rerun = False
        st.rerun()

    if st.session_state.get("workspace_mode") != "seller":
        st.warning("Наразі доступний тільки режим - Seller. Інші режими в розробці!")
        # Тут можна додати логіку для іншого режиму
        st.stop()

    # Ініціалізація project_root
    if "_project_root" not in st.session_state:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        st.session_state._project_root = os.path.abspath(
            os.path.join(current_dir, '..', '..')
        )
    project_root = st.session_state._project_root

    # Ініціалізація стану
    if "seller_stage" not in st.session_state:
        st.session_state.seller_stage = "waiting_input"
    if "app_state" not in st.session_state:
        st.session_state.app_state = {
            "search_query": "", "market_data": {}, "boundaries": [],
            "ai_weights": {}, "quiz_questions": [], "user_answers": {},
            "product_score": 0.0, "chosen_cat_name": "",
            "chosen_katalog_id": None,
        }
    if "current_question_idx" not in st.session_state:
        st.session_state.current_question_idx = 0
    if "show_all_categories" not in st.session_state:
        st.session_state.show_all_categories = False
    if "rating_submitted" not in st.session_state:
        st.session_state.rating_submitted = False
    if "captcha_data" not in st.session_state:
        st.session_state.captcha_data = {}
    if "processing_log" not in st.session_state:
        st.session_state.processing_log = []
    if "processing_done" not in st.session_state:
        st.session_state.processing_done = False

    # Ресурси
    assets  = os.path.join(project_root, "ui", "assets")
    role    = st.session_state.get("user_role", "guest")
    av_path = os.path.join(assets, f"{role}.png")
    if not os.path.exists(av_path):
        av_path = os.path.join(assets, "user.png")

    b64 = {
        "terms":    _get_b64(os.path.join(assets, "terms.png")),
        "settings": _get_b64(os.path.join(assets, "settings.png")),
        "avatar":   _get_b64(av_path),
        "send":     _get_b64(os.path.join(assets, "send_button.png")),
    }

    # Глобальні стилі
    st.markdown("""
<style>
.navbar-right{display:flex;align-items:center;justify-content:flex-end;
gap:14px;width:100%;height:55px;}
.nav-icon{width:46px;height:46px;border-radius:50%;border:2px solid #e5e7eb;
background:#fff;display:flex;align-items:center;justify-content:center;
overflow:hidden;transition:transform .2s;cursor:pointer;}
.nav-icon:hover{transform:scale(1.05);border-color:#00b894;}
.nav-icon img{width:100%;height:100%;object-fit:cover;}
.nav-logout{font-size:.95rem;font-weight:500;color:#4b5563;background:transparent;
border:1px solid #e5e7eb;border-radius:6px;padding:8px 18px;text-decoration:none;}
.nav-logout:hover{border-color:#00b894;color:#00b894;}
.ml-block{background:#f0fdf4;border-left:5px solid #22c55e;padding:20px;
border-radius:8px;margin-bottom:20px;color:#166534;}
.ai-block{background:#f8fafc;border-left:5px solid #3b82f6;padding:20px;
border-radius:8px;color:#1e293b;}
.captcha-box{border:2px dashed #ef4444;background:#fef2f2;
padding:20px;border-radius:8px;margin:20px 0;}
</style>
""", unsafe_allow_html=True)

    # Sidebar
    mode = st.session_state.get("workspace_mode", "seller")
    with st.sidebar:
        mode_img = os.path.join(assets, f"{mode}_mode.png")
        if os.path.exists(mode_img):
            st.markdown(
                f'<div style="border:2px solid #e5e7eb;border-radius:8px;padding:10px;'
                f'background:#fff;margin-bottom:20px;display:flex;justify-content:center;">'
                f'<img src="data:image/png;base64,{_get_b64(mode_img)}" style="width:100%;"></div>',
                unsafe_allow_html=True,
            )
        if st.button("+ New Analysis Chat", use_container_width=True, type="primary"):
            _reset_session()
            st.rerun()
        st.markdown(
            "<br><h5 style='text-align:center;color:#6b7280;'>Recent Chats</h5>",
            unsafe_allow_html=True,
        )
        st.write("📄 Gaming Keyboard Check")

    # Navbar
    c1, c2 = st.columns([5, 4])
    with c1:
        st.markdown(
            "<h2 style='margin:0;color:#00b894;font-weight:bold;'>Price Control Model</h2>",
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            f'<div class="navbar-right">'
            f'<a href="?action=terms"    class="nav-icon">'
            f'<img src="data:image/png;base64,{b64["terms"]}"></a>'
            f'<a href="?action=settings" class="nav-icon">'
            f'<img src="data:image/png;base64,{b64["settings"]}"></a>'
            f'<div class="nav-icon"><img src="data:image/png;base64,{b64["avatar"]}"></div>'
            f'<a href="?action=logout"   class="nav-logout">Log out</a>'
            f'</div>',
            unsafe_allow_html=True,
        )

    st.markdown(
        "<hr style='margin-top:10px;margin-bottom:25px;border:1px solid #e5e7eb;'>",
        unsafe_allow_html=True,
    )

    # ══════════════════════════════════════════════════════════════════════
    # РОБОЧА ЗОНА
    # ══════════════════════════════════════════════════════════════════════

    stage = st.session_state.seller_stage

    # ── 1: Очікування вводу ──────────────────────────────────────────────
    if stage == "waiting_input":
        st.markdown(
            "<h3 style='text-align:center;color:#9ca3af;padding:100px 0;'>"
            "Введіть назву або категорію вашого товару знизу для аналізу ніші...</h3>",
            unsafe_allow_html=True,
        )

    # ── 2: Вибір категорії ────────────────────────────────────────────────
    elif stage == "category_select":
        cats_dict = st.session_state.app_state.get("found_categories", {})
        cat_names = list(cats_dict.keys())

        st.markdown("### 🗂️ Знайдено категорії. Оберіть вашу:")

        limit = len(cat_names) if st.session_state.show_all_categories else 10
        for cat in cat_names[:limit]:
            if st.button(cat, key=f"cat_{cat}", use_container_width=True):
                app = st.session_state.app_state
                app["chosen_cat_name"]   = cat
                app["chosen_katalog_id"] = cats_dict[cat]
                app["user_answers"]      = {}
                st.session_state.show_all_categories  = False
                st.session_state.current_question_idx = 0
                st.session_state.processing_log       = []
                st.session_state.processing_done      = False
                st.session_state.seller_stage = "pre_quiz_processing"
                st.rerun()

        if not st.session_state.show_all_categories and len(cat_names) > 10:
            cols = st.columns([1, 2, 1])
            with cols[1]:
                if st.button("Показати всі категорії", key="show_all", use_container_width=True):
                    st.session_state.show_all_categories = True
                    st.rerun()

    # ── ОНОВЛЕНА КАПЧА / ДЕМОН ОФЛАЙН ─────────────────────────────────────
    elif stage == "captcha_verification":
        st.markdown("### 🔒 Потрібна верифікація сесії (Cloudflare)")
        st.warning("E-Katalog вимагає пройти перевірку безпеки, або ваш фоновий Демон не має актуальних кукі.")

        st.markdown("""
            **Інструкція для розблокування програми:**
            1. **Запустіть скрипт вирішення капчі:** Відкрийте нове вікно терміналу (поруч із запущеним Streamlit) і виконайте команду:
               ```bash
               python core/optimization/solve_captcha.py
               ```
            2. **Пройдіть перевірку:** У вікні повноцінного браузера Chrome, що відкриється, поставте галочку Cloudflare (якщо вона є) та зачекайте завантаження головної сторінки.
            3. **Збережіть кукі:** Поверніться в термінал, де запущено `solve_captcha.py`, і натисніть **ENTER**. Вікно закриється, а сесія збережеться.
            4. **ПЕРЕЗАПУСТІТЬ ДЕМОНА:** Щоб фоновий Демон підтягнув новий файл `ekatalog_session.json`, обов'язково перезапустіть його процес у консолі.
            5. **Повторіть запит:** Після цього натисніть кнопку нижче — система автоматично повторить пошук для вашого слова!
            """)

        if st.button("🔄 Я пройшов капчу та перезапустив Демона (Повторити запит)", type="primary", use_container_width=True):
            return_stage = st.session_state.captcha_data.get("return_stage", "pre_quiz_processing")

            # Якщо капча збила нас на самому початку (крок пошуку слова)
            if return_stage == "waiting_input":
                text = st.session_state.app_state.get("search_query", "")
                if text:
                    with st.spinner("Повторна спроба пошуку категорій..."):
                        result = runner.step_search(text)

                    if result["status"] == "ok":
                        st.session_state.app_state["found_categories"] = result["categories"]
                        st.session_state.show_all_categories = False
                        st.session_state.seller_stage = "category_select"
                        st.session_state.captcha_data = {}
                        st.rerun()
                    else:
                        st.error(f"❌ Помилка: Демон все ще заблокований або повертає помилку: {result.get('message')}")
                        st.stop()
                else:
                    st.session_state.seller_stage = "waiting_input"
                    st.session_state.captcha_data = {}
                    st.rerun()
            else:
                # Якщо впало на етапі збору даних про нішу
                st.session_state.seller_stage = return_stage
                st.session_state.captcha_data = {}
                st.rerun()

    # ── 3: Обробка перед опитуванням ──────────────────────────────────────
    elif stage == "pre_quiz_processing":
        cat_name   = st.session_state.app_state["chosen_cat_name"]
        katalog_id = st.session_state.app_state["chosen_katalog_id"]

        log_ph = st.empty()
        steps  = [
            "Крок 1-2 — Пошук та normalізація запиту",
            f"Крок 3 — Категорію \"{cat_name}\" обрано",
        ]
        log_ph.markdown(_console_log(steps), unsafe_allow_html=True)

        with st.spinner("Збираємо ринкові дані..."):
            result = runner.step_prepare(katalog_id)

        if result["status"] == "captcha" or "captcha" in str(result.get("message", "")).lower():
            st.session_state.captcha_data = {
                "img": result.get("img"),
                "return_stage": "pre_quiz_processing",
                "attempt": st.session_state.captcha_data.get("attempt", 0) + 1,
                "last_error": result.get("error"),
            }
            st.session_state.seller_stage = "captcha_verification"
            st.rerun()

        if result["status"] == "error":
            st.error(f"❌ {result['message']}")
            if st.button("Спробувати інший запит", key="retry_prep"):
                _reset_session()
                st.rerun()
            st.stop()

        app = st.session_state.app_state
        app["market_data"]    = result["market_data"]
        app["boundaries"]     = result["boundaries"]
        app["ai_weights"]     = result["ai_weights"]
        app["quiz_questions"] = result["quiz_questions"]

        n_q = len(result["quiz_questions"])
        steps += [
            "Крок 4 — Ринкові дані отримано",
            "Крок 5 — Цінові зони розраховано",
            "Крок 6 — AI-аналіз фільтрів завершено",
            f"Крок 7 — Згенеровано {n_q} питань",
        ]
        log_ph.markdown(_console_log(steps, done=True), unsafe_allow_html=True)
        st.success("Чудово! Починаємо аналіз вашого товару.")

        import time; time.sleep(0.8)
        st.session_state.captcha_data = {}
        st.session_state.seller_stage = "quiz"
        st.rerun()

    # ── 4: Опитування ─────────────────────────────────────────────────────
    elif stage == "quiz":
        questions = st.session_state.app_state.get("quiz_questions", [])

        if not questions:
            st.error("Список питань порожній — перевірте логіку генерації.")
            if st.button("Почати заново", key="quiz_retry"):
                _reset_session()
                st.rerun()
            st.stop()

        idx   = st.session_state.current_question_idx
        total = len(questions)

        if idx < total:
            q      = questions[idx]
            q_name = q["name"]
            label  = q.get("display_label", "")

            st.progress(idx / total, text=f"Питання {idx + 1} з {total}")
            st.markdown(f"### 🤖 PCM запитує ({idx + 1}/{total})")
            st.info(f"Вкажіть характеристику: **{q_name}** {label}")

            if q["type"] == "input":
                val = st.text_input("Введіть значення:", key=f"iq_{idx}")
                if st.button("Підтвердити", type="primary", key=f"ib_{idx}"):
                    answer = val.strip() if val.strip() else "Не вказано / Інше"
                    st.session_state.app_state["user_answers"][q_name] = answer
                    info = runner.score_answer(
                        q_name, answer, st.session_state.app_state["ai_weights"]
                    )
                    st.toast(
                        f"{q_name}: {answer} | {info['rank_str']} | +{info['gained_points']:.3f}",
                        icon="📊",
                    )
                    st.session_state.current_question_idx += 1
                    st.rerun()
            else:
                opts   = ["Не вказано / Інше"] + q.get("options", [])
                choice = st.radio("Оберіть варіант:", opts, key=f"rq_{idx}")
                if st.button("Підтвердити", type="primary", key=f"rb_{idx}"):
                    st.session_state.app_state["user_answers"][q_name] = choice
                    info = runner.score_answer(
                        q_name, choice, st.session_state.app_state["ai_weights"]
                    )
                    st.toast(
                        f"{q_name}: {choice} | {info['rank_str']} | +{info['gained_points']:.3f}",
                        icon="📊",
                    )
                    st.session_state.current_question_idx += 1
                    st.rerun()
        else:
            app = st.session_state.app_state
            app["product_score"] = runner.finalize_quiz(
                app["quiz_questions"], app["user_answers"], app["ai_weights"]
            )
            st.session_state.seller_stage = "final_processing"
            st.rerun()

    # ── 5: Фінальна обробка ───────────────────────────────────────────────
    elif stage == "final_processing":
        log_ph = st.empty()

        if st.session_state.processing_done:
            st.session_state.seller_stage = "results"
            st.rerun()

        log = st.session_state.processing_log
        log_ph.markdown(_console_log(log), unsafe_allow_html=True)

        app         = st.session_state.app_state
        result_data = None

        for event in runner.step_final_processing(app):
            if "progress" in event:
                log.append(event["progress"])
                st.session_state.processing_log = log
                log_ph.markdown(_console_log(log), unsafe_allow_html=True)

            elif event.get("status") == "captcha" or "captcha" in str(event.get("message", "")).lower():
                st.session_state.captcha_data = {
                    "img": event.get("img"),
                    "return_stage": event.get("return_stage", "final_processing"),
                    "attempt": st.session_state.captcha_data.get("attempt", 0) + 1,
                    "last_error": event.get("error"),
                }
                st.session_state.seller_stage = "captcha_verification"
                st.rerun()

            elif event.get("status") == "error":
                st.error(f"❌ {event['message']}")
                if st.button("Почати заново", key="fp_retry"):
                    _reset_session()
                    st.rerun()
                st.stop()

            elif event.get("status") == "done":
                result_data = event

        if result_data:
            for k, v in result_data.items():
                if k != "status":
                    app[k] = v
            log_ph.markdown(_console_log(log, done=True), unsafe_allow_html=True)
            st.session_state.processing_done = True
            st.session_state.captcha_data    = {}
            st.session_state.seller_stage    = "results"
            st.rerun()

    # ── 6: Результати ─────────────────────────────────────────────────────
    elif stage == "results":
        app       = st.session_state.app_state
        gap       = app.get("gap_summary", {})
        pricing   = app.get("pricing_results", {})
        main_comp = app.get("main_comp")
        score_u   = app.get("product_score", 0)
        score_c   = main_comp.get("score", 0) if main_comp else 0
        cat_b     = app.get("current_category_bounds", {})
        cat_n     = app.get("current_category_name", "")

        pro_text = (
            f"Переваги: {', '.join(gap.get('better', [])[:2])}"
            if gap.get("better") else "Переваги: Повний паритет з лідером"
        )
        con_text = (
            f"Слабкі сторони: {', '.join(gap.get('worse', [])[:2])}"
            if gap.get("worse") else "Слабкі сторони: Відсутні"
        )

        diff = (score_u - score_c) / score_c * 100 if score_c > 0 else 0
        if   diff > 50:   analysis = "Ваш товар значно кращий за лідера. Ви будете домінувати в ніші."
        elif diff >= 0:   analysis = "Ви маєте перевагу над конкурентом. Ринок перспективний."
        elif diff >= -10: analysis = "Ви на рівні з лідером. Посильте дистрибуцію або маркетинг."
        elif diff >= -25: analysis = "Конкуренція жорстка. Товар потребує зусиль у просуванні."
        else:             analysis = "Рекомендуємо переглянути характеристики або цінову категорію."

        comp_name = main_comp.get("name", "N/A") if main_comp else "N/A"

        st.markdown("### 📊 ФІНАЛЬНИЙ БЛОК ВІДПОВІДІ СИСТЕМИ PCM")

        st.markdown(
            f'<div class="ml-block"><h4>🧠 ML Analysis</h4>'
            f'<p><b>1) КАТЕГОРІЯ:</b> Segment "{cat_n}". '
            f'Конкуренти: {cat_b.get("start",0):,.0f}–{cat_b.get("end",0):,.0f} грн.</p>'
            f'<p><b>2) ПЛЮСИ ТА МІНУСИ:</b> {pro_text}. {con_text}.</p>'
            f'<p><b>3) РОЗРАХУНКОВА ЦІНА:</b> '
            f'{pricing.get("final_min",0):,.2f}–{pricing.get("final_max",0):,.2f} грн.</p>'
            f'<p><b>4) КОНКУРЕНТНЕ СЕРЕДОВИЩЕ:</b> '
            f'Ваш товар: {score_u:.1f}/100. Конкурент "{comp_name}": {score_c:.1f}/100. '
            f'{analysis}</p></div>',
            unsafe_allow_html=True,
        )

        raw_advice = app.get("ai_advice", "")

        # Перетворюємо його на HTML-теги
        ai_html = markdown.markdown(raw_advice)

        # Виводимо в блок
        st.markdown(
            f'<div class="ai-block"><h4>🤖 AI Analysis</h4>{ai_html}</div>',
            unsafe_allow_html=True,
        )

        st.markdown("---")
        st.markdown("⭐️ **Оцініть якість аналізу:**")
        if not st.session_state.rating_submitted:
            fb = st.feedback("stars")
            if fb is not None:
                _save_rating(fb)
                st.session_state.rating_submitted = True
                st.success(f"Дякуємо! Оцінка {fb + 1}/5 збережена.")
                st.rerun()
        else:
            st.success("✅ Оцінку збережено. Дякуємо!")

        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🔄 Новий аналіз", use_container_width=True, key="new_analysis"):
            _reset_session()
            st.rerun()

    # ══════════════════════════════════════════════════════════════════════
    # ПОЛЕ ВВОДУ (З'являється тільки на етапі 'waiting_input')
    # ══════════════════════════════════════════════════════════════════════

    if st.session_state.seller_stage == "waiting_input":

        col_in, col_btn = st.columns([93, 7])

        with col_in:
            st.text_input(
                "prompt",
                placeholder="Введіть назву товару (наприклад: Клавіатура)...",
                label_visibility="collapsed",
                key="ws_input",
                on_change=_on_submit,
            )

        with col_btn:
            st.markdown(
                f'<div style="padding-top:8px;display:flex;justify-content:center;">'
                f'<button onclick=\"document.dispatchEvent(new KeyboardEvent(\'keydown\','
                f'{{\'key\':\'Enter\'}}));\"'
                f' style="background:none;border:none;cursor:pointer;width:45px;height:45px;padding:0;">'
                f'<img src="data:image/png;base64,{b64["send"]}"'
                f' style="width:100%;height:100%;object-fit:contain;"></button></div>',
                unsafe_allow_html=True,
            )
