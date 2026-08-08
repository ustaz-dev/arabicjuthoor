#!/usr/bin/env python3
"""Apply the three bounded paperwork-closure batches requested on 2026-08-07.

The script is deliberately assertion-heavy: each batch is tied to the ranked
official queue produced by ``rank_proof_closure_families.py`` and appends only
member-level decisions.  It does not discover families or links.
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
import unicodedata
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
READING = ROOT / "04-cross-linguistic" / "readings" / "aramaic.md"
REPORT = ROOT / "data" / "proof-eligible-families.json"
AUDIT_DIR = ROOT / "05-audits"


def atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    normalized = unicodedata.normalize("NFC", text)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", newline="\n", dir=path.parent, delete=False
    ) as handle:
        handle.write(normalized)
        temporary = Path(handle.name)
    temporary.replace(path)


def positive(
    family_id: str,
    entry_id: str,
    headword: str,
    pronunciation: str,
    pos: str,
    gloss: str,
    verdict: str,
    root: str,
    source: str,
    morphology: str,
    sound: str,
    meaning: str,
    nucleus: str,
    quran: str,
    reason: str,
) -> dict[str, str]:
    item = locals()
    item["kind"] = "positive"
    return item


def terminal(
    family_id: str,
    entry_id: str,
    headword: str,
    pronunciation: str,
    pos: str,
    gloss: str,
    verdict: str,
    root: str,
    source: str,
    morphology: str,
    sound: str,
    meaning: str,
    nucleus: str,
    quran: str,
    reason: str,
) -> dict[str, str]:
    item = locals()
    item["kind"] = "terminal"
    item["state"] = verdict
    return item


def gap(
    family_id: str,
    entry_id: str,
    headword: str,
    pronunciation: str,
    pos: str,
    gloss: str,
    state: str,
    root: str,
    source: str,
    morphology: str,
    sound: str,
    meaning: str,
    nucleus: str,
    quran: str,
    reason: str,
    requires: str,
) -> dict[str, str]:
    item = locals()
    item["kind"] = "gap"
    item["verdict"] = state
    return item


BATCHES: dict[int, list[dict[str, str]]] = {
    1: [
        gap(
            "aramaic:family:04a9002f976e7eb15bfdef3b",
            "kaikki_aramaic:1200:en-סום-arc-verb-yjaG~g~s",
            "סום",
            "swm (سوم)",
            "verb",
            "to put, to place",
            "SOURCE-GAP",
            "سوم",
            "Kaikki Aramaic gives neither a romanization nor an etymology for this member; the two other family members are צום/צומא ‘fast’, a distinct meaning chain.",
            "The inventory marks the member lemma-surface-ready and retains all three consonants s-w-m; nothing is stripped.",
            "SIB-01 licenses ס ↔ س, while w/m are identities; sound alone does not issue a verdict.",
            "Aramaic ‘put, place’ does not meet the attested Arabic fan of سوم (bargain, range/graze) by a named direct sense or a single attested orbit.",
            "The root and nucleus layers were both checked; neither supplies a sourced semantic bridge.",
            "سوم is Quranic (15 morphology occurrences), so borrowing from Aramaic is forbidden; no borrowing closure is issued.",
            "The historical/semantic source needed to decide whether the placement sense belongs to this chain is absent, so NO-TRACE would be premature.",
            "a named historical source for this Aramaic sense or an attested one-step semantic bridge",
        ),
        positive(
            "aramaic:family:0f4f194923ba02f4c189391f",
            "kaikki_aramaic:1842:en-עקרתא-arc-adj-vXpoUGR0",
            "עקרתא",
            "ʿqrtʾ (عقرتأ)",
            "adj",
            "barren, sterile",
            "ROOT-TRACE",
            "عقر",
            "The existing two-layer member review names this exact ID and records ROOT-TRACE plus NUCLEUS-TRACE; Kaikki gives the same barren/sterile chain as עקרא, whose source explicitly compares Arabic عاقر/عقير.",
            "The signed Aramaic zero-step retains the lexical ʿ-q-r base and treats the adjective/state material outside that base; no consonant is silently discarded in this reconciliation.",
            "ע־ק־ר ↔ ع־ق־ر is identity; no substitution row is needed.",
            "Kaikki ‘barren, sterile’ is direct to Lisan al-Arab and Taj al-Arus عقر: the woman who does not conceive is عاقر.",
            "The same member’s prior two-layer card also records NUCLEUS-TRACE for عق; this card preserves both layers while using the stronger root verdict for disposal.",
            "عقر is Quranic (8 morphology occurrences); the filter therefore confirms shared inheritance/Arabic direction, never borrowing into Arabic.",
            "This is an explicit member-level reconciliation of a verdict already issued under an uncounted two-layer heading, not inheritance from the other family member.",
        ),
        gap(
            "aramaic:family:1354f259a46cf4be5c462830",
            "kaikki_aramaic:2031:en-בוצלא-arc-noun-KIlxZxaF",
            "בוצלא",
            "bwṣlʾ (بوصلأ)",
            "noun",
            "onion",
            "MORPHOLOGY-GAP",
            "بصل",
            "Kaikki explicitly compares Hebrew בָּצָל and Arabic بَصَل but publishes no romanization for this longer Aramaic spelling.",
            "After the signed state-vowel step, the inventory still reads b-w-ṣ-l; the internal ו cannot be declared a mater or removed without a published morphological analysis.",
            "The shorter family member בצלא maps directly to بصل, but this member has an additional original inventory consonant w; family grouping is not permission to drop it.",
            "‘Onion’ is direct and the Arabic fan is complete in Lisan al-Arab and Taj al-Arus, but semantics cannot repair the unresolved consonant.",
            "Root and nucleus were displayed together; the full-consonant gate blocks issuance before either can dispose the member.",
            "بصل is Quranic (1 morphology occurrence), so the comparison may not become a borrowing-into-Arabic closure.",
            "The source comparison is real, but the longer spelling fails the full-consonant gate until ו is analyzed.",
            "a published romanization or morphology that identifies the internal ו",
        ),
        positive(
            "aramaic:family:197ffac3c71573a0fa59c659",
            "kaikki_aramaic:1534:en-זמרא-arc-noun-MFlB3Woh",
            "זמרא",
            "zmrʾ (زمرأ)",
            "noun",
            "singing, music",
            "ROOT-ECHO",
            "زمر",
            "The exact member already has a two-layer review recording ROOT-ECHO and NUCLEUS-TRACE; Kaikki’s verbal family member is from Proto-Semitic *zamar-.",
            "ARAM-ZERO-01 removes only the state ending, leaving z-m-r intact.",
            "ז־מ־ר ↔ ز־م־ر is identity.",
            "Kaikki ‘singing, music’ meets Lisan al-Arab ‘زمر بالمزمار: غنى’ and Taj al-Arus ‘زمر بالمزمار غنى’ in one named musical chain.",
            "The prior member card records NUCLEUS-TRACE for زم alongside the root echo; both layers remain visible.",
            "زمر is Quranic (2 morphology occurrences); borrowing into Arabic is excluded and none is claimed.",
            "This card exposes the exact already-issued member verdict to the official counter under the charter’s recognized card shape.",
        ),
        positive(
            "aramaic:family:19d03b32cad07110ddd6427a",
            "kaikki_aramaic:1691:en-טביתא-arc-noun-fKzbWDBb",
            "טביתא",
            "ṭbytʾ (طبيتأ); published ṭabīṯāʾ",
            "noun",
            "gazelle",
            "ROOT-TRACE",
            "ظبي",
            "This member’s Kaikki etymology explicitly compares Aramaic טַבְיָא; the paired source record reconstructs Proto-Semitic *ṯ̣aby(at-) and compares Arabic ظَبْي.",
            "The published reconstruction names the feminine *-at- material and the Aramaic state ending; removing those named elements leaves ṭ-b-y, with no silent consonant loss.",
            "DENT-08 explicitly anchors ט ↔ ظ on ظبي; b and y are identities.",
            "Kaikki ‘gazelle’ directly equals Taj al-Arus and al-Muhkam ظبي ‘gazelle’; no orbit is needed.",
            "Root and nucleus were both checked in the existing family card; the full reconstructed root is the stronger issued layer.",
            "ظبي is not in the Quranic-root inventory; nevertheless the source names common Proto-Semitic ancestry, not a donor, so no borrowing verdict is licensed.",
            "The decision is issued for this member alone from its linked etymological chain and named morphology, not inherited from טביא.",
        ),
    ],
    2: [
        gap(
            "aramaic:family:1a1aa8d73b6394bfb396fbe3",
            "kaikki_aramaic:1335:en-עולא-arc-noun-YE89q0Fg",
            "עולא",
            "ʿwlʾ (عولأ)",
            "noun",
            "fetus, embryo",
            "SOURCE-GAP",
            "عول",
            "Kaikki supplies neither romanization nor etymology for this homonym; the other עולא in the family means ‘injustice’ and the verb עול means ‘harm, wrong’.",
            "ARAM-ZERO-01 removes the state ending only and leaves ʿ-w-l; no further consonant is dropped.",
            "The full skeleton can reach Arabic عول by identity, but a sound match cannot merge the fetus sense with the separately attested injustice chain.",
            "No named Arabic sense in the completed عول fan identifies ‘fetus, embryo’, and no attested one-step bridge has been recorded.",
            "Root and nucleus layers were checked independently; both remain semantically unsupported for this homonym.",
            "عول is Quranic (1 morphology occurrence), so the missing source cannot be replaced by a borrowing-into-Arabic story.",
            "The member is an explicitly separated homonym whose historical sense-chain source is absent; that is a source gap, not NO-TRACE.",
            "an etymology for the fetus homonym or an attested historical semantic bridge",
        ),
        positive(
            "aramaic:family:1b7c92e7c3f835921b43f7fe",
            "kaikki_aramaic:1303:en-אצר-arc-verb-zFXUGHMs",
            "אצר",
            "ʾṣr (أصر); published ʾăṣar",
            "verb",
            "to store, to stockpile",
            "ROOT-ECHO",
            "أصر",
            "Kaikki explicitly calls the member cognate with Hebrew אָצַר and Arabic أَصَرَ ‘confine, shut up, restrain’.",
            "The inventory marks a lemma surface with all three consonants ʾ-ṣ-r; nothing is stripped.",
            "א־צ־ר ↔ أ־ص־ر is the cognate identity given by the source; no ad hoc row is introduced.",
            "Al-Sihah gives أصره ‘held/confined him’, and Taj al-Arus gives أصر الشيء ‘confined and constricted it’; stockpiling is the attested one-step result of holding goods confined.",
            "The full root uses every consonant; the nucleus was inspected but does not replace the stronger full-root echo.",
            "أصر is Quranic (3 morphology occurrences), so the source comparison is read as cognacy/shared inheritance, never borrowing into Arabic.",
            "Sound, source, and the single confinement-to-storage semantic step all converge; the more cautious ROOT-ECHO records that the glosses are not verbatim identical.",
        ),
        gap(
            "aramaic:family:1d39ce152c35e2ea857683da",
            "kaikki_aramaic:1758:en-פעלתא-arc-noun-VRG0k7JK",
            "פעלתא",
            "p/fʿltʾ (فعلتأ)",
            "noun",
            "worker, labourer/laborer",
            "MORPHOLOGY-GAP",
            "فعل",
            "Kaikki supplies neither romanization nor etymology for this longer member; the shorter פעלא has a valid member-level ROOT-ECHO to فعل.",
            "After the signed state ending is removed, the inventory still retains p-ʿ-l-t; no source in this member names the final t as a derivational suffix.",
            "LAB-07 licenses p/f and ʿ-l are identities, but the original t cannot be ignored under the full-consonant gate.",
            "‘Worker’ meets the Arabic فعل/فاعل work chain in Lisan al-Arab and Taj al-Arus; semantic agreement does not authorize removal of t.",
            "A prior two-layer note issued NUCLEUS-TRACE from p-ʿ, but the current full-consonant gate requires the remaining l and t to be accounted for before that disposal can be reconciled.",
            "فعل is Quranic (108 morphology occurrences), so no borrowing-into-Arabic fallback is possible.",
            "The family relation and old nucleus note are retained, but this exact member needs published morphology for t before a verdict can issue.",
            "a published analysis identifying the final ת after the lexical p-ʿ-l base",
        ),
        gap(
            "aramaic:family:1e830a4a8790d550f05d1021",
            "kaikki_aramaic:428:en-פרזלא-arc-noun-BOnA24fn",
            "פרזלא",
            "p/frzlʾ (فرزلأ); published parzəlā",
            "noun",
            "iron",
            "SOURCE-GAP",
            "(no Arabic comparator selected)",
            "Kaikki says only ‘Compare Hebrew בַּרְזֶל and Sumerian 𒀭𒁇𒋤 (AN.BAR.SUD)’; it does not state a donor, direction, or reconstructed ancestor. The readable tool returned the cuneiform unchanged, so the source’s AN-BAR-SUD rendering is retained.",
            "ARAM-ZERO-01 removes the state ending and leaves the full p-r-z-l quadriliteral.",
            "No Arabic full-root comparator is selected, and the cross-language comparison itself is not a licensed sound path or a loan declaration.",
            "The branch meaning ‘iron’ is clear, but neither an Arabic root fan nor a sourced direction follows from a bare compare note.",
            "Full-root and nucleus views were checked; neither can decide origin or disposal without the historical source.",
            "No Arabic comparator is proposed, so the Quranic borrowing gate is not engaged; importantly, the Sumerian comparison is not promoted to LOANWORD.",
            "A comparison to Hebrew and Sumerian without direction is insufficient for either TRACE or LOANWORD and prevents a completed NO-TRACE gate.",
            "a historical etymology that names the ancestor or donor and the direction of transmission",
        ),
        gap(
            "aramaic:family:21e77b4f30b26000090d2f1e",
            "kaikki_aramaic:1170:en-עומקא-arc-noun-XBaOHpyp",
            "עומקא",
            "ʿwmqʾ (عومقأ)",
            "noun",
            "depth, deepness",
            "MORPHOLOGY-GAP",
            "عمق",
            "Kaikki supplies no romanization or etymology for this member; the other family member compares Arabic عمق and several Semitic forms.",
            "ARAM-ZERO-01 removes the state ending, but the inventory still retains ʿ-w-m-q; no member-specific source identifies ו as a vowel letter rather than an original consonant.",
            "The desired Arabic root is ʿ-m-q, but the internal w cannot be silently dropped even though the shorter semantic chain is strong.",
            "‘Depth, deepness’ directly equals the عمق fan in Lisan al-Arab and Taj al-Arus; this does not resolve the full-consonant problem.",
            "A prior two-layer note selected nucleus عق from positions 1 and 4, leaving w and m unexplained; the current full-consonant gate therefore blocks reconciliation of that note.",
            "عمق is Quranic (1 morphology occurrence), so borrowing into Arabic is excluded and cannot solve the morphology.",
            "The remaining issue is specifically whether ו marks the /u/ vowel in this form; until a published romanization or analysis says so, the card stays MORPHOLOGY-GAP.",
            "a published romanization or Aramaic morphology for the internal ו",
        ),
    ],
    3: [
        terminal(
            "aramaic:family:2acd0d57a7748625f1c009a9",
            "kaikki_aramaic:589:en-אצבע-arc-noun-0erdWuaU",
            "אצבע",
            "ʾṣbʿ (أصبع); published ʾeṣbaʿ",
            "noun",
            "singular absolute/construct state of אֶצְבְּעָא (ʾeṣbəʿā, ‘finger’)",
            "FORM-OF-ISOLATED",
            "صبع",
            "The Kaikki gloss explicitly identifies this item as the singular absolute/construct state of אֶצְבְּעָא, pronounced by the readable tool ʾeṣəbəʿāʾ (أصبعأ).",
            "This is an inflectional state of the already judged lexical lemma, not a second independent lexical member; no consonant is removed to manufacture a comparison.",
            "No sound judgment is inherited: the source’s explicit form-of relation is the terminal basis.",
            "The lexical lemma has its own ROOT-TRACE card and Arabic fan; this state form is isolated so it cannot double-count that evidence.",
            "Root and nucleus remain properties of the lemma card; the form closure does not issue another link.",
            "صبع is Quranic (2 morphology occurrences); the terminal decision is morphological and makes no borrowing claim.",
            "The source explicitly labels an inflectional state, so the correct member-level disposal is FORM-OF-ISOLATED.",
        ),
        positive(
            "aramaic:family:336fdcca7343a4e0f82c1ec2",
            "kaikki_aramaic:1584:en-יבשא-arc-noun-WIAdN5go",
            "יבשא",
            "ybšʾ (يبشأ)",
            "noun",
            "earth, dry land",
            "ROOT-TRACE",
            "يبس",
            "Kaikki gives the dry-land noun in the same lexical family as יבש ‘to be dry’; the existing member card records the two-source Arabic fan and signed route.",
            "ARAM-ZERO-01 removes the state ending and leaves every lexical consonant y-b-š.",
            "y and b are identities; SIB-01 is the signed Aramaic š ↔ Arabic s route already used by the family’s verb card.",
            "Lisan al-Arab records أرض يبس and a dry path, while Taj al-Arus records موضع يبس and طريق يبس; Kaikki ‘earth, dry land’ is direct, not an invented orbit.",
            "The complete root succeeds with all consonants; the nucleus was checked independently and is not needed for disposal.",
            "يبس is Quranic (4 morphology occurrences), including the dry-path sense, so borrowing into Arabic is excluded and none is claimed.",
            "The exact noun, signed sound path, and two classical dry-land senses agree directly, supporting a member-level ROOT-TRACE.",
        ),
        terminal(
            "aramaic:family:361e2b5b7daea9c17ce82cd9",
            "kaikki_aramaic:1411:en-כף-arc-noun-icde6LNv",
            "כף",
            "kp/f (كف); published kap̄",
            "noun",
            "absolute state of כַּפָּא (kappā, ‘palm’)",
            "FORM-OF-ISOLATED",
            "كفف",
            "Kaikki marks form_of=1 and names the target כַּפָּא; the readable pronunciation of the target is kap/fāʾ (كفأ).",
            "The inventory classifies this row as form-linked with morphology not-applicable-form; it is the absolute state of the lexical lemma.",
            "No fresh sound path is used for the closure; the lemma’s Proto-Semitic *kapp- and its own judgment remain on the lemma card.",
            "The palm meaning is already represented by כַּפָּא; closing the state form prevents duplicated lexical evidence.",
            "Neither the root nor nucleus layer is reissued on an explicitly linked form.",
            "كفف is Quranic (15 morphology occurrences); this morphological closure makes no borrowing claim.",
            "The database and source both explicitly identify an inflectional state, meeting the FORM-OF-ISOLATED terminal rule.",
        ),
        positive(
            "aramaic:family:3ddde136898fbd9b20c25c86",
            "kaikki_aramaic:97:en-עקב-arc-verb-l8qJXv-n",
            "עקב",
            "ʿqb (عقب)",
            "verb",
            "to search, to investigate",
            "ROOT-ECHO",
            "عقب",
            "Kaikki gives a lemma-surface verb with no loan flag; the family’s noun ‘footprint’ already fixes the same full consonantal chain independently.",
            "All three lemma consonants ʿ-q-b are original and retained.",
            "ע־ק־ב ↔ ع־ق־ب is identity; no substitution row is needed.",
            "Kitab al-Ayn defines the muʿaqqib as one who follows a person’s track seeking a right, and Lisan al-Arab gives تعقبت ما صنع فلان ‘I followed/investigated what he did’; this is the direct search/investigation chain.",
            "The full root accounts for every consonant; the nucleus was also checked but does not replace it.",
            "عقب is Quranic (80 morphology occurrences), so the direction filter forbids borrowing into Arabic; the card claims no such route.",
            "The Arabic fan explicitly contains following a trace to examine a matter, so the branch gloss is a sourced root echo rather than an observational bridge.",
        ),
        terminal(
            "aramaic:family:3f5802f7541e4f342aa0d81d",
            "kaikki_aramaic:1945:en-תמני-arc-num-CALQIT4o",
            "תמני",
            "tmny (تمني); published təmānē",
            "num",
            "feminine of תְּמָנְיָא (təmānəyā, ‘eight’)",
            "FORM-OF-ISOLATED",
            "ثمن",
            "Kaikki marks form_of=1 and names the target תְּמָנְיָא; the readable pronunciation of the target is təmānəyāʾ (تمنيأ).",
            "The inventory classifies the row as form-linked and morphology not-applicable-form; the feminine form is not a second lexical number.",
            "No sound comparison is needed for this terminal decision; the lemma’s Proto-Semitic *ṯamāniy- remains in its own card.",
            "The meaning ‘eight’ is already carried by the lexical lemma, so this grammatical form cannot add independent evidence.",
            "Root and nucleus layers are not reissued for a source-linked inflectional form.",
            "ثمن is Quranic (19 morphology occurrences); the closure is grammatical and contains no borrowing claim.",
            "The explicit form link makes FORM-OF-ISOLATED the proper terminal closure for this inventory member.",
        ),
    ],
}


def render(item: dict[str, str], rank: int, batch: int) -> str:
    state = item.get("state", "READY")
    verdict = item["verdict"]
    is_gap = item["kind"] == "gap"
    requires = item.get("requires", "no unresolved gate; verdict issued")
    result_reason = item["reason"]
    return "\n".join(
        [
            f"### بطاقة: `{item['family_id']}`، إغلاق المسار {batch:03d}، الرتبة {rank}",
            f"- العضو: `{item['entry_id']}`؛ {item['headword']}، {item['pos']}، «{item['gloss']}»؛ النتيجة: {verdict}.",
            f"- تعليل القرار: {result_reason}",
            "- إصدارُ البروتوكول: RECOVERY-v2 (2026-07-14) + TWO-LAYER (2026-08-01).",
            f"- الكلمةُ في الفرع: `{item['headword']}`؛ النطق المقروء: `{item['pronunciation']}`؛ {item['pos']}؛ «{item['gloss']}» [Kaikki Aramaic، `{item['entry_id']}`].",
            f"- المصدر والهوية الصغرى: {item['source']}",
            f"- الخطوة صفر وبوابة الصوامت: {item['morphology']}",
            f"- مسار الصوت: {item['sound']}",
            f"- مسح العربية والمدار: الجذر `{item['root']}`؛ {item['meaning']}",
            f"- عرض الطبقتين: {item['nucleus']}",
            f"- مصفاة القرآن والاتجاه: {item['quran']}",
            "- جسور الاسترداد المفحوصة: الجذر الكامل؛ الأجوف؛ النواة؛ المرشح الصوتي؛ مروحة المعنى؛ عضو الأسرة المقارن؛ المصدر التاريخي؛ القرض؛ المتجانس؛ والاتجاه.",
            f"- عائق: النوع={state}؛ يتطلب={requires}.",
            f"- حالةُ الإغلاق: {state}.",
            (
                f"- الحكم (استكشاف): غير صادر؛ {state} للعضو `{item['entry_id']}`؛ العائق لا يصنع حكمًا سالبًا."
                if is_gap
                else f"- الحكم (استكشاف): {verdict} للعضو `{item['entry_id']}` وحده؛ السبب مسجل أعلاه."
            ),
            "- عدسة الاسترداد: راجعت الحكم السابق غير المرئي للعداد أو كل طبقات الاسترداد قبل تسمية الفجوة.",
            "- عدسة التشكيك: منعت وراثة حكم عضو آخر، وإسقاط الصامت غير المفسر، وقلب المقارنة إلى قرض بلا مانح.",
            "- ملاحظات: دفعة إغلاق ورقية محدودة؛ لا صيد روابط، ولا تشغيل للبرهان.",
            "",
        ]
    )


def current_ranked(max_missing: int = 2) -> list[dict[str, Any]]:
    payload = json.loads(REPORT.read_text(encoding="utf-8"))
    families = []
    for language in ("aramaic", "hebrew"):
        for family in payload["languages"][language]["incomplete_family_queue"]:
            if family["missing_member_count"] > max_missing:
                continue
            item = dict(family)
            item["language"] = language
            families.append(item)
    families.sort(
        key=lambda family: (
            family["missing_member_count"],
            not any(
                member["current_state"] == "UNRECORDED"
                for member in family["missing_members"]
            ),
            family["language"],
            family["family_id"],
        )
    )
    return families


def write_minute(batch: int, items: list[dict[str, str]]) -> None:
    final_count = sum(item["kind"] != "gap" for item in items)
    gaps: dict[str, int] = {}
    for item in items:
        state = item.get("state", "READY")
        if item["kind"] == "gap":
            gaps[state] = gaps.get(state, 0) + 1
    path = AUDIT_DIR / f"2026-08-07-closure-lane-batch-{batch:03d}.md"
    rows = [
        f"| {rank} | `{item['family_id']}` | `{item['entry_id']}` | {item['verdict']} | {item['reason']} |"
        for rank, item in enumerate(items, 1)
    ]
    gap_text = ", ".join(f"{key}={value}" for key, value in sorted(gaps.items())) or "none"
    atomic_write(
        path,
        "\n".join(
            [
                f"# Closure lane batch {batch:03d} minutes",
                "",
                "## Scope",
                "",
                "Five consecutive one-member-short families from the mechanically ranked official queue; no link discovery and no proof execution.",
                "",
                "| Rank | Family | Member | Disposition | Recorded reason |",
                "|---:|---|---|---|---|",
                *rows,
                "",
                "## Batch accounting",
                "",
                f"- Members given a final issued verdict or terminal closure: {final_count}.",
                f"- Named non-final gaps: {gap_text}.",
                "- Families moved from incomplete to eligible: PENDING COUNTER REFRESH.",
                "- Eligible-family total after batch: PENDING COUNTER REFRESH.",
                "- The proof run was not executed.",
                "",
            ]
        ),
    )


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("batch", type=int, choices=sorted(BATCHES))
    parser.add_argument("--refresh-existing", action="store_true")
    args = parser.parse_args()
    batch = args.batch
    items = BATCHES[batch]
    marker = f"<!-- CLOSURE-LANE-BATCH-{batch:03d} -->"
    text = READING.read_text(encoding="utf-8")
    if marker in text and not args.refresh_existing:
        print(f"closure lane batch {batch:03d}: already present")
        return 0

    if not args.refresh_existing:
        ranked = current_ranked()
        expected = [item["family_id"] for item in items]
        observed = [item["family_id"] for item in ranked[: len(items)]]
        if observed != expected:
            raise ValueError(
                f"batch {batch:03d} queue drift: expected {expected}, observed {observed}"
            )
        for specification, family in zip(items, ranked):
            unresolved = family["missing_members"]
            if len(unresolved) != 1:
                raise ValueError(f"{family['family_id']}: not one member short")
            if unresolved[0]["entry_id"] != specification["entry_id"]:
                raise ValueError(
                    f"{family['family_id']}: expected {specification['entry_id']}, "
                    f"observed {unresolved[0]['entry_id']}"
                )

    block = "\n".join(
        [
            "",
            marker,
            "",
            f"## مسار إغلاق أسر البرهان، الدفعة {batch:03d} (2026-08-07)",
            "",
            "### بيان النطاق",
            "",
            "خمس أسر متتابعة من رأس القائمة الرسمية المرتبة آليًا بعدد الأعضاء غير المحسومين؛ لكل أسرة عضو واحد باق. هذه دفعة إغلاق ورقي لا صيد روابط، ولم يُشغّل البرهان.",
            "",
            *[render(item, rank, batch) for rank, item in enumerate(items, 1)],
            f"<!-- CLOSURE-LANE-BATCH-{batch:03d}:END -->",
            "",
        ]
    )
    if args.refresh_existing:
        end_marker = f"<!-- CLOSURE-LANE-BATCH-{batch:03d}:END -->"
        start = text.index(marker)
        end = text.index(end_marker, start) + len(end_marker)
        atomic_write(READING, text[:start].rstrip() + "\n" + block.strip() + "\n" + text[end:].lstrip())
    else:
        atomic_write(READING, text.rstrip() + "\n" + block)
        write_minute(batch, items)
    print(
        json.dumps(
            {
                "batch": batch,
                "members": len(items),
                "final": sum(item["kind"] != "gap" for item in items),
                "gaps": [
                    item["state"] for item in items if item["kind"] == "gap"
                ],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
