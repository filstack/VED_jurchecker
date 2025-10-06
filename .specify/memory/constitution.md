<!--
SYNC IMPACT REPORT
==================
Version Change: Template → 1.0.0 (MAJOR - Initial ratification)

Modified Principles:
- PRINCIPLE_1 → I. Production Stability First
- PRINCIPLE_2 → II. Performance & Caching
- PRINCIPLE_3 → III. Data Integrity & Validation
- PRINCIPLE_4 → IV. API Contract Stability
- PRINCIPLE_5 → V. Minimal Dependencies

Added Sections:
- Production Operations (Deployment Standards, Error Handling, Data Management)
- Development Workflow (Testing Requirements, Code Quality, Change Management)

Removed Sections:
- None (all template sections filled)

Templates Requiring Updates:
✅ plan-template.md - Constitution Check section references verified
✅ spec-template.md - No updates required (technology-agnostic)
✅ tasks-template.md - Testing discipline aligns with principles
⚠️  No command files found in .specify/templates/commands/ - skipped

Follow-up TODOs:
- None - all placeholders resolved

Generation Date: 2025-10-06
-->

# JurChecker Constitution

## Core Principles

### I. Production Stability First
The system MUST maintain stability and reliability as a production service. All changes MUST preserve backward compatibility with existing n8n integrations. Deployments MUST be zero-downtime. Breaking changes require explicit versioning and migration paths.

**Rationale**: This is a live production service integrated with n8n workflows. Downtime or breaking changes directly impact operational workflows and data processing pipelines.

### II. Performance & Caching
Initialization operations MUST be cached to avoid repeated expensive computations. The Aho-Corasick automaton MUST be cached via pickle with CSV hash validation. Cold start time MUST be minimized through persistent caching. Cache invalidation MUST be automatic when source data changes.

**Rationale**: Loading and building search automaton from CSV is expensive. Production services require fast startup and response times. Cache management prevents unnecessary recomputation while ensuring data freshness.

### III. Data Integrity & Validation
CSV registry data MUST be the single source of truth. All input text MUST be normalized (lowercase, ё→е) before processing. Entity matching MUST validate word boundaries to prevent false positives. Response data MUST include context (±150 chars) for verification.

**Rationale**: Legal entity matching requires precision. False positives and false negatives have business consequences. Contextual data enables downstream AI verification through n8n.

### IV. API Contract Stability
FastAPI endpoints MUST maintain fixed request/response schemas. POST /check-candidates accepts `{"text": str}` and returns structured candidate lists. Health endpoint MUST report service readiness. Pydantic models enforce schema validation at runtime.

**Rationale**: n8n integration depends on stable API contracts. Schema changes break workflow automation. Runtime validation prevents silent failures.

### V. Minimal Dependencies
Dependencies MUST be pinned to exact versions in requirements.txt. Production stack MUST remain: FastAPI, uvicorn, pandas, pyahocorasick, pydantic. New dependencies require justification for production stability and security implications.

**Rationale**: Dependency drift causes production incidents. Security vulnerabilities in dependencies pose risks. Minimal surface area reduces attack vectors and maintenance burden.

## Production Operations

### Deployment Standards
- **Platform**: Python 3.10+ server running uvicorn on port 8001
- **Process Management**: Single uvicorn process with startup event handlers
- **Data Files**: registry_entities_rows.csv MUST be present at startup
- **Cache Location**: .cache/ directory for automaton persistence
- **Logging**: Standard Python logging module to stdout/stderr for process managers
- **Health Checks**: /health endpoint for monitoring and load balancer probes

### Error Handling
- File not found (CSV) → HTTP 503 Service Unavailable at startup
- Checker not initialized → HTTP 503 on requests with explicit error message
- Invalid request payload → HTTP 422 with Pydantic validation details
- Cache corruption → Fall back to full rebuild, log warning
- All errors MUST be logged with timestamps and context

### Data Management
- CSV updates MUST invalidate cache automatically via hash comparison
- No external database required - CSV is sufficient for current scale
- Entity deduplication by ID within single request to prevent duplicate results
- Context extraction from original (non-normalized) text preserves formatting

## Development Workflow

### Testing Requirements
- Contract tests for API endpoints (request/response validation)
- Integration tests for JurChecker initialization and caching
- Unit tests for text normalization and word boundary detection
- Performance tests ensuring <100ms response time for typical texts
- Cache invalidation tests validating hash-based freshness

### Code Quality
- Type hints MUST be used (FastAPI requires them for docs generation)
- Docstrings required for public classes and methods
- Logging at INFO level for lifecycle events, WARNING for fallbacks
- No print statements - use logging module exclusively
- Code MUST pass type checking (mypy) and linting (ruff/flake8)

### Change Management
- All changes MUST be tested on development instance before production
- API changes require version bump and changelog entry
- Performance regressions MUST be investigated and resolved
- Breaking changes MUST include migration documentation

## Governance

### Amendment Process
1. Proposed changes MUST document rationale and impact
2. Breaking principle changes require major version bump
3. New principles or expanded guidance require minor version bump
4. Clarifications and wording fixes require patch version bump
5. All amendments MUST verify consistency with plan-template.md, spec-template.md, and tasks-template.md

### Compliance Review
- All feature plans MUST include Constitution Check section
- Code reviews MUST verify adherence to production stability principles
- Performance requirements MUST be validated before deployment
- Dependency additions MUST be approved and security-reviewed

### Constitutional Authority
This constitution supersedes all other development practices and coding preferences. When in doubt, production stability and API contract stability take precedence. Complexity must be justified against operational requirements.

**Version**: 1.0.0 | **Ratified**: 2025-10-06 | **Last Amended**: 2025-10-06
