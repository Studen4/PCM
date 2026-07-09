from bs4 import BeautifulSoup


def find_element_by_text(html_content, target_text):
    soup = BeautifulSoup(html_content, 'html.parser')

    # Шукаємо елемент, який містить наш текст
    # Використовуємо lambda, щоб знайти елемент з точним текстом
    elements = soup.find_all(string=lambda text: text and target_text in text)

    for element in elements:
        parent = element.parent
        print(f"✅ Знайдено: '{element.strip()}'")
        print(f"--- Шлях до елемента (Parents) ---")

        # Проходимо по батьківським елементам, щоб побачити структуру
        for i, p in enumerate(parent.parents):
            if i > 5: break  # Виводимо тільки 5 рівнів вгору
            classes = p.get('class', [])
            tag_info = f"<{p.name}"
            if classes: tag_info += f" class='{' '.join(classes)}'"
            if p.get('id'): tag_info += f" id='{p.get('id')}'"
            tag_info += ">"
            print(f"Рівень {i}: {tag_info}")
        print("-" * 30)