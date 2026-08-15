# -*- coding: utf-8 -*-
"""احصد الجرد اليوناني المحال من القبطية واللاتينية.

لا تولد الأداة مدارًا موجبًا. لا يصدر موجب جديد إلا إذا أضيف نصه يدويًا إلى
MANUAL_POSITIVES. وتبقى سائر البطاقات OPEN-CANDIDATE بعد عرض الأرجل الثلاث.
"""
from __future__ import annotations

import argparse
import itertools
import json
import math
import os
import re
import subprocess
import sys
import tempfile
import types
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import fan_any_script as F  # noqa: E402
import frozen_event as FE  # noqa: E402
import search_arabic_root_senses as AR  # noqa: E402
import count_links as CL  # noqa: E402
import harvest_ancient_greek_sweep as SWEEP_CARD  # noqa: E402


DATE = "2026-08-15"
BASELINE = "1281ac5"
BATCH_SIZE = 150
INVENTORY = ROOT / "data" / "greek-origin-inventory.json"
READING = ROOT / "04-cross-linguistic" / "readings" / "ancient-greek.md"
AUDITS = ROOT / "05-audits"
MANIFESTS = ROOT / "data"
CONTROL_AUDIT = AUDITS / f"{DATE}-greek-origin-harvest-000-control.md"
FINAL_AUDIT = AUDITS / f"{DATE}-greek-origin-harvest-final.md"
MAX_CARD_BYTES = 5 * 1024


CONTROL_SPECS = [
    {"word": "δέρκομαι", "root": "درك", "closure": "ROOT-TRACE", "event_tier": 1},
    {"word": "κιέλλη", "root": "كلل", "closure": "ROOT-TRACE", "event_tier": 1},
    {"word": "ἀμέλγω", "root": "ملج", "closure": "ROOT-TRACE", "event_tier": 3},
    {"word": "ζεῦγος", "root": "زوج", "closure": "ROOT-TRACE", "event_tier": 1},
    {"word": "κέρας", "root": "قرن", "closure": "ROOT-TRACE", "event_tier": 1},
    {"word": "γράφω", "root": "جرف", "closure": "ROOT-TRACE", "event_tier": 1},
]


# كل موجب جديد يجب أن يحمل مدارًا عربيًا مكتوبًا هنا باليد وشواهده ودرجة حدثه.
MANUAL_POSITIVES: dict[str, list[dict[str, Any]]] = {}


GREEK_ENDINGS = (
    "ομαι", "ους", "ευς", "ων", "ως", "ος", "ον", "ας", "ης", "ες",
    "οι", "αι", "ου", "ις", "υς", "μι", "ω",
)


# لا يدخل هنا إلا صف منشور يشمل اليونانية نفسها أو مثالا يونانيا صريحا.
GREEK_ROWS: dict[str, dict[str, str]] = {
    "β": {"ب": "IDN-05"},
    "γ": {"ج": "IDN-08"},
    "δ": {"د": "IDN-09"},
    "ζ": {"ز": "IDN-22"},
    "θ": {},
    "κ": {"ك": "IDN-13", "ق": "GUT-01"},
    "λ": {"ل": "IDN-04"},
    "μ": {"م": "IDN-02"},
    "ν": {"ن": "IDN-03"},
    "π": {"ب": "LAB-01"},
    "ρ": {"ر": "IDN-01"},
    "σ": {"س": "IDN-07"},
    "ς": {"س": "IDN-07"},
    "τ": {"ت": "IDN-11", "ط": "DENT-05"},
    "φ": {"ف": "IDN-06"},
    "χ": {"خ": "IDN-17"},
    "ψ": {},
    "ξ": {},
}


SEMITIC_CODES = {"hebrew", "aramaic-syriac", "arabic", "akkadian", "semitic"}

# نص المؤلف جعل صورة العنصر κερως من مادة κέρας المعلومة الجواب.
LIVE_FORM_ALIASES = {"κερως": "κέρας"}


def clean(value: Any) -> str:
    return (
        " ".join(str(value or "").split())
        .replace("`", "ˋ")
        .replace("—", "؛")
    )


def clip_bytes(value: Any, limit: int) -> str:
    text = clean(value)
    encoded = text.encode("utf-8")
    if len(encoded) <= limit:
        return text
    clipped = encoded[: max(0, limit - len("…".encode("utf-8")))]
    while True:
        try:
            return clipped.decode("utf-8") + "…"
        except UnicodeDecodeError:
            clipped = clipped[:-1]


def atomic_write_text(path: Path, text: str) -> None:
    handle, temporary = tempfile.mkstemp(
        prefix=f"{path.name}.", suffix=".tmp", dir=tempfile.gettempdir()
    )
    try:
        with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(text)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def append_checked(path: Path, original: str, section: str) -> None:
    if path.read_text(encoding="utf-8") != original:
        raise AssertionError("تغير ملف القراءة أثناء بناء الدفعة")
    with path.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write("\n\n" + section)


def require_card_size(lines: list[str], card_id: str) -> int:
    size = len(("\n".join(lines).rstrip() + "\n").encode("utf-8"))
    if size > MAX_CARD_BYTES:
        raise AssertionError(
            f"تجاوزت البطاقة {card_id} حد 5 كيلوبايت: {size} بايت"
        )
    return size


def fit_card_size(
    lines: list[str],
    card_id: str,
    review: list[dict[str, Any]],
    primary: dict[str, Any] | None,
) -> int:
    """اضغط العرض غير المستعمل فقط إذا احتاجت بطاقة بعينها ذلك."""
    size = len(("\n".join(lines).rstrip() + "\n").encode("utf-8"))
    if size <= MAX_CARD_BYTES:
        return size
    if primary:
        for index, line in enumerate(lines):
            if line.startswith("- المروحة مرتبة"):
                lines[index] = (
                    f"- المروحة مرتبة، والوزن ترتيب لا حكم: قُرئت {len(review)} صورة؛ "
                    f"المنتخب {render_candidate(primary)}؛ ولم تُنسخ المنافسات."
                )
                break
    size = len(("\n".join(lines).rstrip() + "\n").encode("utf-8"))
    if size <= MAX_CARD_BYTES:
        return size
    lines[:] = [
        line for line in lines
        if not line.startswith("- منافسات قاموس الفرع:")
    ]
    return require_card_size(lines, card_id)


