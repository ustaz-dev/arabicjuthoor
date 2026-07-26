#!/usr/bin/env python3
"""Apply the old-Arabic fan campaign to the live Hebrew TOOL-GAP cards.

The first 300 Hebrew ranks already carry a later, deterministic fate table.
This pass makes that measured fate authoritative in the older cards, closes
superseded cards by reference, and issues only explicitly named new links
whose branch evidence and two-source Arabic fan are both present.
"""
from __future__ import annotations

import argparse
import json
import re
import sqlite3
import tempfile
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

from search_arabic_root_senses import (
    ARABIC_MARKS,
    DEFAULT_RESOURCES,
    independent_fan,
    matches_for_roots,
)


ROOT = Path(__file__).resolve().parents[1]
READING = ROOT / "04-cross-linguistic" / "readings" / "hebrew.md"
DB = ROOT / "cache" / "recovery_pipeline" / "inventory-v5.sqlite"
DATE = "2026-07-25"
SECTION = re.compile(r"(?=^### )", re.MULTILINE)
CARD = re.compile(
    r"^### بطاقة: `(?P<family>hebrew:family:[0-9a-f]+)`، "
    r"(?P<title>[^\n]+)$",
    re.MULTILINE,
)
RANK = re.compile(r"\(الرتبة (?P<rank>\d+)\)$")
BLOCKER = re.compile(r"^-\s*عائق:\s*.+$", re.MULTILINE)
SCAN = re.compile(r"^-\s*مسحُ?\s*المعاني العربيّة:\s*.+$", re.MULTILINE)
CLOSURE = re.compile(r"^-\s*حالةُ الإغلاق:\s*.+$", re.MULTILINE)
VERDICT = re.compile(r"^-\s*الحكم \(استكشاف\):\s*.+$", re.MULTILINE)
FATE = re.compile(
    r"^\|\s*(?P<rank>\d+)\s*\|\s*`(?P<family>hebrew:family:[0-9a-f]+)`"
    r"\s*\|\s*(?P<head>[^|]+?)\s*\|\s*(?P<fan>[^|]+?)\s*\|\s*"
    r"`(?P<state>[A-Z\-]+)`\s*\|\s*(?P<required>[^|]+?)\s*\|$",
    re.MULTILINE,
)
POSITIVE_PREFIXES = ("ROOT-", "NUCLEUS-")


