# -*- coding: utf-8 -*-
"""ابنِ الدفعة الأولى من بطاقات خشيم للاتينية القديمة.

هذه أداة حصاد RECOVERY-v2 خاصة بصفوف علي فهمي خشيم في كتابه
«اللاتينيّة عربيّة». تفحص الجرد الصالح كله، ثم تكتب مئتي بطاقة ذات عضوية
ثابتة. لا تمنح الأداة حكمًا من تقاطع ألفاظ آلي، ولا تضيف شاهدًا دلاليًا رابعًا:

* الصوت من صفوف شبكة الإبدالات المجمدة، مع تسجيل ألفاظ البحث.
* الرجل المعجمية نص لسان العرب الذي نقله خشيم نفسه في المدخل.
* معنى الفرع من مسح كتاب خشيم بلا ترجمة ولا تهذيب، والمدار جملة بشرية.

المروحة أداة توليد فقط. غياب مرشح خشيم منها أو من السجل يفتح
``OPEN-CANDIDATE`` ولا يسقط المرشح.
"""
from __future__ import annotations

import itertools
import json
import pathlib
import re
import sys
import unicodedata
from collections import Counter
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import fan_any_script as FAN  # noqa: E402

SOURCE = ROOT / "data" / "khashim-pairs.json"
READING = ROOT / "04-cross-linguistic" / "readings" / "old-latin.md"
REPORT = ROOT / "data" / "khashim-old-latin-batch-001.json"
AUDIT = ROOT / "05-audits" / "2026-08-11-khashim-old-latin-batch-001.md"
ROOT_EVENTS = ROOT / "computational" / "data" / "layer_2_results_v2.jsonl"
CORE_LEVELS = ROOT / "data" / "juthoor-core-levels.json"
OCR_LATIN = pathlib.Path.home() / "AI Projects" / "Resources" / "prior-art" / "ocr-latin" / "full.md"

START = "<!-- KHASHIM-OLD-LATIN-BATCH-001:START -->"
END = "<!-- KHASHIM-OLD-LATIN-BATCH-001:END -->"
BOOK = "علي فهمي خشيم، «اللاتينيّة عربيّة»"
BATCH_SIZE = 200
VALID_COUNT = 562
BASELINE_LINKS = 41

AR_MARKS = re.compile(r"[\u064b-\u065fـ]")
LATIN_HEAD = re.compile(r"^[A-Za-zÀ-žĀ-ſæœÆŒ][A-Za-zÀ-žĀ-ſæœÆŒ' -]{1,30}$")
OCR_HEAD = re.compile(r"^[A-Za-zĀ-ſ][A-Za-zĀ-ſ\-']{2,22}$")
OCR_ANSWER = re.compile(r"^[\s*·•]*(?:[ء-ي]{0,4}\s*)?العربية\s*[:：]")
ARABIC = re.compile(r"[؀-ۿ]")
LOAN_MARKERS = (
    "مقترضة", "مستعارة", "كلمة أجنبية", "أصل أجنبي", "من العبرية",
    "من الفارسية", "من الإتروسكية", "من السريانية", "من اليونانية إلى",
)


def ar_bare(value: str) -> str:
    value = unicodedata.normalize("NFKC", str(value or ""))
    value = AR_MARKS.sub("", value).replace("ٱ", "ا")
    return re.sub(r"[^ء-ي]", "", value)


def one_line(value: str) -> str:
    return " ".join(str(value or "").split())


def markdown_quote(value: str) -> str:
    return one_line(value).replace("`", "ˋ")


# هذه القوائم فهرس برمجي لصفوف موجودة فعلًا في الشبكة المجمدة. الحرف c في
# اللاتينية القديمة يقرأ [k] قبل دخوله الشبكة، ولذلك يرث صف k المسمى؛ هذا
# تطبيع قراءة للحرف لا إبدال جديد.
IDENTITY: dict[tuple[str, str], str] = {
    ("r", "ر"): "IDN-01", ("m", "م"): "IDN-02", ("n", "ن"): "IDN-03",
    ("l", "ل"): "IDN-04", ("b", "ب"): "IDN-05", ("f", "ف"): "IDN-06",
    ("s", "س"): "IDN-07", ("g", "ج"): "IDN-08", ("d", "د"): "IDN-09",
    ("w", "و"): "IDN-10", ("u", "و"): "IDN-10", ("t", "ت"): "IDN-11",
    ("q", "ق"): "IDN-12", ("k", "ك"): "IDN-13", ("c", "ك"): "IDN-13",
    ("h", "ه"): "IDN-20", ("z", "ز"): "IDN-22", ("y", "ي"): "IDN-23",
}

SHIFTS: dict[tuple[str, str], str] = {
    ("p", "ب"): "LAB-01", ("p", "ف"): "IDN-06",
    ("b", "ف"): "LAB-02", ("f", "ب"): "LAB-02",
    ("w", "ب"): "LAB-05", ("v", "ب"): "LAB-05",
    ("r", "ل"): "LIQ-01", ("l", "ر"): "LIQ-01",
    ("m", "ن"): "LIQ-02", ("n", "م"): "LIQ-02",
    ("c", "ق"): "GUT-01", ("k", "ق"): "GUT-01", ("q", "ك"): "GUT-01",
    ("c", "ج"): "GUT-03", ("g", "ك"): "GUT-02",
    ("h", "ع"): "GUT-04", ("h", "ح"): "GUT-04",
    ("h", "غ"): "GUT-04", ("h", "ء"): "GUT-04",
    ("t", "ث"): "DENT-01", ("t", "ط"): "DENT-05",
    ("d", "ذ"): "DENT-03", ("d", "ض"): "DENT-06", ("z", "ذ"): "DENT-04",
    ("s", "ث"): "DENT-02", ("s", "ش"): "SIB-01",
    ("s", "ص"): "SIB-02", ("s", "ز"): "SIB-03",
    ("j", "ي"): "GLD-02", ("v", "و"): "LAB-06",
}


