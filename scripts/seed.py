#!/usr/bin/env python3
"""
Seed script — sets up a complete test environment against a running Dalya server.

Usage:
    python scripts/seed.py                          # defaults to http://localhost:8000
    BASE_URL=http://localhost:8080 python scripts/seed.py

Steps:
    1. POST /api/v1/parse-spa with a minimal test PDF
    2. POST /api/v1/listings/{id}/activate with seller pricing
    3. POST /api/v1/whatsapp/send-test x3 — payment question, low offer, high offer
    4. Print summary
"""

import io
import os
import sys
import requests

BASE_URL = os.getenv("BASE_URL", "http://localhost:8000").rstrip("/")


def make_test_pdf() -> bytes:
    """Create a minimal PDF that looks like an SPA for the parser."""
    try:
        import fitz
    except ImportError:
        sys.exit("PyMuPDF (fitz) is required. Install with: pip install PyMuPDF")

    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 80), "SALE AND PURCHASE AGREEMENT", fontsize=16)
    page.insert_text((50, 120), "Developer: Emaar Properties PJSC")
    page.insert_text((50, 140), "Project: Creek Harbour Towers")
    page.insert_text((50, 160), "Unit Number: CHT-1204")
    page.insert_text((50, 180), "Property Type: Apartment")
    page.insert_text((50, 200), "BUA: 1,250 sqft")
    page.insert_text((50, 220), "Purchase Price: AED 2,350,000")
    page.insert_text((50, 260), "Payment Schedule:")
    page.insert_text((50, 280), "1. Down Payment — 10% — AED 235,000 — Due: 2025-03-01")
    page.insert_text((50, 300), "2. 2nd Instalment — 10% — AED 235,000 — Due: 2025-09-01")
    page.insert_text((50, 320), "3. 3rd Instalment — 10% — AED 235,000 — Due: 2026-03-01")
    page.insert_text((50, 340), "4. 4th Instalment — 10% — AED 235,000 — Due: 2026-09-01")
    page.insert_text((50, 360), "5. On Handover — 60% — AED 1,410,000 — Due: 2028-06-30")
    page.insert_text((50, 400), "Purchaser: Test Buyer")
    page.insert_text((50, 420), "Nationality: UAE")
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def step(n: int, label: str):
    print(f"\n{'='*60}")
    print(f"  Step {n}: {label}")
    print(f"{'='*60}")


def main():
    print(f"Dalya seed script — targeting {BASE_URL}")

    # ── Step 1: Parse SPA ─────────────────────────────────────────────────────
    step(1, "Upload test SPA")
    pdf_bytes = make_test_pdf()
    buf = io.BytesIO(pdf_bytes)
    buf.name = "test_spa.pdf"

    resp = requests.post(
        f"{BASE_URL}/api/v1/parse-spa",
        files={"file": ("test_spa.pdf", buf, "application/pdf")},
        timeout=60,
    )
    if resp.status_code not in (200, 422):
        print(f"  FAILED ({resp.status_code}): {resp.text}")
        sys.exit(1)

    parse_result = resp.json()
    listing_id = parse_result.get("listing_id")
    already_exists = parse_result.get("already_exists", False)

    if not listing_id:
        print(f"  FAILED: No listing_id returned. Response: {parse_result}")
        sys.exit(1)

    status = "already existed" if already_exists else "newly created"
    print(f"  Listing ID: {listing_id} ({status})")
    if parse_result.get("data"):
        data = parse_result["data"]
        print(f"  Project:    {data.get('project', '?')}")
        print(f"  Unit:       {data.get('unit_number', '?')}")
        print(f"  Price:      AED {data.get('purchase_price_aed', 0):,.0f}")
        print(f"  Confidence: {data.get('parse_confidence', '?')}")

    # ── Step 2: Activate listing ──────────────────────────────────────────────
    step(2, "Activate listing with seller pricing")
    resp = requests.post(
        f"{BASE_URL}/api/v1/listings/{listing_id}/activate",
        params={
            "seller_asking_price": 2_000_000,
            "negotiation_threshold_aed": 1_800_000,
        },
        timeout=30,
    )
    if resp.status_code != 200:
        print(f"  FAILED ({resp.status_code}): {resp.text}")
        sys.exit(1)

    activate = resp.json()
    wa_link = activate.get("whatsapp_link", "")
    print(f"  Activated:     {activate.get('success')}")
    print(f"  WhatsApp link: {wa_link}")

    # ── Step 3: Simulate buyer conversations ──────────────────────────────────
    step(3, "Simulate buyer messages")
    test_messages = [
        ("What are the payment milestones?", "Payment inquiry"),
        ("I want to offer AED 1,700,000", "Below-threshold offer"),
        ("I want to offer AED 1,900,000", "Above-threshold offer"),
    ]

    buyer_phone = "+971500000099"
    for message, label in test_messages:
        print(f"\n  --- {label} ---")
        print(f"  Buyer: {message}")
        resp = requests.post(
            f"{BASE_URL}/api/v1/whatsapp/send-test",
            params={
                "listing_id": listing_id,
                "buyer_phone": buyer_phone,
                "message": message,
            },
            timeout=60,
        )
        if resp.status_code != 200:
            print(f"  FAILED ({resp.status_code}): {resp.text}")
            continue

        result = resp.json()
        bot_reply = result.get("bot_response", "")
        escalated = result.get("escalation_triggered", False)
        # Truncate long replies for readability
        if len(bot_reply) > 300:
            bot_reply = bot_reply[:300] + "..."
        print(f"  Dalya: {bot_reply}")
        if escalated:
            print(f"  ** ESCALATION TRIGGERED **")

    # ── Summary ───────────────────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print(f"  SEED COMPLETE")
    print(f"{'='*60}")
    print(f"  Listing ID:    {listing_id}")
    print(f"  WhatsApp link: {wa_link}")
    print(f"  Dashboard:     {BASE_URL}/api/v1/listings/{listing_id}/stats")
    print(f"  Portal links:  {BASE_URL}/api/v1/listings/{listing_id}/portal-links")
    print()


if __name__ == "__main__":
    main()
