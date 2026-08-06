# -*- coding: utf-8 -*-
"""يضيف حصاد القراءة المباشرة المحافظة للقطتي phn وxpu على دفعات صغيرة.

لا يمحو السكربت بطاقة ولا يغير المحضر السابق. كل بطاقة جديدة تنسخ عائق
SOURCE-GAP للعضو المحدد وحده لأن تكليف 2026-08-05 عد اللمة المثبتة في
المورد شاهدا مباشرا في مقام الاستكشاف المحلي.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent

CONFIG = {
    "phn": {
        "source": ROOT / "Resources" / "phn" / "kaikki.org-phn-bounded-scout.jsonl",
        "reading": ROOT / "04-cross-linguistic" / "readings" / "phoenician-punic-scout.md",
        "label": "الفينيقيّة",
        "prefix": "PHN-DIRECT",
        "batches": {
            1: [4, 7, 9, 10, 51],
            2: [18, 99, 102, 136, 138],
        },
    },
    "xpu": {
        "source": ROOT / "Resources" / "xpu" / "kaikki.org-xpu-bounded-scout.jsonl",
        "reading": ROOT / "04-cross-linguistic" / "readings" / "punic.md",
        "label": "البونيّة",
        "prefix": "XPU-DIRECT",
        "batches": {
            1: [3, 5, 7, 9],
            2: [14, 48, 70],
        },
    },
}

CANDIDATES = {
    ("phn", 4): {
        "entry": "kaikki_phoenician_bounded_2026_07_16:4:en-𐤁𐤕-phn-noun-7YBMDSG5",
        "family": "phoenician:family:06456375f458a476d3687341",
        "roman": "bt /bēt/",
        "branch_gloss": "house",
        "arabic": "بيت",
        "arabic_meaning": "البيت المبني أو بيت الشعر",
        "sources": "لسان العرب لابن منظور، وتاج اللغة وصحاح العربية للجوهري",
        "zero": "يرد المورد الصورة الصوتية /bēt/ ويصلها بالأم *bayt-، فالواو أو الياء الجوفاء مستعادة من المصدر نفسه، لا محذوفة لانتقاء زوج",
        "sound": "b-y-t ↔ ب-ي-ت هوية كاملة بعد رد الجوفاء المثبتة في *bayt-، ولا صف إبدال لازم",
    },
    ("phn", 7): {
        "entry": "kaikki_phoenician_bounded_2026_07_16:7:en-𐤇𐤋𐤁-phn-noun-iCXnZTD4",
        "family": "phoenician:family:8a83bc81336da841400e6e63",
        "roman": "ḥlb",
        "branch_gloss": "milk",
        "arabic": "حلب",
        "arabic_meaning": "استخراج اللبن من الضرع، والحليب ناتج الحدث نفسه",
        "sources": "لسان العرب لابن منظور، وتاج العروس لمرتضى الزبيدي",
        "zero": "الرسم ثلاثي ḥ-l-b بلا زائدة ولا صامت أصلي مسقط",
        "sound": "ḥ-l-b ↔ ح-ل-ب هوية كاملة، ولا صف إبدال لازم",
    },
    ("phn", 9): {
        "entry": "kaikki_phoenician_bounded_2026_07_16:9:en-𐤔𐤋𐤌-phn-noun-wuEMIL9G",
        "family": "phoenician:family:30563d572688eb8e2420b291",
        "roman": "šlm",
        "branch_gloss": "peace",
        "arabic": "سلم",
        "arabic_meaning": "السلم والسلام والبراءة من الآفة",
        "sources": "تاج العروس لمرتضى الزبيدي، وتاج اللغة وصحاح العربية للجوهري",
        "zero": "الرسم ثلاثي š-l-m بلا زائدة ولا صامت أصلي مسقط",
        "sound": "š-l-m ↔ س-ل-م عبر SIB-01 في الصفير الأول، مع هوية اللام والميم",
    },
    ("phn", 10): {
        "entry": "kaikki_phoenician_bounded_2026_07_16:10:en-𐤔𐤌𐤔-phn-noun-J3VvBQ4U",
        "family": "phoenician:family:c891f45e5cb9866db7791210",
        "roman": "šmš",
        "branch_gloss": "sun",
        "arabic": "شمس",
        "arabic_meaning": "الشمس، عين الضح المعروفة",
        "sources": "لسان العرب لابن منظور، وتاج العروس لمرتضى الزبيدي",
        "zero": "الرسم ثلاثي š-m-š بلا زائدة ولا صامت أصلي مسقط",
        "sound": "الصامت الأول š ↔ ش هوية، والميم هوية، والصامت الأخير š ↔ س عبر SIB-01",
    },
    ("phn", 51): {
        "entry": "kaikki_phoenician_bounded_2026_07_16:51:en-𐤏𐤉𐤍-phn-noun-R8IVtfcO",
        "family": "phoenician:family:826040d21d8e40474d54098a",
        "roman": "ʿyn",
        "branch_gloss": "eye",
        "arabic": "عين",
        "arabic_meaning": "حاسة الرؤية والعين المعروفة",
        "sources": "تاج العروس لمرتضى الزبيدي، وتاج اللغة وصحاح العربية للجوهري",
        "zero": "الرسم ثلاثي ʿ-y-n بلا زائدة ولا صامت أصلي مسقط",
        "sound": "ʿ-y-n ↔ ع-ي-ن هوية كاملة، ولا صف إبدال لازم",
    },
    ("phn", 18): {
        "entry": "kaikki_phoenician_bounded_2026_07_16:18:en-𐤊𐤋𐤁-phn-noun-zWNX792W",
        "family": "phoenician:family:29d2635827be3df72e5301e4",
        "roman": "klb",
        "branch_gloss": "dog",
        "arabic": "كلب",
        "arabic_meaning": "الكلب، النوع النابح المعروف",
        "sources": "لسان العرب لابن منظور، وتاج العروس لمرتضى الزبيدي",
        "zero": "الرسم ثلاثي k-l-b بلا زائدة ولا صامت أصلي مسقط",
        "sound": "k-l-b ↔ ك-ل-ب هوية كاملة، ولا صف إبدال لازم",
    },
    ("phn", 99): {
        "entry": "kaikki_phoenician_bounded_2026_07_16:99:en-𐤀𐤊𐤋-phn-verb-Unr3wQmn",
        "family": "phoenician:family:5c3bc14d8294f0c4d52af82f",
        "roman": "ʾkl /ʔakal/",
        "branch_gloss": "to eat",
        "arabic": "أكل",
        "arabic_meaning": "أكل الطعام وإيصاله إلى الجوف",
        "sources": "لسان العرب لابن منظور، وتاج العروس لمرتضى الزبيدي",
        "zero": "الرسم ثلاثي ʾ-k-l بلا زائدة ولا صامت أصلي مسقط",
        "sound": "ʾ-k-l ↔ أ-ك-ل هوية كاملة، ولا صف إبدال لازم",
    },
    ("phn", 102): {
        "entry": "kaikki_phoenician_bounded_2026_07_16:102:en-𐤓𐤀𐤔-phn-noun-ny5tM6Nx",
        "family": "phoenician:family:4223a33ad393f56b205b652b",
        "roman": "rʾš",
        "branch_gloss": "head",
        "arabic": "رأس",
        "arabic_meaning": "رأس الشيء وأعلاه",
        "sources": "لسان العرب لابن منظور، وتاج اللغة وصحاح العربية للجوهري",
        "zero": "الرسم ثلاثي r-ʾ-š، والهمزة أصل مثبت لا صائت مستعار ولا حرف ساقط",
        "sound": "r-ʾ-š ↔ ر-أ-س عبر SIB-01 في الصامت الأخير، مع هوية الراء والهمزة",
    },
    ("phn", 136): {
        "entry": "kaikki_phoenician_bounded_2026_07_16:136:en-𐤒𐤓𐤍-phn-noun-lUMJjxcE",
        "family": "phoenician:family:bbfcb07b8f7243ba925006cf",
        "roman": "qrn",
        "branch_gloss": "horn",
        "arabic": "قرن",
        "arabic_meaning": "قرن الحيوان والروق من رأسه",
        "sources": "لسان العرب لابن منظور، وتاج العروس لمرتضى الزبيدي",
        "zero": "الرسم ثلاثي q-r-n بلا زائدة ولا صامت أصلي مسقط",
        "sound": "q-r-n ↔ ق-ر-ن هوية كاملة، ولا صف إبدال لازم",
    },
    ("phn", 138): {
        "entry": "kaikki_phoenician_bounded_2026_07_16:138:en-𐤉𐤕𐤌-phn-noun-iPaBGrXY",
        "family": "phoenician:family:dcdb8d5f82bb940b335dbbfc",
        "roman": "ytm",
        "branch_gloss": "orphan",
        "arabic": "يتم",
        "arabic_meaning": "فقدان الأب والانفراد، واليتيم من فقد أباه",
        "sources": "لسان العرب لابن منظور، وتاج العروس لمرتضى الزبيدي",
        "zero": "الرسم ثلاثي y-t-m بلا زائدة ولا صامت أصلي مسقط",
        "sound": "y-t-m ↔ ي-ت-م هوية كاملة، ولا صف إبدال لازم",
    },
    ("xpu", 3): {
        "entry": "kaikki_punic_bounded_2026_07_16:3:en-𐤁𐤕-xpu-noun-1uIShmIa",
        "family": "punic:family:05b45dada0e0a831ffe76072",
        "roman": "bt /bēth/",
        "branch_gloss": "house",
        "arabic": "بيت",
        "arabic_meaning": "البيت المبني أو بيت الشعر",
        "sources": "لسان العرب لابن منظور، وتاج اللغة وصحاح العربية للجوهري",
        "zero": "يرد المورد الصورة /bēth/ إلى الفينيقية وإلى *bayt-، فالجوفاء من المصدر نفسه لا من إسقاط انتقائي",
        "sound": "b-y-t ↔ ب-ي-ت هوية كاملة بعد رد الجوفاء المثبتة في *bayt-",
    },
    ("xpu", 5): {
        "entry": "kaikki_punic_bounded_2026_07_16:5:en-𐤇𐤋𐤁-xpu-noun-iCXnZTD4",
        "family": "punic:family:f0e6b16341a6a972e082d2ea",
        "roman": "ḥlb",
        "branch_gloss": "milk",
        "arabic": "حلب",
        "arabic_meaning": "استخراج اللبن من الضرع، والحليب ناتج الحدث نفسه",
        "sources": "لسان العرب لابن منظور، وتاج العروس لمرتضى الزبيدي",
        "zero": "الرسم ثلاثي ḥ-l-b بلا زائدة ولا صامت أصلي مسقط",
        "sound": "ḥ-l-b ↔ ح-ل-ب هوية كاملة، ولا صف إبدال لازم",
    },
    ("xpu", 7): {
        "entry": "kaikki_punic_bounded_2026_07_16:7:en-𐤔𐤋𐤌-xpu-noun-wuEMIL9G",
        "family": "punic:family:b527a3657b14f0da1b7aef0f",
        "roman": "šlm",
        "branch_gloss": "peace",
        "arabic": "سلم",
        "arabic_meaning": "السلم والسلام والبراءة من الآفة",
        "sources": "تاج العروس لمرتضى الزبيدي، وتاج اللغة وصحاح العربية للجوهري",
        "zero": "الحكم خاص باسم السلام في السطر 7، ولا يمس ضمير الملكية المتجانس في السطر 8",
        "sound": "š-l-m ↔ س-ل-م عبر SIB-01 في الصفير الأول، مع هوية اللام والميم",
    },
    ("xpu", 9): {
        "entry": "kaikki_punic_bounded_2026_07_16:9:en-𐤔𐤌𐤔-xpu-noun-J3VvBQ4U",
        "family": "punic:family:0cc0bf61ac69e1928ebcbb7c",
        "roman": "šmš",
        "branch_gloss": "sun",
        "arabic": "شمس",
        "arabic_meaning": "الشمس، عين الضح المعروفة",
        "sources": "لسان العرب لابن منظور، وتاج العروس لمرتضى الزبيدي",
        "zero": "الرسم ثلاثي š-m-š بلا زائدة ولا صامت أصلي مسقط",
        "sound": "الصامت الأول š ↔ ش هوية، والميم هوية، والصامت الأخير š ↔ س عبر SIB-01",
    },
    ("xpu", 14): {
        "entry": "kaikki_punic_bounded_2026_07_16:14:en-𐤊𐤋𐤁-xpu-noun-zWNX792W",
        "family": "punic:family:4e1da5bf40d9e1695de975c6",
        "roman": "klb",
        "branch_gloss": "dog",
        "arabic": "كلب",
        "arabic_meaning": "الكلب، النوع النابح المعروف",
        "sources": "لسان العرب لابن منظور، وتاج العروس لمرتضى الزبيدي",
        "zero": "الرسم ثلاثي k-l-b بلا زائدة ولا صامت أصلي مسقط",
        "sound": "k-l-b ↔ ك-ل-ب هوية كاملة، ولا صف إبدال لازم",
    },
    ("xpu", 48): {
        "entry": "kaikki_punic_bounded_2026_07_16:48:en-𐤓𐤀𐤔-xpu-noun-ny5tM6Nx",
        "family": "punic:family:4287936a3c74d9ae990c6dfd",
        "roman": "rʾš",
        "branch_gloss": "head",
        "arabic": "رأس",
        "arabic_meaning": "رأس الشيء وأعلاه",
        "sources": "لسان العرب لابن منظور، وتاج اللغة وصحاح العربية للجوهري",
        "zero": "الرسم نفسه يحفظ الألف بين الراء والشين، والتأثيل يرده إلى الفينيقية rʾš، فلا تسقط الهمزة",
        "sound": "r-ʾ-š ↔ ر-أ-س عبر SIB-01 في الصامت الأخير، مع هوية الراء والهمزة",
    },
    ("xpu", 70): {
        "entry": "kaikki_punic_bounded_2026_07_16:70:en-𐤒𐤓𐤀-xpu-verb-SnmE33nV",
        "family": "punic:family:6f6a5d63cd4daad933264408",
        "roman": "qrʾ",
        "branch_gloss": "to read",
        "arabic": "قرأ",
        "arabic_meaning": "قراءة المكتوب والقرآن والقراءة",
        "sources": "لسان العرب لابن منظور، وتاج العروس لمرتضى الزبيدي",
        "zero": "الرسم ثلاثي q-r-ʾ بلا زائدة ولا صامت أصلي مسقط، والحكم على سلسلة المعنى الثانية to read المسجلة في السطر الخام لا على to call",
        "sound": "q-r-ʾ ↔ ق-ر-أ هوية كاملة، ولا صف إبدال لازم",
    },
}


def clean(value: str) -> str:
    return " ".join(str(value).replace("—", "،").replace("–", "،").split())


def glosses(row: dict) -> list[str]:
    return [
        str(gloss)
        for sense in row.get("senses", []) or []
        for gloss in sense.get("glosses", []) or []
    ]


def card(code: str, line: int, row: dict, item: dict, audit_id: str) -> str:
    raw_glosses = glosses(row)
    if item["branch_gloss"] not in raw_glosses:
        raise ValueError(f"{code}:{line}: المعنى المقصود غير موجود في السطر الخام")
    word = str(row.get("word") or "")
    etymology = clean(row.get("etymology_text") or "لا يحمل السطر نص تأثيل")
    route = (
        "يصرح المورد بأن الصورة بونيّة موروثة من الفينيقيّة، وهذا استمرار داخل السلسلة الكنعانية لا شاهد عمق مستقل فوق الفينيقية"
        if code == "xpu"
        else "يرد المورد الصورة إلى طبقة سامية أم أو يقارنها داخل الأخوات، ولا يسمي مانحا أجنبيا"
    )
    return f"""
