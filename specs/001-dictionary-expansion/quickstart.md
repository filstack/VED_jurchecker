# Quickstart: Manual Testing for Dictionary Alias Expansion

**Feature**: 001-dictionary-expansion
**Date**: 2025-10-06
**Purpose**: Manual testing procedure to verify alias expansion works correctly in production-like environment

---

## Overview

This quickstart guide provides step-by-step instructions for manually testing the dictionary alias expansion feature after implementation. It serves as the **acceptance validation** procedure before considering the feature complete.

**Prerequisites:**
- Feature implemented (AliasExpander class integrated into jur_checker.py)
- New dependencies installed (pymorphy3, petrovich, transliterate)
- Test entity added to CSV registry

---

## Step 1: Prepare Test Data

### 1.1 Add Test Entity to CSV

Edit `registry_entities_rows.csv` and add a test entity at the end:

```csv
TEST001,Алексей Анатольевич Навальный,person,"[]"
```

**Fields:**
- `id`: TEST001 (unique test identifier)
- `name`: Алексей Анатольевич Навальный (full Russian name with patronymic)
- `type`: person
- `aliases`: `"[]"` (empty JSON array, expansion will generate aliases)

**Why this entity?**
- Full three-part Russian name (tests name order, initials, patronymics)
- Common first name "Алексей" has known diminutives (Лёша, Леша, Алекс)
- Surname "Навальный" has rich morphology (all 6 Russian cases)
- Transliteration is unambiguous (Navalny, Alexey)

### 1.2 Delete Existing Cache

Force a full dictionary rebuild by removing cache files:

```bash
# Windows
del .cache\registry_entities_rows_automaton.pkl
del .cache\registry_entities_rows_hash.txt

# Linux/Mac
rm .cache/registry_entities_rows_automaton.pkl
rm .cache/registry_entities_rows_hash.txt
```

**Why delete cache?**
- Ensures the new alias expansion logic runs
- Validates build-time performance (should complete in <2 minutes)

---

## Step 2: Start the Service

### 2.1 Launch with Logging Enabled

```bash
python -m uvicorn main:app --port 8001 --reload --log-level info
```

**Expected behavior during startup:**
- Logs show: `"AliasExpander initialized with max_aliases=100"`
- Logs show: `"Загрузка и обработка реестра из файла: registry_entities_rows.csv..."`
- For each entity, logs show: `"Entity <id>: <count> aliases generated"` (FR-017)
- Final log shows: `"Реестр успешно загружен. X ключевых слов добавлено в поисковый движок. Build time: Y.YY seconds"` (FR-019)
- Final log shows: `"Сервис ЮРЧЕКЕР: поисковый движок построен с нуля и готов к работе."`

### 2.2 Verify Startup Logs

**Check for:**

✅ **INFO logs**:
```
AliasExpander initialized with max_aliases=100
Entity TEST001: 47 aliases generated
...
Реестр успешно загружен. 52347 ключевых слов добавлено в поисковый движок. Build time: 67.34 seconds
```

✅ **Build time <2 minutes** (FR-016c):
- If build time >90 seconds: expect WARNING log (FR-021):
  ```
  WARNING: Dictionary build time (93.12s) approaching 2-minute limit (120s)
  ```

✅ **No ERROR logs** during startup

⚠️ **WARNING logs** (expected for some entities):
```
WARNING: Morphological fallback for entity XYZ, surname='Müller'
WARNING: Entity ABC exceeded alias limit (150 generated, 100 kept)
```

**If build time >120 seconds**: FAIL—performance requirement violated (FR-016c)

---

## Step 3: Verify API Functionality

### 3.1 Health Check

```bash
curl http://localhost:8001/health
```

**Expected Response:**
```json
{"status": "ok"}
```

### 3.2 Test Original Name (Baseline)

```bash
curl -X POST http://localhost:8001/check-candidates \
  -H "Content-Type: application/json" \
  -d "{\"text\": \"Встреча с Алексеем Анатольевичем Навальным состоялась вчера\"}"
```

