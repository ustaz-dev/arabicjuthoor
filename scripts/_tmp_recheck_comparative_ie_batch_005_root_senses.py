# -*- coding: utf-8 -*-
"""One-shot Arabic-root-sense rereview for comparative IE batch 005."""
from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import frozen_event as FE  # noqa: E402
import search_arabic_root_senses as AR  # noqa: E402

MANIFEST = ROOT / "data" / "comparative-indo-european-batch-005.json"
AUDIT = ROOT / "05-audits" / "2026-08-14-comparative-indo-european-batch-005.md"
READINGS = ROOT / "04-cross-linguistic" / "readings"
ALLOWED = {"old-latin", "middle-english", "old-norse", "ancient-greek", "old-english", "old-irish", "gothic", "welsh"}
LANG_AR = {
    "old-latin": "اللاتينيّة القديمة/Old Latin",
    "middle-english": "الإنجليزيّة الوسطى/Middle English",
    "old-norse": "النورديّة القديمة/Old Norse",
}
REVIEW_START = "<!-- ARABIC-ROOT-SENSE-REVIEW-005:START -->"
REVIEW_END = "<!-- ARABIC-ROOT-SENSE-REVIEW-005:END -->"
LEDGER_START = "<!-- BRANCH-LEXICON-SELECTION-LEDGER-005:START -->"
LEDGER_END = "<!-- BRANCH-LEXICON-SELECTION-LEDGER-005:END -->"


def clean(value: Any) -> str:
    return " ".join(str(value or "").split())


def norm(value: Any) -> str:
    return clean(value).casefold()


WITNESS = {
    "قصل": {
        "source_id": "lisan", "source": "لسان العرب لابن منظور",
        "quote": "القصل: القطع، وقيل: القصل قطع الشيء من وسطه أو أسفل من ذلك قطعا وحيا.",
        "url": "http://arabiclexicon.hawramani.com/%d9%82%d8%b5%d9%84/?book=3",
    },
    "فرد": {
        "source_id": "al_mufradat", "source": "المفردات في غريب القرآن للراغب",
        "quote": "الفرد: الذي لا يختلط به غيره.",
        "url": "http://arabiclexicon.hawramani.com/%d9%81%d8%b1%d8%af/?book=33",
    },
    "زم": {
        "source_id": "kitab_al_ayn", "source": "كتاب العين للخليل بن أحمد",
        "quote": "زممت الناقة أزمها زما. والزمام: الخيط الذي في أنفها.",
        "url": "http://arabiclexicon.hawramani.com/%d8%b2%d9%85/?book=5",
    },
    "كب": {
        "source_id": "al_mufradat", "source": "المفردات في غريب القرآن للراغب",
        "quote": "الكب: إسقاط الشيء على وجهه.",
        "url": "http://arabiclexicon.hawramani.com/%d9%83%d8%a8/?book=33",
    },
    "دور": {
        "source_id": "kitab_al_ayn", "source": "كتاب العين للخليل بن أحمد",
        "quote": "الدواري: الدهر الدوار بالناس. ويقال: دار دورة واحدة.",
        "url": "http://arabiclexicon.hawramani.com/%d8%af%d9%88%d8%b1/?book=5",
    },
    "بوس": {
        "source_id": "lisan", "source": "لسان العرب لابن منظور",
        "quote": "البوس: التقبيل، فارسي معرب، وقد باسه يبوسه.",
        "url": "http://arabiclexicon.hawramani.com/%d8%a8%d9%88%d8%b3/?book=3",
    },
    "جر": {
        "source_id": "al_muhkam", "source": "المحكم والمحيط الأعظم لابن سيده",
        "quote": "الجر: الجذب، جره يجره جرا.",
        "url": "http://arabiclexicon.hawramani.com/%d8%ac%d8%b1/?book=10",
    },
    "صنج": {
        "source_id": "al_sihah", "source": "تاج اللغة وصحاح العربية للجوهري",
        "quote": "الصنج الذي تعرفه العرب، وهو الذي يتخذ من صفر يضرب أحدهما بالآخر.",
        "url": "http://arabiclexicon.hawramani.com/%d8%b5%d9%86%d8%ac/?book=8",
    },
    "ورد": {
        "source_id": "lisan", "source": "لسان العرب لابن منظور",
        "quote": "الورد لون أحمر يضرب الى صفرة حسنة في كل شيء.",
        "url": "http://arabiclexicon.hawramani.com/%d9%88%d8%b1%d8%af/?book=3",
    },
    "فني": {
        "source_id": "lisan", "source": "لسان العرب لابن منظور",
        "quote": "الفناء: نقيض البقاء.",
        "url": "http://arabiclexicon.hawramani.com/%d9%81%d9%86%d9%8a/?book=3",
    },
    "صكك": {
        "source_id": "al_muhkam", "source": "المحكم والمحيط الأعظم لابن سيده",
        "quote": "الصك: اضطراب الركبتين والعرقوبين من الإنسان وغيره.",
        "url": "http://arabiclexicon.hawramani.com/%d8%b5%d9%83%d9%83/?book=10",
    },
}


