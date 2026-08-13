# -*- coding: utf-8 -*-
from __future__ import annotations
import hashlib,json,re,subprocess,unicodedata
from collections import Counter,defaultdict
from pathlib import Path
from types import SimpleNamespace

ROOT=Path(__file__).resolve().parent.parent
SOURCE=ROOT/'data/prior-art-extended-pairs.json'
OUT=ROOT/'data/comparative-language-assignments.json'
TRIAGE=ROOT/'data/comparative-rows-triaged.json'
ALLOWED={'ancient-greek','gothic','middle-english','old-english','old-irish','old-latin','old-norse','welsh'}

base=subprocess.check_output(['git','show','2882fc0:scripts/_tmp_build_jassem_ie_batch_001.py'],cwd=ROOT,text=True,encoding='utf-8')
ns={'__name__':'_base','__file__':str(ROOT/'scripts/_x.py')};exec(compile(base,'base','exec'),ns);B=SimpleNamespace(**ns)
def norm(x):return B.norm(str(x or ''))
def key(i,r):
 raw=json.dumps([i,r.get('tongue'),norm(r.get('foreign')),B.clean(r.get('foreign_sense')),B.clean(r.get('arabic_root')),B.clean(r.get('arabic_gloss')),r.get('source'),r.get('page')],ensure_ascii=False,separators=(',',':'))
 return hashlib.sha256(raw.encode()).hexdigest()[:24]

existing=defaultdict(set)
for p in sorted((ROOT/'data').glob('khashim-indo-european-batch-*.json')):
 for c in json.loads(p.read_text(encoding='utf-8'))['rows']:
  for f in B.card_forms(c):existing[norm(f)].add(c['language'])
for p in sorted((ROOT/'data').glob('jassem-indo-european-batch-*.json')):
 for c in json.loads(p.read_text(encoding='utf-8')).get('rows',[]):existing[c['normalized_head']].add(c['language'])

def fold(x):return ''.join(c for c in unicodedata.normalize('NFKD',str(x or '')).casefold() if not unicodedata.combining(c))
def has(s,*xs):return any(x in s for x in xs)
MANUAL={
 # Generic ``European languages`` clusters: the cited spelling, not source order,
 # decides which available historical branch receives the row.
 **{i:'old-latin' for i in (95,96,99,447,607,608,609,610,611,612,622,747,2167,2170,2171,2172,2321,2457,2479,2480,2489,2490,2491,2497,2498,2499,2500,2590,2591,2592,2593,2596,2597,2598,2599,2632,2633,2634,2668,2669,2670,2671,2717,2718,2719,2820,2821,2822,2823,2852,2853,2854,2875,2876,2877,2944,3155,3156,3157,3158)},
 **{i:'middle-english' for i in (445,618,623,750,2168,2169,2320,2323,2324,2455,2456,2475,2477,2478,2488,2492,2495,2496,2587,2589,2595,2629,2630,2667,2714,2716,2818,2819,2870,2873,2874,2943)},
 **{i:'old-norse' for i in (98,2322,2454,2476,2487,2493,2494,2588,2850,2871,2872,3154)},
 615:'ancient-greek',
 127:'middle-english',188:'old-latin',217:'old-latin',333:'old-latin',800:'ancient-greek',843:'old-norse',845:'old-latin',
 # Mixed cross-linguistic clusters: only spellings with a visible European owner.
 765:'old-latin',1916:'middle-english',1917:'middle-english',1918:'old-latin',1919:'old-latin',1920:'old-latin',
 1926:'middle-english',1928:'middle-english',1929:'middle-english',1955:'middle-english',2046:'ancient-greek',
 2161:'old-latin',2280:'old-latin',2281:'old-norse',2395:'middle-english',2396:'middle-english',2397:'middle-english',
 2431:'middle-english',2432:'middle-english',2433:'old-latin',2481:'middle-english',2482:'old-latin',2483:'old-latin',2484:'old-latin',2485:'old-latin',
 2751:'middle-english',2752:'middle-english',2808:'old-norse',2809:'old-norse',2810:'middle-english',
 3048:'middle-english',3050:'middle-english',3051:'old-latin',3056:'middle-english',3057:'old-norse',3058:'old-norse',3059:'middle-english',3060:'middle-english',
 3100:'old-latin',3101:'old-latin',3102:'old-latin',3107:'middle-english',3180:'old-norse',3181:'middle-english',
 3300:'ancient-greek',3301:'ancient-greek',3302:'ancient-greek',3303:'ancient-greek',3393:'ancient-greek',3473:'ancient-greek',3550:'ancient-greek',3552:'ancient-greek',
}
MANUAL.update({
 181:'old-norse',584:'old-latin',742:'middle-english',773:'middle-english',774:'old-norse',
 930:'old-latin',994:'old-latin',1367:'middle-english',1371:'old-norse',1372:'middle-english',1373:'middle-english',
 1389:'middle-english',1436:'middle-english',1440:'old-latin',1452:'old-norse',1454:'middle-english',
 1630:'middle-english',1632:'old-norse',1657:'middle-english',1665:'middle-english',
 1752:'old-english',1754:'middle-english',1755:'old-norse',1756:'middle-english',
 1782:'old-norse',1789:'middle-english',1869:'old-english',1870:'old-english',
 1905:'old-english',1906:'old-english',1907:'middle-english',1934:'old-norse',1940:'old-norse',
 1945:'old-norse',1947:'middle-english',1963:'middle-english',1965:'middle-english',
 1973:'middle-english',1974:'middle-english',1975:'middle-english',1984:'middle-english',
 2004:'ancient-greek',2005:'ancient-greek',2021:'old-norse',2023:'middle-english',2024:'middle-english',
 2034:'middle-english',2035:'old-norse',2036:'middle-english',2051:'old-english',2052:'old-english',2053:'middle-english',
 2059:'old-norse',2065:'middle-english',2066:'middle-english',2068:'old-norse',2069:'old-norse',2070:'middle-english',2071:'middle-english',
})

