# -*- coding: utf-8 -*-
"""ابنِ ورقةَ ألغازِ نهاياتِ الحالِ والجمعِ في الشمالِ الساميّ.

هذه أداةُ استكشافٍ لا أداةُ حكم. تقرأُ البطاقاتِ القائمةَ في ملفَّي الآراميّةِ
والعبريّة، وتوحِّدُ تكرارَ البطاقةِ بمعرِّفِ الأسرةِ أو العضو، ثمّ تولِّدُ مروحةَ
الجذورِ العربيّةِ من كلِّ هيكلٍ أعادته ``north_skeletons``. لا يظهرُ في المروحةِ
إلّا جذرٌ شهدت له ذخيرةُ المعاجمِ العربيّةِ المحلّيّة.

الاستعمال:
    python scripts/build_semitic_endings_riddle_sheet.py
    python scripts/build_semitic_endings_riddle_sheet.py --check
"""
from __future__ import annotations

import argparse
import itertools
import re
import sqlite3
import sys
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import bulk_phonetic_sweep as semantic  # noqa: E402
import fan_any_script as northern  # noqa: E402
import fan_northern_word as arabic_lexica  # noqa: E402
import readable  # noqa: E402


READINGS = ROOT / "04-cross-linguistic" / "readings"
OUT = (
    ROOT
    / "04-cross-linguistic"
    / "exploration"
    / "riddle-sheet-semitic-endings.md"
)
AUDIT = ROOT / "05-audits" / "2026-08-10-semitic-state-endings.md"
INVENTORY = ROOT / "cache" / "recovery_pipeline" / "inventory-v5.sqlite"

LANGUAGES = (
    ("aramaic", "الآرامِيَّة"),
    ("hebrew", "العِبْرِيَّة"),
)
EXPECTED = {
    "aramaic": {
        "total": 104,
        "ותא": 7,
        "יתא": 8,
        "תא": 51,
        "יא": 19,
        "ות": 1,
        "ימ": 0,
        "ינ": 13,
        "ה": 2,
        "ת": 3,
    },
    "hebrew": {
        "total": 421,
        "ותא": 0,
        "יתא": 1,
        "תא": 0,
        "יא": 1,
        "ות": 40,
        "ימ": 61,
        "ינ": 23,
        "ה": 237,
        "ת": 58,
    },
}

CARD_HEAD = re.compile(r"^### (?:بطاقة|مراجعة عضوية):")
SECTION_HEAD = re.compile(r"^#{2,3} ")
NORTH_RUN = re.compile(r"[\u0590-\u05ff]+")
FAMILY_ID = re.compile(r"(?:aramaic|hebrew):family:[0-9a-f]+")
ENTRY_ID = re.compile(r"`(kaikki_(?:aramaic|hebrew):[^`]+)`")
HAMZA_FOLD = str.maketrans("أإآؤئ", "اااوي")
NOTABLES = (
    ("עסקתא", "", "عسق"),
    ("ביתא", "house", "بيت"),
    ("שמיא", "sky", "سمو"),
    ("שנתא", "year", "سن"),
    ("גברותא", "power", "جبر"),
    ("גדיא", "goat", "جدي"),
    ("דמעתא", "tear", "دمع"),
    ("נשמתא", "breath", "نسم"),
    ("ענבים", "grape", "عنب"),
    ("ביכורים", "fruits", "بكر"),
)


@dataclass
class Card:
    language: str
    language_ar: str
    source_line: int
    key: str
    word: str
    ending: str
    block: str
    gloss: str = ""
    skeletons: list[dict] | None = None
    original_roots: list[str] | None = None
    alternate_roots: list[str] | None = None
    opened_roots: list[str] | None = None
    machine_pick: str = ""
    machine_score: int = 0
    machine_direct: bool = False
    machine_shared: tuple[str, ...] = ()

    @property
    def opened(self) -> bool:
        return bool(self.opened_roots)


