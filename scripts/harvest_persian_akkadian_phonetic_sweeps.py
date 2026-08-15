#!/usr/bin/env python3
"""حوّل مسحَي الفارسية والأكّادية الصوتيين إلى بطاقات كاملة.

الطابور ثابت: الشهادة المباشرة في اللسانين، ثم بقية اجتماع الصوت والمعنى،
ثم الصوت وحده. المسح يفتح الصوت ولا يحكم المعنى. لذلك لا يصدر موجب إلا من
``MANUAL_SPECS``، وفيه المدار مكتوب بالكلمات. وكل ما عداه يبقى
``OPEN-CANDIDATE`` بعد إظهار المروحة والحدث والشواهد العربية كاملة.
"""

from __future__ import annotations

import argparse
from collections import Counter
import itertools
import json
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

import count_links as COUNT  # noqa: E402
import fan_any_script as FAN  # noqa: E402
import frozen_event as EVENT  # noqa: E402
import search_arabic_root_senses as AR  # noqa: E402


DATE = "2026-08-15"
BATCH_SIZE = 150
CONTROL_BASELINE = "1281ac5"
EXPLORATION = ROOT / "04-cross-linguistic" / "exploration"
READINGS = ROOT / "04-cross-linguistic" / "readings"
DATA = ROOT / "data"
AUDITS = ROOT / "05-audits"

CONFIG = {
    "persian": {
        "label": "الفارسية",
        "id": "PERSIAN",
        "script": "latin",
        "sweep": EXPLORATION / "phonetic-sweep-persian.json",
        "lexicon": DATA / "branch-lexicons" / "persian.json",
        "reading": READINGS / "persian.md",
        "both": 127,
        "direct": 101,
        "sound_only": 974,
    },
    "akkadian": {
        "label": "الأكّادية",
        "id": "AKKADIAN",
        "script": "akkadian",
        "sweep": EXPLORATION / "phonetic-sweep-akkadian.json",
        "lexicon": DATA / "branch-lexicons" / "akkadian.json",
        "reading": READINGS / "akkadian.md",
        "both": 120,
        "direct": 96,
        "sound_only": 359,
    },
}

DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")
ARABIC_DIACRITICS = re.compile(r"[\u0610-\u061a\u064b-\u065f\u0670\u06d6-\u06ed]")


def clean(value: Any) -> str:
    """نص سطري بلا شرطة طويلة وبأرقام غربية."""
    text = " ".join(str(value or "").split()).translate(DIGITS)
    return text.replace("`", "ˋ").replace("—", "؛").replace("–", "؛")


def english_words(value: Any) -> set[str]:
    stop = {
        "the", "and", "with", "from", "into", "that", "this", "form",
        "someone", "something", "used", "type", "one", "for", "of", "to",
        "a", "an", "or", "as", "be", "is", "are", "in", "on",
    }
    return {
        word for word in re.findall(r"[a-z]{2,}", str(value or "").casefold())
        if word not in stop
    }


def roman_key(value: Any) -> str:
    text = unicodedata.normalize("NFD", str(value or "").casefold())
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = (
        text.replace("š", "sh").replace("č", "ch").replace("ž", "zh")
        .replace("ḫ", "kh").replace("ḥ", "h").replace("ṣ", "s")
        .replace("ṭ", "t").replace("ʾ", "").replace("ʿ", "")
    )
    return re.sub(r"[^a-z]", "", text)


def persian_spoken(value: Any) -> str:
    """رومنة مقروءة، مع إبقاء â كما طلب المؤلف وفتح x على kh."""
    text = str(value or "").strip()
    return (
        text.replace("x", "kh").replace("X", "Kh")
        .replace("š", "sh").replace("Š", "Sh")
        .replace("č", "ch").replace("Č", "Ch")
        .replace("ž", "zh").replace("Ž", "Zh")
        .replace("ġ", "gh").replace("ğ", "gh")
    )


def arabic_letters(value: Any) -> str:
    text = ARABIC_DIACRITICS.sub("", str(value or ""))
    return "".join(char for char in text if "ء" <= char <= "ي")


def closure_for(root: str) -> str:
    return "NUCLEUS-TRACE" if len(arabic_letters(root)) == 2 else "ROOT-TRACE"


def spec(root: str, orbit: str, gloss: str = "") -> dict[str, str]:
    return {"root": root, "orbit": orbit, "gloss": gloss}


