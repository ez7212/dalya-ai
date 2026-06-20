from sqlalchemy import text

from app.db.session import (
    SessionLocal,
    get_db_session_context,
    service_db_context_scope,
    service_session,
    set_db_session_context,
    set_service_db_session_context,
)


def _current_rls_settings(db):
    row = db.execute(
        text(
            """
            select
                current_setting('app.user_id', true) as user_id,
                current_setting('app.brokerage_id', true) as brokerage_id,
                current_setting('app.is_service', true) as is_service,
                current_setting('app.is_platform_admin', true) as is_platform_admin
            """
        )
    ).one()
    return {
        "user_id": row.user_id or "",
        "brokerage_id": row.brokerage_id or "",
        "is_service": row.is_service or "",
        "is_platform_admin": row.is_platform_admin or "",
    }


def test_service_helper_records_explicit_service_context():
    with SessionLocal() as db:
        set_service_db_session_context(db, brokerage_id="brokerage-a")

        context = get_db_session_context(db)

    assert context["app.brokerage_id"] == "brokerage-a"
    assert context["app.is_service"] is True
    assert context["app.is_platform_admin"] is False
    assert "app.user_id" not in context


def test_service_session_applies_set_local_context():
    with service_session(brokerage_id="brokerage-a") as db:
        settings = _current_rls_settings(db)

    assert settings["brokerage_id"] == "brokerage-a"
    assert settings["is_service"] == "true"
    assert settings["is_platform_admin"] == "false"


def test_service_context_scope_applies_to_nested_sessions_and_resets():
    with service_db_context_scope(brokerage_id="brokerage-a"):
        with SessionLocal() as db:
            scoped_settings = _current_rls_settings(db)

    with SessionLocal() as db:
        reset_settings = _current_rls_settings(db)

    assert scoped_settings["brokerage_id"] == "brokerage-a"
    assert scoped_settings["is_service"] == "true"
    assert scoped_settings["is_platform_admin"] == "false"
    assert reset_settings["brokerage_id"] == ""
    assert reset_settings["is_service"] == ""
    assert reset_settings["is_platform_admin"] == ""


def test_normal_user_context_does_not_escalate_to_service_or_platform_admin():
    with SessionLocal() as db:
        set_db_session_context(
            db,
            user_id="user-a",
            brokerage_id="brokerage-a",
        )
        settings = _current_rls_settings(db)
        context = get_db_session_context(db)

    assert context["app.user_id"] == "user-a"
    assert context["app.brokerage_id"] == "brokerage-a"
    assert "app.is_service" not in context
    assert "app.is_platform_admin" not in context
    assert settings["user_id"] == "user-a"
    assert settings["brokerage_id"] == "brokerage-a"
    assert settings["is_service"] == ""
    assert settings["is_platform_admin"] == ""


def test_platform_admin_context_requires_explicit_opt_in():
    with service_session() as db:
        default_context = get_db_session_context(db)
        default_settings = _current_rls_settings(db)

    with service_session(is_platform_admin=True) as db:
        admin_context = get_db_session_context(db)
        admin_settings = _current_rls_settings(db)

    assert default_context["app.is_service"] is True
    assert default_context["app.is_platform_admin"] is False
    assert default_settings["is_service"] == "true"
    assert default_settings["is_platform_admin"] == "false"
    assert admin_context["app.is_service"] is True
    assert admin_context["app.is_platform_admin"] is True
    assert admin_settings["is_service"] == "true"
    assert admin_settings["is_platform_admin"] == "true"
