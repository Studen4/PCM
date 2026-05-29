import streamlit as st
import base64
import os

def get_base64_image(image_path):
    """Конвертація зображення в base64 для інлайнового відображення в HTML/CSS."""
    if os.path.exists(image_path):
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()
    return ""

def render_workspace_page(navigate_to):

    # Синхронізація поточного режиму з налаштуваннями
    if 'workspace_mode' not in st.session_state:
        st.session_state.workspace_mode = st.session_state.get('type_cb', 'Customer Mode').lower().split()[0]

    # Шляхи до інтерфейсних асетів
    terms_path = "ui/assets/terms.png"
    settings_path = "ui/assets/settings.png"
    send_path = "ui/assets/send_button.png"

    role = st.session_state.get('user_role', 'guest')
    avatar_path = f"ui/assets/{role}.png"
    if not os.path.exists(avatar_path):
        avatar_path = "ui/assets/user.png"

    # Завантаження картинок в пам'ять
    b64_terms = get_base64_image(terms_path)
    b64_settings = get_base64_image(settings_path)
    b64_avatar = get_base64_image(avatar_path)
    b64_send = get_base64_image(send_path)

    # --- CSS СТИЛІ ---
    st.markdown(f"""
        <style>
            .navbar-right-flexbox {{
                display: flex !important;
                flex-direction: row !important;
                align-items: center !important;
                justify-content: flex-end !important;
                gap: 14px !important;
                width: 100% !important;
                height: 55px !important;
            }}
            .nav-icon-item {{
                width: 46px !important;
                height: 46px !important;
                min-width: 46px !important;
                border-radius: 50% !important;
                border: 2px solid #e5e7eb !important;
                background-color: #ffffff !important;
                display: flex !important;
                align-items: center !important;
                justify-content: center !important;
                overflow: hidden !important;
                transition: transform 0.2s, border-color 0.2s !important;
                text-decoration: none !important;
            }}
            .nav-icon-item:hover {{
                transform: scale(1.05) !important;
                border-color: #00b894 !important;
            }}
            .nav-icon-item img {{
                width: 100% !important;
                height: 100% !important;
                object-fit: cover !important;
            }}
            .nav-logout-item {{
                font-family: inherit !important;
                font-size: 0.95rem !important;
                font-weight: 500 !important;
                color: #4b5563 !important;
                background-color: transparent !important;
                border: 1px solid #e5e7eb !important;
                border-radius: 6px !important;
                padding: 8px 18px !important;
                text-decoration: none !important;
                transition: background-color 0.2s, color 0.2s !important;
                white-space: nowrap !important;
            }}
            .nav-logout-item:hover {{
                background-color: #f3f4f6 !important;
                color: #111827 !important;
                border-color: #d1d5db !important;
            }}
            /* Кнопка відправки: прибрано текст, додано ассет */
            div.interaction-zone-send-block button {{
                width: 55px !important;
                height: 55px !important;
                min-width: 55px !important;
                max-width: 55px !important;
                padding: 0 !important;
                border: none !important;
                background-color: transparent !important;
                background-image: url("data:image/png;base64,{b64_send}") !important;
                background-size: contain !important;
                background-position: center !important;
                background-repeat: no-repeat !important;
                color: transparent !important;
                font-size: 0px !important;
                cursor: pointer !important;
                box-shadow: none !important;
            }}
            div.interaction-zone-send-block button:hover {{
                transform: scale(1.03) !important;
                background-color: transparent !important;
            }}
            .mode-container {{
                border: 2px solid #e5e7eb;
                border-radius: 8px;
                padding: 10px;
                background-color: #ffffff;
                margin-bottom: 20px;
                display: flex;
                justify-content: center;
            }}
            .custom-ai-alert {{
                border-top: 1px solid #e5e7eb;
                padding-top: 15px;
                margin-top: 40px;
                font-size: 0.8rem;
                line-height: 1.4;
                color: #4b5563;
                text-align: justify;
                font-family: 'Courier New', Courier, monospace;
            }}
            .custom-ai-alert strong {{
                color: #dc2626;
            }}
        </style>
    """, unsafe_allow_html=True)

    # --- SIDEBAR ---
    with st.sidebar:
        mode_asset = f"ui/assets/{st.session_state.workspace_mode}_mode.png"
        if os.path.exists(mode_asset):
            b64_mode = get_base64_image(mode_asset)
            st.markdown(f"""
                <div class="mode-container">
                    <img src="data:image/png;base64,{b64_mode}" style="width: 100%; height: auto;">
                </div>
            """, unsafe_allow_html=True)
        st.button("+ New Analysis Chat", use_container_width=True, type="primary")
        st.markdown("<br><h5 style='text-align: center; color: #6b7280; font-weight: bold;'>Recent Chats</h5>", unsafe_allow_html=True)
        st.write("📄 Gaming Laptop Analysis")
        st.write("📄 Office Chair Budgeting")
        st.markdown("<br>" * 8, unsafe_allow_html=True)
        st.markdown("""
            <div class="custom-ai-alert">
                <strong>Attention:</strong> PCM is powered by AI. The model may make mistakes or inaccuracies in calculations. 
                Price analysis results do not constitute financial advice and require final verification by the user before buying or selling.
            </div>
        """, unsafe_allow_html=True)

    # --- NAVBAR ---
    nav_col1, nav_col2 = st.columns([5, 4])
    with nav_col1:
        st.markdown("<h2 style='margin: 0; padding-top: 5px; color: #00b894; font-weight: bold;'>Price Control Model</h2>", unsafe_allow_html=True)
    with nav_col2:
        st.markdown(f"""
            <div class="navbar-right-flexbox">
                <a href="?action=terms" target="_self" class="nav-icon-item" title="Terms of Service">
                    <img src="data:image/png;base64,{b64_terms}">
                </a>
                <a href="?action=settings" target="_self" class="nav-icon-item" title="Settings">
                    <img src="data:image/png;base64,{b64_settings}">
                </a>
                <div class="nav-icon-item" style="cursor: default;" title="Role: {role.capitalize()}">
                    <img src="data:image/png;base64,{b64_avatar}">
                </div>
                <a href="?action=logout" target="_self" class="nav-logout-item">Log out</a>
            </div>
        """, unsafe_allow_html=True)
    st.markdown("<hr style='margin-top: 10px; margin-bottom: 25px; border: 1px solid #e5e7eb;'>", unsafe_allow_html=True)

    # --- WORK ZONE ---
    st.markdown("<h2 style='text-align: center; color: #9ca3af; padding: 120px 0; font-weight: normal;'>Select a chat or start a new analysis...</h2>", unsafe_allow_html=True)

    # --- INTERACTION ZONE (Нижня панель введення та кнопка відправки) ---
    int_col1, int_col2 = st.columns([93, 7])

    with int_col1:
        st.markdown("<div style='padding-top: 18px;'>", unsafe_allow_html=True)
        st.text_input(
            "prompt",
            placeholder="Enter product name, category, or link to analyze...",
            label_visibility="collapsed",
            key="workspace_prompt_input"
        )
        st.markdown("</div>", unsafe_allow_html=True)

    with int_col2:
        # Використовуємо ту саму HTML-логіку, що і для іконок навігації
        # Це працює стабільно і дозволяє легко вставити картинку
        st.markdown(f"""
                <div style='padding-top: 25px; display: flex; justify-content: center;'>
                    <a href="?action=send_query" target="_self" style='display: inline-block; width: 45px; height: 45px;'>
                        <img src="data:image/png;base64,{b64_send}" style="width: 100%; height: 100%; object-fit: contain;">
                    </a>
                </div>
            """, unsafe_allow_html=True)

    # Обробка натискання кнопки
    if st.query_params.get("action") == "send_query":
        pass

        st.query_params.clear()
