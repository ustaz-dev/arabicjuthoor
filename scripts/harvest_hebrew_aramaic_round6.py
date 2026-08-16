# -*- coding: utf-8 -*-
"""Round-six completion of lane C: remaining Hebrew, then Aramaic scan.

The Hebrew frame is every non-duplicate row left after round five.  The
Aramaic pool is reloaded and checked once in memory after Hebrew selection.
This writer appends cards and the lane report only; it never ships or commits.
"""
from __future__ import annotations

import argparse
import collections
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import harvest_hebrew_aramaic_round5 as R5


R3 = R5.R3
ROOT = Path(__file__).resolve().parents[1]
HEBREW = ROOT / "04-cross-linguistic" / "readings" / "hebrew.md"
ARAMAIC = ROOT / "04-cross-linguistic" / "readings" / "aramaic.md"
REPORT = ROOT / "_inbox" / "lane-reports" / "2026-08-16-C.md"
MARKER = "LANE-C-HEBREW-ROUND6-2026-08-17"
REPORT_MARKER = "LANE-C-REPORT-ROUND6-2026-08-17"

Decision = R3.Decision
R = R3.R
O = R3.O
S = R3.S
d = R3.d
LOAN = "LOANWORD"
ABBR = "ABBREVIATION"


# One hand ruling per row, in the exact order asserted by select_rows().
# The fan is a retrieval order only and never supplies a semantic verdict.
DECISIONS: list[Decision] = [
    d("حزا", R, "حزا تكهن حازي", "חזון اسم الرؤية المشتق من חזה «تنبأ ورأى»، والعربية تجعل حزا التكهن والنظر للاستدلال؛ المدار من فعل الاستشراف إلى الرؤية المستشرفة."),
    d("فشل", O, "فشل ضعف جبن", "البطلان وعدم القبول في الفرع لا يساويان الفشل العربي القديم الذي تسميه الشواهد ضعفًا وجبنًا وتراخيًا؛ التشابه الحديث لا ينسخ فرق المدار."),
    d("بطن", LOAN, "بطن جوف", "قاموس الفرع يصرح بأن photon من الإنجليزية؛ عُزل القرض الثالثي المصدر، ولم يرث بطن العربية من مجرد الهيكل.", "LOANWORD-THIRD-PARTY-TO-BRANCH"),
    d("سكن", O, "سكن مسكن إقامة", "الوكيل أو موظف الدار في الفرع لا يساوي السكن والإقامة في العربية؛ وجوده في دار لا يحول ظرف العمل إلى معنى الجذر."),
    d("اسف", O, "أسف حزن", "الجمع والحصاد في الفرع لا يلتقيان الأسف والحزن في العربية؛ رجل المعنى غائبة مع بقاء الصوت مفحوصًا."),
    d("فرش", O, "فرش بسط", "الحسون أو العصفور في الحس المختار لا تسميه شواهد فرش العربية؛ متجانسا التفسير والاعتزال في الفرع مفصولان كذلك."),
    d("صرف", O, "صرف الكلام تصريف", "العبارة في الفرع تركيب من كلمات، وصرف الكلام العربي تزيينه أو اشتقاق بعضه من بعض لا اسم العبارة نفسها؛ المجال اللغوي المشترك أوسع من المدار."),
    d("حفر", R, "حفر الحفيرة المحتفر", "الحفر والتنقيب في الفرع هما حفر الأرض وإخراج ترابها في العربية؛ الاسم المصدري لا يغير الجذر."),
    d("وشم", O, "وشم علامة", "التطبيق والتنفيذ في الفرع لا يساويان الوشم والعلامة في العربية؛ ولا يسمي قاموس الفرع اشتقاقًا يرد الصورة إلى وسم."),
    d("شطف", R, "شطف غسل", "الغسل في الفرع يطابق شطف الشيء وغسله في العربية؛ صفوف الصوت الثلاثة مسماة والحس مباشر."),
    d("كفر", R, "الكفر القرية", "الصفة الريفية في الفرع مشتقة من כפר «قرية»، والعربية تسمي القرية الصغيرة كفرًا؛ المدار من المكان إلى نسبته مباشر."),
    d("مثل", R, "المثل الأمثال", "سفر الأمثال في الفرع مجموعة أمثال وحكم، والمثل في العربية ما يضرب مثالًا؛ حُصر الحكم في اسم النوع لا في اسم العلم وحده."),
    d("عرر", O, "عرر", "التحريك والاعتراض والاحتجاج في الفرع لا تجد حسًا مطابقًا في شواهد عرر العربية؛ الأفعال السياسية لا تُستخرج من الهيكل وحده."),
    d("كبر", R, "الكبر العظمة العظم", "الطول والامتداد في الحس المختار مقدار من العظم، والعربية تسمي الكبر عظمة الشيء؛ فُصل متجانس الغربال العبري قبل الحكم."),
    d("اتن", O, "أتن", "אותנו تركيب من علامة المفعول את وضمير الجمع נו، لا جذر אתנ؛ الهيكل عبر حد الصرف ولذلك بقي الحكم مفتوحًا.", "MORPHOLOGY-GAP"),
    d("فا", O, "الفاء حرف", "الشعر المستعار ووجه المجسم وخصلة الصدغ في الفرع لا يلتقي أي منها اسم الفاء أو مادة فا العربية؛ تعدد الحواس لم يصنع مدارًا."),
    d("علا", R, "علا علو ارتفع", "الصعود والارتفاع في الفرع هما العلو والارتفاع في العربية؛ الاسم المصدري رد إلى עלה والنهاية الضعيفة خارج النواة عل."),
    d("رفأ", R, "رفأ أصلح لأم", "ترميم العمل الفني في الفرع يطابق رفأ الشيء وإصلاح ما وهى منه في العربية؛ الهمزة الجذرية مستعادة من الرسم الكامل."),
    d("حل", O, "حل", "حلقة السلسلة والفقرة في الفرع لا تسميهما شواهد حل العربية بهذا الضبط؛ تصور فك الحلقة لا يساوي اسم العضو."),
    d("عر", O, "عر", "البلدية في الفرع مشتقة من עיר «مدينة» وصيغت قياسًا على بلدية العربية، لكن عر العربية لا يحمل معنى المدينة؛ القياس الصرفي ليس نقلًا للصورة."),
    d("ولا", O, "ولا", "الصورة مؤلفة من ו «و» وלא «لا»؛ التقارب الوظيفي مع ولا العربية واعد، لكن صف both جمعهما هيكلًا جذريًا ولم يرجع فهرس الشواهد مادة مستقلة تغلق الحكم.", "MORPHOLOGY-GAP"),
    d("ار", O, "ار", "اسم برج الأسد موروث من اسم الحيوان *ʔarway في الفرع، ولا تسمي شواهد ار العربية الأسد أو البرج؛ العموم الحيواني في الشاهد الجعزي لا يملأ الرجل العربية."),
    d("عش", ABBR, "عش", "الرسم اختصار لعبارة ערב שבת «عشية السبت»، لا مدخلة من عش العربية؛ عُزل الاختصار قبل المقارنة.", "ABBREVIATION"),
    d("مص", R, "مص امتص مصاص", "العصير سائل مستخرج بالعصر، والمدخل العبري نفسه يرده إلى الضغط والعصر؛ العربية تجعل المص امتصاص السائل، فالمدار من الفعل إلى السائل المستخرج مباشر."),
    d("در", ABBR, "در", "الرسم اختصار للقب דוקטור، لا جذرًا عبريًا يقابل در العربية؛ عُزل الاختصار قبل أن يرث حكم الرسم.", "ABBREVIATION"),
    d("كن", O, "كن", "الاتجاه والتوجيه في الفرع من כון، ولا تسمي شواهد كن العربية الجهة أو فعل التوجيه؛ سقوط الواو من الهيكل لا ينشئ معنى."),
    d("رس", O, "رس", "اسم الروسي ونسبته علم حديث، وقاموس الفرع لا يسمي مانحًا أو طبقة تاريخية؛ لا تسمي مادة رس العربية روسيا.", "SOURCE-GAP"),
    d("عل", O, "على علو", "עליו هو על «على» مع ضمير الغائب، لكن بطاقة الجذر عل لا يثبتها فهرس العربية عضوًا معجميًا بالوظيفة نفسها؛ بقي حد الصرف ظاهرًا.", "MORPHOLOGY-GAP"),
    d("لف", O, "لف", "לפיו ردت إلى לפי «بحسب» مع ضمير الغائب، وهي مركب من لام وفم؛ الهيكل לפ يعبر حد كلمتين ولا يساوي لف العربية.", "MORPHOLOGY-GAP"),
    d("وص", O, "وص", "ויצא صيغة مصرفة من יצא مع واو العطف، وليست جذر וצ؛ الخروج في الفرع لا تسميه شواهد وص العربية.", "MORPHOLOGY-GAP"),
    d("سك", ABBR, "سك", "الرسم ראשי תיבות لعبارة סך הכול «المجموع»، لا نواة معجمية من سك العربية؛ عُزل الاختصار.", "ABBREVIATION"),
    d("جلا", R, "جلا كشف أظهر", "الكشف والاكتشاف في الفرع من גילה، والعربية تجعل جلا الأمر كشفه وأظهره؛ المصدر גילוי يحفظ هذا المدار."),
    d("لن", O, "لن", "اسم القمر الصناعي مشتق من לוה «رافق» مع لاحقة الاسم، ولا تسمي لن العربية المرافق أو التابع؛ الهيكل الآلي حذف الواو الأصلية.", "MORPHOLOGY-GAP"),
    d("رفأ", R, "رفأ أصلح لأم", "الشفاء والإصلاح في الفرع يلتقيان رفأ الشيء وإصلاح ما وهى منه في العربية، وقاموس الجذر يقارن العربية صراحة."),
    d("قوم", R, "قام قيام وجود دوام", "الوجود والدوام في الفرع من קיים/קום، والعربية تسمي القيوم القائم الذي يقوم به وجود كل موجود ودوامه؛ المدار مباشر."),
    d("قري", R, "القرية قرى بلد", "קריה مدينة أو بلدة من الجذر السامي qry/qrt، والقرية في العربية المصر والبلد؛ تاء أو هاء التأنيث خارج الجذر المقارن."),
    d("كهن", R, "كاهن الكهانة", "الكهنوت وجماعة الكهنة في الفرع من כהן، والعربية تسمي الكاهن وحرفته الكهانة؛ قاموس الفرع يسمي العربية في سلسلة الجذر."),
    d("ها", R, "الهاء حرف المعجم", "ה״א اسم حرف الهاء في الفرع، وها أو الهاء في العربية اسم الحرف نفسه؛ الحكم لاسم الحرف لا لأداة التنبيه المتجانسة."),
    d("كاف", R, "الكاف حرف الهجاء", "כ״ף اسم حرف الكاف في الفرع، والكاف في العربية الحرف نفسه؛ الألف في اسم الحرف صائت لا صامت جذر زائد."),
    d("قاف", R, "القاف حرف الهجاء", "קו״ף اسم حرف القاف في الفرع، والقاف في العربية حرف الهجاء نفسه؛ واو الرسم العبري وألف العربية صائتا اسم الحرف."),
    d("علا", R, "علا علو ارتفع", "التهجئة الناقصة من עלייה ما زالت اسم الصعود، وهو العلو والارتفاع في العربية؛ الحكم للحس الصرفي نفسه."),
    d("دج", O, "دج", "السمك في الفرع من דג، ولا تسمي شواهد دج العربية السمك؛ المروحة الصوتية لم تجد مادة معنى عاملة."),
    d("حدو", O, "حدا حدو", "الفرح والحيوية في الفرع مرتبطان بآرامية «فرح»، أما الحدو العربي فغناء سائق الإبل؛ الغناء قد يصاحب الفرح لكنه ليس معناه المعجمي نفسه."),
    d("ار", O, "ار", "الإسطبل في الفرع لا تسميه شواهد ار العربية، ولا يسمي قاموس الفرع صورة أقدم تفتح جسرًا؛ وظيفة إيواء الخيل ليست معنى المادة."),
    d("بهم", R, "الإبهام الإصبع الكبرى", "الإبهام في العربية الإصبع الكبرى، وهو إبهام اليد في الفرع؛ قاموس الفرع ينص أن בהן قد يكون نظير בהם، فاستعيد الميم من البديل المسمى."),
    d("خفي", O, "خفي ستر أخفى", "المغطى في الفرع يلتقي الخفي والمستور في العربية، لكن مقابلة الهاء الضعيفة في جذر חפה بالياء في خفي لا تملك صفًا مسمى في الشبكة؛ بقيت رجل الصوت مفتوحة.", "LAW-GAP"),
    d("حص", R, "حصة قطع قسم نصيب", "الجذر العبري يدل على القسمة إلى اثنين والفصل، والعربية تجعل الحصة قطعة من الجملة وتقول تحاص القوم أي اقتسموا؛ النواة حص محفوظة."),
    d("عر", O, "عر", "البلدة الصغيرة في الفرع مشتقة من עיר «مدينة»، ولا تسمي شواهد عر العربية مدينة أو بلدة؛ بقيت رجل المعنى غائبة."),
    d("روم", LOAN, "الروم رومي", "قاموس الفرع يرد רומי إلى اليونانية Ῥώμη، والعربية تسمي الروم، فالتطابق اسم ترحال ثالثي المصدر لا شاهد إرث.", "LOANWORD-THIRD-PARTY-TO-BRANCH"),
    d("بر", ABBR, "بر", "الرسم اختصار لصيغة تشريف أبوية تشير إلى أن الأب حاخام، لا عضوًا معجميًا من بر العربية؛ عُزل الاختصار.", "ABBREVIATION"),
    d("فا", R, "الفاء حرف هجاء", "פ״א اسم حرف pe في الفرع، والفاء العربية خلفه الصوتي المسمى عبر انتقال p إلى f؛ الحكم لاسم الحرف نفسه لا لمتجانس آخر."),
    d("شين", R, "الشين حرف هجاء", "שי״ן اسم حرف الشين في الفرع، والشين في العربية حرف الهجاء نفسه؛ الرسم والنطق والمعنى محفوظة."),
]


