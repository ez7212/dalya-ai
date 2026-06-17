# Chatbot Master Benchmark Notes

These notes summarize the patterns Dalya should learn from modern production chatbots and AI agents. They are not a claim that Dalya should copy any single product.

## Modern production chatbot principles

1. **Brand-specific voice** — the bot should sound like Dalya/a Dubai real-estate assistant, not generic ChatGPT.
2. **Context before questions** — respond to what the buyer said before asking for more information.
3. **One-question discipline** — one clear next question beats a form disguised as chat.
4. **Flexible state** — users jump around; the bot should update state from any message, not force a fixed sequence.
5. **Confidence-aware handoff** — escalate on high intent, low confidence, legal/financial uncertainty, angry users, or repeated failure.
6. **Full-context human handoff** — the agent should receive summary, missing fields, buyer intent, urgency, suggested next message, and transcript link.
7. **QA loop** — failed conversations must be reviewable and tagged so prompts/flows improve.
8. **Outcome metrics** — optimize for reply rate, qualification completion, viewing booked, handoff quality, and agent acceptance, not just message correctness.

## Sierra-style lessons

- The agent should feel specific to the business and use real workflows, not generic FAQ logic.
- It should integrate with systems of record instead of merely answering questions.
- Escalation should happen when confidence is low, when policy is sensitive, or when the user is high-value.
- Reviewed conversations should feed continuous improvement.

## Intercom Fin-style lessons

- Answers should be concise, directly useful, and grounded in approved content.
- Teams need control over tone, answer behavior, and escalation.
- Handoff should preserve context and avoid making the user repeat themselves.
- Analytics and QA matter because production bot quality decays without review.

## Decagon-style lessons

- The bot should act like a concierge that can handle lifecycle tasks, not a rigid FAQ.
- Personalization should use known context carefully.
- Escalation and resolution metrics matter more than sounding clever.

## Dalya-specific conversation rules

- Do not begin with “I’d be happy to assist.”
- Do not ask for 4+ fields in one message.
- Do not explain obvious real estate basics to a serious buyer unless they ask.
- Do not say a property is available, mortgage-eligible, negotiable, or compliant unless the system has verified data.
- Do not overpromise ROI, capital appreciation, rental yield, or developer timelines.
- For serious buyers, move toward viewing, call, WhatsApp handoff, or agent handoff quickly.
- Always produce an internal lead summary after meaningful conversations.
- Always flag uncertainty and missing fields for the agent.

## Common bad chatbot signs

- “I’d be happy to assist you with that.”
- “To better understand your needs, could you please provide…”
- “As an AI assistant…”
- Asking for budget, location, bedrooms, timeline, financing, nationality, purpose, and viewing time all at once.
- Ignoring that the buyer already gave partial information.
- Repeating the same question after an indirect answer.
- Treating a hot buyer and a browser the same way.
- No handoff trigger.
- No actionable agent summary.
