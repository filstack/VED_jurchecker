# JurChecker - Система проверки текстов на упоминания из реестров РФ

API для автоматического поиска упоминаний лиц и организаций из реестров РФ (иноагенты, экстремисты, нежелательные организации).

## Возможности

- 🔍 **Автоматическое расширение алиасов** - генерирует ~40 вариантов написания каждого имени
- 📝 **Морфология** - находит падежи (Навальный → Навального, Навальному)
- 🔤 **Инициалы** - распознаёт А. Навальный, А.А. Навальный
- 🌐 **Транслитерация** - находит латинские варианты (Navalny)
- ⚡ **Быстрый поиск** - Aho-Corasick автомат с кэшированием
- 🎯 **Уменьшительные имена** - Александр → Саша, Алексей → Лёша

## Быстрый старт

### Установка

```bash
# Клонируйте репозиторий
git clone https://github.com/your-username/jurchecker.git
cd jurchecker

# Создайте виртуальное окружение
python3.10 -m venv .venv
source .venv/bin/activate  # Linux/Mac
# или .venv\Scripts\activate  # Windows

# Установите зависимости
pip install -r requirements.txt
```

### Запуск сервера

```bash
# Запустите FastAPI сервер
uvicorn main:app --host 0.0.0.0 --port 8000

# Сервер доступен по адресу:
# http://localhost:8000
```

### Использование API

**Проверка текста:**

```bash
curl -X POST "http://localhost:8000/check-candidates" \
  -H "Content-Type: application/json" \
  -d '{"text": "Дело Навального рассматривали в суде"}'
```

**Ответ:**

```json
{
  "candidates": [
    {
      "entity_id": "...",
      "entity_name": "Общественное движение Штабы Навального",
      "entity_type": "экстремисты",
      "found_alias": "навального",
      "context": "Дело Навального рассматривали в суде"
    }
  ]
}
```

### Health Check

```bash
curl http://localhost:8000/health
```

## Структура проекта

```
jurchecker/
├── main.py                          # FastAPI сервер
├── jur_checker.py                   # Основная логика + AliasExpander
├── search.py                        # Пример использования
├── requirements.txt                 # Зависимости
├── registry_entities_rows.csv       # База данных сущностей
├── tests/                           # Тесты
│   ├── contract/                    # Юнит-тесты методов
│   └── integration/                 # Интеграционные тесты
└── specs/                           # Документация и спецификации
```

## Формат CSV

Файл `registry_entities_rows.csv` должен содержать:

```csv
id,name,type,required_markup,markup_phrase,legal_basis,done
uuid-1,Иванов Иван Иванович,иноагенты,true,внесён в реестр...,ч. 2.1 ст. 13.15,true
```

**Обязательные колонки:**
- `id` - уникальный идентификатор
- `name` - полное имя сущности
- `type` - тип (иноагенты, экстремисты, нежелательные)

## Автоматическое расширение алиасов

Для имени **"Алексей Навальный"** автоматически генерируются:

**Порядки имени:**
- Алексей Навальный
- Навальный Алексей

**Инициалы:**
- А. Навальный
- Навальный А.

**Морфология (падежи):**
- навального, навальному, навальным, навальном

**Транслитерация:**
- navalny, a. navalny, aleksey navalny

**Уменьшительные:**
- лёша, леша, алекс

**Итого:** ~40-70 вариантов на каждое имя!

## Observability - Метрики и Телеметрия

Система включает встроенные инструменты мониторинга качества алиасов и отслеживания совпадений.

### Build-time метрики

При загрузке реестра автоматически логируются метрики качества алиасов для каждой сущности:

```
ALIAS_METRICS: entity_id=test-1 entity_type=иноагенты alias_count=42 single_word_count=3 is_person=True collision_count=0
```

**Предупреждения о проблемных алиасах:**

