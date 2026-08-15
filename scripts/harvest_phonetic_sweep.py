# -*- coding: utf-8 -*-
"""حوّل المسح الصوتي اللاتيني كله إلى بطاقات استكشاف ذات ثلاث أرجل.

ترتيب العمل ثابت: 285 شهادة مباشرة نظيفة، ثم بقية مجتمع الصوت والمعنى
وعددها 131، ثم 3,000 صورة اجتمع لها الصوت وحده. قول قاموس الفرع في الأصل
حاشية معلوماتية لا بوابة. لا تنشئ الأداة موجبًا آليًا؛ كل موجب جديد له
مواصفة يدوية ومدار مكتوب بالكلمات في ``MANUAL_SPECS``.
"""
from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import asdict
import hashlib
import json
import mmap
import os
import re
import subprocess
import sys
import tempfile
import time
import types
import unicodedata
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import build_kaikki_index as KAIKKI  # noqa: E402
import count_links as COUNT  # noqa: E402
import fan_any_script as FAN  # noqa: E402
import frozen_event as EVENTS_ENGINE  # noqa: E402
import search_arabic_root_senses as ROOT_SENSES  # noqa: E402


DATE = "2026-08-15"
LANGUAGE = "latin"
SCRIPT = "latin"
EXPECTED_BOTH = 416
EXPECTED_DIRECT = 285
EXPECTED_REMAINDER = 131
EXPECTED_SOUND_ONLY = 3_000
EXPECTED_LATIN_LEXICON_ENTRIES = 47_919
BATCH_SIZE = 150
EXPECTED_BATCHES = 23
CONTROL_BASELINE = "1281ac5"

SWEEP = ROOT / "04-cross-linguistic" / "exploration" / "phonetic-sweep-latin.json"
READING = ROOT / "04-cross-linguistic" / "readings" / "old-latin.md"
PREPARATION = ROOT / "data" / "phonetic-sweep-latin-preparation.json"
EVENTS = ROOT / "data" / "phonetic-sweep-latin-events.jsonl"
WITNESS_GLOB = "phonetic-sweep-latin-root-witnesses-part-*.jsonl"
WITNESS_DISPLAY = "data/phonetic-sweep-latin-root-witnesses-part-*.jsonl"
SUMMARY = ROOT / "data" / "phonetic-sweep-latin-cards.json"
FINAL_AUDIT = ROOT / "05-audits" / f"{DATE}-phonetic-sweep-latin-cards-final.md"
GREEK_RESERVE = ROOT / "data" / "greek-borrowings-in-latin.json"
BLOCK_START = "<!-- PHONETIC-SWEEP-LATIN-CARDS:START -->"
BLOCK_END = "<!-- PHONETIC-SWEEP-LATIN-CARDS:END -->"

ENGLISH_TOKEN = re.compile(r"[a-z]+")
ENGLISH_STOP = {
    "a", "an", "and", "as", "at", "be", "by", "for", "from", "in", "into",
    "is", "it", "of", "on", "or", "that", "the", "this", "to", "up", "with",
    "been", "being", "can", "had", "has", "have", "having", "may", "one",
    "something", "thing", "used", "will", "active", "form", "indicative",
    "infinitive", "participle", "passive", "past", "perfect", "person",
    "plural", "present", "singular", "subjunctive",
}
GREEK_LEXICAL_SOURCE = re.compile(
    r"(?i)(?:\b(?:borrowed|derived|taken|translated|transliterated|loaned)\s+"
    r"(?:directly\s+)?from|\bfrom|\bvia)\s+(?:the\s+|a\s+)?"
    r"(?:(?:Ancient|Classical|Koine|Byzantine|Medieval|Modern|Doric|Attic|"
    r"scholarly)\s+)?Greek\b|\bof\s+(?:Ancient\s+|Classical\s+|Koine\s+)?"
    r"Greek\s+origin\b"
)
GREEK_TREE_SOURCE = re.compile(
    r"(?i)\b(?:Ancient|Classical|Koine|Byzantine|Medieval)\s+Greek\b"
    r".{0,120}\bbor\.\s+Latin\b"
)
GREEK_BORROWED_AS = re.compile(
    r"(?i)\bborrowed\s+from\s+(?:a\s+univerbated\s+form\s+of\s+|"
    r"or\s+formed\s+as\s+)(?:Ancient|Classical|Koine|Byzantine|Medieval)?"
    r"\s*Greek\b"
)

CONTROL_SPECS = [
    {"word": "trūdō", "root": "طرد", "closure": "ROOT-TRACE", "event_tier": 1},
    {"word": "cornū", "root": "قرن", "closure": "ROOT-TRACE", "event_tier": 1},
    {"word": "tinniō", "root": "طن", "closure": "FLOOR-TRACE", "event_tier": 4},
    {"word": "separo", "root": "صور", "closure": "ROOT-TRACE", "event_tier": 1},
    {"word": "abutor", "root": "بتر", "closure": "ROOT-TRACE", "event_tier": 1},
    {"word": "tergeo", "root": "ترك", "closure": "ROOT-TRACE", "event_tier": 1},
]


