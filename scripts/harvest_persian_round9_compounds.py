# -*- coding: utf-8 -*-
"""الجولة التاسعة للمسار B: تفكيك المركبات الفارسية المفتوحة نصيا."""

from __future__ import annotations

import json
import re
import sys
import unicodedata
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fan_any_script as FAN  # noqa: E402
import frozen_event as EVENT  # noqa: E402
import harvest_persian_round6 as BASE  # noqa: E402
import search_arabic_root_senses as SENSES  # noqa: E402


READING = ROOT / "04-cross-linguistic" / "readings" / "persian.md"
REPORT = ROOT / "_inbox" / "lane-reports" / "2026-08-16-B.md"
BRANCH = ROOT / "data" / "branch-lexicons" / "persian.json"
MARKER = "LANE-B-PERSIAN-ROUND9-COMPOUNDS-2026-08-17"
FIRST_ID = 601
FIRST_SOURCE = 696
COMPOUND_COUNT = 80
BATCH_SIZES = (40, 40)
CARD_LIMIT = 5120

# هذا الصف موجود في الشبكة النافذة، وقد أضافته الجولة السابعة إلى مجالها المحلي.
BASE.ROUTES[("ک", "ق")] = "GUT-01"


@dataclass(frozen=True)
class Compound:
    source_index: int
    word: str
    reading: str
    pos: str
    member_id: str
    family_id: str
    etymology: str
    gloss: str
    previous_id: str | None
    previous_verdict: str | None


@dataclass(frozen=True)
class ComponentSpec:
    word: str
    reading: str
    gloss: str
    label: str


@dataclass(frozen=True)
class ComponentAnalysis:
    spec: ComponentSpec
    skeleton: tuple[str, ...]
    ranked_fan: tuple[tuple[str, float], ...]
    candidate: str | None
    route: str
    event: str
    match_count: int
    witnesses: tuple[tuple[str, str], tuple[str, str]]
    orbit: str
    obstacle: str
    verdict: str


@dataclass(frozen=True)
class ComponentRef:
    card_id: int
    verdict: str


@dataclass(frozen=True)
class RenderedCompound:
    compound: Compound
    card_ids: tuple[int, ...]
    texts: tuple[str, ...]
    decomposed: bool
    component_verdicts: tuple[str, ...]
    reference_count: int


def spec(word: str, reading: str, gloss: str, label: str) -> ComponentSpec:
    return ComponentSpec(word=word, reading=reading, gloss=gloss, label=label)


