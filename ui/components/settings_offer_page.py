import streamlit as st


def render_settings_offer_page(navigate_to):
    st.markdown("<div class='centered-title'>System Configuration</div>", unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.container(border=True):
            st.markdown(
                "<div class='subtitle' style='margin-top: 20px;'>Would you like to configure the AI model and aggregator settings, or proceed with default values?</div>",
                unsafe_allow_html=True)
            st.write("")

            btn_col1, btn_col2 = st.columns(2)
            with btn_col1:
                if st.button("Configure Settings", use_container_width=True):
                    navigate_to('settings')
            with btn_col2:
                if st.button("Use Default Config", use_container_width=True, type="primary"):
                    navigate_to('workspace')
