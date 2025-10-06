# Data Model: Dictionary Alias Expansion

**Feature**: 001-dictionary-expansion
**Date**: 2025-10-06
**Purpose**: Define the AliasExpander class structure and its integration with JurChecker

---

## Overview

This feature introduces a new internal class `AliasExpander` within `jur_checker.py` that encapsulates all alias generation logic. The existing `JurChecker` class is modified minimally to integrate alias expansion during the dictionary build phase (`_load_and_prepare_data` method).

**Design Principle**: Separation of concerns—`JurChecker` handles search infrastructure (automaton, caching), while `AliasExpander` handles variant generation.

---

## Entity: AliasExpander (NEW)

**Location**: `jur_checker.py` (same file as JurChecker, internal class)

**Purpose**: Generate all alias variants for an entity name during dictionary build time.

### Fields

```python
class AliasExpander:
    """
    Generates searchable alias variants for entity names.

    Handles: name orders, initials, morphological forms, diminutives, transliterations.
    Implements: FR-001 through FR-021.
    """

    morph_analyzer: pymorphy3.MorphAnalyzer
    """Morphological analyzer for Russian case declensions (initialized once)"""

    diminutive_map: dict[str, list[str]]
    """Lookup table: formal_first_name → [diminutive_variants]"""

    max_aliases: int
    """Maximum aliases per entity (default 100, per FR-016a)"""

    alias_priority: dict[str, int]
    """Variant type → priority weight mapping for truncation (FR-016b)"""

    logger: logging.Logger
    """Logger instance for alias counts, warnings, fallbacks"""
```

### Constructor

```python
def __init__(self, max_aliases: int = 100):
    """
    Initialize AliasExpander with morphological analyzer and name dictionaries.

    Args:
        max_aliases: Maximum aliases per entity (FR-016a)

    Performance:
        Initialization takes ~2-3 seconds (library loading).
        Call ONCE in JurChecker.__init__() or _load_and_prepare_data().
    """
    self.max_aliases = max_aliases
    self.logger = logging.getLogger(__name__)

    # Initialize pymorphy3 (heavy operation, do once)
    self.morph_analyzer = pymorphy3.MorphAnalyzer()

    # Build diminutive lookup from petrovich or hardcoded map
    self.diminutive_map = self._build_diminutive_map()

    # Priority weights for alias types (FR-016b)
    self.alias_priority = {
        'original': 100,
        'morphological': 90,
        'name_order': 80,
        'initial': 80,
        'diminutive': 60,
        'transliteration': 40,
    }

    self.logger.info("AliasExpander initialized with max_aliases=%d", max_aliases)
```

### Methods

#### Main Entry Point

```python
def expand_all(self, entity_name: str, entity_type: str) -> list[str]:
    """
    Generate all alias variants for an entity.

    Args:
        entity_name: Full entity name from CSV (e.g., "Алексей Анатольевич Навальный")
        entity_type: Entity type (e.g., "person", "organization")

    Returns:
        List of normalized, deduplicated aliases (length ≤ max_aliases)

    Side Effects:
        - Logs alias count at INFO level (FR-017)
        - Logs WARNING if alias limit exceeded (FR-016b)
        - Logs WARNING if morphological fallback applied (FR-018)

    Implementation Flow:
        1. Parse name (if person type)
        2. Generate all variant types
        3. Normalize all variants
        4. Deduplicate
        5. Prioritize and truncate to max_aliases
        6. Log results
        7. Return final list
    """
    pass  # Implementation in Phase 4
```

#### Name Parsing

```python
def parse_person_name(self, name: str) -> tuple[str, str | None, str]:
    """
    Parse Russian full name into components.

    Args:
        name: Full name string

    Returns:
        (first_name, patronymic_or_none, last_name)

    Parsing Rules:
        - 1 part: (name, None, name) - treat as both first and last
        - 2 parts: (first, None, last) - no patronymic
        - 3 parts: (first, patronymic, last) - standard Russian full name
        - 4+ parts: (joined_first, second_to_last, last) - handle multiple given names

    Examples:
        "Навальный" → ("Навальный", None, "Навальный")
        "Алексей Навальный" → ("Алексей", None, "Навальный")
        "Алексей Анатольевич Навальный" → ("Алексей", "Анатольевич", "Навальный")
        "Анна Мария Петровна Иванова" → ("Анна Мария", "Петровна", "Иванова")
    """
    pass  # Implementation in Phase 4
```

#### Name Order Variants (FR-001, FR-004)

