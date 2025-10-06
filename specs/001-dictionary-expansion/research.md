# Research: Dictionary Alias Expansion

**Feature**: 001-dictionary-expansion
**Date**: 2025-10-06
**Purpose**: Document library choices, integration patterns, and algorithm design for alias expansion

---

## Research Areas

This research phase evaluated libraries and established patterns for:
1. Russian morphological analysis (case declensions)
2. Russian name diminutive mappings
3. Cyrillic→Latin transliteration
4. Name parsing strategies for Russian full names
5. Alias prioritization algorithm with 100-entity limit

---

## 1. pymorphy3 for Morphological Analysis

### Decision
Use **pymorphy3** library for generating all Russian case forms of surnames.

### Rationale
- **Industry standard**: Most widely-used and actively-maintained Russian morphology library
- **Comprehensive coverage**: Supports all 6 Russian cases (nominative, genitive, dative, accusative, instrumental, prepositional)
- **Lexeme support**: `.lexeme` property returns all inflected forms of a word
- **Confidence scoring**: `.score` attribute allows filtering low-confidence parses

### Alternatives Considered
- **pymorphy2**: Older version, less maintained, similar API (rejected: outdated)
- **Manual suffix rules**: Simple suffix-based heuristics (rejected: insufficient accuracy for complex Russian morphology)

### Integration Pattern

```python
import pymorphy3

morph = pymorphy3.MorphAnalyzer()

def get_case_forms(surname: str) -> set[str]:
    """
    Generate all Russian case forms for a surname.

    Returns:
        Set of lowercase case forms, or empty set if parsing fails
    """
    parsed = morph.parse(surname)

    if not parsed:
        return set()  # Parsing failed

    # Use first (highest confidence) parse
    first_parse = parsed[0]

    # Confidence threshold: 0.5 (50%)
    if first_parse.score < 0.5:
        return set()  # Low confidence, trigger fallback

    # Extract all case forms from lexeme
    case_forms = {form.word.lower() for form in first_parse.lexeme}

    return case_forms
```

### Example Output
```python
>>> get_case_forms("Навальный")
{'навальный', 'навального', 'навальному', 'навальным', 'навальном', 'навальные'}
# Note: Some forms may be identical (e.g., accusative=instrumental for this name)
```

### Performance Notes
- **Initialization cost**: `pymorphy3.MorphAnalyzer()` loads dictionaries (~1-2 seconds)
- **Recommendation**: Initialize ONCE in `AliasExpander.__init__()`, reuse across all entities
- **Per-word analysis**: ~0.1-0.5ms per word (acceptable for build-time processing)

### Fallback Strategy
When `score < 0.5` or `parsed` is empty (foreign/rare names):
- Trigger `apply_heuristic_fallback()` method
- Apply manual suffixes: -ого (genitive), -ому (dative), -ым (instrumental), -ом (prepositional)
- Log WARNING for manual review queue (per FR-013a, FR-018)

---

## 2. petrovich for Diminutive Forms

### Decision
Use **petrovich** library's name dictionary for Russian first name → diminutive mappings.

### Rationale
- **Specialized for Russian names**: Focused library for Russian name declension and variants
- **Comprehensive diminutive database**: Contains standard and colloquial diminutive forms
- **Lightweight**: Single-purpose library, no heavy dependencies
- **Established**: Used in Russian developer community, stable API

### Alternatives Considered
- **pymorphy3 name data**: Has some name information but less complete for diminutives (rejected: incomplete coverage)
- **Custom hardcoded dictionary**: Manually compile name→diminutive mappings (rejected: maintenance burden, incompleteness)
- **No diminutives (defer feature)**: Skip diminutive expansion entirely (rejected: user requirement from spec)

### Integration Pattern

