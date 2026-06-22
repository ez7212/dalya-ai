from __future__ import annotations

import sys
from contextlib import contextmanager
from types import ModuleType, SimpleNamespace

import anyio
import pytest

from app.core.messaging import set_transport_override
from app.core.messaging.factory import get_transport


class NoDbSession:
    pass


class BaseModelStub:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

    def model_dump(self) -> dict:
        return dict(self.__dict__)


class HTTPExceptionStub(Exception):
    def __init__(self, status_code: int, detail: str):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


class APIRouterStub:
    def post(self, *args, **kwargs):
        def decorator(func):
            return func

        return decorator

    def get(self, *args, **kwargs):
        def decorator(func):
            return func

        return decorator


class TwilioRequestStub:
    def __init__(self, form_data: dict[str, str]):
        self._form_data = dict(form_data)
        self.headers: dict[str, str] = {}

    async def form(self) -> dict[str, str]:
        return dict(self._form_data)


def _install_no_db_route_import_stubs(monkeypatch):
    pydantic = ModuleType("pydantic")
    pydantic.BaseModel = BaseModelStub
    monkeypatch.setitem(sys.modules, "pydantic", pydantic)

    fastapi = ModuleType("fastapi")
    fastapi.APIRouter = APIRouterStub
    fastapi.Depends = lambda dependency=None, **kwargs: dependency
    fastapi.Form = lambda default=None, **kwargs: default
    fastapi.Header = lambda default=None, **kwargs: default
    fastapi.HTTPException = HTTPExceptionStub
    fastapi.Request = TwilioRequestStub
    monkeypatch.setitem(sys.modules, "fastapi", fastapi)

    fastapi_responses = ModuleType("fastapi.responses")
    fastapi_responses.PlainTextResponse = lambda content, media_type: SimpleNamespace(
        content=content,
        text=content,
        media_type=media_type,
        status_code=200,
    )
    monkeypatch.setitem(sys.modules, "fastapi.responses", fastapi_responses)

    sqlalchemy = ModuleType("sqlalchemy")
    sqlalchemy.func = SimpleNamespace()
    sqlalchemy_orm = ModuleType("sqlalchemy.orm")
    sqlalchemy_orm.Session = NoDbSession
    monkeypatch.setitem(sys.modules, "sqlalchemy", sqlalchemy)
    monkeypatch.setitem(sys.modules, "sqlalchemy.orm", sqlalchemy_orm)

    starlette_concurrency = ModuleType("starlette.concurrency")

    async def run_in_threadpool(func, *args, **kwargs):
        return func(*args, **kwargs)

    starlette_concurrency.run_in_threadpool = run_in_threadpool
    monkeypatch.setitem(sys.modules, "starlette.concurrency", starlette_concurrency)

    twilio_rest = ModuleType("twilio.rest")
    twilio_rest.Client = lambda *args, **kwargs: None
    twilio_validator = ModuleType("twilio.request_validator")

    class RequestValidatorStub:
        def __init__(self, token: str):
            self.token = token

        def validate(self, url: str, form_data: dict[str, str], signature: str) -> bool:
            return False

    twilio_validator.RequestValidator = RequestValidatorStub
    monkeypatch.setitem(sys.modules, "twilio.rest", twilio_rest)
    monkeypatch.setitem(sys.modules, "twilio.request_validator", twilio_validator)

    db_session = ModuleType("app.db.session")

    @contextmanager
    def service_session(*args, **kwargs):
        raise AssertionError("route opened a service DB session")
        yield NoDbSession()

    def get_db():
        raise AssertionError("route resolved the production DB dependency")
        yield NoDbSession()

    def set_service_db_session_context(*args, **kwargs):
        raise AssertionError("route attempted to set DB session context")

    db_session.safe_commit = lambda *args, **kwargs: None
    db_session.service_session = service_session
    db_session.get_db = get_db
    db_session.set_service_db_session_context = set_service_db_session_context
    monkeypatch.setitem(sys.modules, "app.db.session", db_session)

    auth = ModuleType("app.core.auth")
    auth.CurrentUser = BaseModelStub
    auth.get_current_user = lambda: BaseModelStub(id="test-user", email="test-user@dalya.local")
    auth.require_admin = lambda: BaseModelStub(id="test-user", email="test-user@dalya.local")
    monkeypatch.setitem(sys.modules, "app.core.auth", auth)

    brokerage_access = ModuleType("app.core.brokerage_access")
    brokerage_access.capture_requested_brokerage_context = lambda: None
    brokerage_access.current_requested_brokerage_id = lambda: None
    brokerage_access.resolve_request_brokerage_context = lambda *args, **kwargs: None
    monkeypatch.setitem(sys.modules, "app.core.brokerage_access", brokerage_access)

    chatbot_engine = ModuleType("app.core.chatbot_engine")
    chatbot_engine.engine = SimpleNamespace(
        handle_message_resilient=lambda inbound: ("not gated", None, None)
    )
    monkeypatch.setitem(sys.modules, "app.core.chatbot_engine", chatbot_engine)

    webhook_security = ModuleType("app.core.webhook_security")
    webhook_security.mark_inbound_provider_event = lambda *args, **kwargs: None
    webhook_security.record_inbound_provider_event = lambda *args, **kwargs: True
    monkeypatch.setitem(sys.modules, "app.core.webhook_security", webhook_security)

    lead_ingest = ModuleType("app.core.lead_ingest")
    lead_ingest.ingest_lead_email = lambda *args, **kwargs: None
    monkeypatch.setitem(sys.modules, "app.core.lead_ingest", lead_ingest)

    conversation = ModuleType("app.schemas.conversation")
    conversation.InboundMessage = BaseModelStub
    conversation.EscalationAlert = BaseModelStub
    monkeypatch.setitem(sys.modules, "app.schemas.conversation", conversation)


