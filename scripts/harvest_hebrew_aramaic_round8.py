#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Render lane C round 8: move from exhausted short Aramaic opens to Hebrew.

The renderer is append-only.  It recomputes the current pure-open ending-card
queue, proves that no untreated short Aramaic item remains after round 7, then
writes two Hebrew completion batches of forty cards each.  It never ships,
commits, stages, or updates derived publication data.
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

import fan_any_script as FAN  # noqa: E402
import frozen_event as FE  # noqa: E402
import search_arabic_root_senses as AR  # noqa: E402


ARAMAIC = ROOT / "04-cross-linguistic" / "readings" / "aramaic.md"
HEBREW = ROOT / "04-cross-linguistic" / "readings" / "hebrew.md"
DB = ROOT / "cache" / "recovery_pipeline" / "inventory-v5.sqlite"
MARKER = "LANE-C-HEBREW-ROUND8-2026-08-17"
MAX_CARD_BYTES = 5 * 1024
FIRST_SERIAL = 42
POSITIVE = {"ROOT-TRACE", "NUCLEUS-TRACE", "ROOT-ECHO", "NUCLEUS-ECHO", "FLOOR-TRACE"}


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


def p(member_id: str, candidate: str, verdict: str, keywords: str,
      zero: str, sound: str, orbit: str, reason: str) -> Decision:
    assert verdict in POSITIVE
    return Decision(member_id, candidate, verdict, "READY",
                    tuple(part for part in keywords.split("|") if part),
                    zero, sound, orbit, reason)


def g(member_id: str, candidate: str, state: str, keywords: str,
      zero: str, sound: str, orbit: str, reason: str) -> Decision:
    return Decision(member_id, candidate, "OPEN-CANDIDATE", state,
                    tuple(part for part in keywords.split("|") if part),
                    zero, sound, orbit, reason)


def f(member_id: str, candidate: str, reason: str) -> Decision:
    return Decision(
        member_id, candidate, "FORM-OF-ISOLATED", "FORM-OF-ISOLATED", (),
        "تصنيف المصدر أو نص المعنى يصرح بأن العضو صورة صرفية أو إملائية تابعة؛ لم تُحوّل إلى شاهد معجمي ثان.",
        "الإغلاق بنيوي سابق لمسار الصوت؛ لم يُخترع صف ولم ترث الصورة حكم اللمة.",
        "الصورة التابعة تحفظ إحالتها إلى اللمة ولا تضيف صلة مستقلة.", reason,
    )


def t(member_id: str, candidate: str, verdict: str, reason: str) -> Decision:
    return Decision(
        member_id, candidate, verdict, verdict, (),
        "حُفظ العضو بسطحه وتصنيف قاموس الفرع قبل أي تعرية؛ الإغلاق خاص بهذا العضو وحده.",
        "لم يُستعمل التشابه السطحي لإصدار نسب؛ مسار المصدر المسمى هو الحاكم في هذا الإغلاق.",
        "المسار البنيوي أو النقلي المسمى يعزل العضو ولا يورث حكمًا لمتجانس أو مركب.", reason,
    )


