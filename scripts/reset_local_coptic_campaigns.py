#!/usr/bin/env python3
"""Undo the unreviewed 2026-07-27 Coptic campaigns from their own appendices.

This reset exists so the Greek-script detector can be corrected and both local
passes can be regenerated from the exact pre-pass live fields.  It never reads
HEAD and never touches older work.  The order is significant: filter repair,
Arabic fan, then Greek isolation.
"""
from __future__ import annotations

import os
import re
import tempfile
import unicodedata
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
READING = ROOT / "04-cross-linguistic" / "readings" / "coptic.md"
FILTER_CORRECTION = "COPTIC-CAMPAIGN-FILTER-CORRECTION:"
FAN = "ARABIC-FAN-CAMPAIGN:COPTIC-2026-07-27:"
FAN_SHNFE = "ARABIC-FAN-CAMPAIGN:COPTIC-2026-07-27:SHNFE-REFERRED"
GREEK_PURE = "COPTIC-GREEK-LOAN-ISOLATION:PURE:"
GREEK_MIXED = "COPTIC-GREEK-LOAN-ISOLATION:MIXED:"
BLOCKER = re.compile(r"^-\s*عائق:\s*.+$", re.MULTILINE)
SCAN = re.compile(
    r"^-\s*(?:مسحُ المعاني العربيّة|مسح المعاني العربية):\s*.+$",
    re.MULTILINE,
)
FILTER = re.compile(r"^-\s*المصفاة:\s*.+$", re.MULTILINE)
CLOSURE = re.compile(r"^-\s*حالةُ الإغلاق:\s*.+$", re.MULTILINE)
VERDICT = re.compile(r"^-\s*الحكم \(استكشاف\):\s*.+$", re.MULTILINE)


def atomic_write(path: Path, text: str) -> None:
    fd, temporary = tempfile.mkstemp(
        prefix=path.name + ".", suffix=".tmp", dir=path.parent
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(unicodedata.normalize("NFC", text))
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def replace_field(
    section: str, pattern: re.Pattern[str], replacement: str
) -> str:
    match = pattern.search(section)
    if not match:
        raise ValueError(
            f"missing field {pattern.pattern}: {section.splitlines()[0]}"
        )
    return section[: match.start()] + replacement + section[match.end() :]


def stored(
    appendix: str, label: str, indent: int = 4
) -> str:
    match = re.search(
        rf"^{' ' * indent}- `(- {label}:[^\n]*)`$",
        appendix,
        re.MULTILINE,
    )
    if not match:
        raise ValueError(f"missing stored field {label}")
    return match.group(1)


def revert_filter(section: str) -> tuple[str, bool]:
    marker = f"\n<!-- {FILTER_CORRECTION}"
    at = section.find(marker)
    if at < 0:
        return section, False
    appendix = section[at:]
    match = re.search(
        r"^  - السطر السابق محفوظ: `(- المصفاة:[^\n]*)`$",
        appendix,
        re.MULTILINE,
    )
    if not match:
        raise ValueError(
            f"missing stored filter: {section.splitlines()[0]}"
        )
    base = section[:at].rstrip() + "\n"
    return replace_field(base, FILTER, match.group(1)) + "\n", True


def revert_fan(section: str) -> tuple[str, bool]:
    marker = f"\n<!-- {FAN}"
    at = section.find(marker)
    if at < 0:
        return section, False
    appendix = section[at:]
    base = section[:at].rstrip() + "\n"
    if f"<!-- {FAN_SHNFE} -->" in appendix:
        blocker = re.search(
            r"^  - العائق السابق: `(- عائق:[^\n]*)`$",
            appendix,
            re.MULTILINE,
        )
        closure = re.search(
            r"^  - الإغلاق السابق: `(- حالةُ الإغلاق:[^\n]*)`$",
            appendix,
            re.MULTILINE,
        )
        if not blocker or not closure:
            raise ValueError(
                f"missing stored referral fields: {section.splitlines()[0]}"
            )
        base = replace_field(base, BLOCKER, blocker.group(1))
        base = replace_field(
            base, CLOSURE, closure.group(1)
        )
        return base + "\n", True
    base = replace_field(base, BLOCKER, stored(appendix, "عائق"))
    base = replace_field(
        base,
        SCAN,
        stored(appendix, "(?:مسحُ المعاني العربيّة|مسح المعاني العربية)"),
    )
    base = replace_field(
        base, CLOSURE, stored(appendix, "حالةُ الإغلاق")
    )
    base = replace_field(
        base, VERDICT, stored(appendix, "الحكم \\(استكشاف\\)")
    )
    return base + "\n", True


def revert_greek(section: str) -> tuple[str, str | None]:
    pure_marker = f"\n<!-- {GREEK_PURE}"
    mixed_marker = f"\n<!-- {GREEK_MIXED}"
    pure_at = section.find(pure_marker)
    mixed_at = section.find(mixed_marker)
    if pure_at < 0 and mixed_at < 0:
        return section, None
    if pure_at >= 0:
        appendix = section[pure_at:]
        base = section[:pure_at].rstrip() + "\n"
        base = replace_field(base, BLOCKER, stored(appendix, "عائق"))
        base = replace_field(
            base,
            SCAN,
            stored(
                appendix,
                "(?:مسحُ المعاني العربيّة|مسح المعاني العربية)",
            ),
        )
        base = replace_field(
            base, CLOSURE, stored(appendix, "حالةُ الإغلاق")
        )
        base = replace_field(
            base, VERDICT, stored(appendix, "الحكم \\(استكشاف\\)")
        )
        return base + "\n", "pure"
    return section[:mixed_at].rstrip() + "\n\n", "mixed"


def main() -> int:
    text = READING.read_text(encoding="utf-8")
    output: list[str] = []
    counts = {"filter": 0, "fan": 0, "greek-pure": 0, "greek-mixed": 0}
    for section in re.split(r"(?=^### )", text, flags=re.MULTILINE):
        if not section.startswith("### "):
            output.append(section)
            continue
        section, changed = revert_filter(section)
        counts["filter"] += int(changed)
        section, changed = revert_fan(section)
        counts["fan"] += int(changed)
        section, kind = revert_greek(section)
        if kind:
            counts[f"greek-{kind}"] += 1
        output.append(section)
    atomic_write(READING, "".join(output))
    print(counts)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
