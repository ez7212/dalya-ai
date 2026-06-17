"""
Post-generation response validator.

SINGLE entry point for ALL bot output regardless of which prompt path
produced it (buyer, seller, regulatory, no-listing, professional,
conveyancing). Phase 7.5 expanded scope.

Rules enforced (all idempotent):
1. Em-dash replacement
2. Deflective deferral phrase replacement (referential team mentions allowed)
3. Redundant contact-request replacement
4. Buyer-directed developer-check replacement
5. Reflexive closing-question stripping (intent-aware)
6. Markdown-bold stripping
7. Emoji stripping
8. Scaffolding phrase cleanup
9. WhatsApp-readable paragraph/list spacing
10. Unsupported developer puffery/stat cleanup
11. Sentence-boundary casing repair
"""
import re
from typing import Optional
from app.schemas.conversation import BuyerIntent


# ── Rule 1: Em-dash replacement ────────────────────────────────────────────

def replace_em_dashes(text: str) -> str:
    """
    Replace em-dashes with periods or commas based on context.

    Rules:
    - Em-dash followed by a complete sentence → period + capital
    - Em-dash followed by a fragment → comma
    - Em-dash at end of line → period
    """
    text = re.sub(r' — ([A-Z])', r'. \1', text)
    text = re.sub(r' — ([a-z])', r', \1', text)
    text = re.sub(r' —\s*$', r'.', text, flags=re.MULTILINE)
    text = re.sub(r'\s*—\s*', ', ', text)
    text = re.sub(r',(?=[A-Za-z])', ', ', text)
    return text


# ── Rule 2: Deflective deferral phrases ───────────────────────────────────

DEFERRAL_PATTERNS = [
    r"let me (?:check|confirm|ask)(?:\s+with)?\s+(?:the team|our team)",
    r"I'll (?:check|confirm|ask)(?:\s+with)?\s+(?:the team|our team)",
    r"I've passed (?:this|that|it) to the team",
    r"the team will (?:follow up|get back|reach out)",
    r"I'll get (?:back to you|that to you)(?:\s+(?:on|about) (?:that|this))?\s*(?:shortly|soon)?",
]

DEFERRAL_REPLACEMENTS = [
    "I'll need to double check that. Let me come back to you.",
    "Honestly not sure on that one, I'll find out and circle back.",
    "Don't have that detail right now. I'll get the answer for you.",
    "That's not something I have on hand. Let me confirm and come back.",
]


def is_deflective_team_phrase(text: str) -> bool:
    """Returns True only for deflective deferral phrases, not referential team mentions."""
    for pattern in DEFERRAL_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return True
    return False


def replace_deferral_phrases(text: str) -> str:
    """
    Replace deflective deferral phrases with varied honest alternatives.

    Uses a rotating pool to avoid repetition across conversations.
    """
    for pattern in DEFERRAL_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            import hashlib
            idx = int(hashlib.md5(text.encode()).hexdigest(), 16) % len(DEFERRAL_REPLACEMENTS)
            replacement = DEFERRAL_REPLACEMENTS[idx]
            text = re.sub(pattern, replacement, text, count=1, flags=re.IGNORECASE)
    return text


# Backwards-compatibility alias
def replace_the_team_phrases(text: str) -> str:
    """Deprecated: use replace_deferral_phrases() instead."""
    return replace_deferral_phrases(text)


# ── Rule 3: Closing question gating ────────────────────────────────────────

CONTACT_REQUEST_PATTERNS = [
    (
        r"\s*(?:What'?s|What is) the best (?:way|number|phone number|email|email or number|phone number or email)[^?\n]*\?\s*$",
        " They will follow up on this WhatsApp thread.",
    ),
    (
        r"\s*(?:What'?s|What is) your preferred contact method[^?\n]*\?\s*$",
        " They will follow up on this WhatsApp thread.",
    ),
    (
        r"\s*(?:Could I get|Can I get|Quick,?) (?:your )?name and (?:the )?best (?:number|contact|contact number)[^?\n]*\?\s*$",
        " What name should I put this under?",
    ),
    (
        r"\s*(?:What name should I forward this under,? and what'?s your best contact)\?\s*$",
        " What name should I put this under?",
    ),
    (
        r"\s*(?:What'?s your name,? and where can [^?\n]*find you)\?\s*$",
        " What name should I put this under?",
    ),
    (
        r"\s*(?:What'?s your contact number so Eric can follow up)\?\s*$",
        " Eric will follow up on this WhatsApp thread.",
    ),
]


