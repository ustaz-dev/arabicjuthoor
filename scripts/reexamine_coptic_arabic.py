# -*- coding: utf-8 -*-
"""إعادةُ فحص طابور CCL القبطي كلِّه بالعربيّة (أمر المؤلف 2026-08-15).

الأصل المنشور في CCL خبرٌ محفوظ، لا بوابةُ استبعاد. لذلك تفحص هذه الأداة
الصور القبطية كلّها، وصور اللهجات المسجلة في المدخل، ثم الصورة اليونانية
نفسها حين يسميها التأثيل. وتكتب مروحة كل صورة كاملة، وكل درجات الحدث، وكل
شواهد الجذور العربية بلا قطع. لا تصدر الأداة حكمًا موجبًا من تلقاء نفسها؛
الموجبات الوحيدة مواصفات يدوية صريحة، ومدار كل واحد منها مكتوب باليد هنا.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
import unicodedata
from collections import Counter
from dataclasses import asdict
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import fan_any_script as FAN  # noqa: E402
import frozen_event as FE  # noqa: E402
import search_arabic_root_senses as ARS  # noqa: E402


DATE = "2026-08-15"
EXPECTED_DENOMINATOR = 3301
EXPECTED_REEXAMINED = 3284
EXPECTED_NAMED_SEMITIC = 17
BATCH_SIZE = 150
READING = ROOT / "04-cross-linguistic" / "readings" / "coptic.md"
AUDIT = ROOT / "05-audits" / f"{DATE}-reopened-loan-coptic-harvest-final.md"
SUMMARY = ROOT / "data" / "coptic-arabic-reexamination.json"
EVENTS = ROOT / "data" / "coptic-arabic-reexamination-events.jsonl"
LEGACY_WITNESSES = ROOT / "data" / "coptic-arabic-reexamination-root-witnesses.jsonl"
WITNESS_GLOB = "coptic-arabic-reexamination-root-witnesses-part-*.jsonl"
WITNESS_DISPLAY = "data/coptic-arabic-reexamination-root-witnesses-part-*.jsonl"
ORIGIN_REGISTER = ROOT / "data" / "non-coptic-borrowings-in-coptic.json"
BLOCK_START = "<!-- COPTIC-ARABIC-REEXAMINATION:START -->"
BLOCK_END = "<!-- COPTIC-ARABIC-REEXAMINATION:END -->"
GREEK_RUN = re.compile(
    r"[\u0370-\u03e1\u03f0-\u03ff\u1f00-\u1fff\u0300-\u036f]+"
)
GREEK_BASE = re.compile(r"[\u0370-\u03e1\u03f0-\u03ff\u1f00-\u1fff]")


# لا تنشئ الأداة موجبًا آليًا. هذه التسعة قُرئت شواهدها ومداراتها يدويًا،
# ويقف البناء إن خرج الجذر من المروحة أو غاب نص الشاهد أو درجة الحدث.
MANUAL: dict[int, dict[str, Any]] = {
    682: {
        "root": "بطن", "tier": 1, "source_id": "lisan",
        "quote": "البَطْنُ من كل شيء: جَوْفُه",
        "orbit": (
            "العمق والهاوية انتقالٌ إلى جوف الشيء وانخفاضٌ في باطنه؛ فمعنى "
            "الفرع يلتقي نصَّ العربية «البطن جوفه» وحدثَ الجوف الداخلي في مدار "
            "واحد، لا في تشابه صوتي منفرد."
        ),
    },
    774: {
        "root": "جنس", "tier": 3, "source_id": "lisan",
        "quote": "الجِنْسُ: الضَّربُ من كل شيء",
        "orbit": (
            "الجنس يجمع أفرادًا متشابهين تحت حد كلي يستر فروقهم الجزئية؛ فالكثافة "
            "والستر في حدث «جن» يبلغان معنى الصنف والنوع الذي نص عليه الفرع والعربية."
        ),
    },
    1380: {
        "root": "قنن", "tier": 1, "source_id": "taj_al_arus",
        "quote": "والقَوانِينُ: الأُصولُ",
        "orbit": (
            "القانون أصلٌ يحوز الأفعال داخل حد ثابت ويمسكها في نطاقه؛ فالقاعدة "
            "والتعليمة في الفرع تلتقيان نص «القوانين الأصول» وحدث الاحتباس في الحوزة."
        ),
    },
    1642: {
        "root": "قبب", "tier": 1, "source_id": "lisan",
        "quote": "والقُبَّةُ من البناء: معروفة",
        "orbit": (
            "القبة قبوٌ محدب يقوم ظاهره المتسنم فوق فراغ تحته؛ وهذا هو بعينه مدار "
            "الخزنة والقبة في معنى الفرع وحدث الجذر المجمّد."
        ),
    },
    2520: {
        "root": "سكن", "tier": 1, "source_id": "al_sihah",
        "quote": "والمسكن أيضا: المنزل والبيت",
        "orbit": (
            "الخيمة مسكنٌ يحيط بالنازل فيستقر في جوف حيّزه؛ فالدلالة المعجمية "
            "العربية والفرعية وحدث الاستقرار في باطن الحيز تجتمع في مدار واحد."
        ),
    },
    2618: {
        "root": "زوج", "tier": 1, "source_id": "lisan",
        "quote": "الزَّوْجُ الفَرْدُ الذي له قَرِينٌ",
        "orbit": (
            "الزوج فردٌ لا يتم هذا الوصف له إلا بقرين مرتبط به؛ فالاقتران في "
            "الفرع هو تداخل شيئين وارتباطهما في حدث الجذر."
        ),
    },
    2841: {
        "root": "ترف", "tier": 1, "source_id": "asas_al_balagha",
        "quote": "ولم أزل معهم في ترفة أي في نعمة",
        "orbit": (
            "الترف توسع في النعمة والرخاء حتى يتميز صاحبه بسعة العيش؛ وهو مدار "
            "الراحة والنعيم في الفرع وامتلاء الشيء بالري والرخاوة في الحدث."
        ),
    },
    2882: {
        "root": "بين", "tier": 1, "source_id": "al_sihah",
        "quote": "وتبين الشئ: وضح وظهر",
        "orbit": (
            "وضوح الشيء ظهوره منفصلًا عما يلتبس به؛ فالبيان ثمرة الفصل والامتداد "
            "بين طرفين، وهو ما يصل معنى الوضوح في اليونانية بنص العربية وحدث الجذر."
        ),
    },
    3172: {
        "root": "صنو", "tier": 1, "source_id": "al_muhkam",
        "quote": "أصلُها واحدٌ فكلُّ واحدٍ منها صِنْوٌ",
        "orbit": (
            "النسخة نظيرٌ ثانٍ متفرع من أصل نص واحد؛ والصنو واحد من فروع متعددة "
            "يجمعها أصل واحد، فيلتقي معنى duplicate حدثَ تعدد التفرع من أصل."
        ),
    },
}


def clean(value: Any) -> str:
    return " ".join(str(value or "").split()).replace("`", "ˋ")


def nfc(value: Any) -> str:
    return unicodedata.normalize("NFC", str(value or "")).strip()


def unique(values: Iterable[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))


def atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def atomic_write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            for row in rows:
                handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def atomic_write_split_jsonl(
    rows: Iterable[dict[str, Any]], max_bytes: int = 80_000_000
) -> list[Path]:
    """اكتب سجل الشواهد في أجزاء دون حد GitHub الصلب، بلا قطع أي تعريف."""
    data_dir = ROOT / "data"
    paths: list[Path] = []
    handle = None
    temporary = ""
    size = 0
    part = 0

    def open_part() -> tuple[Any, str, Path]:
        nonlocal part
        part += 1
        path = data_dir / f"coptic-arabic-reexamination-root-witnesses-part-{part:03d}.jsonl"
        fd, temp_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=data_dir)
        return os.fdopen(fd, "w", encoding="utf-8", newline="\n"), temp_name, path

    try:
        for row in rows:
            line = json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n"
            encoded_size = len(line.encode("utf-8"))
            if handle is None or (size and size + encoded_size > max_bytes):
                if handle is not None:
                    handle.close()
                    os.replace(temporary, paths[-1])
                handle, temporary, path = open_part()
                paths.append(path)
                size = 0
            handle.write(line)
            size += encoded_size
        if handle is not None:
            handle.close()
            handle = None
            os.replace(temporary, paths[-1])
    finally:
        if handle is not None:
            handle.close()
        if temporary and os.path.exists(temporary):
            os.unlink(temporary)

    keep = set(paths)
    for stale in data_dir.glob(WITNESS_GLOB):
        if stale not in keep:
            stale.unlink()
    if LEGACY_WITNESSES.exists():
        LEGACY_WITNESSES.unlink()
    return paths


def legacy_paths() -> list[Path]:
    return sorted((ROOT / "data").glob("reopened-loan-coptic-harvest-batch-*.json"))


def load_legacy_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in legacy_paths():
        rows.extend(json.loads(path.read_text(encoding="utf-8")).get("rows") or [])
    rows.sort(key=lambda row: int(row["original_index"]))
    if len(rows) != EXPECTED_DENOMINATOR:
        raise AssertionError(f"الجرد القبطي {len(rows)} لا يساوي {EXPECTED_DENOMINATOR}")
    if [int(row["original_index"]) for row in rows] != list(range(3, 3304)):
        raise AssertionError("الجرد القبطي لا يغطي 00003 إلى 03303 بلا فجوة")
    semitic = [row for row in rows if row.get("closure") == "LOANWORD"]
    if len(semitic) != EXPECTED_NAMED_SEMITIC:
        raise AssertionError(f"الإغلاقات السامية {len(semitic)} لا تساوي 17")
    return rows


def origin_statement(row: dict[str, Any]) -> str:
    selected = (row.get("dictionary") or {}).get("selected") or []
    statements = unique(clean(entry.get("etymology")) for entry in selected)
    if not statements:
        statements = [clean(row.get("published_source")) or "لا قول مطبوع في CCL"]
    return "؛ ".join(statements)


def coptic_forms(row: dict[str, Any]) -> list[str]:
    selected = (row.get("dictionary") or {}).get("selected") or []
    forms = unique(
        nfc(form)
        for entry in selected
        for form in (entry.get("forms") or [entry.get("coptic")])
    )
    if not forms:
        forms = unique(nfc(form) for form in row.get("coptic_forms") or [])
    return forms


def greek_forms(row: dict[str, Any]) -> list[str]:
    if (row.get("origin") or {}).get("origin_code") != "ancient-greek":
        return []
    selected = (row.get("dictionary") or {}).get("selected") or []
    texts = [str(entry.get("etymology") or "") for entry in selected]
    texts.append(str(row.get("published_source") or ""))
    forms: list[str] = []
    for text in texts:
        for run in GREEK_RUN.findall(nfc(text)):
            run = run.strip("\u0300\u0301\u0302\u0303\u0304\u0305\u0306\u0307\u0308\u0309\u030a\u030b\u030c\u030d\u030e\u030f\u0310\u0311\u0312\u0313\u0314\u0315\u0316\u0317\u0318\u0319\u031a\u031b\u031c\u031d\u031e\u031f\u0320\u0321\u0322\u0323\u0324\u0325\u0326\u0327\u0328\u0329\u032a\u032b\u032c\u032d\u032e\u032f\u0330\u0331\u0332\u0333\u0334\u0335\u0336\u0337\u0338\u0339\u033a\u033b\u033c\u033d\u033e\u033f\u0340\u0341\u0342\u0343\u0344\u0345\u0346\u0347\u0348\u0349\u034a\u034b\u034c\u034d\u034e\u034f\u0350\u0351\u0352\u0353\u0354\u0355\u0356\u0357\u0358\u0359\u035a\u035b\u035c\u035d\u035e\u035f\u0360\u0361\u0362\u0363\u0364\u0365\u0366\u0367\u0368\u0369\u036a\u036b\u036c\u036d\u036e\u036f")
            if run and GREEK_BASE.search(run):
                forms.append(run)
    return unique(forms)


def fan_record(form: str, script: str, form_source: str) -> dict[str, Any]:
    # النداء المطلوب بنصه، ثم نداء واسع مستقل يثبت أن الحد الافتراضي لم يقتطع.
    base = FAN.fan(form, script)
    unlimited = FAN.fan(form, script, limit=1_000_000)
    if base != unlimited:
        raise AssertionError(f"المروحة الافتراضية مقتطعة في {form!r} ({script})")
    dialect = FAN.fan_with_dialect(form, script)
    base_set = set(base)
    additions = [
        {"root": root, "door": label}
        for root, label in dialect
        if root not in base_set
    ]
    return {
        "form": form,
        "script": script,
        "form_source": form_source,
        "fan_call": f"fan_any_script.fan({form!r}, {script!r})",
        "fan_limit": None,
        "fan_complete": True,
        "fan_count": len(base),
        "fan": base,
        "dialect_call": f"fan_any_script.fan_with_dialect({form!r}, {script!r})",
        "dialect_door_complete": True,
        "dialect_fan_count": len(dialect),
        "dialect_additions": additions,
    }


def comparison_row(row: dict[str, Any]) -> dict[str, Any]:
    index = int(row["original_index"])
    forms = [fan_record(form, "coptic", "CCL form/dialect") for form in coptic_forms(row)]
    forms.extend(fan_record(form, "greek", "CCL published Greek form") for form in greek_forms(row))
    roots = unique(
        root
        for form in forms
        for root in (
            list(form["fan"])
            + [item["root"] for item in form["dialect_additions"]]
        )
    )
    if not forms:
        raise AssertionError(f"لا صورة للمقارنة في {row['card_id']}")
    return {
        "card_id": f"CAR-COPTIC-{index:05d}",
        "supersedes": row["card_id"],
        "original_index": index,
        "coptic_forms": coptic_forms(row),
        "romanizations": row.get("romanizations") or ["غير مطبوعة"],
        "dialects": row.get("dialects") or ["غير موسومة في CCL"],
        "meaning": row.get("meaning") or "",
        "dictionary_entry_ids": (row.get("dictionary") or {}).get("selected_ids") or [],
        "ما يقولُه قاموسُ الفرعِ عن الأصل": origin_statement(row),
        "origin_code": (row.get("origin") or {}).get("origin_code"),
        "origin_is_informational_only": True,
        "comparison_forms": forms,
        "candidate_roots": roots,
        "event_catalog_roots": roots,
        "root_witness_catalog_roots": roots,
        "event_call": "frozen_event.all_tiers(root)",
        "root_witness_call": "search_arabic_root_senses.py ROOT --max-chars 0",
        "arabic_comparison_performed": True,
        "counted_in_denominator": True,
        "closure": "ROOT-TRACE" if index in MANUAL else "OPEN-CANDIDATE",
        "counted_link": index in MANUAL,
        "manual_selection": MANUAL.get(index),
    }


def selected_witness(
    index: int, spec: dict[str, Any], matches: dict[str, list[dict[str, Any]]]
) -> dict[str, Any]:
    candidates = matches.get(spec["root"]) or []
    for item in candidates:
        if ARS.canonical_source_id(str(item.get("source") or "")) != spec["source_id"]:
            continue
        if clean(spec["quote"]) in clean(item.get("definition")):
            return {
                "source_id": spec["source_id"],
                "source_label": ARS.SOURCE_LABELS[spec["source_id"]],
                "quote": spec["quote"],
                "url": item.get("url"),
            }
    raise AssertionError(
        f"الشاهد اليدوي غير موجود كاملًا في نتائج --max-chars 0: {index} {spec['root']}"
    )


def compact_independent_fan(matches: list[dict[str, Any]]) -> dict[str, Any]:
    """احفظ حكم التغطية ومراجع المصادر بلا تكرار نصوصها الكاملة مرتين."""
    fan = ARS.independent_fan(matches)
    fan["selected_sources"] = [
        {
            key: value
            for key, value in item.items()
            if key not in {"definition", "definition_truncated"}
        }
        for item in fan.get("selected_sources") or []
    ]
    return fan


def validate_manual(rows: list[dict[str, Any]], matches: dict[str, list[dict[str, Any]]]) -> None:
    by_index = {int(row["original_index"]): row for row in rows}
    for index, spec in MANUAL.items():
        row = by_index.get(index)
        if row is None:
            raise AssertionError(f"البطاقة اليدوية {index} غائبة")
        hits = [
            form["form"]
            for form in row["comparison_forms"]
            if spec["root"] in form["fan"]
            or spec["root"] in {item["root"] for item in form["dialect_additions"]}
        ]
        if not hits:
            raise AssertionError(f"{spec['root']} خارج المروحة الكاملة في {index}")
        events = FE.all_tiers(spec["root"])
        if not any(event.tier == spec["tier"] for event in events):
            raise AssertionError(f"درجة الحدث {spec['tier']} غائبة لـ{spec['root']}")
        witness = selected_witness(index, spec, matches)
        row["manual_selection"] = {
            **spec,
            "fan_hits": hits,
            "event": asdict(next(event for event in events if event.tier == spec["tier"])),
            "arabic_witness": witness,
            "orbit_written_by_hand": True,
        }


def result_batch_path(batch: int) -> Path:
    return ROOT / "data" / f"coptic-arabic-reexamination-batch-{batch:03d}.json"


def write_result_batches(rows: list[dict[str, Any]]) -> int:
    count = 0
    for offset in range(0, len(rows), BATCH_SIZE):
        count += 1
        window = rows[offset : offset + BATCH_SIZE]
        payload = {
            "schema": "coptic-arabic-reexamination-batch-v1",
            "date": DATE,
            "language": "coptic",
            "batch": count,
            "batch_size": len(window),
            "controls": {
                "origin_is_gate": False,
                "denominator": EXPECTED_DENOMINATOR,
                "coptic_fan_complete": True,
                "dialect_door_complete": True,
                "greek_source_form_compared_when_published": True,
                "all_event_tiers_recorded_in": EVENTS.relative_to(ROOT).as_posix(),
                "full_root_witnesses_recorded_in": WITNESS_DISPLAY,
            },
            "positive_cards": sum(row["closure"] == "ROOT-TRACE" for row in window),
            "open_cards": sum(row["closure"] == "OPEN-CANDIDATE" for row in window),
            "rows": window,
        }
        atomic_write(result_batch_path(count), json.dumps(payload, ensure_ascii=False, indent=1) + "\n")
    return count


def render_forms(values: list[str]) -> str:
    return "، ".join(f"`{clean(value)}`" for value in values)


def render_romans(values: list[str]) -> str:
    return "، ".join(f"/{clean(value)}/" for value in values)


def reading_card(row: dict[str, Any]) -> list[str]:
    index = int(row["original_index"])
    forms = render_forms(row["coptic_forms"])
    romans = render_romans(row["romanizations"])
    origin = clean(row["ما يقولُه قاموسُ الفرعِ عن الأصل"])
    meaning = clean(row["meaning"])
    manifest = f"data/coptic-arabic-reexamination-batch-{((index - 3) // BATCH_SIZE) + 1:03d}.json"
    # البطاقات موزعة بحسب ترتيب الصفوف المفتوحة لا بحسب الرقم؛ صحح الإحالة أدناه
    # عند البناء من الحقل batch المحقون.
    manifest = f"data/coptic-arabic-reexamination-batch-{int(row['batch']):03d}.json"
    heading = f"### بطاقة إعادة الفحص العربي: {forms} {romans}؛ ALR-COPTIC-{index:05d}"
    marker = f"<!-- ARABIC-ROOT-SENSE-REREVIEW:{row['supersedes']} -->"
    if row["closure"] == "OPEN-CANDIDATE":
        line = (
            f"- الحكم (استكشاف): OPEN-CANDIDATE؛ معنى CCL «{meaning}»؛ ما يقولُه قاموسُ الفرعِ عن الأصل: «{origin}». "
            f"فُحصت كل الصور القبطية واللهجية"
            + (" والصورة اليونانية المنشورة" if row["origin_code"] == "ancient-greek" else "")
            + f" بالمروحة الكاملة و`all_tiers` وشواهد الجذور بـ`--max-chars 0` في `{manifest}`؛ "
            "حالة الإغلاق: OPEN-CANDIDATE."
        )
        return [heading, marker, line]

    spec = row["manual_selection"]
    event = spec["event"]
    witness = spec["arabic_witness"]
    comparison_hits = "، ".join(f"`{form}`" for form in spec["fan_hits"])
    greek = [form["form"] for form in row["comparison_forms"] if form["script"] == "greek"]
    return [
        heading,
        marker,
        f"- الصورة القبطية ولهجاتها: {forms}؛ الرومنة: {romans}؛ الصورة اليونانية المنشورة: {render_forms(greek) or 'لا صورة' }.",
        f"- معنى قاموس الفرع: «{meaning}».",
        f"- ما يقولُه قاموسُ الفرعِ عن الأصل: «{origin}»؛ خبرٌ لا يدخل في الحكم ولا في مقام العد.",
        f"- رجل الصوت: الجذر العربي `{spec['root']}` في المروحة الكاملة للصورة/الصور {comparison_hits}؛ تفاصيل المروحة واللهجات في `{manifest}`.",
        f"- رجل الحدث من `frozen_event.all_tiers` (الدرجة {event['tier']}، {event['tier_ar']}): «{clean(event['text'])}»؛ وكل الدرجات في `{EVENTS.relative_to(ROOT).as_posix()}`.",
        f"- شاهد الجذر العربي الكامل: «{clean(witness['quote'])}» [{witness['source_label']}]؛ نتيجة `search_arabic_root_senses.py {spec['root']} --max-chars 0` كاملة في `{WITNESS_DISPLAY}`.",
        f"- المدار المكتوب باليد: {spec['orbit']}",
        f"- الحكم (استكشاف): **ROOT-TRACE**؛ نتيجة الأرجل الثلاث للمقابل `{spec['root']}` موجبة.",
        "- حالة الإغلاق: ROOT-TRACE.",
    ]


def reading_block(rows: list[dict[str, Any]]) -> str:
    lines = [
        BLOCK_START,
        "",
        f"## الأمر الناسخ: إعادة المقارنة العربية للقبطية ({DATE})",
        "",
        "هذا الباب ناسخٌ لحكم التوجيه السابق من غير محو النص التاريخي. كل صورة قبطية، وكل صورة لهجية في CCL، والصورة اليونانية التي يسميها CCL، قوبلت بالعربية بالمروحة الكاملة. «ما يقولُه قاموسُ الفرعِ عن الأصل» خبر محفوظ بجوار المقابلة، لا بوابة حكم ولا استبعاد.",
        "",
        f"المقام هو **{EXPECTED_DENOMINATOR:,}** كاملًا: بقيت إغلاقات المانح السامي المسمى السبعة عشر كما هي، وأعيد فحص {EXPECTED_REEXAMINED:,} بطاقة. كل درجات `frozen_event.all_tiers` وشواهد الجذور الكاملة بـ`--max-chars 0` محفوظة في سجلي البيانات، ولا مدار موجب هنا إلا المدار المكتوب باليد.",
        "",
    ]
    for row in rows:
        lines.extend(reading_card(row))
        lines.append("")
    lines.extend([BLOCK_END, ""])
    return "\n".join(lines)


def replace_reading_block(block: str) -> None:
    text = READING.read_text(encoding="utf-8")
    if BLOCK_START in text:
        start = text.index(BLOCK_START)
        end = text.index(BLOCK_END, start) + len(BLOCK_END)
        text = text[:start].rstrip() + "\n\n" + block + text[end:].lstrip("\n")
    else:
        text = text.rstrip() + "\n\n" + block
    atomic_write(READING, text)


def audit_text(rows: list[dict[str, Any]], counts: dict[str, Any]) -> str:
    lines = [
        f"# إعادة فحص القبطية بالعربية ({DATE})",
        "",
        "## القانون النافذ",
        "",
        "الأصل المنشور في CCL خبرٌ يُكتب في حقل «ما يقولُه قاموسُ الفرعِ عن الأصل» ولا يُستعمل بوابةً للحكم أو العد. فُحصت الصورة القبطية وصور لهجاتها، ثم الصورة اليونانية نفسها حين نشرها CCL، بالعربية وبالأدوات الكاملة.",
        "",
        "هذا المحضر هو النافذ، وينسخ محاضر دفعات التوجيه التاريخية؛ لا يُستفاد منها حكمٌ ولا عدّ، مع بقائها شاهدًا على تسلسل العمل.",
        "",
        f"المقام {EXPECTED_DENOMINATOR:,} كاملًا. الإغلاقات السامية المسماة {EXPECTED_NAMED_SEMITIC} باقية، والبطاقات المعاد فحصها {EXPECTED_REEXAMINED:,}.",
        "",
        "## ما وُجد",
        "",
    ]
    by_index = {int(row["original_index"]): row for row in rows}
    for index in sorted(MANUAL):
        row = by_index[index]
        spec = row["manual_selection"]
        forms = render_forms(row["coptic_forms"])
        greek = [form["form"] for form in row["comparison_forms"] if form["script"] == "greek"]
        lines.append(
            f"- `{row['card_id']}`: {forms} /{clean(row['romanizations'][0])}/"
            + (f"، واليونانية {render_forms(greek)}" if greek else "")
            + f"، «{clean(row['meaning'])}» ↔ `{spec['root']}`؛ ROOT-TRACE. المدار: {spec['orbit']}"
        )
    lines.extend([
        "",
        "## الباقي المفتوح",
        "",
        f"بقي {counts['open_candidates']:,} بطاقة `OPEN-CANDIDATE`، لكل واحدة سطر موجز في القراءة وسجل كامل للمروحة والأحداث والشواهد في ملفات البيانات.",
        "",
        "## مواضع الإثبات",
        "",
        f"- ملخص الجرد: `{SUMMARY.relative_to(ROOT).as_posix()}`.",
        f"- كل درجات الحدث لكل مرشح: `{EVENTS.relative_to(ROOT).as_posix()}`.",
        f"- شواهد الجذور بلا قطع: `{WITNESS_DISPLAY}`.",
        "- دفعات البطاقات التفصيلية: `data/coptic-arabic-reexamination-batch-*.json`.",
        "",
    ])
    return "\n".join(lines)


def load_result_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted((ROOT / "data").glob("coptic-arabic-reexamination-batch-*.json")):
        rows.extend(json.loads(path.read_text(encoding="utf-8")).get("rows") or [])
    rows.sort(key=lambda row: int(row["original_index"]))
    return rows


def published_origin_payload() -> dict[str, Any]:
    legacy = load_legacy_rows()
    results = {int(row["original_index"]): row for row in load_result_rows()}
    if len(results) != EXPECTED_REEXAMINED:
        raise AssertionError("نتائج إعادة الفحص غير مكتملة؛ شغّل reexamine_coptic_arabic.py")
    output: list[dict[str, Any]] = []
    for row in legacy:
        index = int(row["original_index"])
        result = results.get(index)
        named_semitic = row.get("closure") == "LOANWORD"
        if not named_semitic and result is None:
            raise AssertionError(f"نتيجة المقارنة غائبة للبطاقة {index}")
        closure = "LOANWORD" if named_semitic else result["closure"]
        output.append({
            "card_id": row["card_id"] if named_semitic else result["card_id"],
            "original_index": index,
            "coptic_forms": row.get("coptic_forms") or [],
            "romanizations": row.get("romanizations") or [],
            "dialects": row.get("dialects") or [],
            "meaning": row.get("meaning") or "",
            "ما يقولُه قاموسُ الفرعِ عن الأصل": origin_statement(row),
            "origin_code": (row.get("origin") or {}).get("origin_code"),
            "origin_is_informational_only": not named_semitic,
            "named_semitic_donor_closure": named_semitic,
            "arabic_comparison_performed": not named_semitic,
            "counted_in_coptic_denominator": True,
            "closure_in_coptic": closure,
            "counted_link_in_coptic": closure == "ROOT-TRACE",
            "arabic_root": None if named_semitic else (result.get("manual_selection") or {}).get("root"),
        })
    by_origin = Counter(row["origin_code"] for row in output)
    return {
        "schema": "coptic-published-origin-register-v2",
        "date": DATE,
        "source": "Comprehensive Coptic Lexicon v1.2 via build_coptic_index.look",
        "policy": (
            "قول CCL في الأصل خبر لا حكم ولا استبعاد. المقام 3301 كاملًا؛ "
            "لا يغلق إلا المانح السامي المسمى، وكل ما عداه قوبل بالعربية."
        ),
        "counts": {
            "processed_queue_cards": len(output),
            "coptic_denominator": EXPECTED_DENOMINATOR,
            "excluded_by_published_origin": 0,
            "named_semitic_loan_closures": sum(row["named_semitic_donor_closure"] for row in output),
            "arabic_reexaminations": sum(row["arabic_comparison_performed"] for row in output),
            "positive_links": sum(row["counted_link_in_coptic"] for row in output),
            "open_candidates": sum(row["closure_in_coptic"] == "OPEN-CANDIDATE" for row in output),
            "by_published_origin": dict(sorted(by_origin.items())),
        },
        "rows": output,
    }


def build() -> None:
    legacy = load_legacy_rows()
    source_rows = [row for row in legacy if row.get("closure") != "LOANWORD"]
    if len(source_rows) != EXPECTED_REEXAMINED:
        raise AssertionError(f"صفوف إعادة الفحص {len(source_rows)} لا تساوي 3284")

    rows = [comparison_row(row) for row in source_rows]
    roots = set(root for row in rows for root in row["candidate_roots"])
    events = {root: [asdict(event) for event in FE.all_tiers(root)] for root in roots}
    if any(not value for value in events.values()):
        empty = sorted(root for root, value in events.items() if not value)
        raise AssertionError(f"مرشح بلا أي درجة حدث: {empty[:20]}")

    matches = ARS.matches_for_roots(ROOT / "Resources", roots, limit=None)
    if any(item.get("definition_truncated") for values in matches.values() for item in values):
        raise AssertionError("ظهر شاهد مقطوع مع limit=None / --max-chars 0")
    validate_manual(rows, matches)

    atomic_write_jsonl(
        EVENTS,
        (
            {
                "root": root,
                "call": f"frozen_event.all_tiers({root!r})",
                "all_tiers": events[root],
            }
            for root in sorted(roots)
        ),
    )
    witness_paths = atomic_write_split_jsonl(
        (
            {
                "root": root,
                "call": f"python scripts/search_arabic_root_senses.py {root} --max-chars 0",
                "max_chars": 0,
                "definitions_truncated": False,
                "independent_fan": compact_independent_fan(matches.get(root) or []),
                "matches": matches.get(root) or [],
            }
            for root in sorted(roots)
        ),
    )

    for position, row in enumerate(rows):
        row["batch"] = (position // BATCH_SIZE) + 1
    batches = write_result_batches(rows)

    counts = {
        "coptic_denominator": EXPECTED_DENOMINATOR,
        "named_semitic_donor_closures": EXPECTED_NAMED_SEMITIC,
        "arabic_reexaminations": len(rows),
        "published_greek_forms_compared": sum(row["origin_code"] == "ancient-greek" for row in rows),
        "excluded_by_published_origin": 0,
        "positive_links": sum(row["closure"] == "ROOT-TRACE" for row in rows),
        "open_candidates": sum(row["closure"] == "OPEN-CANDIDATE" for row in rows),
        "unique_arabic_candidates": len(roots),
        "candidates_with_lexicographic_witnesses": sum(bool(matches.get(root)) for root in roots),
        "full_lexicographic_witness_records": sum(len(matches.get(root) or []) for root in roots),
        "result_batches": batches,
    }
    summary = {
        "schema": "coptic-arabic-reexamination-v1",
        "date": DATE,
        "law": {
            "every_form_compared_to_arabic": True,
            "published_origin_is_information_only": True,
            "greek_form_itself_compared_to_arabic": True,
            "only_named_semitic_donor_closes_without_comparison": True,
            "fan_complete": True,
            "dialect_door_complete": True,
            "all_event_tiers": True,
            "root_witness_max_chars": 0,
            "orbit_is_handwritten": True,
        },
        "counts": counts,
        "manual_positive_indices": sorted(MANUAL),
        "files": {
            "events": EVENTS.relative_to(ROOT).as_posix(),
            "root_witnesses": WITNESS_DISPLAY,
            "root_witness_parts": len(witness_paths),
            "batches": "data/coptic-arabic-reexamination-batch-*.json",
            "reading": READING.relative_to(ROOT).as_posix(),
            "audit": AUDIT.relative_to(ROOT).as_posix(),
        },
    }
    atomic_write(SUMMARY, json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
    replace_reading_block(reading_block(rows))
    atomic_write(AUDIT, audit_text(rows, counts))
    atomic_write(ORIGIN_REGISTER, json.dumps(published_origin_payload(), ensure_ascii=False, indent=2) + "\n")
    print(
        f"BUILT: {len(rows)} Coptic Arabic reexaminations; "
        f"denominator {EXPECTED_DENOMINATOR}; {counts['positive_links']} positives; "
        f"{counts['open_candidates']} OPEN-CANDIDATE; {len(roots)} unique roots"
    )


def check() -> None:
    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
    counts = summary.get("counts") or {}
    expected = {
        "coptic_denominator": EXPECTED_DENOMINATOR,
        "named_semitic_donor_closures": EXPECTED_NAMED_SEMITIC,
        "arabic_reexaminations": EXPECTED_REEXAMINED,
        "excluded_by_published_origin": 0,
        "positive_links": len(MANUAL),
        "open_candidates": EXPECTED_REEXAMINED - len(MANUAL),
    }
    for key, value in expected.items():
        if counts.get(key) != value:
            raise AssertionError(f"الملخص: {key}={counts.get(key)!r} لا يساوي {value!r}")
    rows = load_result_rows()
    if len(rows) != EXPECTED_REEXAMINED:
        raise AssertionError(f"صفوف النتائج {len(rows)} لا تساوي 3284")
    if any(not row.get("arabic_comparison_performed") for row in rows):
        raise AssertionError("بطاقة معاد فتحها بلا مقارنة عربية")
    if any(not row.get("counted_in_denominator") for row in rows):
        raise AssertionError("قول الأصل أسقط بطاقة من المقام")
    if any(
        not form.get("fan_complete") or not form.get("dialect_door_complete")
        for row in rows for form in row.get("comparison_forms") or []
    ):
        raise AssertionError("مروحة أو باب لهجة غير مكتمل")
    greek = [row for row in rows if row.get("origin_code") == "ancient-greek"]
    if len(greek) != 3280 or any(
        not any(form.get("script") == "greek" for form in row["comparison_forms"])
        for row in greek
    ):
        raise AssertionError("الصورة اليونانية لم تفحص في كل بطاقات CCL اليونانية")
    event_roots = set()
    with EVENTS.open(encoding="utf-8") as handle:
        for line in handle:
            item = json.loads(line)
            if not item.get("all_tiers"):
                raise AssertionError(f"جذر بلا درجات حدث: {item.get('root')}")
            event_roots.add(item["root"])
    witness_roots = set()
    witness_paths = sorted((ROOT / "data").glob(WITNESS_GLOB))
    if not witness_paths:
        raise AssertionError("أجزاء سجل شواهد الجذور غائبة")
    if any(path.stat().st_size >= 100_000_000 for path in witness_paths):
        raise AssertionError("جزء من سجل الشواهد يجاوز حد الإيداع")
    for path in witness_paths:
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                item = json.loads(line)
                if item.get("max_chars") != 0 or item.get("definitions_truncated"):
                    raise AssertionError(f"شاهد مقتطع: {item.get('root')}")
                if any(match.get("definition_truncated") for match in item.get("matches") or []):
                    raise AssertionError(f"تعريف مقتطع: {item.get('root')}")
                witness_roots.add(item["root"])
    expected_roots = {root for row in rows for root in row["candidate_roots"]}
    if event_roots != expected_roots or witness_roots != expected_roots:
        raise AssertionError("فهارس الحدث أو الشواهد لا تغطي المروحة كلها")
    text = READING.read_text(encoding="utf-8")
    block = text[text.index(BLOCK_START) : text.index(BLOCK_END) + len(BLOCK_END)]
    if block.count("ARABIC-ROOT-SENSE-REREVIEW:LH-COPTIC-") != EXPECTED_REEXAMINED:
        raise AssertionError("عدد بطاقات النسخ في القراءة لا يساوي 3284")
    if block.strip() != reading_block(rows).strip():
        raise AssertionError("باب إعادة الفحص في القراءة بائت؛ أعد تشغيل المولد")
    if AUDIT.read_text(encoding="utf-8").strip() != audit_text(rows, counts).strip():
        raise AssertionError("محضر إعادة الفحص بائت؛ أعد تشغيل المولد")
    register = published_origin_payload()
    if register["counts"]["coptic_denominator"] != EXPECTED_DENOMINATOR:
        raise AssertionError("مقام سجل الأصل ليس 3301")
    if register["counts"]["excluded_by_published_origin"] != 0:
        raise AssertionError("قول الأصل ما زال يستبعد من المقام")
    print(
        f"CLEAN: denominator {EXPECTED_DENOMINATOR}; {len(rows)} compared; "
        f"3280 Greek source forms compared; {len(expected_roots)} roots fully witnessed"
    )


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.check:
        check()
    else:
        build()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