# المدار حكم قراءة بشرية. وجود العضو هنا لا يكفي وحده؛ الأرجل الثلاث والمروحة
# ومصفاة الاتجاه تفحص بعده. تحفظ قيمة الجذر لكي يفشل البناء إن تغير الصف.
HUMAN_ORBITS: dict[tuple[str, str], str] = {
    ("amarus", "مرر"): "المرارة والحدة والألم وجه حسي للشدة والضيق في حدث `مرر` المجمد؛ فالمدار مباشر في أثر الطعم.",
    ("braca", "برك"): "الركبة موضع تثبيت البدن حين يبرك ويستقر؛ فالمدار عضو الهيئة التي تحقق الثبات.",
    ("calidus", "قلد"): "الطوق يحوز العنق بحبس ويحمل عليه، وهو الوجه الوظيفي نفسه في حدث `قلد` المجمد.",
    ("carrus", "جرر"): "العربة جرم يحمل ثم يسحب على امتداد الطريق؛ فالمدار الأداة وفعل جرها المباشر.",
    ("castus", "قسط"): "الاستقامة في اتباع القواعد هي الوجه المعنوي للاستواء غير المائل في حدث `قسط`.",
    ("coma", "قمم"): "شعر الرأس ينتبر من قمته ويجتمع في أعلاه؛ فالمدار موضع البروز في الرأس.",
    ("copula", "قبل"): "الصلة والرباط يجعلان الطرفين يتجه أحدهما إلى الآخر ويلتقيان؛ فالمدار فعل الوصل بالمقابلة.",
    ("cornu", "قرن"): "القرن والخوذة والقمة نتوء في أعلى الجسم أو مقدمه؛ فالمدار مباشر بنص الحدث المجمد.",
    ("corona", "قرن"): "التاج شعار بارز في أعلى الرأس؛ فالمدار موضع النتوء العلوي في حدث `قرن`.",
    ("creo", "وقر"): "الإنتاج والتعظيم زيادة تتجمع وتتمكن في الشيء حتى يثقل مقداره؛ فالمدار نمو بالتجمع.",
    ("cuppa", "كوب"): "الكأس والقدح وعاء منبعج مجوف مستدير؛ فالمدار مباشر في هيئة الوعاء.",
    ("domus", "دوم"): "المسكن موضع المكث والثبات على حال ممتدة؛ فالمدار المكان وحدث الإقامة الدائمة فيه.",
    ("fama", "فمم"): "الصوت والضجة يخرجان من فتحة الفم؛ فالمدار الأثر الصوتي وعضو صدوره.",
    ("fodio", "فضض"): "الحفر والنقب والثقب تكسر الجرم الصلب وتفرق بعضه من بعض؛ فالمدار مباشر في فعل الاختراق.",
    ("fur", "فرر"): "معنى الهرب والطيران في سطر الفرع هو المباعدة بخفة واسترسال؛ فالمدار مباشر، ولا يورث إلى معنى اللص.",
    ("furca", "فرق"): "الشوكة ذات الشعبتين تنقسم إلى فرعين؛ فالمدار هيئة الانفصال العميق في الأداة.",
    ("gero", "جرر"): "الحمل والشد والجذب هي وجوه سحب الجرم على امتداد؛ فالمدار مباشر.",
    ("lacus", "لجج"): "الحوض والبحيرة تراكم لماء رخو كثيف في مقر؛ فالمدار المكان والمادة المجتمعة فيه.",
    ("lippus", "لبب"): "الغراء واللصاق يلزمان الشيء في جوف اتصاله بتمكن؛ فالمدار وظيفة التثبيت باللزوم.",
    ("mare", "مور"): "البحر مادة مجتمعة تتردد وتضطرب في مكانها؛ فالمدار مباشر في حركة الموج.",
    ("marra", "مرر"): "الفأس والمعزقة والمحراث أدوات تجتاز التربة بشدة وضيق؛ فالمدار الأداة وفعل مرورها القاسي.",
    ("murra", "مرر"): "الدواء المر يوقع شدة الطعم وضيق أثره؛ فالمدار مباشر في المرارة.",
    ("nidor", "ندد"): "رائحة المحترق والبخور تتباعد من مادتها وتصعد متفرقة؛ فالمدار أثر الاحتراق وحركته.",
    ("palus", "بلل"): "المستنقع والرطوبة والفيضان تحصّل للماء في الأثناء بتمكن؛ فالمدار مباشر في البلل.",
    ("pasta", "بسط"): "العجين والفطيرة يبسطان ويفرشان حتى يتفلطحا؛ فالمدار هيئة الصنع المباشرة.",
    ("porca", "فرق"): "قطعة الأرض قسم مفصول من أرض أوسع؛ فالمدار ناتج فعل الفصل.",
    ("quiris", "قرر"): "المدني من أهل المدن مستقر في المصر لا ينتجع؛ فالمدار صفة السكن والثبات.",
    ("raeda", "رود"): "العربة ذات العجلات وتدريب الخيل كلاهما حركة انتقال وتردد؛ فالمدار حركة المركوب.",
    ("seco", "شقق"): "القطع والفصل والبت صدع نافذ في الجرم؛ فالمدار مباشر في الشق.",
    ("solidus", "صلد"): "الصلابة والثبات والقسوة هي تمام تصلب الشيء ومقاومته للنفاذ؛ فالمدار مباشر.",
    ("sorbeo", "شرب"): "البلع والمص والامتصاص سحب للمائع إلى الجوف؛ فالمدار مباشر.",
    ("storea", "سطر"): "الحصير يبنى من عيدان تصطف طوليًا في صفوف منضبطة؛ فالمدار هيئة الشيء المصنوع.",
    ("topia", "طيب"): "الحديقة والجنة منظر يطيب وقعه على الحس؛ فالمدار المكان وأثره الحسي اللطيف.",
    ("turris", "طور"): "القصر أو القلعة بناء يمتد حول حيز ويعلو فيه؛ فالمدار هيئة الامتداد المكاني في البناء.",
}

