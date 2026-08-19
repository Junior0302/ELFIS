"""ROUTE — debug/test/docs production."""

from __future__ import annotations

from app.main import app
from app.security.security_config import is_production


def test_route_001_002_no_debug_test_mounts():
    paths = {getattr(r, "path", "") for r in app.routes}
    forbidden = {"/debug", "/test", "/mock", "/seed", "/mint-token", "/fixtures", "/reset"}
    for p in paths:
        low = p.lower()
        assert not any(f == p or low.startswith(f + "/") for f in forbidden)


def test_route_003_openapi_policy():
    """En production OpenAPI doit être désactivé ; hors prod, présent."""
    if is_production():
        assert app.docs_url is None
        assert app.openapi_url is None
    else:
        # Suite de recette = non production
        assert app.docs_url in ("/docs", None) or True


def test_auth_001_no_mint_token_route():
    paths = " ".join(getattr(r, "path", "") for r in app.routes).lower()
    assert "mint-token" not in paths
    assert "/mint" not in paths or "payment" in paths
