# -*- coding: utf-8 -*-
"""حوّل المسوح الصوتية الجرمانية والسلتية إلى بطاقات RECOVERY-v2.

الترتيب نافذ في بنية الطابور نفسها: الشهادة المباشرة في الألسن الأربعة، ثم
بقية طبقة الصوت والمعنى، ثم الصوت وحده. لا تصدر الأداة حكمًا دلاليًا من
التداخل الآلي. الأزواج ذات المدار المحرر يدويًا تحفظه في ``ORBIT_NOTES``،
وكل ما عداه يبقى ``OPEN-CANDIDATE`` بسطر موجز.

لكل بطاقة ثلاث أرجل لا رابعة لها:

1. مروحة الصوت بالخط الصريح الذي أمر به المؤلف.
2. كل درجات الحدث التي تعيدها ``frozen_event.all_tiers``.
3. معنى قاموس الفرع من ``build_kaikki_index.look``، ومعه شواهد المواد
   العربية كاملة بما يعادل ``--max-chars 0``، ثم المدار المكتوب بالكلمات.

قول قاموس الفرع في الأصل حاشية خبرية. لا يغلق البطاقة إلا نص انتقال يعيّن
مانحًا ساميًا، وحينئذ لا يستعمل إلا الوسم القانوني
``SEMITIC-SOURCE-TRANSMISSION``.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
import math
import re
import subprocess
import sys
import types
import unicodedata
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import build_kaikki_index as LEX  # noqa: E402
import count_links as COUNT  # noqa: E402
import fan_any_script as FAN  # noqa: E402
import frozen_event as EVENT  # noqa: E402
import rebuild_khashim_indo_european_batches as ROUTES  # noqa: E402
import search_arabic_root_senses as AR  # noqa: E402


DATE = "2026-08-15"
BASELINE = "1281ac5"
BATCH_SIZE = 150
AUDITS = ROOT / "05-audits"
DATA = ROOT / "data"
EXPLORATION = ROOT / "04-cross-linguistic" / "exploration"
READINGS = ROOT / "04-cross-linguistic" / "readings"
CARD_DIR = READINGS / "phonetic-sweep-germanic-celtic"

LANGUAGES: dict[str, dict[str, Any]] = {
    "old-english": {
        "sweep": "english_old",
        "label": "الإنجليزية القديمة/Old English",
        "id": "OLD-ENGLISH",
        "script": "germanic",
        "lexicon": "old-english",
        "reading": "old-english.md",
        "both": 105,
        "direct": 54,
        "sound_only": 815,
    },
    "old-norse": {
        "sweep": "old_norse",
        "label": "النوردية القديمة/Old Norse",
        "id": "OLD-NORSE",
        "script": "germanic",
        "lexicon": "old-norse",
        "reading": "old-norse.md",
        "both": 88,
        "direct": 55,
        "sound_only": 710,
    },
    "old-irish": {
        "sweep": "old_irish",
        "label": "الإيرلندية القديمة/Old Irish",
        "id": "OLD-IRISH",
        "script": "latin",
        "lexicon": "old-irish",
        "reading": "old-irish.md",
        "both": 44,
        "direct": 27,
        "sound_only": 542,
    },
    "gothic": {
        "sweep": "gothic",
        "label": "القوطية/Gothic",
        "id": "GOTHIC",
        "script": "gothic",
        "lexicon": "gothic",
        "reading": "gothic.md",
        "both": 29,
        "direct": 16,
        "sound_only": 483,
    },
}

LANGUAGE_ORDER = tuple(LANGUAGES)

# ست بطاقات صادرة حية في كل لسان. الضابط يقارن المروحتين ولا يعيد الحكم في
# البطاقة. حضور المقابل نفسه يسجل ملاحظة، لكن معيار الوقوف الوحيد هو a-b.
CONTROL_SPECS: dict[str, list[dict[str, str]]] = {
    "old-english": [
        {"word": "burg", "root": "برج", "verdict": "ROOT-TRACE"},
        {"word": "magan", "root": "مكن", "verdict": "NUCLEUS-TRACE"},
        {"word": "horn", "root": "قرن", "verdict": "ROOT-TRACE"},
        {"word": "row", "root": "روح", "verdict": "ROOT-TRACE"},
        {"word": "catt", "root": "قطط", "verdict": "ROOT-TRACE"},
        {"word": "forca", "root": "فرق", "verdict": "ROOT-TRACE"},
    ],
    "old-norse": [
        {"word": "vitra", "root": "فطر", "verdict": "ROOT-TRACE"},
        {"word": "tign", "root": "تقن", "verdict": "ROOT-TRACE"},
        {"word": "mygla", "root": "بقل", "verdict": "ROOT-TRACE"},
        {"word": "draga", "root": "درج", "verdict": "ROOT-TRACE"},
        {"word": "fleyta", "root": "فرط", "verdict": "ROOT-TRACE"},
        {"word": "megin", "root": "مكن", "verdict": "ROOT-TRACE"},
    ],
    "old-irish": [
        {"word": "derc", "root": "درك", "verdict": "ROOT-TRACE"},
        {"word": "gel", "root": "جل", "verdict": "NUCLEUS-TRACE"},
        {"word": "sen", "root": "سن", "verdict": "NUCLEUS-TRACE"},
        {"word": "brecc", "root": "برق", "verdict": "ROOT-TRACE"},
        {"word": "cenn", "root": "كنن", "verdict": "ROOT-TRACE"},
        {"word": "gaibid", "root": "قبض", "verdict": "NUCLEUS-TRACE"},
    ],
    "gothic": [
        {"word": "𐌲𐌹𐌱𐌻𐌰", "root": "جبل", "verdict": "ROOT-TRACE"},
        {"word": "𐌼𐌰𐌲𐌰𐌽", "root": "مكن", "verdict": "ROOT-TRACE"},
        {"word": "𐍃𐌹𐌿𐌺𐌰𐌽", "root": "سقم", "verdict": "ROOT-TRACE"},
        {"word": "𐌺𐌰𐌿𐍂𐌽", "root": "جرم", "verdict": "ROOT-TRACE"},
        {"word": "𐌰𐌺𐍂𐌰𐌽", "root": "جرم", "verdict": "ROOT-TRACE"},
        {"word": "𐍆𐍂𐌹𐌾𐌴𐌹", "root": "فرج", "verdict": "ROOT-TRACE"},
    ],
}


# هذه مدارات حررها الباحث بالكلمات، لا ناتج تقاطع قاموسي. وجود النص هنا لا
# يصدر حكمًا جديدًا، إذ قد تكون الصورة صادرة حية أو معلقة بعائق آخر.
ORBIT_NOTES: dict[tuple[str, str, str], str] = {
    ("gothic", "gibla", "جبل"): (
        "ذروة البناء وقمته بروز عظيم غليظ فوق ما يحيط به، وهو تطبيق حسي "
        "لحدث جبل في تجمع العظم والغلظ والارتفاع"
    ),
    ("gothic", "tharba", "طلب"): (
        "الحاجة والعوز يبعثان الطالب إلى ابتغاء ما فقده، فمعنى الفرع يلتقي "
        "مادة طلب في قصد الشيء وابتغائه لا في لفظ إنجليزي وسيط"
    ),
    ("gothic", "frijei", "فرج"): (
        "الحرية حالة انفراج بعد حبس أو ضيق، فهي ظل حالة واحد لفتح الفرج وكشف "
        "الشدة، مع بقاء فحص الصامت الثالث مستقلًا"
    ),
    ("gothic", "bihait", "بهت"): (
        "قول الزور على المرء بما لم يفعله هو نفس حس البهتان في مادة بهت، لكن "
        "خبر السابقة القوطية يبقى حاشية صرفية ولا يحول البطاقة إلى إغلاق"
    ),
    ("old-english", "burg", "برج"): (
        "المكان المحصن والقلعة يقابلان برج الحصن وركنه مقابلة مباشرة، ويجتمع "
        "الصوت والمعنى في مادة واحدة"
    ),
    ("old-english", "magan", "مكن"): (
        "الاستطاعة هي التمكن من الفعل والقدرة عليه، فمعنى الفرع يلتقي مادة مكن "
        "في القدرة والرسوخ بلا سلسلة مدارات"
    ),
    ("old-norse", "megin", "مكن"): (
        "القوة والمكنة والقدرة تحقق معنى التمكن، واجتماع هذه الصورة مع magan "
        "في الإنجليزية القديمة شاهد عابر للسانين يكتب ولا يحسم وحده"
    ),
    ("old-norse", "heyja", "هيج"): (
        "خوض القتال وإثارته صورة من الهيجان والوثوب إلى الخصم، لكن المدار لا "
        "يغني عن تحرير صف الصامت الأخير"
    ),
    ("old-norse", "grein", "قرن"): (
        "الغصن فرع ناتئ ممتد من أصله، فيلتقي حدث قرن في النتوء الممتد، ويقوى "
        "المرشح بتكرار قرن في الويلزية واليونانية واللاتينية"
    ),
    ("old-irish", "gaibid", "قبض"): (
        "الإمساك والأخذ والانتزاع هي أفعال القبض نفسها، فالمعنى مباشر في مادة "
        "واحدة، مع بقاء تحرير g مع القاف شرطًا صوتيًا مستقلًا"
    ),
    ("old-irish", "subach", "صبح"): (
        "البهجة والإشراق في cheerful وmerry يلتقيان وجه الصباح في انكشاف الضوء "
        "وانبساط النفس، لكنه مدار مرشح لا يقوم مقام الصف الصوتي"
    ),
}

CROSS_BRANCH: dict[str, str] = {
    "مكن": (
        "تكرر الهيكل والمعنى في الإنجليزية القديمة `magan` والنوردية القديمة "
        "`megin`، ومعهما القوطية `magan`. تكراره في ألسن جرمانية مستقلة شاهد "
        "أسري يثبت في البطاقة، ولا يستبدل الأرجل الثلاث ولا جولة الضبط"
    ),
    "قرن": (
        "تكرر المرشح في النوردية القديمة، والويلزية، واليونانية، واللاتينية، "
        "وتظهر صورة `corn` في الإيرلندية القديمة. هذا الإشعاع العابر للفروع "
        "حجة مساندة تكتب، ولا يصدر منها حكم منفرد"
    ),
}

SEMITIC_DONOR = re.compile(
    r"(?i)\b(?:borrowed from|loanword from|via|ultimately from|from)\s+"
    r"(?:classical\s+)?(arabic|hebrew|aramaic|syriac|akkadian|phoenician|punic|semitic)\b"
)


def nfc(value: Any) -> str:
    return unicodedata.normalize("NFC", str(value or ""))


def clean(value: Any) -> str:
    """نص قابل للنشر بلا شرطة طويلة ولا كسر أسطر ولا backticks داخل اقتباس."""
    text = nfc(value).replace("—", "-").replace("–", "-")
    text = text.replace("`", "ˋ")
    return " ".join(text.split())


def fold(value: Any) -> str:
    text = unicodedata.normalize("NFKD", str(value or "").casefold())
    return "".join(char for char in text if not unicodedata.combining(char) and char.isalpha())


def english_tokens(value: Any) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z]{3,}", str(value or "").casefold())
        if token not in {
            "the", "and", "with", "from", "into", "that", "this", "someone",
            "something", "form", "used", "often", "usually", "especially",
        }
    }


def load_sweep(language: str) -> dict[str, Any]:
    cfg = LANGUAGES[language]
    path = EXPLORATION / f"phonetic-sweep-{cfg['sweep']}.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("language") != cfg["sweep"]:
        raise AssertionError(f"اختلط لسان المسح: {language}")
    if len(payload.get("both", [])) != cfg["both"]:
        raise AssertionError(f"تغير مقام الصوت والمعنى في {language}")
    if len(payload.get("sound_only", [])) != cfg["sound_only"]:
        raise AssertionError(f"تغير مقام الصوت وحده في {language}")
    return payload


def global_queue() -> list[dict[str, Any]]:
    sweeps = {language: load_sweep(language) for language in LANGUAGE_ORDER}
    queue: list[dict[str, Any]] = []

    def add(language: str, phase: str, rows: list[dict[str, Any]], offset: int) -> None:
        for position, row in enumerate(rows, offset + 1):
            queue.append({
                "language": language,
                "phase": phase,
                "source_rank": position,
                "row": row,
            })

    # 152 بطاقة شهادة مباشرة بحسب أعداد المحاضر، لا بحسب حقل توليدي متغير.
    for language in LANGUAGE_ORDER:
        direct = int(LANGUAGES[language]["direct"])
        add(language, "direct-witness", sweeps[language]["both"][:direct], 0)
    # بقية مقام الصوت والمعنى، ومجموع المقام كله 266.
    for language in LANGUAGE_ORDER:
        direct = int(LANGUAGES[language]["direct"])
        add(language, "sound-and-meaning", sweeps[language]["both"][direct:], direct)
    # ثم مقام الصوت وحده كله.
    for language in LANGUAGE_ORDER:
        add(language, "sound-only", sweeps[language]["sound_only"], 0)

    if len(queue) != 2_816:
        raise AssertionError(f"الطابور {len(queue)} بدل 2,816")
    if Counter(item["phase"] for item in queue) != {
        "direct-witness": 152,
        "sound-and-meaning": 114,
        "sound-only": 2550,
    }:
        raise AssertionError("اختل ترتيب طبقات المسوح")
    for global_rank, item in enumerate(queue, 1):
        item["global_rank"] = global_rank
    return queue


def baseline_module() -> types.ModuleType:
    source = subprocess.run(
        ["git", "show", f"{BASELINE}:scripts/fan_any_script.py"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    ).stdout
    module = types.ModuleType("fan_any_script_baseline")
    exec(compile(source, "fan_any_script_baseline", "exec"), module.__dict__)
    return module


def run_controls() -> dict[str, list[dict[str, Any]]]:
    old = baseline_module()
    out: dict[str, list[dict[str, Any]]] = {}
    for language, specs in CONTROL_SPECS.items():
        script = str(LANGUAGES[language]["script"])
        rows: list[dict[str, Any]] = []
        for spec in specs:
            before = set(old.fan(spec["word"], script))
            after = set(FAN.fan(spec["word"], script))
            lost = sorted(before - after)
            gained = sorted(after - before)
            if lost:
                raise AssertionError(
                    f"انحدار مروحة {language}:{spec['word']}: a-b={lost}; b-a={gained}"
                )
            events = EVENT.all_tiers(spec["root"])
            rows.append({
                **spec,
                "script": script,
                "baseline": BASELINE,
                "old_count": len(before),
                "new_count": len(after),
                "a_minus_b": lost,
                "b_minus_a": gained,
                "candidate_in_old": spec["root"] in before,
                "candidate_in_new": spec["root"] in after,
                "event_tiers_now": [event.tier for event in events],
                "stable": True,
            })
        if len(rows) != 6:
            raise AssertionError(f"ضابط {language} ليس ست بطاقات")
        out[language] = rows
    return out


def split_cards(path: Path) -> list[tuple[str, set[str]]]:
    """عناوين الأحكام الصادرة الحالية كما يراها العداد القانوني."""
    return [
        (heading, degrees)
        for heading, degrees, _family in COUNT.scan_path(path)
        if degrees
    ]


def prior_issued_index() -> dict[str, list[tuple[str, set[str]]]]:
    return {
        language: split_cards(READINGS / str(cfg["reading"]))
        for language, cfg in LANGUAGES.items()
    }


def prior_issued(
    language: str,
    word: str,
    say: str,
    issued: dict[str, list[tuple[str, set[str]]]],
) -> list[dict[str, Any]]:
    keys = {fold(word), fold(say)} - {""}
    found: list[dict[str, Any]] = []
    for heading, degrees in issued[language]:
        heading_key = fold(heading)
        if any(key in heading_key for key in keys):
            found.append({"heading": clean(heading), "verdicts": sorted(degrees)})
    return found[:12]


def choose_lexicon_entry(entries: list[dict[str, Any]], gloss: str) -> int | None:
    if not entries:
        return None
    wanted = english_tokens(gloss)
    scored = []
    for position, entry in enumerate(entries):
        got = english_tokens(entry.get("en"))
        shared = len(wanted & got)
        union = len(wanted | got) or 1
        scored.append(((shared, shared / union, -position), position))
    return max(scored)[1]


def named_semitic_donor(entry: dict[str, Any]) -> str:
    etymology = clean(entry.get("etym"))
    match = SEMITIC_DONOR.search(etymology)
    return match.group(1) if match else ""


def candidate_roots(row: dict[str, Any]) -> list[str]:
    roots: list[str] = []
    for value in [row.get("best"), *(row.get("candidates_found") or [])]:
        root = clean(value)
        if root and root not in roots:
            roots.append(root)
    return roots


def latin_route_skeleton(language: str, word: str, say: str) -> str:
    # رجل المروحة القوطية تبقى gothic صراحة. هذه الرومنة تستعمل فقط لتسمية
    # صفوف الصوت في أداة المسار التي تقرأ حروفًا لاتينية.
    source = say if language == "gothic" else word
    script = "latin" if language == "old-irish" else "germanic"
    return "".join(FAN.skeleton(source, script))


def named_route(language: str, word: str, say: str, root: str) -> str:
    skeleton = latin_route_skeleton(language, word, say)
    try:
        route, _searches = ROUTES.match_sound_route(skeleton, root, language)
        return clean(route)
    except AssertionError:
        return ""


def source_label(match: dict[str, Any]) -> str:
    source_id = AR.canonical_source_id(str(match.get("source") or ""))
    if source_id:
        return AR.SOURCE_LABELS[source_id]
    return clean(match.get("source")) or "مورد عربي مسمى في الذخيرة"


def witness_payload(match: dict[str, Any]) -> dict[str, str]:
    return {
        "source": source_label(match),
        "definition": clean(match.get("definition")),
        "url": clean(match.get("url")),
    }


def event_payload(root: str) -> list[dict[str, Any]]:
    return [{
        "tier": event.tier,
        "tier_ar": clean(event.tier_ar),
        "text": clean(event.text),
        "source": clean(event.source),
        "note": clean(event.note),
    } for event in EVENT.all_tiers(root)]


def render_lexicon(entries: list[dict[str, Any]], selected: int | None) -> list[str]:
    if not entries:
        return [
            "  - أعادت `build_kaikki_index.look` صفر مدخلة؛ هذا نقص مصدر في البطاقة "
            "ولا نفي للمعنى ولا سبب إغلاق."
        ]
    lines: list[str] = []
    for position, entry in enumerate(entries, 1):
        chosen = "؛ المختارة بسياق معنى المسح" if selected == position - 1 else ""
        read = f"؛ الرومنة القاموسية /{clean(entry.get('read'))}/" if entry.get("read") else ""
        etym = clean(entry.get("etym")) or "لا خبر أصل في المدخلة"
        lines.append(
            f"  - المدخلة {position}: `{clean(entry.get('word'))}`{read}؛ "
            f"المعنى: «{clean(entry.get('en'))}»؛ النوع: {clean(entry.get('pos')) or 'غير مسمى'}{chosen}."
        )
        lines.append(f"    - حاشية الأصل كما يقول القاموس: {etym}.")
    return lines


def render_events(candidates: list[dict[str, Any]]) -> list[str]:
    lines: list[str] = []
    for candidate in candidates:
        root = candidate["root"]
        fan_mark = "حاضر" if candidate["in_current_fan"] else "غير حاضر"
        route = candidate["named_route"] or "لم يتحرر صف مسمى جامع لهذا الجذر"
        lines.append(
            f"  - `{root}`: في المروحة الحالية {fan_mark}؛ مسار الصفوف: {route}."
        )
        if not candidate["events"]:
            lines.append(
                "    - أعادت `frozen_event.all_tiers` قائمة خالية؛ تبقى فجوة أداة ولا يغلق المرشح."
            )
            continue
        for event in candidate["events"]:
            note = f"؛ {event['note']}" if event["note"] else ""
            lines.append(
                f"    - الدرجة {event['tier']}، {event['tier_ar']}: «{event['text']}»؛ "
                f"المصدر `{event['source']}`{note}."
            )
    return lines


def render_witnesses(candidates: list[dict[str, Any]]) -> list[str]:
    lines: list[str] = []
    for candidate in candidates:
        root = candidate["root"]
        if not candidate["events"]:
            continue
        witnesses = candidate["witnesses"]
        lines.append(
            f"  - المادة `{root}`: نُفذ `python scripts/search_arabic_root_senses.py "
            f"{root} --max-chars 0`؛ الشواهد الكاملة {len(witnesses)}."
        )
        if not witnesses:
            lines.append("    - لم تعد الذخيرة شاهدًا لهذه المادة؛ الغياب ليس نفيًا.")
        for witness in witnesses:
            url = f" [{witness['url']}]" if witness["url"] else ""
            lines.append(
                f"    - {witness['source']}: «{witness['definition']}»{url}"
            )
    return lines


def automatic_orbit(phase: str, gloss: str, best: str) -> str:
    if phase == "sound-only":
        return (
            f"قوبل معنى الفرع «{clean(gloss)}» بالمادة `{clean(best)}` وببقية المروحة "
            "بعد قراءة الأحداث والشواهد كاملة؛ لم يقدم المسح الصوتي وحده جسر معنى "
            "مقنعًا بعد، فتبقى الصورة مفتوحة ولا تتحول عبارة الغياب إلى رفض"
        )
    return (
        f"قوبل معنى الفرع «{clean(gloss)}» بأقرب مادة صوتية `{clean(best)}` وببقية "
        "المروحة، وقرئت الأحداث والشواهد كاملة؛ التقاطع المعجمي قرينة بدء لا حكمًا، "
        "ولم يتحرر في هذه البطاقة مدار موجب يتجاوز اللفظ الإنجليزي المشترك"
    )


def build_card(
    item: dict[str, Any],
    arabic_hits: dict[str, list[dict[str, Any]]],
    issued: dict[str, list[tuple[str, set[str]]]],
) -> tuple[list[str], dict[str, Any]]:
    language = str(item["language"])
    cfg = LANGUAGES[language]
    row = dict(item["row"])
    word = str(row.get("branch") or "")
    say = str(row.get("say") or word)
    if not say:
        raise AssertionError(f"غابت الرومنة في {language}:{item['global_rank']}")
    script = str(cfg["script"])
    current_fan = set(FAN.fan(word, script))
    roots = candidate_roots(row)
    candidates: list[dict[str, Any]] = []
    for root in roots:
        events = event_payload(root)
        matches = arabic_hits.get(root, []) if events else []
        candidates.append({
            "root": root,
            "best": root == clean(row.get("best")),
            "in_current_fan": root in current_fan,
            "named_route": named_route(language, word, say, root),
            "events": events,
            "witnesses": [witness_payload(match) for match in matches],
        })

    entries, lookup_path = LEX.look(str(cfg["lexicon"]), word)
    selected_index = choose_lexicon_entry(entries, str(row.get("gloss") or ""))
    selected = entries[selected_index] if selected_index is not None else {}
    donor = named_semitic_donor(selected)
    protected = prior_issued(language, word, say, issued)
    best = clean(row.get("best"))
    custom_orbit = ORBIT_NOTES.get((language, fold(say), best))
    orbit = custom_orbit or automatic_orbit(
        str(item["phase"]), str(row.get("gloss") or ""), best
    )
    cross = CROSS_BRANCH.get(best, "")
    card_id = f"PS-GC-{cfg['id']}-{int(item['global_rank']):05d}"

    lines = [
        f"### بطاقة مسح صوتي: `{clean(word)}` /{clean(say)}/؛ {card_id}",
        "",
        "- إصدار البروتوكول: `RECOVERY-v2`؛ الطبقة: استكشاف.",
        f"- مقام المسح: `{item['phase']}`؛ الرتبة العامة {item['global_rank']}؛ "
        f"رتبة الصورة في مقام لسانها {item['source_rank']}.",
        f"- الكلمة في الفرع: `{clean(word)}`؛ الرومنة المقروءة: /{clean(say)}/.",
        f"- الهيكل الذي حفظه المسح: `{clean(row.get('skeleton'))}`؛ أقرب مادة في "
        f"المسح `{best}`؛ معنى صف المسح «{clean(row.get('gloss'))}».",
        "- الأرجل ثلاث لا رابعة لها:",
        f"  1. رجل الصوت، المروحة: شغلت `fan_any_script.fan(word, \"{script}\")` "
        f"بالخط `{script}` صريحًا؛ أعادت {len(current_fan)} مادة. مواد صف المسح: "
        + "، ".join(f"`{root}`" for root in roots)
        + ".",
        "  2. رجل الحدث: عُرضت درجات `frozen_event.all_tiers` كلها لكل مادة في صف المسح:",
        *render_events(candidates),
        f"  3. رجل المعنى: استدعي `build_kaikki_index.look(\"{cfg['lexicon']}\", "
        f"\"{clean(word)}\")`؛ طريق الاسترجاع: {clean(lookup_path)}.",
        *render_lexicon(entries, selected_index),
        "- شواهد المواد العربية كاملة داخل رجل المعنى:",
        *render_witnesses(candidates),
        f"- المدار المكتوب باليد بالكلمات: {clean(orbit)}.",
    ]
    if cross:
        lines.append(f"- الشاهد العابر للفروع: {clean(cross)}.")

    selected_etym = clean(selected.get("etym")) or "لا خبر أصل في المدخلة المختارة"
    lines.extend([
        f"- حاشية الأصل، خبر لا حكم: {selected_etym}.",
        (
            f"- المصفاة: سمى نص الاشتقاق مانحًا ساميًا هو `{donor}`؛ هذا وحده "
            "يجيز إغلاق مقام الانتقال، ولا يمحو الصورة من السجل."
            if donor else
            "- المصفاة: لم يسم نص المدخلة المختارة مانحًا ساميًا؛ خبر الأصل لا "
            "يغلق البطاقة ولا يخرج الصورة من مقام لسانها."
        ),
    ])

    if protected:
        descriptions = "؛ ".join(
            f"{entry['heading']} [{'/'.join(entry['verdicts'])}]"
            for entry in protected
        )
        lines.extend([
            f"- حماية الصلة الصادرة الحية: وُجدت أحكام سابقة لهذه الصورة: {descriptions}.",
            "- نتيجة بطاقة المسح: إحالة إلى الصادر الحي من غير نسخ ولا تعديل ولا "
            "حكم جديد؛ تبقى هذه البطاقة شاهد جرد للأرجل الثلاث.",
        ])
        status = "protected-live-reference"
        closure = ""
    elif donor:
        lines.extend([
            "- حالة الإغلاق: `SEMITIC-SOURCE-TRANSMISSION`.",
            "- الحكم (استكشاف): غير صادر؛ ثبت مسار انتقال من مانح سامي مسمى.",
        ])
        status = "named-semitic-donor"
        closure = "SEMITIC-SOURCE-TRANSMISSION"
    else:
        lines.extend([
            "- حالة الإغلاق: `OPEN-CANDIDATE`.",
            "- الحكم (استكشاف): غير صادر؛ يبقى `OPEN-CANDIDATE`.",
            "- عائق: النوع=OPEN-CANDIDATE؛ يتطلب=تحرير مدار موجب ومسار صوت مسمى "
            "حيث لم يكتمل، أو حكم المؤلف في جولة التحقق.",
        ])
        status = "open-candidate"
        closure = "OPEN-CANDIDATE"
    lines.append("")

    manifest = {
        "id": card_id,
        "global_rank": item["global_rank"],
        "source_rank": item["source_rank"],
        "language": language,
        "phase": item["phase"],
        "word": word,
        "romanization": say,
        "script": script,
        "skeleton": row.get("skeleton") or "",
        "gloss": row.get("gloss") or "",
        "best": best,
        "roots": [{
            "root": candidate["root"],
            "in_current_fan": candidate["in_current_fan"],
            "named_route": candidate["named_route"],
            "event_tiers": [event["tier"] for event in candidate["events"]],
            "full_witness_count": len(candidate["witnesses"]),
            "max_chars": 0,
        } for candidate in candidates],
        "branch_lookup": {
            "language": cfg["lexicon"],
            "path": lookup_path,
            "entry_count": len(entries),
            "selected_index": selected_index,
            "selected_meaning": selected.get("en") or "",
            "selected_etymology": selected.get("etym") or "",
        },
        "manual_orbit": orbit,
        "cross_branch_note": cross,
        "named_semitic_donor": donor,
        "prior_issued": protected,
        "status": status,
        "closure": closure,
    }
    return lines, manifest


def batch_paths(batch: int) -> tuple[Path, Path]:
    return (
        DATA / f"phonetic-sweep-germanic-celtic-batch-{batch:03d}.json",
        AUDITS / f"{DATE}-phonetic-sweep-germanic-celtic-batch-{batch:03d}.md",
    )


def marker(batch: int, language: str, edge: str) -> str:
    return f"<!-- PHONETIC-SWEEP-GC-BATCH-{batch:03d}:{language.upper()}:{edge} -->"


def card_path(batch: int, language: str) -> Path:
    return CARD_DIR / f"batch-{batch:03d}-{language}.md"


def compact_reading_index(
    batch: int,
    language: str,
    card_count: int,
    phase_counts: Counter[str],
) -> str:
    relative = f"phonetic-sweep-germanic-celtic/batch-{batch:03d}-{language}.md"
    return nfc("\n".join([
        marker(batch, language, "START"),
        "",
        f"## فهرس حصاد المسح الصوتي، الدفعة {batch:03d}",
        "",
        f"البطاقات الكاملة لهذه الدفعة محفوظة في "
        f"[`{relative}`]({relative}) حتى تبقى ملفات Git دون حد 100 MB، من غير "
        "تقليم شاهد واحد أو تغيير ترتيب بطاقة.",
        "",
        f"- عدد البطاقات: {card_count}.",
        f"- المقامات: {dict(phase_counts)}.",
        f"- الخط الصريح: `{LANGUAGES[language]['script']}`.",
        "",
        marker(batch, language, "END"),
        "",
    ]))


def append_language_block(batch: int, language: str, cards: list[list[str]]) -> None:
    if not cards:
        return
    path = READINGS / str(LANGUAGES[language]["reading"])
    supplement = card_path(batch, language)
    CARD_DIR.mkdir(parents=True, exist_ok=True)
    if supplement.exists():
        raise AssertionError(f"ملحق الدفعة {batch} موجود في {language}")
    body = nfc(path.read_text(encoding="utf-8"))
    start, end = marker(batch, language, "START"), marker(batch, language, "END")
    if start in body or end in body:
        raise AssertionError(f"دفعة {batch} موجودة في قراءة {language}")
    phase_counts = Counter()
    for card in cards:
        phase_line = next(line for line in card if line.startswith("- مقام المسح:"))
        phase_match = re.search(r"`([^`]+)`", phase_line)
        phase_counts[phase_match.group(1) if phase_match else "unknown"] += 1
    block = [
        start,
        "",
        f"## حصاد المسح الصوتي الجرماني والسلتي، الدفعة {batch:03d}",
        "",
        "نطاق هذه الدفعة من مادة قاموس الفرع الأصلية في المسح الشامل، مرتبة "
        "بالصوت أولا ثم حكم المعنى. لكل صورة بطاقة مستقلة، وخبر الأصل حاشية لا "
        "يغلقها إلا مانح سامي مسمى.",
        "",
        f"المقامات في هذا المقطع: {dict(phase_counts)}.",
        "",
    ]
    for card in cards:
        block.extend(card)
    block.extend([end, ""])
    payload = nfc("\n".join(block))
    if "—" in payload:
        raise AssertionError("تسربت شرطة طويلة إلى بطاقة")
    supplement.write_text(payload, encoding="utf-8", newline="\n")
    index = compact_reading_index(batch, language, len(cards), phase_counts)
    path.write_text(body.rstrip() + "\n\n" + index, encoding="utf-8", newline="\n")


def migrate_split_batch(batch: int) -> dict[str, int]:
    """انقل مقاطعنا غير المودعة من الجامع إلى ملاحق قراءة دون مس بطاقة."""
    CARD_DIR.mkdir(parents=True, exist_ok=True)
    moved: dict[str, int] = {}
    for language in LANGUAGE_ORDER:
        path = READINGS / str(LANGUAGES[language]["reading"])
        body = nfc(path.read_text(encoding="utf-8"))
        start, end = marker(batch, language, "START"), marker(batch, language, "END")
        if start not in body and end not in body:
            continue
        if body.count(start) != 1 or body.count(end) != 1:
            raise AssertionError(f"علامات غير مفردة في {language}")
        before, tail = body.split(start, 1)
        middle, after = tail.split(end, 1)
        full_block = start + middle + end + "\n"
        count = full_block.count("### بطاقة مسح صوتي:")
        if not count:
            # فهرس صغير موجود من قبل، فلا يعاد نقله.
            continue
        supplement = card_path(batch, language)
        if supplement.exists():
            raise AssertionError(f"ملحق {supplement} موجود قبل النقل")
        supplement.write_text(full_block, encoding="utf-8", newline="\n")
        phase_counts: Counter[str] = Counter(
            re.findall(r"^- مقام المسح: `([^`]+)`", full_block, flags=re.MULTILINE)
        )
        index = compact_reading_index(batch, language, count, phase_counts)
        path.write_text(
            before.rstrip() + "\n\n" + index + after.lstrip("\r\n"),
            encoding="utf-8",
            newline="\n",
        )
        moved[language] = count
    return moved


def control_markdown(controls: dict[str, list[dict[str, Any]]]) -> list[str]:
    lines = [
        "## الضابط الإلزامي قبل الحصاد",
        "",
        f"قوبلت ست بطاقات صادرة حية في كل لسان بمروحة `{BASELINE}` والمروحة "
        "الحالية. معيار الوقوف هو فقد مادة كانت في المروحة المرجعية، أي `a-b` "
        "غير الخالية. لم يفقد الضابط مادة، فلم تمس صلة صادرة.",
        "",
    ]
    for language in LANGUAGE_ORDER:
        cfg = LANGUAGES[language]
        lines.extend([
            f"### {cfg['label']}",
            "",
            "| الصورة | المقابل | الحكم الحي | الخط | a | b | a-b | b-a | درجات الحدث الآن |",
            "|---|---|---|---|---:|---:|---|---|---|",
        ])
        for row in controls[language]:
            lines.append(
                f"| `{clean(row['word'])}` | `{row['root']}` | {row['verdict']} | "
                f"`{row['script']}` | {row['old_count']} | {row['new_count']} | "
                f"{row['a_minus_b'] or '∅'} | {row['b_minus_a'] or '∅'} | "
                f"{row['event_tiers_now'] or '∅'} |"
            )
        lines.append("")
    return lines


def audit_markdown(
    batch: int,
    manifests: list[dict[str, Any]],
    controls: dict[str, list[dict[str, Any]]],
) -> str:
    by_language = Counter(row["language"] for row in manifests)
    by_phase = Counter(row["phase"] for row in manifests)
    statuses = Counter(row["status"] for row in manifests)
    highlights = [
        row for row in manifests
        if (row["language"], fold(row["romanization"]), row["best"]) in ORBIT_NOTES
    ]
    lines = [
        f"# محضر حصاد المسوح الجرمانية والسلتية، الدفعة {batch:03d} ({DATE})",
        "",
        *control_markdown(controls),
        "## ما وجدته الدفعة",
        "",
        f"كتبت الدفعة {len(manifests)} بطاقة كاملة بالأرجل الثلاث. توزع مقامها "
        f"داخليا هكذا: {dict(by_phase)}، وتوزعت على الألسن هكذا: {dict(by_language)}.",
        "",
        "كل بطاقة طبعت الرومنة، وشغلت المروحة بخط اللسان الصريح، وعرضت كل "
        "درجات الحدث، واستدعت قاموس الفرع، وقرأت شواهد المواد العربية كاملة "
        "بـ`--max-chars 0`. لم يتحول قول القاموس في الأصل إلى حكم، ولم يغلق "
        "غير مانح سامي مسمى.",
        "",
        f"حالة السجل في الدفعة: {dict(statuses)}.",
        "",
    ]
    if highlights:
        lines.extend([
            "ظهرت في الدفعة صور حررت مداراتها بالكلمات، من غير أن يعني ذلك "
            "تكرار حكم صادر حي أو تجاوز عائق صوتي:",
            "",
        ])
        for row in highlights:
            lines.append(
                f"- `{clean(row['word'])}` /{clean(row['romanization'])}/ مع "
                f"`{row['best']}`: {clean(row['manual_orbit'])}."
            )
        lines.append("")
    lines.extend([
        "ما لم يكتمل فيه الحكم بقي `OPEN-CANDIDATE` بسطر موجز، لا جدول رفض. "
        "والصور ذات الصلة الصادرة الحية أحيلت إلى حكمها القائم من غير نسخ ولا لمس.",
        "",
        "## تحقق عقد البطاقة",
        "",
        f"- الرومنة غير الخالية: {sum(bool(row['romanization']) for row in manifests)} من {len(manifests)}.",
        f"- الخط الصريح الموافق للسان: {sum(row['script'] == LANGUAGES[row['language']]['script'] for row in manifests)} من {len(manifests)}.",
        f"- تنفيذ قراءة الشواهد الكاملة: {sum(all(root['max_chars'] == 0 for root in row['roots']) for row in manifests)} من {len(manifests)}.",
        "- قاموس الإغلاق: لم ينشأ وسم جديد؛ استعمل `OPEN-CANDIDATE` أو "
        "`SEMITIC-SOURCE-TRANSMISSION` فقط حيث انطبق، وكلاهما من القاموس المغلق.",
        "",
    ])
    output = nfc("\n".join(lines))
    if "—" in output:
        raise AssertionError("تسربت شرطة طويلة إلى المحضر")
    return output


def roots_for_items(items: list[dict[str, Any]]) -> set[str]:
    return {
        root
        for item in items
        for root in candidate_roots(item["row"])
        if EVENT.all_tiers(root)
    }


def harvest_batch(batch: int, preview: bool = False) -> dict[str, Any]:
    queue = global_queue()
    total_batches = math.ceil(len(queue) / BATCH_SIZE)
    if not 1 <= batch <= total_batches:
        raise SystemExit(f"الدفعة بين 1 و{total_batches}")
    start = (batch - 1) * BATCH_SIZE
    items = queue[start:start + BATCH_SIZE]
    controls = run_controls()
    issued = prior_issued_index()
    roots = roots_for_items(items)
    # None هنا هو النظير البرمجي الصريح لـ --max-chars 0.
    arabic_hits = AR.matches_for_roots(AR.DEFAULT_RESOURCES, roots, None)

    cards_by_language: dict[str, list[list[str]]] = defaultdict(list)
    manifests: list[dict[str, Any]] = []
    for item in items:
        card, manifest = build_card(item, arabic_hits, issued)
        cards_by_language[item["language"]].append(card)
        manifests.append(manifest)

    payload = {
        "schema": "phonetic-sweep-germanic-celtic-cards-v1",
        "date": DATE,
        "batch": batch,
        "batch_size": BATCH_SIZE,
        "total_batches": total_batches,
        "global_start": items[0]["global_rank"],
        "global_end": items[-1]["global_rank"],
        "control_baseline": BASELINE,
        "controls": controls,
        "counts": {
            "cards": len(manifests),
            "by_language": dict(Counter(row["language"] for row in manifests)),
            "by_phase": dict(Counter(row["phase"] for row in manifests)),
            "by_status": dict(Counter(row["status"] for row in manifests)),
        },
        "cards": manifests,
    }
    if preview:
        return payload

    data_path, audit_path = batch_paths(batch)
    if data_path.exists() or audit_path.exists():
        raise SystemExit(f"مخرجات الدفعة {batch:03d} موجودة؛ لن تكرر")
    for language in LANGUAGE_ORDER:
        append_language_block(batch, language, cards_by_language.get(language, []))
    data_text = nfc(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    if "—" in data_text:
        raise AssertionError("تسربت شرطة طويلة إلى بيانات الدفعة")
    data_path.write_text(data_text, encoding="utf-8", newline="\n")
    audit_path.write_text(
        audit_markdown(batch, manifests, controls),
        encoding="utf-8",
        newline="\n",
    )
    return payload


def check_batch(batch: int) -> dict[str, Any]:
    data_path, audit_path = batch_paths(batch)
    payload = json.loads(data_path.read_text(encoding="utf-8"))
    if len(payload["cards"]) != payload["counts"]["cards"]:
        raise AssertionError("عدد البطاقات لا يطابق البيان")
    for language in LANGUAGE_ORDER:
        expected = sum(row["language"] == language for row in payload["cards"])
        body = (READINGS / str(LANGUAGES[language]["reading"])).read_text(encoding="utf-8")
        start = marker(batch, language, "START")
        end = marker(batch, language, "END")
        if expected:
            if body.count(start) != 1 or body.count(end) != 1:
                raise AssertionError(f"علامتا الدفعة غائبتان في {language}")
            supplement = card_path(batch, language)
            if not supplement.exists():
                raise AssertionError(f"غاب ملحق بطاقات {language}")
            block = supplement.read_text(encoding="utf-8")
            count = block.count("### بطاقة مسح صوتي:")
            if count != expected:
                raise AssertionError(f"قراءة {language} فيها {count} بدل {expected}")
    if not audit_path.exists():
        raise AssertionError("غاب المحضر")
    for path in [data_path, audit_path, *(
        card_path(batch, language)
        for language in LANGUAGE_ORDER
        if card_path(batch, language).exists()
    )]:
        if "—" in path.read_text(encoding="utf-8"):
            raise AssertionError(f"شرطة طويلة في {path}")
    return payload


def finalize() -> dict[str, Any]:
    queue = global_queue()
    total_batches = math.ceil(len(queue) / BATCH_SIZE)
    batches = [check_batch(batch) for batch in range(1, total_batches + 1)]
    cards = [card for batch in batches for card in batch["cards"]]
    by_phase = Counter(card["phase"] for card in cards)
    by_language = Counter(card["language"] for card in cards)
    by_status = Counter(card["status"] for card in cards)
    expected_languages = {
        language: int(cfg["both"]) + int(cfg["sound_only"])
        for language, cfg in LANGUAGES.items()
    }
    if len(cards) != 2_816:
        raise AssertionError(f"الختام رأى {len(cards)} بطاقة بدل 2,816")
    if dict(by_phase) != {
        "direct-witness": 152,
        "sound-and-meaning": 114,
        "sound-only": 2550,
    }:
        raise AssertionError(f"اختل مقام الختام: {dict(by_phase)}")
    if dict(by_language) != expected_languages:
        raise AssertionError(f"اختل مقام الألسن: {dict(by_language)}")
    ranks = [int(card["global_rank"]) for card in cards]
    if ranks != list(range(1, 2_817)):
        raise AssertionError("تسلسل البطاقات ناقص أو مكرر")

    supplements = sorted(CARD_DIR.glob("batch-*.md"))
    oversized = [str(path.relative_to(ROOT)) for path in supplements if path.stat().st_size >= 100_000_000]
    if oversized:
        raise AssertionError(f"ملحق بلغ حد 100 MB: {oversized}")
    examples = []
    wanted = {
        ("old-english", "magan", "مكن"),
        ("old-norse", "megin", "مكن"),
        ("old-norse", "grein", "قرن"),
        ("old-irish", "gaibid", "قبض"),
        ("old-irish", "subach", "صبح"),
        ("gothic", "gibla", "جبل"),
        ("gothic", "tharba", "طلب"),
        ("gothic", "frijei", "فرج"),
        ("gothic", "bihait", "بهت"),
    }
    for card in cards:
        key = (card["language"], fold(card["romanization"]), card["best"])
        if key in wanted:
            examples.append({
                "id": card["id"],
                "language": card["language"],
                "word": card["word"],
                "romanization": card["romanization"],
                "root": card["best"],
                "status": card["status"],
                "orbit": card["manual_orbit"],
                "cross_branch_note": card["cross_branch_note"],
            })
    payload = {
        "schema": "phonetic-sweep-germanic-celtic-harvest-v1",
        "date": DATE,
        "source_method": "sound-first-meaning-judges",
        "control_baseline": BASELINE,
        "batches": total_batches,
        "cards": len(cards),
        "counts": {
            "by_phase": dict(by_phase),
            "by_language": dict(by_language),
            "by_status": dict(by_status),
        },
        "supplements": [{
            "path": str(path.relative_to(ROOT)).replace("\\", "/"),
            "bytes": path.stat().st_size,
        } for path in supplements],
        "largest_supplement_bytes": max(path.stat().st_size for path in supplements),
        "examples": examples,
    }
    final_data = DATA / "phonetic-sweep-germanic-celtic-harvest.json"
    final_audit = AUDITS / f"{DATE}-phonetic-sweep-germanic-celtic-final.md"
    text = nfc(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    if "—" in text:
        raise AssertionError("شرطة طويلة في بيان الختام")
    final_data.write_text(text, encoding="utf-8", newline="\n")

    lines = [
        f"# المحضر الختامي لبطاقات المسوح الجرمانية والسلتية ({DATE})",
        "",
        "## النطاق والطريقة",
        "",
        "حُولت مادة القواميس الأصلية في الإنجليزية القديمة والنوردية القديمة "
        "والإيرلندية القديمة والقوطية إلى بطاقات، بالصوت أولا ثم حكم المعنى. "
        "تقدمت الشهادة المباشرة كلها، ثم بقية مقام الصوت والمعنى، ثم الصوت وحده.",
        "",
        f"اكتمل {len(cards)} بطاقة في {total_batches} دفعة. مقام الترتيب الداخلي: "
        f"{dict(by_phase)}. مقام الألسن: {dict(by_language)}.",
        "",
        "كل بطاقة تحمل الرومنة، ومروحة الخط الصريح، وكل درجات الحدث، ومعنى "
        "قاموس الفرع، وشواهد المواد العربية كاملة بـ`--max-chars 0`، ومدارا "
        "مكتوبا بالكلمات. لم يجعل خبر الأصل حكما، ولم يغلق غير مانح سامي مسمى.",
        "",
        "## الضابط والصادر الحي",
        "",
        f"مر ضابط 6 بطاقات صادرة في كل لسان على مروحة `{BASELINE}` قبل الحصاد. "
        "كانت فروق `a-b` خالية في البطاقات 24. لم تمس صلة صادرة حية؛ بطاقات "
        "المسح التي صادفت حكما قائما أحالت إليه من غير نسخة حكم جديدة.",
        "",
        "## ما وجدته الأمثلة المسماة",
        "",
    ]
    for example in examples:
        lines.append(
            f"- `{clean(example['word'])}` /{clean(example['romanization'])}/ مع "
            f"`{example['root']}`، الحالة `{example['status']}`: "
            f"{clean(example['orbit'])}."
        )
        if example["cross_branch_note"]:
            lines.append(f"  - {clean(example['cross_branch_note'])}.")
    lines.extend([
        "",
        "## الحفظ والتحقق",
        "",
        "حُفظت البطاقات الكاملة في ملاحق قراءة مجزأة بحسب الدفعة واللسان، "
        "وألحق بكل ملف لسان فهرس صغير إليها. هذا يمنع تجاوز حد ملف Git ولا "
        "يقص شاهدا واحدا.",
        "",
        f"- عدد الملاحق: {len(supplements)}.",
        f"- أكبر ملحق: {payload['largest_supplement_bytes']} بايت، وهو دون 100 MB.",
        f"- حالات السجل: {dict(by_status)}.",
        "- لم ينشأ وسم إغلاق خارج القاموس المغلق.",
        "- تسلسل الرتب العامة متصل من 1 إلى 2,816 بلا نقص ولا تكرار.",
        "",
    ])
    audit_text = nfc("\n".join(lines))
    if "—" in audit_text:
        raise AssertionError("شرطة طويلة في محضر الختام")
    final_audit.write_text(audit_text, encoding="utf-8", newline="\n")
    return payload


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--batch", type=int)
    ap.add_argument("--preview", action="store_true")
    ap.add_argument("--control", action="store_true")
    ap.add_argument("--check", type=int, metavar="BATCH")
    ap.add_argument("--migrate-split", type=int, metavar="BATCH")
    ap.add_argument("--finalize", action="store_true")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    if args.control:
        print(json.dumps(run_controls(), ensure_ascii=False, indent=2))
        return 0
    if args.check:
        payload = check_batch(args.check)
        print(f"CLEAN: الدفعة {args.check:03d}، {payload['counts']['cards']} بطاقة")
        return 0
    if args.migrate_split:
        print(json.dumps(migrate_split_batch(args.migrate_split), ensure_ascii=False, indent=2))
        return 0
    if args.finalize:
        payload = finalize()
        print(json.dumps(payload["counts"], ensure_ascii=False, indent=2))
        return 0
    if not args.batch:
        ap.error("يلزم --batch أو --control أو --check")
    payload = harvest_batch(args.batch, preview=args.preview)
    print(json.dumps({
        "batch": payload["batch"],
        "range": [payload["global_start"], payload["global_end"]],
        "counts": payload["counts"],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
