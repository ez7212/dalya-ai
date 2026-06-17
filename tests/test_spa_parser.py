"""
Tests for the SPA parser.

Run with: pytest tests/ -v

For integration tests (calls Claude API — costs tokens):
  pytest tests/ -v -m integration

For unit tests only (free, no API calls):
  pytest tests/ -v -m "not integration"
"""

import pytest
import json
from unittest.mock import patch, MagicMock
from datetime import date

from app.core.spa_parser import (
    SPAParser,
    calculate_percent_paid,
    derive_noc_eligibility,
    get_noc_threshold,
    pdf_to_base64_images,
)
from app.schemas.spa import PaymentInstalment


# ── Unit tests (no API calls) ──────────────────────────────────────────────────

class TestPercentPaidCalculation:
    """Test the payment calculation logic independently of Claude."""

    def _make_instalment(self, due_date, percentage, amount=100000):
        return PaymentInstalment(
            instalment_number=1,
            due_date=due_date,
            milestone="Test",
            percentage=percentage,
            amount_aed=amount,
            vat_amount_aed=0,
            amount_incl_vat_aed=amount,
        )

    def test_single_past_instalment(self):
        schedule = [self._make_instalment("2025-01-01", 10.0)]
        result = calculate_percent_paid(schedule, reference_date=date(2026, 1, 1))
        assert result == 10.0

    def test_future_instalment_not_counted(self):
        schedule = [self._make_instalment("2027-01-01", 10.0)]
        result = calculate_percent_paid(schedule, reference_date=date(2026, 1, 1))
        assert result == 0.0

    def test_multiple_instalments_partial(self):
        schedule = [
            self._make_instalment("2025-01-01", 10.0),
            self._make_instalment("2025-06-01", 10.0),
            self._make_instalment("2026-06-01", 10.0),  # future
            self._make_instalment("2027-01-01", 20.0),  # future
        ]
        result = calculate_percent_paid(schedule, reference_date=date(2026, 1, 1))
        assert result == 20.0

    def test_milestone_based_no_date(self):
        """Milestone-based instalments with no date should not be auto-counted."""
        schedule = [
            PaymentInstalment(
                instalment_number=1,
                due_date=None,
                milestone="On handover",
                percentage=20.0,
                amount_aed=3000000,
                vat_amount_aed=0,
                amount_incl_vat_aed=3000000,
            )
        ]
        result = calculate_percent_paid(schedule, reference_date=date(2026, 1, 1))
        assert result == 0.0

    def test_empty_schedule(self):
        assert calculate_percent_paid([]) == 0.0

    def test_oasis_spa_schedule(self):
        """
        Test against the real Palace Oasis SPA payment schedule from the uploaded doc.
        10% on 1 Aug 2025 — first instalment.
        As of March 2026, only 2 installments have passed. 
        """
        schedule = [
            self._make_instalment("2025-08-01", 10.0),   # past ✓
            self._make_instalment("2026-01-01", 10.0),   # past ✓
            self._make_instalment("2026-07-01", 10.0),   # future
            self._make_instalment("2027-04-03", 10.0),   # future
            self._make_instalment("2027-12-16", 10.0),   # future
            self._make_instalment("2028-05-16", 10.0),   # future
            self._make_instalment("2028-12-16", 10.0),   # future
            self._make_instalment("2029-09-30", 20.0),   # future
        ]
        result = calculate_percent_paid(schedule, reference_date=date(2026, 3, 26))
        assert result == 20.0


class TestNOCEligibility:
    def test_emaar_below_threshold(self):
        assert derive_noc_eligibility("Emaar Development PJSC", 20.0) is False

    def test_emaar_at_threshold(self):
        assert derive_noc_eligibility("Emaar Development PJSC", 40.0) is True

    def test_emaar_above_threshold(self):
        assert derive_noc_eligibility("Emaar Development PJSC", 60.0) is True

    def test_damac_lower_threshold(self):
        assert derive_noc_eligibility("DAMAC Properties", 30.0) is True

    def test_unknown_developer_defaults_to_40(self):
        threshold = get_noc_threshold("Unknown Developer LLC")
        assert threshold == 40.0

    def test_oasis_unit_current_eligibility(self):
        """
        Palace Oasis unit with 20% paid as of March 2026.
        Emaar requires 40% — should NOT be NOC eligible yet.
        """
        assert derive_noc_eligibility("Emaar Development PJSC", 20.0) is False


