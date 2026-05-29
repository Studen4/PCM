import streamlit as st
from components.login_page import render_login_page
from components.registration_page import render_registration_page
from components.settings_offer_page import render_settings_offer_page
from components.settings_page import render_settings_page
from components.workspace_page import render_workspace_page
from components.terms_page import render_terms_page

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
        st.rerun() # Перезавантажуємо, щоб головний роутер підхопив 'terms'
    elif action == "settings":
        st.session_state.current_page = 'settings'
        st.rerun()
    elif action == "logout":
        st.session_state.current_user = None
        st.session_state.current_page = 'login'
        st.rerun()
    elif action == "send_query":
        # Тут можна додати логіку для кнопки відправки, якщо треба
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
