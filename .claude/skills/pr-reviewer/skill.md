---
name: pr-reviewer
description: >
  Deep PR review for the semantic-search-engine project. Reviews from business
  and technical perspectives, checks architecture alignment, Python standards,
  security, performance, and resource usage. Outputs findings in three severity
  tiers: critical, moderate, minor.
---

# PR Review — Semantic Search Engine

Review the current PR (or PR number $ARGUMENTS if provided) following the steps below.
Do not skip steps — each phase informs the next.

---

## Ground Rules

- **Read before finding.** Never surface findings from memory or assumptions — read the actual diff and files.
- **Stop on missing context.** If the PR, branch, or description is inaccessible — report what's missing and stop.
- **Read-only by default.** Do not post comments, approve, or trigger write operations unless explicitly instructed in this session.
- **Use `gh` CLI and `git` for all GitHub interactions.**
- **Confidence label on every finding:**
  - 🔴 Certain — verifiable fact, clear rule violation
  - 🟡 Likely — strong signal, warrants investigation
  - ⚪ Opinion — style, preference, or architectural suggestion

---

## Phase 1 — Context

**Goal: understand WHY this PR exists before looking at any code.**

```
gh pr view          # description, linked issues, labels, assignees
gh pr checks        # CI status — failing build shifts review priority
git log --oneline origin/main..HEAD   # commit intent and scope coherence
git diff --stat origin/main..HEAD     # file-level map before diving deeper
```

**Extract:**
- The problem being solved
- The proposed solution at a high level
- Explicit constraints or decisions the author called out

If the PR description is missing or vague, flag this as a **moderate** issue:
*"PR lacks context — reviewer cannot verify intent against implementation."*

If `gh pr checks` shows failing checks, note them immediately. A broken build shifts priority: verify correctness of the broken path first, style and quality second.

Note any out-of-place commits from `git log` — they may indicate unintended scope.

---

## Phase 2 — Solution Validation

**Goal: verify the implementation actually solves the stated problem.**

### Before reading any file — find the analogous module

Find the closest existing module that resembles what the PR adds or changes (e.g., new connector → existing connector; new pipeline stage → existing stage). One read pass — compare structure and key patterns only, not line by line. Note divergences; use PR description and commit messages from Phase 1 to judge intentional improvement vs. unintentional inconsistency. Reference this comparison in findings.

If no analogous module exists (entirely new capability), skip and note it in the Context Summary.

### Reading the changed files

Use `git diff --stat` from Phase 1 to classify changed files:
- **Core** — domain models, pipeline stages, connectors, embedding logic
- **Infrastructure** — config, Azure Functions, Cosmos queries, deployment
- **Tests** — unit, integration, fixtures
- **Supporting** — logging, utilities, type aliases, constants

Check structural coherence: is the PR focused or does it mix unrelated concerns? Is there anything changed that the PR description doesn't mention?

Read the **full resulting file**, not just the diff. If the PR changes more than 5 core files, start with the entry point and most heavily modified modules; apply all five validation questions below to those. For remaining files, apply only question 1 and flag obvious correctness issues.

Phases 2 and 3 read the same files — you may combine passes if more natural; they are separated by perspective (intent vs. technical quality), not by when you open the file.

### Validate — for each core file

1. Does this code solve the problem stated in Phase 1?
2. Are **happy path and error path** both handled?
3. Are edge cases covered — null/empty input, large input, external service failure?
4. Will this behave correctly under the load or scale the project targets?
5. Does it introduce **observable behavior change** beyond stated scope?
   *Observable = changed output, different exceptions raised, altered side effects (Cosmos writes, external API calls). Log wording and internal restructuring without behavior change do not count.*

### Flag

- Contradictions with the PR description
- Observable behavior changes not mentioned in the PR (scope creep)
- Missing conditions the PR claims to handle
- Better alternative approaches — only when the tradeoff is clear and worth raising

---