# هذه المدارات هي موضع الحكم اليدوي. لا يقرأ البرنامج تداخل المسح حكمًا.
MANUAL_SPECS: dict[tuple[str, str], list[dict[str, str]]] = {
    ("persian", "نفت"): [spec("نفط", "النفط هو المادة الزيتية القابلة للاشتعال نفسها في الطرفين؛ فالاسم الفارسي القديم وصيغة نفط العربية يلتقيان في جرم واحد لا في وصف عام.")],
    ("persian", "کندر"): [spec("كندر", "الكندر في الطرفين صمغ شجرة البوسويليا العطري المعروف باللبان؛ فاتحد المسمى النباتي ومادته العطرية.")],
    ("persian", "زمان"): [spec("زمن", "الزمان مدة أو عصر يقع فيه الحدث ويمتد؛ وهذا عين معنى الوقت والعصر والفترة في قاموس الفرع.")],
    ("persian", "گرامی"): [spec("كرم", "الشيء الكريم نفيس ممتاز مقبول لدى النفس، وگرامی هو العزيز النفيس الممتاز؛ فالتقاء القبول والنفاسة مباشر.")],
    ("persian", "خنجر"): [spec("خنجر", "الخنجر نصل قصير نافذ يخلخل ما يدخل فيه ويشق باطنه؛ والمسمى في القاموس هو الخنجر نفسه.")],
    ("persian", "پرند"): [spec("فرند", "الفرند والپرند اسم للنسيج الحريري الدمشقي ذي العلامات؛ فاتحد نوع النسيج لا مجرد مادة اللباس.")],
    ("persian", "بازار"): [spec("بزر", "السوق موضع يبرز فيه المتاع ويتحرك بين البائع والمشتري؛ وشواهد بزر العربية تسمي البازار نفسه في هذا العضو المعجمي.")],
    ("persian", "زنگ"): [spec("زنج", "زنج في الطرفين اسم للسكان السود وبلادهم في شرقي إفريقية؛ فاتحد العلم الجماعي ومدلوله.")],
    ("persian", "مهر"): [spec("مهر", "الخاتم يضغط رسمه في المادة فيترك أثرًا مميزًا؛ وهذا هو الختم والانطباع اللذان يسميهما قاموس الفرع.")],
    ("persian", "کنار"): [spec("كنر", "الكنار حد جانبي ينتهي عنده الشيء ويفصل داخله عن خارجه؛ وهو الجانب والحافة والحد في قاموس الفرع.")],
    ("persian", "قاقم"): [spec("ققم", "القاقم في الطرفين الحيوان نفسه المعروف بالermine أو stoat؛ فالتقاء الاسم الحيواني كامل.")],
    ("persian", "بلوط"): [spec("بلط", "البلوط في الطرفين شجرة السنديان وثمرتها؛ فاتحد المسمى النباتي وثمره.")],
    ("persian", "پریش"): [spec("فرش", "التشعث والتبعثر بسط للأجزاء ونشر لها بعد اجتماع؛ فيلتقي پریش حدث فرش في الانبساط والانتشار.")],
    ("persian", "سداب"): [spec("سذب", "السذاب اسم للنبات نفسه في الطرفين، سواء أريد به الحرمل أو نبات rue في المدخلة المختارة.")],
    ("persian", "هندو"): [spec("هند", "النسبة إلى الهند وساكنها ترد إلى اسم هند نفسه؛ فالهندي وممارس ديانتها منسوبان إلى البلد المسمى في الجذر.")],
    ("persian", "روپوش"): [spec("لبس", "الغطاء والثوب الخارجي يداخل الجسد أو الشيء ويلازمه ساترًا له؛ وهذا حدث لبس في التغطية بالمداخلة.")],
    ("persian", "تلک"): [spec("طلق", "التلك والطلق اسم للمعدن الصفائحي اللين نفسه؛ فالمسمى المعدني واحد في قاموس الفرع وشواهد العربية.")],
    ("persian", "بنگ"): [spec("بنج", "البنج في الطرفين نبات مخدر وما يصنع منه من مخدر؛ فاتحد النبات وأثره المسكر.")],
    ("persian", "ترک"): [spec("ترك", "ترك اسم القوم أنفسهم في الطرفين؛ فاتحد العلم الإثني من غير جسر وصفي.")],
    ("persian", "گلیم"): [spec("قلم", "القليم في شواهد العربية والگلیم الفارسي نسيج صوفي خشن يبسط بساطًا؛ فاتحد نوع المنسوج.")],
    ("persian", "زنگی"): [spec("زنج", "الزنگي منسوب إلى زنج في السواد والاسم الجماعي؛ فالمعنى النسبي يعود إلى المسمى نفسه.")],
    ("persian", "کهر"): [spec("كحل", "الكحلة واللون الداكن الضارب إلى الحمرة أو السمرة وصف لوني واحد في الفرس المذكور.")],
    ("persian", "برنج"): [spec("برنج", "البرنج في الطرفين اسم لحب الأرز نفسه؛ فاتحد المسمى الغذائي.")],
    ("persian", "کهربا"): [spec("كهرب", "الكهرباء هنا الكهرمان نفسه، جرم أصفر يجذب الخفيف عند دلكه؛ فاتحد المسمى المادي.")],
    ("persian", "پندک"): [spec("بندق", "البندق في الطرفين الثمرة نفسها، ومدخلة الفرع تضم البرعم من المشابهة الشكلية ولا تنقل إليه الحكم.")],
    ("persian", "کرنا"): [spec("قرن", "آلة الحرب الطويلة بوق يصنع على هيئة القرن ويطلق صوته؛ فالمسمى الآلي قائم على القرن نفسه.")],
    ("persian", "کمرا"): [spec("كمر", "الخيط الذي يشد وسط أتباع زرادشت حزام يحيط بالوسط؛ وهو معنى الكمر والحزام في الشاهد العربي.", "string worn")],
    ("persian", "زمانه"): [spec("زمن", "العصر والحقبة امتداد من الزمن، وهو المعنى الأول المسمى في مدخلة زمانه.")],
    ("persian", "پکر"): [spec("فكر", "الحال المتأمل المنشغل يلازم الفكر ويظهر أثره في السكون والهم؛ فمعنى pensive يلتقي فعل الفكر.")],
    ("persian", "لگام"): [spec("لجم", "اللجام أداة تمسك فم الدابة وتضبط حركتها؛ وهو bridle نفسه في قاموس الفرع.")],
    ("persian", "بن"): [spec("بني", "الأساس أسفل يحمل ما يبنى فوقه ويثبت قوامه؛ فمعنى bottom and foundation يلتقي حدث البناء في إقامة الأصل الحامل.", "foundation")],

    ("akkadian", "ṣillum"): [spec("ظل", "الظل ستر من الضوء وموضع يستظل به، ومنه الحماية والكنف؛ وهذه المعاني نفسها في مدخلة ṣillum.")],
    ("akkadian", "šikarum"): [spec("سكر", "الشراب المسكر يحمل أثر السكر ويغطي تمييز شاربه؛ فالبيرة والشراب الكحولي يلتقيان مادة سكر مباشرة.")],
    ("akkadian", "šumēlum"): [spec("شمل", "الشمال اسم الجهة والجانب الأيسر في العربية، وšumēlum هو اليسار والجانب الأيسر نفسه.")],
    ("akkadian", "talmīdum"): [spec("تلمذ", "التلميذ متعلم يتبع معلما ويتلقى عنه الصنعة؛ وهذا هو apprentice and student في قاموس الفرع.")],
    ("akkadian", "ṣuprum"): [spec("ظفر", "الظفر صفيحة طرف الإصبع التي تخدش وتترك طبعتها؛ وهذه nail and nail impression في المدخلة.")],
    ("akkadian", "šiqlum"): [spec("ثقل", "الشيقل مقدار موزون من الثقل؛ فالوحدة لا تسمى إلا بما يضبط وزنها، ومعنى الوزن مصرح به في الأصل السامي المنشور.")],
    ("akkadian", "ṣalmum"): [spec("ظلم", "السواد والظلمة غياب للنور يكسو المرئي ويغمسه في الدكنة؛ فصفة black and dark هي السلسلة نفسها.")],
    ("akkadian", "qabrum"): [spec("قبر", "القبر حفرة يوارى فيها الميت؛ وهو grave and tomb نفسه.")],
    ("akkadian", "qebērum"): [spec("قبر", "دفن الجسد ولفه استعدادا للمواراة هو فعل القبر نفسه في العربية.")],
    ("akkadian", "šapārum"): [spec("سفر", "إرسال الكلام مكتوبا أو منطوقا ينقله ويكشف مضمونه للمرسل إليه؛ والسفر الكتاب المسفر عن المكتوب.")],
    ("akkadian", "salīmum"): [spec("سلم", "السلام صلح وأمان بعد انقطاع النزاع؛ وهو peace and concord and amity في المدخلة.")],
    ("akkadian", "salāmum"): [spec("سلم", "المصالحة دخول في السلم والأمان؛ فالفعل الأكادي يحقق معنى peace نفسه.")],
    ("akkadian", "tīlum"): [spec("تل", "التل كومة تراب مرتفعة أو mound؛ فاتحد الجرم الأرضي المجموع.")],
    ("akkadian", "quppum"): [spec("قف", "القفة وعاء منسوج أو صندوق يحمل ما يوضع فيه؛ وهذه wicker basket and wooden box في المدخلة.")],
    ("akkadian", "šaplum"): [spec("سفل", "السفل أسفل الشيء وقاعه؛ وهو underside and bottom نفسه، ولا يدخل معنى المتأخرات.")],
    ("akkadian", "šiṭrum"): [spec("سطر", "النص والنقش كتابة مصطفة في سطور؛ فالمعنى الكتابي يلتقي حدث سطر، ولا يدخل معنى النجوم.")],
    ("akkadian", "šaṭārum"): [spec("سطر", "الكتابة والنسخ والنقش إنشاء سطر مكتوب ممتد مضبوط؛ وهذا معنى المدخلتين الاسمية والفعلية.")],
    ("akkadian", "šiprum"): [spec("سفر", "الرسالة والتقرير كلام ينتقل إلى غير صاحبه ويكشف له خبره؛ وهي سلسلة السفر الكتابي والإبلاغ.")],
    ("akkadian", "warāqum"): [spec("ورق", "اخضرار النبات واصفراره يظهران في الورق الرقيق الذي يكسوه؛ فالفعل اللوني متصل مباشرة بمادة ورق.")],
    ("akkadian", "dayyānum"): [spec("دين", "الديان قاض يلزم الخصوم بالحكم والحق؛ وهو judge نفسه في المدخلة.")],
    ("akkadian", "parāsum"): [spec("فرس", "التقسيم والفصل يقطعان الكل ويميزان أجزاءه؛ والفرس في الشواهد شق وتمزيق، فالمعنى الحدثي واحد.")],
    ("akkadian", "warādum"): [spec("ورد", "الورود بلوغ المكان أو الماء بالتقدم إليه أو التدلي؛ والنزول والمجيء في warādum حركة بلوغ من هذا الباب.")],
    ("akkadian", "zamārum"): [spec("زمر", "الغناء المصحوب بالآلة أو المجرد إخراج لصوت موسيقي منظم؛ والزمر عزف بالقصبة وصوتها.")],
    ("akkadian", "napāšum"): [spec("نفش", "التنفس يوسع الصدر ويفرق انقباضه، والاسترخاء والاتساع أثران لهذا الانتفاش؛ فالسلسلة الحسية متصلة.")],
    ("akkadian", "nasāḫum"): [spec("نسخ", "النسخ إزالة الشيء من موضع وتحويله، وهو الاقتلاع والنزع والإزالة المذكورة في الفعل الأكادي.")],
    ("akkadian", "birqum"): [spec("برق", "البرق بروز ضوء حاد لامع في الجو؛ وهو lightning and lightning bolt نفسه.")],
    ("akkadian", "šuršum"): [spec("شرش", "الشرش أصل النبات الممتد في باطن الأرض، ومنه قاعدة الشيء وأساسه؛ وهذه root and base and foundation في المدخلة.")],
    ("akkadian", "šebērum"): [spec("ثبر", "الكسر يجمع أجزاء الجرم منقبضة بعد أن يفصل صلابته ويهدمه؛ ومعنى break and fracture مصرح به في الطرفين المعجميين.")],
    ("akkadian", "šalgum"): [spec("ثلج", "الثلج دقائق ماء تجمدت وتماسكت؛ وهو snow and sleet نفسه.")],
    ("akkadian", "ṣamādum"): [spec("ضمد", "الضمد جمع الشيء إلى الشيء وشده عليه؛ وهذا yoke and harness and tie and attach في الفعل الأكادي.")],
    ("akkadian", "gišrum"): [spec("جسر", "العارضة الخشبية تمتد فوق فرجة وتغلقها أو تتيح العبور عليها؛ فهي أبسط جرم الجسر الحامل الممتد.")],
    ("akkadian", "napṭum"): [spec("نفط", "النفط والنفثا اسم للمادة الزيتية القابلة للاشتعال نفسها.")],
    ("akkadian", "qunnabu"): [spec("قنب", "القنب نبات عطري أو مخدر تؤخذ بذوره وأزهاره؛ والمسمى النباتي واحد في الطرفين.")],
    ("akkadian", "marrum"): [spec("مر", "المرارة طعم حاد لاذع يقبض الفم؛ وهذه bitter and brackish and biting في المدخلة.")],
    ("akkadian", "kīma"): [spec("كم", "كما أداة تشبيه ومماثلة في العربية، وkīma بمعنى like and as and according to أداة الوظيفة نفسها.")],
    ("akkadian", "pītum"): [spec("فت", "الفتحة والثلمة انفصال في جرم كان متصلا، والفت تكسير الهش وفصل أجزائه؛ فمعنى aperture and breach and break يلتقي الحدث.")],
    ("akkadian", "biṣṣūrum"): [spec("بظر", "البظر عضو ظاهر من الفرج داخل مجال المعنى التشريحي الذي تسميه المدخلة vulva؛ فلا يحمل الحكم معنى vagina الأوسع.", "vulva")],
    ("akkadian", "bīnum"): [spec("بن", "الابن نسل خارج من أبيه وأمه، وbīnum هو son نفسه في قاموس الفرع.")],
}


