#!/usr/bin/env python3
"""Lane C read-only retrieval and local discovery-card writer.

The shared recovery databases, frozen network, source snapshots, and Arabic
lexica are opened read-only.  The only outputs are lane-C-prefixed data and
append-only sections in the six reading files owned by lane C.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sqlite3
import sys
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import pyarrow.parquet as pq


ROOT = Path(__file__).resolve().parents[1]
READINGS = ROOT / "04-cross-linguistic" / "readings"
RANKED_OUTPUT = (
    ROOT
    / "04-cross-linguistic"
    / "data"
    / "lane_c_ie_discovery_ranked.json"
)
RESULTS_OUTPUT = (
    ROOT
    / "04-cross-linguistic"
    / "data"
    / "lane_c_ie_discovery_results.json"
)
QUEUE_PATH = (
    ROOT
    / "cache"
    / "recovery_pipeline"
    / "week17-day1"
    / "member-strength-queues.json"
)
ARABIC_ROOTS_PATH = (
    ROOT
    / "Resources"
    / "arabic_roots_hf"
    / "train-00000-of-00001.parquet"
)


@dataclass(frozen=True)
class LanguageConfig:
    key: str
    reading_file: str
    db_path: str
    source_label: str
    required_new_cards: int
    pool_limit: int


LANGUAGES = (
    LanguageConfig(
        "ancient_greek",
        "ancient-greek.md",
        "cache/recovery_pipeline/inventory-v5.sqlite",
        "Kaikki Ancient Greek",
        86,
        420,
    ),
    LanguageConfig(
        "latin",
        "old-latin.md",
        "cache/recovery_pipeline/inventory-v5.sqlite",
        "Kaikki Latin",
        34,
        240,
    ),
    LanguageConfig(
        "persian",
        "persian.md",
        "cache/recovery_pipeline/week17-day1-inventory.sqlite",
        "Kaikki Persian",
        192,
        650,
    ),
    LanguageConfig(
        "gothic",
        "gothic.md",
        "cache/recovery_pipeline/week17-day1-inventory.sqlite",
        "Kaikki Gothic",
        197,
        650,
    ),
    LanguageConfig(
        "old_norse",
        "old-norse.md",
        "cache/recovery_pipeline/week17-day1-inventory.sqlite",
        "Kaikki Old Norse",
        192,
        650,
    ),
    LanguageConfig(
        "welsh",
        "welsh.md",
        "cache/recovery_pipeline/week17-day1-inventory.sqlite",
        "Kaikki Welsh",
        100,
        420,
    ),
)

BAD_POS = {
    "abbrev",
    "character",
    "circumfix",
    "infix",
    "interfix",
    "letter",
    "name",
    "phrase",
    "prefix",
    "proper noun",
    "punct",
    "romanization",
    "suffix",
    "symbol",
}

ENGLISH_STOP_WORDS = {
    "a",
    "about",
    "accord",
    "after",
    "again",
    "also",
    "an",
    "and",
    "another",
    "any",
    "are",
    "as",
    "at",
    "be",
    "because",
    "been",
    "before",
    "being",
    "between",
    "both",
    "but",
    "by",
    "called",
    "can",
    "could",
    "does",
    "either",
    "especially",
    "etc",
    "for",
    "form",
    "from",
    "had",
    "has",
    "have",
    "he",
    "her",
    "here",
    "him",
    "his",
    "i",
    "if",
    "in",
    "into",
    "is",
    "it",
    "its",
    "latter",
    "like",
    "means",
    "more",
    "most",
    "not",
    "of",
    "on",
    "one",
    "only",
    "or",
    "other",
    "our",
    "said",
    "same",
    "see",
    "she",
    "signifies",
    "so",
    "some",
    "such",
    "than",
    "that",
    "the",
    "their",
    "them",
    "then",
    "there",
    "these",
    "they",
    "this",
    "those",
    "to",
    "two",
    "used",
    "was",
    "we",
    "were",
    "when",
    "where",
    "which",
    "while",
    "who",
    "with",
    "would",
    "you",
}
TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z-]+")


# Each positive below was reviewed manually after retrieval.  The absence of an
# entry from this allowlist is never interpreted as a negative judgment.
POSITIVE_ALLOWLIST: dict[str, dict[str, str]] = {
    # Ancient Greek
    "kaikki_ancient_greek:4884:en-φράζω-grc-verb-pMMD3dH6": {
        "arabic_form": "برز",
        "orbit": "مدار 2: الحدث والأثر؛ الإظهار في الفرع إحداث بروز المعنى من الخفاء إلى الظهور",
        "rationale": "المعنى المنشور فعل إظهار، وقراءة برز فعل ظهور قوي؛ الالتقاء في خروج الخفي إلى الظاهر بخطوة واحدة",
    },
    "kaikki_ancient_greek:18062:en-κορύνη-grc-noun-N7z6x9SI": {
        "arabic_form": "قرن",
        "orbit": "مدار 3: الآلة والهيئة؛ رأس الهراوة الناتئ الغليظ يلتقي بنتوء القرن في المقدمة",
        "rationale": "المصدر يصف هراوة ذات رأس حديدي، وقراءة قرن تصف نتوءًا ممتدًا في أعلى الجسم أو مقدمه",
    },
    # Latin
    "kaikki_latin:83239:en-cavum-la-noun-GinBU6b0": {
        "arabic_form": "جوب",
        "orbit": "مدار 2: الحدث والأثر؛ الجوف أو الحفرة أثر قطع وسط الجرم وإخراج مادته",
        "rationale": "معنى الفرع حفرة وتجويف وفتحة، وقراءة جوب تصف قطع الوسط الصلب قطعًا مستديرًا",
    },
    "kaikki_latin:15418:en-separo-la-verb-wNp9ewpz": {
        "arabic_form": "صور",
        "orbit": "مدار 2: الحدث والأثر؛ الفصل يرسم حدًا يميز الشيء عما حوله",
        "rationale": "الفرع ينص على التقسيم والفصل، وقراءة صور على حدود تميز الهيئة عن غيرها",
    },
    "kaikki_latin:58261:en-abutor-la-verb-DK7N~8eG": {
        "arabic_form": "بتر",
        "orbit": "مدار 2: الحدث والأثر؛ الاستنفاد يقطع امتداد الرصيد حتى نهايته",
        "rationale": "الفرع ينص على الاستهلاك التام، وبتر قطع لما يمتد من الشيء؛ الرجل دلالية لينة لكنها خطوة واحدة",
    },
    "kaikki_latin:82528:en-tergeo-la-verb-4-NB6HYc": {
        "arabic_form": "ترك",
        "orbit": "مدار 2: الحدث والأثر؛ المسح والتنظيف يتركان السطح خاليًا مما كان عالقًا به",
        "rationale": "معنى الفرع إزالة الوسخ بالمسح، وقراءة ترك مفارقة الشيء لما كان يعلق به",
    },
    # Persian
    "kaikki_persian_2026_07_23:8924:en-گرامی-fa-adj-2Ht8PO3P": {
        "arabic_form": "كرم",
        "orbit": "مباشر في عائلة النفاسة والامتياز وقبول النفس",
        "rationale": "الفرع ينص على النفاسة والامتياز، وقراءة كرم على النقاء مع قبول النفس",
    },
    "kaikki_persian_2026_07_23:3216:en-گناه-fa-noun-zMxox5KO": {
        "arabic_form": "جنح",
        "orbit": "مدار 2: الحدث والأثر؛ الذنب أثر جنوح وانحراف عن الجهة المستقيمة",
        "rationale": "معنى الفرع الذنب، وقراءة جنح حركة جانبية؛ الالتقاء في الانحراف بخطوة واحدة",
    },
    "kaikki_persian_2026_07_23:10785:en-سوار-fa-noun-4WgfKbBd": {
        "arabic_form": "سور",
        "orbit": "مدار 4: الفاعل؛ الراكب متناول لدابته من أعلاها ومحيط بمقعده",
        "rationale": "معنى الفرع راكب، وقراءة سور إحاطة أو تناول من الأعلى",
    },
    "kaikki_persian_2026_07_23:14039:en-کران-fa-noun-SCyoBQZw": {
        "arabic_form": "قرن",
        "orbit": "مدار 5: المكان والهيئة؛ الحافة نتوء ممتد يحد ظاهر الشيء",
        "rationale": "الفرع ينص على الحد والحافة، وقراءة قرن على نتوء ممتد في المقدمة أو الأعلى",
    },
    # Gothic
    "kaikki_gothic_2026_07_23:21033:en-𐌲𐌰𐌽𐌰𐌿𐌷𐌰-got-noun-eZ1FIQX9": {
        "arabic_form": "قنع",
        "orbit": "مدار 6: الحالة؛ الكفاية بلوغ حد يشتمل على الحاجة فلا يطلب الخارج",
        "rationale": "الفرع ينص على الكفاية، وقراءة قنع على الاشتمال والاحتواء؛ المروحة القديمة تحفظ القناعة والاكتفاء",
    },
    "kaikki_gothic_2026_07_23:592:en-𐌼𐌰𐌲𐌰𐌽-got-verb-dS~XP4x~": {
        "arabic_form": "مكن",
        "orbit": "مباشر في عائلة القدرة والتمكن",
        "rationale": "الفرع ينص على الاستطاعة، والمروحة العربية لمكن تحفظ التمكن والقدرة مع القراءة المحورية للرسوخ",
    },
    "kaikki_gothic_2026_07_23:18275:en-𐍃𐌹𐌿𐌺𐌰𐌽-got-verb-iwU9hZpQ": {
        "arabic_form": "سقم",
        "orbit": "مباشر في عائلة المرض والسقم",
        "rationale": "المعنى المنشور مرض، وقراءة سقم تصف تغير البدن على غير المعتاد بسبب ما في باطنه",
    },
    "kaikki_gothic_2026_07_23:13716:en-𐌰𐌲𐌻𐌿𐌱𐌰-got-adv-~ASLTPc~": {
        "arabic_form": "كلف",
        "orbit": "مدار 6: الحالة؛ الصعوبة كلفة عارضة لازمة تثقل الفعل",
        "rationale": "الفرع ينص على الصعوبة، والمروحة العربية تحفظ الكلفة والمشقة مع قراءة العارض الغريب اللازم",
    },
    "kaikki_gothic_2026_07_23:21250:en-𐌿𐍃𐌻𐌿𐌺-got-noun-Kz~fBcTd": {
        "arabic_form": "سلك",
        "orbit": "مباشر في الفتحة التي ينفذ عبرها الشيء",
        "rationale": "معنى الفرع فتحة، وقراءة سلك نفاذ في أثناء ضيقة بدقة وامتداد",
    },
    "kaikki_gothic_2026_07_23:430:en-𐌰𐌺𐍂𐌰𐌽-got-noun-kglSaqph": {
        "arabic_form": "جرم",
        "orbit": "مدار 2: الحدث والمحصول؛ الثمرة جسم المحصول الذي ينتهي إليه الحصاد",
        "rationale": "الفرع ينص على الثمرة، وقراءة جرم على حصد عذوق التمر بعد تمام حالها",
    },
    "kaikki_gothic_2026_07_23:10967:en-𐌺𐌰𐌿𐍂𐌽-got-noun-got:Q2995529": {
        "arabic_form": "جرم",
        "orbit": "مدار 2: الحدث والمحصول؛ الحب مادة المحصول المحصود عند تمامه",
        "rationale": "الفرع ينص على الحب المحصود، وقراءة جرم تصف حصاد الثمر عند تمامه",
    },
    "kaikki_gothic_2026_07_23:17764:en-𐍆𐍂𐌹𐌾𐌴𐌹-got-noun-QQmUwhUu": {
        "arabic_form": "فرج",
        "orbit": "مدار 6: الحالة؛ الحرية حالة انفتاح بعد ضيق أو حبس",
        "rationale": "الفرع ينص على الحرية، وقراءة فرج على انفتاح أو متسع بين الأجرام",
    },
    # Old Norse
    "kaikki_old_norse_2026_07_23:3433:en-herða-non-verb-VCYLvnn1": {
        "arabic_form": "غلظ",
        "orbit": "مباشر في التصليب وزيادة غلظ الجرم",
        "rationale": "الفرع ينص على التصليب، وقراءة غلظ على عظم الجرم وتَجَسُّمه مع الصلابة",
    },
    "kaikki_old_norse_2026_07_23:3179:en-vitra-non-verb-erZ6XCdy": {
        "arabic_form": "فطر",
        "orbit": "مدار 2: الحدث والأثر؛ الكشف خروج المخفي شاقًا ما يغطيه",
        "rationale": "الفرع ينص على الإظهار والكشف، وقراءة فطر على خروج أولي يشق ما فوقه",
    },
    "kaikki_old_norse_2026_07_23:2539:en-tign-non-noun-yO4N~n1f": {
        "arabic_form": "تقن",
        "orbit": "مدار 6: الحالة؛ الشرف والرفعة حكم بجودة الشيء في بابه",
        "rationale": "الفرع ينص على الشرف والرفعة، وقراءة تقن على جودة الشيء في جنسه",
    },
    "kaikki_old_norse_2026_07_23:2756:en-mygla-non-verb-02XVr-Tz": {
        "arabic_form": "بقل",
        "orbit": "مدار 2: الحدث والأثر؛ العفن نمو ضعيف يظهر على سطح المادة",
        "rationale": "الفرع ينص على نمو العفن، وقراءة بقل على شيء ينبت ضعيفًا في ظاهر شيء",
    },
    "kaikki_old_norse_2026_07_23:312:en-mold-non-noun-gVYb84dc": {
        "arabic_form": "بلد",
        "orbit": "مدار 5: المكان؛ التراب مادة السطح الأرضي المتسع المصمت",
        "rationale": "الفرع ينص على الأرض والتراب، وقراءة بلد على ظاهر متسع مصمت يحتبس فيه ما يتوقع نفاذه",
    },
    "kaikki_old_norse_2026_07_23:2107:en-fleyta-non-verb-4Ji6ArfM": {
        "arabic_form": "فرط",
        "orbit": "مباشر في دفع الشيء إلى الأمام وإطلاقه",
        "rationale": "الفرع ينص على التعويم والإطلاق، وقراءة فرط على اندفاع الشيء متقدمًا",
    },
    "kaikki_old_norse_2026_07_23:550:en-draga-non-verb-LLBoW2bK": {
        "arabic_form": "درج",
        "orbit": "مدار 2: الحدث والنقل؛ الجر حركة حمل أو نقل داخل مسار ضام",
        "rationale": "الفرع ينص على الجر والسحب، وقراءة درج على الضم للنقل برفق",
    },
    # Welsh
    "kaikki_welsh_2026_07_23:2623:en-gwan-cy-adj-SBukAZyd": {
        "arabic_form": "جبن",
        "orbit": "مدار 6: الحالة؛ الضعف أثر ظاهر صلب على باطن خاو أو رقيق",
        "rationale": "الفرع ينص على الضعف، وقراءة جبن على تجمد الظاهر مع خلاء أو رقة في الأثناء؛ المروحة تحفظ الجبن",
    },
    "kaikki_welsh_2026_07_23:26639:en-halogi-cy-verb-1Fv-mKNW": {
        "arabic_form": "هلك",
        "orbit": "مدار 2: الحدث والأثر؛ الإفساد يفرغ الشيء من جوهره وحقيقته",
        "rationale": "الفرع ينص على التدنيس والإفساد، وقراءة هلك على فراغ الجوف من الحقيقة والجوهر",
    },
    "kaikki_welsh_2026_07_23:5997:en-gadael-cy-verb-jBSTCqpA": {
        "arabic_form": "كدر",
        "orbit": "مباشر في الانقلاع والمفارقة والرحيل",
        "rationale": "الفرع ينص على الترك والرحيل، وقراءة كدر على انقلاع الغليظ أو انقطاعه مفارقًا مقره",
    },
    "kaikki_welsh_2026_07_23:4311:en-godro-cy-verb-h-sARU~y": {
        "arabic_form": "كدر",
        "orbit": "مدار 2: الحدث والمادة؛ الحلب اقتلاع مادة غليظة راسخة في وعائها وإخراجها",
        "rationale": "الفرع ينص على استخراج اللبن، وقراءة كدر على انقلاع الغليظ الراسخ مفارقًا مقره",
    },
}

# The post-append zero-step audit found that these surface matches consumed a
# consonant belonging to an inflectional/derivational element, a prefix, or a
# historically different restored stem.  They remain in the append-only record
# and are superseded by explicit retagging sections in the reading files.
RETRACTED_POSITIVE_IDS = {
    "kaikki_ancient_greek:4884:en-φράζω-grc-verb-pMMD3dH6",
    "kaikki_ancient_greek:18062:en-κορύνη-grc-noun-N7z6x9SI",
    "kaikki_latin:83239:en-cavum-la-noun-GinBU6b0",
    "kaikki_latin:15418:en-separo-la-verb-wNp9ewpz",
    "kaikki_latin:58261:en-abutor-la-verb-DK7N~8eG",
    "kaikki_persian_2026_07_23:3216:en-گناه-fa-noun-zMxox5KO",
    "kaikki_persian_2026_07_23:10785:en-سوار-fa-noun-4WgfKbBd",
    "kaikki_gothic_2026_07_23:592:en-𐌼𐌰𐌲𐌰𐌽-got-verb-dS~XP4x~",
    "kaikki_gothic_2026_07_23:18275:en-𐍃𐌹𐌿𐌺𐌰𐌽-got-verb-iwU9hZpQ",
    "kaikki_gothic_2026_07_23:13716:en-𐌰𐌲𐌻𐌿𐌱𐌰-got-adv-~ASLTPc~",
    "kaikki_gothic_2026_07_23:21250:en-𐌿𐍃𐌻𐌿𐌺-got-noun-Kz~fBcTd",
    "kaikki_gothic_2026_07_23:430:en-𐌰𐌺𐍂𐌰𐌽-got-noun-kglSaqph",
    "kaikki_gothic_2026_07_23:17764:en-𐍆𐍂𐌹𐌾𐌴𐌹-got-noun-QQmUwhUu",
    "kaikki_old_norse_2026_07_23:2539:en-tign-non-noun-yO4N~n1f",
    "kaikki_old_norse_2026_07_23:2756:en-mygla-non-verb-02XVr-Tz",
    "kaikki_welsh_2026_07_23:2623:en-gwan-cy-adj-SBukAZyd",
    "kaikki_welsh_2026_07_23:5997:en-gadael-cy-verb-jBSTCqpA",
    "kaikki_welsh_2026_07_23:4311:en-godro-cy-verb-h-sARU~y",
}
for retracted_id in RETRACTED_POSITIVE_IDS:
    POSITIVE_ALLOWLIST.pop(retracted_id)

POSITIVE_ALLOWLIST[
    "kaikki_ancient_greek:193:en-κεφαλή-grc-noun-ny5tM6Nx"
] = {
    "arabic_form": "جبل",
    "orbit": "مدار 3: الهيئة والعضو؛ الرأس كتلة غليظة مرتفعة في أعلى البدن",
    "rationale": "الصورة المستعادة *gʰebʰ-l̥ تحفظ الصوامت الثلاثة، ومعنى الرأس يلتقي بقراءة جبل في الكتلة العظيمة الغليظة المرتفعة",
}


def nfc(value: str) -> str:
    return unicodedata.normalize("NFC", value or "")


def batches(values: list[str], size: int = 300) -> Iterable[list[str]]:
    for start in range(0, len(values), size):
        yield values[start : start + size]


def ro_connection(path: Path) -> sqlite3.Connection:
    return sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)


def load_arabic_english_definitions() -> dict[str, str]:
    table = pq.read_table(
        ARABIC_ROOTS_PATH,
        columns=["root", "definition", "book_name"],
    )
    result: dict[str, str] = {}
    for row in table.to_pylist():
        if row["book_name"] == "المعجم العربي الإنجليزي":
            result[nfc(row["root"])] = nfc(row["definition"])
    return result


def load_classical_source_counts() -> dict[str, dict[str, int]]:
    table = pq.read_table(
        ARABIC_ROOTS_PATH,
        columns=["root", "book_name"],
    )
    result: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for row in table.to_pylist():
        root = nfc(row["root"])
        book = nfc(row["book_name"])
        if book in {
            "لسان العرب لابن منظور",
            "تاج العروس لمرتضى الزبيدي",
        }:
            result[root][book] += 1
    return {root: dict(counts) for root, counts in result.items()}


def load_queues() -> dict[str, list[dict[str, Any]]]:
    data = json.loads(QUEUE_PATH.read_text(encoding="utf-8"))
    return data["queues"]


def term_key(value: str) -> str:
    return nfc(value).strip().strip("`*_،,:؛()[]").casefold()


def existing_ids(
    reading_path: Path,
    language: str,
) -> tuple[set[str], set[str], set[str]]:
    text = reading_path.read_text(encoding="utf-8")
    families = set(re.findall(rf"{re.escape(language)}:family:[0-9a-f]+", text))
    entries = set(
        re.findall(
            r"(?:kaikki_[^:`\s]+(?::\d{4}_\d{2}_\d{2})?|kaikki_[^:`\s]+):"
            r"\d+:[^`\s\]]+",
            text,
        )
    )
    terms: set[str] = set()
    for line in text.splitlines():
        if not line.startswith("### بطاقة:"):
            continue
        body = line.removeprefix("### بطاقة:").strip()
        for quoted in re.findall(r"`([^`]+)`", body):
            key = term_key(quoted)
            if key and ":family:" not in key:
                terms.add(key)
        if "،" in body and ":family:" in body:
            body = body.split("،", 1)[1].strip()
        plain = re.split(r"[«،]", body, maxsplit=1)[0].strip()
        if plain:
            key = term_key(plain.split()[0])
            if key and not key.startswith("<"):
                terms.add(key)
    return families, entries, terms


def family_pool(
    con: sqlite3.Connection,
    config: LanguageConfig,
    queue_map: dict[str, list[dict[str, Any]]],
    used_families: set[str],
) -> list[tuple[str, int]]:
    if config.key in queue_map:
        result: list[tuple[str, int]] = []
        for rank, item in enumerate(queue_map[config.key], start=1):
            family_id = item["family_id"]
            if family_id in used_families:
                continue
            result.append((family_id, rank))
            if len(result) >= config.pool_limit:
                break
        return result

    rows = con.execute(
        """
        SELECT family_id
        FROM families
        WHERE language = ?
          AND candidate_bearing_member_count > 0
        ORDER BY candidate_bearing_member_count DESC,
                 member_count DESC,
                 family_id
        LIMIT ?
        """,
        (config.key, config.pool_limit + len(used_families)),
    ).fetchall()
    result = []
    for row in rows:
        family_id = row[0]
        if family_id in used_families:
            continue
        result.append((family_id, len(result) + 1))
        if len(result) >= config.pool_limit:
            break
    return result


def fetch_pair_rows(
    con: sqlite3.Connection,
    family_ids: list[str],
    used_entries: set[str],
    used_terms: set[str],
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for family_id in family_ids:
        family_row = con.execute(
            """
            SELECT member_count, lemma_count
            FROM families
            WHERE family_id = ?
            """,
            (family_id,),
        ).fetchone()
        if family_row is None:
            continue
        entry_rows = con.execute(
            """
            SELECT
                e.entry_id,
                e.headword,
                e.romanization,
                e.pos,
                e.gloss,
                e.etymology,
                e.loan_hint,
                e.form_of,
                e.alternative_of,
                e.skeleton
            FROM family_members fm INDEXED BY family_members_family
            JOIN entries e ON e.entry_id = fm.entry_id
            WHERE fm.family_id = ?
              AND e.licensed_candidate_count > 0
              AND e.form_of = 0
              AND e.alternative_of = 0
            ORDER BY e.loan_hint,
                     e.licensed_candidate_count DESC,
                     e.candidate_count DESC,
                     e.entry_id
            LIMIT 8
            """,
            (family_id,),
        ).fetchall()
        for entry_row in entry_rows:
            entry_id = nfc(entry_row[0])
            if entry_id in used_entries:
                continue
            if (
                term_key(entry_row[1]) in used_terms
                or term_key(entry_row[2]) in used_terms
            ):
                continue
            pos = nfc(entry_row[3]).lower()
            if pos in BAD_POS:
                continue
            if entry_row[6] or entry_row[7] or entry_row[8]:
                continue
            candidate_rows = con.execute(
                """
                SELECT
                    c.kind,
                    c.form,
                    c.status,
                    c.rule_ids_json,
                    c.route_flag,
                    a.reading
                FROM candidates c
                LEFT JOIN arabic_forms a
                  ON a.form = c.form
                 AND a.kind = c.kind
                WHERE c.entry_id = ?
                  AND c.status = 'licensed'
                  AND c.route_flag = 0
                """,
                (entry_id,),
            ).fetchall()
            for candidate_row in candidate_rows:
                result.append(
                    {
                        "family_id": nfc(family_id),
                        "family_member_count": int(family_row[0]),
                        "family_lemma_count": int(family_row[1]),
                        "entry_id": entry_id,
                        "headword": nfc(entry_row[1]),
                        "romanization": nfc(entry_row[2]),
                        "pos": nfc(entry_row[3]),
                        "gloss": nfc(entry_row[4]),
                        "etymology": nfc(entry_row[5]),
                        "skeleton": nfc(entry_row[9]),
                        "kind": nfc(candidate_row[0]),
                        "arabic_form": nfc(candidate_row[1]),
                        "candidate_status": nfc(candidate_row[2]),
                        "rule_ids": json.loads(candidate_row[3]),
                        "route_flag": bool(candidate_row[4]),
                        "arabic_reading": nfc(candidate_row[5]),
                    }
                )
    return result


def semantic_scores(
    rows: list[dict[str, Any]],
    english_definitions: dict[str, str],
) -> list[float]:
    scores = [0.0] * len(rows)
    root_tokens: dict[str, set[str]] = {}
    document_frequency: Counter[str] = Counter()
    for root, definition in english_definitions.items():
        tokens = {
            token.lower()
            for token in TOKEN_RE.findall(definition)
            if token.lower() not in ENGLISH_STOP_WORDS
        }
        root_tokens[root] = tokens
        document_frequency.update(tokens)
    document_count = len(root_tokens)

    for index, row in enumerate(rows):
        if row["kind"] != "root" or not row["gloss"]:
            continue
        definition_tokens = root_tokens.get(row["arabic_form"])
        if not definition_tokens:
            continue
        gloss_tokens = {
            token.lower()
            for token in TOKEN_RE.findall(row["gloss"])
            if token.lower() not in ENGLISH_STOP_WORDS
        }
        common = gloss_tokens & definition_tokens
        if not common:
            continue

        def weight(token: str) -> float:
            return math.log(
                (document_count + 1)
                / (document_frequency[token] + 1)
            ) + 1.0

        numerator = sum(weight(token) for token in common)
        gloss_weight = sum(weight(token) for token in gloss_tokens)
        definition_weight = sum(weight(token) for token in definition_tokens)
        scores[index] = numerator / math.sqrt(
            max(gloss_weight * definition_weight, 1.0)
        )
    return scores


def best_cards(
    rows: list[dict[str, Any]],
    ranks: dict[str, int],
    english_definitions: dict[str, str],
    source_counts: dict[str, dict[str, int]],
    count: int,
) -> list[dict[str, Any]]:
    scores = semantic_scores(rows, english_definitions)
    by_family: dict[str, list[tuple[float, dict[str, Any]]]] = defaultdict(list)
    for score, row in zip(scores, rows):
        candidate = dict(row)
        candidate["semantic_score"] = round(score, 6)
        candidate["classical_source_counts"] = source_counts.get(
            row["arabic_form"], {}
        )
        by_family[row["family_id"]].append((score, candidate))

    cards: list[dict[str, Any]] = []
    for family_id, pairs in by_family.items():
        pairs.sort(
            key=lambda pair: (
                pair[0],
                pair[1]["kind"] == "root",
                -len(pair[1]["rule_ids"]),
                bool(pair[1]["etymology"]),
            ),
            reverse=True,
        )
        best_score, best = pairs[0]
        same_entry = [
            item
            for _, item in pairs
            if item["entry_id"] == best["entry_id"]
        ]
        unique_candidates: dict[tuple[str, str], dict[str, Any]] = {}
        for item in same_entry:
            key = (item["kind"], item["arabic_form"])
            old = unique_candidates.get(key)
            if old is None or len(item["rule_ids"]) < len(old["rule_ids"]):
                unique_candidates[key] = item
        best["family_rank"] = ranks[family_id]
        best["tested_candidates"] = [
            {
                "kind": item["kind"],
                "form": item["arabic_form"],
                "reading": item["arabic_reading"],
                "rule_ids": item["rule_ids"],
                "classical_source_counts": item["classical_source_counts"],
            }
            for item in sorted(
                unique_candidates.values(),
                key=lambda item: (
                    item["kind"] != "root",
                    len(item["rule_ids"]),
                    item["arabic_form"],
                ),
            )[:24]
        ]
        cards.append(best)

    cards.sort(
        key=lambda card: (
            card["semantic_score"],
            card["kind"] == "root",
            -len(card["rule_ids"]),
            -card["family_rank"],
        ),
        reverse=True,
    )
    if len(cards) < count:
        raise RuntimeError(
            f"only {len(cards)} candidate-bearing families for requested {count}"
        )
    return cards[:count]


def build_ranked_output() -> dict[str, Any]:
    english_definitions = load_arabic_english_definitions()
    source_counts = load_classical_source_counts()
    queue_map = load_queues()
    output: dict[str, Any] = {
        "schema": "lane-c-ie-discovery-ranked-v1",
        "contract": {
            "judgment": "none; retrieval and ranking only",
            "proof_line": "frozen",
            "shared_databases": "read-only",
            "positive_verdicts": "manual allowlist required before append",
        },
        "languages": {},
    }
    for config in LANGUAGES:
        print(f"lane-c: ranking {config.key}", file=sys.stderr, flush=True)
        reading_path = READINGS / config.reading_file
        used_families, used_entries, used_terms = existing_ids(
            reading_path,
            config.key,
        )
        con = ro_connection(ROOT / config.db_path)
        try:
            pool = family_pool(
                con,
                config,
                queue_map,
                used_families,
            )
            ranks = dict(pool)
            rows = fetch_pair_rows(
                con,
                [family_id for family_id, _ in pool],
                used_entries,
                used_terms,
            )
        finally:
            con.close()
        cards = best_cards(
            rows,
            ranks,
            english_definitions,
            source_counts,
            config.required_new_cards,
        )
        output["languages"][config.key] = {
            "reading_file": config.reading_file,
            "required_new_cards": config.required_new_cards,
            "existing_family_ids_seen": len(used_families),
            "pool_size": len(pool),
            "cards": cards,
        }
        RANKED_OUTPUT.write_text(
            nfc(json.dumps(output, ensure_ascii=False, indent=2)) + "\n",
            encoding="utf-8",
            newline="\n",
        )
    return output


def print_review(output: dict[str, Any], top: int) -> None:
    for config in LANGUAGES:
        block = output["languages"][config.key]
        print(f"\n[{config.key}] {block['required_new_cards']} cards")
        for card in block["cards"][:top]:
            rules = ",".join(card["rule_ids"]) or "IDENTITY"
            print(
                "\t".join(
                    (
                        f"{card['semantic_score']:.4f}",
                        card["family_id"],
                        card["entry_id"],
                        card["headword"],
                        card["romanization"],
                        card["pos"],
                        card["gloss"].replace("\t", " ")[:180],
                        card["arabic_form"],
                        card["arabic_reading"],
                        rules,
                        card["etymology"].replace("\t", " ")[:180],
                    )
                )
            )


LOAN_MARKERS: dict[str, tuple[str, ...]] = {
    "ancient_greek": (
        "borrowed from",
        "from akkadian",
        "from egyptian",
        "from hebrew",
        "from latin",
        "from phrygian",
    ),
    "latin": (
        "borrowed from",
        "from ancient greek",
        "from arabic",
        "from etruscan",
        "from hebrew",
        "from old french",
    ),
    "persian": (
        "borrowed from",
        "from arabic",
        "from ancient greek",
        "from azerbaijani",
        "from english",
        "from french",
        "from hebrew",
        "from italian",
        "from japanese",
        "from latin",
        "from old turkic",
        "from turkic",
        "generic trademark",
    ),
    "gothic": (
        "borrowed from",
        "borrowing from",
        "calque of ancient greek",
        "from ancient greek",
        "from latin",
    ),
    "old_norse": (
        "borrowed from",
        "borrowing from",
        "from english",
        "from french",
        "from latin",
        "from middle english",
        "from middle low german",
        "from old french",
        "via latin",
    ),
    "welsh": (
        "borrowed from",
        "borrowing from",
        "from ancient greek",
        "from english",
        "from latin",
        "from middle english",
        "from old french",
        "from vulgar latin",
    ),
}


def clean_inline(value: str, limit: int = 480) -> str:
    cleaned = " ".join(nfc(value).replace("—", "،").split())
    cleaned = cleaned.replace("|", "¦")
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 1].rstrip() + "…"


def loan_marker(language: str, etymology: str) -> str:
    lowered = etymology.casefold()
    window = lowered[:320]
    if window.startswith(("perhaps", "possibly", "probably")):
        return ""
    if "iranian borrowing in turkic" in window:
        return ""
    for marker in LOAN_MARKERS[language]:
        index = window.find(marker)
        if index < 0:
            continue
        context = window[max(0, index - 48) : index]
        if any(
            hedge in context
            for hedge in ("perhaps", "possibly", "probably", "maybe")
        ):
            continue
        if "may also be a direct descendant" in window:
            continue
        if marker in lowered:
            return marker
    return ""


def source_fan_line(card: dict[str, Any]) -> str:
    counts = card.get("classical_source_counts", {})
    lisan = counts.get("لسان العرب لابن منظور", 0)
    taj = counts.get("تاج العروس لمرتضى الزبيدي", 0)
    candidates = card.get("tested_candidates", [])
    preview = []
    for item in candidates[:8]:
        rules = "+".join(item["rule_ids"]) or "تطابق ذاتي"
        reading = item["reading"] or "قراءة غير مسجلة"
        preview.append(
            f"{item['kind']} {item['form']} «{clean_inline(reading, 120)}» [{rules}]"
        )
    return (
        f"المادة الأولى {card['arabic_form']}: لسان العرب={lisan} سجلًا، "
        f"وتاج العروس={taj} سجلًا في الذخيرة المثبتة؛ "
        f"المرشحات المرخصة للعضو={len(candidates)}، وأبرزها: "
        + "؛ ".join(preview)
    )


def source_gap(card: dict[str, Any]) -> bool:
    if card["kind"] != "root":
        return False
    counts = card.get("classical_source_counts", {})
    return not (
        counts.get("لسان العرب لابن منظور", 0)
        and counts.get("تاج العروس لمرتضى الزبيدي", 0)
    )


def render_card(
    config: LanguageConfig,
    card: dict[str, Any],
    ordinal: int,
) -> tuple[str, str]:
    positive = POSITIVE_ALLOWLIST.get(card["entry_id"])
    marker = loan_marker(config.key, card["etymology"])
    if positive and positive["arabic_form"] != card["arabic_form"]:
        raise RuntimeError(
            f"positive form drift for {card['entry_id']}: "
            f"{card['arabic_form']} != {positive['arabic_form']}"
        )
    if positive and marker:
        raise RuntimeError(
            f"positive allowlist conflicts with loan marker for {card['entry_id']}"
        )

    if positive:
        state = "READY"
        verdict = "ROOT-TRACE"
        orbit = positive["orbit"]
        verdict_note = positive["rationale"]
        branch_supported = 1
        arabic_supported = 1
        outcome = "positive"
    elif marker:
        state = "READY"
        verdict = "LOANWORD"
        orbit = (
            "مباشر أو قريب في ظاهر المعنى حيث وجد، لكنه شاهد انتقال "
            "لا مدار نسب مستقل"
        )
        verdict_note = (
            f"المصفاة حسمت مسار تماس منشورًا بالعبارة `{marker}`؛ "
            "لم يحول التطابق إلى صلة مستقلة"
        )
        branch_supported = 0
        arabic_supported = 0
        outcome = "closure"
    elif source_gap(card):
        state = "SOURCE-GAP"
        verdict = "غير صادر"
        orbit = (
            "لم يصدر مدار موجب؛ مروحة المصدرين القديمين ناقصة للمادة "
            "الأولى، فلا إيجاب ولا إغلاق سلبي"
        )
        verdict_note = (
            "حفظت البطاقة المرشحات المرخصة ورفعت نقص المصدر بدل "
            "تحويله إلى NO-TRACE"
        )
        branch_supported = 0
        arabic_supported = 0
        outcome = "open"
    else:
        state = "OPEN-CANDIDATE"
        verdict = "غير صادر"
        orbit = (
            "لم يصدر مدار موجب من خطوة واحدة في المراجعة اليدوية؛ "
            "بقيت المرشحات ظاهرة ولا يعد غياب الحكم إغلاقًا"
        )
        verdict_note = (
            "ممر الاسترداد حفظ الجذر والنواة والمروحة، وممر التشكيك "
            "منع ترقية التشابه الصوتي بلا مدار"
        )
        branch_supported = 0
        arabic_supported = 0
        outcome = "open"

    display = card["headword"]
    if card["romanization"]:
        display += f" {card['romanization']}"
    rules = " + ".join(card["rule_ids"]) or "تطابق ذاتي في الهيكل المطبع"
    oldest = (
        clean_inline(card["etymology"])
        if card["etymology"]
        else "لا صورة أقدم مسماة في حقل الاشتقاق للعضو"
    )
    loan_line = (
        f"يعزل مسار تماس منشورًا: `{marker}` في حقل الاشتقاق"
        if marker
        else "لا مانح أجنبي مسمى في حقل اشتقاق العضو"
    )
    degree = "جذر كامل" if card["kind"] == "root" else "نواة"
    text = f"""
