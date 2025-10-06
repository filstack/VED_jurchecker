# Implementation Plan: Dictionary Alias Expansion

**Branch**: `001-dictionary-expansion` | **Date**: 2025-10-06 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-dictionary-expansion/spec.md`

## Execution Flow (/plan command scope)
```
1. Load feature spec from Input path
   → ✅ Loaded and analyzed spec.md
2. Fill Technical Context (scan for NEEDS CLARIFICATION)
   → ✅ No NEEDS CLARIFICATION markers (all resolved via /clarify)
   → ✅ Project Type: Single Python API service
3. Fill Constitution Check section
   → ✅ All 5 principles evaluated
4. Evaluate Constitution Check section
   → ✅ PASS - No violations, dependencies justified
   → ✅ Updated Progress Tracking: Initial Constitution Check
5. Execute Phase 0 → research.md
   → ✅ Library research complete (pymorphy3, petrovich, transliterate)
6. Execute Phase 1 → contracts, data-model.md, quickstart.md
   → ✅ Generated all Phase 1 artifacts
7. Re-evaluate Constitution Check
   → ✅ PASS - Design maintains all constitutional principles
   → ✅ Updated Progress Tracking: Post-Design Constitution Check
8. Plan Phase 2 → Task generation approach described below
9. STOP - Ready for /tasks command
   → ✅ Planning complete
