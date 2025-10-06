# API Contracts: AliasExpander

**Feature**: 001-dictionary-expansion
**Date**: 2025-10-06
**Purpose**: Define method-level contracts for AliasExpander class with testable input/output examples

---

## Overview

This document specifies the contracts (input/output behavior) for each method in the `AliasExpander` class. Each contract serves as the basis for a contract test that MUST be written (and MUST fail) before implementation begins (TDD requirement per constitution).

**Testing Principle**: All tests are written in `tests/contract/` directory, one test file per contract.

---

## Contract 1: Name Order Expansion

**Method**: `expand_name_orders(first: str, patronymic: str | None, last: str) → list[str]`

**Requirement**: FR-001, FR-004

**Purpose**: Generate all name order variants (First Last, Last First, with/without patronymic).

### Test Case 1.1: Two-Part Name (No Patronymic)

```python
# Input
first = "Алексей"
patronymic = None
last = "Навальный"

# Expected Output (unnormalized, preserves case and spacing)
[
    "Алексей Навальный",      # First Last
    "Навальный Алексей"       # Last First
]

# Test Assertions
assert len(result) == 2
assert "Алексей Навальный" in result
assert "Навальный Алексей" in result
```

### Test Case 1.2: Three-Part Name (With Patronymic)

```python
# Input
first = "Алексей"
patronymic = "Анатольевич"
last = "Навальный"

# Expected Output
[
    "Алексей Анатольевич Навальный",  # Full name (original, FR-004)
    "Алексей Навальный",              # First Last (patronymic omitted)
    "Навальный Алексей"               # Last First (patronymic omitted)
]

# Test Assertions
assert len(result) == 3
assert "Алексей Анатольевич Навальный" in result  # FR-004: original preserved
assert "Алексей Навальный" in result
assert "Навальный Алексей" in result
```

### Test Case 1.3: Single-Word Name

```python
# Input
first = "Навальный"
patronymic = None
last = "Навальный"

# Expected Output
[
    "Навальный Навальный",  # First Last (same word repeated)
    "Навальный Навальный"   # Last First (duplicate, will be deduplicated later)
]

# Test Assertions
assert len(result) >= 1  # May contain duplicates (deduplication happens in expand_all)
assert "Навальный Навальный" in result
```

**Test File**: `tests/contract/test_name_orders.py`

---

## Contract 2: Initial Expansion

**Method**: `expand_initials(first: str, patronymic: str | None, last: str) → list[str]`

**Requirement**: FR-002, FR-003

**Purpose**: Generate initial variants (single and double initials).

### Test Case 2.1: Single Initial (No Patronymic)

```python
# Input
first = "Алексей"
patronymic = None
last = "Навальный"

# Expected Output
[
    "А. Навальный",    # I. Last (FR-002)
    "Навальный А."     # Last I. (FR-002)
]

# Test Assertions
assert len(result) == 2
assert "А. Навальный" in result
assert "Навальный А." in result
```

### Test Case 2.2: Double Initial (With Patronymic)

```python
# Input
first = "Алексей"
patronymic = "Анатольевич"
last = "Навальный"

# Expected Output
[
    "А. Навальный",       # Single initial (FR-002)
    "Навальный А.",       # Single initial reversed (FR-002)
    "А.А. Навальный",     # Double initial (FR-003)
    "Навальный А.А."      # Double initial reversed (FR-003)
]

# Test Assertions
assert len(result) == 4
assert "А. Навальный" in result
assert "Навальный А." in result
assert "А.А. Навальный" in result  # FR-003: patronymic initial included
assert "Навальный А.А." in result
```

### Test Case 2.3: Unicode Handling (Cyrillic Initials)

```python
# Input
first = "Юрий"
patronymic = "Павлович"
last = "Лужков"

# Expected Output
[
    "Ю. Лужков",
    "Лужков Ю.",
    "Ю.П. Лужков",
    "Лужков Ю.П."
]

# Test Assertions
assert "Ю. Лужков" in result  # Cyrillic Ю correctly extracted
assert "Ю.П. Лужков" in result
```

