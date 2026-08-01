#!/usr/bin/env python3
"""Section 26 recovery for Lane A (Hebrew and Aramaic only).

This is deliberately a lane-local, one-shot batch tool.  It does not import or
modify the shared builders.  Each invocation rewrites only the two Lane A
readings as needed, the Lane A coverage ledger, a Lane A data inventory, and
one dated Lane A audit.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import tempfile
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
READINGS = {
    "hebrew": ROOT / "04-cross-linguistic/readings/hebrew.md",
    "aramaic": ROOT / "04-cross-linguistic/readings/aramaic.md",
}
COVERAGE = ROOT / "04-cross-linguistic/data/lane_a_coverage.jsonl"
NAME_ROOTS = ROOT / "04-cross-linguistic/data/lane_a_name_roots.jsonl"
DB = ROOT / "cache/recovery_pipeline/inventory-v5.sqlite"
AUDIT_DIR = ROOT / "05-audits"

CARD_START = re.compile(
    r"(?m)^### (?:بطاقة|مراجعة عضوية|إعادة توسيم):[^\n]*(?:\n|$)"
)
SECTION_START = re.compile(r"(?m)^## [^\n]*(?:\n|$)")
ENTRY_ID = re.compile(r"kaikki_(?:hebrew|aramaic):\d+:[^\s`؛،\]\)]+")
VERDICT = re.compile(r"(?m)^- الحكم \(استكشاف\):\s*`?([A-Z][A-Z0-9-]*)")
STATE = re.compile(r"(?m)^- حالةُ الإغلاق:\s*`?([A-Z][A-Z0-9-]*)")
FAMILY_ID = re.compile(r"(?:hebrew|aramaic):family:[0-9a-f]+")
HEBREW_CHARS = re.compile(r"[\u0590-\u05ff]+")
ARAMAIC_CHARS = re.compile(r"[\u0700-\u074f]+")

POSITIVE = {
    "ROOT-TRACE",
    "NUCLEUS-TRACE",
    "ROOT-ECHO",
    "NUCLEUS-ECHO",
    "FLOOR-TRACE",
}
FORM_STATES = {"FORM-OF-ISOLATED"}
NONLEX_STATES = {"NONLEXICAL-ISOLATED", "FUNCTION-WORD-ISOLATED"}
LOAN_STATES = {"LOANWORD"}
NAME_STATES = {"PROPER-NAME-ISOLATED"}
FUNCTION_POS = {
    "num",
    "number",
    "pron",
    "pronoun",
    "article",
    "conj",
    "conjunction",
    "det",
    "determiner",
    "particle",
    "prep",
    "preposition",
    "postp",
    "postposition",
}


def atomic_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
        os.replace(tmp_name, path)
    finally:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)


def atomic_jsonl(path: Path, rows: list[dict]) -> None:
    text = "".join(
        json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n"
        for row in rows
    )
    atomic_text(path, text)


def clean_id(value: str) -> str:
    # A trailing colon is part of several Kaikki opaque IDs; never normalize it.
    return value.rstrip(".,;`")


def card_blocks(text: str) -> list[dict]:
    starts = list(CARD_START.finditer(text))
    sections = list(SECTION_START.finditer(text))
    section_positions = [m.start() for m in sections]
    blocks: list[dict] = []
    for idx, match in enumerate(starts):
        candidates = [len(text)]
        if idx + 1 < len(starts):
            candidates.append(starts[idx + 1].start())
        candidates.extend(pos for pos in section_positions if pos > match.start())
        end = min(candidates)
        block = text[match.start() : end]
        verdict = VERDICT.search(block)
        state = STATE.search(block)
        outcome = verdict.group(1) if verdict else (state.group(1) if state else "")
        family = FAMILY_ID.search(match.group(0))
        blocks.append(
            {
                "start": match.start(),
                "end": end,
                "text": block,
                "outcome": outcome,
                "family_id": family.group(0) if family else "",
                "ids": {clean_id(x) for x in ENTRY_ID.findall(block)},
            }
        )
    return blocks


def remove_blocks(text: str, states: set[str]) -> tuple[str, list[dict]]:
    blocks = [b for b in card_blocks(text) if b["outcome"] in states]
    for block in reversed(blocks):
        text = text[: block["start"]] + text[block["end"] :]
    return text.rstrip() + "\n", blocks


def all_carded_members(texts: dict[str, str]) -> tuple[set[str], set[str]]:
    judged: set[str] = set()
    positive: set[str] = set()
    for text in texts.values():
        for block in card_blocks(text):
            if not block["outcome"]:
                continue
            judged.update(block["ids"])
            if block["outcome"] in POSITIVE:
                positive.update(block["ids"])
    return judged, positive


def direct_positive_members(texts: dict[str, str]) -> set[str]:
    """Members explicitly named by the decisive lines of a positive card."""
    result: set[str] = set()
    decisive = re.compile(
        r"(?m)^- (?:الحكم \(استكشاف\)|عائق|العضو):[^\n]*"
    )
    for text in texts.values():
        for block in card_blocks(text):
            if block["outcome"] not in POSITIVE:
                continue
            for line in decisive.findall(block["text"]):
                result.update(clean_id(x) for x in ENTRY_ID.findall(line))
    return result


def family_members(conn: sqlite3.Connection, family_id: str) -> list[str]:
    if not family_id:
        return []
    return [
        row[0]
        for row in conn.execute(
            "select entry_id from family_members where family_id=?", (family_id,)
        )
    ]


def get_entries(conn: sqlite3.Connection, ids: set[str] | list[str]) -> dict[str, dict]:
    columns = [
        "entry_id",
        "language",
        "headword",
        "romanization",
        "pos",
        "gloss",
        "etymology",
        "loan_hint",
        "form_of",
        "form_targets_json",
        "alternative_of",
        "alternative_targets_json",
        "original_skeleton",
    ]
    result: dict[str, dict] = {}
    values = list(ids)
    for offset in range(0, len(values), 700):
        part = values[offset : offset + 700]
        marks = ",".join("?" for _ in part)
        for row in conn.execute(
            f"select {','.join(columns)} from entries where entry_id in ({marks})", part
        ):
            result[row[0]] = dict(zip(columns, row))
    return result


def ids_for_blocks(
    conn: sqlite3.Connection, blocks: list[dict], kind: str
) -> set[str]:
    candidate_ids: set[str] = set()
    for block in blocks:
        candidate_ids.update(block["ids"])
        candidate_ids.update(family_members(conn, block["family_id"]))
    entries = get_entries(conn, candidate_ids)
    selected: set[str] = set()
    for entry_id, row in entries.items():
        pos = (row["pos"] or "").lower()
        role = conn.execute(
            "select role from family_members where entry_id=? limit 1", (entry_id,)
        ).fetchone()
        role = (role[0] or "").lower() if role else ""
        if kind == "forms":
            if (
                row["form_of"]
                or row["form_targets_json"]
                or row["alternative_of"]
                or row["alternative_targets_json"]
                or role in {"form", "alternative"}
            ):
                selected.add(entry_id)
        elif kind == "nonlexical":
            if pos in FUNCTION_POS or "nonlex" in role or "function" in role:
                selected.add(entry_id)
        elif kind == "names":
            if pos == "name":
                selected.add(entry_id)
        elif kind == "loans":
            # A LOANWORD card is a judgment over its named family members.
            if entry_id in block["ids"] or row["etymology"] or row["loan_hint"]:
                selected.add(entry_id)
    return selected


def load_coverage() -> dict[str, dict]:
    result: dict[str, dict] = {}
    if not COVERAGE.exists():
        return result
    with COVERAGE.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                row = json.loads(line)
                result[row["member_id"]] = row
    return result


def write_coverage(rows: dict[str, dict]) -> None:
    atomic_jsonl(COVERAGE, [rows[key] for key in sorted(rows)])


def coverage_row(entry: dict, reason: str, batch: str) -> dict:
    return {
        "member_id": entry["entry_id"],
        "language": entry["language"],
        "orthography": entry["headword"] or "",
        "branch_meaning": entry["gloss"] or "",
        "nonissuance_reason": reason,
        "batch_number": batch,
    }


def add_section(reading: str, title: str, cards: list[str]) -> str:
    if not cards:
        return reading
    body = "\n\n".join(card.strip() for card in cards)
    return (
        reading.rstrip()
        + f"\n\n## {title}\n\n"
        + body
        + "\n"
    )


def compact_positive_card(
    entry: dict,
    arabic: str,
    root: str,
    arabic_source: str,
    sound: str,
    note: str,
    batch: str,
) -> str:
    branch_source = (
        f"Kaikki {entry['language'].capitalize()}، العضو `{entry['entry_id']}`"
    )
    etym = (entry["etymology"] or "لا نص اشتقاقي زائد؛ المقابلة الموقعة هي سند الفحص").replace(
        "\n", " "
    )
    return f"""### مراجعة عضوية: `{entry['entry_id']}`، {entry['headword']} ↔ {arabic}