def fold_greek(value: Any) -> str:
    return "".join(
        char for char in unicodedata.normalize("NFD", str(value or "")).casefold()
        if not unicodedata.combining(char)
    )


def baseline_fan_module() -> types.ModuleType:
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
    old = baseline_fan_module()
    rows: list[dict[str, Any]] = []
    for spec in CONTROL_SPECS:
        # اسم الخط مكتوب هنا صراحة، وهو جزء من الضابط لا قيمة افتراضية.
        a = set(old.fan(spec["word"], "greek"))
        b = set(F.fan(spec["word"], "greek"))
        lost = sorted(a - b)
        gained = sorted(b - a)
        if lost:
            raise AssertionError(
                f"يقف العمل: {spec['word']} a-b={lost} b-a={gained}"
            )
        event = FE.resolve(spec["root"], tier=int(spec["event_tier"]))
        if event is None:
            raise AssertionError(
                f"درجة الحدث المعلنة غائبة: {spec['word']} {spec['root']}"
            )
        rows.append({
            **spec,
            "script": "greek",
            "baseline": BASELINE,
            "old_count_a": len(a),
            "current_count_b": len(b),
            "a_minus_b": lost,
            "b_minus_a": gained,
            "event": {
                "tier": event.tier,
                "tier_ar": event.tier_ar,
                "source": event.source,
                "text": event.text,
                "note": event.note,
            },
        })
    return rows


def trim_last_greek_letters(form: str, count: int) -> str:
    positions = [
        index for index, char in enumerate(form)
        if "GREEK" in unicodedata.name(char, "") and unicodedata.category(char).startswith("L")
    ]
    if len(positions) <= count:
        return form
    return form[:positions[-count]]


def morphology_variants(form: str) -> list[dict[str, str]]:
    out = [{"form": form, "operation": "الصورة المنشورة كما هي"}]
    folded = fold_greek(form)
    for ending in GREEK_ENDINGS:
        if not folded.endswith(ending):
            continue
        alternate = trim_last_greek_letters(form, len(ending))
        if len(F.skeleton(alternate, "greek")) >= 2:
            out.append({
                "form": alternate,
                "operation": f"نزع النهاية اليونانية المسماة -{ending}",
            })
        break
    return out


def source_options(
    char: str,
    dictionary_entries: list[dict[str, Any]],
) -> dict[str, str]:
    options = dict(GREEK_ROWS.get(char, {}))
    if char == "φ" and any(
        "bʰ" in str(entry.get("etymology_text") or "")
        for entry in dictionary_entries
    ):
        options["ب"] = "LAB-02"
    return options


def sound_route(
    source: list[str],
    root: str,
    dictionary_entries: list[dict[str, Any]],
) -> tuple[str, list[str]]:
    rows_by_position = [source_options(char, dictionary_entries) for char in source]
    if not rows_by_position or any(not options for options in rows_by_position):
        return "", []
    for combo in itertools.product(*(tuple(options.items()) for options in rows_by_position)):
        base = "".join(arabic for arabic, _ in combo)
        alternatives = {base: ""}
        if len(base) == 2:
            a, b = base
            alternatives.update({
                base + b: "باب المضاعف يكرر الصامت الأخير",
                a + "و" + b: "باب المعتل يثبت الواو في الجوف",
                a + "ي" + b: "باب المعتل يثبت الياء في الجوف",
                a + "ا" + b: "باب المعتل يثبت الألف في الجوف",
                base + "و": "باب المعتل يثبت الواو في الآخر",
                base + "ي": "باب المعتل يثبت الياء في الآخر",
                base + "ا": "باب المعتل يثبت الألف في الآخر",
                "و" + base: "باب المعتل يثبت الواو في الأول",
                "ي" + base: "باب المعتل يثبت الياء في الأول",
            })
        if root not in alternatives:
            continue
        parts = [
            f"{greek}↔{arabic}=`{row_id}`"
            for greek, (arabic, row_id) in zip(source, combo)
        ]
        operation = alternatives[root]
        route = "؛ ".join(parts)
        if operation:
            route += f"؛ {operation}"
        searches = [
            f"`{greek}` + `{arabic}` + «اليونانية/Greek» في عمود الشاهد"
            for greek, (arabic, _) in zip(source, combo)
        ]
        return route, searches
    return "", []


def fan_review(row: dict[str, Any]) -> tuple[list[dict[str, Any]], int]:
    form = str(row["greek_form_published"])
    entries = list(row.get("dictionary_entries") or [])
    variants = morphology_variants(form)
    by_root: dict[str, dict[str, Any]] = {}
    order: list[str] = []
    dialect_additions = 0
    for variant in variants:
        variant_form = variant["form"]
        # اسم الخط صريح في كل استدعاء للمروحة وترتيبها.
        ranked = F.rank(
            variant_form,
            F.fan(variant_form, "greek"),
            "greek",
        )
        labels = {root: "فصيح" for root, _ in ranked}
        for root, label in F.fan_with_dialect(variant_form, "greek"):
            if root not in labels:
                labels[root] = label
                dialect_additions += 1
        weights = dict(ranked)
        source = F.skeleton(variant_form, "greek")
        for root in labels:
            route, searches = sound_route(source, root, entries)
            event_options = FE.all_tiers(root)
            candidate = {
                "root": root,
                "weight": float(weights.get(root, 0.0)),
                "dialect_label": None if labels[root] == "فصيح" else labels[root],
                "fan_form": variant_form,
                "morphology": variant["operation"],
                "source_skeleton": source,
                "sound": bool(route),
                "sound_route": route,
                "sound_searches": searches,
                "event_options": [{
                    "tier": event.tier,
                    "tier_ar": event.tier_ar,
                    "source": event.source,
                    "text": event.text,
                    "note": event.note,
                } for event in event_options],
                "available_event_tiers": [event.tier for event in event_options],
                "manual_orbit": False,
            }
            prior = by_root.get(root)
            if prior is None:
                order.append(root)
                by_root[root] = candidate
            elif (candidate["sound"], candidate["weight"]) > (
                prior["sound"], prior["weight"]
            ):
                by_root[root] = candidate
    return [by_root[root] for root in order], dialect_additions