## Phase 3 — Code Quality

**Review in 3 states:**

### A. Before Changes

Focus on the *specific files being changed* — not the analogous module from Phase 2, which you already have context on.

- Read existing code being modified
- Understand current patterns and conventions in these files
- Note current error handling approach
- Document current behavior (what it does today, before the PR)

### B. The Changes

- What is being added / removed / modified
- Why these specific changes (from Phase 1 context)
- Scope and impact
- Breaking vs. non-breaking

### C. After Changes

- Final code state analysis
- Verify consistency with codebase conventions
- Check alignment with existing patterns
- Validate no regressions

Only report findings from the checklists below — skip items with no issues.

### Consistency with existing codebase

- ❌ Naming deviates from established conventions
- ❌ Error handling or logging style differs from surrounding patterns
- ❌ Connector / pipeline / store integration approach diverges without justification
- ❌ Async patterns inconsistent with existing code

### Python Standards (see `semantic-search-python` skill for full reference)

- [ ] Type annotations use 3.10+ syntax: `list[str]`, `dict[str, int]`, `X | None`
      — never `Optional`, `List`, `Dict`, `Union` from `typing`
- [ ] Pydantic models use v2 syntax: `model_config`, `field_validator` with `@classmethod`,
      `model_dump()` — never `.dict()`, `.parse_obj()`, `@validator`
- [ ] Async code uses `TaskGroup` for concurrent I/O — not bare `asyncio.gather()`
- [ ] No blocking I/O inside `async def`: no `requests`, no `open()` without
      `asyncio.to_thread`, no `time.sleep()`
- [ ] **Async cleanup** — async resources (HTTP sessions, DB connections) are opened and
      closed inside `async with` or `asynccontextmanager`; no bare `try/finally` managing
      async resources manually; task cancellation does not leak open connections
- [ ] Plugin interfaces use `Protocol`, not `ABC`
- [ ] New connectors self-register via `ConnectorRegistry` — no manual wiring
- [ ] Config reads from `Settings` (pydantic-settings) — never `os.getenv()` directly
- [ ] File paths use `pathlib.Path` — never `os.path`
- [ ] Logging uses `logger.info("... %s", value)` — never f-strings in log calls,
      never bare `print()`
- [ ] Exceptions follow the project hierarchy: `SemanticSearchError` → specific subclass
- [ ] **Error observability** — every caught exception that is not re-raised logs enough
      context to debug it in production (which document, which connector, which operation
      failed); bare `except: pass` and silent swallows are always a finding
- [ ] **Type annotation completeness** — all public functions and methods have parameter
      and return type annotations; `Any` is not used as an escape hatch without a comment
      explaining why it cannot be avoided
- [ ] **Public API docstrings** — every public function, class, and method added or modified
      has at least a one-line docstring describing what it does (not how)

### Security

- [ ] No hardcoded secrets, API keys, connection strings, or tokens
- [ ] All secret config fields use `SecretStr` — never plain `str`
- [ ] Secrets are never logged, even at DEBUG level (check `.get_secret_value()` call sites)
- [ ] All external input (user queries, document content, webhook payloads) is validated
      with Pydantic before use
- [ ] No shell injection: `subprocess` calls use list form, never string interpolation
- [ ] CosmosDB queries use parameterized form — no string-concatenated queries

### Performance
*(covers non-LLM operations — for LLM/embedding batching see Resource Usage below)*

- [ ] No N+1 patterns: document/chunk processing is batched, not looped one-by-one
      (if the loop calls the embedding model, report under Resource Usage instead)
- [ ] Async I/O is actually concurrent where parallelism is possible (`TaskGroup`)
- [ ] No large in-memory collections that grow unbounded with input size
- [ ] Expensive operations (Cosmos reads, heavy transforms) are not duplicated inside loops

### Resource Usage — Critical for this project
*(covers LLM/embedding calls and cloud service consumption specifically)*