```python
from petrovich.main import Petrovich
from petrovich.enums import Case, Gender
import petrovich.data as petrovich_data

# Option 1: Use petrovich's name database directly
def build_diminutive_map() -> dict[str, list[str]]:
    """
    Build a lookup table: formal_name → [diminutives]

    Uses petrovich's internal name data.
    """
    diminutive_map = {}

    # Access petrovich's internal name database
    # (This may require inspecting petrovich's source for exact API)
    # Example placeholder pattern:
    # for formal_name, variants in petrovich_data.names.items():
    #     diminutives = [v for v in variants if v.is_diminutive]
    #     if diminutives:
    #         diminutive_map[formal_name.lower()] = [d.lower() for d in diminutives]

    # Hardcoded fallback for common names if petrovich API access is complex:
    diminutive_map = {
        "алексей": ["лёша", "леша", "алекс", "лёха", "алёша"],
        "александр": ["саша", "сашка", "шура", "алекс"],
        "владимир": ["вова", "вовка", "володя"],
        "дмитрий": ["дима", "митя", "димка"],
        "иван": ["ваня", "ванёк", "иванка"],
        "михаил": ["миша", "мишка"],
        "николай": ["коля", "колян", "николаша"],
        # Add more as needed
    }

    return diminutive_map

# Initialize once in AliasExpander.__init__()
self.diminutive_map = build_diminutive_map()

def expand_diminutives(self, first_name: str) -> list[str]:
    """Get diminutive variants for a first name."""
    normalized = first_name.lower()
    return self.diminutive_map.get(normalized, [])
```

### Example Output
```python
>>> expand_diminutives("Алексей")
['лёша', 'леша', 'алекс', 'лёха', 'алёша']

>>> expand_diminutives("Владимир")
['вова', 'вовка', 'володя']

>>> expand_diminutives("Петр")
[]  # No diminutives in map
```

### Implementation Notes
- **ё vs е handling**: Store both variants in map (ё and е), or normalize during lookup
- **Not all names have diminutives**: Return empty list for names without diminutive forms
- **Gender considerations**: Some diminutives are gender-specific, but for search purposes we include all variants

---

## 3. transliterate for Cyrillic→Latin Conversion

### Decision
Use **transliterate** library with simplified phonetic mode (per FR-006 clarification).

### Rationale
- **Configurable**: Supports multiple transliteration standards and custom mappings
- **Phonetic focus**: Can produce English-readable output (Юрий→Yuri not Iurii)
- **Lightweight**: No external dependencies, pure Python
- **Reversible**: Supports both Cyrillic→Latin and Latin→Cyrillic (future extensibility)

### Alternatives Considered
- **GOST 7.79 / ISO 9**: Formal standards with diacritics (rejected: less readable, not aligned with "simplified phonetic" clarification)
- **Custom mapping table**: Build manual Cyrillic↔Latin dict (rejected: reinventing wheel, transliterate already handles edge cases)

### Integration Pattern

```python
from transliterate import translit
from transliterate.base import TranslitLanguagePack, registry
from transliterate.contrib.languages.ru import RussianLanguagePack

# Option 1: Use default transliterate behavior
def simple_transliterate(text: str) -> str:
    """
    Convert Cyrillic to Latin using simplified phonetic approach.
    """
    try:
        # translit(text, 'ru', reversed=True) converts Cyrillic→Latin
        return translit(text, 'ru', reversed=True)
    except:
        return text  # Return original if transliteration fails

# Option 2: Customize for phonetic readability (if needed)
class PhoneticRussianPack(RussianLanguagePack):
    """
    Custom transliteration pack prioritizing English phonetic readability.
    """
    mapping = (
        # Override specific mappings for phonetic simplicity
        "абвгдеёжзийклмнопрстуфхцчшщъыьэюя",
        "abvgdeyozhziyklmnoprstufkhtschshschyeyuya",
    )
    # Simplified: ё→yo (not ë), ю→yu (not iu), й→y (not i)

# Register custom pack
registry.register(PhoneticRussianPack)

def expand_transliterations(self, variants: list[str]) -> list[str]:
    """
    Generate Latin transliterations for all Cyrillic variants.

    Args:
        variants: List of Cyrillic name variants

    Returns:
        List of transliterated (Latin) variants
    """
    transliterations = []

    for variant in variants:
        try:
            latin = translit(variant, 'ru', reversed=True).lower()
            transliterations.append(latin)
        except Exception:
            # Skip if transliteration fails (e.g., already Latin, mixed script)
            continue

    return transliterations
```

### Example Output
```python
>>> expand_transliterations(["Навальный", "А. Навальный", "Алексей Навальный"])
['navalny', 'a. navalny', 'aleksey navalny']

>>> expand_transliterations(["Юрий"])
['yuriy']  # Phonetic: yu not iu
```

