"""Commercial Proposal Engine V1 — sales proposals bounded context.

SalesPilot owns the negotiation lifecycle (draft → sent → accepted/rejected).
PDFs live in ELFIS Vault only. No automatic invoice creation, no automatic
email sending — see conversion.py and service.py docstrings.
"""

from __future__ import annotations