# المفتاح هو (صورة الفرع، أفضل جذر في صف المسح)، حتى لا تختلط صور مكررة.
# الشواهد الكاملة لكل جذر تبقى في السجل؛ needles لاختيار مقتطفين مسميين فقط.
MANUAL_SPECS: dict[tuple[str, str], dict[str, Any]] = {
    ("frico", "فرك"): {
        "root": "فرك", "event_tier": 3,
        "orbit": (
            "الفرك والدلك حركة متكررة تفصل ما علق بالسطح أو تنزع القشر عن اللب؛ "
            "فمعنى rub وchafe في اللاتينية يلتقي فعل العربية الحسي وحدث الفصل "
            "في النواة، لا مجرد لفظ عام"
        ),
        "needles": ("دَلْكُ الشيء", "دَلْك الشَّيْء"),
    },
    ("repudio", "رفض"): {
        "root": "رفض", "event_tier": 4,
        "orbit": (
            "رفض الشيء إخراجه من القبول وتركه متفرقًا خارج الحوزة؛ فـreject وcast off "
            "في اللاتينية هما الترك والإبعاد اللذان تنص عليهما العربية، وتؤلف محاكم "
            "الحروف حركة الانفراج والخروج المبعَد"
        ),
        "needles": ("الرَّفْضُ: تركُكَ الشيءَ", "الرَفْضُ: التركُ"),
    },
    ("incido", "نقض"): {
        "root": "نقض", "event_tier": 1,
        "orbit": (
            "القطع إلى داخل الشيء يشق اتصال أجزائه ويفك ما كان قوي الارتباط؛ "
            "فـcut open وsever صورة حسية مباشرة لتفكك البنية في حدث النقض"
        ),
        "needles": ("نَقْض البناء وهو هَدْمُه", "البِناء المَنْقُوضِ إِذا هُدم"),
    },
    ("nobilis", "نبل"): {
        "root": "نبل", "event_tier": 3,
        "orbit": (
            "النبالة وعلو المنزلة إخراج لصاحبها فوق الرتبة المعتادة وإبانة له "
            "عن نظائره؛ فدلالة النبل والاشتهار في الصورة اللاتينية تحقق ارتفاع "
            "الشيء وابتعاده في الحدث المجمّد، لا مجرد صفة عامة للحسن"
        ),
        "needles": ("الذكاء والنجابة", "رجل نبيل"),
    },
    ("tumulo", "طمر"): {
        "root": "طمر", "event_tier": 3,
        "orbit": (
            "ردم الجسد بتكويم التراب عليه يملأ الموضع ويغطي المدفون حتى يخفيه؛ "
            "فالتغطية بالتل والدفن في المعنى اللاتيني صورة حسية مباشرة لحدث الطمر"
        ),
        "needles": ("المطمورة", "طمر نفسه ومتاعه"),
    },
    ("cooperio", "كفر"): {
        "root": "كفر", "event_tier": 1,
        "orbit": (
            "التغطية الكلية التي لا تدع المغطى ظاهرًا هي نفس الفعل الذي تسميه "
            "الصورة اللاتينية حين تغطي الشيء كله أو تغمره؛ فاتحد الفعل الحسي في الطرفين"
        ),
        "needles": ("غطاه", "يستر ما تحته"),
    },
    ("inquiro", "نقر"): {
        "root": "نقر", "event_tier": 1,
        "orbit": (
            "البحث ينقر الخبر جزءًا دقيقًا بعد جزء ليستخرج خفيه، كما يقلع النقر "
            "من ظاهر الصلب جزءًا صغيرًا ويبقي أثره؛ وقد سمى الشاهد العربي هذا الامتداد نفسه بحثًا"
        ),
        "needles": ("بحثت", "بحث"),
    },
    ("glubo", "كرب"): {
        "root": "كرب", "event_tier": 1,
        "orbit": (
            "تقشير اللحاء ينزع الغطاء الكثيف الملتصق الذي يلي الأصل ويكشف ما تحته؛ "
            "وأصول السعف المسماة كربًا شاهد حسي على هذا الغطاء القريب الكثيف"
        ),
        "needles": ("أصول سعفها", "أصل السعفة"),
    },
    ("incisio", "نقش"): {
        "root": "نقش", "event_tier": 3,
        "orbit": (
            "الشق المادي يقطع في السطح فينشئ فيه فراغًا غائرًا وأثرًا نافذًا؛ "
            "وهذا هو وجه النقش والنقر بالآلة، لا معنى الوقفة العروضية الآخر"
        ),
        "needles": ("نقرها", "بالمنقاش"),
    },
    ("necesse", "نقص"): {
        "root": "نقص", "event_tier": 1,
        "orbit": (
            "الحاجة إلى الشيء تعرف من نقصه: إذا ذهب الجزء اللازم اختل المجموع "
            "فصار ذلك الجزء ضروريًا؛ فالمعنى اللاتيني ينتقل خطوة واحدة من النقص إلى ما لا يستغنى عنه"
        ),
        "needles": ("أعوزه", "احتاج"),
    },
    ("caesim", "قسم"): {
        "root": "قسم", "event_tier": 1,
        "orbit": (
            "القطع بحد الآلة يفصل الكل إلى أجزاء متميزة؛ فهو الأداة الحسية لفعل "
            "القسم الذي يجزئ الشيء ويفرز أنصباءه"
        ),
        "needles": ("جزأه", "إفراز النصيب"),
    },
}


def clean(value: Any) -> str:
    return " ".join(str(value or "").split()).replace("`", "ˋ").replace("—", "؛")


def latin_key(value: Any) -> str:
    text = unicodedata.normalize("NFD", str(value or "").casefold())
    return "".join(char for char in text if not unicodedata.combining(char) and char.isalpha())


def unique(values: Iterable[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))


def atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def atomic_write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            for row in rows:
                handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def atomic_write_split_jsonl(
    rows: Iterable[dict[str, Any]], max_bytes: int = 80_000_000
) -> list[Path]:
    data_dir = ROOT / "data"
    paths: list[Path] = []
    handle = None
    temporary = ""
    size = 0
    part = 0

    def open_part() -> tuple[Any, str, Path]:
        nonlocal part
        part += 1
        path = data_dir / f"phonetic-sweep-latin-root-witnesses-part-{part:03d}.jsonl"
        fd, temp_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=data_dir)
        return os.fdopen(fd, "w", encoding="utf-8", newline="\n"), temp_name, path

    try:
        for row in rows:
            line = json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n"
            encoded_size = len(line.encode("utf-8"))
            if handle is None or (size and size + encoded_size > max_bytes):
                if handle is not None:
                    handle.close()
                    os.replace(temporary, paths[-1])
                handle, temporary, path = open_part()
                paths.append(path)
                size = 0
            handle.write(line)
            size += encoded_size
        if handle is not None:
            handle.close()
            handle = None
            os.replace(temporary, paths[-1])
    finally:
        if handle is not None:
            handle.close()
        if temporary and os.path.exists(temporary):
            os.unlink(temporary)

    keep = set(paths)
    for stale in data_dir.glob(WITNESS_GLOB):
        if stale not in keep:
            stale.unlink()
    return paths


def sweep_hash() -> str:
    return hashlib.sha256(SWEEP.read_bytes()).hexdigest()


def load_sweep() -> dict[str, Any]:
    payload = json.loads(SWEEP.read_text(encoding="utf-8"))
    both = payload.get("both") or []
    sound_only = payload.get("sound_only") or []
    direct = [row for row in both if row.get("direct") and not row.get("loan_suspect")]
    remainder = [row for row in both if row not in direct]
    if payload.get("language") != LANGUAGE:
        raise AssertionError("اختلط لسان المسح؛ المطلوب latin")
    if (len(both), len(direct), len(remainder), len(sound_only)) != (
        EXPECTED_BOTH, EXPECTED_DIRECT, EXPECTED_REMAINDER, EXPECTED_SOUND_ONLY
    ):
        raise AssertionError(
            f"حدود المسح تغيرت: both={len(both)} direct={len(direct)} "
            f"remainder={len(remainder)} sound={len(sound_only)}"
        )
    return payload


def source_windows() -> list[list[dict[str, Any]]]:
    payload = load_sweep()
    both = list(payload["both"])
    direct_rows = [row for row in both if row.get("direct") and not row.get("loan_suspect")]
    remainder_rows = [row for row in both if row not in direct_rows]
    sound_rows = list(payload["sound_only"])

    both_rank = {id(row): rank for rank, row in enumerate(both, 1)}
    sound_rank = {id(row): rank for rank, row in enumerate(sound_rows, 1)}

    def decorate(rows: list[dict[str, Any]], phase: str) -> list[dict[str, Any]]:
        output = []
        for phase_rank, source in enumerate(rows, 1):
            row = dict(source)
            row["phase"] = phase
            row["phase_rank"] = phase_rank
            row["source_rank"] = (
                sound_rank[id(source)] if phase == "sound-only" else both_rank[id(source)]
            )
            output.append(row)
        return output

    direct = decorate(direct_rows, "direct-meaning")
    remainder = decorate(remainder_rows, "meaning-remainder")
    sound = decorate(sound_rows, "sound-only")
    windows = [direct[:BATCH_SIZE], direct[BATCH_SIZE:], remainder]
    windows.extend(sound[offset : offset + BATCH_SIZE] for offset in range(0, len(sound), BATCH_SIZE))
    if len(windows) != EXPECTED_BATCHES or any(not window for window in windows):
        raise AssertionError(f"تقسيم الدفعات ليس {EXPECTED_BATCHES}")
    flattened = [row for window in windows for row in window]
    for global_rank, row in enumerate(flattened, 1):
        row["global_rank"] = global_rank
    for batch, window in enumerate(windows, 1):
        for row in window:
            row["batch"] = batch
    return windows


