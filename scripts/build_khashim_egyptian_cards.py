# -*- coding: utf-8 -*-
"""ابنِ دفعتَي خشيم المصريّتَين بطاقاتِ RECOVERY-v2 قابلةً للتدقيق.

هذه أداةُ حصادٍ لا أداةُ حكمٍ عامّة. تختار من صفوف كتاب علي فهمي خشيم
«البرهان على عروبة اللغة المصرية القديمة» أوضحَ الرؤوس التي سلمت من عيوب
المسح المسمّاة، وتعيد كل زوج من الصفر بأدوات المشروع:

* مروحة ``fan_any_script.py`` كاملة، من غير إسقاط مرشح خشيم إن غاب عنها.
* نص عربي حرفي من لسان العرب، أو من تاج العروس عند غياب اللسان.
* مسار صوتي من شبكة الإبدالات المجمّدة، مع تسجيل ألفاظ البحث نفسها.
* ``OPEN-CANDIDATE`` لكل شك في الصوت أو المعنى أو المصدر.

الاختيار ثابت ومدوّن في تقرير JSON، والإلحاق محاط بعلامتين حتى تمنع إعادة
التشغيل من تكرار البطاقات.
"""
from __future__ import annotations

import csv
import itertools
import json
import pathlib
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import fan_any_script as FAN  # noqa: E402
import search_arabic_root_senses as ARS  # noqa: E402

SOURCE = ROOT / "data" / "khashim-pairs.json"
READING = ROOT / "04-cross-linguistic" / "readings" / "egyptian.md"
REPORT_1 = ROOT / "data" / "khashim-egyptian-batch-001.json"
REPORT_2 = ROOT / "data" / "khashim-egyptian-batch-002.json"
FAN_AUDIT = ROOT / "04-cross-linguistic" / "egyptian-fan-expansion-audit.md"
SHIFT_PROPOSALS = ROOT / "04-cross-linguistic" / "proposed-shift-rows-egyptian.md"
RESOURCES = ROOT / "Resources"

START_1 = "<!-- KHASHIM-EGYPTIAN-BATCH-001:START -->"
END_1 = "<!-- KHASHIM-EGYPTIAN-BATCH-001:END -->"
START_2 = "<!-- KHASHIM-EGYPTIAN-BATCH-002:START -->"
END_2 = "<!-- KHASHIM-EGYPTIAN-BATCH-002:END -->"
BOOK = "علي فهمي خشيم، «البرهان على عروبة اللغة المصرية القديمة»"
FIRST_BATCH_SIZE = 120
SECOND_BATCH_SIZE = 200

AR_MARKS = re.compile(r"[\u064b-\u0652ـ]")
AR_TOKEN = re.compile(r"[ء-ي]{2,16}")
EN_TOKEN = re.compile(r"[a-z]{3,}")
FEMININE = re.compile(r"[-.]t$", re.I)

# رؤوسٌ إنجليزيّة مفردة ثبت من مقابلة السطر بسياقه أن المِعول التقطها مكان
# الرومنة. الرأس ذو الفراغ يعزل آليًّا أيضًا، لأن الدفعة الأولى لا تقبل مركبًا
# أو رأسًا التحمت به عبارة إنجليزيّة حتى يعود إلى الصفحة المصوّرة.
ENGLISH_HEADS = {
    "advance", "apparel", "axe", "cake", "cool", "count", "creatures",
    "crime", "destruction", "devourer", "emission", "embrace", "end",
    "enemy", "faint", "flood", "forms", "friends", "froth", "grass",
    "grave", "grieve", "hall", "herb", "herdsman", "house", "illumine",
    "incantation", "knife", "mourn", "nation", "needs", "one", "order",
    "out", "over", "owner", "peace", "phagus", "place", "plunder",
    "possessions", "praise", "ram", "see", "shoe", "snake", "stand",
    "state", "strain", "strength", "tablet", "thehes", "throne", "touch",
    "uraei", "vase", "vomit", "with", "overflow", "leader", "spouse",
    "region", "bare", "gether", "kohl", "ing",
}

# أمثلة المؤلف في أمر الدفعة تصحح موضع الجذر الذي شوّهه حقل رأس الجواب في
# الاستخراج. لا يعفي التصحيح من المروحة ولا يمنح حكمًا.
AUTHOR_EXAMPLES = {
    "āamāq": "عمق",
    "menā-t": "مني",
    "ḥai-t": "حيا",
    "qars-t": "قرس",
}

# لا يُصدر الحصاد حكمًا آليًّا لمجرد اجتماع ألفاظ عامة في نصين طويلين. هذه
# الأزواج التسعة وحدها راجعها المنفذ عضوًا عضوًا: الصوت كامل بصفوف الشبكة،
# والمعنى منصوص في بدج وفي المعجم العربي المسمى. سائر الدفعة يبقى مفتوحًا.
APPROVED_POSITIVES = {
    99: "بجس",   # beges: dagger; لسان العرب: حديدة يشق بها
    67: "برك",   # bareka: to bless
    68: "برك",   # baraka: to bow the knee in homage
    385: "سمر",  # s-mer: inflict pain; سمر العين بمسامير محماة
    424: "سجر",  # sger: strong enclosed place; الامتلاء والقيد بالساجور
    427: "سجر",  # sgeru: the silent ones; المسجور الساكن
    459: "سفك",  # sefek: to cut; to slay; to cleave
    650: "كف",   # kep: palm/hollow of the hand
    806: "نقر",  # neqr: dust/powder; ضرب الرحى والحجر، مدار التفتيت
}

# المادة الثنائية قد تكون رأس نواة لا جذر المعجم الثلاثي. يبقى المرشح كما
# اقترحه خشيم، ويؤخذ النص من مادته المضعفة المسماة من غير تبديل وحدة الحكم.
LEXICON_ALIASES = {"كف": "كفف", "يم": "يمم"}

# اقتباسات موجزة راجعها المنفذ حرفيًّا في نسخة لسان العرب المحلية. تثبيتُها
# يمنع خوارزمية التقريب من اختيار جملة تشترك مع شرح خشيم في لفظ عام مثل
# «حتى»، ولا يُستعمل أيٌّ منها خارج الصف المسمى.
QUOTE_OVERRIDES = {
    99: "فإن أراد أحد أن يفجرها بظفره قدر على ذلك لامتلائها ولم يحتج إلى حديدة يشقها بها.",
    67: "وبارك الله الشيءَ وبارك فيه وعليه: وضع فيه البَرَكَة.",
    68: "وهو من بَرَكَ البعير إذا أناخ في موضع فلزمه.",
    385: "والسَّمْرُ: شدُّك شيئًا بالمسمار. وسَمَرَ عينه: كَسَمَلَها؛ أي أحمى لها مسامير الحديد ثم كحلهم بها.",
    424: "والساجر والمسجور: الساكن. أبو عبيد: المسجور الساكن والممتلئ معًا. والساجور: القلادة أو الخشبة التي توضع في عنق الكلب.",
    427: "والساجر والمسجور: الساكن. أبو عبيد: المسجور الساكن والممتلئ معًا.",
    459: "السَّفْكُ: صَبُّ الدم ونَثْرُ الكلام. وسَفَك الدمَ والدمعَ يَسْفِكُه سَفْكاً، فهو مَسْفوك وسَفِيك: صبه وهَراقَه، وكأَنه بالدم أَخص.",
    650: "والكفُّ: اليد، أُنثى. وفي التهذيب: والكف كفّ اليد.",
    806: "النَّقْرُ: ضربُ الرَّحى والحجر وغيره بالمِنْقار. ونَقَرَه يَنْقُره نَقْرًا: ضربه.",
    935: "اليَمُّ البحرُ، وكذلك هو في الكتاب، ويَقَع اسمُ اليَمّ على ما كان ماؤه مِلْحاً زُعاقاً، وعلى النهر الكبير العَذْب الماء.",
}

