#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Append lane C round 18 completion cards without shipping.

Round seventeen was accepted and consolidated. This append-only round
rechecks the exhausted short live-open Aramaic queue, records the continued
transition to the registered Egyptian queue, and completes two forty-card
batches from WO-C-OPEN-COMP-00846. AED is read without a hit limit and the
deferred Egyptian ḏ row remains excluded. No git, publication, or shipping
command is run.
"""

from __future__ import annotations

import argparse
import collections
import json
import re
import unicodedata

import harvest_lane_c_round17 as R17


R9 = R17.R9
R10 = R17.R10
AR = R17.AR
ROOT = R17.ROOT
ARAMAIC = R17.ARAMAIC
EGYPTIAN = R17.EGYPTIAN
REPORT = R17.REPORT
MARKER = "LANE-C-ROUND18-2026-08-17"
FIRST_SERIAL = 846
BATCH_SIZE = 40
CARD_COUNT = 80
TRANSITION = (
    "ARAMAIC-SHORT-LIVE-OPEN-EXHAUSTED -> "
    "EGYPTIAN-RECORDED-OPEN-CONTINUED"
)


# Decisions remain member-scoped. The fan is a retrieval surface, not a sound
# law: ꜣ↔r and the other named single-member bridges below stay open. The one
# generic Semitic-loan label does not name a donor or direction, and uncertain
# AED glosses remain source gaps rather than being silently regularized.
DECISIONS: tuple[R9.Decision, ...] = (
    R9.gap("aed-v1.0:33830", "يدي", "SEMANTIC-GAP",
           "be subjugated/subjugate لا يطابق حواس يدي/ءدي العربية، ولا يُدخل خضوع أو قهر من خارج الرسم."),
    R9.gap("aed-v1.0:33890", "يدي", "SEMANTIC-GAP",
           "be deaf/deafen لا يطابق حواس يدي/يضي العربية، ولا يُدخل صمم من خارج الرسم."),
    R9.gap("aed-v1.0:34750", "علي", "SEMANTIC-GAP",
           "be great/rich/grow up لا يطابق حواس علي/عري في المروحة، ولا تُجمع العظمة والغنى والنماء في مادة مفترضة."),
    R9.gap("aed-v1.0:35310", "عرب", "SEMANTIC-GAP",
           "be pleasing لا يطابق حواس عرب/علب العربية، ولا يُدخل رضا أو حسن من خارج الرسم."),
    R9.gap("aed-v1.0:35710", "ععي", "SEMANTIC-GAP",
           "be fearful لا يطابق حواس ععي وبقية المروحة، ولا يُدخل خوف من خارج الرسم."),
    R9.gap("aed-v1.0:35740", "ععو", "SEMANTIC-GAP",
           "sleep، المقصور في AED على سياق النفي، لا يطابق حواس ععو وبقية المروحة، ولا يُدخل نوم من خارج الرسم."),
    R9.gap("aed-v1.0:36840", "عبب", "SOURCE-GAP",
           "AED يشك في make shiny وفي smooth معًا؛ لا يصدر مدار قبل ثبات الحدث نفسه."),
    R9.gap("aed-v1.0:37090", "عبر", "SEMANTIC-GAP",
           "equip/be equipped لا يطابق حواس عبر/عفر العربية، ولا يُدخل عدة أو جهاز من خارج الرسم."),
    R9.gap("aed-v1.0:37380", "عفن", "SEMANTIC-GAP",
           "cover/be covered لا يطابق العفن، وهو فساد من النداوة، ولا يُسوّى الغطاء بالتعفن."),
    R9.gap("aed-v1.0:38070", "عني", "SEMANTIC-GAP",
           "beautiful/kind/pleasing لا يطابق حواس عني/غني في المروحة، ولا تُدمج الصفات الثلاث في مقابل واحد."),
    R9.gap("aed-v1.0:38530", "عنخ", "SEMANTIC-GAP",
           "live/be alive لا يطابق حواس عنخ العربية المسجلة، ولا يكفي شيوع رمز الحياة المصري لإصدار صلة عربية."),
    R9.gap("aed-v1.0:38950", "عنخ", "SOURCE-GAP",
           "something bad, to be avoided تعريف اعتراضي عام لا يعين الحدث أو معناه المعجمي؛ لا يصدر مدار."),
    R9.gap("aed-v1.0:38960", "عنق", "SEMANTIC-GAP",
           "flow of the inundation لا يطابق العنق أو حواس عنق العربية، ولا يُدخل فيضان من خارج الرسم."),
    R9.gap("aed-v1.0:40130", "عحع", "SEMANTIC-GAP",
           "lack/be lacking/wait لا يطابق حواس عحع وبقية المروحة، ولا تُدمج حالة النقص وفعل الانتظار في مادة مفترضة."),
    R9.gap("aed-v1.0:40520", "عخي", "SEMANTIC-GAP",
           "burn/evaporate لا يطابق حواس عخي/غخي العربية، ولا يُدخل نار أو بخار من خارج الرسم."),
    R9.gap("aed-v1.0:41010", "عشر", "SEMANTIC-GAP",
           "be numerous/rich لا يطابق حواس عشر العربية؛ العدد عشرة لا يثبت الكثرة المطلقة أو الغنى."),
    R9.gap("aed-v1.0:41310", "عقر", "SEMANTIC-GAP",
           "accurate/make accurate لا يطابق حواس عقر/عقل العربية في المروحة، ولا يُدخل صواب من خارج الرسم."),
    R9.gap("aed-v1.0:42410", "وري", "LAW-GAP",
           "parch grain/burn يلتقي وريت النار وأوريتها، لكن w-ꜣ-j لا يسوي و-r-y بطريق مصري موقع كامل.",
           sound="w↔و وj↔ي ظاهران؛ ꜣ↔ر هو الموضع غير الموقع لهذا العضو.",
           orbit="وريت النار اتقدت وأوريتها أوقدتها؛ التحميص صورة مخصوصة من الإحراق.",
           keywords="وريت|النار|اتقدت|أوريتها|أوقدتها"),
    R9.gap("aed-v1.0:42550", "ورء", "LAW-GAP",
           "be far/remove oneself يجاور وراء بوصفه جهة خلف وبعد، لكن w-ꜣ-j لا يسوي و-r-ء بطريق مصري كامل.",
           sound="w↔و ظاهر؛ ꜣ↔ر وj↔ء غير موقعين معًا لهذا العضو.",
           orbit="وراء جهة مباعدة لا فعل الابتعاد نفسه؛ بقي الصوت والمدار ناقصين."),
    R9.gap("aed-v1.0:43310", "ورس", "SEMANTIC-GAP",
           "possess power/have dominion/be happy لا يطابق حواس ورس/ولس العربية، ولا تُجمع السلطة والسعادة في مقابل واحد."),
    R9.gap("aed-v1.0:43420", "ورش", "SEMANTIC-GAP",
           "be powerful/worship لا يطابق حواس ورش/ورس العربية، ولا تُسوّى المنزلة بالعبادة."),
    R9.gap("aed-v1.0:44350", "وعي", "SEMANTIC-GAP",
           "be alone/be the only one لا يطابق الوعي أو حواس وعي العربية، ولا يُدخل واحد بصوامت غير محمولة."),
    R9.gap("aed-v1.0:44430", "وعب", "SEMANTIC-GAP",
           "purify/be pure لا يطابق حواس وعب/وغب العربية، ولا يُدخل طهر من خارج الرسم."),
    R9.gap("aed-v1.0:44640", "وعف", "SEMANTIC-GAP",
           "be bent/bend down لا يطابق حواس وعف/وغف العربية، ولا يُدخل عطف أو حنى من خارج الرسم."),
    R9.gap("aed-v1.0:44890", "وبر", "SEMANTIC-GAP",
           "open/drill stone لا يطابق حواس وبر/وبل العربية، ولا يُدخل ثقب من خارج الرسم."),
    R9.gap("aed-v1.0:45270", "وبخ", "SEMANTIC-GAP",
           "be bright/brighten لا يطابق التوبيخ أو حواس وبخ العربية، ولا يُدخل ضياء من خارج الرسم."),
    R9.gap("aed-v1.0:45410", "وبد", "SEMANTIC-GAP",
           "burn/heat لا يطابق حواس وبد/وبض العربية، ولا يُدخل نار أو حر من خارج الرسم."),
    R9.gap("aed-v1.0:45640", "وفي", "SEMANTIC-GAP",
           "divide/open/judge لا يطابق الوفاء أو حواس وفي العربية، ولا تُدمج الأفعال الثلاثة في مادة مفترضة."),
    R9.gap("aed-v1.0:45800", "وبس", "SEMANTIC-GAP",
           "burn up enemies لا يطابق حواس وبس/وفص العربية، ولا يُدخل إحراق من خارج الرسم."),
    R9.gap("aed-v1.0:45920", "ومت", "SEMANTIC-GAP",
           "be thick/become thick لا يطابق حواس ومت/ومط العربية، ولا يُدخل غلظ من خارج الرسم."),
    R9.gap("aed-v1.0:46660", "ونف", "SEMANTIC-GAP",
           "be glad/rejoice لا يطابق حواس ونف العربية، ولا يُدخل فرح من خارج الرسم."),
    R9.gap("aed-v1.0:46710", "ونم", "SEMANTIC-GAP",
           "eat لا يطابق حواس ونم العربية، ولا يُدخل أكل أو نهم بصوامت غير محمولة."),
    R9.gap("aed-v1.0:47270", "ورر", "SEMANTIC-GAP",
           "be great/be large لا يطابق حواس ورر/ولل العربية، ولا يُدخل كبر من خارج الرسم."),
    R9.gap("aed-v1.0:48420", "وهم", "SEMANTIC-GAP",
           "burn لا يطابق الوهم أو الوحم، ولا يُدخل نار من خارج الرسم."),
    R9.gap("aed-v1.0:48640", "وحش", "SEMANTIC-GAP",
           "slacken/be worn out لا يطابق الوحشة أو حواس وحش/وهس العربية، ولا يُدخل وهن من خارج الرسم."),
    R9.gap("aed-v1.0:48660", "وحر", "SEMANTIC-GAP",
           "quarry stone/cut down لا يطابق حواس وحر/وحل العربية، ولا يُدخل قلع أو قطع من خارج الرسم."),
    R9.gap("aed-v1.0:49010", "وحص", "SEMANTIC-GAP",
           "cut off/down لا يطابق حواس وحص، ومنها السحب والبرد والعلة، ولا يُسوّى السحب بالقطع."),
    R9.gap("aed-v1.0:49120", "وخي", "MORPHOLOGY-GAP",
           "seek/want يطابق وخى الأمر، أي قصده وتوخاه، لكن ꜣ المصرية لا تحمل الياء الجذرية العربية بطريق صرفي موقع.",
           sound="w↔و وḫ↔خ هويتان؛ ꜣ المصرية ↔ ي وخي هو الموضع الصرفي غير الموقع.",
           orbit="طلب الشيء وقصده مدار مباشر؛ take أوسع ولا يرث الحكم.",
           keywords="وخى|قصده|توخى|القصد",
           zero="حُفظ wḫꜣ كاملًا؛ وخي قراءة صرفية عربية تشخيصية خارج سطح المروحة، لا حذف مصري ولا موجب."),
    R9.gap("aed-v1.0:49170", "وخا", "SEMANTIC-GAP",
           "be foolish لا يطابق حواس وخا/وخر العربية، ولا يُدخل سفه من خارج الرسم."),
    R9.gap("aed-v1.0:49470", "وسي", "SEMANTIC-GAP",
           "saw/cut لا يطابق حواس وسي/وصي العربية، ولا يُدخل نشر أو قطع من خارج الرسم."),
    R9.gap("aed-v1.0:49520", "وزف", "SEMANTIC-GAP",
           "be idle/neglect لا يطابق حواس وزف/وسف العربية، ولا يُدخل كسل أو إهمال من خارج الرسم."),
    R9.gap("aed-v1.0:49780", "وسح", "SEMANTIC-GAP",
           "burn/heat لا يطابق حواس وسح/وشح/وصح العربية، ولا يُدخل نار من خارج الرسم."),
    R9.gap("aed-v1.0:49800", "وسخ", "SEMANTIC-GAP",
           "be wide/broad لا يطابق الوسخ أو حواس وشخ/وصخ العربية، ولا يُدخل سعة من خارج الرسم."),
    R9.gap("aed-v1.0:50020", "وسط", "SEMANTIC-GAP",
           "be dilapidated لا يطابق الوسط أو حواس وزث/وست العربية، ولا يُدخل خراب من خارج الرسم."),
    R9.gap("aed-v1.0:50900", "وجس", "SEMANTIC-GAP",
           "cut open/gut animals لا يطابق الوجس أو حواس وقص/وغص العربية، ولا يُدخل بقر البطن من خارج الرسم."),
    R9.gap("aed-v1.0:51170", "وطن", "SEMANTIC-GAP",
           "break through لا يطابق الوطن أو حواس وتن العربية، ولا يُدخل خرق من خارج الرسم."),
    R9.gap("aed-v1.0:51330", "وثز", "SEMANTIC-GAP",
           "lift up/carry لا يطابق حواس وثز/وتس العربية، ولا يُدخل رفع أو حمل من خارج الرسم."),
    R9.gap("aed-v1.0:51950", "ودد", "SEMANTIC-GAP",
           "cook/burn لا يطابق الود أو حواس وضض العربية، ولا يُدخل طبخ من خارج الرسم."),
    R9.gap("aed-v1.0:53170", "بري", "SEMANTIC-GAP",
           "be moist لا يطابق حواس بري/بلي العربية، ولا يُدخل بلل من خارج الرسم."),
    R9.gap("aed-v1.0:53730", "برق", "LAW-GAP",
           "be bright يطابق برق الشيء، أي لمع، لكن b-ꜣ-q لا يسوي ب-r-q بطريق مصري موقع كامل.",
           sound="b↔ب وq↔ق هويتان؛ ꜣ↔ر هو الموضع غير الموقع لهذا العضو.",
           orbit="اللمعان والوضوح الحسي مدار مباشر؛ clear of character وbe well لا يرثان الحكم.",
           keywords="برق|لمع|تلألأ|البريق"),
    R9.gap("aed-v1.0:54600", "بين", "SEMANTIC-GAP",
           "be bad/be evil لا يطابق حواس بين/بءن العربية، ولا يُدخل شر من خارج الرسم."),
    R9.gap("aed-v1.0:55260", "بوء", "SEMANTIC-GAP",
           "be high/be esteemed لا يطابق حواس بوء/بور العربية، ولا يُدخل علو أو منزلة من خارج الرسم."),
    R9.gap("aed-v1.0:55940", "بني", "SEMANTIC-GAP",
           "be sweet لا يطابق البناء أو حواس بني العربية، ولا يُدخل حلاوة من خارج الرسم."),
    R9.gap("aed-v1.0:57080", "بخخ", "SEMANTIC-GAP",
           "burn/glow لا يطابق حواس بخخ العربية، ولا يُدخل جمر أو نار من خارج الرسم."),
    R9.gap("aed-v1.0:57530", "بسك", "SEMANTIC-GAP",
           "cut out/eviscerate لا يطابق حواس بسك/بشك/بصك العربية، ولا يُدخل نزع الأحشاء من خارج الرسم."),
    R9.gap("aed-v1.0:57700", "بقي", "DIRECTIONAL-TRANSMISSION",
           "stay يطابق بقي، لكن AED يشك في open/stay ويسمي Semitic loan بلا مانح أو طريق؛ لا يحسم التشابه اتجاه النقل.",
           sound="b↔ب وq↔ق وy↔ي هويات سطحية؛ الهوية لا تعين المانح ولا تثبت الوجه المشكوك.",
           orbit="البقاء ثبات الشيء على حاله؛ open حس آخر مشكوك لا يرث هذا المدار.",
           keywords="بقي|البقاء|ثبات|أقام"),
    R9.gap("aed-v1.0:57820", "بكر", "SEMANTIC-GAP",
           "become pregnant/make pregnant لا يطابق البكر أو حواس بكا/بكل العربية، ولا يُسوّى الحمل بالبكارة."),
    R9.gap("aed-v1.0:58140", "بتر", "SEMANTIC-GAP",
           "make oneself guilty لا يطابق البتر أو البطر، ولا يُدخل ذنب من خارج الرسم."),
    R9.gap("aed-v1.0:58470", "بدش", "SEMANTIC-GAP",
           "be weak/be inert لا يطابق حواس بدش/بضس العربية، ولا يُدخل ضعف أو خمول من خارج الرسم."),
    R9.gap("aed-v1.0:59960", "بنع", "SEMANTIC-GAP",
           "turn upside down/be overturned لا يطابق حواس بنع/فنع العربية، ولا يُدخل قلب من خارج الرسم."),
    R9.gap("aed-v1.0:60070", "بنس", "SEMANTIC-GAP",
           "pull out/cut off لا يطابق بنس بمعنى التأخر ولا فنس بمعنى الفقر، ولا يُدخل نزع من خارج الرسم."),
    R9.gap("aed-v1.0:60180", "فند", "SEMANTIC-GAP",
           "make fruitful لا يطابق الفند بمعاني الضعف والخطأ ولا حواس بند، ولا يُدخل إثمار من خارج الرسم."),
    R9.gap("aed-v1.0:60920", "بري", "SEMANTIC-GAP",
           "go forth/come forth لا يطابق حواس بري/فري العربية مباشرة، ولا يُدخل خرج من خارج الرسم."),
    R9.gap("aed-v1.0:61130", "برع", "SOURCE-GAP",
           "be accessible نفسه موسوم بالشك؛ لا يثبت حدثًا يمكن موازنته بحواس برع/بلغ قبل حسم القراءة."),
    R9.gap("aed-v1.0:61730", "فخر", "SEMANTIC-GAP",
           "open في الاستعمال الطبي لا يطابق حواس فخر/فخل العربية، ولا يُدخل شق من خارج الرسم."),
    R9.gap("aed-v1.0:61900", "بحر", "SEMANTIC-GAP",
           "turn round/go around لا يطابق حواس بحر/بخر/فخر العربية، ولا يُدخل دوران من خارج الرسم."),
    R9.gap("aed-v1.0:62240", "فسخ", "SEMANTIC-GAP",
           "be in disarray/be distraught لا يطابق فسخ الشيء وحله مباشرة، ولا تُسوّى الحالة النفسية بنقض العقد."),
    R9.gap("aed-v1.0:62730", "فجر", "LAW-GAP",
           "unfold/open up يلتقي فجر الشيء، أي شقه شقًا واسعًا، لكن p-g-ꜣ لا يسوي ف-j-r بطريق مصري كامل.",
           sound="p↔ف وg↔ج ظاهران في المروحة؛ ꜣ↔ر هو الموضع غير الموقع لهذا العضو.",
           orbit="الفتح والانشقاق الواسع مدار مباشر؛ unfold أوسع من تفجير الماء.",
           keywords="فجر|شق|انفجر|تفتح|فتح"),
    R9.gap("aed-v1.0:62870", "بقس", "SEMANTIC-GAP",
           "be clothed/ready لا يطابق حواس بقس/فقش العربية، ولا يُدخل لبس أو إعداد من خارج الرسم."),
    R9.gap("aed-v1.0:62900", "بصر", "LAW-GAP",
           "see/behold يطابق البصر، لكن p-t-r لا يسوي ب-ص-r لأن t↔ص غير مرخص في المروحة المصرية.",
           sound="p↔ب وr↔ر ظاهران؛ t المصرية ↔ ص العربية هي الرجل غير الموقعة.",
           orbit="الإبصار والرؤية مدار مباشر كامل الدلالة؛ عائق الصوت وحده باق.",
           keywords="بصر|أبصر|رأى|الرؤية"),
    R9.gap("aed-v1.0:63460", "فري", "SEMANTIC-GAP",
           "lift/carry لا يطابق حواس فري/فلي العربية، ولا يُدخل رفع أو حمل من خارج الرسم."),
    R9.gap("aed-v1.0:63680", "فرك", "SEMANTIC-GAP",
           "be shorn لا يطابق حواس فرك/فلك العربية، ولا يُدخل حلق أو جز من خارج الرسم."),
    R9.gap("aed-v1.0:63700", "فرق", "LAW-GAP",
           "cut off the foreleg يلتقي فرق الشيء وفصله، لكن f-ꜣ-g لا يسوي ف-r-q بطريق مصري موقع كامل.",
           sound="f↔ف ظاهر؛ ꜣ↔ر وg↔ق لا يجتمعان في مسار عضو موقع.",
           orbit="القطع فصل عضو من الجسد، وهو من مدار الفرق؛ تعيين foreleg لا ينتقل إلى العربية.",
           keywords="فرق|فصل|قطع|انفصل"),
    R9.gap("aed-v1.0:63730", "فيو", "SOURCE-GAP",
           "be revolted at يفسره الألماني sich ekeln مع علامة شك؛ لا يثبت هل الحدث اشمئزاز أو نفور أوسع."),
    R9.gap("aed-v1.0:63740", "فيث", "SEMANTIC-GAP",
           "deride/be scornful لا يطابق حواس فيث/فيت العربية، ولا يُدخل سخر أو احتقار من خارج الرسم."),
    R9.gap("aed-v1.0:63860", "فنخ", "SOURCE-GAP",
           "acute يفسر في الألماني klug sein أو ما شابهه؛ لا يُحسم هل المراد حدة حسية أم ذكاء."),
    R9.gap("aed-v1.0:66270", "مرء", "MORPHOLOGY-GAP",
           "see/look يجاور المرأى والرؤية، لكن m-ꜣ-ꜣ لا يحمل جذر رأي ولا يثبت ميم العربية زائدة صرفية مقابلة.",
           sound="الرسم المصري m-ꜣ-ꜣ محفوظ؛ بنية م-r-ء العربية ليست مسارًا مصريًا موقعًا.",
           orbit="المرأى ما تراه العين، لكنه اسم مصدري عربي لا جذرًا مطابقًا للفعل المصري."),
    R9.gap("aed-v1.0:67280", "مرح", "SEMANTIC-GAP",
           "burn up لا يطابق المرح أو حواس ملح/مرخ العربية، ولا يُدخل إحراق من خارج الرسم."),
    R9.gap("aed-v1.0:69220", "موه", "MORPHOLOGY-GAP",
           "be moist/wet يلتقي الماء، وأصل ماء العربي موه، لكن j المصرية النهائية لا تسوي هاء موه أو همزة ماء بصرف موقع.",
           sound="m↔م وw↔و هويتان؛ j المصرية ↔ ه/ء العربية هي الرجل الصرفية غير الموقعة.",
           orbit="الماء أصل البلل والرطوبة، لكن علاقة الشيء بصفته لا تعالج اختلاف اللام.",
           keywords="الماء|ماء|أمواه|مياه|البلل",
           zero="حُفظ mwj كاملًا؛ موه أصل عربي منشور لماء، لكنه خارج سطح المروحة ولا يبرر حذف j المصرية."),
    R9.gap("aed-v1.0:71080", "منخ", "SEMANTIC-GAP",
           "be splendid/effective لا يطابق حواس منخ العربية، ولا تُجمع الروعة والفاعلية في مقابل مفترض."),
)


EXPECTED_IDS = tuple(item.member_id for item in DECISIONS)
assert len(DECISIONS) == CARD_COUNT


def round18_card(serial: int, rank: int, item: dict, decision: R9.Decision,
                 matches: dict[str, list[dict]]) -> str:
    card = R17.round17_card(serial, rank, item, decision, matches)
    card = card.replace("ROUND17-COMPLETION", "ROUND18-COMPLETION")
    card = card.replace(
        f"round17-egyptian-rank={rank}/{CARD_COUNT}",
        f"round18-egyptian-rank={rank}/{CARD_COUNT}",
    )
    size = len(card.encode("utf-8"))
    assert size <= R9.MAX_CARD_BYTES, (
        f"Oversize WO-C-OPEN-COMP-{serial:05d}: {size} bytes"
    )
    return card


def render_appendices() -> tuple[str, str, dict]:
    aramaic_text = ARAMAIC.read_text(encoding="utf-8")
    egyptian_text = EGYPTIAN.read_text(encoding="utf-8")
    report_text = REPORT.read_text(encoding="utf-8")
    if MARKER in egyptian_text or MARKER in report_text:
        raise SystemExit("Round-eighteen marker already exists; append refused.")

    aramaic_exact, _ = R9.load_entries("aramaic")
    aramaic_queue = R9.select_aramaic(aramaic_text, aramaic_exact)
    assert not aramaic_queue, (
        "Aramaic short live-open queue is no longer exhausted: "
        f"{[item['entry_id'] for item in aramaic_queue[:10]]}"
    )

    egyptian_exact, _ = R9.load_entries("egyptian")
    queue = R9.select_egyptian(egyptian_text, egyptian_exact)
    selected = queue[:CARD_COUNT]
    actual_ids = tuple(str(item["entry_id"]) for item in selected)
    assert actual_ids == EXPECTED_IDS, (
        f"Egyptian queue drifted:\nexpected={EXPECTED_IDS}\nactual={actual_ids}"
    )
    assert all("ḏ" not in str(item["headword"]) for item in selected)

    roots = {
        AR.normalize_root(item.candidate)
        for item in DECISIONS if item.candidate not in {"∅", ""}
    }
    matches = AR.matches_for_roots(AR.DEFAULT_RESOURCES, roots, None)
    cards = [
        round18_card(FIRST_SERIAL + rank - 1, rank, item, decision, matches)
        for rank, (item, decision) in enumerate(zip(selected, DECISIONS), 1)
    ]

    body = [
        f"<!-- {MARKER}:EGYPTIAN:START -->", "",
        "## الجولة الثامنة عشرة: استمرار المخزون المصري المسجل المفتوح (2026-08-17)", "",
        ("أُعيد فحص الآرامية أولًا فكان الطابور القصير الحي ذا المروحة غير الفارغة صفرًا. "
         f"لذلك سُجل الانتقال المسمى `{TRANSITION}`. انتُقيت البطاقات المصرية التالية "
         "بدءًا من `WO-C-OPEN-COMP-00846` بقصر الهيكل ثم موضع اللقطة. استُبعد صف ḏ "
         "المؤجل. في كل بطاقة عُرضت إصابات AED كلها بلا حد، وكُتب وسم الطريق والرسم "
         "والمدخل المختار، وحُفظ الاختلاف والمتجانسات بلا محو."), "",
        "### الدفعة الأولى: WO-C-OPEN-COMP-00846 إلى WO-C-OPEN-COMP-00885", "",
    ]
    for rank, card in enumerate(cards, 1):
        if rank == BATCH_SIZE + 1:
            body.extend([
                "### الدفعة الثانية: WO-C-OPEN-COMP-00886 إلى WO-C-OPEN-COMP-00925", "",
            ])
        body.extend([card.rstrip(), ""])
        if rank % 5 == 0:
            body.extend([f"<!-- LANE-C-R18-EGYPTIAN-CHUNK-{rank:03d}:END -->", ""])
    body.append(f"<!-- {MARKER}:EGYPTIAN:END -->")

    state_counts = dict(sorted(collections.Counter(item.state for item in DECISIONS).items()))
    verdict_counts = dict(sorted(collections.Counter(item.verdict for item in DECISIONS).items()))
    last_serial = FIRST_SERIAL + CARD_COUNT - 1
    report = "\n".join([
        "", f"<!-- {MARKER}:REPORT -->",
        "## الجولة الثامنة عشرة: المسار C (2026-08-17)", "",
        "- أُعيد فحص الآرامية أولًا: المفتوح القصير الحي ذو المروحة غير الفارغة=0؛ لم تُكرر بطاقة آرامية.",
        f"- سُجل الانتقال المسمى `{TRANSITION}` إلى المصري المسجل عند نفاد الساميّات.",
        "- كُتبت الدفعة الأولى: 40 بطاقة مصرية من `WO-C-OPEN-COMP-00846` إلى `WO-C-OPEN-COMP-00885`.",
        "- كُتبت الدفعة الثانية: 40 بطاقة مصرية من `WO-C-OPEN-COMP-00886` إلى `WO-C-OPEN-COMP-00925`.",
        "- طُبقت قواعد AED الثلاث: كل الإصابات بلا حد؛ وسم الطريق والرسم والمدخل المختار مكتوبة؛ الاختلاف والمتجانسات محفوظة بلا محو.",
        f"- حالات الإغلاق بعد القراءة: {json.dumps(state_counts, ensure_ascii=False, sort_keys=True)}؛ لا فجوة حُولت إلى نفي.",
        f"- الأحكام: {json.dumps(verdict_counts, ensure_ascii=False, sort_keys=True)}؛ لم يصدر حكم موجب في هذه النافذة.",
        "- المطابقات الدلالية ذات الرجل الناقصة بقيت مفتوحة باسمها: `wꜣj↔وري` و`bꜣq↔برق` و`pgꜣ↔فجر` و`ptr↔بصر` و`fꜣg↔فرق` للصوت، و`wḫꜣ↔وخي` و`mwj↔موه` للصرف.",
        "- `bqy↔بقي` بقي `DIRECTIONAL-TRANSMISSION`: المعنى نفسه مشكوك ووسم القرض السامي لا يسمي مانحًا أو طريقًا.",
        "- صف ḏ مؤجل بقرار المؤلف؛ استُبعد من الانتقاء وبقيت بطاقاته على حالها.",
        "- لا ship ولا commit ولا stage ولا تحديث مشتقات نشر.", "",
        f"LANE-C DONE18 {CARD_COUNT} WO-C-OPEN-COMP-{last_serial:05d}",
    ]) + "\n"

    diagnostics = {
        "aramaic_live_open": len(aramaic_queue),
        "transition": TRANSITION,
        "egyptian_queue_before": len(queue),
        "batch_1": BATCH_SIZE,
        "batch_2": CARD_COUNT - BATCH_SIZE,
        "total_cards": CARD_COUNT,
        "first_card": f"WO-C-OPEN-COMP-{FIRST_SERIAL:05d}",
        "last_card": f"WO-C-OPEN-COMP-{last_serial:05d}",
        "states": state_counts,
        "verdicts": verdict_counts,
        "max_card_bytes": max(len(card.encode("utf-8")) for card in cards),
    }
    egyptian_appendix = unicodedata.normalize("NFC", "\n".join(body).rstrip() + "\n")
    report_appendix = unicodedata.normalize("NFC", report)
    return egyptian_appendix, report_appendix, diagnostics


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    parser.add_argument(
        "--show", type=int,
        choices=range(FIRST_SERIAL, FIRST_SERIAL + CARD_COUNT),
    )
    args = parser.parse_args()
    egyptian, report, diagnostics = render_appendices()
    print(json.dumps(diagnostics, ensure_ascii=False, indent=2))
    if args.show:
        card_id = f"WO-C-OPEN-COMP-{args.show:05d}"
        match = re.search(
            rf"(?ms)^### {re.escape(card_id)}:.*?(?=^### |^<!-- |\Z)",
            egyptian,
        )
        assert match
        print("\n" + match.group().rstrip())
    if args.apply:
        R10.append(EGYPTIAN, f"{MARKER}:EGYPTIAN", egyptian)
        R10.append(REPORT, f"{MARKER}:REPORT", report)
        print(f"APPENDED: {EGYPTIAN.relative_to(ROOT)}")
        print(f"APPENDED: {REPORT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