**Test File**: `tests/contract/test_initials.py`

---

## Contract 3: Morphological Case Expansion

**Method**: `expand_morphological_forms(surname: str) → list[str]`

**Requirement**: FR-011, FR-012

**Purpose**: Generate all 6 Russian case forms using pymorphy3.

### Test Case 3.1: Standard Russian Surname

```python
# Input
surname = "Навальный"

# Expected Output (lowercase, all case forms)
# Note: Some cases may produce identical forms (deduplicated automatically by set)
[
    "навальный",    # Nominative (именительный)
    "навального",   # Genitive (родительный)
    "навальному",   # Dative (дательный)
    "навальным",    # Instrumental (творительный)
    "навальном"     # Prepositional (предложный)
    # Accusative may equal Nominative or Genitive for surnames
]

# Test Assertions
assert "навальный" in result
assert "навального" in result
assert "навальному" in result
assert "навальным" in result
assert "навальном" in result
assert len(result) >= 5  # At least 5 distinct forms
```

### Test Case 3.2: Foreign Surname (Morphology Fails)

```python
# Input
surname = "Müller"

# Expected Output (empty list, triggers fallback in expand_all)
[]

# Test Assertions
assert result == [] or len(result) == 0
# Note: expand_all() will call apply_heuristic_fallback() when this returns empty
```

### Test Case 3.3: Feminine Surname

```python
# Input
surname = "Иванова"

# Expected Output (lowercase case forms for feminine surname)
[
    "иванова",
    "ивановой",   # Genitive feminine
    "ивановой",   # Dative feminine
    "ивановой",   # Instrumental feminine
    "ивановой"    # Prepositional feminine
]

# Test Assertions
assert "иванова" in result
assert "ивановой" in result
assert len(result) >= 2  # At least nominative + genitive
```

**Test File**: `tests/contract/test_morphology.py`

---

## Contract 4: Transliteration Expansion

**Method**: `expand_transliterations(variants: list[str]) → list[str]`

**Requirement**: FR-006, FR-007

**Purpose**: Convert Cyrillic variants to Latin using simplified phonetic transliteration.

### Test Case 4.1: Basic Transliteration

```python
# Input
variants = ["Навальный", "А. Навальный", "Алексей Навальный"]

# Expected Output (lowercase Latin, phonetic)
[
    "navalny",           # Simplified phonetic
    "a. navalny",        # Initials preserved
    "aleksey navalny"    # Full name transliterated
]

# Test Assertions
assert "navalny" in result
assert "a. navalny" in result
assert "aleksey navalny" in result
assert all(s.isascii() for s in result)  # All output is Latin
```

### Test Case 4.2: Phonetic Simplification (Юрий → Yuri)

```python
# Input
variants = ["Юрий", "Ю. Лужков"]

# Expected Output (phonetic, NOT standard ISO)
[
    "yuriy",        # NOT "iurii" (phonetic simplification per FR-006)
    "yu. luzhkov"   # NOT "iu. luzhkov"
]

# Test Assertions
assert "yuriy" in result or "yuri" in result  # Phonetic variant
assert "yu. luzhkov" in result
assert "iu. luzhkov" not in result  # ISO 9 form should NOT appear
```

### Test Case 4.3: Mixed Script (Skip)

```python
# Input (already Latin or mixed)
variants = ["John Smith", "Müller"]

# Expected Output (skip or return as-is, depending on implementation)
# Transliteration library should skip already-Latin text
[]  # Or ["john smith", "muller"] if pass-through

# Test Assertions
# Accept either behavior: skip entirely or pass through
# Main requirement: no crashes, graceful handling
```

**Test File**: `tests/contract/test_transliteration.py`

---

## Contract 5: Alias Limit Enforcement

**Method**: `prioritize_aliases(aliases: list[str], original: str, entity_id: str) → list[str]`