# This is the reproducible shortest-skeleton order selected below.  Positive
# decisions were hand-read against the branch gloss, the named source route,
# the frozen rows, and two independent Arabic witnesses.  Form and loan
# closures use only the explicit source classification of the named member.
DECISIONS: tuple[Decision, ...] = (
    t("kaikki_hebrew:12630:en-פוסה-he-noun-NgBd4pwo", "فس", "LOANWORD-THIRD-PARTY-TO-BRANCH",
      "قاموس الفرع يصرح بقرض إنجليزي مرده النهائي إلى Malagasy fosa."),
    p("kaikki_hebrew:8037:en-נדה-he-noun-F9LQLR4d", "ندد", "ROOT-ECHO", "شرد|نفر|تفرق",
      "رُد الاسم إلى الجذر المنشور נ־ד־ד؛ التضعيف من مادة الجذر لا من تكرار آلي.",
      "נ↔ن عبر IDN-03، وד↔د عبر IDN-09؛ الجذر المضعف محفوظ.",
      "حالة الانفصال والاجتناب تلتقي ند البعير: شرد ونفر وتفرق.",
      "مدار واحد من الانفصال الاجتماعي إلى الشرود عن الجماعة."),
    p("kaikki_hebrew:6130:en-כמה-he-det-np-T31Cc", "كم", "ROOT-TRACE", "عدد|استفهام|كم",
      "الهاء الصامتة علامة كتابة في الصيغة؛ بقيت أداة الاستفهام k-m كما يسميها المصدر.",
      "כ↔ك عبر IDN-13، وמ↔م عبر IDN-02.",
      "How much/how many هي كم الاستفهامية عن العدد نفسه.",
      "المصدر نفسه يقارن العربية كم، والمعنى العددي مباشر."),
    p("kaikki_hebrew:1958:en-שפה-he-noun-6jfE0udx", "شفه", "ROOT-TRACE", "الشفة|الشفاه|الفم",
      "حُفظت ש־פ־ה كاملة؛ المصدر يعيدها إلى *śapat- ولا يخلطها بحس اللغة.",
      "שׂ↔ش عبر SIB-07، وפ↔ف عبر LAB-07، وה↔ه عبر IDN-20.",
      "lip في العضو هي الشفة التي تحيط بالفم في العربية.",
      "اكتمل الجذر والمعنى مع فصل حس العضو عن متجانس اللغة."),
    t("kaikki_hebrew:7432:en-אליה-he-name-3eyaufvu", "اليا", "OUT-OF-SCOPE",
      "المصدر يصنف العضو اسم شخص مختصرًا من Elijah؛ عُزل العلم وحده."),
    f("kaikki_hebrew:12766:en-כולה-he-pron-YTeD9ZfG", "كل",
      "form of כָּל مع ضمير ملكية مؤنث مفرد مسمى."),
    p("kaikki_hebrew:414:en-אתה-he-pron-TMwdrlNN", "أنت", "ROOT-TRACE", "أنت|ضمير|مخاطب",
      "الصورة الأم المنشورة *ʔanta تستعيد النون التي سقطت في سطح العبرية.",
      "א↔أ عبر IDN-16، وנ↔ن عبر IDN-03 في *ʔanta، وת↔ت عبر IDN-11.",
      "you/thou للمخاطب المفرد المذكر هو أنت في العربية.",
      "المقارنة العربية منصوصة في أصل العضو، والنون مستعادة من الصورة الأم."),
    t("kaikki_hebrew:11984:en-בוסה-he-noun-u~4YYF3y", "بوس", "SEMITIC-SOURCE-TRANSMISSION",
      "قاموس الفرع يصرح بأن Hebrew בוסה مقترضة من Arabic بوسة؛ المصدر السامي مسمى."),
    t("kaikki_hebrew:1855:en-בירה-he-noun-HYtM-FTN", "بير", "LOANWORD-THIRD-PARTY-TO-BRANCH",
      "قاموس الفرع يسمي German Bier مانحًا مباشرًا؛ التأثير العربي أو العثماني في النهاية احتمال حاشي."),
    p("kaikki_hebrew:7064:en-גרה-he-noun-bQYHiJii", "جرر", "ROOT-TRACE", "الجرة|الاجترار|البعير",
      "نهاية الاسم خارج المادة، والتضعيف العربي يعيد الجذر ג־ר־ר الذي يدل عليه الاجترار.",
      "ג↔ج عبر GUT-03، وר↔ر عبر IDN-01؛ الراء الثانية بناء المضاعف العربي.",
      "Cud هي الجرة: ما يخرجه البعير من بطنه للاجترار.",
      "المعنى المعجمي المباشر يحصر الحكم في حس الطعام المرتد."),
    p("kaikki_hebrew:6406:en-דלה-he-verb-kKDP5lTv", "دلو", "ROOT-ECHO", "الدلو|البئر|استقى",
      "حُفظت الرجل اللينة في الفعل، وقُرئ اشتقاقه من bucket أو من التدلي كما عرضه المصدر.",
      "ד↔د عبر IDN-09، وל↔ل عبر IDN-04؛ الرجل اللينة تقيد الحكم ECHO.",
      "استخراج الماء من البئر يلتقي إدلاء الدلو ثم جذبها.",
      "الالتقاء في سلسلة حركة الدلو خطوة دلالية واحدة."),
    p("kaikki_hebrew:774:en-יין-he-noun-tY6viEKP", "وين", "ROOT-ECHO", "العنب|الزبيب|وين",
      "حُفظ الأصل المنشور *wayn-، ولم يُختزل السطح y-y-n إلى نواة مصنوعة.",
      "*w↔ו/י عبر GLD-01 مع נ↔ن عبر IDN-03؛ الأصل المنشور يقيد المسار الفردي.",
      "wine المصنوع من العنب يلتقي الوين العربي: العنب الأسود أو الأبيض والزبيب.",
      "انتقال واحد من الثمرة المسماة إلى شرابها، لذلك ECHO لا TRACE."),
    t("kaikki_hebrew:3915:en-סיכה-he-noun-8k1Fg61i", "سكة", "INTRA-HOUSE-TRANSFER",
      "المصدر يرجح Akkadian sikkatum مانحًا ويسمي العربية سكة قرينة داخل البيت السامي."),
    f("kaikki_hebrew:7206:en-שבה-he-verb-7y5LWzK2", "شوب",
      "Third-person feminine singular past of שָׁב مصرح به."),
    f("kaikki_hebrew:15989:en-שיבה-he-noun-i2Dk6tVE", "شوب",
      "verbal noun of שָׁב مصرح به؛ لا شاهد جذري ثان."),
    p("kaikki_hebrew:618:en-אות-he-noun-827aZGDv", "أيي", "ROOT-ECHO", "الآية|العلامة|الرمز",
      "حُفظ אות، واستعملت المقارنة المنشورة *awayat- ↔ Arabic آية دون إنشاء صف عام.",
      "المصدر يصرح بالمقارنة الفردية؛ א↔أ عبر IDN-16، والرجل اللينة مقيدة بالأصل المنشور.",
      "letter بوصفها رمزًا تلتقي الآية بوصفها علامة دالة.",
      "صلة فردية ذات رجل لينة، فلا ترقى إلى TRACE."),
    p("kaikki_hebrew:617:en-אות-he-noun-PqFwVDTJ", "أيي", "ROOT-ECHO", "الآية|العلامة|الدلالة",
      "حُفظ حس sign/omen مستقلًا عن حس letter، واستعمل الأصل *awayat- المنشور.",
      "المصدر يصرح بالمقارنة الفردية مع Arabic آية؛ لا يستخرج منها صف عام.",
      "sign/omen هو الآية والعلامة الدالة في العربية.",
      "صلة فردية ذات رجل لينة، والحكم لهذا المتجانس وحده."),
    g("kaikki_hebrew:11963:en-אימה-he-noun-vXeIkdvo", "أيم", "SEMANTIC-GAP", "الخوف|الرعب|أيم",
      "حُفظ الرسم א־י־מ ولم يُخلط بعضو الأم ذي الرسم القريب.",
      "א↔أ عبر IDN-16، وי↔ي عبر IDN-23، وמ↔م عبر IDN-02.",
      "قاموس الفرع يعطي terror، لكن مروحة أيم العربية تدور على فقد الزوج والحية لا الرعب نفسه.",
      "لم يثبت مدار دلالي مباشر بين terror وحواس أيم المقروءة."),
    f("kaikki_hebrew:11965:en-אימה-he-noun-t1YCub4r", "ام",
      "singular form of אֵם with third-person feminine singular possessor مصرح به."),
    f("kaikki_hebrew:879:en-אלה-he-noun-tnCMEb-B", "أله",
      "قاموس الفرع يسمي العضو defective spelling of אלוה."),
    p("kaikki_hebrew:3789:en-אלוה-he-noun-m0LNC9uk", "أله", "ROOT-TRACE", "إله|المعبود|الله",
      "حُفظ א־ל־ה كاملًا كما في الصورة السامية المنشورة *ʾilh.",
      "א↔أ عبر IDN-16، وל↔ل عبر IDN-04، وה↔ه عبر IDN-20.",
      "a god هو الإله والمعبود في العربية.",
      "المصدر يصرح بالمقارنة العربية، والمعنى مباشر."),
    g("kaikki_hebrew:10252:en-אמה-he-noun-bA4RxTW5", "امم", "SEMANTIC-GAP", "الساعد|الذراع|أمة",
      "حُفظ عضو forearm مستقلًا عن متجانسات الأم والأمة ووحدة القياس.",
      "א↔أ عبر IDN-16، وמ↔م عبر IDN-02؛ التضعيف العربي مرشح بنيوي فقط.",
      "معنى forearm لا يلتقي حواس أمم العربية المقروءة بمدار واحد مقنع.",
      "رجل المعنى غائبة بعد فصل المتجانسات."),
    f("kaikki_hebrew:6671:en-באה-he-verb-qK3FNcda", "بوء",
      "Third-person feminine singular past of בָּא مصرح به."),
    f("kaikki_hebrew:6672:en-באה-he-verb-pDGUiGA-", "بوء",
      "Feminine singular present participle of בָּא مصرح به."),
    t("kaikki_hebrew:375:en-בית-he-noun-HDFib1aK", "بيت", "LOANWORD-THIRD-PARTY-TO-BRANCH",
      "حس byte مقترض من English byte ومشابهته לبيت العبرية لا تجعله حس house."),
    t("kaikki_hebrew:1526:en-ביתא-he-noun-DEJMQgyh", "بيتا", "LOANWORD-THIRD-PARTY-TO-BRANCH",
      "alternative form of beta، والمصدر يسمي Ancient Greek βῆτα مانحًا."),
    f("kaikki_hebrew:657:en-בנה-he-noun-6hhH8TI3", "بن",
      "singular form of בֵּן with feminine singular possessor مصرح به."),
    f("kaikki_hebrew:7065:en-גרה-he-verb-okZhIIcE", "جر",
      "Third-person feminine singular past of גָּר مصرح به."),
    f("kaikki_hebrew:7066:en-גרה-he-verb-3cu5r7TQ", "جر",
      "Feminine singular present participle of גָּר مصرح به."),
    f("kaikki_hebrew:12549:en-דוחה-he-verb-HScJ5OF~", "دحو",
      "Masculine singular present participle of דָּחָה مصرح به."),
    f("kaikki_hebrew:12550:en-דוחה-he-verb-~eGQAu2J", "دحو",
      "Feminine singular present participle of דָּחָה مصرح به."),
    t("kaikki_hebrew:5696:en-הורה-he-noun-3bXrHRXg", "هور", "LOANWORD-THIRD-PARTY-TO-BRANCH",
      "قاموس الفرع يرد hora إلى Yiddish ثم Greek χορός."),
    t("kaikki_hebrew:15933:en-וילה-he-noun-JJnmPLJp", "ويل", "LOANWORD-THIRD-PARTY-TO-BRANCH",
      "قاموس الفرع يصرح بالقرض من Latin villa."),
    t("kaikki_hebrew:16201:en-זוטה-he-noun-oUCSBKCI", "زط", "INTRA-HOUSE-TRANSFER",
      "قاموس الفرع يصرح بالقرض من Aramaic זוּטָא؛ انتقال داخل البيت السامي."),
    f("kaikki_hebrew:3619:en-זונה-he-verb-5Gc7VkHy", "زنو",
      "Masculine singular present participle of זָנָה مصرح به."),
    f("kaikki_hebrew:3620:en-זונה-he-verb-MhmfdUW~", "زنو",
      "Feminine singular present participle of זָנָה مصرح به."),
    t("kaikki_hebrew:1759:en-זין-he-noun-KkElWAT8", "زين", "LOANWORD-THIRD-PARTY-TO-BRANCH",
      "حس arms/weapons مردود في المصدر إلى قرض إيراني قديم."),
    t("kaikki_hebrew:1760:en-זין-he-intj-c-RSDSED", "زين", "LOANWORD-THIRD-PARTY-TO-BRANCH",
      "الحس الاعتراضي مشتق من المتجانس المقترض إيرانيًا؛ عُزل العضو وحده."),
    f("kaikki_hebrew:2862:en-טובה-he-adj-u8wc-hEM", "طيب",
      "feminine singular indefinite form of טוב مصرح به."),
    f("kaikki_hebrew:3592:en-כפה-he-noun-TXk~2Opq", "كف",
      "singular form of כף with feminine singular possessor مصرح به."),

    f("kaikki_hebrew:3593:en-כפה-he-verb-8Ib7vvrD", "كف",
      "Third-person feminine singular past of כף مصرح به."),
    p("kaikki_hebrew:1872:en-מאה-he-num-uZrgUxbM", "مأي", "NUCLEUS-TRACE", "مائة|مئة|المائة",
      "الصورة الأم *miʾat- تفصل النهاية العددية وتحفظ النواة m-ʾ.",
      "מ↔م عبر IDN-02، وא↔ء عبر IDN-16؛ الحكم للنواة م־ء لا للجذر السطحي كله.",
      "hundred هي المائة العددية نفسها في العربية.",
      "اكتملت النواة والمعنى، وبقيت النهايات خارج حكم الجذر الكامل."),
    p("kaikki_hebrew:492:en-אור-he-noun-iucZCQxt", "أور", "ROOT-TRACE", "الأوار|النار|الوهج",
      "حُفظ א־ו־ר كاملًا؛ قاموس الفرع يقارن Arabic أُوار.",
      "א↔أ عبر IDN-16، وו↔و عبر IDN-10، وר↔ر عبر IDN-01.",
      "visible light يلتقي الأوار في ضوء النار ووهجها.",
      "الحكم لحس الضوء وحده، لا لمركبات الأسرة."),
    t("kaikki_hebrew:15:en-מילה-he-noun-pkqug~zr", "ميل", "LOANWORD-THIRD-PARTY-TO-BRANCH",
      "حس ash tree مقترض من Ancient Greek μελία."),
    p("kaikki_hebrew:323:en-מים-he-noun-KWSt58Ho", "ميه", "NUCLEUS-TRACE", "الماء|مياه|المياه",
      "الأصل المنشور *māy- يحفظ m-y؛ ميم الجمع/الصيغة في السطح لا تدخل النواة.",
      "מ↔م عبر IDN-02، وי↔ي عبر IDN-23؛ الحكم للنواة م־ي.",
      "water هو الماء والمياه في العربية بلا انتقال دلالي.",
      "اكتملت النواة والمعنى، ولم يُدع جذر سطحي كامل."),
    f("kaikki_hebrew:8040:en-נידה-he-noun-7tUOn-zz", "ندد",
      "قاموس الفرع يسمي العضو excessive spelling of נִדָּה."),
    t("kaikki_hebrew:6021:en-נישה-he-noun-MDo6-ZvI", "نيش", "LOANWORD-THIRD-PARTY-TO-BRANCH",
      "قاموس الفرع يرد niche إلى French ثم Old French وLatin."),
    f("kaikki_hebrew:16716:en-סהרה-he-noun-MdAP7tYd", "سهر",
      "singular form of סַהַר with feminine singular possessor مصرح به."),
    t("kaikki_hebrew:2576:en-פין-he-noun-ZPRqdSah", "بين", "LOANWORD-THIRD-PARTY-TO-BRANCH",
      "قاموس الفرع يصرح بالقرض من English pin."),
    g("kaikki_hebrew:9996:en-ציפה-he-verb-bbaRxNrr", "صفو", "SEMANTIC-GAP", "توقع|انتظر|صفا",
      "حُفظ حس to expect وحده، ولم يرث حواس الطفو أو الغطاء في المتجانسات.",
      "צ↔ص عبر IDN-19، وפ↔ف عبر LAB-07؛ الرجل اللينة محفوظة ولا تحسم المعنى.",
      "to expect لا يلتقي حواس صفو العربية في الخلوص والنقاء بمدار واحد.",
      "رجل المعنى غائبة بعد قراءة المتجانسات ومروحة صفو."),
    p("kaikki_hebrew:4719:en-קנה-he-verb-gpJd3tGU", "قني", "NUCLEUS-TRACE", "اقتنى|اكتسب|القنية",
      "حُفظ ק־נ، واختلاف الرجلين الضعيفتين يمنع ادعاء الجذر الكامل.",
      "ק↔ق عبر IDN-12، وנ↔ن عبر IDN-03؛ الحكم للنواة ق־ن.",
      "to buy/acquire يلتقي القنية والاقتناء والاكتساب.",
      "اكتملت النواة والمعنى، والجذر الكامل غير مدعى."),
    t("kaikki_hebrew:131:en-קפה-he-noun-NykNdKxN", "قهو", "SEMITIC-SOURCE-TRANSMISSION",
      "سلسلة المصدر تنتهي صراحة إلى Arabic قهوة عبر العثمانية والإيطالية والفرنسية."),
    f("kaikki_hebrew:555:en-ראה-he-verb-FSa60yQV", "رأي",
      "العضو موسوم form_of רָאָה، ومعناه صيغة الفعل نفسه."),
    f("kaikki_hebrew:2969:en-רוצה-he-verb-H6E0YxYj", "رضي",
      "masculine singular present participle of רצה مصرح به."),
    f("kaikki_hebrew:2970:en-רוצה-he-verb-feV7WNk5", "رضي",
      "feminine singular present participle of רצה مصرح به."),
    p("kaikki_hebrew:3440:en-רצה-he-verb-CVriWWbX", "رضي", "ROOT-ECHO", "رضي|اختار|قبل",
      "حُفظت المقارنة الفردية المنشورة مع Arabic رضي والرجل اللينة.",
      "ר↔ر عبر IDN-01، وצ↔ض عبر DENT-02 في المقارنة السامية، والرجل اللينة تقيد ECHO.",
      "want يتجه إلى المختار، ورضي الشيء قبله واختاره واستحسنه.",
      "مدار الميل إلى الشيء خطوة واحدة، لذلك ECHO."),
    p("kaikki_hebrew:7204:en-שבה-he-verb-pu9ug9~W", "سبي", "ROOT-TRACE", "سبى|السبي|الأسر",
      "حُفظ ש־ב־ה، والمصدر يقارن Arabic سبى مباشرة.",
      "ש↔س عبر SIB-01، وב↔ب عبر IDN-05؛ الرجل اللينة مقيدة بالمقارنة المنشورة.",
      "to capture/take captive هو السبي والأسر نفسه.",
      "المعنى مباشر والمقارنة العربية منصوصة."),
    f("kaikki_hebrew:796:en-שים-he-verb-6E~Rw8B~", "سم",
      "Masculine singular imperative of שָׂם مصرح به."),
    f("kaikki_hebrew:16821:en-שלוה-he-noun-Wf~XFqqd", "سلو",
      "قاموس الفرع يسمي العضو defective spelling of שלווה."),
    f("kaikki_hebrew:11226:en-שמה-he-noun-TMpF8Atg", "اسم",
      "singular form of שֵׁם with feminine singular possessor مصرح به."),
    p("kaikki_hebrew:472:en-שנה-he-noun-qEG2w93a", "سنه", "ROOT-TRACE", "السنة|العام|السنين",
      "الصورة الأم المنشورة *šanat- تحفظ المادة والنهاية المؤنثة.",
      "ש↔س عبر SIB-01، وנ↔ن عبر IDN-03؛ النهاية المؤنثة مستعادة في الأصل.",
      "year هي السنة والعام نفسه في العربية.",
      "المعنى الزمني مباشر والمصدر السامي منشور."),
    g("kaikki_hebrew:4715:en-שתה-he-verb-5i9kA2DY", "شتت", "SEMANTIC-GAP", "شرب|الماء|شتت",
      "حُفظ ש־ת־ה ولم يُستبدل بالفعل العربي شرب لمجرد الترجمة.",
      "ש↔ش عبر IDN-21، وת↔ت عبر IDN-11، وה↔ه عبر IDN-20.",
      "to drink لا يلتقي حواس شتت العربية في التفرق والافتراق.",
      "الصوت مكتمل، لكن رجل المعنى غائبة في المروحة العربية."),
    p("kaikki_hebrew:1067:en-שבת-he-verb-~QgYB-gG", "سبت", "ROOT-ECHO", "السبت|السكون|القطع",
      "حُفظ ש־ב־ת كاملًا، وفُصل الفعل عن أسماء اليوم والصيغ التابعة.",
      "ש↔س عبر SIB-01، وב↔ب عبر IDN-05، وת↔ت عبر IDN-11.",
      "التوقف عن العمل والراحة يلتقيان القطع والسكون في مادة سبت.",
      "الالتقاء مداري بخطوة واحدة، لذلك ECHO."),
    t("kaikki_hebrew:650:en-שושנה-he-name-FI-tyJoQ", "ششن", "OUT-OF-SCOPE",
      "المصدر يصنف العضو اسم امرأة ويرده في النهاية إلى المصرية؛ عُزل العلم."),
    t("kaikki_hebrew:3221:en-סכין-he-noun-2YmD6aIQ", "سكين", "INTRA-HOUSE-TRANSFER",
      "قاموس الفرع يصرح بالقرض من Aramaic sakkīn؛ انتقال داخل البيت السامي."),
    t("kaikki_hebrew:9154:en-ספינה-he-noun-Uab~B0Ex", "سفين", "INTRA-HOUSE-TRANSFER",
      "قاموس الفرع يصرح بالقرض من Aramaic səp̄īntā ويذكر انتقال العربية سفينة منه."),
    p("kaikki_hebrew:3220:en-אחות-he-noun-GYDTkn8H", "اخت", "ROOT-TRACE", "الأخت|أخت|الشقيقة",
      "الصورة الأم *ʔaḫwat- تستعيد الواو الداخلية وتثبت مادة القرابة.",
      "א↔أ عبر IDN-16، وח↔خ عبر GUT-05، وת↔ت عبر IDN-11؛ الواو من الصورة الأم.",
      "sister هي الأخت والشقيقة في العربية.",
      "المصدر يقارن العربية أخت، والمعنى القرابي مباشر."),
    f("kaikki_hebrew:1231:en-שמות-he-noun-QV5DCdNM", "اسم",
      "plural indefinite form of שֵׁם مصرح به."),
    f("kaikki_hebrew:1232:en-שמות-he-noun-VNhBUxiM", "اسم",
      "plural construct state form of שֵׁם مصرح به."),
    f("kaikki_hebrew:3674:en-אחים-he-noun-umeTHspa", "اخ",
      "plural indefinite form of אָח مصرح به."),
    f("kaikki_hebrew:1295:en-אחת-he-num-UsD5qv4K", "احد",
      "feminine of אֶחָד مصرح به."),
    f("kaikki_hebrew:353:en-אלוהים-he-noun-05qirz-2", "أله",
      "plural indefinite form of אֱלוֹהַּ مصرح به."),
    f("kaikki_hebrew:5676:en-באים-he-verb-E15UbMV5", "بوء",
      "masculine plural present of בָּא مصرح به."),
    f("kaikki_hebrew:6347:en-בנות-he-noun-YwShl6Wl", "بنت",
      "plural indefinite form of בַּת مصرح به."),
    f("kaikki_hebrew:10687:en-בנין-he-noun-0nydey2W", "بني",
      "قاموس الفرع يسمي العضو defective spelling of בניין."),
    f("kaikki_hebrew:4606:en-גנים-he-noun-nO3MjBOw", "جن",
      "plural indefinite form of גֶּן مصرح به."),
    f("kaikki_hebrew:4079:en-גרים-he-noun-wr8ZKxKW", "جر",
      "plural indefinite form of גֵּר مصرح به."),
    f("kaikki_hebrew:7059:en-גרת-he-noun-puOrYPA-", "جر",
      "singular construct state form of גָּרָה مصرح به."),
    f("kaikki_hebrew:7060:en-גרת-he-noun-n9Toca0X", "جر",
      "singular construct state form of גֵּרָה مصرح به."),
    f("kaikki_hebrew:7061:en-גרת-he-verb-Wf3ADE5y", "جر",
      "Second-person masculine singular past of גָּר مصرح به."),
)