# family: Arabic root, verdict, terms that must occur in each of the two old
# Arabic witnesses, and the exact member or sense-chain receiving the verdict.
POSITIVE_SPECS: dict[str, tuple[str, str, tuple[str, ...], str]] = {
    "hebrew:family:154ac833de0df35a19da37a0": (
        "بعل",
        "ROOT-TRACE",
        ("بعل", "زوج", "رب"),
        "בעל «السيد والمالك» وسلسلة الملك أو الزوج وحدها",
    ),
    "hebrew:family:544164c80fbe1e8a27ab6b8b": (
        "خدر",
        "ROOT-TRACE",
        ("خدر", "ستر"),
        "חדר «الغرفة» وحدها، مع عزل المركبات الحديثة",
    ),
    "hebrew:family:91fa9ff6c7f87841480bfaca": (
        "جور",
        "ROOT-TRACE",
        ("جار", "جوار"),
        "جذر ג־ו־ר في الإقامة والجوار وحده، لا الخوف ولا الهجوم",
    ),
    "hebrew:family:66110ee4e5c5fef39a9a7ee1": (
        "زمر",
        "ROOT-ECHO",
        ("زمر", "مزمار"),
        "זמר في الغناء والإنشاد وحده، لا التقليم ولا الحيوان المتجانس",
    ),
    "hebrew:family:418c554acefd01ac179cd416": (
        "جبل",
        "ROOT-TRACE",
        ("جبل", "خلق", "طبع"),
        "جذر ג־ב־ל في العجن والتشكيل وحده، لا العلم ولا حد البلد",
    ),
    "hebrew:family:4a4f9a48481390cf3362cbaa": (
        "فطر",
        "ROOT-ECHO",
        ("فطر", "شق"),
        "פטר «البكر الذي يفتح الرحم» وحده، لا اسم Peter ولا فعل الحل",
    ),
    "hebrew:family:403454f7dc32d5923bb3f9bf": (
        "خمر",
        "ROOT-TRACE",
        ("خمر", "سكر"),
        "חמר «الخمر والنبيذ المختمر» وحده، لا الحمرة ولا قائد الحمير",
    ),
    "hebrew:family:12a544b084369e46bab6bfc0": (
        "فرد",
        "ROOT-TRACE",
        ("فرد", "واحد"),
        "جذر פ־ר־ד في الانفصال والتفرد وحده، لا أسماء البغل والرمان",
    ),
    "hebrew:family:4f3c9b56871e5f843c402d15": (
        "عصب",
        "ROOT-TRACE",
        ("عصب", "وتر"),
        "עצב «العصب» العضوي وحده، لا الحزن والغضب والتمثال",
    ),
    "hebrew:family:884b411b07e01273a03a7e33": (
        "قرب",
        "ROOT-ECHO",
        ("قرب", "دنا"),
        "קרב «القتال والاشتباك القريب» وحده، على مدار الاقتراب",
    ),
    "hebrew:family:6ddec1a4134cc94383505005": (
        "هرس",
        "ROOT-ECHO",
        ("هرس", "دق", "كسر"),
        "הרס «الهدم والتدمير» وحده، على مدار الدق والكسر",
    ),
    "hebrew:family:cacf136016c7bac479318ab8": (
        "نعم",
        "ROOT-TRACE",
        ("نعم", "نعيم"),
        "נעם في اللطف والسرور والاستحسان وحده، لا النغم ولا النعام",
    ),
    "hebrew:family:6af251d3e1e9ccace85faaaa": (
        "كمم",
        "NUCLEUS-TRACE",
        ("كم", "عدد"),
        "כמה الاستفهامية «كم، كم عددًا» وحدها، لا فعل الشوق",
    ),
    "hebrew:family:22a3ee5d71fa234e9be5d141": (
        "طيب",
        "ROOT-TRACE",
        ("طيب", "خير"),
        "טוב في الخير والجودة وحده",
    ),
    "hebrew:family:3a032f9849cfe7ac4a1a7742": (
        "حمد",
        "ROOT-ECHO",
        ("حمد", "مدح", "ثناء"),
        "חמד في الاستحسان والسرور بالشيء وحده، لا التملك المجرد",
    ),
    "hebrew:family:417fa5bc40ec833e32a34ff5": (
        "بدل",
        "ROOT-ECHO",
        ("بدل", "غير", "خلف"),
        "בדל في الفصل والتمييز وحده، على مدار تغيير الحال والانفصال",
    ),
    "hebrew:family:39579889d2003170a4455346": (
        "بطل",
        "ROOT-TRACE",
        ("بطل", "باطل"),
        "בטל في البطلان والتوقف عن الوجود وحده",
    ),
    "hebrew:family:48387d41ff5f98aaad40fef2": (
        "قصر",
        "ROOT-TRACE",
        ("قصر", "قصير"),
        "קצר في القصر وقلة الطول وحده، لا الحصاد",
    ),
    "hebrew:family:1714fbd861b426804961364e": (
        "لقق",
        "ROOT-TRACE",
        ("لق", "لحس"),
        "לקק «لحس ولعق» وحده، لا المشتق الحديث الدال على محب الحلوى",
    ),
    "hebrew:family:f3ca6f8c1372bae8a0bdc796": (
        "فلق",
        "ROOT-ECHO",
        ("فلق", "شق"),
        "פלג «الجدول والمجرى» وحده، على مدار الشق الذي يجري فيه الماء",
    ),
    "hebrew:family:ff43e43ed8e14d0f006bdfe1": (
        "لوح",
        "ROOT-TRACE",
        ("لوح", "لوح"),
        "לוח «اللوح واللوحة» وحده",
    ),
    "hebrew:family:717530f000ef53aea404734f": (
        "صبغ",
        "ROOT-TRACE",
        ("صبغ", "لون"),
        "צבע في الصبغ والتلوين وحده",
    ),
    "hebrew:family:3d1a812269dcc11383f991f3": (
        "رغب",
        "ROOT-ECHO",
        ("رغب", "طلب"),
        "רעב في اشتهاء الطعام والجوع وحده، على مدار الرغبة",
    ),
    "hebrew:family:7325ecf50f4156f8e485c0cd": (
        "مزج",
        "ROOT-TRACE",
        ("مزج", "خلط"),
        "מזג في المزج وصب الخليط والمزاج وحده",
    ),
    "hebrew:family:a7bb9ab022e5d41bf4cad731": (
        "نسر",
        "ROOT-TRACE",
        ("نسر", "طائر"),
        "נשר «النسر» الطائر وحده، لا سقوط الثمر",
    ),
    "hebrew:family:9b66a00d23300e96da1a993b": (
        "خلل",
        "ROOT-ECHO",
        ("خلل", "خلال", "فرج"),
        "חלל «الفضاء والفراغ» وحده، على مدار الخلال والفرجة",
    ),
    "hebrew:family:44c516f5b29b885c154e5452": (
        "نظر",
        "ROOT-TRACE",
        ("نظر", "بصر"),
        "נצר «حرس وحفظ» وحده، على مدار المراقبة والنظر",
    ),
    "hebrew:family:e5260bd967ab2fce3402d223": (
        "بقر",
        "ROOT-TRACE",
        ("بقر", "بقرة"),
        "בקר «البقر» الحيوان وحده، لا المفتش ولا المصطلح الموسيقي",
    ),
    "hebrew:family:8d3ceb8a480116026dcb54fa": (
        "خسر",
        "ROOT-ECHO",
        ("خسر", "نقص"),
        "חסר في الغياب والنقص وحده، على مدار الخسارة",
    ),
    "hebrew:family:b825ccaf5025b4c0e48543d2": (
        "كلل",
        "NUCLEUS-TRACE",
        ("كل", "جميع"),
        "כל «الكل والجميع» وحده",
    ),
    "hebrew:family:d6c636a1d355cf166096ec36": (
        "ظبي",
        "ROOT-TRACE",
        ("ظبي", "غزال"),
        "צבי «الظبي والغزال» الحيوان وحده، لا اسم الشخص",
    ),
    "hebrew:family:4e6d0ff7f8e256db90b211b4": (
        "غور",
        "ROOT-TRACE",
        ("مغارة", "غار", "كهف"),
        "מערה «المغارة والكهف» وحدها",
    ),
}