class TestSPAParserMocked:
    """Test parser logic with mocked Claude responses — no API cost."""

    MOCK_CLAUDE_RESPONSE = json.dumps({
        "project": "The Oasis – Palace Villas – Ostra",
        "unit_number": "OD Palace Ostra-V-294",
        "developer": "Emaar Development PJSC",
        "property_type": "Villa",
        "property_use": "Single Family Residential Use",
        "bua_sqft": 8048,
        "plot_sqft": 8310,
        "parking": "Parking within the Property",
        "purchase_price_aed": 15173230,
        "vat_percent": 0.0,
        "purchase_price_incl_vat_aed": 15173230,
        "property_status": "Under Construction",
        "handover_condition": "Finished",
        "estimated_completion_date": "2029-09-30",
        "handover_date_description": "Upon completion of construction and receipt of 100% purchase price",
        "dld_registration_fees": "Fully Payable by the Purchaser",
        "plot_number": "2805",
        "sales_order_number": "155053",
        "purchasers": [
            {"name": "David Diyang Zhu", "nationality": "Malta"},
            {"name": "Wenxin Xu", "nationality": "China"},
        ],
        "payment_schedule": [
            {
                "instalment_number": 1, "due_date": "2025-08-01",
                "milestone": "1st Instalment", "percentage": 10.0,
                "amount_aed": 1517323, "vat_amount_aed": 0, "amount_incl_vat_aed": 1517323
            },
            {
                "instalment_number": 2, "due_date": "2026-01-01",
                "milestone": "2nd Instalment", "percentage": 10.0,
                "amount_aed": 1517323, "vat_amount_aed": 0, "amount_incl_vat_aed": 1517323
            },
            {
                "instalment_number": 3, "due_date": "2026-07-01",
                "milestone": "3rd Instalment", "percentage": 10.0,
                "amount_aed": 1517323, "vat_amount_aed": 0, "amount_incl_vat_aed": 1517323
            },
            {
                "instalment_number": 4, "due_date": "2027-04-03",
                "milestone": "20% Construction", "percentage": 10.0,
                "amount_aed": 1517323, "vat_amount_aed": 0, "amount_incl_vat_aed": 1517323
            },
            {
                "instalment_number": 5, "due_date": "2027-12-16",
                "milestone": "40% Construction", "percentage": 10.0,
                "amount_aed": 1517323, "vat_amount_aed": 0, "amount_incl_vat_aed": 1517323
            },
            {
                "instalment_number": 6, "due_date": "2028-05-16",
                "milestone": "60% Construction", "percentage": 10.0,
                "amount_aed": 1517323, "vat_amount_aed": 0, "amount_incl_vat_aed": 1517323
            },
            {
                "instalment_number": 7, "due_date": "2028-12-16",
                "milestone": "80% Construction", "percentage": 10.0,
                "amount_aed": 1517323, "vat_amount_aed": 0, "amount_incl_vat_aed": 1517323
            },
            {
                "instalment_number": 8, "due_date": "2029-09-30",
                "milestone": "100% Construction / Handover", "percentage": 20.0,
                "amount_aed": 3034646, "vat_amount_aed": 0, "amount_incl_vat_aed": 3034646
            },
        ],
        "parse_confidence": 0.97,
        "parse_notes": ["VAT is 0% — residential property, correctly extracted"]
    })

    def _get_dummy_pdf(self) -> bytes:
        """Create a minimal valid PDF for testing."""
        import fitz
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((50, 100), "TEST SPA DOCUMENT")
        return doc.tobytes()

    @patch("app.core.spa_parser.anthropic.Anthropic")
    def test_parse_returns_correct_structure(self, mock_anthropic_class):
        mock_client = MagicMock()
        mock_anthropic_class.return_value = mock_client
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=self.MOCK_CLAUDE_RESPONSE)]
        mock_client.messages.create.return_value = mock_response

        parser = SPAParser()
        result = parser.parse(self._get_dummy_pdf())

        assert result.success is True
        assert result.listing_id is not None
        assert result.data.project == "The Oasis – Palace Villas – Ostra"
        assert result.data.unit_number == "OD Palace Ostra-V-294"
        assert result.data.purchase_price_aed == 15173230
        assert result.data.bua_sqft == 8048
        assert len(result.data.payment_schedule) == 8
        assert result.data.parse_confidence == 0.97

    @patch("app.core.spa_parser.anthropic.Anthropic")
    def test_pii_not_exposed(self, mock_anthropic_class):
        """Ensure passport numbers and Emirates IDs never appear in output."""
        mock_client = MagicMock()
        mock_anthropic_class.return_value = mock_client
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=self.MOCK_CLAUDE_RESPONSE)]
        mock_client.messages.create.return_value = mock_response

        parser = SPAParser()
        result = parser.parse(self._get_dummy_pdf())
        result_dict = result.model_dump()
        result_str = json.dumps(result_dict)

        # These PII values from the real SPA should never appear
        assert "MT208282" not in result_str      # passport number
        assert "EJ4344666" not in result_str     # passport number
        assert "784-1989" not in result_str      # Emirates ID format
        assert "554451336" not in result_str     # phone number

    @patch("app.core.spa_parser.anthropic.Anthropic")
    def test_noc_eligibility_derived(self, mock_anthropic_class):
        """20% paid on Emaar property → not NOC eligible (threshold: 40%)."""
        mock_client = MagicMock()
        mock_anthropic_class.return_value = mock_client
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=self.MOCK_CLAUDE_RESPONSE)]
        mock_client.messages.create.return_value = mock_response

        parser = SPAParser()
        result = parser.parse(self._get_dummy_pdf())

        # As of March 2026, 2 instalments paid = 20% — below 40% Emaar threshold
        assert result.data.noc_eligible is False

    @patch("app.core.spa_parser.anthropic.Anthropic")
    def test_handles_invalid_json_gracefully(self, mock_anthropic_class):
        mock_client = MagicMock()
        mock_anthropic_class.return_value = mock_client
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="This is not JSON at all")]
        mock_client.messages.create.return_value = mock_response

        parser = SPAParser()
        result = parser.parse(self._get_dummy_pdf())

        assert result.success is False
        assert "JSON" in result.error

    @patch("app.core.spa_parser.anthropic.Anthropic")
    def test_purchaser_names_retained(self, mock_anthropic_class):
        """Names (not PII) should be kept for seller verification."""
        mock_client = MagicMock()
        mock_anthropic_class.return_value = mock_client
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=self.MOCK_CLAUDE_RESPONSE)]
        mock_client.messages.create.return_value = mock_response

        parser = SPAParser()
        result = parser.parse(self._get_dummy_pdf())

        names = [p.name for p in result.data.purchasers]
        assert "David Diyang Zhu" in names
        assert "Wenxin Xu" in names