EXPECTED_IDS = tuple(item.member_id for item in DECISIONS)


def blocks(text: str) -> list[tuple[int, str]]:
    return [(match.start(), match.group()) for match in re.finditer(
        r"(?ms)^### .*?(?=^### |\Z)", text
    )]


def endcard_inventory(text: str, language: str) -> dict[str, dict[str, object]]:
    found: dict[str, dict[str, object]] = {}
    all_blocks = blocks(text)
    prefix = f"kaikki_{language}:"
    for position, block in all_blocks:
        if "بطاقة النهاية" not in block:
            continue
        member_match = re.search(rf"`({re.escape(prefix)}[^`]+)`", block)
        if not member_match:
            continue
        member_id = member_match.group(1)
        family_match = re.search(rf"`({language}:family:[0-9a-f]+)`", block)
        number_match = re.search(r"بطاقة النهاية (\d+)", block)
        found[member_id] = {
            "member_id": member_id,
            "family_id": family_match.group(1) if family_match else "غير مسمى في العنوان",
            "endcard": int(number_match.group(1)) if number_match else 0,
            "position": position,
        }
    for member_id, item in found.items():
        later = []
        for position, block in all_blocks:
            if position < int(item["position"]) or member_id not in block:
                continue
            verdicts = re.findall(r"^- الحكم \(استكشاف\): (.+)$", block, flags=re.M)
            if verdicts:
                later.append((position, verdicts[-1], block.splitlines()[0]))
        if later:
            item["latest_position"], item["latest_verdict"], item["latest_heading"] = later[-1]
        else:
            item["latest_position"] = int(item["position"])
            item["latest_verdict"] = ""
            item["latest_heading"] = ""
    return found


