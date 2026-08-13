# -*- coding: utf-8 -*-
"""One-shot builder for Jassem Indo-European bridge-agree batch 002."""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
from collections import Counter, OrderedDict, defaultdict
from pathlib import Path
from types import SimpleNamespace
from typing import Any

HERE = Path(__file__).resolve()
ROOT = HERE.parent.parent
BASE_COMMIT = "2882fc0"
READING_BASE_COMMIT = "d24a181"
base_source = subprocess.check_output(
    ["git", "show", f"{BASE_COMMIT}:scripts/_tmp_build_jassem_ie_batch_001.py"],
    cwd=ROOT, text=True, encoding="utf-8",
)
base_ns: dict[str, Any] = {"__name__": "_jassem_ie_base", "__file__": str(HERE)}
exec(compile(base_source, f"{BASE_COMMIT}:jassem001", "exec"), base_ns)
B = SimpleNamespace(**base_ns)
B.LANG_LABELS.update({"old-norse": "النورديّة القديمة/Old Norse"})

BATCH = 2
SOURCE = ROOT / "data" / "prior-art-pairs.json"
MANIFEST = ROOT / "data" / "jassem-indo-european-batch-002.json"
AUDIT = ROOT / "05-audits" / "2026-08-13-jassem-indo-european-batch-002.md"
READINGS = ROOT / "04-cross-linguistic" / "readings"
KHASHIM = ROOT / "data" / "khashim-indo-european-batch-{number:03d}.json"
START = "<!-- JASSEM-IE-BATCH-002:START -->"
END = "<!-- JASSEM-IE-BATCH-002:END -->"
ALL_LANGUAGES = B.ALL_LANGUAGES

GREEK = set("""Church|Coma|Comet|Coral|Cyan|Democracy|Despot|Diagramme|Diplomacy|Ecclesiastical|Ecology|Enigma|Epidemic""".split("|"))
LATIN = set("""Chick peas|Chimney|Circle|Civil Law|Cognition|Colloquial|Colonial|Comprehend|Conceive|Conciliation|Condemn|Condominium|Confess|Conflict|Congratulate|Conscious|Consensus|Consultation|Contingency Plan|Continue|Contract|Contrary to|Copulate|Copy|Cupid|Diurnal|Diffusion of Nuclear Weapons|Direction|Discipline|Discuss|Dissect|Dissection|District|Diverge|Divide|Duration|Educate|Effervescent|Emancipation|Escalate|Estimate|Evade|Evidence|Excavate|Except|Excite|Excrete|Existence|Expedition|Explode|Extant|Fabric|Facilitate|Fact|Faculty""".split("|"))
NORSE = {"Clip", "Crawl", "Dirt", "Egg", "Enthrall"}
MIDDLE = set("""Chivalry|Chop|Cipher|Cite|Clear|Clement|Clever|Clock|Coast|Coerce|Coffee|Coffin|Collapse|Collar|Collect|Commerce|Commission|Committee|Common Law|Community|Companion|Company|Complaint|Complete|Coast|Coy|Crazy|Cream|Create|Creator|Cremation|Crown|Cuff|Curly Hair|Curve|Cute|Dairy|Damage|Damages|Date|Dazzle|Debate|Declare|Decline|Defense|Degree|Delay|Delicious|Delight|Deliver|Despise|Devise|Dine|Disease|Divorce|Dizzy|Dollar|Donkey|Doze|Drizzle|During|Duty|Embark|Embellish|Embrace|Emperor|Enemy|Engrave|Envy|Fade|Fail|Falcon|False|Fame|Fancy|Farm|Cover girl""".split("|"))


def language_for(head: str) -> str:
    if head in GREEK:
        return "ancient-greek"
    if head in LATIN:
        return "old-latin"
    if head in NORSE:
        return "old-norse"
    if head in MIDDLE:
        return "middle-english"
    return "old-english"


def spec(root: str, closure: str, branch: str, orbit: str, route: str, searches: list[str]) -> dict[str, Any]:
    return {
        "root": root, "closure": closure, "branch_meaning": branch,
        "orbit": orbit, "sound_route": route, "sound_searches": searches,
    }


