#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для регенерации всех алиасов в CSV с новым морфологическим склонением словосочетаний.

Использует обновленный AliasExpander с функцией expand_phrase_morphology для генерации
форм типа "правого сектора", "украинской организации" и т.д.
"""

import sys
sys.stdout.reconfigure(encoding='utf-8')

import pandas as pd
import json
from jur_checker import AliasExpander
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

CSV_PATH = 'registry_entities_rows.csv'
BACKUP_PATH = 'registry_entities_rows.csv.backup'

def regenerate_aliases():
    """
    Регенерирует алиасы для всех записей в CSV.
    """
    logger.info(f"Загрузка CSV: {CSV_PATH}")
    df = pd.read_csv(CSV_PATH, encoding='utf-8')

    logger.info(f"Найдено {len(df)} записей")

    # Создаем backup
    logger.info(f"Создание backup: {BACKUP_PATH}")
    df.to_csv(BACKUP_PATH, index=False, encoding='utf-8')

    # Инициализируем AliasExpander
    logger.info("Инициализация AliasExpander...")
    expander = AliasExpander(max_aliases=100)

    # Счетчики
    total_aliases_before = 0
    total_aliases_after = 0
    updated_count = 0
    error_count = 0

    # Обрабатываем каждую запись
    for idx, row in df.iterrows():
        entity_id = row['id']
        entity_name = row['name']
        entity_type = row['type']

        # Подсчитываем старые алиасы
        old_aliases = []
        if pd.notna(row['aliases']) and row['aliases']:
            try:
                old_aliases = json.loads(row['aliases'])
                total_aliases_before += len(old_aliases)
            except (json.JSONDecodeError, TypeError):
                logger.warning(f"Не удалось распарсить старые алиасы для {entity_id}")

        try:
            # Генерируем новые алиасы с морфологией
            new_aliases = expander.expand_all(entity_name, entity_type)

            # Сохраняем в JSON формат
            df.at[idx, 'aliases'] = json.dumps(new_aliases, ensure_ascii=False)

            total_aliases_after += len(new_aliases)
            updated_count += 1

            # Логируем изменения
            if len(new_aliases) != len(old_aliases):
                logger.info(
                    f"[{idx+1}/{len(df)}] {entity_name[:50]}... "
                    f"({entity_type}): {len(old_aliases)} → {len(new_aliases)} алиасов"
                )

            # Прогресс каждые 100 записей
            if (idx + 1) % 100 == 0:
                logger.info(f"Обработано: {idx+1}/{len(df)} записей")

        except Exception as e:
            logger.error(f"Ошибка при обработке {entity_id}: {e}")
            error_count += 1

    # Сохраняем обновленный CSV
    logger.info(f"Сохранение обновленного CSV: {CSV_PATH}")
    df.to_csv(CSV_PATH, index=False, encoding='utf-8')

    # Статистика
    logger.info("\n" + "="*60)
    logger.info("РЕЗУЛЬТАТЫ РЕГЕНЕРАЦИИ:")
    logger.info("="*60)
    logger.info(f"Обработано записей: {updated_count}/{len(df)}")
    logger.info(f"Ошибок: {error_count}")
    logger.info(f"Алиасов ДО:  {total_aliases_before:,}")
    logger.info(f"Алиасов ПОСЛЕ: {total_aliases_after:,}")
    logger.info(f"Изменение: {total_aliases_after - total_aliases_before:+,} ({(total_aliases_after / max(total_aliases_before, 1) - 1) * 100:+.1f}%)")
    logger.info("="*60)
    logger.info(f"\n✅ Backup сохранен: {BACKUP_PATH}")
    logger.info(f"✅ Обновленный CSV: {CSV_PATH}")

    return updated_count, error_count

if __name__ == '__main__':
    logger.info("Начало регенерации алиасов...")
    logger.info("Это может занять несколько минут...")
    print()

    try:
        updated, errors = regenerate_aliases()

        if errors > 0:
            logger.warning(f"\n⚠️  Завершено с {errors} ошибками")
            sys.exit(1)
        else:
            logger.info("\n✅ Регенерация успешно завершена!")
            sys.exit(0)

    except KeyboardInterrupt:
        logger.warning("\n❌ Прервано пользователем")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\n❌ Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