def load_entries(language: str) -> tuple[dict[str, dict], dict[str, list[dict]]]:
    connection = sqlite3.connect(DB)
    connection.row_factory = sqlite3.Row
    try:
        exact: dict[str, dict] = {}
        by_word: dict[str, list[dict]] = collections.defaultdict(list)
        rows = connection.execute(
            "SELECT entry_id,headword,romanization,pos,gloss,etymology,loan_hint,"
            "form_of,form_targets_json,skeleton,morphology_status FROM entries "
            "WHERE language=?", (language,)
        )
        for row in rows:
            value = dict(row)
            exact[str(row["entry_id"])] = value
            by_word[str(row["headword"])].append(value)
        return exact, dict(by_word)
    finally:
        connection.close()


def select_short_pure_opens(text: str, language: str, exact: dict[str, dict]) -> list[dict]:
    inventory = endcard_inventory(text, language)
    selected = []
    for member_id, item in inventory.items():
        latest = str(item.get("latest_verdict") or "")
        heading = str(item.get("latest_heading") or "")
        if "OPEN-CANDIDATE" not in latest or any(token in latest for token in POSITIVE):
            continue
        if heading.startswith("### WO-C-OPEN-COMP-"):
            continue
        entry = exact[member_id]
        word = str(entry["headword"])
        skeleton = FAN.skeleton(word, "north")
        fan = FAN.fan(word, "north")
        if not (2 <= len(skeleton) <= 4) or not fan:
            continue
        selected.append({**item, **entry, "surface_skeleton": "".join(skeleton), "fan": fan})
    selected.sort(key=lambda item: (len(str(item["surface_skeleton"])), int(item["position"])))
    return selected


