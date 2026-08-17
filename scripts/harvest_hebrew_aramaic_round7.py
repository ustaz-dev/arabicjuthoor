#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Render lane C round 7: close Aramaic ``both`` and complete short opens.

The renderer is deliberately append-only.  It holds ``aramaic.md`` once in
memory, proves that all 426 ``both`` rows are represented, then selects the
current non-issued ending cards by shortest usable northern skeleton.  The
forty-one hand decisions below are the second-batch completion readings.
Nothing in this script commits, deposits, or ships.
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


READING = ROOT / "04-cross-linguistic" / "readings" / "aramaic.md"
SWEEP = ROOT / "04-cross-linguistic" / "exploration" / "phonetic-sweep-aramaic.json"
DB = ROOT / "cache" / "recovery_pipeline" / "inventory-v5.sqlite"
MARKER = "LANE-C-ARAMAIC-ROUND7-2026-08-17"
MAX_CARD_BYTES = 5 * 1024
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


def d(member_id: str, candidate: str, verdict: str, keywords: str,
      zero: str, sound: str, orbit: str, reason: str = "") -> Decision:
    state = "READY" if verdict in POSITIVE else verdict
    if verdict == "OPEN-CANDIDATE":
        raise ValueError("Use gap() so that every open verdict names its blocker")
    return Decision(member_id, candidate, verdict, state,
                    tuple(part.strip() for part in keywords.split("|") if part.strip()),
                    zero, sound, orbit, reason)


def gap(member_id: str, candidate: str, state: str, keywords: str,
        zero: str, sound: str, orbit: str, reason: str) -> Decision:
    return Decision(member_id, candidate, "OPEN-CANDIDATE", state,
                    tuple(part.strip() for part in keywords.split("|") if part.strip()),
                    zero, sound, orbit, reason)


