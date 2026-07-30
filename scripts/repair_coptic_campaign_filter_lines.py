#!/usr/bin/env python3
"""Make the live Coptic loan-filter field agree with local campaign decisions.

The judgment appendices already name every donor member.  This repair updates
the authoritative ``المصفاة`` line so a reader cannot see an old "no loan"
claim beside a new Greek or Semitic isolation.  The replaced field is appended
verbatim and the operation is idempotent.
"""
from __future__ import annotations

import os
import re
import tempfile
import unicodedata
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
READING = ROOT / "04-cross-linguistic" / "readings" / "coptic.md"
FILTER = re.compile(r"^-\s*المصفاة:\s*.+$", re.MULTILINE)
FAMILY = re.compile(r"coptic:family:[0-9a-f]+")
GREEK_PURE = "COPTIC-GREEK-LOAN-ISOLATION:PURE:"
GREEK_MIXED = "COPTIC-GREEK-LOAN-ISOLATION:MIXED:"
FAN = "ARABIC-FAN-CAMPAIGN:COPTIC-2026-07-27:"
CORRECTION = "COPTIC-CAMPAIGN-FILTER-CORRECTION"
SEMITIC_CAMEL_FAMILY = "coptic:family:b7c06e332bc9cb9b02a66c98"


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


def correct(section: str) -> tuple[str, str | None]:
    if f"<!-- {CORRECTION}:" in section:
        return section, None
    relevant = (
        f"<!-- {GREEK_PURE}" in section
        or f"<!-- {GREEK_MIXED}" in section
        or (
            SEMITIC_CAMEL_FAMILY in section
            and f"<!-- {FAN}{SEMITIC_CAMEL_FAMILY} -->" in section
        )
    )
    if not relevant:
        return section, None
    kind: str | None = None
    replacement = ""
    match = FILTER.search(section)
    if not match:
        raise ValueError(f"missing Coptic filter: {section.splitlines()[0]}")
    old = match.group(0)
    already_isolates_greek = (
        "يونان" in old
        and any(token in old for token in ("عزل", "قرض", "مسار", "←"))
    )
    if f"<!-- {GREEK_PURE}" in section and not already_isolates_greek:
        kind = "greek-pure"
        replacement = (
            "- المصفاة: كل أعضاء الأسرة ذات مانح يوناني مسمى في حقل الأصل "
            "الفردي في Comprehensive Coptic Lexicon؛ عزلت الأسرة كلها."
        )
    elif f"<!-- {GREEK_MIXED}" in section and not already_isolates_greek:
        kind = "greek-mixed"
        replacement = (
            "- المصفاة: عزلت الأعضاء ذات المانح اليوناني المسمى عضوًا عضوًا؛ "
            "الأعضاء الأخرى لا ترث حكم القرض وتبقى في نطاق القراءة."
        )
    elif (
        SEMITIC_CAMEL_FAMILY in section
        and f"<!-- {FAN}{SEMITIC_CAMEL_FAMILY} -->" in section
    ):
        kind = "semitic-member"
        replacement = (
            "- المصفاة: CCL يصف ϭⲁⲙⲟⲩⲗ C7737 بأنه "
            "`semitisches Lehnwort`؛ عزل العضو بوصفه انتقالًا ساميًا، "
            "وبقيت ϭⲁⲙⲁⲩⲗⲉ C7738 معلقة حتى يثبت مسارها الفردي."
        )
    if not kind:
        return section, None
    updated = section[: match.start()] + replacement + section[match.end() :]
    family = next(iter(set(FAMILY.findall(section))), "legacy")
    appendix = [
        "",
        f"<!-- {CORRECTION}:{kind}:{family} -->",
        "- تصحيح اتساق المصفاة، 2026-07-27:",
        f"  - السطر السابق محفوظ: `{old}`",
        "  - سبب التصحيح: لا يبقى نفي القرض القديم حقلًا حيًا بعد قراءة "
        "حقل الأصل الفردي؛ أما السطر الذي كان يعزل المسار فعلًا فلم يستبدل.",
    ]
    return updated.rstrip() + "\n" + "\n".join(appendix) + "\n", kind


def revert_prior_correction(section: str) -> str:
    marker = f"\n<!-- {CORRECTION}:"
    marker_at = section.find(marker)
    if marker_at < 0:
        return section
    match = re.search(
        r"^  - السطر السابق محفوظ: `(- المصفاة:[^\n]*)`$",
        section[marker_at:],
        re.MULTILINE,
    )
    if not match:
        raise ValueError(
            f"cannot restore Coptic filter: {section.splitlines()[0]}"
        )
    restored = section[:marker_at].rstrip() + "\n"
    current = FILTER.search(restored)
    if not current:
        raise ValueError(f"missing live Coptic filter: {section.splitlines()[0]}")
    restored = (
        restored[: current.start()]
        + match.group(1)
        + restored[current.end() :]
    )
    return restored + "\n"


def main() -> int:
    text = READING.read_text(encoding="utf-8")
    base_parts = [
        revert_prior_correction(section)
        for section in re.split(r"(?=^### )", text, flags=re.MULTILINE)
    ]
    output: list[str] = []
    counts = {"greek-pure": 0, "greek-mixed": 0, "semitic-member": 0}
    for section in base_parts:
        if not section.startswith("### "):
            output.append(section)
            continue
        changed, kind = correct(section)
        output.append(changed)
        if kind:
            counts[kind] += 1
    atomic_write(READING, "".join(output))
    print(counts)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
