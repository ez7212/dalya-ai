"""
SPA Parser — Core AI Engine
Converts an uploaded SPA PDF into a structured property profile.

Strategy:
1. Convert PDF pages to images (handles scanned docs, mixed Arabic/English)
2. Send images to Claude with a detailed extraction prompt
3. Parse Claude's JSON response into our schema
4. Derive computed fields (% paid, NOC eligibility)
5. Return structured SPAParseResult

Claude model: claude-sonnet-4-20250514
Chosen for: best vision + structured output balance, cost-effective at scale
"""

import anthropic
import base64
import json
import logging
import re
import uuid
from pathlib import Path
from datetime import datetime, date
import fitz  # PyMuPDF — best PDF rendering library

from app.schemas.spa import SPAParseResult, SPAParseResponse, PaymentInstalment, Purchaser

logger = logging.getLogger(__name__)


# ── Extraction prompt ──────────────────────────────────────────────────────────
# This prompt is the core IP of the parser.
# Designed specifically for Emaar SPAs but handles other developers.
# Key design decisions:
#   - Explicit field list prevents Claude from inventing fields
#   - "null if not found" prevents hallucination of missing data
#   - PII fields explicitly excluded for PDPL compliance
#   - Payment schedule extracted as array for downstream calculation
#   - Confidence scoring helps us flag low-quality extractions for manual review

SPA_EXTRACTION_PROMPT = """You are an expert UAE real estate document parser specialising in Sales Purchase Agreements (SPAs) from Dubai developers like Emaar, Damac, Sobha, and Aldar.

Extract the following information from this SPA document image(s). Return ONLY a valid JSON object — no markdown, no explanation, no preamble.

IMPORTANT RULES:
- Return null for any field you cannot find or are uncertain about
- Do NOT extract or include passport numbers, Emirates IDs, phone numbers, or email addresses
- For purchaser names: extract name only
- Dates: use ISO format YYYY-MM-DD where possible, or descriptive string if milestone-based
- Numbers: return as numeric values (not strings), no currency symbols or commas
- Read digits carefully, character by character — do not guess or approximate reference numbers, sales order numbers, or unit numbers
- If multiple pages, treat as one document

Extract this exact JSON structure:

{
  "developer": "developer company name (e.g. Sobha Realty, Emaar Properties)",
  "project": "community/development name ONLY — no tower, cluster, or unit info (e.g. 'Sobha Seahaven', 'The Oasis', 'Damac Hills')",
  "sub_community": "tower, cluster, phase, or sub-development name if present (e.g. 'Tower A', 'Palace Villas Ostra', 'Santorini') — null if not applicable",
  "unit_number": "the numeric villa or apartment number only (e.g. 2805, 2305) — NOT the property type code, floor plan code, or project abbreviation. For Emaar SPAs this is typically a 4-digit number found next to 'Unit No.', 'Villa No.', 'Property No.', or 'Plot Number'. DO NOT extract the suffix from internal property codes like 'OD Palace Ostra-V-294' — use the Plot Number instead.",
  "property_type": "Villa / Apartment / Townhouse / etc",
  "property_use": "Single Family Residential Use / Commercial / etc",
  "bedrooms": null,
  "bathrooms": null,
  "bua_sqft": 0.0,
  "plot_sqft": 0.0,
  "parking": "description of parking",
  "purchase_price_aed": 0.0,
  "vat_percent": 0.0,
  "purchase_price_incl_vat_aed": 0.0,
  "property_status": "Under Construction / Ready / Completed",
  "handover_condition": "Finished / Shell and Core / etc",
  "estimated_completion_date": "YYYY-MM-DD or descriptive",
  "handover_date_description": "full handover clause text if complex",
  "dld_registration_fees": "who pays, any conditions",
  "plot_number": "plot/land number if shown",
  "sales_order_number": "sales order number if shown",
  "purchasers": [
    {
      "name": "full name only",
      "nationality": "nationality if shown"
    }
  ],
  "payment_schedule": [
    {
      "instalment_number": 1,
      "due_date": "YYYY-MM-DD or null if milestone-based",
      "milestone": "milestone description EXACTLY as written on the SPA — e.g. '1st Instalment', '4th Instalment', '20% Construction', 'On Handover'",
      "percentage": 10.0,
      "amount_aed": 0.0,
      "vat_amount_aed": 0.0,
      "amount_incl_vat_aed": 0.0
    }
  ],

  CRITICAL payment_schedule rules (read carefully — parsers frequently mis-align this table):
  - Extract EVERY row from the Schedule of Payments table EXACTLY as it appears — one JSON entry per row
  - Each visible row in the table has FOUR aligned cells: Instalment Date, Milestone, Payment (%), Amount (AED). These belong to ONE row — do NOT shift dates up or down relative to milestones.
  - The FIRST date in the Instalment Date column belongs to the FIRST milestone row (typically "1st Installment"). It is NOT a separate booking/down-payment row, even if the date seems early or the row appears slightly offset visually.
  - Count the rows in the milestone column. Count the rows in the date column. These counts MUST be equal. If they differ, you are mis-reading the table — look again.
  - Do NOT merge, combine, summarize, or drop rows. If the table has 9 rows, return 9 entries.
  - Do NOT rename milestones — use the exact text from the milestone column (e.g. "4th Installment" stays "4th Installment", NOT "20% Construction"). If a row has TWO pieces of text stacked (like "4th Installment" above "20% Construction"), that is TWO SEPARATE ROWS, not one row with two labels.
  - Do NOT add rows that don't exist in the document.
  - Each row's percentage and amount must match the document exactly.
  - VERIFY before returning: the sum of all percentages must equal 100%. If your sum is 90% or 110%, you have dropped, duplicated, or mis-aligned a row — re-examine the table and fix before returning.
  - Emaar "The Oasis / Palace Villas" SPAs typically have 9 payment rows: 1st–4th Installment (10% each) + 20%/40%/60%/80% Construction (10% each) + 100% Construction (20% on handover). If you see this pattern, all 9 rows should be present.
  "parse_confidence": 0.95,
  "parse_notes": [
    "any assumptions made, ambiguities found, or fields that needed interpretation"
  ]
}

For parse_confidence:
- 0.95-1.0: all key fields clearly found, clean document
- 0.80-0.94: most fields found, minor ambiguities
- 0.60-0.79: some fields missing or document quality issues
- Below 0.60: significant extraction problems, flag for manual review

Now extract from the provided document:"""


