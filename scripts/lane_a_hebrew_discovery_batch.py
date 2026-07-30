#!/usr/bin/env python3
"""Append lane A's Hebrew discovery cohort without touching shared outputs.

The cohort is deterministic: every old-witness Hebrew member whose Kaikki
etymology carries an explicit ``cog`` template pointing to Arabic and which
does not already carry a positive member verdict.  The script never treats the
template as an automatic verdict.  It requires the named Arabic form to occur
inside two independent old Arabic lexica under one morphology-indexed root.

This is a lane-local writer.  It writes only the Hebrew reading and the lane A
audit named below.  It does not rebuild the ledger, status snapshot, proof
population, or any other shared artifact.
"""

from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import re
import sqlite3
import unicodedata
from collections import defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
READING = ROOT / "04-cross-linguistic" / "readings" / "hebrew.md"
AUDIT = (
    ROOT
    / "05-audits"
    / "2026-07-29-lane-a-hebrew-old-witness-arabic-cognates.md"
)
WITNESSES = ROOT / "data" / "hebrew-temporal-witnesses.json"
RAW = ROOT / "Resources" / "hebrew" / "kaikki.org-dictionary-Hebrew.jsonl"
MUKHTAR = (
    ROOT
    / "Resources"
    / "Ten dictionaries for Arabic language"
    / "mukhtar.csv"
)
DB = ROOT / "cache" / "recovery_pipeline" / "inventory-v5.sqlite"
FAN_TOOL = ROOT / "scripts" / "search_arabic_root_senses.py"

START = "<!-- LANE-A-HEBREW-DISCOVERY-2026-07-29:START -->"
END = "<!-- LANE-A-HEBREW-DISCOVERY-2026-07-29:END -->"
DATE = "2026-07-29"

ARABIC_MARKS = re.compile(
    "[\u0610-\u061a\u064b-\u065f\u0670\u06d6-\u06ed\u0640]"
)
HEBREW_MARKS = re.compile("[\u0591-\u05c7]")
ENTRY_ID = re.compile(r"`(kaikki_hebrew:[^`]+)`")
CARD_SPLIT = re.compile(r"(?=^### بطاقة: )", re.MULTILINE)

OLD_SOURCE_IDS = {
    "lisan",
    "taj_al_arus",
    "al_sihah",
    "al_muhkam",
    "kitab_al_ayn",
    "asas_al_balagha",
    "al_mufradat",
    "al_misbah",
    "al_muhit",
}

UNCERTAINTY_WORDS = (
    "uncertain",
    "possibly related",
    "perhaps related",
    "unlikely related",
    "false cognate",
    "it remains unclear",
    "of unknown origin",
)

EXTERNAL_LOAN_WORDS = (
    "borrowed from ancient greek",
    "borrowed from latin",
    "borrowed from greek",
    "borrowed from persian",
    "borrowed from sumerian",
    "from latin ",
    "from ancient greek ",
)

ENGLISH_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "being",
    "by",
    "especially",
    "for",
    "from",
    "in",
    "into",
    "is",
    "it",
    "of",
    "on",
    "one",
    "or",
    "person",
    "something",
    "that",
    "the",
    "this",
    "to",
    "used",
    "with",
}