```python
def expand_name_orders(
    self,
    first: str,
    patronymic: str | None,
    last: str
) -> list[str]:
    """
    Generate name order variants.

    Args:
        first: First name
        patronymic: Patronymic (may be None)
        last: Last name

    Returns:
        List of name order variants (not normalized yet)

    Variants Generated:
        - "First Last" (if patronymic is None)
        - "Last First" (if patronymic is None)
        - "First Patronymic Last" (full name, always included - FR-004)
        - "Last First" (if patronymic present, omit patronymic)

    Examples:
        ("Алексей", None, "Навальный") →
            ["Алексей Навальный", "Навальный Алексей"]

        ("Алексей", "Анатольевич", "Навальный") →
            ["Алексей Анатольевич Навальный", "Алексей Навальный", "Навальный Алексей"]
    """
    pass  # Implementation in Phase 4
```

#### Initial Variants (FR-002, FR-003)

```python
def expand_initials(
    self,
    first: str,
    patronymic: str | None,
    last: str
) -> list[str]:
    """
    Generate initial variants.

    Args:
        first: First name
        patronymic: Patronymic (may be None)
        last: Last name

    Returns:
        List of initial variants (not normalized yet)

    Variants Generated (single initial, FR-002):
        - "I. Last" (e.g., "А. Навальный")
        - "Last I." (e.g., "Навальный А.")

    Variants Generated (double initial, FR-003, only if patronymic present):
        - "I.P. Last" (e.g., "А.А. Навальный")
        - "Last I.P." (e.g., "Навальный А.А.")

    Examples:
        ("Алексей", None, "Навальный") →
            ["А. Навальный", "Навальный А."]

        ("Алексей", "Анатольевич", "Навальный") →
            ["А. Навальный", "Навальный А.", "А.А. Навальный", "Навальный А.А."]
    """
    pass  # Implementation in Phase 4
```

#### Diminutive Forms (FR-005)

```python
def expand_diminutives(self, first_name: str) -> list[str]:
    """
    Get diminutive variants for a first name.

    Args:
        first_name: Russian first name

    Returns:
        List of diminutive forms (empty if none found)

    Uses:
        self.diminutive_map (built from petrovich or hardcoded)

    Examples:
        "Алексей" → ["Лёша", "Леша", "Алекс", "Лёха", "Алёша"]
        "Владимир" → ["Вова", "Вовка", "Володя"]
        "Петр" → [] (no diminutives in map)
    """
    normalized = first_name.lower()
    return self.diminutive_map.get(normalized, [])
```

#### Transliteration (FR-006, FR-007)

```python
def expand_transliterations(self, variants: list[str]) -> list[str]:
    """
    Generate Latin transliterations for Cyrillic variants.

    Args:
        variants: List of Cyrillic name variants (already generated)

    Returns:
        List of transliterated (Latin) variants

    Uses:
        transliterate library with simplified phonetic mode

    Examples:
        ["Навальный", "А. Навальный", "Алексей Навальный"] →
            ["navalny", "a. navalny", "aleksey navalny"]

        ["Юрий"] → ["yuriy"] (phonetic: yu not iu)

    Error Handling:
        - Skip variants that fail transliteration (e.g., already Latin, mixed script)
        - Do not log errors (transliteration failures are expected for mixed content)
    """
    pass  # Implementation in Phase 4
```

#### Morphological Case Forms (FR-011, FR-012)

```python
def expand_morphological_forms(self, surname: str) -> list[str]:
    """
    Generate all Russian case forms for a surname using pymorphy3.

    Args:
        surname: Last name to decline

    Returns:
        List of case forms (lowercase), or empty if parsing fails

    Uses:
        self.morph_analyzer.parse().lexeme for all inflected forms

    Cases Generated:
        - Nominative (original)
        - Genitive (кого? чего?)
        - Dative (кому? чему?)
        - Accusative (кого? что?)
        - Instrumental (кем? чем?)
        - Prepositional (о ком? о чём?)

    Examples:
        "Навальный" → ["навальный", "навального", "навальному", "навальным", "навальном"]

    Fallback:
        If pymorphy3 confidence < 0.5 or parsing fails:
        - Call apply_heuristic_fallback() (FR-013)
        - Do NOT return empty list; return heuristic forms
    """
    pass  # Implementation in Phase 4
```

#### Heuristic Fallback (FR-013, FR-013a, FR-018)

```python
def apply_heuristic_fallback(self, surname: str, entity_id: str = "") -> list[str]:
    """
    Apply manual suffix heuristics when morphological analysis fails.

    Args:
        surname: Last name that failed morphology
        entity_id: Entity ID for warning log (FR-018)

    Returns:
        List of surname + heuristic suffixes

    Heuristic Suffixes:
        -ого (genitive)
        -ому (dative)
        -ым  (instrumental)
        -ом  (prepositional)

    Side Effects:
        Logs WARNING with entity ID and name (FR-013a, FR-018, FR-020)

    Examples:
        "Müller" → ["müller", "müllerого", "müllerому", "müllerым", "müllerом"]

    Log Message:
        WARNING: "Morphological fallback for entity {entity_id}, surname='{surname}'"
    """
    pass  # Implementation in Phase 4
```

