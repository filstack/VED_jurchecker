# Tasks: Dictionary Alias Expansion

**Input**: Design documents from `/specs/001-dictionary-expansion/`
**Prerequisites**: plan.md ✓, research.md ✓, data-model.md ✓, contracts/ ✓, quickstart.md ✓

## Execution Flow (main)
```
1. Load plan.md from feature directory
   → ✓ Tech stack: Python 3.10+, pymorphy3, petrovich, transliterate
   → ✓ Structure: Single project (jur_checker.py + tests/)
2. Load design documents:
   → ✓ data-model.md: AliasExpander class (9 methods)
   → ✓ contracts/alias_expander.md: 8 contract specifications
   → ✓ research.md: Library integration patterns
   → ✓ quickstart.md: 10 manual test scenarios
3. Generate tasks by category:
   → Setup: Dependencies, test directory structure
   → Tests: 8 contract tests + 3 integration tests
   → Core: AliasExpander class (9 methods)
   → Integration: JurChecker modification, logging
   → Polish: Unit tests, performance validation, manual testing
4. Apply task rules:
   → Different test files = [P]
   → Different AliasExpander methods = [P]
   → Same file (jur_checker.py) modifications = sequential
   → Tests before implementation (TDD)
5. Number tasks sequentially (T001-T027)
6. Dependencies validated
7. Parallel execution examples provided
8. SUCCESS - 27 tasks ready for execution
```

## Format: `[ID] [P?] Description`
- **[P]**: Can run in parallel (different files, no dependencies)
- Include exact file paths in descriptions

## Path Conventions
- **Project root**: D:\00_dev\01_Ведомости\Юрчекер\law_ch
- **Main code**: jur_checker.py (root level, not in src/)
- **Tests**: tests/ directory (to be created)
  - tests/contract/
  - tests/integration/
  - tests/unit/

---

## Phase 3.1: Setup

- [x] **T001** Update requirements.txt with new dependencies
  - **File**: D:\00_dev\01_Ведомости\Юрчекер\law_ch\requirements.txt
  - **Action**: Add pymorphy3, petrovich, transliterate with pinned versions
  - **Example**:
    ```
    pymorphy3==1.2.0
    petrovich==1.0.5
    transliterate==1.10.2
    ```
  - **Validation**: Run `pip install -r requirements.txt` successfully

- [x] **T002** Create test directory structure
  - **Directories**:
    - D:\00_dev\01_Ведомости\Юрчекер\law_ch\tests\contract\
    - D:\00_dev\01_Ведомости\Юрчекер\law_ch\tests\integration\
    - D:\00_dev\01_Ведомости\Юрчекер\law_ch\tests\unit\
  - **Files**: Create __init__.py in each directory
  - **Validation**: `pytest --collect-only` runs without errors

- [x] **T003** [P] Create pytest configuration
  - **File**: D:\00_dev\01_Ведомости\Юрчекер\law_ch\pytest.ini
  - **Content**:
    ```ini
    [pytest]
    testpaths = tests
    python_files = test_*.py
    python_classes = Test*
    python_functions = test_*
    ```
  - **Validation**: `pytest --version` shows pytest configured correctly

---

## Phase 3.2: Tests First (TDD) ⚠️ MUST COMPLETE BEFORE 3.3
**CRITICAL: These tests MUST be written and MUST FAIL before ANY implementation**

### Contract Tests (from contracts/alias_expander.md)

- [x] **T004** [P] Contract test for name order expansion
  - **File**: D:\00_dev\01_Ведомости\Юрчекер\law_ch\tests\contract\test_name_orders.py
  - **Contract**: Contract 1 (expand_name_orders method)
  - **Test cases**:
    - Two-part name (no patronymic)
    - Three-part name (with patronymic)
    - Single-word name
  - **Expected**: Tests FAIL (method not implemented yet)
  - **Reference**: contracts/alias_expander.md lines 17-100

- [x] **T005** [P] Contract test for initial expansion
  - **File**: D:\00_dev\01_Ведомости\Юрчекер\law_ch\tests\contract\test_initials.py
  - **Contract**: Contract 2 (expand_initials method)
  - **Test cases**:
    - Single initial (no patronymic)
    - Double initial (with patronymic)
    - Unicode handling (Cyrillic initials)
  - **Expected**: Tests FAIL
  - **Reference**: contracts/alias_expander.md Contract 2

