"""
Comprehensive WhatsApp chatbot test — runs all personas against both listings.
Saves results to /tmp/chatbot_test_results.json as it goes.
"""
import json
import sys
import time
import requests
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tests.safety import UnsafeTestDatabaseError, assert_safe_test_database, load_test_environment_file

BASE_URL = "http://localhost:8000"
RESULTS_FILE = "/tmp/chatbot_test_results.json"

LOW_PRICE_ID = "__harness_low_price__"
HIGH_PRICE_ID = "__harness_high_price__"


def configure_harness_listings():
    """Seed the canonical harness and map the legacy persona roles to harness listings."""
    global LOW_PRICE_ID, HIGH_PRICE_ID
    from app.db.session import SessionLocal
    from tests.harness import build_harness

    with SessionLocal() as db:
        seed = build_harness(db)

    if not seed.listings:
        raise RuntimeError("Canonical harness did not return any listings for chatbot_test.py")

    HIGH_PRICE_ID = max(seed.listings, key=lambda item: item.asking_price_aed).listing_id
    LOW_PRICE_ID = min(seed.listings, key=lambda item: item.asking_price_aed).listing_id
    print(f"[harness] high-price role -> {HIGH_PRICE_ID}")
    print(f"[harness] low-price role -> {LOW_PRICE_ID}")


def ask(listing_id, phone, message):
    try:
        r = requests.post(
            f"{BASE_URL}/api/v1/whatsapp/send-test",
            params={"listing_id": listing_id, "buyer_phone": phone, "message": message},
            timeout=120,
        )
        data = r.json()
        return {
            "response": data.get("bot_response", ""),
            "escalation": data.get("escalation_triggered", False),
            "escalation_data": data.get("escalation"),
        }
    except Exception as e:
        return {"response": f"ERROR: {e}", "escalation": False, "escalation_data": None}