```

**IMPORTANT**: The /plan command STOPS here. Phase 2 (task generation) is executed by `/tasks` command.

## Summary

This feature enhances JurChecker's entity detection recall by automatically expanding entity names into multiple searchable variants during offline dictionary compilation. The system will generate:

- **Name order variants**: "Имя Фамилия" ↔ "Фамилия Имя"
- **Initial forms**: "И. Фамилия", "И.О. Фамилия", etc.
- **Morphological case forms**: All 6 Russian cases using pymorphy3
- **Diminutive forms**: "Алексей" → "Лёша", "Леша", "Алекс" via petrovich
- **Transliterations**: Simplified phonetic Cyrillic→Latin conversion
- **Normalized variants**: ё→е, whitespace cleanup, lowercase

All expansion happens at dictionary build time (inside `JurChecker._load_and_prepare_data()`), ensuring **zero query-time performance impact**. The existing pickle cache mechanism stores the expanded automaton, and the existing CSV hash validation ensures cache invalidation when the registry updates.

**Technical Approach**: Add a new internal `AliasExpander` class to `jur_checker.py` that encapsulates all variant generation logic. Integrate it into the existing data loading pipeline with comprehensive logging and a 100-alias-per-entity limit to prevent dictionary explosion.

## Technical Context

**Language/Version**: Python 3.10+
**Primary Dependencies**:
- Existing: FastAPI 0.115.0, uvicorn 0.30.0, pandas 2.2.0, pyahocorasick 2.1.0, pydantic 2.9.0
- New: pymorphy3 (~1.2.0), petrovich (~1.0.0), transliterate (~1.10.0)

**Storage**: CSV registry file (`registry_entities_rows.csv`) + pickle cache (`.cache/` directory)
**Testing**: pytest (new), manual quickstart validation
**Target Platform**: Python server (Linux/Windows) running uvicorn on port 8001
**Project Type**: Single project (standalone Python API service, no frontend/backend split)
**Performance Goals**:
- Dictionary build time: <2 minutes (FR-016c)
- Query response time: <100ms (existing, must preserve)
- Performance warning threshold: 90 seconds (FR-021)

**Constraints**:
- Zero query-time performance impact (all expansion offline during build)
- Maximum 100 aliases per entity (FR-016a)
- Backward compatible with existing n8n integration (no API changes)
- Preserve existing cache invalidation mechanism (CSV hash-based)

**Scale/Scope**:
- Current registry: ~1000s of entities (based on CSV size ~1.3MB)
- Expansion multiplier: ~10-50x per entity (depending on name complexity)
- Expected total aliases: ~50,000-500,000 in automaton

## Constitution Check
*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### ✅ I. Production Stability First
**Compliance**: PASS
- Feature adds alias expansion in `JurChecker` class ONLY during dictionary build phase
- **No API changes**: FastAPI endpoints, request/response schemas unchanged
- **Zero-downtime deployment**: Build-time feature uses existing cache mechanism for gradual rollout
- **Backward compatibility**: Automaton structure preserved, only more entries added (additive change)
- **n8n integration**: Completely transparent—no workflow changes required

### ✅ II. Performance & Caching
**Compliance**: PASS
- All alias generation happens during `_load_and_prepare_data()` method (offline)
- Expanded automaton cached via existing pickle mechanism (no new caching infrastructure)
- Automatic cache invalidation via existing CSV hash validation
- Build time enforced at <2 minutes with 90-second warning threshold (FR-016c, FR-021)
- Query-time performance preserved (zero impact)

### ✅ III. Data Integrity & Validation
**Compliance**: PASS
- CSV registry remains single source of truth
- Existing normalization (lowercase, ё→е) extended to all generated aliases (FR-008, FR-009, FR-010)
- Existing word boundary validation applies to all alias variants
- Context extraction (±150 chars) unchanged—no impact on downstream AI verification

### ✅ IV. API Contract Stability
**Compliance**: PASS
- **Zero API contract changes**: POST /check-candidates schema unchanged
- Pydantic models (TextIn, CandidateOut, CandidatesResponse) unchanged
- Existing runtime validation preserved
- Response format identical (more candidates may be returned, which is expected behavior improvement)

### ✅ V. Minimal Dependencies
**Compliance**: PASS (with justification)
**New Dependencies** (3 additions):
1. **pymorphy3** (~1.2.0):
   - Purpose: Russian morphological analysis for surname declension (6 cases)
   - Justification: Industry-standard library, widely used in Russian NLP, actively maintained
   - Security: Established package with 500K+ downloads/month, no known vulnerabilities

2. **petrovich** (~1.0.0):
   - Purpose: Russian name declension and diminutive mappings
   - Justification: Specialized Russian name library, lightweight, focused single purpose
   - Security: Open-source, Russian developer community standard, stable API

3. **transliterate** (~1.10.0):
   - Purpose: Cyrillic→Latin phonetic transliteration
   - Justification: Configurable transliteration, supports simplified phonetic mode
   - Security: Lightweight library, no external dependencies, maintained

**Versions will be pinned** in requirements.txt per constitutional requirement.

**Gate Status**: ✅ PASS (all principles compliant, 3 new dependencies justified for production)

## Project Structure

### Documentation (this feature)
```
specs/001-dictionary-expansion/
├── spec.md              # Feature specification (complete)
├── plan.md              # This file (/plan command output)
├── research.md          # Phase 0 output: Library research & name parsing
├── data-model.md        # Phase 1 output: AliasExpander entity model
├── quickstart.md        # Phase 1 output: Manual testing procedure
├── contracts/           # Phase 1 output: Method contracts
│   └── alias_expander.md
└── tasks.md             # Phase 2 output (/tasks command - not created by /plan)
```

### Source Code (repository root)
```
# Current structure (single project)
D:\00_dev\01_Ведомости\Юрчекер\law_ch/
├── jur_checker.py           # Main service class (will be enhanced)
├── main.py                  # FastAPI app (no changes needed)
├── requirements.txt         # Will add pymorphy3, petrovich, transliterate
├── registry_entities_rows.csv  # CSV registry (unchanged)
├── .cache/                  # Existing cache directory
│   ├── registry_entities_rows_automaton.pkl
│   └── registry_entities_rows_hash.txt
└── tests/                   # NEW: Test directory structure
    ├── contract/            # Contract tests for each expansion type
    │   ├── test_name_orders.py
    │   ├── test_initials.py
    │   ├── test_morphology.py
    │   ├── test_transliteration.py
    │   └── test_alias_limit.py
    ├── integration/         # Integration tests for full build cycle
    │   ├── test_full_build.py
    │   ├── test_cache_invalidation.py
    │   └── test_performance.py
    └── unit/                # Unit tests for normalization, parsing
        ├── test_normalization.py
        └── test_name_parsing.py

