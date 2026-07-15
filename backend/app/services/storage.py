from __future__ import annotations

import uuid
from pathlib import Path

import aiofiles

from app.config import settings


async def save_upload(filename: str, content: bytes) -> Path:
    safe_name = Path(filename).name
    unique = f"{uuid.uuid4().hex[:12]}_{safe_name}"
    dest = settings.storage_path / unique
    async with aiofiles.open(dest, "wb") as f:
        await f.write(content)
    return dest


def resolve_stored(path_str: str) -> Path:
    path = Path(path_str)
    if not path.is_absolute():
        path = Path.cwd() / path
    return path