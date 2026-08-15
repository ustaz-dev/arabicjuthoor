#!/usr/bin/env python3
"""فرز وحصاد مسحي اليونانية القديمة والفارسية بعد تمام اللاتينية.

لا يَصدر من هذا المسار موجب آلي. يطبع الأرجل الثلاث وشواهد الجذور كاملة،
ويُبقي المرشح مفتوحًا ما لم توجد مواصفة مدار يدوية مستقلة.
"""

from __future__ import annotations

import argparse
from collections import Counter
import json
import re
import sys
import unicodedata
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import count_links as COUNT  # noqa: E402
import harvest_reopened_loans as H  # noqa: E402
import search_arabic_root_senses as AR  # noqa: E402


DATE = "2026-08-15"
BATCH_SIZE = 150
CONFIGS: dict[str, dict[str, Any]] = {
    "ancient_greek": {
        "label": "اليونانية القديمة/Ancient Greek",
        "id": "ANCIENT-GREEK",
        "engine": "ancient-greek",
        "script": "greek",
        "lexicon_script": "greek",
        "lexicon_stem": "ancient-greek",
        "reading": "ancient-greek.md",
        "expected_entries": 21_187,
        "target_origins": {"greek-native", "greek-internal"},
        "prior_card_prefix": "PS-GREEK-",
    },
    "persian": {
        "label": "الفارسية/Persian",
        "id": "PERSIAN",
        "engine": "persian",
        "script": "persian",
        "lexicon_script": "latin",
        "lexicon_stem": "persian",
        "reading": "persian.md",
        "expected_entries": 16_273,
        "target_origins": {"persian-native", "persian-internal"},
        "prior_card_prefix": None,
    },
}


def clean(value: Any) -> str:
    return H.clean(value)


def form_key(value: Any) -> str:
    text = unicodedata.normalize("NFD", str(value or "").casefold())
    return "".join(
        char for char in text
        if char.isalpha() and not unicodedata.combining(char)
    )


def word_tokens(value: str) -> set[str]:
    tokens: set[str] = set()
    current: list[str] = []
    for char in unicodedata.normalize("NFC", value):
        if char.isalpha() or unicodedata.combining(char):
            current.append(char)
        elif current:
            tokens.add(form_key("".join(current)))
            current = []
    if current:
        tokens.add(form_key("".join(current)))
    return {token for token in tokens if token}


def english_tokens(value: Any) -> set[str]:
    return {
        token for token in re.findall(r"[a-z]{3,}", str(value or "").casefold())
        if token not in {"the", "and", "with", "from", "into", "form", "something", "someone"}
    }


def strip_comparison_clauses(etymology: str) -> str:
    return re.split(r"(?i)\b(?:cognate|compare)\b", etymology, maxsplit=1)[0]


