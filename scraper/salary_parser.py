import requests
from bs4 import BeautifulSoup
import streamlit as st


@st.cache_data(ttl=86400)  # Кешуємо на 24 години
def get_normalized_salary():
    """
    Зчитує обраний регіон із st.session_state, парсить середню річну ЗП в USD,
    конвертує в локальну валюту (через Мінфін для UAH) і вираховує чисту місячну ЗП (-23%).
    """
    # Зчитуємо обраний у налаштуваннях регіон
    selected_region = st.session_state.get('reg_cb', 'Ukraine (UAH)')

    try:
        country_name = selected_region.split(' (')[0].strip()  # "Ukraine"
        currency_code = selected_region.split(' (')[1].replace(')', '').strip()  # "UAH"
    except IndexError:
        country_name = "Ukraine"
        currency_code = "UAH"

    fallback_salary_usd_year = 5200.0
    usd_rate = 41.50  # Базовий fallback

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }

    # --- 1. ПАРСИНГ СЕРЕДНЬОЇ ЗАРПЛАТИ (WorldData) ---
    try:
        url_salary = "https://www.worlddata.info/average-income.php"
        resp_s = requests.get(url_salary, headers=headers, timeout=10)

        if resp_s.status_code == 200:
            soup_s = BeautifulSoup(resp_s.text, 'html.parser')
            for row in soup_s.find_all('tr'):
                if country_name.lower() in row.text.lower():
                    cells = row.find_all('td')
                    if len(cells) > 1:
                        raw_income = cells[1].text.replace('$', '').replace(',', '').strip()
                        fallback_salary_usd_year = float(raw_income)
                        break
    except Exception:
        pass

    monthly_salary_usd = fallback_salary_usd_year / 12

    # --- 2. ПАРСИНГ КУРСУ ВАЛЮТ (Мінфін) ---
    if currency_code == "UAH":
        try:
            url_rate = "https://minfin.com.ua/ua/currency/"
            resp_r = requests.get(url_rate, headers=headers, timeout=10)

            if resp_r.status_code == 200:
                soup_r = BeautifulSoup(resp_r.text, 'html.parser')
                all_tds = [td.text.strip() for td in soup_r.find_all('td') if td.text]

                for i, text in enumerate(all_tds):
                    if "USD" in text or "$ " in text:
                        for j in range(1, 4):
                            potential_rate = all_tds[i + j].replace('\n', '').replace(' ', '').replace(',', '.')
                            try:
                                val = float(potential_rate[:5])
                                if 35.0 < val < 50.0:
                                    usd_rate = val
                                    break
                            except ValueError:
                                continue
                        break
        except Exception:
            pass

        monthly_salary_local = monthly_salary_usd * usd_rate
    else:
        monthly_salary_local = monthly_salary_usd

    # --- 3. НОРМАЛІЗАЦІЯ (Зрізання 23% податків) ---
    net_monthly_salary = monthly_salary_local * 0.77

    return round(net_monthly_salary, 2)

# --- ТЕСТОВИЙ БЛОК ЗАКОМЕНТОВАНО ДЛЯ ПРОДАКШЕНУ ---
# if __name__ == "__main__":
#     import sys
#     class MockStreamlit:
#         def cache_data(self, *args, **kwargs): return lambda f: f
#         @property
#         def session_state(self): return {'reg_cb': 'Ukraine (UAH)'}
#     sys.modules['streamlit'] = MockStreamlit()
#
#     final_net = get_normalized_salary()
#     print(f"🎯 OUTPUT FOR ENGINE: {final_net} UAH")
