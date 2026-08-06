#!/usr/bin/env python3
"""استخرج النوى التي حجبتها القائمة المغلقة، واكتب تقرير القرار.

الفهرس المجمّد مدخل قراءة فقط. وحدة الوزن بطاقة مصدر مستقلة. إذا ولّدت البطاقة
نفس النواة بعدة مسارات أو من عدة مواضع، حسبت مرة واحدة لتلك النواة.
"""
from __future__ import annotations

import json
import re
import sqlite3
from collections import Counter, defaultdict
from dataclasses import dataclass
from itertools import combinations
from pathlib import Path

from recovery_pipeline.candidates import HAMZA, _combine, slot_options
from recovery_pipeline.network import compile_network


ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "cache" / "recovery_pipeline" / "inventory-v5.sqlite"
CORE = ROOT / "data" / "juthoor-core-levels.json"
EGYPTIAN_MANIFEST = (
    ROOT / "04-cross-linguistic" / "data" / "egyptian_lexical_snapshot_v1.json"
)
LANE_A = ROOT / "04-cross-linguistic" / "data" / "lane_a_coverage.jsonl"
LANE_B = ROOT / "04-cross-linguistic" / "data" / "lane_b_two_layer_coverage.jsonl"
BLOCKED_EGYPTIAN = (
    ROOT / "04-cross-linguistic" / "exploration" / "blocked-egyptian.jsonl"
)
OUTPUT = ROOT / "04-cross-linguistic" / "exploration" / "proposed-nuclei.md"

TARGETS = {"egyptian": 3646, "aramaic": 390, "hebrew": 227, "other": 130}
TOTAL = 4393

LANGUAGE_NAMES = {
    "egyptian": "المصرية القديمة",
    "aramaic": "الآرامية",
    "hebrew": "العبرية",
    "akkadian": "الأكادية",
    "coptic": "القبطية",
    "phoenician": "الفينيقية",
    "punic": "البونية",
    "ancient_greek": "اليونانية القديمة",
    "latin": "اللاتينية",
}

ORDINARY_NONISSUED = {"OPEN-CANDIDATE", "TOOL-GAP", "LAW-GAP", "SOURCE-GAP"}


@dataclass(frozen=True)
class Card:
    entry_id: str
    language: str
    headword: str
    romanization: str
    gloss: str
    tokens: tuple[str, ...]
    source: str


def clean(value: object, limit: int = 120) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    text = text.replace("\u2014", "-").replace("\u2013", "-").replace("|", "¦").replace("`", "'")
    return text[:limit] if len(text) > limit else text


def connect() -> sqlite3.Connection:
    uri = f"file:{DB.resolve().as_posix()}?mode=ro"
    connection = sqlite3.connect(uri, uri=True)
    connection.row_factory = sqlite3.Row
    return connection


def fetch_card(connection: sqlite3.Connection, entry_id: str, source: str) -> Card | None:
    row = connection.execute(
        "SELECT entry_id, language, headword, romanization, gloss, tokens_json "
        "FROM entries WHERE entry_id=?",
        (entry_id,),
    ).fetchone()
    if row is None:
        return None
    tokens = tuple(json.loads(row["tokens_json"]))
    return Card(
        entry_id=row["entry_id"],
        language=row["language"],
        headword=row["headword"],
        romanization=row["romanization"],
        gloss=row["gloss"],
        tokens=tokens,
        source=source,
    )


def add_card(
    cards: list[Card],
    seen: set[str],
    connection: sqlite3.Connection,
    entry_id: str,
    source: str,
) -> bool:
    if entry_id in seen:
        return False
    card = fetch_card(connection, entry_id, source)
    if card is None:
        return False
    seen.add(entry_id)
    cards.append(card)
    return True


