"""Tải và cache ảnh avatar 式神 (`/imgs/shishen/<id>.webp`)."""

from __future__ import annotations

import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Iterable, Mapping

from . import BASE_URL
from .http import DEFAULT_HEADERS, DEFAULT_TIMEOUT

AVATAR_URL_TEMPLATE = f"{BASE_URL}/imgs/shishen/{{shishen_id}}.webp"
POLITE_DELAY_SECONDS = 0.1
MIN_VALID_BYTES = 256

# Icon 御魂 nằm trên CDN của NetEase, nơi từ chối (403) mọi request mang Referer
# trỏ về yysrank.win. Gửi kèm User-Agent nhưng bỏ Referer.
EXTERNAL_HEADERS = {
    key: value for key, value in DEFAULT_HEADERS.items() if key not in {"Referer", "X-Requested-With"}
}


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


def download_yuhun_icons(
    yuhun_ids: Iterable[int],
    yuhun_map: Mapping[int, Mapping[str, str]],
    target_dir: Path,
    *,
    timeout: float = DEFAULT_TIMEOUT,
) -> tuple[int, tuple[int, ...]]:
    """Tải icon 御魂 về `target_dir`, đặt tên `<id><ext>`.

    `icon` trong asset có 3 dạng: đường dẫn tương đối trên yysrank.win, URL
    tuyệt đối trên CDN NetEase, hoặc rỗng (bộ 2 món — bỏ qua, không tính là lỗi).
    Trả về (số icon tải mới, tuple id không tải được).
    """
    target_dir.mkdir(parents=True, exist_ok=True)
    fetched = 0
    missing: list[int] = []

    for yuhun_id in yuhun_ids:
        icon = (yuhun_map.get(yuhun_id) or {}).get("icon") or ""
        if not icon:
            continue

        is_external = icon.startswith("http")
        url = icon if is_external else f"{BASE_URL}{icon}"
        # CDN NetEase trả 403 nếu có Referer trỏ về yysrank.win — chính vì vậy
        # site đặt referrerpolicy="no-referrer" trên thẻ <img>.
        headers = EXTERNAL_HEADERS if is_external else DEFAULT_HEADERS
        suffix = ".webp" if url.endswith(".webp") else ".png"
        destination = target_dir / f"{yuhun_id}{suffix}"
        if destination.is_file() and destination.stat().st_size >= MIN_VALID_BYTES:
            continue

        request = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                payload = response.read()
        except (urllib.error.URLError, TimeoutError, OSError):
            missing.append(yuhun_id)
            continue

        if len(payload) < MIN_VALID_BYTES:
            missing.append(yuhun_id)
            continue

        destination.write_bytes(payload)
        fetched += 1
        time.sleep(POLITE_DELAY_SECONDS)

    return fetched, tuple(missing)
