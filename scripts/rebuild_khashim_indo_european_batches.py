# -*- coding: utf-8 -*-
"""Merge and rejudge the five Khashim Indo-European exploration batches.

The old 1,500 cards remain in the append-only reading history.  This builder
adds one superseding merged card per lexical-form family, rewrites the five
machine reports to schema 2.0, and never treats absence from our snapshots as
a judgment blocker.  A named Khashim form that is absent locally carries
SOURCE-GAP in ``deficiencies`` only.
"""
from __future__ import annotations

import hashlib
import itertools
import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import fan_any_script as FAN  # noqa: E402
import frozen_event as FE  # noqa: E402
from search_arabic_root_senses import (  # noqa: E402
    DEFAULT_RESOURCES,
    independent_fan,
    matches_for_roots,
)

BATCH_PATH = ROOT / "data" / "khashim-indo-european-batch-{number:03d}.json"
PRIOR_ART = ROOT / "data" / "prior-art-extended-pairs.json"
READINGS = ROOT / "04-cross-linguistic" / "readings"
TARGET_LANGUAGES = (
    "ancient-greek",
    "gothic",
    "middle-english",
    "old-english",
    "old-irish",
    "old-latin",
    "old-norse",
    "welsh",
)
START = "<!-- KHASHIM-IE-MERGED-REREAD-001-005:START -->"
END = "<!-- KHASHIM-IE-MERGED-REREAD-001-005:END -->"
SOURCE_GAP_PHRASE = "الصورة المذكورة لم تثبت في لقطة الطبقة التاريخية المختارة"
LEGAL_CLOSURES = set(
    json.loads((ROOT / "data" / "closure-vocabulary.json").read_text(encoding="utf-8"))["legal"]
)

ARABIC_LABELS = {
    "ancient-greek": "اليونانيّة القديمة/Ancient Greek",
    "gothic": "القوطيّة/Gothic",
    "middle-english": "الإنجليزيّة الوسطى/Middle English",
    "old-english": "الإنجليزيّة القديمة/Old English",
    "old-irish": "الإيرلنديّة القديمة/Old Irish",
    "old-latin": "اللاتينيّة القديمة/Old Latin",
    "old-norse": "النورديّة القديمة/Old Norse",
    "welsh": "الويلزيّة/Welsh",
}