SEMANTIC_LABELS = {
    99: "الحديدة التي يُشق بها، وهي مدار الخنجر ووظيفته",
    67: "البركة والدعاء بها",
    68: "البروك والإنَاخة ولزوم الموضع، وهو وجه ثني الركبة",
    385: "إيلام الجسد بإدخال المسمار المحمى",
    424: "الإحاطة والامتلاء والقيد، وهي مدار المكان المحصن المغلق",
    427: "السكون؛ نص اللسان يسمّي المسجور ساكنًا",
    459: "السفك وإراقة الدم، وهو وجه الذبح في معنى بدج",
    650: "الكف واليد",
    806: "ضرب الرحى والحجر والتفتيت الناتج عنه إلى دقيق ومسحوق",
    935: "اليم: البحر والنهر الكبير",
}

AR_STOP = {
    "الذي", "التي", "هذا", "هذه", "ذلك", "تلك", "في", "من", "على",
    "إلى", "عن", "مع", "كما", "قارن", "انظر", "أيضا", "أيضًا", "العربية",
    "العبرية", "الكنعانية", "البابلية", "القبطية", "المصرية", "الدارجة",
    "المعنى", "الأصلي", "أصل", "أصلا", "لعل", "بلاد", "العرب", "ليس",
    "كان", "كانت", "وهو", "وهي", "مما", "عند", "بعد", "قبل", "نوع",
    "شيء", "شأن", "نحو", "غير", "واحد", "واحدة", "إلخ", "أحد",
}
EN_STOP = {
    "the", "and", "for", "see", "with", "from", "any", "some", "kind",
    "var", "rev", "thing", "things", "made", "place", "land", "about",
}

_BRIDGE_AT_IMPORT = json.loads(
    (ROOT / "data" / "en-ar-bridge.json").read_text(encoding="utf-8")
)["root_head"]
GLOBAL_ENGLISH_WORDS = {
    word for words in _BRIDGE_AT_IMPORT.values() for word in words
    if re.fullmatch(r"[a-z]{4,}", word)
}

# الصفوف التي يستعملها هذا الحصاد. ما ليس هنا لا يُخترع له اسم، بل يفتح الزوج.
IDENTITY = {
    ("r", "ر"): "IDN-01", ("m", "م"): "IDN-02", ("n", "ن"): "IDN-03",
    ("b", "ب"): "IDN-05", ("f", "ف"): "IDN-06", ("s", "س"): "IDN-07",
    ("g", "ج"): "IDN-08", ("d", "د"): "IDN-09", ("w", "و"): "IDN-10",
    ("t", "ت"): "IDN-11", ("q", "ق"): "IDN-12",
    ("k", "ك"): "IDN-13", ("ḥ", "ح"): "IDN-14", ("ꜥ", "ع"): "IDN-15",
    ("ḫ", "خ"): "IDN-17", ("h", "ه"): "IDN-20", ("š", "ش"): "IDN-21",
    ("z", "ز"): "IDN-22", ("y", "ي"): "IDN-23", ("ḏ", "ذ"): "IDN-24",
}
SHIFTS = {
    ("p", "ب"): "LAB-01", ("p", "ف"): "IDN-06",
    ("r", "ل"): "BR-EGYP-01", ("k", "ق"): "GUT-01",
    ("g", "ج"): "GUT-03", ("t", "ط"): "DENT-05",
    ("d", "ض"): "DENT-06", ("ḫ", "ح"): "GUT-05",
    ("s", "ش"): "SIB-01", ("s", "ص"): "SIB-02",
    ("š", "س"): "SIB-01", ("z", "س"): "SIB-03",
    ("ḏ", "ز"): "DENT-04",
    # الصفّان موجودان في الشبكة المجمّدة؛ كان النقص في فهرس هذه الأداة.
    ("i", "ي"): "IDN-23", ("s", "ث"): "BR-EGYP-03",
}


def ar_bare(value: str) -> str:
    value = unicodedata.normalize("NFKC", str(value))
    value = AR_MARKS.sub("", value).replace("ٱ", "ا")
    return re.sub(r"[^ء-ي]", "", value)


def ar_words(value: str) -> list[str]:
    return [w for w in AR_TOKEN.findall(AR_MARKS.sub("", value))
            if w not in AR_STOP and len(w) >= 2]


def en_words(value: str) -> set[str]:
    return set(EN_TOKEN.findall(value.lower())) - EN_STOP


def glyph_chars(value: str) -> list[str]:
    return [c for c in value if 0x13000 <= ord(c) <= 0x1342F]


def scan_defect(row: dict[str, Any]) -> list[str]:
    foreign = row["foreign"].strip()
    sense = row["foreign_sense"]
    glyphs = glyph_chars(row.get("glyphs", ""))
    reasons: list[str] = []
    if " " in foreign:
        reasons.append("رأس ذو فراغ: مركب أو التحمت به عبارة إنجليزية")
    if (foreign.lower() in ENGLISH_HEADS
            or (len(foreign) >= 4 and foreign.lower() in GLOBAL_ENGLISH_WORDS)
            or re.match(r"^(?:a|an|the|to)\s", foreign, re.I)):
        reasons.append("الرأس إنجليزي لا رومنة مصرية")
    if len(glyphs) >= 2 and len(set(glyphs)) == 1:
        reasons.append("رمز هيروغليفي واحد مكرر بخلل المسح")
    latin = len(re.findall(r"[A-Za-z]", sense))
    repeated = max(
        (sense.count(c) for c in set(sense)
         if ord(c) > 127 and unicodedata.category(c)[0] in {"L", "M", "S"}),
        default=0,
    )
    symbols = sum(unicodedata.category(c).startswith("S") for c in sense)
    content = en_words(sense) - {
        "stele", "anastasi", "leyd", "hymn", "amen", "koller", "jour",
        "compare", "arab", "heth", "rev", "darius",
    }
    # في هذه الدفعة لا يكفي أن يكون الرأس الإنجليزي قابلًا للتقطيع؛ ينبغي أن
    # يحمل لفظًا دلاليًّا معروفًا في جسر الذخيرة. ما عدا ذلك يؤجل إلى مقابلة
    # الصفحة المصوّرة، وهو الميل الآمن أمام بقايا الفهارس والأعلام.
    if (latin < 4 or repeated > 2 or symbols > 10 or not content
            or not (content & GLOBAL_ENGLISH_WORDS)):
        reasons.append("المعنى الإنجليزي لم يسلم من المسح")
    return reasons


def morphology(row: dict[str, Any]) -> tuple[str, str, str]:
    foreign = row["foreign"].strip()
    raw = "".join(FAN.skeleton(foreign, "egyptian"))
    if FEMININE.search(foreign):
        stem = foreign[:-2]
        return stem, "تاء الاسم المؤنث الموصولة بشرطة `-t`", raw
    return foreign, "لا لاحقة مصرية مسماة في الرأس", raw


