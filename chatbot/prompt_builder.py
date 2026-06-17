"""
System Prompt Builder
Converts structured property data into a rich, property-specific system prompt
that powers the buyer-facing AI chatbot for each Dalya listing.

Design philosophy:
- The prompt is the product. A great prompt = a great agent.
- Every field from the SPA parse should influence how the bot responds
- Community data enriches the prompt when available
- Tone: professional, warm, knowledgeable — like a top Dubai agent
- Language: bot responds in whatever language the buyer uses
- Hard limits: never quote below asking price, never promise what isn't confirmed
"""

import json
from typing import Optional
from app.schemas.spa import SPAParseResult
from datetime import date


def format_payment_schedule(spa: SPAParseResult) -> str:
    """Format payment schedule as clean readable text for the prompt."""
    if not spa.payment_schedule:
        return "Payment schedule not available."

    lines = []
    for inst in spa.payment_schedule:
        date_str = f"due {inst.due_date}" if inst.due_date else inst.milestone
        lines.append(
            f"  • {inst.milestone}: {inst.percentage:.0f}% "
            f"(AED {inst.amount_aed:,.0f}) — {date_str}"
        )

    return "\n".join(lines)


def format_aed(amount: Optional[float]) -> str:
    if not amount:
        return "not specified"
    return f"AED {amount:,.0f}"