#### Normalization (FR-008, FR-009, FR-010)

```python
def normalize_alias(self, alias: str) -> str:
    """
    Normalize alias for consistent automaton insertion.

    Args:
        alias: Raw alias variant

    Returns:
        Normalized alias (lowercase, ё→е, whitespace cleaned)

    Normalization Steps:
        1. ё → е (FR-009)
        2. Lowercase (FR-010)
        3. Replace [\s\.\-]+ with single space (FR-008)
        4. Trim leading/trailing whitespace

    Examples:
        "Алексей   Навальный" → "алексей навальный"
        "А.  А.   Навальный" → "а а навальный"
        "Алёша-Лёша" → "алеша леша"
        "НАВАЛЬНЫЙ" → "навальный"
    """
    pass  # Implementation in Phase 4
```

#### Prioritization & Truncation (FR-016a, FR-016b, FR-021)

```python
def prioritize_aliases(
    self,
    aliases: list[str],
    original: str,
    entity_id: str = ""
) -> list[str]:
    """
    Select top N aliases by priority when total exceeds max_aliases.

    Args:
        aliases: All generated aliases (may be >max_aliases)
        original: Original entity name (for logging)
        entity_id: Entity ID (for logging)

    Returns:
        Top max_aliases by priority

    Priority Order (FR-016b):
        1. Original name (100)
        2. Morphological case forms (90)
        3. Name order variants + initials (80)
        4. Diminutive forms (60)
        5. Transliterations (40)

    Side Effects:
        Logs WARNING if truncation occurs (FR-016b):
        "Entity {entity_id} exceeded alias limit ({len} generated, {max} kept)"

    Algorithm:
        1. Assign priority score to each alias based on type detection
        2. Sort by score descending, then alphabetically (stability)
        3. Take top max_aliases
        4. Log warning if truncated
    """
    pass  # Implementation in Phase 4
```

#### Helper: Build Diminutive Map

```python
def _build_diminutive_map(self) -> dict[str, list[str]]:
    """
    Build lookup table for first name → diminutives.

    Returns:
        Dictionary mapping formal names to diminutive lists

    Sources:
        - petrovich library's name database (if API accessible)
        - Hardcoded common names (fallback)

    Examples:
        {
            "алексей": ["лёша", "леша", "алекс", "лёха", "алёша"],
            "владимир": ["вова", "вовка", "володя"],
            ...
        }
    """
    # Implementation: Access petrovich data or use hardcoded map
    # See research.md for pattern
    pass  # Implementation in Phase 4
```

---

## Entity: JurChecker (MODIFIED)

**Location**: `jur_checker.py`

**Changes**: Integrate `AliasExpander` into dictionary build phase.

### Modified Method: `_load_and_prepare_data()`

```python
def _load_and_prepare_data(self, csv_path: str) -> dict:
    """
    Загружает данные из CSV, парсит псевдонимы и наполняет
    автомат Ахо-Корасик для быстрого поиска. Каждое ключевое слово
    (имя или псевдоним) будет указывать на полную информацию о сущности.

    MODIFIED: Now generates expanded aliases using AliasExpander.

    Args:
        csv_path (str): Путь к CSV-файлу.

    Returns:
        dict: Словарь для быстрого доступа к данным сущности по ключевому слову.

    Changes:
        1. Initialize AliasExpander once before loop
        2. Start build timer for performance tracking (FR-021)
        3. For each entity: call expander.expand_all() to get variants
        4. Add all expanded aliases to automaton
        5. Log alias count per entity (FR-017)
        6. After loop: log total build time, warn if >90s (FR-021)
    """
    import time
    from .alias_expander import AliasExpander  # Internal import

    logger.info(f"Загрузка и обработка реестра из файла: {csv_path}...")

    # NEW: Initialize expander (heavy operation, do once)
    expander = AliasExpander(max_aliases=100)

    # NEW: Start build timer
    build_start_time = time.time()

    entity_map = {}

    try:
        df = pd.read_csv(csv_path)
    except FileNotFoundError:
        logger.error(f"Файл {csv_path} не найден.")
        return entity_map

    total_aliases_count = 0

    for index, row in df.iterrows():
        entity_data = row.to_dict()
        entity_id = entity_data.get('id', f'unknown_{index}')
        entity_name = str(entity_data.get('name', '')).strip()
        entity_type = entity_data.get('type', 'unknown')

        if not entity_name:
            continue  # Skip empty names

        # NEW: Generate expanded aliases
        aliases = expander.expand_all(entity_name, entity_type)

        # Add all aliases to automaton
        for alias in aliases:
            self.automaton.add_word(alias, (alias, entity_data))
            entity_map[alias] = entity_data

        total_aliases_count += len(aliases)

        # NEW: Log alias count per entity (FR-017)
        logger.info(f"Entity {entity_id}: {len(aliases)} aliases generated")

    # NEW: Calculate build time
    build_time = time.time() - build_start_time

    # NEW: Log total dictionary size and build time (FR-019)
    logger.info(
        f"Реестр успешно загружен. {total_aliases_count} ключевых слов добавлено в поисковый движок. "
        f"Build time: {build_time:.2f} seconds"
    )

    # NEW: Warn if approaching 2-minute limit (FR-021)
    if build_time > 90:
        logger.warning(
            f"Dictionary build time ({build_time:.2f}s) approaching 2-minute limit (120s)"
        )

    return entity_map
```

