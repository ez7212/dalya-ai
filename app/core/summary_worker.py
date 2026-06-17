"""
Conversation Summarization Worker

Runs every few minutes alongside the debounce worker. Finds conversations that
have been inactive for 30+ minutes and have new messages since their last summary,
then generates AI-powered summaries using Claude Haiku with:

- Batching by listing (multiple conversations per API call)
- Prompt caching on the shared listing context
- Incremental summarization (previous summary + new messages only)
- Tiered strategy (rule-based for very short conversations, Haiku for longer)
- Structured JSON output
- Skip low-signal runs

Stores structured summary on DBConversation.ai_summary as JSON.
"""

import asyncio
import json
import logging
import os
import re
from datetime import datetime, timedelta

import anthropic

from app.db.session import SessionLocal, safe_commit
from app.models.db_models import DBConversation, DBMessage, DBListing

logger = logging.getLogger(__name__)

SUMMARY_CHECK_INTERVAL_SECONDS = int(os.getenv("SUMMARY_CHECK_INTERVAL_SECONDS", "1800"))  # 30 min
SUMMARY_INACTIVITY_MINUTES = 30       # wait 30 min after last message before summarizing
SUMMARY_MIN_NEW_MESSAGES = 2          # need at least 2 new messages to bother
SUMMARY_BATCH_SIZE = 10               # conversations per Claude call

# Use Haiku 4.5 — cheapest model for summarization
MODEL = "claude-haiku-4-5-20251001"


async def run_summary_worker():
    """Main worker loop. Runs until server shutdown."""
    logger.info(
        f"Summary worker started "
        f"(check every {SUMMARY_CHECK_INTERVAL_SECONDS}s, "
        f"{SUMMARY_INACTIVITY_MINUTES}min inactivity threshold)"
    )
    while True:
        try:
            await _process_ready_conversations()
        except Exception as e:
            logger.error(f"Summary worker error: {e}", exc_info=True)
        await asyncio.sleep(SUMMARY_CHECK_INTERVAL_SECONDS)


async def _process_ready_conversations():
    """Find inactive conversations needing summarization and process them."""
    now = datetime.utcnow()
    inactivity_cutoff = now - timedelta(minutes=SUMMARY_INACTIVITY_MINUTES)

    with SessionLocal() as db:
        # Conversations that:
        # 1. Have been inactive for 30+ min (updated_at < cutoff)
        # 2. Have messages newer than their last summary (or no summary yet)
        candidates = (
            db.query(DBConversation)
            .filter(DBConversation.updated_at < inactivity_cutoff)
            .filter(
                (DBConversation.last_summarized_at.is_(None))
                | (DBConversation.last_summarized_at < DBConversation.updated_at)
            )
            .all()
        )

        if not candidates:
            return

        logger.info(f"Summarizing {len(candidates)} inactive conversations")

        # Group by listing for batched prompt caching
        by_listing: dict = {}
        for conv in candidates:
            by_listing.setdefault(conv.listing_id, []).append(conv)

        # Process each listing's conversations in batches
        for listing_id, convs in by_listing.items():
            listing = db.get(DBListing, listing_id)
            if not listing:
                continue

            for i in range(0, len(convs), SUMMARY_BATCH_SIZE):
                batch = convs[i : i + SUMMARY_BATCH_SIZE]
                await _summarize_batch(db, listing, batch)