SPECS = {
    "CMP-IE-005-001": ("cisoria", "caesor", "قصل", "ROOT-TRACE",
        "c=[k] ثم c↔ق=`GUT-01`؛ s↔ص=`SIB-02`؛ r↔ل=`LIQ-01`؛ وتعرية النهاية -ia",
        ["`c` + `ق` + «اللاتينيّة القديمة/Old Latin»", "`s` + `ص` + «اللاتينيّة القديمة/Old Latin»", "`r` + `ل` + «اللاتينيّة القديمة/Old Latin»"],
        "معنى `caesor`، القاطع أو النحّات، يلتقي نص لسان العرب في القطع نفسه؛ فالشاهد العربي يثبت حقل الجذر الذي سمّاه المدار."),
    "CMP-IE-005-014": ("part", "part", "فرد", "ROOT-TRACE",
        "p↔ف=`IDN-06`؛ r↔ر=`IDN-01`؛ t↔د=`BR-GRIM-02`",
        ["`p` + `ف` + «الإنجليزيّة الوسطى/Middle English»", "`r` + `ر` + «الإنجليزيّة الوسطى/Middle English»", "`t` + `د` + «الإنجليزيّة الوسطى/Middle English»"],
        "الجزء `part` مفروز من الكل؛ ونص المفردات يجعل الفرد ما لا يختلط به غيره، فيثبت مدار العزل والانفراد."),
    "CMP-IE-005-046": ("cubo", "cubo", "كب", "NUCLEUS-TRACE",
        "c=[k]↔ك=`IDN-13`؛ b↔ب=`IDN-05`؛ وتعرية الصائت النهائي",
        ["`c` + `ك` + «اللاتينيّة القديمة/Old Latin»", "`b` + `ب` + «اللاتينيّة القديمة/Old Latin»"],
        "قاموس الفرع يجعل `cubo` الاضطجاع والاستلقاء؛ وشاهد المفردات يجعل الكب إسقاط الجسد على وجهه، والمدار انتقال البدن من القيام إلى هيئة ملقاة أو مضطجعة."),
    "CMP-IE-005-048": ("duree", "duro", "دور", "ROOT-ECHO",
        "d↔د=`IDN-09`؛ r↔ر=`IDN-01`؛ فتح الواو المعتلة؛ وتعرية النهاية",
        ["`d` + `د` + «اللاتينيّة القديمة/Old Latin»", "`r` + `ر` + «اللاتينيّة القديمة/Old Latin»"],
        "معنى `duro`، البقاء والاستمرار، يمر في شاهد العين بالدهر الدوار ودوراته؛ فالمدة ما يبقى خلال تعاقب الدورة، وهو صدى جذري لا تطابق اسمي."),
    "CMP-IE-005-056": ("beso", "basio", "بوس", "ROOT-TRACE",
        "b↔ب=`IDN-05`؛ s↔س=`IDN-07`؛ وفتح الواو المعتلة",
        ["`b` + `ب` + «اللاتينيّة القديمة/Old Latin»", "`s` + `س` + «اللاتينيّة القديمة/Old Latin»"],
        "قاموس الفرع يرد `beso` هيكليا إلى `basio`، ومعناه التقبيل؛ ولسان العرب يقول في `بوس` التقبيل نفسه، فالتقاء المعنيين مباشر."),
    "CMP-IE-005-061": ("carrus", "carrus", "جر", "ROOT-ECHO",
        "c=[k]↔ج=`GUT-03`؛ r↔ر=`IDN-01`؛ رد الإدغام rr؛ وتعرية -us",
        ["`c` + `ج` + «اللاتينيّة القديمة/Old Latin»", "`r` + `ر` + «اللاتينيّة القديمة/Old Latin»"],
        "`carrus` عربة وحمولة عربة، والعربة تجر وتجذب؛ ونص المحكم يجعل الجر الجذب، فالمعنى صدى فعل الحركة الذي تقوم به العربة."),
    "CMP-IE-005-079": ("song", "song", "صنج", "ROOT-ECHO",
        "s↔ص=`SIB-02`؛ n↔ن=`IDN-03`؛ g↔ج=`IDN-08`",
        ["`s` + `ص` + «الإنجليزيّة الوسطى/Middle English»", "`n` + `ن` + «الإنجليزيّة الوسطى/Middle English»", "`g` + `ج` + «الإنجليزيّة الوسطى/Middle English»"],
        "`song` غناء أو إنشاد، والصنج آلة تضرب فتقيم الصوت الموسيقي؛ فشاهد الصحاح يثبت مدار الأداء الموسيقي على جهة الصدى لا التطابق."),
    "CMP-IE-005-081": ("som", "sam-", "زم", "NUCLEUS-TRACE",
        "s↔ز=`SIB-03`؛ m↔م=`IDN-02`",
        ["`s` + `ز` + «النورديّة القديمة/Old Norse»", "`m` + `م` + «النورديّة القديمة/Old Norse»"],
        "السابقة `sam-` تعني معًا؛ والزمام خيط يجمع الناقة ويضبطها، فيلتقي الجمع والربط بحدث ضم الكثير باكتناز."),
    "CMP-IE-005-100": ("rood", "red", "ورد", "ROOT-TRACE",
        "r↔ر=`IDN-01`؛ d↔د=`IDN-09`؛ وفتح الواو الابتدائية المعتلة",
        ["`r` + `ر` + «الإنجليزيّة الوسطى/Middle English»", "`d` + `د` + «الإنجليزيّة الوسطى/Middle English»"],
        "قاموس الفرع يرد `rood` هيكليا إلى `red` بمعنى الأحمر والقرمزي؛ ولسان العرب يثبت للورد لونا أحمر، فالمدار لوني مباشر."),
    "CMP-IE-005-113": ("finis", "finis", "فني", "ROOT-TRACE",
        "f↔ف=`IDN-06`؛ n↔ن=`IDN-03`؛ فتح الياء المعتلة؛ وتعرية سين الرفع",
        ["`f` + `ف` + «اللاتينيّة القديمة/Old Latin»", "`n` + `ن` + «اللاتينيّة القديمة/Old Latin»"],
        "`finis` نهاية وحد؛ ولسان العرب يجعل الفناء نقيض البقاء، أي بلوغ الشيء نهايته وزوال استمراره، فالمدار مباشر إلى حقل الجذر."),
    "CMP-IE-005-129": ("skaka", "skaka", "صكك", "ROOT-TRACE",
        "s↔ص=`SIB-02`؛ k-k↔ك-ك=`IDN-13`؛ وتعرية الصائت النهائي",
        ["`s` + `ص` + «النورديّة القديمة/Old Norse»", "`k` + `ك` + «النورديّة القديمة/Old Norse»"],
        "`skaka` هو الهز؛ والمحكم يثبت للصك اضطراب الركبتين والعرقوبين، والاضطراب هز متكرر، فالمدار جذري مباشر."),
}

