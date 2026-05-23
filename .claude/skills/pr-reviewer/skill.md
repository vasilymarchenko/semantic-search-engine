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

1. Read the PR description and any linked issues. Extract:
   - The problem being solved
   - The proposed solution at a high level
   - Explicit constraints or decisions the author called out

2. Run `git log --oneline origin/main..HEAD` to see all commits in this PR.
   Commit messages reveal intent and scope; note if any seem out of place.

3. Run `git diff --stat origin/main..HEAD` to get a file-level overview.
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
   - Is there anything changed that the PR description doesn't mention?

---

## Phase 3 — Core Changes: Business Perspective

**Goal: verify the implementation actually solves the stated problem.**

For each core-classified file:

1. Read the **full resulting file** (not just the diff) to understand the code
   in its final state. Use the diff only to understand what changed.

2. Ask:
   - Does this code solve the problem stated in Phase 1?
   - Are happy-path and error-path behaviors both handled?
   - Are edge cases covered (empty input, large input, external service failure)?
   - Will this behave correctly under the load or scale the project targets?
   - Does it introduce any observable behavior change beyond the stated scope?

---

## Phase 4 — Core Changes: Technical Perspective

**Goal: verify correctness, patterns, and alignment with project standards.**

Review against each checklist item. Only report findings — skip items with no issues.

### Python Standards (see `semantic-search-python` skill for full reference)

- [ ] Type annotations use 3.10+ syntax: `list[str]`, `dict[str, int]`, `X | None`
      — never `Optional`, `List`, `Dict`, `Union` from `typing`
- [ ] Pydantic models use v2 syntax: `model_config`, `field_validator` with `@classmethod`,
      `model_dump()` — never `.dict()`, `.parse_obj()`, `@validator`
- [ ] Async code uses `TaskGroup` for concurrent I/O — not bare `asyncio.gather()`
- [ ] No blocking I/O inside `async def`: no `requests`, no `open()` without
      `asyncio.to_thread`, no `time.sleep()`
- [ ] Plugin interfaces use `Protocol`, not `ABC`
- [ ] New connectors self-register via `ConnectorRegistry` — no manual wiring
- [ ] Config reads from `Settings` (pydantic-settings) — never `os.getenv()` directly
- [ ] File paths use `pathlib.Path` — never `os.path`
- [ ] Logging uses `logger.info("... %s", value)` — never f-strings in log calls,
      never bare `print()`
- [ ] Exceptions follow the project hierarchy: `SemanticSearchError` → specific subclass

### Architecture Alignment

- [ ] The change fits the existing layered structure (connector → processor → pipeline → store)
- [ ] No new abstractions introduced that duplicate existing ones
- [ ] New public interfaces are Protocol-based and mockable in tests
- [ ] Dependency direction is clean — lower layers don't import upper layers

### Security

- [ ] No hardcoded secrets, API keys, connection strings, or tokens
- [ ] All secret config fields use `SecretStr` — never plain `str`
- [ ] Secrets are never logged, even at DEBUG level (check `.get_secret_value()` call sites)
- [ ] All external input (user queries, document content, webhook payloads) is validated
      with Pydantic before use
- [ ] No shell injection: `subprocess` calls use list form, never string interpolation
- [ ] CosmosDB queries use parameterized form — no string-concatenated queries

### Performance

- [ ] No N+1 patterns: document/chunk processing is batched, not looped one-by-one
- [ ] Async I/O is actually concurrent where parallelism is possible (`TaskGroup`)
- [ ] No large in-memory collections that grow unbounded with input size
- [ ] Expensive operations (embedding calls, Cosmos reads) are not duplicated inside loops

### Resource Usage — Critical for this project

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
- Test changes: do tests actually assert behavior, or just that code runs?
  Are fixtures realistic? Are failure cases tested, not just the happy path?
- Deployment / Azure Function changes: are bindings correct, are secrets
  sourced from Key Vault references, not plaintext app settings?

---

## Output Format

Present findings in exactly this structure. Omit any tier that has no findings.

---

### Context Summary
One short paragraph: what this PR is trying to do and whether the implementation
matches that intent.

---

### Critical
Issues that must be fixed before merge: security vulnerabilities, data loss risk,
incorrect logic that breaks the stated functionality, severe resource waste
(e.g., embedding every document individually instead of batching).

- **[File:line]** — description of the issue and why it matters
- ...

### Moderate
Issues that degrade maintainability, introduce technical debt, or violate
project conventions in ways that will cause pain later. Should be fixed,
acceptable to defer with a tracked issue.

- **[File:line]** — description
- ...

### Minor
Style, naming, minor convention deviations, missing docstrings on public APIs,
low-priority improvements. Fix opportunistically.

- **[File:line]** — description
- ...

---

### Summary
One or two sentences: overall assessment and recommended action
(approve / approve with minor fixes / request changes).
