import math
import sys
import os

# Додаємо кореневу директорію в sys.path, щоб імпорти скраперів працювали коректно
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from scraper.salary_parser import get_normalized_salary
from scraper.ekatalog_parser import parse_category_page


def calculate_price_categories(W, P_min, P_max, gamma=0.5):
    # ... (Твоя логіка залишається без змін) ...
    if P_max / P_min < 1.5:
        cut_percent = 0.0
        P_max_adjusted = P_max
        S = 1.0
    elif P_min >= W:
        cut_percent = 0.10
        P_max_adjusted = max(P_min * 1.5, P_max * (1 - cut_percent))
        R = P_max_adjusted / P_min
        A = P_max_adjusted / W
        S = 1 + gamma * math.log10(R) * math.sqrt(A)
    else:
        K_max = P_max / W
        K_min = P_min / W
        order_max = math.floor(math.log10(K_max))
        order_min = math.floor(math.log10(K_min))
        power_diff = order_max - order_min
        K_min_scaled = K_min * (10 ** power_diff)
        ratio = min(1.0, K_min_scaled / K_max)
        cut_percent = 1 - ratio
        P_max_adjusted = P_max * (1 - cut_percent)
        if P_max_adjusted < P_min * 1.5:
            P_max_adjusted = min(P_max, P_min * 1.5)
            cut_percent = 1 - (P_max_adjusted / P_max)
        R = P_max_adjusted / P_min
        A = P_max_adjusted / W
        S = 1 + gamma * math.log10(R) * math.sqrt(A)

    weights = [i ** S for i in range(1, 6)]
    sum_weights = sum(weights)
    percentages = [(w / sum_weights) for w in weights]
    delta = P_max_adjusted - P_min
    boundaries = []
    current_price = P_min
    categories = ["Найдешевші", "Дешеві", "Стандартні", "Преміум", "Люкс"]
    for i in range(5):
        next_price = P_max if i == 4 else current_price + (delta * percentages[i])
        boundaries.append(
            {"category": categories[i], "start": current_price, "end": next_price, "percent": percentages[i] * 100})
        current_price = next_price
    return boundaries, cut_percent, P_max_adjusted, S


def get_price_zones(katalog_id, min_price=None, max_price=None):
    W = get_normalized_salary()
    # ВИКЛИК НОВОГО ПАРСЕРА
    ek_data = parse_category_page(katalog_id, min_price, max_price)

    P_min = min_price if min_price else (ek_data['price_pool']['min'] or 1.0)
    P_max = max_price if max_price else (ek_data['price_pool']['max'] or (P_min * 2))

    boundaries, cut, p_adj, s_factor = calculate_price_categories(W, P_min, P_max)
    return {
        "salary_w": W,
        "raw_min": P_min,
        "raw_max": P_max,
        "boundaries": boundaries,
        "metrics": {"cut_percent": cut, "adjusted_max": p_adj, "s_factor": s_factor}
    }


if __name__ == "__main__":
    # Тестовий запуск інтеграції
    print("--- Запуск інтегрованого аналізатора ---")
    query = "Акустичні гітари"
    # Для прикладу задамо ціни вручну, як у твоєму запиті
    result = get_price_zones(query, 5000, 125000)

    print(f"Робоча ЗП (W): {result['salary_w']} грн")
    print("\nРозподіл категорій:")
    for b in result['boundaries']:
        print(f"{b['category']}: {b['start']:,.0f} - {b['end']:,.0f} грн ({b['percent']:.1f}%)")
