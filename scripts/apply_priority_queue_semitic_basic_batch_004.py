#!/usr/bin/env python3
"""Apply the basic Hebrew/Aramaic rows remaining in the path-2 queue."""

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
BATCH = "priority-queue-semitic-004-basic"
HEBREW_MARKER = "<!-- PATH2-PRIORITY-QUEUE:HEBREW-004-BASIC:BEGIN -->"
ARAMAIC_MARKER = "<!-- PATH2-PRIORITY-QUEUE:ARAMAIC-004-BASIC:BEGIN -->"


Layer = tuple[str, bool, str, dict[str, Any] | None]


TOOTH_SELECTED = {
    "nucleus": "سن",
    "reading_ar": "الامتداد أو النفاذ مع حدة أو دقة",
    "status": "licensed",
    "positions": ["1-2"],
    "rule_ids": ["SIB-01"],
    "route_required": False,
    "arabic_root_witness": "سنن",
    "old_arabic_sources": ["كتاب العين للخليل بن أحمد", "لسان العرب لابن منظور"],
    "omitted_branch_consonant": "none",
    "omission_basis": "The two distinct consonants are sh-n; historical doubling is gemination, not an omitted third radical.",
}


CHANGES: dict[str, dict[str, Layer]] = {
    "kaikki_hebrew:2093:en-כוכב-he-noun-Ul7KHVCJ": {
        "root": ("ROOT-TRACE", True, "כוכב وكوكب انعكاسان للاسم السامي الموروث *kabkab- في معنى النجم؛ لم يُختزل الرباعي إلى نواة.", None),
        "nucleus": ("OPEN-CANDIDATE", False, "تحليل التضعيف الخارجي لا يكفي لإصدار k-b؛ لا مدار عربي مجمد مستقل للنجم.", None),
    },
    "kaikki_hebrew:5224:en-ליל-he-noun-F2Rz1zEz": {
        "root": ("ROOT-TRACE", True, "الجذع l-y-l يقابل ل-ي-ل كاملًا في الليل.", None),
        "nucleus": ("OPEN-CANDIDATE", False, "اللام الثالثة أصل في الجذع المستعمل؛ وصف Klein للتضعيف لا يرخص حذفها دون مدار مستقل.", None),
    },
    "kaikki_hebrew:2054:en-שן-he-noun-lyLUpLWc": {
        "root": ("ROOT-TRACE", True, "שן من *šinn- يقابل سنّ من s-n-n بتقابل SIB-01 وبحفظ التضعيف التاريخي.", None),
        "nucleus": ("NUCLEUS-TRACE", True, "الصامتان المتميزان sh-n كاملان، والتضعيف ليس صامتًا أصليًا ثالثًا مسقطًا؛ معنى السن يحقق الحدة والنفاذ.", TOOTH_SELECTED),
    },
    "kaikki_hebrew:903:en-אדמה-he-noun-dgbnW57Y": {
        "root": ("ROOT-TRACE", True, "بعد تعرية -ā يبقى ʔ-d-m، ويقابل أ-د-م في أديم الأرض ووجهها.", None),
        "nucleus": ("OPEN-CANDIDATE", False, "الهمزة صامت أصلي في الجذر المقارن؛ لا يجوز إسقاطها لإصدار دم من معنى الأرض.", None),
    },
    "kaikki_hebrew:397:en-בת-he-noun-TtKPgsqW": {
        "root": ("ROOT-TRACE", True, "الاسم يرجع إلى *bint- ويقابل بنت؛ النون مدغمة في التاء العبرية لا محذوفة من التحليل.", None),
        "nucleus": ("OPEN-CANDIDATE", False, "الخلاف في تاريخ التاء والنون يمنع تحويل بنت إلى نواة b-t أو b-n بلا إسقاط أصل.", None),
    },
    "kaikki_hebrew:389:en-אב-he-noun-hYTLhfxL": {
        "root": ("ROOT-TRACE", True, "العضو אב نفسه موروث من *ʔabw- ويقابل أب/أبو؛ فُصل عن الصورة אבא ذات مسار الاقتراض الداخلي.", None),
        "nucleus": ("OPEN-CANDIDATE", False, "الواو التاريخية ظاهرة في أبو والتثنية؛ لا تختزل المادة إلى ʔ-b كنواة بلا مدار مستقل.", None),
    },
    "kaikki_hebrew:399:en-שמש-he-noun-J3VvBQ4U": {
        "root": ("ROOT-TRACE", True, "الجذر sh-m-sh يقابل ش-م-س كاملًا في اسم الشمس بتقابل الشين النهائية والسين.", None),
        "nucleus": ("OPEN-CANDIDATE", False, "الصامت الثالث أصلي؛ ربط الشمس بمدار شم في جمع المنتشر إلى أعلى جسر مصنوع لا يسوغ الحذف.", None),
    },
    "kaikki_aramaic:415:en-כוכבא-arc-noun-1oSi-LD1": {
        "root": ("ROOT-TRACE", True, "بعد تعرية ألف الحالة يبقى انعكاس *kabkab-، ويقابل كوكب في النجم الموروث دون اختزال نووي.", None),
        "nucleus": ("OPEN-CANDIDATE", False, "رد الاسم المضعف إلى قاعدة ثنائية اقتراح خارجي لا يثبت مدارًا عربيًا مستقلًا للنجم.", None),
    },
    "kaikki_aramaic:473:en-ליליא-arc-noun-F2Rz1zEz": {
        "root": ("ROOT-TRACE", True, "بعد تعرية -yā يبقى l-y-l، ويقابل ل-ي-ل كاملًا في الليل.", None),
        "nucleus": ("OPEN-CANDIDATE", False, "اللام الثالثة أصل في الجذع؛ لا تسقط إلى li لمجرد وصف البنية بالمضعفة.", None),
    },
    "kaikki_aramaic:161:en-שנא-arc-noun-lyLUpLWc": {
        "root": ("ROOT-TRACE", True, "بعد تعرية ألف الحالة يبقى š-n(n)، ويقابل س-ن-ن في السن بتقابل SIB-01.", None),
        "nucleus": ("NUCLEUS-TRACE", True, "الصامتان المتميزان sh-n كاملان، والتضعيف ليس ثالثًا مسقطًا؛ السن تحقق الحدة والنفاذ.", TOOTH_SELECTED),
    },
    "kaikki_aramaic:1862:en-אדמתא-arc-noun-W78vbzp-": {
        "root": ("ROOT-TRACE", True, "بعد تعرية -tā يبقى ʔ-d-m، ويقابل أ-د-م في أديم الأرض ووجهها.", None),
        "nucleus": ("OPEN-CANDIDATE", False, "الهمزة أصل في الجذر الكامل؛ الحكم القديم دم أسقطها بلا سابقة صرفية.", None),
    },
    "kaikki_aramaic:162:en-שמשא-arc-noun-J3VvBQ4U": {
        "root": ("ROOT-TRACE", True, "بعد تعرية ألف الحالة يبقى sh-m-sh، ويقابل ش-م-س كاملًا في الشمس.", None),
        "nucleus": ("OPEN-CANDIDATE", False, "الشين الثالثة أصل؛ لا مدار مستقل يجيز إسقاطها إلى شم.", None),
    },
    "kaikki_aramaic:328:en-אחא-arc-noun-C0vXfOxw": {
        "root": ("ROOT-TRACE", True, "بعد تعرية ألف الحالة واستعادة الضعيف يبقى *ʔ-ḥ-w، ويقابل أ-خ-و كاملًا في الأخ.", None),
        "nucleus": ("LAW-GAP", False, "تقابل ḥ/ḫ في هذا المسار ليس قانونًا نوويًا نافذًا، والواو الأصلية لا تسقط؛ لا تعديل للقانون.", None),
    },
    "kaikki_aramaic:357:en-אמא-arc-noun-zwYi7ypm": {
        "root": ("ROOT-TRACE", True, "بعد تعرية ألف الحالة يبقى *ʔ-m(m)، ويقابل أمّ مع حفظ التضعيف.", None),
        "nucleus": ("OPEN-CANDIDATE", False, "الصورة ثنائية مضعفة، لكن مدار ءم المجمد لا يحمل الأمومة؛ لا حكم من اقتراح القاعدة وحده.", None),
    },
}