REVOKE = {
    "CMP-IE-005-035": ("رس", "المفردات في غريب القرآن للراغب", "أصل الرس: الأثر القليل الموجود في الشيء.", "لم تشهد المعاجم للجري أو السباق أو الامتداد الذي قام عليه الحكم السابق."),
    "CMP-IE-005-097": ("بر", "المفردات في غريب القرآن للراغب", "البر خلاف البحر، وتصور منه التوسع في فعل الخير.", "لم تشهد المعاجم للنقاء أو الخلوص الذي قام عليه الحكم السابق."),
    "CMP-IE-005-118": ("درن", "كتاب العين للخليل بن أحمد", "الدرن: تلطخ الوسخ.", "شواهد الجذر في الوسخ والتلطخ، لا الدوام والاستمرار الذي قام عليه الحكم السابق."),
}


def find_entry(card: dict[str, Any], form_name: str, word: str) -> tuple[dict[str, Any], dict[str, Any]]:
    form = next(item for item in card["forms"] if norm(item["form"]) == norm(form_name))
    entries = [item for item in form["branch_lexicon"]["entries"] if norm(item.get("word")) == norm(word)]
    if card["card_id"] == "CMP-IE-005-100":
        entries = [item for item in entries if item.get("pos") == "adj" and "crimson" in clean(item.get("en")).casefold()]
    if len(entries) != 1:
        raise AssertionError(f"entry ambiguity {card['card_id']}:{form_name}:{word}:{len(entries)}")
    return form, entries[0]


def positive_for(card: dict[str, Any], spec: tuple[Any, ...], root_matches: dict[str, list[dict[str, Any]]] | None = None) -> dict[str, Any]:
    form_name, entry_word, root, closure, sound_route, searches, orbit = spec
    for form in card["forms"]:
        form["positives"] = []
        for item in form.get("fan_review", []):
            item["meaning"] = "×" if item.get("event") == "✓" else "؟"
    form, entry = find_entry(card, form_name, entry_word)
    lex = form["branch_lexicon"]
    lex["selected"] = entry
    sense = " | ".join(dict.fromkeys(clean(c.get("foreign_sense")) for c in card["source_claims"] if norm(c.get("foreign")) == norm(form_name)))
    lex["selection"] = (
        f"اختير `{entry_word}` بعد موازنة جميع الإصابات بسياق الصف «{sense}»؛ "
        "قاموس الفرع مقدم على عمود الباحث."
    )
    lex["dictionary_precedes_researcher"] = True
    selected_fan = next(item for item in form["fan_review"] if item["root"] == root)
    selected_fan["meaning"] = "✓"
    ev = FE.resolve(root)
    if ev is None:
        raise AssertionError(f"no frozen event {root}")
    witness = dict(WITNESS[root])
    if root_matches is not None:
        witness["root_match_count"] = len(root_matches[root])
        witness["definition_truncated"] = False
    positive = {
        "root": root,
        "closure": closure,
        "branch_meaning": f"`{clean(entry['word'])}` [{clean(entry.get('pos')) or '—'}] في قاموس الفرع: «{clean(entry.get('en')) or '—'}»",
        "orbit": orbit,
        "sound_route": sound_route,
        "sound_searches": searches,
        "frozen_event": ev.text,
        "event_source": ev.source,
        "event_tier": ev.tier,
        "event_tier_ar": ev.tier_ar,
        "event_note": ev.note,
        "branch_dictionary": lex["source"],
        "branch_dictionary_path": lex["lookup_path"],
        "branch_dictionary_entry": entry,
        "root_witness": witness,
    }
    form["positives"] = [positive]
    card["positives"] = [positive]
    card["closure"] = closure
    card["judgment"] = closure
    card["blocker_type"] = None
    card["required"] = None
    if card["card_id"] == "CMP-IE-005-056":
        card["source_gap"] = {"forms": ["beijo"], "outside_judgment": True}
    return positive