def folded(value: str) -> str:
    return AR.ARABIC_MARKS.sub("", value)


def excerpt(definition: str, keywords: tuple[str, ...], limit: int = 150) -> str:
    value = re.sub(r"\s+", " ", definition).strip()
    positions = [folded(value).find(folded(keyword)) for keyword in keywords
                 if folded(value).find(folded(keyword)) >= 0]
    center = min(positions) if positions else 0
    left = max(0, center - 45)
    right = min(len(value), left + limit)
    left = max(0, right - limit)
    return (("…" if left else "") + value[left:right].strip(" ،؛:")
            + ("…" if right < len(value) else ""))


def witnesses(matches: list[dict], keywords: tuple[str, ...]) -> list[dict]:
    by_source: dict[str, list[dict]] = collections.defaultdict(list)
    for item in matches:
        source_id = AR.canonical_source_id(str(item.get("source") or ""))
        if source_id:
            by_source[source_id].append(item)
    ranked = []
    for priority, source_id in enumerate(AR.SOURCE_PRIORITY):
        items = by_source.get(source_id) or []
        if not items:
            continue
        chosen = max(items, key=lambda item: (
            sum(folded(keyword) in folded(str(item.get("definition") or ""))
                for keyword in keywords),
            len(str(item.get("definition") or "")),
        ))
        definition = folded(str(chosen.get("definition") or ""))
        hits = sum(definition.count(folded(keyword)) for keyword in keywords)
        distinct = sum(folded(keyword) in definition for keyword in keywords)
        ranked.append((-distinct, -hits, priority, source_id, chosen))
    ranked.sort()
    return [{**item, "source_label": AR.SOURCE_LABELS[source_id]}
            for _, _, _, source_id, item in ranked[:2]]


