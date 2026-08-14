# -*- coding: utf-8 -*-
"""أعد حصاد مخزن المصرية والقبطية في دفعات إلحاقية من 150 صفا.

المروحة والصوت استرجاع آلي، والحدث لا يؤخذ إلا من ``FE.resolve``. معنى الفرع
لا يؤخذ من عمود خشيم المقارن بل من AED: تعرض البطاقة كل الإصابات وتسمّي المدخل
الذي اختاره القارئ في سياق الصف. أما المدار فلا يولده هذا الملف: لا يصدر موجب
إلا بمفتاح موجود صراحة في ``MANUAL_NEW``.
"""
from __future__ import annotations

import argparse
import glob
import json
import pathlib
import sys
from collections import Counter

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import build_egyptian_gods_maqar_cards as OLD  # noqa: E402
import build_aed_index as AED  # noqa: E402
import frozen_event as FE  # noqa: E402
import search_arabic_root_senses as ARS  # noqa: E402

BATCH_SIZE = 150
READING = ROOT / "04-cross-linguistic" / "readings" / "egyptian.md"
MARKER = "EGYPTIAN-COPTIC-STORE-REHARVEST"


# اختيارات سياقية يدوية من جميع إصابات AED. القيمة lemma id، لا رتبة الإصابة.
# ما أصابه الفهرس ولم يرد هنا بقي بلا اختيار، ومنه Amentet: إصابته `mnt.t`
# «diorite» لا توافق الغرب أو أرض الأموات، فلا تؤخذ لمجرد أنها الأولى.
AED_SELECTIONS: dict[int, str] = {
    1: "69590", 2: "69590",                    # mn, remain/endure/established
    7: "79000", 8: "79000", 9: "79000",      # n.t, Red Crown
    10: "79010", 11: "79010", 12: "79010",   # Nj.t, Neith
    22: "149130", 23: "149130", 24: "149130", # sṯ.tjw, Asiatics
    28: "96120", 29: "96120", 30: "96120",      # rs.w, south-wind
    55: "94200", 56: "94200",                  # rm.yt, tears
    57: "94190", 58: "94190",                  # Rm.y, Weeper (sun god)
    64: "96011", 65: "96011", 66: "96011",    # rs.j, south
    67: "96070", 68: "96070", 69: "96070",    # rs.jw, southerners
    70: "96590", 71: "96590", 72: "96590", 73: "96590",  # Retjenu
    90: "175490", 91: "175490", 92: "175490", 93: "175490",  # Libyan
    110: "73860", 111: "73860",                # north wind
    112: "73580", 113: "73580",                # northerners
    114: "73940", 115: "73940",                # Lower Egypt
    145: "26140", 146: "26140",                # right side; west; land dead
    187: "93960", 188: "93960", 189: "93960", # Rbw, region of Libya
    209: "99330", 210: "99330",                # Hs, Libyan tribe
    211: "76410", 212: "76410",                # Mšwš, Libyan tribe
    269: "82090", 270: "82090", 271: "82090", # nb.t-pr, mistress of house
    272: "87870", 273: "87870", 274: "87870", # ns.t, seat; throne
    288: "110310", 289: "110310", 290: "110310", 291: "110310", # Hekat
    305: "32820", 306: "32820", 307: "32820", # jtj, father
    314: "162200", 315: "162200", 316: "162200", # qs, bone
    320: "23290", 321: "23290", 322: "23290", # jb, heart
    337: "74750", 338: "74750",               # ms, child
    368: "76230",                              # msḏr, ear
    370: "138920", 371: "138920",             # sr, nobleman; official
    380: "91900",                              # r, preposition
    381: "78870", 382: "78870",               # n, preposition
    405: "28250", 406: "28250", 407: "28250", 408: "28250",
    409: "28250", 410: "28250",               # jr.t, eye
    411: "46750", 412: "46750", 413: "46750", 414: "46750",
    415: "46750", 416: "46750",               # wnm.t, right eye
    423: "34070", 424: "34070", 425: "34070", 426: "34070",
    427: "34070",                              # jdn, ear
    438: "38930", 439: "38930", 440: "38930", 441: "38930",
    442: "38930",                              # ꜥnḫ.wj, pair of ears
    449: "124510", 450: "124510",             # ẖrd, to be a child
    451: "124510", 452: "124510", 453: "124510", 454: "124510", # ẖrd, child
    455: "74750", 456: "74750", 457: "74750", 458: "74750",
    459: "74750", 460: "74750",               # ms, child
    461: "156650", 462: "156650", 463: "156650", 464: "156650",
    465: "156650", 466: "156650",             # šrj, child; son; lad
    473: "150150", 474: "150150", 475: "150150", 476: "150150",
    477: "150150", 478: "150150", 479: "150150", 480: "150150",
    481: "150150", 482: "150150",             # sḏ.tj, child; foster child
    483: "87260", 484: "87260", 485: "87260", 486: "87260",
    487: "87260", 488: "87260", 489: "87260", 490: "87260",
    491: "87260", 492: "87260",               # nḫn, to become a child
    513: "52730", 514: "52730", 515: "52730", 516: "52730",
    517: "52730", 518: "52730", 519: "52730", 520: "52730",
    521: "52730", 522: "52730",               # wḏḥ, weaned child
    523: "103060", 524: "103060", 525: "103060", 526: "103060",
    527: "103060", 528: "103060", 529: "103060", 530: "103060",
    531: "103060", 532: "103060",             # ḥwn, childhood; youth
    604: "167210",                             # gmi̯, to find; discover
    606: "89630",                              # ngi̯, to break open
    608: "62180",                              # psi̯, cook; bake; heat
    610: "45640",                              # wpi̯, divide; open; judge
    617: "130150",                             # swn, recognize
    621: "90690", 622: "90690",              # ndj, to fell
    625: "72470",                              # mri̯, love; wish
    626: "28800",                              # wdf, delay
    628: "139770",                             # srq, open; make inhale
    631: "131940",                             # sbḫ, enclose with the arms
    632: "64320",                              # fdq, sever; hack into pieces
    638: "111230",                             # ḥtp, content; set of sun
    640: "46660", 641: "46660",              # wnf, glad; rejoice
    642: "49530", 643: "49530", 644: "49530", 645: "49530", # idleness
    653: "32240",                              # jqr, excellent; trustworthy
    659: "138670",                             # snṯr, incense
    685: "109110",                             # ḥrr.t, flower
    687: "85020", 688: "85020",              # nr, herdsman; protector
    692: "179910", 693: "179910", 694: "179910", # dns, heavy; burdensome
    700: "55150",                              # bw.t, abomination
    759: "186250", 760: "186250", 761: "186250", # ḏdf.t, snake; worm
    762: "92560", 763: "92560", 764: "92560", 765: "92560",
    766: "92560",                              # rʾ, mouth
    777: "94180", 778: "94180", 779: "94180", 780: "94180",
    781: "94180",                              # rmi̯, to weep
    782: "94220", 783: "94220", 784: "94220", 785: "94220",
    786: "94220",                              # rm.w, weeping
    836: "180220", 837: "180220", 838: "180220", 839: "180220",
    840: "180220", 841: "180220", 842: "180220", 843: "180220",
    844: "180220",                             # drp, offer; feed; present
    845: "180250", 846: "180250", 847: "180250", 848: "180250",
    849: "180250", 850: "180250", 851: "180250", 852: "180250",
    853: "180250",                             # drf, writing; script
    864: "74750", 865: "74750", 866: "74750", 867: "74750",
    868: "74750", 869: "74750", 870: "74750", 871: "74750",
    872: "74750", 873: "74750",               # ms, child
    880: "74750", 881: "74750", 882: "74750", 883: "74750",
    884: "74750", 885: "74750",               # ms, child
    891: "69590", 892: "69590", 893: "69590", 894: "69590", # mn, remain
}

