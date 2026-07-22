# توقيعُ المؤلّف: التسجيلُ المسبقُ لخطِّ البرهانِ الساميّ (2026-07-23)

**السند:** عُرِضَت على المؤلّفِ ياسين تمسّك ورقةُ العرضِ النهائيِّ `_inbox/2026-07-22-proof-preregistration-final-author-review.md` بندًا بندًا بالعربيّةِ الميسَّرة، ومعها تحفُّظُ العدسةِ الثالثةِ الوحيد (غيابُ بندِ موعدِ التشغيلِ الحاسم) وحلُّه المقترح (الخيارُ الأوّل: إضافةُ بندِ العتبةِ ثمّ التوقيع). فأجابَ نصًّا: **"ok i accept your idea. do what u need"** (2026-07-23)، قابلًا صيغةَ القرارِ المعروضةَ معَ بندِ الموعد.

## ما جُمِّدَ بالتوقيع

النصُّ الآليُّ الحاكمُ `data/recovery-proof-preregistration.json` بحالتِه `AUTHOR-SIGNED` عندَ الالتزامِ الأمِّ `41c36dee1080c08da564473c3ac278a13a4f82ea`، بكلِّ حقولِه المعروضة: السكّانُ (الآراميّةُ والعبريّةُ بلقطتَيهما المبصومتَين)، ووحدةُ التحليلِ (الأسرة) ووحدةُ الحكمِ (العضو)، وعزلُ القروضِ والأعلام، وقاعدةُ المطابقةِ الدلاليّةِ بمصدرَينِ قديمَين، وقصرُ البسطِ على الجسورِ المعجميّةِ الداخليّة، ونموذجُ الصدفةِ (تبديلٌ بلا نقطةٍ ثابتةٍ يحفظُ الخصائصَ المسمّاة، 1000 تكرارٍ ببذرة 20260721)، وتعميةُ المروحة، وفترةُ 95% بعشرةِ آلافِ bootstrap عنقوديّ، والاختبارُ الساميُّ المجمعُ أوّليًّا وحيدًا معَ تصحيحِ Holm للتفريعات.

## بندُ الموعدِ المضافُ قبلَ التوقيعِ بقبولِ المؤلّف

**تشغيلٌ حاسمٌ واحدٌ لا يتكرّر**، يقعُ يومَ يبلغُ مقامُ الأسرِ المؤهّلةِ مكتملةِ المراجعةِ العتبةَ المعلنة: **600 أسرةً مجموعًا، منها 150 على الأقلِّ في كلِّ لغة**، معدودةً من السجلِّ الآليِّ `data/family-review-states.json` بعدٍّ قابلٍ للتدقيق. **لا تشغيلَ استطلاعيًّا قبلَها ولا بعدَها**، والرقمُ يُودَعُ يومَ خروجِه كما خرجَ، موجبًا أو سالبًا.

## هندسةُ الإنفاذِ: موقَّعةٌ مسلَّحةٌ لا مفتوحة

بوّابةُ التنفيذِ `require_execution_authority` صارت تفحصُ معَ التوقيعِ وجودَ ملفِّ الإشهادِ `05-audits/proof-run-trigger-attestation.md`، ولا يُكتَبُ هذا الملفُّ إلّا يومَ تتحقّقُ العتبةُ بعدٍّ مسجَّلٍ فيه. فالحالُ بعدَ التوقيع: `validate` يشهدُ VALID (AUTHOR-SIGNED)، و`execution-check` يبقى LOCKED برسالةِ التسليحِ حتى يومِ الإشهاد، وحارسُ CI يثبتُ ذلك في كلِّ تشغيل. بهذا يستحيلُ تشغيلٌ مبكّرٌ ولو سهوًا، وتسقطُ سلفًا تهمةُ «شغّلوه مرارًا حتى أعجبَهم الرقم».

## ما لا يأذنُ به هذا التوقيع

لا نشرَ لأيِّ نتيجةٍ (النشرُ قرارُ المؤلّفِ المستقلُّ يومَ الخروج)، ولا مساسَ بقراءاتِ جبل، ولا صفَّ جديدًا، ولا مصدرَ جديدًا، ولا تعديلَ لأيِّ بندٍ بعدَ فتحِ النتائج. والتوقيعُ كلُّه قابلٌ للنقضِ بكلمةٍ من المؤلّفِ ما دامَ التشغيلُ الحاسمُ لم يقع.

*English abstract:* On 2026-07-23 the author signed the Semitic proof-line preregistration by accepting the clause-by-clause presentation together with the third lens's single reservation and its remedy: a run-trigger clause added before signature. The machine text is frozen AUTHOR-SIGNED at parent commit 41c36de with its full design (Aramaic and Hebrew pinned populations, family analysis unit, member verdict unit, loan and proper-name exclusion, two-old-dictionary semantic rule, lexicon-internal primary numerator, fixed-point-free property-preserving derangement with 1000 iterations at seed 20260721, blinded fans, clustered bootstrap and permutation inference, pooled Semitic test as the sole primary with Holm-corrected secondaries). The added trigger: one single confirmatory run, ever, on the day the eligible fully-reviewed family denominator first reaches 600 total with at least 150 per language, counted auditably from the machine review record; no interim runs. Enforcement is armed-not-open: the execution gate now also requires a dated attestation file that can only exist once the threshold is met, so validate passes, execution-check stays locked, and CI proves it on every run. Publication remains a separate author decision; the signature is reversible by his word until the confirmatory run occurs.