def event_line(candidate: str) -> str:
    tiers = FE.all_tiers(candidate)
    if not tiers:
        normalized = candidate.translate(str.maketrans("أإؤئآ", "ءءءءء"))
        tiers = FE.all_tiers(normalized)
    assert tiers, f"No frozen event for {candidate}"
    return tiers[0].line() + f"؛ عُرضت {len(tiers)} درجات واختيرت المعلنة."


def render_card(serial: int, queue_rank: int, item: dict, decision: Decision,
                by_word: dict[str, list[dict]], arabic_matches: dict[str, list[dict]]) -> str:
    word = str(item["headword"])
    read = str(item["romanization"] or "").strip() or "بلا رومنة منشورة"
    gloss = re.sub(r"\s+", " ", str(item["gloss"])).strip()
    etym = re.sub(r"\s+", " ", str(item["etymology"] or "")).strip()
    homographs = by_word[word]
    homograph_text = "؛ ".join(
        f"{entry['pos']} «{str(entry['gloss'])[:62]}»" for entry in homographs[:4]
    )
    if len(homographs) > 4:
        homograph_text += f"؛ والباقي {len(homographs) - 4} قُرئ ولم يُنسخ"
    ranked = FAN.rank(word, list(item["fan"]), "north", "hebrew")
    selected_rank = next((rank for rank, (candidate, _) in enumerate(ranked, 1)
                          if candidate == decision.candidate), None)
    membership = (f"المرشح داخلها في الرتبة {selected_rank}"
                  if selected_rank is not None else
                  "المقابل خارج سطح المروحة؛ استُعيد من صرف الفرع أو الأصل المسمى")
    top = "، ".join(candidate for candidate, _ in ranked[:8]) or "لا مرشح"

    root = AR.normalize_root(decision.candidate)
    matches = arabic_matches.get(root, [])
    fan_status = AR.independent_fan(matches) if matches else {"judgment_ready": False}
    chosen_witnesses = witnesses(matches, decision.keywords)
    witness_text = "؛ ".join(
        f"قال {entry['source_label']}: «{excerpt(str(entry.get('definition') or ''), decision.keywords)}»"
        for entry in chosen_witnesses
    ) or "لا شاهد عربي عامل؛ والحكم لا يدعي صلة موجبة"

    if decision.verdict in POSITIVE or decision.verdict == "OPEN-CANDIDATE":
        frozen = event_line(decision.candidate)
    else:
        frozen = ("- الحدث المجمّد: لم يُستعمل بوابة؛ "
                  "الإغلاق بنيوي أو نقلي لا حكم صلة معجمي موجب.")
    if decision.verdict in POSITIVE:
        assert len(chosen_witnesses) == 2, (
            f"Positive card {serial} lacks two Arabic sources for {decision.candidate}"
        )
        filter_line = "اكتملت أرجل الصوت والحدث ومعنى الفرع في المدار المكتوب؛ لا شرط رابع."
    elif decision.verdict == "OPEN-CANDIDATE":
        filter_line = f"العائق القاتل مسمى: {decision.reason}"
    else:
        filter_line = f"الإغلاق النهائي مسمى: {decision.reason}"
    if decision.verdict in POSITIVE:
        arabic_radiance = "قُرئت المروحة كاملة؛ كُتب الشاهدان العاملان فقط."
    elif decision.verdict == "OPEN-CANDIDATE":
        arabic_radiance = "قُرئت المروحة كاملة؛ لم يثبت المدار المطلوب للحكم الموجب."
    else:
        arabic_radiance = "الإغلاق البنيوي أو النقلي لا يحتاج شاهدين عربيين."

    source = etym or "لا نص اشتقاق منشورًا في العضو"
    if len(source) > 240:
        source = source[:237].rstrip() + "…"
    form_note = (f"؛ form_of={item['form_of']}؛ targets={item['form_targets_json']}"
                 if int(item["form_of"]) else "")
    card_id = f"WO-C-OPEN-COMP-{serial:05d}"
    lines = [
        f"### {card_id}: `{word}` /{read}/ ↔ `{decision.candidate}`",
        "- إصدار البروتوكول: RECOVERY-v2 (2026-08-16) + ROUND8-COMPLETION (2026-08-17).",
        (f"- إحالة الجرد المفتوح: بطاقة النهاية {item['endcard']}؛ `{item['family_id']}`؛ "
         f"العضو `{decision.member_id}`؛ كانت أحدث حالته الخالصة `OPEN-CANDIDATE` قبل الإتمام."),
        f"- الكلمة في الفرع: عبرية `{word}` /{read}/، {item['pos']}، «{gloss}».",
        f"- أقدم صورة مستعادة: {source}{form_note}.",
        f"- الخطوة صفر (التعرية بصرف الفرع): {decision.zero}",
        (f"- المروحة المفحوصة في الذاكرة: الهيكل القصير `{item['surface_skeleton']}`؛ "
         f"قُرئت {len(ranked)} صورة مرتبة كلها ولم تُنسخ؛ أوائلها: {top}؛ {membership}."),
        (f"- مسح المعاني العربية: قُرئت {len(matches)} نتيجة للجذر `{root}` بما يكافئ "
         f"`--max-chars 0`؛ المروحة المستقلة "
         f"{'مكتملة' if fan_status.get('judgment_ready') else 'غير مكتملة'}؛ {witness_text}."),
        f"- المقابل من اللسان: `{decision.candidate}`.",
        f"- مسار الصوت: {decision.sound}",
        frozen,
        f"- المعنى من قاموس الفرع: «{gloss}» [الجرد المثبت؛ العضو المختار بعد فصل المتجانسات].",
        f"- جميع المتجانسات بنص الرسم ({len(homographs)}): {homograph_text}؛ الحكم للعضو المسمى وحده.",
        f"- المدار المكتوب باليد: {decision.orbit}",
        f"- المصفاة: {filter_line}",
        "- فصل المتجانسات والاقتراض: قُرئ الأصل والقرض والمتجانس؛ لا وراثة.",
        (f"- مؤشر اليتم: عضو بطاقة نهاية مفتوحة؛ family=`{item['family_id']}`؛ "
         f"round8-rank={queue_rank}/80."),
        f"- إشعاع الأسرة في الفرع: المتجانسات المقروءة={len(homographs)}؛ المختار=1.",
        f"- إشعاع الأسرة في العربية: {arabic_radiance}",
        "- جسور الاسترداد: الصرف؛ المروحة؛ الحدث؛ القاموس؛ الأصل؛ القرض؛ المتجانس؛ الاتجاه.",
        f"- عائق/تعليل الإغلاق: {decision.reason}",
        f"- حالة الإغلاق: {decision.state}.",
        f"- الحكم (استكشاف): {decision.verdict}.",
        "- ملاحظات: اكتملت عدستا الاسترداد والتشكيك؛ لا وراثة ولا شرط رابع.",
    ]
    card = "\n".join(lines) + "\n"
    size = len(card.encode("utf-8"))
    assert size <= MAX_CARD_BYTES, f"Card {card_id} is {size} bytes"
    return card


