#!/usr/bin/env python3
"""Apply the first author-ordered Arabic-fan release batch to Aramaic cards.

The batch is deliberately explicit.  Retrieval is mechanical, but the semantic
decision for every family is listed below and is never inferred by the script.
The script verifies that every positive decision has a full, untruncated fan
from two independent old Arabic lexica, preserves the superseded fields in a
dated appendix, and writes an identity-counted audit.
"""
from __future__ import annotations

from collections import Counter
import json
import re
import sys
import tempfile
import unicodedata
from pathlib import Path

from search_arabic_root_senses import DEFAULT_RESOURCES, root_sense_fan


ROOT = Path(__file__).resolve().parents[1]
READING = ROOT / "04-cross-linguistic" / "readings" / "aramaic.md"
FAN_CACHE = ROOT / "cache" / "recovery_pipeline" / "aramaic-complete-root-fans.json"
AUDIT_JSON = (
    ROOT
    / "cache"
    / "recovery_pipeline"
    / "arabic-fan-campaign-aramaic-batch-01.json"
)
AUDIT_MD = (
    ROOT
    / "05-audits"
    / "2026-07-25-arabic-fan-campaign-aramaic-batch-01.md"
)
DATE = "2026-07-25"
BATCH = "ARAMAIC-01"


def positive(
    family: str, root: str, verdict: str, sense: str, note: str = ""
) -> dict[str, str]:
    return {
        "family": family,
        "root": root,
        "verdict": verdict,
        "sense": sense,
        "note": note,
        "state": "READY",
        "requires": "المراجعة المضادة الثالثة قبل الإيداع",
    }


def held(
    family: str,
    state: str,
    requires: str,
    note: str,
    root: str = "",
) -> dict[str, str]:
    return {
        "family": family,
        "root": root,
        "verdict": "غير صادر",
        "sense": "",
        "note": note,
        "state": state,
        "requires": requires,
    }