# The orbit is a human judgment.  An entry here is necessary but never
# sufficient: the builder also asserts sound, frozen event, and two old Arabic
# lexica.  Indices not listed here receive no positive judgment.
POSITIVE_SPECS: dict[int, dict[str, str]] = {
    17: {"root": "رجل", "orbit": "الساق والرجل عضو قائم ممتد يحمل البدن وتختلف به الحركة رأسيًا؛ فمعنى المصدر يلتقي حدث `رجل` في العضو وحركته."},
    41: {"root": "زم", "orbit": "المجموع ضم لأجزاء كثيرة في كل واحد مكتنز؛ فمعنى Summa يلتقي حدث `زم` في جمع الكثير واكتنازه."},
    77: {"root": "قرن", "orbit": "القرن نتوء صلب ممتد في أعلى الحيوان أو مقدمه؛ وهذا هو حدث `قرن` مباشرة."},
    84: {"root": "صفو", "orbit": "التنظيف بالصابون يزيل الوسخ والكدر حتى يخلو السطح منهما؛ فهذا مدار مباشر إلى خلو `صفو` من الكدر والخشونة."},
    97: {"root": "فرق", "orbit": "الثقب يفصل أجزاء الجرم فصلًا واصلًا إلى العمق؛ فيلتقي معنى pierce حدث `فرق` مباشرة."},
    97_001: {"root": "فرج", "orbit": "الثقب يفتح فرجة في أثناء جرم كثيف؛ فيلتقي معنى pierce حدث `فرج` في الانفتاح داخل الجرم."},
    152: {"root": "فر", "orbit": "الحرية انفصال عن قيد كان ملتحمًا بالفاعل؛ فهي مدار مباشر إلى فصل `فر` وتفريقه."},
    169: {"root": "برج", "orbit": "الحصن والقلعة بناء بارز قوي من بين ما يكتنفه؛ فيلتقيان بروز `برج` الظاهر."},
    171: {"root": "برج", "orbit": "القلعة والمدينة المحصنة بناء بارز قوي من بين ما يكتنفه؛ فيلتقي معنى المصدر بحدث `برج`."},
    172: {"root": "برج", "orbit": "الحصن والقلعة بناء بارز قوي من بين ما يكتنفه؛ فيلتقيان بروز `برج` الظاهر."},
    173: {"root": "برج", "orbit": "البرج والحصن بناء بارز قوي في ظاهر المكان؛ فالمدار مباشر إلى حدث `برج`."},
    192: {"root": "وطن", "orbit": "الإقليم والبلاد مكان يخص أهله ويستقرون ويأوون إليه؛ فهذا هو مدار `وطن` المكاني."},
    238: {"root": "كيل", "orbit": "الكيلو وحدة تضبط مقدار ما في الشيء؛ فيلتقي معنى المقدار حدث `كيل` في الضبط والإمساك بالمحتوى."},
    311: {"root": "سطر", "orbit": "الكتابة المذكورة في معنى المصدر تصطف علاماتها طوليًا في سطور منضبطة؛ فهذا مدار مباشر إلى حدث `سطر`."},
    357: {"root": "قص", "orbit": "القطع في caesum فصل مع تسوية للجزء المقطوع؛ فيلتقي حدث `قص` في القطع والتسوية."},
    357_001: {"root": "قصم", "orbit": "الكسر والقطع في caesum يبلغان أصل الجرم أو صلبه؛ فيلتقيان حدث `قصم` في الكسر من الأصل."},
    358: {"root": "قد", "orbit": "القطع في caedo يحدث امتدادًا طوليًا محددًا في الجرم؛ فيلتقي حدث `قد` مباشرة."},
    537: {"root": "صلد", "orbit": "الصلابة والثبات والقسوة هي تمام تصلب الشيء ومقاومته للنفاذ؛ فالمدار مباشر إلى `صلد`."},
    545: {"root": "لب", "orbit": "الحب تعلق وتلازم وتداخل بين المحب والمحبوب؛ فيلتقي حدث `لب` في اللزوم والتداخل."},
    546: {"root": "لب", "orbit": "الحب تعلق وتلازم وتداخل؛ فيلتقي حدث `لب` في اللزوم والتداخل."},
    547: {"root": "لب", "orbit": "الحب تعلق وتلازم وتداخل؛ فيلتقي معنى المصدر حدث `لب` في اللزوم."},
    550: {"root": "لب", "orbit": "المحبوب من يلزمه الحب ويتداخل به الود؛ فهذا مدار مباشر إلى لزوم `لب`."},
    593: {"root": "فرق", "orbit": "الشوكة ذات الشعبتين تنفصل إلى فرعين؛ فهي هيئة ظاهرة لحدث `فرق` في الفصل العميق."},
    594: {"root": "فرق", "orbit": "الشوكة ذات الشعبتين تنفصل إلى فرعين؛ فهي هيئة ظاهرة لحدث `فرق`."},
    596: {"root": "فرق", "orbit": "الكسر والجزء الهش ناتجان من فصل أجزاء الجرم بعضها من بعض؛ فيلتقيان حدث `فرق`."},
    596_001: {"root": "فرج", "orbit": "الكسر يفتح فرجة بين أجزاء الجرم بعد اتصالها؛ فهذا مدار مباشر إلى انفتاح `فرج`."},
    694: {"root": "ولد", "orbit": "الصبي نسل صغير من جنس والديه؛ فيلتقي معنى lad حدث `ولد` في خروج نسل الحي صغيرًا."},
    743: {"root": "فطر", "orbit": "الأب مبدأ خروج الولد وظهوره أول أمره؛ فهذا مدار الخلق والابتداء في حدث `فطر`."},
    750: {"root": "فطر", "orbit": "الانفتاح والاتساع خروج في الجرم بشق ما فوقه؛ فيلتقي معنى patulus حدث `فطر`."},
    751: {"root": "فطر", "orbit": "الانفتاح والاتساع خروج في الجرم بشق ما فوقه؛ فيلتقي معنى المصدر حدث `فطر`."},
    900: {"root": "صن", "orbit": "السياج والحائط والمستودع تحتجز ما في الجوف وتمسكه في الأثناء؛ فهذا مدار مباشر إلى حدث `صن`."},
    903: {"root": "حوش", "orbit": "البيت يجمع أهله في حيز متنح عن خارجه؛ فيلتقي حدث `حوش` في الجمع بالتنحية."},
    920: {"root": "بر", "orbit": "الخارج متجرد مما يحيط بالداخل وخالص منه؛ فيلتقي معنى foras حدث `بر` في التجرد والخلوص."},
    921: {"root": "بر", "orbit": "الخارج متجرد مما يحيط بالداخل وخالص منه؛ فيلتقي معنى المصدر حدث `بر`."},
    974: {"root": "فرض", "orbit": "المخاضة والفرضة قطع غائر في حافة النهر يهيئ موضع العبور؛ فيلتقيان حدث `فرض`."},
    985: {"root": "زفر", "orbit": "التنفس والنفخ حمل للنفس مع حركة إلى الخارج؛ فيلتقي معنى المصدر حدث `زفر` مباشرة."},
    988: {"root": "زفر", "orbit": "التنفس إخراج للنفس بحمل وحركة؛ فيلتقي معنى aspiration حدث `زفر` مباشرة."},
    1081: {"root": "زفر", "orbit": "التنفس والروح والنفس خروج محمول متحرك؛ فيلتقي معنى spirare حدث `زفر` مباشرة."},
    1086: {"root": "طرق", "orbit": "المسار والسفر والجر أثر ممتد تسويه حركة وضغط متكرر؛ فيلتقي معنى trek حدث `طرق`."},
    1092: {"root": "رود", "orbit": "الطريق موضع حركة انتقال وتردد، والركوب حركة عليه بخفة وعدم ثبات؛ فيلتقي معنى road حدث `رود`."},
    1094: {"root": "رود", "orbit": "الركوب حركة انتقال وتردد على الطريق؛ فيلتقي معنى ride حدث `رود` مباشرة."},
    1109: {"root": "جر", "orbit": "الحامل والناقل يمد المحمول معه في حركة؛ فيلتقي معنى carrier استرسال `جر` وامتداده."},
    1114: {"root": "جر", "orbit": "العربة تحمل جرمًا وتسترسل به على الطريق؛ فيلتقي معنى car حدث `جر` في الامتداد."},
    1270: {"root": "ستر", "orbit": "المخزون محفوظ تحت غطاء أو وراء حاجز؛ فيلتقي معنى store حدث `ستر` في تغطية ما وراءه."},
    1385: {"root": "برج", "orbit": "الجبل والمرتفع في معنى المصدر بروز قوي ظاهر من بين ما يكتنفه؛ فيلتقي حدث `برج`."},
    1436: {"root": "رجل", "orbit": "الرجل عضو قائم ممتد يحمل البدن وتختلف به الحركة رأسيًا؛ فالمعنى يلتقي حدث `رجل` مباشرة."},
    1465: {"root": "بت", "orbit": "العض يفصل جزءًا من الطعام ويقطعه؛ فيلتقي معنى bite حدث `بت` في القطع."},
    1469: {"root": "حفر", "orbit": "الحشرة الحفارة تقلع من الجرم وتخرج منه مادة لتصنع حفرتها؛ فيلتقي معنى المصدر حدث `حفر`."},
    1476: {"root": "ثور", "orbit": "الثور يندفع وتثور قوته الكامنة انتشارًا حادًا؛ فهذا مدار الحيوان إلى حدث `ثور` المجمّد."},
}