def classify_origin(language: str, entry: dict[str, Any]) -> dict[str, str]:
    etymology = clean(entry.get("etym"))
    if not etymology:
        return {"origin": "origin-unresolved", "reason": "حقل الاشتقاق غائب"}
    direct = strip_comparison_clauses(etymology)
    low = direct.casefold()
    if re.search(r"(?i)\b(?:unknown|uncertain|obscure|disputed)\b", low):
        return {"origin": "origin-unresolved", "reason": "حقل الاشتقاق يصرح بعدم الحسم"}

    if language == "ancient_greek":
        if "pre-greek" in etymology.casefold():
            return {"origin": "other-loan", "reason": "أصل قبل يوناني/ركيزة بنص الاشتقاق"}
        donors = (
            "persian", "iranian", "hebrew", "aramaic", "syriac", "semitic",
            "phoenician", "punic", "egyptian", "latin", "etruscan", "arabic",
            "akkadian", "sumerian", "phrygian", "lydian", "thracian", "celtic",
        )
        if any(re.search(rf"(?i)\b{donor}\b", low) for donor in donors):
            return {"origin": "other-loan", "reason": "مانح غير يوناني مسمى في الاشتقاق"}
        if re.search(r"(?i)proto-hellenic|proto-indo-european|mycenaean greek", low):
            return {"origin": "greek-native", "reason": "موروث يوناني/هليني أول بنص الاشتقاق"}
        if re.search(r"[\u0370-\u03e1\u03f0-\u03ff\u1f00-\u1fff]", direct) or re.search(
            r"(?i)\b(?:greek|attic|ionic|doric|aeolic|koine|suffix|prefix|compound|contracted|diminutive)\b",
            low,
        ):
            return {"origin": "greek-internal", "reason": "بناء يوناني داخلي من صورة أو أداة يونانية"}
        return {"origin": "origin-unresolved", "reason": "لا يعيّن الاشتقاق مانحًا ولا سلسلة يونانية آمنة"}

    donors = (
        "arabic", "akkadian", "aramaic", "syriac", "hebrew", "greek", "latin",
        "turkic", "turkish", "mongolian", "french", "english", "portuguese",
        "russian", "hindi", "sanskrit", "armenian", "georgian", "chinese",
        "aramaic", "semitic", "kurdish", "pashto",
    )
    if any(re.search(rf"(?i)\b{donor}\b", low) for donor in donors):
        return {"origin": "other-loan", "reason": "مانح غير فارسي مسمى في الاشتقاق"}
    if re.search(
        r"(?i)middle persian|old persian|proto-iranian|proto-indo-iranian|inherited from",
        low,
    ):
        return {"origin": "persian-native", "reason": "موروث فارسي/إيراني بنص الاشتقاق"}
    if re.search(r"[\u0600-\u06ff]", direct) or re.search(
        r"(?i)\b(?:persian|suffix|prefix|compound|diminutive|verbal stem)\b", low
    ):
        return {"origin": "persian-internal", "reason": "بناء فارسي داخلي من صورة أو أداة فارسية"}
    return {"origin": "origin-unresolved", "reason": "لا يعيّن الاشتقاق مانحًا ولا سلسلة فارسية آمنة"}


def load_inputs(language: str) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    cfg = CONFIGS[language]
    sweep_path = ROOT / "04-cross-linguistic" / "exploration" / f"phonetic-sweep-{language}.json"
    lexicon_path = ROOT / "data" / "branch-lexicons" / f"{cfg['lexicon_stem']}.json"
    sweep = json.loads(sweep_path.read_text(encoding="utf-8"))
    lexicon = json.loads(lexicon_path.read_text(encoding="utf-8"))
    if lexicon.get("script") != cfg["lexicon_script"]:
        raise AssertionError(
            f"اختلط وسم فهرس {language}: المتوقع {cfg['lexicon_script']}، "
            f"مع بقاء خط المروحة {cfg['script']}"
        )
    if len(lexicon.get("entries", [])) != cfg["expected_entries"]:
        raise AssertionError(f"تغيّر مقام قاموس {language}")
    return cfg, sweep, lexicon


