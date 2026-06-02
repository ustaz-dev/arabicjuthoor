#!/usr/bin/env python3
"""Build the Coptic restoration layer: Arabic <-> Hieroglyphic Egyptian <-> Coptic.
Coptic is the SPOKEN third witness: it restores consonants the consonantal hieroglyphic
script dropped (the flagship: لسان l-s-n ↔ hieroglyphic ns ↔ Coptic ⲗⲁⲥ las — the ل reappears).
Most entries here are restorations of already-confirmed Egyptian cognates, so the Coptic
ADDS evidence rather than making new claims. Graded honestly with the full rubric.
Fields: arabic / egyptian_hieroglyphic (with * = reconstructed) / coptic_lemma / gloss / reading / verdict."""
import json, sys
from collections import Counter
sys.stdout.reconfigure(encoding='utf-8')
ROOT='C:/Users/yassi/AI Projects/The Arabic Tongue (nature-genome-application)/'

# [arabic, egyptian, coptic, gloss, reading(gesture), verdict]
E=[
('لِسان','ns','ⲗⲁⲥ (las)','tongue','س-ن fine-stream + inner-resonance = the tongue; Coptic restores the ل dropped in hieroglyphic ns — metathesis closed','STRONG'),
('نَفَس / نَفْس','nfsw','ⲛⲓϥⲉ (nife)','soul, breath, self','ن-ف-س inner-resonance + parting + flow = breath-as-soul; Coptic nife "to breathe" is near-identical','PERFECT'),
('ماء','mw','ⲙⲱⲟⲩ (mōou)','water','م-gathered mass + و-binding flow = the held-yet-flowing substance','PERFECT'),
('مات','mwt','ⲙⲟⲩ (mou)','to die','م-gather + و-bind + ت-completion = the final gathering-and-sealing','STRONG'),
('يَمّ','ym','ⲓⲟⲙ (iom)','sea, current','ي-extension binding the م-gathered mass = the sea','STRONG'),
('طِين / طُوب','*ḏbt','ⲧⲱⲱⲃⲉ (tōōbe)','brick, mud, clay','ط-heavy spreading + b = the pressed clay/brick; طوب↔ⲧⲱⲱⲃⲉ is an attested loan into Arabic','STRONG'),
('واسِع','wsḫ','ⲟⲩⲱϣ (ouōš)','wide, spread','و+س-خ bound extension piercing outward to width; same root as واسخ (dual-face)','STRONG'),
('نَفيس','nfr','ⲛⲟⲩϥⲉ (noufe)','good, fine, precious','ن-ف-ر inner-resonance parting-through and flowing = the radiant-fine','STRONG'),
('قاع','*qꜣḥ','ⲕⲁϩ (kah)','earth, soil, ground','ق-firm + ʿ-depth = the firm settled ground/bottom','STRONG'),
('حَيّة','ḥfꜣw','ϩⲱϥ (hōf)','serpent, snake','f-ʿ Afroasiatic serpent-root; the gliding-cover gesture','STRONG'),
('بانَ','wbn','ⲟⲩⲱⲃⲛ (ouōbn)','to shine, appear, rise','ب-n what was sealed-inside released into outward resonance = emerging-into-light','STRONG'),
('جِسر','jsr','ϫⲟⲥⲣ (čosr)','bridge, crossing, clear path','ج-gather + س-flow + ر-run = the gathered crossing that runs across','STRONG'),
('جاءَ','jw / ii','ⲉⲓ (ei)','to come, arrive','ج-gathered-surfacing + ي-gentle extension forward = arrival','STRONG'),
('هَوى','*hꜣy','ϩⲉ (he)','to fall, descend','ه-soft breath + descent = the gentle falling-down','STRONG'),
('حَكَمَ / حِكمة','ḥkꜣ','ϩⲓⲕ (hik)','rule, wisdom, magic','ح-warm-containment + ك-sealed-precision = wisdom held secret','STRONG'),
('حَطّ','ḥtp','ϩⲱⲧⲡ (hōtp)','rest, settle, offering','ح-containment + ط-heavy spreading = settling-down-into-rest','STRONG'),
('شَمّ','sn','ⲥⲱⲛ (sōn)','to smell, scent, kiss','ش-front-spread + ن-nasal gathering = the smelling gesture','STRONG'),
('سَمير','smr','ⲥⲙⲟⲩⲣ (smour)','companion, friend','س-م-ر streaming-gathering that runs together = the late-talking companion','STRONG'),
('شَنّ','šn','ϣⲱⲛⲉ (šōne)','to encircle, loop, net','ش-wide spread + ن-inner resonance = the encircling enclosure','STRONG'),
('ثاني / اثنان','snw','ⲥⲛⲁⲩ (snau)','two, second','س-ن the matched-pair-by-shared-fine-source nucleus','STRONG'),
('أَنف','fnḏ','ϥⲁⲛϣ (fanš)','nose, snout','ن-ف inner-resonance + parting-the-breath = the organ where breath parts (metathesis ʾnf↔fnḏ)','STRONG'),
('شَبَّ','ḫpr','ϣⲱⲡⲉ (šōpe)','to become, grow, come into being','ḫ/š + p the coming-into-being; same root as ḫpr "become"','STRONG'),
('مَرَّخَ','mrḥt','ⲙⲣⲉϩⲏⲧ (mrehēt)','ointment, grease, oil','م-ر-ح the passing-running grease; smeared/anointing','STRONG'),
('مَوضِع / ما','ma','ⲙⲁ (ma)','place, location','م-binding relational place-marker','STRONG'),
('جَمَّ','gmj','ϭⲓⲛⲉ (čine)','to find, gather','ج/g-gathering-surfacing = coming-upon/gathering (Coptic g→č palatalization)','PARTIAL'),
('شَرِبَ','swr','ⲥⲱ (sō)','to drink','ش/s-extending-flow running inward = the drinking-in of liquid','STRONG'),
('سَمن','*smj','ⲥⲙⲟⲩ (smou)','butter, fat, cream','س-م streaming-gather = the fatty gathered cream','PARTIAL'),
('حَلْق','*ḥlq','ϩⲗⲁⲕ (hlak)','ring, circle, throat','ح-containment + ل-bridge + q = the encircling throat-ring','PARTIAL'),
('عُروة','r','ⲣⲱ (rō)','mouth, opening, loop','ر/rō the opening/loop — the opened ring','PARTIAL'),
('فَلَقَ','*wp','ⲡⲱⲣϫ (pōrč)','to split, cleave, open','ف-parting + ل-q = the splitting-open (Coptic pōrč "divide")','PARTIAL'),
('خَلَقَ','ḫpr','ϣⲱⲡⲉ (šōpe)','to become, create, shape','the creating/forming sense of ḫpr; overlaps شبّ (same Coptic šōpe)','PARTIAL'),
('حَلَبَ','*ḥrb','ⲉⲣⲱⲧⲉ (erōte)','to milk, yield liquid','ح-l-b the milking; drawing the liquid out','PARTIAL'),
('بَيت','pr','ⲡⲏⲓ (pēi)','house','pr "house" → Coptic pēi; Arabic بيت is a parallel dwelling-stem','PROVISIONAL'),
]
entries=[]
for i,(ar,eg,cop,gl,rd,v) in enumerate(E, start=1):
    entries.append({'id':i,'arabic':ar,'egyptian_hieroglyphic':eg,'coptic_lemma':cop,
                    'gloss':gl,'reading':rd,'verdict':v})
dist=Counter(e['verdict'] for e in entries)
out={'project':'The Arabic Tongue · Coptic restoration layer · Arabic ↔ Hieroglyphic Egyptian ↔ Coptic',
     'version':'2026-05-24','count':len(entries),
     'verdict_distribution':dict(dist.most_common()),
     'license':'CC-BY 4.0',
     'note':'Coptic is the SPOKEN third witness — it restores consonants the consonantal hieroglyphic script dropped (flagship لسان↔ns↔ⲗⲁⲥ). Most entries confirm already-attested Egyptian cognates; the Coptic adds evidence, not new claims. * marks a reconstructed Egyptian ancestor (standard historical-linguistics convention). Coptic lemmas from Crum / KELLIA.',
     'entries':entries}
json.dump(out,open(ROOT+'04-cross-linguistic/data/coptic-cognates.json','w',encoding='utf-8'),ensure_ascii=False,indent=2)
top=dist['PERFECT']+dist['STRONG']
print('Coptic restoration layer: %d entries' % len(entries))
print('Distribution:', dict(dist.most_common()))
print('Top-tier (PERFECT+STRONG): %d/%d = %d%%' % (top,len(entries),round(top/len(entries)*100)))
