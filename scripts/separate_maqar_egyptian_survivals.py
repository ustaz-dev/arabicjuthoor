# -*- coding: utf-8 -*-
"""افصل بقايا مقّار المصرية عن بطاقات الصلة القبطية.

صف مقّار وحدته كلمة مصرية أو قبطية بإزاء لفظ عامي مصري، واتجاهه من
المصرية إلى العامية. لذلك يحفظ الجرد كله في طبقة مستقلة لا تدخل العد، ولا
تعاد منه بطاقة إلى ``readings/coptic.md`` إلا إذا أمكن رد اللفظ العربي إلى
مادة معجمية مسماة في لسان العرب أو تاج العروس. مرشح مقّار لا يستعمل جذرًا،
وتفحص مروحة الصوت كلها قبل الحكم.
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

import build_akkadian_maqar_coptic_cards as CARDS  # noqa: E402
import search_arabic_root_senses as LEX  # noqa: E402

SOURCE = ROOT / "data" / "prior-art-extended-pairs.json"
BATCHES = tuple(ROOT / "data" / f"maqar-coptic-batch-{n:03d}.json" for n in (1, 2, 3))
READING = ROOT / "04-cross-linguistic" / "readings" / "coptic.md"
SURVIVALS = ROOT / "04-cross-linguistic" / "exploration" / "maqar-egyptian-survivals.md"
REPORT = ROOT / "data" / "maqar-egyptian-survivals.json"
AUDIT = ROOT / "05-audits" / "2026-08-12-maqar-egyptian-survivals-separation.md"

SOURCE_START = "<!-- MAQAR-COPTIC-HARVEST-BATCH-001:START -->"
SOURCE_END = "<!-- MAQAR-COPTIC-HARVEST-BATCH-003:END -->"
ARCHIVE_START = "<!-- MAQAR-EGYPTIAN-SURVIVALS-OLD-CARDS:START -->"
ARCHIVE_END = "<!-- MAQAR-EGYPTIAN-SURVIVALS-OLD-CARDS:END -->"
NEW_START = "<!-- MAQAR-COPTIC-CLASSICAL-REGENERATION:START -->"
NEW_END = "<!-- MAQAR-COPTIC-CLASSICAL-REGENERATION:END -->"

EXPECTED = 865
DATE = "2026-08-12"
POSITIVE_ROOTS = {137, 159, 193, 205, 237, 247, 257, 270}
POSITIVE_NUCLEI = {342, 361, 371, 383, 414, 432, 493, 577, 580, 707}
PRIOR_POSITIVE = POSITIVE_ROOTS | POSITIVE_NUCLEI

# قرارات بشرية في مواضع لا يكفي فيها الرسم العامي لاختيار المادة. القيمة None
# تعني أن التجانس لم يثبت مادة بعينها، فيبقى الصف في طبقة البقايا وحدها.
OVERRIDES: dict[int, str | None] = {
    8: "موه", 9: "موه",                         # ماء، ومية في الاستعمال الحي
    62: None, 104: None, 173: None, 176: None, 345: None,
    110: "أرز", 192: "أمم", 207: "جبب", 213: "ثوب", 244: "تمم",
    274: "حير", 283: "أوه", 284: "أحح", 286: "أوه", 287: "أحح",
    295: "أمم", 296: None, 297: "أمم", 302: None, 304: None, 329: None,
    342: "تلل", 349: "جرأ", 351: "جرأ", 352: "جرأ", 358: None,
    361: "حلل", 362: "حمو", 365: "حمم", 369: "حمم", 371: "حكك",
    383: "خنن", 394: "ذرو", 410: "بنت", 414: "رشش", 427: "رأس",
    430: "رأس", 432: "ضمم", 493: "شكك", 577: "بتت", 580: "فتت",
    634: "لأم", 675: "مرأ", 676: "مرأ", 707: "هتت", 709: "هتت",
}

SOURCE_LABELS = {
    "lisan": "لسان العرب لابن منظور",
    "taj_al_arus": "تاج العروس لمرتضى الزبيدي",
    "al_sihah": "تاج اللغة وصحاح العربية للجوهري",
    "al_muhkam": "المحكم والمحيط الأعظم لابن سيده",
    "kitab_al_ayn": "كتاب العين للخليل بن أحمد",
    "asas_al_balagha": "أساس البلاغة للزمخشري",
    "al_mufradat": "المفردات في غريب القرآن للراغب",
    "al_misbah": "المصباح المنير",
    "al_muhit": "المحيط",
    "arabic_english": "المعجم العربي الإنجليزي",
}


def one_line(value: Any) -> str:
    return " ".join(str(value or "").split())


def safe(value: Any) -> str:
    return one_line(value).replace("|", "/").replace("`", "ˋ").replace("—", "،")


def fold_ar(value: Any) -> str:
    text = LEX.normalize_root(str(value or ""))
    return text.translate(str.maketrans("ٱأإآىةؤئ", "اااايهوي"))


def arabic_tokens(value: Any) -> set[str]:
    text = unicodedata.normalize("NFKC", str(value or ""))
    text = LEX.ARABIC_MARKS.sub("", text).replace("ـ", "")
    return {fold_ar(token) for token in re.findall(r"[ء-ي]+", text) if token}


def readable_pronunciation(value: str) -> str:
    """تقريب عربي للرومنة كما نقلها الصف، لا دعوى IPA مستقلة."""
    text = unicodedata.normalize("NFC", one_line(value)).lower()
    pairs = (
        ("sh", "ش"), ("kh", "خ"), ("gh", "غ"), ("th", "ث"),
        ("dh", "ذ"), ("ph", "ف"), ("ch", "خ"), ("ou", "و"),
        ("oo", "و"), ("ee", "ي"), ("ai", "اي"), ("ay", "اي"),
        ("ei", "اي"),
    )
    for left, right in pairs:
        text = text.replace(left, right)
    single = str.maketrans({
        "a": "ا", "e": "ي", "i": "ي", "o": "و", "u": "و", "y": "ي",
        "b": "ب", "p": "ب", "t": "ت", "d": "د", "j": "ج", "g": "ج",
        "k": "ك", "q": "ق", "f": "ف", "v": "ڤ", "s": "س", "z": "ز",
        "h": "ه", "m": "م", "n": "ن", "l": "ل", "r": "ر", "w": "و",
        "c": "ك", "x": "كس", "'": "ء", "-": "-", " ": " ",
    })
    out = text.translate(single)
    out = re.sub(r"([اوي])\1+", r"\1", out)
    if value.lower().startswith("a") and out.startswith("ا"):
        out = "آ" + out[1:]
    return out or value


def load_rows() -> list[dict[str, Any]]:
    payload = json.loads(SOURCE.read_text(encoding="utf-8"))
    rows = [
        row for row in payload["rows"]
        if row.get("source") == "ocr-maqar-egyptian-colloquial"
        and row.get("tongue") == "coptic"
    ]
    if len(rows) != EXPECTED:
        raise SystemExit(f"تغير مقام صفوف مقار القبطية: {len(rows)}")
    return rows


def load_batch_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in BATCHES:
        payload = json.loads(path.read_text(encoding="utf-8"))
        rows.extend(payload["rows"])
    rows.sort(key=lambda row: int(row["index"]))
    if [int(row["index"]) for row in rows] != list(range(EXPECTED)):
        raise SystemExit("جرد دفعات مقار غير متصل من 0 إلى 864")
    return rows


def source_work_ids(matches: list[dict[str, Any]]) -> set[str]:
    return {
        source_id for source_id in (
            LEX.canonical_source_id(str(item.get("source") or ""))
            for item in matches
        ) if source_id
    }


def build_morphology_index(wanted: set[str]) -> dict[str, list[str]]:
    path = ROOT / "Resources" / "Ten dictionaries for Arabic language" / "mukhtar.csv"
    out: dict[str, list[str]] = defaultdict(list)
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle, delimiter=";"):
            term = fold_ar(row.get("Normalized Term"))
            variants = {term}
            if term.startswith("ال") and len(term) > 3:
                variants.add(term[2:])
            root = LEX.normalize_root(row.get("Root") or "")
            if not root:
                continue
            for variant in variants & wanted:
                if root not in out[variant]:
                    out[variant].append(root)
    return out


def mentions_surface(
    root: str, surface: str, matches: dict[str, list[dict[str, Any]]]
) -> bool:
    form = fold_ar(surface)
    definite = "ال" + form
    for item in matches.get(root, []):
        source_id = LEX.canonical_source_id(str(item.get("source") or ""))
        if source_id not in {"lisan", "taj_al_arus"}:
            continue
        tokens = arabic_tokens(item.get("definition") or "")
        if form in tokens or definite in tokens:
            return True
    return False


def classify(
    rows: list[dict[str, Any]],
) -> tuple[dict[int, str], dict[str, list[dict[str, Any]]], dict[int, list[str]]]:
    wanted = {fold_ar(row.get("arabic_root")) for row in rows}
    morphology = build_morphology_index(wanted)
    roots = {LEX.normalize_root(row.get("arabic_root") or "") for row in rows}
    roots |= {root for values in morphology.values() for root in values}
    roots |= {root for root in OVERRIDES.values() if root}
    matches = LEX.matches_for_roots(ROOT / "Resources", roots, None)

    chosen: dict[int, str] = {}
    candidates_by_row: dict[int, list[str]] = {}
    for index, row in enumerate(rows):
        candidates: list[str] = []
        exact = LEX.normalize_root(row.get("arabic_root") or "")
        if exact:
            candidates.append(exact)
        for root in morphology.get(fold_ar(row.get("arabic_root")), []):
            if root not in candidates:
                candidates.append(root)
        eligible = []
        for root in candidates:
            works = source_work_ids(matches.get(root, []))
            if not ({"lisan", "taj_al_arus"} & works):
                continue
            if len(works) < 2:
                continue
            if mentions_surface(root, str(row.get("arabic_root") or ""), matches):
                eligible.append(root)
        candidates_by_row[index] = eligible

        if index in OVERRIDES:
            root = OVERRIDES[index]
            if root is None:
                continue
            works = source_work_ids(matches.get(root, []))
            if not ({"lisan", "taj_al_arus"} & works) or len(works) < 2:
                raise SystemExit(f"المادة اليدوية بلا شاهدين قديمين: {index} {root}")
            chosen[index] = root
            continue
        if not eligible:
            continue
        if len(eligible) > 1:
            raise SystemExit(f"مادة ملتبسة تحتاج قرارا يدويا: {index} {eligible}")
        chosen[index] = eligible[0]
    return chosen, matches, candidates_by_row


def quote_clause(definition: str, needles: tuple[str, ...]) -> str:
    text = one_line(definition)
    parts = [part.strip() for part in re.split(r"(?<=[.؟!؛])\s+", text) if part.strip()]
    folded_needles = tuple(fold_ar(value) for value in needles if value)
    for part in parts:
        folded = fold_ar(part)
        if any(needle and needle in folded for needle in folded_needles):
            return part
    return parts[0] if parts else text


def lexicon_witnesses(
    root: str, surface: str, matches: dict[str, list[dict[str, Any]]]
) -> list[dict[str, str]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in matches[root]:
        source_id = LEX.canonical_source_id(str(item.get("source") or ""))
        if source_id and str(item.get("definition") or "").strip():
            grouped[source_id].append(item)
    order = (
        "lisan", "taj_al_arus", "al_sihah", "al_muhkam", "kitab_al_ayn",
        "asas_al_balagha", "al_misbah", "al_muhit", "al_mufradat",
        "arabic_english",
    )
    picked: list[dict[str, str]] = []
    for source_id in order:
        if not grouped.get(source_id):
            continue
        item = max(grouped[source_id], key=lambda value: len(str(value.get("definition") or "")))
        picked.append({
            "source_id": source_id,
            "source": SOURCE_LABELS[source_id],
            "quote": quote_clause(str(item["definition"]), (surface, root)),
        })
        if len(picked) == 2:
            break
    if len(picked) < 2 or not ({"lisan", "taj_al_arus"} & {x["source_id"] for x in picked}):
        raise SystemExit(f"تعذر شاهدان مستقلان للمادة {root}")
    return picked


def old_archive(text: str) -> tuple[str, str]:
    if SOURCE_START in text and SOURCE_END in text:
        start = text.index(SOURCE_START)
        end = text.index(SOURCE_END, start) + len(SOURCE_END)
        return text[start:end], text[:start].rstrip() + "\n"
    if NEW_START in text and NEW_END in text:
        start = text.index(NEW_START)
        end = text.index(NEW_END, start) + len(NEW_END)
        base = text[:start].rstrip() + text[end:]
        if SURVIVALS.exists():
            stored = SURVIVALS.read_text(encoding="utf-8")
            a = stored.index(ARCHIVE_START) + len(ARCHIVE_START)
            b = stored.index(ARCHIVE_END, a)
            return stored[a:b].strip(), base.rstrip() + "\n"
    raise SystemExit("لم توجد كتل مقار القديمة ولا أرشيف سابق صالح")


def annotate_archive(archive: str, chosen: dict[int, str]) -> str:
    """ألحق بكل بطاقة قديمة سطر نسخ من غير تغيير شيء من نصها السابق."""
    prefix = f"- سطر النقل، {DATE}: نُقلت هذه البطاقة لأن طرفها العربي في نص مقّار لفظ عامي لا جذر قياس؛ رفع حكمها في هذا الموضع وبقي نصها القديم محفوظا."
    lines = archive.splitlines()
    out: list[str] = []
    seen: set[int] = set()
    index = 0
    while index < len(lines):
        line = lines[index]
        out.append(line)
        marker = re.fullmatch(r"<!-- MAQAR-COPTIC-\d{3}:(\d+) -->", line)
        if marker:
            row_index = int(marker.group(1))
            seen.add(row_index)
            already = index + 1 < len(lines) and lines[index + 1].startswith(prefix)
            if not already:
                if row_index in chosen:
                    tail = f" أعيدت بطاقة مستقلة في مسار القراءة على المادة الكلاسيكية `{chosen[row_index]}`."
                else:
                    tail = " لم تثبت لهذا اللفظ مادة كلاسيكية مسماة، فبقي في طبقة البقايا وحدها."
                out.append(prefix + tail)
        index += 1
    if seen != set(range(EXPECTED)):
        raise SystemExit(f"اختل جرد البطاقات المحفوظة عند إضافة سطور النقل: {len(seen)}")
    annotated = "\n".join(out)
    if annotated.count(prefix) != EXPECTED:
        raise SystemExit("لم يكتب سطر نقل واحد لكل بطاقة قديمة")
    return annotated


def compact_fan_tests(index: int, row: dict[str, Any]) -> str:
    skeleton = CARDS.candidate_fan("coptic", one_line(row.get("foreign")))[1]
    values = []
    orbit_spec = CARDS.COPTIC_ORBITS.get(index)
    for root in row["fan"]:
        sound = CARDS.sound_audit("coptic", skeleton, root)[0]
        event = bool(CARDS.event_for(root)[0])
        meaning = bool(orbit_spec and orbit_spec[0] == root)
        values.append(
            f"`{root}`[ص{'✓' if sound else '×'}،ح{'✓' if event else '×'}،"
            f"م{'✓' if meaning else '×'}]"
        )
    return "، ".join(values) or "(لم تولد الأداة مرشحا)"


def outcome_for(
    index: int, row: dict[str, Any], classical_root: str
) -> dict[str, Any]:
    skeleton = CARDS.candidate_fan("coptic", one_line(row.get("foreign")))[1]
    root_sound, root_rows, root_misses, root_alignment = CARDS.sound_audit(
        "coptic", skeleton, classical_root
    )
    root_event, _, root_event_source = CARDS.event_for(classical_root)
    nucleus, nucleus_reading = CARDS.our_nucleus(classical_root)
    nucleus_sound = False
    nucleus_rows: list[str] = []
    nucleus_misses: list[str] = []
    if nucleus:
        nucleus_sound, nucleus_rows, nucleus_misses, _ = CARDS.sound_audit(
            "coptic", skeleton, nucleus
        )

    old_orbit = CARDS.COPTIC_ORBITS.get(index)
    orbit = old_orbit[1] if old_orbit else ""
    root_positive = bool(
        index in POSITIVE_ROOTS and root_sound and root_event and orbit
    )
    nucleus_positive = bool(
        index in POSITIVE_NUCLEI and nucleus and nucleus_sound and nucleus_reading and orbit
    )
    return {
        "root_sound": root_sound,
        "root_rows": root_rows,
        "root_misses": root_misses,
        "root_alignment": root_alignment,
        "root_event": root_event,
        "root_event_source": root_event_source,
        "nucleus": nucleus,
        "nucleus_reading": nucleus_reading,
        "nucleus_sound": nucleus_sound,
        "nucleus_rows": nucleus_rows,
        "nucleus_misses": nucleus_misses,
        "orbit": orbit,
        "root_positive": root_positive,
        "nucleus_positive": nucleus_positive,
    }


def card_markdown(
    index: int,
    source_row: dict[str, Any],
    batch_row: dict[str, Any],
    classical_root: str,
    witnesses: list[dict[str, str]],
) -> tuple[str, dict[str, Any]]:
    result = outcome_for(index, source_row, classical_root)
    source_word = safe(source_row.get("arabic_root"))
    foreign = safe(source_row.get("foreign"))
    sense = safe(source_row.get("foreign_sense"))
    page = int(source_row.get("page") or 0)
    fan = "، ".join(f"`{safe(root)}`" for root in batch_row["fan"]) or "(فارغة)"
    tests = compact_fan_tests(index, batch_row)
    root_route = "؛ ".join(result["root_rows"]) or "؛ ".join(result["root_misses"]) or "لا مسار"
    nucleus_route = "؛ ".join(result["nucleus_rows"]) or "؛ ".join(result["nucleus_misses"]) or "لا مسار"
    if result["root_positive"]:
        root_verdict = "ROOT-TRACE"
    else:
        root_verdict = "OPEN-CANDIDATE؛ لم تجتمع الأرجل الثلاث في طبقة الجذر"
    if result["nucleus_positive"]:
        nucleus_verdict = "NUCLEUS-TRACE"
    else:
        nucleus_verdict = "OPEN-CANDIDATE؛ لم تجتمع الأرجل الثلاث في طبقة النواة"
    positives = [
        label for label, yes in (
            ("ROOT-TRACE", result["root_positive"]),
            ("NUCLEUS-TRACE", result["nucleus_positive"]),
        ) if yes
    ]
    final = " + ".join(positives) if positives else "**غير صادر (استكشاف)**"
    closure = "READY" if positives else "OPEN-CANDIDATE"
    required = (
        "لا عائق معلق"
        if positives
        else "مدار مكتوب يربط معنى الفرع بحدث المادة أو نواتها مع تمام مسار الصوت"
    )
    witness_lines = "\n".join(
        f"- شاهد المادة من {item['source']}: «{safe(item['quote'])}»."
        for item in witnesses
    )
    event = safe(result["root_event"]) or "(لا حدث معتمد لهذه المادة في السجل المجمد)"
    nucleus = result["nucleus"] or "(لا نواة مفهرسة)"
    nucleus_reading = safe(result["nucleus_reading"]) or "(لا قراءة نواة معتمدة)"
    orbit = safe(result["orbit"]) or "غير مكتوب؛ لا تولد الأداة مدارا من تقاطع الألفاظ"
    text = f"""### بطاقة: `{foreign}` «{sense}»؛ MAQAR-COPTIC-CLASSICAL/{index:03d}
