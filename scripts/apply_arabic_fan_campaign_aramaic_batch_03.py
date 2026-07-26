#!/usr/bin/env python3
"""Apply the third Aramaic fan batch: source-anchored inherited vocabulary."""
from __future__ import annotations

from collections import Counter
import json
import re
import sqlite3
import sys
import tempfile
import unicodedata
from pathlib import Path

from search_arabic_root_senses import DEFAULT_RESOURCES, root_sense_fan


ROOT = Path(__file__).resolve().parents[1]
READING = ROOT / "04-cross-linguistic" / "readings" / "aramaic.md"
DB = ROOT / "cache" / "recovery_pipeline" / "inventory-v5.sqlite"
AUDIT_JSON = (
    ROOT / "cache" / "recovery_pipeline"
    / "arabic-fan-campaign-aramaic-batch-03.json"
)
AUDIT_MD = (
    ROOT / "05-audits"
    / "2026-07-25-arabic-fan-campaign-aramaic-batch-03.md"
)
DATE = "2026-07-25"
BATCH = "ARAMAIC-03"
CARD_HEADING = re.compile(r"^### (?:بطاقة|إعادةُ توسيم).*$", re.MULTILINE)
FAMILY_ID = re.compile(r"aramaic:family:[0-9a-f]+")


# family: (Arabic fan root, verdict, named semantic bridge)
POSITIVES = {
    "aramaic:family:d7aef9c102205f7fdaf5df59":
        ("بطل", "ROOT-TRACE", "البطلان والتعطيل يقابلان التوقف والإلغاء"),
    "aramaic:family:fbed84a3aa934ba000596f46":
        ("فتل", "ROOT-TRACE", "الفتل والجدل يقابلان الخيط المفتول والفتيلة"),
    "aramaic:family:fecc4482328376b7a07e4a18":
        ("روح", "ROOT-TRACE", "الروح تقابل الروح والشبح في السلسلة المسماة"),
    "aramaic:family:db7ad2fac189d3e03b86608e":
        ("عين", "ROOT-TRACE", "العين الباصرة وعين الماء تقابلان المعنيين نفسيهما"),
    "aramaic:family:9904daf94f30c371d4c906c5":
        ("كنف", "ROOT-TRACE", "الكنف بمعنى الجانب والناحية يقابل الجانب والحافة"),
    "aramaic:family:e615eb75b7f4cfd82453b5d9":
        ("رجل", "ROOT-TRACE", "الرجل والقدم تقابلان الساق والقدم"),
    "aramaic:family:cc015a78a6d7bf3a228d63ba":
        ("جمل", "ROOT-TRACE", "الجمل والجمال يقابلان الحيوان وسائسه"),
    "aramaic:family:6bd2bc999a49f0a234a8cdcf":
        ("نور", "ROOT-ECHO", "النور والضياء يقابلان النار في مدار الإضاءة"),
    "aramaic:family:2be3b50c1e966a5d5cf7f7cc":
        ("أخذ", "ROOT-TRACE", "الأخذ والإمساك يقابلان القبض والأخذ"),
    "aramaic:family:730fc88ca7c2656c9838f0b5":
        ("نسم", "ROOT-TRACE", "النسمة والنفس يقابلان النفس والروح"),
    "aramaic:family:c5f0f61b5c8e7e881d5a0dd4":
        ("بوب", "ROOT-TRACE", "الباب يقابل المدخل والبوابة"),
    "aramaic:family:93d1db410607ace04fd01312":
        ("أتن", "ROOT-TRACE", "الأتان تقابل أنثى الحمار"),
    "aramaic:family:c9e249f2603285f71417caa2":
        ("ذنب", "ROOT-TRACE", "الذنب يقابل الذيل والنهاية"),
    "aramaic:family:f70163d5a27992638444f5f0":
        ("أكل", "ROOT-TRACE", "الأكل يقابل الأكل والاستهلاك"),
    "aramaic:family:818a75fd5ecb73fb731781cd":
        ("يمن", "ROOT-TRACE", "اليمين تقابل الجهة اليمنى"),
    "aramaic:family:c13db91f4cab656bb2264218":
        ("بكي", "ROOT-TRACE", "البكاء يقابل النحيب والحزن"),
    "aramaic:family:0ff542a2384f3360e90c5b40":
        ("رحم", "ROOT-TRACE", "الرحمة والرحمن يقابلان الإله الرحيم"),
    "aramaic:family:ae228621a32c0e1bfecce235":
        ("كذب", "ROOT-TRACE", "الكذب والكذاب يقابلان كثير الكذب"),
    "aramaic:family:23f81542a00c2859d88d6eb1":
        ("عمد", "ROOT-TRACE", "العمود يقابل السارية والدعامة"),
    "aramaic:family:3acfaab83edcd56496806c01":
        ("أمم", "ROOT-TRACE", "الأمة تقابل الشعب والجماعة"),
    "aramaic:family:2a0fd9a73fa920adf56b4284":
        ("طحل", "ROOT-TRACE", "الطحال يقابل عضو الطحال"),
    "aramaic:family:7400f919423e700817e7830a":
        ("بعل", "ROOT-TRACE", "البعل السيد يقابل الرب والسيد"),
    "aramaic:family:3d59aadd77ad89b22d581d26":
        ("ثور", "ROOT-TRACE", "الثور يقابل البقرة المؤنثة من السلسلة الحيوانية نفسها"),
    "aramaic:family:50973cb49a325ee0f85180a8":
        ("بيت", "ROOT-TRACE", "البيت يقابل المنزل والدار"),
    "aramaic:family:5f3f53683c0fb8f5cbdedf6e":
        ("ثدي", "ROOT-TRACE", "الثدي يقابل الثدي والحلمة"),
    "aramaic:family:781d7ba70c68c9f96abf697d":
        ("قدم", "ROOT-TRACE", "القدم والسبق يقابلان الأول والمتقدم"),
    "aramaic:family:d0e5ea44076c36fa4dba82e9":
        ("تين", "ROOT-TRACE", "التين يقابل ثمرة التين"),
    "aramaic:family:1354f259a46cf4be5c462830":
        ("بصل", "ROOT-TRACE", "البصل يقابل البصلة"),
    "aramaic:family:2b4b6c224a6768d7d40bfe18":
        ("كلب", "ROOT-TRACE", "الكلبة تقابل أنثى الكلب"),
    "aramaic:family:361e2b5b7daea9c17ce82cd9":
        ("كفف", "ROOT-TRACE", "الكف تقابل راحة اليد"),
    "aramaic:family:0973cfd715e4ab71a83a0160":
        ("بأر", "ROOT-TRACE", "البئر تقابل البئر والحفرة"),
    "aramaic:family:fbce46241e7244d3c68004b3":
        ("مسح", "ROOT-TRACE", "المسح بالدهن يقابل المسح"),
    "aramaic:family:f1f96dcc82a49b45322f3373":
        ("برك", "ROOT-TRACE", "البركة تقابل البركة والدعاء"),
    "aramaic:family:37ef1c278ebee491dcfa8836":
        ("نمر", "ROOT-TRACE", "النمر يقابل حيوان النمر"),
    "aramaic:family:4e4ab2ec965f8468cc65fee3":
        ("لسن", "ROOT-TRACE", "اللسان يقابل عضو اللسان"),
    "aramaic:family:b82dba34dba0baee82bce5e2":
        ("أمم", "ROOT-TRACE", "الأم تقابل الأم"),
    "aramaic:family:474e0f1f78c86b99d64f4c4a":
        ("مخخ", "ROOT-TRACE", "المخ يقابل الدماغ"),
    "aramaic:family:4e684dd08a53eb41592ad9f7":
        ("سنن", "ROOT-TRACE", "السن تقابل سن الفم"),
    "aramaic:family:73cbf80afaaddc5504ebd63c":
        ("ذقن", "ROOT-TRACE", "الذقن تقابل اللحية والذقن"),
    "aramaic:family:a2cb92f09a553a7671acc2f0":
        ("قمح", "ROOT-TRACE", "القمح والدقيق يقابلان الطحين"),
    "aramaic:family:abaf9ad1d6a73dd9b363eb9e":
        ("موت", "ROOT-TRACE", "الموت يقابل الموت"),
    "aramaic:family:ad89772a971261d33bf61ab7":
        ("عنب", "ROOT-TRACE", "العنب يقابل ثمرة العنب"),
    "aramaic:family:b14501462b0cbc472ae97d85":
        ("عنن", "ROOT-TRACE", "العنان والسحاب يقابلان الغيم"),
    "aramaic:family:d797669eab331919768a1a0b":
        ("ليل", "ROOT-TRACE", "الليل يقابل الليل"),
    "aramaic:family:f7011416f675ced581b5bd82":
        ("دبس", "ROOT-ECHO", "الدبس الحلو الكثيف يقابل العسل في مدار الحلاوة المركزة"),
    "aramaic:family:18e5f36ab4fd31faef0d923a":
        ("طيب", "ROOT-TRACE", "الطيب والجودة يقابلان معنى حسن"),
    "aramaic:family:1a890e63f45b4449cef87e5c":
        ("برد", "ROOT-TRACE", "البرد وحب البرد يقابلان البرد النازل"),
    "aramaic:family:770c42440139b9c8a4bd8765":
        ("ملك", "ROOT-TRACE", "الملك يقابل صاحب الملك"),
    "aramaic:family:d657b39008758bb583e2cb72":
        ("أكل", "ROOT-TRACE", "الأكل يقابل الطعام"),
    "aramaic:family:fc412a8b40d5542cdca29cf5":
        ("دبب", "ROOT-TRACE", "الدب يقابل حيوان الدب"),
    "aramaic:family:90fcf738efda6cd3825567cd":
        ("أذن", "ROOT-TRACE", "الأذن تقابل عضو السمع"),
    "aramaic:family:df346847757f2e21111a59d5":
        ("يوم", "ROOT-TRACE", "اليوم يقابل النهار واليوم"),
    "aramaic:family:e76bbe02185bce9d6b545a36":
        ("كلب", "ROOT-TRACE", "الكلب يقابل حيوان الكلب"),
    "aramaic:family:6377a3a8d24e8c694a880cb4":
        ("أخو", "ROOT-TRACE", "الأخ يقابل الأخ"),
}