def replace_redundant_contact_requests(text: str) -> str:
    """Remove requests for phone/contact details already known from WhatsApp."""
    for pattern, replacement in CONTACT_REQUEST_PATTERNS:
        text = re.sub(pattern, replacement, text, count=1, flags=re.IGNORECASE)
    return text.rstrip()


# ── Rule 4: Buyer-directed developer-check replacement ─────────────────────

# Each pattern optionally consumes a leading connector ("that's", "it is", a
# comma) so the replacement reads as a clean standalone sentence rather than
# splicing a full sentence into the middle of a clause (DAL-48 / R4).
_DEV_CHECK_LEAD = r"(?:[,;]?\s*(?:that'?s|that is|it'?s|it is)\s+)?"
DEVELOPER_CHECK_PATTERNS = [
    (
        _DEV_CHECK_LEAD + r"(?:Best to|You'?d want to|You should|Worth)\s+(?:ask|asking|confirm|checking)[^.\n]*(?:Emaar|Sobha|developer)[^.\n]*(?:\.|$)",
        ". The listing brokerage will verify that before you commit.",
    ),
    (
        _DEV_CHECK_LEAD + r"(?:ask|check with|confirm with)\s+(?:Emaar|Sobha|the developer)\s+directly[^.\n]*(?:\.|$)",
        ". The listing brokerage will verify that before you commit.",
    ),
    (
        _DEV_CHECK_LEAD + r"checking with other buyers[^.\n]*(?:\.|$)",
        ". The listing brokerage will verify that before you commit.",
    ),
]


def replace_buyer_directed_developer_checks(text: str) -> str:
    for pattern, replacement in DEVELOPER_CHECK_PATTERNS:
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    # Collapse any stray doubled sentence punctuation introduced when the
    # replacement followed an existing period/comma.
    text = re.sub(r"[.,;]\s*\.\s*", ". ", text)
    text = re.sub(r"\s+\.", ".", text)
    text = re.sub(r"^\s*\.\s*", "", text)  # drop a leading stray period
    return text.rstrip()


# ── Rule 5: Closing question gating ────────────────────────────────────────

# Intents where a closing question is justified (bot needs info to advance)
QUESTION_JUSTIFIED_INTENTS = {
    BuyerIntent.offer_submission,
    BuyerIntent.contact_sharing,
}

# Phase 7.4: expanded patterns covering generic professional-inquiry closes,
# rapport-check closes, and "does that help?" reflexives.
REFLEXIVE_CLOSER_PATTERNS = [
    r"\s*(?:Anything else (?:I can help with|about the (?:property|villa|unit))?\??)\s*$",
    r"\s*(?:What else would you like to know\??)\s*$",
    r"\s*(?:Any (?:other )?questions\??)\s*$",
    r"\s*(?:Is there anything else (?:about the property)?\??)\s*$",
    r"\s*(?:What (?:are you|did you have) (?:looking for|in mind)\??)\s*$",
    r"\s*(?:Hope (?:this|that) helps[!.]?\s*)$",
    # Phase 7.4 additions
    r"\s*(?:Does (?:that|this) (?:help|answer your question|make sense|work for you))\??\s*$",
    r"\s*(?:What['’]s your (?:thinking|preference|next step|timeline|budget|ceiling|position))\??\s*$",
    r"\s*(?:Anything (?:specific|particular) (?:on your mind|you'?d like to know|else))\??\s*$",
    r"\s*(?:Do you have any (?:other )?questions)\??\s*$",
    r"\s*(?:Let me know (?:if you'?d like (?:to know more|more details)|if you have (?:any )?questions))[.!]?\s*$",
    r"\s*(?:Would that help)\??\s*$",
    r"\s*(?:Want me to (?:walk you through|share|explain) (?:more|further|anything else|the details))\??\s*$",
    r"\s*(?:What (?:else )?(?:can I|would you like (?:me )?to (?:help with|explain|share|cover)))\??\s*$",
    # Generic professional-inquiry closer ("invest or end-use?", "for yourself or your client?")
    r"\s*(?:Are you (?:looking )?(?:to invest|for an investment|for end-use|for yourself or)[^?\n]*)\??\s*$",
    r"\s*(?:Is (?:that|this) for (?:yourself|your client|investment|end-use)[^?\n]*)\??\s*$",
    # Buyer-side rapport closes
    r"\s*(?:Would you like (?:me )?to (?:share|send|walk you through|cover)[^?\n]*)\??\s*$",
    r"\s*(?:Shall I (?:send|share|walk you through|cover)[^?\n]*)\??\s*$",
    r"\s*(?:Where are you currently based[^?\n]*)\??\s*$",
    r"\s*(?:What curriculum are you leaning towards[^?\n]*)\??\s*$",
    r"\s*(?:What caught your eye[^?\n]*)\??\s*$",
    r"\s*(?:What'?s drawing you to (?:it|this|this specific unit)[^?\n]*)\??\s*$",
    r"\s*(?:What'?s your timeline (?:looking like)?[^?\n]*)\??\s*$",
]