# لا يدخل هذا الجدول إلا تفكيك صريح في سطر بطاقة الفرع إلى عنصرين مكتوبين
# بالفارسية. التفكيكات الواقعة داخل أصل يوناني/سنسكريتي ونحوها لا تنقل إلى
# سطح العضو الفارسي، والتراكيب الثلاثية لا تختزل إلى عنصرين بالحدس.
DECOMPOSITION_CATALOG: dict[int, tuple[ComponentSpec, ComponentSpec]] = {
    3025: (
        spec("ملت", "millat", "nation", "ملت (millat, “nation”)") ,
        spec("ـیت", "-iyyat", "suffix forming a state or condition", "ـیت (-iyyat)"),
    ),
    4113: (
        spec("بال", "bâl", "wing", "بال (bâl, “wing”)") ,
        spec(
            "گرد",
            "gard",
            "present stem of گردیدن; to rotate",
            "گرد (gard, present stem of گردیدن (gardidan, “to rotate”))",
        ),
    ),
    4203: (
        spec("خله", "xale", "helm, oar", "خله (xale, “helm, oar”)") ,
        spec("ـبان", "-bân", "keeper, guardian suffix", "ـبان (-bân)"),
    ),
    5074: (
        spec("کار", "kâr", "work", "کار (kâr, “work”)") ,
        spec("گیر", "gir", "hold", "گیر (gir, “hold”)") ,
    ),
    7203: (
        spec("اقل", "aqall", "less", "اقل (aqall)") ,
        spec("ـیت", "-iyyat", "suffix forming a state or condition", "ـیت (-iyyat)"),
    ),
    8319: (
        spec("بیـ", "bē /bi", "-less, without", "بیـ (bē /bi, “-less, without”)") ,
        spec("هوده", "hūda /hude", "benefit, use", "هوده (hūda /hude, “benefit, use”)") ,
    ),
    8628: (
        spec(
            "قمپز",
            "qompoz",
            "a cannon without projectile used for the psychological effect of its sound (from Ottoman Turkish)",
            "قمپز (qompoz, “a cannon without projectile used for the psychological effect of its sound (from Ottoman Turkish)”)",
        ),
        spec(
            "درکردن",
            "darkardan",
            "to discharge, to shoot",
            "درکردن (darkardan, “to discharge, to shoot”)",
        ),
    ),
    8772: (
        spec("تال", "tâl", "pond", "تال (tâl, “pond”)") ,
        spec("آب", "āb", "water", "آب (āb, “water”)") ,
    ),
    8842: (
        spec("شور", "šur", "salty", "شور (šur, “salty”)") ,
        spec("ـه", "-e", "suffix -e", "ـه (-e)"),
    ),
    8843: (
        spec("شور", "šur", "salty", "شور (šur, “salty”)") ,
        spec("ـه", "-e", "suffix -e", "ـه (-e)"),
    ),
    8961: (
        spec("دوست", "dust, dôst", "friend, beloved", "دوست (dust, dôst)") ,
        spec("کام", "kâm", "desire, wish; beloved", "کام (kâm)"),
    ),
    9370: (
        spec("جنگ", "jang", "present stem of جنگیدن; to fight", "جنگ (jang, present stem of جنگیدن (jangidan, “to fight”))") ,
        spec("ـنده", "-ande", "agent-noun suffix", "ـنده (-ande)"),
    ),
    10424: (
        spec("قاچاق", "qâčâq", "smuggling", "قاچاق (qâčâq, “smuggling”)") ,
        spec("ـچی", "-či", "occupational suffix", "ـچی (-či, “occupational suffix”)") ,
    ),
    14769: (
        spec("مدنی", "madanī /madani", "civil, civic", "مدنی (madanī /madani)") ,
        spec("ـیت", "-iyyat /-iyat", "suffix forming a state or condition", "ـیت (-iyyat /-iyat)"),
    ),
    16102: (
        spec("پنوموـ", "penomo-", "pneumo-", "پنوموـ (penomo-, “pneumo-”)") ,
        spec("ـلوژی", "-loži", "-logy", "ـلوژی (-loži, “-logy”)") ,
    ),
    16104: (
        spec("پنوموـ", "penomo-", "pneumo-", "پنوموـ (penomo-, “pneumo-”)") ,
        spec("توراکس", "torâks", "thorax", "توراکس (torâks, “thorax”)") ,
    ),
    16107: (
        spec("پنوموـ", "penomo-", "pneumo-", "پنوموـ (penomo-, “pneumo-”)") ,
        spec("ـکوک", "-kok", "-coccus", "ـکوک (-kok, “-coccus”)") ,
    ),
    16108: (
        spec("استافیلوـ", "estâfilo-", "staphylo-", "استافیلوـ (estâfilo-, “staphylo-”)") ,
        spec("ـکوک", "-kok", "-coccus", "ـکوک (-kok, “-coccus”)") ,
    ),
    16111: (
        spec("استرپتوـ", "esterepto-", "strepto-", "استرپتوـ (esterepto-, “strepto-”)") ,
        spec("ـکوک", "-kok", "-coccus", "ـکوک (-kok, “-coccus”)") ,
    ),
    16126: (
        spec("میکروـ", "mikro-", "micro-", "میکروـ (mikro-, “micro-”)") ,
        spec("ارگانیسم", "orgânism", "organism", "ارگانیسم (orgânism, “organism”)") ,
    ),
    16128: (
        spec("میکروـ", "mikro-", "micro-", "میکروـ (mikro-, “micro-”)") ,
        spec("بیولوژی", "biyoloži", "biology", "بیولوژی (biyoloži, “biology”)") ,
    ),
    16170: (
        spec("رینوـ", "rino-", "rhino-", "رینوـ (rino-, “rhino-”)") ,
        spec("فارنژیت", "fâranžit", "pharyngitis", "فارنژیت (fâranžit, “pharyngitis”)") ,
    ),
    16175: (
        spec("رینوـ", "rino-", "rhino-", "رینوـ (rino-, “rhino-”)") ,
        spec("ـپلاستی", "-plâsti", "-plasty", "ـپلاستی (-plâsti, “-plasty”)") ,
    ),
    17643: (
        spec("حکیم", "hakīm", "doctor", "حکیم (hakīm, “doctor”)") ,
        spec("جی", "jī", "honorific particle", "جی (jī, honorific particle)"),
    ),
    17775: (
        spec("هیر", "hir", "fire; worship, obedience", "هیر (hir, “fire; worship, obedience”)") ,
        spec("ـبد", "-bod", "lord, master", "ـبد (-bod, “lord, master”)") ,
    ),
}

# نافذة الجولة التاسعة هي أول ثمانين عضوا من حوض الهيكل الطويل المؤجل. لا
# تستعمل من الكتالوج إلا الأسطر الواقعة فعلا في هذه النافذة.
DECOMPOSITIONS: dict[int, tuple[ComponentSpec, ComponentSpec]] = {
    source_index: DECOMPOSITION_CATALOG[source_index]
    for source_index in (4113, 8628, 8961, 9370)
}


# إحالات مكونات محكومة قبل الجولة التاسعة. لا تعاد قراءتها.
PRIOR_COMPONENTS: dict[str, ComponentRef] = {
    "شور": ComponentRef(274, "OPEN-CANDIDATE"),
    "جنگ": ComponentRef(38, "OPEN-CANDIDATE"),
    "بیولوژی": ComponentRef(130, "LAW-GAP"),
}


DIRECT_SEMITIC_COMPONENTS = {"ملت", "مدنی", "حکیم"}


def clean(value: str) -> str:
    value = unicodedata.normalize("NFC", value)
    value = " ".join(value.split())
    return value.replace("—", "-")


def clip(value: str, limit: int) -> str:
    value = clean(value)
    if len(value) <= limit:
        return value
    return value[:limit].rstrip() + "…"