TERMINAL_SPECS: dict[str, tuple[str, str]] = {
    "hebrew:family:f20c69111ede6cfbeba0199a": (
        "INTRA-HOUSE-TRANSFER",
        "سلسلة السلم منقولة من الأكدية داخل البيت السامي؛ لا تعد شاهد فرع مستقل",
    ),
    "hebrew:family:d7756f7631dd8cda1493dbb2": (
        "INTRA-HOUSE-TRANSFER",
        "معنى الكتابة موصوف في المصدر بأنه انتشار دلالي داخل البيت؛ يحال إلى زوج المانح",
    ),
    "hebrew:family:5bd8b2840850d6a4c1a4af23": (
        "LOANWORD",
        "أعضاء נחס موسومة صراحة بأنها مقترضة من العربية نحس",
    ),
}


SPECIAL_TITLES = {
    "צבר، متابعة الرتبة 66",
    "עין، متابعة الرتبة 137",
    "צבי «ظبي» ↔ ظبي",
    "מערה «مغارة» ↔ مغارة",
    "פרעוש «برغوث» ↔ برغوث",
}


def atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", newline="\n", dir=path.parent, delete=False
    ) as handle:
        handle.write(unicodedata.normalize("NFC", text))
        temporary = Path(handle.name)
    temporary.replace(path)


def fold(value: str) -> str:
    value = ARABIC_MARKS.sub("", unicodedata.normalize("NFKC", value))
    value = value.translate(str.maketrans("أإآؤئ", "اااوي"))
    return "".join(value.split())