# Python keys must be integers in the finished table.  The suffixed literals
# above let one source form carry two independently judged roots.
MULTI_SPECS = {
    97: [POSITIVE_SPECS.pop(97), POSITIVE_SPECS.pop(97_001)],
    357: [POSITIVE_SPECS.pop(357), POSITIVE_SPECS.pop(357_001)],
    596: [POSITIVE_SPECS.pop(596_001)],
}
POSITIVE_SPECS.pop(596)
for _index, _spec in list(POSITIVE_SPECS.items()):
    MULTI_SPECS[int(_index)] = [_spec]

ROW_IDS: dict[tuple[str, str], str] = {
    ("r", "ر"): "IDN-01", ("m", "م"): "IDN-02", ("n", "ن"): "IDN-03",
    ("l", "ل"): "IDN-04", ("b", "ب"): "IDN-05", ("f", "ف"): "IDN-06",
    ("p", "ف"): "IDN-06", ("s", "س"): "IDN-07", ("g", "ج"): "IDN-08",
    ("d", "د"): "IDN-09", ("w", "و"): "IDN-10", ("v", "و"): "LAB-06",
    ("t", "ت"): "IDN-11", ("q", "ق"): "IDN-12", ("k", "ك"): "IDN-13",
    ("c", "ك"): "IDN-13", ("h", "ه"): "IDN-20", ("z", "ز"): "IDN-22",
    ("y", "ي"): "IDN-23", ("p", "ب"): "LAB-01", ("b", "ف"): "LAB-02",
    ("f", "ب"): "LAB-02", ("w", "ب"): "LAB-05", ("v", "ب"): "LAB-05",
    ("r", "ل"): "LIQ-01", ("l", "ر"): "LIQ-01", ("m", "ن"): "LIQ-02",
    ("n", "م"): "LIQ-02", ("c", "ق"): "GUT-01", ("k", "ق"): "GUT-01",
    ("q", "ك"): "GUT-01", ("c", "ج"): "GUT-03", ("g", "ك"): "GUT-02",
    ("h", "ع"): "GUT-04", ("h", "ح"): "GUT-04", ("h", "غ"): "GUT-04",
    ("t", "ث"): "DENT-01", ("t", "ط"): "DENT-05", ("d", "ذ"): "DENT-03",
    ("d", "ض"): "DENT-06", ("z", "ذ"): "DENT-04", ("s", "ث"): "DENT-02",
    ("s", "ش"): "SIB-01", ("s", "ص"): "SIB-02", ("s", "ز"): "SIB-03",
    ("j", "ي"): "GLD-02",
}


def clean_form(value: str) -> str:
    value = "".join(
        char for char in unicodedata.normalize("NFKD", value.lower())
        if not unicodedata.combining(char)
    )
    return re.sub(r"[^a-z]", "", value)


def folded_form(value: str) -> str:
    value = clean_form(value)
    for left, right in (("ph", "f"), ("th", "t"), ("sh", "s"), ("ch", "k"), ("qu", "k"), ("ck", "k")):
        value = value.replace(left, right)
    return value.translate(str.maketrans({"c": "k", "q": "k", "g": "k", "v": "w", "f": "w", "p": "b", "z": "s"}))


def form_score(left: str, right: str) -> float:
    left_clean, right_clean = clean_form(left), clean_form(right)
    if not left_clean or not right_clean:
        return 0.0
    low, high = min(len(left_clean), len(right_clean)), max(len(left_clean), len(right_clean))
    return max(
        1.0 if folded_form(left) == folded_form(right) else 0.0,
        SequenceMatcher(None, left_clean, right_clean).ratio() if low >= 3 else 0.0,
        low / high if low >= 3 and (left_clean.startswith(right_clean) or right_clean.startswith(left_clean)) else 0.0,
    )


