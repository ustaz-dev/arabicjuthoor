# -*- coding: utf-8 -*-
"""مولّد تاريخي منسوخ بأمر المؤلف في 2026-08-15؛ لا يُشغّل.

مخرجاته القديمة محفوظة مدخلًا تاريخيًا لطبقة النسخ، لكن قاعدته التي جعلت
قول CCL في الأصل بوابة استبعاد أُبطلت. المولّد النافذ هو
``reexamine_coptic_arabic.py``: يقابل القبطية وصور لهجاتها والصورة اليونانية
نفسها بالعربية، ويجعل المقام 3,301 كاملًا.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import types
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import build_coptic_index as COP  # noqa: E402
import fan_any_script as FAN  # noqa: E402
import frozen_event as FE  # noqa: E402

DATE = "2026-08-15"
BATCH_SIZE = 150
EXPECTED = 3301
BASELINE = "1281ac5"
READING = ROOT / "04-cross-linguistic" / "readings" / "coptic.md"
RESERVE = ROOT / "data" / "non-coptic-borrowings-in-coptic.json"
GREEK = re.compile(r"[\u0370-\u03e1\u03f0-\u03ff\u1f00-\u1fff]")

CONTROLS = [
    {"word": "mou", "root": "موت", "event_tier": 1, "card": "ⲙⲟⲩ mou «die»"},
    {"word": "soshf", "root": "خسف", "event_tier": 1,
     "card": "ⲥⲱϣϥ sōšf «be despised, humbled»"},
    {"word": "kah", "root": "قوع", "event_tier": 1,
     "card": "ⲕⲁϩ kah «earth, soil»"},
    {"word": "solp", "root": "سلب", "event_tier": 1,
     "card": "ⲥⲱⲗⲡ sōlp «cut off; strip»"},
    {"word": "beb", "root": "باب", "event_tier": 3,
     "card": "ⲃⲏⲃ bēb «cave, hole, den, nest»"},
    {"word": "oft", "root": "فت", "event_tier": 2,
     "card": "ⲱϥⲧ ōft «be worn, eaten away, emaciated»"},
]


def clean(value: Any) -> str:
    return " ".join(str(value or "").split()).replace("`", "ˋ")


def atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
        os.replace(temp_name, path)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def baseline_module() -> types.ModuleType:
    source = subprocess.run(
        ["git", "show", f"{BASELINE}:scripts/fan_any_script.py"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    ).stdout
    module = types.ModuleType("fan_any_script_baseline")
    exec(compile(source, "fan_any_script_baseline", "exec"), module.__dict__)
    return module


def control_run() -> list[dict[str, Any]]:
    old = baseline_module()
    rows: list[dict[str, Any]] = []
    for spec in CONTROLS:
        before = set(old.fan(str(spec["word"]), "coptic"))
        after = set(FAN.fan(str(spec["word"]), "coptic"))
        lost = sorted(before - after)
        gained = sorted(after - before)
        if lost:
            raise AssertionError(
                f"يقف الحصاد: ضاع مرشح في {spec['word']}: a-b={lost}; b-a={gained}"
            )
        event = FE.resolve(str(spec["root"]), tier=int(spec["event_tier"]))
        if event is None:
            raise AssertionError(
                f"درجة البطاقة غير متاحة: {spec['root']} tier={spec['event_tier']}"
            )
        rows.append({
            **spec,
            "baseline": BASELINE,
            "old_count": len(before),
            "new_count": len(after),
            "a_minus_b": lost,
            "b_minus_a": gained,
            "candidate_in_old": spec["root"] in before,
            "candidate_in_new": spec["root"] in after,
            "event_available_at_declared_tier": True,
            "event_tier_ar": event.tier_ar,
            "event_text": event.text,
        })
    return rows


def source_line(block: str) -> str:
    match = re.search(r"^- أقدمُ صورةٍ مستعادة:\s*(.*)$", block, re.MULTILINE)
    return match.group(1).strip() if match else ""


def original_cards() -> list[dict[str, Any]]:
    body = READING.read_text(encoding="utf-8")
    pattern = re.compile(r"LOAN-REOPEN-COPTIC-(\d+)")
    found: dict[int, dict[str, Any]] = {}
    for block in re.split(r"(?=^### )", body, flags=re.MULTILINE):
        if "أعيدت إلى الطابور" not in block or "سطر النسخ (2026-08-05" not in block:
            continue
        matches = pattern.findall(block)
        if not matches:
            continue
        index = int(matches[-1])
        word_line_match = re.search(r"^- الكلمةُ? في الفرع:\s*(.*)$", block, re.MULTILINE)
        meaning_match = re.search(r"^- المعنى من قاموس الفرع:\s*«([^»]*)»", block, re.MULTILINE)
        if not word_line_match or not meaning_match:
            raise AssertionError(f"تعذر استخراج صورة أو معنى البطاقة {index}")
        word_line = word_line_match.group(1).strip()
        ids = {
            left or right
            for left, right in re.findall(
                r"kellia_coptic_lexicon:(C\d+)|KELLIA\s+(C\d+)", word_line
            )
        }
        ids.update(re.findall(r"\bC\d+\b", word_line))
        if not ids:
            marker = re.search(r"lane-b-week2-full-coverage:coptic:(C\d+)", block)
            if marker:
                ids.add(marker.group(1))
        if not ids:
            raise AssertionError(f"لا معرف CCL في البطاقة {index}")
        found[index] = {
            "index": index,
            "old_id": f"LOAN-REOPEN-COPTIC-{index:05d}",
            "heading": block.splitlines()[0].removeprefix("### ").strip(),
            "word_line": word_line,
            "meaning": meaning_match.group(1).strip(),
            "source": source_line(block),
            "entry_ids": sorted(ids, key=lambda value: int(value[1:])),
        }
    cards = [found[index] for index in sorted(found)]
    if len(cards) != EXPECTED or [card["index"] for card in cards] != list(range(3, 3304)):
        raise AssertionError(
            f"جرد القبطية {len(cards)} لا يساوي {EXPECTED} أو لا يغطي 00003 إلى 03303"
        )
    return cards


def index_entries() -> dict[str, dict[str, Any]]:
    return {
        str(entry.get("id")): entry
        for entry in COP.lexicon()["entries"]
        if entry.get("id")
    }


def dictionary_review(card: dict[str, Any], by_id: dict[str, dict[str, Any]]) -> dict[str, Any]:
    selected = [by_id[entry_id] for entry_id in card["entry_ids"] if entry_id in by_id]
    missing = [entry_id for entry_id in card["entry_ids"] if entry_id not in by_id]
    if missing:
        raise AssertionError(f"معرفات CCL غائبة في {card['old_id']}: {missing}")
    hits: list[dict[str, Any]] = []
    signatures: set[str] = set()
    paths: list[str] = []
    for entry in selected:
        form = str(entry.get("latin") or entry.get("coptic") or "")
        current, path = COP.look(form)
        if path not in paths:
            paths.append(path)
        for hit in current:
            signature = json.dumps(hit, ensure_ascii=False, sort_keys=True)
            if signature not in signatures:
                signatures.add(signature)
                hits.append(hit)
    selected_ids = {str(entry.get("id")) for entry in selected}
    returned_ids = {str(entry.get("id")) for entry in hits}
    if not selected_ids <= returned_ids:
        raise AssertionError(
            f"بحث CCL لم يعد المدخل المختار في {card['old_id']}: {sorted(selected_ids-returned_ids)}"
        )
    return {
        "call": [f"build_coptic_index.look({entry['latin']!r})" for entry in selected],
        "paths": paths,
        "selected": selected,
        "all_homographic_entries": hits,
        "selected_ids": sorted(selected_ids, key=lambda value: int(value[1:])),
        "romanizations": list(dict.fromkeys(str(entry.get("latin") or "") for entry in selected)),
        "forms": list(dict.fromkeys(str(entry.get("coptic") or "") for entry in selected)),
        "dialects": list(dict.fromkeys(
            dialect
            for entry in selected
            for dialect in (entry.get("dialects") or ["غير موسومة في CCL"])
        )),
        "references": list(dict.fromkeys(
            str(entry.get("ref") or "لا إحالة معجمية مطبوعة في المدخل")
            for entry in selected
        )),
        "etymologies": list(dict.fromkeys(
            str(entry.get("etymology") or card["source"])
            for entry in selected
        )),
    }


def classify_origin(source: str) -> dict[str, Any]:
    lower = source.casefold()
    if GREEK.search(source) or "اليونان" in source:
        return {
            "origin": "اليونانية القديمة",
            "origin_code": "ancient-greek",
            "named_semitic": False,
            "closure": "OPEN-CANDIDATE",
            "target": "مسار اليونانية القديمة",
        }
    named = (
        ("العربية", "arabic", r"arabisch|arabic|العربي"),
        ("الآرامية", "aramaic", r"aramäisch|aramaic|الآرام"),
        ("العبرية", "hebrew", r"hebräisch|hebrew|العبر"),
        ("السريانية", "syriac", r"syriakisch|syriac|السريان"),
    )
    for donor, code, pattern in named:
        if re.search(pattern, lower, re.IGNORECASE):
            return {
                "origin": donor,
                "origin_code": code,
                "named_semitic": True,
                "closure": "LOANWORD",
                "target": "سجل المانحين الساميين المسمين",
            }
    other = (
        ("الفارسية", "persian", r"persisch|persian|الفارس"),
        ("الحامية الليبية", "hamitic-libyan", r"hamitisch.libysch|hamitic.libyan|الحامي"),
    )
    for donor, code, pattern in other:
        if re.search(pattern, lower, re.IGNORECASE):
            return {
                "origin": donor,
                "origin_code": code,
                "named_semitic": False,
                "closure": "OPEN-CANDIDATE",
                "target": f"مسار {donor}",
            }
    raise AssertionError(f"أصل غير مصنف: {source}")


def render_entry(position: int, entry: dict[str, Any]) -> str:
    dialects = "، ".join(entry.get("dialects") or ["غير موسومة في CCL"])
    etymology = clean(entry.get("etymology")) or "لا تأثيل مطبوع"
    reference = clean(entry.get("ref")) or "لا إحالة مطبوعة"
    return (
        f"#{position} `{clean(entry.get('id'))}` `{clean(entry.get('coptic'))}` "
        f"/{clean(entry.get('latin'))}/، اللهجة: {dialects}، النوع: "
        f"{clean(entry.get('pos')) or 'غير مطبوع'}، المعنى: «{clean(entry.get('en'))}»، "
        f"الإحالة: {reference}، التأثيل: {etymology}"
    )


def build_card(card: dict[str, Any], by_id: dict[str, dict[str, Any]], batch: int) -> tuple[list[str], dict[str, Any]]:
    review = dictionary_review(card, by_id)
    origin = classify_origin(str(card["source"]))
    new_id = f"LH-COPTIC-{int(card['index']):05d}"
    romanizations = "، ".join(f"/{clean(value)}/" for value in review["romanizations"])
    forms = "، ".join(f"`{clean(value)}`" for value in review["forms"])
    dialects = "، ".join(clean(value) for value in review["dialects"])
    references = "؛ ".join(clean(value) for value in review["references"])
    etymologies = "؛ ".join(clean(value) for value in review["etymologies"])
    homographs = "؛ ".join(
        render_entry(position, entry)
        for position, entry in enumerate(review["all_homographic_entries"], 1)
    ) or "لا مدخل"
    lines = [
        f"### بطاقة حصاد القرض المعاد فتحه: {forms} {romanizations}؛ {new_id}",
        f"<!-- LOAN-HARVEST-REREVIEW:{card['old_id']} -->",
        f"- ناسخ البطاقة السابقة: `{card['old_id']}` ← `{new_id}`؛ بقي النص السابق كاملًا، وهذا الحكم هو النافذ بتاريخ {DATE}.",
        "- اللسان المستقبِل: القبطية/Coptic؛ الطبقة: استكشاف.",
        f"- الصورة القبطية: {forms}؛ الرومنة المطبوعة: {romanizations}.",
        f"- اللهجة في CCL: {dialects}.",
        f"- معنى قاموس الفرع بلا رتوش: «{clean(card['meaning'])}».",
        f"- إحالة Crum وسائر مراجع المدخل: {references}.",
        f"- وسم الطريق في `build_coptic_index.look`: {'، '.join(review['paths'])}؛ الاستعلام: {'، '.join(review['call'])}.",
        f"- كل مداخل الرسم المتجانس التي أعادها الفهرس ({len(review['all_homographic_entries'])}): {homographs}.",
        f"- المداخل المختارة بسياق البطاقة: {', '.join(review['selected_ids'])}؛ تأثيلها: {etymologies}.",
        f"- الأصل المنشور المحفوظ من البطاقة التاريخية: {clean(card['source'])}",
        f"- نتيجة فحص الأصل: الصورة ليست قبطية الأصل؛ أصلها المسمى: **{origin['origin']}**.",
    ]
    if origin["named_semitic"]:
        lines.extend([
            f"- المانح السامي المسمى: {origin['origin']}؛ يغلق بطاقة الاستقبال بنص القاعدة القبطية الخاصة.",
            "- المروحة والحدث والمدار: لا تُستعمل لصناعة صلة بعد ثبوت جهة النقل؛ هذا إغلاق قرض لا حكم نسب.",
            "- الحكم (استكشاف): **LOANWORD (استكشاف)**؛ لا تدخل البطاقة عد الصلات.",
            "- حالة الإغلاق: LOANWORD.",
        ])
    else:
        lines.extend([
            f"- وجهة المادة: {origin['target']}؛ لا تُهمَل ولا تُحسب في مقام القبطية المصحح.",
            "- المروحة والحدث والمدار: لم تُحاكم الصورة المنقولة بوصفها أصلًا قبطيًا؛ تُفحص مادتها في لسان الأصل نفسه.",
            "- الحكم (استكشاف): **غير صادر (استكشاف)**؛ ذكر الناقل غير السامي لا يغلق سؤال أصل المادة.",
            f"- عائق: النوع=OPEN-CANDIDATE؛ يتطلب=حصاد المادة في {origin['target']} مع الأرجل الثلاث هناك.",
            "- حالة الإغلاق: OPEN-CANDIDATE.",
        ])
    lines.append("")
    row = {
        "card_id": new_id,
        "supersedes": card["old_id"],
        "original_index": card["index"],
        "batch": batch,
        "coptic_forms": review["forms"],
        "romanizations": review["romanizations"],
        "dialects": review["dialects"],
        "meaning": card["meaning"],
        "dictionary": review,
        "published_source": card["source"],
        "origin": origin,
        "closure": origin["closure"],
        "counted_link": False,
        "excluded_from_corrected_coptic_denominator": True,
    }
    return lines, row


def control_audit(controls: list[dict[str, Any]]) -> list[str]:
    lines = [
        "## نتيجة الضابط الإلزامي",
        "",
        f"قوبلت المروحة الحالية بالنسخة المرجعية `{BASELINE}` على ست بطاقات قبطية صادرة حية. معيار الوقوف الوحيد هو `a - b`.",
        "",
        "| البطاقة | المرشح | درجة البطاقة | القديم | الجديد | `a - b` | `b - a` | حدث الدرجة | القرار |",
        "|---|---|---:|---:|---:|---|---|---|---|",
    ]
    for row in controls:
        lines.append(
            f"| {row['card']} | `{row['root']}` | {row['event_tier']} | "
            f"{row['old_count']} | {row['new_count']} | "
            f"{row['a_minus_b'] or '∅'} | {row['b_minus_a'] or '∅'} | "
            f"متاح: {clean(row['event_text'])} | امضِ |"
        )
    lines.extend([
        "",
        "- النتيجة: `a - b = ∅` في البطاقات الست، فلا فقد في الأداة ويُمضى في الحصاد.",
        "- عضوية مرشح البطاقة في المروحة لم تُجعل شرطًا. المروحتان فارغتان في هذه العينة، وهو ثبات لا سبب وقف.",
        "- فُحصت رجل الحدث بـ`FE.resolve(c, tier=n)` في درجة كل بطاقة، ولم يُستبدل بها حدث درجة أعلى.",
        "",
    ])
    return lines


def audit_text(batch: int, rows: list[dict[str, Any]], controls: list[dict[str, Any]]) -> str:
    origins = Counter(row["origin"]["origin_code"] for row in rows)
    closures = [row for row in rows if row["closure"] == "LOANWORD"]
    opened = [row for row in rows if row["closure"] == "OPEN-CANDIDATE"]
    lines = [
        f"# حصاد القرض المعاد فتحه: القبطية، الدفعة {batch:03d} ({DATE})",
        "",
    ]
    if batch == 1:
        lines.extend(control_audit(controls))
    lines.extend([
        "## القانون والقراءة",
        "",
        "- قُرئت كل مداخل الرسم المتجانس من CCL، وطُبعت الرومنة واللهجة وإحالة Crum أو غيابها الصريح في كل بطاقة.",
        "- الأصل اليوناني ليس إغلاقًا؛ وُجّه إلى مسار اليونانية القديمة وبقي OPEN-CANDIDATE.",
        "- المانح العربي أو السامي المسمى أغلق LOANWORD بلا صلة.",
        "- كل صورة ثبت أنها غير قبطية الأصل أُلحقت بسجل `data/non-coptic-borrowings-in-coptic.json`.",
        "",
        "## الحصيلة",
        "",
        f"- فُحص: {len(rows)} بطاقة.",
        f"- كُتب: {len(rows)} بطاقة ناسخة ملحقة، بلا محو نص تاريخي.",
        "- موجب بالأرجل الثلاث: 0 بطاقة، و0 صلة.",
        f"- أُغلق بمانح سامي مسمى: {len(closures)} بطاقة LOANWORD، ولا واحدة منها صلة.",
        f"- بقي OPEN-CANDIDATE موجها إلى لسان الأصل: {len(opened)} بطاقة.",
        f"- خارج مقام القبطية لثبوت الأصل غير القبطي: {len(rows)} بطاقة.",
        "- مقام القبطية المصحح في هذه الدفعة: 0 بطاقة.",
        f"- تفصيل الأصول: {json.dumps(dict(origins), ensure_ascii=False, sort_keys=True)}.",
        "",
        "## أسباب الفتح بالعد",
        "",
    ])
    for code, count in sorted(origins.items()):
        subset = [row for row in rows if row["origin"]["origin_code"] == code]
        if subset and subset[0]["closure"] == "OPEN-CANDIDATE":
            lines.append(f"- {count} بطاقة: مادة {subset[0]['origin']['origin']} موجهة إلى {subset[0]['origin']['target']}.")
    lines.extend(["", "## أبرز عشرة مسارات دخلت", ""])
    for row in rows[:10]:
        form = row["coptic_forms"][0] if row["coptic_forms"] else ""
        roman = row["romanizations"][0] if row["romanizations"] else ""
        lines.append(
            f"- `{clean(form)}` /{clean(roman)}/ → {row['origin']['origin']}، {row['closure']}."
        )
    lines.extend(["", "## مقام الطابور المصحح", ""])
    lines.append(
        f"- المقام الخام لهذه الدفعة {len(rows)}، والمستبعد المثبت غير القبطي {len(rows)}، فالمقام القبطي المصحح 0. المادة باقية في سجل الأصول وليست مهملة."
    )
    lines.append("")
    return "\n".join(lines)


def reserve_payload() -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for path in sorted((ROOT / "data").glob("reopened-loan-coptic-harvest-batch-*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        for row in payload.get("rows") or []:
            rows.append({
                "card_id": row["card_id"],
                "original_index": row["original_index"],
                "batch": row["batch"],
                "coptic_forms": row["coptic_forms"],
                "romanizations": row["romanizations"],
                "dialects": row["dialects"],
                "meaning": row["meaning"],
                "published_source": row["published_source"],
                "origin": row["origin"]["origin"],
                "origin_code": row["origin"]["origin_code"],
                "target": row["origin"]["target"],
                "closure_in_coptic": row["closure"],
                "counted_link_in_coptic": False,
                "dictionary_entry_ids": row["dictionary"]["selected_ids"],
                "dictionary_references": row["dictionary"]["references"],
            })
    rows.sort(key=lambda row: int(row["original_index"]))
    by_origin = Counter(row["origin_code"] for row in rows)
    return {
        "schema": "non-coptic-borrowings-in-coptic-v1",
        "date": DATE,
        "source": "Comprehensive Coptic Lexicon v1.2 via build_coptic_index.look",
        "policy": (
            "المادة غير القبطية لا تدخل مقام القبطية المصحح. المانح السامي "
            "المسمى يغلق LOANWORD بلا صلة، وغيره يبقى موجها إلى مسار لسان الأصل."
        ),
        "counts": {
            "processed_queue_cards": len(rows),
            "excluded_non_coptic_origin_cards": len(rows),
            "corrected_coptic_denominator": 0,
            "named_semitic_loan_closures": sum(row["closure_in_coptic"] == "LOANWORD" for row in rows),
            "redirected_open_cards": sum(row["closure_in_coptic"] == "OPEN-CANDIDATE" for row in rows),
            "by_origin": dict(sorted(by_origin.items())),
        },
        "rows": rows,
    }


def write_reserve() -> dict[str, Any]:
    payload = reserve_payload()
    atomic_write(RESERVE, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    return payload


def main() -> int:
    raise SystemExit(
        "هذا المولد منسوخ. شغّل scripts/reexamine_coptic_arabic.py؛ "
        "قول CCL في الأصل خبر لا بوابة استبعاد."
    )
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch", type=int, required=True)
    args = parser.parse_args()
    cards = original_cards()
    start = (args.batch - 1) * BATCH_SIZE
    window = cards[start:start + BATCH_SIZE]
    if not window:
        raise SystemExit("الدفعة خارج الجرد")
    marker = f"LOAN-HARVEST-COPTIC-BATCH-{args.batch:03d}"
    audit = ROOT / "05-audits" / f"{DATE}-reopened-loan-coptic-harvest-batch-{args.batch:03d}.md"
    manifest = ROOT / "data" / f"reopened-loan-coptic-harvest-batch-{args.batch:03d}.json"
    reading_text = READING.read_text(encoding="utf-8")
    if audit.exists() or manifest.exists() or f"<!-- {marker}:START -->" in reading_text:
        raise AssertionError(f"مخرجات الدفعة {args.batch} موجودة من قبل")

    controls = control_run() if args.batch == 1 else []
    by_id = index_entries()
    rows: list[dict[str, Any]] = []
    card_lines: list[str] = []
    for card in window:
        lines, row = build_card(card, by_id, args.batch)
        card_lines.extend(lines)
        rows.append(row)

    counts = Counter(row["origin"]["origin_code"] for row in rows)
    payload = {
        "schema": "reopened-loan-coptic-harvest-v1",
        "date": DATE,
        "language": "coptic",
        "batch": args.batch,
        "batch_size": len(rows),
        "controls": controls,
        "positive_cards": 0,
        "positive_traces": 0,
        "named_semitic_loan_closures": sum(row["closure"] == "LOANWORD" for row in rows),
        "open_cards": sum(row["closure"] == "OPEN-CANDIDATE" for row in rows),
        "excluded_non_coptic_origin_cards": len(rows),
        "corrected_coptic_denominator": 0,
        "by_origin": dict(sorted(counts.items())),
        "rows": rows,
    }
    section = "\n".join([
        f"<!-- {marker}:START -->",
        "",
        f"## حصاد القرض المعاد فتحه، الدفعة {args.batch:03d} ({DATE})",
        "",
        *card_lines,
        f"<!-- {marker}:END -->",
        "",
    ])
    if READING.read_text(encoding="utf-8") != reading_text:
        raise AssertionError("تغير ملف القراءة أثناء بناء الدفعة؛ أوقف الحفظ")
    atomic_write(manifest, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    atomic_write(audit, audit_text(args.batch, rows, controls))
    atomic_write(READING, reading_text.rstrip() + "\n\n" + section)
    reserve = write_reserve()
    print(json.dumps({
        "batch": args.batch,
        "cards": len(rows),
        "origins": dict(counts),
        "loanword_closures": payload["named_semitic_loan_closures"],
        "open": payload["open_cards"],
        "reserve_cards": reserve["counts"]["processed_queue_cards"],
        "corrected_coptic_denominator": 0,
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
