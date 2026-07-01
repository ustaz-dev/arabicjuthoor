# Cross-linguistic rigor upgrade: from permissive substitution to regular correspondence

**Author:** Yassine Temessek · Temessek for Research, Publishing & Training
**Status:** Proposal · not yet implemented · written before any change to the rosters
**Scope:** the cross-linguistic layer only (the internal-Arabic engine is untouched)

## خلاصة

قوانينُ خشيمِ التِّسعةُ التي يقومُ عليها الضابطُ الأوّلُ للنَّظائرِ هي «إجازاتٌ» تسامحيّة: تقولُ إنّ هذا الصوتَ *قد* يُبدَلُ بذاك. والتسامحُ يُدخِلُ إيجابيّاتٍ كاذبة، وهو أضعفُ ما تُسنَدُ إليه أطروحةُ اللسانِ الواحد. هذه الورقةُ تقترحُ ثلاثَ ترقياتٍ تُقوّي الأطروحةَ لا تُضعِفُها: (1) جداولُ تطابُقٍ **منتظم** لكلِّ فرعٍ بدلَ الإبدالِ المُجاز، لأنّ الانتظامَ نفسَه هو توقيعُ الانحدار؛ (2) **خطُّ أساسِ المصادفة** يقيسُ كم زوجٍ عشوائيٍّ يطابقُ تحتَ نفسِ القوانين، فيفصلُ الإشارةَ عن الضجيج؛ (3) **فلترُ الاستعاراتِ المعروفة** يميّزُ الأثرَ الموروثَ من الكلمةِ المُستعارة. لا تغييرَ في المحرّكِ الداخليِّ للعربيّة، ولا في الدرجات، قبلَ تنفيذِ هذا.

## The problem, stated plainly

The four-bar rubric's first bar (consonant-skeleton match) currently rests on Dr. Ali Fahmi Khshim's nine sound-substitution laws (plus the tenth, ط↔T, that our corpus surfaced). These laws are *permissive*: each says a given Arabic consonant *may* correspond to a given foreign one. Permissiveness is the weak point a comparative linguist attacks first, because a generous substitution set can pair almost any two short skeletons by chance.

The irony is that our own thesis already points to the fix. In the Aramaic block we write that "the regularity of the shifts is itself the signature of a single language diverging, not a scatter of coincidences." That is exactly right, and it is the standard of the comparative method: **regular** correspondence, not permitted substitution, is what proves descent. Adopting it does not make the claim more cautious. It makes the bold claim, one original tongue, provable on the terms that the field itself accepts.

So this is not a retreat toward mainstream skepticism. It is the sharpest available weapon *for* the descent reading: replace "these two consonants are allowed to swap" with "these two consonants correspond in this environment every time, and here are the cases."

## Upgrade 1 · Regular sound-correspondence tables, per branch

Replace the single permissive substitution list with a predictive correspondence table for each branch, drawn from the established reconstructions and stated as environment-conditioned rules rather than free swaps.

- **Semitic sisters** (Hebrew, Aramaic, Akkadian): the interdental and guttural correspondences are already regular and well documented (ث↔š↔t, ḍ↔ʿ, guttural loss in Akkadian). Formalize them as a table with the conditioning environment, so each Tier-A Semitic pair cites the rule it obeys.
- **Indo-European**: use the classical sound laws (Grimm, Grassmann, Verner) so that a claimed Arabic↔IE correspondence is tied to a stated, regular shift rather than an ad-hoc allowance. Where the correspondence is *not* regular, the pair is flagged, not hidden.
- **Afro-Asiatic super-family** (Egyptian): anchor to the Orel-Stolbova and Ehret correspondence sets, again with the conditioning environment recorded.

Deliverable: a `correspondences/` table per branch, and a new roster field `rule` on every cross-linguistic entry naming the regular correspondence it satisfies (or `irregular` if it does not). Pairs that only survive under a permissive swap, not a regular rule, drop from top tier to a watch list until a regular account is found.

## Upgrade 2 · A chance baseline (null model)

For every claimed skeleton match, we should know how often the same match would arise by chance under the same rules. Without this number a reader cannot tell signal from noise, and a reviewer will not accept the list.

- Build a null distribution: draw random Arabic roots and random target-language words, apply the same correspondence rules, and measure the rate of "matches" at each skeleton length. Short skeletons (two consonants, e.g. G-M for Gemini) will show a high chance rate; long ones (Q-M-S, N-J-L) a low one.
- Report, per pair, a **signal-over-chance** figure, and per branch, an aggregate. We already have fragments of this instinct (the 4.4x-over-chance coherence result, the per-branch Pearson correlations); this generalizes it to the headline cognates.
- Consequence: short-skeleton pairs must clear a higher semantic and dual-family bar to survive, because their phonetic match is cheap. This is precisely the honest filter the current rubric lacks.

Deliverable: a `chance_rate` and `signal_over_chance` field per entry, and a one-line null-model note under the Tier-A table on the dashboard.

## Upgrade 3 · A known-borrowing (Wanderwort) screen

Some pairs on the current list have a documented borrowing route on the Indo-European side (copy via Latin copia, genie via Latin genius, syrup which is itself an Arabic-origin word). Descent and borrowing are different claims, and conflating them is what invites the "cherry-picking" charge.

- Screen every Tier-A pair against the standard borrowing literature and etymological dictionaries. Tag each as `inherited-trace`, `reverse-borrowing` (Arabic into the other, which supports our direction), or `wanderwort` (a travelled culture-word whose direction is contested).
- Keep reverse-borrowings, they help the thesis, but label them honestly. Move contested Wanderwörter to their own clearly marked row, exactly as the four `‡` pairs are now footnoted on the dashboard.

Deliverable: a `route` field per entry with those three values, and the contested pairs visually separated from the inherited-trace core.

## How this strengthens the vision, not weakens it

The strong core of the list, the kinship-body-number pairs with clean witnesses in both families (qarn/horn, thawr/taurus, sabʿ/seven, salām/shalom), will pass all three upgrades and come out *stronger*, because they will now be backed by regular correspondence, a low chance rate, and a clean inheritance route. The weak pairs will be honestly quarantined. The net effect is a shorter, harder, unassailable core, which is a better foundation for the one-original-tongue claim than a longer list a skeptic can wave away.

## Order of work (when approved)

1. Build the per-branch regular-correspondence tables and add the `rule` field to the Semitic rosters first (they are already the most regular).
2. Implement the null model and add `chance_rate` / `signal_over_chance` to the Indo-European Tier-A entries, where chance is the real risk.
3. Run the borrowing screen and add the `route` field across all Tier-A entries.
4. Re-rank the dashboard Tier-A table by the new evidence, and rewrite the four-bar section to lead with regularity.

Nothing here changes the internal-Arabic engine (28 charges, 453 nuclei, 11 modes, 2,285 roots) or any existing grade. It only hardens how cross-linguistic pairs earn their place.