def nfc(value: str) -> str:
    return unicodedata.normalize("NFC", str(value))


def one_line(value: str) -> str:
    return " ".join(nfc(value).replace("\x00", "").split())


def fold_arabic(value: str) -> str:
    """طيُّ الهمزةِ النافذُ في المستودع، مع ردِّ الهمزةِ المفردةِ إلى ألف."""
    return arabic_lexica.bare_ar(nfc(value)).translate(HAMZA_FOLD).replace("ء", "ا")


def clean_north(value: str) -> str:
    return northern._north_letters(value)  # noqa: SLF001


def ending_of(word: str) -> str:
    normalized = clean_north(word)
    for ending, _ in northern.NORTH_ENDINGS:
        if normalized.endswith(ending):
            return ending
    return ""


def card_key(language: str, heading: str, source_line: int) -> str:
    if match := FAMILY_ID.search(heading):
        return match.group(0)
    if match := ENTRY_ID.search(heading):
        return match.group(1)
    return f"{language}:card:{source_line}"


def cards_of(language: str, language_ar: str) -> list[Card]:
    path = READINGS / f"{language}.md"
    lines = path.read_text(encoding="utf-8").splitlines()
    found: dict[str, Card] = {}
    for index, heading in enumerate(lines):
        if not CARD_HEAD.match(heading):
            continue
        words = NORTH_RUN.findall(heading)
        if not words:
            continue
        word = nfc(words[0])
        ending = ending_of(word)
        if not ending:
            continue
        key = card_key(language, heading, index + 1)
        if key in found:
            continue
        end = next(
            (
                cursor
                for cursor in range(index + 1, len(lines))
                if SECTION_HEAD.match(lines[cursor])
            ),
            len(lines),
        )
        found[key] = Card(
            language=language,
            language_ar=language_ar,
            source_line=index + 1,
            key=key,
            word=word,
            ending=ending,
            block="\n".join(lines[index:end]),
        )
    return list(found.values())


def inventory_connection() -> sqlite3.Connection:
    if not INVENTORY.exists():
        raise FileNotFoundError(f"غاب جردُ المصدر: {INVENTORY}")
    connection = sqlite3.connect(
        f"file:{INVENTORY.resolve().as_posix()}?mode=ro&immutable=1",
        uri=True,
    )
    connection.row_factory = sqlite3.Row
    return connection


def same_north(left: str, right: str) -> bool:
    return clean_north(left) == clean_north(right)


def family_rows(connection: sqlite3.Connection, card: Card) -> list[sqlite3.Row]:
    rows = connection.execute(
        """
        SELECT e.entry_id,e.headword,e.romanization,e.pos,e.gloss
        FROM family_members fm
        JOIN entries e ON e.entry_id=fm.entry_id
        WHERE fm.family_id=?
        ORDER BY CAST(substr(e.entry_id,instr(e.entry_id,':')+1) AS INTEGER),e.entry_id
        """,
        (card.key,),
    ).fetchall()
    exact = [row for row in rows if same_north(row["headword"], card.word)]
    if exact:
        return exact
    anchor = connection.execute(
        """
        SELECT e.entry_id,e.headword,e.romanization,e.pos,e.gloss
        FROM families f JOIN entries e ON e.entry_id=f.anchor_entry_id
        WHERE f.family_id=?
        """,
        (card.key,),
    ).fetchone()
    return [anchor] if anchor else rows[:1]


def entry_rows(connection: sqlite3.Connection, card: Card) -> list[sqlite3.Row]:
    row = connection.execute(
        "SELECT entry_id,headword,romanization,pos,gloss FROM entries WHERE entry_id=?",
        (card.key,),
    ).fetchone()
    if row:
        return [row]
    line_match = re.search(r":(\d+):", card.key)
    if not line_match:
        return []
    like = f"kaikki_{card.language}:{line_match.group(1)}:%"
    rows = connection.execute(
        """
        SELECT entry_id,headword,romanization,pos,gloss
        FROM entries WHERE language=? AND entry_id LIKE ? ORDER BY entry_id
        """,
        (card.language, like),
    ).fetchall()
    exact = [row for row in rows if same_north(row["headword"], card.word)]
    return exact or rows[:1]


