"""
Community Research API Router — admin-only endpoints for managing
automated community KB research jobs.

Endpoints:
  POST   /admin/research              — trigger a new research job
  GET    /admin/research              — list all research jobs
  GET    /admin/research/{id}         — get a specific research job
  POST   /admin/research/{id}/approve — approve and move KB file to live
  DELETE /admin/research/{id}         — reject and delete draft
"""

import asyncio
import json
import logging
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.auth import CurrentUser, require_admin
from app.core.community_researcher import CommunityResearcher
from app.db.session import get_db, safe_commit, service_session, set_service_db_session_context
from app.models.db_models import DBCommunityResearch, DBListing

logger = logging.getLogger(__name__)

router = APIRouter()

_PROJECT_ROOT = Path(__file__).parent.parent.parent
_KNOWLEDGE_BASE_DIR = _PROJECT_ROOT / "knowledge_base"

# ── Simple rate limiter for expensive operations ─────────────────────────
# Prevents accidental cost spikes from spamming the trigger/re-research endpoints.
# Max 5 research jobs triggered per hour.

_research_trigger_timestamps: list[float] = []
RESEARCH_RATE_LIMIT = 5          # max triggers
RESEARCH_RATE_WINDOW = 3600      # per hour


def _check_research_rate_limit():
    """Raise 429 if too many research jobs triggered recently."""
    import time
    now = time.time()
    cutoff = now - RESEARCH_RATE_WINDOW
    # Prune old entries
    _research_trigger_timestamps[:] = [t for t in _research_trigger_timestamps if t > cutoff]
    if len(_research_trigger_timestamps) >= RESEARCH_RATE_LIMIT:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit: max {RESEARCH_RATE_LIMIT} research jobs per hour. "
                   f"Try again in {int(RESEARCH_RATE_WINDOW - (now - _research_trigger_timestamps[0]))}s.",
        )
    _research_trigger_timestamps.append(now)


# ── Concurrency control ─────────────────────────────────────────────────────
# Max 2 research jobs run simultaneously. Others queue on the semaphore.
# Prevents Opus rate limit hits and cost spikes when many SPAs arrive at once.

_research_semaphore = asyncio.Semaphore(2)


# ── Request / Response schemas ───────────────────────────────────────────────

class ResearchRequest(BaseModel):
    project_name: str
    developer: str
    sub_community: str | None = None


class ResearchJobResponse(BaseModel):
    id: int
    project_name: str
    developer: str
    status: str
    file_path: str | None
    research_confidence: float | None
    source_urls: list | None
    audit_flags: list | None
    created_at: datetime | None
    last_researched_at: datetime | None

    class Config:
        from_attributes = True


# ── Background task ──────────────────────────────────────────────────────────

RESEARCH_TIMEOUT_SECONDS = 1800  # 30 minutes


async def _notify_admin_research_complete(project_name: str, result: dict):
    """Send a Telegram message to admin when research is ready for review."""
    telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
    telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not telegram_token or not telegram_chat_id:
        return

    confidence = result.get("research_confidence") or 0
    flags = result.get("audit_flags", [])
    flag_count = len(flags)
    flag_summary = ""
    if flags:
        # Show first 3 flags
        flag_lines = "\n".join(f"  • {f}" for f in flags[:3])
        remaining = f"\n  + {flag_count - 3} more" if flag_count > 3 else ""
        flag_summary = f"\n\nAudit flags ({flag_count}):\n{flag_lines}{remaining}"

    message = (
        f"📋 Community research complete: {project_name}\n"
        f"Confidence: {confidence:.0%}\n"
        f"Status: needs_review{flag_summary}\n\n"
        f"Review and approve at /api/v1/admin/research"
    )

    try:
        import httpx
        async with httpx.AsyncClient() as client:
            await client.post(
                f"https://api.telegram.org/bot{telegram_token}/sendMessage",
                json={"chat_id": telegram_chat_id, "text": message},
                timeout=10,
            )
    except Exception as e:
        logger.warning("Failed to send Telegram notification: %s", e)


async def _run_research_job(research_id: int, project_name: str, developer: str, sub_community: str | None):
    """Background coroutine that runs the full research pipeline with a 30-min timeout."""
    async with _research_semaphore:
        await _run_research_job_inner(research_id, project_name, developer, sub_community)


