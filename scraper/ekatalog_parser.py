import json
import urllib.parse
import re
import time
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
import os
from difflib import SequenceMatcher
from playwright_stealth import Stealth
import psutil

# Глобальні змінні для браузера
_playwright = None
_browser = None
_page = None


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


def close_browser():
    global _browser, _playwright, _page
    if _page: _page.close()
    if _browser: _browser.close()
    if _playwright: _playwright.stop()
    _page = None
    _browser = None
    _playwright = None

def force_kill_playwright_driver():
    """
    Примусово знаходить і вбиває процес node.exe, який є драйвером Playwright.
    """
    try:
        # Проходимо по всіх процесах
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                # Шукаємо саме node.exe, який працює з Playwright
                # Зазвичай у командному рядку є 'playwright' або 'driver'
                if proc.info['name'] == 'node.exe':
                    cmdline = proc.info['cmdline']
                    if cmdline and any('playwright' in str(c).lower() for c in cmdline):
                        print(f"[DEBUG] Знаходимо процес Playwright (PID: {proc.pid}). Вбиваємо...", flush=True)
                        proc.kill()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
    except Exception as e:
        print(f"[WARNING] Помилка при спробі вбити драйвер: {e}", flush=True)

def get_page(headless=True):
    global _playwright, _browser, _page
    session_file = "ekatalog_session.json"

    if _page is None or _page.is_closed():
        _playwright = sync_playwright().start()

        # Використовуємо реальний Chrome для парсингу
        _browser = _playwright.chromium.launch(
            headless=headless,
            channel="chrome",
            args=["--disable-blink-features=AutomationControlled"]
        )

        context = _browser.new_context(
            storage_state=session_file if os.path.exists(session_file) else None,
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
            locale='uk-UA',
            viewport={'width': 1920, 'height': 1080}
        )
        _page = context.new_page()

        # Застосовуємо маскування Stealth
        stealth = Stealth()
        stealth.apply_stealth_sync(_page)

    return _page


def solve_captcha_manually(url):
    """
    Відкриває видимий браузер, чекає проходження захисту
    та зберігає надійну сесію.
    """
    print(f"\n[!] ПОТРІБНА РУЧНА ВЕРІФІКАЦІЯ (Cloudflare/Заглушка): {url}")
    close_browser()

    # Відкриваємо видимий браузер
    get_page(headless=False)

    # Використовуємо великий таймаут для очікування
    _page.goto(url, wait_until="domcontentloaded", timeout=60000)

    print(">>> [MONITORING] Очікую на проходження капчі (або оновіть сторінку F5)...")

    # Цикл спостереження
    while is_blocked(_page):
        time.sleep(2)
        if _page.is_closed():
            print("[ERROR] Вікно браузера закрито користувачем.")
            break

    print("\n[SUCCESS] Захист пройдено! Очікую завантаження контенту сайту...")

    try:
        # Розумне очікування результатів
        _page.wait_for_selector("span.wrap-s-res, div.tile-wrapper, div.model-short-title", timeout=7000)
    except Exception:
        _page.wait_for_timeout(1500)

    # Мікропауза для фіксації кукі Cloudflare
    _page.wait_for_timeout(500)

    print("[SUCCESS] Зберігаю ідеальну сесію...")
    _page.context.storage_state(path="ekatalog_session.json")

    # Закриваємо вікно і повертаємося до "тихого" (headless) режиму
    close_browser()
    print("[+] Готово.")


def _get_soup(url: str, retry_attempt=True):
    # Завжди пробуємо спочатку невидимо
    page = get_page(headless=True)

    try:
        page.goto(url, wait_until="domcontentloaded", timeout=30000)

        # Перевірка на блокування
        if is_blocked(page):
            if retry_attempt:
                print("[WARN] Виявлено захист Cloudflare. Перемикаюсь на видимий браузер...")
                solve_captcha_manually(url)
                # Після збереження сесії, пробуємо ще раз (вже невидимо)
                return _get_soup(url, retry_attempt=False)
            else:
                print("[ERROR] Заблоковано навіть після ручної перевірки.")
                return None, None

        return BeautifulSoup(page.content(), "html.parser"), page
    except Exception as e:
        print(f"[ERROR] Помилка парсингу: {e}")
        return None, None