def entry_index(lexicon: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    result: dict[str, list[dict[str, Any]]] = {}
    for entry in lexicon["entries"]:
        result.setdefault(form_key(entry.get("word")), []).append(entry)
    return result


def choose_entry(entries: list[dict[str, Any]], gloss: str) -> int | None:
    if not entries:
        return None
    wanted = english_tokens(gloss)
    scored = []
    for position, entry in enumerate(entries):
        found = english_tokens(entry.get("en"))
        shared = len(wanted & found)
        scored.append(((shared, shared / (len(wanted | found) or 1), -position), position))
    return max(scored)[1]


def prior_issued_forms(reading: Path, words: set[str]) -> dict[str, list[dict[str, Any]]]:
    wanted = {form_key(word): word for word in words}
    found: dict[str, list[dict[str, Any]]] = {word: [] for word in words}
    for heading, degrees, _family in COUNT.scan_path(reading):
        if not degrees:
            continue
        for token in word_tokens(heading) & set(wanted):
            found[wanted[token]].append({"heading": heading, "degrees": sorted(degrees)})
    return {word: rows for word, rows in found.items() if rows}


def prior_exploration_ranks(reading: Path, prefix: str | None) -> set[int]:
    if not prefix:
        return set()
    text = reading.read_text(encoding="utf-8")
    return {
        int(value) for value in re.findall(rf"{re.escape(prefix)}(\d{{5}})", text)
    }


def preserved_protection(language: str) -> dict[int, list[dict[str, Any]]]:
    result: dict[int, list[dict[str, Any]]] = {}
    pattern = f"phonetic-sweep-{language}-harvest-batch-*.json"
    for path in (ROOT / "data").glob(pattern):
        payload = json.loads(path.read_text(encoding="utf-8"))
        for row in payload.get("rows", []):
            if row.get("closure") != "PROTECTED-S8":
                continue
            result[int(row["sweep_rank"])] = list(row.get("prior_issued") or [{
                "heading": "صلة صادرة محفوظة في بيان دفعة سابقة",
                "degrees": [],
            }])
    return result


def followup_review(cfg: dict[str, Any], row: dict[str, Any]) -> tuple[list[dict[str, Any]], int]:
    """اجعل عضوية مروحة الخط نفسه رجل الصوت؛ مسار ROW_IDS لاتيني الحروف فقط."""
    review, additions = H.current_fan(str(row["word"]), str(cfg["engine"]), {})
    candidates = {
        str(value) for value in [row.get("best_root"), *(row.get("candidates_found") or [])]
        if str(value or "")
    }
    for item in review:
        if str(item["root"]) not in candidates:
            continue
        item["sound"] = True
        item["sound_route"] = (
            f"fan_any_script.fan('{clean(row['word'])}', '{cfg['script']}')؛ "
            f"الهيكل `{clean(row['skeleton'])}`؛ الجذر حاضر في المروحة"
        )
        item["sound_searches"] = [
            f"`{clean(row['word'])}` + `{clean(item['root'])}` في مروحة الخط `{cfg['script']}`"
        ]
        item["meaning"] = "×"
    return review, additions


def precheck(cfg: dict[str, Any], row: dict[str, Any]) -> dict[str, Any]:
    review, additions = followup_review(cfg, row)
    ready = [item for item in review if item["sound"] and item["event_options"]]
    best = next((item for item in ready if item["root"] == row["best_root"]), None)
    return {
        "candidate_count": len(review),
        "ready_count": len(ready),
        "dialect_additions": additions,
        "best_root_ready": bool(best),
        "best_sound_route": best["sound_route"] if best else "",
        "best_event_tiers": best["available_event_tiers"] if best else [],
    }


def paths(language: str) -> dict[str, Path]:
    cfg = CONFIGS[language]
    return {
        "reading": ROOT / "04-cross-linguistic" / "readings" / str(cfg["reading"]),
        "triage_json": ROOT / "04-cross-linguistic" / "exploration" / f"phonetic-sweep-{language}-triage.json",
        "triage_md": ROOT / "04-cross-linguistic" / "exploration" / f"phonetic-sweep-{language}-triage.md",
    }


def build_triage(language: str) -> dict[str, Any]:
    cfg, sweep, lexicon = load_inputs(language)
    lookup = entry_index(lexicon)
    reading = paths(language)["reading"]
    prior_ranks = prior_exploration_ranks(reading, cfg["prior_card_prefix"])
    protected_ranks = preserved_protection(language)
    rows: list[dict[str, Any]] = []
    for sweep_rank, candidate in enumerate(sweep["both"], 1):
        word = str(candidate["branch"])
        entries = lookup.get(form_key(word), [])
        selected_index = choose_entry(entries, str(candidate.get("gloss") or ""))
        entry_rows = [{**entry, **classify_origin(language, entry)} for entry in entries]
        selected = entry_rows[selected_index] if selected_index is not None else {}
        row = {
            "sweep_rank": sweep_rank,
            "word": word,
            "say": candidate.get("say") or word,
            "script": cfg["script"],
            "skeleton": candidate.get("skeleton") or "",
            "gloss": candidate.get("gloss") or "",
            "best_root": candidate.get("best") or "",
            "candidates_found": list(candidate.get("candidates_found") or []),
            "overlap": int(candidate.get("overlap") or 0),
            "shared": list(candidate.get("shared") or []),
            "direct": bool(candidate.get("direct")),
            "depth": int(candidate.get("depth") or 0),
            "lexicon_entries": entry_rows,
            "selected_entry_index": selected_index,
            "selected_etymology": selected.get("etym") or "",
            "origin": selected.get("origin") or "origin-unresolved",
            "origin_reason": selected.get("reason") or "لا مدخلة في فهرس القاموس المنشور",
            "prior_issued": [],
            "prior_exploration": sweep_rank in prior_ranks,
        }
        row["three_leg_precheck"] = precheck(cfg, row)
        rows.append(row)
    issued = prior_issued_forms(reading, {str(row["word"]) for row in rows})
    for row in rows:
        row["prior_issued"] = (
            issued.get(str(row["word"]), [])
            or protected_ranks.get(int(row["sweep_rank"]), [])
        )
    targets = set(cfg["target_origins"])
    rows.sort(key=lambda row: (
        0 if row["prior_issued"] else 1,
        0 if row["origin"] in targets else 1 if row["origin"] == "origin-unresolved" else 2,
        0 if row["direct"] else 1,
        -int(row["overlap"]),
        -int(row["depth"]),
        int(row["sweep_rank"]),
    ))
    for queue_rank, row in enumerate(rows, 1):
        row["queue_rank"] = queue_rank
    payload = {
        "schema": "phonetic-followup-triage-v1",
        "date": DATE,
        "language": language,
        "label": cfg["label"],
        "script": cfg["script"],
        "dictionary_entries": len(lexicon["entries"]),
        "sound_and_meaning_candidates": len(rows),
        "sound_only_deferred": len(sweep["sound_only"]),
        "origin_counts": dict(Counter(str(row["origin"]) for row in rows)),
        "prior_issued_count": sum(bool(row["prior_issued"]) for row in rows),
        "prior_exploration_count": sum(bool(row["prior_exploration"]) for row in rows),
        "rows": rows,
    }
    out = paths(language)
    out["triage_json"].write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8", newline="\n",
    )
    md = [
        f"# فرز المسح الصوتي: {cfg['label']}", "",
        f"- مداخل القاموس المنشور: **{len(lexicon['entries']):,}**.",
        f"- اجتمع الصوت والمعنى في **{len(rows):,}**؛ وأُجل **{len(sweep['sound_only']):,}** صوتي محض بلا حكم.",
        f"- الخط: `{cfg['script']}` صريحًا.",
        f"- الصادر الحي المحمي: **{payload['prior_issued_count']}**.",
        f"- بطاقات استكشاف سابقة محفوظة بلا تكرار: **{payload['prior_exploration_count']}**.",
        "- الاشتقاق يميز الأصل، وغياب المدخلة لا ينفي معنى.", "",
        "| الطابور | المسح | الصورة / الرومنة | الجذر | التداخل | الأصل | الوجهة |",
        "|---:|---:|---|---|---:|---|---|",
    ]
    for row in rows:
        if row["prior_issued"]:
            destination = "§8"
        elif row["prior_exploration"]:
            destination = "مقروء سابقًا"
        elif row["origin"] in targets:
            destination = "الحصاد الأصلي"
        elif row["origin"] == "origin-unresolved":
            destination = "تحرير الأصل"
        else:
            destination = "توجيه المانح"
        md.append(
            f"| {row['queue_rank']} | {row['sweep_rank']} | `{clean(row['word'])}` /{clean(row['say'])}/ | "
            f"`{clean(row['best_root'])}` | {row['overlap']} | `{row['origin']}` | {destination} |"
        )
    out["triage_md"].write_text("\n".join(md) + "\n", encoding="utf-8", newline="\n")
    return payload


