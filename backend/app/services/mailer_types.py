from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MailAttachment:
    filename: str
    content: bytes
    maintype: str = "application"
    subtype: str = "octet-stream"
