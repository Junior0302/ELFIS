"""Interface abstraite HealthProvider."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.system_health.health_schemas import HealthCheckResult


class HealthProvider(ABC):
    """Contrat pour un contrôle de santé de service plateforme."""

    service_id: str
    service_name: str
    category: str

    @abstractmethod
    def check_health(self) -> HealthCheckResult:
        """Exécute le contrôle (sync). Aucun appel réseau externe en RC2.1."""
        ...