HEBREW_CARDS = r'''

<!-- PATH2-PRIORITY-QUEUE:HEBREW-004-BASIC:BEGIN -->

## طابور المسار الثاني — بقية الأساسي العبري (2026-08-01)

### بطاقة: `כוכב`، العضو `kaikki_hebrew:2093:en-כוכב-he-noun-Ul7KHVCJ`
- أصل المرشح: طابور المسار 2، اقتراح كلاين 1987 في مادة `כוכב`، من صفوف `leads-semitic-sisters.md`.
- كلمة الفرع: `כוכב` kokháv، noun، «star» [Kaikki Hebrew]. الصورة التاريخية الكاملة التي يسندها مصدر العضو `*kabkab-`؛ الواو في الرسم حامل حركة في هذا الموضع، ولم تُنزع بحدس صرفي.
- جذر الفرع بصوامته كاملة بعد التعرية: البنية التاريخية المضعفة `k-b-k-b`؛ لم يؤخذ منها زوج، ولم يسقط الثالث أو الرابع.
- حكم طبقة الجذر: ROOT-TRACE للاسم الموروث `כוכב ↔ كوكب`. حكم طبقة النواة: OPEN-CANDIDATE؛ لا تصدر `kb`.
- مسح العربية: كتاب العين للخليل بن أحمد: «الكوْكبُ النجم»؛ لسان العرب لابن منظور: «الكَوْكَبُ، معروف، من كَواكِبِ السماءِ».
- الجسر الدلالي الصريح: الكوكب هو النجم السماوي نفسه الذي يسميه العضو العبري؛ هذا جسر الاسم الكامل، لا جسر نواة عامة.
- المصفاة الاتجاهية: مصدر العضو يعيده إلى السامية ولا يسمي مانحًا؛ موافقة كلاين ليست حكمًا.
- الحكم (استكشاف): ROOT-TRACE؛ النواة OPEN-CANDIDATE.
- سطر النسخ: السابق root=OPEN-CANDIDATE؛ الجديد ROOT-TRACE؛ السبب: اكتملت قراءة الصورة التاريخية ومروحة الاسم الكامل. بقيت النواة مفتوحة.

### بطاقة: `ליל`، العضو `kaikki_hebrew:5224:en-ליל-he-noun-F2Rz1zEz`
- أصل المرشح: طابور المسار 2، اقتراح كلاين 1987 في مادة `ליל`، من صفوف `leads-semitic-sisters.md`.
- كلمة الفرع: `ליל` léyl، noun، «night» [Kaikki Hebrew]. جذر الفرع كاملًا بعد التعرية `l-y-l`؛ لا سابقة ولا لاحقة.
- الصامتان اللذان يلمح إليهما تحليل التضعيف الخارجي `l-y` من الموضعين 1 و2؛ اللام الثالثة في الموضع 3 أصل في الجذع المستعمل، ولا نص صرفيًا يسقطها.
- حكم طبقة الجذر: ROOT-TRACE؛ `l-y-l ↔ ل-y-l`. حكم طبقة النواة: OPEN-CANDIDATE.
- مسح العربية: لسان العرب لابن منظور: «اللَّيْلُ: عقيب النهار ومَبْدَؤُه من غروب الشمس»؛ تاج العروس لمرتضى الزبيدي: «اللَّيْلُ: ضِدُّ النهارِ معروفٌ».
- الجسر الدلالي الصريح: الطرفان يسميان الزمن المقابل للنهار من غروب الشمس؛ التطابق في المادة الثلاثية الكاملة.
- المصفاة الاتجاهية: لا مانح مسمى؛ موافقة كلاين ليست حكمًا، ووصفه للبنية لا يبيح حذف اللام.
- الحكم محفوظ: ROOT-TRACE؛ النواة OPEN-CANDIDATE؛ لا سطر نسخ لأن الحكمين لم يتغيرا.

### بطاقة: `שן`، العضو `kaikki_hebrew:2054:en-שן-he-noun-lyLUpLWc`
- أصل المرشح: طابور المسار 2، اقتراح ميليتاريف `SEM 131` وكلاين 1987 و`HSED 2250`، من صفوف `leads-semitic-sisters.md`.
- كلمة الفرع: `שן` shen، noun، «tooth» [Kaikki Hebrew]. جذر الفرع كاملًا `š-n(n)` من `*šinn-`؛ التضعيف صفة للصامت الثاني، لا صامت ثالث مستقل.
- الصامتان المأخوذان `š-n` في الموضعين 1 و2؛ لم يسقط أصل، وقاعدة الصوت `SIB-01` تسوي `š ↔ s`.
- حكم طبقة الجذر: ROOT-TRACE؛ `*šinn- ↔ سنّ`. حكم طبقة النواة: NUCLEUS-TRACE؛ `سن` «الامتداد أو النفاذ مع حدة أو دقة».
- مسح العربية: كتاب العين للخليل بن أحمد: «السِّنُّ واحدةُ الأَسنان» و«المِسَنُّ الحَجَرُ الذي يُسَنُّ عليه السِّكِّينُ أي يُحَدَّدُ»؛ لسان العرب لابن منظور: «الضِّرْسُ: السِّنُّ».
- الجسر الدلالي الصريح: السن جسم ممتد حاد ينفذ في الطعام، وسن السكين تحديده؛ فالعضو ومدار الحدة والنفاذ من مادة واحدة.
- المصفاة الاتجاهية: لا مانح مسمى؛ الاقتراحات الثلاثة نَسَبٌ للمرشح لا بدل من القراءة.
- الحكم (استكشاف): ROOT-TRACE وNUCLEUS-TRACE.
- سطر النسخ: السابق root=ROOT-ECHO؛ الجديد ROOT-TRACE؛ السبب: التقابل `š/s` مرخص والمادة المضعفة كاملة. النواة محفوظة بعد إثبات عدم سقوط ثالث.

### بطاقة: `אדמה`، العضو `kaikki_hebrew:903:en-אדמה-he-noun-dgbnW57Y`
- أصل المرشح: طابور المسار 2، اقتراح Orel وStolbova، `HSED 16`، من صفوف `leads-semitic-sisters.md`.
- كلمة الفرع: `אדמה` adamá، noun، «soil, ground, earth» [Kaikki Hebrew]. بعد تعرية نهاية الاسم `-ā` يبقى الجذر كاملًا `ʔ-d-m`.
- الزوج الذي اقترحه الخارج `d-m` من الموضعين 2 و3؛ الهمزة في الموضع الأول أصل في الجذر المقارن، لا سابقة صرفية، ولذلك لا تسقط.
- حكم طبقة الجذر: ROOT-TRACE؛ `ʔ-d-m ↔ أ-d-m` في أديم الأرض. حكم طبقة النواة: OPEN-CANDIDATE؛ رُفض `dm`.
- مسح العربية: كتاب العين للخليل بن أحمد: «أديمُ كُلِّ شيءٍ ظاهرُ جلدِه» و«أَدَمَة الأرض وَجهُها»؛ تاج اللغة وصحاح العربية للجوهري: «وربما سمى وجهُ الأرض أديماً».
- الجسر الدلالي الصريح: أديم الأرض وأدمتها وجهها الظاهر، وهو التربة أو سطح الأرض الذي تسميه العبرية؛ الصورة والمعنى من `أدم` نفسها.
- المصفاة الاتجاهية: لا مانح مسمى؛ موافقة HSED ليست حكمًا، والهمزة الأصلية تمنع النواة المقترحة.
- الحكم (استكشاف): ROOT-TRACE؛ النواة OPEN-CANDIDATE.
- سطر النسخ: السابق root=MORPHOLOGY-GAP وnucleus=MORPHOLOGY-GAP؛ الجديد ROOT-TRACE وOPEN-CANDIDATE؛ السبب: عُريت نهاية الاسم، ثم حُفظت الهمزة الأصلية بدل إسقاطها.

### بطاقة: `בת`، العضو `kaikki_hebrew:397:en-בת-he-noun-TtKPgsqW`
- أصل المرشح: طابور المسار 2، اقتراح كلاين 1987 في مادة `בת`، من صفوف `leads-semitic-sisters.md`.
- كلمة الفرع: `בת` bat، noun، «daughter» [Kaikki Hebrew]. جذر الاسم التاريخي كاملًا `b-n-t` من `*bint-`؛ النون مدغمة في التاء العبرية، وليست محذوفة من التحليل.
- لا زوج نووي صادر: أخذ `b-t` يسقط النون الأصلية، وأخذ `b-n` يتجاوز التاء قبل حسم تاريخها بين اللغتين.
- حكم طبقة الجذر: ROOT-TRACE؛ `*bint- ↔ بنت`. حكم طبقة النواة: OPEN-CANDIDATE.
- مسح العربية: لسان العرب لابن منظور: «والأُنثى ابنة وبنتٌ» و«ولامِ بِنْت واو، والتاء بدل منها»؛ كتاب العين للخليل بن أحمد: «هي ابنةُ فلانٍ وهي بِنْتُهُ».
- الجسر الدلالي الصريح: الطرفان اسما الأنثى من الولد؛ الحكم للاسم التاريخي الكامل، لا لزوج منتقى من خلاف صرفي.
- المصفاة الاتجاهية: لا مانح مسمى؛ قول كلاين إن التاء علامة تأنيث لا يُورث حكمًا، وشاهد العربية نفسه يحفظ تحليلًا آخر.
- الحكم محفوظ: ROOT-TRACE؛ النواة OPEN-CANDIDATE؛ لا سطر نسخ لأن الحكمين لم يتغيرا.

### بطاقة: `אב`، العضو `kaikki_hebrew:389:en-אב-he-noun-hYTLhfxL`
- أصل المرشح: طابور المسار 2، اقتراح ميليتاريف `SEM 1`، من صفوف `leads-semitic-sisters.md`.
- كلمة الفرع: `אב` av، noun، «father» [Kaikki Hebrew]. الجذر التاريخي كاملًا `ʔ-b-w` من `*ʔabw-`؛ الضعيف يظهر في العربية `أبو` وفي تصريفات الاسم.
- لا زوج نووي صادر: `ʔ-b` موضعاه 1 و2، لكن الواو التاريخية في الموضع 3 أصل وليست لاحقة تسقط.
- حكم طبقة الجذر: ROOT-TRACE للعضو `אב` نفسه. حكم طبقة النواة: OPEN-CANDIDATE.
- مسح العربية: كتاب العين للخليل بن أحمد: «أَبَوْتُ الرّجلَ آبوه إذا كنتُ له أباً» و«يأبُو هذا اليتيم إباوةً أي يغذوه كما يغذو الوالد ولده»؛ القاموس المحيط للفيروزآبادي: «والأَبُ مَعْرُوفٌ» و«يَأْبُوْ اليَتِيْمَ إبَاوَةً أي يَغْذُوه».
- الجسر الدلالي الصريح: الأب هو الوالد القائم بغذاء ولده في الطرفين؛ مادة `أبو` نفسها تحفظ الاسم وفعل القيام مقام الأب.
- المصفاة الاتجاهية: فُصل `אב` الموروث عن الدوبليت `אבא` الذي تذكر له المصادر انتقالًا آراميًا؛ لا يُنقل حكم عضو إلى عضو.
- الحكم (استكشاف): ROOT-TRACE؛ النواة OPEN-CANDIDATE.
- سطر النسخ: السابق root=OPEN-CANDIDATE؛ الجديد ROOT-TRACE؛ السبب: زال خلط العضو الموروث بالدوبليت المقترض واكتملت مروحة `أبو`. بقيت النواة مفتوحة لحفظ الواو.

### بطاقة: `שמש`، العضو `kaikki_hebrew:399:en-שמש-he-noun-J3VvBQ4U`
- أصل المرشح: طابور المسار 2، اقتراح ميليتاريف `SEM 1489`، من صفوف `leads-semitic-sisters.md`.
- كلمة الفرع: `שמש` shémesh، noun، «sun» [Kaikki Hebrew]. جذر الفرع كاملًا `sh-m-sh`؛ لا سابقة ولا لاحقة.
- الزوج القديم `sh-m` من الموضعين 1 و2؛ الشين الثالثة في الموضع 3 أصل، ولا تعرية صرفية تسوغ إسقاطها.
- حكم طبقة الجذر: ROOT-TRACE؛ `sh-m-sh ↔ ش-m-s` كاملًا. حكم طبقة النواة: OPEN-CANDIDATE.
- مسح العربية: لسان العرب لابن منظور: «الشمس معروفة»؛ تاج العروس لمرتضى الزبيدي: «الشَّمْسُ... معروفَةٌ» و«الشَّمْسُ عَيْنٌ الضَّحِّ».
- الجسر الدلالي الصريح: الطرفان يسميان الجرم المضيء المعروف نفسه؛ هذا تطابق اسم كامل، ولا يلزم منه أن الشمس «جمع منتشر إلى أعلى».
- المصفاة الاتجاهية: لا مانح مسمى؛ تحليل ميليتاريف للتضعيف يبقى اقتراحًا، ولا يحذف الصامت الثالث من هذا العضو.
- الحكم (استكشاف): ROOT-TRACE؛ النواة OPEN-CANDIDATE.
- سطر النسخ: السابق nucleus=NUCLEUS-TRACE (`شم`)؛ الجديد nucleus=OPEN-CANDIDATE؛ السبب: الشين الثالثة أصل، والجسر النووي القديم مصنوع. حكم الجذر محفوظ.

<!-- PATH2-PRIORITY-QUEUE:HEBREW-004-BASIC:END -->
'''


