# P1-2 Fresh Parse Verification — SSH-A2305

**Date:** 2026-04-27  
**File:** `SPA - SEA HAVEN - SSH-A2305.pdf`  
**listing_id:** `991f0c8908f9dfc6d97010779db79a6a45b8`

## Parse Output (key fields)

| Field | Value |
|---|---|
| parse_confidence | 0.93 |
| bedrooms | 2 (resolved via bedroom_lookup — not in SPA text) |
| bathrooms | 2 (resolved via bedroom_lookup — not in SPA text) |
| bua_sqft | 1,474.77 sq.ft |
| plot_sqft | 0.0 (N/A — apartment) |
| purchase_price_aed | AED 5,751,603 |
| payment_schedule entries | 6 |
| payment_schedule sum | 100.0% |
| total_paid_percent (stored) | 50.0% |

## validate_spa_parse Warnings

No warnings fired. Bedrooms were None in the raw SPA text but resolved to 2 by `bedroom_lookup` before `validate_spa_parse` ran. The new bedrooms-None warning (added in spa_parser.py) is therefore not triggered — correct behavior, since the lookup succeeded. The warning will fire only when the lookup also returns None, which is the intended gap-detection case.

parse_notes confirm: "Bedrooms and bathrooms not specified in the extracted document text" — the lookup filled the gap silently.

## compute_paid_to_date Output

```json
{
  "paid_pct": 50.0,
  "remaining_pct": 50.0,
  "needs_verification": true
}
```

Instalments 1–4 (Booking + First through Third, covering 50%) have due dates in the past (pre-2026-04-27). The Fourth Installment is due 2026-06-09 (future) and the Final Installment (40%) is milestone-based with no date, so both are excluded from the auto-calculation. `needs_verification: true` is expected because the Final Installment is undated. The 50% figure is accurate.

## Conclusion

P1-2 is fully verified. The end-to-end parse path (PDF → text extraction → Claude → schema → bedroom_lookup → validate_spa_parse → compute_paid_to_date) works correctly. One gap to monitor: when bedroom_lookup resolves successfully, the new bedrooms-None warning in validate_spa_parse will not fire — the warning is only reachable if lookup itself returns None, which requires a genuinely unknown unit. This is the correct behavior but means gap detection relies on the lookup coverage being complete.
