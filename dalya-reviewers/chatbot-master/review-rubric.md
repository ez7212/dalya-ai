# Chatbot Master Review Rubric

## 1. Human-likeness — score 1-10

Look for:

- Sounds like a real Dubai agent, not generic AI.
- No fake empathy.
- No verbose intros.
- Responds to the buyer's actual words.
- Uses natural variation.
- Keeps messages short enough for WhatsApp-style behavior.

## 2. Flexibility — score 1-10

Look for:

- Handles vague replies.
- Handles impatient users.
- Handles buyers who jump ahead.
- Updates state from any user message.
- Avoids repeating already answered questions.
- Does not depend on brittle if/else scripts.

## 3. Qualification quality — score 1-10

Assess whether it gathers the right data naturally:

- Budget.
- Location/community preference.
- Property type.
- Bedrooms/size.
- Ready vs off-plan.
- Cash vs mortgage.
- Mortgage pre-approval if relevant.
- Purchase timeline.
- End-use vs investment.
- Viewing availability.
- Urgency.
- Contact preference.

## 4. Conversion risk — score 1-10, where 10 means low risk

Look for:

- Too many questions.
- Slow movement toward viewing/call/WhatsApp.
- Failure to recognize hot leads.
- Over-explaining.
- Asking for information before providing obvious value.
- Making users repeat themselves.

## 5. Handoff quality — score 1-10

Look for:

- Clear handoff triggers.
- Agent gets clean summary.
- Missing fields are explicit.
- Suggested next action is obvious.
- Transcript/context is preserved.
- Buyer does not have to repeat themselves.

## 6. Production readiness — score 1-10

Look for:

- Prompt/version management.
- Conversation test cases.
- Edge-case coverage.
- Analytics for drop-off and handoff.
- QA tagging.
- Guardrails around claims, fees, and availability.
- Safe fallback behavior.

## Required output additions

For every weak chatbot message, provide:

1. Original message.
2. Why it is weak.
3. Better rewrite.
4. Expected effect on conversion or lead quality.
