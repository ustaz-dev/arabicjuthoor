# -*- coding: utf-8 -*-
"""Round-three ruled cards for lane C (Hebrew, then exhausted Aramaic).

The work order fixes the sampling frame: take the next non-duplicate ``both``
rows in descending overlap order, while holding each reading file in memory.
This script keeps the hand decisions beside the mechanical retrieval so the
batch can be reproduced and audited without copying whole dictionary entries.
"""
from __future__ import annotations

import argparse
import collections
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import build_kaikki_index as LEX  # noqa: E402
import fan_any_script as FAN  # noqa: E402
import frozen_event as FE  # noqa: E402
import search_arabic_root_senses as AR  # noqa: E402

EXPLORATION = ROOT / "04-cross-linguistic" / "exploration"
READINGS = ROOT / "04-cross-linguistic" / "readings"
HEBREW = READINGS / "hebrew.md"
ARAMAIC = READINGS / "aramaic.md"
MAX_CARD_BYTES = 5 * 1024
MARKER = "LANE-C-HEBREW-ROUND3-2026-08-16"


@dataclass(frozen=True)
class Decision:
    candidate: str
    verdict: str
    keywords: tuple[str, ...]
    orbit: str
    state: str | None = None


R = "ROOT-TRACE"
O = "OPEN-CANDIDATE"
S = "SEMITIC-SOURCE-TRANSMISSION"


def d(candidate: str, verdict: str, keywords: str, orbit: str,
      state: str | None = None) -> Decision:
    values = (keywords.split("|") if "|" in keywords else keywords.split())
    return Decision(candidate, verdict, tuple(value.strip() for value in values), orbit, state)