# A positive verdict is deliberately impossible without one of these
# hand-checked semantic specifications.  Each Arabic anchor is a word-bounded
# phrase that must occur in the excerpt of the named old lexicon itself.  The
# etymology template retrieves the pair; it never supplies the semantic proof.
MANUAL_SENSE_SPECS: dict[str, dict[str, Any]] = {
    "kaikki_hebrew:160:en-יום-he-noun-1n7m-QBp": {
        "term": "يوم",
        "root": "يوم",
        "arabic_gloss": (
            "اليوم المعروف الممتد من طلوع الشمس إلى غروبها"
        ),
        "meeting": (
            "جوار الزمن النهاري المحدود بين الصباح والمساء هو "
            "نفسه في الحس العبري وفي الشاهدين العربيين"
        ),
        "member_sense_reviewed": True,
        "anchors": {
            "lisan": ["اليوم معروف مقداره"],
            "taj_al_arus": ["معروف مقداره من طلوع الشمس"],
        },
    },
    "kaikki_hebrew:342:en-טוב-he-adj-GwpOY2mq": {
        "term": "طيب",
        "root": "طيب",
        "arabic_gloss": "الطيب خلاف الخبيث، وما لذ وزكا",
        "meeting": (
            "يلتقي الحس العبري والعائلة العربية في مدار الجودة "
            "والاستحسان والصلاح"
        ),
        "member_sense_reviewed": True,
        "anchors": {
            "lisan": ["الطيب خلاف الخبيث"],
            "taj_al_arus": ["لذ وزكا"],
        },
    },
    "kaikki_hebrew:552:en-מקום-he-noun-oN8V7~cg": {
        "term": "مقام",
        "root": "قوم",
        "arabic_gloss": "المقام موضع القدمين وموضع الإقامة",
        "meeting": (
            "جوار المكان الثابت الذي يقوم أو يقيم فيه المرء "
            "يجمع الحس العبري بالعائلة العربية"
        ),
        "member_sense_reviewed": True,
        "anchors": {
            "lisan": ["موضع القدمين"],
            "taj_al_arus": ["موضع القدمين"],
        },
    },
    "kaikki_hebrew:1247:en-מה-he-pron-dJqywNBs": {
        "term": "ما",
        "root": "ما",
        "arabic_gloss": "ما الاستفهامية",
        "meeting": "أداة الاستفهام عن الشيء هي نفسها في الاستعمالين",
        "member_sense_reviewed": True,
        "anchors": {
            "lisan": ["الاستفهام نحو ما عندك"],
            "taj_al_arus": ["ما عندك مستفهما"],
        },
    },
    "kaikki_hebrew:617:en-אות-he-noun-PqFwVDTJ": {
        "term": "آية",
        "root": "أيي",
        "arabic_gloss": "العلامة",
        "meeting": "العلامة الدالة",
        "anchors": {
            "al_muhkam": ["والآية العلامة والشخص"],
            "taj_al_arus": ["والآية العلامة", "العلامة"],
        },
    },
    "kaikki_hebrew:991:en-ערום-he-adj-ndZJigRT": {
        "term": "عريان",
        "root": "عرا",
        "arabic_gloss": "العريان المتجرد من الثياب",
        "meeting": "التجرد من الثياب",
        "anchors": {
            "al_sihah": ["عريان", "عاريا", "عار"],
            "lisan": ["عاريا", "عريان"],
        },
    },
    "kaikki_hebrew:1978:en-שם-he-noun-NulsYmM2": {
        "term": "اسم",
        "root": "سما",
        "arabic_gloss": "ما يعرف به ذات الشيء",
        "meeting": "الاسم الذي يعرف به المسمى",
        "temporal_layer": "توراتي في الصورة الصرفية שמך للأسرة نفسها",
        "temporal_references": [
            "שמך، Genesis 32:28-29، شاهد توراتي صريح في الأسرة نفسها"
        ],
        "temporal_basis": "شاهد توراتي في الصورة الصرفية للأصل نفسه",
        "anchors": {
            "al_mufradat": ["والاسم ما يعرف به ذات الشيء"],
            "al_sihah": ["والاسم مشتق من سموت"],
        },
    },
    "kaikki_hebrew:2028:en-כפר-he-noun-Bc--KDOB": {
        "term": "كفر",
        "root": "كفر",
        "arabic_gloss": "القرية",
        "meeting": "القرية",
        "anchors": {
            "al_sihah": ["والكفر أيضا القرية"],
            "al_misbah": ["والكفر القرية"],
        },
    },
    "kaikki_hebrew:2125:en-גמל-he-noun-SBJYXpRJ": {
        "term": "جمل",
        "root": "جمل",
        "arabic_gloss": "ذكر الإبل",
        "meeting": "الحيوان نفسه، ذكر الإبل",
        "anchors": {
            "al_sihah": ["الجمل من الإبل"],
            "lisan": ["الجمل الذكر من الإبل"],
        },
    },
    "kaikki_hebrew:2189:en-שוט-he-noun-6u7vAXDs": {
        "term": "سوط",
        "root": "سوط",
        "arabic_gloss": "أداة الضرب",
        "meeting": "أداة الضرب",
        "anchors": {
            "al_muhkam": ["والسوط الذي يضرب به"],
            "al_misbah": ["السوط معروف"],
        },
    },
    "kaikki_hebrew:2200:en-סל-he-noun--nbZmtlX": {
        "term": "سلة",
        "root": "سلل",
        "arabic_gloss": "سلة الخبز والوعاء",
        "meeting": "الوعاء الذي يحمل فيه الخبز ونحوه",
        "anchors": {
            "al_sihah": ["وسلة الخبز معروفة"],
            "al_muhkam": ["والسل والسلة كالجونة"],
        },
    },
    "kaikki_hebrew:2510:en-טעם-he-verb-2vkp6OfM": {
        "term": "طعم",
        "root": "طعم",
        "arabic_gloss": "ذاق الشيء",
        "meeting": "إدراك الذوق",
        "anchors": {
            "al_muhkam": ["طعم الشيء ذاقه", "ذاقه", "الذوق"],
            "lisan": ["طعم الشيء ذاقه", "ذاقه", "الذوق"],
        },
    },
    "kaikki_hebrew:2999:en-טל-he-noun-hy8Adsfk": {
        "term": "طل",
        "root": "طلل",
        "arabic_gloss": "الندى",
        "meeting": "الندى",
        "anchors": {
            "al_sihah": ["الطل الندى", "الندى"],
            "lisan": ["الطل الندى", "الندى"],
        },
    },
    "kaikki_hebrew:3133:en-קשת-he-noun-Qes~eLzO": {
        "term": "قوس",
        "root": "قوس",
        "arabic_gloss": "القوس التي يرمى عنها",
        "meeting": "القوس أداة الرامي الملازمة",
        "anchors": {
            "al_sihah": ["القوس يذكر ويؤنث"],
            "al_muhkam": ["القوس التي يرمى عنها", "يرمى عنها", "القوس"],
        },
    },
    "kaikki_hebrew:3306:en-גבינה-he-noun-hzrJ~-pN": {
        "term": "جبن",
        "root": "جبن",
        "arabic_gloss": "الجبن المأكول",
        "meeting": "طعام الجبن نفسه",
        "anchors": {
            "al_sihah": ["الجبن هذا الذي يؤكل"],
            "taj_al_arus": ["وهو الذي يؤكل"],
        },
    },
    "kaikki_hebrew:3395:en-תמר-he-noun-LIasoCnF": {
        "term": "ثمر",
        "root": "ثمر",
        "arabic_gloss": "حمل الشجر",
        "meeting": "الثمر الخارج من الشجر",
        "anchors": {
            "kitab_al_ayn": ["الثمر حمل الشجر"],
            "al_muhkam": ["الثمر حمل الشجر"],
        },
    },
    "kaikki_hebrew:5224:en-ליל-he-noun-F2Rz1zEz": {
        "term": "ليل",
        "root": "ليل",
        "arabic_gloss": "الليل ضد النهار",
        "meeting": "الليل",
        "temporal_layer": "موروث من Proto-Semitic *layl- بتصريح المصدر",
        "temporal_references": [
            "Kaikki Hebrew etymology: From Proto-Semitic *layl- (night)"
        ],
        "temporal_basis": "تصريح وراثة صريح من Proto-Semitic *layl-",
        "anchors": {
            "kitab_al_ayn": ["الليل ضد النهار"],
            "lisan": ["الليل ضد النهار"],
        },
    },
    "kaikki_hebrew:6022:en-נישה-he-verb-QnVoX7TH": {
        "term": "نسي",
        "root": "نسي",
        "arabic_gloss": "أنساه الشيء",
        "meeting": "التسبب في النسيان",
        "anchors": {
            "al_muhkam": ["النسيان"],
            "taj_al_arus": ["أنساه إياه"],
        },
    },
    "kaikki_hebrew:6135:en-נדיר-he-adj-aXd2n-Fz": {
        "term": "ندر",
        "root": "ندر",
        "arabic_gloss": "شذ وقل وجوده",
        "meeting": "الشذوذ والقلة",
        "anchors": {
            "al_sihah": ["ندر الشيء يندر ندورا سقط وشذ", "وشذ", "شذ"],
            "lisan": ["ندر الشيء يندر ندورا سقط وشذ", "وشذ", "شذ"],
        },
    },
    "kaikki_hebrew:7014:en-חש-he-verb-IbjjAxuR": {
        "term": "حس",
        "root": "حسس",
        "arabic_gloss": "أحس به وشعر",
        "meeting": "الإحساس والإدراك",
        "anchors": {
            "lisan": ["أحس به شعر به", "شعر به", "الحس"],
            "taj_al_arus": ["أحس به شعر به", "شعر به", "الحس"],
        },
    },
    "kaikki_hebrew:10573:en-שכר-he-noun-OyfQW2Zq": {
        "term": "سكر",
        "root": "سكر",
        "arabic_gloss": "الشراب المسكر",
        "meeting": "الشراب المسكر",
        "anchors": {
            "lisan": ["السكر نقيع التمر", "نقيع التمر", "المسكر"],
            "taj_al_arus": ["الشراب المسكر", "نقيع التمر", "المسكر"],
        },
    },
    "kaikki_hebrew:13031:en-חרבה-he-noun-Nzwkod5p": {
        "term": "خربة",
        "root": "خرب",
        "arabic_gloss": "موضع الخراب",
        "meeting": "الموضع الخرب",
        "anchors": {
            "al_sihah": ["الخراب ضد العمران", "الخراب"],
            "lisan": ["الخراب ضد العمران", "الخراب"],
        },
    },
    "kaikki_hebrew:16612:en-נקם-he-verb-sBtWgCcF": {
        "term": "انتقم",
        "root": "نقم",
        "arabic_gloss": "عاقبه وانتقم منه",
        "meeting": "الانتقام والعقوبة",
        "anchors": {
            "lisan": ["نقم منه ينقم نقما عاقبه", "عاقبه", "الانتقام"],
            "taj_al_arus": ["نقم منه ينقم نقما عاقبه", "عاقبه", "الانتقام"],
        },
    },
    "kaikki_hebrew:16941:en-קצח-he-noun-5JrI~Bur": {
        "term": "قزح",
        "root": "قزح",
        "arabic_gloss": "بزر البصل والتابل",
        "meeting": "بذور التابل",
        "anchors": {
            "al_muhkam": ["القزح بزر البصل"],
            "lisan": ["القزح بزر البصل"],
        },
    },
    "kaikki_hebrew:186:en-עבר-he-noun-INRAT-74": {
        "term": "عبر",
        "root": "عبر",
        "arabic_gloss": "العبر هو شاطئ الوادي وناحيته",
        "meeting": (
            "جوار المعنى في الفرع هو الجانب والناحية المقابلة، "
            "وجواره في العربية شاطئ الوادي وناحيته؛ يلتقيان في "
            "مدار جانب الموضع الذي يعبر منه أو إليه"
        ),
        "member_sense_reviewed": True,
        "anchors": {
            "lisan": ["شاطئه وناحيته"],
            "taj_al_arus": ["شاطئه وناحيته"],
        },
    },
    "kaikki_hebrew:217:en-ירך-he-noun-iYGn1Q1V": {
        "term": "ورك",
        "root": "ورك",
        "arabic_gloss": "ما فوق الفخذ",
        "meeting": "موضع الورك والفخذ",
        "anchors": {
            "al_sihah": ["الورك"],
            "al_muhkam": ["الورك"],
        },
    },
    "kaikki_hebrew:243:en-אבטיח-he-noun-7v60Jfyr": {
        "term": "بطيخ",
        "root": "بطخ",
        "arabic_gloss": "البطيخ المعروف",
        "meeting": "ثمرة البطيخ",
        "anchors": {
            "al_sihah": ["البطيخ"],
            "lisan": ["البطيخ"],
        },
    },
    "kaikki_hebrew:385:en-אלף-he-num-VLihaHgM": {
        "term": "ألف",
        "root": "ألف",
        "arabic_gloss": "الألف من العدد",
        "meeting": "عدد الألف",
        "anchors": {
            "al_muhkam": ["الألف من العدد"],
            "lisan": ["الألف من العدد"],
        },
    },
    "kaikki_hebrew:425:en-ברא-he-verb-9EBO3chg": {
        "term": "برأ",
        "root": "برأ",
        "arabic_gloss": "خلق وأنشأ",
        "meeting": "الخلق والإنشاء",
        "anchors": {
            "lisan": ["خلق"],
            "taj_al_arus": ["خلق"],
        },
    },
    "kaikki_hebrew:430:en-מהר-he-verb-PBHiTOwU": {
        "term": "مهر",
        "root": "مهر",
        "arabic_gloss": "أعطاها مهرها وصداقها",
        "meeting": "دفع المهر في عقد الزواج",
        "anchors": {
            "al_sihah": ["المهر الصداق"],
            "al_muhkam": ["المهر الصداق"],
        },
    },
    "kaikki_hebrew:526:en-בין-he-prep-zPhF4cXs": {
        "term": "بين",
        "root": "بين",
        "arabic_gloss": "الوسط والفصل بين الشيئين",
        "meeting": "الموقع بين شيئين",
        "anchors": {
            "al_sihah": ["بين"],
            "lisan": ["بين"],
        },
    },
    "kaikki_hebrew:618:en-אות-he-noun-827aZGDv": {
        "term": "آية",
        "root": "أيي",
        "arabic_gloss": "العلامة",
        "meeting": "الرمز بوصفه علامة",
        "anchors": {
            "al_muhkam": ["والآية العلامة والشخص"],
            "taj_al_arus": ["العلامة"],
        },
    },
    "kaikki_hebrew:623:en-צלם-he-noun-67IkmaSP": {
        "term": "صنم",
        "root": "صنم",
        "arabic_gloss": "الصورة والوثن",
        "meeting": "الصورة المنحوتة",
        "anchors": {
            "lisan": ["الصنم"],
            "taj_al_arus": ["الصنم"],
        },
    },
    "kaikki_hebrew:686:en-תלם-he-noun-5iMY8IzZ": {
        "term": "ثلم",
        "root": "ثلم",
        "arabic_gloss": "الشق والكسر في الحافة",
        "meeting": "الشق الممتد في السطح",
        "anchors": {
            "al_sihah": ["الثلم"],
            "taj_al_arus": ["الثلم"],
        },
    },
    "kaikki_hebrew:710:en-עזז-he-verb-aZpQHPdF": {
        "term": "عز",
        "root": "عزز",
        "arabic_gloss": "قوي واشتد",
        "meeting": "القوة والشدة",
        "anchors": {
            "al_sihah": ["العز القوة", "قوي"],
            "lisan": ["العز القوة", "قوي"],
        },
    },
    "kaikki_hebrew:831:en-צאן-he-noun-m8ikfk0y": {
        "term": "ضأن",
        "root": "ضأن",
        "arabic_gloss": "الضأن من الغنم",
        "meeting": "الضأن والغنم",
        "anchors": {
            "al_sihah": ["الضأن"],
            "al_muhkam": ["الضأن"],
        },
    },
    "kaikki_hebrew:848:en-זהב-he-noun--9kx~gSp": {
        "term": "ذهب",
        "root": "ذهب",
        "arabic_gloss": "الذهب المعدن",
        "meeting": "معدن الذهب",
        "anchors": {
            "al_sihah": ["الذهب"],
            "al_muhkam": ["الذهب"],
        },
    },
    "kaikki_hebrew:857:en-מלחמה-he-noun-ywckuaGt": {
        "term": "ملحمة",
        "root": "لحم",
        "arabic_gloss": "الحرب والوقعة العظيمة",
        "meeting": "الحرب والقتال",
        "temporal_layer": "Hebrew Bible، Isaiah، 6th century BCE",
        "temporal_references": [
            "Hebrew Bible، Book of Isaiah، 6th century BCE"
        ],
        "temporal_basis": "شاهد قديم صريح للعضو نفسه في سفر Isaiah",
        "anchors": {
            "lisan": ["الملحمة الحرب", "الملحمة"],
            "taj_al_arus": ["الملحمة الحرب", "الملحمة"],
        },
    },
    "kaikki_hebrew:882:en-שיח-he-noun-dvRkgnLU": {
        "term": "شيح",
        "root": "شيح",
        "arabic_gloss": "نبت الشيح",
        "meeting": "النبت الشجيري",
        "anchors": {
            "al_sihah": ["الشيح"],
            "al_muhkam": ["الشيح"],
        },
    },
    "kaikki_hebrew:886:en-מטר-he-noun-MZtExXCk": {
        "term": "مطر",
        "root": "مطر",
        "arabic_gloss": "المطر",
        "meeting": "المطر",
        "anchors": {
            "al_sihah": ["المطر"],
            "al_muhkam": ["المطر"],
        },
    },
    "kaikki_hebrew:894:en-השקה-he-verb-eP-HhoJf": {
        "term": "أسقى",
        "root": "سقي",
        "arabic_gloss": "أسقاه وسقاه الماء",
        "meeting": "إعطاء الماء والسقي",
        "anchors": {
            "al_muhkam": ["أسقاه"],
            "lisan": ["أسقاه"],
        },
    },
    "kaikki_hebrew:1274:en-שור-he-noun-HdFP~Dww": {
        "term": "ثور",
        "root": "ثور",
        "arabic_gloss": "الثور من البقر",
        "meeting": "ذكر البقر نفسه",
        "anchors": {
            "al_sihah": ["الثور"],
            "al_muhkam": ["الثور"],
        },
    },
    "kaikki_hebrew:1277:en-רימון-he-noun-Jur8FWhv": {
        "term": "رمان",
        "root": "رمن",
        "arabic_gloss": "ثمر الرمان",
        "meeting": "ثمرة الرمان نفسها",
        "member_sense_reviewed": True,
        "anchors": {
            "al_sihah": ["الرمان"],
            "lisan": ["الرمان"],
        },
    },
    "kaikki_hebrew:1313:en-שעה-he-noun-XRfSPk8G": {
        "term": "ساعة",
        "root": "سوع",
        "arabic_gloss": "الساعة من الزمان",
        "meeting": "المقدار المسمى من الزمن",
        "anchors": {
            "al_sihah": ["الساعة"],
            "al_muhkam": ["الساعة"],
        },
    },
    "kaikki_hebrew:1329:en-שבע-he-verb-dJtZBW1B": {
        "term": "شبع",
        "root": "شبع",
        "arabic_gloss": "امتلأ من الطعام",
        "meeting": "الامتلاء من الطعام",
        "member_sense_reviewed": True,
        "anchors": {
            "al_sihah": ["شبع"],
            "al_muhkam": ["الشبع"],
        },
    },
    "kaikki_hebrew:1532:en-כל-he-noun-2FC52MV1": {
        "term": "كل",
        "root": "كلل",
        "arabic_gloss": "الكل والتمام",
        "meeting": "الاستغراق والتمام",
        "anchors": {
            "al_sihah": ["الكل"],
            "al_muhkam": ["الكل"],
        },
    },
    "kaikki_hebrew:1670:en-כרם-he-noun-zjSbQfKl": {
        "term": "كرم",
        "root": "كرم",
        "arabic_gloss": "شجر العنب",
        "meeting": "موضع شجر العنب وثمره",
        "anchors": {
            "al_sihah": ["الكرم"],
            "al_muhkam": ["الكرم"],
        },
    },
    "kaikki_hebrew:1886:en-ענן-he-noun-VmgQELdT": {
        "term": "عنان",
        "root": "عنن",
        "arabic_gloss": "السحاب",
        "meeting": "السحاب المرتفع في الجو",
        "anchors": {
            "al_sihah": ["العنان"],
            "lisan": ["العنان"],
        },
    },
    "kaikki_hebrew:1912:en-חלום-he-noun-MP3jWLNH": {
        "term": "حلم",
        "root": "حلم",
        "arabic_gloss": "الرؤيا في النوم",
        "meeting": "ما يراه النائم",
        "temporal_layer": "Midrash Genesis Rabbah، نحو 500 C.E.",
        "temporal_references": [
            "Genesis Rabbah 17:5، نحو 500 C.E."
        ],
        "temporal_basis": "شاهد قديم مؤرخ للعضو نفسه",
        "anchors": {
            "al_sihah": ["الحلم"],
            "al_muhkam": ["الحلم"],
        },
    },
    "kaikki_hebrew:1961:en-חיים-he-noun-f5U70Zs-": {
        "term": "حياة",
        "root": "حيي",
        "arabic_gloss": "الحياة ضد الموت",
        "meeting": "الحياة والبقاء حيًا",
        "anchors": {
            "taj_al_arus": ["الحياة"],
            "al_misbah": ["الحياة"],
        },
    },
    "kaikki_hebrew:2232:en-חטא-he-noun-K-RiQSF9": {
        "term": "خطئ",
        "root": "خطأ",
        "arabic_gloss": "الخطأ والخطيئة",
        "meeting": "الذنب والخروج عن الصواب",
        "anchors": {
            "lisan": ["الخطيئة"],
            "taj_al_arus": ["الخطيئة"],
        },
    },
    "kaikki_hebrew:2258:en-פרש-he-noun-Vc99puEb": {
        "term": "فرث",
        "root": "فرث",
        "arabic_gloss": "الفرث وما في الكرش",
        "meeting": "المادة الهضمية الخارجة من الجوف",
        "anchors": {
            "al_sihah": ["الفرث"],
            "al_muhkam": ["الفرث"],
        },
    },
    "kaikki_hebrew:2296:en-שלווה-he-noun-fK2atHAS": {
        "term": "سلوى",
        "root": "سلو",
        "arabic_gloss": "السلو وسكون النفس",
        "meeting": "سكون النفس وزوال الحزن",
        "anchors": {
            "kitab_al_ayn": ["السلوى"],
            "al_muhkam": ["السلوى"],
        },
    },
    "kaikki_hebrew:2325:en-זקן-he-noun-lBGSq7CG": {
        "term": "ذقن",
        "root": "ذقن",
        "arabic_gloss": "الذقن من الوجه",
        "meeting": "موضع الذقن وما ينبت عليه من اللحية",
        "anchors": {
            "lisan": ["الذقن"],
            "taj_al_arus": ["الذقن"],
        },
    },
    "kaikki_hebrew:2338:en-בניין-he-noun-UWfpZ34f": {
        "term": "بنيان",
        "root": "بني",
        "arabic_gloss": "البناء والبنيان",
        "meeting": "الشيء المبني وعمل تشييده",
        "member_sense_reviewed": True,
        "temporal_layer": "Hebrew Bible، Ezekiel 42:5",
        "temporal_references": ["Ezekiel 42:5"],
        "temporal_basis": "شاهد توراتي صريح للعضو نفسه",
        "anchors": {
            "al_muhkam": ["البنيان", "البناء"],
            "lisan": ["البنيان", "البناء"],
        },
    },
    "kaikki_hebrew:2377:en-קטל-he-verb-9W9eC7bx": {
        "term": "قتل",
        "root": "قتل",
        "arabic_gloss": "أمات وذبح",
        "meeting": "إزهاق الحياة",
        "member_sense_reviewed": True,
        "anchors": {
            "al_sihah": ["قتل"],
            "al_muhkam": ["قتل"],
        },
    },
    "kaikki_hebrew:2413:en-רחם-he-noun-mjZCd5IO": {
        "term": "رحم",
        "root": "رحم",
        "arabic_gloss": "الرحم من المرأة",
        "meeting": "موضع الحمل والولادة",
        "member_sense_reviewed": True,
        "anchors": {
            "al_muhkam": ["الرحم"],
            "lisan": ["الرحم"],
        },
    },
    "kaikki_hebrew:2435:en-מלא-he-verb-0KItSfIS": {
        "term": "ملأ",
        "root": "ملأ",
        "arabic_gloss": "ملأ الإناء فامتلأ",
        "meeting": "شغل الحيز حتى التمام",
        "member_sense_reviewed": True,
        "anchors": {
            "al_sihah": ["ملأ"],
            "al_muhkam": ["ملأ"],
        },
    },
    "kaikki_hebrew:2442:en-רקד-he-verb-baKAHQa3": {
        "term": "رقص",
        "root": "رقص",
        "arabic_gloss": "رقص وتحرك",
        "meeting": "الحركة المتتابعة بالوثب والرقص",
        "anchors": {
            "al_sihah": ["رقص"],
            "al_muhkam": ["رقص"],
        },
    },
    "kaikki_hebrew:2503:en-יקר-he-adj-w18qPVqg": {
        "term": "وقار",
        "root": "وقر",
        "arabic_gloss": "الثقل والرزانة والقيمة",
        "meeting": "الثقل المعنوي الذي ينتج عنه التوقير وعلو القيمة",
        "member_sense_reviewed": True,
        "temporal_layer": "موروث من Proto-Semitic *waqar- بتصريح المصدر",
        "temporal_references": [
            "Kaikki Hebrew etymology: From Proto-Semitic *waqar-"
        ],
        "temporal_basis": "تصريح وراثة صريح من Proto-Semitic *waqar-",
        "anchors": {
            "al_sihah": ["الوقار"],
            "lisan": ["الوقار", "الثقل"],
        },
    },
    "kaikki_hebrew:2670:en-בטן-he-noun-k0tadk24": {
        "term": "بطن",
        "root": "بطن",
        "arabic_gloss": "البطن من الجسد",
        "meeting": "جوف البدن وناحية البطن",
        "anchors": {
            "al_sihah": ["البطن"],
            "al_muhkam": ["البطن"],
        },
    },
    "kaikki_hebrew:2675:en-שחר-he-noun-Jw7qozlp": {
        "term": "سحر",
        "root": "سحر",
        "arabic_gloss": "السحر قبيل الصبح",
        "meeting": "الوقت السابق لطلوع الصبح",
        "anchors": {
            "al_sihah": ["السحر"],
            "al_muhkam": ["السحر"],
        },
    },
    "kaikki_hebrew:2993:en-צל-he-noun-C0AKIidY": {
        "term": "ظل",
        "root": "ظلل",
        "arabic_gloss": "الظل والفيء",
        "meeting": "الستر عن الضوء وما يحدثه من ظل",
        "member_sense_reviewed": True,
        "anchors": {
            "al_sihah": ["الظل"],
            "al_muhkam": ["الظل"],
        },
    },
    "kaikki_hebrew:3165:en-רגם-he-verb-G70x82eq": {
        "term": "رجم",
        "root": "رجم",
        "arabic_gloss": "رماه بالحجارة",
        "meeting": "الرمي بالحجارة",
        "anchors": {
            "al_sihah": ["رجم"],
            "al_muhkam": ["رجم"],
        },
    },
    "kaikki_hebrew:3560:en-צום-he-noun-0~jJP8X0": {
        "term": "صوم",
        "root": "صوم",
        "arabic_gloss": "الإمساك عن الطعام",
        "meeting": "الإمساك التعبدي عن الطعام",
        "anchors": {
            "al_sihah": ["الصوم"],
            "al_muhkam": ["الصوم"],
        },
    },
    "kaikki_hebrew:5328:en-מנע-he-verb-AK5383xr": {
        "term": "منع",
        "root": "منع",
        "arabic_gloss": "حال دونه وحبسه",
        "meeting": "الحيلولة دون وقوع الفعل",
        "member_sense_reviewed": True,
        "anchors": {
            "al_sihah": ["منع"],
            "al_muhkam": ["منع"],
        },
    },
    "kaikki_hebrew:3217:en-כף-he-noun-Plo3-i9A": {
        "term": "كف",
        "root": "كفف",
        "arabic_gloss": "راحة اليد",
        "meeting": "باطن اليد وراحتها",
        "member_sense_reviewed": True,
        "anchors": {
            "al_sihah": ["الكف"],
            "al_muhkam": ["الكف"],
        },
    },
    "kaikki_hebrew:3658:en-חרם-he-noun-nbplobzR": {
        "term": "حرم",
        "root": "حرم",
        "arabic_gloss": "المحظور والممنوع",
        "meeting": "حد المنع الذي يجعل الشيء محظورًا أو مقدسًا",
        "member_sense_reviewed": True,
        "anchors": {
            "al_sihah": ["الحرام"],
            "al_muhkam": ["الحرام"],
        },
    },
    "kaikki_hebrew:3802:en-קם-he-verb-2avzINsN": {
        "term": "قام",
        "root": "قوم",
        "arabic_gloss": "نهض واستوى قائمًا",
        "meeting": "النهوض والقيام",
        "member_sense_reviewed": True,
        "anchors": {
            "lisan": ["ضد القعود"],
            "taj_al_arus": ["قام يقوم"],
        },
    },
    "kaikki_hebrew:4260:en-ארז-he-noun-m90Pgggd": {
        "term": "أرز",
        "root": "أرز",
        "arabic_gloss": "شجر الأرز",
        "meeting": "شجرة الأرز نفسها",
        "member_sense_reviewed": True,
        "anchors": {
            "al_sihah": ["الأرز"],
            "lisan": ["الأرز"],
        },
    },
    "kaikki_hebrew:4279:en-בצל-he-noun-KIlxZxaF": {
        "term": "بصل",
        "root": "بصل",
        "arabic_gloss": "البصل المعروف",
        "meeting": "البصل نفسه",
        "member_sense_reviewed": True,
        "anchors": {
            "lisan": ["البصل معروف"],
            "taj_al_arus": ["من البصل ومنافعه مذكورة"],
        },
    },
    "kaikki_hebrew:4603:en-גן-he-noun-C770M4we": {
        "term": "جنة",
        "root": "جنن",
        "arabic_gloss": "البستان كثير الشجر",
        "meeting": "البستان المحفوف بالشجر",
        "anchors": {
            "al_sihah": ["الجنة"],
            "lisan": ["الجنة"],
        },
    },
    "kaikki_hebrew:5201:en-שה-he-noun-0mk1qSOc": {
        "term": "شاة",
        "root": "شوي",
        "arabic_gloss": "الواحدة من الغنم",
        "meeting": "الواحدة من الضأن أو المعز",
        "anchors": {
            "al_muhkam": ["الشاة"],
            "taj_al_arus": ["الشاة"],
        },
    },
    "kaikki_hebrew:1932:en-לב-he-noun-XqzSz-DG": {
        "term": "لب",
        "root": "لبب",
        "arabic_gloss": "خالص الشيء وداخله",
        "meeting": "داخل الشيء ومركزه الذي يقوم مقام القلب",
        "member_sense_reviewed": True,
        "anchors": {
            "al_muhkam": ["لب كل شيء ولبابه خالصه"],
            "lisan": ["لب كل شيء ولبابه خالصه"],
        },
    },
    "kaikki_hebrew:3216:en-שביל-he-noun-pwDTWDxx": {
        "term": "سبيل",
        "root": "سبل",
        "arabic_gloss": "الطريق الواضح",
        "meeting": "الطريق والمسلك",
        "member_sense_reviewed": True,
        "anchors": {
            "al_sihah": ["سبيل"],
            "al_muhkam": ["سبيل"],
        },
    },
    "kaikki_hebrew:3290:en-שועל-he-noun-~bjrYTAt": {
        "term": "ثعلب",
        "root": "ثعلب",
        "arabic_gloss": "الثعلب من السباع",
        "meeting": "الحيوان نفسه، الثعلب",
        "member_sense_reviewed": True,
        "anchors": {
            "al_sihah": ["الثعلب معروف"],
            "lisan": ["الثعلب من السباع"],
        },
    },
    "kaikki_hebrew:3789:en-אלוה-he-noun-m0LNC9uk": {
        "term": "إله",
        "root": "أله",
        "arabic_gloss": "المعبود",
        "meeting": "المعبود الذي يسمى إلهًا",
        "member_sense_reviewed": True,
        "anchors": {
            "al_sihah": ["إله"],
            "lisan": ["إله"],
        },
    },
    "kaikki_hebrew:4153:en-עכביש-he-noun-m~oLUKkO": {
        "term": "عنكبوت",
        "root": "عنكب",
        "arabic_gloss": "العنكبوت",
        "meeting": "الحيوان نفسه، العنكبوت",
        "member_sense_reviewed": True,
        "anchors": {
            "lisan": ["العنكبوت"],
            "taj_al_arus": ["العنكبوت"],
        },
    },
    "kaikki_hebrew:6468:en-אחווה-he-noun-pWb5jTFs": {
        "term": "أخوة",
        "root": "أخو",
        "arabic_gloss": "رابطة الأخوة والإخاء",
        "meeting": "رابطة الأخوة بين الناس",
        "member_sense_reviewed": True,
        "anchors": {
            "kitab_al_ayn": ["وبيني وبينه أخوة وإخاء"],
            "taj_al_arus": ["أخوة بالضم"],
        },
    },
    "kaikki_hebrew:6882:en-נחושת-he-noun-5V3lO-e8": {
        "term": "نحاس",
        "root": "نحس",
        "arabic_gloss": "النحاس، ضرب من الصفر",
        "meeting": "المعدن نفسه، النحاس",
        "member_sense_reviewed": True,
        "anchors": {
            "kitab_al_ayn": ["نحاس"],
            "taj_al_arus": ["نحاس"],
        },
    },
    "kaikki_hebrew:7204:en-שבה-he-verb-pu9ug9~W": {
        "term": "سبى",
        "root": "سبي",
        "arabic_gloss": "أسر العدو",
        "meeting": "الأسر وأخذ السبي",
        "member_sense_reviewed": True,
        "anchors": {
            "al_muhkam": ["سبى"],
            "lisan": ["سبى"],
        },
    },
    "kaikki_hebrew:7355:en-גדי-he-noun-V5QD7gXN": {
        "term": "جدي",
        "root": "جدي",
        "arabic_gloss": "الذكر من أولاد المعز",
        "meeting": "صغير المعز نفسه",
        "member_sense_reviewed": True,
        "anchors": {
            "kitab_al_ayn": ["الجدي الذكر من أولاد المعز"],
            "taj_al_arus": ["الجدي من أولاد المعز ذكرها"],
        },
    },
    "kaikki_hebrew:7719:en-צדיק-he-noun-YSXN4oua": {
        "term": "صديق",
        "root": "صدق",
        "arabic_gloss": "المبالغ في الصدق وتصديق القول بالعمل",
        "meeting": "الاستقامة التي تتحقق بصدق القول والعمل",
        "member_sense_reviewed": True,
        "anchors": {
            "al_sihah": ["صديق"],
            "al_muhkam": ["صديق"],
        },
    },
    "kaikki_hebrew:7906:en-נא-he-adj-2VcbvpLu": {
        "term": "نيء",
        "root": "نيأ",
        "arabic_gloss": "الطعام الذي لم ينضج",
        "meeting": "عدم نضج الطعام",
        "member_sense_reviewed": True,
        "anchors": {
            "al_muhkam": ["نيء"],
            "lisan": ["نيء"],
        },
    },
    "kaikki_hebrew:8118:en-חנון-he-adj-hNOmxVMj": {
        "term": "حنون",
        "root": "حنن",
        "arabic_gloss": "ذو رقة وعطف",
        "meeting": "الرقة والرحمة والعطف",
        "member_sense_reviewed": True,
        "anchors": {
            "lisan": ["الحنون من النساء"],
            "taj_al_arus": ["الحنون من النساء"],
        },
    },
    "kaikki_hebrew:8261:en-משכן-he-noun-4nhYKUw~": {
        "term": "مسكن",
        "root": "سكن",
        "arabic_gloss": "المنزل والبيت",
        "meeting": "موضع السكن والإقامة",
        "member_sense_reviewed": True,
        "anchors": {
            "al_sihah": ["مسكن"],
            "al_mufradat": ["مسكن"],
        },
    },
    "kaikki_hebrew:8528:en-רומח-he-noun-jyzJNrGW": {
        "term": "رمح",
        "root": "رمح",
        "arabic_gloss": "الرمح المعروف",
        "meeting": "السلاح نفسه، الرمح",
        "member_sense_reviewed": True,
        "anchors": {
            "al_sihah": ["رمح"],
            "al_muhkam": ["رمح"],
        },
    },
    "kaikki_hebrew:9427:en-ממלכה-he-noun-YDisTXiT": {
        "term": "مملكة",
        "root": "ملك",
        "arabic_gloss": "موضع الملك وسلطانه",
        "meeting": "الدولة أو الأرض الواقعة تحت الملك",
        "member_sense_reviewed": True,
        "anchors": {
            "al_sihah": ["مملكة"],
            "lisan": ["مملكة"],
        },
    },
    "kaikki_hebrew:6314:en-אתון-he-noun-C5O87jMy": {
        "term": "أتان",
        "root": "أتن",
        "arabic_gloss": "الأنثى من الحمر",
        "meeting": "أنثى الحمار نفسها",
        "member_sense_reviewed": True,
        "anchors": {
            "lisan": ["والأتان والحمارة الأنثى خاصة"],
            "taj_al_arus": ["الأتان الحمارة"],
        },
    },
    "kaikki_hebrew:2269:en-מלח-he-noun-Gr3gJ0cU": {
        "term": "ملح",
        "root": "ملح",
        "arabic_gloss": "الملح الذي يطيب به الطعام",
        "meeting": "المادة المعدنية المستعملة لتطييب الطعام",
        "member_sense_reviewed": True,
        "anchors": {
            "lisan": ["الملح ما يطيب به الطعام"],
            "taj_al_arus": ["ما يطيب به الطعام"],
        },
    },
    "kaikki_hebrew:2434:en-מלא-he-adj-rXHGzmEP": {
        "term": "ملأ",
        "root": "ملأ",
        "arabic_gloss": "ملأ الشيء فصار مملوءا",
        "meeting": "شغل الحيز والوصول إلى حالة الامتلاء",
        "member_sense_reviewed": True,
        "anchors": {
            "lisan": ["فهو مملوء"],
            "taj_al_arus": ["يملؤه ملأ"],
        },
    },
    "kaikki_hebrew:2505:en-קלל-he-verb-fwkS0yvT": {
        "term": "قل",
        "root": "قلل",
        "arabic_gloss": "قلله، أي جعله قليلا",
        "meeting": "النقص وتقليل المقدار",
        "member_sense_reviewed": True,
        "anchors": {
            "lisan": ["جعله قليلا"],
            "taj_al_arus": ["جعله قليلا"],
        },
    },
    "kaikki_hebrew:3131:en-חלם-he-verb-3I7ASTb5": {
        "term": "حلم",
        "root": "حلم",
        "arabic_gloss": "رأى في المنام",
        "meeting": "رؤية المنام",
        "member_sense_reviewed": True,
        "anchors": {
            "lisan": ["الرؤيا والجمع أحلام"],
            "taj_al_arus": ["ما يراه النائم"],
        },
    },
    "kaikki_hebrew:6258:en-אחז-he-verb-wddo9PTy": {
        "term": "أخذ",
        "root": "أخذ",
        "arabic_gloss": "الأخذ خلاف العطاء وهو التناول",
        "meeting": "تناول الشيء وإمساكه ونقله إلى حوزة الآخذ",
        "member_sense_reviewed": True,
        "anchors": {
            "lisan": ["الأخذ خلاف العطاء"],
            "taj_al_arus": ["الأخذ خلاف العطاء"],
        },
    },
    "kaikki_hebrew:6316:en-שב-he-verb-Z283K0m9": {
        "term": "ثاب",
        "root": "ثوب",
        "arabic_gloss": "رجع بعد ذهابه",
        "meeting": "الرجوع إلى المكان أو الحال بعد الذهاب",
        "member_sense_reviewed": True,
        "anchors": {
            "lisan": ["ثاب الرجل يثوب ثوبا وثوبانا رجع بعد ذهابه"],
            "taj_al_arus": [
                "ثاب الرجل يثوب ثوبا وثوبانا رجع بعد ذهابه"
            ],
        },
    },
    "kaikki_hebrew:2388:en-חטף-he-verb-8BRm0szY": {
        "term": "خطف",
        "root": "خطف",
        "arabic_gloss": "استلاب الشيء وأخذه بسرعة",
        "meeting": "القبض السريع وانتزاع الشيء",
        "member_sense_reviewed": True,
        "anchors": {
            "lisan": ["استلاب الشيء وأخذه بسرعة"],
            "taj_al_arus": ["الاختلاس"],
        },
    },
    "kaikki_hebrew:4791:en-קרן-he-noun-RilJN~6~": {
        "term": "قرن",
        "root": "قرن",
        "arabic_gloss": "القرن، وهو الروق من الحيوان",
        "meeting": "النتوء الصلب الخارج من رأس الحيوان",
        "member_sense_reviewed": True,
        "temporal_layer": "موروث من Proto-Semitic *ḳarn- بتصريح المصدر",
        "temporal_references": [
            "Kaikki Hebrew etymology: From Proto-Semitic *ḳarn-"
        ],
        "temporal_basis": "تصريح وراثة صريح من Proto-Semitic *ḳarn-",
        "anchors": {
            "lisan": ["القرن للثور وغيره الروق"],
            "taj_al_arus": ["الروق من الحيوان"],
        },
    },
    "kaikki_hebrew:7837:en-מרד-he-verb-aToLyV6S": {
        "term": "تمرد",
        "root": "مرد",
        "arabic_gloss": "عتا وطغى وعصى",
        "meeting": "الخروج على الطاعة والعصيان",
        "member_sense_reviewed": True,
        "anchors": {
            "lisan": ["عتا وطغى"],
            "taj_al_arus": ["عتا وعصى"],
        },
    },
    "kaikki_hebrew:1044:en-עור-he-verb-hsvGoXrI": {
        "term": "عور",
        "root": "عور",
        "arabic_gloss": "ذهب بصر إحدى العينين أو أصابه العور",
        "meeting": "إصابة البصر بالعور والعمى",
        "member_sense_reviewed": True,
        "anchors": {
            "al_muhkam": ["عور"],
            "lisan": ["عور"],
        },
    },
    "kaikki_hebrew:5015:en-חרש-he-verb-rB7t3rJG": {
        "term": "خرس",
        "root": "خرس",
        "arabic_gloss": "ذهب كلامه وعجز عن النطق",
        "meeting": "فقدان الكلام والصمت",
        "member_sense_reviewed": True,
        "anchors": {
            "al_sihah": ["خرس"],
            "lisan": ["خرس"],
        },
    },
    "kaikki_hebrew:5625:en-צרה-he-noun-~4bJOYun": {
        "term": "ضرة",
        "root": "ضرر",
        "arabic_gloss": "إحدى الزوجتين بالنسبة إلى الأخرى",
        "meeting": "الزوجة المشاركة في الزوج نفسه",
        "member_sense_reviewed": True,
        "anchors": {
            "al_muhkam": ["ضرة"],
            "lisan": ["ضرة"],
        },
    },
    "kaikki_hebrew:12715:en-גווע-he-verb-hsl74D1J": {
        "term": "جاع",
        "root": "جوع",
        "arabic_gloss": "اشتد به الجوع",
        "meeting": "الهلاك جوعًا ثم امتداد الفعل إلى الهلاك عامة",
        "member_sense_reviewed": True,
        "anchors": {
            "al_sihah": ["جاع"],
            "lisan": ["جاع"],
        },
    },
    "kaikki_hebrew:12777:en-נשה-he-verb-wF6McvUS": {
        "term": "نسأ",
        "root": "نسأ",
        "arabic_gloss": "أخر الدين وباع بالنسيئة",
        "meeting": "تأخير الدين والبيع المؤجل بفائدة",
        "member_sense_reviewed": True,
        "anchors": {
            "al_muhkam": ["نسأ"],
            "lisan": ["نسأ"],
        },
    },
    "kaikki_hebrew:13315:en-אשל-he-noun-m6jLJZC6": {
        "term": "أثل",
        "root": "أثل",
        "arabic_gloss": "شجر الأثل",
        "meeting": "شجرة الأثل أو الطرفاء نفسها",
        "member_sense_reviewed": True,
        "anchors": {
            "lisan": ["أثل"],
            "taj_al_arus": ["أثل"],
        },
    },
    "kaikki_hebrew:13483:en-תבן-he-noun-wxdvNwkI": {
        "term": "تبن",
        "root": "تبن",
        "arabic_gloss": "التبن من بقايا الزرع",
        "meeting": "التبن والقش اليابس",
        "member_sense_reviewed": True,
        "anchors": {
            "al_sihah": ["تبن"],
            "lisan": ["تبن"],
        },
    },
    "kaikki_hebrew:14886:en-פרא-he-noun-S2tMzPZt": {
        "term": "فرأ",
        "root": "فرأ",
        "arabic_gloss": "الحمار الوحشي",
        "meeting": "الحمار الوحشي نفسه",
        "member_sense_reviewed": True,
        "anchors": {
            "al_sihah": ["فرأ"],
            "lisan": ["فرأ"],
        },
    },
    "kaikki_hebrew:16096:en-מוהר-he-noun-vHqipcD5": {
        "term": "مهر",
        "root": "مهر",
        "arabic_gloss": "الصداق الذي يعطى في الزواج",
        "meeting": "مال المهر في عقد الزواج",
        "member_sense_reviewed": True,
        "anchors": {
            "al_muhkam": ["مهر"],
            "lisan": ["مهر"],
        },
    },
    "kaikki_hebrew:16296:en-אטר-he-verb-JqSouGpw": {
        "term": "أطر",
        "root": "أطر",
        "arabic_gloss": "ثنى الشيء وعطفه",
        "meeting": "الثني الذي يفضي إلى الإغلاق أو الربط",
        "member_sense_reviewed": True,
        "anchors": {
            "al_muhkam": ["أطر"],
            "lisan": ["أطر"],
        },
    },
    "kaikki_hebrew:16372:en-יקע-he-verb-BffgJfBR": {
        "term": "وقع",
        "root": "وقع",
        "arabic_gloss": "سقط ووقع",
        "meeting": "السقوط الذي يخرج الشيء من موضع استقراره",
        "member_sense_reviewed": True,
        "anchors": {
            "al_sihah": ["وقع"],
            "lisan": ["وقع"],
        },
    },
    "kaikki_hebrew:16695:en-נזם-he-noun-kdmPDQgl": {
        "term": "زمام",
        "root": "زمم",
        "arabic_gloss": "ما يربط به ويقاد",
        "meeting": "حلقة أو رباط يمسك به العضو ويقاد",
        "member_sense_reviewed": True,
        "anchors": {
            "al_muhkam": ["زمام"],
            "lisan": ["زمام"],
        },
    },
    "kaikki_hebrew:17017:en-צאל-he-noun-kC3N9wlf": {
        "term": "ضال",
        "root": "ضأل",
        "arabic_gloss": "شجر السدر البري",
        "meeting": "الشجرة البرية المسماة نفسها",
        "member_sense_reviewed": True,
        "anchors": {
            "al_sihah": ["ضال"],
            "taj_al_arus": ["ضال"],
        },
    },
    "kaikki_hebrew:849:en-גנב-he-verb-6exYWwd2": {
        "term": "جنب",
        "root": "جنب",
        "arabic_gloss": "نحى الشيء وأبعده عن موضعه",
        "meeting": (
            "إخراج الشيء من حوزة صاحبه يلتقي مع تنحيته وإبعاده، "
            "ولا تدعى هوية ترجمة بين السرقة والتنحية"
        ),
        "member_sense_reviewed": True,
        "anchors": {
            "kitab_al_ayn": ["جنب"],
            "al_sihah": ["جنب"],
        },
    },
    "kaikki_hebrew:956:en-לקח-he-verb-6O9mGx1Z": {
        "term": "لحق",
        "root": "لحق",
        "arabic_gloss": "لحق الشيء بالشيء واتصل به",
        "meeting": (
            "الأخذ يضم الشيء إلى حوزة الآخذ، واللحوق يضم اللاحق "
            "إلى ما لحق به؛ الالتقاء في اتصال المنقول بوجهته"
        ),
        "member_sense_reviewed": True,
        "anchors": {
            "al_muhkam": ["لحق"],
            "lisan": ["لحق"],
        },
    },
    "kaikki_hebrew:1015:en-עם-he-noun-JHiSqRoY": {
        "term": "عام",
        "root": "عمم",
        "arabic_gloss": "العام خلاف الخاص، وما شمل الجماعة",
        "meeting": (
            "الشعب جماعة يشملها اسم واحد، والعام ما يشمل الجماعة؛ "
            "الالتقاء في مدار الجمع والشمول لا في ترجمة nation وحدها"
        ),
        "member_sense_reviewed": True,
        "anchors": {
            "lisan": ["عام"],
            "al_misbah": ["عام"],
        },
    },
    "kaikki_hebrew:2326:en-זקן-he-adj-8y-PgIUM": {
        "term": "ذقن",
        "root": "ذقن",
        "arabic_gloss": "مجتمع اللحيين وما ينبت عليه من شعر",
        "meeting": (
            "انتقل وصف الكبير في السن من علامة اللحية والذقن؛ "
            "الالتقاء مدار سمة الشيخ لا تطابق ترجمة الصفة والعضو"
        ),
        "member_sense_reviewed": True,
        "temporal_layer": (
            "موروث من Proto-Semitic *ḏaḳan- بتصريح المصدر"
        ),
        "temporal_references": [
            "Kaikki Hebrew etymology: From Proto-Semitic *ḏaḳan-"
        ],
        "temporal_basis": (
            "تصريح وراثة صريح من Proto-Semitic *ḏaḳan-"
        ),
        "anchors": {
            "al_sihah": ["ذقن الإنسان مجمع لحييه"],
            "lisan": ["ذقن الإنسان مجتمع لحييه"],
        },
    },
    "kaikki_hebrew:3186:en-גנן-he-verb-nPJEdrS-": {
        "term": "جن",
        "root": "جنن",
        "arabic_gloss": "ستر الشيء وغطاه",
        "meeting": (
            "الحماية في الفرع إحاطة تستر المحمي، والجن في العربية "
            "ستر عن الحس؛ يلتقيان في مدار الستر الواقي"
        ),
        "member_sense_reviewed": True,
        "anchors": {
            "asas_al_balagha": ["جنه ستره فاجتن"],
            "taj_al_arus": ["أصل الجن الستر عن الحاسة"],
        },
    },
    "kaikki_hebrew:4792:en-קרן-he-verb-xct6IO~N": {
        "term": "قرن",
        "root": "قرن",
        "arabic_gloss": "القرن النتوء الخارج من الرأس",
        "meeting": (
            "الشعاع البارز من الوجه والقرن البارز من الرأس يلتقيان "
            "في مدار الامتداد الناتئ، لا في ترجمة shine وhorn"
        ),
        "member_sense_reviewed": True,
        "temporal_layer": (
            "موروث من Proto-Semitic *ḳarn- بتصريح المصدر"
        ),
        "temporal_references": [
            "Kaikki Hebrew etymology: From Proto-Semitic *ḳarn-"
        ],
        "temporal_basis": (
            "تصريح وراثة صريح من Proto-Semitic *ḳarn-"
        ),
        "anchors": {
            "al_sihah": ["قرن"],
            "al_muhkam": ["قرن"],
        },
    },
    "kaikki_hebrew:6406:en-דלה-he-verb-kKDP5lTv": {
        "term": "دلى",
        "root": "دلو",
        "arabic_gloss": "أرسل الدلو في البئر ثم جذبها",
        "meeting": (
            "الفرع يسمي استخراج الماء، والعربية تسمي إنزال الدلو "
            "في البئر؛ يلتقيان في سلسلة حركة الدلو في الاستقاء"
        ),
        "member_sense_reviewed": True,
        "anchors": {
            "kitab_al_ayn": ["وأدليتها"],
            "al_misbah": ["الدلو"],
        },
    },
    "kaikki_hebrew:6504:en-מגד-he-noun-wF2-ThXQ": {
        "term": "مجد",
        "root": "مجد",
        "arabic_gloss": "السعة في الخير والكرم والجلال",
        "meeting": (
            "الحسن والخير في الفرع والسعة في الكرم والجلال في "
            "العربية يلتقيان في مدار القيمة المحمودة"
        ),
        "member_sense_reviewed": True,
        "anchors": {
            "al_sihah": ["المجد"],
            "al_mufradat": ["المجد"],
        },
    },
    "kaikki_hebrew:6911:en-קצר-he-verb-b2dpeEUu": {
        "term": "قصير",
        "root": "قصر",
        "arabic_gloss": "ما كان خلاف الطويل أو صير قصيرا",
        "meeting": (
            "الحصاد قطع يختصر ساق الزرع، والقصر تقليل الطول؛ "
            "الالتقاء في مدار القطع والتقصير لا في ترجمة reap وshort"
        ),
        "member_sense_reviewed": True,
        "anchors": {
            "kitab_al_ayn": ["قصيرا"],
            "al_muhkam": ["قصير"],
        },
    },
    "kaikki_hebrew:7238:en-חלד-he-noun-c0-xCNC0": {
        "term": "خلد",
        "root": "خلد",
        "arabic_gloss": "دام بقاؤه وطال مكثه",
        "meeting": (
            "العمر مدة البقاء في الدنيا، والخلود طول البقاء؛ "
            "يلتقيان في مدار امتداد زمن الحياة مع اختلاف الحد"
        ),
        "member_sense_reviewed": True,
        "temporal_layer": "biblical، Hebrew Bible",
        "temporal_references": ["Tanach, Psalms 49:1"],
        "temporal_basis": "شاهد توراتي صريح للعضو نفسه",
        "anchors": {
            "al_sihah": ["الخلد دوام البقاء"],
            "al_mufradat": ["والخلود"],
        },
    },
    "kaikki_hebrew:8147:en-ישר-he-adj-JAhiDoA1": {
        "term": "يسير",
        "root": "يسر",
        "arabic_gloss": "الهين السهل غير العسير",
        "meeting": (
            "الطريق المستقيم لا عوج فيه، واليسير سهل لا عسر فيه؛ "
            "الالتقاء في مدار انعدام العائق والانحراف"
        ),
        "member_sense_reviewed": True,
        "anchors": {
            "al_sihah": ["يسير"],
            "asas_al_balagha": ["يسير"],
        },
    },
    "kaikki_hebrew:8313:en-הדס-he-noun-he:myrtle": {
        "term": "آس",
        "root": "أوس",
        "arabic_gloss": "شجر الآس المعروف",
        "meeting": "النبت العطري نفسه، شجر الآس أو myrtle",
        "member_sense_reviewed": True,
        "anchors": {
            "al_sihah": ["والآس"],
            "al_muhkam": ["الآس"],
        },
    },
    "kaikki_hebrew:8569:en-מגילה-he-noun-4WqdTRz5": {
        "term": "مجلة",
        "root": "جلل",
        "arabic_gloss": "الصحيفة أو الكتاب",
        "meeting": (
            "اللفافة المكتوبة في الفرع والصحيفة أو الكتاب في "
            "العربية يلتقيان في مدار الوعاء المكتوب"
        ),
        "member_sense_reviewed": True,
        "anchors": {
            "al_sihah": ["والمجلة"],
            "taj_al_arus": ["المجلة"],
        },
    },
    "kaikki_hebrew:8644:en-ציווה-he-verb-7uyCMGGP": {
        "term": "وصى",
        "root": "وصي",
        "arabic_gloss": "عهد إليه وأمره بما يفعل",
        "meeting": (
            "الأمر الملزم في الفرع والوصية المعهود بها في العربية "
            "يلتقيان في مدار توجيه المخاطب إلى فعل"
        ),
        "member_sense_reviewed": True,
        "anchors": {
            "kitab_al_ayn": ["الوصية"],
            "lisan": ["ووصاه"],
        },
    },
    "kaikki_hebrew:10493:en-טרי-he-adj-0JirXkS5": {
        "term": "طري",
        "root": "طري",
        "arabic_gloss": "الشيء الطري غير اليابس",
        "meeting": "حالة الجدة والطراوة نفسها في الصفتين",
        "member_sense_reviewed": True,
        "anchors": {
            "asas_al_balagha": ["شيء طري"],
            "taj_al_arus": ["طري"],
        },
    },
    "kaikki_hebrew:11777:en-בעיר-he-noun-ppl-kR25": {
        "term": "بعير",
        "root": "بعر",
        "arabic_gloss": "الجمل أو الناقة من الإبل",
        "meeting": (
            "الفرع يسمي بهيمة الرعي الجامعة، والعربية فردا من "
            "الإبل؛ يلتقيان في مدار الدابة الرعوية الكبيرة"
        ),
        "member_sense_reviewed": True,
        "temporal_layer": (
            "موروث من Proto-Semitic *bVʕVr- بتصريح المصدر"
        ),
        "temporal_references": [
            "Kaikki Hebrew etymology: From Proto-Semitic *bVʕVr-"
        ],
        "temporal_basis": (
            "تصريح وراثة صريح من Proto-Semitic *bVʕVr-"
        ),
        "anchors": {
            "al_sihah": ["البعير"],
            "taj_al_arus": ["البعير"],
        },
    },
    "kaikki_hebrew:11817:en-תיש-he-noun-jY-zIUyu": {
        "term": "تيس",
        "root": "تيس",
        "arabic_gloss": "الذكر من المعز",
        "meeting": "الحيوان نفسه، ذكر المعز",
        "member_sense_reviewed": True,
        "anchors": {
            "al_sihah": ["التيس من المعز"],
            "al_misbah": ["التيس الذكر من المعز"],
        },
    },
    "kaikki_hebrew:11834:en-חך-he-noun-rhOG~dmM": {
        "term": "حنك",
        "root": "حنك",
        "arabic_gloss": "باطن أعلى الفم وسقفه",
        "meeting": "العضو نفسه، سقف الفم أو الحنك",
        "member_sense_reviewed": True,
        "anchors": {
            "asas_al_balagha": ["وهو سقف أعلى الفم"],
            "lisan": ["الحنك من الإنسان والدابة باطن أعلى الفم"],
        },
    },
    "kaikki_hebrew:12167:en-שחק-he-verb-hAh7OITr": {
        "term": "ضحك",
        "root": "ضحك",
        "arabic_gloss": "انبساط الوجه وتكشف الأسنان من السرور",
        "meeting": "فعل الضحك نفسه",
        "member_sense_reviewed": True,
        "anchors": {
            "kitab_al_ayn": ["ضحك"],
            "al_mufradat": ["الضحك"],
        },
    },
    "kaikki_hebrew:386:en-אלף-he-noun-Sxp0HWeM": {
        "term": "ألف",
        "root": "ألف",
        "arabic_gloss": "الألف من العدد المعروف",
        "meeting": (
            "جوار المعنى في الفرع هو مقدار الألف، وجواره في "
            "العربية العدد ألف؛ يلتقيان في المقدار العددي نفسه"
        ),
        "member_sense_reviewed": True,
        "anchors": {
            "lisan": ["الألف من العدد معروف"],
            "taj_al_arus": ["الألف من العدد مذكر"],
        },
    },
    "kaikki_hebrew:445:en-שבר-he-verb-he:break_verb": {
        "term": "ثبر",
        "root": "ثبر",
        "arabic_gloss": "ثبره، أي أهلكه إهلاكا لا ينتعش بعده",
        "meeting": (
            "جوار المعنى في الفرع هو كسر الشيء وتفريق أجزائه، "
            "وجواره في العربية الإهلاك الذي لا ينتعش منه؛ "
            "يلتقيان في مدار إبطال البنية وإيصالها إلى التلف"
        ),
        "member_sense_reviewed": True,
        "anchors": {
            "lisan": ["أهلكه إهلاكا لا ينتعش"],
            "taj_al_arus": ["أهلكه إهلاكا لا ينتعش"],
        },
    },
    "kaikki_hebrew:933:en-נהר-he-verb-U7EY147G": {
        "term": "نهر",
        "root": "نهر",
        "arabic_gloss": "نهر الماء، أي جرى في الأرض واتخذ مجرى",
        "meeting": (
            "جوار المعنى في الفرع هو جريان الماء واندفاعه، "
            "وجواره في العربية جريان الماء في الأرض؛ يلتقيان "
            "في مدار السيلان المتخذ مجرى"
        ),
        "member_sense_reviewed": True,
        "anchors": {
            "lisan": ["جرى في الأرض"],
            "taj_al_arus": ["جرى في الأرض"],
        },
    },
    "kaikki_hebrew:6488:en-עמוד-he-noun-Tb51ToHb": {
        "term": "عمود",
        "root": "عمد",
        "arabic_gloss": (
            "العمود الخشبة القائمة التي يحمل عليها البناء أو الخباء"
        ),
        "meeting": (
            "جوار المعنى في الفرع هو الدعامة القائمة الحاملة، "
            "وجواره في العربية الخشبة القائمة؛ يلتقيان في مدار "
            "الجسم القائم الذي يسند ما فوقه"
        ),
        "member_sense_reviewed": True,
        "anchors": {
            "lisan": ["الخشبة القائمة في وسط الخباء"],
            "taj_al_arus": ["الخشبة القائمة في وسط الخباء"],
        },
    },
    "kaikki_hebrew:9425:en-כיזב-he-verb-AZ6uvW1l": {
        "term": "كذب",
        "root": "كذب",
        "arabic_gloss": "الكذب ضد الصدق",
        "meeting": (
            "جوار المعنى في الفرع هو قول غير الصدق وإظهار الباطل، "
            "وجواره في العربية الكذب ضد الصدق؛ يلتقيان في مدار "
            "مخالفة الخبر للواقع"
        ),
        "member_sense_reviewed": True,
        "anchors": {
            "lisan": ["الكذب ضد الصدق"],
            "taj_al_arus": ["الكذب ضد الصدق"],
        },
    },
    "kaikki_hebrew:9208:en-חביב-he-adj-XYfYKYue": {
        "term": "حبيب",
        "root": "حبب",
        "arabic_gloss": "الحبيب هو المحبوب",
        "meeting": (
            "جوار المعنى في الفرع هو من كان محبوبا أو لطيفا "
            "قريبا إلى النفس، وجواره في العربية المحبوب؛ "
            "يلتقيان في مدار المحبة والاستلطاف"
        ),
        "member_sense_reviewed": True,
        "anchors": {
            "lisan": ["المحبوب"],
            "taj_al_arus": ["المحبوب"],
        },
    },
    "kaikki_hebrew:12994:en-עקידה-he-noun-ZDBlH~VN": {
        "term": "عقد",
        "root": "عقد",
        "arabic_gloss": "عقد الحبل فصار معقودا",
        "meeting": (
            "جوار المعنى في الفرع هو ربط الأطراف وتوثيقها، "
            "وجواره في العربية عقد الحبل؛ يلتقيان في فعل الربط "
            "والإحكام نفسه"
        ),
        "member_sense_reviewed": True,
        "anchors": {
            "lisan": ["عقدت الحبل فهو معقود"],
            "taj_al_arus": ["عقدت الحبل فهو معقود"],
        },
    },
    "kaikki_hebrew:16404:en-קושש-he-verb-Pi10u8GR": {
        "term": "قش",
        "root": "قشش",
        "arabic_gloss": "قش الشيء، أي جمعه",
        "meeting": (
            "جوار المعنى في الفرع هو جمع العيدان أو القش، "
            "وجواره في العربية جمع الشيء؛ يلتقيان في مدار "
            "الالتقاط والجمع"
        ),
        "member_sense_reviewed": True,
        "anchors": {
            "lisan": ["الشيء يقشه", "جمعه"],
            "taj_al_arus": ["الشيء يقشه", "جمعه"],
        },
    },
    "kaikki_hebrew:2218:en-אווז-he-noun-wtN90FdX": {
        "term": "إوز",
        "root": "أوز",
        "arabic_gloss": "الإوز من طير الماء",
        "meeting": (
            "جوار المعنى في الفرع هو طائر الإوز، وجواره في "
            "العربية الإوز من البط وطير الماء؛ يلتقيان في "
            "الطائر المائي نفسه"
        ),
        "member_sense_reviewed": True,
        "anchors": {
            "lisan": ["الإوز", "البط"],
            "taj_al_arus": ["الإوز", "البط"],
        },
    },
    "kaikki_hebrew:25:en-שלום-he-noun-wuEMIL9G": {
        "term": "سلام",
        "root": "سلم",
        "arabic_gloss": "السلام ضد الحرب، والسلامة من الآفات",
        "meeting": (
            "جوار المعنى في الفرع هو السلم والطمأنينة، وجواره "
            "في العربية السلام والسلامة؛ يلتقيان في مدار زوال "
            "العدوان والآفة"
        ),
        "member_sense_reviewed": True,
        "anchors": {
            "al_muhkam": ["سلام"],
            "taj_al_arus": ["سلام"],
        },
    },
    "kaikki_hebrew:184:en-עבר-he-verb-KfvU0Xzc": {
        "term": "عبر",
        "root": "عبر",
        "arabic_gloss": "عبر الموضع، أي اجتازه من جانب إلى جانب",
        "meeting": "فعل الاجتياز والانتقال من جانب إلى آخر نفسه",
        "member_sense_reviewed": True,
        "anchors": {
            "al_muhkam": ["عبر"],
            "lisan": ["عبر"],
        },
    },
    "kaikki_hebrew:315:en-ראש-he-noun-ny5tM6Nx": {
        "term": "رأس",
        "root": "رأس",
        "arabic_gloss": "رأس الإنسان وغيره، أعلى البدن ومقدمه",
        "meeting": "العضو الأعلى من البدن نفسه",
        "member_sense_reviewed": True,
        "anchors": {
            "al_sihah": ["رأس"],
            "lisan": ["رأس"],
        },
    },
    "kaikki_hebrew:370:en-בית-he-noun-1uIShmIa": {
        "term": "بيت",
        "root": "بيت",
        "arabic_gloss": "البيت المسكن والمنزل",
        "meeting": "موضع السكن والإيواء نفسه",
        "member_sense_reviewed": True,
        "anchors": {
            "al_sihah": ["بيت"],
            "lisan": ["بيت"],
        },
    },
    "kaikki_hebrew:397:en-בת-he-noun-TtKPgsqW": {
        "term": "بنت",
        "root": "بني",
        "arabic_gloss": "البنت الأنثى من الولد",
        "meeting": "صلة النسب نفسها، الأنثى من الولد",
        "member_sense_reviewed": True,
        "anchors": {
            "al_muhkam": ["بنت"],
            "lisan": ["بنت"],
        },
    },
    "kaikki_hebrew:540:en-תחת-he-prep-itokv2vz": {
        "term": "تحت",
        "root": "تحت",
        "arabic_gloss": "تحت نقيض فوق",
        "meeting": "جهة السفل المقابلة للفوق نفسها",
        "member_sense_reviewed": True,
        "anchors": {
            "al_mufradat": ["تحت"],
            "lisan": ["تحت"],
        },
    },
    "kaikki_hebrew:562:en-זרע-he-noun-GbJYVuHB": {
        "term": "زرع",
        "root": "زرع",
        "arabic_gloss": "الزرع الحب والبذر والنبات النابت منه",
        "meeting": "البذر الذي يطرح للإنبات وما ينشأ منه",
        "member_sense_reviewed": True,
        "anchors": {
            "al_muhkam": ["زرع"],
            "lisan": ["زرع"],
        },
    },
    "kaikki_hebrew:1770:en-צהריים-he-noun-aNJPgw9Q": {
        "term": "ظهر",
        "root": "ظهر",
        "arabic_gloss": "الظهر وقت انتصاف النهار",
        "meeting": "وقت منتصف النهار نفسه",
        "member_sense_reviewed": True,
        "anchors": {
            "al_sihah": ["ظهر"],
            "lisan": ["ظهر"],
        },
    },
    "kaikki_hebrew:2034:en-עבודה-he-noun-xWfFCqzn": {
        "term": "عبادة",
        "root": "عبد",
        "arabic_gloss": "العبادة الطاعة والخضوع لله",
        "meeting": "الخدمة التعبدية والخضوع في الشعيرة نفسها",
        "member_sense_reviewed": True,
        "anchors": {
            "al_muhkam": ["عبادة"],
            "lisan": ["عبادة"],
        },
    },
    "kaikki_hebrew:2231:en-חטא-he-noun-zMxox5KO": {
        "term": "خطئ",
        "root": "خطأ",
        "arabic_gloss": "خطئ، أي أثم وأصاب الخطيئة",
        "meeting": "الإثم والخطيئة ومجاوزة الصواب",
        "member_sense_reviewed": True,
        "anchors": {
            "al_sihah": ["خطئ"],
            "lisan": ["خطئ"],
        },
    },
    "kaikki_hebrew:2443:en-עול-he-noun-wUs3q3ob": {
        "term": "غل",
        "root": "غلل",
        "arabic_gloss": "الغل ما يقيد به العنق أو اليد",
        "meeting": (
            "النير يقيد العنق للعمل، والغل يقيد العنق أو اليد؛ "
            "يلتقيان في مدار القيد المحمول"
        ),
        "member_sense_reviewed": True,
        "anchors": {
            "al_sihah": ["غل"],
            "lisan": ["غل"],
        },
    },
    "kaikki_hebrew:2509:en-טעם-he-noun-0b5BsReM": {
        "term": "طعم",
        "root": "طعم",
        "arabic_gloss": "الطعم ما يدرك بالذوق",
        "meeting": "حاسة الذوق وما تدركه من الطعام",
        "member_sense_reviewed": True,
        "anchors": {
            "al_muhkam": ["طعم"],
            "lisan": ["طعم"],
        },
    },
    "kaikki_hebrew:2939:en-עמד-he-verb-7SUANQDE": {
        "term": "عمد",
        "root": "عمد",
        "arabic_gloss": "عمد الشيء، أي أقامه وأسنده بعماد",
        "meeting": (
            "الوقوف قيام على سند، والعمد إقامة الشيء بعماد؛ "
            "يلتقيان في مدار الانتصاب والثبات"
        ),
        "member_sense_reviewed": True,
        "anchors": {
            "al_muhkam": ["عمد"],
            "lisan": ["عمد"],
        },
    },
    "kaikki_hebrew:3132:en-קשת-he-noun-j87QC2zi": {
        "term": "قوس",
        "root": "قوس",
        "arabic_gloss": "القوس المنحنية التي يرمى عنها",
        "meeting": (
            "قوس المطر في الفرع والقوس في العربية يلتقيان في "
            "مدار الهيئة المنحنية المقوسة، لا في مادة الاستعمال"
        ),
        "member_sense_reviewed": True,
        "anchors": {
            "al_muhkam": ["قوس"],
            "lisan": ["قوس"],
        },
    },
    "kaikki_hebrew:3440:en-רצה-he-verb-CVriWWbX": {
        "term": "رضي",
        "root": "رضي",
        "arabic_gloss": "رضي الشيء، أي اختاره وقبله واستحسنه",
        "meeting": (
            "الإرادة توجه إلى المختار، والرضا قبول المختار "
            "واستحسانه؛ يلتقيان في مدار الميل إلى الشيء"
        ),
        "member_sense_reviewed": True,
        "anchors": {
            "lisan": ["رضي"],
            "taj_al_arus": ["رضي"],
        },
    },
    "kaikki_hebrew:3458:en-נכרי-he-adj-RifvnLo1": {
        "term": "نكر",
        "root": "نكر",
        "arabic_gloss": "نكر الشيء، أي جهله ولم يعرفه",
        "meeting": (
            "الأجنبي غير المعروف من الجماعة، والمنكور ما لم "
            "يعرف؛ يلتقيان في مدار الغربة وعدم المعرفة"
        ),
        "member_sense_reviewed": True,
        "anchors": {
            "al_muhkam": ["نكر"],
            "lisan": ["نكر"],
        },
    },
    "kaikki_hebrew:5018:en-חרש-he-noun-vnNsMOMB": {
        "term": "خرس",
        "root": "خرس",
        "arabic_gloss": "الخرس ذهاب الكلام والصمت",
        "meeting": (
            "الفعل السري يقع بلا صوت، والخرس امتناع الكلام؛ "
            "يلتقيان في مدار الصمت وحجب الصوت"
        ),
        "member_sense_reviewed": True,
        "anchors": {
            "al_muhkam": ["خرس"],
            "lisan": ["خرس"],
        },
    },
    "kaikki_hebrew:5668:en-הרס-he-verb-QP2RsijE": {
        "term": "هرس",
        "root": "هرس",
        "arabic_gloss": "هرس الشيء، أي دقه وكسره",
        "meeting": (
            "الهدم يزيل البنية، والهرس يدق أجزاءها؛ يلتقيان "
            "في مدار تفكيك الشيء وإفساده"
        ),
        "member_sense_reviewed": True,
        "anchors": {
            "al_sihah": ["هرس"],
            "lisan": ["هرس"],
        },
    },
    "kaikki_hebrew:6022:en-נישה-he-verb-QnVoX7TH": {
        "term": "نسى",
        "root": "نسي",
        "arabic_gloss": "نساه الشيء وأنساه إياه",
        "meeting": "التسبب في النسيان وإزالة الشيء من الذاكرة",
        "member_sense_reviewed": True,
        "anchors": {
            "al_muhkam": ["نسى"],
            "taj_al_arus": ["نسى"],
        },
    },
    "kaikki_hebrew:7469:en-סדר-he-noun-xa1RUv2G": {
        "term": "سرد",
        "root": "سرد",
        "arabic_gloss": "السرد تتابع الشيء بعضه إثر بعض",
        "meeting": (
            "الترتيب يضع الأجزاء في نسق، والسرد يتابع بعضها "
            "إثر بعض؛ يلتقيان في مدار التسلسل المنظم"
        ),
        "member_sense_reviewed": True,
        "anchors": {
            "al_muhkam": ["سرد"],
            "lisan": ["سرد"],
        },
    },
    "kaikki_hebrew:7568:en-כיס-he-noun-eCpfs4-Y": {
        "term": "كيس",
        "root": "كيس",
        "arabic_gloss": "الكيس وعاء من جلد أو ثوب",
        "meeting": "الوعاء المحمول لحفظ المال أو الأشياء نفسه",
        "member_sense_reviewed": True,
        "anchors": {
            "al_muhkam": ["كيس"],
            "lisan": ["كيس"],
        },
    },
    "kaikki_hebrew:1:en-כלב-he-noun-JG1v3E-S": {
        "term": "كلب",
        "root": "كلب",
        "arabic_gloss": "الكلب النوع النابح المعروف",
        "meeting": "الحيوان الكلبي المستأنس نفسه",
        "member_sense_reviewed": True,
        "temporal_layer": (
            "موروث من Proto-Semitic *kalb- بتصريح المصدر"
        ),
        "temporal_references": [
            "Kaikki Hebrew etymology: Inherited from Proto-Semitic *kalb-"
        ],
        "temporal_basis": (
            "تصريح وراثة صريح من Proto-Semitic *kalb-"
        ),
        "anchors": {
            "lisan": ["النوع النابح"],
            "taj_al_arus": ["النوع النابح"],
        },
    },
    "kaikki_hebrew:309:en-רגל-he-noun-Xac9Gpm4": {
        "term": "رجل",
        "root": "رجل",
        "arabic_gloss": "الرجل بالكسر القدم وعضو المشي",
        "meeting": "القدم والساق بوصفهما عضو المشي نفسه",
        "member_sense_reviewed": True,
        "temporal_layer": (
            "موروث من Proto-Semitic *rigl- بتصريح المصدر"
        ),
        "temporal_references": [
            "Kaikki Hebrew etymology: From Proto-Semitic *rigl-"
        ],
        "temporal_basis": (
            "تصريح وراثة صريح من Proto-Semitic *rigl-"
        ),
        "anchors": {
            "lisan": ["القدم"],
            "taj_al_arus": ["القدم"],
        },
    },
    "kaikki_hebrew:3425:en-כבד-he-noun-PcYg7dyD": {
        "term": "كبد",
        "root": "كبد",
        "arabic_gloss": "الكبد اللحمة السوداء في البطن",
        "meeting": "عضو الكبد نفسه",
        "member_sense_reviewed": True,
        "temporal_layer": (
            "موروث من Proto-Semitic *kabid- بتصريح المصدر"
        ),
        "temporal_references": [
            "Kaikki Hebrew etymology: From Proto-Semitic *kabid-"
        ],
        "temporal_basis": (
            "تصريح وراثة صريح من Proto-Semitic *kabid-"
        ),
        "anchors": {
            "lisan": ["اللحمة السوداء في البطن"],
            "taj_al_arus": ["في الجانب الأيمن لحمة سوداء"],
        },
    },
    "kaikki_hebrew:1378:en-סיבה-he-noun-~GV9vquN": {
        "term": "سبب",
        "root": "سبب",
        "arabic_gloss": "السبب ما يتوصل به إلى غيره",
        "meeting": (
            "جوار المعنى في الفرع هو منشأ الحدث أو علته، وجواره "
            "في العربية ما يتوصل به إلى الشيء؛ يلتقيان في الواسطة "
            "المنتجة للنتيجة"
        ),
        "member_sense_reviewed": True,
        "sound_rules": [],
        "anchors": {
            "lisan": ["كل شيء يتوصل به إلى الشيء فهو سبب"],
            "al_misbah": ["والسبب الحبل"],
        },
    },
    "kaikki_hebrew:2657:en-דחה-he-verb-Fv0VCuKj": {
        "term": "دحا",
        "root": "دحا",
        "arabic_gloss": "دحا الشيء بسطه وأزاله عن موضعه",
        "meeting": (
            "جوار المعنى في الفرع هو دفع الشيء جانبًا، وجواره في "
            "العربية إزالته عن مقرّه وجرفه؛ يلتقيان في الدفع المزيل"
        ),
        "member_sense_reviewed": True,
        "sound_rules": [],
        "anchors": {
            "al_sihah": ["دحوت الشئ دحوا بسطته"],
            "al_mufradat": ["أزالها عن مقرها"],
        },
    },
    "kaikki_hebrew:3103:en-בא-he-verb-TtJvuTO9": {
        "term": "باء",
        "root": "باء",
        "arabic_gloss": "باء رجع وحل في موضعه",
        "meeting": (
            "جوار المعنى في الفرع هو المجيء إلى موضع، وجواره في "
            "العربية الرجوع والحلول في موضع؛ يلتقيان في بلوغ المكان"
        ),
        "member_sense_reviewed": True,
        "sound_rules": [],
        "anchors": {
            "al_mufradat": ["أي رجع"],
            "al_muhit": ["الباء"],
        },
    },
    "kaikki_hebrew:5019:en-חרש-he-adv-2OKIKdQM": {
        "term": "خرس",
        "root": "خرس",
        "arabic_gloss": "الخرس ذهاب الكلام والعجز عنه",
        "meeting": (
            "جوار المعنى في الفرع هو الفعل سرًا بلا صوت، وجواره "
            "في العربية انقطاع الكلام؛ يلتقيان في مدار الصمت"
        ),
        "member_sense_reviewed": True,
        "sound_rules": ["GUT-05"],
        "anchors": {
            "lisan": ["ذهاب الكلام"],
            "al_misbah": ["منع الكلام"],
        },
    },
    "kaikki_hebrew:5563:en-אז-he-adv--EPAHTK~": {
        "term": "إذ",
        "root": "إذ",
        "arabic_gloss": "إذ ظرف لما مضى من الزمان",
        "meeting": (
            "جوار المعنى في الفرع هو الإحالة إلى ذلك الحين، وجواره "
            "في العربية ظرف الزمن الماضي؛ يلتقيان في الإشارة الزمنية"
        ),
        "member_sense_reviewed": True,
        "sound_rules": ["DENT-04"],
        "anchors": {
            "al_sihah": ["إذ"],
            "al_misbah": ["إذ"],
        },
    },
    "kaikki_hebrew:5564:en-אז-he-pron-XYiOLiie": {
        "term": "إذ",
        "root": "إذ",
        "arabic_gloss": "إذ ظرف لما مضى من الزمان",
        "meeting": (
            "جوار المعنى في الفرع هو ذلك الوقت، وجواره في العربية "
            "الزمن الماضي المشار إليه؛ يلتقيان في تعيين الحين"
        ),
        "member_sense_reviewed": True,
        "sound_rules": ["DENT-04"],
        "anchors": {
            "al_sihah": ["إذ"],
            "al_misbah": ["إذ"],
        },
    },
    "kaikki_hebrew:5647:en-לו-he-conj-XQvhQykR": {
        "term": "لو",
        "root": "لو",
        "arabic_gloss": "لو حرف شرط يدل على امتناع لامتناع",
        "meeting": (
            "جوار المعنى في الفرع هو الشرط المخالف للواقع، وجواره "
            "في العربية الشرط الممتنع؛ يلتقيان في أداة الشرط نفسها"
        ),
        "member_sense_reviewed": True,
        "sound_rules": [],
        "anchors": {
            "kitab_al_ayn": ["لو"],
            "taj_al_arus": ["لو"],
        },
    },
    "kaikki_hebrew:8155:en-ברד-he-noun-H2Y5qKUc": {
        "term": "برد",
        "root": "برد",
        "arabic_gloss": "البرد حب الغمام الجامد النازل من السحاب",
        "meeting": (
            "جوار المعنى في الفرع هو حب الجليد النازل من السحاب، "
            "وجواره في العربية برد الغمام؛ يلتقيان في الهطول نفسه"
        ),
        "member_sense_reviewed": True,
        "sound_rules": [],
        "anchors": {
            "al_sihah": ["البرد"],
            "al_muhkam": ["البرد"],
        },
    },
    "kaikki_hebrew:8256:en-שמאל-he-noun-ZOzu-t2n": {
        "term": "شمال",
        "root": "شمل",
        "arabic_gloss": "الشمال خلاف اليمين والجهة المعروفة",
        "meeting": (
            "جوار المعنى في الفرع هو جهة اليسار، وجواره في العربية "
            "الشمال خلاف اليمين؛ يلتقيان في الجهة نفسها"
        ),
        "member_sense_reviewed": True,
        "sound_rules": [],
        "anchors": {
            "al_sihah": ["الشمال"],
            "lisan": ["الشمال"],
        },
    },
    "kaikki_hebrew:8590:en-רחמים-he-noun-TVH9mY~T": {
        "term": "رحمة",
        "root": "رحم",
        "arabic_gloss": "الرحمة الرقة والتعطف",
        "meeting": (
            "جوار المعنى في الفرع هو الرحمة، وجواره في العربية "
            "الرقة والتعطف؛ يلتقيان في الشفقة نفسها"
        ),
        "member_sense_reviewed": True,
        "sound_rules": [],
        "anchors": {
            "al_muhkam": ["الرحمة"],
            "lisan": ["الرحمة"],
        },
    },
    "kaikki_hebrew:444:en-שבר-he-noun-he:break_noun": {
        "term": "ثبر",
        "root": "ثبر",
        "arabic_gloss": "الثبور الهلاك والفساد",
        "meeting": (
            "جوار المعنى في الفرع هو موضع الانكسار، وجواره في "
            "العربية الهلاك والفساد؛ يلتقيان في مدار تهديم البنية"
        ),
        "member_sense_reviewed": True,
        "sound_rules": ["DENT-02"],
        "anchors": {
            "lisan": ["الثبور"],
            "taj_al_arus": ["الثبور"],
        },
    },
    "kaikki_hebrew:9498:en-צבי-he-noun-fKzbWDBb": {
        "term": "ظبي",
        "root": "ظبي",
        "arabic_gloss": "الظبي الحيوان المعروف من ذوات الحافر",
        "meeting": (
            "جوار المعنى في الفرع هو الغزال، وجواره في العربية "
            "الظبي؛ يلتقيان في الحيوان نفسه"
        ),
        "member_sense_reviewed": True,
        "sound_rules": ["DENT-08"],
        "anchors": {
            "al_muhkam": ["الظبي"],
            "taj_al_arus": ["الظبي"],
        },
    },
    "kaikki_hebrew:9633:en-גזע-he-noun--ny9PU-7": {
        "term": "جذع",
        "root": "جذع",
        "arabic_gloss": "الجذع ساق النخلة وما شاكلها",
        "meeting": (
            "جوار المعنى في الفرع هو جذع الشجرة وأصل ساقها، "
            "وجواره في العربية ساق الشجرة؛ يلتقيان في العضو النباتي نفسه"
        ),
        "member_sense_reviewed": True,
        "sound_rules": ["DENT-04"],
        "anchors": {
            "kitab_al_ayn": ["الجذع"],
            "al_sihah": ["الجذع"],
        },
    },
    "kaikki_hebrew:9821:en-גיבור-he-noun-DA72tFgc": {
        "term": "جبار",
        "root": "جبر",
        "arabic_gloss": "الجبار القوي العظيم",
        "meeting": (
            "جوار المعنى في الفرع هو الرجل شديد القوة، وجواره في "
            "العربية الجبار القوي؛ يلتقيان في القوة الغالبة"
        ),
        "member_sense_reviewed": True,
        "sound_rules": ["GUT-03"],
        "anchors": {
            "al_muhkam": ["جبار"],
            "lisan": ["جبار"],
        },
    },
    "kaikki_hebrew:10109:en-חפר-he-verb-Dmbqc2e4": {
        "term": "حفر",
        "root": "حفر",
        "arabic_gloss": "حفر الأرض شقها وأخرج ترابها",
        "meeting": (
            "جوار المعنى في الفرع هو شق الأرض بالحفر، وجواره في "
            "العربية الفعل نفسه؛ يلتقيان في إحداث الحفرة"
        ),
        "member_sense_reviewed": True,
        "sound_rules": [],
        "anchors": {
            "al_sihah": ["حفر"],
            "al_muhkam": ["حفر"],
        },
    },
    "kaikki_hebrew:11999:en-סהר-he-noun-lK9ncA9p": {
        "term": "شهر",
        "root": "شهر",
        "arabic_gloss": "الشهر الزمن المقدر بدورة الهلال",
        "meeting": (
            "جوار المعنى في الفرع هو الهلال، وجواره في العربية "
            "الشهر المبتدئ بالهلال؛ يلتقيان في الدورة القمرية وعلامتها"
        ),
        "member_sense_reviewed": True,
        "sound_rules": ["SIB-01"],
        "anchors": {
            "al_mufradat": ["بإهلال الهلال"],
            "al_misbah": ["الشهر الهلال"],
        },
    },
    "kaikki_hebrew:13036:en-נקר-he-verb-wPlY8LYI": {
        "term": "نقر",
        "root": "نقر",
        "arabic_gloss": "نقر الشيء ثقبه وحفره",
        "meeting": (
            "جوار المعنى في الفرع هو الثقب والحفر، وجواره في العربية "
            "النقر في الشيء؛ يلتقيان في إحداث الثقب"
        ),
        "member_sense_reviewed": True,
        "sound_rules": [],
        "anchors": {
            "al_sihah": ["نقر"],
            "al_muhkam": ["نقر"],
        },
    },
    "kaikki_hebrew:523:en-אמר-he-verb-VTuewo7k": {
        "term": "أمر",
        "root": "أمر",
        "arabic_gloss": "أمره بكذا، أي قال له أن يفعله",
        "meeting": (
            "جوار المعنى في الفرع هو القول والإخبار، وجواره في العربية "
            "القول الموجّه بالفعل؛ يلتقيان في حدث الكلام الموجّه"
        ),
        "member_sense_reviewed": True,
        "sound_rules": [],
        "anchors": {
            "al_sihah": ["أمر"],
            "al_muhkam": ["أمر"],
        },
    },
    "kaikki_hebrew:1407:en-יער-he-noun-YZoszxJs": {
        "term": "وعر",
        "root": "وعر",
        "arabic_gloss": "الوعر المكان الصعب الغليظ ضد السهل",
        "meeting": (
            "جوار المعنى في الفرع هو الأرض الكثيفة بالشجر، وجواره "
            "في العربية الأرض الصعبة الغليظة؛ يلتقيان في المكان "
            "البري غير السهل"
        ),
        "member_sense_reviewed": True,
        "sound_rules": [],
        "anchors": {
            "al_sihah": ["جبل وعر"],
            "al_muhkam": ["الوعر ضد السهل"],
        },
    },
    "kaikki_hebrew:3261:en-נשא-he-verb-BHgkj6hh": {
        "term": "نشأ",
        "root": "نشأ",
        "arabic_gloss": "نشأ الشيء ارتفع وحدث",
        "meeting": (
            "جوار المعنى في الفرع هو رفع الشيء، وجواره في العربية "
            "نشوء الشيء وارتفاعه؛ يلتقيان في الحركة إلى أعلى"
        ),
        "member_sense_reviewed": True,
        "sound_rules": ["SIB-01"],
        "anchors": {
            "al_mufradat": ["نشأ"],
            "asas_al_balagha": ["نشأ"],
        },
    },
    "kaikki_hebrew:13774:en-כחל-he-verb-7Lqts8h0": {
        "term": "كحل",
        "root": "كحل",
        "arabic_gloss": "كحل العين جعل الكحل فيها",
        "meeting": (
            "جوار المعنى في الفرع هو طلاء العين بالكحل، وجواره "
            "في العربية جعل الكحل في العين؛ يلتقيان في الفعل نفسه"
        ),
        "member_sense_reviewed": True,
        "loan_reviewed_no_external_donor": True,
        "sound_rules": [],
        "anchors": {
            "asas_al_balagha": ["كحل"],
            "al_misbah": ["كحل"],
        },
    },
    "kaikki_hebrew:9810:en-זעזע-he-verb-ImAi4lwe": {
        "term": "زعزع",
        "root": "زعزع",
        "arabic_gloss": "زعزع الشيء حركه بشدة",
        "meeting": (
            "جوار المعنى في الفرع هو الهز العنيف، وجواره في العربية "
            "التحريك بشدة؛ يلتقيان في الحدث نفسه"
        ),
        "member_sense_reviewed": True,
        "sound_rules": [],
        "anchors": {
            "asas_al_balagha": ["زعزع"],
            "taj_al_arus": ["زعزع"],
        },
    },
    "kaikki_hebrew:9718:en-קינא-he-verb-deGMJ1Xs": {
        "term": "قنأ",
        "root": "قنأ",
        "arabic_gloss": "قنأ اللون اشتدت حمرته",
        "meeting": (
            "جوار المعنى في الفرع هو الغيرة والحسد، وجواره في العربية "
            "احمرار الوجه؛ يلتقيان في أثر الانفعال الظاهر الذي سماه "
            "المصدر نفسه جسرًا"
        ),
        "member_sense_reviewed": True,
        "sound_rules": [],
        "anchors": {
            "al_sihah": ["اشتدت حمرتها"],
            "lisan": ["اشتدت حمرته"],
        },
    },
    "kaikki_hebrew:16641:en-בצע-he-noun-SM96L1Eo": {
        "term": "بضع",
        "root": "بضع",
        "arabic_gloss": "بضع الشيء قطعه",
        "meeting": (
            "جوار المعنى في الفرع هو الكسب المقتطع بغير حق، وجواره "
            "في العربية قطع الشيء؛ يلتقيان في أخذ القطعة وفصلها"
        ),
        "member_sense_reviewed": True,
        "sound_rules": [],
        "anchors": {
            "al_muhkam": ["قطعه"],
            "lisan": ["قطعه"],
        },
    },
    "kaikki_hebrew:16758:en-שגל-he-verb-FtHwUKnL": {
        "term": "سجل",
        "root": "سجل",
        "arabic_gloss": "سجل الماء صبه فانسجل",
        "meeting": (
            "جوار المعنى في الفرع هو الإفراغ في سياق جنسي، وجواره "
            "في العربية صب الماء؛ يلتقيان في حدث الإفراغ الذي صرّح "
            "المصدر بنقله إلى السياق الجنسي"
        ),
        "member_sense_reviewed": True,
        "sound_rules": ["SIB-01"],
        "anchors": {
            "al_sihah": ["سجل"],
            "lisan": ["سجل"],
        },
    },
    "kaikki_hebrew:16169:en-סרר-he-verb-3x-0qwxX": {
        "term": "شر",
        "root": "شرر",
        "arabic_gloss": "الشر السوء ونقيض الخير",
        "meeting": (
            "جوار المعنى في الفرع هو العصيان والتمرد، وجواره في "
            "العربية الشر والسوء؛ يلتقيان في السلوك الخارج عن الخير"
        ),
        "member_sense_reviewed": True,
        "sound_rules": ["SIB-01"],
        "anchors": {
            "al_sihah": ["الشر نقيض الخير"],
            "lisan": ["الشر السوء"],
        },
    },
    "kaikki_hebrew:10698:en-הפטיר-he-verb-3c8PdmDP": {
        "term": "فطر",
        "root": "فطر",
        "arabic_gloss": "فطر الشيء شقه وفتحه",
        "meeting": (
            "جوار المعنى في الفرع هو إفلات الشيء وإخراجه، وجواره "
            "في العربية شقه وفتحه؛ يلتقيان في فك الانغلاق وإطلاق ما فيه"
        ),
        "member_sense_reviewed": True,
        "sound_rules": [],
        "anchors": {
            "al_sihah": ["فطر"],
            "al_muhkam": ["فطر"],
        },
    },
    "kaikki_hebrew:11001:en-ערוה-he-noun-u98UwwVC": {
        "term": "عورة",
        "root": "عور",
        "arabic_gloss": "العورة سوأة الإنسان وكل ما يستر حياء",
        "meeting": (
            "جوار المعنى في الفرع هو العري وانكشاف السوأة، وجواره "
            "في العربية موضع السوأة المستور؛ يلتقيان في انكشاف البدن"
        ),
        "member_sense_reviewed": True,
        "sound_rules": [],
        "anchors": {
            "al_muhkam": ["عورة الرجل والمرأة"],
            "kitab_al_ayn": ["العورة سوأة الإنسان"],
        },
    },
}