**Requirement**: FR-016a, FR-016b

**Purpose**: Truncate aliases to maximum 100 when limit exceeded, prioritizing by type.

### Test Case 5.1: Below Limit (No Truncation)

```python
# Input
aliases = ["навальный", "навального", "навальному", ...]  # 50 aliases total
original = "Алексей Навальный"
entity_id = "TEST001"
max_aliases = 100

# Expected Output (all aliases returned, no truncation)
result = aliases  # Same list

# Test Assertions
assert len(result) == 50
assert result == aliases
# No WARNING log should be generated
```

### Test Case 5.2: Exceeds Limit (Truncation Required)

```python
# Input (150 aliases generated)
aliases = [
    "алексей анатольевич навальный",  # Original (priority 100)
    "навального",                      # Morphological (priority 90)
    "навальному",                      # Morphological (priority 90)
    # ... 145 more aliases ...
    "navalny",                         # Transliteration (priority 40, likely truncated)
]
original = "Алексей Анатольевич Навальный"
entity_id = "TEST123"
max_aliases = 100

# Expected Output (top 100 by priority)
result  # Length exactly 100

# Test Assertions
assert len(result) == 100
assert "алексей анатольевич навальный" in result  # Original always included (priority 100)
assert "навального" in result                     # High-priority morphological forms included
# Low-priority transliterations likely truncated (check via mock logger for WARNING)
```

### Test Case 5.3: Prioritization Order

```python
# Input (carefully crafted to test priority order)
aliases = [
    "aleksey navalny",                 # Transliteration (40)
    "леша",                            # Diminutive (60)
    "а. навальный",                    # Initial (80)
    "навального",                      # Morphological (90)
    "алексей анатольевич навальный"   # Original (100)
] * 30  # Repeat to create 150 total

original = "Алексей Анатольевич Навальный"
max_aliases = 100

# Expected Output
# Top 100 should prioritize: original > morphological > initials > diminutives > transliterations

result

# Test Assertions
# Count how many of each type in top 100
originals = [a for a in result if a == "алексей анатольевич навальный"]
morphological = [a for a in result if "ого" in a or "ому" in a or "ым" in a]
transliterations = [a for a in result if a.isascii()]

assert len(originals) >= 1            # Original always included
assert len(morphological) > len(transliterations)  # Higher priority types more prevalent
```

### Test Case 5.4: Logging Verification

```python
# Input (exceeds limit)
aliases = ["alias" + str(i) for i in range(150)]
original = "Test Entity"
entity_id = "TEST_LIMIT"
max_aliases = 100

# Expected Side Effect
# WARNING log: "Entity TEST_LIMIT exceeded alias limit (150 generated, 100 kept)"

# Test Assertions (using mock logger)
import logging
from unittest.mock import Mock

mock_logger = Mock(spec=logging.Logger)
expander.logger = mock_logger

result = expander.prioritize_aliases(aliases, original, entity_id)

# Verify WARNING was logged
mock_logger.warning.assert_called_once()
call_args = mock_logger.warning.call_args[0][0]  # First positional arg (message)
assert "TEST_LIMIT" in call_args
assert "150 generated" in call_args
assert "100 kept" in call_args
```

**Test File**: `tests/contract/test_alias_limit.py`

---

## Contract 6: Heuristic Fallback

**Method**: `apply_heuristic_fallback(surname: str, entity_id: str) → list[str]`

**Requirement**: FR-013, FR-013a, FR-018, FR-020

**Purpose**: Apply manual suffix heuristics when morphological analysis fails (foreign/rare names).

### Test Case 6.1: Foreign Surname

```python
# Input
surname = "Müller"
entity_id = "FOREIGN_001"

# Expected Output (base + heuristic suffixes, lowercase)
[
    "müller",       # Original (normalized)
    "müllerого",    # Genitive suffix
    "müllerому",    # Dative suffix
    "müllerым",     # Instrumental suffix
    "müllerом"      # Prepositional suffix
]

# Test Assertions
assert len(result) == 5
assert "müller" in result
assert "müllerого" in result
assert "müllerому" in result
assert "müllerым" in result
assert "müllerом" in result
```

