# سجل القروض المعزولة في قراءات الاسترداد

التاريخ: 2026-08-27

الحالة: سجل داخلي استرجاعي. لا يستنبط قرضًا ولا اتجاهًا ولا مصدرًا، بل ينقل بطاقات `LOANWORD` الصريحة المودعة في `HEAD` كما هي. الأحكام المحلية غير المراجعة لا تدخل السجل، والحقل الفارغ يبقى فارغًا ولا يستكمل بالتخمين.

| اللغة | البطاقة | اللفظ | المسار المسمى في البطاقة | المصدر المسمى | الموضع |
|---|---|---|---|---|---|
| العبرية | blwg (بلوج) «مدوّنة إلكترونية» | בלוג blwg (بلوج)، وصورتها المعجمية בְּלוֹג bəlwog (بلوج)، اسم مذكر؛ نطق `scripts/readable.py` هو `blwg (بلوج)` و`bəlwog (بلوج)`، والرومنة المنشورة `blog`. | يعزل مسارًا مسمى من الإنجليزية إلى العبرية: `Borrowed from English blog`. صححت القراءة السالب الكاذب `loan_suspect=false` في الصف، ولم تغير ملف الطابور المولد. | Kaikki Hebrew، السطر 5217؛ Kaikki Hebrew، `kaikki_hebrew:5217:en-בלוג-he-noun-4iFKqZz4` | `04-cross-linguistic/readings/hebrew.md:44097` |
| العبرية | hyndy (هـيندي) «اللغة الهندية Hindi» | הינדי hyndy (هـيندي)، اسم لغة مؤنث؛ نطق `scripts/readable.py` هو `hyndy (هـيندي)`، والرومنة المنشورة `híndi`. | يعزل مسارًا من Classical Persian هندی إلى العبرية. صححت القراءة السالب الكاذب `loan_suspect=false`. هند ليس في جرد القرآن؛ لا تُستنتج من الغياب دعوى اتجاه إلى العربية. | Kaikki Hebrew، السطر 15466؛ Kaikki Hebrew، `kaikki_hebrew:15466:en-הינדי-he-name-oonRlPW~` | `04-cross-linguistic/readings/hebrew.md:44139` |
| العبرية | kslw (كسلو) «شهر كِسليف» | כסלו kslw (كسلو)، وصورتها المعجمية כִּסְלֵו kisəlew (كسلو)، اسم شهر؛ نطق `scripts/readable.py` هو `kslw (كسلو)` و`kisəlew (كسلو)`. | `From Akkadian 𒌗𒃶 (ⁱᵗⁱkislimu)` مسار مانح صريح. لا يُبدَّل هذا إلى وراثة بسبب `loan_suspect=false`، ولا تُغلق كسل القرآنية قرضًا. | نحميا 1:1؛ Kaikki Hebrew، السطر 10672؛ Kaikki Hebrew، `kaikki_hebrew:10672:en-כסלו-he-name-m7A8vug9` | `04-cross-linguistic/readings/hebrew.md:44234` |
| العبرية | hndsh (هـندسهـ) «الهندسة والهندسة الرياضية» | הנדסה hndsh (هـندسهـ)، وصورتها المعجمية הַנְדָּסָה hanədāsāh (هـندسهـ)، اسم مؤنث؛ نطق `scripts/readable.py` هو `hndsh (هـندسهـ)` و`hanədāsāh (هـندسهـ)`. | نص المورد: `From Arabic هَنْدَسَة (handasa), from the same Iranic source as modern Persian ... “measuring”`. صحح ذلك السالب الكاذب `loan_suspect=false`. هندس ليست في جرد القرآن؛ الحكم بالقرض مصدره النص المعجمي لا الغياب. | معجم الرياضيات الصادر عن لجنة اللغة سنة 1940؛ Kaikki Hebrew، `kaikki_hebrew:3353:en-הנדסה-he-noun--Jzi8ZIV` و`en-הנדסה-he-noun-Y9bVpruY` | `04-cross-linguistic/readings/hebrew.md:44440` |
| العبرية | ʿrq (عرق) «شراب العَرَق» | ערק ʿrq (عرق)، وصورتها المعجمية الاسمية עַרַק ʿaraq (عرق)، اسم مذكر؛ نطق `scripts/readable.py` هو `ʿrq (عرق)` و`ʿaraq (عرق)`. | `From Arabic عَرَق` مسار مانح صريح، فيصحح `loan_suspect=false`. عرق وعرك وغرك وضرك ليست في جرد الجذور القرآنية؛ حرق وغرق وحرك قرآنية ومحفوظة عربية محضة، ولم تُغلق أي منها قرضًا. | مرسوم المشروبات المسكرة المؤرخ 4 ديسمبر 1927؛ Kaikki Hebrew، `kaikki_hebrew:2447:en-ערק-he-noun-b-~cloFE` | `04-cross-linguistic/readings/hebrew.md:44463` |
| القبطية | tōōbe «brick, adobe» | ⲧⲱⲱⲃⲉ tōōbe | يعزل مسارا: القبطية إلى العربية المصرية [Hinds and Badawi, *A Dictionary of Egyptian Arabic*, 1986، مادة طوبة] | Hinds and Badawi, *A Dictionary of Egyptian Arabic*, 1986، مادة طوبة؛ TLA Lemma ID 183120؛ Erman & Grapow, Wb 5, 553.7-554.18: https://thesaurus-linguae-aegyptiae.de/lemma/183120؛ Crum, CD 398a؛ KELLIA C4084/C4085 | `04-cross-linguistic/readings/coptic.md:90` |
| القبطية | apa «abbot (father); title of reverence» | ⲁⲡⲁ apa، وله وجه ⲁⲃⲃⲁ | يعزل مسارا: سريانية إلى يونانية ἀββᾶς ثم إلى القبطية، كما يصرح حقل `<etym>` | KELLIA C164؛ Crum, CD 13ab؛ Crum, CD 13ab؛ KELLIA C164 | `04-cross-linguistic/readings/coptic.md:104` |
| اللاتينية القديمة | corōlla «إكليل صغير، طوق زهر» | corōlla؛ وأخرجت أداة النطق المجمدة corolla؛ والنطق الكلاسيكي /kɔˈroːl.la/ «كُرولّا». | يعزل مسارا يونانيا قديما إلى اللاتينية: κορώνη ← corōna ← corōlla. ليست المشكلة أن corolla دولية نباتية حديثة؛ الحس القديم كلاسيكي، لكن القاعدة اللاتينية نفسها قرض يوناني. | Kaikki Latin، corolla وcorona؛ Kaikki Latin، corolla؛ Lewis & Short، corolla | `04-cross-linguistic/readings/old-latin.md:217228` |
| اللاتينية القديمة | follis «منفاخ؛ كيس أو صرّة نقود» | follis؛ وأخرجت أداة النطق المجمدة `follis`؛ والنطق الكلاسيكي /ˈfɔl.lɪs/ «فُلِّس». | يعزل مسارًا: Latin follis → Greek phóllis → Aramaic puləsā → Arabic fals. تؤكد Encyclopaedia Iranica أن folūs من Greek phóllis ومن Latin follis في النقد البيزنطي. الحكم LATIN-TO-ARABIC-TRANSMISSION، لا أثر موروث. | Kaikki Latin، `follis`، `etymology_text`؛ Kaikki Latin، `follis`؛ Lewis & Short، `follis` | `04-cross-linguistic/readings/old-latin.md:217394` |

