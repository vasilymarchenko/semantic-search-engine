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

## Phase 1 — Context

**Goal: understand WHY this PR exists before looking at any code.**

1. Run `gh pr view` to fetch the PR description, linked issues, labels, and assignees.
   Extract:
   - The problem being solved
   - The proposed solution at a high level
   - Explicit constraints or decisions the author called out

2. Run `gh pr checks` to see CI status. If any checks are failing, note them now —
   a failing build changes the review priority (broken code first, style second).

3. Run `git log --oneline origin/main..HEAD` to see all commits in this PR.
   Commit messages reveal intent and scope; note if any seem out of place.

4. Run `git diff --stat origin/main..HEAD` to get a file-level overview.
   Categorize files mentally: core domain change vs. config / tests / docs.

If the PR description is missing or vague, flag this as a **moderate** issue
("PR lacks context — reviewer cannot verify intent against implementation").

---

## Phase 2 — Structure Analysis

**Goal: identify what changed and where the weight of the PR is.**

1. List all changed files and classify each:
   - **Core** — domain models, pipeline stages, connectors, embedding logic
   - **Infrastructure** — config, Azure Functions, Cosmos queries, deployment
   - **Tests** — unit, integration, fixtures
   - **Supporting** — logging, utilities, type aliases, constants

2. Check structural coherence:
   - Is the PR focused, or does it mix unrelated concerns?
   - Are test files present for every new or changed core module?
     (Phase 2 only checks presence — Phase 5 evaluates test quality.)
   - Is there anything changed that the PR description doesn't mention?

---

## Phase 3 — Core Changes: Business Perspective

**Goal: verify the implementation actually solves the stated problem.**

If the PR has more than 5 core files, prioritize: read the files that are central to the
stated problem first (usually the entry point and any new/heavily changed modules). Apply
the questions below to those files in full; for the remaining files, focus only on question 1.

Phase 3 and Phase 4 read the same files — you may combine the read passes if it is more
natural. The phases are separated by perspective, not by when you open the file.

For each core-classified file:

1. Read the **full resulting file** (not just the diff) to understand the code
   in its final state. Use the diff only to understand what changed.

2. Ask:
   - Does this code solve the problem stated in Phase 1?
   - Are happy-path and error-path behaviors both handled?
   - Are edge cases covered (empty input, large input, external service failure)?
   - Will this behave correctly under the load or scale the project targets?
   - Does it introduce any observable behavior change beyond the stated scope?
     (Observable means: changed output, different exceptions raised, altered side effects
     such as writes to Cosmos or external API calls. Log wording changes and internal
     restructuring without behavior change do not count.)

---

## Phase 4 — Core Changes: Technical Perspective

**Goal: verify correctness, patterns, and alignment with project standards.**

Before running the checklist, find the closest analogous existing module in the codebase
(e.g., if the PR adds a connector, find an existing connector; if it adds a pipeline stage,
find an existing one). Do one read pass — compare structure and key patterns only, not line-by-line.
Note where the PR's approach diverges; use the PR description and commit messages from Phase 1
to judge whether a divergence is intentional improvement or unintentional inconsistency.
Reference this comparison in findings.

If no analogous module exists (the PR introduces an entirely new capability), skip this step
and note that in the Context Summary.

Review against each checklist item. Only report findings — skip items with no issues.

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

### Architecture Alignment

- [ ] The change fits the existing layered structure (connector → processor → pipeline → store)
- [ ] No new abstractions introduced that duplicate existing ones
- [ ] New public interfaces are Protocol-based and mockable in tests
- [ ] Dependency direction is clean — lower layers don't import upper layers
- [ ] **Backwards compatibility** — if the PR changes a public interface (function signature,
      Pydantic model fields, Protocol method), check whether any existing caller is broken.
      Search for call sites before flagging as safe.
- [ ] **Dead code** — check whether the PR's own changes render any existing code unreachable
      or unused (deleted branch, replaced function, orphaned import).
- [ ] **New third-party dependencies** — if new packages are imported, verify they are added
      to requirements files and that the addition is justified (not a stdlib or existing-dep
      equivalent already available).

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

---

## Phase 5 — Supporting Changes

Apply a lighter pass to infrastructure, utilities, and test files:

- Config changes: are new fields typed correctly, defaulted safely, documented?
- Deployment / Azure Function changes: are bindings correct, are secrets
  sourced from Key Vault references, not plaintext app settings?

### Test quality — check each of these explicitly

- **Behavior vs. execution** — do assertions verify *what* the code does, or just that
  it doesn't throw? `assert result is not None` is not a meaningful test.
- **Mock scope** — are mocks applied at the right boundary (external I/O only)?
  Mocking internal project code usually means the test is testing the wrong thing.
- **Failure paths** — is there at least one test per public function that covers an
  error case (bad input, external service failure, empty result)?
  "Public function" means any function or method not prefixed with `_`, including
  async functions and class methods on public classes.
- **Fixture realism** — do fixtures resemble real data shapes? Fake data with wrong types
  or missing required fields will miss entire categories of bugs.
- **Assertion specificity** — `assert len(results) == 3` is weaker than asserting
  the actual content; flag tests where the assertion could pass for the wrong reason.

---

## Output Format

Present findings in exactly this structure. Omit any tier that has no findings.

**For every finding, regardless of tier, include:**
1. What the problem is (one sentence).
2. Why it matters — the specific consequence if left unfixed (broken behavior, resource leak,
   security risk, maintainability pain, style divergence from the rest of the codebase).
3. The Python/design concept being violated, named explicitly so the author can learn it
   (e.g., "this is an N+1 pattern", "this breaks the Protocol contract", "pydantic v1 syntax").
4. A label: **[violation]** for a clear rule broken, or **[judgment call]** when multiple
   valid approaches exist and this is a preference — explain the tradeoff briefly.
   Note: Critical findings are always **[violation]** — if something is a judgment call,
   it cannot be must-fix, so it belongs in Moderate or Minor.

When a PR has more than 8 findings total, you may use a condensed one-line form for Minor
findings only: `**[File:line]** [label] — what + why in one sentence.` All Critical and
Moderate findings must always use the full 4-element format.

---

### Context Summary
One short paragraph: what this PR is trying to do and whether the implementation
matches that intent.

---

### Patterns Done Well
List any notable things the PR got right — specifically named, with a one-line note on
*why* it's the right approach. This is not flattery; it reinforces patterns worth repeating.
There is no minimum or maximum count. Omit this section only if there is genuinely nothing notable.

---

### Critical
Issues that must be fixed before merge: security vulnerabilities, data loss risk,
incorrect logic that breaks the stated functionality, severe resource waste
(e.g., embedding every document individually instead of batching).

- **[File:line]** [violation] — what, why it matters, concept name
- ...

### Moderate
Issues that degrade maintainability, introduce technical debt, or violate
project conventions in ways that will cause pain later. Should be fixed,
acceptable to defer — the PR author should open a follow-up issue before merging.

- **[File:line]** [violation|judgment call] — what, why it matters, concept name
- ...

### Minor
Style, naming, minor convention deviations, missing docstrings on public APIs,
low-priority improvements. Fix opportunistically.

- **[File:line]** [violation|judgment call] — what, why it matters, concept name
- ...

---

### Summary
One or two sentences: overall assessment and recommended action
(approve / approve with minor fixes / request changes).
