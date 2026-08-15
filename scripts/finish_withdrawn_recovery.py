# -*- coding: utf-8 -*-
"""يبني دفعتَي استكمال المسحوب 005 و006 ومحضر الإقفال النهائي.

النطاق ثابت في ``data/withdrawn-without-live-verdict.json``. الدفعات الأربع
الأولى استردت 68 بطاقة من بطاقات النطاق نفسها. يستبعد هذا البناء تلك البطاقات
فقط، ثم يحفظ البطاقات الأربع التي وجدت حكمًا حيًا لاحقًا من أي تكرار.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import frozen_event as FE  # noqa: E402


SCOPE = ROOT / "data" / "withdrawn-without-live-verdict.json"
AUDIT_DIR = ROOT / "05-audits"

# هذه هي بطاقات النطاق الأصلية التي استردت صلتها هي، لا الأعضاء المفصولة من
# بطاقة مختلطة، ولا الضوابط الواقعة خارج نافذة الدفعة.
RECOVERED = {
    1, 2, 7, 10,
    *range(12, 24), *range(25, 32),
    43, 44, 51, 52, 53, 59, 60, 65, 66, 67, 68, 70, 71,
    *range(87, 116), 118, 125, 127,
}

# بطاقات في الباقي وجدت صلاتها حية بحكم لاحق أو بضابط سابق. لا يكتب البناء
# عليها إلحاقًا جديدًا ولا يلمس الصلة القائمة.
PROTECTED_LIVE = {56, 58, 86, 116}

# المرشح والدرجة التي أعلنتها البطاقة. الغرض هنا منع عودة عطب الشلال: لا
# تستعمل resolve بلا tier في بطاقة صرحت بطبقتها.
EVENT_CHECKS = {
    11: ("جبل", 1),
    32: ("نم", 2),
    33: ("بق", 2),
    34: ("من", 2),
    35: ("تق", 2),
    36: ("شج", 2),
    37: ("سب", 2),
    38: ("جر", 2),
    45: ("حبس", 1),
    46: ("حبس", 1),
    47: ("حبس", 1),
    48: ("حبس", 1),
    49: ("حبس", 1),
    50: ("حبس", 1),
    69: ("عمد", 1),
    83: ("كلف", 1),
    117: ("ثبر", 1),
    119: ("عض", 2),
    128: ("قب", 2),
    133: ("كنن", 1),
    138: ("بر", 2),
    141: ("تر", 2),
    144: ("هلك", 1),
}

# تصنيف أولي واحد لكل بطاقة بقيت بلا حكم موجب. توجد بطاقات ذات أكثر من عيب؛
# اختير المانع الأول الذي يكفي وحده لإبقاء السحب كي تجمع الأعداد إلى 73.
CATEGORIES = {
    "صرف الفرع وبنية الجذر وحدود المورفيم": {
        8, 34, 35, 36, 37, 38, 54, 55, 82, 83, 84, 119, 120, 123,
        124, 126, 129, 130, 131, 132, 136, 137, 142, 143, 145,
    },
    "فجوة قانون صوتي أو استعمال صف خارج نطاقه": {
        6, 9, 24, 61, 72, 73, 74, 75, 76, 77, 78, 79, 80, 81, 121,
        122, 134, 135, 139, 140,
    },
    "فشل الحدث أو المدار أو الشاهد الدلالي": {
        11, 32, 33, 45, 46, 47, 48, 49, 50, 57, 69, 85, 117, 128,
        133, 138, 141, 144,
    },
    "اتجاه قرض قائم": {39, 40, 41, 42, 62, 63, 64},
    "وحدة الحكم أو منع ازدواج العد": {3, 4, 5},
}


def previous_records() -> dict[int, dict[str, str]]:
    records: dict[int, dict[str, str]] = {}
    paths = sorted(AUDIT_DIR.glob("2026-08-14-withdrawn-recovery-batch-00[1-4].md"))
    if len(paths) != 4:
        raise RuntimeError(f"انتظرت أربعة محاضر سابقة، فوجدت {len(paths)}")
    for path in paths:
        text = path.read_text(encoding="utf-8")
        parts = re.split(r"(?m)^## (\d+)\. ", text)[1:]
        for number, body in zip(parts[0::2], parts[1::2]):
            lines = body.strip().splitlines()
            reason = next((x for x in lines if x.startswith("- سبب")), "")
            state = next((x for x in lines if x.startswith("- حال")), "")
            output = next((x for x in lines if x.startswith("- الصادر")), "")
            if int(number) not in RECOVERED and (not reason or not state or not output):
                raise RuntimeError(f"نقص سجل البطاقة {number} في {path.name}")
            records[int(number)] = {
                "title": lines[0], "reason": reason, "state": state, "output": output,
            }
    if set(records) != set(range(1, 146)):
        raise RuntimeError("المحاضر السابقة لا تغطي الأرقام 1 إلى 145 مرة واحدة")
    return records


def event_line(number: int) -> str | None:
    check = EVENT_CHECKS.get(number)
    if not check:
        return None
    candidate, tier = check
    tiers = [event.tier for event in FE.all_tiers(candidate)]
    event = FE.resolve(candidate, tier=tier)
    if event is None:
        raise RuntimeError(f"غابت الدرجة {tier} المعلنة للبطاقة {number}: {candidate}")
    available = "، ".join(str(value) for value in tiers)
    return (
        f"- إعادة فحص الحدث بعد إصلاح الأداة: درجات `{candidate}` المتاحة "
        f"هي {available}؛ طلبت البطاقة درجتها المعلنة {tier} صراحة، فردت "
        f"`FE.resolve(\"{candidate}\", tier={tier})` النص «{event.text}». "
        "وجود درجة أدنى لم يبدل المانع المستقل المذكور أعلاه."
    )


def decision(number: int, old_output: str) -> str:
    special = {
        3: (
            "- قرار الاستكمال: لم يصدر حكم جديد لـ`māru`؛ بقي خارج حكم البنوة، "
            "وحمي إلحاق `bīnu B ↔ ابن` الحي من التكرار."
        ),
        4: (
            "- قرار الاستكمال: لم يصدر حكم جديد لبقية الأسرة؛ حمي إلحاق "
            "`kāsum ↔ كأس` الحي من التكرار."
        ),
        5: (
            "- قرار الاستكمال: لم يصدر حكم جديد؛ بقيت البطاقة إحالة تمنع عد "
            "`akālu/akalu ↔ أكل` مرتين. البديل الأكادي الجديد `ءكل` يعيد "
            "الصلة الحية نفسها ولا ينشئ صلة أخرى."
        ),
        56: (
            "- قرار الاستكمال: لا إلحاق جديد؛ حميت الصلة الحية `ḥsb ↔ حسب` "
            "في `WITHDRAWN-RECOVERY-001-001`."
        ),
        58: (
            "- قرار الاستكمال: لا إلحاق جديد؛ هذه صورة ثانية للعضو نفسه، "
            "فحميت الصلة الحية `ḥsb ↔ حسب` من الازدواج."
        ),
        86: (
            "- قرار الاستكمال: لا إلحاق جديد؛ حميت الصلة الحية `רעב ↔ رغب` "
            "في `LANE-B-SEM-RESOLVE-002`."
        ),
        116: (
            "- قرار الاستكمال: لا إلحاق جديد؛ حميت الصلة الحية `מערה ↔ غور` "
            "في `LANE-B-SEM-RESOLVE-003`."
        ),
    }
    if number in special:
        return special[number]
    return old_output.replace("- الصادر الآن:", "- قرار الاستكمال:", 1)


def render_batch(batch: str, numbers: list[int], records: dict[int, dict[str, str]]) -> str:
    protected = sorted(set(numbers) & PROTECTED_LIVE)
    held = len(numbers) - len(protected)
    number_text = "، ".join(str(number) for number in numbers)
    lines = [
        f"# محضر استكمال الباقي من المسحوب، الدفعة {batch}",
        "",
        "- تاريخ التنفيذ: 2026-08-15.",
        (
            f"- النطاق: {len(numbers)} بطاقة من الباقي بعد الـ68 المستردة، "
            f"وأرقامها الأصلية في `data/withdrawn-without-live-verdict.json`: "
            f"{number_text}."
        ),
        (
            f"- النتيجة: لا حكم موجب جديد؛ بقيت {held} بطاقة بلا حكم موجب جديد، "
            f"وحميت {len(protected)} بطاقة ذات حكم حي من التكرار."
        ),
        (
            "- منهج الحكم: ثبت سبب السحب بنصه، ثم فحص بقاؤه بعد آخر تعديلين. "
            "إذا تعلق السبب بالحدث طلبت الدرجة التي أعلنتها البطاقة بواسطة "
            "`FE.resolve(candidate, tier=...)` بعد جرد `FE.all_tiers(candidate)`. "
            "وبقيت الأرجل ثلاثا والمدار مكتوبا باليد، ولم يستعمل القاموس مصفاة نفي."
        ),
        (
            "- فحص المروحة الأكادية: البطاقات الأكادية الثلاث في الدفعة لم يكن "
            "مانعها ضيق المروحة. بقي `māru` خارج حكم `bīnu B`، وبقيت بقية أسرة "
            "`kāsum` خارج حكم عضو الكأس، وفتح البديل الجديد في `aklum` صورة `ءكل` "
            "التي تحيل إلى الصلة الحية نفسها ولا تجيز عدها مرتين."
        ) if batch == "005" else (
            "- فحص المروحة الأكادية: لا بطاقة أكادية في هذه الدفعة، فلا ينطبق "
            "بابا `h ↔ خ/ح` وهمزة البدء على شيء من نطاقها."
        ),
        "- سلامة النطاق: لم تمس صلة صادرة حية، وبقي OPEN-CANDIDATE وسم شرف لا حكم نفي.",
        "",
    ]
    for number in numbers:
        record = records[number]
        lines.extend([
            f"## {number}. {record['title']}",
            "",
            record["reason"],
            record["state"],
        ])
        event = event_line(number)
        if event:
            lines.append(event)
        lines.extend([decision(number, record["output"]), ""])
    return "\n".join(lines).rstrip() + "\n"


def render_final(remaining: list[int]) -> str:
    held = sorted(set(remaining) - PROTECTED_LIVE)
    classified = set().union(*CATEGORIES.values())
    if classified != set(held):
        missing = sorted(set(held) - classified)
        extra = sorted(classified - set(held))
        raise RuntimeError(f"اختل تصنيف الختام؛ ناقص={missing} زائد={extra}")
    if sum(len(values) for values in CATEGORIES.values()) != len(classified):
        raise RuntimeError("تداخلت فئات أسباب السحب")

    lines = [
        "# المحضر الختامي لاسترداد المسحوب الذي زال مانعه",
        "",
        "- تاريخ الإقفال: 2026-08-15.",
        "- النطاق الكلي: 145 بطاقة في `data/withdrawn-without-live-verdict.json`.",
        (
            "- المسترد جملة: 68 بطاقة من بطاقات النطاق الأصلية؛ منها 58 "
            "`ROOT-TRACE` و6 `NUCLEUS-TRACE` و4 `NUCLEUS-ECHO`. لم تضف "
            "الدفعتان 005 و006 حكما موجبا جديدا."
        ),
        (
            "- المحمي من التكرار: 4 بطاقات وجدت صلاتها حية بحكم لاحق أو بضابط "
            "سابق، وهي 56 و58 و86 و116. لم تمس هذه الصلات."
        ),
        (
            "- الباقي مسحوبا بلا حكم موجب: 73 بطاقة. يرد التصنيف الآتي على "
            "المانع الأول الكافي وحده؛ بعض البطاقات تحمل عيبا ثانيا أيضا."
        ),
        "",
        "## أسباب الباقي مصنفة",
        "",
        "| السبب الأول الكافي | العدد | أرقام البطاقات الأصلية |",
        "|---|---:|---|",
    ]
    for label, values in CATEGORIES.items():
        number_text = "، ".join(str(number) for number in sorted(values))
        lines.append(f"| {label} | {len(values)} | {number_text} |")
    lines.extend([
        "",
        "## أثر إصلاحي الحدث والمروحة",
        "",
        (
            f"- أعيد فحص {len(EVENT_CHECKS)} موضعا يتصل مانعه بالحدث بدرجته "
            "المعلنة، لا بأعلى درجة متاحة. بطاقات الجذر طلبت الدرجة 1 وبطاقات "
            "النواة طلبت الدرجة 2. لم توجد في الباقي بطاقة تعلن الدرجة 4، فلم "
            "يكن سحب أي بطاقة باقية أثرا لعطب الشلال وحده."
        ),
        (
            "- لم توجد في الباقي بطاقة أكادية سبب سحبها ضيق المروحة. أظهر الفحص "
            "أن `fan(\"aklum\", \"akkadian\")` يضيف `ءكل`، لكنه يحيل إلى "
            "`akālu/akalu ↔ أكل` الحية، فبقي منع ازدواج العد قائما."
        ),
        "",
        "## أكثر الأسباب تكرارا وما تدل عليه",
        "",
        (
            "أكثر الموانع صرف الفرع وبنية الجذر وحدود المورفيم، 25 بطاقة، ثم "
            "فجوات القانون الصوتي أو استعمال الصف خارج نطاقه، 20 بطاقة، ثم فشل "
            "الحدث أو المدار أو الشاهد الدلالي، 18 بطاقة. هذه الثلاثة تمثل 63 من "
            "73 بطاقة باقية، فهي موضع الإصلاح التالي قبل توسيع الحصاد."
        ),
        "",
        (
            "تتركز فجوة الصوت في كتلة `ḏbꜥ` و`ḏnḥ` المصرية، وتتكرر فجوة المعنى "
            "في كتلة الغطاء القبطية بإزاء `حبس`. أما اتجاه القرض فسبع بطاقات "
            "تحتاج سجل مانح واتجاه، لا توسيع المروحة. وبقيت سبع بطاقات موسومة "
            "`OPEN-CANDIDATE` لأنها فرص موثقة لم تكتمل أرجلها، لا أحكاما بالنفي."
        ),
    ])
    return "\n".join(lines).rstrip() + "\n"


def main() -> None:
    scope = json.loads(SCOPE.read_text(encoding="utf-8"))
    if len(scope) != 145:
        raise RuntimeError(f"تغير نطاق الـ145: صار {len(scope)}")
    if len(RECOVERED) != 68:
        raise RuntimeError(f"اختل عد المسترد: {len(RECOVERED)}")

    records = previous_records()
    remaining = [number for number in range(1, 146) if number not in RECOVERED]
    if len(remaining) != 77:
        raise RuntimeError(f"اختل عد الباقي: {len(remaining)}")
    batches = {"005": remaining[:40], "006": remaining[40:]}
    if [len(batches["005"]), len(batches["006"])] != [40, 37]:
        raise RuntimeError("اختل تقطيع الدفعتين")

    outputs = {
        AUDIT_DIR / "2026-08-15-withdrawn-recovery-batch-005.md": render_batch(
            "005", batches["005"], records
        ),
        AUDIT_DIR / "2026-08-15-withdrawn-recovery-batch-006.md": render_batch(
            "006", batches["006"], records
        ),
        AUDIT_DIR / "2026-08-15-withdrawn-recovery-final.md": render_final(remaining),
    }
    for path, text in outputs.items():
        if chr(0x2014) in text:
            raise RuntimeError(f"وجدت شرطة طويلة في {path.name}")
        path.write_text(text, encoding="utf-8")
        print(f"كتب {path.relative_to(ROOT)}: {len(text.splitlines())} سطرا")


if __name__ == "__main__":
    main()