**Expected Response:**
```json
{
  "candidates": [
    {
      "entity_id": "TEST001",
      "entity_name": "Алексей Анатольевич Навальный",
      "entity_type": "person",
      "found_alias": "алексеем анатольевичем навальным",
      "context": "...Встреча с Алексеем Анатольевичем Навальным состоялась вчера..."
    }
  ]
}
```

✅ **Pass if:** TEST001 found with correct context

---

### 3.3 Test Morphological Case Form (Instrumental Case)

```bash
curl -X POST http://localhost:8001/check-candidates \
  -H "Content-Type: application/json" \
  -d "{\"text\": \"Интервью с Навальным было опубликовано\"}"
```

**Expected Response:**
```json
{
  "candidates": [
    {
      "entity_id": "TEST001",
      "entity_name": "Алексей Анатольевич Навальный",
      "entity_type": "person",
      "found_alias": "навальным",
      "context": "...Интервью с Навальным было опубликовано..."
    }
  ]
}
```

✅ **Pass if:** "Навальным" (instrumental case) matches TEST001
❌ **Fail if:** No candidates found → morphological expansion not working

---

### 3.4 Test Genitive Case Form

```bash
curl -X POST http://localhost:8001/check-candidates \
  -H "Content-Type: application/json" \
  -d "{\"text\": \"Дело Навального получило огласку\"}"
```

**Expected Response:**
```json
{
  "candidates": [
    {
      "entity_id": "TEST001",
      "found_alias": "навального",
      "context": "...Дело Навального получило огласку..."
    }
  ]
}
```

✅ **Pass if:** "Навального" (genitive case) matches TEST001

---

### 3.5 Test Initial Variant (Single Initial)

```bash
curl -X POST http://localhost:8001/check-candidates \
  -H "Content-Type: application/json" \
  -d "{\"text\": \"А. Навальный выступил на конференции\"}"
```

**Expected Response:**
```json
{
  "candidates": [
    {
      "entity_id": "TEST001",
      "found_alias": "а. навальный",
      "context": "...А. Навальный выступил на конференции..."
    }
  ]
}
```

✅ **Pass if:** "А. Навальный" matches TEST001
❌ **Fail if:** No match → initial expansion not working

---

### 3.6 Test Double Initial Variant

```bash
curl -X POST http://localhost:8001/check-candidates \
  -H "Content-Type: application/json" \
  -d "{\"text\": \"Заявление А.А. Навального\"}"
```

**Expected Response:**
```json
{
  "candidates": [
    {
      "entity_id": "TEST001",
      "found_alias": "а.а. навального",
      "context": "...Заявление А.А. Навального..."
    }
  ]
}
```

✅ **Pass if:** "А.А. Навального" matches (combines double initial + genitive case)

---

### 3.7 Test Transliteration (Latin)

```bash
curl -X POST http://localhost:8001/check-candidates \
  -H "Content-Type: application/json" \
  -d "{\"text\": \"Interview with Alexey Navalny was published\"}"
```

**Expected Response:**
```json
{
  "candidates": [
    {
      "entity_id": "TEST001",
      "found_alias": "alexey navalny",
      "context": "...Interview with Alexey Navalny was published..."
    }
  ]
}
```

✅ **Pass if:** "Alexey Navalny" (transliteration) matches TEST001
❌ **Fail if:** No match → transliteration expansion not working

---

### 3.8 Test Transliteration (Surname Only)

```bash
curl -X POST http://localhost:8001/check-candidates \
  -H "Content-Type: application/json" \
  -d "{\"text\": \"Navalny's statement was released\"}"
```

**Expected Response:**
```json
{
  "candidates": [
    {
      "entity_id": "TEST001",
      "found_alias": "navalny",
      "context": "...Navalny's statement was released..."
    }
  ]
}
```

