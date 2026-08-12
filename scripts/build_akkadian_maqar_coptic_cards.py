# -*- coding: utf-8 -*-
"""ابن حصاد الأكادية عند خشيم والقبطية عند سامح مقار في دفعات ثابتة.

هذه أداة حصاد RECOVERY-v2، لا أداة حكم دلالي عام. تفعل الآتي:

* تمرر الرسم الأكادي العربي إلى ``fan_any_script.fan`` من غير تعيين خط يدوي.
* تثبت المروحة كلها قبل النظر في المعنى، وتحفظ مرشح صاحب المصدر ولو غاب عنها.
* تفحص الصوت والحدث المجمد والمدار المكتوب لكل مرشح، ولا تولد مدارًا آليًا.
* تفصل سامح مقار عن علي فهمي خشيم في كل بطاقة قبطية.
* تعرض نواة صاحب المصدر ونواة الفهرس منفصلتين، ولا تملأ الأولى من الثانية.

العضوية هي ترتيب الصفوف في ملف المصدر، 300 بطاقة في الدفعة الكاملة، وتحيط
علامتان بكل دفعة كي تكون إعادة التشغيل إدماجية لا إلحاقًا مكررًا.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
import unicodedata
from collections import Counter
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import fan_any_script as FAN  # noqa: E402

AKKADIAN_SOURCE = ROOT / "data" / "khashim-pairs.json"
COPTIC_SOURCE = ROOT / "data" / "prior-art-extended-pairs.json"
AKKADIAN_READING = ROOT / "04-cross-linguistic" / "readings" / "akkadian.md"
COPTIC_READING = ROOT / "04-cross-linguistic" / "readings" / "coptic.md"
ROOT_EVENTS = ROOT / "computational" / "data" / "layer_2_results_v2.jsonl"
CORE_LEVELS = ROOT / "data" / "juthoor-core-levels.json"
FINAL_AUDIT = ROOT / "05-audits" / "2026-08-11-akkadian-and-coptic-harvest.md"

AKKADIAN_BOOK = "علي فهمي خشيم، «الأكّاديّة عربيّة»"
COPTIC_BOOK = "سامح مقّار، «أصل الألفاظ العامية من المصرية القديمة»"
AKKADIAN_EXPECTED = 588
COPTIC_EXPECTED = 865
BATCH_SIZE = 300

AR_MARKS = re.compile(r"[\u064b-\u065f\u0670ـ]")
AR_CHARS = re.compile(r"[ء-ي]")
LOAN_MARKERS = (
    "مأخوذ من", "مأخوذة من", "من اليونانية", "من اليونانيّة",
    "من العبرية", "من العبريّة", "من السريانية", "من السريانيّة",
    "دخيل", "اقتراض", "مقترض", "أصل يوناني", "أصل عبراني",
)

# صفوف الهوية النافذة في الشبكة المجمدة.
IDENTITY_AR = {
    "ر": "IDN-01", "م": "IDN-02", "ن": "IDN-03", "ل": "IDN-04",
    "ب": "IDN-05", "ف": "IDN-06", "س": "IDN-07", "ج": "IDN-08",
    "د": "IDN-09", "و": "IDN-10", "ت": "IDN-11", "ق": "IDN-12",
    "ك": "IDN-13", "ح": "IDN-14", "ع": "IDN-15", "ء": "IDN-16",
    "خ": "IDN-17", "ط": "IDN-18", "ص": "IDN-19", "ه": "IDN-20",
    "ش": "IDN-21", "ز": "IDN-22", "ي": "IDN-23", "ذ": "IDN-24",
}


def symmetric(rows: dict[tuple[str, str], str]) -> dict[tuple[str, str], str]:
    out = dict(rows)
    for (left, right), row_id in list(rows.items()):
        out.setdefault((right, left), row_id)
    return out


ARABIC_SHIFTS = symmetric({
    ("ث", "ت"): "DENT-01", ("ث", "س"): "DENT-02",
    ("ث", "ش"): "DENT-02", ("ذ", "د"): "DENT-03",
    ("ذ", "ز"): "DENT-04", ("ط", "ت"): "DENT-05",
    ("د", "ض"): "DENT-06", ("ظ", "ض"): "DENT-07",
    ("ل", "ر"): "LIQ-01", ("ن", "م"): "LIQ-02",
    ("ر", "ن"): "LIQ-03", ("ب", "ف"): "LAB-02",
    ("و", "ب"): "LAB-05", ("ق", "ك"): "GUT-01",
    ("ك", "ج"): "GUT-03", ("ح", "خ"): "GUT-05",
    ("س", "ش"): "SIB-01", ("س", "ص"): "SIB-02",
    ("ز", "س"): "SIB-03", ("ش", "ت"): "SIB-05",
    ("و", "ي"): "GLD-01",
})

LATIN_IDENTITY = {
    ("r", "ر"): "IDN-01", ("m", "م"): "IDN-02",
    ("n", "ن"): "IDN-03", ("l", "ل"): "IDN-04",
    ("b", "ب"): "IDN-05", ("f", "ف"): "IDN-06",
    ("s", "س"): "IDN-07", ("g", "ج"): "IDN-08",
    ("j", "ج"): "IDN-08", ("d", "د"): "IDN-09",
    ("w", "و"): "IDN-10", ("u", "و"): "IDN-10",
    ("t", "ت"): "IDN-11", ("q", "ق"): "IDN-12",
    ("k", "ك"): "IDN-13", ("c", "ك"): "IDN-13",
    ("h", "ه"): "IDN-20", ("z", "ز"): "IDN-22",
    ("y", "ي"): "IDN-23", ("SH", "ش"): "IDN-21",
    ("KH", "خ"): "IDN-17", ("TH", "ث"): "DENT-01",
}
LATIN_SHIFTS = {
    ("p", "ب"): "LAB-01", ("p", "ف"): "IDN-06",
    ("b", "ف"): "LAB-02", ("f", "ب"): "LAB-02",
    ("w", "ب"): "LAB-05", ("v", "ب"): "LAB-05",
    ("r", "ل"): "LIQ-01", ("l", "ر"): "LIQ-01",
    ("m", "ن"): "LIQ-02", ("n", "م"): "LIQ-02",
    ("c", "ق"): "GUT-01", ("k", "ق"): "GUT-01",
    ("q", "ك"): "GUT-01", ("c", "ج"): "GUT-03",
    ("g", "ك"): "GUT-02", ("h", "ع"): "GUT-04",
    ("h", "ح"): "GUT-04", ("h", "غ"): "GUT-04",
    ("h", "ء"): "GUT-04", ("t", "ث"): "DENT-01",
    ("t", "ط"): "DENT-05", ("d", "ذ"): "DENT-03",
    ("d", "ض"): "DENT-06", ("z", "ذ"): "DENT-04",
    ("s", "ث"): "DENT-02", ("s", "ش"): "SIB-01",
    ("s", "ص"): "SIB-02", ("s", "ز"): "SIB-03",
    ("j", "ي"): "GLD-02", ("v", "و"): "LAB-06",
    ("SH", "س"): "SIB-01", ("KH", "ح"): "GUT-05",
    ("TH", "ت"): "DENT-01", ("TH", "ط"): "DENT-05",
    ("CH", "خ"): "GUT-04", ("CH", "ك"): "GUT-01",
    ("GH", "ج"): "GUT-03", ("GH", "ق"): "GUT-03",
    ("PH", "ف"): "IDN-06", ("PH", "ب"): "LAB-01",
}

# المدار جملة كتبها القارئ. لا يصدر موجب لعضو غير موجود هنا.
AKKADIAN_ORBITS: dict[int, tuple[str, str]] = {
    48: ("شمس", "قرص الشمس في معنى الفرع هو الجرم الذي تظهر منه الحدة البالغة والنور، وهو الوجه الظاهر نفسه في حدث `شمس` المجمد."),
    87: ("ذلل", "الخضوع والإهانة في معنى الفرع هما نقصان الارتفاع والتيسير بالقهر في حدث `ذلل`؛ فالمدار مباشر."),
    114: ("صور", "التشكيل في معنى الفرع هو إبانة هيئة الشيء بحدوده في حدث `صور`؛ فالمدار مباشر."),
    125: ("جمل", "المعروف والفضل في معنى الفرع يقعان في وجه الحسن والتمام المتجانس الذي يحمله حدث `جمل`؛ فالمدار الصفة المحببة."),
    129: ("حبل", "الصياد وناصب الفخاخ يستعمل الحبل في الضم الوثيق الممتد الذي يسميه حدث `حبل`؛ فالمدار الآلة وفعلها."),
    161: ("شقق", "القطعة والجزء في معنى الفرع هما ناتج صدع الشيء النافذ في حدث `شقق`؛ فالمدار الناتج المباشر."),
    177: ("كشف", "العراف في معنى الفرع فاعل يكشف المستور، وحدث `كشف` هو تنحي الغطاء وظهور ما تحته؛ فالمدار الفاعل وفعل الكشف."),
    199: ("قتر", "الدخان ينفذ قليلًا أو ضعيفًا من منفذ ضيق، وهو عين الحركة التي يسميها حدث `قتر`؛ فالمدار مباشر."),
    321: ("سلم", "التمام والصحة في معنى الفرع هما صحة الجرم والتئامه وعدم تصدعه في حدث `سلم`؛ فالمدار مباشر."),
    357: ("سكن", "المحل والموضع والمنزل حيّز يستقر فيه الساكن، وهو حدث `سكن` المجمد؛ فالمدار المكان وحدثه."),
    367: ("سمن", "الدهن الخائر مادة غليظة مجتمعة، وحدث `سمن` هو امتلاء البدن وغلظه من تجمع المادة؛ فالمدار المادة وأثرها."),
    415: ("وسم", "التحلية والزينة تتركان أثرًا ظاهرًا دالًا، وهو الوجه نفسه في حدث `وسم`؛ فالمدار مباشر في الأثر الظاهر."),
    445: ("دور", "الإحاطة في معنى الفرع هي تحوي الشيء والاستدارة حوله في حدث `دور`؛ فالمدار مباشر."),
    461: ("قرر", "الوضع والحط في معنى الفرع ينتهيان إلى ثبات الشيء في مقره، وهو حدث `قرر`؛ فالمدار مباشر."),
    517: ("زين", "الزخرفة في معنى الفرع زيادة محببة تتعلق بظاهر الشيء، وهو نص حدث `زين` المجمد؛ فالمدار مباشر."),
}

COPTIC_ORBITS: dict[int, tuple[str, str]] = {
    137: ("ملح", "الملح في معنى الفرع مادة حادة قوية الأثر تتعلق في أثناء المطعوم، وهو حدث `ملح`؛ فالمدار مباشر."),
    159: ("فرش", "الفعل يفرد الشيء وينشره منبسطًا، وهو الانبساط والانتشار في حدث `فرش`؛ فالمدار مباشر."),
    193: ("موت", "الوفاة والرحيل في معنى الفرع انتهاء إلى همود وسكون وذهاب الحركة، وهو حدث `موت`؛ فالمدار مباشر."),
    205: ("حلق", "حلقة الأذن محيط قوي زال وسطه وبقي حدّه، وهي الهيئة نفسها في حدث `حلق`؛ فالمدار مباشر."),
    237: ("نحب", "العويل والبكاء يستفرغان النفس والجهد المخزون، وهو حدث `نحب`؛ فالمدار الفعل وأثره المباشر."),
    247: ("رحب", "السعة والفسحة في معنى الفرع هما انبساط الحيز في حدث `رحب`؛ فالمدار مباشر."),
    257: ("طمس", "الدفن يغطي ظاهر المدفون ويطم أثره، وهو حدث `طمس` المجمد؛ فالمدار الفعل المباشر."),
    270: ("فوت", "الهرب والمرور يباعدان الشيء عما كان متصلًا به، وهو الانفصال والتباعد في حدث `فوت`؛ فالمدار مباشر."),
    326: ("بحبح", "التوسعة تفرغ الحيز مما يشغله وتفتح مكانه، وهو حدث `بحبح`؛ فالمدار مباشر."),
    342: ("تل", "التل مكان مرتفع من مادة مكدسة، وحدث النواة `تل` هو التكديس والاتباع؛ فالمدار الناتج المباشر."),
    347: ("تلتل", "الكومة والتل في معنى الفرع هما تكديس المادة حتى تصير جثوة رابئة متماسكة في حدث `تلتل`؛ فالمدار مباشر."),
    361: ("حل", "الذهاب والرحيل انفكاك من المكان والاتصال به، وهو التسيب والتفكك في حدث النواة `حل`؛ فالمدار مباشر."),
    371: ("حك", "الدعك والحك والكشط حركة دلك بضغط على الصلب، وهو نص حدث النواة `حك`؛ فالمدار مباشر."),
    383: ("خن", "الداخل حيّز ممتد في الباطن، وهو نص حدث النواة `خن`؛ فالمدار مباشر."),
    412: ("رجرج", "هز السائل في وعائه اضطراب لجرم مجتمع رخو، وهو حدث `رجرج`؛ فالمدار مباشر."),
    414: ("رش", "التوزيع في هذا المدخل انتشار لقطرات دقيقة طرية، وهو حدث النواة `رش`؛ فالمدار مباشر."),
    432: ("ضم", "الضم والجمع في معنى الفرع هما الجمع بالضغط واللأم في حدث النواة `ضم`؛ فالمدار مباشر."),
    435: ("دحدح", "الضرب والطرح أرضًا صدم وضغط بعرض على الجرم، وهو حدث `دحدح`؛ فالمدار مباشر."),
    493: ("شك", "الوخز دخول بحدة وقوة في الجسم، وهو نص حدث النواة `شك`؛ فالمدار مباشر."),
    577: ("بت", "القطع والاستئصال في معنى الفرع هما القطع والانفصال في حدث النواة `بت`؛ فالمدار مباشر."),
    580: ("فت", "القطع والاستئصال يفضيان إلى تكسير الشيء وانفصال أجزائه، وهو حدث النواة `فت`؛ فالمدار مباشر."),
    707: ("هت", "الإضناء والإنهاك دفع للطاقة المجتمعة إلى نهايتها، وهو حدث النواة `هت`؛ فالمدار الأثر المباشر."),
}


def one_line(value: Any) -> str:
    return " ".join(str(value or "").split())


def safe(value: Any, limit: int = 520) -> str:
    text = (one_line(value).replace("`", "ˋ").replace("|", "/")
            .replace("—", "،"))
    if len(text) <= limit:
        return text
    return text[:limit].rsplit(" ", 1)[0] + "…"


def ar_bare(value: Any) -> str:
    text = unicodedata.normalize("NFC", str(value or ""))
    text = AR_MARKS.sub("", text).replace("ٱ", "ا")
    return "".join(AR_CHARS.findall(text))


def load_root_events() -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for line in ROOT_EVENTS.read_text(encoding="utf-8").splitlines():
        if line.strip():
            row = json.loads(line)
            out[row["tri_root"]] = row
    return out


def load_nucleus_events() -> dict[str, str]:
    payload = json.loads(CORE_LEVELS.read_text(encoding="utf-8"))
    return {
        row["nucleus"]: row["jabal_lexicon_reading_ar"]
        for row in payload["levels"]["level_2_binary_nuclei"]["nuclei"]
        if row.get("jabal_lexicon_reading_ar")
    }


ROOT_RECORDS = load_root_events()
NUCLEUS_EVENTS = load_nucleus_events()


def event_for(root: str) -> tuple[str, str, str]:
    if len(root) == 2:
        event = one_line(NUCLEUS_EVENTS.get(root, ""))
        return event, "NUCLEUS-TRACE", "data/juthoor-core-levels.json: jabal_lexicon_reading_ar"
    if len(root) == 3:
        record = ROOT_RECORDS.get(root, {})
        event = one_line(record.get("jabal_axial", ""))
        return event, "ROOT-TRACE", "computational/data/layer_2_results_v2.jsonl: jabal_axial"
    return "", "OPEN-CANDIDATE", "لا سجل مجمد لوحدة بهذا الطول"


def our_nucleus(root: str) -> tuple[str, str]:
    if len(root) == 2 and root in NUCLEUS_EVENTS:
        return root, NUCLEUS_EVENTS[root]
    record = ROOT_RECORDS.get(root, {})
    nucleus = one_line(record.get("binary", ""))
    if not nucleus:
        return "", ""
    reading = one_line(record.get("binary_reading_ar", "")) or one_line(
        NUCLEUS_EVENTS.get(nucleus, "")
    )
    return nucleus, reading


def explicit_loan(row: dict[str, Any]) -> str:
    text = one_line(row.get("foreign_sense")) + " " + one_line(row.get("arabic_gloss"))
    return next((marker for marker in LOAN_MARKERS if marker in text), "")


def align(skeleton: list[str], root: str) -> tuple[list[str], str]:
    weak_positions = [i for i, letter in enumerate(root) if letter in "اوي"]
    geminate = len(skeleton) == 2 and len(root) == 3 and root[-1] == root[-2]
    weak = len(skeleton) == 2 and len(root) == 3 and len(weak_positions) == 1
    if len(skeleton) == len(root):
        return list(root), "تطابق عدد الصوامت"
    if geminate:
        return list(root[:2]), "باب المضاعف: الصامت الأخير مكرر في العربية"
    if weak:
        strong = [letter for letter in root if letter not in "اوي"]
        return strong, "باب المعتل: حرف العلة العربي يقابل صائت الفرع مع بقاء الصامتين"
    return [], f"عدد الصوامت {len(skeleton)} في الفرع و{len(root)} في المرشح"


def route_row(language: str, branch: str, arabic: str) -> str | None:
    if language == "akkadian":
        if branch == arabic:
            return IDENTITY_AR.get(arabic)
        return ARABIC_SHIFTS.get((branch, arabic))
    return LATIN_IDENTITY.get((branch, arabic)) or LATIN_SHIFTS.get((branch, arabic))


def sound_audit(language: str, skeleton: list[str], root: str) -> tuple[bool, list[str], list[str], str]:
    aligned, alignment = align(skeleton, root)
    if not aligned:
        return False, [], [alignment], alignment
    tongue_ar = "الأكّاديّة" if language == "akkadian" else "القبطيّة"
    tongue_en = "Akkadian" if language == "akkadian" else "Coptic"
    rows: list[str] = []
    misses: list[str] = []
    for branch, arabic in zip(skeleton, aligned):
        row_id = route_row(language, branch, arabic)
        query = f"`{branch}` + `{arabic}` + «{tongue_ar}/{tongue_en}» في عمود الشاهد"
        if row_id:
            rows.append(f"{branch}↔{arabic} = `{row_id}`، بحث: {query}")
        else:
            misses.append(f"{branch}↔{arabic}، بحث: {query}، ولا صف مناسب")
    if "باب" in alignment:
        rows.append(alignment)
    return not misses, rows, misses, alignment


def candidate_fan(language: str, word: str) -> tuple[list[str], list[str], str]:
    if language == "akkadian":
        detected = FAN.detect(word)
        fan = FAN.fan(word)
        skeleton = FAN.skeleton(word, detected)
        return fan, skeleton, detected
    fan = FAN.fan(word, "latin")
    skeleton = FAN.skeleton(word, "latin")
    return fan, skeleton, "latin-transcription"


def manual_orbit(language: str, index: int, root: str) -> str:
    table = AKKADIAN_ORBITS if language == "akkadian" else COPTIC_ORBITS
    spec = table.get(index)
    if not spec:
        return ""
    if spec[0] != root:
        raise SystemExit(
            f"تغير مرشح المدار اليدوي في {language}/{index}: {spec[0]} ← {root}"
        )
    return spec[1]


def evaluate_candidate(
    language: str,
    index: int,
    skeleton: list[str],
    root: str,
    source_root: str,
    loan_marker: str,
) -> dict[str, Any]:
    sound, sound_rows, sound_misses, alignment = sound_audit(language, skeleton, root)
    event, degree, event_source = event_for(root)
    orbit = manual_orbit(language, index, root) if root == source_root else ""
    meaning = bool(orbit)
    complete = bool(sound and event and meaning and not loan_marker)
    return {
        "root": root,
        "sound": sound,
        "sound_rows": sound_rows,
        "sound_misses": sound_misses,
        "alignment": alignment,
        "event": event,
        "event_source": event_source,
        "written_orbit": orbit,
        "meaning": meaning,
        "loan_marker": loan_marker or None,
        "complete": complete,
        "verdict": degree if complete else "OPEN-CANDIDATE",
    }


def compact_tests(values: list[dict[str, Any]]) -> str:
    return "، ".join(
        f"`{item['root']}`[ص{'✓' if item['sound'] else '×'}،"
        f"ح{'✓' if item['event'] else '×'}،"
        f"م{'✓' if item['meaning'] else '×'}]"
        for item in values
    ) or "(لم تولد الأداة مرشحًا)"


def nucleus_comparison(source_nucleus: str, nucleus: str) -> str:
    if not source_nucleus:
        return "لا مقارنة: نواة صاحب المصدر غائبة، ولم تملأ من تقسيم المشروع"
    if not nucleus:
        return "لا مقارنة: نواة صاحب المصدر موجودة ونواة الفهرس غائبة"
    return "متوافقتان" if source_nucleus == nucleus else "مختلفتان"


def evaluate_card(language: str, index: int, row: dict[str, Any]) -> dict[str, Any]:
    foreign = one_line(row.get("foreign"))
    source_root = ar_bare(row.get("arabic_root"))
    fan, skeleton, detected = candidate_fan(language, foreign)
    loan_marker = explicit_loan(row)
    tested = [
        evaluate_candidate(language, index, skeleton, root, source_root, loan_marker)
        for root in fan
    ]
    by_root = {item["root"]: item for item in tested}
    source_test = by_root.get(source_root)
    if source_root and source_test is None:
        source_test = evaluate_candidate(
            language, index, skeleton, source_root, source_root, loan_marker
        )
    positives = [item for item in tested if item["complete"]]
    if source_test and source_test["complete"] and source_test not in positives:
        positives.append(source_test)
    if len(positives) > 1:
        raise SystemExit(f"تعددت الأحكام الموجبة في {language}/{index}: {positives}")
    winner = positives[0] if positives else None
    source_nucleus = ar_bare(row.get("arabic_nucleus"))
    nucleus, nucleus_reading = our_nucleus(source_root)

    if winner:
        outcome = winner["verdict"]
        required = "لا عائق معلق"
    else:
        outcome = "OPEN-CANDIDATE"
        reasons = []
        if not source_root:
            reasons.append("استرداد مادة عربية سليمة من صف المصدر")
        elif source_test:
            if not source_test["sound"]:
                reasons.append("مسار صوتي كامل من الصفوف المسماة")
            if not source_test["event"]:
                reasons.append("حدث المادة من السجل المجمد")
            if not source_test["meaning"]:
                reasons.append("مدار بشري مكتوب يربط معنى الفرع بالحدث المجمد")
            if loan_marker:
                reasons.append("حسم اتجاه النقل المسمى قبل دعوى الأثر")
        required = "؛ ".join(reasons) or "مدار مكتوب لمرشح من المروحة"
    return {
        "index": index,
        "row": row,
        "foreign": foreign,
        "source_root": source_root,
        "source_nucleus": source_nucleus,
        "our_nucleus": nucleus,
        "our_nucleus_reading": nucleus_reading,
        "nucleus_comparison": nucleus_comparison(source_nucleus, nucleus),
        "fan": fan,
        "skeleton": skeleton,
        "detected_script": detected,
        "source_in_fan": source_root in fan,
        "source_fan_position": fan.index(source_root) + 1 if source_root in fan else None,
        "candidate_tests": tested,
        "source_test": source_test,
        "winner": winner,
        "outcome": outcome,
        "required": required,
        "loan_marker": loan_marker or None,
    }


def fan_text(values: list[str]) -> str:
    return "، ".join(f"`{value}`" for value in values) if values else "(فارغة)"


def render_card(language: str, batch: int, card: dict[str, Any]) -> str:
    row = card["row"]
    prefix = "KHASHIM-AKKADIAN" if language == "akkadian" else "MAQAR-COPTIC"
    author = AKKADIAN_BOOK if language == "akkadian" else COPTIC_BOOK
    source_test = card["source_test"]
    winner = card["winner"]
    source_location = (
        f"داخل المروحة في الرتبة {card['source_fan_position']} من {len(card['fan'])}"
        if card["source_in_fan"] else
        f"خارج المروحة ذات {len(card['fan'])} مرشحًا، ومحفوظ بلا إسقاط"
    )
    sound = "؛ ".join((source_test or {}).get("sound_rows", []) +
                      (source_test or {}).get("sound_misses", []))
    if not sound:
        sound = "لا رصف كامل؛ فُتشت الشبكة بالحرفين وباسمي اللسان في عمود الشاهد"
    event = (source_test or {}).get("event") or "(لا حدث معتمد لهذه المادة في السجل المجمد)"
    event_source = (source_test or {}).get("event_source") or "السجل المجمد"
    orbit = (source_test or {}).get("written_orbit") or (
        "غير مكتوب؛ معنى الفرع محفوظ كما هو، ولا تولد الآلة مدارًا من تقاطع الألفاظ"
    )
    verdict = (
        f"**{winner['verdict']} (استكشاف)** بالمقابل `{winner['root']}`"
        if winner else "**غير صادر (استكشاف)**"
    )
    if language == "akkadian":
        attribution = (
            f"الرسم الأكادي والمعنى والمرشح وشرحه من {author}؛ المروحة والحدث والمسار "
            "والمدار والحكم من أدوات المشروع"
        )
        word_line = (
            f"`{card['foreign']}` بحروف عربية كما طبعه خشيم؛ اكتشف "
            f"`F.fan(word)` الطريق `{card['detected_script']}` آليًا"
        )
        source_note = "المعنى من كتاب الفرع كما نقله خشيم"
        page_note = "لا صفحة مفردة في صف الحصاد"
    else:
        attribution = (
            f"اللفظ والمعنى والمرشح وشرحه من {author}؛ سامح مقّار مؤلف مستقل عن "
            "علي فهمي خشيم، والمروحة والحدث والمسار والمدار والحكم من أدوات المشروع"
        )
        word_line = f"`{card['foreign']}` برومنة المصدر؛ حللت بوصفها رومنة قبطية لاتينية"
        source_note = "المعنى من كتاب سامح مقّار بلا رتوش"
        page_note = f"صفحة {row.get('page', '(غير مسجلة)')}"

    if winner and winner["verdict"] == "ROOT-TRACE":
        root_layer = f"ROOT-TRACE بالمادة `{winner['root']}`"
        nucleus_layer = "OPEN-CANDIDATE؛ فُحصت النواة مستقلة ولم يكتب لها مدار مستقل"
    elif winner and winner["verdict"] == "NUCLEUS-TRACE":
        root_layer = "OPEN-CANDIDATE؛ لا جذر كامل صادر"
        nucleus_layer = f"NUCLEUS-TRACE بالنواة `{winner['root']}`"
    else:
        root_layer = "OPEN-CANDIDATE؛ لا جذر كامل استوفى الأرجل الثلاث"
        nucleus_layer = "OPEN-CANDIDATE؛ لا نواة استوفت الأرجل الثلاث"

    lines = [
        f"### بطاقة: `{card['foreign']}` «{safe(row.get('foreign_sense'))}»؛ {prefix}-{batch:03d}/{card['index']:03d}",
        f"<!-- {prefix}-{batch:03d}:{card['index']} -->",
        "- إصدار البروتوكول: RECOVERY-v2 (استكشاف).",
        f"- نسبة المصدر: {attribution}.",
        f"- الكلمة في الفرع: {word_line}؛ {page_note}.",
        "- أقدم صورة مستعادة: لا تدعى صورة أقدم من الرسم المنقول في صف المصدر؛ غياب الصورة الأقدم يبقى ظاهرًا ولا يصنع حكمًا.",
        f"- الخطوة صفر: صوامت الرسم بعد طرح الصوائت المعلنة `{''.join(card['skeleton']) or '∅'}`؛ لم ينزع صامت أصلي بحدس.",
        f"- مرشح صاحب المصدر: `{card['source_root'] or '(غير مسترد)'}`؛ {source_location}؛ نص شرحه «{safe(row.get('arabic_gloss'))}».",
        f"- مروحة أداتنا المثبتة قبل المعنى: {fan_text(card['fan'])}.",
        f"- فحص كل مرشحات المروحة بالأرجل الثلاث: {compact_tests(card['candidate_tests'])}.",
        f"- مسار صوت مرشح المصدر: {sound}.",
        f"- الحدث من السجل المجمد كما هو: «{safe(event)}» [{event_source}].",
        f"- المعنى من قاموس الفرع: «{safe(row.get('foreign_sense'))}» [{source_note}، {author}].",
        f"- المدار المكتوب: {orbit}.",
        f"- نواة صاحب المقارنة المنقولة: `{card['source_nucleus']}`" if card["source_nucleus"] else "- نواة صاحب المقارنة المنقولة: (غائبة في الصف؛ لم تملأ من تقسيم المشروع).",
        f"- نواة الفهرس المجمد للمادة `{card['source_root']}`: " +
        (f"`{card['our_nucleus']}` «{safe(card['our_nucleus_reading'])}»" if card["our_nucleus"] else "(لا نواة مفهرسة لهذه المادة)"),
        f"- مقارنة النواتين: {card['nucleus_comparison']}.",
        f"- حكم طبقة الجذر: {root_layer}.",
        f"- حكم طبقة النواة: {nucleus_layer}.",
        f"- المصفاة: " +
        (f"وردت علامة انتقال «{card['loan_marker']}»، فحفظت ولم تستعمل أثرًا" if card["loan_marker"] else "لا مانح أجنبي مسمى في صف المصدر؛ غياب الاسم ليس إثبات أصالة"),
        "- فصل المتجانسات والاقتراض: الحكم، إن صدر، لهذا الصف ومعناه وحدهما؛ لا يرثه متحد الرسم ولا مركب آخر.",
        "- جسور الاسترداد المفحوصة: الرسم؛ المروحة كاملة؛ مرشح صاحب المصدر داخلها أو خارجها؛ الجذر؛ النواة؛ السجل المجمد؛ الشبكة بالحرفين وباسمي اللسان؛ المدار؛ اتجاه النقل.",
        f"- عائق: النوع={card['outcome']}؛ يتطلب={card['required']}",
        f"- حالة الإغلاق: {card['outcome']}",
        f"- الحكم (استكشاف): {verdict}",
        "- ملاحظات: عدسة الاسترداد أبقت كل مرشح، وعدسة التشكيك منعت الحكم عند غياب أي رجل من الصوت والحدث والمعنى بمداره المكتوب.",
    ]
    return "\n".join(lines)


def replace_block(text: str, start: str, end: str, block: str) -> str:
    if start in text and end in text:
        before, rest = text.split(start, 1)
        _, after = rest.split(end, 1)
        tail = after.lstrip()
        return before.rstrip() + "\n\n" + block.rstrip() + ("\n\n" + tail if tail else "\n")
    return text.rstrip() + "\n\n" + block.rstrip() + "\n"


def source_rows(language: str) -> list[dict[str, Any]]:
    if language == "akkadian":
        payload = json.loads(AKKADIAN_SOURCE.read_text(encoding="utf-8"))
        rows = [row for row in payload["rows"] if row.get("tongue") == "akkadian"]
        expected = AKKADIAN_EXPECTED
    else:
        payload = json.loads(COPTIC_SOURCE.read_text(encoding="utf-8"))
        rows = [
            row for row in payload["rows"]
            if row.get("tongue") == "coptic"
            and row.get("source") == "ocr-maqar-egyptian-colloquial"
        ]
        expected = COPTIC_EXPECTED
    if len(rows) != expected:
        raise SystemExit(f"تغير جرد {language}: {len(rows)}، والمتوقع {expected}")
    return rows


def paths(language: str, batch: int) -> tuple[pathlib.Path, pathlib.Path, str, str]:
    if language == "akkadian":
        reading = AKKADIAN_READING
        report = ROOT / "data" / f"khashim-akkadian-batch-{batch:03d}.json"
        marker = f"KHASHIM-AKKADIAN-HARVEST-BATCH-{batch:03d}"
    else:
        reading = COPTIC_READING
        report = ROOT / "data" / f"maqar-coptic-batch-{batch:03d}.json"
        marker = f"MAQAR-COPTIC-HARVEST-BATCH-{batch:03d}"
    return reading, report, f"<!-- {marker}:START -->", f"<!-- {marker}:END -->"


def actual_card_count(text: str) -> int:
    return sum(
        1 for line in text.splitlines()
        if line.startswith("### بطاقة") and "<الكلمة" not in line
    )


def build(language: str, batch: int) -> dict[str, Any]:
    rows = source_rows(language)
    start_index = (batch - 1) * BATCH_SIZE
    selected = rows[start_index:start_index + BATCH_SIZE]
    if not selected:
        raise SystemExit(f"لا عضوية للدفعة {language}/{batch}")
    evaluated = [
        evaluate_card(language, start_index + offset, row)
        for offset, row in enumerate(selected)
    ]
    positives = sum(card["winner"] is not None for card in evaluated)
    fan_hits = sum(card["source_in_fan"] for card in evaluated)
    source_nuclei = sum(bool(card["source_nucleus"]) for card in evaluated)
    agreements = Counter(card["nucleus_comparison"] for card in evaluated)
    reading, report, start, end = paths(language, batch)
    if language == "akkadian":
        title = f"## حصاد خشيم الأكادي، الدفعة {batch:03d} ({len(evaluated)} بطاقة؛ 2026-08-11)"
        scope = (
            f"الصفوف {start_index} إلى {start_index + len(evaluated) - 1} من جرد "
            f"{AKKADIAN_EXPECTED} مرشحًا في {AKKADIAN_BOOK}. الرسم الأكادي عربي، "
            "ولذلك شغلت `F.fan(word)` بلا تعيين خط يدوي حتى تختار طريق `arabic-script`. "
            "مرشح خشيم محفوظ سواء دخل المروحة أم بقي خارجها."
        )
    else:
        title = f"## حصاد سامح مقّار القبطي، الدفعة {batch:03d} ({len(evaluated)} بطاقة؛ 2026-08-11)"
        scope = (
            f"الصفوف {start_index} إلى {start_index + len(evaluated) - 1} من جرد "
            f"{COPTIC_EXPECTED} مرشحًا مصدرها {COPTIC_BOOK}. سامح مقّار مستقل عن خشيم. "
            "تظهر نواة صاحب المصدر ونواة الفهرس منفصلتين، ولا تملأ الأولى من الثانية. "
            "ونسبة النواة القبطية 85.6% في قياس المشروع السابق شهادة بنيوية معروضة هنا بلا إعادة نشر رقم من هذه الطبقة."
        )
    cards_text = "\n\n".join(render_card(language, batch, card) for card in evaluated)
    block = "\n".join([
        start,
        title,
        "",
        "**بيان النطاق.** " + scope,
        "",
        "**قانون الحكم.** الموجب ثلاث أرجل: مسار صوتي مسمى، وحدث من السجل المجمد كما هو، ومعنى الفرع بلا رتوش مع مدار مكتوب. لا شرط رابع، ولا يحتكر مرشح صاحب المصدر الحكم.",
        "",
        f"**حصيلة الدفعة.** كُتبت {len(evaluated)} بطاقة؛ صدر {positives} موجبًا؛ أصاب مرشح صاحب المصدر المروحة في {fan_hits} بطاقة؛ بقي غير المستوفي `OPEN-CANDIDATE` بحجته.",
        "",
        cards_text,
        end,
    ])
    current = reading.read_text(encoding="utf-8")
    updated = unicodedata.normalize("NFC", replace_block(current, start, end, block))
    reading.write_text(updated, encoding="utf-8", newline="\n")
    file_cards = actual_card_count(updated)

    report_rows = []
    for card in evaluated:
        source_test = card["source_test"]
        report_rows.append({
            "index": card["index"],
            "foreign": card["foreign"],
            "foreign_sense": one_line(card["row"].get("foreign_sense")),
            "source_root": card["source_root"],
            "source_in_fan": card["source_in_fan"],
            "source_fan_position": card["source_fan_position"],
            "fan": card["fan"],
            "candidate_tests": [
                {
                    "root": item["root"], "sound": item["sound"],
                    "event": bool(item["event"]), "written_orbit": bool(item["written_orbit"]),
                    "complete": item["complete"], "verdict": item["verdict"],
                }
                for item in card["candidate_tests"]
            ],
            "source_test": source_test,
            "source_nucleus": card["source_nucleus"] or None,
            "our_nucleus": card["our_nucleus"] or None,
            "nucleus_comparison": card["nucleus_comparison"],
            "outcome": card["outcome"],
            "required": card["required"],
            "winner": card["winner"],
        })
    payload = {
        "schema": "juthoor-source-harvest-batch-v1",
        "generated_by": "scripts/build_akkadian_maqar_coptic_cards.py",
        "layer": "استكشاف",
        "language": language,
        "batch": batch,
        "source": str((AKKADIAN_SOURCE if language == "akkadian" else COPTIC_SOURCE).relative_to(ROOT)).replace("\\", "/"),
        "source_author": "علي فهمي خشيم" if language == "akkadian" else "سامح مقّار",
        "source_book": AKKADIAN_BOOK if language == "akkadian" else COPTIC_BOOK,
        "source_rows_total": len(rows),
        "source_index_start": start_index,
        "source_index_end": start_index + len(evaluated) - 1,
        "cards_written": len(evaluated),
        "positive": positives,
        "open_candidate": len(evaluated) - positives,
        "source_candidate_in_fan": fan_hits,
        "source_nucleus_present": source_nuclei,
        "nucleus_comparison_counts": dict(agreements),
        "reading_file_cards_after": file_cards,
        "rows": report_rows,
    }
    report.write_text(
        json.dumps(payload, ensure_ascii=False, indent=1),
        encoding="utf-8", newline="\n",
    )
    return {"report": report, **payload}


def write_final_audit() -> None:
    reports = [
        ROOT / "data" / "khashim-akkadian-batch-001.json",
        ROOT / "data" / "khashim-akkadian-batch-002.json",
        ROOT / "data" / "maqar-coptic-batch-001.json",
        ROOT / "data" / "maqar-coptic-batch-002.json",
        ROOT / "data" / "maqar-coptic-batch-003.json",
    ]
    missing = [path for path in reports if not path.exists()]
    if missing:
        raise SystemExit("تعذر المحضر النهائي؛ تقارير ناقصة: " + ", ".join(str(x) for x in missing))
    payloads = [json.loads(path.read_text(encoding="utf-8")) for path in reports]
    akk = payloads[:2]
    cop = payloads[2:]
    akk_cards = sum(item["cards_written"] for item in akk)
    cop_cards = sum(item["cards_written"] for item in cop)
    akk_positive = sum(item["positive"] for item in akk)
    cop_positive = sum(item["positive"] for item in cop)
    akk_fan = sum(item["source_candidate_in_fan"] for item in akk)
    cop_fan = sum(item["source_candidate_in_fan"] for item in cop)
    cop_source_nuclei = sum(item["source_nucleus_present"] for item in cop)
    lines = [
        "# محضر حصاد الأكادية والقبطية من صفوف خشيم ومقّار",
        "",
        "**التاريخ:** 2026-08-11.  ",
        "**الطبقة:** استكشاف، لا تحقق مقيس.",
        "",
        "## الجرد الكامل",
        "",
        f"- الأكادية: {akk_cards}/{AKKADIAN_EXPECTED} بطاقة من {AKKADIAN_BOOK}؛ الموجب {akk_positive}؛ ومرشح خشيم داخل مروحة `arabic-script` في {akk_fan} صفًا.",
        f"- القبطية: {cop_cards}/{COPTIC_EXPECTED} بطاقة من {COPTIC_BOOK}؛ الموجب {cop_positive}؛ ومرشح مقّار داخل المروحة في {cop_fan} صفًا.",
        f"- المجموع: {akk_cards + cop_cards} بطاقة، بلا إسقاط صف واحد من المقامين المحددين.",
        "",
        "## نسبة المصدر",
        "",
        "صفوف الأكادية من علي فهمي خشيم. صفوف القبطية من سامح مقّار، وهو مؤلف مستقل عنه. كررت كل بطاقة النسبة حتى لا تنتقل نسبة أحدهما إلى الآخر عند الاقتباس المنفرد.",
        "",
        "## مروحة الأكادية العربية الرسم",
        "",
        "شغلت الأداة `F.fan(word)` كما أمر المؤلف، فاختارت الخط `arabic-script` آليًا. لم يكن دخول مرشح خشيم في المروحة شرط حفظ، ولم يكن خروجه حكم سقوط. عرضت كل بطاقة المروحة كاملة وموقع مرشح خشيم منها، وحمل التقرير الآلي فحص الأرجل الثلاث لكل مرشح فيها.",
        "",
        "## نواتا القبطية",
        "",
        f"حقل `arabic_nucleus` حاضر في {cop_source_nuclei} من صفوف مقّار البالغ عددها {COPTIC_EXPECTED}. لذلك لم تملأ الأداة نواة صاحب المصدر من تقسيم المشروع في أي صف غاب فيه الحقل. عُرضت نواة الفهرس المجمد مستقلة، وقيل صراحة إن المقارنة متعذرة عند غياب نواة المصدر. ونسبة النواة القبطية 85.6% في قياس المشروع السابق باقية شهادة بنيوية، لا رقمًا مستخرجًا من حصاد مقّار.",
        "",
        "## قانون الحكم والمراجعتان",
        "",
        "لم يصدر موجب إلا باجتماع مسار صوتي مسمى، وحدث من السجل المجمد كما هو، ومعنى من المصدر بلا رتوش مع مدار كتبه القارئ. فُحصت المروحة كلها ولم يحتكر مرشح صاحب المصدر الحكم. عدسة الاسترداد حفظت الخارج من المروحة والمشتبه فيه، وعدسة التشكيك أبقت كل ما نقصته رجل واحدة `OPEN-CANDIDATE` بحجته.",
        "",
        "## الدفعات",
        "",
        "| اللسان | الدفعة | المكتوب | الموجب | صار ملف القراءة |",
        "|---|---:|---:|---:|---:|",
    ]
    for item in payloads:
        name = "الأكادية" if item["language"] == "akkadian" else "القبطية"
        lines.append(
            f"| {name} | {item['batch']:03d} | {item['cards_written']} | "
            f"{item['positive']} | {item['reading_file_cards_after']} |"
        )
    lines.extend([
        "",
        "## خاتمة",
        "",
        "انتهى المقامان المحددان: كل صف له بطاقة وتقرير، وكل موجب له الأرجل الثلاث ومدار مكتوب، وكل غير مستوف محفوظ باسم `OPEN-CANDIDATE`. لم تمس هذه الجولة ملف المصرية ولا ملفات الهندية الأوروبية.",
        "",
        "*English abstract.* This exploratory harvest covers all 588 Akkadian proposals attributed to Ali Fahmi Khashim and all 865 Coptic proposals attributed independently to Sameh Maqar. Every source row has a card. Khashim's Arabic-script Akkadian forms are passed through the automatic Arabic-script fan, while Maqar's absent source nuclei are never backfilled from the project's frozen nucleus index. A positive outcome requires exactly three legs: a named sound route, an unchanged frozen event, and the source meaning with a reader-written orbit. All other proposals remain OPEN-CANDIDATE with an explicit reason.",
        "",
    ])
    text = unicodedata.normalize("NFC", "\n".join(lines))
    FINAL_AUDIT.write_text(text, encoding="utf-8", newline="\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--language", choices=("akkadian", "coptic"), required=True)
    parser.add_argument("--batch", type=int, required=True)
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    valid_batches = 2 if args.language == "akkadian" else 3
    if not 1 <= args.batch <= valid_batches:
        raise SystemExit(f"رقم الدفعة خارج المقام: {args.batch}")
    result = build(args.language, args.batch)
    if args.language == "coptic" and args.batch == 3:
        write_final_audit()
    print(
        f"اللسان={args.language}؛ كتب={result['cards_written']}؛ "
        f"موجب={result['positive']}؛ مفتوح={result['open_candidate']}؛ "
        f"صار الملف={result['reading_file_cards_after']}"
    )
    print(f"كُتب: {result['report'].relative_to(ROOT).as_posix()}")
    if args.language == "coptic" and args.batch == 3:
        print(f"كُتب: {FINAL_AUDIT.relative_to(ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
