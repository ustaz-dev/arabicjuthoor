#!/usr/bin/env python3
"""Apply Aramaic fan batch 04: source-anchored Semitic vocabulary."""
from __future__ import annotations

from collections import Counter
import json
import re
import sqlite3
import sys
import tempfile
import unicodedata
from pathlib import Path

from search_arabic_root_senses import ARABIC_MARKS, DEFAULT_RESOURCES, root_sense_fan


ROOT = Path(__file__).resolve().parents[1]
READING = ROOT / "04-cross-linguistic" / "readings" / "aramaic.md"
DB = ROOT / "cache" / "recovery_pipeline" / "inventory-v5.sqlite"
AUDIT_JSON = (
    ROOT / "cache" / "recovery_pipeline"
    / "arabic-fan-campaign-aramaic-batch-04.json"
)
AUDIT_MD = (
    ROOT / "05-audits"
    / "2026-07-25-arabic-fan-campaign-aramaic-batch-04.md"
)
DATE = "2026-07-25"
BATCH = "ARAMAIC-04"
CARD_HEADING = re.compile(r"^### (?:بطاقة|إعادةُ توسيم).*$", re.MULTILINE)
FAMILY_ID = re.compile(r"aramaic:family:[0-9a-f]+")


# family: (Arabic fan root, verdict, semantic terms required in both old sources,
#          named semantic/phonetic bridge)
POSITIVES = {
    "aramaic:family:c7d871f6bba8210e34dfc647": (
        "رمن", "ROOT-TRACE", ("رمان",),
        "الرمان هو الثمرة نفسها، والهيكل ر-م-ن مطابق بعد فصل النهاية الاسمية",
    ),
    "aramaic:family:3959909517797f48c9947481": (
        "يدي", "ROOT-TRACE", ("اليد",),
        "اليد هي العضو نفسه، ومصدر العربية القديم يصرح بأصل الياء المحذوفة",
    ),
    "aramaic:family:1e0474e9c0762f3ddd061684": (
        "وأم", "ROOT-ECHO", ("توأ",),
        "التوأم هو المعنى نفسه؛ شبه الصائت والصيغة الاسمية مدونان ملاحظة لا عائقا",
    ),
    "aramaic:family:dfce542bfa67a74d8d141973": (
        "مسح", "ROOT-TRACE", ("مسح",),
        "المسيح والممسوح سلسلة المسح بالدهن نفسها، مع صف الصفير الموقع",
    ),
    "aramaic:family:ea90cca03be52c4fa47cc0c3": (
        "أله", "ROOT-TRACE", ("اله",),
        "الإله والمعبود معنى واحد، وصوامت أ-ل-ه محفوظة",
    ),
    "aramaic:family:f7e756241609d23ec7f643d7": (
        "كوكب", "ROOT-TRACE", ("كوكب",),
        "الكوكب والنجم معنى واحد، والصورة الرباعية محفوظة",
    ),
    "aramaic:family:f091e9a4d6bb20ac1d2812c4": (
        "أرض", "ROOT-TRACE", ("ارض",),
        "الأرض والتراب واليابسة حقل واحد، والفرق في المطبق على الصف الموقع",
    ),
    "aramaic:family:7832ace12a2ea664c89197e2": (
        "خنزر", "ROOT-ECHO", ("خنزير",),
        "الخنزير هو الحيوان نفسه؛ النون العربية الزائدة تحفظ ملاحظة صوتية",
    ),
    "aramaic:family:de095018e1918bca0b72a167": (
        "خنزر", "ROOT-ECHO", ("خنزير",),
        "الخنزيرة هي أنثى الحيوان نفسه؛ النون العربية الزائدة تحفظ ملاحظة صوتية",
    ),
    "aramaic:family:fae22766f0684165c24ad6ca": (
        "مسح", "ROOT-TRACE", ("مسح",),
        "الصورة السريانية للمسيح من جذر المسح نفسه",
    ),
    "aramaic:family:0936411ed5257817af8c7f58": (
        "خمر", "ROOT-TRACE", ("خمر",),
        "الخمار وصانع الخمر داخل السلسلة الاسمية للخمر نفسها",
    ),
    "aramaic:family:19d03b32cad07110ddd6427a": (
        "ظبي", "ROOT-TRACE", ("ظبي",),
        "الظبي هو الحيوان نفسه، وصف DENT-08 هو المسار اللازم وحده",
    ),
    "aramaic:family:e5f427b88b5e365b305674d7": (
        "غرب", "ROOT-TRACE", ("غراب",),
        "الغراب هو الطائر نفسه، والغين المندمجة شمالا قراءة عضوية موثقة",
    ),
    "aramaic:family:198330336d4e9c74778cc9b7": (
        "عظم", "ROOT-ECHO", ("عظم",),
        "الفخذ والورك عضو عظمي؛ المعنى مداري قريب لا تطابق معجمي تام",
    ),
    "aramaic:family:4eaaee9ae0fcfeaaf864ae6c": (
        "أنث", "ROOT-TRACE", ("انث",),
        "المرأة والأنثى معنى عضوي واحد، ومصدر الفرع يشرح nt إلى tt صراحة",
    ),
    "aramaic:family:3f5802f7541e4f342aa0d81d": (
        "ثمن", "ROOT-TRACE", ("ثمان",),
        "الثمانية هي العدد نفسه، وصف الثاء الموقع هو المسار اللازم",
    ),
    "aramaic:family:ec2502633194642a217f2368": (
        "ثلث", "ROOT-TRACE", ("ثلاث",),
        "الثلاثة هي العدد نفسه، وصف الثاء الموقع هو المسار اللازم",
    ),
    "aramaic:family:59aec728ddf0eafb69df50c1": (
        "ربع", "ROOT-TRACE", ("اربع",),
        "الأربعة هي العدد نفسه وصوامتها محفوظة",
    ),
    "aramaic:family:a240277d311fdab726057e99": (
        "خمس", "ROOT-TRACE", ("خمس",),
        "الخمسة هي العدد نفسه مع الصفين الحلقي والصفيري الموقعين",
    ),
    "aramaic:family:be7753461275f5788739d862": (
        "عشر", "ROOT-TRACE", ("عشر",),
        "العشرة هي العدد نفسه مع صف الصفير الموقع",
    ),
    "aramaic:family:eb11952e7cb348fde50f0c9f": (
        "تسع", "ROOT-TRACE", ("تسع",),
        "التسعة هي العدد نفسه وصوامتها محفوظة",
    ),
    "aramaic:family:2cb3f2854007559e1a642149": (
        "ستت", "ROOT-TRACE", ("ست",),
        "الستة هي العدد نفسه، والمعاجم العربية تسمي أصلها الصوتي",
    ),
    "aramaic:family:40e34b0de5aede060fa04b0d": (
        "ثني", "ROOT-ECHO", ("اثن",),
        "الاثنان هما العدد نفسه؛ الصورة الشمالية القصيرة تسجل صدى جذر لا تطابق سطح",
    ),
    "aramaic:family:66c5b424deb8bdaca6ee7a38": (
        "أحد", "ROOT-ECHO", ("احد", "واحد"),
        "الأحد والواحد هما العدد نفسه؛ سقوط الهمزة الشمالية يسجل ملاحظة",
    ),
    "aramaic:family:c1988d494419053156cc816a": (
        "ستت", "ROOT-TRACE", ("ست",),
        "الستة هي العدد نفسه، والمعاجم العربية تسمي أصلها الصوتي",
    ),
    "aramaic:family:74e9e12931f01f52979fc1a4": (
        "عنكب", "ROOT-ECHO", ("عنكبوت",),
        "العنكبوت هو الحيوان نفسه؛ اختلاف البنية الرباعية والخماسية يمنع TRACE",
    ),
    "aramaic:family:94ca818923ea665b99418962": (
        "ثعلب", "ROOT-ECHO", ("ثعلب",),
        "الثعلب هو الحيوان نفسه؛ الباء النهائية المحفوظة في الأصل غير ظاهرة في الرأس",
    ),
    "aramaic:family:c9a9af0ddaebb695a06af50e": (
        "قيظ", "ROOT-TRACE", ("قيظ", "الصيف"),
        "القيظ والصيف الحار معنى واحد، وصف DENT-08 هو المسار اللازم",
    ),
    "aramaic:family:647628b99d2ceadd05c66bfb": (
        "نسر", "ROOT-TRACE", ("نسر",),
        "النسر هو الطائر نفسه مع صف الصفير الموقع",
    ),
    "aramaic:family:b9857fcf1b44ed59d4e4f309": (
        "لبب", "ROOT-TRACE", ("قلب", "لب"),
        "القلب ولب الشيء مركزه الداخلي، والجذر المضاعف محفوظ",
    ),
    "aramaic:family:c1ae2ef8f567bad81ecd2397": (
        "لحم", "ROOT-ECHO", ("لحم",),
        "الخبز واللحم طعامان في السلسلة المشتركة؛ الصوت تام والمعنى متحول",
    ),
    "aramaic:family:ec3374a76fa7e68563ea867a": (
        "فوه", "ROOT-ECHO", ("فوه", "فم"),
        "الفم هو العضو نفسه؛ تغير بناء آخر الكلمة يمنع TRACE التام",
    ),
    "aramaic:family:7f2e27e81bbf419cad765d3f": (
        "ثلج", "ROOT-TRACE", ("ثلج",),
        "الثلج هو المادة نفسها، وصفا الثاء والجيم الموقعان هما المسار اللازم",
    ),
    "aramaic:family:8b9e7b23ea025d740de240a9": (
        "ذأب", "ROOT-TRACE", ("ذيب",),
        "الذئب هو الحيوان نفسه، واختلاف شبه الصائت والهمزة موثق في العربية",
    ),
    "aramaic:family:b4f0c2ac3a96201754010f25": (
        "عظم", "ROOT-TRACE", ("عظم",),
        "العظم هو العضو نفسه، وصف DENT-08 هو المسار اللازم",
    ),
    "aramaic:family:e0cb76975bfc604e3b3b5ecd": (
        "سمو", "ROOT-ECHO", ("اسم",),
        "الاسم هو المعنى نفسه؛ اشتقاق العربية الداخلي من سمو يسجل صدى لا تطابق سطح",
    ),
    "aramaic:family:c371d23e54d96f280b36d9c0": (
        "شفه", "ROOT-TRACE", ("شفة", "شفاه"),
        "الشفة هي العضو نفسه، مع صف الشفة الموقع وفصل تاء الصيغة الشمالية",
    ),
}