def classify(i,r):
 f=str(r.get('foreign') or '').strip();n=norm(f);ta=str(r.get('tongue_ar') or '');cat=r.get('tongue')
 if len(existing.get(n,()))==1:return next(iter(existing[n])),'exact form already has one Indo-European card'
 if i in MANUAL:return MANUAL[i],'cited spelling gives a specific European branch inside a mixed or generic cluster'
 if re.search(r'[\u0370-\u03ff\u1f00-\u1fff]',f):return 'ancient-greek','Greek script in the cited form'
 if re.search(r'[\U00010330-\U0001034f]',f):return 'gothic','Gothic script in the cited form'
 if has(ta,'الإيرلندي','الإسكتلندي') and not has(ta,'الإنكليزيّة','اللاتينيّة','اليونانيّة'):return 'old-irish','Irish/Scottish language named for this form cluster'
 if has(ta,'الويلزي') and not has(ta,'الإنكليزيّة','اللاتينيّة','اليونانيّة'):return 'welsh','Welsh named for this form cluster'
 ff=fold(f)
 norse_named=has(ta,'النوردي','السويدي','الدنماركي')
 greek_named=has(ta,'اليوناني')
 latin_named=has(ta,'اللاتيني')
 english_named=has(ta,'الإنكليزي')
 germanic_named=has(ta,'الجرماني','الألماني','الهولندي','السويدي','الدنماركي','النوردي')
 romance_named=has(ta,'الروماني','الفرنسي','الإيطالي','الإسباني','البرتغالي')
 # Visible historical morphology outranks a multi-language cluster label.
 if norse_named and (re.search(r'[þðæøǫ]',ff) or re.search(r'(?:r|ar|ir|ur)$',ff)):
  return 'old-norse','Norse/Scandinavian named and cited form has a Norse-looking ending or letter'
 if greek_named and re.search(r'(?:os|on|es|e|oi|ai|ia|ikos|ikon|ismos|ma|sis)$',ff):
  return 'ancient-greek','Greek named and cited form has Greek/romanized Greek morphology'
 if latin_named and re.search(r'(?:us|um|ae|is|am|as|ibus|orum|arum|ium|io|ius|icus|ica|alis|aris|itas|are|ere|ire|ntia|tio|tor|trix)$',ff):
  return 'old-latin','Latin named and cited form has Latin morphology'
 if cat=='cross-european':
  if latin_named or romance_named:return 'old-latin','Latin/Romance branch named; routed to the Latin historical file'
  if greek_named:return 'ancient-greek','Greek is the named historical branch'
  if norse_named:return 'old-norse','Norse/Scandinavian branch named'
  if english_named or germanic_named:return 'middle-english','English/Germanic modern or medieval-looking form; routed to Middle English'
  if has(ta,'الغاليّة') or has(ta,'الكلتي'):return 'welsh','Celtic/Gaulish cluster routed to the available Brittonic historical file'
  return None,'cross-European label does not identify which allowed historical language owns this cited form'
 # Mixed cross-linguistic rows need a positive European signal; otherwise do not steal another lane's form.
 if latin_named and (re.search(r'[a-z]',ff) and not re.fullmatch(r'[A-Z0-9 .()/-]+',f)):return 'old-latin','Latin named and the cited lower-case alphabetic form is compatible with Latin/Romance'
 if greek_named and re.search(r'(?:os|on|es|ia|ion|ikos|ma|sis)$',ff):return 'ancient-greek','Greek named and the cited form has Greek morphology'
 if norse_named and (re.search(r'[þðæøǫ]',ff) or re.search(r'(?:r|ar|ir|ur)$',ff)):return 'old-norse','Norse named and form-specific morphology supports it'
 if english_named and re.fullmatch(r"[A-Za-z][A-Za-z '\-]*",f):return 'middle-english','English named and cited form is an English alphabetic word'
 if has(ta,'الويلزي') and re.fullmatch(r"[A-Za-z][A-Za-z '\-]*",f):return 'welsh','Welsh named and cited form is compatible with the Welsh branch'
 if has(ta,'الإيرلندي','الإسكتلندي') and re.fullmatch(r"[A-Za-z][A-Za-z '\-]*",f):return 'old-irish','Irish/Scottish named and cited form is compatible with the Gaelic branch'
 return None,'mixed-language row; cited form cannot be assigned confidently to one of the eight allowed Indo-European files'