BASELINE_POSITIVE_ORDINALS = {1, 2, 41}


# مدارات هذه الجولة مكتوبة يدويا، واحدا واحدا. رقم المفتاح هو رتبة الصف في
# الجرد الثابت، والمرشح لا يحتكر المروحة بسبب وجوده هنا.
MANUAL_NEW: dict[tuple[int, str], tuple[str, str]] = {
    (1, "من"): (
        "NUCLEUS-TRACE",
        "مدار الحالة: `to remain; to endure; to be established` بقاء ودوام "
        "وثبوت؛ وهي تقع مباشرة في وجه الثبات من حدث النواة `من`.",
    ),
    (2, "من"): (
        "NUCLEUS-TRACE",
        "مدار الحالة: `to remain; to endure; to be established` بقاء ودوام "
        "وثبوت؛ وهي تقع مباشرة في وجه الثبات من حدث النواة `من`.",
    ),
    (7, "نتت"): (
        "ROOT-TRACE",
        "مدار الهيئة: `Red Crown` تاج ناتئ محدد على ظاهر الرأس؛ فالنتوء الدقيق "
        "الحاد في ظاهر الشيء هو هيئة التاج التي يقرأها حدث `نتت`.",
    ),
    (8, "نتت"): (
        "ROOT-TRACE",
        "مدار الهيئة: `Red Crown` تاج ناتئ محدد على ظاهر الرأس؛ فالنتوء الدقيق "
        "الحاد في ظاهر الشيء هو هيئة التاج التي يقرأها حدث `نتت`.",
    ),
    (9, "نتت"): (
        "ROOT-TRACE",
        "مدار الهيئة: `Red Crown` تاج ناتئ محدد على ظاهر الرأس؛ فالنتوء الدقيق "
        "الحاد في ظاهر الشيء هو هيئة التاج التي يقرأها حدث `نتت`.",
    ),
    (55, "رميت"): (
        "NUCLEUS-TRACE",
        "مدار المادة: `tears` سائل رخو يتجمع في أثناء العين عند تحول حاد من "
        "البكاء ثم ينساب؛ وهذا هو وجه التجمع الرخو والتحول في حدث `رميت`.",
    ),
    (56, "رميت"): (
        "NUCLEUS-TRACE",
        "مدار المادة: `tears` سائل رخو يتجمع في أثناء العين عند تحول حاد من "
        "البكاء ثم ينساب؛ وهذا هو وجه التجمع الرخو والتحول في حدث `رميت`.",
    ),
    (145, "يمن"): (
        "ROOT-TRACE",
        "شاهد عائلة الجذر من تاج العروس لمرتضى الزبيدي: «اليَمِينُ: ضِدُّ "
        "اليَسارِ»، ثم «أَيْضاً: (القُوَّةُ) والقُدْرَةُ». ومدارنا: معنى AED "
        "`right side; west; land of the dead` يثبت جانب اليمين نفسه، واليمين "
        "هي جهة اليد التي تكون أداة القوة والعون في العمل؛ فيتصل معنى الفرع "
        "مباشرة بحدث `يمن` «أداة قوة وعون أساسية على كل عمل».",
    ),
    (146, "يمن"): (
        "ROOT-TRACE",
        "شاهد عائلة الجذر من تاج العروس لمرتضى الزبيدي: «اليَمِينُ: ضِدُّ "
        "اليَسارِ»، ثم «أَيْضاً: (القُوَّةُ) والقُدْرَةُ». ومدارنا: معنى AED "
        "`right side; west; land of the dead` يثبت جانب اليمين نفسه، واليمين "
        "هي جهة اليد التي تكون أداة القوة والعون في العمل؛ فيتصل معنى الفرع "
        "مباشرة بحدث `يمن` «أداة قوة وعون أساسية على كل عمل».",
    ),
    (314, "قسو"): (
        "NUCLEUS-TRACE",
        "مدار الصفة الملازمة للمادة: `bone` مادة صلبة في داخل البدن، وحدث "
        "`قسو` صلابة الأثناء مع حدة أو جفاف؛ والحكم مقصور على العظم.",
    ),
    (315, "قسو"): (
        "NUCLEUS-TRACE",
        "مدار الصفة الملازمة للمادة: `bone` مادة صلبة في داخل البدن، وحدث "
        "`قسو` صلابة الأثناء مع حدة أو جفاف؛ والحكم مقصور على العظم.",
    ),
    (316, "قسو"): (
        "NUCLEUS-TRACE",
        "مدار الصفة الملازمة للمادة: `bone` مادة صلبة في داخل البدن، وحدث "
        "`قسو` صلابة الأثناء مع حدة أو جفاف؛ والحكم مقصور على العظم.",
    ),
    (449, "خرد"): (
        "ROOT-TRACE",
        "مدار الحالة العمرية: `to be a child` بقاء على أصل الفطرة قبل "
        "الاستعمال والتجربة؛ وهذا هو حدث `خرد` المجمّد.",
    ),
    (450, "خرد"): (
        "ROOT-TRACE",
        "مدار الحالة العمرية: `to be a child` بقاء على أصل الفطرة قبل "
        "الاستعمال والتجربة؛ وهذا هو حدث `خرد` المجمّد.",
    ),
    (451, "خرد"): (
        "ROOT-TRACE",
        "مدار الحالة العمرية: `to be a child` بقاء على أصل الفطرة قبل "
        "الاستعمال والتجربة؛ وهذا هو حدث `خرد` المجمّد.",
    ),
    (452, "خرد"): (
        "ROOT-TRACE",
        "مدار الحالة العمرية: `to be a child` بقاء على أصل الفطرة قبل "
        "الاستعمال والتجربة؛ وهذا هو حدث `خرد` المجمّد.",
    ),
    (453, "خرد"): (
        "ROOT-TRACE",
        "مدار الحالة العمرية: `to be a child` بقاء على أصل الفطرة قبل "
        "الاستعمال والتجربة؛ وهذا هو حدث `خرد` المجمّد.",
    ),
    (454, "خرد"): (
        "ROOT-TRACE",
        "مدار الحالة العمرية: `to be a child` بقاء على أصل الفطرة قبل "
        "الاستعمال والتجربة؛ وهذا هو حدث `خرد` المجمّد.",
    ),
    (632, "فضق"): (
        "ROOT-TRACE",
        "مدار الفعل المادي: `to sever; to hack into pieces` قطع يفرّق الجسم "
        "بضربات قوية إلى أجزاء، والحدث المجمّد لـ`فضق` هو «الكسر والتفريق "
        "بقوة وغلظ»؛ فالمعنيان يقعان على التفريق القسري نفسه.",
    ),
    (782, "رمو"): (
        "NUCLEUS-TRACE",
        "مدار الأثر الجسدي: `weeping` بكاء يظهر بتجمع سائل رخو في أثناء "
        "العين عند تحول حاد ثم خروجه؛ وهذا هو وجه التجمع الرخو والتحول في "
        "حدث `رمو` المجمّد.",
    ),
    (783, "رمو"): (
        "NUCLEUS-TRACE",
        "مدار الأثر الجسدي: `weeping` بكاء يظهر بتجمع سائل رخو في أثناء "
        "العين عند تحول حاد ثم خروجه؛ وهذا هو وجه التجمع الرخو والتحول في "
        "حدث `رمو` المجمّد.",
    ),
    (784, "رمو"): (
        "NUCLEUS-TRACE",
        "مدار الأثر الجسدي: `weeping` بكاء يظهر بتجمع سائل رخو في أثناء "
        "العين عند تحول حاد ثم خروجه؛ وهذا هو وجه التجمع الرخو والتحول في "
        "حدث `رمو` المجمّد.",
    ),
    (785, "رمو"): (
        "NUCLEUS-TRACE",
        "مدار الأثر الجسدي: `weeping` بكاء يظهر بتجمع سائل رخو في أثناء "
        "العين عند تحول حاد ثم خروجه؛ وهذا هو وجه التجمع الرخو والتحول في "
        "حدث `رمو` المجمّد.",
    ),
    (786, "رمو"): (
        "NUCLEUS-TRACE",
        "مدار الأثر الجسدي: `weeping` بكاء يظهر بتجمع سائل رخو في أثناء "
        "العين عند تحول حاد ثم خروجه؛ وهذا هو وجه التجمع الرخو والتحول في "
        "حدث `رمو` المجمّد.",
    ),
    (891, "من"): (
        "NUCLEUS-TRACE",
        "مدار الحالة: `to remain; to endure; to be established` بقاء ودوام "
        "وثبوت؛ وهي تقع مباشرة في وجه الثبات من حدث النواة `من`.",
    ),
    (892, "من"): (
        "NUCLEUS-TRACE",
        "مدار الحالة: `to remain; to endure; to be established` بقاء ودوام "
        "وثبوت؛ وهي تقع مباشرة في وجه الثبات من حدث النواة `من`.",
    ),
    (893, "من"): (
        "NUCLEUS-TRACE",
        "مدار الحالة: `to remain; to endure; to be established` بقاء ودوام "
        "وثبوت؛ وهي تقع مباشرة في وجه الثبات من حدث النواة `من`.",
    ),
    (894, "من"): (
        "NUCLEUS-TRACE",
        "مدار الحالة: `to remain; to endure; to be established` بقاء ودوام "
        "وثبوت؛ وهي تقع مباشرة في وجه الثبات من حدث النواة `من`.",
    ),
}