def _get_price_from_sorting(katalog_id: int, order: str):
    """Допоміжна функція для отримання ціни через сортування."""
    url = f"https://ek.ua/ua/ek-list.php?katalog_={katalog_id}&order_={order}"
    soup, _ = _get_soup(url)
    if not soup: return None

    # Шукаємо ціну: спочатку спробуємо знайти тег з класом ib, потім будь-який ціновий клас
    price_tag = soup.find('i', class_='ib') or soup.find(class_=re.compile(r'(price|pr35)'))

    if price_tag:
        text = price_tag.text.replace('\xa0', '').replace(' ', '').replace(',', '.')
        match = re.search(r'(\d+)', text)
        return int(match.group(1)) if match else None
    return None


def save_debug_html(soup, filename="debug_filters.html"):
    """Зберігає сторінку з підсвіткою елементів, які знаходить парсер."""
    import re
    import os

    from bs4 import BeautifulSoup
    debug_soup = BeautifulSoup(str(soup), 'html.parser')

    # Шукаємо заголовки
    elements = debug_soup.find_all('div', class_=re.compile(r'h2'))

    count = 0
    for el in elements:
        style = el.get('style', '')
        el['style'] = style + "; border: 3px solid lime !important; background-color: rgba(0, 255, 0, 0.1) !important;"
        count += 1

    # Зберігаємо файл ТАМ ЖЕ, де знаходиться цей скрипт
    current_dir = os.path.dirname(os.path.abspath(__file__))
    filepath = os.path.join(current_dir, filename)

    try:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(debug_soup.prettify())
        print(f"\n[DEBUG] Збережено сторінку для відладки: {filepath} (Знайдено {count} h2-елементів)")
    except Exception as e:
        print(f"\n[DEBUG ERROR] Не вдалося зберегти файл: {e}")

def parse_search_page(query: str):
    url = f"https://ek.ua/ua/ek-list.php?soft_s_=1&search_={urllib.parse.quote(query)}"
    result = {"categories": {}, "url": url}

    soup, response = _get_soup(url)
    if not soup: return result

    # 1. Збір категорій
    temp_categories = {}
    categories = soup.find_all('span', class_='wrap-s-res')
    for span in categories:
        name = span.text.strip()
        a = span.find_parent('a')
        if a and 'katalog_=' in a.get('href', ''):
            match = re.search(r'katalog_=(\d+)', a['href'])
            if match:
                temp_categories[name] = int(match.group(1))

    # 2. Розумне сортування з Fuzzy Matching
    def calculate_relevance(name):
        name_lower = name.lower()
        query_lower = query.lower()

        # Перевірка 1: чи містить назва запит (вищий пріоритет)
        if query_lower in name_lower:
            return 1.0

            # Перевірка 2: наскільки схожі слова (fuzzy match для друкарських помилок)
        # SequenceMatcher повертає число від 0 до 1
        return SequenceMatcher(None, query_lower, name_lower).ratio()

    # Сортуємо: чим вищий бал релевантності, тим вище категорія
    sorted_items = sorted(
        temp_categories.items(),
        key=lambda item: calculate_relevance(item[0]),
        reverse=True
    )

    result["categories"] = dict(sorted_items)
    return result