ORIGINAL_LOOKUP = R5.choose_lexicon_entry
ORIGINAL_SOUND_PATH = R5.sound_path


def choose_lexicon_entry(row: dict) -> tuple[dict, list[dict], str]:
    """Keep exact row senses when the punctuation-stripped index collides."""
    branch = str(row["branch"])
    if branch in {"אותנו", "ב״ר"}:
        pseudo = {
            "word": branch,
            "read": str(row["say"]).split("  (")[0],
            "pos": "pron" if branch == "אותנו" else "abbreviation",
            "en": row["gloss"],
            "etym": "",
        }
        return pseudo, [pseudo], "صف المسح محفوظ لأن فهرس الرسم المنزوع الترقيم خلط متجانسات"
    if branch == "לפיו":
        hits, how = R3.LEX.look("hebrew", branch)
        chosen = next(hit for hit in hits if hit.get("word") == "לפי")
        return chosen, hits, f"أقرب قاعدة صرفية؛ {how}"
    return ORIGINAL_LOOKUP(row)


SPECIAL_SOUND: dict[str, str] = {
    "חזון": "ח↔ح عبر IDN-14/SEM-04، وז↔ز عبر IDN-22؛ ردت صيغة חזון إلى חזה، والنهاية الضعيفة في حזה/حزا خارج النواة חז/حز",
    "עלייה": "ע↔ع عبر SEM-03/IDN-15، وל↔ل عبر IDN-04؛ رد المصدر إلى עלה، والنهاية الضعيفة في עלה/علا خارج النواة על/عل",
    "עליה": "ע↔ع عبر SEM-03/IDN-15، وל↔ل عبر IDN-04؛ التهجئة ناقصة من עלייה وردت إلى עלה، والنهاية الضعيفة خارج النواة",
    "רופא": "ר↔ر عبر IDN-01، وפ↔ف عبر LAB-07/IDN-06، وא↔ء عبر IDN-16؛ الهمزة استعيدت من سطح רופא ومن قاعدة רפא",
    "ריפא": "ר↔ر عبر IDN-01، وפ↔ف عبر LAB-07/IDN-06، وא↔ء عبر IDN-16؛ ياء الصيغة صائت والهمزة الأخيرة جذرية",
    "ולא": "ו↔و عبر IDN-10، وל↔ل عبر IDN-04، وא↔ا عبر IDN-16؛ المقابلة سطحية للمركب كله ولا تحوله إلى جذر",
    "גילוי": "ג↔ج عبر IDN-08، وל↔ل عبر IDN-04؛ رد المصدر إلى גילה، والنهاية الضعيفة في גלה/جلا خارج النواة גל/جل",
    "קיום": "ק↔ق عبر IDN-12، وו↔و عبر IDN-10، وמ↔م عبر IDN-02؛ استعيدت الواو الأصلية من קום ولم تحسب ياء الصيغة",
    "קריה": "ק↔ق عبر IDN-12، وר↔ر عبر IDN-01، وי↔ي عبر IDN-23؛ ה/ة نهاية اسمية خارج الجذر qry",
    "כהונה": "כ↔ك عبر IDN-13، وה↔ه عبر IDN-20، وנ↔ن عبر IDN-03؛ الواو صائت وهاء التأنيث خارج جذر כהן/كهن",
    "כ״ף": "כ↔ك عبر IDN-13، وפ↔ف عبر LAB-07/IDN-06؛ ألف كاف صائت اسم الحرف لا صامت زائد",
    "קו״ף": "ק↔ق عبر IDN-12، وפ↔ف عبر LAB-07/IDN-06؛ واو קו״ף وألف قاف صائتا اسم الحرف",
    "בוהן": "ב↔ب عبر IDN-05، وה↔ه عبر IDN-20، وמ↔م عبر IDN-02؛ الميم من البديل בהם الذي سماه قاموس الفرع للصورة בהן",
    "חפוי": "ח↔خ عبر SEM-05، وפ↔ف عبر LAB-07/IDN-06؛ أما ה الضعيفة في قاعدة חפה↔ي في خفي فلا صف مسمى بعد البحث بالحرفين وباسم العبرية",
    "רומי": "ר↔ر عبر IDN-01، وו↔و عبر IDN-10، وמ↔م عبر IDN-02؛ ياء רומי لاحقة نسبة خارج اسم روم",
    "שי\"ן": "ש↔ش عبر IDN-21، وי↔ي عبر IDN-23، وנ↔ن عبر IDN-03؛ قُرئ اسم الحرف بسطحه لا كجذر",
}