DECISIONS = [
    held(
        "aramaic:family:fd2a92ba2eccd2db9249addc",
        "SOURCE-GAP",
        "شاهد عربي قديم لمعنى التخليط؛ المصدران يصرحان بأن التشويش مولد",
        "المروحة رفعت فجوة الأداة، لكنها لم تثبت قدم المعنى العربي.",
        "شوش",
    ),
    positive(
        "aramaic:family:71c15290a555041a881eace5",
        "علو",
        "ROOT-TRACE",
        "العلو وأعلى الدار يقابلان الغرفة العليا",
    ),
    positive(
        "aramaic:family:070253db4f41371635d35e24",
        "زمر",
        "ROOT-TRACE",
        "الزمر والغناء بالمزمار يقابلان المغني والموسيقي",
    ),
    held(
        "aramaic:family:77eeff1013808e3816a4258c",
        "LAW-GAP",
        "ترخيص الياء النهائية الآرامية مقابل واو حلو خارج موضع GLD-01",
        "معنى الحلاوة ثابت في المصدرين، لكن رجل الصوت الكاملة غير مرخصة.",
        "حلو",
    ),
    positive(
        "aramaic:family:8c63d5d56732a12875e05816",
        "قتل",
        "ROOT-TRACE",
        "القتل يقابل صفة المقتول",
    ),
    positive(
        "aramaic:family:b946d1bf63957f703f65614e",
        "سلط",
        "ROOT-TRACE",
        "القهر والسلطة والشدة تقابل الحكم والقوة",
        "مسار ش الآرامية إلى س العربية مسجل في SIB-01.",
    ),
    positive(
        "aramaic:family:cefe81ebb024352493b9a4ac",
        "بني",
        "ROOT-TRACE",
        "البني والبناء نقيض الهدم يقابلان البناء والتشييد",
    ),
    positive(
        "aramaic:family:eee8a7826689a8c54a03e48f",
        "قبر",
        "ROOT-TRACE",
        "القبر والمدفن يقابلان صفة المدفون",
    ),
    positive(
        "aramaic:family:0f4f194923ba02f4c189391f",
        "عقر",
        "ROOT-TRACE",
        "العقر بمعنى العقم يقابل العاقر والعقيم",
    ),
    positive(
        "aramaic:family:23284e1b9b0519982a17134c",
        "دور",
        "ROOT-TRACE",
        "الدار محل يحل فيه القوم تقابل السكن والإقامة",
        "مدخل الفرع نفسه يرد דר إلى الجذر ד־ו־ר.",
    ),
    positive(
        "aramaic:family:3981ff54eaa33910ce9c4691",
        "عتد",
        "ROOT-TRACE",
        "العتيد الحاضر المهيأ يقابل الجاهز المعد",
    ),
    positive(
        "aramaic:family:6364819a571800efb892c273",
        "أكل",
        "ROOT-TRACE",
        "الأكل يقابل صفة المأكول",
    ),
    positive(
        "aramaic:family:68c38d9414a1fcc5206aef61",
        "حرر",
        "ROOT-TRACE",
        "الحر نقيض العبد والتحرير عتق يقابلان الحر والمحرر",
    ),
    positive(
        "aramaic:family:08c04ebf51a319b85bd79a2b",
        "أري",
        "ROOT-ECHO",
        "الآري محبس الدابة يقابل حجرة الدابة في الإسطبل",
        "الحكم صدى كامل الجذر مع حفظ هيئة أورיא وعدم اختزالها إلى رسم عربي.",
    ),
    positive(
        "aramaic:family:126fb327a61050ce6e834f3a",
        "حصن",
        "ROOT-TRACE",
        "الحصين المنيع يقابل القوي المقتدر",
    ),
    positive(
        "aramaic:family:36c4e6ec4443955ac12e5a9d",
        "نهر",
        "ROOT-TRACE",
        "النهر والنهار يحملان السعة والضياء في المعاجم ويقابلان الإضاءة",
        "الألف بادئة الصيغة السببية في مدخل الفرع.",
    ),
    positive(
        "aramaic:family:553ddd9a98b76c1f829cd6c5",
        "أخر",
        "ROOT-TRACE",
        "الآخر بعد الأول يقابل غيره وآخره",
    ),
    positive(
        "aramaic:family:5fdc083c38af3f628dabd308",
        "قلا",
        "ROOT-TRACE",
        "قلي الشيء وإنضاجه على المقلاة يقابل المحمص والمقلي",
        "استعملت مروحة قلا التي تسمي قلي وقلو لغتين، لا مروحة البغض وحدها.",
    ),
    positive(
        "aramaic:family:e8b66d40bda950d5042df6c5",
        "كنس",
        "ROOT-ECHO",
        "الكنس يجمع المطروح بعضه إلى بعض ويضم إلى الكناس، وهو مدار الحشد والجمع",
    ),
    positive(
        "aramaic:family:fcac3b01ba8e313ed918e521",
        "كفر",
        "ROOT-TRACE",
        "الكفر ضد الإيمان يقابل الوثني والكافر",
    ),
    positive(
        "aramaic:family:3d90d46d5d9ef3b881b99b23",
        "عبد",
        "ROOT-TRACE",
        "العبد المملوك يقابل العبودية والرق",
    ),
    positive(
        "aramaic:family:cd2e44c83a1d1e2b491d2707",
        "بلي",
        "ROOT-TRACE",
        "بلي الثوب وقدمه يقابل الاهتراء والقدم",
    ),
    positive(
        "aramaic:family:f0aeb917d3a48bf38dcaacf3",
        "زرع",
        "ROOT-ECHO",
        "طرح البذر والإنبات يقابلان إخراج مادة النسل في مدار البذر التناسلي",
    ),
    positive(
        "aramaic:family:0ca94f7a3b5a1120b654c9b9",
        "ذكر",
        "ROOT-TRACE",
        "الذكر والتذكار يقابلان التذكر وإقامة الذكرى",
    ),
    positive(
        "aramaic:family:2869cc229cad79c7319b237b",
        "سبت",
        "ROOT-TRACE",
        "السبت يوم معروف في العربية القديمة يقابل السبت الآرامي",
        "ش الآرامية إلى س العربية مرخص في SIB-01.",
    ),
    held(
        "aramaic:family:3dcd3c19e686729706c8ad6a",
        "OPEN-CANDIDATE",
        "قراءة عربية عضوية لفعل פיס بعد استنفاد الجذر والأجوف ومراجعة نوى البطاقة",
        "المروحة لا تملك جذرا عربيا كاملا مرخصا، ونوى البطاقة لا تسمي الإقناع.",
    ),
    positive(
        "aramaic:family:4860acef76d03fce415ad74f",
        "حبب",
        "ROOT-TRACE",
        "الحب والمحبة يقابلان المحبوب والحبيب",
    ),
    positive(
        "aramaic:family:545932f837ad31640842db22",
        "حكم",
        "ROOT-TRACE",
        "الحكيم والعالم بالحكم يقابلان الحكيم والعليم",
    ),
    positive(
        "aramaic:family:b3438965df0c79029b5c882d",
        "بدل",
        "ROOT-ECHO",
        "إحلال غير الشيء مكانه يقتضي تمييز الأول وفصله، وهو مدار الفصل والتبديل",
    ),
    positive(
        "aramaic:family:cc4ac92ff01b9dbe2428a45c",
        "نهر",
        "ROOT-ECHO",
        "الضياء والنور في مادة النهر والنهار يقابلان السطوع والوضوح",
    ),
    positive(
        "aramaic:family:e25f9ef0693f71f50f4080fd",
        "بلي",
        "ROOT-TRACE",
        "البلى والقدم يقابلان صفة البالي القديم",
    ),
    positive(
        "aramaic:family:e6c93233ba0a6b0b0b3cbc21",
        "حكم",
        "ROOT-TRACE",
        "الحكمة والعلم بالحكم يقابلان الحكمة والمعرفة",
    ),
    held(
        "aramaic:family:bd4b71ba8f81eb9763f9ce1e",
        "OPEN-CANDIDATE",
        "مقابل عربي عضوي للراحة في سلسلة נוח أو مدار نواة مسمى",
        "الجذر والأجوف لم يخرجا مقابلا، والنوى المستعادة لا تسمي الراحة.",
    ),
    held(
        "aramaic:family:ec2db8130656331f8146ef04",
        "OPEN-CANDIDATE",
        "مقابل عربي عضوي للشر والفجور بعد فحص مخرج רתע ونوى البطاقة",
        "مروحة رتع مكتملة لكنها لا تطابق الشر، والنوى لا تقدم مدارا واحدا.",
    ),
    held(
        "aramaic:family:ed6448f7c593baf09c6ec2b2",
        "OPEN-CANDIDATE",
        "مقابل عربي عضوي للرفقة في חבר أو مدار نواة مسمى",
        "مروحة حبر لا تسمي الرفقة، ونوى البطاقة لا تقدم مدارا مباشرا.",
        "حبر",
    ),
    positive(
        "aramaic:family:170d97e9786dd34f9a48d68f",
        "كتب",
        "ROOT-TRACE",
        "الكتب والكتابة والكتاب تقابل الكتابة والكتاب",
    ),
    positive(
        "aramaic:family:599b68f425b0ff5af081c192",
        "نكر",
        "ROOT-ECHO",
        "جعل الشيء مجهولا وإنكاره يقابلان التغريب والإبعاد عن الألفة",
    ),
    positive(
        "aramaic:family:c176afad76ad054a5f5f05d2",
        "رطب",
        "ROOT-TRACE",
        "الرطب ضد اليابس يقابل الرطوبة والنداوة",
    ),
    held(
        "aramaic:family:8515b1bfdfddacee43802cf8",
        "LAW-GAP",
        "ترخيص الياء النهائية الآرامية مقابل واو حلو خارج موضع GLD-01",
        "معنى الحلاوة ثابت في المصدرين، لكن رجل الصوت الكاملة غير مرخصة.",
        "حلو",
    ),
    positive(
        "aramaic:family:cbe288cc0387787d584386a3",
        "سبح",
        "ROOT-TRACE",
        "التسبيح والتنزيه والثناء يقابلان المدح والتسبيح",
        "ش الآرامية إلى س العربية مرخص في SIB-01.",
    ),
    positive(
        "aramaic:family:dfaf8cd411d3a69a278f1fa9",
        "قتل",
        "ROOT-TRACE",
        "القتل يقابل القتل والذبح",
    ),
    positive(
        "aramaic:family:e2b765d84791341a3c83803b",
        "حقل",
        "ROOT-TRACE",
        "الحقل أرض تزرع يقابل الحقل المحدد المزروع",
    ),
    positive(
        "aramaic:family:073c4c6aa4d014622650aace",
        "ملك",
        "ROOT-TRACE",
        "الملك والملكة يقابلان الملكة صاحبة الملك",
    ),
    held(
        "aramaic:family:4b8d3f8bebcae50b4e2dcf89",
        "LAW-GAP",
        "ضابط خارجي غير شمالي غربي لمسار الواو العربية إلى الياء في وتر",
        "مروحة وتر تثبت الفرد والباقي، لكن شرط GLD-01 الخارجي غير مسمى في البطاقة.",
        "وتر",
    ),
    held(
        "aramaic:family:53fa33d0a0d469b28fe59b3a",
        "LAW-GAP",
        "ترخيص ش إلى س مع الياء النهائية إلى واو قسو في هذه الصورة",
        "مروحة قسو تثبت الصلابة، لكن المسار الصوتي المركب غير مكتمل.",
        "قسو",
    ),
    positive(
        "aramaic:family:550dd35629d993466c33804f",
        "قلل",
        "ROOT-ECHO",
        "القلة والخفة وانخفاض الحمل تقابل خفة الوزن",
    ),
]


