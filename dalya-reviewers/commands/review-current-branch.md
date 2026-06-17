# Review Current Branch Command

Use after implementing a feature but before merging.

## Instructions

1. Read `dalya-reviewers/file-routing.md`.
2. Identify changed files versus the base branch.
3. Infer which reviewer(s) should inspect the change:
   - Chatbot changes -> Chatbot Master + Real Estate Guru.
   - Dashboard/workflow changes -> UX Designer + Real Estate Guru.
   - Backend/auth/API/RLS/deployment changes -> Security Researcher.
4. Run only the relevant reviews.
5. Do not change code.
6. Return findings and Linear-ready follow-up tasks.

## Output

- Changed scope summary.
- Reviewers used and why.
- P0/P1/P2 or Critical/High/Medium/Low findings.
- Merge recommendation: Block / Merge with fixes soon / Safe to merge.
