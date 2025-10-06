from jur_checker import JurChecker
import sys

# Исправление кодировки для Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# Укажите путь к вашему CSV
checker = JurChecker(csv_path="registry_entities_rows.csv")

# Укажите текст для проверки
text = """
Дело Навального рассматривали в суде.
А. Навальный выступил.
Navalny mentioned in article.
Захаров Андрей работает.
"""

# Поиск
matches = checker.find_raw_candidates(text)

# Вывод результатов
print(f"\nНайдено совпадений: {len(matches)}\n")

for match in matches:
    print(f"[OK] Найдено: {match['entity_name']}")
    print(f"     Вариант: {match['found_alias']}")
    print(f"     Тип: {match['entity_type']}")
    print()