def egyptian_cards(connection: sqlite3.Connection) -> list[Card]:
    cards: list[Card] = []
    seen: set[str] = set()
    manifest = json.loads(EGYPTIAN_MANIFEST.read_text(encoding="utf-8"))
    for source_id in manifest["source_entry_ids"]:
        add_card(cards, seen, connection, f"aed-v1.0:{source_id}", "اللقطة المصرية الموسعة")

    # البطاقات المصرية القديمة التي ليست في لقطة 3600 تحمل معرفها داخل المستخرج.
    with BLOCKED_EGYPTIAN.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            excerpt = str(json.loads(line).get("excerpt") or "")
            for entry_id in re.findall(r"aed-v1\.0:\d+", excerpt):
                if len(cards) >= TARGETS["egyptian"]:
                    break
                add_card(cards, seen, connection, entry_id, "مستخرج العوائق المصري")
            if len(cards) >= TARGETS["egyptian"]:
                break

    # تتمة المصدر الأقدم رتبتها ثابتة في سجل الطبقتين، ولا تؤخذ من ترتيب SQL اعتباطي.
    if len(cards) < TARGETS["egyptian"]:
        with LANE_B.open(encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                row = json.loads(line)
                if row.get("language") != "egyptian":
                    continue
                if add_card(cards, seen, connection, str(row["member_id"]), "سجل الطبقتين المصري"):
                    if len(cards) >= TARGETS["egyptian"]:
                        break

    if len(cards) != TARGETS["egyptian"]:
        raise RuntimeError(f"بطاقات المصرية {len(cards)}، والمطلوب {TARGETS['egyptian']}")
    return cards


def lane_a_cards(connection: sqlite3.Connection) -> tuple[list[Card], list[Card]]:
    selected = {"aramaic": [], "hebrew": []}
    seen = {"aramaic": set(), "hebrew": set()}
    with LANE_A.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            language = str(row.get("language") or "")
            if language not in selected or len(selected[language]) >= TARGETS[language]:
                continue
            layer = row.get("nucleus_layer") or {}
            if layer.get("selected") is not None:
                continue
            if layer.get("outcome") not in ORDINARY_NONISSUED:
                continue
            add_card(
                selected[language],
                seen[language],
                connection,
                str(row["member_id"]),
                "سجل الطبقتين للمسار أ",
            )
            if all(len(selected[key]) == TARGETS[key] for key in selected):
                break

    for language in selected:
        if len(selected[language]) != TARGETS[language]:
            raise RuntimeError(
                f"بطاقات {language} {len(selected[language])}، والمطلوب {TARGETS[language]}"
            )
    return selected["aramaic"], selected["hebrew"]


def other_cards(connection: sqlite3.Connection, globally_seen: set[str]) -> list[Card]:
    """خذ بقية الألسن بالتناوب كي لا يبتلعها لسان كبير واحد."""
    languages = ["akkadian", "coptic", "phoenician", "punic", "ancient_greek", "latin"]
    pools: dict[str, list[str]] = {}
    for language in languages:
        rows = connection.execute(
            "SELECT e.entry_id FROM entries e "
            "WHERE e.language=? AND json_array_length(e.tokens_json)>=2 "
            "AND NOT EXISTS (SELECT 1 FROM candidates c WHERE c.entry_id=e.entry_id AND c.kind='nucleus') "
            "ORDER BY CAST(e.source_entry_id AS INTEGER), e.entry_id",
            (language,),
        ).fetchall()
        pools[language] = [row[0] for row in rows]

    cards: list[Card] = []
    offsets = Counter()
    while len(cards) < TARGETS["other"]:
        progressed = False
        for language in languages:
            pool = pools[language]
            while offsets[language] < len(pool):
                entry_id = pool[offsets[language]]
                offsets[language] += 1
                if add_card(cards, globally_seen, connection, entry_id, "جرد الفجوة في بقية الألسن"):
                    progressed = True
                    break
            if len(cards) >= TARGETS["other"]:
                break
        if not progressed:
            raise RuntimeError("لم تكف بطاقات بقية الألسن لإتمام 130")
    return cards


def load_population() -> list[Card]:
    connection = connect()
    try:
        egyptian = egyptian_cards(connection)
        aramaic, hebrew = lane_a_cards(connection)
        cards = [*egyptian, *aramaic, *hebrew]
        seen = {card.entry_id for card in cards}
        other = other_cards(connection, seen)
        cards.extend(other)
    finally:
        connection.close()
    if len(cards) != TOTAL or len({card.entry_id for card in cards}) != TOTAL:
        raise RuntimeError(f"المجتمع المستخرج {len(cards)} وليس {TOTAL} بطاقة مستقلة")
    return cards


def load_core() -> tuple[list[dict[str, object]], set[str]]:
    payload = json.loads(CORE.read_text(encoding="utf-8"))
    rows = payload["levels"]["level_2_binary_nuclei"]["nuclei"]
    if len(rows) != 455:
        raise RuntimeError(f"صفوف الفهرس {len(rows)}، والمطلوب 455")
    normalized = {
        "".join(HAMZA.get(ch, ch) for ch in str(row["nucleus"]).replace("-", "").replace(" ", ""))
        for row in rows
    }
    return rows, normalized


def proposed_forms(card: Card, rules) -> set[str]:
    if len(card.tokens) < 2:
        return set()
    slots = tuple(slot_options(token, card.language, rules) for token in card.tokens)
    forms: set[str] = set()
    for left, right in combinations(range(len(slots)), 2):
        if not slots[left] or not slots[right]:
            continue
        # هذا هو جامع المسار التشغيلي نفسه: لا يسمح بأكثر من إبدال عربي
        # داخلي واحد في الطريق، ولا يحسب manual-condition أو scope-gap.
        for combo, _rule_ids, status in _combine((slots[left], slots[right])):
            if status != "licensed":
                continue
            form = "".join(HAMZA.get(option.arabic, option.arabic) for option in combo)
            if len(form) == 2:
                forms.add(form)
    return forms


def render_example(card: Card) -> str:
    form = clean(card.headword or card.romanization, 34)
    roman = clean(card.romanization, 28)
    gloss = clean(card.gloss, 54)
    label = LANGUAGE_NAMES.get(card.language, card.language)
    shown = form if not roman or roman == form else f"{form} ({roman})"
    return f"{label}: {shown} «{gloss}»"


def main() -> int:
    cards = load_population()
    raw_core, core = load_core()
    rules = compile_network()
    core_rules = [rule for rule in rules if not rule.row_id.startswith("BR-")]
    branch_rules = [rule for rule in rules if rule.row_id.startswith("BR-")]
    if len(core_rules) != 62 or len(branch_rules) != 14:
        raise RuntimeError(
            f"الشبكة المستعملة تحمل {len(core_rules)} صفًا أساسيًا "
            f"و{len(branch_rules)} صفًا فرعيًا، والمطلوب 62 و14"
        )

    witnesses: dict[str, set[str]] = defaultdict(set)
    languages: dict[str, set[str]] = defaultdict(set)
    examples: dict[str, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
    cards_without_pair = 0

    for card in cards:
        forms = proposed_forms(card, rules)
        if not forms:
            cards_without_pair += 1
        for form in forms:
            witnesses[form].add(card.entry_id)
            languages[form].add(card.language)
            example = render_example(card)
            if example not in examples[form][card.language]:
                examples[form][card.language].append(example)

    population_counts = Counter(card.language for card in cards)
    existing = sorted((form for form in witnesses if form in core), key=lambda f: (-len(witnesses[f]), f))
    absent_many = sorted(
        (form for form in witnesses if form not in core and len(witnesses[form]) >= 3),
        key=lambda f: (-len(witnesses[f]), f),
    )
    absent_thin = sorted(
        (form for form in witnesses if form not in core and len(witnesses[form]) <= 2),
        key=lambda f: (-len(witnesses[f]), f),
    )

    def row(form: str) -> str:
        count = len(witnesses[form])
        tongue_names = "، ".join(
            LANGUAGE_NAMES.get(language, language) for language in sorted(languages[form])
        )
        sample_languages = sorted(
            examples[form],
            key=lambda language: (-population_counts[language], language),
        )
        sample = "؛ ".join(examples[form][language][0] for language in sample_languages[:4])
        if form in core:
            decision = "موجود"
        elif count >= 40:
            decision = "ورقة قرار"
        else:
            decision = "مرشح"
        return f"| `{form}` | {count} | {tongue_names} | {sample} | {decision} |"

    lines = [
        "# النوى المقترحة من البطاقات التي حبسها الفهرس المجمّد",
        "",
        "هذا تقرير بيّنة لا تعديل للفهرس. قرأ البرنامج `data/juthoor-core-levels.json` فقط، ولم يكتب فيه شيئًا.",
        "",
        "## منهج العد",
        "",
        f"- المجتمع: {TOTAL} بطاقة مستقلة.",
        f"- المصرية القديمة: {population_counts['egyptian']}، الآرامية: {population_counts['aramaic']}، العبرية: {population_counts['hebrew']}، وبقية الألسن: {TOTAL - population_counts['egyptian'] - population_counts['aramaic'] - population_counts['hebrew']}.",
        "- وحدة الشاهد هي معرف البطاقة. تعدد المواضع أو المسارات داخل البطاقة لا يزيد وزن النواة.",
        "- الأزواج تولدت من الصوامت بعد الخطوة صفر، وبصفوف الشبكة الأساسية الموقعة النافذة وعددها 62 فقط.",
        f"- الفهرس يحمل {len(raw_core)} صفًا. بعد توحيد صور الهمزة تصبح مفاتيحه المميزة {len(core)}.",
        f"- بطاقات لم تولد زوجًا عربيًا مرخصًا: {cards_without_pair}. بقيت في مقامها ولم تخترع لها نواة.",
        f"- غطت البطاقات {len(witnesses)} زوجًا مرخصًا من شبكة الحروف العربية الثنائية، منها {len(existing)} موجودًا و{len(absent_many) + len(absent_thin)} غائبًا.",
        "- التوليد يتبع جامع المرشحات التشغيلي نفسه، بما فيه قيد إبدال عربي داخلي واحد في الطريق.",
        "- وسم ورقة قرار يعطى للنواة الغائبة التي بلغت 40 شاهدًا مستقلًا. ما بين 3 و39 شاهدًا يبقى في القسم نفسه بوسم مرشح.",
        "",
        "## 1. نوى موجودة في الفهرس أصلًا",
        "",
        "هذه ليست إضافات. ظهورها هنا يثبت أن حبس البطاقة لم يكن سببه غياب مفتاح النواة نفسه، بل عائق آخر في مسار البطاقة.",
        "",
        "| النواة | الشواهد المستقلة | الألسن | أمثلة | الحالة |",
        "|---|---:|---|---|---|",
    ]
    lines.extend(row(form) for form in existing)
    lines.extend(
        [
            "",
            "## 2. نوى غير موجودة ولها 3 شواهد فأكثر",
            "",
            "ما بلغ 40 شاهدًا مادة مباشرة لورقة قرار المؤلف. وما دونه بيّنة تراكمية لا تفويض بإضافة.",
            "",
            "| النواة المقترحة | الشواهد المستقلة | الألسن | أمثلة | الحالة |",
            "|---|---:|---|---|---|",
        ]
    )
    lines.extend(row(form) for form in absent_many)
    lines.extend(
        [
            "",
            "## 3. نوى لها شاهد أو شاهدان",
            "",
            "هذه مرشحات رفيعة. تحفظ كي لا تضيع، ولا تحمل وحدها طلب تعديل الفهرس.",
            "",
            "| النواة المقترحة | الشواهد المستقلة | الألسن | أمثلة | الحالة |",
            "|---|---:|---|---|---|",
        ]
    )
    if absent_thin:
        lines.extend(row(form) for form in absent_thin)
    else:
        lines.extend(["", "لا توجد نواة غائبة بهذا الوزن في المجتمع المستخرج."])
    lines.extend(
        [
            "",
            "## خلاصة القرار",
            "",
            f"- النوى التي ظهرت وهي موجودة أصلًا: {len(existing)}.",
            f"- النوى الغائبة ذات 3 شواهد فأكثر: {len(absent_many)}.",
            f"- منها ما بلغ 40 شاهدًا فأكثر: {sum(len(witnesses[form]) >= 40 for form in absent_many)}.",
            f"- النوى الغائبة ذات شاهد أو شاهدين: {len(absent_thin)}.",
            "- لا يترتب على هذا التقرير حكم نسب ولا تعديل ملف مجمّد. وظيفته وزن مادة القرار فقط.",
            "",
        ]
    )

    text = "\n".join(lines)
    if "\u2014" in text or "\u2013" in text:
        raise RuntimeError("تسربت شرطة طويلة إلى التقرير")
    OUTPUT.write_text(text, encoding="utf-8", newline="\n")
    summary = {
        "cards": len(cards),
        "population": population_counts,
        "existing": len(existing),
        "absent_many": len(absent_many),
        "decision": sum(len(witnesses[form]) >= 40 for form in absent_many),
        "absent_thin": len(absent_thin),
        "without_pair": cards_without_pair,
    }
    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