def strip_reflexive_closers(text: str, intent: Optional[BuyerIntent]) -> str:
    """
    Strip reflexive closing questions when the bot doesn't need information
    from the buyer to advance the conversation.

    Keeps closing questions when intent is in QUESTION_JUSTIFIED_INTENTS,
    except generic contact requests are replaced before this step.
    """
    if intent in QUESTION_JUSTIFIED_INTENTS:
        return text

    for pattern in REFLEXIVE_CLOSER_PATTERNS:
        text = re.sub(pattern, '', text, flags=re.IGNORECASE | re.MULTILINE).rstrip()

    return text.rstrip()


# ── Rule 6: Scaffolding phrase cleanup ────────────────────────────────────

SCAFFOLDING_PATTERNS = [
    (r"\bWhat I can tell you is(?: that)?\s*", ""),
    (r"\bThat said,\s*", ""),
    (r"\bFor your own diligence,\s*", ""),
    (r"\bFor your own diligence\s*", ""),
    (r"^\s*(?:Absolutely|Sure|Of course|Happy to help)[.!]?\s*", ""),
    (r"\bHappy to discuss if anything else comes up[^.?!]*(?:[.?!]|$)", ""),
]


def strip_scaffolding_phrases(text: str) -> str:
    if not text:
        return text
    for pattern, replacement in SCAFFOLDING_PATTERNS:
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    return text.strip()


# ── Rule 7: Markdown bold stripping ────────────────────────────────────────

_MARKDOWN_BOLD_RE = re.compile(r'\*\*([^*]+)\*\*')


def strip_markdown_bold(text: str) -> str:
    """
    Remove **bold** markdown markers entirely.

    WhatsApp doesn't render `**bold**` (it uses single-asterisk *bold*),
    so double-asterisks appear as literal characters and look broken.
    Strip them whole. Asking-price formatting will be handled at the
    presentation layer if needed (dashboard renders markdown; WhatsApp
    does not).
    """
    return _MARKDOWN_BOLD_RE.sub(r'\1', text)


# ── Rule 8: Emoji stripping ───────────────────────────────────────────────

# Cover the major Unicode emoji blocks. Keep currency symbols, math symbols,
# and ordinary punctuation untouched.
_EMOJI_RE = re.compile(
    "["
    "\U0001F300-\U0001F5FF"   # Misc Symbols & Pictographs
    "\U0001F600-\U0001F64F"   # Emoticons
    "\U0001F680-\U0001F6FF"   # Transport & Map
    "\U0001F700-\U0001F77F"   # Alchemical
    "\U0001F780-\U0001F7FF"   # Geometric Shapes Ext
    "\U0001F800-\U0001F8FF"   # Supplemental Arrows-C
    "\U0001F900-\U0001F9FF"   # Supplemental Symbols & Pictographs
    "\U0001FA00-\U0001FA6F"   # Chess Symbols
    "\U0001FA70-\U0001FAFF"   # Symbols & Pictographs Ext-A
    "\U0001F1E0-\U0001F1FF"   # Flags
    "✀-➿"           # Dingbats
    "]+",
    flags=re.UNICODE,
)


def strip_emojis(text: str) -> str:
    """Remove emoji characters from response."""
    return _EMOJI_RE.sub('', text)


# ── Rule 9: Template concatenation cleanup ─────────────────────────────────