# These are semantic readings, not machine classifications.  Their order is
# exactly the 100-row non-duplicate window asserted in select_rows().
DECISIONS: list[Decision] = [
    d("وحد", R, "الواحد وحدة منفرد", "الوحدة في الفرع واتحاد الشيء وانفراده واحدًا في العربية يصفان مدارًا واحدًا."),
    d("ردد", O, "ردد رد", "الضحالة وقلة العمق في الفرع لا تلتقيان رد الشيء وإعادته في شواهد العربية؛ رجل المعنى غائبة."),
    d("سبع", R, "سابع|سبعة", "الفرع يصنع ألفاظ العدد سبعة، والعربية تسمي العدد نفسه؛ حُصر الحكم في حس العدد دون الشبع أو القسم."),
    d("بند", O, "بند", "الباندا حيوان بعينه، ولا تسمي شواهد بند العربية هذا الحيوان؛ التشابه الصوتي بلا مدار معجمي."),
    d("ملح", R, "الملح مملحة", "المملحة وعاء للملح، والملح هو المادة المسماة في العربية؛ الاشتقاق من الشيء إلى وعائه مباشر."),
    d("وب", O, "وب", "الجمال والاستحسان في الفرع لا يجدان حسًا مطابقًا في شواهد وب العربية؛ فلا يُنشأ المدار من لفظ التعجب العام."),
    d("خطأ", R, "أخطأ الخطأ الرامي الغرض", "إخطاء العلامة والوقوع في الذنب في الفرع يلتقيان الخطأ ومجاوزة الصواب في العربية؛ حس التطهير مفصول."),
    d("عل", O, "عل", "الصورة ضمير ملحق بحرف الجر «على»، وشواهد عل لا تثبت هذا الاستعمال التركيبي نفسه؛ رجل المعنى المعجمي غائبة."),
    d("ترجم", R, "ترجمة مترجم نقل", "الترجمة في الطرفين نقل الكلام من لسان إلى لسان؛ والحكم لنتيجة النقل لا لاسم الترجوم وحده."),
    d("ترجم", R, "ترجمة مترجم نقل", "فعل الفرع «يترجم» وفعل العربية في الشواهد يصفان نقل الكلام نفسه."),
    d("خردل", R, "الخردل|ضرب من الحرف|معروف", "الخردل في الفرع والعربية اسم للنبات أو حبه نفسه؛ اختلاف الأصل النهائي المذكور في الحاشية لا يضيف بوابة."),
    d("فلسف", R, "فلسفة فيلسوف", "الفيلسوف في الفرع هو صاحب الفلسفة التي تسميها العربية من مادة فلسف؛ حُصر الحكم في هذا الاصطلاح."),
    d("تلمذ", O, "تلميذ المتعلم", "التعليم والتلمذة يلتقيان معنى، لكن ד↔ذ لا يملك هنا طريق المصدر المسمى الذي يشترطه DENT-03؛ رجل الصوت ناقصة.", "LAW-GAP"),
    d("كرفس", R, "كرفس", "الكرفس في المدخل النباتي وفي العربية اسم للنبات نفسه؛ مدخل النسيج المتجانس مفصول."),
    d("هندس", R, "المهندس|مقدر لمجاري|الهندسة", "النعت العبري متعلق بالهندسة، والعربية تسمي العلم والصنعة نفسيهما؛ المدار اشتقاق صفة من اسم المجال."),
    d("ودد", R, "الود محبة وديد", "الصديق المحبوب في الفرع يلتقي الود والمحبة في العربية، لا مجرد عموم الصحبة."),
    d("سمر", O, "سمر", "الحراسة والحفظ في معنى الصف لا يلتقيان السمر وحديث الليل في العربية؛ وفُصل متجانس الشمر النباتي."),
    d("سرف", R, "التبذير|الإسراف|النفقة", "استعمال الشيء حتى النفاد والهدر في الفرع يلتقي السرف ومجاوزة القصد في العربية؛ حس الإحراق وحده لا يرث الحكم."),
    d("صرح", R, "الصرح قصر بناء", "البرج والبناء المرتفع في الفرع يلتقيان الصرح بوصفه بناء ظاهرًا عاليًا في العربية."),
    d("جلح", R, "أجلح الشعر الرأس", "قصة الشعر المحلوقة في الفرع تلتقي انحسار الشعر والجلح في العربية؛ حس الكاهن لا يدخل إلا من طريق قصة الشعر."),
    d("هلل", R, "لا إله التوحيد", "صيغة «سبحوا الرب» في الفرع فعل ثناء، والتهليل في العربية رفع الصوت بالذكر؛ مدار الثناء المعلن مباشر."),
    d("خذل", "ABBREVIATION", "خذل", "الرسم اختصار لعبارة «حكماؤنا رحمهم الذكر» وليس عضوًا معجميًا من جذر خذل؛ يُعزل الاختصار قبل المقارنة.", "ABBREVIATION"),
    d("ثلث", R, "ثالث ثلاثة", "الثالث في الفرع ورتبة الثالث في العربية موضع واحد في سلسلة العدد."),
    d("خمس", R, "خامس خمسة", "الخامس في الفرع هو رتبة العدد خمسة التي تثبتها العربية."),
    d("نقب", O, "نقب", "الأنثى والجنس المؤنث في الفرع لا تسميهما شواهد نقب العربية؛ تفسير الصورة الجنسية اشتقاق داخلي لا يكفي مدارًا."),
    d("شقف", O, "شقف شقفة", "شريحة العرض الشفافة ليست شقفة أو كسرة في الشواهد العربية؛ اشتراك «قطعة» الإنجليزي أعم من المدار."),
    d("غلم", R, "غلام شاب", "المرأة الشابة في الفرع والغلام والشباب في العربية يلتقيان سن الحداثة؛ اختلاف الجنس النحوي مسجل ولا يبدل المدار."),
    d("سبع", R, "سابع سبعة", "السابع في الفرع هو رتبة العدد سبعة نفسها في العربية."),
    d("بحر", O, "بحر", "الفتاة البالغة في الفرع لا تلتقي البحر أو سعته في العربية؛ كلمة female المشتركة لا تنشئ صلة."),
    d("دلق", R, "النمس مقرض دويبة", "اسم حيوان الدلق في مدخل الفرع يطابق اسم الدلق الحيواني في العربية؛ حسا الوقود والفعل مفصولان."),
    d("بنت", O, "بنت", "النسبة إلى فنلندا مع التأنيث لا تجعل المرأة الفنلندية بنتًا معجميًا؛ الجنس وحده تغطية عامة لا مدار."),
    d("خمس", R, "خمسة الخمسة", "الصيغة الكتابية الناقصة في الفرع ما زالت اسم العدد خمسة نفسه في العربية."),
    d("ثمن", R, "ثمانية ثمان", "العدد ثمانية في الفرع والعربية واحد؛ حُصر الحكم في العدد دون معنى السعر."),
    d("عشر", R, "عشرة العشرة", "العشرة في الفرع والعربية اسم للعدد نفسه."),
    d("فرع", O, "فرع", "اسم فرعون المنقول من المصرية لا يساوي الفرع العربي معنى؛ قول الأصل المصري حاشية لا يغلق بطاقة بلا مانح سامي."),
    d("جلد", S, "جليد الجامد البرد", "المدخل يسمي الآرامية مانحًا للصورة العبرية الدالة على المثلجات، والعربية تثبت الجليد؛ لذلك يعزل النقل السامي من دعوى الإرث."),
    d("فتح", R, "مفتوح فتح الباب", "المفتوح غير المغلق في الفرع هو المفتوح في العربية؛ المدار نقيض الإغلاق مباشرة."),
    d("حنك", O, "حنك", "التدشين والتكريس في الفرع لا يلتقيان الحنك أو الخبرة في العربية؛ اسم العيد لا يسد رجل المعنى."),
    d("رجح", O, "رجح", "اللحظة القصيرة وطلب الانتظار لا يلتقيان رجحان الشيء ووزنه في العربية؛ وفوق ذلك لا صف مسمى لـע↔ح.", "LAW-GAP"),
    d("نغم", R, "حسن الصوت|جرس الكلمة|النغمة", "اللحن في الفرع هو النغمة المؤلفة في العربية؛ المدار صوت موسيقي منظم."),
    d("سكن", R, "سكنى مسكن الإقامة", "الحي مجموعة مساكن متجاورة، والسكن في العربية الإقامة والمسكن؛ المدار من الفعل إلى موضع الجماعة."),
    d("ورد", O, "ورد", "النزول والهبوط في الفرع لا يلتقيان الورود أو الوصول إلى الماء في العربية؛ الاتجاه المكاني مختلف."),
    d("نمل", R, "النمل معروف|دويبة|حشرة", "النملة في الفرع والعربية اسم للحشرة نفسها."),
    d("مطر", O, "مطر", "الهدف والغاية في الفرع لا يلتقيان المطر في العربية؛ كلمة cause المشتركة عامة ولا تقوم مقام المدار."),
    d("برك", R, "بركة الخير النماء", "البركة والتهنئة في الفرع تلتقيان البركة والنماء والخير في العربية؛ حس الحوض المتجانس مفصول."),
    d("نسم", R, "نسمة نفس الروح", "النفس الواحد في الفرع يلتقي النسمة ونفس الروح في العربية."),
    d("عنب", R, "عنبة العنب الثمر", "العنبة في الفرع والعربية ثمرة العنب نفسها، والـberry الأعم لا يورث الحكم لسائر الثمار."),
    d("طحل", R, "طحال الطحال", "الطحال في الفرع والعربية العضو الجسدي نفسه."),
    d("سفد", R, "حديدة|يشوى به اللحم|السفود", "السفود في العربية سيخ الشواء، وهو الـskewer نفسه في الفرع؛ الحكم للأداة لا لسائر معاني الجذر."),
    d("قبر", R, "القبر دفن الميت", "الدفن في الفرع فعل وضع الميت في القبر الذي تصفه العربية؛ مدار الفعل وموضعه مباشر."),
    d("سكر", R, "الحلوى", "الحلوى في الفرع مصنوعة من السكر الذي تسميه العربية؛ المدار من المادة إلى القطعة المصنوعة منها."),
    d("مسح", R, "ممسوح بالدهن|الدهن|الزيت", "الدهن بالزيت في الفرع نوع من المسح والإمرار على الجسد في العربية؛ حُصر الحكم في فعل الدهن."),
    d("طبخ", R, "طباخ الطبخ", "حس الطباخ في مدخل الفرع يطابق الطباخ والطبخ في العربية؛ الذبح والمجزرة متجانسان لا يرثان الحكم."),
    d("حبس", O, "حبس", "الحرية وعدم السجن في الفرع نقيض الحبس في العربية؛ التضاد لا يحقق معنى واحدًا."),
    d("طعم", R, "ما يؤديه الذوق|حلو الطعم|ذاق", "اللذيذ ذو الطعم المحبوب في الفرع يلتقي الذوق والطعم في العربية؛ المدار خاص بحاسة الذوق."),
    d("حجر", O, "حجر", "الحزام في الفرع لا يلتقي الحجر أو الحجرة في العربية؛ الإحاطة الوصفية وحدها لا تكفي."),
    d("سبح", R, "تسبيح التنزيه الثناء", "الثناء في الفرع يلتقي التسبيح والتنزيه والثناء في العربية؛ حس زيادة القيمة مفصول."),
    d("سمر", O, "سمر", "الحارس والحافظ في حس الصف لا يلتقيان السمر في العربية؛ متجانسا الشمر النباتي وسومر مفصولان."),
    d("حلب", R, "الحلبة|حب معروف|الفريقة", "الحلبة في الفرع والعربية اسم للنبات نفسه؛ لا يُنقل الحكم إلى فعل استخراج اللبن."),
    d("جزر", R, "carrot المأكول أرومة", "الجزر في حس النبات في الفرع والعربية اسم للخضرة نفسها؛ فعلا القطع والجزر البحري مفصولان."),
    d("قلد", S, "إقليد المفتاح", "قاموس الفرع يسمّي الآرامية طريقًا للصورة الدالة على المفتاح، وشواهد العربية تثبت الإقليد؛ فيغلق النقل السامي دون دعوى إرث."),
    d("نقم", R, "النقمة|المكافأة بالعقوبة|انتقام", "الانتقام في الفرع هو النقمة وطلب الجزاء في العربية."),
    d("يشب", O, "اليشب حجر جوهر", "قاموس الفرع يسمي اليشب حجرًا، لكن مروحة العربية أعادت شاهد معنى واحدًا فقط والثاني يقول إن المادة مهملة؛ رجل المصدر العربي ناقصة.", "SOURCE-GAP"),
    d("برز", O, "برز بروز", "اختراق الحاجز والبروز يلتقيان معنى، لكن צ↔ز غير مسمى في الشبكة بعد البحث بالحرفين وباسم العبرية؛ رجل الصوت ناقصة.", "LAW-GAP"),
    d("فطس", O, "فطس", "المطرقة في الفرع لا تسميها شواهد فطس العربية؛ أثر التسطيح المحتمل نتيجة للأداة لا اسمًا لها."),
    d("نخر", R, "منخر منخار الأنف", "المنخر في العربية فتحة الأنف، وهو الـnostril نفسه في الفرع؛ اختير نخر من كامل المروحة بدل نحر الأعلى وزنًا."),
    d("كنس", R, "متعبد اليهود|النصارى|كنيسة اليهود", "الكنيسة في حس المدخل العبري تقابل الكنيسة المسماة في العربية؛ معنى التجمع يفسر المدار ولا يورث سائر الكنس."),
    d("غرل", R, "غرلة القلفة أغرل", "الغرلة في العربية هي القلفة، وهي الـforeskin نفسه في الفرع؛ حس ثمر السنوات الثلاث مفصول."),
    d("طفل", S, "طفيلي متطفل التطفيل", "قاموس الفرع ينص أن اللفظ الحديث صيغ على العربية «طفيل»، وهي مادة الطفيلي؛ لذلك الحكم نقل سامي مسمى."),
    d("وعل", R, "تيس الجبل|الأروى", "الوعل في الفرع والعربية اسم لحيوان الجبل نفسه."),
    d("نمص", O, "نمص", "الوجود والعثور في الفرع لا يلتقيان النمص وإزالة الشعر في العربية."),
    d("نفخ", R, "منفوخ انتفخ الهواء", "المنتفخ المملوء بالهواء في الفرع يلتقي النفخ وإدخال الهواء في العربية؛ المجاز المتكبر مفصول."),
    d("زمن", R, "زمان الوقت الزمن", "الزمن والوقت في الفرع والعربية مدار واحد؛ حس الدعوة والترتيب مفصول."),
    d("قدم", R, "تقدم أمام السابق", "المتقدم الواقع في الأمام في الفرع يلتقي القدم والتقدم والسبق في العربية؛ الحكم لحس الأمام."),
    d("فتح", O, "فتح", "المدخل اسم حديث لحركة سياسية، وشواهد فتح القديمة تثبت الفعل لا الاسم الخاص؛ يلزم مصدر عربي يسمي العلم نفسه.", "SOURCE-GAP"),
    d("حمض", R, "حامض حموضة الحمض", "الحمض في الفرع والعربية مادة حامضة؛ المدار الكيميائي والحسي واحد في هذا العضو."),
    d("قرب", R, "القربى|القرابة|الدنو في النسب", "القريبة الأنثى عضو من القرابة، والعربية تسمي القربى والقرابة؛ حس القصيدة المتجانس مفصول."),
    d("ظرف", O, "ظرف", "الطعام المحرم أو الفريسة في الفرع لا يلتقيان الظرف في العربية، كما أن DENT-08 المشروط لا تتحقق شروطه هنا."),
    d("شبك", R, "شبكة اشتبك تشابك", "التعقيد في الفرع تشابك عناصر يصعب فصلها، والشبك في العربية إدخال بعضها في بعض؛ المدار بنيوي مباشر."),
    d("شبك", R, "شبكة اشتبك تشابك", "الجذر العبري يصنع ألفاظ التعقيد، والشبك العربي يصف تداخل الأجزاء؛ المدار هو التشابك المولد للتعقيد."),
    d("رشش", R, "رش رشه قطر", "الرش في الفرع والعربية نثر السائل قطرات دقيقة؛ الفعل واحد."),
    d("كلم", O, "كلم كلام", "ضمير «أي شيء» وأداة السؤال في الفرع لا يلتقيان الكلام أو الجرح في العربية."),
    d("شبر", O, "شبر", "البوق الطقسي وقرن الحيوان في الفرع لا يلتقيان الشبر بوصفه قياسًا في العربية؛ حاشية الأصل الأكادي لا تسمي مانحًا ساميًا مباشرًا للفرع."),
    d("عرق", R, "عروق الشجر الجسد الشريان الوريد", "الشريان وعِرق الورقة والعِرق المعدني في الفرع تلتقي عروق الجسد والنبات والمعدن في العربية."),
    d("يتم", R, "انقطاع الصبي عن أبيه|مات أبوه|فقد الأب", "اليتيم في الفرع والعربية من فقد أحد والديه أو سنده؛ المدار واحد."),
    d("وتر", O, "وتر", "قاموس الفرع يحلل الصورة تصريفًا من ראה «رأى» لا من هيكل ותר؛ مروحة وتر مبنية على تعرية صرفية خاطئة.", "MORPHOLOGY-GAP"),
    d("اخت", R, "أخت الأخت", "بعد نزع ضمير الملكية، الأخت في الفرع والعربية اسم لقريبة النسب نفسها."),
    d("دنر", R, "دينار دنانير", "الدينار في الفرع والعربية اسم لوحدة النقد نفسها؛ الحكم للاسم النقدي لا لمادة أخرى."),
    d("سرق", O, "سرق سرقة", "الصفير في الفرع لا يلتقي السرقة في العربية؛ اشتراك كلمة act الإنجليزية أعم من المدار."),
    d("حمض", R, "حامض حموضة الحمض", "الحساء المسمى في الفرع موصوف بالحموضة والقشدة الحامضة، والعربية تسمي الطعم الحامض؛ الحكم لحس الحموضة الذي قامت عليه التسمية."),
    d("ثكل", R, "ثكلى فقد الولد", "فقد الولد في الفرع هو الثكل في العربية؛ المدار مباشر ومحصول على حس الفقد وحده."),
    d("ثلث", R, "صاروا ثلاثة|ثلاثة", "الثلاثة في الفرع والعربية اسم للعدد نفسه."),
    d("كلب", O, "كلب", "مقطع الفيديو الموسيقي قرض من الإنجليزية clip، ولا يلتقي الكلب في العربية؛ التشابه الهيكلي عرضي."),
    d("نكب", S, "نكبة النكبات كارثة", "قاموس الفرع ينص أن الاسم من العربية «نكبة»، ومعنى الكارثة محفوظ؛ فيغلق النقل العربي المسمى."),
    d("خرس", O, "خرس أخرس", "الصمم وعدم السمع في الفرع لا يساوي الخرس وعدم النطق في العربية؛ التقارب في باب العجز الحسي أعم من المدار."),
    d("سفر", R, "السفر الكتاب|الكتاب الكبير|أسفار", "القصة والحكاية في الفرع سجل للأحداث، والسِفر في العربية كتاب مكتوب؛ المدار هو الخبر المثبت في سجل، لا السفر المكاني."),
    d("ثمن", R, "ثامن ثمانية", "الثامن في الفرع رتبة العدد ثمانية نفسها في العربية؛ حس السعر مفصول."),
    d("عشر", R, "عاشر عشرة", "العاشر في الفرع رتبة العدد عشرة نفسها في العربية."),
    d("فطر", R, "الفطر كمأة نبات", "الفطر في الفرع والعربية اسم لجنس المشروم؛ المعاني الأخرى للمادة مفصولة."),
    d("حبب", S, "الحب المحبة|محبوب|التحبب", "قاموس الفرع يصرح أن «حبيبي» مقترض من العربية، ومعنى التحبب محفوظ؛ لذلك الإغلاق نقل سامي مسمى."),
]


