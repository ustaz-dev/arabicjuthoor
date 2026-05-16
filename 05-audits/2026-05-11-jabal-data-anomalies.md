# Jabal data anomalies — 4 non-nucleus entries

The Jabal lexicon contains 4 entries in the `binary_root` column that are not
true binary nuclei. They are data-quality artefacts and should be filtered
when computing nucleus statistics.

| Entry | Why excluded |
|---|---|
| `التراكيبالخائية` | A section header from the original xlsx that bled into the data column |
| `جn` | Mojibake — Latin letter mixed into Arabic; corrupted source row |
| `عs` | Same — Latin letter mixed into Arabic |
| `ه` | Single letter; binaries should be at least 2 letters |

**Corrected total of legitimate binary nuclei in Jabal's lexicon: 453.**
Earlier 457 figure was inclusive of the 4 anomalies above.