POSITIVE: dict[str, list[dict[str, Any]]] = {
    "cipher": [spec(
        "كفر", "ROOT-ECHO", "`cipher` في النص المشفّر الذي يحجب مضمونه عن غير مالك المفتاح",
        "التشفير يكسو المعنى بترميز كثيف حتى لا يظهر المقصود تحته؛ فهذا مدار واحد إلى تغطية `كفر` التامة.",
        B.route("c↔ك=`IDN-13`", "ph/f↔ف=`IDN-06`", "r↔ر=`IDN-01`"),
        ["`c` + `ك` + «الإنجليزيّة الوسطى/Middle English»", "`f` + `ف` + «الإنجليزيّة الوسطى/Middle English»", "`r` + `ر` + «الإنجليزيّة الوسطى/Middle English»"],
    )],
    "clip": [
        spec(
            "كلب", "ROOT-TRACE", "`clip` في المشبك أو فعل التثبيت به، إذ يقبض على الشيء ولا يفلته",
            "المشبك يعض طرفي المادة ويقبض عليهما قبضًا شديدًا؛ وهذا حدث `كلب` مباشرة، ولا يدخل فيه معنى القطع المتمايز.",
            B.route("c↔ك=`IDN-13`", "l↔ل=`IDN-04`", "p↔ب=`LAB-01`"),
            ["`c` + `ك` + «النورديّة القديمة/Old Norse»", "`l` + `ل` + «النورديّة القديمة/Old Norse»", "`p` + `ب` + «النورديّة القديمة/Old Norse»"],
        ),
        spec(
            "جرف", "ROOT-TRACE", "`clip` في القطع أو تقصير طرف شيء وإزالة جزء منه",
            "القص بالمقص يقطع جزءًا من أصل مادة قابلة للقطع ويزيله؛ وهذا حدث `جرف` مباشرة، وهو مفصول عن مشبك القبض السابق.",
            B.route("c↔ج=`GUT-03`", "l↔ر=`LIQ-01`", "p↔ف=`IDN-06`"),
            ["`c` + `ج` + «النورديّة القديمة/Old Norse»", "`l` + `ر` + «النورديّة القديمة/Old Norse»", "`p` + `ف` + «النورديّة القديمة/Old Norse»"],
        ),
    ],
    "coffin": [spec(
        "جفن", "ROOT-TRACE", "`coffin`، صندوق يحيط بالجسد ويسعه ويغطيه ويحفظه",
        "التابوت غلاف محيط بجسد ذي حرمة، يسعه ويغطيه ويحفظه؛ وهذا نص حدث `جفن` مباشرة.",
        B.route("c↔ج=`GUT-03`", "ff↔ف=`IDN-06`", "n↔ن=`IDN-03`"),
        ["`c` + `ج` + «الإنجليزيّة الوسطى/Middle English»", "`f` + `ف` + «الإنجليزيّة الوسطى/Middle English»", "`n` + `ن` + «الإنجليزيّة الوسطى/Middle English»"],
    )],
    "corn": [spec(
        "قرن", "ROOT-ECHO", "`corn` في الحبّة أو السنبلة الناتئة الصلبة في أعلى ساقها",
        "الحبة والسنبلة نتوء صلب ممتد في أعلى جسم النبات؛ فهذا مدار عضوي واحد إلى نتوء `قرن`، لا دعوى أنه قرن الحيوان نفسه.",
        B.route("c↔ق=`GUT-01`", "r↔ر=`IDN-01`", "n↔ن=`IDN-03`"),
        ["`c` + `ق` + «الإنجليزيّة القديمة/Old English»", "`r` + `ر` + «الإنجليزيّة القديمة/Old English»", "`n` + `ن` + «الإنجليزيّة القديمة/Old English»"],
    )],
    "crab": [spec(
        "كلب", "ROOT-ECHO", "`crab`، الحيوان الذي تقبض كلابته على الشيء ولا تفلته",
        "كلّابة السرطان تعض المقبوض عليه وتمسكه بشدة؛ فالاسم يلتقي حدث `كلب` في عضو الحيوان المميز ومداره الحركي.",
        B.route("c↔ك=`IDN-13`", "r↔ل=`LIQ-01`", "b↔ب=`IDN-05`"),
        ["`c` + `ك` + «الإنجليزيّة القديمة/Old English»", "`r` + `ل` + «الإنجليزيّة القديمة/Old English»", "`b` + `ب` + «الإنجليزيّة القديمة/Old English»"],
    )],
    "cream": [spec(
        "كرم", "ROOT-ECHO", "`cream`، الدهن الرقيق المتجمع الصافي في أعلى اللبن، ثم خيار الشيء",
        "القشدة مادة رقيقة متجمعة مصفاة تقبلها النفس، ومنها معنى خيار الشيء؛ وهذا مدار واحد إلى حدث `كرم`.",
        B.route("c↔ك=`IDN-13`", "r↔ر=`IDN-01`", "m↔م=`IDN-02`"),
        ["`c` + `ك` + «الإنجليزيّة الوسطى/Middle English»", "`r` + `ر` + «الإنجليزيّة الوسطى/Middle English»", "`m` + `م` + «الإنجليزيّة الوسطى/Middle English»"],
    )],
    "cuff": [spec(
        "كف", "NUCLEUS-ECHO", "`cuff`، طرف الكم المطوي أو المحيط بالرسغ",
        "الكُفّة ثني لطرف الكم يجعله يحيط بموضع الكف ويقبض عليه؛ فيلتقي حدث `كف` في الانثناء والقبض بمدار واحد.",
        B.route("c↔ك=`IDN-13`", "ff↔ف=`IDN-06`"),
        ["`c` + `ك` + «الإنجليزيّة الوسطى/Middle English»", "`f` + `ف` + «الإنجليزيّة الوسطى/Middle English»"],
    )],
    "dig": [spec(
        "دق", "NUCLEUS-TRACE", "`dig`، إدخال أداة حادة في الأرض بالضغط أو الضرب",
        "الحفر يضغط طرفًا حادًا في المادة ويصدمها حتى تنفصل؛ وهذا حدث `دق` مباشرة.",
        B.route("d↔د=`IDN-09`", "g↔ق=`GUT-01`"),
        ["`d` + `د` + «الإنجليزيّة القديمة/Old English»", "`g` + `ق` + «الإنجليزيّة القديمة/Old English»"],
    )],
    "drizzle": [spec(
        "ذرذر", "ROOT-TRACE", "`drizzle`، نزول المطر في قطرات بالغة الدقة منتشرة",
        "الرذاذ نثر لدقائق الماء البالغة الدقة كأنها مسحوقة؛ وهذا نص حدث `ذرذر` مباشرة.",
        B.route("d↔ذ=`DENT-03`", "r↔ر=`IDN-01`", "z↔ذ=`DENT-04`", "l↔ر=`LIQ-01`"),
        ["`d` + `ذ` + «الإنجليزيّة الوسطى/Middle English»", "`r` + `ر` + «الإنجليزيّة الوسطى/Middle English»", "`z` + `ذ` + «الإنجليزيّة الوسطى/Middle English»", "`l` + `ر` + «الإنجليزيّة الوسطى/Middle English»"],
    )],
    "fart": [spec(
        "فرط", "ROOT-ECHO", "`fart`، اندفاع ريح من الجسد إلى خارجه",
        "الريح الخارجة جزء متسيب يندفع مبتعدًا من جرم الجسد بقوة؛ فهذا مدار حركي واحد إلى حدث `فرط`.",
        B.route("f↔ف=`IDN-06`", "r↔ر=`IDN-01`", "t↔ط=`DENT-05`"),
        ["`f` + `ف` + «الإنجليزيّة القديمة/Old English»", "`r` + `ر` + «الإنجليزيّة القديمة/Old English»", "`t` + `ط` + «الإنجليزيّة القديمة/Old English»"],
    )],
}