# يصرح AED في الرسم jmn.t بأن التاء لاحقة التأنيث. صفا 145 و146 وصلا من
# المسح بلا النقطة، فلا يجوز إبقاء التاء في الجذر بعد أن ردها قاموس الفرع.
AED_MORPHOLOGY_OVERRIDES: dict[int, tuple[str, str]] = {
    145: (
        "imn",
        "فُصلت تاء التأنيث الأخيرة بشاهد رسم AED `jmn.t`؛ الخام `i m n t`؛ "
        "لب الجذر `i m n`",
    ),
    146: (
        "imn",
        "فُصلت تاء التأنيث الأخيرة بشاهد رسم AED `jmn.t`؛ الخام `i m n t`؛ "
        "لب الجذر `i m n`",
    ),
}


ROOT_WITNESSES: dict[str, list[dict[str, str]]] = {
    "يمن": [{
        "source": "تاج العروس لمرتضى الزبيدي",
        "quote": "اليَمِينُ: ضِدُّ اليَسارِ",
        "url": "http://arabiclexicon.hawramani.com/%d9%8a%d9%85%d9%86/?book=27",
    }, {
        "source": "تاج العروس لمرتضى الزبيدي",
        "quote": "أَيْضاً: (القُوَّةُ) والقُدْرَةُ",
        "url": "http://arabiclexicon.hawramani.com/%d9%8a%d9%85%d9%86/?book=27",
    }],
}


ROOT_RECHECK_TRANSITIONS = {
    "no_aed_to_orbit": [28, 29, 30],
    "orbit_to_positive": [145, 146],
}


def old_rows() -> dict[int, dict]:
    out: dict[int, dict] = {}
    for name in sorted(glob.glob(str(ROOT / "data" / "egyptian-gods-maqar-batch-*.json"))):
        payload = json.loads(pathlib.Path(name).read_text(encoding="utf-8"))
        for row in payload.get("rows", []):
            out[int(row["ordinal"])] = row
    return out


def report_path(batch: int) -> pathlib.Path:
    return ROOT / "data" / f"egyptian-coptic-store-reharvest-batch-{batch:03d}.json"


def audit_path(batch: int) -> pathlib.Path:
    return ROOT / "05-audits" / f"2026-08-14-egyptian-coptic-store-reharvest-batch-{batch:03d}.md"


def marker(batch: int, side: str) -> str:
    return f"<!-- {MARKER}-BATCH-{batch:03d}:{side} -->"


def aed_payload(ordinal: int, form: str) -> dict:
    hits, how = AED.look(form)
    wanted = AED_SELECTIONS.get(ordinal)
    chosen = next((entry for entry in hits if str(entry.get("id")) == wanted), None)
    if wanted and chosen is None:
        raise RuntimeError(f"اختيار AED غائب في الصف {ordinal}: {wanted}")
    return {
        "path": how,
        "query": form,
        "hits": hits,
        "selected": chosen,
        "selection": (
            "اختير يدويا لموافقته سياق الصف في كتاب خشيم، ويقدم معناه على عمود المقارنة."
            if chosen else (
                "عُرضت الإصابات كلها ولم يوافق شيء منها سياق الصف في كتاب خشيم."
                if hits else "لم يرجع AED مدخلا لهذه الصورة."
            )
        ),
    }