# Order is the reproducible shortest-skeleton order asserted by select_open().
# Every positive/terminal choice is a hand reading.  In particular, older
# positives for siptā, ḥzīrtā, ʿakkāḇīṯā, and qṭīltā are not inherited across
# their still-unlicensed sound or morphology legs.
DECISIONS: tuple[Decision, ...] = (
    d("kaikki_aramaic:1633:en-צות-arc-verb-eB2aRjhi", "صوت", "ROOT-ECHO", "الصوت|يسمع",
      "أُبقيت الواو الأصلية في צות؛ الهيكل الكامل ṣ-w-t، لا الهيكل الآلي المختزل ṣ-t.",
      "צ↔ص عبر IDN-19، وו↔و عبر IDN-10، وת↔ت عبر IDN-11.",
      "الإصغاء وإدراك المسموع خطوة واحدة إلى الصوت الذي يُسمع.",
      "اكتملت الأرجل الثلاث مع حصر الحكم في فعل السماع."),
    d("kaikki_aramaic:804:en-טביא-arc-noun-fKzbWDBb", "ظبي", "ROOT-TRACE", "الظبي|غزال",
      "نُزعت ألف الحالة وحدها؛ بقيت ساق ṭ-b-y المنشورة من *ṯ̣aby(at-).",
      "ט↔ظ عبر DENT-08 في مرساته المسماة ظبي/*ṯ̣aby-، وב↔ب عبر IDN-05، وי↔ي عبر IDN-23.",
      "الطرفان يسمّيان الحيوان نفسه: الظبي أو الغزال.",
      "المصدر نفسه يقارن العربية ظبي، فاستوفى شرط DENT-08."),
    d("kaikki_aramaic:2045:en-מניא-arc-noun-m7hA339p", "من", "LOAN-ROUTE-ISOLATED", "المنا|الوزن",
      "نُزعت ألف الحالة، لكن اسم وحدة الوزن لم يُعامل جذرًا موروثًا.",
      "تشابه מ־נ وم־ن مقروء؛ لا يُستعمل لإصدار نسب مع بقاء الوحدة لفظًا رحالًا.",
      "المِنا اسم وزن ونقد يدور بين الألسن؛ اتصال الصورة لا يثبت اتجاه إرث.",
      "عُزل مسار اللفظ الرحال لوحدة الوزن بدل تحويله إلى شاهد جذر مستقل."),
    d("kaikki_aramaic:554:en-רחיא-arc-noun-13KoUaFt", "رحي", "NUCLEUS-TRACE", "الرحى|الرحا|طاحونة",
      "نُزعت ألف الحالة؛ حُفظت الياء الضعيفة، والحكم للنواة ر־ח لا لجذر ضعيف مدّعى.",
      "ר↔ر عبر IDN-01، وח↔ح عبر IDN-14؛ اختلاف الرجل الضعيفة يمنع ROOT-TRACE.",
      "רחיא والرحى اسمان لآلة الطحن نفسها، والنواة ر־ح محفوظة.",
      "اكتملت النواة والمعنى والمصدران من غير ترقية إلى جذر كامل."),
    d("kaikki_aramaic:2084:en-שיתא-arc-num-pNZtnEPK", "ست", "ROOT-TRACE", "ستة|الستة|ست",
      "نُزعت ألف الحالة، والياء حركة مد في الصيغة؛ بقيت مادة š-t العددية.",
      "ש↔س عبر SIB-01، وת↔ت عبر IDN-11.",
      "الفرع والعربية يسمّيان العدد ستة نفسه.",
      "أصل الفرع *šidṯatum ومعنى العدد يحصران الحكم في الحس العددي."),
    d("kaikki_aramaic:175:en-שמיא-arc-noun-BfUU-ufK", "سمو", "ROOT-TRACE", "السماء|سما|ارتفع",
      "نُزعت ألف الحالة وحدها؛ الياء لام الجذر في *šamāy- وليست لاحقة.",
      "ש↔س عبر SIB-01، وמ↔م عبر IDN-02، وי↔و/ي عبر GLD-01 في اللام المعتلة.",
      "السماء هي السماء التي تظل الأرض، ومادة سمو تسمي الارتفاع.",
      "الجذر المعتل الكامل متاح، فلا يُستبدل بنواة سم."),
    d("kaikki_aramaic:177:en-אריא-arc-name-W8Qm6Nge", "أري", "OUT-OF-SCOPE", "الأسد|البرج",
      "العضو المختار اسم برج Leo لا عضو אריא الاسمي بمعنى الأسد.",
      "العلم عُزل قبل استعمال أي صف؛ لا يرث حكم متجانسه الاسمي.",
      "اسم البرج وحدة علمية، لا شاهد جذر مستقل في هذا الجرد.",
      "إغلاق نطاق للعضو العلم وحده."),
    d("kaikki_aramaic:18:en-בית-arc-noun-PSSmc5RZ", "بيت", "FORM-OF-ISOLATED", "البيت",
      "قاعدة الجرد تسمي العضو construct form وتحيل صراحة إلى בַּיְתָא.",
      "لا يحتاج العضو الصرفي صفًا جديدًا؛ تُحفظ إحالة الصورة إلى اللمة.",
      "صيغة الإضافة ليست شاهدًا معجميًا ثانيًا لمعنى البيت.",
      "form_of=1 والهدف المسمى محفوظان في الجرد."),
    d("kaikki_aramaic:1822:en-בתיא-arc-noun--w5LYeRn", "بيت", "FORM-OF-ISOLATED", "البيت|البيوت",
      "قاعدة الجرد تسمي العضو plural of בַּיְתָא وتحيل إلى اللمة.",
      "لا يصدر حكم صوت لصيغة جمع مرتبطة بلمتها.",
      "الجمع لا يضيف شاهد جذر مستقلًا إلى عضو البيت المعجمي.",
      "form_of=1 والهدف المسمى محفوظان في الجرد."),
    d("kaikki_aramaic:386:en-דין-arc-adv-z9lt2S9-", "دين", "LOANWORD-THIRD-PARTY-TO-BRANCH", "لكن|بعد",
      "حُكم الظرف نفسه بعد فصل متجانس الربط.",
      "المصدر يسمي اليونانية القديمة δέ مانحًا؛ لا تُحوّل ד־י־ן إلى جذر عربي.",
      "معنى yet في الظرف وصل إلى الفرع بطريق قرض يوناني مسمى.",
      "Borrowed from Ancient Greek δέ إغلاق اتجاهي صريح."),
    d("kaikki_aramaic:387:en-דין-arc-conj-NrQXECuG", "دين", "LOANWORD-THIRD-PARTY-TO-BRANCH", "لكن|غير أن",
      "حُكم أداة الربط نفسها بعد فصل المتجانس الظرفي.",
      "المصدر يسمي اليونانية القديمة δέ مانحًا؛ لا تُحوّل الصورة إلى جذر عربي.",
      "معنى yet/but/however في الأداة وصل بطريق القرض المسمى.",
      "Borrowed from Ancient Greek δέ إغلاق اتجاهي صريح."),
    d("kaikki_aramaic:70:en-רבה-arc-adj-TLtyKNv7", "ربب", "ROOT-ECHO", "عظم|الكبير|زاد",
      "ألف الصفة خارج المادة؛ الساق r-b تقابل باب ربب المضعف.",
      "ר↔ر عبر IDN-01، وב↔ب عبر IDN-05؛ تضعيف الباء بناء الجذر العربي من الساق الثنائية.",
      "كبر الشيء وعظمه وزيادته مدار واحد في רבה وباب ربب.",
      "الجسر خطوة اشتقاقية واحدة، لذلك ECHO لا TRACE."),
    d("kaikki_aramaic:1093:en-עמתא-arc-noun-Pdq-m1bA", "عمم", "ROOT-TRACE", "العمة|عمته|أخت الأب",
      "نُزعت نهاية -tā الاسمية؛ بقيت ساق القرابة ʿ-m، وبابها العربي المضعف عمم.",
      "ע↔ع عبر SEM-03/IDN-15، وמ↔م عبر IDN-02؛ الميم الثانية بناء المضاعف العربي.",
      "العمة في الطرفين أخت الأب وعضو القرابة نفسه.",
      "المعنى المعجمي المباشر يقيّد الجذر ولا يعتمد نواة قرابية مصنوعة."),
    d("kaikki_aramaic:825:en-שבתא-arc-noun-C-qsyD2O", "سبت", "ROOT-TRACE", "السبت|اليهود|الأسبوع",
      "نُزعت ألف الحالة؛ بقي š-b-t كاملًا.",
      "ש↔س عبر SIB-01، وב↔ب عبر IDN-05، وת↔ت عبر IDN-11.",
      "Shabbat/Sabbath/Saturday هو السبت المسمى في العربية.",
      "حُصر الحكم في اليوم والشعيرة، لا سائر معاني سبت."),
    d("kaikki_aramaic:2083:en-איתתא-arc-noun-zy5b~x7w", "أنث", "ROOT-TRACE", "الأنثى|المرأة|النساء",
      "المصدر يعيد العضو إلى *ʾanθ-at- ويسمي العربية أُنثى؛ نهاية التأنيث لا تدخل الجذر.",
      "א↔أ عبر IDN-16، وנ↔ن عبر IDN-03 في الأصل المنشور، وת↔ث عبر DENT-01.",
      "woman في الفرع والأنثى/المرأة في العربية حس جنسي واحد.",
      "المقارنة العربية مطبوعة في أصل العضو، وشاهدا أنث مستقلان."),
    d("kaikki_aramaic:456:en-חדתא-arc-adj-EVB6Di9e", "حدث", "ROOT-TRACE", "حدث|حديث|الجديد",
      "نُزعت ألف الحالة؛ بقي ḥ-d-t.",
      "ח↔ح عبر IDN-14، وד↔د عبر IDN-09، وת↔ث عبر DENT-01.",
      "الجديد ما حدث بعد أن لم يكن؛ الصفة والفعل في مدار الجِدّة نفسه.",
      "حُصر الحكم في الجدة والحدوث، لا الخبر والكلام."),
    gap("kaikki_aramaic:334:en-סיפתא-arc-noun-isHvU4HK", "شفه", "LAW-GAP", "الشفة|الشفاه|الفم",
        "نُزعت -tā؛ الأصل المنشور *śapat- يحفظ الصوامت التي لا يجوز طيها.",
        "ס↔ش عبر SIB-07، وפ↔ف عبر LAB-07؛ أما ת↔ه في شفه فلا صف نافذ له.",
        "المعنى مباشر بين lip والشفة، لكن رجل الصوت الأخيرة غير مكتملة.",
        "تحتاج البطاقة صفًا موقعًا لـת الآرامية ↔ ه العربية أو تحليلًا مصدريًا يعزلهما."),
    d("kaikki_aramaic:269:en-תלתא-arc-num-5Asrj~fW", "ثلث", "ROOT-TRACE", "الثلاثة|ثلاث|ثلث",
      "نُزعت ألف الحالة؛ بقي t-l-t العددي.",
      "ת↔ث عبر DENT-01 في الموضعين، وל↔ل عبر IDN-04.",
      "الفرع والعربية يسمّيان العدد ثلاثة نفسه.",
      "الأصل *ṯalāṯatum يسند المسار الكامل."),
    d("kaikki_aramaic:268:en-תרין-arc-num-Y3SmX0x5", "ثني", "ROOT-ECHO", "اثنان|اثنين|ثنى",
      "حُفظت صورة trēn، وقُرئ الأصل المنشور *ṯin- قبالة بناء اثنين/ثني العربي.",
      "ת↔ث عبر DENT-01، وנ↔ن عبر IDN-03؛ الراء والبناء الضعيف يمنعان ادعاء TRACE سطحي.",
      "two في الفرع والاثنان في العربية العدد نفسه.",
      "صلة عددية مسندة بالأصل، مع بقاء الفرق الصرفي سبب تصنيفها ECHO."),
    d("kaikki_aramaic:396:en-אמין-arc-adj-lvZUnGuX", "أمن", "ROOT-ECHO", "أمين|الأمانة|الثقة",
      "حُفظت الهمزة الأصلية؛ لم تُسقط لصنع النواة من.",
      "א↔أ عبر IDN-16، وמ↔م عبر IDN-02، وנ↔ن عبر IDN-03.",
      "الثبات والاعتماد والثقة في الصفة تلتقي الوثاقة والأمانة العربية.",
      "خطوة واحدة من الوثاقة إلى الثبات؛ لذلك ROOT-ECHO."),
    d("kaikki_aramaic:1733:en-מרתא-arc-name-AZv9nLDk", "مرت", "OUT-OF-SCOPE", "مرثا|الاسم",
      "اختير عضو name «Martha» لا متجانس lady ولا bitterness.",
      "العلم عُزل قبل أي مقارنة صوتية ولا يرث حكم المتجانسين.",
      "اسم الشخص ليس مادة جذرية مستقلة في هذا الجرد.",
      "إغلاق نطاق للعضو العلم وحده."),
    d("kaikki_aramaic:315:en-רמתא-arc-name-KB3FI2Cd", "رمت", "OUT-OF-SCOPE", "الرملة|الاسم",
      "اختير عضو name «Arimathaea; Ramah» وفُصل عن hill وhigh.",
      "العلم عُزل قبل أي مقارنة صوتية ولا يرث حكم متجانسه الاسمي أو الوصفي.",
      "اسم الموضع ليس شاهد جذر مستقلًا في هذا الجرد.",
      "إغلاق نطاق للعضو العلم وحده."),
    d("kaikki_aramaic:352:en-תורתא-arc-noun-ckTNW84e", "ثور", "ROOT-TRACE", "الثور|البقر|البقرة",
      "نُزعت نهاية التأنيث والحالة -tā؛ بقي t-w-r من *ṯawr-.",
      "ת↔ث عبر DENT-01، وו↔و عبر IDN-10، وר↔ر عبر IDN-01.",
      "cow/heifer مؤنث الحيوان الذي تسمي مادته العربية الثور والبقر.",
      "الأصل السامي المنشور يثبت المادة، والفرق فرق جنس اشتقاقي مسمى."),
    d("kaikki_aramaic:1903:en-חנוכתא-arc-name-WvbaLZ49", "حنك", "OUT-OF-SCOPE", "حانوكا|التدشين",
      "العضو اسم عيد Hanukkah، لا فعل التدشين المعجمي.",
      "العلم عُزل قبل استعمال مرشح حنك الذي لا يسمي العيد في العربية.",
      "اسم العيد وحدة علمية لا شاهد جذر مستقلًا.",
      "إغلاق نطاق؛ لا وراثة من مادة חנך القريبة."),
    d("kaikki_aramaic:1284:en-כבריתא-arc-noun-IqPlD1SS", "كبرت", "SEMITIC-SOURCE-TRANSMISSION", "الكبريت|النار",
      "نُزعت نهاية الحالة، لكن الصورة لم تُعامل إرثًا عربيًا مباشرًا.",
      "حقل الأصل يسمي الأكادية kibrītu مانحًا؛ المسار أكادي→آرامي داخل البيت السامي.",
      "اسم الكبريت انتقل من صورة أكادية مسماة، فلا يُعاد احتسابه جذرًا مستقلًا.",
      "From Akkadian kibrītu إغلاق نقل سامي مصدري."),
    d("kaikki_aramaic:1109:en-לבונתא-arc-noun-kxD1hYOb", "لبن", "ROOT-TRACE", "اللبان|البخور",
      "نُزعت -tā، وحُللت الواو في بناء الاسم؛ بقيت مادة l-b-n.",
      "ל↔ل عبر IDN-04، وב↔ب عبر IDN-05، وנ↔ن عبر IDN-03.",
      "לבונתא واللبان اسمان للبخور نفسه.",
      "المعنى المباشر وشاهدا اللبان يكملان الجذر."),
    d("kaikki_aramaic:376:en-עסרין-arc-num-yGfml7aM", "عشر", "ROOT-TRACE", "عشرين|العشرة|عشر",
      "نُزعت لاحقة الجمع العددي -ין؛ بقي ʿ-s-r.",
      "ע↔ع عبر SEM-03، وס↔ش عبر SIB-07، وר↔ر عبر IDN-01.",
      "twenty في الفرع وعشرون العربية بناء العدد نفسه من عشرة.",
      "حُصر الحكم في العدد."),
    d("kaikki_aramaic:957:en-קדמיתא-arc-adj-9b695Yck", "قدم", "ROOT-ECHO", "قدم|تقدم|أمام|الأول",
      "نُزعت لاحقة الصفة المؤنثة -יתא؛ بقي q-d-m.",
      "ק↔ق عبر IDN-12، وד↔د عبر IDN-09، وמ↔م عبر IDN-02.",
      "first هو المتقدم السابق الواقع أمام غيره.",
      "الانتقال من التقدم المكاني إلى الرتبة الأولى خطوة واحدة؛ ROOT-ECHO."),
    d("kaikki_aramaic:381:en-שבעין-arc-num-r9g9T2DG", "سبع", "ROOT-TRACE", "سبعين|سبعة|السبع",
      "نُزعت لاحقة العدد -ין؛ بقي š-b-ʿ.",
      "ש↔س عبر SIB-01، وב↔ب عبر IDN-05، وע↔ع عبر SEM-03.",
      "seventy في الفرع وسبعون العربية بناء العدد نفسه من سبعة.",
      "حُصر الحكم في العدد."),
    d("kaikki_aramaic:2171:en-ארמיותא-arc-noun-t3E-OxOI", "ارم", "OUT-OF-SCOPE", "الآراميين|الآرامية",
      "العضو اسم مجتمع ونسبة مشتق من اسم الآراميين، لا مادة أصلية مستقلة.",
      "المشتق عُزل قبل استعمال الهيكل الصوتي.",
      "gentiledom/pagan society تسمية اجتماعية مشتقة لا شاهد جذر.",
      "إغلاق نطاق يحفظ اسم القوم في بطاقته ولا يورثه للمشتق."),
    d("kaikki_aramaic:2010:en-ברכתא-arc-noun-G5V54fgO", "برك", "FORM-OF-ISOLATED", "البركة|البركات",
      "قاعدة الجرد تسمي العضو plural of בִּרְכְּתָא وتحيل إلى اللمة.",
      "لا يصدر حكم صوت لصيغة جمع مرتبطة بلمتها.",
      "الجمع لا يضيف شاهدًا معجميًا مستقلًا لمادة البركة.",
      "form_of=1 والهدف المسمى محفوظان في الجرد."),
    gap("kaikki_aramaic:236:en-חזירתא-arc-noun-heFmkv19", "خنزير", "MORPHOLOGY-GAP", "الخنزير|الخنزيرة|السؤر",
        "نُزعت -tā؛ بقي ḥ-z-r، بينما المقابل الذي يسميه المصدر خنزيرة.",
        "ח↔خ عبر SEM-05، وז↔ز عبر IDN-22، وר↔ر عبر IDN-01؛ نون العربية لا يفسرها تحليل موقع.",
        "المعنى مباشر بين sow والخنزيرة، لكن بنية النون تمنع الحكم الموجب.",
        "تحتاج النون العربية إلى تحليل تاريخي أو صرفي مسمى؛ لا تُضاف من المعنى."),
    d("kaikki_aramaic:1655:en-יסמין-arc-noun-30La7GAn", "ياسمين", "LOANWORD-THIRD-PARTY-TO-BRANCH", "الياسمين|النبات",
      "حُفظت الصورة الاسمية كاملة ولم تُحوّل إلى جذر عربي.",
      "حقل الأصل يسمي مصدرًا إيرانيًا ويقارن الفارسية yâsaman؛ لا صف إرث مستعمل.",
      "اسم jasmine دخل الفرع من طرف إيراني مسمى.",
      "Borrowed from Iranian إغلاق قرض خارجي إلى الفرع."),
    d("kaikki_aramaic:1722:en-לעיסתא-arc-adj-J725lO3G", "لعس", "ROOT-TRACE", "لعس|العض|المضغ",
      "نُزعت ياء المد ولاحقة الحالة -tā؛ بقي l-ʿ-s كاملًا.",
      "ל↔ل عبر IDN-04، وע↔ع عبر SEM-03، وס↔س عبر IDN-07.",
      "chewed في الفرع يلتقي لعس العربية في العض والمضغ.",
      "استعادة اللام تمنع النواة القديمة عس وتصدر الجذر الكامل."),
    d("kaikki_aramaic:1641:en-מסאתא-arc-name-KPsfP5Z1", "ميز", "OUT-OF-SCOPE", "الميزان|البرج",
      "اختير عضو name «Libra» وفُصل عن المتجانس noun «balance, scales».",
      "العلم عُزل قبل مقارنة ميزان العربية؛ لا يرث حكم متجانسه الاسمي.",
      "اسم البرج وحدة علمية، لا شاهد جذر مستقلًا.",
      "إغلاق نطاق للعضو العلم وحده."),
    gap("kaikki_aramaic:2103:en-עכביתא-arc-noun-m~oLUKkO", "عنكبوت", "MORPHOLOGY-GAP", "العنكبوت|العناكب|النسيج",
        "نُزعت -tā؛ بقيت صورة ʿ-k-k-b-y، والمصدر يقارن العربية عنكبوت.",
        "ע↔ع عبر SEM-03، وכ↔ك عبر IDN-13، وב↔ب عبر IDN-05؛ النون والواو والتاء العربية بلا تحليل موقع جامع.",
        "المعنى مباشر بين spider والعنكبوت، لكن البنية لا تستوفي رجل الصوت.",
        "تحتاج الزيادات والضعف إلى تحليل تاريخي مسمى؛ المقارنة المعجمية وحدها لا تنشئ قانونًا."),
    d("kaikki_aramaic:841:en-עסקתא-arc-adj-zQHmZH4L", "عسق", "ROOT-TRACE", "التواء|عسر|ضيق|سوء الخلق",
      "نُزعت لاحقة الصفة والحالة -tā؛ بقي ʿ-s-q كاملًا، ولم تُستبدل القاف بالراء.",
      "ע↔ع عبر SEM-03، وס↔س عبر IDN-07، وק↔ق عبر IDN-12.",
      "difficult/troublesome/perverse يلتقي نص العربية في عسق: الالتواء وعسر الخلق وضيقه.",
      "المروحة المستقلة الآن كاملة في مصدرين قديمين، فزال SOURCE-GAP القديم."),
    gap("kaikki_aramaic:1379:en-קטילתא-arc-adj-U5dQogc5", "قتل", "LAW-GAP", "قتل|المقتول|القتل",
        "نُزعت ياء البناء ولاحقة الصفة -tā؛ بقي q-ṭ-l كما يطبعه الفرع.",
        "ק↔ق عبر IDN-12، وל↔ل عبر IDN-04؛ أما ט↔ت فلا صف نافذ، وDENT-08 خاص بظ↔ט المشروط.",
        "المعنى مباشر بين killed والمقتول، لكن رجل الصوت الوسطى غير مكتملة.",
        "تحتاج ט الآرامية ↔ ت العربية إلى صف مسمى أو تحليل مصدر؛ لا تكفي الرومنة التي تطويهما."),
    d("kaikki_aramaic:1023:en-קרישתא-arc-adj-nqGx8iem", "قرر", "NUCLEUS-ECHO", "القر|البرد|تجمد|قرر",
      "نُزعت -tā؛ لم يُدع تطابق الجذر الطويل، واختيرت النواة q-r فقط.",
      "ק↔ق عبر IDN-12، وר↔ر عبر IDN-01؛ بقية הבنية خارج حكم النواة.",
      "cold/frozen يلتقي القرّ والبرد، واستقرار السائل حين يجمد صدى حدث قر.",
      "الحكم للنواة قر وحدها ولا يرثه جذر كامل غير مصفوف."),
    d("kaikki_aramaic:1667:en-תאנתא-arc-noun-f4K80FSg", "تين", "NUCLEUS-TRACE", "التين|الثمر|الشجر",
      "نُزعت -tā؛ الأصل *tiʾin- يحفظ التاء والنون مع رجل ضعيفة بينهما.",
      "ת↔ت عبر IDN-11، وנ↔ن عبر IDN-03؛ اختلاف الهمزة/الياء يمنع ROOT-TRACE.",
      "תאנתא والتين للثمر والشجر نفسيهما من الأصل السامي المنشور.",
      "اكتملت النواة الثنائية والمعنى، وبقي الجذر الكامل دون ادعاء."),
    d("kaikki_aramaic:1458:en-תשרין_א-arc-name-~deReHtk", "تشرين", "OUT-OF-SCOPE", "تشرين|أكتوبر",
      "العضو الكامل תשרין א اسم شهر October؛ لم يُخلط بعضو November.",
      "اسم الشهر عُزل قبل تحويل رسم تشرين إلى شاهد جذر.",
      "الاسم التقويمي وحدة علمية لا مادة جذرية مستقلة في هذا الجرد.",
      "إغلاق نطاق للعضو العلم وحده."),
)


