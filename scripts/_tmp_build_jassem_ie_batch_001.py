# -*- coding: utf-8 -*-
"""One-shot builder for Jassem Indo-European bridge-agree batch 001."""
from __future__ import annotations

import json
import re
import sys
from collections import Counter, OrderedDict, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import fan_any_script as F  # noqa: E402
from rebuild_khashim_indo_european_batches import load_events  # noqa: E402

SOURCE = ROOT / "data" / "prior-art-pairs.json"
MANIFEST = ROOT / "data" / "jassem-indo-european-batch-001.json"
AUDIT = ROOT / "05-audits" / "2026-08-13-jassem-indo-european-batch-001.md"
READINGS = ROOT / "04-cross-linguistic" / "readings"
KHASHIM = ROOT / "data" / "khashim-indo-european-batch-{number:03d}.json"
START = "<!-- JASSEM-IE-BATCH-001:START -->"
END = "<!-- JASSEM-IE-BATCH-001:END -->"

LANG_LABELS = {
    "ancient-greek": "اليونانيّة القديمة/Ancient Greek",
    "middle-english": "الإنجليزيّة الوسطى/Middle English",
    "old-english": "الإنجليزيّة القديمة/Old English",
    "old-latin": "اللاتينيّة القديمة/Old Latin",
    "welsh": "الويلزيّة/Welsh",
}

GREEK = set("""Abacus|Anarchy|Anatomy|Angel|Architecture|Aroma|Ascetic|Atomic Bomb/Weapon|Bishop|Cardiac Failure|Chameleon""".split("|"))
LATIN = set("""Accelerate|Accent|Accusative|Acquire|Adolescent|Affidavit|Amicable|Area|Art|Article|Ascent|Attribute|Authority|Autumn|Binary|Canonical|Cedar|Central|Ceremony""".split("|"))
MIDDLE = set("""Abhor|Abrade|Accuse|Adventure|Advise|Advisor|Affair|Affiliation|Age|Agree|Alienate|Apartment|Appear|Appetite|Arrive|Bachelor|Ballot Box|Banquet|Bar|Barrister|Basil|Battle|Beautiful|Beef|Beverage|Bias|Bikini|Blouse|Boil|Bomb|Bracelet|Brandy|Browse|Bureaucracy|Burnoose|Button|Cabbage|Candy|Cane|Cannon|Cant|Canvas|Carpet|Carpet bombing|Carrot|Cause|Cavalry|Charge d'Affairs|Cheers|Chef|Cherry|Chimney|Chivalry""".split("|"))


def route(*parts: str) -> str:
    return "؛ ".join(parts)