CARD_HEADING = re.compile(r"^### (?:بطاقة|إعادةُ توسيم).*$", re.MULTILINE)
FAMILY_ID = re.compile(r"aramaic:family:[0-9a-f]+")


def atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", newline="\n", dir=path.parent, delete=False
    ) as handle:
        handle.write(unicodedata.normalize("NFC", text))
        temporary = Path(handle.name)
    temporary.replace(path)


def fans() -> dict[str, dict]:
    if not FAN_CACHE.exists():
        return {}
    payload = json.loads(FAN_CACHE.read_text(encoding="utf-8"))
    return payload.get("fans", {})


def fan_for(root: str, cached: dict[str, dict]) -> dict:
    if root in cached:
        return cached[root]["independent_fan"]
    return root_sense_fan(DEFAULT_RESOURCES, root, None)["independent_fan"]


def source_evidence(decision: dict[str, str], cached: dict[str, dict]) -> dict:
    root = decision["root"]
    if not root:
        return {
            "root": None,
            "complete": False,
            "judgment_ready": False,
            "sources": [],
        }
    fan = fan_for(root, cached)
    evidence = {
        "root": root,
        "complete": bool(fan["complete"]),
        "judgment_ready": bool(fan["judgment_ready"]),
        "sources": [
            {
                "source_id": item["source_id"],
                "source_label": item["source_label"],
            }
            for item in fan["selected_sources"]
        ],
    }
    if decision["verdict"] != "غير صادر" and (
        not evidence["judgment_ready"] or len(evidence["sources"]) < 2
    ):
        raise ValueError(
            f"{decision['family']}: positive verdict lacks a full two-source fan "
            f"for {root}"
        )
    return evidence