EXPECTED_IDS = tuple(item.member_id for item in DECISIONS)


def blocks(text: str) -> list[tuple[int, str]]:
    return [(match.start(), match.group()) for match in re.finditer(
        r"(?ms)^### .*?(?=^### |\Z)", text
    )]


def endcard_inventory(text: str) -> dict[str, dict[str, object]]:
    found: dict[str, dict[str, object]] = {}
    all_blocks = blocks(text)
    for position, block in all_blocks:
        if "بطاقة النهاية" not in block:
            continue
        member_match = re.search(r"`(kaikki_aramaic:[^`]+)`", block)
        if not member_match:
            continue
        member_id = member_match.group(1)
        family_match = re.search(r"`(aramaic:family:[0-9a-f]+)`", block)
        number_match = re.search(r"بطاقة النهاية (\d+)", block)
        found[member_id] = {
            "member_id": member_id,
            "family_id": family_match.group(1) if family_match else "غير مسمى في العنوان",
            "endcard": int(number_match.group(1)) if number_match else 0,
            "position": position,
        }
    for member_id, item in found.items():
        later = [
            (position, block) for position, block in all_blocks
            if position >= int(item["position"]) and member_id in block
            and re.search(r"^- الحكم \(استكشاف\):", block, flags=re.M)
        ]
        if not later:
            item["latest_verdict"] = ""
            item["latest_position"] = int(item["position"])
            continue
        position, block = later[-1]
        verdicts = re.findall(r"^- الحكم \(استكشاف\): (.+)$", block, flags=re.M)
        item["latest_verdict"] = verdicts[-1] if verdicts else ""
        item["latest_position"] = position
    return found


