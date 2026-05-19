# Opening the door · the quadriliteral and quintiliteral grammar

> The Arabic version is at [`quad-quint-grammar-roadmap-ar.md`](quad-quint-grammar-roadmap-ar.md).
>
> Status: **research-design document, not a finished theory.** This file names the gap, surveys the empirical landscape, proposes two structural extensions of the eleven-mode operative grammar, works through ten attested cases, and sets the research plan to formalise the framework end-to-end. Calling it "opening the door" is deliberate: the door is open here, not walked through.

## Why this layer is needed

The eleven-mode operative grammar in `lv2-operative-grammar.md` reads every Arabic **trilateral** root cleanly: (binary nucleus L1·L2) operates on (L3-charge as material) via one of eleven native modes plus a LOANWORD label. 2,285 of 2,288 trilaterals fit at 100% native composition.

Two layers above this remain only partially formalised:

- **Quadriliterals** (four-consonant roots) — e.g. زَلْزَل, دَحْرَج, قَنْطَر, نَمْرَق, جَهَنَّم.
- **Quintiliterals** (five-consonant roots) — e.g. زَنْجَبِيل, سَلْسَبِيل, عَنْدَلِيب, سَفَرْجَل, خَنْدَرِيس.

The framework currently sketches their behaviour with the formula *binary on L3, then ternary on L4* but does not specify which of the eleven modes applies at the higher levels, nor how the modes compose when the structure runs two levels deep. This is the gap the loanword audit named honestly when it left زَنْجَبِيل and مَجوس in the **UNRESOLVED** category: not because the borrowing claim was confirmed, but because the **native grammar that would settle the question is not yet written**.

This document opens that door.

## The empirical landscape

In Jabal's corpus, quadriliterals are a small but structured minority of all roots:

| Root length | Approx. count in the catalogue | Notes |
|---|---:|---|
| Trilateral (3 consonants) | ~2,288 | The canonical body; 11-mode grammar reads 2,285 of these natively. |
| Quadriliteral (4 consonants) | ~150–200 | Many are reduplicated (XYXY, XYYX); some are genuine 4-root compounds; a handful are borrowing candidates. |
| Quintiliteral (5 consonants) | ~20–30 | Mostly inherited noun stems; common in flora and fauna (plant names, animal names, ornamental terms). |
| Six+ consonants | a handful | Borrowings, compounds, or onomatopoeia. |

Two structural sub-families inside the quadriliterals are already obvious from the form alone:

**Reduplicated quadriliterals (XYXY or XYYX).** زَلْزَل = ز·ل·ز·ل = (زل)(زل). وَسْوَس = و·س·و·س = (وس)(وس). دَمْدَم = د·م·د·م = (دم)(دم). سَحْسَح = س·ح·س·ح = (سح)(سح). For these, the framework already has a partial reading: the **INTENSIFY** mode of the eleven-mode grammar is "doubled or amplified L3". Reduplicated quadriliterals are INTENSIFY applied not to a third letter but to a whole second binary nucleus, which is the binary nucleus repeated. The semantic of *to shake-and-shake-and-shake* (زلزل as earthquake) is exactly *the binary زل intensified by being doubled into itself*. **This sub-family is already covered by the eleven-mode grammar with no extension; we just need to be explicit that INTENSIFY at the quadriliteral level reads as binary-on-itself.**

**Genuine quadriliterals (non-reduplicated, four distinct consonants).** قَنْطَر, دَحْرَج, نَمْرَق, جَهَنَّم, زَخْرَف, عَسْكَر. These are the cases that need the extension proper. They decompose as (binary B1)·(binary B2), with B1 the agent binary and B2 the material binary. The eleven modes operate, but at the binary-on-binary level instead of binary-on-letter.

