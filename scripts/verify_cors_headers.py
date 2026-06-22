from __future__ import annotations

import argparse
import importlib
import json
import sys
from pathlib import Path
from types import ModuleType
from typing import TypedDict

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.testclient import TestClient


API_MODULES = (
    "agent",
    "agent_dashboard",
    "crm",
    "leads",
    "listings",
    "media",
    "onboarding",
    "research",
    "seller",
    "spa_parser",
    "viewings",
    "whatsapp",
)


class CorsEvidence(TypedDict):
    origin: str
    status_code: int
    access_control_allow_origin: str | None
    access_control_allow_credentials: str | None
    configured_allow_origins: list[str]
    passed: bool


def _install_api_route_stubs() -> None:
    for module_name in API_MODULES:
        module = ModuleType(f"app.api.{module_name}")
        module.router = APIRouter()
        sys.modules[f"app.api.{module_name}"] = module


def _import_app() -> FastAPI:
    _install_api_route_stubs()
    sys.modules.pop("app.main", None)
    app_module = importlib.import_module("app.main")
    return app_module.app


def _configured_allow_origins(app: FastAPI) -> list[str]:
    for middleware in app.user_middleware:
        if middleware.cls is CORSMiddleware:
            return [str(origin) for origin in middleware.kwargs["allow_origins"]]
    raise RuntimeError("CORSMiddleware was not registered")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--origin", required=True)
    parser.add_argument("--evidence", required=True)
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    app = _import_app()
    response = TestClient(app).options(
        "/",
        headers={
            "Origin": args.origin,
            "Access-Control-Request-Method": "GET",
        },
    )
    evidence: CorsEvidence = {
        "origin": args.origin,
        "status_code": response.status_code,
        "access_control_allow_origin": response.headers.get("access-control-allow-origin"),
        "access_control_allow_credentials": response.headers.get(
            "access-control-allow-credentials"
        ),
        "configured_allow_origins": _configured_allow_origins(app),
        "passed": response.headers.get("access-control-allow-origin") == args.origin,
    }
    evidence_path = Path(args.evidence)
    evidence_path.parent.mkdir(parents=True, exist_ok=True)
    evidence_path.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n")
    return 0 if evidence["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