def load_entries() -> tuple[dict[str, dict], dict[str, list[dict]]]:
    connection = sqlite3.connect(DB)
    connection.row_factory = sqlite3.Row
    try:
        exact: dict[str, dict] = {}
        by_word: dict[str, list[dict]] = collections.defaultdict(list)
        rows = connection.execute(
            "SELECT entry_id,headword,romanization,pos,gloss,etymology,loan_hint,"
            "form_of,form_targets_json,skeleton,morphology_status FROM entries "
            "WHERE language='aramaic'"
        )
        for row in rows:
            value = dict(row)
            exact[str(row["entry_id"])] = value
            by_word[str(row["headword"])].append(value)
        return exact, dict(by_word)
    finally:
        connection.close()


def select_open(text: str, exact: dict[str, dict]) -> tuple[list[dict], dict]:
    inventory = endcard_inventory(text)
    selected: list[dict] = []
    current_open = 0
    for member_id, item in inventory.items():
        latest = str(item.get("latest_verdict") or "")
        if "OPEN-CANDIDATE" not in latest or any(token in latest for token in POSITIVE):
            continue
        current_open += 1
        entry = exact[member_id]
        word = str(entry["headword"])
        skeleton = FAN.skeleton(word, "north")
        fan = FAN.fan(word, "north")
        if not (2 <= len(skeleton) <= 4) or not fan:
            continue
        selected.append({**item, **entry, "surface_skeleton": "".join(skeleton), "fan": fan})
    selected.sort(key=lambda item: (len(str(item["surface_skeleton"])), int(item["position"])))
    ids = tuple(str(item["member_id"]) for item in selected)
    assert ids == EXPECTED_IDS, (
        "Current Aramaic short-open queue drifted:\n"
        f"expected={EXPECTED_IDS}\nactual={ids}"
    )
    return selected, {
        "unique_endcards": len(inventory),
        "current_open_endcards": current_open,
        "short_open_selected": len(selected),
    }


