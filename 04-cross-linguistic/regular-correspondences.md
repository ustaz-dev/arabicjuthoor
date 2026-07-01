# Regular correspondences and the borrowing screen

**Status:** reference, in progress. Semitic branches first (they are the most regular).
**Companion to:** [`cross-linguistic-rigor-upgrade.md`](cross-linguistic-rigor-upgrade.md) and the [chance baseline](../05-audits/2026-07-02-skeleton-chance-baseline.md).

## Why regular, not permissive

Khshim's laws say a sound *may* correspond to another. That is permissive, and permissiveness is what a skeptic attacks: a generous swap-list can pair almost anything. The stronger statement, and the one the comparative method accepts as proof of descent, is that a sound corresponds to another **regularly**, the same shift, in the same environment, every time. Regularity is not a weaker claim than "one original tongue"; it is the single best evidence *for* it. The project already says this in the Aramaic block: "the regularity of the shifts is itself the signature of a single language diverging."

So this file records, per branch, the regular Arabic-to-target reflexes, each with an attested roster pair. A cross-linguistic entry is strongest when it names the regular rule it obeys, not merely that a swap was allowed.

## Part 1. Regular correspondences, Semitic branches

Each row: the Arabic phoneme, its regular reflex in the branch, and a confirmed pair from the roster. Identity (a sound maps to itself) is the default and is not tabled.

### Arabic to Hebrew

| Arabic | Hebrew reflex | Attested pair (roster) |
|---|---|---|
| ث (ṯ) | שׁ (š) | ثلاث ↔ שָׁלוֹשׁ *shalosh* (three); ثور ↔ שׁוֹר *shor* (ox) |
| ذ (ḏ) | ז (z) | ذهب ↔ זָהָב *zahav* (gold) |
| ض (ḍ) | צ (ts) | أرض ↔ אֶרֶץ *erets* (earth) |
| س (s) | שׁ (š) | سلام ↔ שָׁלוֹם *shalom*; سبع ↔ שֶׁבַע *shevaʿ* (seven) |
| ق (q) | ק (q) | قرن ↔ קֶרֶן *qeren* (horn) |

### Arabic to Aramaic

| Arabic | Aramaic reflex | Attested pair (roster) |
|---|---|---|
| ض (ḍ) | ע (ʿ) | أرض ↔ אַרְעָא *ʾarʿā* (earth), the classic ḍ→ʿ shift |
| ث (ṯ) | ת (t) | ثلاث ↔ תְּלָת *telāt* (three) |
| ذ (ḏ) | ד (d) | ذهب ↔ דַּהְבָא *dahbā* (gold) |
| س (s) | שׁ (š) | سلام ↔ שְׁלָמָא *šelāmā* (peace) |

### Arabic to Akkadian

| Arabic | Akkadian reflex | Attested pair (roster) |
|---|---|---|
| ع / ء (gutturals) | lost, with vowel colouring | بعل ↔ *bēlu* (lord); عين ↔ *īnu* (eye) |
| ض (ḍ) | ṣ | أرض ↔ *erṣetu* (earth) |
| ث (ṯ) | š | ثلاث ↔ *šalāš* (three) |
| ذ (ḏ) | z | أذن ↔ *uznu* (ear) |
| س (s) | š | اسم ↔ *šumu* (name) |

These are textbook comparative-Semitic correspondences. Their value here is that they are **regular**: the same input gives the same output across the roster, which is the divergence-by-rule signature of one tongue splitting, not a scatter of coincidences. Egyptian (Afro-Asiatic, a deeper split) and the Indo-European branches are the next tables to build; those correspondences are looser and need the chance baseline alongside them.

## Part 2. The borrowing screen (route)

Descent and borrowing are different claims. Conflating them invites the cherry-picking charge, so every cross-linguistic pair is screened into one of three routes:

- **inherited-trace**, kept in both branches from the one source. The strong core sits here: qarn/horn, thawr/taurus, sabʿ/seven, salām/shalom, rabb/rabbi, and the Semitic tables above.
- **reverse-borrowing**, the word travelled *from* Arabic outward. These support the project's direction and are kept, labelled. Example: *syrup* from Arabic *sharāb*; *carat* from *qīrāṭ*; and the reverse-borrowings surfaced by the [loanword audit](quranic-loanword-audit.md).
- **wanderwort / contested**, a travelled culture-word whose Indo-European route is tangled or whose skeleton is too short to trust. These are quarantined, not leaned on: *copy* (via Latin *copia*), *genie* (via Latin *genius*), *Gemini* (a two-consonant skeleton, which the [chance baseline](../05-audits/2026-07-02-skeleton-chance-baseline.md) shows matches ~3.5% of the time by accident).

The rule: keep inherited-trace and reverse-borrowing as evidence, mark wanderwort/contested and never build on them. The strong core carries the claim; the contested tail is shown honestly and set aside.

## Next

- Extend Part 1 to Egyptian (Orel-Stolbova, Ehret) and to the Indo-European branches (Grimm, Grassmann, Verner), each reflex tied to an attested pair.
- Add a `rule` and a `route` field per entry in the roster JSONs so the whole set is machine-checkable.