def aed_lines(aed: dict, khashim_sense: str) -> list[str]:
    rendered = (
        "؛ ".join(
            f"`{entry['translit']}` [{entry.get('pos') or 'بلا قسم'}] "
            f"«{entry.get('en') or '[لا ترجمة إنجليزية]'}» "
            f"(AED `{entry.get('id')}`؛ {entry.get('ref') or 'بلا إحالة Wb'})"
            for entry in aed["hits"]
        ) if aed["hits"] else "لا إصابات"
    )
    chosen = aed["selected"]
    chosen_text = (
        f"`{chosen['translit']}` [{chosen.get('pos') or 'بلا قسم'}] "
        f"«{chosen.get('en') or '[لا ترجمة إنجليزية]'}» (AED `{chosen.get('id')}`)"
        if chosen else "لا اختيار"
    )
    return [
        f"- عمود خشيم المقارن محفوظ للخلاف لا بوصفه قاموسا: «{khashim_sense}».",
        f"- بحث AED: {aed['path']}؛ الصورة المستعلم عنها `{aed['query']}`؛ جميع المداخل: {rendered}.",
        f"- مدخل AED المختار: {chosen_text}؛ {aed['selection']}",
    ]


def previous_positive_root(row: dict) -> str:
    return str(row.get("positive_root") or "")


def morphology_for(source: dict, previous: dict, aed: dict) -> tuple[str, str, list[str]]:
    script, _ = OLD.script_for(source)
    stem, stripping, raw = OLD.morphology(source, script)
    override = AED_MORPHOLOGY_OVERRIDES.get(int(previous["ordinal"]))
    if override:
        chosen = aed.get("selected") or {}
        if str(chosen.get("translit")) != "jmn.t":
            raise RuntimeError(
                f"غاب شاهد صرف AED في الصف {previous['ordinal']}: {chosen.get('translit')}"
            )
        stem, stripping = override
    return stem, stripping, raw


def candidate_inventory(source: dict, previous: dict, aed: dict) -> tuple[
    str, str, str, list[str], list[str], str, list[tuple[str, float]]
]:
    script, _ = OLD.script_for(source)
    stem, stripping, raw = morphology_for(source, previous, aed)
    fan = OLD.K.FAN.fan(stem, script, limit=400)
    author = OLD.K.ar_bare(source.get("classical_root") or source.get("arabic_root", ""))
    prior_root = previous_positive_root(previous)
    values = list(fan)
    for extra in (author, prior_root):
        if extra and extra not in values:
            values.append(extra)
    ranked = OLD.K.FAN.rank(stem, values, script, "hebrew")
    return script, stem, stripping, raw, fan, author, ranked


def root_sense_summary(root: str, matches: list[dict]) -> dict:
    fan = ARS.independent_fan(matches)
    return {
        "root": root,
        "command": f"python scripts/search_arabic_root_senses.py {root} --max-chars 0",
        "max_chars": 0,
        "match_count": len(matches),
        "truncated": bool(fan["truncated"]),
        "judgment_ready": bool(fan["judgment_ready"]),
        "selected_sources": [
            {
                "source": item["source_label"],
                "url": item.get("url"),
            }
            for item in fan["selected_sources"]
        ],
    }


def validated_root_witnesses(root: str, matches: list[dict]) -> list[dict[str, str]]:
    witnesses = ROOT_WITNESSES.get(root, [])
    for witness in witnesses:
        if not any(
            item.get("source") == witness["source"]
            and witness["quote"] in str(item.get("definition") or "")
            for item in matches
        ):
            raise RuntimeError(
                f"شاهد عائلة الجذر غير موجود حرفيا: {root} / {witness['source']} / "
                f"{witness['quote']}"
            )
    return witnesses


def candidate_rows(
    source: dict,
    previous: dict,
    aed: dict,
    root_matches: dict[str, list[dict]],
) -> tuple[list[dict], str, int | None]:
    script, stem, _, _, fan, author, ranked = candidate_inventory(source, previous, aed)
    fan_set = set(fan)
    rows: list[dict] = []
    author_position: int | None = None
    for position, (candidate, weight) in enumerate(ranked, 1):
        if candidate == author:
            author_position = position
        sound_ready, sound_rows, sound_misses = OLD.sound_for(stem, candidate, script)
        ev = FE.resolve(candidate)
        manual = MANUAL_NEW.get((int(previous["ordinal"]), candidate))
        if manual and aed["selected"]:
            verdict, orbit, orbit_origin = manual[0], manual[1], "مدار جديد مكتوب باليد"
        else:
            verdict, orbit, orbit_origin = None, None, None
        positive = bool(verdict and orbit and sound_ready and ev)
        matches = root_matches.get(candidate, [])
        witnesses = validated_root_witnesses(candidate, matches) if manual else []
        rows.append({
            "candidate": candidate,
            "rank": position,
            "mansur_weight": weight,
            "origin": "مروحة fan()" if candidate in fan_set else (
                "مرشح المصدر خارج المروحة" if candidate == author else "جذر حكم سابق محفوظ في العرض"
            ),
            "sound_ready": sound_ready,
            "sound_rows": sound_rows,
            "sound_misses": sound_misses,
            "event": None if ev is None else {
                "text": ev.text,
                "source": ev.source,
                "tier": ev.tier,
                "tier_ar": ev.tier_ar,
                "note": ev.note,
                "line": ev.line(),
            },
            "branch_sense": (
                aed["selected"].get("en") if aed["selected"] else None
            ),
            "branch_sense_source": "AED" if aed["selected"] else None,
            "arabic_root_sense_scan": root_sense_summary(candidate, matches),
            "arabic_root_witnesses": witnesses,
            "semantic_orbit": orbit,
            "orbit_authorship": orbit_origin,
            "verdict": verdict if positive else None,
            "positive": positive,
        })
    return rows, author, author_position


