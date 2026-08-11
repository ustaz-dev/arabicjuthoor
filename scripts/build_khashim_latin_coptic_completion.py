# -*- coding: utf-8 -*-
"""أعد حكم حصاد خشيم في اللاتينية والقبطية على المروحة كلها.

وحدة الحكم هي مدخل الفرع ومعناه، لا صف المسح. لذلك تدمج الشواهد القديمة
والجديدة للمدخل نفسه، ثم تثبت مروحة المرشحين قبل اختبار المعنى. يفحص كل
مرشح في المروحة بالصوت والنص المعجمي المقترن بجذره والمدار المكتوب. يبقى
كل اقتراح لخشيم ظاهرًا، سواء دخل المروحة أم بقي خارجها.
"""
from __future__ import annotations

import json
import pathlib
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import build_khashim_old_latin_cards as LAT  # noqa: E402
import search_arabic_root_senses as ARS  # noqa: E402

SOURCE = ROOT / "data" / "khashim-pairs.json"
RESOURCES = ROOT / "Resources"
LATIN_READING = ROOT / "04-cross-linguistic" / "readings" / "old-latin.md"
COPTIC_READING = ROOT / "04-cross-linguistic" / "readings" / "coptic.md"
LATIN_REPORT = ROOT / "data" / "khashim-old-latin-batch-002.json"
LATIN_LEGACY_REPORT = ROOT / "data" / "khashim-old-latin-batch-001.json"
COPTIC_REPORT = ROOT / "data" / "khashim-coptic-batch-001.json"
LATIN_AUDIT = ROOT / "05-audits" / "2026-08-11-khashim-old-latin-batch-002.md"
LATIN_LEGACY_AUDIT = ROOT / "05-audits" / "2026-08-11-khashim-old-latin-batch-001.md"
COPTIC_AUDIT = ROOT / "05-audits" / "2026-08-11-khashim-coptic-batch-001.md"

LATIN_LEGACY_START = "<!-- KHASHIM-OLD-LATIN-BATCH-001:START -->"
LATIN_LEGACY_END = "<!-- KHASHIM-OLD-LATIN-BATCH-001:END -->"
LATIN_START = "<!-- KHASHIM-OLD-LATIN-BATCH-002:START -->"
LATIN_END = "<!-- KHASHIM-OLD-LATIN-BATCH-002:END -->"
COPTIC_START = "<!-- KHASHIM-COPTIC-BATCH-001:START -->"
COPTIC_END = "<!-- KHASHIM-COPTIC-BATCH-001:END -->"

LATIN_BOOK = "علي فهمي خشيم، «اللاتينيّة عربيّة»"
COPTIC_BOOK = "علي فهمي خشيم، «القبطيّة عربيّة»"
FALLEN = "(سقطَ حرفُه في المسح)"
LATIN_SOURCE_ROWS = 562
LATIN_UNIFIED_CARDS = 533
COPTIC_SOURCE_ROWS = 186
LATIN_BASELINE = 41
COPTIC_BASELINE = 189

LATIN_HEAD = LAT.LATIN_HEAD
COPTIC_ROMAN_HEAD = re.compile(
    r"^[A-Za-zÀ-žĀ-ſæœÆŒ][A-Za-zÀ-žĀ-ſæœÆŒ,' -]{1,34}$"
)

# مواضع قرأها الممر السابق قراءة بشرية مفصلة. تبقى نصوصها كما هي، لكن
# الحكم الجديد لا يستعملها إلا للمرشح نفسه بعد فحص المروحة كلها.
LATIN_MANUAL_ORBITS = dict(LAT.HUMAN_ORBITS)
COPTIC_MANUAL_ORBITS: dict[tuple[str, str, str], str] = {
    ("poh", "بحح", "ب ح وصل. جاء. حلّ بالمكان"): (
        "الوصول والمجيء والحلول بالمكان تنتهي إلى التمكن في الحلول والمقام الذي "
        "نقله خشيم في مادة `بحح`؛ فالمدار بلوغ المكان والاستقرار فيه."
    ),
    ("meini", "من", "مبانٍ. علامات"): (
        "المباني العالية تثبت بقوتها وتبرز علامات باقية؛ وهذا هو وجه القوة والثبات "
        "الذي يسميه نص العربية ومدار النواة `من`."
    ),
    ("mise", "مشي", "ولد. مولود"): (
        "الولادة في الفرع هي نفسها قول النص المقترن بـ`مشي`: مشت الغنم، أي كثر "
        "أولادها، وأمشى، أي ولد كثيرًا؛ فالمدار مباشر في التولد."
    ),
    ("mir, mer", "مر", "ربط"): (
        "الربط في الفرع يطابق النص في الحبل الذي أجيد فتله وفي أمر الشيء، أي شده "
        "بالمرار؛ فالمدار شد الحبل وربطه."
    ),
}

