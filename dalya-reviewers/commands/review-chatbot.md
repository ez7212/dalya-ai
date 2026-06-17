# Review Chatbot Command

Use when reviewing Dalya's chatbot, prompts, conversation logic, qualification, and handoff.

## Read first

- `dalya-reviewers/shared-context.md`
- `dalya-reviewers/review-session-rules.md`
- `dalya-reviewers/file-routing.md`
- `dalya-reviewers/templates/review-output-template.md`
- `dalya-reviewers/chatbot-master/persona.md`
- `dalya-reviewers/chatbot-master/benchmark-notes.md`
- `dalya-reviewers/chatbot-master/eval-cases.md`
- `dalya-reviewers/chatbot-master/review-rubric.md`
- `dalya-reviewers/real-estate-guru/persona.md`
- `dalya-reviewers/real-estate-guru/knowledge-pack.md`
- `dalya-reviewers/real-estate-guru/transaction-reference.md`
- `dalya-reviewers/real-estate-guru/review-rubric.md`

## Scope

Review:

- Chatbot prompts.
- Conversation state machine.
- Buyer qualification logic.
- Message generation.
- Conversation memory/context.
- Handoff triggers.
- Agent summary output.
- Analytics/QA loop if present.
- UI where agent reviews chatbot conversations.

## Instructions

Do not change code.

Return:

1. Chatbot Master findings.
2. Real Estate Guru findings.
3. Combined production-readiness score.
4. Top 10 fixes ranked by launch impact.
5. Linear-ready tasks.
