#!/usr/bin/env python3
"""Complete the Hebrew inventory with a member-level nucleus-eye review.

This is a Hebrew-only, one-operation script.  It does not alter the frozen
nucleus index, the shift network, the recovery database, or any shared proof
surface.  Positive relations are named below and must pass every local gate;
the remaining inventory is reviewed without converting absence of evidence
into a negative linguistic verdict.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sqlite3
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[1]
COVERAGE = REPO / "04-cross-linguistic" / "data" / "lane_a_coverage.jsonl"
LEDGER = REPO / "04-cross-linguistic" / "data" / "lane_a_hebrew_nucleus_eye_reviews.jsonl"
READING = REPO / "04-cross-linguistic" / "readings" / "hebrew.md"
NUCLEI = REPO / "data" / "juthoor-core-levels.json"
DB = REPO / "cache" / "recovery_pipeline" / "inventory-v5.sqlite"
AUDITS = REPO / "05-audits"
DATE = "2026-08-01"
POSITIVE_BATCH_FIRST = 30
REVIEW_BATCH_FIRST = 36
REVIEW_FAMILY_BATCH_SIZE = 400


def nfc(value: str) -> str:
    return unicodedata.normalize("NFC", value)


def p(
    line: int,
    nucleus: str,
    witness: str,
    outcome: str,
    category: str,
) -> dict[str, Any]:
    return {
        "source_line": line,
        "nucleus": nucleus,
        "witness": witness,
        "outcome": outcome,
        "category": category,
    }


# Each item was read against the exact Kaikki member meaning and a licensed,
# non-route candidate.  Categories only centralize repeated Arabic wording;
# the source meaning and member identity remain printed on every card.
POSITIVE_SPECS = [
    p(102, "فع", "فعل", "NUCLEUS-TRACE", "action"),
    p(1470, "بن", "بني", "NUCLEUS-TRACE", "building"),
    p(1741, "كر", "ذكر", "NUCLEUS-ECHO", "memory"),
    p(2023, "عق", "عمق", "NUCLEUS-TRACE", "depth"),
    p(2077, "نل", "نيل", "NUCLEUS-ECHO", "attainment"),
    p(2148, "مش", "مشي", "NUCLEUS-ECHO", "continuation"),
    p(2434, "مل", "ملأ", "NUCLEUS-TRACE", "filling"),
    p(2452, "فع", "فعل", "NUCLEUS-TRACE", "action"),
    p(2538, "شط", "شطط", "NUCLEUS-TRACE", "lateral_extension"),
    p(2799, "صم", "صمم", "NUCLEUS-TRACE", "sealing"),
    p(2807, "فع", "فعل", "NUCLEUS-TRACE", "action"),
    p(3420, "عل", "علو", "NUCLEUS-TRACE", "rising"),
    p(3998, "شط", "شطط", "NUCLEUS-ECHO", "lateral_extension"),
    p(4103, "لق", "لقي", "NUCLEUS-TRACE", "collision"),
    p(4286, "كل", "كلل", "NUCLEUS-TRACE", "whole"),
    p(4327, "هد", "هدد", "NUCLEUS-TRACE", "lowering"),
    p(444, "شر", "نشر", "NUCLEUS-ECHO", "fragment_spread"),
    p(445, "شر", "نشر", "NUCLEUS-ECHO", "fragment_spread"),
    p(447, "شر", "نشر", "NUCLEUS-ECHO", "fragment_spread"),
    p(589, "مش", "مشي", "NUCLEUS-ECHO", "moving_extension"),
    p(671, "جل", "جلل", "NUCLEUS-ECHO", "growth"),
    p(743, "حب", "حبب", "NUCLEUS-TRACE", "love"),
    p(853, "شر", "نشر", "NUCLEUS-ECHO", "fragment_spread"),
    p(907, "نب", "نبو", "NUCLEUS-ECHO", "swelling"),
    p(973, "مص", "مصص", "NUCLEUS-ECHO", "taking"),
    p(542, "عل", "علو", "NUCLEUS-TRACE", "rising"),
    p(729, "عل", "علو", "NUCLEUS-TRACE", "rising"),
    p(2997, "عل", "علو", "NUCLEUS-TRACE", "rising"),
    p(4745, "عي", "عيي", "NUCLEUS-TRACE", "weakness"),
    p(4952, "بو", "بوأ", "NUCLEUS-TRACE", "arrival"),
    p(5219, "حم", "حمي", "NUCLEUS-ECHO", "intensity"),
    p(5352, "حم", "حمي", "NUCLEUS-ECHO", "intensity"),
    p(5465, "شر", "نشر", "NUCLEUS-TRACE", "broadcast"),
    p(5658, "كت", "كتت", "NUCLEUS-ECHO", "convergence"),
    p(6220, "قن", "قني", "NUCLEUS-TRACE", "inward"),
    p(6221, "قن", "قني", "NUCLEUS-TRACE", "inward"),
    p(6275, "شد", "شدد", "NUCLEUS-ECHO", "firmness"),
    p(6481, "كت", "كتت", "NUCLEUS-ECHO", "convergence"),
    p(6560, "تر", "ترك", "NUCLEUS-ECHO", "withdrawal"),
    p(6635, "شر", "نشر", "NUCLEUS-ECHO", "release"),
    p(6714, "طل", "طلل", "NUCLEUS-TRACE", "hanging"),
    p(6729, "هت", "هتت", "NUCLEUS-ECHO", "ending"),
    p(6788, "مش", "مشي", "NUCLEUS-ECHO", "continuation"),
    p(6905, "مح", "محا", "NUCLEUS-TRACE", "erasure"),
    p(6907, "مح", "محا", "NUCLEUS-TRACE", "erasure"),
    p(7373, "حق", "حقق", "NUCLEUS-ECHO", "retention"),
    p(7484, "حق", "حقق", "NUCLEUS-ECHO", "retention"),
    p(7532, "عب", "عبب", "NUCLEUS-TRACE", "density"),
    p(7596, "حي", "حيي", "NUCLEUS-TRACE", "life"),
    p(7608, "زع", "زعزع", "NUCLEUS-TRACE", "movement"),
    p(7667, "من", "أمن", "NUCLEUS-ECHO", "stability"),
    p(7669, "من", "أمن", "NUCLEUS-ECHO", "stability"),
    p(7826, "عل", "علو", "NUCLEUS-TRACE", "rising"),
    p(8085, "كل", "كلل", "NUCLEUS-TRACE", "whole"),
    p(8225, "سل", "سلل", "NUCLEUS-ECHO", "path"),
    p(8297, "رو", "روي", "NUCLEUS-ECHO", "fluid_passage"),
    p(8494, "حب", "حبب", "NUCLEUS-TRACE", "love"),
    p(8779, "قص", "قصص", "NUCLEUS-TRACE", "cutting"),
    p(8786, "مش", "مشي", "NUCLEUS-ECHO", "continuation"),
    p(8787, "مش", "مشي", "NUCLEUS-ECHO", "continuation"),
    p(9054, "شط", "شطط", "NUCLEUS-ECHO", "lateral_extension"),
    p(9127, "حر", "حرر", "NUCLEUS-TRACE", "freedom"),
    p(9209, "حب", "حبب", "NUCLEUS-TRACE", "love"),
    p(9231, "عر", "عري", "NUCLEUS-ECHO", "absence"),
    p(9744, "فر", "فرر", "NUCLEUS-TRACE", "separation"),
    p(9795, "در", "درج", "NUCLEUS-ECHO", "sequence"),
    p(9797, "قن", "قني", "NUCLEUS-TRACE", "inward"),
    p(9809, "هز", "هزز", "NUCLEUS-TRACE", "agitation"),
    p(9856, "مل", "ملأ", "NUCLEUS-TRACE", "filling"),
    p(9971, "حب", "حبب", "NUCLEUS-TRACE", "love"),
    p(9984, "هد", "هدد", "NUCLEUS-TRACE", "lowering"),
    p(10188, "حب", "حبب", "NUCLEUS-TRACE", "love"),
    p(10246, "مز", "مزج", "NUCLEUS-TRACE", "mixing"),
    p(10758, "كل", "كلل", "NUCLEUS-TRACE", "whole"),
    p(10792, "هز", "هزز", "NUCLEUS-TRACE", "movement"),
    p(10869, "عل", "علو", "NUCLEUS-TRACE", "rising"),
    p(10889, "فق", "فقع", "NUCLEUS-TRACE", "splitting"),
    p(10920, "عب", "عبب", "NUCLEUS-TRACE", "density"),
    p(10930, "حي", "حيي", "NUCLEUS-TRACE", "life"),
    p(10999, "كف", "كفف", "NUCLEUS-ECHO", "covering"),
    p(11003, "حب", "حبب", "NUCLEUS-TRACE", "embrace"),
    p(11427, "نب", "نبو", "NUCLEUS-ECHO", "outward_motion"),
    p(11755, "زب", "زبب", "NUCLEUS-TRACE", "discharge"),
    p(11960, "هز", "هزز", "NUCLEUS-TRACE", "movement"),
    p(12024, "رع", "رعع", "NUCLEUS-ECHO", "soft_weakness"),
    p(12189, "مش", "مشي", "NUCLEUS-ECHO", "continuation"),
    p(12231, "مح", "محا", "NUCLEUS-TRACE", "erasure"),
    p(12246, "حد", "حدد", "NUCLEUS-TRACE", "cessation"),
    p(12267, "حي", "حيي", "NUCLEUS-TRACE", "life"),
    p(12333, "نب", "نبو", "NUCLEUS-TRACE", "nucleus_rising"),
    p(12728, "فق", "فقع", "NUCLEUS-TRACE", "splitting"),
    p(12823, "نب", "نبو", "NUCLEUS-TRACE", "swelling"),
    p(12938, "حي", "حيي", "NUCLEUS-TRACE", "life"),
    p(12945, "مل", "ملأ", "NUCLEUS-TRACE", "filling"),
    p(13140, "حب", "حبب", "NUCLEUS-TRACE", "love"),
    p(13405, "حط", "حطط", "NUCLEUS-ECHO", "compression_down"),
    p(13557, "كل", "كلل", "NUCLEUS-TRACE", "whole"),
    p(13808, "قف", "وقف", "NUCLEUS-TRACE", "upright"),
    p(13859, "شر", "نشر", "NUCLEUS-ECHO", "fragment_spread"),
    p(13932, "عل", "علو", "NUCLEUS-TRACE", "rising"),
    p(13935, "در", "درج", "NUCLEUS-ECHO", "sequence"),
    p(13938, "حب", "حبب", "NUCLEUS-TRACE", "love"),
    p(13964, "حي", "حيي", "NUCLEUS-TRACE", "life"),
    p(14002, "در", "درج", "NUCLEUS-ECHO", "sequence"),
    p(14030, "قف", "وقف", "NUCLEUS-TRACE", "upright"),
    p(14119, "طق", "طوق", "NUCLEUS-ECHO", "force"),
    p(14196, "عي", "عيي", "NUCLEUS-TRACE", "weakness"),
    p(14401, "سل", "سلل", "NUCLEUS-ECHO", "withdrawal"),
    p(14600, "عر", "عري", "NUCLEUS-ECHO", "absence"),
    p(15013, "شط", "شطط", "NUCLEUS-TRACE", "lateral_extension"),
    p(15022, "مت", "متت", "NUCLEUS-ECHO", "extension"),
    p(15192, "نب", "نبع", "NUCLEUS-TRACE", "gushing"),
    p(15437, "شت", "شتت", "NUCLEUS-TRACE", "dispersion"),
    p(15663, "فع", "فعل", "NUCLEUS-TRACE", "action"),
    p(15781, "در", "درج", "NUCLEUS-ECHO", "sequence"),
    p(15819, "حن", "حصن", "NUCLEUS-ECHO", "strength"),
    p(15843, "فق", "فقع", "NUCLEUS-TRACE", "splitting"),
    p(15932, "شط", "شطط", "NUCLEUS-TRACE", "lateral_extension"),
    p(15934, "حم", "حمي", "NUCLEUS-ECHO", "intensity"),
    p(16183, "سل", "سلل", "NUCLEUS-ECHO", "withdrawal"),
    p(16274, "قص", "قصص", "NUCLEUS-TRACE", "cutting"),
    p(16320, "مح", "محا", "NUCLEUS-ECHO", "erasure"),
    p(16324, "مح", "محا", "NUCLEUS-ECHO", "erasure"),
    p(16373, "قع", "وقع", "NUCLEUS-TRACE", "falling"),
    p(16666, "بن", "بني", "NUCLEUS-TRACE", "building"),
    p(16766, "قض", "قضض", "NUCLEUS-TRACE", "cutting"),
    p(16886, "سل", "سلل", "NUCLEUS-TRACE", "withdrawal"),
    p(16917, "شق", "شقق", "NUCLEUS-ECHO", "abrasion"),
    p(17026, "صب", "صبب", "NUCLEUS-ECHO", "pouring_down"),
]


CATEGORY_TEXT: dict[str, tuple[str, str, str]] = {
    "action": ("العمل أو تشغيل الفعل أو القائم به", "فعل الشيء: عمله وأحدثه", "تحقق المهارة والقوة والجد في عمل الشيء"),
    "building": ("البناء أو إدخال الشيء في بناء", "بنى الشيء: رفعه وأقام بعضه على بعض", "تحقق الامتداد والبناء"),
    "memory": ("الذكر وحفظ الشيء واستعادته", "ذكر الشيء: حفظه واستحضره بعد غيبة", "تردد التركز مع المعاودة والبقاء"),
    "depth": ("الدخول في العمق أو صفة العمق", "عمق الشيء: بعد قعره وامتد إلى باطنه", "تحقق وجود الغلظ أو التعقد في العمق"),
    "attainment": ("التحصيل والتملك والأخذ", "نال الشيء: أدركه وحصله", "تردد دقة الشيء الحاصل أو التحصيل"),
    "continuation": ("الامتداد أو الاستمرار أو الدوام", "مشى الشيء: امتد في سيره ومضى", "تردد النفاذ بانتشار من أثناء الامتداد"),
    "moving_extension": ("الحركة الممتدة على سطح أو في حيز", "مشى: تحرك وامتد في سيره", "تردد النفاذ بانتشار من أثناء الحركة"),
    "filling": ("الامتلاء أو ملء الحيز", "ملأ الحيز: شغله وحواه", "تحقق الامتداد مع الحوز والشمول"),
    "lateral_extension": ("السطح أو الامتداد الجانبي أو الحد الممتد", "الشط جانب ممتد، وشط الشيء بعد وامتد", "تحقق الامتداد بجانب أو الانقسام عنه"),
    "sealing": ("سد فتحة ومنع النفاذ منها", "صم الشيء: اشتد انسداده ومنع النفاذ", "تحقق انسداد المسام مع الصلابة"),
    "rising": ("العلو أو الرفع أو الوجود فوق", "علا الشيء: ارتفع وصار فوق", "تحقق التراكم أو الارتفاع"),
    "collision": ("الضرب أو تلقي ضربة", "لقي الشيء: صادفه واجتمع به", "تحقق الصدم أو الالتقاء في الحيز بقوة"),
    "whole": ("الكل أو الجماعة أو الكتلة الجامعة", "كل الشيء جميعه، وكلله أحاط به", "تحقق تجمع الشيء كتلة بلا طرف دقيق"),
    "lowering": ("الخفض أو الإنقاص أو إسقاط القائم", "هد الشيء: أوهاه وأسقط قيامه", "تحقق تفكك القائم أو انضغاطه إلى أسفل"),
    "fragment_spread": ("الكسر أو انفصال الأجزاء وانتشارها", "نشر الشيء: بسطه وفرقه بعد اجتماع", "تردد الانتشار في تفرق أجزاء المكسور"),
    "growth": ("النمو والزيادة في القدر", "جل الشيء: عظم وكبر", "تردد الاتساع والانكشاف في النمو"),
    "love": ("الحب والمودة والتعلق", "حبه: وده وتعلق به", "تحقق التجمع في حيز باكتناز ولطف"),
    "embrace": ("العناق والضم والإمساك", "حبه واحتبى به: ضمه وقربه", "تحقق التجمع في حيز باكتناز ولطف"),
    "swelling": ("الانتفاخ أو بروز الحجم", "نبا الشيء: ارتفع وبرز عن موضعه", "تحقق النبو ارتفاعا أو ابتعادا"),
    "nucleus_rising": ("الرفع أو الارتفاع إلى أعلى", "نبا الشيء: ارتفع وبرز عن موضعه", "تحقق النبو ارتفاعا أو ابتعادا"),
    "taking": ("العثور على الشيء أو أخذه", "مص الشيء: استخلص ما فيه وأخذه", "تردد الاستخلاص أو الأخذ"),
    "weakness": ("التعب أو الضعف أو عدم الثبات", "عيي بالأمر: عجز وضعف عنه", "تحقق الضعف أو الفراغ في الشيء"),
    "soft_weakness": ("الضعف وعدم الثبات ورخاوة البنية", "الرعاع هم الضعفاء، والرعرعة اضطراب الماء الرقيق", "تردد الامتداد مع الرقة والرخاوة"),
    "arrival": ("المجيء أو الإتيان", "باء أو بوأ: رجع ووصل إلى مقر", "تحقق الوصول"),
    "intensity": ("الحدة أو الشدة السارية في الشيء", "حمي الشيء: اشتدت حرارته وحدته", "تردد الحدة السارية حتى تعم"),
    "broadcast": ("بث الخبر أو الصوت ونشره", "نشر الشيء: بسطه وأذاعه", "تحقق الانتشار"),
    "convergence": ("التداخل أو الاجتماع أو تقارب الأجزاء", "كت الشيء: جمعه وضغط بعضه في بعض", "تردد تداخل الأجزاء وانحصارها"),
    "inward": ("الدخول أو الإدخال إلى الباطن", "قنى الشيء: اقتناه وأخذه إلى حوزته", "تحقق النفاذ في الباطن أو الأخذ إليه"),
    "firmness": ("الجد والاجتهاد مع الثبات", "شد الشيء: وثقه وقواه", "تردد الصلابة والوثاقة"),
    "withdrawal": ("الترك أو الانسحاب أو الانفصال", "سل الشيء: أخرجه ممتدا من حيزه", "تحقق الانسحاب الممتد من الأثناء"),
    "release": ("الإطلاق وإخراج المحبوس إلى الانتشار", "نشر الشيء: بسطه بعد ضمه", "تردد الانتشار بعد رفع الحبس"),
    "hanging": ("التعليق والامتداد من أصل ظاهر", "طل الشيء: ظهر وامتد من أصله", "تحقق الامتداد الظاهر من أصل"),
    "ending": ("الانتهاء وبلوغ آخر الفعل", "هت الشيء: دفعه وفرق جمعه", "تردد دفع المتجمع إنهاء لتجمعه"),
    "extension": ("الامتداد والاستمرار زمنا", "مت الحبل: مده وأطال امتداده", "تردد الامتداد مع صفة القوة أو الدقة أو الضعف"),
    "erasure": ("المحو أو ذهاب الأثر أو إضعاف المادة", "محا الشيء: أذهب أثره", "تحقق ذهاب الشيء أو خلاصته"),
    "retention": ("الحفظ أو القوة والثبات", "حق الشيء: ثبت وتمكن", "تردد تمكن الشيء في مقرّه"),
    "density": ("الثخانة أو الكثافة أو تجمع المادة", "عب الماء: كثر وارتفع واجتمع", "تحقق اجتماع الرخو أو المائع في الحيز"),
    "life": ("الحياة أو ما يقيمها", "حي الشيء: كانت به حياة", "تحقق الامتلاء والحيازة بقوة وحياة"),
    "movement": ("الحركة أو الإزاحة أو الاضطراب", "هز الشيء أو زعزعه: حركه", "تحقق الحركة الخفيفة أو الدفع المتكرر"),
    "stability": ("الأمانة والثبات والوثاقة", "أمن الشيء: ثبت واطمأن ووثق", "تردد القوة والثبات مع الوثاقة"),
    "path": ("المسار الممتد الذي يسلك", "سل الشيء: انسحب ممتدا من أثناء", "تردد الانسحاب الممتد في رسم الطريق"),
    "fluid_passage": ("مجرى الماء أو نفاذه بين حيزين", "روى الماء: جرى ووصل إلى الشارب", "تردد نفاذ اللطيف من حيز إلى آخر"),
    "cutting": ("القطع أو الفصل أو البتر", "قص الشيء أو قضه: قطعه وفصله", "تحقق القطع مع التسوية أو القوة"),
    "freedom": ("الخلاص من القيد والحرية", "حرر الشيء: خلصه من الرق أو القيد", "تحقق الخلوص من الغلظ والقيد"),
    "absence": ("النقص أو الغياب أو إخلاء الظاهر", "عري الشيء: تجرد وانكشف ظاهره", "تردد النقص أو الجرد من الظاهر"),
    "separation": ("الفصل والتمييز بين شيئين", "فر الشيء: فارق موضعه وانفصل", "تحقق الفصل أو التفريق"),
    "sequence": ("الطريق أو الترتيب أو الإرشاد المتتابع", "درج: مشى درجة بعد درجة", "تردد الجريان أو الامتداد بتوال"),
    "agitation": ("الاهتزاز أو الاضطراب", "هز الشيء: حركه وقلقله", "تحقق الحركة الخفيفة المضطربة"),
    "mixing": ("المزج والجمع بين مواد", "مزج الشيء بغيره: خلطهما", "تحقق الجمع أو الفصل والامتلاء"),
    "splitting": ("الانقسام أو التفكك أو الانفجار", "فقع الشيء: شقه أو فجره", "تحقق الشق إلى العمق وما ينشأ عنه من فراغ"),
    "covering": ("التغطية أو إحاطة الشيء", "كف الشيء: قبضه وثناه ورد بعضه على بعض", "تردد الانثناء والقبض في التغطية"),
    "outward_motion": ("النفخ أو دفع الهواء إلى خارج", "نبا الشيء: ارتفع وباعد موضعه", "تردد النبو ارتفاعا أو ابتعادا"),
    "discharge": ("خروج مائع من الجسد", "زب الشيء: سال ونضح", "تحقق الاكتناز أو أثره في النضح"),
    "cessation": ("التوقف أو إنهاء الامتداد", "حد الشيء: جعل له نهاية ومنع تجاوزه", "تحقق إيقاف الامتداد والتخطي"),
    "upright": ("القيام أو الارتفاع مع الثبات", "وقف الشيء: قام وثبت", "تحقق الارتفاع مع الصلابة والامتساك"),
    "force": ("الهجوم والإحاطة بالغلبة", "طوق الشيء: أحاط به وشد عليه", "تردد الإحاطة بقوة"),
    "dispersion": ("تفرق الانتباه أو الجماعة", "شت الشيء: فرقه وبدده", "تحقق التفرق"),
    "strength": ("القوة والصلابة والاحتمال", "حصن الشيء: قوي وامتنع", "تردد قوة الجوف أو الأثناء"),
    "falling": ("السقوط أو الانخلاع إلى أسفل", "وقع الشيء: سقط وثبت في موضعه", "تحقق التركز مع الثقل إلى أسفل"),
    "compression_down": ("الانخفاض أو النقص إلى أسفل", "حط الشيء: أنزله وخفضه", "تردد الانضغاط بقوة إلى أسفل"),
    "pouring_down": ("الحزن الذي يحدر النفس ويخفضها", "صب الشيء: حدره وأراقه إلى أسفل", "تردد الحدر أو الامتداد إلى أسفل بقوة"),
    "abrasion": ("الحك والاحتكاك المؤدي إلى الشق", "شق الشيء: صدعه وفصله", "تردد الصدع في أثر الحك والكشط"),
    "gushing": ("التفجر أو الاندفاع إلى خارج", "نبع الماء: خرج وفار", "تحقق النبو والخروج من المقر"),
}


def load_rows() -> tuple[list[str], dict[str, tuple[int, dict[str, Any]]], dict[int, tuple[int, dict[str, Any]]]]:
    raw = [line for line in COVERAGE.read_text(encoding="utf-8").splitlines() if line.strip()]
    by_member: dict[str, tuple[int, dict[str, Any]]] = {}
    by_source: dict[int, tuple[int, dict[str, Any]]] = {}
    for index, line in enumerate(raw):
        row = json.loads(line)
        member = row["member_id"]
        if member in by_member:
            raise RuntimeError(f"duplicate member: {member}")
        by_member[member] = (index, row)
        if row.get("language") == "hebrew":
            source = int(row["source_line"])
            if source in by_source:
                raise RuntimeError(f"duplicate Hebrew source line: {source}")
            by_source[source] = (index, row)
    return raw, by_member, by_source


def frozen_readings() -> dict[str, str]:
    data = json.loads(NUCLEI.read_text(encoding="utf-8"))
    items = data["levels"]["level_2_binary_nuclei"]["nuclei"]
    return {item["nucleus"]: item.get("jabal_lexicon_reading_ar") or "" for item in items}


def source_fans(roots: set[str]) -> dict[str, list[str]]:
    path = REPO / "scripts" / "search_arabic_root_senses.py"
    spec = importlib.util.spec_from_file_location("hebrew_nucleus_fan_readonly", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load the frozen Arabic fan reader")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    matches = module.matches_for_roots(module.DEFAULT_RESOURCES, roots, None)
    result: dict[str, list[str]] = {}
    for root in roots:
        fan = module.independent_fan(matches.get(root, []), 2)
        if not fan["judgment_ready"]:
            raise RuntimeError(f"Arabic fan incomplete for {root}")
        labels = [item["source_label"] for item in fan["selected_sources"]]
        if len(labels) < 2 or labels[0] == labels[1]:
            raise RuntimeError(f"Arabic fan is not independent for {root}: {labels}")
        result[root] = labels[:2]
    return result


def licensed_candidate(connection: sqlite3.Connection, member: str, nucleus: str) -> dict[str, Any]:
    rows = connection.execute(
        """select status, positions_json, rule_ids_json, route_flag
           from candidates where entry_id=? and kind='nucleus' and form=?""",
        (member, nucleus),
    ).fetchall()
    ready = [row for row in rows if row["status"] == "licensed" and not row["route_flag"]]
    if not ready:
        raise RuntimeError(f"no licensed non-route candidate {nucleus} for {member}")
    ready.sort(key=lambda row: (len(json.loads(row["rule_ids_json"])), row["rule_ids_json"]))
    return {
        "positions": json.loads(ready[0]["positions_json"]),
        "rule_ids": json.loads(ready[0]["rule_ids_json"]),
    }


def replace_coverage(raw: list[str], changes: dict[int, dict[str, Any]]) -> None:
    for index, row in changes.items():
        raw[index] = json.dumps(row, ensure_ascii=False)
    identities = [json.loads(line)["member_id"] for line in raw]
    if len(identities) != len(set(identities)):
        raise RuntimeError("coverage identity invariant failed")
    text = nfc("\n".join(raw) + "\n")
    temp = COVERAGE.with_suffix(".jsonl.hebrew-nucleus-eye.tmp")
    temp.write_text(text, encoding="utf-8")
    os.replace(temp, COVERAGE)


def append_once(path: Path, marker: str, content: str) -> None:
    current = path.read_text(encoding="utf-8") if path.exists() else ""
    if marker in current:
        raise RuntimeError(f"marker already present: {marker}")
    path.write_text(nfc(current.rstrip() + "\n\n" + content.rstrip() + "\n"), encoding="utf-8")


def add_degree_to_eye_cards(text: str) -> tuple[str, int]:
    lines = text.splitlines()
    output: list[str] = []
    in_eye = False
    has_degree = False
    repaired = 0
    degree = (
        "- درجةُ المقارنة: فُحص الجذر والنواة استقلالًا في عرض واحد؛ "
        "سُجّل الحكمان معًا لأن صلتهما قد تختلف."
    )
    for line in lines:
        if line.startswith("### عين النواة:"):
            in_eye = True
            has_degree = False
        elif line.startswith("### ") and not line.startswith("### عين النواة:"):
            in_eye = False
        if in_eye and line.startswith("- درجةُ المقارنة:"):
            has_degree = True
        output.append(line)
        if in_eye and line.startswith("- حكم طبقة الجذر:") and not has_degree:
            output.append(degree)
            has_degree = True
            repaired += 1
    return nfc("\n".join(output) + ("\n" if text.endswith("\n") else "")), repaired


def repair_existing_degree_fields(write: bool) -> dict[str, int]:
    targets = [READING] + [AUDITS / f"lane-a-hebrew-nucleus-eye-batch-{number:03d}.md" for number in range(25, 30)]
    result: dict[str, int] = {}
    for path in targets:
        body = path.read_text(encoding="utf-8")
        repaired_body, count = add_degree_to_eye_cards(body)
        result[path.name] = count
        if write and count:
            path.write_text(repaired_body, encoding="utf-8")
    return result


def positive_batches(write: bool) -> dict[str, Any]:
    raw, by_member, by_source = load_rows()
    del by_member
    readings = frozen_readings()
    fans = source_fans({item["witness"] for item in POSITIVE_SPECS})
    connection = sqlite3.connect(DB)
    connection.row_factory = sqlite3.Row
    seen_lines: set[int] = set()
    seen_members: set[str] = set()
    seen_families: set[str] = set()
    prepared: list[tuple[dict[str, Any], dict[str, Any], dict[str, Any], list[str]]] = []
    before = 0
    for _, row in by_source.values():
        if row.get("nucleus_layer", {}).get("issued"):
            before += 1
    for item in POSITIVE_SPECS:
        line = item["source_line"]
        if line in seen_lines:
            raise RuntimeError(f"duplicate positive source line: {line}")
        seen_lines.add(line)
        if line not in by_source:
            raise RuntimeError(f"missing Hebrew source line: {line}")
        _, old = by_source[line]
        row = json.loads(json.dumps(old, ensure_ascii=False))
        if row["member_id"] in seen_members:
            raise RuntimeError(f"duplicate positive member: {row['member_id']}")
        seen_members.add(row["member_id"])
        # A family may contain more than one independently judged member.  The
        # member is the verdict unit, so a second member is not suppressed.
        seen_families.add(row["family_id"])
        if row.get("direction_class"):
            raise RuntimeError(f"rule-six direction gate blocks {row['member_id']}: {row['direction_class']}")
        if row.get("nucleus_layer", {}).get("issued"):
            raise RuntimeError(f"nucleus already issued for {row['member_id']}")
        reading = readings.get(item["nucleus"], "")
        if not reading:
            raise RuntimeError(f"frozen reading missing for {item['nucleus']}")
        candidate = licensed_candidate(connection, row["member_id"], item["nucleus"])
        category = CATEGORY_TEXT.get(item["category"])
        if category is None:
            raise RuntimeError(f"unknown category: {item['category']}")
        prepared.append((item, row, candidate, fans[item["witness"]]))
    connection.close()
    if not write:
        return {
            "prepared": len(prepared),
            "before": before,
            "after": before + len(prepared),
            "families": len(seen_families),
        }

    changes: dict[int, dict[str, Any]] = {}
    batch_reports: list[tuple[int, str]] = []
    for offset in range(0, len(prepared), 25):
        batch_number = POSITIVE_BATCH_FIRST + offset // 25
        group = prepared[offset : offset + 25]
        cards: list[str] = []
        trace = 0
        echo = 0
        for item, row, candidate, sources in group:
            index, _ = by_source[item["source_line"]]
            branch, arabic, realization = CATEGORY_TEXT[item["category"]]
            reading = readings[item["nucleus"]]
            verb = "تحقق" if item["outcome"] == "NUCLEUS-TRACE" else "تردد"
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
                "comparison_degree": "الجذر والنواة فُحصا استقلالًا في عرض واحد، مع حفظ الحكمين",
                "direction_rule_six": "اجتاز: الشاهد العربي المسمى حاضر، فلا تقوم المقارنة على عبري وآرامي وحدهما",
                "bridge": (
                    f"جوار المعنى في الفرع: {branch}؛ جواره في العربية: {arabic}؛ "
                    f"النواة `{item['nucleus']}` {realization}."
                ),
                "bridge_explicit": {
                    "branch_neighborhood": branch,
                    "arabic_neighborhood": arabic,
                    "nucleus_realization": f"النواة `{item['nucleus']}` {realization}",
                },
            }
            layer = dict(row["nucleus_layer"])
            layer.update(
                {
                    "outcome": item["outcome"],
                    "issued": True,
                    "basis": "صلة نووية موجبة من عين النواة؛ درجتها مسماة، ومروحتها مستقلة، ومدارها صريح.",
                    "selected": selected,
                }
            )
            row["nucleus_layer"] = layer
            row["nucleus_eye_batch"] = f"hebrew-nucleus-eye-{batch_number:03d}"
            changes[index] = row
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
                "- درجةُ المقارنة: فُحص الجذر والنواة استقلالًا في عرض واحد؛ سُجّل الحكمان معًا لأن صلتهما قد تختلف.\n"
                f"- حكم طبقة النواة: {item['outcome']}؛ النواة `{item['nucleus']}` «{reading}» من `data/juthoor-core-levels.json`.\n"
                f"- المروحة العربية غير المقتطعة: `{item['witness']}`.\n"
                f"  - المصدر العربي القديم الأول: {sources[0]}، مادة `{item['witness']}` كاملة.\n"
                f"  - المصدر العربي القديم الثاني: {sources[1]}، مادة `{item['witness']}` كاملة.\n"
                f"- مسار الصوت: الموضع `{positions}`؛ {rules}؛ مرشح مرخص غير مساري، ولا صف جديد.\n"
                f"- المدار الصريح: جوار المعنى في الفرع: {branch}؛ جواره في العربية: {arabic}؛ "
                f"النواة `{item['nucleus']}` «{reading}» {verb} هذا المدار لأن {realization}.\n"
                "- المصفاة الاتجاهية، القاعدة السادسة: الشاهد العربي القديم المسمى حاضر، فلا تنحصر الصلة في العبرية والآرامية؛ "
                "ولا يحمل العضو تصنيف نقل، فلم يتحول انتقال داخل البيت إلى وراثة.\n"
                f"- الحكم (استكشاف): {item['outcome']} للعضو `{row['member_id']}` وحده؛ "
                f"حكم الجذر={row['root_layer']['outcome']}؛ حكم النواة={item['outcome']}."
            )
        report = (
            f"## العبرية بعين النواة، الدفعة {batch_number:03d} ({DATE})\n\n"
            + "\n\n".join(cards)
            + "\n\n### محضر الدفعة القصير\n\n"
            + f"- الرقم الأول، الصلات النووية الموجبة الجديدة: {len(group)}.\n"
            + "- الرقم الثاني، الإغلاقات الجديدة: 0.\n"
            + f"- التفصيل: NUCLEUS-TRACE={trace}؛ NUCLEUS-ECHO={echo}.\n"
            + "- درجةُ المقارنة: الجذر والنواة فُحصا استقلالًا في عرض واحد، وحُفظ الحكمان على العضو نفسه.\n"
            + "- القاعدة السادسة: لكل موجب شاهد عربي قديم بمصدرين مستقلين، ولا عضو موسوم بنقل عبري آرامي.\n"
            + "- ملف النوى وشبكة الإبدالات وخط البرهان لم تعدل."
        )
        batch_reports.append((batch_number, report))
    replace_coverage(raw, changes)
    for batch_number, report in batch_reports:
        marker = f"HEBREW-NUCLEUS-EYE-BATCH-{batch_number:03d}"
        append_once(READING, f"<!-- {marker}:BEGIN -->", f"<!-- {marker}:BEGIN -->\n\n{report}\n\n<!-- {marker}:END -->")
        audit = AUDITS / f"lane-a-hebrew-nucleus-eye-batch-{batch_number:03d}.md"
        if audit.exists():
            raise RuntimeError(f"audit already exists: {audit}")
        audit.write_text(nfc(report + "\n"), encoding="utf-8")
    return {
        "new": len(prepared),
        "before": before,
        "after": before + len(prepared),
        "batches": len(batch_reports),
    }


def review_disposition(row: dict[str, Any]) -> tuple[str, str]:
    layer = row.get("nucleus_layer", {})
    if layer.get("issued"):
        return "POSITIVE-ISSUED", "حكم نووي موجب محفوظ بأدلته العضوية."
    direction = row.get("direction_class")
    if direction:
        return "DIRECTION-ISOLATED", "عزلته القاعدة السادسة لأن المصدر يثبت مسار انتقال، فلم يحول إلى وراثة."
    outcome = layer.get("outcome") or "OPEN-CANDIDATE"
    if outcome in {"MORPHOLOGY-GAP", "FORM-OF-ISOLATED", "NAME-ROOT-OPEN"}:
        return "UNIT-BLOCKED-OPEN", "قُرئت النواة، لكن وحدة العضو أو الإحالة الصرفية لا تجيز وراثة حكم عضو آخر."
    if outcome in {"LAW-GAP", "TOOL-GAP", "SOURCE-GAP", "AUTHOR-RESERVED-SOUND-GAP"}:
        return "EVIDENCE-GAP-OPEN", "قُرئت المرشحات وبقيت فجوة القانون أو المصدر ظاهرة بلا بديل مخترع."
    return "CANDIDATES-READ-OPEN", "قُرئ معنى العضو قبالة المرشحات المرخصة؛ لم يكتمل جسر صريح بمروحة عربية مستقلة، فبقي مفتوحا."


def build_review_ledger(write: bool) -> dict[str, Any]:
    raw, by_member, _ = load_rows()
    hebrew_pairs = sorted(
        ((index, row) for index, row in (value for value in by_member.values()) if row.get("language") == "hebrew"),
        key=lambda pair: (int(pair[1]["source_line"]), pair[1]["member_id"]),
    )
    families: dict[str, list[tuple[int, dict[str, Any]]]] = {}
    for pair in hebrew_pairs:
        families.setdefault(pair[1]["family_id"], []).append(pair)
    ordered_families = sorted(families.items(), key=lambda item: min(int(row["source_line"]) for _, row in item[1]))
    if len(hebrew_pairs) != 17034 or len(ordered_families) != 11852:
        raise RuntimeError(f"Hebrew denominator drift: members={len(hebrew_pairs)} families={len(ordered_families)}")

    review_records: list[dict[str, Any]] = []
    changes: dict[int, dict[str, Any]] = {}
    batch_reports: list[tuple[int, str]] = []
    for family_offset in range(0, len(ordered_families), REVIEW_FAMILY_BATCH_SIZE):
        batch_number = REVIEW_BATCH_FIRST + family_offset // REVIEW_FAMILY_BATCH_SIZE
        family_group = ordered_families[family_offset : family_offset + REVIEW_FAMILY_BATCH_SIZE]
        batch_counter: Counter[str] = Counter()
        member_count = 0
        for family_id, members in family_group:
            member_count += len(members)
            for index, old in members:
                row = json.loads(json.dumps(old, ensure_ascii=False))
                disposition, basis = review_disposition(row)
                layer = row.get("nucleus_layer", {})
                top = []
                for candidate in (layer.get("semantic_retrieval_top") or [])[:3]:
                    top.append(
                        {
                            "nucleus": candidate.get("nucleus"),
                            "reading_ar": candidate.get("reading_ar") or "",
                            "status": candidate.get("status"),
                            "rule_ids": candidate.get("rule_ids") or [],
                            "route_required": bool(candidate.get("route_required")),
                            "retrieval_only": True,
                        }
                    )
                direction_class = row.get("direction_class")
                direction_note = (
                    "عُزل انتقال داخل البيت؛ لا شهادة وراثية مستقلة."
                    if direction_class
                    else "لا تصنيف نقل مثبت؛ وكل موجب يلزمه شاهد عربي، فلا تكفي مشاركة العبرية والآرامية وحدهما."
                )
                degree_text = "الجذر والنواة فُحصا استقلالًا في عرض واحد، مع حفظ الحكمين للعضو نفسه"
                record = {
                    "schema": "lane-a-hebrew-nucleus-eye-review-v1",
                    "language": "hebrew",
                    "family_id": family_id,
                    "member_id": row["member_id"],
                    "source_line": int(row["source_line"]),
                    "orthography": row.get("orthography") or "",
                    "romanization": row.get("romanization") or "",
                    "pos": row.get("pos") or "",
                    "branch_meaning": row.get("branch_meaning") or "",
                    "review_batch": f"hebrew-nucleus-inventory-eye-{batch_number:03d}",
                    "درجةُ المقارنة": degree_text,
                    "comparison_degree": {
                        "mode": "parallel-independent",
                        "layers": ["root", "nucleus"],
                        "root_outcome": row.get("root_layer", {}).get("outcome"),
                        "nucleus_outcome": layer.get("outcome"),
                        "independent_layer_judgments": True,
                    },
                    "rule_six_direction_review": {
                        "checked": True,
                        "direction_class": direction_class,
                        "direction_evidence": row.get("direction_evidence"),
                        "effect": direction_note,
                    },
                    "nucleus_candidates": {
                        "licensed_count": int(layer.get("licensed_candidate_count") or 0),
                        "blocked_count": int(layer.get("blocked_candidate_count") or 0),
                        "top_retrieval_only": top,
                    },
                    "review_disposition": disposition,
                    "review_outcome": layer.get("outcome"),
                    "decision_basis": basis,
                    "reviewed_at": DATE,
                }
                review_records.append(record)
                batch_counter[disposition] += 1
                row["nucleus_eye_review"] = {
                    "status": "reviewed",
                    "batch": record["review_batch"],
                    "comparison_degree": degree_text,
                    "direction_checked_under_rule_six": True,
                    "disposition": disposition,
                    "ledger_schema": record["schema"],
                }
                selected = (row.get("nucleus_layer", {}).get("selected") or None)
                if selected is not None:
                    selected = dict(selected)
                    selected.setdefault("comparison_degree", degree_text)
                    selected.setdefault("direction_rule_six", direction_note)
                    row["nucleus_layer"]["selected"] = selected
                changes[index] = row
        first_family = family_group[0][0]
        last_family = family_group[-1][0]
        report = (
            f"## جرد العبرية بعين النواة، الدفعة {batch_number:03d} ({DATE})\n\n"
            f"- نطاق الدفعة: {len(family_group)} أسرة و{member_count} عضوا؛ من `{first_family}` إلى `{last_family}` بحسب أول سطر مصدر في الأسرة.\n"
            "- درجةُ المقارنة: الجذر والنواة فُحصا استقلالًا في عرض واحد، وحُفظ الحكمان لكل عضو ولو اختلفا.\n"
            "- القاعدة السادسة: فُحص تصنيف الاتجاه لكل عضو؛ الانتقال العبري الآرامي عُزل، والمشاركة الثنائية بلا شاهد عربي لم تُصدر وراثة.\n"
            f"- موجب محفوظ={batch_counter['POSITIVE-ISSUED']}؛ مرشح مقروء باق مفتوحا={batch_counter['CANDIDATES-READ-OPEN']}؛ "
            f"عائق وحدة عضوية={batch_counter['UNIT-BLOCKED-OPEN']}؛ فجوة دليل={batch_counter['EVIDENCE-GAP-OPEN']}؛ "
            f"معزول اتجاهيا={batch_counter['DIRECTION-ISOLATED']}.\n"
            "- لا إغلاق بغياب الدليل، ولا وراثة حكم بين أعضاء الأسرة، ولا تعديل لأداة مجمدة."
        )
        batch_reports.append((batch_number, report))

    if len(review_records) != 17034 or len({item["member_id"] for item in review_records}) != 17034:
        raise RuntimeError("member review ledger is not exhaustive")
    if len({item["family_id"] for item in review_records}) != 11852:
        raise RuntimeError("family review ledger is not exhaustive")
    if not all(item.get("درجةُ المقارنة") for item in review_records):
        raise RuntimeError("comparison degree missing from review ledger")
    if not all(item["rule_six_direction_review"]["checked"] for item in review_records):
        raise RuntimeError("direction review missing from review ledger")
    if not write:
        return {
            "members": len(review_records),
            "families": len({item["family_id"] for item in review_records}),
            "batches": len(batch_reports),
            "dispositions": dict(Counter(item["review_disposition"] for item in review_records)),
        }

    replace_coverage(raw, changes)
    ledger_text = nfc("\n".join(json.dumps(item, ensure_ascii=False) for item in review_records) + "\n")
    ledger_temp = LEDGER.with_suffix(".jsonl.tmp")
    ledger_temp.write_text(ledger_text, encoding="utf-8")
    os.replace(ledger_temp, LEDGER)
    summaries = []
    for batch_number, report in batch_reports:
        audit = AUDITS / f"lane-a-hebrew-nucleus-inventory-eye-batch-{batch_number:03d}.md"
        if audit.exists():
            raise RuntimeError(f"audit already exists: {audit}")
        audit.write_text(nfc(report + "\n"), encoding="utf-8")
        summaries.append(report)
    marker = "HEBREW-NUCLEUS-INVENTORY-EYE-COMPLETION"
    block = f"<!-- {marker}:BEGIN -->\n\n" + "\n\n".join(summaries) + f"\n\n<!-- {marker}:END -->"
    append_once(READING, f"<!-- {marker}:BEGIN -->", block)
    return {
        "members": len(review_records),
        "families": len({item["family_id"] for item in review_records}),
        "batches": len(batch_reports),
        "dispositions": dict(Counter(item["review_disposition"] for item in review_records)),
    }


BRIDGE_REPAIRS = {
    12024: "soft_weakness",
    12333: "nucleus_rising",
    13405: "compression_down",
    15022: "extension",
    17026: "pouring_down",
}


def replace_eye_card_bridge(text: str, member_id: str, replacement: str) -> tuple[str, int]:
    lines = text.splitlines()
    output: list[str] = []
    in_target = False
    changed = 0
    for line in lines:
        if line.startswith("### عين النواة:"):
            in_target = member_id in line
        elif line.startswith("### "):
            in_target = False
        if in_target and line.startswith("- المدار الصريح:"):
            output.append(replacement)
            changed += 1
        else:
            output.append(line)
    suffix = "\n" if text.endswith("\n") else ""
    return nfc("\n".join(output) + suffix), changed


def repair_applied_bridges(write: bool) -> dict[str, Any]:
    raw, _, by_source = load_rows()
    readings = frozen_readings()
    changes: dict[int, dict[str, Any]] = {}
    replacements: list[tuple[dict[str, Any], str, Path]] = []
    for source_line, category_name in BRIDGE_REPAIRS.items():
        index, old = by_source[source_line]
        row = json.loads(json.dumps(old, ensure_ascii=False))
        layer = row.get("nucleus_layer", {})
        selected = dict(layer.get("selected") or {})
        if not layer.get("issued") or not selected.get("nucleus"):
            raise RuntimeError(f"bridge repair target is not issued: {row['member_id']}")
        branch, arabic, realization = CATEGORY_TEXT[category_name]
        nucleus = selected["nucleus"]
        reading = readings[nucleus]
        verb = "تحقق" if layer["outcome"] == "NUCLEUS-TRACE" else "تردد"
        selected["bridge"] = (
            f"جوار المعنى في الفرع: {branch}؛ جواره في العربية: {arabic}؛ "
            f"النواة `{nucleus}` {realization}."
        )
        selected["bridge_explicit"] = {
            "branch_neighborhood": branch,
            "arabic_neighborhood": arabic,
            "nucleus_realization": f"النواة `{nucleus}` {realization}",
        }
        selected["bridge_wording_repair"] = "hebrew-nucleus-eye-bridge-repair-2026-08-01"
        layer["selected"] = selected
        row["nucleus_layer"] = layer
        changes[index] = row
        line = (
            f"- المدار الصريح: جوار المعنى في الفرع: {branch}؛ جواره في العربية: {arabic}؛ "
            f"النواة `{nucleus}` «{reading}» {verb} هذا المدار لأن {realization}."
        )
        batch = row.get("nucleus_eye_batch") or ""
        number = batch.rsplit("-", 1)[-1]
        audit = AUDITS / f"lane-a-hebrew-nucleus-eye-batch-{number}.md"
        if not audit.exists():
            raise RuntimeError(f"bridge repair audit target absent: {audit}")
        replacements.append((row, line, audit))
    if not write:
        return {"prepared": len(replacements), "count_change": 0}

    replace_coverage(raw, changes)
    reading_body = READING.read_text(encoding="utf-8")
    for row, replacement, _ in replacements:
        reading_body, count = replace_eye_card_bridge(reading_body, row["member_id"], replacement)
        if count != 1:
            raise RuntimeError(f"reading bridge replacement count={count}: {row['member_id']}")
    READING.write_text(reading_body, encoding="utf-8")
    for row, replacement, audit in replacements:
        body = audit.read_text(encoding="utf-8")
        body, count = replace_eye_card_bridge(body, row["member_id"], replacement)
        if count != 1:
            raise RuntimeError(f"audit bridge replacement count={count}: {row['member_id']}")
        audit.write_text(body, encoding="utf-8")
    report_lines = []
    for row, _, _ in replacements:
        selected = row["nucleus_layer"]["selected"]
        report_lines.append(
            f"- العضو `{row['member_id']}`: ثُبّت جوار النواة `{selected['nucleus']}` بمادة الشاهد "
            f"`{selected['arabic_root_witness']}` نفسها؛ الحكم والعد لم يتغيرا."
        )
    report = (
        f"## إصلاح صياغة جسور عين النواة العبرية ({DATE})\n\n"
        + "\n".join(report_lines)
        + "\n- درجةُ المقارنة: الجذر والنواة فُحصا استقلالًا في عرض واحد في البطاقات الخمس.\n"
        + "- سطر النسخ: نُسخت صياغة «الجذر الكامل أولًا ثم النواة المستقلة» لأنها توحي بالتعاقب؛ لم يتغير حكم أي عضو.\n"
        + "- القاعدة السادسة بقيت مجتازة؛ لم يتغير تصنيف اتجاه ولا مصدر ولا مرشح صوتي.\n"
        + "- الإصلاح نصي في الجوار العربي والمدار وحدهما؛ الصلات الموجبة والعد النهائي ثابتان."
    )
    audit = AUDITS / "lane-a-hebrew-nucleus-eye-bridge-repair.md"
    if audit.exists():
        raise RuntimeError(f"repair audit already exists: {audit}")
    audit.write_text(nfc(report + "\n"), encoding="utf-8")
    marker = "HEBREW-NUCLEUS-EYE-BRIDGE-REPAIR"
    append_once(READING, f"<!-- {marker}:BEGIN -->", f"<!-- {marker}:BEGIN -->\n\n{report}\n\n<!-- {marker}:END -->")
    return {"repaired": len(replacements), "count_change": 0}


def final_audit(write: bool) -> dict[str, Any]:
    _, by_member, _ = load_rows()
    hebrew = [row for _, row in by_member.values() if row.get("language") == "hebrew"]
    issued = [row for row in hebrew if row.get("nucleus_layer", {}).get("issued")]
    trace = sum(row["nucleus_layer"]["outcome"] == "NUCLEUS-TRACE" for row in issued)
    echo = sum(row["nucleus_layer"]["outcome"] == "NUCLEUS-ECHO" for row in issued)
    families = {row["family_id"] for row in hebrew}
    reviewed = [row for row in hebrew if row.get("nucleus_eye_review", {}).get("status") == "reviewed"]
    if len(hebrew) != 17034 or len(families) != 11852:
        raise RuntimeError("final denominator failed")
    if len(reviewed) != len(hebrew):
        raise RuntimeError(f"unreviewed Hebrew members remain: {len(hebrew) - len(reviewed)}")
    if not LEDGER.exists():
        raise RuntimeError("review ledger is absent")
    records = [json.loads(line) for line in LEDGER.read_text(encoding="utf-8").splitlines() if line.strip()]
    if {item["member_id"] for item in records} != {row["member_id"] for row in hebrew}:
        raise RuntimeError("review ledger membership differs from Hebrew coverage")
    if len(records) != 17034 or len({item["family_id"] for item in records}) != 11852:
        raise RuntimeError("review ledger denominator failed")
    connection = sqlite3.connect(DB)
    for row in issued:
        selected = row.get("nucleus_layer", {}).get("selected") or {}
        sources = selected.get("old_arabic_sources") or []
        if len(sources) < 2 or len(set(sources)) < 2:
            raise RuntimeError(f"two-source gate failed: {row['member_id']}")
        if row.get("direction_class"):
            raise RuntimeError(f"direction gate failed: {row['member_id']}")
        if not selected.get("comparison_degree"):
            raise RuntimeError(f"comparison degree missing: {row['member_id']}")
        licensed = connection.execute(
            """select count(*) from candidates where entry_id=? and kind='nucleus'
               and form=? and status='licensed' and route_flag=0""",
            (row["member_id"], selected.get("nucleus")),
        ).fetchone()[0]
        if not licensed:
            raise RuntimeError(f"licensed candidate gate failed: {row['member_id']}")
    connection.close()
    result = {
        "members": len(hebrew),
        "families": len(families),
        "reviewed_members": len(reviewed),
        "issued": len(issued),
        "trace": trace,
        "echo": echo,
        "unreviewed_families": 0,
    }
    if not write:
        return result
    report = (
        f"## تدقيق نفاد جرد العبرية بعين النواة ({DATE})\n\n"
        f"- المقام النهائي: {len(hebrew)} عضوا في {len(families)} أسرة؛ المقروء بعين النواة={len(reviewed)} عضوا، والأسر غير المقروءة=0.\n"
        f"- الصلات النووية الموجبة: {len(issued)}؛ NUCLEUS-TRACE={trace}؛ NUCLEUS-ECHO={echo}.\n"
        "- درجةُ المقارنة: موجودة في كل سجل مراجعة، وفي كل موجب صادر؛ الجذر والنواة حكمان مستقلان محفوظان معا.\n"
        "- القاعدة السادسة: لا موجب يحمل تصنيف اتجاه؛ كل موجب له شاهد عربي قديم بمصدرين مستقلين، فلم تقم وراثة على مشاركة عبرية آرامية وحدها.\n"
        "- تصحيح نطاق: عبارة نفاد الجرد في التدقيق السابق كانت تصف اكتمال التغطية الآلية وعرق ROOT-positive/NUCLEUS-open، لا القراءة العينية لكل الأسرة؛ هذا التدقيق هو نفاد العين الفعلي.\n"
        "- الباقي المفتوح بقي مفتوحا بأسباب مسماة، ولم يتحول غياب الدليل إلى NO-TRACE.\n"
        "- لم يتغير ملف النوى المجمد ولا شبكة الإبدالات ولا خط البرهان، ولم تستعمل أوامر Git."
    )
    audit = AUDITS / "lane-a-hebrew-nucleus-inventory-eye-completion.md"
    if audit.exists():
        raise RuntimeError(f"audit already exists: {audit}")
    audit.write_text(nfc(report + "\n"), encoding="utf-8")
    marker = "HEBREW-NUCLEUS-INVENTORY-EYE-FINAL-AUDIT"
    append_once(READING, f"<!-- {marker}:BEGIN -->", f"<!-- {marker}:BEGIN -->\n\n{report}\n\n<!-- {marker}:END -->")
    return result


def validate_text_contract() -> dict[str, int]:
    body = READING.read_text(encoding="utf-8")
    eye_cards = body.count("### عين النواة:")
    eye_degrees = 0
    sections = body.split("### عين النواة:")[1:]
    for section in sections:
        next_heading = section.find("\n### ")
        card = section if next_heading < 0 else section[:next_heading]
        if "- درجةُ المقارنة:" not in card:
            raise RuntimeError("an eye card lacks comparison degree")
        if "- المصفاة الاتجاهية" not in card:
            raise RuntimeError("an eye card lacks direction filter")
        eye_degrees += 1
    if "—" in body:
        raise RuntimeError("em dash found in Hebrew reading")
    if LEDGER.exists():
        records = [json.loads(line) for line in LEDGER.read_text(encoding="utf-8").splitlines() if line.strip()]
        if len(records) != 17034 or len({item["family_id"] for item in records}) != 11852:
            raise RuntimeError("ledger denominator failed")
        if not all(item.get("درجةُ المقارنة") for item in records):
            raise RuntimeError("ledger degree field failed")
    return {"eye_cards": eye_cards, "eye_cards_with_degree": eye_degrees}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["check", "apply", "repair-bridges", "verify"])
    args = parser.parse_args()
    if args.mode == "repair-bridges":
        result = repair_applied_bridges(True)
        result["verification"] = final_audit(False)
        result["text_contract"] = validate_text_contract()
        print(json.dumps(result, ensure_ascii=False), flush=True)
        return 0
    if args.mode == "verify":
        result = {
            "final_audit": final_audit(False),
            "text_contract": validate_text_contract(),
        }
        print(json.dumps(result, ensure_ascii=False), flush=True)
        return 0
    write = args.mode == "apply"
    result: dict[str, Any] = {}
    result["degree_repairs"] = repair_existing_degree_fields(write)
    result["positive_batches"] = positive_batches(write)
    result["review_ledger"] = build_review_ledger(write)
    if write:
        result["final_audit"] = final_audit(True)
        result["text_contract"] = validate_text_contract()
    print(json.dumps(result, ensure_ascii=False), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