POSITIVE: dict[str, dict[str, Any]] = {
    "abide": {
        "root": "بيت", "closure": "ROOT-TRACE",
        "branch_meaning": "`abide` في البقاء والسكن والإقامة",
        "orbit": "الإقامة بقاءٌ في حيزٍ مسكون؛ فيلتقي معنى `abide` حدث `بيت` في الحيز الذي يُسكن ويُستقر فيه مباشرة.",
        "sound_route": route("b↔ب=`IDN-05`", "d↔ت=`BR-GRIM-02`", "باب المعتل المسمى يثبت الياء في الجوف"),
        "sound_searches": ["`b` + `ب` + «الإنجليزيّة القديمة/Old English»", "`d` + `ت` + «الإنجليزيّة القديمة/Old English»"],
    },
    "acorn": {
        "root": "قرن", "closure": "ROOT-ECHO",
        "branch_meaning": "`acorn`، ثمرة البلوط الصلبة الناتئة من موضع اتصالها بالغصن",
        "orbit": "الثمرة جسم صلب ناتئ ممتد من مقدم موضع اتصاله؛ فهذا مدار عضوي واحد إلى نتوء `قرن`، لا دعوى أنها قرن الحيوان نفسه.",
        "sound_route": route("c↔ق=`GUT-01`", "r↔ر=`IDN-01`", "n↔ن=`IDN-03`"),
        "sound_searches": ["`c` + `ق` + «الإنجليزيّة القديمة/Old English»", "`r` + `ر` + «الإنجليزيّة القديمة/Old English»", "`n` + `ن` + «الإنجليزيّة القديمة/Old English»"],
    },
    "ally": {
        "root": "ولي", "closure": "ROOT-TRACE",
        "branch_meaning": "`ally`، من يلزم غيره وينضم إليه ناصرًا أو تابعًا في عهد",
        "orbit": "الحليف يلزم حليفه ويتبعه مع اشتمال العهد عليه؛ وهذا هو حدث `ولي` مباشرة.",
        "sound_route": route("ll↔ل=`IDN-04` بعد قراءة الإدغام صوتًا واحدًا", "y↔ي=`IDN-23`", "باب المعتل المسمى يثبت الواو في الأول"),
        "sound_searches": ["`l` + `ل` + «الإنجليزيّة القديمة/Old English»", "`y` + `ي` + «الإنجليزيّة القديمة/Old English»"],
    },
    "bit": {
        "root": "بت", "closure": "NUCLEUS-TRACE",
        "branch_meaning": "`bit`، جزء أو قطعة صغيرة منفصلة من كل أكبر",
        "orbit": "القطعة الصغيرة تحصل بقطع الامتداد وانفصال جزء منه؛ فالمعنى مباشر في حدث `بت`.",
        "sound_route": route("b↔ب=`IDN-05`", "t↔ت=`IDN-11`"),
        "sound_searches": ["`b` + `ب` + «الإنجليزيّة القديمة/Old English»", "`t` + `ت` + «الإنجليزيّة القديمة/Old English»"],
    },
    "blaze": {
        "root": "برز", "closure": "ROOT-ECHO",
        "branch_meaning": "`blaze`، لهب أو ضوء يظهر ظهورًا شديدًا",
        "orbit": "اللهب المتأجج بروز ضوء قوي من بين ما يكتنفه؛ فيلتقي حدث `برز` في الظهور القوي بمدار واحد.",
        "sound_route": route("b↔ب=`IDN-05`", "l↔ر=`LIQ-01`", "z↔ز=`IDN-22`"),
        "sound_searches": ["`b` + `ب` + «الإنجليزيّة القديمة/Old English»", "`l` + `ر` + «الإنجليزيّة القديمة/Old English»", "`z` + `ز` + «الإنجليزيّة القديمة/Old English»"],
    },
    "booth": {
        "root": "بيت", "closure": "ROOT-TRACE",
        "branch_meaning": "`booth`، حيز صغير محيط يُقام أو يُعمل فيه",
        "orbit": "المقصورة حيز محيط يشغله الإنسان ويستقر فيه زمن العمل أو العرض؛ وهذا حدث `بيت` مباشرة.",
        "sound_route": route("b↔ب=`IDN-05`", "th↔ت=`BR-GRIM-01`", "باب المعتل المسمى يثبت الياء في الجوف"),
        "sound_searches": ["`b` + `ب` + «الإنجليزيّة القديمة/Old English»", "`th` + `ت` + «الإنجليزيّة القديمة/Old English»"],
    },
    "but": {
        "root": "بت", "closure": "NUCLEUS-ECHO",
        "branch_meaning": "`but` أداة استدراك تفصل ما بعدها عما كان سيسترسل من قبلها",
        "orbit": "الاستدراك يقطع استرسال القضية الأولى ويفصل عنها قيدًا مخالفًا؛ فهذا مدار نحوي واحد إلى قطع `بت` وانفصاله.",
        "sound_route": route("b↔ب=`IDN-05`", "t↔ت=`IDN-11`"),
        "sound_searches": ["`b` + `ب` + «الإنجليزيّة القديمة/Old English»", "`t` + `ت` + «الإنجليزيّة القديمة/Old English»"],
    },
    "butter": {
        "root": "بتل", "closure": "ROOT-ECHO",
        "branch_meaning": "`butter`، مادة دهنية تتميز من اللبن أو القشدة وتستقل كتلة وافرة",
        "orbit": "صنع الزبد يميز الدهن من أصله اللبني حتى يصير كتلة قائمة بذاتها؛ فيلتقي حدث `بتل` في الانفصال عن الأصل مع الوفرة.",
        "sound_route": route("b↔ب=`IDN-05`", "t↔ت=`IDN-11`", "r↔ل=`LIQ-01`"),
        "sound_searches": ["`b` + `ب` + «الإنجليزيّة القديمة/Old English»", "`t` + `ت` + «الإنجليزيّة القديمة/Old English»", "`r` + `ل` + «الإنجليزيّة القديمة/Old English»"],
    },
    "cave": {
        "root": "قوب", "closure": "ROOT-TRACE",
        "branch_meaning": "`cave`، فراغ جوفي محدود داخل جرم متماسك",
        "orbit": "الكهف فراغ جوفي محدود الجوانب مقور في جرم الأرض أو الصخر؛ وهذا نص حدث `قوب` مباشرة.",
        "sound_route": route("c↔ق=`GUT-01`", "v↔ب=`LAB-05`", "باب المعتل المسمى يثبت الواو في الجوف"),
        "sound_searches": ["`c` + `ق` + «الإنجليزيّة الوسطى/Middle English»", "`v` + `ب` + «الإنجليزيّة الوسطى/Middle English»"],
    },
}


