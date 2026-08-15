# -*- coding: utf-8 -*-
"""ابن جرد الصور اليونانية المحالة من القبطية واللاتينية."""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import unicodedata
from collections import Counter, defaultdict
from typing import Any, Iterable


ROOT = pathlib.Path(__file__).resolve().parent.parent
COPTIC = ROOT / "data" / "non-coptic-borrowings-in-coptic.json"
LATIN = ROOT / "data" / "greek-borrowings-in-latin.json"
LATIN_RAW = ROOT / "Resources" / "latin" / "kaikki.org-dictionary-Latin.jsonl"
GREEK_RAW = (
    ROOT / "Resources" / "ancient_greek"
    / "kaikki.org-dictionary-AncientGreek.jsonl"
)
OUT = ROOT / "data" / "greek-origin-inventory.json"

LATIN_GREEK_PATTERN = re.compile(
    r"(?i)\b(?:(Ancient|Byzantine|Koine|Medieval|Modern|Doric|Attic|scholarly)\s+)?Greek\b"
)


def clean_space(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def nfc(value: Any) -> str:
    return unicodedata.normalize("NFC", str(value or "")).strip()


def fold_greek(value: Any) -> str:
    """مفتاح رسم فقط: يطرح النبر والكم ولا يبدل حرفًا يونانيًا بحرف آخر."""
    return "".join(
        char for char in unicodedata.normalize("NFD", str(value or "")).casefold()
        if not unicodedata.combining(char)
    )


def dedup_greek_key(value: Any) -> str:
    """وحّد حالة الحرف وعلامتي الكم، وأبق النبر والتنفس الفارقين بين المداخل."""
    return unicodedata.normalize(
        "NFC",
        "".join(
            char
            for char in unicodedata.normalize("NFD", str(value or "")).casefold()
            if char not in {"\u0304", "\u0306"}  # macron, breve
        ),
    )


def preferred_published_form(forms: Iterable[str]) -> str:
    """اختر الصورة الأغنى بكمها، ثم الصغيرة، مع حفظ كل البدائل في الجرد."""
    def score(form: str) -> tuple[int, int, str]:
        decomposed = unicodedata.normalize("NFD", form)
        quantity = sum(char in {"\u0304", "\u0306"} for char in decomposed)
        has_upper = int(any(char.isupper() for char in form))
        return (-quantity, has_upper, form)

    return min(forms, key=score)


def is_greek_letter(char: str) -> bool:
    code = ord(char)
    return (
        0x0370 <= code <= 0x03FF
        or 0x1F00 <= code <= 0x1FFF
    ) and unicodedata.category(char).startswith("L")


MIXED_COPTIC_TO_GREEK = str.maketrans({
    "ⲓ": "ι",
    "ⲉ": "ε",
    "ⲟ": "ο",
    "ⲁ": "α",
    "ⲏ": "η",
    "ⲩ": "υ",
    "ⲱ": "ω",
})


def repair_mixed_coptic(source: str) -> tuple[str, list[dict[str, str]]]:
    """أصلح حرف صائت قبطيًا محصورًا داخل رسم يوناني، مع إبقاء سجل التصحيح."""
    chars = list(source)
    repairs: list[dict[str, str]] = []
    for index, char in enumerate(chars):
        mapped = char.translate(MIXED_COPTIC_TO_GREEK)
        if mapped == char:
            continue
        left = chars[index - 1] if index else ""
        right = chars[index + 1] if index + 1 < len(chars) else ""
        if is_greek_letter(left) and is_greek_letter(right):
            chars[index] = mapped
            repairs.append({"published": char, "lookup": mapped})
    return "".join(chars), repairs


def expand_optional_parentheses(token: str) -> list[str]:
    match = re.fullmatch(r"([^()]*)\(([^()]*)\)([^()]*)", token)
    if not match:
        return [token]
    left, optional, right = match.groups()
    return [left + right, left + optional + right]


def greek_tokens(source: str) -> tuple[list[str], list[dict[str, str]]]:
    """استخرج الرسوم اليونانية المنشورة من النص بلا رومنة وسيطة."""
    repaired, repairs = repair_mixed_coptic(source)
    tokens: list[str] = []
    index = 0
    while index < len(repaired):
        if not is_greek_letter(repaired[index]):
            index += 1
            continue
        start = index
        index += 1
        while index < len(repaired):
            char = repaired[index]
            if is_greek_letter(char) or unicodedata.combining(char):
                index += 1
                continue
            if char == "(" and ")" in repaired[index + 1:]:
                end = repaired.index(")", index + 1)
                middle = repaired[index + 1:end]
                if middle and all(
                    is_greek_letter(item) or unicodedata.combining(item)
                    for item in middle
                ):
                    index = end + 1
                    continue
            break
        published = nfc(repaired[start:index])
        for expanded in expand_optional_parentheses(published):
            expanded = nfc(expanded)
            if expanded and expanded not in tokens:
                tokens.append(expanded)
    return tokens, repairs


def coptic_published_forms(source: str) -> tuple[list[str], list[dict[str, str]]]:
    """خذ رأس كل مدخلة يونانية في حقل القبطية، لا حروف صفحات LSJ."""
    repaired, repairs = repair_mixed_coptic(source)
    forms: list[str] = []
    # يجمع الحقل أحيانا مداخل متجانسة، ولكل واحدة رقم بعد فاصلة عربية.
    for segment in re.split(r"؛\s*(?=\d+\s)", repaired):
        segment = re.sub(r"^\s*\d+\s+", "", segment)
        ascii_word = re.search(r"[A-Za-z]", segment)
        head = segment[:ascii_word.start()] if ascii_word else segment
        tokens, _ = greek_tokens(head)
        for token in tokens:
            if token not in forms:
                forms.append(token)
    # مدخلة ألمانية واحدة تكتب «über gr. ἀμμά» بلا رقم ولا رأس Crum المعتاد.
    # إذا لم يخرج الرأس شيئا نأخذ الرسم اليوناني الصريح من العبارة كلها.
    if not forms:
        tokens, _ = greek_tokens(repaired)
        for token in tokens:
            if token not in forms:
                forms.append(token)
    return forms, repairs


def latin_direct_greek_forms(etymology: str) -> list[str]:
    """خذ الأصل المباشر بعد Greek وطبقاته، واترك تحليل from/+ لقاموس اليونانية."""
    forms: list[str] = []
    matches = list(LATIN_GREEK_PATTERN.finditer(etymology))
    if not matches:
        return forms
    selected_matches = [matches[0]]
    # في الصياغة الكلاسيكية المركبة لا توجد كلمة يونانية كلية، بل عنصران
    # منسوبان كلاهما إلى Greek؛ أما بعد أصل يوناني كلي فالتكرار شرح للمركب.
    if "compound" in etymology[:matches[0].start()].casefold():
        selected_matches = matches
    for match in selected_matches:
        tail = etymology[match.end():].lstrip()
        stop_positions = [
            position for position in (
                tail.find("("), tail.find(". "), tail.find("; ")
            ) if position >= 0
        ]
        head = tail[:min(stop_positions)] if stop_positions else tail
        tokens, _ = greek_tokens(head)
        for token in tokens:
            if token not in forms:
                forms.append(token)
    return forms


def greek_strata(etymology: str) -> list[str]:
    labels: list[str] = []
    for match in LATIN_GREEK_PATTERN.finditer(etymology):
        label = (match.group(1) or "unspecified").casefold()
        if label not in labels:
            labels.append(label)
    return labels


def romanization(row: dict[str, Any]) -> str:
    for form in row.get("forms") or []:
        if "romanization" in (form.get("tags") or []):
            return clean_space(form.get("form"))
    return ""


SKIP_GLOSS = re.compile(
    r"^(inflection of|plural of|genitive of|alternative (form|spelling) of|"
    r"obsolete (form|spelling) of|misspelling of|romanization of)\b",
    re.I,
)


def glosses_of(row: dict[str, Any], limit: int | None = 3) -> list[str]:
    out: list[str] = []
    for sense in row.get("senses") or []:
        if "form-of" in (sense.get("tags") or []):
            continue
        for gloss in sense.get("glosses") or []:
            gloss = clean_space(gloss)
            if gloss and not SKIP_GLOSS.match(gloss) and gloss not in out:
                out.append(gloss)
        if limit is not None and len(out) >= limit:
            break
    return out if limit is None else out[:limit]


def latin_ancient_greek_spans(etymology: str) -> list[str]:
    """خذ العبارة التي تنسب الأصل إلى اليونانية القديمة، لا إحالة Greek الحديثة."""
    spans: list[str] = []
    pattern = re.compile(r"(?i)\bAncient Greek\b")
    for match in pattern.finditer(etymology):
        tail = etymology[match.end():]
        stops = [
            position for position in (
                tail.find(". Compare "),
                tail.find(". Cognate "),
                tail.find(". See "),
            ) if position >= 0
        ]
        if stops:
            tail = tail[:min(stops)]
        spans.append(tail)
    return spans


def latin_raw_entries(rows: list[dict[str, Any]]) -> tuple[dict[str, list[dict]], list[str]]:
    """استعد النص الاشتقاقي الكامل بدل حقل الفهرس المقتطع عند 180 محرفًا."""
    targets: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        targets[str(row["latin_form"]).casefold()].append(row)
    found: dict[str, list[dict]] = defaultdict(list)
    with LATIN_RAW.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            raw = json.loads(line)
            key = str(raw.get("word") or "").casefold()
            if key not in targets:
                continue
            full = clean_space(raw.get("etymology_text"))
            if not full or not re.search(r"(?i)\bAncient Greek\b", full):
                continue
            indexed = clean_space(full)[:180]
            meanings = "؛ ".join(glosses_of(raw))
            for source_row in targets[key]:
                prefix = clean_space(source_row["greek_origin_published"])
                if not (
                    indexed == prefix
                    or full.startswith(prefix)
                    or prefix.startswith(indexed)
                ):
                    continue
                if meanings and source_row.get("meaning") and (
                    clean_space(source_row["meaning"]) != meanings
                ):
                    # يبقى التطابق الاشتقاقي حاكمًا؛ المعنى عون في كشف المتجانس فقط.
                    pass
                entry = {
                    "card_id": source_row["card_id"],
                    "latin_form": source_row["latin_form"],
                    "meaning": source_row["meaning"],
                    "pos": clean_space(raw.get("pos")),
                    "raw_id": clean_space(raw.get("id")),
                    "full_etymology": full,
                    "raw_meanings": glosses_of(raw, None),
                }
                if entry not in found[source_row["card_id"]]:
                    found[source_row["card_id"]].append(entry)
    missing = [row["card_id"] for row in rows if row["card_id"] not in found]
    return dict(found), missing


def source_occurrences() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    coptic = json.loads(COPTIC.read_text(encoding="utf-8"))
    latin = json.loads(LATIN.read_text(encoding="utf-8"))
    coptic_rows = [
        row for row in coptic["rows"]
        if row.get("origin_code") == "ancient-greek"
    ]
    latin_rows = list(latin["rows"])
    latin_full, latin_missing = latin_raw_entries(latin_rows)

    out: list[dict[str, Any]] = []
    coptic_without_greek_text_ids: list[str] = []
    for row in coptic_rows:
        published_source = str(
            row.get("published_source")
            or row.get("ما يقولُه قاموسُ الفرعِ عن الأصل")
            or ""
        )
        tokens, repairs = coptic_published_forms(published_source)
        if not tokens:
            coptic_without_greek_text_ids.append(row["card_id"])
        for token in tokens:
            out.append({
                "greek_form_published": token,
                "source_lane": "coptic",
                "source_card_id": row["card_id"],
                "intermediate_form": " / ".join(row.get("coptic_forms") or []),
                "intermediate_meaning": row.get("meaning") or "",
                "published_source": published_source,
                "source_repairs": repairs,
            })

    latin_without_greek_text = 0
    latin_without_greek_text_ids: list[str] = []
    for row in latin_rows:
        entries = latin_full.get(row["card_id"], [])
        card_tokens: list[str] = []
        source_texts = [entry["full_etymology"] for entry in entries]
        if not source_texts:
            source_texts = [str(row.get("greek_origin_published") or "")]
        for source_text in source_texts:
            tokens = latin_direct_greek_forms(source_text)
            for token in tokens:
                if token not in card_tokens:
                    card_tokens.append(token)
                out.append({
                    "greek_form_published": token,
                    "source_lane": "latin",
                    "source_card_id": row["card_id"],
                    "intermediate_form": row["latin_form"],
                    "intermediate_meaning": row.get("meaning") or "",
                    "published_source": source_text,
                    "source_repairs": [],
                    "greek_source_strata": greek_strata(source_text),
                })
        if not card_tokens:
            latin_without_greek_text += 1
            latin_without_greek_text_ids.append(row["card_id"])

    meta = {
        "input_coptic_rows": len(coptic_rows),
        "coptic_rows_without_published_greek_script": len(coptic_without_greek_text_ids),
        "coptic_rows_without_published_greek_script_ids": coptic_without_greek_text_ids,
        "input_latin_rows_live": len(latin_rows),
        "input_latin_distinct_intermediate_forms_live": len({
            str(row["latin_form"]).casefold() for row in latin_rows
        }),
        "latin_rows_missing_full_raw_match": len(latin_missing),
        "latin_missing_full_raw_match_ids": latin_missing,
        "latin_rows_without_published_greek_script": latin_without_greek_text,
        "latin_rows_without_published_greek_script_ids": latin_without_greek_text_ids,
        "latin_rows_by_named_greek_stratum": dict(Counter(
            (greek_strata(str(row.get("greek_origin_published") or "")) or ["unmarked"])[0]
            for row in latin_rows
        )),
    }
    return out, meta


def raw_greek_entries(forms: set[str]) -> dict[str, list[dict[str, Any]]]:
    found: dict[str, list[dict[str, Any]]] = defaultdict(list)
    with GREEK_RAW.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            raw = json.loads(line)
            word = nfc(raw.get("word"))
            if word not in forms:
                continue
            found[word].append({
                "raw_id": clean_space(raw.get("id")),
                "word": word,
                "romanization": romanization(raw),
                "pos": clean_space(raw.get("pos")),
                "meanings": glosses_of(raw, None),
                "etymology_text": clean_space(raw.get("etymology_text")),
            })
    return dict(found)


FOREIGN_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("egyptian", re.compile(r"(?i)\b(?:from|borrowed from|probably from)\s+(?:Ancient\s+)?Egyptian\b")),
    ("hebrew", re.compile(r"(?i)\b(?:from|borrowed from)\s+(?:Biblical\s+)?Hebrew\b")),
    ("aramaic-syriac", re.compile(r"(?i)\b(?:from|borrowed from)\s+(?:Classical\s+)?(?:Aramaic|Syriac)\b|\baus dem Syrischen\b")),
    ("arabic", re.compile(r"(?i)\b(?:from|borrowed from)\s+Arabic\b")),
    ("akkadian", re.compile(r"(?i)\b(?:from|borrowed from)\s+Akkadian\b")),
    ("semitic", re.compile(r"(?i)\b(?:of\s+)?Semitic origin\b|\bborrowed from\s+Semitic\b|\bfrom\s+Proto-(?:West\s+)?Semitic\b")),
    ("latin", re.compile(r"(?i)\b(?:from|borrowed from)\s+(?:Old\s+)?Latin\b")),
    ("persian-iranian", re.compile(r"(?i)\b(?:from|borrowed from)\s+(?:Old\s+|Middle\s+)?Persian\b|\bfrom\s+(?:Proto-)?Iranian\b")),
    ("coptic", re.compile(r"(?i)\b(?:from|borrowed from)\s+Coptic\b")),
    ("sumerian", re.compile(r"(?i)\b(?:from|borrowed from)\s+Sumerian\b")),
    ("anatolian", re.compile(r"(?i)\b(?:from|borrowed from)\s+(?:Lydian|Lycian|Hittite|Carian)\b")),
    ("pre-greek", re.compile(r"(?i)\bPre-Greek\b|\bpre-Indo-European language\b")),
]