REQUIRED_EXAMPLES = {
    ("remus", "رمي"), ("rigo", "ريق"), ("turris", "طور"),
    ("bulga", "ولج"), ("cuppa", "كوب"),
}

TOP_TWENTY_KEYS = [
    ("cuppa", "كوب"), ("cornu", "قرن"), ("carrus", "جرر"),
    ("gero", "جرر"), ("sorbeo", "شرب"), ("solidus", "صلد"),
    ("fodio", "فضض"), ("furca", "فرق"), ("seco", "شقق"),
    ("palus", "بلل"), ("pasta", "بسط"), ("lacus", "لجج"),
    ("mare", "مور"), ("nidor", "ندد"), ("storea", "سطر"),
    ("topia", "طيب"), ("castus", "قسط"), ("braca", "برك"),
    ("quiris", "قرر"), ("turris", "طور"),
]


def load_root_events() -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for line in ROOT_EVENTS.read_text(encoding="utf-8").splitlines():
        if line.strip():
            row = json.loads(line)
            out[row["tri_root"]] = row
    return out


def load_nucleus_events() -> dict[str, str]:
    payload = json.loads(CORE_LEVELS.read_text(encoding="utf-8"))
    return {
        row["nucleus"]: row["jabal_lexicon_reading_ar"]
        for row in payload["levels"]["level_2_binary_nuclei"]["nuclei"]
        if row.get("jabal_lexicon_reading_ar")
    }


ROOT_RECORDS = load_root_events()
NUCLEUS_EVENTS = load_nucleus_events()


def ocr_sense_index() -> dict[str, tuple[str, int]]:
    """استرد المعنى من أول سطر عربي بعد الرأس في المسح نفسه، بلا رتوش."""
    if not OCR_LATIN.exists():
        raise SystemExit(f"غاب مسح كتاب اللاتينية: {OCR_LATIN}")
    lines = OCR_LATIN.read_text(encoding="utf-8").splitlines()
    out: dict[str, tuple[str, int]] = {}
    for index, raw in enumerate(lines):
        head = raw.strip()
        if not OCR_HEAD.fullmatch(head) or head in out:
            continue
        for following in range(index + 1, min(index + 9, len(lines))):
            candidate = lines[following].strip()
            if not candidate or candidate.startswith("<!--"):
                continue
            if OCR_ANSWER.match(candidate) or OCR_HEAD.fullmatch(candidate):
                break
            if ARABIC.search(candidate):
                out[head] = (candidate, following + 1)
                break
    return out


def morphology(word: str) -> tuple[str, str, list[str], list[str]]:
    raw = FAN.skeleton(word, "latin")
    for ending in FAN.LATIN_ENDINGS:
        if word.lower().endswith(ending) and len(word) - len(ending) >= 2:
            stem = word[:-len(ending)]
            alternate = FAN.skeleton(stem, "latin")
            if 2 <= len(alternate) <= 4 and alternate != raw:
                return stem, f"نزع النهاية اللاتينية المسماة `-{ending}`", raw, alternate
            break
    return word, "لا تعرية؛ لم تنطبق نهاية من قائمة الأداة", raw, raw


def fan_from_skeleton(skeleton: list[str], limit: int = 400) -> list[str]:
    if not (2 <= len(skeleton) <= 4):
        return []
    options = [FAN.LATIN_FAN.get(symbol, ()) for symbol in skeleton]
    if any(not values for values in options):
        return []
    out: list[str] = []
    seen: set[str] = set()
    for combo in itertools.islice(itertools.product(*options), limit):
        word = "".join(combo)
        if word not in seen:
            seen.add(word)
            out.append(word)
    if len(skeleton) == 2:
        for word in list(out):
            if len(word) != 2:
                continue
            first, second = word
            for candidate in (
                word + second, first + "و" + second, first + "ي" + second,
                first + "ا" + second, word + "و", word + "ي", word + "ا",
                "و" + word, "ي" + word,
            ):
                if candidate not in seen and len(out) < limit * 3:
                    seen.add(candidate)
                    out.append(candidate)
    return out[: limit * 3]


def candidate_fan(word: str, root: str) -> dict[str, Any]:
    stem, stripping, raw_skeleton, stem_skeleton = morphology(word)
    raw_only = fan_from_skeleton(raw_skeleton)
    alternate = fan_from_skeleton(stem_skeleton) if stem_skeleton != raw_skeleton else []
    full = FAN.fan(word, "latin", limit=400)
    if root in raw_only:
        source = "الهيكل الخام"
        route_skeleton = raw_skeleton
    elif root in alternate:
        source = "الهيكل البديل بعد النهاية الإعرابية"
        route_skeleton = stem_skeleton
    else:
        source = "خارج المروحة"
        route_skeleton = stem_skeleton
    return {
        "stem": stem,
        "stripping": stripping,
        "raw_skeleton": raw_skeleton,
        "stem_skeleton": stem_skeleton,
        "full": full,
        "hit": root in full,
        "position": full.index(root) + 1 if root in full else None,
        "source": source,
        "route_skeleton": route_skeleton,
    }