- إصدار البروتوكول: SECTION-26-RECOVERY (2026-07-30)
- العضو: `{entry['entry_id']}`؛ {entry['headword']}، {entry['pos']}، «{entry['gloss']}».
- المصدر الأول المسمى: {branch_source}؛ نص الأصل/المقارنة: {etym}
- المصدر الثاني المسمى: {arabic_source}؛ المدخل العربي `{root}`.
- مسار الصوت: {sound}.
- الفصل الدلالي: {note}
- حالة الإغلاق: READY.
- الحكم (استكشاف): ROOT-TRACE؛ {entry['headword']} ↔ {arabic}.
- البسط الإحصائي: داخل البسط؛ حكم موجب صادر مستقل.
- الدفعة: `{batch}`."""


def compact_form_card(entry: dict, base: dict, batch: str) -> str:
    targets = entry["form_targets_json"] or entry["alternative_targets_json"] or "[]"
    return f"""### مراجعة عضوية: `{entry['entry_id']}`، إحالة صرفية محكومة
- إصدار البروتوكول: SECTION-26-RECOVERY (2026-07-30)
- العضو: `{entry['entry_id']}`؛ {entry['headword']}، «{entry['gloss']}».
- الأصل المكتوب بطاقة والمحكوم فيه: `{base['entry_id']}`؛ {base['headword']}، «{base['gloss']}».
- سند الإحالة في المصدر: Kaikki {entry['language'].capitalize()}؛ form/alternative targets={targets}.
- حالة الإغلاق: FORM-OF-ISOLATED.
- الحكم (استكشاف): FORM-OF-ISOLATED؛ إحالة إلى أصل مسمى ذي حكم صادر، ولا توريث إلى أصل غائب.
- البسط الإحصائي: لا حكم موجب مستقل للصورة.
- الدفعة: `{batch}`."""


def explicit_specs() -> dict[str, list[dict]]:
    return {
        "hebrew": [
            dict(head="אח", pos="noun", ar="أخ", root="أخو", src="كتاب العين للخليل بن أحمد، مادة «أخو»", sound="GUT-05 الموقّع: خ العربية ↔ ח العبرية", note="الأخوّة وحدها؛ لا تُورث إلى «آه» أو «موقد»"),
            dict(head="אני", pos="pron", ar="أنا", root="أنن", src="لسان العرب لابن منظور، مادة «أنن» في ضمير المتكلم", sound="إسناد Kaikki المنشور إلى Proto-Semitic *ʔanāku؛ لا صف صوتي مستحدث", note="ضمير المتكلم وحده"),
            dict(head="אתה", pos="pron", ar="أنتَ", root="أنن", src="لسان العرب لابن منظور، مادة «أنن» في ضمير المخاطب", sound="إسناد Kaikki المنشور إلى Proto-Semitic *ʔanta؛ لا صف صوتي مستحدث", note="ضمير المخاطب المذكر المفرد وحده"),
            dict(head="הוא", pos="pron", ar="هو", root="هوو", src="المحكم والمحيط الأعظم لابن سيده، مادة «هوو»", sound="إسناد الأصل المنشور في Kaikki؛ لا صف صوتي مستحدث", note="ضمير الغائب المذكر وحده"),
            dict(head="היא", pos="pron", ar="هي", root="هيي", src="المحكم والمحيط الأعظم لابن سيده، باب الضمائر «هي»", sound="إسناد الأصل المنشور في Kaikki؛ لا صف صوتي مستحدث", note="ضمير الغائبة المؤنثة وحده"),
            dict(head="הן", pos="pron", ar="هنّ", root="هنن", src="لسان العرب لابن منظور، باب الضمائر «هنّ»", sound="نص Kaikki يسمّي العربية هنّ في سلسلة القرابة؛ لا صف صوتي مستحدث", note="ضمير جمع المؤنث وحده"),
            dict(head="מה", pos="pron", ar="ما", root="ما", src="لسان العرب لابن منظور، مادة «ما»", sound="نص Kaikki يسمّي العربية ما؛ لا صف صوتي مستحدث", note="أداة الاستفهام/الموصول وحدها"),
            dict(head="אחד", pos="num", ar="أحد", root="وحد", src="لسان العرب لابن منظور، مادة «وحد»", sound="إسناد Kaikki إلى Proto-Semitic *ʔaḥad مع تطابق حاء مباشر؛ لا صف جديد", note="العدد واحد وحده"),
        ],
        "aramaic": [
            dict(head="עסרין", pos="num", ar="عشرين", root="عشر", src="لسان العرب لابن منظور، مادة «عشر»", sound="جسر Kaikki المسمى إلى العبرية עשרים ثم SIB-07 الموقّع إلى عشر؛ لا صف جديد", note="العدد عشرون وحده"),
            dict(head="ארבעין", pos="num", ar="أربعين", root="ربع", src="لسان العرب لابن منظور، مادة «ربع»", sound="تطابق مهيكل مباشر، ولا صف إضافي", note="العدد أربعون وحده"),
            dict(head="שבעין", pos="num", ar="سبعين", root="سبع", src="لسان العرب لابن منظور، مادة «سبع»", sound="SIB-01 الموقّع: س العربية ↔ ש السامية الشمالية الغربية", note="العدد سبعون وحده"),
            dict(head="תמנאין", pos="num", ar="ثمانين", root="ثمن", src="لسان العرب لابن منظور، مادة «ثمن»", sound="DENT-01 الموقّع: ث العربية ↔ ת الآرامية", note="العدد ثمانون وحده"),
            dict(head="מאתן", pos="num", ar="مئتين", root="مءي", src="المفردات في غريب القرآن للراغب الأصفهاني، مادة «مائة»", sound="تطابق مهيكل مباشر، ولا صف إضافي", note="العدد مئتان وحده"),
            dict(head="חמשמאא", pos="num", ar="خمسمئة", root="خمس", src="لسان العرب لابن منظور، مادة «خمس»", sound="GUT-05 الموقّع: خ العربية ↔ ח الآرامية/العبرية، وبقية المركب مباشر", note="العدد خمسمئة وحده"),
        ],
    }


def pick_explicit_entries(
    conn: sqlite3.Connection, language: str, specs: list[dict]
) -> list[tuple[dict, dict]]:
    picked: list[tuple[dict, dict]] = []
    for spec in specs:
        rows = conn.execute(
            """select entry_id,language,headword,romanization,pos,gloss,etymology,
                      loan_hint,form_of,form_targets_json,alternative_of,
                      alternative_targets_json,original_skeleton
               from entries where language=? and headword=? and lower(pos)=?
               order by entry_id""",
            (language, spec["head"], spec["pos"]),
        ).fetchall()
        if not rows:
            raise RuntimeError(f"missing explicit Section 26 entry: {language} {spec}")
        columns = [
            "entry_id",
            "language",
            "headword",
            "romanization",
            "pos",
            "gloss",
            "etymology",
            "loan_hint",
            "form_of",
            "form_targets_json",
            "alternative_of",
            "alternative_targets_json",
            "original_skeleton",
        ]
        # Prefer the lexical sense, not a form/alternative accidentally sharing spelling.
        row = next(
            (
                row
                for row in rows
                if not row[8] and not row[10] and "alternative" not in (row[5] or "").lower()
            ),
            rows[0],
        )
        picked.append((dict(zip(columns, row)), spec))
    return picked


def form_targets(conn: sqlite3.Connection, entry: dict) -> list[str]:
    targets: list[str] = []
    for row in conn.execute(
        """select candidate_entry_ids_json,resolved_target_entry_id
           from form_links where form_entry_id=?""",
        (entry["entry_id"],),
    ):
        if row[1]:
            targets.append(row[1])
        if row[0]:
            try:
                targets.extend(json.loads(row[0]))
            except json.JSONDecodeError:
                pass
    for field in ("form_targets_json", "alternative_targets_json"):
        if entry[field]:
            try:
                values = json.loads(entry[field])
                if isinstance(values, list):
                    targets.extend(v for v in values if isinstance(v, str) and v.startswith("kaikki_"))
            except json.JSONDecodeError:
                pass
    return list(dict.fromkeys(targets))


def remaining_invalid(texts: dict[str, str]) -> Counter:
    result: Counter = Counter()
    affected = FORM_STATES | NONLEX_STATES | LOAN_STATES | NAME_STATES
    for text in texts.values():
        for block in card_blocks(text):
            # Reissued Section 26 cards are completed queue items, even when
            # their lawful outcome retains the same categorical label.
            if (
                block["outcome"] in affected
                and "SECTION-26-RECOVERY" not in block["text"]
            ):
                result[block["outcome"]] += 1
    return result


def write_audit(
    slug: str,
    title: str,
    start: int,
    end: int,
    remaining: int,
    positives: int,
    closures: int,
    details: list[str],
) -> Path:
    path = AUDIT_DIR / f"2026-07-30-lane-a-section26-{slug}.md"
    bullets = "\n".join(f"- {item}" for item in details)
    text = f"""# {title}