TENTATIVE_ORIGIN = re.compile(
    r"(?i)\b(?:perhaps|possibly|probably|may|might|candidate|tentative(?:ly)?|"
    r"uncertain|unclear|suspect(?:s|ed|ing)?|suggest(?:s|ed|ing)?|claim(?:s|ed|ing)?|"
    r"if|would|assum(?:e|es|ed|ing)|prefer(?:s|red|ring)?|argu(?:e|es|ed|ing))\b"
)

ASSERTED_PRE_GREEK = re.compile(
    r"(?i)^(?:from|of) Pre-Greek\b|^Pre-Greek (?:origin|hydronym)\b|"
    r"\b(?:clearly|undoubtedly) (?:a )?Pre-Greek word\b|"
    r"\b(?:a |the )?(?:Mediterranean[^.]{0,30})?Pre-Greek substrate loanword\b"
)

ORIGIN_DISPUTE_PREFIX = re.compile(
    r"(?i)\b(?:uncertain|unknown|apparently|perhaps|possible|possibly|probably|maybe|may|might|"
    r"according to|alternatively|alternative|theor(?:y|ies)|suggest(?:s|ed|ing)?|"
    r"propos(?:e|es|ed|al)|argu(?:e|es|ed|ing)|claim(?:s|ed|ing)?|"
    r"reject(?:s|ed|ing)?|prefer(?:s|red|ring)?|or)\b"
)


