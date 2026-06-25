"""
Agent community-override scoping + isolation tests.

Verifies the security-critical guarantees: corrections are private to the owning
agent, never leak to another agent or brokerage, the buyer-safe flag gates what
reaches the advisor prompt, and the edit guard requires a listing in the project.
"""
import uuid

import pytest

from app.core import agent_community_overrides as svc
from app.db.session import SessionLocal
from app.models.db_models import (
    DBAgentCommunityOverride,
    DBBrokerage,
    DBBrokerageMember,
    DBListing,
)


@pytest.fixture
def seed():
    s = uuid.uuid4().hex[:8]
    bkg, bkg_other = f"aco-bkg-{s}", f"aco-bkgo-{s}"
    agent_a, agent_b, agent_none = f"aco-a-{s}", f"aco-b-{s}", f"aco-none-{s}"
    la, lb = f"aco-la-{s}", f"aco-lb-{s}"

    def brokerage(bid, name):
        return DBBrokerage(
            brokerage_id=bid, name=name, slug=bid, status="active",
            brokerage_ai_number=f"+9715{int(s, 16) % 100000000:08d}",
            agents_ai_number=f"+9716{int(s, 16) % 100000000:08d}",
        )

    def listing(lid, agent):
        return DBListing(
            listing_id=lid, brokerage_id=bkg, assigned_agent_id=agent, seller_id=agent,
            spa_data={"project": "Golf Grove"}, commission_rate=0.02, property_type="ready",
        )

    with SessionLocal() as db:
        db.add_all([
            brokerage(bkg, "ACO A"),
            brokerage(bkg_other, "ACO B"),
            DBBrokerageMember(brokerage_id=bkg, user_id=agent_a, role="agent", status="active"),
            DBBrokerageMember(brokerage_id=bkg, user_id=agent_b, role="agent", status="active"),
            DBBrokerageMember(brokerage_id=bkg, user_id=agent_none, role="agent", status="active"),
            listing(la, agent_a),
            listing(lb, agent_b),
        ])
        db.commit()

    data = dict(bkg=bkg, bkg_other=bkg_other, a=agent_a, b=agent_b, none=agent_none, la=la, lb=lb)
    yield data

    with SessionLocal() as db:
        db.query(DBAgentCommunityOverride).filter(
            DBAgentCommunityOverride.brokerage_id.in_([bkg, bkg_other])
        ).delete(synchronize_session=False)
        db.query(DBListing).filter(DBListing.listing_id.in_([la, lb])).delete(synchronize_session=False)
        db.query(DBBrokerageMember).filter(DBBrokerageMember.brokerage_id == bkg).delete(synchronize_session=False)
        db.query(DBBrokerage).filter(DBBrokerage.brokerage_id.in_([bkg, bkg_other])).delete(synchronize_session=False)
        db.commit()


def test_edit_guard_requires_listing_in_project(seed):
    with SessionLocal() as db:
        assert svc.agent_holds_listing_in_project(db, brokerage_id=seed["bkg"], agent_user_id=seed["a"], project_key="golf_grove")
        assert svc.agent_holds_listing_in_project(db, brokerage_id=seed["bkg"], agent_user_id=seed["b"], project_key="golf_grove")
        # An agent with no listing in the project cannot be granted overrides there.
        assert not svc.agent_holds_listing_in_project(db, brokerage_id=seed["bkg"], agent_user_id=seed["none"], project_key="golf_grove")
        # Wrong project key never matches.
        assert not svc.agent_holds_listing_in_project(db, brokerage_id=seed["bkg"], agent_user_id=seed["a"], project_key="park_ridge")


def test_override_is_private_to_owning_agent(seed):
    with SessionLocal() as db:
        db.add(DBAgentCommunityOverride(
            brokerage_id=seed["bkg"], agent_user_id=seed["a"], project_key="golf_grove",
            field_key="total_units", value_text="166 units", buyer_safe=True,
        ))
        db.commit()

        la = db.get(DBListing, seed["la"])
        lb = db.get(DBListing, seed["lb"])
        view_a = svc.build_community_view(db, listing=la, brokerage_id=seed["bkg"], agent_user_id=seed["a"])
        view_b = svc.build_community_view(db, listing=lb, brokerage_id=seed["bkg"], agent_user_id=seed["b"])

        tu_a = next(f for f in view_a["fields"] if f["key"] == "total_units")
        tu_b = next(f for f in view_b["fields"] if f["key"] == "total_units")
        assert tu_a["override"] and tu_a["override"]["value_text"] == "166 units"
        # Agent B (same brokerage, same project) must NOT see agent A's correction.
        assert tu_b["override"] is None

        assert svc.overrides_for_prompt(db, brokerage_id=seed["bkg"], agent_user_id=seed["a"], project_key="golf_grove")
        assert svc.overrides_for_prompt(db, brokerage_id=seed["bkg"], agent_user_id=seed["b"], project_key="golf_grove") == []


def test_cross_brokerage_isolation(seed):
    with SessionLocal() as db:
        db.add(DBAgentCommunityOverride(
            brokerage_id=seed["bkg_other"], agent_user_id=seed["a"], project_key="golf_grove",
            field_key="total_units", value_text="999 units", buyer_safe=True,
        ))
        db.commit()
        # Same agent id + project but a different brokerage must not surface.
        assert svc.overrides_for_prompt(db, brokerage_id=seed["bkg"], agent_user_id=seed["a"], project_key="golf_grove") == []


def test_buyer_safe_flag_gates_prompt(seed):
    with SessionLocal() as db:
        db.add(DBAgentCommunityOverride(
            brokerage_id=seed["bkg"], agent_user_id=seed["a"], project_key="golf_grove",
            field_key="service_charge", value_text="internal estimate only", buyer_safe=False,
        ))
        db.commit()
        prompts = svc.overrides_for_prompt(db, brokerage_id=seed["bkg"], agent_user_id=seed["a"], project_key="golf_grove")
        assert all(p["value"] != "internal estimate only" for p in prompts)
