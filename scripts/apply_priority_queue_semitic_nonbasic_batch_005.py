#!/usr/bin/env python3
"""Apply the non-basic Hebrew/Aramaic rows in the path-2 queue."""

from __future__ import annotations

import json
import os
import tempfile
import unicodedata
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
COVERAGE = ROOT / "04-cross-linguistic" / "data" / "lane_a_coverage.jsonl"
HEBREW = ROOT / "04-cross-linguistic" / "readings" / "hebrew.md"
ARAMAIC = ROOT / "04-cross-linguistic" / "readings" / "aramaic.md"
DATE = "2026-08-01"
BATCH = "priority-queue-semitic-005-nonbasic"
HEBREW_MARKER = "<!-- PATH2-PRIORITY-QUEUE:HEBREW-005-NONBASIC:BEGIN -->"
ARAMAIC_MARKER = "<!-- PATH2-PRIORITY-QUEUE:ARAMAIC-005-NONBASIC:BEGIN -->"


Layer = tuple[str, bool, str]


CHANGES: dict[str, dict[str, Layer]] = {
    "kaikki_hebrew:1323:en-שש-he-num-aKqzGmk9": {
        "root": ("FORM-OF-ISOLATED", False, "שש مؤنث إحالي إلى שישה؛ الحكم الاشتقاقي للأصل المعجمي لا للصورة التابعة."),
        "nucleus": ("FORM-OF-ISOLATED", False, "الصورة التابعة لا تنشئ نواة مستقلة ولا ترث حكم الأصل آليًا."),
    },
    "kaikki_hebrew:1326:en-שישה-he-num-RHeNgjZe": {
        "root": ("ROOT-ECHO", True, "صلة العدد السادس مسندة من *šidṯatum إلى ستة، لكن مسار الصوامت المدغمة لا يحقق تطابقًا جذريًا تامًا."),
        "nucleus": ("OPEN-CANDIDATE", False, "العربية القديمة ترد ستة إلى سدسة؛ لا تُجعل الصورة المدغمة ست نواة أصلية، ومدار ست المجمد في الستر لا يدل على العدد."),
    },
    "kaikki_aramaic:264:en-שת-arc-num-pNZtnEPK": {
        "root": ("ROOT-ECHO", True, "مصدر العضو يصرح بقرابة *šidṯ- مع ست؛ الصلة العددية ثابتة، لكن الإدغامات لا تسند TRACE جذريًا كاملًا."),
        "nucleus": ("OPEN-CANDIDATE", False, "شاهد العربية يرد ست إلى سدس، والمرشح ست خارج النطاق ومداره لا يحمل العدد؛ لا نواة."),
    },
    "kaikki_hebrew:908:en-אף-he-noun-134iEj5k": {
        "root": ("ROOT-TRACE", True, "الصورة المستعادة *ʔanp- تقابل أ-ن-ف كاملة مع p/f في الأنف نفسه."),
        "nucleus": ("OPEN-CANDIDATE", False, "النون أصل في الصورة المستعادة والعربية؛ لا يسوغ إسقاطها لقبول قاعدة HSED الثنائية *ʔap-."),
    },
    "kaikki_aramaic:1617:en-אפא-arc-noun-VTUotbYH": {
        "root": ("ROOT-ECHO", True, "אפא الوجه يجاور أسرة *ʔanp- للأنف بقرينة الصف الخارجي والعبرية، لكن فقد النون والانزياح من الأنف إلى الوجه يمنعان TRACE."),
        "nucleus": ("OPEN-CANDIDATE", False, "بعد تعرية ألف الحالة يبقى ʔ-p؛ لا يُصدر هذا الزوج نواة الفم، ولا تُعد النون العربية زيادة بلا دليل مستقل."),
    },
    "kaikki_aramaic:819:en-אתא-arc-verb-NxJ~s~mm": {
        "root": ("ROOT-ECHO", True, "אתא وأتى للمجيء نفسه، مع اختلاف الضعيف الثالث بين ʔ/w/y؛ لذلك صدى جذري لا TRACE كامل."),
        "nucleus": ("OPEN-CANDIDATE", False, "تحليل *ʔVt- الخارجي قوي، لكن أت ليست مدخلًا في فهرس النوى المجمد، والبديل المرخص ءث لا يحمل المجيء."),
    },
    "kaikki_hebrew:160:en-יום-he-noun-1n7m-QBp": {
        "root": ("ROOT-TRACE", True, "الجذر y-w-m يقابل ي-و-م كاملًا في اليوم."),
        "nucleus": ("OPEN-CANDIDATE", False, "حاشية *yam-? استفهامية، ولا تسمي الواو توسعة ثانوية؛ لا تسقط من يوم."),
    },
    "kaikki_aramaic:188:en-יומא-arc-noun-lEwn5bl6": {
        "root": ("ROOT-TRACE", True, "بعد تعرية ألف الحالة يبقى y-w-m، ويقابل ي-و-م كاملًا في اليوم."),
        "nucleus": ("OPEN-CANDIDATE", False, "الواو أصل في الصورة المنشورة *yawm-؛ اقتراح *yam-? لا يكفي لإسقاطها."),
    },
}


