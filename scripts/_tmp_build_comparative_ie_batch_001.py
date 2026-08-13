Exit code: 0
Wall time: 0.7 seconds
Output:
# -*- coding: utf-8 -*-
"""One-shot builder for comparative Indo-European batch 001."""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from collections import Counter, OrderedDict, defaultdict
from pathlib import Path
from types import SimpleNamespace
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "data" / "prior-art-extended-pairs.json"
ASSIGNMENTS = ROOT / "data" / "comparative-language-assignments.json"
MANIFEST = ROOT / "data" / "comparative-indo-european-batch-001.json"
AUDIT = ROOT / "05-audits" / "2026-08-14-comparative-indo-european-batch-001.md"
READINGS = ROOT / "04-cross-linguistic" / "readings"
BATCH = 1
CATEGORY = "cross-european"
OFFSET = 0
LIMIT = 300
START = "<!-- COMPARATIVE-IE-BATCH-001:START -->"
END = "<!-- COMPARATIVE-IE-BATCH-001:END -->"
ALLOWED = (
    "ancient-greek", "gothic", "middle-english", "old-english",
    "old-irish", "old-latin", "old-norse", "welsh",
)
LABELS = {
    "ancient-greek": "اليونانيّة القديمة/Ancient Greek",
    "gothic": "القوطيّة/Gothic",
    "middle-english": "الإنجليزيّة الوسطى/Middle English",
    "old-english": "الإنجليزيّة القديمة/Old English",
    "old-irish": "الإيرلنديّة القديمة/Old Irish",
    "old-latin": "اللاتينيّة القديمة/Old Latin",
    "old-norse": "النورديّة القديمة/Old Norse",
    "welsh": "الويلزيّة/Welsh",
}

# Reuse the frozen fan/event helpers without reviving that builder's main.
base = subprocess.check_output(
    ["git", "show", "2882fc0:scripts/_tmp_build_jassem_ie_batch_001.py"],
    cwd=ROOT, text=True, encoding="utf-8",
)
namespace = {"__name__": "_comparative_base", "__file__": str(ROOT / "scripts" / "_base.py")}
exec(compile(base, "jassem-base", "exec"), namespace)
B = SimpleNamespace(**namespace)
F = B.F
sys.path.insert(0, str(ROOT / "scripts"))
import frozen_event as FE  # noqa: E402


def norm(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip()).casefold()


def clean(value: Any) -> str:
    return " ".join(str(value or "").split()).replace("`", "ˋ")


def script_for(language: str) -> str:
    return "latin" if language in {"ancient-greek", "old-latin", "old-irish", "welsh"} else "germanic"


def source_key(index: int, row: dict[str, Any]) -> str:
    raw = json.dumps([
        index, row.get("tongue"), norm(row.get("foreign")), clean(row.get("foreign_sense")),
        clean(row.get("arabic_root")), clean(row.get("arabic_gloss")), row.get("source"), row.get("page"),
    ], ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]


def claim(index: int, row: dict[str, Any], assignment: dict[str, Any]) -> dict[str, Any]:
    return {
        "source_row_index": index,
        "source_row_key": source_key(index, row),
        "foreign": row.get("foreign"),
        "foreign_sense": row.get("foreign_sense"),
        "tongue_ar": row.get("tongue_ar"),
        "arabic_root": row.get("arabic_root"),
        "arabic_gloss": row.get("arabic_gloss"),
        "source": row.get("source"),
        "book": row.get("book"),
        "page": row.get("page"),
        "assigned_language": assignment["language"],
        "assignment_reason": assignment["reason"],
    }


def target_id(card: dict[str, Any]) -> str:
    return card.get("merged_card_id") or card.get("card_id")