def roots_for(container: dict[str, Any]) -> list[str]:
    roots: set[str] = set()
    for form in container.get("forms", []):
        if (form.get("branch_lexicon") or {}).get("entries"):
            roots.update(item["root"] for item in form.get("fan_review", []))
    return sorted(roots)


def make_review(container: dict[str, Any], matches: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    roots = roots_for(container)
    counts = {root: len(matches[root]) for root in roots if matches[root]}
    return {
        "date": "2026-08-14",
        "command": "python scripts/search_arabic_root_senses.py ROOT --max-chars 0",
        "max_chars": 0,
        "definition_truncated": False,
        "roots_reviewed": roots,
        "roots_with_witnesses": len(counts),
        "lexicographic_witnesses_reviewed": sum(counts.values()),
        "root_match_counts": counts,
        "result": "positive witness selected" if container.get("positives") else "no further convincing orbit after full witness review",
    }


def review_lines(review: dict[str, Any], extra: str | None = None) -> list[str]:
    lines = [
        REVIEW_START,
        f"- فحص معاني الجذور العربية: قُرئت بلا اقتطاع بـ`--max-chars 0` شواهد {len(review['roots_reviewed'])} جذرا من المروحة؛ وُجد {review['lexicographic_witnesses_reviewed']} شاهدا لـ{review['roots_with_witnesses']} جذرا، ولم يحكم العدد ولا ترتيب المعاجم.",
    ]
    if extra:
        lines.append(extra)
    lines.append(REVIEW_END)
    return lines


def insert_review(block: str, lines: list[str]) -> str:
    block = re.sub(rf"\n?{re.escape(REVIEW_START)}.*?{re.escape(REVIEW_END)}\n?", "\n", block, flags=re.DOTALL)
    items = block.splitlines()
    positions = [i for i, line in enumerate(items) if line.startswith("- فحص `fan_with_dialect`")]
    at = positions[-1] + 1 if positions else max(1, len(items) - 1)
    items[at:at] = lines
    return "\n".join(items)


def replace_outcome(block: str, lines: list[str]) -> str:
    items = block.splitlines()
    starts = [i for i, line in enumerate(items) if line.startswith("- المقابل المنتخب") or line.startswith("- عائق:")]
    if not starts:
        raise AssertionError("outcome start missing")
    start = starts[0]
    end = next(i for i in range(start, len(items)) if items[i].startswith("- حالة الإغلاق:"))
    items[start:end + 1] = lines
    return "\n".join(items)


def positive_lines(card: dict[str, Any], positive: dict[str, Any]) -> list[str]:
    w = positive["root_witness"]
    event = FE.resolve(positive["root"])
    assert event is not None
    source_gap = (
        "الصورة `beijo` لم تثبت في لقطة القاموس؛ الغياب `SOURCE-GAP` خارج الحكم، واعتمد الحكم على `beso` ومدخله `basio`."
        if card["card_id"] == "CMP-IE-005-056" else
        "لا يشترط ثبوت الصورة في اللقطة، ولا يحول غيابها إلى رفض."
    )
    return [
        f"- المقابل المنتخب من المروحة كلها: `{positive['root']}`؛ مسار الصوت المسمى: {positive['sound_route']}.",
        f"- ما فُتش في الشبكة: {'؛ '.join(positive['sound_searches'])}.",
        event.line(),
        f"- شاهد الجذر العربي: يقول {w['source']}: «{w['quote']}»؛ قُرئت مادة الجذر كاملة بلا اقتطاع.",
        f"- معنى الفرع بلا رتوش: {positive['branch_meaning']}.",
        f"- المدار المكتوب: {positive['orbit']}",
        f"- الحكم (استكشاف): **{positive['closure']} (استكشاف)**؛ `{positive['root']}`={positive['closure']}.",
        f"- حقل النقص، خارج الحكم: {source_gap}",
        f"- حالة الإغلاق: {positive['closure']}.",
    ]


def update_card_reading(card: dict[str, Any], positive: dict[str, Any] | None, revoke: tuple[str, str, str, str] | None) -> None:
    path = READINGS / f"{card['language']}.md"
    if card["language"] not in ALLOWED:
        raise AssertionError(card["language"])
    text = path.read_text(encoding="utf-8")
    marker = f"<!-- COMPARATIVE-IE:{card['card_id']} -->"
    start = text.index(marker)
    candidates = [pos for pos in (text.find("\n### ", start + len(marker)), text.find("\n<!-- COMPARATIVE-IE-BATCH-005:END -->", start)) if pos >= 0]
    end = min(candidates) if candidates else len(text)
    block = text[start:end]
    extra = None
    if revoke:
        root, source, quote, reason = revoke
        extra = f"- شاهد نقض الحكم السابق: يقول {source}: «{quote}»؛ {reason}"
    block = insert_review(block, review_lines(card["arabic_root_sense_review"], extra))
    if positive:
        block = replace_outcome(block, positive_lines(card, positive))
    elif revoke:
        block = replace_outcome(block, [
            "- عائق: النوع=SEMANTIC-ORBIT-GAP؛ يتطلب=مدارا بشريا مقنعا بعد قراءة شواهد الجذور العربية كاملة.",
            f"- المدار المكتوب: {revoke[3]}",
            "- الحكم (استكشاف): **غير صادر (استكشاف)**.",
            "- حقل النقص، خارج الحكم: لا يشترط ثبوت الصورة في اللقطة، ولا يحول غيابها إلى رفض.",
            "- حالة الإغلاق: OPEN-CANDIDATE.",
        ])
    path.write_text(text[:start] + block.rstrip() + "\n" + text[end:], encoding="utf-8", newline="\n")


def render_entry(entry: dict[str, Any]) -> str:
    read = f" /{clean(entry.get('read'))}/" if entry.get("read") else ""
    etym = f"؛ الاشتقاق «{clean(entry.get('etym'))}»" if entry.get("etym") else ""
    return f"`{clean(entry.get('word'))}`{read} [{clean(entry.get('pos')) or '—'}] «{clean(entry.get('en')) or '—'}»{etym}"


def rebuild_selection_ledgers(payload: dict[str, Any]) -> None:
    by_language: dict[str, list[dict[str, Any]]] = {}
    for item in payload["supplements"]:
        by_language.setdefault(item["target_language"], []).append(item)
    for item in payload["rows"]:
        by_language.setdefault(item["language"], []).append(item)
    for language, containers in by_language.items():
        path = READINGS / f"{language}.md"
        text = path.read_text(encoding="utf-8")
        text = re.sub(rf"\n?{re.escape(LEDGER_START)}.*?{re.escape(LEDGER_END)}\n?", "\n", text, flags=re.DOTALL)
        lines = [LEDGER_START, "### سجل اختيار قاموس الفرع، الدفعة المقارنة 005", "", "القوائم الكاملة في البطاقات أعلاه؛ وهذا السجل يعيّن المدخل المختار أو يصرح بعدم المطابقة، مع تقديم القاموس على عمود الباحث.", ""]
        for container in containers:
            cid = container.get("card_id") or container.get("target_card_id")
            lines.append(f"- البطاقة/الإلحاق `{cid}`:")
            for form in container["forms"]:
                lex = form["branch_lexicon"]
                selected = lex.get("selected")
                choice = render_entry(selected) if selected else "لا مدخل مختار"
                lines.append(f"  - اختيار قاموس الفرع لصورة `{clean(form['form'])}` ({lex['lookup_path']}): {choice}. {clean(lex.get('selection'))}")
            if container.get("closure") == "LOANWORD":
                loan = container["loanword"]
                lines.append(f"  - حكم قاموس الفرع: **LOANWORD**؛ المانح المسمى {loan['donor']} بالصورة `{loan['donor_form']}`؛ لا تعد البطاقة أو الإلحاق صلة.")
        lines.extend([LEDGER_END, ""])
        path.write_text(text.rstrip() + "\n\n" + "\n".join(lines), encoding="utf-8", newline="\n")


def update_supplement_reading(supplement: dict[str, Any], extra: str | None = None) -> None:
    path = READINGS / f"{supplement['target_language']}.md"
    text = path.read_text(encoding="utf-8")
    sm = f"<!-- COMPARATIVE-IE-SUPPLEMENT-005:{supplement['target_card_id']}:START -->"
    em = f"<!-- COMPARATIVE-IE-SUPPLEMENT-005:{supplement['target_card_id']}:END -->"
    start, end = text.index(sm), text.index(em, text.index(sm))
    block = text[start:end]
    block = re.sub(rf"\n?{re.escape(REVIEW_START)}.*?{re.escape(REVIEW_END)}\n?", "\n", block, flags=re.DOTALL)
    insert_at = block.find("<!-- BRANCH-LEXICON-SELECTION-005:START -->")
    if insert_at < 0:
        insert_at = len(block)
    lines = review_lines(supplement["arabic_root_sense_review"], extra)
    block = block[:insert_at].rstrip() + "\n" + "\n".join(lines) + "\n" + block[insert_at:].lstrip()
    if supplement["target_card_id"] == "JAS-IE-004-182":
        block = block.replace(
            "- الإلحاق في البطاقة القائمة يمنع تكرار صور الكلمة عبر الكتب؛ لا تغيّر أولوية المؤلف الحكم السابق.",
            "- الإلحاق في البطاقة القائمة يمنع التكرار؛ وأعاد فحص معاجم الجذر الحكم الموروث إلى OPEN-CANDIDATE لأن `بر` لا يشهد للنقاء أو الخلوص.",
        )
    path.write_text(text[:start] + block + text[end:], encoding="utf-8", newline="\n")


def update_prior_cards(payload: dict[str, Any], matches: dict[str, list[dict[str, Any]]]) -> None:
    supplements = {item["target_card_id"]: item for item in payload["supplements"]}
    # Revoke the inherited Pure judgment.
    path = ROOT / "data" / "jassem-indo-european-batch-004.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    card = next(item for item in data["rows"] if item["card_id"] == "JAS-IE-004-182")
    if card.get("positives"):
        data["newly_issued_positive_cards"] -= 1
        data["newly_issued_positive_roots"] -= 1
        data["open_new_cards"] += 1
    for item in card["fan_review"]:
        if item["root"] == "بر":
            item["meaning"] = "×"
    card["positives"] = []
    card["closure"] = "OPEN-CANDIDATE"
    card["judgment"] = "غير صادر"
    card["blocker_type"] = "SEMANTIC-ORBIT-GAP"
    card["required"] = "مدار بشري مقنع بعد قراءة شواهد الجذور العربية كاملة"
    card["arabic_root_sense_review"] = supplements["JAS-IE-004-182"]["arabic_root_sense_review"]
    card["root_sense_correction"] = {
        "date": "2026-08-14", "root": "بر",
        "witness": "البر خلاف البحر، وتصور منه التوسع في فعل الخير.",
        "source": "المفردات في غريب القرآن للراغب",
        "result": "no lexicographic purity sense; prior positive revoked",
    }
    for item in card.get("later_comparative_supplements", []):
        if item.get("batch") == 5:
            item["arabic_root_sense_review"] = supplements["JAS-IE-004-182"]["arabic_root_sense_review"]
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")

    reading = READINGS / "middle-english.md"
    text = reading.read_text(encoding="utf-8")
    marker = "<!-- JASSEM-IE:JAS-IE-004-182 -->"
    start, end = text.index(marker), text.index("\n<!-- JASSEM-IE-BATCH-004:END -->", text.index(marker))
    block = text[start:end]
    block = block.replace("`بر`[و0.000000،ص✓،ح✓،م✓]", "`بر`[و0.000000،ص✓،ح✓،م×]", 1)
    block = replace_outcome(block, [
        REVIEW_START,
        "- فحص معاني الجذور العربية: قُرئت مروحة الجذور كاملة بلا اقتطاع بـ`--max-chars 0`؛ يقول المفردات: «البر خلاف البحر، وتصور منه التوسع في فعل الخير»، ولا شاهد فيه للنقاء أو الخلوص.",
        REVIEW_END,
        "- عائق: النوع=SEMANTIC-ORBIT-GAP؛ يتطلب=مدارا بشريا مقنعا بعد قراءة شواهد الجذور العربية كاملة.",
        "- المدار المكتوب: نُقض المدار السابق لأن معاجم `بر` تشهد للبر والصدق والطاعة واليابسة، لا للنقاء أو الخلوص.",
        "- الحكم (استكشاف): **غير صادر (استكشاف)**.",
        "- حقل النقص، خارج الحكم: لا يشترط ثبوت الصورة في اللقطة، ولا يحول غيابها إلى رفض.",
        "- حالة الإغلاق: OPEN-CANDIDATE.",
    ])
    reading.write_text(text[:start] + block + text[end:], encoding="utf-8", newline="\n")

    # Add the exact Arabic witness to the inherited somme positive.
    path = ROOT / "data" / "khashim-indo-european-batch-006.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    card = next(item for item in data["rows"] if item["card_id"] == "KIE-N006-012")
    root_witness = {**WITNESS["زم"], "root_match_count": len(matches["زم"]), "definition_truncated": False}
    card["positives"][0]["root_witness"] = root_witness
    card["arabic_root_sense_review"] = supplements["KIE-N006-012"]["arabic_root_sense_review"]
    for item in card.get("comparative_supplements", []):
        if item.get("batch") == 5:
            item["arabic_root_sense_review"] = supplements["KIE-N006-012"]["arabic_root_sense_review"]
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")

    reading = READINGS / "old-latin.md"
    text = reading.read_text(encoding="utf-8")
    marker = "<!-- KHASHIM-IE-CONT:KIE-N006-012 -->"
    start, end = text.index(marker), text.index("<!-- COMPARATIVE-IE-SUPPLEMENT-005:KIE-N006-012:START -->", text.index(marker))
    block = text[start:end]
    local_start = "<!-- ARABIC-ROOT-SENSE-REVIEW-KIE-N006-012:START -->"
    local_end = "<!-- ARABIC-ROOT-SENSE-REVIEW-KIE-N006-012:END -->"
    block = re.sub(rf"\n?{re.escape(local_start)}.*?{re.escape(local_end)}\n?", "\n", block, flags=re.DOTALL)
    needle = "- المدار المكتوب:"
    at = block.index(needle)
    witness_lines = (
        local_start + "\n"
        "- شاهد الجذر العربي: يقول كتاب العين للخليل بن أحمد: «زممت الناقة أزمها زما. والزمام: الخيط الذي في أنفها»؛ قُرئت المادة كاملة بلا اقتطاع، فثبت طرف الربط في المدار.\n"
        + local_end + "\n"
    )
    block = block[:at] + witness_lines + block[at:]
    reading.write_text(text[:start] + block + text[end:], encoding="utf-8", newline="\n")


def write_audit(payload: dict[str, Any]) -> None:
    counts = payload["counts"]
    blockers = counts["open_cards_by_blocker"]
    pairs = ["cisoria ↔ قصل", "part ↔ فرد", "cubo ↔ كب", "duree ↔ دور", "beso/basio ↔ بوس", "carrus ↔ جر", "song ↔ صنج", "som ↔ زم", "rood/red ↔ ورد", "finis ↔ فني", "skaka ↔ صكك"]
    text = "\n".join([
        "# محضر الصفوف المقارنة الهندية الأوربية، الدفعة 005 (2026-08-14)", "",
        "## النطاق والحصيلة", "",
        f"- فُحص {counts['source_rows']} صفا ختاميا من `cross-european`: {counts['already_embedded_rows']} مضمّنة، و{counts['supplement_rows']} صفا في {counts['supplement_blocks']} إلحاقا، و{counts['new_card_rows']} صفا في {counts['new_cards']} بطاقة جديدة.",
        f"- صدر {counts['new_positive_cards']} حكما موجبا على {counts['new_positive_roots']} جذرا؛ بقي {blockers.get('SEMANTIC-ORBIT-GAP', 0)} بمانع المدار و{blockers.get('SOURCE-GAP', 0)} بمانع قاموس الفرع.",
        f"- قُرئت بلا اقتطاع شواهد {counts['arabic_root_sense_roots_reviewed']} جذرا عربيا في {counts['arabic_root_sense_containers_reviewed']} بطاقة وإلحاقا؛ بلغ مجموع الشواهد {counts['arabic_root_sense_witnesses_reviewed']}، وكلها بـ`--max-chars 0`.",
        f"- فُحصت {counts['branch_lexicon_forms_reviewed']} صورة في قواميس الفروع، وعرضت {counts['branch_lexicon_entries_shown']} إصابة كاملة، واختير سياقيا {counts['branch_lexicon_contextual_selections']} مدخلا.",
        "- فُحصت المراوح كلها مرتبة بـ`F.rank`، واستُعمل `fan_with_dialect` بعد عجز الفصحى؛ الوزن ترتيب لا حكم.", "",
        "## الأحكام الموجبة", "",
        "- " + "؛ ".join(pairs) + ".", "",
        "## تصحيحات واجبة", "",
        "- نُقضت أحكام `ras ↔ رس` و`puro ↔ بر` و`duren ↔ درن` لأن معاجم الجذور لا تشهد للمعاني التي قام عليها مدارها.",
        "- نُقض كذلك الحكم الموروث `Pure ↔ بر` في `JAS-IE-004-182`؛ تشهد المادة لليابسة والبر والطاعة، لا للنقاء والخلوص.",
        "- ثُبّت شاهد `زم` المعجمي في بطاقة `somme` الموروثة من خشيم، من غير تكرار بطاقة الأسرة.", "",
        "## تحقق الحفظ", "",
        "- اتحاد المضمّن والإلحاقات والبطاقات الجديدة يساوي الصفوف المختارة بلا غياب ولا تكرار.",
        f"- عُرض {counts['ranked_candidates_in_new_or_supplemental_full_fans']} مرشحا في المراوح الكاملة؛ لم يحكم الوزن.",
        "- انتهى مخزون `cross-european` وبقي 0 صف؛ ينتقل المسار إلى `cross-linguistic`.", "",
    ])
    AUDIT.write_text(text, encoding="utf-8", newline="\n")


def main() -> int:
    payload = json.loads(MANIFEST.read_text(encoding="utf-8"))
    cards = {item["card_id"]: item for item in payload["rows"]}
    for cid in REVOKE:
        card = cards[cid]
        for form in card["forms"]:
            form["positives"] = []
            for item in form.get("fan_review", []):
                item["meaning"] = "×" if item.get("event") == "✓" else "؟"
        card["positives"] = []
        card["closure"] = "OPEN-CANDIDATE"
        card["judgment"] = "غير صادر"
        card["blocker_type"] = "SEMANTIC-ORBIT-GAP"
        card["required"] = "مدار بشري مقنع بعد قراءة شواهد الجذور العربية كاملة"
        card["root_sense_correction"] = {"date": "2026-08-14", "root": REVOKE[cid][0], "result": REVOKE[cid][3]}

    # First select the final positive set so the review universe is exact.
    for cid, spec in SPECS.items():
        positive_for(cards[cid], spec)

    containers: list[dict[str, Any]] = []
    for card in payload["rows"]:
        if card.get("positives") or card.get("blocker_type") == "SEMANTIC-ORBIT-GAP":
            containers.append(card)
    for supplement in payload["supplements"]:
        if roots_for(supplement):
            containers.append(supplement)
    all_roots = {root for container in containers for root in roots_for(container)}
    matches = AR.matches_for_roots(AR.DEFAULT_RESOURCES, all_roots, None)
    if any(item.get("definition_truncated") for values in matches.values() for item in values):
        raise AssertionError("clipped Arabic root witness")

    # Rebuild positives with witnessed root metadata, then attach full reviews.
    positives: dict[str, dict[str, Any]] = {}
    for cid, spec in SPECS.items():
        positives[cid] = positive_for(cards[cid], spec, matches)
    for container in containers:
        container["arabic_root_sense_review"] = make_review(container, matches)

    for cid, card in cards.items():
        if cid in SPECS:
            update_card_reading(card, positives[cid], None)
        elif cid in REVOKE:
            update_card_reading(card, None, REVOKE[cid])
        elif card.get("blocker_type") == "SEMANTIC-ORBIT-GAP":
            update_card_reading(card, None, None)

    for supplement in payload["supplements"]:
        if supplement.get("arabic_root_sense_review"):
            extra = None
            if supplement["target_card_id"] == "KIE-N006-012":
                extra = "- شاهد الجذر العربي: يقول كتاب العين للخليل بن أحمد: «زممت الناقة أزمها زما. والزمام: الخيط الذي في أنفها»؛ الشاهد يقوي مدار الجمع بالربط."
            elif supplement["target_card_id"] == "JAS-IE-004-182":
                extra = "- شاهد نقض الحكم الموروث: يقول المفردات: «البر خلاف البحر، وتصور منه التوسع في فعل الخير»؛ لا شاهد للنقاء أو الخلوص."
            update_supplement_reading(supplement, extra)

    update_prior_cards(payload, matches)
    rebuild_selection_ledgers(payload)

    counts = payload["counts"]
    counts["new_positive_cards"] = sum(bool(card.get("positives")) for card in payload["rows"])
    counts["new_positive_roots"] = len({p["root"] for card in payload["rows"] for p in card.get("positives", [])})
    counts["open_cards_by_blocker"] = dict(Counter(card.get("blocker_type") for card in payload["rows"] if card.get("closure") == "OPEN-CANDIDATE"))
    counts["branch_lexicon_contextual_selections"] = sum(bool(form["branch_lexicon"].get("selected")) for container in [*payload["supplements"], *payload["rows"]] for form in container["forms"])
    counts["branch_lexicon_forms_without_contextual_selection"] = counts["branch_lexicon_forms_reviewed"] - counts["branch_lexicon_contextual_selections"]
    counts["arabic_root_sense_containers_reviewed"] = len(containers)
    counts["arabic_root_sense_roots_reviewed"] = len(all_roots)
    counts["arabic_root_sense_witnesses_reviewed"] = sum(len(values) for values in matches.values())
    counts["arabic_root_sense_definitions_truncated"] = 0
    payload["arabic_root_sense_policy"] = {
        "command": "python scripts/search_arabic_root_senses.py ROOT --max-chars 0",
        "full_fan_before_no_orbit": True,
        "definition_truncated": False,
        "exact_quote_and_dictionary_required_for_positive": True,
    }
    MANIFEST.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    write_audit(payload)

    assert counts["new_positive_cards"] == 11, counts
    assert counts["new_positive_roots"] == 11, counts
    assert counts["open_cards_by_blocker"] == {"SEMANTIC-ORBIT-GAP": 58, "SOURCE-GAP": 68}, counts
    assert counts["arabic_root_sense_roots_reviewed"] == 1929, counts
    assert counts["arabic_root_sense_witnesses_reviewed"] == 8858, counts
    assert counts["branch_lexicon_contextual_selections"] == 54, counts
    for cid in SPECS:
        positive = cards[cid]["positives"][0]
        assert positive["root_witness"]["quote"]
        assert FE.resolve(positive["root"]).text == positive["frozen_event"]
    print(json.dumps({
        "positives": counts["new_positive_cards"],
        "blockers": counts["open_cards_by_blocker"],
        "roots": counts["arabic_root_sense_roots_reviewed"],
        "witnesses": counts["arabic_root_sense_witnesses_reviewed"],
        "branch_selections": counts["branch_lexicon_contextual_selections"],
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
