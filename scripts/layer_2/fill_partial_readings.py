#!/usr/bin/env python3
"""Fill the missing binary_reading_en/ar on the 302 partial Layer-2 records.

The 302 partials reduce to ~80 distinct WEAK-letter nuclei (أ/و/ي/ء as a radical) —
the hollow / hamzated / defective roots the manual batches left for last. Neither the
results file nor the charge-only dossiers cover them, so each nucleus reading is DERIVED
from the two fixed letter-charges and ANCHORED to the recorded jabal_axial of its roots.

Charge anchor for this batch:  أ «تَأكيد + ابتِداء» = originating affirmation / sustained onset,
composed with the second radical's charge.

Safety: fills BLANKS ONLY (never overwrites a populated reading); writes a .bak first;
atomic replace. Re-run scripts/layer_2/audit_partial_records.py afterwards to verify.
"""
from __future__ import annotations
import json, os, sys, shutil
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "computational" / "data" / "layer_2_results_v2.jsonl"

# nucleus -> (binary_reading_en, binary_reading_ar)
# Each reading is the seed (L1·L2); the trilateral specifics come from L3 + mode.
READINGS = {
    # ---- أ-group : أ = originating affirmation / sustained onset ----
    "أب": ("originating attachment, affirmed holding", "اتّصالٌ مُبتَدأٌ راسخ"),
    "أت": ("affirmed extension reaching arrival", "امتدادٌ مُؤَكَّدٌ يَبلُغ"),
    "أح": ("affirmed enclosing, contained wholeness", "إحاطةٌ مُؤَكَّدةٌ جامِعة"),
    "أخ": ("affirmed bond drawn from one source", "صِلةٌ مُؤَكَّدةٌ من أصلٍ ممتَدّ"),
    "أد": ("affirmed fixity, settled enablement", "ثَباتٌ مُؤَكَّدٌ مُمَكَّن"),
    "أذ": ("affirmed fine piercing brought outward", "نَفاذٌ لطيفٌ مُؤَكَّدٌ يَبرُز"),
    "أر": ("affirmed running flow drawn to a knot", "جَرَيانٌ مُؤَكَّدٌ يُعقَد"),
    "أز": ("affirmed thrust, intensifying drive", "اندفاعٌ مُؤَكَّدٌ يَشتَدّ"),
    "أش": ("affirmed outward spread to sharp edges", "انتشارٌ مُؤَكَّدٌ إلى أطرافٍ حادّة"),
    "أص": ("affirmed firm sealing, rooted fastness", "إطباقٌ مُؤَكَّدٌ راسخ"),
    "أك": ("affirmed pressed closure, grinding shut", "كَتمٌ مُؤَكَّدٌ ضاغطٌ قاطع"),
    "أل": ("affirmed extending attachment", "تَعَلُّقٌ مُؤَكَّدٌ مُمتَدّ"),
    "أم": ("affirmed gathering, originating mass", "تَجَمُّعٌ مُؤَكَّدٌ مُؤَصَّل"),
    "أه": ("affirmed soft interior passing", "نَفَسٌ لطيفٌ مُؤَكَّدٌ يَسوغ"),
}

def main() -> int:
    if not RESULTS.exists():
        print(f"ERROR: {RESULTS} not found", file=sys.stderr); return 1
    recs = [json.loads(l) for l in RESULTS.read_text(encoding="utf-8").splitlines() if l.strip()]

    filled = 0
    touched_nuclei = set()
    still_blank = set()
    for r in recs:
        en = (r.get("binary_reading_en") or "").strip()
        ar = (r.get("binary_reading_ar") or "").strip()
        if en and ar:
            continue
        b = r.get("binary")
        if b in READINGS:
            r["binary_reading_en"], r["binary_reading_ar"] = READINGS[b]
            r["binary_reading_source"] = "charge-derived, jabal-anchored (weak-nuclei batch)"
            r["needs_binary_reading"] = False
            filled += 1
            touched_nuclei.add(b)
        else:
            still_blank.add(b)

    # backup + atomic write
    shutil.copy2(RESULTS, RESULTS.with_suffix(RESULTS.suffix + ".bak"))
    tmp = RESULTS.with_suffix(RESULTS.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        for r in recs:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
        f.flush(); os.fsync(f.fileno())
    tmp.replace(RESULTS)

    print(f"filled {filled} records across {len(touched_nuclei)} nuclei: {sorted(touched_nuclei)}")
    print(f"remaining blank nuclei: {len(still_blank)} -> {sorted(still_blank)}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
