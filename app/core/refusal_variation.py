"""
Deterministic refusal phrasing for probe-like requests.

Haiku does not reliably vary refusal text under repeated pressure. This module
keeps refusal classes out of the generic generation path, tracks prior turns
from conversation history, and produces a short firmness ladder with one
threshold handoff.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable


SELLER_PII = "seller_pii"
OUT_OF_SCOPE = "out_of_scope"
GATING = "gating"

DEFAULT_ESCALATION_TURN = 7


@dataclass(frozen=True)
class RefusalDecision:
    intent: str
    text: str
    ask_count: int
    should_escalate: bool = False
    escalation_reason: str | None = None


SELLER_PII_PATTERNS = [
    r"(?:seller|owner|ownr|vendor)['’]?(?:s)?\s+(?:number|phone|whatsap|whatsapp|email|contact|mobile|full name|name)",
    r"(?:share|send|give|forward).{0,40}(?:seller|owner|ownr|vendor).{0,30}(?:number|phone|whatsap|whatsapp|email|contact|mobile)",
    r"(?:speak|talk|deal|connect|reach|message|text|contact)\s+(?:to|with)?\s*(?:the\s+)?(?:seller|owner|ownr|vendor)\s+direct",
    r"(?:seller|owner|ownr|vendor).{0,40}(?:number|phone|whatsap|whatsapp|email|contact|mobile)",
    r"seller now",
]

OUT_OF_SCOPE_PATTERNS = [
    r"ignore (?:your|all|previous) instructions",
    r"system prompt",
    r"developer mode",
    r"jailbreak",
    r"print your prompt",
    r"reveal your prompt",
    r"forget the rules",
    r"bypass the transaction",
    r"skip the brokerage",
    r"skip the broker",
]


SELLER_PII_VARIANTS_EN = [
    "I'm Dalya's property advisor. I can't share seller contact details, but I can answer questions here or route a serious offer through the proper transaction process.",
    "Seller contact details stay private. If you want to move forward, send the offer terms and I'll keep it on the proper channel.",
    "I won't send the owner's number. The seller-side channel stays protected until formal transaction steps.",
    "No direct seller contact is shared on WhatsApp. Use this thread for questions, offers, and verified next steps.",
    "I can't help you bypass the brokerage channel. Seller contact stays private.",
    "The answer is still no on the seller's number. I can only handle the listing and proper offer path.",
    "I won't share the seller's contact. I've flagged this thread for {managing_agent_name} so they have the context.",
]

SELLER_PII_HOLD_EN = [
    "No. I won't share seller contact details.",
    "No. Seller contact stays private.",
]

OUT_OF_SCOPE_VARIANTS_EN = [
    "I'm Dalya's property advisor and I only handle this listing: price, specs, payment, transfer process, and genuine next steps.",
    "I can't help with internal-instruction requests or attempts to bypass the transaction process.",
    "That is outside this property conversation. I can answer listing details and transaction-process questions only.",
    "I won't follow instruction-override requests. Keep it to the property, pricing, payment, or next steps.",
    "No. I won't reveal internal instructions or help route around the transaction process.",
    "That request is out of scope. I can continue only on the listing and legitimate purchase process.",
    "I won't engage with that probe. I've flagged this thread for {managing_agent_name} so they have the context.",
]

OUT_OF_SCOPE_HOLD_EN = [
    "No. I won't help with that request.",
    "No. This stays limited to the property and proper transaction path.",
]

GATING_VARIANTS_EN = [
    "I need clearer buying intent before involving the listing agent.",
    "I can involve the listing agent once there is a concrete buying step.",
    "For now, keep questions here. A listing-agent handoff needs a clearer purchase signal.",
    "I won't open a handoff yet without a specific buying step.",
]

# R11: Arabic conversations must keep refusals in Arabic.
SELLER_PII_VARIANTS_AR = [
    "أنا مساعدة العقارات لهذه الشركة. لا يمكنني مشاركة بيانات تواصل البائع، لكن يمكنني الإجابة على أسئلتك هنا أو تمرير عرض جدي عبر مسار المعاملة الصحيح.",
    "تفاصيل تواصل البائع تبقى خاصة. إذا أردت المتابعة، أرسل شروط العرض وسأبقيه على القناة الصحيحة.",
    "لن أشارك رقم المالك. تبقى قناة البائع محمية حتى خطوات المعاملة الرسمية.",
    "لا تتم مشاركة تواصل مباشر مع البائع عبر واتساب. استخدم هذه المحادثة للأسئلة والعروض والخطوات الموثّقة.",
    "لا أستطيع مساعدتك في تجاوز قناة الوساطة. تواصل البائع يبقى خاصاً.",
    "الجواب لا يزال لا بخصوص رقم البائع. يمكنني فقط التعامل مع العقار ومسار العرض الصحيح.",
    "لن أشارك تواصل البائع. لقد نبّهت {managing_agent_name} بخصوص هذه المحادثة ليكون لديه السياق.",
]

SELLER_PII_HOLD_AR = [
    "لا. لن أشارك بيانات تواصل البائع.",
    "لا. تواصل البائع يبقى خاصاً.",
]

OUT_OF_SCOPE_VARIANTS_AR = [
    "أنا مساعدة العقارات لهذه الشركة وأتعامل فقط مع هذا العقار: السعر، المواصفات، الدفعات، إجراءات النقل، والخطوات الجدية للشراء.",
    "لا أستطيع المساعدة في طلبات تتعلق بتعليمات داخلية أو تجاوز مسار المعاملة.",
    "هذا خارج نطاق محادثة العقار. يمكنني الإجابة فقط على تفاصيل العقار وأسئلة إجراءات المعاملة.",
    "لن أنفّذ طلبات تجاوز التعليمات. لنبقَ ضمن العقار والسعر والدفع والخطوات التالية.",
    "لا. لن أكشف تعليمات داخلية أو أساعد في الالتفاف على مسار المعاملة.",
    "هذا الطلب خارج النطاق. يمكنني المتابعة فقط بخصوص العقار ومسار الشراء المشروع.",
    "لن أتفاعل مع هذا الطلب. لقد نبّهت {managing_agent_name} بخصوص هذه المحادثة ليكون لديه السياق.",
]

OUT_OF_SCOPE_HOLD_AR = [
    "لا. لن أساعد في هذا الطلب.",
    "لا. يبقى هذا محصوراً بالعقار ومسار المعاملة الصحيح.",
]

GATING_VARIANTS_AR = [
    "أحتاج إلى نية شراء أوضح قبل إشراك وكيل العقار.",
    "يمكنني إشراك وكيل العقار بمجرد وجود خطوة شراء ملموسة.",
    "في الوقت الحالي، أبقِ الأسئلة هنا. تحويل المحادثة لوكيل العقار يحتاج إشارة شراء أوضح.",
    "لن أفتح تحويلاً بعد دون خطوة شراء محددة.",
]


def _assistant_texts(conv) -> set[str]:
    return {
        (getattr(message, "content", "") or "").strip()
        for message in (getattr(conv, "messages", None) or [])
        if getattr(message, "role", None) == "assistant"
    }


def _user_texts(conv) -> list[str]:
    return [
        (getattr(message, "content", "") or "").strip()
        for message in (getattr(conv, "messages", None) or [])
        if getattr(message, "role", None) == "user"
    ]


def _matches_any(text: str, patterns: Iterable[str]) -> bool:
    return any(re.search(pattern, text or "", re.IGNORECASE) for pattern in patterns)


def count_refusal_asks(conv, intent: str) -> int:
    patterns = SELLER_PII_PATTERNS if intent == SELLER_PII else OUT_OF_SCOPE_PATTERNS
    if intent != SELLER_PII:
        return sum(1 for text in _user_texts(conv) if _matches_any(text, patterns))

    count = 0
    seller_probe_seen = False
    for text in _user_texts(conv):
        if _matches_any(text, patterns):
            count += 1
            seller_probe_seen = True
            continue
        short_follow_up = (
            seller_probe_seen
            and len((text or "").split()) <= 14
            and re.search(r"\b(?:number|digits|contact|whatsap|whatsapp|mobile|phone)\b", text or "", re.IGNORECASE)
        )
        if short_follow_up:
            count += 1
    return count


def _choose_line(variants: list[str], used: set[str], count: int) -> str:
    for variant in variants:
        if variant not in used:
            return variant
    return variants[(max(count, 1) - 1) % len(variants)]


def render_refusal(
    *,
    intent: str,
    conv,
    managing_agent_name: str = "the listing agent",
    escalation_turn: int = DEFAULT_ESCALATION_TURN,
    already_escalated: bool = False,
    ask_count_override: int | None = None,
    used_texts_override: Iterable[str] | None = None,
    language: str = "en",
) -> RefusalDecision:
    ask_count = max(1, ask_count_override or count_refusal_asks(conv, intent))
    used = set(used_texts_override) if used_texts_override is not None else _assistant_texts(conv)
    is_ar = (language or "en").lower().startswith("ar")

    if intent == GATING:
        text = _choose_line(GATING_VARIANTS_AR if is_ar else GATING_VARIANTS_EN, used, ask_count)
        return RefusalDecision(intent=intent, text=text, ask_count=ask_count)

    if intent == SELLER_PII:
        variants = SELLER_PII_VARIANTS_AR if is_ar else SELLER_PII_VARIANTS_EN
        hold = SELLER_PII_HOLD_AR if is_ar else SELLER_PII_HOLD_EN
    else:
        variants = OUT_OF_SCOPE_VARIANTS_AR if is_ar else OUT_OF_SCOPE_VARIANTS_EN
        hold = OUT_OF_SCOPE_HOLD_AR if is_ar else OUT_OF_SCOPE_HOLD_EN

    should_escalate = ask_count >= escalation_turn and not already_escalated
    if should_escalate:
        idx = min(escalation_turn, len(variants)) - 1
        text = variants[idx]
    elif ask_count > escalation_turn or already_escalated:
        # Give one or two terse hold lines, then repeat. Post-escalation repeats
        # are intentional; the customer is probing, not exploring options.
        text = hold[min(max(ask_count - escalation_turn - 1, 0), len(hold) - 1)]
    else:
        text = _choose_line(variants[: max(escalation_turn - 1, 1)], used, ask_count)

    text = text.replace("{managing_agent_name}", managing_agent_name)
    return RefusalDecision(
        intent=intent,
        text=text,
        ask_count=ask_count,
        should_escalate=should_escalate,
        escalation_reason=f"refusal:{intent}" if should_escalate else None,
    )