- [x] **T006** [P] Contract test for morphological case expansion
  - **File**: D:\00_dev\01_Ведомости\Юрчекер\law_ch\tests\contract\test_morphology.py
  - **Contract**: Contract 3 (expand_morphological_forms method)
  - **Test cases**:
    - Standard Russian surname (6 case forms)
    - Foreign surname (morphology fails, returns empty)
    - Feminine surname
  - **Expected**: Tests FAIL
  - **Reference**: contracts/alias_expander.md Contract 3

- [ ] **T007** [P] Contract test for transliteration
  - **File**: D:\00_dev\01_Ведомости\Юрчекер\law_ch\tests\contract\test_transliteration.py
  - **Contract**: Contract 4 (expand_transliterations method)
  - **Test cases**:
    - Basic transliteration (Cyrillic→Latin)
    - Phonetic simplification (Юрий→Yuri not Iurii)
    - Mixed script handling (skip or pass-through)
  - **Expected**: Tests FAIL
  - **Reference**: contracts/alias_expander.md Contract 4

- [ ] **T008** [P] Contract test for alias limit enforcement
  - **File**: D:\00_dev\01_Ведомости\Юрчекер\law_ch\tests\contract\test_alias_limit.py
  - **Contract**: Contract 5 (prioritize_aliases method)
  - **Test cases**:
    - Below limit (no truncation)
    - Exceeds limit (truncation to 100)
    - Prioritization order (original > cases > initials > diminutives > translit)
    - Logging verification (WARNING when truncated)
  - **Expected**: Tests FAIL
  - **Reference**: contracts/alias_expander.md Contract 5

- [ ] **T009** [P] Contract test for heuristic fallback
  - **File**: D:\00_dev\01_Ведомости\Юрчекер\law_ch\tests\contract\test_heuristic_fallback.py
  - **Contract**: Contract 6 (apply_heuristic_fallback method)
  - **Test cases**:
    - Foreign surname (Müller → suffix heuristics)
    - Rare Russian surname
    - Logging verification (WARNING with entity ID)
  - **Expected**: Tests FAIL
  - **Reference**: contracts/alias_expander.md Contract 6

- [ ] **T010** [P] Contract test for normalization
  - **File**: D:\00_dev\01_Ведомости\Юрчекер\law_ch\tests\contract\test_normalization.py
  - **Contract**: Contract 7 (normalize_alias method)
  - **Test cases**:
    - ё→е conversion
    - Lowercase conversion
    - Whitespace cleanup (multiple spaces→single space)
    - Hyphen and dot cleanup
    - Combined normalization
  - **Expected**: Tests FAIL
  - **Reference**: contracts/alias_expander.md Contract 7

- [ ] **T011** [P] Contract test for expand_all orchestration
  - **File**: D:\00_dev\01_Ведомости\Юрчекер\law_ch\tests\contract\test_expand_all.py
  - **Contract**: Contract 8 (expand_all method - integration)
  - **Test cases**:
    - Full person name (all expansion types applied)
    - Organization name (no diminutives)
    - Logging verification (alias count logged)
  - **Expected**: Tests FAIL
  - **Reference**: contracts/alias_expander.md Contract 8

### Integration Tests (from quickstart.md)

- [ ] **T012** [P] Integration test for full dictionary build cycle
  - **File**: D:\00_dev\01_Ведомости\Юрчекер\law_ch\tests\integration\test_full_build.py
  - **Scenario**: Add test entity to CSV, build dictionary, verify all variants findable
  - **Test steps**:
    1. Add TEST001 entity to CSV programmatically
    2. Delete cache
    3. Initialize JurChecker
    4. Verify build completes
    5. Test all variant types (morphology, initials, transliteration, diminutives)
  - **Expected**: Tests FAIL (AliasExpander not integrated yet)
  - **Reference**: quickstart.md Steps 1-3, test scenarios 3.3-3.10

- [ ] **T013** [P] Integration test for cache invalidation
  - **File**: D:\00_dev\01_Ведомости\Юрчекер\law_ch\tests\integration\test_cache_invalidation.py
  - **Scenario**: Modify CSV, verify cache rebuild triggered
  - **Test steps**:
    1. Build once (cache created)
    2. Modify CSV (change entity name)
    3. Re-initialize JurChecker
    4. Verify cache rebuild detected (hash mismatch)
    5. Verify new aliases present
  - **Expected**: Tests FAIL
  - **Reference**: quickstart.md Step 6.2