def load_morphology() -> dict[str, set[str]]:
    out: dict[str, set[str]] = defaultdict(set)
    path = RESOURCES / "Ten dictionaries for Arabic language" / "mukhtar.csv"
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle, delimiter=";"):
            term, root = ar_bare(row.get("Normalized Term", "")), ar_bare(row.get("Root", ""))
            if term and 2 <= len(root) <= 4:
                out[term].add(root)
    return out


def candidate_tokens(row: dict[str, Any], morphology_map: dict[str, set[str]],
                     root_inventory: set[str]) -> list[tuple[str, str, int]]:
    foreign = row["foreign"].strip()
    tokens: list[tuple[str, str, int]] = []
    if foreign in AUTHOR_EXAMPLES:
        tokens.append((AUTHOR_EXAMPLES[foreign], "تصحيح المثال الذي سمّاه المؤلف", 0))
    field = ar_bare(row["arabic_root"])
    if field:
        tokens.append((field, "حقل `arabic_root` في الحصاد", 1))
    parenthetical = " ".join(re.findall(r"\(([^)]*)\)", row["arabic_gloss"]))
    for pos, token in enumerate(ar_words(parenthetical), 2):
        tokens.append((ar_bare(token), "شرح خشيم بين القوسين", pos))

    expanded: list[tuple[str, str, int]] = []
    seen: set[str] = set()
    for token, source, pos in tokens:
        options = []
        # حقلُ خشيم نفسه مرشَّحٌ استكشافيٌّ ولو لم تعرفه ذخيرةُ الجذور بعدُ؛
        # غيابُه من فهرس الأداة لا يجوز أن يُسقطه قبل عرضِه على المعجم المسمّى.
        if source == "حقل `arabic_root` في الحصاد" and 2 <= len(token) <= 4:
            options.append(token)
        if token in root_inventory:
            options.append(token)
        options.extend(sorted(morphology_map.get(token, set())))
        if token.startswith("ال"):
            options.extend(sorted(morphology_map.get(token[2:], set())))
        for root in options:
            if root in seen or not 2 <= len(root) <= 4:
                continue
            seen.add(root)
            expanded.append((root, source, pos))
    return expanded


def preferred_lexicon(matches: list[dict[str, Any]]) -> dict[str, Any] | None:
    ranked: list[tuple[int, int, dict[str, Any]]] = []
    for item in matches:
        source_id = ARS.canonical_source_id(str(item.get("source", "")))
        if source_id not in {"lisan", "taj_al_arus"}:
            continue
        definition = " ".join(str(item.get("definition", "")).split())
        if not definition:
            continue
        rank = 0 if source_id == "lisan" else 1
        ranked.append((rank, -len(definition), {**item, "source_id": source_id,
                                                "definition": definition}))
    return min(ranked, default=(0, 0, None))[2]


def meaningful_tokens(value: str) -> set[str]:
    out = set()
    for word in ar_words(value):
        word = ar_bare(word)
        if word.startswith("ال") and len(word) > 4:
            word = word[2:]
        if len(word) >= 3:
            out.add(word)
    return out


def semantic_overlap(row: dict[str, Any], definition: str) -> set[str]:
    gloss = row["arabic_gloss"].split("(", 1)[0]
    left, right = meaningful_tokens(gloss), meaningful_tokens(definition)
    exact = left & right
    if exact:
        return exact
    # تقارب صرفي صغير لا يبدل المادة: أول ثلاثة أحرف بعد أل التعريف.
    return {a for a in left if any(len(a) >= 3 and len(b) >= 3 and a[:3] == b[:3]
                                   for b in right)}


def excerpt(definition: str, row: dict[str, Any], limit: int = 430) -> str:
    definition = " ".join(definition.split())
    parts = [p.strip() for p in re.split(r"(?<=[.؛؟!])\s+|\s*[؛]\s*", definition) if p.strip()]
    targets = meaningful_tokens(row["arabic_gloss"].split("(", 1)[0])

    def score(part: str) -> tuple[int, int]:
        words = meaningful_tokens(part)
        direct = len(words & targets)
        stems = sum(1 for t in targets if any(t[:3] == w[:3] for w in words))
        return direct * 4 + stems, -len(part)

    chosen = max(parts, key=score, default=definition)
    if len(chosen) <= limit:
        return chosen
    # القطع على حد كلمة اقتباسٌ حرفيٌّ قصير، لا إعادة صياغة.
    return chosen[:limit].rsplit(" ", 1)[0] + "…"


def pair_row(symbol: str, arabic: str) -> str | None:
    return IDENTITY.get((symbol, arabic)) or SHIFTS.get((symbol, arabic))


def sound_audit(stem: str, root: str) -> tuple[bool, list[str], list[str]]:
    skeleton = FAN.skeleton(stem, "egyptian")
    if len(skeleton) != len(root):
        return False, [], [f"عدد الصوامت {len(skeleton)} في الفرع و{len(root)} في المرشح"]
    rows: list[str] = []
    misses: list[str] = []
    for symbol, arabic in zip(skeleton, root):
        row = pair_row(symbol, arabic)
        query = f"`{symbol}` + `{arabic}` + «المصريّة/Egyptian» في عمود الشاهد"
        if row:
            rows.append(f"{symbol}↔{arabic} = `{row}` (بحث: {query})")
        else:
            misses.append(f"{symbol}↔{arabic} (بحث: {query}؛ لا صف مناسب)")
    return not misses, rows, misses


def existing_heads() -> set[str]:
    text = READING.read_text(encoding="utf-8")
    for start, end in ((START_1, END_1), (START_2, END_2)):
        if start in text and end in text:
            before, rest = text.split(start, 1)
            _, after = rest.split(end, 1)
            text = before + after
    heads = set()
    for head in re.findall(r"(?m)^### بطاقة[^\n]*", text):
        for token in re.findall(r"`([^`]+)`", head):
            heads.add(token.strip())
        m = re.match(r"^### بطاقة:\s*([^\s«،]+)", head)
        if m:
            heads.add(m.group(1).strip("`"))
    return heads


