from pathlib import Path
from types import ModuleType, SimpleNamespace
import importlib.util
import sys


FORBIDDEN_SAMPLE_MARKERS = (
    "sample-",
    "Ahmed K.",
    "sample-conv",
    "sample-campaign",
    "+971502148821",
    "+971551110000",
    "+971500000000",
)


def _module(name: str, **attrs):
    module = ModuleType(name)
    for key, value in attrs.items():
        setattr(module, key, value)
    return module


class _BaseModel:
    def __init__(self, **values):
        for key, value in values.items():
            setattr(self, key, value)


class _HTTPException(Exception):
    def __init__(self, status_code: int, detail: str):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


class _Router:
    def __init__(self, *args, **kwargs):
        pass

    def get(self, *args, **kwargs):
        return self._decorator

    def post(self, *args, **kwargs):
        return self._decorator

    def patch(self, *args, **kwargs):
        return self._decorator

    @staticmethod
    def _decorator(func):
        return func


class _Func:
    def __getattr__(self, name):
        return self

    def __call__(self, *args, **kwargs):
        return self


class _Model:
    pass


def _depends(value=None):
    return value


def _query(default=None, **kwargs):
    return default


def _install_import_stubs():
    model_names = (
        "DBAIDraft",
        "DBAgentMessageRoute",
        "DBAgentProfile",
        "DBBrokerage",
        "DBBrokerageBuyerProfile",
        "DBBrokerageMember",
        "DBBuyerSuppression",
        "DBCampaign",
        "DBCampaignRecipient",
        "DBCampaignUpload",
        "DBConversation",
        "DBDraftReply",
        "DBLeadAction",
        "DBLeadAssignment",
        "DBLeadTask",
        "DBMarketingEvent",
        "DBMarketingPage",
        "DBMessage",
        "DBEscalationThread",
        "DBEscalationThreadQuestion",
        "DBListing",
        "DBOfferRecord",
        "DBOwnerLead",
        "DBOutreachDraft",
        "DBViewing",
    )
    stubs = {
        "fastapi": _module(
            "fastapi",
            APIRouter=_Router,
            Depends=_depends,
            HTTPException=_HTTPException,
            Query=_query,
        ),
        "pydantic": _module("pydantic", BaseModel=_BaseModel),
        "sqlalchemy": _module("sqlalchemy", func=_Func(), or_=lambda *args: args),
        "sqlalchemy.orm": _module(
            "sqlalchemy.orm",
            Session=type("Session", (), {}),
            aliased=lambda value, *args, **kwargs: value,
            joinedload=lambda *args, **kwargs: SimpleNamespace(joinedload=lambda *inner_args, **inner_kwargs: None),
        ),
        "app": _module("app"),
        "app.core": _module("app.core"),
        "app.core.auth": _module(
            "app.core.auth",
            CurrentUser=type("CurrentUser", (), {}),
            get_current_user=lambda: None,
        ),
        "app.core.brokerage_access": _module(
            "app.core.brokerage_access",
            can_view_conversation=lambda *args, **kwargs: True,
            capture_requested_brokerage_context=lambda: None,
            current_requested_brokerage_id=lambda: None,
            is_buyer_suppressed=lambda *args, **kwargs: False,
            record_compliance_event=lambda *args, **kwargs: None,
            resolve_request_brokerage_context=lambda *args, **kwargs: None,
        ),
        "app.core.buyer_profiles": _module("app.core.buyer_profiles", effective_fields=lambda *args, **kwargs: {}),
        "app.core.deal_readiness": _module(
            "app.core.deal_readiness",
            compute_readiness=lambda *args, **kwargs: {},
            fields_from_effective_fields=lambda *args, **kwargs: {},
            serialize_readiness=lambda value: value,
        ),
        "app.core.hot_list": _module(
            "app.core.hot_list",
            latest_hotlist_refresh_run=lambda *args, **kwargs: None,
            refresh_hotlist_with_run=lambda *args, **kwargs: None,
            refresh_morning_hot_list=lambda *args, **kwargs: None,
        ),
        "app.db": _module("app.db"),
        "app.db.session": _module("app.db.session", get_db=lambda: None, safe_commit=lambda *args, **kwargs: None),
        "app.models": _module("app.models"),
        "app.models.db_models": _module("app.models.db_models", **{name: _Model for name in model_names}),
    }
    previous = {name: sys.modules.get(name) for name in stubs}
    sys.modules.update(stubs)
    return previous, tuple(stubs)


