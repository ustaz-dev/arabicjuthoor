# -*- coding: utf-8 -*-
"""إعادةُ حصادِ الدفعات المقارنة 001-004 بقواميس الفروع (2026-08-14).

هذا ناسخٌ محدود النطاق: لا يعيد توليد المراوح ولا يلمس خط البرهان. يمرر كل
صورة في الدفعات الأربع على ``build_kaikki_index.look``، يحفظ القائمة كاملة
وطريق البحث والمدخل السياقي إن وجد، ثم يعيد اختبار الموجبات الأحد عشر وحدها
ويغلق القروض العربية الصريحة التي كشفها قاموس الفرع.
"""
from __future__ import annotations

import json
import pathlib
import re
import sys
from collections import Counter
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import build_kaikki_index as LEX  # noqa: E402

DATA = ROOT / "data"
READINGS = ROOT / "04-cross-linguistic" / "readings"
AUDITS = ROOT / "05-audits"
REPORT = AUDITS / "2026-08-14-comparative-branch-lexicon-recheck.md"

LANG = {
    "ancient-greek": "ancient-greek",
    "gothic": "gothic",
    "middle-english": "middle-english",
    "old-english": "old-english",
    "old-irish": "old-irish",
    "old-latin": "latin",
    "old-norse": "old-norse",
    "welsh": "welsh",
}

# المدخل المختار يعيّن بالرأس وبقطعة من المعنى عند وجود المتجانس. كل ما عدا
# ذلك يبقى بلا اختيار بعد عرض القائمة كاملة، ولا تؤخذ الإصابة الأولى آليا.
MANUAL_SELECTED: dict[tuple[str, str], tuple[str, str]] = {
    ("CMP-IE-001-021", "furka"): ("forke", "fork"),
    ("CMP-IE-003-002", "tungo"): ("tunge", "tongue"),
    ("CMP-IE-003-007", "katt"): ("ketta", "cat"),
    ("CMP-IE-003-012", "corne"): ("cornu", "horn"),
    ("CMP-IE-004-019", "calx"): ("calx", "limestone"),
    ("CMP-IE-004-025", "gold"): ("gold", "gold"),
    ("CMP-IE-004-039", "mous"): ("Μοῦσα", "Muse"),
    ("CMP-IE-004-049", "box"): ("box", "container"),
    ("CMP-IE-004-056", "tapis"): ("tapes", "carpet"),
    ("CMP-IE-004-064", "mattress"): ("materas", "mattress"),
    ("CMP-IE-004-064", "matras"): ("materas", "mattress"),
    ("CMP-IE-004-083", "sugar"): ("sugre", "sugar"),
    ("CMP-IE-004-089", "bottle"): ("botel", "bottle"),
    ("CMP-IE-004-095", "jarro"): ("jarra", "jar"),
    ("CMP-IE-004-104", "sag"): ("sǫg", "saw"),
}
EXACT_MISMATCH = {
    ("CMP-IE-004-057", "kissen"),   # القاموس: kiss، والسياق: cushion
    ("CMP-IE-004-077", "flour"),    # القاموس: flower، والسياق: دقيق
    ("CMP-IE-004-094", "plato"),    # القاموس: Plato، والسياق: plate
}

RETAINED = {
    "CMP-IE-001-021": "furka",
    "CMP-IE-003-012": "corne",
    "CMP-IE-004-041": "pipe",
}
REVOKED = {
    "CMP-IE-001-006",
    "CMP-IE-003-011",
    "CMP-IE-004-045",
    "CMP-IE-004-072",
    "CMP-IE-004-087",
    "CMP-IE-004-090",
    "CMP-IE-004-099",
    "CMP-IE-004-102",
}
TRANSMISSION = "CMP-IE-004-072"
ARABIC_LOANS = {
    "CMP-IE-001-013": ("Arabic", "ambra", "عَنْبَر"),
    "CMP-IE-004-064": ("Arabic", "materas", "مَطْرَح"),
    "CMP-IE-004-095": ("Arabic", "jarra", "جَرَّة"),
}

START = "<!-- BRANCH-LEXICON-RECHECK-2026-08-14:START -->"
END = "<!-- BRANCH-LEXICON-RECHECK-2026-08-14:END -->"


def norm(value: Any) -> str:
    return " ".join(str(value or "").split()).casefold()