STRUCTURAL = {
    "aramaic:family:80659d373be421ba81b08593": (
        "LOAN-ROUTE-ISOLATED",
        "LOANWORD",
        "المانح البارثي الخارجي للتاج مسمى في حقل الاشتقاق.",
    ),
    "aramaic:family:a1f89d7b6eb867f4c7a4f009": (
        "LOAN-ROUTE-ISOLATED",
        "LOANWORD",
        "المسار من السومرية عبر الأكادية إلى اسم المائدة مسمى في المصدر.",
    ),
    "aramaic:family:3da792c0fc5bfa0690932c03": (
        "INTRA-HOUSE-TRANSFER",
        "غير صادر",
        "القهوة من العربية بنص المصدر؛ انتقال داخل البيت لا شاهد فرع مستقل.",
    ),
    "aramaic:family:fc39029995907b35d3f96db2": (
        "INTRA-HOUSE-TRANSFER",
        "غير صادر",
        "اسم السنور من الأكادية بنص المصدر؛ يحال إلى زوج المانح الأخت.",
    ),
    "aramaic:family:5dded3e99cfb36dc2473588b": (
        "PROPER-NAME-ISOLATED",
        "غير صادر",
        "اسم مصر علم موضع، مع حفظ مقارناته وعدم عده عضوا معجميا عاما.",
    ),
    "aramaic:family:08ded857c9df9c93cc179740": (
        "PROPER-NAME-ISOLATED",
        "غير صادر",
        "يمما هنا علم شخص مؤنث، فلا يرث حكم اليوم.",
    ),
    "aramaic:family:7c6c36222012ef0bd252c257": (
        "PROPER-NAME-ISOLATED",
        "غير صادر",
        "آدم علم شخص في المدخل، فلا يصدر منه حكم معجمي عام.",
    ),
}


def atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", newline="\n", dir=path.parent, delete=False
    ) as handle:
        handle.write(unicodedata.normalize("NFC", text))
        temporary = Path(handle.name)
    temporary.replace(path)


def source_anchor(family: str, connection: sqlite3.Connection) -> str:
    rows = connection.execute(
        """
        SELECT e.etymology
        FROM family_members fm JOIN entries e ON e.entry_id=fm.entry_id
        WHERE fm.family_id=? AND e.etymology<>''
        ORDER BY e.entry_id
        """,
        (family,),
    ).fetchall()
    anchors = [row[0].strip() for row in rows if row[0].strip()]
    if not anchors:
        raise ValueError(f"{family}: missing source etymology anchor")
    return anchors[0]


def replace_one(section: str, pattern: str, replacement: str) -> tuple[str, str]:
    match = re.search(pattern, section, re.MULTILINE)
    if not match:
        raise ValueError(f"missing field {pattern}")
    old = match.group(0)
    changed, count = re.subn(pattern, replacement, section, count=1, flags=re.MULTILINE)
    if count != 1:
        raise ValueError(f"ambiguous field {pattern}")
    return changed, old


def decision(family: str, connection: sqlite3.Connection) -> dict | None:
    if family in POSITIVES:
        root, verdict, sense = POSITIVES[family]
        fan = root_sense_fan(DEFAULT_RESOURCES, root, None)["independent_fan"]
        if not fan["judgment_ready"] or len(fan["selected_sources"]) < 2:
            raise ValueError(f"{family}: incomplete fan for positive root {root}")
        return {
            "state": "READY",
            "requires": "المراجعة المضادة الثالثة قبل الإيداع",
            "verdict": verdict,
            "note": sense,
            "fan_root": root,
            "fan_sources": [
                item["source_label"] for item in fan["selected_sources"]
            ],
            "source_anchor": source_anchor(family, connection),
        }
    if family in STRUCTURAL:
        state, verdict, note = STRUCTURAL[family]
        return {
            "state": state,
            "requires": "لا شيء للحكم النسبي؛ التصنيف البنيوي مسمى في المصدر",
            "verdict": verdict,
            "note": note,
            "fan_root": None,
            "fan_sources": [],
            "source_anchor": source_anchor(family, connection),
        }
    return None


