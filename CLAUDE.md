# Claude Code Context: JurChecker

**Project**: JurChecker - Russian Legal Entity Detection API
**Language**: Python 3.10+
**Framework**: FastAPI
**Deployment**: uvicorn on port 8001

---

## Tech Stack

### Core Dependencies
- **FastAPI** 0.115.0 - REST API framework
- **uvicorn** 0.30.0 - ASGI server
- **pandas** 2.2.0 - CSV registry loading
- **pyahocorasick** 2.1.0 - Aho-Corasick automaton for fast text search
- **pydantic** 2.9.0 - Request/response validation

### New Dependencies (Dictionary Expansion Feature)
- **pymorphy3** ~1.2.0 - Russian morphological analysis for surname case declensions
- **petrovich** ~1.0.0 - Russian name declension and diminutive mappings
- **transliterate** ~1.10.0 - Cyrillic→Latin phonetic transliteration

---

## Architecture

### Main Components

**`jur_checker.py`**: Core service class
- `JurChecker` - Main class for entity detection
  - `_load_and_prepare_data()` - Loads CSV, builds Aho-Corasick automaton, **ENHANCED** with alias expansion
  - `_load_from_cache()` / `_save_to_cache()` - Pickle cache management with CSV hash validation
  - `find_raw_candidates()` - Searches text for entity mentions with word boundary validation

- `AliasExpander` (NEW) - Internal class for alias variant generation
  - `expand_all()` - Main entry point for generating all alias types
  - `expand_name_orders()` - First Last / Last First variants
  - `expand_initials()` - I. Last / I.P. Last variants
  - `expand_morphological_forms()` - Russian case declensions via pymorphy3
  - `expand_diminutives()` - Diminutive name forms via petrovich
  - `expand_transliterations()` - Cyrillic→Latin phonetic conversion
  - `normalize_alias()` - ё→е, lowercase, whitespace cleanup
  - `prioritize_aliases()` - Truncates to max 100 aliases per entity

**`main.py`**: FastAPI application
- POST `/check-candidates` - Accepts `{"text": str}`, returns candidate matches
- GET `/health` - Service health check
- Startup event handler loads JurChecker once

### Data Flow

```
CSV Registry (registry_entities_rows.csv)
  ↓ pandas.read_csv()
JurChecker._load_and_prepare_data()
  ↓ for each entity
AliasExpander.expand_all()
  ↓ generates name orders, initials, cases, diminutives, transliterations
  ↓ normalizes, deduplicates, prioritizes (max 100 per entity)
Aho-Corasick Automaton
  ↓ pickle cache
.cache/registry_entities_rows_automaton.pkl
  ↓ on query
find_raw_candidates(text)
  ↓ return
POST /check-candidates response
```

---

## Recent Changes

### 2025-10-06: Dictionary Alias Expansion (Feature 001)
Added automatic alias generation during dictionary build to improve entity detection recall:
- **Name order variants**: "Имя Фамилия" ↔ "Фамилия Имя"
- **Initial forms**: "И. Фамилия", "И.О. Фамилия"
- **Morphological case forms**: All 6 Russian cases (genitive, dative, accusative, instrumental, prepositional) via pymorphy3
- **Diminutive forms**: "Алексей" → "Лёша", "Леша", "Алекс" via petrovich dictionaries
- **Transliterations**: Simplified phonetic Cyrillic→Latin (Навальный → Navalny, Юрий → Yuri)
- **Performance**: All expansion at build time (zero query-time impact), <2 min build constraint
- **Limits**: Max 100 aliases per entity with priority-based truncation
- **Logging**: Per-entity alias counts, fallback warnings, performance warnings

---

## Key Design Patterns

### Separation of Concerns
- `JurChecker` handles search infrastructure (automaton, caching, query processing)
- `AliasExpander` handles variant generation (morphology, transliteration, normalization)

### Performance Optimization
- **Build-time expansion**: All alias generation happens offline during dictionary load
- **Persistent caching**: Expanded automaton cached via pickle with CSV hash validation
- **Single initialization**: pymorphy3 analyzer initialized once, reused across all entities

### Constitutional Compliance
- **Production Stability**: No API contract changes, backward compatible
- **Performance & Caching**: Existing cache mechanism preserves <100ms query time
- **Data Integrity**: CSV single source of truth, normalization applied consistently
- **API Contract Stability**: Zero changes to FastAPI endpoints or Pydantic models
- **Minimal Dependencies**: Only 3 new libraries, all justified and security-reviewed

---

## File Locations

```
D:\00_dev\01_Ведомости\Юрчекер\law_ch/
├── jur_checker.py           # Core service + AliasExpander class
├── main.py                  # FastAPI app (no changes from expansion feature)
├── requirements.txt         # Dependencies (updated with pymorphy3, petrovich, transliterate)
├── registry_entities_rows.csv  # CSV registry (1.3MB, ~1000s entities)
├── .cache/                  # Pickle cache for automaton
│   ├── registry_entities_rows_automaton.pkl
│   └── registry_entities_rows_hash.txt
├── specs/                   # Feature specifications
│   └── 001-dictionary-expansion/
│       ├── spec.md          # Feature spec (clarified)
│       ├── plan.md          # Implementation plan
│       ├── research.md      # Library research
│       ├── data-model.md    # AliasExpander class design
│       ├── quickstart.md    # Manual testing procedure
│       └── contracts/       # Method contracts
└── tests/                   # Test suite (NEW)
    ├── contract/            # Contract tests (TDD)
    ├── integration/         # Integration tests
    └── unit/                # Unit tests
```

---

## Development Workflow

### Testing Approach (TDD)
1. Write contract tests (must fail initially)
2. Implement method
3. Run tests until pass
4. Refactor

### Build Process
1. Edit `registry_entities_rows.csv` (if adding entities)
2. Delete `.cache/` to force rebuild
3. Run `uvicorn main:app --port 8001` → triggers dictionary build
4. Check logs for build time (<2 min) and alias counts
5. Test API with `POST /check-candidates`

### Performance Requirements
- **Dictionary build**: <2 minutes (warn at 90s)
- **Query response**: <100ms for typical text
- **Alias limit**: Max 100 per entity

---

## Common Tasks

### Add New Entity to Registry
Edit `registry_entities_rows.csv`:
```csv
NEW_ID,Имя Отчество Фамилия,person,"[]"
```
Restart service (cache invalidates automatically via hash check).

### Debug Morphological Expansion
```python
import pymorphy3
morph = pymorphy3.MorphAnalyzer()
parsed = morph.parse("Навальный")
for form in parsed[0].lexeme:
    print(form.word, form.tag)
```

### Check Alias Expansion for Entity
Review logs during startup:
```
Entity XYZ123: 47 aliases generated
```
or enable DEBUG logging for detailed alias list.

---

## Integration Points

### n8n Workflow Integration
- JurChecker exposes REST API consumed by n8n HTTP nodes
- Response format stable (Pydantic validation)
- Alias expansion transparent to n8n (more matches, same schema)

### Deployment
- Platform: Python 3.10+ server (Linux/Windows)
- Port: 8001 (uvicorn)
- Process management: Single process with startup event handler
- Health check: GET /health for monitoring

---

**Last Updated**: 2025-10-06 (Dictionary Expansion feature planning complete)