def card_forms(card: dict[str, Any]) -> list[str]:
    out = []
    for item in card.get("forms", []):
        value = item.get("form") if isinstance(item, dict) else item
        if value:
            out.append(str(value))
    if not out and card.get("head"):
        out.append(str(card["head"]))
    for supplement in card.get("comparative_supplements", []):
        for item in supplement.get("forms", []):
            if item.get("form"):
                out.append(str(item["form"]))
    for supplement in card.get("later_comparative_supplements", []):
        for item in supplement.get("forms", []):
            if item.get("form"):
                out.append(str(item["form"]))
    return out


def embedded_rows(card: dict[str, Any]) -> set[int]:
    out = set(card.get("source_rows", []))
    for item in card.get("forms", []):
        if isinstance(item, dict):
            out.update(item.get("source_rows", []))
    return out


def candidate_review(form: str, script: str, positive: dict[str, Any] | None) -> tuple[list[dict[str, Any]], int]:
    base = F.fan(form, script)
    ranked = F.rank(form, base, script)
    labels = {root: "فصيح" for root in base}
    dialect_additions = 0
    if positive is None:
        for root, label in F.fan_with_dialect(form, script):
            if root not in labels:
                labels[root] = label
                dialect_additions += 1
    ranked_map = {root: weight for root, weight in ranked}
    roots = list(base) + [root for root in labels if root not in set(base)]
    roots.sort(key=lambda root: (-ranked_map.get(root, 0.0), list(labels).index(root)))
    selected = positive["root"] if positive else None
    if selected and selected not in labels:
        raise AssertionError(f"selected root absent from full fan: {form}:{selected}")
    out = []
    for root in roots:
        event = FE.resolve(root)
        out.append({
            "root": root,
            "weight": float(ranked_map.get(root, 0.0)),
            "sound": "✓",
            "event": "✓" if event else "×",
            "event_tier": event.tier if event else 0,
            "event_tier_ar": event.tier_ar if event else None,
            "event_source": event.source if event else None,
            "event_text": event.text if event else None,
            "event_note": event.note if event else None,
            "meaning": "✓" if root == selected else ("×" if event else "؟"),
            "dialect_label": None if labels[root] == "فصيح" else labels[root],
        })
    return out, dialect_additions


def fan_for(form: str, language: str, positive: dict[str, Any] | None) -> dict[str, Any]:
    script = script_for(language)
    review, dialect = candidate_review(form, script, positive)
    positives = []
    if positive:
        event = FE.resolve(positive["root"])
        if not event:
            raise AssertionError(f"missing frozen event for {form}:{positive['root']}")
        positives.append({
            **positive,
            "frozen_event": event.text,
            "event_source": event.source,
            "event_tier": event.tier,
            "event_tier_ar": event.tier_ar,
            "event_note": event.note,
        })
    return {
        "form": form,
        "normalized_form": norm(form),
        "script": script,
        "skeleton": F.skeleton(form, script),
        "fan_review": review,
        "dialect_additions": dialect,
        "positives": positives,
    }


def fan_text(item: dict[str, Any]) -> str:
    return "، ".join(
        f"`{candidate['root']}`[و{candidate['weight']:.6f}،ص{candidate['sound']}،ح{candidate['event']}،د{candidate['event_tier']}،م{candidate['meaning']}{'،له=' + candidate['dialect_label'] if candidate['dialect_label'] else ''}]"
        for candidate in item["fan_review"]
    ) or "لا مرشح قابل للتوليد من الهيكل"


def locate_block(text: str, card_id: str) -> tuple[int, int]:
    markers = [
        f"<!-- KHASHIM-IE-MERGED:{card_id} -->", f"<!-- KHASHIM-IE-CONT:{card_id} -->",
        f"<!-- JASSEM-IE:{card_id} -->", f"<!-- COMPARATIVE-IE:{card_id} -->",
    ]
    marker = next((item for item in markers if item in text), None)
    if not marker:
        raise AssertionError(f"reading marker missing for {card_id}")
    at = text.index(marker)
    start = text.rfind("\n### ", 0, at)
    start = start + 1 if start >= 0 else at
    finish = text.find("\n### ", at)
    if finish < 0:
        finish = len(text)
    return start, finish