def apply(section: str, family: str, item: dict) -> tuple[str, dict]:
    marker = f"<!-- ARABIC-FAN-CAMPAIGN:{BATCH}:{family} -->"
    if marker in section:
        return section, {"already_applied": True}
    section, old_blocker = replace_one(
        section,
        r"^-\s*عائق:\s*.+$",
        f"- عائق: النوع={item['state']}؛ يتطلب={item['requires']}",
    )
    if "النوع=TOOL-GAP" not in old_blocker:
        raise ValueError(f"{family}: not a TOOL-GAP card")
    section, old_closure = replace_one(
        section,
        r"^-\s*حالةُ الإغلاق:\s*.+$",
        f"- حالةُ الإغلاق: {item['state']}",
    )
    verdict_line = (
        f"- الحكم (استكشاف): {item['verdict']} للسلسلة العضوية المسماة وحدها؛ "
        "لا وراثة عبر عضو مخالف."
        if item["verdict"] != "غير صادر"
        else f"- الحكم (استكشاف): غير صادر؛ {item['note']}"
    )
    section, old_verdict = replace_one(
        section, r"^-\s*الحكم \(استكشاف\):\s*.+$", verdict_line
    )
    fan_text = (
        f"`{item['fan_root']}`؛ "
        + " + ".join(item["fan_sources"])
        + "؛ كاملة غير مقتطعة"
        if item["fan_root"]
        else "لا مروحة موجبة في التصنيف البنيوي"
    )
    appendix = "\n".join(
        [
            "",
            marker,
            f"- ملحقُ حملةِ فكّ الحبس، {DATE}:",
            f"  - مروحة العربية: {fan_text}.",
            f"  - إسناد الفرع المنشور: {item['source_anchor']}",
            f"  - الحسم: {item['verdict']}؛ {item['note']}",
            "  - السجل التاريخي المحفوظ:",
            f"    - `{old_blocker}`",
            f"    - `{old_closure}`",
            f"    - `{old_verdict}`",
        ]
    )
    return section.rstrip() + "\n" + appendix + "\n\n", {
        "already_applied": False,
        "old_blocker": old_blocker,
        "old_closure": old_closure,
        "old_verdict": old_verdict,
    }


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    text = READING.read_text(encoding="utf-8")
    starts = list(CARD_HEADING.finditer(text))
    connection = sqlite3.connect(DB)
    parts, records, seen = [], [], set()
    cursor = 0
    try:
        for index, heading in enumerate(starts):
            end = starts[index + 1].start() if index + 1 < len(starts) else len(text)
            parts.append(text[cursor:heading.start()])
            section = text[heading.start():end]
            family_match = FAMILY_ID.search(heading.group(0))
            family = family_match.group(0) if family_match else ""
            marker = f"<!-- ARABIC-FAN-CAMPAIGN:{BATCH}:{family} -->"
            is_target_card = bool(
                re.search(
                    r"^-\s*عائق:\s*النوع\s*=\s*TOOL-GAP\b",
                    section,
                    re.MULTILINE,
                )
            ) or marker in section
            item = decision(family, connection) if family and is_target_card else None
            if item:
                if family in seen:
                    raise ValueError(f"duplicate target card: {family}")
                seen.add(family)
                section, changes = apply(section, family, item)
                records.append({"family": family, **item, "changes": changes})
            parts.append(section)
            cursor = end
        parts.append(text[cursor:])
    finally:
        connection.close()

    expected = len(POSITIVES) + len(STRUCTURAL)
    if len(records) != expected:
        missing = sorted(set(POSITIVES) | set(STRUCTURAL) - seen)
        raise ValueError(
            f"expected {expected} records, found {len(records)}; missing={missing}"
        )
    updated = "".join(parts)
    if unicodedata.normalize("NFC", updated) != updated:
        raise ValueError("updated Aramaic reading is not NFC")
    atomic_write(READING, updated)

    verdict_counts = Counter(
        item["verdict"] if item["verdict"] != "غير صادر" else item["state"]
        for item in records
    )
    payload = {
        "schema": "arabic-fan-campaign-batch-v1",
        "status": "LOCAL-THIRD-LENS-REVIEW-REQUIRED",
        "date": DATE,
        "batch": BATCH,
        "language": "aramaic",
        "unit": "card-identity",
        "summary": {
            "cards_reviewed": len(records),
            "released_from_suspension": len(records),
            "released_verdict_counts": dict(sorted(verdict_counts.items())),
            "held_state_counts": {},
        },
        "records": records,
    }
    atomic_write(
        AUDIT_JSON, json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    )
    distribution = "، ".join(
        f"{key}={value}" for key, value in sorted(verdict_counts.items())
    )
    atomic_write(
        AUDIT_MD,
        "\n".join(
            [
                "# محضر حملة فك الحبس، الآرامية، الدفعة 03",
                "",
                f"**التاريخ:** {DATE}.",
                "",
                "دفعة محلية للمراجعة المضادة، جمعت بين مروحة عربية كاملة وإسناد اشتقاقي منشور في حقل مصدر الفرع.",
                "",
                "## الرقمان المطلوبان",
                "",
                f"- خرج من التعليق: {len(records)}.",
                f"- توزيع الأحكام والتصنيفات الخارجة: {distribution}.",
                "",
                "لا رقم في هذا المحضر للنشر ولا تشغيل لخط البرهان.",
                "",
            ]
        ),
    )
    print(json.dumps(payload["summary"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