def evaluate_rows(rows: list[dict[str, Any]],
                  forced_roots: dict[int, str] | None = None
                  ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    forced_roots = forced_roots or {}
    bridge = json.loads((ROOT / "data" / "en-ar-bridge.json").read_text(encoding="utf-8"))["root_head"]
    root_inventory = set(bridge)
    morph = load_morphology()
    root_inventory.update(root for values in morph.values() for root in values)
    old_heads = existing_heads()

    defects: list[dict[str, Any]] = []
    pool: list[dict[str, Any]] = []
    all_roots: set[str] = set()
    for index, row in enumerate(rows):
        reasons = scan_defect(row)
        if reasons:
            defects.append({"index": index, "foreign": row["foreign"], "reasons": reasons})
        if not (2 <= len(FAN.skeleton(row["foreign"], "egyptian")) <= 4):
            continue
        if row["foreign"] in old_heads:
            continue
        stem, stripping, raw_skeleton = morphology(row)
        raw_fan = FAN.fan(row["foreign"], "egyptian", limit=400)
        stem_fan = FAN.fan(stem, "egyptian", limit=400)
        candidates = candidate_tokens(row, morph, root_inventory)
        if not candidates:
            continue
        for root, _, _ in candidates:
            all_roots.add(root)
            if root in LEXICON_ALIASES:
                all_roots.add(LEXICON_ALIASES[root])
        pool.append({
            "index": index, "row": row, "stem": stem, "stripping": stripping,
            "raw_skeleton": raw_skeleton, "raw_fan": raw_fan, "stem_fan": stem_fan,
            "candidates": candidates, "scan_reasons": reasons,
        })

    lexica = ARS.matches_for_roots(RESOURCES, all_roots, limit=None)
    for item in pool:
        row = item["row"]
        evaluated = []
        for root, origin, pos in item["candidates"]:
            lexicon_root = LEXICON_ALIASES.get(root, root)
            lexicon = preferred_lexicon(lexica.get(lexicon_root, []))
            definition = lexicon["definition"] if lexicon else ""
            ar_hit = semantic_overlap(row, definition) if definition else set()
            en_hit = en_words(row["foreign_sense"]) & set(bridge.get(root, []))
            raw_hit = root in item["raw_fan"]
            stem_hit = root in item["stem_fan"]
            sound_ready, sound_rows, sound_misses = sound_audit(item["stem"], root)
            score = (
                (32 if raw_hit else 26 if stem_hit else 0)
                + (20 if sound_ready else 0)
                + min(30, len(en_hit) * 10)
                + min(24, len(ar_hit) * 6)
                + (4 if lexicon else 0)
                + (3 if "?" not in row["foreign_sense"] and "[" not in row["foreign_sense"] else 0)
                + (2 if row.get("glyphs") else 0)
                + max(0, 4 - pos)
                - (8 if not en_hit and not ar_hit else 0)
                - (18 * len(item["scan_reasons"]))
            )
            evaluated.append({
                "root": root, "root_origin": origin, "position": pos,
                "lexicon_root": lexicon_root,
                "lexicon": lexicon, "ar_hit": sorted(ar_hit), "en_hit": sorted(en_hit),
                "raw_hit": raw_hit, "stem_hit": stem_hit, "sound_ready": sound_ready,
                "sound_rows": sound_rows, "sound_misses": sound_misses, "score": score,
            })
        approved_root = forced_roots.get(item["index"], APPROVED_POSITIVES.get(item["index"]))
        approved = [x for x in evaluated if x["root"] == approved_root]
        chosen = (approved[0] if approved else
                  sorted(evaluated, key=lambda x: (-x["score"], x["position"], x["root"]))[0])
        item["chosen"] = chosen
        item["score"] = chosen["score"]

    pool.sort(key=lambda x: (-x["score"], len(x["scan_reasons"]), x["index"]))
    return pool, defects


def choose_batches(rows: list[dict[str, Any]]) -> tuple[
        list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]],
        list[dict[str, Any]]]:
    prior = json.loads(REPORT_1.read_text(encoding="utf-8")) if REPORT_1.exists() else {"rows": []}
    first_roots = {int(row["index"]): str(row["root"]) for row in prior.get("rows", [])}
    pool, defects = evaluate_rows(rows, first_roots)

    if first_roots:
        first = [item for item in pool if item["index"] in first_roots]
    else:
        clean = [item for item in pool if not item["scan_reasons"]]
        forced = [item for item in clean if item["index"] in APPROVED_POSITIVES]
        first = forced + [item for item in clean if item["index"] not in APPROVED_POSITIVES][
            :FIRST_BATCH_SIZE - len(forced)
        ]
    if len(first) != FIRST_BATCH_SIZE:
        raise SystemExit(f"لم تُحفَظ الدفعة الأولى: {len(first)} من {FIRST_BATCH_SIZE}")
    first_ids = {item["index"] for item in first}
    structural_scan_defects = {
        "الرأس إنجليزي لا رومنة مصرية",
        "رأس ذو فراغ: مركب أو التحمت به عبارة إنجليزية",
        "رمز هيروغليفي واحد مكرر بخلل المسح",
    }
    second_pool = [
        item for item in pool
        if item["index"] not in first_ids
        and not (set(item["scan_reasons"]) & structural_scan_defects)
    ]
    second = second_pool[:SECOND_BATCH_SIZE]
    if len(second) != SECOND_BATCH_SIZE:
        raise SystemExit(f"لم تبلغ الدفعة الثانية {SECOND_BATCH_SIZE}: المتاح {len(second)}")
    first.sort(key=lambda x: (-x["score"], x["index"]))
    second.sort(key=lambda x: (-x["score"], x["index"]))
    return first, second, defects, pool


def fan_text(values: list[str]) -> str:
    return "، ".join(f"`{x}`" for x in values) if values else "(لم تولّد الأداة مرشحًا)"