def baseline_fan_module() -> types.ModuleType:
    source = subprocess.run(
        ["git", "show", f"{CONTROL_BASELINE}:scripts/fan_any_script.py"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    ).stdout
    module = types.ModuleType("fan_any_script_baseline")
    exec(compile(source, "fan_any_script_baseline", "exec"), module.__dict__)
    return module


def control_run() -> list[dict[str, Any]]:
    old = baseline_fan_module()
    results: list[dict[str, Any]] = []
    for spec in CONTROL_SPECS:
        before = set(old.fan(spec["word"], SCRIPT))
        after = set(FAN.fan(spec["word"], SCRIPT))
        lost = sorted(before - after)
        gained = sorted(after - before)
        if lost:
            raise AssertionError(
                f"يقف الحصاد: {spec['word']} a-b={lost}؛ b-a={gained}"
            )
        event = EVENTS_ENGINE.resolve(spec["root"], tier=int(spec["event_tier"]))
        if event is None:
            raise AssertionError(
                f"يقف الحصاد: درجة الحدث المعلنة غائبة في {spec['word']}"
            )
        results.append({
            **spec,
            "baseline": CONTROL_BASELINE,
            "old_count": len(before),
            "new_count": len(after),
            "a_minus_b": lost,
            "b_minus_a": gained,
            "event_available_at_declared_tier": True,
            "event_text": event.text,
        })
    return results


def prior_issued_forms(words: set[str]) -> dict[str, list[dict[str, Any]]]:
    wanted = {latin_key(word) for word in words}
    found: dict[str, list[dict[str, Any]]] = {}
    before = (READING.stat().st_size, READING.stat().st_mtime_ns)
    latin_letters = "A-Za-zÀ-ÖØ-öø-ÿĀ-žḀ-ỿ"
    for heading, degrees, _family in COUNT.scan_path(READING):
        if not degrees:
            continue
        tokens = {
            latin_key(token)
            for token in re.findall(rf"[{latin_letters}]+", heading)
            if latin_key(token)
        }
        for token in tokens & wanted:
            rows = found.setdefault(token, [])
            item = {"heading": clean(heading), "closures": sorted(degrees)}
            if item not in rows:
                rows.append(item)
    after = (READING.stat().st_size, READING.stat().st_mtime_ns)
    if before != after:
        raise AssertionError("تغير ملف القراءة أثناء جرد الصلات الحية؛ أوقف التحضير")
    return found


def fan_record(word: str) -> dict[str, Any]:
    base = FAN.fan(word, SCRIPT)
    unlimited = FAN.fan(word, SCRIPT, limit=1_000_000)
    if base != unlimited:
        raise AssertionError(f"المروحة الافتراضية مقتطعة في {word}")
    if not base:
        raise AssertionError(f"الصورة بلا مروحة: {word}")
    return {
        "call": f"fan_any_script.fan({word!r}, 'latin')",
        "limit": None,
        "complete": True,
        "count": len(base),
        "roots": base,
    }


def english_tokens(value: Any) -> set[str]:
    return {
        token for token in ENGLISH_TOKEN.findall(str(value or "").casefold())
        if len(token) > 2 and token not in ENGLISH_STOP
    }


def select_dictionary_entry(
    entries: list[dict[str, str]], word: str, sweep_gloss: str, route: str
) -> tuple[dict[str, str] | None, list[dict[str, str]]]:
    """انتخب المدخلة التي استعملها صف المسح بعد قراءة جميع المنافسات."""
    if not entries:
        return None, []
    wanted = english_tokens(sweep_gloss)
    ranked: list[tuple[tuple[int, int, int, int], int, dict[str, str]]] = []
    for index, entry in enumerate(entries):
        meaning = str(entry.get("en") or "")
        overlap = len(wanted & english_tokens(meaning))
        folded_gloss = clean(sweep_gloss).casefold()
        folded_meaning = meaning.casefold()
        phrase = int(
            bool(folded_gloss and folded_meaning)
            and (folded_gloss in folded_meaning or folded_meaning in folded_gloss)
        )
        exact = int(
            latin_key(entry.get("word")) == latin_key(word)
            or (
                bool(entry.get("read"))
                and latin_key(entry.get("read")) == latin_key(word)
            )
        )
        ranked.append(((phrase, overlap, exact, -index), index, entry))
    ranked.sort(reverse=True, key=lambda item: item[0])
    best_score, _best_index, selected = ranked[0]
    # في طريق الهيكل لا تكفي المشابهة الصوتية لادعاء معنى قاموسي. لا ننتخب
    # مدخلة إلا إذا وصلها معنى صف المسح بمعنى مسمى واحد على الأقل.
    if route != "الصورةُ بنصِّها" and not (best_score[0] or best_score[1]):
        return None, []
    competitors = [
        entry for score, _index, entry in ranked[1:]
        if (score[0] or score[1]) and score[:2] == best_score[:2]
    ][:2]
    return selected, competitors


def has_greek_lexical_source(etymology: str) -> bool:
    """قولٌ صريح بمسار يوناني، لا مجرد مقارنة أو اسم نظير يوناني."""
    return bool(
        GREEK_LEXICAL_SOURCE.search(etymology)
        or GREEK_TREE_SOURCE.search(etymology)
        or GREEK_BORROWED_AS.search(etymology)
    )


def dictionary_record(word: str, sweep_gloss: str, sweep_say: str) -> dict[str, Any]:
    entries, how = KAIKKI.look(LANGUAGE, word)
    cleaned = [
        {
            "word": clean(entry.get("word")),
            "read": clean(entry.get("read")),
            "pos": clean(entry.get("pos")),
            "en": clean(entry.get("en")),
            "etym": clean(entry.get("etym")),
        }
        for entry in entries
    ]
    selected, competitors = select_dictionary_entry(cleaned, word, sweep_gloss, clean(how))
    selected = selected or {}
    meaning = clean(selected.get("en"))
    origin = clean(selected.get("etym"))
    reads = unique(entry["read"] for entry in cleaned if entry["read"])
    donor_pattern = re.compile(
        r"(?i)\b(?:from|borrowed from|via)\b[^.]{0,120}\b"
        r"(?:arabic|hebrew|aramaic|syriac|akkadian|phoenician|punic|semitic)\b"
    )
    donor_claims = [origin] if origin and donor_pattern.search(origin) else []
    return {
        "call": f"build_kaikki_index.look('latin', {word!r})",
        "lookup_route": clean(how),
        "lexicon_population": EXPECTED_LATIN_LEXICON_ENTRIES,
        "entries_read_count": len(cleaned),
        "selected_entry": selected or None,
        "useful_competitors": competitors,
        "meaning": (
            meaning if meaning
            else "لم تُنتخب مدخلة قاموسية لهذه الصورة بعد قراءة جميع المداخل المسترجعة"
        ),
        "dictionary_meaning_found": bool(meaning),
        "meaning_fallback_to_sweep": False,
        "sweep_gloss_context": clean(sweep_gloss),
        "romanization": clean(sweep_say) or (reads[0] if reads else clean(word)),
        "ما يقولُه قاموسُ الفرعِ عن الأصل": (
            origin if origin else "لم تطبع المدخلة المختارة قولًا في الأصل"
        ),
        "named_semitic_donor_claims": donor_claims,
        "greek_origin_published": origin if has_greek_lexical_source(origin) else "",
        "greek_redirect": has_greek_lexical_source(origin),
        "greek_reserve": GREEK_RESERVE.relative_to(ROOT).as_posix(),
        "origin_is_informational_only": True,
        "origin_excluded_card": False,
    }


def witness_excerpt(definition: str, needle: str, radius: int = 260) -> str:
    text = clean(definition)
    position = text.find(needle)
    if position < 0:
        return text[: radius * 2]
    start = max(0, position - radius)
    end = min(len(text), position + len(needle) + radius)
    return text[start:end].strip()


def select_manual_witnesses(
    root: str,
    needles: tuple[str, ...],
    matches: dict[str, list[dict[str, Any]]],
) -> list[dict[str, str]]:
    candidates = matches.get(root) or []
    chosen: list[dict[str, str]] = []
    used: set[str] = set()
    for needle in needles:
        ranked = []
        for item in candidates:
            definition = clean(item.get("definition"))
            if needle not in definition:
                continue
            source_id = ROOT_SENSES.canonical_source_id(str(item.get("source") or ""))
            if not source_id or source_id in used:
                continue
            try:
                priority = ROOT_SENSES.SOURCE_PRIORITY.index(source_id)
            except ValueError:
                priority = len(ROOT_SENSES.SOURCE_PRIORITY)
            ranked.append((priority, item, source_id))
        if not ranked:
            continue
        _priority, item, source_id = min(ranked, key=lambda value: value[0])
        used.add(source_id)
        chosen.append({
            "source_id": source_id,
            "source": ROOT_SENSES.SOURCE_LABELS[source_id],
            "quote": witness_excerpt(str(item.get("definition") or ""), needle),
            "url": clean(item.get("url")),
        })
    if len(chosen) < 2:
        fan = ROOT_SENSES.independent_fan(candidates)
        for item in fan.get("selected_sources") or []:
            source_id = str(item.get("source_id") or "")
            if not source_id or source_id in used:
                continue
            chosen.append({
                "source_id": source_id,
                "source": str(item.get("source_label") or source_id),
                "quote": witness_excerpt(str(item.get("definition") or ""), ""),
                "url": clean(item.get("url")),
            })
            used.add(source_id)
            if len(chosen) == 2:
                break
    if len(chosen) < 2:
        raise AssertionError(f"لم يكتمل شاهدان مستقلان للموجب {root}")
    return chosen[:2]


def compact_independent_fan(matches: list[dict[str, Any]]) -> dict[str, Any]:
    fan = ROOT_SENSES.independent_fan(matches)
    fan["selected_sources"] = [
        {
            key: value
            for key, value in item.items()
            if key not in {"definition", "definition_truncated"}
        }
        for item in fan.get("selected_sources") or []
    ]
    return fan


def closure_for(root: str) -> str:
    return "NUCLEUS-TRACE" if len(re.findall(r"[ء-ي]", root)) == 2 else "ROOT-TRACE"


def card_id(row: dict[str, Any]) -> str:
    labels = {
        "direct-meaning": "DIRECT",
        "meaning-remainder": "MEANING",
        "sound-only": "SOUND",
    }
    return f"PS-LATIN-{labels[row['phase']]}-{int(row['phase_rank']):05d}"


def manual_spec(row: dict[str, Any]) -> dict[str, Any] | None:
    if row["phase"] == "sound-only":
        return None
    return MANUAL_SPECS.get((str(row["branch"]), str(row["best"])))


def comparison_row(
    source: dict[str, Any],
    preparation: dict[str, Any],
    manual_matches: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    word = str(source["branch"])
    fan = fan_record(word)
    dictionary = dictionary_record(word, str(source.get("gloss") or ""), str(source.get("say") or word))
    prior = (preparation.get("prior_issued") or {}).get(latin_key(word), [])
    spec = manual_spec(source)
    selection = None
    protected = bool(prior)
    greek_redirect = bool(dictionary.get("greek_redirect"))

    if protected:
        existing = unique(
            closure
            for item in prior
            for closure in item.get("closures") or []
        )
        closure = existing[0] if existing else "OPEN-CANDIDATE"
        state = "PROTECTED-S8"
        counted_link = False
    elif greek_redirect:
        closure = "OPEN-CANDIDATE"
        state = "GREEK-REDIRECT"
        counted_link = False
    elif spec:
        if not dictionary.get("dictionary_meaning_found"):
            raise AssertionError(f"الموجب اليدوي بلا مدخلة قاموسية منتخبة: {word}")
        root = str(spec["root"])
        if root not in fan["roots"]:
            raise AssertionError(f"الجذر اليدوي {root} خارج مروحة {word}")
        all_tiers = EVENTS_ENGINE.all_tiers(root)
        event = next(
            (item for item in all_tiers if item.tier == int(spec["event_tier"])),
            None,
        )
        if event is None:
            raise AssertionError(f"درجة الحدث اليدوية غائبة: {word} {root}")
        witnesses = select_manual_witnesses(root, tuple(spec["needles"]), manual_matches)
        selection = {
            "root": root,
            "event_tier": int(spec["event_tier"]),
            "event": asdict(event),
            "witnesses": witnesses,
            "orbit": str(spec["orbit"]),
            "orbit_written_by_hand": True,
        }
        closure = closure_for(root)
        state = "NEW-TRACE"
        counted_link = True
    else:
        closure = "OPEN-CANDIDATE"
        state = "OPEN-CANDIDATE"
        counted_link = False

    return {
        "card_id": card_id(source),
        "batch": int(source["batch"]),
        "global_rank": int(source["global_rank"]),
        "phase": source["phase"],
        "phase_rank": int(source["phase_rank"]),
        "source_rank": int(source["source_rank"]),
        "word": clean(word),
        "romanization": dictionary["romanization"],
        "script": SCRIPT,
        "sweep": {
            "skeleton": clean(source.get("skeleton")),
            "gloss": clean(source.get("gloss")),
            "best": clean(source.get("best")),
            "overlap": int(source.get("overlap") or 0),
            "shared": [clean(value) for value in source.get("shared") or []],
            "direct": bool(source.get("direct")),
            "loan_suspect": bool(source.get("loan_suspect")),
            "candidates_found": [clean(value) for value in source.get("candidates_found") or []],
        },
        "fan": fan,
        "event_call": "frozen_event.all_tiers(root)",
        "event_catalog_roots": fan["roots"],
        "event_catalog": EVENTS.relative_to(ROOT).as_posix(),
        "dictionary": dictionary,
        "root_witness_call": "search_arabic_root_senses.py ROOT --max-chars 0",
        "root_witness_catalog_roots": fan["roots"],
        "root_witness_catalog": WITNESS_DISPLAY,
        "root_witness_max_chars": 0,
        "definitions_truncated": False,
        "three_legs_complete": True,
        "origin_is_gate": False,
        "origin_excluded_card": False,
        "greek_redirect": greek_redirect,
        "excluded_from_latin_count": greek_redirect,
        "protected_live_link": protected,
        "prior_issued": prior,
        "state": state,
        "closure": closure,
        "counted_new_link": counted_link,
        "manual_selection": selection,
    }


def batch_path(batch: int) -> Path:
    return ROOT / "data" / f"phonetic-sweep-latin-cards-batch-{batch:03d}.json"


def batch_audit_path(batch: int) -> Path:
    return ROOT / "05-audits" / f"{DATE}-phonetic-sweep-latin-cards-batch-{batch:03d}.md"


def delete_superseded_files() -> int:
    stale_paths = [
        *sorted((ROOT / "data").glob("phonetic-sweep-latin-harvest-batch-*.json")),
        *sorted((ROOT / "05-audits").glob(f"{DATE}-phonetic-sweep-latin-harvest-batch-*.md")),
        ROOT / "04-cross-linguistic" / "exploration" / "phonetic-sweep-latin-triage.json",
        ROOT / "04-cross-linguistic" / "exploration" / "phonetic-sweep-latin-triage.md",
    ]
    removed = 0
    for path in stale_paths:
        if path.exists():
            path.unlink()
            removed += 1
    return removed


def install_pending_clean() -> None:
    candidates = sorted(
        READING.parent.glob(READING.name + ".*.tmp"),
        key=lambda path: path.stat().st_mtime_ns,
        reverse=True,
    )
    if not candidates:
        raise AssertionError("لا نسخة تنظيف معلقة")
    pending = candidates[0]
    expected = (READING.stat().st_size, READING.stat().st_mtime_ns)
    with pending.open("rb") as handle, mmap.mmap(
        handle.fileno(), 0, access=mmap.ACCESS_READ
    ) as mapped:
        if mapped.find(b"PHONETIC-SWEEP-LATIN-BATCH-") >= 0:
            raise AssertionError("النسخة المعلقة ما زالت تحمل كتل المولد المنسوخ")
        if len(mapped) >= expected[0]:
            raise AssertionError("النسخة المعلقة لا تبدو ناتج رفع الكتل")

    deadline = time.time() + 7_200
    while True:
        current = (READING.stat().st_size, READING.stat().st_mtime_ns)
        if current != expected:
            raise AssertionError("تغير أصل القراءة بعد بناء النسخة المعلقة")
        try:
            os.replace(pending, READING)
            break
        except FileNotFoundError:
            with READING.open("rb") as handle, mmap.mmap(
                handle.fileno(), 0, access=mmap.ACCESS_READ
            ) as mapped:
                if mapped.find(b"PHONETIC-SWEEP-LATIN-BATCH-") < 0:
                    break
            raise
        except PermissionError:
            if time.time() >= deadline:
                raise
            time.sleep(0.01)
    removed = delete_superseded_files()
    print(f"INSTALLED: pending clean reading; removed {removed} superseded files")


def cleanup_superseded() -> None:
    """ارفع مخرجات المولد المنسوخ التي جعلت خبر الأصل بوابة حكم."""
    intervals: list[tuple[int, int]] = []
    before = (READING.stat().st_size, READING.stat().st_mtime_ns)
    with READING.open("rb") as source, mmap.mmap(
        source.fileno(), 0, access=mmap.ACCESS_READ
    ) as mapped:
        prefix = b"<!-- PHONETIC-SWEEP-LATIN-BATCH-"
        position = 0
        while True:
            start = mapped.find(prefix, position)
            if start < 0:
                break
            token_end = mapped.find(b" -->", start)
            if token_end < 0:
                raise AssertionError("علامة كتلة منسوخة بلا إغلاق")
            start_token = mapped[start : token_end + 4]
            if b":START -->" not in start_token:
                position = token_end + 4
                continue
            end_token = start_token.replace(b":START -->", b":END -->")
            end = mapped.find(end_token, start)
            if end < 0:
                raise AssertionError(f"كتلة منسوخة بلا نهاية: {start_token!r}")
            intervals.append((start, end + len(end_token)))
            position = end + len(end_token)

        if intervals:
            fd, temporary = tempfile.mkstemp(
                prefix=READING.name + ".", suffix=".tmp", dir=READING.parent
            )
            try:
                with os.fdopen(fd, "wb") as output:
                    position = 0
                    for start, end in sorted(intervals):
                        while position < start:
                            chunk = mapped[position : min(start, position + 8 * 1024 * 1024)]
                            output.write(chunk)
                            position += len(chunk)
                        position = end
                    while position < len(mapped):
                        chunk = mapped[position : min(len(mapped), position + 8 * 1024 * 1024)]
                        output.write(chunk)
                        position += len(chunk)
                current = (READING.stat().st_size, READING.stat().st_mtime_ns)
                if current != before:
                    raise AssertionError("تغير ملف القراءة أثناء رفع الكتل المنسوخة")
                deadline = time.time() + 7_200
                while True:
                    try:
                        os.replace(temporary, READING)
                        break
                    except PermissionError:
                        if time.time() >= deadline:
                            raise
                        time.sleep(1)
            finally:
                if os.path.exists(temporary):
                    os.unlink(temporary)

    removed = delete_superseded_files()
    print(f"CLEANUP: removed {len(intervals)} superseded reading blocks and {removed} files")


def prepare() -> None:
    controls = control_run()
    lexicon_population = len((KAIKKI.lexicon(LANGUAGE).get("entries") or []))
    if lexicon_population != EXPECTED_LATIN_LEXICON_ENTRIES:
        raise AssertionError(
            f"تغير سكان القاموس اللاتيني: {lexicon_population}"
        )
    windows = source_windows()
    rows = [row for window in windows for row in window]
    roots = unique(
        root
        for row in rows
        for root in FAN.fan(str(row["branch"]), SCRIPT)
    )
    if any(not EVENTS_ENGINE.all_tiers(root) for root in roots):
        raise AssertionError("ظهر جذر مرشح بلا درجة حدث")

    words = {str(row["branch"]) for row in rows}
    prior = prior_issued_forms(words)
    matches = ROOT_SENSES.matches_for_roots(ROOT_SENSES.DEFAULT_RESOURCES, set(roots), None)
    if any(
        item.get("definition_truncated")
        for values in matches.values()
        for item in values
    ):
        raise AssertionError("ظهر شاهد مقطوع مع --max-chars 0")

    atomic_write_jsonl(
        EVENTS,
        (
            {
                "root": root,
                "call": f"frozen_event.all_tiers({root!r})",
                "all_tiers": [asdict(event) for event in EVENTS_ENGINE.all_tiers(root)],
            }
            for root in sorted(roots)
        ),
    )
    witness_paths = atomic_write_split_jsonl(
        (
            {
                "root": root,
                "call": f"python scripts/search_arabic_root_senses.py {root} --max-chars 0",
                "max_chars": 0,
                "definitions_truncated": False,
                "independent_fan": compact_independent_fan(matches.get(root) or []),
                "matches": matches.get(root) or [],
            }
            for root in sorted(roots)
        )
    )
    counts = {
        "sound_and_meaning": EXPECTED_BOTH,
        "direct_meaning": EXPECTED_DIRECT,
        "meaning_remainder": EXPECTED_REMAINDER,
        "sound_only_waiting": EXPECTED_SOUND_ONLY,
        "cards": len(rows),
        "batches": len(windows),
        "unique_candidate_roots": len(roots),
        "roots_with_lexicographic_witnesses": sum(bool(matches.get(root)) for root in roots),
        "full_lexicographic_witness_records": sum(len(matches.get(root) or []) for root in roots),
        "prior_issued_forms": len(prior),
        "latin_lexicon_entries": lexicon_population,
    }
    payload = {
        "schema": "phonetic-sweep-latin-preparation-v1",
        "date": DATE,
        "language": LANGUAGE,
        "script": SCRIPT,
        "sweep_sha256": sweep_hash(),
        "counts": counts,
        "controls": controls,
        "a_minus_b_nonempty": sum(bool(item["a_minus_b"]) for item in controls),
        "law": {
            "fan_call": "fan_any_script.fan(w, 'latin')",
            "all_event_tiers": True,
            "dictionary_call": "build_kaikki_index.look('latin', w)",
            "root_witness_max_chars": 0,
            "origin_is_information_only": True,
            "greek_origin_routes_to_greek_reserve": True,
            "sound_only_is_waiting_not_rejected": True,
            "live_outbound_links_untouched": True,
            "manual_positive_orbits_only": True,
        },
        "prior_issued": prior,
        "files": {
            "events": EVENTS.relative_to(ROOT).as_posix(),
            "root_witnesses": WITNESS_DISPLAY,
            "root_witness_parts": len(witness_paths),
            "batches": "data/phonetic-sweep-latin-cards-batch-*.json",
        },
    }
    atomic_write(PREPARATION, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    print(
        f"PREPARED: {len(rows)} cards; {len(roots)} roots; "
        f"{len(witness_paths)} witness parts; a-b empty"
    )


def load_preparation() -> dict[str, Any]:
    payload = json.loads(PREPARATION.read_text(encoding="utf-8"))
    if payload.get("schema") != "phonetic-sweep-latin-preparation-v1":
        raise AssertionError("ملف التحضير غير معروف")
    if payload.get("sweep_sha256") != sweep_hash():
        raise AssertionError("تغير ملف المسح بعد التحضير")
    if payload.get("a_minus_b_nonempty"):
        raise AssertionError("التحضير يحمل a-b غير فارغة")
    return payload


def audit_text(batch: int, rows: list[dict[str, Any]], controls: list[dict[str, Any]]) -> str:
    counts = Counter(row["state"] for row in rows)
    lines = [
        f"# محضر بطاقات المسح الصوتي اللاتيني، الدفعة {batch:03d}",
        "",
        f"- التاريخ: {DATE}.",
        f"- الطور: `{rows[0]['phase']}`، وعدد البطاقات {len(rows)}.",
        "- الأرجل الثلاث: المروحة اللاتينية الكاملة، وكل درجات الحدث، ومعنى قاموس الفرع مع شواهد الجذور الكاملة.",
        "- حاشية «ما يقوله قاموس الفرع عن الأصل» معلوماتية فقط؛ والاستثناء المنهجي أن الأصل اليوناني المسمى يُحال إلى ملف اليونانية ولا يدخل عد اللاتينية.",
        f"- المفتوح المنتظر: {counts['OPEN-CANDIDATE']}، والمحَال إلى اليونانية: {counts['GREEK-REDIRECT']}، والصادر الحي المحمي في §8: {counts['PROTECTED-S8']}، والموجب اليدوي الجديد: {counts['NEW-TRACE']}.",
        "- مادة الصوت وحده، إن حضرت في هذه الدفعة، باقية تنتظر قياس المعنى وليست مرفوضة.",
        "",
        "## ضابط الست الصادرة",
        "",
    ]
    for item in controls:
        lines.append(
            f"- `{item['word']}` ↔ `{item['root']}`: `a-b=∅`، "
            f"`b-a={clean(item['b_minus_a']) or '∅'}`، والحدث المعلن حاضر."
        )
    positives = [row for row in rows if row["state"] == "NEW-TRACE"]
    if positives:
        lines.extend(["", "## ما وجد في هذه الدفعة", ""])
        for row in positives:
            selected = row["manual_selection"]
            lines.append(
                f"- `{row['word']}` /{row['romanization']}/ ↔ `{selected['root']}`: "
                f"`{row['closure']}`؛ {clean(selected['orbit'])}."
            )
    lines.extend(["", "جميع حقول `a-b` فارغة؛ لذلك انعقدت الدفعة.", ""])
    return "\n".join(lines)


def build_batches(numbers: list[int]) -> None:
    preparation = load_preparation()
    controls = control_run()
    if any(item["a_minus_b"] for item in controls):
        raise AssertionError("ضابط الصادرات فقد مرشحًا؛ أوقف الحصاد")
    windows = source_windows()
    requested = unique(str(number) for number in numbers)
    batch_numbers = [int(value) for value in requested]
    if any(number < 1 or number > len(windows) for number in batch_numbers):
        raise AssertionError("رقم دفعة خارج 1 إلى 23")

    manual_roots = {
        str(spec["root"])
        for number in batch_numbers
        for row in windows[number - 1]
        if (spec := manual_spec(row)) is not None
        and latin_key(str(row["branch"])) not in (preparation.get("prior_issued") or {})
    }
    manual_matches = ROOT_SENSES.matches_for_roots(
        ROOT_SENSES.DEFAULT_RESOURCES, manual_roots, None
    ) if manual_roots else {}

    for number in batch_numbers:
        rows = [comparison_row(row, preparation, manual_matches) for row in windows[number - 1]]
        payload = {
            "schema": "phonetic-sweep-latin-cards-batch-v1",
            "date": DATE,
            "language": LANGUAGE,
            "script": SCRIPT,
            "batch": number,
            "batch_size": len(rows),
            "phase": rows[0]["phase"],
            "controls": {
                "baseline": CONTROL_BASELINE,
                "a_minus_b_nonempty": 0,
                "origin_is_gate": False,
                "fan_complete": True,
                "all_event_tiers_recorded_in": EVENTS.relative_to(ROOT).as_posix(),
                "full_root_witnesses_recorded_in": WITNESS_DISPLAY,
                "root_witness_max_chars": 0,
            },
            "counts": dict(Counter(row["state"] for row in rows)),
            "rows": rows,
        }
        atomic_write(batch_path(number), json.dumps(payload, ensure_ascii=False, indent=1) + "\n")
        atomic_write(batch_audit_path(number), audit_text(number, rows, controls))
        print(
            f"BATCH {number:03d}: {len(rows)} cards; "
            f"{payload['counts'].get('NEW-TRACE', 0)} new; "
            f"{payload['counts'].get('OPEN-CANDIDATE', 0)} open"
        )


def load_result_rows(require_all: bool = False) -> list[dict[str, Any]]:
    paths = sorted((ROOT / "data").glob("phonetic-sweep-latin-cards-batch-*.json"))
    numbers = [int(path.stem.rsplit("-", 1)[-1]) for path in paths]
    if numbers and numbers != list(range(1, max(numbers) + 1)):
        raise AssertionError(f"دفعات غير متصلة: {numbers}")
    if require_all and numbers != list(range(1, EXPECTED_BATCHES + 1)):
        raise AssertionError(f"الموجود من الدفعات {numbers} وليس 1 إلى {EXPECTED_BATCHES}")
    rows: list[dict[str, Any]] = []
    for path in paths:
        payload = json.loads(path.read_text(encoding="utf-8"))
        rows.extend(payload.get("rows") or [])
    return rows


def render_witnesses(witnesses: list[dict[str, Any]]) -> str:
    return "؛ ".join(
        f"قال {clean(item['source'])}: «{clean(item['quote'])}»"
        for item in witnesses
    )


def selected_entry_text(row: dict[str, Any]) -> str:
    dictionary = row["dictionary"]
    count = int(dictionary.get("entries_read_count") or 0)
    selected = dictionary.get("selected_entry") or {}
    if not selected:
        return f"من قاموس اللاتينية ذي 47,919 مدخلةً قُرئت {count} مدخلةً؛ ولم تُنتخب مدخلة لأن طريق الهيكل لم يجتمع له جسر معنًى مسمّى"
    head = clean(selected.get("word"))
    read = clean(selected.get("read"))
    pos = clean(selected.get("pos"))
    meaning = clean(selected.get("en"))
    vocal = f" /{read}/" if read else ""
    return f"من قاموس اللاتينية ذي 47,919 مدخلةً قُرئت {count} مدخلةً؛ المختارة `{head}`{vocal} [{pos}] «{meaning}»"


def reading_card(row: dict[str, Any]) -> list[str]:
    manifest = f"data/phonetic-sweep-latin-cards-batch-{int(row['batch']):03d}.json"
    word = clean(row["word"])
    roman = clean(row["romanization"])
    meaning = clean(row["dictionary"]["meaning"])
    origin = clean(row["dictionary"]["ما يقولُه قاموسُ الفرعِ عن الأصل"])
    selected_text = selected_entry_text(row)
    heading = f"### بطاقة المسح الصوتي اللاتيني: `{word}` /{roman}/؛ {row['card_id']}"
    marker = f"<!-- PHONETIC-SWEEP-LATIN-CARD:{row['card_id']} -->"
    if row["state"] == "GREEK-REDIRECT":
        return [
            heading,
            marker,
            f"- {selected_text}؛ ما يقوله قاموس الفرع عن الأصل: «{origin}». هذه صورة يونانية الأصل، فوُجّهت إلى `{GREEK_RESERVE.relative_to(ROOT).as_posix()}` ولم تُحسب في مقام اللاتينية؛ ولا يصدر هنا حكم جديد، وحالة الإغلاق `OPEN-CANDIDATE`.",
        ]
    if row["state"] == "OPEN-CANDIDATE":
        return [
            heading,
            marker,
            f"- {selected_text}؛ ما يقوله قاموس الفرع عن الأصل: «{origin}»، خبر لا يدخل في الحكم؛ فحصت `fan_any_script.fan({word!r}, 'latin')` وكل درجات `all_tiers` وشواهد الجذور كاملة بـ`--max-chars 0` في `{manifest}` والسجلين؛ المدار ما زال مفتوحًا، وحالة البطاقة `OPEN-CANDIDATE`، ومادة الصوت وحده انتظار لا رفض.",
        ]
    if row["state"] == "PROTECTED-S8":
        return [
            heading,
            marker,
            f"- {selected_text}؛ ما يقوله قاموس الفرع عن الأصل: «{origin}»، خبر لا يدخل في الحكم؛ الأرجل الثلاث كاملة في `{manifest}` والسجلين، والصلة الصادرة الحية محفوظة في §8 بلا مساس ولا عد جديد.",
        ]

    selected = row["manual_selection"]
    event = selected["event"]
    return [
        heading,
        marker,
        f"- الصورة والرومنة: `{word}` /{roman}/؛ الخط في المروحة `latin`.",
        f"- معنى قاموس الفرع: {selected_text}؛ النداء `build_kaikki_index.look('latin', {word!r})`.",
        f"- ما يقوله قاموس الفرع عن الأصل: «{origin}»؛ خبر معلوماتي لا يغلق الباب ولا يخرج الصورة من المقام.",
        f"- رجل الصوت: `{selected['root']}` حاضر في `fan_any_script.fan({word!r}, 'latin')`؛ المروحة كلها في `{manifest}`.",
        f"- رجل الحدث من `frozen_event.all_tiers`، الدرجة {event['tier']} ({clean(event['tier_ar'])}): «{clean(event['text'])}»؛ كل الدرجات في `{EVENTS.relative_to(ROOT).as_posix()}`.",
        f"- شواهد الجذر العربي: {render_witnesses(selected['witnesses'])}؛ والقراءة الكاملة بـ`--max-chars 0` في `{WITNESS_DISPLAY}`.",
        f"- المدار المكتوب باليد: {clean(selected['orbit'])}.",
        f"- نتيجة الأرجل الثلاث: **{row['closure']} (استكشاف)**.",
        f"- حالة الإغلاق: {row['closure']}.",
    ]


def reading_block(rows: list[dict[str, Any]]) -> str:
    lines = [
        BLOCK_START,
        "",
        f"## بطاقات المسح الصوتي للمادة اللاتينية ({DATE})",
        "",
        "قوبلت الصورة بالصوت أولًا، ثم حكم المعنى. حاشية «ما يقوله قاموس الفرع عن الأصل» تحفظ قول القاموس ولا تغلق بابًا؛ وما سماه القاموس يوناني الأصل وُجه إلى ملف اليونانية ولم يدخل عد اللاتينية. الأرجل ثلاث: المروحة، والحدث بكل درجاته، ومعنى قاموس الفرع مع شواهد الجذور العربية الكاملة.",
        "",
        f"بدأ العمل بـ{EXPECTED_DIRECT} شهادة مباشرة في دفعتين، ثم {EXPECTED_REMAINDER} بطاقة من بقية مجتمع الصوت والمعنى، ثم {EXPECTED_SOUND_ONLY:,} بطاقة صوتية باقية للقياس الدلالي. مادة الصوت وحده تنتظر ولا ترفض.",
        "",
    ]
    for row in rows:
        lines.extend(reading_card(row))
        lines.append("")
    lines.extend([BLOCK_END, ""])
    block = "\n".join(lines)
    if "—" in block:
        raise AssertionError("ظهرت شرطة طويلة في باب البطاقات")
    return block


def replace_reading_block(block: str) -> None:
    start_bytes = BLOCK_START.encode("utf-8")
    end_bytes = BLOCK_END.encode("utf-8")
    fd, temporary = tempfile.mkstemp(prefix=READING.name + ".", suffix=".tmp", dir=READING.parent)
    try:
        with READING.open("rb") as source, os.fdopen(fd, "wb") as output:
            with mmap.mmap(source.fileno(), 0, access=mmap.ACCESS_READ) as mapped:
                start = mapped.find(start_bytes)
                if start < 0:
                    prefix_end = len(mapped)
                    suffix_start = len(mapped)
                else:
                    end = mapped.find(end_bytes, start)
                    if end < 0:
                        raise AssertionError("بداية باب البطاقات موجودة بلا نهاية")
                    prefix_end = start
                    suffix_start = end + len(end_bytes)

                def copy_range(begin: int, finish: int) -> None:
                    position = begin
                    while position < finish:
                        chunk = mapped[position : min(finish, position + 8 * 1024 * 1024)]
                        output.write(chunk)
                        position += len(chunk)

                copy_range(0, prefix_end)
                if prefix_end and mapped[prefix_end - 1 : prefix_end] != b"\n":
                    output.write(b"\n")
                output.write(b"\n" + block.encode("utf-8"))
                if suffix_start < len(mapped):
                    output.write(b"\n")
                    copy_range(suffix_start, len(mapped))
        os.replace(temporary, READING)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def final_audit_text(rows: list[dict[str, Any]], counts: dict[str, Any]) -> str:
    lines = [
        "# المحضر النهائي لبطاقات المسح الصوتي اللاتيني",
        "",
        f"- التاريخ: {DATE}.",
        f"- البطاقات: {len(rows):,}، منها {EXPECTED_DIRECT} شهادة مباشرة، و{EXPECTED_REMAINDER} من بقية مجتمع الصوت والمعنى، و{EXPECTED_SOUND_ONLY:,} من مادة الصوت وحده.",
        f"- الجذور المرشحة الفريدة: {counts['unique_candidate_roots']:,}، وكل درجات الحدث محفوظة.",
        f"- الشواهد المعجمية الكاملة: {counts['full_lexicographic_witness_records']:,} سجلًا، بلا اقتطاع.",
        f"- الموجبات اليدوية الجديدة: {counts['new_links']}، والمفتوح: {counts['open_candidates']}، والمحَال إلى اليونانية: {counts['greek_redirects']}، والصادر الحي المحمي في §8: {counts['protected_live_links']}.",
        "- سجل قول الأصل في حاشيته كما قاله قاموس الفرع؛ وما ثبت فيه مسار يوناني صريح أحيل إلى ملف اليونانية ولم يدخل عد اللاتينية.",
        "- مادة الصوت وحده باقية تنتظر قياس المعنى، وليست مرفوضة ولا مغلقة.",
        "",
        "## ما وجد",
        "",
    ]
    for row in rows:
        if row["state"] != "NEW-TRACE":
            continue
        selected = row["manual_selection"]
        lines.append(
            f"- `{row['word']}` /{row['romanization']}/ ↔ `{selected['root']}`: "
            f"`{row['closure']}`؛ {clean(selected['orbit'])}."
        )
    lines.extend([
        "",
        "## مواضع السجلات",
        "",
        "- البطاقات: `data/phonetic-sweep-latin-cards-batch-*.json`.",
        f"- الأحداث: `{EVENTS.relative_to(ROOT).as_posix()}`.",
        f"- شواهد الجذور: `{WITNESS_DISPLAY}`.",
        "",
    ])
    return "\n".join(lines)


def finalize() -> None:
    cleanup_superseded()
    preparation = load_preparation()
    controls = control_run()
    if any(item["a_minus_b"] for item in controls):
        raise AssertionError("ظهر a-b قبل الحصيلة النهائية")
    rows = load_result_rows(require_all=True)
    if len(rows) != EXPECTED_BOTH + EXPECTED_SOUND_ONLY:
        raise AssertionError(f"عدد البطاقات النهائي {len(rows)}")
    states = Counter(row["state"] for row in rows)
    prep_counts = preparation["counts"]
    counts = {
        **prep_counts,
        "new_links": states["NEW-TRACE"],
        "open_candidates": states["OPEN-CANDIDATE"],
        "protected_live_links": states["PROTECTED-S8"],
        "greek_redirects": states["GREEK-REDIRECT"],
        "origin_exclusions": sum(bool(row["origin_excluded_card"]) for row in rows),
    }
    payload = {
        "schema": "phonetic-sweep-latin-cards-v1",
        "date": DATE,
        "language": LANGUAGE,
        "script": SCRIPT,
        "law": preparation["law"],
        "counts": counts,
        "controls": controls,
        "manual_positive_cards": [
            row["card_id"] for row in rows if row["state"] == "NEW-TRACE"
        ],
        "files": {
            **preparation["files"],
            "reading": READING.relative_to(ROOT).as_posix(),
            "audit": FINAL_AUDIT.relative_to(ROOT).as_posix(),
            "summary": SUMMARY.relative_to(ROOT).as_posix(),
        },
    }
    atomic_write(SUMMARY, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    replace_reading_block(reading_block(rows))
    atomic_write(FINAL_AUDIT, final_audit_text(rows, counts))
    check(require_final=True)
    print(
        f"FINALIZED: {len(rows)} cards; {states['NEW-TRACE']} new; "
        f"{states['OPEN-CANDIDATE']} open; {states['PROTECTED-S8']} protected"
    )


def check(require_final: bool = False) -> None:
    preparation = load_preparation()
    if any(item.get("a_minus_b") for item in preparation.get("controls") or []):
        raise AssertionError("a-b غير فارغة في التحضير")
    rows = load_result_rows(require_all=require_final or SUMMARY.exists())
    for row in rows:
        if not row.get("romanization"):
            raise AssertionError(f"بطاقة بلا رومنة: {row.get('card_id')}")
        if not row.get("three_legs_complete") or not row.get("fan", {}).get("complete"):
            raise AssertionError(f"بطاقة ناقصة الأرجل: {row.get('card_id')}")
        if row.get("origin_is_gate") or row.get("origin_excluded_card"):
            raise AssertionError(f"قول الأصل صار بوابة: {row.get('card_id')}")
        dictionary = row.get("dictionary") or {}
        if "entries_read_count" not in dictionary or "selected_entry" not in dictionary:
            raise AssertionError(f"بطاقة بلا جرد مداخل منتخب: {row.get('card_id')}")
        if row.get("state") == "GREEK-REDIRECT" and not (
            row.get("greek_redirect")
            and row.get("excluded_from_latin_count")
            and row.get("closure") == "OPEN-CANDIDATE"
            and not row.get("counted_new_link")
        ):
            raise AssertionError(f"إحالة يونانية دخلت مقام اللاتينية: {row.get('card_id')}")
        if row.get("root_witness_max_chars") != 0 or row.get("definitions_truncated"):
            raise AssertionError(f"شاهد مقتطع: {row.get('card_id')}")
        if row.get("state") == "NEW-TRACE" and not (
            row.get("manual_selection") or {}
        ).get("orbit_written_by_hand"):
            raise AssertionError(f"موجب بلا مدار يدوي: {row.get('card_id')}")
        size = len(("\n".join(reading_card(row)) + "\n").encode("utf-8"))
        if size > 5 * 1024:
            raise AssertionError(f"بطاقة فوق خمسة كيلوبايت: {row.get('card_id')} {size}")

    expected_roots = {
        root
        for window in source_windows()
        for source in window
        for root in FAN.fan(str(source["branch"]), SCRIPT)
    }
    event_roots = set()
    with EVENTS.open(encoding="utf-8") as handle:
        for line in handle:
            item = json.loads(line)
            if not item.get("all_tiers"):
                raise AssertionError(f"جذر بلا حدث: {item.get('root')}")
            event_roots.add(item["root"])
    witness_roots = set()
    witness_paths = sorted((ROOT / "data").glob(WITNESS_GLOB))
    if not witness_paths or any(path.stat().st_size >= 100_000_000 for path in witness_paths):
        raise AssertionError("أجزاء سجل الشواهد غائبة أو فوق حد الإيداع")
    for path in witness_paths:
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                item = json.loads(line)
                if item.get("max_chars") != 0 or item.get("definitions_truncated"):
                    raise AssertionError(f"شاهد مقتطع: {item.get('root')}")
                if any(match.get("definition_truncated") for match in item.get("matches") or []):
                    raise AssertionError(f"تعريف مقتطع: {item.get('root')}")
                witness_roots.add(item["root"])
    if event_roots != expected_roots or witness_roots != expected_roots:
        raise AssertionError("سجلا الحدث والشواهد لا يغطيان المروحة كلها")

    if require_final or SUMMARY.exists():
        if len(rows) != EXPECTED_BOTH + EXPECTED_SOUND_ONLY:
            raise AssertionError("الحصيلة النهائية ناقصة")
        text = READING.read_text(encoding="utf-8", errors="strict")
        if text.count("PHONETIC-SWEEP-LATIN-CARD:PS-LATIN-") != len(rows):
            raise AssertionError("عدد البطاقات في القراءة لا يساوي البيان")
        block = text[text.index(BLOCK_START) : text.index(BLOCK_END) + len(BLOCK_END)]
        if "—" in block:
            raise AssertionError("شرطة طويلة في باب البطاقات")
    print(
        f"CLEAN: {len(rows)} built cards; {len(expected_roots)} roots fully witnessed; "
        f"origin exclusions 0"
    )


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("--lang", choices=(LANGUAGE,), default=LANGUAGE)
    parser.add_argument("--prepare", action="store_true")
    parser.add_argument("--batches", nargs="+", type=int)
    parser.add_argument("--finalize", action="store_true")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--cleanup-superseded", action="store_true")
    parser.add_argument("--install-pending-clean", action="store_true")
    args = parser.parse_args()
    selected = sum(
        bool(value)
        for value in (
            args.prepare,
            args.batches,
            args.finalize,
            args.check,
            args.cleanup_superseded,
            args.install_pending_clean,
        )
    )
    if selected != 1:
        raise SystemExit(
            "اختر واحدًا من --prepare أو --batches أو --finalize أو --check "
            "أو --cleanup-superseded"
        )
    if args.prepare:
        prepare()
    elif args.batches:
        build_batches(args.batches)
    elif args.finalize:
        finalize()
    elif args.cleanup_superseded:
        cleanup_superseded()
    elif args.install_pending_clean:
        install_pending_clean()
    else:
        check()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