@pytest.fixture
def no_db_route_modules(monkeypatch):
    _install_no_db_route_import_stubs(monkeypatch)
    sys.modules.pop("app.api.whatsapp", None)
    sys.modules.pop("app.api.leads", None)

    import app.api.leads as leads_api
    import app.api.whatsapp as whatsapp_api

    yield SimpleNamespace(whatsapp=whatsapp_api, leads=leads_api)

    sys.modules.pop("app.api.whatsapp", None)
    sys.modules.pop("app.api.leads", None)


def _twilio_form(message_sid: str, body: str = "Hello") -> dict[str, str]:
    return {
        "From": "whatsapp:+971501234567",
        "To": "whatsapp:+971500000001",
        "Body": body,
        "MessageSid": message_sid,
        "NumMedia": "0",
    }


@pytest.mark.no_db
@pytest.mark.parametrize("dalya_env", ["staging", "preview"])
def test_whatsapp_send_test_routes_are_blocked_in_live_class_environments(no_db_route_modules, monkeypatch, dalya_env):
    whatsapp_api = no_db_route_modules.whatsapp

    # Given: a live-class environment with debug routes explicitly enabled.
    monkeypatch.setenv("DALYA_ENV", dalya_env)
    monkeypatch.setenv("ENABLE_DEBUG_ROUTES", "true")
    calls = []

    def fake_handle_message_resilient(inbound):
        calls.append(inbound)
        return "not gated", None, None

    monkeypatch.setattr(whatsapp_api.engine, "handle_message_resilient", fake_handle_message_resilient)

    # When: the debug send-test endpoint is called.
    async def call_route() -> None:
        await whatsapp_api.send_test_message(
            listing_id="listing",
            buyer_phone="+971501234567",
            message="hello",
        )

    # Then: the route is hidden before the simulation path can run.
    with pytest.raises(whatsapp_api.HTTPException) as exc_info:
        anyio.run(call_route)
    assert exc_info.value.status_code == 404
    assert calls == []


@pytest.mark.no_db
@pytest.mark.parametrize("dalya_env", ["staging", "preview"])
def test_whatsapp_send_test_voice_route_is_blocked_in_live_class_environments(no_db_route_modules, monkeypatch, dalya_env):
    whatsapp_api = no_db_route_modules.whatsapp

    # Given: a live-class environment with debug routes explicitly enabled.
    monkeypatch.setenv("DALYA_ENV", dalya_env)
    monkeypatch.setenv("ENABLE_DEBUG_ROUTES", "true")

    def service_session_should_not_run(*args, **kwargs):
        raise AssertionError("voice send-test reached DB before debug-route gate")

    monkeypatch.setattr(whatsapp_api, "service_session", service_session_should_not_run)

    # When: the debug voice send-test endpoint is called.
    async def call_route() -> None:
        await whatsapp_api.send_test_voice_note(
            listing_id="listing",
            buyer_phone="+971501234567",
            transcript_text="hello",
        )

    # Then: the route is hidden before the voice simulation path can run.
    with pytest.raises(whatsapp_api.HTTPException) as exc_info:
        anyio.run(call_route)
    assert exc_info.value.status_code == 404


@pytest.mark.no_db
@pytest.mark.parametrize("dalya_env", ["staging", "preview"])
def test_whatsapp_webhook_fails_closed_without_token_in_live_class_environments(no_db_route_modules, monkeypatch, dalya_env):
    whatsapp_api = no_db_route_modules.whatsapp

    # Given: a live-class webhook environment with no Twilio auth token.
    monkeypatch.setenv("DALYA_ENV", dalya_env)
    monkeypatch.setattr(whatsapp_api, "TWILIO_AUTH_TOKEN", "")

    def service_session_should_not_run(*args, **kwargs):
        raise AssertionError("webhook reached DB before provider verification failed closed")

    monkeypatch.setattr(whatsapp_api, "service_session", service_session_should_not_run)

    # When: Twilio posts an inbound webhook.
    form_data = _twilio_form(f"{dalya_env}-missing-token")

    async def call_route() -> None:
        await whatsapp_api.whatsapp_webhook(TwilioRequestStub(form_data), **form_data)

    # Then: the request fails closed before DB/provider-event work.
    with pytest.raises(whatsapp_api.HTTPException) as exc_info:
        anyio.run(call_route)
    assert exc_info.value.status_code == 503
    assert "verification is not configured" in exc_info.value.detail