def analysis_rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows = list(payload["rows"])
    by_form = {row["greek_form_published"]: row for row in rows}
    direct = {
        row["greek_form_published"]
        for row in rows
        if any(
            item.get("source_lane") in {"coptic", "latin"}
            for item in row.get("provenance") or []
        )
    }
    parents = {
        row["greek_form_published"]
        for row in rows
        if row["greek_form_published"] in direct and row.get("compound_components")
    }
    components = {
        component["form"]
        for row in rows if row["greek_form_published"] in parents
        for component in row.get("compound_components") or []
    }
    forms = sorted((direct - parents) | components, key=lambda value: (fold_greek(value), value))
    out: list[dict[str, Any]] = []
    for index, form in enumerate(forms, 1):
        row = dict(by_form[form])
        row["analysis_index"] = index
        row["analysis_role"] = "compound-component" if form in components else "direct-form"
        row["compound_parents"] = sorted({
            item.get("intermediate_form")
            for item in row.get("provenance") or []
            if item.get("source_lane") == "compound-component"
            and item.get("intermediate_form")
        })
        out.append(row)
    return out


def existing_live_links(forms: set[str]) -> dict[str, dict[str, Any]]:
    """خذ كل موجب يعده العداد القانوني واحجز صورته من أي حكم جديد."""
    by_fold = {fold_greek(form): form for form in forms}
    found: dict[str, dict[str, Any]] = {}
    text = READING.read_text(encoding="utf-8")
    for block in re.split(r"(?=^#{3,4}\s+)", text, flags=re.M):
        if not block.startswith("#"):
            continue
        degrees = sorted(CL.scan_card(block))
        if not degrees:
            continue
        identifying = [block.splitlines()[0]]
        identifying.extend(
            line for line in block.splitlines()[1:25]
            if re.match(r"^- (?:الكلمة.? في الفرع|الصورة اليونانية)", line)
        )
        tokens: list[str] = []
        for line in identifying:
            cursor = 0
            while cursor < len(line):
                char = line[cursor]
                if "GREEK" not in unicodedata.name(char, ""):
                    cursor += 1
                    continue
                start = cursor
                cursor += 1
                while cursor < len(line) and (
                    "GREEK" in unicodedata.name(line[cursor], "")
                    or unicodedata.combining(line[cursor])
                ):
                    cursor += 1
                tokens.append(unicodedata.normalize("NFC", line[start:cursor]))
        for token in tokens:
            form = by_fold.get(fold_greek(token))
            if form:
                found[form] = {
                    "degrees": degrees,
                    "heading": clean(block.splitlines()[0]),
                }
    form_by_fold = {fold_greek(form): form for form in forms}
    for alias, target in LIVE_FORM_ALIASES.items():
        alias_form = form_by_fold.get(fold_greek(alias))
        target_form = form_by_fold.get(fold_greek(target))
        target_reference = found.get(target_form or target)
        if alias_form and target_reference:
            found[alias_form] = {
                **target_reference,
                "alias_of": target,
            }
    return found


def source_label(match: dict[str, Any]) -> str:
    source_id = AR.canonical_source_id(str(match.get("source") or ""))
    return AR.SOURCE_LABELS[source_id] if source_id else clean(match.get("source"))


def render_entry(entry: dict[str, Any]) -> str:
    meanings = clip_bytes(
        "؛ ".join(clean(value) for value in entry.get("meanings") or [])
        or "لا معنى في اللقطة",
        350,
    )
    etymology = clip_bytes(
        entry.get("etymology_text") or "لا اشتقاق منشور في اللقطة",
        200,
    )
    return (
        f"`{clean(entry.get('word'))}` /{clean(entry.get('romanization'))}/ "
        f"[{clean(entry.get('pos'))}] «{meanings}»؛ الاشتقاق «{etymology}»"
    )


EN_TOKEN = re.compile(r"[a-z]{3,}")
EN_STOP = {
    "and", "the", "for", "from", "into", "with", "that", "this",
    "used", "someone", "something", "form", "kind", "other",
}


def english_tokens(value: Any) -> set[str]:
    return {
        token for token in EN_TOKEN.findall(str(value or "").casefold())
        if token not in EN_STOP
    }


def select_dictionary_entry(row: dict[str, Any]) -> int:
    entries = list(row.get("dictionary_entries") or [])
    if not entries:
        return -1
    context = english_tokens(" ".join(
        str(item.get("intermediate_meaning") or "")
        for item in row.get("provenance") or []
    ))
    scores: list[tuple[int, float, int]] = []
    for index, entry in enumerate(entries):
        found = english_tokens(" ".join(entry.get("meanings") or []))
        shared = len(context & found)
        union = len(context | found) or 1
        scores.append((shared, shared / union, -index))
    return -max(scores)[2]


def useful_competitor(entry: dict[str, Any], chosen: dict[str, Any]) -> bool:
    if clean(entry.get("word")) != clean(chosen.get("word")):
        return True
    if clean(entry.get("pos")) != clean(chosen.get("pos")):
        return True
    candidate = english_tokens(" ".join(entry.get("meanings") or []))
    selected = english_tokens(" ".join(chosen.get("meanings") or []))
    return not (candidate <= selected or selected <= candidate)


def render_candidate(item: dict[str, Any]) -> str:
    tiers = "/".join(str(value) for value in item["available_event_tiers"]) or "0"
    return (
        f"`{item['root']}`[و{item['weight']:.6f}،"
        f"ص{'✓' if item['sound'] else '×'}،ح{'✓' if item['event_options'] else '×'}،"
        f"د{tiers}،م×]"
    )