- [ ] **LLM/embedding calls are batched** — `embedding_batch_size` from `Settings` is respected;
      no single-document embedding calls in a loop
- [ ] **Token budgets are enforced** — chunks sent to LLMs have token counts validated
      before the call, not after
- [ ] **No runaway Cosmos RU consumption** — point reads used where possible,
      cross-partition queries justified and bounded
- [ ] **External API rate limits respected** — connectors implement backoff/retry,
      not tight loops on failure
- [ ] **No redundant re-embedding** — deduplication or caching is in place before
      calling the embedding model

### Supporting files — lighter pass

- Config changes: are new fields typed correctly, defaulted safely, documented in `Settings`?
- Azure Function changes: are bindings correct, are secrets sourced from Key Vault references,
  not plaintext app settings?

### Testing (pragmatic approach)

**Unit tests — cover:**
- ✅ Complex business logic, critical algorithms, error handling paths
- ✅ Edge cases that matter (empty input, boundaries, external service failure)
- ❌ Avoid: trivial code, simple accessors, framework functionality

**Integration tests — required for:**
- ✅ Connector implementations against real or stubbed external services
- ✅ Cosmos read/write paths
- ✅ Full pipeline stage outputs

**Test quality — check each explicitly:**

- **Behavior vs. execution** — assertions verify *what* the code does, not just that it doesn't throw; `assert result is not None` is not a meaningful test
- **Mock scope** — mocks applied at the right boundary (external I/O only); mocking internal project code usually tests the wrong thing
- **Failure paths** — at least one test per public function covers an error case; "public function" means any function or method not prefixed with `_`, including async functions and class methods
- **Fixture realism** — fixtures resemble real data shapes; fake data with wrong types or missing required fields misses entire categories of bugs
- **Assertion specificity** — `assert len(results) == 3` is weaker than asserting actual content; flag tests where the assertion could pass for the wrong reason

---

## Phase 4 — Design & Architecture

**Goal: verify the change is coherent at a structural level — not just correct line by line. Only report findings — skip sub-sections with no issues.**

For every finding, suggest the improvement and explain the tradeoff — design observations without a concrete alternative are not actionable.

### Dependency direction

- Must flow inward: `connector → processor → pipeline → store`. Lower layers do not import higher layers.
- New code depends on abstractions (`Protocol`), not concretions.
- Lower layer importing a higher layer = always a finding.

### Cohesion & coupling

- Each class/module should have one reason to change. Flag classes mixing concerns (e.g., orchestrating pipeline logic and constructing HTTP requests).
- High fan-out (one class importing many unrelated dependencies) is a smell.
- New abstractions should group things that genuinely change together; splitting for the sake of splitting increases coupling without improving cohesion.

### Layer & boundary integrity

- Pipeline stages: thin only — receive input chunk/document, run transform, yield output. No I/O inside a stage.
- Business logic must not leak into connectors, config parsing, or Azure Function bindings.
- DTOs and domain models must be separate types; flag any Pydantic model used both as a wire format and in pipeline logic.

### Encapsulation

- Domain objects protect their own state — callers cannot put them into invalid state.
- Internals not exposed unnecessarily.
- Prefer frozen dataclasses or Pydantic models with `model_config = ConfigDict(frozen=True)` for value objects.
- If the PR makes previously encapsulated state public to satisfy a new requirement, question whether that is the right approach.

### SOLID in Python

- **S** — Single responsibility: each new/modified class has one reason to change.
- **O** — Open/closed: extension via new `Protocol` implementations, not modifying existing logic branches.
- **L** — Liskov: `Protocol` implementors satisfy the full contract; no silent no-ops or surprise exceptions.
- **I** — Interface segregation: `Protocol`s are focused; clients not forced to depend on methods they don't use.
- **D** — Dependency inversion: high-level pipeline code depends on `Protocol` abstractions, not concrete connectors or store implementations.