class UnionFind:
    def __init__(self, values: list[int]) -> None:
        self.parent = {value: value for value in values}

    def find(self, value: int) -> int:
        if self.parent[value] != value:
            self.parent[value] = self.find(self.parent[value])
        return self.parent[value]

    def union(self, left: int, right: int) -> None:
        left, right = self.find(left), self.find(right)
        if left != right:
            self.parent[max(left, right)] = min(left, right)


def line_value(block: str, prefix: str) -> str:
    match = re.search(rf"^- {re.escape(prefix)}.*$", block, re.MULTILINE)
    return match.group(0) if match else ""


def parse_fan(block: str) -> list[dict[str, str]]:
    line = line_value(block, "فحص كل مرشحات المروحة:")
    return [
        {"root": root, "sound": sound, "event": event, "meaning": meaning}
        for root, sound, event, meaning in re.findall(
            r"`([^`]+)`\[ص([✓×])،ح([✓×])،م([✓×؟])\]", line
        )
    ]


def source_skeleton(block: str) -> str:
    line = line_value(block, "الخطوة صفر وحساب الصوامت:")
    alternative = re.search(r"البديل `([^`]+)`", line)
    raw = re.search(r"الخام `([^`]+)`", line)
    values = []
    for match in (raw, alternative):
        if match and match.group(1).lower() not in values:
            values.append(match.group(1).lower())
    return "|".join(values)


def match_sound_route(skeleton: str, root: str, language: str) -> tuple[str, list[str]]:
    original = skeleton
    for skeleton_variant in original.split("|"):
        skeleton_variant = re.sub(r"[^a-z]", "", skeleton_variant.lower())
        options = []
        for token in skeleton_variant:
            rows = [(arabic, row_id) for (foreign, arabic), row_id in ROW_IDS.items() if foreign == token]
            options.append(rows)
        if not options or any(not rows for rows in options):
            continue

        operation = ""
        chosen: tuple[tuple[str, str], ...] | None = None
        for combo in itertools.product(*options):
            base = "".join(item[0] for item in combo)
            alternatives = {
                base: "",
                base + base[-1]: "؛ ثم باب المضاعف المسمى يكرر الصامت الأخير",
            }
            if len(base) == 2:
                alternatives.update({
                    base[0] + "و" + base[1]: "؛ ثم باب المعتل المسمى يثبت الواو في الجوف",
                    base[0] + "ي" + base[1]: "؛ ثم باب المعتل المسمى يثبت الياء في الجوف",
                    base[0] + "ا" + base[1]: "؛ ثم باب المعتل المسمى يثبت الألف في الجوف",
                    base + "و": "؛ ثم باب المعتل المسمى يثبت الواو في الآخر",
                    base + "ي": "؛ ثم باب المعتل المسمى يثبت الياء في الآخر",
                    base + "ا": "؛ ثم باب المعتل المسمى يثبت الألف في الآخر",
                    "و" + base: "؛ ثم باب المعتل المسمى يثبت الواو في الأول",
                    "ي" + base: "؛ ثم باب المعتل المسمى يثبت الياء في الأول",
                })
            if root in alternatives:
                chosen, operation = combo, alternatives[root]
                break
        if chosen is None:
            continue

        tongue = ARABIC_LABELS[language]
        parts, searches = [], []
        for token, (arabic, row_id) in zip(skeleton_variant, chosen):
            parts.append(f"{token}↔{arabic}=`{row_id}`")
            searches.append(f"`{token}` + `{arabic}` + «{tongue}» في عمود الشاهد")
        if "|" in original and skeleton_variant != original.split("|")[0]:
            operation = "؛ بعد التعرية الصرفية المسماة" + operation
        return "؛ ".join(parts) + operation, searches
    raise AssertionError(f"Named fan route did not reproduce {original!r} -> {root!r}")


def load_events() -> tuple[dict[str, str], dict[str, str]]:
    roots: dict[str, str] = {}
    for line in (ROOT / "computational" / "data" / "layer_2_results_v2.jsonl").read_text(encoding="utf-8").splitlines():
        if line.strip():
            row = json.loads(line)
            if row.get("jabal_axial"):
                roots[row["tri_root"]] = row["jabal_axial"]
    payload = json.loads((ROOT / "data" / "juthoor-core-levels.json").read_text(encoding="utf-8"))
    nuclei = {
        row["nucleus"]: row["jabal_lexicon_reading_ar"]
        for row in payload["levels"]["level_2_binary_nuclei"]["nuclei"]
        if row.get("jabal_lexicon_reading_ar")
    }
    return roots, nuclei


def assigned_language(members: list[dict[str, Any]], raw_rows: list[dict[str, Any]]) -> str:
    attested = [member["language"] for member in members if not member["source_gap"]]
    if attested:
        return Counter(attested).most_common(1)[0][0]
    tongues = " ".join(
        str(raw_rows[index].get("tongue") or "").lower()
        for member in members for index in member["source_rows"]
    )
    if "greek" in tongues and "latin" not in tongues:
        return "ancient-greek"
    if "welsh" in tongues:
        return "welsh"
    if "irish" in tongues or "celtic" in tongues:
        return "old-irish"
    if "norse" in tongues or "scandinav" in tongues:
        return "old-norse"
    if "goth" in tongues:
        return "gothic"
    if any(label in tongues for label in ("german", "english", "dutch")):
        return "old-english"
    return "old-latin"