### بطاقة: `{card['family_id']}`، {display} (الموجة ج، {ordinal})
- إصدارُ البروتوكول: RECOVERY-v2؛ طور الاكتشاف، وخط البرهان مجمد.
- الكلمةُ في الفرع: {display} [{card['pos']}؛ `{card['entry_id']}`].
- أقدمُ صورةٍ مستعادة: {oldest} [{config.source_label}، حقل `etymology_text`].
- الخطوةُ صفر (التعرية بصرف الفرع): لم تطبق الموجة نزعًا آليًا؛ الهيكل الصامتي الصارم في الجرد `{card['skeleton']}`، وأي تحليل صرفي صريح في الأصل المنشور نافذ قبل الحكم البشري.
- درجةُ المقارنة: {degree}.
- مسحُ المعاني العربيّة: {source_fan_line(card)}.
- المقابلُ من اللسان: {card['arabic_form']} «{clean_inline(card['arabic_reading'], 220) or 'قراءة غير مسجلة'}» [الأداة المجمدة].
- مسارُ الصوت: {rules}؛ المرشح موسوم `licensed` و`route_flag=0` في الجرد؛ لا صف جديد.
- المعنى من قاموس الفرع: «{clean_inline(card['gloss'], 360)}» [{config.source_label}، العضو المسمى].
- المدار: {orbit}.
- المصفاة: {loan_line}.
- فصلُ المتجانسات والاقتراض: الحكم، إن صدر، لهذا العضو ولسلسلة معناه وحدها؛ لا وراثة عبر الأسرة أو المركب.
- مؤشر اليتم: الأسرة تضم {card['family_member_count']} عضوًا، منها {card['family_lemma_count']} لمّة؛ العدد وصف استرجاع لا قرينة حكم.
- إشعاع الأسرة في الفرع: الأعضاء المعجمية المدعومة={branch_supported}؛ سلاسل المعنى المدعومة={branch_supported}؛ حُد الدعم بالعضو المقروء ولم يورث لبقية الأسرة.
- إشعاع الأسرة في العربية: الأعضاء المعجمية المدعومة={arabic_supported}؛ سلاسل المعنى المدعومة={arabic_supported}؛ حُد الدعم بالمادة المسماة ومعناها المداري.
- جسورُ الاسترداد المفحوصة: الجذر الكامل؛ المرشحات المرخصة؛ النواة حيث حضرت؛ مروحة لسان العرب وتاج العروس؛ الأصل المنشور؛ القرض؛ المدار.
- حالةُ الإغلاق: {state}.
- الحكم (استكشاف): {verdict}.
- عدسة الاسترداد: لم يسقط مرشح مرخص بسبب أول ترجمة، وحُفظت القائمة الكاملة في `04-cross-linguistic/data/lane_c_ie_discovery_ranked.json`.
- عدسة التشكيك: {verdict_note}.
- ملاحظات: لا تشغيل لخط البرهان، ولا توقيع صف، ولا رقم منشور من طبقة التحقق.
"""
    return nfc(text), outcome


def append_discovery_cards(output: dict[str, Any]) -> dict[str, Any]:
    expected_positive_ids = set(POSITIVE_ALLOWLIST)
    present_positive_ids: set[str] = set()
    summary: dict[str, Any] = {
        "schema": "lane-c-ie-discovery-results-v1",
        "date": "2026-07-29",
        "proof_line": "frozen",
        "languages": {},
        "totals": {
            "cards": 0,
            "positive": 0,
            "closures": 0,
            "open": 0,
        },
    }
    rendered: dict[str, str] = {}

    for config in LANGUAGES:
        block = output["languages"][config.key]
        cards = block["cards"]
        if len(cards) != config.required_new_cards:
            raise RuntimeError(
                f"{config.key}: expected {config.required_new_cards}, got {len(cards)}"
            )
        marker = f"LANE-C-IE-DISCOVERY-2026-07-29:{config.key}"
        reading_path = READINGS / config.reading_file
        old_text = reading_path.read_text(encoding="utf-8")
        if marker in old_text:
            raise RuntimeError(f"append marker already exists in {reading_path}")

        counts = {"cards": len(cards), "positive": 0, "closures": 0, "open": 0}
        card_texts = []
        for ordinal, card in enumerate(cards, start=1):
            text, outcome = render_card(config, card, ordinal)
            card_texts.append(text)
            counts[outcome if outcome != "closure" else "closures"] += 1
            if card["entry_id"] in POSITIVE_ALLOWLIST:
                present_positive_ids.add(card["entry_id"])

        section = f"""