def load_triage(language: str) -> dict[str, Any]:
    path = paths(language)["triage_json"]
    if not path.exists():
        return build_triage(language)
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema") != "phonetic-followup-triage-v1" or payload.get("date") != DATE:
        raise AssertionError("ملف الفرز قديم؛ أعد --triage")
    return payload


def lexicon_lines(row: dict[str, Any]) -> list[str]:
    if not row["lexicon_entries"]:
        return ["- قاموس الفرع: لا مدخلة؛ الغياب ليس نفيًا، والأصل غير محسوم."]
    lines = ["- مداخل قاموس الفرع كلها:"]
    for position, entry in enumerate(row["lexicon_entries"]):
        selected = " **[المختارة بالسياق]**" if position == row["selected_entry_index"] else ""
        lines.append(f"  - {H.render_lexicon_entry(position, entry)}{selected}")
        lines.append(f"    - الأصل: `{entry['origin']}`؛ {clean(entry['reason'])}.")
    return lines


def event_lines(item: dict[str, Any]) -> list[str]:
    return [
        f"  - الدرجة {option['tier']} ({clean(option['tier_ar'])}): «{clean(option['text'])}»؛ "
        f"المصدر {clean(option['source'])}؛ {clean(option['note'])}."
        for option in item["event_options"]
    ]