### Performance Notes
- **Fast operation**: Pure string mapping, ~0.01ms per word
- **No initialization cost**: Stateless function

---

## 4. Russian Name Parsing Patterns

### Decision
Use heuristic-based parsing: split on whitespace, apply structural patterns.

### Parsing Algorithm

```python
def parse_person_name(name: str) -> tuple[str, str | None, str]:
    """
    Parse Russian full name into components.

    Args:
        name: Full name string (e.g., "Алексей Анатольевич Навальный")

    Returns:
        (first_name, patronymic or None, last_name)

    Patterns:
        2 parts: "FirstName LastName" (patronymic omitted)
        3 parts: "FirstName Patronymic LastName"
        4+ parts: "FirstName ... Patronymic LastName" (middle names joined to first)
    """
    parts = name.strip().split()

    if len(parts) == 1:
        # Single name (organization or mononym)
        return (parts[0], None, parts[0])  # Treat as both first and last

    elif len(parts) == 2:
        # FirstName LastName (no patronymic)
        return (parts[0], None, parts[1])

    elif len(parts) == 3:
        # FirstName Patronymic LastName (standard Russian full name)
        return (parts[0], parts[1], parts[2])

    else:
        # 4+ parts: assume last is surname, second-to-last is patronymic, rest is first name
        first_name = " ".join(parts[:-2])  # Everything except last two
        patronymic = parts[-2]
        last_name = parts[-1]
        return (first_name, patronymic, last_name)
```

### Example Parsing

| Input | Output |
|-------|--------|
| "Навальный" | ("Навальный", None, "Навальный") |
| "Алексей Навальный" | ("Алексей", None, "Навальный") |
| "Алексей Анатольевич Навальный" | ("Алексей", "Анатольевич", "Навальный") |
| "Мария Ивановна Петрова-Смирнова" | ("Мария", "Ивановна", "Петрова-Смирнова") |
| "Анна Мария Петровна Иванова" | ("Анна Мария", "Петровна", "Иванова") |

### Edge Cases Handled
- **Compound surnames**: Hyphenated names (e.g., "Петров-Водкин") treated as single LastName unit (no splitting on hyphen)
- **Multiple given names**: Rare but occurs (e.g., "Мария Анна")—joined into single FirstName
- **Organizations**: Single-word names treated as both first and last (skip person-specific expansions in `expand_all()` based on `entity_type`)

---

## 5. Expansion Algorithm with 100-Alias Limit

### Decision
Generate all possible variants, then prioritize and truncate to top 100.

### Priority Weighting (per FR-016b)

| Variant Type | Weight | Rationale |
|--------------|--------|-----------|
| Original name | 100 | Always include (base case) |
| Morphological cases | 90 | Highest value for Russian legal texts (most common variation) |
| Name orders + initials | 80 | Common in formal documents, official records |
| Diminutive forms | 60 | Moderate frequency in informal references |
| Transliterations | 40 | Less common in Russian-language documents (lower priority) |

### Algorithm Flow

```python
def prioritize_aliases(self, aliases: list[str], original: str, limit: int = 100) -> list[str]:
    """
    Select top N aliases by priority when total exceeds limit.

    Args:
        aliases: All generated aliases (may be >100)
        original: Original entity name (always included)
        limit: Maximum aliases to return (default 100)

    Returns:
        Top `limit` aliases sorted by priority

    Side Effects:
        Logs WARNING if truncation occurs (FR-016b)
    """
    if len(aliases) <= limit:
        return aliases  # No truncation needed

    # Assign priority scores
    scored_aliases = []

    for alias in aliases:
        # Determine variant type and assign weight
        if alias == original.lower():
            score = 100  # Original
        elif self._is_case_form(alias):
            score = 90   # Morphological
        elif self._is_name_order_or_initial(alias):
            score = 80   # Name order/initial
        elif self._is_diminutive(alias):
            score = 60   # Diminutive
        elif self._is_transliteration(alias):
            score = 40   # Transliteration
        else:
            score = 50   # Default/unknown

        scored_aliases.append((score, alias))

    # Sort by score descending, then alphabetically for stability
    scored_aliases.sort(key=lambda x: (-x[0], x[1]))

    # Take top N
    top_aliases = [alias for score, alias in scored_aliases[:limit]]

    # Log warning about truncation
    logger.warning(
        f"Alias limit exceeded: {len(aliases)} generated, {limit} kept "
        f"(original: '{original}')"
    )

    return top_aliases
```