# ── NOC eligibility logic ──────────────────────────────────────────────────────
# Emaar typically requires 30-40% paid before issuing NOC for resale transfer
# This threshold varies by developer — we default to 40% for Emaar
EMAAR_NOC_THRESHOLD_PERCENT = 40.0

DEVELOPER_NOC_THRESHOLDS = {
    "emaar": 40.0,
    "damac": 30.0,
    "sobha": 40.0,
    "aldar": 30.0,
    "meraas": 40.0,
    "nakheel": 30.0,
}


def get_noc_threshold(developer: str) -> float:
    """Get NOC threshold for a developer. Default 40% if unknown."""
    if not developer:
        return 40.0
    dev_lower = developer.lower()
    for key, threshold in DEVELOPER_NOC_THRESHOLDS.items():
        if key in dev_lower:
            return threshold
    return 40.0


def calculate_percent_paid(
    payment_schedule: list[PaymentInstalment],
    reference_date: date = None,
) -> float:
    """
    Calculate percentage of purchase price paid to date.
    Uses today's date to determine which instalments have passed.
    Only counts instalments with a specific due_date in the past.
    Milestone-based instalments (no date) are not counted automatically.
    """
    if not payment_schedule:
        return 0.0

    if reference_date is None:
        reference_date = date.today()

    total_paid = 0.0
    for inst in payment_schedule:
        if inst.due_date:
            try:
                due = date.fromisoformat(inst.due_date)
                if due <= reference_date:
                    total_paid += inst.percentage
            except ValueError:
                # Date parsing failed — skip for auto calculation
                pass

    return round(total_paid, 2)


def derive_noc_eligibility(
    developer: str,
    percent_paid: float,
) -> bool:
    """
    Determine if property is eligible for NOC based on amount paid.
    Returns True if paid percentage meets or exceeds developer threshold.
    """
    threshold = get_noc_threshold(developer)
    return percent_paid >= threshold


def validate_spa_parse(parsed: SPAParseResult) -> list[str]:
    """Returns a list of warning strings. Empty list means clean parse."""
    warnings = []
    if parsed.bua_sqft is not None and parsed.bua_sqft >= 100 and parsed.bua_sqft % 100 == 0:
        warnings.append(
            f"BUA {parsed.bua_sqft:.0f} is suspiciously round — likely rounded by parser or hand-crafted fixture"
        )
    if parsed.plot_sqft is not None and parsed.plot_sqft >= 100 and parsed.plot_sqft % 100 == 0:
        warnings.append(
            f"Plot {parsed.plot_sqft:.0f} is suspiciously round — likely rounded by parser or hand-crafted fixture"
        )
    if parsed.purchase_price_aed and (parsed.purchase_price_aed < 500_000 or parsed.purchase_price_aed > 200_000_000):
        warnings.append(
            f"purchase_price_aed {parsed.purchase_price_aed:,.0f} outside plausible range"
        )
    sched = parsed.payment_schedule or []
    if sched:
        total = sum((i.percentage or 0.0) for i in sched)
        if abs(total - 100.0) > 0.5:
            warnings.append(f"payment_schedule percentages sum to {total:.1f}%, not 100%")
    if parsed.bedrooms is None and parsed.property_type in ("Villa", "Apartment", "Townhouse"):
        warnings.append(f"bedrooms is None for {parsed.property_type} — likely SPA-extraction gap; manually confirm before activating")
    return warnings


