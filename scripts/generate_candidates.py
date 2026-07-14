#!/usr/bin/env python3
"""Sound-first Arabic candidate generator (charter step 10, mechanized).

Given a branch word's consonant skeleton (romanized or Arabic), list EVERY
Arabic root and nucleus reachable through (a) the standard articulation-family
transliteration anchor and (b) the licensed rows parsed live from the frozen
shift network. The tool proposes CANDIDATES ONLY: no verdict, no reading, no
semantic claim. It exists so that no card is ever closed after testing only
the first Arabic counterpart that came to mind.

Usage:
  python scripts/generate_candidates.py snf
  python scripts/generate_candidates.py "s n w"
  python scripts/generate_candidates.py ختم --max 40
"""
from __future__ import annotations
import json, re, os, sys, argparse, unicodedata
from itertools import product

sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)

AR = set('ءابتثجحخدذرزسشصضطظعغفقكلمنهوي')

# articulation-family transliteration anchor (identity layer, not shifts):
# each romanized symbol maps to the Arabic letters of ITS OWN mouth family.
ANCHOR = {
    'b': 'ب', 'p': 'بف', 'f': 'ف', 'm': 'م', 'w': 'و', 'v': 'وف',
    't': 'تط', 'd': 'دض', 'ṭ': 'ط', 'ḍ': 'ض', 'th': 'ث', 'ṯ': 'ث', 'dh': 'ذ', 'ḏ': 'ذظ',
    's': 'سص', 'ṣ': 'ص', 'z': 'ز', 'š': 'ش', 'sh': 'ش',
    'n': 'ن', 'l': 'ل', 'r': 'ر',
    'k': 'كق', 'g': 'جقك', 'q': 'ق', 'ḳ': 'ق',
    'ḫ': 'خ', 'x': 'خ', 'kh': 'خ', 'ġ': 'غ', 'gh': 'غ',
    'ḥ': 'ح', 'h': 'هح', 'ʕ': 'ع', 'ꜥ': 'ع', '3': 'ع', 'ʔ': 'ء', 'j': 'جي', 'y': 'ي', 'i̯': 'ي',
    'c': 'كق',
}
MULTI = sorted((k for k in ANCHOR if len(k) > 1), key=len, reverse=True)

def parse_network_pairs():
    """Licensed one-step pairs parsed live from the frozen shift network."""
    pairs = {}
    t = open('04-cross-linguistic/shift-network-draft.md', encoding='utf-8').read()
    for m in re.finditer(r'^\|\s*([A-Z]+-\d+)\s*\|\s*([^|]+)\|', t, re.M):
        rid, cell = m.group(1), m.group(2).strip()
        mm = re.match(r'([ء-ي])\s*↔\s*([ء-يA-Za-zṯḏšḫḥʕġṣṭḍ/øØ]+)', cell)
        if not mm:
            continue
        a, b = mm.group(1), mm.group(2)
        for alt in re.split(r'[/،,]', b):
            alt = alt.strip()
            if len(alt) == 1 and alt in AR:
                pairs.setdefault(a, set()).add((alt, rid))
                pairs.setdefault(alt, set()).add((a, rid))
    return pairs

def skeletonize(word):
    """Input (romanized or Arabic) -> list of per-slot Arabic candidate sets."""
    word = unicodedata.normalize('NFC', word.strip().lower())
    word = re.sub(r'[\s.\-_]+', '', word)
    slots = []
    i = 0
    while i < len(word):
        ch = word[i]
        if ch in AR:
            slots.append({(ch, 'identity')}); i += 1; continue
        matched = None
        for mk in MULTI:
            if word.startswith(mk, i):
                matched = mk; break
        key = matched or ch
        if key in ANCHOR:
            slots.append({(c, 'anchor') for c in ANCHOR[key]})
            i += len(key)
        elif ch in 'aeiouāēīōūǎě':
            i += 1  # vowels are not skeleton slots
        else:
            i += 1  # unknown symbol: skipped, reported by caller if needed
    return slots

def expand(slots, pairs, allow_shift=True):
    """All Arabic skeletons reachable: anchor identity + at most ONE licensed shift."""
    out = {}
    base_sets = [[c for c, _ in s] for s in slots]
    for combo in product(*base_sets):
        out.setdefault(''.join(combo), []).append('مرساة العائلة')
    if allow_shift:
        for idx, s in enumerate(slots):
            for c, _ in s:
                for alt, rid in pairs.get(c, ()):  # one licensed step in one slot
                    sets2 = list(base_sets)
                    sets2[idx] = [alt]
                    for combo in product(*sets2):
                        out.setdefault(''.join(combo), []).append(f'صف {rid} في الخانة {idx+1}')
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('skeleton')
    ap.add_argument('--max', type=int, default=30)
    a = ap.parse_args()

    pairs = parse_network_pairs()
    slots = skeletonize(a.skeleton)
    if not slots:
        print('لا هيكلَ صامتيًّا مقروءًا في المدخل'); return
    cands = expand(slots, pairs)

    roots = {}
    for line in open('computational/data/layer_2_results_v2.jsonl', encoding='utf-8'):
        if line.strip():
            r = json.loads(line)
            roots[r['tri_root']] = r.get('jabal_axial', '')
    core = json.load(open('data/juthoor-core-levels.json', encoding='utf-8'))
    HM = {'أ': 'ء', 'إ': 'ء', 'آ': 'ء'}
    nuc = {}
    for n in core['levels']['level_2_binary_nuclei']['nuclei']:
        k = ''.join(HM.get(c, c) for c in n['nucleus'].replace('-', '').replace(' ', ''))
        nuc[k] = n.get('jabal_lexicon_reading_ar') or n.get('composed_reading_ar') or ''

    n_slots = len(slots)
    hits = []
    for skel, paths in cands.items():
        path = sorted(set(paths))[0]
        if n_slots >= 3 and skel in roots:
            hits.append(('جذر كامل', skel, roots[skel][:60], path))
        if skel[:2] in nuc:
            label = 'نواة' if n_slots == 2 else 'نواة (أول حرفين)'
            hits.append((label, skel[:2], nuc[skel[:2]][:60], path))
        if n_slots == 2:
            # hollow expansion: C1 + مد + C2 roots (amendment 1)
            for mid in 'اوي':
                hollow = skel[0] + mid + skel[1]
                if hollow in roots:
                    hits.append(('جذر أجوف (تعديل 1)', hollow, roots[hollow][:60], path + ' + خانة مد'))
    seen, out = set(), []
    for h in hits:
        key = (h[0], h[1])
        if key not in seen:
            seen.add(key); out.append(h)
    print(f'الهيكل: {a.skeleton} ({n_slots} خانات) | مرشحات مولدة: {len(cands)} | إصابات في الأدوات: {len(out)}')
    print('تذكير: هذه مرشحات صوتية فقط؛ المعنى والمصفاة والحكم على البطاقة لا هنا.')
    for kind, k, reading, path in out[:a.max]:
        print(f'  [{kind}] {k} «{reading}» ← {path}')
    if len(out) > a.max:
        print(f'  ... و{len(out) - a.max} أخرى (ارفع --max)')

if __name__ == '__main__':
    main()