✅ **Pass if:** "Navalny" matches TEST001

---

### 3.9 Test Diminutive Form

```bash
curl -X POST http://localhost:8001/check-candidates \
  -H "Content-Type: application/json" \
  -d "{\"text\": \"Леша приехал на встречу\"}"
```

**Expected Response:**
```json
{
  "candidates": [
    {
      "entity_id": "TEST001",
      "found_alias": "леша",
      "context": "...Леша приехал на встречу..."
    }
  ]
}
```

✅ **Pass if:** "Леша" (diminutive of Алексей) matches TEST001
❌ **Fail if:** No match → diminutive expansion not working

**Note:** This test assumes "Леша" is in the diminutive map for "Алексей". If not, try "Лёша" or "Алекс".

---

### 3.10 Test Name Order Reversal

```bash
curl -X POST http://localhost:8001/check-candidates \
  -H "Content-Type: application/json" \
  -d "{\"text\": \"Навальный Алексей был арестован\"}"
```

**Expected Response:**
```json
{
  "candidates": [
    {
      "entity_id": "TEST001",
      "found_alias": "навальный алексей",
      "context": "...Навальный Алексей был арестован..."
    }
  ]
}
```

✅ **Pass if:** "Навальный Алексей" (Last First order) matches TEST001

---

## Step 4: Verify Backward Compatibility

### 4.1 Test Existing Entity (Pre-Expansion)

Choose an existing entity from the registry (not TEST001) and search for it using its **original name** from the CSV.

```bash
# Example: if CSV has entity "Владимир Путин"
curl -X POST http://localhost:8001/check-candidates \
  -H "Content-Type: application/json" \
  -d "{\"text\": \"Выступление Владимира Путина\"}"
```

**Expected:**
- Entity should still be found (backward compatibility)
- May now also match case forms (e.g., "Путина" genitive)

✅ **Pass if:** Existing entities still findable
❌ **Fail if:** Previously-working entities no longer match → regression

---

## Step 5: Verify Performance & Logging

### 5.1 Check Build Time (FR-016c)

Review startup logs for build time:

```
Реестр успешно загружен. X ключевых слов добавлено в поисковый движок. Build time: 67.34 seconds
```

✅ **Pass if:** Build time <120 seconds (2 minutes)
⚠️ **Warning if:** Build time >90 seconds (should see WARNING log per FR-021)
❌ **Fail if:** Build time >120 seconds

### 5.2 Check Alias Counts (FR-017)

Review logs for per-entity alias counts:

```
Entity TEST001: 47 aliases generated
Entity XYZ123: 23 aliases generated
Entity ABC456: 100 aliases generated  ← At limit
```

✅ **Pass if:** Alias counts logged for all entities at INFO level

### 5.3 Check Warning Logs (FR-018, FR-021, FR-016b)

Review logs for expected warnings:

**Morphological fallback** (FR-018):
```
WARNING: Morphological fallback for entity FOREIGN_001, surname='Müller'
```

**Alias limit exceeded** (FR-016b):
```
WARNING: Entity COMPLEX_NAME exceeded alias limit (150 generated, 100 kept)
```

**Build time warning** (FR-021, if applicable):
```
WARNING: Dictionary build time (93.12s) approaching 2-minute limit (120s)
```

✅ **Pass if:** Warnings present for edge cases (foreign names, complex names)

---

## Step 6: Verify Cache Functionality

### 6.1 Restart Service (Cache Hit)

Stop the service (Ctrl+C) and restart:

```bash
python -m uvicorn main:app --port 8001 --reload --log-level info
```

**Expected logs:**
```
Кэш успешно загружен из D:\...\law_ch\.cache\registry_entities_rows_automaton.pkl
Сервис ЮРЧЕКЕР: поисковый движок загружен из кэша и готов к работе.
```

✅ **Pass if:** Startup is fast (<5 seconds), cache loaded successfully
❌ **Fail if:** Full rebuild happens again (cache invalidation broken)

