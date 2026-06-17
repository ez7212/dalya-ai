import requests
import json
import sys

__test__ = False

LISTING_ID = "7eb2b37b95468b1856d907113ad4c09c36be"
BASE_URL = "http://localhost:8000/api/v1/whatsapp/send-test"
results = []

def ask(listing_id, phone, message):
    r = requests.post(BASE_URL, params={'listing_id': listing_id, 'buyer_phone': phone, 'message': message}, timeout=120)
    data = r.json()
    return data.get('bot_response', str(data)), data.get('escalation_triggered', False), data.get('escalation')

def test_msg(persona, phone, message, listing_id=LISTING_ID):
    try:
        resp, esc_triggered, esc_detail = ask(listing_id, phone, message)
    except Exception as e:
        resp, esc_triggered, esc_detail = f"ERROR: {e}", False, None
    result = {
        'persona': persona,
        'phone': phone,
        'question': message,
        'response': resp,
        'escalation_triggered': esc_triggered,
        'escalation_detail': esc_detail
    }
    results.append(result)
    q_display = message[:80] if message else "(empty)"
    print(f"[{persona}] Q: {q_display}", flush=True)
    print(f"  A: {str(resp)[:300]}", flush=True)
    print(f"  Esc: {esc_triggered} | {esc_detail}", flush=True)
    print("---", flush=True)
    # Save incrementally
    with open('/Users/eric/dalya-ai/test_oasis_results.json', 'w') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    return result

# PERSONA 7: Fatima Al Thani
print("=== PERSONA 7: Fatima Al Thani ===", flush=True)
p = "+971502222001"
for msg in [
    "Good morning, we're looking at this villa. How big is it?",
    "What's the plot size?",
    "Tell me about the community \u2014 we have three children",
    "What amenities does The Oasis have?",
    "How does the cycling track work? My husband is an avid cyclist",
    "Are there any lagoons or beach areas?",
    "What schools are nearby? We need IB curriculum",
    "How is the developer? We've bought from Emaar before in Downtown",
    "What's the asking price for this villa?",
    "What's the remaining payment schedule?",
    "How much has been paid so far?",
    "Is the villa eligible for Golden Visa?",
    "We'd like to make an offer. AED 17,000,000",
]:
    test_msg("P7-Fatima", p, msg)

# PERSONA 8: Raj Kapoor
print("\n=== PERSONA 8: Raj Kapoor ===", flush=True)
p = "+971502222002"
for msg in [
    "How does this compare to Sobha developments?",
    "What's the ROI projection?",
    "What's the handover timeline?",
    "Can I see the floor plan?",
    "What's the service charge?",
    "Is there a penalty for late payment on the installments?",
    "What are the DLD registration fees?",
    "Do you have any apartments as well? I'm also looking for something smaller",
]:
    test_msg("P8-Raj", p, msg)

# PERSONA 9: Mike - Skeptical American
print("\n=== PERSONA 9: Mike ===", flush=True)
p = "+971502222003"
for msg in [
    "Is this an AI or a real person?",
    "What happens if Emaar goes bankrupt before completion?",
    "Can I get my money back if I don't want the unit anymore?",
    "Why is the resale price higher than the SPA price? Seems like a ripoff",
    "I've heard Dubai is in a property bubble. What do you think?",
    "What guarantees do I have that this will be delivered on time?",
    "Can you share the original SPA document?",
    "I'll offer 15 million",
    "Fine, 16.9 million",
]:
    test_msg("P9-Mike", p, msg)

# PERSONA 10: Russian-speaking buyer
print("\n=== PERSONA 10: Russian ===", flush=True)
p = "+971502222004"
for msg in [
    "\u0417\u0434\u0440\u0430\u0432\u0441\u0442\u0432\u0443\u0439\u0442\u0435, \u0440\u0430\u0441\u0441\u043a\u0430\u0436\u0438\u0442\u0435 \u043e \u0432\u0438\u043b\u043b\u0435",
    "\u041a\u0430\u043a\u0430\u044f \u043f\u043b\u043e\u0449\u0430\u0434\u044c \u0443\u0447\u0430\u0441\u0442\u043a\u0430?",
    "\u0421\u043a\u043e\u043b\u044c\u043a\u043e \u0441\u0442\u043e\u0438\u0442?",
    "\u041a\u043e\u0433\u0434\u0430 \u043f\u043b\u0430\u043d\u0438\u0440\u0443\u0435\u0442\u0441\u044f \u0441\u0434\u0430\u0447\u0430?",
    "\u041a\u0430\u043a\u0438\u0435 \u0448\u043a\u043e\u043b\u044b \u0440\u044f\u0434\u043e\u043c?",
]:
    test_msg("P10-Russian", p, msg)

# PERSONA 11: Hindi-speaking buyer
print("\n=== PERSONA 11: Hindi ===", flush=True)
p = "+971502222005"
for msg in [
    "\u0928\u092e\u0938\u094d\u0924\u0947, \u0907\u0938 \u0935\u093f\u0932\u093e \u0915\u0947 \u092c\u093e\u0930\u0947 \u092e\u0947\u0902 \u092c\u0924\u093e\u0907\u090f",
    "\u0915\u093f\u0930\u093e\u092f\u093e \u0915\u093f\u0924\u0928\u093e \u0906\u0924\u093e \u0939\u0948?",
    "\u0917\u094b\u0932\u094d\u0921\u0928 \u0935\u0940\u0938\u093e \u092e\u093f\u0932\u0947\u0917\u093e?",
]:
    test_msg("P11-Hindi", p, msg)

# PERSONA 12: Edge cases
print("\n=== PERSONA 12: Edge Cases ===", flush=True)
p = "+971502222006"
test_msg("P12-Edge", p, "Do you have any other properties available?")
test_msg("P12-Edge", p, "I'm looking for something under 7 million")
test_msg("P12-Edge", p, "What if I want a 2-bedroom apartment instead?")
test_msg("P12-Edge", p, "")
long_msg = "Hi, my name is Alexander and I'm a 45-year-old businessman from London. I've been living in Dubai for the past 8 years and I currently own two apartments in Downtown Dubai and one villa in Arabian Ranches. I'm looking to diversify my property portfolio and I'm particularly interested in off-plan developments because I believe the Dubai real estate market still has significant upside potential. My family includes my wife, three children aged 12, 8, and 5, and my mother-in-law who visits frequently from the UK. We need at least 4 bedrooms, a spacious garden, and preferably a community with good schools nearby. My budget is flexible but ideally between 15 and 20 million AED. Can you tell me everything about this property?"
test_msg("P12-Edge", p, long_msg)
test_msg("P12-Edge", p, "Can I speak to a human?")
test_msg("P12-Edge", p, "What's the weather like in Dubai?")
test_msg("P12-Edge", p, "LISTING:invalid-id Hello")

print(f"\n\nDONE. Total messages: {len(results)}", flush=True)