def render(
    source: dict,
    previous: dict,
    batch: int,
    root_matches: dict[str, list[dict]],
) -> tuple[str, dict]:
    ordinal = int(previous["ordinal"])
    had_baseline_positive = (
        ordinal in BASELINE_POSITIVE_ORDINALS if batch == 1 else bool(previous.get("verdict"))
    )
    aed = aed_payload(ordinal, source["foreign"])
    script, script_note = OLD.script_for(source)
    stem, stripping, raw = morphology_for(source, previous, aed)
    stem_skeleton = OLD.K.FAN.skeleton(stem, script)
    candidates, author, author_position = candidate_rows(
        source, previous, aed, root_matches
    )
    positives = [c for c in candidates if c["positive"]]
    if len(positives) > 1:
        raise RuntimeError(f"تعدد موجب الصف {ordinal}")
    positive = positives[0] if positives else None
    proper = bool(previous.get("proper_name"))
    focus = positive or next((c for c in candidates if c["candidate"] == author), None)
    focus = focus or next((c for c in candidates if c["event"]), candidates[0] if candidates else None)
    closure = positive["verdict"] if positive else "OPEN-CANDIDATE"
    counted = bool(positive and not proper)
    ready = sum(bool(c["sound_ready"] and c["event"]) for c in candidates)
    eventless = sum(c["event"] is None for c in candidates)
    sound_open = sum(not c["sound_ready"] for c in candidates)
    tiers = Counter(str(c["event"]["tier"]) if c["event"] else "0" for c in candidates)
    ranked_text = "، ".join(
        f"`{c['candidate']}` ({c['mansur_weight']:.6f})" for c in candidates
    )
    reviewed_candidates = [
        c for c in candidates if c["sound_ready"] and c["event"]
    ]
    reviewed_roots = [c["candidate"] for c in reviewed_candidates]
    attested_roots = [
        f"`{c['candidate']}`={c['arabic_root_sense_scan']['match_count']}"
        for c in reviewed_candidates
        if c["arabic_root_sense_scan"]["match_count"]
    ]
    root_scan_line = (
        "- فحص عائلات الجذور العربية قبل حكم المدار: شُغّل "
        "`search_arabic_root_senses.py` مع `--max-chars 0` على "
        f"{len(reviewed_roots)} مرشحا كامل الصوت والحدث؛ الجذور ذات الشواهد: "
        + ("، ".join(attested_roots) if attested_roots else "لا شاهد في الذخيرة")
        + "."
    )
    root_witness_lines = []
    if positive and positive["arabic_root_witnesses"]:
        root_witness_lines = [
            f"- شاهد عائلة الجذر المنقول حرفيا: «{item['quote']}» "
            f"من {item['source']}؛ الرابط: {item['url']}."
            for item in positive["arabic_root_witnesses"]
        ]
    if positive:
        event_line = positive["event"]["line"]
        sound_text = "؛ ".join(positive["sound_rows"])
        orbit_line = positive["semantic_orbit"]
        verdict_line = positive["verdict"]
        obstacle = "لا عائق معلق"
        copy_line = (
            f"بقي الحكم السابق {positive['verdict']} بعد تصحيح معناه إلى AED"
            if had_baseline_positive else
            (
                f"نُسخ الحكم السابق غير صادر بالحكم {positive['verdict']} بعد استيفاء "
                "معنى AED وشاهد عائلة الجذر العربية"
                if ordinal in ROOT_RECHECK_TRANSITIONS["orbit_to_positive"] else
                f"نُسخ الحكم السابق غير صادر بالحكم {positive['verdict']} بعد اكتمال معنى AED المفرد"
            )
        )
    else:
        if focus and focus["event"]:
            event_line = focus["event"]["line"]
        else:
            event_line = "- الحدث من السجل المجمد: لم يرجع `FE.resolve` حدثا لمرشح العرض."
        if focus:
            sound_text = "؛ ".join(focus["sound_rows"] + focus["sound_misses"])
        else:
            sound_text = "لا مرشح قابل للرصف"
        if not aed["selected"]:
            orbit_line = "لم يثبت معنى AED موافق للسياق، فلا مادة أمينة لكتابة مدار موجب."
        elif ready == 0:
            orbit_line = "ثبت معنى AED مفرد، لكن لم يكتمل الصوت والحدث معا لمرشح واحد."
        else:
            orbit_line = (
                "فُحصت أحداث جميع المرشحين مع معنى AED المختار، ولم يقنع مدار واحد؛ "
                "لم تولد الآلة مدارا ولم يصدر حكم."
            )
        verdict_line = "غير صادر"
        if not aed["selected"]:
            obstacle = "معنى AED يوافق سياق الصف"
        elif ready == 0:
            obstacle = "مرشح تكتمل له رجل الصوت والحدث"
        else:
            obstacle = "مدار يدوي مقنع من معنى AED المختار"
        copy_line = (
            "نُسخ الحكم السابق الموجب لأن معنى AED لم يسند مداره"
            if had_baseline_positive else
            "بقي الحكم السابق غير صادر بعد إعادة المروحة والحدث ومعنى AED"
        )
    superseded_claim = None
    aed_contradiction = None
    if had_baseline_positive and not positive:
        superseded_claim = (
            str(previous.get("human_orbit") or "").strip()
            or (
                f"ربط معنى الفرع السابق «{source['foreign_sense']}» بالمرشح "
                f"`{previous_positive_root(previous) or previous.get('comparison_root') or author}` "
                f"على دعوى المصدر: «{previous.get('arabic_gloss') or '[لا شرح محفوظ]'}»"
            )
        )
        aed_meanings = "؛ ".join(
            str(entry.get("en") or "[لا ترجمة إنجليزية]")
            for entry in aed["hits"]
        ) or "لا مدخل"
        aed_contradiction = (
            f"AED أعاد: «{aed_meanings}»؛ لم يثبت فيها معنى «{source['foreign_sense']}» "
            "الذي حمل الدعوى السابقة."
        )
    comparison_place = (
        f"الرتبة {author_position} في العرض الموزون" if author_position
        else "خارج المروحة، فحفظ ولم يحتكر الحكم"
    )
    lines = [
        f"### بطاقة: إعادة حصاد `extended-egyptian:{ordinal:04d}`؛ `{source['foreign']}` «{source['foreign_sense']}»",
        f"<!-- {MARKER}:{ordinal:04d} -->",
        "- إصدار البروتوكول: RECOVERY-v2؛ طبقة استكشاف.",
        f"- سجل البطاقة السابقة: `EGYPTIAN-GODS-MAQAR:{ordinal:04d}`؛ نسبة المصدر: "
        f"{OLD.BOOK_LABELS[str(source['book'])]}، ص {source['page']}.",
        f"- الكلمة في الفرع: `{source['foreign']}`؛ وسم اللسان `{source['tongue']}`؛ {script_note}.",
        f"- جرد العلم: {'علم أو عنصر علم، يفصل عن العد' if proper else 'مفردة غير موسومة علما في الجرد السابق'}.",
        f"- الخطوة صفر: {stripping}؛ الخام `{' '.join(raw) or '∅'}`؛ اللب `{' '.join(stem_skeleton) or '∅'}`.",
        f"- المروحة المرتبة بوزن `F.rank`: {ranked_text}.",
        f"- مرشح المصدر: `{author or '(غير مستخرج)'}`؛ {comparison_place}؛ لا يستعمل دليلا مستقلا.",
        f"- فحص المروحة العضوي: {len(candidates)} مرشحا؛ {ready} لها الصوت والحدث معا؛ "
        f"{eventless} بلا حدث؛ {sound_open} صوتها مفتوح؛ درجات الحدث "
        f"1={tiers['1']}، 2={tiers['2']}، 3={tiers['3']}، 4={tiers['4']}، غياب={tiers['0']}.",
        event_line,
        f"- مسار الصوت للمرشح المعروض: {sound_text}.",
        *aed_lines(aed, source["foreign_sense"]),
        root_scan_line,
        *root_witness_lines,
        (f"- المعنى من قاموس الفرع بلا رتوش: «{aed['selected'].get('en')}» "
         f"من `{aed['selected']['translit']}` في AED."
         if aed["selected"] else
         "- المعنى من قاموس الفرع: لم يثبت مدخل AED موافق للسياق؛ بقيت الرجل الثالثة مفتوحة."),
        *(
            [f"- دعوى المدار السابق المنسوخة: {superseded_claim}.",
             f"- خلاف AED الذي أوجب النسخ: {aed_contradiction}"]
            if superseded_claim else []
        ),
        f"- المدار: {orbit_line}",
        "- المصفاة: لم يسم صف المصدر مانحا خارجيا؛ غياب المانح ليس برهان وراثة.",
        f"- عائق: النوع={closure}؛ يتطلب={obstacle}.",
        f"- حالة الإغلاق: {closure}.",
        f"- الحكم (استكشاف): {verdict_line}.",
        f"- سطر النسخ (2026-08-14، {MARKER}:{ordinal:04d}): {copy_line}.",
        "- مراجعة الاسترداد: حُفظت المروحة كاملة ومرشح المصدر ودرجة كل حدث.",
        "- مراجعة التشكيك: لم تقبل دعوى المصدر دليلا، وفُصل العلم عن العدد، ولم يصدر موجب بلا مدار مكتوب.",
    ]
    card = "\n".join(lines)
    if chr(0x2014) in card:
        raise ValueError(f"شرطة طويلة في بطاقة {ordinal}")
    summary = {
        "row_id": f"extended-egyptian:{ordinal:04d}",
        "ordinal": ordinal,
        "batch": batch,
        "book": source["book"],
        "page": source["page"],
        "tongue": source["tongue"],
        "foreign": source["foreign"],
        "foreign_sense": source["foreign_sense"],
        "khashim_comparative_sense": source["foreign_sense"],
        "aed": aed,
        "branch_dictionary_sense": (
            aed["selected"].get("en") if aed["selected"] else None
        ),
        "proper_name": proper,
        "script": script,
        "stem": stem,
        "stem_skeleton": stem_skeleton,
        "author_root": author,
        "author_root_rank": author_position,
        "candidates": candidates,
        "candidate_count": len(candidates),
        "event_tiers": dict(sorted(tiers.items())),
        "closure": closure,
        "verdict": positive["verdict"] if positive else None,
        "positive_root": positive["candidate"] if positive else None,
        "semantic_orbit": positive["semantic_orbit"] if positive else None,
        "orbit_authorship": positive["orbit_authorship"] if positive else None,
        "arabic_root_sense_reviews": [
            c["arabic_root_sense_scan"] for c in reviewed_candidates
        ],
        "arabic_root_witnesses": (
            positive["arabic_root_witnesses"] if positive else []
        ),
        "superseded_positive_claim": superseded_claim,
        "aed_contradiction": aed_contradiction,
        "counted_link": counted,
        "open_reason": None if positive else (
            ("لا معنى AED موافق للسياق" if aed["hits"] else "لا مدخل AED")
            if not aed["selected"] else
            ("لا مرشح تكتمل له رجل الصوت والحدث" if ready == 0 else "لا مدار يدوي مقنع")
        ),
    }
    return card, summary


