"""
Rule-based intent detection — replaces the Claude API call for intent classification.

This eliminates ~50% of API costs. Claude is only used for the actual response generation.
For edge cases where rules can't determine intent, returns "general_enquiry" which is safe.
"""

import re
from typing import Optional


def detect_intent_rules(message: str) -> dict:
    """
    Classify buyer intent using keyword matching and regex patterns.
    Returns the same shape as the old Claude-based detect_intent.
    """
    msg = message.strip()
    msg_lower = msg.lower()

    result = {
        "intent": "general_enquiry",
        "confidence": 0.8,
        "should_escalate": False,
        "extracted_name": None,
        "extracted_budget": None,
        "extracted_bedrooms": None,
        "extracted_area": None,
        "extracted_purpose": None,
        "extracted_offer_amount": None,
        "escalation_reason": None,
        "is_unanswerable": False,
    }

    # Empty message
    if not msg:
        result["intent"] = "empty_message"
        return result

    # ── Offer detection ──────────────────────────────────────────────────
    offer_patterns = [
        r"(?:i(?:'ll| will)?|we(?:'ll| will)?|let me|i(?:'d| would) like to)\s+(?:offer|put in|submit|make an offer)",
        r"(?:offer|bid)\s+(?:of\s+)?(?:aed\s*)?[\d,]+",
        r"(?:aed\s*)?[\d,]+(?:\.\d+)?\s*(?:million|m)\b.*(?:offer|take|deal)",
        r"(?:would you (?:take|accept)|how about|what about)\s+(?:aed\s*)?[\d,]+",
        r"(?:i(?:'ll| will)?|we(?:'ll| will)?)\s+take\s+it",
        r"(?:can (?:the seller|you) (?:do|accept))\s+(?:aed\s*)?[\d,]+",
    ]

    for pattern in offer_patterns:
        if re.search(pattern, msg_lower):
            result["intent"] = "offer_submission"
            result["should_escalate"] = True
            result["escalation_reason"] = "offer"
            # Extract amount
            amount = _extract_amount(msg)
            if amount:
                result["extracted_offer_amount"] = amount
            break

    # ── Viewing request ──────────────────────────────────────────────────
    if result["intent"] == "general_enquiry":
        viewing_keywords = [
            "view", "viewing", "visit", "see the", "see this",
            "come see", "tour", "site visit", "show me", "walk through",
            "open house", "inspection",
        ]
        if any(kw in msg_lower for kw in viewing_keywords):
            result["intent"] = "viewing_request"

    # ── Contact sharing ──────────────────────────────────────────────────
    if result["intent"] == "general_enquiry":
        # Phone number pattern
        if re.search(r"(?:\+?\d{10,15}|\d{3}[-.\s]\d{3}[-.\s]\d{4})", msg):
            result["intent"] = "contact_sharing"
        # Email pattern
        elif re.search(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", msg):
            result["intent"] = "contact_sharing"

    # ── Price negotiation (not a firm offer) ─────────────────────────────
    if result["intent"] == "general_enquiry":
        negotiate_patterns = [
            r"(?:best|lowest|final|bottom)\s+price",
            r"(?:negotiate|negotiation|bargain|discount|reduce|come down|lower)",
            r"(?:too (?:high|expensive|much))",
            r"(?:above|beyond|over) (?:my|our) budget",
        ]
        if any(re.search(p, msg_lower) for p in negotiate_patterns):
            result["intent"] = "price_negotiation"

    # ── Payment plan query ───────────────────────────────────────────────
    if result["intent"] == "general_enquiry":
        payment_keywords = [
            "payment plan", "payment schedule", "instalment", "installment",
            "how much paid", "how much has been paid", "remaining balance",
            "remaining payment", "what's left to pay", "paid so far",
            "paid to date",
        ]
        if any(kw in msg_lower for kw in payment_keywords):
            result["intent"] = "payment_plan_query"

    # ── Speak to human ───────────────────────────────────────────────────
    if result["intent"] == "general_enquiry":
        human_patterns = [
            r"speak (?:to|with) (?:a |an )?(?:human|person|agent|someone|real person)",
            r"talk to (?:a |an )?(?:human|person|agent|someone)",
            r"connect me (?:with|to)",
            r"real (?:person|agent|human)",
            r"can i (?:call|phone|talk|speak)",
        ]
        if any(re.search(p, msg_lower) for p in human_patterns):
            result["intent"] = "speak_to_human"
            result["should_escalate"] = True
            result["escalation_reason"] = "buyer_requested_human"

    # ── Extract buyer info ───────────────────────────────────────────────
    # Name extraction (simple patterns)
    name_patterns = [
        r"(?:my name is|i'm|i am|this is|call me)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)",
        r"^(?:hi|hello|hey),?\s+(?:i'm|i am)\s+([A-Z][a-z]+)",
    ]
    for p in name_patterns:
        match = re.search(p, msg)
        if match:
            result["extracted_name"] = match.group(1).strip()
            break

    # Budget extraction
    budget = _extract_amount(msg)
    if budget and result["intent"] != "offer_submission":
        # Only treat as budget if they're talking about what they can spend
        budget_context = ["budget", "afford", "spend", "looking to pay", "price range", "max", "maximum"]
        if any(kw in msg_lower for kw in budget_context):
            result["extracted_budget"] = budget

    # Bedroom extraction
    bed_match = re.search(r"(\d)\s*(?:bed(?:room)?s?|br|bhk)", msg_lower)
    if bed_match:
        result["extracted_bedrooms"] = int(bed_match.group(1))

    # Purpose extraction
    if any(kw in msg_lower for kw in ["invest", "rental", "roi", "yield", "return"]):
        result["extracted_purpose"] = "investment"
    elif any(kw in msg_lower for kw in ["live in", "family", "move", "relocat", "primary home", "children", "kids", "school"]):
        result["extracted_purpose"] = "end_user"

    return result


WRITTEN_NUMBERS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14,
    "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18,
    "nineteen": 19, "twenty": 20, "thirty": 30,
}