- [ ] **T014** Performance test for 2-minute build constraint
  - **File**: D:\00_dev\01_Ведомості\Юрчекер\law_ch\tests\integration\test_performance.py
  - **Scenario**: Build full registry, verify time <2 minutes, warnings logged
  - **Test steps**:
    1. Use full production CSV (or representative subset)
    2. Time dictionary build
    3. Assert build_time < 120 seconds
    4. If >90 seconds, verify WARNING logged
  - **Expected**: Tests FAIL
  - **Reference**: quickstart.md Step 5.1, FR-016c, FR-021

---

## Phase 3.3: Core Implementation (ONLY after tests T004-T014 are failing)

### AliasExpander Class Implementation

- [ ] **T015** Create AliasExpander class stub with __init__
  - **File**: D:\00_dev\01_Ведомости\Юрчекер\law_ch\jur_checker.py
  - **Action**: Add new class at end of file
  - **Code skeleton**:
    ```python
    class AliasExpander:
        def __init__(self, max_aliases: int = 100):
            self.max_aliases = max_aliases
            self.logger = logging.getLogger(__name__)
            # Initialize pymorphy3
            # Build diminutive map
            # Set priority weights
    ```
  - **Validation**: `from jur_checker import AliasExpander` succeeds
  - **Blocks**: T016-T024

- [ ] **T016** [P] Implement parse_person_name method
  - **File**: D:\00_dev\01_Ведомости\Юрчекер\law_ch\jur_checker.py
  - **Method**: `AliasExpander.parse_person_name(name: str) → tuple`
  - **Logic**: Split on whitespace, apply 1/2/3/4+ part patterns
  - **Reference**: research.md Section 4, data-model.md lines 141-162
  - **Validation**: Unit test or contract test passes

- [ ] **T017** [P] Implement expand_name_orders method
  - **File**: D:\00_dev\01_Ведомості\Юрчекер\law_ch\jur_checker.py
  - **Method**: `AliasExpander.expand_name_orders(first, patronymic, last) → list[str]`
  - **Logic**: Generate "First Last", "Last First", "First Patronymic Last"
  - **Reference**: data-model.md lines 164-200, Contract 1
  - **Validation**: T004 contract test passes

- [ ] **T018** [P] Implement expand_initials method
  - **File**: D:\00_dev\01_Ведомості\Юрчекер\law_ch\jur_checker.py
  - **Method**: `AliasExpander.expand_initials(first, patronymic, last) → list[str]`
  - **Logic**: Extract first letters, format "I. Last", "Last I.", "I.P. Last", etc.
  - **Reference**: data-model.md lines 202-235, Contract 2
  - **Validation**: T005 contract test passes

- [ ] **T019** Implement expand_diminutives method
  - **File**: D:\00_dev\01_Ведомості\Юрчекер\law_ch\jur_checker.py
  - **Method**: `AliasExpander.expand_diminutives(first_name: str) → list[str]`
  - **Logic**: Lookup in self.diminutive_map (built from petrovich or hardcoded)
  - **Reference**: research.md Section 2, data-model.md lines 237-253
  - **Depends on**: T015 (diminutive_map initialized in __init__)
  - **Validation**: Test with "Алексей" → ["Лёша", "Леша", "Алекс"]

- [ ] **T020** Implement expand_transliterations method
  - **File**: D:\00_dev\01_Ведомості\Юрчекер\law_ch\jur_checker.py
  - **Method**: `AliasExpander.expand_transliterations(variants: list[str]) → list[str]`
  - **Logic**: Use transliterate library, simplified phonetic mode
  - **Reference**: research.md Section 3, data-model.md lines 255-285, Contract 4
  - **Validation**: T007 contract test passes

- [ ] **T021** Implement expand_morphological_forms method
  - **File**: D:\00_dev\01_Ведомості\Юрчекер\law_ch\jur_checker.py
  - **Method**: `AliasExpander.expand_morphological_forms(surname: str) → list[str]`
  - **Logic**: Use pymorphy3, extract lexeme, fallback if confidence <0.5
  - **Reference**: research.md Section 1, data-model.md lines 287-320, Contract 3
  - **Depends on**: T022 (fallback method)
  - **Validation**: T006 contract test passes

- [ ] **T022** Implement apply_heuristic_fallback method
  - **File**: D:\00_dev\01_Ведомості\Юрчекер\law_ch\jur_checker.py
  - **Method**: `AliasExpander.apply_heuristic_fallback(surname: str, entity_id: str) → list[str]`
  - **Logic**: Add suffixes -ого, -ому, -ым, -ом; log WARNING
  - **Reference**: data-model.md lines 322-351, Contract 6
  - **Validation**: T009 contract test passes

