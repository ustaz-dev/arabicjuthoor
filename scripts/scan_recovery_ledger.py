#!/usr/bin/env python3
"""Recovery ledger scanner (charter step 16).

Parses every reading file's cards, extracts verdicts and closure states, and
emits data/recovery-ledger.json plus a console queue of everything suspended
(TOOL-GAP / LAW-GAP / SOURCE-GAP / OPEN-CANDIDATE). Cross-references each
blocker against the current instruments and flags cards whose blocker has
since been resolved (a signed shift row now exists, a nucleus now exists in
the catalog) so no connection is ever silently forgotten.

Run:  python scripts/scan_recovery_ledger.py
"""
from __future__ import annotations
import json, re, os, sys, glob, unicodedata

sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)

GAPS = ('TOOL-GAP', 'LAW-GAP', 'SOURCE-GAP', 'OPEN-CANDIDATE', 'MORPHOLOGY-GAP')

def cards(path):
    body = open(path, encoding='utf-8').read()
    # A reading card ends at the next level-three section, not merely at the
    # next card.  Organic-review sections often follow a READY card and carry
    # their own blockers; letting the preceding card swallow that section
    # falsely re-suspends the READY verdict.
    blocks = re.split(r'(?=^### )', body, flags=re.M)
    for b in blocks:
        if not (b.startswith('### بطاقة') or b.startswith('### إعادةُ توسيم')):
            continue
        head = b.split('\n', 1)[0]
        title = head.replace('### بطاقة', '').replace('### إعادةُ توسيم', '(إعادةُ توسيم)').strip(' :')
        if '<' in title:
            continue  # template block, not a real card
        verdict = ''
        m = re.search(r'الحكم[^\n]*?:\s*\*{0,2}([A-Z\-]+(?:\s+[^\n*]{0,40})?)', b)
        if m:
            verdict = m.group(1).strip(' *')
        closure = ''
        m = re.search(r'حالةُ? الإغلاق[^\n]*?:\s*\*{0,2}([^\n*]+)', b)
        if m:
            closure = m.group(1).strip()
        # structured blocker line is authoritative: - عائق: النوع=LAW-GAP؛ يتطلب=...
        blocker_type, required = '', ''
        m = re.search(r'^-\s*عائق:\s*النوع\s*=\s*([A-Z\-]+)\s*[؛;]\s*يتطلب\s*=\s*([^\n]+)', b, re.M)
        if m:
            blocker_type, required = m.group(1).strip(), m.group(2).strip()
        # Historical appendices deliberately preserve the obstacle they replaced.
        # Reading every gap token anywhere in the card therefore re-suspends a
        # resolved card merely because its audit trail says "كان TOOL-GAP".
        # The structured blocker is authoritative when present; the current
        # closure is the fallback for older cards that predate that field.
        gaps = []
        if blocker_type:
            if blocker_type in GAPS:
                gaps.append(blocker_type)
            gaps.extend(g for g in GAPS if g in closure and g not in gaps)
        else:
            gaps = [g for g in GAPS if g in closure]
        # prose mentions are hints only, never unlock triggers
        rows = sorted(set(re.findall(r'\bBR-[A-Z]+-\d+\b', b)))
        # بطاقاتُ إعادة الفحص تُلحَقُ ولا تمحو البطاقةَ التاريخيّة. يربط هذا
        # المعرّفُ الناسخَ بالمنسوخ كي يبقى النصُّ القديم في القراءة ولا يبقى
        # عائقُه القديم نافذًا في السجل. لا يُستعمل هذا الباب بلا معرّفٍ صريح.
        card_id = ''
        m = re.search(r'<!--\s*KHASHIM-IE:(\d+):[^>]+-->', b)
        if m:
            card_id = f'KHASHIM-IE:{m.group(1)}'
        supersedes = ''
        m = re.search(r'<!--\s*DEAD-GATE-REREVIEW:(KHASHIM-IE:\d+)\s*-->', b)
        if m:
            supersedes = m.group(1)
        yield {'file': path.replace('\\', '/'), 'card': title[:80], 'verdict': verdict,
               'closure': closure, 'gaps': gaps, 'blocker_type': blocker_type,
               'required': required, 'row_mentions': rows,
               '_card_id': card_id, '_supersedes': supersedes}

