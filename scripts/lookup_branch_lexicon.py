#!/usr/bin/env python3
"""Branch-side skeleton lookup over the kaikki dictionaries (charter step 15).

The reverse-sweep companion of generate_candidates.py: given a consonant
skeleton (from an Arabic root or nucleus, romanized), stream a language's
kaikki JSONL and return every entry whose own consonant skeleton matches.
Retrieval only: no verdict, no reading, no claim.

Usage:
  python scripts/lookup_branch_lexicon.py latin krn
  python scripts/lookup_branch_lexicon.py old_norse "mn" --max 15
Languages = folder names under Resources/ that hold a kaikki jsonl.
"""
from __future__ import annotations
import json, re, os, sys, argparse, glob, unicodedata

sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)

# per-symbol normalization into a comparable consonant alphabet
FOLD = {'c': 'k', 'q': 'k', 'x': 'ks', 'ph': 'f', 'th': 'th', 'ch': 'kh',
        'ß': 'ss', 'þ': 'th', 'ð': 'dh', 'ƕ': 'hw'}
VOWELS = set('aeiouyāēīōūȳăĕĭŏŭàèìòùáéíóúäëïöüâêîôûæœ')

def skeleton(word):
    w = unicodedata.normalize('NFD', word.lower())
    w = ''.join(c for c in w if not unicodedata.combining(c))
    out, i = [], 0
    while i < len(w):
        two = w[i:i+2]
        if two in FOLD:
            out.append(FOLD[two]); i += 2; continue
        ch = w[i]
        if ch in FOLD:
            out.append(FOLD[ch])
        elif ch.isalpha() and ch not in VOWELS:
            out.append(ch)
        i += 1
    return ''.join(out)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('language', help='folder name under Resources/ (e.g. latin, gothic, persian)')
    ap.add_argument('skel', help='consonant skeleton to match, romanized (e.g. krn)')
    ap.add_argument('--max', type=int, default=25)
    ap.add_argument('--contains', action='store_true', help='match as substring instead of exact')
    a = ap.parse_args()

    files = glob.glob(os.path.join('Resources', a.language, '*.jsonl'))
    if not files:
        print(f'لا ملف kaikki تحت Resources/{a.language}؛ راجع فهرس الذخيرة'); return
    want = skeleton(a.skel) or a.skel.lower()
    hits, scanned = [], 0
    with open(files[0], encoding='utf-8') as fh:
        for line in fh:
            scanned += 1
            try:
                e = json.loads(line)
            except json.JSONDecodeError:
                continue
            w = e.get('word', '')
            sk = skeleton(w)
            ok = (want in sk) if a.contains else (sk == want)
            if ok:
                gloss = ''
                for s in e.get('senses', []):
                    gl = s.get('glosses') or s.get('raw_glosses') or []
                    if gl:
                        gloss = gl[0]; break
                ety = (e.get('etymology_text') or '')[:90]
                hits.append((w, e.get('pos', ''), gloss[:90], ety))
                if len(hits) >= a.max:
                    break
    print(f'{a.language}: هيكل «{want}» | فحص {scanned} سطرًا | إصابات: {len(hits)}')
    print('تذكير: استرجاع فقط؛ البطاقة والمصفاة والحكم في ملف اللغة.')
    for w, pos, gloss, ety in hits:
        line = f'  {w} [{pos}] {gloss}'
        if ety:
            line += f'  || أصلها: {ety}'
        print(line)

if __name__ == '__main__':
    main()