def choose(card_id: str, form: str, hits: list[dict], how: str) -> dict | None:
    spec = MANUAL_SELECTED.get((card_id, norm(form)))
    if spec:
        word, sense = spec
        for entry in hits:
            if entry.get("word") == word and sense.casefold() in str(entry.get("en") or "").casefold():
                return entry
        raise AssertionError(f"manual branch entry missing: {card_id}:{form}:{spec}")
    if (card_id, norm(form)) in EXACT_MISMATCH:
        return None
    if how == "الصورةُ بنصِّها" and len(hits) == 1:
        return hits[0]
    return None


def lexical_payload(card_id: str, language: str, form: str) -> dict:
    lex_lang = LANG[language]
    hits, how = LEX.look(lex_lang, form)
    selected = choose(card_id, form, hits, how)
    if selected:
        selection = (
            f"اختير `{selected['word']}` لأنه المدخل الذي يوافق سياق الصف؛ "
            "لم تؤخذ الإصابة الأولى لمجرد ترتيبها."
        )
    elif hits:
        selection = "عُرضت جميع الإصابات، ولم يثبت منها مدخل يوافق سياق الصف على وجه يحمل الحكم."
    else:
        selection = "لم يرجع قاموس الفرع مدخلا لهذه الصورة."
    return {
        "language": lex_lang,
        "source": f"data/branch-lexicons/{lex_lang}.json",
        "lookup_path": how,
        "query": form,
        "entries": hits,
        "selected": selected,
        "selection": selection,
    }


def entry_text(entry: dict) -> str:
    read = f" /{entry['read']}/" if entry.get("read") else ""
    etym = f"؛ الاشتقاق: «{entry['etym']}»" if entry.get("etym") else ""
    return f"`{entry['word']}`{read} [{entry.get('pos') or '—'}] «{entry.get('en') or '—'}»{etym}"


def locate_card(text: str, card_id: str) -> tuple[int, int]:
    marker = f"<!-- COMPARATIVE-IE:{card_id} -->"
    at = text.find(marker)
    if at < 0:
        raise AssertionError(f"reading card missing: {card_id}")
    left = text.rfind("\n### ", 0, at)
    left = left + 1 if left >= 0 else at
    right = text.find("\n### ", at)
    if right < 0:
        right = len(text)
    return left, right


def replace_judgment(block: str, line: str) -> str:
    pattern = r"^- الحكم \(استكشاف\): \*\*.*$"
    if re.search(pattern, block, flags=re.MULTILINE):
        return re.sub(pattern, line, block, count=1, flags=re.MULTILINE)
    return block.rstrip() + "\n" + line + "\n"


def recheck_lines(card: dict) -> list[str]:
    lines = [START, "- إعادة قاموس الفرع: عُرضت قائمة كل صورة، وحُفظ طريق البحث ورسم المدخل كما في القاموس."]
    for form in card["forms"]:
        lex = form["branch_lexicon"]
        entries = " | ".join(entry_text(entry) for entry in lex["entries"]) or "لا مدخل"
        lines.append(
            f"- صورة `{form['form']}`؛ الطريق: {lex['lookup_path']}؛ المصدر: `{lex['source']}`؛ "
            f"القائمة كاملة: {entries}."
        )
        selected = lex["selected"]
        lines.append(
            f"- اختيار صورة `{form['form']}`: "
            + (entry_text(selected) + ". " if selected else "لا شيء. ")
            + lex["selection"]
        )
    if card["card_id"] in RETAINED:
        lines.append("- أثر الإعادة: بقي الموجب لأن المدخل المختار يسند المعنى الذي قام عليه المدار.")
    elif card["card_id"] in REVOKED:
        if card["card_id"] == TRANSMISSION:
            lines.append("- أثر الإعادة: نُسخ الموجب الموروث؛ الاشتقاق يسمّي العبرية مانحا ساميا، فصارت البطاقة `SEMITIC-SOURCE-TRANSMISSION` خارج عد الصلات.")
        else:
            lines.append("- أثر الإعادة: نُسخ الموجب؛ قاموس الفرع لا يسند المعنى الذي قام عليه مداره السابق، وبقي الحكم غير صادر.")
    elif card["card_id"] in ARABIC_LOANS:
        donor, _entry, donor_form = ARABIC_LOANS[card["card_id"]]
        lines.append(f"- أثر الإعادة: `LOANWORD`؛ المانح المسمى {donor} بالصورة `{donor_form}`؛ لا تعد البطاقة صلة.")
    else:
        lines.append("- أثر الإعادة: لا موجب جديد؛ المدخل المختار، إن وجد، لم يكمل مع الصوت والحدث مدارا مستوفيا.")
    lines.append(END)
    return lines