<!-- MAQAR-COPTIC-CLASSICAL:{index} -->
- إصدار البروتوكول: RECOVERY-v2 (استكشاف).
- نسبة المصدر: اللفظ القبطي أو المصري ومعناه واللفظ العامي وشرحه من سامح مقّار، «أصل الألفاظ العامية من المصرية القديمة»؛ سامح مقّار مستقل عن علي فهمي خشيم. اتجاه مقّار مصري إلى عامي، وهو محفوظ في طبقة البقايا ولا يمنح حكما هنا.
- الكلمة في الفرع: `{foreign}`، والنطق المقروء تقريبا «{readable_pronunciation(str(source_row.get('foreign') or ''))}»؛ صفحة {page}.
- المعنى من قاموس الفرع: «{sense}» [سامح مقّار، بلا رتوش].
- اللفظ العامي عند مقّار: `{source_word}`؛ ليس جذرا، ولا يستعمل مرشحا حاكما.
- المادة العربية الكلاسيكية المستقلة: `{classical_root}`؛ أعيد توليدها من المعجمين لا من دعوى اتجاه مقّار.
{witness_lines}
- مروحة الصوت المثبتة قبل المعنى: {fan}.
- فحص المروحة كلها بالأرجل الثلاث: {tests}.
- مسار صوت المادة الكلاسيكية: {safe(root_route)}؛ المحاذاة: {safe(result['root_alignment'])}.
- حدث الجذر من السجل المجمد كما هو: «{event}» [{safe(result['root_event_source'])}].
- النواة المفهرسة للمادة: `{nucleus}` «{nucleus_reading}».
- مسار صوت النواة: {safe(nucleus_route)}.
- المدار المكتوب: {orbit}.
- المصفاة والاتجاه: دعوى مقّار بقاء مصري في العامية، أي اتجاهها معكوس عن دعوى المشروع؛ لا تدخل هذه الدعوى الحكم، والحكم إن صدر فبإعادة التوليد المستقلة وحدها.
- حكم طبقة الجذر: {root_verdict}.
- حكم طبقة النواة: {nucleus_verdict}.
- عائق: النوع={'READY' if positives else 'OPEN-CANDIDATE'}؛ يتطلب={required}
- حالة الإغلاق: {closure}
- الحكم (استكشاف): {final}
- سطر النسخ، {DATE}: الحكم القديم محفوظ بحروفه في `exploration/maqar-egyptian-survivals.md`؛ أعيدت هذه البطاقة على المادة الكلاسيكية `{classical_root}` لأن اللفظ العامي ليس جذر قياس.
"""
    return text, {**result, "positives": positives}


def build_reading_section(
    rows: list[dict[str, Any]],
    batch_rows: list[dict[str, Any]],
    chosen: dict[int, str],
    matches: dict[str, list[dict[str, Any]]],
) -> tuple[str, list[dict[str, Any]]]:
    cards: list[str] = []
    results: list[dict[str, Any]] = []
    for index in sorted(chosen):
        root = chosen[index]
        witnesses = lexicon_witnesses(root, str(rows[index].get("arabic_root") or ""), matches)
        text, outcome = card_markdown(index, rows[index], batch_rows[index], root, witnesses)
        cards.append(text)
        results.append({
            "index": index,
            "foreign": rows[index]["foreign"],
            "source_word": rows[index]["arabic_root"],
            "classical_root": root,
            "positive": outcome["positives"],
            "root_positive": outcome["root_positive"],
            "nucleus_positive": outcome["nucleus_positive"],
            "witnesses": witnesses,
        })
    survived = {item["index"] for item in results if item["positive"]} & PRIOR_POSITIVE
    if survived != PRIOR_POSITIVE:
        raise SystemExit(
            f"تغيرت مراجعة الأحكام القديمة: صمد {len(survived)} من {len(PRIOR_POSITIVE)}"
        )
    header = f"""
{NEW_START}
## إعادة توليد مادة مقّار ذات الجذر الكلاسيكي، {DATE}

