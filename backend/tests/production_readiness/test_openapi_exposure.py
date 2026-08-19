"""OpenAPI — politique production."""

from __future__ import annotations

from app.main import app
from app.security.security_config import is_production


def test_openapi_exposure_policy():
    if is_production():
        assert app.docs_url is None
        assert app.redoc_url is None
        assert app.openapi_url is None
    else:
        # Recette / dev : docs disponibles
        assert app.docs_url == "/docs" or app.docs_url is None
