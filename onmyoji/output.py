"""Chuẩn hoá bản ghi và ghi ra JSON / CSV."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

CSV_COLUMNS = (
    "rank",
    "team_ids",
    "team_names",
    "win_rate",
    "pick_rate",
    "total",
    "duration",
)


def normalize_row(
    row: Mapping[str, Any],
    rank: int,
    shishen_names: Mapping[int, str],
) -> Mapping[str, Any]:
    """Trả về bản ghi mới đã bổ sung tên 式神 — không sửa `row` gốc."""
    team_ids = tuple(int(sid) for sid in (row.get("team") or []))
    team_names = tuple(shishen_names.get(sid, f"#{sid}") for sid in team_ids)

    return {
        "rank": rank,
        "team_ids": team_ids,
        "team_names": team_names,
        "win_rate": float(row.get("win_rate") or 0.0),
        "pick_rate": float(row.get("pick_rate") or 0.0),
        "total": int(row.get("total") or 0),
        "duration": float(row.get("duration") or 0.0),
    }


def write_json(path: Path, metadata: Mapping[str, Any], rows: Sequence[Mapping[str, Any]]) -> None:
    document = {"metadata": dict(metadata), "count": len(rows), "teams": list(rows)}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(document, ensure_ascii=False, indent=2, default=list),
        encoding="utf-8",
    )


def write_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "rank": row["rank"],
                    "team_ids": " ".join(str(sid) for sid in row["team_ids"]),
                    "team_names": " / ".join(row["team_names"]),
                    "win_rate": f"{row['win_rate'] * 100:.2f}",
                    "pick_rate": f"{row['pick_rate'] * 100:.4f}",
                    "total": row["total"],
                    "duration": round(row["duration"]),
                }
            )
