#!/usr/bin/env python3
"""Sound-first Arabic candidate generator (charter step 10, mechanized). v2

Given a branch word (romanized, Greek, Coptic, or Egyptological transliteration),
list EVERY Arabic root and nucleus reachable through (a) the articulation-family
anchor, (b) the anchor EXTENSIONS licensed by the frozen shift network's
Arabic-to-branch rows, and (c) at most one Arabic-internal licensed shift.
Retrieval only: no verdict, no reading, no semantic claim.

Honesty devices (v2):
- prints exactly which network rows were parsed, as what, and which were NOT
  (this parser reads the network's TABLE rows; branch-internal BR-* laws live
  in prose and must be applied by the reader, as the charter requires);
- unknown symbols are never dropped silently: they are reported, and --strict
  aborts instead of degrading the skeleton.

Usage:
  python scripts/generate_candidates.py snf
  python scripts/generate_candidates.py "τρεῖς" --strict
  python scripts/generate_candidates.py ϣⲛϥⲉ
"""
from __future__ import annotations
import json, re, os, sys, argparse, unicodedata
from itertools import product

sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)

AR = set('ءابتثجحخدذرزسشصضطظعغفقكلمنهوي')

# ---------- script folding: Greek / Coptic / Egyptological -> latin-ish tokens ----------
GREEK = {'α':'a','β':'b','γ':'g','δ':'d','ε':'e','ζ':'z','η':'e','θ':'th','ι':'i','κ':'k',
         'λ':'l','μ':'m','ν':'n','ξ':'ks','ο':'o','π':'p','ρ':'r','σ':'s','ς':'s','τ':'t',
         'υ':'u','φ':'f','χ':'kh','ψ':'ps','ω':'o'}
COPTIC = {'ⲁ':'a','ⲃ':'b','ⲅ':'g','ⲇ':'d','ⲉ':'e','ⲍ':'z','ⲏ':'e','ⲑ':'th','ⲓ':'i','ⲕ':'k',
          'ⲗ':'l','ⲙ':'m','ⲛ':'n','ⲝ':'ks','ⲟ':'o','ⲡ':'p','ⲣ':'r','ⲥ':'s','ⲧ':'t','ⲩ':'u',
          'ⲫ':'f','ⲭ':'kh','ⲯ':'ps','ⲱ':'o','ϣ':'š','ϥ':'f','ϧ':'ḫ','ϩ':'h','ϫ':'j','ϭ':'č','ϯ':'ti'}
EGYPTO = {'ꜣ':'ʔ', 'ꜥ':'ʕ', 'ı͗':'j', 'ỉ':'j', 'i̯':'y'}

# articulation-family transliteration anchor (identity layer, not shifts)
ANCHOR = {
    'b': 'ب', 'p': 'بف', 'f': 'ف', 'm': 'م', 'w': 'و', 'v': 'وف',
    't': 'تط', 'd': 'دض', 'ṭ': 'ط', 'ḍ': 'ض', 'th': 'ث', 'ṯ': 'ث', 'dh': 'ذ', 'ḏ': 'ذظ',
    's': 'سص', 'ṣ': 'ص', 'z': 'ز', 'š': 'ش', 'sh': 'ش', 'č': 'شج',
    'n': 'ن', 'l': 'ل', 'r': 'ر',
    'k': 'كق', 'g': 'جقك', 'q': 'ق', 'ḳ': 'ق',
    'ḫ': 'خ', 'x': 'خ', 'kh': 'خ', 'ġ': 'غ', 'gh': 'غ',
    'ḥ': 'ح', 'h': 'هح', 'ʕ': 'ع', 'ꜥ': 'ع', '3': 'ع', 'ʔ': 'ء', 'j': 'جي', 'y': 'ي',
    'c': 'كق', 'ps': 'بس', 'ks': 'كس', 'ti': 'ت',
}
MULTI = sorted((k for k in ANCHOR if len(k) > 1), key=len, reverse=True)
VOWELS = set('aeiouāēīōūǎěáéíóúàèìòù')


def parse_network():
    """Read every TABLE row of the frozen network; classify, never skip silently."""
    ar_pairs, anchor_ext = {}, {}
    parsed_ar, parsed_ext, branch_internal, unparsed = [], [], [], []
    t = open('04-cross-linguistic/shift-network-draft.md', encoding='utf-8').read()
    for m in re.finditer(r'^\|\s*([A-Z]+-\d+)\s*\|\s*([^|]+)\|', t, re.M):
        rid, cell = m.group(1), m.group(2).strip()
        if '↔' not in cell:
            unparsed.append(rid); continue
        left, right = [s.strip() for s in cell.split('↔', 1)]
        right = re.sub(r'\(.*?\)', '', right).strip()  # strip scope notes like (إيرانية)
        L_ar = [c for c in left if c in AR]
        R_ar = [c for c in right if c in AR]
        L_lat = [tok for tok in re.split(r'[/،,\s]+', left) if tok and not any(c in AR for c in tok)]
        R_lat = [tok for tok in re.split(r'[/،,\s]+', right) if tok and not any(c in AR for c in tok)]
        if L_ar and R_ar:
            for a in L_ar:
                for b in R_ar:
                    ar_pairs.setdefault(a, set()).add((b, rid))
                    ar_pairs.setdefault(b, set()).add((a, rid))
            parsed_ar.append(rid)
        elif L_ar and R_lat:
            for tok in R_lat:
                key = tok.lower()
                if key in ('ø', 'Ø'.lower()):
                    continue  # deletion rows license absence, not a slot letter
                for a in L_ar:
                    anchor_ext.setdefault(key, set()).add((a, rid))
            parsed_ext.append(rid)
        elif L_lat and R_lat:
            branch_internal.append(rid)
        else:
            unparsed.append(rid)
    return ar_pairs, anchor_ext, {'ar': parsed_ar, 'ext': parsed_ext,
                                  'internal': branch_internal, 'unparsed': unparsed}


