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
import build_kaikki_index as LEX  # noqa: E402
import search_arabic_root_senses as ARS  # noqa: E402

READINGS = ROOT / "04-cross-linguistic" / "readings"
NETWORK = ROOT / "04-cross-linguistic" / "shift-network-draft.md"
PRIOR_ART = ROOT / "data" / "prior-art-extended-pairs.json"
SOURCE_GATE = "الصورة المذكورة لم تثبت في لقطة الطبقة التاريخية المختارة"
EVENT_GATE = "لم يوجد حدث مجمد لمرشح صالح داخل المروحة"
BATCH_SIZE = 150
DATE = "2026-08-14"

# هذه هي البطاقات التي كان سبب فتحها ORBIT-NOT-CONVINCING قبل إعادة
# FAN-EMPTY.  تثبيت القائمة يمنع اختلاطها بالبطاقات التي انتقلت من
# FAN-EMPTY إلى سبب المدار بعد إصلاح الساق اللاتيني.
ORIGINAL_ORBIT_TARGETS: dict[int, tuple[int, ...]] = {
    1: (
        2, 8, 11, 12, 13, 19, 22, 27, 30, 37, 38, 43, 49, 50, 52, 53,
        55, 56, 57, 58, 65, 66, 67, 68, 73, 80, 81, 83, 85, 86, 117,
        121, 132, 147, 148, 149, 150, 153, 159, 162, 165, 166, 167, 174,
        175, 183, 185, 186, 188, 189, 190, 195, 196, 199, 205, 209, 210,
        211, 212, 232, 233, 248, 251, 277, 280, 283,
    ),
    2: (
        285, 288, 289, 290, 292, 293, 295, 302, 306, 309, 310, 328, 329,
        331, 334, 335, 337, 339, 341, 342, 347, 350, 352, 353, 355, 365,
        371, 374, 388, 389, 395, 411, 415, 417, 420, 421, 422, 423, 424,
        425, 426, 427, 432, 434, 435, 441, 446, 447, 448, 449, 459, 464,
        465, 473, 474, 478, 480, 481, 482, 483, 484, 488, 489, 492, 493,
        500, 516, 520, 523, 531, 532, 534, 535, 539, 542, 543, 551, 554,
        556, 557, 559, 561,
    ),
    3: (
        569, 570, 571, 573, 574, 575, 577, 578, 579, 582, 584, 586, 597,
        604, 609, 611, 612, 621, 626, 629, 633, 634, 637, 638, 643, 644,
        645, 646, 647, 648, 649, 651, 652, 658, 670, 671, 679, 683, 687,
        691, 692, 696, 699, 717, 718, 720, 722, 725, 728, 729, 730, 731,
        732, 733, 737, 745, 746, 759, 765, 767, 768, 773, 774, 778, 779,
        780, 783, 784, 787, 789, 790, 795, 797, 803, 804, 805, 806, 807,
        810, 811, 812, 813, 815, 817, 818, 828, 830, 832, 835, 836, 837,
        838, 840, 842, 843, 846, 848, 855,
    ),
}
ORIGINAL_FAN_EMPTY_COUNTS = {1: 58, 2: 44, 3: 38}

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
BRANCH_LEXICON_LANGUAGE = {
    "ancient-greek": "ancient-greek",
    "gothic": "gothic",
    "middle-english": "middle-english",
    "old-english": "old-english",
    "old-irish": "old-irish",
    "old-latin": "latin",
    "old-norse": "old-norse",
    "welsh": "welsh",
}