def parse_previous_completions(text: str) -> dict[str, tuple[str, str]]:
    found: dict[str, tuple[str, str]] = {}
    for block in re.split(r"(?=^### WO-B-OPEN-COMP-)", text, flags=re.MULTILINE):
        heading = re.match(r"### (WO-B-OPEN-COMP-\d+):", block)
        member = re.search(r"العضو الفردي `([^`]+)`", block)
        verdict = re.search(r"^- الحكم \(استكشاف\): ([A-Z-]+)\.$", block, re.MULTILINE)
        if heading and member and verdict:
            number = int(heading.group(1).rsplit("-", 1)[1])
            if number >= FIRST_ID:
                continue
            found[member.group(1)] = (heading.group(1), verdict.group(1))
    return found


def parse_compounds(text: str) -> list[Compound]:
    previous = parse_previous_completions(text)
    compounds: list[Compound] = []
    for block in re.split(r"(?=^### )", text, flags=re.MULTILINE):
        if not block.startswith("### بطاقة: `persian:family:"):
            continue
        if "الحكم (استكشاف): غير صادر" not in block:
            continue
        member = re.search(
            r"- الكلمةُ في الفرع: (.*?) \((.*?)\) \[([^؛]+)؛ "
            r"`(kaikki_persian_[^`]+)`\]\.",
            block,
        )
        family = re.search(r"`(persian:family:[0-9a-f]+)`", block)
        etymology = re.search(r"- أقدمُ صورةٍ مستعادة: (.*?) \[Kaikki Persian", block)
        gloss = re.search(r"- المعنى من قاموس الفرع: «(.*?)» \[Kaikki Persian", block)
        if not (member and family and etymology and gloss):
            continue
        word, reading, pos, member_id = member.groups()
        source_index = int(member_id.split(":", 2)[1])
        etym = clean(etymology.group(1))
        skeleton = tuple(FAN.skeleton(word, "persian"))
        if source_index < FIRST_SOURCE or member_id in previous or len(skeleton) <= 4:
            continue
        prior = previous.get(member_id)
        compounds.append(
            Compound(
                source_index=source_index,
                word=clean(word),
                reading=clean(reading),
                pos=clean(pos),
                member_id=clean(member_id),
                family_id=family.group(1),
                etymology=etym,
                gloss=clean(gloss.group(1)),
                previous_id=prior[0] if prior else None,
                previous_verdict=prior[1] if prior else None,
            )
        )
    compounds.sort(key=lambda item: item.source_index)
    compounds = compounds[:COMPOUND_COUNT]
    if len(compounds) != COMPOUND_COUNT:
        raise AssertionError(f"نافذة المركبات تغيرت: {len(compounds)} لا {COMPOUND_COUNT}")
    if compounds[0].word != "تلسکوپ" or compounds[-1].word != "آنتی‌ژن":
        raise AssertionError("تغير طرف نافذة المركبات في الجولة التاسعة")
    if len({item.member_id for item in compounds}) != len(compounds):
        raise AssertionError("تكرر عضو في نافذة المركبات")
    if set(DECOMPOSITIONS) - {item.source_index for item in compounds}:
        raise AssertionError("تفكيك يدوي خارج نافذة المركبات")
    return compounds


def route_text(skeleton: tuple[str, ...], candidate: str) -> tuple[str, bool]:
    if len(skeleton) != len(candidate):
        return "تعذر الرصف لاختلاف طول الهيكل عن المرشح؛ لا يحذف صامت بالحدس.", False
    parts: list[str] = []
    complete = True
    for source, target in zip(skeleton, candidate):
        row = BASE.ROUTES.get((source, target))
        if row is None:
            parts.append(f"{source}↔{target}=غير مسمى")
            complete = False
        else:
            parts.append(f"{source}↔{target}=`{row}`")
    return "الرصف المفحوص: " + "، ".join(parts), complete


def event_text(candidate: str) -> str:
    events = EVENT.all_tiers(candidate)
    if not events:
        return "لا حدث متاح للمرشح في السجل المجمد."
    event = events[0]
    return f"درجة {event.tier}، {event.tier_ar}: «{clean(event.text)}» [{event.source}]"


def fan_text(ranked: tuple[tuple[str, float], ...]) -> str:
    return "،".join(
        f"{candidate}:{'0' if weight == 0 else format(weight, '.6g')}"
        for candidate, weight in ranked
    )


