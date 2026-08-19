"""Comptes de recette — jamais seedés en production."""

from __future__ import annotations

import inspect

from app.services.auth import seed_auth
from tests.functional.catalog import USERS
from tests.functional.seed import assert_safe_environment


def test_auth_002_seed_auth_does_not_create_recette_accounts():
    """seed_auth runtime = catalogue RBAC uniquement, pas les comptes @test.elfis.local."""
    src = inspect.getsource(seed_auth)
    for spec in USERS.values():
        assert spec.email not in src
    assert "test.elfis.local" not in src
    assert "ElfisRecette" not in src


def test_auth_002b_functional_seed_refuses_prod_and_prod_like_url():
    raised = False
    try:
        assert_safe_environment(
            database_url="postgresql://u:p@db/elfis_production",
            environment="staging",
        )
    except RuntimeError:
        raised = True
    assert raised