def gloss_from_block(card: Card) -> str:
    preferred = [
        line
        for line in card.block.splitlines()
        if line.startswith("- المعنى من قاموس الفرع:")
        or line.startswith("- العضو:")
        or line.startswith("- الكلمةُ في الفرع:")
    ]
    for line in preferred:
        quoted = [one_line(value) for value in re.findall(r"«([^»]+)»", line)]
        if quoted:
            return "; ".join(dict.fromkeys(quoted))
    quoted = [one_line(value) for value in re.findall(r"«([^»]+)»", card.block)]
    return "; ".join(dict.fromkeys(quoted[:3])) or "لا معنًى منشورًا مستخرجًا"


def attach_glosses(cards: list[Card]) -> None:
    connection = inventory_connection()
    try:
        for card in cards:
            if ":family:" in card.key:
                rows = family_rows(connection, card)
            elif card.key.startswith("kaikki_"):
                rows = entry_rows(connection, card)
            else:
                rows = []
            glosses = [one_line(row["gloss"]) for row in rows if one_line(row["gloss"])]
            card.gloss = "; ".join(dict.fromkeys(glosses)) or gloss_from_block(card)
    finally:
        connection.close()


def folded_root_index() -> tuple[dict[str, list[str]], dict[str, list[tuple[str, str]]]]:
    roots = arabic_lexica.load_arabic_roots()
    by_fold: dict[str, list[str]] = defaultdict(list)
    for root in roots:
        folded = fold_arabic(root)
        if folded and root not in by_fold[folded]:
            by_fold[folded].append(root)
    return dict(by_fold), roots


def candidates_of(
    skeleton: list[str],
    by_fold: dict[str, list[str]],
) -> list[str]:
    if not 2 <= len(skeleton) <= 4:
        return []
    options = [northern.NORTH_FAN.get(letter, ()) for letter in skeleton]
    if any(not option for option in options):
        return []
    out: list[str] = []
    seen: set[str] = set()
    for combination in itertools.product(*options):
        generated = "".join(combination)
        for root in by_fold.get(fold_arabic(generated), []):
            if root not in seen:
                seen.add(root)
                out.append(root)
    return out


def folded_semantic_bridge() -> tuple[dict[str, set[str]], dict[str, set[str]]]:
    head, gloss = semantic.load_bridge()
    folded_head: dict[str, set[str]] = defaultdict(set)
    folded_gloss: dict[str, set[str]] = defaultdict(set)
    for root, words in head.items():
        folded_head[fold_arabic(root)].update(words)
    for root, words in gloss.items():
        folded_gloss[fold_arabic(root)].update(words)
    return dict(folded_head), dict(folded_gloss)