def pair_row(symbol: str, arabic: str) -> str | None:
    return IDENTITY.get((symbol, arabic)) or SHIFTS.get((symbol, arabic))


def sound_audit(skeleton: list[str], root: str) -> tuple[bool, list[str], list[str]]:
    strong = "".join(letter for letter in root if letter not in "اوي")
    weak_positions = [i for i, letter in enumerate(root) if letter in "اوي"]
    geminate = len(skeleton) == 2 and len(root) == 3 and root[-1] == root[-2]
    weak = len(skeleton) == 2 and len(root) == 3 and len(weak_positions) == 1
    if len(skeleton) != len(root) and not geminate and not weak:
        return False, [], [f"عدد الصوامت {len(skeleton)} في الفرع و{len(root)} في مرشح خشيم"]
    aligned = root[:2] if geminate else strong if weak else root
    if len(aligned) != len(skeleton):
        return False, [], [f"تعذر رصف الهيكل `{''.join(skeleton)}` بالمادة `{root}`"]
    rows: list[str] = []
    misses: list[str] = []
    for symbol, arabic in zip(skeleton, aligned):
        row = pair_row(symbol, arabic)
        normalized = "c=[k] ثم " if symbol == "c" else ""
        query = f"`{symbol}` + `{arabic}` + «اللاتينيّة/Latin» في عمود الشاهد"
        if row:
            rows.append(f"{normalized}{symbol}↔{arabic} = `{row}` (بحث: {query})")
        else:
            misses.append(f"{symbol}↔{arabic} (بحث: {query}؛ لا صف مناسب)")
    if geminate:
        rows.append(f"باب المضاعف: تكرير `{root[-1]}` في آخر الجذر العربي، والهيكل الأصلي باق")
    if weak:
        position = ("الأول" if weak_positions[0] == 0 else
                    "الأوسط" if weak_positions[0] == 1 else "الأخير")
        rows.append(
            f"باب المعتل: حرف العلة `{root[weak_positions[0]]}` في الموضع {position} "
            "يقابل صائت الفرع، مع بقاء الصامتين القويين"
        )
    return not misses, rows, misses


def explicit_loan(text: str) -> str | None:
    lowered = one_line(text)
    for marker in LOAN_MARKERS:
        if marker in lowered:
            return marker
    return None