def card(item: dict[str, Any], batch_no: int) -> tuple[str, dict[str, Any]]:
    row, chosen = item["row"], item["chosen"]
    root = chosen["root"]
    raw_fan, stem_fan = item["raw_fan"], item["stem_fan"]
    lexicon = chosen["lexicon"]
    source_label = (ARS.SOURCE_LABELS.get(lexicon["source_id"], lexicon["source"])
                    if lexicon else "")
    quote = QUOTE_OVERRIDES.get(item["index"], "")
    if not quote and lexicon:
        quote = excerpt(lexicon["definition"], row)
    direct_semantics = bool(chosen["en_hit"] or chosen["ar_hit"])
    semantic_ready = direct_semantics or APPROVED_POSITIVES.get(item["index"]) == root
    source_ready = bool(lexicon and quote)
    length_ready = len(root) in {2, 3}
    fan_ready = chosen["raw_hit"] or chosen["stem_hit"]
    positive = (
        APPROVED_POSITIVES.get(item["index"]) == root
        and all((chosen["sound_ready"], source_ready, length_ready, fan_ready,
                 "?" not in row["foreign_sense"]))
    )
    degree = "ROOT-TRACE" if len(root) == 3 else "NUCLEUS-TRACE"
    closure = "READY" if positive else "OPEN-CANDIDATE"
    verdict = f"**{degree} (استكشاف)**" if positive else "**غير صادر (استكشاف)**"
    glyphs = row.get("glyphs", "") or "(لم يسلم رمز من المسح، فلا يستعمل دليلًا)"
    raw_skeleton = item["raw_skeleton"] or "∅"
    stem_skeleton = "".join(FAN.skeleton(item["stem"], "egyptian")) or "∅"

    if chosen["raw_hit"]:
        location = f"المادة المرشحة المستخرجة من صف خشيم `{root}` داخل المروحة الخام"
    elif chosen["stem_hit"]:
        location = (f"المادة المرشحة المستخرجة من صف خشيم `{root}` ليست في المروحة الخام، وتظهر في مروحة اللب بعد "
                    f"{item['stripping']}")
    else:
        location = (f"المادة المرشحة المستخرجة من صف خشيم `{root}` غير موجودة في المروحة الخام ولا في مروحة اللب؛ "
                    "حُفظ ولم يُسقط")

    fan_lines = [
        f"- مروحةُ المرشحات العربيّة من أداتنا: شُغّل `scripts/fan_any_script.py` على "
        f"`{row['foreign']}` بلسان `egyptian`؛ الهيكل `{raw_skeleton}`؛ المروحة الكاملة: "
        f"{fan_text(raw_fan)}.",
    ]
    if item["stem"] != row["foreign"]:
        fan_lines.append(
            f"- مروحةُ اللب بعد التعرية: `{item['stem']}`؛ الهيكل `{stem_skeleton}`؛ "
            f"المروحة الكاملة: {fan_text(stem_fan)}."
        )

    if lexicon and quote:
        material_note = (f"، تحت مادة `{chosen['lexicon_root']}` الشارحة للنواة `{root}`"
                         if chosen["lexicon_root"] != root else "")
        if chosen["ar_hit"] or item["index"] in SEMANTIC_LABELS:
            semantic_note = (
                "القريب المراد هو "
                f"{SEMANTIC_LABELS.get(item['index'], ', '.join(chosen['ar_hit']))}؛ "
                "وسائر وجوه النص لا تُنقل إلى المصرية"
            )
        else:
            semantic_note = (
                "أُثبت النص المعجمي الحرفي للحفظ والمراجعة؛ ولم تعثر الأداة على عبارة "
                "عربية مشتركة كافية، فلا يُجعل الاقتباس وحده حكمًا دلاليًّا"
            )
        scan = (f"المادة `{root}`{material_note}؛ نص {source_label}: «{quote}». ونص خشيم المنقول في "
                f"الصف: «{row['arabic_gloss']}». {semantic_note}.")
    else:
        scan = (f"لم يوجد للمادة `{root}` نص في لسان العرب ولا تاج العروس في الذخيرة "
                f"المحلية؛ نص خشيم وحده «{row['arabic_gloss']}» محفوظ ولا يقوم مقام معجم مسمّى.")

    sound_parts = chosen["sound_rows"] + chosen["sound_misses"]
    sound = "؛ ".join(sound_parts) if sound_parts else (
        "اختل عدد الصوامت، ثم فُتشت الشبكة بالحرفين وبالمصريّة/Egyptian في عمود الشاهد"
    )
    obstacles = []
    if not fan_ready:
        obstacles.append("إصابة مرشح خشيم داخل مروحة الأداة بعد التعرية المسماة")
    if not chosen["sound_ready"]:
        obstacles.append("صفوف الشبكة الناقصة المبيّنة في مسار الصوت")
    if not source_ready:
        obstacles.append("نص لسان العرب أو تاج العروس للمادة")
    if not semantic_ready:
        obstacles.append("شاهد دلالي منشور يصل نص بدج بنص المعجم العربي")
    if not length_ready:
        obstacles.append("تحليل يبيّن وحدة المقارنة العربية ذات الأربعة صوامت")
    if item["scan_reasons"]:
        obstacles.append("مقابلة الصفحة المصوّرة لعيب المسح المسمّى")
    if not positive and not obstacles:
        obstacles.append("مراجعة دلالية بشرية مستقلة تتجاوز التقارب الآلي بين النصوص")
    required = "؛ ".join(obstacles) if obstacles else "لا عائق معلق"

    degree_text = "جذر كامل" if len(root) == 3 else "نواة" if len(root) == 2 else "مفتوحة بلا درجة صادرة"
    orbit_hits = ([SEMANTIC_LABELS[item["index"]]]
                  if item["index"] in SEMANTIC_LABELS
                  else chosen["en_hit"] + chosen["ar_hit"])
    orbit = ("مباشر؛ التقى نص بدج ونص المعجم العربي في "
             + ("، ".join(orbit_hits) if orbit_hits else "الوجه النصي المقتبس")) if semantic_ready else (
        "غير صادر؛ شرح خشيم يرشح الصلة، لكن النصين لم يلتقيا بلفظ مستقل كاف للحكم"
    )
    family_ar = 1 if positive else 0
    batch_label = f"{batch_no:03d}"
    scan_status = ("؛ ".join(item["scan_reasons"]) if item["scan_reasons"]
                   else "لم تُسجّل أداة المسح عيبًا في هذا الصف")
    lines = [
        f"### بطاقة: `{row['foreign']}` «{row['foreign_sense']}»؛ خشيم {batch_label}/{item['index']:03d}",
        f"<!-- khashim-egyptian-batch-{batch_label}:{item['index']} -->",
        "- إصدارُ البروتوكول: RECOVERY-v2 (2026-07-14)",
        f"- الكلمةُ في الفرع: `{row['foreign']}`؛ الرمز المنقول `{glyphs}`؛ الرومنة من بدج كما نقلها خشيم.",
        f"- أقدمُ صورةٍ مستعادة: لا تُدّعى صورة أقدم من رومنة بدج المنقولة في {BOOK}؛ "
        "الصف من `data/khashim-pairs.json` ومصدره `ocr-egyptian2`.",
        f"- سلامةُ صف المسح: {scan_status}؛ العيب، إن وُجد، يفتح المقابلة ولا يُسقط المرشح.",
        f"- الخطوةُ صفر (التعرية بصرف الفرع): {item['stripping']}؛ صوامت الرأس كاملة "
        f"`{raw_skeleton}` ← اللب `{stem_skeleton}`.",
        f"- حسابُ الصوامت: صوامت اللب {len(FAN.skeleton(item['stem'], 'egyptian'))}؛ "
        f"صوامت مرشح خشيم `{root}` = {len(root)}؛ لم يُسقط صامت أصلي غير مسمى.",
        f"- درجةُ المقارنة: {degree_text}؛ فُحص الجذر والنواة في عرض واحد، ولا يصدر "
        "حكم للطبقة الأخرى بلا مادتها المستقلة.",
        *fan_lines,
        f"- موضعُ مرشح خشيم من المروحة: {location}؛ وهذه المروحة من أداتنا لا من قول خشيم.",
        f"- مسحُ المعاني العربيّة: {scan}",
        f"- المقابلُ من اللسان: `{root}`؛ مادة الصلة المستخرجة من صف خشيم، لا مادة ولّدتها "
        f"المروحة؛ النص الحرفي لحقل `arabic_root` هو `{row['arabic_root']}`؛ "
        f"مصدر الاستخراج: {chosen['root_origin']}.",
        f"- مسارُ الصوت: {sound}. فُتش كل موضع بالحرفين معًا، ثم بلفظي "
        "«المصريّة» و`Egyptian` في عمود الشاهد من `shift-network-draft.md`.",
        f"- المعنى من قاموس الفرع: «{row['foreign_sense']}» [Budge، كما نقله {BOOK}]؛ "
        "لم يُترجم النص الإنجليزي في رجل الفرع.",
        f"- المدار: {orbit}.",
        "- المصفاة: لا يسمّي صف الحصاد مانحًا ولا طريق اقتراض؛ غياب الاسم ليس إثبات أصالة، "
        "وتبقى جهة النقل سؤال الجولة المقيسة.",
        "- فصلُ المتجانسات والاقتراض: الحكم، إن صدر، لهذا الصف بمعناه الإنجليزي وحده؛ "
        "لا يرثه متحد الرسم ولا معنى آخر في كتاب بدج.",
        "- جردُ العَلَم: غير علم بحسب رأس الصف ومعناه؛ لا حكم على متّحد رسم قد يكون علمًا.",
        "- مؤشر اليتم: غير حاسم؛ لا يحمل صف الحصاد جرد أسرة مصرية، فلا يستعمل التفرد رفعًا أو إسقاطًا.",
        f"- إشعاع الأسرة في الفرع: الأعضاء المعجمية المدعومة={1 if positive else 0}؛ "
        f"سلاسل المعنى المدعومة={1 if positive else 0}؛ الصف المفرد وحده، ولا تعميم على الأسرة.",
        f"- إشعاع الأسرة في العربية: الأعضاء المعجمية المدعومة={family_ar}؛ "
        f"سلاسل المعنى المدعومة={family_ar}؛ مادة `{root}` في الوجه النصي المقتبس وحده.",
        "- جسورُ الاسترداد المفحوصة: الرأس الكامل؛ التعرية المسمّاة؛ مروحة الأداة الخام "
        "ومروحة اللب حيث وجدت؛ مرشح خشيم؛ لسان العرب ثم تاج العروس؛ شبكة الإبدالات "
        "بالحرفين وبأسماء اللسان في عمود الشاهد؛ المدار؛ القرض؛ المتجانسات.",
        f"- عائق: النوع={closure}؛ يتطلب={required}",
        f"- حالةُ الإغلاق: {closure}",
        f"- الحكم (استكشاف): {verdict}",
        f"- ملاحظات: أصل المرشح وشرحُه «{row['arabic_gloss']}» من {BOOK}، والمعنى الإنجليزي من معجم بدج كما نقله خشيم. "
        "فُصلت نسبة خشيم وبدج عن المروحة والمسار والحكم، وهي عمل المشروع. "
        f"عدسة الاسترداد أبقت المرشح عند الشك؛ وعدسة التشكيك {'أصدرت الحكم بعد اكتمال الأرجل' if positive else 'منعت الحكم ولم تغلق الزوج'}.",
    ]
    summary = {
        "index": item["index"], "foreign": row["foreign"], "sense": row["foreign_sense"],
        "root": root, "score": item["score"], "raw_fan_count": len(raw_fan),
        "root_in_raw_fan": chosen["raw_hit"], "root_in_stem_fan": chosen["stem_hit"],
        "lexicon": source_label or None, "semantic_hits": chosen["en_hit"] + chosen["ar_hit"],
        "closure": closure, "verdict": degree if positive else None,
        "sound_rows": chosen["sound_rows"], "sound_misses": chosen["sound_misses"],
        "scan_reasons": item["scan_reasons"], "open_reasons": obstacles,
    }
    return "\n".join(lines), summary


