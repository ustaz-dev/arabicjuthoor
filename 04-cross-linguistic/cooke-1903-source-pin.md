# ورقةُ تثبيتِ مصدرٍ: Cooke 1903، نصُّ نقوشِ شمالِ الساميّة (2026-07-24)

**السند:** وجّهَ المؤلّفُ نصًّا في 2026-07-24: الكتابُ موجودٌ عندنا PDF في `Data raw`، ويُفرَّغُ ليصيرَ مقروءًا. والكتابُ عامُّ الملكيّةِ بيقين (نُشِرَ 1903 عن Oxford Clarendon، وقد تحقّقَ من ملكيّتِه العامّةِ في ورقةِ مصادرِ 2026-07-24).

**الهُويّة:** George Albert Cooke, *A Text-book of North-Semitic Inscriptions: Moabite, Hebrew, Phoenician, Aramaic, Nabataean, Palmyrene, Jewish*, Oxford: Clarendon Press, 1903.

## ما جُمِعَ فعلًا (كلُّه مجّانيٌّ وعامُّ الملكيّة)

| المادّة | المصدر | الحجم | الحالة |
|---|---|---|---|
| النسخةُ المحليّةُ الأصل | `Data raw/Cooke 1903.pdf` | 11.9 ميغا، 472 صفحة | مصدرٌ مثبَّت |
| طبقةُ النصِّ المدمجةُ المستخرَجة | استخراجٌ محليٌّ من الـPDF | 233 صفحةً، 792,170 حرفًا | مستخرَجةٌ في `Data raw/cooke1903_text/` |
| النصُّ الكاملُ، نسخةُ تورونتو | أرشيفُ الإنترنت `textbookofnorths00cookuoft` | 971,619 حرفًا | كاملُ الكتاب |
| النصُّ الكاملُ، نسخةُ كورنيل | أرشيفُ الإنترنت `cu31924096083104` | 853,208 حرفًا | شاهدٌ ثانٍ مستقلّ |
| النصُّ الكاملُ، نسخةُ Google | أرشيفُ الإنترنت `atextbooknorths00cookgoog` | 846,795 حرفًا | شاهدٌ ثالثٌ مستقلّ |

**فائدةُ الشواهدِ الثلاثةِ المستقلّة:** ثلاثُ عمليّاتِ تفريغٍ مختلفةٍ للكتابِ نفسِه تعملُ شواهدَ متقاطعةً على مواضعِ الخطأ: ما اتّفقَت عليه الثلاثةُ أوثقُ ممّا انفردَ به واحد. وهذا يوافقُ منهجَ المشروعِ في تعدُّدِ الشهود.

## القيدُ الحاسمُ المكتشَفُ بالفحص

**الشرحُ الإنجليزيُّ صالحٌ، والنصُّ الساميُّ خردةٌ في التفريغاتِ الثلاثةِ كلِّها.**

ما نجحَ: العناوينُ والمواضعُ وأرقامُ النقوشِ وإحالاتُ CIS (184 إحالة) والتواريخُ والمتاحفُ والترجماتُ الإنجليزيّةُ والشرحُ اللغويُّ كلُّه، ومعه النقحراتُ اللاتينيّةُ الواردةُ داخلَ الشرح.

ما فشل: النقوشُ نفسُها، وقد طبعَها Cooke بالحرفِ العبريِّ المربَّع، فخرجت من تفريغِ 1903 حروفًا مبعثرة. الشاهدُ الحيُّ من نقشِ جبيل (رقم 3): خرجَ نصُّه «K p p yiTirr p \*ni S:u h n:&&&» وهو خردةٌ لا تُقرأ. ولوحاتُ جداولِ الأبجديّاتِ في آخرِ الكتابِ خرجت خردةً كذلك بطبيعتِها (صورُ خطوطٍ لا نصّ).

