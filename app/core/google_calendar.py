from __future__ import annotations

import os
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional
from urllib.parse import urlencode

import httpx

from app.models.db_models import DBAgentCalendarConnection, DBConversation, DBListing, DBViewing


GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_CALENDAR_API = "https://www.googleapis.com/calendar/v3"
DEFAULT_SCOPES = [
    "https://www.googleapis.com/auth/calendar.freebusy",
    "https://www.googleapis.com/auth/calendar.events",
]


@dataclass
class CalendarBusyWindow:
    starts_at: datetime
    ends_at: datetime
    calendar_id: str


class CalendarProviderError(RuntimeError):
    pass


class GoogleCalendarProvider:
    def authorization_url(self, *, state: str, redirect_uri: str, scopes: Optional[list[str]] = None) -> str:
        client_id = os.getenv("GOOGLE_CALENDAR_CLIENT_ID")
        if not client_id:
            raise CalendarProviderError("GOOGLE_CALENDAR_CLIENT_ID is not configured")
        params = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "access_type": "offline",
            "prompt": "consent",
            "scope": " ".join(scopes or DEFAULT_SCOPES),
            "state": state,
        }
        return f"{GOOGLE_AUTH_URL}?{urlencode(params)}"

    def exchange_code(self, *, code: str, redirect_uri: str) -> dict[str, Any]:
        client_id = os.getenv("GOOGLE_CALENDAR_CLIENT_ID")
        client_secret = os.getenv("GOOGLE_CALENDAR_CLIENT_SECRET")
        if not client_id or not client_secret:
            raise CalendarProviderError("Google Calendar OAuth credentials are not configured")
        response = httpx.post(
            GOOGLE_TOKEN_URL,
            data={
                "code": code,
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            },
            timeout=15,
        )
        if response.status_code >= 400:
            raise CalendarProviderError(f"Google OAuth token exchange failed: {response.text[:300]}")
        return response.json()

    def freebusy(
        self,
        connection: DBAgentCalendarConnection,
        *,
        time_min: datetime,
        time_max: datetime,
    ) -> list[CalendarBusyWindow]:
        token = self._access_token(connection)
        calendar_ids = self._calendar_ids(connection)
        response = httpx.post(
            f"{GOOGLE_CALENDAR_API}/freeBusy",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "timeMin": time_min.isoformat(),
                "timeMax": time_max.isoformat(),
                "items": [{"id": calendar_id} for calendar_id in calendar_ids],
            },
            timeout=15,
        )
        if response.status_code >= 400:
            raise CalendarProviderError(f"Google free/busy failed: {response.text[:300]}")
        payload = response.json()
        windows: list[CalendarBusyWindow] = []
        for calendar_id, calendar_payload in (payload.get("calendars") or {}).items():
            for item in calendar_payload.get("busy") or []:
                try:
                    windows.append(
                        CalendarBusyWindow(
                            starts_at=datetime.fromisoformat(str(item["start"]).replace("Z", "+00:00")).replace(tzinfo=None),
                            ends_at=datetime.fromisoformat(str(item["end"]).replace("Z", "+00:00")).replace(tzinfo=None),
                            calendar_id=calendar_id,
                        )
                    )
                except (KeyError, ValueError, TypeError):
                    continue
        return windows

    def upsert_viewing_event(
        self,
        connection: DBAgentCalendarConnection,
        *,
        viewing: DBViewing,
        listing: DBListing,
        conversation: DBConversation,
        scheduled_for: datetime,
        duration_minutes: int = 45,
        existing_event_id: Optional[str] = None,
    ) -> dict[str, Any]:
        from datetime import timedelta

        token = self._access_token(connection)
        calendar_id = self._calendar_ids(connection)[0]
        timezone = (connection.settings or {}).get("timezone") or "Asia/Dubai"
        spa = listing.spa_data or {}
        summary = f"Viewing: {spa.get('project') or 'Listing'} Unit {spa.get('unit_number') or ''}".strip()
        description = (
            f"Buyer: {conversation.buyer_name or conversation.buyer_phone}\n"
            f"Listing ID: {listing.listing_id}\n"
            f"Viewing ID: {viewing.viewing_id}\n"
            "Created by Dalya."
        )
        ends_at = scheduled_for + timedelta(minutes=duration_minutes)
        body = {
            "summary": summary,
            "description": description,
            "start": {"dateTime": scheduled_for.isoformat(), "timeZone": timezone},
            "end": {"dateTime": ends_at.isoformat(), "timeZone": timezone},
            "extendedProperties": {
                "private": {
                    "dalya_viewing_id": viewing.viewing_id,
                    "dalya_listing_id": listing.listing_id,
                    "dalya_conversation_id": conversation.conversation_id,
                }
            },
        }
        if existing_event_id:
            response = httpx.patch(
                f"{GOOGLE_CALENDAR_API}/calendars/{calendar_id}/events/{existing_event_id}",
                headers={"Authorization": f"Bearer {token}"},
                json=body,
                timeout=15,
            )
        else:
            response = httpx.post(
                f"{GOOGLE_CALENDAR_API}/calendars/{calendar_id}/events",
                headers={"Authorization": f"Bearer {token}"},
                json=body,
                timeout=15,
            )
        if response.status_code >= 400:
            raise CalendarProviderError(f"Google calendar event write failed: {response.text[:300]}")
        payload = response.json()
        return {
            "provider": "google",
            "calendar_id": calendar_id,
            "event_id": payload.get("id") or existing_event_id,
            "html_link": payload.get("htmlLink"),
            "status": payload.get("status") or "confirmed",
            "synced_at": datetime.utcnow().isoformat(),
        }

    def delete_viewing_event(
        self,
        connection: DBAgentCalendarConnection,
        *,
        event_id: str,
        calendar_id: Optional[str] = None,
    ) -> dict[str, Any]:
        token = self._access_token(connection)
        resolved_calendar_id = calendar_id or self._calendar_ids(connection)[0]
        response = httpx.delete(
            f"{GOOGLE_CALENDAR_API}/calendars/{resolved_calendar_id}/events/{event_id}",
            headers={"Authorization": f"Bearer {token}"},
            timeout=15,
        )
        if response.status_code not in {200, 204, 410}:
            raise CalendarProviderError(f"Google calendar event delete failed: {response.text[:300]}")
        return {
            "provider": "google",
            "calendar_id": resolved_calendar_id,
            "event_id": event_id,
            "deleted_at": datetime.utcnow().isoformat(),
        }

    def _calendar_ids(self, connection: DBAgentCalendarConnection) -> list[str]:
        ids = list(connection.selected_calendar_ids or [])
        return ids or ["primary"]

    def _access_token(self, connection: DBAgentCalendarConnection) -> str:
        token_ref = connection.token_ref or ""
        settings = connection.settings or {}
        env_name = settings.get("access_token_env")
        if token_ref.startswith("env:"):
            env_name = token_ref.split(":", 1)[1]
        if env_name:
            token = os.getenv(env_name)
            if token:
                return token
        if token_ref.startswith("literal:") and os.getenv("ALLOW_LITERAL_CALENDAR_TOKENS") == "true":
            return token_ref.split(":", 1)[1]
        raise CalendarProviderError("Google Calendar token_ref could not be resolved")


_calendar_provider_override: Optional[Any] = None


def set_calendar_provider_override(provider: Optional[Any]) -> None:
    global _calendar_provider_override
    _calendar_provider_override = provider


def calendar_provider() -> Any:
    return _calendar_provider_override or GoogleCalendarProvider()


def connected_google_connection(connection: Optional[DBAgentCalendarConnection]) -> bool:
    if not connection:
        return False
    if connection.provider != "google" or connection.status != "connected":
        return False
    return bool(connection.token_ref and (connection.selected_calendar_ids or ["primary"]))


def new_oauth_state() -> str:
    return uuid.uuid4().hex
