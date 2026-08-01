#!/usr/bin/env python3
"""Append a consonant-only Egyptian lexical snapshot in deterministic batches.

The source inventory is opened read-only.  The script adds detailed, explicitly
non-judgmental cards to the Egyptian reading; it never changes the denominator
ledger, candidate inventory, or any root/nucleus verdict.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sqlite3
import tempfile
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]
READING = ROOT / "04-cross-linguistic" / "readings" / "egyptian.md"
MANIFEST = (
    ROOT
    / "04-cross-linguistic"
    / "data"
    / "egyptian_lexical_snapshot_v1.json"
)
AUDIT_DIR = ROOT / "05-audits"
DB = ROOT / "cache" / "recovery_pipeline" / "inventory-v5.sqlite"
CORE = ROOT / "data" / "juthoor-core-levels.json"
ROOT_RESULTS = ROOT / "computational" / "data" / "layer_2_results_v2.jsonl"
DATE = "2026-08-01"
SCHEMA = "egyptian-lexical-snapshot-v1"
MARKER = "EGYPTIAN-LEXICAL-SNAPSHOT-v1"
TARGET = 3600
BATCH_SIZE = 450

BODY = (
    "body", "belly", "womb", "head", "face", "eye", "ear", "nose",
    "mouth", "tongue", "lip", "tooth", "teeth", "neck", "throat",
    "chest", "breast", "heart", "blood", "bone", "flesh", "skin",
    "hair", "hand", "finger", "arm", "leg", "foot", "feet", "back",
)
KIN = (
    "mother", "father", "parent", "brother", "sister", "son", "daughter",
    "child", "wife", "husband", "woman", "man", "family", "kin",
)
COSMOS = (
    "water", "fire", "flame", "earth", "land", "ground", "soil", "sky",
    "heaven", "sun", "moon", "star", "river", "sea", "wind", "rain",
    "night", "day",
)
PRIMARY_VERBS = (
    "be", "do", "make", "go", "come", "stand", "sit", "lie", "sleep",
    "eat", "drink", "see", "hear", "speak", "say", "tell", "give",
    "take", "bring", "carry", "live", "die", "know", "think", "love",
    "hate", "open", "close", "cut", "break", "burn", "flow",
)
LEXICAL_POS = (
    "substantive", "verb", "adjective", "adverb", "preposition", "particle",
    "pronoun", "numeral", "interjection",
)
FORBIDDEN_VOWEL_TOKENS = {
    "a", "e", "i", "o", "u", "aa", "ee", "ii", "oo", "uu",
    "ā", "ē", "ī", "ō", "ū",
}
REQUIRED_FIELDS = (
    "- إصدارُ البروتوكول:",
    "- الكلمةُ في الفرع:",
    "- أقدمُ صورةٍ مستعادة:",
    "- الخطوةُ صفر (التعرية بصرف الفرع):",
    "- درجةُ المقارنة:",
    "- مسحُ المعاني العربيّة:",
    "- المقابلُ من اللسان:",
    "- مسارُ الصوت:",
    "- المعنى من قاموس الفرع:",
    "- المدار:",
    "- المصفاة:",
    "- فصلُ المتجانسات والاقتراض:",
    "- مؤشر اليتم:",
    "- إشعاع الأسرة في الفرع:",
    "- إشعاع الأسرة في العربية:",
    "- جسورُ الاسترداد المفحوصة:",
    "- حالةُ الإغلاق:",
    "- الحكم (استكشاف):",
    "- ملاحظات:",
)


@dataclass(frozen=True)
class Entry:
    entry_id: str
    source_entry_id: str
    headword: str
    romanization: str
    pos: str
    gloss: str
    etymology: str
    loan_hint: bool
    selected_input: str
    skeleton: str
    tokens: tuple[str, ...]
    processing_status: str
    morphology_status: str


@dataclass(frozen=True)
class Candidate:
    kind: str
    form: str
    status: str
    positions: tuple[str, ...]
    rules: tuple[str, ...]
    route_flag: bool


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


def clean(value: object, limit: int = 700) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    text = text.replace("`", "'").replace("—", "-").replace("–", "-")
    return text[:limit] if len(text) > limit else text


def numeric_id(entry: Entry) -> int:
    match = re.search(r"(\d+)$", entry.source_entry_id)
    return int(match.group(1)) if match else 10**12


def english_gloss(gloss: str) -> str:
    match = re.search(r"(?:^|\|)\s*EN:\s*(.*?)(?=\s*\|\s*[A-Z]{2,3}:|$)", gloss)
    return clean(match.group(1) if match else gloss, 260)


def has_word(text: str, words: Iterable[str]) -> bool:
    return any(re.search(rf"(?<![a-z]){re.escape(word)}(?![a-z])", text) for word in words)


def basic_category(entry: Entry) -> str | None:
    gloss = english_gloss(entry.gloss).lower()
    pos = entry.pos.lower()
    if has_word(gloss, BODY):
        return "01-body"
    if has_word(gloss, KIN):
        return "02-kinship"
    if has_word(gloss, COSMOS):
        return "03-water-fire-earth-sky"
    if pos.startswith("verb") and any(
        re.search(rf"(?:^|[,;/ ]+)to\s+{re.escape(verb)}(?![a-z])", gloss)
        for verb in PRIMARY_VERBS
    ):
        return "04-primary-verbs"
    if "numeral" in pos or re.search(r"\b(one|two|three|four|five|six|seven|eight|nine|ten)\b", gloss):
        return "05-numerals"
    if "pronoun" in pos:
        if "demonstrative" in pos or "interrogative" in pos:
            return "07-demonstratives-interrogatives"
        return "06-pronouns"
    if "demonstrative" in pos or "interrogative" in pos:
        return "07-demonstratives-interrogatives"
    if re.search(r"\b(this|that|these|those|who|what|which|where|when)\b", gloss) and (
        "particle" in pos or "adverb" in pos
    ):
        return "07-demonstratives-interrogatives"
    return None


def eligible(entry: Entry) -> bool:
    if entry.selected_input != "romanization" or not entry.tokens:
        return False
    if entry.headword in {"", "_"} or entry.romanization in {"", "_"}:
        return False
    pos = entry.pos.lower()
    if any(label in pos for label in ("name", "epithet", "title", "entity")):
        return False
    if not any(pos.startswith(prefix) for prefix in LEXICAL_POS):
        return False
    if "EN:" not in entry.gloss:
        return False
    if any(token.lower() in FORBIDDEN_VOWEL_TOKENS for token in entry.tokens):
        raise RuntimeError(f"vowel token survived in {entry.entry_id}: {entry.tokens}")
    return True


def evenly_spaced(entries: list[Entry], count: int) -> list[Entry]:
    if count <= 0:
        return []
    if count >= len(entries):
        return entries[:]
    # Stable source-wide sampling prevents the detailed layer from becoming a
    # transcription of only the first alphabetic stretch of AED.
    positions = [int(index * len(entries) / count) for index in range(count)]
    return [entries[position] for position in positions]


def load_inventory() -> tuple[list[Entry], dict[str, list[Candidate]]]:
    uri = f"file:{DB.resolve().as_posix()}?mode=ro"
    connection = sqlite3.connect(uri, uri=True)
    connection.row_factory = sqlite3.Row
    try:
        rows = connection.execute(
            """
            SELECT entry_id, source_entry_id, headword, romanization, pos, gloss,
                   etymology, loan_hint, selected_input, skeleton, tokens_json,
                   processing_status, morphology_status
            FROM entries
            WHERE language = 'egyptian'
            ORDER BY CAST(source_entry_id AS INTEGER), entry_id
            """
        ).fetchall()
        candidate_rows = connection.execute(
            """
            SELECT c.entry_id, c.kind, c.form, c.status, c.positions_json,
                   c.rule_ids_json, c.route_flag
            FROM candidates c
            JOIN entries e ON e.entry_id = c.entry_id
            WHERE e.language = 'egyptian'
            ORDER BY c.entry_id, c.kind, c.form, c.status
            """
        ).fetchall()
    finally:
        connection.close()

    entries = [
        Entry(
            entry_id=row["entry_id"],
            source_entry_id=row["source_entry_id"],
            headword=row["headword"],
            romanization=row["romanization"],
            pos=row["pos"],
            gloss=row["gloss"],
            etymology=row["etymology"],
            loan_hint=bool(row["loan_hint"]),
            selected_input=row["selected_input"],
            skeleton=row["skeleton"],
            tokens=tuple(json.loads(row["tokens_json"])),
            processing_status=row["processing_status"],
            morphology_status=row["morphology_status"],
        )
        for row in rows
    ]
    candidates: dict[str, list[Candidate]] = defaultdict(list)
    for row in candidate_rows:
        candidates[row["entry_id"]].append(
            Candidate(
                kind=row["kind"],
                form=row["form"],
                status=row["status"],
                positions=tuple(json.loads(row["positions_json"])),
                rules=tuple(json.loads(row["rule_ids_json"])),
                route_flag=bool(row["route_flag"]),
            )
        )
    return entries, candidates


def existing_source_ids() -> set[str]:
    text = READING.read_text(encoding="utf-8")
    return set(re.findall(r"aed-v1\.0:(\d+)", text))


def choose(entries: list[Entry]) -> tuple[list[Entry], dict[str, str]]:
    existing = existing_source_ids()
    pool = [entry for entry in entries if entry.source_entry_id not in existing and eligible(entry)]
    categories = {entry.entry_id: basic_category(entry) for entry in pool}
    basic = sorted(
        (entry for entry in pool if categories[entry.entry_id]),
        key=lambda entry: (categories[entry.entry_id] or "", numeric_id(entry)),
    )
    selected = basic[:TARGET]
    if len(selected) < TARGET:
        selected_ids = {entry.entry_id for entry in selected}
        general = sorted(
            (entry for entry in pool if entry.entry_id not in selected_ids),
            key=numeric_id,
        )
        selected.extend(evenly_spaced(general, TARGET - len(selected)))
    if len(selected) != TARGET:
        raise RuntimeError(f"wanted {TARGET} entries, selected {len(selected)}")
    selected_categories = {
        entry.entry_id: categories[entry.entry_id] or "08-core-lexicon"
        for entry in selected
    }
    return selected, selected_categories


def load_readings() -> tuple[dict[str, str], dict[str, str]]:
    root_readings: dict[str, str] = {}
    for line in ROOT_RESULTS.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        form = clean(row.get("tri_root"))
        reading = clean(row.get("jabal_axial"), 220)
        if form and reading:
            root_readings.setdefault(form, reading)
    core = json.loads(CORE.read_text(encoding="utf-8"))
    nuclei = core["levels"]["level_2_binary_nuclei"]["nuclei"]
    nucleus_readings = {
        clean(row["nucleus"]): clean(row.get("jabal_lexicon_reading_ar"), 220)
        for row in nuclei
        if row.get("nucleus")
    }
    return root_readings, nucleus_readings


def candidate_text(
    items: list[Candidate], kind: str, readings: dict[str, str], limit: int
) -> str:
    relevant = [item for item in items if item.kind == kind]
    if not relevant:
        return "لا مرشّح آلي في هذه الطبقة"
    rendered: list[str] = []
    for item in relevant[:limit]:
        positions = ",".join(item.positions) or "غير مسجل"
        rules = ",".join(item.rules) or "هوية"
        reading = readings.get(item.form, "قراءة معجميّة غير موصولة في المصدّر")
        route = "; route-flag" if item.route_flag else ""
        rendered.append(
            f"'{clean(item.form)}' «{reading}» [{clean(item.status)}؛ الموضع {positions}؛ {rules}{route}]"
        )
    omitted = len(relevant) - len(rendered)
    if omitted:
        rendered.append(f"و{omitted} مرشّحًا آليًا آخر")
    return "؛ ".join(rendered)


def render_card(
    entry: Entry,
    category: str,
    ordinal: int,
    items: list[Candidate],
    root_readings: dict[str, str],
    nucleus_readings: dict[str, str],
) -> str:
    gloss = english_gloss(entry.gloss) or clean(entry.gloss, 260)
    tokens = "-".join(clean(token, 40) for token in entry.tokens)
    roots = candidate_text(items, "root", root_readings, 4)
    nuclei = candidate_text(items, "nucleus", nucleus_readings, 6)
    named_source = clean(entry.etymology, 500) or "لا بيان اشتقاق منشور في حقل المصدر"
    gap = "SOURCE-GAP" if entry.loan_hint else "OPEN-CANDIDATE"
    loan_filter = (
        "في AED إشارة اقتراض أو اشتقاق خارجي؛ لا تُحوّل الإشارة العامة إلى حكم وراثة أو نقل، "
        "ولا يُصدر شيء قبل تسمية المانح والطريق على هذا العضو"
        if entry.loan_hint
        else "لا يسمّي حقل المصدر مانحًا مفردًا لهذا العضو؛ وهذا غياب دليل نقل لا برهان أصالة"
    )
    return f"""### بطاقة: `{clean(entry.romanization, 120)}` «{gloss}» - اللقطة المعجميّة {ordinal}/{TARGET}
