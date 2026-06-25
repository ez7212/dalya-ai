# DAL-203 Listings Workspace Rebrand - Final Verification

Final status: **PASS with documented non-product limitations**.

T12 final verification completed against the current dirty tree without reverting or editing product code. The T12 gate-review rejection was remediated by rerunning the browser QA harness with evidence-derived adversarial verdicts, adding a focused code-quality/slop report, and adding a dirty-worktree boundary receipt. The canonical `/listings` workspace, route-backed `/listings/[id]` tabs, legacy `/dashboard/listings/*` redirects, inventory API tests, typecheck, build, targeted verification scripts, brand/navigation scans, and staged browser QA all have evidence under `.omo/evidence/dalya-listings-workspace-rebrand/final-qa/`.

## Changed Surfaces

- `/listings` is verified as the active agent inventory command center.
- `/listings/[id]`, `/documents`, `/knowledge`, `/logistics`, and `/offers` are verified as canonical route-backed workspace routes under the shared shell.
- `/dashboard/listings/[id]`, `/knowledge`, `/logistics`, `/offers`, and `/spa` are verified to land on canonical `/listings/*` routes, with `/spa` mapping to `/documents`.
- `BACKLOG.md` now marks DAL-203 delivered and records Pass 2 creation-flow split as follow-up.
- `PROJECT_BRIEF.md` now reflects `/listings` as the active agent listing workspace.

## Verification Commands

| Command | Exit | Verdict | Artifact |
| --- | ---: | --- | --- |
| `cd frontend && npx --no-install tsc --noEmit` | 0 | PASS | `final-qa/tsc.txt` |
| `cd frontend && node scripts/verify-listings-workspace.mjs` | 0 | PASS | `final-qa/verify-listings-workspace.txt` |
| `cd frontend && node scripts/verify-listing-legacy-redirects.mjs` | 0 | PASS | `final-qa/verify-listing-legacy-redirects.txt` |
| `.venv-pilot/bin/dotenv -f .env.test run -- env PYTHONPATH=. .venv-pilot/bin/python -m pytest tests/test_listing_inventory_api.py -q` | 4 | BLOCKED in sandbox by DNS to Neon test host | `final-qa/pytest-listing-inventory.txt` |
| Same pytest command with escalation | 0 | PASS, `6 passed` | `final-qa/pytest-listing-inventory-escalated.txt` |
| `cd frontend && npm run lint` | 1 | BLOCKED by pre-existing unrelated frontend lint errors outside listings workspace | `final-qa/npm-lint.txt` |
| `cd frontend && npm run build` | 1 | BLOCKED in sandbox by Google Fonts network fetch | `final-qa/npm-build.txt` |
| Same build command with escalation | 0 | PASS | `final-qa/npm-build-escalated.txt` |
| Canonical `/dashboard/listings` link scan | 1/no matches | PASS | `final-qa/canonical-dashboard-link-scan.txt` |
| Precise canonical workspace legacy token scan | 1/no matches | PASS | `final-qa/canonical-workspace-precise-legacy-scan.txt` |
| Browser QA harness remediation rerun | 0 | PASS, 23 surface cases and 5 evidence-derived adversarial cases | `final-qa/manualQa.json`, `final-qa/final-browser-qa-output-remediation.txt` |

## Browser QA

Browser QA ran through a staged temporary frontend with local auth/API stubs because the pre-existing port 3000 process was unreachable and Next refused a second dev server in the project workdir. The harness verified `/listings`, `/listings/[id]`, `/documents`, `/knowledge`, `/logistics`, and `/offers` at 1280px, 768px, and 375px. It also drove legacy `/dashboard/listings/*` routes and confirmed final canonical paths.

The adversarial rows are now computed from observable evidence rather than hard-coded PASS values:

- `stale_state`: route counts, route markers, current fixture text, and no API-stub 404s.
- `dirty_worktree`: non-empty T12 dirty-worktree receipt plus successful route evidence.
- `misleading_success_output`: non-empty screenshot files plus DOM route/link/overflow checks.
- `hung_or_long_commands`: QA server cleanup result, safe temp removal, and closed QA port.
- `flaky_tests`: deterministic listing fixture, exact route transcript, and screenshot evidence.

Primary artifacts:

- `final-qa/manualQa.json`
- `final-qa/browser-transcript.json`
- `final-qa/final-browser-qa-output-remediation.txt`
- `final-qa/index-1280.png`, `index-768.png`, `index-375.png`
- `final-qa/overview-1280.png`, `overview-768.png`, `overview-375.png`
- `final-qa/documents-1280.png`, `documents-768.png`, `documents-375.png`
- `final-qa/knowledge-1280.png`, `knowledge-768.png`, `knowledge-375.png`
- `final-qa/logistics-1280.png`, `logistics-768.png`, `logistics-375.png`
- `final-qa/offers-1280.png`, `offers-768.png`, `offers-375.png`
- `final-qa/cleanup-receipt.txt`
- `final-qa/t12-dirty-worktree-receipt.txt`
- `final-qa/t12-code-quality-review.md`

## Known Limitations

- Full `npm run lint` remains blocked by existing unrelated lint errors in `ConversationDetail.tsx`, `EscalationInbox.tsx`, `SellerUpload.tsx`, and `InspectionAudioInput.tsx`. The listings verifier and typecheck pass; the lint blocker is not a DAL-203 product blocker.
- The broad banned-token scan intentionally catches `--color-surface-1` CSS variable references in deferred creation-flow files. The precise canonical workspace scan has no banned legacy class/token matches, and creation-flow route splitting remains Pass 2 follow-up.
- The first pytest run and first build run were blocked by sandboxed network/DNS restrictions. Escalated reruns passed.
- Port 3000 had a pre-existing Node listener (`PID 25996`) and was left untouched. It was not reachable via `localhost` or `127.0.0.1` during final QA. The T12 QA-owned staged server was stopped and its temp frontend was removed.
- The remediated final QA harness is 351 pure LOC after removing unused helpers. This is documented as a one-off evidence-harness exception in `final-qa/t12-code-quality-review.md`: it lives under `.omo/evidence/`, is not imported by production code, writes only final QA artifacts, starts a random-port QA server, verifies cleanup, and exits non-zero on any failed surface/adversarial row.
- A true pre-T12 dirty-worktree snapshot cannot be recreated. `final-qa/t12-dirty-worktree-receipt.txt` records that limitation and uses the Task 1 baseline plus pre/post remediation status to distinguish evidence-only remediation from existing product-code changes.

## Evidence Index

- Structured final JSON: `task-12-final.json`
- Manual QA matrix: `final-qa/manualQa.json`
- T12 code-quality/slop report: `final-qa/t12-code-quality-review.md`
- T12 dirty-worktree receipt: `final-qa/t12-dirty-worktree-receipt.txt`
- Command Center log: `final-qa/command-center-activity-log.txt`
- Cleanup receipt: `final-qa/cleanup-receipt.txt`
- Port 3000 disposition: `final-qa/lsof-port-3000-after.txt`, `final-qa/curl-localhost-3000-listings.txt`, `final-qa/curl-127001-3000-listings.txt`