def candidate_review(head: str, script: str, specs: list[dict[str, Any]], root_events: dict[str, str], nucleus_events: dict[str, str]) -> tuple[list[dict[str, Any]], int]:
    base = B.F.fan(head, script)
    ranked = B.F.rank(head, base, script)
    labels = {root: "فصيح" for root in base}
    additions = 0
    if not specs:
        for root, label in B.F.fan_with_dialect(head, script):
            if root not in labels:
                labels[root] = label
                additions += 1
    selected = {item["root"] for item in specs}
    if not selected.issubset(labels):
        raise AssertionError(f"selected roots absent from fan of {head}: {selected - set(labels)}")
    weights = {root: value for root, value in ranked}
    order = list(labels)
    roots = sorted(labels, key=lambda root: (-weights.get(root, 0.0), order.index(root)))
    return ([{
        "root": root, "weight": float(weights.get(root, 0.0)), "sound": "✓",
        "event": "✓" if root in root_events or root in nucleus_events else "×",
        "meaning": "✓" if root in selected else ("×" if root in root_events or root in nucleus_events else "؟"),
        "dialect_label": None if labels[root] == "فصيح" else labels[root],
    } for root in roots], additions)


def processed_keys(payload: dict[str, Any]) -> set[str]:
    out = {item["source_row_key"] for item in payload.get("source_head_gaps", [])}
    for card in payload.get("rows", []):
        out.update(item["source_row_key"] for item in card.get("source_claims", []))
    for field in ("supplements", "khashim_card_supplements", "jassem_card_supplements"):
        for item in payload.get(field, []):
            out.update(claim["source_row_key"] for claim in item.get("source_claims", []))
    return out


def find_reading_block(text: str, marker: str) -> tuple[int, int, str]:
    at = text.index(marker)
    start = text.rfind("\n### ", 0, at)
    start = start + 1 if start >= 0 else at
    finish = text.find("\n### ", at)
    if finish < 0:
        finish = len(text)
    return start, finish, text[start:finish]


