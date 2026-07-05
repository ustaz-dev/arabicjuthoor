# Pre-registration: new branch rosters (Old Persian, Greek, Latin) and the gradient prediction

**Date registered:** 2026-07-05 (committed before any dictionary work on these three branches began; the git timestamp of this file is the proof)
**Framework:** the fixed 28 charges, the four-bar rubric with `rule` (regular correspondence) and `route` (inherited / reverse-borrowing / wanderwort) fields from day one
**Baseline:** the skeleton chance baseline (05-audits/2026-07-02) computed per roster

## العيّنةُ مُعلَنةٌ قبلَ فتحِ أيِّ قاموس

وحدةُ الدليلِ في هذا المشروعِ نِسبةٌ على عيّنةٍ مُصرَّحٍ بها ضدَّ خطِّ المصادفة، لا قائمةٌ منتقاة. لذلك تُعلَنُ العيّنةُ هنا قبلَ العمل، وتُنشَرُ الروستراتُ كاملةً بمردوداتِها، ولا يُعنوَنُ أيُّ قسمٍ بعددِ ما وُجِد.

## The declared sample (identical frame for all three branches)

The same core-semantic-field frame used for the Egyptian roster, anchored on the Swadesh-207 concept list plus the fields the project reads deepest:

1. Pronouns and deixis (I, you, we, this, that, who, what)
2. Kinship (mother, father, son, daughter, brother, sister)
3. Body (eye, ear, tongue, tooth, heart, hand, foot, bone, blood, horn)
4. Numbers (one through ten, hundred)
5. Nature (water, fire, earth, sky, sun, moon, star, mountain, night, day)
6. Basic acts (eat, drink, sleep, die, come, go, give, take, see, hear, say, know)
7. Core qualities (big, small, long, new, old, good)
8. The sacred/social lexicon where attested (king, name, house, road, peace)

Every concept in the frame is looked up for all three branches; every worked pair is published with its verdict, including the declined ones. Pruning is per-pair (no attested form, or no honest reading), never per-result.

## Sources (attested forms only)

- **Old Persian:** Kent, *Old Persian: Grammar, Texts, Lexicon*; Avestan support from Bartholomae where Old Persian is unattested.
- **Greek:** LSJ (Liddell-Scott-Jones).
- **Latin:** OLD / Lewis & Short.
- Arabic side: Lisān al-ʿArab / Tāj al-ʿArūs, as everywhere in the project.

## Pre-registered prediction (the gradient test)

The one-tongue reading predicts an **ordering**, declared here before any pair is worked:

1. **Old Persian (Indo-Iranian) reads cleaner than Greek and Latin.** The Indo-Iranian branch already reads at 93% top-tier on the worked Sanskrit set; Old Persian, its sister, should land nearer that end than the ~25% calibrated Greek/Latin region.
2. **All three land above their skeleton chance baseline** at the declared sample size.
3. **The deep-core fields (pronouns, kinship, numbers, body) read cleaner than the sample average** in every branch, as they did in Egyptian (80% deep-core vs 55% overall).

If the ordering fails, that is reported as measured; the prediction is falsifiable and that is its value. If it holds, the preservation gradient has passed a declared-in-advance test on three new branches.

## Per-entry fields (machine-checkable from day one)

`id, arabic, <branch form>, gloss, verdict, rule, route, category` where `rule` names the regular correspondence the pair obeys (or `irregular`), and `route` is one of `inherited-trace / reverse-borrowing / wanderwort`. `check_rosters.py` will be extended to validate both fields.
