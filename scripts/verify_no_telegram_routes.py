#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
from dataclasses import asdict, dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class TelegramRouteEvidence:
    telegram_route_registered: bool
    telegram_router_included: bool
    startup_registers_webhook: bool
    health_reports_telegram: bool
    app_imported: bool
    import_error: str | None
    route_paths: list[str]

    @property
    def passed(self) -> bool:
        return not (
            self.telegram_route_registered
            or self.telegram_router_included
            or self.startup_registers_webhook
            or self.health_reports_telegram
        )


def _source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _health_source(main_source: str) -> str:
    tree = ast.parse(main_source, filename="app/main.py")
    for node in ast.walk(tree):
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "health":
            return ast.get_source_segment(main_source, node) or ""
    return ""


def _source_evidence() -> TelegramRouteEvidence:
    main_source = _source(ROOT / "app" / "main.py")
    health_source = _health_source(main_source)
    return TelegramRouteEvidence(
        telegram_route_registered="/telegram/webhook" in main_source,
        telegram_router_included="include_router(telegram" in main_source,
        startup_registers_webhook="register_telegram_webhook" in main_source
        or "setWebhook" in main_source,
        health_reports_telegram="telegram" in health_source.lower(),
        app_imported=False,
        import_error=None,
        route_paths=[],
    )


def _runtime_route_paths() -> tuple[list[str], str | None]:
    try:
        from app.main import app
    except ModuleNotFoundError as exc:
        return [], f"{type(exc).__name__}: {exc}"

    return [getattr(route, "path", "") for route in app.routes], None


def build_evidence() -> TelegramRouteEvidence:
    source = _source_evidence()
    route_paths, import_error = _runtime_route_paths()
    route_registered = source.telegram_route_registered or "/api/v1/telegram/webhook" in route_paths

    return TelegramRouteEvidence(
        telegram_route_registered=route_registered,
        telegram_router_included=source.telegram_router_included,
        startup_registers_webhook=source.startup_registers_webhook,
        health_reports_telegram=source.health_reports_telegram,
        app_imported=import_error is None,
        import_error=import_error,
        route_paths=route_paths,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence", required=True, type=Path)
    args = parser.parse_args()

    evidence = build_evidence()
    payload = asdict(evidence) | {"passed": evidence.passed}
    args.evidence.parent.mkdir(parents=True, exist_ok=True)
    args.evidence.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(payload, sort_keys=True))
    return 0 if evidence.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
