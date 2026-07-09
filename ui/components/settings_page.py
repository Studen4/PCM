import streamlit as st


def render_settings_page(navigate_to):
    st.markdown("<div class='centered-title'>PCM Engine Settings</div>", unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.container(border=True):
            st.markdown("<div class='subtitle' style='margin-top: 10px;'>Adjust the core parameters for market analysis.</div>", unsafe_allow_html=True)

            # Використовуємо st.write для створення вертикальних відступів
            cfg_col1, cfg_col2 = st.columns([1, 2])
            with cfg_col1:
                st.write("") # Відступ
                st.markdown("**AI Model:**")
                st.write("") # Відступ
                st.markdown("**Data Aggregator:**")
                st.write("") # Відступ
                st.markdown("**Market Region:**")
                st.write("") # Відступ
                st.markdown("**Results Limit:**")
                st.write("") # Відступ
                st.markdown("**Operation Mode:**")
            with cfg_col2:
                st.selectbox("Model", ["PCM Basic", "PCM Professional", "PCM Seller Extended", "PCM Customer Extended"], key="model_cb", label_visibility="collapsed")
                st.selectbox("Aggregator", ["e-katalog (ek.ua)", "OLX (olx.ua)", "Rozetka (rozetka.com.ua)", "Aliexpress (aliexpress.com)"], key="agg_cb", label_visibility="collapsed")
                st.selectbox("Region", ["Ukraine (UAH)", "Poland (PLN)", "USA (USD)"], key="reg_cb", label_visibility="collapsed")
                st.selectbox("Top Results", ["Top-1", "Top-2", "Top-3"], key="top_cb", label_visibility="collapsed")
                st.selectbox("Mode Type", ["Customer Mode", "Seller Mode"], key="type_cb", label_visibility="collapsed")

            if st.button("Save & Continue to Workspace", use_container_width=True, type="primary"):
                # Зберігаємо режим в session_state
                st.session_state.workspace_mode = st.session_state.type_cb.lower().split()[0]
                navigate_to('workspace')
