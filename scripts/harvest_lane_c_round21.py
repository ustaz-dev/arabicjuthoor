#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Lane C round 21: two fresh Hebrew batches from the doubled ``both`` pool.

The reading ledger is loaded exactly once.  Rows are stably ordered by
descending overlap, every branch already present in that in-memory ledger is
skipped, and each newly selected branch is immediately added to the same
memory before selection continues.  The script appends research cards and the
lane report only; it never stages, commits, publishes, or ships.
"""

from __future__ import annotations

import argparse
import collections
import json
import re
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import build_kaikki_index as LEX  # noqa: E402
import fan_any_script as FAN  # noqa: E402
import frozen_event as FE  # noqa: E402
import harvest_hebrew_aramaic_round3 as R3  # noqa: E402
import search_arabic_root_senses as AR  # noqa: E402


HEBREW = ROOT / "04-cross-linguistic" / "readings" / "hebrew.md"
SWEEP = ROOT / "04-cross-linguistic" / "exploration" / "phonetic-sweep-hebrew.json"
REPORT = ROOT / "_inbox" / "lane-reports" / "2026-08-16-C.md"
MARKER = "LANE-C-HEBREW-ROUND21-2026-08-18"
REPORT_MARKER = "LANE-C-REPORT-ROUND21-2026-08-18"
BATCH_SIZE = 50
CARD_COUNT = 100
POOL_EXPECTED = 1851
MODEL = "WO-B-PROBE-001"
MAX_CARD_BYTES = 5 * 1024

ROOT_TRACE = "ROOT-TRACE"
ROOT_ECHO = "ROOT-ECHO"
NUCLEUS_ECHO = "NUCLEUS-ECHO"
OPEN = "OPEN-CANDIDATE"
LOAN = "LOANWORD"
SEMITIC_LOAN = "SEMITIC-SOURCE-TRANSMISSION"
FORM = "FORM-OF-ISOLATED"


@dataclass(frozen=True)
class Decision:
    candidate: str
    verdict: str
    state: str
    keywords: tuple[str, ...]
    orbit: str
    hebrew_root: str | None = None
    nucleus: str | None = None


def d(candidate: str, verdict: str, state: str, keywords: str, orbit: str,
      hebrew_root: str | None = None, nucleus: str | None = None) -> Decision:
    return Decision(
        candidate=candidate,
        verdict=verdict,
        state=state,
        keywords=tuple(value.strip() for value in keywords.split("|") if value.strip()),
        orbit=orbit,
        hebrew_root=hebrew_root,
        nucleus=nucleus,
    )


# One handwritten ruling per selected row.  The order is asserted against the
# doubled sweep below.  Retrieval overlap never supplies a semantic verdict.
DECISIONS: tuple[Decision, ...] = (
    d("زيت", LOAN, "LOANWORD-THIRD-PARTY-TO-BRANCH", "زيت|الزيت", "zeta اسم حرف يوناني، لا الزيت العربي؛ عُزل القرض قبل أن يرث معنى المرشح.", "זית"),
    d("عدس", ROOT_TRACE, "READY", "عدس|العدسة|عدسة", "العدسة في الطرفين جسم بصري، والاسم العربي مشتق من صورة العدسة؛ اكتمل مدار الشيء نفسه.", "עדש"),
    d("ضلع", ROOT_TRACE, "READY", "ضلع|الأضلاع|الضلع", "الضلع في الفرع والعربية عضو الجسد نفسه، وحس قطعة اللحم تابع له ولا يعمم الحكم.", "צלע"),
    d("عتق", SEMITIC_LOAN, "SEMITIC-SOURCE-TRANSMISSION", "عتيق|قديم|العتق", "العتيق والقديم في الطرفين وصف للقدم، لكن قاموس الفرع يرد العضو إلى الآرامية؛ أُغلق النقل السامي دون دعوى إرث.", "עתק"),
    d("قفز", OPEN, "LAW-GAP", "قفز|وثب|القفز", "القفز والوثب مطابقان دلالة، لكن צ↔ز غير موقع في الشبكة النافذة؛ لم يصدر حكم نواة بديل.", "קפצ"),
    d("بلي", NUCLEUS_ECHO, "READY", "بلي|البلى|خلق|قديم", "الجذر الكامل בלה↔بلي يبقى ضعيف النهاية بلا صف ه↔ي؛ بعد تثبيت ذلك نُزل إلى بل فأصدر ECHO البلى والاهتراء.", "בלה", "بل"),
    d("جدي", ROOT_TRACE, "READY", "الجدي|ولد المعز|المعز", "الجدي هو صغير المعز نفسه؛ التأنيث في العضو العبري لا يغير الجذر أو النوع الحيواني.", "גדי"),
    d("نبو", OPEN, "SEMANTIC-GAP", "نبا|نبو|النبوة", "الحس المختار idiom أو saying لا يطابق النبو أو النبوة؛ وحس الناب المتجانس لم يُورث البطاقة.", "ניב"),
    d("كوش", OPEN, "NAME-ROOT-OPEN", "كوش|الحبشة|الكوشيين", "الاسم الإثني ظاهر، لكن لم يثبت في المروحة العربية شاهدان قديمان ولا اتجاه انتقال؛ بقي اسمًا مفتوحًا.", "כוש"),
    d("دين", ROOT_TRACE, "READY", "دين|الحكم|القضاء|القانون", "الحكم والقانون والتدبير القضائي مدار واحد في الجذرين.", "דין"),
    d("جيف", OPEN, "LAW-GAP", "الجيفة|الميتة|جيف", "الجثة والجيفة متطابقتان دلالة، لكن ו↔ي في גוף↔جيف بلا صف موقع؛ لم تُسقط الرجل الوسطى.", "גוף"),
    d("لير", LOAN, "LOANWORD-THIRD-PARTY-TO-BRANCH", "ليرة|الليرة", "اسم العملة lira قرض دولي؛ الهوية الاسمية لا تثبت إرثًا ساميًا.", "ליר"),
    d("جيم", LOAN, "LOANWORD-THIRD-PARTY-TO-BRANCH", "الجيم|حرف الجيم", "gamma اسم حرف يوناني مقترض، ولا يصير جيمًا عربيًا لمجرد اشتراكهما في باب الحروف.", "גמא"),
    d("كول", LOAN, "LOANWORD-THIRD-PARTY-TO-BRANCH", "كولا|كول", "Coca-Cola اسم تجاري دولي مقترض؛ عُزل النقل الثالثي المصدر.", "קול"),
    d("ردي", OPEN, "SEMANTIC-GAP", "ردى|أردى|الهلاك", "الدوس والإخضاع في الفرع لا يساويان الردى أو الهلاك في العربية، مع بقاء النهاية الضعيفة غير محسومة.", "רדה"),
    d("زعزع", ROOT_TRACE, "READY", "زعزع|اضطرب|حرك", "الزعزعة والاهتزاز العنيف وعدم الاستقرار فعل واحد في الطرفين.", "זעזע"),
    d("حشيش", OPEN, "DIRECTIONAL-TRANSMISSION", "الحشيش|نبات|يابس", "الحشيش اسم المادة النباتية نفسه، لكن العضو لا يسمي المانح أو طريق الأخذ؛ بقي اتجاه النقل مفتوحًا.", "חשיש"),
    d("زعق", ROOT_TRACE, "READY", "زعق|صاح|الصياح", "الزعق والصياح في الطرفين حدث صوتي واحد.", "זעק"),
    d("عصب", OPEN, "SEMANTIC-GAP", "عصب|العصب|العصابة", "الحزن في العضو العبري لا يساوي العصب أو الشد في العربية؛ لم يُستبدل به الغضب لمجرد الجوار.", "עצב"),
    d("عقد", ROOT_TRACE, "READY", "عقد|ربط|العقد", "ربط الأطراف وجمعها بعقدة هو العقد نفسه في العربية.", "עקד"),
    d("وعظ", OPEN, "LAW-GAP", "وعظ|نصح|الموعظة", "النصح والموعظة متقاربان مباشرة، لكن DENT-08 لا يعمل بلا إعادة بناء *ṯ̣ منصوصة واختبار نفي.", "יעצ"),
    d("وعظ", OPEN, "LAW-GAP", "وعظ|نصح|الموعظة", "النصيحة في الاسم العبري تقابل الوعظ معنى، وبقي شرط DENT-08 نفسه غير مستوفى.", "יעצ"),
    d("غطي", OPEN, "LAW-GAP", "غطى|التغطية|ستر", "التغطية واللف مباشران، لكن النهاية ה↔ي غير موقعة في الجذر الكامل؛ لم تُختزل البطاقة إلى حرفين قسرًا.", "עטה"),
    d("ثني", ROOT_TRACE, "READY", "الثاني|اثنان|ثنى", "second مشتق من العدد اثنين في الطرفين؛ وحدة الزمن حس مشتق لا جذر جديد.", "שני"),
    d("صور", ROOT_TRACE, "READY", "صورة|صور|هيئة", "الصورة والهيئة والشكل مدار واحد في الجذر الكامل.", "צור"),
    d("ثني", ROOT_TRACE, "READY", "الثاني|اثنان|ثنى", "التهجئة البديلة لثانية الزمن تحفظ جذر العدد نفسه ولا تنشئ شاهدًا مستقلًا.", "שני"),
    d("معي", ROOT_TRACE, "READY", "المعى|الأمعاء|معي", "المعى والأمعاء عضو الهضم نفسه في الطرفين.", "מעי"),
    d("صور", ROOT_TRACE, "READY", "صورة|تصوير|رسم", "الرسم والتصوير إنشاء صورة؛ العضو مشتق مباشرة من الجذر الكامل صور.", "צור"),
    d("زيف", ROOT_TRACE, "READY", "زيف|مزيف|التزييف", "التزييف وصنع المزور أو المقلد فعل واحد.", "זיפ"),
    d("قوف", LOAN, "LOANWORD-THIRD-PARTY-TO-BRANCH", "قاف|قوف", "kappa اسم حرف يوناني مقترض؛ لا صلة عربية صادرة من تشابه اسم الحرف.", "קפא"),
    d("شيع", OPEN, "DIRECTIONAL-TRANSMISSION", "الشيعة|شيعي|شيع", "اسم Shia مطابق للمصطلح العربي، لكن العضو لا يسمي المانح أو طبقة الأخذ؛ بقي الاتجاه مفتوحًا.", "שיע"),
    d("سور", OPEN, "DIRECTIONAL-TRANSMISSION", "سورية|سوري|الشام", "النسبة إلى سورية ظاهرة، لكن المانح والطبقة التاريخية غير محسومين في العضو؛ بقي الاتجاه مفتوحًا.", "סור"),
    d("سبي", ROOT_TRACE, "READY", "سبي|الأسير|سبى", "الأسير المسبِيّ والحبس الناتج من السبي مدار واحد.", "שבי"),
    d("شيم", OPEN, "SEMANTIC-GAP", "شيم|الشيمة|الطبع", "الخفي والمستور لا يطابق الشيم أو الشيمة؛ shared مجرد استرجاع لا حكم.", "סמו"),
    d("بني", ROOT_TRACE, "READY", "بنى|البناء|بني", "البناء والإنشاء من الجذر بني في الطرفين.", "בני"),
    d("حكي", ROOT_TRACE, "READY", "حكى|الحكاية|المحاكاة|تقليد", "المحاكاة والتقليد إعادة صورة الفعل أو الصوت، وهو حس حكى العامل هنا.", "חקי"),
    d("زيف", ROOT_TRACE, "READY", "زيف|التزييف|مزور", "اسم التزوير والتزييف مشتق من الفعل نفسه في البطاقة السابقة مع بقاء العضو مستقلًا.", "זיפ"),
    d("سوني", LOAN, "LOANWORD-THIRD-PARTY-TO-BRANCH", "سوني|شركة", "Sony علم شركة يابانية منقول دوليًا؛ لا جذر سامي.", "סוני"),
    d("مصص", ROOT_TRACE, "READY", "مص|مصص|امتص", "المص وامتصاص السائل حدث واحد؛ الحس الجنسي المتجانس لا يوسع الحكم.", "מצצ"),
    d("عظم", ROOT_TRACE, "READY", "عظيم|العظمة|عظم", "العظمة والكبر والقوة في الفرع من الجذر السامي نفسه؛ مرساة *ʕaṯ̣m- تحقق شرط DENT-08.", "עצמ"),
    d("ودع", OPEN, "SEMANTIC-GAP", "ودع|أودع|الوديعة", "الإعلام والتعريف في الفرع لا يساويان الإيداع أو الترك في العربية؛ التحليل الآلي أخفى جذر ידע.", "ידע"),
    d("ضبع", ROOT_TRACE, "READY", "الضبع|ضبع|حيوان", "الضبع في الطرفين الحيوان نفسه؛ أسطورة التحول في الشرح لا تغير اسم النوع.", "צבע"),
    d("نور", ROOT_ECHO, "READY", "نور|الضوء|أنار", "المصباح الكهربائي حامل للنور ومصدره؛ الحكم ECHO للانتقال من الضوء إلى آلته لا لكل حس נורה.", "נור"),
    d("فرو", SEMITIC_LOAN, "SEMITIC-SOURCE-TRANSMISSION", "الفروة|فرو|الجلد", "الفرو مطابق اسميًا، وقاموس الفرع يسمي العربية مانحًا للصورة العبرية؛ أُغلق النقل دون دعوى إرث.", "פרו"),
    d("مخا", OPEN, "DIRECTIONAL-TRANSMISSION", "مخا|اليمن|ميناء", "Mocha هو اسم مخا اليمنية نفسه، لكن العضو لا يسمي المانح أو طريق النقل؛ بقي الاتجاه مفتوحًا.", "מחא"),
    d("صوص", LOAN, "LOANWORD-THIRD-PARTY-TO-BRANCH", "صوص|فرخ|كتكوت", "الحس العبري امرأة جذابة من slang أجنبي، لا الصوص الحيواني العربي؛ عُزل القرض والمتجانس.", "צוצ"),
    d("زعزع", ROOT_TRACE, "READY", "زعزع|اضطراب|خلخل", "وسم الجذر العبري للصدم والاضطراب يطابق فعل زعزع الكامل.", "זעזע"),
    d("زعزع", ROOT_TRACE, "READY", "زعزع|اضطراب|فزع", "الصدمة والاضطراب والهيجان نتائج مباشرة للزعزعة في اسم المصدر.", "זעזע"),
    d("تسع", ROOT_TRACE, "READY", "تسعة|تسع|التاسع", "العدد تسعة واحد في الطرفين؛ هاء التأنيث خارج الجذر.", "תשע"),
    d("بضع", ROOT_ECHO, "READY", "بضع|قطع|شق", "الجرح قطع في الجسد، والبضع القطع؛ الحكم ECHO لمدار القطع المحدث للجرح لا لمساواة كل جرح ببضع.", "פצע"),
    d("تسع", ROOT_TRACE, "READY", "التاسع|تسعة|تسع", "رتبة التاسع مشتقة من العدد تسعة نفسه.", "תשע"),
    d("سعف", ROOT_ECHO, "READY", "السعف|غصن|فرع", "الفقرة أو البند فرع من نص أكبر، والسعف فرع النخل؛ الحكم ECHO لاستعارة الفرع لا تطابق الحس القانوني حرفيًا.", "סעפ"),
    d("ضحك", ROOT_TRACE, "READY", "ضحك|الضحك|قهقه", "الضحك في الطرفين حدث الصوت والسرور نفسه.", "צחק"),
    d("صعد", ROOT_ECHO, "READY", "صعد|الصعود|خطا", "الخطوة حركة تقدم، والصعود تقدم إلى علو؛ الحكم ECHO للحركة المتدرجة لا مساواة كل خطوة بصعود.", "צעד"),
    d("سعد", SEMITIC_LOAN, "SEMITIC-SOURCE-TRANSMISSION", "سعود|السعودية|سعد", "اسم السعودية من آل سعود منقول من العربية؛ الاتجاه مسمى ولا دعوى إرث للعلم.", "סעד"),
    d("صنع", SEMITIC_LOAN, "SEMITIC-SOURCE-TRANSMISSION", "صنعاء|اليمن|صنع", "צנעא هو اسم صنعاء العربي المنقول؛ الحكم لطريق الاسم وحده.", "צנע"),
    d("وعظ", OPEN, "LAW-GAP", "وعظ|نصح|الموعظة", "فعل counsel يعيد حس النصيحة، وبقي شرط DENT-08 بلا إعادة بناء منشورة.", "יעצ"),
    d("عظم", ROOT_TRACE, "READY", "العظمة|عظيم|القوة", "القوة والشدة والعظمة امتداد مباشر لجذر عظم السامي الموثق.", "עצמ"),
    d("وعد", ROOT_ECHO, "READY", "وعد|موعد|ميعاد", "الموعد والتعيين في الفرع يلتقيان الوعد والميعاد؛ الحكم ECHO لأن designation أوسع من الوعد.", "יעד"),
    d("سود", OPEN, "NAME-ROOT-OPEN", "السيد|الرب|سود", "שדי لقب إلهي مخصوص، ولا يثبت سود العربية اسمه أو اشتقاقه؛ بقي الاسم مفتوحًا.", "שדי"),
    d("ويك", LOAN, "LOANWORD-THIRD-PARTY-TO-BRANCH", "ويكي|موسوعة", "wiki قرض دولي حديث؛ لا جذر سامي.", "ויק"),
    d("رضو", OPEN, "SEMANTIC-GAP", "رضي|الرضا|ركض", "الجري في רוץ لا يطابق الرضا، ولم تُستبدل به ركض خارج المروحة بلا مسار صوت مكتوب.", "רוצ"),
    d("عشش", OPEN, "SEMANTIC-GAP", "عش|عشش|العش", "الفعل العام do/make في עשה لا يساوي بناء العش أو التعشيش؛ العموم الإنجليزي لا يسد المدار.", "עשה"),
    d("توج", SEMITIC_LOAN, "SEMITIC-SOURCE-TRANSMISSION", "تاج|توج|إكليل", "قاموس الفرع يرد tag «التاج الحرفي» إلى آرامية תַגָּא؛ أُغلق النقل السامي ولم يُحوّل تاج العربية إلى إرث.", "תג"),
    d("يوني", LOAN, "LOANWORD-THIRD-PARTY-TO-BRANCH", "يونيو|حزيران", "June اسم شهر أوروبي منقول؛ عُزل عن مواد وني ويون العربية.", "יוני"),
    d("كون", OPEN, "SEMANTIC-GAP", "كون|كان|الكينونة", "القصد والنية في כוונה لا يساويان الكون أو الوجود؛ الاشتراك الصوتي بلا مدار.", "כונ"),
    d("كبب", OPEN, "SEMANTIC-GAP", "كب|كبب|انكب", "المعدة العضو الهضمي لا تسميه مادة كبب العربية؛ food سياق وظيفة لا معنى الجذر.", "קיב"),
    d("جسس", OPEN, "SEMANTIC-GAP", "جس|جسس|الجس", "أخت الزوج أو الزوجة لا تلتقي الجس أو التحسس؛ female تغطية عامة لا مدار.", "גיס"),
    d("بهر", ROOT_TRACE, "READY", "بهر|باهر|الضوء|أضاء", "الباهر الساطع والواضح يطابق bright وclear في الحس المختار.", "בהר"),
    d("قلي", ROOT_TRACE, "READY", "قلى|القلي|شوى", "التحميص والتسخين الجاف يلتقيان القلي في هذا الحس، مع فصل القلى بمعنى البغض.", "קלי"),
    d("رضي", ROOT_ECHO, "READY", "رضي|الرضا|مرضي", "المرغوب والمقبول ما يُرضى عنه؛ الحكم ECHO من الرضا إلى صفة desired لا مساواة صرفية تامة.", "רצי"),
    d("ثني", SEMITIC_LOAN, "SEMITIC-SOURCE-TRANSMISSION", "ثنى|التثنية|كرر", "قاموس الفرع يرد لقب Tanna إلى الآرامية תנא؛ أُغلق النقل السامي مع بقاء مقابلة ثني العربية في موضع الشاهد لا المانح.", "תנא"),
    d("صك", LOAN, "LOANWORD-THIRD-PARTY-TO-BRANCH", "صك|شيك|سند", "check المالي في العبرية قرض إنجليزي؛ مطابقته بالصك العربي معنى لا تحوله إلى إرث.", "צק"),
    d("وري", OPEN, "SEMANTIC-GAP", "ورى|أورى|أطلق", "رامية السلاح من ירה لا يثبتها وري العربية؛ إشعال النار أو الستر حسان آخران.", "ירי"),
    d("ساح", OPEN, "SEMANTIC-GAP", "ساح|سبح|الماء", "السباحة حركة في الماء، وساح العربية جرى أو ذهب في الأرض؛ الوسط المشترك أعم من الفعل.", "שחי"),
    d("كوس", OPEN, "MORPHOLOGY-GAP", "كوس|كأس", "כש־ أداة مركبة بمعنى when/as وليست جذرًا معجميًا؛ أُغلق حد الصرف قبل النواة.", "כש"),
    d("قرأ", ROOT_TRACE, "READY", "قرأ|القراءة|دعا", "القراءة والنداء في קרוא من الجذر קרא، وهو قرأ العربي في حس التلاوة والدعاء.", "קרא"),
    d("سوق", ROOT_TRACE, "READY", "سوق|التسويق|باع", "التسويق وإيصال السلعة إلى السوق مشتقان من الجذر نفسه في الطرفين.", "שוק"),
    d("مضي", FORM, "FORM-OF-ISOLATED", "مضى|المضي", "القاموس يصرح بأنها تهجئة ناقصة وصورة صرفية من מצווה؛ لم تُنشأ صلة مستقلة مع مضي.", "מצו"),
    d("كسو", NUCLEUS_ECHO, "READY", "كسا|كسوة|غطى", "الجذر الكامل כסה↔كسو يبقى ضعيف النهاية بلا صف ه↔و؛ بعد ذلك فقط نزلت القراءة إلى كس، فظهر مدار الستر والكسوة ECHO.", "כסה", "كس"),
    d("صيد", ROOT_TRACE, "READY", "صيد|الصائد|الصياد", "الصياد وصيد الحيوان من الجذر نفسه؛ الياء صامت الجذر في المقارنة.", "ציד"),
    d("حقق", ROOT_TRACE, "READY", "حق|الحق|القانون|حقق", "القانوني والمأذون بالحق يلتقيان الحق والحكم الثابت في العربية.", "חקק"),
    d("قسو", NUCLEUS_ECHO, "READY", "قسا|القسوة|صلب", "الجذر الكامل קשה↔قسو يبقى ضعيف النهاية بلا صف ه↔و؛ بعد ذلك فقط نُزل إلى قس فأصدر ECHO الصلابة والقسوة.", "קשה", "قس"),
    d("كهن", ROOT_TRACE, "READY", "كاهن|الكهانة|كهن", "خدمة الكاهن والكهنوت من الجذر كهن نفسه؛ حس شغل المنصب الأعم لا يورث الحكم وحده.", "כהנ"),
    d("بلو", OPEN, "SEMANTIC-GAP", "بلا|ابتلى|بلو", "قضاء الوقت والتسكع في الاستعمال الحديث لا يساوي البلاء أو الاختبار؛ الصلة التاريخية المحتملة لا تغلق الحس.", "בלי"),
    d("جبي", OPEN, "SEMANTIC-GAP", "جبى|جبي|جمع", "العلو والطول في גבוה لا يطابق الجباية أو الجمع؛ large تغطية وصفية عامة.", "גבה"),
    d("كذا", OPEN, "MORPHOLOGY-GAP", "كذا|مثل هذا", "כזה مركب من כ־ «مثل» وזה «هذا»، ويقابل كذا تركيبيًا؛ لكنه ليس جذرًا كاملًا ولا نواة معجمية مستقلة.", "כזה"),
    d("فني", ROOT_ECHO, "READY", "فني|الفناء|زال", "الإخلاء يزيل شاغل المكان، والفناء زوال الشيء؛ الحكم ECHO لمدار الإزالة لا تطابق الحدثين حرفيًا.", "פני"),
    d("قني", ROOT_TRACE, "READY", "قنى|اقتنى|القنية|ملك", "الاقتناء والشراء وتحصيل الملك فعل واحد في الجذر الضعيف قني.", "קני"),
    d("حلو", FORM, "FORM-OF-ISOLATED", "حلوى|حلو|الحلاوة", "العضو تهجئة ناقصة من חלווה؛ حُفظت إحالة الصورة ولم تُحسب شاهد نقل جديدًا.", "חלו"),
    d("فصح", NUCLEUS_ECHO, "READY", "فصح|الفصاحة|تكلم", "الجذر الكامل פצה↔فصح لا يكتمل بسبب ה↔ح؛ بعده فقط يردد لب פצ↔فص فتح الفم للكلام والفصاحة، وهو الاحتمال الذي يسميه قاموس الفرع.", "פצה", "فص"),
    d("جاز", LOAN, "LOANWORD-THIRD-PARTY-TO-BRANCH", "جاز|موسيقى", "jazz قرض إنجليزي حديث؛ عُزل عن جاز العربية.", "גז"),
    d("كسا", NUCLEUS_ECHO, "READY", "كسا|كسوة|ستر", "الجذر الكامل כסה↔كسا ضعيف النهاية بلا صف ه↔ا مستقل؛ ثم نزلت القراءة إلى كس فأثبتت ECHO الستر والكسوة.", "כסה", "كس"),
    d("ملأ", ROOT_TRACE, "READY", "ملأ|مملوء|امتلأ", "الامتلاء وكون الشيء مملوءًا حدث واحد في الجذر מלא↔ملأ.", "מלא"),
    d("فرو", FORM, "FORM-OF-ISOLATED", "فرو|الفروة", "العضو excessive spelling من פַּרְוָה؛ عُزلت الصورة ولم ترث حكم اللمة أو اتجاهها.", "פרו"),
    d("بكي", ROOT_TRACE, "READY", "بكى|البكاء|حزن", "الرثاء والبكاء على الميت من الجذر بكي نفسه.", "בכי"),
    d("كبا", NUCLEUS_ECHO, "READY", "كبا|خمد|النار", "الجذر الكامل כבה↔كبا ضعيف النهاية بلا صف ه↔ا؛ بعد فحصه نزلت القراءة إلى كب فأصدرت ECHO خمود النار.", "כבה", "كب"),
    d("كبا", NUCLEUS_ECHO, "READY", "كبا|خمد|انطفأ", "الصيغة المبنية للمجهول تحفظ انطفاء النار؛ الكامل بقي ضعيف النهاية، ثم أصدر لب كب ECHO وحده.", "כבה", "كب"),
    d("يود", OPEN, "SOURCE-GAP", "الياء|يود|حرف", "اسم yod العبري واسم الياء العربي يشيران إلى الحرف التاريخي نفسه، لكن صورة يود العربية لم تثبت بشاهدين عاملين.", "יוד"),
    d("سنو", LOAN, "LOANWORD-THIRD-PARTY-TO-BRANCH", "سيوان|شهر|السنة", "Sivan اسم شهر منقول من طبقة أكادية/بابلية؛ year تغطية تقويمية لا جذر سنو عربي.", "סונ"),
)


assert len(DECISIONS) == CARD_COUNT


def load_pool() -> list[dict]:
    payload = json.loads(SWEEP.read_text(encoding="utf-8"))
    rows = payload["both"]
    assert len(rows) == POOL_EXPECTED, f"Hebrew both pool drifted: {len(rows)}"
    return rows


def select_rows() -> tuple[str, list[tuple[int, dict]], int, int]:
    """Read Hebrew once, then perform stable descending-overlap de-duplication."""
    original_memory = HEBREW.read_text(encoding="utf-8")
    if MARKER in original_memory:
        raise SystemExit("Round-21 Hebrew marker already exists; append refused.")
    memory = original_memory
    ordered = sorted(
        enumerate(load_pool()),
        key=lambda item: (-int(item[1].get("overlap", 0)), item[0]),
    )
    fresh: list[tuple[int, dict]] = []
    skipped = 0
    for index, row in ordered:
        branch = str(row["branch"])
        if branch in memory:
            skipped += 1
            continue
        fresh.append((index, row))
        memory += "\n" + branch
    chosen = fresh[:CARD_COUNT]
    assert len(chosen) == CARD_COUNT
    expected = (39, 865, 915, 1477)
    actual = (chosen[0][0], chosen[49][0], chosen[50][0], chosen[-1][0])
    assert actual == expected, f"Fresh Hebrew window drifted: expected={expected}, actual={actual}"
    return original_memory, chosen, len(fresh), skipped


def english_tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z]{3,}", text.casefold()))


def choose_entry(row: dict) -> tuple[dict, list[dict], str]:
    hits, how = LEX.look("hebrew", str(row["branch"]))
    if not hits:
        pseudo = {
            "word": row["branch"],
            "read": str(row["say"]).split("  (")[0],
            "en": row.get("gloss") or "",
            "etym": "",
        }
        return pseudo, [pseudo], "صف المسح؛ فجوة فهرس قاموس الفرع مسماة"
    wanted = english_tokens(str(row.get("gloss") or ""))
    wanted.update(english_tokens(" ".join(row.get("shared") or [])))
    chosen = max(
        hits,
        key=lambda hit: (
            len(wanted & english_tokens(str(hit.get("en") or ""))),
            -hits.index(hit),
        ),
    )
    return chosen, hits, how


def source_letters(value: str) -> list[str]:
    finals = str.maketrans("ךםןףץ", "כמנפצ")
    return [ch.translate(finals) for ch in value if "א" <= ch <= "ת"]


def arabic_letters(value: str) -> list[str]:
    return [
        {"أ": "ء", "إ": "ء", "ؤ": "ء", "ئ": "ء"}.get(ch, ch)
        for ch in value if "ء" <= ch <= "ي"
    ]


def sound_path(row: dict, decision: Decision) -> str:
    source = source_letters(decision.hebrew_root or str(row["skeleton"]))
    target = arabic_letters(decision.candidate)
    if len(source) != len(target):
        return (
            f"فُحص صف الجذر الكامل {''.join(source)}↔{decision.candidate}؛ "
            "تعذر الاصطفاف الكامل، والفارق البنيوي محفوظ في حالة الإغلاق"
        )
    parts: list[str] = []
    for left, right in zip(source, target):
        row_id = R3.PAIR_ROWS.get((left, right))
        parts.append(f"{left}↔{right} عبر {row_id}" if row_id else f"{left}↔{right} بلا صف مسمى")
    return "، و".join(parts)


def root_first_note(row: dict, decision: Decision) -> str:
    source = decision.hebrew_root or str(row["skeleton"])
    if decision.verdict == ROOT_TRACE:
        outcome = "اكتمل الجذر الكامل دلالةً وصوتًا في الحس المكتوب؛ لم يلزم إصدار حكم نواة مستقل"
    elif decision.verdict == ROOT_ECHO:
        outcome = "صدر ECHO على الجذر الكامل للمدار المقيد في البطاقة؛ لم يُعمم على بقية الحواس"
    elif decision.verdict == NUCLEUS_ECHO:
        outcome = f"لم يكتمل الجذر الكامل؛ بعد تثبيت سبب ذلك فقط نُزل إلى النواة `{decision.nucleus}` فأصدرت ECHO"
    elif decision.verdict in {LOAN, SEMITIC_LOAN, FORM}:
        outcome = "أُغلق النقل أو الصرف قبل دعوى الإرث؛ لم تُستعمل النواة للالتفاف على الإغلاق"
    else:
        outcome = "لم يكتمل الجذر الكامل؛ قُرئت النواة بعده ولم يصدر منها حكم مستقل بلا جسر"
    return (
        f"الجذر الكامل `{source}`↔`{decision.candidate}` فُحص أولًا: {outcome}. "
        "حدث الحرف ليس شرطًا لإصدار الحكم"
    )


def event_reference(candidate: str) -> str:
    tiers = FE.all_tiers(candidate)
    used = candidate
    if not tiers:
        used = candidate.translate(str.maketrans("أإؤئ", "ءءءء"))
        tiers = FE.all_tiers(used)
    if not tiers:
        return "لا قراءة مجمدة متاحة؛ سُجل الغياب ولم يُجعل حدث حرف بوابةً للحكم"
    return f"{tiers[0].line().removeprefix('- ')}؛ قُرئ مرجعًا بعد الجذر الكامل لا شرطًا حرفيًا"


def excerpt(value: str, limit: int) -> str:
    text = re.sub(r"\s+", " ", value).strip()
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def render_card(serial: int, index: int, row: dict, decision: Decision,
                matches_by_root: dict[str, list[dict]]) -> str:
    entry, hits, how = choose_entry(row)
    reading = str(entry.get("read") or "").strip() or str(row["say"]).split("  (")[0]
    gloss = excerpt(str(entry.get("en") or row.get("gloss") or ""), 280)
    etym = excerpt(str(entry.get("etym") or ""), 300)
    root = AR.normalize_root(decision.candidate)
    matches = matches_by_root.get(root, [])
    witnesses = R3.selected_witnesses(matches, decision.keywords)
    if witnesses:
        witness_text = "؛ ".join(
            f"قال {item['source_label']}: «{R3.excerpt(str(item.get('definition') or ''), decision.keywords, limit=120)}»"
            for item in witnesses
        )
    else:
        witness_text = "لم يرجع الفهرس شاهدًا عربيًا عاملًا؛ الفجوة محفوظة في الحكم"

    fans = FAN.fan(str(row["branch"]), "north")
    ranked = FAN.rank(str(row["branch"]), fans, "north", "hebrew")
    fan_rank = next((number for number, (value, _) in enumerate(ranked, 1)
                     if value == decision.candidate), None)
    membership = f"رتبته {fan_rank}" if fan_rank else "خارج السطح الآلي واستعيد من الجذر الكامل أو الصرف المكتوب"
    earliest = (
        f"{etym} [قاموس الفرع؛ قُرئت {len(hits)} مدخلة؛ {how}]"
        if etym else
        f"لا يسمّي العضو صورة أقدم أو مانحًا [قاموس الفرع؛ قُرئت {len(hits)} مدخلة؛ {how}]"
    )
    homonyms = "؛ ".join(
        f"{hit.get('pos') or 'مدخلة'} «{excerpt(str(hit.get('en') or ''), 72)}»"
        for hit in hits[:4]
    ) or "لا متجانس مسمى"
    shared = "، ".join(str(value) for value in row.get("shared") or []) or "لا لفظ مشترك حاكم"
    batch = 10 if serial <= BATCH_SIZE else 11
    within = ((serial - 1) % BATCH_SIZE) + 1
    card_id = f"WO-C-HEBREW-{batch:03d}-{within:03d}"
    degree = (
        "جذر كامل" if decision.verdict in {ROOT_TRACE, ROOT_ECHO}
        else "الجذر الكامل ثم النواة" if decision.verdict == NUCLEUS_ECHO
        else "الجذر الكامل أولًا؛ لا حكم موجب"
    )
    lines = [
        f"### {card_id}: `{row['branch']}` /{reading}/ ↔ `{decision.candidate}`",
        f"- إصدارُ البروتوكول: RECOVERY-v2 (2026-08-16)؛ النموذج: `{MODEL}`؛ ROUND21 (2026-08-18).",
        f"- الكلمةُ في الفرع: عبريّة `{row['branch']}` /{reading}/.",
        f"- أقدمُ صورةٍ مستعادة: {earliest}.",
        (f"- الخطوةُ صفر (التعرية بصرف الفرع): رُد السطح إلى الجذر العبري "
         f"`{decision.hebrew_root or row['skeleton']}` قبل المقارنة؛ لم يُسقط صامت لمجرد تحسين المرشح."),
        f"- درجةُ المقارنة: {degree}.",
        f"- التذكير السامي (الجذر الكامل أولًا ثم النواة): {root_first_note(row, decision)}.",
        (f"- مسحُ المعاني العربيّة: قُرئت {len(matches)} نتيجة للجذر `{root}` بما يكافئ "
         f"`--max-chars 0`؛ {witness_text}."),
        f"- المقابلُ من اللسان: `{decision.candidate}`؛ تغطية صف المسح: {shared}.",
        (f"- مسارُ الصوت: {sound_path(row, decision)}؛ قُرئت المروحة كاملة "
         f"({len(ranked)} مرشحًا)، والمنتخب {membership}."),
        f"- الحدثُ المجمّد: {event_reference(decision.candidate)}.",
        f"- المعنى من قاموس الفرع: «{gloss}» [العضو المختار بعد قراءة المتجانسات].",
        f"- المدار المكتوب باليد: {decision.orbit}",
        (f"- المصفاة: الحالة `{decision.state}`؛ الحكم لا يتجاوز الحس المختار، "
         "ولا يحول انخفاض الاسترجاع إلى نفي."),
        f"- فصلُ المتجانسات والاقتراض: المداخل المقروءة={len(hits)}؛ {homonyms}؛ الحكم للعضو المختار وحده.",
        (f"- مؤشر اليتم: صف `both[{index}]` في الحوض ذي {POOL_EXPECTED:,} صفًا؛ "
         f"التداخل {row['overlap']}؛ direct={str(bool(row['direct'])).lower()}؛ loan_suspect={str(bool(row['loan_suspect'])).lower()}."),
        f"- إشعاع الأسرة في الفرع: المتجانسات المقروءة={len(hits)}؛ المختار=1.",
        "- إشعاع الأسرة في العربية: [قُرئت المروحة كاملة ولم تُنسخ؛ طُبع شاهدان عاملان كحد أقصى].",
        "- جسور الاسترداد المفحوصة: الجذر الكامل؛ النواة بعده؛ صرف الشمال؛ المروحة؛ قاموس الفرع؛ شواهد العربية؛ صفوف الصوت؛ النقل والمتجانس.",
        f"- حالةُ الإغلاق: {decision.state}.",
        f"- الحكم (استكشاف): {decision.verdict}.",
        "- ملاحظات: عدسة الاسترداد أبقت المرشحات ظاهرة، وعدسة التشكيك منعت حدث الحرف من أن يصير شرطًا رابعًا.",
    ]
    card = "\n".join(lines) + "\n"
    size = len(card.encode("utf-8"))
    assert size <= MAX_CARD_BYTES, f"Oversize {card_id}: {size} bytes"
    return card


def render_appendices() -> tuple[str, str, dict, str]:
    original_memory, chosen, fresh_total, skipped = select_rows()
    roots = {AR.normalize_root(item.candidate) for item in DECISIONS}
    matches = AR.matches_for_roots(AR.DEFAULT_RESOURCES, roots, None)
    cards = [
        render_card(serial, index, row, decision, matches)
        for serial, ((index, row), decision) in enumerate(zip(chosen, DECISIONS), 1)
    ]
    body: list[str] = [
        f"<!-- {MARKER}:START -->", "",
        "## الجولة الحادية والعشرون: الحوض العبري المضاعف، الدفعة 010 (2026-08-18)", "",
        ("الحالة: طبقة الاستكشاف؛ إلحاق فقط. حُمّل `hebrew.md` مرة واحدة في الذاكرة، "
         "وتُجاوز كل رسم حاضر، ثم اختيرت أول خمسين بطاقة طازجة بترتيب `overlap` النازل."), "",
    ]
    for number, card in enumerate(cards, 1):
        if number == BATCH_SIZE + 1:
            body.extend([
                "## الجولة الحادية والعشرون: الحوض العبري المضاعف، الدفعة 011 (2026-08-18)", "",
                ("الحالة: طبقة الاستكشاف؛ إلحاق فقط. استؤنف متغير الذاكرة نفسه بلا إعادة تحميل، "
                 "واختيرت الخمسون التالية بالترتيب نفسه."), "",
            ])
        body.extend([card.rstrip(), ""])
        if number % 5 == 0:
            body.extend([f"<!-- LANE-C-R21-HEBREW-CHUNK-{number:03d}:END -->", ""])
    body.append(f"<!-- {MARKER}:END -->")
    appendix = "\n".join(body).rstrip() + "\n"

    verdicts = collections.Counter(item.verdict for item in DECISIONS)
    states = collections.Counter(item.state for item in DECISIONS)
    first_index = chosen[0][0]
    batch1_last = chosen[49][0]
    batch2_first = chosen[50][0]
    last_index = chosen[-1][0]
    now = datetime.now(ZoneInfo("Africa/Cairo")).strftime("%Y-%m-%d %H:%M:%S %z")
    now = now[:-2] + ":" + now[-2:]
    report = "\n".join([
        "", f"<!-- {REPORT_MARKER}:REPORT -->",
        "## الجولة الحادية والعشرون: المسار C، الحوض العبري المضاعف (2026-08-18)", "",
        f"- الوقت: {now}.",
        f"- حجم `both` المثبت: {POOL_EXPECTED:,} صفًا؛ الصفوف القديمة التي سماها أمر العمل: 1,319.",
        "- قانون التكرار: حُمّل `hebrew.md` كاملًا مرة واحدة، واختبر كل `branch` في الذاكرة، وأضيف كل رسم منتخب إلى المتغير نفسه فورًا.",
        f"- الطازج بحسب قانون الرسم بعد المسح الكامل={fresh_total}؛ المتجاوز في الحوض بسبب الحضور السابق أو تكرر الرسم={skipped}.",
        f"- الدفعة الأولى: 50 بطاقة؛ من `both[{first_index}]` إلى `both[{batch1_last}]` بترتيب overlap النازل بعد إسقاط المكرر.",
        f"- الدفعة الثانية: 50 بطاقة؛ من `both[{batch2_first}]` إلى `both[{last_index}]` بالترتيب نفسه ومن الذاكرة نفسها.",
        f"- الأحكام: {json.dumps(dict(sorted(verdicts.items())), ensure_ascii=False)}.",
        f"- حالات الإغلاق: {json.dumps(dict(sorted(states.items())), ensure_ascii=False)}؛ لا فجوة حُولت إلى نفي.",
        "- التذكير السامي مطبق في 100/100: الجذر الكامل أولًا، ثم النواة عند الحاجة فقط؛ حدث الحرف مرجع لا شرط.",
        "- بُنيت البطاقات على حقول نموذج `WO-B-PROBE-001` مع حفظ المتجانسات والنقل والمصفاة والحكم.",
        "- لا ship ولا commit ولا stage ولا تحديث مشتقات نشر.", "",
        f"LANE-C DONE21 {CARD_COUNT} both[{last_index}]",
    ]) + "\n"
    diagnostics = {
        "pool": POOL_EXPECTED,
        "fresh_total": fresh_total,
        "skipped": skipped,
        "batch_1": BATCH_SIZE,
        "batch_2": CARD_COUNT - BATCH_SIZE,
        "total": CARD_COUNT,
        "first_rank": f"both[{first_index}]",
        "batch_1_last": f"both[{batch1_last}]",
        "batch_2_first": f"both[{batch2_first}]",
        "last_rank": f"both[{last_index}]",
        "overlap_first": chosen[0][1]["overlap"],
        "overlap_last": chosen[-1][1]["overlap"],
        "verdicts": dict(sorted(verdicts.items())),
        "states": dict(sorted(states.items())),
        "max_card_bytes": max(len(card.encode("utf-8")) for card in cards),
        "appendix_bytes": len(appendix.encode("utf-8")),
    }
    return appendix, report, diagnostics, original_memory


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--show", type=int, choices=range(1, CARD_COUNT + 1))
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    appendix, report, diagnostics, original_memory = render_appendices()
    print(json.dumps(diagnostics, ensure_ascii=False, indent=2))
    if args.show:
        cards = re.split(r"(?=^### WO-C-HEBREW-)", appendix, flags=re.M)
        card = [value for value in cards if value.startswith("### WO-C-HEBREW-")][args.show - 1]
        print("\n" + card.split("\n<!--", 1)[0].rstrip())
    if args.apply:
        report_memory = REPORT.read_text(encoding="utf-8")
        if REPORT_MARKER in report_memory:
            raise SystemExit("Round-21 report marker already exists; append refused.")
        with HEBREW.open("a", encoding="utf-8", newline="\n") as handle:
            if not original_memory.endswith("\n"):
                handle.write("\n")
            handle.write("\n" + appendix)
        with REPORT.open("a", encoding="utf-8", newline="\n") as handle:
            if not report_memory.endswith("\n"):
                handle.write("\n")
            handle.write(report)
        print(f"APPENDED: {HEBREW.relative_to(ROOT)}")
        print(f"APPENDED: {REPORT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