# current instruments
net = open('04-cross-linguistic/shift-network-draft.md', encoding='utf-8').read()
signed_rows = set(re.findall(r'\bBR-[A-Z]+-\d+\b', net)) | set(re.findall(r'^\|\s*([A-Z]+-\d+)\s*\|', net, re.M))
core = json.load(open('data/juthoor-core-levels.json', encoding='utf-8'))
HM = {'أ': 'ء', 'إ': 'ء', 'آ': 'ء'}
catalog = {''.join(HM.get(c, c) for c in n['nucleus'].replace('-', '').replace(' ', ''))
           for n in core['levels']['level_2_binary_nuclei']['nuclei']}

scanned = []
for path in sorted(glob.glob('04-cross-linguistic/readings/*.md')):
    for c in cards(path):
        scanned.append(c)

superseding = [c['_supersedes'] for c in scanned if c['_supersedes']]
duplicates = sorted({value for value in superseding if superseding.count(value) > 1})
if duplicates:
    print('FAIL: أكثر من بطاقة إعادة فحص تنسخ المعرّف نفسه: ' + '، '.join(duplicates[:10]))
    sys.exit(1)
known = {c['_card_id'] for c in scanned if c['_card_id']}
missing = sorted(set(superseding) - known)
if missing:
    print('FAIL: بطاقة إعادة فحص تشير إلى معرّف تاريخي غير موجود: ' + '، '.join(missing[:10]))
    sys.exit(1)

ledger, open_q, unlocked = [], [], []
superseded = set(superseding)
for c in scanned:
    if c['_card_id'] in superseded:
        continue
    c = {key: value for key, value in c.items() if not key.startswith('_')}
    ledger.append(c)
    suspended = bool(c['gaps']) or any(g in c['closure'] for g in GAPS)
    if not suspended:
        continue
    open_q.append(c)
    # unlock triggers come ONLY from the structured requirement field
    req = c.get('required', '')
    hints = []
    for rid in re.findall(r'\bBR-[A-Z]+-\d+\b', req):
        if rid in signed_rows:
            hints.append(f'الصف المطلوب {rid} موجود الآن في الشبكة')
    m = re.search(r'نواة\s+([ء-ي]{2,3})', req)
    if m and m.group(1) in catalog:
        hints.append(f'النواة المطلوبة {m.group(1)} موجودة الآن في الفهرس')
    if hints:
        unlocked.append((c, hints))

payload = {'generated_from': 'scan_recovery_ledger.py', 'cards_total': len(ledger),
           'suspended': [c for c in open_q]}
if '--check' in sys.argv:
    try:
        committed = json.load(open('data/recovery-ledger.json', encoding='utf-8'))
    except FileNotFoundError:
        print('FAIL: data/recovery-ledger.json missing; run the scanner and commit it')
        sys.exit(1)
    if committed != payload:
        print('FAIL: recovery ledger is stale; rerun scan_recovery_ledger.py and commit the result')
        sys.exit(1)
    print(f'ledger check: fresh ({len(open_q)} suspended of {len(ledger)} cards)')
    sys.exit(0)
os.makedirs('data', exist_ok=True)
json.dump(payload, open('data/recovery-ledger.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

print(f'بطاقات ممسوحة: {len(ledger)} | معلقة في الاسترداد: {len(open_q)}')
for c in open_q:
    tags = ','.join(c['gaps']) or c['closure'][:40]
    print(f"  [{tags}] {c['card']}  ({os.path.basename(c['file'])})")
if unlocked:
    print('\nبطاقات انفتح قيدها ويجب العودة إليها:')
    for c, hints in unlocked:
        print(f"  ← {c['card']}: " + '؛ '.join(sorted(set(hints))))
print('\nكتب: data/recovery-ledger.json')