async def _run_research_job_inner(research_id: int, project_name: str, developer: str, sub_community: str | None):
    """Inner research job — runs under the concurrency semaphore."""
    with service_session(is_platform_admin=True) as db:
        try:
            # Mark as researching
            record = db.query(DBCommunityResearch).filter_by(id=research_id).first()
            if not record:
                logger.error("Research record %d not found", research_id)
                return
            record.status = "researching"
            safe_commit(db)
            logger.info("Research job %d: status → researching", research_id)

            # Run the research pipeline with timeout
            researcher = CommunityResearcher()
            result = await asyncio.wait_for(
                researcher.research_community(
                    project_name=project_name,
                    developer=developer,
                    sub_community=sub_community,
                ),
                timeout=RESEARCH_TIMEOUT_SECONDS,
            )

            # Update record with results
            record.status = "needs_review"
            record.file_path = result["file_path"]
            record.research_confidence = result.get("research_confidence")
            record.source_urls = result.get("source_urls", [])
            record.audit_flags = result.get("audit_flags", [])
            record.last_researched_at = datetime.now(timezone.utc)
            safe_commit(db)
            logger.info(
                "Research job %d: status → needs_review (confidence=%.2f, flags=%d)",
                research_id,
                result.get("research_confidence") or 0,
                len(result.get("audit_flags", [])),
            )

            # Notify admin via Telegram
            await _notify_admin_research_complete(project_name, result)

        except asyncio.TimeoutError:
            logger.error("Research job %d timed out after %ds", research_id, RESEARCH_TIMEOUT_SECONDS)
            try:
                record = db.query(DBCommunityResearch).filter_by(id=research_id).first()
                if record:
                    record.status = "failed"
                    record.audit_flags = [f"Research timed out after {RESEARCH_TIMEOUT_SECONDS}s"]
                    safe_commit(db)
            except Exception:
                logger.error("Failed to update research record %d to failed status", research_id)

        except Exception as e:
            logger.error("Research job %d failed: %s", research_id, e, exc_info=True)
            try:
                record = db.query(DBCommunityResearch).filter_by(id=research_id).first()
                if record:
                    record.status = "failed"
                    record.audit_flags = [f"Research failed: {e}"]
                    safe_commit(db)
            except Exception:
                logger.error("Failed to update research record %d to failed status", research_id)


# ── Endpoints ────────────────────────────────────────────────────────────────

