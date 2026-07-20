"""Registry des handlers de jobs — un job_name = un handler en V1."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from app.jobs.job_exceptions import JobUnknownTypeError
from app.jobs.job_types import ALL_KNOWN_JOB_NAMES, IMPLEMENTED_JOB_NAMES

if TYPE_CHECKING:
    from app.jobs.job_context import JobContext
    from app.jobs.job_models import ElfisJob
    from app.jobs.job_schemas import JobExecutionResult


class JobHandler(ABC):
    handler_name: str
    job_name: str

    @abstractmethod
    def handle(self, job: "ElfisJob", context: "JobContext") -> "JobExecutionResult":
        raise NotImplementedError


class JobHandlerRegistry:
    def __init__(self) -> None:
        self._by_job: dict[str, JobHandler] = {}
        self._by_handler: dict[str, JobHandler] = {}

    def register(self, *, job_name: str | None = None, handler: JobHandler) -> None:
        name = (handler.handler_name or "").strip()
        if not name:
            raise ValueError("handler_name requis")
        jn = (job_name or handler.job_name or "").strip()
        if not jn:
            raise ValueError("job_name requis")
        if jn not in ALL_KNOWN_JOB_NAMES:
            raise JobUnknownTypeError(jn)
        if jn in self._by_job and self._by_job[jn] is not handler:
            raise ValueError(f"Handler déjà enregistré pour {jn}")
        if name in self._by_handler and self._by_handler[name] is not handler:
            raise ValueError(f"handler_name déjà enregistré: {name}")
        self._by_job[jn] = handler
        self._by_handler[name] = handler

    def get(self, job_name: str) -> JobHandler:
        handler = self._by_job.get(job_name)
        if handler is None:
            raise JobUnknownTypeError(job_name)
        return handler

    def has(self, job_name: str) -> bool:
        return job_name in self._by_job

    def is_known(self, job_name: str) -> bool:
        return job_name in ALL_KNOWN_JOB_NAMES

    def is_implemented(self, job_name: str) -> bool:
        return job_name in IMPLEMENTED_JOB_NAMES and job_name in self._by_job

    def clear(self) -> None:
        self._by_job.clear()
        self._by_handler.clear()


default_job_registry = JobHandlerRegistry()