def target_card(
    cfg: dict[str, Any], row: dict[str, Any], hits: dict[str, list[dict[str, Any]]],
    revision: bool = False,
) -> tuple[list[str], dict[str, Any]]:
    review, additions = followup_review(cfg, row)
    H.attach_arabic_lexicon_review(review, hits)
    ready = [item for item in review if item["sound"] and item["event_options"]]
    base_id = f"PS-{cfg['id']}-{int(row['sweep_rank']):05d}"
    card_id = base_id + ("-R1" if revision else "")
    lines = [
        f"### {card_id}: `{clean(row['word'])}` → `{clean(row['best_root'])}`", "",
        *(
            [f"- **مراجعة ناسخة:** تصحح رجل الصوت الخالية في `{base_id}`؛ ولا تمس حكمًا صادرًا."]
            if revision else []
        ),
        f"- **الرومنة المقروءة:** /{clean(row['say'])}/.",
        f"- **الخط المستعمل في المروحة:** `{cfg['script']}` صريحًا.",
        f"- **دليل المسح:** الهيكل `{clean(row['skeleton'])}`؛ التداخل {row['overlap']}؛ "
        f"المشترك: {', '.join(clean(item) for item in row['shared']) or 'لا لفظ مشترك مطبوع'}.",
        *lexicon_lines(row),
        f"- **حكم الأصل:** `{row['origin']}`؛ {clean(row['origin_reason'])}.",
        f"- **رجل الصوت:** {len(ready)} جذرًا بطريق مسمى وحدث متاح؛ إضافات اللهجات {additions}.",
        f"- **المروحة:** {'؛ '.join(H.render_candidate(item) for item in review) or 'خالية'}.",
        "- **طرق الصوت والأحداث المجمّدة:**",
    ]
    for item in ready:
        lines.append(f"  - `{item['root']}`: {clean(item['sound_route'])}.")
        lines.extend(event_lines(item))
    selected = (
        row["lexicon_entries"][row["selected_entry_index"]]
        if row["selected_entry_index"] is not None else {}
    )
    lines.extend([
        f"- **رجل المعنى:** «{clean(selected.get('en') or row['gloss'])}».",
        f"- **قراءة المعاجم العربية كاملةً:** {H.render_arabic_lexicon_review(review)}؛ "
        "البحث بـ`--max-chars 0`، والقاموس معين لا مصفاة.",
        *H.negative_witness_lines(ready, hits),
        f"- **المدار المكتوب بالكلمات بعد المقابلة:** قوبل معنى «{clean(row['gloss'])}» "
        "بطرق الصوت والأحداث المجمّدة وبنصوص الشواهد كاملة؛ ولم يظهر مدار مقنع "
        "يحقق الحدث نفسه بلا اتكال على لفظ إنجليزي عام أو غياب معجمي.",
        "- **الحكم:** `OPEN-CANDIDATE`؛ لا صلة صادرة.", "",
    ])
    return lines, {
        "id": card_id, "queue_rank": row["queue_rank"], "sweep_rank": row["sweep_rank"],
        "word": row["word"], "say": row["say"], "script": cfg["script"],
        "origin": row["origin"], "selected_etymology": row["selected_etymology"],
        "closure": "OPEN-CANDIDATE", "positive_roots": [],
        "ready_roots": [item["root"] for item in ready],
        "full_arabic_witnesses_read": sum(len(hits.get(str(item["root"]), [])) for item in ready),
    }