def fix_template_concatenation_artifacts(text: str) -> str:
    """Repair common variant-splice artifacts before they reach WhatsApp."""
    if not text:
        return text
    replacements = [
        (
            r"Let me confirm that for you and Honestly not sure on that one, I'll find out and circle back\.on it\.",
            "I don't have that detail in the listing record. I'll ask the listing agent to confirm.",
        ),
        (
            r"\bBefore I need a clearer buying intent before involving the listing agent\.",
            "I need a clearer buying intent before involving the listing agent.",
        ),
        (
            r",?\s+that'?s\s+The listing\s+I need a clearer buying intent before involving the listing agent\.?",
            ". I need clearer buying intent before involving the listing agent.",
        ),
        # R4: a leading connector spliced directly onto the developer-check
        # replacement ("that's The listing brokerage will verify ...").
        (
            r"\b(?:that'?s|that is|it'?s|it is)\s+(The listing brokerage will verify)",
            r"\1",
        ),
        # R4: truncated/garbled "that's The listing <something>" where the
        # brokerage sentence was cut — close the prior clause cleanly.
        (
            r",?\s+(?:that'?s|that is|it'?s|it is)\s+The listing\s+(What I can say|However|That said|On that)",
            r". \1",
        ),
        (
            r",?\s+(?:that'?s|that is|it'?s|it is)\s+The listing\s*$",
            ".",
        ),
        (
            r"\bOnce offers come in,\s+Your dashboard remains the source of truth,",
            "Your dashboard remains the source of truth,",
        ),
        (
            r"\band\s+That'?s not something I have on hand\. Let me confirm and come back\.\.?",
            "That's not something I have on hand. Let me confirm and come back.",
        ),
        (
            r"\bare items your\s+That'?s standard practice\.",
            "are items your conveyancer should verify. That's standard practice.",
        ),
        (
            r"\bIf your buyer wants to put a number forward\.",
            "If your buyer wants to put a number forward, send the amount in this thread and I'll record it.",
        ),
        (
            r"\bIf your buyer wants to put a number forward,\s*Pricing and urgency details sit with the seller\.",
            "Pricing and urgency details sit with the seller. If your buyer wants to put a number forward, send the amount in this thread and I'll record it.",
        ),
    ]
    for pattern, replacement in replacements:
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    text = re.sub(r"\.on it\b", ". on it", text)
    text = re.sub(r"\bbefore before\b", "before", text, flags=re.IGNORECASE)
    return text


def normalize_sentence_boundary_casing(text: str) -> str:
    """Repair casing glitches caused by template/post-processor stitching."""
    if not text:
        return text

    text = re.sub(
        r"([.!?][ \t\n]+)([a-z])",
        lambda m: m.group(1) + m.group(2).upper(),
        text,
    )
    # Comma splices from variants can produce ", That's ..." mid-sentence.
    text = re.sub(
        r"(,\s+)That(?=(?:'s|\s+(?:is|would|will|should|can)\b))",
        r"\1that",
        text,
    )
    return text


# ── Rule 10: WhatsApp spacing cleanup ──────────────────────────────────────

_INLINE_SECTION_LABELS = (
    "Unit specs",
    "Price & fees",
    "Price and fees",
    "Timeline",
    "Developer",
    "Location",
    "Payment",
    "Payment & timeline",
    "Payment and timeline",
    "Fees",
    "Amenities",
    "Connectivity",
    "Costs",
    "NOC",
    "Prayer facilities",
    "Schools near",
    "IB schools near",
    "Listings",
    "Properties",
    "Options",
)


