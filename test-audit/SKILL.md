---
name: test-audit
description: Use BEFORE implementing any change that alters behavior (feature, bugfix, behavior-affecting refactor) in any repository, to write the spec and the integration/E2E tests first with anonymized real data. Also use when writing or reviewing tests, before pushing a branch or opening, updating, or merging any MR/PR (conference gate), and when asked to audit or clean up a test suite.
---

# Test Audit

Errors are prevented before the code exists. The spec and the tests come first. The code comes last and exists to make them pass. A test earns its place by catching a behavior break a user would notice.

When `superpowers:test-driven-development` conflicts with this skill, this skill wins: the red-green cycle runs on integration and E2E tests, not on unit tests.

## The directives

1. Write the spec and the tests BEFORE writing or changing any code. Run the tests and see them fail for the expected reason before implementing.
2. Integration and E2E tests only. A unit test is allowed only for a pure function with calculation or parsing logic (money, dates, scores, parsers), and only after its failure-mode list is written.
3. Tests use real data, anonymized. Read real records from production or preprod (read-only), mask name, CPF, e-mail, phone and address, and freeze them as fixtures. Never invent sample data when a real record exists. Never commit raw personal data.
4. Tests never write to production. They run against local or preprod.
5. An integration test that mocks the boundary it claims to integrate is not an integration test.
6. Tautological tests considered harmful.
7. Change-detector tests considered harmful.
8. A bugfix starts with a failing test that reproduces the bug with real data. If an existing test should have caught it, fix that test instead of adding a new one.

## Mode A: before implementing (pre-production)

Run it before the first line of code of any behavior change.

1. **Spec.** Write the behavior in observable terms: inputs, expected outputs, the user-visible outcome, and the failure modes (what can go wrong and what the system does then). Put it where the repository keeps specs (`docs/`, `openspec/`, `specs/`). If there is none, write it in the "Spec" section of the MR description draft.
2. **Real data.** Pick real records that exercise each spec case: the main path, each failure mode, the edge cases. Read only. Anonymize before saving as fixtures.
3. **Tests.** Write one integration or E2E test per spec case, with those fixtures. Each test asserts an observable outcome.
4. **Red.** Run only the new tests, with capped workers (e.g. `--maxWorkers=2`). Each one fails because the behavior is missing, never because of setup errors.
5. **Commit.** Commit the spec and the tests on their own, before the implementation.
6. **Green.** Implement until the tests pass. Change a test only when the spec was wrong, and fix the spec first.

## Mode B: conference gate before any MR/PR

Run it on the diff, every time, in every repository.

1. Order: the spec and test commit comes before the implementation commits (`git log --reverse`). If the tests are missing or came after, write them now and say so in the MR description.
2. Run only the tests of the change, with capped workers. They pass.
3. Fixtures: no real name, CPF, e-mail, phone or address in the diff.
4. Classify each test added or changed. Remove every harmful verdict.
5. Complex feature: run the E2E flow. Attach the artifact (report, screenshot, JSON output, log) and the command that reproduces it.
6. Add a "Test audit" section to the MR description: spec link, tests kept and removed with verdict, the commit that proves the order, artifact link.

## Classify every test case

| Verdict | The test… | Examples |
|---|---|---|
| **Tautological** → delete | passes by construction; asserts what the test itself set up | mock returns X, assert X; assert a constant equals its own literal; `expect(true).toBe(true)`; re-implements the logic inside the test and compares; asserts only that a stub was called with the args the test passed in |
| **Change-detector** → delete | fails on a refactor that keeps behavior; pins implementation | exact call order/args to internal collaborators; private helpers; snapshots of prompts, copy, markup, CSS classes, SQL text; a list that mirrors a config or catalog literal |
| **Regression without gap** → delete | named after a bug/ticket, and an existing behavior test already covers that input and outcome, or it pins the fix's code | `it('DEVPM-123 fix')` that repeats a case another test already asserts |
| **Dead** → delete | never runs, so it cannot fail | no runner config matches the path; imports modules that no longer exist; runner not installed; skipped for good |
| **Unit outside the exception** → replace | unit test of anything other than a pure calculation or parsing function | component rendered with every service mocked; handler tested with the database mocked |
| **Behavior** → keep | drives public behavior with anonymized real data and asserts an observable outcome | integration or E2E test with an artifact; pure-function unit test backed by a failure-mode list |

A file with mixed verdicts loses only the harmful cases. When a helper, fixture, or mock becomes unused after a deletion, delete it too.

## Mode C: audit an existing suite

1. Branch from the remote default branch in a separate worktree. Never touch another session's working tree.
2. Inventory the test files. For large suites, split them into batches and classify in parallel read-only subagents. Each returns: file, test name, verdict, one-line reason.
3. Delete only harmful verdicts. Keep an existing unit test while no integration or E2E test covers its behavior, and list it as a replacement candidate. List the integration and E2E gaps in the MR description. Do not rewrite the suite.
4. Verify: type-check, lint, and run only the edited test files with capped workers.
5. Open the MR. The description lists each deletion (file, test, verdict, reason), the replacement candidates, and the gaps.

## Red flags: stop and reclassify

- "I'll write the tests after it works."
- "A unit test is faster to write here," for code that is not a pure calculation or parsing function.
- Sample data like "John Doe" or "test@test.com" when a real record exists.
- A fixture with a real CPF, e-mail or phone.
- "Adding a test for completeness."
- "A snapshot locks the prompt in place."
- Every collaborator is mocked, and the asserts check the mocks.
- The test would still pass if the function body were replaced by the expected literal.
