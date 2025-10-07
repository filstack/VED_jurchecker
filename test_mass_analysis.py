"""
Массовое тестирование JurChecker на реальных данных из Excel
Сравнивает текущий алгоритм на реальных текстах
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import openpyxl
import requests
import json
from collections import Counter
import time

# API endpoint (remote server)
API_URL = "http://93.189.231.235:8021/check-candidates"

def load_texts_from_excel(filepath, max_texts=50):
    """Загружает тексты из Excel файла"""
    print(f"[FILE] Открываю файл: {filepath}")
    wb = openpyxl.load_workbook(filepath, read_only=True)
    sheet = wb.active

    texts = []
    for row_idx, row in enumerate(sheet.iter_rows(min_row=2, values_only=True), start=2):
        if len(texts) >= max_texts:
            break

        # Берем текст из 6-й колонки (индекс 5) - там основной контент
        if len(row) > 5 and row[5]:
            text = str(row[5])
            if len(text) > 50:  # Минимум 50 символов
                texts.append({
                    'row': row_idx,
                    'text': text[:5000],  # Обрезаем очень длинные тексты
                    'length': len(text)
                })

    print(f"[OK] Загружено {len(texts)} текстов")
    print(f"[STAT] Средняя длина: {sum(t['length'] for t in texts) / len(texts):.0f} символов")
    return texts

def test_current_api(texts):
    """Тестирует текущий API"""
    print("\n[TEST] ТЕКУЩИЙ АЛГОРИТМ (готовые алиасы из CSV)")

    results = []
    entity_counter = Counter()
    alias_counter = Counter()
    total_time = 0

    for idx, item in enumerate(texts, 1):
        text = item['text']

        try:
            start = time.time()
            response = requests.post(API_URL, json={"text": text}, timeout=10)
            elapsed = time.time() - start
            total_time += elapsed

            if response.status_code == 200:
                data = response.json()
                # API returns {"candidates": [...]}
                candidates = data.get('candidates', [])

                results.append({
                    'row': item['row'],
                    'found_count': len(candidates),
                    'entities': [c['entity_name'] for c in candidates],
                    'aliases': [c['found_alias'] for c in candidates],
                    'time': elapsed
                })

                # Статистика
                for c in candidates:
                    entity_counter[c['entity_name']] += 1
                    alias_counter[c['found_alias']] += 1

                if idx % 10 == 0:
                    print(f"  Обработано: {idx}/{len(texts)}")
            else:
                print(f"  [ERROR] Ошибка в строке {item['row']}: HTTP {response.status_code}")

        except Exception as e:
            print(f"  [ERROR] Ошибка в строке {item['row']}: {e}")

    # Итоговая статистика
    total_matches = sum(r['found_count'] for r in results)
    texts_with_matches = sum(1 for r in results if r['found_count'] > 0)

    print(f"\n[RESULTS] ИТОГИ:")
    print(f"  Всего совпадений: {total_matches}")
    print(f"  Текстов с совпадениями: {texts_with_matches}/{len(texts)} ({texts_with_matches/len(texts)*100:.1f}%)")
    print(f"  Уникальных сущностей: {len(entity_counter)}")
    print(f"  Среднее время на текст: {total_time/len(texts)*1000:.0f}мс")

    print(f"\n[TOP] ТОП-10 найденных сущностей:")
    for entity, count in entity_counter.most_common(10):
        print(f"    {count:3d}x {entity[:80]}")

    print(f"\n[ALIASES] ТОП-10 найденных алиасов:")
    for alias, count in alias_counter.most_common(10):
        print(f"    {count:3d}x '{alias}'")

    return {
        'results': results,
        'total_matches': total_matches,
        'texts_with_matches': texts_with_matches,
        'unique_entities': len(entity_counter),
        'entity_counter': entity_counter,
        'alias_counter': alias_counter,
        'avg_time_ms': total_time/len(texts)*1000
    }

def analyze_false_positives(results):
    """Анализирует потенциальные ложные срабатывания"""
    print(f"\n[WARNING] АНАЛИЗ ПОТЕНЦИАЛЬНЫХ ЛОЖНЫХ СРАБАТЫВАНИЙ:")

    # Однословные алиасы - высокий риск
    single_word = [alias for alias, count in results['alias_counter'].items()
                   if ' ' not in alias and '.' not in alias]

    if single_word:
        print(f"\n  Однословные алиасы (риск ложных срабатываний):")
        for alias in single_word[:15]:
            count = results['alias_counter'][alias]
            print(f"    {count:3d}x '{alias}'")

    # Частые алиасы - могут быть общие слова
    frequent = [(alias, count) for alias, count in results['alias_counter'].items()
                if count >= 5]

    if frequent:
        print(f"\n  Частые алиасы (>=5 раз, проверьте вручную):")
        for alias, count in sorted(frequent, key=lambda x: -x[1])[:10]:
            print(f"    {count:3d}x '{alias}'")

def main():
    print("=" * 80)
    print("МАССОВОЕ ТЕСТИРОВАНИЕ JURCHECKER")
    print("=" * 80)

    # Загружаем тексты
    texts = load_texts_from_excel("output (2).xlsx", max_texts=20)

    if not texts:
        print("[ERROR] Не удалось загрузить тексты из файла")
        return

    # Тестируем текущий алгоритм
    current_results = test_current_api(texts)

    # Анализируем ложные срабатывания
    analyze_false_positives(current_results)

    print("\n" + "=" * 80)
    print("[DONE] ТЕСТИРОВАНИЕ ЗАВЕРШЕНО")
    print("=" * 80)

    # Сохраняем детальные результаты
    with open('test_results.json', 'w', encoding='utf-8') as f:
        json.dump({
            'summary': {
                'total_texts': len(texts),
                'total_matches': current_results['total_matches'],
                'texts_with_matches': current_results['texts_with_matches'],
                'unique_entities': current_results['unique_entities'],
                'avg_time_ms': current_results['avg_time_ms']
            },
            'top_entities': dict(current_results['entity_counter'].most_common(20)),
            'top_aliases': dict(current_results['alias_counter'].most_common(20)),
            'detailed_results': current_results['results']
        }, f, ensure_ascii=False, indent=2)

    print(f"\n[SAVED] Детальные результаты сохранены в: test_results.json")

if __name__ == "__main__":
    main()