def skeletonize(word, anchor_ext):
    """word -> (slots, unknown_symbols). Never drops a symbol silently."""
    w = unicodedata.normalize('NFD', word.strip().lower())
    w = ''.join(c for c in w if not unicodedata.combining(c))
    w = unicodedata.normalize('NFC', w)
    # fold scripts to latin-ish tokens first
    folded = []
    for ch in w:
        folded.append(GREEK.get(ch) or COPTIC.get(ch) or EGYPTO.get(ch) or ch)
    w = ''.join(folded)
    w = re.sub(r'[\s.\-_·]+', '', w)
    slots, unknown, i = [], [], 0
    while i < len(w):
        ch = w[i]
        if ch in AR:
            slots.append({(ch, 'identity')}); i += 1; continue
        key = None
        for mk in MULTI:
            if w.startswith(mk, i):
                key = mk; break
        key = key or ch
        opts = set()
        if key in ANCHOR:
            opts |= {(c, 'مرساة') for c in ANCHOR[key]}
        if key in anchor_ext:
            opts |= {(c, f'صف {rid}') for c, rid in anchor_ext[key]}
        if opts:
            slots.append(opts); i += len(key)
        elif ch in VOWELS:
            i += 1
        else:
            unknown.append(ch); i += 1
    return slots, unknown


def expand(slots, ar_pairs):
    out = {}
    base = [sorted({c for c, _ in s}) for s in slots]
    paths0 = ['+'.join(sorted({p for _, p in s if p != 'identity'}) or ['مرساة']) for s in slots]
    for combo in product(*base):
        out.setdefault(''.join(combo), set()).add('مرساة/امتداد مرخص')
    for idx, s in enumerate(slots):
        for c, _ in s:
            for alt, rid in ar_pairs.get(c, ()):  # one Arabic-internal licensed step
                sets2 = list(base)
                sets2[idx] = [alt]
                for combo in product(*sets2):
                    out.setdefault(''.join(combo), set()).add(f'صف {rid} في الخانة {idx + 1}')
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('skeleton')
    ap.add_argument('--max', type=int, default=30)
    ap.add_argument('--strict', action='store_true', help='abort on any unknown symbol')
    a = ap.parse_args()

    ar_pairs, anchor_ext, cov = parse_network()
    print(f"قراءة الشبكة: {len(cov['ar'])} صف عربي-عربي، {len(cov['ext'])} صف امتداد مرساة، "
          f"{len(cov['internal'])} صف داخلي للفرع (يُطبَّق يدويًّا من نصه)، {len(cov['unparsed'])} غير مقروء"
          + (f" [{', '.join(cov['unparsed'])}]" if cov['unparsed'] else ''))
    print(f"  عربي-عربي: {', '.join(cov['ar'])}")
    print(f"  امتدادات: {', '.join(cov['ext'])} | داخلية: {', '.join(cov['internal'])}")
    print("  تنبيه: صفوف BR-* الداخلية للفروع (المصرية، الصينية...) نصوص خارج الجدول؛ طبِّقها يدويًّا قبل الهيكلة.")

    slots, unknown = skeletonize(a.skeleton, anchor_ext)
    if unknown:
        msg = f"رموز غير معروفة لم تُهيكل: {', '.join(sorted(set(unknown)))}"
        if a.strict:
            print('إيقاف (--strict): ' + msg); sys.exit(2)
        print('تحذير: ' + msg + ' — الهيكل ناقص وقد تفوتك مرشحات؛ أضف الرمز لجداول التطبيع أو استعمل صورة رومنة أخرى.')
    if not slots:
        print('لا هيكل صامتيا مقروءا في المدخل'); sys.exit(2)

    cands = expand(slots, ar_pairs)

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
    hits, seen = [], set()

    def add(kind, key, reading, path):
        if (kind, key) not in seen:
            seen.add((kind, key)); hits.append((kind, key, reading, path))

    for skel, paths in sorted(cands.items()):
        path = sorted(paths)[0]
        if n_slots >= 3 and skel in roots:
            add('جذر كامل', skel, roots[skel][:60], path)
        if skel[:2] in nuc:
            add('نواة' if n_slots == 2 else 'نواة (أول حرفين)', skel[:2], nuc[skel[:2]][:60], path)
        if n_slots == 2:
            for mid in 'اوي':
                hollow = skel[0] + mid + skel[1]
                if hollow in roots:
                    add('جذر أجوف (تعديل 1)', hollow, roots[hollow][:60], path + ' + خانة مد')

    print(f"\nالهيكل: {a.skeleton} ← {n_slots} خانات | هياكل مولدة: {len(cands)} | إصابات في الأدوات: {len(hits)}")
    print('تذكير: مرشحات صوتية فقط؛ المعنى والمصفاة والحكم على البطاقة لا هنا.')
    for kind, k, reading, path in hits[:a.max]:
        print(f'  [{kind}] {k} «{reading}» ← {path}')
    if len(hits) > a.max:
        print(f'  ... و{len(hits) - a.max} أخرى (ارفع --max)')


if __name__ == '__main__':
    main()