HEBREW_CARDS = r'''

<!-- PATH2-PRIORITY-QUEUE:HEBREW-005-NONBASIC:BEGIN -->

## طابور المسار الثاني — غير الأساسي العبري (2026-08-01)

### بطاقة: صف `שש`، العضو التابع `kaikki_hebrew:1323:en-שש-he-num-aKqzGmk9`
- أصل المرشح: طابور المسار 2، اقتراح كلاين 1987 في مادة `שֵׁשׁ`، من صفوف `leads-semitic-sisters.md`.
- كلمة الفرع الموجودة بهذا الرسم: `שש` shésh، num، «feminine of שישה “six”» [Kaikki Hebrew]؛ هي إحالة صرفية صريحة، لا أصل معجمي مستقل.
- جذر الفرع بعد التعرية: لا يُستخرج من الصورة التابعة؛ أُحيل إلى الأصل الموجود `שישה` في البطاقة التالية، ولم يُسقط صامت.
- حكم طبقة الجذر: FORM-OF-ISOLATED. حكم طبقة النواة: FORM-OF-ISOLATED.
- المصفاة: موافقة كلاين ليست حكمًا، والصورة التابعة لا ترث آليًا.
- الحكم (استكشاف): FORM-OF-ISOLATED في الطبقتين.
- سطر النسخ: السابق MORPHOLOGY-GAP في الطبقتين؛ الجديد FORM-OF-ISOLATED؛ السبب: حُلّت الإحالة إلى أصل موجود بدل إبقاء فجوة صرفية عامة.

### بطاقة: أصل `שישה`، العضو `kaikki_hebrew:1326:en-שישה-he-num-RHeNgjZe`
- أصل المرشح: طابور المسار 2، اقتراح كلاين 1987 في مادة `שֵׁשׁ`؛ فُتح الأصل الذي أحال إليه عضو الصف.
- كلمة الفرع: `שישה` shishá، num، «six» [Kaikki Hebrew]؛ مصدر العضو يعيده إلى `*šidṯatum`.
- جذر الفرع بصوامته التاريخية كاملة بعد تعرية نهاية العدد: `š-d-ṯ`؛ لا يُختزل إلى الصامتين الظاهرين، ولا يسقط الدال التاريخي.
- حكم طبقة الجذر: ROOT-ECHO للعدد السادس؛ لا TRACE لأن مسار الإدغام بين `*šidṯ-` و`سدس/ست` غير مطابق صامتًا صامتًا. حكم طبقة النواة: OPEN-CANDIDATE.
- مسح العربية: كتاب العين للخليل بن أحمد: «سِتَّةٌ وسِتٌّ في الأصل سِدْسَةٌ وسِدْسٌ» و«تصغير سِتّةٍ سُدَيْسَة»؛ تاج اللغة وصحاح العربية للجوهري: «سِتَّةُ رجالٍ وسِتُّ نسوةٍ» و«أصلُ سِتَّةٍ سِدْسَةٌ».
- الجسر الدلالي الصريح: الطرفان يسمّيان العدد الواقع بين خمسة وسبعة؛ الصلة معجمية عددية، لكن شاهد العربية نفسه يرد الصورة الثنائية الظاهرة إلى أصل ذي صوامت ثلاثة.
- المصفاة الاتجاهية: مصدر العضو يسمي الإرث السامي ولا مانحًا؛ موافقة كلاين لا تحول الإدغام إلى نواة.
- الحكم (استكشاف): ROOT-ECHO؛ النواة OPEN-CANDIDATE.
- سطر النسخ: السابق root=OPEN-CANDIDATE؛ الجديد ROOT-ECHO؛ السبب: قُرئ الأصل لا الصورة التابعة، وثبتت القرابة العددية مع حفظ `*š-d-ṯ`. النواة بقيت مفتوحة.

### بطاقة: `אף`، العضو `kaikki_hebrew:908:en-אף-he-noun-134iEj5k`
- أصل المرشح: طابور المسار 2، اقتراح Orel وStolbova، `HSED 46`؛ يبنيان `*ʔap-` «فم» ويعدان النون زيادة.
- كلمة الفرع: `אף` af، noun، «nose» [Kaikki Hebrew]. مصدر العضو نفسه يستعيد `*ʔanp-`؛ جذر الفرع كاملًا `ʔ-n-p`، والنون أصل في هذه القراءة.
- الزوج المقترح `ʔ-p` من الموضعين 1 و3؛ النون في الموضع 2 أصل مستعاد، لا سابقة ولا لاحقة، فلا تسقط.
- حكم طبقة الجذر: ROOT-TRACE؛ `*ʔanp- ↔ أ-n-f` مع `p/f`. حكم طبقة النواة: OPEN-CANDIDATE.
- مسح العربية: لسان العرب لابن منظور: «الأنف المنخر معروف، وهو للإنسان وغيره»؛ تاج العروس لمرتضى الزبيدي: «الأنف للإنسان وغيره، وهو مجموع المنخرين والحاجز والقصبة».
- الجسر الدلالي الصريح: الطرفان يسميان الأنف، عضو الشم نفسه؛ الصلة في الصورة الثلاثية المستعادة، لا في معنى «الفم» الخارجي.
- المصفاة الاتجاهية: لا مانح مسمى؛ خولف اقتراح HSED لأن القراءة العضوية وشاهد العربية يحفظان النون.
- الحكم محفوظ: ROOT-TRACE؛ النواة OPEN-CANDIDATE؛ لا سطر نسخ لأن الحكمين لم يتغيرا.

### بطاقة فجوة: صف الفعل العبري `ʔty אתה` «أتى»
- أصل المرشح: طابور المسار 2، اقتراح ميليتاريف `SEM 1439` وكلاين 1987 في مادة الفعل `אתה`.
- المطابقة العضوية: العضو الموجود `kaikki_hebrew:414:en-אתה-he-pron-TMwdrlNN` ضمير «أنت»، من `*ʔanta`، وليس فعل «أتى»؛ لم يُلبس حكم الفعل للضمير ولم تُمس أحكام الضمير السابقة.
- جذر الفرع للفعل المقصود: غير قابل للتقرير من عضو غائب؛ سجل الصف `ENTRY-GAP` للمعنى اللفظي. لا زوج مأخوذ ولا صامت ساقط.
- حكم الصف الخارجي: ENTRY-GAP في طبقتي الجذر والنواة إلى أن يدخل عضو الفعل نفسه الجرد.
- المصفاة: التشابه الكتابي لا يلغي اختلاف الصنف والمعنى؛ موافقة المقترحين ليست حكمًا.
- الحكم (استكشاف): ENTRY-GAP؛ لا تغيير تغطية، لأن العضو الموجود يخص ضميرًا آخر.

### بطاقة: `יום`، العضو `kaikki_hebrew:160:en-יום-he-noun-1n7m-QBp`
- أصل المرشح: طابور المسار 2، اقتراح ميليتاريف `SEM 792` وكلاين 1987 في مادة `יוֹם`؛ حاشية ميليتاريف: «مبني على ثنائي *yam-؟» بعلامة السؤال.
- كلمة الفرع: `יום` yom، noun، «day: the period between dawn and dusk» [Kaikki Hebrew]. جذر الفرع كاملًا `y-w-m` من الصورة المنشورة `*yawm-`؛ لا زيادة صرفية.
- الزوج المقترح `y-m` من الموضعين 1 و3؛ الواو في الموضع 2 أصل في الصورة المنشورة، والحاشية الاستفهامية لا تسميها توسعة ثانوية.
- حكم طبقة الجذر: ROOT-TRACE؛ `y-w-m ↔ ي-w-m`. حكم طبقة النواة: OPEN-CANDIDATE.
- مسح العربية: لسان العرب لابن منظور: «اليَوْمُ: معروفٌ مِقدارُه من طلوع الشمس إِلى غروبها»؛ تاج العروس لمرتضى الزبيدي: «اليَوْمُ: معروفٌ، مِقْدَارُهُ مِنْ طُلُوعِ الشَّمْسِ إِلَى غُرُوبِهَا».
- الجسر الدلالي الصريح: الطرفان يسميان المدة النهارية المحدودة بين طلوع الشمس وغروبها؛ الصلة في `يوم` كاملًا.
- المصفاة الاتجاهية: لا مانح مسمى؛ موافقة ميليتاريف وكلاين ليست حكمًا، وعلامة السؤال لا تقوم مقام حاشية `קום` الصريحة.
- الحكم محفوظ: ROOT-TRACE؛ النواة OPEN-CANDIDATE؛ لا سطر نسخ لأن الحكمين لم يتغيرا.

<!-- PATH2-PRIORITY-QUEUE:HEBREW-005-NONBASIC:END -->
'''


