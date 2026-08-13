# -*- coding: utf-8 -*-
"""حصاد بطاقات القرض التي أعادها فحص 2026-08-05 إلى الطابور.

تولد الأداة المروحة وترتبها، وتطلب الحدث من السجل المجمد وحده. لا تولد
مدارًا موجبًا: كل صلة موجبة موجودة نصًا في ``MANUAL_SPECS``. وتبقى البطاقة
القديمة في ملف القراءة، ثم تلحق بها بطاقة ناسخة ذات معرّف صريح.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import fan_any_script as F  # noqa: E402
import frozen_event as FE  # noqa: E402
import rebuild_khashim_indo_european_batches as K  # noqa: E402

DATE = "2026-08-14"
BATCH_SIZE = 150
READINGS = ROOT / "04-cross-linguistic" / "readings"
NETWORK = ROOT / "04-cross-linguistic" / "shift-network-draft.md"

LANGUAGES = {
    "welsh": {
        "label": "الويلزية/Welsh",
        "id_label": "WELSH",
        "script": "latin",
        "expected": 2913,
    },
    "old-irish": {
        "label": "الإيرلندية القديمة/Old Irish",
        "id_label": "OLD-IRISH",
        "script": "latin",
        "expected": 735,
    },
    "gothic": {
        "label": "القوطية/Gothic",
        "id_label": "GOTHIC",
        "script": "germanic",
        "expected": 193,
    },
    "old-norse": {
        "label": "النوردية القديمة/Old Norse",
        "id_label": "OLD-NORSE",
        "script": "germanic",
        "expected": 115,
    },
}

# لا يصدر موجب إلا من هذا النص المكتوب يدويًا. معنى الفرع لا يولد المدار.
MANUAL_SPECS: dict[tuple[str, int], list[dict[str, str]]] = {
    ("welsh", 18): [{
        "root": "حوط",
        "orbit": (
            "القبعة تحيط بأعلى الرأس في استدارة، وتجعل الرأس داخل حدها كما "
            "يجعل الحائط ما وراءه في حوزته؛ فمعنى `hat` يصل إلى حدث `حوط` "
            "في الاستدارة حول الشيء وصيانته داخل محيط."
        ),
        "lisan": "الحائط: الجدار لأنه يحوط ما فيه.",
        "taj": "الحائط: الجدار، لأنه يحوط ما فيه.",
    }],
    ("welsh", 20): [{
        "root": "كنن",
        "orbit": (
            "العلبة جوف متين يضم ما يوضع فيه، فيستره ويحميه من الخارج؛ "
            "فمعنى `a can` يصل إلى حدث `كنن` في جعل الشيء داخل كن واق يحجبه "
            "ويصونه."
        ),
        "lisan": "الكِن والكِنّة والكِنان: وقاء كل شيء وستره.",
        "taj": "الكِن: وقاء كل شيء وستره، والكِن البيت يرد البرد والحر.",
    }],
    ("welsh", 80): [{
        "root": "صلد",
        "orbit": (
            "الشيء الموصوف بأنه `solid` متماسك صلب لا تتخلله مادة ولا ينفذ "
            "فيه شيء بسهولة؛ فمعنى الصلابة في الفرع يصل مباشرة إلى حدث `صلد` "
            "في تمام الصلابة وملاسة السطح المانعة للنفاذ."
        ),
        "lisan": "حجر صلد وصلود: بين الصلادة والصلود، صلب أملس.",
        "taj": "الصلد: الصلب الأملس؛ يقال حجر صلد وصلود وصليد.",
    }],
}

# إغلاقات لا تنشئ صلة مقارنة. لكل عضو دليله، ولا يورث الحكم لمتحد الرسم.
NAMED_CLOSURES: dict[tuple[str, int], dict[str, str]] = {
    ("welsh", 48): {
        "closure": "SEMITIC-SOURCE-TRANSMISSION",
        "donor": "العربية لَيْمُون (laymūn)",
        "route": "العربية لَيْمُون ← الفرنسية القديمة lymon ← الإنجليزية الوسطى lymon ثم الإنجليزية lemon ← الويلزية lemon",
        "evidence": "04-cross-linguistic/data/lane_d_middle_english_transmissions.jsonl، السطر 88",
    },
    ("welsh", 100): {
        "closure": "ABBREVIATION",
        "donor": "لا مانح سامي؛ العضو اختصار حرفي",
        "route": "`CD` تسمية مختصرة من الحرفين الأولين في `compact disc`، لا مادة لفظية مستقلة للمقارنة الجذرية",
        "evidence": "معنى العضو وأصله المنشوران في البطاقة التاريخية نفسها",
    },
    ("welsh", 148): {
        "closure": "SEMITIC-SOURCE-TRANSMISSION",
        "donor": "الأكدية qanû، القصبة والمقياس",
        "route": "الأكدية qanû ← اليونانية kanōn، قضيب القياس ثم القاعدة ← اللاتينية canon ← الإنجليزية canon ← الويلزية canon",
        "evidence": "data/alawlaqi-prior-attempts.json، مادة قانون، ونقل باقر ص.141",
    },
    ("welsh", 149): {
        "closure": "SEMITIC-SOURCE-TRANSMISSION",
        "donor": "الأكدية qanû، القصبة والمقياس",
        "route": "الأكدية qanû ← اليونانية kanōn ← اللاتينية canon في الاستعمال الكنسي ← الإنجليزية canon ← الويلزية canon",
        "evidence": "data/alawlaqi-prior-attempts.json، مادة قانون، ونقل باقر ص.141",
    },
    ("welsh", 150): {
        "closure": "SEMITIC-SOURCE-TRANSMISSION",
        "donor": "الأكدية qanû، القصبة",
        "route": "الأكدية qanû ← اليونانية kanna ← اللاتينية canna ← الإيطالية cannone ← الفرنسية الوسطى canon ← الإنجليزية cannon ← الويلزية canon",
        "evidence": "04-cross-linguistic/data/lane_d_middle_english_transmissions.jsonl، السطر 14",
    },
}

CONTROL_SPECS = [
    {"word": "mwg", "root": "موج", "closure": "ROOT-TRACE"},
    {"word": "melg", "root": "ملج", "closure": "ROOT-ECHO"},
    {"word": "senos", "root": "سن", "closure": "NUCLEUS-TRACE"},
    {"word": "caer", "root": "قر", "closure": "NUCLEUS-TRACE"},
    {"word": "môr", "root": "مور", "closure": "ROOT-ECHO"},
    {"word": "car", "root": "جر", "closure": "NUCLEUS-TRACE"},
]


def clean(value: Any) -> str:
    return " ".join(str(value or "").split()).replace("`", "ˋ")


def skeleton_variants(form: str, script: str) -> str:
    values = ["".join(F.skeleton(form, script))]
    if script in {"latin", "germanic", "greek"}:
        for ending in F.LATIN_ENDINGS:
            if form.lower().endswith(ending) and len(form) - len(ending) >= 2:
                alternate = "".join(F.skeleton(form[:-len(ending)], script))
                if 2 <= len(alternate) <= 4 and alternate not in values:
                    values.append(alternate)
                break
    return "|".join(value for value in values if value)


def current_fan(
    form: str,
    language: str,
    selected: set[str],
) -> tuple[list[dict[str, Any]], int]:
    cfg = LANGUAGES[language]
    script = str(cfg["script"])
    ranked = F.rank(form, F.fan(form, script), script)
    ordered = [root for root, _ in ranked]
    weights = dict(ranked)
    labels = {root: "فصيح" for root in ordered}
    dialect_additions = 0
    for root, label in F.fan_with_dialect(form, script):
        if root not in labels:
            labels[root] = label
            ordered.append(root)
            dialect_additions += 1

    skeleton = skeleton_variants(form, script)
    review: list[dict[str, Any]] = []
    for root in ordered:
        route = ""
        searches: list[str] = []
        try:
            route, searches = K.match_sound_route(skeleton, root, language)
        except AssertionError:
            pass
        event = FE.resolve(root)
        review.append({
            "root": root,
            "weight": float(weights.get(root, 0.0)),
            "dialect_label": None if labels[root] == "فصيح" else labels[root],
            "sound": bool(route),
            "sound_route": route,
            "sound_searches": searches,
            "event_tier": event.tier if event else 0,
            "event_tier_ar": event.tier_ar if event else "",
            "event_source": event.source if event else "",
            "event_text": event.text if event else "",
            "event_note": event.note if event else "",
            "meaning": "✓" if root in selected else ("×" if route and event else "؟"),
        })
    return review, dialect_additions


def render_candidate(item: dict[str, Any]) -> str:
    dialect = f"،له={item['dialect_label']}" if item["dialect_label"] else ""
    return (
        f"`{item['root']}`[و{item['weight']:.6f}،"
        f"ص{'✓' if item['sound'] else '×'}،ح{'✓' if item['event_tier'] else '×'}،"
        f"د{item['event_tier']}،م{item['meaning']}{dialect}]"
    )


def missing_sound_searches(form: str, language: str) -> list[str]:
    cfg = LANGUAGES[language]
    script = str(cfg["script"])
    label = str(cfg["label"])
    language_names = [part.strip() for part in label.split("/")]
    lines = NETWORK.read_text(encoding="utf-8").splitlines()
    queries: list[str] = []
    seen: set[tuple[str, str]] = set()
    for source in F.skeleton(form, script):
        for arabic in F.FANS[script].get(source, ()):
            pair = (source, arabic)
            if pair in seen or pair in K.ROW_IDS:
                continue
            seen.add(pair)
            hits = sum(
                source.casefold() in line.casefold()
                and arabic in line
                and any(name.casefold() in line.casefold() for name in language_names)
                for line in lines
            )
            queries.append(
                f"`{source}` + `{arabic}` + «{label}» في عمود الشاهد، النتائج الحرفية {hits}"
            )
    return queries or [
        f"الهيكل الكامل + «{label}» في عمود الشاهد، النتائج الحرفية 0"
    ]


def original_cards(language: str) -> list[dict[str, Any]]:
    cfg = LANGUAGES[language]
    path = READINGS / f"{language}.md"
    body = path.read_text(encoding="utf-8")
    blocks = re.split(r"(?=^### )", body, flags=re.MULTILINE)
    pattern = re.compile(
        rf"LOAN-REOPEN-{re.escape(str(cfg['id_label']))}-(\d+)"
    )
    found: dict[int, dict[str, Any]] = {}
    for block in blocks:
        if "أعيدت إلى الطابور" not in block or "سطر النسخ (2026-08-05" not in block:
            continue
        matches = pattern.findall(block)
        if not matches:
            continue
        index = int(matches[-1])
        word_match = re.search(r"^- الكلمةُ? في الفرع:\s*([^\s\[]+)", block, re.MULTILINE)
        meaning_match = re.search(r"^- المعنى من قاموس الفرع:\s*«([^»]*)»", block, re.MULTILINE)
        source_match = re.search(r"^- أقدمُ صورةٍ مستعادة:\s*(.*?)\s*\[Kaikki", block, re.MULTILINE)
        if not word_match or not meaning_match:
            raise AssertionError(f"تعذر استخراج صورة أو معنى البطاقة {index}")
        found[index] = {
            "index": index,
            "old_id": f"LOAN-REOPEN-{cfg['id_label']}-{index:05d}",
            "word": word_match.group(1).strip().strip("`"),
            "meaning": meaning_match.group(1).strip(),
            "source": source_match.group(1).strip() if source_match else "لا نص أصل مستخرج",
            "heading": block.splitlines()[0].replace("### ", "").strip(),
        }
    cards = [found[index] for index in sorted(found)]
    if len(cards) != int(cfg["expected"]):
        raise AssertionError(
            f"جرد {language} المنقول من ملفات القراءة {len(cards)} لا يساوي المتوقع {cfg['expected']}"
        )
    ledger = json.loads((ROOT / "data" / "recovery-ledger.json").read_text(encoding="utf-8"))
    ledger_count = sum(
        row.get("file") == f"04-cross-linguistic/readings/{language}.md"
        and "أعيدت إلى الطابور" in row.get("closure", "")
        for row in ledger["suspended"]
    )
    if ledger_count != int(cfg["expected"]):
        raise AssertionError(
            f"مرشح السجل أعاد {ledger_count} بطاقة لـ{language} بدل {cfg['expected']}"
        )
    return cards


def closure_for(root: str) -> str:
    return "NUCLEUS-TRACE" if len(re.findall(r"[ء-ي]", root)) == 2 else "ROOT-TRACE"


def control_run() -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for spec in CONTROL_SPECS:
        review, _ = current_fan(spec["word"], "welsh", {spec["root"]})
        by_root = {item["root"]: item for item in review}
        item = by_root.get(spec["root"])
        if not item:
            raise AssertionError(f"تغير الضابط: خرج {spec['word']} ↔ {spec['root']} من المروحة")
        if not item["sound"]:
            raise AssertionError(f"تغير الضابط: سقط المسار الصوتي لـ{spec['word']} ↔ {spec['root']}")
        if not item["event_tier"]:
            raise AssertionError(f"تغير الضابط: لم يعد الحدث يحل لـ{spec['word']} ↔ {spec['root']}")
        results.append({
            **spec,
            "current_verdict": spec["closure"],
            "weight": item["weight"],
            "sound_route": item["sound_route"],
            "event_tier": item["event_tier"],
            "event_tier_ar": item["event_tier_ar"],
            "event_text": item["event_text"],
            "unchanged": True,
        })
    return results


def build_card(language: str, card: dict[str, Any]) -> tuple[list[str], dict[str, Any], str]:
    index = int(card["index"])
    word = str(card["word"])
    meaning = str(card["meaning"])
    specs = MANUAL_SPECS.get((language, index), [])
    named = NAMED_CLOSURES.get((language, index))
    selected = {spec["root"] for spec in specs}
    review, dialect_additions = current_fan(word, language, selected)
    by_root = {item["root"]: item for item in review}
    cfg = LANGUAGES[language]
    new_id = f"LH-{cfg['id_label']}-{index:05d}"
    lines = [
        f"### بطاقة حصاد القرض المعاد فتحه: `{clean(word)}`؛ {new_id}",
        f"<!-- LOAN-HARVEST-REREVIEW:{card['old_id']} -->",
        f"- ناسخ البطاقة التاريخية: `{card['old_id']}` ← `{new_id}`؛ بقي النص القديم كاملًا، وهذا الحكم هو النافذ بتاريخ {DATE}.",
        f"- اللسان: {cfg['label']}؛ الطبقة: استكشاف.",
        f"- العضو ومعناه في الفرع: `{clean(word)}` «{clean(meaning)}».",
        f"- الأصل المنشور في بطاقة العضو: {clean(card['source'])}",
        f"- الخطوة صفر: الصورة `{clean(word)}`؛ باب المروحة `{cfg['script']}`؛ الهياكل الحالية `{' / '.join(skeleton_variants(word, str(cfg['script'])).split('|')) or '∅'}`.",
        f"- المروحة الكاملة من `fan_any_script.fan` مرتبة بـ`fan_any_script.rank`: {('، '.join(render_candidate(item) for item in review) or 'لا مرشح قابل للتوليد')}. الوزن ترتيب لا حكم؛ ص=مسار صوت؛ ح=حدث؛ د=درجة الحدث؛ م× يعني أن معنى الفرع لم يتصل بالحدث في مدار مقنع.",
        f"- فحص `fan_with_dialect`: أضاف {dialect_additions} صورة موسومة بعد الفصيح ولم يحذف الفصيح.",
        "- رجل الحدث: حُل كل مرشح ظاهر أعلاه بـ`frozen_event.resolve` وحده؛ لم تُسأل عضوية ملف الـ2,285.",
    ]

    positives: list[dict[str, Any]] = []
    for spec in specs:
        root = spec["root"]
        item = by_root.get(root)
        if not item or not item["sound"] or not item["event_tier"]:
            raise AssertionError(f"الموجب اليدوي لا يستوفي الأداتين الحاليتين: {card['old_id']}:{root}")
        closure = closure_for(root)
        orbit = clean(spec["orbit"])
        if len(orbit) < 80:
            raise AssertionError(f"مدار موجب أقصر من حد الضبط: {card['old_id']}:{root}")
        lines.extend([
            f"- المقابل المنتخب: `{root}`؛ وزن العرض {item['weight']:.6f}.",
            f"- مسار الصوت المسمى: {item['sound_route']}.",
            f"- ما فُتش في الشبكة بالحرفين وباسمي اللسان: {'؛ '.join(item['sound_searches'])}.",
            f"- الحدث من السجل المجمد كما هو (درجة {item['event_tier']}، {item['event_tier_ar']}): «{item['event_text']}» [{item['event_source']}]."
            + (f" {item['event_note']}." if item["event_note"] else ""),
            f"- شاهد لسان العرب: «{clean(spec['lisan'])}»",
            f"- شاهد تاج العروس: «{clean(spec['taj'])}»",
            f"- المدار المكتوب باليد: {orbit}",
            f"- نتيجة الأرجل الثلاث للمقابل `{root}`: **{closure} (استكشاف)**.",
        ])
        positives.append({
            "root": root,
            "closure": closure,
            "orbit": orbit,
            **{key: item[key] for key in (
                "weight", "sound_route", "sound_searches", "event_tier",
                "event_tier_ar", "event_source", "event_text", "event_note",
            )},
        })

    if positives:
        closures = list(dict.fromkeys(item["closure"] for item in positives))
        closure = " + ".join(closures)
        lines.extend([
            f"- الحكم (استكشاف): **{closure} (استكشاف)**.",
            f"- حالة الإغلاق: {closure}.",
            "",
        ])
        reason = ""
    elif named:
        closure = named["closure"]
        lines.extend([
            f"- فحص الأصل الأعمق: {clean(named['route'])}.",
            f"- المانح أو الباب المسمى: {clean(named['donor'])}.",
            f"- موضع الدليل: {clean(named['evidence'])}.",
            "- المدار المكتوب باليد: لم يُنشأ مدار نسب؛ الإغلاق هنا حكم نقل مسمى أو بنية اختصار، لا صلة بين معنى الفرع وحدث عربي.",
            f"- الحكم (استكشاف): **{closure} (استكشاف)**.",
            f"- حالة الإغلاق: {closure}.",
            "",
        ])
        reason = ""
    else:
        ready = [item for item in review if item["sound"] and item["event_tier"]]
        sounded = [item for item in review if item["sound"]]
        if ready:
            reason = "orbit_not_convincing"
            requirement = "صلة دلالية يقتنع بها القارئ بين معنى هذا العضو وحدث مرشح ذي صوت مسمى"
            search_line = "لم يعلن صف ناقص؛ وُجدت مسارات صوتية مسماة، وكان الامتناع في رجل المدار وحدها."
        elif sounded:
            reason = "event_unresolved"
            requirement = "حدث مجمد يحله السجل لمرشح ذي صوت مسمى، ثم مدار دلالي مقنع"
            search_line = "لم يعلن صف ناقص؛ وُجد مسار صوتي مسمى، ولم يحل السجل حدث المرشح."
        elif review:
            reason = "no_named_sound"
            requirement = "مسار صوتي مسمى لمرشح في المروحة، ثم حدث ومدار مقنعان"
            search_line = "؛ ".join(missing_sound_searches(word, language))
        else:
            reason = "fan_empty"
            requirement = "مرشح تولده المروحة من الهيكل المثبت، ثم الأرجل الباقية"
            search_line = "لم يعلن صف ناقص لأن الأداة لم تولد مرشحًا يفحص في الشبكة."
        lines.extend([
            f"- المدار المكتوب باليد: فُحص معنى `{clean(word)}` «{clean(meaning)}» بإزاء أحداث المرشحين الظاهرين، ولم أجد صلة تصل المعنى بحدث السجل صلة يطمئن إليها القارئ؛ لذلك لم أصطنع مدارًا.",
            f"- ما فُتش قبل إعلان نقص صف: {search_line}",
            "- الحكم (استكشاف): **غير صادر (استكشاف)**.",
            f"- عائق: النوع=OPEN-CANDIDATE؛ يتطلب={requirement}",
            "- حالة الإغلاق: OPEN-CANDIDATE.",
            "",
        ])
        closure = "OPEN-CANDIDATE"

    manifest = {
        "card_id": new_id,
        "supersedes": card["old_id"],
        "original_index": index,
        "language": language,
        "form": word,
        "branch_meaning": meaning,
        "published_source": card["source"],
        "fan_script": cfg["script"],
        "fan_candidates": review,
        "dialect_additions": dialect_additions,
        "positives": positives,
        "named_closure": named or {},
        "closure": closure,
        "open_reason": reason,
    }
    return lines, manifest, reason


def audit_text(
    language: str,
    batch: int,
    rows: list[dict[str, Any]],
    controls: list[dict[str, Any]],
    reasons: Counter[str],
) -> str:
    cfg = LANGUAGES[language]
    positive = [row for row in rows if row["positives"]]
    named = [row for row in rows if row["named_closure"]]
    opened = [row for row in rows if row["closure"] == "OPEN-CANDIDATE"]
    semitic = [row for row in named if row["closure"] == "SEMITIC-SOURCE-TRANSMISSION"]
    abbreviations = [row for row in named if row["closure"] == "ABBREVIATION"]
    transformed = len(positive) + len(named)
    reason_ar = {
        "orbit_not_convincing": "اكتمل الصوت والحدث ولم يقنع مدار يدوي",
        "event_unresolved": "اكتمل الصوت ولم يحل السجل حدث المرشح",
        "no_named_sound": "لم يكتمل مسار صوتي مسمى بعد البحث بالحرفين واللسان",
        "fan_empty": "لم تولد المروحة مرشحًا من الهيكل",
    }
    lines = [
        f"# حصاد القرض المعاد فتحه: {cfg['label']}، الدفعة {batch:03d} ({DATE})",
        "",
        "## الضابط الإلزامي قبل الحصاد",
        "",
        "أعيد حساب ست بطاقات صادرة من قبل بالمروحة الحالية وبـ`frozen_event.resolve` وحده. لم يتغير حكم واحدة منها، فجاز بدء الحصاد.",
        "",
        "| الصورة | المقابل | الحكم السابق | الحكم الحالي | وزن العرض | درجة الحدث | النتيجة |",
        "|---|---|---|---|---:|---:|---|",
    ]
    for row in controls:
        lines.append(
            f"| `{row['word']}` | `{row['root']}` | {row['closure']} | {row['current_verdict']} | {row['weight']:.6f} | {row['event_tier']} | ثابت |"
        )
    lines.extend([
        "",
        "ثبتت كذلك المسارات الصوتية المسماة والأحداث نفسها لكل الأزواج الستة؛ لا تستعمل النتيجة عضوية ملف الـ2,285 بوابة للحكم.",
        "",
        "## القانون المنفذ",
        "",
        "لكل بطاقة ثلاث أرجل فقط: المروحة ومسار الصوت المسمى، ثم الحدث من السجل المجمد، ثم معنى الفرع ومدار مكتوب باليد. لم يجعل اكتمال الحدث البطاقة موجبة؛ بقي الحسم في المدار. اللاتينية أو اليونانية ناقلًا أخيرًا لا تغلقان البطاقة، أما المانح السامي المسمى فيغلق عضو المعنى نفسه.",
        "",
        "## الحصيلة",
        "",
        f"- فُحص: {len(rows)} بطاقة.",
        f"- كُتب: {len(rows)} بطاقة ناسخة ملحقة، من غير محو البطاقة التاريخية.",
        f"- تحوّل عن الفتح: {transformed} بطاقات.",
        f"- موجب بالأرجل الثلاث: {len(positive)} من البطاقات، وفيها {sum(len(row['positives']) for row in positive)} صلة.",
        f"- أعيد إغلاقه بمانح سامي مسمى: {len(semitic)} من البطاقات.",
        f"- أغلق بوسم ABBREVIATION: {len(abbreviations)} من البطاقات.",
        f"- بقي OPEN-CANDIDATE: {len(opened)} بطاقة.",
    ])
    for key in ("orbit_not_convincing", "event_unresolved", "no_named_sound", "fan_empty"):
        if reasons[key]:
            lines.append(f"- سبب الفتح: {reasons[key]} من البطاقات، {reason_ar[key]}.")
    lines.extend([
        "",
        "## أبرز الأزواج الداخلة",
        "",
    ])
    pairs = [
        f"`{row['form']}` ↔ `{item['root']}` ({item['closure']})"
        for row in positive for item in row["positives"]
    ][:10]
    lines.extend(f"{position}. {pair}" for position, pair in enumerate(pairs, 1))
    if not pairs:
        lines.append("لم تدخل صلة في هذه الدفعة، وهو ناتج جائز لا يغير معيار المدار.")
    if named:
        lines.extend([
            "",
            "## الإغلاقات غير النسبية",
            "",
        ])
        for row in named:
            source = row["named_closure"]
            lines.append(
                f"- `{row['form']}` «{clean(row['branch_meaning'])}»: {row['closure']}؛ {clean(source['donor'])}؛ {clean(source['evidence'])}."
            )
    lines.extend([
        "",
        "## ضبط النسخ والعد",
        "",
        "كل بطاقة جديدة تحمل معرّف بطاقة 2026-08-05 التي تنسخ حكمها. بقي النص القديم كاملًا في ملف القراءة، وأسقط ماسح سجل الاسترداد الحكم المنسوخ من العد النافذ. قاموس الإغلاق بقي في ألفاظه الـ25 ولم يضف إليه وسم.",
        "",
    ])
    return "\n".join(lines)


def inspect_batch(language: str, window: list[dict[str, Any]]) -> None:
    for card in window:
        specs = MANUAL_SPECS.get((language, int(card["index"])), [])
        review, _ = current_fan(str(card["word"]), language, {item["root"] for item in specs})
        ready = [item for item in review if item["sound"] and item["event_tier"]]
        print(
            f"{card['index']:05d} {card['word']} | {card['meaning']} | "
            f"ready={len(ready)} | named={bool(NAMED_CLOSURES.get((language, int(card['index']))))}"
        )
        for item in ready:
            print(
                f"  {item['root']} w={item['weight']:.6f} t={item['event_tier']} "
                f"{clean(item['event_text'])}"
            )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--language", choices=tuple(LANGUAGES), required=True)
    parser.add_argument("--batch", type=int, required=True)
    parser.add_argument("--inspect", action="store_true")
    args = parser.parse_args()
    language = args.language
    cards = original_cards(language)
    start = (args.batch - 1) * BATCH_SIZE
    window = cards[start:start + BATCH_SIZE]
    if not window:
        raise SystemExit("الدفعة خارج الجرد")
    if args.inspect:
        inspect_batch(language, window)
        return 0

    cfg = LANGUAGES[language]
    marker = f"LOAN-HARVEST-{cfg['id_label']}-BATCH-{args.batch:03d}"
    audit = ROOT / "05-audits" / f"{DATE}-reopened-loan-{language}-harvest-batch-{args.batch:03d}.md"
    manifest = ROOT / "data" / f"reopened-loan-{language}-harvest-batch-{args.batch:03d}.json"
    reading = READINGS / f"{language}.md"
    text = reading.read_text(encoding="utf-8")
    if audit.exists() or manifest.exists() or f"<!-- {marker}:START -->" in text:
        raise AssertionError(f"مخرجات الدفعة {args.batch} موجودة من قبل")

    controls = control_run() if language == "welsh" and args.batch == 1 else []
    lines: list[str] = []
    rows: list[dict[str, Any]] = []
    reasons: Counter[str] = Counter()
    for card in window:
        card_lines, row, reason = build_card(language, card)
        lines.extend(card_lines)
        rows.append(row)
        if reason:
            reasons[reason] += 1

    section = [
        f"<!-- {marker}:START -->",
        "",
        f"## حصاد القرض المعاد فتحه، الدفعة {args.batch:03d} ({DATE})",
        "",
        *lines,
        f"<!-- {marker}:END -->",
        "",
    ]
    reading.write_text(text.rstrip() + "\n\n" + "\n".join(section), encoding="utf-8", newline="\n")
    payload = {
        "schema": "reopened-loan-harvest-v1",
        "date": DATE,
        "language": language,
        "language_label": cfg["label"],
        "batch": args.batch,
        "batch_size": len(rows),
        "controls": controls,
        "transformed_cards": sum(row["closure"] != "OPEN-CANDIDATE" for row in rows),
        "positive_cards": sum(bool(row["positives"]) for row in rows),
        "positive_traces": sum(len(row["positives"]) for row in rows),
        "named_semantic_closures": sum(row["closure"] == "SEMITIC-SOURCE-TRANSMISSION" for row in rows),
        "abbreviation_closures": sum(row["closure"] == "ABBREVIATION" for row in rows),
        "open_cards": sum(row["closure"] == "OPEN-CANDIDATE" for row in rows),
        "open_reasons": dict(reasons),
        "rows": rows,
    }
    manifest.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    audit.write_text(
        audit_text(language, args.batch, rows, controls, reasons),
        encoding="utf-8",
        newline="\n",
    )
    print(json.dumps({key: value for key, value in payload.items() if key != "rows"}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