def field(section: str, pattern: str) -> str:
    match = re.search(pattern, section, re.MULTILINE)
    if not match:
        raise ValueError(f"missing field matching {pattern}")
    return match.group(0)


def replace_first(section: str, pattern: str, replacement: str) -> str:
    changed, count = re.subn(pattern, replacement, section, count=1, flags=re.MULTILINE)
    if count != 1:
        raise ValueError(f"expected one field matching {pattern}, found {count}")
    return changed


def apply_section(
    section: str, decision: dict[str, str], evidence: dict
) -> tuple[str, dict]:
    marker = f"<!-- ARABIC-FAN-CAMPAIGN:{BATCH}:{decision['family']} -->"
    if marker in section:
        return section, {"already_applied": True}

    old_blocker = field(section, r"^-\s*عائق:\s*.+$")
    old_closure = field(section, r"^-\s*حالةُ الإغلاق:\s*.+$")
    old_verdict = field(section, r"^-\s*الحكم \(استكشاف\):\s*.+$")
    if "النوع=TOOL-GAP" not in old_blocker:
        raise ValueError(
            f"{decision['family']}: batch target no longer has TOOL-GAP blocker"
        )

    new_blocker = (
        f"- عائق: النوع={decision['state']}؛ يتطلب={decision['requires']}"
    )
    new_closure = f"- حالةُ الإغلاق: {decision['state']}"
    if decision["verdict"] == "غير صادر":
        new_verdict = (
            f"- الحكم (استكشاف): غير صادر؛ {decision['note']}"
        )
    else:
        new_verdict = (
            f"- الحكم (استكشاف): {decision['verdict']} للسلسلة الدلالية "
            "المسماة في البطاقة؛ لا يرثه عضو مخالف."
        )

    section = replace_first(section, r"^-\s*عائق:\s*.+$", new_blocker)
    section = replace_first(
        section, r"^-\s*حالةُ الإغلاق:\s*.+$", new_closure
    )
    section = replace_first(
        section, r"^-\s*الحكم \(استكشاف\):\s*.+$", new_verdict
    )

    source_names = " + ".join(
        item["source_label"] for item in evidence["sources"]
    )
    fan_line = (
        f"الجذر `{evidence['root']}`؛ مروحة كاملة غير مقتطعة؛ "
        f"المصدران المستعملان: {source_names}"
        if evidence["root"] and evidence["judgment_ready"]
        else (
            f"الجذر `{evidence['root']}`؛ المروحة غير كافية للحكم"
            if evidence["root"]
            else "لا جذر عربي كامل مرخص خرج من الاسترداد"
        )
    )
    result_line = (
        f"{decision['verdict']}؛ المعنى العربي المسند: {decision['sense']}"
        if decision["verdict"] != "غير صادر"
        else f"بقي {decision['state']}؛ {decision['note']}"
    )
    appendix = "\n".join(
        [
            "",
            marker,
            f"- ملحقُ حملةِ فكّ الحبس، {DATE}:",
            f"  - المروحة: {fan_line}.",
            f"  - الحسم العضوي: {result_line}.",
            "  - السجل التاريخي المحفوظ:",
            f"    - `{old_blocker}`",
            f"    - `{old_closure}`",
            f"    - `{old_verdict}`",
        ]
    )
    section = section.rstrip() + "\n" + appendix + "\n\n"
    return section, {
        "already_applied": False,
        "old_blocker": old_blocker,
        "old_closure": old_closure,
        "old_verdict": old_verdict,
        "new_blocker": new_blocker,
        "new_closure": new_closure,
        "new_verdict": new_verdict,
    }


