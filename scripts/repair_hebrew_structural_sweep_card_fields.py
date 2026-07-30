#!/usr/bin/env python3
"""Restore the two literal RECOVERY-v2 fields in Hebrew structural sweep 08."""
from __future__ import annotations

import argparse
import tempfile
import unicodedata
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
READING = ROOT / "04-cross-linguistic" / "readings" / "hebrew.md"
START = "<!-- HEBREW-EXPLICIT-STRUCTURAL-CLOSURES-08 -->"
END = "<!-- HEBREW-EXPLICIT-STRUCTURAL-CLOSURES-08:END -->"
PROTOCOL = "- إصدارُ البروتوكول: RECOVERY-v2 (2026-07-14)"
BRANCH = "- الكلمةُ في الفرع: الأعضاء المسماة أدناه برسومها وتصنيفاتها من Kaikki Hebrew؛ لا تدمج في كلمة واحدة."
OLDEST = "- أقدمُ صورةٍ مستعادة: رسم كل عضو في لقطة المصدر المثبتة أدناه؛ لا استعادة صرفية ولا تعرية في هذا الكنس."
HEADING = "### بطاقة:"
OLD_OBSTACLE = "- عائق: النوع=STRUCTURAL-SWEEP؛ يتطلب=المراجعة المضادة الثالثة قبل إدخال الإغلاقات في السجل المركزي."
NEW_OBSTACLE = OLD_OBSTACLE.rstrip(".") + "؛ الأعضاء=كل عضو مسمى أدناه."


def atomic_write(path: Path, text: str) -> None:
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", newline="\n", dir=path.parent, delete=False
    ) as handle:
        handle.write(unicodedata.normalize("NFC", text))
        temporary = Path(handle.name)
    temporary.replace(path)


def repaired_text(text: str) -> tuple[str, int]:
    if START not in text or END not in text:
        raise ValueError("Hebrew structural sweep markers are missing")
    before, rest = text.split(START, 1)
    block, after = rest.split(END, 1)
    cards = block.split(HEADING)
    repaired = 0
    output = [cards[0]]
    for raw in cards[1:]:
        card = HEADING + raw
        if BRANCH not in card or OLDEST not in card:
            if PROTOCOL not in card:
                raise ValueError("structural card lacks the protocol field")
            card = card.replace(
                PROTOCOL,
                "\n".join((PROTOCOL, BRANCH, OLDEST)),
                1,
            )
            repaired += 1
        if OLD_OBSTACLE in card and NEW_OBSTACLE not in card:
            card = card.replace(OLD_OBSTACLE, NEW_OBSTACLE, 1)
            repaired += 1
        output.append(card)
    return before + START + "".join(output) + END + after, repaired


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    text = READING.read_text(encoding="utf-8")
    updated, repaired = repaired_text(text)
    if args.check:
        if updated != text:
            print(f"STALE: {repaired} Hebrew structural cards need literal fields")
            return 1
        print("CLEAN: Hebrew structural sweep literal card fields")
        return 0
    if repaired == 0:
        print("Hebrew structural sweep literal fields: already current")
        return 0
    atomic_write(READING, updated)
    print(f"repaired Hebrew structural sweep cards: {repaired}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