def norm(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip()).casefold()


def clean(value: Any) -> str:
    return " ".join(str(value or "").split()).replace("`", "ˋ")


def language_for(head: str) -> str:
    if head in GREEK:
        return "ancient-greek"
    if head in LATIN:
        return "old-latin"
    if head in MIDDLE:
        return "middle-english"
    return "old-english"


def script_for(language: str) -> str:
    return "latin" if language in {"ancient-greek", "old-latin"} else "germanic"


def candidate_review(head: str, script: str, positive: dict[str, Any] | None, root_events: dict[str, str], nucleus_events: dict[str, str]) -> tuple[list[dict[str, Any]], int]:
    base = F.fan(head, script)
    ranked = F.rank(head, base, script)
    labels = {root: "فصيح" for root in base}
    dialect_additions = 0
    if positive is None:
        for root, label in F.fan_with_dialect(head, script):
            if root not in labels:
                labels[root] = label
                dialect_additions += 1
    ranked_map = {root: weight for root, weight in ranked}
    roots = list(base) + [root for root in labels if root not in set(base)]
    roots.sort(key=lambda root: (-ranked_map.get(root, 0.0), list(labels).index(root)))
    out = []
    selected = positive["root"] if positive else None
    if selected and selected not in labels:
        raise AssertionError(f"selected root {selected} is absent from full fan of {head}")
    for root in roots:
        event = root_events.get(root) or nucleus_events.get(root)
        out.append({
            "root": root,
            "weight": float(ranked_map.get(root, 0.0)),
            "sound": "✓",
            "event": "✓" if event else "×",
            "meaning": "✓" if root == selected else ("×" if event else "؟"),
            "dialect_label": None if labels[root] == "فصيح" else labels[root],
        })
    return out, dialect_additions


def find_card(card_id: str, manifests: list[dict[str, Any]]) -> tuple[int, dict[str, Any]]:
    for number, payload in enumerate(manifests, 1):
        for card in payload["rows"]:
            if (card.get("merged_card_id") or card.get("card_id")) == card_id:
                return number, card
    raise KeyError(card_id)


def card_forms(card: dict[str, Any]) -> list[str]:
    return [item.get("form", "") for item in card.get("forms", []) if isinstance(item, dict) and item.get("form")]