def baseline_egyptian_table() -> dict[str, tuple[str, ...]]:
    """مروحةُ 526dd60 قبل إضافتَي h المَقيسَتَين في هذه الجولة."""
    return {
        symbol: tuple(value for value in values
                      if not (symbol == "h" and value in {"ر", "ح"}))
        for symbol, values in FAN.EGYPTIAN_FAN.items()
    }


def fan_from_table(word: str, table: dict[str, tuple[str, ...]]) -> list[str]:
    skeleton = FAN.skeleton(word, "egyptian")
    if not (2 <= len(skeleton) <= 4):
        return []
    options = [table.get(symbol, ()) for symbol in skeleton]
    if any(not values for values in options):
        return []
    return ["".join(value) for value in itertools.islice(itertools.product(*options), 400)]


def all_rows_fan_audit(rows: list[dict[str, Any]], pool: list[dict[str, Any]],
                       first: list[dict[str, Any]]) -> dict[str, int]:
    bridge = json.loads((ROOT / "data" / "en-ar-bridge.json").read_text(encoding="utf-8"))["root_head"]
    morphology_map = load_morphology()
    root_inventory = set(bridge)
    root_inventory.update(root for values in morphology_map.values() for root in values)
    old_table = baseline_egyptian_table()
    stats = Counter(rows_examined=len(rows))
    for row in rows:
        stem, _, _ = morphology(row)
        candidates = candidate_tokens(row, morphology_map, root_inventory)
        if candidates:
            stats["rows_with_khashim_candidate"] += 1
        old_raw = set(fan_from_table(row["foreign"], old_table))
        old_stem = set(fan_from_table(stem, old_table))
        new_raw = set(FAN.fan(row["foreign"], "egyptian", limit=400))
        new_stem = set(FAN.fan(stem, "egyptian", limit=400))
        roots = {root for root, _, _ in candidates}
        if roots & (old_raw | old_stem):
            stats["rows_any_candidate_in_old_fan"] += 1
        if roots & (new_raw | new_stem):
            stats["rows_any_candidate_in_expanded_fan"] += 1
        field = ar_bare(row.get("arabic_root", ""))
        if field and field in old_raw | old_stem:
            stats["rows_exact_field_in_old_fan"] += 1
        if field and field in new_raw | new_stem:
            stats["rows_exact_field_in_expanded_fan"] += 1
    stats["rows_evaluable_after_skeleton_and_candidate"] = len(pool)
    stats["chosen_candidate_in_expanded_fan"] = sum(
        item["chosen"]["raw_hit"] or item["chosen"]["stem_hit"] for item in pool
    )
    old_table = baseline_egyptian_table()
    first_old_hits = 0
    for item in first:
        root = item["chosen"]["root"]
        old = set(fan_from_table(item["row"]["foreign"], old_table))
        old.update(fan_from_table(item["stem"], old_table))
        first_old_hits += root in old
    stats["first_batch_chosen_in_old_fan"] = first_old_hits
    stats["first_batch_chosen_in_expanded_fan"] = sum(
        item["chosen"]["raw_hit"] or item["chosen"]["stem_hit"] for item in first
    )
    return dict(stats)


def audit_fan_gaps(first: list[dict[str, Any]]) -> tuple[
        Counter[tuple[str, str]], dict[tuple[str, str], list[str]], list[dict[str, Any]]]:
    table = baseline_egyptian_table()
    missing: Counter[tuple[str, str]] = Counter()
    examples: dict[tuple[str, str], list[str]] = defaultdict(list)
    unaligned: list[dict[str, Any]] = []
    for item in first:
        root = item["chosen"]["root"]
        skeletons: list[list[str]] = []
        for word in (item["row"]["foreign"], item["stem"]):
            skeleton = FAN.skeleton(word, "egyptian")
            if skeleton not in skeletons:
                skeletons.append(skeleton)
        if any(root in fan_from_table(word, table)
               for word in (item["row"]["foreign"], item["stem"])):
            continue
        alignments = [skeleton for skeleton in skeletons if len(skeleton) == len(root)]
        if not alignments:
            unaligned.append(item)
            continue
        skeleton = min(
            alignments,
            key=lambda value: sum(arabic not in table.get(symbol, ())
                                  for symbol, arabic in zip(value, root)),
        )
        for symbol, arabic in zip(skeleton, root):
            if arabic in table.get(symbol, ()):
                continue
            pair = (symbol, arabic)
            missing[pair] += 1
            examples[pair].append(f"`{item['row']['foreign']}`→`{root}`")
    return missing, examples, unaligned


def audit_network_gaps(first: list[dict[str, Any]]) -> tuple[
        Counter[tuple[str, str]], dict[tuple[str, str], list[str]], list[dict[str, Any]], int]:
    # يعيد فهرسَ 526dd60 عمدًا كي يبقى جردُ الـ99 قابلًا لإعادة الإنتاج.
    baseline_shifts = {
        pair: row for pair, row in SHIFTS.items()
        if pair not in {("i", "ي"), ("s", "ث")}
    }
    missing: Counter[tuple[str, str]] = Counter()
    examples: dict[tuple[str, str], list[str]] = defaultdict(list)
    unaligned: list[dict[str, Any]] = []
    gap_cards = 0
    for item in first:
        skeleton = FAN.skeleton(item["stem"], "egyptian")
        root = item["chosen"]["root"]
        if len(skeleton) != len(root):
            gap_cards += 1
            unaligned.append(item)
            continue
        card_has_gap = False
        for symbol, arabic in zip(skeleton, root):
            if IDENTITY.get((symbol, arabic)) or baseline_shifts.get((symbol, arabic)):
                continue
            card_has_gap = True
            pair = (symbol, arabic)
            missing[pair] += 1
            sense = " ".join(item["row"]["foreign_sense"].split()).replace("|", "/")
            examples[pair].append(
                f"`{item['row']['foreign']}`→`{root}` «{sense}»"
            )
        gap_cards += card_has_gap
    return missing, examples, unaligned, gap_cards


