from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_BACKEND_DIR = Path(__file__).resolve().parent.parent
_DEFAULT_DB = (_BACKEND_DIR / "comptapilot.db").as_posix()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_BACKEND_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    openai_api_key: str = ""
    openai_chat_model: str = "gpt-4o-mini"
    app_env: str = "development"
    database_url: str = f"sqlite:///{_DEFAULT_DB}"
    storage_dir: str = str(_BACKEND_DIR / "storage")
    # "*" = accessible depuis n'importe quel appareil du réseau (MVP LAN)
    cors_origins: str = "*"
    app_name: str = "ELFIS Core"
    product_name: str = "ComptaPilot IA"
    jwt_secret: str = "comptapilot-elfis-dev-secret-change-me"
    auth_required: bool = True
    firebase_web_api_key: str = ""
    firebase_project_id: str = ""
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_price_pro: str = ""
    stripe_trial_days: int = 14
    stripe_past_due_grace_days: int = 3
    subscription_terms_version: str = "v1"
    subscription_cron_token: str = ""
    frontend_url: str = "http://localhost:5173"
    # URL publique HTTPS de l’API (Render) — pour avatars / liens absolus
    public_api_url: str = ""
    platform_admin_emails: str = ""
    # E-mail transactionnel : clé Brevo = plateforme uniquement (jamais par org)
    brevo_api_key: str = ""
    brevo_webhook_secret: str = ""
    # Adresse technique authentifiée (ex. documents@elfiscore.com)
    platform_email_from: str = ""
    platform_email_from_name: str = "ComptaPilot"
    # Alias rétrocompatibles
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""
    smtp_use_tls: bool = True
    # OAuth boîtes org + chiffrement des jetons
    email_credentials_encryption_key: str = ""
    google_client_id: str = ""
    google_client_secret: str = ""
    google_oauth_redirect_uri: str = ""
    microsoft_client_id: str = ""
    microsoft_client_secret: str = ""
    microsoft_tenant_id: str = "common"
    microsoft_oauth_redirect_uri: str = ""

    @property
    def effective_platform_from(self) -> str:
        return (self.platform_email_from or self.smtp_from or "").strip()

    @property
    def effective_platform_from_name(self) -> str:
        return (self.platform_email_from_name or self.product_name or "ComptaPilot").strip()

    @staticmethod
    def _clean_secret(value: str) -> str:
        """Enlève guillemets / espaces / retours ligne collés depuis Render."""
        cleaned = (value or "").strip()
        if len(cleaned) >= 2 and cleaned[0] == cleaned[-1] and cleaned[0] in {'"', "'"}:
            cleaned = cleaned[1:-1].strip()
        if cleaned.lower().startswith("bearer "):
            cleaned = cleaned[7:].strip()
        return cleaned.replace("\r", "").replace("\n", "").strip()

    @model_validator(mode="after")
    def validate_production_security(self):
        self.stripe_secret_key = self._clean_secret(self.stripe_secret_key)
        self.stripe_webhook_secret = self._clean_secret(self.stripe_webhook_secret)
        self.stripe_price_pro = self.stripe_price_pro.strip()
        self.brevo_api_key = self._clean_secret(self.brevo_api_key)
        self.smtp_user = self._clean_secret(self.smtp_user)
        self.smtp_password = self._clean_secret(self.smtp_password)
        self.smtp_host = (self.smtp_host or "").strip()
        self.platform_email_from = (self.platform_email_from or "").strip()
        self.smtp_from = (self.smtp_from or "").strip()
        self.frontend_url = self.frontend_url.strip() or "http://localhost:5173"
        if self.app_env.lower() != "production":
            return self
        if self.jwt_secret == "comptapilot-elfis-dev-secret-change-me" or len(self.jwt_secret) < 32:
            raise ValueError("JWT_SECRET doit contenir au moins 32 caractères en production")
        if self.cors_origins.strip() == "*":
            raise ValueError("CORS_ORIGINS doit lister les domaines autorisés en production")
        if not self.firebase_web_api_key or not self.firebase_project_id:
            raise ValueError("Firebase doit être configuré en production")
        return self

    @property
    def cors_origin_list(self) -> list[str]:
        raw = [o.strip() for o in self.cors_origins.split(",") if o.strip()]
        return raw or ["*"]

    @property
    def storage_path(self) -> Path:
        path = Path(self.storage_dir)
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def platform_admin_email_set(self) -> set[str]:
        return {
            email.strip().lower()
            for email in self.platform_admin_emails.split(",")
            if email.strip()
        }


settings = Settings()