def restore_khashim_block(text: str, language: str, card_id: str) -> str:
    """Restore the whole pre-batch-002 card, preserving all older judgments."""
    path = f"04-cross-linguistic/readings/{language}.md"
    baseline = subprocess.check_output(
        ["git", "show", f"{READING_BASE_COMMIT}:{path}"],
        cwd=ROOT, text=True, encoding="utf-8",
    )
    marker = next(item for item in (f"<!-- KHASHIM-IE-MERGED:{card_id} -->", f"<!-- KHASHIM-IE-CONT:{card_id} -->") if item in text and item in baseline)
    start, finish, _ = find_reading_block(text, marker)
    _, _, old_block = find_reading_block(baseline, marker)
    return text[:start] + old_block + text[finish:]


def add_jassem_supplement(text: str, card_id: str, claims: list[dict[str, Any]]) -> str:
    marker = f"<!-- JASSEM-IE:{card_id} -->"
    start, finish, block = find_reading_block(text, marker)
    s = f"<!-- JASSEM-IE-CROSS-SUPPLEMENT-002:{card_id}:START -->"
    e = f"<!-- JASSEM-IE-CROSS-SUPPLEMENT-002:{card_id}:END -->"
    block = re.sub(rf"\n?{re.escape(s)}.*?{re.escape(e)}\n?", "\n", block, flags=re.DOTALL)
    joined = " | ".join(
        f"صف {row['source_row_index_at_freeze']}: `{B.clean(row['european'])}` ↔ `{B.clean(row['arabic_root'])}` ({B.clean(row['author_translit'])})؛ «{B.clean(row['arabic_gloss'])}» [{B.clean(row['source'])}]"
        for row in claims
    )
    block = block.rstrip() + f"\n{s}\n- إلحاق جاسم، الدفعة 002: {joined}. بقيت المروحة والحكم في البطاقة الواحدة نفسها.\n{e}\n"
    return text[:start] + block + text[finish:]


def add_khashim_supplement(text: str, card_id: str, supplement: dict[str, Any], specs: list[dict[str, Any]], root_events: dict[str, str], nucleus_events: dict[str, str], closure: str) -> str:
    marker = next(item for item in (f"<!-- KHASHIM-IE-MERGED:{card_id} -->", f"<!-- KHASHIM-IE-CONT:{card_id} -->") if item in text)
    start, finish, block = find_reading_block(text, marker)
    s = f"<!-- JASSEM-IE-SUPPLEMENT-002:{card_id}:START -->"
    e = f"<!-- JASSEM-IE-SUPPLEMENT-002:{card_id}:END -->"
    block = re.sub(rf"\n?{re.escape(s)}.*?{re.escape(e)}\n?", "\n", block, flags=re.DOTALL)
    joined = " | ".join(
        f"صف {row['source_row_index_at_freeze']}: `{B.clean(row['european'])}` ↔ `{B.clean(row['arabic_root'])}` ({B.clean(row['author_translit'])})؛ «{B.clean(row['arabic_gloss'])}» [{B.clean(row['source'])}]"
        for row in supplement["source_claims"]
    )
    lines = [s, f"- إلحاق جاسم، الدفعة 002: {joined}. قيمة `bridge_agrees=نعم` أولوية فحص وليست حكمًا."]
    for item in specs:
        root = item["root"]
        event = root_events.get(root) or nucleus_events.get(root)
        form = supplement["matched_form"]
        fan_line = re.compile(
            rf"^- فحص كل مرشحات مروحة `{re.escape(form)}`[^\n]*$",
            flags=re.MULTILINE,
        )
        line_match = fan_line.search(block)
        if not line_match:
            raise AssertionError(f"fan line missing in {card_id}:{form}")
        line, count = re.subn(
            rf"(`{re.escape(root)}`\[و[0-9.]+،)ص[✓×]،ح✓،م[✓×؟](\])",
            rf"\1ص✓،ح✓،م✓\2", line_match.group(0), count=1,
        )
        if count == 0:
            raise AssertionError(f"selected fan member missing in {card_id}:{form}:{root}")
        block = block[:line_match.start()] + line + block[line_match.end():]
        lines.extend([
            f"- إعادة حكم جاسم من المروحة كلها: `{root}`؛ مسار الصوت: {item['sound_route']}.",
            f"- الحدث المجمّد كما هو: «{event}».", f"- معنى الفرع: {item['branch_meaning']}.",
            f"- المدار الناسخ: {item['orbit']}", f"- الحصيلة الناسخة: **{item['closure']} (استكشاف)** بالمقابل `{root}`.",
        ])
    if specs:
        orbit = " ".join(item["orbit"] for item in specs)
        block, n1 = re.subn(r"^- المدار المكتوب:.*$", f"- المدار المكتوب: {orbit}", block, count=1, flags=re.MULTILINE)
        block, n2 = re.subn(r"^- الحكم \(استكشاف\):.*$", f"- الحكم (استكشاف): **{closure} (استكشاف)** من إعادة فحص جاسم للمروحة كلها.", block, count=1, flags=re.MULTILINE)
        block, n3 = re.subn(r"^- حالة الإغلاق: [A-Z +\-]+\.?$", f"- حالة الإغلاق: {closure}.", block, count=1, flags=re.MULTILINE)
        if not (n1 and n2 and n3):
            raise AssertionError(f"could not supersede {card_id}: {(n1, n2, n3)}")
    lines.append(e)
    block = block.rstrip() + "\n" + "\n".join(lines) + "\n"
    return text[:start] + block + text[finish:]