rows=json.loads(SOURCE.read_text(encoding='utf-8'))['rows'];items=[];tri=[]
for i,r in enumerate(rows):
 if r.get('tongue') not in {'cross-european','cross-linguistic'}:continue
 lang,reason=classify(i,r);item={'source_row_index':i,'source_row_key':key(i,r),'category':r['tongue'],'foreign':r.get('foreign'),'foreign_sense':r.get('foreign_sense'),'tongue_ar':r.get('tongue_ar'),'language':lang,'reason':reason,'source':r.get('source'),'book':r.get('book'),'page':r.get('page')};items.append(item)
 if lang is None:tri.append({**item,'row':r})
assert len(items)==1942 and all(x['language'] in ALLOWED or x['language'] is None for x in items)
payload={'schema':'comparative-language-assignments-v1.0','date':'2026-08-14','source':'data/prior-art-extended-pairs.json','policy':'exact prior card first; then cited form/script and named branch; ambiguous mixed-language forms remain triaged','counts':{'total':len(items),'assigned':sum(x['language'] is not None for x in items),'triaged':len(tri),'by_category':dict(Counter(x['category'] for x in items)),'assigned_by_language':dict(sorted(Counter(x['language'] for x in items if x['language']).items())),'triaged_by_category':dict(Counter(x['category'] for x in tri))},'rows':items}
OUT.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
TRIAGE.write_text(json.dumps({'schema':'comparative-rows-triaged-v1.0','date':'2026-08-14','source':'data/prior-art-extended-pairs.json','count':len(tri),'reason':'could not confidently assign the cited form to one of the eight allowed Indo-European reading files','rows':tri},ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
print(json.dumps(payload['counts'],ensure_ascii=False))
for x in tri[:80]:print(x['source_row_index'],x['category'],x['foreign'],x['tongue_ar'])