@router.post("/admin/research")
async def trigger_research(
    body: ResearchRequest,
    admin: CurrentUser = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Create a research job. Runs asynchronously in the background."""
    set_service_db_session_context(db, is_platform_admin=True)
    _check_research_rate_limit()

    # Check for existing research job (unique constraint on project_name + developer)
    existing = db.query(DBCommunityResearch).filter_by(
        project_name=body.project_name, developer=body.developer,
    ).first()
    if existing and existing.status in ("pending", "researching"):
        return {
            "id": existing.id,
            "status": existing.status,
            "message": f"Research job already {existing.status} for '{body.project_name}'.",
        }
    if existing and existing.status == "needs_review":
        return {
            "id": existing.id,
            "status": "needs_review",
            "message": f"Research for '{body.project_name}' is already awaiting review.",
        }

    # Create or re-use a failed/rejected/stale record
    if existing:
        record = existing
        record.status = "pending"
        record.audit_flags = []
        record.file_path = None
    else:
        record = DBCommunityResearch(
            project_name=body.project_name,
            developer=body.developer,
            status="pending",
        )
        db.add(record)
    safe_commit(db)
    db.refresh(record)

    logger.info(
        "Created research job %d: %s by %s (requested by %s)",
        record.id, body.project_name, body.developer, admin.email,
    )

    # Launch background task
    asyncio.create_task(
        _run_research_job(
            research_id=record.id,
            project_name=body.project_name,
            developer=body.developer,
            sub_community=body.sub_community,
        )
    )

    return {
        "id": record.id,
        "status": "pending",
        "message": f"Research job created for '{body.project_name}'. "
                   "Check status via GET /api/v1/admin/research/{id}.",
    }


@router.get("/admin/knowledge-base")
async def list_knowledge_base_files(
    admin: CurrentUser = Depends(require_admin),
):
    """List all knowledge-base JSON files (live + needs_review)."""
    files = []
    if _KNOWLEDGE_BASE_DIR.exists():
        for p in sorted(_KNOWLEDGE_BASE_DIR.glob("*.json")):
            if p.name == "schema.json":
                continue
            stat = p.stat()
            files.append({
                "filename": p.name,
                "status": "live",
                "size_bytes": stat.st_size,
                "modified_at": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
            })
        needs_review_dir = _KNOWLEDGE_BASE_DIR / "needs_review"
        if needs_review_dir.exists():
            for p in sorted(needs_review_dir.glob("*.json")):
                stat = p.stat()
                files.append({
                    "filename": f"needs_review/{p.name}",
                    "status": "needs_review",
                    "size_bytes": stat.st_size,
                    "modified_at": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
                })
    return {"files": files, "count": len(files)}


@router.get("/admin/knowledge-base/{filename:path}")
async def get_knowledge_base_file(
    filename: str,
    admin: CurrentUser = Depends(require_admin),
):
    """Return the parsed JSON contents of a single KB file."""
    # Resolve path safely — prevent traversal beyond knowledge_base/.
    safe_rel = Path(filename)
    if safe_rel.is_absolute() or ".." in safe_rel.parts:
        raise HTTPException(status_code=400, detail="Invalid filename")
    if not filename.endswith(".json"):
        raise HTTPException(status_code=400, detail="Only .json files are served")

    target = (_KNOWLEDGE_BASE_DIR / safe_rel).resolve()
    try:
        target.relative_to(_KNOWLEDGE_BASE_DIR.resolve())
    except ValueError:
        raise HTTPException(status_code=400, detail="Path escapes knowledge_base/")

    if not target.exists() or not target.is_file():
        raise HTTPException(status_code=404, detail="KB file not found")

    try:
        with target.open("r", encoding="utf-8") as f:
            content = json.load(f)
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=500, detail=f"Invalid JSON: {e}")

    stat = target.stat()
    return {
        "filename": filename,
        "status": "needs_review" if "needs_review" in filename else "live",
        "size_bytes": stat.st_size,
        "modified_at": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
        "content": content,
    }


@router.get("/admin/research")
async def list_research_jobs(
    admin: CurrentUser = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """List all community research records with their status."""
    set_service_db_session_context(db, is_platform_admin=True)
    records = (
        db.query(DBCommunityResearch)
        .order_by(DBCommunityResearch.created_at.desc())
        .all()
    )
    return [
        ResearchJobResponse.model_validate(r)
        for r in records
    ]


@router.get("/admin/research/{research_id}")
async def get_research_job(
    research_id: int,
    admin: CurrentUser = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Get details of a research job including audit flags."""
    set_service_db_session_context(db, is_platform_admin=True)
    record = db.query(DBCommunityResearch).filter_by(id=research_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Research job not found")
    return ResearchJobResponse.model_validate(record)


@router.post("/admin/research/{research_id}/approve")
async def approve_research(
    research_id: int,
    admin: CurrentUser = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Move a needs_review KB file to the live knowledge_base/ directory.
    Updates the research record status to 'approved'.
    Reloads the community data index so new listings pick it up.
    """
    set_service_db_session_context(db, is_platform_admin=True)
    record = db.query(DBCommunityResearch).filter_by(id=research_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Research job not found")

    if record.status == "approved":
        raise HTTPException(
            status_code=409,
            detail=f"Research job {research_id} is already approved (file: {record.file_path}).",
        )

    if record.status != "needs_review":
        raise HTTPException(
            status_code=400,
            detail=f"Cannot approve a research job with status '{record.status}'. "
                   "Only 'needs_review' jobs can be approved.",
        )

    if not record.file_path:
        raise HTTPException(
            status_code=400,
            detail="Research job has no file_path — nothing to approve.",
        )

    # Resolve file paths
    source_path = _KNOWLEDGE_BASE_DIR / record.file_path
    filename = Path(record.file_path).name
    dest_path = _KNOWLEDGE_BASE_DIR / filename

    if not source_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Draft file not found at {record.file_path}",
        )

    # Check if destination already exists (another approval or manual upload)
    if dest_path.exists():
        raise HTTPException(
            status_code=409,
            detail=f"KB file already exists at knowledge_base/{filename}. "
                   "Remove it first or reject this draft.",
        )

    # Move file to live directory
    shutil.move(str(source_path), str(dest_path))
    logger.info("Moved KB file: %s → %s", source_path, dest_path)

    # Update DB record
    record.status = "approved"
    record.file_path = filename
    record.last_audited_at = datetime.now(timezone.utc)

    # Incrementally add to index — no full rebuild needed
    try:
        from app.core.community_data import add_to_index
        add_to_index(dest_path)
    except Exception as e:
        logger.warning("Failed to add to community data index: %s", e)

    # Attach community data to any matching listings that lack it
    _attach_community_data_to_listings(db, dest_path, record.project_name)

    safe_commit(db)

    return {
        "id": record.id,
        "status": "approved",
        "file_path": filename,
        "message": f"KB file approved and moved to knowledge_base/{filename}. "
                   "Community data index will rebuild on next access.",
    }


@router.post("/admin/research/{research_id}/re-research")
async def re_research(
    research_id: int,
    admin: CurrentUser = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Re-run research for an approved or stale community.
    Preserves the existing live file as a backup until the new draft is approved.
    """
    set_service_db_session_context(db, is_platform_admin=True)
    _check_research_rate_limit()

    record = db.query(DBCommunityResearch).filter_by(id=research_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Research job not found")

    if record.status in ("pending", "researching"):
        return {
            "id": record.id,
            "status": record.status,
            "message": f"Research is already {record.status} — cannot re-research.",
        }

    # Backup the current live file if it exists in knowledge_base/ (not needs_review)
    backup_note = None
    if record.file_path and not record.file_path.startswith("needs_review/"):
        live_path = _KNOWLEDGE_BASE_DIR / record.file_path
        if live_path.exists():
            backup_path = _KNOWLEDGE_BASE_DIR / f".backup_{record.file_path}"
            shutil.copy2(str(live_path), str(backup_path))
            backup_note = f"Backed up existing file to .backup_{record.file_path}"
            logger.info("Backed up %s → %s", live_path, backup_path)

    # Reset to pending and re-fire
    record.status = "pending"
    record.audit_flags = [note for note in (record.audit_flags or []) if "FIXED" not in note]
    if backup_note:
        record.audit_flags.append(backup_note)
    record.file_path = None
    safe_commit(db)

    logger.info("Re-research triggered for job %d (%s)", record.id, record.project_name)

    asyncio.create_task(
        _run_research_job(
            research_id=record.id,
            project_name=record.project_name,
            developer=record.developer,
            sub_community=None,
        )
    )

    return {
        "id": record.id,
        "status": "pending",
        "backup": backup_note,
        "message": f"Re-research triggered for '{record.project_name}'. "
                   "Existing live file preserved as backup until new draft is approved.",
    }


@router.delete("/admin/research/{research_id}")
async def reject_research(
    research_id: int,
    admin: CurrentUser = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Delete the draft file and mark the research as rejected."""
    set_service_db_session_context(db, is_platform_admin=True)
    record = db.query(DBCommunityResearch).filter_by(id=research_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Research job not found")

    # Delete the draft file if it exists
    if record.file_path:
        file_path = _KNOWLEDGE_BASE_DIR / record.file_path
        if file_path.exists():
            file_path.unlink()
            logger.info("Deleted draft KB file: %s", file_path)

    record.status = "rejected"
    safe_commit(db)

    return {
        "id": record.id,
        "status": "rejected",
        "message": "Research job rejected and draft file deleted.",
    }


# ── Helpers ──────────────────────────────────────────────────────────────────

def _attach_community_data_to_listings(db: Session, kb_path: Path, project_name: str):
    """
    Find listings that match this community and attach community_data
    if they don't already have it.
    """
    try:
        with open(kb_path) as f:
            kb_data = json.load(f)
    except Exception as e:
        logger.warning("Failed to read KB file for listing attachment: %s", e)
        return

    aliases = [a.lower() for a in kb_data.get("aliases", [])]
    if not aliases:
        return

    # Find listings without community_data whose project name matches
    listings = db.query(DBListing).filter(DBListing.community_data.is_(None)).all()
    attached_count = 0

    for listing in listings:
        spa = listing.spa_data or {}
        listing_project = (spa.get("project") or "").lower()
        if any(alias in listing_project for alias in aliases):
            from app.core.community_data import get_community_data_for_listing

            community = get_community_data_for_listing(
                project_name=spa.get("project", ""),
                developer=spa.get("developer"),
            )
            if community:
                listing.community_data = community
                attached_count += 1

    if attached_count:
        logger.info(
            "Attached community data to %d listing(s) for project '%s'",
            attached_count, project_name,
        )
