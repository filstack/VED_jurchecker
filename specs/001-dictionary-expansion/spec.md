# Feature Specification: Dictionary Alias Expansion

**Feature Branch**: `001-dictionary-expansion`
**Created**: 2025-10-06
**Status**: Draft
**Input**: User description: "1) Расширение алиасов (Dictionary Expansion) При компиляции словаря автоматически генерируй варианты..."

## Execution Flow (main)
```
1. Parse user description from Input
   → If empty: ERROR "No feature description provided"
2. Extract key concepts from description
   → Identify: actors, actions, data, constraints
3. For each unclear aspect:
   → Mark with [NEEDS CLARIFICATION: specific question]
4. Fill User Scenarios & Testing section
   → If no clear user flow: ERROR "Cannot determine user scenarios"
5. Generate Functional Requirements
   → Each requirement must be testable
   → Mark ambiguous requirements
6. Identify Key Entities (if data involved)
7. Run Review Checklist
   → If any [NEEDS CLARIFICATION]: WARN "Spec has uncertainties"
   → If implementation details found: ERROR "Remove tech details"
8. Return: SUCCESS (spec ready for planning)
```

---

## ⚡ Quick Guidelines
- ✅ Focus on WHAT users need and WHY
- ❌ Avoid HOW to implement (no tech stack, APIs, code structure)
- 👥 Written for business stakeholders, not developers

### Section Requirements
- **Mandatory sections**: Must be completed for every feature
- **Optional sections**: Include only when relevant to the feature
- When a section doesn't apply, remove it entirely (don't leave as "N/A")

### For AI Generation
When creating this spec from a user prompt:
1. **Mark all ambiguities**: Use [NEEDS CLARIFICATION: specific question] for any assumption you'd need to make
2. **Don't guess**: If the prompt doesn't specify something (e.g., "login system" without auth method), mark it
3. **Think like a tester**: Every vague requirement should fail the "testable and unambiguous" checklist item
4. **Common underspecified areas**:
   - User types and permissions
   - Data retention/deletion policies
   - Performance targets and scale
   - Error handling behaviors
   - Integration requirements
   - Security/compliance needs

---

## Clarifications

### Session 2025-10-06
- Q: What should be the source of diminutive name mappings? → A: petrovich/pymorphy3 + словарь имён
- Q: Which transliteration standard should the system use for Cyrillic→Latin conversion? → A: Simplified phonetic
- Q: When morphological analyzer fails to parse a surname, what should the system do? → A: Heuristics + log warning
- Q: What is the maximum acceptable number of generated aliases per entity? → A: 100 aliases per entity
- Q: What is the maximum acceptable dictionary build time (from CSV load to cached automaton ready)? → A: <2 minutes

---

## User Scenarios & Testing *(mandatory)*

### Primary User Story
The JurChecker service needs to improve entity detection recall by automatically expanding entity names into multiple searchable variants during dictionary compilation. When an entity entry (person name or organization) is loaded from the CSV registry, the system should generate multiple alias forms to match how entities might be mentioned in real Russian legal texts—including different name orders, initials, diminutive forms, transliterations, morphological case variants, and normalized punctuation.

This expansion happens **offline during dictionary build time**, not at query time, ensuring no performance impact on the production search API.

### Acceptance Scenarios

1. **Given** a person entity "Алексей Анатольевич Навальный" in the registry, **When** the dictionary is compiled, **Then** the system generates aliases including:
   - Name order variants: "Алексей Навальный", "Навальный Алексей"
   - Initial variants: "А. Навальный", "Навальный А.", "А.А. Навальный", "Навальный А.А."
   - Morphological forms: "Навального", "Навальному", "Навальным", "Навальном"
   - Transliteration: "Navalny", "Alexey Navalny", "A. Navalny"
   - Normalized punctuation: all variants with spaces normalized from sequences of `[\s\.\-]+`

2. **Given** an entity with diminutive name forms (e.g., "Алексей"), **When** aliases are expanded, **Then** variants include "Лёша", "Леша", "Алекс" generated from petrovich/pymorphy3 name dictionaries

3. **Given** an entity name containing "ё" characters, **When** aliases are generated, **Then** both "ё" and "е" normalized variants are included in the automaton

4. **Given** a person's surname, **When** morphological expansion is applied, **Then** the system uses pymorphy3/pymorphy2 to generate all Russian case forms (nominative, genitive, dative, accusative, instrumental, prepositional)

5. **Given** a rare or foreign surname that morphological analyzer cannot process, **When** expansion occurs, **Then** the system applies heuristic suffixes (-ого, -ому, -ым, -ом) as fallback variants and logs a warning for manual review