**فقُلْ في هذه المادّةِ ما هو حقٌّ:** هي **جهازُ Cooke الإنجليزيُّ كاملًا**، لا نصوصُ النقوشِ السامية. وهي بهذا مادّةُ معنًى وإسنادٍ ممتازة (تعطي لكلِّ نقشٍ معناه ومكانَه وتاريخَه ورقمَه في CIS)، وليست مادّةَ صورةٍ كتابيّةٍ للكلماتِ الفينيقيّة.

## ما بقيَ ليكتملَ الكتاب

قراءةُ الخطِّ الساميِّ المطبوعِ سنةَ 1903 تحتاجُ تفريغًا حديثًا بنماذجَ بصريّةٍ تقرأُ العبريّةَ المربّعة. الأداةُ جاهزةٌ في `scripts/ocr_cooke1903_mistral.py`، وفيها وضعُ عيّنةٍ رخيصةٍ (`--sample`) يُجرَّبُ قبلَ الكتابِ كلِّه (`--all`)، وتقيسُ بنفسِها كم حرفًا عبريًّا استُرِدَّ فعلًا فلا يُدفَعُ ثمنُ تفريغٍ كاملٍ قبلَ إثباتِ جدواه. تنتظرُ الأداةُ مفتاحَ خدمةٍ يضعُه المؤلّفُ بنفسِه في متغيّرِ بيئةٍ أو في `Data raw/.mistral_key` (خارجَ git، ولا يُودَعُ أبدًا).

## قاعدةُ الاستعمالِ في البطاقات

المادّةُ الإنجليزيّةُ من Cooke تُستعمَلُ **إسنادَ معنًى ومكانٍ وتاريخٍ ورقمِ نقشٍ**، وتُسمّى في البطاقةِ باسمِها ورقمِ النقش. ولا يُبنى على تفريغِ الأرشيفِ أيُّ صورةٍ كتابيّةٍ فينيقيّةٍ حتى يتمَّ التفريغُ الحديثُ للخطّ، فالصورةُ الكتابيّةُ تُؤخَذُ حتى ذلك الحينِ من لقطاتِنا المثبَّتةِ وحدَها.

*English abstract:* Source pin for Cooke 1903, public domain by age, held locally as a 472-page PDF and now supplemented by three independent Internet Archive full-text renderings (Toronto, Cornell, Google) plus the 233-page text layer embedded in our own copy. Verified limitation: all three legacy OCR renderings recover Cooke's English apparatus in full (headings, provenances, dates, museums, 184 CIS references, translations, philological commentary, Latin-script transliterations inside the commentary) but reduce the Hebrew-square Semitic inscription text to noise, as the Byblos inscription sample shows. The material is therefore excellent evidence for meaning, provenance and inscription identity, and is not a source of Phoenician graphic forms. A modern OCR pass is prepared in scripts/ocr_cooke1903_mistral.py with a cheap sample mode that measures actual Hebrew-character recovery before any full run; it waits on a key the author places himself outside git.

## نتيجةُ التفريغِ الحديثِ بالدفعات (نُفِّذَ 2026-07-24)

نُفِّذَ التفريغُ بواجهةِ الدفعاتِ كما أمرَ المؤلّف (قاعدةٌ نافذةٌ من اليوم: كلُّ عملِ Mistral يمرُّ بالدفعاتِ لا بالنداءِ المفرد). الكتابُ كلُّه في وظيفةٍ واحدةٍ من 24 طلبًا بعشرين صفحةً لكلِّ طلب، ونجحَت الأربعةُ والعشرونَ كلُّها بلا فشلٍ واحد.

| المقياس | القيمة |
|---|---|
| الصفحاتُ المفرَّغة | 472 من 472 |
| الحروفُ المستخرَجة | 5,368,067 |
| الحروفُ الساميّةُ المستردَّة | 99,638 (والتفريغُ القديمُ يعطي صفرًا صالحًا) |
| بعدَ تجريدِ التشكيلِ المضاف | 77,903 حرفًا صامتيًّا |
| الأداة | `scripts/ocr_cooke1903_mistral.py` ثمّ `scripts/clean_cooke1903_ocr.py` |

### الشاهدُ الحاسم: نقشُ جبيلٍ الذي عجزَ عنه التفريغُ القديم

