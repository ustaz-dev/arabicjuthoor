# -*- coding: utf-8 -*-
"""إعادة فحص بطاقات خشيم التي بقيت وراء بوابتين منسوختين.

المروحة والوزن والحدث آلية لأنها أدوات المشروع المجمّدة. أمّا المدار فلا
يولّده هذا الملف: لا يصدر موجب إلا إذا وُجد نصه حرفيًا في ``MANUAL_SPECS``.
كل تشغيل يكتب دفعة واحدة من 150 بطاقة فريدة، ويحفظ البطاقة القديمة كاملة
ويضيف بطاقة ناسخة ذات معرّف صريح يفهمه ماسح سجل الاسترداد.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import fan_any_script as F  # noqa: E402
import frozen_event as FE  # noqa: E402
import rebuild_khashim_indo_european_batches as K  # noqa: E402

READINGS = ROOT / "04-cross-linguistic" / "readings"
NETWORK = ROOT / "04-cross-linguistic" / "shift-network-draft.md"
PRIOR_ART = ROOT / "data" / "prior-art-extended-pairs.json"
SOURCE_GATE = "الصورة المذكورة لم تثبت في لقطة الطبقة التاريخية المختارة"
EVENT_GATE = "لم يوجد حدث مجمد لمرشح صالح داخل المروحة"
BATCH_SIZE = 150
DATE = "2026-08-14"

LANGUAGE_ORDER = (
    "middle-english",
    "old-latin",
    "ancient-greek",
    "old-english",
    "gothic",
    "welsh",
    "old-norse",
    "old-irish",
)
LANGUAGE_LABELS = K.ARABIC_LABELS

# هذه المدارات مكتوبة يدويًا. مدارات الجولة الجامعة السابقة تُستعمل بنصها،
# ولا تتحول أي نتيجة مستخرجة آليًا إلى هذا القاموس.
MANUAL_SPECS: dict[int, list[dict[str, str]]] = {
    index: [dict(spec) for spec in specs]
    for index, specs in K.MULTI_SPECS.items()
}
MANUAL_SPECS.update({
    36: [{
        "root": "جلي",
        "orbit": "اللمعان والسطوع يجعلان الشيء منجليًا مكشوفًا للنظر؛ فمعنى المصدر يصل إلى الاتساع والانكشاف في حدث `جلي` من جهة ظهور البياض بعد خفائه.",
    }],
    94: [{
        "root": "سبر",
        "orbit": "الرمح جسم دقيق ممتد يتصل بالمطعون ويمضي فيه ليبلغ غوره؛ فمعنى الطعن والثقب يصل إلى الامتداد الدقيق المتصل في حدث `سبر`.",
    }],
    247: [{
        "root": "متر",
        "orbit": "المتر يضبط طولًا ممتدًا بمقدار دقيق؛ فمعنى وحدة الطول يصل إلى الامتداد الموصوف بالدقة في حدث `متر`.",
    }],
})


def script_for(language: str) -> str:
    if language in {"ancient-greek", "old-latin", "old-irish", "welsh"}:
        return "latin"
    return "germanic"


def clean(value: Any) -> str:
    return " ".join(str(value or "").split()).replace("`", "ˋ")


def original_blocks() -> tuple[dict[int, str], dict[int, str]]:
    blocks: dict[int, str] = {}
    files: dict[int, str] = {}
    for language in K.TARGET_LANGUAGES:
        text = (READINGS / f"{language}.md").read_text(encoding="utf-8")
        for marker in re.finditer(r"^<!-- KHASHIM-IE:(\d+):[^>]+-->$", text, re.MULTILINE):
            start = text.rfind("\n### ", 0, marker.start())
            start = start + 1 if start >= 0 else marker.start()
            ends = [
                value for value in (
                    text.find("\n### ", marker.end()),
                    text.find("\n<!-- KHASHIM-IE-BATCH-", marker.end()),
                ) if value >= 0
            ]
            finish = min(ends) if ends else len(text)
            index = int(marker.group(1))
            blocks[index] = text[start:finish].strip()
            files[index] = language
    if len(blocks) != 1500:
        raise AssertionError(f"expected 1,500 original cards, found {len(blocks)}")
    return blocks, files


def form_index() -> dict[int, dict[str, Any]]:
    out: dict[int, dict[str, Any]] = {}
    for number in range(1, 6):
        path = ROOT / "data" / f"khashim-indo-european-batch-{number:03d}.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        for card in payload["rows"]:
            for form in card["forms"]:
                out[form["card_index"]] = form
    if set(out) != set(range(1, 1501)):
        raise AssertionError("the five Khashim manifests do not retain all original members")
    return out


def source_rows() -> list[dict[str, Any]]:
    payload = json.loads(PRIOR_ART.read_text(encoding="utf-8"))["rows"]
    return [
        row for row in payload
        if row.get("book") in {"khashim-journey1", "khashim-emperors"}
    ]


def targets(blocks: dict[int, str], files: dict[int, str]) -> list[int]:
    order = {language: position for position, language in enumerate(LANGUAGE_ORDER)}
    selected = [
        index for index, block in blocks.items()
        if SOURCE_GATE in block or EVENT_GATE in block
    ]
    selected.sort(key=lambda index: (order[files[index]], index))
    mentions = sum(
        (SOURCE_GATE in blocks[index]) + (EVENT_GATE in blocks[index])
        for index in selected
    )
    if len(selected) != 915 or mentions != 1141:
        raise AssertionError(
            f"dead-gate inventory drift: {len(selected)} unique cards, {mentions} gate mentions"
        )
    return selected


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


def current_fan(form: str, language: str, selected: set[str]) -> tuple[list[dict[str, Any]], int]:
    script = script_for(language)
    base = F.fan(form, script)
    ranked = F.rank(form, base, script)
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
        meaning = "✓" if root in selected else ("×" if route and event else "؟")
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
            "meaning": meaning,
        })
    return review, dialect_additions


def missing_sound_searches(form: str, language: str) -> list[str]:
    script = script_for(language)
    label = LANGUAGE_LABELS[language]
    lines = NETWORK.read_text(encoding="utf-8").splitlines()
    queries: list[str] = []
    seen: set[tuple[str, str]] = set()
    for source in F.skeleton(form, script):
        for arabic in F.FANS[script].get(source, ()):  # كل حرفَي الباب، لا أحدهما
            pair = (source, arabic)
            if pair in seen or pair in K.ROW_IDS:
                continue
            seen.add(pair)
            language_names = [part.strip() for part in label.split("/")]
            hits = sum(
                source.casefold() in line.casefold()
                and arabic in line
                and any(name.casefold() in line.casefold() for name in language_names)
                for line in lines
            )
            queries.append(
                f"`{source}` + `{arabic}` + «{label}» في عمود الشاهد، النتائج الحرفية {hits}"
            )
    return queries or [f"الهيكل الكامل + «{label}» في عمود الشاهد، النتائج الحرفية 0"]


def closure_for(root: str) -> str:
    letters = re.findall(r"[ء-ي]", root)
    return "NUCLEUS-TRACE" if len(letters) == 2 else "ROOT-TRACE"


def render_candidate(item: dict[str, Any]) -> str:
    dialect = f"،له={item['dialect_label']}" if item["dialect_label"] else ""
    return (
        f"`{item['root']}`[و{item['weight']:.6f}،"
        f"ص{'✓' if item['sound'] else '×'}،ح{'✓' if item['event_tier'] else '×'}،"
        f"د{item['event_tier']}،م{item['meaning']}{dialect}]"
    )


def branch_line(block: str) -> str:
    match = re.search(r"^- الكلمة في الفرع ومعناها: (.*)$", block, re.MULTILINE)
    return match.group(1).strip() if match else "(لا مدخل مطابق في لقطة الفرع التاريخية)."


def build_card(
    index: int,
    language: str,
    block: str,
    form: dict[str, Any],
    raw_rows: list[dict[str, Any]],
) -> tuple[list[str], dict[str, Any], str]:
    word = str(form["form"])
    specs = MANUAL_SPECS.get(index, [])
    selected_roots = {spec["root"] for spec in specs}
    if len(selected_roots) != len(specs):
        raise AssertionError(f"duplicate manual root in card {index}")
    review, dialect_additions = current_fan(word, language, selected_roots)
    by_root = {item["root"]: item for item in review}
    claims = [raw_rows[position] for position in form["source_rows"]]
    source_meanings = " | ".join(
        f"`{clean(item.get('foreign'))}` «{clean(item.get('foreign_sense'))}» "
        f"[{clean(item.get('book'))} ص.{clean(item.get('page'))}]"
        for item in claims
    )
    source_claims = " | ".join(
        f"`{clean(item.get('foreign'))}` «{clean(item.get('foreign_sense'))}» ↔ "
        f"`{clean(item.get('arabic_root'))}`؛ {clean(item.get('arabic_gloss'))} "
        f"[{clean(item.get('book'))} ص.{clean(item.get('page'))}]"
        for item in claims
    )
    gates = []
    if SOURCE_GATE in block:
        gates.append("بوابة ثبوت الصورة في اللقطة")
    if EVENT_GATE in block:
        gates.append("بوابة عضوية ملف الـ2,285")

    lines = [
        f"### بطاقة إعادة فحص البوابتين الميتتين: `{clean(word)}`؛ DG-{index:04d}",
        f"<!-- DEAD-GATE-REREVIEW:KHASHIM-IE:{index} -->",
        f"- سطر النسخ: `KHASHIM-IE:{index}` ← `DG-{index:04d}`؛ النص التاريخي باق في موضعه، وهذا الحكم هو النافذ بتاريخ {DATE}.",
        f"- البوابة أو البوابتان المنسوختان في البطاقة القديمة: {'؛ '.join(gates)}؛ لم تدخلا الحكم الجديد.",
        "- نسبة المصدر: الصورة والمعنى والجذر المقترح والشرح لعلي فهمي خشيم؛ المروحة والمسار والحدث والمدار والحكم أعمال المشروع.",
        f"- اللسان: {LANGUAGE_LABELS[language]}؛ الطبقة: استكشاف.",
        f"- نقل المصدر بلا رتوش: {source_claims}",
        f"- معنى الفرع بلا رتوش: {branch_line(block)} وعند غياب اللقطة يبقى نقل المصدر المسمى صالحًا: {source_meanings}.",
        f"- الخطوة صفر: الصورة `{clean(word)}`؛ الرسم `{script_for(language)}`؛ الهياكل الحالية `{' / '.join(skeleton_variants(word, script_for(language)).split('|')) or '∅'}`.",
        f"- المروحة الكاملة من `fan_any_script.fan` مرتبة بـ`fan_any_script.rank`: {('، '.join(render_candidate(item) for item in review) or 'لا مرشح قابل للتوليد')}. الوزن ترتيب لا حكم؛ د=درجة الحدث؛ م× يعني أن المدار فُحص ولم يقنع.",
        f"- فحص `fan_with_dialect`: أضاف {dialect_additions} صورة موسومة بعد الفصيح ولم يحذف الفصيح.",
    ]

    positives: list[dict[str, Any]] = []
    for spec in specs:
        root = spec["root"]
        orbit = clean(spec.get("orbit"))
        if not orbit or len(orbit) < 45:
            raise AssertionError(f"manual orbit is absent or too short: {index}:{root}")
        candidate = by_root.get(root)
        if not candidate:
            raise AssertionError(f"manual positive absent from current full fan: {index}:{root}")
        if not candidate["sound"]:
            raise AssertionError(f"manual positive lacks a named sound route: {index}:{root}")
        if not candidate["event_tier"]:
            raise AssertionError(f"manual positive lacks frozen event descent: {index}:{root}")
        if candidate["event_tier"] == 4 and len(orbit) < 95:
            raise AssertionError(f"tier-four orbit needs a fuller hand-written bridge: {index}:{root}")
        closure = closure_for(root)
        lines.extend([
            f"- المقابل المنتخب: `{root}`؛ وزن العرض {candidate['weight']:.6f}.",
            f"- مسار الصوت المسمى: {candidate['sound_route']}.",
            f"- ما فُتش في الشبكة بالحرفين وباسمي اللسان: {'؛ '.join(candidate['sound_searches'])}.",
            f"- الحدث من السجل المجمّد كما هو (درجة {candidate['event_tier']}، {candidate['event_tier_ar']}): «{candidate['event_text']}» [{candidate['event_source']}]."
            + (f" {candidate['event_note']}." if candidate["event_note"] else ""),
            f"- المدار المكتوب باليد: {orbit}",
            f"- نتيجة الأرجل الثلاث للمقابل `{root}`: **{closure} (استكشاف)**.",
        ])
        positives.append({
            "root": root,
            "closure": closure,
            "orbit": orbit,
            **{key: candidate[key] for key in (
                "weight", "sound_route", "sound_searches", "event_tier",
                "event_tier_ar", "event_source", "event_text", "event_note",
            )},
        })

    if positives:
        closures = list(dict.fromkeys(item["closure"] for item in positives))
        closure = " + ".join(closures)
        pairs = "، ".join(f"`{item['root']}`={item['closure']}" for item in positives)
        lines.extend([
            f"- الحكم (استكشاف): **{closure} (استكشاف)**؛ {pairs}.",
            f"- حقل النقص، خارج الحكم: {'الصورة من نقل المصدر ولم تثبت في لقطتنا [SOURCE-GAP].' if SOURCE_GATE in block else 'لا نقص متعلق بالبوابتين المنسوختين.'}",
            f"- حالة الإغلاق: {closure}.",
            "",
        ])
        open_reason = ""
    else:
        ready = [item for item in review if item["sound"] and item["event_tier"]]
        sounded = [item for item in review if item["sound"]]
        if ready:
            reason_key = "ORBIT-NOT-CONVINCING"
            required = "بقي المدار البشري مفتوحًا بعد عرض المروحة كلها"
            search_line = "لم يعلن صف ناقص؛ وُجدت مسارات صوتية مسماة، وكان الامتناع في رجل المدار وحدها."
        elif sounded:
            reason_key = "EVENT-UNRESOLVED"
            required = "لم يحل محلل frozen_event حدثًا لمرشح ذي مسار صوتي مسمى؛ بقي المدار البشري مفتوحًا"
            search_line = "لم يعلن صف ناقص؛ وُجد مسار صوتي مسمى، لكن محلل الحدث لم يحل المرشح."
        elif review:
            reason_key = "NO-NAMED-SOUND"
            required = "لم يكتمل مسار صوتي مسمى لأي مرشح داخل المروحة؛ بقي المدار البشري مفتوحًا"
            search_line = "؛ ".join(missing_sound_searches(word, language))
        else:
            reason_key = "FAN-EMPTY"
            required = "لم تولد المروحة مرشحًا من الهيكل المثبت؛ بقي المدار البشري مفتوحًا"
            search_line = "لم يعلن صف ناقص لأن الأداة لم تولد مرشحًا يُفحص في الشبكة."
        lines.extend([
            f"- المدار المكتوب باليد: لم يقنع القارئ مدار لمرشح مكتمل الأرجل؛ بقيت البطاقة مفتوحة ولم يُنشأ لها مدار آلي.",
            f"- ما فُتش قبل إعلان نقص صف: {search_line}",
            "- الحكم (استكشاف): **غير صادر (استكشاف)**.",
            f"- عائق: النوع=OPEN-CANDIDATE؛ يتطلب={required}",
            f"- حقل النقص، خارج الحكم: {'الصورة من نقل المصدر ولم تثبت في لقطتنا [SOURCE-GAP].' if SOURCE_GATE in block else 'لا نقص متعلق ببوابة اللقطة.'}",
            "- حالة الإغلاق: OPEN-CANDIDATE.",
            "",
        ])
        closure = "OPEN-CANDIDATE"
        open_reason = reason_key

    manifest = {
        "card_id": f"DG-{index:04d}",
        "supersedes": f"KHASHIM-IE:{index}",
        "original_index": index,
        "language": language,
        "form": word,
        "source_rows": form["source_rows"],
        "dead_gates": gates,
        "fan_script": script_for(language),
        "fan_candidates": review,
        "dialect_additions": dialect_additions,
        "positives": positives,
        "closure": closure,
        "open_reason": open_reason,
    }
    return lines, manifest, open_reason


def audit_text(
    batch: int,
    rows: list[dict[str, Any]],
    gate_mentions: int,
    reason_counts: Counter[str],
) -> str:
    positive = [row for row in rows if row["positives"]]
    opened = [row for row in rows if not row["positives"]]
    traces = sum(len(row["positives"]) for row in positive)
    pairs = [
        f"`{row['form']}` ↔ `{item['root']}` ({item['closure']})"
        for row in positive for item in row["positives"]
    ][:10]
    reason_ar = {
        "ORBIT-NOT-CONVINCING": "لم يقنع مدار يدوي بعد اكتمال الصوت والحدث",
        "EVENT-UNRESOLVED": "لم يحل محلل الحدث مرشحًا ذا صوت مسمى",
        "NO-NAMED-SOUND": "لم يكتمل مسار صوتي مسمى بعد البحث بالحرفين واللسان",
        "FAN-EMPTY": "لم تولد المروحة مرشحًا من الهيكل",
    }
    lines = [
        f"# إعادة فحص البوابتين الميتتين، الدفعة {batch:03d} ({DATE})",
        "",
        "## النطاق والقانون",
        "",
        f"فُحصت {len(rows)} بطاقة فريدة بالترتيب الذي يقدّم الإنجليزية الوسطى. تحمل هذه البطاقات {gate_mentions} ظهورًا للبوابتين القديمتين؛ قد تحمل البطاقة الواحدة العبارتين معًا، ولذلك لا يساوي عدد الظهور عدد البطاقات.",
        "",
        "الحكم بثلاث أرجل لا رابعة لها: مروحة `fan_any_script.fan` ومسار صوت مسمى، ثم حدث `frozen_event.resolve` بدرجته ومصدره، ثم معنى الفرع ومدار مكتوب باليد. غياب الصورة عن اللقطة `SOURCE-GAP` في حقل النقص لا في الحكم. لا يولد الباني مدارًا.",
        "",
        "## الحصيلة",
        "",
        f"- فُحص: {len(rows)} بطاقة.",
        f"- تحوّل إلى حكم موجب: {len(positive)} بطاقة، وفيها {traces} صلة.",
        f"- بقي `OPEN-CANDIDATE`: {len(opened)} بطاقة.",
    ]
    for key, count in reason_counts.items():
        if count:
            lines.append(f"- سبب الفتح `{key}`: {count}، {reason_ar[key]}.")
    lines.extend([
        "",
        "## أبرز الأزواج الداخلة",
        "",
    ])
    lines.extend(f"{position}. {pair}" for position, pair in enumerate(pairs, 1))
    if not pairs:
        lines.append("لم يدخل موجب في هذه الدفعة، وهو ناتج جائز لا يغيّر معيار المدار.")
    lines.extend([
        "",
        "## ضبط النسخ والعد",
        "",
        "كل بطاقة جديدة تحمل معرّف البطاقة التاريخية التي تنسخ حكمها. بقي النص القديم في ملف القراءة كاملًا، وأسقط ماسح السجل حكمه المنسوخ من العد النافذ. قاموس الإغلاق لم يتغير.",
        "",
    ])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch", type=int, required=True)
    args = parser.parse_args()
    if not 1 <= args.batch <= 7:
        raise SystemExit("batch must be between 1 and 7")

    blocks, files = original_blocks()
    forms = form_index()
    raw_rows = source_rows()
    selected = targets(blocks, files)
    window = selected[(args.batch - 1) * BATCH_SIZE:args.batch * BATCH_SIZE]
    expected = 15 if args.batch == 7 else 150
    if len(window) != expected:
        raise AssertionError(f"batch {args.batch} expected {expected}, got {len(window)}")

    marker = f"DEAD-GATE-REREVIEW-BATCH-{args.batch:03d}"
    audit = ROOT / "05-audits" / f"{DATE}-dead-gate-rereview-batch-{args.batch:03d}.md"
    manifest = ROOT / "data" / f"dead-gate-rereview-batch-{args.batch:03d}.json"
    if audit.exists() or manifest.exists():
        raise AssertionError(f"batch {args.batch} output already exists")

    by_language: dict[str, list[str]] = defaultdict(list)
    report_rows: list[dict[str, Any]] = []
    reasons: Counter[str] = Counter()
    gate_mentions = 0
    for index in window:
        language = files[index]
        card_lines, row, reason = build_card(
            index, language, blocks[index], forms[index], raw_rows
        )
        by_language[language].extend(card_lines)
        report_rows.append(row)
        if reason:
            reasons[reason] += 1
        gate_mentions += (SOURCE_GATE in blocks[index]) + (EVENT_GATE in blocks[index])

    for language, lines in by_language.items():
        path = READINGS / f"{language}.md"
        text = path.read_text(encoding="utf-8")
        if f"<!-- {marker}:START -->" in text:
            raise AssertionError(f"batch marker already present in {path}")
        section = [
            f"<!-- {marker}:START -->",
            "",
            f"## إعادة فحص البوابتين الميتتين، الدفعة {args.batch:03d} ({DATE})",
            "",
            *lines,
            f"<!-- {marker}:END -->",
            "",
        ]
        path.write_text(text.rstrip() + "\n\n" + "\n".join(section), encoding="utf-8", newline="\n")

    payload = {
        "schema": "dead-gate-rereview-v1",
        "date": DATE,
        "batch": args.batch,
        "batch_size": len(report_rows),
        "gate_mentions": gate_mentions,
        "ordering": list(LANGUAGE_ORDER),
        "positive_cards": sum(bool(row["positives"]) for row in report_rows),
        "positive_traces": sum(len(row["positives"]) for row in report_rows),
        "open_cards": sum(not row["positives"] for row in report_rows),
        "open_reasons": dict(reasons),
        "rows": report_rows,
    }
    manifest.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    audit.write_text(
        audit_text(args.batch, report_rows, gate_mentions, reasons),
        encoding="utf-8",
        newline="\n",
    )
    print(json.dumps({key: value for key, value in payload.items() if key != "rows"}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