def origin_confidence(code: str, etymology: str, match: re.Match[str]) -> str:
    if code == "pre-greek":
        # لا يخرج من المقام إلا النص الجازم؛ النظريات المتعارضة تبقى مسماة
        # في origin-disputed ولا تتحول إلى نفي للأصل اليوناني.
        native_alternative = re.search(
            r"(?i)\bor from Proto-(?:Indo-European|Hellenic)\b",
            etymology,
        )
        return (
            "asserted"
            if ASSERTED_PRE_GREEK.search(etymology) and not native_alternative
            else "tentative"
        )
    prefix = etymology[:match.end()]
    if ORIGIN_DISPUTE_PREFIX.search(prefix):
        return "tentative"
    if re.search(r"(?i)\bsemantic loan\b", etymology[max(0, match.start() - 80):match.end()]):
        return "tentative"
    explicit_loan = re.search(
        r"(?i)\b(?:borrowed|loaned)(?:\s+ultimately)?\s+from\b|"
        r"\bloan (?:word )?(?:of|from)\b",
        prefix,
    )
    return (
        "asserted"
        if match.start() < 80 or explicit_loan
        else "tentative"
    )


def foreign_routes(entries: Iterable[dict[str, Any]]) -> list[dict[str, str]]:
    routes: list[dict[str, str]] = []
    for entry in entries:
        etymology = str(entry.get("etymology_text") or "")
        for code, pattern in FOREIGN_PATTERNS:
            match = pattern.search(etymology)
            if match:
                confidence = origin_confidence(code, etymology, match)
                item = {
                    "origin_code": code,
                    "confidence": confidence,
                    "entry_id": str(entry.get("raw_id") or ""),
                    "published_etymology": etymology,
                }
                if item not in routes:
                    routes.append(item)
    return routes