ARAMAIC_CARDS = r'''

<!-- PATH2-PRIORITY-QUEUE:ARAMAIC-005-NONBASIC:BEGIN -->

## طابور المسار الثاني — غير الأساسي الآرامي (2026-08-01)

### بطاقة: `שת`، العضو `kaikki_aramaic:264:en-שת-arc-num-pNZtnEPK`
- أصل المرشح: طابور المسار 2، اقتراح كلاين 1987 في مادة `שֵׁשׁ`، من صفوف `leads-semitic-sisters.md`.
- كلمة الفرع: `שת` sheṯ، num، «six (6)» [Kaikki Aramaic]. مصدر العضو يعيده إلى `*šidṯ-`؛ جذر الفرع التاريخي كاملًا `š-d-ṯ`، لا الزوج السطحي وحده.
- لا زوج نووي صادر: الصورة `š-t` جاءت بعد تاريخ إدغام، والدال التاريخي لا يحذف بالانتقاء؛ كما أن `ست` في الفهرس خارج نطاق هذا الصف ومدارها «التغطية والإخفاء» لا يدل على العدد.
- حكم طبقة الجذر: ROOT-ECHO؛ الصلة العددية مصرح بها، لكن المسار لا يحقق تطابقًا جذريًا تامًا. حكم طبقة النواة: OPEN-CANDIDATE.
- مسح العربية: كتاب العين للخليل بن أحمد: «سِتَّةٌ وسِتٌّ في الأصل سِدْسَةٌ وسِدْسٌ» و«تصغير سِتّةٍ سُدَيْسَة»؛ تاج اللغة وصحاح العربية للجوهري: «سِتَّةُ رجالٍ وسِتُّ نسوةٍ» و«أصلُ سِتَّةٍ سِدْسَةٌ».
- الجسر الدلالي الصريح: الطرفان يسمّيان العدد السادس نفسه؛ شاهد العربية يحفظ الأصل الثلاثي، ولذلك تثبت الصلة المعجمية ولا تثبت نواة ثنائية.
- المصفاة الاتجاهية: مصدر العضو يسمي قرابة سامية ولا مانحًا؛ موافقة كلاين ليست حكمًا.
- الحكم (استكشاف): ROOT-ECHO؛ النواة OPEN-CANDIDATE.
- سطر النسخ: السابق root=OPEN-CANDIDATE؛ الجديد ROOT-ECHO؛ السبب: ثبتت القرابة العددية المنشورة مع حفظ `*š-d-ṯ`. النواة بقيت مفتوحة.

### بطاقة: `אפא`، العضو `kaikki_aramaic:1617:en-אפא-arc-noun-VTUotbYH`
- أصل المرشح: طابور المسار 2، اقتراح Orel وStolbova، `HSED 46`؛ يبنيان الأصل على `*ʔap-` «فم» ويعدان النون زيادة.
- كلمة الفرع: `אפא`، noun، «face, countenance» [Kaikki Aramaic]. بعد تعرية ألف الحالة بصفر الآرامية يبقى الجذع السطحي كاملًا `ʔ-p`؛ الصف الخارجي يقترح ربطه بأسرة `*ʔanp-`.
- الصامتان السطحيان 1 و2 أُخذا كلاهما؛ لا ثالث سطحي. لكن النون في العربية `أنف` وفي الصورة العبرية المستعادة أصل، فلا تُسمى زيادة لإصدار نواة `ʔ-p`.
- حكم طبقة الجذر: ROOT-ECHO، لا TRACE: الصلة بين الأنف والوجه مجاز جزء وكل، وفقد النون غير محسوم في العضو. حكم طبقة النواة: OPEN-CANDIDATE.
- مسح العربية من المادة نفسها `أنف`: لسان العرب لابن منظور: «الأنف المنخر معروف، وهو للإنسان وغيره»؛ تاج العروس لمرتضى الزبيدي: «الأنف للإنسان وغيره، وهو مجموع المنخرين والحاجز والقصبة».
- الجسر الدلالي الصريح: الأنف جزء بارز من الوجه، فيجوز أن يجاور اسم الجزء اسم الوجه في صدى معجمي؛ لا يجوز أن يتحول هذا المجاز إلى تطابق معنى أو إلى إسقاط النون.
- المصفاة الاتجاهية: لا مانح مسمى؛ خُولف معنى «الفم» في HSED ولم يؤخذ شاهد `وجه` للصورة وشاهد `أنف` للمعنى.
- الحكم (استكشاف): ROOT-ECHO؛ النواة OPEN-CANDIDATE.
- سطر النسخ: السابق root=OPEN-CANDIDATE؛ الجديد ROOT-ECHO؛ السبب: قُرئ المجاز العضوي مع أسرة الأنف، مع إبقاء فقد النون مانعًا من TRACE والنواة.

### بطاقة: `אתא`، العضو `kaikki_aramaic:819:en-אתא-arc-verb-NxJ~s~mm`
- أصل المرشح: طابور المسار 2، اقتراح ميليتاريف `SEM 1439` وكلاين 1987؛ الحاشية: «اشتقاقات شتى من الأصل *ʔVt- باستعمال w وy وʔ صامتًا ثالثًا».
- كلمة الفرع: `אתא` ʾaṯā، verb، «to come, to arrive» [Kaikki Aramaic]. صوامت العضو كاملة `ʔ-t-ʔ`؛ والمقارنات المنشورة تعرض `ʔ-t-w` و`ʔ-t-y`، فلا يُمحى الضعيف الثالث.
- الزوج الخارجي `ʔ-t` من الموضعين 1 و2؛ الثالث ضعيف مختلف ومعلل في حاشية المصدر، لكنه لا يكفي لإصدار مدخل نووي غير موجود في الفهرس المجمد.
- حكم طبقة الجذر: ROOT-ECHO؛ `אתא ↔ أتى` في المجيء مع اختلاف الضعيف الثالث. حكم طبقة النواة: OPEN-CANDIDATE.
- مسح العربية: لسان العرب لابن منظور: «أَتَيْتُه أَتْياً وإِتْياناً: جِئْتُه»؛ تاج العروس لمرتضى الزبيدي: «حقيقةُ الإِتيانِ المَجيءُ بسهولة» و«الإِتيانُ يُقال للمجيء بالذات».
- الجسر الدلالي الصريح: المجيء والوصول هما معنى الفعل في الطرفين؛ الصدى من مادة الإتيان نفسها، لا من مادة عربية أخرى.
- المصفاة الاتجاهية: لا مانح مسمى؛ الحاشية شهادة صرفية معتبرة، لكنها لا تنشئ نواة `أت` خارج الفهرس، ولا يُستبدل بها `ءث` ذي المدار المخالف.
- الحكم (استكشاف): ROOT-ECHO؛ النواة OPEN-CANDIDATE.
- سطر النسخ: السابق root=TOOL-GAP؛ الجديد ROOT-ECHO؛ السبب: فُتح الصدى المعجمي مع حفظ الضعيف الثالث. حكم النواة OPEN-CANDIDATE محفوظ، وسطر نسخه الأقدم من الموجب إلى المفتوح محفوظ في سجل التغطية.

### بطاقة: `יומא`، العضو `kaikki_aramaic:188:en-יומא-arc-noun-lEwn5bl6`
- أصل المرشح: طابور المسار 2، اقتراح ميليتاريف `SEM 792` وكلاين 1987؛ حاشية ميليتاريف: «مبني على ثنائي *yam-؟».
- كلمة الفرع: `יומא` yōmā، noun، «day» [Kaikki Aramaic]. بعد تعرية ألف الحالة يبقى الجذر كاملًا `y-w-m`، ومصدر العضو يعيده إلى `*yawm-`.
- الزوج المقترح `y-m` من الموضعين 1 و3؛ الواو في الموضع 2 أصل في الصورة المنشورة، والحاشية استفهامية لا تسميها توسعة ثانوية.
- حكم طبقة الجذر: ROOT-TRACE؛ `y-w-m ↔ ي-w-m`. حكم طبقة النواة: OPEN-CANDIDATE.
- مسح العربية: لسان العرب لابن منظور: «اليَوْمُ: معروفٌ مِقدارُه من طلوع الشمس إِلى غروبها»؛ تاج العروس لمرتضى الزبيدي: «اليَوْمُ: معروفٌ، مِقْدَارُهُ مِنْ طُلُوعِ الشَّمْسِ إِلَى غُرُوبِهَا».
- الجسر الدلالي الصريح: الطرفان يسميان اليوم المعروف والمدة النهارية؛ الصورة والمعنى من `يوم` كاملة.
- المصفاة الاتجاهية: لا مانح مسمى؛ لم تُسو حاشية السؤال بحاشية `קום` الجازمة بالتوسعة الثانوية.
- الحكم (استكشاف): ROOT-TRACE؛ النواة OPEN-CANDIDATE.
- سطر النسخ: السابق root=OPEN-CANDIDATE؛ الجديد ROOT-TRACE؛ السبب: عُريت ألف الحالة واكتملت مروحة `يوم`. بقيت النواة مفتوحة لحفظ الواو.

<!-- PATH2-PRIORITY-QUEUE:ARAMAIC-005-NONBASIC:END -->
'''