**النطاق.** بقيت هنا {len(chosen)} بطاقة فقط من جرد مقّار. كل بطاقة تسمي مادة عربية كلاسيكية شهد لها لسان العرب أو تاج العروس ومعجم قديم مستقل ثان. أما صف مقّار نفسه فاتجاهه من المصرية إلى العامية، وهو محفوظ في `../exploration/maqar-egyptian-survivals.md` ولا يدخل عد الصلات.

**قانون الحكم.** الشروط ثلاثة لا رابع لها: مسار صوت مسمى، وحدث من السجل المجمد بلا تعديل، ومعنى الفرع بمدار كتبه القارئ. المروحة كلها تفحص، ولا يحتكر لفظ مقّار العامي الحكم. قاموس الإغلاق هو القاموس المغلق ذو 25 وسما.

**سطر النسخ الجامع، {DATE}.** نقلت البطاقات القديمة بحروفها إلى طبقة البقايا، ورفع حكمها هناك. أعيدت البطاقات أدناه من أولها على موادها الكلاسيكية؛ فالسجل القديم محفوظ، والحكم الحي هو آخر حكم في هذه الكتلة.

""".lstrip()
    return header + "\n".join(cards) + NEW_END + "\n", results


def build_survivals(
    rows: list[dict[str, Any]], chosen: dict[int, str], archive: str
) -> str:
    lines = [
        "# بقايا مصرية في العامية المصرية عند سامح مقّار",
        "",
        "**الحالة:** طبقة استكشاف مستقلة لمسار البقايا والاقتراض. **ليست هذه الأزواج صلات في دعوى المشروع، ولا يدخل شيء منها عد الصلات البتة.**",
        "",
        "**الاتجاه:** من المصرية القديمة أو القبطية إلى العامية المصرية الحية، وهو معكوس عن اتجاه الدعوى التي يختبرها المشروع. لذلك لا يستعمل اللفظ العامي هنا جذرا عربيا، ولا تتحول موافقة مقّار إلى حكم.",
        "",
        "**المصدر والنسبة:** سامح مقّار، «أصل الألفاظ العامية من اللغة المصرية القديمة». سامح مقّار مؤلف مستقل عن علي فهمي خشيم، ولا تخلط مادته بمادة خشيم ولا تنسب إحداهما إلى الآخر.",
        "",
        f"**الجرد:** {len(rows)} زوجا. بقي منها {len(chosen)} في مسار البطاقات بعد إعادة توليد مادة كلاسيكية مستقلة، وانتقل {len(rows) - len(chosen)} إلى هذه الطبقة وحدها. وجود الزوج في القسمين لا يخلط الاتجاهين: صف البقايا لا يعد، والبطاقة المستقلة وحدها تقرأ أدوات المشروع.",
        "",
        "النطق المقروء أدناه تقريب عربي للرومنة التي نقلها الجرد، لا استعادة صوتية مستقلة ولا IPA جديدا.",
        "",
        "| المعرّف | المصرية أو القبطية | النطق المقروء | معناها | اللفظ العامي عند مقّار | الصفحة | حال المسار المنضبط | سطر النقل |",
        "|---:|---|---|---|---|---:|---|---|",
    ]
    for index, row in enumerate(rows):
        if index in chosen:
            state = f"أعيدت بطاقة مستقلة على المادة `{chosen[index]}`"
            reason = f"{DATE}: حفظ صف البقايا وفصل اتجاهه، ولم يستعمل اللفظ العامي جذرا"
        else:
            state = "بقايا فقط، لا بطاقة صلة"
            reason = f"{DATE}: نقل لأن اللفظ العامي لم يثبت مادة كلاسيكية مسماة صالحة للقياس"
        lines.append(
            f"| {index} | `{safe(row.get('foreign'))}` | {readable_pronunciation(str(row.get('foreign') or ''))} | "
            f"{safe(row.get('foreign_sense'))} | {safe(row.get('arabic_root'))} | {int(row.get('page') or 0)} | {state} | {reason} |"
        )
    lines += [
        "",
        "## السجل القديم المحفوظ بحروفه",
        "",
        f"**سطر النسخ، {DATE}:** الكتل الآتية هي نص البطاقات السابق كما كتب، وقد نقلت من `readings/coptic.md` لأن وحدة الطرف العربي فيها لفظ عامي لا جذر. أحكامها القديمة منسوخة، والنص باق للتدقيق التاريخي ولا يعد من هذا الموضع.",
        "",
        ARCHIVE_START,
        archive.strip(),
        ARCHIVE_END,
        "",
        "---",
        "",
        "*English abstract.* This is an independent inventory of Egyptian survivals in living Egyptian colloquial speech as proposed by Sameh Maqar. Its direction runs from Egyptian or Coptic into colloquial Egyptian, the reverse of the project's claim. None of these rows is a project link or enters the link count. A row appears again in the disciplined reading lane only when an independent classical Arabic root is explicitly attested in Lisan al-Arab or Taj al-Arus and a second old lexicon; that regenerated card does not inherit Maqar's direction claim.",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    rows = load_rows()
    batch_rows = load_batch_rows()
    text = READING.read_text(encoding="utf-8")
    archive, base = old_archive(text)
    chosen, matches, candidates = classify(rows)
    archive = annotate_archive(archive, chosen)
    section, results = build_reading_section(rows, batch_rows, chosen, matches)
    survival_text = build_survivals(rows, chosen, archive)

    positive_rows = [item for item in results if item["positive"]]
    prior_survived = [item for item in positive_rows if item["index"] in PRIOR_POSITIVE]
    results_by_index = {item["index"]: item for item in results}
    prior_reviews = [
        {
            "index": index,
            "foreign": rows[index]["foreign"],
            "old_source_form": rows[index]["arabic_root"],
            "prior_layer": "root" if index in POSITIVE_ROOTS else "nucleus",
            "classical_root": chosen[index],
            "live_layer": "root" if results_by_index[index]["root_positive"] else "nucleus",
            "result": "survived",
        }
        for index in sorted(PRIOR_POSITIVE)
    ]
    moved = len(rows) - len(chosen)
    report = {
        "schema": "maqar-egyptian-survivals-separation-v1",
        "generated_by": "scripts/separate_maqar_egyptian_survivals.py",
        "date": DATE,
        "source_author": "سامح مقّار",
        "source_book": "أصل الألفاظ العامية من اللغة المصرية القديمة",
        "direction": "egyptian-or-coptic-to-egyptian-colloquial",
        "excluded_from_project_link_count": True,
        "source_pairs": len(rows),
        "survival_only_pairs": moved,
        "classical_cards_retained": len(chosen),
        "prior_positive_reviewed": len(PRIOR_POSITIVE),
        "prior_positive_survived": len(prior_survived),
        "prior_positive_reviews": prior_reviews,
        "live_positive_rows": len(positive_rows),
        "live_root_trace": sum(item["root_positive"] for item in results),
        "live_nucleus_trace": sum(item["nucleus_positive"] for item in results),
        "rows": [
            {
                "index": index,
                "foreign": row["foreign"],
                "pronunciation_ar": readable_pronunciation(str(row["foreign"])),
                "foreign_sense": row["foreign_sense"],
                "maqar_colloquial": row["arabic_root"],
                "page": row["page"],
                "lane": "classical-card-and-survival" if index in chosen else "survival-only",
                "classical_root": chosen.get(index),
                "dictionary_candidates": candidates.get(index, []),
            }
            for index, row in enumerate(rows)
        ],
    }
    review_table = "\n".join(
        f"| {item['index']} | `{safe(item['foreign'])}` | `{safe(item['old_source_form'])}` | "
        f"{item['prior_layer']} | `{item['classical_root']}` | {item['live_layer']} | صمد |"
        for item in prior_reviews
    )
    audit = f"""# فصل بقايا مقّار المصرية عن بطاقات الصلة القبطية

