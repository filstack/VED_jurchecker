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
