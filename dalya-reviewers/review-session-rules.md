# Review Session Rules

These rules apply to every Dalya reviewer.

## Default mode

Review only. Do not edit code unless Eric explicitly asks you to implement accepted fixes.

## Evidence standard

Do not make generic claims. Tie findings to one of:

- File path
- Function/component/route name
- Prompt snippet
- Database table/policy
- API endpoint
- Screenshot/screen/flow name
- Conversation transcript excerpt
- Missing artifact that should exist

If you cannot find the relevant files, say exactly what you searched for and what was missing.

## Prioritization

Product/UX/chatbot priorities:

- **P0** — Launch blocker. Fix before demo or production.
- **P1** — Serious issue. Fix before wider use.
- **P2** — Improvement. Useful but not blocking.

Security severities:

- **Critical** — likely cross-tenant data exposure, auth bypass, secret exposure, or destructive action.
- **High** — plausible abuse or data exposure with some conditions.
- **Medium** — meaningful weakness requiring hardening.
- **Low** — best-practice improvement or defense-in-depth.

## Output style

- Be concise but specific.
- Do not spend words praising obvious basics.
- Include exact suggested copy rewrites for chatbot/UX issues.
- Include attack scenario and verification for security issues.
- Include Linear-ready tasks for anything actionable.

## Collaboration rules

- Chatbot Master judges conversation quality and production chatbot behavior.
- Real Estate Guru judges Dubai real-estate correctness and sales usefulness.
- UX Designer judges adoption, workflow, and dashboard comprehension.
- Security Researcher judges whether the system can be abused or leak data.

When reviewers disagree, state the tradeoff rather than forcing false consensus.
