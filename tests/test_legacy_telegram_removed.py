from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP_MAIN = ROOT / "app" / "main.py"
APP_TELEGRAM = ROOT / "app" / "api" / "telegram.py"
APP_WHATSAPP = ROOT / "app" / "api" / "whatsapp.py"
APP_RESEARCH = ROOT / "app" / "api" / "research.py"
ENV_EXAMPLE = ROOT / ".env.example"


def _source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _literal_strings(path: Path) -> set[str]:
    tree = ast.parse(_source(path), filename=str(path))
    return {
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    }


def test_fastapi_app_does_not_register_removed_transport_route() -> None:
    main_source = _source(APP_MAIN)
    router_call = "include_router(" + "telegram"
    webhook_path = "/telegram" + "/webhook"

    assert "telegram" not in main_source.split("from app.api import", 1)[1].split("\n", 1)[0]
    assert router_call not in main_source
    assert webhook_path not in _literal_strings(APP_MAIN)
    assert not APP_TELEGRAM.exists()


def test_startup_never_registers_telegram_webhook() -> None:
    main_source = _source(APP_MAIN)
    token_env = "TELEGRAM" + "_BOT_TOKEN"

    assert "register_" + "telegram_webhook" not in main_source
    assert "setWebhook" not in main_source
    assert token_env not in main_source


def test_health_does_not_require_or_report_telegram() -> None:
    main_source = _source(APP_MAIN)
    tree = ast.parse(main_source, filename=str(APP_MAIN))
    health_nodes = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "health"
    ]

    assert len(health_nodes) == 1
    health_source = ast.get_source_segment(main_source, health_nodes[0]) or ""
    assert "telegram" not in health_source.lower()
    assert "TELEGRAM_" not in health_source


def test_active_runtime_code_does_not_send_telegram_notifications() -> None:
    runtime_sources = "\n".join(_source(path) for path in (APP_WHATSAPP, APP_RESEARCH))

    forbidden_terms = (
        "api.telegram.org",
        "TELEGRAM" + "_BOT_TOKEN",
        "TELEGRAM" + "_CHAT_ID",
        "DBTelegramReplyRoute",
        "Reply to THIS message on " + "Telegram",
        "Failed to send " + "Telegram",
        "Telegram notification",
    )
    for term in forbidden_terms:
        assert term not in runtime_sources


def test_env_example_does_not_encourage_telegram_setup() -> None:
    env_source = _source(ENV_EXAMPLE)
    token_env = "TELEGRAM" + "_BOT_TOKEN"
    chat_env = "TELEGRAM" + "_CHAT_ID"

    assert token_env not in env_source
    assert chat_env not in env_source
    assert "Telegram" not in env_source
    assert "register " + "Telegram " + "webhook" not in env_source