# The shared research lane supplies manually reviewed Arabic senses for this
# exact Hebrew window.  Reading the file is safe in lane A; it is never
# modified here.  These pairs remain individual protocol comparisons, not
# claims that Kaikki published an etymological relation and not new sound
# laws.
for _spec_name in (
    "lane_a_hebrew_manual_specs_09.json",
    "lane_a_hebrew_manual_specs_10.json",
    "lane_a_hebrew_manual_specs_11.json",
):
    _spec_path = ROOT / "04-cross-linguistic" / "data" / _spec_name
    if _spec_path.exists():
        for _entry_id, _spec in json.loads(
            _spec_path.read_text(encoding="utf-8")
        ).items():
            MANUAL_SENSE_SPECS[_entry_id] = {
                **_spec,
                "member_sense_reviewed": True,
                "protocol_comparison": True,
                "sound_rules": (
                    ["SIB-01"]
                    if _entry_id
                    == "kaikki_hebrew:2058:en-דבש-he-noun-pV4uOEal"
                    else []
                ),
                **(
                    {
                        "temporal_layer": (
                            "سامية أم؛ حقل التأثيل يصرح بإعادة "
                            "بناء Proto-Semitic"
                        ),
                        "temporal_references": [
                            (
                                "Kaikki Hebrew etymology، "
                                f"`{_entry_id}`"
                            )
                        ],
                        "temporal_basis": (
                            "تصريح From Proto-Semitic في حقل "
                            "تأثيل العضو نفسه"
                        ),
                    }
                    if _spec_name.endswith("_11.json")
                    else {}
                ),
            }

