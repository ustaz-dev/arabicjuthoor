#!/usr/bin/env python3
"""Build the Arabic <-> Aramaic cognate dataset (the second Semitic sibling).
These complete the sibling trio. They are NOT a test of the framework — they are
the unity baseline: Aramaic and Arabic are the same Semitic tongue split by regular
rule. The famous regular shifts are themselves the proof of that one-tongue divergence:
  Proto-Semitic ḍ → Aramaic ʿ   (Arabic أرض arḍ → Aramaic ארעא arʿā)
  Proto-Semitic ṯ → Aramaic t   (Arabic ثلاث ṯalāṯ → Aramaic תלת tlāt)
  Proto-Semitic ḏ → Aramaic d   (Arabic ذهب ḏahab → Aramaic דהב dahab)
  Proto-Semitic ẓ → Aramaic ʿ/ṭ
PERFECT = same root, no shift; STRONG = one regular Aramaic shift."""
import json, sys
from collections import Counter
sys.stdout.reconfigure(encoding='utf-8')
ROOT='C:/Users/yassi/AI Projects/The Arabic Tongue (nature-genome-application)/'

# [arabic, aramaic (Syriac/Imperial), gloss, verdict, category]
E=[
# Body
('عَين','עֵינָא ʿaynā','eye','PERFECT','body'),
('أُذُن','אֵדְנָא ʾednā','ear','PERFECT','body'),
('يَد','יְדָא yedā','hand','PERFECT','body'),
('رِجل','רֵגְלָא reglā','foot, leg','PERFECT','body'),
('قَلب','לִבָּא libbā','heart — l-b core','STRONG','body'),
('رَأس','רֵישָׁא rēšā','head','PERFECT','body'),
('كَرِش/بَطن','כַּרְסָא karsā','belly','PERFECT','body'),
('لِسان','לִשָּׁנָא liššānā','tongue','PERFECT','body'),
('سِنّ','שִׁנָּא šinnā','tooth — س↔š','STRONG','body'),
('شَعر','סַעְרָא saʿrā','hair — ش↔s','STRONG','body'),
('دَم','דְּמָא demā','blood','PERFECT','body'),
('قَرن','קַרְנָא qarnā','horn','PERFECT','body'),
('عَظم','גַּרְמָא garmā','bone (parallel)','PROVISIONAL','body'),
('نَفس','נַפְשָׁא nafšā','soul, self — س↔š','STRONG','body'),
('روح','רוּחָא rūḥā','spirit, wind','PERFECT','body'),
('إِصبَع','אֶצְבְּעָא ʾeṣbeʿā','finger','PERFECT','body'),
('كَبِد','כַּבְדָּא kavdā','liver','PERFECT','body'),
# Kinship
('أَب','אַבָּא ʾabbā','father','PERFECT','kin'),
('أُمّ','אִמָּא ʾemmā','mother','PERFECT','kin'),
('ابن/بَر','בְּרָא berā / בַּר bar','son (Aram. uses bar)','STRONG','kin'),
('بِنت/بَرت','בְּרַתָּא berattā','daughter','STRONG','kin'),
('أَخ','אַחָא ʾaḥā','brother','PERFECT','kin'),
('أُخت','חָתָא ḥātā','sister','PERFECT','kin'),
('حَمّ','חְמָא ḥemā','father-in-law','PERFECT','kin'),
('أَنا','אֲנָא ʾanā','I','PROTO-FAMILY','pronoun'),
('أَنتَ','אַנְתְּ ʾant','you (m.)','PROTO-FAMILY','pronoun'),
('نَحنُ','אֲנַחְנָא ʾanaḥnā','we','PROTO-FAMILY','pronoun'),
('مَن','מַן man','who','PERFECT','pronoun'),
('ما/مَه','מָה mā','what','PERFECT','pronoun'),
('مِن','מִן min','from','PROTO-FAMILY','prep'),
('عَلى','עַל ʿal','on, upon','PERFECT','prep'),
('تَحت','תְּחוֹת teḥōt','under','PERFECT','prep'),
('بَين','בֵּינַי bēnay','between','PERFECT','prep'),
('كُلّ','כֹּל kol','all, every','PERFECT','prep'),
# Nature
('ماء','מַיָּא mayyā','water','PERFECT','nature'),
('نَهر','נַהְרָא nahrā','river','PERFECT','nature'),
('يَمّ','יַמָּא yammā','sea','PERFECT','nature'),
('سَماء','שְׁמַיָּא šemayyā','sky, heaven — س↔š','STRONG','nature'),
('أَرض','אַרְעָא ʾarʿā','earth — ض→ʿ (the classic Aramaic shift)','STRONG','nature'),
('شَمس','שִׁמְשָׁא šimšā','sun — ش↔š','STRONG','nature'),
('نار','נוּרָא nūrā','fire','PERFECT','nature'),
('لَيل','לֵילְיָא lēlyā','night','PERFECT','time'),
('يَوم','יוֹמָא yōmā','day','PERFECT','time'),
('كَوكَب','כּוֹכְבָא kōkhvā','star','PERFECT','nature'),
('حَجَر','כֵּאפָא kēʾfā','stone (parallel)','PROVISIONAL','nature'),
('جَبَل/طور','טוּרָא ṭūrā','mountain — ط↔ṭ','STRONG','nature'),
('زَيت','זַיְתָא zaytā','olive, oil','PERFECT','nature'),
('عِنَب','עִנְבָא ʿinbā','grape','PERFECT','nature'),
('خَمر','חַמְרָא ḥamrā','wine — خ↔ḥ','STRONG','nature'),
('لَحم','לַחְמָא laḥmā','bread/meat','PERFECT','nature'),
('مِلح','מִלְחָא milḥā','salt','PERFECT','nature'),
('ذَهَب','דַּהְבָא dahbā','gold — ذ→d (the classic shift)','STRONG','nature'),
('قَمح','חִטְּתָא? קַמְחָא qamḥā','flour, grain','PERFECT','nature'),
# Numbers (the regular shifts shine here)
('واحِد/حَد','חַד ḥad','one','PERFECT','num'),
('اثنان/تَرَين','תְּרֵין terēn','two','STRONG','num'),
('ثَلاث','תְּלָת telāt','three — ث→t (the classic shift)','STRONG','num'),
('أَربَع','אַרְבְּעָא ʾarbeʿā','four','PERFECT','num'),
('خَمس','חַמְשָׁא ḥamšā','five — خ↔ḥ','STRONG','num'),
('سِتّ','שִׁתָּא šittā','six — س↔š','STRONG','num'),
('سَبع','שַׁבְעָא šabʿā','seven — س↔š','STRONG','num'),
('ثَمان','תְּמָנְיָא temānyā','eight — ث→t','STRONG','num'),
('تِسع','תִּשְׁעָא tišʿā','nine','PERFECT','num'),
('عَشر','עַשְׂרָא ʿaśrā','ten','PERFECT','num'),
('مِئة','מְאָה meʾā','hundred','PERFECT','num'),
('أَلف','אַלְפָא ʾalpā','thousand','PERFECT','num'),
# Verbs
('كَتَب','כְּתַב ketav','to write','PERFECT','action'),
('قَرَأ','קְרָא qerā','to read, call','PERFECT','action'),
('سَمِع','שְׁמַע šemaʿ','to hear — س↔š','STRONG','mind'),
('عَلِم/يَدَع','יְדַע yedaʿ','to know (parallel)','PROVISIONAL','mind'),
('ذَكَر','דְּכַר dekhar','to remember — ذ→d','STRONG','mind'),
('أَكَل','אֲכַל ʾakhal','to eat','PERFECT','action'),
('ماتَ','מִית mīt','to die','PERFECT','kin'),
('قَتَل','קְטַל qeṭal','to kill','PERFECT','action'),
('وَلَد/يَلَد','יְלַד yelad','to give birth — و↔י','STRONG','kin'),
('بَنى','בְּנָא benā','to build','PERFECT','action'),
('عَبَد','עֲבַד ʿavad','to do, make, serve','PERFECT','action'),
('سَكَن/شَكَن','שְׁכֵן šekhēn','to dwell — س↔š','STRONG','motion'),
('قامَ','קָם qām','to rise, stand','PERFECT','motion'),
('نَزَل/نَحَت','נְחֵת neḥēt','to descend','PERFECT','motion'),
('سَجَد','סְגֵד seged','to prostrate, worship','PERFECT','abstract'),
('صَلّى','צְלִי ṣelī','to pray — ص↔ṣ','STRONG','abstract'),
('قُربان','קוּרְבָּנָא qurbānā','offering, sacrifice','PERFECT','abstract'),
('قُدُس','קַדִּישָׁא qaddišā','holy — س↔š','STRONG','abstract'),
('سَلام','שְׁלָמָא šelāmā','peace — س↔š','STRONG','abstract'),
('مَلِك','מַלְכָּא malkā','king','PERFECT','abstract'),
('رَبّ','רַבָּא rabbā','lord, master, great','PERFECT','abstract'),
('كاهِن','כָּהֲנָא kāhanā','priest','PERFECT','abstract'),
('نَبيّ','נְבִיָּא neviyyā','prophet','PERFECT','abstract'),
('سِفر/سَفَر','סִפְרָא siprā','book, scribe','PERFECT','abstract'),
('بَيت','בַּיְתָא baytā','house','PERFECT','abstract'),
('باب','בָּבָא bābā','gate, door','PERFECT','abstract'),
('بِئر','בֵּירָא bērā','well, pit','PERFECT','nature'),
('اسم','שְׁמָא šemā','name — س↔š','STRONG','abstract'),
('سَنة','שַׁתָּא šattā','year (š-t)','STRONG','time'),
('دَبَّر/دَبَر','דַּבַּר dabbar','to lead, speak, word','PERFECT','abstract'),
('حَيّ','חַי ḥay','alive','PERFECT','abstract'),
]
entries=[]
for i,(ar,ar2,gl,v,cat) in enumerate(E, start=1):
    entries.append({'id':i,'arabic':ar,'aramaic':ar2,'gloss':gl,'verdict':v,'category':cat})
dist=Counter(e['verdict'] for e in entries)
out={'project':'The Arabic Tongue · Tier-A Semitic-sister cognates · Arabic ↔ Aramaic',
     'version':'2026-05-24','count':len(entries),
     'verdict_distribution':dict(dist.most_common()),
     'license':'CC-BY 4.0',
     'note':'The unity baseline, not a test. Aramaic and Arabic are one Semitic tongue split by regular rule. Famous shifts: ḍ→ʿ (أرض→ארעא), ṯ→t (ثلاث→תלת), ḏ→d (ذهب→דהב), س↔š.',
     'entries':entries}
json.dump(out,open(ROOT+'04-cross-linguistic/data/aramaic-cognates.json','w',encoding='utf-8'),ensure_ascii=False,indent=2)
top=dist['PERFECT']+dist['PROTO-FAMILY']+dist['STRONG']
print('Aramaic dataset: %d entries' % len(entries))
print('Distribution:', dict(dist.most_common()))
print('Top-tier: %d/%d = %d%%' % (top,len(entries),round(top/len(entries)*100)))