def check_both(text: str) -> dict:
    rows = json.loads(SWEEP.read_text(encoding="utf-8"))["both"]
    assert len(rows) == 426, f"Aramaic both size changed: {len(rows)}"
    missing = [index for index, row in enumerate(rows) if str(row["branch"]) not in text]
    tail = [
        {"index": index, "branch": str(rows[index]["branch"]),
         "represented": str(rows[index]["branch"]) in text}
        for index in range(417, 426)
    ]
    assert not missing, f"Aramaic both has unrepresented rows: {missing[:10]}"
    assert all(item["represented"] for item in tail)
    return {
        "pool_rows": len(rows),
        "represented": len(rows) - len(missing),
        "missing": len(missing),
        "physical_last_index": 425,
        "requested_terminal_position": "aramaic both[426/426]",
        "post_416_tail": tail,
    }


def folded(value: str) -> str:
    return AR.ARABIC_MARKS.sub("", value)


def excerpt(definition: str, keywords: tuple[str, ...], limit: int = 190) -> str:
    value = re.sub(r"\s+", " ", definition).strip()
    positions = [
        folded(value).find(folded(keyword)) for keyword in keywords
        if folded(value).find(folded(keyword)) >= 0
    ]
    center = min(positions) if positions else 0
    left = max(0, center - 45)
    right = min(len(value), left + limit)
    left = max(0, right - limit)
    return ("…" if left else "") + value[left:right].strip(" ،؛:") + ("…" if right < len(value) else "")