For quintiliterals, the dominant pattern is **trilateral nucleus + binary closure** or **binary + trilateral + closure** depending on the root. زَنْجَبِيل = ز·ن·ج·ب·ي·ل can be read as (زن)·(جب)·(يل) — three binaries stacked — or as (زنج) compound + (بيل) closure. The framework needs to specify which decomposition applies and on what evidence.

## Proposed structural extension

The eleven-mode grammar's central move at the trilateral level is:

> (binary nucleus L1·L2) operates on (L3-charge as material) via mode M.

The proposed extension generalises this to the **binary-on-binary** level for quadriliterals, and to the **two-step composition** level for quintiliterals.

### Quadriliteral extension · binary on binary

For a four-consonant root L1·L2·L3·L4:

> (binary nucleus B1 = L1·L2) operates on (binary B2 = L3·L4 read as composite material) via one of the eleven modes M, where the mode is selected by the *interface charge* between L2 (the trailing letter of B1) and L3 (the leading letter of B2).

The reading proceeds in three steps:

1. **Identify the agent binary B1** as L1·L2. The same binary nucleus catalogue used at the trilateral level applies.
2. **Identify the material binary B2** as L3·L4. This too should be in the binary catalogue (or be a legitimate "promoted" binary from the 54 binaries that appear inside trilaterals but were not catalogued).
3. **Read the interface** L2·L3 as a "joiner binary" that selects the mode. The interface determines whether B1 carries B2, holds B2, releases B2, blocks B2, channels B2, and so on — exactly the same eleven modes from the trilateral grammar, now operating one level up.

Worked example — قَنْطَر (qanṭara, "to build a bridge"):

- L1·L2·L3·L4 = ق·ن·ط·ر
- B1 = ق·ن (a documented binary nucleus: *closing-fold, enclosing*, as in قَنَع, قَنَّ)
- B2 = ط·ر (a documented binary: *spreading-flow, extending-edge*, as in طَرَح, طَرَف)
- Interface = ن·ط (a documented binary: *resonance-spreading, the ringing extension*)
- Reading: the **CHANNEL** mode of the eleven-mode grammar applied at the binary-on-binary level. *The closing-fold (ق·ن) channels the spreading-edge (ط·ر) into a directed extension* — which is exactly what a bridge does: it folds an enclosure across a gap to channel the extending traffic. The Arabic *qanṭara* (bridge) and *muqanṭarah* (the bridged, the spanned) follow this reading without forcing.

Worked example — دَحْرَج (daḥraja, "to roll"):

- L1·L2·L3·L4 = د·ح·ر·ج
- B1 = د·ح (a documented binary: *firm-warm push*, as in دَحَا)
- B2 = ر·ج (a documented binary: *running-gathering, the recurring assembly*, as in رَجَّ, رَجَع)
- Reading: the **CARRY** mode at the binary-on-binary level. *The firm-warm push (د·ح) carries the running-recurrence (ر·ج) forward* — which is rolling. An object rolls when a fixed-warmly push imparts continuous recurring motion to it.

Worked example — نَمْرَق (numruq, "patterned cushion"):

- L1·L2·L3·L4 = ن·م·ر·ق
- B1 = ن·م (a documented binary: *quiet-resonant-mass*, as in نَمَّ)
- B2 = ر·ق (a documented binary: *thin-fine-flowing*, as in رَقَّ, الرَّقّ)
- Reading: the **HOLD** mode at the binary-on-binary level. *The quiet-resonant-mass (ن·م) holds the thin-fine-flowing surface (ر·ق)* — a cushion is precisely a held mass with a thin patterned cover.
- Cross-check with the loanword audit: the same word reads natively as ن-م-ر (spotted) + ق, the trilateral-plus-augment path. Both readings are consistent and converge on the same semantic. The quadriliteral grammar gives one path; the trilateral-plus-augment reading gives the same word a parallel native reading. Two clean roads, no forcing — which is what a real framework should do.

### Quadriliteral extension · trilateral plus augment