# Internal structure within jur_checker.py (refactored):
class JurChecker:                    # Existing class
    __init__()                       # Existing
    _load_and_prepare_data()         # ENHANCED: Integrates AliasExpander
    _load_from_cache()               # Existing (unchanged)
    _save_to_cache()                 # Existing (unchanged)
    find_raw_candidates()            # Existing (unchanged)

class AliasExpander:                 # NEW internal class
    __init__(max_aliases=100)
    expand_all(name, entity_type) → list[str]  # Main entry point
    parse_person_name(name) → tuple
    expand_name_orders(...)
    expand_initials(...)
    expand_diminutives(...)
    expand_transliterations(...)
    expand_morphological_forms(...)
    apply_heuristic_fallback(...)
    normalize_alias(...)
    prioritize_aliases(...)
```

**Structure Decision**: Single project structure (Option 1) selected. JurChecker is a standalone Python API service with no frontend/backend split. All alias expansion logic will be added as a new internal `AliasExpander` class within `jur_checker.py` to maintain:
- **Separation of concerns**: Expansion logic isolated from search logic
- **Code locality**: Related functionality stays in same module
- **Minimal refactoring**: No need to create new packages/modules for ~300 lines of expansion code

This aligns with the constitution's "Minimal Dependencies" principle by avoiding unnecessary architectural complexity.

## Phase 0: Outline & Research

### Research Areas
1. **pymorphy3 integration** for morphological case generation
2. **petrovich library** for Russian name diminutives
3. **transliterate library** for Cyrillic→Latin conversion
4. **Name parsing patterns** for Russian full names (First/Patronymic/Last)
5. **Expansion algorithm design** with 100-alias limit and prioritization

### Research Findings (see research.md for details)

**1. pymorphy3 for Morphological Analysis**
- **Decision**: Use `pymorphy3.MorphAnalyzer().parse(word)[0].lexeme` for surname declension
- **Rationale**: Returns all inflected forms (6 Russian cases) for a word
- **Integration Pattern**:
  ```python
  morph = pymorphy3.MorphAnalyzer()
  parsed = morph.parse(surname)
  if parsed and parsed[0].score >= 0.5:  # Confidence threshold
      cases = {form.word for form in parsed[0].lexeme}
  else:
      apply_heuristic_fallback(surname)
  ```
- **Fallback Strategy**: If confidence <0.5 or foreign name, apply suffix heuristics (-ого, -ому, -ым, -ом)

**2. petrovich for Diminutive Forms**
- **Decision**: Use petrovich's internal name database for diminutive mappings
- **Rationale**: Contains comprehensive Russian first name→diminutive mappings
- **Alternative Considered**: pymorphy3 has some name data but less complete for diminutives
- **Integration**: Access petrovich's name dictionary at initialization, build lookup table

**3. transliterate for Cyrillic→Latin Conversion**
- **Decision**: Use `translit(text, 'ru', reversed=True)` with phonetic customization
- **Rationale**: Supports simplified phonetic transliteration (Юрий→Yuri not Iurii)
- **Configuration**: Override default mappings for readability (per FR-006 clarification)

**4. Russian Name Parsing Patterns**
- **Full Name Structure**: `[FirstName] [Patronymic?] [LastName]`
- **Parsing Heuristic**:
  - 2 parts: Assume FirstName LastName (patronymic omitted)
  - 3 parts: FirstName Patronymic LastName
  - 4+ parts: First Middle Patronymic Last (treat Middle as part of FirstName)
- **Edge Cases**:
  - Compound surnames with hyphens: "Иванов-Петров" treated as single LastName unit
  - Single names: Organizations or mononyms—skip person-specific expansions

**5. Expansion Algorithm with 100-Alias Limit**
- **Priority Order** (FR-016b):
  1. Original name (always included, weight=100)
  2. Morphological case forms (weight=90, highest value for Russian legal texts)
  3. Name order variants + initials (weight=80, common in formal documents)
  4. Diminutive forms (weight=60, moderate frequency)
  5. Transliterations (weight=40, less common in Russian-language documents)

- **Algorithm**:
  ```
  1. Generate all variants by type (may exceed 100)
  2. Assign priority scores to each variant
  3. Sort by priority descending
  4. Take top 100
  5. If truncated, log WARNING with entity ID
  ```

**Output**: [research.md](./research.md) documenting library integration guides, name parsing algorithm, and expansion prioritization strategy

## Phase 1: Design & Contracts
*Prerequisites: research.md complete ✅*

### 1. Data Model (data-model.md)

#### AliasExpander Class (NEW)

**Purpose**: Encapsulates all alias expansion logic, called by `JurChecker._load_and_prepare_data()` for each entity during dictionary build.

**Fields**:
- `morph_analyzer: pymorphy3.MorphAnalyzer` - Morphological analyzer instance (initialized once)
- `translit_config: dict` - Transliteration customization for simplified phonetic mode
- `diminutive_map: dict[str, list[str]]` - FirstName → [diminutives] lookup (from petrovich)
- `max_aliases: int` - Maximum aliases per entity (default 100, per FR-016a)
- `alias_priority: dict[str, int]` - Variant type → priority weight mapping

**Methods**:
- `expand_all(entity_name: str, entity_type: str) → list[str]`
  - Main entry point, orchestrates all expansion types
  - Returns normalized, deduplicated, prioritized list (≤100 aliases)
  - Logs alias count at INFO level (FR-017)

- `parse_person_name(name: str) → tuple[str, str|None, str]`
  - Extracts (FirstName, Patronymic, LastName) from full name string
  - Handles 2-part, 3-part, and compound name structures

- `expand_name_orders(first: str, patronymic: str|None, last: str) → list[str]`
  - Implements FR-001: "First Last", "Last First", "First Patronymic Last"

- `expand_initials(first: str, patronymic: str|None, last: str) → list[str]`
  - Implements FR-002, FR-003: "I. Last", "Last I.", "I.P. Last", "Last I.P."

- `expand_diminutives(first_name: str) → list[str]`
  - Implements FR-005: Looks up diminutives in petrovich dictionary
  - Returns empty list if no diminutives found (not all names have diminutives)

- `expand_transliterations(variants: list[str]) → list[str]`
  - Implements FR-006, FR-007: Applies transliterate library to existing variants
  - Returns Latin versions using simplified phonetic rules

- `expand_morphological_forms(surname: str) → list[str]`
  - Implements FR-011: Generates all 6 Russian case forms via pymorphy3
  - Returns declensions: genitive, dative, accusative, instrumental, prepositional

- `apply_heuristic_fallback(surname: str) → list[str]`
  - Implements FR-013: Adds suffixes -ого, -ому, -ым, -ом when morphology fails
  - Logs WARNING with entity details (FR-013a, FR-018)

- `normalize_alias(alias: str) → str`
  - Implements FR-008, FR-009, FR-010: lowercase, ё→е, whitespace cleanup

- `prioritize_aliases(aliases: list[str], limit: int) → list[str]`
  - Implements FR-016a, FR-016b: Sorts by priority, returns top N
  - Logs WARNING if truncation occurs

#### JurChecker Class (MODIFIED)

**Modified Method**: `_load_and_prepare_data(csv_path: str) → dict`
- **Changes**:
  1. Initialize `expander = AliasExpander()` once before loop
  2. Start build timer (for FR-021 90-second warning)
  3. For each entity row:
     - Call `aliases = expander.expand_all(entity_data['name'], entity_data['type'])`
     - Add all aliases to automaton (existing logic)
     - Log alias count per entity (FR-017)
  4. After loop: Log total build time, warn if >90s (FR-021)
  5. Return entity_map (unchanged structure)

**Unchanged Methods**: All other methods (`_load_from_cache`, `_save_to_cache`, `find_raw_candidates`, etc.) remain unchanged—backward compatibility preserved.

### 2. API Contracts (contracts/alias_expander.md)

**Contract 1: Name Order Expansion** (FR-001)
```python
# Input
first = "Алексей"
patronymic = "Анатольевич"
last = "Навальный"