PAIR_ROWS: dict[tuple[str, str], str] = {
    ("א", "ء"): "IDN-16", ("א", "ا"): "IDN-16",
    ("ב", "ب"): "IDN-05", ("ג", "ج"): "IDN-08",
    ("ד", "د"): "IDN-09", ("ד", "ذ"): "DENT-03",
    ("ה", "ه"): "IDN-20", ("ו", "و"): "IDN-10",
    ("ז", "ز"): "IDN-22", ("ז", "ذ"): "DENT-04",
    ("ח", "ح"): "IDN-14/SEM-04", ("ח", "خ"): "SEM-05",
    ("ט", "ط"): "IDN-18", ("ט", "ظ"): "DENT-08 (مشروط)",
    ("י", "ي"): "IDN-23", ("י", "و"): "GLD-01",
    ("כ", "ك"): "IDN-13", ("ל", "ل"): "IDN-04",
    ("מ", "م"): "IDN-02", ("נ", "ن"): "IDN-03",
    ("ס", "س"): "IDN-07", ("ס", "ش"): "SIB-07",
    ("ע", "ع"): "SEM-03/IDN-15", ("ע", "غ"): "SEM-02",
    ("פ", "ف"): "LAB-07/IDN-06", ("פ", "ب"): "LAB-01",
    ("צ", "ص"): "IDN-19", ("צ", "ض"): "SEM-01",
    ("צ", "ظ"): "DENT-08 (مشروط)",
    ("ק", "ق"): "IDN-12", ("ק", "ك"): "IDN-12",
    ("ר", "ر"): "IDN-01",
    ("ש", "ش"): "IDN-21", ("ש", "س"): "SIB-01", ("ש", "ث"): "DENT-02",
    ("ת", "ت"): "IDN-11",
}