### Edge Cases
- When morphological analyzer fails, system applies heuristic suffixes and logs warnings for manual review queue
- How does the system handle names that are already in non-standard order or contain unusual punctuation?
- How should the system handle names with non-standard romanizations already present in source documents?
- How should the system handle entity names with more than 3 parts (e.g., compound surnames or multiple given names)?
- System enforces maximum of 100 generated aliases per entity to prevent dictionary explosion

## Requirements *(mandatory)*

### Functional Requirements

**Name Order & Initials**
- **FR-001**: System MUST generate both "FirstName LastName" and "LastName FirstName" variants for person names
- **FR-002**: System MUST generate initial variants: "I. LastName", "LastName I." (single initial)
- **FR-003**: System MUST generate patronymic initial variants: "I.P. LastName", "LastName I.P." (first + patronymic initials)
- **FR-004**: System MUST preserve original full name as one of the aliases

**Diminutive Forms**
- **FR-005**: System MUST expand common Russian first names into diminutive variants using petrovich or pymorphy3 name dictionaries (e.g., Алексей → Лёша, Леша, Алекс)

**Transliteration**
- **FR-006**: System MUST generate Latin transliteration variants for Russian names using simplified phonetic transliteration (prioritizing English readability, e.g., Юрий → Yuri)
- **FR-007**: System MUST generate transliterated initial variants (e.g., "A. Navalny", "Alexey Navalny")

**Text Normalization**
- **FR-008**: System MUST normalize all sequences of spaces, dots, and hyphens `[\s\.\-]+` to a single space when generating alias keys
- **FR-009**: System MUST convert "ё" to "е" for all generated aliases
- **FR-010**: System MUST apply case normalization (lowercase) to all generated aliases before adding to Aho-Corasick automaton

**Morphological Case Forms**
- **FR-011**: System MUST generate all Russian case forms (genitive, dative, accusative, instrumental, prepositional) for person surnames using pymorphy3 or pymorphy2
- **FR-012**: System MUST apply morphological analysis at dictionary build time (offline), not at query time
- **FR-013**: System MUST apply heuristic suffix rules (-ого, -ому, -ым, -ом) when morphological analyzer fails to parse foreign/rare surnames
- **FR-013a**: System MUST log warnings with entity details when heuristic fallback is applied, enabling manual review queue generation

**Cache & Performance**
- **FR-014**: System MUST include all expanded aliases in the pickle-cached Aho-Corasick automaton
- **FR-015**: System MUST invalidate cache when CSV registry is updated (existing hash-based mechanism)
- **FR-016**: Alias expansion MUST NOT impact query-time performance (all expansion at build time)
- **FR-016a**: System MUST limit generated aliases to maximum 100 per entity to prevent dictionary explosion
- **FR-016b**: When alias limit is reached, system MUST log warning with entity ID and prioritize most common variant types (order: original, case forms, initials, diminutives, transliterations)
- **FR-016c**: Dictionary build time (CSV load through automaton finalization and caching) MUST complete within 2 minutes

**Logging & Observability**
- **FR-017**: System MUST log the count of generated aliases per entity at INFO level during dictionary build
- **FR-018**: System MUST log warnings with entity ID and name when morphological analysis fails and heuristic fallback is applied
- **FR-019**: System MUST log total dictionary size (unique alias count) and total build time after expansion
- **FR-020**: System MUST aggregate fallback warnings to enable manual review queue generation
- **FR-021**: System MUST log performance warning if dictionary build exceeds 90 seconds (approaching 2-minute limit)

### Key Entities

- **Entity**: Core registry entry with `id`, `name`, `type`, and existing `aliases` (JSON array from CSV)
- **Alias Variant**: Generated searchable form of entity name (e.g., initial form, case form, transliteration)
- **Morphological Form**: Russian case variant of a surname (nominative, genitive, dative, accusative, instrumental, prepositional)
- **Diminutive Mapping**: Relationship between formal first name and its diminutive forms sourced from petrovich/pymorphy3 dictionaries (e.g., Алексей → [Лёша, Леша, Алекс])
- **Transliteration Rule**: Mapping between Cyrillic and Latin character representations using simplified phonetic approach for English readability

---

## Review & Acceptance Checklist
*GATE: Automated checks run during main() execution*

### Content Quality
- [x] No implementation details (languages, frameworks, APIs)
- [x] Focused on user value and business needs
- [x] Written for non-technical stakeholders
- [x] All mandatory sections completed

### Requirement Completeness
- [x] No [NEEDS CLARIFICATION] markers remain
- [x] Requirements are testable and unambiguous
- [x] Success criteria are measurable
- [x] Scope is clearly bounded
- [x] Dependencies and assumptions identified

---

## Execution Status
*Updated by main() during processing*

- [x] User description parsed
- [x] Key concepts extracted
- [x] Ambiguities marked
- [x] User scenarios defined
- [x] Requirements generated
- [x] Entities identified
- [x] Review checklist passed
- [x] Clarifications complete (5 questions answered)

---
