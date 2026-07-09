import os
import time
from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth


def run_manual_solver():
    session_file = "../test_data/ekatalog_session.json"
    url = "https://ek.ua/ua/"

    print("🚀 Запуск незалежного вікна для авторизації в E-katalog...")

    with sync_playwright() as p:
        # Відкриваємо СПРАВЖНІЙ видимий браузер Chrome
        browser = p.chromium.launch(
            headless=False,
            channel="chrome",
            args=["--disable-blink-features=AutomationControlled"]
        )

        context = browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
            locale='uk-UA',
            viewport={'width': 1200, 'height': 800}
        )

        page = context.new_page()
        stealth = Stealth()
        stealth.apply_stealth_sync(page)

        print(f"🔗 Перехід на сайт: {url}")
        page.goto(url, wait_until="domcontentloaded")

        print("\n" + "=" * 60)
        print("🚩 ІНСТРУКЦІЯ ДЛЯ ВАС:")
        print("1. Якщо на екрані з'явилася капча Cloudflare (клікнути на квадратик) — КЛІКНІТЬ ЙОГО.")
        print("2. Переконайтеся, що головна сторінка е-каталогу повністю завантажилась.")
        print("3. ПІСЛЯ ЦЬОГО поверніться в цей термінал і натисніть ENTER, щоб зберегти сесію.")
        print("=" * 60 + "\n")

        input("Натисніть ENTER ТУТ, коли успішно пройдете капчу на сайті... ")

        # Зберігаємо стан кукі у файл, який ділять Демон та проект
        context.storage_state(path=session_file)
        print(f"✅ Сесію успішно збережено у файл: {os.path.abspath(session_file)}")

        browser.close()


if __name__ == "__main__":
    run_manual_solver()