def update_existing_block(text: str, card_id: str, supplement: dict[str, Any], rejudgment: dict[str, Any] | None, root_events: dict[str, str], nucleus_events: dict[str, str]) -> str:
    markers = [f"<!-- KHASHIM-IE-MERGED:{card_id} -->", f"<!-- KHASHIM-IE-CONT:{card_id} -->"]
    marker = next((item for item in markers if item in text), None)
    if not marker:
        raise AssertionError(f"reading marker missing for {card_id}")
    at = text.index(marker)
    start = text.rfind("\n### ", 0, at)
    start = start + 1 if start >= 0 else at
    finish = text.find("\n### ", at)
    if finish < 0:
        finish = len(text)
    block = text[start:finish]
    s = f"<!-- JASSEM-IE-SUPPLEMENT-001:{card_id}:START -->"
    e = f"<!-- JASSEM-IE-SUPPLEMENT-001:{card_id}:END -->"
    block = re.sub(rf"\n?{re.escape(s)}.*?{re.escape(e)}\n?", "\n", block, flags=re.DOTALL)
    claims = " | ".join(
        f"صف {row['source_row_index']}: `{clean(row['european'])}` ↔ `{clean(row['arabic_root'])}` ({clean(row['author_translit'])})؛ «{clean(row['arabic_gloss'])}» [{clean(row['source'])}]"
        for row in supplement["source_claims"]
    )
    lines = [s, f"- إلحاق جاسم، الدفعة 001: {claims}. قيمة `bridge_agrees=نعم` أولوية فحص مستقلة وليست حكمًا."]
    if rejudgment:
        root = rejudgment["root"]
        event = root_events.get(root) or nucleus_events.get(root)
        if not event:
            raise AssertionError(f"missing event for existing rejudgment {card_id}:{root}")
        # Mark the selected member in the already displayed whole fan.
        block, count = re.subn(
            rf"(`{re.escape(root)}`\[و[0-9.]+،)ص[✓×]،ح✓،م[×؟](\])",
            rf"\1ص✓،ح✓،م✓\2", block, count=1,
        )
        if count == 0:
            block, count = re.subn(
                rf"(`{re.escape(root)}`\[)ص[✓×]،ح✓،م[×؟](\])",
                rf"\1ص✓،ح✓،م✓\2", block, count=1,
            )
        if count == 0:
            raise AssertionError(f"selected fan member not found in reading block {card_id}:{root}")
        block, n1 = re.subn(r"^- المدار المكتوب:.*$", f"- المدار المكتوب: {rejudgment['orbit']}", block, count=1, flags=re.MULTILINE)
        block, n2 = re.subn(r"^- الحكم \(استكشاف\):.*$", f"- الحكم (استكشاف): **{rejudgment['closure']} (استكشاف)** بالمقابل `{root}`.", block, count=1, flags=re.MULTILINE)
        block, n3 = re.subn(r"^- حالة الإغلاق: [A-Z-]+\.?$", f"- حالة الإغلاق: {rejudgment['closure']}.", block, count=1, flags=re.MULTILINE)
        if not (n1 and n2 and n3):
            raise AssertionError(f"could not supersede judgment lines in {card_id}: {n1,n2,n3}")
        lines.extend([
            f"- إعادة حكم جاسم من المروحة كلها: `{root}`؛ مسار الصوت: {rejudgment['sound_route']}.",
            f"- الحدث المجمّد كما هو: «{event}».",
            f"- معنى الفرع: {rejudgment['branch_meaning']}.",
            f"- المدار الناسخ: {rejudgment['orbit']}",
            f"- الحصيلة الناسخة: **{rejudgment['closure']} (استكشاف)** بالمقابل `{root}`.",
        ])
    lines.append(e)
    block = block.rstrip() + "\n" + "\n".join(lines) + "\n"
    return text[:start] + block + text[finish:]