**التاريخ:** {DATE}. **الطبقة:** استكشاف.

فصل الجرد صف مقّار ذي الاتجاه المصري إلى العامي عن بطاقة المشروع ذات المادة العربية الكلاسيكية. كل الأزواج {len(rows)} محفوظة في طبقة البقايا ولا يدخل واحد منها العد من ذلك الموضع. انتقل {moved} زوجا إلى طبقة البقايا وحدها، وبقي {len(chosen)} في مسار البطاقات بعد إعادة توليده على مادة شهد لها لسان العرب أو تاج العروس ومعجم قديم مستقل ثان.

راجعت الأحكام الموجبة السابقة كلها، وعددها {len(PRIOR_POSITIVE)}. صمد منها {len(prior_survived)} بعد استبدال الرسم العامي أو الثنائي بالمادة الكلاسيكية المسماة مع حفظ الحكم القديم بحروفه. الحصيلة الحية في كتلة مقّار المعاد توليدها: {sum(item['root_positive'] for item in results)} حكم جذر و{sum(item['nucleus_positive'] for item in results)} حكم نواة.

| الصف | الفرع | الصورة القديمة | طبقتها | المادة الكلاسيكية | الطبقة الحية | المراجعة |
|---:|---|---|---|---|---|---|
{review_table}