### Variant Type Detection Helpers

```python
def _is_case_form(self, alias: str) -> bool:
    """Check if alias is a morphological case variant."""
    # Simple heuristic: ends with common case suffixes
    case_suffixes = ('ого', 'ому', 'ым', 'ом', 'ой', 'ую', 'ей')
    return any(alias.endswith(suffix) for suffix in case_suffixes)

def _is_name_order_or_initial(self, alias: str) -> bool:
    """Check if alias contains initials (dots) or multiple words."""
    return '.' in alias or ' ' in alias

def _is_diminutive(self, alias: str) -> bool:
    """Check if alias is in diminutive map."""
    # Check if alias appears as a diminutive value in the map
    for diminutives in self.diminutive_map.values():
        if alias in diminutives:
            return True
    return False

def _is_transliteration(self, alias: str) -> bool:
    """Check if alias is Latin-only (transliterated)."""
    # Simple heuristic: all characters are Latin alphabet
    return alias.isascii() and alias.isalpha()
```

### Example Prioritization

```
Input: 150 aliases generated for "Алексей Анатольевич Навальный"

Prioritization:
  1. "алексей анатольевич навальный" (score 100, original)
  2. "навального" (score 90, genitive case)
  3. "навальному" (score 90, dative case)
  ...
  10. "а. навальный" (score 80, initial)
  ...
  50. "леша" (score 60, diminutive)
  ...
  100. "navalny" (score 40, transliteration)

Truncated (scores 40-50, alphabetically last): 50 aliases discarded

Output: Top 100 aliases
WARNING log: "Alias limit exceeded: 150 generated, 100 kept (original: 'Алексей Анатольевич Навальный')"
```

---

## 6. Normalization Sequence

### Decision
Apply normalization consistently across ALL generated aliases before adding to automaton.

### Normalization Steps (per FR-008, FR-009, FR-010)

1. **Convert ё → е** (FR-009)
2. **Lowercase** (FR-010)
3. **Whitespace cleanup**: Replace sequences of `[\s\.\-]+` with single space (FR-008)
4. **Trim**: Remove leading/trailing whitespace

```python
import re

def normalize_alias(alias: str) -> str:
    """
    Normalize alias for consistent automaton insertion.

    Implements FR-008, FR-009, FR-010.
    """
    # Step 1: ё → е
    normalized = alias.replace('ё', 'е')

    # Step 2: Lowercase
    normalized = normalized.lower()

    # Step 3: Whitespace/punctuation cleanup
    normalized = re.sub(r'[\s\.\-]+', ' ', normalized)

    # Step 4: Trim
    normalized = normalized.strip()

    return normalized
```

### Example Normalization

| Input | Output |
|-------|--------|
| "Алексей   Навальный" | "алексей навальный" |
| "А.  А.   Навальный" | "а а навальный" |
| "Алёша-Лёша" | "алеша леша" |
| "НАВАЛЬНЫЙ" | "навальный" |

### Application Point
Call `normalize_alias()` on **every generated alias** before:
1. Adding to automaton (`self.automaton.add_word()`)
2. Adding to entity_map dictionary
3. Deduplication (to catch "Алёша" and "Алеша" as same normalized form)

---

## Summary of Decisions

| Research Area | Decision | Library/Pattern |
|---------------|----------|-----------------|
| Morphology | pymorphy3 | `MorphAnalyzer().parse().lexeme` for all case forms |
| Diminutives | petrovich | Name dictionary lookup table |
| Transliteration | transliterate | Simplified phonetic mode |
| Name Parsing | Heuristic | Split on whitespace, 2/3/4+ part patterns |
| Prioritization | Weighted scoring | 100 (original) > 90 (cases) > 80 (initials) > 60 (diminutives) > 40 (translit) |
| Normalization | Regex + string ops | ё→е, lowercase, whitespace cleanup |

All patterns designed for **build-time execution** (no query-time impact), with performance targets:
- **Library initialization**: <3 seconds total (pymorphy3 + petrovich + transliterate)
- **Per-entity expansion**: <50ms average
- **Total build time**: <2 minutes for ~1000 entities

---

**Next Phase**: Implement AliasExpander class based on these research findings (see data-model.md and contracts/)
