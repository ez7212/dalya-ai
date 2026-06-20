import logging
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from app.api import agent, agent_dashboard, crm, leads, listings, media, onboarding, research, seller, spa_parser, telegram, viewings, whatsapp
from app.core.runtime_config import debug_routes_enabled, is_production

logger = logging.getLogger(__name__)


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Configure root logger
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        level=getattr(logging, log_level, logging.INFO),
        format="%(asctime)s %(levelname)-8s %(message)s",
    )

    # Create all tables on startup (safe to run multiple times — no-ops if tables exist)
    from app.db.session import engine, Base
    import app.models.db_models  # noqa: F401 — registers models with Base
    Base.metadata.create_all(bind=engine)

    # Recover stuck research jobs (crashed/deployed during 15-20 min pipeline)
    from datetime import datetime, timedelta
    from app.db.session import SessionLocal, safe_commit
    from app.models.db_models import DBCommunityResearch
    try:
        with SessionLocal() as db:
            cutoff = datetime.utcnow() - timedelta(minutes=25)
            stuck = db.query(DBCommunityResearch).filter(
                DBCommunityResearch.status == "researching",
                DBCommunityResearch.created_at < cutoff,
            ).all()
            for record in stuck:
                logger.warning(
                    "Recovering stuck research job %d (%s) — resetting to pending",
                    record.id, record.project_name,
                )
                record.status = "pending"
                record.audit_flags = (record.audit_flags or []) + [
                    "Auto-recovered from stuck 'researching' state on server restart"
                ]
            if stuck:
                safe_commit(db)
                logger.info("Recovered %d stuck research job(s)", len(stuck))
    except Exception as e:
        logger.error("Failed to recover stuck research jobs: %s", e)

    # Re-fire recovered pending jobs
    import asyncio
    try:
        with SessionLocal() as db:
            pending = db.query(DBCommunityResearch).filter_by(status="pending").all()
            for record in pending:
                from app.api.research import _run_research_job
                asyncio.create_task(_run_research_job(
                    research_id=record.id,
                    project_name=record.project_name,
                    developer=record.developer,
                    sub_community=None,
                ))
                logger.info("Re-fired research job %d (%s)", record.id, record.project_name)
    except Exception as e:
        logger.error("Failed to re-fire pending research jobs: %s", e)

    # Start optional background workers. Keep these gated so local/dev servers
    # do not keep serverless Postgres compute warm when no live WhatsApp traffic
    # is expected.
    worker_tasks = []
    if _env_bool("ENABLE_DEBOUNCE_WORKER", default=False):
        from app.core.debounce_worker import run_debounce_worker
        worker_tasks.append(asyncio.create_task(run_debounce_worker()))
    else:
        logger.info("Debounce worker disabled (ENABLE_DEBOUNCE_WORKER=false)")

    if _env_bool("ENABLE_SUMMARY_WORKER", default=False):
        from app.core.summary_worker import run_summary_worker
        worker_tasks.append(asyncio.create_task(run_summary_worker()))
    else:
        logger.info("Summary worker disabled (ENABLE_SUMMARY_WORKER=false)")

    if _env_bool("ENABLE_RESEARCH_AUDITOR", default=False):
        from app.core.research_auditor import run_audit_worker
        worker_tasks.append(asyncio.create_task(run_audit_worker()))
    else:
        logger.info("Research auditor disabled (ENABLE_RESEARCH_AUDITOR=false)")

    # Register Telegram webhook if public URL is configured
    public_url = os.getenv("PUBLIC_URL", "")
    if public_url and os.getenv("TELEGRAM_BOT_TOKEN"):
        from app.api.telegram import register_telegram_webhook
        await register_telegram_webhook(public_url)

    yield

    # Shutdown: cancel workers gracefully
    for task in worker_tasks:
        task.cancel()
    for task in worker_tasks:
        try:
            await task
        except asyncio.CancelledError:
            pass