# هذه ليست إصابات آلية. هي مواضع راجع فيها النص المقترن بالجذر عند خشيم
# وظهر فيه معنى الفرع صريحًا. تصاغ منها جملة المدار، ولا تعمم إلى جذر آخر.
KHASHIM_DIRECT: dict[tuple[str, str], str] = {
    ("bonus", "بنن"): "الجودة والطيب",
    ("caelum", "قلم"): "القطع والقلم",
    ("caleo", "قلي"): "الحرارة والشواء",
    ("clamo", "كلم"): "الكلام والإعلان بالصوت",
    ("cleps", "كلب"): "الأخذ والسرقة",
    ("crinis", "قرن"): "ذؤابة المرأة وضفيرتها",
    ("cruppa", "كرب"): "الحبل الغليظ والشد",
    ("curro", "جري"): "الجري والركض والعدو",
    ("domo", "دم"): "الضرب والإخضاع",
    ("fulgo", "فلج"): "الضياء والإشراق",
    ("geno", "جني"): "إنتاج الثمر وجنيه",
    ("grumus", "جرم"): "النواة والبذرة",
    ("hinnio", "حن"): "صوت الدابة وحنينها",
    ("munus", "من"): "العطاء والإنعام",
    ("mutilus", "مثل"): "القطع والتمثيل بالأطراف",
    ("neruus", "نير"): "الخيط والرباط",
    ("pars", "فرس"): "القطع والفصل",
    ("remus", "رمي"): "القذف والرمي",
    ("sem", "زم"): "الجمع والوحدة بالشد",
    ("semita", "سمت"): "الطريق والسمت",
    ("sera", "سرر"): "الإغلاق والكتم",
    ("sesima", "سمم"): "السمسم والجلجلان",
    ("socius", "شقق"): "الشقيق والرفيق والمرافق",
    ("talea", "تول"): "الفسيلة وصغار النخل",
    ("taurus", "ثور"): "الثور، ذكر البقر",
    ("vaco", "بوق"): "الجوف والفراغ",
    ("veredus", "برد"): "البريد ودابته",
}

# مرشحات لم يقترحها خشيم في المدخل، ففحصت في الذخيرة المحلية. تحدد cues
# موضع النص الذي يحمل المعنى حتى لا ينتخب شاهد عارض من مادة طويلة.
LOCAL_ORBITS: dict[tuple[str, str], dict[str, Any]] = {
    ("frico", "فرك"): {
        "cues": ("دلك", "دلك الشيء"),
        "orbit": "الفرك في نص المعجم هو دلك الشيء، ومعنى الفرع الحك؛ فالمدار حركة الاحتكاك نفسها.",
    },
    ("iterum", "تور"): {
        "cues": ("تارة أخرى", "مرة بعد مرة"),
        "orbit": "نص `تور` يقول: جاء به تارة أخرى، أي مرة بعد مرة؛ ومعنى الفرع الإعادة والتكرار، فالمدار مباشر.",
    },
    ("nimis", "نمي"): {
        "cues": ("النماء الزيادة", "الزيادة"),
        "orbit": "النماء في نص المعجم هو الزيادة، ومعنى الفرع الكثرة والوفرة؛ فالمدار ازدياد المقدار.",
    },
    ("sinapi", "صنب"): {
        "cues": ("الخردل",),
        "orbit": "الصناب في نص المعجم صباغ يتخذ من الخردل، ومعنى المدخل الخردل؛ فالمدار النبات نفسه ومنتجه.",
    },
    ("dirus", "ضرر"): {
        "cues": ("المضرة خلاف المنفعة", "الضرر"),
        "orbit": "الضرر والمضرة في نص المعجم أذى ونقصان وخلاف المنفعة، ومعنى الفرع الشر والشؤم؛ فالمدار الأذى الواقع.",
    },
    ("heli", "هول"): {
        "cues": ("الهول المخافة", "هو الخوف"),
        "orbit": "الهول في نص المعجم هو الخوف والمخافة من الأمر الشديد، ومعنى الفرع الخوف والرعب؛ فالمدار مباشر.",
    },
    ("moni", "مني"): {
        "cues": ("المنية الموت", "المنى والمنية"),
        "orbit": "المنى والمنية في نص المعجم هما الموت، وهو أحد معاني المدخل بنصه؛ فالمدار مباشر في الموت المقدر.",
    },
}

FEATURED = [
    ("remus", "رمي"), ("cuppa", "كوب"), ("cornu", "قرن"),
    ("carrus", "جرر"), ("gero", "جرر"), ("sorbeo", "شرب"),
    ("solidus", "صلد"), ("fodio", "فضض"), ("furca", "فرق"),
    ("seco", "شقق"), ("palus", "بلل"), ("pasta", "بسط"),
    ("lacus", "لجج"), ("mare", "مور"), ("nidor", "ندد"),
    ("storea", "سطر"), ("topia", "طيب"), ("castus", "قسط"),
    ("braca", "برك"), ("turris", "طور"),
]


def one_line(value: Any) -> str:
    return " ".join(str(value or "").split())


def quote(value: Any, limit: int = 460) -> str:
    text = one_line(value).replace("`", "ˋ")
    if len(text) <= limit:
        return text
    return text[:limit].rsplit(" ", 1)[0] + "…"


def normalized_key(row: dict[str, Any]) -> tuple[str, str]:
    return one_line(row.get("foreign")).casefold(), one_line(row.get("foreign_sense"))


def replace_block(text: str, start: str, end: str, block: str) -> str:
    if start in text and end in text:
        before, rest = text.split(start, 1)
        _, after = rest.split(end, 1)
        tail = after.lstrip()
        middle = block.rstrip()
        pieces = [before.rstrip()]
        if middle:
            pieces.append(middle)
        if tail:
            pieces.append(tail.rstrip())
        return "\n\n".join(piece for piece in pieces if piece) + "\n"
    if not block:
        return text
    return text.rstrip() + "\n\n" + block.rstrip() + "\n"