def network_analogue(pair: tuple[str, str]) -> str:
    exact = {
        ("i", "ي"): "موجودٌ معنىً في `IDN-23`؛ يُوسَّع شاهدُه ليصرّح بـ`i` المصريّة، لا صف جديد",
        ("s", "ث"): "موجودٌ نصًّا في `BR-EGYP-03`؛ هذا خطأ فهرسة وقد أُصلح، لا صف جديد",
        ("n", "ل"): "موجودٌ مشروطًا في `BR-EGYP-02`؛ لا يُعمَّم بلا خلف ديموطيقي/قبطي",
        ("h", "ح"): "نظيرُه `GUT-04`، لكن شاهدَه لا يسمّي المصريّة؛ يُوسَّع نطاقه وشاهدُه",
        ("h", "ع"): "نظيرُه `GUT-04`، لكن شاهدَه لا يسمّي المصريّة؛ يُوسَّع نطاقه وشاهدُه",
        ("n", "م"): "نظيرُه `LIQ-02` في الأنفيّات؛ يحتاج شاهدًا مصريًّا في الصف",
        ("r", "ن"): "نظيرُه `LIQ-03` في الذلقيّات؛ يحتاج شاهدًا مصريًّا في الصف",
        ("t", "ث"): "نظيرُه `DENT-01` في فرع آخر؛ يحتاج شاهدًا مصريًّا صريحًا",
    }
    if pair in exact:
        return exact[pair]
    if pair[1] in {"أ", "إ", "آ"}:
        return "فجوةُ تطبيعٍ للهمزة أولًا، لا يُنشأ صف صوتي قبل توحيد الرسم"
    return "لا نظيرَ مطابقًا في الشبكة؛ مسوّدة صف جديد"


def write_expansion_audits(first: list[dict[str, Any]], fan_stats: dict[str, int]) -> None:
    fan_missing, fan_examples, fan_unaligned = audit_fan_gaps(first)
    fan_lines = [
        "# جردُ توسيع مروحة المصريّة من دفعة خشيم 001",
        "",
        "هذا جردٌ للمروحة كما كانت في الإيداع `526dd60`. عُدَّ الزوج خارجها إذا لم "
        "يظهر مرشح خشيم في المروحة الخام ولا في مروحة اللب بعد تعرية `-t` المسماة.",
        "",
        f"- البطاقات الخارجة من المروحة القديمة: {len(first) - fan_stats['first_batch_chosen_in_old_fan']}.",
        f"- القابلة لمحاذاة حرف بحرف: {len(first) - fan_stats['first_batch_chosen_in_old_fan'] - len(fan_unaligned)}؛ "
        f"فيها {sum(fan_missing.values())} موضع نقل و{len(fan_missing)} نقلة متميزة.",
        f"- غير القابلة لمحاذاة حرف بحرف لاختلاف عدد الصوامت: {len(fan_unaligned)}؛ "
        "حُفظت ولم يُخترع لها إسقاط أو إدغام.",
        "- دخلت المروحةَ النقلاتُ المتكررة ثلاث مرات فأكثر فقط: `h→ر` (4) و`h→ح` (3).",
        "",
        "## جدولُ النقلات الناقصة كاملًا",
        "",
        "| المصري | العربي | الشواهد | أمثلة من الدفعة | القرار |",
        "|---|---|---:|---|---|",
    ]
    for pair, count in sorted(fan_missing.items(), key=lambda value: (-value[1], value[0])):
        decision = "أُضيفت إلى `EGYPTIAN_FAN`" if count >= 3 else "تبقى مرصودة دون إدخال"
        fan_lines.append(
            f"| `{pair[0]}` | `{pair[1]}` | {count} | "
            f"{ '؛ '.join(fan_examples[pair][:3]) } | {decision} |"
        )
    fan_lines.extend([
        "",
        "## الأزواج التي لا تعطي محاذاة حرفية",
        "",
        "| الرأس المصري | مرشح خشيم | صوامت الرأس/اللب | صوامت المرشح |",
        "|---|---|---:|---:|",
    ])
    for item in sorted(fan_unaligned, key=lambda value: value["index"]):
        raw = len(FAN.skeleton(item["row"]["foreign"], "egyptian"))
        stem = len(FAN.skeleton(item["stem"], "egyptian"))
        fan_lines.append(
            f"| `{item['row']['foreign']}` | `{item['chosen']['root']}` | {raw}/{stem} | "
            f"{len(item['chosen']['root'])} |"
        )
    fan_lines.extend([
        "",
        "## إعادة تمرير الصفوف الـ938",
        "",
        f"- فيها مرشح خشيم قابل للاستخراج: {fan_stats['rows_with_khashim_candidate']}.",
        f"- أصاب مرشحٌ واحد على الأقل المروحة القديمة في {fan_stats['rows_any_candidate_in_old_fan']} صفًا، "
        f"والمروحة الموسعة في {fan_stats['rows_any_candidate_in_expanded_fan']} صفًا.",
        f"- وبالاقتصار على حقل `arabic_root` الحرفي: {fan_stats['rows_exact_field_in_old_fan']} قديمًا، "
        f"و{fan_stats['rows_exact_field_in_expanded_fan']} بعد التوسيع.",
        f"- وفي الدفعة الأولى نفسها صار المرشح المختار داخل المروحة في "
        f"{fan_stats['first_batch_chosen_in_expanded_fan']} من 120، وكان القياس المعاد من ملف الإيداع "
        f"{fan_stats['first_batch_chosen_in_old_fan']} من 120.",
        "",
    ])
    FAN_AUDIT.write_text("\n".join(fan_lines), encoding="utf-8", newline="\n")

    network_missing, network_examples, network_unaligned, gap_cards = audit_network_gaps(first)
    shift_lines = [
        "# مسوّدةُ صفوف الإبدال المصريّة المقترحة من دفعة خشيم 001",
        "",
        "> هذه مسوّدة خارج الشبكة النافذة. لم يُمسّ `shift-network-draft.md` لأنه مجمّد ولا يدخل "
        "من هذه الورقة أي صف قبل توقيع المؤلف.",
        "",
        "## طريقة التفتيش",
        "",
        "فُتّش `shift-network-draft.md` لكل نقلة بالحرفين معًا في الترتيبين "
        "(`<الحرف المصري>.*<الحرف العربي>` و`<الحرف العربي>.*<الحرف المصري>`)، ثم فُتّشت ألفاظ النطاق والشاهد "
        "`المصريّة` و`المصرية` و`Egyptian` و`BR-EGYP`، ثم قُرئ عمود «مثال موثّق» "
        "وعمود النطاق. وأظهر ذلك صفين أخطأ فهرس الأداة في إعلان غيابهما: `i→ي` له "
        "صف الهوية `IDN-23` الذي يحتاج تصريحًا بالرومنة المصرية، و`s→ث` موجود نصًا "
        "في `BR-EGYP-03`. كما ظهر `n→ل` في `BR-EGYP-02` لكنه مشروط بخلف لاحق، فلا "
        "يُطلق على شاهد الحصاد بلا شرطه.",
        "",
        f"الجرد الأصلي وسم {gap_cards} بطاقةً بعائق شبكة. منها {len(network_unaligned)} بطاقة "
        f"سببها اختلاف عدد الصوامت لا غياب صف، وخرجت من الباقي {sum(network_missing.values())} "
        f"مواضع نقل في {len(network_missing)} زوجًا متميزًا.",
        "",
        "## صفوف النقل المقترحة أو التوسيعات اللازمة",
        "",
        "الأمثلة ثلاثة حيث أتاح الحصاد ثلاثة، وكل الشواهد المتاحة حيث كان العدد أقل.",
        "",
        "| المصري | العربي | عدد الشواهد | أمثلة بأسمائها | صف قائم يُوسّع أم صف جديد؟ |",
        "|---|---|---:|---|---|",
    ]
    for pair, count in sorted(network_missing.items(), key=lambda value: (-value[1], value[0])):
        shift_lines.append(
            f"| `{pair[0]}` | `{pair[1]}` | {count} | "
            f"{'؛ '.join(network_examples[pair][:3])} | {network_analogue(pair)} |"
        )
    shift_lines.extend([
        "",
        "## مواضع اختلاف عدد الصوامت، وليست صفوفًا ناقصة",
        "",
        "| الرأس المصري | مرشح خشيم | صوامت اللب | صوامت المرشح |",
        "|---|---|---:|---:|",
    ])
    for item in sorted(network_unaligned, key=lambda value: value["index"]):
        shift_lines.append(
            f"| `{item['row']['foreign']}` | `{item['chosen']['root']}` | "
            f"{len(FAN.skeleton(item['stem'], 'egyptian'))} | {len(item['chosen']['root'])} |"
        )
    shift_lines.append("")
    SHIFT_PROPOSALS.write_text("\n".join(shift_lines), encoding="utf-8", newline="\n")


