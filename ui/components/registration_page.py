import streamlit as st
import json
import os
import time


def render_registration_page(navigate_to):
    st.markdown("<div class='centered-title'>Create an Account</div>", unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown(
            "<div class='subtitle'>Join the PCM platform to save your analysis history and configuration preferences.</div>",
            unsafe_allow_html=True)

        with st.container(border=True):
            st.markdown("**Create Login:**")
            reg_login = st.text_input("New Username", key="reg_login", label_visibility="collapsed",
                                      placeholder="Enter new login")

            st.markdown("**Create Password:**")
            reg_pass = st.text_input("New Password", type="password", key="reg_pass", label_visibility="collapsed",
                                     placeholder="Enter new password")

            st.write("")
            if st.button("Register Account", use_container_width=True, type="primary"):
                if not reg_login or not reg_pass:
                    st.error("❌ Заповніть всі поля!")
                else:
                    db_path = os.path.join("data", "users_db.json")
                    db = {}
                    if os.path.exists(db_path):
                        with open(db_path, "r", encoding="utf-8") as f:
                            db = json.load(f)

                    if reg_login in db:
                        st.error("❌ Користувач з таким логіном вже існує!")
                    else:
                        db[reg_login] = {"password": reg_pass, "role": "user"}
                        with open(db_path, "w", encoding="utf-8") as f:
                            json.dump(db, f, indent=4)

                        st.success("✅ Реєстрація успішна! Перенаправлення...")
                        time.sleep(1.5)
                        navigate_to('login')

        if st.button("Back to Login", use_container_width=True):
            navigate_to('login')