<!-- {MARKER}:aed-v1.0:{entry.source_entry_id} -->
- عائق: النوع={gap}؛ يتطلب=فحص المعنيين العربيين من معجمين قديمين، ثم توقيع المسار الصوتي والاتجاه إن وُجد.
- إصدارُ البروتوكول: RECOVERY-v2 (2026-07-14)؛ بطاقة تغطية تفصيليّة بلا حكم.
- الكلمةُ في الفرع: `{clean(entry.romanization, 160)}`؛ الرسم المعجمي `{clean(entry.headword, 160)}`؛ النوع `{clean(entry.pos, 120)}`؛ العضو `aed-v1.0:{entry.source_entry_id}`؛ الفئة `{category}`.
- أقدمُ صورةٍ مستعادة: لا تُنشأ صورة صوتيّة ولا حركة معادة البناء؛ يؤخذ الرسم والرومنة المنشوران من AED، وبيان المصدر: {named_source}.
- الخطوةُ صفر (التعرية بصرف الفرع): الهيكل الصامتي المباشر من `tokens_json` هو `{tokens}`؛ الحركات المعاد بناؤها مستبعدة من الإدخال والترتيب والحكم.
- درجةُ المقارنة: الجذر والنواة يُعرضان كمرشّحين مستقلين للاسترداد فقط؛ لا رجوع من فشل الجذر إلى النواة، ولا حكم صادر في هذه البطاقة.
- مسحُ المعاني العربيّة: لم يكتمل بعد فحص المعنى المحدد في معجمين عربيين قديمين؛ المروحة أدناه مروحة استرداد لا إثبات دلالي.
- المقابلُ من اللسان: مرشّحات الجذر: {roots}. مرشّحات النواة: {nuclei}.
- مسارُ الصوت: لا مسار مصري-عربي موقع؛ الظاهر فقط هويات الصوامت أو معرّفات الصفوف المسجلة مع كل مرشّح، من غير إدخال صوائت معادة البناء.
- المعنى من قاموس الفرع: «{gloss}» [AED {entry.source_entry_id}]؛ النص الكامل المثبّت في المصدر: {clean(entry.gloss, 500)}.
- المدار: معنى العضو المفرد أعلاه فقط؛ لا يتسع إلى متجانس أو مشتق أو جار أسرة.
- المصفاة: {loan_filter}.
- فصلُ المتجانسات والاقتراض: العضو `aed-v1.0:{entry.source_entry_id}` مستقل؛ لا يرث حكم متحد الرسم، ولا يمنح اقتراض عضو آخر، ولا يدخل بسط الوراثة بلا فصل فردي.
- مؤشر اليتم: لا شاهد عربي مسمى ومحقق بعد؛ يبقى العضو خارج البسط ولا يرفع مرشّحًا بمجرد التشابه الصامتي.
- إشعاع الأسرة في الفرع: لا إشعاع حكمي؛ هذه بطاقة عضو واحد ولا تنقل شيئًا إلى مشتقاته أو متجانساته.
- إشعاع الأسرة في العربية: لا إشعاع حكمي؛ المرشّحات الظاهرة مفاتيح بحث لا أعضاء عائلة مثبتة.
- جسورُ الاسترداد المفحوصة: الهيكل الصامتي المباشر؛ مرشّحات الجذر؛ مرشّحات النواة؛ إشارة القرض في المصدر؛ بقي فحص المعنى والمسار والاتجاه مفتوحًا.
- حالةُ الإغلاق: {gap}؛ البطاقة تفصيليّة مكتملة الحقول، لكن التحقيق المقارن غير مغلق.
- الحكم (استكشاف): **غير صادر**؛ البطاقة خارج بسط الوراثة، ولا تغيير في العدّ السابق.
- ملاحظات: توسعة للطبقة المعجميّة المصريّة، وحالة المعالجة `{clean(entry.processing_status, 100)}` وحالة الصرف `{clean(entry.morphology_status, 100)}`؛ يبقى سطر المقام الأصلي وسجل الطبقتين كما هما.
"""


def chunks(items: list[Entry], size: int) -> Iterable[list[Entry]]:
    for start in range(0, len(items), size):
        yield items[start : start + size]


def manifest_for(selected: list[Entry], categories: dict[str, str]) -> dict[str, object]:
    ids = [entry.source_entry_id for entry in selected]
    digest = hashlib.sha256("\n".join(ids).encode("utf-8")).hexdigest()
    return {
        "schema": SCHEMA,
        "date": DATE,
        "source": "AED v1.0 via inventory-v5.sqlite opened read-only",
        "method": "basic lexicon first, then evenly spaced source-wide core lexicon",
        "judgment_policy": "coverage cards only; no root/nucleus/inheritance verdicts",
        "consonant_policy": "tokens_json from published romanization; reconstructed vowels excluded",
        "target": TARGET,
        "batch_size": BATCH_SIZE,
        "batch_count": (TARGET + BATCH_SIZE - 1) // BATCH_SIZE,
        "category_counts": dict(sorted(Counter(categories.values()).items())),
        "source_entry_ids": ids,
        "source_entry_ids_sha256": digest,
    }


def render_appendix(
    selected: list[Entry],
    categories: dict[str, str],
    candidates: dict[str, list[Candidate]],
) -> str:
    root_readings, nucleus_readings = load_readings()
    blocks = [
        "\n## اللقطة المعجميّة المصريّة الموسّعة: الهيكل الصامتي المباشر (2026-08-01)\n",
        "<!-- RECOVERY-PROTOCOL-v2 -->\n",
        "<!-- RADIATION-FIELDS-v1 -->\n",
        f"<!-- {MARKER}:BEGIN -->\n\n",
        "هذه طبقة وصف تفصيلي موازية لسجل المقام الكامل. تبدأ بالمعجم الأساسي، ثم عيّنة موزعة على امتداد AED حتى تقارب كثافة بطاقات اللقطة القبطية. لا تستبدل سطر تغطية، ولا تصدر حكمًا، ولا تدخل حركة معادة البناء في الاسترداد أو الحكم.\n",
    ]
    ordinal = 0
    for batch_number, batch in enumerate(chunks(selected, BATCH_SIZE), start=1):
        start = ordinal + 1
        end = ordinal + len(batch)
        batch_counts = Counter(categories[entry.entry_id] for entry in batch)
        summary = "؛ ".join(f"{key}={value}" for key, value in sorted(batch_counts.items()))
        blocks.append(
            f"\n## دفعة اللقطة المصريّة {batch_number:03d}: البطاقات {start}-{end}\n"
            f"<!-- {MARKER}:BATCH:{batch_number:03d} -->\n\n"
            f"- توزيع الدفعة: {summary}.\n"
            "- قيد الحكم: كل البطاقات الآتية خارج البسط حتى يكتمل التحقيق الفردي.\n\n"
        )
        for entry in batch:
            ordinal += 1
            blocks.append(
                render_card(
                    entry,
                    categories[entry.entry_id],
                    ordinal,
                    candidates.get(entry.entry_id, []),
                    root_readings,
                    nucleus_readings,
                )
            )
            blocks.append("\n")
    blocks.append(f"<!-- {MARKER}:END -->\n")
    return "".join(blocks)


def render_audit(
    batch_number: int,
    batch: list[Entry],
    categories: dict[str, str],
    candidates: dict[str, list[Candidate]],
) -> str:
    counts = Counter(categories[entry.entry_id] for entry in batch)
    root_members = sum(any(c.kind == "root" for c in candidates.get(e.entry_id, [])) for e in batch)
    nucleus_members = sum(any(c.kind == "nucleus" for c in candidates.get(e.entry_id, [])) for e in batch)
    loan_hints = sum(entry.loan_hint for entry in batch)
    category_lines = "\n".join(f"- `{key}`: {value}" for key, value in sorted(counts.items()))
    return f"""# محضر دفعة اللقطة المصريّة {batch_number:03d}