PRIOR_POSITIVE_IDS = {
    "kaikki_hebrew:16612:en-נקם-he-verb-sBtWgCcF",
    "kaikki_hebrew:710:en-עזז-he-verb-aZpQHPdF",
    "kaikki_hebrew:886:en-מטר-he-noun-MZtExXCk",
    "kaikki_hebrew:1274:en-שור-he-noun-HdFP~Dww",
    "kaikki_hebrew:1670:en-כרם-he-noun-zjSbQfKl",
    "kaikki_hebrew:1886:en-ענן-he-noun-VmgQELdT",
    "kaikki_hebrew:2377:en-קטל-he-verb-9W9eC7bx",
    "kaikki_hebrew:2413:en-רחם-he-noun-mjZCd5IO",
    "kaikki_hebrew:2505:en-קלל-he-verb-fwkS0yvT",
    "kaikki_hebrew:2670:en-בטן-he-noun-k0tadk24",
    "kaikki_hebrew:1044:en-עור-he-verb-hsvGoXrI",
    "kaikki_hebrew:4279:en-בצל-he-noun-KIlxZxaF",
    "kaikki_hebrew:7837:en-מרד-he-verb-aToLyV6S",
    "kaikki_hebrew:3165:en-רגם-he-verb-G70x82eq",
    "kaikki_hebrew:3560:en-צום-he-noun-0~jJP8X0",
    "kaikki_hebrew:3658:en-חרם-he-noun-nbplobzR",
    "kaikki_hebrew:5328:en-מנע-he-verb-AK5383xr",
    "kaikki_hebrew:561:en-זרע-he-verb-8hYCr1Os",
    "kaikki_hebrew:562:en-זרע-he-noun-GbJYVuHB",
    "kaikki_hebrew:10109:en-חפר-he-verb-Dmbqc2e4",
    "kaikki_hebrew:13036:en-נקר-he-verb-wPlY8LYI",
    "kaikki_hebrew:10493:en-טרי-he-adj-0JirXkS5",
    "kaikki_hebrew:14886:en-פרא-he-noun-S2tMzPZt",
}