def component_analysis(
    item: ComponentSpec,
    sense_map: dict[str, list[dict]],
    quote_limit: int = 55,
) -> ComponentAnalysis:
    skeleton = tuple(FAN.skeleton(item.word, "persian"))
    fan = FAN.fan(item.word, "persian")
    ranked = tuple(FAN.rank(item.word, fan, "persian")) if fan else ()
    empty_witnesses = (
        ("فجوة المورد", "لم ينشأ مرشح عربي صالح للمسح؛ لا يختلق جذر."),
        ("فجوة المورد", "لم ينشأ مرشح عربي صالح للمسح؛ لا يختلق جذر."),
    )
    if not ranked:
        morphological = len(skeleton) < 2 or "ـ" in item.word
        verdict = "MORPHOLOGY-GAP" if morphological else "TOOL-GAP"
        return ComponentAnalysis(
            spec=item,
            skeleton=skeleton,
            ranked_fan=ranked,
            candidate=None,
            route="لا مرشح من المروحة؛ بقيت حدود الصرف والصوامت كما نشرها الفرع.",
            event="لا يستدعى حدث بلا مرشح عربي؛ لا يختلق جذر.",
            match_count=0,
            witnesses=empty_witnesses,
            orbit=(
                f"معنى المكون في سطر الفرع «{item.gloss}» مقروء، لكن غياب "
                "مرشح آلي يمنع بناء مدار عربي."
            ),
            obstacle="المروحة لم تعد مرشحا صالحا لهذا المكون بحدوده المنشورة.",
            verdict=verdict,
        )

    candidate = ranked[0][0]
    route, route_complete = route_text(skeleton, candidate)
    match_count, selected = BASE.selected_witnesses(candidate, sense_map, quote_limit)
    witnesses = (selected[0], selected[1])
    independent = SENSES.independent_fan(sense_map.get(candidate, []), 2)
    if not route_complete:
        verdict = "LAW-GAP"
        orbit = (
            f"قوبل معنى المكون «{item.gloss}» بالمرشح `{candidate}`، لكن المدار "
            "لا يصدر قبل اكتمال كل صف صوتي مسمى."
        )
        obstacle = "بقي في الرصف صف صوتي غير مسمى."
    elif not independent["source_coverage_complete"]:
        verdict = "SOURCE-GAP"
        orbit = (
            f"معنى المكون «{item.gloss}» حاضر، ولم يعط المسح شاهدين عربيين "
            f"مستقلين لـ`{candidate}`؛ تبقى رجل المعنى مفتوحة."
        )
        obstacle = "لم يكتمل شاهدان عربيان مستقلان؛ الغياب لا ينفي اللسان."
    elif item.word in DIRECT_SEMITIC_COMPONENTS:
        verdict = "SEMITIC-SOURCE-TRANSMISSION"
        orbit = (
            f"سطر المكون في قاموس الفرع يسمي المصدر العربي، ومعنى «{item.gloss}» "
            f"يلتقي المادة `{candidate}` مباشرة؛ ثبت النقل للمكون وحده."
        )
        obstacle = "اكتملت أرجل الصوت والحدث والمعنى، والمصدر العربي مسمى للمكون."
    else:
        verdict = "OPEN-CANDIDATE"
        orbit = (
            f"قوبل معنى المكون «{item.gloss}» بشاهدي `{candidate}`؛ لم يثبت "
            "اتحاد نقطة المعنى اتحادا مباشرا، فلا ينشأ جسر من التشابه العام."
        )
        obstacle = "قرأ المعنى والشاهدان، ولم يثبت مدار دلالي يدوي مباشر."
    return ComponentAnalysis(
        spec=item,
        skeleton=skeleton,
        ranked_fan=ranked,
        candidate=candidate,
        route=route,
        event=event_text(candidate),
        match_count=match_count,
        witnesses=witnesses,
        orbit=orbit,
        obstacle=obstacle,
        verdict=verdict,
    )


def render_component_full(number: int, analysis: ComponentAnalysis) -> str:
    item = analysis.spec
    skeleton = "ـ".join(analysis.skeleton) if analysis.skeleton else "فارغ"
    fan = fan_text(analysis.ranked_fan) if analysis.ranked_fan else "لا مرشح"
    candidate = f"`{analysis.candidate}`" if analysis.candidate else "لا مرشح"
    return "\n".join(
        [
            f"- قراءة المكون `{item.word}` /{item.reading}/، كما سماه السطر: «{item.label}».",
            f"  - الخطوة صفر والمروحة: الهيكل `{skeleton}`؛ `fan_any_script.fan({item.word}, persian)` أعاد {len(analysis.ranked_fan)}: {fan}.",
            f"  - المقابل ومساره المسمى: {candidate}؛ {analysis.route}",
            f"  - الحدث من السجل المجمد: {analysis.event}",
            f"  - المعنى من قاموس الفرع: «{item.gloss}».",
            f"  - مسح المعاني العربية: {analysis.match_count} نتيجة؛ الشاهد 1، {analysis.witnesses[0][0]}: «{analysis.witnesses[0][1]}»؛ الشاهد 2، {analysis.witnesses[1][0]}: «{analysis.witnesses[1][1]}».",
            f"  - المدار المكتوب بالكلمات: {analysis.orbit}",
            f"  - عائق القرار أو تمامه: {analysis.obstacle}",
            f"  - الحكم المستقل للمكون: {analysis.verdict}؛ موضعه `WO-B-OPEN-COMP-{number:05d}`.",
        ]
    )


def render_component_ref(item: ComponentSpec, ref: ComponentRef) -> str:
    return (
        f"- قراءة المكون `{item.word}` /{item.reading}/: إحالة إلى "
        f"`WO-B-OPEN-COMP-{ref.card_id:05d}`؛ هناك تمت المروحة والمسار والحدث "
        f"والمعنى، وحكم المكون المستقل {ref.verdict}. معنى السطر الحالي «{item.gloss}»؛ "
        "لم تكرر القراءة."
    )


