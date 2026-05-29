import streamlit as st


def render_settings_page(navigate_to):
    st.markdown("<div class='centered-title'>PCM Engine Settings</div>", unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.container(border=True):
            st.markdown(
                "<div class='subtitle' style='margin-top: 10px;'>Adjust the core parameters for market analysis.</div>",
                unsafe_allow_html=True)

            cfg_col1, cfg_col2 = st.columns([1, 2])
            with cfg_col1:
                st.markdown("<br>**AI Model:**", unsafe_allow_html=True)
                st.markdown("<br>**Data Aggregator:**", unsafe_allow_html=True)
                st.markdown("<br>**Market Region:**", unsafe_allow_html=True)
                st.markdown("<br>**Results Limit:**", unsafe_allow_html=True)
                st.markdown("<br>**Operation Mode:**", unsafe_allow_html=True)
            with cfg_col2:
                st.selectbox("Model", ["PCM Basic Engine", "GPT-4o"], key="model_cb", label_visibility="collapsed")
                st.selectbox("Aggregator", ["e-katalog (ek.ua)"], key="agg_cb", label_visibility="collapsed")
                st.selectbox("Region", ["Ukraine (UAH)"], key="reg_cb", label_visibility="collapsed")
                st.selectbox("Top Results", ["Top-1", "Top-2", "Top-3"], key="top_cb", label_visibility="collapsed")
                st.selectbox("Mode Type", ["Customer Mode", "Seller Mode"], key="type_cb", label_visibility="collapsed")

            st.write("")
            if st.button("Save & Continue to Workspace", use_container_width=True, type="primary"):
                # Зберігаємо вибраний режим для коректного відображення асету
                st.session_state.workspace_mode = st.session_state.type_cb.lower().split()[0]
                navigate_to('workspace')

        if st.session_state.get('current_user') is not None:
            if st.button("Cancel & Back", use_container_width=True):
                navigate_to('workspace')