- [ ] **T023** [P] Implement normalize_alias method
  - **File**: D:\00_dev\01_Ведомості\Юрчекер\law_ch\jur_checker.py
  - **Method**: `AliasExpander.normalize_alias(alias: str) → str`
  - **Logic**: ё→е, lowercase, regex [\s\.\-]+ → space, strip
  - **Reference**: research.md Section 6, data-model.md lines 353-375, Contract 7
  - **Validation**: T010 contract test passes

- [ ] **T024** Implement prioritize_aliases method
  - **File**: D:\00_dev\01_Ведомості\Юрчекер\law_ch\jur_checker.py
  - **Method**: `AliasExpander.prioritize_aliases(aliases, original, entity_id) → list[str]`
  - **Logic**: Assign scores, sort, take top 100, log WARNING if truncated
  - **Reference**: research.md Section 5, data-model.md lines 377-411, Contract 5
  - **Validation**: T008 contract test passes

- [ ] **T025** Implement expand_all orchestrator method
  - **File**: D:\00_dev\01_Ведомості\Юрчекер\law_ch\jur_checker.py
  - **Method**: `AliasExpander.expand_all(entity_name: str, entity_type: str) → list[str]`
  - **Logic**: Call all expansion methods, normalize, deduplicate, prioritize, log count
  - **Reference**: data-model.md lines 79-107
  - **Depends on**: T016-T024 (all methods must exist)
  - **Validation**: T011 contract test passes

---

## Phase 3.4: Integration

- [ ] **T026** Integrate AliasExpander into JurChecker._load_and_prepare_data
  - **File**: D:\00_dev\01_Ведомості\Юрчекер\law_ch\jur_checker.py
  - **Method**: Modify `JurChecker._load_and_prepare_data`
  - **Changes**:
    1. Initialize `expander = AliasExpander()` before loop
    2. Start build timer
    3. For each entity: `aliases = expander.expand_all(entity_data['name'], entity_data['type'])`
    4. Add all aliases to automaton (replace single name addition)
    5. Log alias count per entity (FR-017)
    6. After loop: log total build time, warn if >90s (FR-021)
  - **Reference**: data-model.md lines 417-490
  - **Depends on**: T025 (expand_all must work)
  - **Validation**: T012 integration test passes

- [ ] **T027** Add logging for alias counts and performance warnings
  - **File**: D:\00_dev\01_Ведомості\Юрчекер\law_ch\jur_checker.py
  - **Locations**: Multiple (within T026 integration + AliasExpander methods)
  - **Logging additions**:
    - INFO: "Entity {id}: {count} aliases generated" (FR-017)
    - INFO: "Реестр успешно загружен. {total} ключевых слов. Build time: {time}s" (FR-019)
    - WARNING: "Build time ({time}s) approaching 2-minute limit" if >90s (FR-021)
    - WARNING: "Morphological fallback for entity {id}, surname='{name}'" (FR-018)
    - WARNING: "Entity {id} exceeded alias limit ({generated} generated, {kept} kept)" (FR-016b)
  - **Reference**: data-model.md lines 618-656
  - **Validation**: Review logs during manual quickstart testing

---

## Phase 3.5: Polish

- [ ] **T028** [P] Unit tests for name parsing edge cases
  - **File**: D:\00_dev\01_Ведомості\Юрчекер\law_ch\tests\unit\test_name_parsing.py
  - **Test cases**:
    - Compound surnames (hyphenated)
    - Multiple given names (4+ parts)
    - Single-word names
  - **Validation**: All edge cases covered

- [ ] **T029** [P] Unit tests for normalization edge cases
  - **File**: D:\00_dev\01_Ведомості\Юрчекер\law_ch\tests\unit\test_normalization.py
  - **Test cases**:
    - Mixed Cyrillic/Latin
    - Unicode handling
    - Empty/whitespace-only input
  - **Validation**: Normalization robust

- [ ] **T030** Run manual quickstart validation
  - **File**: specs/001-dictionary-expansion/quickstart.md
  - **Action**: Follow all steps 1-7 manually
  - **Checklist**:
    - Add TEST001 entity to CSV
    - Verify all 10 API test scenarios pass
    - Check logs for correct alias counts, build time, warnings
    - Verify backward compatibility (existing entities still work)
    - Test cache invalidation
  - **Validation**: All acceptance criteria pass (quickstart.md summary table)