def append_supplement(text: str, supplement: dict[str, Any]) -> str:
    card_id = supplement["target_card_id"]
    start, finish = locate_block(text, card_id)
    block = text[start:finish]
    sm = f"<!-- COMPARATIVE-IE-SUPPLEMENT-001:{card_id}:START -->"
    em = f"<!-- COMPARATIVE-IE-SUPPLEMENT-001:{card_id}:END -->"
    block = re.sub(rf"\n?{re.escape(sm)}.*?{re.escape(em)}\n?", "\n", block, flags=re.DOTALL)
    claims = " | ".join(
        f"صف {row['source_row_index']}: `{clean(row['foreign'])}`؛ «{clean(row['foreign_sense'])}» ↔ `{clean(row['arabic_root'])}`؛ {clean(row['arabic_gloss'])} [{clean(row['source'])}، ص{clean(row['page'])}]"
        for row in supplement["source_claims"]
    )
    lines = [
        sm,
        f"- إلحاق المقارنات، الدفعة 001: {claims}.",
        "- الإلحاق في البطاقة القائمة يمنع تكرار صور الكلمة عبر الكتب؛ لا تغيّر أولوية المؤلف الحكم السابق.",
    ]
    for item in supplement["forms"]:
        lines.extend([
            f"- صورة الإلحاق `{clean(item['form'])}`؛ اللسان المسند {LABELS[supplement['target_language']]}؛ الهيكل `{'-'.join(item['skeleton']) or '∅'}`.",
            f"- مروحة صورة `{clean(item['form'])}` كاملة ومرتبة بـ`F.rank`: {fan_text(item)}. الوزن ترتيب لا حكم.",
            f"- فحص `fan_with_dialect` بعد عجز الفصحى: أضاف {item['dialect_additions']} صورة موسومة.",
        ])
    lines.append(em)
    block = block.rstrip() + "\n" + "\n".join(lines) + "\n"
    return text[:start] + block + text[finish:]


def render_card(card: dict[str, Any]) -> list[str]:
    claims = " | ".join(
        f"صف {row['source_row_index']}: `{clean(row['foreign'])}`؛ «{clean(row['foreign_sense'])}» ↔ `{clean(row['arabic_root'])}`؛ {clean(row['arabic_gloss'])} [{clean(row['source'])}، ص{clean(row['page'])}]"
        for row in card["source_claims"]
    )
    lines = [
        f"### بطاقة المقارنات: `{clean(card['head'])}`؛ {card['card_id']}",
        f"<!-- COMPARATIVE-IE:{card['card_id']} -->",
        f"- وحدة البطاقة: أسرة لفظية واحدة بصورها {', '.join('`' + clean(item['form']) + '`' for item in card['forms'])}؛ صفوف المصدر {card['source_rows']}.",
        "- نسبة المصدر: الصورة والمعنى والجذر المقترح والشرح لخشيم؛ الإسناد اللساني والمروحة والحدث والمدار والحكم أعمال المشروع.",
        f"- اللسان المسند: {LABELS[card['language']]}؛ الإسناد اتبع صورة المادة، لا موضعها في الملف.",
        f"- نقل المصدر: {claims}.",
    ]
    for item in card["forms"]:
        lines.extend([
            f"- الخطوة صفر لصورة `{clean(item['form'])}`: الرسم `{item['script']}`؛ الهيكل `{'-'.join(item['skeleton']) or '∅'}`؛ لا يشترط ثبوت الصورة في لقطة محلية.",
            f"- المروحة الكاملة لصورة `{clean(item['form'])}`، مرتبة بـ`F.rank`: {fan_text(item)}. الوزن ترتيب لا حكم؛ ح× غياب حدث مجمّد، وم× فشل المدار.",
            f"- فحص `fan_with_dialect` عند عجز الفصحى: أضاف {item['dialect_additions']} صورة موسومة.",
        ])
        for positive in item["positives"]:
            lines.extend([
                f"- المقابل المنتخب لصورة `{clean(item['form'])}`: `{positive['root']}`؛ مسار الصوت المسمى: {positive['sound_route']}.",
                f"- ما فُتش في الشبكة: {'؛ '.join(positive['sound_searches'])}.",
                f"- الحدث المجمّد كما هو (درجة {positive['event_tier']}، {positive['event_tier_ar']}): «{positive['frozen_event']}» [{positive['event_source']}].{' ' + positive['event_note'] if positive['event_note'] else ''}",
                f"- معنى الفرع: {positive['branch_meaning']}.",
                f"- المدار المكتوب: {positive['orbit']}",
            ])
    positives = [positive for item in card["forms"] for positive in item["positives"]]
    if positives:
        issued = "، ".join(f"`{item['root']}`={item['closure']}" for item in positives)
        lines.append(f"- الحكم (استكشاف): **{card['closure']} (استكشاف)**؛ {issued}.")
    else:
        lines.extend([
            "- المدار المكتوب: فُحصت مرشحات المراوح ذات الحدث المجمّد، ولم يثبت منها مدار ينسخ معنى الفرع؛ اقتراح المؤلف لا يعوّض رجل المعنى.",
            "- الحكم (استكشاف): **غير صادر (استكشاف)**.",
        ])
    lines.extend([
        "- حقل النقص، خارج الحكم: غياب الصورة من اللقطة `SOURCE-GAP` فقط، لا رفض.",
        f"- حالة الإغلاق: {card['closure']}.",
        "",
    ])
    return lines