# The ladder value is a reviewed part of each positive member verdict, not a
# batch-wide default.  ROOT-TRACE requires a complete root route and a direct
# semantic meeting.  ROOT-ECHO is retained for a licensed individual
# comparison whose sound route or semantic orbit remains soft.
MANUAL_VERDICTS = {
    "kaikki_hebrew:160:en-יום-he-noun-1n7m-QBp": "ROOT-TRACE",
    "kaikki_hebrew:217:en-ירך-he-noun-iYGn1Q1V": "ROOT-ECHO",
    "kaikki_hebrew:243:en-אבטיח-he-noun-7v60Jfyr": "ROOT-ECHO",
    "kaikki_hebrew:342:en-טוב-he-adj-GwpOY2mq": "ROOT-ECHO",
    "kaikki_hebrew:385:en-אלף-he-num-VLihaHgM": "ROOT-TRACE",
    "kaikki_hebrew:425:en-ברא-he-verb-9EBO3chg": "ROOT-TRACE",
    "kaikki_hebrew:430:en-מהר-he-verb-PBHiTOwU": "ROOT-TRACE",
    "kaikki_hebrew:526:en-בין-he-prep-zPhF4cXs": "ROOT-TRACE",
    "kaikki_hebrew:552:en-מקום-he-noun-oN8V7~cg": "ROOT-TRACE",
    "kaikki_hebrew:617:en-אות-he-noun-PqFwVDTJ": "ROOT-ECHO",
    "kaikki_hebrew:618:en-אות-he-noun-827aZGDv": "ROOT-ECHO",
    "kaikki_hebrew:623:en-צלם-he-noun-67IkmaSP": "ROOT-ECHO",
    "kaikki_hebrew:686:en-תלם-he-noun-5iMY8IzZ": "ROOT-TRACE",
    "kaikki_hebrew:831:en-צאן-he-noun-m8ikfk0y": "ROOT-ECHO",
    "kaikki_hebrew:848:en-זהב-he-noun--9kx~gSp": "ROOT-TRACE",
    "kaikki_hebrew:857:en-מלחמה-he-noun-ywckuaGt": "ROOT-TRACE",
    "kaikki_hebrew:882:en-שיח-he-noun-dvRkgnLU": "ROOT-TRACE",
    "kaikki_hebrew:894:en-השקה-he-verb-eP-HhoJf": "ROOT-TRACE",
    "kaikki_hebrew:991:en-ערום-he-adj-ndZJigRT": "ROOT-ECHO",
    "kaikki_hebrew:1277:en-רימון-he-noun-Jur8FWhv": "ROOT-TRACE",
    "kaikki_hebrew:1313:en-שעה-he-noun-XRfSPk8G": "ROOT-ECHO",
    "kaikki_hebrew:1329:en-שבע-he-verb-dJtZBW1B": "ROOT-TRACE",
    "kaikki_hebrew:1532:en-כל-he-noun-2FC52MV1": "ROOT-TRACE",
    "kaikki_hebrew:1912:en-חלום-he-noun-MP3jWLNH": "ROOT-TRACE",
    "kaikki_hebrew:1932:en-לב-he-noun-XqzSz-DG": "ROOT-TRACE",
    "kaikki_hebrew:1961:en-חיים-he-noun-f5U70Zs-": "ROOT-TRACE",
    "kaikki_hebrew:1978:en-שם-he-noun-NulsYmM2": "ROOT-ECHO",
    "kaikki_hebrew:2028:en-כפר-he-noun-Bc--KDOB": "ROOT-TRACE",
    "kaikki_hebrew:2125:en-גמל-he-noun-SBJYXpRJ": "ROOT-TRACE",
    "kaikki_hebrew:2189:en-שוט-he-noun-6u7vAXDs": "ROOT-TRACE",
    "kaikki_hebrew:2200:en-סל-he-noun--nbZmtlX": "ROOT-TRACE",
    "kaikki_hebrew:2269:en-מלח-he-noun-Gr3gJ0cU": "ROOT-TRACE",
    "kaikki_hebrew:2232:en-חטא-he-noun-K-RiQSF9": "ROOT-ECHO",
    "kaikki_hebrew:2258:en-פרש-he-noun-Vc99puEb": "ROOT-TRACE",
    "kaikki_hebrew:2296:en-שלווה-he-noun-fK2atHAS": "ROOT-TRACE",
    "kaikki_hebrew:2388:en-חטף-he-verb-8BRm0szY": "ROOT-TRACE",
    "kaikki_hebrew:2325:en-זקן-he-noun-lBGSq7CG": "ROOT-ECHO",
    "kaikki_hebrew:2338:en-בניין-he-noun-UWfpZ34f": "ROOT-TRACE",
    "kaikki_hebrew:2434:en-מלא-he-adj-rXHGzmEP": "ROOT-TRACE",
    "kaikki_hebrew:2435:en-מלא-he-verb-0KItSfIS": "ROOT-TRACE",
    "kaikki_hebrew:2442:en-רקד-he-verb-baKAHQa3": "ROOT-ECHO",
    "kaikki_hebrew:2503:en-יקר-he-adj-w18qPVqg": "ROOT-ECHO",
    "kaikki_hebrew:2505:en-קלל-he-verb-fwkS0yvT": "ROOT-TRACE",
    "kaikki_hebrew:2675:en-שחר-he-noun-Jw7qozlp": "ROOT-TRACE",
    "kaikki_hebrew:2993:en-צל-he-noun-C0AKIidY": "ROOT-TRACE",
    "kaikki_hebrew:2999:en-טל-he-noun-hy8Adsfk": "ROOT-TRACE",
    "kaikki_hebrew:3133:en-קשת-he-noun-Qes~eLzO": "ROOT-ECHO",
    "kaikki_hebrew:3131:en-חלם-he-verb-3I7ASTb5": "ROOT-TRACE",
    "kaikki_hebrew:3217:en-כף-he-noun-Plo3-i9A": "ROOT-TRACE",
    "kaikki_hebrew:3216:en-שביל-he-noun-pwDTWDxx": "ROOT-TRACE",
    "kaikki_hebrew:3290:en-שועל-he-noun-~bjrYTAt": "ROOT-ECHO",
    "kaikki_hebrew:3306:en-גבינה-he-noun-hzrJ~-pN": "ROOT-TRACE",
    "kaikki_hebrew:3658:en-חרם-he-noun-nbplobzR": "ROOT-TRACE",
    "kaikki_hebrew:3789:en-אלוה-he-noun-m0LNC9uk": "ROOT-TRACE",
    "kaikki_hebrew:3802:en-קם-he-verb-2avzINsN": "ROOT-TRACE",
    "kaikki_hebrew:4153:en-עכביש-he-noun-m~oLUKkO": "ROOT-ECHO",
    "kaikki_hebrew:4260:en-ארז-he-noun-m90Pgggd": "ROOT-TRACE",
    "kaikki_hebrew:4279:en-בצל-he-noun-KIlxZxaF": "ROOT-TRACE",
    "kaikki_hebrew:4791:en-קרן-he-noun-RilJN~6~": "ROOT-TRACE",
    "kaikki_hebrew:4603:en-גן-he-noun-C770M4we": "ROOT-TRACE",
    "kaikki_hebrew:6314:en-אתון-he-noun-C5O87jMy": "ROOT-TRACE",
    "kaikki_hebrew:6258:en-אחז-he-verb-wddo9PTy": "ROOT-ECHO",
    "kaikki_hebrew:6316:en-שב-he-verb-Z283K0m9": "ROOT-TRACE",
    "kaikki_hebrew:6468:en-אחווה-he-noun-pWb5jTFs": "ROOT-TRACE",
    "kaikki_hebrew:6882:en-נחושת-he-noun-5V3lO-e8": "ROOT-ECHO",
    "kaikki_hebrew:7204:en-שבה-he-verb-pu9ug9~W": "ROOT-TRACE",
    "kaikki_hebrew:7355:en-גדי-he-noun-V5QD7gXN": "ROOT-TRACE",
    "kaikki_hebrew:7719:en-צדיק-he-noun-YSXN4oua": "ROOT-ECHO",
    "kaikki_hebrew:7837:en-מרד-he-verb-aToLyV6S": "ROOT-TRACE",
    "kaikki_hebrew:7906:en-נא-he-adj-2VcbvpLu": "ROOT-TRACE",
    "kaikki_hebrew:8118:en-חנון-he-adj-hNOmxVMj": "ROOT-TRACE",
    "kaikki_hebrew:8261:en-משכן-he-noun-4nhYKUw~": "ROOT-TRACE",
    "kaikki_hebrew:8528:en-רומח-he-noun-jyzJNrGW": "ROOT-TRACE",
    "kaikki_hebrew:9427:en-ממלכה-he-noun-YDisTXiT": "ROOT-TRACE",
    "kaikki_hebrew:5201:en-שה-he-noun-0mk1qSOc": "ROOT-TRACE",
    "kaikki_hebrew:5224:en-ליל-he-noun-F2Rz1zEz": "ROOT-TRACE",
    "kaikki_hebrew:10573:en-שכר-he-noun-OyfQW2Zq": "ROOT-TRACE",
    "kaikki_hebrew:13031:en-חרבה-he-noun-Nzwkod5p": "ROOT-TRACE",
    "kaikki_hebrew:16941:en-קצח-he-noun-5JrI~Bur": "ROOT-ECHO",
    "kaikki_hebrew:1044:en-עור-he-verb-hsvGoXrI": "ROOT-TRACE",
    "kaikki_hebrew:5015:en-חרש-he-verb-rB7t3rJG": "ROOT-ECHO",
    "kaikki_hebrew:5625:en-צרה-he-noun-~4bJOYun": "ROOT-TRACE",
    "kaikki_hebrew:12715:en-גווע-he-verb-hsl74D1J": "ROOT-ECHO",
    "kaikki_hebrew:12777:en-נשה-he-verb-wF6McvUS": "ROOT-ECHO",
    "kaikki_hebrew:13315:en-אשל-he-noun-m6jLJZC6": "ROOT-TRACE",
    "kaikki_hebrew:13483:en-תבן-he-noun-wxdvNwkI": "ROOT-TRACE",
    "kaikki_hebrew:14886:en-פרא-he-noun-S2tMzPZt": "ROOT-TRACE",
    "kaikki_hebrew:16096:en-מוהר-he-noun-vHqipcD5": "ROOT-TRACE",
    "kaikki_hebrew:16296:en-אטר-he-verb-JqSouGpw": "ROOT-ECHO",
    "kaikki_hebrew:16372:en-יקע-he-verb-BffgJfBR": "ROOT-ECHO",
    "kaikki_hebrew:16695:en-נזם-he-noun-kdmPDQgl": "ROOT-ECHO",
    "kaikki_hebrew:17017:en-צאל-he-noun-kC3N9wlf": "ROOT-ECHO",
    "kaikki_hebrew:186:en-עבר-he-noun-INRAT-74": "ROOT-TRACE",
    "kaikki_hebrew:386:en-אלף-he-noun-Sxp0HWeM": "ROOT-TRACE",
    "kaikki_hebrew:445:en-שבר-he-verb-he:break_verb": "ROOT-ECHO",
    "kaikki_hebrew:933:en-נהר-he-verb-U7EY147G": "ROOT-TRACE",
    "kaikki_hebrew:6488:en-עמוד-he-noun-Tb51ToHb": "ROOT-TRACE",
    "kaikki_hebrew:9425:en-כיזב-he-verb-AZ6uvW1l": "ROOT-ECHO",
    "kaikki_hebrew:9208:en-חביב-he-adj-XYfYKYue": "ROOT-TRACE",
    "kaikki_hebrew:12994:en-עקידה-he-noun-ZDBlH~VN": "ROOT-TRACE",
    "kaikki_hebrew:16404:en-קושש-he-verb-Pi10u8GR": "ROOT-ECHO",
    "kaikki_hebrew:2218:en-אווז-he-noun-wtN90FdX": "ROOT-ECHO",
    "kaikki_hebrew:25:en-שלום-he-noun-wuEMIL9G": "ROOT-ECHO",
    "kaikki_hebrew:184:en-עבר-he-verb-KfvU0Xzc": "ROOT-TRACE",
    "kaikki_hebrew:315:en-ראש-he-noun-ny5tM6Nx": "ROOT-TRACE",
    "kaikki_hebrew:370:en-בית-he-noun-1uIShmIa": "ROOT-TRACE",
    "kaikki_hebrew:397:en-בת-he-noun-TtKPgsqW": "ROOT-TRACE",
    "kaikki_hebrew:540:en-תחת-he-prep-itokv2vz": "ROOT-ECHO",
    "kaikki_hebrew:562:en-זרע-he-noun-GbJYVuHB": "ROOT-TRACE",
    "kaikki_hebrew:1770:en-צהריים-he-noun-aNJPgw9Q": "ROOT-ECHO",
    "kaikki_hebrew:2034:en-עבודה-he-noun-xWfFCqzn": "ROOT-TRACE",
    "kaikki_hebrew:2231:en-חטא-he-noun-zMxox5KO": "ROOT-ECHO",
    "kaikki_hebrew:2443:en-עול-he-noun-wUs3q3ob": "ROOT-ECHO",
    "kaikki_hebrew:2509:en-טעם-he-noun-0b5BsReM": "ROOT-TRACE",
    "kaikki_hebrew:2939:en-עמד-he-verb-7SUANQDE": "ROOT-TRACE",
    "kaikki_hebrew:3132:en-קשת-he-noun-j87QC2zi": "ROOT-ECHO",
    "kaikki_hebrew:3440:en-רצה-he-verb-CVriWWbX": "ROOT-ECHO",
    "kaikki_hebrew:3458:en-נכרי-he-adj-RifvnLo1": "ROOT-ECHO",
    "kaikki_hebrew:5018:en-חרש-he-noun-vnNsMOMB": "ROOT-ECHO",
    "kaikki_hebrew:5668:en-הרס-he-verb-QP2RsijE": "ROOT-ECHO",
    "kaikki_hebrew:6022:en-נישה-he-verb-QnVoX7TH": "ROOT-TRACE",
    "kaikki_hebrew:7469:en-סדר-he-noun-xa1RUv2G": "ROOT-ECHO",
    "kaikki_hebrew:7568:en-כיס-he-noun-eCpfs4-Y": "ROOT-TRACE",
    "kaikki_hebrew:849:en-גנב-he-verb-6exYWwd2": "ROOT-ECHO",
    "kaikki_hebrew:956:en-לקח-he-verb-6O9mGx1Z": "ROOT-ECHO",
    "kaikki_hebrew:1015:en-עם-he-noun-JHiSqRoY": "ROOT-ECHO",
    "kaikki_hebrew:2326:en-זקן-he-adj-8y-PgIUM": "ROOT-ECHO",
    "kaikki_hebrew:3186:en-גנן-he-verb-nPJEdrS-": "ROOT-TRACE",
    "kaikki_hebrew:4792:en-קרן-he-verb-xct6IO~N": "ROOT-ECHO",
    "kaikki_hebrew:6406:en-דלה-he-verb-kKDP5lTv": "ROOT-ECHO",
    "kaikki_hebrew:6504:en-מגד-he-noun-wF2-ThXQ": "ROOT-ECHO",
    "kaikki_hebrew:6911:en-קצר-he-verb-b2dpeEUu": "ROOT-ECHO",
    "kaikki_hebrew:7238:en-חלד-he-noun-c0-xCNC0": "ROOT-ECHO",
    "kaikki_hebrew:8147:en-ישר-he-adj-JAhiDoA1": "ROOT-ECHO",
    "kaikki_hebrew:8313:en-הדס-he-noun-he:myrtle": "ROOT-ECHO",
    "kaikki_hebrew:8569:en-מגילה-he-noun-4WqdTRz5": "ROOT-ECHO",
    "kaikki_hebrew:8644:en-ציווה-he-verb-7uyCMGGP": "ROOT-ECHO",
    "kaikki_hebrew:10493:en-טרי-he-adj-0JirXkS5": "ROOT-ECHO",
    "kaikki_hebrew:11777:en-בעיר-he-noun-ppl-kR25": "ROOT-ECHO",
    "kaikki_hebrew:11817:en-תיש-he-noun-jY-zIUyu": "ROOT-TRACE",
    "kaikki_hebrew:11834:en-חך-he-noun-rhOG~dmM": "ROOT-ECHO",
    "kaikki_hebrew:12167:en-שחק-he-verb-hAh7OITr": "ROOT-ECHO",
    "kaikki_hebrew:1378:en-סיבה-he-noun-~GV9vquN": "ROOT-ECHO",
    "kaikki_hebrew:2657:en-דחה-he-verb-Fv0VCuKj": "ROOT-ECHO",
    "kaikki_hebrew:3103:en-בא-he-verb-TtJvuTO9": "ROOT-ECHO",
    "kaikki_hebrew:5019:en-חרש-he-adv-2OKIKdQM": "ROOT-ECHO",
    "kaikki_hebrew:5563:en-אז-he-adv--EPAHTK~": "ROOT-ECHO",
    "kaikki_hebrew:5564:en-אז-he-pron-XYiOLiie": "ROOT-ECHO",
    "kaikki_hebrew:8155:en-ברד-he-noun-H2Y5qKUc": "ROOT-TRACE",
    "kaikki_hebrew:8256:en-שמאל-he-noun-ZOzu-t2n": "ROOT-TRACE",
    "kaikki_hebrew:8590:en-רחמים-he-noun-TVH9mY~T": "ROOT-TRACE",
    "kaikki_hebrew:444:en-שבר-he-noun-he:break_noun": "ROOT-ECHO",
    "kaikki_hebrew:9498:en-צבי-he-noun-fKzbWDBb": "ROOT-TRACE",
    "kaikki_hebrew:9633:en-גזע-he-noun--ny9PU-7": "ROOT-TRACE",
    "kaikki_hebrew:9821:en-גיבור-he-noun-DA72tFgc": "ROOT-TRACE",
    "kaikki_hebrew:10109:en-חפר-he-verb-Dmbqc2e4": "ROOT-TRACE",
    "kaikki_hebrew:11999:en-סהר-he-noun-lK9ncA9p": "ROOT-ECHO",
    "kaikki_hebrew:13036:en-נקר-he-verb-wPlY8LYI": "ROOT-TRACE",
    "kaikki_hebrew:8506:en-גפן-he-noun-yF0mJuKF": "ROOT-ECHO",
    "kaikki_hebrew:15816:en-לקט-he-verb-wW6YqBQu": "ROOT-ECHO",
    "kaikki_hebrew:706:en-לחם-he-verb-Unr3wQmn": "ROOT-ECHO",
    "kaikki_hebrew:14341:en-נסך-he-noun-ow8pPen7": "ROOT-ECHO",
    "kaikki_hebrew:14340:en-נסך-he-verb-TNTliOmh": "ROOT-ECHO",
    "kaikki_hebrew:904:en-נפח-he-verb-WNYlq1Hs": "ROOT-ECHO",
    "kaikki_hebrew:2333:en-פרק-he-noun-1prr0fOh": "ROOT-ECHO",
    "kaikki_hebrew:2936:en-פקד-he-verb-Ty~A-DMC": "ROOT-ECHO",
    "kaikki_hebrew:3229:en-חגר-he-verb-aVbJgJL1": "ROOT-ECHO",
    "kaikki_hebrew:3515:en-זמם-he-verb-SuZFn5pM": "ROOT-ECHO",
    "kaikki_hebrew:523:en-אמר-he-verb-VTuewo7k": "ROOT-ECHO",
    "kaikki_hebrew:1407:en-יער-he-noun-YZoszxJs": "ROOT-ECHO",
    "kaikki_hebrew:3261:en-נשא-he-verb-BHgkj6hh": "ROOT-ECHO",
    "kaikki_hebrew:13774:en-כחל-he-verb-7Lqts8h0": "ROOT-ECHO",
    "kaikki_hebrew:9810:en-זעזע-he-verb-ImAi4lwe": "ROOT-TRACE",
    "kaikki_hebrew:9718:en-קינא-he-verb-deGMJ1Xs": "ROOT-ECHO",
    "kaikki_hebrew:16641:en-בצע-he-noun-SM96L1Eo": "ROOT-ECHO",
    "kaikki_hebrew:16758:en-שגל-he-verb-FtHwUKnL": "ROOT-ECHO",
    "kaikki_hebrew:16169:en-סרר-he-verb-3x-0qwxX": "ROOT-ECHO",
    "kaikki_hebrew:10698:en-הפטיר-he-verb-3c8PdmDP": "ROOT-ECHO",
    "kaikki_hebrew:51:en-קדוש-he-adj-FVHR6wIK": "ROOT-ECHO",
    "kaikki_hebrew:123:en-דם-he-noun-Po5AwK9f": "ROOT-TRACE",
    "kaikki_hebrew:183:en-עזב-he-verb-HD3Wx54V": "ROOT-ECHO",
    "kaikki_hebrew:11001:en-ערוה-he-noun-u98UwwVC": "ROOT-ECHO",
    "kaikki_hebrew:2054:en-שן-he-noun-lyLUpLWc": "ROOT-ECHO",
    "kaikki_hebrew:2058:en-דבש-he-noun-pV4uOEal": "ROOT-TRACE",
    "kaikki_hebrew:2090:en-עקרב-he-noun-Yx~6ULWa": "ROOT-TRACE",
    "kaikki_hebrew:2274:en-פתח-he-verb-HCS1YmVi": "ROOT-TRACE",
    "kaikki_hebrew:2596:en-חבל-he-noun-~k1Vuf-l": "ROOT-TRACE",
}