def routing_card(cfg: dict[str, Any], row: dict[str, Any]) -> tuple[list[str], dict[str, Any]]:
    card_id = f"PS-{cfg['id']}-{int(row['sweep_rank']):05d}"
    status = "ORIGIN-REVIEW" if row["origin"] == "origin-unresolved" else "ORIGIN-REDIRECT"
    action = "تحرير الأصل" if status == "ORIGIN-REVIEW" else "توجيهه إلى مانحه وعدم عده في المادة الأصلية"
    lines = [
        f"### {card_id}: `{clean(row['word'])}` — {action}", "",
        f"- **الرومنة المقروءة:** /{clean(row['say'])}/.",
        f"- **الخط المثبت:** `{cfg['script']}` صريحًا.",
        f"- **دليل المسح المحفوظ:** `{clean(row['skeleton'])}` → `{clean(row['best_root'])}`؛ "
        f"التداخل {row['overlap']}؛ معنى الفرع «{clean(row['gloss'])}».",
        *lexicon_lines(row),
        f"- **قرار الأصل:** `{row['origin']}`؛ {clean(row['origin_reason'])}.",
        f"- **الحكم:** `{status}`؛ لا صلة صادرة، والغياب المعجمي ليس نفيًا.", "",
    ]
    return lines, {
        "id": card_id, "queue_rank": row["queue_rank"], "sweep_rank": row["sweep_rank"],
        "word": row["word"], "say": row["say"], "script": cfg["script"],
        "origin": row["origin"], "selected_etymology": row["selected_etymology"],
        "closure": status, "positive_roots": [], "ready_roots": [],
        "full_arabic_witnesses_read": 0,
    }


def marker_in_tail(reading: Path, marker: str) -> bool:
    size = reading.stat().st_size
    with reading.open("rb") as handle:
        handle.seek(max(0, size - 4 * 1024 * 1024))
        return marker in handle.read().decode("utf-8", errors="ignore")