def quote_excerpt(value: str, width: int = 360) -> str:
    value = " ".join(str(value).split()).replace("`", "ˋ")
    if len(value) <= width:
        return value
    return value[:width].rstrip() + "…"


def main() -> int:
    batches = [json.loads(Path(str(BATCH_PATH).format(number=number)).read_text(encoding="utf-8")) for number in range(1, 6)]
    original_rows: list[dict[str, Any]] = []
    for batch in batches:
        if str(batch.get("schema") or "").endswith("v2.0"):
            # Make the builder idempotent.  Schema 2 retains every original
            # member and its source rows inside the merged card.
            for merged in batch["rows"]:
                for form in merged["forms"]:
                    original_rows.append({
                        "card_index": form["card_index"],
                        "foreign": form["form"],
                        "language": form["original_language"],
                        "source_rows": form["source_rows"],
                        "books": [],
                        "khashim_proposals": [],
                        "fan_candidates": 0,
                        "positive_roots": [],
                        "closure": "OPEN-CANDIDATE",
                        "obstacle": SOURCE_GAP_PHRASE if form["attestation"] == "source-only" else "",
                        "missing_row_searches": merged.get("missing_row_searches", []),
                    })
        else:
            original_rows.extend(batch["rows"])
    prior = json.loads(PRIOR_ART.read_text(encoding="utf-8"))["rows"]
    raw_rows = [row for row in prior if row.get("book") in {"khashim-journey1", "khashim-emperors"}]

    blocks: dict[int, str] = {}
    block_files: dict[int, str] = {}
    for language in TARGET_LANGUAGES:
        text = (READINGS / f"{language}.md").read_text(encoding="utf-8")
        markers = list(re.finditer(r"^<!-- KHASHIM-IE:(\d+):[^>]+-->$", text, re.MULTILINE))
        for position, marker in enumerate(markers):
            start = text.rfind("\n### ", 0, marker.start())
            start = start + 1 if start >= 0 else marker.start()
            candidates = [value for value in (text.find("\n### ", marker.end()), text.find("\n<!-- KHASHIM-IE-BATCH-", marker.end())) if value >= 0]
            finish = min(candidates) if candidates else len(text)
            index = int(marker.group(1))
            blocks[index] = text[start:finish].strip()
            block_files[index] = language
    if len(blocks) != 1500:
        missing = sorted(set(range(1, 1501)) - set(blocks))
        raise AssertionError(f"Could not recover all old card blocks: {len(blocks)}; missing={missing[:10]}")

    # A partially rewritten set can arise if another process replaces one
    # report while this builder is running.  The append-only blocks retain the
    # original member, language, and source-row list, so recover any missing
    # members from that authoritative history before rebuilding all five.
    present = {row["card_index"] for row in original_rows}
    for index in sorted(set(range(1, 1501)) - present):
        block = blocks[index]
        heading = re.search(r"^### بطاقة: `([^`]+)`", block, re.MULTILINE)
        source_list = re.search(r"صفوف المصدر \[([^\]]*)\]", block)
        if not heading or not source_list:
            raise AssertionError(f"Cannot recover original member {index} from its reading block")
        source_rows = [int(value) for value in re.findall(r"\d+", source_list.group(1))]
        original_rows.append({
            "card_index": index,
            "foreign": heading.group(1),
            "language": block_files[index],
            "source_rows": source_rows,
            "books": [],
            "khashim_proposals": [],
            "fan_candidates": 0,
            "positive_roots": [],
            "closure": "OPEN-CANDIDATE",
            "obstacle": SOURCE_GAP_PHRASE if SOURCE_GAP_PHRASE in block else "",
            "missing_row_searches": sorted(set(re.findall(
                r"`[^`]+` \+ `[^`]+` \+ «[^»]+» في عمود الشاهد", block
            ))),
        })
    original_rows.sort(key=lambda row: row["card_index"])
    if len(original_rows) != 1500 or {row["card_index"] for row in original_rows} != set(range(1, 1501)):
        raise AssertionError("Expected the complete original 1,500-card run")

    cards: dict[int, dict[str, Any]] = {}
    for row in original_rows:
        index = row["card_index"]
        block = blocks[index]
        cards[index] = {
            **row,
            "block": block,
            "branch_line": line_value(block, "الكلمة في الفرع ومعناها:"),
            "source_line": line_value(block, "نصوص خشيم العربية:"),
            "fan_review": parse_fan(block),
            "skeleton": source_skeleton(block),
            "source_gap": SOURCE_GAP_PHRASE in str(row.get("obstacle") or ""),
        }
        old_closure = re.search(r"^- حالة الإغلاق: ([A-Z-]+)", block, re.MULTILINE)
        if old_closure:
            cards[index]["closure"] = old_closure.group(1)

    # A source claim is the book/page/tongue/sense/root/gloss tuple.  Forms are
    # merged only inside the same claim and with a high lexical similarity.
    claims: dict[tuple[Any, ...], list[int]] = defaultdict(list)
    for card in cards.values():
        for source_index in card["source_rows"]:
            row = raw_rows[source_index]
            signature = tuple(row.get(key) for key in ("book", "page", "tongue", "foreign_sense", "arabic_root", "arabic_gloss"))
            claims[signature].append(card["card_index"])

    union = UnionFind(list(cards))
    for indices in claims.values():
        indices = sorted(set(indices))
        for offset, left in enumerate(indices):
            for right in indices[offset + 1:]:
                if form_score(cards[left]["foreign"], cards[right]["foreign"]) >= 0.70:
                    union.union(left, right)
    # Three Romance reflexes of the same named lexeme sit just below the
    # general spelling threshold and are explicit rather than hidden in a
    # looser global rule.
    union.union(1454, 1457)  # lingua / langue
    union.union(1457, 1458)  # langue / lengua
    union.union(1442, 1443)  # nerve / nerf

    grouped: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for card in cards.values():
        grouped[union.find(card["card_index"])].append(card)
    groups = [sorted(members, key=lambda item: item["card_index"]) for _, members in sorted(grouped.items())]
    if len(groups) != 789:
        raise AssertionError(f"Merge drift: expected 789 cards, got {len(groups)}")
    wake_group = next(members for members in groups if any(member["card_index"] == 1201 for member in members))
    if [member["foreign"] for member in wake_group] != ["wake", "awake", "waka", "vaka", "wakan"]:
        raise AssertionError("The wake family merge changed")

    root_events, nucleus_events = load_events()
    positive_roots = {spec["root"] for specs in MULTI_SPECS.values() for spec in specs}
    lexicon_matches = matches_for_roots(DEFAULT_RESOURCES, positive_roots, None)
    lexicon_evidence: dict[str, dict[str, Any]] = {}
    for root in sorted(positive_roots):
        fan = independent_fan(lexicon_matches[root], minimum_sources=2)
        if not fan["judgment_ready"]:
            raise AssertionError(f"Two complete independent Arabic lexica are required for {root}")
        lexicon_evidence[root] = {
            "complete_scan": True,
            "selected_sources": fan["selected_sources"],
            "coverage": fan["coverage"],
        }

    merged_cards: list[dict[str, Any]] = []
    positive_card_count = 0
    positive_trace_count = 0
    source_gap_positive_cards = 0
    for ordinal, members in enumerate(groups, 1):
        language = assigned_language(members, raw_rows)
        positive: list[dict[str, Any]] = []
        for member in members:
            for spec in MULTI_SPECS.get(member["card_index"], []):
                root = spec["root"]
                candidate = next((item for item in member["fan_review"] if item["root"] == root), None)
                if not candidate or candidate["sound"] != "✓" or candidate["event"] != "✓":
                    raise AssertionError(f"Positive {member['card_index']}:{root} lacks sound or frozen event")
                # **كان هنا `raise` لا سكوتٌ فحسب**: أيُّ جذرٍ خارجَ الـ2,285
                # يُسقِطُ الدفعةَ كلَّها بالخطأ، فلم يكنْ للمسارِ بدٌّ من تصفيةِ
                # مرشَّحيه إلى تلك العضويّةِ قبلَ أن ينظرَ فيهم. والتعديلُ 2
                # ينصُّ على النزولِ إلى النواةِ عندَ الغياب، لا على الامتناع.
                frozen = FE.resolve(root)
                if not frozen:
                    continue
                event, event_source = frozen.text, (
                    f"{frozen.source}؛ درجة {frozen.tier}، {frozen.tier_ar}")
                closure = "ROOT-TRACE" if frozen.tier == 1 else "NUCLEUS-TRACE"
                route, route_searches = match_sound_route(member["skeleton"], root, language)
                source_claims = [
                    raw_rows[source_index] for source_index in member["source_rows"]
                    if root in str(raw_rows[source_index].get("arabic_root") or "")
                ]
                if not source_claims:
                    source_claims = [raw_rows[source_index] for source_index in member["source_rows"]]
                positive.append({
                    "member_index": member["card_index"],
                    "form": member["foreign"],
                    "root": root,
                    "closure": closure,
                    "sound_route": route,
                    "sound_searches": route_searches,
                    "frozen_event": event,
                    "event_source": event_source,
                    "branch_meaning": member["branch_line"],
                    "source_claims": source_claims,
                    "orbit": spec["orbit"],
                    "arabic_lexica": [item["source_label"] for item in lexicon_evidence[root]["selected_sources"]],
                    "source_gap": member["source_gap"],
                })

        selected_by_member = defaultdict(set)
        for item in positive:
            selected_by_member[item["member_index"]].add(item["root"])
        fan_reviews = []
        for member in members:
            review = []
            for item in member["fan_review"]:
                updated = dict(item)
                if item["root"] in selected_by_member[member["card_index"]]:
                    updated["meaning"] = "✓"
                elif item["sound"] == "✓" and item["event"] == "✓":
                    updated["meaning"] = "×"
                review.append(updated)
            fan_reviews.append({"member_index": member["card_index"], "form": member["foreign"], "candidates": review})

        deficiencies = []
        for member in members:
            if member["source_gap"]:
                deficiencies.append({
                    "member_index": member["card_index"],
                    "form": member["foreign"],
                    "tag": "SOURCE-GAP",
                    "note": "الصورة من نقل المصدر ولم تثبت في لقطتنا",
                })
        original_nontrace = [
            str(member.get("closure") or "") for member in members
            if str(member.get("closure") or "") in LEGAL_CLOSURES
            and str(member.get("closure") or "") not in {"ROOT-TRACE", "NUCLEUS-TRACE", "SOURCE-GAP", "OPEN-CANDIDATE"}
        ]
        closures = sorted({item["closure"] for item in positive})
        if positive:
            judgment = " + ".join(closures)
            closure = judgment
            positive_card_count += 1
            positive_trace_count += len(positive)
            if any(item["source_gap"] for item in positive):
                source_gap_positive_cards += 1
        elif original_nontrace:
            closure = original_nontrace[0]
            judgment = f"غير موجب؛ عزل={closure}"
        else:
            closure = "OPEN-CANDIDATE"
            judgment = "غير صادر"
        if any(label not in LEGAL_CLOSURES for label in closures or [closure] if label != "ROOT-TRACE + NUCLEUS-TRACE"):
            raise AssertionError(f"Illegal closure label in merged card {ordinal}: {closure}")

        searches = sorted({search for member in members for search in member.get("missing_row_searches", [])})
        for item in positive:
            searches.extend(search for search in item["sound_searches"] if search not in searches)
        source_rows = sorted({source_index for member in members for source_index in member["source_rows"]})
        merged_cards.append({
            "merged_card_id": f"KIE-M{ordinal:04d}",
            "assigned_batch": min((member["card_index"] - 1) // 300 + 1 for member in members),
            "language": language,
            "original_card_indices": [member["card_index"] for member in members],
            "forms": [
                {
                    "card_index": member["card_index"],
                    "form": member["foreign"],
                    "original_language": member["language"],
                    "attestation": "source-only" if member["source_gap"] else "local-snapshot",
                    "branch_meaning": member["branch_line"],
                    "source_rows": member["source_rows"],
                }
                for member in members
            ],
            "source_rows": source_rows,
            "source_claims": [raw_rows[index] for index in source_rows],
            "fan_reviews": fan_reviews,
            "positives": positive,
            "deficiencies": deficiencies,
            "missing_row_searches": searches,
            "closure": closure,
            "judgment": judgment,
        })

    global_stats = {
        "original_cards": 1500,
        "merged_cards": len(merged_cards),
        "cards_saved": 1500 - len(merged_cards),
        "positive_cards": positive_card_count,
        "positive_traces": positive_trace_count,
        "positive_cards_with_source_gap": source_gap_positive_cards,
        "by_language": dict(sorted(Counter(card["language"] for card in merged_cards).items())),
        "wake_family": [member["foreign"] for member in wake_group],
    }

    by_language_cards: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for card in merged_cards:
        by_language_cards[card["language"]].append(card)

    for language in TARGET_LANGUAGES:
        path = READINGS / f"{language}.md"
        text = path.read_text(encoding="utf-8")
        text = re.sub(rf"\n?{re.escape(START)}.*?{re.escape(END)}\n?", "\n", text, flags=re.DOTALL)
        cards_here = by_language_cards[language]
        lines = [
            START,
            "",
            "## إعادة القراءة المدمجة لدفعات خشيم الهنديّة الأوربيّة 001 إلى 005 (2026-08-12)",
            "",
            f"- سطر النسخ الجمعي: البطاقات أدناه ناسخة للأعضاء القديمة المسماة فيها من الدفعات الخمس؛ بقي التاريخ القديم في موضعه ولم يمح.",
            f"- قاعدة الحكم: الصوت بمسار مسمى، والحدث من السجل المجمّد كما هو، ومعنى الفرع مع مدار مكتوب. لا شرط رابع.",
            f"- قاعدة المصدر: غياب صورة نقلها خشيم عن لقطتنا يسجل `SOURCE-GAP` في حقل النقص فقط، ولا يدخل حقل الحكم.",
            f"- التوزيع: في هذا الملف {len(cards_here)} بطاقة لأن الإسناد اتبع مادة اللسان وشواهده، لا ترتيب ملف الإدخال.",
            "",
        ]
        for card in cards_here:
            forms = " / ".join(f"`{item['form']}`" for item in card["forms"])
            lines.extend([
                f"### بطاقة مدمجة: {forms}؛ {card['merged_card_id']}",
                f"<!-- KHASHIM-IE-MERGED:{card['merged_card_id']} -->",
                f"- سطر النسخ: الأعضاء القديمة {card['original_card_indices']} ← {card['merged_card_id']}؛ السابق أحكام الدفعات 001 إلى 005، والجديد `{card['judgment']}`؛ السبب دمج صور الكلمة وإسقاط شرط اللقطة؛ التاريخ 2026-08-12.",
                f"- وحدة البطاقة: {len(card['forms'])} صورة؛ صفوف المصدر {card['source_rows']}؛ نسبة المقترحات والمعاني إلى علي فهمي خشيم في الكتب والصفحات المبينة في صفوف المصدر.",
            ])
            for form in card["forms"]:
                status = "مثبتة في لقطتنا" if form["attestation"] == "local-snapshot" else "الصورة من نقل المصدر ولم تثبت في لقطتنا؛ النقص `SOURCE-GAP`"
                lines.append(f"- صورة `{form['form']}`، العضو {form['card_index']}: {status}. {form['branch_meaning']}")
            source_claims = " | ".join(
                f"{item['book']} ص.{item['page']}: `{item['foreign']}` «{item['foreign_sense']}» ↔ `{item['arabic_root']}`؛ {item['arabic_gloss']}"
                for item in card["source_claims"]
            )
            lines.append(f"- نقل المصدر المسمى: {source_claims}")
            for review in card["fan_reviews"]:
                rendered = "، ".join(
                    f"`{item['root']}`[ص{item['sound']}،ح{item['event']}،م{item['meaning']}]"
                    for item in review["candidates"]
                )
                lines.append(f"- فحص كل مرشحات مروحة `{review['form']}`، العضو {review['member_index']}: {rendered}. م× تعني أن المدار الدلالي فحص ولم يثبت؛ وم؟ لا يصدر لأن رجلًا سابقة غير مكتملة.")
            if card["positives"]:
                for positive in card["positives"]:
                    evidence = lexicon_evidence[positive["root"]]["selected_sources"]
                    citations = " | ".join(
                        f"{item['source_label']}: «{quote_excerpt(item['definition'])}»"
                        for item in evidence
                    )
                    source_meaning = " | ".join(
                        f"`{item['foreign']}` «{item['foreign_sense']}» [{item['book']} ص.{item['page']}]"
                        for item in positive["source_claims"]
                    )
                    lines.extend([
                        f"- المقابل الموجب للعضو {positive['member_index']}: `{positive['root']}`؛ المسح العربي من مصدرين مستقلين كاملين في ملف البيانات: {citations}.",
                        f"- مسار الصوت المنتخب لـ`{positive['form']}` ↔ `{positive['root']}`: {positive['sound_route']}. بحث الصف: {'؛ '.join(positive['sound_searches'])}.",
                        f"- الحدث من السجل المجمّد كما هو: «{positive['frozen_event']}» [{positive['event_source']}].",
                        f"- معنى الفرع: {positive['branch_meaning']} وعند غياب اللقطة يعتمد نقل المصدر المسمى: {source_meaning}.",
                        f"- المدار المكتوب: {positive['orbit']}",
                        f"- نتيجة الأرجل الثلاث للعضو {positive['member_index']}: **{positive['closure']} (استكشاف)** بالمقابل `{positive['root']}`.",
                    ])
                issued_pairs = "، ".join(
                    f"العضو {item['member_index']} ↔ `{item['root']}`" for item in card["positives"]
                )
                lines.append(f"- الحكم (استكشاف): **{card['judgment']} (استكشاف)**؛ {issued_pairs}.")
            else:
                lines.append("- المدار المكتوب: فحصت المرشحات التي اجتمع لها ص✓ وح✓، ولم يثبت بينها مدار من معنى الفرع إلى الحدث المجمّد؛ لذلك لا موجب بلا مدار.")
                lines.append(f"- الحكم (استكشاف): **{card['judgment']} (استكشاف)**.")
            if card["deficiencies"]:
                detail = "؛ ".join(f"{item['member_index']} `{item['form']}`: {item['note']} [{item['tag']}]" for item in card["deficiencies"])
                lines.append(f"- حقل النقص، خارج الحكم: {detail}.")
            else:
                lines.append("- حقل النقص، خارج الحكم: لا `SOURCE-GAP` في صور هذه البطاقة.")
            searched = "؛ ".join(card["missing_row_searches"]) if card["missing_row_searches"] else "لم يعلن صف ناقص؛ المسار المسمى مكتمل أو لم يدخل الحكم"
            lines.extend([
                f"- ما فُتش قبل إعلان نقص صف: {searched}.",
                f"- حالة الإغلاق: {card['closure']}.",
                "",
            ])
        lines.append(END)
        path.write_text(text.rstrip() + "\n\n" + "\n".join(lines) + "\n", encoding="utf-8", newline="\n")

    for number in range(1, 6):
        rows = [card for card in merged_cards if card["assigned_batch"] == number]
        relevant_roots = sorted({positive["root"] for card in rows for positive in card["positives"]})
        payload = {
            "schema": "khashim-indo-european-batch-v2.0",
            "source_author": "علي فهمي خشيم",
            "source_books": ["khashim-journey1", "khashim-emperors"],
            "layer": "exploration",
            "batch": number,
            "merge_policy": {
                "source_claim_signature": ["book", "page", "tongue", "foreign_sense", "arabic_root", "arabic_gloss"],
                "lexical_form_similarity_minimum": 0.70,
                "explicit_same_lexeme_pairs": [[1454, 1457], [1457, 1458], [1442, 1443]],
                "snapshot_absence": "SOURCE-GAP in deficiencies only; never a judgment condition",
                "judgment_legs": ["named sound route", "frozen event", "branch meaning with written orbit"],
            },
            "cards_written": len(rows),
            "positive_cards": sum(bool(card["positives"]) for card in rows),
            "positive_traces": sum(len(card["positives"]) for card in rows),
            "by_language": dict(sorted(Counter(card["language"] for card in rows).items())),
            "global": global_stats,
            "arabic_lexicon_evidence": {root: lexicon_evidence[root] for root in relevant_roots},
            "rows": rows,
        }
        path = Path(str(BATCH_PATH).format(number=number))
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")

    digest = hashlib.sha256(json.dumps(global_stats, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()[:16]
    print(json.dumps({**global_stats, "stats_sha256": digest}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
