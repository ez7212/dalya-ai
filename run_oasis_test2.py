import requests
import json
import sys

LISTING_ID = "7eb2b37b95468b1856d907113ad4c09c36be"
BASE_URL = "http://localhost:8000/api/v1/whatsapp/send-test"
results = []

def ask(listing_id, phone, message):
    r = requests.post(BASE_URL, params={'listing_id': listing_id, 'buyer_phone': phone, 'message': message}, timeout=180)
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
    sys.stdout.write(f"[{persona}] Q: {q_display}\n")
    sys.stdout.write(f"  A: {str(resp)[:300]}\n")
    sys.stdout.write(f"  Esc: {esc_triggered} | {esc_detail}\n---\n")
    sys.stdout.flush()
    with open('/Users/eric/dalya-ai/test_oasis_results2.json', 'w') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    return result

# Use fresh phone numbers with 9xx prefix to avoid conversation history buildup
# PERSONA 7: Fatima Al Thani
sys.stdout.write("=== PERSONA 7: Fatima Al Thani ===\n"); sys.stdout.flush()
p = "+971509222001"
for msg in [
    "Good morning, we're looking at this villa. How big is it?",
    "What's the plot size?",
    "Tell me about the community — we have three children",
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
sys.stdout.write("\n=== PERSONA 8: Raj Kapoor ===\n"); sys.stdout.flush()
p = "+971509222002"
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

# PERSONA 9: Mike
sys.stdout.write("\n=== PERSONA 9: Mike ===\n"); sys.stdout.flush()
p = "+971509222003"
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

# PERSONA 10: Russian
sys.stdout.write("\n=== PERSONA 10: Russian ===\n"); sys.stdout.flush()
p = "+971509222004"
for msg in [
    "Здравствуйте, расскажите о вилле",
    "Какая площадь участка?",
    "Сколько стоит?",
    "Когда планируется сдача?",
    "Какие школы рядом?",
]:
    test_msg("P10-Russian", p, msg)

# PERSONA 11: Hindi
sys.stdout.write("\n=== PERSONA 11: Hindi ===\n"); sys.stdout.flush()
p = "+971509222005"
for msg in [
    "नमस्ते, इस विला के बारे में बताइए",
    "किराया कितना आता है?",
    "गोल्डन वीसा मिलेगा?",
]:
    test_msg("P11-Hindi", p, msg)

# PERSONA 12: Edge cases
sys.stdout.write("\n=== PERSONA 12: Edge Cases ===\n"); sys.stdout.flush()
p = "+971509222006"
test_msg("P12-Edge", p, "Do you have any other properties available?")
test_msg("P12-Edge", p, "I'm looking for something under 7 million")
test_msg("P12-Edge", p, "What if I want a 2-bedroom apartment instead?")
test_msg("P12-Edge", p, "")
long_msg = "Hi, my name is Alexander and I'm a 45-year-old businessman from London. I've been living in Dubai for the past 8 years and I currently own two apartments in Downtown Dubai and one villa in Arabian Ranches. I'm looking to diversify my property portfolio and I'm particularly interested in off-plan developments because I believe the Dubai real estate market still has significant upside potential. My family includes my wife, three children aged 12, 8, and 5, and my mother-in-law who visits frequently from the UK. We need at least 4 bedrooms, a spacious garden, and preferably a community with good schools nearby. My budget is flexible but ideally between 15 and 20 million AED. Can you tell me everything about this property?"
test_msg("P12-Edge", p, long_msg)
test_msg("P12-Edge", p, "Can I speak to a human?")
test_msg("P12-Edge", p, "What's the weather like in Dubai?")
test_msg("P12-Edge", p, "LISTING:invalid-id Hello")

sys.stdout.write(f"\n\nDONE. Total messages: {len(results)}\n"); sys.stdout.flush()
