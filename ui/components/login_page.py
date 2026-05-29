import streamlit as st
import json
import os


def render_login_page(navigate_to):
    st.markdown("<div class='centered-title'>Login to your account</div>", unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown(
            "<div class='subtitle'>Welcome to the official PCM resource, log in to your account to start enjoying the benefits of AI pricing.</div>",
            unsafe_allow_html=True)

        with st.container(border=True):
            st.markdown("**Login:**")
            login_input = st.text_input("Username", key="login_input", label_visibility="collapsed",
                                        placeholder="ExampleLogin")

            st.markdown("**Password:**")
            password_input = st.text_input("Password", type="password", key="password_input",
                                           label_visibility="collapsed", placeholder="ExamplePass")

            st.write("")
            btn_col1, btn_col2 = st.columns(2)
            with btn_col1:
                if st.button("Let's start!", use_container_width=True, type="primary"):
                    db_path = os.path.join("data", "users_db.json")

                    if not login_input or not password_input:
                        st.error("❌ Поля не можуть бути пустими!")
                    elif os.path.exists(db_path):
                        with open(db_path, "r", encoding="utf-8") as f:
                            db = json.load(f)

                        if login_input in db and db[login_input]["password"] == password_input:
                            st.session_state.current_user = login_input
                            st.session_state.user_role = db[login_input]["role"]
                            navigate_to('settings-offer')
                        else:
                            st.error("❌ Невірний логін або пароль!")
                    else:
                        st.error("❌ База даних не знайдена!")

            with btn_col2:
                if st.button("Login as Guest", use_container_width=True):
                    st.session_state.current_user = "Guest"
                    st.session_state.user_role = "guest"
                    navigate_to('settings-offer')

        st.write("")
        if st.button("Don't have an account? Register here", use_container_width=True):
            navigate_to('registration')
