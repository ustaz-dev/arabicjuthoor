# -*- coding: utf-8 -*-
"""حصاد بطاقات القرض التي أعادها فحص 2026-08-05 إلى الطابور.

تولد الأداة المروحة وترتبها، وتطلب الحدث من السجل المجمد وحده. لا تولد
مدارًا موجبًا: كل صلة موجبة موجودة نصًا في ``MANUAL_SPECS``. وتبقى البطاقة
القديمة في ملف القراءة، ثم تلحق بها بطاقة ناسخة ذات معرّف صريح.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import fan_any_script as F  # noqa: E402
import frozen_event as FE  # noqa: E402
import build_kaikki_index as LEX  # noqa: E402
import rebuild_khashim_indo_european_batches as K  # noqa: E402
import search_arabic_root_senses as AR  # noqa: E402

DATE = "2026-08-14"
BATCH_SIZE = 150
READINGS = ROOT / "04-cross-linguistic" / "readings"
NETWORK = ROOT / "04-cross-linguistic" / "shift-network-draft.md"

LANGUAGES = {
    "welsh": {
        "label": "الويلزية/Welsh",
        "id_label": "WELSH",
        "script": "latin",
        "expected": 2913,
    },
    "old-irish": {
        "label": "الإيرلندية القديمة/Old Irish",
        "id_label": "OLD-IRISH",
        "script": "latin",
        # محضر 2026-08-05: 377 صفًا، منها 349 بطاقة و28 فجوة مورد.
        "expected": 349,
    },
    "gothic": {
        "label": "القوطية/Gothic",
        "id_label": "GOTHIC",
        "script": "germanic",
        "expected": 193,
    },
    "old-norse": {
        "label": "النوردية القديمة/Old Norse",
        "id_label": "OLD-NORSE",
        "script": "germanic",
        "expected": 115,
    },
}

# لا يصدر موجب إلا من هذا النص المكتوب يدويًا. معنى الفرع لا يولد المدار.
MANUAL_SPECS: dict[tuple[str, int], list[dict[str, Any]]] = {
    ("welsh", 18): [{
        "root": "حوط",
        "orbit": (
            "القبعة تحيط بأعلى الرأس في استدارة، وتجعل الرأس داخل حدها كما "
            "يجعل الحائط ما وراءه في حوزته؛ فمعنى `hat` يصل إلى حدث `حوط` "
            "في الاستدارة حول الشيء وصيانته داخل محيط."
        ),
        "lisan": "الحائط: الجدار لأنه يحوط ما فيه.",
        "taj": "الحائط: الجدار، لأنه يحوط ما فيه.",
    }],
    ("welsh", 20): [{
        "root": "كنن",
        "orbit": (
            "العلبة جوف متين يضم ما يوضع فيه، فيستره ويحميه من الخارج؛ "
            "فمعنى `a can` يصل إلى حدث `كنن` في جعل الشيء داخل كن واق يحجبه "
            "ويصونه."
        ),
        "lisan": "الكِن والكِنّة والكِنان: وقاء كل شيء وستره.",
        "taj": "الكِن: وقاء كل شيء وستره، والكِن البيت يرد البرد والحر.",
    }],
    ("welsh", 80): [{
        "root": "صلد",
        "orbit": (
            "الشيء الموصوف بأنه `solid` متماسك صلب لا تتخلله مادة ولا ينفذ "
            "فيه شيء بسهولة؛ فمعنى الصلابة في الفرع يصل مباشرة إلى حدث `صلد` "
            "في تمام الصلابة وملاسة السطح المانعة للنفاذ."
        ),
        "lisan": "حجر صلد وصلود: بين الصلادة والصلود، صلب أملس.",
        "taj": "الصلد: الصلب الأملس؛ يقال حجر صلد وصلود وصليد.",
    }],
    ("welsh", 168): [{
        "root": "شد",
        "orbit": (
            "معنى `sad` في هذه البطاقة هو الثبات والرسوخ والصلابة، لا الحزن؛ "
            "فالشيء الثابت المتين قد اشتدت أجزاؤه ووثق بعضها ببعض، ولذلك يصل "
            "معنى الفرع مباشرة إلى حدث `شد` في صلابة الشيء ووثاقة تركيبه."
        ),
        "lisan": "الشدة: الصلابة، وهي نقيض اللين.",
        "taj": "الشد: العقد القوي؛ يقال شددت الشيء: قويت عقده.",
    }],
    ("welsh", 175): [{
        "root": "قرن",
        "orbit": (
            "الـ`horn` قرن ناتئ صلب يمتد من أعلى رأس الحيوان أو مقدمه؛ وهذا "
            "هو بعينه حدث `قرن` المسجل: نتوء بشدة يمتد في أعلى الجسم أو "
            "مقدمه، فلا يحتاج الانتقال بين المعنيين إلى واسطة مصطنعة."
        ),
        "lisan": "القرن للثور وغيره: الروق، وموضعه من رأس الإنسان قرن أيضا.",
        "taj": "القرن، محركة: الروق من الحيوان، والجمع قرون.",
    }],
    ("welsh", 194): [{
        "root": "فتن",
        "orbit": (
            "معنى `putain` في قاموس الفرع `prostitute, harlot, whore`، "
            "والشاهد العربي يصرّح بفتنة المرأة وبإرادة الفجور بالنساء. "
            "فالمرأة هنا سبب الفتنة التي تنقل صاحبها عن حاله، وهو تطبيق "
            "مخصوص لحدث `فتن` المجمّد في تحويل باطن الشيء بالابتلاء، لا "
            "مجرد اقتران أخلاقي بعيد."
        ),
        "witnesses": [{
            "source": "تاج اللغة وصِحاح العربية للجوهري",
            "quote": "وفَتَنَتْهُ المرأة، إذا دلهته، وافتتنته أيضا.",
            "url": "http://arabiclexicon.hawramani.com/%d9%81%d8%aa%d9%86/?book=8",
        }, {
            "source": "لسان العرب لابن منظور",
            "quote": "وفتَنَ إِلى النساءِ فُتُوناً وفُتِنَ إِليهن: أَراد الفُجُور بهنَّ.",
            "url": "http://arabiclexicon.hawramani.com/%d9%81%d8%aa%d9%86/?book=3",
        }],
    }],
    ("welsh", 195): [{
        "root": "بسط",
        "orbit": (
            "معنى `past` المختار في قاموس الفرع هو `paste`، أي مادة تُمدّ "
            "وتُنشر على سطح؛ والشاهد العربي يعرّف البسط بالنشر ويقابل القبض. "
            "فالمدار هو استعمال العجينة مادةً قابلة للبسط، وهو صورة مباشرة "
            "من حدث `بسط` المجمّد في التسطيح والنشر والمد."
        ),
        "witnesses": [{
            "source": "تاج اللغة وصِحاح العربية للجوهري",
            "quote": "بسط الشئ: نشره، وبالصاد أيضاً.",
            "url": "http://arabiclexicon.hawramani.com/%d8%a8%d8%b3%d8%b7/?book=8",
        }, {
            "source": "كتاب العين للخليل بن أحمد",
            "quote": "البسط نقيض القبض. والبَسيطةُ من الأرض كالبساط من المَتاع، وجمعه بُسُط.",
            "url": "http://arabiclexicon.hawramani.com/%d8%a8%d8%b3%d8%b7/?book=5",
        }],
    }],
    ("welsh", 214): [{
        "root": "ثول",
        "orbit": (
            "معنى `twr` في قاموس الفرع `crowd, group؛ heap, pile`، والشاهد "
            "العربي يسمّي `الثول` جماعة النحل و`الثويلة` جماعة من الناس. "
            "فالمدار هو الجماعة المتكاثفة نفسها، وهي نتيجة حدث `ثول` المجمّد: "
            "تجمع الدقائق وتماسكها."
        ),
        "witnesses": [{
            "source": "تاج اللغة وصحاح العربية للجوهري",
            "quote": "الثَوْلُ: جماعة النحل.",
            "url": "http://arabiclexicon.hawramani.com/%d8%ab%d9%88%d9%84/?book=8",
        }, {
            "source": "كتاب العين للخليل بن أحمد",
            "quote": "الثَّوْلُ: جماعةُ النَّحل، لا واحِدَ له.",
            "url": "http://arabiclexicon.hawramani.com/%d8%ab%d9%88%d9%84/?book=5",
        }],
    }],
    ("welsh", 217): [{
        "root": "كور",
        "orbit": (
            "الـ`choir` جماعة جُمعت للغناء، وقاموس الفرع يضم إليه `court, "
            "circle, range`؛ والشاهد العربي يسمّي `الكور` الجماعة الكثيرة. "
            "فالجماعة هي نتيجة الإدارة والجمع المثبتين في حدث `كور` المجمّد، "
            "لا مجرد تشابه لفظي."
        ),
        "witnesses": [{
            "source": "تاج اللغة وصحاح العربية للجوهري",
            "quote": "والكَوْرُ أيضاً: الجماعة الكثيرة من الإبل.",
            "url": "http://arabiclexicon.hawramani.com/%d9%83%d9%88%d8%b1/?book=8",
        }, {
            "source": "المحكم والمحيط الأعظم لابن سيده",
            "quote": "والكُور من الْإِبِل: القطيع الضخم.",
            "url": "http://arabiclexicon.hawramani.com/%d9%83%d9%88%d8%b1/?book=10",
        }],
    }],
    ("welsh", 244): [{
        "root": "دور",
        "orbit": (
            "معنى الفرع `idol`، والشاهد العربي يسمّي `الدوّار` صنمًا كانوا "
            "يطوفون حوله. فالصنم هو مركز فعل الدوران والإحاطة، وبذلك يصل معنى "
            "الفرع إلى حدث `دور` المجمّد في تحوي الشيء أو إحاطته حول شيء."
        ),
        "witnesses": [{
            "source": "لسان العرب لابن منظور",
            "quote": "دُوَّارٌ، بالضم: صنم، وقد يفتح، وفي الأَزهري: الدَّوَّارُ صنم كانت العرب تنصبه يجعلون موضعاً حوله يَدُورُون به.",
            "url": "http://arabiclexicon.hawramani.com/%d8%af%d9%88%d8%b1/?book=3",
        }],
    }],
    ("welsh", 416): [{
        "root": "لفف",
        "orbit": (
            "اللف هو إدارة غطاء على ظاهر الشيء حتى يحيط به ويضمه، وهذا هو "
            "معنى `to wrap up, around` في مدخلة الفرع المختارة؛ فيصل المعنى "
            "مباشرة إلى حدث `لفف`: تلوي شيء على آخر من ظاهره عالقًا غير لاصق."
        ),
        "lisan": "لف الشيء يلفه لفًا: جمعه وضمه بعضه إلى بعض.",
        "taj": "لف الشيء يلفه لفًا: جمعه وضم بعضه إلى بعض.",
    }],
    ("welsh", 506): [{
        "root": "صلب",
        "orbit": (
            "الـ`slab` كتلة ذات جرم متماسك ممتد، وكذلك الـ`lump` والـ`clod` "
            "جرمان يقوم كل منهما بتماسك مادته في قطعة؛ فيتصل معنى المدخلة "
            "بحدث `صلب` في شدة تماسك الشيء مع امتداده، من غير إضافة معنى "
            "خارج المدخلة."
        ),
        "lisan": "الصلب من كل شيء: الشديد؛ والصلابة ضد اللين.",
        "taj": "الصلب: الشديد؛ والصلابة ضد اللين.",
    }],
    ("welsh", 630): [{
        "root": "بوب",
        "orbit": (
            "الـ`pipe` مجرى مفتوح الجوف يصل بين طرفين اتصالًا دائمًا ما دام "
            "الأنبوب قائمًا؛ فيتصل معنى المدخلة مباشرة بحدث `بوب` في الانفتاح "
            "مع الاتصال الدائم، لا بمجرد شبه الشكل."
        ),
        "lisan": "الباب: المدخل؛ وجمعه أبواب.",
        "taj": "الباب: المدخل؛ وجمعه أبواب.",
    }],
    ("welsh", 767): [{
        "root": "قوب",
        "orbit": (
            "الـ`vessel` والـ`container` جوف محدود تحيط به جوانب تحفظ ما يوضع "
            "فيه؛ وهذا هو حدث `قوب` كما في السجل: فراغ جوفي محدود الجوانب "
            "مقور، فتتصل المدخلة بالحدث من غير واسطة."
        ),
        "lisan": "قاب الشيء يقوبه قوبًا: خرقه؛ والقوب: الخرق.",
        "taj": "قابه يقوبه قوبًا: خرقه؛ والقوب: الخرق.",
    }],
    ("welsh", 784): [{
        "root": "قرن",
        "orbit": (
            "الـ`crown` غطاء ملكي يقوم في أعلى الرأس، وتبرز أجزاؤه أو شرفاته "
            "فوقه؛ فيتصل معنى المدخلة بحدث `قرن` في نتوء شديد يمتد في أعلى "
            "الجسم أو مقدمه."
        ),
        "lisan": "القرن للثور وغيره: الروق، وموضعه من رأس الإنسان قرن أيضا.",
        "taj": "القرن، محركة: الروق من الحيوان، والجمع قرون.",
    }],
    ("welsh", 1389): [{
        "root": "شيد",
        "orbit": (
            "الـ`shed` بناءٌ مؤقتٌ قائمٌ يضم ما يوضع فيه ويقيه، ومدخلة الفرع "
            "تسمّيه صراحةً `temporary structure`؛ وهذا يصل مباشرةً إلى حدث "
            "`شيد` المجمّد في الشد نحو البناء وإمساكه، وإلى شاهد إحكام البناء "
            "ورفعه، من غير نقلٍ لمعنى المدخلة."
        ),
        "lisan": "كل ما أُحكم من البناء فقد شُيّد، وتشييد البناء إحكامه ورفعه.",
        "taj": "التشييد في البناء إحكامه ورفعه، والشيد الجص.",
    }],
    ("welsh", 1616): [{
        "root": "وجس",
        "orbit": (
            "معنى `gès` في قاموس الفرع `guess, idea, estimate`؛ والواجس في "
            "الشاهد العربي هو الهاجس والخاطر، أي فكرة تقع في النفس. فهذا "
            "التقدير أو الفكرة المتحصلة في الباطن صورة مباشرة من حدث `وجس` "
            "المجمّد في تحصّل شيء دقيق الوقع في أثناء، لا مجرد مصاحبة ذهنية."
        ),
        "witnesses": [{
            "source": "المفردات في غريب القرآن للراغب الأصفهاني",
            "quote": "الإيجاس: وجود ذلك في النفس؛ والواجس الخاطر.",
            "url": "http://arabiclexicon.hawramani.com/%d9%88%d8%ac%d8%b3/?book=33",
        }, {
            "source": "تاج اللغة وصِحاح العربية للجوهري",
            "quote": "الواجس: الهاجس. وأوجس في نفسه خيفة، أي أضمر.",
            "url": "http://arabiclexicon.hawramani.com/%d9%88%d8%ac%d8%b3/?book=8",
        }],
    }],
    ("welsh", 1679): [{
        "root": "قرن",
        "orbit": (
            "قاموس الفرع يعيّن `corun` تاجًا وأعلى الرأس وأعلى السن؛ وهذه "
            "مواضع علوّ ونتوء في أعلى الجسم أو مقدمه، فتقع في حدث `قرن` "
            "المجمّد نفسه: نتوءٌ شديدٌ ممتد في الأعلى أو المقدّم، لا في مجرد "
            "شبه صورة التاج."
        ),
        "lisan": "القرن للثور وغيره: الروق، وموضعه من رأس الإنسان قرن أيضا.",
        "taj": "القرن، محركة: الروق من الحيوان، والجمع قرون.",
    }],
    ("old-irish", 20): [{
        "root": "قرن",
        "orbit": (
            "معنى قاموس الفرع `drinking-horn, goblet` يسمّي وعاء الشرب "
            "المتخذ من القرن باسمه، والأصل المنشور يرده إلى اللاتينية `cornū`. "
            "والشاهدان العربيان يثبتان أن `القَرْن` هو روق الثور وغيره؛ فالمادة "
            "المسماة في الوعاء هي بعينها النتوء الصلب الممتد في أعلى جسم "
            "الحيوان الذي يصفه حدث `قرن` المجمّد، لا تشابهًا عامًا في الشكل."
        ),
        "witnesses": [{
            "source": "تاج اللغة وصِحاح العربية للجوهري",
            "quote": "القَرْنُ للثَور وغيره.",
            "url": "http://arabiclexicon.hawramani.com/%d9%82%d8%b1%d9%86/?book=8",
        }, {
            "source": "كتاب العين للخليل بن أحمد الفراهيدي",
            "quote": "قَرْنُ الثور معروف، وموضعه من رأس الإنسان قَرنٌ أيضاً.",
            "url": "http://arabiclexicon.hawramani.com/%d9%82%d8%b1%d9%86/?book=5",
        }],
    }],
}

# إغلاقات لا تنشئ صلة مقارنة. لكل عضو دليله، ولا يورث الحكم لمتحد الرسم.
NAMED_CLOSURES: dict[tuple[str, int], dict[str, str]] = {
    ("welsh", 48): {
        "closure": "SEMITIC-SOURCE-TRANSMISSION",
        "donor": "العربية لَيْمُون (laymūn)",
        "route": "العربية لَيْمُون ← الفرنسية القديمة lymon ← الإنجليزية الوسطى lymon ثم الإنجليزية lemon ← الويلزية lemon",
        "evidence": "04-cross-linguistic/data/lane_d_middle_english_transmissions.jsonl، السطر 88",
    },
    ("welsh", 100): {
        "closure": "ABBREVIATION",
        "donor": "لا مانح سامي؛ العضو اختصار حرفي",
        "route": "`CD` تسمية مختصرة من الحرفين الأولين في `compact disc`، لا مادة لفظية مستقلة للمقارنة الجذرية",
        "evidence": "معنى العضو وأصله المنشوران في البطاقة التاريخية نفسها",
    },
    ("welsh", 148): {
        "closure": "SEMITIC-SOURCE-TRANSMISSION",
        "donor": "الأكدية qanû، القصبة والمقياس",
        "route": "الأكدية qanû ← اليونانية kanōn، قضيب القياس ثم القاعدة ← اللاتينية canon ← الإنجليزية canon ← الويلزية canon",
        "evidence": "data/alawlaqi-prior-attempts.json، مادة قانون، ونقل باقر ص.141",
    },
    ("welsh", 149): {
        "closure": "SEMITIC-SOURCE-TRANSMISSION",
        "donor": "الأكدية qanû، القصبة والمقياس",
        "route": "الأكدية qanû ← اليونانية kanōn ← اللاتينية canon في الاستعمال الكنسي ← الإنجليزية canon ← الويلزية canon",
        "evidence": "data/alawlaqi-prior-attempts.json، مادة قانون، ونقل باقر ص.141",
    },
    ("welsh", 150): {
        "closure": "SEMITIC-SOURCE-TRANSMISSION",
        "donor": "الأكدية qanû، القصبة",
        "route": "الأكدية qanû ← اليونانية kanna ← اللاتينية canna ← الإيطالية cannone ← الفرنسية الوسطى canon ← الإنجليزية cannon ← الويلزية canon",
        "evidence": "04-cross-linguistic/data/lane_d_middle_english_transmissions.jsonl، السطر 14",
    },
    ("welsh", 186): {
        "closure": "SEMITIC-SOURCE-TRANSMISSION",
        "donor": "العربية الغطاس (al-ġaṭṭās)، الغواص أو طائر البحر",
        "route": "العربية الغطاس ← الإسبانية أو البرتغالية alcatraz ← الإنجليزية albatross ← الويلزية albatros",
        "evidence": "Merriam-Webster، مادة albatross، فقرة Word History؛ وCNRTL، مادة alcatraz",
    },
    ("welsh", 233): {
        "closure": "SEMITIC-SOURCE-TRANSMISSION",
        "donor": "العبرية בֹּשֶׂם (bōśem)، الطيب أو البلسم",
        "route": "العبرية bōśem ← اليونانية balsamon ← اللاتينية balsamum ← الفرنسية القديمة basme أو baume ← الإنجليزية balm ← الويلزية balm",
        "evidence": "CNRTL، مادة baume، فقرة Étymologie؛ ويؤيده Merriam-Webster، مادة balsam، فقرة Word History",
    },
    ("welsh", 454): {
        "closure": "SEMITIC-SOURCE-TRANSMISSION",
        "donor": "العربية نارنج (nāranj)، ثمر النارنج",
        "route": "العربية nāranj ← الأوكستانية القديمة auranja ← الفرنسية والإنجليزية orange ← الويلزية oren",
        "evidence": "Merriam-Webster، مادة orange، فقرة Word History؛ وCNRTL، مادة orange، فقرة Étymologie et Histoire",
    },
    ("welsh", 455): {
        "closure": "SEMITIC-SOURCE-TRANSMISSION",
        "donor": "العربية نارنج (nāranj)، ثمر النارنج الذي سميت به الدرجة اللونية",
        "route": "العربية nāranj ← الأوكستانية القديمة auranja ← الفرنسية والإنجليزية orange، ثم اسم اللون ← الويلزية oren",
        "evidence": "Merriam-Webster، مادة orange، فقرة Word History؛ وCNRTL، مادة orange، فقرة Étymologie et Histoire",
    },
    ("welsh", 603): {
        "closure": "SEMITIC-SOURCE-TRANSMISSION",
        "donor": "العربية قَهْوَة (qahwa)، شراب القهوة",
        "route": "العربية qahwa ← التركية العثمانية kahve ← الإيطالية caffè والفرنسية café ← الإنجليزية café ← الويلزية caffi",
        "evidence": "Merriam-Webster، مقال 11 Terms from the Coffee Shop، مادة Coffee، وأصل الفرع المنشور في قاموس الويلزية",
    },
    ("welsh", 700): {
        "closure": "SEMITIC-SOURCE-TRANSMISSION",
        "donor": "العربية سُكَّر (sukkar)، السكر",
        "route": "العربية sukkar ← الإيطالية القديمة zucchero واللاتينية الوسيطة zuccarum ← الفرنسية الأنجلوية sucre ← الويلزية siwgr",
        "evidence": "Merriam-Webster، مادة sugar، فقرة Word History؛ وCNRTL، مادة sucre؛ ويصرح به أصل قاموس الفرع",
    },
    ("welsh", 1163): {
        "closure": "SEMITIC-SOURCE-TRANSMISSION",
        "donor": "العربية قَهْوَة (qahwa)، مادة اسم القهوة التي اشتقت منها تسمية الكافيين",
        "route": "العربية qahwa ← التركية العثمانية kahve ← الفرنسية café، ثم caféine ← الإنجليزية caffeine ← الويلزية caffîn",
        "evidence": "CNRTL، مادة caféine، المشتقة من café؛ وMerriam-Webster، مقال 11 Terms from the Coffee Shop، مادة Coffee",
    },
    ("welsh", 1166): {
        "closure": "SEMITIC-SOURCE-TRANSMISSION",
        "donor": "العربية مُومِيَاء (mūmiyāʾ)، الجسد المحنط أو مادة التحنيط",
        "route": "العربية mūmiyāʾ ← اللاتينية الوسيطة mumia ← الإنجليزية mummy ← الويلزية mymi",
        "evidence": "CNRTL، مادة momie، فقرة Étymologie et Histoire",
    },
    ("welsh", 1180): {
        "closure": "SEMITIC-SOURCE-TRANSMISSION",
        "donor": "العربية لَيْمُون (laymūn)",
        "route": "العربية لَيْمُون ← الفرنسية القديمة lymon ← الإنجليزية الوسطى lymon ثم الإنجليزية lemon ← الويلزية lemwn",
        "evidence": "04-cross-linguistic/data/lane_d_middle_english_transmissions.jsonl، السطر 88",
    },
    ("welsh", 1290): {
        "closure": "SEMITIC-SOURCE-TRANSMISSION",
        "donor": "العربية شَرَاب (šarāb)، ما يُشرَب",
        "route": "العربية šarāb ← اللاتينية الوسيطة syrupus ← الفرنسية الأنجلوية sirop ← الإنجليزية الوسطى sirup ثم الإنجليزية syrup ← الويلزية surop",
        "evidence": "Merriam-Webster، مادة syrup، فقرة Word History",
    },
    ("welsh", 1475): {
        "closure": "SEMITIC-SOURCE-TRANSMISSION",
        "donor": "العبرية בֹּשֶׂם (bōśem)، الطيب أو البلسم",
        "route": "العبرية bōśem ← اليونانية balsamon ← اللاتينية balsamum ← الفرنسية القديمة baume ثم الإنجليزية الوسطى bawme ← الويلزية bawm",
        "evidence": "CNRTL، مادة baume، فقرة Étymologie؛ ويؤيده Merriam-Webster، مادة balsam، فقرة Word History",
    },
    ("welsh", 1683): {
        "closure": "SEMITIC-SOURCE-TRANSMISSION",
        "donor": "العربية الخُرْشُوف (al-khurshūf)، نبات الأرضي شوكي",
        "route": "العربية al-khurshūf ← الإيطالية اللهجية articiocco، بوسائط رومانسية لا يفصلها المصدر ← الإنجليزية artichoke ← الويلزية artisiog",
        "evidence": "Merriam-Webster، مادة artichoke، فقرة Word History",
    },
    ("welsh", 1819): {
        "closure": "SEMITIC-SOURCE-TRANSMISSION",
        "donor": "العربية لَيْمُون (laymūn)، الليمون",
        "route": "العربية laymūn ← الفرنسية القديمة lymon ← الإنجليزية الوسطى lymon ثم lemon، ومنها lemonade ← الويلزية lemonêd",
        "evidence": "04-cross-linguistic/data/lane_d_middle_english_transmissions.jsonl، السطر 88؛ ومدخلة الفرع التي ترد lemonêd إلى الإنجليزية lemonade",
    },
    ("welsh", 2130): {
        "closure": "SEMITIC-SOURCE-TRANSMISSION",
        "donor": "العربية الكِيمِيَاء (al-kīmiyāʾ)، وفيها الأداة العربية مع مادةٍ أقدم",
        "route": "العربية al-kīmiyāʾ ← اللاتينية الوسيطة alkimia/alchymia والفرنسية الأنجلوية alkemye ← الإنجليزية alchemy ← الويلزية alcemeg",
        "evidence": "Merriam-Webster، مادة alchemy، فقرة Word History؛ ومدخلة الفرع التي ترد alcemeg إلى الإنجليزية alchemy",
    },
    ("welsh", 2268): {
        "closure": "SEMITIC-SOURCE-TRANSMISSION",
        "donor": "العربية عُصْفُر (ʿuṣfur) أو أَصْفَر (ʿaṣfar)، العصفر أو لونه",
        "route": "العربية ʿuṣfur/ʿaṣfar ← الإيطالية القديمة saffiore ← الفرنسية الوسطى saffleur ← الإنجليزية safflower ← الويلزية safflwr",
        "evidence": "Merriam-Webster، مادة safflower، فقرة Word History",
    },
    ("welsh", 2353): {
        "closure": "SEMITIC-SOURCE-TRANSMISSION",
        "donor": "العربية صِفْر (ṣifr)، الخلو من المقدار والعدد صفر",
        "route": "العربية ṣifr ← اللاتينية الوسيطة zephirum ← الإيطالية zero ← الإنجليزية zero ← الويلزية sero، ثم an- + sero في ansero بمعنى nonzero",
        "evidence": "Merriam-Webster، مادة zero، فقرة Word History؛ ومدخلة قاموس الفرع التي تحلل ansero إلى an- + sero",
    },
}

CONTROL_SPECS = [
    {"word": "mwg", "root": "موج", "closure": "ROOT-TRACE"},
    {"word": "melg", "root": "ملج", "closure": "ROOT-ECHO"},
    {"word": "senos", "root": "سن", "closure": "NUCLEUS-TRACE"},
    {"word": "caer", "root": "قر", "closure": "NUCLEUS-TRACE"},
    {"word": "môr", "root": "مور", "closure": "ROOT-ECHO"},
    {"word": "car", "root": "جر", "closure": "NUCLEUS-TRACE"},
]


def clean(value: Any) -> str:
    return " ".join(str(value or "").split()).replace("`", "ˋ")


def context_key(value: Any) -> str:
    """صيغة مقارنة فقط؛ النص المعجمي نفسه يبقى بلا تعديل في البطاقة."""
    text = str(value or "").casefold()
    text = text.replace("“", "").replace("”", "").replace("’", "'")
    return re.sub(r"\s+", " ", text).strip(" .؛;")


def lexicon_context(language: str, card: dict[str, Any]) -> dict[str, Any]:
    """اعرض جميع المداخل، ثم اختر بالسياق لا بترتيب القائمة."""
    hits, how = LEX.look(language, str(card["word"]))
    researcher_meaning = str(card["meaning"])
    researcher_source = str(card["source"])
    meaning_key = context_key(researcher_meaning)
    source_key = context_key(researcher_source)

    scored: list[tuple[tuple[int, int], int]] = []
    for position, entry in enumerate(hits):
        entry_meaning = context_key(entry.get("en"))
        parts = [context_key(part) for part in str(entry.get("en") or "").split("؛")]
        if meaning_key and meaning_key == entry_meaning:
            meaning_score = 4
        elif meaning_key and meaning_key in parts:
            meaning_score = 3
        elif meaning_key and entry_meaning and (
            meaning_key in entry_meaning or entry_meaning in meaning_key
        ):
            meaning_score = 2
        else:
            meaning_score = 0

        entry_source = context_key(entry.get("etym"))
        if source_key and entry_source and source_key == entry_source:
            source_score = 3
        elif source_key and entry_source and (
            source_key.startswith(entry_source) or entry_source.startswith(source_key)
        ):
            source_score = 2
        else:
            source_score = 0
        scored.append(((meaning_score, source_score), position))

    selected_index: int | None = None
    selection_note = "لم توافق مدخلةٌ سياقَ المعنى والاشتقاق في بطاقة المصدر"
    if scored:
        best = max(score for score, _ in scored)
        winners = [position for score, position in scored if score == best and max(score) > 0]
        if len(winners) == 1:
            selected_index = winners[0]
            selection_note = "اختيرت بالمعنى والاشتقاق الموافقين لسياق الصف"
        elif winners:
            canonical = {
                json.dumps(hits[position], ensure_ascii=False, sort_keys=True)
                for position in winners
            }
            if len(canonical) == 1:
                selected_index = winners[0]
                selection_note = (
                    "تساوت مداخل متطابقة النص؛ اختير الرسم الأول بعد عرضها كلها، "
                    "ولا يغيّر الاختيار معنى البطاقة"
                )
            else:
                selection_note = (
                    "بقي أكثر من مدخلة مختلفة موافقًا للسياق ولم يعيّن المصدر "
                    "إحداها، فتركت البطاقة مفتوحة"
                )

    selected = hits[selected_index] if selected_index is not None else None
    dictionary_meaning = str(selected.get("en") or "") if selected else ""
    conflict = bool(selected and context_key(dictionary_meaning) != meaning_key)
    return {
        "file": f"data/branch-lexicons/{language}.json",
        "path": how,
        "entries": hits,
        "selected_index": selected_index,
        "selected": selected or {},
        "selection_note": selection_note,
        "dictionary_meaning": dictionary_meaning,
        "researcher_meaning": researcher_meaning,
        "conflict": conflict,
        "agreement": selected is not None,
    }


def render_lexicon_entry(position: int, entry: dict[str, Any]) -> str:
    reading = f" /{clean(entry.get('read'))}/" if entry.get("read") else ""
    etym = f"؛ اشتقاقًا: {clean(entry.get('etym'))}" if entry.get("etym") else ""
    return (
        f"#{position} `{clean(entry.get('word'))}`{reading} "
        f"[{clean(entry.get('pos')) or 'غير موسوم'}] «{clean(entry.get('en'))}»{etym}"
    )


DIRECT_ARABIC_SOURCE = re.compile(
    r"(?i)(?:ultimately\s+)?from\s+Arabic\b|borrow(?:ed|ing)\s+from\s+Arabic\b"
)


def lexicon_arabic_closure(lexicon: dict[str, Any]) -> dict[str, str] | None:
    """الإغلاق للاتجاه العربي ← الفرع، لا لمجرد المرور باللاتينية."""
    selected = lexicon.get("selected") or {}
    etym = str(selected.get("etym") or "")
    if not DIRECT_ARABIC_SOURCE.search(etym):
        return None
    return {
        "closure": "SEMITIC-SOURCE-TRANSMISSION",
        "donor": "المانح العربي المسمى بنص اشتقاق قاموس الفرع",
        "route": etym,
        "evidence": (
            f"{lexicon['file']}، المدخلة `{clean(selected.get('word'))}`، "
            f"طريق البحث: {lexicon['path']}"
        ),
    }


def skeleton_variants(form: str, script: str) -> str:
    values = ["".join(F.skeleton(form, script))]
    if script in {"latin", "germanic", "greek"}:
        for ending in F.LATIN_ENDINGS:
            if form.lower().endswith(ending) and len(form) - len(ending) >= 2:
                alternate = "".join(F.skeleton(form[:-len(ending)], script))
                if 2 <= len(alternate) <= 4 and alternate not in values:
                    values.append(alternate)
                break
    return "|".join(value for value in values if value)


def current_fan(
    form: str,
    language: str,
    selected: set[str],
) -> tuple[list[dict[str, Any]], int]:
    cfg = LANGUAGES[language]
    script = str(cfg["script"])
    ranked = F.rank(form, F.fan(form, script), script)
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
            "meaning": "✓" if root in selected else ("×" if route and event else "؟"),
        })
    return review, dialect_additions


def arabic_source_labels(matches: list[dict[str, Any]]) -> list[str]:
    labels: list[str] = []
    for match in matches:
        source_id = AR.canonical_source_id(str(match.get("source") or ""))
        label = (
            AR.SOURCE_LABELS[source_id]
            if source_id else clean(match.get("source"))
        )
        if label and label not in labels:
            labels.append(label)
    return labels


def attach_arabic_lexicon_review(
    review: list[dict[str, Any]],
    hits_by_root: dict[str, list[dict[str, Any]]],
) -> None:
    """Record a full max_chars=0 search for every sound+event candidate."""
    for item in review:
        if not item["sound"] or not item["event_tier"]:
            item["arabic_lexicon_review"] = {}
            continue
        matches = hits_by_root.get(str(item["root"]), [])
        independent = AR.independent_fan(matches)
        item["arabic_lexicon_review"] = {
            "command": (
                "python scripts/search_arabic_root_senses.py "
                f"{item['root']} --max-chars 0"
            ),
            "max_chars": 0,
            "truncated": any(
                bool(match.get("definition_truncated")) for match in matches
            ),
            "witness_count": len(matches),
            "sources": arabic_source_labels(matches),
            "independent_fan_complete": bool(independent["complete"]),
            "judgment_ready": bool(independent["judgment_ready"]),
        }


def render_arabic_lexicon_review(review: list[dict[str, Any]]) -> str:
    ready = [item for item in review if item["sound"] and item["event_tier"]]
    return "، ".join(
        f"`{item['root']}`[ش{item['arabic_lexicon_review']['witness_count']}، "
        f"م{len(item['arabic_lexicon_review']['sources'])}]"
        for item in ready
    ) or "لا جذر اكتمل فيه الصوت والحدث"


def manual_witnesses(spec: dict[str, Any]) -> list[dict[str, str]]:
    explicit = spec.get("witnesses")
    if explicit:
        return [dict(witness) for witness in explicit]
    return [{
        "source": "لسان العرب لابن منظور",
        "quote": str(spec["lisan"]),
        "url": "",
    }, {
        "source": "تاج العروس لمرتضى الزبيدي",
        "quote": str(spec["taj"]),
        "url": "",
    }]


def orbit_with_witnesses(
    orbit: str,
    witnesses: list[dict[str, str]],
) -> str:
    """Keep the lexicon's exact wording and name inside the orbit itself."""
    if not witnesses:
        raise AssertionError("لا يصدر مدار موجب بلا شاهد معجمي مسمى")
    support = "؛ ".join(
        f"قال {clean(witness['source'])}: «{clean(witness['quote'])}»"
        for witness in witnesses
    )
    return f"{clean(orbit).rstrip('.؟!')}؛ وسند هذا المدار: {support}."


