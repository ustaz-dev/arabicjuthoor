#!/usr/bin/env python3
"""Apply the hand-reviewed Aramaic repairs and Hebrew nucleus-eye batches.

The frozen nucleus index and the recovery SQLite database remain read-only.
Every Hebrew issue is rejected unless its exact member has a licensed, non-route
nucleus candidate and a complete two-work Arabic fan.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sqlite3
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[1]
COVERAGE = REPO / "04-cross-linguistic" / "data" / "lane_a_coverage.jsonl"
HEBREW_READING = REPO / "04-cross-linguistic" / "readings" / "hebrew.md"
ARAMAIC_READING = REPO / "04-cross-linguistic" / "readings" / "aramaic.md"
NUCLEI = REPO / "data" / "juthoor-core-levels.json"
DB = REPO / "cache" / "recovery_pipeline" / "inventory-v5.sqlite"
AUDITS = REPO / "05-audits"


def h(
    line: int,
    nucleus: str,
    witness: str,
    outcome: str,
    branch: str,
    arabic: str,
    realization: str,
) -> dict[str, Any]:
    return {
        "source_line": line,
        "nucleus": nucleus,
        "witness": witness,
        "outcome": outcome,
        "branch": branch,
        "arabic": arabic,
        "realization": realization,
    }


HEBREW_BATCHES: dict[str, list[dict[str, Any]]] = {
    "025": [
        h(425, "بر", "برأ", "NUCLEUS-ECHO", "الإيجاد والخلق وإبراز الموجود", "برأ: خلق وأنشأ، وخلص الشيء من غيره", "تردد التجرد والخلوص حين يبرز المخلوق متميزا عما لم يكن"),
        h(552, "قم", "قوم", "NUCLEUS-TRACE", "المكان والموضع الذي يقوم فيه الشيء", "المقام موضع القيام والاستقرار", "تحقق قيام الشيء وثبوته في حيز مع معنى التسنم والارتفاع"),
        h(591, "نف", "كنف", "NUCLEUS-ECHO", "الجناح الممتد من جانب الطائر", "كنف الشيء ناحيته وستره، وكنفا الطائر جناحاه", "تردد إبعاد الجناح وانتشاره عن الجسد"),
        h(656, "بن", "بني", "NUCLEUS-TRACE", "رفع البناء وإقامة أجزائه", "بنى البناء: رفعه وأقام بعضه على بعض", "تحقق الامتداد والبناء نفسه"),
        h(686, "تل", "تلم", "NUCLEUS-TRACE", "الأخدود والحيد المتتابعان في الأرض", "التلم شق الأرض وما ارتفع بين الأخاديد", "تحقق التكديس والاتباع في توالي الأخدود والحيد"),
        h(894, "سق", "سقي", "NUCLEUS-TRACE", "إعطاء الماء وإدخاله إلى الشارب أو الأرض", "سقى: أعطى الماء وأوصله إلى موضع الشرب", "تحقق نفاذ المائع من جوف الوعاء إلى جوف المتلقي"),
        h(933, "هر", "نهر", "NUCLEUS-TRACE", "جريان الماء وانسيابه", "نهر الماء جرى، والنهر مجرى الماء الواسع", "تحقق التسيب البالغ الرقة في جريان الماء"),
        h(988, "دب", "دبق", "NUCLEUS-ECHO", "اللصوق والتشبث ومنع الانفصال", "الدبق لزج يلصق الشيء ويعوق انفكاكه", "تردد الثقل والضغط والحركة المتباطئة التي يحدثها اللزج"),
        h(991, "عر", "عري", "NUCLEUS-TRACE", "التجرد من اللباس وانكشاف الجسد", "عري من ثوبه: تجرد وانكشف ظاهره", "تحقق نقص الغطاء عن الظاهر وبدو ما كان خافيا"),
        h(1002, "فق", "فقح", "NUCLEUS-TRACE", "فتح العين وإزالة انطباقها", "فقحت العين: انفتحت وانفرجت", "تحقق شق المنطبق إلى العمق ونشوء الفراغ"),
        h(1329, "شب", "شبع", "NUCLEUS-TRACE", "الامتلاء من الطعام وذهاب الجوع", "شبع من الطعام: امتلأ واكتفى", "تحقق تجمع الغذاء بعد انتشاره في حيز الباطن حتى التركز"),
        h(1670, "كر", "كرم", "NUCLEUS-ECHO", "الكرم، أي بستان العنب وشجره", "الكرم شجر العنب، وهو نبات معمر يعاود الإثمار", "تردد التركز مع المعاودة والبقاء الطويل لحصول النفع والثمر"),
        h(1776, "بز", "بزز", "NUCLEUS-ECHO", "أخذ الغنيمة وسلب المال", "بزه متاعه: سلبه وغلبه عليه", "تردد النفاذ من مضيق الحيازة والحراسة لإخراج المال"),
        h(1821, "زر", "أزر", "NUCLEUS-TRACE", "الإزار أو الحزام المشدود على الوسط", "الإزار ما يشد على الوسط، والأزر القوة والشد", "تحقق النفاذ الدقيق حول الوسط مع إمساك الثوب والجسد"),
        h(1939, "تل", "تلل", "NUCLEUS-TRACE", "التل، وهو كومة أو ربوة من طبقات متراكمة", "التل ما ارتفع من التراب وتراكم", "تحقق التكديس والاتباع طبقة فوق طبقة"),
        h(1961, "حي", "حيي", "NUCLEUS-TRACE", "الحياة وبقاء الكائن حيا", "حي حياة: كان ذا حياة وقوة", "تحقق الامتلاء والحيازة بقوة وحياة نصا ومعنى"),
        h(1965, "زل", "زلل", "NUCLEUS-ECHO", "المائع السائل الذي يجري ولا يثبت على هيئة", "الزلل حركة سهلة عن مستو، وزل الشيء عن موضعه", "تردد الانزلاق السهل في سيولة المادة وانتقالها"),
        h(2054, "سن", "سنن", "NUCLEUS-TRACE", "السن، وهو جسم ممتد حاد ينفذ في الطعام", "السن عضو القطع، وسن الشيء أحده", "تحقق الامتداد والنفاذ مع الحدة والدقة"),
        h(2274, "بح", "بوح", "NUCLEUS-ECHO", "فتح الشيء وإزالة انغلاقه", "باح الشيء ظهر وانكشف، والباحة فضاء ظاهر", "تردد الكشف والفراغ الناتجين من الفتح"),
        h(2435, "مل", "ملأ", "NUCLEUS-TRACE", "ملء الحيز حتى يصير ممتلئا", "ملأ الإناء: شغل حيزه وحواه", "تحقق الامتداد مع الحوز والشمول داخل الوعاء"),
        h(3103, "بء", "بوأ", "NUCLEUS-ECHO", "المجيء والوصول إلى جهة", "بوأه منزلا: أنزله ومكنه، وباء: رجع", "تردد الاستقرار والرجوع بوصفهما منتهى المجيء"),
        h(3186, "جن", "جنن", "NUCLEUS-TRACE", "الحماية والوقاية من وصول الأذى", "جن عليه: ستره، والجنة ما يستر ويقي", "تحقق الستر والكثافة اللذين يحولان دون النفاذ"),
        h(3217, "كف", "كفف", "NUCLEUS-TRACE", "باطن اليد أو الكف القابض", "الكف اليد، وكف الشيء قبضه أو منعه", "تحقق الانثناء والقبض على الشيء"),
        h(3802, "قم", "قوم", "NUCLEUS-TRACE", "النهوض والقيام من السكون", "قام: نهض وانتصب", "تحقق تجمع الجسد في قوام قوي مع تسنم وارتفاع"),
        h(3937, "كت", "كتت", "NUCLEUS-TRACE", "الدق والسحق بالضرب", "كت الشيء: دقه وكسره حتى صغر", "تحقق تداخل الأجزاء تحت الضغط حتى تدق وتنحصر"),
    ],
    "026": [
        h(4603, "جن", "جنن", "NUCLEUS-TRACE", "البستان الكثيف المحوط", "الجنة البستان لاستتار أرضه بكثافة الشجر", "تحقق الستر والكثافة في البستان"),
        h(4062, "حم", "فحم", "NUCLEUS-TRACE", "الفحم، وهو جسم يحمل الحرارة والجمر", "الفحم مادة الوقود السوداء التي تتقد وتحمي", "تحقق حدة الحرارة السارية في الجسم حتى تعمه"),
        h(5668, "هر", "هرس", "NUCLEUS-ECHO", "هدم البناء وتمزيق تماسكه", "هرس الشيء: دقه وفتته", "تردد التسيب البالغ الرقة حين يتحول المتماسك إلى فتات"),
        h(6488, "عم", "عمد", "NUCLEUS-TRACE", "العمود القائم الحامل لما فوقه", "العمود ما يعتمد عليه، وعمد الشيء أسنده", "تحقق الالتحام العلوي إذ يجمع العمود ما فوقه ويسنده"),
        h(6911, "قص", "قصص", "NUCLEUS-TRACE", "الحصاد بقطع الزرع في صفوف متتابعة", "قص الشيء: قطعه وأتبعه قطعا", "تحقق القطع مع التسوية والتتابع الممتد"),
        h(6989, "نق", "نقر", "NUCLEUS-TRACE", "شق أو نقرة غائرة في جسم", "النقرة حفرة في الشيء، ونقره أحدث فيه أثرا", "تحقق فراغ في العمق ينفذ فيه جسم غليظ"),
        h(7170, "صر", "صرر", "NUCLEUS-ECHO", "القبض على الشخص وحبس حركته", "صر الشيء: شده وجمعه ومنعه من التفرق", "تردد التضام الشديد الذي يمنع الانتشار والحركة"),
        h(9027, "صر", "صرر", "NUCLEUS-TRACE", "حزمة أو صرة مشدودة مجتمعة", "الصرة ما جمع وشد، وصر المتاع ضمه", "تحقق التضام الشديد الذي يمنع الانتشار"),
        h(9517, "لب", "لبب", "NUCLEUS-TRACE", "القلب، أي المركز الباطن الحي", "اللب خالص الشيء وباطنه، ويقال لب القلب", "تحقق اللزوم والتداخل في المركز الباطن"),
        h(9810, "زع", "زعزع", "NUCLEUS-TRACE", "الهز العنيف المتكرر", "زعزع الشيء: حركه وقلقله", "تحقق دفعات قليلة المقدار متكررة تصنع الاهتزاز"),
        h(14035, "بت", "بطل", "NUCLEUS-TRACE", "التوقف والإلغاء وانقطاع الفعل", "بطل الشيء: ذهب حكمه وتوقف أثره", "تحقق القطع والانفصال بقطع استمرار الفعل أو الحكم"),
        h(16169, "صر", "صرر", "NUCLEUS-ECHO", "العناد والانغلاق عن الطاعة أو التغير", "صر الشيء شده، ومنه الإصرار على الأمر", "تردد التضام الذي يمنع الانتشار في انغلاق الإرادة على موقف واحد"),
        h(16277, "قص", "قصص", "NUCLEUS-TRACE", "القطع والفصل والبتر والتشذيب", "قص الشيء: قطعه وسوى أطرافه", "تحقق القطع مع التسوية والتتابع الممتد"),
        h(16383, "كت", "كتت", "NUCLEUS-TRACE", "زيت من زيتون مدقوق مضغوط", "كت الزيتون: دقه وكسره", "تحقق تداخل الأجزاء بالدق والضغط حتى تنحصر ويخرج الزيت"),
        h(239, "مل", "ملك", "NUCLEUS-ECHO", "الملك صاحب السلطان على جماعة وحيز", "ملك الشيء حازه، والملك ذو السلطان", "تردد الامتداد مع الحوز والشمول في امتداد السلطان على الملك"),
        h(849, "جن", "جنن", "NUCLEUS-ECHO", "السرقة، وهي أخذ مال الغير في خفاء", "جن الشيء ستره وأخفاه", "تردد الستر والكثافة في خفاء فعل السرقة ومسروقها"),
        h(13961, "زم", "زمر", "NUCLEUS-ECHO", "الغناء وتأليف الصوت في أداء", "الزمر الغناء أو النفخ في المزمار", "تردد ضم الأنفاس والنغمات الكثيرة مكتنزة في عبارة صوتية"),
        h(5705, "رك", "ركب", "NUCLEUS-ECHO", "إجلاس شخص على دابة أو مركبة للركوب", "ركب الدابة أو المركب: علاه واستقر عليه", "تردد تجمع الراكب والمركوب بتماسك محدود عند موضع الحمل"),
        h(10678, "قب", "قبر", "NUCLEUS-TRACE", "دفن الجسد وإدخاله القبر", "القبر حفرة يوارى فيها الميت", "تحقق التجوف المحاط بصلابة الذي يستقر فيه المدفون"),
        h(6406, "دل", "دلو", "NUCLEUS-TRACE", "إدلاء الوعاء في البئر لاستخراج الماء", "أدلى الدلو: أرسلها إلى البئر، والدلو وعاء الاستقاء", "تحقق الامتداد من أعلى إلى مقر في العمق بقوة"),
        h(6897, "كف", "كفف", "NUCLEUS-ECHO", "المضاعفة أو جعل الشيء ذا طيتين", "كف الشيء: ثناه وقبض بعضه على بعض", "تردد الانثناء الذي يرد جزءا على جزء فينشأ الضعف"),
        h(8261, "كن", "سكن", "NUCLEUS-TRACE", "المسكن أو موضع الإقامة داخل بناء", "السكن المنزل الذي يأوي إليه المرء ويستقر", "تحقق الاستتار في جوف حيز يحوي الساكن"),
        h(8547, "من", "منع", "NUCLEUS-TRACE", "الامتناع والكف عن فعل", "منع الشيء: حجزه وكفه", "تحقق القوة والثبات مع الحجز"),
        h(8679, "زم", "زمر", "NUCLEUS-ECHO", "المزمور، أي نشيد مقدس مؤلف", "الزمر غناء ونفخ مؤلف من نغمات", "تردد ضم النغمات الكثيرة مكتنزة في نشيد واحد"),
        h(13578, "رح", "رحم", "NUCLEUS-TRACE", "الرحمة والرقة والتعطف", "رحمه: رق له وتعطف وأحسن إليه", "تحقق الاتساع والانبساط مع الرقة"),
    ],
    "027": [
        h(530, "حد", "وحد", "NUCLEUS-TRACE", "الواحد المنفرد الذي لا يتعدد", "وحد الشيء: أفرده، والواحد ما لا ثاني له", "تحقق إيقاف الامتداد والتخطي عند حد فرد واحد"),
        h(563, "شب", "عشب", "NUCLEUS-TRACE", "العشب والنبات الغض المجتمع في الأرض", "العشب نبات غض ينبت متجمعا", "تحقق تجمع النبت بعد انتشاره من البذر مع التركز"),
        h(701, "من", "يمن", "NUCLEUS-ECHO", "اليد اليمنى أو جهة اليمين", "اليمن واليمين يقترنان بالقوة والبركة", "تردد القوة والثبات في الجهة الأقوى المستعملة للتمكين"),
        h(764, "رك", "ركب", "NUCLEUS-ECHO", "العربة أو المركبة التي تجمع راكبا وحملا", "المركب ما يركب ويحمل الناس والمتاع", "تردد تجمع أجزاء المركبة وحمولتها بتماسك غير مصمت"),
        h(1110, "فح", "تفح", "NUCLEUS-ECHO", "التفاح، وهو ثمر ذو رائحة ظاهرة", "التفاح الثمر المعروف، وتذكر المروحة رائحته", "تردد صدور أثر حاد منتشر من كائن حي في فوح رائحة الثمرة"),
        h(1195, "صب", "صبغ", "NUCLEUS-ECHO", "اللون والصبغة الظاهرة على الجسم", "صبغ الشيء: لونه، والصبغ ما يسري على السطح", "تردد الحدر والامتداد إلى أسفل بقوة في سيلان مادة الصبغ على المصبوغ"),
        h(1277, "رم", "رمن", "NUCLEUS-TRACE", "ثمرة الرمان ذات الحبوب واللب المجتمع في جوفها", "الرمان ثمرة معروفة تحوي حبا ولبا كثيرا", "تحقق تجمع الرخو في الأثناء بعد تحول الثمرة ونضجها"),
        h(1706, "لق", "علق", "NUCLEUS-ECHO", "العلقة التي تلتصق بالجسم وتمتص منه", "العلق دودة تتعلق بالبدن، وعلق الشيء لزمه", "تردد الالتقاء القوي بالشيء في حيز التماس"),
        h(1913, "مل", "شمل", "NUCLEUS-TRACE", "ثوب يلتف على البدن ويغطيه", "الشملة كساء يشتمل به، وشمل الشيء أحاط به", "تحقق الامتداد مع الحوز والشمول حول البدن"),
        h(2058, "دب", "دبس", "NUCLEUS-ECHO", "العسل، وهو مائع حلو لزج بطيء الجريان", "الدبس عصارة حلوة كثيفة لزجة", "تردد الثقل والضغط والحركة البطيئة في لزوجة المائع"),
        h(2125, "جم", "جمل", "NUCLEUS-ECHO", "الجمل ذو الجسم الكبير والسنام", "الجمل الحيوان المعروف ذو السنام", "تردد التجمع والكثرة في كتلة البدن وما يجتمع في السنام"),
        h(2338, "بن", "بني", "NUCLEUS-TRACE", "البناء المرفوع المركب من أجزاء", "بنى البناء: رفعه وضم بعضه إلى بعض", "تحقق الامتداد والبناء نصا وآلية"),
        h(2936, "قد", "قدر", "NUCLEUS-ECHO", "العد وإحصاء الوحدات واحدة بعد أخرى", "قدر الشيء: حدد مقداره وقاسه", "تردد الامتداد المتتابع مع التحدد في مرور العد على الوحدات"),
        h(2999, "طل", "طلل", "NUCLEUS-TRACE", "الندى الظاهر قطرا على السطح", "الطل أضعف المطر والندى الذي يبدو على النبات", "تحقق الامتداد الظاهر من أصل في انتشار القطر على السطح"),
        h(3094, "سج", "سجد", "NUCLEUS-TRACE", "السجود والانحناء للعبادة", "سجد: خضع ووضع جبهته على الأرض", "تحقق الاعتدال والاستواء حين يسوى الجسد إلى سطح الأرض"),
        h(3281, "كب", "كبش", "NUCLEUS-ECHO", "الكبش أو الضأن ذو البدن المكتنز", "الكبش ذكر الضأن المعروف", "تردد تجمع الجرم كتلة متضاغطة في بدن الحيوان"),
        h(3306, "جب", "جبن", "NUCLEUS-ECHO", "الجبن المتجمد من اللبن", "الجبن ما انعقد من اللبن وصار جرما", "تردد التجسم والبروز حين ينقطع المائع ويتحول إلى كتلة مستوية"),
        h(3658, "حر", "حرم", "NUCLEUS-ECHO", "التحريم والتخصيص والإخراج من المباح أو الجماعة", "حرم الشيء: منعه، والحرام مفصول عن المباح", "تردد الخلوص من الغلظ في تنحية المحرم عن المجال المشترك"),
        h(5096, "هر", "هرس", "NUCLEUS-ECHO", "جذر يدل على الهدم والتخريب", "هرس الشيء: دقه وفتته", "تردد التسيب البالغ الرقة حين يفقد البناء تماسكه"),
        h(6258, "خذ", "أخذ", "NUCLEUS-TRACE", "الإمساك بالشيء وحيازته", "أخذ الشيء: تناوله وحازه", "تحقق النفاذ بقوة إلى الحوزة وإدخال المأخوذ فيها"),
        h(6316, "ثب", "ثوب", "NUCLEUS-ECHO", "الرجوع إلى المكان أو الشخص", "ثاب إلى موضعه: رجع واجتمع إليه", "تردد التجمع والتماسك حين يعود المتفرق إلى أصله"),
        h(7204, "شب", "شبك", "NUCLEUS-ECHO", "الأسر وجمع الشخص في حيازة الآسر", "شبكه في الشبكة: أنشبه وأمسكه", "تردد التجمع بعد الانتشار مع التركز في حيز الأسر"),
        h(7316, "مل", "ملأ", "NUCLEUS-TRACE", "جعل الشيء ممتلئا وشغل حيزه", "ملأ الوعاء: شغل حيزه وحواه", "تحقق الامتداد مع الحوز والشمول"),
        h(10988, "قص", "قصص", "NUCLEUS-TRACE", "الحصاد، أي الزرع المقطوع تباعا", "قص الشيء: قطعه وأتبع القطع", "تحقق القطع مع التسوية والتتابع الممتد"),
        h(17025, "عص", "عصب", "NUCLEUS-ECHO", "الألم والحزن وما فيهما من انقباض", "عصب الشيء: شده وربطه، والعصب اشتداد", "تردد الصلابة والاشتداد في انقباض الألم والحزن"),
    ],
    "028": [
        h(25, "سل", "سلم", "NUCLEUS-ECHO", "السلام وغياب الخصام والأذى", "السلم والسلام ضد الحرب وموضع الأمان", "تردد انسحاب الأذى ممتدا من الأثناء برفق"),
        h(385, "لف", "ألف", "NUCLEUS-ECHO", "الألف، أي جماعة من مئات ووحدات كثيرة", "الألف العدد المعروف، وألف الشيء جمعه وضم بعضه إلى بعض", "تردد الالتواء على الظاهر والوجود بكثافة في ضم الوحدات إلى عدد واحد"),
        h(523, "مر", "أمر", "NUCLEUS-ECHO", "القول وإخبار المخاطب", "أمره: قال له وطلب منه، والأمر كلام موجه", "تردد الاسترسال والحركة ذات الصفة في جريان الكلام ونبرته"),
        h(635, "رق", "ورق", "NUCLEUS-ECHO", "الخضرة أو النبات ذي الورق", "الورق ما انبسط رقيقا من الشجر", "تردد الانبساط مع الرقة في صفحة الورقة"),
        h(847, "لح", "لحي", "NUCLEUS-TRACE", "الخد أو جانب الفك العريض", "اللحي عظم الفك وما اتصل به من جانب الوجه", "تحقق الالتحام وما يلزمه من عرض وامتداد"),
        h(882, "شح", "شيح", "NUCLEUS-ECHO", "شجيرة أو جنبة خشبية", "الشيح نبات معروف دقيق الورق قوي الرائحة", "تردد جفاف الجرم وحدته مع عرض وتجسم في فروع الشجيرة"),
        h(930, "كل", "أكل", "NUCLEUS-ECHO", "الطعام أو الوجبة المجموعة للأكل", "الأكل تناول الطعام، والمأكل ما يجمع للأكل", "تردد تجمع المادة كتلة بلا طرف دقيق في الوجبة"),
        h(1015, "عم", "عمم", "NUCLEUS-ECHO", "الشعب أو الجماعة التي يشملها اسم واحد", "عم الشيء الجماعة وشملها", "تردد الالتحام والتجمع تحت اسم أعلى جامع"),
        h(1545, "حن", "حنن", "NUCLEUS-ECHO", "العفو والصفح بدافع الرحمة", "الحنان الرحمة والعطف، وحن عليه رق", "تردد جوف الشيء القوي وأثنائه في الرقة النابعة من الداخل"),
        h(1912, "حل", "حلم", "NUCLEUS-ECHO", "الحلم وما تتشكل فيه صور النوم", "الحلم ما يراه النائم", "تردد التسيب والتفكك في تحلل نظام اليقظة إلى صور المنام"),
        h(2296, "سل", "سلو", "NUCLEUS-ECHO", "الهدوء والسلام وانطفاء الاضطراب", "سلا همه: نسيه وسكن عنه", "تردد انسحاب الاضطراب ممتدا من الأثناء برفق"),
        h(2442, "رق", "رقص", "NUCLEUS-ECHO", "الرقص والوثب بخفة", "رقص: تحرك ووثب على إيقاع", "تردد الانبساط مع الرقة في امتداد الأطراف وخفة الحركة"),
        h(2503, "قر", "وقر", "NUCLEUS-ECHO", "غلاء الثمن وثقل القيمة", "الوقر الثقل، والوقار ثبات ورزانة", "تردد استقرار ما شأنه التسيب في ثقل القيمة ورسوخها"),
        h(3041, "لب", "لبب", "NUCLEUS-ECHO", "الشحم الحيواني المتخلل للحم", "اللب باطن الشيء وخالصه", "تردد اللزوم والتداخل في تشرب الشحم خلال الأنسجة"),
        h(3261, "نش", "نشز", "NUCLEUS-TRACE", "رفع الشيء إلى أعلى", "نشز الشيء: ارتفع، وأنشزه: رفعه", "تحقق الارتفاع بانتشار مع حدة"),
        h(4479, "شط", "شطط", "NUCLEUS-ECHO", "نزع الثوب وإبعاده عن الجسد", "شط الشيء: بعد وامتد جانبا", "تردد الامتداد بجانب والانقسام عن الجسد في فصل طبقة اللباس"),
        h(4791, "قر", "قرن", "NUCLEUS-ECHO", "القرن الصلب النابت من الرأس", "القرن نتوء صلب ثابت في الرأس", "تردد استقرار ما شأنه الامتداد في قاعدة صلبة وحيز الرأس"),
        h(5073, "حم", "حمد", "NUCLEUS-ECHO", "الشيء المحبوب النفيس الباعث للسرور", "حمد الشيء: أثنى عليه لفضله وحسنه", "تردد حدة تسري في النفس حتى تعمها في أثر الاستحسان"),
        h(8569, "جل", "جلل", "NUCLEUS-ECHO", "اللفافة أو الدرج الذي يبسط للقراءة", "جلا الشيء كشفه، والجلل ما يعم ويغطي", "تردد الاتساع والانكشاف حين يبسط الدرج ويظهر مكتوبه"),
        h(8716, "نص", "نصب", "NUCLEUS-TRACE", "الساق أو الفرخ النباتي الصاعد", "نصب الشيء: أقامه ورفعه", "تحقق النفاذ بامتداد مع علو في صعود الساق"),
        h(9718, "قن", "قني", "NUCLEUS-ECHO", "الحسد والرغبة في امتلاك ما عند الغير", "قني المال: اكتسبه واتخذه لنفسه", "تردد الأخذ إلى الباطن بعمق في نزوع الحاسد إلى الحيازة"),
        h(11370, "هر", "نهر", "NUCLEUS-TRACE", "واد عميق يجري فيه ماء", "النهر مجرى الماء الجاري", "تحقق التسيب البالغ الرقة في الماء الممتد خلال الوادي"),
        h(11834, "حك", "حكك", "NUCLEUS-ECHO", "الحنك، وهو السطح الصلب في أعلى الفم", "حك الشيء بالصلب: دلكه وضغطه عليه", "تردد الدلك بضغط على الصلب في تماس اللسان والطعام بالحنك"),
        h(12672, "قت", "قتر", "NUCLEUS-ECHO", "البخور ودخانه الدقيق النافذ", "القتر دخان ذو رائحة ينتشر من الاحتراق", "تردد الدقة وقلة القوة في العمق في نفاذ أثر الدخان اللطيف"),
        h(16404, "قش", "قشش", "NUCLEUS-TRACE", "جمع العيدان أو القش اليابس", "القش يابس النبات، وقشش الشيء جمعه", "تحقق جفاف الظاهر وتقلصه في المادة المجموعة نفسها"),
    ],
    "029": [
        h(386, "لف", "ألف", "NUCLEUS-ECHO", "الألفية، أي مدة ملتئمة من ألف سنة", "الألف العدد المعروف، وألف الشيء ضمه وجمعه", "تردد الالتواء على الظاهر والوجود بكثافة في ضم السنين إلى وحدة زمنية"),
        h(956, "لق", "لقط", "NUCLEUS-ECHO", "أخذ الشيء وقبضه باليد", "لقط الشيء: أخذه من موضعه", "تردد الالتقاء بالشيء في الحيز بقوة عند القبض"),
        h(1274, "شو", "ثور", "NUCLEUS-ECHO", "الثور ذو القرنين البارزين", "الثور الحيوان المعروف ذو القرنين", "تردد النتوء والظهور والزيادة الدقيقة في بروز القرنين"),
        h(2231, "حط", "حطط", "NUCLEUS-ECHO", "الخطيئة وما فيها من سقوط عن الصواب", "حط الشيء: أنزله ووضعه أسفل", "تردد الانضغاط بقوة إلى أسفل في صورة السقوط المعنوي"),
        h(2232, "حط", "حطط", "NUCLEUS-ECHO", "الخاطئ الذي انحط عن وجه الصواب", "حط الشيء: أنزله ووضعه أسفل", "تردد الانضغاط بقوة إلى أسفل في انحطاط الفاعل عن الصواب"),
        h(5540, "فر", "فرر", "NUCLEUS-ECHO", "البرغوث الذي يقفز ويفارق موضعه سريعا", "فر: هرب وفارق موضعه", "تردد الفصل والتفريق في وثب الحشرة بعيدا عن موضع التماس"),
        h(5906, "شح", "شحح", "NUCLEUS-ECHO", "داء السل الذي يهزل الجسم ويجففه", "شح الجسم: يبس ونحل، والشح قلة المادة", "تردد جفاف الجرم وحدته مع بقاء تجسمه في هزال المرض"),
        h(6482, "حم", "حمد", "NUCLEUS-ECHO", "جذر اللذة والحسن والنفاسة", "حمد الشيء: أثنى عليه لحسنه وفضله", "تردد حدة تسري في النفس حتى تعمها في أثر الاستحسان"),
        h(7202, "شب", "شعب", "NUCLEUS-ECHO", "إرجاع الشيء إلى موضعه أو صاحبه", "شعب الشيء: جمعه بعد تفرق وأصلحه", "تردد التجمع بعد الانتشار مع التركز عند العودة"),
        h(7504, "بك", "بكر", "NUCLEUS-ECHO", "صغير الإبل في أول سنه", "البكر الفتي من الإبل وما كان في أول حاله", "تردد الضغط والاحتباس في طور النشأة القريب من الحيازة الأولى"),
        h(7729, "قط", "قطب", "NUCLEUS-ECHO", "الشوكة أو اللسعة ذات الطرف القاطع", "القطب شوك أو حديدة ذات طرف", "تردد القطع باستواء في نفاذ الطرف الحاد"),
        h(8118, "حن", "حنن", "NUCLEUS-ECHO", "الرأفة والرحمة واللطف", "الحنان الرحمة والعطف", "تردد جوف الشيء القوي وأثنائه في الرقة النابعة من الداخل"),
        h(9425, "كذ", "كذب", "NUCLEUS-ECHO", "الكذب والخداع وإخراج الخبر عن حقيقته", "كذب: أخبر بخلاف الواقع", "تردد الرخاوة النسبية في خبر لا يثبت على حقيقة صلبة"),
        h(9821, "جب", "جبر", "NUCLEUS-ECHO", "الرجل الجبار القوي البارز بين قومه", "الجبر القوة والقهر وإقامة المكسور", "تردد التجسم والبروز في ظهور القوة في صاحبها"),
        h(9880, "بك", "بكر", "NUCLEUS-ECHO", "المولود الأول الخارج من الحمل الأول", "البكر أول الولد وما تقدم في بابه", "تردد الضغط والاحتباس في الخروج من أول حيازة رحمية"),
        h(12781, "شب", "شبك", "NUCLEUS-ECHO", "الأسر والحالة التي يجمع فيها الأسير داخل حيازة", "شبكه: أنشبه وأمسكه في الشبكة", "تردد التجمع بعد الانتشار مع التركز في حيز الأسر"),
        h(13031, "خر", "خرب", "NUCLEUS-TRACE", "الخراب والدمار والموضع المتداعي", "خرب المكان: تهدم وذهب عمرانه", "تحقق تخلخل الأثناء وتسيبها ونقص البنية"),
        h(13047, "بق", "بقع", "NUCLEUS-TRACE", "واد واسع مكشوف بين المرتفعات", "البقعة قطعة ظاهرة من الأرض", "تحقق الثبات والكشف باتساع في الحيز الأرضي المفتوح"),
        h(15805, "قل", "قلي", "NUCLEUS-ECHO", "خبز محمص أخرجت النار بعض رطوبته", "قلى الطعام: أنضجه على النار", "تردد الرفع في رفع الرطوبة والخفة من الخبز بالحرارة"),
        h(15995, "قر", "قرب", "NUCLEUS-TRACE", "تقريب الشيء وإحضاره وتقديمه قربانا", "قرب الشيء: دنا، وقربه: أدناه وقدمه", "تحقق استقرار ما شأنه التسيب في حيز دان مشترك"),
        h(16042, "حف", "حفن", "NUCLEUS-TRACE", "حفنة يحيط بها باطن اليد والأصابع", "حفن الشيء: أخذه بملء الكفين", "تحقق الإحاطة بالشيء من خارج"),
        h(16096, "مر", "مهر", "NUCLEUS-ECHO", "مهر العروس المنتقل إلى أهلها", "المهر صداق المرأة المدفوع عند الزواج", "تردد الاسترسال والحركة ذات الصفة في انتقال العوض المسمى"),
        h(16206, "شن", "شنن", "NUCLEUS-ECHO", "شحذ الحد حتى يصير أدق وأمضى", "شن الشيء: فرقه ونشر دقاقه", "تردد انتشار الدقاق من أثناء الشيء في برادة الشحذ"),
        h(16391, "لق", "لعق", "NUCLEUS-ECHO", "محب الحلو الذي يكرر لعق الطعام", "لعق الطعام: تناوله بلسانه", "تردد الالتقاء بالشيء في الحيز عند تماس اللسان بالطعام"),
        h(16695, "زم", "زمم", "NUCLEUS-ECHO", "حلقة الأنف التي تمسك في موضع ضيق", "الزمام ما يشد به ويضبط، وزم الشيء شده", "تردد ضم الكثير باكتناز في إحكام الحلقة وما تمسكه"),
    ],
}


def a(
    line: int,
    branch: str,
    arabic: str,
    realization: str,
    witness_override: str | None = None,
) -> dict[str, Any]:
    return {
        "source_line": line,
        "branch": branch,
        "arabic": arabic,
        "realization": realization,
        "witness_override": witness_override,
    }


ARAMAIC_REPAIRS = [
    a(6, "الثقب والطعن", "ذكر الحديد: حد وصلب", "تردد حدة الرأس وصلابته البالغة في فعل الطعن"),
    a(63, "التمييز والفصل", "فض الشيء: كسره وفرق أجزاءه", "تحقق الكسر والتفريق بقوة وغلظ"),
    a(73, "الذهاب ومفارقة الموضع", "زل عن موضعه: تحرك عنه بسهولة", "تردد الانزلاق عن مستو يتيح الحركة والمفارقة"),
    a(84, "القوة والاقتدار", "عز الشيء: قوي واشتد", "تحقق تماسك الأثناء والاشتداد"),
    a(104, "نزول المطر", "مطر السحاب: صب ماءه", "تحقق الامتداد والانسكاب من أعلى"),
    a(107, "النفخ وإخراج النفس", "نفح: هب وانتشر أثره", "تحقق النفاذ أو الإبعاد بانتشار"),
    a(554, "الرحى أو حجر الطحن الدائري", "الرحى حجر عريض يدور على ما يطحن", "تحقق الاتساع والانبساط في سطح الحجر الدائر"),
    a(690, "حضن البيض للتفريخ", "الحمي والحمى حرارة تسري وتحفظ", "تردد حدة الدفء السارية في البيض حتى تعمه"),
    a(692, "الحرارة والحمى", "حم الشيء واحتم: اشتدت حرارته", "تحقق الحدة السارية في الجسم حتى تعمه"),
    a(881, "الصلاة والدعاء", "صلى: أدى الصلاة ولزم هيئتها", "تحقق التماسك الدقيق في اتصال حركات الصلاة وتوجهها"),
    a(916, "الإطعام والرعي", "رعى الماشية: أسامها في المرعى وغذاها", "تحقق الامتداد مع الرقة في انتشار الرعي على النبات الغض"),
    a(1022, "البرودة والتجمد", "قر الماء: سكن وثبت، والقر البرد", "تردد استقرار ما شأنه التسيب حين يجمد السائل"),
    a(1023, "البرودة والتجمد في الصفة المؤنثة", "قر الماء: سكن وثبت، والقر البرد", "تردد استقرار ما شأنه التسيب حين يجمد السائل"),
    a(1039, "البكاء والنواح", "بكى: سال دمعه لحزن", "تحقق الضغط والاحتباس في انقباض الحزن قبل خروج الدمع"),
    a(1761, "الاكتساب والحصول", "قني المال: اكتسبه واتخذه لنفسه", "تحقق الأخذ إلى الباطن والضم إلى الحيازة", "قني"),
    a(1810, "الملكية والمال المقتنى", "القنية ما اكتسب وثبت لصاحبه", "تحقق الأخذ إلى الباطن والدوام في الحيازة", "قني"),
    a(2044, "التعيين في منصب", "منى الأمر: قدره وحدده", "تحقق القوة والثبات مع الحجز حين يثبت المنصب لصاحبه", "مني"),
    a(2045, "المنا، وهو وزن مقدر", "المنا مقدار يوزن به، ومنى بمعنى قدر", "تحقق الثبات والتحديد والحجز في مقدار الوزن", "مني"),
    a(138, "بسط الشيء إلى الخارج", "الشط جانب ممتد بعيد عن الوسط", "تردد الامتداد بجانب أو الانقسام عنه"),
    a(167, "الروح أو الشبح اللطيف الخفي", "الروح النفس وما به الحياة", "تردد نفاذ شيء لطيف أو خفي من حيز إلى آخر"),
    a(204, "الاستغراق: كل الشيء وأجمعه", "كل للاستغراق وجمع الأجزاء", "تحقق تجمع الشيء كله كتلة بلا طرف مستثنى"),
    a(344, "المطر النازل", "المطر ماء السحاب المنسكب", "تحقق الامتداد والانسكاب من السحاب"),
    a(1485, "اليد التي تمتد للقبض والعمل", "اليد والكف أداة القبض والتمكين", "تحقق الامتداد بقوة للتمكين أو الضغط"),
    a(410, "صورة اليد البديلة", "اليد والكف أداة القبض والتمكين", "تحقق الامتداد بقوة للتمكين أو الضغط"),
    a(325, "الحياة والحيوات", "حي حياة: كان ذا حياة وقوة", "تحقق الامتلاء والحيازة بقوة وحياة"),
]


def load_rows() -> tuple[list[str], dict[str, tuple[int, dict[str, Any]]]]:
    raw = COVERAGE.read_text(encoding="utf-8").splitlines()
    by_member: dict[str, tuple[int, dict[str, Any]]] = {}
    for index, line in enumerate(raw):
        row = json.loads(line)
        member = row.get("member_id")
        if member in by_member:
            raise RuntimeError(f"duplicate coverage member: {member}")
        by_member[member] = (index, row)
    return raw, by_member


def rows_by_source(
    by_member: dict[str, tuple[int, dict[str, Any]]], language: str
) -> dict[int, tuple[int, dict[str, Any]]]:
    result: dict[int, tuple[int, dict[str, Any]]] = {}
    for index, row in by_member.values():
        if row.get("language") == language:
            line = int(row["source_line"])
            if line in result:
                raise RuntimeError(f"duplicate {language} source line: {line}")
            result[line] = (index, row)
    return result


def frozen_readings() -> dict[str, str]:
    data = json.loads(NUCLEI.read_text(encoding="utf-8"))
    items = data["levels"]["level_2_binary_nuclei"]["nuclei"]
    return {item["nucleus"]: item.get("jabal_lexicon_reading_ar") or "" for item in items}


def load_fan_module():
    path = REPO / "scripts" / "search_arabic_root_senses.py"
    spec = importlib.util.spec_from_file_location("arabic_fan", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load Arabic fan module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def source_fans(roots: set[str]) -> dict[str, list[str]]:
    module = load_fan_module()
    matches = module.matches_for_roots(module.DEFAULT_RESOURCES, roots, None)
    result: dict[str, list[str]] = {}
    for root in roots:
        fan = module.independent_fan(matches.get(root, []), 2)
        if not fan["judgment_ready"]:
            raise RuntimeError(f"Arabic fan incomplete for {root}")
        sources = [item["source_label"] for item in fan["selected_sources"]]
        if len(sources) < 2 or sources[0] == sources[1]:
            raise RuntimeError(f"Arabic fan not independent for {root}: {sources}")
        result[root] = sources[:2]
    return result


def choose_candidate(connection: sqlite3.Connection, member: str, nucleus: str) -> dict[str, Any]:
    rows = connection.execute(
        """select form, status, positions_json, rule_ids_json, route_flag
           from candidates where entry_id=? and kind='nucleus' and form=?""",
        (member, nucleus),
    ).fetchall()
    ready = [row for row in rows if row["status"] == "licensed" and not row["route_flag"]]
    if not ready:
        raise RuntimeError(f"no licensed non-route nucleus {nucleus} for {member}")
    ready.sort(key=lambda row: (len(json.loads(row["rule_ids_json"])), row["rule_ids_json"]))
    row = ready[0]
    return {
        "positions": json.loads(row["positions_json"]),
        "rule_ids": json.loads(row["rule_ids_json"]),
    }


def replace_coverage(raw: list[str], changes: dict[int, dict[str, Any]]) -> None:
    for index, row in changes.items():
        raw[index] = json.dumps(row, ensure_ascii=False)
    if len(raw) != len(set(json.loads(line)["member_id"] for line in raw)):
        raise RuntimeError("coverage identity invariant failed")
    temp = COVERAGE.with_suffix(".jsonl.nucleus-eye.tmp")
    temp.write_text("\n".join(raw) + "\n", encoding="utf-8")
    os.replace(temp, COVERAGE)


def append_once(path: Path, marker: str, text: str) -> None:
    current = path.read_text(encoding="utf-8")
    if marker in current:
        raise RuntimeError(f"marker already present: {marker}")
    path.write_text(current.rstrip() + "\n\n" + text.rstrip() + "\n", encoding="utf-8")


def apply_hebrew(batch: str) -> dict[str, int]:
    specs = HEBREW_BATCHES[batch]
    raw, by_member = load_rows()
    by_source = rows_by_source(by_member, "hebrew")
    readings = frozen_readings()
    fans = source_fans({item["witness"] for item in specs})
    connection = sqlite3.connect(DB)
    connection.row_factory = sqlite3.Row
    before = sum(
        1
        for _, row in by_member.values()
        if row.get("language") == "hebrew" and row.get("nucleus_layer", {}).get("issued")
    )
    changes: dict[int, dict[str, Any]] = {}
    cards: list[str] = []
    trace = 0
    echo = 0
    chosen_rows: list[dict[str, Any]] = []
    for item in specs:
        index, old = by_source[item["source_line"]]
        row = json.loads(json.dumps(old, ensure_ascii=False))
        if row.get("direction_class"):
            raise RuntimeError(f"direction gate blocks {row['member_id']}")
        if row.get("nucleus_layer", {}).get("issued"):
            raise RuntimeError(f"nucleus already issued for {row['member_id']}")
        if not row.get("root_layer", {}).get("issued"):
            raise RuntimeError(f"root-positive seam absent for {row['member_id']}")
        reading = readings.get(item["nucleus"], "")
        if not reading:
            raise RuntimeError(f"frozen reading missing for {item['nucleus']}")
        candidate = choose_candidate(connection, row["member_id"], item["nucleus"])
        sources = fans[item["witness"]]
        verb = "تحقق" if item["outcome"] == "NUCLEUS-TRACE" else "تردد"
        bridge = (
            f"جوار المعنى في الفرع: {item['branch']}؛ جواره في العربية: "
            f"{item['arabic']}؛ النواة `{item['nucleus']}` {item['realization']}."
        )
        selected = {
            "nucleus": item["nucleus"],
            "reading_ar": reading,
            "status": "licensed",
            "positions": candidate["positions"],
            "rule_ids": candidate["rule_ids"],
            "route_required": False,
            "arabic_root_witness": item["witness"],
            "old_arabic_sources": sources,
            "outcome": item["outcome"],
            "bridge": bridge,
            "bridge_explicit": {
                "branch_neighborhood": item["branch"],
                "arabic_neighborhood": item["arabic"],
                "nucleus_realization": f"النواة `{item['nucleus']}` {item['realization']}",
            },
        }
        layer = dict(row["nucleus_layer"])
        layer.update(
            {
                "outcome": item["outcome"],
                "issued": True,
                "basis": "صلة نووية موجبة من عين النواة؛ المروحة مستقلة والمدار ثلاثي صريح.",
                "selected": selected,
            }
        )
        row["nucleus_layer"] = layer
        row["nucleus_eye_batch"] = f"hebrew-nucleus-eye-{batch}"
        changes[index] = row
        chosen_rows.append(row)
        if item["outcome"] == "NUCLEUS-TRACE":
            trace += 1
        else:
            echo += 1
        rules = "هوية بلا صف" if not candidate["rule_ids"] else " + ".join(candidate["rule_ids"])
        positions = ",".join(candidate["positions"])
        cards.append(
            f"### عين النواة: `{row['family_id']}`، {row['orthography']}، العضو `{row['member_id']}`\n"
            f"- العضو في الفرع: {row['orthography']} `{row.get('romanization') or 'بلا رومنة'}`، "
            f"{row.get('pos') or 'غير موسوم'}، «{row.get('branch_meaning') or 'غير منشور'}» [Kaikki Hebrew، السطر {row['source_line']}].\n"
            f"- حكم طبقة الجذر: {row['root_layer']['outcome']}؛ بقي الحكم الجذري مستقلا ولم يُستعمل بديلا من قراءة النواة.\n"
            "- درجةُ المقارنة: فُحص الجذر والنواة استقلالًا في عرض واحد؛ لا تتوقف طبقة على نجاح الأخرى أو فشلها.\n"
            f"- حكم طبقة النواة: {item['outcome']}؛ النواة `{item['nucleus']}` «{reading}» من `data/juthoor-core-levels.json`.\n"
            f"- المروحة العربية غير المقتطعة: `{item['witness']}`.\n"
            f"  - المصدر العربي القديم الأول: {sources[0]}، مادة `{item['witness']}` كاملة.\n"
            f"  - المصدر العربي القديم الثاني: {sources[1]}، مادة `{item['witness']}` كاملة.\n"
            f"- مسار الصوت: الموضع `{positions}`؛ {rules}؛ مرشح مرخص في السجل النافذ، ولا صف جديد.\n"
            f"- المدار الصريح: جوار المعنى في الفرع: {item['branch']}؛ جواره في العربية: {item['arabic']}؛ "
            f"النواة `{item['nucleus']}` «{reading}» {verb} هذا المدار لأن {item['realization']}.\n"
            f"- المصفاة الاتجاهية: لا يحمل العضو تصنيف نقل؛ لم تتحول المقارنة إلى قرض ولا القرض إلى إرث.\n"
            f"- الحكم (استكشاف): {item['outcome']} للعضو `{row['member_id']}` وحده؛ "
            f"حكم الجذر={row['root_layer']['outcome']}؛ حكم النواة={item['outcome']}."
        )
    connection.close()
    if len(changes) != len(specs):
        raise RuntimeError("Hebrew change count mismatch")
    replace_coverage(raw, changes)
    after = before + len(specs)
    marker = f"HEBREW-NUCLEUS-EYE-BATCH-{batch}"
    start = min(chosen_rows, key=lambda row: row["source_line"])
    end = max(chosen_rows, key=lambda row: row["source_line"])
    report = (
        f"## العبرية بعين النواة، الدفعة {batch} (2026-08-01)\n\n"
        + "\n\n".join(cards)
        + "\n\n### محضر الدفعة القصير\n\n"
        + f"- الرقم الأول، الصلات النووية الموجبة الجديدة: {len(specs)}.\n"
        + "- الرقم الثاني، الإغلاقات الجديدة: 0.\n"
        + f"- التفصيل: NUCLEUS-TRACE={trace}؛ NUCLEUS-ECHO={echo}؛ الإجمالي العبري {before} ← {after}.\n"
        + f"- سطر الموضع: عرق ROOT-positive/NUCLEUS-open؛ من `{start['member_id']}` عند سطر المصدر {start['source_line']} "
        + f"إلى `{end['member_id']}` عند سطر المصدر {end['source_line']}؛ الأعضاء غير متجاورة لأنها مستخرجة من العرق لا من شريحة الجرد.\n"
        + "- التغطية: الجرد العبري باق كامل التغطية؛ تغير حكم النواة لهذه الأعضاء وحدها، ولم ينشأ إغلاق في الفراغ.\n"
        + "- الضوابط: لكل صلة مصدران عربيان قديمان مستقلان مسميان، ومدار ثلاثي صريح، ومسار مرخص غير اتجاهي؛ ملف النوى المجمد لم يعدل."
    )
    wrapped = f"<!-- {marker}:BEGIN -->\n\n{report}\n\n<!-- {marker}:END -->"
    append_once(HEBREW_READING, f"<!-- {marker}:BEGIN -->", wrapped)
    audit = AUDITS / f"lane-a-hebrew-nucleus-eye-batch-{batch}.md"
    if audit.exists():
        raise RuntimeError(f"audit already exists: {audit}")
    audit.write_text(report + "\n", encoding="utf-8")
    return {"new": len(specs), "closures": 0, "before": before, "after": after, "trace": trace, "echo": echo}


def apply_aramaic_repairs() -> dict[str, int]:
    raw, by_member = load_rows()
    by_source = rows_by_source(by_member, "aramaic")
    overrides = source_fans({"قني", "مني"})
    changes: dict[int, dict[str, Any]] = {}
    cards: list[str] = []
    before = sum(
        1
        for _, row in by_member.values()
        if row.get("language") == "aramaic" and row.get("nucleus_layer", {}).get("issued")
    )
    for item in ARAMAIC_REPAIRS:
        index, old = by_source[item["source_line"]]
        row = json.loads(json.dumps(old, ensure_ascii=False))
        layer = row.get("nucleus_layer", {})
        selected = dict(layer.get("selected") or {})
        if not layer.get("issued") or selected.get("status") != "licensed" or selected.get("route_required"):
            raise RuntimeError(f"repair target is not an issued licensed nucleus: {row['member_id']}")
        witness = item["witness_override"] or selected["arabic_root_witness"]
        sources = overrides[witness] if item["witness_override"] else list(selected["old_arabic_sources"])
        if len(sources) < 2 or sources[0] == sources[1]:
            raise RuntimeError(f"repair source gate failed: {row['member_id']}")
        outcome = layer["outcome"]
        verb = "تحقق" if outcome == "NUCLEUS-TRACE" else "تردد"
        bridge = (
            f"جوار المعنى في الفرع: {item['branch']}؛ جواره في العربية: {item['arabic']}؛ "
            f"النواة `{selected['nucleus']}` {item['realization']}."
        )
        selected.update(
            {
                "arabic_root_witness": witness,
                "old_arabic_sources": sources[:2],
                "outcome": outcome,
                "bridge": bridge,
                "bridge_explicit": {
                    "branch_neighborhood": item["branch"],
                    "arabic_neighborhood": item["arabic"],
                    "nucleus_realization": f"النواة `{selected['nucleus']}` {item['realization']}",
                },
            }
        )
        layer["selected"] = selected
        row["nucleus_layer"] = layer
        row["aramaic_repair_batch"] = "aramaic-nucleus-card-repair-025"
        changes[index] = row
        rules = "هوية بلا صف" if not selected.get("rule_ids") else " + ".join(selected["rule_ids"])
        cards.append(
            f"### إصلاح البطاقة: `{row['family_id']}`، {row['orthography']}، العضو `{row['member_id']}`\n"
            f"- الحكم محفوظ بلا زيادة عد: {outcome}؛ النواة `{selected['nucleus']}` «{selected['reading_ar']}».\n"
            f"- المصدر العربي القديم الأول: {sources[0]}، مادة `{witness}` كاملة غير مقتطعة.\n"
            f"- المصدر العربي القديم الثاني: {sources[1]}، مادة `{witness}` كاملة غير مقتطعة.\n"
            f"- مسار الصوت: الموضع `{','.join(selected['positions'])}`؛ {rules}؛ لا صف جديد.\n"
            f"- المدار الصريح: جوار المعنى في الفرع: {item['branch']}؛ جواره في العربية: {item['arabic']}؛ "
            f"النواة `{selected['nucleus']}` «{selected['reading_ar']}» {verb} هذا المدار لأن {item['realization']}.\n"
            f"- المصفاة الاتجاهية: بقي حكم العضو غير اتجاهي؛ لا قرض حُوّل إلى إرث."
        )
    if len(changes) != 25:
        raise RuntimeError(f"Aramaic repair set is {len(changes)}, expected 25")
    replace_coverage(raw, changes)
    marker = "ARAMAIC-NUCLEUS-CARD-REPAIR-025"
    report = (
        "## إصلاح خمس وعشرين بطاقة آرامية (2026-08-01)\n\n"
        + "\n\n".join(cards)
        + "\n\n### محضر الإصلاح القصير\n\n"
        + "- الرقم الأول، البطاقات المصححة: 25.\n"
        + "- الرقم الثاني، الإغلاقات الجديدة: 0.\n"
        + f"- صلات النواة الآرامية قبل الإصلاح وبعده: {before} ← {before}؛ لا زيادة عدية، لأن العمل توثيقي على أحكام قائمة.\n"
        + "- سطر الموضع: 14 فجوة بطاقة + 4 فجوات تسمية مصدر ثان + 7 فجوات صياغة مدار = 25 هوية مسماة؛ امتد موضعها من سطر Kaikki 6 إلى 2045.\n"
        + "- لكل بطاقة الآن مصدران قديمان مستقلان مسميان ومدار يصرح بجوار الفرع وجوار العربية والنواة المحققة أو المرددة."
    )
    wrapped = f"<!-- {marker}:BEGIN -->\n\n{report}\n\n<!-- {marker}:END -->"
    append_once(ARAMAIC_READING, f"<!-- {marker}:BEGIN -->", wrapped)
    audit = AUDITS / "lane-a-aramaic-nucleus-card-repair-025.md"
    if audit.exists():
        raise RuntimeError(f"audit already exists: {audit}")
    audit.write_text(report + "\n", encoding="utf-8")
    return {"repaired": 25, "closures": 0, "before": before, "after": before}


def apply_final_audit() -> dict[str, int]:
    raw, by_member = load_rows()
    target = "kaikki_hebrew:4849:en-הראה-he-verb-HGMzUJ3r"
    index, old = by_member[target]
    row = json.loads(json.dumps(old, ensure_ascii=False))
    layer = row["nucleus_layer"]
    selected = dict(layer.get("selected") or {})
    if not layer.get("issued") or selected.get("nucleus") != "رأ":
        raise RuntimeError("expected the pre-existing unlicensed רא nucleus issue")
    row["withdrawn_nucleus_audit"] = {
        "previous_outcome": layer["outcome"],
        "previous_selected": selected,
        "reason": "لا يوجد للعضو مرشح nucleus=رأ مرخص مطابق في سجل candidates؛ لم يخترع بديل.",
    }
    layer.update(
        {
            "outcome": "LAW-GAP",
            "issued": False,
            "basis": "LAW-GAP: سُحب الحكم القديم لأن nucleus=رأ لا يطابق مرشحا مرخصا للعضو؛ بقي مفتوحا بلا بديل مخترع.",
            "selected": None,
        }
    )
    row["nucleus_layer"] = layer
    row["nucleus_eye_audit"] = "hebrew-nucleus-eye-operation-final"
    replace_coverage(raw, {index: row})

    raw2, members = load_rows()
    del raw2
    connection = sqlite3.connect(DB)
    coverage = [value[1] for value in members.values()]
    for language in ("hebrew", "aramaic"):
        rows = [item for item in coverage if item.get("language") == language]
        entry_ids = {
            value[0]
            for value in connection.execute("select entry_id from entries where language=?", (language,))
        }
        family_ids = {
            value[0]
            for value in connection.execute("select family_id from families where language=?", (language,))
        }
        if {item["member_id"] for item in rows} != entry_ids:
            raise RuntimeError(f"coverage/member mismatch for {language}")
        if {item["family_id"] for item in rows} != family_ids:
            raise RuntimeError(f"coverage/family mismatch for {language}")
        if not all(item.get("root_layer", {}).get("outcome") and item.get("nucleus_layer", {}).get("outcome") for item in rows):
            raise RuntimeError(f"missing two-layer outcome for {language}")
        for item in rows:
            nucleus_layer = item.get("nucleus_layer", {})
            if not nucleus_layer.get("issued"):
                continue
            chosen = nucleus_layer.get("selected") or {}
            sources = chosen.get("old_arabic_sources") or []
            if len(sources) < 2 or len(set(sources)) < 2:
                raise RuntimeError(f"two-source gate failed for {item['member_id']}")
            if item.get("direction_class"):
                raise RuntimeError(f"direction gate failed for {item['member_id']}")
            licensed = connection.execute(
                """select count(*) from candidates where entry_id=? and kind='nucleus'
                   and form=? and status='licensed' and route_flag=0""",
                (item["member_id"], chosen["nucleus"]),
            ).fetchone()[0]
            if not licensed:
                raise RuntimeError(f"sound-candidate gate failed for {item['member_id']}")
    connection.close()

    hebrew = [item for item in coverage if item.get("language") == "hebrew"]
    aramaic = [item for item in coverage if item.get("language") == "aramaic"]
    hebrew_issued = [item for item in hebrew if item.get("nucleus_layer", {}).get("issued")]
    aramaic_issued = [item for item in aramaic if item.get("nucleus_layer", {}).get("issued")]
    new = [item for item in hebrew if str(item.get("nucleus_eye_batch", "")).startswith("hebrew-nucleus-eye-")]
    repaired = [item for item in aramaic if item.get("aramaic_repair_batch") == "aramaic-nucleus-card-repair-025"]
    root_open = [
        item
        for item in hebrew
        if item.get("root_layer", {}).get("issued")
        and not item.get("nucleus_layer", {}).get("issued")
        and not item.get("direction_class")
    ]
    if len(new) != 125 or not all((item["nucleus_layer"].get("selected") or {}).get("bridge_explicit") for item in new):
        raise RuntimeError("new Hebrew operation set failed")
    if len(repaired) != 25 or not all((item["nucleus_layer"].get("selected") or {}).get("bridge_explicit") for item in repaired):
        raise RuntimeError("Aramaic repair set failed")
    if len(hebrew) != 17034 or len({item["family_id"] for item in hebrew}) != 11852:
        raise RuntimeError("Hebrew inventory denominator changed")
    if len(aramaic) != 2176 or len({item["family_id"] for item in aramaic}) != 1573:
        raise RuntimeError("Aramaic inventory denominator changed")

    trace = sum(item["nucleus_layer"]["outcome"] == "NUCLEUS-TRACE" for item in hebrew_issued)
    echo = sum(item["nucleus_layer"]["outcome"] == "NUCLEUS-ECHO" for item in hebrew_issued)
    marker = "HEBREW-NUCLEUS-EYE-OPERATION-FINAL-AUDIT"
    report = (
        "## تدقيق نفاد عملية العبرية بعين النواة (2026-08-01)\n\n"
        "- الرقم الأول، الصلات النووية العبرية الجديدة في العملية: 125.\n"
        "- الرقم الثاني، الإغلاقات الجديدة: 0.\n"
        f"- الحصيلة النهائية: صلات النواة العبرية={len(hebrew_issued)}؛ NUCLEUS-TRACE={trace}؛ NUCLEUS-ECHO={echo}. "
        "كان العد المؤقت 200، ثم سُحب حكم قديم واحد في `הראה` لأن `رأ` لا يملك مرشحا مطابقا مرخصا للعضو؛ صار LAW-GAP مفتوحا ولم يخترع بديل.\n"
        f"- إصلاح الآرامية: {len(repaired)} بطاقة مصححة؛ صلات النواة الآرامية بقيت {len(aramaic_issued)}.\n"
        f"- التغطية العبرية: {len(hebrew)} عضوا في {len({item['family_id'] for item in hebrew})} أسرة؛ لكل عضو حكم جذر وحكم نواة في `lane_a_coverage.jsonl`.\n"
        f"- التغطية الآرامية: {len(aramaic)} عضوا في {len({item['family_id'] for item in aramaic})} أسرة؛ لا عضو مفقود من المقام.\n"
        f"- العرق الباقي: {len(root_open)} عضوا عبريا له حكم جذري موجب ونواة مفتوحة؛ بقيت صفوفه ظاهرة ولم تتحول إلى NO-TRACE أو إغلاق بغياب الدليل.\n"
        "- بوابات الإصدار النهائية: كل صلة موجبة عبرية وآرامية تحمل مصدرين قديمين مستقلين مسميين، ولا تحمل تصنيف اتجاه، وتطابق مرشحا نوويا مرخصا غير route في سجل العضو.\n"
        "- سطر الموضع: نفد جرد العبرية كاملا من سطر Kaikki 0 إلى 17033؛ موضع هذه العملية عرق ROOT-positive/NUCLEUS-open عبر الجرد، لا شريحة متجاورة.\n"
        "- ملف `data/juthoor-core-levels.json` بقي طبقة بحث مجمدة ولم يعدل؛ لم يضف صف صوتي."
    )
    wrapped = f"<!-- {marker}:BEGIN -->\n\n{report}\n\n<!-- {marker}:END -->"
    append_once(HEBREW_READING, f"<!-- {marker}:BEGIN -->", wrapped)
    audit = AUDITS / "lane-a-hebrew-nucleus-eye-operation-audit.md"
    if audit.exists():
        raise RuntimeError(f"audit already exists: {audit}")
    audit.write_text(report + "\n", encoding="utf-8")
    return {
        "new": 125,
        "closures": 0,
        "hebrew_total": len(hebrew_issued),
        "aramaic_repaired": len(repaired),
        "withdrawn_old_sound_issue": 1,
        "root_positive_nucleus_open": len(root_open),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("target", choices=["aramaic-repair", "final-audit", *HEBREW_BATCHES])
    args = parser.parse_args()
    if args.target == "aramaic-repair":
        result = apply_aramaic_repairs()
    elif args.target == "final-audit":
        result = apply_final_audit()
    else:
        result = apply_hebrew(args.target)
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