CONTROL_SPECS = {
    "persian": [
        ("parêš", "فرش", "بطاقة: parêš «مبعثر/متناثر»"),
        ("astar", "ستر", "بطاقة: astar «بطانة»"),
        ("rōd", "رود", "بطاقة 970: رود «river; torrent»"),
        ("zar", "زر", "بطاقة 1020: زر"),
        ("daryā", "دريا", "بطاقة 1030: دریا"),
        ("rīš", "ريش", "بطاقة 1929: ریش"),
    ],
    "akkadian": [
        ("aḫāzu", "أخذ", "بطاقة: aḫāzu «يأخذ ويمسك»"),
        ("malkum", "ملك", "بطاقة: malku A «ملك وحاكم»"),
        ("akālum", "أكل", "بطاقة: akālu/akalu «يأكل، وطعام»"),
        ("lišānum", "لسن", "بطاقة: lišānu «اللسان واللغة»"),
        ("šinnum", "سن", "بطاقة: šinnu A «السن»"),
        ("dāmum", "دم", "بطاقة: dāmu/dāmum «الدم»"),
    ],
}


def load_inputs() -> dict[str, dict[str, Any]]:
    loaded: dict[str, dict[str, Any]] = {}
    for language, cfg in CONFIG.items():
        sweep = json.loads(cfg["sweep"].read_text(encoding="utf-8"))
        lexicon = json.loads(cfg["lexicon"].read_text(encoding="utf-8"))
        both = list(sweep.get("both") or [])
        sound_only = list(sweep.get("sound_only") or [])
        if len(both) != cfg["both"] or len(sound_only) != cfg["sound_only"]:
            raise AssertionError(f"تغير مقام مسح {language}")
        if sum(bool(row.get("direct")) for row in both) != cfg["direct"]:
            raise AssertionError(f"تغير عدد الشهادة المباشرة في {language}")
        if lexicon.get("language") != language or lexicon.get("script") != cfg["script"]:
            raise AssertionError(f"اختلط قاموس الفرع أو خطه في {language}")
        index: dict[str, list[dict[str, Any]]] = {}
        for entry in lexicon.get("entries") or []:
            index.setdefault(str(entry.get("word") or ""), []).append(entry)
        loaded[language] = {"sweep": sweep, "lexicon": lexicon, "index": index}
    return loaded