def main() -> int:
    source_text = SOURCE.read_text(encoding="utf-8")
    source_payload = json.loads(source_text)
    source_sha = hashlib.sha256(source_text.encode("utf-8")).hexdigest()
    prior_paths = sorted((ROOT / "data").glob("jassem-indo-european-batch-*.json"))
    prior_payloads: list[tuple[Path, dict[str, Any]]] = []
    done: set[str] = set()
    for path in prior_paths:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if int(payload.get("batch", 0)) < BATCH:
            prior_payloads.append((path, payload))
            done |= processed_keys(payload)
    eligible = [(i, row) for i, row in enumerate(source_payload["rows"]) if row.get("bridge_agrees") == "نعم" and B.claim_key(row) not in done]
    selected = eligible[:300]
    if len(selected) != 300:
        raise AssertionError(f"expected 300 unprocessed bridge rows, got {len(selected)}")
    gaps: list[dict[str, Any]] = []
    groups: OrderedDict[str, list[tuple[int, dict[str, Any]]]] = OrderedDict()
    for index, row in selected:
        head = str(row.get("european") or "").strip()
        claim = {"source_row_index": index, "source_row_index_at_freeze": index, "source_row_key": B.claim_key(row), **row}
        if not head:
            gaps.append({"source_row_index": index, "source_row_index_at_freeze": index, "source_row_key": B.claim_key(row), "tag": "SOURCE-HEAD-GAP", "source_claim": row})
        else:
            groups.setdefault(B.norm(head), []).append((index, claim))

    reading_texts = {lang: (READINGS / f"{lang}.md").read_text(encoding="utf-8") for lang in ALL_LANGUAGES}
    for lang, text in reading_texts.items():
        text = re.sub(rf"\n?{re.escape(START)}.*?{re.escape(END)}\n?", "\n", text, flags=re.DOTALL)
        text = re.sub(r"\n?<!-- JASSEM-IE-(?:CROSS-)?SUPPLEMENT-002:[^:]+:START -->.*?<!-- JASSEM-IE-(?:CROSS-)?SUPPLEMENT-002:[^:]+:END -->\n?", "\n", text, flags=re.DOTALL)
        reading_texts[lang] = text

    khashim_payloads = [json.loads(Path(str(KHASHIM).format(number=n)).read_text(encoding="utf-8")) for n in range(1, 11)]
    reset_khashim: set[int] = set()
    for number, payload in enumerate(khashim_payloads, 1):
        for card in payload["rows"]:
            old_rejudgments = [x for x in card.get("jassem_rejudgments", []) if x.get("batch") == BATCH]
            old_supplements = [x for x in card.get("jassem_supplements", []) if x.get("batch") == BATCH]
            if old_supplements or old_rejudgments:
                reset_khashim.add(number)
            if old_rejudgments:
                cid = card.get("merged_card_id") or card.get("card_id")
                reading_texts[card["language"]] = restore_khashim_block(reading_texts[card["language"]], card["language"], cid)
            card["jassem_supplements"] = [x for x in card.get("jassem_supplements", []) if x.get("batch") != BATCH]
            card["jassem_rejudgments"] = [x for x in card.get("jassem_rejudgments", []) if x.get("batch") != BATCH]
            if not card["jassem_supplements"]:
                card.pop("jassem_supplements", None)
            if not card["jassem_rejudgments"]:
                card.pop("jassem_rejudgments", None)
            if old_rejudgments:
                card["positives"] = [x for x in card.get("positives", []) if x.get("batch") != BATCH]
                closures = sorted({x["closure"] for x in card["positives"]})
                card["closure"] = " + ".join(closures) if closures else "OPEN-CANDIDATE"
                card["judgment"] = card["closure"] if closures else "غير صادر"

    prior_jassem: dict[str, tuple[Path, dict[str, Any], dict[str, Any]]] = {}
    for path, payload in prior_payloads:
        for card in payload.get("rows", []):
            card["later_jassem_supplements"] = [x for x in card.get("later_jassem_supplements", []) if x.get("batch") != BATCH]
            if not card["later_jassem_supplements"]:
                card.pop("later_jassem_supplements", None)
            prior_jassem[card["normalized_head"]] = (path, payload, card)

    existing_khashim: dict[str, tuple[int, dict[str, Any], str]] = {}
    for number, payload in enumerate(khashim_payloads, 1):
        for card in payload["rows"]:
            for form in B.card_forms(card):
                existing_khashim.setdefault(B.norm(form), (number, card, form))

    root_events, nucleus_events = B.load_events()
    new_cards: list[dict[str, Any]] = []
    khashim_supplements: list[dict[str, Any]] = []
    jassem_supplements: list[dict[str, Any]] = []
    ordinal = 0
    for key, members in groups.items():
        head = str(members[0][1]["european"]).strip()
        claims = [claim for _, claim in members]
        specs = POSITIVE.get(key, [])
        if key in prior_jassem:
            if specs:
                raise AssertionError(f"positive rejudgment of prior Jassem card not implemented: {head}")
            path, prior_payload, card = prior_jassem[key]
            item = {"head": head, "source_rows": [i for i, _ in members], "source_claims": claims, "target_manifest": path.name, "target_card_id": card["card_id"], "target_language": card["language"], "fan_size": len(card["fan_review"]), "reason": "same normalized Jassem head; supplement the one prior card"}
            card.setdefault("later_jassem_supplements", []).append({"batch": BATCH, "source": SOURCE.name, "source_claims": claims})
            reading_texts[card["language"]] = add_jassem_supplement(reading_texts[card["language"]], card["card_id"], claims)
            jassem_supplements.append(item)
            continue
        if key in existing_khashim:
            number, card, form = existing_khashim[key]
            cid = card.get("merged_card_id") or card.get("card_id")
            review = next((x for x in card.get("fan_reviews", []) if B.norm(x.get("form", "")) == key), None)
            if review is None:
                raise AssertionError(f"fan review missing for {head}:{cid}")
            candidate_roots = {x["root"] for x in review["candidates"]}
            if not {x["root"] for x in specs}.issubset(candidate_roots):
                raise AssertionError(f"selected Khashim roots absent for {head}")
            item = {"head": head, "source_rows": [i for i, _ in members], "source_claims": claims, "target_batch": number, "target_card_id": cid, "target_language": card["language"], "matched_form": form, "fan_size": len(review["candidates"]), "rejudgments": specs, "reason": "exact normalized form in Khashim; supplement without duplication"}
            card.setdefault("jassem_supplements", []).append({"batch": BATCH, "source": SOURCE.relative_to(ROOT).as_posix(), "source_claims": claims})
            for judged in specs:
                event = root_events.get(judged["root"]) or nucleus_events.get(judged["root"])
                enriched = {**judged, "frozen_event": event}
                card.setdefault("jassem_rejudgments", []).append({"batch": BATCH, "source": SOURCE.relative_to(ROOT).as_posix(), "source_claims": claims, **enriched})
                if not any(x.get("root") == judged["root"] and x.get("batch") == BATCH for x in card.get("positives", [])):
                    card.setdefault("positives", []).append({"batch": BATCH, "source": SOURCE.relative_to(ROOT).as_posix(), "form": head, **enriched, "event_source": "computational/data/layer_2_results_v2.jsonl؛ jabal_axial" if judged["root"] in root_events else "data/juthoor-core-levels.json؛ jabal_lexicon_reading_ar"})
            closures = sorted({x["closure"] for x in card.get("positives", [])})
            card["closure"] = " + ".join(closures) if closures else "OPEN-CANDIDATE"
            card["judgment"] = card["closure"] if closures else "غير صادر"
            reading_texts[card["language"]] = add_khashim_supplement(reading_texts[card["language"]], cid, item, specs, root_events, nucleus_events, card["closure"])
            khashim_supplements.append(item)
            continue
        ordinal += 1
        language = language_for(head)
        script = B.script_for(language)
        review, additions = candidate_review(head, script, specs, root_events, nucleus_events)
        positives = []
        for judged in specs:
            event = root_events.get(judged["root"]) or nucleus_events.get(judged["root"])
            positives.append({**judged, "frozen_event": event, "event_source": "computational/data/layer_2_results_v2.jsonl؛ jabal_axial" if judged["root"] in root_events else "data/juthoor-core-levels.json؛ jabal_lexicon_reading_ar"})
        closures = sorted({x["closure"] for x in positives})
        closure = " + ".join(closures) if closures else "OPEN-CANDIDATE"
        new_cards.append({"card_id": f"JAS-IE-002-{ordinal:03d}", "batch": BATCH, "head": head, "normalized_head": key, "language": language, "script": script, "skeleton": B.F.skeleton(head, script), "source_rows": [i for i, _ in members], "source_claims": claims, "fan_review": review, "dialect_additions": additions, "positives": positives, "closure": closure, "judgment": closure if positives else "غير صادر"})

    if len(gaps) + sum(len(x) for x in groups.values()) != 300:
        raise AssertionError("source coverage failed")
    if len(groups) != len(new_cards) + len(khashim_supplements) + len(jassem_supplements):
        raise AssertionError("one-card grouping failed")

    by_language: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for card in new_cards:
        by_language[card["language"]].append(card)
    for language, cards in by_language.items():
        lines = [START, "", "## حصادُ زيدان علي جاسم الهنديّ الأوربيّ، دفعة الموافقات 002 (2026-08-13)", "", f"- في هذا الملف {len(cards)} بطاقة جديدة؛ اتبع الإسناد مادة الكلمة لا ترتيب ملف المصدر.", "- `bridge_agrees=نعم` قدّم الصف للفحص فقط؛ الحكم لا يصدر إلا بمسار صوت مسمى، وحدث مجمد كما هو، ومعنى فرع ومدار إنساني مكتوب.", "- فُحصت المروحة كلها مرتبة بـ`F.rank`، واستُعمل `fan_with_dialect` بعد عجز الفصيح؛ الوزن ترتيب لا حكم.", ""]
        for card in cards:
            lines.extend(B.render_card(card))
        lines.append(END)
        reading_texts[language] = reading_texts[language].rstrip() + "\n\n" + "\n".join(lines) + "\n"
    for language, text in reading_texts.items():
        (READINGS / f"{language}.md").write_text(text, encoding="utf-8", newline="\n")

    changed_khashim = reset_khashim | {x["target_batch"] for x in khashim_supplements}
    for number in changed_khashim:
        Path(str(KHASHIM).format(number=number)).write_text(json.dumps(khashim_payloads[number - 1], ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    for path, payload in prior_payloads:
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")

    positive_new = [card for card in new_cards if card["positives"]]
    positive_existing = [item for item in khashim_supplements if item["rejudgments"]]
    all_candidates = sum(len(card["fan_review"]) for card in new_cards) + sum(x["fan_size"] for x in khashim_supplements + jassem_supplements)
    payload = {
        "schema": "jassem-indo-european-batch-v1.0", "date": "2026-08-13", "source_author": "زيدان علي جاسم", "source_affiliation": "جامعة القصيم", "source": SOURCE.relative_to(ROOT).as_posix(), "layer": "exploration", "batch": BATCH,
        "selection": {"criterion": "first 300 bridge_agrees=نعم claims whose stable source_row_key is absent from earlier Jassem manifests", "row_identity": "SHA-256/24 of normalized european + arabic_root + arabic_gloss + author_translit; indices are freeze-time locators", "source_sha256_at_freeze": source_sha, "prior_claim_keys_excluded": len(done), "eligible_unprocessed_at_freeze": len(eligible), "selected_source_rows": 300, "first_source_row_index": selected[0][0], "last_source_row_index": selected[-1][0], "source_head_gaps": len(gaps), "nonempty_source_rows": 300 - len(gaps), "unique_european_heads": len(groups)},
        "jassem_transliteration": {"3": "ع", "2": "ح", "kh": "خ", "gh": "غ", "T": "ط", "D": "ض", "S": "ص", "Dh": "ظ", "'": "ء"},
        "merge_policy": {"same_normalized_head": "one card across Jassem batches and Khashim books", "snapshot_absence": "never a judgment condition", "judgment_legs": ["named sound route", "frozen event verbatim", "branch meaning with human-written orbit"], "bridge_agrees": "priority signal only"},
        "cards_touched": len(groups), "new_cards_written": len(new_cards), "khashim_card_supplements_count": len(khashim_supplements), "jassem_card_supplements_count": len(jassem_supplements), "newly_issued_positive_cards": len(positive_new) + len(positive_existing), "newly_issued_positive_roots": sum(len(x["positives"]) for x in positive_new) + sum(len(x["rejudgments"]) for x in positive_existing), "open_new_cards": len(new_cards) - len(positive_new),
        "new_cards_by_language": dict(sorted(Counter(x["language"] for x in new_cards).items())),
        "rank_review": {"method": "F.rank", "ranked_candidates_in_new_or_referenced_full_fans": all_candidates, "new_card_fan_with_dialect_additions": sum(x["dialect_additions"] for x in new_cards), "policy": "weight orders display and never judges"},
        "source_head_gaps": gaps, "jassem_card_supplements": jassem_supplements, "khashim_card_supplements": khashim_supplements, "rows": new_cards,
    }
    MANIFEST.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")

    highlights = [
        "`Cipher` ↔ `كفر`: الشفرة تغطي المعنى تغطية لا يظهر معها لغير مالك المفتاح؛ `ROOT-ECHO`.",
        "`Clip` فُصل فيه المشبك القابض `كلب` عن فعل القص `جرف`؛ مساران تامان في بطاقة واحدة بلا خلط المتجانسين.",
        "`Coffin` ↔ `جفن`: التابوت غلاف يسع الجسد ويغطيه ويحفظه؛ `ROOT-TRACE`.",
        "`Corn` دُمجت في بطاقة خشيم القائمة، وأخرجت المروحة `قرن` في النتوء الصلب أعلى النبات؛ `ROOT-ECHO`.",
        "`Crab` دُمجت في بطاقة خشيم؛ كلّابته تعض المقبوض وتمسكه في حدث `كلب`؛ `ROOT-ECHO`.",
        "`Cream` ↔ `كرم`: مادة رقيقة متجمعة صافية مقبولة، ومنها خيار الشيء؛ `ROOT-ECHO`.",
        "`Cuff` ↔ `كف`: طرف مطوي يحيط بالرسغ ويقبض عليه؛ `NUCLEUS-ECHO`.",
        "`Dig` دُمجت في بطاقة خشيم؛ الحفر ضغط أو صدم بطرف حاد في حدث `دق`؛ `NUCLEUS-TRACE`.",
        "`Drizzle` ↔ `ذرذر`: المطر نثر لدقائق الماء البالغة الدقة؛ `ROOT-TRACE`.",
        "`Fart` ↔ `فرط`: اندفاع جزء متسيب من الجسد مبتعدًا بقوة؛ `ROOT-ECHO`.",
    ]
    if not set(POSITIVE).issubset(groups):
        raise AssertionError(f"highlight positives left the frozen selection: {set(POSITIVE) - set(groups)}")
    audit = [
        "# محضر حصاد جاسم الهنديّ الأوربيّ، دفعة الموافقات 002 (2026-08-13)", "", "## النطاق والحصيلة", "",
        f"- انتُخبت 300 هوية موافقة غير معالجة بعد استبعاد {len(done)} مفتاحًا ثابتًا مودعًا في الدفعات السابقة؛ كان الباقي عند التجميد {len(eligible)}.",
        f"- انكمشت الصفوف إلى {len(groups)} كلمة: {len(jassem_supplements)} إلحاقًا ببطاقات جاسم السابقة، و{len(khashim_supplements)} إلحاقًا ببطاقات خشيم، و{len(new_cards)} بطاقة جديدة؛ فجوات المدخل={len(gaps)}.",
        f"- صدر {len(positive_new) + len(positive_existing)} حكمًا موجبًا على بطاقات و{payload['newly_issued_positive_roots']} مقابلًا، وبقي {len(new_cards) - len(positive_new)} من البطاقات الجديدة مفتوحًا.",
        "- توزيع البطاقات الجديدة: " + "، ".join(f"{B.LANG_LABELS[k]}={v}" for k, v in sorted(Counter(x['language'] for x in new_cards).items())) + ".",
        f"- فُحص أو روجع {all_candidates} مرشحًا في المراوح الكاملة المرتبة بـ`F.rank`؛ أضاف `fan_with_dialect` {sum(x['dialect_additions'] for x in new_cards)} صورة بعد عجز الفصيح، والوزن لم يحكم.",
        "", "## أسباب الأحكام", "",
        "- موافقة الجسر رتبت الطابور ولم تدخل الحكم؛ كل موجب أعلاه استوفى مسارًا مسمى وحدثًا مجمدًا ومدارًا مكتوبًا.",
        "- جمعت الكلمة الواحدة عبر الدفعات والكتابين؛ والإلحاق يشير إلى المروحة الكاملة في البطاقة الأصلية بدل إنشاء نسخة.",
        "- فُصلت معاني الرسم الواحد حين اختلف الحدث، كما في مشبك `clip` وفعل القص، ولم يرث أحدهما حكم الآخر.",
        "- غياب الصورة من اللقطة لم يدخل الحكم، وأرقام الصفوف مواضع تجميد لا هويات.",
        "", "## عشرة مواضع بارزة", "",
    ] + [f"{i}. {line}" for i, line in enumerate(highlights, 1)] + [
        "", "## تحقق الإيداع", "", "- البيان: `data/jassem-indo-european-batch-002.json`.", "- القراءة: الملفات الثمانية المسموح بها وحدها، مع الإلحاق داخل البطاقة الأصلية.", "- الإيداع يُجرى بأمر `scripts/ship.py --only ... --push` بعد خضرة البوابات.",
    ]
    AUDIT.write_text("\n".join(audit) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"selected": 300, "heads": len(groups), "gaps": len(gaps), "new_cards": len(new_cards), "jassem_supplements": len(jassem_supplements), "khashim_supplements": len(khashim_supplements), "positive_cards": len(positive_new) + len(positive_existing), "positive_roots": payload["newly_issued_positive_roots"], "candidates": all_candidates, "languages": Counter(x["language"] for x in new_cards)}, ensure_ascii=False, default=dict))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