def header_lines(compound: Compound, number: int, part: str | None = None) -> list[str]:
    suffix = f"، القسم {part}" if part else ""
    prior = (
        f"`{compound.previous_id}` بحكم {compound.previous_verdict}"
        if compound.previous_id
        else "لا إتمام سابق لهذا العضو"
    )
    return [
        f"### WO-B-OPEN-COMP-{number:05d}: إتمام المركب `{compound.word}` /{compound.reading}/{suffix}",
        "- إصدار البروتوكول: COMPOUND-DECOMPOSITION-v1 (2026-08-17).",
        f"- مرجع بطاقة الجرد: `{compound.family_id}`؛ العضو الفردي `{compound.member_id}`؛ السابق: {prior}.",
        f"- الكلمة في الفرع: فارسية `{compound.word}` /{compound.reading}/؛ الصنف `{compound.pos}`؛ المعنى «{compound.gloss}».",
    ]


def descriptive_line(compound: Compound, specs: tuple[ComponentSpec, ComponentSpec]) -> str:
    first, second = specs
    qualifier = ""
    if compound.source_index == 5074:
        qualifier = " النص يقيده بإعادة تحليل شعبية، لا بأصل تاريخي جديد؛"
    elif compound.source_index == 8961:
        qualifier = " النص يرده إلى الأصل الداخلي `دوستکام` قبل طريق القرض؛"
    return (
        f"- الحكم الوصفي للمركب، خارج السلم: يصل قاموس الفرع `{compound.word}` "
        f"بـ`{first.word}` «{first.gloss}» + `{second.word}` «{second.gloss}»؛{qualifier} "
        "لا يرث المركب حكم أي مكون، ولا يدخل السلم إلا حكمان مستقلان للمكونين."
    )


def render_boundary(compound: Compound, number: int) -> str:
    lines = header_lines(compound, number)
    lines.extend(
        [
            f"- نص قاموس الفرع المنقول بلا تفكيك حدسي: «{clip(compound.etymology, 520)}» [بطاقة persian.md؛ data/branch-lexicons/persian.json].",
            "- اختبار الحد: لا يسمي السطر تفكيكا فارسيا صالحا على صورة مكون أول + مكون ثان يمكن قراءة كل منهما من الفرع؛ قد يسمي قرضا مركبا أو تفكيك أصل أجنبي أو اختصارا أو بنية ليست ثنائية.",
            "- حظر الحدس: لم تقسم المسافة أو الواصلة أو طول الهيكل إلى جذرين، ولم تنقل عناصر لغة مانحة إلى مكونات فارسية.",
            f"- الحكم الوصفي للمركب، خارج السلم: معنى الفرع «{compound.gloss}» محفوظ، ولا يدخل المركب السلم بوصفه جذرا واحدا.",
            "- حالة الإغلاق: COMPOUND-BOUNDARY.",
            "- عائق الإتمام: يلزم سطر قاموسي من الفرع نفسه يسمي المكونين نصا؛ لا يعوضه التخمين الرسومي.",
        ]
    )
    return "\n".join(lines) + "\n"


def render_single(
    compound: Compound,
    number: int,
    specs: tuple[ComponentSpec, ComponentSpec],
    component_texts: tuple[str, str],
) -> str:
    lines = header_lines(compound, number)
    lines.extend(
        [
            f"- سطر التفكيك من قاموس الفرع كما هو: «{clip(compound.etymology, 520)}» [بطاقة persian.md؛ data/branch-lexicons/persian.json].",
            f"- المكونان من نص السطر بلا حدس: «{specs[0].label} + {specs[1].label}».",
            component_texts[0],
            component_texts[1],
            descriptive_line(compound, specs),
            "- حالة بطاقة التفكيك: READY؛ حكم المركب وصفي فقط.",
        ]
    )
    return "\n".join(lines) + "\n"


def render_split(
    compound: Compound,
    numbers: tuple[int, int],
    specs: tuple[ComponentSpec, ComponentSpec],
    component_texts: tuple[str, str],
) -> tuple[str, str]:
    first_lines = header_lines(compound, numbers[0], "1/2")
    first_lines.extend(
        [
            f"- سطر التفكيك من قاموس الفرع كما هو: «{clip(compound.etymology, 520)}» [بطاقة persian.md؛ data/branch-lexicons/persian.json].",
            f"- المكونان من نص السطر بلا حدس: «{specs[0].label} + {specs[1].label}».",
            f"- إحالة متبادلة: قراءة المكون الثاني والحكم الوصفي في `WO-B-OPEN-COMP-{numbers[1]:05d}`.",
            component_texts[0],
            "- حالة هذا القسم: CONTINUED؛ لا حكم للمركب قبل القسم الثاني.",
        ]
    )
    second_lines = header_lines(compound, numbers[1], "2/2")
    second_lines.extend(
        [
            f"- سطر التفكيك المحكوم هو نفسه في `WO-B-OPEN-COMP-{numbers[0]:05d}`؛ المكونان «{specs[0].label} + {specs[1].label}».",
            f"- إحالة متبادلة: قراءة المكون الأول في `WO-B-OPEN-COMP-{numbers[0]:05d}`.",
            component_texts[1],
            descriptive_line(compound, specs),
            "- حالة بطاقة التفكيك: READY؛ حكم المركب وصفي فقط.",
        ]
    )
    return "\n".join(first_lines) + "\n", "\n".join(second_lines) + "\n"