# ── Integration test (calls real Claude API) ───────────────────────────────────

@pytest.mark.integration
class TestSPAParserIntegration:
    """
    Real API call tests. Run with: pytest -m integration
    Requires ANTHROPIC_API_KEY in environment.
    Will consume tokens.
    """

    def test_parse_real_spa_image(self):
        """
        Test parsing the actual Palace Oasis SPA uploaded to this conversation.
        Requires the SPA file to be available at the path below.
        """
        import os
        spa_path = "/mnt/user-data/uploads/1774496480369_image.png"

        if not os.path.exists(spa_path):
            pytest.skip("Real SPA file not available in this environment")

        with open(spa_path, "rb") as f:
            content = f.read()

        parser = SPAParser()

        # Convert image to PDF for parser
        import fitz
        img_doc = fitz.open(stream=content, filetype="png")
        doc = fitz.open()
        doc.insert_pdf(img_doc)
        pdf_bytes = doc.tobytes()

        result = parser.parse(pdf_bytes, "palace_oasis_spa.pdf")

        assert result.success is True
        assert result.data is not None
        assert result.data.parse_confidence >= 0.7
        assert "Oasis" in result.data.project or "Palace" in result.data.project
        assert result.data.purchase_price_aed > 0
        assert len(result.data.payment_schedule) > 0

        print("\n=== Integration Test Result ===")
        print(f"Project: {result.data.project}")
        print(f"Unit: {result.data.unit_number}")
        print(f"Price: AED {result.data.purchase_price_aed:,.0f}")
        print(f"BUA: {result.data.bua_sqft} sqft")
        print(f"% Paid: {result.data.total_paid_percent}%")
        print(f"NOC Eligible: {result.data.noc_eligible}")
        print(f"Confidence: {result.data.parse_confidence}")
        print(f"Notes: {result.data.parse_notes}")
        print(f"Instalments: {len(result.data.payment_schedule)}")