def witnesses(matches: list[dict], keywords: tuple[str, ...]) -> list[dict]:
    by_source: dict[str, list[dict]] = collections.defaultdict(list)
    for item in matches:
        source_id = AR.canonical_source_id(str(item.get("source") or ""))
        if source_id:
            by_source[source_id].append(item)
    ranked: list[tuple[int, int, int, str, dict]] = []
    for priority, source_id in enumerate(AR.SOURCE_PRIORITY):
        items = by_source.get(source_id) or []
        if not items:
            continue
        chosen = max(items, key=lambda item: (
            sum(folded(keyword) in folded(str(item.get("definition") or "")) for keyword in keywords),
            len(str(item.get("definition") or "")),
        ))
        definition = folded(str(chosen.get("definition") or ""))
        hits = sum(definition.count(folded(keyword)) for keyword in keywords)
        distinct = sum(folded(keyword) in definition for keyword in keywords)
        ranked.append((-distinct, -hits, priority, source_id, chosen))
    ranked.sort()
    return [
        {**item, "source_label": AR.SOURCE_LABELS[source_id]}
        for _, _, _, source_id, item in ranked[:2]
    ]


def render_card(serial: int, item: dict, decision: Decision,
                by_word: dict[str, list[dict]], arabic_matches: dict[str, list[dict]]) -> str:
    word = str(item["headword"])
    read = str(item["romanization"] or "").strip() or "بلا رومنة منشورة"
    gloss = re.sub(r"\s+", " ", str(item["gloss"])).strip()
    etym = re.sub(r"\s+", " ", str(item["etymology"] or "")).strip()
    homographs = by_word[word]
    homograph_text = "؛ ".join(
        f"{entry['pos']} «{str(entry['gloss'])[:62]}»"
        for entry in homographs
    )

    fan = list(item["fan"])
    ranked = FAN.rank(word, fan, "north", "aramaic")
    selected_rank = next((rank for rank, (candidate, _) in enumerate(ranked, 1)
                          if candidate == decision.candidate), None)
    selected_weight = next((weight for candidate, weight in ranked
                            if candidate == decision.candidate), None)
    membership = (
        f"المرشح داخلها في الرتبة {selected_rank} بوزن {selected_weight:.6f}"
        if selected_rank is not None and selected_weight is not None else
        "المقابل خارج سطح المروحة؛ استُعيد من صرف الفرع أو حقل الأصل المسمى"
    )
    top = "، ".join(candidate for candidate, _ in ranked[:8]) or "لا مرشح"

    root = AR.normalize_root(decision.candidate)
    matches = arabic_matches.get(root, [])
    fan_status = AR.independent_fan(matches) if matches else {
        "judgment_ready": False, "selected_sources": []
    }
    chosen_witnesses = witnesses(matches, decision.keywords)
    witness_text = "؛ ".join(
        f"قال {entry['source_label']}: «{excerpt(str(entry.get('definition') or ''), decision.keywords)}»"
        for entry in chosen_witnesses
    ) or "لا شاهد عربي عامل؛ والإغلاق لا يدعي صلة موجبة"

    if decision.verdict in POSITIVE or decision.verdict == "OPEN-CANDIDATE":
        tiers = FE.all_tiers(decision.candidate)
        if not tiers:
            normalized = decision.candidate.translate(str.maketrans("أإؤئ", "ءءءء"))
            tiers = FE.all_tiers(normalized)
        assert tiers, f"No frozen event for {decision.candidate}"
        event_line = tiers[0].line() + f"؛ عُرضت {len(tiers)} درجات واختيرت المعلنة."
    else:
        event_line = ("- الحدث المجمّد: قُرئ المقابل ولم يُستعمل بوابةً؛ "
                      "الإغلاق صرفي/نطاقي/اتجاهي لا حكم صلة موجب.")

    if decision.verdict in POSITIVE:
        assert len(chosen_witnesses) == 2, (
            f"Positive card {serial} lacks two Arabic sources for {decision.candidate}"
        )
        filter_line = "اكتملت أرجل الصوت والحدث ومعنى الفرع في المدار المكتوب؛ لا شرط رابع."
    elif decision.verdict == "OPEN-CANDIDATE":
        filter_line = f"العائق القاتل مسمى: {decision.reason}"
    else:
        filter_line = f"الإغلاق النهائي مسمى: {decision.reason}"

    family = str(item["family_id"])
    form_note = (
        f"؛ form_of={item['form_of']}؛ targets={item['form_targets_json']}"
        if int(item["form_of"]) else ""
    )
    source = etym or "لا نص اشتقاق منشورًا في العضو"
    if len(source) > 240:
        source = source[:237].rstrip() + "…"
    card_id = f"WO-C-OPEN-COMP-{serial:05d}"
    lines = [
        f"### {card_id}: `{word}` /{read}/ ↔ `{decision.candidate}`",
        "- إصدار البروتوكول: RECOVERY-v2 (2026-08-16) + ROUND7-COMPLETION (2026-08-17).",
        (f"- إحالة الجرد المفتوح: بطاقة النهاية {item['endcard']}؛ `{family}`؛ "
         f"العضو `{decision.member_id}`؛ كانت أحدث حالته `OPEN-CANDIDATE` قبل بطاقة الإتمام هذه."),
        f"- الكلمة في الفرع: آرامية `{word}` /{read}/، {item['pos']}، «{gloss}».",
        f"- أقدم صورة مستعادة: {source}{form_note}.",
        f"- الخطوة صفر (التعرية بصرف الفرع): {decision.zero}",
        (f"- المروحة المفحوصة في الذاكرة: الهيكل السطحي القصير `{item['surface_skeleton']}`؛ "
         f"قُرئت {len(ranked)} صورة مرتبة كلها ولم تُنسخ؛ أوائلها: {top}؛ {membership}."),
        (f"- مسح المعاني العربية: قُرئت {len(matches)} نتيجة للجذر `{root}` "
         f"بما يكافئ `--max-chars 0`؛ المروحة المستقلة "
         f"{'مكتملة' if fan_status['judgment_ready'] else 'غير مكتملة'}؛ {witness_text}."),
        f"- المقابل من اللسان: `{decision.candidate}`.",
        f"- مسار الصوت: {decision.sound}",
        event_line,
        f"- المعنى من قاموس الفرع: «{gloss}» [الجرد المثبت؛ العضو المختار بعد قراءة جميع المتجانسات].",
        f"- جميع المتجانسات بنص الرسم ({len(homographs)}): {homograph_text}؛ الحكم للعضو المسمى وحده.",
        f"- المدار المكتوب باليد: {decision.orbit}",
        f"- المصفاة: {filter_line}",
        "- فصل المتجانسات والاقتراض: قُرئ الأصل والقرض؛ لا وراثة بين الأعضاء ولا تحويل للقرض إلى إرث.",
        f"- مؤشر اليتم: عضو بطاقة نهاية مفتوحة؛ family=`{family}`؛ completion-rank={serial}/41.",
        f"- إشعاع الأسرة في الفرع: المتجانسات المقروءة={len(homographs)}؛ المختار=1.",
        "- إشعاع الأسرة في العربية: [قُرئت المروحة كاملة ولم تُنسخ؛ الشاهدان العاملان فقط أعلاه عند وجود حكم موجب].",
        "- جسور الاسترداد المفحوصة: الصرف؛ المروحة؛ الحدث؛ القاموس؛ العربية؛ الأصل؛ القرض؛ المتجانس؛ الاتجاه.",
        f"- عائق/تعليل الإغلاق: {decision.reason}",
        f"- حالة الإغلاق: {decision.state}.",
        f"- الحكم (استكشاف): {decision.verdict}.",
        "- ملاحظات: عدستا الاسترداد والتشكيك قرأتا المرشحات ومنعتا إسقاط صامت أو وراثة حكم أو شرطًا رابعًا.",
    ]
    card = "\n".join(lines) + "\n"
    size = len(card.encode("utf-8"))
    assert size <= MAX_CARD_BYTES, f"Card {card_id} is {size} bytes"
    return card