def sound_path(row: dict, decision: Decision) -> str:
    special = SPECIAL_SOUND.get(str(row["branch"]))
    return special if special is not None else ORIGINAL_SOUND_PATH(row, decision)


SPECIAL_ZERO: dict[str, str] = {
    "חזון": "قاموس الفرع يرد الاسم إلى חזה «تنبأ ورأى» مع لاحقة الاسم ־ון؛ اللب المقارن חזה",
    "פסול": "صفة مفعول من פסל «أبطل واستبعد»؛ الواو صائت صيغة واللب פסל",
    "פוטון": "قرض إنجليزي حديث كامل الصورة؛ لا تعرية سامية له",
    "א־ס־ף": "الرسم نفسه وسم جذر صريح؛ قُرئ אסף بلا علامة الفصل",
    "חפירה": "اسم مصدر من חפר؛ طرحت لاحقة الاسم فبقي חפר",
    "שטיפה": "اسم الغسل من שטף؛ هاء الاسم خارج الجذر שטף",
    "כפרי": "صفة نسبة من כפר «قرية»؛ ياء النسبة خارج الجذر כפר",
    "משלי": "اسم السفر من أمثال משל؛ ياء صيغة الإضافة لا تدخل الجذر משל",
    "אותנו": "الصورة את + נו، علامة مفعول مع ضمير جمع؛ الهيكل אתנ عابر لحد الصرف وليس جذرًا",
    "עלייה": "اسم مصدر من עלה «صعد»؛ لاحقة الاسم والصوائت خارج الجذر الضعيف עלה",
    "רופא": "الصورة الكاملة ردت إلى רפא «رمم أو شفي»؛ الواو صائت صيغة والألف جذرية",
    "עירייה": "اشتقاق حديث من עיר «مدينة» بلاحقة بلدية قيست على العربية؛ الهيكل ער لا يحمل اللاحقة ولا يثبت نقل بلدية",
    "ולא": "تركيب من ו־ «و» وלא «لا»؛ حُفظ المركب ولم يعامل جذرًا واحدًا",
    "אריה": "اسم البرج هو اسم الأسد، موروث من *ʔarway؛ ياء وهاء الصيغة ليستا جذرًا عربيًا مفترضًا",
    "ע״ש": "اختصار من ערב שבת في الحس المختار؛ لا جذر עש",
    "מיץ": "الاسم التوراتي من حس العصر والضغط؛ بقيت النواة מצ",
    "ד״ר": "اختصار من דוקטור؛ لا جذر דר",
    "כיוון": "قاموس الفرع يرد الفعل والاسم إلى כ־ו־ן؛ الهيكل כנ أسقط الواو الأصلية وسُجل العطب",
    "רוסי": "اسم نسبة حديث إلى روسيا؛ ياء النسبة خارج الاسم ولا جذر سامي مسمى",
    "עליו": "حرف الجر על مع ضمير الغائب ־יו؛ رد إلى על ولم يدخل الضمير الهيكل",
    "לפיו": "לפי «بحسب» مع ضمير الغائب ־ו؛ وقاعدة לפי نفسها من ל־ + פי «فم»",
    "ויצא": "واو عطف مع صيغة مصرفة من יצא «خرج»؛ الهيكل וצ الناتج ليس جذرًا",
    "סה״כ": "اختصار من סך הכול؛ لا جذر סכ مستقل في هذا العضو",
    "גילוי": "اسم مصدر من גילה «كشف وأظهر»؛ رد إلى גלה ولم تدخل واو وياء الصيغة الجذر",
    "לוין": "اسم مشتق من לוה «رافق» مع لاحقة ־ן؛ الهيكل לנ أسقط الواو الأصلية",
    "ריפא": "صيغة فعل من רפא «شفى وأصلح»؛ ياء الصيغة ليست جذرية والألف الأخيرة جذرية",
    "קיום": "اسم من קיים المرتبط بـקום؛ استعيد جذر קום من قاموس الفرع وطرحت ياء الصيغة",
    "קריה": "اسم المدينة من qry/qrt السامي المسمى في الاشتقاق؛ ה نهاية اسمية",
    "כהונה": "اسم الخدمة والكهنوت من כהן؛ الواو صائت وهاء التأنيث لاحقة",
    "ה״א": "الرسم اسم حرف كامل لا اختصارًا؛ قُرئ הא/ها صوتيًا",
    "כ״ף": "الرسم اسم حرف كامل لا اختصارًا؛ قُرئ כפ/كاف مع طرح صائت الاسم",
    "קו״ף": "الرسم اسم حرف كامل لا اختصارًا؛ قُرئ קפ/قاف مع طرح صائت الاسم",
    "עליה": "تهجئة ناقصة من עלייה؛ ردت إلى עלה «صعد»",
    "דגה": "اسم جنس من דג «سمك»؛ هاء الاسم خارج اللب דג",
    "חדווה": "قاموس الفرع يربط الاسم بآرامية חدا «فرح»؛ الواوان وهاء الاسم خارج اللب المفحوص",
    "בוהן": "قاموس الفرع يرد الاسم إلى בהן ويذكر בהם بديلًا ممكنًا؛ استعمل البديل المسمى لا إدغامًا مخترعًا",
    "חפוי": "صفة مفعول «مغطى» من عائلة חיפה/חפה «غطى» في قاموس الفرع؛ واو وياء الصيغة خارج القاعدة",
    "ח־צ־ה": "الجذر الصريح חצה للقسمة والفصل، وقاموس الفرع يسمي חצץ صورة ثانوية؛ فُحصت النواة חצ بلا إسقاط صامت أصلي",
    "עיירה": "اسم مصغر دلاليًا مشتق من עיר «مدينة»؛ لواحق الاسم خارج الهيكل ער",
    "רומי": "صفة نسبة إلى רומא/Ῥώμη؛ ياء النسبة خارج اسم روم",
    "ב״ר": "اختصار تشريفي أبوي؛ لا جذر בר في هذا العضو",
    "פ״א": "الرسم اسم حرف كامل في الحس المختار، لا اختصارًا لجذر آخر",
    "שי\"ן": "الرسم اسم حرف كامل؛ الياء صائت اسم الحرف لا علة حذف آلية",
}


