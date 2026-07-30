#!/usr/bin/env python3
"""Repair lane A batch 01 headings and structured READY blockers in place."""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "04-cross-linguistic" / "readings" / "aramaic.md"
DB = ROOT / "cache" / "recovery_pipeline" / "inventory-v5.sqlite"
START = "<!-- LANE-A-ARAMAIC-DISCOVERY-2026-07-29:START -->"
END = "<!-- LANE-A-ARAMAIC-DISCOVERY-2026-07-29:END -->"
CARD = re.compile(
    r"(?ms)^### بطاقة اكتشاف آرامية أ 1\.(?P<rank>\d+): "
    r"`(?P<entry>[^`]+)`، (?P<head>[^\n]+)\n"
    r"- عائق: النوع=لا يوجد؛ يتطلب=[^\n]+\n"
)


def main() -> None:
    text = TARGET.read_text(encoding="utf-8")
    if START not in text or END not in text:
        raise SystemExit("حدود الدفعة غير موجودة")
    before, remainder = text.split(START, 1)
    batch, after = remainder.split(END, 1)
    entry_ids = [match.group("entry") for match in CARD.finditer(batch)]
    if len(entry_ids) != 30:
        raise SystemExit(f"عدد البطاقات القابلة للإصلاح غير متوقع: {len(entry_ids)}")

    connection = sqlite3.connect(DB)
    connection.row_factory = sqlite3.Row
    placeholders = ",".join("?" for _ in entry_ids)
    family_ids = {
        str(row["entry_id"]): str(row["family_id"])
        for row in connection.execute(
            f"select entry_id, family_id from family_members "
            f"where entry_id in ({placeholders})",
            entry_ids,
        )
    }
    connection.close()
    if len(family_ids) != len(set(entry_ids)):
        raise SystemExit("تعذر تعيين أسرة لكل عضو")

    def replace(match: re.Match[str]) -> str:
        rank = match.group("rank")
        entry_id = match.group("entry")
        head = match.group("head")
        family_id = family_ids[entry_id]
        if not family_id.startswith("aramaic:family:"):
            raise SystemExit(f"معرف أسرة غير صالح: {family_id}")
        return (
            f"### بطاقة: `{family_id}`، {head}، دفعة الاكتشاف الآرامية أ 1، "
            f"الرتبة {rank}، العضو `{entry_id}`\n"
            f"- عائق: النوع=READY؛ يتطلب=المراجعة المضادة الثالثة؛ "
            f"العضو=`{entry_id}`.\n"
        )

    repaired, count = CARD.subn(replace, batch)
    if count != 30:
        raise SystemExit(f"لم تصلح البطاقات كلها: {count}")
    TARGET.write_text(
        before + START + repaired + END + after,
        encoding="utf-8",
        newline="\n",
    )
    print("repaired=30 family_ids=30 blockers=30")


if __name__ == "__main__":
    main()
