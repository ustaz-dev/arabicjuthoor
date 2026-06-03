#!/usr/bin/env python3
"""Build the Arabic <-> Akkadian cognate dataset — the OLDEST attested Semitic sister.

Akkadian (East Semitic, attested from ~2500 BCE) is the earliest written sister of Arabic.
Like Hebrew/Aramaic it is the unity baseline, not a test of the framework — but pushed back
two millennia, which is why it matters to the common-origin reading: the regular shifts are
the signature of ONE tongue diverging, and the closeness to Arabic at this time-depth deepens
the trace of the original source.

Akkadian's signature correspondences vs Arabic (proto-Semitic):
  - LOSS OF THE GUTTURALS: ʾ ʿ ḥ h ġ → ø, usually coloring a neighbouring a → e
      (Arabic بَعل baʿl → Akk. bēlu ; عَين ʿayn → īnu ; أَرض ʾarḍ → erṣetu)
  - interdentals: ṯ → š,  ḏ → z,  ẓ → ṣ      (ثَلاث ṯalāṯ → šalāš ; أُذُن ʾuḏun → uznu)
  - emphatic: ḍ → ṣ                           (أَرض ʾarḍ → erṣetu)
  - sibilant: s → š                           (سَلام salām → šulmu ; اسم ism → šumu)
  - w- initial often weakens/drops; nouns carry mimation -u(m).
PERFECT = same root, no shift; STRONG = one+ regular Akkadian shift; PROTO-FAMILY = shared pronoun.
Sources: Chicago Assyrian Dictionary (CAD); von Soden, Akkadisches Handwörterbuch (AHw)."""
import json, sys
from collections import Counter
sys.stdout.reconfigure(encoding='utf-8')
ROOT='C:/Users/yassi/AI Projects/The Arabic Tongue (nature-genome-application)/'