def replace_one(
    section: str, pattern: re.Pattern[str], replacement: str
) -> tuple[str, str]:
    match = pattern.search(section)
    if not match:
        raise ValueError(f"missing required field: {pattern.pattern}")
    old = match.group(0)
    return (
        section[: match.start()] + replacement + section[match.end() :],
        old,
    )


def parse_fates(text: str) -> dict[str, dict[str, object]]:
    result: dict[str, dict[str, object]] = {}
    for match in FATE.finditer(text):
        rank = int(match.group("rank"))
        if rank > 300:
            continue
        result[match.group("family")] = {
            "rank": rank,
            "fan": match.group("fan").strip(),
            "state": match.group("state").strip(),
            "required": match.group("required").strip(),
        }
    return result


def parse_card_states(
    text: str,
) -> dict[str, list[dict[str, str]]]:
    result: dict[str, list[dict[str, str]]] = defaultdict(list)
    for section in SECTION.split(text):
        match = CARD.match(section)
        if not match:
            continue
        blocker = BLOCKER.search(section)
        verdict = VERDICT.search(section)
        result[match.group("family")].append(
            {
                "title": match.group("title"),
                "blocker": blocker.group(0) if blocker else "",
                "verdict": verdict.group(0) if verdict else "",
            }
        )
    return result


def sibling_verdict(
    family: str,
    title: str,
    states: dict[str, list[dict[str, str]]],
) -> dict[str, str] | None:
    for row in states.get(family, []):
        if row["title"] == title:
            continue
        if "النوع=READY" not in row["blocker"]:
            continue
        if any(prefix in row["verdict"] for prefix in POSITIVE_PREFIXES) or (
            "LOANWORD" in row["verdict"]
        ):
            return row
    return None


def family_rows(
    connection: sqlite3.Connection, family: str
) -> list[dict[str, object]]:
    return [
        {
            "entry_id": row[0],
            "headword": row[1],
            "pos": row[2],
            "gloss": row[3],
            "etymology": row[4],
            "loan_hint": bool(row[5]),
            "form_of": bool(row[6]),
        }
        for row in connection.execute(
            """
            SELECT e.entry_id,e.headword,e.pos,e.gloss,e.etymology,
                   e.loan_hint,e.form_of
            FROM family_members fm
            JOIN entries e ON e.entry_id=fm.entry_id
            WHERE fm.family_id=?
            ORDER BY e.entry_id
            """,
            (family,),
        )
    ]


def candidates(
    connection: sqlite3.Connection, family: str
) -> list[dict[str, object]]:
    return [
        {
            "kind": row[0],
            "form": row[1],
            "status": row[2],
            "rules": json.loads(row[3]),
        }
        for row in connection.execute(
            """
            SELECT DISTINCT c.kind,c.form,c.status,c.rule_ids_json
            FROM family_members fm
            JOIN candidates c ON c.entry_id=fm.entry_id
            WHERE fm.family_id=? AND c.kind IN ('root','hollow-root','nucleus')
            ORDER BY c.kind,c.status,c.form,c.rule_ids_json
            """,
            (family,),
        )
    ]


def branch_anchor(rows: list[dict[str, object]]) -> str:
    anchors = [
        " ".join(str(row["etymology"]).split())
        for row in rows
        if str(row["etymology"]).strip()
    ]
    return " | ".join(anchors[:3])


