#!/usr/bin/env python3
"""Build the Sanskrit layer — a faithful structured mirror of the authored doc
`sanskrit-indo-iranian-echoes.md` (30 worked entries).

Each Sanskrit word is read through the 28 FIXED letter-charges; graded by whether the
gesture composes to its attested meaning. Where it does — landing on the same meaning the
same gesture builds in Arabic — the framework reads it as a surviving trace of one original
tongue ("the original Arabic") whose sound-meaning logic Qur'anic Arabic kept most intact.
NOT genetic-cognate grading, NOT a borrowing roster, NOT "convergence/coincidence/pareidolia".

Grades are the author's own per-entry verdicts from the doc: 11 PERFECT · 18 STRONG · 1 PARTIAL.
Fields: arabic / sanskrit / gloss / reading (the charge-composition) / verdict / note.
Sources: Monier-Williams Sanskrit-English Dictionary."""
import json, sys
from collections import Counter
sys.stdout.reconfigure(encoding='utf-8')
ROOT='C:/Users/yassi/AI Projects/The Arabic Tongue (nature-genome-application)/'

# [arabic, sanskrit, gloss, verdict, reading(charge-composition), note]
E=[
('زوج','yuga','pair, yoke, union','PERFECT',
 'ز/y sliding thrust + و binding loop + ج closed assembly = the yoking of two into one pair',''),
('ثلاث','trayas','three','STRONG',
 'ث dental boundary-release + ل lateral extension flowing outward = the threefold spreading (l↔r, ث↔t)',''),
('ستّ','ṣaṣ','six','STRONG',
 'س continuous sibilant friction closing on a د/ت dental stop = friction sealing the senary count',''),
('سبع','sapta','seven','STRONG',
 'س streaming flow + ب bilabial seal + ع pharyngeal release = completion of the septenary cycle',''),
('ناموس','namas','submission, obeisance, sacred law','PERFECT',
 'ن interior resonance + م gathered containment/humility + س smooth extension = bowing in reverent submission (n-m-s ↔ n-m-s, exact)',''),
('بعل','bala','strength, lord, master','STRONG',
 'ب firm anchor + ع pharyngeal force + ل bridging high = lord/master/strength (Sanskrit drops ʿ with vowel lengthening)',''),
('كرّ','kṛ','action, doing, repetition','PERFECT',
 'ك sharp decisive strike + ر rolling repetition = the act of doing / returning / repeating (k-r ↔ k-r)',''),
('مخّ','makha','head, chief, inner marrow','PERFECT',
 'م gathered mass inside + خ pierced/extracted = the inner essence — brain/marrow, the chief (m-ḫ ↔ m-kh)',''),
('لسان','las','shine, play, speak, tongue','STRONG',
 'ل tongue extending + س breath sliding = playing / shining / speaking (l-s ↔ l-s)',''),
('أخ','bhrātṛ','brother, companion','PARTIAL',
 'the companion issuing from the same originating anchor; Sanskrit keeps the bh-/r that pharyngealized to ʾ-ḫ in Arabic',''),
('صندل','candana','sandalwood','STRONG',
 'ص piercing fragrance + ن radiating scent + د hard wood + ل tall tree = the fragrant hardwood that radiates its essence',
 'travelled the trade routes as a Wanderwort, yet composes cleanly on the sibilant-nasal-dental class'),
('اسم','nāman','name','PARTIAL',
 'س spoken breath + م gathered, bound identity = breath gathered to designate a thing (n-m ↔ s-m)',''),
('أمّ','mātṛ','mother','STRONG',
 'م the lips gathering in nurturing containment = the maternal origin that gathers and nurtures life',''),
('أب','pitṛ','father','STRONG',
 'أ originating anchor + ب firm boundary/support = the provider, the father (p-t ↔ b-t)',''),
('سنّ','danta','tooth','STRONG',
 'س/د dental contact + ن continuous nasal resonance = the gnashing dental organ (s-n ↔ d-n-t)',''),
('نخس','nakha','to prod, prick (Arabic نَخَسَ); Skt nakha = nail, claw','STRONG',
 'ن directional point + خ piercing/scraping friction = the sharp nail/claw that pricks (n-ḫ ↔ n-kh)',''),
('بدّ','pāda','foot, step','STRONG',
 'ب firm anchor-seal + د flat settled stop = a foot stamped down (p-d ↔ b-d)',''),
('قرن','karṇa','ear / horn, corner','PERFECT',
 'ق curved hook + ر rolling projection + ن resonance cavity = the horn-like corner projection, the ear (k-r-ṇ ↔ q-r-n, exact)',''),
('نسم','nasa','nose / to breathe','STRONG',
 'ن nasal resonance + س air streaming = the breathing organ (n-s ↔ n-s)',''),
('بدا','vid','to know, find / to appear','STRONG',
 'ب/و releasing into visibility + د settled certainty = finding / knowing the manifest (v-d ↔ b-d)',''),
('ضوء','div','sky, shine / light','STRONG',
 'ض heavy pharyngeal intensity + و radiant field = bright light, shine (d-v ↔ ḍ-w)',''),
('أجّ','agni','fire / to blaze','STRONG',
 'ج ignition stop + ن rising resonance (heat/smoke) = blazing fire',''),
('طنّ','tan','to stretch, tension','PERFECT',
 'ت/ط pulling dental contact + ن continuous vibrating line = stretching to maximum tension (t-n ↔ ṭ-n)',''),
('رجل','rāj','king, ruler / leader','STRONG',
 'ر rolling authority + ج closed assembly = the ruler who directs the gathered tribe (r-j ↔ r-j)',''),
('منى','man','to think / to wish, measure in mind','PERFECT',
 'م deep internal concentration + ن rising resonance-thought = to measure in mind, to think, to wish (m-n ↔ m-n)',''),
('ثبت','sthā','to stand, remain firm','STRONG',
 'ث/س sibilant contact locked into a ت dental stop = absolute stability, standing firm (s-t ↔ th-t)',''),
('باء','bhū','to become, earth / habitat, return','PERFECT',
 'ب enclosing space/earth + و/ي dynamic state of being = existence, habitat, the earth (bh-u ↔ b-y/w)',''),
('أدّى','dā','to give / to pay, deliver','PERFECT',
 'د decisive outward thrust + ي smooth release to another = to give, to deliver (d-a ↔ d-y)',''),
('وسق','vah','to carry, lead / to load','STRONG',
 'و rounded gathering + ه/ح flowing release = gathering to transport onward, to carry / lead',''),
('مذق','madhu','honey, sweet / to mix sweet drink','PERFECT',
 'م gathered mass + ذ smooth trickling slide = sweet honey, mixed sweet liquid (m-dh ↔ m-dh)',''),
]
entries=[]
for i,(ar,sk,gl,v,rd,note) in enumerate(E, start=1):
    e={'id':i,'arabic':ar,'sanskrit':sk,'gloss':gl,'reading':rd,'verdict':v}
    if note: e['note']=note
    entries.append(e)