def run_persona(listing_id, persona_name, phone, messages, results):
    print(f"\n{'='*60}")
    print(f"PERSONA: {persona_name} | Phone: {phone}")
    print(f"{'='*60}")

    persona_results = []
    for i, msg in enumerate(messages):
        print(f"\n  Q{i+1}: {msg[:80]}...")
        start = time.time()
        result = ask(listing_id, phone, msg)
        elapsed = time.time() - start
        print(f"  A{i+1}: {result['response'][:100]}...")
        print(f"  Escalation: {result['escalation']} | Time: {elapsed:.1f}s")

        persona_results.append({
            "question": msg,
            "response": result["response"],
            "escalation": result["escalation"],
            "escalation_data": result["escalation_data"],
            "time_s": round(elapsed, 1),
        })

    results.append({
        "persona": persona_name,
        "phone": phone,
        "listing_id": listing_id,
        "messages": persona_results,
    })

    # Save after each persona
    with open(RESULTS_FILE, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\n  [Saved to {RESULTS_FILE}]")


def main():
    load_test_environment_file()
    try:
        assert_safe_test_database(operation="scripts/chatbot_test.py persona run")
    except UnsafeTestDatabaseError as exc:
        raise SystemExit(f"\n*** DALYA TEST DATABASE SAFETY GUARD ***\n{exc}\n") from exc

    configure_harness_listings()

    results = []
    batch = sys.argv[1] if len(sys.argv) > 1 else "all"

    # ── the developer PERSONAS ──

    if batch in ("all", "the developer", "s1"):
        run_persona(LOW_PRICE_ID, "P1: Sarah Chen (First-time buyer)", "+971501111001", [
            "Hi, I'm looking at this apartment. Can you tell me more about it?",
            "What's the size of the unit?",
            "How many bedrooms and bathrooms does it have?",
            "What's the asking price?",
            "What area is this in? I'm new to Dubai and don't know the neighborhoods",
            "What schools are nearby? I have a 7-year-old",
            "Is it freehold? Can I get a Golden Visa?",
            "What's the payment schedule? How much has been paid already?",
            "When is the expected completion?",
            "Can I come see the unit?",
            "I'm interested. Can I make an offer of AED 5,500,000?",
            "Actually, let me offer AED 5,800,000",
        ], results)

    if batch in ("all", "the developer", "s2"):
        run_persona(LOW_PRICE_ID, "P2: Ahmad (Experienced investor)", "+971501111002", [
            "What's the ROI on this unit?",
            "What's the developer track record? I've had issues with delayed handovers before",
            "What's the service charge per sqft?",
            "How does this compare to similar units in Dubai Marina?",
            "What's the current rental yield in Dubai Harbour?",
            "What's left on the payment plan?",
            "Is NOC transfer possible? What percentage has been paid?",
            "I want to offer AED 6,100,000",
        ], results)

    if batch in ("all", "the developer", "s3"):
        run_persona(LOW_PRICE_ID, "P3: Mohammed (Agent)", "+971501111003", [
            "I have a client interested. Can you share the SPA details?",
            "What's the plot number for this unit?",
            "What's the commission structure?",
            "Is the seller willing to negotiate on the price?",
            "Can my client get the unit transferred before completion?",
            "What are the DLD transfer fees?",
            "Does the seller have any other units available?",
        ], results)

    if batch in ("all", "the developer", "s4"):
        run_persona(LOW_PRICE_ID, "P4: Arabic speaker", "+971501111004", [
            "مرحبا، أريد معلومات عن هذه الشقة",
            "كم سعر الشقة؟",
            "ما هي مساحة الشقة؟",
            "هل يمكنني الحصول على تأشيرة ذهبية؟",
            "ما هي خطة الدفع المتبقية؟",
        ], results)

    if batch in ("all", "the developer", "s5"):
        run_persona(LOW_PRICE_ID, "P5: James (Budget negotiator)", "+971501111005", [
            "What's your best price?",
            "That's way above my budget. Would you take 4.5 million?",
            "Can the seller come down to 5 million?",
            "What about 5.75 million?",
        ], results)

    if batch in ("all", "the developer", "s6"):
        run_persona(LOW_PRICE_ID, "P6: Quick-fire facts", "+971501111006", [
            "Developer name?",
            "Unit number?",
            "Total purchase price?",
            "BUA in sqft?",
            "Completion date?",
            "How much has been paid so far?",
            "How many parking spots?",
            "What floor is it on?",
            "What's the view like?",
            "Are pets allowed?",
        ], results)

    # ── the community PERSONAS ──

    if batch in ("all", "the community", "o1"):
        run_persona(HIGH_PRICE_ID, "P7: Fatima (UHNW family)", "+971502222001", [
            "Good morning, we're looking at this villa. How big is it?",
            "What's the plot size?",
            "Tell me about the community — we have three children",
            "What amenities does The the community have?",
            "How does the cycling track work? My husband is an avid cyclist",
            "Are there any lagoons or beach areas?",
            "What schools are nearby? We need IB curriculum",
            "How is the developer? We've bought from the developer before in Downtown",
            "What's the asking price for this villa?",
            "What's the remaining payment schedule?",
            "How much has been paid so far?",
            "Is the villa eligible for Golden Visa?",
            "We'd like to make an offer. AED {prior_offer}",
        ], results)

    if batch in ("all", "the community", "o2"):
        run_persona(HIGH_PRICE_ID, "P8: Raj (Comparing investor)", "+971502222002", [
            "How does this compare to the developer developments?",
            "What's the ROI projection?",
            "What's the handover timeline?",
            "Can I see the floor plan?",
            "What's the service charge?",
            "Is there a penalty for late payment on the installments?",
            "What are the DLD registration fees?",
            "Do you have any apartments as well? I'm also looking for something smaller",
        ], results)

    if batch in ("all", "the community", "o3"):
        run_persona(HIGH_PRICE_ID, "P9: Mike (Skeptical)", "+971502222003", [
            "Is this an AI or a real person?",
            "What happens if the developer goes bankrupt before completion?",
            "Can I get my money back if I don't want the unit anymore?",
            "Why is the resale price higher than the SPA price? Seems like a ripoff",
            "I've heard Dubai is in a property bubble. What do you think?",
            "What guarantees do I have that this will be delivered on time?",
            "Can you share the original SPA document?",
            "I'll offer 15 million",
            "Fine, 16.9 million",
        ], results)

    if batch in ("all", "the community", "o4"):
        run_persona(HIGH_PRICE_ID, "P10: Russian speaker", "+971502222004", [
            "Здравствуйте, расскажите о вилле",
            "Какая площадь участка?",
            "Сколько стоит?",
            "Когда планируется сдача?",
            "Какие школы рядом?",
        ], results)

    if batch in ("all", "the community", "o5"):
        run_persona(HIGH_PRICE_ID, "P11: Hindi speaker", "+971502222005", [
            "नमस्ते, इस विला के बारे में बताइए",
            "किराया कितना आता है?",
            "गोल्डन वीसा मिलेगा?",
        ], results)

    if batch in ("all", "the community", "o6"):
        run_persona(HIGH_PRICE_ID, "P12: Edge cases + cross-listing", "+971502222006", [
            "Do you have any other properties available?",
            "I'm looking for something under 7 million",
            "What if I want a 2-bedroom apartment instead?",
            "Can I speak to a human?",
            "What's the weather like in Dubai?",
        ], results)

    print(f"\n\n{'='*60}")
    print(f"ALL TESTS COMPLETE — {len(results)} personas, {sum(len(p['messages']) for p in results)} messages")
    print(f"Results saved to {RESULTS_FILE}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
