"""
Объединение результатов массового тестирования из двух батчей
"""
import json
from collections import Counter

# Загружаем результаты batch 1 и batch 2
with open('test_results.json', 'r', encoding='utf-8') as f:
    batch1 = json.load(f)

with open('test_results_batch2.json', 'r', encoding='utf-8') as f:
    batch2 = json.load(f)

# Объединяем счетчики
entity_counter = Counter(batch1['top_entities'])
entity_counter.update(batch2['top_entities'])

alias_counter = Counter(batch1['top_aliases'])
alias_counter.update(batch2['top_aliases'])

# Объединяем детальные результаты
all_results = batch1['detailed_results'] + batch2['detailed_results']

# Вычисляем общую статистику
total_texts = batch1['summary']['total_texts'] + batch2['summary']['total_texts']
total_matches = batch1['summary']['total_matches'] + batch2['summary']['total_matches']
texts_with_matches = batch1['summary']['texts_with_matches'] + batch2['summary']['texts_with_matches']
unique_entities = len(entity_counter)
avg_time = (batch1['summary']['avg_time_ms'] + batch2['summary']['avg_time_ms']) / 2

# Выводим объединённую статистику
print("=" * 80)
print("ОБЪЕДИНЁННЫЕ РЕЗУЛЬТАТЫ МАССОВОГО ТЕСТИРОВАНИЯ")
print("=" * 80)
print(f"\n[SUMMARY] ОБЩАЯ СТАТИСТИКА:")
print(f"  Всего текстов протестировано: {total_texts}")
print(f"  Всего совпадений найдено: {total_matches}")
print(f"  Текстов с совпадениями: {texts_with_matches}/{total_texts} ({texts_with_matches/total_texts*100:.1f}%)")
print(f"  Уникальных сущностей: {unique_entities}")
print(f"  Среднее время на текст: {avg_time:.0f}мс")

print(f"\n[TOP] ТОП-20 найденных сущностей:")
for entity, count in entity_counter.most_common(20):
    print(f"    {count:3d}x {entity[:80]}")

print(f"\n[ALIASES] ТОП-30 найденных алиасов:")
for alias, count in alias_counter.most_common(30):
    print(f"    {count:3d}x '{alias}'")

# Анализ ложных срабатываний
print(f"\n[WARNING] АНАЛИЗ ЛОЖНЫХ СРАБАТЫВАНИЙ:")

single_word = [(alias, count) for alias, count in alias_counter.items()
               if ' ' not in alias and '.' not in alias]

print(f"\n  Однословные алиасы (ТОП-30, высокий риск ложных срабатываний):")
for alias, count in sorted(single_word, key=lambda x: -x[1])[:30]:
    print(f"    {count:3d}x '{alias}'")

frequent = [(alias, count) for alias, count in alias_counter.items()
            if count >= 10]

print(f"\n  Очень частые алиасы (>=10 раз, проверьте вручную):")
for alias, count in sorted(frequent, key=lambda x: -x[1])[:30]:
    print(f"    {count:3d}x '{alias}'")

# Сохраняем объединённые результаты
merged = {
    'summary': {
        'total_texts': total_texts,
        'total_matches': total_matches,
        'texts_with_matches': texts_with_matches,
        'unique_entities': unique_entities,
        'avg_time_ms': avg_time
    },
    'top_entities': dict(entity_counter.most_common(50)),
    'top_aliases': dict(alias_counter.most_common(100)),
    'detailed_results': all_results
}

with open('test_results_merged.json', 'w', encoding='utf-8') as f:
    json.dump(merged, f, ensure_ascii=False, indent=2)

print("\n" + "=" * 80)
print("[SAVED] Объединённые результаты сохранены в: test_results_merged.json")
print("=" * 80)