dist=Counter(e['verdict'] for e in entries)
top=dist['PERFECT']+dist['STRONG']
out={'project':'The Arabic Tongue · Sanskrit through the fixed charges · Arabic ↔ Sanskrit',
     'version':'2026-06-02-charge-read',
     'method':'Each Sanskrit word is read through the 28 FIXED letter-charges and graded by whether its gesture composes to its attested meaning — NOT by genetic-cognate status. Clean composition that lands on the same meaning the same gesture builds in Arabic is read, per the framework, as a surviving trace of one original tongue ("the original Arabic") whose sound-meaning logic Qur\'anic Arabic kept most intact.',
     'count':len(entries),
     'verdict_distribution':dict(dist.most_common()),
     'license':'CC-BY 4.0',
     'source_lexicon':'Monier-Williams Sanskrit-English Dictionary',
     'companion_doc':'04-cross-linguistic/sanskrit-indo-iranian-echoes.md',
     'note':'A structured mirror of the authored worked-entries doc. The deep core vocabulary — kin, body, number, basic action — composes cleanly through the fixed charges even on the most distant branch tested, which the framework reads as evidence of the one original tongue, not coincidence at distance.',
     'entries':entries}
json.dump(out,open(ROOT+'04-cross-linguistic/data/sanskrit-cognates.json','w',encoding='utf-8'),ensure_ascii=False,indent=2)
print('Sanskrit (charge-read, mirror of doc): %d entries' % len(entries))
print('Distribution:', dict(dist.most_common()))
print('Top-tier (PERFECT+STRONG): %d/%d = %d%%' % (top,len(entries),round(top/len(entries)*100)))