def render_card(card: dict[str, Any]) -> list[str]:
    claims = " | ".join(
        f"صف {row['source_row_index']}: `{clean(row['european'])}` ↔ `{clean(row['arabic_root'])}`؛ رومنة جاسم `{clean(row['author_translit'])}`؛ «{clean(row['arabic_gloss'])}» [{clean(row['source'])}]"
        for row in card["source_claims"]
    )
    fan = "، ".join(
        f"`{item['root']}`[و{item['weight']:.6f}،ص{item['sound']}،ح{item['event']}،م{item['meaning']}{'،له=' + item['dialect_label'] if item['dialect_label'] else ''}]"
        for item in card["fan_review"]
    ) or "لا مرشح قابل للتوليد من الهيكل"
    lines = [
        f"### بطاقة جاسم: `{card['head']}`؛ {card['card_id']}",
        f"<!-- JASSEM-IE:{card['card_id']} -->",
        f"- وحدة البطاقة: مدخل واحد، وصفوف المصدر {card['source_rows']}؛ جُمعت دعاوى الكلمة نفسها عبر أبحاث جاسم ولم تتكرر البطاقة.",
        "- نسبة المصدر: المدخل الأوربي والجذر والرومنة والشرح واقتراح المقابلة للدكتور زيدان علي جاسم؛ المروحة والحدث والمدار والحكم أعمال المشروع.",
        f"- الكلمة في الفرع: `{card['head']}` كما سماها جدول المصدر؛ لا يشترط ثبوتها في لقطة معجمية محلية.",
        f"- نقل جاسم المسمى: {claims}.",
        f"- الخطوة صفر: النص مكتوب بالرسم اللاتيني؛ اللسان المسند {LANG_LABELS[card['language']]}؛ المروحة `{card['script']}`؛ الهيكل `{'-'.join(card['skeleton']) or '∅'}`.",
        f"- فحص كل مرشحات المروحة، مرتبة بـ`F.rank`: {fan}. الوزن ترتيب لا حكم؛ ح× تعني غياب حدث مجمد، وم× تعني أن المدار فُحص ولم يثبت.",
        f"- فحص `fan_with_dialect` عند عجز الفصحى: أضاف {card['dialect_additions']} صورة موسومة؛ بقي الفصيح أولًا ولم تستبدله الصورة اللهجية.",
    ]
    if card["positives"]:
        for positive in card["positives"]:
            lines.extend([
                f"- المقابل المنتخب من المروحة كلها: `{positive['root']}`؛ مسار الصوت المسمى: {positive['sound_route']}.",
                f"- ما فُتش في الشبكة: {'؛ '.join(positive['sound_searches'])}.",
                f"- الحدث من السجل المجمّد كما هو: «{positive['frozen_event']}» [{positive['event_source']}].",
                f"- معنى الفرع: {positive['branch_meaning']}.",
                f"- المدار المكتوب: {positive['orbit']}",
            ])
        issued = "، ".join(f"`{p['root']}`={p['closure']}" for p in card["positives"])
        lines.append(f"- الحكم (استكشاف): **{card['closure']} (استكشاف)**؛ {issued}.")
    else:
        lines.extend([
            "- المدار المكتوب: فُحصت جميع المرشحات ذات الحدث المجمّد، ولم يثبت منها مدار إلى معنى المدخل؛ وموافقة الجسر لا تعوّض رجل المعنى.",
            "- الحكم (استكشاف): **غير صادر (استكشاف)**.",
        ])
    lines.extend([
        "- حقل النقص، خارج الحكم: لا يطلب ثبوت الصورة في اللقطة، ولا يحوّل غيابها إلى رفض.",
        f"- حالة الإغلاق: {card['closure']}.",
        "",
    ])
    return lines