def prepare_analyses(
    compounds: list[Compound],
) -> dict[str, ComponentAnalysis]:
    unique: dict[str, ComponentSpec] = {}
    for compound in compounds:
        for item in DECOMPOSITIONS.get(compound.source_index, ()):
            if item.word not in PRIOR_COMPONENTS:
                unique.setdefault(item.word, item)
    candidates: dict[str, str] = {}
    for word, item in unique.items():
        fan = FAN.fan(item.word, "persian")
        ranked = FAN.rank(item.word, fan, "persian") if fan else []
        if ranked:
            candidates[word] = ranked[0][0]
    sense_map = SENSES.matches_for_roots(
        SENSES.DEFAULT_RESOURCES,
        set(candidates.values()),
        None,
    )
    return {
        word: component_analysis(item, sense_map)
        for word, item in unique.items()
    }


def render_all(compounds: list[Compound]) -> list[RenderedCompound]:
    analyses = prepare_analyses(compounds)
    registry = dict(PRIOR_COMPONENTS)
    rendered: list[RenderedCompound] = []
    next_id = FIRST_ID

    for compound in compounds:
        specs = DECOMPOSITIONS.get(compound.source_index)
        if specs is None:
            text = render_boundary(compound, next_id)
            rendered.append(
                RenderedCompound(
                    compound=compound,
                    card_ids=(next_id,),
                    texts=(text,),
                    decomposed=False,
                    component_verdicts=(),
                    reference_count=0,
                )
            )
            next_id += 1
            continue

        refs: list[ComponentRef | None] = [registry.get(item.word) for item in specs]
        verdicts = tuple(
            ref.verdict if ref else analyses[item.word].verdict
            for item, ref in zip(specs, refs)
        )
        reference_count = sum(ref is not None for ref in refs)
        component_texts = tuple(
            render_component_ref(item, ref)
            if ref
            else render_component_full(next_id, analyses[item.word])
            for item, ref in zip(specs, refs)
        )
        single = render_single(compound, next_id, specs, component_texts)  # type: ignore[arg-type]
        if len(single.encode("utf-8")) < CARD_LIMIT:
            texts = (single,)
            ids = (next_id,)
            for item, ref, verdict in zip(specs, refs, verdicts):
                if ref is None:
                    registry[item.word] = ComponentRef(next_id, verdict)
            next_id += 1
        else:
            ids = (next_id, next_id + 1)
            # يعاد رقم موضع الحكم داخل كل قراءة بعد معرفة رقم القسم الفعلي.
            split_component_texts = tuple(
                render_component_ref(item, ref)
                if ref
                else render_component_full(ids[index], analyses[item.word])
                for index, (item, ref) in enumerate(zip(specs, refs))
            )
            texts = render_split(compound, ids, specs, split_component_texts)  # type: ignore[arg-type]
            for index, (item, ref, verdict) in enumerate(zip(specs, refs, verdicts)):
                if ref is None:
                    registry[item.word] = ComponentRef(ids[index], verdict)
            next_id += 2
        rendered.append(
            RenderedCompound(
                compound=compound,
                card_ids=ids,
                texts=texts,
                decomposed=True,
                component_verdicts=verdicts,
                reference_count=reference_count,
            )
        )
    return rendered


def validate_rendered(rendered: list[RenderedCompound]) -> None:
    if len(rendered) != COMPOUND_COUNT:
        raise AssertionError("عدد المركبات المكتوبة غير مكتمل")
    all_ids = [card_id for item in rendered for card_id in item.card_ids]
    if all_ids != list(range(FIRST_ID, all_ids[-1] + 1)):
        raise AssertionError("معرفات بطاقات الجولة التاسعة غير متصلة")
    texts = [text for item in rendered for text in item.texts]
    for card_id, text in zip(all_ids, texts):
        size = len(text.encode("utf-8"))
        if size >= CARD_LIMIT:
            raise AssertionError(f"تجاوزت البطاقة {card_id:05d} حد 5KB: {size}")
        if "—" in text or re.search(r"[۰-۹٠-٩]", text):
            raise AssertionError(f"شرطة طويلة أو أرقام غير غربية في {card_id:05d}")
    for item in rendered:
        joined = "\n".join(item.texts)
        if item.decomposed:
            specs = DECOMPOSITIONS[item.compound.source_index]
            if len(item.component_verdicts) != 2:
                raise AssertionError("غاب حكم مكون مستقل")
            for component in specs:
                if component.label not in joined:
                    raise AssertionError(f"لم ينقل المكون نصيا: {component.label}")
            if "الحكم الوصفي للمركب، خارج السلم" not in joined:
                raise AssertionError("غاب الحكم الوصفي للمركب")
            if len(item.card_ids) == 2:
                if f"WO-B-OPEN-COMP-{item.card_ids[0]:05d}" not in item.texts[1]:
                    raise AssertionError("غابت الإحالة العكسية في البطاقة المنقسمة")
                if f"WO-B-OPEN-COMP-{item.card_ids[1]:05d}" not in item.texts[0]:
                    raise AssertionError("غابت الإحالة الأمامية في البطاقة المنقسمة")
        elif "COMPOUND-BOUNDARY" not in joined:
            raise AssertionError("غاب وسم حد المركب غير المفكك")
    decomposed = sum(item.decomposed for item in rendered)
    if decomposed != len(DECOMPOSITIONS):
        raise AssertionError("عدد التفكيكات المكتوبة لا يطابق القائمة النصية")