def parse_category_page(katalog_id: int, min_price: int = None, max_price: int = None):
    """
    Збирає дані про категорію: фільтри, ціновий діапазон та товари.
    Повертає словник result у будь-якому випадку.
    """
    url = f"https://ek.ua/ua/ek-list.php?katalog_={katalog_id}&save_podbor_=1&sc_id_=980&order_=pop"

    result = {
        "url": url,
        "total_items": 0,
        "price_pool": {"min": min_price or 0, "max": max_price or 0},
        "sidebar_filters": {},
        "products": []
    }

    soup, _ = _get_soup(url)

    if not soup:
        # save_debug_html(soup)
        print(f"[ERROR] Не вдалося отримати контент для категорії ID: {katalog_id}")
        return result

    # Створюємо дебаг файл
    # save_debug_html(soup)

    try:
        # 1. Парсинг цінового слайдера
        slider = soup.find('div', class_='match-price-range-slider')
        tgq_tag = soup.find(class_=re.compile(r'(t-g-q|total-models-count|preset-text)'))

        if tgq_tag:
            clean_text = tgq_tag.text.replace('\xa0', ' ').replace('&nbsp;', ' ')
            match = re.search(r'(\d+)', clean_text)
            if match:
                result["total_items"] = int(match.group(1))

        if slider and slider.has_attr('data-options'):
            try:
                options = json.loads(slider['data-options'])
                result["price_pool"]["min"] = int(options.get("range_min", 0))
                result["price_pool"]["max"] = int(options.get("range_max", 0))
            except:
                pass

        # 2. FALLBACK: Якщо ціни 0
        if result["price_pool"]["max"] == 0:
            min_p = _get_price_from_sorting(katalog_id, 'price')
            max_p = _get_price_from_sorting(katalog_id, 'price_desc')
            if min_p: result["price_pool"]["min"] = min_p
            if max_p: result["price_pool"]["max"] = max_p

        # 3. ФІЛЬТРИ БІЧНОЇ ПАНЕЛІ (З ДЕБАГ-ЛОГУВАННЯМ)
        filter_headers = soup.find_all('div', class_=re.compile(r'h2'))
        print(f"\n[DEBUG] Знайдено {len(filter_headers)} заголовків фільтрів.")

        for header in filter_headers:
            filter_name = header.text.strip()
            print(f"--- Аналіз фільтра: '{filter_name}' ---")

            if not filter_name:
                print("  [SKIP] Порожня назва.")
                continue

            # Знаходимо ID контейнера
            target_id = header.get('jclose')
            target_container = None

            if target_id:
                target_container = soup.find(id=target_id)
                print(f"  [LOG] Пошук по ID '{target_id}': {'ЗНАЙДЕНО' if target_container else 'НЕ ЗНАЙДЕНО'}")

            # Якщо по ID не знайшли, беремо просто наступний блок
            if not target_container:
                target_container = header.find_next_sibling(['div', 'ul'], class_=re.compile(r'(list-wrap|list)'))
                print(f"  [LOG] Пошук по sibling: {'ЗНАЙДЕНО' if target_container else 'НЕ ЗНАЙДЕНО'}")

            if target_container:
                # Визначаємо, чи контейнер вже є списком <ul>, чи список всередині нього
                if target_container.name == 'ul':
                    ul_tag = target_container
                else:
                    ul_tag = target_container.find('ul', class_=re.compile(r'list'))

                if ul_tag:
                    options = []
                    # Збираємо текст
                    lis = ul_tag.find_all('li')
                    print(f"  [LOG] Знайдено <li> тегів: {len(lis)}")

                    for li in lis:
                        label = li.find('label')
                        if label:
                            opt_text = label.text.strip()
                            if opt_text:
                                options.append(opt_text)
                        else:
                            # Спробуємо взяти текст з самого <li>, якщо label немає
                            text = li.text.strip()
                            if text:
                                options.append(text)
                                print(f"  [WARN] Знайдено текст у <li> без <label>: {text}")

                    if options:
                        result["sidebar_filters"][filter_name] = list(dict.fromkeys(options))
                        print(f"  [SUCCESS] Додано {len(options)} опцій.")
                    else:
                        print(f"  [FAIL] Контейнер знайдено, але опцій всередині 0.")
                else:
                    print(f"  [FAIL] Контейнер знайдено, але <ul> всередині не знайдено.")
            else:
                print(f"  [FAIL] Не вдалося знайти ніякого контейнера для цього фільтра.")

        # 4. Парсинг товарів (Основний)
        title_containers = soup.find_all(['div', 'td', 'span', 'a'],
                                         class_=re.compile(r'(model-short-title|model-name|product-title)'))

        if not title_containers:
            title_containers = soup.find_all('div',
                                             class_=re.compile(r'(model-short-block|model-short-div|product-card)'))

        for container in title_containers:
            title_tag = container if container.name == 'a' else container.find('a')
            if not title_tag: continue

            name = title_tag.text.strip()
            if not name or len(name) < 2: continue

            container_parent = container.find_parent(['div', 'tr', 'table', 'article']) or container
            price_tag = container_parent.find(['div', 'span', 'td', 'a'],
                                              class_=re.compile(r'(model-price-range|price|pr35|range)'))

            if not price_tag:
                price_tag = container_parent.find(text=re.compile(r'грн'))

            price = price_tag.text if hasattr(price_tag, 'text') else (str(price_tag) if price_tag else "Ціна відсутня")
            price = price.replace('\xa0', ' ').strip()

            if not any(p["name"] == name for p in result["products"]):
                result["products"].append({"name": name, "price_range": price})

        # 5. РЕЗЕРВНИЙ ЗАХИСТ ТОВАРІВ
        if not result["products"]:
            for a in soup.find_all('a', href=re.compile(r'(/prices/|/model.php|/desc/)')):
                name = a.text.strip()
                if name and len(name) > 5 and not any(
                        bad in name.lower() for bad in ["відгуки", "опис", "купити", "ціни", "характеристики"]):
                    container_parent = a.find_parent(['div', 'tr', 'td']) or a
                    price_tag = container_parent.find(text=re.compile(r'грн'))
                    price = price_tag.strip().replace('\xa0', ' ') if price_tag else "Ціна відсутня"
                    if not any(p["name"] == name for p in result["products"]):
                        result["products"].append({"name": name, "price_range": price})

        # Корекція лічильника
        if result["total_items"] == 0 and result["products"]:
            result["total_items"] = len(result["products"])

    except Exception as e:
        print(f"[CRITICAL ERROR] Парсинг категорії не вдався: {e}")

    return result


