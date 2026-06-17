"""
Env-driven transport selection.

`MESSAGING_TRANSPORT` env var controls which implementation is returned:
- "twilio"     (default; live)
- "dialog360"  (stub; raises NotImplementedError on use)
- "simulated"  (in-memory; used by tests and the simulation script)

Tests can also call `set_transport_override(transport)` to inject an instance
directly without touching env.
"""

from __future__ import annotations

import logging
import os
import threading
from typing import Optional

from app.core.runtime_config import is_production
from app.core.messaging.transport import MessagingTransport

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_override: Optional[MessagingTransport] = None
_cached: Optional[MessagingTransport] = None
_cached_kind: Optional[str] = None


def _build(kind: str) -> MessagingTransport:
    if kind == "simulated":
        if is_production():
            raise RuntimeError("Simulated messaging transport is not allowed in production")
        from app.core.messaging.simulated_transport import SimulatedTransport
        return SimulatedTransport()
    if kind == "dialog360":
        if is_production():
            raise RuntimeError("360dialog transport is not production-ready until signature verification is implemented")
        from app.core.messaging.dialog360_transport import Dialog360Transport
        return Dialog360Transport()
    # default
    from app.core.messaging.twilio_transport import TwilioTransport
    return TwilioTransport()


def get_transport() -> MessagingTransport:
    """Return the active MessagingTransport instance (singleton per kind)."""
    global _cached, _cached_kind
    with _lock:
        if _override is not None:
            return _override
        kind = (os.getenv("MESSAGING_TRANSPORT") or "twilio").lower()
        if _cached is not None and _cached_kind == kind:
            return _cached
        _cached = _build(kind)
        _cached_kind = kind
        logger.info("Messaging transport initialised: %s", kind)
        return _cached


def set_transport_override(transport: Optional[MessagingTransport]) -> None:
    """Inject a transport (e.g. SimulatedTransport for a test). Pass None to clear."""
    global _override, _cached, _cached_kind
    with _lock:
        _override = transport
        # Clear cache so subsequent get_transport() re-evaluates if override goes away
        _cached = None
        _cached_kind = None