### Unchanged Methods

All other `JurChecker` methods remain unchanged:
- `__init__()` - No changes needed
- `_load_from_cache()` - Unchanged (cache format compatible)
- `_save_to_cache()` - Unchanged (saves expanded automaton transparently)
- `_get_csv_hash()` - Unchanged
- `_normalize_text()` - Unchanged (still used for query normalization)
- `find_raw_candidates()` - Unchanged (works with expanded automaton seamlessly)

**Backward Compatibility**: Existing API contracts preserved. Cache files will simply contain more entries (expanded aliases), but structure remains identical.

---

## Data Entities Summary

| Entity | Type | Purpose | Location |
|--------|------|---------|----------|
| **AliasExpander** | NEW class | Generate alias variants during build | `jur_checker.py` |
| **JurChecker** | MODIFIED class | Integrate alias expansion | `jur_checker.py` (existing) |
| **Entity** | Data record | CSV registry entry (unchanged) | `registry_entities_rows.csv` |
| **Alias Variant** | String | Generated searchable form | In-memory during build, stored in automaton cache |

---

## Relationships

```
CSV Registry (registry_entities_rows.csv)
    ↓ loaded by
JurChecker._load_and_prepare_data()
    ↓ calls for each entity
AliasExpander.expand_all(name, type)
    ↓ generates
List[str] (aliases)
    ↓ normalized & added to
Aho-Corasick Automaton
    ↓ cached to
.cache/registry_entities_rows_automaton.pkl
```

---

## State Transitions

**Build Phase** (offline, happens once on startup or cache miss):
```
START
  → Initialize AliasExpander (load libraries)
  → For each CSV entity:
      → Parse name
      → Generate variants (orders, initials, diminutives, transliterations, cases)
      → Normalize all variants
      → Deduplicate
      → Prioritize & truncate to 100
      → Add to automaton
      → Log alias count
  → Finalize automaton
  → Cache to pickle
  → Log total build time
END
```

**Query Phase** (online, happens on each API request):
```
START (unchanged from current implementation)
  → Normalize query text
  → Search automaton (find_raw_candidates)
  → Validate word boundaries
  → Extract context
  → Return candidates
END
```

**No state changes in query phase**—all alias expansion is precomputed.

---

## Validation Rules

### Entity-Level Validations

1. **Name must not be empty** (skip entity if name is blank)
2. **Entity type determines expansion**:
   - "person" → apply all expansion types
   - "organization" → skip diminutives, apply only name orders and morphology
3. **Maximum 100 aliases per entity** (FR-016a)—enforced by `prioritize_aliases()`

### Alias-Level Validations

1. **Normalization mandatory** (FR-008, FR-009, FR-010)—every alias passes through `normalize_alias()`
2. **Deduplication required**—use `set()` to remove normalized duplicates before prioritization
3. **Non-empty after normalization**—skip any alias that normalizes to empty string

### Build-Time Validations

1. **Total build time <2 minutes** (FR-016c)—logged, not enforced (feature may exceed if data grows)
2. **Performance warning at 90 seconds** (FR-021)—logged as WARNING
3. **Morphological fallback logged** (FR-018, FR-020)—every heuristic application generates WARNING

---

## Logging Specifications

### INFO Level (FR-017, FR-019)

```
"AliasExpander initialized with max_aliases=100"
"Entity TEST001: 47 aliases generated"
"Реестр успешно загружен. 50234 ключевых слов добавлено в поисковый движок. Build time: 67.34 seconds"
```

### WARNING Level (FR-018, FR-021, FR-016b)

```
"Morphological fallback for entity TEST001, surname='Müller'"
"Entity TEST123 exceeded alias limit (150 generated, 100 kept)"
"Dictionary build time (93.12s) approaching 2-minute limit (120s)"
```

### ERROR Level

No new error conditions introduced. Existing error handling preserved:
- File not found → HTTP 503 (existing)
- Cache corruption → Fall back to full rebuild (existing)

---

**Next**: See contracts/alias_expander.md for method-level contracts and test specifications