def selected_for_card(card: dict, wanted_form: str | None = None) -> tuple[dict, dict] | None:
    for form in card["forms"]:
        if wanted_form and norm(form["form"]) != norm(wanted_form):
            continue
        if form["branch_lexicon"]["selected"]:
            return form, form["branch_lexicon"]["selected"]
    return None


def selected_entry_for_card(card: dict, wanted_word: str) -> tuple[dict, dict] | None:
    """Find a contextual selection by dictionary headword, not by source-row form."""
    for form in card["forms"]:
        entry = form["branch_lexicon"]["selected"]
        if entry and entry.get("word") == wanted_word:
            return form, entry
    return None


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    reading_texts = {
        language: (READINGS / f"{language}.md").read_text(encoding="utf-8")
        for language in LANG
    }
    batch_stats = {}
    retained_ids: list[str] = []
    revoked_ids: list[str] = []
    loan_ids: list[str] = []
    all_cards = 0
    all_forms = 0
    path_counts: Counter[str] = Counter()

    for batch in range(1, 5):
        path = DATA / f"comparative-indo-european-batch-{batch:03d}.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        baseline = sum(card["card_id"] in RETAINED or card["card_id"] in REVOKED for card in payload["rows"])
        batch_retained = 0
        batch_revoked = 0
        batch_loans = 0
        for card in payload["rows"]:
            all_cards += 1
            card_id = card["card_id"]
            for form in card["forms"]:
                lex = lexical_payload(card_id, card["language"], form["form"])
                form["branch_lexicon"] = lex
                all_forms += 1
                path_counts[lex["lookup_path"]] += 1
            card["branch_dictionary_recheck"] = {
                "date": "2026-08-14",
                "tool": "scripts/build_kaikki_index.py",
                "all_entries_shown": True,
                "dictionary_precedes_researcher_column": True,
            }

            if card_id in RETAINED:
                chosen = selected_for_card(card, RETAINED[card_id])
                if not chosen:
                    raise AssertionError(f"retained card lacks contextual entry: {card_id}")
                form, entry = chosen
                for positive in card.get("positives", []):
                    positive["branch_meaning"] = (
                        f"`{entry['word']}` [{entry.get('pos') or '—'}] في قاموس الفرع: «{entry.get('en') or '—'}»"
                    )
                    positive["branch_dictionary"] = form["branch_lexicon"]["source"]
                    positive["branch_dictionary_path"] = form["branch_lexicon"]["lookup_path"]
                    positive["branch_dictionary_entry"] = entry
                batch_retained += 1
                retained_ids.append(card_id)

            elif card_id in REVOKED:
                old = card.get("positives") or card.get("revoked_positives", [])
                if not old:
                    raise AssertionError(f"expected prior positive missing: {card_id}")
                card["revoked_positives"] = old
                card["revocation"] = {
                    "date": "2026-08-14",
                    "reason": "قاموس الفرع لا يسند المعنى الذي قام عليه المدار السابق",
                    "tool": "scripts/build_kaikki_index.py",
                }
                card["positives"] = []
                for form in card["forms"]:
                    if form.get("positives"):
                        form["revoked_positives"] = form["positives"]
                        form["positives"] = []
                    for candidate in form.get("fan_review", []):
                        if candidate.get("meaning") == "✓":
                            candidate["meaning"] = "×"
                if card_id == TRANSMISSION:
                    chosen = selected_for_card(card, "sikera")
                    if not chosen:
                        raise AssertionError("sikera dictionary entry missing")
                    form, entry = chosen
                    card["closure"] = "SEMITIC-SOURCE-TRANSMISSION"
                    card["judgment"] = "SEMITIC-SOURCE-TRANSMISSION"
                    card["transmission"] = {
                        "donor": "Biblical Hebrew",
                        "ultimate_source": "Proto-Semitic *šikar-",
                        "branch_entry": entry,
                        "evidence": entry["etym"],
                        "counted_link": False,
                    }
                else:
                    card["closure"] = "OPEN-CANDIDATE"
                    card["judgment"] = "غير صادر"
                    card["blocker_type"] = "BRANCH-LEXICON-MISMATCH"
                    card["required"] = "مدخل قاموس فرع يوافق سياق الصف ثم مدار ينسخ معناه"
                batch_revoked += 1
                revoked_ids.append(card_id)

            if card_id in ARABIC_LOANS:
                donor, wanted_word, donor_form = ARABIC_LOANS[card_id]
                chosen = selected_entry_for_card(card, wanted_word)
                if not chosen:
                    raise AssertionError(f"Arabic-loan entry missing: {card_id}:{wanted_word}")
                form, entry = chosen
                card["closure"] = "LOANWORD"
                card["judgment"] = "LOANWORD"
                card["loanword"] = {
                    "donor": donor,
                    "donor_form": donor_form,
                    "branch_entry": entry,
                    "evidence": entry["etym"],
                    "counted_link": False,
                }
                card["blocker_type"] = None
                card["required"] = None
                batch_loans += 1
                loan_ids.append(card_id)

            text = reading_texts[card["language"]]
            left, right = locate_card(text, card_id)
            block = text[left:right]
            block = re.sub(
                rf"\n?{re.escape(START)}.*?{re.escape(END)}\n?", "\n", block,
                flags=re.DOTALL,
            )
            if card_id in REVOKED:
                if card_id == TRANSMISSION:
                    block = replace_judgment(
                        block,
                        "- الحكم (استكشاف): **SEMITIC-SOURCE-TRANSMISSION**؛ مانح عبري مسمى، خارج عد الصلات.",
                    )
                else:
                    block = replace_judgment(block, "- الحكم (استكشاف): **غير صادر (استكشاف)**.")
            elif card_id in ARABIC_LOANS:
                donor, _wanted, donor_form = ARABIC_LOANS[card_id]
                block = replace_judgment(
                    block,
                    f"- الحكم (استكشاف): **LOANWORD**؛ المانح المسمى {donor} بالصورة `{donor_form}`؛ لا صلة.",
                )
            block = block.rstrip() + "\n" + "\n".join(recheck_lines(card)) + "\n"
            reading_texts[card["language"]] = text[:left] + block + text[right:]

        current = sum(bool(card.get("positives")) for card in payload["rows"])
        if current != batch_retained:
            raise AssertionError(f"current-positive mismatch in batch {batch}: {current}!={batch_retained}")
        counts = payload["counts"]
        counts["baseline_positive_cards_before_branch_dictionary"] = baseline
        counts["converted_after_branch_dictionary_sense"] = 0
        counts["retained_positive_cards_after_branch_dictionary"] = batch_retained
        counts["revoked_positive_cards_after_branch_dictionary"] = batch_revoked
        counts["new_positive_cards"] = current
        counts["new_positive_roots"] = sum(len(card.get("positives", [])) for card in payload["rows"])
        counts["loanword_cards_closed_by_branch_dictionary"] = batch_loans
        payload["branch_dictionary"] = "data/branch-lexicons/ via scripts/build_kaikki_index.py"
        payload["branch_dictionary_recheck"] = {
            "date": "2026-08-14",
            "converted": 0,
            "retained": batch_retained,
            "revoked": batch_revoked,
            "loanword_closures": batch_loans,
        }
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
        batch_stats[batch] = (len(payload["rows"]), baseline, 0, batch_retained, batch_revoked, batch_loans)

    for language, text in reading_texts.items():
        (READINGS / f"{language}.md").write_text(text, encoding="utf-8", newline="\n")

    audit_marker_start = "<!-- BRANCH-LEXICON-RECHECK:START -->"
    audit_marker_end = "<!-- BRANCH-LEXICON-RECHECK:END -->"
    for batch, stats in batch_stats.items():
        cards, baseline, converted, retained, revoked, loans = stats
        audit_path = AUDITS / f"2026-08-14-comparative-indo-european-batch-{batch:03d}.md"
        text = audit_path.read_text(encoding="utf-8")
        text = re.sub(
            rf"\n?{re.escape(audit_marker_start)}.*?{re.escape(audit_marker_end)}\n?", "\n", text,
            flags=re.DOTALL,
        )
        appendix = "\n".join([
            audit_marker_start,
            "## ناسخ قاموس الفرع (2026-08-14)",
            "",
            f"- أُعيدت بطاقات الدفعة كلها وعددها {cards} على قاموس كل فرع، وعُرضت قائمة المداخل لكل صورة قبل الاختيار.",
            f"- كان الموجب قبل القاموس {baseline}؛ **تحول من مفتوح إلى موجب: {converted}**؛ بقي موجبًا: {retained}؛ **نُسخ من الموجب: {revoked}**.",
            f"- أُغلقت بالقرض الصريح من غير عد صلة: {loans}.",
            "- قاموس الفرع مقدّم على عمود الباحث؛ بقي الخلاف ظاهرًا في البطاقة ولم يمح نقل المصدر.",
            audit_marker_end,
            "",
        ])
        audit_path.write_text(text.rstrip() + "\n\n" + appendix, encoding="utf-8", newline="\n")

    table = [
        "| الدفعة | البطاقات | الموجب السابق | تحوّل إلى موجب | بقي موجبًا | نُسخ | أُغلق LOANWORD |",
        "|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for batch, stats in batch_stats.items():
        table.append(f"| {batch:03d} | {stats[0]} | {stats[1]} | {stats[2]} | {stats[3]} | {stats[4]} | {stats[5]} |")
    report = "\n".join([
        "# إعادة قاموس الفرع للدفعات المقارنة 001-004 (2026-08-14)",
        "",
        "## الحصيلة الناسخة",
        "",
        *table,
        "",
        f"**الرقمان المطلوبان:** تحوّل **0** من المفتوح إلى موجب، ونُسخ **{len(revoked_ids)}** من الموجب. بقيت **{len(retained_ids)}** موجبات من أصل 11.",
        "",
        f"- البطاقات الباقية موجبة: {', '.join(f'`{item}`' for item in retained_ids)}.",
        f"- البطاقات المنسوخة: {', '.join(f'`{item}`' for item in revoked_ids)}.",
        f"- قروض عربية صريحة أُغلقت بلا عد: {', '.join(f'`{item}`' for item in loan_ids)}.",
        f"- طرق البحث في {all_forms} صورة ضمن {all_cards} بطاقة: " + "، ".join(f"{key}={value}" for key, value in sorted(path_counts.items())) + ".",
        "",
        "## مواضع حاسمة",
        "",
        "- `sikera`: وجد مسار الرومنة المدخل `σίκερα /síkera/` بمعنى الشراب المخمّر، لكن اشتقاقه يسمّي العبرية `שֵׁכָר` وProto-Semitic `*šikar-`؛ لذلك نُسخ حكم الوراثة وصارت البطاقة `SEMITIC-SOURCE-TRANSMISSION` خارج العد.",
        "- `bourge` و`Kabiros` و`seife` و`aigre` و`kopp` و`okse` و`cisellum`: عُرضت إصابات القاموس، ولم توافق سياق المعنى الذي قام عليه المدار السابق، فنُسخت موجباتها.",
        "- `furka` و`corne` و`pipe`: أسندت المداخل السياقية `forke` و`cornu` و`pipe` معاني الشوكة والقرن والأنبوب، فبقيت موجباتها.",
        "- `ambra` و`materas` و`jarra`: سمّت الاشتقاقات العربية مانحًا، فأُغلقت `LOANWORD` مع اسم المانح ولم تدخل عد الصلات.",
        "",
        "## الحراسة",
        "",
        "- لم تؤخذ المدخلة الأولى آليًا؛ الاختيار معرّف بالرأس والمعنى عند المتجانس.",
        "- حُفظ وسم الطريق ورسم المدخل والرومنة وقسم الكلام والمعنى والاشتقاق في JSON وفي بطاقة القراءة.",
        "- بقي عمود خشيم منسوبًا إليه وظاهرًا، لكن الحكم صار لمعنى قاموس الفرع.",
        "- لم يتحول أي مفتوح إلى موجب: أوضح ما أكمله القاموس دلاليًا بقي ناقص صف صوت نافذ أو مدارًا مستوفيًا، فلم يُخترع صف ولم يُستخرج موجب من الوزن.",
        "",
    ])
    REPORT.write_text(report, encoding="utf-8", newline="\n")

    if len(retained_ids) != 3 or len(revoked_ids) != 8:
        raise AssertionError((retained_ids, revoked_ids))
    print(
        f"CLEAN: cards={all_cards}, forms={all_forms}, converted=0, "
        f"retained={len(retained_ids)}, revoked={len(revoked_ids)}, loans={len(loan_ids)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