# [arabic, akkadian (normalized transliteration), gloss, verdict, category]
E=[
# Body
('عَين','īnu','eye — ʿ lost, ay→ī','STRONG','body'),
('أُذُن','uznu','ear — ḏ→z','STRONG','body'),
('رَأس','rēšu','head — ʾ lost','STRONG','body'),
('لِسان','lišānu','tongue','PERFECT','body'),
('سِنّ','šinnu','tooth — s→š','STRONG','body'),
('دَم','damu','blood','PERFECT','body'),
('قَرن','qarnu','horn','PERFECT','body'),
('نَفس','napištu','life, soul, throat — s→š','STRONG','body'),
('كَبِد','kabattu','liver, inner self','PERFECT','body'),
('شَعر','šārtu','hair — ʿ lost, s→š','STRONG','body'),
('قَلب','libbu','heart — l-b core','STRONG','body'),
('عَظم','eṣemtu','bone — ʿ→e, ẓ→ṣ','STRONG','body'),
('يَد','idu','arm, hand, side — w/y weakened','STRONG','body'),
('دَمع','dimtu','tear — ʿ lost','STRONG','body'),
# Kinship
('أَب','abu','father','PERFECT','kin'),
('أُمّ','ummu','mother','PERFECT','kin'),
('أَخ','aḫu','brother','PERFECT','kin'),
('أُخت','aḫātu','sister','PERFECT','kin'),
('حَمّ','emu','father-in-law — ḥ lost, e-color','STRONG','kin'),
('أَرمَلة','almattu','widow','PERFECT','kin'),
('كَنّة','kallatu','bride, daughter-in-law','STRONG','kin'),
# Pronouns
('أَنا','anāku','I','PROTO-FAMILY','pronoun'),
('أَنتَ','atta','you (m.)','PROTO-FAMILY','pronoun'),
('أَنتِ','atti','you (f.)','PROTO-FAMILY','pronoun'),
('مَن','mannu','who','PERFECT','pronoun'),
('ما','mīnu','what','STRONG','pronoun'),
# Nature
('ماء','mû','water','STRONG','nature'),
('سَماء','šamû','sky, heaven — s→š','STRONG','nature'),
('أَرض','erṣetu','earth — ʾ→e, ḍ→ṣ (the classic shift)','STRONG','nature'),
('شَمس','šamšu','sun','PERFECT','nature'),
('نور','nūru','light','PERFECT','nature'),
('يَوم','ūmu','day — w lost','STRONG','time'),
('لَيل','līliātu','evening, night','STRONG','time'),
('كَوكَب','kakkabu','star','PERFECT','nature'),
('نَهر','nāru','river','PERFECT','nature'),
('ثَور','šūru','bull, ox — ṯ→š','STRONG','nature'),
('كَلب','kalbu','dog','PERFECT','nature'),
('حِمار','imēru','donkey — ḥ lost','STRONG','nature'),
('حَقل','eqlu','field — ḥ→e','STRONG','nature'),
('بَيت','bītu','house','PERFECT','nature'),
('باب','bābu','gate, door','PERFECT','nature'),
# Numbers (the regular shifts shine here)
('أَحَد','ēdu','one, single — ḥ lost','STRONG','num'),
('اثنان','šina','two — ṯ→š','STRONG','num'),
('ثَلاث','šalāš','three — ṯ→š (the classic shift)','STRONG','num'),
('أَربَع','erbe','four','STRONG','num'),
('خَمس','ḫamšu','five — s→š','STRONG','num'),
('سِتّ','šeššu','six — s→š','STRONG','num'),
('سَبع','sebe','seven — ʿ lost','STRONG','num'),
('ثَمان','samānû','eight — ṯ→s','STRONG','num'),
('تِسع','tiše','nine — ʿ lost','STRONG','num'),
('عَشر','ešer','ten — ʿ→e','STRONG','num'),
('مِئة','meʾtu','hundred','STRONG','num'),
# Verbs & abstract
('سَمِع','šemû','to hear — s→š, ʿ lost','STRONG','mind'),
('أَكَل','akālu','to eat','PERFECT','action'),
('ماتَ','mâtu','to die','PERFECT','action'),
('بَنى','banû','to build, create','PERFECT','action'),
('وَلَد','(w)alādu','to give birth','STRONG','kin'),
('دانَ','dânu','to judge — dīnu = judgment','PERFECT','abstract'),
('قَرُب','qarābu','to approach, draw near','PERFECT','motion'),
('سَكَن','šakānu','to set, place, dwell — s→š','STRONG','motion'),
('نَظَر/نَصَر','naṣāru','to guard, protect — ẓ→ṣ','STRONG','action'),
('لَبِس','labāšu','to clothe — s→š','STRONG','action'),
('سَطَر','šaṭāru','to write, inscribe — s→š','STRONG','abstract'),
('مَلَك','malāku','to rule, counsel — malku = prince','STRONG','abstract'),
('رَبّ','rabû','great; to be great','PERFECT','abstract'),
('بَعل','bēlu','lord, owner — ʿ lost, a→ē','STRONG','abstract'),
('إِله','ilu','god','PERFECT','abstract'),
('اسم','šumu','name — s→š','STRONG','abstract'),
('سَلام','šulmu','peace, well-being — s→š','STRONG','abstract'),
('سَنة','šattu','year — s→š','STRONG','time'),
# Honest parallel stems — Akkadian uses a different root for the concept (not forced into a cognate)
('ابن','māru','son (parallel stem — Akk uses māru, not b-n)','PROVISIONAL','kin'),
('مَلِك','šarru','king (parallel — the usual Akk title; cf. malku ↔ مَلَك above)','PROVISIONAL','abstract'),
('بَحر/يَمّ','tâmtu','sea (parallel stem)','PROVISIONAL','nature'),
('جَبَل','šadû','mountain (parallel stem)','PROVISIONAL','nature'),
('نار','išātu','fire (parallel — Arabic نار ↔ Akk nūru means "light")','PROVISIONAL','nature'),
]
entries=[]
for i,(ar,ak,gl,v,cat) in enumerate(E, start=1):
    entries.append({'id':i,'arabic':ar,'akkadian':ak,'gloss':gl,'verdict':v,'category':cat})
dist=Counter(e['verdict'] for e in entries)
top=dist['PERFECT']+dist['PROTO-FAMILY']+dist['STRONG']
out={'project':'The Arabic Tongue · Semitic-sister cognates · Arabic ↔ Akkadian (oldest attested Semitic)',
     'version':'2026-06-03','count':len(entries),
     'verdict_distribution':dict(dist.most_common()),
     'license':'CC-BY 4.0',
     'source_lexicon':'Chicago Assyrian Dictionary (CAD); von Soden, Akkadisches Handwörterbuch (AHw)',
     'note':'The oldest attested Semitic (East Semitic, ~2500 BCE) — the earliest written sister of Arabic, the unity baseline pushed back two millennia. Signature: loss of the gutturals (ʾ ʿ ḥ h ġ → ø, a→e) + interdental/emphatic shifts (ṯ→š, ḏ→z, ẓ/ḍ→ṣ) + s→š. The regularity of these shifts is the signature of one tongue diverging; the closeness at this time-depth deepens the trace of the one original source.',
     'entries':entries}
json.dump(out,open(ROOT+'04-cross-linguistic/data/akkadian-cognates.json','w',encoding='utf-8'),ensure_ascii=False,indent=2)
print('Akkadian dataset: %d entries' % len(entries))
print('Distribution:', dict(dist.most_common()))
print('Top-tier (PERFECT+STRONG+PROTO-FAMILY): %d/%d = %d%%' % (top,len(entries),round(top/len(entries)*100)))