def render() -> tuple[str, dict]:
    aramaic_text = ARAMAIC.read_text(encoding="utf-8")
    hebrew_text = HEBREW.read_text(encoding="utf-8")
    if MARKER in hebrew_text:
        raise SystemExit("Round-eight marker already exists; append refused.")

    aramaic_exact, _ = load_entries("aramaic")
    aramaic_short = select_short_pure_opens(aramaic_text, "aramaic", aramaic_exact)
    assert not aramaic_short, (
        "Untreated short pure-open Aramaic queue is not exhausted: "
        + ", ".join(str(item["member_id"]) for item in aramaic_short[:5])
    )

    hebrew_exact, by_word = load_entries("hebrew")
    hebrew_queue = select_short_pure_opens(hebrew_text, "hebrew", hebrew_exact)
    selected = hebrew_queue[:80]
    ids = tuple(str(item["member_id"]) for item in selected)
    assert ids == EXPECTED_IDS, f"Round-eight Hebrew queue drifted:\nexpected={EXPECTED_IDS}\nactual={ids}"

    roots = {AR.normalize_root(item.candidate) for item in DECISIONS
             if item.verdict in POSITIVE or item.verdict == "OPEN-CANDIDATE"}
    arabic_matches = AR.matches_for_roots(AR.DEFAULT_RESOURCES, roots, None)
    cards = [
        render_card(FIRST_SERIAL + rank - 1, rank, item, decision, by_word, arabic_matches)
        for rank, (item, decision) in enumerate(zip(selected, DECISIONS), 1)
    ]

    body = [
        f"<!-- {MARKER}:START -->", "",
        "## الجولة الثامنة: الانتقال من المفتوح الآرامي القصير إلى المفتوح العبري (2026-08-17)", "",
        "### معلم الانتقال", "",
        ("أُعيد حساب الحالات الحية الأحدث: لا عضو آرامي خالص الفتح، قصير الهيكل، غير معالَج "
         "ببطاقة إتمام سابقة. أمّا الأحكام المركبة التي لها حكم جذري موجب، والفجوات الأربع "
         "المسماة في الجولة السابعة، فلم تُنسخ في بطاقات مكررة. لذلك وقع الانتقال المسمى "
         "`ARAMAIC-SHORT-OPEN-EXHAUSTED -> HEBREW-SHORT-OPEN`، وبدأ الترقيم من "
         "`WO-C-OPEN-COMP-00042`."), "",
        "### الدفعة الأولى: WO-C-OPEN-COMP-00042 إلى WO-C-OPEN-COMP-00081", "",
    ]
    for rank, card in enumerate(cards, 1):
        if rank == 41:
            body.extend([
                "### الدفعة الثانية: WO-C-OPEN-COMP-00082 إلى WO-C-OPEN-COMP-00121", "",
            ])
        body.append(card.rstrip())
        body.append("")
        if rank % 5 == 0:
            body.append(f"<!-- LANE-C-OPEN-COMP-R8-CHUNK-{rank // 5:03d}:END -->")
            body.append("")
    body.append(f"<!-- {MARKER}:END -->")
    appendix = "\n".join(body).rstrip() + "\n"

    verdicts = collections.Counter(item.verdict for item in DECISIONS)
    states = collections.Counter(item.state for item in DECISIONS)
    diagnostics = {
        "aramaic_short_pure_open_remaining": len(aramaic_short),
        "hebrew_short_pure_open_before": len(hebrew_queue),
        "cards": len(cards),
        "batches": [40, 40],
        "first_card": "WO-C-OPEN-COMP-00042",
        "last_card": "WO-C-OPEN-COMP-00121",
        "verdicts": dict(sorted(verdicts.items())),
        "states": dict(sorted(states.items())),
        "appendix_bytes": len(appendix.encode("utf-8")),
        "max_card_bytes": max(len(card.encode("utf-8")) for card in cards),
    }
    return appendix, diagnostics


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--show", type=int, choices=range(42, 122))
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    appendix, diagnostics = render()
    print(json.dumps(diagnostics, ensure_ascii=False, indent=2))
    if args.show:
        card_id = f"WO-C-OPEN-COMP-{args.show:05d}"
        match = re.search(rf"(?ms)^### {re.escape(card_id)}:.*?(?=^### |^<!-- |\Z)", appendix)
        assert match
        print("\n" + match.group().rstrip())
    if args.apply:
        current = HEBREW.read_text(encoding="utf-8")
        if MARKER in current:
            raise SystemExit("Round-eight marker appeared during render; append refused.")
        with HEBREW.open("a", encoding="utf-8", newline="\n") as handle:
            if not current.endswith("\n"):
                handle.write("\n")
            handle.write("\n" + appendix)
        print(f"APPENDED: {HEBREW.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
