#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Append lane C round 9 completion cards (Aramaic, then Egyptian).

The script is deliberately append-only.  It recomputes the latest explicit
member status in the Aramaic ledger, exhausts the remaining short live-open
members, then takes the first forty short, fan-bearing Egyptian lexical
snapshot cards.  AED is queried without a limit and every homographic hit is
written into the Egyptian completion card.  The deferred Egyptian ḏ row is
excluded.  No git, publication, or shipping command is run here.
"""

from __future__ import annotations

import argparse
import collections
from dataclasses import dataclass
import json
from pathlib import Path
import re
import sqlite3
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import build_aed_index as AED  # noqa: E402
import fan_any_script as FAN  # noqa: E402
import frozen_event as FE  # noqa: E402
import harvest_hebrew_aramaic_round8 as R8  # noqa: E402
import search_arabic_root_senses as AR  # noqa: E402


ARAMAIC = ROOT / "04-cross-linguistic" / "readings" / "aramaic.md"
EGYPTIAN = ROOT / "04-cross-linguistic" / "readings" / "egyptian.md"
REPORT = ROOT / "_inbox" / "lane-reports" / "2026-08-16-C.md"
DB = ROOT / "cache" / "recovery_pipeline" / "inventory-v5.sqlite"
MARKER = "LANE-C-ROUND9-2026-08-17"
FIRST_SERIAL = 122
MAX_CARD_BYTES = 5 * 1024
OPEN_STATES = {
    "OPEN-CANDIDATE", "TOOL-GAP", "SOURCE-GAP", "MORPHOLOGY-GAP",
    "LAW-GAP", "SEMANTIC-GAP", "NAME-ROOT-OPEN", "DIRECTIONAL-TRANSMISSION",
}
POSITIVE = R8.POSITIVE


@dataclass(frozen=True)
class Decision:
    member_id: str
    candidate: str
    verdict: str
    state: str
    keywords: tuple[str, ...]
    zero: str
    sound: str
    orbit: str
    reason: str


def words(value: str) -> tuple[str, ...]:
    return tuple(part for part in value.split("|") if part)


def pos(member_id: str, candidate: str, verdict: str, keywords: str,
        sound: str, orbit: str, reason: str, zero: str = "") -> Decision:
    assert verdict in POSITIVE
    return Decision(member_id, candidate, verdict, "READY", words(keywords),
                    zero, sound, orbit, reason)


def gap(member_id: str, candidate: str, state: str, reason: str,
        sound: str = "المروحة بنيوية فقط؛ لا يُرقّى التشابه إلى قانون أو نسب.",
        orbit: str = "لم يثبت مدار مباشر مكتمل الأرجل.",
        keywords: str = "", zero: str = "") -> Decision:
    assert state in OPEN_STATES
    return Decision(member_id, candidate, "OPEN-CANDIDATE", state,
                    words(keywords), zero, sound, orbit, reason)


def terminal(member_id: str, candidate: str, verdict: str, reason: str,
             zero: str = "") -> Decision:
    return Decision(
        member_id, candidate, verdict, verdict, (), zero,
        "الإغلاق بنيوي أو نقلي؛ لم يُستعمل التشابه السطحي لإصدار نسب.",
        "المسار المسمى يعزل العضو ولا يورث حكمًا لمتجانس أو مشتق.", reason,
    )


ARAMAIC_DECISIONS: tuple[Decision, ...] = (
    gap("kaikki_aramaic:1051:en-תור-arc-verb-N1bd30UM", "ثور", "SEMANTIC-GAP",
        "معنى amaze/wonder لا يطابق حواس ثور العربية بعد قراءة المروحة."),
    pos("kaikki_aramaic:350:en-תורא-arc-noun-vg0X~9GM", "ثور", "ROOT-ECHO",
        "الثور|البقر|أثار الأرض", "ת↔ث عبر DENT-01؛ ו/w↔و عبر LAB-06؛ ר↔ر هوية.",
        "اسم المهنة مشتق صراحة من ox، وهو الثور الذي تُثار به الأرض.",
        "الحكم للمشتق المهني ECHO، لا ادعاء تطابق الصيغة الاسمية.",
        "نُزعت ألف الحالة النهائية فقط بوسم ARAM-ZERO-01؛ بقيت مادة ת־ו־ר."),
    terminal("kaikki_aramaic:351:en-תורא-arc-noun-HdNCvATx", "تور",
             "SEMITIC-SOURCE-TRANSMISSION",
             "النص يرد cord/band إلى Akkadian turru/ṭurru، ويحفظ احتمال التأثير السومري أو الأصل السامي بلا محو.",
             "نُزعت ألف الحالة النهائية وحدها؛ لم يُحسم الخلاف الاشتقاقي بالقوة."),
    gap("kaikki_aramaic:1179:en-חוא-arc-verb-d81Q-QOH", "حو", "SEMANTIC-GAP",
        "حواس حو/حوي العربية المقروءة لا تعطي show/reveal مباشرة."),
    terminal("kaikki_aramaic:1008:en-אסא-arc-verb-arc:heal", "أسا",
             "LOANWORD-THIRD-PARTY-TO-BRANCH",
             "الفعل back-formation من اسم الطبيب الآرامي الذي يصرح مصدره بطريق Akkadian ثم Sumerian؛ حُفظ طريق الاشتقاق.",
             "حُفظت صيغة back-formation كما سماها المصدر ولم تُعامل جذرًا موروثًا."),
    pos("kaikki_aramaic:1019:en-זוג-arc-verb-PoS1kYgp", "زوج", "ROOT-TRACE",
        "زوج|قرين|قرن|تزوج", "ז↔ز هوية؛ ו↔و عبر LAB-06؛ ג↔ج عبر GUT-03.",
        "to pair/join/marry هو التزويج والقرن بين اثنين.",
        "الجذر الكامل والمعنى المباشر مكتملان."),
    gap("kaikki_aramaic:925:en-צרא-arc-verb-Ew6QDGY0", "صري", "LAW-GAP",
        "المعنى العربي يثبت القطع، لكن الرجل الضعيفة النهائية بين א وـي بلا صف موقع لهذه البطاقة.",
        "צ↔ص وר↔ر ظاهران؛ التحويل النهائي א↔ي غير موقع.",
        "split/tear يلتقي القطع، وبقيت فجوة الصوت وحدها.", "قطع|شق|دفع"),
    terminal("kaikki_aramaic:1960:en-הה״ד-arc-phrase-5FZFu0rk", "∅", "ABBREVIATION",
             "المصدر يصنفها اختصار العبارة hāḏā hū diḵṯīḇ؛ لا جذر معجمي مستقل."),
    gap("kaikki_aramaic:156:en-או-arc-intj-QpbEpEaR", "او", "TOOL-GAP",
        "الاعتراض woe/alas لا يملك مادة جذرية مستقلة قابلة لحكم النسب."),
    pos("kaikki_aramaic:222:en-שמא-arc-noun-gqNTf~Db", "سمو", "NUCLEUS-TRACE",
        "الاسم|سمى|تسمية", "ש↔س عبر SIB-01؛ מ↔م هوية؛ الحكم للنواة s-m، والواو أصل الاسم مصرح به عربيًا.",
        "name هو الاسم؛ المعاجم العربية تنص على أصل الاسم سمو وتسميته.",
        "النواة وحدها مدعاة، لا مساواة شكلية بين اللام الضعيفة والصيغة الآرامية.",
        "حُفظت *šim- المنشورة؛ لم تُدخل ألف الحالة في النواة."),
    gap("kaikki_aramaic:746:en-איכא-arc-adv-tIERwQxl", "ايك", "TOOL-GAP",
        "أداة where غير محللة إلى جذر معجمي موثق في المصدر."),
    gap("kaikki_aramaic:1848:en-גוא-arc-noun-B4u5x-2E", "جوف", "MORPHOLOGY-GAP",
        "المعنى قريب من الجوف، لكن الصامت الأخير المطلوب ف غير مثبت في سطح الفرع أو صرفه.",
        "ג↔ج عبر GUT-03؛ ו↔و؛ أما א↔ف فلا صف له.",
        "belly/innards يلتقي الجوف دلالة، ولم تكتمل البنية.", "الجوف|البطن|الداخل"),
    gap("kaikki_aramaic:1200:en-סום-arc-verb-yjaG~g~s", "سوم", "SOURCE-GAP",
        "لم يثبت مصدران قديمان معنى put/place في مادة سوم المقروءة."),
    gap("kaikki_aramaic:1335:en-עולא-arc-noun-YE89q0Fg", "عول", "SOURCE-GAP",
        "لا شاهدان عربيان يثبتان fetus/embryo في مروحة عول."),
    gap("kaikki_aramaic:1396:en-סברא-arc-noun-7RPgGqmv", "سبر", "SEMANTIC-GAP",
        "الأمل والثقة لا يطابقان اختبار الغور والهيئة في سبر."),
    pos("kaikki_aramaic:1397:en-סברא-arc-noun-m5~eecPR", "سبر", "ROOT-ECHO",
        "اختبر|خبر|علم|الرأي", "ס↔س وב↔ب وר↔ر هويات صامتية.",
        "consideration/conjecture/opinion تلتقي سبر الأمر: خبره واستخرج كنهه.",
        "صلة مدار النظر والاختبار إلى الرأي؛ لذلك ECHO.",
        "نُزعت ألف الحالة بوسم ARAM-ZERO-01؛ بقي ס־ב־ר."),
    pos("kaikki_aramaic:1398:en-סברא-arc-noun-1p0hSmCs", "سبر", "ROOT-ECHO",
        "الغور|خبر|الهيئة|المنظر", "ס↔س وב↔ب وר↔ر هويات صامتية.",
        "perspicacity/discernment يلتقي اختبار الغور، وcountenance يلتقي السبر: الهيئة والمنظر.",
        "وجهان عربيان مسميان يطابقان وجهي العضو، مع بقاء الحكم ECHO للاسم.",
        "نُزعت ألف الحالة بوسم ARAM-ZERO-01؛ بقي ס־ב־ר."),
    gap("kaikki_aramaic:1399:en-סברא-arc-noun-9pRatnWQ", "سبر", "SEMANTIC-GAP",
        "fine teacher/scholar مشتق مهني، ولا تسمي مروحة سبر العربية هذا الشخص مباشرة."),
    gap("kaikki_aramaic:1745:en-פלחא-arc-noun-FvKi3iSD", "فلح", "SEMANTIC-GAP",
        "المصدر يربطه بالعمل، لكن servant/attendant لا يطابق فلاح/شق مباشرة."),
    gap("kaikki_aramaic:1060:en-עמץ-arc-verb-HlYmbano", "غمض", "LAW-GAP",
        "الدلالة مطابقة لإغماض العين، لكن صف ע الآرامية ↔ غ العربية غير موقع.",
        "מ↔م؛ צ↔ض محتمل؛ الموضع الأول بلا صف مغلق.",
        "to close the eyes هو غمض العين، وفجوة الصوت مانعة.", "غمض|العين|أغمض"),
    gap("kaikki_aramaic:1577:en-אכר-arc-verb-PEXNq0ZH", "اكر", "SOURCE-GAP",
        "ظهر معنى plow/dig في مصدر عربي قديم واحد ومعجم ترجمة؛ لم يكتمل شرط المصدرين القديمين.",
        orbit="الدلالة مباشرة، لكن رجل المصدر العربي ناقصة.", keywords="حرث|حفر|الأرض"),
    gap("kaikki_aramaic:564:en-קופדא-arc-noun-D9zZBolT", "قفذ", "MORPHOLOGY-GAP",
        "العربية تسمي القنفذ بنون داخلية لا يثبت المصدر سقوطها، وشاهد الجذر المستقل واحد.",
        "ק↔ق؛ פ↔ف LAB-07؛ ד↔ذ DENT-03؛ النون الداخلية بلا تعليل.",
        "porcupine/hedgehog قريب من القنفذ، لكن البنية والمصدر ناقصان.", "القنفذ|الشيهم"),
    gap("kaikki_aramaic:1101:en-דרעא-arc-noun-RhAIFdbk", "زرع", "LAW-GAP",
        "المصدر يقارن Arabic زرع والمعنى يلتقي البذر، لكن ד الآرامية ↔ ز العربية بلا صف واحد موقع.",
        "ר↔ر وע↔ع هويتان؛ ד↔ز هو الموضع المانع.",
        "seed يلتقي زرع، وsperm امتداد بذري؛ الصوت يمنع الحكم.", "زرع|البذر|النسل"),
    gap("kaikki_aramaic:2065:en-פרחא-arc-noun-wGsM~gzF", "فرخ", "SEMANTIC-GAP",
        "حواس فرح/فرخ لا تعطي flower نفسه بلا جسر زائد."),
    pos("kaikki_aramaic:1616:en-כפרא-arc-noun-wgvvOXSC", "كفر", "ROOT-ECHO",
        "غطى|ستر|الكفر", "כ↔ك؛ פ↔ف عبر LAB-07؛ ר↔ر.",
        "smearing تغطية سطح بمادة، وتلتقي كفر الشيء: غطاه وستره.",
        "الالتقاء في فعل التغطية خطوة واحدة؛ الاسم الآرامي ECHO.",
        "نُزعت ألف الحالة بوسم ARAM-ZERO-01؛ بقي כ־פ־ר."),
    pos("kaikki_aramaic:1229:en-פרס-arc-verb-dJhTD84U", "فرس", "ROOT-ECHO",
        "دق|كسر|فرس الشيء", "פ↔ف عبر LAB-07؛ ר↔ر؛ ס↔س.",
        "to divide يلتقي أصل الفرس العربي في الدق والكسر وتفريق الجرم.",
        "الكسر مدار واحد لا مساواة لفظية كاملة، لذلك ECHO."),
    gap("kaikki_aramaic:1230:en-פרס-arc-verb-GuJRUmT0", "فرش", "LAW-GAP",
        "spread يطابق فرش دلالة، لكن ס الآرامية ↔ ش العربية لا يملك صفًا آراميًا موقعًا.",
        "פ↔ف LAB-07 وר↔ر؛ الصامت الأخير مانع.",
        "الدلالة مباشرة، والصوت غير مكتمل.", "فرش|بسط|نشر"),
    gap("kaikki_aramaic:2046:en-פרסא-arc-noun-QHaENWQf", "فرس", "SEMANTIC-GAP",
        "half-unit مشتق من divide في المصدر، لكن مروحة فرس العربية لا تسمي الوحدة نفسها."),
    gap("kaikki_aramaic:206:en-עלמא-arc-noun-wojgNfmr", "عالم", "SEMANTIC-GAP",
        "المصدر يقارن عالم، لكن eternity/forever لا يساوي world في شاهدين عربيين مباشرين."),
    gap("kaikki_aramaic:1562:en-בתל-arc-verb-0NF781ej", "بتل", "SEMANTIC-GAP",
        "القطع والانفصال في بتل لا يثبت ravish/violate مباشرة."),
    pos("kaikki_aramaic:1226:en-תקל-arc-verb-S-AX4MvP", "ثقل", "ROOT-ECHO",
        "الثقل|ثقيل|الحمل", "ת↔ث عبر DENT-01؛ ק↔ق؛ ל↔ل.",
        "to stumble نتيجة مباشرة لثقل الحمل، والمصدر يعيد اللفظ إلى *ṯql weight.",
        "المصدر المشترك مثبت، والدلالة اشتقاق حركي واحد؛ لذلك ECHO."),
    gap("kaikki_aramaic:331:en-גברא-arc-noun-mXVeTB88", "جبر", "SEMANTIC-GAP",
        "man/husband لا يطابق حواس جبر العربية رغم انتظام الصوامت."),
    gap("kaikki_aramaic:1834:en-קפס-arc-verb-2tgEuiC3", "كبس", "LAW-GAP",
        "contract/compress يلتقي كبس، لكن ק↔ك وפ↔ب وס↔س لا تجتمع في مسار واحد موقع لهذا العضو."),
    pos("kaikki_aramaic:1247:en-גלד-arc-verb-fe4etWAW", "جلد", "ROOT-ECHO",
        "الجليد|مجلودة|جمد", "ג↔ج عبر GUT-03؛ ל↔ل؛ ד↔د.",
        "to freeze يلتقي جَلَدَت الأرض من الجليد وأرض مجلودة.",
        "المعنى فعلي مباشر، وECHO احتياط لاختلاف الصياغة المعجمية."),
    pos("kaikki_aramaic:1901:en-ברכא-arc-noun-ae9aiLAn", "برك", "ROOT-ECHO",
        "برك البعير|الركبة|الصدر", "ב↔ب؛ ר↔ر؛ כ↔ك.",
        "knee تلتقي البروك على الركبتين وصدر البعير.",
        "صلة العضو بالفعل خطوة واحدة؛ لذلك ECHO.",
        "نُزعت ألف الحالة بوسم ARAM-ZERO-01؛ بقي ב־ר־כ."),
    terminal("kaikki_aramaic:2068:en-ארישא-arc-noun-8G7uxe-f", "ارس",
             "FORM-OF-ISOLATED", "المصدر يصرح بأنها alternative form of אריסא؛ لا شاهد جذري ثان."),
    pos("kaikki_aramaic:415:en-כוכבא-arc-noun-1oSi-LD1", "كوكب", "ROOT-ECHO",
        "الكوكب|النجم|كواكب", "כ↔ك؛ ו↔و عبر LAB-06؛ כ↔ك؛ ב↔ب.",
        "star هو الكوكب والنجم؛ والمصدر يعيد الفرع إلى *kabkab-.",
        "الرجل الواوية في الصيغتين محفوظة، وECHO احتياط لاختلاف بناء *kabkab/كوكب.",
        "نُزعت ألف الحالة؛ حُفظ kawkb- المنشور ولم تُختزل الواو."),
    pos("kaikki_aramaic:2031:en-בוצלא-arc-noun-KIlxZxaF", "بصل", "ROOT-TRACE",
        "البصل|بصلة|معروف", "ב↔ب؛ צ↔ص؛ ל↔ل.",
        "onion هو البصل نفسه، والمصدر يقارن العربية بصل صراحة.",
        "أكمل نص المصدر التعرية التي كانت فجوة صرفية؛ لا صف جديد.",
        "المقارنة المنشورة تعين ב־צ־ל، وتخرج واو الرسم وألف الحالة من الجذر."),
    pos("kaikki_aramaic:1170:en-עומקא-arc-noun-XBaOHpyp", "عمق", "ROOT-TRACE",
        "العمق|القعر|البعد إلى أسفل", "ע↔ع؛ מ↔م؛ ק↔ق.",
        "depth/deepness هو العمق والبعد إلى أسفل.",
        "أكمل الهيكل المعجمي ع־מ־ק معناه المباشر.",
        "وسم ARAM-ZERO-01 والهيكل المسجل يثبتان اللب ע־מ־ק بعد ألف الحالة وكتابة الصائت."),
    terminal("kaikki_aramaic:1146:en-פלפל-arc-noun-R9iJgAYn", "فلفل",
             "FORM-OF-ISOLATED", "المصدر يصرح بأنها alternative form of פלפלא؛ لا حكم مستقل."),
    pos("kaikki_aramaic:2009:en-ברכתא-arc-noun-WI08~zEW", "برك", "ROOT-TRACE",
        "البركة|بارك|بركات", "ב↔ب؛ ר↔ر؛ כ↔ك؛ تاء التأنيث صرف لا صامت جذري.",
        "blessing هي البركة، والمصدر يقارن Arabic بركة صراحة.",
        "المقارنة المنشورة تسند نزع -תא وتغلق فجوة الأداة دون تعميم.",
        "عُزلت -תא بوصفها نهاية الاسم المؤنث في هذا العضو وبسند المقارنة العربية المنشورة."),
    gap("kaikki_aramaic:2012:en-הלכתא-arc-noun-IAL9yJ9-", "هلك", "MORPHOLOGY-GAP",
        "لا سند فردي ينزع -תא ثم يصل custom/usual practice بمادة هلك العربية."),
    gap("kaikki_aramaic:1758:en-פעלתא-arc-noun-VRG0k7JK", "فعل", "MORPHOLOGY-GAP",
        "worker يوافق فاعل الدلالة، لكن نزع -תא والانتقال من פעלת إلى فعل غير مسند فرديًا."),
    gap("kaikki_aramaic:428:en-פרזלא-arc-noun-BOnA24fn", "فرزل", "SOURCE-GAP",
        "iron يقارن Hebrew barzel ويذكر Sumerian، ولا شاهدان عربيان قديمان لمادة فرزل."),
)


EGYPTIAN_IDS = (
    "283", "351", "23290", "24650", "33850", "38060", "52870", "52880",
    "56270", "57810", "68590", "77310", "90190", "96600", "102330",
    "107510", "108100", "111000", "117490", "120510", "120610", "122080",
    "125670", "132340", "138980", "155220", "157920", "160950", "162200",
    "164330", "859149", "23360", "38080", "44870", "69670", "71800",
    "73350", "74750", "79820", "95630",
)


def eid(number: str) -> str:
    return f"aed-v1.0:{number}"


EGYPTIAN_DECISIONS: tuple[Decision, ...] = (
    gap(eid("283"), "ءش", "SOURCE-GAP", "معنى AED نفسه محاط بعلامة الشك ولا شاهد عربي مباشر للصفة العينية."),
    gap(eid("351"), "ءد", "SEMANTIC-GAP", "to fail of the heart لا يطابق حواس ءد/أد العربية."),
    gap(eid("23290"), "يب", "LAW-GAP", "heart/mind يقترح لُبًّا دلاليًا، لكن ل خارج المروحة ولا صف j↔ل موقع؛ لم يُنتق متجانس AED الموافق."),
    gap(eid("24650"), "يم", "SEMANTIC-GAP", "pupil of the eye لا يطابق حواس يم/أم المقروءة."),
    pos(eid("33850"), "يد", "NUCLEUS-TRACE", "اليد|الجارحة|الذراع",
        "j↔ي عبر GLD-02 كما رخصه سجل المرشح؛ d↔د هوية.",
        "hand هي اليد والجارحة نفسها.", "AED فصل bull عن hand؛ الحكم للعضو 33850 وحده.",
        "المدخل verb/body lexeme ثنائي؛ لم تدخل حركة معادة البناء."),
    pos(eid("38060"), "عين", "NUCLEUS-ECHO", "العين|البصر|حاسة الرؤية",
        "ꜥ↔ع وn↔ن هويتان؛ الياء طبقة الأجوف العربية المسجلة بلا صف تحويل.",
        "eye as a writing character هو رسم العين، لا أحد متجانسات ꜥn الأخرى.",
        "تخصص العين بوصفها علامة كتابة يجعل الحكم ECHO للنواة.",
        "حُفظ الثنائي المصري ꜥ-n؛ لم تُخترع له صائتة، وعُرضت طبقة الأجوف عين مستقلة."),
    gap(eid("52870"), "بر", "SEMANTIC-GAP", "leopard skin لا يطابق حواس بر/بل."),
    gap(eid("52880"), "بر", "SEMANTIC-GAP", "leopard-skin garment عضو مستقل ولا يطابق حواس بر/بل."),
    gap(eid("56270"), "بر", "MORPHOLOGY-GAP", "eyeball/eye يحتاج صامتًا دلاليًا زائدًا في العربية، ولا يجوز اختراعه."),
    gap(eid("57810"), "بك", "SOURCE-GAP", "lock of hair لا يطابق مادة بك، وسجل AED يضم معدنًا وجذورًا فارغة بالهيكل نفسه."),
    gap(eid("68590"), "مع", "SEMANTIC-GAP", "basin for washing feet لا يطابق حواس مع/مض/مغ."),
    gap(eid("77310"), "مت", "SEMANTIC-GAP", "vessel/cord of the body لا يطابق حواس مت/مط."),
    gap(eid("90190"), "نث", "SEMANTIC-GAP", "tongue لا يطابق حواس نث/نت/نط."),
    gap(eid("96600"), "رد", "SEMANTIC-GAP", "foot/footprint لا يطابق حواس رد/رض/لد."),
    gap(eid("102330"), "حو", "SEMANTIC-GAP", "chisel الطقسي لا يطابق حواس حو."),
    gap(eid("107510"), "حور", "LAW-GAP", "face/sight يقترب من حور العين دلاليًا، لكن إدخال الواو وبناء الجذر بلا سند فردي ممنوع."),
    gap(eid("108100"), "خن", "SOURCE-GAP", "scowling face واصل AED كلاهما مشكوك، ولا شاهد عربي مباشر."),
    gap(eid("111000"), "حت", "SOURCE-GAP", "AED لا يعين الفعل المتصل بالشعر؛ لا يُبنى مدار على معنى مجهول."),
    gap(eid("117490"), "خن", "SEMANTIC-GAP", "direct one's hand against لا يطابق حواس خن."),
    gap(eid("120510"), "خخ", "SEMANTIC-GAP", "neck/throat لا يطابق حواس خخ المصنوعة من الهيكل."),
    gap(eid("120610"), "خس", "SEMANTIC-GAP", "rubbing stone لإزالة الشعر لا يطابق حواس خس/خش/خص."),
    gap(eid("122080"), "حت", "SEMANTIC-GAP", "body/belly/womb لا يطابق حواس حت/حط، والمتجانسات محفوظة."),
    gap(eid("125670"), "سر", "LAW-GAP", "back قد يقترح وراء، لكنه خارج الهيكل ولا يملك مسارًا موقعًا؛ بقي حكم البطاقة المفتوح."),
    gap(eid("132340"), "زب", "MORPHOLOGY-GAP", "clot يقترب من زبد دلاليًا، لكن الدال غير موجودة في المصري ولا يجوز إدخالها."),
    gap(eid("138980"), "شر", "MORPHOLOGY-GAP", "hair يطابق شعر، لكن العين صامت جذري زائد بلا سند سقوط."),
    gap(eid("155220"), "شن", "SEMANTIC-GAP", "body of water/sea لا يطابق حواس شن/سن مباشرة."),
    gap(eid("157920"), "شت", "SOURCE-GAP", "نوع علاج الأذن نفسه مشكوك pill/plug؛ لا مدار قطعي."),
    gap(eid("160950"), "قن", "SEMANTIC-GAP", "lion-shaped spout لا يطابق حواس قن، وفُصل عن strong warrior وبقية qn."),
    gap(eid("162200"), "قص", "MORPHOLOGY-GAP", "bone لا يطابق قص، وأي وصل بقصب يحتاج باء غير مثبتة."),
    gap(eid("164330"), "كم", "SEMANTIC-GAP", "pupil بوصفه black of eye لا يطابق مادة كم؛ فُصل عن km black نفسه."),
    gap(eid("859149"), "حع", "SEMANTIC-GAP", "flesh لا يطابق مروحة حع/حض/حغ."),
    gap(eid("23360"), "يب", "SEMANTIC-GAP", "thirsty man لا يطابق حواس يب، ولا يرث معنى jb heart أو kid."),
    gap(eid("38080"), "عين", "SEMANTIC-GAP", "pleasant man لا يرث حكم ꜥn eye؛ AED يفصل العضوين رغم اتحاد الرسم."),
    gap(eid("44870"), "وو", "SOURCE-GAP", "singing/music-making woman معنى مشكوك ومشتق من فعل مشكوك؛ لا حكم نسب."),
    gap(eid("69670"), "من", "SEMANTIC-GAP", "sick man لا يطابق حواس من، وفُصل عن mn remain والنفي."),
    gap(eid("71800"), "مر", "SEMANTIC-GAP", "sick man لا يطابق حواس مر مباشرة، ولا يُدخل ضاد مرض المحذوفة."),
    gap(eid("73350"), "مح", "SEMANTIC-GAP", "child لا يطابق حواس مح، وفُصل عن cubit/nest وبقية mḥ."),
    gap(eid("74750"), "مس", "SEMANTIC-GAP", "child لا يطابق حواس مس، وفُصل عن calf/grain/title."),
    gap(eid("79820"), "ني", "SOURCE-GAP", "noise of a newborn معنى طبي محاط بعلامة الشك ولا شاهد عربي مباشر."),
    gap(eid("95630"), "رخ", "SEMANTIC-GAP", "wise man/knower لا يطابق حواس رخ/لخ العربية."),
)


EXPECTED_ARAMAIC = tuple(item.member_id for item in ARAMAIC_DECISIONS)
EXPECTED_EGYPTIAN = tuple(eid(number) for number in EGYPTIAN_IDS)


def completed_aramaic_ids(text: str) -> set[str]:
    completed: set[str] = set()
    for block in re.finditer(r"(?ms)^### WO-C-OPEN-COMP-.*?(?=^### |\Z)", text):
        completed.update(re.findall(r"`(kaikki_aramaic:[^`]+)`", block.group()))
    return completed


def latest_aramaic_member_results(text: str) -> dict[str, dict]:
    latest: dict[str, dict] = {}
    for line_match in re.finditer(r"^.*$", text, re.M):
        line = line_match.group()
        if "- العضو:" not in line:
            continue
        for member in re.finditer(
            r"- العضو: `(kaikki_aramaic:[^`]+)`؛(.*?)(?=\s*\|\s*- العضو:|$)", line
        ):
            result = re.search(r"النتيجة: `?([A-Z][A-Z-]+)", member.group(2))
            if result:
                position = line_match.start() + member.start()
                latest[member.group(1)] = {
                    "position": position,
                    "line_number": text.count("\n", 0, position) + 1,
                    "prior_result": result.group(1),
                    "inventory_excerpt": member.group(2),
                }
    return latest


def load_entries(language: str) -> tuple[dict[str, dict], dict[str, list[dict]]]:
    connection = sqlite3.connect(DB)
    connection.row_factory = sqlite3.Row
    try:
        exact: dict[str, dict] = {}
        by_word: dict[str, list[dict]] = collections.defaultdict(list)
        for row in connection.execute("SELECT * FROM entries WHERE language=?", (language,)):
            value = dict(row)
            exact[str(row["entry_id"])] = value
            by_word[str(row["headword"])].append(value)
        return exact, dict(by_word)
    finally:
        connection.close()


def family_ids() -> dict[str, str]:
    connection = sqlite3.connect(DB)
    connection.row_factory = sqlite3.Row
    try:
        return {str(row["entry_id"]): str(row["family_id"])
                for row in connection.execute("SELECT entry_id,family_id FROM family_members")}
    finally:
        connection.close()


def select_aramaic(text: str, exact: dict[str, dict]) -> list[dict]:
    latest = latest_aramaic_member_results(text)
    completed = completed_aramaic_ids(text)
    selected = []
    for member_id, inventory in latest.items():
        if inventory["prior_result"] not in OPEN_STATES or member_id in completed:
            continue
        entry = exact.get(member_id)
        if not entry:
            continue
        tokens = FAN.skeleton(str(entry["headword"]), "north")
        fan = FAN.fan(str(entry["headword"]), "north")
        if 2 <= len(tokens) <= 4 and fan:
            selected.append({**entry, **inventory, "skeleton_tokens": tokens, "fan": fan})
    selected.sort(key=lambda item: (len(item["skeleton_tokens"]), int(item["position"])))
    return selected


def heading_blocks(text: str) -> list[tuple[int, str]]:
    return [(match.start(), match.group()) for match in re.finditer(
        r"(?ms)^### .*?(?=^### |\Z)", text
    )]


def select_egyptian(text: str, exact: dict[str, dict]) -> list[dict]:
    first_snapshot: dict[str, dict] = {}
    latest: dict[str, dict] = {}
    completed_ids = set(re.findall(
        r"(?ms)^### WO-C-OPEN-COMP-.*?`(aed-v1\.0:\d+)`.*?(?=^### |\Z)", text
    ))
    for position, block in heading_blocks(text):
        ids = list(dict.fromkeys(re.findall(r"aed-v1\.0:\d+", block)))
        if not ids:
            continue
        states = re.findall(r"^- حالةُ? الإغلاق:\s*([^\n]+)", block, re.M)
        verdicts = re.findall(r"^- الحكم \(استكشاف\):\s*([^\n]+)", block, re.M)
        status_text = " ".join((states[-1:] + verdicts[-1:]))
        heading = block.splitlines()[0]
        for member_id in ids:
            latest[member_id] = {
                "latest_position": position,
                "latest_status": status_text,
                "latest_heading": heading,
            }
            if f"EGYPTIAN-LEXICAL-SNAPSHOT-v1:{member_id}" in block:
                first_snapshot.setdefault(member_id, {
                    "snapshot_position": position,
                    "snapshot_line": text.count("\n", 0, position) + 1,
                    "snapshot_heading": heading,
                    "snapshot_inventory_id": f"EGYPTIAN-LEXICAL-SNAPSHOT-v1:{member_id}",
                })
    selected = []
    open_tokens = tuple(OPEN_STATES) + ("غير صادر", "غيرُ صادر")
    for member_id, snapshot in first_snapshot.items():
        if member_id in completed_ids:
            continue
        current = latest.get(member_id) or {}
        if not any(token in str(current.get("latest_status") or "") for token in open_tokens):
            continue
        entry = exact.get(member_id)
        if not entry or "ḏ" in str(entry["headword"]):
            continue
        tokens = FAN.skeleton(str(entry["headword"]), "egyptian")
        fan = FAN.fan(str(entry["headword"]), "egyptian")
        if 2 <= len(tokens) <= 4 and fan:
            selected.append({**entry, **snapshot, **current,
                             "skeleton_tokens": tokens, "fan": fan})
    selected.sort(key=lambda item: (len(item["skeleton_tokens"]), int(item["snapshot_position"])))
    return selected


def clean(value: object, limit: int = 260) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    return text if len(text) <= limit else text[:limit - 1].rstrip() + "…"


def safe_event(candidate: str, required: bool) -> str:
    tiers = FE.all_tiers(candidate)
    if not tiers:
        normalized = candidate.translate(str.maketrans("أإؤئآ", "ءءءءء"))
        tiers = FE.all_tiers(normalized)
    if required:
        assert tiers, f"No frozen event for positive candidate {candidate}"
    if not tiers:
        return "- الحدث المجمّد: لا حدث مسجل لهذا المرشح؛ بقيت البطاقة مفتوحة."
    return tiers[0].line() + f"؛ عُرضت {len(tiers)} درجات واختيرت المعلنة."


def fan_and_arabic(item: dict, decision: Decision, script: str,
                   matches_by_root: dict[str, list[dict]]) -> tuple[str, str, str]:
    word = str(item["headword"])
    ranked = FAN.rank(word, list(item["fan"]), script,
                      "aramaic" if script == "north" else "egyptian")
    top = "، ".join(candidate for candidate, _ in ranked[:10]) or "لا مرشح"
    selected_rank = next((rank for rank, (candidate, _) in enumerate(ranked, 1)
                          if candidate == decision.candidate), None)
    membership = (f"المرشح المختار في الرتبة {selected_rank}"
                  if selected_rank else
                  "المقابل خارج سطح المروحة، واستعيد من نص المصدر أو طبقة صرف مسماة")
    root = AR.normalize_root(decision.candidate)
    matches = matches_by_root.get(root, [])
    chosen = R8.witnesses(matches, decision.keywords)
    witness_text = "؛ ".join(
        f"قال {entry['source_label']}: «{R8.excerpt(str(entry.get('definition') or ''), decision.keywords)}»"
        for entry in chosen
    ) or "لا شاهد عربي عامل؛ والحكم لا يدعي صلة موجبة"
    if decision.verdict in POSITIVE:
        assert len(chosen) == 2, (
            f"Positive {decision.member_id} lacks two Arabic witnesses for {decision.candidate}"
        )
    fan_line = (f"الهيكل `{''.join(item['skeleton_tokens'])}`؛ قُرئت {len(ranked)} صورة مرتبة "
                f"كلها ولم تُنسخ؛ أوائلها: {top}؛ {membership}.")
    arabic_line = (f"قُرئت {len(matches)} نتيجة للجذر `{root}` بما يكافئ `--max-chars 0`؛ "
                   f"{witness_text}.")
    return fan_line, arabic_line, root


def default_zero(item: dict, decision: Decision) -> str:
    if decision.zero:
        return decision.zero
    return ("حُفظ الرسم والرومنة المنشوران؛ لا نزع بحدس. حالة الصرف المسجلة: "
            f"`{item.get('morphology_status') or 'غير مسماة'}`.")


def render_aramaic_card(serial: int, rank: int, item: dict, decision: Decision,
                         by_word: dict[str, list[dict]], families: dict[str, str],
                         matches: dict[str, list[dict]]) -> str:
    word = str(item["headword"])
    read = clean(item.get("romanization")) or "بلا رومنة منشورة"
    gloss = clean(item.get("gloss"), 300)
    etymology = clean(item.get("etymology"), 340) or "لا نص اشتقاق منشورًا في العضو"
    fan_line, arabic_line, root = fan_and_arabic(item, decision, "north", matches)
    homographs = by_word.get(word) or [item]
    homograph_text = "؛ ".join(
        f"{entry.get('pos') or 'بلا قسم'} «{clean(entry.get('gloss'), 90)}»"
        for entry in homographs
    )
    event = safe_event(decision.candidate, decision.verdict in POSITIVE)
    if decision.verdict in POSITIVE:
        filter_text = "اكتملت أرجل الصوت والحدث ومعنى الفرع؛ لا شرط رابع."
    elif decision.verdict == "OPEN-CANDIDATE":
        filter_text = f"العائق القاتل مسمى: {decision.reason}"
    else:
        filter_text = f"الإغلاق النهائي مسمى: {decision.reason}"
    card_id = f"WO-C-OPEN-COMP-{serial:05d}"
    family = families.get(decision.member_id, "غير مسمى")
    lines = [
        f"### {card_id}: `{word}` /{read}/ ↔ `{decision.candidate}`",
        "- إصدار البروتوكول: RECOVERY-v2 (2026-08-16) + ROUND9-COMPLETION (2026-08-17).",
        (f"- إحالة الجرد المفتوح: `{decision.member_id}`؛ family=`{family}`؛ "
         f"السطر السابق {item['line_number']}؛ النتيجة الأحدث قبل الإتمام `{item['prior_result']}`."),
        f"- الكلمة في الفرع: آرامية `{word}` /{read}/، {item.get('pos') or 'بلا قسم'}، «{gloss}».",
        f"- أقدم صورة/طريق مصدر: {etymology}.",
        f"- الخطوة صفر (التعرية بصرف الفرع): {default_zero(item, decision)}",
        f"- المروحة المفحوصة في الذاكرة: {fan_line}",
        f"- مسح المعاني العربية: {arabic_line}",
        f"- المقابل من اللسان: `{decision.candidate}`؛ مادة البحث `{root}`.",
        f"- مسار الصوت: {decision.sound}",
        event,
        f"- المعنى من قاموس الفرع: «{gloss}» [Kaikki؛ `{decision.member_id}`].",
        f"- جميع المتجانسات بنص الرسم ({len(homographs)}): {homograph_text}؛ الحكم للعضو المسمى وحده.",
        f"- المدار المكتوب باليد: {decision.orbit}",
        f"- المصفاة: {filter_text}",
        "- فصل المتجانسات والاقتراض: قُرئ نص الأصل والقرض والمتجانس؛ لا وراثة.",
        f"- مؤشر اليتم: عضو الجرد `{decision.member_id}`؛ round9-aramaic-rank={rank}/44.",
        "- إشعاع الأسرة: لا ينتقل الحكم خارج العضو المسمى؛ الشاهدان العربيان العاملان وحدهما كُتبا.",
        "- جسور الاسترداد: الصرف؛ المروحة؛ الحدث؛ المعاجم؛ الأصل؛ القرض؛ المتجانس؛ الاتجاه.",
        f"- عائق/تعليل الإغلاق: {decision.reason}",
        f"- حالة الإغلاق: {decision.state}.",
        f"- الحكم (استكشاف): {decision.verdict}.",
        "- ملاحظات: بطاقـة إتمام لاحقة فقط؛ لا تعديل للسجل التاريخي ولا شرط رابع.",
    ]
    card = "\n".join(lines) + "\n"
    assert len(card.encode("utf-8")) <= MAX_CARD_BYTES, f"Oversize {card_id}"
    return card


def render_aed_hits(hits: list[dict]) -> str:
    return "؛ ".join(
        f"`{entry.get('id')}` «{clean(entry.get('en') or '[∅]', 40)}»"
        for entry in hits
    ) or "لا إصابات"


def render_egyptian_card(serial: int, rank: int, item: dict, decision: Decision,
                          matches: dict[str, list[dict]]) -> str:
    word = str(item["headword"])
    read = clean(item.get("romanization")) or word
    gloss = clean(item.get("gloss"), 310)
    fan_line, arabic_line, root = fan_and_arabic(item, decision, "egyptian", matches)
    hits, path = AED.look(word)
    assert hits, f"AED unexpectedly has no hits for {word}"
    chosen = next((entry for entry in hits
                   if str(entry.get("id")) == decision.member_id.split(":")[-1]), None)
    assert chosen, f"AED chosen inventory member missing: {decision.member_id}"
    all_hits = render_aed_hits(hits)
    selected_line = (f"`{chosen.get('id')}`:`{chosen.get('translit')}` "
                     f"[{chosen.get('pos') or 'بلا قسم'}] "
                     f"EN «{clean(chosen.get('en') or '[لا ترجمة]', 150)}»؛ "
                     f"DE «{clean(chosen.get('de') or '[لا ترجمة]', 150)}»")
    event = safe_event(decision.candidate, decision.verdict in POSITIVE)
    if decision.verdict in POSITIVE:
        filter_text = "اكتملت أرجل الصوت والحدث ومعنى الفرع؛ لا شرط رابع."
    else:
        filter_text = f"العائق القاتل مسمى: {decision.reason}"
    card_id = f"WO-C-OPEN-COMP-{serial:05d}"
    lines = [
        f"### {card_id}: `{word}` /{read}/ ↔ `{decision.candidate}`",
        "- إصدار البروتوكول: RECOVERY-v2 (2026-08-16) + ROUND9-COMPLETION (2026-08-17).",
        (f"- إحالة الجرد المفتوح: `{item['snapshot_inventory_id']}`؛ السطر {item['snapshot_line']}؛ "
         f"العضو `{decision.member_id}`؛ أحدث الحالة قبل الإتمام: {clean(item['latest_status'], 180)}."),
        f"- الكلمة في الفرع: مصرية `{word}`؛ {item.get('pos') or 'بلا قسم'}؛ «{gloss}».",
        "- الخطوة صفر: حُفظت صوامت AED كما هي؛ لا صائتة معادة البناء ولا إسقاط لصامت مصري.",
        f"- المروحة المفحوصة في الذاكرة: {fan_line}",
        f"- مسح المعاني العربية: {arabic_line}",
        f"- بحث AED: وسم الطريق `{path}`؛ الصورة `{word}`؛ عُرضت المداخل كلها ({len(hits)}): {all_hits}.",
        f"- مدخل AED المختار بالسياق ومعرف الجرد: {selected_line}.",
        (f"- سجل الاختلاف المحفوظ: معنى بطاقة الجرد «{gloss}» باقٍ؛ اختير العضو "
         f"`{decision.member_id}` لا أول إصابة، وبقيت معاني المتجانسات أعلاه بلا محو أو دمج."),
        f"- المقابل من اللسان: `{decision.candidate}`؛ مادة البحث `{root}`.",
        f"- مسار الصوت: {decision.sound}",
        event,
        f"- المعنى من قاموس الفرع: EN «{clean(chosen.get('en'), 190)}»؛ DE «{clean(chosen.get('de'), 190)}» [AED `{chosen.get('id')}`].",
        f"- المدار المكتوب باليد: {decision.orbit}",
        f"- المصفاة: {filter_text}",
        "- فصل المتجانسات والاقتراض: كل إصابات AED مكتوبة أعلاه؛ لا يرث المختار معنى جار الرسم.",
        f"- مؤشر اليتم: `{decision.member_id}`؛ round9-egyptian-rank={rank}/40؛ المخزون المعلن=9,263.",
        "- جسور الاسترداد: الهيكل؛ المروحة؛ الحدث؛ المعاجم؛ AED الكامل؛ المتجانس؛ الاتجاه.",
        f"- عائق/تعليل الإغلاق: {decision.reason}",
        f"- حالة الإغلاق: {decision.state}.",
        f"- الحكم (استكشاف): {decision.verdict}.",
        "- ملاحظات: صف ḏ مؤجل بقرار المؤلف ومستبعد من هذا الانتقاء؛ لا تعديل لبطاقاته.",
    ]
    card = "\n".join(lines) + "\n"
    size = len(card.encode("utf-8"))
    assert size <= MAX_CARD_BYTES, f"Oversize {card_id}: {size} bytes"
    return card


def render_appendices() -> tuple[str, str, str, dict]:
    aramaic_text = ARAMAIC.read_text(encoding="utf-8")
    egyptian_text = EGYPTIAN.read_text(encoding="utf-8")
    report_text = REPORT.read_text(encoding="utf-8")
    if MARKER in aramaic_text or MARKER in egyptian_text or MARKER in report_text:
        raise SystemExit("Round-nine marker already exists; append refused.")

    aramaic_exact, aramaic_by_word = load_entries("aramaic")
    egyptian_exact, _ = load_entries("egyptian")
    families = family_ids()

    aramaic_queue = select_aramaic(aramaic_text, aramaic_exact)
    aramaic_ids = tuple(str(item["entry_id"]) for item in aramaic_queue)
    assert aramaic_ids == EXPECTED_ARAMAIC, (
        f"Aramaic live-open queue drifted:\nexpected={EXPECTED_ARAMAIC}\nactual={aramaic_ids}"
    )
    egyptian_queue = select_egyptian(egyptian_text, egyptian_exact)
    egyptian_selected = egyptian_queue[:40]
    egyptian_ids = tuple(str(item["entry_id"]) for item in egyptian_selected)
    assert egyptian_ids == EXPECTED_EGYPTIAN, (
        f"Egyptian queue drifted:\nexpected={EXPECTED_EGYPTIAN}\nactual={egyptian_ids}"
    )
    assert all("ḏ" not in str(item["headword"]) for item in egyptian_selected)

    roots = {
        AR.normalize_root(decision.candidate)
        for decision in ARAMAIC_DECISIONS + EGYPTIAN_DECISIONS
        if decision.candidate not in {"∅", ""}
    }
    matches = AR.matches_for_roots(AR.DEFAULT_RESOURCES, roots, None)

    aramaic_cards = [
        render_aramaic_card(FIRST_SERIAL + rank - 1, rank, item, decision,
                             aramaic_by_word, families, matches)
        for rank, (item, decision) in enumerate(zip(aramaic_queue, ARAMAIC_DECISIONS), 1)
    ]
    egyptian_first_serial = FIRST_SERIAL + len(aramaic_cards)
    egyptian_cards = [
        render_egyptian_card(egyptian_first_serial + rank - 1, rank, item, decision, matches)
        for rank, (item, decision) in enumerate(zip(egyptian_selected, EGYPTIAN_DECISIONS), 1)
    ]

    aramaic_body = [
        f"<!-- {MARKER}:ARAMAIC:START -->", "",
        "## الجولة التاسعة: إتمام بقية المفتوح الآرامي القصير (2026-08-17)", "",
        ("أُعيدت الحالة إلى أحدث نتيجة صريحة لكل عضو، لا إلى حالة عائلته الأقدم. "
         "بقي 44 عضوًا قصير الهيكل ذا مروحة غير فارغة، فاستُنفدوا جميعًا في "
         "`WO-C-OPEN-COMP-00122..00165`. بعدهم صار العدد الحي في هذا الطابور صفرًا، "
         "فوقع الانتقال المسمى `ARAMAIC-SHORT-LIVE-OPEN-EXHAUSTED -> EGYPTIAN-RECORDED-OPEN`."), "",
    ]
    for rank, card in enumerate(aramaic_cards, 1):
        aramaic_body.extend([card.rstrip(), ""])
        if rank % 5 == 0 or rank == len(aramaic_cards):
            aramaic_body.extend([f"<!-- LANE-C-R9-ARAMAIC-CHUNK-{rank:03d}:END -->", ""])
    aramaic_body.append(f"<!-- {MARKER}:ARAMAIC:END -->")

    egyptian_body = [
        f"<!-- {MARKER}:EGYPTIAN:START -->", "",
        "## الجولة التاسعة: بدء المخزون المصري المسجل المفتوح (2026-08-17)", "",
        ("بدأ الانتقاء بعد نفاد الطابور الآرامي من المخزون المعلن ذي 9,263 بطاقة. "
         "أُخذت أول 40 بطاقة بحسب قصر الهيكل ثم موضع بطاقة اللقطة، مع اشتراط مروحة غير فارغة. "
         "استُبعد كل رسم يحوي ḏ تنفيذًا لتأجيل صفه، ولم تُمس بطاقاته. في كل بطاقة قُرئت "
         "جميع إصابات AED بلا حد، وكُتب وسم الطريق والمدخل المختار ومعاني المتجانسات بلا محو."), "",
    ]
    for rank, card in enumerate(egyptian_cards, 1):
        egyptian_body.extend([card.rstrip(), ""])
        if rank % 5 == 0:
            egyptian_body.extend([f"<!-- LANE-C-R9-EGYPTIAN-CHUNK-{rank:03d}:END -->", ""])
    egyptian_body.append(f"<!-- {MARKER}:EGYPTIAN:END -->")

    total = len(aramaic_cards) + len(egyptian_cards)
    last_serial = FIRST_SERIAL + total - 1
    report_body = "\n".join([
        "", f"<!-- {MARKER}:REPORT -->",
        "## الجولة التاسعة — المسار C (2026-08-17)", "",
        (f"- كُتبت {len(aramaic_cards)} بطاقة إتمام آرامية من "
         f"`WO-C-OPEN-COMP-{FIRST_SERIAL:05d}` إلى "
         f"`WO-C-OPEN-COMP-{egyptian_first_serial - 1:05d}`؛ وهي كل الباقي الحي القصير بعد تقديم أحدث حكم للعضو على حالة العائلة القديمة."),
        "- نَفِد الطابور الآرامي القصير ذو المروحة غير الفارغة، وسُجل الانتقال إلى المخزون المصري المفتوح المعلن (9,263 بطاقة).",
        (f"- كُتبت {len(egyptian_cards)} بطاقة إتمام مصرية من "
         f"`WO-C-OPEN-COMP-{egyptian_first_serial:05d}` إلى `WO-C-OPEN-COMP-{last_serial:05d}`؛ الأقصر أولًا."),
        "- في المصري: AED بلا حد لكل الإصابات، وسم الطريق مكتوب، والمدخل المختار مسمى، والاختلاف والمتجانسات محفوظة بلا محو.",
        "- صف ḏ مؤجل بقرار المؤلف؛ استُبعد من الانتقاء وبقيت بطاقاته على حالها.",
        "- لا ship ولا commit ولا stage ولا تحديث مشتقات نشر.", "",
        f"LANE-C DONE9 {total} WO-C-OPEN-COMP-{last_serial:05d}",
    ]) + "\n"

    diagnostics = {
        "aramaic_cards": len(aramaic_cards),
        "aramaic_live_open_after": len(aramaic_queue) - len(aramaic_cards),
        "egyptian_cards": len(egyptian_cards),
        "egyptian_declared_stock": 9263,
        "total_cards": total,
        "first_card": f"WO-C-OPEN-COMP-{FIRST_SERIAL:05d}",
        "transition_card": f"WO-C-OPEN-COMP-{egyptian_first_serial:05d}",
        "last_card": f"WO-C-OPEN-COMP-{last_serial:05d}",
        "aramaic_verdicts": dict(sorted(collections.Counter(
            item.verdict for item in ARAMAIC_DECISIONS).items())),
        "egyptian_verdicts": dict(sorted(collections.Counter(
            item.verdict for item in EGYPTIAN_DECISIONS).items())),
        "max_card_bytes": max(len(card.encode("utf-8"))
                              for card in aramaic_cards + egyptian_cards),
    }
    return ("\n".join(aramaic_body).rstrip() + "\n",
            "\n".join(egyptian_body).rstrip() + "\n",
            report_body, diagnostics)


def append(path: Path, marker: str, payload: str) -> None:
    current = path.read_text(encoding="utf-8")
    if marker in current:
        raise SystemExit(f"Marker appeared during render in {path}; append refused.")
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        if not current.endswith("\n"):
            handle.write("\n")
        handle.write("\n" + payload)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--show", type=int, choices=range(122, 206))
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    aramaic, egyptian, report, diagnostics = render_appendices()
    print(json.dumps(diagnostics, ensure_ascii=False, indent=2))
    if args.show:
        card_id = f"WO-C-OPEN-COMP-{args.show:05d}"
        source = aramaic if args.show < FIRST_SERIAL + len(ARAMAIC_DECISIONS) else egyptian
        match = re.search(rf"(?ms)^### {re.escape(card_id)}:.*?(?=^### |^<!-- |\Z)", source)
        assert match
        print("\n" + match.group().rstrip())
    if args.apply:
        append(ARAMAIC, f"{MARKER}:ARAMAIC", aramaic)
        append(EGYPTIAN, f"{MARKER}:EGYPTIAN", egyptian)
        append(REPORT, f"{MARKER}:REPORT", report)
        print(f"APPENDED: {ARAMAIC.relative_to(ROOT)}")
        print(f"APPENDED: {EGYPTIAN.relative_to(ROOT)}")
        print(f"APPENDED: {REPORT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
