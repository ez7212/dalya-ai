from dotenv import load_dotenv
load_dotenv()

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse

from app.core.auth import CurrentUser, get_current_user
from app.core.runtime_config import debug_routes_enabled
from app.core.spa_parser import SPAParser
from app.schemas.spa import SPAParseResponse

router = APIRouter()
parser = SPAParser()

ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/png",
    "image/jpg",
}
MAX_FILE_SIZE_MB = 20


@router.post("/parse-spa", response_model=SPAParseResponse)
async def parse_spa(
    file: UploadFile = File(...),
    user: CurrentUser = Depends(get_current_user),
):
    """
    Upload a Sales Purchase Agreement (PDF or image).
    Returns a structured property profile extracted by AI.

    - Accepts PDF (multi-page), JPEG, PNG
    - Max file size: 20MB
    - PII (passport, Emirates ID, phone, email) is deliberately excluded from response
    - Returns parse_confidence score — flag anything below 0.7 for manual review
    """
    # Validate content type
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {file.content_type}. Accepted: PDF, JPEG, PNG",
        )

    # Read and size-check
    content = await file.read()
    size_mb = len(content) / (1024 * 1024)

    if size_mb > MAX_FILE_SIZE_MB:
        raise HTTPException(
            status_code=413,
            detail=f"File too large: {size_mb:.1f}MB. Maximum: {MAX_FILE_SIZE_MB}MB",
        )

    # Handle image uploads — wrap in minimal PDF or pass as image
    if file.content_type in {"image/jpeg", "image/png", "image/jpg"}:
        result = await _parse_image(content, file.content_type, file.filename)
    else:
        result = parser.parse(content, file.filename or "spa.pdf")

    if not result.success:
        raise HTTPException(status_code=422, detail=result.error)

    # Flag low-confidence parses in response headers
    headers = {}
    if result.data and result.data.parse_confidence < 0.7:
        headers["X-Parse-Warning"] = "low-confidence-extraction-manual-review-recommended"

    # Duplicate detection: if stable ID already exists, return existing data without overwriting
    if result.success and result.data and result.listing_id:
        from app.db.session import SessionLocal
        from app.db import crud
        with SessionLocal() as db:
            existing = crud.get_listing(db, result.listing_id)
            if existing:
                return JSONResponse(
                    content={
                        **result.model_dump(exclude_none=False),
                        "already_exists": True,
                        "message": "This SPA has already been uploaded. Existing listing returned — no changes made.",
                    },
                    headers=headers,
                )
            crud.save_listing(db, listing_id=result.listing_id, spa=result.data)

    return JSONResponse(
        content=result.model_dump(exclude_none=False),
        headers=headers,
    )


async def _parse_image(content: bytes, content_type: str, filename: str) -> SPAParseResponse:
    """
    Handle image uploads — resize to under 5MB then send directly to Claude.
    """
    try:
        return await _parse_image_inner(content, content_type, filename)
    except Exception as e:
        return SPAParseResponse(
            success=False,
            listing_id=None,
            data=None,
            error=f"Failed to parse image: {e}",
        )


async def _parse_image_inner(content: bytes, content_type: str, filename: str) -> SPAParseResponse:
    from PIL import Image
    import io

    # Open and resize image until under 5MB
    img = Image.open(io.BytesIO(content))
    
    # Convert to RGB if needed (removes alpha channel)
    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")

    quality = 85
    scale = 1.0
    img_bytes = content

    while len(img_bytes) > 4 * 1024 * 1024:  # target 4MB to be safe
        scale *= 0.75
        new_size = (int(img.width * scale), int(img.height * scale))
        resized = img.resize(new_size, Image.LANCZOS)
        buf = io.BytesIO()
        resized.save(buf, format="JPEG", quality=quality)
        img_bytes = buf.getvalue()

    # Send directly as JPEG — no PDF conversion needed
    import base64
    b64 = base64.standard_b64encode(img_bytes).decode("utf-8")

    import anthropic
    client = anthropic.Anthropic()

    from app.core.spa_parser import SPA_EXTRACTION_PROMPT
    import json, re
    from app.schemas.spa import SPAParseResponse, SPAParseResult, PaymentInstalment, Purchaser
    from app.core.spa_parser import calculate_percent_paid, derive_noc_eligibility, SPAParser as _SPAParser

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/jpeg",
                        "data": b64,
                    }
                },
                {
                    "type": "text",
                    "text": SPA_EXTRACTION_PROMPT,
                }
            ]
        }]
    )

    raw_text = response.content[0].text.strip()
    json_text = re.sub(r"^```(?:json)?\n?", "", raw_text)
    json_text = re.sub(r"\n?```$", "", json_text)
    extracted = json.loads(json_text)

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

    developer = extracted.get("developer") or "Unknown"
    project = extracted.get("project") or "Unknown"
    unit_number = str(extracted.get("unit_number") or "Unknown")
    percent_paid = calculate_percent_paid(payment_schedule)
    listing_id = _SPAParser.stable_listing_id(
        developer=developer,
        project=project,
        unit_number=unit_number,
    )

    result = SPAParseResult(
        project=extracted.get("project") or "Unknown",
        sub_community=extracted.get("sub_community"),
        unit_number=str(extracted.get("unit_number") or "Unknown"),
        developer=developer or "Unknown",
        property_type=extracted.get("property_type") or "Residential",
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
        noc_eligible=derive_noc_eligibility(developer, percent_paid),
        parse_confidence=float(extracted.get("parse_confidence", 0.0)),
        parse_notes=extracted.get("parse_notes", []),
    )

    return SPAParseResponse(
        success=True,
        listing_id=listing_id,
        data=result,
    )


@router.get("/parse-spa/{listing_id}")
async def get_listing(listing_id: str):
    """Retrieve a previously parsed listing by ID."""
    if not debug_routes_enabled():
        raise HTTPException(status_code=404, detail="Listing not found.")

    from app.db.session import SessionLocal
    from app.db import crud
    with SessionLocal() as db:
        row = crud.get_listing(db, listing_id)
    if not row:
        raise HTTPException(status_code=404, detail="Listing not found.")
    return {"listing_id": listing_id, "data": row.spa_data}
