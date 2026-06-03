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

    # ---- و as second radical (و = وَصل+ربط, binding/joining) : hollow/round nuclei ----
    "جو": ("gathered hollow bound within a space", "تَجَمُّعٌ في حَيِّزٍ أجوَفَ مَوصول"),
    "خو": ("rarefied hollow, loosely bound within", "تَخَلخُلٌ رِخوٌ في الأثناءِ مَوصول"),
    "عو": ("a depth-grip looping back, bound", "قَبضٌ حَلقيٌّ يَنعَطِفُ مَوصولًا"),
    "فو": ("a parted opening bound toward a gap", "انفِتاحٌ مَوصولٌ نَحوَ فُرجة"),
    "هو": ("soft breath in a bound void", "نَفَسٌ خَفيفٌ في فَراغٍ مَوصول"),
    "صو": ("a firm seal bound around a form", "إطباقٌ صُلبٌ مَوصولٌ حَولَ هَيئة"),
    "كو": ("pressed gathering rounded and bound", "كَتمٌ مَوصولٌ يُستَدار"),
    "مو": ("a gathered mass loosely bound, wavering in place", "تَجَمُّعٌ مَوصولٌ مُتَرَدِّدٌ في مَكانِه"),
    "زو": ("a thrust gathered and bound together", "اندفاعٌ مَوصولٌ يَجتَمِع"),
    "دو": ("a fixed point bound into a turning round", "ثَباتٌ مَوصولٌ يَدور"),
    "تو": ("a gentle return bound back", "امتدادٌ لطيفٌ مَوصولٌ يَرجِع"),
    "ثو": ("the scattered drawn back and bound together", "مُتَناثِرٌ مَوصولٌ يَلتَئِم"),

    # ---- و as first radical (وَصل+ربط composed with the second charge) ----
    "وق": ("a bound firm settling, weight fixed in place", "وَصلٌ مُحكَمٌ يَستَقِرُّ بِثِقَل"),
    "وس": ("a binding that flows toward, a sustained reaching", "وَصلٌ سَيّالٌ يَتَوَصَّلُ نَحوَ مَطلوب"),
    "وج": ("a binding that lodges in a hollow", "وَصلٌ يَحُلُّ في حَيِّز"),
    "وص": ("a firm binding, joined fast", "وَصلٌ صُلبٌ مُحكَمُ الاشتِباك"),
    "ور": ("a binding that runs and arrives", "وَصلٌ جارٍ يَبلُغ"),
    "وه": ("a binding that loosens and lets pass", "وَصلٌ يَرخو فيَنفَلِت"),
    "وب": ("a binding attached over a surface", "وَصلٌ مُتَمَسِّكٌ يُغَطّي الظاهِر"),
    "وت": ("a binding stretched single and fixed", "وَصلٌ مَمدودٌ مُفرَدٌ ثابِت"),
    "وز": ("a bound thrust held back, weight contained", "وَصلٌ يَكُفُّ الاندِفاعَ ويَزِن"),
    "وط": ("a binding pressed broad and low, settled", "وَصلٌ مُنبَسِطٌ يَستَقِرُّ بِثِقَل"),
    "وك": ("a binding pressed tight, firmly committed", "وَصلٌ مَكتومٌ يُشَدُّ ويُوكَل"),
    "وث": ("a binding densely gathered, made firm", "وَصلٌ مُتَكاثِفٌ يُوثَق"),
    "وذ": ("a binding pierced through and cut into pieces", "وَصلٌ يُنفَذُ فيُقطَعُ قِطَعًا"),
    "وأ": ("a binding brought to a sealed rest", "وَصلٌ يُفضي إلى مَقَرٍّ مَكين"),
    "وي": ("a binding drawn out toward a declared end", "وَصلٌ مُمتَدٌّ نَحوَ عاقِبة"),
    "وش": ("a binding with a fine branching trace", "وَصلٌ بِزِيادةٍ دَقيقةٍ مُنتَشِرة"),
    "وض": ("a binding drawn together heavily, set low", "وَصلٌ مَضمومٌ يوضَعُ بِثِقَل"),

    # ---- ي as first radical (ي = امتداد+لِين+سَريان, gentle directed extension) ----
    "يق": ("a gentle extension settled firm and sure", "امتدادٌ لَيِّنٌ يَستَقِرُّ مُتَيَقِّنًا"),
    "يم": ("a gentle extension gathered soft", "امتدادٌ لَيِّنٌ يَتَجَمَّعُ مُتَّصِلًا"),
    "ين": ("a gentle extension softening to ripeness", "امتدادٌ لَيِّنٌ يَرِقُّ ويَنضَج"),
    "يس": ("a gentle extension flowing easily within", "امتدادٌ لَيِّنٌ يَسري سَهلًا في الباطن"),
    "يت": ("a gentle extension set apart, single", "امتدادٌ لَيِّنٌ يَنفَرِدُ مُستَقِلًّا"),
    "يو": ("a gentle extension bound into a continuous span", "امتدادٌ لَيِّنٌ مَوصولٌ مُتَّصِلُ المَدى"),
    "يب": ("a thin extension drying to stiffness", "امتدادٌ رَقيقٌ يَجِفُّ فيَيبَس"),
    "يأ": ("a gentle extension hardened to a settled edge", "امتدادٌ لَيِّنٌ يَتَأَكَّدُ حِدّةً في النَّفس"),

    # ---- ي as second radical (defective roots; gentle extension composed with the first charge) ----
    "ري": ("a running flow drawn out gently to a limit", "جَريانٌ يَمتَدُّ لَيِّنًا إلى حَدّ"),
    "خي": ("rarefied within, drawn out soft", "تَخَلخُلٌ في الأثناءِ يَمتَدُّ لَيِّنًا"),
    "سي": ("an extending flow drawn out steadily", "سَيَلانٌ يَمتَدُّ مُطَّرِدًا"),
    "مي": ("a gathered mass drawn out and loosened", "تَجَمُّعٌ يَمتَدُّ فيَلين"),
    "بي": ("an attachment drawn out between two points", "اتّصالٌ يَمتَدُّ بَينَ طَرَفَين"),
    "ضي": ("a dense drawing-together stretched thin and outward", "ضَمٌّ بِثِقَلٍ يَمتَدُّ فيَنبَسِط"),
    "طي": ("a heavy spread drawn out, folding or rising", "انبساطٌ ثَقيلٌ يَمتَدُّ طَيًّا أو ارتِفاعًا"),
    "غي": ("a concealing depth drawn out till it shifts or covers", "غَورٌ يَمتَدُّ فيُغَيِّبُ أو يُحَوِّل"),
    "كي": ("pressed gathering drawn out, turned and worked", "كَتمٌ يَمتَدُّ يُدارُ ويُعالَج"),
    "زي": ("a thrust drawn out as an added increase", "اندفاعٌ يَمتَدُّ زِيادةً مُضافة"),
    "جي": ("a gathered hollow drawn out within", "حَيِّزٌ أجوَفُ يَمتَدُّ في الباطن"),
    "شي": ("a branching spread drawn out gently", "انتشارٌ يَمتَدُّ مُتَفَرِّقًا لَيِّنًا"),
    "دي": ("a fixed point drawn out, encircling or enduring", "ثَباتٌ يَمتَدُّ دَورًا أو دَوامًا"),
    "تي": ("a gentle return drawn out, recurring", "امتدادٌ لَيِّنٌ يَرجِعُ مُتَرَدِّدًا"),
    "ني": ("an inner resonance drawn out to attainment", "رَنينٌ يَمتَدُّ فيَنال"),
    "قي": ("a firm settling drawn out to a resting place", "إحكامٌ يَمتَدُّ إلى مَقَرٍّ مُؤَقَّت"),
    "ذي": ("a fine bringing-out drawn out till it disperses", "إبرازٌ يَمتَدُّ حتى يَشيعَ ويَتَفَرَّق"),
    "هي": ("a soft breath drawn out into a slack void", "نَفَسٌ خَفيفٌ يَمتَدُّ في فَراغٍ مُنهال"),

    # ---- hamza as second radical (ء = تَأكيد+قَطع, affirmation/decisive cut) ----
    "بأ": ("an attachment cut inward, opening into depth", "اتّصالٌ يُقطَعُ نافِذًا إلى الجَوف"),
    "سأ": ("a flow cut to draw out what is held", "سَيَلانٌ مَقطوعٌ يَستَخرِجُ المَطلوب"),
    "ذأ": ("a fine bringing-out cut sharply, thrusting or shrinking", "إبرازٌ مَقطوعٌ يَندَفِعُ أو يَتَحاقَر"),
    "مأ": ("a gathering affirmed into a holding breadth", "تَجَمُّعٌ مُؤَكَّدٌ يَتَّسِعُ ويُمسِك"),
    "شأ": ("a branching affirmed, fine offshoots within", "انتشارٌ مُؤَكَّدٌ بِشُعَبٍ دَقيقةٍ في الأثناء"),
    "جأ": ("a gathering cut forth, bursting from its source", "تَجَمُّعٌ يَنبَثِقُ بِقوّةٍ من مَصدَرِه"),
    "لأ": ("an extending attachment affirmed, concentrated bright", "تَعَلُّقٌ مُؤَكَّدٌ يَتَرَكَّزُ صَفاءً ولَمَعانًا"),
    "دأ": ("a fixity affirmed into persistent drive", "ثَباتٌ مُؤَكَّدٌ يُداوِمُ بِدَفع"),
    "ضأ": ("a heavy drawing-together affirmed, soft density within", "ضَمٌّ مُؤَكَّدٌ بِكَثافةٍ رِخوةٍ في الباطن"),
    "ضَ": ("rays parting from a thing, dispersing density", "أشِعّةٌ تَنفُذُ فتُزيلُ كَثافةَ الظِّل"),

    # ---- geminate / identical-letter nuclei recorded without a seed reading ----
    "دك": ("a fixed pressing, sealed down till it caves", "ضَبطٌ يَضغَطُ مَكتومًا حتى يَتَداكّ"),
    "هه": ("a breath upon breath, an expected void", "نَفَسٌ على نَفَسٍ، فَراغٌ مُعتاد"),
    "فظ": ("a parting that pierces harsh and tight", "نَفاذٌ يَشُقُّ بِغِلَظٍ وضِيق"),
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