def format_whatsapp_spacing(text: str) -> str:
    """Keep generated replies readable in WhatsApp.

    The model sometimes emits structurally correct answers as one paragraph or
    as inline list strings. Preserve plain text, but enforce line breaks for
    sections, bullets, and long multi-sentence paragraphs.
    """
    if not text:
        return text

    # Stack list items that were emitted inline. Only split where a list marker
    # follows a real boundary (colon, sentence punctuation, or line start). Do
    # not split ordinary hyphens inside names like "DIA - Emirates Hills".
    text = re.sub(r"([:])[ \t]+(\d{1,2}\.\s+)(?=[A-Z0-9])", r"\1\n\2", text)
    text = re.sub(r"([.;])[ \t]+(\d{1,2}\.\s+)(?=[A-Z0-9])", r"\1\n\2", text)
    text = re.sub(r"([:])[ \t]+[-•][ \t]+(?=[A-Z0-9])", r"\1\n- ", text)
    text = re.sub(r"([.;])[ \t]+[-•][ \t]+(?=[A-Z0-9])", r"\1\n- ", text)
    # LLMs often write semicolon-delimited nearby-place lists. Convert those
    # to line items when the sentence is clearly a POI/listing list.
    if re.search(r"\b(?:schools?|listings?|properties|units?)\b", text, re.IGNORECASE):
        text = re.sub(
            r"((?:IB schools near|Schools near|Nearby schools|Here(?:'s| is| are)|Options|Listings|Properties)[^:\n]*:)\s+([A-Z0-9][^;\n]+;\s+[A-Z0-9])",
            r"\1\n\n- \2",
            text,
            flags=re.IGNORECASE,
        )
        text = re.sub(r";\s+(?=[A-Z0-9])", "\n- ", text)

    labels = "|".join(re.escape(label) for label in _INLINE_SECTION_LABELS)
    text = re.sub(
        rf"(?<=[.!?:;])[ \t]+({labels}):",
        r"\n\n\1:",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"(?<!^)(?<!\n)[ \t]+(Other key amenities include|Amenities include|Location-wise,|You're walking distance)",
        r"\n\n\1",
        text,
        flags=re.IGNORECASE,
    )

    paragraphs = re.split(r"\n{2,}", text)
    formatted: list[str] = []
    for paragraph in paragraphs:
        para = paragraph.strip()
        if not para:
            continue
        # Already line-oriented content should stay line-oriented.
        if "\n" in para:
            formatted.append(re.sub(r"\n{3,}", "\n\n", para))
            continue
        sentences = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9])", para)
        if len(sentences) <= 3 or len(para) < 420:
            formatted.append(para)
            continue
        chunks = [
            " ".join(s.strip() for s in sentences[i:i + 3] if s.strip())
            for i in range(0, len(sentences), 3)
        ]
        formatted.append("\n\n".join(chunk for chunk in chunks if chunk))

    return "\n\n".join(formatted).strip()


# ── Rule 11: Volunteered rental-yield figures ──────────────────────────────

_YIELD_DECLINE = (
    "I can't give a rental-yield figure to rely on. That should come from current DLD rental "
    "and transaction data rather than an estimate, so the listing agent or your own analyst can confirm it."
)


def replace_volunteered_yield(text: str) -> str:
    """Strip volunteered rental-yield percentages (DAL-87). A sentence that
    mentions yield/ROI/rental return AND a numeric percentage is replaced once
    with a decline. Fee/LTV/DLD percentages (no yield word) are untouched."""
    if not text:
        return text
    sentences = re.split(r"(?<=[.!?])\s+", text)
    out: list[str] = []
    declined = False
    for sent in sentences:
        low = sent.lower()
        has_yield_word = bool(re.search(r"\b(?:rental\s+yield|gross\s+yield|net\s+yield|\byield\b|\broi\b|rental\s+return)\b", low))
        has_pct = bool(re.search(r"\d+(?:\.\d+)?\s*%", sent))
        if has_yield_word and has_pct:
            if not declined:
                out.append(_YIELD_DECLINE)
                declined = True
            continue  # drop the figure-bearing sentence
        out.append(sent)
    if not declined:
        return text.strip()
    return "\n\n".join(s for s in out if s).strip() if "\n\n" in text else " ".join(s for s in out if s).strip()


# ── Rule 12: Unsupported developer puffery/stat cleanup ────────────────────

_DEVELOPER_PUFFERY_RE = re.compile(
    r"\b(?:"
    r"AAA(?:\s+(?:S&P|rating|rated))?|"
    r"S&P\s+(?:credit\s+)?rating|"
    r"95\s*%\s+on[-\s]?time|"
    r"on[-\s]?time\s+delivery\s+rate|"
    r"100,?000\+?\s+(?:homes|units)|"
    r"outperform(?:s|ed|ing)?\b|"
    r"gold\s+standard"
    r")",
    re.IGNORECASE,
)