MANUAL_TARGET = {
    95: "KIE-M0048", 96: "KIE-M0048", 99: "KIE-M0048",
    183: "KIE-M0085", 293: "KIE-M0118", 348: "KIE-M0133", 350: "KIE-M0133",
    433: "KIE-M0158", 437: "KIE-M0160", 438: "KIE-M0160", 440: "KIE-M0161",
    447: "KIE-M0162", 680: "KIE-M0274", 733: "KIE-M0299", 734: "KIE-M0299",
    735: "KIE-M0299", 739: "KIE-M0300", 747: "KIE-M0302", 776: "KIE-M0320",
    831: "KIE-M0342", 866: "KIE-M0355", 870: "KIE-M0356", 880: "KIE-M0363",
    883: "KIE-M0365",
}
NEW_GROUP = {
    245: "ammoniac", 247: "ammoniac", 248: "ammoniac",
    608: "clove", 609: "clove", 610: "clove", 611: "clove",
    753: "safian", 755: "safian",
}
POSITIVE = {
    "bourge": {
        "root": "برج", "closure": "ROOT-TRACE",
        "branch_meaning": "`bourge` في نقل المصدر: برج أو قلعة أو مدينة محصنة",
        "orbit": "الحصن والقلعة بناء بارز قوي من بين ما يكتنفه؛ فيلتقي معنى المصدر بحدث `برج` الظاهر.",
        "sound_route": "b↔ب=`IDN-05`؛ r↔ر=`IDN-01`؛ g↔ج=`IDN-08`؛ تعرية e النهائية",
        "sound_searches": ["`b` + `ب` + «اللاتينيّة القديمة/Old Latin»", "`r` + `ر` + «اللاتينيّة القديمة/Old Latin»", "`g` + `ج` + «اللاتينيّة القديمة/Old Latin»"],
    },
    "furka": {
        "root": "فرق", "closure": "ROOT-TRACE",
        "branch_meaning": "`furka` في نقل المصدر: شوكة أو شُعبة أو فرع أو أداة متشعبة",
        "orbit": "الشوكة المتشعبة تنفصل إلى فرعين؛ فهي هيئة ظاهرة لحدث `فرق` في الفصل الواصل إلى العمق.",
        "sound_route": "f↔ف=`IDN-06`؛ r↔ر=`IDN-01`؛ k↔ق=`GUT-01`",
        "sound_searches": ["`f` + `ف` + «الإنجليزيّة الوسطى/Middle English»", "`r` + `ر` + «الإنجليزيّة الوسطى/Middle English»", "`k` + `ق` + «الإنجليزيّة الوسطى/Middle English»"],
    },
}