التاريخ: 2026-07-30  
النطاق: `aramaic.md` و`hebrew.md` فقط، مع دفتر التغطية الخاص بالمسار A.

## قيد الطابور

- بداية الدفعة: {start}
- نهاية الدفعة: {end}
- الباقي في طابور القواعد الأربع: {remaining}

## ما نُفّذ

{bullets}

## الرقمان المفصولان

**الروابط الموجبة الجديدة: {positives}**

**الإغلاقات الجديدة: {closures}**

الإغلاق هنا لا يُحسب إلا إذا صار بعد إعادة الفتح حكمًا صادرًا مستوفيًا للقسم 26. صفوف
`lane_a_coverage.jsonl` ليست إغلاقات، بل إبقاء صريح للعضو في الاكتشاف.
"""
    atomic_text(path, text)
    return path


def run_forms(conn: sqlite3.Connection, texts: dict[str, str]) -> dict:
    batch = "section26-forms"
    before = remaining_invalid(texts)
    coverage = load_coverage()
    removed_by_lang: dict[str, set[str]] = {}
    cards_by_lang: dict[str, list[str]] = defaultdict(list)

    # First issue the missing base אח itself.
    he_spec = explicit_specs()["hebrew"][0]
    base_entry, _ = pick_explicit_entries(conn, "hebrew", [he_spec])[0]
    cards_by_lang["hebrew"].append(
        compact_positive_card(
            base_entry,
            he_spec["ar"],
            he_spec["root"],
            he_spec["src"],
            he_spec["sound"],
            he_spec["note"],
            batch,
        )
    )
    coverage.pop(base_entry["entry_id"], None)

    for language in ("aramaic", "hebrew"):
        texts[language], blocks = remove_blocks(texts[language], FORM_STATES)
        removed_by_lang[language] = ids_for_blocks(conn, blocks, "forms")

    _, previous_positive = all_carded_members(texts)
    direct_positive = direct_positive_members(texts)
    direct_positive.add(base_entry["entry_id"])
    entry_cache = get_entries(
        conn, set().union(*removed_by_lang.values()) | direct_positive
    )
    reclosed = 0
    pending = 0
    for language, ids in removed_by_lang.items():
        for entry_id in sorted(ids):
            entry = entry_cache.get(entry_id)
            if not entry:
                continue
            targets = form_targets(conn, entry)
            # אחי is explicitly resolved to the brother entry; do not let the
            # unrelated homographs "alas"/"hearth" keep the void referral alive.
            if language == "hebrew" and entry["headword"] == "אחי":
                targets = [base_entry["entry_id"]]
            valid = [t for t in targets if t in direct_positive]
            if len(valid) == 1 and valid[0] in entry_cache:
                cards_by_lang[language].append(
                    compact_form_card(entry, entry_cache[valid[0]], batch)
                )
                coverage.pop(entry_id, None)
                reclosed += 1
            else:
                coverage[entry_id] = coverage_row(
                    entry,
                    "OPEN-CANDIDATE: نقض إحالة صورة صرفية إلى أصل غير مكتوب بطاقة ومحكوم فيه؛ يجب قراءة الأصل أولًا أو حكم الصورة نفسها",
                    batch,
                )
                pending += 1

    for language in ("aramaic", "hebrew"):
        texts[language] = add_section(
            texts[language],
            "استرداد القسم 26: الصور الصرفية",
            cards_by_lang[language],
        )
        atomic_text(READINGS[language], texts[language])
    write_coverage(coverage)
    after = remaining_invalid(texts)
    start = sum(before.values())
    end = sum(after.values())
    audit = write_audit(
        "forms",
        "محضر استرداد القسم 26: الصور الصرفية",
        start,
        end,
        end,
        1,
        reclosed,
        [
            f"أعيد فتح {sum(len(v) for v in removed_by_lang.values())} عضوًا كان تحت FORM-OF-ISOLATED.",
            f"ثبت أصل אח نفسه في بطاقة موجبة مستقلة قبل إحالة صوره إليه.",
            f"أعيد إغلاق {reclosed} صورة فقط لأن أصلها المسمى يحمل حكمًا صادرًا.",
            f"بقي {pending} عضوًا مفتوحًا في دفتر التغطية؛ لا إغلاق في الفراغ.",
        ],
    )
    return dict(positives=1, closures=reclosed, audit=audit, remaining=end)


def run_nonlexical(conn: sqlite3.Connection, texts: dict[str, str]) -> dict:
    batch = "section26-nonlexical"
    before = remaining_invalid(texts)
    coverage = load_coverage()
    reopened: set[str] = set()
    for language in ("aramaic", "hebrew"):
        texts[language], blocks = remove_blocks(texts[language], NONLEX_STATES)
        reopened.update(ids_for_blocks(conn, blocks, "nonlexical"))

    pairs: list[tuple[dict, dict]] = []
    for language, specs in explicit_specs().items():
        # אח belongs to the preceding batch.
        if language == "hebrew":
            specs = specs[1:]
        pairs.extend(pick_explicit_entries(conn, language, specs))
    issued_ids = {entry["entry_id"] for entry, _ in pairs}

    cards_by_lang: dict[str, list[str]] = defaultdict(list)
    for entry, spec in pairs:
        cards_by_lang[entry["language"]].append(
            compact_positive_card(
                entry,
                spec["ar"],
                spec["root"],
                spec["src"],
                spec["sound"],
                spec["note"],
                batch,
            )
        )
        coverage.pop(entry["entry_id"], None)

    # The lifted exclusion applies to the complete functional inventory, not
    # merely to members that happened to receive an old isolation card.
    rows = conn.execute(
        """select entry_id,language,headword,romanization,pos,gloss,etymology,
                  loan_hint,form_of,form_targets_json,alternative_of,
                  alternative_targets_json,original_skeleton
           from entries where language in ('hebrew','aramaic')"""
    )
    columns = [
        "entry_id",
        "language",
        "headword",
        "romanization",
        "pos",
        "gloss",
        "etymology",
        "loan_hint",
        "form_of",
        "form_targets_json",
        "alternative_of",
        "alternative_targets_json",
        "original_skeleton",
    ]
    _, positive_now = all_carded_members(texts)
    judged_now, _ = all_carded_members(texts)
    considered = 0
    open_count = 0
    for raw in rows:
        entry = dict(zip(columns, raw))
        if (entry["pos"] or "").lower() not in FUNCTION_POS:
            continue
        considered += 1
        entry_id = entry["entry_id"]
        if entry_id in issued_ids or entry_id in judged_now:
            continue
        coverage[entry_id] = coverage_row(
            entry,
            "OPEN-CANDIDATE: رفع القسم 26 الاستبعاد غير المعجمي؛ العدد/الضمير/الأداة يدخل الاكتشاف كسائر الكلمات ولم يصدر له حكم بعد",
            batch,
        )
        open_count += 1

    for language in ("aramaic", "hebrew"):
        texts[language] = add_section(
            texts[language],
            "استرداد القسم 26: الأعداد والضمائر والأدوات",
            cards_by_lang[language],
        )
        atomic_text(READINGS[language], texts[language])
    write_coverage(coverage)
    after = remaining_invalid(texts)
    start = sum(before.values())
    end = sum(after.values())
    audit = write_audit(
        "nonlexical",
        "محضر استرداد القسم 26: رفع الاستبعاد غير المعجمي",
        start,
        end,
        end,
        len(pairs),
        0,
        [
            f"أعيد فتح {len(reopened)} عضوًا كان معزولًا بكونه عددًا أو ضميرًا أو أداة.",
            f"فُحص المخزون الوظيفي الكامل: {considered} عضوًا في اللغتين.",
            f"صدرت {len(pairs)} صلة مستقلة من أمثلة القسم 26 ذات المصدرين والمسار الموقّع أو الجسر المنشور.",
            f"بقي {open_count} عضوًا بلا حكم في دفتر التغطية، لا بوصفه مستبعدًا بل مرشحًا مفتوحًا.",
        ],
    )
    return dict(positives=len(pairs), closures=0, audit=audit, remaining=end)


DONOR_PATTERNS = [
    "Ancient Greek",
    "Greek",
    "Latin",
    "Egyptian",
    "Sumerian",
    "Akkadian",
    "Syriac",
    "Aramaic",
    "Arabic",
    "Persian",
    "Iranian",
    "Sanskrit",
    "Tamil",
    "English",
    "French",
    "German",
    "Yiddish",
    "Russian",
    "Turkish",
    "Coptic",
    "Phoenician",
]


def named_donor(etymology: str | None, loan_hint: str | None) -> tuple[str, str] | None:
    text = " ".join(str(x) for x in (etymology, loan_hint) if x).strip()
    if not text:
        return None
    low = text.lower()
    if any(
        phrase in low
        for phrase in (
            "either native or borrowed",
            "native or borrowed",
            "direction uncertain",
            "unknown origin",
        )
    ):
        return None
    first = re.split(r"(?<=[.;])\s+", text, maxsplit=1)[0]
    transfer = re.search(
        r"\b(?:borrowed|borrowing|loan(?:word)?|from|ultimately from|derived from)\b",
        first,
        re.I,
    )
    if not transfer:
        return None
    # Proto-Semitic ancestry is inheritance, not a donor loan.
    if re.search(r"Proto-(?:Semitic|Afro-Asiatic|Northwest Semitic)", first, re.I):
        return None
    donor = next((name for name in DONOR_PATTERNS if name.lower() in first.lower()), None)
    if not donor:
        return None
    return donor, first


def compact_loan_card(entry: dict, donor: str, path: str, batch: str) -> str:
    return f"""### مراجعة عضوية: `{entry['entry_id']}`، قرض ذو مانح مسمى