def _restore_import_stubs(previous, names):
    for name in names:
        if previous[name] is None:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = previous[name]


def _load_agent_dashboard_module():
    previous, names = _install_import_stubs()
    try:
        module_path = Path(__file__).resolve().parents[1] / "app" / "api" / "agent_dashboard.py"
        spec = importlib.util.spec_from_file_location("agent_dashboard_under_test", module_path)
        module = importlib.util.module_from_spec(spec)
        assert spec and spec.loader
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        return module
    finally:
        _restore_import_stubs(previous, names)


def _run_completed(coro):
    try:
        coro.send(None)
    except StopIteration as stop:
        return stop.value
    raise AssertionError("Expected dashboard coroutine to complete synchronously")


def _flatten_text(value):
    if isinstance(value, dict):
        return " ".join(_flatten_text(item) for item in value.values())
    if isinstance(value, list):
        return " ".join(_flatten_text(item) for item in value)
    return str(value)


def test_authenticated_empty_dashboard_returns_live_empty_workspace():
    # Given: an authenticated brokerage workspace whose dashboard sources all return no live rows.
    module = _load_agent_dashboard_module()
    context = module.AgentDashboardContext(
        brokerage_id="brokerage-empty",
        brokerage_name="Empty Brokerage",
        user_id="agent-empty",
        role="agent",
        display_name="Empty Agent",
    )
    module._agent_context = lambda user, db: context
    module.refresh_morning_hot_list = lambda *args, **kwargs: None
    module._conversation_inbox = lambda db, ctx: []
    module._hot_leads = lambda db, ctx: []
    module._tasks = lambda db, ctx: []
    module._viewings = lambda db, ctx: []
    module._escalation_threads = lambda *args, **kwargs: []
    module._drafts = lambda db, ctx: {"reply_drafts": [], "ai_drafts": [], "outreach_drafts": []}
    module._hotlist_refresh_payload = lambda db, ctx: {
        "status": "not_run",
        "last_refresh_at": None,
        "completed_at": None,
        "trigger": None,
        "assignment_count": 0,
        "task_count": 0,
        "draft_count": 0,
        "error": None,
    }
    module._campaigns = lambda db, ctx: []
    module._campaign_uploads = lambda db, ctx: []
    module._campaign_recipients = lambda db, ctx: []
    module._owner_leads = lambda db, ctx: []
    module._marketing = lambda db, ctx: {"pages": [], "events_7d": 0}
    module._metrics = lambda db, ctx, payload: {
        "conversations": 0,
        "needs_reply": 0,
        "hot_leads": 0,
        "open_tasks": 0,
        "viewings_today": 0,
        "stale_leads": 0,
        "draft_replies": 0,
        "outreach_drafts": 0,
        "active_campaigns": 0,
        "new_owner_leads": 0,
        "marketing_events_7d": 0,
        "open_escalations": 0,
    }
    module._performance_metrics = lambda db, ctx: {
        "scope": "current_agent",
        "agent_user_id": ctx.user_id,
        "generated_at": None,
        "windows": [],
        "primary": {
            "key": "today",
            "label": "Today",
            "start_at": None,
            "end_at": None,
            "metrics": {
                "new_buyer_conversations": 0,
                "escalations_handled": 0,
                "avg_response_minutes": None,
                "follow_ups_sent": 0,
                "viewings_proposed": 0,
                "viewings_confirmed": 0,
                "viewings_completed": 0,
                "offers_detected": 0,
                "hot_leads_active": 0,
                "tasks_overdue": 0,
            },
        },
    }

    # When: the authenticated dashboard endpoint builds the response.
    payload = _run_completed(module.agent_dashboard(user=object(), db=object()))

    # Then: it returns a real empty live workspace, not operational sample data.
    assert payload["sample_data"] is False
    assert payload["empty_state"]["reason"] == "no_workspace_activity"
    assert payload["empty_state"]["message"]
    assert all(value == 0 for value in payload["metrics"].values())
    for key in (
        "conversations",
        "hot_leads",
        "tasks",
        "viewings",
        "escalation_threads",
        "campaigns",
        "campaign_uploads",
        "campaign_recipients",
        "owner_leads",
    ):
        assert payload[key] == []
    assert payload["drafts"] == {"reply_drafts": [], "ai_drafts": [], "outreach_drafts": []}
    body_text = _flatten_text(payload)
    assert not any(marker in body_text for marker in FORBIDDEN_SAMPLE_MARKERS)


if __name__ == "__main__":
    test_authenticated_empty_dashboard_returns_live_empty_workspace()