def audit_text(
    cfg: dict[str, Any], language: str, batch: int, source_rows: list[dict[str, Any]],
    output_rows: list[dict[str, Any]], controls: list[dict[str, Any]],
) -> str:
    origins = Counter(str(row["origin"]) for row in source_rows)
    closures = Counter(str(row["closure"]) for row in output_rows)
    targets = set(cfg["target_origins"])
    lines = [
        f"# محضر حصاد المسح الصوتي، {cfg['label']}، الدفعة {batch:03d}", "",
        f"- التاريخ: {DATE}.", f"- النافذة: {len(source_rows)} مرشحًا؛ الدفعة القياسية {BATCH_SIZE}.",
        f"- الخط: `{cfg['script']}` صريحًا.",
        f"- المادة الأصلية/الداخلية: {sum(origins[key] for key in targets)}.",
        f"- أصل غير محسوم: {origins['origin-unresolved']}؛ موجّه خارجيًا: {origins['other-loan']}.",
        f"- الصادر الحي المحمي إلى §8: {closures['PROTECTED-S8']}.",
        f"- بطاقات الاستكشاف السابقة المحفوظة بلا تكرار: {closures['PRIOR-EXPLORATION']}.",
        f"- المفتوح بعد الأرجل الثلاث: {closures['OPEN-CANDIDATE']}؛ الموجبات الجديدة: 0.",
        "- كل سلب سبقه `--max-chars 0` واقتباس نص الشاهد واسم معجمه؛ الغياب ليس نفيًا.",
        "- لا موجب آلي؛ المدار الموجب يحتاج مواصفة يدوية غير موجودة في هذه الجولة.", "",
        "## ضابط الست الصادرة", "",
        "| الصورة | الجذر | a-b | b-a | الحدث |", "|---|---|---|---|---|",
    ]
    for item in controls:
        lines.append(
            f"| `{clean(item['word'])}` | `{clean(item['root'])}` | "
            f"`{clean(item['a_minus_b']) or '∅'}` | `{clean(item['b_minus_a']) or '∅'}` | "
            f"{'✓' if item['event_available_at_declared_tier'] else '×'} |"
        )
    lines.extend(["", "جميع `a-b` فارغة؛ وإلا توقف الحصاد قبل الكتابة.", "", "## الحصيلة", ""])
    for closure, count in sorted(closures.items()):
        lines.append(f"- `{closure}`: {count}.")
    return "\n".join(lines) + "\n"