- إصدار البروتوكول: SECTION-26-RECOVERY (2026-07-30)
- العضو: `{entry['entry_id']}`؛ {entry['headword']}، {entry['pos']}، «{entry['gloss']}».
- مصدر المسار المنشور: Kaikki {entry['language'].capitalize()}، العضو نفسه.
- المانح المسمى: {donor}.
- مسار النقل المنشور: {path}
- حالة الإغلاق: LOANWORD.
- الحكم (استكشاف): LOANWORD؛ عزل من بسط النسب لهذا المعنى بسبب مانح مسمى ومسار منشور، لا بسبب وسم آلي مجهول الاتجاه.
- الدفعة: `{batch}`."""


def run_loans(conn: sqlite3.Connection, texts: dict[str, str]) -> dict:
    batch = "section26-loans"
    before = remaining_invalid(texts)
    coverage = load_coverage()
    reopened_by_lang: dict[str, set[str]] = {}
    cards_by_lang: dict[str, list[str]] = defaultdict(list)
    for language in ("aramaic", "hebrew"):
        texts[language], blocks = remove_blocks(texts[language], LOAN_STATES)
        reopened_by_lang[language] = ids_for_blocks(conn, blocks, "loans")
    all_ids = set().union(*reopened_by_lang.values())
    entries = get_entries(conn, all_ids)
    valid = 0
    open_count = 0
    donor_counts: Counter = Counter()
    for language, ids in reopened_by_lang.items():
        for entry_id in sorted(ids):
            entry = entries.get(entry_id)
            if not entry:
                continue
            route = named_donor(entry["etymology"], entry["loan_hint"])
            if route:
                donor, path = route
                cards_by_lang[language].append(
                    compact_loan_card(entry, donor, path, batch)
                )
                coverage.pop(entry_id, None)
                donor_counts[donor] += 1
                valid += 1
            else:
                evidence = (entry["etymology"] or entry["loan_hint"] or "لا نص مانح").replace(
                    "\n", " "
                )
                coverage[entry_id] = coverage_row(
                    entry,
                    f"OPEN-CANDIDATE: نقض LOANWORD؛ لا مانح مسمى مع اتجاه ومسار منشور. النص المحفوظ: {evidence}",
                    batch,
                )
                open_count += 1
    for language in ("aramaic", "hebrew"):
        texts[language] = add_section(
            texts[language],
            "استرداد القسم 26: القروض ذات المانح المسمى",
            cards_by_lang[language],
        )
        atomic_text(READINGS[language], texts[language])
    write_coverage(coverage)
    after = remaining_invalid(texts)
    start = sum(before.values())
    end = sum(after.values())
    donors = "، ".join(f"{k}={v}" for k, v in donor_counts.most_common()) or "لا شيء"
    audit = write_audit(
        "loans",
        "محضر استرداد القسم 26: لا قرض بلا مانح مسمى",
        start,
        end,
        end,
        0,
        valid,
        [
            f"أعيد فتح {len(all_ids)} عضوًا كان يحمل LOANWORD.",
            f"أعيد إغلاق {valid} عضوًا فقط بعد تسمية المانح وحفظ مسار النقل المنشور.",
            f"عاد {open_count} عضوًا إلى الحكم لأن النص لا يثبت مانحًا واتجاهًا معًا.",
            f"توزيع المانحين في الإغلاقات المجددة: {donors}.",
        ],
    )
    return dict(positives=0, closures=valid, audit=audit, remaining=end)


def strip_marks(value: str) -> str:
    return "".join(
        ch for ch in unicodedata.normalize("NFD", value)
        if unicodedata.category(ch) != "Mn" and ch not in "־· -'\"״׳"
    )


def name_root_record(entry: dict) -> dict:
    etym = entry["etymology"] or ""
    head = strip_marks(entry["headword"] or "")
    explicit = {
        ("hebrew", "ביתלחם"): ("בית+לחם", "author-signed-section26", "القسم 26: بيت لحم حرفًا بحرف"),
        ("hebrew", "אדרמלך"): ("מלך", "author-signed-section26", "القسم 26: حفظ عنصر מלך شاهدًا للجذر"),
        ("hebrew", "שאול"): ("שאל", "author-signed-section26", "القسم 26: שאול من שאל ↔ سأل"),
    }
    key = (entry["language"], head)
    if key in explicit:
        root, status, evidence = explicit[key]
    else:
        matcher = HEBREW_CHARS if entry["language"] in {"hebrew", "aramaic"} else ARAMAIC_CHARS
        tokens = [strip_marks(t) for t in matcher.findall(etym)]
        tokens = [t for t in tokens if t and t != head]
        proto = re.search(r"\*([A-Za-zʾʿḥḫšśṣṭḍṯḏġḳ]+)", etym)
        if tokens:
            root = "+".join(dict.fromkeys(tokens[:3]))
            status = "source-text"
            evidence = etym.replace("\n", " ")
        elif proto:
            root = proto.group(1)
            status = "proto-source"
            evidence = etym.replace("\n", " ")
        else:
            root = entry["original_skeleton"] or head
            status = "surface-only-root-open"
            evidence = "لم يسم المصدر جذرًا؛ حُفظ الهيكل السطحي ولم يُخترع تحليل جذري"
    return {
        "member_id": entry["entry_id"],
        "language": entry["language"],
        "orthography": entry["headword"] or "",
        "gloss": entry["gloss"] or "",
        "extracted_root_or_segments": root,
        "extraction_status": status,
        "source_evidence": evidence,
        "in_statistical_numerator": False,
        "discovery_role": "root-witness",
    }


def run_names(conn: sqlite3.Connection, texts: dict[str, str]) -> dict:
    batch = "section26-names"
    before = remaining_invalid(texts)
    coverage = load_coverage()
    reopened: set[str] = set()
    for language in ("aramaic", "hebrew"):
        texts[language], blocks = remove_blocks(texts[language], NAME_STATES)
        reopened.update(ids_for_blocks(conn, blocks, "names"))

    columns = [
        "entry_id",
        "language",
        "headword",
        "romanization",
        "pos",
        "gloss",
        "etymology",
        "loan_hint",
        "form_of",
        "form_targets_json",
        "alternative_of",
        "alternative_targets_json",
        "original_skeleton",
    ]
    rows = [
        dict(zip(columns, raw))
        for raw in conn.execute(
            f"""select {','.join(columns)} from entries
                where language in ('hebrew','aramaic') and lower(pos)='name'
                order by language,entry_id"""
        )
    ]
    records = [name_root_record(entry) for entry in rows]
    atomic_jsonl(NAME_ROOTS, records)
    record_by_id = {r["member_id"]: r for r in records}
    entries = {entry["entry_id"]: entry for entry in rows}
    for entry_id in reopened:
        entry = entries.get(entry_id)
        record = record_by_id.get(entry_id)
        if not entry or not record:
            continue
        coverage[entry_id] = coverage_row(
            entry,
            "NAME-ROOT-INVENTORY: "
            + record["extracted_root_or_segments"]
            + f"؛ status={record['extraction_status']}؛ العلم خارج البسط، والجذر شاهد داخل الاكتشاف، ولا إغلاق للاسم",
            batch,
        )
    write_coverage(coverage)

    counts = Counter(r["extraction_status"] for r in records)
    summaries = {
        "hebrew": [
            """### بيان جرد الأعلام
