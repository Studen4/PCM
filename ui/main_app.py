import os
import sys
import subprocess
import time
# import atexit
import requests

# 1. НАЛАШТОВУЄМО ШЛЯХИ
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import streamlit as st
from components.login_page import render_login_page
from components.registration_page import render_registration_page
from components.settings_offer_page import render_settings_offer_page
from components.settings_page import render_settings_page
from components.workspace_page import render_workspace_page
from components.terms_page import render_terms_page


# @st.cache_resource
# def launch_session_daemon():
#     """
#     Надійно запускає session_daemon.py у фоновому процесі рівно ОДИН раз.
#     """
#     # 1. Швидка і легка перевірка, чи порт 8000 взагалі живий (будь-яка відповідь, навіть 404, є ок)
#     try:
#         res = requests.get("http://127.0.0.1:8000/", timeout=0.5)
#         return "Already running"
#     except requests.exceptions.ConnectionError:
#         pass  # Порт вільний, демон точно не запущений
#
#     # Формуємо шлях до демона
#     daemon_path = os.path.join(project_root, "core", "optimization", "session_daemon.py")
#
#     if os.path.exists(daemon_path):
#         # 2. Налаштовуємо змінні оточення, щоб демон бачив корінь проєкту PCM
#         env = os.environ.copy()
#         env["PYTHONPATH"] = project_root + os.pathsep + env.get("PYTHONPATH", "")
#
#         # 3. Створюємо файл для логів демона, щоб бачити помилки, якщо він впаде
#         log_dir = os.path.join(project_root, "data")
#         os.makedirs(log_dir, exist_ok=True)
#         log_file = open(os.path.join(log_dir, "daemon.log"), "w", encoding="utf-8")
#
#         # 4. Запускаємо процес із явним зазначенням робочої директорії (cwd)
#         proc = subprocess.Popen(
#             [sys.executable, daemon_path],
#             cwd=project_root,  # Запуск суворо з кореня!
#             env=env,
#             stdout=log_file,
#             stderr=log_file
#         )
#
#         # Функція очищення при виходу зі Streamlit
#         def kill_daemon():
#             proc.terminate()
#             proc.wait()
#             log_file.close()
#
#         atexit.register(kill_daemon)
#
#         # Даємо демону 3 секунди, щоб підняти FastAPI та Playwright Chrome
#         time.sleep(3.0)
#         return "Successfully launched background daemon"
#
#     return "Daemon file not found"
#
#
# # Викликаємо функцію запуску. Завдяки cache_resource вона виконається лише 1 раз при першому відкритті сайту.
# daemon_status = launch_session_daemon()

# --- КОНФІГУРАЦІЯ СТОРІНКИ ТА CSS ---
st.set_page_config(page_title="PCM Basic", layout="wide", initial_sidebar_state="expanded")

custom_css = """
<style>
    html, body, [class*="css"] {
        font-family: 'Courier New', Courier, monospace !important;
        background-color: #FFFFFF !important;
    }
    .centered-title {
        text-align: center;
        font-weight: bold;
        font-size: 2.5rem;
        margin-bottom: 20px;
        color: #1f2937;
    }
    .subtitle {
        text-align: center;
        color: #4b5563;
        font-size: 1.1rem;
        margin-bottom: 30px;
    }
</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)

# --- ІНІЦІАЛІЗАЦІЯ СТАНУ СЕСІЇ ---
if 'current_page' not in st.session_state:
    st.session_state.current_page = 'login'
if 'current_user' not in st.session_state:
    st.session_state.current_user = None


def navigate_to(page_name):
    st.session_state.current_page = page_name
    st.rerun()


# --- РОУТЕР-ІНТЕРЦЕПТОР (Глобальна обробка) ---
if "action" in st.query_params:
    action = st.query_params["action"]
    st.query_params.clear()  # Миттєво видаляємо параметр, щоб він не дублювався

    if action == "terms":
        st.session_state.current_page = 'terms'
        st.rerun()  # Перезавантажуємо, щоб головний роутер підхопив 'terms'
    elif action == "settings":
        st.session_state.current_page = 'settings'
        st.rerun()
    elif action == "logout":
        st.session_state.current_user = None
        st.session_state.current_page = 'login'
        st.rerun()

    # --- ОБРОБКА СКИДАННЯ СЕСІЇ ТА НОВОГО ЧАТУ ---
    elif action == "new_chat":
        # 1. Очищуємо всі змінні стану інтерфейсу аналізу
        keys_to_clear = [
            'seller_stage', 'app_state', 'current_question_idx',
            'show_all_categories', 'rating_submitted', 'captcha_data'
        ]
        for key in keys_to_clear:
            if key in st.session_state:
                del st.session_state[key]

        # 2. Викликаємо функцію закриття заблокованого браузера з вашого парсера
        try:
            from scraper.ekatalog_parser import reset_parser_session

            reset_parser_session()
        except Exception as e:
            pass

        # 3. Повертаємо користувача на чисту робочу зону
        st.session_state.current_page = 'workspace'
        st.rerun()

    elif action == "send_query":
        pass

# --- РОУТЕР ---
if st.session_state.current_page == 'login':
    render_login_page(navigate_to)
elif st.session_state.current_page == 'registration':
    render_registration_page(navigate_to)
elif st.session_state.current_page == 'settings-offer':
    render_settings_offer_page(navigate_to)
elif st.session_state.current_page == 'settings':
    render_settings_page(navigate_to)
elif st.session_state.current_page == 'workspace':
    render_workspace_page(navigate_to)
elif st.session_state.current_page == 'terms':
    render_terms_page(navigate_to)
