# -*- coding: utf-8 -*-
"""حصاد الأصول اليونانية المنشورة في سجلي القبطي واللاتيني.

الترتيب هنا مقصود: الأصل اليوناني المنشور هو الصورة التي تدخل المروحة، لا
صورته اللاتينية أو القبطية. وإذا صرح قاموس اليونانية بتركيب، تسجل عناصره
صورا مستقلة وتفحص كل صورة بأرجل الصوت والحدث والمعنى نفسها.

الاستعمال:
  python scripts/harvest_ancient_greek_directed_sources.py --prepare
  python scripts/harvest_ancient_greek_directed_sources.py --batches 1 2 3
  python scripts/harvest_ancient_greek_directed_sources.py --finalize
  python scripts/harvest_ancient_greek_directed_sources.py --check
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import bulk_phonetic_sweep as BULK  # noqa: E402
import fan_northern_word as ROOT_FAN  # noqa: E402
import harvest_ancient_greek_sweep as BASE  # noqa: E402


DATE = "2026-08-15"
BATCH_SIZE = 150
MAX_COMPONENT_DEPTH = 3
QUEUE = ROOT / "data" / "ancient-greek-directed-source-queue.json"
READING = ROOT / "04-cross-linguistic" / "readings" / "ancient-greek.md"
COPTIC = ROOT / "data" / "non-coptic-borrowings-in-coptic.json"
LATIN = ROOT / "data" / "greek-borrowings-in-latin.json"
SWEEP = ROOT / "04-cross-linguistic" / "exploration" / "phonetic-sweep-ancient_greek.json"
PREP_AUDIT = ROOT / "05-audits" / f"{DATE}-ancient-greek-directed-source-preparation.md"
FINAL_AUDIT = ROOT / "05-audits" / f"{DATE}-ancient-greek-directed-source-final.md"

# تفصل Unicode الحروف القبطية القديمة في U+03E2..U+03EF داخل الكتلة نفسها.
# لا تدخل تلك النافذة في ملتقط الأصل اليوناني.
GREEK_TOKEN = re.compile(r"[\u0370-\u03e1\u03f0-\u03ff\u1f00-\u1fff]+")
COMPARISON_CLAUSE = re.compile(
    r"(?i)\b(?:compare|cognate|see also|related|ultimately)\b"
)
NAMED_SEMITIC_DONOR = re.compile(
    r"(?is)\bfrom\s+(?:the\s+|a\s+|an\s+)?"
    r"(?:Biblical\s+Hebrew|Hebrew|Arabic|Aramaic|Classical\s+Syriac|Syriac|"
    r"Akkadian|Phoenician|Punic|Canaanite|Ugaritic|Ge['’]ez|Sabaic|"
    r"Old\s+South\s+Arabian|Proto-West\s+Semitic|Proto-Semitic)\b"
)
UNCERTAIN_ROUTE_OPENING = re.compile(
    r"(?is)^\s*(?:uncertain\b|possibly\b|perhaps\b|the\s+word\s+may\b|"
    r"since\s+long\b|borrowing\b[^.;]{0,120}\bdoubtful\b|"
    r"loaned\b[^.;]{0,120}\bpossibly\b)"
)
KERA_KEYS = {"κερασ", "κερωσ"}


def clean(value: Any) -> str:
    return BASE.clean(value)


def nfc(value: Any) -> str:
    return unicodedata.normalize("NFC", str(value or "").strip())


def greek_key(value: Any) -> str:
    source = unicodedata.normalize("NFD", nfc(value).casefold()).replace("ς", "σ")
    return "".join(char for char in source if not unicodedata.combining(char))


def greek_tokens(value: Any) -> list[str]:
    return [nfc(token) for token in GREEK_TOKEN.findall(str(value or ""))]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def compact_entry(entry: dict[str, Any]) -> dict[str, str]:
    return {
        "word": clean(entry.get("word")),
        "read": clean(entry.get("read")),
        "pos": clean(entry.get("pos")),
        "en": clean(entry.get("en")),
        "etym": clean(entry.get("etym")),
    }


def provenance_key(row: dict[str, Any]) -> str:
    return json.dumps(row, ensure_ascii=False, sort_keys=True)


def add_provenance(
    store: dict[str, list[dict[str, Any]]],
    order: list[str],
    word: str,
    provenance: dict[str, Any],
) -> None:
    word = nfc(word)
    if not word:
        return
    if word not in store:
        store[word] = []
        order.append(word)
    key = provenance_key(provenance)
    if all(provenance_key(old) != key for old in store[word]):
        store[word].append(provenance)


def source_inventory() -> tuple[dict[str, list[dict[str, Any]]], list[str], list[dict[str, Any]], dict[str, int]]:
    provenance: dict[str, list[dict[str, Any]]] = {}
    order: list[str] = []
    row_gaps: list[dict[str, Any]] = []

    coptic_rows = json.loads(COPTIC.read_text(encoding="utf-8")).get("rows", [])
    coptic_rows = [row for row in coptic_rows if row.get("origin_code") == "ancient-greek"]
    coptic_rows.sort(key=lambda row: (int(row.get("original_index") or 0), str(row.get("card_id") or "")))
    for row in coptic_rows:
        origin = clean(row.get("ما يقولُه قاموسُ الفرعِ عن الأصل"))
        tokens = greek_tokens(origin)
        if not tokens:
            row_gaps.append({
                "source": "coptic",
                "source_card": clean(row.get("card_id")),
                "state": "OPEN-CANDIDATE",
                "reason": "لا رسم يوناني في حقل الأصل المنشور",
            })
            continue
        for position, token in enumerate(tokens, 1):
            add_provenance(provenance, order, token, {
                "kind": "published",
                "source": "coptic",
                "source_card": clean(row.get("card_id")),
                "source_form": "، ".join(clean(x) for x in row.get("coptic_forms", [])),
                "source_meaning": clean(row.get("meaning")),
                "published_origin": origin,
                "sequence_position": position,
            })

    latin_rows = json.loads(LATIN.read_text(encoding="utf-8")).get("rows", [])
    latin_rows.sort(key=lambda row: (
        int(row.get("batch") or 0),
        int(row.get("original_index") or 0),
        str(row.get("card_id") or ""),
    ))
    for row in latin_rows:
        origin = clean(row.get("greek_origin_published"))
        tokens = greek_tokens(origin)
        if not tokens:
            row_gaps.append({
                "source": "latin",
                "source_card": clean(row.get("card_id")),
                "state": "OPEN-CANDIDATE",
                "reason": "لا رسم يوناني في حقل الأصل المنشور",
            })
            continue
        for position, token in enumerate(tokens, 1):
            add_provenance(provenance, order, token, {
                "kind": "published",
                "source": "latin",
                "source_card": clean(row.get("card_id")),
                "source_form": clean(row.get("latin_form")),
                "source_meaning": clean(row.get("meaning")),
                "published_origin": origin,
                "declared_elements": [clean(x) for x in row.get("elements", [])],
                "sequence_position": position,
            })

    counts = {
        "coptic_rows": len(coptic_rows),
        "latin_rows": len(latin_rows),
        "source_rows": len(coptic_rows) + len(latin_rows),
        "published_unique_greek_tokens": len(order),
        "rows_without_greek_script": len(row_gaps),
    }
    return provenance, order, row_gaps, counts


def context_for(provenance: list[dict[str, Any]]) -> str:
    meanings = []
    for row in provenance:
        value = clean(row.get("source_meaning"))
        if value and value not in meanings:
            meanings.append(value)
    return "; ".join(meanings)


def exact_dictionary_entries(
    published: str,
    provenance: list[dict[str, Any]],
) -> tuple[list[dict[str, str]], int, str, dict[str, str]] | None:
    entries, path = BASE.LEX.look(BASE.LANGUAGE, published)
    if not entries:
        return None
    selected = BASE.select_lexicon(entries, context_for(provenance))
    chosen = compact_entry(entries[selected])
    canonical = chosen["word"] or published
    exact, exact_path = BASE.LEX.look(BASE.LANGUAGE, canonical)
    exact_rows = [compact_entry(entry) for entry in exact] or [chosen]
    exact_selected = 0
    for index, entry in enumerate(exact_rows):
        if entry["en"] == chosen["en"] and entry["pos"] == chosen["pos"]:
            exact_selected = index
            break
    return exact_rows, exact_selected, clean(path or exact_path), exact_rows[exact_selected]


def components_from(entry: dict[str, str], parent: str) -> list[str]:
    etymology = entry.get("etym", "")
    if "+" not in etymology:
        return []
    head = COMPARISON_CLAUSE.split(etymology, maxsplit=1)[0]
    found: list[str] = []
    parent_key = greek_key(parent)
    for token in greek_tokens(head):
        if greek_key(token) == parent_key:
            continue
        if token not in found:
            found.append(token)
    return found


def semitic_route(entry: dict[str, str], published: str) -> str:
    etymology = entry.get("etym", "")
    # إصابةُ الهيكل قد تعيد مدخلةً أخرى ذات أصل سامي؛ لا تُغلق الصورة المنشورة
    # بحاشية معجمية ليست لها. وكذلك يبقى الاحتمال الصريح مفتوحا ولو سمى مقارنة.
    if greek_key(entry.get("word")) != greek_key(published):
        return ""
    if UNCERTAIN_ROUTE_OPENING.search(etymology):
        return ""
    return etymology if NAMED_SEMITIC_DONOR.search(etymology) else ""


def root_choice(
    word: str,
    entry: dict[str, str],
    provenance: list[dict[str, Any]],
    arabic_roots: set[str],
    bridge_head: dict[str, set[str]],
    bridge_gloss: dict[str, set[str]],
) -> dict[str, Any] | None:
    skeleton, ranked = BASE.sound_fan(word)
    if not ranked:
        return None
    rank_index = {root: index for index, (root, _weight) in enumerate(ranked)}
    branch_words = BULK.words_of(entry.get("en", "") + " " + context_for(provenance))
    scored = []
    for root, weight in ranked:
        if root not in arabic_roots:
            continue
        direct = branch_words & bridge_head.get(root, set())
        near = (branch_words & bridge_gloss.get(root, set())) - direct
        score = 3 * len(direct) + len(near)
        scored.append({
            "root": root,
            "score": score,
            "direct": bool(direct),
            "shared": sorted(direct)[:5] or sorted(near)[:5],
            "weight": weight,
            "fan_index": rank_index[root],
        })
    scored.sort(key=lambda row: (-int(row["score"]), int(row["fan_index"])))
    if scored:
        selected = scored[0]
        in_resources = True
    else:
        selected = {
            "root": ranked[0][0],
            "score": 0,
            "direct": False,
            "shared": [],
            "weight": ranked[0][1],
            "fan_index": 0,
        }
        in_resources = False
    return {
        "skeleton": skeleton,
        "fan": [{"root": root, "weight": weight} for root, weight in ranked],
        "selected": selected,
        "root_in_arabic_resources": in_resources,
    }


def prepare() -> dict[str, Any]:
    controls = BASE.CONTROL.control_run()
    if any(row.get("lost") for row in controls):
        raise AssertionError("سقط ضابط من الست الصادرة")

    provenance, order, row_gaps, source_counts = source_inventory()
    sweep_rows = json.loads(SWEEP.read_text(encoding="utf-8")).get("both", [])
    existing_sweep = {nfc(row.get("branch")): index for index, row in enumerate(sweep_rows, 1)}
    arabic_roots = set(ROOT_FAN.load_arabic_roots())
    bridge_head, bridge_gloss = BULK.load_bridge()

    cards: list[dict[str, Any]] = []
    gaps: list[dict[str, Any]] = list(row_gaps)
    existing: list[dict[str, Any]] = []
    protected: list[dict[str, Any]] = []
    processed: set[str] = set()
    depth: dict[str, int] = {word: 0 for word in order}
    dictionary_cache: dict[str, tuple[list[dict[str, str]], int, str, dict[str, str]] | None] = {}
    card_by_word: dict[str, dict[str, Any]] = {}

    cursor = 0
    while cursor < len(order):
        word = order[cursor]
        cursor += 1
        if word in processed:
            continue
        processed.add(word)
        prov = provenance[word]
        result = dictionary_cache.get(word)
        if word not in dictionary_cache:
            result = exact_dictionary_entries(word, prov)
            dictionary_cache[word] = result
        if result is None:
            gaps.append({
                "word": word,
                "state": "OPEN-CANDIDATE",
                "reason": "لم يعد build_kaikki_index.look معنى من قاموس الفرع",
                "provenance": prov,
            })
            continue
        entries, selected_index, path, chosen = result

        components = components_from(chosen, word)
        if depth.get(word, 0) < MAX_COMPONENT_DEPTH:
            source_refs = sorted({clean(row.get("source_card")) for row in prov if row.get("source_card")})
            for component in components:
                add_provenance(provenance, order, component, {
                    "kind": "component",
                    "source": "greek-dictionary-compound",
                    "component_of": word,
                    "source_card": ", ".join(source_refs),
                    "source_meaning": chosen.get("en", ""),
                    "published_origin": chosen.get("etym", ""),
                })
                depth[component] = min(depth.get(component, MAX_COMPONENT_DEPTH), depth.get(word, 0) + 1)

        if word in existing_sweep:
            existing.append({
                "word": word,
                "sweep_rank": existing_sweep[word],
                "card": f"PS-GREEK-{existing_sweep[word]:05d}",
                "provenance": prov,
                "components": components,
            })
            continue
        if greek_key(chosen.get("word") or word) in KERA_KEYS or greek_key(word) in KERA_KEYS:
            protected.append({
                "word": word,
                "canonical": chosen.get("word") or word,
                "root": "قرن",
                "state": "PROTECTED-LIVE",
                "note": "κέρας ↔ قرن حكم حي معلوم، فسجل المصدر ولم تعد كتابة الحكم",
                "provenance": prov,
            })
            continue

        sound = root_choice(
            word, chosen, prov, arabic_roots, bridge_head, bridge_gloss
        )
        if sound is None:
            gaps.append({
                "word": word,
                "state": "OPEN-CANDIDATE",
                "reason": "لم تولد مروحة greek جذرا لصورة الأصل كله",
                "dictionary_entry": chosen,
                "components": components,
                "provenance": prov,
            })
            continue

        romanization = BASE.reader_romanization(word, chosen.get("read", ""))
        item = {
            "word": word,
            "canonical": chosen.get("word") or word,
            "romanization": romanization,
            "component": any(row.get("kind") == "component" for row in prov),
            "component_of": sorted({clean(row.get("component_of")) for row in prov if row.get("component_of")}),
            "provenance": prov,
            "dictionary_call": f"build_kaikki_index.look('ancient-greek', {word!r})",
            "dictionary_path": path,
            "dictionary_entries": entries,
            "dictionary_selected": selected_index,
            "dictionary_entry": chosen,
            "named_semitic_route": semitic_route(chosen, word),
            **sound,
        }
        cards.append(item)
        card_by_word[word] = item

    # قد يضاف مسار عنصر إلى صورة عولجت قبل أبيها؛ نعيد ربط القائمة الحية قبل التجميد.
    for item in cards:
        item["provenance"] = provenance[item["word"]]
        item["component"] = any(row.get("kind") == "component" for row in item["provenance"])
        item["component_of"] = sorted({
            clean(row.get("component_of"))
            for row in item["provenance"]
            if row.get("component_of")
        })
    for index, item in enumerate(cards, 1):
        item["directed_rank"] = index
        item["id"] = f"GD-GREEK-{index:05d}"

    input_hashes = {path.relative_to(ROOT).as_posix(): sha256(path) for path in (COPTIC, LATIN, SWEEP)}
    counts = {
        **source_counts,
        "discovered_tokens_with_components": len(provenance),
        "cards": len(cards),
        "batches": math.ceil(len(cards) / BATCH_SIZE),
        "existing_sweep_cards_reused": len(existing),
        "protected_live_relations": len(protected),
        "open_source_records": len(gaps),
        "named_semitic_routes": sum(bool(row.get("named_semitic_route")) for row in cards),
        "root_present_in_arabic_resources": sum(bool(row.get("root_in_arabic_resources")) for row in cards),
    }
    payload = {
        "schema": "ancient-greek-directed-source-queue-v1",
        "date": DATE,
        "batch_size": BATCH_SIZE,
        "policy": {
            "published_greek_not_recipient_form": True,
            "compound_elements_independent": True,
            "sound_call": "fan_any_script.fan(w, 'greek')",
            "event_call": "frozen_event.all_tiers(root)",
            "dictionary_call": "build_kaikki_index.look('ancient-greek', w)",
            "arabic_witness_call": "search_arabic_root_senses.py root --max-chars 0",
            "etymology_is_note_only": True,
            "only_named_semitic_donor_closes": True,
        },
        "inputs": input_hashes,
        "counts": counts,
        "controls": controls,
        "cards": cards,
        "existing": existing,
        "protected": protected,
        "open": gaps,
    }
    QUEUE.write_text(json.dumps(payload, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    PREP_AUDIT.write_text(preparation_audit(payload), encoding="utf-8", newline="\n")
    return payload


def preparation_audit(payload: dict[str, Any]) -> str:
    counts = payload["counts"]
    lines = [
        "# محضر إعداد الأصول اليونانية الموجهة من القبطي واللاتيني",
        "",
        f"- التاريخ: {DATE}.",
        f"- صفوف المصدر: {counts['source_rows']}؛ القبطي {counts['coptic_rows']}؛ اللاتيني {counts['latin_rows']}.",
        f"- الصور اليونانية المنشورة المتميزة: {counts['published_unique_greek_tokens']}.",
        f"- الصور بعد فك العناصر: {counts['discovered_tokens_with_components']}.",
        f"- البطاقات المكتملة القابلة للحصاد: {counts['cards']} في {counts['batches']} دفعة.",
        f"- صور المسح السابق المعاد استعمال بطاقتها بلا تكرار: {counts['existing_sweep_cards_reused']}.",
        f"- الأحكام الحية المحمية: {counts['protected_live_relations']}، ومنها `κέρας ↔ قرن`.",
        f"- الباقي مفتوح بسبب فجوة رسم أو قاموس أو مروحة: {counts['open_source_records']}؛ وليس رفضا.",
        "- استخرج الرسم اليوناني المنشور نفسه، ولم تدخل الصورة القبطية أو اللاتينية مروحة اليونانية.",
        "- حاشية الأصل خبر، ولا تغلق إلا إذا سمت طريقا من مانح سامي.",
        "- ضابط الست الصادرة مر بلا فقد قبل تجميد الطابور.",
        "",
    ]
    return unicodedata.normalize("NFC", "\n".join(lines)).replace("—", "؛")


def provenance_lines(rows: list[dict[str, Any]]) -> list[str]:
    lines = ["- حاشية المادة الموجهة، وليست رجلا رابعة:"]
    for row in rows:
        if row.get("kind") == "component":
            lines.append(
                f"  - عنصر مستقل من `{clean(row.get('component_of'))}`؛ إحالات المصدر: "
                f"{clean(row.get('source_card')) or 'غير مسماة'}؛ نص التركيب: {clean(row.get('published_origin'))}."
            )
        else:
            lines.append(
                f"  - {clean(row.get('source'))}؛ البطاقة `{clean(row.get('source_card'))}`؛ "
                f"الصورة المستقبلة `{clean(row.get('source_form'))}`؛ معناها «{clean(row.get('source_meaning'))}»؛ "
                f"الأصل المنشور: {clean(row.get('published_origin'))}."
            )
    return lines


def directed_card(row: dict[str, Any], witnesses: list[dict[str, Any]]) -> tuple[list[str], dict[str, Any]]:
    word = clean(row["word"])
    root = clean(row["selected"]["root"])
    route = clean(row.get("named_semitic_route"))
    fan_text = "، ".join(
        f"`{clean(item['root'])}`[{float(item['weight']):.6f}]" for item in row["fan"]
    )
    entries = row["dictionary_entries"]
    selected = int(row["dictionary_selected"])
    meaning = clean(entries[selected].get("en"))
    if route:
        closure = "SEMITIC-SOURCE-TRANSMISSION"
        verdict = "LOANWORD"
        orbit = (
            "سمى قاموس اليونانية مانحا ساميا في طريق الصورة، فثبت النقل المسمى وحده؛ "
            "وبقيت مقابلة الصوت والمعنى معروضة في مقام اليونانية"
        )
    elif not row.get("root_in_arabic_resources"):
        closure = "OPEN-CANDIDATE"
        verdict = "غير صادر"
        orbit = (
            f"ولدت مروحة اليونانية `{root}`، لكن البحث الكامل لم يجد له شاهدا في موارد الجذور "
            "المسماة؛ فلا يكتب مدار دلالي بلا مادة عربية، وتبقى الصورة مفتوحة"
        )
    else:
        closure = "OPEN-CANDIDATE"
        verdict = "غير صادر"
        orbit = BASE.open_orbit(meaning, root)

    lines = [
        f"### بطاقة موجهة: `{word}` /{clean(row['romanization'])}/ ↔ `{root}`؛ {clean(row['id'])}",
        "",
        "- إصدار البروتوكول: RECOVERY-v2؛ الطبقة: استكشاف.",
        f"- الصورة والرومنة: `{word}` /{clean(row['romanization'])}/؛ الأصل اليوناني المنشور هو الذي فحص.",
        f"- نوع الصورة: {'عنصر مركب فحص مستقلا' if row.get('component') else 'صورة أصل يوناني منشور'}.",
        *provenance_lines(row.get("provenance", [])),
        f"- رجل الصوت: استدعاء `fan_any_script.fan('{word}', 'greek')` بالخط `greek` صريحا؛ "
        f"الهيكل `{clean(row['skeleton'])}`؛ الجذر المنتخب `{root}` حاضر في المروحة.",
        f"- المروحة كاملة مرتبة، والوزن ترتيب لا حكم: {fan_text}.",
        "- رجل الحدث: `frozen_event.all_tiers(root)` أعاد الدرجات الآتية بلا زيادة:",
        *BASE.render_event(root),
        *BASE.render_lexicon(entries, selected, clean(row.get("dictionary_path"))),
        *BASE.render_arabic_witnesses(root, witnesses),
        f"- المدار المكتوب باليد بالكلمات: {clean(orbit)}.",
        f"- حاشية الأصل، وليست رجلا رابعة: {clean(entries[selected].get('etym')) or 'لم يذكر القاموس أصلا'}.",
    ]
    if route:
        lines.append(f"- المانح السامي المسمى: {route}.")
    lines.extend([
        f"- حالة الإغلاق: `{closure}`.",
        f"- الحكم (استكشاف): `{verdict}`.",
        "",
    ])
    return lines, {
        "id": row["id"],
        "directed_rank": row["directed_rank"],
        "word": row["word"],
        "romanization": row["romanization"],
        "root": root,
        "component": bool(row.get("component")),
        "component_of": row.get("component_of", []),
        "provenance_count": len(row.get("provenance", [])),
        "dictionary_path": row.get("dictionary_path"),
        "dictionary_entry_count": len(entries),
        "arabic_witness_count": len(witnesses),
        "event_tiers": [item.tier for item in BASE.EVENT.all_tiers(root)],
        "closure": closure,
        "verdict": verdict,
        "named_semitic_route": route,
    }


def batch_audit(batch: int, rows: list[dict[str, Any]], cards: list[dict[str, Any]], controls: list[dict[str, Any]]) -> str:
    counts = Counter(card["closure"] for card in cards)
    lines = [
        f"# محضر الأصول اليونانية الموجهة، الدفعة {batch:03d}",
        "",
        f"- التاريخ: {DATE}.",
        f"- النافذة: {len(rows)} صورة يونانية منشورة أو عنصر مركب مستقل.",
        "- الأرجل ثلاث: مروحة greek، وجميع درجات الحدث، ومعنى قاموس اليونانية وشواهد الجذر كاملة.",
        "- الصورة القبطية أو اللاتينية حاشية مصدر فقط، ولم تدخل المروحة.",
        "- غير المحسوم بقي OPEN-CANDIDATE، ولم يتحول غياب المورد إلى رفض.",
        f"- النقل السامي المسمى: {counts['SEMITIC-SOURCE-TRANSMISSION']}.",
        f"- المفتوح: {counts['OPEN-CANDIDATE']}.",
        f"- ضابط الست الصادرة: {len(controls)} من 6؛ الفقد: {sum(bool(row.get('lost')) for row in controls)}.",
        "",
    ]
    return unicodedata.normalize("NFC", "\n".join(lines)).replace("—", "؛")


def batch_manifest_path(batch: int) -> Path:
    return ROOT / "data" / f"ancient-greek-directed-source-batch-{batch:03d}.json"


def batch_audit_path(batch: int) -> Path:
    return ROOT / "05-audits" / f"{DATE}-ancient-greek-directed-source-batch-{batch:03d}.md"


def build_batches(numbers: list[int]) -> list[dict[str, Any]]:
    if not QUEUE.exists():
        raise AssertionError("شغل --prepare أولا")
    queue = json.loads(QUEUE.read_text(encoding="utf-8"))
    cards = queue.get("cards", [])
    total = math.ceil(len(cards) / BATCH_SIZE)
    requested = sorted(set(numbers))
    if not requested or any(batch < 1 or batch > total for batch in requested):
        raise AssertionError(f"أرقام الدفعات خارج 1..{total}")
    controls = BASE.CONTROL.control_run()
    if any(row.get("lost") for row in controls):
        raise AssertionError("سقط ضابط من الست الصادرة")

    selected_rows: dict[int, list[dict[str, Any]]] = {
        batch: cards[(batch - 1) * BATCH_SIZE: batch * BATCH_SIZE]
        for batch in requested
    }
    roots = sorted({row["selected"]["root"] for rows in selected_rows.values() for row in rows})
    witnesses = BASE.AR.matches_for_roots(BASE.AR.DEFAULT_RESOURCES, roots, None)
    reading_text = READING.read_text(encoding="utf-8")
    results = []
    append_chunks: list[str] = []
    for batch in requested:
        marker = f"ANCIENT-GREEK-DIRECTED-SOURCE-BATCH-{batch:03d}"
        if f"<!-- {marker}:START -->" in reading_text:
            raise AssertionError(f"الدفعة {batch:03d} موجودة")
        output_rows = []
        card_lines = []
        for row in selected_rows[batch]:
            lines, output = directed_card(row, witnesses.get(row["selected"]["root"], []))
            card_lines.extend(lines)
            output_rows.append(output)
        chunk = "\n".join([
            f"<!-- {marker}:START -->",
            "",
            f"## الأصول اليونانية الموجهة من القبطي واللاتيني، الدفعة {batch:03d} ({DATE})",
            "",
            *card_lines,
            f"<!-- {marker}:END -->",
            "",
        ])
        chunk = unicodedata.normalize("NFC", chunk).replace("—", "؛")
        if "—" in chunk:
            raise AssertionError("بقيت شرطة طويلة في البطاقة")
        append_chunks.append(chunk)
        payload = {
            "schema": "ancient-greek-directed-source-batch-v1",
            "date": DATE,
            "batch": batch,
            "batch_size": len(selected_rows[batch]),
            "queue_sha256": sha256(QUEUE),
            "controls": controls,
            "cards": output_rows,
        }
        batch_manifest_path(batch).write_text(
            json.dumps(payload, ensure_ascii=False, indent=1) + "\n",
            encoding="utf-8", newline="\n",
        )
        batch_audit_path(batch).write_text(
            batch_audit(batch, selected_rows[batch], output_rows, controls),
            encoding="utf-8", newline="\n",
        )
        results.append(payload)
    with READING.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write("\n" + "\n".join(append_chunks))
    return results


def replace_batches(numbers: list[int]) -> list[dict[str, Any]]:
    """أعِد بناء دفعاتنا نفسها بعد تصحيح قاعدة، بلا مساس بأي قراءة أخرى."""
    reading = READING.read_text(encoding="utf-8")
    for batch in sorted(set(numbers)):
        marker = f"ANCIENT-GREEK-DIRECTED-SOURCE-BATCH-{batch:03d}"
        pattern = re.compile(
            rf"\n*<!-- {re.escape(marker)}:START -->.*?"
            rf"<!-- {re.escape(marker)}:END -->\n*",
            re.S,
        )
        reading, count = pattern.subn("\n\n", reading)
        if count != 1:
            raise AssertionError(f"تعذر تعيين كتلة الدفعة {batch:03d} وحدها: {count}")
        batch_manifest_path(batch).unlink(missing_ok=True)
        batch_audit_path(batch).unlink(missing_ok=True)
    READING.write_text(
        unicodedata.normalize("NFC", reading.rstrip()) + "\n",
        encoding="utf-8", newline="\n",
    )
    return build_batches(numbers)


def finalize() -> dict[str, Any]:
    queue = json.loads(QUEUE.read_text(encoding="utf-8"))
    total = int(queue["counts"]["batches"])
    reading = READING.read_text(encoding="utf-8")
    missing = [
        batch for batch in range(1, total + 1)
        if f"<!-- ANCIENT-GREEK-DIRECTED-SOURCE-BATCH-{batch:03d}:END -->" not in reading
    ]
    if missing:
        raise AssertionError(f"دفعات لم تحصد بعد: {missing}")
    marker = "ANCIENT-GREEK-DIRECTED-SOURCE-OPEN-REGISTER"
    if f"<!-- {marker}:START -->" in reading:
        raise AssertionError("سجل المفتوح موجود")
    lines = [
        f"<!-- {marker}:START -->",
        "",
        f"## سجل ما بقي مفتوحا في المادة اليونانية الموجهة ({DATE})",
        "",
        "هذه صور دخلت سجل العمل، ولم تكتمل لها بطاقة الأرجل الثلاث؛ بقاؤها انتظار مادة لا رفض.",
        "",
    ]
    for row in queue.get("open", []):
        word = clean(row.get("word")) or "[صف مصدر بلا رسم يوناني]"
        lines.append(f"- `{word}`: `OPEN-CANDIDATE`؛ {clean(row.get('reason'))}.")
    for row in queue.get("protected", []):
        lines.append(
            f"- `{clean(row.get('word'))} ↔ {clean(row.get('root'))}`: حكم حي محمي؛ "
            "دخلت إحالات المصدر السجل ولم تعد كتابة الحكم."
        )
    lines.extend(["", f"<!-- {marker}:END -->", ""])
    chunk = unicodedata.normalize("NFC", "\n".join(lines)).replace("—", "؛")
    with READING.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write("\n" + chunk)
    summary = {
        "schema": "ancient-greek-directed-source-final-v1",
        "date": DATE,
        "counts": queue["counts"],
        "queue_sha256": sha256(QUEUE),
        "batches": total,
        "complete": True,
    }
    FINAL_AUDIT.write_text(
        "\n".join([
            "# المحضر النهائي للأصول اليونانية الموجهة",
            "",
            f"- البطاقات: {queue['counts']['cards']}.",
            f"- الدفعات: {total}.",
            f"- المفتوح في سجل المصدر: {queue['counts']['open_source_records']}.",
            f"- الأحكام الحية المحمية: {queue['counts']['protected_live_relations']}.",
            "- كل الدفعات وسجل المفتوح موجودة، وضابط الست الصادرة محفوظ.",
            "",
        ]),
        encoding="utf-8", newline="\n",
    )
    return summary


def check() -> dict[str, Any]:
    queue = json.loads(QUEUE.read_text(encoding="utf-8"))
    stale = []
    for relative, expected in queue.get("inputs", {}).items():
        path = ROOT / relative
        if not path.exists() or sha256(path) != expected:
            stale.append(relative)
    ids = [row.get("id") for row in queue.get("cards", [])]
    if len(ids) != len(set(ids)):
        raise AssertionError("تكررت معرفات الطابور")
    bad_fan = [
        row.get("id") for row in queue.get("cards", [])
        if row.get("selected", {}).get("root") not in {item.get("root") for item in row.get("fan", [])}
    ]
    if bad_fan:
        raise AssertionError(f"جذر خارج المروحة: {bad_fan[:5]}")
    return {
        "cards": len(ids),
        "batches": queue.get("counts", {}).get("batches"),
        "stale_inputs": stale,
        "fan_failures": len(bad_fan),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--prepare", action="store_true")
    group.add_argument("--batches", nargs="+", type=int)
    group.add_argument("--replace-batches", nargs="+", type=int)
    group.add_argument("--finalize", action="store_true")
    group.add_argument("--check", action="store_true")
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    if args.prepare:
        payload = prepare()
        print(json.dumps(payload["counts"], ensure_ascii=False))
    elif args.batches:
        payloads = build_batches(args.batches)
        print(json.dumps({"batches": [row["batch"] for row in payloads], "cards": sum(len(row["cards"]) for row in payloads)}, ensure_ascii=False))
    elif args.replace_batches:
        payloads = replace_batches(args.replace_batches)
        print(json.dumps({"replaced_batches": [row["batch"] for row in payloads], "cards": sum(len(row["cards"]) for row in payloads)}, ensure_ascii=False))
    elif args.finalize:
        print(json.dumps(finalize(), ensure_ascii=False))
    else:
        print(json.dumps(check(), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