def atomic_write(path: Path, text: str) -> None:
    descriptor, name = tempfile.mkstemp(prefix=path.name + ".", dir=path.parent)
    os.close(descriptor)
    temporary = Path(name)
    try:
        temporary.write_text(unicodedata.normalize("NFC", text), encoding="utf-8", newline="\n")
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def supersede(row: dict[str, Any], layer: str, old: str, new: str, reason: str) -> None:
    language = "hebrew" if row["member_id"].startswith("kaikki_hebrew:") else "aramaic"
    evidence = f"04-cross-linguistic/readings/{language}.md#path2-priority-queue-{language}-005-nonbasic"
    record = {
        "schema": "lane-a-judgment-supersession-v1",
        "date": DATE,
        "member_id": row["member_id"],
        "layer": layer,
        "previous_outcome": old,
        "new_outcome": new,
        "reason": reason,
        "evidence": evidence,
    }
    history = row.setdefault("judgment_supersessions", [])
    if not any(item.get("layer") == layer and item.get("evidence") == evidence for item in history):
        history.append(record)


def main() -> int:
    rows = [json.loads(line) for line in COVERAGE.read_text(encoding="utf-8").splitlines() if line.strip()]
    indexed = {row["member_id"]: row for row in rows}
    missing = sorted(set(CHANGES) - set(indexed))
    if missing:
        raise RuntimeError(f"coverage members missing: {missing}")

    for member_id, layers in CHANGES.items():
        row = indexed[member_id]
        for layer, (outcome, issued, basis) in layers.items():
            target = row[f"{layer}_layer"]
            previous = str(target.get("outcome"))
            if previous != outcome:
                supersede(row, layer, previous, outcome, basis)
            target["outcome"] = outcome
            target["issued"] = issued
            target["basis"] = basis
            if layer == "nucleus":
                target.pop("selected", None)
        row["batch_number"] = BATCH

    atomic_write(COVERAGE, "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n")

    hebrew_text = HEBREW.read_text(encoding="utf-8")
    if HEBREW_MARKER not in hebrew_text:
        atomic_write(HEBREW, hebrew_text.rstrip() + "\n" + HEBREW_CARDS.lstrip("\n"))

    aramaic_text = ARAMAIC.read_text(encoding="utf-8")
    if ARAMAIC_MARKER not in aramaic_text:
        atomic_write(ARAMAIC, aramaic_text.rstrip() + "\n" + ARAMAIC_CARDS.lstrip("\n"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
