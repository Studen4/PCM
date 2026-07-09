import os
import time
from playwright.sync_api import sync_playwright
# Імпортуємо новий клас замість старої функції
from playwright_stealth import Stealth

SESSION_FILE = "../test_data/ekatalog_session_debug.json"


def is_blocked(page):
    """Перевіряє, чи сторінка заблокована капчею або заглушкою."""
    try:
        content = page.content().lower()
        return any(x in content for x in [
            "checking your browser", "just a moment", "cloudflare",
            "verify you are human", "captcha", "access denied",
            "connection_error.php", "сайт на обслуговуванні", "under maintenance"
        ])
    except:
        return True


def debug_ekatalog():
    with sync_playwright() as p:
        print("[DEBUG] Відкриваю браузер (Реальний Chrome + Stealth)...")

        # Використовуємо реальний Chrome замість дефолтного Chromium
        browser = p.chromium.launch(
            headless=False,
            channel="chrome",  # Підключає ваш справжній Google Chrome
            args=["--disable-blink-features=AutomationControlled"]
        )

        context = browser.new_context(
            storage_state=SESSION_FILE if os.path.exists(SESSION_FILE) else None,
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
            locale='uk-UA',
            viewport={'width': 1920, 'height': 1080}  # Реалістичний розмір екрану
        )
        page = context.new_page()

        # НОВИЙ СИНТАКСИС ДЛЯ ВЕРСІЇ 2.X:
        stealth = Stealth()
        stealth.apply_stealth_sync(page)  # Застосовуємо маскування до сторінки

        test_url = "https://ek.ua/ua/ek-list.php?soft_s_=1&search_=%D0%9A%D0%BB%D0%B0%D0%B2%D1%96%D0%B0%D1%82%D1%83%D1%80%D0%B8"
        print(f"[DEBUG] Переходжу на сторінку: {test_url}")

        page.goto(test_url, wait_until="domcontentloaded", timeout=60000)

        # Перевіряємо, чи пустило нас
        if is_blocked(page):
            print("\n[!] ВИЯВЛЕНО ЗАХИСТ (Капча або Заглушка).")
            print(
                ">>> Скрипт чекає. Якщо є капча - пройдіть її. Якщо просто помилка - спробуйте оновити сторінку (F5).")

            while is_blocked(page):
                time.sleep(2)
                if page.is_closed():
                    print("[ERROR] Вікно закрито.")
                    return

            print("\n[SUCCESS] Захист пройдено! Очікую завантаження контенту сайту...")

            try:
                # ОПТИМІЗАЦІЯ: Чекаємо появу результатів пошуку (категорій або товарів)
                # 'span.wrap-s-res' — блоки категорій, 'div.tile-wrapper' — картки товарів у сітці
                page.wait_for_selector("span.wrap-s-res, div.tile-wrapper, div.model-short-title", timeout=7000)
                print("[+] Контент сайту з'явився на екрані!")
            except Exception:
                # Якщо сталася непередбачувана поведінка — почекаємо 1.5 сек для страховки
                page.wait_for_timeout(1500)

            # Робимо безпечну мікропаузу в 500 мілісекунд (0.5 сек)
            # Це потрібно, щоб внутрішні процеси Chromium встигли скинути токен cf_clearance в контекст
            page.wait_for_timeout(500)

            context.storage_state(path=SESSION_FILE)
            print(f"[+] Ідеальну сесію збережено в {SESSION_FILE}!")
        else:
            print("\n[+] Доступ отримано миттєво! Захист вас не помітив.")
            context.storage_state(path=SESSION_FILE)

        with open("../test_data/debug_output_connection.html", "w", encoding="utf-8") as f:
            f.write(page.content())
        print("[+] HTML збережено в debug_output_connection.html")

        browser.close()


if __name__ == "__main__":
    debug_ekatalog()
