# DAL-199 Task 2 Path Normalization Evidence

Date: 2026-06-23
Workspace: `/Users/eric/dalya-ai`

## Changed files

- `scripts/run_focused_backend_qa.py`
- `scripts/focused_backend_qa_policy.py`
- `tests/test_focused_backend_qa_runner.py`
- `docs/runbooks/focused-backend-qa.md`
- `BACKLOG.md`

## Scenarios and binary observables

| Scenario | Invocation | Result | Artifact |
|---|---|---|---|
| DB-backed canonical path blocked | `python3 scripts/run_focused_backend_qa.py --python python3 --evidence .omo/evidence/dal-199-task2-canonical-blocked.json -- tests/test_seller_lead_privacy.py -q` | Exit 2, `status=BLOCKED`, `reason=db_backed_tests_disallowed:tests/test_seller_lead_privacy.py(...)`, `commands=[]`, `cleanup_reason=real_run_not_started` | `.omo/evidence/dal-199-task2-canonical-blocked.json` |
| DB-backed `./` path blocked | `python3 scripts/run_focused_backend_qa.py --python python3 --evidence .omo/evidence/dal-199-task2-dot-blocked.json -- ./tests/test_seller_lead_privacy.py -q` | Exit 2, `status=BLOCKED`, `reason=db_backed_tests_disallowed:tests/test_seller_lead_privacy.py(...)`, `commands=[]`, `cleanup_reason=real_run_not_started` | `.omo/evidence/dal-199-task2-dot-blocked.json` |
| DB-backed absolute path blocked | `python3 scripts/run_focused_backend_qa.py --python python3 --evidence .omo/evidence/dal-199-task2-absolute-blocked.json -- /Users/eric/dalya-ai/tests/test_seller_lead_privacy.py -q` | Exit 2, `status=BLOCKED`, `reason=db_backed_tests_disallowed:tests/test_seller_lead_privacy.py(...)`, `commands=[]`, `cleanup_reason=real_run_not_started` | `.omo/evidence/dal-199-task2-absolute-blocked.json` |
| `tests` directory discovery blocked | `python3 scripts/run_focused_backend_qa.py --python python3 --evidence .omo/evidence/dal-199-task2-directory-blocked.json -- tests -q` | Exit 2, `status=BLOCKED`, `reason=db_backed_directory_discovery_disallowed:tests(...)`, `commands=[]`, `cleanup_reason=real_run_not_started` | `.omo/evidence/dal-199-task2-directory-blocked.json` |
| Package-style DB-backed selector blocked | `python3 scripts/run_focused_backend_qa.py --python python3 --evidence .omo/evidence/dal-199-task2-module-blocked.json -- tests.test_seller_lead_privacy -q` | Exit 2, `status=BLOCKED`, `reason=db_backed_tests_disallowed:tests/test_seller_lead_privacy.py(...)`, `commands=[]`, `cleanup_reason=real_run_not_started` | `.omo/evidence/dal-199-task2-module-blocked.json` |
| Default no-DB check-only behavior remains truthful | `python3 scripts/run_focused_backend_qa.py --check-only --evidence .omo/evidence/dal-199-task2-default-check-only.json` | Exit 2, `status=BLOCKED` because local `python3` is 3.14 and repo venv symlink points to missing `python3.13`; `suite_policy=allowed_no_db_tests_only`, `commands=[]`, `cleanup_reason=real_run_not_started` | `.omo/evidence/dal-199-task2-default-check-only.json` |

## Test and hygiene commands

- RED before fix: `python3 -m unittest tests.test_focused_backend_qa_runner` failed 4 selector subtests for `./tests/test_seller_lead_privacy.py`, `/Users/eric/dalya-ai/tests/test_seller_lead_privacy.py`, `tests`, and `tests.test_seller_lead_privacy`.
- GREEN after fix: `python3 -m unittest tests.test_focused_backend_qa_runner` exited 0 with `Ran 2 tests in 0.000s` and `OK`.
- `python3 -m py_compile scripts/run_focused_backend_qa.py` exited 0.
- `python3 -m py_compile scripts/focused_backend_qa_policy.py tests/test_focused_backend_qa_runner.py` exited 0.
- `git diff --check` exited 0.
- `rg -n "<<<<<<<|=======|>>>>>>>" scripts docs` exited 1 with no output, meaning no conflict markers were found.
- `test ! -d /private/tmp/dalya-focused-backend-qa-venv` exited 0.

## Size review

- `scripts/run_focused_backend_qa.py`: 227 pure LOC.
- `scripts/focused_backend_qa_policy.py`: 93 pure LOC.
- `tests/test_focused_backend_qa_runner.py`: 47 pure LOC.

## Cleanup and constraints

- The temp venv path `/private/tmp/dalya-focused-backend-qa-venv` is absent.
- The blocked runner artifacts all recorded `commands=[]`, so no venv creation, dependency installation, or pytest command was started for DB-backed selectors.
- No app/product behavior, dependency or lockfile, env-file read, DB test, live write, migration, DDL, RLS, role/grant, or plan checkbox was changed.

## Residual risks

- Default check-only remains locally `BLOCKED` because the available `python3` is 3.14 and the repo venv symlink points at missing `python3.13`; this is truthful and separate from path policy.
- `git diff --check` does not include untracked files until they are added to git, so the new untracked files were also syntax-compiled and unit-tested directly.