## حدود السجل

- لا يدخل وسم القرض الآلي أو مجرد ذكر أصل أجنبي ما لم تحمل البطاقة حكم `LOANWORD` صريحًا.
- يقرأ المولد نسخة `HEAD` لا شجرة العمل، حتى لا يتسرب حكم محلي ينتظر المراجعة إلى السجل البنيوي المودع.
- الحكم للعضو أو سلسلة المعنى المسماة، ولا ينتقل إلى بقية الأسرة أو المركبات أو المتجانسات.
- هذا سجل عزل ومحاسبة، وليس بسطًا لخط البرهان ولا رقمًا للنشر.
- يعاد بناؤه بالأمر `python scripts/build_recovery_loan_registry.py --check` للتحقق، أو بلا `--check` للتحديث.

## عائق فحص كفر القرية

- عائق: النوع=SOURCE-GAP؛ يتطلب=نسخة محلية مشروعة من Fraenkel, *Die aramäischen Fremdwörter im Arabischen* لفحص عضو كفر بمعنى القرية.
- استنفاد البحث المحلي: لم توجد نسخة من الكتاب في `Resources/` أو في ملفات المشروع. الموجود إحالة ببليوغرافية إليه فقط، فلا تعامل الإحالة نسخة مفحوصة.
- النتيجة: يبقى عضو القرية الآرامي معاد الفتح، ولا يمس ذلك عضو الإنكار أو التكفير.
