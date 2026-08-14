# -*- coding: utf-8 -*-
"""تثبيت الاختيار السياقي لقاموس الفرع في الدفعة المقارنة 005."""
from __future__ import annotations

import json
import pathlib
import re
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
READINGS = ROOT / "04-cross-linguistic" / "readings"
AUDIT = ROOT / "05-audits" / "2026-08-14-comparative-indo-european-batch-005.md"
MANIFEST = DATA / "comparative-indo-european-batch-005.json"
START = "<!-- BRANCH-LEXICON-SELECTION-005:START -->"
END = "<!-- BRANCH-LEXICON-SELECTION-005:END -->"
LEDGER_START = "<!-- BRANCH-LEXICON-SELECTION-LEDGER-005:START -->"
LEDGER_END = "<!-- BRANCH-LEXICON-SELECTION-LEDGER-005:END -->"

# الرأس وقطعة معنى يعيّنان المدخل بعد موازنة القائمة بسياق المصدر. لا يؤخذ
# أول عنصر آليا، وكل صورة غير مذكورة هنا تبقى بلا اختيار صريح.
CONTEXTUAL_ENTRY: dict[str, tuple[str, str]] = {
    "avarie": ("avaria", "customs duty"),
    "averia": ("avaria", "customs duty"),
    "degree": ("degre", "degree or generation"),
    "somme": ("summa", "sum, summary, total"),
    "suma": ("summa", "sum, summary, total"),
    "soma": ("summa", "sum, summary, total"),
    "somma": ("summa", "sum, summary, total"),
    "summa": ("summa", "sum, summary, total"),
    "pur": ("pure", "pure, unadulterated"),
    "pure": ("pure", "pure, unadulterated"),
    "puro": ("puro", "to purify"),
    "cisoria": ("caesor", "cutter"),
    "doctor": ("doctour", "medical practitioner"),
    "musician": ("musicien", "musician"),
    "musiker": ("musiker", "musician"),
    "part": ("part", "part"),
    "porte": ("porto", "carry, bear"),
    "signum": ("signum", "sign, mark"),
    "captain": ("capitain", "head of a military force"),
    "aetas": ("aetas", "period of life"),
    "coraticum": ("coraticum", "courage, bravery"),
    "courage": ("corage", "courage"),
    "crimen": ("crimen", "crime, fault"),
    "cry": ("cry", "shout or yell"),
    "durata": ("duratio", "duration"),
    "duree": ("duro", "last or endure"),
    "gratitud": ("gratitudo", "gratitude"),
    "gratia": ("gratia", "thankfulness"),
    "carrus": ("carrus", "cartload"),
    "kn": ("ken", "recognition"),
    "kun": ("kunna", "know, understand"),
    "ras": ("rás", "race, running"),
    "rifiuto": ("refuto", "restrain, oppose"),
    "scale": ("scale", "ladder"),
    "scala": ("scala", "ladder"),
    "escala": ("scala", "ladder"),
    "odeur": ("odor", "smell, perfume"),
    "odore": ("odor", "smell, perfume"),
    "song": ("song", "song"),
    "sang": ("song", "song"),
    "cancion": ("concino", "sing, chant"),
    "som": ("sam-", "together, con-"),
    "richness": ("richenesse", "wealthiness"),
    "reich": ("riche", "rich, wealthy"),
    "antiquus": ("antiquus", "old, ancient"),
    "elegante": ("elegantia", "elegance"),
    "rood": ("red", "red, crimson"),
    "finis": ("finis", "end"),
    "duren": ("duren", "last, continue, endure"),
    "dauern": ("duren", "last, continue, endure"),
    "captia": ("capto", "seize, catch"),
    "skaka": ("skaka", "shake"),
}


def clean(value: Any) -> str:
    return " ".join(str(value or "").split())


def norm(value: Any) -> str:
    return clean(value).casefold()


def card_id(card: dict[str, Any]) -> str:
    for key in ("card_id", "merged_card_id", "continuation_card_id"):
        if card.get(key):
            return str(card[key])
    raise AssertionError("card id missing")


def sense_for(container: dict[str, Any], form: str) -> str:
    senses = [
        clean(claim.get("foreign_sense"))
        for claim in container.get("source_claims", [])
        if norm(claim.get("foreign")) == norm(form)
    ]
    return " | ".join(dict.fromkeys(senses))