- `SINGLE_WORD_ALIAS` - однословные алиасы от имён людей (высокий риск ложных срабатываний)
- `COMMON_WORD_ALIAS` - алиасы совпадающие с частыми русскими словами (очень высокий риск)
- `ALIAS_COLLISION` - алиасы, встречающиеся в >5 сущностях (риск неоднозначности)

### Production телеметрия (опционально)

Включите логирование совпадений для анализа и оптимизации:

```bash
# Включить телеметрию
export ENABLE_MATCH_LOGGING=true

# Настроить хранение логов (по умолчанию 30 дней)
export LOG_RETENTION_DAYS=90
```

**Формат логов:** `.logs/matches-{YYYY-MM-DD}.jsonl`

```json
{
  "timestamp": "2025-01-15T14:30:00.000Z",
  "alias": "навального",
  "entity_id": "uuid-123",
  "entity_name": "Алексей Навальный",
  "entity_type": "экстремисты",
  "context": "Дело Навального рассматривали в суде..."
}
```

**Политика хранения:**
- Контекст обрезается до 300 символов (конфиденциальность)
- Старые логи удаляются автоматически при старте сервиса
- Логи не пишутся по умолчанию (opt-in)

### Режимы строгости (ALIAS_STRICTNESS)

Управляйте компромиссом между полнотой и точностью:

```bash
# Строгий режим (по умолчанию) - меньше ложных срабатываний
export ALIAS_STRICTNESS=strict

# Сбалансированный режим
export ALIAS_STRICTNESS=balanced

# Агрессивный режим - максимальное покрытие
export ALIAS_STRICTNESS=aggressive
```

**Эффект режимов:**
- Каждый режим создаёт отдельный кэш автомата
- Смена режима инициирует пересборку с другими стратегиями
- Режим отображается в `/health` endpoint:

```json
{
  "status": "ok",
  "alias_mode": "strict"
}
```

### Конфигурация через переменные окружения

| Переменная | Значение по умолчанию | Описание |
|------------|----------------------|----------|
| `ALIAS_STRICTNESS` | `strict` | Режим строгости алиасов (strict/balanced/aggressive) |
| `ENABLE_MATCH_LOGGING` | `false` | Включить телеметрию совпадений |
| `LOG_RETENTION_DAYS` | `30` | Срок хранения логов совпадений (дни) |

**Пример systemd сервиса с observability:**

```ini
[Service]
Environment="ALIAS_STRICTNESS=strict"
Environment="ENABLE_MATCH_LOGGING=true"
Environment="LOG_RETENTION_DAYS=90"
```

## Производительность

- **Первый запуск:** ~1-2 секунды для 1000 сущностей
- **Последующие запуски:** <1 секунда (загрузка из кэша)
- **Кэш:** `.cache/registry_entities_rows_automaton.pkl`
- **Поиск:** <100мс для текста любого размера

## Деплой на сервер

### Systemd сервис

Создайте `/etc/systemd/system/jurchecker.service`:

```ini
[Unit]
Description=JurChecker API Service
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/jurchecker
Environment="PATH=/opt/jurchecker/.venv/bin"
ExecStart=/opt/jurchecker/.venv/bin/uvicorn main:app --host 0.0.0.0 --port 8001
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Запустите:

```bash
sudo systemctl daemon-reload
sudo systemctl enable jurchecker
sudo systemctl start jurchecker
sudo systemctl status jurchecker
```

## Тестирование

```bash
# Запустите все тесты
pytest tests/ -v

# Только контрактные тесты
pytest tests/contract/ -v

# Только интеграционные тесты
pytest tests/integration/ -v
```

**Покрытие:** 37/37 тестов ✅

## Технологии

- **Python 3.10+**
- **FastAPI** - веб-фреймворк
- **pymorphy3** - морфологический анализатор
- **petrovich** - русские уменьшительные имена
- **transliterate** - транслитерация кириллицы
- **pyahocorasick** - быстрый поиск подстрок

## Лицензия

MIT

## Автор

Проект разработан для автоматизации проверки текстов на упоминания из реестров РФ.