def original_latin_inventory(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    inventory = [
        row for row in rows
        if row.get("tongue") == "old-latin"
        and (
            row.get("source") == "ocr-latin"
            or (
                row.get("source") == "khashim-latin"
                and not row.get("ocr_recovery")
                and row.get("foreign") != FALLEN
            )
        )
    ]
    if len(inventory) != LATIN_SOURCE_ROWS:
        raise SystemExit(
            f"تغيّر مقام اللاتينية: {len(inventory)}، والمتوقع {LATIN_SOURCE_ROWS}"
        )
    return inventory


def unified_latin_cards(
    inventory: list[dict[str, Any]], all_rows: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    witnesses: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in all_rows:
        if row.get("tongue") != "old-latin" or one_line(row.get("foreign")) == FALLEN:
            continue
        witnesses[normalized_key(row)].append(row)

    cards: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for source_index, row in enumerate(inventory):
        key = normalized_key(row)
        if key in seen:
            continue
        seen.add(key)
        members = [member for member in inventory if normalized_key(member) == key]
        cards.append({
            "source_indices": [
                index for index, member in enumerate(inventory) if normalized_key(member) == key
            ],
            "foreign": key[0],
            "sense": key[1],
            "members": members,
            "witnesses": witnesses.get(key, members),
            "first_source_index": source_index,
        })
    if len(cards) != LATIN_UNIFIED_CARDS:
        raise SystemExit(
            f"تغيّر عدد البطاقات اللاتينية الموحدة: {len(cards)}، والمتوقع {LATIN_UNIFIED_CARDS}"
        )
    return cards


def khashim_proposals(witnesses: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}
    seen_text: dict[str, set[str]] = defaultdict(set)
    for row in witnesses:
        root = LAT.ar_bare(row.get("arabic_root", ""))
        if not root:
            continue
        proposal = grouped.setdefault(root, {
            "root": root, "texts": [], "sources": [], "source_lines": [],
            "khashim_nuclei": [],
        })
        source = one_line(row.get("source"))
        if source and source not in proposal["sources"]:
            proposal["sources"].append(source)
        line = row.get("source_line") or (row.get("ocr_recovery") or {}).get("source_line")
        if line is not None and line not in proposal["source_lines"]:
            proposal["source_lines"].append(line)
        nucleus = LAT.ar_bare(row.get("arabic_nucleus", ""))
        if nucleus and nucleus not in proposal["khashim_nuclei"]:
            proposal["khashim_nuclei"].append(nucleus)
        text = one_line(row.get("arabic_gloss"))
        if text and text not in seen_text[root]:
            seen_text[root].add(text)
            proposal["texts"].append(text)
    return list(grouped.values())


def preferred_lexicon(
    matches: list[dict[str, Any]], cues: tuple[str, ...] = ()
) -> dict[str, Any] | None:
    ranked: list[tuple[int, int, int, str, dict[str, Any]]] = []
    priority = {
        "lisan": 0, "taj_al_arus": 1, "al_sihah": 2, "al_muhkam": 3,
        "kitab_al_ayn": 4, "asas_al_balagha": 5,
    }
    folded_cues = tuple(LAT.ar_bare(cue) for cue in cues)
    for item in matches:
        source_id = ARS.canonical_source_id(str(item.get("source") or ""))
        if source_id not in priority:
            continue
        definition = one_line(item.get("definition"))
        if not definition:
            continue
        bare_definition = LAT.ar_bare(definition)
        cue_hits = sum(cue in bare_definition for cue in folded_cues if cue)
        if cues and not cue_hits:
            continue
        ranked.append((-cue_hits, priority[source_id], -len(definition), definition, {
            **item,
            "source_id": source_id,
            "source_label": ARS.SOURCE_LABELS[source_id],
            "definition": definition,
        }))
    if not ranked:
        return None
    return min(ranked, key=lambda item: item[:4])[4]


def relevant_excerpt(text: str, cues: tuple[str, ...] = (), limit: int = 360) -> str:
    text = one_line(text)
    if not text:
        return ""
    parts = [part.strip() for part in re.split(r"(?<=[.؟!])\s+|\s*[؛]\s*", text) if part.strip()]
    folded = tuple(LAT.ar_bare(cue) for cue in cues)
    if folded:
        matching = [
            part for part in parts
            if any(cue and cue in LAT.ar_bare(part) for cue in folded)
        ]
        if matching:
            text = min(matching, key=len)
    if len(text) <= limit:
        return text
    return text[:limit].rsplit(" ", 1)[0] + "…"


def semantic_cues(label: str) -> tuple[str, ...]:
    cues: list[str] = []
    for word in re.findall(r"[\u0621-\u064a]+", label):
        word = re.sub(r"^و", "", word)
        word = re.sub(r"^ال", "", word)
        if len(word) >= 3 and word not in cues:
            cues.append(word)
    return tuple(cues)


def sound_audit(
    skeleton: list[str], root: str, tongue_ar: str, tongue_en: str
) -> tuple[bool, list[str], list[str]]:
    strong = "".join(letter for letter in root if letter not in "اوي")
    weak_positions = [index for index, letter in enumerate(root) if letter in "اوي"]
    geminate = len(skeleton) == 2 and len(root) == 3 and root[-1] == root[-2]
    weak = len(skeleton) == 2 and len(root) == 3 and len(weak_positions) == 1
    if len(skeleton) != len(root) and not geminate and not weak:
        return False, [], [
            f"عدد الصوامت {len(skeleton)} في الفرع و{len(root)} في المرشح"
        ]
    aligned = root[:2] if geminate else strong if weak else root
    if len(aligned) != len(skeleton):
        return False, [], [
            f"تعذر رصف الهيكل `{''.join(skeleton)}` بالمادة `{root}`"
        ]
    rows: list[str] = []
    misses: list[str] = []
    for symbol, arabic in zip(skeleton, aligned):
        row_id = LAT.pair_row(symbol, arabic)
        normalized = "c=[k] ثم " if symbol == "c" else ""
        query = f"`{symbol}` + `{arabic}` + «{tongue_ar}/{tongue_en}» في عمود الشاهد"
        if row_id:
            rows.append(f"{normalized}{symbol}↔{arabic} = `{row_id}` (بحث: {query})")
        else:
            misses.append(f"{symbol}↔{arabic} (بحث: {query}؛ لا صف مناسب)")
    if geminate:
        rows.append(f"باب المضاعف: تكرير `{root[-1]}` في آخر الجذر العربي")
    if weak:
        position = ("الأول" if weak_positions[0] == 0 else
                    "الأوسط" if weak_positions[0] == 1 else "الأخير")
        rows.append(
            f"باب المعتل: حرف العلة `{root[weak_positions[0]]}` في الموضع {position} "
            "يقابل صائت الفرع، مع بقاء الصامتين القويين"
        )
    return not misses, rows, misses


def orbit_for(
    language: str, foreign: str, sense: str, root: str, has_khashim_text: bool
) -> tuple[str, str, tuple[str, ...]]:
    if language == "latin" and (foreign, root) in LATIN_MANUAL_ORBITS:
        return LATIN_MANUAL_ORBITS[(foreign, root)], "مراجعة بشرية سابقة محفوظة", (root,)
    if language == "coptic" and (foreign, root, sense) in COPTIC_MANUAL_ORBITS:
        return COPTIC_MANUAL_ORBITS[(foreign, root, sense)], "مراجعة بشرية سابقة محفوظة", (root,)
    if has_khashim_text and (foreign, root) in KHASHIM_DIRECT:
        center = KHASHIM_DIRECT[(foreign, root)]
        orbit = (
            f"معنى الفرع «{sense}» ونص خشيم المقترن بالجذر `{root}` يلتقيان صراحة "
            f"في {center}؛ فالمدار مباشر في هذا المعنى المسمى."
        )
        return orbit, "نص خشيم المقترن بالجذر نفسه", semantic_cues(center)
    local = LOCAL_ORBITS.get((foreign, root))
    if local:
        return str(local["orbit"]), "ذخيرة المعاجم العربية المحلية", tuple(local["cues"])
    return "", "", ()


def evaluate_card(
    language: str,
    card_index: int,
    foreign: str,
    sense: str,
    witnesses: list[dict[str, Any]],
    source_indices: list[int],
    lexica: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    proposals = khashim_proposals(witnesses)
    proposals_by_root = {proposal["root"]: proposal for proposal in proposals}
    if language == "latin":
        valid_head = bool(LATIN_HEAD.fullmatch(foreign))
        analysis_head = foreign
        tongue_ar, tongue_en = "اللاتينيّة", "Latin"
        book = LATIN_BOOK
    else:
        valid_head = bool(COPTIC_ROMAN_HEAD.fullmatch(foreign)) and any(
            witness.get("source") == "ocr-coptic" for witness in witnesses
        )
        analysis_head = foreign.split(",", 1)[0].strip()
        tongue_ar, tongue_en = "القبطيّة", "Coptic"
        book = COPTIC_BOOK

    if valid_head:
        fan = LAT.candidate_fan(analysis_head, "")
        candidates = fan["full"]
    else:
        fan = {
            "stem": analysis_head,
            "stripping": "تعذر توليد المروحة لأن رأس الفرع ليس رومنة صالحة",
            "raw_skeleton": [], "stem_skeleton": [], "route_skeleton": [],
            "full": [],
        }
        candidates = []

    candidate_rows: list[dict[str, Any]] = []
    for position, root in enumerate(candidates, 1):
        routed = LAT.candidate_fan(analysis_head, root)
        sound, sound_rows, sound_misses = sound_audit(
            routed["route_skeleton"], root, tongue_ar, tongue_en
        )
        proposal = proposals_by_root.get(root)
        has_khashim_text = bool(proposal and proposal["texts"])
        orbit, orbit_source, cues = orbit_for(
            language, foreign, sense, root, has_khashim_text
        )
        if has_khashim_text:
            texts = proposal["texts"]
            if cues:
                matching = [
                    text for text in texts
                    if any(LAT.ar_bare(cue) in LAT.ar_bare(text) for cue in cues)
                ]
                selected_text = min(matching or texts, key=len)
            else:
                selected_text = min(texts, key=len)
            lexicon_source = f"{book}؛ نص خشيم المقترن بالجذر نفسه"
            lexicon_origin = "khashim"
        else:
            witness = preferred_lexicon(lexica.get(root, []), cues=cues)
            if witness is None and not cues:
                witness = preferred_lexicon(lexica.get(root, []))
            selected_text = witness["definition"] if witness else ""
            lexicon_source = witness.get("source_label", "") if witness else ""
            lexicon_origin = "resources" if witness else None
        lexicon_excerpt = relevant_excerpt(selected_text, cues=cues)
        lexicon_ready = bool(selected_text)
        orbit_ready = bool(orbit and sense)
        loan = LAT.explicit_loan(" ".join((sense, lexicon_excerpt)))
        candidate_rows.append({
            "root": root,
            "fan_position": position,
            "fan_source": routed["source"],
            "route_skeleton": routed["route_skeleton"],
            "sound_ready": sound,
            "sound_rows": sound_rows,
            "sound_misses": sound_misses,
            "named_lexicon_ready": lexicon_ready,
            "named_lexicon_source": lexicon_source or None,
            "lexicon_origin": lexicon_origin,
            "lexicon_excerpt": lexicon_excerpt or None,
            "written_orbit_ready": orbit_ready,
            "written_orbit": orbit or None,
            "orbit_source": orbit_source or None,
            "loan_marker": loan,
            "three_legs": {
                "sound": sound,
                "named_lexicon": lexicon_ready,
                "written_orbit": orbit_ready,
            },
        })

    blocking_loans = sorted({
        candidate["loan_marker"] for candidate in candidate_rows
        if all(candidate["three_legs"].values()) and candidate["loan_marker"]
    })
    positives = [
        candidate for candidate in candidate_rows
        if all(candidate["three_legs"].values()) and not candidate["loan_marker"]
    ]

    def winner_key(candidate: dict[str, Any]) -> tuple[int, int, int]:
        provenance = candidate.get("orbit_source") or ""
        rank = (0 if "مراجعة بشرية" in provenance else
                1 if candidate.get("lexicon_origin") == "khashim" else 2)
        degree = 0 if len(candidate["root"]) == 3 else 1 if len(candidate["root"]) == 2 else 2
        return rank, degree, int(candidate["fan_position"])

    winner = min(positives, key=winner_key) if positives else None
    fan_positions = {candidate["root"]: candidate["fan_position"] for candidate in candidate_rows}
    candidate_by_root = {candidate["root"]: candidate for candidate in candidate_rows}
    for proposal in proposals:
        proposal["fan_position"] = fan_positions.get(proposal["root"])
        proposal["fan_status"] = (
            "IN-FAN" if proposal["root"] in fan_positions else "OUTSIDE-FAN-PRESERVED"
        )
        candidate = candidate_by_root.get(proposal["root"])
        proposal["candidate_three_legs"] = candidate["three_legs"] if candidate else None

    if winner:
        closure = "READY"
        degree = "NUCLEUS-TRACE" if len(winner["root"]) == 2 else "ROOT-TRACE"
        verdict = degree
        open_reasons: list[str] = []
    else:
        closure = "OPEN-CANDIDATE"
        verdict = None
        open_reasons = []
        if not valid_head:
            open_reasons.append("استرداد رسم صالح لرأس الفرع قبل توليد المروحة")
        elif not candidate_rows:
            open_reasons.append("لم تولد الأداة مرشحًا من الهيكل المثبت")
        else:
            if not any(candidate["sound_ready"] for candidate in candidate_rows):
                open_reasons.append("لا مرشح في المروحة أكمل الرصف الصوتي")
            if not any(candidate["named_lexicon_ready"] for candidate in candidate_rows):
                open_reasons.append("لا مرشح في المروحة وجد له نص معجمي مقترن بجذره")
            if not any(candidate["written_orbit_ready"] for candidate in candidate_rows):
                open_reasons.append("لا مرشح في المروحة ثبت له مدار مكتوب بعد قراءة النص")
            if not open_reasons:
                open_reasons.append("استنفدت المروحة ولم تجتمع الأرجل الثلاث في مرشح واحد")
        if blocking_loans:
            open_reasons.append(
                "عزل اتجاه النقل المسمى «" + "؛ ".join(blocking_loans) + "»"
            )

    stats = {
        "fan_candidates": len(candidate_rows),
        "sound_ready": sum(candidate["sound_ready"] for candidate in candidate_rows),
        "named_lexicon_ready": sum(
            candidate["named_lexicon_ready"] for candidate in candidate_rows
        ),
        "written_orbit_ready": sum(
            candidate["written_orbit_ready"] for candidate in candidate_rows
        ),
        "three_legs_ready": len(positives),
    }
    return {
        "card_index": card_index,
        "language": language,
        "foreign": foreign,
        "sense": sense,
        "source_row_indices": source_indices,
        "source_row_count": len(source_indices),
        "source_witness_count": len(witnesses),
        "analysis_head": analysis_head,
        "valid_head": valid_head,
        "stripping": fan["stripping"],
        "raw_skeleton": fan["raw_skeleton"],
        "stem_skeleton": fan["stem_skeleton"],
        "fan": candidates,
        "fan_stats": stats,
        "khashim_proposals": proposals,
        "candidate_evaluations": candidate_rows,
        "loan_marker": None if winner else "؛ ".join(blocking_loans) or None,
        "winner": winner,
        "closure": closure,
        "verdict": verdict,
        "open_reasons": open_reasons,
    }


def compact_candidate_scan(card: dict[str, Any]) -> str:
    if not card["candidate_evaluations"]:
        return "(لا مروحة قبل استرداد الرأس)"
    values = []
    for candidate in card["candidate_evaluations"]:
        legs = candidate["three_legs"]
        values.append(
            f"`{candidate['root']}`[ص{'✓' if legs['sound'] else '×'}،"
            f"م{'✓' if legs['named_lexicon'] else '×'}،"
            f"د{'✓' if legs['written_orbit'] else '×'}]"
        )
    return "، ".join(values)


def proposal_text(card: dict[str, Any]) -> str:
    if not card["khashim_proposals"]:
        return "(لم يسترد اقتراح عربي من الصف)"
    values = []
    for proposal in card["khashim_proposals"]:
        location = (
            f"داخل المروحة في الرتبة {proposal['fan_position']}"
            if proposal["fan_position"] is not None
            else "خارج المروحة ومحفوظ في موضعه"
        )
        text = quote(proposal["texts"][0], 220) if proposal["texts"] else "بلا نص سالم"
        values.append(f"`{proposal['root']}`: {location}؛ «{text}»")
    return " | ".join(values)


def render_card(card: dict[str, Any], book: str, marker: str) -> str:
    winner = card["winner"]
    stats = card["fan_stats"]
    required = "؛ ".join(card["open_reasons"]) or "لا عائق معلق"
    verdict = (
        f"**{card['verdict']} (استكشاف)** بالمقابل `{winner['root']}`"
        if winner else "**غير صادر (استكشاف)**"
    )
    if winner:
        lexicon = (
            f"`{winner['root']}`؛ «{winner['lexicon_excerpt']}» "
            f"[{winner['named_lexicon_source']}]"
        )
        sound = "؛ ".join(winner["sound_rows"])
        orbit = winner["written_orbit"]
    else:
        lexicon = "لا نص منتخب للحكم؛ نصوص المرشحين محفوظة في سجل الفحص"
        sound = "لا مسار منتخب للحكم؛ مسارات المرشحين محفوظة في سجل الفحص"
        orbit = "لا مدار محكوم بعد استنفاد المرشحين المسجلين"
    source_rows = ", ".join(str(index) for index in card["source_row_indices"])
    lines = [
        f"### بطاقة: `{card['foreign']}` «{quote(card['sense']) if card['sense'] else '(المعنى لم يسترد)'}»؛ {marker}/{card['card_index']:03d}",
        f"<!-- {marker}:{card['card_index']} -->",
        "- إصدار البروتوكول: RECOVERY-v2 (استكشاف)، مع تطبيق البند 10 على المروحة كلها.",
        f"- وحدة البطاقة: صفوف المصدر [{source_rows}]، وعددها {card['source_row_count']}؛ دُمجت لأنها تحمل المدخل والمعنى نفسيهما.",
        f"- نسبة المصدر: معنى الفرع واقتراحات خشيم ونصوصه من {book}؛ المروحة والمسار والمدار والحكم أعمال المشروع.",
        f"- الكلمة في الفرع: `{card['foreign']}`؛ المعنى «{quote(card['sense'])}» بلا رتوش.",
        f"- الخطوة صفر: {card['stripping']}؛ الخام `{''.join(card['raw_skeleton']) or '∅'}`؛ البديل `{''.join(card['stem_skeleton']) or '∅'}`.",
        f"- اقتراحات خشيم مجتمعة: {proposal_text(card)}.",
        f"- المروحة المثبتة قبل المعنى: {', '.join(f'`{root}`' for root in card['fan']) if card['fan'] else '(فارغة)'}.",
        f"- فحص كل مرشحات المروحة: {compact_candidate_scan(card)}.",
        f"- حصيلة الفحص: المروحة={stats['fan_candidates']}؛ الصوت={stats['sound_ready']}؛ النص المقترن بالجذر={stats['named_lexicon_ready']}؛ المدار المكتوب={stats['written_orbit_ready']}؛ مكتمل الأرجل={stats['three_legs_ready']}.",
        f"- المقابل من اللسان: {lexicon}.",
        f"- مسار الصوت المنتخب: {sound}.",
        f"- المدار: {orbit}.",
        f"- المصفاة: {'علامة الاتجاه «' + card['loan_marker'] + '» تمنع حكم النسب' if card['loan_marker'] else 'لا مانح أجنبي صريح في نص البطاقة؛ غياب الاسم ليس إثبات أصالة'}.",
        "- فصل المتجانسات: الحكم لهذا المدخل وهذا المعنى وحدهما، ولا يرثه متحد الرسم أو معنى آخر.",
        "- جسور الاسترداد المفحوصة: المسحان؛ التعرية؛ المروحة كاملة؛ كل اقتراح لخشيم؛ نص كل جذر من خشيم أو الذخيرة؛ الشبكة؛ المدار؛ الاتجاه.",
        f"- عائق: النوع={card['closure']}؛ يتطلب={required}",
        f"- حالة الإغلاق: {card['closure']}",
        f"- الحكم (استكشاف): {verdict}",
        "- ملاحظات: عدسة الاسترداد منعت احتكار أول مقابل، وعدسة التشكيك لم تقبل تقاطع لفظ عارض بدل مدار مقروء.",
    ]
    return "\n".join(lines)


def write_legacy_supersession() -> None:
    payload = {
        "schema": "khashim-old-latin-superseded-v1",
        "batch": "001",
        "status": "superseded",
        "reason": "دُمجت صفوف المسحين وحُكم على المروحة كلها في الدفعة 002",
        "superseded_by": "data/khashim-old-latin-batch-002.json",
        "rows": [],
    }
    LATIN_LEGACY_REPORT.write_text(
        json.dumps(payload, ensure_ascii=False, indent=1) + "\n",
        encoding="utf-8", newline="\n",
    )
    LATIN_LEGACY_AUDIT.write_text(
        "\n".join([
            "# حصاد خشيم للاتينية القديمة، الدفعة 001: سجل مستبدل",
            "",
            "استُبدلت هذه القسمة في 2026-08-11 لأن صفوف المدخل الواحد عبر المسحين "
            "كانت تتوزع على بطاقتين، ولأن الحكم كان يختبر اقتراح خشيم وحده. السجل "
            "النافذ الجامع هو `data/khashim-old-latin-batch-002.json`، والبطاقات "
            "النافذة في كتلة الحصاد الموحدة من قراءة اللاتينية القديمة.",
            "",
        ]),
        encoding="utf-8", newline="\n",
    )


def write_latin_audit(report: dict[str, Any]) -> None:
    rows = report["rows"]
    reasons = Counter(reason for row in rows for reason in row["open_reasons"])
    by_pair = {
        (row["foreign"], row["winner"]["root"]): row
        for row in rows if row["winner"]
    }
    featured = [by_pair[pair] for pair in FEATURED if pair in by_pair]
    if len(featured) != len(FEATURED):
        missing = [pair for pair in FEATURED if pair not in by_pair]
        raise SystemExit(f"غابت أزواج العشرين البارزة بعد إعادة الحكم: {missing}")
    lines = [
        "# إعادة حكم حصاد خشيم للاتينية القديمة على المروحة كلها",
        "", "## الأعداد", "",
        f"- صفوف المصدر المفحوصة: {report['inventory']['source_rows']}.",
        f"- البطاقات بعد دمج المدخل والمعنى عبر المسحين: {report['cards_written']}.",
        f"- مجموع مرشحات المراوح المفحوصة: {report['candidate_totals']['fan_candidates']}.",
        f"- موجب استكشافي: {report['positive']}. مفتوح: {report['open_candidate']}.",
        f"- عداد اللاتينية: {report['count_links']['before']}→{report['count_links']['after']}.",
        "", "## أسباب الفتح المتداخلة", "", "| السبب | البطاقات |", "|---|---:|",
    ]
    lines.extend(f"| {reason} | {count} |" for reason, count in reasons.most_common())
    lines.extend([
        "", "## أبرز عشرين", "",
        "| # | اللاتينية | المقابل المنتخب | المدار المكتوب |",
        "|---:|---|---|---|",
    ])
    for number, row in enumerate(featured, 1):
        winner = row["winner"]
        lines.append(
            f"| {number} | `{row['foreign']}` «{row['sense']}» | `{winner['root']}` | {winner['written_orbit']} |"
        )
    lines.extend([
        "", "## حراسة التصحيح", "",
        "ثُبتت المروحة قبل اختبار المعنى، ثم فُحص كل مرشح بالصوت والنص المعجمي "
        "المقترن بجذره والمدار المكتوب. اقتراح خشيم شاهد داخل القائمة لا سيد عليها. "
        "إذا غاب نصه عن جذر بعينه طُلب نص ذلك الجذر من الذخيرة المحلية، وإذا غاب "
        "من الموضعين بقيت الرجل المعجمية مفتوحة. لا ينقل نص جذر إلى جذر آخر.",
        "",
    ])
    LATIN_AUDIT.write_text("\n".join(lines), encoding="utf-8", newline="\n")


def write_coptic_audit(report: dict[str, Any]) -> None:
    rows = report["rows"]
    reasons = Counter(reason for row in rows for reason in row["open_reasons"])
    positives = [row for row in rows if row["winner"]]
    lines = [
        "# إعادة حكم حصاد خشيم للقبطية على المروحة كلها",
        "", "## الأعداد", "",
        f"- صفوف المصدر والبطاقات: {report['cards_written']}.",
        f"- الرؤوس الصالحة لتوليد المروحة: {report['inventory']['usable_heads']}.",
        f"- مجموع مرشحات المراوح المفحوصة: {report['candidate_totals']['fan_candidates']}.",
        f"- موجب استكشافي: {report['positive']}. مفتوح: {report['open_candidate']}.",
        f"- عداد القبطية: {report['count_links']['before']}→{report['count_links']['after']}.",
        "", "## الموجبات", "", "| القبطية | المقابل المنتخب | المدار |", "|---|---|---|",
    ]
    for row in positives:
        winner = row["winner"]
        lines.append(
            f"| `{row['foreign']}` «{row['sense']}» | `{winner['root']}` | {winner['written_orbit']} |"
        )
    lines.extend(["", "## أسباب الفتح المتداخلة", "", "| السبب | البطاقات |", "|---|---:|"])
    lines.extend(f"| {reason} | {count} |" for reason, count in reasons.most_common())
    lines.extend([
        "", "## حراسة التصحيح", "",
        "فُحصت المروحة كلها في الرؤوس السبعة عشر السليمة. بقيت الصفوف القديمة "
        "ذات الرأس المكسور مفتوحة، مع حفظ اقتراحات خشيم ونصوصها، ولم تُنشأ لها "
        "مروحة من رسم غير مسترد.", "",
    ])
    COPTIC_AUDIT.write_text("\n".join(lines), encoding="utf-8", newline="\n")


def report_payload(
    language: str,
    rows: list[dict[str, Any]],
    inventory: dict[str, Any],
    baseline: int,
    book: str,
) -> dict[str, Any]:
    positive = sum(bool(row["winner"]) for row in rows)
    totals = Counter()
    for row in rows:
        totals.update(row["fan_stats"])
    return {
        "schema": "khashim-full-fan-reruling-v2",
        "generated_by": "scripts/build_khashim_latin_coptic_completion.py",
        "language": language,
        "source": "data/khashim-pairs.json",
        "book": book,
        "layer": "استكشاف",
        "inventory": inventory,
        "cards_written": len(rows),
        "positive": positive,
        "open_candidate": len(rows) - positive,
        "candidate_totals": dict(totals),
        "count_links": {"before": baseline, "after": baseline + positive},
        "rows": rows,
    }


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    payload = json.loads(SOURCE.read_text(encoding="utf-8"))
    all_rows = payload["rows"]
    inventory = original_latin_inventory(all_rows)
    latin_cards = unified_latin_cards(inventory, all_rows)
    coptic_cards = [
        {
            "foreign": normalized_key(row)[0],
            "sense": normalized_key(row)[1],
            "witnesses": [row],
            "source_indices": [index],
        }
        for index, row in enumerate(
            [row for row in all_rows if row.get("tongue") == "coptic"]
        )
    ]
    if len(coptic_cards) != COPTIC_SOURCE_ROWS:
        raise SystemExit(f"تغيّر مقام القبطية: {len(coptic_cards)}")

    all_candidate_roots: set[str] = set()
    for language, cards in (("latin", latin_cards), ("coptic", coptic_cards)):
        for card in cards:
            foreign = card["foreign"]
            usable = (
                bool(LATIN_HEAD.fullmatch(foreign)) if language == "latin"
                else bool(COPTIC_ROMAN_HEAD.fullmatch(foreign))
                and any(row.get("source") == "ocr-coptic" for row in card["witnesses"])
            )
            if usable:
                head = foreign if language == "latin" else foreign.split(",", 1)[0].strip()
                all_candidate_roots.update(LAT.candidate_fan(head, "")["full"])
    lexica = ARS.matches_for_roots(RESOURCES, all_candidate_roots, limit=None)

    latin_rows = [
        evaluate_card(
            "latin", index, card["foreign"], card["sense"], card["witnesses"],
            card["source_indices"], lexica,
        )
        for index, card in enumerate(latin_cards)
    ]
    coptic_rows = [
        evaluate_card(
            "coptic", index, card["foreign"], card["sense"], card["witnesses"],
            card["source_indices"], lexica,
        )
        for index, card in enumerate(coptic_cards)
    ]

    remus = [row for row in latin_rows if row["foreign"] == "remus"]
    if len(remus) != 1:
        raise SystemExit(f"لم تتوحد remus في بطاقة واحدة: {len(remus)}")
    remus_proposals = {proposal["root"] for proposal in remus[0]["khashim_proposals"]}
    if not {"رمي", "روى"} <= remus_proposals:
        raise SystemExit(f"غاب أحد اقتراحي خشيم في remus: {sorted(remus_proposals)}")
    if not remus[0]["winner"] or remus[0]["winner"]["root"] != "رمي":
        raise SystemExit("لم يصدر حكم remus بالمقابل رمي")
    if any(row["winner"] and not row["winner"]["written_orbit"] for row in latin_rows + coptic_rows):
        raise SystemExit("صدر حكم موجب بلا مدار مكتوب")

    latin_report = report_payload(
        "old-latin", latin_rows,
        {
            "source_rows": LATIN_SOURCE_ROWS,
            "unified_cards": len(latin_rows),
            "merged_duplicate_rows": LATIN_SOURCE_ROWS - len(latin_rows),
        },
        LATIN_BASELINE, LATIN_BOOK,
    )
    coptic_report = report_payload(
        "coptic", coptic_rows,
        {
            "source_rows": COPTIC_SOURCE_ROWS,
            "unified_cards": len(coptic_rows),
            "usable_heads": sum(row["valid_head"] for row in coptic_rows),
        },
        COPTIC_BASELINE, COPTIC_BOOK,
    )

    latin_section = "\n".join([
        LATIN_START,
        "## حصاد خشيم لللاتينية القديمة بعد إعادة الحكم على المروحة كلها (2026-08-11)",
        "",
        f"**المقام.** فُحصت صفوف المصدر الـ{LATIN_SOURCE_ROWS} كلها، ثم دُمجت الصفوف التي "
        f"تحمل المدخل والمعنى نفسيهما في {len(latin_rows)} بطاقة. لا يحتكر اقتراح خشيم "
        "الحكم؛ يبقى ظاهرًا في موضعه، وتفحص معه المروحة كاملة.",
        "",
        "**الأرجل الثلاث.** لكل مرشح سجل مستقل للصوت، والنص المعجمي المقترن بجذره "
        "من خشيم أو من الذخيرة، والمدار المكتوب. لا ينقل نص جذر إلى غيره.",
        "",
        f"**الحصيلة.** موجب {latin_report['positive']}؛ مفتوح {latin_report['open_candidate']}.",
        "",
        *[render_card(row, LATIN_BOOK, "khashim-old-latin-full-fan") for row in latin_rows],
        LATIN_END,
    ])
    latin_text = LATIN_READING.read_text(encoding="utf-8")
    latin_text = replace_block(latin_text, LATIN_LEGACY_START, LATIN_LEGACY_END, "")
    latin_text = replace_block(latin_text, LATIN_START, LATIN_END, latin_section)
    LATIN_READING.write_text(
        unicodedata.normalize("NFC", latin_text), encoding="utf-8", newline="\n"
    )

    coptic_section = "\n".join([
        COPTIC_START,
        "## حصاد خشيم للقبطية بعد إعادة الحكم على المروحة كلها (2026-08-11)",
        "",
        f"**المقام.** فُحصت البطاقات الـ{COPTIC_SOURCE_ROWS} كلها. تولدت المروحة في "
        f"{coptic_report['inventory']['usable_heads']} رأسًا سليمًا، وبقي الرأس المكسور "
        "مفتوحًا مع حفظ اقتراح خشيم.",
        "",
        f"**الحصيلة.** موجب {coptic_report['positive']}؛ مفتوح {coptic_report['open_candidate']}.",
        "",
        *[render_card(row, COPTIC_BOOK, "khashim-coptic-full-fan") for row in coptic_rows],
        COPTIC_END,
    ])
    COPTIC_READING.write_text(
        unicodedata.normalize("NFC", replace_block(
            COPTIC_READING.read_text(encoding="utf-8"),
            COPTIC_START, COPTIC_END, coptic_section,
        )),
        encoding="utf-8", newline="\n",
    )

    LATIN_REPORT.write_text(
        json.dumps(latin_report, ensure_ascii=False, indent=1) + "\n",
        encoding="utf-8", newline="\n",
    )
    COPTIC_REPORT.write_text(
        json.dumps(coptic_report, ensure_ascii=False, indent=1) + "\n",
        encoding="utf-8", newline="\n",
    )
    write_legacy_supersession()
    write_latin_audit(latin_report)
    write_coptic_audit(coptic_report)
    print(
        f"اللاتينية: {LATIN_SOURCE_ROWS} صفًا→{len(latin_rows)} بطاقة؛ "
        f"موجب {latin_report['positive']}، مفتوح {latin_report['open_candidate']}."
    )
    print(
        f"القبطية: {len(coptic_rows)} بطاقة؛ موجب {coptic_report['positive']}، "
        f"مفتوح {coptic_report['open_candidate']}."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