def choose(form: str, entries: list[dict[str, Any]]) -> dict[str, Any] | None:
    spec = CONTEXTUAL_ENTRY.get(norm(form))
    if not spec:
        return None
    word, sense = spec
    matches = [
        entry for entry in entries
        if entry.get("word") == word and sense.casefold() in clean(entry.get("en")).casefold()
    ]
    if len(matches) != 1:
        raise AssertionError(f"contextual entry missing or ambiguous: {form}:{spec}:{len(matches)}")
    return matches[0]


def render_entry(entry: dict[str, Any]) -> str:
    read = f" /{clean(entry.get('read'))}/" if entry.get("read") else ""
    etym = f"؛ الاشتقاق «{clean(entry.get('etym'))}»" if entry.get("etym") else ""
    return (
        f"`{clean(entry.get('word'))}`{read} [{clean(entry.get('pos')) or '—'}] "
        f"«{clean(entry.get('en')) or '—'}»{etym}"
    )


def selection_lines(container: dict[str, Any]) -> list[str]:
    lines = [START]
    for form in container.get("forms", []):
        lex = form["branch_lexicon"]
        if lex["selected"]:
            lines.append(
                f"- اختيار قاموس الفرع لصورة `{clean(form['form'])}` ({lex['lookup_path']}): "
                f"{render_entry(lex['selected'])}. {lex['selection']}"
            )
        else:
            lines.append(
                f"- اختيار قاموس الفرع لصورة `{clean(form['form'])}` ({lex['lookup_path']}): "
                f"لا مدخل مختار. {lex['selection']}"
            )
    if container.get("closure") == "LOANWORD":
        loan = container["loanword"]
        lines.append(
            f"- حكم قاموس الفرع: **LOANWORD**؛ المانح المسمى {loan['donor']} "
            f"بالصورة `{loan['donor_form']}`؛ لا تعد البطاقة أو الإلحاق صلة."
        )
    lines.append(END)
    return lines


def replace_card_appendix(text: str, cid: str, lines: list[str]) -> str:
    marker = f"<!-- COMPARATIVE-IE:{cid} -->"
    at = text.find(marker)
    if at < 0:
        raise AssertionError(f"reading marker missing: {cid}")
    finish = text.find("\n### ", at)
    if finish < 0:
        finish = len(text)
    block = text[at:finish]
    block = re.sub(rf"\n?{re.escape(START)}.*?{re.escape(END)}\n?", "\n", block, flags=re.DOTALL)
    block = block.rstrip() + "\n" + "\n".join(lines) + "\n"
    return text[:at] + block + text[finish:]


def replace_supplement_appendix(text: str, cid: str, lines: list[str]) -> str:
    sm = f"<!-- COMPARATIVE-IE-SUPPLEMENT-005:{cid}:START -->"
    em = f"<!-- COMPARATIVE-IE-SUPPLEMENT-005:{cid}:END -->"
    left = text.find(sm)
    right = text.find(em, left + len(sm))
    if left < 0 or right < 0:
        raise AssertionError(f"supplement marker missing: {cid}")
    block = text[left:right]
    block = re.sub(rf"\n?{re.escape(START)}.*?{re.escape(END)}\n?", "\n", block, flags=re.DOTALL)
    block = block.rstrip() + "\n" + "\n".join(lines) + "\n"
    return text[:left] + block + text[right:]


