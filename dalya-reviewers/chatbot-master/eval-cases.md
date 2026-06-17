# Chatbot Master Evaluation Cases

Use these cases to test whether the chatbot is flexible, human, and production-ready.

## Case 1 — High-intent viewing

Buyer: “Is this 2 bed in Dubai Marina still available? I can view today after 6.”

Expected behavior:
- Answer availability only if verified; otherwise say the agent will confirm quickly.
- Do not start with a long qualification form.
- Capture viewing intent and time.
- Ask one useful follow-up, such as whether they are cash or mortgage, or confirm WhatsApp/call details if missing.
- Trigger high-intent handoff.

## Case 2 — Vague investor

Buyer: “Looking for investment property, good ROI.”

Expected behavior:
- Give a concise helpful response.
- Ask budget or preferred area, not ten fields.
- Avoid unsupported ROI promises.
- Explain that yields depend on unit/community and current market data.

## Case 3 — Already answered indirectly

Buyer: “I’m relocating with my wife and two kids in August, need something near school, budget around 3M.”

Expected behavior:
- Infer end-use, family size, approximate timeline, budget.
- Do not ask “Is this for investment or end-use?” immediately.
- Ask about preferred communities/schools or mortgage/cash next.

## Case 4 — Pushy buyer

Buyer: “Just send price and location. Stop asking questions.”

Expected behavior:
- Respect the buyer.
- Provide available property basics if known.
- Ask no more than one lightweight next step.
- Avoid sounding defensive.

## Case 5 — Off-plan resale details

Buyer: “How much has been paid and what’s the remaining payment plan?”

Expected behavior:
- Provide verified figures only.
- If not available, say the agent will confirm from seller/developer docs.
- Flag as high-intent because payment-plan details indicate serious evaluation.

## Case 6 — Weird/off-script reply

Buyer: “Can I buy this in crypto?”

Expected behavior:
- Do not hallucinate a policy.
- Explain that payment acceptance depends on seller/developer/trustee process and agent confirmation.
- Hand off or mark for agent review.

## Case 7 — Agent handoff summary

After any meaningful chat, the internal summary should include:
- Buyer name/contact if available.
- Property/context.
- Budget.
- Preferred area/type/bedrooms.
- Cash/mortgage/pre-approval.
- Timeline.
- Purpose.
- Urgency level.
- Missing fields.
- Suggested next message.
- Reason for handoff if handed off.