def render() -> tuple[str, dict]:
    text = READING.read_text(encoding="utf-8")
    if MARKER in text:
        raise SystemExit("Round-seven marker already exists; append refused.")
    both = check_both(text)
    exact, by_word = load_entries()
    selected, open_diagnostics = select_open(text, exact)
    roots = {
        AR.normalize_root(decision.candidate)
        for decision in DECISIONS
        if decision.verdict in POSITIVE or decision.verdict == "OPEN-CANDIDATE"
    }
    arabic_matches = AR.matches_for_roots(AR.DEFAULT_RESOURCES, roots, None)
    cards = [
        render_card(serial, item, decision, by_word, arabic_matches)
        for serial, (item, decision) in enumerate(zip(selected, DECISIONS), 1)
    ]
    body = [
        f"<!-- {MARKER}:START -->",
        "",
        "## الجولة السابعة: إغلاق حوض الآرامية both وإتمام المفتوح القصير (2026-08-17)",
        "",
        "### الدفعة الأولى: إغلاق حوض الآرامية both",
        "",
        ("حُمّل ملف الآرامية مرة واحدة في الذاكرة. وبعد البطاقة المكتوبة للموضع "
         "`both[416]` فُحص الذيل الفيزيائي `both[417]..both[425]`؛ كانت رسومه "
         "كلها ممثلة في الملف، فلم تُكتب بطاقات مكررة."),
        "",
        "- حدث الإغلاق المسمى: `ARAMAIC-BOTH-CLOSED 426/426`.",
        "- الصفوف الممثلة: 426 من 426؛ المتبقي غير المكرر: 0.",
        "- آخر فهرس فيزيائي: `both[425]`؛ موضع نهاية الحوض بحسب عد المستخدم: `aramaic both[426/426]`.",
        "",
        "### الدفعة الثانية: بطاقات إتمام «غير صادر» قصيرة الهيكل",
        "",
        ("اختيرت الحالات الحية الأحدث فقط، بعد نقض البطاقات التاريخية المنسوخة؛ "
         "العدد 41 ضمن نافذة 40–60، وكل بطاقة تنتهي بحكم أو إغلاق أو فجوة مسماة."),
        "",
    ]
    for serial, card in enumerate(cards, 1):
        body.append(card.rstrip())
        body.append("")
        if serial % 5 == 0:
            body.append(f"<!-- LANE-C-OPEN-COMP-R7-CHUNK-{serial // 5:03d}:END -->")
            body.append("")
    body.append(f"<!-- {MARKER}:END -->")
    appendix = "\n".join(body).rstrip() + "\n"

    verdicts = collections.Counter(item.verdict for item in DECISIONS)
    states = collections.Counter(item.state for item in DECISIONS)
    diagnostics = {
        "both": both,
        "open_inventory": open_diagnostics,
        "cards": len(cards),
        "first_card": "WO-C-OPEN-COMP-00001",
        "last_card": "WO-C-OPEN-COMP-00041",
        "verdicts": dict(sorted(verdicts.items())),
        "states": dict(sorted(states.items())),
        "appendix_bytes": len(appendix.encode("utf-8")),
        "max_card_bytes": max(len(card.encode("utf-8")) for card in cards),
    }
    return appendix, diagnostics


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--show", type=int, choices=range(1, 42))
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
        current = READING.read_text(encoding="utf-8")
        if MARKER in current:
            raise SystemExit("Round-seven marker appeared during render; append refused.")
        with READING.open("a", encoding="utf-8", newline="\n") as handle:
            if not current.endswith("\n"):
                handle.write("\n")
            handle.write("\n" + appendix)
        print(f"APPENDED: {READING.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