WRITTEN_FRACTIONS = {
    "point one": 0.1, "point two": 0.2, "point three": 0.3,
    "point four": 0.4, "point five": 0.5, "point six": 0.6,
    "point seven": 0.7, "point eight": 0.8, "point nine": 0.9,
}


def _extract_amount(msg: str) -> Optional[float]:
    """Extract an AED amount from a message. Returns float or None."""
    msg_lower = msg.lower()

    # Pattern: "X million" or "X.Y million" or "Xm"
    million_match = re.search(
        r"(?:aed\s*)?(\d+(?:\.\d+)?)\s*(?:million|m)\b", msg_lower
    )
    if million_match:
        return float(million_match.group(1)) * 1_000_000

    # Pattern: written-out numbers with million — "five point eight million"
    if "million" in msg_lower:
        # Find the FIRST matching written number by position in the string
        first_pos = len(msg_lower)
        first_val = None
        for whole_word, whole_val in WRITTEN_NUMBERS.items():
            match = re.search(r'\b' + whole_word + r'\b', msg_lower)
            if match and match.start() < first_pos:
                first_pos = match.start()
                first_val = whole_val
        if first_val is not None:
            frac_val = 0.0
            for frac_word, frac_num in WRITTEN_FRACTIONS.items():
                if frac_word in msg_lower:
                    frac_val = frac_num
                    break
            return (first_val + frac_val) * 1_000_000

    # Pattern: "X,XXXK" or "XXXXK" — thousands
    k_match = re.search(r"(?:aed\s*)?(\d[\d,]*)\s*k\b", msg_lower)
    if k_match:
        return float(k_match.group(1).replace(",", "")) * 1_000

    # Pattern: "XXX lakhs" or "XX lakh" — Indian number system (1 lakh = 100,000)
    lakh_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:lakhs?|lacs?)\b", msg_lower)
    if lakh_match:
        return float(lakh_match.group(1)) * 100_000

    # Pattern: "XXX crore" — Indian (1 crore = 10,000,000)
    crore_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:crores?)\b", msg_lower)
    if crore_match:
        return float(crore_match.group(1)) * 10_000_000

    # Pattern: "AED X,XXX,XXX" or just "X,XXX,XXX"
    amount_match = re.search(
        r"(?:aed\s*)?(\d{1,3}(?:,\d{3})+(?:\.\d+)?)", msg_lower
    )
    if amount_match:
        return float(amount_match.group(1).replace(",", ""))

    # Pattern: plain large number "XXXXXXX"
    plain_match = re.search(r"(?:aed\s*)(\d{6,})", msg_lower)
    if plain_match:
        return float(plain_match.group(1))

    return None