def build(batch: int) -> None:
    source_rows = OLD.selected_rows()
    prior = old_rows()
    total_batches = (len(source_rows) + BATCH_SIZE - 1) // BATCH_SIZE
    if not 1 <= batch <= total_batches:
        raise SystemExit(f"رقم الدفعة خارج 1 إلى {total_batches}")
    start = (batch - 1) * BATCH_SIZE
    selected = source_rows[start:start + BATCH_SIZE]
    root_queries: set[str] = set()
    for offset, source in enumerate(selected, start=start + 1):
        if source.get("lane") == "survival-only":
            continue
        if offset not in prior:
            raise RuntimeError(f"لا بطاقة أصلية للصف {offset}")
        aed = aed_payload(offset, source["foreign"])
        *_, ranked = candidate_inventory(source, prior[offset], aed)
        root_queries.update(candidate for candidate, _ in ranked)
    # limit=None هو التنفيذ البرمجي المكافئ حرفيا لـ --max-chars 0.
    root_matches = ARS.matches_for_roots(
        ARS.DEFAULT_RESOURCES, root_queries, limit=None
    )
    rendered: list[str] = []
    summaries: list[dict] = []
    survival: list[dict] = []
    for offset, source in enumerate(selected, start=start + 1):
        if source.get("lane") == "survival-only":
            survival.append({
                "row_id": f"extended-egyptian:{offset:04d}",
                "ordinal": offset,
                "lane": "survival-only",
                "excluded_from_project_link_count": True,
            })
            continue
        if offset not in prior:
            raise RuntimeError(f"لا بطاقة أصلية للصف {offset}")
        text, summary = render(source, prior[offset], batch, root_matches)
        rendered.append(text)
        summaries.append(summary)

    positives = [r for r in summaries if r["verdict"]]
    counted = [r for r in positives if r["counted_link"]]
    opens = [r for r in summaries if not r["verdict"]]
    positive_ordinals = {int(r["ordinal"]) for r in positives}
    baseline_positive_ordinals = (
        set(BASELINE_POSITIVE_ORDINALS) if batch == 1 else {
            ordinal for ordinal in range(start + 1, start + len(selected) + 1)
            if ordinal in prior and prior[ordinal].get("verdict")
        }
    )
    converted = positive_ordinals - baseline_positive_ordinals
    retained = positive_ordinals & baseline_positive_ordinals
    revoked = baseline_positive_ordinals - positive_ordinals
    root_converted = converted & set(ROOT_RECHECK_TRANSITIONS["orbit_to_positive"])
    dictionary_converted = converted - root_converted
    aed_hit_cards = sum(bool(r["aed"]["hits"]) for r in summaries)
    aed_selected_cards = sum(bool(r["aed"]["selected"]) for r in summaries)
    aed_paths = Counter(r["aed"]["path"] for r in summaries)
    candidate_tiers = Counter()
    for row in summaries:
        candidate_tiers.update(row["event_tiers"])
    root_recheck = None
    if batch == 1:
        rows_by_ordinal = {int(row["ordinal"]): row for row in summaries}
        for ordinal in ROOT_RECHECK_TRANSITIONS["no_aed_to_orbit"]:
            row = rows_by_ordinal[ordinal]
            if row["open_reason"] != "لا مدار يدوي مقنع" or not row["aed"]["selected"]:
                raise RuntimeError(f"لم ينتقل الصف {ordinal} من عائق AED إلى عائق المدار")
        for ordinal in ROOT_RECHECK_TRANSITIONS["orbit_to_positive"]:
            row = rows_by_ordinal[ordinal]
            if row["verdict"] != "ROOT-TRACE" or row["positive_root"] != "يمن":
                raise RuntimeError(f"لم يتحول الصف {ordinal} بعد شاهد عائلة الجذر")
        open_counts = Counter(r["open_reason"] for r in opens)
        root_recheck = {
            "prior_counts": {
                "لا معنى AED موافق للسياق": 52,
                "لا مدار يدوي مقنع": 25,
            },
            "transitions": {
                "لا معنى AED موافق للسياق -> لا مدار يدوي مقنع":
                    ROOT_RECHECK_TRANSITIONS["no_aed_to_orbit"],
                "لا مدار يدوي مقنع -> ROOT-TRACE":
                    ROOT_RECHECK_TRANSITIONS["orbit_to_positive"],
            },
            "changed_cards": sum(len(v) for v in ROOT_RECHECK_TRANSITIONS.values()),
            "positive_conversions": len(root_converted),
            "current_counts": {
                "لا معنى AED موافق للسياق": open_counts["لا معنى AED موافق للسياق"],
                "لا مدار يدوي مقنع": open_counts["لا مدار يدوي مقنع"],
            },
        }
    report = {
        "schema": "egyptian-coptic-store-reharvest-v1.2-root-senses",
        "generated_at": "2026-08-14",
        "source_store": "data/egyptian-gods-maqar-batch-001.json إلى 010",
        "event_resolver": "scripts/frozen_event.py:FE.resolve",
        "fan": "scripts/fan_any_script.py:fan",
        "branch_dictionary": "AED, Simon D. Schweitzer (data/aed-egyptian-lexicon.json)",
        "arabic_root_sense_tool": {
            "path": "scripts/search_arabic_root_senses.py",
            "max_chars": 0,
        },
        "batch": batch,
        "batch_size": BATCH_SIZE,
        "total_batches": total_batches,
        "first_ordinal": start + 1,
        "last_ordinal": start + len(selected),
        "source_rows_examined": len(selected),
        "cards_written": len(summaries),
        "survival_only": len(survival),
        "candidate_count": sum(r["candidate_count"] for r in summaries),
        "arabic_root_query_count": len(root_queries),
        "arabic_root_attested_count": sum(bool(root_matches[root]) for root in root_queries),
        "candidate_event_tiers": dict(sorted(candidate_tiers.items())),
        "aed_path_counts": dict(sorted(aed_paths.items())),
        "aed_hit_cards": aed_hit_cards,
        "aed_selected_cards": aed_selected_cards,
        "positive_raw": len(positives),
        "positive_counted": len(counted),
        "open_candidate": len(opens),
        "baseline_positive_raw": len(baseline_positive_ordinals),
        "converted_from_baseline_open": len(converted),
        "converted_after_dictionary_sense": len(dictionary_converted),
        "converted_after_arabic_root_sense": len(root_converted),
        "converted_ordinals": sorted(converted),
        "retained_positive_ordinals": sorted(retained),
        "revoked_positive_ordinals": sorted(revoked),
        "arabic_root_recheck": root_recheck,
        "open_reason_counts": dict(Counter(r["open_reason"] for r in opens)),
        "rows": summaries,
        "survival_rows": survival,
    }
    report_path(batch).write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8", newline="\n",
    )

    section = "\n".join([
        marker(batch, "START"),
        f"## إعادة حصاد مخزن المصرية والقبطية، الدفعة {batch:03d} (2026-08-14)",
        "",
        f"**بيان النطاق.** الصفوف {start + 1:04d} إلى {start + len(selected):04d} من المخزن الثابت. "
        "أعيدت المروحة عبر `fan()` والحدث عبر `FE.resolve`، وأخذ معنى الفرع من AED لا من عمود خشيم. وفي كل مرشح اكتمل صوته وحدثه فُحصت عائلة الجذر العربية بـ`search_arabic_root_senses.py` مع `--max-chars 0` قبل حكم المدار. تعرض كل بطاقة جميع إصابات AED وشواهد الجذر، والمدار لا يصدر إلا مكتوبا باليد.",
        "",
        f"**الحصيلة.** فُحص {len(selected)} صفا، وكُتبت {len(summaries)} بطاقة، "
        f"والبقايا فقط {len(survival)}، والموجب الخام {len(positives)}، والموجب المعدود {len(counted)}، "
        f"والمفتوح {len(opens)}.",
        "",
        *rendered,
        marker(batch, "END"),
    ]) + "\n"
    current = READING.read_text(encoding="utf-8")
    if chr(0x2014) in section:
        raise ValueError("شرطة طويلة في قسم القراءة")
    section_start = marker(batch, "START")
    section_end = marker(batch, "END")
    if section_start in current:
        before, tail = current.split(section_start, 1)
        _, after = tail.split(section_end, 1)
        updated = before + section.rstrip() + after
    else:
        updated = current.rstrip() + "\n\n" + section
    READING.write_text(updated, encoding="utf-8", newline="\n")

    highlights = [
        f"`{r['foreign']} ↔ {r['positive_root']}`، {r['verdict']}"
        for r in positives[:10]
    ]
    audit = "\n".join([
        f"# محضر إعادة حصاد مخزن المصرية والقبطية، الدفعة {batch:03d}",
        "",
        "**التاريخ:** 2026-08-14  ",
        f"**النطاق:** الصفوف {start + 1:04d} إلى {start + len(selected):04d}، وعددها {len(selected)}.  ",
        "**الحالة:** مكتملة ومراجعة بعدستين.",
        "",
        "## ضابط الانحدار",
        "",
        "الضابط الإلزامي خُتم قبل الدفعة صفر: `ḫtm/ختم` و`mwt/موت` و`smr/سمر` و`mn/من` و`mr/مر` و`nfi̯/نف`، 6 من 6 سليمة وصفر تغير في الحكم. سجله الكامل في محضر الدفعة صفر.",
        "",
        "## الحصيلة",
        "",
        "| البند | العدد |",
        "|---|---:|",
        f"| فُحص | {len(selected)} |",
        f"| كُتب | {len(summaries)} |",
        f"| مرشحو المروحة | {report['candidate_count']} |",
        f"| موجب خام | {len(positives)} |",
        f"| موجب معدود | {len(counted)} |",
        f"| مفتوح | {len(opens)} |",
        f"| بطاقات أصابها AED | {aed_hit_cards} |",
        f"| بطاقات اختير لها معنى AED مفرد | {aed_selected_cards} |",
        f"| تحولت من مفتوح إلى موجب في الجملة | {len(converted)} |",
        f"| منها بعد معنى AED المفرد | {len(dictionary_converted)} |",
        f"| منها بعد شاهد عائلة الجذر العربي | {len(root_converted)} |",
        f"| موجب قديم بقي | {len(retained)} |",
        f"| موجب قديم نُسخ | {len(revoked)} |",
        "",
        f"**رقم الفرق المطلوب:** تحولت {len(converted)} بطاقات في الجملة: "
        + "، ".join(f"`{ordinal:03d}`" for ordinal in sorted(converted)) + ".",
        f"منها {len(dictionary_converted)} بعد تعيين معنى AED المفرد: "
        + "، ".join(f"`{ordinal:03d}`" for ordinal in sorted(dictionary_converted))
        + f"؛ ومنها {len(root_converted)} بعد استيفاء شاهد عائلة الجذر: "
        + "، ".join(f"`{ordinal:03d}`" for ordinal in sorted(root_converted)) + ".",
        f"بقي من الموجب القديم {len(retained)}: "
        + "، ".join(f"`{ordinal:03d}`" for ordinal in sorted(retained))
        + f"؛ ونُسخ {len(revoked)}: "
        + "، ".join(f"`{ordinal:03d}`" for ordinal in sorted(revoked)) + ".",
        "",
        "أسباب المفتوح بالعد: " + "، ".join(
            f"{reason}={number}" for reason, number in report["open_reason_counts"].items()
        ) + ".",
        "",
        *( [
            "## إعادة صفوف العائقين على عائلات اللسان",
            "",
            "شُغلت الأداة على كل جذر عربي اكتمل له الصوت والحدث، بالصيغة المثبتة في كل بطاقة وبالخيار `--max-chars 0`، ثم قُرئت الشواهد كاملة. الشاهد سند للمدار المكتوب، لا بديل منه.",
            "",
            "| الوصف السابق | العدد السابق | ما تغير | الوصف الحالي | العدد الحالي |",
            "|---|---:|---|---|---:|",
            f"| لا معنى AED موافق للسياق | 52 | `028` و`029` و`030`: ثبت معنى AED، ولم يقنع المدار | لا معنى AED موافق للسياق | {report['open_reason_counts'].get('لا معنى AED موافق للسياق', 0)} |",
            f"| لا مدار يدوي مقنع | 25 | `145` و`146`: دخلا ROOT-TRACE بشاهد تاج العروس | لا مدار يدوي مقنع | {report['open_reason_counts'].get('لا مدار يدوي مقنع', 0)} |",
            "",
            "تغير وصف خمس بطاقات من المجموعتين: ثلاث انتقلت من عائق المعنى القاموسي إلى عائق المدار، واثنتان تحولتا إلى موجب. واقتُبس في بطاقتي الموجب نصا تاج العروس واسم المعجم والرابط، ثم كُتب المدار الواصل بين معنى AED والحدث المجمد.",
            "",
        ] if batch == 1 else [] ),
        "درجات أحداث المرشحين: " + "، ".join(
            f"الدرجة {tier}={number}" if tier != "0" else f"غياب={number}"
            for tier, number in report["candidate_event_tiers"].items()
        ) + ". الدرجة لم تغير رتبة السلم.",
        "",
        "## أبرز الأزواج الداخلة",
        "",
        *(f"- {x}." for x in highlights),
        *( ["- لم تبلغ الدفعة عشرة أزواج موجبة، فذُكر جميع ما دخل بلا حشو."] if len(highlights) < 10 else [] ),
        "",
        "## المراجعتان",
        "",
        "- عدسة الاسترداد: شغلت `fan()` لكل صف، وحفظت كل مرشح ووزنه ومساره ودرجة حدثه، وعرضت قائمة AED كاملة، ثم شغلت عائلات اللسان بلا قطع عرض لكل مرشح تام الصوت والحدث.",
        "- عدسة التشكيك: لم تأخذ إصابة AED الأولى آليا، وراجعت المختار في سياق خشيم، وفصلت الأعلام عن العدد، ونسخت كل موجب قديم لم يسنده المعنى القاموسي مع إظهار الدعوى السابقة وخلاف AED، ولم تحول غياب المدار إلى `NO-TRACE`.",
        "",
        "## سطر الحصيلة",
        "",
        f"فُحص {len(selected)} صفا، وكُتبت {len(summaries)} بطاقة؛ الموجب الخام {len(positives)}، "
        f"والمعدود {len(counted)}، والمفتوح {len(opens)}؛ تحولت {len(converted)} بطاقات، "
        f"منها {len(dictionary_converted)} بعد معنى AED و{len(root_converted)} بعد شاهد عائلة الجذر.",
        "",
    ])
    if chr(0x2014) in audit:
        raise ValueError("شرطة طويلة في المحضر")
    audit_path(batch).write_text(audit, encoding="utf-8", newline="\n")
    print(
        f"الدفعة {batch:03d}: فُحص {len(selected)}؛ كُتب {len(summaries)}؛ "
        f"موجب خام {len(positives)}؛ موجب معدود {len(counted)}؛ مفتوح {len(opens)}؛ "
        f"تحول {len(converted)}"
    )
    print(f"كُتب: {report_path(batch).relative_to(ROOT).as_posix()}")
    print(f"كُتب: {audit_path(batch).relative_to(ROOT).as_posix()}")