def entry_is_named_foreign(entry: dict[str, Any]) -> bool:
    return any(
        route["confidence"] == "asserted"
        for route in foreign_routes([entry])
    )


def entry_has_disputed_foreign(entry: dict[str, Any]) -> bool:
    return any(
        route["confidence"] == "tentative"
        for route in foreign_routes([entry])
    )


def compound_components(form: str, entries: list[dict[str, Any]]) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    if form == "ῥῑνόκερως":
        return [
            {"form": "ῥῑνο", "evidence": "تفكيك المؤلف الملزم في تكليف 2026-08-15"},
            {"form": "κερως", "evidence": "تفكيك المؤلف الملزم في تكليف 2026-08-15"},
        ]
    for entry in entries:
        etymology = str(entry.get("etymology_text") or "")
        first_sentence = etymology.split(". ", 1)[0]
        if "+" not in first_sentence:
            continue
        # لا نعد اللاحقة أو السابقة المعلّمة بشرطة عنصرًا معجميًا مستقلا.
        # المطلوب تفكيك المركب إلى عناصره المنشورة، لا تفكيك كل اشتقاق صرفي.
        components: list[str] = []
        parts = first_sentence.split("+")
        for part_index, part in enumerate(parts):
            repaired, _ = repair_mixed_coptic(part)
            spans: list[tuple[int, int]] = []
            cursor = 0
            while cursor < len(repaired):
                if not is_greek_letter(repaired[cursor]):
                    cursor += 1
                    continue
                start = cursor
                cursor += 1
                while cursor < len(repaired) and (
                    is_greek_letter(repaired[cursor])
                    or unicodedata.combining(repaired[cursor])
                ):
                    cursor += 1
                spans.append((start, cursor))
            if not spans:
                continue
            # قبل أول + قد يسبق التحليل اسم بديل؛ العنصر المقصود أقربها إلى +.
            # وبعد + يكون العنصر المقصود أول رسم، وما بعده شرح أو شاهد.
            start, end = spans[-1] if part_index == 0 else spans[0]
            token = nfc(repaired[start:end])
            left = repaired[:start].rstrip()
            right = repaired[end:].lstrip()
            # السابقة أو الصورة الرابطة عنصر مطلوب؛ اللاحقة الصرفية ليست مركبا.
            if left.endswith("-"):
                continue
            if token != form and token not in components:
                components.append(token)
        if len(components) < 2:
            continue
        for token in components:
            item = {"form": token, "evidence": first_sentence}
            if item not in out:
                out.append(item)
    return out