def choose_entry(row: dict[str, Any], entries: list[dict[str, Any]]) -> int | None:
    if not entries:
        return None
    wanted = english_words(row.get("gloss"))
    shared = set(str(value).casefold() for value in row.get("shared") or [])
    scores: list[tuple[tuple[int, int, float, int], int]] = []
    for index, entry in enumerate(entries):
        found = english_words(entry.get("en"))
        overlap = len(wanted & found)
        union = len(wanted | found) or 1
        scores.append(((len(shared & found), overlap, overlap / union, -index), index))
    return max(scores)[1]


def queue_rows(loaded: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    stages: list[tuple[str, str, list[dict[str, Any]]]] = []
    for stage in ("direct", "both-rest", "sound-only"):
        for language in ("persian", "akkadian"):
            sweep = loaded[language]["sweep"]
            if stage == "direct":
                rows = [row for row in sweep["both"] if row.get("direct")]
            elif stage == "both-rest":
                rows = [row for row in sweep["both"] if not row.get("direct")]
            else:
                rows = list(sweep["sound_only"])
            stages.append((stage, language, rows))

    output: list[dict[str, Any]] = []
    ordinal = 0
    counters = {language: {"both": 0, "sound-only": 0} for language in CONFIG}
    for stage, language, rows in stages:
        for row in rows:
            ordinal += 1
            kind = "sound-only" if stage == "sound-only" else "both"
            counters[language][kind] += 1
            entries = loaded[language]["index"].get(str(row.get("branch") or ""), [])
            selected = choose_entry(row, entries)
            selected_entry = entries[selected] if selected is not None else {}
            published = str(selected_entry.get("read") or row.get("say") or row.get("branch") or "")
            spoken = persian_spoken(published) if language == "persian" else published
            output.append({
                **row,
                "language": language,
                "stage": stage,
                "ordinal": ordinal,
                "language_index": counters[language][kind],
                "entries": entries,
                "selected_entry_index": selected,
                "selected_entry": selected_entry,
                "published_romanization": published,
                "spoken_romanization": spoken,
            })
    if len(output) != 1580:
        raise AssertionError(f"تغير مجموع الطابور: {len(output)}")
    if [row["stage"] for row in output[:197]].count("direct") != 197:
        raise AssertionError("اختل تقديم الشهادة المباشرة")
    if [row["stage"] for row in output[197:247]].count("both-rest") != 50:
        raise AssertionError("اختل موضع بقية اجتماع الصوت والمعنى")
    return output


def batch_windows(queue: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    """حدود أمر المؤلف: 150 ثم 47 مباشرة، ثم 50، ثم الصوت وحده."""
    windows = [queue[:150], queue[150:197], queue[197:247]]
    sound_only = queue[247:]
    windows.extend(
        sound_only[start:start + BATCH_SIZE]
        for start in range(0, len(sound_only), BATCH_SIZE)
    )
    if [len(rows) for rows in windows[:3]] != [150, 47, 50]:
        raise AssertionError("اختلت حدود الشهادة المباشرة وبقية اجتماع المعنى")
    return windows


def positive_headings(language: str) -> list[str]:
    return [
        heading for heading, degrees, _family in COUNT.scan_path(CONFIG[language]["reading"])
        if degrees
    ]


def prior_issued(row: dict[str, Any], headings: dict[str, list[str]]) -> list[str]:
    language = str(row["language"])
    if language == "persian":
        word = str(row.get("branch") or "")
        keys = {
            roman_key(row.get("published_romanization")),
            roman_key(row.get("spoken_romanization")),
        } - {""}
        found = []
        for heading in headings[language]:
            tokens = {
                roman_key(token) for token in re.findall(r"[A-Za-zÀ-žḀ-ỿʾʿ]+", heading)
            } - {""}
            if word in heading or keys & tokens:
                found.append(heading)
        return found

    target = "".join(FAN.skeleton(str(row["spoken_romanization"]), "akkadian"))
    found = []
    for heading in headings[language]:
        tokens = re.findall(r"[A-Za-zāēīōūâêîûšṣṭḫḥʾʿ]+", heading)
        skeletons = {"".join(FAN.skeleton(token, "akkadian")) for token in tokens}
        if target and target in skeletons:
            found.append(heading)
    return found


def direct_arabic_loan(etymology: str) -> tuple[bool, str]:
    text = str(etymology or "")
    direct = bool(
        re.search(r"\b(?:Borrowed|borrowing)\s+from\s+Arabic\b", text, re.I)
        or re.search(r"\bFrom\s+Arabic\b", text, re.I)
        or re.search(r"\bArabic\b.{0,100}\bbor\.\s*Persian\b", text, re.I)
    )
    if not direct:
        return False, ""
    nearby = re.search(r"Arabic\s+([ء-يَ-ْـ]+)", text, re.I)
    donor = arabic_letters(nearby.group(1)) if nearby else ""
    return True, donor or "العربية في حقل الاشتقاق"


def named_branch_loan(language: str, etymology: str) -> tuple[str, str]:
    """مانح مباشر مسمى. الفارسية العربية لها حكم المؤلف الخاص."""
    if language == "persian":
        is_arabic, donor = direct_arabic_loan(etymology)
        return ("LOANWORD", donor) if is_arabic else ("", "")
    match = re.search(
        r"(?:Borrowed from|loan from|From)\s+(Sumerian|West Semitic|Elamite|Hurrian)",
        str(etymology or ""), re.I,
    )
    if not match:
        return "", ""
    return "LOANWORD-THIRD-PARTY-TO-BRANCH", clean(match.group(1))


def source_skeletons(word: str, script: str) -> list[list[str]]:
    skeleton = FAN.skeleton(word, script)
    output = [skeleton]
    if script == "akkadian":
        source = unicodedata.normalize("NFD", str(word).strip().lower())
        if source[:1] in "aeiou" and 1 <= len(skeleton) <= 3:
            output.append(["ʾ", *skeleton])
    if script == "latin":
        for ending in FAN.LATIN_ENDINGS:
            if word.lower().endswith(ending) and len(word) - len(ending) >= 2:
                alternate = FAN.skeleton(word[:-len(ending)], script)
                if 2 <= len(alternate) <= 4 and alternate not in output:
                    output.append(alternate)
                break
        if len(skeleton) > 4:
            for alternate, _label in FAN.latin_stem_skeletons(word, script):
                if alternate not in output:
                    output.append(alternate)
    return output


def sound_route(word: str, script: str, root: str) -> str:
    table = FAN.FANS[script]
    for skeleton in source_skeletons(word, script):
        if not (2 <= len(skeleton) <= 4):
            continue
        options = [table.get(token, ()) for token in skeleton]
        if any(not option for option in options):
            continue
        for combo in itertools.product(*options):
            base = "".join(combo)
            alternatives = {base: "الصوامت كما خرجت من المروحة"}
            if len(base) == 2:
                a, b = base
                alternatives.update({
                    base + b: "باب المضاعف يكرر الصامت الأخير",
                    a + "و" + b: "باب المعتل يثبت الواو في الجوف",
                    a + "ي" + b: "باب المعتل يثبت الياء في الجوف",
                    a + "ا" + b: "باب المعتل يثبت الألف في الجوف",
                    base + "و": "باب المعتل يثبت الواو في الآخر",
                    base + "ي": "باب المعتل يثبت الياء في الآخر",
                    base + "ا": "باب المعتل يثبت الألف في الآخر",
                    "و" + base: "باب المعتل يثبت الواو في الأول",
                    "ي" + base: "باب المعتل يثبت الياء في الأول",
                })
            if root not in alternatives:
                continue
            pairs = "، ".join(
                f"{clean(token)}↔{arabic}" for token, arabic in zip(skeleton, combo)
            )
            initial = "؛ هيكل همزة البدء المضاف" if skeleton[:1] == ["ʾ"] else ""
            return f"{pairs}{initial}؛ {alternatives[root]}"
    return "صادر من المروحة المعلنة، وتعذر اختصار طريقه في سطر واحد"


def fan_review(row: dict[str, Any]) -> list[dict[str, Any]]:
    language = str(row["language"])
    script = str(CONFIG[language]["script"])
    word = str(row["spoken_romanization"])
    candidates = FAN.fan(word, script)
    ranked = FAN.rank(word, candidates, script)
    weights = {root: weight for root, weight in ranked}
    ordered = [root for root, _weight in ranked]
    for root in candidates:
        if root not in weights:
            ordered.append(root)
    return [{
        "root": root,
        "weight": float(weights.get(root, 0.0)),
        "sound_route": sound_route(word, script, root),
        "events": EVENT.all_tiers(root),
    } for root in ordered]


def select_manual_spec(row: dict[str, Any], review: list[dict[str, Any]]) -> tuple[dict[str, str] | None, dict[str, Any] | None]:
    for candidate in MANUAL_SPECS.get((str(row["language"]), str(row["branch"])), []):
        if candidate.get("gloss") and candidate["gloss"].casefold() not in str(row.get("gloss") or "").casefold():
            continue
        item = next((entry for entry in review if entry["root"] == candidate["root"]), None)
        if item and item["events"]:
            return candidate, item
    return None, None


def event_choice(item: dict[str, Any]) -> Any:
    """درجة الجذر أولا، ثم النواة للثنائي، ثم النزول، ثم المحاكم."""
    events = list(item["events"])
    preferred = (1, 2, 3, 4)
    return next(event for tier in preferred for event in events if event.tier == tier)


def lexicon_lines(row: dict[str, Any]) -> list[str]:
    entries = list(row["entries"])
    if not entries:
        return ["- قاموس الفرع: لم أجد مدخلة مطابقة في اللقطة، وهذا لا يصنع نفيا."]
    lines = ["- قاموس الفرع، جميع المداخل المطابقة للرسم:"]
    for index, entry in enumerate(entries):
        selected = " [المختارة بالسياق]" if index == row["selected_entry_index"] else ""
        lines.append(
            f"  - `{clean(entry.get('word'))}` /{clean(entry.get('read')) or 'بلا رومنة زائدة'}/، "
            f"{clean(entry.get('pos')) or 'بلا صنف'}، «{clean(entry.get('en'))}»؛ "
            f"الاشتقاق: «{clean(entry.get('etym')) or 'غير مكتوب'}»{selected}."
        )
    return lines


def event_lines(review: list[dict[str, Any]]) -> list[str]:
    lines: list[str] = []
    for item in review:
        if not item["events"]:
            continue
        lines.append(f"  - `{item['root']}`؛ طريق الصوت: {clean(item['sound_route'])}.")
        for event in item["events"]:
            note = f"؛ {clean(event.note)}" if event.note else ""
            lines.append(
                f"    - الدرجة {event.tier}، {clean(event.tier_ar)}: «{clean(event.text)}»؛ "
                f"المصدر: `{clean(event.source)}`{note}."
            )
    return lines or ["  - لا مرشحا في هذه المروحة له حدث متاح في درجات `all_tiers`."]


def witness_lines(review: list[dict[str, Any]], hits: dict[str, list[dict[str, Any]]]) -> list[str]:
    lines: list[str] = []
    for item in review:
        if not item["events"]:
            continue
        root = str(item["root"])
        matches = hits.get(root, [])
        lines.append(
            f"- شواهد الجذر `{root}` كاملة بعد `python scripts/search_arabic_root_senses.py "
            f"{root} --max-chars 0`، وعددها {len(matches)}:"
        )
        if not matches:
            lines.append("  - لا شاهد في الموارد المسماة؛ وهذا غياب مورد لا حكم معنى.")
            continue
        for match in matches:
            source_id = AR.canonical_source_id(str(match.get("source") or ""))
            source = AR.SOURCE_LABELS[source_id] if source_id else clean(match.get("source"))
            url = f"؛ الرابط: {clean(match.get('url'))}" if match.get("url") else ""
            lines.append(f"  - {source}: «{clean(match.get('definition'))}»{url}.")
    return lines


def build_card(
    row: dict[str, Any],
    review: list[dict[str, Any]],
    hits: dict[str, list[dict[str, Any]]],
) -> tuple[list[str], dict[str, Any]]:
    language = str(row["language"])
    cfg = CONFIG[language]
    card_id = f"PS-{cfg['id']}-{row['stage'].upper()}-{int(row['language_index']):05d}"
    selected = row["selected_entry"]
    etymology = str(selected.get("etym") or "")
    loan_closure, donor = named_branch_loan(language, etymology)
    manual, positive_item = select_manual_spec(row, review)
    if loan_closure:
        manual, positive_item = None, None

    fan_text = "؛ ".join(
        f"`{item['root']}`[و{item['weight']:.6f}،د"
        f"{'/'.join(str(event.tier) for event in item['events']) or '0'}]"
        for item in review
    ) or "خالية"
    lines = [
        f"### {card_id}: `{clean(row['branch'])}` /{clean(row['spoken_romanization'])}/",
        "",
        f"- الرومنة المنشورة: /{clean(row['published_romanization'])}/؛ والرومنة المقروءة: /{clean(row['spoken_romanization'])}/.",
        f"- طبقة المسح: `{row['stage']}`؛ ترتيبها العام {row['ordinal']}؛ الرسم الأصلي `{clean(row['branch'])}`.",
        *lexicon_lines(row),
        f"- ملاحظة الأصل المنشور: «{clean(etymology) or 'لا خبر اشتقاقيا مكتوبا'}»؛ قول Middle Persian أو Avestan أو Old Persian خبر طبقي لا يغلق المقابلة.",
        "- رجل الصوت:",
        f"  - استدعاء المروحة: `fan({clean(row['spoken_romanization'])}, {cfg['script']})`؛ الخط `{cfg['script']}` صريحا.",
        f"  - الهيكل أو هياكله: {', '.join('`' + clean(''.join(value)) + '`' for value in source_skeletons(str(row['spoken_romanization']), str(cfg['script'])))}.",
        f"  - المروحة كاملة، {len(review)} مرشحا: {fan_text}.",
        "- رجل الحدث من `frozen_event.all_tiers`:",
        *event_lines(review),
        "- رجل المعنى:",
        f"  - معنى قاموس الفرع المختار: «{clean(selected.get('en') or row.get('gloss'))}».",
        *witness_lines(review, hits),
    ]

    if loan_closure:
        orbit = (
            f"يسمي حقل الاشتقاق المانح `{clean(donor)}` واتجاهه إلى {cfg['label']}؛ "
            "فالاتحاد الصوتي والدلالي هنا أثر نقل مسمى لا صلة محسوبة."
        )
        closure = loan_closure
        positive_roots: list[str] = []
        selected_tier = 0
    elif manual and positive_item:
        chosen = event_choice(positive_item)
        orbit = str(manual["orbit"])
        closure = closure_for(str(manual["root"]))
        positive_roots = [str(manual["root"])]
        selected_tier = int(chosen.tier)
        lines.extend([
            f"- الجذر المختار: `{manual['root']}`؛ طريق الصوت: {clean(positive_item['sound_route'])}.",
            f"- الحدث المختار من المعروض، الدرجة {chosen.tier}: «{clean(chosen.text)}»؛ المصدر `{clean(chosen.source)}`.",
        ])
    else:
        best = clean(row.get("best")) or "لا مرشح مفرد"
        orbit = (
            f"قوبل معنى «{clean(selected.get('en') or row.get('gloss'))}» بالمروحة كلها، "
            f"ومنها المرشح الأول في المسح `{best}`، ثم قرئت أحداثها وشواهد جذورها كاملة؛ "
            "ولم أجد مدار حدث واحدا محكما يكفي لإصدار صلة."
        )
        closure = "OPEN-CANDIDATE"
        positive_roots = []
        selected_tier = 0

    lines.extend([
        f"- المدار المكتوب بالكلمات: {clean(orbit)}",
        f"- الحكم: `{closure}`" + ("؛ لا صلة صادرة." if closure not in {"ROOT-TRACE", "NUCLEUS-TRACE", "FLOOR-TRACE"} else "."),
        "",
    ])
    return lines, {
        "id": card_id,
        "ordinal": row["ordinal"],
        "stage": row["stage"],
        "language": language,
        "word": row["branch"],
        "published_romanization": row["published_romanization"],
        "spoken_romanization": row["spoken_romanization"],
        "script": cfg["script"],
        "closure": closure,
        "donor": donor,
        "positive_roots": positive_roots,
        "selected_event_tier": selected_tier,
        "fan_count": len(review),
        "event_root_count": sum(bool(item["events"]) for item in review),
        "full_arabic_witness_count": sum(len(hits.get(str(item["root"]), [])) for item in review if item["events"]),
    }


def baseline_module() -> types.ModuleType:
    source = subprocess.run(
        ["git", "show", f"{CONTROL_BASELINE}:scripts/fan_any_script.py"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    ).stdout
    module = types.ModuleType("fan_any_script_baseline")
    exec(compile(source, "fan_any_script_baseline", "exec"), module.__dict__)
    return module


def control_run() -> dict[str, list[dict[str, Any]]]:
    old = baseline_module()
    output: dict[str, list[dict[str, Any]]] = {}
    for language, specs in CONTROL_SPECS.items():
        script = str(CONFIG[language]["script"])
        rows = []
        for word, root, heading in specs:
            before = set(old.fan(word, script))
            after = set(FAN.fan(word, script))
            lost = sorted(before - after)
            if lost:
                raise AssertionError(f"ضابط الست فقد مرشحين في {language}:{word}: {lost}")
            events = EVENT.all_tiers(root)
            if not events:
                raise AssertionError(f"ضابط الست فقد الحدث في {language}:{root}")
            rows.append({
                "word": word,
                "root": root,
                "heading": heading,
                "baseline": CONTROL_BASELINE,
                "old_count": len(before),
                "new_count": len(after),
                "a_minus_b": lost,
                "b_minus_a": sorted(after - before),
                "event_tiers": [event.tier for event in events],
            })
        output[language] = rows
    return output


def audit_text(batch: int, rows: list[dict[str, Any]], outputs: list[dict[str, Any]], controls: dict[str, list[dict[str, Any]]]) -> str:
    stages = Counter(str(row["stage"]) for row in rows)
    languages = Counter(str(row["language"]) for row in rows)
    closures = Counter(str(row["closure"]) for row in outputs)
    lines = [
        f"# محضر بطاقات المسحين الفارسي والأكادي، الدفعة {batch:03d}",
        "",
        f"- التاريخ: {DATE}.",
        f"- نافذة الطابور: {rows[0]['ordinal']} إلى {rows[-1]['ordinal']}، وعددها {len(rows)}.",
        f"- الطبقات: شهادة مباشرة {stages['direct']}، بقية الصوت والمعنى {stages['both-rest']}، صوت وحده {stages['sound-only']}.",
        f"- الألسن: فارسية {languages['persian']}، أكادية {languages['akkadian']}.",
        "- الفارسية مررت رومنتها المقروءة إلى `latin`، والأكادية إلى `akkadian`.",
        "- كل حدث عرض من `frozen_event.all_tiers`، وكل شاهد عربي قرئ بـ`--max-chars 0`.",
        "- الصلات الصادرة الحية لم تمس؛ الصف الموافق لها حفظ `PROTECTED-S8` بلا بطاقة مكررة.",
        "",
        "## ضابط ست بطاقات صادرة في كل لسان",
        "",
    ]
    for language in ("persian", "akkadian"):
        lines.append(f"- {CONFIG[language]['label']}:")
        for item in controls[language]:
            lines.append(
                f"  - `{item['word']} ↔ {item['root']}` من {clean(item['heading'])}: "
                f"`a-b=∅`، والدرجات {','.join(str(value) for value in item['event_tiers'])}."
            )
    lines.extend(["", "## ما وجدته", ""])
    for closure, count in sorted(closures.items()):
        lines.append(f"- `{closure}`: {count}.")
    return "\n".join(lines) + "\n"


def harvest_batch(batch: int) -> dict[str, Any]:
    loaded = load_inputs()
    queue = queue_rows(loaded)
    windows = batch_windows(queue)
    if not 1 <= batch <= len(windows):
        raise SystemExit("الدفعة خارج الطابور ذي 1,580 صفا")
    rows = windows[batch - 1]
    marker = f"PHONETIC-SWEEP-PERSIAN-AKKADIAN-BATCH-{batch:03d}"
    manifest = DATA / f"phonetic-sweep-persian-akkadian-harvest-batch-{batch:03d}.json"
    audit = AUDITS / f"{DATE}-phonetic-sweep-persian-akkadian-harvest-batch-{batch:03d}.md"
    if manifest.exists() or audit.exists():
        raise AssertionError(f"مخرجات الدفعة {batch:03d} موجودة")

    controls = control_run()
    headings = {language: positive_headings(language) for language in CONFIG}
    for row in rows:
        row["prior_issued"] = prior_issued(row, headings)
        row["review"] = [] if row["prior_issued"] else fan_review(row)

    roots = {
        str(item["root"])
        for row in rows if not row["prior_issued"]
        for item in row["review"] if item["events"]
    }
    hits = AR.matches_for_roots(AR.DEFAULT_RESOURCES, roots, None)

    originals = {language: CONFIG[language]["reading"].read_text(encoding="utf-8") for language in CONFIG}
    sections = {
        language: [
            f"<!-- {marker}-{CONFIG[language]['id']}:START -->",
            "",
            f"## بطاقات المسح الصوتي، الدفعة {batch:03d}، {CONFIG[language]['label']} ({DATE})",
            "",
        ]
        for language in CONFIG
    }
    outputs: list[dict[str, Any]] = []
    written_counts = Counter()
    for row in rows:
        language = str(row["language"])
        if row["prior_issued"]:
            outputs.append({
                "id": f"PS-{CONFIG[language]['id']}-{row['stage'].upper()}-{int(row['language_index']):05d}",
                "ordinal": row["ordinal"],
                "stage": row["stage"],
                "language": language,
                "word": row["branch"],
                "published_romanization": row["published_romanization"],
                "spoken_romanization": row["spoken_romanization"],
                "script": CONFIG[language]["script"],
                "closure": "PROTECTED-S8",
                "positive_roots": [],
                "selected_event_tier": 0,
                "fan_count": 0,
                "event_root_count": 0,
                "full_arabic_witness_count": 0,
                "prior_issued": row["prior_issued"],
            })
            continue
        card_lines, output = build_card(row, row["review"], hits)
        sections[language].extend(card_lines)
        written_counts[language] += 1
        outputs.append(output)
    for language in CONFIG:
        sections[language].extend([f"<!-- {marker}-{CONFIG[language]['id']}:END -->", ""])

    for language, section in sections.items():
        path = CONFIG[language]["reading"]
        latest = path.read_text(encoding="utf-8")
        if latest != originals[language]:
            raise AssertionError(f"تغير ملف قراءة {language} أثناء بناء الدفعة")
        if not written_counts[language]:
            continue
        path.write_text(
            originals[language].rstrip() + "\n\n" + "\n".join(section),
            encoding="utf-8",
            newline="\n",
        )

    closures = Counter(str(row["closure"]) for row in outputs)
    payload = {
        "schema": "phonetic-sweep-persian-akkadian-harvest-v1",
        "date": DATE,
        "batch": batch,
        "batch_size": len(rows),
        "queue_start": rows[0]["ordinal"],
        "queue_end": rows[-1]["ordinal"],
        "controls": controls,
        "a_minus_b_nonempty": sum(bool(item["a_minus_b"]) for values in controls.values() for item in values),
        "stage_counts": dict(Counter(str(row["stage"]) for row in rows)),
        "language_counts": dict(Counter(str(row["language"]) for row in rows)),
        "closure_counts": dict(closures),
        "rows": outputs,
    }
    manifest.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    audit.write_text(audit_text(batch, rows, outputs, controls), encoding="utf-8", newline="\n")
    return payload


def refresh_akkadian_batch(batch: int) -> dict[str, Any]:
    """أعد بناء قسمنا الأكادي وحده بعد فتح باب صوتي إضافي.

    لا يعيد هذا المسار فحص الصلات الصادرة ولا يكتب بطاقة لصف محمي؛ بل يأخذ
    أحكام الحماية من محضر الدفعة الموجود، ويستبدل القسم المحصور بين وسمينا فقط.
    """
    loaded = load_inputs()
    queue = queue_rows(loaded)
    windows = batch_windows(queue)
    if not 1 <= batch <= len(windows):
        raise SystemExit("الدفعة خارج الطابور ذي 1,580 صفا")
    rows = windows[batch - 1]
    akkadian_rows = [row for row in rows if row["language"] == "akkadian"]
    if not akkadian_rows:
        raise AssertionError(f"لا قسم أكاديا في الدفعة {batch:03d}")

    marker = f"PHONETIC-SWEEP-PERSIAN-AKKADIAN-BATCH-{batch:03d}"
    manifest = DATA / f"phonetic-sweep-persian-akkadian-harvest-batch-{batch:03d}.json"
    audit = AUDITS / f"{DATE}-phonetic-sweep-persian-akkadian-harvest-batch-{batch:03d}.md"
    if not manifest.exists() or not audit.exists():
        raise AssertionError(f"مخرجات الدفعة {batch:03d} غير مكتملة")
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    old_by_id = {str(item["id"]): item for item in payload["rows"]}

    rebuilt_rows: list[dict[str, Any]] = []
    for row in akkadian_rows:
        card_id = f"PS-AKKADIAN-{row['stage'].upper()}-{int(row['language_index']):05d}"
        old = old_by_id[card_id]
        if old["closure"] == "PROTECTED-S8":
            continue
        row["review"] = fan_review(row)
        rebuilt_rows.append(row)

    roots = {
        str(item["root"])
        for row in rebuilt_rows
        for item in row["review"] if item["events"]
    }
    hits = AR.matches_for_roots(AR.DEFAULT_RESOURCES, roots, None)
    section = [
        f"<!-- {marker}-AKKADIAN:START -->",
        "",
        f"## بطاقات المسح الصوتي، الدفعة {batch:03d}، الأكادية ({DATE})",
        "",
    ]
    replacements: dict[str, dict[str, Any]] = {}
    for row in rebuilt_rows:
        card_lines, output = build_card(row, row["review"], hits)
        old = old_by_id[str(output["id"])]
        if output["closure"] != old["closure"] or output["positive_roots"] != old["positive_roots"]:
            raise AssertionError(f"تغير حكم البطاقة عند فتح الباب: {output['id']}")
        section.extend(card_lines)
        replacements[str(output["id"])] = output
    section.extend([f"<!-- {marker}-AKKADIAN:END -->", ""])

    reading = CONFIG["akkadian"]["reading"]
    original = reading.read_text(encoding="utf-8")
    start = f"<!-- {marker}-AKKADIAN:START -->"
    end = f"<!-- {marker}-AKKADIAN:END -->"
    pattern = re.compile(re.escape(start) + r".*?" + re.escape(end) + r"\n?", re.S)
    replacement = "\n".join(section)
    refreshed, count = pattern.subn(lambda _match: replacement, original)
    if count != 1:
        raise AssertionError(f"عدد أقسام الأكادية في الدفعة {batch:03d}: {count}")

    controls = control_run()
    outputs = [replacements.get(str(item["id"]), item) for item in payload["rows"]]
    payload["controls"] = controls
    payload["a_minus_b_nonempty"] = sum(
        bool(item["a_minus_b"]) for values in controls.values() for item in values
    )
    payload["closure_counts"] = dict(Counter(str(item["closure"]) for item in outputs))
    payload["rows"] = outputs
    reading.write_text(refreshed, encoding="utf-8", newline="\n")
    manifest.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    audit.write_text(audit_text(batch, rows, outputs, controls), encoding="utf-8", newline="\n")
    return payload


def plan_payload() -> dict[str, Any]:
    loaded = load_inputs()
    queue = queue_rows(loaded)
    windows = batch_windows(queue)
    return {
        "schema": "phonetic-sweep-persian-akkadian-plan-v1",
        "total": len(queue),
        "direct": sum(row["stage"] == "direct" for row in queue),
        "both_rest": sum(row["stage"] == "both-rest" for row in queue),
        "sound_only": sum(row["stage"] == "sound-only" for row in queue),
        "batches": len(windows),
        "batch_windows": [
            {
                "batch": index + 1,
                "start": rows[0]["ordinal"],
                "end": rows[-1]["ordinal"],
                "stages": dict(Counter(row["stage"] for row in rows)),
                "languages": dict(Counter(row["language"] for row in rows)),
            }
            for index, rows in enumerate(windows)
        ],
    }


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", action="store_true")
    parser.add_argument("--batch", type=int)
    parser.add_argument("--refresh-akkadian-batch", type=int)
    args = parser.parse_args()
    if args.plan:
        print(json.dumps(plan_payload(), ensure_ascii=False, indent=2))
        return 0
    if args.refresh_akkadian_batch is not None:
        payload = refresh_akkadian_batch(args.refresh_akkadian_batch)
        print(json.dumps({key: value for key, value in payload.items() if key not in {"rows", "controls"}}, ensure_ascii=False))
        return 0
    if args.batch is None:
        raise SystemExit("اختر --plan أو --batch N أو --refresh-akkadian-batch N")
    payload = harvest_batch(args.batch)
    print(json.dumps({key: value for key, value in payload.items() if key not in {"rows", "controls"}}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