A second valid path for some quadriliterals is **trilateral plus augment**: read the first three letters as a standard trilateral under the eleven-mode grammar, then read the fourth letter as a modifier that extends the trilateral's semantic in a known direction.

This is analogous to the Arabic *augmented verbal forms* (Forms II–X) which add letters to a trilateral root with specific semantic functions (intensification, causation, reflexivity, etc.). The proposal is that the **same augment functions exist at the noun level for quadriliteral nouns**.

Worked example — جَهَنَّم (Jahannam):

- L1·L2·L3·L4 = ج·ه·ن·م
- Trilateral nucleus = ج·ه·ن (a candidate reading: *the gathering-presence-of-resonance*, the manifest-domain that holds resonance)
- Augment = م (the gathering-into-mass closure)
- Reading: the trilateral *the manifest-domain-of-held-resonance* augmented by م into *the gathered, contained, manifest domain* — the bounded, confining place. This matches the Quranic semantic of the Hellfire as the bounded confining place.
- Cross-check with the loanword audit's CONVERGENT verdict: Hebrew *Gēhinnom* (Valley of Hinnom) and Arabic جهنّم share the consonant skeleton, and both readings (place-name borrowing + native compositional reading) can be true simultaneously. The quadriliteral grammar now gives the native reading its formal place.

### Quintiliteral extension · stacked composition

For five-consonant roots, the proposed reading is a **stack of binaries** with the composition operating in sequence:

> (B1 = L1·L2) operates on (B2 = L3·L4 as intermediate composite) → (B3 = L4·L5 as final material)

The reading is genuinely sequential: the first binary acts on the second, the second's product becomes the material on which the third operates, and so on.

Worked example — سَلْسَبِيل (salsabīl, the paradise fountain):

- L1·L2·L3·L4·L5 = س·ل·س·ب·ي·ل
- Decomposition: (سل = the smooth-extending) → (سب = the smooth-released flow) → (يل = the gently-extending stream)
- Reading: *the smoothly-extending-into-released-flow-that-gently-streams* — a perfectly-flowing fountain that issues without interruption. Already a coherent native reading.

Worked example — زَنْجَبِيل (zanjabīl, ginger):

- L1·L2·L3·L4·L5 = ز·ن·ج·ب·ي·ل
- Decomposition path A (binary stack): (زن = the sharp-resonance) → (جب = the gathering-attached) → (يل = the gently-extending). The reading would be *the sharp-resonant-gathering-that-extends-gently* — a strong-but-warm spice that lingers. Coherent, defensible, but admittedly post-hoc-feeling for a spice name.
- Decomposition path B (compound name): زنج = a recognised Arabic ethnic-geographic term (the people of Zanj / East Africa), بيل as an attribute or container. The reading would be *the Zanj-origin attribute* — a spice known from the Indian-Ocean trade route via Zanj.
- Verdict for now: **the quintiliteral grammar permits a native compositional reading**, but the framework has not yet settled which decomposition is canonical. This is a place where the proposed extension opens the path without forcing the answer; the empirical evidence will need to choose.

Worked example — سَفَرْجَل (safarjal, quince):

- L1·L2·L3·L4·L5 = س·ف·ر·ج·ل
- Decomposition: (سف = the parting-flow) → (رج = the running-gathering) → (جل = the gathered-extending)
- Reading: *the parting-flow-that-gathers-as-it-extends* — a fruit with a complex sweetness that opens layered on the tongue. Defensible.

## What this extension does not yet resolve

The extension above is a **research proposal**, not a settled grammar. Three open questions remain:

1. **Which decomposition path applies when?** For نَمْرَق we showed two paths (binary-on-binary and trilateral-plus-augment) converging on the same reading. For زَنْجَبِيل we showed two paths (binary-stack and compound-name) that need empirical settling. The framework needs an explicit rule, derived from the data, for which decomposition path takes precedence in any given quadriliteral or quintiliteral.

