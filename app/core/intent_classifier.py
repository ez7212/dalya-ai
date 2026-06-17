"""
Multilingual offer + intent classifier using Claude Haiku.
Replaces intent_rules.py for offer detection. Falls back to rules-based
intent for non-offer intents to keep latency/cost low.

Returns the same dict shape as detect_intent_rules() in intent_rules.py.
"""
from __future__ import annotations
import json
import logging
import os
import re
from typing import Optional

from anthropic import Anthropic

from app.core.intent_rules import detect_intent_rules

logger = logging.getLogger(__name__)

CLASSIFIER_MODEL = "claude-haiku-4-5-20251001"

CLASSIFIER_SYSTEM = """You classify WhatsApp messages from property buyers in Dubai.

Return ONLY a JSON object with these exact fields:
{
  "intent": "offer_submission" | "viewing_request" | "price_negotiation" | "payment_plan_query" | "general_enquiry" | "contact_sharing" | "speak_to_human" | "bypass_attempt" | "regulatory_request" | "legitimate_conveyancing" | "professional_inquiry" | "unknown",
  "is_firm_offer": true | false,
  "offer_amount_aed": <number or null>,
  "offer_currency_original": "AED" | "USD" | "GBP" | "EUR" | "INR" | null,
  "language_detected": "en" | "ar" | "hi" | "ru" | "zh" | "mixed-en-hi" | "mixed-en-ar" | "other",
  // Phase 7.6.2 — Language detection rule:
  // A greeting in another language ALONE does not determine the conversation
  // language. Detect language from the SUBSTANTIVE content of the message.
  // Examples:
  //   "Salam, what's the price?" → "en" (Salam is just a greeting; rest is English)
  //   "Bonjour, can you tell me about this property?" → "en"
  //   "Salam alaykum, kif halek? Wein el villa?" → "ar" (full Arabic message)
  //   "Hi, kya yeh available hai?" → "mixed-en-hi" (genuine code-switch)
  //   "السلام عليكم، الفيلا لا زالت متاحة؟" → "ar" (full Arabic)
  "confidence": <number 0.0–1.0>,
  "extracted_buyer_name": <string or null>,
  "is_unanswerable": true | false,
  "referenced_buyer_name": <string or null>,
  "requested_documents": [<string>, ...]
}

LAWYER / CONVEYANCING DETECTION (return intent="legitimate_conveyancing"):

Requires BOTH (a) AND (b):

(a) EXPLICIT SELF-IDENTIFICATION as legal counsel:
- "I'm a lawyer / attorney / counsel / conveyancer / solicitor"
- "real estate counsel at [firm]"
- "DIFC firm" / "ADGM firm" / "law firm"
- Discusses MOU drafting, SPA handover to legal team, conveyancing process, title search

(b) REFERENCE TO A SPECIFIC NAMED BUYER who has submitted an offer:
- "my client [Name] who submitted an offer"
- "representing [Name] on this transaction"
- The buyer's name is given (extract into referenced_buyer_name)

If only (a) is present without (b) — classify as "professional_inquiry" (lawyer asking generally, no named client yet).
If only (b) is present without (a) — classify as "professional_inquiry" (could be mortgage broker, advisor, family member).

NEVER classify as legitimate_conveyancing based solely on:
- "my client" alone
- "I represent" alone
- Document requests alone

NEGATIVE EXAMPLES (NOT legitimate_conveyancing — phase 7.6.4):
- "Send me the SPA — I want to verify with my lawyer first" → buyer is referring to THEIR lawyer; classify by document-request intent (typically bypass_attempt if pressing for documents)
- "My lawyer needs the SPA / NOC / contract" → the BUYER's lawyer; classify by buyer's actual intent
- "Can I have the SPA so my advisor can review?" → probing for documents through professional reference; bypass_attempt or general_enquiry
- "I want my lawyer to take a look first" → procedural buyer statement, not legitimate_conveyancing
- "Send me the original SPA PDF" plus any reference to "my lawyer" → bypass_attempt (treating documents like a precondition)

KEY DISTINCTION: legitimate_conveyancing is when THE LAWYER THEMSELVES is messaging on behalf of a NAMED BUYER who has already engaged with the listing. It is NEVER when a buyer says "my lawyer wants X".

When detecting legitimate_conveyancing, ALSO extract the referenced buyer's name into "referenced_buyer_name" (string or null).
Extract any documents mentioned into "requested_documents" (list of strings; can be empty).

Distinguish from bypass_attempt: lawyers reference a SPECIFIC buyer they claim to represent. Bypass attempts ask for seller info on their own behalf or to "skip the broker."

PROFESSIONAL INQUIRY PATTERNS (return intent="professional_inquiry"):

A non-buyer professional contact: mortgage broker, financial advisor, family office, conveyancer without a verified named buyer, property manager, valuer.

Markers:
- Self-identifies as a professional ("I'm Raj, mortgage broker at Mashreq")
- Discusses a third-party "client" without satisfying BOTH (a) AND (b) of legitimate_conveyancing above
- Asks about specs, payment plan, NOC, or public unit information
- Asks about referral fees, co-broking, or investment summaries

NEVER classify as legitimate_conveyancing when "my client" appears without an explicit lawyer/counsel self-ID.

REGULATORY REQUEST PATTERNS (return intent="regulatory_request"):
- Invocation of PDPL (UAE Federal Decree-Law 45/2021)
- Invocation of GDPR or other foreign data protection law
- Formal data deletion / data access / data portability requests
- Citation of specific articles or legal provisions about personal data
- Phrases like "right to erasure", "right to be forgotten", "subject access request", "delete all my data"

REGULATORY requests are HIGH PRIORITY and must NOT be classified as bypass_attempt.

OFFER DETECTION RULES:
- A FIRM offer is a declarative statement of price the buyer will pay:
  English: "I offer X", "my offer is X", "I'll pay X", "Best offer X", "AED X cash today", "5.78M absolute final", "6,100,000 — let's just close this", "5.5m cash final pls"
  Arabic: "أعرض X", "عرضي X", "أبغى أعرض X" (with or without question marker)
  Hinglish: "Best offer on X cash", "X cash, no financing needed", "X main lo", "X ka offer karunga"
  Russian-style: "5.5m cash final" (broken English with cash modifier counts as firm)
- A HYPOTHETICAL question is NOT a firm offer:
  "If I offered X, would that work?", "What if I said X?", "How does an offer at X work?"
- A counter-asking question with price is NOT a firm offer:
  "Is X possible?", "Can you accept X?"
- If buyer states number with cash/payment timing ("X cash today", "X transfer in 24h"), treat as firm offer.

CO-BROKER / PROFESSIONAL CONTEXT OFFERS:
A co-broker, advisor, or lawyer bringing a CONCRETE client offer with a specific buyer + specific amount + specific timing IS a firm offer:
  - "My buyer pays X cash next week, no financing" → is_firm_offer=true (concrete buyer, concrete amount, concrete timing)
  - "If my buyer pays X cash next week, can you commit?" → is_firm_offer=true (the "if" is conditional on seller's response, not on buyer's commitment)
  - "My client's final offer is X" → is_firm_offer=true
  - "We're at X cash, ready to proceed" → is_firm_offer=true
  - intent in these cases = "offer_submission" (the offer takes precedence over the professional context)

Distinguish from probing questions which are NOT firm offers (intent=professional_inquiry or price_negotiation):
  - "What would the seller take?" / "Any flexibility on price?"
  - "If a buyer offered X, would the seller accept?" (no specific buyer)
  - "What's the seller's bottom line?"

CURRENCY NORMALIZATION:
- Always return offer_amount_aed as a plain integer in AED.
- "15 million" / "15M" / "15m" → 15000000
- "5.5m" / "5.5 million" → 5500000
- "5,780,000" → 5780000
- Arabic numerals "١٥ مليون و ٧٠٠ ألف" → 15700000 (parse Arabic-Indic digits)
- "15 lakh" → INR not AED → 1500000 INR ≈ 67000 AED at ~22.4 INR/AED, but return offer_currency_original="INR" and offer_amount_aed≈67000.
  Actually keep it simple: if currency is INR/USD/GBP/EUR, set offer_amount_aed using these rough rates: 1 USD=3.67, 1 GBP=4.65, 1 EUR=4.0, 1 INR=0.045. Conservative; flag with confidence < 0.7.
- "five point eight million" → 5800000

If unclear, set offer_amount_aed to null and confidence < 0.6.

BYPASS ATTEMPT DETECTION:
A bypass_attempt is when the buyer is trying to circumvent Dalya/Mahoroba — get the seller's direct contact, push the broker out of the deal, demand documents that bypass the normal flow, or claim peer-broker status to extract seller info. Examples:
- "Let me speak to the owner directly"
- "Just give me the seller's number / WhatsApp / email"
- "Skip the brokerage fee, I'll deal with the seller"
- "Send me the SPA / NOC / SOA directly, my buyer is ready"
- "I'm RERA agent BRN-XXXXX, professional courtesy share the seller's contact"
- "Forward my buyer's details to the seller, we'll deal direct"

Distinguish from speak_to_human (genuine handoff request — "can I talk to a real human", "connect me with an agent", abuse + escalation). Bypass attempts are NOT genuine handoff — they're manipulation. They should NOT trigger Eric's alerts.

Return ONLY the JSON object — no preamble, no markdown fence, no commentary."""