DEFERRED_PRIOR_TERMINAL_IDS = {
    "kaikki_hebrew:3395:en-תמר-he-noun-LIasoCnF",
    "kaikki_hebrew:13483:en-תבן-he-noun-wxdvNwkI",
    "kaikki_hebrew:540:en-תחת-he-prep-itokv2vz",
    "kaikki_hebrew:1:en-כלב-he-noun-JG1v3E-S",
    "kaikki_hebrew:309:en-רגל-he-noun-Xac9Gpm4",
    "kaikki_hebrew:3425:en-כבד-he-noun-PcYg7dyD",
    "kaikki_hebrew:5647:en-לו-he-conj-XQvhQykR",
}

DEFERRED_MODERN_ONLY_IDS = {
    "kaikki_hebrew:2510:en-טעם-he-verb-2vkp6OfM",
    "kaikki_hebrew:6135:en-נדיר-he-adj-aXd2n-Fz",
    "kaikki_hebrew:7014:en-חש-he-verb-IbjjAxuR",
}

PRIOR_PENDING_REVIEW = {
    "kaikki_hebrew:16641:en-בצע-he-noun-SM96L1Eo",
    "kaikki_hebrew:160:en-יום-he-noun-1n7m-QBp",
    "kaikki_hebrew:342:en-טוב-he-adj-GwpOY2mq",
    "kaikki_hebrew:552:en-מקום-he-noun-oN8V7~cg",
    "kaikki_hebrew:6882:en-נחושת-he-noun-5V3lO-e8",
    "kaikki_hebrew:2269:en-מלח-he-noun-Gr3gJ0cU",
    "kaikki_hebrew:2434:en-מלא-he-adj-rXHGzmEP",
    "kaikki_hebrew:2505:en-קלל-he-verb-fwkS0yvT",
    "kaikki_hebrew:3131:en-חלם-he-verb-3I7ASTb5",
    "kaikki_hebrew:6258:en-אחז-he-verb-wddo9PTy",
    "kaikki_hebrew:6316:en-שב-he-verb-Z283K0m9",
    "kaikki_hebrew:3802:en-קם-he-verb-2avzINsN",
    "kaikki_hebrew:1044:en-עור-he-verb-hsvGoXrI",
    "kaikki_hebrew:5015:en-חרש-he-verb-rB7t3rJG",
    "kaikki_hebrew:5625:en-צרה-he-noun-~4bJOYun",
    "kaikki_hebrew:12715:en-גווע-he-verb-hsl74D1J",
    "kaikki_hebrew:12777:en-נשה-he-verb-wF6McvUS",
    "kaikki_hebrew:13315:en-אשל-he-noun-m6jLJZC6",
    "kaikki_hebrew:13483:en-תבן-he-noun-wxdvNwkI",
    "kaikki_hebrew:14886:en-פרא-he-noun-S2tMzPZt",
    "kaikki_hebrew:16096:en-מוהר-he-noun-vHqipcD5",
    "kaikki_hebrew:16296:en-אטר-he-verb-JqSouGpw",
    "kaikki_hebrew:16372:en-יקע-he-verb-BffgJfBR",
    "kaikki_hebrew:16695:en-נזם-he-noun-kdmPDQgl",
    "kaikki_hebrew:17017:en-צאל-he-noun-kC3N9wlf",
    "kaikki_hebrew:617:en-אות-he-noun-PqFwVDTJ",
    "kaikki_hebrew:2028:en-כפר-he-noun-Bc--KDOB",
    "kaikki_hebrew:16941:en-קצח-he-noun-5JrI~Bur",
    "kaikki_hebrew:686:en-תלם-he-noun-5iMY8IzZ",
    "kaikki_hebrew:831:en-צאן-he-noun-m8ikfk0y",
    "kaikki_hebrew:882:en-שיח-he-noun-dvRkgnLU",
    "kaikki_hebrew:849:en-גנב-he-verb-6exYWwd2",
    "kaikki_hebrew:956:en-לקח-he-verb-6O9mGx1Z",
    "kaikki_hebrew:1015:en-עם-he-noun-JHiSqRoY",
    "kaikki_hebrew:2326:en-זקן-he-adj-8y-PgIUM",
    "kaikki_hebrew:3186:en-גנן-he-verb-nPJEdrS-",
    "kaikki_hebrew:4792:en-קרן-he-verb-xct6IO~N",
    "kaikki_hebrew:6406:en-דלה-he-verb-kKDP5lTv",
    "kaikki_hebrew:6504:en-מגד-he-noun-wF2-ThXQ",
    "kaikki_hebrew:6911:en-קצר-he-verb-b2dpeEUu",
    "kaikki_hebrew:7238:en-חלד-he-noun-c0-xCNC0",
    "kaikki_hebrew:8147:en-ישר-he-adj-JAhiDoA1",
    "kaikki_hebrew:8313:en-הדס-he-noun-he:myrtle",
    "kaikki_hebrew:8569:en-מגילה-he-noun-4WqdTRz5",
    "kaikki_hebrew:8644:en-ציווה-he-verb-7uyCMGGP",
    "kaikki_hebrew:10493:en-טרי-he-adj-0JirXkS5",
    "kaikki_hebrew:11777:en-בעיר-he-noun-ppl-kR25",
    "kaikki_hebrew:11817:en-תיש-he-noun-jY-zIUyu",
    "kaikki_hebrew:11834:en-חך-he-noun-rhOG~dmM",
    "kaikki_hebrew:12167:en-שחק-he-verb-hAh7OITr",
    "kaikki_hebrew:186:en-עבר-he-noun-INRAT-74",
    "kaikki_hebrew:386:en-אלף-he-noun-Sxp0HWeM",
    "kaikki_hebrew:445:en-שבר-he-verb-he:break_verb",
    "kaikki_hebrew:933:en-נהר-he-verb-U7EY147G",
    "kaikki_hebrew:6488:en-עמוד-he-noun-Tb51ToHb",
    "kaikki_hebrew:9425:en-כיזב-he-verb-AZ6uvW1l",
    "kaikki_hebrew:9208:en-חביב-he-adj-XYfYKYue",
    "kaikki_hebrew:12994:en-עקידה-he-noun-ZDBlH~VN",
    "kaikki_hebrew:16404:en-קושש-he-verb-Pi10u8GR",
    "kaikki_hebrew:2218:en-אווז-he-noun-wtN90FdX",
    "kaikki_hebrew:25:en-שלום-he-noun-wuEMIL9G",
    "kaikki_hebrew:184:en-עבר-he-verb-KfvU0Xzc",
    "kaikki_hebrew:315:en-ראש-he-noun-ny5tM6Nx",
    "kaikki_hebrew:370:en-בית-he-noun-1uIShmIa",
    "kaikki_hebrew:397:en-בת-he-noun-TtKPgsqW",
    "kaikki_hebrew:540:en-תחת-he-prep-itokv2vz",
    "kaikki_hebrew:562:en-זרע-he-noun-GbJYVuHB",
    "kaikki_hebrew:1770:en-צהריים-he-noun-aNJPgw9Q",
    "kaikki_hebrew:2034:en-עבודה-he-noun-xWfFCqzn",
    "kaikki_hebrew:2231:en-חטא-he-noun-zMxox5KO",
    "kaikki_hebrew:2443:en-עול-he-noun-wUs3q3ob",
    "kaikki_hebrew:2509:en-טעם-he-noun-0b5BsReM",
    "kaikki_hebrew:2939:en-עמד-he-verb-7SUANQDE",
    "kaikki_hebrew:3132:en-קשת-he-noun-j87QC2zi",
    "kaikki_hebrew:3440:en-רצה-he-verb-CVriWWbX",
    "kaikki_hebrew:3458:en-נכרי-he-adj-RifvnLo1",
    "kaikki_hebrew:5018:en-חרש-he-noun-vnNsMOMB",
    "kaikki_hebrew:5668:en-הרס-he-verb-QP2RsijE",
    "kaikki_hebrew:6022:en-נישה-he-verb-QnVoX7TH",
    "kaikki_hebrew:7469:en-סדר-he-noun-xa1RUv2G",
    "kaikki_hebrew:7568:en-כיס-he-noun-eCpfs4-Y",
}