def render_audit(payload: dict) -> str:
    lines = [
        "# محضر حملة فك الحبس، الآرامية، الدفعة 01",
        "",
        f"**التاريخ:** {DATE}.",
        "",
        "هذه دفعة أحكام استكشافية محلية للمراجعة المضادة الثالثة. العد بالمعرفات، والمروحة الكاملة غير المقتطعة من مصدرين قديمين مستقلين شرط لازم لكل حكم موجب.",
        "",
        "## الرقمان المطلوبان",
        "",
        f"- خرج من التعليق: {payload['summary']['released_from_suspension']}.",
        "- توزيع الأحكام الخارجة: "
        + "، ".join(
            f"{key}={value}"
            for key, value in payload["summary"]["released_verdict_counts"].items()
        )
        + ".",
        "",
        "## ما بقي معلقا بسبب حقيقي",
        "",
        "- "
        + "، ".join(
            f"{key}={value}"
            for key, value in payload["summary"]["held_state_counts"].items()
        )
        + ".",
        "",
        "لا يتضمن هذا المحضر أي رقم للنشر ولا يشغل خط البرهان.",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if len({item["family"] for item in DECISIONS}) != len(DECISIONS):
        raise ValueError("duplicate family decision")

    cached = fans()
    evidence_by_family = {
        item["family"]: source_evidence(item, cached) for item in DECISIONS
    }
    text = READING.read_text(encoding="utf-8")
    starts = list(CARD_HEADING.finditer(text))
    decision_by_family = {item["family"]: item for item in DECISIONS}
    found: set[str] = set()
    records = []
    parts = []
    cursor = 0
    for index, heading in enumerate(starts):
        end = starts[index + 1].start() if index + 1 < len(starts) else len(text)
        parts.append(text[cursor:heading.start()])
        section = text[heading.start():end]
        family_match = FAMILY_ID.search(heading.group(0))
        family = family_match.group(0) if family_match else ""
        decision = decision_by_family.get(family)
        if decision:
            marker = f"<!-- ARABIC-FAN-CAMPAIGN:{BATCH}:{family} -->"
            current_tool_gap = bool(
                re.search(
                    r"^-\s*عائق:\s*النوع\s*=\s*TOOL-GAP\b",
                    section,
                    re.MULTILINE,
                )
            )
            # A family can have a later organic judgment card in the same
            # append-only ledger.  This batch repairs the original suspended
            # identity card only; the later card remains independent evidence.
            if current_tool_gap or marker in section:
                if family in found:
                    raise ValueError(f"duplicate TOOL-GAP target card: {family}")
                found.add(family)
                section, changes = apply_section(
                    section, decision, evidence_by_family[family]
                )
                records.append(
                    {
                        **decision,
                        "evidence": evidence_by_family[family],
                        "changes": changes,
                        "released_from_suspension": decision["state"] == "READY",
                    }
                )
        parts.append(section)
        cursor = end
    parts.append(text[cursor:])
    missing = sorted(set(decision_by_family).difference(found))
    if missing:
        raise ValueError(f"batch targets missing from reading: {missing}")

    updated = "".join(parts)
    if unicodedata.normalize("NFC", updated) != updated:
        raise ValueError("updated Aramaic reading is not NFC")
    atomic_write(READING, updated)

    released_counts = Counter(
        item["verdict"] for item in records if item["released_from_suspension"]
    )
    held_counts = Counter(
        item["state"] for item in records if not item["released_from_suspension"]
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
            "released_from_suspension": sum(
                item["released_from_suspension"] for item in records
            ),
            "released_verdict_counts": dict(sorted(released_counts.items())),
            "held_state_counts": dict(sorted(held_counts.items())),
        },
        "records": records,
    }
    atomic_write(
        AUDIT_JSON,
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
    )
    atomic_write(AUDIT_MD, render_audit(payload))
    print(json.dumps(payload["summary"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
