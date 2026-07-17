from __future__ import annotations

from cryptography.fernet import Fernet
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models_saas import Organization, OrganizationMember, ProfessionalEmail, Role, User
from app.services.professional_emails import (
    activate_professional_email,
    create_professional_email_request,
    sender_options_for_user,
    suggest_elfis_email,
)


def _session(monkeypatch):
    key = Fernet.generate_key().decode()
    monkeypatch.setattr("app.config.settings.email_credentials_encryption_key", key)
    monkeypatch.setattr("app.config.settings.brevo_api_key", "")
    monkeypatch.setattr("app.config.settings.platform_email_from", "")
    monkeypatch.setattr("app.config.settings.app_env", "development")
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def test_suggest_and_request_flow(monkeypatch):
    db = _session(monkeypatch)
    monkeypatch.setattr("app.services.professional_emails._send_admin_notification", lambda s: None)
    monkeypatch.setattr("app.services.professional_emails._send_user_confirmation", lambda u: None)

    user = User(
        first_name="Jean",
        last_name="Dupont",
        email="jean@gmail.com",
        phone="0612345678",
        status="active",
    )
    org = Organization(name="JD Consulting", legal_name="JD Consulting")
    db.add_all([user, org])
    db.commit()
    db.refresh(user)
    db.refresh(org)
    role = Role(name="owner", permissions='["*"]')
    db.add(role)
    db.commit()
    db.refresh(role)
    db.add(OrganizationMember(user_id=user.id, organization_id=org.id, role_id=role.id, status="active"))
    db.commit()

    assert suggest_elfis_email(user) == "jean.dupont@elfis-core.com"
    row, notify = create_professional_email_request(db, user, organization_id=org.id)
    assert row.status == "pending"
    assert row.suggested_email == "jean.dupont@elfis-core.com"
    assert notify["notify_to"] == "urequest@elfis-core.com"

    admin = User(first_name="Admin", last_name="ELF", email="admin@elfis-core.com", status="active")
    db.add(admin)
    db.commit()
    db.refresh(admin)

    activated = activate_professional_email(
        db,
        row.id,
        admin=admin,
        email="jean.dupont@elfis-core.com",
        make_default=True,
    )
    assert activated.status == "active"
    assert activated.email == "jean.dupont@elfis-core.com"
    assert activated.is_default is True

    options = sender_options_for_user(db, user, organization=org)
    assert any(o["kind"] == "professional" and o["is_default"] for o in options)
    assert any(o["kind"] == "personal" for o in options)