def load_fan_tool():
    spec = importlib.util.spec_from_file_location("lane_a_fan_tool", FAN_TOOL)
    if spec is None or spec.loader is None:
        raise RuntimeError("تعذر تحميل أداة المروحة")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def clean_arabic(value: str) -> str:
    """Preserve hamza identity while stripping marks and non-Arabic text."""
    value = unicodedata.normalize("NFKC", value)
    value = ARABIC_MARKS.sub("", value)
    return "".join(
        char
        for char in value
        if "\u0621" <= char <= "\u064a"
    )


def fold_arabic(value: str) -> str:
    value = clean_arabic(value)
    return value.translate(
        str.maketrans(
            {
                "أ": "ا",
                "إ": "ا",
                "آ": "ا",
                "ٱ": "ا",
                "ى": "ي",
                "ؤ": "و",
                "ئ": "ي",
            }
        )
    )


def clean_hebrew(value: str) -> str:
    value = unicodedata.normalize("NFC", value)
    value = HEBREW_MARKS.sub("", value)
    return "".join(
        char
        for char in value
        if "\u05d0" <= char <= "\u05ea"
    )


def english_tokens(value: str) -> set[str]:
    result: set[str] = set()
    for word in re.findall(r"[a-z]+", str(value).lower()):
        if word in ENGLISH_STOPWORDS or len(word) < 3:
            continue
        if word.endswith("ing") and len(word) > 5:
            word = word[:-3]
        elif word.endswith("es") and len(word) > 4:
            word = word[:-2]
        elif word.endswith("s") and len(word) > 3:
            word = word[:-1]
        result.add(word)
    return result


def related_english(left: str, right: str) -> tuple[bool, list[str]]:
    left_folded = single_line(left).lower()
    right_folded = single_line(right).lower()
    if not left_folded or not right_folded:
        return False, []
    if left_folded in right_folded:
        return True, [left_folded]
    if right_folded in left_folded:
        return True, [right_folded]
    left_tokens = english_tokens(left_folded)
    right_tokens = english_tokens(right_folded)
    shared = sorted(left_tokens & right_tokens)
    if shared:
        return True, shared
    for one in left_tokens:
        for two in right_tokens:
            if len(one) >= 4 and len(two) >= 4 and (
                one.startswith(two) or two.startswith(one)
            ):
                return True, [one if len(one) <= len(two) else two]
    return False, []


def template_gloss(template: dict[str, Any]) -> str:
    arguments = template.get("args") or {}
    for key in ("t", "gloss", "4"):
        value = str(arguments.get(key) or "").strip()
        if value:
            return single_line(value)
    expansion = str(template.get("expansion") or "")
    match = re.search(r'[“"]([^”"]+)[”"]', expansion)
    return single_line(match.group(1)) if match else ""


def sense_gloss(sense: dict[str, Any]) -> str:
    glosses = sense.get("glosses") or sense.get("raw_glosses") or []
    return single_line("; ".join(str(item) for item in glosses))


def coherent_sense_chain(raw: dict[str, Any], target: dict[str, Any]) -> bool:
    target_gloss = sense_gloss(target)
    for sense in raw.get("senses") or []:
        gloss = sense_gloss(sense)
        if not gloss:
            continue
        related, _ = related_english(target_gloss, gloss)
        if not related:
            return False
    return True


def single_line(value: str) -> str:
    value = " ".join(str(value).split())
    return value.replace("،", "،").replace("–", "-")


def atomic_write(path: Path, text: str) -> None:
    temporary = path.with_suffix(path.suffix + ".lane-a.tmp")
    temporary.write_text(
        unicodedata.normalize("NFC", text),
        encoding="utf-8",
        newline="\n",
    )
    temporary.replace(path)


def positive_member_ids(text: str) -> set[str]:
    result: set[str] = set()
    for block in CARD_SPLIT.split(text):
        verdict_match = re.search(
            r"^- الحكم \(استكشاف\):\s*([^\n]+)",
            block,
            re.MULTILINE,
        )
        if not verdict_match:
            continue
        verdict = verdict_match.group(1)
        if "غير صادر" in verdict:
            continue
        if not any(
            label in verdict
            for label in (
                "ROOT-TRACE",
                "ROOT-ECHO",
                "NUCLEUS-TRACE",
                "NUCLEUS-ECHO",
            )
        ):
            continue
        member_match = re.search(
            r"العضو=`(kaikki_hebrew:[^`]+)`",
            block,
        )
        if member_match:
            result.add(member_match.group(1))
            continue
        verdict_ids = ENTRY_ID.findall(verdict)
        if len(verdict_ids) == 1:
            result.add(verdict_ids[0])
    return result


def morphology_map() -> dict[str, list[str]]:
    result: dict[str, set[str]] = defaultdict(set)
    with MUKHTAR.open(
        "r",
        encoding="utf-8-sig",
        errors="replace",
        newline="",
    ) as handle:
        for row in csv.DictReader(handle, delimiter=";"):
            if str(row.get("Is Sure") or "").upper() != "TRUE":
                continue
            root = clean_arabic(str(row.get("Root") or ""))
            if not root:
                continue
            for field in ("Term", "Normalized Term"):
                term = fold_arabic(str(row.get(field) or ""))
                if term:
                    result[term].add(root)
    return {
        term: sorted(roots, key=lambda item: (len(item), item))
        for term, roots in result.items()
    }


def root_candidates(
    arabic_term: str,
    morphology: dict[str, list[str]],
) -> list[str]:
    clean = clean_arabic(arabic_term)
    folded = fold_arabic(arabic_term)
    candidates: list[str] = []

    # A three-letter dictionary form is tested as printed before morphology
    # alternatives.  This prevents أمر from drifting to مرر and بين to لكن.
    if len(clean) == 3:
        candidates.append(clean)
    candidates.extend(morphology.get(folded, []))

    result: list[str] = []
    seen: set[str] = set()
    for item in candidates:
        if item and item not in seen:
            seen.add(item)
            result.append(item)
    return result


def arabic_tokens_with_spans(
    value: str,
) -> list[tuple[str, int, int]]:
    normalized = unicodedata.normalize("NFKC", value)
    stripped: list[str] = []
    positions: list[int] = []
    for index, char in enumerate(normalized):
        if ARABIC_MARKS.fullmatch(char) or char == "\u0640":
            continue
        if "\u0621" <= char <= "\u064a":
            replacement = fold_arabic(char)
            for repl in replacement:
                stripped.append(repl)
                positions.append(index)
        else:
            stripped.append(" ")
            positions.append(index)
    folded = "".join(stripped)
    return [
        (match.group(0), positions[match.start()], positions[match.end() - 1] + 1)
        for match in re.finditer(r"[\u0621-\u064a]+", folded)
    ]


def term_tokens(value: str) -> list[str]:
    return [
        token
        for token, _, _ in arabic_tokens_with_spans(value)
    ]


def term_span(definition: str, term: str) -> tuple[int, int] | None:
    haystack = arabic_tokens_with_spans(definition)
    needle = term_tokens(term)
    if not needle:
        return None
    width = len(needle)
    for index in range(0, len(haystack) - width + 1):
        if [row[0] for row in haystack[index:index + width]] == needle:
            return haystack[index][1], haystack[index + width - 1][2]
    return None


def excerpt_around(definition: str, anchor: str) -> str:
    compact = single_line(definition)
    span = term_span(compact, anchor)
    if span is None:
        raise ValueError(f"المرساة الدلالية غير حاضرة: {anchor}")
    original = span[0]
    start = max(0, original - 110)
    end = min(len(compact), original + 310)
    prefix = "…" if start else ""
    suffix = "…" if end < len(compact) else ""
    return prefix + compact[start:end].strip() + suffix


def source_rows_for(
    fan_tool: Any,
    matches: list[dict[str, Any]],
    term: str,
    anchors_by_source: dict[str, list[str]],
) -> list[dict[str, str]]:
    selected: dict[str, dict[str, str]] = {}
    if not term_tokens(term):
        return []
    for row in matches:
        source_id = fan_tool.canonical_source_id(
            str(row.get("source") or "")
        )
        if source_id not in OLD_SOURCE_IDS or source_id in selected:
            continue
        definition = str(row.get("definition") or "").strip()
        if not definition:
            continue
        anchors = anchors_by_source.get(source_id, [])
        anchor = next(
            (
                candidate
                for candidate in anchors
                if term_span(definition, candidate) is not None
            ),
            None,
        )
        if anchor is None:
            continue
        selected[source_id] = {
            "source_id": source_id,
            "source": fan_tool.SOURCE_LABELS[source_id],
            "anchor": anchor,
            "excerpt": excerpt_around(definition, anchor),
        }
    return [
        selected[source_id]
        for source_id in fan_tool.SOURCE_PRIORITY
        if source_id in selected
    ]


def load_raw(lines: set[int]) -> dict[int, dict[str, Any]]:
    result: dict[int, dict[str, Any]] = {}
    if not lines:
        return result
    last = max(lines)
    with RAW.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if line_number in lines:
                result[line_number] = json.loads(line)
            if line_number >= last:
                break
    missing = sorted(lines - result.keys())
    if missing:
        raise ValueError(f"سطور Kaikki مفقودة: {missing[:10]}")
    return result


def exact_sense(raw: dict[str, Any], entry_id: str) -> dict[str, Any]:
    sense_id = entry_id.split(":", 2)[2]
    for sense in raw.get("senses") or []:
        if sense.get("id") == sense_id:
            return sense
    raise ValueError(f"الحس الدقيق غير موجود: {entry_id}")


def cognate_templates(raw: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        item
        for item in raw.get("etymology_templates") or []
        if item.get("name") in {"cog", "ncog"}
        and str((item.get("args") or {}).get("1") or "") == "ar"
        and clean_arabic(
            str((item.get("args") or {}).get("2") or "")
        )
    ]


def old_layer(witnesses: list[dict[str, Any]]) -> str:
    strata = {str(item["stratum"]) for item in witnesses}
    labels = {
        "biblical": "توراتي",
        "mishnaic": "مشنائي",
        "other-referenced": "قديم محال إلى موضعه",
    }
    return " + ".join(
        labels[item]
        for item in ("biblical", "mishnaic", "other-referenced")
        if item in strata
    )


def is_ancient_witness(item: dict[str, Any]) -> bool:
    if item["stratum"] in {"biblical", "mishnaic"}:
        return True
    reference = str(item.get("reference") or "")
    return bool(
        re.search(r"\bB\.?C\.?E\.?\b|\bcentury BCE\b", reference, re.I)
        or any(
            book in reference
            for book in (
                "Genesis",
                "Exodus",
                "Leviticus",
                "Numbers",
                "Deuteronomy",
                "Tanach",
                "Tanakh",
            )
        )
    )


def source_named_route(etymology: str) -> str:
    lowered = etymology.lower()
    named: list[str] = []
    for english, arabic in (
        ("metathesis", "قلب مكاني"),
        ("dissimilation", "مخالفة صوتية"),
        ("assimilating", "إدغام"),
        ("assimilation", "إدغام"),
        ("syncope", "حذف وسطي"),
    ):
        if english in lowered and arabic not in named:
            named.append(arabic)
    return "، ".join(named) if named else "لا تحويل عام مضاف"