def load_rows(language: str) -> list[dict]:
    path = EXPLORATION / f"phonetic-sweep-{language}.json"
    return json.loads(path.read_text(encoding="utf-8"))["both"]


def nonduplicates(language: str) -> list[tuple[int, dict]]:
    """Hold the reading file once and update that in-memory text per selection."""
    path = READINGS / f"{language}.md"
    memory = path.read_text(encoding="utf-8")
    selected: list[tuple[int, dict]] = []
    for index, row in enumerate(load_rows(language)):
        branch = str(row["branch"])
        if branch in memory:
            continue
        selected.append((index, row))
        memory += "\n" + branch
    return selected


def select_rows() -> tuple[list[tuple[int, dict]], list[tuple[int, dict]]]:
    hebrew = nonduplicates("hebrew")
    aramaic = nonduplicates("aramaic")
    chosen = hebrew[:100]
    assert len(DECISIONS) == 100
    assert len(chosen) == 100
    assert chosen[0][0] == 391 and chosen[-1][0] == 715
    assert chosen[49][0] == 552 and chosen[50][0] == 557
    assert not aramaic, f"Aramaic inventory changed: {aramaic[:3]}"
    return chosen, aramaic


def english_tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z]{3,}", text.casefold()))


def choose_lexicon_entry(row: dict) -> tuple[dict, list[dict], str]:
    hits, how = LEX.look("hebrew", str(row["branch"]))
    assert hits, f"No Hebrew lexicon entry for {row['branch']}"
    wanted = english_tokens(str(row.get("gloss") or ""))
    wanted.update(english_tokens(" ".join(row.get("shared") or [])))
    chosen = max(hits, key=lambda hit: (
        len(wanted & english_tokens(str(hit.get("en") or ""))),
        -hits.index(hit),
    ))
    return chosen, hits, how