def strip_unsupported_developer_puffery(text: str) -> str:
    """Remove likely hallucinated developer ratings/performance claims."""
    if not text or not _DEVELOPER_PUFFERY_RE.search(text):
        return text

    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    kept = [part for part in parts if part and not _DEVELOPER_PUFFERY_RE.search(part)]
    if kept:
        return " ".join(kept).strip()

    low = text.lower()
    if "emaar" in low:
        return (
            "Emaar is one of Dubai's established developers, with landmark projects "
            "including Downtown Dubai and Burj Khalifa. Still verify the SPA and "
            "title/NOC position before you commit."
        )
    if "developer" in low:
        return (
            "The developer has an established Dubai track record. Still verify the "
            "SPA and title/NOC position before you commit."
        )
    return ""


# ── Main validator ─────────────────────────────────────────────────────────

def validate_and_rewrite_response(
    response: str,
    intent: Optional[BuyerIntent] = None,
) -> tuple[str, dict]:
    """
    Single entry point for ALL bot output.

    Returns (rewritten_response, telemetry_dict).
    """
    if not response:
        return response, {
            "em_dashes_replaced": 0,
            "deferral_phrases_replaced": 0,
            "contact_requests_replaced": 0,
            "developer_checks_replaced": 0,
            "closing_questions_stripped": 0,
            "scaffolding_phrases_stripped": 0,
            "markdown_bold_stripped": 0,
            "emojis_stripped": 0,
            "concat_artifacts_fixed": 0,
            "whatsapp_spacing_fixed": 0,
            "yield_figures_stripped": 0,
            "developer_puffery_stripped": 0,
            "sentence_casing_fixed": 0,
        }

    original = response
    telemetry = {
        "em_dashes_replaced": 0,
        "deferral_phrases_replaced": 0,
        "contact_requests_replaced": 0,
        "developer_checks_replaced": 0,
        "closing_questions_stripped": 0,
        "scaffolding_phrases_stripped": 0,
        "markdown_bold_stripped": 0,
        "emojis_stripped": 0,
        "concat_artifacts_fixed": 0,
        "whatsapp_spacing_fixed": 0,
        "yield_figures_stripped": 0,
        "developer_puffery_stripped": 0,
        "sentence_casing_fixed": 0,
    }

    telemetry["em_dashes_replaced"] = original.count('—')
    response = replace_em_dashes(response)

    for pattern in DEFERRAL_PATTERNS:
        if re.search(pattern, original, re.IGNORECASE):
            telemetry["deferral_phrases_replaced"] += 1
    response = replace_deferral_phrases(response)

    pre_contact = response
    response = replace_redundant_contact_requests(response)
    if response != pre_contact:
        telemetry["contact_requests_replaced"] = 1

    pre_developer = response
    response = replace_buyer_directed_developer_checks(response)
    if response != pre_developer:
        telemetry["developer_checks_replaced"] = 1

    pre_strip = response
    response = strip_reflexive_closers(response, intent)
    if response != pre_strip:
        telemetry["closing_questions_stripped"] = 1

    pre_scaffold = response
    response = strip_scaffolding_phrases(response)
    if response != pre_scaffold:
        telemetry["scaffolding_phrases_stripped"] = 1

    pre_md = response
    response = strip_markdown_bold(response)
    if response != pre_md:
        # Each pair of ** brackets is one stripped bold span
        telemetry["markdown_bold_stripped"] = (pre_md.count("**") - response.count("**")) // 2

    pre_emoji = response
    response = strip_emojis(response)
    if response != pre_emoji:
        telemetry["emojis_stripped"] = sum(
            len(m) for m in _EMOJI_RE.findall(pre_emoji)
        )

    pre_concat = response
    response = fix_template_concatenation_artifacts(response)
    if response != pre_concat:
        telemetry["concat_artifacts_fixed"] = 1

    pre_case = response
    response = normalize_sentence_boundary_casing(response)
    if response != pre_case:
        telemetry["sentence_casing_fixed"] = 1

    pre_yield = response
    response = replace_volunteered_yield(response)
    if response != pre_yield:
        telemetry["yield_figures_stripped"] = 1

    pre_puffery = response
    response = strip_unsupported_developer_puffery(response)
    if response != pre_puffery:
        telemetry["developer_puffery_stripped"] = 1

    pre_spacing = response
    response = format_whatsapp_spacing(response)
    if response != pre_spacing:
        telemetry["whatsapp_spacing_fixed"] = 1

    return response, telemetry