def build() -> dict[str, Any]:
    occurrences, meta = source_occurrences()
    provenance: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for occurrence in occurrences:
        form = nfc(occurrence["greek_form_published"])
        occurrence = {**occurrence, "greek_form_published": form}
        if occurrence not in provenance[form]:
            provenance[form].append(occurrence)

    entries = raw_greek_entries(set(provenance))
    components_by_parent: dict[str, list[dict[str, str]]] = {}
    for form in sorted(provenance):
        components = compound_components(form, entries.get(form, []))
        if components:
            components_by_parent[form] = components

    # كل عنصر منشور في تفكيك مركب يصير وحدة فحص مستقلة مع حفظ أبويه.
    for parent, components in components_by_parent.items():
        for component in components:
            form = nfc(component["form"])
            occurrence = {
                "greek_form_published": form,
                "source_lane": "compound-component",
                "source_card_id": "",
                "intermediate_form": parent,
                "intermediate_meaning": "",
                "published_source": component["evidence"],
                "source_repairs": [],
            }
            if occurrence not in provenance[form]:
                provenance[form].append(occurrence)

    missing_component_forms = set(provenance) - set(entries)
    if missing_component_forms:
        # الفهرس المبني كاف هنا للعنصر المضاف بعد المسح الخام؛ الغياب لا ينفيه.
        branch = json.loads(
            (ROOT / "data" / "branch-lexicons" / "ancient-greek.json")
            .read_text(encoding="utf-8")
        )
        all_entries = branch.get("entries") or []
        by_dedup_word: dict[str, list[int]] = defaultdict(list)
        for index, item in enumerate(all_entries):
            by_dedup_word[dedup_greek_key(item.get("word"))].append(index)
        for form in sorted(missing_component_forms):
            # لا تسقط النبر أو التنفس هنا؛ ذلك كان يخلط ἀμμά بـἅμμα.
            for index in by_dedup_word.get(dedup_greek_key(form), []):
                item = all_entries[index]
                entries.setdefault(form, []).append({
                    "raw_id": "",
                    "word": item.get("word") or form,
                    "romanization": item.get("read") or "",
                    "pos": item.get("pos") or "",
                    "meanings": str(item.get("en") or "").split("؛ "),
                    "etymology_text": item.get("etym") or "",
                })

    # اجمع اختلافات الكم والحالة في مدخلة واحدة، مع إبقاء كل صورة منشورة
    # وكل مدخلة معجمية. لا يطرح المفتاح النبر أو التنفس، فلا يخلط مدخلتين.
    exact_provenance = provenance
    exact_entries = entries
    exact_components = components_by_parent
    grouped: dict[str, list[str]] = defaultdict(list)
    for form in exact_provenance:
        grouped[dedup_greek_key(form)].append(form)
    representative_for_exact: dict[str, str] = {}
    variants_by_form: dict[str, list[str]] = {}
    for variants in grouped.values():
        representative = preferred_published_form(variants)
        variants_by_form[representative] = sorted(variants)
        for variant in variants:
            representative_for_exact[variant] = representative

    provenance = defaultdict(list)
    entries = defaultdict(list)
    components_by_parent = defaultdict(list)
    for exact_form, occurrences_for_form in exact_provenance.items():
        representative = representative_for_exact[exact_form]
        for occurrence in occurrences_for_form:
            if occurrence not in provenance[representative]:
                provenance[representative].append(occurrence)
        for entry in exact_entries.get(exact_form, []):
            if entry not in entries[representative]:
                entries[representative].append(entry)
        for component in exact_components.get(exact_form, []):
            exact_component = nfc(component["form"])
            remapped = {
                **component,
                "form": representative_for_exact[exact_component],
            }
            if remapped not in components_by_parent[representative]:
                components_by_parent[representative].append(remapped)

    rows: list[dict[str, Any]] = []
    origin_counts: Counter[str] = Counter()
    for index, form in enumerate(sorted(provenance), 1):
        form_entries = entries.get(form, [])
        source_origin_entries = [{
            "raw_id": item.get("source_card_id") or "",
            "etymology_text": item.get("published_source") or "",
        } for item in provenance[form]]
        routes = foreign_routes([*form_entries, *source_origin_entries])
        foreign_flags = [entry_is_named_foreign(entry) for entry in form_entries]
        disputed_flags = [entry_has_disputed_foreign(entry) for entry in form_entries]
        source_foreign = any(
            entry_is_named_foreign(entry) for entry in source_origin_entries
        )
        source_disputed = any(
            entry_has_disputed_foreign(entry) for entry in source_origin_entries
        )
        if foreign_flags and all(foreign_flags):
            status = "redirect-named-foreign"
        elif any(foreign_flags) or (form_entries and source_foreign):
            status = "mixed-homographs"
        elif not form_entries and source_foreign:
            status = "redirect-named-foreign"
        elif any(disputed_flags) or source_disputed:
            status = "origin-disputed"
        elif form_entries:
            status = "greek-or-unresolved"
        else:
            status = "source-gap"
        origin_counts[status] += 1
        rows.append({
            "inventory_id": f"GREEK-ORIGIN-{index:05d}",
            "greek_form_published": form,
            "greek_forms_published_variants": variants_by_form[form],
            "source_lanes": sorted({item["source_lane"] for item in provenance[form]}),
            "provenance": provenance[form],
            "dictionary_entries": form_entries,
            "compound_components": components_by_parent.get(form, []),
            "origin_status": status,
            "foreign_origin_routes": routes,
        })

    by_form = {row["greek_form_published"]: row for row in rows}
    direct_forms = {
        representative_for_exact[nfc(occurrence["greek_form_published"])]
        for occurrence in occurrences
    }
    direct_forms_by_lane = {
        lane: {
            representative_for_exact[nfc(occurrence["greek_form_published"])]
            for occurrence in occurrences
            if occurrence["source_lane"] == lane
        }
        for lane in ("coptic", "latin")
    }
    compound_parents = set(components_by_parent)
    component_forms = {
        nfc(component["form"])
        for components in components_by_parent.values()
        for component in components
    }
    analysis_units = (direct_forms - compound_parents) | component_forms
    redirected_direct = {
        form for form in direct_forms
        if by_form[form]["origin_status"] == "redirect-named-foreign"
    }
    redirected_analysis = {
        form for form in analysis_units
        if by_form[form]["origin_status"] == "redirect-named-foreign"
    }
    return {
        "schema": "greek-origin-inventory-v1",
        "date": "2026-08-15",
        "policy": (
            "NFC Greek forms are deduplicated by case and quantity marks only; accent and "
            "breathing remain contrastive. Every published spelling and every homograph entry "
            "is retained. Latin and Coptic intermediaries are provenance only. Published "
            "compound components are separate analysis units; dictionary absence is SOURCE-GAP "
            "and never a negative verdict."
        ),
        "input_counts": meta,
        "counts": {
            "published_occurrences": len(occurrences),
            "distinct_greek_forms_after_components": len(rows),
            "direct_distinct_forms_before_components": len(direct_forms),
            "direct_distinct_forms_by_source_lane": {
                lane: len(forms)
                for lane, forms in direct_forms_by_lane.items()
            },
            "direct_distinct_forms_shared_by_both_lanes": len(
                direct_forms_by_lane["coptic"] & direct_forms_by_lane["latin"]
            ),
            "compound_parents_with_published_decomposition": len(components_by_parent),
            "distinct_component_forms": len(component_forms),
            "analysis_units_after_replacing_compounds_with_components": len(analysis_units),
            "named_foreign_origin_direct_forms_redirected": len(redirected_direct),
            "corrected_direct_greek_denominator": len(direct_forms - redirected_direct),
            "named_foreign_origin_analysis_units_redirected": len(redirected_analysis),
            "corrected_analysis_denominator": len(analysis_units - redirected_analysis),
            "origin_status": dict(origin_counts),
            "by_source_lane": dict(Counter(
                occurrence["source_lane"] for occurrence in occurrences
            )),
        },
        "rows": rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--check",
        action="store_true",
        help="أعد البناء في الذاكرة وافشل إذا اختلف الملف المحفوظ.",
    )
    args = parser.parse_args()
    payload = build()
    rendered = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    if args.check:
        if not OUT.exists() or OUT.read_text(encoding="utf-8") != rendered:
            raise SystemExit(f"STALE: {OUT.relative_to(ROOT)}")
    else:
        OUT.write_text(rendered, encoding="utf-8", newline="\n")
    print(json.dumps({
        "input_counts": {
            key: value for key, value in payload["input_counts"].items()
            if key != "latin_missing_full_raw_match_ids"
        },
        "counts": payload["counts"],
        "out": str(OUT.relative_to(ROOT)),
        "check": args.check,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