### بطاقة حسم مباشر: {word} `{item['roman']}` «{item['branch_gloss']}»
- إصدارُ البروتوكول: RECOVERY-v2 (2026-07-14)
- معرّف العضو: `{item['entry']}`
- معرّف الأسرة: `{item['family']}`
- الكلمةُ في الفرع: `{word}`، ونسخها `{item['roman']}`، ومعناها «{item['branch_gloss']}».
- أقدمُ صورةٍ مستعادة: `{item['roman']}` كما يثبتها `Resources/{code}` في السطر {line}؛ ونص التأثيل: {etymology}
- شاهد الفرع الخام: `Resources/{code}`، السطر {line}: `{word}` `{item['roman']}`، ومعناه «{item['branch_gloss']}». نص التأثيل: {etymology}
- الخطوةُ صفر (التعرية بصرف الفرع): {item['zero']}.
- درجةُ المقارنة: جذر كامل.
- مسحُ المعاني العربيّة: المروحة الكاملة محفوظة في بطاقة المراجعة العضوية للعضو نفسه، ومصدراها {item['sources']}؛ كلاهما يثبت `{item['arabic']}` في معنى {item['arabic_meaning']}.
- المقابلُ من اللسان: `{item['arabic']}`، {item['arabic_meaning']}.
- مسارُ الصوت: {item['sound']}.
- المعنى من قاموس الفرع: «{item['branch_gloss']}» في السطر الخام المثبت.
- المدار: مباشر بين معنى الفرع ومعنى العربية، بلا أخذ الصورة من مادة والمعنى من أخرى.
- المصفاة: {route}. لا يصدر الحكم من كلمة جوالة أو قرض أكادي أو إيراني أو مصري، ولا من تعمير.
- فصلُ المتجانسات والاقتراض: الحكم خاص بمعرّف العضو ومعناه المسجلين أعلاه، ولا يرثه متجانس أو اسم علم أو معنى آخر.
- مؤشر اليتم: غير يتيم؛ مورد الفرع حاضر، والمروحة العربيّة مثبتة من مصدرين، ومسار الصوت مصرح به.
- جسورُ الاسترداد المفحوصة: الجذر الكامل، والتعرية، والمروحة، والتأثيل، والقرض، والمتجانسات، والتعمير.
- سطر النسخ (2026-08-05، {audit_id}): الحكم السابق غير صادر بسبب `SOURCE-GAP` منسوخ لهذا العضو وحده؛ السبب: تكليف 2026-08-05 عد مورد `{code}` المثبت شاهدًا مباشرًا في هذا المقام، واجتمع معه جذر كامل ومروحة عربيّة من مصدرين ومصفاة قرض سالمة.
- حالةُ الإغلاق: READY محليًا للمراجعة الثالثة.
- الحكم (استكشاف): ROOT-TRACE
- القراءة الدلالية العضوية: اكتملت للعضو المحدد، ولا يضاعف هذا الحكم إن كان له شاهد في اللسان الأخت.
- عدسة الاسترداد: اختبرت الجذر الكامل أولًا، ثم راجعت التعرية والمروحة والتأثيل قبل إصدار الحكم.
- عدسة التشكيك: فحصت الصوامت الأصلية والمتجانسات والقرض والتعمير، ولم تنتق زوجًا ولم تعبر حد مورفيم.
- ملاحظات: بطاقة استكشاف محلية مرتبطة بالسطر الخام ومعرّف العضو، وتنتظر المراجعة الثالثة قبل دخول خط البرهان.
""".rstrip()


def repair_existing(code: str, batch: int, parsed: list[dict], reading: str) -> str:
    cfg = CONFIG[code]
    marker = f"<!-- {cfg['prefix']}-BATCH-{batch:02d}-2026-08-05 -->"
    if marker not in reading:
        raise ValueError(f"لا توجد دفعة لإصلاحها: {marker}")
    repaired = reading
    for line in cfg["batches"][batch]:
        item = CANDIDATES[(code, line)]
        audit_id = f"{cfg['prefix']}-{line:03d}"
        start = repaired.find("### بطاقة حسم مباشر:", repaired.find(marker))
        while start >= 0:
            end = repaired.find("\n### بطاقة حسم مباشر:", start + 1)
            if end < 0:
                end = len(repaired)
            block = repaired[start:end]
            if audit_id in block:
                break
            start = repaired.find("### بطاقة حسم مباشر:", end)
        if start < 0 or audit_id not in block:
            raise ValueError(f"تعذر العثور على البطاقة: {audit_id}")
        row = parsed[line - 1]
        word = str(row.get("word") or "")
        etymology = clean(row.get("etymology_text") or "لا يحمل السطر نص تأثيل")
        if "- الكلمةُ في الفرع:" not in block:
            anchor = f"- معرّف الأسرة: `{item['family']}`\n"
            addition = (
                f"- الكلمةُ في الفرع: `{word}`، ونسخها `{item['roman']}`، ومعناها «{item['branch_gloss']}».\n"
                f"- أقدمُ صورةٍ مستعادة: `{item['roman']}` كما يثبتها `Resources/{code}` في السطر {line}؛ ونص التأثيل: {etymology}\n"
            )
            block = block.replace(anchor, anchor + addition, 1)
        block = block.replace(
            "- الخطوةُ صفر:",
            "- الخطوةُ صفر (التعرية بصرف الفرع):",
            1,
        )
        if "- مؤشر اليتم:" not in block:
            anchor = "- سطر النسخ ("
            addition = (
                "- مؤشر اليتم: غير يتيم؛ مورد الفرع حاضر، والمروحة العربيّة مثبتة من مصدرين، ومسار الصوت مصرح به.\n"
                "- جسورُ الاسترداد المفحوصة: الجذر الكامل، والتعرية، والمروحة، والتأثيل، والقرض، والمتجانسات، والتعمير.\n"
            )
            block = block.replace(anchor, addition + anchor, 1)
        if "- ملاحظات:" not in block:
            block = block.rstrip() + (
                "\n- ملاحظات: بطاقة استكشاف محلية مرتبطة بالسطر الخام ومعرّف العضو، "
                "وتنتظر المراجعة الثالثة قبل دخول خط البرهان.\n"
            )
        repaired = repaired[:start] + block + repaired[end:]
    return repaired


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--code", choices=sorted(CONFIG), required=True)
    parser.add_argument("--batch", type=int, choices=(1, 2), required=True)
    parser.add_argument("--repair-existing", action="store_true")
    args = parser.parse_args()
    cfg = CONFIG[args.code]
    lines = cfg["source"].read_text(encoding="utf-8").splitlines()
    parsed = [json.loads(value) for value in lines if value.strip()]
    expected = 170 if args.code == "phn" else 106
    if len(parsed) != expected:
        raise ValueError(f"اختل عدد أسطر {args.code}: {len(parsed)}")
    marker = f"<!-- {cfg['prefix']}-BATCH-{args.batch:02d}-2026-08-05 -->"
    reading = cfg["reading"].read_text(encoding="utf-8")
    if args.repair_existing:
        repaired = repair_existing(args.code, args.batch, parsed, reading)
        cfg["reading"].write_text(repaired, encoding="utf-8", newline="\n")
        print(f"أصلحت حقول الدفعة {args.batch} في {cfg['reading'].relative_to(ROOT)}")
        return 0
    if marker in reading:
        print(f"الدفعة موجودة من قبل: {marker}")
        return 0
    selected = cfg["batches"][args.batch]
    cards = []
    for line in selected:
        item = CANDIDATES[(args.code, line)]
        if item["entry"] not in reading:
            raise ValueError(f"العضو غير ممثل في ملف القراءة: {item['entry']}")
        audit_id = f"{cfg['prefix']}-{line:03d}"
        if audit_id in reading:
            raise ValueError(f"معرف الحسم موجود بلا علامة الدفعة: {audit_id}")
        cards.append(card(args.code, line, parsed[line - 1], item, audit_id))
    header = f"""

{marker}

## حصاد القراءة المباشرة لمورد `Resources/{args.code}`، الدفعة {args.batch}

هذه إضافة فوق محضر القراءة الكاملة، لا محو له. يظل حكم `SOURCE-GAP` التاريخي ظاهرًا، وينسخ فقط للمعرفات الآتية لأن التكليف الحالي عد اللمم المثبتة في المورد شواهد مباشرة في مقام الاستكشاف المحلي. لا تدخل هذه البطاقات خط البرهان قبل المراجعة الثالثة.

"""
    with cfg["reading"].open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(header + "\n\n".join(cards) + "\n")
    print(f"أضيفت {len(cards)} بطاقات إلى {cfg['reading'].relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