# ── PDF → images ───────────────────────────────────────────────────────────────

def pdf_to_base64_images(pdf_bytes: bytes, dpi: int = 72) -> list[str]:
    """
    Convert PDF pages to base64-encoded PNG images.
    DPI 72 is the sweet spot: good OCR quality, reasonable token cost.
    Higher DPI = better quality but more tokens = higher cost.
    For scanned/handwritten docs, consider 200 DPI.
    """
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    images = []

    for page_num in range(len(doc)):
        page = doc[page_num]
        # Matrix for DPI scaling (72 DPI is PyMuPDF default)
        mat = fitz.Matrix(dpi / 72, dpi / 72)
        pix = page.get_pixmap(matrix=mat, colorspace=fitz.csRGB)
        png_bytes = pix.tobytes("png")
        b64 = base64.standard_b64encode(png_bytes).decode("utf-8")
        images.append(b64)

    doc.close()
    return images


# ── Main parser ────────────────────────────────────────────────────────────────

class SPAParser:
    def __init__(self):
        self.client = anthropic.Anthropic()
        self.model = "claude-sonnet-4-6"

    @staticmethod
    def stable_listing_id(developer: str, project: str, unit_number: str) -> str:
        """
        Generate a deterministic listing ID from the natural key (developer + project + unit).
        Uploading the same SPA twice always produces the same ID, so save_listing()
        updates the existing row instead of creating a duplicate.
        """
        import hashlib
        key = f"{str(developer).lower().strip()}|{str(project).lower().strip()}|{str(unit_number).lower().strip()}"
        return hashlib.sha1(key.encode()).hexdigest()[:36]

    def _extract_text_from_pdf(self, pdf_bytes: bytes) -> str:
        """Extract selectable text from PDF using PyMuPDF. Instant, no API call."""
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        text = ""
        for page in doc:
            text += page.get_text("text") + "\n"
        doc.close()
        return text.strip()

    def _parse_from_text(self, text: str) -> SPAParseResponse:
        """Parse SPA from extracted text — much faster since no image tokens."""
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                messages=[{
                    "role": "user",
                    "content": f"The following is raw text extracted from a UAE Sale and Purchase Agreement (SPA) PDF document.\n\n---\n\n{text}\n\n---\n\n{SPA_EXTRACTION_PROMPT}",
                }],
            )
            return self._process_claude_response(response)
        except json.JSONDecodeError as e:
            return SPAParseResponse(success=False, error=f"Failed to parse JSON: {e}")
        except Exception as e:
            return SPAParseResponse(success=False, error=f"Parser error: {e}")

    # Maximum pages to send as images — SPA key data is in the first pages
    MAX_IMAGE_PAGES = 8

    def parse(self, pdf_bytes: bytes, filename: str = "spa.pdf") -> SPAParseResponse:
        """
        Main entry point. Takes raw PDF bytes, returns structured SPAParseResponse.

        Strategy:
        1. Try text extraction first (instant, no API cost for images)
        2. If text is rich enough (>500 chars), parse from text
        3. Otherwise fall back to image-based extraction (scanned PDFs)
        4. Cap image pages to MAX_IMAGE_PAGES to control latency
        """
        listing_id = None  # set after extraction

        try:
            # Step 1: Try text extraction first (free, instant)
            extracted_text = self._extract_text_from_pdf(pdf_bytes)

            if len(extracted_text) > 500:
                # Text-based extraction — typically 5-10s vs 30-60s for images
                result = self._parse_from_text(extracted_text)
                if result.success:
                    return result
                # If text parsing failed, fall through to image-based

            # Step 2: Fall back to image-based extraction
            images = pdf_to_base64_images(pdf_bytes)

            if not images:
                return SPAParseResponse(
                    success=False,
                    error="Could not extract any pages from PDF",
                )

            # Cap pages to reduce latency — SPA data is concentrated in first pages
            if len(images) > self.MAX_IMAGE_PAGES:
                images = images[:self.MAX_IMAGE_PAGES]

            # Step 3: Build Claude message with page images
            content = []

            for i, b64_img in enumerate(images):
                content.append({
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/png",
                        "data": b64_img,
                    },
                })
                content.append({
                    "type": "text",
                    "text": f"[Page {i + 1} of {len(images)}]",
                })

            content.append({
                "type": "text",
                "text": SPA_EXTRACTION_PROMPT,
            })

            # Step 4: Call Claude
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                messages=[{"role": "user", "content": content}],
            )

            return self._process_claude_response(response)

        except json.JSONDecodeError as e:
            return SPAParseResponse(
                success=False,
                error=f"Failed to parse Claude's JSON response: {str(e)}",
            )
        except Exception as e:
            return SPAParseResponse(
                success=False,
                error=f"Parser error: {str(e)}",
            )

    def _process_claude_response(self, response) -> SPAParseResponse:
        """Shared response processing for both text and image extraction paths."""
        raw_text = response.content[0].text.strip()

        # Strip markdown code fences
        json_text = re.sub(r"^```(?:json)?\n?", "", raw_text)
        json_text = re.sub(r"\n?```$", "", json_text)

        extracted = json.loads(json_text)

        # Map to schema
        payment_schedule = []
        for i, inst_data in enumerate(extracted.get("payment_schedule", [])):
            payment_schedule.append(PaymentInstalment(
                instalment_number=inst_data.get("instalment_number", i + 1),
                due_date=inst_data.get("due_date"),
                milestone=inst_data.get("milestone", f"Instalment {i + 1}"),
                percentage=float(inst_data.get("percentage") or 0),
                amount_aed=float(inst_data.get("amount_aed") or 0),
                vat_amount_aed=float(inst_data.get("vat_amount_aed") or 0),
                amount_incl_vat_aed=float(inst_data.get("amount_incl_vat_aed") or 0),
            ))

        purchasers = []
        for p in extracted.get("purchasers", []):
            purchasers.append(Purchaser(
                name=p.get("name", ""),
                nationality=p.get("nationality"),
            ))

        # Derive computed fields
        developer = extracted.get("developer", "")
        percent_paid = calculate_percent_paid(payment_schedule)
        noc_eligible = derive_noc_eligibility(developer, percent_paid)

        listing_id = self.stable_listing_id(
            developer=developer,
            project=extracted.get("project", ""),
            unit_number=extracted.get("unit_number", ""),
        )

        result = SPAParseResult(
            project=extracted.get("project", ""),
            sub_community=extracted.get("sub_community"),
            unit_number=str(extracted.get("unit_number", "")),
            developer=developer,
            property_type=extracted.get("property_type", ""),
            property_use=extracted.get("property_use"),
            bedrooms=extracted.get("bedrooms"),
            bathrooms=extracted.get("bathrooms"),
            bua_sqft=extracted.get("bua_sqft"),
            plot_sqft=extracted.get("plot_sqft"),
            parking=extracted.get("parking"),
            purchase_price_aed=float(extracted.get("purchase_price_aed") or 0),
            vat_percent=float(extracted.get("vat_percent") or 0),
            purchase_price_incl_vat_aed=extracted.get("purchase_price_incl_vat_aed"),
            property_status=extracted.get("property_status"),
            handover_condition=extracted.get("handover_condition"),
            estimated_completion_date=extracted.get("estimated_completion_date"),
            handover_date_description=extracted.get("handover_date_description"),
            dld_registration_fees=extracted.get("dld_registration_fees"),
            plot_number=extracted.get("plot_number"),
            sales_order_number=extracted.get("sales_order_number"),
            purchasers=purchasers,
            payment_schedule=payment_schedule,
            total_paid_percent=percent_paid,
            noc_eligible=noc_eligible,
            parse_confidence=float(extracted.get("parse_confidence", 0.0)),
            parse_notes=extracted.get("parse_notes", []),
            raw_text_extracted=raw_text,
        )

        # Auto-fill bedrooms/bathrooms if not in the document
        if result.bedrooms is None or result.bathrooms is None:
            from app.core.bedroom_lookup import lookup_bedrooms_bathrooms
            try:
                lookup = lookup_bedrooms_bathrooms(
                    project=result.project,
                    sub_community=result.sub_community,
                    developer=result.developer,
                    property_type=result.property_type,
                    bua_sqft=result.bua_sqft,
                    unit_number=result.unit_number,
                )
                if lookup["bedrooms"] is not None and result.bedrooms is None:
                    result.bedrooms = lookup["bedrooms"]
                if lookup["bathrooms"] is not None and result.bathrooms is None:
                    result.bathrooms = lookup["bathrooms"]
            except Exception:
                pass  # Non-critical — listing still works without bedroom count

        # Validate the parsed result and log any warnings (non-blocking)
        parse_warnings = validate_spa_parse(result)
        for w in parse_warnings:
            logger.warning("SPA parse validation: %s (listing_id=%s)", w, listing_id)

        return SPAParseResponse(
            success=True,
            listing_id=listing_id,
            data=result,
        )