# Expected Output
[
    "Алексей Навальный",           # First Last
    "Навальный Алексей",           # Last First
    "Алексей Анатольевич Навальный"  # Full (original preserved)
]

# Test: Verify all 3 variants present, normalized
```

**Contract 2: Initial Expansion** (FR-002, FR-003)
```python
# Input (same as above)
first = "Алексей"
patronymic = "Анатольевич"
last = "Навальный"

# Expected Output
[
    "А. Навальный",      # Single initial + Last
    "Навальный А.",      # Last + single initial
    "А.А. Навальный",    # Double initial + Last
    "Навальный А.А."     # Last + double initial
]

# Test: Verify initial extraction (first letter only), period formatting
```

**Contract 3: Morphological Case Expansion** (FR-011)
```python
# Input
surname = "Навальный"

# Expected Output (after normalization)
[
    "навальный",     # Nominative (original)
    "навального",    # Genitive
    "навальному",    # Dative
    "навальным",     # Instrumental (same as Accusative for this name)
    "навальном"      # Prepositional
]

# Test: Verify pymorphy3 returns all forms, deduplicated, lowercase
```

**Contract 4: Transliteration Expansion** (FR-006, FR-007)
```python
# Input (variants in Cyrillic)
variants = ["Навальный", "А. Навальный", "Алексей Навальный"]