---

## Dependencies

### Setup Phase
- T001 (dependencies) must complete before any code changes
- T002, T003 (test structure) before any tests can be written

### TDD Discipline
- **CRITICAL**: All tests (T004-T014) MUST FAIL before starting T015
- Tests must be written and failing to comply with constitutional TDD requirement

### Core Implementation
- T015 (AliasExpander stub) blocks all method implementations (T016-T025)
- T022 (heuristic fallback) must exist before T021 (morphology) can call it
- T025 (expand_all) requires T016-T024 complete

### Integration Phase
- T026 (JurChecker integration) requires T025 (expand_all working)
- T027 (logging) can happen alongside T026 or after

### Parallel Opportunities
- **Contract tests (T004-T011)**: All [P] - different files
- **Method implementations (T016-T018, T020, T023)**: [P] - different methods, independent
- **Integration tests (T012-T013)**: [P] - different test files

### Sequential Constraints
- T019 (diminutives) depends on T015 (init builds diminutive_map)
- T021 (morphology) calls T022 (fallback) - T022 must exist first
- T024 (prioritize) uses helper methods - can be parallel with other methods
- T025 (expand_all) orchestrates all methods - MUST be last in core phase

---

## Parallel Execution Examples

### Launch all contract tests together (after T003):
```bash
# Parallel contract test execution
pytest tests/contract/test_name_orders.py &
pytest tests/contract/test_initials.py &
pytest tests/contract/test_morphology.py &
pytest tests/contract/test_transliteration.py &
pytest tests/contract/test_alias_limit.py &
pytest tests/contract/test_heuristic_fallback.py &
pytest tests/contract/test_normalization.py &
pytest tests/contract/test_expand_all.py &
wait
```

### Launch independent method implementations (after T015):
```python
# Task agent commands for parallel method implementation
Task: "Implement parse_person_name method in jur_checker.py per data-model.md"
Task: "Implement expand_name_orders method in jur_checker.py per Contract 1"
Task: "Implement expand_initials method in jur_checker.py per Contract 2"
Task: "Implement normalize_alias method in jur_checker.py per Contract 7"
# These can run in parallel - different methods, no interdependencies
```

---

## Validation Checklist
*GATE: Verified before considering feature complete*

- [x] All contracts have corresponding tests (T004-T011 cover all 8 contracts)
- [x] All entities have model tasks (AliasExpander class covered by T015-T025)
- [x] All tests come before implementation (T004-T014 before T015-T027)
- [x] Parallel tasks truly independent (verified: different files or different methods)
- [x] Each task specifies exact file path (all tasks have explicit paths)
- [x] No task modifies same file as another [P] task (verified: jur_checker.py tasks are sequential)

---

## Notes

### TDD Enforcement
- **Constitutional requirement**: Tests MUST be written first and MUST fail
- Run `pytest tests/contract/` after T004-T011 → expect 100% failures
- Run `pytest tests/integration/` after T012-T014 → expect failures
- Implementation (T015-T027) turns failures to passes

### Performance Targets
- Build time <2 minutes (FR-016c) validated by T014
- Warning at 90 seconds (FR-021) validated by T014 + T027 logging
- Alias limit 100 per entity (FR-016a) validated by T008

### Commit Strategy
- Commit after each completed task (atomic commits)
- Suggested commit messages:
  - T001: "chore: add alias expansion dependencies"
  - T004: "test: add contract test for name order expansion (failing)"
  - T017: "feat: implement name order expansion (T004 passes)"
  - T026: "feat: integrate AliasExpander into JurChecker build phase"
  - T030: "test: validate quickstart acceptance criteria"

### Common Pitfalls to Avoid
- ❌ Implementing before tests written (violates TDD)
- ❌ Running [P] tasks sequentially (wastes time)
- ❌ Vague task descriptions (each task is specific and actionable)
- ❌ Same file conflicts (jur_checker.py edits are ordered sequentially)

---

**Total Tasks**: 30 (Setup: 3, Tests: 11, Core: 11, Integration: 2, Polish: 3)
**Estimated Completion Time**: 12-16 hours (assuming parallel execution where marked)
**Critical Path**: T001 → T002 → (T004-T014 parallel) → T015 → T025 → T026 → T030

**Ready for execution**: Yes ✓