def ordered_union(groups: Iterable[Iterable[str]]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for group in groups:
        for value in group:
            if value not in seen:
                seen.add(value)
                out.append(value)
    return out


def attach_fans(cards: list[Card]) -> None:
    by_fold, _ = folded_root_index()
    head, gloss = folded_semantic_bridge()
    for card in cards:
        skeleton_rows = []
        for skeleton, label in northern.north_skeletons(card.word):
            roots = candidates_of(skeleton, by_fold)
            skeleton_rows.append(
                {
                    "skeleton": skeleton,
                    "label": label,
                    "roots": roots,
                }
            )
        card.skeletons = skeleton_rows
        card.original_roots = skeleton_rows[0]["roots"] if skeleton_rows else []
        card.alternate_roots = ordered_union(
            row["roots"] for row in skeleton_rows[1:]
        )
        original_folds = {fold_arabic(root) for root in card.original_roots}
        opened_folds: set[str] = set()
        card.opened_roots = []
        for root in card.alternate_roots:
            folded = fold_arabic(root)
            if folded not in original_folds and folded not in opened_folds:
                opened_folds.add(folded)
                card.opened_roots.append(root)

        branch_words = semantic.words_of(card.gloss)
        scored = []
        all_roots = ordered_union(row["roots"] for row in skeleton_rows)
        for order, root in enumerate(all_roots):
            folded = fold_arabic(root)
            direct = branch_words & head.get(folded, set())
            near = (branch_words & gloss.get(folded, set())) - direct
            score = 3 * len(direct) + len(near)
            scored.append(
                (
                    -score,
                    order,
                    root,
                    bool(direct),
                    tuple(sorted(direct)[:4] or sorted(near)[:3]),
                )
            )
        if scored:
            scored.sort()
            negative, _, root, direct, shared = scored[0]
            card.machine_pick = root
            card.machine_score = -negative
            card.machine_direct = direct
            card.machine_shared = shared


def validate_inventory(cards: list[Card]) -> None:
    by_language = Counter(card.language for card in cards)
    if sum(by_language.values()) != 525:
        raise RuntimeError(f"اختلَّ جردُ النهايات: {dict(by_language)}")
    for language, _ in LANGUAGES:
        expected = EXPECTED[language]
        if by_language[language] != expected["total"]:
            raise RuntimeError(
                f"اختلَّ جردُ {language}: {by_language[language]} لا {expected['total']}"
            )
        endings = Counter(card.ending for card in cards if card.language == language)
        for ending, _ in northern.NORTH_ENDINGS:
            if endings[ending] != expected[ending]:
                raise RuntimeError(
                    f"اختلَّت نهايةُ {ending} في {language}: "
                    f"{endings[ending]} لا {expected[ending]}"
                )


def validate_regressions(cards: list[Card]) -> None:
    if fold_arabic("رءس") != fold_arabic("رأس") or fold_arabic("رأس") != "راس":
        raise RuntimeError("فشل حارسُ طيِّ الهمزةِ في رأس")
    by_word: dict[str, list[Card]] = defaultdict(list)
    for card in cards:
        by_word[clean_north(card.word)].append(card)
    expected_openings = {
        "עסקתא": {"عسق", "عشق", "غسق"},
        "ביתא": {"بيت"},
        "שמיא": {"سمو"},
        "שנתא": {"سن"},
    }
    for word, roots in expected_openings.items():
        rows = by_word.get(clean_north(word), [])
        reached = {
            fold_arabic(root)
            for row in rows
            for root in (row.opened_roots or [])
        }
        missing = {fold_arabic(root) for root in roots} - reached
        if missing:
            raise RuntimeError(f"فشل حارسُ {word}: غابت {sorted(missing)}")


def esc(value: str) -> str:
    return (
        one_line(value)
        .replace("|", "،")
        .replace("—", "،")
        .replace("–", "،")
    )


def north_form(value: str, language: str) -> str:
    said = one_line(readable.say(value, language))
    return f"`{value}` · **{said}**"


def annotate_north(value: str, language: str) -> str:
    return NORTH_RUN.sub(lambda match: north_form(match.group(0), language), esc(value))


def ending_form(ending: str, language: str) -> str:
    return north_form(ending, language)


def label_form(label: str, language: str) -> str:
    return annotate_north(label, language)


def roots_form(roots: list[str], best: str = "") -> str:
    if not roots:
        return "لا جذرَ معجميًّا"
    return "، ".join(f"**{root}**" if root == best else root for root in roots)


def skeleton_form(row: dict, card: Card) -> str:
    skeleton = "".join(row["skeleton"])
    return (
        f"{north_form(skeleton, card.language)}: "
        f"{roots_form(row['roots'], card.machine_pick)}"
    )


def alternatives_form(card: Card) -> str:
    rows = card.skeletons or []
    if len(rows) < 2:
        return "لا هيكلَ بديلًا"
    parts = []
    for row in rows[1:]:
        parts.append(
            f"{label_form(row['label'], card.language)}: {skeleton_form(row, card)}"
        )
    return "<br>".join(parts)


def pick_form(card: Card) -> str:
    if not card.machine_pick:
        return "لا اختيارَ معجميًّا"
    if card.machine_score == 0:
        return f"**{card.machine_pick}**، بلا تقاطعٍ لفظيّ"
    witness = "مباشر" if card.machine_direct else "قرينة"
    shared = ", ".join(card.machine_shared)
    return f"**{card.machine_pick}**، {witness} {card.machine_score}" + (
        f" ({shared})" if shared else ""
    )


def opened_form(card: Card) -> str:
    if not card.opened:
        return "لا"
    return f"نعم: {roots_form(card.opened_roots or [], card.machine_pick)}"


def source_form(card: Card) -> str:
    return f"`{card.language}.md:{card.source_line}`"


def sorted_cards(cards: list[Card], language: str) -> list[Card]:
    selected = [card for card in cards if card.language == language]
    return sorted(
        selected,
        key=lambda card: (
            not card.opened,
            -card.machine_score,
            clean_north(card.word),
            card.source_line,
        ),
    )


def render_sheet(cards: list[Card]) -> str:
    opened = sum(card.opened for card in cards)
    lines = [
        "# وَرَقَةُ الأَلْغازِ: ما فَتَحَتْهُ نِهاياتُ الحالِ والجَمْعِ السَّامِيَّة",
        "",
        "**التاريخ:** 2026-08-10. **الطَّبقة:** استكشاف. "
        "**هذه مَرْوَحَةٌ يُختارُ مِنها، لا حُكْمٌ يُصَدَّق.**",
        "",
        "تَقرأُ هذه الوَرَقةُ كُلَّ بِطاقةٍ في الآرامِيَّةِ والعِبْرِيَّةِ حَمَلَتْ "
        "كَلِمَتُها الرَّأْسُ واحِدَةً مِن نِهاياتِ الحالِ أو الجَمْعِ المَفْتوحَة. "
        "لِكُلِّ كَلِمَةٍ يُعْرَضُ الهَيْكَلُ «كما وَرَدَتْ»، ثُمَّ كُلُّ هَيْكَلٍ بَديلٍ "
        "أعادَتْهُ الأداةُ مَعَ وَسْمِهِ.",
        "",
        "**وَحْدَةُ الجَرْد:** `### بطاقة:` و`### مراجعة عضوية:`، مَعَ تَوْحيدِ "
        "الإعاداتِ بِمُعَرِّفِ الأُسْرَةِ أو العُضْو. لذلك لا تُعَدُّ مُراجَعَةُ "
        "البِطاقةِ بِطاقةً ثانيةً.",
        "",
        "**كَيفَ تُحَلُّ:** يُقْرَأُ النُّطْقُ جَهْرًا، ثُمَّ المَعْنى المَنْشور، ثُمَّ "
        "تُقارَنُ مَرْوَحَةُ الهَيْكَلِ الأَصْليِّ بِمَرْوَحاتِ البَدائل. كُلُّ جَذْرٍ "
        "مَعْروضٍ مَوْجودٌ فِعْلًا في ذَخيرَةِ المَعاجِمِ العَرَبِيَّةِ المَحَلِّيَّة، "
        "واخْتِيارُ الأداةِ تَرْتيبٌ بِتَقاطُعِ المَعْنى لا حُكْمٌ لُغَوِيّ.",
        "",
        f"**التَّرْتيبُ:** البِطاقاتُ الَّتي فَتَحَ فيها البَديلُ جَذْرًا لَمْ يَكُنْ "
        f"يُبْلَغُ تَأْتي أَوَّلًا. وَقَعَ ذلكَ في {opened} بِطاقةً مِن أَصْلِ "
        "الجَرْدِ الكامِلِ.",
        "",
    ]

    for language, language_ar in LANGUAGES:
        rows = sorted_cards(cards, language)
        opened_language = sum(card.opened for card in rows)
        lines += [
            f"## {language_ar} ({len(rows)} بِطاقةً، فَتَحَ البَديلُ في {opened_language})",
            "",
            "| # | الكَلِمَةُ ونُطْقُها | مَعْناها المَنْشور | النِّهايَةُ | "
            "الهَيْكَلُ «كما وَرَدَتْ» ومَرْوَحَتُه | الهَيْكَلُ البَديلُ "
            "ووَسْمُه ومَرْوَحَتُه | اخْتِيارُ الأداة | هَلْ فَتَحَ البَديلُ "
            "جَذْرًا لَمْ يَكُنْ يُبْلَغ؟ | المَوْضِعُ |",
            "|---:|---|---|---|---|---|---|---|---|",
        ]
        for index, card in enumerate(rows, 1):
            skeletons = card.skeletons or []
            original = skeleton_form(skeletons[0], card) if skeletons else "لا هَيْكَلَ"
            lines.append(
                f"| {index} | {north_form(card.word, card.language)} | "
                f"{annotate_north(card.gloss, card.language)} [Kaikki {language.title()}] | "
                f"{ending_form(card.ending, card.language)} | {original} | "
                f"{alternatives_form(card)} | {pick_form(card)} | "
                f"{opened_form(card)} | {source_form(card)} |"
            )
        lines.append("")

    lines += [
        "---",
        "",
        "*English abstract.* This exploratory riddle sheet inventories every deduplicated "
        "Aramaic and Hebrew reading card whose headword carries one of the selected state, "
        "gender, or plural endings. Every skeleton returned by the northern word tool is "
        "expanded into its complete Arabic candidate fan and retained only where the local "
        "Arabic lexicon store attests the root. Hamza folding follows the repository rule, "
        "including bare hamza to alif, so roots such as ra's remain reachable. Rows opened by "
        "an alternate skeleton are presented first. Semantic overlap ranks candidates for "
        "inspection but issues no linguistic verdict.",
    ]
    return "\n".join(lines) + "\n"


def notable_cards(cards: list[Card], limit: int = 10) -> list[Card]:
    opened = [card for card in cards if card.opened]
    out: list[Card] = []
    for word, gloss_needle, _ in NOTABLES:
        card = next(
            (
                item
                for item in opened
                if clean_north(item.word) == clean_north(word)
                and gloss_needle in item.gloss.lower()
            ),
            None,
        )
        if card and card not in out:
            out.append(card)
    for card in sorted(
        opened,
        key=lambda item: (
            -item.machine_score,
            not item.machine_direct,
            len(item.opened_roots or []),
            item.language,
            clean_north(item.word),
        ),
    ):
        if card not in out:
            out.append(card)
        if len(out) >= limit:
            break
    return out[:limit]


def notable_root(card: Card) -> str:
    for word, gloss_needle, root in NOTABLES:
        if (
            clean_north(card.word) == clean_north(word)
            and gloss_needle in card.gloss.lower()
        ):
            return root
    return card.machine_pick


def render_audit(cards: list[Card]) -> str:
    opened = sum(card.opened for card in cards)
    counts = {
        language: Counter(card.ending for card in cards if card.language == language)
        for language, _ in LANGUAGES
    }
    lines = [
        "# مَحْضَرُ نِهاياتِ الحالِ والجَمْعِ في الشَّمالِ السَّامِيّ",
        "",
        "**التاريخ:** 2026-08-10. **الطَّبقة:** استكشاف. **لا حُكْمَ في بِطاقةٍ "
        "ولا تَعْديلَ في مَلَفَّي القِراءات.**",
        "",
        "## قَرارُ المُؤَلِّف",
        "",
        f"عُرِضَتْ عليه الآرامِيَّةُ {north_form('עסקתא', 'aramaic')} فقالَ بِنَصِّهِ: "
        "«من السهلِ الواضحِ أن تنزعَ الـ ta من الكلمةِ لتراها أحسن، ʿsaq عَسْق، "
        "قد تكونُ موصولةً بـعشق أو غسق».",
        "",
        f"وعُرِضَتْ {north_form('פערא', 'aramaic')} فقالَ بِنَصِّهِ: «كما نعلمُ "
        "الألفُ الأخيرةُ ليست أصليّةً في الآراميّةِ والعبريّة، هي طريقةُ نطقِهم "
        "والجذرُ يبقى، فعْرا ← فغر، واضحٌ جدًّا».",
        "",
        "هذا العَطَبُ هُوَ الفَصيلَةُ الثَّالِثَةُ مِن عَطَبِ **«الصَّرْفُ يُحْسَبُ "
        "أَصْلًا»**، بَعْدَ لاحِقَةِ `*-tḗr` وسِينِ الرَّفْعِ في `rēx`. في المَرَّاتِ "
        "الثَّلاثِ دَخَلَتْ عَلامَةٌ صَرْفِيَّةٌ في الهَيْكَلِ الَّذي تُوَلِّدُ مِنْهُ "
        "المَرْوَحَة، فَحُجِبَ جَذْرٌ كانَ يَظْهَرُ بَعْدَ التَّعْرِيَة.",
        "",
        "## الجَرْد",
        "",
        "وَحْدَةُ الجَرْدِ هِيَ البِطاقةُ أو المُراجَعَةُ العُضْوِيَّةُ ذاتُ "
        "المُعَرِّفِ المُسْتَقِلّ، مَعَ تَوْحيدِ كُلِّ إعادَةٍ لِلمُعَرِّفِ نَفْسِهِ. "
        "جاءَ الجَرْدُ كَالآتي:",
        "",
        "| النِّهايَةُ ونُطْقُها | الآرامِيَّة | العِبْرِيَّة | المَجْموع |",
        "|---|---:|---:|---:|",
    ]
    for ending, _ in northern.NORTH_ENDINGS:
        aramaic = counts["aramaic"][ending]
        hebrew = counts["hebrew"][ending]
        lines.append(
            f"| {ending_form(ending, 'aramaic')} | {aramaic} | {hebrew} | "
            f"{aramaic + hebrew} |"
        )
    lines += [
        f"| **المَجْموع** | **{EXPECTED['aramaic']['total']}** | "
        f"**{EXPECTED['hebrew']['total']}** | **525** |",
        "",
        f"مَسَّتْ إعادَةُ المَرْوَحَةِ **525 بِطاقةً**. وفَتَحَ واحِدٌ مِنَ "
        f"الهَياكِلِ البَديلَةِ جَذْرًا مَعْجَمِيًّا لَمْ يَكُنْ يُبْلَغُ مِنَ "
        f"الهَيْكَلِ «كما وَرَدَتْ» في **{opened} بِطاقةً**. هذا وَصْفٌ لِناتِجِ "
        "الأداةِ في طَبَقَةِ الاستكشاف، لا رَقْمُ تَحَقُّقٍ ولا حُكْمُ نَسَب.",
        "",
        "## أَبْرَزُ عَشَرَةِ أَمْثِلَة",
        "",
        "| # | اللِّسانُ | الكَلِمَةُ ونُطْقُها | المَعْنى المَنْشور | "
        "مَرْوَحَةُ «كما وَرَدَتْ» | ما فَتَحَهُ البَديلُ | اخْتِيارُ الأداة |",
        "|---:|---|---|---|---|---|---|",
    ]
    for index, card in enumerate(notable_cards(cards), 1):
        lines.append(
            f"| {index} | {card.language_ar} | {north_form(card.word, card.language)} | "
            f"{annotate_north(card.gloss, card.language)} | "
            f"{roots_form(card.original_roots or [])} | "
            f"{roots_form(card.opened_roots or [], notable_root(card))} | "
            f"{pick_form(card)} |"
        )
    lines += [
        "",
        "## حَدُّ النَّتيجَة",
        "",
        "لَمْ تُصْدِرِ الإعادَةُ حُكْمًا في أَيِّ بِطاقة، ولَمْ تَكْتُبْ في "
        "`04-cross-linguistic/readings/`. وَظيفَتُها تَوْسيعُ الاسْتِرْجاعِ وَعَرْضُ "
        "المَرْوَحَةِ لِعَيْنِ المُؤَلِّف. اخْتِيارُ الأداةِ تَرْتيبُ نَظَرٍ "
        "بِتَقاطُعِ أَلْفاظِ المَعْنى، وقد يُصيبُ أو يُخْطِئ.",
        "",
        "---",
        "",
        "*English abstract.* The author's two rulings identify a third instance of the "
        "same retrieval defect: inflectional material was counted as lexical root material, "
        "after the earlier *-ter suffix and nominative *-s cases. The deduplicated inventory "
        "contains 525 Aramaic and Hebrew cards bearing the selected endings. Every skeleton "
        "returned by the northern tool was expanded, hamza-folded, checked against the local "
        "Arabic lexicon store, and ranked against the published branch gloss. The count of "
        "cards gaining a previously unreachable dictionary root is reported as exploratory "
        "tool output only. No reading card was changed and no verdict was issued.",
    ]
    return "\n".join(lines) + "\n"


def validate_text(text: str, name: str) -> None:
    if text != nfc(text):
        raise RuntimeError(f"النصُّ غيرُ مطبَّعٍ NFC: {name}")
    if "—" in text or "–" in text:
        raise RuntimeError(f"تسرَّبت شرطةٌ طويلةٌ إلى {name}")
    for line_number, line in enumerate(text.splitlines(), 1):
        for match in NORTH_RUN.finditer(line):
            if match.start() == 0 or line[match.start() - 1] != "`":
                raise RuntimeError(
                    f"خطٌّ شماليٌّ عارٍ في {name}:{line_number}: {match.group(0)}"
                )
            if not line[match.end():].startswith("` · **"):
                raise RuntimeError(
                    f"خطٌّ شماليٌّ بلا نطقٍ في {name}:{line_number}: {match.group(0)}"
                )


def write_or_check(path: Path, text: str, check: bool) -> None:
    if check:
        if not path.exists() or path.read_text(encoding="utf-8") != text:
            raise RuntimeError(f"الناتجُ بائتٌ أو مفقود: {path.relative_to(ROOT)}")
        return
    path.write_text(text, encoding="utf-8", newline="\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    cards = [
        card
        for language, language_ar in LANGUAGES
        for card in cards_of(language, language_ar)
    ]
    validate_inventory(cards)
    attach_glosses(cards)
    attach_fans(cards)
    validate_regressions(cards)

    sheet = nfc(render_sheet(cards))
    audit = nfc(render_audit(cards))
    validate_text(sheet, OUT.name)
    validate_text(audit, AUDIT.name)
    write_or_check(OUT, sheet, args.check)
    write_or_check(AUDIT, audit, args.check)

    summary = {
        "cards": len(cards),
        "aramaic": sum(card.language == "aramaic" for card in cards),
        "hebrew": sum(card.language == "hebrew" for card in cards),
        "opened": sum(card.opened for card in cards),
    }
    print(" · ".join(f"{key}={value}" for key, value in summary.items()))
    print(OUT.relative_to(ROOT).as_posix())
    print(AUDIT.relative_to(ROOT).as_posix())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