كانَ يخرجُ من الأرشيف: «K p p yiTirr p \*ni S:u h n:&&&». وصارَ يخرجُ الآن نصًّا مقروءًا مطابقًا لترجمتِه في الصفحةِ نفسِها، وهو نقشُ يحومَلك ملكِ جبيل:

> אני יחומלך מלך גבל בן יהרבע בן בן ארמלך מלך גבל אש פעלתו הרבת בעלת גבל ממלכת על גבל וקרא אנך את רבתי בעלת גבל [כי שמע] קל ופעל... המזבח נחשת זן

ويقابلُه في الكتابِ نفسِه: "I am Yehaw-milk, king of Gebal, son of Yehar-ba'al, grand-son of Uri-milk... and I invoke my lady, mistress of Gebal, [for she hears] my voice... this altar of bronze".

فصارَت بينَ أيدينا **الصورةُ الكتابيّةُ والمعنى المنشورُ معًا في مكانٍ واحد**، وهو ما لم تكن تعطيه لقطةُ kaikki ولا التفريغُ القديم.

### عيبانِ مقيسانِ قُيِّدا قبلَ أيِّ استعمال

1. **تشكيلٌ من عندِ النموذجِ لا من الكتاب.** Cooke يطبعُ النقوشَ بالخطِّ المربَّعِ غيرِ المشكول، لأنّ الكتابةَ الفينيقيّةَ صامتيّةٌ لا تحملُ حركات. وقد أعادَ التفريغُ نصًّا مشكولًا كاملًا في 115 صفحة، فالحركاتُ **مضافةٌ من النموذجِ لا مثبتةٌ في المصدر**. جُرِّدَت كلُّها، ولا يُبنى على حركةٍ منها حكمٌ أبدًا؛ والمعتمدُ الهيكلُ الصامتيُّ وحدَه، وهو أصلًا وحدةُ المقارنةِ عندنا.
2. **دوراتُ تكرار.** في صفحاتِ الشرحِ الكثيفةِ ينحبسُ النموذجُ أحيانًا على لفظٍ قصيرٍ فيكرّرُه عشرات المرّات. رُصِدَ ذلك في 19 صفحةً من 472، ووُسِمَت كلُّها `FLAGGED` في النصِّ المنقّى بنسبةِ تكرارِها واللفظِ المتكرّر. **لا يُستشهَدُ بصفحةٍ موسومةٍ إلّا بعدَ مقابلتِها على صورةِ الصفحةِ في الـPDF.**

### قاعدةُ الاستعمالِ النافذة

الملفُّ المعتمَدُ للاستشهادِ هو `cooke1903_clean.md` (المنقَّى) لا الخام. وكلُّ بطاقةٍ تستشهدُ به تسمّي رقمَ النقشِ ورقمَ الصفحة، وتأخذُ الصورةَ الكتابيّةَ من الهيكلِ الصامتيِّ المجرَّد، والمعنى من ترجمةِ Cooke أو شرحِه، وتتحقّقُ من وسمِ `FLAGGED` قبلَ الاعتماد. وتبقى لقطاتُنا المثبَّتةُ شاهدًا موازيًا حيثُ وُجِدَ الزوجُ في الجهتَين.

*English abstract (execution note):* The full book was OCR'd through the Mistral Batch API per the author's standing instruction that all Mistral work go through batches, as one job of 24 twenty-page requests, all 24 succeeding. Recovery: 472 of 472 pages, 5.37 million characters, 99,638 Semitic characters where the legacy OCR yielded none usable, reduced to 77,903 consonantal characters after stripping model-supplied pointing. The decisive proof is the Yehawmilk of Byblos inscription, previously pure noise, now readable and matching its own facing translation. Two measured defects are recorded and handled: the model supplies vocalisation absent from Cooke's consonantal print (115 pages, stripped, never citable), and it enters repetition loops on dense commentary (19 of 472 pages, each marked FLAGGED with its ratio and looped token, never citable without checking the page image). Cards cite the cleaned file only, naming inscription and page.