SOURCE_ALIASES = {"كاف": "كوف", "قاف": "قوف"}


def select_rows() -> tuple[list[tuple[int, dict]], list[tuple[int, dict]]]:
    hebrew = R3.nonduplicates("hebrew")
    aramaic = R3.nonduplicates("aramaic")
    assert len(DECISIONS) == 52
    assert len(hebrew) == 52
    assert hebrew[0][0] == 1180 and hebrew[-1][0] == 1316
    assert len(R3.load_rows("hebrew")) == 1319
    assert not aramaic, f"Aramaic inventory changed: {aramaic[:3]}"
    return hebrew, aramaic


def render_card(serial: int, index: int, row: dict, decision: Decision,
                arabic_matches: dict[str, list[dict]]) -> str:
    R3.choose_lexicon_entry = choose_lexicon_entry
    R3.sound_path = sound_path
    card = R3.render_card(serial, index, row, decision, arabic_matches)
    card = card.replace("—", "،")
    card = re.sub(
        r"WO-C-HEBREW-\d{3}-\d{3}",
        f"WO-C-HEBREW-009-{serial:03d}",
        card,
        count=1,
    )
    zero = SPECIAL_ZERO.get(str(row["branch"]))
    if zero:
        card = re.sub(
            r"^- الخطوةُ صفر \(التعرية بصرف الفرع\): .*$",
            f"- الخطوةُ صفر (التعرية بصرف الفرع): {zero}.",
            card,
            count=1,
            flags=re.M,
        )
    if decision.verdict == ABBR:
        card = card.replace(
            "الاختصار ليس جذرًا معجميًا؛ عُزل قبل أن يرث حكم خذل لمجرد الرسم.",
            f"الاختصار ليس جذرًا معجميًا؛ عُزل قبل أن يرث حكم {decision.candidate} لمجرد الرسم.",
        )
    alias = SOURCE_ALIASES.get(decision.candidate)
    if alias:
        root = R3.AR.normalize_root(decision.candidate)
        card = card.replace(
            f"نتيجة للجذر `{root}` بـ`--max-chars 0`",
            f"نتيجة لاسم `{root}` المفهرس مع مادته المعجمية `{alias}` بـ`--max-chars 0`",
        )
    size = len(card.encode("utf-8"))
    assert size <= R3.MAX_CARD_BYTES, f"Round-six card is {size} bytes"
    return card