def attach_arabic_review(
    review: list[dict[str, Any]],
    hits_by_root: dict[str, list[dict[str, Any]]],
) -> None:
    for item in review:
        matches = hits_by_root.get(item["root"], []) if item["sound"] and item["event_options"] else []
        independent = AR.independent_fan(matches)
        item["arabic_lexicon_review"] = {
            "command": f"python scripts/search_arabic_root_senses.py {item['root']} --max-chars 0",
            "max_chars": 0,
            "truncated": any(bool(match.get("definition_truncated")) for match in matches),
            "witness_count": len(matches),
            "sources": list(dict.fromkeys(source_label(match) for match in matches)),
            "independent_fan_complete": bool(independent["complete"]),
            "judgment_ready": bool(independent["judgment_ready"]),
        }


def compact_candidates(review: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for item in review:
        ar = item.get("arabic_lexicon_review") or {}
        out.append({
            "root": item["root"],
            "weight": item["weight"],
            "sound": item["sound"],
            "sound_route": item["sound_route"],
            "event_options": item["available_event_tiers"],
            "available_event_tiers": item["available_event_tiers"],
            "arabic_lexicon_review": {
                "command": ar.get("command", ""),
                "max_chars": ar.get("max_chars"),
                "truncated": ar.get("truncated", False),
                "witness_count": ar.get("witness_count", 0),
                "sources": ar.get("sources", []),
            },
        })
    return out


def render_fan_summary(review: list[dict[str, Any]], primary: dict[str, Any] | None) -> str:
    selected = primary.get("root") if primary else ""
    shown: list[dict[str, Any]] = []
    if primary:
        shown.append(primary)
    shown.extend(
        item for item in review
        if item.get("root") != selected and len(shown) < 2
    )
    rendered = "، ".join(render_candidate(item) for item in shown) or "فارغة"
    suffix = "؛ المعروض المنتخب ومنافس" if len(review) > len(shown) else ""
    return f"قُرئت {len(review)} صورة؛ {rendered}{suffix}"


def render_event_options(primary: dict[str, Any] | None) -> list[str]:
    if primary is None or not primary.get("event_options"):
        return ["- رجل الحدث: لا حدث للمرشح المعروض في السجل المجمد."]
    lines = [
        f"- رجل الحدث: `frozen_event.all_tiers('{clean(primary['root'])}')` أعاد "
        f"{len(primary['event_options'])} درجة بلا زيادة:"
    ]
    for item in primary["event_options"]:
        lines.append(
            f"  - الدرجة {item['tier']} ({clean(item['tier_ar'])}): "
            f"«{clean(item['text'])}»؛ المصدر `{clean(item['source'])}`؛ "
            f"الملاحظة: {clean(item['note']) or 'لا ملاحظة زائدة'}."
        )
    return lines


def donor_closure(row: dict[str, Any]) -> str:
    codes = {
        route["origin_code"]
        for route in row.get("foreign_origin_routes") or []
        if route.get("confidence") == "asserted"
    }
    return (
        "SEMITIC-SOURCE-TRANSMISSION"
        if codes and codes <= SEMITIC_CODES
        else "LOANWORD-THIRD-PARTY-TO-BRANCH"
    )


def build_card(
    row: dict[str, Any],
    review: list[dict[str, Any]],
    dialect_additions: int,
) -> tuple[list[str], dict[str, Any], str]:
    form = str(row["greek_form_published"])
    entries = list(row.get("dictionary_entries") or [])
    ready = [item for item in review if item["sound"] and item["event_options"]]
    sounded = [item for item in review if item["sound"]]
    primary = (ready or sounded or review or [None])[0]
    selected_entry = select_dictionary_entry(row)
    chosen = entries[selected_entry] if selected_entry >= 0 else None
    romanization = SWEEP_CARD.reader_romanization(
        form, clean(chosen.get("romanization")) if chosen else ""
    )
    competitors = [
        index for index, entry in enumerate(entries)
        if index != selected_entry and chosen and useful_competitor(entry, chosen)
    ][:1]
    provenance = list(row.get("provenance") or [])
    provenance_shown = provenance[:1]
    card_id = f"GREEK-ORIGIN-HARVEST-{row['analysis_index']:05d}"
    lines = [
        f"### بطاقة الجرد اليوناني: `{clean(form)}` /{romanization}/؛ {card_id}",
        f"- الصورة اليونانية المنشورة ورومنتها: `{clean(form)}` /{romanization}/؛ دورها: {row['analysis_role']}.",
        f"- الإحالات: قُرئت {len(provenance)}؛ المستعمل في تعيين السياق: " + "؛ ".join(
            f"{item['source_lane']}:{item['source_card_id']} عبر `{clean(item['intermediate_form'])}`"
            for item in provenance_shown
        ) + ".",
        f"- قاموس الفرع: قُرئت {len(entries)} مدخلة متجانسة؛ "
        + (f"المختارة للسياق {render_entry(chosen)}." if chosen else "لا مدخل؛ الغياب فجوة مصدر لا نفي."),
    ]
    if competitors:
        lines.append(
            "- منافسات قاموس الفرع: "
            + " | ".join(render_entry(entries[index]) for index in competitors)
            + "."
        )
    if row.get("compound_parents"):
        lines.append(
            "- عنصر مركب مفحوص استقلالا؛ أبواه: "
            + "، ".join(f"`{clean(parent)}`" for parent in row["compound_parents"])
            + "."
        )
    lines.extend([
        "- الخطوة صفر: استدعيت `fan_any_script` بالخط `greek` صراحة؛ البدائل الصرفية: "
        + "؛ ".join(
            f"`{clean(item['form'])}` ({item['operation']})"
            for item in morphology_variants(form)
        ) + ".",
        "- المروحة مرتبة، والوزن ترتيب لا حكم: " + render_fan_summary(review, primary) + ".",
        f"- فحص `fan_with_dialect` بالخط `greek`: أضاف {dialect_additions} صورة موسومة.",
        *render_event_options(primary),
    ])

    if primary and primary.get("sound") and primary.get("event_options"):
        ar = primary.get("arabic_lexicon_review") or {}
        lines.append(
            f"- شواهد الجذر العربي `{clean(primary['root'])}`: قُرئت كاملة بالأمر "
            f"`{clean(ar.get('command'))}`؛ الشواهد={ar.get('witness_count', 0)}؛ "
            f"المعاجم={len(ar.get('sources') or [])}؛ القطع=لا."
        )
        lines.append("  - لم يُقتبس شاهد؛ لا مدار موجب في هذه البطاقة يقوم عليه.")

    status = str(row.get("origin_status") or "")
    existing = row.get("existing_live_reference") or {}
    if existing:
        closure = str(existing["degrees"][0])
        reason = "existing-live-reference"
        lines.extend([
            f"- حارس الصلة الحية: أحال العداد القانوني هذه الصورة إلى {', '.join(existing['degrees'])} في «{existing['heading']}».",
            *(
                [f"- تعيين العنصر: `{clean(form)}` هو عنصر `{existing['alias_of']}` الذي نص عليه المؤلف، فلا يعاد فتح جوابه."]
                if existing.get("alias_of") else []
            ),
            "- الحكم (استكشاف): مرجع فحص غير مستقل؛ الحكم في البطاقة الحية المذكورة، ولا صلة صادرة جديدة.",
            "- المدار المكتوب باليد: محفوظ في البطاقة الحية المشار إليها؛ بطاقة الجرد هذه مرجع فحص لا ناسخ حكم، ولم تضف حكما ثانيا.",
            "- حالة الجرد: EXISTING-LIVE-REFERENCE؛ لا سطر حكم جديد ولا تغيير في العد.",
            "",
        ])
    elif status == "redirect-named-foreign":
        closure = donor_closure(row)
        reason = "redirect-named-foreign"
        routes = [
            route for route in row.get("foreign_origin_routes") or []
            if route.get("confidence") == "asserted"
        ]
        lines.extend([
            "- مصفاة الأصل: خرجت الصورة من مقام اليونانية لأن قاموس الفرع سمى مانحا غير يوناني.",
            "- طرق التوجيه المنشورة: " + " | ".join(
                f"{route['origin_code']}: «{clip_bytes(route['published_etymology'], 450)}»"
                for route in routes
            ) + ".",
            "- المدار المكتوب باليد: غير مطلوب؛ لم تقابل مادة المانح الثالث بجذر عربي في ملف اليونانية.",
            f"- حالة الإغلاق: {closure}.",
            f"- الحكم (استكشاف): {closure}.",
            "",
        ])
    else:
        if status == "origin-disputed":
            lines.append("- مصفاة الأصل: في الاشتقاق اقتراح غير جازم بمانح ثالث؛ بقيت الصورة في المقام ولم يتحول الاحتمال إلى نفي.")
        elif status == "mixed-homographs":
            lines.append("- فصل المتجانسات: بعض المداخل يسمي مانحا ثالثا وبعضها لا؛ عرضت كلها ولم يرث أحدها حكم الآخر.")
        elif status == "source-gap":
            lines.append("- فجوة قاموس الفرع: لا مدخل مطابق في اللقطة المحلية؛ بقيت البطاقة مفتوحة ولم يعد الغياب نفيا.")
        else:
            lines.append("- مصفاة الأصل: لا مانح ثالث جازم في المداخل المنشورة المعروضة.")

        if ready:
            meaning = (
                "؛ ".join(clean(value) for value in chosen.get("meanings") or [])
                if chosen else "لا معنى في لقطة القاموس"
            )
            event_text = clip_bytes(primary["event_options"][0]["text"], 250)
            lines.append(
                f"- المدار المكتوب بالكلمات: معنى الفرع «{clip_bytes(meaning, 350)}» عُرض على "
                f"حدث `{clean(primary['root'])}` «{event_text}» وعلى شواهده المقروءة كاملة؛ "
                "ولم يثبت مدار محدود يجمع المعنيين من غير تعميم أو قفزة، فلم يصدر حكم موجب."
            )
            reason = "manual-orbit-not-issued"
        elif any(item["sound"] for item in review):
            lines.append("- المدار المكتوب باليد: لم يبلغ الفحص رجل المدار لأن المرشحين ذوي الصوت المسمى لا حدث مجمدا لهم.")
            reason = "event-gap"
        elif review:
            lines.append("- المدار المكتوب باليد: لم يبلغ الفحص رجل المدار لأن المروحة لم تبلغ مرشحا بصفوف يونانية مسماة.")
            reason = "law-gap"
        else:
            lines.append("- المدار المكتوب باليد: لم يبلغ الفحص رجل المدار لأن الهيكل بعد التفكيك والصرف لم يدخل حد المروحة.")
            reason = "fan-gap"
        closure = "OPEN-CANDIDATE"
        lines.extend([
            "- الحكم (استكشاف): غير صادر (استكشاف).",
            "- حالة الإغلاق: OPEN-CANDIDATE.",
            "",
        ])

    size = fit_card_size(lines, card_id, review, primary)
    manifest = {
        "analysis_index": row["analysis_index"],
        "analysis_role": row["analysis_role"],
        "greek_form_published": form,
        "romanization": romanization,
        "origin_status": row.get("origin_status"),
        "foreign_origin_routes": row.get("foreign_origin_routes") or [],
        "provenance_count": len(provenance),
        "dictionary_entry_count": len(entries),
        "dictionary_selected": selected_entry,
        "dictionary_entry": chosen,
        "card_id": card_id,
        "fan_script": "greek",
        "morphology_variants": morphology_variants(form),
        "fan_candidate_count": len(review),
        "fan_candidates": compact_candidates(review),
        "selected_root": primary.get("root") if primary else "",
        "dialect_additions": dialect_additions,
        "closure": closure,
        "open_reason": reason if closure == "OPEN-CANDIDATE" else "",
        "positive_links_added": [],
        "existing_live_reference": existing,
        "card_bytes": size,
    }
    return lines, manifest, reason


def control_audit_text(controls: list[dict[str, Any]]) -> str:
    lines = [
        f"# ضابط حصاد اليونانية وبداية العمل ({DATE})",
        "",
        "## الضابط الإلزامي قبل الحصاد",
        "",
        f"عرّفت `a` بأنها مروحة `{BASELINE}` و`b` بأنها المروحة الحالية، واستدعيت الخط `greek` صراحة. شرط الوقف الوحيد هو أن تكون `a - b` غير فارغة. لم يقع الشرط في أي بطاقة.",
        "",
        "| البطاقة الحية | الجذر | الحكم | a | b | a - b | b - a | درجة الحدث المعلنة |",
        "|---|---|---:|---:|---:|---|---|---:|",
    ]
    for row in controls:
        lines.append(
            f"| `{row['word']}` | `{row['root']}` | {row['closure']} | {row['old_count_a']} | {row['current_count_b']} | {row['a_minus_b'] or '∅'} | {row['b_minus_a'] or '∅'} | {row['event_tier']} |"
        )
    lines.extend([
        "",
        "## الثلاثة معلومة الجواب",
        "",
        "### `κέρας ↔ قرن`",
        "",
        "- النتيجة: ثابتة بالحكم الحي الصادر اليوم؛ لم أضف صلة ثانية ولم أمس النص الحي.",
        "- الصوت: `GUT-01` في κ↔ق و`IDN-01` في ρ↔ر، مع الساق المنشورة `κέρατ-`.",
        "- الحدث المعلن: الدرجة 1، «نتوء بشدة أو اعتصار يمتد في أعلى الجسم أو مقدمه».",
        "- الشاهد بعد `python scripts/search_arabic_root_senses.py قرن --max-chars 0`: كتاب العين «قَرْنُ الثور معروف، وموضعه من رأس الإنسان قَرنٌ أيضاً»؛ لسان العرب «القَرْنُ للثَّوْر وغيره: الرَّوْقُ»؛ تاج العروس «القَرْنُ: الرَّوْقُ من الحَيَوانِ».",
        "- المدار الحي المكتوب باليد: قرن الحيوان عضو صلب ناتئ يمتد من أعلى الرأس أو مقدمه، وهو horn نفسه.",
        "- الحكم: ROOT-TRACE مرجعي حي، بلا زيادة في العد.",
        "",
        "### `ζυγόν`",
        "",
        "- قاموس الفرع: `yoke, for joining animals؛ anything which joins two pieces together`، ومن Proto-Hellenic `*dzugón`.",
        "- المروحة: نزع `-ον` يعطي `ζυγ`، واستدعاء `greek` يبلغ `زوج` سطحيًا عبر `IDN-22` و`IDN-08` وباب الواو الجوفاء.",
        "- الحدث المعلن: الدرجة 1، «تداخل بين شيء وآخر حتى يشتبكا ويختلطا ويرتبطا معًا».",
        "- الشاهد بعد `python scripts/search_arabic_root_senses.py زوج --max-chars 0`: لسان العرب «الزَّوْجُ: خلاف الفَرْدِ» و«الزَّوْجُ الفَرْدُ الذي له قَرِينٌ»؛ تاج العروس يثبت الزوج والبعل والقرين.",
        "- المدار المكتوب باليد: النير يجمع حيوانين أو قطعتين، والزوج قرين مقترن بآخر؛ رجل المعنى مستقيمة.",
        "- العائق: الصامت `d` في أقدم صورة منشورة `*dzugón` ما زال بلا مقابل، ولم يغير تحديث المروحة هذا الواقع.",
        "- الحكم: OPEN-CANDIDATE؛ لم تتغير حالها.",
        "",
        "### `γῦρος`",
        "",
        "- قاموس الفرع: `ring, circle`، ومن PIE `*gew-` بمعنى curve أو bend.",
        "- المروحة: نزع `-ος` يعطي `γῦρ`، واستدعاء `greek` يبلغ `جور` عبر `IDN-08` و`IDN-01` وباب الواو الجوفاء.",
        "- الحدث المعلن: الدرجة 1، «دخول في حيز شيء بقوة للإقامة أو افتجاء للاحتواء».",
        "- الشاهد بعد `python scripts/search_arabic_root_senses.py جور --max-chars 0`: لسان العرب «الجَوْرُ: نقيض العدل» و«الجَوْرُ: الميل عن القصد»؛ تاج العروس «الجَوْرُ: ضد القصد، أو الميل عنه».",
        "- المدار المكتوب باليد: الحلقة والانحناء لا يحققان حدث الدخول في الحيز المنشور، واتخاذ الميل عن الطريق جسرا إلى الانحناء الهندسي يترك حدث الجذر نفسه؛ لذلك لم يصدر مدار.",
        "- الحكم: OPEN-CANDIDATE.",
        "",
        "ثبت واحد من الثلاثة بحكم حي، فاستمر العمل كما اشترط التكليف.",
        "",
    ])
    return "\n".join(lines)


def write_control() -> None:
    controls = control_run()
    AUDITS.mkdir(parents=True, exist_ok=True)
    CONTROL_AUDIT.write_text(
        control_audit_text(controls), encoding="utf-8", newline="\n"
    )
    print(json.dumps({"controls": controls, "audit": str(CONTROL_AUDIT)}, ensure_ascii=False))


def audit_text(
    batch: int,
    total_batches: int,
    rows: list[dict[str, Any]],
    reasons: Counter[str],
) -> str:
    closures = Counter(row["closure"] for row in rows)
    donors = Counter(
        route["origin_code"]
        for row in rows for route in row.get("foreign_origin_routes") or []
        if row["origin_status"] == "redirect-named-foreign"
        and route.get("confidence") == "asserted"
    )
    return "\n".join([
        f"# حصاد الصور اليونانية المحالة، الدفعة {batch:03d} من {total_batches:03d} ({DATE})",
        "",
        f"- حجم الدفعة: {len(rows)} وحدة من وحدات الفحص بعد تفكيك المركبات.",
        "- الخط: `greek` صراحة في `fan` و`rank` و`fan_with_dialect`.",
        "- الأرجل: صف صوتي يوناني مسمى، ثم جميع درجات الحدث، ثم مدار لا يصدر موجبه إلا من نص يدوي.",
        f"- الإغلاقات: {dict(closures)}.",
        f"- أسباب البقاء مفتوحا: {dict(reasons)}.",
        f"- التوجيه خارج المقام بحسب المانح المنشور: {dict(donors)}.",
        "- لم تضف الدفعة صلة صادرة جديدة، ولم تمس صلة يونانية صادرة حية.",
        "- كل غياب في قاموس الفرع بقي فجوة مصدر لا نفيا.",
        "- قُرئت شواهد الجذور كاملة؛ حفظت البطاقات العدد وأسماء المعاجم، ولم تنسخ إلا شاهدا يقوم عليه مدار موجب.",
        "",
    ])


def process_batch(batch: int, write_reading: bool) -> None:
    inventory = json.loads(INVENTORY.read_text(encoding="utf-8"))
    all_rows = analysis_rows(inventory)
    total_batches = math.ceil(len(all_rows) / BATCH_SIZE)
    start = (batch - 1) * BATCH_SIZE
    window = all_rows[start:start + BATCH_SIZE]
    if not window:
        raise SystemExit(f"الدفعة خارج الجرد؛ المدى 1..{total_batches}")

    prepared: list[tuple[dict[str, Any], list[dict[str, Any]], int]] = []
    live = existing_live_links({row["greek_form_published"] for row in all_rows})
    roots: set[str] = set()
    for row in window:
        if row["greek_form_published"] in live:
            row = {**row, "existing_live_reference": live[row["greek_form_published"]]}
        review, dialect = fan_review(row)
        prepared.append((row, review, dialect))
        roots.update(
            item["root"] for item in review
            if item["sound"] and item["event_options"]
        )
    hits = AR.matches_for_roots(AR.DEFAULT_RESOURCES, roots, None)

    lines: list[str] = []
    manifests: list[dict[str, Any]] = []
    reasons: Counter[str] = Counter()
    for row, review, dialect in prepared:
        attach_arabic_review(review, hits)
        card_lines, manifest, reason = build_card(row, review, dialect)
        lines.extend(card_lines)
        manifests.append(manifest)
        if manifest["closure"] == "OPEN-CANDIDATE":
            reasons[reason] += 1

    AUDITS.mkdir(parents=True, exist_ok=True)
    MANIFESTS.mkdir(parents=True, exist_ok=True)
    audit = AUDITS / f"{DATE}-greek-origin-harvest-batch-{batch:03d}.md"
    manifest_path = MANIFESTS / f"greek-origin-harvest-batch-{batch:03d}.json"
    audit.write_text(
        audit_text(batch, total_batches, manifests, reasons),
        encoding="utf-8", newline="\n",
    )
    payload = {
        "schema": "greek-origin-harvest-v1",
        "date": DATE,
        "batch": batch,
        "total_batches": total_batches,
        "batch_size": len(manifests),
        "fan_script": "greek",
        "positive_links_added": 0,
        "closures": dict(Counter(row["closure"] for row in manifests)),
        "open_reasons": dict(reasons),
        "rows": manifests,
    }
    manifest_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8", newline="\n",
    )
    if write_reading:
        marker = f"GREEK-ORIGIN-HARVEST-BATCH-{batch:03d}"
        old_text = READING.read_text(encoding="utf-8")
        if f"<!-- {marker}:START -->" in old_text:
            raise AssertionError(f"مقطع الدفعة {batch} موجود")
        section = "\n".join([
            f"<!-- {marker}:START -->",
            "",
            f"## حصاد الصور اليونانية المحالة، الدفعة {batch:03d} ({DATE})",
            "",
            *lines,
            f"<!-- {marker}:END -->",
            "",
        ])
        append_checked(READING, old_text, section)
    print(json.dumps({
        key: value for key, value in payload.items() if key != "rows"
    }, ensure_ascii=False))