# لا يُنتخَب مدخلٌ من قائمة الهيكل آليًا. هذا الاختيار الوحيد في بقية
# البوابتين راجعه الكاتب على سياق الصف: ``road`` في المصدر تقابله ``rode``
# «ride, journey, voyage» في قاموس الإنجليزية الوسطى. وما عداه من موجبات
# الدفعتين 004 و006 لا يسنده قاموس الفرع، فلا يصدر في الإعادة الجديدة.
MANUAL_BRANCH_SELECTED: dict[int, tuple[str, str]] = {
    38: ("cok", "rooster, cock"),
    43: ("dude", "did"),
    81: ("cornet", "A cornet"),
    85: ("sope", "Soap; a cleaning agent"),
    153: ("fredom", "freedom, liberty"),
    162: ("meson", "a house"),
    165: ("meson", "a house"),
    166: ("mansioun", "A place where one makes their home"),
    195: ("mor", "moor"),
    205: ("mariner", "sailor"),
    289: ("dialog", "An organised talk between two people"),
    302: ("Capitolie", "Roman Capitol, Capitolium"),
    310: ("historie", "A (written) narrative"),
    520: ("Crist", "Christ"),
    532: ("gele", "A jelly"),
    543: ("amour", "love, affection"),
    575: ("aketoun", "A jacket with padding"),
    604: ("brike", "A breach"),
    609: ("plat", "flat; level"),
    651: ("hostel", "A hostel or guesthouse"),
    699: ("lof", "loaf (block of bread)"),
    718: ("maister", "master; lord; ruler"),
    720: ("maister", "master; lord; ruler"),
    725: ("mages", "Wizards, occult scholars"),
    729: ("magicien", "magician, mage"),
    783: ("moder", "A mother"),
    803: ("band", "a restraint"),
    804: ("bonde", "tenant farmer, bond"),
    805: ("band", "a restraint"),
    812: ("mariage", "marriage"),
    813: ("boye", "servant, attendant"),
    815: ("baby", "A child or baby"),
    818: ("girle", "A girl"),
    828: ("madame", "madam"),
    832: ("man", "man (male human)"),
    837: ("womman", "A female adult person"),
    843: ("femele", "A woman"),
    1092: ("rode", "ride, journey, voyage"),
}
MANUAL_ORBIT_OVERRIDES: dict[tuple[int, str], str] = {
    (1092, "رود"): (
        "مدخل الفرع `rode` معناه الحرفي «ride, journey, voyage». ويقول تاج "
        "العروس في شاهد الجذر: «الرَّوْدُ الذهابُ والمجيءُ، يقال راد يرود إذا "
        "جاء وذهب ولم يطمئنّ»؛ فالسفر والركوب ذهابٌ ومجيءٌ على الطريق، وهذا "
        "هو المدار المسمّى إلى حدث `رود`."
    ),
}
MANUAL_ROOT_WITNESS_SOURCE: dict[tuple[int, str], str] = {
    (609, "بلط"): "lisan",
    (699, "ربب"): "al_muhkam",
    (1092, "رود"): "taj_al_arus",
}

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
    438: [{
        "root": "بنن",
        "orbit": "الرائحة الطيبة تنبعث من مادتها وتمتد في الهواء امتدادًا لطيفًا؛ فمعنى الطيب في نقل المصدر يصل إلى امتداد الشيء اللطيف من أصله في حدث `بنن`.",
    }],
    510: [{
        "root": "كوب",
        "orbit": "قدح الماء وعاء مجوف مستدير يضم الشراب في باطنه؛ فمعنى القدح في نقل المصدر يصل إلى انبعاج الشيء المجوف مستديرًا في حدث `كوب`.",
    }],
    511: [{
        "root": "كوب",
        "orbit": "قدح الماء وعاء مجوف مستدير يضم الشراب في باطنه؛ فمعنى القدح في نقل المصدر يصل إلى انبعاج الشيء المجوف مستديرًا في حدث `كوب`.",
    }],
    512: [{
        "root": "كوب",
        "orbit": "الكأس وعاء مقعر مستدير يحمل الشراب في جوفه؛ فمعنى `cup` يصل مباشرة إلى انبعاج الشيء المجوف مستديرًا في حدث `كوب`.",
    }],
    515: [{
        "root": "مسح",
        "orbit": "المسيح هو الممسوح بالدهن، والمسح يبسط الدهن على ظاهر الجسد حتى يستوي عليه؛ فمعنى الممسوح يصل إلى انبساط الظاهر واستوائه في حدث `مسح`.",
    }],
    625: [{
        "root": "جن",
        "orbit": "الجن في معنى الفرع كائن مستور عن العين لا يظهر في العادة؛ فخفاء شخصه يصل مباشرة إلى الستر والكثافة في حدث النواة `جن`.",
    }],
    609: [{
        "root": "بلط",
        "witness_quote": "البَلاطُ: الأَرضُ، وقيل: الأَرض المُسْتَوِيةُ المَلْساء",
        "orbit": (
            "مدخل الفرع `plat` يصف الأرض بأنها «flat; level»، أي سطح منبسط "
            "مستوٍ. ونصُّ لسان العرب لابن منظور: «البَلاطُ: الأَرضُ، وقيل: "
            "الأَرض المُسْتَوِيةُ المَلْساء»؛ فاستواء سطح الهضبة وانتشاره "
            "العريض يصلان `plateau` إلى الانبساط المنتشر في حدث `بلط`."
        ),
    }],
    699: [{
        "root": "ربب",
        "witness_quote": (
            "والرُّبُّ دِبْسُ كُلِّ ثَمَرَةٍ وهو سُلافَةُ خُثارَتِها "
            "بعدَ الاعْتِصارِ والطَّبْخِ"
        ),
        "orbit": (
            "مدخل الفرع `lof` معناه «loaf (block of bread)»، أي كتلة غذاء "
            "تتماسك بالعمل والحرارة. ونصُّ المحكم والمحيط الأعظم لابن سيده "
            "الأندلسي: «والرُّبُّ دِبْسُ كُلِّ ثَمَرَةٍ وهو سُلافَةُ خُثارَتِها "
            "بعدَ الاعْتِصارِ والطَّبْخِ»؛ فالتخثّر بالطبخ حتى تصير المادة كتلةً "
            "صالحة للانتفاع يصل الرغيف إلى حدث `ربب`."
        ),
    }],
    966: [{
        "root": "ريف",
        "orbit": "الضفة شريط طرفي ممتد يفصل الماء من اليابسة، وتلين أرضها بقرب الماء؛ فمعنى الشاطئ يصل إلى الامتداد والطرفية مع الرخاوة في حدث `ريف`.",
    }],
    1037: [{
        "root": "سكر",
        "orbit": "المكان الآمن يُحمى بسد منافذ الدخول على المهاجم؛ فمعنى الحماية من الخطر يصل إلى سد الفتحة واحتباس ما يجري منها في حدث `سكر`.",
    }],
    1074: [{
        "root": "بنك",
        "orbit": "مقعد القضاة جسم مبني ممتد يجلس عليه أكثر من واحد؛ فمعنى bench في الفرع يصل إلى الامتداد والبناء في حدث `بنك`.",
    }],
    1121: [{
        "root": "بوص",
        "orbit": "المرور من جانب إلى آخر حركة تنفذ خلال الموضع وتتجاوزه؛ فمعنى `pass` يصل مباشرة إلى النفاذ في حدث `بوص`.",
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


def skeleton_variant_items(form: str, script: str) -> list[dict[str, Any]]:
    """Return every skeleton used by the fan, preserving its morphology label."""
    items: list[dict[str, Any]] = []
    seen: set[str] = set()

    def add(letters: list[str], label: str, usable: bool | None = None) -> None:
        value = "".join(letters)
        if not value or value in seen:
            return
        seen.add(value)
        items.append({
            "skeleton": value,
            "label": label,
            "usable": 2 <= len(letters) <= 4 if usable is None else usable,
        })

    raw = F.skeleton(form, script)
    raw_label = "كما وردَت"
    if not 2 <= len(raw) <= 4:
        raw_label += "؛ خارج حدّ المروحة"
    add(raw, raw_label)

    if script in {"latin", "germanic", "greek"}:
        for ending in F.LATIN_ENDINGS:
            if form.lower().endswith(ending) and len(form) - len(ending) >= 2:
                alternate = F.skeleton(form[:-len(ending)], script)
                if 2 <= len(alternate) <= 4:
                    add(alternate, f"بإسقاطِ لاحقةِ `-{ending}`")
                break
    if script in {"latin", "germanic"} and len(raw) > 4:
        for alternate, label in F.latin_stem_skeletons(form, script):
            add(alternate, label)
    return items


def skeleton_variants(form: str, script: str) -> str:
    return "|".join(
        item["skeleton"] for item in skeleton_variant_items(form, script)
        if item["usable"]
    )


def render_skeleton_variants(items: list[dict[str, Any]]) -> str:
    return " / ".join(
        f"`{item['skeleton']}` ({item['label']})" for item in items
    ) or "∅"


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
    sources = [
        source
        for item in skeleton_variant_items(form, script) if item["usable"]
        for source in item["skeleton"]
    ]
    for source in sources:
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


def branch_entry_text(entry: dict[str, Any]) -> str:
    reading = f" /{entry['read']}/" if entry.get("read") else ""
    etymology = f"؛ الاشتقاق: «{entry['etym']}»" if entry.get("etym") else ""
    return (
        f"`{clean(entry.get('word'))}`{reading} [{clean(entry.get('pos')) or '—'}] "
        f"«{clean(entry.get('en')) or '—'}»{etymology}"
    )


def branch_lexicon_payload(index: int, language: str, word: str) -> dict[str, Any]:
    lexicon_language = BRANCH_LEXICON_LANGUAGE[language]
    hits, how = LEX.look(lexicon_language, word)
    selected = None
    specification = MANUAL_BRANCH_SELECTED.get(index)
    if specification:
        wanted_word, wanted_sense = specification
        selected = next((
            entry for entry in hits
            if entry.get("word") == wanted_word
            and wanted_sense.casefold() in str(entry.get("en") or "").casefold()
        ), None)
        if selected is None:
            raise AssertionError(
                f"manual branch entry missing for DG-{index:04d}: {specification}"
            )
    return {
        "language": lexicon_language,
        "source": f"data/branch-lexicons/{lexicon_language}.json",
        "query": word,
        "lookup_path": how,
        "entries": hits,
        "selected": selected,
        "selection_note": (
            "اختير المدخل يدويًا لأنه يوافق سياق الصف، بعد عرض القائمة كلها."
            if selected else
            "عُرضت القائمة كلها، ولم ينتخب الكاتب مدخلًا يحمل حكم هذه الصورة."
        ),
    }


def witness_with_source(item: dict[str, Any]) -> dict[str, Any]:
    source = str(item.get("source") or "")
    source_id = ARS.canonical_source_id(source)
    return {
        **item,
        "source_id": source_id,
        "source_label": ARS.SOURCE_LABELS.get(source_id, source),
    }


def compact_root_sense(
    root: str,
    matches: list[dict[str, Any]],
    retain_witnesses: bool = False,
) -> dict[str, Any]:
    fan = ARS.independent_fan(matches)
    truncated = any(bool(item.get("definition_truncated")) for item in matches)
    return {
        "root": root,
        "match_count": len(matches),
        "command": f"python scripts/search_arabic_root_senses.py {root} --max-chars 0",
        "max_chars": 0,
        "truncated": truncated,
        "all_witnesses_reviewed": True,
        "judgment_ready": fan["judgment_ready"],
        "selected_source_labels": [
            item["source_label"] for item in fan["selected_sources"]
        ],
        # لا نكرر المتون الضخمة لكل مرشح. نحتفظ بها كاملةً فقط للجذور التي
        # اختير منها شاهد في مدار موجب، كي نتحقق من الاقتباس حرفيًا.
        "witnesses": (
            [witness_with_source(item) for item in matches]
            if retain_witnesses else []
        ),
    }


def root_senses_for_indices(
    indices: list[int],
    blocks: dict[int, str],
    files: dict[int, str],
    forms: dict[int, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Read every ready Arabic root in one untruncated scan for the whole batch."""
    roots: set[str] = set()
    citation_roots = {
        spec["root"]
        for index in indices
        for spec in MANUAL_SPECS.get(index, [])
    }
    for index in indices:
        language = files[index]
        review, _ = current_fan(str(forms[index]["form"]), language, set())
        roots.update(
            item["root"] for item in review if item["sound"] and item["event_tier"]
        )
    matches = ARS.matches_for_roots(ARS.DEFAULT_RESOURCES, roots, limit=None)
    return {
        root: compact_root_sense(
            root,
            matches.get(ARS.normalize_root(root), []),
            retain_witnesses=root in citation_roots,
        )
        for root in sorted(roots)
    }


def root_sense_line(item: dict[str, Any]) -> str:
    sources = "، ".join(item.get("selected_source_labels", [])) \
        or "لا شاهدين مستقلين مكتملين"
    return (
        f"`{item['root']}`: قُرئت الشواهدُ كلُّها وعددها {item['match_count']}؛ "
        f"المصادر المنتخبة للتثبّت {sources}؛ القراءة كاملة بلا قطع "
        f"(`--max-chars 0`)"
    )


def public_root_sense(item: dict[str, Any]) -> dict[str, Any]:
    """Drop retained full definitions after exact-quote validation."""
    return {
        key: value for key, value in item.items() if key != "witnesses"
    }


def build_card(
    index: int,
    language: str,
    block: str,
    form: dict[str, Any],
    raw_rows: list[dict[str, Any]],
    root_senses: dict[str, dict[str, Any]] | None = None,
) -> tuple[list[str], dict[str, Any], str]:
    word = str(form["form"])
    fan_script = script_for(language)
    fan_skeletons = skeleton_variant_items(word, fan_script)
    branch_lexicon = branch_lexicon_payload(index, language, word)
    stem_labels = [
        item["label"] for item in fan_skeletons
        if item["label"] != "كما وردَت"
        and not item["label"].startswith("كما وردَت؛")
    ]
    raw_specs = MANUAL_SPECS.get(index, [])
    specs = raw_specs if branch_lexicon["selected"] else []
    rejected_specs = raw_specs if not branch_lexicon["selected"] else []
    selected_roots = {spec["root"] for spec in specs}
    if len(selected_roots) != len(specs):
        raise AssertionError(f"duplicate manual root in card {index}")
    review, dialect_additions = current_fan(word, language, selected_roots)
    by_root = {item["root"]: item for item in review}
    ready_items = [
        item for item in review if item["sound"] and item["event_tier"]
    ]
    if ready_items and root_senses is None:
        raise AssertionError(
            f"Arabic root senses must be scanned before an orbit verdict: {index}"
        )
    ready_root_senses: list[dict[str, Any]] = []
    for item in ready_items:
        evidence = (root_senses or {}).get(item["root"])
        if evidence is None:
            raise AssertionError(
                f"Arabic root sense scan omitted {index}:{item['root']}"
            )
        if (
            evidence.get("max_chars") != 0
            or evidence.get("truncated")
            or not evidence.get("all_witnesses_reviewed")
        ):
            raise AssertionError(
                f"Arabic root witnesses were not read in full: {index}:{item['root']}"
            )
        ready_root_senses.append(evidence)
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
        f"- معنى اللقطة التاريخية السابقة: {branch_line(block)}؛ ونقل الباحث المسمى، خارج قاموس الفرع: {source_meanings}.",
        f"- قاموس الفرع: `{branch_lexicon['source']}`؛ الطريق: {branch_lexicon['lookup_path']}؛ القائمة كاملة: "
        + (" | ".join(branch_entry_text(entry) for entry in branch_lexicon["entries"]) or "لا مدخل") + ".",
        f"- اختيار معنى الفرع: "
        + (branch_entry_text(branch_lexicon["selected"]) if branch_lexicon["selected"] else "لا شيء")
        + f"؛ {branch_lexicon['selection_note']}",
        f"- الخطوة صفر: الصورة `{clean(word)}`؛ الرسم الصريح `{fan_script}`؛ الهياكل الحالية {render_skeleton_variants(fan_skeletons)}.",
        f"- باب الساق اللاتيني الموسوم: {('؛ '.join(stem_labels) + '؛ بقيت الصورة كما وردت في أول العرض حيث صلحت.') if stem_labels else 'لم يضف هيكلًا بديلًا لهذه الصورة.'}",
        f"- المروحة الكاملة من `fan_any_script.fan` مرتبة بـ`fan_any_script.rank`: {('، '.join(render_candidate(item) for item in review) or 'لا مرشح قابل للتوليد')}. الوزن ترتيب لا حكم؛ د=درجة الحدث؛ م× يعني أن المدار فُحص ولم يقنع.",
        f"- فحص `fan_with_dialect`: أضاف {dialect_additions} صورة موسومة بعد الفصيح ولم يحذف الفصيح.",
    ]
    if stem_labels:
        lines.append(
            "- تنبيه التأريخ: التعرية لا تجعل الصياغة الإنجليزية المشتقة حديثًا قديمة؛ "
            "المقابلة، إن ثبتت أرجلها، تكون مع عنصرها اللاتيني الباقي لا مع الصياغة الحديثة نفسها."
        )
    if ready_root_senses:
        lines.append(
            "- شواهد الجذور العربية قبل حكم المدار: "
            + "؛ ".join(root_sense_line(item) for item in ready_root_senses) + "."
        )
    else:
        lines.append("- شواهد الجذور العربية: لم يبلغ مرشحٌ رجلَي الصوت والحدث ليبدأ فحص المدار.")
    if rejected_specs:
        lines.append(
            "- أثر قاموس الفرع في المقترحات القديمة: لم تُصدر المقترحات "
            + "، ".join(f"`{spec['root']}`" for spec in rejected_specs)
            + "؛ مدخل قاموس الفرع المنتخب غائب، فلا يكتمل معنى الفرع بنقل الباحث وحده."
        )

    positives: list[dict[str, Any]] = []
    for spec in specs:
        root = spec["root"]
        orbit = clean(MANUAL_ORBIT_OVERRIDES.get((index, root), spec.get("orbit")))
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
        root_evidence = (root_senses or {}).get(root)
        if not root_evidence or not root_evidence.get("judgment_ready"):
            raise AssertionError(f"manual positive lacks full Arabic root senses: {index}:{root}")
        witness_source = MANUAL_ROOT_WITNESS_SOURCE.get((index, root))
        witness_quote = clean(spec.get("witness_quote"))
        witness = next((
            source for source in root_evidence.get("witnesses", [])
            if source.get("source_id") == witness_source
            and (
                not witness_quote
                or witness_quote in clean(source.get("definition"))
            )
        ), None)
        if witness is None:
            raise AssertionError(f"manual Arabic witness missing: {index}:{root}")
        quoted_text = witness_quote or clean(witness["definition"])
        witness_label = str(witness["source_label"])
        if witness_quote and (
            witness_quote not in orbit or witness_label not in orbit
        ):
            raise AssertionError(
                f"orbit must quote the Arabic witness and name its lexicon: {index}:{root}"
            )
        cited_witness = {
            "root": root,
            "quote": quoted_text,
            "source_id": witness.get("source_id"),
            "source_label": witness_label,
            "source_record": witness.get("source"),
            "url": witness.get("url"),
            "definition_truncated": bool(witness.get("definition_truncated")),
            "max_chars": 0,
        }
        closure = closure_for(root)
        lines.extend([
            f"- معنى الفرع المنتخب بلا رتوش: {branch_entry_text(branch_lexicon['selected'])}.",
            f"- المقابل المنتخب: `{root}`؛ وزن العرض {candidate['weight']:.6f}.",
            f"- مسار الصوت المسمى: {candidate['sound_route']}.",
            f"- ما فُتش في الشبكة بالحرفين وباسمي اللسان: {'؛ '.join(candidate['sound_searches'])}.",
            f"- الحدث من السجل المجمّد كما هو (درجة {candidate['event_tier']}، {candidate['event_tier_ar']}): «{candidate['event_text']}» [{candidate['event_source']}]."
            + (f" {candidate['event_note']}." if candidate["event_note"] else ""),
            f"- شاهد الجذر العربي المقروء بلا قطع: «{quoted_text}» [{witness_label}]"
            + (f"؛ {witness['url']}." if witness.get("url") else "."),
            f"- المدار المكتوب باليد: {orbit}",
            f"- نتيجة الأرجل الثلاث للمقابل `{root}`: **{closure} (استكشاف)**.",
        ])
        positives.append({
            "root": root,
            "closure": closure,
            "orbit": orbit,
            "branch_dictionary": branch_lexicon["source"],
            "branch_dictionary_path": branch_lexicon["lookup_path"],
            "branch_dictionary_entry": branch_lexicon["selected"],
            "arabic_root_witness": cited_witness,
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
        if ready and not branch_lexicon["selected"]:
            reason_key = "BRANCH-LEXICON-NOT-ESTABLISHED"
            required = "لم ينتخب الكاتب مدخلًا من قائمة قاموس الفرع يوافق سياق الصورة؛ لا يكفي نقل الباحث"
            search_line = "الصوت والحدث مكتملان، لكن رجل معنى الفرع من قاموسه لم تثبت؛ عُرضت القائمة كاملة أعلاه."
        elif ready:
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
        "fan_script": fan_script,
        "fan_skeletons": fan_skeletons,
        "branch_lexicon": branch_lexicon,
        "arabic_root_sense_review": {
            "tool": "scripts/search_arabic_root_senses.py",
            "max_chars": 0,
            "truncated": False,
            "all_witnesses_reviewed": True,
            "roots": [item["root"] for item in ready_root_senses],
            "witness_records_read": sum(
                item["match_count"] for item in ready_root_senses
            ),
        },
        "rejected_manual_specs": rejected_specs,
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
    fan_empty_rereview: dict[str, Any] | None = None,
    orbit_sense_rereview: dict[str, Any] | None = None,
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
        "BRANCH-LEXICON-NOT-ESTABLISHED": "لم يثبت مدخل سياقي من قاموس الفرع بعد عرض قائمته كاملة",
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
    if fan_empty_rereview:
        transitions = fan_empty_rereview["after"]
        lines.extend([
            "",
            "## تصحيح مروحة الساق اللاتيني",
            "",
            f"- أُعيدت {fan_empty_rereview['targeted_cards']} بطاقة من صفوف `FAN-EMPTY` الأصلية وحدها؛ لم تُعَد بطاقة من خارج تلك المجموعة.",
            f"- صار لـ{fan_empty_rereview['cards_gained_fan']} بطاقة منها مرشحون بعد التعرية الموسومة، وبقيت {transitions.get('FAN-EMPTY', 0)} بلا مرشح.",
            f"- دخل {fan_empty_rereview['new_positive_cards']} موجب جديد من هذه الإعادة؛ وُزعت بقية النتائج: "
            + "، ".join(f"`{key}`={value}" for key, value in transitions.items()) + ".",
            "- كل بطاقة اتسعت مروحتها تسمي الزائدة المنزوعة، وتصرح بأن الصياغة الإنجليزية الحديثة ليست هي المدعى قدمها؛ المقابلة مع العنصر اللاتيني وحده.",
        ])
    if orbit_sense_rereview:
        transitions = orbit_sense_rereview["after"]
        lines.extend([
            "",
            "## إعادة المدار بالشواهد العربية",
            "",
            f"- أُعيدت بطاقات `ORBIT-NOT-CONVINCING` الأصلية وعددها {orbit_sense_rereview['targeted_cards']} في هذه الدفعة.",
            f"- شُغّل `search_arabic_root_senses.py` على {orbit_sense_rereview['unique_roots_scanned']} جذرًا مكتمل الصوت والحدث، دائمًا بـ`--max-chars 0`؛ قُرئ {orbit_sense_rereview['witness_records_read']} شاهدًا بلا قطع.",
            f"- تحوّل من هذه البطاقات إلى حكم موجب: {orbit_sense_rereview['converted_cards']}؛ وبقي `ORBIT-NOT-CONVINCING`: {transitions.get('ORBIT-NOT-CONVINCING', 0)}.",
            "- توزيع البقية بعد استيفاء طرفَي الفرع والجذر العربي: "
            + "، ".join(f"`{key}`={value}" for key, value in transitions.items()) + ".",
            "- كل موجب جديد يورد نص الشاهد العربي واسم معجمه ورابط مادته داخل البطاقة؛ الشاهد يسند المدار المكتوب باليد ولا يقوم مقامه.",
        ])
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


def replace_rereview_card(text: str, index: int, card_lines: list[str]) -> str:
    marker = f"<!-- DEAD-GATE-REREVIEW:KHASHIM-IE:{index} -->"
    marker_at = text.find(marker)
    if marker_at < 0 or text.find(marker, marker_at + len(marker)) >= 0:
        raise AssertionError(f"expected one rereview marker for card {index}")
    heading_at = text.rfind("\n### ", 0, marker_at)
    start = heading_at + 1 if heading_at >= 0 else 0
    following = [
        value + 1 for value in (
            text.find("\n### ", marker_at + len(marker)),
            text.find("\n<!-- DEAD-GATE-REREVIEW-BATCH-", marker_at + len(marker)),
        ) if value >= 0
    ]
    if not following:
        raise AssertionError(f"could not find the end of rereview card {index}")
    finish = min(following)
    replacement = "\n".join(card_lines).rstrip() + "\n\n"
    return text[:start] + replacement + text[finish:]


def redo_fan_empty(batch: int) -> int:
    audit_path = ROOT / "05-audits" / f"{DATE}-dead-gate-rereview-batch-{batch:03d}.md"
    manifest_path = ROOT / "data" / f"dead-gate-rereview-batch-{batch:03d}.json"
    if not audit_path.exists() or not manifest_path.exists():
        raise AssertionError(f"batch {batch} must exist before its FAN-EMPTY rereview")

    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    if payload.get("batch") != batch:
        raise AssertionError(f"manifest batch mismatch in {manifest_path}")
    if batch in ORIGINAL_FAN_EMPTY_COUNTS:
        target_positions = [
            position for position, row in enumerate(payload["rows"])
            if row.get("fan_skeletons")
            and not row["fan_skeletons"][0].get("usable")
            and row.get("original_index") not in set(ORIGINAL_ORBIT_TARGETS[batch])
        ]
        expected = ORIGINAL_FAN_EMPTY_COUNTS[batch]
        if len(target_positions) != expected:
            raise AssertionError(
                f"batch {batch} expected {expected} original FAN-EMPTY rows, "
                f"found {len(target_positions)}"
            )
    else:
        target_positions = [
            position for position, row in enumerate(payload["rows"])
            if row.get("open_reason") == "FAN-EMPTY"
        ]
    if not target_positions:
        raise AssertionError(f"batch {batch} has no current FAN-EMPTY rows to rereview")

    blocks, files = original_blocks()
    forms = form_index()
    raw_rows = source_rows()
    target_indices = [payload["rows"][position]["original_index"] for position in target_positions]
    root_senses = root_senses_for_indices(target_indices, blocks, files, forms)
    before_untouched = {
        position: json.dumps(row, ensure_ascii=False, sort_keys=True)
        for position, row in enumerate(payload["rows"])
        if position not in target_positions
    }
    reading_texts: dict[str, str] = {}
    transitions: Counter[str] = Counter()
    cards_gained_fan = 0
    new_positive_cards = 0

    for position in target_positions:
        old = payload["rows"][position]
        index = old["original_index"]
        language = files[index]
        if old["language"] != language or old["form"] != forms[index]["form"]:
            raise AssertionError(f"source identity drift in dead-gate card {index}")
        card_lines, row, _ = build_card(
            index, language, blocks[index], forms[index], raw_rows, root_senses
        )
        if row["fan_candidates"]:
            cards_gained_fan += 1
        if row["positives"]:
            new_positive_cards += 1
            transition = "+".join(dict.fromkeys(
                positive["closure"] for positive in row["positives"]
            ))
        else:
            transition = row["open_reason"]
        transitions[transition] += 1
        payload["rows"][position] = row

        if language not in reading_texts:
            path = READINGS / f"{language}.md"
            reading_texts[language] = path.read_text(encoding="utf-8")
        reading_texts[language] = replace_rereview_card(
            reading_texts[language], index, card_lines
        )

    for position, serialized in before_untouched.items():
        current = json.dumps(payload["rows"][position], ensure_ascii=False, sort_keys=True)
        if current != serialized:
            raise AssertionError(f"non-FAN-EMPTY row {position} changed in batch {batch}")

    reason_counts = Counter(
        row["open_reason"] for row in payload["rows"] if not row["positives"]
    )
    summary = {
        "date": DATE,
        "targeted_cards": len(target_positions),
        "cards_gained_fan": cards_gained_fan,
        "new_positive_cards": new_positive_cards,
        "before": {"FAN-EMPTY": len(target_positions)},
        "after": dict(transitions),
        "unique_arabic_roots_scanned": len(root_senses),
        "arabic_witness_records_read": sum(
            item["match_count"] for item in root_senses.values()
        ),
        "max_chars": 0,
        "policy": "only rows originally classified FAN-EMPTY were rebuilt",
    }
    root_catalog = dict(payload.get("arabic_root_sense_catalog") or {})
    root_catalog.update({
        root: public_root_sense(item) for root, item in root_senses.items()
    })
    payload.update({
        "positive_cards": sum(bool(row["positives"]) for row in payload["rows"]),
        "positive_traces": sum(len(row["positives"]) for row in payload["rows"]),
        "open_cards": sum(not row["positives"] for row in payload["rows"]),
        "open_reasons": dict(reason_counts),
        "arabic_root_sense_catalog": root_catalog,
        "fan_empty_rereview": summary,
    })

    for language, text in reading_texts.items():
        (READINGS / f"{language}.md").write_text(
            text, encoding="utf-8", newline="\n"
        )
    manifest_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    audit_path.write_text(
        audit_text(
            batch,
            payload["rows"],
            payload["gate_mentions"],
            reason_counts,
            summary,
            payload.get("orbit_sense_rereview"),
        ),
        encoding="utf-8",
        newline="\n",
    )
    print(json.dumps(summary, ensure_ascii=False))
    return 0


def redo_orbit_not_convincing(batch: int) -> int:
    audit_path = ROOT / "05-audits" / f"{DATE}-dead-gate-rereview-batch-{batch:03d}.md"
    manifest_path = ROOT / "data" / f"dead-gate-rereview-batch-{batch:03d}.json"
    if batch not in ORIGINAL_ORBIT_TARGETS:
        raise AssertionError("the requested ORBIT rereview is limited to batches 001-003")
    if not audit_path.exists() or not manifest_path.exists():
        raise AssertionError(f"batch {batch} must exist before its ORBIT rereview")

    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    if payload.get("batch") != batch:
        raise AssertionError(f"manifest batch mismatch in {manifest_path}")
    wanted = set(ORIGINAL_ORBIT_TARGETS[batch])
    target_positions = [
        position for position, row in enumerate(payload["rows"])
        if row.get("original_index") in wanted
    ]
    found = {payload["rows"][position]["original_index"] for position in target_positions}
    if found != wanted or len(target_positions) != len(wanted):
        raise AssertionError(
            f"batch {batch} ORBIT inventory drift: wanted {len(wanted)}, found {len(found)}"
        )

    blocks, files = original_blocks()
    forms = form_index()
    raw_rows = source_rows()
    target_indices = [payload["rows"][position]["original_index"] for position in target_positions]
    root_senses = root_senses_for_indices(target_indices, blocks, files, forms)
    before_untouched = {
        position: json.dumps(row, ensure_ascii=False, sort_keys=True)
        for position, row in enumerate(payload["rows"])
        if position not in target_positions
    }
    reading_texts: dict[str, str] = {}
    transitions: Counter[str] = Counter()
    converted_cards = 0

    for position in target_positions:
        old = payload["rows"][position]
        index = old["original_index"]
        language = files[index]
        if old["language"] != language or old["form"] != forms[index]["form"]:
            raise AssertionError(f"source identity drift in dead-gate card {index}")
        card_lines, row, _ = build_card(
            index, language, blocks[index], forms[index], raw_rows, root_senses
        )
        if row["positives"]:
            converted_cards += 1
            transition = "+".join(dict.fromkeys(
                positive["closure"] for positive in row["positives"]
            ))
        else:
            transition = row["open_reason"]
        transitions[transition] += 1
        payload["rows"][position] = row

        if language not in reading_texts:
            path = READINGS / f"{language}.md"
            reading_texts[language] = path.read_text(encoding="utf-8")
        reading_texts[language] = replace_rereview_card(
            reading_texts[language], index, card_lines
        )

    for position, serialized in before_untouched.items():
        current = json.dumps(payload["rows"][position], ensure_ascii=False, sort_keys=True)
        if current != serialized:
            raise AssertionError(f"non-ORBIT row {position} changed in batch {batch}")

    reason_counts = Counter(
        row["open_reason"] for row in payload["rows"] if not row["positives"]
    )
    summary = {
        "date": DATE,
        "targeted_cards": len(target_positions),
        "tool": "scripts/search_arabic_root_senses.py",
        "max_chars": 0,
        "unique_roots_scanned": len(root_senses),
        "roots_with_witnesses": sum(
            bool(item["match_count"]) for item in root_senses.values()
        ),
        "witness_records_read": sum(
            item["match_count"] for item in root_senses.values()
        ),
        "converted_cards": converted_cards,
        "before": {"ORBIT-NOT-CONVINCING": len(target_positions)},
        "after": dict(transitions),
        "policy": (
            "every sound-and-event-ready Arabic root was scanned without clipping; "
            "a positive requires a selected branch entry, an exact named lexicon quote, "
            "and a hand-written orbit"
        ),
    }
    root_catalog = dict(payload.get("arabic_root_sense_catalog") or {})
    root_catalog.update({
        root: public_root_sense(item) for root, item in root_senses.items()
    })
    payload.update({
        "positive_cards": sum(bool(row["positives"]) for row in payload["rows"]),
        "positive_traces": sum(len(row["positives"]) for row in payload["rows"]),
        "open_cards": sum(not row["positives"] for row in payload["rows"]),
        "open_reasons": dict(reason_counts),
        "arabic_root_sense_catalog": root_catalog,
        "orbit_sense_rereview": summary,
    })

    for language, content in reading_texts.items():
        (READINGS / f"{language}.md").write_text(
            content, encoding="utf-8", newline="\n"
        )
    manifest_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    audit_path.write_text(
        audit_text(
            batch,
            payload["rows"],
            payload["gate_mentions"],
            reason_counts,
            payload.get("fan_empty_rereview"),
            summary,
        ),
        encoding="utf-8",
        newline="\n",
    )
    print(json.dumps(summary, ensure_ascii=False))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch", type=int, required=True)
    rerun = parser.add_mutually_exclusive_group()
    rerun.add_argument("--redo-fan-empty", action="store_true")
    rerun.add_argument("--redo-orbit-not-convincing", action="store_true")
    parser.add_argument("--rebuild-existing", action="store_true")
    args = parser.parse_args()
    if not 1 <= args.batch <= 7:
        raise SystemExit("batch must be between 1 and 7")
    if args.redo_fan_empty:
        return redo_fan_empty(args.batch)
    if args.redo_orbit_not_convincing:
        return redo_orbit_not_convincing(args.batch)

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
    if (audit.exists() or manifest.exists()) and not args.rebuild_existing:
        raise AssertionError(f"batch {args.batch} output already exists")

    if args.rebuild_existing:
        start_marker = f"<!-- {marker}:START -->"
        end_marker = f"<!-- {marker}:END -->"
        for language in K.TARGET_LANGUAGES:
            path = READINGS / f"{language}.md"
            text = path.read_text(encoding="utf-8")
            cleaned, count = re.subn(
                rf"\n?{re.escape(start_marker)}.*?{re.escape(end_marker)}\n?",
                "\n",
                text,
                count=1,
                flags=re.DOTALL,
            )
            if count:
                path.write_text(cleaned.rstrip() + "\n", encoding="utf-8", newline="\n")

    by_language: dict[str, list[str]] = defaultdict(list)
    report_rows: list[dict[str, Any]] = []
    reasons: Counter[str] = Counter()
    gate_mentions = 0
    root_senses = root_senses_for_indices(window, blocks, files, forms)
    for index in window:
        language = files[index]
        card_lines, row, reason = build_card(
            index, language, blocks[index], forms[index], raw_rows, root_senses
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
        "arabic_root_sense_catalog": {
            root: public_root_sense(item) for root, item in root_senses.items()
        },
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