def parse_compact_grid(katalog_id, min_price=None, max_price=None, page=0):
    """
    [ПОВНІСТЮ ДИНАМІЧНИЙ] Збирає товари з компактної безрекламної сітки (list_view_type_=4).
    Працює з будь-яким ID категорії, отриманим з state.
    """
    # Формуємо лінк суто на основі переданого katalog_id
    url = f"https://ek.ua/ua/ek-list.php?katalog_={katalog_id}&list_view_type_=4"
    if page > 0:
        url += f"&page_={page}"
    if min_price is not None:
        url += f"&minPrice_={min_price}"
    if max_price is not None:
        url += f"&maxPrice_={max_price}"

    # Безпечне отримання через Playwright-сесію
    soup, _ = _get_soup(url)
    if not soup:
        return {"products": []}

    products = []
    tiles = soup.find_all("div", class_="tile-wrapper")

    for tile in tiles:
        name_tag = tile.find("div", class_="tile-name")
        name = name_tag.get_text(strip=True) if name_tag else "Невідомий товар"

        price = 0.0
        price_div = tile.find("div", class_="model-price-range")
        if price_div:
            price_span = price_div.find("span", id=lambda x: x and x.startswith("price_"))
            if price_span:
                price_str = re.sub(r"\s+", "", price_span.get_text(strip=True))
                try:
                    price = float(price_str)
                except ValueError:
                    price = 0.0

        features = []
        features_div = tile.find("div", class_="m-s-f2")
        if features_div:
            features_text = features_div.get_text(strip=True)
            features = [f.strip().lower() for f in features_text.split(",") if f.strip()]

        products.append({
            "name": name,
            "price": price,
            "features": features
        })

    return {"products": products}