def positive_decision(
    family: str,
    rows: list[dict[str, object]],
    generated: list[dict[str, object]],
    fans: dict[str, dict[str, object]],
) -> dict[str, object] | None:
    specification = POSITIVE_SPECS.get(family)
    if not specification:
        return None
    root, verdict, terms, scope = specification
    fan = fans[root]
    selected = fan["selected_sources"]
    if not fan["judgment_ready"] or len(selected) < 2:
        raise ValueError(f"{family}: incomplete two-source fan for {root}")
    for witness in selected:
        definition = fold(str(witness["definition"]))
        if not any(fold(term) in definition for term in terms):
            raise ValueError(
                f"{family}: named sense absent from "
                f"{witness['source_label']} for {root}"
            )
    anchor = branch_anchor(rows)
    if not anchor:
        raise ValueError(f"{family}: positive lacks branch etymological anchor")
    licensed = [
        item
        for item in generated
        if item["form"] == root
        and item["status"] in {"licensed", "manual-condition"}
    ]
    sound_rules = min(
        (list(item["rules"]) for item in licensed),
        key=lambda value: (len(value), value),
        default=[],
    )
    sound_note = "تطابق مهيكل مباشر بلا صف إضافي"
    if sound_rules:
        sound_note = "، ".join(sound_rules)
    if family in {
        "hebrew:family:d6c636a1d355cf166096ec36",
        "hebrew:family:44c516f5b29b885c154e5452",
    }:
        sound_note = "DENT-08 اليدوي بشروطه واختبار نفيه"
    if family == "hebrew:family:4e6d0ff7f8e256db90b211b4":
        sound_note = (
            "اندماج الغين الشمالية العضوي المثبت في نص الأصل، بلا صف عام"
        )
    return {
        "state": "READY",
        "positive": True,
        "closure": False,
        "verdict": verdict,
        "root": root,
        "terms": list(terms),
        "scope": scope,
        "sources": [item["source_label"] for item in selected],
        "witnesses": selected,
        "branch_anchor": anchor,
        "sound_note": sound_note,
    }


def held_or_terminal_decision(
    family: str,
    fate: dict[str, object] | None,
) -> dict[str, object]:
    if family in TERMINAL_SPECS:
        state, note = TERMINAL_SPECS[family]
        return {
            "state": state,
            "positive": False,
            "closure": True,
            "verdict": "LOANWORD" if state == "LOANWORD" else "غير صادر",
            "note": note,
            "fan": str(fate["fan"]) if fate else "مستنفدة في البطاقة",
        }
    if fate:
        if fate["state"] == "READY":
            raise ValueError(
                f"{family}: fate says READY but no issued sibling was found"
            )
        state = str(fate["state"])
        note = str(fate["required"])
        if state == "TOOL-GAP":
            state = "SOURCE-GAP"
            note = (
                "استنفد المسح الآلي ولم يوفر مصدرين عربيين قديمين مستقلين؛ "
                f"{note}"
            )
        return {
            "state": state,
            "positive": False,
            "closure": False,
            "verdict": "غير صادر",
            "note": note,
            "fan": str(fate["fan"]),
        }
    if family == "hebrew:family:9bb9582b5980353810e095c2":
        return {
            "state": "SOURCE-GAP",
            "positive": False,
            "closure": False,
            "verdict": "غير صادر",
            "note": (
                "لا مروحة مصدرين قديمين للمادة برغوث، ولا شاهد عبري قديم "
                "مسمى للعضو"
            ),
            "fan": "استنفدت، ولم تكتمل لمادة برغوث",
        }
    raise ValueError(f"{family}: no fate or explicit terminal decision")


def referral_decision(
    sibling: dict[str, str],
    fate: dict[str, object] | None,
) -> dict[str, object]:
    return {
        "state": "REFERRED",
        "positive": False,
        "closure": True,
        "verdict": "غير صادر",
        "note": (
            "بطاقة أقدم أحيلت إلى الحكم العضوي اللاحق في الأسرة نفسها؛ "
            "لا تعد صلة جديدة"
        ),
        "fan": str(fate["fan"]) if fate else "مفصلة في بطاقة الحكم اللاحقة",
        "referred_to": sibling["title"],
    }