- الجرد الكامل: `04-cross-linguistic/data/lane_a_name_roots.jsonl`.
- القاعدة: كل علم خارج البسط الإحصائي، لكن جذره أو هيكله المسند شاهد داخل الاكتشاف.
- أمثلة القسم 26: ביתלחם → בית+לחם؛ אדרמלך → מלך؛ שאול → שאל ↔ سأل.
- الحكم (استكشاف): لا إغلاق اسمي؛ الجذر يدخل طابور المقارنة، والسطح غير المحلول يبقى ROOT-OPEN."""
        ],
        "aramaic": [
            """### بيان جرد الأعلام
- الجرد الكامل: `04-cross-linguistic/data/lane_a_name_roots.jsonl`.
- القاعدة: كل علم خارج البسط الإحصائي، لكن جذره أو هيكله المسند شاهد داخل الاكتشاف.
- בית לחם محفوظ بعنصريه وبمساره المنشور من العبرية «house of bread».
- الحكم (استكشاف): لا إغلاق اسمي؛ الجذر يدخل طابور المقارنة، والسطح غير المحلول يبقى ROOT-OPEN."""
        ],
    }
    for language in ("aramaic", "hebrew"):
        texts[language] = add_section(
            texts[language],
            "استرداد القسم 26: جرد جذور الأعلام",
            summaries[language],
        )
        atomic_text(READINGS[language], texts[language])
    after = remaining_invalid(texts)
    start = sum(before.values())
    end = sum(after.values())
    audit = write_audit(
        "names",
        "محضر استرداد القسم 26: الأعلام وجذورها",
        start,
        end,
        end,
        0,
        0,
        [
            f"أعيد فتح {len(reopened)} عضوًا كان معزولًا لمجرد كونه علمًا.",
            f"سُجل {len(records)} علمًا في الجرد المستقل، وكلها موسومة خارج البسط.",
            "حالات الاستخراج: " + "، ".join(f"{k}={v}" for k, v in sorted(counts.items())) + ".",
            "لم يُختلق جذر: حيث لم يسم المصدر أصلًا حُفظ الهيكل السطحي ووسم ROOT-OPEN.",
        ],
    )
    return dict(positives=0, closures=0, audit=audit, remaining=end)


def run_verify(conn: sqlite3.Connection, texts: dict[str, str]) -> dict:
    """Normalize the no-judgment ledger and prove the Section 26 invariants."""
    judged, _ = all_carded_members(texts)
    # Use the entry-specific lines/headings, not incidental family citations.
    direct_judged: set[str] = set()
    legacy_affected: list[tuple[str, str]] = []
    section26_positive = 0
    section26_forms = 0
    section26_loans = 0
    named_source_failures: list[str] = []
    form_base_ids: list[str] = []
    loan_field_failures: list[str] = []
    used_rows: set[str] = set()
    for language, text in texts.items():
        for block in card_blocks(text):
            outcome = block["outcome"]
            if outcome and outcome in (FORM_STATES | NONLEX_STATES | LOAN_STATES | NAME_STATES):
                if "SECTION-26-RECOVERY" not in block["text"]:
                    legacy_affected.append((language, outcome))
            if outcome:
                heading = block["text"].splitlines()[0] if block["text"] else ""
                decisive = [heading] + re.findall(
                    r"(?m)^- (?:العضو|عائق|الحكم \(استكشاف\)):[^\n]*",
                    block["text"],
                )
                for line in decisive:
                    direct_judged.update(clean_id(x) for x in ENTRY_ID.findall(line))
            if "SECTION-26-RECOVERY" not in block["text"]:
                continue
            if outcome in POSITIVE:
                section26_positive += 1
                if (
                    "المصدر الأول المسمى:" not in block["text"]
                    or "المصدر الثاني المسمى:" not in block["text"]
                ):
                    named_source_failures.append(heading)
                used_rows.update(
                    re.findall(r"\b(?:GUT|SIB|DENT|LAB|LIQ)-\d\d\b", block["text"])
                )
            elif outcome in FORM_STATES:
                section26_forms += 1
                match = re.search(
                    r"الأصل المكتوب بطاقة والمحكوم فيه: `([^`]+)`",
                    block["text"],
                )
                if match:
                    form_base_ids.append(match.group(1))
                else:
                    named_source_failures.append(heading)
            elif outcome in LOAN_STATES:
                section26_loans += 1
                if (
                    "المانح المسمى:" not in block["text"]
                    or "مسار النقل المنشور:" not in block["text"]
                ):
                    loan_field_failures.append(heading)

    columns = ["entry_id", "language", "headword", "gloss", "pos"]
    inventory = {
        row[0]: dict(zip(columns, row))
        for row in conn.execute(
            """select entry_id,language,headword,gloss,pos from entries
               where language in ('hebrew','aramaic')"""
        )
    }
    direct_judged &= set(inventory)
    coverage = load_coverage()
    removed_overlap = len(set(coverage) & direct_judged)
    for entry_id in direct_judged:
        coverage.pop(entry_id, None)

    name_records: dict[str, dict] = {}
    with NAME_ROOTS.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                row = json.loads(line)
                name_records[row["member_id"]] = row
    added_missing = 0
    for entry_id, entry in inventory.items():
        if entry_id in direct_judged or entry_id in coverage:
            continue
        name_record = name_records.get(entry_id)
        if name_record:
            reason = (
                "NAME-ROOT-INVENTORY: "
                + name_record["extracted_root_or_segments"]
                + f"؛ status={name_record['extraction_status']}؛ العلم خارج البسط، "
                  "والجذر شاهد داخل الاكتشاف، ولا حكم عضوي صادر"
            )
        else:
            reason = (
                "OPEN-CANDIDATE: العضو حاضر في المخزون ولا يحمل حكمًا عضويًا صادرًا؛ "
                "يبقى في التغطية للاكتشاف ولا يغلق بغياب البطاقة"
            )
        coverage[entry_id] = {
            "member_id": entry_id,
            "language": entry["language"],
            "orthography": entry["headword"] or "",
            "branch_meaning": entry["gloss"] or "",
            "nonissuance_reason": reason,
            "batch_number": "section26-final-coverage",
        }
        added_missing += 1
    write_coverage(coverage)

    shift_text = (ROOT / "04-cross-linguistic/shift-network-draft.md").read_text(
        encoding="utf-8"
    )
    unsigned_rows = sorted(row for row in used_rows if row not in shift_text)
    missing_bases = sorted(set(form_base_ids) - direct_judged)
    coverage_overlap = set(coverage) & direct_judged
    uncovered = set(inventory) - (set(coverage) | direct_judged)
    name_count_db = sum(
        1
        for entry in inventory.values()
        if (entry["pos"] or "").lower() == "name"
    )
    name_numerator = sum(
        bool(row.get("in_statistical_numerator")) for row in name_records.values()
    )
    failures = {
        "legacy_affected": legacy_affected,
        "named_source_failures": named_source_failures,
        "loan_field_failures": loan_field_failures,
        "unsigned_rows": unsigned_rows,
        "missing_form_bases": missing_bases,
        "coverage_overlap": sorted(coverage_overlap),
        "uncovered": sorted(uncovered),
        "name_inventory_mismatch": len(name_records) != name_count_db,
        "names_in_numerator": name_numerator,
    }
    bad = {key: value for key, value in failures.items() if value}
    if bad:
        raise RuntimeError("Section 26 verification failed: " + json.dumps(bad, ensure_ascii=False))

    path = AUDIT_DIR / "2026-07-30-lane-a-section26-final-verification.md"
    text = f"""# التحقق النهائي لتنفيذ القسم 26 في المسار A

