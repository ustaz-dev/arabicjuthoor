#!/usr/bin/env python3
"""Apply the dated second third-lens review without erasing prior evidence.

The review accepted the remaining positive cards except for 17 named cards.
This pass:

1. returns those 17 cards to SOURCE-GAP while preserving their old live
   fields in a dated historical appendix;
2. repairs stale live Arabic-fan scan lines on accepted READY cards when a
   later appendix in the same card already names two old Arabic sources;
3. writes a machine-readable audit cache.

It never changes a linguistic instrument, shift row, proof registration, or
the source evidence carried by a card.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import tempfile
import unicodedata
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
READINGS = ROOT / "04-cross-linguistic" / "readings"
CACHE = ROOT / "cache" / "recovery_pipeline" / "third-lens-round-two.json"
DATE = "2026-07-25"
MARKER = "THIRD-LENS-ROUND-TWO"

LINK_VERDICTS = {
    "ROOT-TRACE",
    "ROOT-ECHO",
    "NUCLEUS-TRACE",
    "NUCLEUS-ECHO",
    "FLOOR-TRACE",
}

# The first 16 are the table in the first third-lens audit.  The seventeenth
# is the additional Hebrew card named in the second-round audit.
REJECTED = {
    "aramaic.md": (
        "aramaic:family:553ddd9a98b76c1f829cd6c5",
        "aramaic:family:5fdc083c38af3f628dabd308",
        "aramaic:family:02812a94f02b083c91053bcb",
        "aramaic:family:50973cb49a325ee0f85180a8",
        "aramaic:family:781d7ba70c68c9f96abf697d",
        "aramaic:family:4e684dd08a53eb41592ad9f7",
        "aramaic:family:59d35ee0f532ff769047e21e",
        "aramaic:family:8b37714117691130a108b931",
    ),
    "coptic.md": ("ϣⲓⲕⲉ وϭⲓⲛϣⲓⲕⲉ",),
    "hebrew.md": (
        "hebrew:family:de8c3313b806ae8cc5bfdf33",
        "hebrew:family:d68aa11b6dc337a5ce644c02",
        "hebrew:family:8fd3002ca26b804067cc33a7",
        "hebrew:family:14c0e576b3e8fec13f8bac12",
        "hebrew:family:02912c1cf41101f2836df6ed",
        "hebrew:family:32d76a601129e2faab838c32",
        "hebrew:family:9b66a00d23300e96da1a993b",
    ),
    "welsh.md": ("`sgogi`",),
}

SOURCE_ALIASES = (
    ("لسان العرب لابن منظور", ("لسان العرب لابن منظور", "*لسان العرب*", "لسان العرب")),
    ("تاج العروس لمرتضى الزبيدي", ("تاج العروس لمرتضى الزبيدي", "*تاج العروس*", "تاج العروس")),
    (
        "تاج اللغة وصحاح العربية للجوهري",
        ("تاج اللغة وصحاح العربية للجوهري", "صحاح العربية للجوهري", "الصحاح للجوهري"),
    ),
    (
        "المحكم والمحيط الأعظم لابن سيده",
        ("المحكم والمحيط الأعظم لابن سيده", "المحكم والمحيط الأعظم", "المحكم"),
    ),
    ("كتاب العين للخليل", ("كتاب العين للخليل", "العين للخليل", "كتاب العين")),
    ("أساس البلاغة للزمخشري", ("أساس البلاغة للزمخشري", "أساس البلاغة")),
)

NEGATIVE_SCAN_HINTS = (
    "لم يجر",
    "لم يُجر",
    "لم تجر",
    "لم تُجر",
    "غير منفذ",
    "غير منفّذ",
    "غير مفحوص",
    "لم يكتمل",
    "لم تكتمل",
)


def atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(
        prefix=path.name + ".", suffix=".tmp", dir=path.parent
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
        os.replace(temp_name, path)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def split_sections(text: str) -> list[str]:
    return re.split(r"(?=^### )", text, flags=re.M)


def is_card(section: str) -> bool:
    return section.startswith("### بطاقة") or section.startswith("### إعادةُ توسيم")


def title(section: str) -> str:
    return section.splitlines()[0].strip()


def first_line(section: str, label: str) -> str:
    patterns = {
        "عائق:": r"^- عائق:[^\n]*$",
        "مسحُ المعاني العربيّة:": (
            r"^- (?:مسحُ المعاني العربيّة|مسح المعاني العربية):[^\n]*$"
        ),
        "حالةُ الإغلاق:": (
            r"^- (?:حالةُ الإغلاق|حالة الإغلاق):[^\n]*$"
        ),
        "الحكم (استكشاف):": r"^- الحكم \(استكشاف\):[^\n]*$",
    }
    match = re.search(patterns[label], section, re.M)
    return match.group(0) if match else ""


def blocker(section: str) -> str:
    match = re.search(r"^- عائق:\s*النوع=([A-Z\-]+)", section, re.M)
    return match.group(1) if match else ""


def verdict(section: str) -> str:
    match = re.search(
        r"^- الحكم \(استكشاف\):\s*([A-Z\-]+)", section, re.M
    )
    return match.group(1) if match else ""


def named_sources(section: str) -> list[str]:
    found: list[str] = []
    for canonical, aliases in SOURCE_ALIASES:
        if any(alias in section for alias in aliases):
            found.append(canonical)
    return found


def replace_first_line(section: str, old: str, new: str) -> str:
    if not old:
        raise ValueError(f"missing live field in {title(section)}")
    return section.replace(old, new, 1)


def target_key(file_name: str, section: str) -> str | None:
    for key in REJECTED.get(file_name, ()):
        if key in title(section):
            return key
    return None


def return_to_hold(
    file_name: str, section: str, key: str
) -> tuple[str, dict[str, object]]:
    if f"<!-- {MARKER}:RETURN:{key} -->" in section:
        return section, {"key": key, "already_applied": True}
    if blocker(section) != "READY" or verdict(section) not in LINK_VERDICTS:
        raise ValueError(
            f"named rejected card is not a live positive READY card: "
            f"{file_name}: {title(section)}"
        )

    old_blocker = first_line(section, "عائق:")
    old_scan = first_line(section, "مسحُ المعاني العربيّة:")
    old_closure = first_line(section, "حالةُ الإغلاق:")
    old_verdict = first_line(section, "الحكم (استكشاف):")
    sources = named_sources(section)

    reason = (
        "قرار المراجعة الثالثة في الجولة الثانية؛ يلزم إثبات مروحة "
        "مصدرين عربيين قديمين مستقلة للبطاقة نفسها قبل إعادة الحكم"
    )
    updated = replace_first_line(
        section,
        old_blocker,
        f"- عائق: النوع=SOURCE-GAP؛ يتطلب={reason}؛",
    )
    updated = replace_first_line(
        updated,
        old_scan,
        "- مسحُ المعاني العربيّة: أعادت المراجعة الثالثة البطاقة إلى "
        "التعليق؛ الأدلة والمصادر المذكورة أدناه محفوظة، لكنها لا تُعد "
        "إجازة نهائية لهذه البطاقة.",
    )
    updated = replace_first_line(
        updated,
        old_closure,
        "- حالةُ الإغلاق: SOURCE-GAP؛ أعادتها المراجعة الثالثة إلى التعليق.",
    )
    updated = replace_first_line(
        updated,
        old_verdict,
        "- الحكم (استكشاف): غير صادر؛ الحكم الموجب السابق محفوظ تاريخيًا "
        "ولا يدخل العد حتى إعادة الإجازة.",
    )
    history = (
        f"\n<!-- {MARKER}:RETURN:{key} -->\n"
        f"- ملحق قرار المراجعة الثالثة، {DATE}:\n"
        "  - المصير الجاري: `SOURCE-GAP`.\n"
        f"  - المصادر القديمة المسماة المحفوظة: "
        f"{' + '.join(sources) if sources else 'لا مصدرين مسميين في البطاقة'}.\n"
        "  - الحقول الحاكمة السابقة، محفوظة بلا محو:\n"
        f"    - `{old_blocker}`\n"
        f"    - `{old_scan}`\n"
        f"    - `{old_closure}`\n"
        f"    - `{old_verdict}`\n"
    )
    return updated.rstrip() + history + "\n", {
        "key": key,
        "file": file_name,
        "title": title(section),
        "sources_preserved": sources,
    }


def refer_duplicate(
    file_name: str, section: str, key: str
) -> tuple[str, dict[str, object]]:
    marker = f"<!-- {MARKER}:DUPLICATE-REFERRAL:{key} -->"
    if marker in section:
        return section, {"key": key, "already_applied": True}
    old_blocker = first_line(section, "عائق:")
    old_scan = first_line(section, "مسحُ المعاني العربيّة:")
    old_closure = first_line(section, "حالةُ الإغلاق:")
    old_verdict = first_line(section, "الحكم (استكشاف):")
    updated = replace_first_line(
        section,
        old_blocker,
        "- عائق: النوع=REFERRED؛ يتطلب=بطاقة حكم مكررة في الأسرة نفسها؛ "
        "أحيلت إلى البطاقة الأولى المعادة للمراجعة ولا تعد صلة ثانية؛",
    )
    updated = replace_first_line(
        updated,
        old_scan,
        "- مسحُ المعاني العربيّة: محفوظ في البطاقة، لكن هذه النسخة المكررة "
        "لا تصدر حكمًا مستقلًا.",
    )
    updated = replace_first_line(
        updated,
        old_closure,
        "- حالةُ الإغلاق: REFERRED؛ إحالة بنيوية بلا حكم نسب.",
    )
    updated = replace_first_line(
        updated,
        old_verdict,
        "- الحكم (استكشاف): غير صادر؛ لا تضاعف بطاقة الأسرة الواحدة.",
    )
    history = (
        f"\n{marker}\n"
        f"- ملحق إزالة التكرار، {DATE}:\n"
        "  - المصير الجاري: `REFERRED`.\n"
        "  - الحقول الحاكمة السابقة، محفوظة بلا محو:\n"
        f"    - `{old_blocker}`\n"
        f"    - `{old_scan}`\n"
        f"    - `{old_closure}`\n"
        f"    - `{old_verdict}`\n"
    )
    return updated.rstrip() + history + "\n", {
        "key": key,
        "file": file_name,
        "title": title(section),
    }


def repair_scan(
    file_name: str, section: str
) -> tuple[str, dict[str, object] | None]:
    if blocker(section) != "READY" or verdict(section) not in LINK_VERDICTS:
        return section, None
    if f"<!-- {MARKER}:SCAN-REPAIR -->" in section:
        return section, None
    old_scan = first_line(section, "مسحُ المعاني العربيّة:")
    if not old_scan or not any(hint in old_scan for hint in NEGATIVE_SCAN_HINTS):
        return section, None
    sources = named_sources(section)
    if len(sources) < 2:
        return section, None
    new_scan = (
        "- مسحُ المعاني العربيّة: مروحة مصدرين عربيين قديمين مثبتة في "
        f"ملحق البطاقة: {' + '.join(sources[:2])}؛ حُدث هذا الحقل الحي "
        "ليطابق السجل التفصيلي المحفوظ أدناه."
    )
    updated = replace_first_line(section, old_scan, new_scan)
    updated = (
        updated.rstrip()
        + f"\n<!-- {MARKER}:SCAN-REPAIR -->\n"
        + f"- سجل تحديث الحقل الحي، {DATE}: `{old_scan}`\n"
    )
    return updated, {
        "file": file_name,
        "title": title(section),
        "sources": sources[:2],
    }


def process(check: bool) -> dict[str, object]:
    returns: list[dict[str, object]] = []
    duplicate_referrals: list[dict[str, object]] = []
    scan_repairs: list[dict[str, object]] = []
    seen_keys: set[str] = set()
    verified_return_keys: set[str] = set()
    files_changed: list[str] = []

    for path in sorted(READINGS.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        output: list[str] = []
        changed = False
        for section in split_sections(text):
            if not is_card(section):
                output.append(section)
                continue
            key = target_key(path.name, section)
            if key and f"<!-- {MARKER}:RETURN:{key} -->" in section:
                if blocker(section) != "SOURCE-GAP" or verdict(section):
                    raise ValueError(
                        f"applied return drifted: {path.name}: {title(section)}"
                    )
                seen_keys.add(key)
                verified_return_keys.add(key)
                output.append(section)
                continue
            if key and f"<!-- {MARKER}:DUPLICATE-REFERRAL:{key} -->" in section:
                if blocker(section) != "REFERRED" or verdict(section):
                    raise ValueError(
                        f"duplicate referral drifted: {path.name}: {title(section)}"
                    )
                output.append(section)
                continue
            if key and blocker(section) == "READY" and verdict(section) in LINK_VERDICTS:
                if key in seen_keys:
                    updated, record = refer_duplicate(path.name, section, key)
                    if not record.get("already_applied"):
                        duplicate_referrals.append(record)
                else:
                    seen_keys.add(key)
                    updated, record = return_to_hold(path.name, section, key)
                    if not record.get("already_applied"):
                        returns.append(record)
                changed = changed or updated != section
                output.append(updated)
                continue
            updated, repair = repair_scan(path.name, section)
            if repair:
                scan_repairs.append(repair)
            changed = changed or updated != section
            output.append(updated)
        rebuilt = "".join(output)
        if unicodedata.normalize("NFC", rebuilt) != rebuilt:
            raise ValueError(f"NFC drift in {path}")
        if changed:
            files_changed.append(path.name)
            if not check:
                atomic_write(path, rebuilt)

    expected = {key for keys in REJECTED.values() for key in keys}
    missing = sorted(expected - seen_keys)
    if missing:
        raise ValueError("rejected targets not found as live READY positives: " + ", ".join(missing))

    payload: dict[str, object] = {
        "schema": "third-lens-round-two-application-v1",
        "date": DATE,
        "status": "CHECK-ONLY" if check else "APPLIED",
        "returned_to_hold": len(returns),
        "returns_verified": len(verified_return_keys),
        "duplicate_referrals": len(duplicate_referrals),
        "scan_lines_repaired": len(scan_repairs),
        "files_changed": files_changed,
        "returns": returns,
        "duplicate_referral_records": duplicate_referrals,
        "scan_repairs": scan_repairs,
    }
    if not check:
        atomic_write(
            CACHE,
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        )
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    payload = process(args.check)
    print(
        json.dumps(
            {
                "returned_to_hold": payload["returned_to_hold"],
                "returns_verified": payload["returns_verified"],
                "duplicate_referrals": payload["duplicate_referrals"],
                "scan_lines_repaired": payload["scan_lines_repaired"],
                "files_changed": payload["files_changed"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