def apply_decision(
    section: str,
    family: str,
    batch: str,
    decision: dict[str, object],
) -> tuple[str, dict[str, str]]:
    marker = f"<!-- ARABIC-FAN-CAMPAIGN:{batch}:{family} -->"
    if marker in section:
        return section, {"already_applied": "true"}
    state = str(decision["state"])
    section, old_blocker = replace_one(
        section,
        BLOCKER,
        f"- عائق: النوع={state}؛ يتطلب="
        f"{decision.get('scope') or decision.get('note')}؛",
    )
    if "النوع=TOOL-GAP" not in old_blocker:
        raise ValueError(f"{family}: target no longer starts at TOOL-GAP")
    scan_text = (
        "مروحة مستقلة مكتملة للجذر "
        f"`{decision['root']}` من "
        + " + ".join(decision["sources"])
        + "؛ تحقق المعنى في المصدرين بلا اقتطاع"
        if decision["positive"]
        else str(decision.get("fan") or "استنفدت وسمي عائقها الجاري")
    )
    section, old_scan = replace_one(
        section,
        SCAN,
        f"- مسحُ المعاني العربيّة: {scan_text}.",
    )
    section, old_closure = replace_one(
        section, CLOSURE, f"- حالةُ الإغلاق: {state}."
    )
    if decision["positive"]:
        verdict_line = (
            f"- الحكم (استكشاف): {decision['verdict']}؛ "
            f"{decision['scope']}؛ لا وراثة عبر عضو مخالف."
        )
    elif decision["verdict"] == "LOANWORD":
        verdict_line = "- الحكم (استكشاف): LOANWORD؛ عزل بلا حكم نسب."
    else:
        verdict_line = f"- الحكم (استكشاف): غير صادر؛ {decision['note']}."
    section, old_verdict = replace_one(section, VERDICT, verdict_line)

    lines = [
        "",
        marker,
        f"- ملحق حملة المروحة العبرية، {DATE}:",
        f"  - المصير الجاري: `{state}`.",
    ]
    if decision["positive"]:
        lines.extend(
            [
                f"  - الجذر أو النواة العربية: `{decision['root']}`.",
                "  - المصدران العربيان القديمان: "
                + " + ".join(decision["sources"])
                + ".",
                "  - ألفاظ التحقق الدلالي: "
                + "، ".join(f"`{term}`" for term in decision["terms"])
                + ".",
                f"  - سند الفرع المنشور: {decision['branch_anchor']}",
                f"  - مسار الصوت اللازم وحده: {decision['sound_note']}.",
            ]
        )
    elif decision.get("referred_to"):
        lines.append(f"  - الإحالة الحية: {decision['referred_to']}.")
    else:
        lines.append(f"  - نتيجة المروحة: {decision.get('fan')}.")
    lines.extend(
        [
            "  - السجل التاريخي المحفوظ:",
            f"    - `{old_blocker}`",
            f"    - `{old_scan}`",
            f"    - `{old_closure}`",
            f"    - `{old_verdict}`",
        ]
    )
    return section.rstrip() + "\n" + "\n".join(lines) + "\n\n", {
        "old_blocker": old_blocker,
        "old_scan": old_scan,
        "old_closure": old_closure,
        "old_verdict": old_verdict,
    }