<!-- {marker} -->
## شهر الاكتشاف: فتح الطبقة الهندوأوروبية، المسار ج (2026-07-29)

### بيان النطاق

أُلحقت {len(cards)} بطاقة جديدة من أسر لم تحمل بطاقة فعلية سابقة في هذا الملف. بدأ السحب من طابور قوة المرشح أو من الأسر الحاملة لمرشح مرخص، ثم رتبت المقابلات بمشترك دلالي للاسترجاع فقط. لم يصدر الترتيب حكمًا. كل موجب أدناه مدرج في قائمة سماح بشرية صريحة، وكل ما عداها بقي قرضًا معزولًا أو مرشحًا مفتوحًا. لا خط برهان، ولا صف صوتي جديد، ولا بناء لملف مشترك.

{''.join(card_texts)}
<!-- /{marker} -->
"""
        rendered[config.key] = nfc(old_text.rstrip() + section + "\n")
        summary["languages"][config.key] = counts
        for key in ("cards", "positive", "closures", "open"):
            summary["totals"][key] += counts[key]

    missing = expected_positive_ids - present_positive_ids
    if missing:
        raise RuntimeError(
            "positive allowlist entries absent after duplicate filtering: "
            + ", ".join(sorted(missing))
        )
    if summary["totals"]["cards"] != sum(
        config.required_new_cards for config in LANGUAGES
    ):
        raise RuntimeError("unexpected total card count")

    for config in LANGUAGES:
        (READINGS / config.reading_file).write_text(
            rendered[config.key],
            encoding="utf-8",
            newline="\n",
        )
    RESULTS_OUTPUT.write_text(
        nfc(json.dumps(summary, ensure_ascii=False, indent=2)) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--rank",
        action="store_true",
        help="build the lane-C ranked retrieval artifact",
    )
    parser.add_argument(
        "--review",
        type=int,
        metavar="N",
        help="print the top N ranked cards per language",
    )
    parser.add_argument(
        "--append",
        action="store_true",
        help="append reviewed lane-C cards to the six owned reading files",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.rank and args.review is None and not args.append:
        raise SystemExit("choose --rank, --review N, and/or --append")
    output: dict[str, Any]
    if args.rank:
        output = build_ranked_output()
    else:
        output = json.loads(RANKED_OUTPUT.read_text(encoding="utf-8"))
    if args.review is not None:
        print_review(output, args.review)
    if args.append:
        summary = append_discovery_cards(output)
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