### Test Case 6.2: Rare Russian Surname

```python
# Input
surname = "Шойгу"
entity_id = "RARE_002"

# Expected Output (if pymorphy3 fails)
[
    "шойгу",
    "шойгуого",
    "шойгуому",
    "шойгуым",
    "шойгуом"
]

# Test Assertions
assert len(result) == 5
assert all(s.startswith("шойгу") for s in result)
```

### Test Case 6.3: Logging Verification

```python
# Input
surname = "Müller"
entity_id = "LOG_TEST"

# Expected Side Effect
# WARNING log: "Morphological fallback for entity LOG_TEST, surname='Müller'"

# Test Assertions (using mock logger)
import logging
from unittest.mock import Mock

mock_logger = Mock(spec=logging.Logger)
expander.logger = mock_logger

result = expander.apply_heuristic_fallback(surname, entity_id)

# Verify WARNING was logged with correct format (FR-018, FR-020)
mock_logger.warning.assert_called_once()
call_args = mock_logger.warning.call_args[0][0]
assert "LOG_TEST" in call_args
assert "Müller" in call_args or "müller" in call_args
assert "fallback" in call_args.lower()
```

**Test File**: `tests/contract/test_heuristic_fallback.py`

---

## Contract 7: Normalization

**Method**: `normalize_alias(alias: str) → str`

**Requirement**: FR-008, FR-009, FR-010

**Purpose**: Normalize aliases for consistent automaton insertion (lowercase, ё→е, whitespace cleanup).

### Test Case 7.1: ё → е Conversion (FR-009)

```python
# Input
alias = "Алёша Лёша"

# Expected Output
"алеша леша"  # ё converted to е, lowercased

# Test Assertions
assert result == "алеша леша"
assert "ё" not in result
```

### Test Case 7.2: Lowercase Conversion (FR-010)

```python
# Input
alias = "НАВАЛЬНЫЙ"

# Expected Output
"навальный"

# Test Assertions
assert result == "навальный"
assert result.islower()
```

### Test Case 7.3: Whitespace Cleanup (FR-008)

```python
# Input
alias = "А.  А.   Навальный"

# Expected Output
"а а навальный"  # Multiple spaces/dots replaced with single space

# Test Assertions
assert result == "а а навальный"
assert "  " not in result  # No double spaces
```

### Test Case 7.4: Hyphen and Dot Cleanup (FR-008)

```python
# Input
alias = "Петров-Водкин"

# Expected Output
"петров водкин"  # Hyphen replaced with space

# Test Assertions
assert result == "петров водкин"
assert "-" not in result
```

### Test Case 7.5: Combined Normalization

```python
# Input
alias = "  Алёша  -  ЛЁША  .  Навальный  "

# Expected Output
"алеша леша навальный"  # All rules applied: trim, ё→е, lowercase, whitespace cleanup

# Test Assertions
assert result == "алеша леша навальный"
assert result == result.strip()
assert "ё" not in result
assert "  " not in result
assert result.islower()
```

**Test File**: `tests/contract/test_normalization.py`

---

## Contract 8: Orchestration (expand_all)

**Method**: `expand_all(entity_name: str, entity_type: str) → list[str]`

**Requirement**: All FRs (orchestrates all expansion types)

**Purpose**: Main entry point that generates, normalizes, deduplicates, prioritizes, and logs all aliases.

### Test Case 8.1: Full Person Name (Integration)