ARAMAIC_CARDS = r'''

<!-- PATH2-PRIORITY-QUEUE:ARAMAIC-004-BASIC:BEGIN -->

## طابور المسار الثاني — الأساسي الآرامي والسرياني (2026-08-01)

### بطاقة: `כוכבא`، العضو `kaikki_aramaic:415:en-כוכבא-arc-noun-1oSi-LD1`
- أصل المرشح: طابور المسار 2، اقتراح كلاين 1987 في مادة `כוכב`، من صفوف `leads-semitic-sisters.md`.
- كلمة الفرع: `כוכבא` kawkbā، noun، «star (celestial body)» [Kaikki Aramaic]. بعد تعرية ألف الحالة يبقى انعكاس البنية التاريخية الكاملة `*k-b-k-b`؛ لم يُنتق زوج ولم يسقط ثالث أو رابع.
- حكم طبقة الجذر: ROOT-TRACE للاسم الموروث `כוכבא ↔ كوكب`. حكم طبقة النواة: OPEN-CANDIDATE؛ لا تصدر `kb`.
- مسح العربية: كتاب العين للخليل بن أحمد: «الكوْكبُ النجم»؛ لسان العرب لابن منظور: «الكَوْكَبُ، معروف، من كَواكِبِ السماءِ».
- الجسر الدلالي الصريح: الطرفان يسميان الجرم السماوي النجم نفسه؛ التطابق للاسم الكامل لا لمدار ثنائي مفترض.
- المصفاة الاتجاهية: المصدر يعيد العضو إلى `*kabkab-` ولا يسمي مانحًا؛ موافقة كلاين ليست حكمًا.
- الحكم محفوظ: ROOT-TRACE؛ النواة OPEN-CANDIDATE؛ لا سطر نسخ لأن الحكمين لم يتغيرا.

### بطاقة: `ליליא`، العضو `kaikki_aramaic:473:en-ליליא-arc-noun-F2Rz1zEz`
- أصل المرشح: طابور المسار 2، اقتراح كلاين 1987 في مادة `ליל`، من صفوف `leads-semitic-sisters.md`.
- كلمة الفرع: `ליליא` lēlyā، noun، «night» [Kaikki Aramaic]. بعد تعرية `-yā` يبقى الجذر كاملًا `l-y-l`.
- الزوج القديم `l-y` من الموضعين 1 و2؛ اللام الثالثة في الموضع 3 أصل ولا تسقط بوصف التضعيف وحده.
- حكم طبقة الجذر: ROOT-TRACE؛ `l-y-l ↔ ل-y-l`. حكم طبقة النواة: OPEN-CANDIDATE.
- مسح العربية: لسان العرب لابن منظور: «اللَّيْلُ: عقيب النهار ومَبْدَؤُه من غروب الشمس»؛ تاج العروس لمرتضى الزبيدي: «اللَّيْلُ: ضِدُّ النهارِ معروفٌ».
- الجسر الدلالي الصريح: الطرفان يسميان الزمن المقابل للنهار؛ الصلة في `ليل` كاملًا لا في زوج أسقط لامه.
- المصفاة الاتجاهية: لا مانح مسمى؛ موافقة كلاين ليست حكمًا.
- الحكم (استكشاف): ROOT-TRACE؛ النواة OPEN-CANDIDATE.
- سطر النسخ: السابق nucleus=NUCLEUS-TRACE (`لي`)؛ الجديد nucleus=OPEN-CANDIDATE؛ السبب: اللام الثالثة أصل، ولم يثبت مدار ثنائي مستقل. حكم الجذر محفوظ.

### بطاقة: `שנא`، العضو `kaikki_aramaic:161:en-שנא-arc-noun-lyLUpLWc`
- أصل المرشح: طابور المسار 2، اقتراح ميليتاريف `SEM 131` وكلاين 1987 و`HSED 2250`، من صفوف `leads-semitic-sisters.md`.
- كلمة الفرع: `שנא` shennā، noun، «tooth» [Kaikki Aramaic]. بعد تعرية ألف الحالة يبقى الجذر كاملًا `š-n(n)`؛ التضعيف ليس صامتًا ثالثًا مستقلًا.
- الصامتان المأخوذان `š-n` في الموضعين 1 و2؛ لم يسقط أصل، والمسار `SIB-01` يسوي `š ↔ s`.
- حكم طبقة الجذر: ROOT-TRACE؛ `š-n(n) ↔ س-n-n`. حكم طبقة النواة: NUCLEUS-TRACE؛ `سن` «الامتداد أو النفاذ مع حدة أو دقة».
- مسح العربية: كتاب العين للخليل بن أحمد: «السِّنُّ واحدةُ الأَسنان» و«المِسَنُّ الحَجَرُ الذي يُسَنُّ عليه السِّكِّينُ أي يُحَدَّدُ»؛ لسان العرب لابن منظور: «الضِّرْسُ: السِّنُّ».
- الجسر الدلالي الصريح: السن جسم ممتد حاد ينفذ في الطعام، وسن السكين تحديده؛ الصورة والمعنى من المادة نفسها.
- المصفاة الاتجاهية: لا مانح مسمى؛ موافقة المقترحين ليست حكمًا.
- الحكم (استكشاف): ROOT-TRACE وNUCLEUS-TRACE.
- سطر النسخ: السابق root=OPEN-CANDIDATE وnucleus=OPEN-CANDIDATE؛ الجديد ROOT-TRACE وNUCLEUS-TRACE؛ السبب: عُريت ألف الحالة وثبت أن التضعيف لا يمثل ثالثًا مسقطًا.

### بطاقة: `אדמתא`، العضو `kaikki_aramaic:1862:en-אדמתא-arc-noun-W78vbzp-`
- أصل المرشح: طابور المسار 2، اقتراح Orel وStolbova، `HSED 16`، من صفوف `leads-semitic-sisters.md`.
- كلمة الفرع: `אדמתא` admatā، noun، «the ground» [Kaikki Aramaic]. بعد تعرية لاحقة الحالة `-tā` يبقى الجذر كاملًا `ʔ-d-m`.
- الزوج القديم `d-m` من الموضعين الجذريين 2 و3؛ الهمزة في الموضع 1 أصل قاطع لا سابقة، فلا تسقط.
- حكم طبقة الجذر: ROOT-TRACE؛ `ʔ-d-m ↔ أ-d-m`. حكم طبقة النواة: OPEN-CANDIDATE؛ رُفض `دم`.
- مسح العربية: كتاب العين للخليل بن أحمد: «أديمُ كُلِّ شيءٍ ظاهرُ جلدِه» و«أَدَمَة الأرض وَجهُها»؛ تاج اللغة وصحاح العربية للجوهري: «وربما سمى وجهُ الأرض أديماً».
- الجسر الدلالي الصريح: أديم الأرض وجهها الظاهر، وهو الأرض التي يسميها العضو الآرامي؛ مادة `أدم` تحمل الصورة والمعنى معًا.
- المصفاة الاتجاهية: لا مانح مسمى؛ موافقة HSED ليست حكمًا.
- الحكم (استكشاف): ROOT-TRACE؛ النواة OPEN-CANDIDATE.
- سطر النسخ: السابق root=OPEN-CANDIDATE وnucleus=NUCLEUS-TRACE (`دم`)؛ الجديد ROOT-TRACE وOPEN-CANDIDATE؛ السبب: رُدت الهمزة الأصلية واستُعمل الجذر الكامل بدل الزوج المنتقى.

### بطاقة: `שמשא`، العضو `kaikki_aramaic:162:en-שמשא-arc-noun-J3VvBQ4U`
- أصل المرشح: طابور المسار 2، اقتراح ميليتاريف `SEM 1489`، من صفوف `leads-semitic-sisters.md`.
- كلمة الفرع: `שמשא` shimshā، noun، «sun» [Kaikki Aramaic]. بعد تعرية ألف الحالة يبقى الجذر كاملًا `sh-m-sh`؛ الصوامت الثلاثة أصول.
- الزوج الخارجي `sh-m` من الموضعين 1 و2؛ الشين الثالثة في الموضع 3 أصل، ولا تسقط.
- حكم طبقة الجذر: ROOT-TRACE؛ `sh-m-sh ↔ ش-m-s`. حكم طبقة النواة: OPEN-CANDIDATE.
- مسح العربية: لسان العرب لابن منظور: «الشمس معروفة»؛ تاج العروس لمرتضى الزبيدي: «الشَّمْسُ... معروفَةٌ» و«الشَّمْسُ عَيْنٌ الضَّحِّ».
- الجسر الدلالي الصريح: الاسم الآرامي والعربي للجرم المضيء نفسه؛ التطابق في الجذر الكامل، ولا حاجة إلى مدار `شم` مصنوع.
- المصفاة الاتجاهية: لا مانح مسمى؛ موافقة ميليتاريف ليست حكمًا.
- الحكم (استكشاف): ROOT-TRACE؛ النواة OPEN-CANDIDATE.
- سطر النسخ: السابق root=OPEN-CANDIDATE؛ الجديد ROOT-TRACE؛ السبب: اكتملت مروحة `شمس` والتعرية. بقيت النواة مفتوحة لوجود الثالث الأصلي.

### بطاقة: `אחא`، العضو `kaikki_aramaic:328:en-אחא-arc-noun-C0vXfOxw`
- أصل المرشح: طابور المسار 2، اقتراح del Olmo Lete بقاعدة `/ʔ-ḫ/` للأخ والأخت، من صفوف `leads-semitic-sisters.md`.
- كلمة الفرع: `אחא` aḥā، noun، «brother» [Kaikki Aramaic]. بعد تعرية ألف الحالة واستعادة الضعيف المنشور يبقى الجذر كاملًا `*ʔ-ḥ-w`.
- الزوج المقترح `ʔ-ḥ` من الموضعين 1 و2؛ الواو التاريخية في الموضع 3 أصل. كما أن صف `ḥ/ḫ` ليس قانونًا نوويًا نافذًا هنا.
- حكم طبقة الجذر: ROOT-TRACE؛ `*ʔ-ḥ-w ↔ أ-خ-و`. حكم طبقة النواة: LAW-GAP؛ لا تعديل للقانون ولا حكم موجب.
- مسح العربية: تاج العروس لمرتضى الزبيدي: «والأَخُ أَحَدُ الأَسْماءِ السِّتَّةِ» و«أَصْلُه أَخو»؛ تاج اللغة وصحاح العربية للجوهري: «الأَخُ أصله أَخَوٌ بالتحريك» و«الذاهب منه واوٌ».
- الجسر الدلالي الصريح: الطرفان يسميان الذكر المشارك في الوالدين، وصورة `أخو` تحفظ الضعيف الذي تستعيده المقارنة.
- فصل العضو: لفظة الأخت `ḥātā` المذكورة في صف الخارج غير موجودة عضوًا مستقلًا في جردنا؛ سُجلت ENTRY-GAP ولا ترث حكم `אחא`.
- المصفاة الاتجاهية: لا مانح مسمى؛ اقتراح del Olmo Lete لا يفتح صفًا صوتيًا جديدًا.
- الحكم (استكشاف): ROOT-TRACE؛ النواة LAW-GAP.
- سطر النسخ: السابق root=OPEN-CANDIDATE؛ الجديد ROOT-TRACE؛ السبب: اكتملت استعادة `*ʔ-ḥ-w` ومروحة `أخو`. حكم النواة محفوظ LAW-GAP.

### بطاقة: `אמא`، العضو `kaikki_aramaic:357:en-אמא-arc-noun-zwYi7ypm`
- أصل المرشح: طابور المسار 2، اقتراح del Olmo Lete بقاعدة `/ʔ-m/` للأم، من صفوف `leads-semitic-sisters.md`.
- كلمة الفرع: `אמא` immā، noun، «mother» [Kaikki Aramaic]. بعد تعرية ألف الحالة يبقى الجذر كاملًا `*ʔ-m(m)`؛ التضعيف محفوظ، لا ثالث مستقل.
- الصامتان المقترحان `ʔ-m` في الموضعين 1 و2؛ لم يسقط أصل، لكن مجرد ثنائية الصورة لا يثبت المدار النووي.
- حكم طبقة الجذر: ROOT-TRACE؛ `*ʔ-m(m) ↔ أمّ`. حكم طبقة النواة: OPEN-CANDIDATE.
- مسح العربية: لسان العرب لابن منظور: «الأُمّ الوالدة من الحيوان»؛ تاج اللغة وصحاح العربية للجوهري: «الأُمُّ الوالدةُ، والجمع أُمَّاتٌ».
- الجسر الدلالي الصريح: الطرفان يسميان الوالدة نفسها، والتضعيف في `أمّ` يقابل البنية المنشورة للفرع.
- المصفاة الاتجاهية: لا مانح مسمى؛ موافقة del Olmo Lete لا تكفي للنواة، ومدار `ءم` المجمد لا يحمل الأمومة.
- الحكم (استكشاف): ROOT-TRACE؛ النواة OPEN-CANDIDATE.
- سطر النسخ: السابق root=MORPHOLOGY-GAP؛ الجديد ROOT-TRACE؛ السبب: عُريت ألف الحالة بنص صرف الفرع وقورنت الصورة المضعفة كاملة. النواة بقيت مفتوحة.

<!-- PATH2-PRIORITY-QUEUE:ARAMAIC-004-BASIC:END -->
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
    evidence = f"04-cross-linguistic/readings/{language}.md#path2-priority-queue-{language}-004-basic"
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
        for layer, (outcome, issued, basis, selected) in layers.items():
            target = row[f"{layer}_layer"]
            previous = str(target.get("outcome"))
            if previous != outcome:
                supersede(row, layer, previous, outcome, basis)
            target["outcome"] = outcome
            target["issued"] = issued
            target["basis"] = basis
            if layer == "nucleus":
                if selected is None:
                    target.pop("selected", None)
                else:
                    target["selected"] = selected
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