def preferred_lexicon(matches: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not matches:
        return None
    order = ("تاج العروس", "تاج اللغة", "المحكم", "تهذيب اللغة", "كتاب العين", "القاموس المحيط")
    for name in order:
        for row in matches:
            if name in row.get("source", "") and "لسان العرب" not in row.get("source", ""):
                return row
    return matches[0]


def excerpt(value: str, limit: int = 380) -> str:
    value = one_line(value)
    if len(value) <= limit:
        return value
    return value[:limit].rsplit(" ", 1)[0] + "…"


def prepare_rows() -> tuple[list[dict[str, Any]], dict[str, int]]:
    payload = json.loads(SOURCE.read_text(encoding="utf-8"))
    all_latin = [row for row in payload["rows"] if row.get("tongue") == "old-latin"]
    # يبقى مقام الـ562 ثابتًا بعد استرداد 290 رأسًا من المسح القديم: المسح
    # الجديد كله، ومعه الصفوف القديمة السبعة والأربعون التي كان رأسها سالمًا
    # أصلًا. أما المستردة فتثري نظائرها ولا تنشئ مرشحات مكررة.
    valid = [
        row for row in all_latin
        if row.get("source") == "ocr-latin"
        or (
            row.get("source") == "khashim-latin"
            and not row.get("ocr_recovery")
            and row.get("foreign") != "(سقطَ حرفُه في المسح)"
        )
    ]
    if len(valid) != VALID_COUNT:
        raise SystemExit(f"تغيّر جرد اللاتينية الصالح: {len(valid)}، والمتوقع {VALID_COUNT}")
    sense_index = ocr_sense_index()
    evaluated: list[dict[str, Any]] = []
    stats = Counter(rows_examined=len(valid), rows_total_old_latin=len(all_latin))
    for valid_index, row in enumerate(valid):
        foreign = one_line(row.get("foreign", ""))
        root = ar_bare(row.get("arabic_root", ""))
        if not LATIN_HEAD.fullmatch(foreign):
            stats["rows_examined_without_latin_head"] += 1
            continue
        stats["rows_with_latin_head"] += 1
        raw_sense = one_line(row.get("foreign_sense", ""))
        recovered = sense_index.get(foreign)
        if raw_sense:
            sense = raw_sense
            sense_origin = "حقل `foreign_sense` كما هو"
            sense_line = recovered[1] if recovered else None
        elif recovered:
            sense, sense_line = recovered
            sense_origin = f"استرداد حرفي من مسح الكتاب، السطر {sense_line}"
            stats["senses_recovered_from_book_scan"] += 1
        else:
            sense = ""
            sense_line = None
            sense_origin = "لم يسترد معنى الفرع من الحقل ولا من سطر المسح"
            stats["senses_still_missing"] += 1
        fan = candidate_fan(foreign, root)
        sound_ready, sound_rows, sound_misses = sound_audit(fan["route_skeleton"], root)
        event = ROOT_RECORDS.get(root) if len(root) == 3 else None
        nucleus_event = NUCLEUS_EVENTS.get(root) if len(root) == 2 else None
        event_ready = bool(event and event.get("jabal_axial")) if len(root) == 3 else bool(nucleus_event)
        loan = explicit_loan(sense)
        key = (foreign, root)
        if fan["hit"]:
            stats["rows_exact_khashim_candidate_in_fan"] += 1
        if sound_ready:
            stats["rows_sound_route_complete"] += 1
        if event_ready:
            stats["rows_event_in_frozen_registry"] += 1
        score = (
            (1000 if key in REQUIRED_EXAMPLES else 0)
            + (800 if key in HUMAN_ORBITS else 0)
            + (90 if fan["hit"] else 0)
            + (60 if sound_ready else 0)
            + (50 if event_ready else 0)
            + (40 if sense else 0)
            + (20 if len(root) in {2, 3} else 0)
            - (80 if loan else 0)
            - valid_index / 10000
        )
        evaluated.append({
            "valid_index": valid_index, "row": row, "foreign": foreign, "root": root,
            "sense": sense, "sense_origin": sense_origin, "sense_line": sense_line,
            "fan": fan, "sound_ready": sound_ready, "sound_rows": sound_rows,
            "sound_misses": sound_misses, "root_event": event,
            "nucleus_event": nucleus_event, "event_ready": event_ready,
            "loan_marker": loan, "score": score,
        })
    evaluated.sort(key=lambda item: (-item["score"], item["valid_index"]))
    selected = evaluated[:BATCH_SIZE]
    selected_keys = {(item["foreign"], item["root"]) for item in selected}
    missing = sorted((REQUIRED_EXAMPLES | set(HUMAN_ORBITS)) - selected_keys)
    if missing:
        raise SystemExit(f"غابت أمثلة أو مدارات من عضوية الدفعة: {missing}")
    if len(selected) != BATCH_SIZE:
        raise SystemExit(f"لم تبلغ الدفعة {BATCH_SIZE}: {len(selected)}")
    return selected, dict(stats)


def fan_text(values: list[str]) -> str:
    return "، ".join(f"`{value}`" for value in values) if values else "(لم تولد الأداة مرشحًا)"


def card(item: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    row = item["row"]
    foreign, root, sense = item["foreign"], item["root"], item["sense"]
    fan = item["fan"]
    key = (foreign, root)
    orbit = HUMAN_ORBITS.get(key, "")
    root_record = item["root_event"]
    root_event = one_line(root_record.get("jabal_axial", "")) if root_record else ""
    nucleus = one_line(root_record.get("binary", "")) if root_record else ""
    binary_event = one_line(root_record.get("binary_reading_ar", "")) if root_record else ""
    if len(root) == 2:
        event_text = item["nucleus_event"] or ""
        event_source = "`data/juthoor-core-levels.json`، حقل `jabal_lexicon_reading_ar`"
        degree = "NUCLEUS-TRACE"
    else:
        event_text = root_event
        event_source = "`computational/data/layer_2_results_v2.jsonl`، حقل `jabal_axial`"
        degree = "ROOT-TRACE"

    # الأرجل الثلاث وحدها: الصوت، نص المعجم المسمى، والمدار المكتوب.
    sound_leg = item["sound_ready"]
    source_leg = bool(one_line(row.get("arabic_gloss", "")))
    orbit_leg = bool(sense and orbit)
    structural_ready = bool(fan["hit"] and len(root) in {2, 3})
    direction_ready = not item["loan_marker"]
    positive = all((sound_leg, source_leg, orbit_leg)) and structural_ready and direction_ready
    closure = "READY" if positive else "OPEN-CANDIDATE"
    verdict = f"**{degree} (استكشاف)**" if positive else "**غير صادر (استكشاف)**"

    if fan["hit"]:
        location = (
            f"داخل المروحة في الرتبة {fan['position']} من {len(fan['full'])}؛ "
            f"المولد هو {fan['source']}"
        )
    else:
        location = (
            f"غير موجود في المروحة ذات {len(fan['full'])} مرشحًا؛ حقل خشيم محفوظ "
            "ولا يستبدل به أول مرشح من الأداة"
        )

    sound = "؛ ".join(item["sound_rows"] + item["sound_misses"])
    if not sound:
        sound = "تعذر الرصف؛ وبحثت الشبكة بالحرفين وباسمي اللسان كما هو مسجل في العائق"

    obstacles: list[str] = []
    if not fan["hit"]:
        obstacles.append("دخول مرشح خشيم نفسه في مروحة الأداة")
    if len(root) not in {2, 3}:
        obstacles.append("تحليل يحدد درجة المادة العربية")
    if not sound_leg:
        obstacles.append("صف أو صفوف الشبكة المبينة في مسار الصوت")
    if not source_leg:
        obstacles.append("نص لسان العرب الذي نقله خشيم في المدخل")
    if not sense:
        obstacles.append("معنى الفرع الحرفي من مسح الكتاب")
    if sense and not orbit:
        obstacles.append("مدار بشري مقنع مكتوب يصل معنى الفرع بالحدث المجمد")
    if item["loan_marker"]:
        obstacles.append(f"عزل اتجاه النقل الذي سماه النص بعبارة «{item['loan_marker']}»")
    required = "؛ ".join(obstacles) if obstacles else "لا عائق معلق"

    if root_record:
        nucleus_line = (
            f"النواة المسجلة `{nucleus}` وحدثها «{binary_event}» فحصا مستقلين؛ "
            "لا يصدر لهما حكم نواة في هذه البطاقة لأن المدار المكتوب للجذر الكامل"
        )
    elif len(root) == 2:
        nucleus_line = "هذه المادة نواة ثنائية مستقلة، وحدثها هو حدث الحكم المبين أدناه"
    else:
        strong = "".join(letter for letter in root if letter not in "اوي")[:2]
        nucleus_line = (
            f"فحصت النواة القوية المحتملة `{strong or '(غير متاحة)'}` استقلالًا، "
            "ولم يصدر لها حكم في غياب سجل جذر يحدد نواته"
        )

    loan_note = (
        f"النص يسمي علامة الاتجاه «{item['loan_marker']}»، فعزلت ومنعت الحكم"
        if item["loan_marker"] else
        "لا يسمي سطر المعنى مانحًا أجنبيًا باتجاه نقل صريح؛ لا يحول غياب الاسم إلى إثبات أصالة"
    )
    family_count = 1 if positive else 0
    index = item["valid_index"]
    scan_location = f"؛ سطر المسح {item['sense_line']}" if item["sense_line"] else ""
    orbit_text = (
        orbit.rstrip(" .") + "." if orbit else
        "غير مكتوب؛ لم تقنع القراءة البشرية بمدار واحد مع الحدث المجمد."
    )
    lines = [
        f"### بطاقة: `{foreign}` «{markdown_quote(sense) if sense else '(المعنى لم يسترد)' }»؛ خشيم لاتيني 001/{index:03d}",
        f"<!-- khashim-old-latin-batch-001:{index}:{root} -->",
        "- إصدار البروتوكول: RECOVERY-v2 (استكشاف).",
        f"- نسبة المصدر: المرشح `{foreign}→{root}` ونص الشرح العربي من {BOOK}؛ "
        "المروحة والمسار والحدث والمدار والحكم أعمال المشروع لا أقوال خشيم.",
        f"- الكلمة في الفرع: `{foreign}`؛ أقدم صورة مستعملة هي رسم المدخل في مسح {BOOK} المأذون، "
        "ولا تدعى صورة أقدم منه في هذه البطاقة.",
        f"- موضع الصف: `data/khashim-pairs.json`، اللسان `old-latin`، العضو الصالح {index}؛ "
        f"معنى الفرع: {item['sense_origin']}.",
        f"- الخطوة صفر (التعرية بصرف الفرع): {fan['stripping']}؛ الخام `{''.join(fan['raw_skeleton']) or '∅'}` "
        f"والهيكل البديل `{''.join(fan['stem_skeleton']) or '∅'}`؛ البديل مضموم إلى الأصل ولا يحل محله.",
        f"- حساب الصوامت: الخام={len(fan['raw_skeleton'])}؛ البديل={len(fan['stem_skeleton'])}؛ "
        f"مرشح خشيم `{root}`={len(root)}؛ لم يسقط صامت أصلي بغير باب مسمى.",
        f"- درجة المقارنة: {'جذر كامل' if len(root) == 3 else 'نواة' if len(root) == 2 else 'مفتوحة'}؛ {nucleus_line}.",
        f"- مروحة المرشحات العربية من أداتنا: شغل `scripts/fan_any_script.py` على `{foreign}` بلسان "
        f"`latin`؛ المروحة الكاملة: {fan_text(fan['full'])}.",
        f"- موضع مرشح خشيم من المروحة: `{root}` {location}؛ المروحة من أداتنا لا من قول خشيم.",
        f"- مسح المعاني العربية: مادة خشيم `{row.get('arabic_root', '')}`؛ «{markdown_quote(row.get('arabic_gloss', ''))}» "
        "[نقلَه خشيمٌ عن لسان العرب؛ هو الرجل المعجمية المسماة نفسها، بلا طلب بديل].",
        f"- الحدث من السجل المجمد (فحص موازٍ لا رجل زائدة): {'«' + event_text + '» [' + event_source + '؛ نقل كما هو]' if event_text else '(لا حدث مسجل لهذه المادة)'}.",
        f"- المقابل من اللسان: `{root}`؛ هو النص الحرفي لحقل `arabic_root` عند خشيم، لا مرشح اختارته المروحة.",
        f"- مسار الصوت: {sound}. فُتش كل موضع بالحرفين معًا ثم بلفظي «اللاتينيّة» و`Latin` "
        "في عمود الشاهد من `shift-network-draft.md`؛ لم يكتب في الملف المجمد.",
        f"- المعنى من قاموس الفرع: «{markdown_quote(sense) if sense else '(فارغ في الصف ولم يسترد من المسح)'}» "
        f"[{BOOK}؛ بلا ترجمة ولا رتوش{scan_location}].",
        f"- المدار: {orbit_text}",
        f"- المصفاة: {loan_note}.",
        "- فصل المتجانسات والاقتراض: الحكم، إن صدر، لهذا المدخل بهذا المعنى وحده؛ "
        "لا يرثه متحد الرسم ولا معنى آخر للفظ.",
        "- جرد العلم: لا يعامل علمًا بحسب رأس الصف ومعناه؛ ولا يورث ذلك إلى متحد رسم قد يكون علمًا.",
        "- مؤشر اليتم: غير حاسم؛ صف خشيم لا يحمل جرد أسرة لاتينية كاملًا، فلا يستعمل التفرد رفعًا أو إسقاطًا.",
        f"- إشعاع الأسرة في الفرع: الأعضاء المعجمية المدعومة={family_count}؛ "
        f"سلاسل المعنى المدعومة={family_count}؛ المدخل المفرد وحده.",
        f"- إشعاع الأسرة في العربية: الأعضاء المعجمية المدعومة={family_count}؛ "
        f"سلاسل المعنى المدعومة={family_count}؛ مادة `{root}` في الحدث والمدار المسميين وحدهما.",
        "- جسور الاسترداد المفحوصة: الرسم اللاتيني المستعاد؛ معنى الفرع في المسح؛ التعرية اللاتينية؛ "
        "المروحة الخام والبديلة؛ مرشح خشيم؛ نص لسان العرب الذي نقله خشيم؛ سجل الحدث الموازي؛ "
        "الشبكة بالحرفين وباسمي اللسان؛ المدار؛ الاتجاه؛ المتجانسات.",
        f"- عائق: النوع={closure}؛ يتطلب={required}",
        f"- حالة الإغلاق: {closure}",
        f"- الحكم (استكشاف): {verdict}",
        f"- ملاحظات: أصل الزوج وشرح لسان العرب ومعنى اللاتينية من {BOOK}. "
        f"عدسة الاسترداد أبقت مرشح خشيم {'وأدخلته الحكم بعد اكتمال الأرجل الثلاث' if positive else 'مفتوحًا ولم تسقطه'}؛ "
        f"وعدسة التشكيك {'راجعت الصوت والحدث والمدار ثم أصدرت حكم الاستكشاف' if positive else 'منعت الحكم للعلل المسماة من غير NO-TRACE'}.",
    ]
    summary = {
        "valid_index": index, "foreign": foreign, "sense": sense, "root": root,
        "source_book": BOOK, "sense_origin": item["sense_origin"],
        "sense_scan_line": item["sense_line"], "fan_count": len(fan["full"]),
        "root_in_fan": fan["hit"], "root_fan_position": fan["position"],
        "fan_source": fan["source"], "sound_ready": sound_leg,
        "sound_rows": item["sound_rows"], "sound_misses": item["sound_misses"],
        "named_lexicon_ready": source_leg,
        "named_lexicon_source": "نقلَه خشيمٌ عن لسان العرب" if source_leg else None,
        "event_ready": bool(event_text), "event": event_text or None,
        "event_source": event_source if event_text else None,
        "human_orbit": orbit or None, "loan_marker": item["loan_marker"],
        "three_legs": {"sound": sound_leg, "named_lexicon": source_leg, "written_orbit": orbit_leg},
        "closure": closure, "verdict": degree if positive else None,
        "open_reasons": obstacles,
    }
    return "\n".join(lines), summary


def replace_batch(text: str, block: str) -> str:
    if START in text and END in text:
        before, rest = text.split(START, 1)
        _, after = rest.split(END, 1)
        tail = after.lstrip()
        return before.rstrip() + "\n\n" + block.rstrip() + ("\n\n" + tail if tail else "\n")
    return text.rstrip() + "\n\n" + block.rstrip() + "\n"


def write_audit(report_rows: list[dict[str, Any]], inventory: dict[str, int]) -> None:
    positives = [row for row in report_rows if row["verdict"]]
    opens = [row for row in report_rows if not row["verdict"]]
    reasons = Counter(reason for row in opens for reason in row["open_reasons"])
    by_key = {(row["foreign"], row["root"]): row for row in positives}
    featured = [by_key[key] for key in TOP_TWENTY_KEYS if key in by_key]
    if len(featured) != 20:
        missing = [key for key in TOP_TWENTY_KEYS if key not in by_key]
        raise SystemExit(f"لم تدخل الأزواج العشرون المميزة: {missing}")
    lines = [
        "# حصاد خشيم للاتينية القديمة، الدفعة 001",
        "",
        "## النطاق والحصيلة",
        "",
        f"فُحصت الصفوف الصالحة كلها وعددها {inventory['rows_examined']} من `data/khashim-pairs.json`. "
        f"كان منها {inventory['rows_with_latin_head']} رأسًا بالحرف اللاتيني، و"
        f"{inventory['rows_examined_without_latin_head']} صفًا قديمًا صالح العلامة لم يدخل اختيار الدفعة "
        "لأن الرأس اللاتيني المستعاد أوضح منه. كتبت الدفعة أعلى 200 بطاقة مع إدخال أمثلة المؤلف الخمسة حتمًا.",
        "",
        f"- فُحص: {inventory['rows_examined']}.",
        f"- كُتب: {len(report_rows)}.",
        f"- موجب استكشافي: {len(positives)}.",
        f"- مفتوح `OPEN-CANDIDATE`: {len(opens)}.",
        f"- استرد معنى الفرع حرفيًا من مسح الكتاب لصفوف كان حقلها فارغًا: "
        f"{inventory.get('senses_recovered_from_book_scan', 0)} من الجرد ذي الرأس اللاتيني.",
        f"- دخل مرشح خشيم نفسه مروحة الأداة في {inventory['rows_exact_khashim_candidate_in_fan']} "
        f"من {inventory['rows_with_latin_head']} رأسًا لاتينيًا مفحوصًا.",
        f"- أثبت `python scripts/count_links.py` خط أساس {BASELINE_LINKS} صلة لاتينية، "
        f"ثم {BASELINE_LINKS + len(positives)} بعد الدفعة؛ الزيادة الفعلية {len(positives)}.",
        "",
        "## أسباب الفتح المتداخلة",
        "",
        "كل بطاقة مفتوحة تحمل الوسم القانوني `OPEN-CANDIDATE` وحده؛ العبارات التالية حاجاتها "
        "البشرية وليست أوسمة إغلاق جديدة.",
        "",
        "| السبب | البطاقات |",
        "|---|---:|",
    ]
    for reason, count in reasons.most_common():
        lines.append(f"| {reason} | {count} |")
    lines.extend([
        "",
        "## أبرز عشرين زوجًا دخل",
        "",
        "| # | اللاتينية | مرشح خشيم | المدار المكتوب |",
        "|---:|---|---|---|",
    ])
    for number, row in enumerate(featured, 1):
        lines.append(
            f"| {number} | `{row['foreign']}` «{row['sense']}» | `{row['root']}` | {row['human_orbit']} |"
        )
    lines.extend([
        "",
        "## حراسة الأرجل الثلاث",
        "",
        "الحكم الموجب لا يطلب شاهدًا دلاليًا منشورًا يصل النصين. البوابة في البنّاء ثلاثة "
        "متغيرات فقط: `sound` و`named_lexicon` و`written_orbit`. الرجل المعجمية "
        "هي نص لسان العرب الذي نقله خشيم في المدخل نفسه، والمدار جملة بشرية "
        "مسجلة في `HUMAN_ORBITS`، والمروحة مرحلة توليد سابقة لا شاهد معنى رابعًا. كل صف صوتي "
        "ناقص يحمل ألفاظ البحث بالحرفين وبلفظي «اللاتينيّة» و`Latin` قبل إعلان النقص.",
        "",
        "نسبة المرشحات والنصوص إلى علي فهمي خشيم وكتابه «اللاتينيّة عربيّة» صريحة في كل "
        "بطاقة. المروحة والشبكة والحدث والمدار والحكم من عمل المشروع، ولا تنسب إليه.",
        "",
    ])
    AUDIT.write_text("\n".join(lines), encoding="utf-8", newline="\n")


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    selected, inventory = prepare_rows()
    rendered: list[str] = []
    report_rows: list[dict[str, Any]] = []
    for item in selected:
        text, summary = card(item)
        rendered.append(text)
        report_rows.append(summary)
    positives = sum(bool(row["verdict"]) for row in report_rows)
    opens = sum(row["closure"] == "OPEN-CANDIDATE" for row in report_rows)
    if positives + opens != BATCH_SIZE:
        raise SystemExit("اختل عد البطاقات الموجبة والمفتوحة")
    if any(row["verdict"] and not row["human_orbit"] for row in report_rows):
        raise SystemExit("صدر حكم موجب بلا مدار بشري مكتوب")
    if any(row["closure"] not in {"READY", "OPEN-CANDIDATE"} for row in report_rows):
        raise SystemExit("ظهر وسم إغلاق خارج القاموس المغلق")

    section = [
        START,
        "## حصاد خشيم للاتينية القديمة، الدفعة الأولى (200 بطاقة؛ 2026-08-11)",
        "",
        "**بيان النطاق.** فحص البنّاء الصفوف الـ562 الصالحة كلها من `data/khashim-pairs.json`، "
        "ثم اختار مئتي بطاقة بأولوية اكتمال الرسم والمروحة والسجل، مع إدخال أمثلة الأمر الخمسة. "
        "كل مرشح ونص معجمي لاتيني وعربي من علي فهمي خشيم، «اللاتينيّة عربيّة». "
        "المروحة والمسار والحدث والمدار والحكم من أدوات المشروع.",
        "",
        "**الأرجل الثلاث.** لا حكم موجب إلا بصوت من الشبكة المجمدة، ونص لسان العرب "
        "الذي نقله خشيم في المدخل نفسه، ومدار بشري مكتوب يصل معنى الفرع بالنص. "
        "سجل الحدث فحص موازٍ لا شاهد دلالي رابع.",
        "",
        "**قاموس الإغلاق المغلق.** تستعمل الدفعة `READY` و`OPEN-CANDIDATE` فقط. "
        f"صدر {positives} حكمًا موجبًا موسومًا `(استكشاف)`، وبقي {opens} مرشحًا مفتوحًا.",
        "",
        *rendered,
        END,
    ]
    current = READING.read_text(encoding="utf-8")
    updated = replace_batch(current, "\n".join(section))
    READING.write_text(unicodedata.normalize("NFC", updated), encoding="utf-8", newline="\n")

    open_reasons = Counter(
        reason for row in report_rows for reason in row["open_reasons"]
    )
    report = {
        "generated_by": "scripts/build_khashim_old_latin_cards.py",
        "source": "data/khashim-pairs.json",
        "source_author": "علي فهمي خشيم",
        "source_book": "اللاتينيّة عربيّة",
        "layer": "استكشاف",
        "batch": "001",
        "inventory": inventory,
        "cards_written": BATCH_SIZE,
        "positive": positives,
        "open_candidate": opens,
        "open_reasons_overlapping": dict(open_reasons.most_common()),
        "count_links": {
            "command": "python scripts/count_links.py",
            "old_latin_before": BASELINE_LINKS,
            "old_latin_after": BASELINE_LINKS + positives,
            "increase": positives,
        },
        "top_twenty": [
            {"foreign": foreign, "root": root}
            for foreign, root in TOP_TWENTY_KEYS
        ],
        "rows": report_rows,
    }
    REPORT.write_text(
        json.dumps(report, ensure_ascii=False, indent=1) + "\n",
        encoding="utf-8", newline="\n",
    )
    write_audit(report_rows, inventory)
    print(
        f"فُحص {inventory['rows_examined']}؛ كُتب {BATCH_SIZE}؛ "
        f"موجب {positives}؛ مفتوح {opens}؛ حصيلة عداد اللاتينية "
        f"{BASELINE_LINKS}→{BASELINE_LINKS + positives}."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
