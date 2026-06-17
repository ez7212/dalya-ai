from pydantic import BaseModel, Field
from typing import Optional
from datetime import date


class PaymentInstalment(BaseModel):
    instalment_number: int
    due_date: Optional[str] = None
    milestone: str  # e.g. "1st Instalment", "40% Construction"
    percentage: float
    amount_aed: float
    vat_amount_aed: float = 0.0
    amount_incl_vat_aed: float
    actually_paid: Optional[bool] = None  # explicit override: True=paid, False=unpaid, None=infer from due_date
    paid_date: Optional[date] = None      # date payment was confirmed received, if known


class Purchaser(BaseModel):
    name: str
    nationality: Optional[str] = None
    # NOTE: passport, emirates_id, phone, email deliberately excluded
    # We never store PII from SPAs — PDPL compliance


class SPAParseResult(BaseModel):
    # Core property identity
    project: str          # Community name e.g. "Sobha Seahaven", "The Oasis"
    sub_community: Optional[str] = None  # Tower/cluster/phase e.g. "Tower A", "Palace Villas Ostra"
    unit_number: str      # Villa or apartment number e.g. "2305", "2805"
    developer: str
    property_type: str  # Villa, Apartment, Townhouse, etc.
    property_use: Optional[str] = None  # Single Family, Commercial, etc.

    # Size
    bedrooms: Optional[int] = None
    bathrooms: Optional[int] = None
    bua_sqft: Optional[float] = None  # Built-up area
    plot_sqft: Optional[float] = None
    parking: Optional[str] = None

    # Financials
    purchase_price_aed: float
    vat_percent: float = 0.0
    purchase_price_incl_vat_aed: Optional[float] = None

    # Status
    property_status: Optional[str] = None  # Under Construction, Ready, etc.
    handover_condition: Optional[str] = None  # Finished, Shell, etc.
    estimated_completion_date: Optional[str] = None
    handover_date_description: Optional[str] = None

    # Payment
    payment_schedule: list[PaymentInstalment] = []
    total_paid_percent: Optional[float] = None  # derived: sum of past instalments
    noc_eligible: Optional[bool] = None  # derived from % paid vs developer threshold

    # Admin
    dld_registration_fees: Optional[str] = None
    plot_number: Optional[str] = None
    sales_order_number: Optional[str] = None

    # Purchaser info (name only, no PII)
    purchasers: list[Purchaser] = []

    # Parser metadata
    parse_confidence: float = Field(
        description="0-1 confidence score from parser", default=0.0
    )
    parse_notes: list[str] = Field(
        description="Any warnings or assumptions made during parsing", default=[]
    )
    raw_text_extracted: Optional[str] = Field(
        description="Raw text Claude extracted before structuring",
        default=None,
        exclude=True,  # Don't expose in API response
    )


class SPAParseResponse(BaseModel):
    success: bool
    listing_id: Optional[str] = None  # UUID assigned to this listing
    data: Optional[SPAParseResult] = None
    error: Optional[str] = None