@pytest.mark.no_db
@pytest.mark.parametrize("dalya_env", ["staging", "preview"])
def test_whatsapp_webhook_fails_closed_without_public_url_in_live_class_environments(no_db_route_modules, monkeypatch, dalya_env):
    whatsapp_api = no_db_route_modules.whatsapp

    # Given: a live-class webhook environment with a token but no public URL.
    monkeypatch.setenv("DALYA_ENV", dalya_env)
    monkeypatch.setattr(whatsapp_api, "TWILIO_AUTH_TOKEN", "token")
    monkeypatch.delenv("PUBLIC_URL", raising=False)

    def service_session_should_not_run(*args, **kwargs):
        raise AssertionError("webhook reached DB before PUBLIC_URL verification failed closed")

    monkeypatch.setattr(whatsapp_api, "service_session", service_session_should_not_run)

    # When: Twilio posts an inbound webhook.
    form_data = _twilio_form(f"{dalya_env}-missing-public-url")

    async def call_route() -> None:
        await whatsapp_api.whatsapp_webhook(TwilioRequestStub(form_data), **form_data)

    # Then: PUBLIC_URL is required before signature verification can proceed.
    with pytest.raises(whatsapp_api.HTTPException) as exc_info:
        anyio.run(call_route)
    assert exc_info.value.status_code == 503
    assert "PUBLIC_URL is required" in exc_info.value.detail


@pytest.mark.no_db
@pytest.mark.parametrize("dalya_env", ["staging", "preview"])
def test_lead_ingest_fails_closed_without_secret_in_live_class_environments(no_db_route_modules, monkeypatch, dalya_env):
    leads_api = no_db_route_modules.leads

    # Given: a live-class lead-ingest environment without a shared secret.
    monkeypatch.setenv("DALYA_ENV", dalya_env)
    monkeypatch.delenv("LEAD_INGEST_SECRET", raising=False)

    def record_event_should_not_run(*args, **kwargs):
        raise AssertionError("lead ingest reached provider ledger before secret check failed closed")

    monkeypatch.setattr(leads_api, "record_inbound_provider_event", record_event_should_not_run)

    # When: an inbound lead email is posted.
    payload = leads_api.InboundLeadEmail(
        to="leads+missing@dalya.ai",
        body="Phone: +971501234567",
    )

    async def call_route() -> None:
        await leads_api.ingest_email(payload, db=NoDbSession())

    # Then: the request fails closed before provider-ledger work.
    with pytest.raises(leads_api.HTTPException) as exc_info:
        anyio.run(call_route)
    assert exc_info.value.status_code == 503
    assert "verification is not configured" in exc_info.value.detail


@pytest.mark.parametrize("dalya_env", ["staging", "preview", "live"])
def test_live_class_environments_block_simulated_and_dialog360_transports(monkeypatch, dalya_env):
    # Given: a live-class environment with test/stub transports configured.
    monkeypatch.setenv("DALYA_ENV", dalya_env)
    set_transport_override(None)
    try:
        # When / Then: simulated transport is rejected.
        monkeypatch.setenv("MESSAGING_TRANSPORT", "simulated")
        with pytest.raises(RuntimeError, match="Simulated messaging transport"):
            get_transport()

        # When / Then: 360dialog remains rejected until signature verification is ready.
        set_transport_override(None)
        monkeypatch.setenv("MESSAGING_TRANSPORT", "dialog360")
        with pytest.raises(RuntimeError, match="360dialog"):
            get_transport()
    finally:
        set_transport_override(None)


@pytest.mark.parametrize("dalya_env", ["staging", "preview", "live"])
def test_live_class_twilio_transport_requires_credentials(monkeypatch, dalya_env):
    from app.core.messaging.twilio_transport import TwilioTransport

    # Given: a live-class environment without Twilio credentials.
    monkeypatch.setenv("DALYA_ENV", dalya_env)
    monkeypatch.delenv("TWILIO_ACCOUNT_SID", raising=False)
    monkeypatch.delenv("TWILIO_AUTH_TOKEN", raising=False)

    # When / Then: the live transport refuses to initialize.
    with pytest.raises(RuntimeError, match="TWILIO_ACCOUNT_SID"):
        TwilioTransport()