الموجب لا يصدر إلا باجتماع الصوت ذي المسار المسمى، والحدث المجمد كما هو، ومعنى الفرع بمدار كتبه القارئ. لا شرط رابع. المروحة كلها مثبتة ومفحوصة، ومرشح المصدر لا يحتكر الحكم. لم يضف وسم إغلاق إلى القاموس المغلق.
"""

    SURVIVALS.parent.mkdir(parents=True, exist_ok=True)
    READING.write_text(
        unicodedata.normalize("NFC", base.rstrip() + "\n\n" + section),
        encoding="utf-8", newline="\n",
    )
    SURVIVALS.write_text(
        unicodedata.normalize("NFC", survival_text), encoding="utf-8", newline="\n"
    )
    REPORT.write_text(
        json.dumps(report, ensure_ascii=False, indent=1) + "\n",
        encoding="utf-8", newline="\n",
    )
    AUDIT.write_text(
        unicodedata.normalize("NFC", audit), encoding="utf-8", newline="\n"
    )
    print(
        f"pairs={len(rows)} survival_only={moved} retained={len(chosen)} "
        f"reviewed={len(PRIOR_POSITIVE)} survived={len(prior_survived)} "
        f"root={report['live_root_trace']} nucleus={report['live_nucleus_trace']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