def folded_arabic(value: str) -> str:
    return AR.ARABIC_MARKS.sub("", value)


def selected_witnesses(matches: list[dict], keywords: tuple[str, ...]) -> list[dict]:
    by_source: dict[str, list[dict]] = collections.defaultdict(list)
    for item in matches:
        source_id = AR.canonical_source_id(str(item.get("source") or ""))
        if source_id:
            by_source[source_id].append(item)
    ranked_sources: list[tuple[int, int, int, str, dict]] = []
    for priority, source_id in enumerate(AR.SOURCE_PRIORITY):
        items = by_source.get(source_id) or []
        if not items:
            continue
        item = max(items, key=lambda value: (
            sum(folded_arabic(str(value.get("definition") or "")).count(folded_arabic(k))
                for k in keywords),
            len(str(value.get("definition") or "")),
        ))
        folded = folded_arabic(str(item.get("definition") or ""))
        counts = [folded.count(folded_arabic(k)) for k in keywords]
        distinct = sum(value > 0 for value in counts)
        total = sum(counts)
        ranked_sources.append((-distinct, -total, priority, source_id, item))
    ranked_sources.sort()
    return [
        {**item, "source_label": AR.SOURCE_LABELS[source_id]}
        for _, _, _, source_id, item in ranked_sources[:2]
    ]


