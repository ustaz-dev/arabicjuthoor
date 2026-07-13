#!/usr/bin/env python3
"""Roster integrity check: recompute every cross-linguistic roster's verdict_distribution
from its actual entries and assert the header matches. Catches the figure-drift the team has
had to fix by hand (stale headers, mislabelled verdicts). Run before every commit that touches
04-cross-linguistic/data/*.json. Exit code 1 on any mismatch.

Usage:  python scripts/layer_2/check_rosters.py
"""
import json, sys, glob, os
from collections import Counter
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA = os.path.join(ROOT, '04-cross-linguistic', 'data')

ALLOWED = {
    'PERFECT', 'STRONG', 'PARTIAL', 'PROVISIONAL',
    'PROTO-FAMILY', 'PROTO-AFRO-ASIATIC', 'DUAL-FACE', 'PARALLEL-STEMS', 'DIVERGED-STEMS',
    'CONVERGENT', 'FLOOR-TRACE', 'LOANWORD', 'RETRACTED',
}
TOP_TIER = {'PERFECT', 'STRONG', 'PROTO-FAMILY', 'PROTO-AFRO-ASIATIC', 'DUAL-FACE'}
# rule/route fields (pre-registration-branch-rosters.md): enforced on any roster that carries them
ROUTES = {'inherited-trace', 'reverse-borrowing', 'wanderwort'}

def main():
    problems = []
    files = sorted(glob.glob(os.path.join(DATA, '*.json')))
    for f in files:
        d = json.load(open(f, encoding='utf-8'))
        if 'entries' not in d:
            continue
        name = os.path.basename(f)
        entries = d['entries']
        actual = Counter(e.get('verdict') for e in entries)
        # 1. count header
        if 'count' in d and d['count'] != len(entries):
            problems.append(f"{name}: header count={d['count']} but {len(entries)} entries")
        # 2. verdict_distribution header
        decl = d.get('verdict_distribution')
        if decl is not None and dict(actual.most_common()) != dict(Counter(decl).most_common()):
            problems.append(f"{name}: verdict_distribution stale. header={decl} actual={dict(actual.most_common())}")
        # 3. unknown verdict labels
        bad = set(actual) - ALLOWED
        if bad:
            problems.append(f"{name}: unknown verdict label(s) {bad}")
        # 4. id uniqueness
        ids = [e.get('id') for e in entries if 'id' in e]
        if len(ids) != len(set(ids)):
            problems.append(f"{name}: duplicate ids")
        # 5. rule/route integrity: if ANY entry carries the fields, EVERY entry must
        has_rr = any(('rule' in e or 'route' in e) for e in entries)
        if has_rr:
            for e in entries:
                eid = e.get('id', '?')
                rule = e.get('rule')
                if not isinstance(rule, str) or not rule.strip():
                    problems.append(f"{name}: entry {eid} missing/empty rule")
                route = e.get('route')
                if route not in ROUTES:
                    problems.append(f"{name}: entry {eid} bad route {route!r}")
        top = sum(v for k, v in actual.items() if k in TOP_TIER)
        print(f"  OK  {name:28s} {len(entries):4d} entries · top-tier {top}/{len(entries)} = {round(top/len(entries)*100)}% · {dict(actual.most_common())}")

    print()
    if problems:
        print("FAIL — %d roster problem(s):" % len(problems))
        for p in problems:
            print("  ✗", p)
        return 1
    print("PASS — all rosters internally consistent.")
    return 0

if __name__ == '__main__':
    sys.exit(main())