### Anti-patterns to flag

- **God Object** — one class accumulating unrelated responsibilities
- **Primitive Obsession** — domain concepts (ChunkId, DocumentUrl) as raw `str`/`int`
- **Anemic Model** — domain objects are pure data bags; all logic in services
- **Shotgun Surgery** — PR touches many unrelated files for one conceptual change (missing abstraction)
- **Service Locator** — resolving dependencies at runtime instead of injecting via constructor or function parameter

### Change impact

- **Backwards compatibility** — if the PR changes a public interface (function signature, Pydantic model fields, Protocol method), search call sites before declaring safe. Breaking without updating all callers = 🔴 Critical.
- **Dead code** — PR's changes render existing code unreachable or unused? Flag and suggest removal.
- **New third-party dependencies** — verify added to `pyproject.toml` / `requirements.txt`, justified (no stdlib or existing-dep equivalent), no known vulnerabilities.

---

## Phase 5 — Change Prioritization

**After reading all code, use these tiers to determine finding severity based on where they appear.**

A correctness issue in a 🔴 Critical area is always must-fix. The same type of issue in a ⚪ Low area may be a minor note.

**🔴 Critical** (must fix before merge):
- Public API surface and Pydantic model schemas (breaking field changes)
- Security-sensitive code (secrets, input validation)
- Embedding / LLM call correctness and batching
- Cosmos write paths
- Breaking changes to connector `Protocol`
- Production config

**🟡 High** (should fix — open follow-up if not in this PR):
- Pipeline stage logic and orchestration
- Connector implementations
- Error handling and retry logic
- Resource usage (runaway RU, unbatched embeddings)
- Major refactorings touching shared abstractions

**🟢 Medium** (fix opportunistically):
- Internal utilities and helpers
- Logging and observability
- Unit test quality
- Config field typing and defaults

**⚪ Low** (note only):
- Docstrings and comments
- Formatting and minor naming
- Test fixtures

CI failures from `gh pr checks` override tier — a failing check always surfaces as Critical regardless of file area.

---

## Output Format

Present findings in exactly this structure. Omit any tier that has no findings.

**Every Critical and Moderate finding must include all four elements:**
1. **What** — one sentence describing the problem.
2. **Why it matters** — specific consequence if unfixed (broken behavior, resource leak, security risk, maintainability pain).
3. **Concept** — principle violated, named explicitly (e.g., "N+1 pattern", "Pydantic v1 syntax", "broken Protocol contract").
4. **Label** — `[violation]` for a clear rule broken, `[judgment call]` when multiple valid approaches exist. Critical findings are always `[violation]`.

When a PR has more than 8 findings total, Minor findings may use condensed one-line form:
`**[File:line]** [label] — what + why in one sentence.`

All Critical and Moderate findings always use the full 4-element format.

---

### Context Summary
One short paragraph: what this PR is trying to do and whether the implementation matches that intent. Note if no analogous module was found.

---

### Patterns Done Well
Notable things the PR got right — specifically named, with a one-line note on *why* it's the right approach. Reinforces patterns worth repeating. Omit only if genuinely nothing notable.

---

### Critical
Issues that must be fixed before merge: security vulnerabilities, data loss risk, incorrect logic that breaks stated functionality, severe resource waste (e.g., embedding every document individually instead of batching), breaking interface changes without verified call sites.

- **[File:line]** [violation] — what · why it matters · concept name

### Moderate
Issues that degrade maintainability, violate project conventions, or introduce technical debt. Should be fixed; acceptable to defer if a follow-up issue is opened before merge.

- **[File:line]** [violation|judgment call] — what · why it matters · concept name

### Minor
Style, naming, minor convention deviations, missing docstrings. Fix opportunistically.

- **[File:line]** [violation|judgment call] — what · why it matters · concept name

---

### Summary
One or two sentences: overall assessment and recommended action
(approve / approve with minor fixes / request changes).