- التاريخ: {DATE}
- المخطط: `{SCHEMA}`
- المجال: `aed-v1.0:{batch[0].source_entry_id}` إلى `aed-v1.0:{batch[-1].source_entry_id}` ضمن ترتيب اللقطة، وعدد البطاقات {len(batch)}.
- المصدر: `inventory-v5.sqlite` بوضع القراءة فقط؛ لم يكتب البرنامج في قاعدة الجرد ولا في سجلي المقام والطبقتين.
- الهيكل: `tokens_json` المشتق من الرومنة المنشورة؛ لا صائت معاد البناء في البطاقة أو المطابقة.
- مرشّح جذر آلي ظاهر: {root_members} عضوًا؛ مرشّح نواة آلي ظاهر: {nucleus_members} عضوًا؛ إشارة قرض مصدرية: {loan_hints} أعضاء.
- الحكم (استكشاف): صفر أحكام جديدة؛ كل البطاقات `OPEN-CANDIDATE` أو `SOURCE-GAP` وخارج بسط الوراثة.
- الأداة: تنفيذ محلي متتابع، بلا git وبلا كتابة في أداة أو مخزن مشترك.

## توزيع الفئات

{category_lines}
"""


def card_sections(text: str) -> dict[str, str]:
    sections: dict[str, str] = {}
    pattern = re.compile(
        rf"(?ms)^### بطاقة:.*?^<!-- {re.escape(MARKER)}:aed-v1\.0:(\d+) -->\n(.*?)(?=^### بطاقة:|^## |^<!-- {re.escape(MARKER)}:END -->)"
    )
    for source_id, section in pattern.findall(text):
        if source_id in sections:
            raise RuntimeError(f"duplicate snapshot card: {source_id}")
        sections[source_id] = section
    return sections


def validate(manifest: dict[str, object] | None = None) -> str:
    if manifest is None:
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    text = READING.read_text(encoding="utf-8")
    sections = card_sections(text)
    expected_ids = list(manifest["source_entry_ids"])
    if set(sections) != set(expected_ids):
        missing = sorted(set(expected_ids) - set(sections))[:5]
        extra = sorted(set(sections) - set(expected_ids))[:5]
        raise RuntimeError(f"snapshot card mismatch: missing={missing}, extra={extra}")
    for source_id in expected_ids:
        section = sections[source_id]
        missing_fields = [field for field in REQUIRED_FIELDS if field not in section]
        if missing_fields:
            raise RuntimeError(f"card {source_id} lacks fields: {missing_fields}")
        if "**غير صادر**" not in section:
            raise RuntimeError(f"card {source_id} accidentally lacks non-verdict")
        zero = re.search(r"^- الخطوةُ صفر .*?$", section, re.MULTILINE)
        if not zero or "الحركات المعاد بناؤها مستبعدة" not in zero.group(0):
            raise RuntimeError(f"card {source_id} lacks consonant-only assertion")
    digest = hashlib.sha256("\n".join(expected_ids).encode("utf-8")).hexdigest()
    if digest != manifest["source_entry_ids_sha256"]:
        raise RuntimeError("manifest source ID digest mismatch")
    if text.count(f"<!-- {MARKER}:BATCH:") != manifest["batch_count"]:
        raise RuntimeError("batch marker count mismatch")
    return (
        f"Egyptian lexical snapshot: CLEAN ({len(sections)} cards, "
        f"{manifest['batch_count']} batches, consonant-only, zero verdicts)"
    )


def plan() -> tuple[list[Entry], dict[str, str], dict[str, list[Candidate]], dict[str, object]]:
    entries, candidates = load_inventory()
    selected, categories = choose(entries)
    manifest = manifest_for(selected, categories)
    return selected, categories, candidates, manifest


def apply() -> str:
    if MANIFEST.exists():
        return validate()
    selected, categories, candidates, manifest = plan()
    reading = READING.read_text(encoding="utf-8").rstrip() + "\n"
    atomic_write(READING, reading + render_appendix(selected, categories, candidates))
    atomic_write(MANIFEST, json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    for batch_number, batch in enumerate(chunks(selected, BATCH_SIZE), start=1):
        audit = AUDIT_DIR / f"2026-08-01-egyptian-lexical-snapshot-batch-{batch_number:03d}.md"
        atomic_write(audit, render_audit(batch_number, batch, categories, candidates))
    return validate(manifest)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("plan", "apply", "validate"))
    args = parser.parse_args()
    if args.command == "validate":
        print(validate())
        return
    if args.command == "apply":
        print(apply())
        return
    selected, categories, candidates, manifest = plan()
    root_members = sum(any(c.kind == "root" for c in candidates.get(e.entry_id, [])) for e in selected)
    nucleus_members = sum(any(c.kind == "nucleus" for c in candidates.get(e.entry_id, [])) for e in selected)
    print(json.dumps({
        "target": len(selected),
        "batches": manifest["batch_count"],
        "categories": manifest["category_counts"],
        "root_candidate_members": root_members,
        "nucleus_candidate_members": nucleus_members,
        "loan_hint_members": sum(entry.loan_hint for entry in selected),
        "first": selected[0].entry_id,
        "last": selected[-1].entry_id,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