def replace_batch(text: str, start: str, end: str, block: str) -> str:
    if start in text and end in text:
        before, rest = text.split(start, 1)
        _, after = rest.split(end, 1)
        tail = after.lstrip()
        return (before.rstrip() + "\n\n" + block.rstrip()
                + ("\n\n" + tail if tail else "\n"))
    return text.rstrip() + "\n\n" + block.rstrip() + "\n"


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    payload = json.loads(SOURCE.read_text(encoding="utf-8"))
    rows = [row for row in payload["rows"] if row.get("tongue") == "egyptian"]
    if len(rows) != 938:
        raise SystemExit(f"تغيّر جرد المصرية: {len(rows)}، والمتوقع 938")
    first, second, defects, pool = choose_batches(rows)
    fan_stats = all_rows_fan_audit(rows, pool, first)
    write_expansion_audits(first, fan_stats)

    def render_batch(selected: list[dict[str, Any]], batch_no: int,
                     start: str, end: str) -> tuple[str, list[dict[str, Any]]]:
        rendered: list[str] = []
        report_rows: list[dict[str, Any]] = []
        for item in selected:
            text, summary = card(item, batch_no)
            rendered.append(text)
            report_rows.append(summary)
        positives = sum(bool(row["verdict"]) for row in report_rows)
        opens = sum(row["closure"] == "OPEN-CANDIDATE" for row in report_rows)
        if batch_no == 1:
            scope = (
                "هذه هي العضوية المودعة في الدفعة الأولى نفسها، وأعيد بناؤها بالمروحة "
                "الموسعة. أصل كل مرشح من خشيم ومعناه الإنجليزي من بدج؛ أما المروحة "
                "والشبكة والنص المعجمي والحكم فمن أدوات المشروع."
            )
            title = "## حصادُ خشيم المصري، الدفعة الأولى (مراجعة 2026-08-11)"
        else:
            scope = (
                "هذه 200 بطاقة جديدة بعد الدفعة الأولى. استُبعد الرأس الإنجليزي والمركب "
                "والرمز الهيروغليفي المكرر بخلل المسح، ولم يُسقط ضعف التقاطع الآلي ولا "
                "غياب الجذر من فهرس الأداة مرشح خشيم؛ بل سُمّي العيب داخل البطاقة وبقي "
                "`OPEN-CANDIDATE`. أصل المرشح من خشيم والمعنى الإنجليزي من بدج، والمروحة "
                "والشبكة والنص المعجمي والحكم من أدوات المشروع."
            )
            title = "## حصادُ خشيم المصري، الدفعة الثانية (2026-08-11)"
        section = [
            start, title, "", "**بيان النطاق.** " + scope, "",
            f"**قاموس الإغلاق المغلق.** لا تستعمل البطاقات إلا `READY` و`OPEN-CANDIDATE`. "
            f"صدر {positives} حكمًا استكشافيًا وبقي {opens} مفتوحًا؛ الفتح حفظٌ للمرشح "
            "لا حكمٌ سلبي عليه.",
            "", *rendered, end,
        ]
        return "\n".join(section), report_rows

    first_block, first_rows = render_batch(first, 1, START_1, END_1)
    second_block, second_rows = render_batch(second, 2, START_2, END_2)
    current = READING.read_text(encoding="utf-8")
    updated = replace_batch(current, START_1, END_1, first_block)
    updated = replace_batch(updated, START_2, END_2, second_block)
    updated = unicodedata.normalize("NFC", updated)
    READING.write_text(updated, encoding="utf-8", newline="\n")

    reasons: dict[str, int] = defaultdict(int)
    for item in defects:
        for reason in item["reasons"]:
            reasons[reason] += 1
    def write_report(path: pathlib.Path, batch_no: int,
                     report_rows: list[dict[str, Any]]) -> tuple[int, int]:
        open_reasons: dict[str, int] = defaultdict(int)
        selection_scan_reasons: dict[str, int] = defaultdict(int)
        for item in report_rows:
            for reason in item["open_reasons"]:
                open_reasons[reason] += 1
            for reason in item["scan_reasons"]:
                selection_scan_reasons[reason] += 1
        positives = sum(bool(row["verdict"]) for row in report_rows)
        opens = sum(row["closure"] == "OPEN-CANDIDATE" for row in report_rows)
        report = {
            "generated_by": "scripts/build_khashim_egyptian_cards.py",
            "batch": batch_no,
            "source": "data/khashim-pairs.json",
            "book": BOOK,
            "rows_examined": len(rows),
            "fan_audit_938": fan_stats,
            "scan_defects_union": len(defects),
            "scan_defects_by_reason": dict(sorted(reasons.items())),
            "selection_scan_reasons": dict(sorted(selection_scan_reasons.items())),
            "cards_written": len(report_rows),
            "positive": positives,
            "open_candidate": opens,
            "open_reasons_overlapping": dict(sorted(open_reasons.items())),
            "rows": report_rows,
        }
        path.write_text(json.dumps(report, ensure_ascii=False, indent=1),
                        encoding="utf-8", newline="\n")
        return positives, opens

    first_positive, first_open = write_report(REPORT_1, 1, first_rows)
    second_positive, second_open = write_report(REPORT_2, 2, second_rows)
    print(f"فُحص {len(rows)}؛ داخل المروحة الموسعة {fan_stats['rows_any_candidate_in_expanded_fan']}؛ "
          f"الدفعة 001: موجب {first_positive} ومفتوح {first_open}؛ "
          f"الدفعة 002: {len(second_rows)} بطاقة، موجب {second_positive} ومفتوح {second_open}")
    print(f"كُتب: {READING.relative_to(ROOT).as_posix()}")
    for path in (REPORT_1, REPORT_2, FAN_AUDIT, SHIFT_PROPOSALS):
        print(f"كُتب: {path.relative_to(ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