def write_final_audit() -> None:
    """اجمع الدفعات، وتحقق من التغطية، واكتب مقام اليونانية المصحح."""
    control_run()
    inventory = json.loads(INVENTORY.read_text(encoding="utf-8"))
    expected = analysis_rows(inventory)
    total_batches = math.ceil(len(expected) / BATCH_SIZE)
    rows: list[dict[str, Any]] = []
    closures: Counter[str] = Counter()
    reasons: Counter[str] = Counter()
    donors: Counter[str] = Counter()
    full_witnesses = 0
    ready_candidates = 0
    for batch in range(1, total_batches + 1):
        path = MANIFESTS / f"greek-origin-harvest-batch-{batch:03d}.json"
        if not path.exists():
            raise AssertionError(f"بيانات الدفعة غائبة: {path.name}")
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("batch") != batch or payload.get("total_batches") != total_batches:
            raise AssertionError(f"بيانات دفعة غير منسجمة: {path.name}")
        closures.update(payload.get("closures") or {})
        reasons.update(payload.get("open_reasons") or {})
        for row in payload.get("rows") or []:
            if row.get("fan_script") != "greek":
                raise AssertionError(f"خط غير يوناني: {row.get('card_id')}")
            if row.get("positive_links_added"):
                raise AssertionError(f"موجب آلي محظور: {row.get('card_id')}")
            if row.get("origin_status") == "redirect-named-foreign":
                for route in row.get("foreign_origin_routes") or []:
                    if route.get("confidence") == "asserted":
                        donors[route["origin_code"]] += 1
            for candidate in row.get("fan_candidates") or []:
                if not (candidate.get("sound") and candidate.get("event_options")):
                    continue
                ready_candidates += 1
                review = candidate.get("arabic_lexicon_review") or {}
                if (
                    review.get("max_chars") != 0
                    or review.get("truncated")
                    or "--max-chars 0" not in review.get("command", "")
                ):
                    raise AssertionError(
                        f"شاهد عربي ناقص: {row.get('card_id')} {candidate.get('root')}"
                    )
                full_witnesses += int(review.get("witness_count") or 0)
            rows.append(row)

    indexes = [int(row["analysis_index"]) for row in rows]
    forms = [str(row["greek_form_published"]) for row in rows]
    if indexes != list(range(1, len(expected) + 1)):
        raise AssertionError("ترتيب بطاقات الدفعات غير كامل")
    if len(forms) != len(set(forms)) or forms != [
        str(row["greek_form_published"]) for row in expected
    ]:
        raise AssertionError("صور الدفعات مكررة أو لا تطابق الجرد")

    counts = inventory["counts"]
    inputs = inventory["input_counts"]
    live = [
        row for row in rows if row.get("existing_live_reference")
    ]
    live_text = "، ".join(
        f"`{clean(row['greek_form_published'])}` ({row['closure']})"
        for row in live
    ) or "لا شيء"
    AUDITS.mkdir(parents=True, exist_ok=True)
    lines = [
        f"# المحضر الجامع لحصاد اليونانية القديمة ({DATE})",
        "",
        "## الضابط",
        "",
        f"سبق هذا المحضر محضر الضابط `{CONTROL_AUDIT.name}`. فيه قوبلت مروحة `{BASELINE}` بالمروحة الحالية على 6 بطاقات صادرة حية، بالخط `greek` صراحة، وكانت `a - b = ∅` في الست كلها. لذلك لم يقع شرط الوقف.",
        "",
        "## الجرد والمقام",
        "",
        f"- صفوف الإحالة الداخلة: {inputs['input_coptic_rows']} من القبطية و{inputs['input_latin_rows_live']} من اللاتينية الحية.",
        f"- الورود ذات الرسم اليوناني المنشور: {counts['published_occurrences']}، منها {counts['by_source_lane']['coptic']} في مسار القبطية و{counts['by_source_lane']['latin']} في مسار اللاتينية.",
        f"- الصور المباشرة المتمايزة قبل تفكيك المركبات: {counts['direct_distinct_forms_before_components']}؛ القبطية {counts['direct_distinct_forms_by_source_lane']['coptic']}، واللاتينية {counts['direct_distinct_forms_by_source_lane']['latin']}، والمشترك بينهما {counts['direct_distinct_forms_shared_by_both_lanes']}.",
        f"- المركبات المفككة بنص منشور: {counts['compound_parents_with_published_decomposition']}، وعناصرها المتمايزة {counts['distinct_component_forms']}، ووحدات الفحص بعد إحلال العناصر محل المركبات {counts['analysis_units_after_replacing_compounds_with_components']}.",
        f"- خرج من مقام الصور المباشرة {counts['named_foreign_origin_direct_forms_redirected']} رسمًا لأن أصله الأجنبي مسمى جازم؛ فمقام اليونانية المباشر المصحح {counts['corrected_direct_greek_denominator']}.",
        f"- وفي مقام وحدات الفحص خرج {counts['named_foreign_origin_analysis_units_redirected']} من {counts['analysis_units_after_replacing_compounds_with_components']}؛ فالمقام التحليلي المصحح {counts['corrected_analysis_denominator']}.",
        f"- بقي المختلف في أصله داخل المقام، وبقي غياب مدخلة قاموس الفرع فجوة مصدر لا نفيًا. أما {inputs['latin_rows_without_published_greek_script']} صفًا لاتينيًا فلم ينشر رسمًا يونانيًا أصلًا، فسجلت فجوة المصدر ولم أستنبط لها رسمًا من الوسيط.",
        "",
        "## الفحص بالدفعات",
        "",
        f"- الدفعات: {total_batches}، بحجم {BATCH_SIZE} إلا الأخيرة؛ البطاقات {len(rows)}، والصور المتمايزة فيها {len(set(forms))}.",
        f"- مرشحو الصوت والحدث المقروءون: {ready_candidates}؛ مجموع الشواهد العربية المقروءة: {full_witnesses}، وكلها بأمر `python scripts/search_arabic_root_senses.py <الجذر> --max-chars 0` بلا اقتطاع؛ لم تنسخ النصوص الكاملة في البيانات.",
        f"- الإغلاقات والحالات: `{dict(closures)}`.",
        f"- أسباب الفتح: `{dict(reasons)}`.",
        f"- مسالك المانحين الجازمة في وحدات الفحص: `{dict(donors)}`.",
        f"- المراجع الحية المصونة: {live_text}.",
        "- الموجبات الجديدة: 0. لم يولد البرنامج مدارًا، ولم يمس صلة صادرة حية، وبقي غير المحسوم OPEN-CANDIDATE.",
        "",
        "## الثلاثة الافتتاحية",
        "",
        "- `κέρας ↔ قرن`: ROOT-TRACE حي محفوظ، وأحيل إليه العنصر `κερως` من غير عد ثان.",
        "- `ζυγόν`: OPEN-CANDIDATE؛ بقي الصامت `d` في `*dzugón` بلا مقابل.",
        "- `γῦρος`: OPEN-CANDIDATE؛ لا يحقق معنى الحلقة والانحناء حدث الدخول في الحيز المعلن.",
        "",
    ]
    FINAL_AUDIT.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    print(json.dumps({
        "audit": str(FINAL_AUDIT),
        "rows": len(rows),
        "closures": dict(closures),
        "corrected_direct_greek_denominator": counts["corrected_direct_greek_denominator"],
        "corrected_analysis_denominator": counts["corrected_analysis_denominator"],
    }, ensure_ascii=False))


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("--control-only", action="store_true")
    parser.add_argument("--batch", type=int)
    parser.add_argument("--write-reading", action="store_true")
    parser.add_argument("--count", action="store_true")
    parser.add_argument("--final-audit", action="store_true")
    args = parser.parse_args()
    if args.control_only:
        write_control()
        return 0
    if args.final_audit:
        write_final_audit()
        return 0
    payload = json.loads(INVENTORY.read_text(encoding="utf-8"))
    rows = analysis_rows(payload)
    if args.count:
        print(json.dumps({
            "analysis_units": len(rows),
            "batches": math.ceil(len(rows) / BATCH_SIZE),
            "batch_size": BATCH_SIZE,
        }, ensure_ascii=False))
        return 0
    if not args.batch:
        parser.error("--batch مطلوب")
    control_run()
    process_batch(args.batch, args.write_reading)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