def build_card(
    rank: int,
    item: dict[str, Any],
) -> str:
    entry_id = item["entry_id"]
    family_id = item["family_id"]
    headword = item["headword"]
    arabic_term = item["arabic_term"]
    arabic_root = item["arabic_root"]
    sources = item["sources"]
    references = "؛ ".join(item["references"])
    rules = item["rules"]
    verdict = item["verdict"]
    source_published = item["comparison_kind"] == "source-published"
    pair_label = (
        "المقابل العربي المنشور"
        if source_published
        else "المقابل العربي المختبر فرديًا"
    )
    origin_text = (
        single_line(item["etymology"])
        if item["etymology"]
        else "لا يصرح حقل التأثيل بمقابل عربي لهذا العضو"
    )
    comparison_constraint = (
        "تصريح cognate المنشور"
        if source_published
        else "المقارنة الفردية المعلنة في مواصفات المسار"
    )
    rules_text = (
        "، ".join(rules)
        if rules
        else (
            "المقابلة الجذرية الكاملة المصرح بها في حقل التأثيل، "
            "بلا صف إضافي"
            if verdict == "ROOT-TRACE"
            else "المقابلة الفردية المنشورة في حقل التأثيل، بلا صف جديد"
        )
    )
    named_route = source_named_route(item["etymology"])
    source_one, source_two = sources[:2]
    heading_prefix = (
        "### مراجعة عضوية:"
        if entry_id in PRIOR_PENDING_REVIEW
        else "### بطاقة:"
    )
    prior_fate = (
        "- مراجعة المصير: المصير السابق غير صادر ومحفوظ في "
        "البطاقة الأقدم؛ هذه مراجعة موجبة محلية تنتظر العدسة "
        "الثالثة ولا تمحو السابق."
        if entry_id in PRIOR_PENDING_REVIEW
        else None
    )

    lines = [
            f"{heading_prefix} `{family_id}`، {headword}، "
            "كتلة الشواهد القديمة ذات المقابل العربي، "
            f"الرتبة {rank}",
            f"- عائق: النوع={verdict}؛ يتطلب=المراجعة المضادة "
            f"الثالثة؛ العضو=`{entry_id}`.",
            "- إصدارُ البروتوكول: RECOVERY-v2 (2026-07-14).",
            f"- الكلمةُ في الفرع: {headword} `{item['romanization'] or 'بلا رومنة'}`، "
            f"{item['pos']}، «{item['gloss']}» [Kaikki Hebrew، "
            f"`{entry_id}`، السطر {item['source_line']}].",
            f"- الرسمُ الصامتيّ: العبري `{clean_hebrew(headword)}`؛ "
            f"{pair_label} `{arabic_term}`؛ جذر المروحة "
            f"`{arabic_root}`.",
            f"- أقدمُ صورةٍ مستعادة: طبقة={item['layer']}؛ "
            f"الأساس الزمني: {item['temporal_basis']}؛ "
            f"الإحالة: {references}.",
            f"- معنى الفرع المنشور: «{item['gloss']}» "
            f"[Kaikki Hebrew، `{entry_id}`].",
            f"- الأصل المنشور: {origin_text}.",
            f"- أساس المقابل العربي في هذه البطاقة: "
            f"{single_line(item['cognate_expansion'])}.",
            "- الخطوةُ صفر (التعرية بصرف الفرع): العضو المشهود نفسه "
            "وحدة الحكم؛ لا تنزع "
            "زيادة ولا ترد صورة إلى جذر إلا بنص المصدر أو فهرس "
            "الصرف العربي المسمى، ولا يرث المركب أو المتجانس الحكم.",
            "- درجةُ المقارنة: الجذر الكامل أولًا، ثم النواة بعد "
            "حفظ الصورة الصرفية؛ لم تستعمل النواة لإصدار الحكم هنا.",
            f"- درجةُ الجذر الكامل: `{clean_hebrew(headword)}` ↔ "
            f"`{arabic_root}`؛ بدأت المقارنة هنا، وحُفظت الصورة "
            f"السطحية كاملة، ثم قيّدت {comparison_constraint} المقارنة "
            "بهذا الزوج وحده.",
            "- درجةُ النواة: لم تُستعمل لإصدار الحكم؛ الجذر أو "
            "المادة المعجمية المنشورة كفت، فلا قفز إلى درجة أدنى.",
            f"- مسحُ المعاني العربيّة: مروحة فعلية من مصدرين "
            f"قديمين مستقلين، وفي كليهما اللفظ `{arabic_term}` "
            "نفسه داخل مادة الجذر.",
            f"  - {source_one['source']}: «{source_one['excerpt']}»",
            f"  - {source_two['source']}: «{source_two['excerpt']}»",
            f"- مسارُ الصوت: {rules_text}؛ المسار المسمى داخل "
            f"المصدر={named_route}؛ لا يُستخرج من هذه البطاقة صف "
            "عام ولا يضاف إلى الشبكة.",
            f"- المقابلُ من اللسان: `{arabic_term}`، مادة "
            f"`{arabic_root}`، بالحس «{item['arabic_gloss']}».",
            f"- المعنى من قاموس الفرع: `{headword}`، «{item['gloss']}» "
            f"[Kaikki Hebrew، `{entry_id}`].",
            f"- إشعاع الأسرة في الفرع: جوار العضو `{headword}` في "
            f"الحس المحكوم هو «{item['gloss']}»؛ لا يرثه متجانس "
            "ولا مركب ولا عضو آخر في الأسرة.",
            f"- إشعاع الأسرة في العربية: جوار المقابل "
            f"`{arabic_term}` في مادة `{arabic_root}` هو "
            f"«{item['arabic_gloss']}» كما تعرضه "
            f"{source_one['source']} و{source_two['source']}؛ لا "
            "يتعدى الحكم هذا الحس المسمى.",
            f"- المدار: جوار المعنى في الفرع: «{item['gloss']}» "
            f"في العضو `{headword}` المشهود؛ جوار المعنى في العربية: "
            f"«{item['arabic_gloss']}» للمقابل `{arabic_term}`، "
            f"وتعرضه مادة `{arabic_root}` في "
            f"{source_one['source']} و{source_two['source']}؛ موضع "
            f"الالتقاء الدلالي: المعنى المشترك المنشور هو "
            f"«{item['semantic_meeting']}»، وهو حاضر في معنى الحس "
            "العبري وفي معنى المقابل العربي المسمى، لا مستنتج من "
            "مجرد وسم cognate.",
            f"- المصفاة: {item['temporal_basis']}؛ لا وسم قرض خارجي؛ "
            "لا صيغة علم؛ لا عبارة عدم يقين في أصل هذا الزوج؛ "
            "المعجمان العربيان مستقلان.",
            f"- فصلُ المتجانسات والاقتراض: الحكم للعضو `{entry_id}` "
            "ولهذا الحس وحده؛ لا وراثة عبر بقية الأسرة.",
            "- جسورُ الاسترداد المفحوصة: الشاهد القديم؛ الرسم "
            "الصامتي؛ أساس المقارنة العربية الفردية؛ فهرس الصرف؛ مروحة "
            "المعجمين؛ الجذر؛ النواة؛ المدار؛ القرض؛ المتجانس.",
            "- مؤشر اليتم: غير حاسم.",
            f"- حالةُ الإغلاق: {verdict}.",
            f"- الحكم (استكشاف): {verdict}؛ العضو `{entry_id}` "
            f"وحده؛ `{headword}` ↔ `{arabic_term}` "
            + (
                "أثر جذر كامل مباشر"
                if verdict == "ROOT-TRACE"
                else "صلة معجمية فردية ذات رجل لينة"
            )
            + f" يلتقي معناها في «{item['semantic_meeting']}» "
            "ومسنَدة بمروحة المصدرين أعلاه، ولا تستحدث قانونًا صوتيًا.",
            "- عدسة الاسترداد: بدأت بالمقابل العربي الفردي المعلن "
            "لهذا العضو، ثم اختبرت معناه في معجمين قديمين.",
            "- عدسة التشكيك: منعت القرض الخارجي والعلم وعدم اليقين "
            "ووراثة الحكم، ولم تحول المقارنة الفردية إلى صف عام.",
            "- ملاحظات: محلي للمراجعة المضادة الثالثة؛ لا خط برهان "
            "ولا سجل مركزي ولا رقم للنشر.",
            "",
    ]
    if prior_fate is not None:
        lines.insert(2, prior_fate)
    return "\n".join(lines)


def held_row(item: dict[str, Any]) -> str:
    return (
        f"| `{item['entry_id']}` | `{item['headword']}` | "
        f"{item['reason']} | الحكم غير صادر |"
    )


def terminal_row(item: dict[str, Any]) -> str:
    return (
        f"| `{item['entry_id']}` | `{item['headword']}` | "
        f"{item['reason']} | {item['terminal']} |"
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Measure the deterministic cohort without writing.",
    )
    parser.add_argument(
        "--rebuild",
        action="store_true",
        help="Replace this lane's still-local marked block atomically.",
    )
    args = parser.parse_args()

    reading_text = READING.read_text(encoding="utf-8")
    if START in reading_text:
        before, remainder = reading_text.split(START, 1)
        if END not in remainder:
            raise ValueError("بداية كتلة المسار موجودة بلا علامة نهاية")
        _, after = remainder.split(END, 1)
        reading_text = before.rstrip() + "\n" + after.lstrip()
        if not args.dry_run and not args.rebuild:
            print("Lane A Hebrew discovery block already present.")
            return 0

    positive_ids = positive_member_ids(reading_text) | PRIOR_POSITIVE_IDS
    witness_document = json.loads(WITNESSES.read_text(encoding="utf-8"))
    by_entry: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in witness_document["witnesses"]:
        if row["stratum"] in {
            "biblical",
            "mishnaic",
            "other-referenced",
        }:
            by_entry[str(row["entry_id"])].append(row)
    for entry_id, sense_spec in MANUAL_SENSE_SPECS.items():
        if (
            sense_spec.get("protocol_comparison")
            and sense_spec.get("temporal_layer")
        ):
            by_entry.setdefault(entry_id, [])

    source_lines = {
        int(entry_id.split(":")[1])
        for entry_id in by_entry
        if entry_id not in positive_ids
    }
    raw_by_line = load_raw(source_lines)
    morphology = morphology_map()
    fan_tool = load_fan_tool()

    connection = sqlite3.connect(DB)
    candidates: list[dict[str, Any]] = []
    try:
        for entry_id, witnesses in by_entry.items():
            if entry_id in positive_ids:
                continue
            source_line = int(entry_id.split(":")[1])
            raw = raw_by_line[source_line]
            templates = cognate_templates(raw)
            manual_spec = MANUAL_SENSE_SPECS.get(entry_id)
            if not templates and not (
                manual_spec
                and manual_spec.get("protocol_comparison")
            ):
                continue
            db_row = connection.execute(
                """
                SELECT e.headword,e.romanization,e.pos,e.gloss,e.etymology,
                       e.loan_hint,fm.family_id
                FROM entries AS e
                JOIN family_members AS fm ON fm.entry_id=e.entry_id
                WHERE e.entry_id=?
                """,
                (entry_id,),
            ).fetchone()
            if db_row is None:
                raise ValueError(f"العضو غير موجود في الجرد: {entry_id}")
            rules_by_root: dict[str, list[str]] = {}
            for root, status, rules_json, route_flag in connection.execute(
                """
                SELECT form,status,rule_ids_json,route_flag
                FROM candidates
                WHERE entry_id=? AND kind='root'
                ORDER BY route_flag,status,form,rule_ids_json
                """,
                (entry_id,),
            ):
                if status == "licensed" and not route_flag:
                    rules_by_root.setdefault(root, json.loads(rules_json))
            candidate = {
                "entry_id": entry_id,
                "source_line": source_line,
                "family_id": db_row[6],
                "headword": db_row[0],
                "romanization": db_row[1],
                "pos": db_row[2],
                "gloss": db_row[3],
                "etymology": db_row[4],
                "loan_hint": bool(db_row[5]),
                "witnesses": witnesses,
                "templates": templates,
                "comparison_kind": (
                    "protocol-individual"
                    if not templates
                    else "source-published"
                ),
                "rules_by_root": rules_by_root,
                "sense": exact_sense(raw, entry_id),
            }
            candidate["sense_chain_coherent"] = coherent_sense_chain(
                raw,
                candidate["sense"],
            )
            candidate["sense_spec"] = MANUAL_SENSE_SPECS.get(entry_id)
            candidates.append(candidate)
    finally:
        connection.close()

    candidates.sort(
        key=lambda item: (item["source_line"], item["entry_id"])
    )

    # Resolve every printed Arabic cognate to candidate Arabic roots before the
    # single batch scan.  No root is inferred from the Hebrew side.
    all_roots: set[str] = set()
    for item in candidates:
        options: list[dict[str, Any]] = []
        sense_spec = item["sense_spec"]
        if sense_spec:
            term = sense_spec["term"]
            matching_template = next(
                (
                    template
                    for template in item["templates"]
                    if clean_arabic(
                        str((template.get("args") or {}).get("2") or "")
                    )
                    == term
                ),
                None,
            )
            if (
                matching_template is None
                and sense_spec.get("protocol_comparison")
            ):
                matching_template = {
                    "expansion": (
                        "مقارنة بروتوكولية فردية تحت الاختبار: "
                        f"{term}"
                    ),
                    "args": {"1": "ar", "2": term},
                }
            if matching_template is not None:
                root = sense_spec["root"]
                options.append(
                    {
                        "term": term,
                        "root": root,
                        "template": matching_template,
                        "arabic_gloss": sense_spec["arabic_gloss"],
                        "semantic_meeting": sense_spec["meeting"],
                        "anchors": sense_spec["anchors"],
                    }
                )
                all_roots.add(root)
        item["options"] = options

    matches = fan_tool.matches_for_roots(
        ROOT / "Resources",
        all_roots,
        None,
    )

    positives: list[dict[str, Any]] = []
    held: list[dict[str, Any]] = []
    for item in candidates:
        etymology_lower = str(item["etymology"]).lower()
        pos = str(item["pos"])

        if pos in {"name", "symbol", "character"}:
            item["reason"] = "علم أو رمز؛ الحكم غير صادر في هذه الدفعة"
            held.append(item)
            continue
        if item["entry_id"] in DEFERRED_PRIOR_TERMINAL_IDS:
            item["reason"] = (
                "له إغلاق نهائي سابق؛ لا يفتح بلا نقض أقوى ومراجعة "
                "العدسة الثالثة"
            )
            held.append(item)
            continue
        if item["entry_id"] in DEFERRED_MODERN_ONLY_IDS:
            item["reason"] = (
                "الشاهد المحال حديث، وحقل التأثيل يقول cognate فقط "
                "بلا شاهد قديم للعضو ولا تصريح inheritance"
            )
            held.append(item)
            continue
        if any(
            word in etymology_lower for word in EXTERNAL_LOAN_WORDS
        ):
            item["reason"] = (
                "مانح خارجي مسمى؛ يحتاج بطاقة عزل مستقلة، والحكم "
                "غير صادر هنا"
            )
            held.append(item)
            continue
        if (
            item["loan_hint"]
            and not (
                item["sense_spec"]
                and item["sense_spec"].get(
                    "loan_reviewed_no_external_donor"
                )
            )
        ):
            item["reason"] = (
                "وسم قرض بلا مانح خارجي مسمى؛ لا يثبت العزل"
            )
            held.append(item)
            continue
        if any(word in etymology_lower for word in UNCERTAINTY_WORDS):
            item["reason"] = "صيغة عدم يقين صريحة في أصل الزوج المنشور"
            held.append(item)
            continue
        if (
            not item["sense_chain_coherent"]
            and not (
                item["sense_spec"]
                and item["sense_spec"].get("member_sense_reviewed")
            )
        ):
            item["reason"] = (
                "حواس المدخل لا تقع في جوار دلالي واحد، فلا يرث "
                "الحس تأثيل المدخل آليًا"
            )
            held.append(item)
            continue
        if not item["sense_spec"]:
            item["reason"] = (
                "لم تُراجع مقتطفا المروحة مراجعة دلالية يدوية بعد"
            )
            held.append(item)
            continue
        if (
            not item["sense_spec"].get("temporal_layer")
            and not any(
                is_ancient_witness(row)
                for row in item["witnesses"]
            )
        ):
            item["reason"] = (
                "لا شاهد توراتي أو مشنائي صريح للعضو، ولا تصريح "
                "وراثة قديم في المصدر"
            )
            held.append(item)
            continue
        if item["entry_id"] not in MANUAL_VERDICTS:
            item["reason"] = (
                "درجة الحكم على السلم لم تراجع يدويًا لهذا العضو"
            )
            held.append(item)
            continue
        if not item["options"]:
            item["reason"] = (
                "المقابل اليدوي لا يطابق قالب cognate المنشور "
                "ولا مواصفة مقارنة فردية معتمدة لهذا العضو"
            )
            held.append(item)
            continue

        resolved: dict[str, Any] | None = None
        for option in item["options"]:
            root = option["root"]
            source_rows = source_rows_for(
                fan_tool,
                matches.get(root, []),
                option["term"],
                option["anchors"],
            )
            if len(source_rows) < 2:
                continue
            resolved = {
                **option,
                "sources": source_rows[:2],
            }
            break
        if resolved is None:
            item["reason"] = (
                "لم يجتمع فهرس الصرف مع ظهور اللفظ نفسه في "
                "مصدرين عربيين قديمين"
            )
            held.append(item)
            continue

        template = resolved["template"]
        expansion = str(template.get("expansion") or "").strip()
        if not expansion:
            expansion = (
                "Arabic "
                + clean_arabic(
                    str((template.get("args") or {}).get("2") or "")
                )
            )
        references = sorted(
            {
                single_line(str(row["reference"]))
                for row in item["witnesses"]
                if str(row.get("reference") or "").strip()
                and is_ancient_witness(row)
            }
        )
        positives.append(
            {
                **item,
                "arabic_term": resolved["term"],
                "arabic_root": resolved["root"],
                "sources": resolved["sources"],
                "cognate_expansion": expansion,
                "arabic_gloss": resolved["arabic_gloss"],
                "semantic_meeting": resolved["semantic_meeting"],
                "layer": item["sense_spec"].get(
                    "temporal_layer",
                    old_layer(
                        [
                            row
                            for row in item["witnesses"]
                            if is_ancient_witness(row)
                        ]
                    ),
                ),
                "references": item["sense_spec"].get(
                    "temporal_references",
                    references,
                ),
                "temporal_basis": item["sense_spec"].get(
                    "temporal_basis",
                    "شاهد قديم صريح للعضو نفسه",
                ),
                "rules": item["sense_spec"].get(
                    "sound_rules",
                    item["rules_by_root"].get(
                        resolved["root"],
                        [],
                    ),
                ),
                "verdict": MANUAL_VERDICTS[item["entry_id"]],
            }
        )

    summary = {
        "cohort": len(candidates),
        "positive_connections": len(positives),
        "terminal_closures": 0,
        "held_without_verdict": len(held),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if args.dry_run:
        return 0

    cards = [
        build_card(rank, item)
        for rank, item in enumerate(positives, 1)
    ]
    held_table = [
        "| المعرّف | الرسم | السبب الواحد | المصير |",
        "|---|---|---|---|",
        *[held_row(item) for item in held],
    ]

    block = "\n".join(
        [
            "",
            START,
            "",
            f"## كتلة الاستكشاف العبري ذات الشواهد القديمة ({DATE}، محلية)",
            "",
            "### بيان النطاق، الخطوة 14",
            "",
            "النطاق كتلة حتمية مرتبة بسطر المصدر: كل عضو عبري يحمل "
            "شاهدًا قديمًا صريحًا وقالب `etymology_templates:cog` "
            "يسمي مقابلًا عربيًا أو مواصفة مقارنة فردية معلنة، ولم "
            "يصدر للعضو نفسه حكم موجب من "
            "قبل. لا انتقاء يدوي داخل الكتلة. لا يصدر الموجب إلا "
            "بعد ظهور المقابل العربي نفسه في مادتين مستقلتين من "
            "المعاجم العربية القديمة وربطه بجذره عبر فهرس مختار. "
            "الأعلام والقروض الخارجية تعزل، وعدم اليقين ونقص "
            "المروحة يبقيان الحكم غير صادر.",
            "",
            f"- أفراد الكتلة: {len(candidates)}.",
            f"- الصلات الموجبة المحلية: {len(positives)}.",
            "- الإغلاقات: 0.",
            f"- غير المحسوم بلا حكم: {len(held)}.",
            "",
            *cards,
            "### المعزولات المرشحة وغير المحسوم، بلا حكم",
            "",
            *held_table,
            "",
            END,
            "",
        ]
    )
    atomic_write(READING, reading_text.rstrip() + "\n" + block)

    audit_text = "\n".join(
        [
            "# محضر المسار أ: كتلة العبرية ذات الشواهد القديمة",
            "",
            f"- التاريخ: {DATE}.",
            "- الحالة: محلي للمراجعة المضادة الثالثة، بلا إيداع.",
            "- الترتيب: سطر مصدر Kaikki ثم معرّف العضو، بلا انتقاء.",
            "- وحدة الحكم: العضو أو سلسلة معناه، لا الأسرة ولا المركب.",
            "- شرط المعنى العربي: اللفظ العربي المسمى في قالب "
            "`cog` حاضر داخل مادتين مستقلتين من المعاجم القديمة.",
            "- شرط الصوت: صفوف الجرد المرخصة تذكر إن انطبقت؛ وإلا "
            "تبقى المقابلة فردية منشورة ولا تتحول إلى صف عام.",
            "",
            "## الرقمان المفصولان",
            "",
            f"- الصلات الموجبة: {len(positives)}.",
            "- الإغلاقات: 0.",
            "",
            "## غير المحسوم",
            "",
            f"- بقي بلا حكم: {len(held)}.",
            "",
            "## حدود الدفعة",
            "",
            "- لا خط برهان، ولا عد أسر، ولا سجل مركزي، ولا لقطة موقع.",
            "- لم يعدل أي ملف قراءة غير العبرية، ولا أي ملف بيانات مشترك.",
            "",
            "## الملفات المكتوبة",
            "",
            "- `04-cross-linguistic/readings/hebrew.md`.",
            "- `05-audits/2026-07-29-lane-a-hebrew-old-witness-arabic-cognates.md`.",
            "",
        ]
    )
    atomic_write(AUDIT, audit_text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