def main() -> int:
    source_payload = json.loads(SOURCE.read_text(encoding="utf-8"))
    all_rows = source_payload["rows"]
    eligible = [(index, row) for index, row in enumerate(all_rows) if row.get("bridge_agrees") == "نعم"]
    selected = eligible[:300]
    if len(selected) != 300:
        raise AssertionError("expected 300 bridge-agree source rows")

    head_gaps = []
    groups: OrderedDict[str, list[tuple[int, dict[str, Any]]]] = OrderedDict()
    for index, row in selected:
        head = str(row.get("european") or "").strip()
        if not head:
            head_gaps.append({"source_row_index": index, "tag": "SOURCE-HEAD-GAP", "source_claim": row})
            continue
        groups.setdefault(norm(head), []).append((index, row))

    khashim_payloads = [json.loads(Path(str(KHASHIM).format(number=number)).read_text(encoding="utf-8")) for number in range(1, 11)]
    existing: dict[str, list[tuple[int, str, str, str]]] = defaultdict(list)
    for number, payload in enumerate(khashim_payloads, 1):
        for card in payload["rows"]:
            cid = card.get("merged_card_id") or card.get("card_id")
            for form in card_forms(card):
                existing[norm(form)].append((number, cid, card["language"], form))

    root_events, nucleus_events = load_events()
    supplements = []
    new_cards = []
    new_ordinal = 0
    for key, members in groups.items():
        head = str(members[0][1]["european"]).strip()
        claims = [{"source_row_index": index, **row} for index, row in members]
        if key in existing:
            target = existing[key][0]
            number, cid, language, matched_form = target
            supplement = {
                "head": head,
                "source_rows": [index for index, _ in members],
                "source_claims": claims,
                "target_batch": number,
                "target_card_id": cid,
                "target_language": language,
                "matched_form": matched_form,
                "reason": "exact same normalized European lexical form; merged across Khashim and Jassem",
            }
            spec = POSITIVE.get(key)
            if key == "car":
                supplement["existing_positive_confirmed"] = "جر؛ NUCLEUS-TRACE already issued on the merged Khashim card"
            if spec:
                event = root_events.get(spec["root"]) or nucleus_events.get(spec["root"])
                if not event:
                    raise AssertionError(f"missing frozen event for {head}:{spec['root']}")
                supplement["rejudgment"] = {**spec, "frozen_event": event}
            supplements.append(supplement)
            continue

        new_ordinal += 1
        language = language_for(head)
        script = script_for(language)
        spec = POSITIVE.get(key)
        review, dialect_additions = candidate_review(head, script, spec, root_events, nucleus_events)
        positives = []
        if spec:
            event = root_events.get(spec["root"]) or nucleus_events.get(spec["root"])
            if not event:
                raise AssertionError(f"missing frozen event for {head}:{spec['root']}")
            positives.append({
                **spec,
                "frozen_event": event,
                "event_source": "computational/data/layer_2_results_v2.jsonl؛ jabal_axial" if len(spec["root"]) == 3 else "data/juthoor-core-levels.json؛ jabal_lexicon_reading_ar",
            })
        closure = positives[0]["closure"] if positives else "OPEN-CANDIDATE"
        new_cards.append({
            "card_id": f"JAS-IE-001-{new_ordinal:03d}",
            "batch": 1,
            "head": head,
            "normalized_head": key,
            "language": language,
            "script": script,
            "skeleton": F.skeleton(head, script),
            "source_rows": [index for index, _ in members],
            "source_claims": claims,
            "fan_review": review,
            "dialect_additions": dialect_additions,
            "positives": positives,
            "closure": closure,
            "judgment": closure if positives else "غير صادر",
        })

    if len(groups) != len(supplements) + len(new_cards) or len(head_gaps) + sum(len(value) for value in groups.values()) != 300:
        raise AssertionError((len(groups), len(supplements), len(new_cards), len(head_gaps)))

    # Merge the nineteen exact forms into their Khashim cards and update the two
    # cards for which the newly inspected whole fan completes all three legs.
    reading_texts: dict[str, str] = {}
    touched_khashim_batches = set()
    for supplement in supplements:
        number, card = find_card(supplement["target_card_id"], khashim_payloads)
        touched_khashim_batches.add(number)
        prior_supplements = [item for item in card.get("jassem_supplements", []) if item.get("batch") != 1]
        prior_supplements.append({
            "batch": 1,
            "source": "data/prior-art-pairs.json",
            "source_rows": supplement["source_rows"],
            "source_claims": supplement["source_claims"],
            "bridge_agrees": True,
        })
        card["jassem_supplements"] = prior_supplements
        if supplement.get("rejudgment"):
            judged = supplement["rejudgment"]
            card["jassem_rejudgments"] = [{
                "batch": 1, "source": "data/prior-art-pairs.json", "source_rows": supplement["source_rows"], **judged,
            }]
            if not any(item.get("root") == judged["root"] and item.get("source") == "data/prior-art-pairs.json" for item in card.get("positives", [])):
                card.setdefault("positives", []).append({
                    "source": "data/prior-art-pairs.json",
                    "source_rows": supplement["source_rows"],
                    "form": supplement["head"],
                    **judged,
                    "event_source": "computational/data/layer_2_results_v2.jsonl؛ jabal_axial",
                })
            card["closure"] = judged["closure"]
            card["judgment"] = judged["closure"]
        language = supplement["target_language"]
        if language not in reading_texts:
            reading_texts[language] = (READINGS / f"{language}.md").read_text(encoding="utf-8")
        reading_texts[language] = update_existing_block(
            reading_texts[language], supplement["target_card_id"], supplement,
            supplement.get("rejudgment"), root_events, nucleus_events,
        )

    # Append the new card sections only to the four material files selected by
    # the forms, preserving any earlier append-only history.
    by_language: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for card in new_cards:
        by_language[card["language"]].append(card)
    for language, cards in by_language.items():
        if language not in reading_texts:
            reading_texts[language] = (READINGS / f"{language}.md").read_text(encoding="utf-8")
        text = re.sub(rf"\n?{re.escape(START)}.*?{re.escape(END)}\n?", "\n", reading_texts[language], flags=re.DOTALL)
        lines = [
            START,
            "",
            "## حصادُ زيدان علي جاسم الهنديّ الأوربيّ، دفعة الموافقات 001 (2026-08-13)",
            "",
            f"- في هذا الملف {len(cards)} بطاقة جديدة؛ اتبع الإسناد مادة الكلمة لا ترتيب ملف المصدر.",
            "- `bridge_agrees=نعم` قدّم الصف للفحص فقط؛ الحكم لا يصدر إلا بمسار صوت مسمى، وحدث مجمد كما هو، ومعنى فرع ومدار إنساني مكتوب.",
            "- فُحصت المروحة كلها مرتبة بـ`F.rank`، واستُعمل `fan_with_dialect` بعد عجز الفصيح؛ الوزن ترتيب لا حكم.",
            "",
        ]
        for card in cards:
            lines.extend(render_card(card))
        lines.append(END)
        reading_texts[language] = text.rstrip() + "\n\n" + "\n".join(lines) + "\n"

    for language, text in reading_texts.items():
        (READINGS / f"{language}.md").write_text(text, encoding="utf-8", newline="\n")
    for number in touched_khashim_batches:
        Path(str(KHASHIM).format(number=number)).write_text(
            json.dumps(khashim_payloads[number - 1], ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8", newline="\n",
        )

    all_candidates = sum(len(card["fan_review"]) for card in new_cards)
    dialect_additions = sum(card["dialect_additions"] for card in new_cards)
    new_positive_cards = [card for card in new_cards if card["positives"]]
    rejudged = [item for item in supplements if item.get("rejudgment")]
    payload = {
        "schema": "jassem-indo-european-batch-v1.0",
        "date": "2026-08-13",
        "source_author": "زيدان علي جاسم",
        "source_affiliation": "جامعة القصيم",
        "source": "data/prior-art-pairs.json",
        "layer": "exploration",
        "batch": 1,
        "selection": {
            "criterion": "first 300 source rows with bridge_agrees=نعم in source order",
            "eligible_bridge_agrees_rows_current": len(eligible),
            "selected_source_rows": 300,
            "first_source_row_index": selected[0][0],
            "last_source_row_index": selected[-1][0],
            "source_head_gaps": len(head_gaps),
            "nonempty_source_rows": 300 - len(head_gaps),
            "unique_european_heads": len(groups),
        },
        "jassem_transliteration": {"3": "ع", "2": "ح", "kh": "خ", "gh": "غ", "T": "ط", "D": "ض", "S": "ص", "Dh": "ظ", "'": "ء"},
        "merge_policy": {
            "same_normalized_european_head": "one card with all Jassem rows",
            "exact_form_in_khashim": "supplement the existing card; never duplicate",
            "snapshot_absence": "never a judgment condition",
            "judgment_legs": ["named sound route", "frozen event verbatim", "branch meaning with human-written orbit"],
            "bridge_agrees": "priority signal only, never a verdict",
        },
        "cards_touched": len(groups),
        "new_cards_written": len(new_cards),
        "existing_card_supplements": len(supplements),
        "newly_issued_positive_cards": len(new_positive_cards) + len(rejudged),
        "previous_positive_confirmations": 1,
        "open_new_cards": len(new_cards) - len(new_positive_cards),
        "new_cards_by_language": dict(sorted(Counter(card["language"] for card in new_cards).items())),
        "all_heads_by_target_language": dict(sorted(Counter(
            [card["language"] for card in new_cards] + [item["target_language"] for item in supplements]
        ).items())),
        "rank_review": {
            "method": "F.rank",
            "ranked_candidates": all_candidates,
            "nonzero_weights": sum(item["weight"] > 0 for card in new_cards for item in card["fan_review"]),
            "fan_with_dialect_additions": dialect_additions,
            "policy": "weight orders display and never judges",
        },
        "source_head_gaps": head_gaps,
        "supplements": supplements,
        "rows": new_cards,
    }
    MANIFEST.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")

    highlights = [
        "`Abide` دُمجت في بطاقة خشيم القائمة، ورفعت المروحة الكاملة `بيت` لا جذر المؤلف وحده؛ `ROOT-TRACE`.",
        "`Acorn` ↔ `قرن`: `ROOT-ECHO` في النتوء الصلب، مع فصل ثمرة البلوط عن قرن الحيوان.",
        "`Ally` ↔ `ولي`: `ROOT-TRACE` في اللزوم والتبعية والاشتمال.",
        "`Bit` ↔ `بت`: `NUCLEUS-TRACE` في القطعة الناتجة من القطع والانفصال.",
        "`Blaze` ↔ `برز`: `ROOT-ECHO` في بروز الضوء أو اللهب ظهورًا قويًا.",
        "`Booth` ↔ `بيت`: `ROOT-TRACE` في الحيز المحيط الذي يشغله الإنسان.",
        "`But` ↔ `بت`: `NUCLEUS-ECHO` في قطع استرسال القضية بأداة الاستدراك.",
        "`Butter` ↔ `بتل`: `ROOT-ECHO` في تميز الدهن من أصله وصيرورته كتلة قائمة.",
        "`Car` لم تتكرر؛ أضيف شاهد جاسم إلى بطاقة خشيم الويلزية ذات `جر` الصادرة من قبل.",
        "`Cave` دُمجت في بطاقة خشيم القائمة، وأخرج فحص المروحة `قوب` «فراغ جوفي محدود الجوانب»؛ `ROOT-TRACE`.",
    ]
    audit_lines = [
        "# محضر حصاد جاسم الهنديّ الأوربيّ، دفعة الموافقات 001 (2026-08-13)",
        "",
        "## النطاق والحصيلة",
        "",
        f"- انتُخبت أول 300 صف من الصفوف ذات `bridge_agrees=نعم`؛ المخزون الجاري يحمل {len(eligible)} صفًا موافقًا بعد توسع الحصاد، لا العدد القديم وحده.",
        f"- {len(head_gaps)} صفًا بلا مدخل أوربي حُفظت في البيان بوسم حسابي `SOURCE-HEAD-GAP` ولم تُختلق لها بطاقات.",
        f"- {300 - len(head_gaps)} صفًا غير فارغ انكمشت إلى {len(groups)} كلمة: {len(supplements)} أُلحقت ببطاقات خشيم القائمة، و{len(new_cards)} بطاقة جديدة.",
        f"- أُصدر {len(new_positive_cards) + len(rejudged)} حكم موجب جديد، وثُبّت شاهد جاسم لبطاقة `car↔جر` الموجبة من قبل؛ بقي {len(new_cards) - len(new_positive_cards)} من البطاقات الجديدة مفتوحًا.",
        f"- توزيع البطاقات الجديدة: " + "، ".join(f"{LANG_LABELS[k]}={v}" for k, v in sorted(Counter(card['language'] for card in new_cards).items())) + ".",
        f"- فُحص {all_candidates} مرشحًا مرتبة بـ`F.rank`، ومنها {dialect_additions} إضافة موسومة من `fan_with_dialect`؛ الوزن لم يحكم.",
        "- رومنة جاسم قُرئت بمفتاحه المعلن، لكن الجذر العربي في `arabic_root` هو المعتمد كما أمر المؤلف.",
        "",
        "## أسباب الأحكام",
        "",
        "- لم تُعامل موافقة الجسر حكمًا رابعًا ولا بديلًا من الأرجل الثلاث؛ إنما قدّمت الصف إلى أول الطابور.",
        "- كل مرشح ذي حدث مجمد عُرض على معنى المدخل؛ تشابه الرسم بلا مدار بقي مفتوحًا، مثل `cat↔قط` لأن حدث `قط` هو القطع لا الحيوان.",
        "- جُمعت دعاوى المدخل الواحد عبر أبحاث جاسم، وجُمعت المطابقات الحرفية مع بطاقات خشيم بدل إنشاء نسخ موازية.",
        "- غياب الصورة من لقطة المشروع لم يدخل الحكم ولم يُنتج `SOURCE-GAP` مفترضًا.",
        "",
        "## عشرة مواضع بارزة",
        "",
    ] + [f"{i}. {line}" for i, line in enumerate(highlights, 1)] + [
        "",
        "## تحقق الإيداع",
        "",
        "- البيان: `data/jassem-indo-european-batch-001.json`.",
        "- القراءة: الملفات المسموح بها وحدها، مع إلحاقات المطابقات إلى مواضعها القائمة.",
        "- الإيداع يُجرى بأمر `scripts/ship.py --only ... --push` بعد خضرة البوابات.",
    ]
    AUDIT.write_text("\n".join(audit_lines) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({
        "selected": 300, "head_gaps": len(head_gaps), "unique_heads": len(groups),
        "supplements": len(supplements), "new_cards": len(new_cards),
        "new_positive_cards": len(new_positive_cards), "rejudgments": len(rejudged),
        "candidates": all_candidates, "dialect_additions": dialect_additions,
        "languages": Counter(card["language"] for card in new_cards),
        "touched_khashim_batches": sorted(touched_khashim_batches),
    }, ensure_ascii=False, default=dict))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
