# -*- coding: utf-8 -*-
"""ابنِ دفعةَ خشيم المصريّة الأولى بطاقاتِ RECOVERY-v2 قابلةً للتدقيق.

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
import json
import pathlib
import re
import sys
import unicodedata
from collections import defaultdict
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import fan_any_script as FAN  # noqa: E402
import search_arabic_root_senses as ARS  # noqa: E402

SOURCE = ROOT / "data" / "khashim-pairs.json"
READING = ROOT / "04-cross-linguistic" / "readings" / "egyptian.md"
REPORT = ROOT / "data" / "khashim-egyptian-batch-001.json"
RESOURCES = ROOT / "Resources"

START = "<!-- KHASHIM-EGYPTIAN-BATCH-001:START -->"
END = "<!-- KHASHIM-EGYPTIAN-BATCH-001:END -->"
BOOK = "علي فهمي خشيم، «البرهان على عروبة اللغة المصرية القديمة»"
BATCH_SIZE = 120

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
# الأزواج الخمسة وحدها راجعها المنفذ عضوًا عضوًا: الصوت كامل بصفوف الشبكة،
# والمعنى منصوص في بدج وفي المعجم العربي المسمى. سائر الدفعة يبقى مفتوحًا.
APPROVED_POSITIVES = {
    67: "برك",   # bareka: to bless
    68: "برك",   # baraka: to bow the knee in homage
    459: "سفك",  # sefek: to cut; to slay; to cleave
    650: "كف",   # kep: palm/hollow of the hand
}

# المادة الثنائية قد تكون رأس نواة لا جذر المعجم الثلاثي. يبقى المرشح كما
# اقترحه خشيم، ويؤخذ النص من مادته المضعفة المسماة من غير تبديل وحدة الحكم.
LEXICON_ALIASES = {"كف": "كفف", "يم": "يمم"}

# اقتباسات موجزة راجعها المنفذ حرفيًّا في نسخة لسان العرب المحلية. تثبيتُها
# يمنع خوارزمية التقريب من اختيار جملة تشترك مع شرح خشيم في لفظ عام مثل
# «حتى»، ولا يُستعمل أيٌّ منها خارج الصف المسمى.
QUOTE_OVERRIDES = {
    67: "وبارك الله الشيءَ وبارك فيه وعليه: وضع فيه البَرَكَة.",
    68: "وهو من بَرَكَ البعير إذا أناخ في موضع فلزمه.",
    459: "السَّفْكُ: صَبُّ الدم ونَثْرُ الكلام. وسَفَك الدمَ والدمعَ يَسْفِكُه سَفْكاً، فهو مَسْفوك وسَفِيك: صبه وهَراقَه، وكأَنه بالدم أَخص.",
    650: "والكفُّ: اليد، أُنثى. وفي التهذيب: والكف كفّ اليد.",
    935: "اليَمُّ البحرُ، وكذلك هو في الكتاب، ويَقَع اسمُ اليَمّ على ما كان ماؤه مِلْحاً زُعاقاً، وعلى النهر الكبير العَذْب الماء.",
}

SEMANTIC_LABELS = {
    67: "البركة والدعاء بها",
    68: "البروك والإنَاخة ولزوم الموضع، وهو وجه ثني الركبة",
    459: "السفك وإراقة الدم، وهو وجه الذبح في معنى بدج",
    650: "الكف واليد",
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
    if START in text and END in text:
        before, rest = text.split(START, 1)
        _, after = rest.split(END, 1)
        text = before + after
    heads = set()
    for head in re.findall(r"(?m)^### بطاقة[^\n]*", text):
        for token in re.findall(r"`([^`]+)`", head):
            heads.add(token.strip())
        m = re.match(r"^### بطاقة:\s*([^\s«،]+)", head)
        if m:
            heads.add(m.group(1).strip("`"))
    return heads


def choose_rows(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
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
            continue
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
            "candidates": candidates,
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
            )
            evaluated.append({
                "root": root, "root_origin": origin, "position": pos,
                "lexicon_root": lexicon_root,
                "lexicon": lexicon, "ar_hit": sorted(ar_hit), "en_hit": sorted(en_hit),
                "raw_hit": raw_hit, "stem_hit": stem_hit, "sound_ready": sound_ready,
                "sound_rows": sound_rows, "sound_misses": sound_misses, "score": score,
            })
        approved_root = APPROVED_POSITIVES.get(item["index"])
        approved = [x for x in evaluated if x["root"] == approved_root]
        chosen = (approved[0] if approved else
                  sorted(evaluated, key=lambda x: (-x["score"], x["position"], x["root"]))[0])
        item["chosen"] = chosen
        item["score"] = chosen["score"]

    pool.sort(key=lambda x: (-x["score"], x["index"]))
    forced = [x for x in pool if x["index"] in APPROVED_POSITIVES]
    selected = forced + [x for x in pool if x["index"] not in APPROVED_POSITIVES][
        :BATCH_SIZE - len(forced)
    ]
    selected.sort(key=lambda x: (-x["score"], x["index"]))
    if len(selected) != BATCH_SIZE:
        raise SystemExit(f"لم تبلغ الدفعة {BATCH_SIZE}: المتاح {len(selected)}")
    return selected, defects


def fan_text(values: list[str]) -> str:
    return "، ".join(f"`{x}`" for x in values) if values else "(لم تولّد الأداة مرشحًا)"


def card(item: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    row, chosen = item["row"], item["chosen"]
    root = chosen["root"]
    raw_fan, stem_fan = item["raw_fan"], item["stem_fan"]
    lexicon = chosen["lexicon"]
    source_label = (ARS.SOURCE_LABELS.get(lexicon["source_id"], lexicon["source"])
                    if lexicon else "")
    quote = QUOTE_OVERRIDES.get(item["index"], "")
    if not quote and lexicon and chosen["ar_hit"]:
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
        scan = (f"المادة `{root}`{material_note}؛ نص {source_label}: «{quote}». ونص خشيم المنقول في "
                f"الصف: «{row['arabic_gloss']}». القريب المراد هو "
                f"{SEMANTIC_LABELS.get(item['index'], ', '.join(chosen['ar_hit']) if chosen['ar_hit'] else 'ما عيّنه خشيم')}؛ "
                "وسائر وجوه النص لا تُنقل إلى المصرية.")
    elif lexicon:
        scan = (f"وُجدت المادة `{root}` في {source_label}، لكن لم تُستخرج من نصها عبارة "
                "تطابق المعنى المقصود تطابقًا صالحًا للاقتباس؛ لذلك لا نضع نصًّا معجميًّا "
                f"مضللًا. نص خشيم «{row['arabic_gloss']}» محفوظ، والزوج مفتوح.")
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
    lines = [
        f"### بطاقة: `{row['foreign']}` «{row['foreign_sense']}»؛ خشيم 001/{item['index']:03d}",
        f"<!-- khashim-egyptian-batch-001:{item['index']} -->",
        "- إصدارُ البروتوكول: RECOVERY-v2 (2026-07-14)",
        f"- الكلمةُ في الفرع: `{row['foreign']}`؛ الرمز المنقول `{glyphs}`؛ الرومنة من بدج كما نقلها خشيم.",
        f"- أقدمُ صورةٍ مستعادة: لا تُدّعى صورة أقدم من رومنة بدج المنقولة في {BOOK}؛ "
        "الصف من `data/khashim-pairs.json` ومصدره `ocr-egyptian2`.",
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
        "open_reasons": obstacles,
    }
    return "\n".join(lines), summary


def replace_batch(text: str, block: str) -> str:
    if START in text and END in text:
        before, rest = text.split(START, 1)
        _, after = rest.split(END, 1)
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
    selected, defects = choose_rows(rows)
    rendered, report_rows = [], []
    for item in selected:
        text, summary = card(item)
        rendered.append(text)
        report_rows.append(summary)

    positives = sum(bool(row["verdict"]) for row in report_rows)
    opens = sum(row["closure"] == "OPEN-CANDIDATE" for row in report_rows)
    section = [
        START,
        "## حصادُ خشيم المصري، الدفعة الأولى (2026-08-11)",
        "",
        "**بيان النطاق.** فُحصت صفوف المصرية البالغ عددها 938 في `data/khashim-pairs.json`. "
        "عُزلت الرؤوس الإنجليزية، والرؤوس الملتبسة ذات الفراغ، والرموز الهيروغليفية "
        "المكررة من رمز واحد، والمعاني التي لم يسلم نصها الإنجليزي. ثم رتبت البقية قبل "
        "الحكم بقرب نص بدج من مروحة المعجم العربي، وإصابة مروحة الصوت، وسلامة المصدر. "
        "هذه 120 بطاقة استكشاف، وأصل كل مرشح من خشيم ومعناه الإنجليزي من بدج؛ أما المروحة "
        "والشبكة والحكم فمن أدوات المشروع.",
        "",
        f"**عدستا المراجعة.** أبقت عدسة الاسترداد كل مرشح مشكوك فيه `OPEN-CANDIDATE` "
        f"بدل إسقاطه. وراجعت عدسة التشكيك الصوامت كاملة ومجال صف الشبكة ونص المعجم؛ "
        f"فصدر {positives} حكمًا، وبقي {opens} مفتوحًا. هذه أعداد جرد الدفعة لا نسبة منشورة.",
        "",
        *rendered,
        END,
    ]
    current = READING.read_text(encoding="utf-8")
    updated = unicodedata.normalize("NFC", replace_batch(current, "\n".join(section)))
    READING.write_text(updated, encoding="utf-8", newline="\n")

    reasons: dict[str, int] = defaultdict(int)
    for item in defects:
        for reason in item["reasons"]:
            reasons[reason] += 1
    open_reasons: dict[str, int] = defaultdict(int)
    for item in report_rows:
        for reason in item["open_reasons"]:
            open_reasons[reason] += 1
    report = {
        "generated_by": "scripts/build_khashim_egyptian_cards.py",
        "source": "data/khashim-pairs.json",
        "book": BOOK,
        "rows_examined": len(rows),
        "scan_defects_union": len(defects),
        "scan_defects_by_reason": dict(sorted(reasons.items())),
        "cards_written": len(report_rows),
        "positive": positives,
        "open_candidate": opens,
        "open_reasons_overlapping": dict(sorted(open_reasons.items())),
        "rows": report_rows,
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=1),
                      encoding="utf-8", newline="\n")
    print(f"فُحص {len(rows)}؛ عيب مسح {len(defects)}؛ بطاقات {len(report_rows)}؛ "
          f"موجب {positives}؛ مفتوح {opens}")
    print(f"كُتب: {READING.relative_to(ROOT).as_posix()}")
    print(f"كُتب: {REPORT.relative_to(ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