def batch_sections(rendered: list[RenderedCompound]) -> tuple[str, list[dict[str, object]]]:
    output: list[str] = []
    summaries: list[dict[str, object]] = []
    offset = 0
    for batch_number, batch_size in enumerate(BATCH_SIZES, 1):
        batch = rendered[offset : offset + batch_size]
        offset += batch_size
        output.extend(
            [
                f"## الجولة التاسعة، دفعة تفكيك المركبات رقم {batch_number}",
                "",
                f"- النطاق: {batch_size} مركبا، من `{batch[0].compound.word}` إلى `{batch[-1].compound.word}`؛ التفكيك من نص قاموس الفرع وحده.",
                "",
            ]
        )
        for item in batch:
            output.extend(text.rstrip() for text in item.texts)
            output.append("")
        summaries.append(
            {
                "batch_number": batch_number,
                "compound_count": batch_size,
                "card_count": sum(len(item.card_ids) for item in batch),
                "first_id": batch[0].card_ids[0],
                "last_id": batch[-1].card_ids[-1],
                "first_word": batch[0].compound.word,
                "last_word": batch[-1].compound.word,
                "decomposed": sum(item.decomposed for item in batch),
                "boundary": sum(not item.decomposed for item in batch),
                "splits": sum(len(item.card_ids) == 2 for item in batch),
                "references": sum(item.reference_count for item in batch),
                "component_verdicts": Counter(
                    verdict for item in batch for verdict in item.component_verdicts
                ),
            }
        )
    return "\n".join(output).rstrip() + "\n", summaries


def report_section(rendered: list[RenderedCompound], summaries: list[dict[str, object]]) -> str:
    now = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M %z")
    lines = [f"<!-- {MARKER}:START -->", ""]
    for summary in summaries:
        verdicts: Counter[str] = summary["component_verdicts"]  # type: ignore[assignment]
        distribution = "؛ ".join(f"{key}={verdicts[key]}" for key in sorted(verdicts)) or "لا مكونات قابلة للقراءة"
        lines.extend(
            [
                f"## الجولة التاسعة، دفعة تفكيك المركبات رقم {summary['batch_number']}",
                "",
                f"- الوقت: {now}، Africa/Cairo.",
                f"- المركبات: {summary['compound_count']}؛ البطاقات الفيزيائية: {summary['card_count']}؛ المدى `WO-B-OPEN-COMP-{summary['first_id']:05d}` إلى `WO-B-OPEN-COMP-{summary['last_id']:05d}`.",
                f"- أول المركبات `{summary['first_word']}`؛ آخرها `{summary['last_word']}`.",
                f"- التفكيك النصي المكتمل: {summary['decomposed']}؛ الباقي COMPOUND-BOUNDARY: {summary['boundary']}؛ المنقسم لحد 5KB: {summary['splits']}.",
                f"- أحكام المكونات المستقلة: {distribution}؛ الإحالات إلى قراءة سابقة: {summary['references']}.",
                "- حكم المركب وصفي خارج السلم في كل تفكيك؛ لم يدخل السلم إلا المكون، ولم يفكك أي عضو من الرسم أو المسافة أو الواصلة بالحدس.",
                "",
            ]
        )
    all_cards = [(card_id, text) for item in rendered for card_id, text in zip(item.card_ids, item.texts)]
    sizes = [len(text.encode("utf-8")) for _, text in all_cards]
    max_pos = sizes.index(max(sizes))
    component_verdicts = Counter(
        verdict for item in rendered for verdict in item.component_verdicts
    )
    distribution = "؛ ".join(
        f"{key}={component_verdicts[key]}" for key in sorted(component_verdicts)
    )
    last_id = rendered[-1].card_ids[-1]
    lines.extend(
        [
            "## حصيلة الجولة التاسعة",
            "",
            f"- مجموع المركبات: {len(rendered)} في دفعتين {BATCH_SIZES[0]} + {BATCH_SIZES[1]}؛ التفكيك النصي={sum(item.decomposed for item in rendered)}؛ COMPOUND-BOUNDARY={sum(not item.decomposed for item in rendered)}.",
            f"- بطاقات الإتمام الفيزيائية: {len(all_cards)} من `WO-B-OPEN-COMP-{FIRST_ID:05d}` إلى `WO-B-OPEN-COMP-{last_id:05d}`؛ الانقسامات ذات الإحالة المتبادلة={sum(len(item.card_ids) == 2 for item in rendered)}.",
            f"- حصيلة أحكام المكونات، لا المركبات: {distribution}.",
            f"- أكبر بطاقة: {max(sizes)} بايت، `WO-B-OPEN-COMP-{all_cards[max_pos][0]:05d}`؛ لا بطاقة تبلغ 5KB، ولا شرطة طويلة، ولا أرقام فارسية.",
            "- مصدر التفكيك: بطاقات `persian.md` و`data/branch-lexicons/persian.json` فقط؛ رُتبت النافذة من أول حوض الهيكل الطويل المؤجل، والتفكيكات الأجنبية الداخلية لم تنقل إلى سطح الفارسية.",
            "- عطب أداة أساسية: 0؛ عملت المروحة و`all_tiers` ومسح الجذور حيث أعادت المروحة مرشحا، وسميت فجوات الصرف أو الأداة حيث لم تعده.",
            f"- آخر موضع: `WO-B-OPEN-COMP-{last_id:05d}`، المركب `{rendered[-1].compound.word}` /{rendered[-1].compound.reading}/.",
            "",
            f"<!-- {MARKER}:END -->",
            "",
            f"LANE-B DONE9 {len(rendered)} WO-B-OPEN-COMP-{last_id:05d}",
        ]
    )
    return "\n".join(lines)