def close_target_card(supplement: dict[str, Any], loan: dict[str, Any]) -> None:
    path = DATA / supplement["target_manifest"]
    payload = json.loads(path.read_text(encoding="utf-8"))
    target = next(card for card in payload.get("rows", []) if card_id(card) == supplement["target_card_id"])
    if target.get("positives"):
        raise AssertionError(f"cannot overwrite positive target with loan closure: {supplement['target_card_id']}")
    target["closure"] = "LOANWORD"
    target["judgment"] = "LOANWORD"
    target["loanword"] = loan
    target["blocker_type"] = None
    target["required"] = None
    target["branch_dictionary_recheck"] = {
        "date": "2026-08-14",
        "source_batch": 5,
        "dictionary_precedes_researcher_column": True,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def main() -> int:
    payload = json.loads(MANIFEST.read_text(encoding="utf-8"))
    selected = 0
    used: set[str] = set()
    loan_supplements = 0

    for container in [*payload["supplements"], *payload["rows"]]:
        loans: list[dict[str, Any]] = []
        for form in container["forms"]:
            lex = form["branch_lexicon"]
            sense = sense_for(container, form["form"])
            entry = choose(form["form"], lex["entries"])
            lex["query"] = form["form"]
            lex["selected"] = entry
            lex["researcher_sense"] = sense
            lex["dictionary_precedes_researcher"] = True
            if entry:
                used.add(norm(form["form"]))
                selected += 1
                lex["selection"] = (
                    f"اختير `{entry['word']}` بعد موازنة القائمة بسياق الصف «{sense}»؛ "
                    "لم تؤخذ الإصابة الأولى لمجرد ترتيبها، وقاموس الفرع مقدم على عمود الباحث."
                )
                if re.search(r"\bArabic\b", clean(entry.get("etym")), flags=re.IGNORECASE):
                    loans.append({"form": form["form"], "entry": entry})
            elif lex["entries"]:
                lex["selection"] = (
                    f"عُرضت جميع الإصابات، ولم يثبت منها مدخل يوافق سياق الصف «{sense}» "
                    "على وجه يحمل الحكم؛ بقي عمود الباحث ظاهرًا ولم يؤخذ بدل القاموس."
                )
            else:
                lex["selection"] = (
                    f"لم يرجع قاموس الفرع مدخلًا للصورة في سياق «{sense}»؛ "
                    "بقيت مفتوحة ولم يؤخذ عمود الباحث بدل القاموس."
                )

            if form.get("positives"):
                if not entry:
                    raise AssertionError(
                        f"positive lacks a context-selected dictionary entry: "
                        f"{container.get('card_id')}:{form['form']}"
                    )
                for positive in form["positives"]:
                    positive["branch_meaning"] = (
                        f"`{entry['word']}` [{entry.get('pos') or '—'}] في قاموس الفرع: "
                        f"«{entry.get('en') or '—'}»"
                    )
                    positive["branch_dictionary"] = lex["source"]
                    positive["branch_dictionary_path"] = lex["lookup_path"]
                    positive["branch_dictionary_entry"] = entry

        if container.get("card_id"):
            container["positives"] = [
                positive for form in container["forms"] for positive in form.get("positives", [])
            ]

        if loans:
            entry = loans[0]["entry"]
            loan = {
                "donor": "Arabic",
                "donor_form": "عَوَارِيَّة",
                "branch_entry": entry,
                "evidence": entry.get("etym"),
                "forms": [item["form"] for item in loans],
                "counted_link": False,
            }
            container["closure"] = "LOANWORD"
            container["judgment"] = "LOANWORD"
            container["loanword"] = loan
            container["blocker_type"] = None
            container["required"] = None
            if "target_card_id" in container:
                loan_supplements += 1
                close_target_card(container, loan)

    missing_specs = set(CONTEXTUAL_ENTRY) - used
    if missing_specs:
        raise AssertionError(f"unused contextual selections: {sorted(missing_specs)}")

    counts = payload["counts"]
    total_forms = len([form for container in [*payload["supplements"], *payload["rows"]] for form in container["forms"]])
    counts["branch_lexicon_contextual_selections"] = selected
    counts["branch_lexicon_forms_without_contextual_selection"] = total_forms - selected
    counts["loanword_supplements_closed_by_branch_dictionary"] = loan_supplements
    payload["merge_policy"]["branch_lexicon"] = (
        "all Kaikki hits and lookup paths are recorded; a context-selected entry is explicit, "
        "otherwise the card says that no hit matches; branch meaning overrides the researcher gloss"
    )
    MANIFEST.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")

    # A single indexed ledger per reading file avoids repeatedly copying a very
    # large Markdown string once for every card. The card-local full hit lists
    # are already present; this ledger supplies the explicit contextual choice.
    by_language: dict[str, list[dict[str, Any]]] = {}
    for container in payload["supplements"]:
        by_language.setdefault(container["target_language"], []).append(container)
    for container in payload["rows"]:
        by_language.setdefault(container["language"], []).append(container)
    for language, containers in by_language.items():
        path = READINGS / f"{language}.md"
        text = path.read_text(encoding="utf-8")
        text = re.sub(
            rf"\n?{re.escape(LEDGER_START)}.*?{re.escape(LEDGER_END)}\n?",
            "\n", text, flags=re.DOTALL,
        )
        ledger = [
            LEDGER_START,
            "### سجل اختيار قاموس الفرع، الدفعة المقارنة 005",
            "",
            "القوائم الكاملة في البطاقات أعلاه؛ وهذا السجل يعيّن المدخل المختار أو يصرح بعدم المطابقة، مع تقديم القاموس على عمود الباحث.",
            "",
        ]
        for container in containers:
            cid = container.get("card_id") or container.get("target_card_id")
            ledger.append(f"- البطاقة/الإلحاق `{cid}`:")
            ledger.extend(f"  {line}" for line in selection_lines(container)[1:-1])
        ledger.extend([LEDGER_END, ""])
        path.write_text(text.rstrip() + "\n\n" + "\n".join(ledger), encoding="utf-8", newline="\n")

    selection = payload["selection"]
    audit = "\n".join([
        "# محضر الصفوف المقارنة الهندية الأوربية، الدفعة 005 (2026-08-14)",
        "",
        "## النطاق والحصيلة",
        "",
        f"- عولجت الدفعة الخامسة الختامية: {counts['source_rows']} صفًا من `cross-european` بحسب ترتيب المصدر المجمد؛ بقي {selection['remaining_category_rows_after_batch']} صفًا.",
        f"- أُحيل {counts['already_embedded_rows']} صفوف مضمّنة بلا تكرار، وأُلحق {counts['supplement_rows']} صفًا في {counts['supplement_blocks']} بطاقة قائمة، وصنع {counts['new_card_rows']} صفًا {counts['new_cards']} بطاقة جديدة.",
        f"- صدر {counts['new_positive_cards']} موجبًا على {counts['new_positive_roots']} مقابل؛ بقيت البطاقات الجديدة بلا موجب لأن معنى القاموس لم يكمل مدارًا مستوفيًا.",
        f"- فُحصت {counts['branch_lexicon_forms_reviewed']} صورة بقاموس فرعها، وعُرضت {counts['branch_lexicon_entries_shown']} إصابة؛ اختير سياقيًا {selected} مدخلًا، وبقيت {total_forms - selected} صورة بلا اختيار سياقي.",
        f"- طرق البحث: {json.dumps(counts['branch_lexicon_lookup_paths'], ensure_ascii=False)}.",
        "- قاموس الفرع مقدم على عمود الباحث عند الخلاف؛ حُفظ العمود والخلاف ولم يمحيا.",
        "",
        "## القرض المحروس",
        "",
        f"- أُغلق {loan_supplements} إلحاق `LOANWORD`: `avarie/averia`، إذ نص اشتقاق `avaria` على العربية `عَوَارِيَّة` من `عَوَار`؛ المانح مسمى ولا تعد صلة.",
        "- كل مدخل مختار محفوظ برسمه وقسمه ومعناه واشتقاقه، ومعه وسم طريق البحث؛ وكل قائمة إصابات مطبوعة كاملة في البطاقة.",
        "",
        "## تحقق الحفظ",
        "",
        "- البيان: `data/comparative-indo-european-batch-005.json`.",
        f"- اتحاد الإحالات والإلحاقات والبطاقات الجديدة يساوي الصفوف {counts['source_rows']} المختارة بلا غياب ولا تكرار.",
        f"- فُحص {counts['ranked_candidates_in_new_or_supplemental_full_fans']} مرشحًا في المراوح، ولم يحكم الوزن.",
        "- انتهى مخزون الفئة: المتبقي 0، فتقف الحملة هنا ولا تولد دفعة فارغة.",
        "",
    ])
    AUDIT.write_text(audit, encoding="utf-8", newline="\n")
    print(
        f"CLEAN: forms={total_forms}, selected={selected}, open={total_forms-selected}, "
        f"loanword_supplements={loan_supplements}, remaining={selection['remaining_category_rows_after_batch']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
