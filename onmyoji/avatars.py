"""Tải và cache ảnh avatar 式神 (`/imgs/shishen/<id>.webp`)."""

from __future__ import annotations

import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Iterable

from . import BASE_URL
from .http import DEFAULT_HEADERS, DEFAULT_TIMEOUT

AVATAR_URL_TEMPLATE = f"{BASE_URL}/imgs/shishen/{{shishen_id}}.webp"
POLITE_DELAY_SECONDS = 0.1
MIN_VALID_BYTES = 256


def download_avatars(
    shishen_ids: Iterable[int],
    target_dir: Path,
    *,
    timeout: float = DEFAULT_TIMEOUT,
) -> tuple[int, tuple[int, ...]]:
    """Tải avatar còn thiếu về `target_dir`.

    Trả về (số ảnh tải mới, tuple id không tải được).
    """
    target_dir.mkdir(parents=True, exist_ok=True)
    fetched = 0
    missing: list[int] = []

    for shishen_id in shishen_ids:
        destination = target_dir / f"{shishen_id}.webp"
        if destination.is_file() and destination.stat().st_size >= MIN_VALID_BYTES:
            continue

        request = urllib.request.Request(
            AVATAR_URL_TEMPLATE.format(shishen_id=shishen_id),
            headers=DEFAULT_HEADERS,
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                payload = response.read()
        except (urllib.error.URLError, TimeoutError, OSError):
            missing.append(shishen_id)
            continue

        if len(payload) < MIN_VALID_BYTES:
            missing.append(shishen_id)
            continue

        destination.write_bytes(payload)
        fetched += 1
        time.sleep(POLITE_DELAY_SECONDS)

    return fetched, tuple(missing)