def excerpt(definition: str, keywords: tuple[str, ...], limit: int = 185) -> str:
    text = re.sub(r"\s+", " ", definition).strip()
    parts = [p.strip(" ،؛:") for p in re.split(r"(?<=[.!؟؛])\s+|\n+", text) if p.strip()]
    ranked = sorted(parts, key=lambda part: (
        -sum(folded_arabic(k) in folded_arabic(part) for k in keywords),
        len(part),
    ))
    part = ranked[0] if ranked else text
    if len(part) <= limit:
        return part
    # Match through vocalization while preserving the exact quoted spelling.
    chars: list[str] = []
    original_positions: list[int] = []
    for original_index, char in enumerate(part):
        if AR.ARABIC_MARKS.fullmatch(char):
            continue
        chars.append(char)
        original_positions.append(original_index)
    folded_part = "".join(chars)
    folded_positions = [
        (len(folded_arabic(k)), folded_part.find(folded_arabic(k)))
        for k in keywords if folded_part.find(folded_arabic(k)) >= 0
    ]
    # Prefer the longest, most specific semantic phrase over an earlier generic
    # occurrence of the headword in the same unpunctuated dictionary article.
    best_position = max(folded_positions, default=(0, 0))[1]
    positions = [original_positions[best_position]] if original_positions else [0]
    center = min(positions) if positions else 0
    left = max(0, center - limit // 3)
    right = min(len(part), left + limit)
    left = max(0, right - limit)
    clipped = part[left:right].strip(" ،؛:")
    return ("…" if left else "") + clipped + ("…" if right < len(part) else "")


def normalized_arabic_letters(candidate: str) -> list[str]:
    return [
        {"أ": "ء", "إ": "ء", "ؤ": "ء", "ئ": "ء"}.get(ch, ch)
        for ch in candidate if "ء" <= ch <= "ي"
    ]


def source_letters(row: dict, decision: Decision) -> list[str]:
    if row["branch"] == "ח־ט־א":
        return list("חטא")
    return list(str(row["skeleton"]))


def sound_path(row: dict, decision: Decision) -> str:
    src = source_letters(row, decision)
    dst = normalized_arabic_letters(decision.candidate)
    if row["branch"] == "תלמוד":
        return ("ת↔ت عبر IDN-11، وל↔ل عبر IDN-04، وמ↔م عبر IDN-02، "
                "وأما ד↔ذ فلا صف مباشر له؛ فُتشت الشبكة بالحرفين وباسم العبرية، "
                "وDENT-03 لا يعمل بلا طريق مصدر أكادي أو آرامي مسمى")
    if row["branch"] == "פורץ":
        return ("פ↔ب عبر LAB-01، وר↔ر عبر IDN-01، وأما צ↔ز فلا صف مسمى؛ "
                "فُتشت الشبكة بالحرفين وباسم العبرية قبل إعلان الفجوة")
    if row["branch"] == "רגע":
        return ("ר↔ر عبر IDN-01، وג↔ج عبر IDN-08، وأما ע↔ح فلا صف مسمى؛ "
                "فُتشت الشبكة بالحرفين وباسم العبرية قبل إعلان الفجوة")
    if len(src) != len(dst):
        return f"تعذر صفّ الهيكل {''.join(src)} على {decision.candidate} بعد التعرية؛ الفجوة مسماة في الحكم"
    steps = []
    for a, b in zip(src, dst):
        row_id = PAIR_ROWS.get((a, b))
        if not row_id:
            steps.append(f"{a}↔{b} بلا صف مسمى")
        else:
            steps.append(f"{a}↔{b} عبر {row_id}")
    return "، و".join(steps)


def event_for(candidate: str) -> tuple[FE.Ev, int, str]:
    tiers = FE.all_tiers(candidate)
    used = candidate
    if not tiers:
        used = candidate.translate(str.maketrans("أإؤئ", "ءءءء"))
        tiers = FE.all_tiers(used)
    assert tiers, f"No frozen event for {candidate}"
    return tiers[0], len(tiers), used


def render_card(serial: int, index: int, row: dict, decision: Decision,
                arabic_matches: dict[str, list[dict]]) -> str:
    entry, hits, how = choose_lexicon_entry(row)
    reading = str(entry.get("read") or "").strip() or str(row["say"]).split("  (")[0]
    gloss = re.sub(r"\s+", " ", str(entry.get("en") or row.get("gloss") or "")).strip()
    etym = re.sub(r"\s+", " ", str(entry.get("etym") or "")).strip()
    root = AR.normalize_root(decision.candidate)
    matches = arabic_matches.get(root, [])
    witnesses = selected_witnesses(matches, decision.keywords)
    witness_text = "؛ ".join(
        f"قال {item['source_label']}: «{excerpt(str(item.get('definition') or ''), decision.keywords)}»"
        for item in witnesses
    ) or "لم يرجع الفهرس شاهدًا عربيًا عاملًا"

    fans = FAN.fan(str(row["branch"]), "north")
    ranked = FAN.rank(str(row["branch"]), fans, "north", "hebrew")
    rank = next((n for n, (candidate, _) in enumerate(ranked, 1)
                 if candidate == decision.candidate), None)
    weight = next((weight for candidate, weight in ranked
                   if candidate == decision.candidate), 0.0)
    membership = (f"رتبته {rank} ووزنه {weight:.6f}"
                  if rank else "خارج المروحة الآلية؛ استعيد من التحليل الصرفي المكتوب في البطاقة")
    ev, tier_count, event_candidate = event_for(decision.candidate)
    event_note = (f"؛ طُبع حدث {event_candidate} بعد توحيد كرسي الهمزة"
                  if event_candidate != decision.candidate else "")

    if row["branch"] == "ותרא":
        zero = ("قاموس الفرع يثبت أنها صيغة مؤنث مفرد مع واو القلب من ראה «رأى»؛ "
                "لذلك الهيكل الآلي ותר ليس لبًا معجميًا صالحًا")
    elif row["branch"] == "עליי":
        zero = "نُزع ضمير المتكلم الملحق من עליי فرُدت إلى حرف الجر על؛ الهيكل المقارن על"
    elif row["branch"] == "אחתו":
        zero = "نُزع ضمير الملكية ו من الصورة الناقصة، وردت إلى אחת/אחות؛ الهيكل المقارن אחת"
    else:
        zero = (f"قُرئت بصرف الفرع وردت إلى الهيكل `{row['skeleton']}` كما في صف both؛ "
                "لم تُحسب الصوائت أو اللواحق التي طرحها مسح الشمال")

    earliest = (f"{etym} [قاموس الفرع، {len(hits)} مدخلة قُرئت كلّها، {how}]"
                if etym else
                f"لا يسمّي قاموس الفرع صورة أقدم ولا مانحًا [{len(hits)} مدخلة قُرئت كلّها، {how}]")
    shared = "، ".join(str(value) for value in row.get("shared") or []) or "لا لفظ مشترك حاكم"
    state = decision.state or ("READY" if decision.verdict == R else decision.verdict)
    if decision.verdict == R:
        filter_line = "اكتملت الأرجل الثلاث في الحس المختار؛ قول القاموس عن الأصل حاشية لا بوابة."
    elif decision.verdict == S:
        filter_line = "سمى قاموس الفرع مانحًا ساميًا في طريق الأخذ، فأغلق النقل السامي الموجب دون دعوى إرث."
    elif decision.verdict == "ABBREVIATION":
        filter_line = "الاختصار ليس جذرًا معجميًا؛ عُزل قبل أن يرث حكم خذل لمجرد الرسم."
    else:
        filter_line = decision.orbit

    card_id = f"WO-C-HEBREW-{3 if serial <= 50 else 4:03d}-{((serial - 1) % 50) + 1:03d}"
    lines = [
        f"### {card_id}: `{row['branch']}` /{reading}/ ↔ `{decision.candidate}`",
        "- إصدارُ البروتوكول: RECOVERY-v2 (2026-08-16).",
        f"- الكلمةُ في الفرع: عبريّة `{row['branch']}` /{reading}/.",
        f"- أقدمُ صورةٍ مستعادة: {earliest}.",
        f"- الخطوةُ صفر (التعرية بصرف الفرع): {zero}.",
        f"- درجةُ المقارنة: {'نواة ثنائية' if len(root) == 2 else 'جذر كامل'}.",
        (f"- مسحُ المعاني العربيّة: قُرئت {len(matches)} نتيجة للجذر `{root}` "
         f"بـ`--max-chars 0`؛ {witness_text}."),
        f"- المقابلُ من اللسان: `{decision.candidate}`؛ التغطية المشتركة في صف المسح: {shared}.",
        (f"- مسارُ الصوت: {sound_path(row, decision)}؛ قُرئت المروحة كاملة "
         f"({len(ranked)} مرشحًا)، والمنتخب {membership}."),
        (ev.line() + f"؛ عرضت `all_tiers` {tier_count} درجات واختيرت المعلنة{event_note}."),
        f"- المعنى من قاموس الفرع: «{gloss[:360]}» [المدخلة المختارة بالسياق بعد قراءة المتجانسات].",
        f"- المدار: {decision.orbit}",
        f"- المصفاة: {filter_line}",
        (f"- فصلُ المتجانسات والاقتراض: الحكم خاص بحس الصف ذي معنى «{gloss[:190]}»؛ "
         "لا يرثه متحد الرسم، ونسبة القاموس مذكورة في حاشية أقدم صورة."),
        f"- مؤشر اليتم: صف `both[{index}]`؛ التداخل {row['overlap']}؛ direct={str(bool(row['direct'])).lower()}.",
        f"- إشعاع الأسرة في الفرع: المداخل المقروءة={len(hits)}؛ المختار=1.",
        "- إشعاع الأسرة في العربية: [قُرئت المروحة كاملة ولم تُنسخ؛ شاهدان عاملان فقط أعلاه].",
        "- جسور الاسترداد المفحوصة: صرف الشمال؛ المروحة المرتبة؛ قاموس الفرع؛ شواهد العربية؛ صفوف الصوت؛ `all_tiers`؛ مصفاة النقل.",
        f"- حالةُ الإغلاق: {state}.",
        f"- الحكم (استكشاف): {decision.verdict}.",
        "- ملاحظات: عدسة الاسترداد قرأت المرشحات والمتجانسات، وعدسة التشكيك حصرت الحكم في الحس المكتوب ولم تضف شرطًا رابعًا.",
    ]
    card = "\n".join(lines) + "\n"
    size = len(card.encode("utf-8"))
    assert size <= MAX_CARD_BYTES, f"Card {card_id} is {size} bytes"
    return card


def render_batches() -> tuple[str, dict]:
    chosen, aramaic = select_rows()
    roots = {AR.normalize_root(decision.candidate) for decision in DECISIONS}
    arabic_matches = AR.matches_for_roots(AR.DEFAULT_RESOURCES, roots, None)
    cards = [
        render_card(serial, index, row, decision, arabic_matches)
        for serial, ((index, row), decision) in enumerate(zip(chosen, DECISIONS), 1)
    ]
    batches = []
    for batch_number, start in ((3, 0), (4, 50)):
        batch = cards[start:start + 50]
        batches += [
            f"## الدفعة العبرية {batch_number}: الجولة الثالثة من حوض both (2026-08-16)",
            "",
            ("الحالة: طبقة الاستكشاف؛ إلحاق فقط. اختيرت أول خمسين صورة غير مكررة "
             "من الذاكرة بترتيب `overlap` النازل، وكل بطاقة منتهية بحكم."),
            "",
        ]
        for offset, card in enumerate(batch, 1):
            batches.append(card.rstrip())
            batches.append("")
            if offset % 5 == 0:
                batches.append(
                    f"<!-- LANE-C-HEBREW-R3-B{batch_number}-CHUNK-{offset // 5:03d}:END -->")
                batches.append("")
    appendix = "\n".join(batches).rstrip() + f"\n\n<!-- {MARKER}:END -->\n"
    verdicts = collections.Counter(decision.verdict for decision in DECISIONS)
    states = collections.Counter(
        decision.state or ("READY" if decision.verdict == R else decision.verdict)
        for decision in DECISIONS
    )
    diagnostics = {
        "hebrew_remaining_before": len(nonduplicates("hebrew")),
        "aramaic_remaining": len(aramaic),
        "first": chosen[0][0],
        "batch1_last": chosen[49][0],
        "batch2_first": chosen[50][0],
        "last": chosen[-1][0],
        "verdicts": dict(sorted(verdicts.items())),
        "states": dict(sorted(states.items())),
        "appendix_bytes": len(appendix.encode("utf-8")),
        "max_card_bytes": max(len(card.encode("utf-8")) for card in cards),
    }
    return appendix, diagnostics


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--show", type=int, choices=range(1, 101))
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    appendix, diagnostics = render_batches()
    print(json.dumps(diagnostics, ensure_ascii=False, indent=2))
    if args.show:
        cards = re.split(r"(?=^### WO-C-HEBREW-)", appendix, flags=re.M)
        card = next(value for value in cards if value.startswith(
            f"### WO-C-HEBREW-{3 if args.show <= 50 else 4:03d}-{((args.show - 1) % 50) + 1:03d}"))
        print("\n" + card.split("\n<!--", 1)[0].rstrip())
    if args.apply:
        current = HEBREW.read_text(encoding="utf-8")
        if MARKER in current:
            raise SystemExit("Round-three marker already exists; append refused.")
        with HEBREW.open("a", encoding="utf-8", newline="\n") as handle:
            if not current.endswith("\n"):
                handle.write("\n")
            handle.write("\n" + appendix)
        print(f"APPENDED: {HEBREW.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