2. **What are the augment-letter functions at the noun level?** At the verbal level, Forms II–X have known semantic functions (intensification, causation, etc.). The proposed quadriliteral-as-trilateral-plus-augment reading needs an analogous catalogue at the noun level. The empirical work would be: for every quadriliteral that reads cleanly as trilateral-plus-augment, what is the semantic function of the augment letter? Does it depend on the augment letter's charge, on its position (final, infixed), or on the trilateral it augments?

3. **How does the mode-selection logic generalise?** At the trilateral level, the mode is selected by the L3-charge interacting with the binary. At the quadriliteral level, the proposal above suggests the interface charge (L2·L3) selects the mode. This needs to be tested against the catalogue: does the interface-charge-selects-mode rule predict the right mode for every quadriliteral, or is it incomplete?

## What this extension can do today

Even unfinished, the proposal lets us do three things the framework couldn't do cleanly before:

- **Read quadriliterals natively** with one of two principled paths. The 150–200 quadriliterals in Jabal's catalogue stop being a residue; they become a class with a documented grammar (even if the grammar has open questions).
- **Settle some "loanword" claims** that depended on the framework being silent on quadriliterals. زَخْرَف, نَمْرَق, جَهَنَّم all become clearly readable natively. The audit's UNRESOLVED count for these drops to zero.
- **Generate predictive tests.** With a proposed grammar, we can predict what undiscovered or hypothetical quadriliteral compositions would mean, and check those predictions against the language's actual usage. This is the same generative move the lexical-gaps test made at the trilateral level.

## Research plan

A complete formalisation of this layer needs four work items, in order:

1. **Catalogue the quadriliteral roots.** Extract from Jabal's lexicon every quadriliteral, with its existing definition and Quranic / classical attestation. Estimated count: 150–200 entries. Output: a structured JSONL or table parallel to the 453-nucleus catalogue.

2. **Apply both decomposition paths to each quadriliteral.** For every entry, attempt the binary-on-binary reading and the trilateral-plus-augment reading. Record which path yields the cleaner reading and on what evidence. This produces the empirical basis for the precedence rule.

3. **Catalogue the augment-letter functions.** From the trilateral-plus-augment entries in step 2, induce the semantic functions of each augment letter (ر, ن, ل, م, ج, q, etc.) by its position and by the trilateral it augments. This produces the augment-function table.

4. **Test mode-selection.** For each binary-on-binary entry from step 2, check whether the interface-charge-selects-mode rule predicts the right mode. Record the success rate. If high (>85%), promote the rule to a confirmed extension; if lower, refine.

The same protocol scales to quintiliterals with a stacked-binary catalogue, but the quintiliteral set is smaller (~20–30) and can wait until the quadriliteral grammar is settled.

## Connection to the loanword audit

The two UNRESOLVED cases from the [Quranic loanword audit](../04-cross-linguistic/quranic-loanword-audit.md) — زَنْجَبِيل and مَجوس — both involve the kind of higher-than-trilateral compositional structure this document addresses. When the quadriliteral and quintiliteral grammars are formalised, those two cases get re-tested under the new framework. The expectation, based on the worked examples above, is that the native reading will become defensible for at least one of them and the UNRESOLVED count will drop further.

The pattern across the framework as a whole is consistent: every honest gap the methodology names gets a research path, and the path closes the gap rather than skirting it. This is what a falsifiable framework looks like when it is taken seriously.

---

_See also: [`lv2-operative-grammar.md`](lv2-operative-grammar.md) for the trilateral grammar this layer extends, [`04-cross-linguistic/quranic-loanword-audit.md`](../04-cross-linguistic/quranic-loanword-audit.md) for the cases that motivated the extension, and [`03-scholar-extracts/lexical-gaps-generative-test.md`](../03-scholar-extracts/lexical-gaps-generative-test.md) for the parallel generative experiment at the trilateral level._