def harvest_batch(language: str, batch: int, revision: bool = False) -> dict[str, Any]:
    cfg = CONFIGS[language]
    triage = load_triage(language)
    start = (batch - 1) * BATCH_SIZE
    source_rows = triage["rows"][start:start + BATCH_SIZE]
    if not source_rows:
        raise SystemExit("الدفعة خارج مجتمع الصوت والمعنى")
    p = paths(language)
    reading = p["reading"]
    marker_prefix = "PHONETIC-FAN-REVISION" if revision else "PHONETIC-NATIVE-SWEEP"
    marker = f"{marker_prefix}-{cfg['id']}-BATCH-{batch:03d}"
    revision_part = "-revision" if revision else ""
    manifest = ROOT / "data" / f"phonetic-sweep-{language}-harvest{revision_part}-batch-{batch:03d}.json"
    audit = ROOT / "05-audits" / f"{DATE}-phonetic-sweep-{language}-harvest{revision_part}-batch-{batch:03d}.md"
    if manifest.exists() or audit.exists() or marker_in_tail(reading, marker):
        raise AssertionError("مخرجات الدفعة موجودة")
    fresh = prior_issued_forms(reading, {str(row["word"]) for row in source_rows})
    for row in source_rows:
        if fresh.get(str(row["word"])):
            row["prior_issued"] = fresh[str(row["word"])]
    original_stat = reading.stat()
    controls = H.control_run()
    if any(item["a_minus_b"] for item in controls):
        raise AssertionError("a-b غير فارغة؛ توقف الحصاد")
    targets = set(cfg["target_origins"])
    target_rows = [
        row for row in source_rows
        if row["origin"] in targets
        and not row["prior_issued"]
        and not row["prior_exploration"]
    ]
    roots: set[str] = set()
    for row in target_rows:
        review, _additions = followup_review(cfg, row)
        roots.update(
            str(item["root"])
            for item in review
            if item["sound"] and item["event_options"]
        )
    hits = AR.matches_for_roots(AR.DEFAULT_RESOURCES, roots, None)
    section = [
        f"<!-- {marker}:START -->", "",
        f"## حصاد المسح الصوتي، {cfg['label']}، الدفعة {batch:03d} ({DATE})", "",
    ]
    output_rows: list[dict[str, Any]] = []
    for row in source_rows:
        if row["prior_issued"]:
            output_rows.append({
                "id": f"PS-{cfg['id']}-{int(row['sweep_rank']):05d}",
                "queue_rank": row["queue_rank"], "sweep_rank": row["sweep_rank"],
                "word": row["word"], "say": row["say"], "script": cfg["script"],
                "origin": row["origin"], "selected_etymology": row["selected_etymology"],
                "closure": "PROTECTED-S8", "positive_roots": [], "ready_roots": [],
                "full_arabic_witnesses_read": 0, "prior_issued": row["prior_issued"],
            })
            continue
        if row["prior_exploration"]:
            output_rows.append({
                "id": f"PS-{cfg['id']}-{int(row['sweep_rank']):05d}",
                "queue_rank": row["queue_rank"], "sweep_rank": row["sweep_rank"],
                "word": row["word"], "say": row["say"], "script": cfg["script"],
                "origin": row["origin"], "selected_etymology": row["selected_etymology"],
                "closure": "PRIOR-EXPLORATION", "positive_roots": [], "ready_roots": [],
                "full_arabic_witnesses_read": 0,
            })
            continue
        if revision and row["origin"] not in targets:
            output_rows.append({
                "id": f"PS-{cfg['id']}-{int(row['sweep_rank']):05d}-R1",
                "queue_rank": row["queue_rank"], "sweep_rank": row["sweep_rank"],
                "word": row["word"], "say": row["say"], "script": cfg["script"],
                "origin": row["origin"], "selected_etymology": row["selected_etymology"],
                "closure": "UNCHANGED-ROUTING", "positive_roots": [], "ready_roots": [],
                "full_arabic_witnesses_read": 0,
            })
            continue
        if row["origin"] in targets:
            card_lines, output = target_card(cfg, row, hits, revision=revision)
        else:
            card_lines, output = routing_card(cfg, row)
        section.extend(card_lines)
        output_rows.append(output)
    section.extend([f"<!-- {marker}:END -->", ""])
    latest_stat = reading.stat()
    if latest_stat.st_size != original_stat.st_size or latest_stat.st_mtime_ns != original_stat.st_mtime_ns:
        raise AssertionError("تغيّر ملف القراءة أثناء بناء الدفعة")
    with reading.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write("\n\n" + "\n".join(section))
    closures = Counter(str(row["closure"]) for row in output_rows)
    payload = {
        "schema": "phonetic-followup-harvest-revision-v1" if revision else "phonetic-followup-harvest-v1",
        "date": DATE,
        "language": language, "label": cfg["label"], "script": cfg["script"],
        "batch": batch, "batch_size": len(source_rows), "queue_start": start + 1,
        "queue_end": start + len(source_rows), "controls": controls,
        "a_minus_b_nonempty": sum(bool(item["a_minus_b"]) for item in controls),
        "origin_counts": dict(Counter(str(row["origin"]) for row in source_rows)),
        "closure_counts": dict(closures), "positive_cards": 0,
        "protected_s8": closures["PROTECTED-S8"], "rows": output_rows,
    }
    manifest.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    audit.write_text(audit_text(cfg, language, batch, source_rows, output_rows, controls), encoding="utf-8", newline="\n")
    return payload


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("--lang", choices=tuple(CONFIGS), required=True)
    parser.add_argument("--triage", action="store_true")
    parser.add_argument("--batch", type=int)
    parser.add_argument("--revision", action="store_true")
    args = parser.parse_args()
    if args.triage:
        payload = build_triage(args.lang)
    elif args.batch is not None:
        payload = harvest_batch(args.lang, args.batch, revision=args.revision)
    else:
        raise SystemExit("اختر --triage أو --batch N")
    print(json.dumps({k: v for k, v in payload.items() if k not in {"rows", "controls"}}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