app = FastAPI(
    title="Dalya API",
    description="B2B agent workflow infrastructure for Dubai real estate brokerages",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(media.router, tags=["Media"])
app.include_router(spa_parser.router, prefix="/api/v1", tags=["SPA Parser"])
app.include_router(whatsapp.router, prefix="/api/v1", tags=["WhatsApp"])
app.include_router(telegram.router, prefix="/api/v1", tags=["Telegram"])
app.include_router(onboarding.router, prefix="/api/v1", tags=["Onboarding"])
app.include_router(listings.router, prefix="/api/v1", tags=["Listings"])
app.include_router(agent.router, prefix="/api/v1", tags=["Agent"])
app.include_router(agent_dashboard.router, prefix="/api/v1", tags=["Agent Dashboard"])
app.include_router(viewings.router, prefix="/api/v1", tags=["Viewing Logistics"])
app.include_router(seller.router, prefix="/api/v1", tags=["Seller"])
app.include_router(crm.router, prefix="/api/v1", tags=["CRM"])
app.include_router(leads.router, prefix="/api/v1", tags=["Lead Ingestion"])
app.include_router(research.router, prefix="/api/v1", tags=["Research"])


@app.get("/health")
async def health():
    import asyncio
    from sqlalchemy import text

    checks: dict = {
        "anthropic_api": "missing",
        "database": "error",
        "twilio": "unconfigured",
        "telegram": "unconfigured",
        "active_listings": 0,
        "pending_queue_messages": 0,
    }

    # Anthropic API key — present and starts with expected prefix
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if api_key and api_key.startswith("sk-"):
        checks["anthropic_api"] = "ok"

    # Twilio env vars
    if os.getenv("TWILIO_ACCOUNT_SID") and os.getenv("TWILIO_AUTH_TOKEN"):
        checks["twilio"] = "ok"

    # Telegram env vars
    if os.getenv("TELEGRAM_BOT_TOKEN") and os.getenv("TELEGRAM_CHAT_ID"):
        checks["telegram"] = "ok"

    # Database connectivity + counts (sync engine, run in threadpool)
    def _db_checks():
        from app.db.session import SessionLocal
        db = SessionLocal()
        try:
            listings_count = db.execute(
                text("SELECT count(*) FROM listings")
            ).scalar()
            pending_count = db.execute(
                text("SELECT count(*) FROM message_queue WHERE status = 'pending'")
            ).scalar()
            return "ok", listings_count or 0, pending_count or 0
        except Exception:
            return "error", 0, 0
        finally:
            db.close()

    try:
        db_status, listings_count, pending_count = await asyncio.get_event_loop().run_in_executor(
            None, _db_checks
        )
        checks["database"] = db_status
        checks["active_listings"] = listings_count
        checks["pending_queue_messages"] = pending_count
    except Exception:
        pass  # checks already default to "error" / 0

    status = "ok"
    if (
        checks["anthropic_api"] != "ok"
        or checks["database"] != "ok"
        or checks["twilio"] != "ok"
        or checks["telegram"] != "ok"
    ):
        status = "degraded"

    if is_production():
        return {"status": status}
    return {"status": status, "checks": checks}


@app.get("/admin-dashboard", response_class=HTMLResponse)
async def admin_dashboard():
    """Multi-listing dashboard — styled HTML page showing all active listings."""
    if not debug_routes_enabled():
        raise HTTPException(status_code=404, detail="Not found")

    import asyncio
    from app.db.session import SessionLocal
    from app.models.db_models import DBListing, DBConversation
    from app.core.chatbot_engine import engine

    def _query():
        with SessionLocal() as db:
            listings = db.query(DBListing).all()
            results = []
            for listing in listings:
                spa = listing.spa_data or {}
                stats = engine.get_listing_stats(listing.listing_id)
                last_activity = listing.created_at
                conv = (
                    db.query(DBConversation)
                    .filter_by(listing_id=listing.listing_id)
                    .order_by(DBConversation.updated_at.desc())
                    .first()
                )
                if conv:
                    last_activity = conv.updated_at
                results.append({
                    "project": spa.get("project", "Unknown"),
                    "unit_number": spa.get("unit_number", "—"),
                    "seller_asking_price": listing.seller_asking_price,
                    "total_conversations": stats.get("total_conversations", 0),
                    "escalated_leads": stats.get("escalated_leads", 0),
                    "last_activity": last_activity,
                })
            return results

    listings = await asyncio.get_event_loop().run_in_executor(None, _query)

    # Build table rows
    if listings:
        rows_html = ""
        for li in listings:
            price = (
                f"AED {li['seller_asking_price']:,.0f}"
                if li["seller_asking_price"]
                else "—"
            )
            esc = li["escalated_leads"]
            esc_color = "#C9A96E" if esc > 0 else "#4A7C6F"
            activity = (
                li["last_activity"].strftime("%d %b %Y, %H:%M")
                if li["last_activity"]
                else "—"
            )
            rows_html += f"""<tr>
  <td style="padding:14px 18px;"><span style="color:#F5EFE6;">{li['project']}</span><br><span style="color:#8A8078;font-size:13px;">Unit {li['unit_number']}</span></td>
  <td style="padding:14px 18px;color:#C9A96E;font-family:monospace;white-space:nowrap;">{price}</td>
  <td style="padding:14px 18px;text-align:center;color:#F5EFE6;">{li['total_conversations']}</td>
  <td style="padding:14px 18px;text-align:center;color:{esc_color};font-weight:600;">{esc}</td>
  <td style="padding:14px 18px;color:#8A8078;font-size:13px;white-space:nowrap;">{activity}</td>
</tr>"""
        body = f"""<table style="width:100%;border-collapse:collapse;">
  <thead>
    <tr style="border-bottom:1px solid #2E4057;">
      <th style="padding:12px 18px;text-align:left;color:#8A8078;font-weight:500;font-size:12px;text-transform:uppercase;letter-spacing:0.05em;">Property</th>
      <th style="padding:12px 18px;text-align:left;color:#8A8078;font-weight:500;font-size:12px;text-transform:uppercase;letter-spacing:0.05em;">Asking Price</th>
      <th style="padding:12px 18px;text-align:center;color:#8A8078;font-weight:500;font-size:12px;text-transform:uppercase;letter-spacing:0.05em;">Conversations</th>
      <th style="padding:12px 18px;text-align:center;color:#8A8078;font-weight:500;font-size:12px;text-transform:uppercase;letter-spacing:0.05em;">Escalated</th>
      <th style="padding:12px 18px;text-align:left;color:#8A8078;font-weight:500;font-size:12px;text-transform:uppercase;letter-spacing:0.05em;">Last Activity</th>
    </tr>
  </thead>
  <tbody>{rows_html}</tbody>
</table>"""
    else:
        body = """<div style="text-align:center;padding:80px 20px;">
  <p style="color:#8A8078;font-size:18px;margin:0;">No active listings yet.</p>
  <p style="color:#8A8078;font-size:14px;margin:12px 0 0;">Upload an SPA to create your first listing.</p>
</div>"""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Dalya — Listings</title>
<style>
  *{{margin:0;padding:0;box-sizing:border-box;}}
  body{{background:#0F1923;color:#F5EFE6;font-family:system-ui,-apple-system,sans-serif;min-height:100vh;}}
  .container{{max-width:960px;margin:0 auto;padding:40px 20px;}}
  h1{{font-size:22px;font-weight:600;margin-bottom:8px;}}
  .subtitle{{color:#8A8078;font-size:14px;margin-bottom:32px;}}
  .card{{background:#1A2B3C;border-radius:10px;overflow:hidden;}}
  table tbody tr{{border-bottom:1px solid rgba(46,64,87,0.5);}}
  table tbody tr:last-child{{border-bottom:none;}}
  table tbody tr:hover{{background:rgba(46,64,87,0.3);}}
  @media(max-width:640px){{
    table,thead,tbody,tr,th,td{{display:block;}}
    thead{{display:none;}}
    tr{{padding:14px 18px;border-bottom:1px solid rgba(46,64,87,0.5);}}
    td{{padding:4px 0 !important;text-align:left !important;}}
    td:first-child{{padding-bottom:8px !important;}}
  }}
</style>
</head>
<body>
<div class="container">
  <h1>Dalya — Listings</h1>
  <p class="subtitle">RERA Licensed &middot; Trakheesi Partner &middot; DLD Registered</p>
  <div class="card">{body}</div>
</div>
</body>
</html>"""
    return HTMLResponse(content=html)
