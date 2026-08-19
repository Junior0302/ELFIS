"""Types observabilité."""

from __future__ import annotations


class MetricNames:
    HTTP_REQUESTS = "http_requests_total"
    HTTP_DURATION = "http_request_duration_ms"
    HTTP_ERRORS = "http_errors_total"
    HTTP_RATE_LIMIT = "http_rate_limit_hits"
    JOBS = "jobs_total"
    EVENTS = "events_total"
    AI_EXECUTIONS = "ai_executions_total"
    DELIVERY = "delivery_total"
    BILLING = "billing_events_total"
    SEARCH = "search_queries_total"