# Expected Output (simplified phonetic)
[
    "navalny",           # Transliterated surname
    "a. navalny",        # Transliterated initial + surname
    "alexey navalny"     # Transliterated full name
]

# Test: Verify Юрий→Yuri (not Iurii), phonetic readability
```

**Contract 5: Alias Limit Enforcement** (FR-016a, FR-016b)
```python
# Input
generated_aliases = [...150 items...]  # More than max_aliases=100

# Expected Output
top_100_aliases  # Sorted by priority, top 100 only

# Side Effect
# WARNING log: "Entity TEST123 exceeded alias limit (150 generated, 100 kept)"

# Test: Verify prioritization order (original > cases > initials > diminutives > translit)
```

**Contract 6: Heuristic Fallback** (FR-013, FR-013a, FR-018)
```python
# Input (foreign surname, pymorphy3 fails)
surname = "Müller"

# Expected Output
[
    "müller",       # Original (normalized)
    "müllerого",    # Heuristic genitive suffix
    "müllerому",    # Heuristic dative suffix
    "müllerым",     # Heuristic instrumental suffix
    "müllerом"      # Heuristic prepositional suffix
]

# Side Effect
# WARNING log: "Morphological fallback for entity ID=123, name='Müller'"

# Test: Verify heuristic suffix application, warning logged
```

### 3. Contract Tests (generated from contracts)

**Test Files** (in `tests/contract/`):
- `test_name_orders.py` - Contract 1
- `test_initials.py` - Contract 2
- `test_morphology.py` - Contract 3
- `test_transliteration.py` - Contract 4
- `test_alias_limit.py` - Contract 5
- `test_heuristic_fallback.py` - Contract 6

**Test Structure Template**:
```python
import pytest
from jur_checker import AliasExpander

def test_name_order_expansion():
    """Contract 1: Verify name order variants generation"""
    expander = AliasExpander()
    first, patronymic, last = "Алексей", "Анатольевич", "Навальный"

    variants = expander.expand_name_orders(first, patronymic, last)

    # Normalize for comparison
    normalized = [expander.normalize_alias(v) for v in variants]

    assert "алексей навальный" in normalized
    assert "навальный алексей" in normalized
    assert "алексей анатольевич навальный" in normalized
    # Test MUST FAIL until implementation complete
