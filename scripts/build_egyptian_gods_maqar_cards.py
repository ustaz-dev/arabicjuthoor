# -*- coding: utf-8 -*-
"""ابنِ جولةَ المصريّةِ الكبرى من حصادِ خشيم ومقّار في دفعاتٍ ثابتة.

هذا الباني يعيد استعمال قلب ``build_khashim_egyptian_cards.py`` الذي نجح في
جولة بدج: مروحة المرشحين، وتطبيع الجذر العربي، وفهرس النوى، ومسارات الشبكة.
ولا يعيد استعمال مصفاة المعاني الإنجليزية لأن المادة الجديدة عربية الشرح.

الآلة تسترجع ولا تحكم دلاليًا. كل مرشح في المروحة يدخل بيان الدفعة، ويصدر الحكم
الموجب فقط لعضو له مدار مكتوب صراحة في ``HUMAN_ORBITS`` بعد اكتمال الأرجل
الثلاث. غير ذلك يبقى ``OPEN-CANDIDATE`` ولا يتحول غياب المدار إلى اختبار آلي.

الاستعمال:
    python scripts/build_egyptian_gods_maqar_cards.py --batch 1
    python scripts/build_egyptian_gods_maqar_cards.py --check
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
import unicodedata
from collections import Counter
from functools import cache
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import build_khashim_egyptian_cards as K  # noqa: E402
import frozen_event as FE  # noqa: E402
import search_arabic_root_senses as ARS  # noqa: E402
import separate_maqar_egyptian_survivals as MSEP  # noqa: E402

SOURCE = ROOT / "data" / "prior-art-extended-pairs.json"
READING = ROOT / "04-cross-linguistic" / "readings" / "egyptian.md"
AUDIT = ROOT / "05-audits" / "2026-08-12-egyptian-gods-and-maqar-rerun.md"
ROOT_EVENTS_PATH = ROOT / "computational" / "data" / "layer_2_results_v2.jsonl"
MAQAR_COPTIC_SEPARATION = ROOT / "data" / "maqar-egyptian-survivals.json"
MAQAR_EGYPTIAN_SEPARATION = ROOT / "data" / "maqar-ancient-egyptian-survivals.json"
MAQAR_SURVIVALS_READING = (
    ROOT / "04-cross-linguistic" / "exploration" / "maqar-egyptian-survivals.md"
)
MAQAR_START = "<!-- MAQAR-ANCIENT-EGYPTIAN-SURVIVALS:START -->"
MAQAR_END = "<!-- MAQAR-ANCIENT-EGYPTIAN-SURVIVALS:END -->"

BATCH_SIZE = 300
EXPECTED = 2725
EXPECTED_BOOKS = {
    "khashim-gods1": 2046,
    "maqar-egyptian-colloquial": 503,
    "khashim-hieroglyphic": 176,
}
BOOK_ORDER = tuple(EXPECTED_BOOKS)
BOOK_LABELS = {
    "khashim-gods1": "علي فهمي خشيم، «آلهة مصر العربية، الجزء الأول»",
    "maqar-egyptian-colloquial": "سامح مقّار، «أصل الألفاظ العامية من المصرية القديمة»",
    "khashim-hieroglyphic": "علي فهمي خشيم محققًا، «العرب والهيروغليفية»",
}
AUTHOR_LABELS = {
    "khashim-gods1": "علي فهمي خشيم",
    "maqar-egyptian-colloquial": "سامح مقّار",
    "khashim-hieroglyphic": "علي فهمي خشيم",
}

NAME_RE = re.compile(
    r"(?<![\w])(?:إله|الإله|إلهة|الآلهة|معبود|معبودة|رب الأرباب|الرب|رب|"
    r"ربة|حورس|رع|أوزير|إيزيس|آمون|أتوم|خنوم|حتحور|أنوبيس)(?![\w])",
    re.I,
)
ROYAL_NAME_RE = re.compile(
    r"(?:موحّد القطرين|موحد القطرين|أسماء ملوك|اسم ملك|اسم فرعون|أسماء الفراعنة)",
    re.I,
)
FEMININE = re.compile(r"[-.]t$", re.I)
PROPER_FOREIGN = {
    "Mina", "Mena", "Menes", "Ptah", "Ra-neb", "Hermes",
    "Amon", "Amun", "Amen", "Atum", "Ra", "Horus", "Osiris", "Isis",
}


# المدار قراءة بشرية مكتوبة، لا تقاطع ألفاظ آلي. المفتاح هو رتبة الصف في الجرد
# الثابت ثم المرشح الذي صدر له الحكم. تُضاف المدارات على دفعات بعد قراءة العضو.
HUMAN_ORBITS: dict[tuple[int, str], tuple[str, str]] = {
    (0, "من"): (
        "NUCLEUS-TRACE",
        "وصفُ الاسم الملكي بالقوي يطابق وجه القوة والثبات في حدث النواة `من`؛ "
        "فالمدار مباشر في القوة، ولا يرث الاسم منه حكم مفردة معجمية عامة.",
    ),
    (449, "خرد"): (
        "ROOT-TRACE",
        "الطفل والمولود باقيان على الفطرة والأصل قبل الاستعمال والتجربة، وهو الحدث "
        "نفسه في قراءة `خرد` المجمّدة؛ فالمدار مباشر في حداثة الأصل.",
    ),
    (955, "كم"): (
        "NUCLEUS-TRACE",
        "السواد حال غشاء يحجب ظاهر الشيء، وحدث `كم` هو تغطيته بغطاء زائد؛ فالمدار "
        "حال التغطية المظلمة، مع فصل اسم الكلب عن الصفة.",
    ),
    (1491, "جن"): (
        "NUCLEUS-TRACE",
        "البستان المستور بكثافة نباته يحقق الستر والكثافة في حدث `جن`؛ فالمدار "
        "مباشر في هيئة الحديقة المحوطة المستورة.",
    ),
    (1757, "قبس"): (
        "ROOT-TRACE",
        "السطوع النجمي نور مأخوذ من أصل مضيء، والقبس تحصيل مباشر لمادة حادة من "
        "أصلها؛ فالمدار شعلة الضوء المقتبسة، والعلم الإلهي مفصول عن اسم الجنس.",
    ),
    (1807, "دب"): (
        "NUCLEUS-TRACE",
        "ثقل فرس النهر وحركته البطيئة يطابقان الثقل والضغط والدبيب في حدث `دب`؛ "
        "فالمدار مباشر في هيئة الحيوان وحركته.",
    ),
    (2147, "تف"): (
        "NUCLEUS-TRACE",
        "البصاق وسخ رطب يخرج إلى ظاهر الجلد أو الأرض، وحدث `تف` هو الوسخ على الجلد "
        "ونحوه؛ فالمدار مباشر في المادة المطرودة.",
    ),
    (2158, "شن"): (
        "NUCLEUS-TRACE",
        "النفس هواء دقيق ينتشر من الباطن إلى الخارج، وحدث `شن` انتشار الدقاق من "
        "أثناء الشيء؛ فالمدار مباشر في انتشار الزفير.",
    ),
    (2162, "موت"): (
        "ROOT-TRACE",
        "الانتقال إلى عالم الموت هو ذهاب الحياة وهمود الجسد، وهو نص حدث `موت`؛ "
        "فالمدار مباشر بلا واسطة.",
    ),
    (2187, "تم"): (
        "NUCLEUS-TRACE",
        "اكتمال الشيء يميزه وحدة مستقلة عما سواه، وحدث `تم` هو تميز الشيء مستقلًا؛ "
        "فالمدار حال التمام الناتجة.",
    ),
    (2189, "تمم"): (
        "ROOT-TRACE",
        "قول الفرع ينتهي ويكمل يطابق استيفاء جرم الشيء حجمه في حدث `تمم`؛ فالمدار "
        "مباشر في الإكمال.",
    ),
    (2203, "ختم"): (
        "ROOT-TRACE",
        "الإقفال والختم في الفرع هما إنهاء الشيء ومنع الزيادة عليه في حدث `ختم`؛ "
        "فالمدار مباشر.",
    ),
    (2238, "بيت"): (
        "ROOT-TRACE",
        "مسكن رع حيز محيط يستقر فيه ساكنه، وهو حدث `بيت` المجمّد؛ فالمدار مباشر "
        "في معنى المسكن، ولا يرثه معنى السماء على حدة.",
    ),
    (2249, "بيت"): (
        "ROOT-TRACE",
        "المسكن المذكور في معنى الفرع هو الحيز المحيط المستقر في حدث `بيت`؛ فالمدار "
        "مباشر، والياء باب المعتل المسمى لا صامت مصري محذوف.",
    ),
    (2306, "خر"): (
        "NUCLEUS-TRACE",
        "السقوط والنزول نتيجة تخلخل ما كان قائمًا وتسيب أجزائه، وهو حدث `خر`؛ "
        "فالمدار الأثر الناتج من التخلخل.",
    ),
    (2365, "زم"): (
        "NUCLEUS-TRACE",
        "الضم في الفرع هو جمع الكثير باكتناز في حدث `زم`؛ فالمدار مباشر.",
    ),
    (2468, "هد"): (
        "NUCLEUS-TRACE",
        "الضعف تضعضع القائم وتفككه، وهو حدث `هد` المجمّد؛ فالمدار مباشر في انهيار "
        "القوة.",
    ),
    (2470, "هت"): (
        "NUCLEUS-TRACE",
        "الهزيمة تفريق جمع الخصم وإنهاء تماسكه، وحدث `هت` دفع المتجمع إنهاء "
        "لتجمعه؛ فالمدار مباشر في نتيجة الدفع.",
    ),
    (2707, "تم"): (
        "NUCLEUS-TRACE",
        "وصف المعبود بالكامل يلتقي بتميز الشيء مستقلًا عند تمام حدّه في حدث `تم`؛ "
        "فالمدار حال الكمال، والبطاقة لعلم إلهي لا لمفردة معجمية عامة.",
    ),
    (2188, "تمم"): (
        "ROOT-TRACE",
        "الانتهاء والإكمال استيفاء للشيء حتى يتم جرمه، وهو حدث `تمم` المجمّد؛ فالمدار مباشر.",
    ),
    (2190, "تمم"): (
        "ROOT-TRACE",
        "الانتهاء والإكمال استيفاء للشيء حتى يتم جرمه، وهو حدث `تمم` المجمّد؛ فالمدار مباشر.",
    ),
    (2639, "فتح"): (
        "ROOT-TRACE",
        "الخالق في شرح الصف هو مفتتح الخلق ومخرجه من الانغلاق إلى الظهور، وحدث `فتح` فتح منفذ في محيط مغلق؛ والعلم خارج بسط العد.",
    ),
}

# الحكم هنا للعضو نفسه، لا لمرشح صاحب المقارنة. لذلك تمتد القراءة البشرية إلى
# كل صف يحمل الصورة والمعنى نفسيهما متى ظهر المرشح نفسه في المروحة المصححة.
# النص مكتوب يدويًا بعد عرض معنى الفرع وحدث السجل، ولا تولده الآلة من تقاطع ألفاظ.
HUMAN_GROUP_ORBITS: dict[tuple[str, str, str], tuple[str, str]] = {
    ("mn", "موحّد القطرين؛ القوي", "من"): (
        "NUCLEUS-TRACE",
        "وصف الاسم الملكي بالقوة يلتقي مباشرة بالقوة والثبات في حدث `من`؛ والعلم يبقى خارج بسط العد.",
    ),
    ("Mina", "موحّد القطرين؛ القوي", "من"): (
        "NUCLEUS-TRACE",
        "وصف مينا موحّد القطرين بالقوة يلتقي مباشرة بالقوة والثبات في حدث `من`؛ والعلم يبقى خارج بسط العد.",
    ),
    ("MZ", "انتزع وخطف", "مز"): (
        "NUCLEUS-TRACE",
        "الانتزاع فصل للشيء عما كان مجتمعًا به، وحدث `مز` يصرح بالفصل؛ فالمدار مباشر.",
    ),
    ("MT", "مات", "موت"): (
        "ROOT-TRACE",
        "الموت في الفرع هو همود الجسد وذهاب حدته المعتادة في حدث `موت`؛ فالمدار مباشر.",
    ),
    ("BZ", "صب", "بز"): (
        "NUCLEUS-TRACE",
        "الصب خروج المائع من مضيق بضغط، وحدث `بز` هو النفاذ من مضيق؛ فالمدار حركة المائع نفسها.",
    ),
    ("SWR", "شرب", "سور"): (
        "ROOT-TRACE",
        "الشرب تناول للمائع من الإناء، وحدث `سور` يضم التناول من الأعلى؛ فالمدار مباشر في فعل الأخذ.",
    ),
    ("KS", "سكين", "قص"): (
        "NUCLEUS-TRACE",
        "السكين آلة القطع، وحدث `قص` قطع مع تسوية وتتابع؛ فالمدار الآلة وفعلها المباشر.",
    ),
    ("khrd", "طفل؛ صغير؛ مولود", "خرد"): (
        "ROOT-TRACE",
        "الطفل والمولود باقيان على أصل الفطرة قبل الاستعمال، وهو حدث `خرد` المجمّد؛ فالمدار مباشر في حداثة الأصل.",
    ),
    ("emet", "مات", "موت"): (
        "ROOT-TRACE",
        "الفعل المصري «مات» يطابق ذهاب الحياة وهمود الجسد في حدث `موت`؛ فالمدار مباشر.",
    ),
    ("eftek", "شق", "فتق"): (
        "ROOT-TRACE",
        "الشق في الفرع هو الفتح الواصل إلى العمق الملتحم في حدث `فتق`؛ فالمدار مباشر.",
    ),
    ("saq", "جمع", "وسق"): (
        "ROOT-TRACE",
        "الجمع ضم كمية في حوز واحد، وحدث `وسق` حمل الكم العظيم بحوز وثيق؛ فالمدار مباشر في الجمع والحمل.",
    ),
    ("payt", "مقعد؛ فتح؛ باب؛ بيت؛ رجع", "بيت"): (
        "ROOT-TRACE",
        "معنى البيت المصرح به في الصف هو الحيز المحيط الذي يسكن ويستقر فيه في حدث `بيت`؛ والحكم لهذا العضو من السلسلة.",
    ),
    ("bayt", "مقعد؛ فتح؛ باب؛ بيت؛ رجع", "بيت"): (
        "ROOT-TRACE",
        "معنى البيت المصرح به في الصف هو الحيز المحيط الذي يسكن ويستقر فيه في حدث `بيت`؛ والحكم لهذا العضو من السلسلة.",
    ),
    ("mn", "قوي؛ منّة؛ أسماء ملوك؛ وليد رع", "من"): (
        "NUCLEUS-TRACE",
        "صفة القوة في الاسم الملكي هي القوة والثبات نفسيهما في حدث `من`؛ والعلم لا يدخل بسط العد.",
    ),
    ("mn", "ضلع؛ ثور وبقرة وقطيع؛ قوي", "من"): (
        "NUCLEUS-TRACE",
        "عضو القوة المصرح به في معنى الفرع يطابق القوة والثبات في حدث `من`؛ ولا يرثه معنى الحيوان على حدة.",
    ),
    ("Mena", "مينا؛ الدائم أو الراعي", "من"): (
        "NUCLEUS-TRACE",
        "دوام الاسم ورسوخه يطابقان الثبات في حدث `من`؛ والعلم موسوم خارج بسط العد.",
    ),
    ("mt", "طريق", "مت"): (
        "NUCLEUS-TRACE",
        "الطريق امتداد مكاني موصول، وحدث `مت` هو الامتداد مع صفة؛ فالمدار مباشر.",
    ),
    ("tm", "أتوم التام؛ قرص الشمس؛ دائرة", "تم"): (
        "NUCLEUS-TRACE",
        "وصف أتوم بالتام يلتقي بتميز الشيء مستقلًا عند تمام حده في حدث `تم`؛ والعلم خارج بسط العد.",
    ),
    ("gn", "حديقة؛ بستان", "جن"): (
        "NUCLEUS-TRACE",
        "البستان مستور بكثافة نباته وسوره، وحدث `جن` هو الستر والكثافة؛ فالمدار مباشر.",
    ),
    ("gnn", "حديقة؛ بستان", "جنن"): (
        "ROOT-TRACE",
        "الحديقة حيز يستره كثيف النبات، وحدث `جنن` ستر الشيء بكثيف يعلوه أو يحيط به؛ فالمدار مباشر.",
    ),
    ("knn", "حديقة؛ بستان", "كنن"): (
        "ROOT-TRACE",
        "البستان حيز محوط يستر ويحمي ما فيه، وحدث `كنن` هو الستر في تجوف متين؛ فالمدار مباشر.",
    ),
    ("sda", "مستشار أو خازن ملك الدلتا؛ خاتم؛ حامل أختام؛ خزنة", "سد"): (
        "NUCLEUS-TRACE",
        "الخاتم والخزنة يمنعان النفاذ إلى المحفوظ، وحدث `سد` مادة معترضة تمنع المرور؛ فالمدار وظيفة الحفظ والإغلاق.",
    ),
    ("Sed", "مهرجان الذيل؛ الذيل أو النهاية", "سط"): (
        "NUCLEUS-TRACE",
        "الذيل جرم دقيق ممتد ينتهي بغلظ، وهو نص حدث `سط`؛ فالمدار هيئة العضو المصرح به.",
    ),
    ("sd", "مهرجان الذيل؛ الذيل أو النهاية", "سط"): (
        "NUCLEUS-TRACE",
        "الذيل جرم دقيق ممتد ينتهي بغلظ، وهو نص حدث `سط`؛ فالمدار هيئة العضو المصرح به.",
    ),
    ("kht", "حقراء؛ خادم البيت؛ حربة؛ طعن", "خت"): (
        "NUCLEUS-TRACE",
        "وصف الحقارة انتقاص للقدر، وحدث `خت` نقص الحدة أو الجرم؛ فالمدار لعضو الحقارة وحده.",
    ),
    ("khns", "رب القمر؛ المسافر والراحل", "خنس"): (
        "ROOT-TRACE",
        "الرحيل تأخر عن الموضع وغور بعد نتوء، وحدث `خنس` هو التأخر والغور؛ فالمدار حركة المغادرة.",
    ),
    ("qbs", "الآلهة النجمية الساطعة", "قبس"): (
        "ROOT-TRACE",
        "السطوع النجمي نور حاد مأخوذ من أصل مضيء، وحدث `قبس` تحصيل مادة حادة من أصلها؛ والعلم خارج بسط العد.",
    ),
    ("db", "فرس النهر؛ الحمأة العظيمة", "دب"): (
        "NUCLEUS-TRACE",
        "ثقل فرس النهر وحركته البطيئة يطابقان الثقل والضغط والدبيب في حدث `دب`؛ فالمدار مباشر في هيئة الحيوان وحركته.",
    ),
    ("bs", "يدخل؛ يتقدم", "بص"): (
        "NUCLEUS-TRACE",
        "الدخول نفاذ إلى الحيز، وحدث `بص` هو النفاذ والإدراك؛ فالمدار الحركي مباشر.",
    ),
    ("tf", "يبصق", "تف"): (
        "NUCLEUS-TRACE",
        "البصاق أذى رطب يفرز إلى الظاهر، وحدث `تف` وسخ على الجلد ونحوه؛ فالمدار في المادة المطرودة.",
    ),
    ("sn", "يأخذ نفساً", "شن"): (
        "NUCLEUS-TRACE",
        "النفس هواء دقيق ينتشر من الباطن، وحدث `شن` انتشار دقاق من أثناء الشيء؛ فالمدار مباشر في انتشار الزفير.",
    ),
    ("mut", "الانتقال إلى العالم الآخر", "موت"): (
        "ROOT-TRACE",
        "الانتقال إلى عالم الموت هو ذهاب الحياة وهمود الجسد، وهو حدث `موت`؛ فالمدار مباشر.",
    ),
    ("khtm", "يقفل؛ يختم؛ ختم أو عقد", "ختم"): (
        "ROOT-TRACE",
        "الإقفال والختم إنهاء للشيء ومنع للزيادة عليه، وهو حدث `ختم` المجمّد؛ فالمدار مباشر.",
    ),
    ("byt", "سماء؛ مسكن رع", "بيت"): (
        "ROOT-TRACE",
        "مسكن رع حيز محيط يستقر فيه ساكنه، وهو حدث `بيت`؛ والحكم لعضو المسكن دون السماء.",
    ),
    ("pt", "سماء؛ مسكن رع", "بيت"): (
        "ROOT-TRACE",
        "المسكن المصرح به في معنى الفرع هو الحيز المحيط المستقر في حدث `بيت`؛ والحكم لهذا العضو وحده.",
    ),
    ("kfa", "مؤخرة؛ قعر", "كفو"): (
        "ROOT-TRACE",
        "المؤخرة هي الجانب الخلفي المكشوف، وحدث `كفو` انطباق يغطي الجانب الخلفي؛ فالمدار موضع الظهر نفسه.",
    ),
    ("pr", "يخرج", "بر"): (
        "NUCLEUS-TRACE",
        "الخروج خلوص من الحيز وتجرد منه، وحدث `بر` هو التجرد والخلوص؛ فالمدار مباشر.",
    ),
    ("khat", "قليل؛ بعض الشيء", "خت"): (
        "NUCLEUS-TRACE",
        "القلة نقص في الجرم أو القدر، وحدث `خت` نقص الحدة أو الجرم؛ فالمدار مباشر.",
    ),
    ("dh", "إلى أسفل", "ده"): (
        "NUCLEUS-TRACE",
        "الاتجاه إلى أسفل هو الحدر في فراغ أو مهواة في حدث `ده`؛ فالمدار مباشر.",
    ),
    ("rqu", "ترجيح كفة الميزان", "رقو"): (
        "ROOT-TRACE",
        "ترجيح كفة يخفض واحدة ويرفع مقابلها بلطف، وحدث `رقو` ارتفاع بلطف؛ فالمدار حركة الكفة.",
    ),
    ("khr", "يسقط؛ ينزل", "خر"): (
        "NUCLEUS-TRACE",
        "السقوط والنزول نتيجة تخلخل القائم وتسيب أجزائه، وهو حدث `خر`؛ فالمدار مباشر في الأثر.",
    ),
    ("zma", "يضم", "زم"): (
        "NUCLEUS-TRACE",
        "الضم في الفرع هو جمع الكثير باكتناز في حدث `زم`؛ فالمدار مباشر.",
    ),
    ("shd", "يجذب؛ ينقذ؛ يعلم؛ يتلو", "شد"): (
        "NUCLEUS-TRACE",
        "الجذب شد للشيء وتوثيق لاتصاله، وحدث `شد` هو الصلابة والوثاقة؛ والحكم لعضو الجذب وحده.",
    ),
    ("bd", "يهرب؛ يمر", "بدد"): (
        "ROOT-TRACE",
        "الهرب مباعدة دائمة عن الموضع، وحدث `بدد` تفريق وإبعاد ممتد؛ فالمدار حركة الفرار.",
    ),
    ("mkh", "عقل", "مخ"): (
        "NUCLEUS-TRACE",
        "المخ مادة رخوة تتوسط الرأس، وحدث `مخ` توسط مادة رخوة؛ فالمدار العضو ومادته المباشرة.",
    ),
    ("ht", "يهزم؛ يحبط", "هت"): (
        "NUCLEUS-TRACE",
        "الهزيمة تفريق جمع الخصم وإنهاء تماسكه، وحدث `هت` دفع المتجمع إنهاء لتجمعه؛ فالمدار مباشر.",
    ),
    ("wn", "يستريح؛ يتغاضى", "ون"): (
        "NUCLEUS-TRACE",
        "الاستراحة فتور وتوقف عن الحركة، وهو حدث `ون` المجمّد؛ فالمدار مباشر.",
    ),
    ("bsh", "يخرج شيئاً من فمه", "بش"): (
        "NUCLEUS-TRACE",
        "خروج المادة من الفم انتشار ظاهر، وحدث `بش` هو الانتشار الظاهر؛ فالمدار مباشر.",
    ),
    ("bssh", "يقسم", "بشش"): (
        "ROOT-TRACE",
        "القسم تفريق لما كان مجموعًا، وحدث `بشش` انتشار وتفش في الظاهر؛ فالمدار فعل التفريق.",
    ),
    ("itm", "الشمس عند الغروب؛ الإله الكامل", "يتم"): (
        "ROOT-TRACE",
        "الإله الكامل قائم مستقل بذاته، وحدث `يتم` انفراد الشيء مستقلًا؛ والعلم خارج بسط العد.",
    ),
}

# مواضع مقّار المصرية القديمة التي لم يحسمها التصنيف الآلي. None يبقي اللفظ
# العامي في طبقة البقايا وحدها. الأرقام محلية داخل 503 صفوف المصرية القديمة.
MAQAR_CLASSICAL_OVERRIDES: dict[int, str | None] = {
    50: "عمم", 52: "عمم", 72: "حمم", 101: None,
    169: "معع", 170: "معع", 175: None,
    211: "برر", 218: "برر", 219: "بين",
    248: None, 251: None, 267: "خطا",
}


def nfc(value: str) -> str:
    return unicodedata.normalize("NFC", str(value))


def classify_maqar_rows(rows: list[dict[str, Any]]) -> None:
    maqar = [row for row in rows if row.get("book") == "maqar-egyptian-colloquial"]
    if len(maqar) != EXPECTED_BOOKS["maqar-egyptian-colloquial"]:
        raise SystemExit(f"اختل جرد مقّار المصرية القديمة: {len(maqar)}")

    prior = json.loads(MAQAR_COPTIC_SEPARATION.read_text(encoding="utf-8"))
    known: dict[str, str] = {}
    for item in prior["rows"]:
        surface = MSEP.fold_ar(item.get("maqar_colloquial"))
        classical = item.get("classical_root")
        if surface and classical:
            normalized = ARS.normalize_root(classical)
            if surface in known and known[surface] != normalized:
                raise SystemExit(f"تعارض جذر مقّار السابق للصورة {surface}")
            known[surface] = normalized

    wanted = {MSEP.fold_ar(row.get("arabic_root")) for row in maqar}
    morphology = MSEP.build_morphology_index(wanted)
    roots = {ARS.normalize_root(row.get("arabic_root") or "") for row in maqar}
    roots |= {root for values in morphology.values() for root in values}
    roots |= set(known.values())
    roots |= {root for root in MAQAR_CLASSICAL_OVERRIDES.values() if root}
    matches = ARS.matches_for_roots(ROOT / "Resources", roots, None)

    classical_count = 0
    for index, row in enumerate(maqar):
        surface = str(row.get("arabic_root") or "")
        folded = MSEP.fold_ar(surface)
        candidates: list[str] = []
        exact = ARS.normalize_root(surface)
        if exact:
            candidates.append(exact)
        for root in morphology.get(folded, []):
            if root not in candidates:
                candidates.append(root)
        eligible: list[str] = []
        for root in candidates:
            works = MSEP.source_work_ids(matches.get(root, []))
            if not ({"lisan", "taj_al_arus"} & works) or len(works) < 2:
                continue
            if MSEP.mentions_surface(root, surface, matches):
                eligible.append(root)

        basis = "لا شاهد كلاسيكي مستوف للمعيار؛ طبقة البقايا وحدها"
        classical: str | None = None
        if folded in known:
            classical = known[folded]
            basis = "قرار سابق موثق في فصل مقّار القبطي للصورة العامية نفسها"
        elif index in MAQAR_CLASSICAL_OVERRIDES:
            classical = MAQAR_CLASSICAL_OVERRIDES[index]
            basis = (
                "مراجعة يدوية أبقت الصورة العامية في طبقة البقايا وحدها"
                if classical is None else
                "مراجعة يدوية لشاهدي المعجم القديم والصيغة العامية"
            )
        elif len(eligible) == 1:
            classical = eligible[0]
            basis = "لسان العرب أو تاج العروس، ومعجم قديم ثان، وشاهد للصيغة"
        elif len(eligible) > 1:
            raise SystemExit(f"مادة مقّار ملتبسة تحتاج قرارا: {index} {eligible}")

        if classical:
            works = MSEP.source_work_ids(matches.get(classical, []))
            if not ({"lisan", "taj_al_arus"} & works) or len(works) < 2:
                raise SystemExit(f"جذر مقّار بلا شاهدين قديمين: {index} {classical}")
            classical_count += 1
            row["lane"] = "classical-card-and-survival"
            row["classical_root"] = classical
        else:
            row["lane"] = "survival-only"
            row["classical_root"] = None
        row["maqar_colloquial"] = surface
        row["dictionary_candidates"] = eligible
        row["classification_basis"] = basis

    if classical_count != 186:
        raise SystemExit(f"اختل فصل مقّار: الجذور الكلاسيكية {classical_count}، والمتوقع 186")


@cache
def selected_rows() -> list[dict[str, Any]]:
    payload = json.loads(SOURCE.read_text(encoding="utf-8"))
    source_rows = payload["rows"]
    out: list[dict[str, Any]] = []
    for book in BOOK_ORDER:
        if book == "khashim-gods1":
            rows = [
                row for row in source_rows
                if row.get("book") == book
                and row.get("tongue") in {"egyptian", "egyptian-greek", "egyptian-libyan"}
            ]
        elif book == "maqar-egyptian-colloquial":
            rows = [
                row for row in source_rows
                if row.get("book") == book and row.get("tongue") == "ancient-egyptian"
            ]
        else:
            rows = [row for row in source_rows if row.get("book") == book]
        if len(rows) != EXPECTED_BOOKS[book]:
            raise SystemExit(
                f"اختل جرد {book}: {len(rows)}، والمتوقع {EXPECTED_BOOKS[book]}"
            )
        out.extend(rows)
    if len(out) != EXPECTED:
        raise SystemExit(f"اختل الجرد الجامع: {len(out)}، والمتوقع {EXPECTED}")
    classify_maqar_rows(out)
    for row in out:
        if row.get("book") != "maqar-egyptian-colloquial":
            row["lane"] = "disciplined-card"
            row["classical_root"] = row.get("arabic_root")
    return out


def write_maqar_separation(rows: list[dict[str, Any]]) -> None:
    maqar_rows: list[dict[str, Any]] = []
    table_rows: list[str] = []
    for ordinal, row in enumerate(rows, 1):
        if row.get("book") != "maqar-egyptian-colloquial":
            continue
        item = {
            "source_ordinal": ordinal,
            "foreign": row.get("foreign"),
            "foreign_sense": row.get("foreign_sense"),
            "maqar_colloquial": row.get("maqar_colloquial"),
            "page": row.get("page"),
            "lane": row.get("lane"),
            "classical_root": row.get("classical_root"),
            "dictionary_candidates": row.get("dictionary_candidates", []),
            "classification_basis": row.get("classification_basis"),
        }
        maqar_rows.append(item)
        lane = "بطاقة كلاسيكية وبقايا" if row["classical_root"] else "بقايا فقط"
        classical = row["classical_root"] or "لا جذر كلاسيكي مثبت"
        sense = str(row.get("foreign_sense", "")).replace("|", "\\|")
        table_rows.append(
            f"| {ordinal:04d} | `{row['foreign']}` | {sense} | "
            f"`{row['maqar_colloquial']}` | `{classical}` | {lane} |"
        )

    classical = sum(bool(row["classical_root"]) for row in maqar_rows)
    survival = len(maqar_rows) - classical
    payload = {
        "schema": "1.0",
        "generated_by": "scripts/build_egyptian_gods_maqar_cards.py",
        "date": "2026-08-12",
        "source_author": "سامح مقّار",
        "source_book": "أصل الألفاظ العامية من المصرية القديمة",
        "direction": "ancient-egyptian-to-living-egyptian-colloquial",
        "excluded_from_project_link_count": True,
        "source_pairs": len(maqar_rows),
        "survival_only_pairs": survival,
        "classical_cards_retained": classical,
        "rows": maqar_rows,
    }
    MAQAR_EGYPTIAN_SEPARATION.write_text(
        nfc(json.dumps(payload, ensure_ascii=False, indent=1)),
        encoding="utf-8",
        newline="\n",
    )

    block = [
        MAQAR_START,
        "## صفوف المصرية القديمة في كتاب مقّار",
        "",
        "فُصلت في 2026-08-12 صفوف الكتاب الموسومة `ancient-egyptian` بالقاعدة "
        "نفسها التي فُصلت بها صفوفه القبطية. طرف المقارنة العربي عند مقّار هو "
        "لفظ من العامية المصرية الحية، واتجاه دعواه من المصرية القديمة إلى "
        "العامية، وهو عكس اتجاه صلة المشروع. لذلك لا يدخل واحد من الصفوف "
        "الخمسمئة والثلاثة عدّ صلات المشروع من جهة دعوى البقايا.",
        "",
        f"من هذه الصفوف بقي {survival} في طبقة البقايا وحدها لعدم ثبوت جذر "
        f"كلاسيكي مستقل، وأعيد توليد {classical} بطاقة فقط بعد رد الصورة العامية "
        "إلى جذر شهد له لسان العرب أو تاج العروس ومعجم قديم ثان. البطاقة "
        "المتولدة لا ترث اتجاه مقّار ولا حكمه.",
        "",
        "| رتبة الجرد | المصرية القديمة | معنى الفرع | عامية مقّار | الجذر الكلاسيكي | المسار |",
        "|---:|---|---|---|---|---|",
        *table_rows,
        MAQAR_END,
    ]
    text = MAQAR_SURVIVALS_READING.read_text(encoding="utf-8")
    if MAQAR_START in text and MAQAR_END in text:
        before, rest = text.split(MAQAR_START, 1)
        _, after = rest.split(MAQAR_END, 1)
        text = before.rstrip() + "\n\n" + "\n".join(block) + "\n\n" + after.lstrip()
    else:
        anchor = "\n---\n\n*English abstract.*"
        if anchor not in text:
            raise SystemExit("لم يوجد موضع فصل مقّار قبل الملخص الإنجليزي")
        text = text.replace(anchor, "\n\n" + "\n".join(block) + anchor, 1)
    MAQAR_SURVIVALS_READING.write_text(nfc(text), encoding="utf-8", newline="\n")


def root_events() -> dict[str, str]:
    out: dict[str, str] = {}
    for line in ROOT_EVENTS_PATH.read_text(encoding="utf-8").splitlines():
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        root = K.ar_bare(row.get("tri_root", ""))
        event = nfc(row.get("jabal_axial", "")).strip()
        if root and event:
            out[root] = event
    return out


ROOT_EVENTS = root_events()


def script_for(row: dict[str, Any]) -> tuple[str, str]:
    tongue = str(row.get("tongue", ""))
    word = str(row.get("foreign", ""))
    if tongue in {"egyptian", "ancient-egyptian", "egyptian-greek", "egyptian-libyan"}:
        return "egyptian", "رومنة مصرية أو وسم مختلط يبدأ بالمصرية"
    if tongue == "coptic" and any("Ⲁ" <= c <= "⳿" or "Ϣ" <= c <= "ϯ" for c in word):
        return "coptic", "رسم قبطي"
    if tongue == "greek" and any("Ͱ" <= c <= "Ͽ" for c in word):
        return "greek", "رسم يوناني"
    if tongue in {"akkadian"}:
        return "akkadian", "رومنة سامية"
    if tongue in {"hebrew", "syriac", "canaanite", "nabataean", "sabaic", "old_south_arabian"}:
        if any("֐" <= c <= "׿" for c in word):
            return "north", "رسم شمالي سامي"
        return "akkadian", "رومنة سامية محفوظة مع وسم اللسان"
    if tongue == "persian" and any("ء" <= c <= "ی" for c in word):
        return "persian", "رسم فارسي"
    return "latin", "رومنة لاتينية؛ لا تنسب الصف إلى المصرية"


def morphology(row: dict[str, Any], script: str) -> tuple[str, str, list[str]]:
    word = str(row.get("foreign", "")).strip()
    raw = K.FAN.skeleton(word, script)
    if script == "egyptian" and FEMININE.search(word):
        stem = word[:-2]
        return stem, "نزع تاء الاسم المؤنث المكتوبة `-t` أو `.t`", raw
    return word, "لا لاحقة مسماة في صف المصدر، فحُفظت الصوامت كلها", raw


def event_for(candidate: str) -> tuple[str | None, str | None]:
    """الحدثُ المجمَّدُ بالنزولِ الذي نصَّ عليه التعديل 2، لا بعضويّةِ ملفٍّ واحد.

    **ما كان هنا** سؤالٌ واحد: هل الجذرُ في الـ2,285؟ فإن لم يكنْ رجعَ
    `None, None` فأُغلِقَت البطاقةُ بلا حكم. وقد قِيسَت كلفتُه: **23.2%**
    من 30,998 مرشَّحًا مصريًّا وحدَها كان لها حدثٌ بهذا السؤال، و738 بطاقةً
    كُتِبَت في يومٍ واحدٍ فخرجَ منها صفرُ صلة.

    **والقانونُ نصَّ على النزولِ لا على الصمت** (التعديل 2): «وعندَ غيابِه
    يُنزَلُ إلى مسارِ النواةِ كما كان». فصارَ السؤالُ في `frozen_event`
    مرتَّبًا على أربعِ درجاتٍ كلُّها منقولةٌ من ملفٍّ مجمَّد، والتغطيةُ
    23.2% ← 99.3%. والدرجةُ تُكتَبُ في البطاقةِ ليُنقَضَ ما شاءَ المؤلّفُ منها.
    """
    ev = FE.resolve(candidate)
    return (ev.text, ev.source) if ev else (None, None)


def sound_for(stem: str, candidate: str, script: str) -> tuple[bool, list[str], list[str]]:
    if script != "egyptian":
        return False, [], [
            "الصف من لسان غير مصري داخل كتاب الهيروغليفية؛ لم يُنسب إليه مسار مصري"
        ]
    return K.sound_audit(stem, candidate)


def is_name(row: dict[str, Any], ordinal: int) -> tuple[bool, str]:
    joined = " ".join(
        str(row.get(key, "")) for key in ("foreign_sense", "arabic_gloss")
    )
    if (
        str(row.get("foreign", "")) in PROPER_FOREIGN
        or ordinal in {0, 2707}
        or NAME_RE.search(joined)
        or ROYAL_NAME_RE.search(joined)
    ):
        return True, "عَلَم أو عنصر عَلَم بحسب معنى الصف؛ لا يعامل مفردة معجمية عامة"
    if row.get("book") == "khashim-gods1":
        return False, "مفردة في سياق كتاب الآلهة؛ لم يثبت من هذا الصف وحده أنها عَلَم"
    return False, "مفردة معجمية بحسب صف المصدر؛ لا عَلَم مصرحًا به"


def candidate_audits(
    row: dict[str, Any], ordinal: int, stem: str, script: str
) -> tuple[list[dict[str, Any]], str, int | None]:
    fan = K.FAN.fan(stem, script, limit=400)
    author = K.ar_bare(row.get("classical_root") or row.get("arabic_root", ""))
    candidates = list(fan)
    author_position: int | None = None
    if author:
        if author in candidates:
            author_position = candidates.index(author) + 1
        else:
            candidates.append(author)
    audits: list[dict[str, Any]] = []
    for position, candidate in enumerate(candidates, 1):
        sound_ready, sound_rows, sound_misses = sound_for(stem, candidate, script)
        event, event_source = event_for(candidate)
        orbit_spec = HUMAN_ORBITS.get((ordinal, candidate)) or HUMAN_GROUP_ORBITS.get(
            (str(row.get("foreign", "")), str(row.get("foreign_sense", "")), candidate)
        )
        audits.append({
            "candidate": candidate,
            "position": position if candidate in fan else None,
            "origin": "مروحة الأداة" if candidate in fan else (
                "الجذر الكلاسيكي المستعاد خارج المروحة"
                if row.get("lane") == "classical-card-and-survival" else
                "مرشح المؤلف خارج المروحة"
            ),
            "sound_ready": sound_ready,
            "sound_rows": sound_rows,
            "sound_misses": sound_misses,
            "event": event,
            "event_source": event_source,
            "event_tier": (lambda e: f"درجة {e.tier}، {e.tier_ar}" if e else None)(
                FE.resolve(candidate)),
            "branch_sense": row.get("foreign_sense", ""),
            "human_orbit": orbit_spec[1] if orbit_spec else None,
            "degree": orbit_spec[0] if orbit_spec else None,
            "positive": bool(orbit_spec and sound_ready and event),
            "state": orbit_spec[0] if orbit_spec and sound_ready and event else "OPEN-CANDIDATE",
        })
    return audits, author, author_position


def compact_fan(values: list[str]) -> str:
    if not values:
        return "(لم تولد المروحة مرشحًا؛ بقي مرشح المؤلف محفوظًا)"
    return "، ".join(f"`{value}`" for value in values)


def render_card(row: dict[str, Any], ordinal: int, batch: int) -> tuple[str, dict[str, Any]]:
    script, script_note = script_for(row)
    stem, stripping, raw_skeleton = morphology(row, script)
    stem_skeleton = K.FAN.skeleton(stem, script)
    buggy_raw_skeleton = (
        K.skeleton_from_table(str(row.get("foreign", "")), K.faulty_egyptian_table())
        if script == "egyptian" else []
    )
    foreign = str(row.get("foreign", ""))
    first = foreign[:1].lower()
    case_head_restored = bool(
        script == "egyptian"
        and foreign[:1].isascii()
        and foreign[:1].isupper()
        and raw_skeleton
        and raw_skeleton[0] == first
        and (not buggy_raw_skeleton or buggy_raw_skeleton[0] != first)
    )
    audits, author_root, author_position = candidate_audits(row, ordinal, stem, script)
    fan_values = [item["candidate"] for item in audits if item["origin"] == "مروحة الأداة"]
    positives = [item for item in audits if item["positive"]]
    if len(positives) > 1:
        raise SystemExit(f"تعددت الأحكام في الصف {ordinal} بلا بطاقة طبقة مستقلة")
    positive = positives[0] if positives else None
    focus = positive or next((x for x in audits if x["candidate"] == author_root), None)
    focus = focus or next((x for x in audits if x["event"]), None)
    focus = focus or (audits[0] if audits else None)
    is_proper, name_note = is_name(row, ordinal)
    closure = positive["degree"] if positive else "OPEN-CANDIDATE"
    verdict = (
        f"**{positive['degree']} (استكشاف)**"
        if positive else "**غير صادر (استكشاف)**"
    )
    focus_root = focus["candidate"] if focus else "(لا مرشح قابل للرصف)"
    focus_event = focus.get("event") if focus else None
    focus_source = focus.get("event_source") if focus else None
    sound_rows = focus.get("sound_rows", []) if focus else []
    sound_misses = focus.get("sound_misses", []) if focus else []
    sound_text = "؛ ".join(sound_rows + sound_misses) or "لا رصف صوتي صادر"
    orbit = positive["human_orbit"] if positive else (
        "لم يُكتب مدار موجب لهذا العضو؛ الآلة عرضت المروحة ولم تحوّل المعنى إلى اختبار"
    )
    ready_candidates = [x for x in audits if x["event"] and x["sound_ready"]]
    eventless = sum(not x["event"] for x in audits)
    sound_open = sum(not x["sound_ready"] for x in audits)
    comparison_place = (
        f"الموضع {author_position} من {len(fan_values)}"
        if author_position else "خارج المروحة، فحُفظ ولم يحتكر الحكم"
    )
    if row.get("lane") == "classical-card-and-survival":
        comparison_line = (
            f"- صورة مقّار العامية: `{row['maqar_colloquial']}`؛ ردها المشروع إلى "
            f"الجذر الكلاسيكي `{author_root or '(غير مستخرج)'}`؛ {comparison_place}. "
            "هذا الرد مستقل عن دعوى اتجاه البقايا ولا ينسب الجذر إلى مقّار."
        )
    else:
        comparison_line = (
            f"- موضعُ مرشح المؤلف: `{author_root or '(غير مستخرج)'}`؛ {comparison_place}؛ "
            f"نص شرحه: «{row['arabic_gloss']}»."
        )
    required = "لا عائق معلق" if positive else (
        "مدار بشري مكتوب لمرشح تكتمل له رجل الصوت وحدث السجل؛ أو إبقاء المرشح مفتوحًا"
    )
    rid = f"extended-egyptian:{ordinal + 1:04d}"
    book = str(row["book"])
    lines = [
        f"### بطاقة: `{rid}`؛ `{row['foreign']}` «{row['foreign_sense']}»",
        f"<!-- EGYPTIAN-GODS-MAQAR:{ordinal + 1:04d} -->",
        "- إصدارُ البروتوكول: RECOVERY-v2؛ طبقةُ استكشاف.",
        f"- نسبةُ المصدر: {BOOK_LABELS[book]}، ص {row['page']}؛ حقل المصدر "
        f"`{row['source']}`. المرشح والشرح للمؤلف، والمروحة والمسار والحكم للمشروع.",
        f"- الكلمةُ في الفرع: `{row['foreign']}`؛ وسم اللسان في الحصاد "
        f"`{row['tongue']}` «{row['tongue_ar']}»؛ {script_note}.",
        f"- جردُ العَلَم: {name_note}.",
        "- أقدمُ صورةٍ مستعادة: لا تُدعى صورة أقدم من الرسم المنقول في الكتاب؛ "
        "رقم الصفحة هو سند هذه الجولة، وأي تأريخ أقدم يبقى سؤال مصدر.",
        f"- الخطوةُ صفر (التعرية بصرف الفرع): {stripping} ← اللب `{stem}`.",
        f"- حسابُ الصوامت: الخام `{' '.join(raw_skeleton) or '∅'}` = {len(raw_skeleton)}؛ "
        f"اللب `{' '.join(stem_skeleton) or '∅'}` = {len(stem_skeleton)}؛ لم يُسقط صامت أصلي بحدس.",
        *([
            f"- استردادُ الصدر بعد إصلاح التصغير: اللقطة المعيبة كانت `{' '.join(buggy_raw_skeleton) or '∅'}`، "
            f"والمروحة المصححة بدأت بـ`{raw_skeleton[0]}` في `{' '.join(raw_skeleton)}`."
        ] if case_head_restored else []),
        "- درجةُ المقارنة: فُحص الجذر الكامل والنواة استقلالًا في عرض واحد؛ ولا "
        "تُستخرج نواة من ساق ذات صامت ثالث أصلي بلا تعرية منشورة.",
        f"- مروحةُ المرشحين من أداتنا: شُغّل `fan_any_script.py` بلسان `{script}`؛ "
        f"المرشحون ({len(fan_values)}): {compact_fan(fan_values)}.",
        comparison_line,
        f"- مسحُ المعاني العربيّة: سجّل بيان الدفعة {len(audits)} مرشحًا عضويا؛ "
        f"منها {len(ready_candidates)} لها مسار وحدث معًا، و{eventless} بلا حدث مجمد، "
        f"و{sound_open} بقي صوتها مفتوحًا. عُرض حدث كل مرشح مع شرح المؤلف، ولم يمنح "
        "الفحص الآلي حكم معنى أو يختزل المروحة في المادة الأولى.",
        f"- المقابلُ من اللسان: `{focus_root}`؛ عرضه لا يمنحه احتكارًا، "
        "وسجل البيان يحفظ سائر المرشحين ونتيجة كل رجل.",
        f"- الحدثُ من السجل المجمد ({focus.get('event_tier')}): «{focus_event}» "
        f"[{focus_source}]. الدرجة تسمي الملف الذي نُقل عنه الحدث حرفيا ولا تغير "
        "رتبة السلم، فالرتبة تحددها الأرجل الثلاث وحدها."
        if focus_event else
        "- الحدثُ من السجل المجمد: لا حرف من هذا المرشح في محاكم الحروف التسع "
        "والعشرين، وهي حال نادرة تسمى ولا تعالج آليا.",
        f"- مسارُ الصوت: {sound_text}. قبل إعلان أي صف ناقص فُتش كل موضع بالحرفين "
        "معًا وبألفاظ «المصرية» و«المصريّة» و`Egyptian` في عمود الشاهد.",
        f"- المعنى من قاموس الفرع: «{row['foreign_sense']}» بلا رتوش، وهو معنى "
        "الصف في المصدر الذي حدده نطاق الجولة "
        f"[{BOOK_LABELS[book]}، ص {row['page']}].",
        f"- المدار: {orbit}" + ("" if orbit.endswith(".") else "."),
        "- المصفاة: لا يسمّي صف الحصاد مانحًا خارجيًا ولا اتجاه قرض؛ غياب الاسم لا "
        "يثبت الوراثة، فيبقى الاتجاه مفتوحًا للجولة المقيسة.",
        "- فصلُ المتجانسات والاقتراض: الحكم، إن صدر، لهذا الصف ومعناه وحده؛ لا يرثه "
        "متحد الرسم ولا عنصر آخر من اسم مركب، ولا يرث العلم حكم مفردة عامة.",
        "- مؤشر اليتم: غير حاسم؛ لا يحمل صف الحصاد جرد أسرة الفرع، فلا يستعمل "
        "التفرد رفعًا أو إسقاطًا.",
        "- جسورُ الاسترداد المفحوصة: الجذر والنواة في عرض واحد؛ المروحة المصححة؛ "
        "مرشح المؤلف في موقعه؛ سجل الحدث؛ الشبكة بالحرفين وبأسماء اللسان؛ المعنى "
        "المنقول؛ العَلَم؛ القرض؛ المتجانسات.",
        f"- عائق: النوع={closure}؛ يتطلب={required}",
        f"- حالةُ الإغلاق: {closure}",
        f"- الحكم (استكشاف): {verdict}",
        f"- ملاحظات: عدسة الاسترداد حفظت جميع مرشحي المروحة ومرشح المؤلف؛ وعدسة "
        f"التشكيك {'أبقت وسم العَلَم خارج بسط التحقق مع إصدار حكم العنصر نفسه بالأرجل الثلاث' if positive and is_proper else 'أصدرت الحكم بعد اكتمال الأرجل الثلاث' if positive else 'منعت الحكم ولم تحول النقص إلى NO-TRACE'}.",
    ]
    summary = {
        "row_id": rid,
        "ordinal": ordinal + 1,
        "batch": batch,
        "book": book,
        "author": AUTHOR_LABELS[book],
        "page": row["page"],
        "tongue": row["tongue"],
        "foreign": row["foreign"],
        "foreign_sense": row["foreign_sense"],
        "author_root": K.ar_bare(row.get("arabic_root", "")),
        "comparison_root": author_root,
        "author_root_position": author_position,
        "arabic_gloss": row["arabic_gloss"],
        "proper_name": is_proper,
        "script": script,
        "raw_skeleton": raw_skeleton,
        "buggy_raw_skeleton": buggy_raw_skeleton,
        "case_head_restored": case_head_restored,
        "stem": stem,
        "stem_skeleton": stem_skeleton,
        "fan_count": len(fan_values),
        "candidates": audits,
        "closure": closure,
        "verdict": positive["degree"] if positive else None,
        "positive_root": positive["candidate"] if positive else None,
        "human_orbit": positive["human_orbit"] if positive else None,
    }
    return nfc("\n".join(lines)), summary


def marker(batch: int, side: str) -> str:
    return f"<!-- EGYPTIAN-GODS-MAQAR-BATCH-{batch:03d}:{side} -->"


def replace_batch(text: str, batch: int, block: str) -> str:
    start, end = marker(batch, "START"), marker(batch, "END")
    if start in text and end in text:
        before, rest = text.split(start, 1)
        _, after = rest.split(end, 1)
        return before.rstrip() + "\n\n" + block.rstrip() + "\n\n" + after.lstrip()
    return text.rstrip() + "\n\n" + block.rstrip() + "\n"


def report_path(batch: int) -> pathlib.Path:
    return ROOT / "data" / f"egyptian-gods-maqar-batch-{batch:03d}.json"


def write_audit(total_batches: int) -> None:
    reports = []
    for batch in range(1, total_batches + 1):
        path = report_path(batch)
        if path.exists():
            reports.append(json.loads(path.read_text(encoding="utf-8")))
    cards = [row for report in reports for row in report["rows"]]
    survival_rows = [
        row for report in reports for row in report.get("survival_rows", [])
    ]
    positives = [row for row in cards if row["verdict"]]
    counted_positives = [row for row in positives if not row["proper_name"]]
    proper_positives = [row for row in positives if row["proper_name"]]
    opens = [row for row in cards if not row["verdict"]]
    by_book = Counter(
        row["book"] for report in reports
        for row in report["rows"] + report.get("survival_rows", [])
    )
    by_author = Counter(row["author"] for row in cards)
    proper = sum(bool(row["proper_name"]) for row in cards)
    source_examined = sum(
        int(report.get("source_rows_examined", report["cards_written"]))
        for report in reports
    )
    complete = source_examined == EXPECTED and len(reports) == total_batches
    first_two = [report for report in reports if report["batch"] <= 2]
    first_two_cards = [row for report in first_two for row in report["rows"]]
    first_two_positive = [row for row in first_two_cards if row["verdict"]]
    first_two_counted = [row for row in first_two_positive if not row["proper_name"]]
    restored = sum(bool(row.get("case_head_restored")) for row in cards)

    names: list[tuple[str, str, str, str, str]] = []
    for name in ("Mina", "Mena", "Ptah", "Ra-neb", "Hermes"):
        rows_for_name = [row for row in cards if row["foreign"] == name]
        if not rows_for_name:
            continue
        old = K.skeleton_from_table(name, K.faulty_egyptian_table())
        new = K.FAN.skeleton(name, "egyptian")
        fan = K.FAN.fan(name, "egyptian", limit=400)
        favored = [
            candidate for candidate in ("مين", "من", "منن", "مون", "مان", "فتح", "بته", "رنب", "هرمس", "حرمس")
            if candidate in fan
        ]
        preview = favored or fan[:6]
        issued = [
            f"{row['positive_root']} {row['verdict']}" for row in rows_for_name
            if row["verdict"]
        ]
        if issued:
            result = "؛ ".join(dict.fromkeys(issued))
        elif all(row["script"] != "egyptian" for row in rows_for_name):
            result = "لا حكم: وسم الصف يوناني، وعرض المروحة هنا تشخيص للإصلاح فقط"
        else:
            result = "لا حكم: لم تكتمل الأرجل الثلاث"
        names.append((name, " ".join(old) or "∅", " ".join(new) or "∅", "، ".join(preview), result))

    lines = [
        "# محضر إعادة جولة المصرية بعد استرداد صدور الأعلام",
        "",
        "**التاريخ:** 2026-08-12.  ",
        "**الطبقة:** استكشاف دائمًا.  ",
        "**الحالة:** " + ("اكتمل الجرد." if complete else "جرد تراكمي قيد التنفيذ."),
        "",
        "## النطاق والنتيجة",
        "",
        f"أعيد فحص {source_examined} صفًا من الجرد الثابت. كُتبت {len(cards)} "
        f"بطاقة منضبطة، ونُقل {len(survival_rows)} صفًا من عامية مقّار إلى طبقة "
        "البقايا وحدها. لم يرث مرشح المؤلف حكم المشروع، وفُحصت المروحة كلها.",
        "",
        f"صدر {len(positives)} حكمًا موجبًا بالأرجل الثلاث، منها "
        f"{len(proper_positives)} في أعلام لا تدخل بسط العد. لذلك صار موجب العد "
        f"{len(counted_positives)}، وبقي {len(opens)} `OPEN-CANDIDATE`.",
        "",
        f"في الدفعتين 001 و002 وحدهما صار الناتج الخام {len(first_two_positive)} "
        f"موجبًا بعد أن كان 2 من 600 في الجولة المعيبة. وبعد إسقاط الأعلام من "
        f"البسط المقيس يبقى {len(first_two_counted)} موجبًا معدودًا.",
        "",
        "| المصدر | صفوف الجرد المفحوصة |",
        "|---|---:|",
    ]
    for book in BOOK_ORDER:
        lines.append(f"| {BOOK_LABELS[book]} | {by_book[book]} |")
    lines.extend([
        "",
        "| المؤلف | البطاقات المنضبطة |",
        "|---|---:|",
    ])
    for author, count in sorted(by_author.items()):
        lines.append(f"| {author} | {count} |")
    lines.extend([
        "",
        "## فصل مادة مقّار",
        "",
        "صفوف مقّار الموسومة بالمصرية القديمة تقابل المصرية بالعامية المصرية "
        "الحية، لا بجذر عربي كلاسيكي بالضرورة. لذلك حُفظت الصفوف الخمسمئة "
        "والثلاثة في بيان البقايا المستقل. ثبت جذر كلاسيكي مستقل لـ186 صفًا، "
        "فولد لها هذا المسار بطاقات جديدة بالجذر، وبقي 317 صفًا في البقايا وحدها "
        "ولم يدخل عدد البطاقات أو الأحكام.",
        "",
        "## الأعلام بعد إصلاح التصغير",
        "",
        f"استرد الإصلاح صامت الصدر في {restored} بطاقة تبدأ رومنتها بحرف كبير. "
        f"وُسم {proper} صفًا عَلَمًا أو عنصر عَلَم. بلغ {len(proper_positives)} "
        "منها الأرجل الثلاث لو كانت الأعلام تعد، لكنها بقيت خارج بسط صلات المشروع.",
        "",
        "| الاسم | الصوامت في اللقطة المعيبة | الصوامت بعد الإصلاح | أبرز خرج المروحة | الحكم لو عُد العلم |",
        "|---|---|---|---|---|",
    ])
    for name, old, new, fan, result in names:
        lines.append(f"| `{name}` | `{old}` | `{new}` | `{fan}` | {result} |")
    lines.extend([
        "",
        "ظهر `Amon` في البحث الشامل للمستودع تحت مادة أخرى من خشيم، لكنه ليس "
        "في الألسن الأربعة التي حددها نطاق هذا الجرد، فلم يُدخل خلسة في 2725 صفًا.",
        "",
        "## الأرجل وقاموس الإغلاق",
        "",
        "لم يصدر حكم إلا بمسار صوتي مسمى، والحدث من السجل المجمد كما هو، "
        "ومعنى الفرع بلا رتوش مع مدار مكتوب. هذه هي الشروط الثلاثة بلا شرط رابع. "
        "حُفظ كل مرشح للمروحة وموضع مرشح المؤلف، واستُعملت أوسام "
        "`ROOT-TRACE` و`NUCLEUS-TRACE` و`OPEN-CANDIDATE` من قاموس الإغلاق "
        "المغلق، بلا وسم جديد.",
        "",
        "لكل صف صوتي مفتوح سجّل البيان بحث الشبكة بالحرفين مع ألفاظ "
        "«المصرية» و«المصريّة» و`Egyptian` في عمود الشاهد قبل إبقائه مفتوحًا. "
        "لم يتحول غياب صف إلى شرط حكم رابع.",
        "",
        "## حصيلة الدفعات",
        "",
        "| الدفعة | المجال | فُحص | بطاقات | بقايا فقط | موجب خام | موجب معدود | مفتوح |",
        "|---:|---|---:|---:|---:|---:|---:|---:|",
    ])
    for report in reports:
        report_counted = sum(
            bool(row["verdict"]) and not row["proper_name"] for row in report["rows"]
        )
        lines.append(
            f"| {report['batch']:03d} | {report['first_ordinal']:04d} إلى "
            f"{report['last_ordinal']:04d} | "
            f"{report.get('source_rows_examined', report['cards_written'])} | "
            f"{report['cards_written']} | {report.get('survival_only', 0)} | "
            f"{report['positive']} | {report_counted} | {report['open_candidate']} |"
        )
    if complete:
        lines.extend([
            "",
            "## خاتمة الجرد",
            "",
            "اكتمل فحص 2725/2725 بلا إسقاط: 2408 بطاقات منضبطة و317 صف بقايا "
            "مقّارية فقط. بقيت الطبقة استكشافًا، وكل ما لم تكتمل له الأرجل "
            "`OPEN-CANDIDATE` بحجته.",
        ])
    lines.extend([
        "",
        "---",
        "",
        "*English abstract.* This rerun examines all 2,725 source rows after repairing "
        "case folding in the Egyptian fan. It writes disciplined cards only for 2,408 "
        "rows, while 317 Maqar colloquial survivals without an independently attested "
        "classical Arabic root remain solely in the reverse-direction survival layer. "
        "Every fan candidate is retained. Positive verdicts require exactly the named "
        "sound path, unchanged frozen event, and source meaning with a written orbit. "
        "Proper-name positives are reported but excluded from the measured numerator.",
        "",
    ])
    AUDIT.write_text(nfc("\n".join(lines)), encoding="utf-8", newline="\n")


def build_batch(batch: int) -> tuple[int, int, int]:
    rows = selected_rows()
    write_maqar_separation(rows)
    total_batches = (len(rows) + BATCH_SIZE - 1) // BATCH_SIZE
    if not 1 <= batch <= total_batches:
        raise SystemExit(f"رقم الدفعة {batch} خارج 1 إلى {total_batches}")
    start_index = (batch - 1) * BATCH_SIZE
    selected = rows[start_index:start_index + BATCH_SIZE]
    rendered: list[str] = []
    summaries: list[dict[str, Any]] = []
    survival_summaries: list[dict[str, Any]] = []
    for offset, row in enumerate(selected):
        ordinal = start_index + offset
        if row.get("lane") == "survival-only":
            survival_summaries.append({
                "row_id": f"extended-egyptian:{ordinal + 1:04d}",
                "ordinal": ordinal + 1,
                "batch": batch,
                "book": row["book"],
                "author": AUTHOR_LABELS[row["book"]],
                "page": row["page"],
                "tongue": row["tongue"],
                "foreign": row["foreign"],
                "foreign_sense": row["foreign_sense"],
                "maqar_colloquial": row["maqar_colloquial"],
                "classical_root": None,
                "lane": "survival-only",
                "excluded_from_project_link_count": True,
                "classification_basis": row["classification_basis"],
            })
            continue
        card, summary = render_card(row, start_index + offset, batch)
        summary["lane"] = row.get("lane")
        summary["maqar_colloquial"] = row.get("maqar_colloquial")
        summary["classical_root"] = row.get("classical_root")
        rendered.append(card)
        summaries.append(summary)
    positives = sum(bool(row["verdict"]) for row in summaries)
    opens = len(summaries) - positives
    by_book = Counter(row["book"] for row in selected)
    block = [
        marker(batch, "START"),
        f"## الجولةُ المصريّةُ الكبرى، الدفعةُ {batch:03d}",
        "",
        f"**بيانُ النطاق.** الصفوف {start_index + 1:04d} إلى "
        f"{start_index + len(selected):04d} من الجرد الثابت ذي 2725 صفًّا، بترتيب "
        "خشيم في «آلهة مصر العربية»، ثم مقّار، ثم جميع صفوف «العرب والهيروغليفية».",
        "",
        "**قانونُ الحكم.** ثلاثة أرجل لا رابعة لها: مسار صوتي مسمى؛ والحدث من "
        "السجل المجمد كما هو؛ والمعنى من مصدر الفرع بلا رتوش مع مدار مكتوب. كل ما "
        "لم يستوف ذلك `OPEN-CANDIDATE` بحجته.",
        "",
        "**قانونُ المروحة.** فُحصت كل مرشحات المروحة، وسُجلت نتائجها العضوية في "
        f"`data/egyptian-gods-maqar-batch-{batch:03d}.json`. مرشح المؤلف مذكور "
        "بموقعه ولا يحتكر البحث.",
        "",
        "**الأعلام.** يكتب العَلَم وعنصر الاسم ولا يُمنع، لكنه يوسم بأنه ليس مفردة "
        "معجمية عامة، ويبقى خارج بسط التحقق المقيس.",
        "",
        "**فصل مقّار.** الصورة العامية التي لم يثبت لها جذر كلاسيكي نُقلت إلى "
        "طبقة البقايا ولم تُنشأ لها بطاقة في هذا العد.",
        "",
        f"**الحصيلة.** فُحص {len(selected)} صفًا؛ كُتبت {len(summaries)} بطاقة، "
        f"ونُقل {len(survival_summaries)} صفًا إلى البقايا وحدها؛ صدر {positives} "
        f"حكمًا موجبًا، وبقي {opens} `OPEN-CANDIDATE` بين البطاقات.",
        "",
        *rendered,
        marker(batch, "END"),
    ]
    current = READING.read_text(encoding="utf-8")
    READING.write_text(
        nfc(replace_batch(current, batch, "\n".join(block))),
        encoding="utf-8",
        newline="\n",
    )
    report = {
        "generated_by": "scripts/build_egyptian_gods_maqar_cards.py",
        "source": "data/prior-art-extended-pairs.json",
        "layer": "استكشاف",
        "batch": batch,
        "batch_size": BATCH_SIZE,
        "total_batches": total_batches,
        "selected_total": len(rows),
        "first_ordinal": start_index + 1,
        "last_ordinal": start_index + len(selected),
        "source_rows_examined": len(selected),
        "cards_written": len(summaries),
        "survival_only": len(survival_summaries),
        "positive": positives,
        "open_candidate": opens,
        "books": dict(sorted(by_book.items())),
        "rows": summaries,
        "survival_rows": survival_summaries,
    }
    report_path(batch).write_text(
        nfc(json.dumps(report, ensure_ascii=False, indent=1)),
        encoding="utf-8",
        newline="\n",
    )
    write_audit(total_batches)
    return len(selected), positives, opens


def check() -> int:
    rows = selected_rows()
    total_batches = (len(rows) + BATCH_SIZE - 1) // BATCH_SIZE
    legal = set(json.loads((ROOT / "data" / "closure-vocabulary.json").read_text(encoding="utf-8"))["legal"])
    bad = []
    all_ids: list[str] = []
    all_ordinals: list[int] = []
    card_count = 0
    survival_count = 0
    for batch in range(1, total_batches + 1):
        path = report_path(batch)
        if not path.exists():
            bad.append(f"بيان الدفعة {batch:03d} غائب")
            continue
        report = json.loads(path.read_text(encoding="utf-8"))
        if report["cards_written"] != len(report["rows"]):
            bad.append(f"اختل عدد صفوف البيان {batch}")
        if report.get("survival_only") != len(report.get("survival_rows", [])):
            bad.append(f"اختل عدد بقايا البيان {batch}")
        if report.get("source_rows_examined") != report["cards_written"] + report.get("survival_only", 0):
            bad.append(f"اختل مقام صفوف البيان {batch}")
        card_count += report["cards_written"]
        survival_count += report.get("survival_only", 0)
        for row in report["rows"]:
            all_ids.append(row["row_id"])
            all_ordinals.append(int(row["ordinal"]))
            if row["closure"] not in legal:
                bad.append(f"وسم إغلاق غير مشروع {row['row_id']}")
            if row["verdict"] and not row["human_orbit"]:
                bad.append(f"حكم موجب بلا مدار {row['row_id']}")
            if row["verdict"]:
                chosen = [c for c in row["candidates"] if c["positive"]]
                if len(chosen) != 1 or not chosen[0]["sound_ready"] or not chosen[0]["event"]:
                    bad.append(f"حكم موجب بلا الأرجل الثلاث {row['row_id']}")
            if row.get("lane") == "classical-card-and-survival" and not row.get("classical_root"):
                bad.append(f"بطاقة مقّار بلا جذر كلاسيكي {row['row_id']}")
        for row in report.get("survival_rows", []):
            all_ids.append(row["row_id"])
            all_ordinals.append(int(row["ordinal"]))
            if row.get("lane") != "survival-only" or not row.get("excluded_from_project_link_count"):
                bad.append(f"صف بقايا دخل المسار المنضبط {row['row_id']}")
    if len(all_ids) != len(set(all_ids)):
        bad.append("تكرر معرّف صف بين البيانات")
    if sorted(all_ordinals) != list(range(1, EXPECTED + 1)):
        bad.append("جرد الصفوف لا يغطي 1 إلى 2725 مرة واحدة")
    if card_count != 2408 or survival_count != 317:
        bad.append(f"اختل الفصل: بطاقات {card_count} وبقايا {survival_count}")
    if bad:
        print("FAIL: " + "؛ ".join(bad[:12]))
        return 1
    print(
        f"CLEAN: الجرد الثابت {len(rows)}؛ البطاقات {card_count}؛ البقايا {survival_count}؛ "
        "أوسام الإغلاق من القاموس المغلق؛ لا موجب بلا الأرجل الثلاث"
    )
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--batch", type=int)
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    if args.check:
        return check()
    if args.all:
        total_batches = (len(selected_rows()) + BATCH_SIZE - 1) // BATCH_SIZE
        total_positive = 0
        total_open = 0
        for batch in range(1, total_batches + 1):
            examined, positives, opens = build_batch(batch)
            total_positive += positives
            total_open += opens
            print(f"الدفعة {batch:03d}: فُحص {examined}؛ موجب {positives}؛ مفتوح {opens}")
        print(f"المجموع الخام: موجب {total_positive}؛ مفتوح {total_open}")
        return 0
    if not args.batch:
        raise SystemExit("سمّ رقم الدفعة: --batch N أو --all")
    written, positives, opens = build_batch(args.batch)
    print(
        f"الدفعة {args.batch:03d}: فُحص {written}؛ موجب {positives}؛ "
        f"OPEN-CANDIDATE {opens}"
    )
    print(f"كُتب: {report_path(args.batch).relative_to(ROOT).as_posix()}")
    print(f"كُتب: {AUDIT.relative_to(ROOT).as_posix()}")
    print(f"كُتب: {READING.relative_to(ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