def fold_semantics(value: str) -> str:
    value = ARABIC_MARKS.sub("", unicodedata.normalize("NFKC", value))
    return value.translate(str.maketrans("أإآؤئ", "اااوي"))


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
    specification = POSITIVES.get(family)
    if not specification:
        return None
    root, verdict, terms, note = specification
    fan = root_sense_fan(DEFAULT_RESOURCES, root, None)["independent_fan"]
    selected = fan["selected_sources"]
    if not fan["judgment_ready"] or len(selected) < 2:
        raise ValueError(f"{family}: incomplete fan for positive root {root}")
    folded_terms = tuple(fold_semantics(term) for term in terms)
    for witness in selected:
        definition = fold_semantics(str(witness["definition"]))
        if not any(term in definition for term in folded_terms):
            raise ValueError(
                f"{family}: named sense absent from {witness['source_label']}"
            )
    return {
        "state": "READY",
        "requires": "المراجعة المضادة الثالثة قبل الإيداع",
        "verdict": verdict,
        "note": note,
        "fan_root": root,
        "semantic_terms": list(terms),
        "fan_sources": [item["source_label"] for item in selected],
        "source_anchor": source_anchor(family, connection),
    }


def apply(section: str, family: str, item: dict) -> tuple[str, dict]:
    marker = f"<!-- ARABIC-FAN-CAMPAIGN:{BATCH}:{family} -->"
    if marker in section:
        return section, {"already_applied": True}
    section, old_blocker = replace_one(
        section,
        r"^-\s*عائق:\s*.+$",
        f"- عائق: النوع=READY؛ يتطلب={item['requires']}",
    )
    if "النوع=TOOL-GAP" not in old_blocker:
        raise ValueError(f"{family}: not a TOOL-GAP card")
    section, old_closure = replace_one(
        section, r"^-\s*حالةُ الإغلاق:\s*.+$", "- حالةُ الإغلاق: READY"
    )
    section, old_verdict = replace_one(
        section,
        r"^-\s*الحكم \(استكشاف\):\s*.+$",
        f"- الحكم (استكشاف): {item['verdict']} للسلسلة العضوية المسماة وحدها؛ "
        "لا وراثة عبر عضو مخالف.",
    )
    appendix = "\n".join(
        [
            "",
            marker,
            f"- ملحقُ حملةِ فكّ الحبس، {DATE}:",
            f"  - مروحة العربية: `{item['fan_root']}`؛ "
            + " + ".join(item["fan_sources"])
            + "؛ كاملة غير مقتطعة.",
            "  - تحقق المعنى في المصدرين: "
            + "، ".join(f"`{term}`" for term in item["semantic_terms"])
            + ".",
            f"  - إسناد الفرع المنشور: {item['source_anchor']}",
            f"  - الحسم: {item['verdict']}؛ {item['note']}.",
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
            is_target = bool(
                re.search(r"^-\s*عائق:\s*النوع\s*=\s*TOOL-GAP\b", section, re.MULTILINE)
            ) or marker in section
            item = decision(family, connection) if family and is_target else None
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

    if len(records) != len(POSITIVES):
        missing = sorted(set(POSITIVES) - seen)
        raise ValueError(
            f"expected {len(POSITIVES)} records, found {len(records)}; missing={missing}"
        )
    updated = "".join(parts)
    if unicodedata.normalize("NFC", updated) != updated:
        raise ValueError("updated Aramaic reading is not NFC")
    atomic_write(READING, updated)

    verdict_counts = Counter(item["verdict"] for item in records)
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
    atomic_write(AUDIT_JSON, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    distribution = "، ".join(
        f"{key}={value}" for key, value in sorted(verdict_counts.items())
    )
    atomic_write(
        AUDIT_MD,
        "\n".join(
            [
                "# محضر حملة فك الحبس، الآرامية، الدفعة 04",
                "",
                f"**التاريخ:** {DATE}.",
                "",
                "دفعة محلية للمراجعة المضادة. لا يصدر الحكم فيها إلا بعد تحقق اللفظ الدلالي المسمى داخل شاهدين عربيين قديمين مستقلين، مع إسناد الفرع المنشور.",
                "",
                "## الرقمان المطلوبان",
                "",
                f"- خرج من التعليق: {len(records)}.",
                f"- توزيع الأحكام: {distribution}.",
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