التاريخ: 2026-07-30  
النطاق: الآرامية والعبرية وحدهما.

## النتيجة

- بطاقات القواعد الأربع القديمة الباقية: 0.
- الروابط الموجبة الجديدة في القسم 26: {section26_positive}.
- إحالات الصور المجددة بعد أصل محكوم: {section26_forms}.
- إغلاقات القرض المجددة بعد مانح ومسار منشورين: {section26_loans}.
- صفوف التغطية لغير المحكوم فيهم: {len(coverage)}، بلا تكرار وبلا تقاطع مع حكم عضوي صادر.
- تغطية المخزون: {len(inventory)} من {len(inventory)}.
- جرد الأعلام: {len(name_records)} من {name_count_db}، وكلها خارج البسط الإحصائي.

## البوابات

- كل صلة موجبة جديدة تحمل مصدرين مسميين.
- كل صف صوتي مستعمل في البطاقات الجديدة موجود في `shift-network-draft.md`: {"، ".join(sorted(used_rows)) or "لا صف لازم"}.
- كل إحالة صرفية مجددة تسمي بطاقة أصل ذات حكم صادر.
- كل LOANWORD مجدد يسمي المانح ويحفظ مسار النقل المنشور.
- أزيل {removed_overlap} سطر تغطية كان يتقاطع مع حكم عضوي، وأضيف {added_missing} سطرًا لأعضاء بلا حكم، فصار دفتر التغطية مطابقًا لقاعدته.
- لا git، ولا باني مشترك، ولا تعديل لأداة مشتركة.
"""
    atomic_text(path, text)
    return dict(
        positives=section26_positive,
        closures=section26_forms + section26_loans,
        audit=path,
        remaining=0,
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--batch",
        required=True,
        choices=("forms", "nonlexical", "loans", "names", "verify"),
    )
    args = parser.parse_args()
    texts = {language: path.read_text(encoding="utf-8") for language, path in READINGS.items()}
    conn = sqlite3.connect(f"file:{DB.as_posix()}?mode=ro", uri=True)
    try:
        result = globals()[f"run_{args.batch}"](conn, texts)
    finally:
        conn.close()
    print(
        json.dumps(
            {
                "batch": args.batch,
                "positives": result["positives"],
                "closures": result["closures"],
                "remaining": result["remaining"],
                "audit": str(result["audit"].relative_to(ROOT)),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