def validate_existing(reading_text: str, report_text: str) -> None:
    reading_match = re.search(
        rf"<!-- {re.escape(MARKER)}:START -->(.*?)<!-- {re.escape(MARKER)}:END -->",
        reading_text,
        re.DOTALL,
    )
    if not reading_match:
        raise AssertionError("محضر الجولة التاسعة موجود بلا مقطع القراءة")
    ids = [
        int(value)
        for value in re.findall(r"^### WO-B-OPEN-COMP-(\d+):", reading_match.group(1), re.MULTILINE)
    ]
    if not ids or ids != list(range(FIRST_ID, ids[-1] + 1)):
        raise AssertionError("مقطع الجولة التاسعة الموجود غير متصل")
    for block in re.split(r"(?=^### WO-B-OPEN-COMP-)", reading_match.group(1), flags=re.MULTILINE):
        if not block.startswith("### WO-B-OPEN-COMP-"):
            continue
        if len(block.encode("utf-8")) >= CARD_LIMIT:
            raise AssertionError("بطاقة موجودة تتجاوز 5KB")
    expected = f"LANE-B DONE9 {COMPOUND_COUNT} WO-B-OPEN-COMP-{ids[-1]:05d}"
    if not report_text.rstrip().endswith(expected):
        raise AssertionError("سطر DONE9 ليس خاتمة التقرير")


def main() -> int:
    reading_text = READING.read_text(encoding="utf-8")
    report_text = REPORT.read_text(encoding="utf-8")
    if MARKER in reading_text or MARKER in report_text:
        if MARKER not in reading_text or MARKER not in report_text:
            raise AssertionError("الجولة التاسعة مودعة جزئيا")
        if "--replace" not in sys.argv[1:]:
            validate_existing(reading_text, report_text)
            print("ROUND9 COMPOUNDS ALREADY PRESENT AND VALID")
            return 0
        reading_start = f"<!-- {MARKER}:START -->"
        report_start = f"<!-- {MARKER}:START -->"
        reading_prefix, reading_tail = reading_text.split(reading_start, 1)
        report_prefix, report_tail = report_text.split(report_start, 1)
        if f"<!-- {MARKER}:END -->" not in reading_tail:
            raise AssertionError("لا نهاية لمقطع القراءة القديم")
        if f"<!-- {MARKER}:END -->" not in report_tail or "LANE-B DONE9" not in report_tail:
            raise AssertionError("لا نهاية لمحضر الجولة التاسعة القديم")
        reading_text = reading_prefix.rstrip() + "\n"
        report_text = report_prefix.rstrip() + "\n"
        # استبدال ميكانيكي لمقطع الجولة التاسعة وحده بعد تصحيح حد النافذة.
        READING.write_text(reading_text, encoding="utf-8", newline="")
        REPORT.write_text(report_text, encoding="utf-8", newline="")

    compounds = parse_compounds(reading_text)
    rendered = render_all(compounds)
    validate_rendered(rendered)
    reading_cards, summaries = batch_sections(rendered)
    reading_append = (
        f"\n\n<!-- {MARKER}:START -->\n\n"
        "## الجولة التاسعة: تفكيك المركبات الفارسية (2026-08-17)\n\n"
        "- النطاق: أول ثمانين عضوا من حوض الهيكل الطويل المؤجل، بدءا بـ`تلسکوپ`؛ دفعتان 40 و40. نقل المكونان من سطر قاموس الفرع وحده، وما لم يسمهما السطر بقي COMPOUND-BOUNDARY.\n\n"
        + reading_cards
        + f"\n<!-- {MARKER}:END -->\n"
    )
    report_append = "\n\n" + report_section(rendered, summaries) + "\n"
    reading_append = unicodedata.normalize("NFC", reading_append)
    report_append = unicodedata.normalize("NFC", report_append)

    # إلحاق مولد كبير محكوم تحققيا؛ لا يمس النص السابق ولا يعيد تنسيقه.
    with READING.open("a", encoding="utf-8", newline="") as handle:
        handle.write(reading_append)
    with REPORT.open("a", encoding="utf-8", newline="") as handle:
        handle.write(report_append)

    new_reading = READING.read_text(encoding="utf-8")
    new_report = REPORT.read_text(encoding="utf-8")
    validate_existing(new_reading, new_report)
    all_cards = [(card_id, text) for item in rendered for card_id, text in zip(item.card_ids, item.texts)]
    print("ROUND9 COMPOUNDS WRITTEN")
    print("COMPOUNDS", len(rendered), f"BATCHES={BATCH_SIZES[0]}+{BATCH_SIZES[1]}")
    print("DECOMPOSED", sum(item.decomposed for item in rendered))
    print("BOUNDARY", sum(not item.decomposed for item in rendered))
    print("PHYSICAL_CARDS", len(all_cards), f"RANGE={FIRST_ID:05d}-{all_cards[-1][0]:05d}")
    print("SPLITS", sum(len(item.card_ids) == 2 for item in rendered))
    print("MAX_CARD", max(len(text.encode("utf-8")) for _, text in all_cards))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