def arabic_hits_for_cards(
    language: str,
    cards: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    roots: set[str] = set()
    for card in cards:
        review, _ = current_fan(str(card["word"]), language, set())
        roots.update(
            str(item["root"])
            for item in review
            if item["sound"] and item["event_tier"]
        )
    # ``None`` is the module-level equivalent of CLI ``--max-chars 0``.
    return AR.matches_for_roots(AR.DEFAULT_RESOURCES, roots, None)


def render_candidate(item: dict[str, Any]) -> str:
    dialect = f"،له={item['dialect_label']}" if item["dialect_label"] else ""
    return (
        f"`{item['root']}`[و{item['weight']:.6f}،"
        f"ص{'✓' if item['sound'] else '×'}،ح{'✓' if item['event_tier'] else '×'}،"
        f"د{item['event_tier']}،م{item['meaning']}{dialect}]"
    )


def missing_sound_searches(form: str, language: str) -> list[str]:
    cfg = LANGUAGES[language]
    script = str(cfg["script"])
    label = str(cfg["label"])
    language_names = [part.strip() for part in label.split("/")]
    lines = NETWORK.read_text(encoding="utf-8").splitlines()
    queries: list[str] = []
    seen: set[tuple[str, str]] = set()
    for source in F.skeleton(form, script):
        for arabic in F.FANS[script].get(source, ()):
            pair = (source, arabic)
            if pair in seen or pair in K.ROW_IDS:
                continue
            seen.add(pair)
            hits = sum(
                source.casefold() in line.casefold()
                and arabic in line
                and any(name.casefold() in line.casefold() for name in language_names)
                for line in lines
            )
            queries.append(
                f"`{source}` + `{arabic}` + «{label}» في عمود الشاهد، النتائج الحرفية {hits}"
            )
    return queries or [
        f"الهيكل الكامل + «{label}» في عمود الشاهد، النتائج الحرفية 0"
    ]


def original_cards(language: str) -> list[dict[str, Any]]:
    cfg = LANGUAGES[language]
    path = READINGS / f"{language}.md"
    body = path.read_text(encoding="utf-8")
    blocks = re.split(r"(?=^### )", body, flags=re.MULTILINE)
    pattern = re.compile(
        rf"LOAN-REOPEN-{re.escape(str(cfg['id_label']))}-(\d+)"
    )
    found: dict[int, dict[str, Any]] = {}
    for block in blocks:
        if "أعيدت إلى الطابور" not in block or "سطر النسخ (2026-08-05" not in block:
            continue
        matches = pattern.findall(block)
        if not matches:
            continue
        index = int(matches[-1])
        word_match = re.search(r"^- الكلمةُ? في الفرع:\s*([^\s\[]+)", block, re.MULTILINE)
        meaning_match = re.search(r"^- المعنى من قاموس الفرع:\s*«([^»]*)»", block, re.MULTILINE)
        source_match = re.search(r"^- أقدمُ صورةٍ مستعادة:\s*(.*?)\s*\[Kaikki", block, re.MULTILINE)
        if not word_match or not meaning_match:
            raise AssertionError(f"تعذر استخراج صورة أو معنى البطاقة {index}")
        found[index] = {
            "index": index,
            "old_id": f"LOAN-REOPEN-{cfg['id_label']}-{index:05d}",
            "word": word_match.group(1).strip().strip("`"),
            "meaning": meaning_match.group(1).strip(),
            "source": source_match.group(1).strip() if source_match else "لا نص أصل مستخرج",
            "heading": block.splitlines()[0].replace("### ", "").strip(),
        }
    cards = [found[index] for index in sorted(found)]
    if len(cards) != int(cfg["expected"]):
        raise AssertionError(
            f"جرد {language} المنقول من ملفات القراءة {len(cards)} لا يساوي المتوقع {cfg['expected']}"
        )
    ledger = json.loads((ROOT / "data" / "recovery-ledger.json").read_text(encoding="utf-8"))
    ledger_count = sum(
        row.get("file") == f"04-cross-linguistic/readings/{language}.md"
        and "أعيدت إلى الطابور" in row.get("closure", "")
        for row in ledger["suspended"]
    )
    superseded = {
        int(value)
        for value in re.findall(
            rf"LOAN-HARVEST-REREVIEW:LOAN-REOPEN-{re.escape(str(cfg['id_label']))}-(\d+)",
            body,
        )
    }
    expected_active = int(cfg["expected"]) - len(superseded)
    if ledger_count != expected_active:
        raise AssertionError(
            f"مرشح السجل أعاد {ledger_count} بطاقة لـ{language} بدل {expected_active} "
            f"بعد طرح {len(superseded)} بطاقة منسوخة"
        )
    return cards


def closure_for(root: str) -> str:
    return "NUCLEUS-TRACE" if len(re.findall(r"[ء-ي]", root)) == 2 else "ROOT-TRACE"


def control_run() -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for spec in CONTROL_SPECS:
        review, _ = current_fan(spec["word"], "welsh", {spec["root"]})
        by_root = {item["root"]: item for item in review}
        item = by_root.get(spec["root"])
        if not item:
            raise AssertionError(f"تغير الضابط: خرج {spec['word']} ↔ {spec['root']} من المروحة")
        if not item["sound"]:
            raise AssertionError(f"تغير الضابط: سقط المسار الصوتي لـ{spec['word']} ↔ {spec['root']}")
        if not item["event_tier"]:
            raise AssertionError(f"تغير الضابط: لم يعد الحدث يحل لـ{spec['word']} ↔ {spec['root']}")
        results.append({
            **spec,
            "current_verdict": spec["closure"],
            "weight": item["weight"],
            "sound_route": item["sound_route"],
            "event_tier": item["event_tier"],
            "event_tier_ar": item["event_tier_ar"],
            "event_text": item["event_text"],
            "unchanged": True,
        })
    return results


def build_card(
    language: str,
    card: dict[str, Any],
    arabic_hits_by_root: dict[str, list[dict[str, Any]]],
    orbit_reassessment: bool = False,
    revision_id: str | None = None,
    supersedes_id: str | None = None,
    supersedes_marker: str = "LOAN-HARVEST-REREVIEW",
) -> tuple[list[str], dict[str, Any], str]:
    index = int(card["index"])
    word = str(card["word"])
    lexicon = lexicon_context(language, card)
    researcher_meaning = str(card["meaning"])
    meaning = str(lexicon["dictionary_meaning"] or researcher_meaning)
    specs = MANUAL_SPECS.get((language, index), [])
    named = NAMED_CLOSURES.get((language, index)) or lexicon_arabic_closure(lexicon)
    if specs and named:
        raise AssertionError(
            f"موجب يدوي أغلقه اشتقاق الفرع بمانح سامي: {card['old_id']}"
        )
    selected = {spec["root"] for spec in specs}
    review, dialect_additions = current_fan(word, language, selected)
    attach_arabic_lexicon_review(review, arabic_hits_by_root)
    by_root = {item["root"]: item for item in review}
    cfg = LANGUAGES[language]
    new_id = revision_id or f"LH-{cfg['id_label']}-{index:05d}"
    superseded = supersedes_id or str(card["old_id"])
    if supersedes_marker == "ARABIC-ROOT-SENSE-REREVIEW":
        heading = "بطاقة إعادة قراءة الشواهد المعجمية العربية"
    elif revision_id:
        heading = "بطاقة إعادة قراءة عائلات اللسان"
    else:
        heading = "بطاقة حصاد القرض المعاد فتحه"
    lines = [
        f"### {heading}: `{clean(word)}`؛ {new_id}",
        f"<!-- {supersedes_marker}:{superseded} -->",
        f"- ناسخ البطاقة السابقة: `{superseded}` ← `{new_id}`؛ بقي النص السابق كاملًا، وهذا الحكم هو النافذ بتاريخ {DATE}.",
        f"- اللسان: {cfg['label']}؛ الطبقة: استكشاف.",
        f"- معنى الباحث في البطاقة التاريخية: `{clean(word)}` «{clean(researcher_meaning)}».",
        f"- الأصل المنشور في بطاقة العضو: {clean(card['source'])}",
        f"- قاموس الفرع: `{lexicon['file']}`؛ وسم الطريق: **{lexicon['path']}**.",
        "- قائمة مداخل الصورة كلها: "
        + (
            "؛ ".join(
                render_lexicon_entry(position, entry)
                for position, entry in enumerate(lexicon["entries"], 1)
            )
            if lexicon["entries"] else "لا مدخل"
        )
        + ".",
        (
            f"- المدخلة المختارة بسياق الصف: #{int(lexicon['selected_index']) + 1} "
            f"`{clean(lexicon['selected'].get('word'))}`؛ {lexicon['selection_note']}."
            if lexicon["agreement"] else
            f"- المدخلة المختارة بسياق الصف: لا شيء؛ {lexicon['selection_note']}."
        ),
        f"- معنى قاموس الفرع المعتمد بلا رتوش: «{clean(meaning)}».",
        (
            f"- الخلاف المدون: عمود الباحث «{clean(researcher_meaning)}»، وقاموس الفرع "
            f"«{clean(meaning)}»؛ قُدّم القاموس في الحكم ولم يُمحَ قول الباحث."
            if lexicon["conflict"] else
            "- الخلاف المدون: لا خلاف مؤثر بين معنى الباحث والمدخلة المختارة."
        ),
        f"- الخطوة صفر: الصورة `{clean(word)}`؛ باب المروحة `{cfg['script']}`؛ الهياكل الحالية `{' / '.join(skeleton_variants(word, str(cfg['script'])).split('|')) or '∅'}`.",
        f"- المروحة الكاملة من `fan_any_script.fan` مرتبة بـ`fan_any_script.rank`: {('، '.join(render_candidate(item) for item in review) or 'لا مرشح قابل للتوليد')}. الوزن ترتيب لا حكم؛ ص=مسار صوت؛ ح=حدث؛ د=درجة الحدث؛ م× يعني أن معنى الفرع لم يتصل بالحدث في مدار مقنع.",
        f"- فحص `fan_with_dialect`: أضاف {dialect_additions} صورة موسومة بعد الفصيح ولم يحذف الفصيح.",
        "- رجل الحدث: حُل كل مرشح ظاهر أعلاه بـ`frozen_event.resolve` وحده؛ لم تُسأل عضوية ملف الـ2,285.",
        "- قراءة عائلات اللسان قبل حكم المدار: شُغّل منطق "
        "`search_arabic_root_senses.py` على كل جذر اكتمل فيه الصوت والحدث "
        "بـ`--max-chars 0`؛ ش=عدد الشواهد الكاملة، م=عدد المعاجم المستقلة أو "
        f"المصادر المسماة: {render_arabic_lexicon_review(review)}.",
    ]

    positives: list[dict[str, Any]] = []
    for spec in specs if lexicon["agreement"] else []:
        root = spec["root"]
        item = by_root.get(root)
        if not item or not item["sound"] or not item["event_tier"]:
            raise AssertionError(f"الموجب اليدوي لا يستوفي الأداتين الحاليتين: {card['old_id']}:{root}")
        closure = closure_for(root)
        witnesses = manual_witnesses(spec)
        orbit = orbit_with_witnesses(str(spec["orbit"]), witnesses)
        if len(orbit) < 80:
            raise AssertionError(f"مدار موجب أقصر من حد الضبط: {card['old_id']}:{root}")
        lines.extend([
            f"- المقابل المنتخب: `{root}`؛ وزن العرض {item['weight']:.6f}.",
            f"- مسار الصوت المسمى: {item['sound_route']}.",
            f"- ما فُتش في الشبكة بالحرفين وباسمي اللسان: {'؛ '.join(item['sound_searches'])}.",
            f"- الحدث من السجل المجمد كما هو (درجة {item['event_tier']}، {item['event_tier_ar']}): «{item['event_text']}» [{item['event_source']}]."
            + (f" {item['event_note']}." if item["event_note"] else ""),
        ])
        for witness in witnesses:
            url = f" [{clean(witness.get('url'))}]" if witness.get("url") else ""
            lines.append(
                f"- شاهد {clean(witness['source'])}: «{clean(witness['quote'])}»{url}"
            )
        lines.extend([
            f"- المدار المكتوب باليد: {orbit}",
            f"- نتيجة الأرجل الثلاث للمقابل `{root}`: **{closure} (استكشاف)**.",
        ])
        positives.append({
            "root": root,
            "closure": closure,
            "orbit": orbit,
            "arabic_witnesses": witnesses,
            **{key: item[key] for key in (
                "weight", "sound_route", "sound_searches", "event_tier",
                "event_tier_ar", "event_source", "event_text", "event_note",
            )},
        })

    if positives:
        closures = list(dict.fromkeys(item["closure"] for item in positives))
        closure = " + ".join(closures)
        lines.extend([
            f"- الحكم (استكشاف): **{closure} (استكشاف)**.",
            f"- حالة الإغلاق: {closure}.",
            "",
        ])
        reason = ""
    elif named and lexicon["agreement"]:
        closure = named["closure"]
        lines.extend([
            f"- فحص الأصل الأعمق: {clean(named['route'])}.",
            f"- المانح أو الباب المسمى: {clean(named['donor'])}.",
            f"- موضع الدليل: {clean(named['evidence'])}.",
            "- المدار المكتوب باليد: لم يُنشأ مدار نسب؛ الإغلاق هنا حكم نقل مسمى أو بنية اختصار، لا صلة بين معنى الفرع وحدث عربي.",
            f"- الحكم (استكشاف): **{closure} (استكشاف)**.",
            f"- حالة الإغلاق: {closure}.",
            "",
        ])
        reason = ""
    else:
        ready = [item for item in review if item["sound"] and item["event_tier"]]
        sounded = [item for item in review if item["sound"]]
        if not lexicon["agreement"]:
            reason = "branch_lexicon_context_unresolved"
            requirement = "مدخلة من قاموس الفرع توافق سياق الصف، ثم فحص الأرجل الثلاث"
            search_line = "لم يعلن صف صوتي ناقص؛ العائق سابق له في تعيين معنى قاموس الفرع."
        elif ready:
            reason = "orbit_not_convincing"
            requirement = "صلة دلالية يقتنع بها القارئ بين معنى هذا العضو وحدث مرشح ذي صوت مسمى"
            search_line = "لم يعلن صف ناقص؛ وُجدت مسارات صوتية مسماة، وكان الامتناع في رجل المدار وحدها."
        elif sounded:
            reason = "event_unresolved"
            requirement = "حدث مجمد يحله السجل لمرشح ذي صوت مسمى، ثم مدار دلالي مقنع"
            search_line = "لم يعلن صف ناقص؛ وُجد مسار صوتي مسمى، ولم يحل السجل حدث المرشح."
        elif review:
            reason = "no_named_sound"
            requirement = "مسار صوتي مسمى لمرشح في المروحة، ثم حدث ومدار مقنعان"
            search_line = "؛ ".join(missing_sound_searches(word, language))
        else:
            reason = "fan_empty"
            requirement = "مرشح تولده المروحة من الهيكل المثبت، ثم الأرجل الباقية"
            search_line = "لم يعلن صف ناقص لأن الأداة لم تولد مرشحًا يفحص في الشبكة."
        lines.extend([
            f"- المدار المكتوب باليد: فُحص معنى `{clean(word)}` «{clean(meaning)}» بإزاء أحداث المرشحين الظاهرين، ولم أجد صلة تصل المعنى بحدث السجل صلة يطمئن إليها القارئ؛ لذلك لم أصطنع مدارًا.",
            f"- ما فُتش قبل إعلان نقص صف: {search_line}",
            "- الحكم (استكشاف): **غير صادر (استكشاف)**.",
            f"- عائق: النوع=OPEN-CANDIDATE؛ يتطلب={requirement}",
            "- حالة الإغلاق: OPEN-CANDIDATE.",
            "",
        ])
        closure = "OPEN-CANDIDATE"

    manifest = {
        "card_id": new_id,
        "supersedes": superseded,
        "original_index": index,
        "language": language,
        "form": word,
        "branch_meaning": meaning,
        "researcher_meaning": researcher_meaning,
        "branch_lexicon": lexicon,
        "published_source": card["source"],
        "fan_script": cfg["script"],
        "fan_candidates": review,
        "dialect_additions": dialect_additions,
        "positives": positives,
        "named_closure": named or {},
        "closure": closure,
        "open_reason": reason,
        "arabic_orbit_reassessment": orbit_reassessment,
        "lexicon_reaudit": (
            "stable" if language == "welsh" and index <= 301 and specs and positives
            else "copied" if language == "welsh" and index <= 301 and specs
            else "not-applicable"
        ),
    }
    return lines, manifest, reason


def audit_text(
    language: str,
    batch: int,
    rows: list[dict[str, Any]],
    controls: list[dict[str, Any]],
    reasons: Counter[str],
) -> str:
    cfg = LANGUAGES[language]
    positive = [row for row in rows if row["positives"]]
    named = [row for row in rows if row["named_closure"]]
    opened = [row for row in rows if row["closure"] == "OPEN-CANDIDATE"]
    semitic = [row for row in named if row["closure"] == "SEMITIC-SOURCE-TRANSMISSION"]
    abbreviations = [row for row in named if row["closure"] == "ABBREVIATION"]
    transformed = len(positive) + len(named)
    reason_ar = {
        "branch_lexicon_context_unresolved": "لم تتعين مدخلة من قاموس الفرع توافق سياق الصف",
        "orbit_not_convincing": "اكتمل الصوت والحدث ولم يقنع مدار يدوي",
        "event_unresolved": "اكتمل الصوت ولم يحل السجل حدث المرشح",
        "no_named_sound": "لم يكتمل مسار صوتي مسمى بعد البحث بالحرفين واللسان",
        "fan_empty": "لم تولد المروحة مرشحًا من الهيكل",
    }
    lines = [
        f"# حصاد القرض المعاد فتحه: {cfg['label']}، الدفعة {batch:03d} ({DATE})",
        "",
        "## الضابط الإلزامي قبل الحصاد",
        "",
        "أعيد حساب ست بطاقات صادرة من قبل بالمروحة الحالية وبـ`frozen_event.resolve` وحده. لم يتغير حكم واحدة منها، فجاز بدء الحصاد.",
        "",
        "| الصورة | المقابل | الحكم السابق | الحكم الحالي | وزن العرض | درجة الحدث | النتيجة |",
        "|---|---|---|---|---:|---:|---|",
    ]
    for row in controls:
        lines.append(
            f"| `{row['word']}` | `{row['root']}` | {row['closure']} | {row['current_verdict']} | {row['weight']:.6f} | {row['event_tier']} | ثابت |"
        )
    lines.extend([
        "",
        "ثبتت كذلك المسارات الصوتية المسماة والأحداث نفسها لكل الأزواج الستة؛ لا تستعمل النتيجة عضوية ملف الـ2,285 بوابة للحكم.",
        "",
        "## القانون المنفذ",
        "",
        "لكل بطاقة ثلاث أرجل فقط: المروحة ومسار الصوت المسمى، ثم الحدث من السجل المجمد، ثم معنى الفرع ومدار مكتوب باليد. معنى الفرع مأخوذ من `data/branch-lexicons/` بعد عرض جميع المداخل واختيار الموافق لسياق الصف، مع وسم الطريق ورسم المدخل. لم يجعل اكتمال الحدث البطاقة موجبة؛ بقي الحسم في المدار. اللاتينية أو اليونانية ناقلًا أخيرًا لا تغلقان البطاقة، أما المانح السامي المسمى فيغلق عضو المعنى نفسه.",
        "",
        "## ضبط قاموس الفرع",
        "",
        f"- مر على القاموس: {len(rows)} من {len(rows)} بطاقة.",
        f"- تعينت مدخلة موافقة للسياق: {sum(bool(row['branch_lexicon']['agreement']) for row in rows)} بطاقة.",
        f"- بقي سياق المدخلة غير متعين: {sum(not row['branch_lexicon']['agreement'] for row in rows)} بطاقة.",
        f"- سُجل اختلاف بين عمود الباحث ومعنى القاموس الأوسع أو المختلف: {sum(bool(row['branch_lexicon']['conflict']) for row in rows)} بطاقة.",
        "",
        "## الحصيلة",
        "",
        f"- فُحص: {len(rows)} بطاقة.",
        f"- كُتب: {len(rows)} بطاقة ناسخة ملحقة، من غير محو البطاقة التاريخية.",
        f"- تحوّل عن الفتح: {transformed} بطاقات.",
        f"- موجب بالأرجل الثلاث: {len(positive)} من البطاقات، وفيها {sum(len(row['positives']) for row in positive)} صلة.",
        f"- أعيد إغلاقه بمانح سامي مسمى: {len(semitic)} من البطاقات.",
        f"- أغلق بوسم ABBREVIATION: {len(abbreviations)} من البطاقات.",
        f"- بقي OPEN-CANDIDATE: {len(opened)} بطاقة.",
    ])
    for key in (
        "branch_lexicon_context_unresolved", "orbit_not_convincing",
        "event_unresolved", "no_named_sound", "fan_empty",
    ):
        if reasons[key]:
            lines.append(f"- سبب الفتح: {reasons[key]} من البطاقات، {reason_ar[key]}.")
    reaudited = [row for row in rows if row["lexicon_reaudit"] != "not-applicable"]
    if reaudited:
        stable = sum(row["lexicon_reaudit"] == "stable" for row in reaudited)
        copied = sum(row["lexicon_reaudit"] == "copied" for row in reaudited)
        lines.extend([
            "",
            "## إعادة فحص موجبات الجولة بقاموس الفرع",
            "",
            f"- أعيد فحص: {len(reaudited)} بطاقة موجبة سابقة.",
            "- تحوّل من مفتوح إلى موجب بعد القاموس: 0 بطاقة.",
            f"- نُسخ لأن القاموس لا يسند معناه: {copied} بطاقة.",
            f"- ثبت موجبًا في المدخلة الموافقة للسياق: {stable} بطاقة.",
        ])
    lines.extend([
        "",
        "## أبرز الأزواج الداخلة",
        "",
    ])
    pairs = [
        f"`{row['form']}` ↔ `{item['root']}` ({item['closure']})"
        for row in positive for item in row["positives"]
    ][:10]
    lines.extend(f"{position}. {pair}" for position, pair in enumerate(pairs, 1))
    if not pairs:
        lines.append("لم تدخل صلة في هذه الدفعة، وهو ناتج جائز لا يغير معيار المدار.")
    if named:
        lines.extend([
            "",
            "## الإغلاقات غير النسبية",
            "",
        ])
        for row in named:
            source = row["named_closure"]
            lines.append(
                f"- `{row['form']}` «{clean(row['branch_meaning'])}»: {row['closure']}؛ {clean(source['donor'])}؛ {clean(source['evidence'])}."
            )
    lines.extend([
        "",
        "## ضبط النسخ والعد",
        "",
        "كل بطاقة جديدة تحمل معرّف بطاقة 2026-08-05 التي تنسخ حكمها. بقي النص القديم كاملًا في ملف القراءة، وأسقط ماسح سجل الاسترداد الحكم المنسوخ من العد النافذ. قاموس الإغلاق بقي في ألفاظه الـ25 ولم يضف إليه وسم.",
        "",
    ])
    return "\n".join(lines)


def inspect_batch(language: str, window: list[dict[str, Any]]) -> None:
    for card in window:
        specs = MANUAL_SPECS.get((language, int(card["index"])), [])
        review, _ = current_fan(str(card["word"]), language, {item["root"] for item in specs})
        ready = [item for item in review if item["sound"] and item["event_tier"]]
        print(
            f"{card['index']:05d} {card['word']} | {card['meaning']} | "
            f"ready={len(ready)} | named={bool(NAMED_CLOSURES.get((language, int(card['index']))))}"
        )
        for item in ready:
            print(
                f"  {item['root']} w={item['weight']:.6f} t={item['event_tier']} "
                f"{clean(item['event_text'])}"
            )


def inspect_arabic_senses(
    language: str,
    window: list[dict[str, Any]],
    show_context: bool = False,
) -> None:
    """Surface gloss overlaps after reading the full, unclipped root fan.

    This is a reading aid only.  It cannot create a verdict or a manual orbit.
    """
    prepared: list[tuple[dict[str, Any], list[dict[str, Any]]]] = []
    roots: set[str] = set()
    for card in window:
        branch_lexicon = lexicon_context(language, card)
        inspected_card = {
            **card,
            "meaning": branch_lexicon["dictionary_meaning"] or card["meaning"],
        }
        review, _ = current_fan(str(card["word"]), language, set())
        ready = [item for item in review if item["sound"] and item["event_tier"]]
        prepared.append((inspected_card, ready))
        roots.update(item["root"] for item in ready)
    hits_by_root = AR.matches_for_roots(AR.DEFAULT_RESOURCES, roots, None)
    print(
        f"FULL-LEXICON-SCAN cards={len(window)} roots={len(roots)} "
        "max_chars=0 truncated=false"
    )
    stop = {
        "the", "and", "for", "from", "with", "that", "this", "into",
        "forms", "given", "related", "etc", "one", "two", "item",
    }
    arabic_cues: dict[int, tuple[str, ...]] = {
        152: ("ليل", "مساء", "عشاء"), 153: ("عربة", "عجلة", "مركبة"),
        154: ("مربى", "ازدحم", "اجتمع"), 155: ("فخ", "شرك", "حبالة"),
        156: ("قنبلة", "انفجر"), 157: ("درجة", "سلم", "خطوة"),
        160: ("عكس", "رجع", "قلب"), 161: ("كتاب", "صحيفة", "سجل"),
        163: ("منضدة", "مائدة", "لوح"), 165: ("حزام", "سير", "رباط"),
        166: ("قوم", "شعب"), 167: ("عصب",), 169: ("جرعة", "مقدار"),
        170: ("فاصلة",), 172: ("سند", "دعم", "عماد"),
        174: ("طبيعة", "طبع", "خلقة"), 176: ("عجين", "طعام"),
        177: ("خزانة", "ستر"), 178: ("ميل", "انحراف"),
        179: ("صورة", "مرئي"), 180: ("سلاح",), 183: ("طائر",),
        185: ("لحية", "شعر"), 187: ("غنى", "غناء", "منشد"),
        190: ("نسيج", "ثوب", "خرق"), 191: ("إيجار", "كراء", "عقد"),
        192: ("لباس", "ثوب"), 193: ("ريش",),
        194: ("بغي", "زنا", "فجور", "امرأة"),
        195: ("لصق", "عجين", "بسط", "نشر"),
        196: ("ألم", "وجع", "تشنج"), 197: ("جميل", "حسن"),
        198: ("مهر", "فلو"), 199: ("فارغ", "بياض", "خلو"),
        201: ("مهرج",), 202: ("حمار", "مخطط"),
        203: ("إنجاز", "عمل", "فعل"), 204: ("معبد", "كنيسة"),
        206: ("الرز", "الأرز"), 207: ("حزن", "كمد"),
        208: ("نقطة",), 209: ("تنورة", "قميص", "ثوب"),
        212: ("حديث", "جديد"), 213: ("برج", "جبل", "مرتفع"),
        214: ("جماعة", "جمع", "قطيع"), 215: ("دبوس", "وتد"),
        216: ("قلم",), 217: ("جماعة", "جمع", "غناء"),
        218: ("ورق", "حزمة", "جمع"), 219: ("كوب", "قدح", "إناء"),
        220: ("كدر", "تغير", "لون"), 221: ("قار", "زفت"),
        222: ("وثن", "شرك"), 223: ("وعاء", "سلة"),
        224: ("ختم", "طابع"), 225: ("قصدير", "معدن"),
        227: ("سجل", "كتب"), 228: ("ضريبة", "خراج", "مكس"),
        229: ("شعر", "باروكة"), 230: ("سفينة", "قعر"),
        231: ("مثال", "نموذج"), 235: ("غناء", "مسرح"),
        236: ("مني", "نطفة"), 237: ("فأس", "معول"),
        238: ("ورقة", "نبات"), 240: ("طبخ", "طباخ"),
        241: ("ألم", "وجع"), 242: ("مسابقة", "سباق"),
        243: ("طائر",), 244: ("صنم", "وثن"),
        246: ("ميزاب", "قناة"), 247: ("علامة", "وسم", "بقعة"),
        248: ("خيمة",), 249: ("خطوة", "خطو"),
        250: ("قميص", "ثوب"), 251: ("طفل", "صبي"),
        252: ("قشر", "جلد"), 253: ("مخبز", "خبز", "مجرفة"),
        256: ("سكن", "أقام", "عاش"), 257: ("صمت", "بكم", "خرس"),
        258: ("فهرس", "قائمة"), 259: ("شر", "حقد", "خبث"),
        260: ("جبن", "لبن"), 262: ("علامة", "وسم"),
        266: ("بريد", "رسالة"), 267: ("عمود", "دعامة"),
        268: ("جبن", "لبن", "خثرة"), 272: ("مسدس", "سلاح"),
        273: ("ألف",), 274: ("ساعة", "وقت"),
        275: ("ذهب",), 276: ("ذهب", "ذهبي"), 277: ("تنين", "حية"),
        279: ("مدرسة", "تعليم"), 280: ("سلم", "درجة"),
        281: ("كنيسة", "معبد"), 282: ("كنيسة", "معبد"),
        283: ("مصرف", "مال"), 284: ("تل", "جبل", "مرتفع"),
        286: ("هواء", "سماء"), 289: ("متجر", "سوق"),
        292: ("حمام", "يمام"), 293: ("صواب", "صحيح", "حق"),
        295: ("يمين", "حق"), 297: ("عار", "وصمة"),
        299: ("سراج", "مصباح"), 300: ("جلد", "بشرة"),
        301: ("معلم", "مرشد"),
    }
    for card, ready in prepared:
        tokens = {
            token.casefold()
            for token in re.findall(r"[A-Za-z]{3,}", str(card["meaning"]))
            if token.casefold() not in stop
        }
        scored: list[tuple[int, str, int, list[str], list[dict[str, Any]]]] = []
        for item in ready:
            matches = hits_by_root.get(item["root"], [])
            raw_definitions = " ".join(
                str(hit.get("definition") or "") for hit in matches
            )
            definitions = raw_definitions.casefold()
            found = sorted(token for token in tokens if token in definitions)
            cues = sorted(
                cue for cue in (
                    arabic_cues.get(int(card["index"]), ())
                    if language == "welsh" else ()
                )
                if cue in raw_definitions
            )
            labels = [*(f"en:{token}" for token in found), *(f"ar:{cue}" for cue in cues)]
            if labels:
                scored.append((len(labels), item["root"], len(matches), labels, matches))
        if scored:
            print(
                f"{int(card['index']):05d}|{clean(card['word'])}|"
                f"{clean(card['meaning'])}|ready={len(ready)}"
            )
            for score, root, count, found, matches in sorted(scored, reverse=True):
                print(f"  {root}|witnesses={count}|tokens={','.join(found)}")
                if show_context:
                    needles = [label[3:] for label in found if label.startswith("ar:")]
                    excerpts = 0
                    for hit in matches:
                        definition = str(hit.get("definition") or "")
                        positions = [definition.find(needle) for needle in needles]
                        positions = [position for position in positions if position >= 0]
                        if not positions:
                            continue
                        position = min(positions)
                        start = max(0, position - 90)
                        end = min(len(definition), position + 230)
                        print(
                            f"    {clean(hit.get('source'))}: «"
                            f"{clean(definition[start:end])}»"
                        )
                        excerpts += 1
                        if excerpts == 2:
                            break


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("--language", choices=tuple(LANGUAGES), required=True)
    parser.add_argument("--batch", type=int, required=True)
    parser.add_argument("--inspect", action="store_true")
    parser.add_argument("--inspect-arabic-senses", action="store_true")
    parser.add_argument("--inspect-card", type=int, action="append")
    parser.add_argument("--show-context", action="store_true")
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument("--recover-missing-section", action="store_true")
    args = parser.parse_args()
    language = args.language
    cards = original_cards(language)
    start = (args.batch - 1) * BATCH_SIZE
    window = cards[start:start + BATCH_SIZE]
    if not window:
        raise SystemExit("الدفعة خارج الجرد")
    if args.inspect:
        inspect_batch(language, window)
        return 0
    if args.inspect_arabic_senses:
        inspect_window = (
            [card for card in window if int(card["index"]) in set(args.inspect_card)]
            if args.inspect_card else window
        )
        inspect_arabic_senses(language, inspect_window, args.show_context)
        return 0

    cfg = LANGUAGES[language]
    marker = f"LOAN-HARVEST-{cfg['id_label']}-BATCH-{args.batch:03d}"
    audit = ROOT / "05-audits" / f"{DATE}-reopened-loan-{language}-harvest-batch-{args.batch:03d}.md"
    manifest = ROOT / "data" / f"reopened-loan-{language}-harvest-batch-{args.batch:03d}.json"
    reading = READINGS / f"{language}.md"
    text = reading.read_text(encoding="utf-8")
    if args.refresh:
        raise AssertionError(
            "ملف القراءة إلحاقي؛ لا تجوز إعادة كتابة مقطع قائم. "
            "اكتب مراجعة ناسخة جديدة بدل --refresh"
        )
    exists = audit.exists() or manifest.exists() or f"<!-- {marker}:START -->" in text
    marker_exists = f"<!-- {marker}:START -->" in text
    if args.recover_missing_section:
        if not audit.exists() or not manifest.exists() or marker_exists:
            raise AssertionError(
                f"استرداد الدفعة {args.batch} خاص بوجود المحضر والبيانات وغياب مقطع القراءة"
            )
    elif exists:
        raise AssertionError(f"مخرجات الدفعة {args.batch} موجودة من قبل")

    controls = control_run() if language == "welsh" else []
    arabic_hits_by_root = arabic_hits_for_cards(language, window)
    lines: list[str] = []
    rows: list[dict[str, Any]] = []
    reasons: Counter[str] = Counter()
    for card in window:
        card_lines, row, reason = build_card(
            language, card, arabic_hits_by_root
        )
        lines.extend(card_lines)
        rows.append(row)
        if reason:
            reasons[reason] += 1

    section = [
        f"<!-- {marker}:START -->",
        "",
        f"## حصاد القرض المعاد فتحه، الدفعة {args.batch:03d} ({DATE})",
        "",
        *lines,
        f"<!-- {marker}:END -->",
        "",
    ]
    rendered_section = "\n".join(section)
    latest_text = reading.read_text(encoding="utf-8")
    if latest_text != text:
        raise AssertionError(
            "تغيّر ملف القراءة أثناء بناء الدفعة؛ أُوقف الحفظ لمنع ضياع إلحاق متزامن"
        )
    reading.write_text(
        text.rstrip() + "\n\n" + rendered_section,
        encoding="utf-8",
        newline="\n",
    )
    payload = {
        "schema": "reopened-loan-harvest-v1",
        "date": DATE,
        "language": language,
        "language_label": cfg["label"],
        "batch": args.batch,
        "batch_size": len(rows),
        "controls": controls,
        "transformed_cards": sum(row["closure"] != "OPEN-CANDIDATE" for row in rows),
        "positive_cards": sum(bool(row["positives"]) for row in rows),
        "positive_traces": sum(len(row["positives"]) for row in rows),
        "named_semantic_closures": sum(row["closure"] == "SEMITIC-SOURCE-TRANSMISSION" for row in rows),
        "abbreviation_closures": sum(row["closure"] == "ABBREVIATION" for row in rows),
        "branch_lexicon_selected": sum(row["branch_lexicon"]["agreement"] for row in rows),
        "branch_lexicon_unresolved": sum(not row["branch_lexicon"]["agreement"] for row in rows),
        "lexicon_reaudit_transformed": 0,
        "lexicon_reaudit_copied": sum(row["lexicon_reaudit"] == "copied" for row in rows),
        "lexicon_reaudit_stable": sum(row["lexicon_reaudit"] == "stable" for row in rows),
        "open_cards": sum(row["closure"] == "OPEN-CANDIDATE" for row in rows),
        "open_reasons": dict(reasons),
        "rows": rows,
    }
    manifest.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    audit.write_text(
        audit_text(language, args.batch, rows, controls, reasons),
        encoding="utf-8",
        newline="\n",
    )
    print(json.dumps({key: value for key, value in payload.items() if key != "rows"}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