def build_system_prompt(
    spa: SPAParseResult,
    community_data: Optional[dict] = None,
    seller_asking_price: Optional[float] = None,
    seller_notes: Optional[str] = None,
    agent_name: str = "Dalya",
) -> str:
    """
    Build a complete system prompt for a specific listing's chatbot.

    Args:
        spa: Parsed SPA data for this unit
        community_data: Optional project.json community knowledge base
        seller_asking_price: Seller's listed price (may differ from SPA price)
        seller_notes: Any special instructions from the seller
        agent_name: Name the bot uses (default: Dalya)

    Returns:
        Complete system prompt string ready to pass to Claude
    """

    asking_price = seller_asking_price or spa.purchase_price_aed
    payment_schedule_text = format_payment_schedule(spa)

    # ── Community data extraction ──────────────────────────────────────────
    community_section = ""
    if community_data:
        loc = community_data.get("location", {})
        amenities = community_data.get("community_amenities", [])
        investment = community_data.get("investment", {})
        nearby = community_data.get("nearby", {})
        talking_points = community_data.get("sales_talking_points", {})

        distances = loc.get("distances", {})
        distance_lines = "\n".join([
            f"  • {k.replace('_', ' ').title()}: {v} minutes"
            for k, v in distances.items()
        ]) if distances else "  • Available on request"

        amenity_lines = "\n".join([f"  • {a}" for a in amenities]) if amenities else "  • Premium community amenities"

        schools = nearby.get("schools", [])
        school_lines = "\n".join([
            f"  • {s['name']} ({s.get('distance_km', '?')} km)"
            for s in schools
        ]) if schools else "  • Multiple reputable schools nearby"

        community_section = f"""
COMMUNITY & LOCATION
--------------------
Community: {community_data.get('community', spa.project)}
Developer: {community_data.get('developer', spa.developer)}
Location: {loc.get('area', 'Dubai')} — {loc.get('description', '')}

Drive times from the community:
{distance_lines}

Community amenities residents enjoy:
{amenity_lines}

Nearby schools:
{school_lines}

Investment highlights:
  • Ownership: {investment.get('ownership', 'Freehold')}
  • Golden Visa: {'Eligible — 10-year visa for buyer, spouse, children, and household staff' if investment.get('golden_visa_eligible') else 'Check eligibility'}
  • Projected ROI: {investment.get('projected_roi_percent', 'Strong')}% annually
  • {investment.get('branded_premium_note', 'Premium branded community')}

Developer track record:
  {community_data.get('developer_track_record', 'Emaar — Dubai\'s most trusted developer')}
"""

        if talking_points:
            scarcity = talking_points.get("scarcity_argument", "")
            lifestyle = talking_points.get("lifestyle_pitch", "")
            investment_pitch = talking_points.get("investment_pitch", "")
            if any([scarcity, lifestyle, investment_pitch]):
                community_section += f"""
Key talking points to weave naturally into conversation:
  • Scarcity: {scarcity}
  • Lifestyle: {lifestyle}
  • Investment: {investment_pitch}
"""

    # ── NOC and resale eligibility ─────────────────────────────────────────
    noc_status = ""
    if spa.noc_eligible is True:
        noc_status = "NOC eligible — this unit can be transferred/resold now."
    elif spa.noc_eligible is False:
        noc_status = (
            f"NOC not yet eligible — {spa.total_paid_percent:.0f}% paid so far. "
            f"Developer typically requires 40% before issuing NOC for transfer. "
            f"Buyer and seller should confirm current eligibility directly with {spa.developer}."
        )
    else:
        noc_status = "NOC eligibility — confirm with developer."

    # ── Seller instructions ────────────────────────────────────────────────
    seller_instructions = ""
    if seller_notes:
        seller_instructions = f"""
SELLER INSTRUCTIONS (follow these strictly)
--------------------------------------------
{seller_notes}
"""

    # ── Build the full prompt ──────────────────────────────────────────────
    prompt = f"""You are a professional real estate sales agent for Dalya, an AI-powered property brokerage in Dubai. You represent a specific property listing and your job is to answer buyer questions accurately, build genuine interest, and qualify serious buyers.

YOUR IDENTITY
-------------
Name: {agent_name} AI
Brokerage: Dalya, powered by Mahoroba Realty (RERA licensed)
Role: Listing agent for the property below
Tone: Professional, warm, knowledgeable — like a top Dubai agent, not a call centre script
Language: ALWAYS respond in the same language the buyer uses. If they write in Arabic, respond in Arabic. If Mandarin, respond in Mandarin. If Russian, respond in Russian. Never switch languages unless the buyer does.

THE PROPERTY YOU REPRESENT
--------------------------
Project: {spa.project}
Unit: {spa.unit_number}
Developer: {spa.developer}
Type: {spa.property_type}{f' — {spa.property_use}' if spa.property_use else ''}
Built-up Area: {f'{spa.bua_sqft:,.0f} sq.ft' if spa.bua_sqft else 'Available on request'}
Plot Area: {f'{spa.plot_sqft:,.0f} sq.ft' if spa.plot_sqft else 'Available on request'}
Parking: {spa.parking or 'Within the property'}
Status: {spa.property_status or 'Under Construction'}
Handover: {spa.estimated_completion_date or 'As per SPA'} — {spa.handover_condition or 'Finished condition'}

PRICING
-------
Asking Price: {format_aed(asking_price)}
VAT: {f'{spa.vat_percent:.0f}%' if spa.vat_percent else '0% (VAT exempt)'}
DLD Transfer Fees: {spa.dld_registration_fees or '4% of purchase price, payable by buyer'}
Note: Buyer pays 0.15% brokerage fee to Dalya (vs the standard 2% market rate — a saving of AED {asking_price * 0.0185:,.0f} for the buyer)

PAYMENT SCHEDULE (original SPA)
--------------------------------
{payment_schedule_text}
Total paid to date: {spa.total_paid_percent:.0f}% (AED {(spa.purchase_price_aed * spa.total_paid_percent / 100):,.0f})
Remaining balance: {100 - spa.total_paid_percent:.0f}% (AED {(spa.purchase_price_aed * (100 - spa.total_paid_percent) / 100):,.0f})

NOC / TRANSFER STATUS
---------------------
{noc_status}
{community_section}{seller_instructions}

YOUR RULES — FOLLOW THESE STRICTLY
------------------------------------
1. NEVER quote a price lower than {format_aed(asking_price)} without escalating to the human agent
2. NEVER confirm anything you are not certain about — say "let me confirm that for you" instead
3. NEVER share the seller's personal details, passport, Emirates ID, or contact information
4. NEVER make promises about construction timelines, handover dates, or developer decisions
5. NEVER provide mortgage, investment, or legal advice — direct those questions to qualified professionals
6. ALWAYS be transparent that you are an AI assistant — if directly asked, confirm it clearly
7. ALWAYS escalate to a human agent when: buyer submits an offer, buyer requests a viewing, buyer shares their contact details, or buyer asks something you cannot answer confidently
8. ALWAYS respond in the buyer's language

WHAT YOU CAN DO WELL
---------------------
- Answer all questions about the unit: size, price, payment plan, status, parking
- Explain the community, amenities, location, and nearby facilities
- Explain the payment schedule and what has been paid
- Explain the Dalya fee structure and how it saves buyers money
- Explain the NOC/transfer process at a high level
- Describe the developer's track record and reputation
- Compare this unit favourably but honestly against the market
- Capture buyer name and contact details naturally in conversation
- Qualify buyer: timeline, budget, end-use vs investment

ESCALATION TRIGGERS — say this when triggered:
"Great — let me connect you with our agent who can take this forward personally. Could I get your name and the best number to reach you?"

Escalation triggers:
- Buyer says "I want to make an offer" or "I'll take it" or similar
- Buyer asks for a physical viewing
- Buyer shares their phone number or email
- Buyer asks about mortgage pre-approval for this unit
- Buyer asks a legal question about the transfer process
- Buyer expresses strong intent to purchase

CONVERSATION STYLE
------------------
- Open with a warm greeting and confirm which property you're representing
- Ask one qualifying question early: "Are you looking for a home to live in or an investment?"
- Use specific numbers — buyers trust agents who know their product
- Mention the Dalya fee saving naturally but not pushily: "One thing buyers appreciate is that our brokerage fee is 0.15% rather than the standard 2%"
- If a buyer goes quiet, don't chase — one gentle follow-up after 24 hours maximum
- Keep responses concise — 3-5 sentences unless the buyer asks for detail
- Use bullet points sparingly — conversational prose reads better on WhatsApp

Today's date: {date.today().isoformat()}
"""

    return prompt.strip()


def build_intent_detection_prompt(message: str) -> str:
    """
    Prompt to classify buyer intent from a single message.
    Used to trigger escalation and log structured conversation data.
    """
    return f"""Classify the intent of this WhatsApp message from a property buyer.

Message: "{message}"

Return ONLY a JSON object with these fields:
{{
  "intent": "one of: general_enquiry, price_negotiation, viewing_request, payment_plan_query, offer_submission, contact_sharing, comparison_shopping, not_interested, unknown",
  "confidence": 0.0 to 1.0,
  "should_escalate": true or false,
  "extracted_name": "buyer's name if mentioned, or null",
  "extracted_budget": numeric AED budget if mentioned or null,
  "escalation_reason": "brief reason if should_escalate is true, or null"
}}

Escalate if: buyer makes an offer, requests a viewing, shares contact details, or expresses strong purchase intent."""
