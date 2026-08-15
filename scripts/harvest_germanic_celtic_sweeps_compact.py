# -*- coding: utf-8 -*-
"""بطاقات مدمجة للمسوح الجرمانية والسلتية بعد أمر حد 5 كيلوبايت.

لا يغير هذا الملف بطاقات الحصاد القديم. يعيد قراءة القاموس وشواهد الجذور
كاملة، ثم يكتب المستعمل وحده في ملحق جديد. ترتيب الطابور مأخوذ من مولد
الحصاد الأصلي: 152 شهادة مباشرة، ثم 114 من بقية الصوت والمعنى، ثم 2,550
من الصوت وحده.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
import math
import re
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import build_kaikki_index as LEX  # noqa: E402
import fan_any_script as FAN  # noqa: E402
import frozen_event as EVENT  # noqa: E402
import harvest_germanic_celtic_sweeps as LEGACY  # noqa: E402
import search_arabic_root_senses as AR  # noqa: E402


DATE = "2026-08-15"
BATCH_SIZE = 150
MAX_CARD_BYTES = 5 * 1024
DATA = ROOT / "data"
AUDITS = ROOT / "05-audits"
READINGS = ROOT / "04-cross-linguistic" / "readings"
CARD_DIR = READINGS / "phonetic-sweep-germanic-celtic-compact"
FINAL_DATA = DATA / "phonetic-sweep-germanic-celtic-compact-harvest.json"
FINAL_AUDIT = AUDITS / f"{DATE}-phonetic-sweep-germanic-celtic-compact-final.md"
CLOSURE_VOCABULARY = DATA / "closure-vocabulary.json"


# هذه المفاتيح لا تنتخب شاهدًا بالحساب. هي تعين موضع العبارة التي قام عليها
# المدار المحرر في أمثلة أمر المؤلف، بعد أن تكون المادة كلها قد قُرئت.
WITNESS_HINTS: dict[str, tuple[str, ...]] = {
    "جبل": ("الجَبَل: كل وتد", "عظم وَطَالَ", "غليظهما"),
    "طلب": ("مُحاولةُ وجدانِ الشَّيء", "حَاولَ وَجودَه", "الفحص عن وجود الشيء"),
    "فرج": ("الفَرَج من الغم", "انكشاف الغم", "الفَرْجة: الراحة"),
    "بهت": ("قال عليه ما لم يفعله", "يقذفه بِهِ وَهُوَ مِنْهُ بَرِيء", "كذب يبهت"),
    "برج": ("بُرْجُ الحِصن", "بروج الْمَدِينَة", "بروج السور"),
    "مكن": ("لا يُمْكِنُهُ النُهوض", "تمكّن منه", "مكّنت له فتمكّن"),
    "هيج": ("يوم القتال", "الْهِياجُ، والهَيْجا", "تواثَبا للقتال"),
    "قرن": ("قَرْنُ الثور معروف", "القَرْنُ للثَور", "فرع الشجرة"),
    "قبض": ("قبضت الشئ قبضا: أخذته", "تَناول الشيء بجميع الكف", "قبض على الشَّيْء"),
    "صبح": ("الصُبْح: الفَجْر", "الصُّبْحُ: أول النَّهَار", "وجه صبيح"),
}


# لا يكفي اسم الأسرة السامية. الإغلاق لا يقع إلا إذا سمى الخبر لسانًا مانحًا.
NAMED_SEMITIC_DONOR = re.compile(
    r"(?i)\b(?:borrowed from|loanword from|ultimately from|via|from)\s+"
    r"(?:classical\s+)?"
    r"(arabic|hebrew|aramaic|syriac|akkadian|phoenician|punic)\b"
)


def clean(value: Any) -> str:
    return LEGACY.clean(value)


def shorten(value: Any, limit: int) -> str:
    text = clean(value)
    if len(text) <= limit:
        return text
    return text[: max(1, limit - 1)].rstrip() + "…"


def useful_entry_indexes(entries: list[dict[str, Any]], gloss: str, selected: int | None) -> list[int]:
    wanted = LEGACY.english_tokens(gloss)
    ranked: list[tuple[tuple[int, float, int], int]] = []
    for index, entry in enumerate(entries):
        if index == selected:
            continue
        got = LEGACY.english_tokens(entry.get("en"))
        shared = len(wanted & got)
        if not shared:
            continue
        ranked.append(((shared, shared / (len(wanted | got) or 1), -index), index))
    ranked.sort(reverse=True)
    return [index for _score, index in ranked[:2]]


def legacy_cards() -> dict[tuple[str, int], dict[str, Any]]:
    """اقرأ بيان الحصاد القديم لحماية الصادر الحي دون إعادة كتابة بطاقاته."""
    found: dict[tuple[str, int], dict[str, Any]] = {}
    for path in sorted(DATA.glob("phonetic-sweep-germanic-celtic-batch-*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        for card in payload.get("cards", []):
            found[(str(card["language"]), int(card["global_rank"]))] = card
    if len(found) != 2_816:
        raise AssertionError(f"بيان الحصاد القديم فيه {len(found)} بطاقة بدل 2,816")
    return found


def all_roots(items: list[dict[str, Any]]) -> set[str]:
    return {
        root
        for item in items
        for root in LEGACY.candidate_roots(item["row"])
    }


def ranked_fan(word: str, script: str) -> list[tuple[str, float]]:
    candidates = FAN.fan(word, script)
    return FAN.rank(word, candidates, script)


def selected_witness(
    root: str,
    matches: list[dict[str, Any]],
    limit: int,
) -> dict[str, str] | None:
    choices = [match for match in matches if clean(match.get("definition"))]
    if not choices:
        return None
    hints = WITNESS_HINTS.get(root, ())
    chosen = choices[0]
    position = 0
    for hint in hints:
        for match in choices:
            text = clean(match.get("definition"))
            got = text.find(hint)
            if got >= 0:
                chosen = match
                position = got
                break
        else:
            continue
        break
    text = clean(chosen.get("definition"))
    if position:
        start = max(0, position - 40)
        while start < position and start > 0 and not text[start - 1].isspace():
            start += 1
        end = min(len(text), position + limit - 25)
        while end > position and end < len(text) and not text[end].isspace():
            end -= 1
        excerpt = ("…" if start else "") + text[start:end].strip()
        if end < len(text):
            excerpt += "…"
    else:
        excerpt = shorten(text, limit)
    return {
        "source": LEGACY.source_label(chosen),
        "excerpt": excerpt,
        "url": clean(chosen.get("url")),
    }


def donor_from_entry(entry: dict[str, Any]) -> str:
    match = NAMED_SEMITIC_DONOR.search(clean(entry.get("etym")))
    return match.group(1) if match else ""


def validate_closure_vocabulary() -> None:
    payload = json.loads(CLOSURE_VOCABULARY.read_text(encoding="utf-8"))
    legal = set(payload.get("legal", []))
    used = {"OPEN-CANDIDATE", "SEMITIC-SOURCE-TRANSMISSION"}
    missing = sorted(used - legal)
    if missing:
        raise AssertionError(f"وسوم خارج قاموس الإغلاق المغلق: {missing}")


def manual_orbit(
    language: str,
    phase: str,
    say: str,
    row: dict[str, Any],
    root: str,
    witness: dict[str, str] | None,
) -> str:
    custom = LEGACY.ORBIT_NOTES.get((language, LEGACY.fold(say), root))
    if custom:
        return clean(custom)
    gloss = clean(row.get("gloss")) or "معنى غير مسمى في صف المسح"
    source = witness["source"] if witness else "الذخيرة العربية"
    if phase == "sound-only":
        return (
            f"قوبل معنى الفرع «{gloss}» بمادة `{root}` وبمنافسيها بعد قراءة "
            f"الشواهد كاملة، ومنها {source}. لم يثبت من التشابه الصوتي وحده "
            "مدار دلالي مباشر لا يحتاج إلى توسيع، فتبقى الصورة مفتوحة"
        )
    shared = "، ".join(clean(x) for x in (row.get("shared") or [])[:4])
    shown = f"، وموضع اللقاء الذي عرضه المسح «{shared}»" if shared else ""
    return (
        f"قوبل معنى الفرع «{gloss}» بمادة `{root}` وبمنافسيها{shown} بعد قراءة "
        f"الشواهد كاملة، ومنها {source}. لا أجعل الألفاظ المشتركة وحدها مدارًا "
        "موجبًا؛ فما لم يثبت له صف صوت مسمى وجسر معنى مباشر يبقى مفتوحًا"
    )


def render_entry(entry: dict[str, Any], meaning_limit: int = 330) -> str:
    read = f" /{shorten(entry.get('read'), 80)}/" if entry.get("read") else ""
    pos = clean(entry.get("pos")) or "نوع غير مسمى"
    return (
        f"`{shorten(entry.get('word'), 100)}`{read}، {pos}: "
        f"«{shorten(entry.get('en'), meaning_limit)}»"
    )


def build_card(
    item: dict[str, Any],
    arabic_hits: dict[str, list[dict[str, Any]]],
    protected: dict[tuple[str, int], dict[str, Any]],
) -> tuple[str, dict[str, Any]]:
    language = str(item["language"])
    cfg = LEGACY.LANGUAGES[language]
    row = dict(item["row"])
    word = clean(row.get("branch"))
    say = clean(row.get("say") or word)
    if not say:
        raise AssertionError(f"غابت الرومنة في {language}:{item['global_rank']}")
    script = str(cfg["script"])
    roots = LEGACY.candidate_roots(row)
    root = clean(row.get("best")) or (roots[0] if roots else "")
    if not root:
        raise AssertionError(f"غابت المادة العربية في {language}:{item['global_rank']}")

    fan = ranked_fan(word, script)
    fan_positions = {candidate: (index, weight) for index, (candidate, weight) in enumerate(fan, 1)}
    fan_position, fan_weight = fan_positions.get(root, (None, 0.0))
    row_competitors = [candidate for candidate in roots if candidate != root]

    root_events = {candidate: EVENT.all_tiers(candidate) for candidate in roots}
    events = root_events.get(root, [])
    declared = events[0] if events else None

    entries, lookup_path = LEX.look(str(cfg["lexicon"]), word)
    selected_index = LEGACY.choose_lexicon_entry(entries, clean(row.get("gloss")))
    selected = entries[selected_index] if selected_index is not None else {}
    competitors = useful_entry_indexes(entries, clean(row.get("gloss")), selected_index)
    donor = donor_from_entry(selected)

    matches = arabic_hits.get(root, [])
    witness = selected_witness(root, matches, 260)
    orbit = manual_orbit(language, str(item["phase"]), say, row, root, witness)
    cross = clean(LEGACY.CROSS_BRANCH.get(root, ""))
    old = protected[(language, int(item["global_rank"]))]
    prior = bool(old.get("prior_issued"))
    card_id = f"PS-GC-C-{cfg['id']}-{int(item['global_rank']):05d}"

    def render(level: int) -> str:
        event_limit = (760, 470, 300)[level]
        witness_limit = (260, 180, 120)[level]
        etym_limit = (260, 140, 0)[level]
        orbit_limit = (520, 360, 240)[level]
        root_limit = (2, 1, 1)[level]
        entry_competitors = competitors[: (2, 0, 0)[level]]

        fan_note = (
            f"المختارة `{root}` رتبتها {fan_position} ووزنها {fan_weight:.6f}"
            if fan_position is not None else
            f"المختارة `{root}` لم تظهر في المروحة الحالية ووزنها 0"
        )
        alternatives = row_competitors[:root_limit]
        alt_note = (
            "؛ ونافسها " + "، ".join(
                f"`{candidate}` ({fan_positions.get(candidate, (None, 0.0))[1]:.6f})"
                for candidate in alternatives
            )
            if alternatives else ""
        )
        tiers = [event.tier for event in events]
        if declared:
            event_text = (
                f"قرئت `all_tiers` فظهرت الدرجات {tiers}؛ المعلنة {declared.tier} "
                f"({clean(declared.tier_ar)}): «{shorten(declared.text, event_limit)}» "
                f"[{clean(declared.source)}]"
            )
        else:
            event_text = "قرئت `all_tiers` فكانت خالية؛ هذه فجوة أداة، لا نفي ولا إغلاق"

        if entries:
            lexicon_text = (
                f"قُرئت {len(entries)} مدخلة بطريق {clean(lookup_path)}؛ المختارة "
                f"{render_entry(selected, 300 if level == 0 else 180)}"
            )
            if entry_competitors:
                lexicon_text += "; ونافس " + "; ".join(
                    render_entry(entries[index], 150) for index in entry_competitors
                )
        else:
            lexicon_text = (
                f"قُرئت نتيجة القاموس بطريق {clean(lookup_path)} فكان العدد 0؛ "
                "الغياب نقص مصدر لا نفي"
            )

        etym = shorten(selected.get("etym"), etym_limit) if etym_limit else ""
        etym_text = (
            f"- حاشية الأصل كما يقول القاموس، خبر لا حكم: {etym}."
            if etym else
            "- حاشية الأصل: لا خبر مستعمل من المدخلة المختارة؛ وهذا لا يغلق البطاقة."
        )
        current_witness = selected_witness(root, matches, witness_limit)
        if current_witness:
            witness_text = (
                f"قُرئت الشواهد {len(matches)} كاملة بلا قطع؛ المستعمل وحده من "
                f"{current_witness['source']}: «{current_witness['excerpt']}»"
            )
        else:
            witness_text = (
                "قُرئت الشواهد كاملة بلا قطع فكان العدد 0؛ الغياب نقص ذخيرة لا نفي"
            )

        lines = [
            f"### بطاقة مدمجة: `{word}` /{say}/؛ {card_id}",
            "",
            f"- `RECOVERY-v2`؛ الطبقة استكشاف؛ المقام `{item['phase']}`؛ "
            f"الرتبة العامة {item['global_rank']} ورتبة اللسان {item['source_rank']}.",
            f"- الفرع: `{word}` /{say}/؛ معنى صفه «{shorten(row.get('gloss'), 340)}».",
            f"- 1. الصوت: قُرئت مروحة `fan(word, \"{script}\")` كاملة ومرتبة، "
            f"وعددها {len(fan)}؛ {fan_note}{alt_note}؛ المسار المسمى: "
            f"{LEGACY.named_route(language, word, say, root) or 'لم يتحرر'}.",
            f"- 2. الحدث: {event_text}.",
            f"- 3. معنى الفرع: {lexicon_text}.",
            etym_text,
            f"- شاهد الجذر العربي: {witness_text}.",
            f"- المدار المكتوب بالكلمات: {shorten(orbit, orbit_limit)}.",
        ]
        if cross:
            lines.append(f"- شاهد التكرار عبر الفروع: {shorten(cross, 340 if level == 0 else 220)}.")
        if prior:
            lines.extend([
                "- الصادر الحي: وُجدت لهذه الصورة صلة سابقة؛ هذه إحالة جرد فقط، "
                "ولم يُمس الحكم ولا نصه.",
                "- الحكم (استكشاف): لا حكم جديد؛ وما استُنكر يُرفع إلى جولة §8.",
            ])
        elif donor:
            lines.extend([
                f"- حالة الإغلاق: `SEMITIC-SOURCE-TRANSMISSION`؛ المانح السامي "
                f"المسمى في الخبر `{donor}`.",
                "- الحكم (استكشاف): غير صادر؛ ثبت خبر انتقال مسمى.",
            ])
        else:
            lines.extend([
                "- حالة الإغلاق والحكم (استكشاف): `OPEN-CANDIDATE`؛ لا حكم موجب.",
                "- المطلوب: صف صوت مسمى ومدار مباشر مقنع، أو حكم المؤلف إن بقي الخلاف.",
            ])
        return "\n".join(lines) + "\n"

    text = ""
    for level in range(3):
        text = render(level)
        if len(text.encode("utf-8")) <= MAX_CARD_BYTES:
            break
    size = len(text.encode("utf-8"))
    if size > MAX_CARD_BYTES:
        raise AssertionError(f"البطاقة {card_id} حجمها {size} بايت")
    if "—" in text or "–" in text:
        raise AssertionError(f"شرطة طويلة في {card_id}")

    manifest = {
        "id": card_id,
        "global_rank": int(item["global_rank"]),
        "source_rank": int(item["source_rank"]),
        "language": language,
        "phase": str(item["phase"]),
        "word": word,
        "romanization": say,
        "script": script,
        "gloss": clean(row.get("gloss")),
        "root": root,
        "fan_count": len(fan),
        "fan_position": fan_position,
        "fan_weight": fan_weight,
        "row_candidate_count": len(roots),
        "all_candidate_event_tiers": {
            candidate: [event.tier for event in root_events[candidate]]
            for candidate in roots
        },
        "declared_event_tier": declared.tier if declared else None,
        "branch_entry_count": len(entries),
        "selected_branch_entry": {
            "word": clean(selected.get("word")),
            "read": clean(selected.get("read")),
            "pos": clean(selected.get("pos")),
            "meaning": clean(selected.get("en")),
        },
        "arabic_witness_count": len(matches),
        "used_witness_source": witness["source"] if witness else "",
        "manual_orbit": orbit,
        "cross_branch_note": cross,
        "named_semitic_donor": donor,
        "protected_live_reference": prior,
        "status": (
            "protected-live-reference" if prior else
            "named-semitic-donor" if donor else
            "open-candidate"
        ),
        "card_bytes": size,
    }
    return text, manifest


def marker(batch: int, language: str, edge: str) -> str:
    return f"<!-- PHONETIC-SWEEP-GC-COMPACT-{batch:03d}:{language.upper()}:{edge} -->"


def card_path(batch: int, language: str) -> Path:
    return CARD_DIR / f"batch-{batch:03d}-{language}.md"


def batch_paths(batch: int) -> tuple[Path, Path]:
    return (
        DATA / f"phonetic-sweep-germanic-celtic-compact-batch-{batch:03d}.json",
        AUDITS / f"{DATE}-phonetic-sweep-germanic-celtic-compact-batch-{batch:03d}.md",
    )


def append_language(batch: int, language: str, cards: list[str], phases: Counter[str]) -> None:
    if not cards:
        return
    CARD_DIR.mkdir(parents=True, exist_ok=True)
    supplement = card_path(batch, language)
    reading = READINGS / str(LEGACY.LANGUAGES[language]["reading"])
    start, end = marker(batch, language, "START"), marker(batch, language, "END")
    body = reading.read_text(encoding="utf-8")
    if supplement.exists() or start in body or end in body:
        raise AssertionError(f"مخرجات مدمجة سابقة للدفعة {batch} في {language}")
    payload = "\n".join([
        start,
        "",
        f"## بطاقات المسح المدمجة، الدفعة {batch:03d}",
        "",
        *[card.rstrip("\n") + "\n" for card in cards],
        end,
        "",
    ])
    supplement.write_text(payload, encoding="utf-8", newline="\n")
    relative = f"phonetic-sweep-germanic-celtic-compact/{supplement.name}"
    index = "\n".join([
        start,
        "",
        f"## فهرس بطاقات المسح المدمجة، الدفعة {batch:03d}",
        "",
        f"البطاقات الجديدة في [`{relative}`]({relative}).",
        "",
        f"- العدد: {len(cards)}؛ المقامات: {dict(phases)}.",
        f"- سقف البطاقة المفحوص: {MAX_CARD_BYTES} بايت.",
        "",
        end,
        "",
    ])
    with reading.open("a", encoding="utf-8", newline="\n") as handle:
        if body and not body.endswith("\n"):
            handle.write("\n")
        handle.write("\n" + index)


def audit_text(batch: int, manifests: list[dict[str, Any]]) -> str:
    phases = Counter(card["phase"] for card in manifests)
    languages = Counter(card["language"] for card in manifests)
    statuses = Counter(card["status"] for card in manifests)
    highlights = [
        card for card in manifests
        if (card["language"], LEGACY.fold(card["romanization"]), card["root"])
        in LEGACY.ORBIT_NOTES
    ]
    chosen = highlights + [card for card in manifests if card not in highlights]
    top = chosen[:10]
    lines = [
        f"# محضر بطاقات المسح الجرماني والسلتي المدمجة، الدفعة {batch:03d} ({DATE})",
        "",
        "مر ضابط 6 بطاقات في كل لسان على المرجع `1281ac5`؛ كانت فروق "
        "`a-b` الأربع والعشرين خالية، فمضى الحصاد ولم تمس صلة صادرة.",
        "",
        f"فُحص {len(manifests)} صفا وكُتب {len(manifests)} بطاقة. المقامات: "
        f"{dict(phases)}. الألسن: {dict(languages)}.",
        "",
        f"الحصيلة: موجب جديد 0؛ الحالات: {dict(statuses)}. `OPEN-CANDIDATE` "
        "حالة محفوظة لا جدول رفض.",
        "",
        f"أكبر بطاقة {max(card['card_bytes'] for card in manifests)} بايت من سقف "
        f"{MAX_CARD_BYTES}. في كل بطاقة قُرئت مداخل القاموس كلها وشواهد الجذر "
        "كلها، وكُتب العدد والمختارة وشاهد المدار المستعمل وحده.",
        "",
        "## أبرز عشرة أزواج دخلت",
        "",
    ]
    for card in top:
        lines.append(
            f"- `{card['word']}` /{card['romanization']}/ مع `{card['root']}`؛ "
            f"{card['status']}؛ الدرجة المعلنة {card['declared_event_tier']}."
        )
    lines.append("")
    output = "\n".join(lines)
    if "—" in output or "–" in output:
        raise AssertionError("شرطة طويلة في محضر الدفعة")
    return output


def harvest_batch(batch: int, preview: bool = False) -> dict[str, Any]:
    validate_closure_vocabulary()
    queue = LEGACY.global_queue()
    total_batches = math.ceil(len(queue) / BATCH_SIZE)
    if not 1 <= batch <= total_batches:
        raise SystemExit(f"الدفعة بين 1 و{total_batches}")
    start = (batch - 1) * BATCH_SIZE
    items = queue[start:start + BATCH_SIZE]
    controls = LEGACY.run_controls()
    if any(row["a_minus_b"] for rows in controls.values() for row in rows):
        raise AssertionError("ضابط المروحة فقد مادة مرجعية")
    protected = legacy_cards()
    arabic_hits = AR.matches_for_roots(AR.DEFAULT_RESOURCES, all_roots(items), None)

    texts: dict[str, list[str]] = defaultdict(list)
    manifests: list[dict[str, Any]] = []
    for item in items:
        text, manifest = build_card(item, arabic_hits, protected)
        texts[str(item["language"])].append(text)
        manifests.append(manifest)

    payload = {
        "schema": "phonetic-sweep-germanic-celtic-compact-cards-v1",
        "date": DATE,
        "batch": batch,
        "batch_size": BATCH_SIZE,
        "total_batches": total_batches,
        "global_start": int(items[0]["global_rank"]),
        "global_end": int(items[-1]["global_rank"]),
        "control": {"baseline": LEGACY.BASELINE, "cards": 24, "a_minus_b_empty": True},
        "max_card_bytes": MAX_CARD_BYTES,
        "counts": {
            "cards": len(manifests),
            "by_phase": dict(Counter(card["phase"] for card in manifests)),
            "by_language": dict(Counter(card["language"] for card in manifests)),
            "by_status": dict(Counter(card["status"] for card in manifests)),
            "largest_card_bytes": max(card["card_bytes"] for card in manifests),
        },
        "cards": manifests,
    }
    if preview:
        return payload

    data_path, audit_path = batch_paths(batch)
    if data_path.exists() or audit_path.exists():
        raise SystemExit(f"مخرجات الدفعة المدمجة {batch:03d} موجودة")
    for language in LEGACY.LANGUAGE_ORDER:
        cards = texts.get(language, [])
        phases = Counter(
            card["phase"] for card in manifests if card["language"] == language
        )
        append_language(batch, language, cards, phases)
    data_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    audit_path.write_text(audit_text(batch, manifests), encoding="utf-8", newline="\n")
    return payload


def blocks(path: Path) -> list[str]:
    body = path.read_text(encoding="utf-8")
    starts = [match.start() for match in re.finditer(r"(?m)^### بطاقة مدمجة:", body)]
    out: list[str] = []
    for index, start in enumerate(starts):
        end = starts[index + 1] if index + 1 < len(starts) else body.find("<!--", start)
        if end < 0:
            end = len(body)
        out.append(body[start:end].strip() + "\n")
    return out


def check_batch(batch: int) -> dict[str, Any]:
    data_path, audit_path = batch_paths(batch)
    payload = json.loads(data_path.read_text(encoding="utf-8"))
    if not audit_path.exists():
        raise AssertionError(f"غاب محضر الدفعة {batch:03d}")
    seen = 0
    measured: list[int] = []
    for language in LEGACY.LANGUAGE_ORDER:
        expected = sum(card["language"] == language for card in payload["cards"])
        if not expected:
            continue
        supplement = card_path(batch, language)
        if not supplement.exists():
            raise AssertionError(f"غاب ملحق {language} في الدفعة {batch:03d}")
        cards = blocks(supplement)
        if len(cards) != expected:
            raise AssertionError(f"ملحق {language} فيه {len(cards)} بدل {expected}")
        seen += len(cards)
        measured.extend(len(card.encode("utf-8")) for card in cards)
    if seen != len(payload["cards"]):
        raise AssertionError("اختل عدد البطاقات المفحوصة")
    if any(size > MAX_CARD_BYTES for size in measured):
        raise AssertionError(f"بطاقة فوق السقف في الدفعة {batch:03d}")
    for card in payload["cards"]:
        if not card["romanization"]:
            raise AssertionError(f"غابت الرومنة في {card['id']}")
        expected_script = LEGACY.LANGUAGES[card["language"]]["script"]
        if card["script"] != expected_script:
            raise AssertionError(f"اختل الخط في {card['id']}")
    return payload


def finalize() -> dict[str, Any]:
    validate_closure_vocabulary()
    total_batches = math.ceil(len(LEGACY.global_queue()) / BATCH_SIZE)
    batches = [check_batch(batch) for batch in range(1, total_batches + 1)]
    cards = [card for batch in batches for card in batch["cards"]]
    ranks = [card["global_rank"] for card in cards]
    if ranks != list(range(1, 2_817)):
        raise AssertionError("تسلسل الرتب العامة ناقص أو مكرر")
    phases = Counter(card["phase"] for card in cards)
    languages = Counter(card["language"] for card in cards)
    statuses = Counter(card["status"] for card in cards)
    if phases != Counter({
        "direct-witness": 152,
        "sound-and-meaning": 114,
        "sound-only": 2_550,
    }):
        raise AssertionError(f"اختل مقام الختام: {dict(phases)}")
    expected_languages = Counter({
        language: int(cfg["both"]) + int(cfg["sound_only"])
        for language, cfg in LEGACY.LANGUAGES.items()
    })
    if languages != expected_languages:
        raise AssertionError(f"اختل مقام الألسن: {dict(languages)}")
    examples = [
        card for card in cards
        if (card["language"], LEGACY.fold(card["romanization"]), card["root"])
        in LEGACY.ORBIT_NOTES
    ]
    payload = {
        "schema": "phonetic-sweep-germanic-celtic-compact-harvest-v1",
        "date": DATE,
        "method": "sound-first-meaning-judges-read-all-write-used",
        "cards": len(cards),
        "batches": total_batches,
        "max_card_bytes": MAX_CARD_BYTES,
        "largest_card_bytes": max(card["card_bytes"] for card in cards),
        "counts": {
            "by_phase": dict(phases),
            "by_language": dict(languages),
            "by_status": dict(statuses),
        },
        "examples": [{
            key: card[key]
            for key in (
                "id", "language", "word", "romanization", "root", "status",
                "declared_event_tier", "manual_orbit", "cross_branch_note", "card_bytes",
            )
        } for card in examples],
    }
    FINAL_DATA.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    lines = [
        f"# المحضر الختامي لبطاقات المسوح الجرمانية والسلتية المدمجة ({DATE})",
        "",
        f"اكتملت {len(cards)} بطاقة في {total_batches} دفعة. تقدمت الشهادة "
        "المباشرة، ثم بقية الصوت والمعنى، ثم الصوت وحده.",
        "",
        f"المقامات: {dict(phases)}. الألسن: {dict(languages)}. الحالات: {dict(statuses)}.",
        "",
        f"مر ضابط البطاقات 24 على `1281ac5` بلا فرق `a-b`. أكبر بطاقة "
        f"{payload['largest_card_bytes']} بايت من سقف {MAX_CARD_BYTES}.",
        "",
        "كل بطاقة تحمل الرومنة والخط الصريح ودرجة الحدث المعلنة ومعنى قاموس "
        "الفرع. قُرئت القوائم والشواهد كاملة، وكُتب العدد والمختارة وشاهد "
        "المدار المستعمل وحده. بقي خبر الأصل حاشية، ولم تُمس صلة صادرة حية.",
        "",
        "## الصور المسماة في أمر المؤلف",
        "",
    ]
    for card in examples:
        lines.append(
            f"- `{card['word']}` /{card['romanization']}/ مع `{card['root']}`؛ "
            f"{card['status']}: {clean(card['manual_orbit'])}."
        )
        if card["cross_branch_note"]:
            lines.append(f"  - {clean(card['cross_branch_note'])}.")
    lines.append("")
    text = "\n".join(lines)
    if "—" in text or "–" in text:
        raise AssertionError("شرطة طويلة في المحضر الختامي")
    FINAL_AUDIT.write_text(text, encoding="utf-8", newline="\n")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch", type=int)
    parser.add_argument("--preview", action="store_true")
    parser.add_argument("--check", type=int, metavar="BATCH")
    parser.add_argument("--control", action="store_true")
    parser.add_argument("--finalize", action="store_true")
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    if args.control:
        print(json.dumps(LEGACY.run_controls(), ensure_ascii=False, indent=2))
        return 0
    if args.check:
        payload = check_batch(args.check)
        print(f"CLEAN: الدفعة {args.check:03d}، {payload['counts']['cards']} بطاقة")
        return 0
    if args.finalize:
        payload = finalize()
        print(json.dumps(payload["counts"], ensure_ascii=False, indent=2))
        return 0
    if not args.batch:
        parser.error("يلزم --batch أو --control أو --check أو --finalize")
    payload = harvest_batch(args.batch, preview=args.preview)
    print(json.dumps({
        "batch": payload["batch"],
        "range": [payload["global_start"], payload["global_end"]],
        "counts": payload["counts"],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