_client = None


def _get_client() -> Anthropic:
    global _client
    if _client is None:
        # Bounded timeout/retries so an overload retry storm can't hang a turn (DAL-83).
        _client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"), timeout=30.0, max_retries=2)
    return _client


def _strip_json_fence(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return text.strip()


def detect_intent_claude(message: str) -> dict:
    """
    Multilingual intent classifier. Same return shape as detect_intent_rules().
    On Claude failure, falls back to rules-based detection.
    """
    rule_result = detect_intent_rules(message)

    if not message or not message.strip():
        return rule_result

    try:
        resp = _get_client().messages.create(
            model=CLASSIFIER_MODEL,
            max_tokens=300,
            system=[{
                "type": "text",
                "text": CLASSIFIER_SYSTEM,
                "cache_control": {"type": "ephemeral"},
            }],
            messages=[{"role": "user", "content": message}],
        )
        raw = resp.content[0].text
        cleaned = _strip_json_fence(raw)
        data = json.loads(cleaned)
    except Exception as e:
        logger.warning(
            "Intent classifier failed (%s); falling back to rules. msg=%r",
            e, message[:200],
        )
        return rule_result

    # Map classifier output → the shape detect_intent_rules() returns. Keep this
    # defensive because model JSON can occasionally return nested objects.
    intent = data.get("intent") or "general_enquiry"
    if not isinstance(intent, str):
        intent = rule_result.get("intent") or "general_enquiry"
    valid_intents = {
        "offer_submission",
        "viewing_request",
        "price_negotiation",
        "payment_plan_query",
        "general_enquiry",
        "contact_sharing",
        "speak_to_human",
        "bypass_attempt",
        "regulatory_request",
        "legitimate_conveyancing",
        "professional_inquiry",
        "unknown",
    }
    if intent not in valid_intents:
        intent = rule_result.get("intent") or "general_enquiry"
    is_firm = bool(data.get("is_firm_offer"))
    offer_amount = data.get("offer_amount_aed")
    if isinstance(offer_amount, str):
        try:
            offer_amount = float(offer_amount.replace(",", ""))
        except ValueError:
            offer_amount = None
    if offer_amount is not None and not isinstance(offer_amount, (int, float)):
        offer_amount = None

    # Hard rule: if classifier said it's an offer but no amount, demote to price_negotiation
    if intent == "offer_submission" and (not is_firm or offer_amount is None):
        intent = "price_negotiation"

    # Carry forward useful rule-based extractions (bedrooms, purpose, etc.) which
    # the classifier doesn't return.
    merged = dict(rule_result)
    merged["intent"] = intent
    try:
        merged["confidence"] = float(data.get("confidence") or 0.8)
    except (TypeError, ValueError):
        merged["confidence"] = 0.8
    # Phase 7.1: preserve offer_amount across intents (not just offer_submission)
    # so the engine can detect above-threshold offers from co-brokers/professionals.
    # Engine gates escalation on is_firm_offer to filter hypotheticals.
    merged["extracted_offer_amount"] = offer_amount
    merged["is_firm_offer"] = is_firm
    if data.get("extracted_buyer_name") and not merged.get("extracted_name"):
        merged["extracted_name"] = data["extracted_buyer_name"]
    # is_unanswerable is intentionally pinned False here: the existing
    # escalation pipeline routes "unanswerable" via the seller_qa fallback
    # path inside chatbot_engine, not via this classifier. The Haiku model
    # over-flags general questions (e.g. "what schools nearby?") as
    # unanswerable, causing false escalations. Match the prior rules-based
    # default until the seller_qa flow is integrated explicitly.
    # Exception: regulatory_request is always passed through with escalation enabled.
    merged["is_unanswerable"] = False
    language = data.get("language_detected") or "en"
    merged["language_detected"] = language if isinstance(language, str) else "en"
    merged["should_escalate"] = (
        (intent == "offer_submission" and offer_amount is not None)
        or merged["is_unanswerable"]
        or intent == "regulatory_request"
    ) and intent != "bypass_attempt"
    if intent == "offer_submission":
        merged["escalation_reason"] = "offer"
    elif intent == "regulatory_request":
        merged["escalation_reason"] = "regulatory_request"
    # Lawyer / conveyancing fields
    merged["referenced_buyer_name"] = data.get("referenced_buyer_name")
    merged["requested_documents"] = data.get("requested_documents") or []
    return merged