async def _summarize_batch(db, listing: DBListing, convs: list):
    """Summarize a batch of conversations for a single listing."""
    # Filter out low-signal conversations — use rule-based or skip entirely
    to_summarize = []
    for conv in convs:
        last_summarized = conv.last_summarized_at

        # Count new messages since last summary
        if last_summarized:
            new_msgs = [m for m in conv.messages if m.timestamp > last_summarized]
        else:
            new_msgs = list(conv.messages)

        new_buyer_msgs = [m for m in new_msgs if m.role == "user"]

        # Skip if too few new messages
        if len(new_buyer_msgs) < SUMMARY_MIN_NEW_MESSAGES and last_summarized:
            # Just bump the timestamp so we don't keep checking it
            conv.last_summarized_at = datetime.utcnow()
            continue

        to_summarize.append((conv, new_msgs))

    if not to_summarize:
        safe_commit(db)
        return

    # Build the batched prompt
    spa = listing.spa_data or {}
    sub_community = spa.get("sub_community")
    sub_community_part = f" — {sub_community}" if sub_community else ""
    price = listing.seller_asking_price or spa.get("purchase_price_aed", 0) or 0
    listing_context = (
        f"Listing: {spa.get('project', 'Unknown')}{sub_community_part}, "
        f"Unit {spa.get('unit_number', '?')}, "
        f"{spa.get('property_type', 'Property')}, "
        f"{spa.get('bedrooms', '?')} bed, "
        f"AED {price:,.0f}"
    )

    system_prompt = f"""You are analyzing buyer conversations for a Dubai real estate listing agent. Your job is to produce concise, structured summaries that help the seller understand what each buyer wants.

{listing_context}

For each conversation below, produce a structured summary as JSON with these fields:
- "topics": array of specific things the buyer asked about (e.g. "sea view", "schools", "payment plan", "Golden Visa")
- "interest_level": "high" | "medium" | "low" — based on engagement depth and specific questions
- "sentiment": "positive" | "neutral" | "concerned" | "negative"
- "key_question": one main question or concern the buyer raised (or null)
- "next_step_hint": a short phrase describing what this buyer seems to need next (e.g. "comparing options", "ready for viewing", "awaiting price response")
- "buyer_context": one-line description of the buyer's situation if clear (e.g. "family buyer focused on schools", "investor comparing yields", "first-time Dubai buyer")

Rules:
- NEVER include buyer personal information (names, phone numbers, emails, nationalities)
- Be specific — say "asked about school curriculum and distance" not "general questions"
- Keep topics concrete and searchable
- If this is an UPDATE with a previous summary, merge new findings with prior context — don't lose earlier topics unless they're contradicted

Output format: JSON array of objects with shape {{"id": "...", "summary": {{...}}}}, one per conversation, in the same order provided. Nothing else."""

    # Build user message with all conversations in batch
    user_parts = []
    for conv, new_msgs in to_summarize:
        prev_summary = conv.ai_summary
        prev_text = (
            f"PREVIOUS SUMMARY: {json.dumps(prev_summary)}\n"
            if prev_summary
            else "PREVIOUS SUMMARY: (none — this is the first summary)\n"
        )
        # Include only new messages, truncate content
        msg_lines = []
        for m in new_msgs[-30:]:  # cap at last 30 messages
            role = "BUYER" if m.role == "user" else "DALYA"
            content = m.content[:300]  # truncate long messages
            msg_lines.append(f"{role}: {content}")
        msgs_text = "\n".join(msg_lines) if msg_lines else "(no new messages)"

        user_parts.append(
            f"=== CONVERSATION {conv.conversation_id} ===\n"
            f"{prev_text}"
            f"NEW MESSAGES:\n{msgs_text}"
        )

    user_message = "\n\n".join(user_parts)

    # Call Claude Haiku with prompt caching on the system prompt
    try:
        client = anthropic.Anthropic()
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: client.messages.create(
                model=MODEL,
                max_tokens=2048,
                system=[{
                    "type": "text",
                    "text": system_prompt,
                    "cache_control": {"type": "ephemeral"},
                }],
                messages=[{"role": "user", "content": user_message}],
            ),
        )

        raw = response.content[0].text.strip()
        # Strip markdown code fences
        json_text = re.sub(r"^```(?:json)?\n?", "", raw)
        json_text = re.sub(r"\n?```$", "", json_text)
        results = json.loads(json_text)

        if not isinstance(results, list):
            raise ValueError("Expected JSON array")

        # Map results back to conversations
        result_by_id = {r["id"]: r["summary"] for r in results if isinstance(r, dict) and "id" in r}

        now = datetime.utcnow()
        updated_count = 0
        for conv, _ in to_summarize:
            summary = result_by_id.get(conv.conversation_id)
            if summary:
                conv.ai_summary = summary
                conv.last_summarized_at = now
                updated_count += 1

        safe_commit(db)
        logger.info(
            f"Summarized {updated_count}/{len(to_summarize)} conversations "
            f"for {spa.get('project', 'listing')} "
            f"(input: {response.usage.input_tokens}, "
            f"cache_read: {getattr(response.usage, 'cache_read_input_tokens', 0)}, "
            f"output: {response.usage.output_tokens})"
        )

    except Exception as e:
        logger.error(f"Failed to summarize batch for listing {listing.listing_id}: {e}", exc_info=True)
        db.rollback()
