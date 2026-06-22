from dataclasses import dataclass
from types import TracebackType
from typing import NoReturn

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

import app.api.whatsapp as whatsapp_api
from app.core.auth import CurrentUser
from app.db import crud as listing_crud


pytestmark = pytest.mark.no_db


@pytest.fixture
def app() -> FastAPI:
    test_app = FastAPI()
    test_app.include_router(whatsapp_api.router, prefix="/api/v1")
    return test_app


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    return TestClient(app)


LEGACY_LISTING_ROUTE_PATHS = {
    "/api/v1/listings/{listing_id}/portal-links",
    "/api/v1/listings/{listing_id}/stats",
    "/api/v1/listings/{listing_id}/conversations",
    "/api/v1/listings/{listing_id}/media",
}
LISTING_ACTIVATION_ROUTE_PATH = "/api/v1/listings/{listing_id}/activate"


@dataclass(frozen=True, slots=True)
class FakeBrokerageContext:
    brokerage_id: str


@dataclass(slots=True)  # noqa: MUTABLE_OK
class FakeDbSession:
    """Mutable session fake carrying only the context-manager surface under test."""

    info: dict[str, str]

    def in_transaction(self) -> bool:
        return False


@dataclass(slots=True)  # noqa: MUTABLE_OK
class FakeListing:
    """Mutable listing fake so denial tests can verify no activation writes occurred."""

    brokerage_id: str
    seller_id: str | None = None
    seller_phone: str | None = None


@dataclass(frozen=True, slots=True)
class FakeServiceSession:
    db: FakeDbSession

    def __enter__(self) -> FakeDbSession:
        return self.db

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool:
        return False


def test_legacy_listing_routes_are_not_registered(app: FastAPI) -> None:
    # Given: the current FastAPI application route table.
    registered_paths = {
        route.path
        for route in app.routes
        if isinstance(route, APIRoute)
    }

    # When: checking for legacy listing routes that lack scoped agent ownership.
    registered_legacy_paths = registered_paths & LEGACY_LISTING_ROUTE_PATHS

    # Then: those public legacy routes are not registered on the app.
    assert registered_legacy_paths == set()


def test_legacy_listing_paths_return_plain_not_found(client: TestClient) -> None:
    # Given: unauthenticated requests to the legacy listing path shapes.
    requests = [
        ("GET", "/api/v1/listings/unknown-listing/portal-links", None),
        ("GET", "/api/v1/listings/unknown-listing/stats", None),
        ("GET", "/api/v1/listings/unknown-listing/conversations", None),
        ("POST", "/api/v1/listings/unknown-listing/media", ["https://example.test/render.jpg"]),
    ]

    for method, path, json_body in requests:
        # When: the path is requested without authenticated brokerage context.
        response = client.request(method, path, json=json_body)

        # Then: FastAPI closes the route as an unmatched path, not a service handler.
        assert response.status_code == 404
        assert response.json() == {"detail": "Not Found"}


def test_listing_activation_captures_requested_brokerage_context(app: FastAPI) -> None:
    # Given: the retained authenticated listing activation route.
    activation_routes = [
        route
        for route in app.routes
        if isinstance(route, APIRoute) and route.path == LISTING_ACTIVATION_ROUTE_PATH
    ]
    assert len(activation_routes) == 1
    route = activation_routes[0]

    # When: inspecting the route dependency boundary.
    dependency_names = {
        dependency.call.__name__
        for dependency in route.dependant.dependencies
        if dependency.call is not None
    }

    # Then: brokerage context is captured before the endpoint body runs.
    assert "capture_requested_brokerage_context" in dependency_names


@pytest.mark.asyncio
async def test_listing_activation_resolver_failure_prevents_listing_lookup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Given: brokerage context resolution denies the authenticated user.
    fake_db = FakeDbSession(info={})
    user = CurrentUser(id="agent-a", email="agent-a@example.test")
    lookup_calls: list[str] = []

    def service_session() -> FakeServiceSession:
        return FakeServiceSession(fake_db)

    def deny_brokerage_context(
        db: FakeDbSession,
        current_user: CurrentUser,
        requested_brokerage_id: str | None,
    ) -> NoReturn:
        raise HTTPException(status_code=403, detail="forbidden")

    def fail_listing_lookup(db: FakeDbSession, listing_id: str) -> NoReturn:
        lookup_calls.append(listing_id)
        pytest.fail("listing lookup must not run before brokerage authorization")

    monkeypatch.setattr(whatsapp_api, "service_session", service_session)
    monkeypatch.setattr(whatsapp_api, "resolve_request_brokerage_context", deny_brokerage_context)
    monkeypatch.setattr(listing_crud, "get_listing", fail_listing_lookup)

    # When: activation is attempted.
    with pytest.raises(HTTPException) as exc_info:
        await whatsapp_api.activate_listing_chatbot("listing-a", user=user)

    # Then: authorization failure is returned and listing lookup never ran.
    assert exc_info.value.status_code == 403
    assert lookup_calls == []


@pytest.mark.asyncio
async def test_listing_activation_cross_brokerage_listing_denies_before_mutation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Given: the user resolves to one brokerage and the listing belongs to another.
    fake_db = FakeDbSession(info={})
    listing = FakeListing(brokerage_id="brokerage-a")
    user = CurrentUser(id="agent-b", email="agent-b@example.test")

    def service_session() -> FakeServiceSession:
        return FakeServiceSession(fake_db)

    def resolve_other_brokerage(
        db: FakeDbSession,
        current_user: CurrentUser,
        requested_brokerage_id: str | None,
    ) -> FakeBrokerageContext:
        return FakeBrokerageContext(brokerage_id="brokerage-b")

    def get_cross_brokerage_listing(db: FakeDbSession, listing_id: str) -> FakeListing:
        return listing

    monkeypatch.setattr(whatsapp_api, "service_session", service_session)
    monkeypatch.setattr(whatsapp_api, "resolve_request_brokerage_context", resolve_other_brokerage)
    monkeypatch.setattr(listing_crud, "get_listing", get_cross_brokerage_listing)

    # When: activation is attempted for the cross-brokerage listing.
    with pytest.raises(HTTPException) as exc_info:
        await whatsapp_api.activate_listing_chatbot(
            "listing-a",
            seller_phone="+971500000000",
            user=user,
        )

    # Then: the request is denied before seller ownership fields are mutated.
    assert exc_info.value.status_code == 404
    assert listing.seller_id is None
    assert listing.seller_phone is None