def check(batch: int) -> int:
    path = report_path(batch)
    payload = json.loads(path.read_text(encoding="utf-8"))
    bad: list[str] = []
    if payload["source_rows_examined"] != BATCH_SIZE and batch != payload["total_batches"]:
        bad.append("حجم الدفعة ليس 150")
    if payload["cards_written"] != len(payload["rows"]):
        bad.append("عدد البطاقات مختل")
    for row in payload["rows"]:
        for review in row.get("arabic_root_sense_reviews", []):
            if review.get("max_chars") != 0 or review.get("truncated"):
                bad.append(f"فحص جذر مقطوع في {row['row_id']}:{review.get('root')}")
        for candidate in row["candidates"]:
            ev = FE.resolve(candidate["candidate"])
            if (ev is None) != (candidate["event"] is None):
                bad.append(f"اختل الحدث في {row['row_id']}:{candidate['candidate']}")
            elif ev and candidate["event"]["line"] != ev.line():
                bad.append(f"لم ينقل الحدث حرفيا في {row['row_id']}:{candidate['candidate']}")
        if row["verdict"]:
            chosen = [c for c in row["candidates"] if c["positive"]]
            if len(chosen) != 1 or not chosen[0]["sound_ready"] or not chosen[0]["event"] or not row["semantic_orbit"]:
                bad.append(f"موجب بلا الأرجل الثلاث في {row['row_id']}")
        if int(row["ordinal"]) in ROOT_RECHECK_TRANSITIONS["orbit_to_positive"]:
            if row.get("verdict") != "ROOT-TRACE" or len(row.get("arabic_root_witnesses", [])) != 2:
                bad.append(f"تحويل عائلة الجذر ناقص في {row['row_id']}")
            for witness in row.get("arabic_root_witnesses", []):
                if not witness.get("quote") or not witness.get("source") or not witness.get("url"):
                    bad.append(f"شاهد معجمي ناقص في {row['row_id']}")
    if batch == 1:
        recheck = payload.get("arabic_root_recheck") or {}
        if recheck.get("changed_cards") != 5 or recheck.get("positive_conversions") != 2:
            bad.append("اختل عد انتقال صفوف العائقين")
    if bad:
        print("FAIL: " + "؛ ".join(bad[:12]))
        return 1
    print(
        f"CLEAN: الدفعة {batch:03d}؛ الصفوف {payload['source_rows_examined']}؛ "
        f"المرشحون {payload['candidate_count']}؛ كل الأحداث مطابقة لـFE.resolve"
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch", type=int, required=True)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    if args.check:
        return check(args.batch)
    build(args.batch)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