### 6.2 Modify CSV (Cache Invalidation)

Edit `registry_entities_rows.csv`: add a new test entity or modify existing one.

Restart service.

**Expected logs:**
```
Кэш устарел (CSV изменился), будет выполнена полная загрузка.
...
Сервис ЮРЧЕКЕР: поисковый движок построен с нуля и готов к работе.
```

✅ **Pass if:** Cache invalidation detected, full rebuild triggered
❌ **Fail if:** Stale cache used (changes not reflected)

---

## Step 7: Test Alias Limit Edge Case

### 7.1 Add Complex Entity

Add entity with very long compound name to CSV:

```csv
LIMIT_TEST,Анна Мария Виктория Петровна Александровна Иванова-Смирнова-Петрова,person,"[]"
```

### 7.2 Restart Service

**Expected logs:**
```
Entity LIMIT_TEST: 100 aliases generated
WARNING: Entity LIMIT_TEST exceeded alias limit (237 generated, 100 kept)
```

✅ **Pass if:** Limit enforced (exactly 100 aliases), WARNING logged
❌ **Fail if:** >100 aliases generated or no warning logged

---

## Acceptance Criteria Summary

| Criterion | Test Step | Pass Condition |
|-----------|-----------|----------------|
| **Build time <2 min** | 5.1 | Build completes in <120s |
| **No ERROR logs** | 2.2 | Startup clean, no errors |
| **Morphological forms work** | 3.3, 3.4 | Case variants match |
| **Initials work** | 3.5, 3.6 | Initial variants match |
| **Transliterations work** | 3.7, 3.8 | Latin variants match |
| **Diminutives work** | 3.9 | Diminutive forms match |
| **Name orders work** | 3.10 | Reversed name order matches |
| **Backward compatibility** | 4.1 | Existing entities still findable |
| **Cache invalidation** | 6.2 | CSV changes trigger rebuild |
| **Alias limit enforced** | 7.2 | Max 100 aliases, warning logged |
| **Logging complete** | 5.2, 5.3 | Alias counts and warnings logged |

**Feature is COMPLETE when all criteria PASS.**

---

## Troubleshooting

### Issue: Build time >2 minutes

**Possible causes:**
- CSV is very large (>10,000 entities)
- Morphological analysis slow (pymorphy3 initialization overhead)
- Diminutive map is too large

**Solutions:**
- Profile with `cProfile` to identify bottleneck
- Consider async build process (constitutional change required)
- Optimize prioritization algorithm (reduce complexity)

### Issue: Morphological forms not matching

**Possible causes:**
- pymorphy3 not installed
- Morphological confidence threshold too high
- Fallback heuristics not applied

**Debug:**
- Check logs for `"Morphological fallback for entity..."` warnings
- Manually test pymorphy3: `morph.parse("Навальный")[0].lexeme`
- Verify heuristic suffixes applied when morphology fails

### Issue: Transliterations not matching

**Possible causes:**
- transliterate library not installed
- Custom transliteration mapping not configured
- Transliteration returning ISO 9 format instead of phonetic

**Debug:**
- Manually test: `translit("Юрий", 'ru', reversed=True)` → should be "Yuriy" not "Iurii"
- Check if simplified phonetic mode configured correctly

### Issue: Cache always rebuilding

**Possible causes:**
- CSV hash calculation broken
- Cache files not being written
- File permissions issue

**Debug:**
- Check `.cache/` directory exists and is writable
- Verify `registry_entities_rows_hash.txt` contains valid MD5 hash
- Check logs for cache save errors

---

## Next Steps

After all acceptance criteria pass:
1. Run automated contract tests: `pytest tests/contract/`
2. Run integration tests: `pytest tests/integration/`
3. Performance profiling if build time >60s
4. Ready for `/tasks` command to generate detailed task breakdown

**Status**: Manual quickstart validation complete → Proceed to automated testing