def render_batch() -> tuple[str, dict]:
    chosen, aramaic = select_rows()
    requested_roots = {R3.AR.normalize_root(value.candidate) for value in DECISIONS}
    requested_roots.update(SOURCE_ALIASES.values())
    raw_matches = R3.AR.matches_for_roots(
        R3.AR.DEFAULT_RESOURCES, requested_roots, None)
    arabic_matches = dict(raw_matches)
    for candidate, alias in SOURCE_ALIASES.items():
        arabic_matches[R3.AR.normalize_root(candidate)] = raw_matches.get(
            R3.AR.normalize_root(alias), [])
    cards = [
        render_card(serial, index, row, decision, arabic_matches)
        for serial, ((index, row), decision) in enumerate(
            zip(chosen, DECISIONS), 1)
    ]
    parts = [
        "## الدفعة العبرية 9: إتمام حوض both في الجولة السادسة (2026-08-17)",
        "",
        ("الحالة: طبقة الاستكشاف؛ إلحاق فقط. اختيرت الرسوم الاثنان والخمسون "
         "الباقية غير المكررة من الذاكرة بترتيب `overlap` النازل، وكل بطاقة "
         "منتهية بحكم."),
        "",
    ]
    for offset, card in enumerate(cards, 1):
        parts.extend([card.rstrip(), ""])
        if offset % 5 == 0 or offset == len(cards):
            parts.extend([
                f"<!-- LANE-C-HEBREW-R6-B9-CHUNK-{(offset + 4) // 5:03d}:END -->",
                "",
            ])
    appendix = "\n".join(parts).rstrip() + f"\n\n<!-- {MARKER}:END -->\n"

    after_memory = HEBREW.read_text(encoding="utf-8") + "\n" + appendix
    remaining_after = []
    for index, row in enumerate(R3.load_rows("hebrew")):
        if str(row["branch"]) not in after_memory:
            remaining_after.append(index)
            after_memory += "\n" + str(row["branch"])

    verdicts = collections.Counter(value.verdict for value in DECISIONS)
    states = collections.Counter(
        value.state or ("READY" if value.verdict == R else value.verdict)
        for value in DECISIONS
    )
    diagnostics = {
        "hebrew_rows": len(R3.load_rows("hebrew")),
        "hebrew_remaining_before": len(chosen),
        "hebrew_remaining_after": len(remaining_after),
        "aramaic_rows": len(R3.load_rows("aramaic")),
        "aramaic_remaining": len(aramaic),
        "first_written": chosen[0][0],
        "last_written": chosen[-1][0],
        "last_scanned": len(R3.load_rows("hebrew")) - 1,
        "trailing_duplicate_indexes": [1317, 1318],
        "verdicts": dict(sorted(verdicts.items())),
        "states": dict(sorted(states.items())),
        "appendix_bytes": len(appendix.encode("utf-8")),
        "max_card_bytes": max(len(card.encode("utf-8")) for card in cards),
        "card_count": len(cards),
        "branch_index_fallbacks": sum(
            "فهرس الرسم المنزوع الترقيم خلط متجانسات" in card for card in cards),
    }
    assert diagnostics["hebrew_remaining_after"] == 0
    return appendix, diagnostics