def target_card(
    title: str,
    start_rank: int | None,
    end_rank: int | None,
    extras: bool,
) -> tuple[bool, int | None]:
    rank_match = RANK.search(title)
    if rank_match and start_rank is not None and end_rank is not None:
        rank = int(rank_match.group("rank"))
        return start_rank <= rank <= end_rank, rank
    if extras and title in SPECIAL_TITLES:
        return True, None
    return False, None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start-rank", type=int)
    parser.add_argument("--end-rank", type=int)
    parser.add_argument("--extras", action="store_true")
    args = parser.parse_args()
    rank_mode = args.start_rank is not None or args.end_rank is not None
    if rank_mode and (
        args.start_rank is None
        or args.end_rank is None
        or not (1 <= args.start_rank <= args.end_rank <= 300)
    ):
        raise SystemExit("provide a complete rank window within 1-300")
    if not rank_mode and not args.extras:
        raise SystemExit("provide a rank window or --extras")

    batch = (
        f"HEBREW-{args.start_rank:03d}-{args.end_rank:03d}"
        if rank_mode
        else "HEBREW-EXTRAS"
    )
    text = READING.read_text(encoding="utf-8")
    fates = parse_fates(text)
    states = parse_card_states(text)
    needed_roots = {
        POSITIVE_SPECS[family][0]
        for family in POSITIVE_SPECS
    }
    matches = matches_for_roots(DEFAULT_RESOURCES, needed_roots, None)
    fans = {
        root: independent_fan(matches[root])
        for root in sorted(needed_roots)
    }

    parts = SECTION.split(text)
    output: list[str] = []
    records: list[dict[str, object]] = []
    connection = sqlite3.connect(DB)
    try:
        for section in parts:
            match = CARD.match(section)
            if not match:
                output.append(section)
                continue
            title = match.group("title")
            is_target, rank = target_card(
                title,
                args.start_rank,
                args.end_rank,
                args.extras,
            )
            if not is_target or "النوع=TOOL-GAP" not in section:
                output.append(section)
                continue
            family = match.group("family")
            fate = fates.get(family)
            sibling = sibling_verdict(family, title, states)
            rows = family_rows(connection, family)
            generated = candidates(connection, family)
            if sibling:
                decision = referral_decision(sibling, fate)
            else:
                decision = (
                    positive_decision(family, rows, generated, fans)
                    or held_or_terminal_decision(family, fate)
                )
            changed, history = apply_decision(
                section, family, batch, decision
            )
            output.append(changed)
            records.append(
                {
                    "family": family,
                    "title": title,
                    "rank": rank,
                    "members": [row["entry_id"] for row in rows],
                    **decision,
                    "history": history,
                }
            )
    finally:
        connection.close()

    if not records:
        raise ValueError(f"{batch}: no live TOOL-GAP target cards found")
    updated = "".join(output)
    if unicodedata.normalize("NFC", updated) != updated:
        raise ValueError("Hebrew reading is not NFC")
    atomic_write(READING, updated)

    positives = [row for row in records if row["positive"]]
    closures = [row for row in records if row["closure"]]
    held = [
        row
        for row in records
        if not row["positive"] and not row["closure"]
    ]
    payload = {
        "schema": "arabic-fan-campaign-hebrew-v1",
        "status": "LOCAL-THIRD-LENS-REVIEW-REQUIRED",
        "date": DATE,
        "batch": batch,
        "language": "hebrew",
        "rank_window": (
            [args.start_rank, args.end_rank] if rank_mode else None
        ),
        "summary": {
            "cards_reviewed": len(records),
            "positive_connections": len(positives),
            "positive_verdicts": dict(
                sorted(Counter(row["verdict"] for row in positives).items())
            ),
            "closures": len(closures),
            "closure_states": dict(
                sorted(Counter(row["state"] for row in closures).items())
            ),
            "held_states": dict(
                sorted(Counter(row["state"] for row in held).items())
            ),
        },
        "records": records,
    }
    suffix = (
        f"{args.start_rank:03d}-{args.end_rank:03d}"
        if rank_mode
        else "extras"
    )
    cache = (
        ROOT
        / "cache"
        / "recovery_pipeline"
        / f"arabic-fan-campaign-hebrew-{suffix}.json"
    )
    audit = (
        ROOT
        / "05-audits"
        / f"2026-07-25-arabic-fan-campaign-hebrew-{suffix}.md"
    )
    atomic_write(cache, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    positive_text = "، ".join(
        f"{key}={value}"
        for key, value in payload["summary"]["positive_verdicts"].items()
    ) or "لا شيء"
    closure_text = "، ".join(
        f"{key}={value}"
        for key, value in payload["summary"]["closure_states"].items()
    ) or "لا شيء"
    held_text = "، ".join(
        f"{key}={value}"
        for key, value in payload["summary"]["held_states"].items()
    ) or "لا شيء"
    atomic_write(
        audit,
        "\n".join(
            [
                f"# حملة المروحة العبرية، الدفعة {suffix}",
                "",
                "دفعة أحكام محلية للمراجعة المضادة الثالثة. الإحالات إلى حكم قائم ليست صلات جديدة، وتبقى منفصلة في العد.",
                "",
                "## الرقمان المفصولان",
                "",
                f"- الصلات الموجبة الجديدة: {len(positives)} ({positive_text}).",
                f"- الإغلاقات: {len(closures)} ({closure_text}).",
                "",
                f"- بقي معلقا بسببه الحقيقي: {held_text}.",
                "- لا رقم في هذا المحضر للنشر ولا تشغيل لخط البرهان.",
                "",
            ]
        ),
    )
    print(json.dumps(payload["summary"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
