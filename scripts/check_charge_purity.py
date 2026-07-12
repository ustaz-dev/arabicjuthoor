#!/usr/bin/env python3
"""Permanent charge-purity and data-hygiene checker (constitutional amendment 3).

Structural guarantees enforced on every run:
 1. nucleus labels in both Jabal extracts are 2-3 Arabic letters
 2. no exported nucleus reading is actually a LETTER description (the six-column leak)
 3. every recomposed nucleus keeps its legacy_reading_ar, different from the new reading
 4. no em-dash in the canonical scholarly files
 5. every exported Jabal reading exists letter-identically (diacritics stripped) in a source file
 6. WARN: known unlicensed rider words inside composed readings

Exit code 1 on any hard failure. Run:  python scripts/check_charge_purity.py
"""
import json, re, os, sys, unicodedata
from collections import Counter
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)

AR = 'ءاأإآبتثجحخدذرزسشصضطظعغفقكلمنهوي'
DIAC = re.compile(r'[ً-ْٰـ]')
strip = lambda s: DIAC.sub('', s)
HM = {'أ': 'ء', 'إ': 'ء', 'آ': 'ء'}
norm = lambda n: ''.join(HM.get(c, c) for c in n.replace(' ', '').replace('-', ''))

fails, warns = [], []
CAT = open('03-scholar-extracts/jabal-nuclei-catalog.md', encoding='utf-8').read()
UND = open('03-scholar-extracts/jabal-nuclei-undocumented.md', encoding='utf-8').read()
EXT = open('03-scholar-extracts/jabal-nuclei-extended.md', encoding='utf-8').read()
EXP = json.load(open('data/juthoor-core-levels.json', encoding='utf-8'))
NUC = EXP['levels']['level_2_binary_nuclei']['nuclei']

# 1. nucleus label hygiene at the sources
for src, body in (('catalog', CAT), ('undocumented', UND)):
    for m in re.finditer(r'^\|\s*\*\*([^*|]+)\*\*', body, re.M):
        k = norm(m.group(1).strip())
        if k in ('نواة', 'النواة'): continue  # header rows
        if not (2 <= len(k) <= 3) or any(c not in AR for c in k):
            fails.append(f'label hygiene ({src}): «{m.group(1).strip()}»')

# 2. letter-description leak detector
by_letter = {}
for body in (CAT, UND):
    for m in re.finditer(r'^\|\s*\*\*([^*|]+)\*\*[^|]*\|\s*([^|]*)\|\s*([^|]*)\|', body, re.M):
        k = norm(m.group(1))
        if not (2 <= len(k) <= 3) or any(c not in AR for c in k): continue
        for pos, cell in ((0, m.group(2).strip()), (1, m.group(3).strip())):
            if len(cell) > 6:
                by_letter.setdefault(k[pos], Counter())[strip(cell)] += 1
LDESC = {L: {s for s, n in c.items() if n >= 4} for L, c in by_letter.items()}
for n in NUC:
    k = norm(n['nucleus'])
    r = strip(n.get('jabal_lexicon_reading_ar', '') or '')
    if r and len(k) >= 2 and (r in LDESC.get(k[0], set()) or r in LDESC.get(k[1], set())):
        fails.append(f'letter-desc leak: {k} reads like a letter description «{r[:40]}»')

# 3. legacy preservation for recomposed nuclei
try:
    LEG = json.load(open('data/legacy-readings-2026-07-12.json', encoding='utf-8'))
except FileNotFoundError:
    LEG = {}
byk = {norm(n['nucleus']): n for n in NUC}
for k, old in LEG.items():
    rec = byk.get(norm(k))
    if not rec:
        fails.append(f'legacy: nucleus {k} vanished from export'); continue
    if rec.get('legacy_reading_ar', '').strip() != old.strip():
        fails.append(f'legacy: {k} lost its legacy_reading_ar')
    if strip(rec.get('composed_reading_ar', '')) == strip(old):
        fails.append(f'legacy: {k} composed reading equals the legacy one (recomposition lost)')

# 4. no em-dash in canonical scholarly files
import glob
CANON_MD = (['03-scholar-extracts/canonical-letter-registry.md',
             '02-architecture/deep-decomposition-method.md',
             '03-scholar-extracts/letter-dossier-ba-draft.md']
            + glob.glob('03-scholar-extracts/letter-dossiers/*.md'))
for p in CANON_MD:
    body = open(p, encoding='utf-8').read()
    cnt = body.count('—')
    if cnt:
        fails.append(f'em-dash: {p} contains {cnt}')

# 5. exported Jabal readings must exist letter-identically at a source
SRC_STRIPPED = strip(CAT) + strip(UND) + strip(EXT)
for n in NUC:
    r = (n.get('jabal_lexicon_reading_ar') or '').strip()
    if r and strip(r) not in SRC_STRIPPED:
        fails.append(f'provenance: {norm(n["nucleus"])} jabal reading not found at any source «{r[:35]}»')

# 6. rider words inside composed readings (WARN only; frozen-card exceptions listed in rulings)
RIDERS = ['مفاجئ', 'صاعِدًا', 'صاعدا', 'يرتفع', 'بألم', 'مشقّة', 'مشقة', 'ثمن', 'فكرة', 'حُبّ']
FROZEN_DEFERRED = {'نخ', 'عن', 'مه'}
for n in NUC:
    c = n.get('composed_reading_ar', '') or ''
    k = norm(n['nucleus'])
    for w in RIDERS:
        if w in c:
            (warns if k in FROZEN_DEFERRED else fails).append(
                f'rider: {k} carries «{w}» in its composed reading' + (' (frozen, deferred to the author)' if k in FROZEN_DEFERRED else ''))

print(f'checked {len(NUC)} nuclei, {len(CANON_MD)} canonical files')
for w in warns: print('WARN :', w)
for f in fails: print('FAIL :', f)
print('RESULT:', 'CLEAN' if not fails else f'{len(fails)} failure(s)')
sys.exit(1 if fails else 0)
