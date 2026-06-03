# Session integrity audit — the cross-linguistic expansion

**Date:** 2026-05-24
**Scope:** audit everything added this session (new tests, words, docs, UI) for integrity, honest grading, and presentation consistency.

## What was added this session — the inventory

### ✅ Confirmed & committed (meets the honesty bar)

| Artifact | Count | Top-tier | Status |
|---|--:|--:|---|
| **Afro-Asiatic · Arabic ↔ Ancient Egyptian** (`afro-asiatic-200.json`) | 324 | 55% | ✅ vetted, committed |
| **Semitic sister · Arabic ↔ Hebrew** (`hebrew-cognates.json`) | 219 | 84% | ✅ committed |
| **Semitic sister · Arabic ↔ Aramaic** (`aramaic-cognates.json`) | 96 | 97% | ✅ committed |
| Second-attack audit (re-cracked the "didn't work" pile) | 79 re-examined | — | ✅ committed |
| Rounds 3–24 mining docs | — | — | ✅ committed |
| **Why the shared roots mean what they mean** (the phenomenological reading — the framework's actual family-level contribution) | ~20 roots | — | ✅ committed |
| Honest reframe: "the Semitic siblings are the baseline, not the proof" | — | — | ✅ committed |
| `afro-asiatic.html` interactive browser | 324 rows | — | ✅ committed, in sync |

These are internally consistent and honestly graded (a real mix of PERFECT / STRONG / PARTIAL / PROVISIONAL, not a uniform inflation).

### ⚠️ Found wrong — and fixed in this audit

**1. 100 bulk-generated Coptic entries inflated the Afro-Asiatic roster (324 → 424).**
A bulk-exploration pass (`explore_coptic_sanskrit.py`) appended 100 entries (ids 325–424) to the confirmed Egyptian dataset. **Every one was graded STRONG**, every one was category `coptic`, and **many carried a literal `"Hieroglyphic *"` placeholder instead of a real attested Egyptian form.** This is the exact honesty-bar violation that was caught and pruned at small scale earlier in the session (the guessed Coptic forms in "round 15") — here at 100× scale. It pushed the headline top-tier rate from an honest 55% to an inflated 66%.

- **Fix applied:** reverted `afro-asiatic-200.json` to the last vetted committed state — **324 entries, 55% top-tier, zero placeholder forms, 14 honest original Coptic-parallel entries retained.**

**2. Stale top-tier numbers in the live dashboard.** `index.html` still claimed "60% and climbing" for the Afro-Asiatic roster in five places, from a mid-session moment before the count grew and the rate honestly settled.
- **Fix applied:** all five corrected to the honest **55%** (179 / 324).

**3. Working directories not ignored.** `scratch/`, `temp/`, `outputs/` were untracked and at risk of being committed.
- **Fix applied:** added to `.gitignore`.

### 🟡 Flagged for your decision — exploratory, now honestly labeled (NOT committed as confirmed)

A coherent but **unverified** exploration layer was built and partly wired into the dashboard. It is kept on disk for you to develop, but is **not** part of the confirmed rosters and is **not** wired into the live site:

- **`sanskrit-cognates.json`** (33 entries, mixed grading) + `sanskrit-indo-iranian-echoes.md` (+AR). Sanskrit is genuinely the bold Indo-European frontier (distant family — the real test). The grading is more honest than the Coptic bulk, but some entries are speculative (أخ↔bhrātṛ, اسم↔nāman are contested), and it needs vetting against Monier-Williams before any claim.
- **`coptic-egyptian-echoes.md`**, **`coptic-egyptian-unexplored-lexicon.md`** (+AR). Tied to the bulk Coptic data; the analysis docs may hold real cases (لِسان↔ⲗⲁⲥ, طِين↔ⲧⲱⲱⲃⲉ) but rest on unverified forms.
- An **interactive Sanskrit/Coptic lookup sandbox** added to `lookup.html` (601 lines) and **roadmap links** in `index.html`. These claimed "30 worked entries demonstrating identical underlying semantic charges" — overclaiming unverified work. **Reverted from the live files** and preserved in `scratch/uncommitted-ui-backup/` so nothing is lost; re-enable once the data is vetted.
- **Action taken:** prepended a clear `⚠️ EXPLORATORY DRAFT — UNVERIFIED` banner to all five exploration docs so they can never be mistaken for confirmed work.

## The honest numbers, after audit

| Roster | Entries | Top-tier | What it is |
|---|--:|--:|---|
| Arabic ↔ Hebrew | 219 | 84% | sibling — **the unity baseline, not proof** |
| Arabic ↔ Aramaic | 96 | 97% | sibling — the unity baseline |
| Arabic ↔ Ancient Egyptian | 324 | 55% | close family — a real cross-family test |
| Arabic ↔ Indo-European (calibrated) | 770 → 189 | 25% | distant — the boldest reach |

The **preservation gradient (siblings ~90% → super-family 55% → more-distant branches lower)** is intact: it measures how much of the original tongue's sound-meaning logic each branch kept, not how "real" the signal is. The inflated 66% would have blurred that honest reading by padding the super-family with placeholder forms. Removing the padding makes the case *stronger and more honest*, not weaker — every retained entry traces to a real attested form.

## Standing principle reaffirmed

The bar held the whole session: **prune, don't fabricate.** Twice now — the small "round 15" Coptic guesses and this 100-entry bulk — unverified material was removed rather than allowed to pad a number. The confirmed rosters are what we can defend line-by-line; the exploration is kept separate and labeled. That separation is the project's credibility.

## Open recommendations (your call)

1. **Vet the Sanskrit set** properly (Monier-Williams) — it's the genuinely bold frontier and worth doing right.
2. **Build a verified Coptic dataset** from Crum's dictionary (the `eye1_berlin_tla.py` pipeline is ready) rather than the bulk placeholders, then re-enable the lookup sandbox.
3. **Leave the siblings where they are** — Hebrew/Aramaic are the baseline; no need to pad them further.
