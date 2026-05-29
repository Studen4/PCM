import streamlit as st
import urllib.parse

TERMS_HTML_CONTENT = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Terms of Service - PCM</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            line-height: 1.6;
            color: #1f2937;
            background-color: #f9fafb;
            margin: 0;
            padding: 40px 20px;
        }
        .container {
            max-width: 800px;
            margin: 0 auto;
            background: #ffffff;
            padding: 40px;
            border-radius: 12px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
            border: 1px solid #e5e7eb;
        }
        h1 {
            font-size: 2rem;
            color: #111827;
            margin-bottom: 8px;
            border-bottom: 2px solid #e5e7eb;
            padding-bottom: 16px;
        }
        h2 {
            font-size: 1.35rem;
            color: #374151;
            margin-top: 28px;
            margin-bottom: 12px;
        }
        p, li {
            font-size: 1rem;
            color: #4b5563;
        }
        ul {
            padding-left: 20px;
        }
        li {
            margin-bottom: 8px;
        }
        .highlight {
            font-weight: 600;
            color: #2563eb;
        }
        .footer {
            margin-top: 40px;
            text-align: center;
            font-size: 0.85rem;
            color: #9ca3af;
            border-top: 1px solid #e5e7eb;
            padding-top: 20px;
        }
    </style>
</head>
<body>

<div class="container">
    <h1>Terms of Service</h1>
    <p>Welcome to <span class="highlight">Price Control Model (PCM)</span>. Please read these Terms of Service carefully before using our software platform.</p>

    <h2>1. General Provisions</h2>
    <p>PCM is an experimental software designed to automate product price category analysis. By accessing this platform as a Guest \\ User or an Administrator, you acknowledge and agree to the scope and limitations outlined below.</p>

    <h2>2. Disclaimer & Limitation of Liability</h2>
    <ul>
        <li><strong>No Financial Advice:</strong> The AI-driven algorithms and mathematical models applied within PCM provide purely analytical and hypothetical data. This software <strong>does not</strong> constitute financial, business, investment, or legal advice.</li>
        <li><strong>Inaccuracies & AI Limitations:</strong> As an AI-powered assistant, the model may occasionally generate incorrect metrics, miscalculate price caps, or experience hallucinations.</li>
        <li><strong>User Responsibility:</strong> All market assessments, generated price groups, and external product links require mandatory final verification by the user before executing any real-world buying or selling transactions.</li>
        <li><strong>Limitation of Liability:</strong> Under no circumstances shall the developers or creators of PCM be held liable for any direct, indirect, financial, or incidental losses resulting from reliance on the software's output.</li>
    </ul>

    <h2>3. Data Collection & Privacy</h2>
    <p>In this version, data processing is kept highly secure through localized workflows:</p>
    <ul>
        <li>All chat histories, session tokens, and dynamic system settings are stored <strong>locally within your local session environment</strong>.</li>
        <li>No personal files or data are uploaded to permanent remote databases, except for anonymized text inputs transmitted securely to artificial intelligence APIs (such as OpenAI/Anthropic) required to fulfill your prompt analysis.</li>
    </ul>

    <h2>4. Modifications to the Service</h2>
    <p>We reserve the right to alter the mathematical equations, adjust default parameters, or temporarily modify access roles at any time to test and improve the algorithm's performance.</p>

    <div class="footer">
        Price Control Model • Version 1.0.0 (PCM Basic) • 2026
    </div>
</div>

</body>
</html>
"""


def render_terms_page(navigate_to):
    # 1. Кодуємо HTML-контент у безпечний формат для URL
    encoded_html = urllib.parse.quote(TERMS_HTML_CONTENT)

    # 2. Створюємо Data URL
    data_url = f"data:text/html;charset=utf-8,{encoded_html}"

    # 3. Використовуємо st.iframe, як того вимагає Streamlit
    st.iframe(src=data_url, height=800)

    # Кнопка для повернення назад
    st.markdown("<br><hr>", unsafe_allow_html=True)
    if st.button("← Back"):
        target = 'workspace' if st.session_state.get('current_user') else 'login'
        navigate_to(target)