def report_text(diagnostics: dict) -> str:
    now = datetime.now(ZoneInfo("Africa/Cairo")).strftime("%Y-%m-%d %H:%M:%S %z")
    now = now[:-2] + ":" + now[-2:]
    verdicts = "، ".join(
        f"`{key}`={value}" for key, value in diagnostics["verdicts"].items())
    states = "، ".join(
        f"`{key}`={value}" for key, value in diagnostics["states"].items())
    return f"""

## الجولة السادسة: إتمام العبرية ثم إعادة فحص الآرامية

- الوقت: {now}.
- قانون التكرار: حُمّل ملف القراءة كاملًا مرة واحدة في الذاكرة، واختُبر كل `branch` فيه، ثم أضيف كل رسم منتخب إلى الذاكرة قبل مواصلة الصفوف؛ وهو العقد المقبول في الجولات السابقة.
- المقام قبل الكتابة: العبرية غير المكررة={diagnostics['hebrew_remaining_before']} من {diagnostics['hebrew_rows']:,}؛ الآرامية غير المكررة={diagnostics['aramaic_remaining']} من {diagnostics['aramaic_rows']}.

### الدفعة الأولى المطلوبة: إتمام العبرية، WO-C-HEBREW-009

- فُحص من `both[{diagnostics['first_written']}]` إلى نهاية الحوض `both[{diagnostics['last_scanned']}]`؛ كُتب: {diagnostics['card_count']}؛ آخر مكتوب غير مكرر `both[{diagnostics['last_written']}]`.
- صفا `both[1317]` و`both[1318]` ممثلان سابقًا، فاجتازتهما ذاكرة التكرار ولم تنشئ لهما بطاقة ثانية.
- أول عشرة أحكام: `חזון↔حزا`، `פסול↔فشل`، `פוטון↔بطن`، `סוכן↔سكن`، `א־ס־ף↔اسف`، `פרוש↔فرش`، `צירוף↔صرف`، `חפירה↔حفر`، `יישם↔وشم`، `שטיפה↔شطف`.
- آخر عشرة أحكام: `חדווה↔حدو`، `אורווה↔ار`، `בוהן↔بهم`، `חפוי↔خفي`، `ח־צ־ה↔حص`، `עיירה↔عر`، `רומי↔روم`، `ב״ר↔بر`، `פ״א↔فا`، `שי"ן↔شين`.

### الدفعة الثانية المطلوبة: الآرامية من موضع التوقف

- أُعيد فحص الحوض الآرامي كاملًا في الذاكرة: {diagnostics['aramaic_rows']} صفًا؛ مكرر={diagnostics['aramaic_rows'] - diagnostics['aramaic_remaining']}؛ غير مكرر={diagnostics['aramaic_remaining']}؛ مكتوب=0.
- لا صف بعد `both[425]` في لقطة الحوض، وكل رسومها ممثلة سابقًا؛ لذلك تعذر تكوين دفعة 40 إلى 60 بلا تكرار، ولم يُمس `aramaic.md`.

### التحقق والحصيلة

- مجموع الجولة السادسة المكتوب: {diagnostics['card_count']} بطاقة عبرية محكومة؛ توزيع الأحكام: {verdicts}.
- توزيع حالات الإغلاق: {states}.
- الحوض العبري مقروء حتى صفه الفيزيائي الأخير `both[{diagnostics['last_scanned']}]`، وهو 1,319 من 1,319؛ الباقي غير المكرر=0. آخر بطاقة جديدة عند `both[{diagnostics['last_written']}]`.
- بنية البطاقات: {diagnostics['card_count']}/{diagnostics['card_count']} لها مسار صوت، وحدث من `all_tiers`، ومعنى من قاموس الفرع أو عائق مسمى، ومدار يدوي، ومصفاة، وحكم؛ بدائل فهرس الرسم الصريحة={diagnostics['branch_index_fallbacks']}؛ أكبر بطاقة={diagnostics['max_card_bytes']:,} بايت، دون حد 5 كيلوبايت.
- لم يُشغّل `scripts/ship.py`، ولم يُنشأ إيداع.

<!-- {REPORT_MARKER}:END -->
LANE-C DONE6 {diagnostics['card_count']} hebrew both[{diagnostics['last_scanned']}]
"""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--show", type=int, choices=range(1, 53))
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    appendix, diagnostics = render_batch()
    print(json.dumps(diagnostics, ensure_ascii=False, indent=2))
    if args.show:
        card_id = f"WO-C-HEBREW-009-{args.show:03d}"
        cards = re.split(r"(?=^### WO-C-HEBREW-)", appendix, flags=re.M)
        card = next(value for value in cards if value.startswith(f"### {card_id}"))
        print("\n" + card.split("\n<!--", 1)[0].rstrip())
    if args.apply:
        hebrew_current = HEBREW.read_text(encoding="utf-8")
        report_current = REPORT.read_text(encoding="utf-8")
        if MARKER in hebrew_current:
            raise SystemExit("Round-six Hebrew marker already exists; append refused.")
        if REPORT_MARKER in report_current:
            raise SystemExit("Round-six report marker already exists; append refused.")
        with HEBREW.open("a", encoding="utf-8", newline="\n") as handle:
            if not hebrew_current.endswith("\n"):
                handle.write("\n")
            handle.write("\n" + appendix)
        with REPORT.open("a", encoding="utf-8", newline="\n") as handle:
            if not report_current.endswith("\n"):
                handle.write("\n")
            handle.write(report_text(diagnostics))
        print(f"APPENDED: {HEBREW.relative_to(ROOT)}")
        print(f"APPENDED: {REPORT.relative_to(ROOT)}")
        print(f"UNCHANGED: {ARAMAIC.relative_to(ROOT)} (exhausted in memory)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