```python
# Input
entity_name = "Алексей Анатольевич Навальный"
entity_type = "person"
max_aliases = 100

# Expected Behavior
# 1. Parse name → ("Алексей", "Анатольевич", "Навальный")
# 2. Generate name orders (3 variants)
# 3. Generate initials (4 variants)
# 4. Generate diminutives for "Алексей" (~5 variants: Лёша, Леша, etc.)
# 5. Generate morphological forms for "Навальный" (~5 variants)
# 6. Generate transliterations for all above (~20 variants)
# 7. Normalize all (lowercase, ё→е, whitespace cleanup)
# 8. Deduplicate (remove exact duplicates after normalization)
# 9. Prioritize and truncate if >100
# 10. Log alias count

# Expected Output
result  # List of normalized aliases, length ≤100

# Test Assertions
assert len(result) <= 100
assert "алексей анатольевич навальный" in result  # Original preserved
assert "навального" in result                     # Morphological form
assert "а. навальный" in result                   # Initial
assert any("леша" in a or "алекс" in a for a in result)  # Diminutive
assert any(a.isascii() for a in result)           # Transliteration present
assert all(a == a.lower() for a in result)        # All lowercase
assert all("ё" not in a for a in result)          # All ё→е converted
```

### Test Case 8.2: Organization Name (No Diminutives)

```python
# Input
entity_name = "ООО Рога и Копыта"
entity_type = "organization"

# Expected Behavior
# Skip diminutive expansion (only applies to person first names)
# Still apply: name orders, morphology (if applicable), transliteration

# Expected Output
result

# Test Assertions
# No diminutives should be present
# (Hard to test precisely without knowing implementation, but verify reasonable output)
assert len(result) > 0
assert len(result) <= 100
```

### Test Case 8.3: Logging Verification

```python
# Input
entity_name = "Алексей Навальный"
entity_type = "person"

# Expected Side Effect
# INFO log: "Entity <id>: X aliases generated" (FR-017)

# Test Assertions (using mock logger)
import logging
from unittest.mock import Mock

mock_logger = Mock(spec=logging.Logger)
expander.logger = mock_logger

result = expander.expand_all(entity_name, entity_type)

# Verify INFO log was called
mock_logger.info.assert_called()
# (Exact call may vary, but should mention alias count)
```

**Test File**: `tests/contract/test_expand_all.py`

---

## Contract Testing Requirements

### Test Structure Template

```python
import pytest
from jur_checker import AliasExpander

class TestContractX:
    """Contract tests for <method_name>"""

    @pytest.fixture
    def expander(self):
        """Initialize AliasExpander for tests"""
        return AliasExpander(max_aliases=100)

    def test_case_1(self, expander):
        """Test <specific_scenario>"""
        # Arrange
        input_data = ...

        # Act
        result = expander.method_name(input_data)

        # Assert
        assert condition
```

### TDD Requirement

**All contract tests MUST:**
1. Be written BEFORE implementation
2. FAIL initially (no implementation exists yet)
3. Serve as acceptance criteria for implementation
4. Pass after implementation is complete

**Test Execution Order:**
1. Write contract test (Phase 1) ✓
2. Run test → FAIL (expected)
3. Implement method (Phase 4)
4. Run test → PASS (success criteria)

---

## Summary of Contracts

| Contract | Method | Requirements | Test File |
|----------|--------|--------------|-----------|
| 1 | expand_name_orders | FR-001, FR-004 | test_name_orders.py |
| 2 | expand_initials | FR-002, FR-003 | test_initials.py |
| 3 | expand_morphological_forms | FR-011, FR-012 | test_morphology.py |
| 4 | expand_transliterations | FR-006, FR-007 | test_transliteration.py |
| 5 | prioritize_aliases | FR-016a, FR-016b | test_alias_limit.py |
| 6 | apply_heuristic_fallback | FR-013, FR-013a, FR-018, FR-020 | test_heuristic_fallback.py |
| 7 | normalize_alias | FR-008, FR-009, FR-010 | test_normalization.py |
| 8 | expand_all | All FRs (orchestration) | test_expand_all.py |

**Total Contract Tests**: 8 test files with ~20 test cases total

---

**Next**: See quickstart.md for manual integration testing procedure after implementation
