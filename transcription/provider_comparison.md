# Transcription Provider Comparison

`DAL-5` requires a quality bake-off before fully committing to Speechmatics.

## Status

Planned. Awaiting 20-30 consented Dubai real estate voice notes from Luqman's chats and agent dictations.

## Providers

| Provider | Role | Configuration |
|---|---|---|
| Speechmatics | Default candidate | English batch transcription, `additional_vocab` from `transcription/dictionary.yaml` |
| AssemblyAI Universal-3 Pro | Fallback candidate | Pre-recorded transcription, `keyterms_prompt` from `transcription/dictionary.yaml` |

## Evaluation Set

Use consented samples representing:

- Indian, Pakistani, Filipino, Arabic, Russian, Gulf, European, and Western expat-accented English.
- Quiet indoor recordings and noisy WhatsApp-style recordings.
- Dubai real estate terms, developer names, project names, and brokerage/legal terms.
- Price-talk variants including implicit-unit numbers.

## Metrics

| Metric | Speechmatics | AssemblyAI Universal-3 Pro | Notes |
|---|---:|---:|---|
| Overall WER | TBD | TBD | Manual reference transcript required |
| Real estate terminology accuracy | TBD | TBD | Count exact developer/project/legal-term matches |
| Number recognition accuracy | TBD | TBD | Pay special attention to AED amounts and shorthand |
| Accent robustness | TBD | TBD | Score by accent group and noise level |
| Latency | TBD | TBD | Include upload, processing, and polling |
| Cost per audio hour | TBD | TBD | Include vocabulary/keyterms surcharge where applicable |

## Decision Log

No final provider decision yet. Speechmatics remains default because of expected accent coverage fit, but this file should be updated with measured results before production volume is routed through one provider by default.