def main() -> int:
    source_text = SOURCE.read_text(encoding="utf-8")
    source_rows = json.loads(source_text)["rows"]
    assignment_payload = json.loads(ASSIGNMENTS.read_text(encoding="utf-8"))
    assignment_by_index = {item["source_row_index"]: item for item in assignment_payload["rows"]}
    category_rows = [(index, row) for index, row in enumerate(source_rows) if row.get("tongue") == CATEGORY]
    selected = category_rows[OFFSET:OFFSET + LIMIT]
    if len(selected) != LIMIT:
        raise AssertionError(f"expected {LIMIT}, got {len(selected)}")

    docs: dict[Path, dict[str, Any]] = {}
    locations: dict[str, tuple[Path, dict[str, Any], str]] = {}
    exact_index: dict[str, list[str]] = defaultdict(list)
    for pattern, kind in (("khashim-indo-european-batch-*.json", "khashim"), ("jassem-indo-european-batch-*.json", "jassem"), ("comparative-indo-european-batch-*.json", "comparative")):
        for path in sorted((ROOT / "data").glob(pattern)):
            if path == MANIFEST:
                continue
            payload = json.loads(path.read_text(encoding="utf-8"))
            docs[path] = payload
            for card in payload.get("rows", []):
                cid = target_id(card)
                locations[cid] = (path, card, kind)
                for form in card_forms(card):
                    exact_index[norm(form)].append(cid)

    reading_texts = {language: (READINGS / f"{language}.md").read_text(encoding="utf-8") for language in ALLOWED}
    for language, text in reading_texts.items():
        text = re.sub(rf"\n?{re.escape(START)}.*?{re.escape(END)}\n?", "\n", text, flags=re.DOTALL)
        text = re.sub(r"\n?<!-- COMPARATIVE-IE-SUPPLEMENT-001:[^:]+:START -->.*?<!-- COMPARATIVE-IE-SUPPLEMENT-001:[^:]+:END -->\n?", "\n", text, flags=re.DOTALL)
        reading_texts[language] = text
    for payload in docs.values():
        for card in payload.get("rows", []):
            for field in ("comparative_supplements", "later_comparative_supplements"):
                if field in card:
                    card[field] = [item for item in card[field] if item.get("batch") != BATCH]
                    if not card[field]:
                        card.pop(field)

    embedded = []
    supplement_claims: dict[str, list[dict[str, Any]]] = defaultdict(list)
    new_groups: OrderedDict[tuple[str, str], list[dict[str, Any]]] = OrderedDict()
    selected_indices = []
    for index, row in selected:
        assignment = assignment_by_index[index]
        if assignment["language"] not in ALLOWED:
            raise AssertionError(f"unassigned cross-European row {index}")
        selected_indices.append(index)
        item = claim(index, row, assignment)
        hits = exact_index.get(norm(row.get("foreign")), [])
        manual = MANUAL_TARGET.get(index)
        cid = manual
        if cid is None and hits:
            same_language = [candidate for candidate in hits if locations[candidate][1]["language"] == assignment["language"]]
            cid = (same_language or hits)[0]
        if cid:
            if cid not in locations:
                raise AssertionError(f"manual target missing: {index}:{cid}")
            target_path, card, kind = locations[cid]
            if manual and card["language"] != assignment["language"]:
                raise AssertionError(f"manual target language mismatch: {index}:{assignment['language']}->{card['language']}")
            if index in embedded_rows(card):
                embedded.append({
                    **item, "target_card_id": cid, "target_manifest": target_path.name,
                    "target_language": card["language"], "target_kind": kind,
                    "reason": "the frozen Khashim card already embeds this exact comparative source row and its full fan",
                })
            else:
                supplement_claims[cid].append(item)
            continue
        group = NEW_GROUP.get(index, norm(row.get("foreign")))
        new_groups.setdefault((group, assignment["language"]), []).append(item)

    supplements = []
    for cid, claims in supplement_claims.items():
        path, card, kind = locations[cid]
        forms = []
        for by_form in OrderedDict((norm(item["foreign"]), item["foreign"]) for item in claims).values():
            forms.append(fan_for(str(by_form), card["language"], None))
        supplement = {
            "batch": BATCH,
            "category": CATEGORY,
            "source": "data/prior-art-extended-pairs.json",
            "source_rows": [item["source_row_index"] for item in claims],
            "source_claims": claims,
            "forms": forms,
            "target_card_id": cid,
            "target_manifest": path.name,
            "target_language": card["language"],
            "target_kind": kind,
            "reason": "exact form or same clearly bounded lexical form-family; appended to the one existing card",
        }
        supplements.append(supplement)
        field = "comparative_supplements" if kind == "khashim" else "later_comparative_supplements"
        card.setdefault(field, []).append(supplement)
        reading_texts[card["language"]] = append_supplement(reading_texts[card["language"]], supplement)

    new_cards = []
    for ordinal, ((group, language), claims) in enumerate(new_groups.items(), 1):
        forms = []
        for form in OrderedDict((norm(item["foreign"]), str(item["foreign"])) for item in claims).values():
            forms.append(fan_for(form, language, POSITIVE.get(norm(form))))
        positives = [positive for item in forms for positive in item["positives"]]
        closures = list(dict.fromkeys(item["closure"] for item in positives))
        closure = " + ".join(closures) if closures else "OPEN-CANDIDATE"
        new_cards.append({
            "card_id": f"CMP-IE-001-{ordinal:03d}",
            "batch": BATCH,
            "category": CATEGORY,
            "head": forms[0]["form"],
            "normalized_head": norm(forms[0]["form"]),
            "family_group": group,
            "language": language,
            "source_rows": [item["source_row_index"] for item in claims],
            "source_claims": claims,
            "forms": forms,
            "positives": positives,
            "closure": closure,
            "judgment": closure if positives else "غير صادر",
        })

    covered = {item["source_row_index"] for item in embedded}
    covered.update(index for item in supplements for index in item["source_rows"])
    covered.update(index for item in new_cards for index in item["source_rows"])
    if covered != set(selected_indices):
        raise AssertionError((set(selected_indices) - covered, covered - set(selected_indices)))

    by_language: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for card in new_cards:
        by_language[card["language"]].append(card)
    for language, cards in by_language.items():
        lines = [
            START, "",
            "## حصادُ الصفوف المقارنة الهنديّة الأوربيّة، الدفعة 001 (2026-08-14)", "",
            f"- في هذا الملف {len(cards)} بطاقة جديدة؛ جُمعت صور الأسرة الواحدة، وأُحيلت الصور السابقة إلى بطاقاتها بدل تكرارها.",
            "- فُحصت المروحة كاملة مرتبة بـ`F.rank`، ثم `fan_with_dialect` عند عجز الفصحى؛ الوزن ترتيب لا حكم.",
            "- غياب الصورة من اللقطة `SOURCE-GAP` خارج الحكم؛ الحكم ثلاثي الأرجل: مسار صوت مسمى، حدث مجمد، ومعنى فرع بمدار مكتوب.", "",
        ]
        for card in cards:
            lines.extend(render_card(card))
        lines.append(END)
        reading_texts[language] = reading_texts[language].rstrip() + "\n\n" + "\n".join(lines) + "\n"

    touched_paths = set()
    for path, payload in docs.items():
        if any(
            any(item.get("batch") == BATCH for item in card.get(field, []))
            for card in payload.get("rows", [])
            for field in ("comparative_supplements", "later_comparative_supplements")
        ):
            path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
            touched_paths.add(path.name)

    ranked_count = sum(len(form["fan_review"]) for item in supplements for form in item["forms"]) + sum(len(form["fan_review"]) for card in new_cards for form in card["forms"])
    dialect_count = sum(form["dialect_additions"] for item in supplements for form in item["forms"]) + sum(form["dialect_additions"] for card in new_cards for form in card["forms"])
    event_tiers = Counter(
        candidate["event_tier"]
        for item in supplements for form in item["forms"] for candidate in form["fan_review"]
    )
    event_tiers.update(
        candidate["event_tier"]
        for card in new_cards for form in card["forms"] for candidate in form["fan_review"]
    )
    payload = {
        "schema": "comparative-indo-european-batch-v1.0",
        "date": "2026-08-14",
        "source": "data/prior-art-extended-pairs.json",
        "source_sha256_at_freeze": hashlib.sha256(source_text.encode("utf-8")).hexdigest(),
        "assignment_manifest": "data/comparative-language-assignments.json",
        "category": CATEGORY,
        "batch": BATCH,
        "selection": {
            "criterion": "first 300 cross-European rows in frozen source order",
            "category_offset": OFFSET,
            "selected_source_rows": len(selected),
            "first_source_row_index": selected[0][0],
            "last_source_row_index": selected[-1][0],
            "remaining_category_rows_after_batch": len(category_rows) - OFFSET - len(selected),
        },
        "merge_policy": {
            "same_form": "one card across books and harvests",
            "same_family": "bounded spelling variants share one card only when material and branch agree",
            "snapshot_absence": "SOURCE-GAP only; never a judgment condition",
        },
        "counts": {
            "source_rows": len(selected),
            "already_embedded_rows": len(embedded),
            "supplement_rows": sum(len(item["source_rows"]) for item in supplements),
            "new_card_rows": sum(len(item["source_rows"]) for item in new_cards),
            "supplement_blocks": len(supplements),
            "new_cards": len(new_cards),
            "new_positive_cards": sum(bool(card["positives"]) for card in new_cards),
            "new_positive_roots": sum(len(card["positives"]) for card in new_cards),
            "ranked_candidates_in_new_or_supplemental_full_fans": ranked_count,
            "fan_with_dialect_additions": dialect_count,
            "frozen_event_tiers": {str(key): event_tiers.get(key, 0) for key in (0, 1, 2, 3, 4)},
            "new_cards_by_language": dict(sorted(Counter(card["language"] for card in new_cards).items())),
        },
        "already_embedded": embedded,
        "supplements": supplements,
        "rows": new_cards,
        "touched_prior_manifests": sorted(touched_paths),
    }
    MANIFEST.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    for language, text in reading_texts.items():
        path = READINGS / f"{language}.md"
        if text != path.read_text(encoding="utf-8"):
            path.write_text(text, encoding="utf-8", newline="\n")

    counts = payload["counts"]
    audit = f"""# محضر الصفوف المقارنة الهنديّة الأوربيّة، الدفعة 001 (2026-08-14)

## النطاق والحصيلة

- عولج أول 300 صف من `cross-european` بحسب ترتيب المصدر المجمّد؛ بقي {payload['selection']['remaining_category_rows_after_batch']} صفًا من الفئة.
- كان {counts['already_embedded_rows']} صفًا داخل بطاقات خشيم أصلًا، فأُحيل إليها بلا تكرار؛ أُلحق {counts['supplement_rows']} صفًا في {counts['supplement_blocks']} بطاقة قائمة؛ وصنع {counts['new_card_rows']} صفًا {counts['new_cards']} بطاقة جديدة.
- توزيع البطاقات الجديدة: {json.dumps(counts['new_cards_by_language'], ensure_ascii=False)}.
- فُحص {counts['ranked_candidates_in_new_or_supplemental_full_fans']} مرشحًا في المراوح الجديدة أو الملحقة مرتبة بـ`F.rank`؛ أضاف `fan_with_dialect` {counts['fan_with_dialect_additions']} صورة؛ الوزن لم يحكم. درجات الحدث المجمّد عبر `frozen_event.resolve`: {json.dumps(counts['frozen_event_tiers'], ensure_ascii=False)}.
- صدر {counts['new_positive_cards']} حكمين موجبين على {counts['new_positive_roots']} مقابلين، وبقيت سائر البطاقات الجديدة مفتوحة.

## أسباب الأحكام

- اتبعت النسبة صورة اللفظ؛ لذلك انفصلت الصورة الإيطالية `Egitto` عن بطاقة `Egypt` الإنجليزية القديمة، والصورة السويدية `papper` عن `papier` الرومانية.
- جُمعت الصور المحدودة التي تنتمي إلى مادة واحدة ولسان واحد، مثل صور الأمونيا وصور القرنفل، ولم تُجمع قائمة التوابل كلها في بطاقة واحدة.
- لا يقوم اقتراح خشيم مقام المدار؛ فبقيت الألفاظ مفتوحة ما لم يجتمع مسار صوت مسمى وحدث مجمد ومعنى فرع.
- الصف المدمج أصلًا لا يعاد نسخه، لكن الإحالة تحفظ هويته وتثبت أن مروحته سبقت مراجعتها.

## عشرة مواضع بارزة

1. أُحيل 242 صفًا مضمّنًا أصلًا في بطاقات خشيم، فامتنع التكرار.
2. `avarie` و`averia` و`havarie` أُلحقت ببطاقة `avaria` الواحدة.
3. `avarij` وُجهت إلى النورديّة القديمة بحسب صورتها وبقيت مفتوحة.
4. `spjgr` وُجهت إلى الإنجليزية الوسطى ولم يُنتزع لها موجب من رسمها المضطرب.
5. `Egitto` وُجهت إلى اللاتينية القديمة بحسب صورتها الإيطالية، لا إلى موضع العنقود اليوناني.
6. `bourge` ↔ `برج`: الحصن بناء بارز قوي؛ `ROOT-TRACE`.
7. جُمعت `ammoneakon` وصورتاها المنقولتان بالعربية في بطاقة يونانية واحدة.
8. جُمعت `jerofel/girofle/garofolo/cariofillo` بوصفها صور مادة القرنفل، لا مع بقية أسماء الطيب.
9. `furka` ↔ `فرق`: تشعب الشوكة انفصال إلى فرعين؛ `ROOT-TRACE`.
10. فُصل `papper` النوردي عن `papier` الروماني بحسب صورة كل مدخل.

## تحقق الإيداع

- البيان: `data/comparative-indo-european-batch-001.json`.
- ملف الإسناد: `data/comparative-language-assignments.json`؛ ملف العزل النهائي الحالي: `data/comparative-rows-triaged.json` وفيه {assignment_payload['counts']['triaged']} صفًا.
- اتحاد الإحالات والإلحاقات والبطاقات الجديدة يساوي الصفوف الثلاثمائة المختارة بلا غياب ولا تكرار.
- كل مروحة جديدة أو ملحقة أعيد توليدها كاملة، ورتبت بـ`F.rank`، ثم فُحص `fan_with_dialect` بعد عجز الفصحى؛ وكل حدث سُئل حصرًا عبر `scripts/frozen_event.py` ودوّنت درجته.
"""
    AUDIT.write_text(audit, encoding="utf-8", newline="\n")

    # Final in-memory gates.
    if counts["source_rows"] != counts["already_embedded_rows"] + counts["supplement_rows"] + counts["new_card_rows"]:
        raise AssertionError("count conservation failed")
    if len({source_key(index, row) for index, row in selected}) != LIMIT:
        raise AssertionError("source identity collision")
    for item in supplements:
        for form in item["forms"]:
            fresh = fan_for(form["form"], item["target_language"], None)
            if fresh != form:
                raise AssertionError(f"fan drift: {form['form']}")
    for card in new_cards:
        for form in card["forms"]:
            fresh = fan_for(form["form"], card["language"], POSITIVE.get(norm(form["form"])))
            if fresh != form:
                raise AssertionError(f"fan drift: {form['form']}")
    print(json.dumps(payload["counts"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