```

All contract tests MUST fail initially (TDD requirement per constitution).

### 4. Integration Test Scenarios (from quickstart.md)

**Scenario 1: Full Build Cycle** (`tests/integration/test_full_build.py`)
- Setup: Add test entity to CSV, delete cache
- Execute: Initialize JurChecker
- Verify:
  - Build completes successfully
  - Cache files created
  - Test entity findable by all variant forms
  - Build time <2 minutes

**Scenario 2: Cache Invalidation** (`tests/integration/test_cache_invalidation.py`)
- Setup: Build once, modify CSV
- Execute: Re-initialize JurChecker
- Verify:
  - Cache rebuild triggered (hash mismatch detected)
  - New aliases from updated CSV present in automaton

**Scenario 3: Performance Constraint** (`tests/integration/test_performance.py`)
- Setup: Full production-size CSV
- Execute: Build with timing
- Verify:
  - Total build time <120 seconds (FR-016c)
  - WARNING logged if >90 seconds (FR-021)
  - Alias counts logged (FR-017)

### 5. Quickstart Manual Testing (quickstart.md)

**Procedure**:
1. **Setup Test Data**:
   - Add entity to CSV: `TEST001,Алексей Анатольевич Навальный,person,"[]"`
   - Delete `.cache/` directory to force rebuild

2. **Start Service**:
   ```bash
   python -m uvicorn main:app --port 8001 --reload
   ```

3. **Verify Logs**:
   - Check for `"Реестр успешно загружен. X ключевых слов добавлено"` (X should be >>1000 more)
   - Look for alias count logs: `"Entity TEST001: 47 aliases generated"`
   - Verify build time: `"Dictionary build completed in 67.3 seconds"`
   - No ERROR logs, only INFO/WARNING

4. **Test API - Base Case**:
   ```bash
   curl -X POST http://localhost:8001/check-candidates \
     -H "Content-Type: application/json" \
     -d '{"text": "Встреча с Навальным состоялась вчера"}'
   ```
   Expected: `candidates` array contains TEST001 with `found_alias: "навальным"` (instrumental case)

5. **Test API - Initial Variant**:
   ```bash
   curl -X POST http://localhost:8001/check-candidates \
     -H "Content-Type: application/json" \
     -d '{"text": "А. Навальный выступил на конференции"}'
   ```
   Expected: TEST001 found with `found_alias: "а. навальный"`

6. **Test API - Transliteration**:
   ```bash
   curl -X POST http://localhost:8001/check-candidates \
     -H "Content-Type: application/json" \
     -d '{"text": "Interview with Alexey Navalny was published"}'
   ```
   Expected: TEST001 found with `found_alias: "alexey navalny"`

7. **Test Backward Compatibility**:
   - Search for existing entity using original name
   - Verify still found (additive change, nothing broken)

8. **Test Alias Limit**:
   - Add entity with very long compound name (e.g., 5-part name)
   - Check logs for WARNING: `"Entity XYZ exceeded alias limit"`

**Acceptance Criteria** (from spec.md):
- ✅ Build completes in <2 minutes
- ✅ No ERROR logs during startup
- ✅ Cache file size increases (more aliases stored)
- ✅ Test entity findable by all variant types (case, initial, transliteration)
- ✅ Existing entities still findable (backward compatibility verified)

### 6. Agent File Update

**Execute**: `.specify/scripts/powershell/update-agent-context.ps1 -AgentType claude`

**Expected Updates**:
- **Recent Changes** (add): "Added dictionary alias expansion: name orders, initials, morphology (pymorphy3), diminutives (petrovich), transliteration"
- **Tech Stack** (add): "pymorphy3 (Russian morphology), petrovich (name declension), transliterate (Cyrillic→Latin)"
- **Architecture** (modify): "JurChecker with internal AliasExpander class for build-time alias generation"

**Output**: CLAUDE.md at repository root with updated context (≤150 lines per constitutional efficiency requirement)

## Phase 2: Task Planning Approach
*This section describes what the /tasks command will do - DO NOT execute during /plan*

**Task Generation Strategy**:
1. **From contracts/** (6 contract test tasks):
   - T001 [P]: Contract test for name order expansion
   - T002 [P]: Contract test for initial expansion
   - T003 [P]: Contract test for morphological forms
   - T004 [P]: Contract test for transliteration
   - T005 [P]: Contract test for alias limit enforcement
   - T006 [P]: Contract test for heuristic fallback

2. **From data-model.md** (AliasExpander implementation):
   - T007: Create AliasExpander class stub with __init__
   - T008 [P]: Implement parse_person_name() method
   - T009 [P]: Implement expand_name_orders() method
   - T010 [P]: Implement expand_initials() method
   - T011: Implement expand_diminutives() method (depends on petrovich setup)
   - T012: Implement expand_transliterations() method
   - T013: Implement expand_morphological_forms() method (pymorphy3)
   - T014: Implement apply_heuristic_fallback() method
   - T015 [P]: Implement normalize_alias() method
   - T016: Implement prioritize_aliases() method
   - T017: Implement expand_all() orchestrator method

3. **From quickstart.md** (integration tests):
   - T018 [P]: Integration test for full build cycle
   - T019 [P]: Integration test for cache invalidation
   - T020: Performance test for 2-minute build constraint

4. **Implementation tasks**:
   - T021: Update requirements.txt with pymorphy3, petrovich, transliterate
   - T022: Refactor JurChecker._load_and_prepare_data() to integrate AliasExpander
   - T023: Add logging for alias counts per entity (FR-017)
   - T024: Add logging for build time and performance warnings (FR-019, FR-021)
   - T025: Add logging for morphological fallback (FR-018, FR-020)

5. **Validation tasks**:
   - T026: Run manual quickstart verification procedure
   - T027: Performance profiling if build time >90 seconds

**Ordering Strategy**:
- **TDD order**: Contract tests (T001-T006) before implementation (T008-T017)
- **Dependency order**:
  - AliasExpander stub (T007) blocks all method implementations
  - expand_all() (T017) depends on all other methods complete
  - JurChecker integration (T022) depends on AliasExpander complete
  - Logging tasks (T023-T025) parallel with integration
  - Integration tests (T018-T020) after core implementation
- **Parallel opportunities**: [P] marks independent tasks (different files/methods)

**Estimated Output**: 27 numbered, dependency-ordered tasks in tasks.md

**IMPORTANT**: This phase is executed by the `/tasks` command, NOT by `/plan`. The plan stops here.

## Phase 3+: Future Implementation
*These phases are beyond the scope of the /plan command*

**Phase 3**: Task execution (`/tasks` command creates tasks.md with detailed breakdown)
**Phase 4**: Implementation (execute tasks.md following TDD and constitutional principles)
**Phase 5**: Validation (run all tests, execute quickstart.md, verify performance <2 minutes)

## Complexity Tracking
*Fill ONLY if Constitution Check has violations that must be justified*

No violations detected. All constitutional gates passed.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| (none) | - | - |

## Progress Tracking
*This checklist is updated during execution flow*

**Phase Status**:
- [x] Phase 0: Research complete (/plan command)
- [x] Phase 1: Design complete (/plan command)
- [x] Phase 2: Task planning approach described (/plan command - approach only, not execution)
- [ ] Phase 3: Tasks generated (/tasks command - not executed by /plan)
- [ ] Phase 4: Implementation complete
- [ ] Phase 5: Validation passed

**Gate Status**:
- [x] Initial Constitution Check: PASS (all 5 principles compliant)
- [x] Post-Design Constitution Check: PASS (design preserves all principles)
- [x] All NEEDS CLARIFICATION resolved (5 clarifications documented in spec.md)
- [x] Complexity deviations documented (none - no violations)

---

*Based on Constitution v1.0.0 - See `.specify/memory/constitution.md`*
