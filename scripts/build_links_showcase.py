# -*- coding: utf-8 -*-
"""بناءُ معرضِ الصلاتِ للموقع (2026-08-06)

يقرأُ بطاقاتِ القراءةِ ويستخرجُ منها الصلاتِ الصادرةَ بتفصيلِها: كلمةُ الفرعِ ونطقُها
ومعناها، والعربيُّ المقابلُ ونصُّه المعجميّ، والطبقةُ التي وقعَت فيها الصلة.

**والطبقةُ هي محورُ العرض:** الجذرُ الثلاثيُّ طورٌ متأخّرٌ يبقى حيثُ قرُبَ الفرع،
والنواةُ الثنائيّةُ طورٌ أقدمُ فهي وحدَها ما يبقى حينَ يبعُد. فتوزّعُ الطبقتَينِ على
الألسنِ هو الدعوى نفسُها معروضةً بالأرقام.

**والاستخراجُ يقرأُ العنوانَ أوّلًا لا الحقول**، لأنّ عنوانَ البطاقةِ عندَ المؤلّفِ
يجمعُ الكلمةَ ومعناها ونظيرَها في سطرٍ واحدٍ نظيف: `بطاقة: seofon «seven»`، بينَما
حقلُ «الكلمةُ في الفرع» يحملُ معه الرمزَ الصوتيَّ والقسمَ والمعرّفَ المركَّب.

المخرَجان: data/links-showcase.json يقرؤُه links.html (ثمانيةُ أمثلةٍ
في اللسانِ للواجهة)، و**data/link-catalog.json** يقرؤُه catalog.html وفيه
كلُّ حكمٍ صادرٍ بساقِه الثلاث، وهو عملُنا الذي يستحقُّ النشر.
"""
from __future__ import annotations

import json
import pathlib
import re
import sys
import unicodedata

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from readable import say  # noqa: E402
import count_links as C  # noqa: E402

READINGS = ROOT / "04-cross-linguistic" / "readings"
OUT = ROOT / "data" / "links-showcase.json"
CATALOG = ROOT / "data" / "link-catalog.json"

ARABIC = re.compile(r"[ء-ي]")
LATIN = re.compile(r"[A-Za-zĀ-ſǍ-ǰḀ-ỿ]")

FIELD = lambda n: re.compile(r"^-\s*" + n + r"[^\n]*?[:：]\s*(.+)$", re.M)
RX_WORD = FIELD(r"(?:الكلمةُ? في الفرع|العضو)")
RX_SENSE = FIELD(r"المعنى من قاموس الفرع")
RX_ARABIC = FIELD(r"(?:المقابلُ? من اللسان|النظيرُ? العربيّ)")
RX_SCAN = FIELD(r"مسح (?:المعاني )?العربي[ةه]")
# الساقانِ الباقيتانِ من الثلاث: المسارُ المسمّى من الشبكةِ المغلقة، والمدارُ
# الذي كتبَه قارئٌ بيدِه. وهما ما يجعلُ الصفَّ حجّةً لا مصادفةَ رسمٍ متشابه،
# فلا يُعرَضُ صفٌّ في الكتالوجِ بلا موضعٍ لهما.
RX_PATH = FIELD(r"مسارُ? الصوت")
RX_ORBIT = FIELD(r"المدار(?:ُ المكتوب)?")

# `بطاقة: seofon «seven»`  و  `بطاقة: κιέλλη «ضياء» ↔ كلل، WEEK-DAY1`
RX_HEAD = re.compile(r"^[^:\n]{0,34}:\s*[`*]?(.+?)[`*]?\s*[«\"“]([^»\"”]{1,120})[»\"”]")
# بطاقةُ الأسرة: `بطاقة: `hebrew:family:38483…`، פשר، الرتبة 216`
RX_HEAD_FAM = re.compile(r"^[^:\n]{0,34}:\s*`[a-z-]+:family:[0-9a-f]+`\s*،\s*([^،\n]{1,26})")
# حقلُها: `أسرة `structural` مرساتها פשר، وفيها 2 عضو: פשר `pésher`، noun، «…»`
RX_ANCHOR = re.compile(r"مرساتها\s+([^\s،؛]{1,26})")
# `بطاقة: `אמין`، العضو `kaikki_aramaic:396:…`` : الكلمةُ في العنوانِ بين
# علامتَينِ ومعناها في حقلٍ مستقلٍّ لا بجانبِها، فيفشلُ عنوانُ «كلمة «معنى»»
# ولا حقلَ «الكلمة في الفرع» فيها. وهي أكثرُ ما سقطَ من الآراميّةِ والعبريّة.
RX_HEAD_TICK = re.compile(r"^[^:\n]{0,34}:\s*`([^`\n]{1,26})`")
RX_QUOTE_AR = re.compile(r"[«“]\s*([^»”]{10,190})\s*[»”]")
RX_LEX = re.compile(
    r"(لسان العرب|تاج العروس|الصحاح|القاموس المحيط|مقاييس اللغة|كتاب العين|العين"
    r"|تهذيب اللغة|المخصص|أساس البلاغة|جمهرة اللغة|المحكم|العباب|النهاية|الجيم)")

# ما يتصدَّرُ حقلَ المقابلِ فيُلبِسُه ثوبَ جذرٍ وليسَ بجذر
LEAD = re.compile(
    r"^(?:ال)?(?:نواة|جذر|وجه|مادة|كلمة|أصل|بناء|صيغة|فعل|اسم|لفظ|مروحة|سلسلة"
    r"|قراءة|بطاقة|حقل|طبقة|درجة|مقابل|نظير|في|من|عند|هو|هي|و)\s+")
NOT_ROOT = {
    "نواة", "النواة", "جذر", "الجذر", "وجه", "الوجه", "مادة", "المادة", "كلمة",
    "الكلمة", "اللسان", "العربية", "العربيّة", "لا", "نعم", "مباشر", "صلة", "أثر",
    "صدى", "حكم", "الحكم", "درجة", "طبقة", "مطابق", "غير", "مورد", "ليس", "قريب",
    "بعيد", "شاهد", "معنى", "المعنى", "هذا", "هذه", "ذلك", "التي", "الذي", "كما",
}
RX_ROOTISH = re.compile(r"^[ء-ي]{2}(?:[\s\-ـ]?[ء-ي]){0,3}$")

# طيُّ الرومنةِ العلميّةِ إلى حروفٍ تُقرَأُ بالعين
FOLD = {
    "ḫ": "kh", "ẖ": "kh", "ḥ": "h", "š": "sh", "ṯ": "th", "ṭ": "t", "ṣ": "s",
    "ḏ": "dh", "ḍ": "d", "ẓ": "z", "ġ": "gh", "ǧ": "j", "č": "ch", "ṇ": "n",
    "ꜣ": "ʾ", "ꜥ": "ʿ", "ð": "dh", "þ": "th", "ø": "o", "æ": "ae", "œ": "oe",
    "ē": "e", "ī": "i", "ō": "o", "ū": "u", "ā": "a", "ǖ": "u", "ê": "e",
    "â": "a", "î": "i", "û": "u", "ô": "o", "ü": "u", "ö": "o", "ä": "a",
}

NAMES = {
    "aramaic": ("الآراميّة", "Aramaic"), "hebrew": ("العبريّة", "Hebrew"),
    "coptic": ("القبطيّة", "Coptic"), "egyptian": ("المصريّة القديمة", "Ancient Egyptian"),
    "akkadian": ("الأكّاديّة", "Akkadian"), "ancient-greek": ("اليونانيّة القديمة", "Ancient Greek"),
    "old-latin": ("اللاتينيّة القديمة", "Old Latin"), "gothic": ("القوطيّة", "Gothic"),
    "old-norse": ("النُّرديّة القديمة", "Old Norse"), "old-english": ("الإنجليزيّة القديمة", "Old English"),
    "middle-english": ("الإنجليزيّة الوسطى", "Middle English"),
    "old-irish": ("الإيرلنديّة القديمة", "Old Irish"), "welsh": ("الويلزيّة", "Welsh"),
    "persian": ("الفارسيّة", "Persian"),
    "phoenician-punic-scout": ("الفينيقيّة", "Phoenician"), "punic": ("البونيّة", "Punic"),
}
# قربُ الفرعِ من العربيّة، لترتيبِ عرضِ التدرُّج
DISTANCE = {
    "aramaic": 1, "hebrew": 1, "akkadian": 1, "phoenician-punic-scout": 1, "punic": 1,
    "egyptian": 2, "coptic": 2,
    "ancient-greek": 3, "old-latin": 3, "persian": 3,
    "gothic": 4, "old-norse": 4, "old-english": 4, "middle-english": 4,
    "old-irish": 4, "welsh": 4,
}
WANT = 8


def clean(s: str) -> str:
    s = re.sub(r"\[[^\]]*\]", "", str(s))
    s = re.sub(r"\s+", " ", s)
    return unicodedata.normalize("NFC", s).strip(" .;،؛`*«»\"'")


def fold(s: str) -> str:
    return "".join(FOLD.get(c, FOLD.get(c.lower(), c)) for c in s)


def split_word(raw: str) -> tuple[str, str]:
    """يفصلُ صورةَ الخطِّ عن نطقِها. `ⲗⲁⲥ las` -> (ⲗⲁⲥ, las)"""
    raw = clean(raw)
    # حقلُ «العضو» يبدأُ بمعرّفِ اللقطةِ ثمّ فاصلةٍ منقوطةٍ ثمّ الكلمة، مثل
    # `` `kaikki_hebrew:1849:en-אח-he-noun-rmX6gcfB`؛ אח، noun، «brother» ``.
    # وكان المعرّفُ يُؤخَذُ كلمةً فيسقطُ الصفُّ لطولِه، و94 حكمًا عبريًّا سقطَت به.
    raw = re.sub(r"^\s*`?[a-z_]+(?:_[a-z]+)*:[^`؛\n]{4,}`?\s*[؛;]\s*", "", raw)
    # عرفُ المؤلّفِ أن يكتبَ صورةَ الفرعِ بين علامتَين، ويصفَها قبلَ ذلك بالعربيّة:
    # `بطاقة: أسرة `קם / קום` qwm «قام ونهض»` و`بطاقة: جذر AED `fd` «[sweat]»`.
    # فكانَ الوصفُ يُؤخَذُ صورةً فيظهرُ في الكتالوجِ «أسرة» و«جذر» مكانَ الكلمة.
    tick = re.search(r"`([^`\n]{1,26})`", raw)
    if tick and not re.fullmatch(r"[a-z-]+:[^`]*", tick.group(1)):
        raw = tick.group(1)
    raw = raw.split("،")[0].split("؛")[0].split("/")[0].strip(" `*")
    raw = re.sub(r"^\S*(?:ال)?(?:أكادي|آرامي|عبري|قبطي|يوناني|مصري)\S*\s+", "", raw)
    raw = re.sub(r"\s*\((?:[^)]*)\)\s*$", "", raw).strip(" `*")
    toks = [t.strip(" `*,") for t in raw.split() if t.strip(" `*,")]
    if not toks:
        return "", ""
    native = [t for t in toks if not LATIN.search(t) and not ARABIC.search(t)]
    latin = [t for t in toks if LATIN.search(t)]
    if native and latin:
        # النطقُ يلي الصورةَ مباشرةً في كتابةِ المؤلّف: `ⲗⲁⲥ las`. وأخذُ أوّلِ
        # كلمةٍ لاتينيّةٍ في الحقلِ كائنةً ما كانت جعلَ نطقَ `κεβλή` «Macedonian»،
        # وهي اسمُ لهجةٍ لا نطقٌ للكلمة.
        i = toks.index(native[0])
        nxt = toks[i + 1] if i + 1 < len(toks) else ""
        if nxt and LATIN.search(nxt) and not ARABIC.search(nxt):
            return native[0], fold(nxt)
        spoken = say(native[0])
        return native[0], (fold(spoken.split("(")[0].strip())
                           if spoken != native[0] else "")
    word = toks[0]
    if LATIN.search(word):                      # كلمةٌ مرقونةٌ أصلًا
        return word, (fold(word) if fold(word) != word else "")
    spoken = say(word)                          # خطٌّ غيرُ لاتينيّ: يُنطَقُ له
    spoken = fold(spoken.split("(")[0].strip()) if spoken != word else ""
    return word, spoken


def ok_root(root: str) -> bool:
    letters = re.sub(r"[^ء-ي]", "", root)
    if not (2 <= len(letters) <= 8) or root in NOT_ROOT or letters in NOT_ROOT:
        return False
    return not (letters.startswith("ال") and len(letters) < 4)


# الجانبُ العربيُّ من المسارِ المسمّى: `ʾ-ḫ-z ↔ ء-خ-ذ` و`t-w-r ↔ ṭ-w-r`.
# وهو أوثقُ ما يُستَخرَجُ منه المقابلُ حينَ لا يُسمّى حقلٌ له، لأنّه تعريفُ
# الصلةِ نفسِها لا استنتاجٌ عنها، وبه تُستَردُّ مئاتُ الأحكامِ التي كانت تسقطُ.
RX_ARROW_AR = re.compile(r"[↔=]\s*`?\s*([ء-ي](?:[\-ـ\s][ء-ي]){1,3}|[ء-ي]{2,6})")

# **المقابلُ يُؤخَذُ من حقلٍ معناه المقابل، لا من أوّلِ كلمةٍ عربيّةٍ في البطاقة.**
# فحقلُ «عائق» و«ملاحظات» يحملانِ عربيّةً كثيرةً وليسَ فيهما نظيرٌ البتّة، ومن
# أخذَ منهما نسبَ إلى البطاقةِ ما لم تقُلْه. وهذه الحقولُ مرتَّبةٌ بالأوثقِ أوّلًا،
# وكلُّها مرصودةٌ في الملفّاتِ لا مفترضة: بطاقاتُ حملةِ فكِّ الحبسِ تكتبُ نظيرَها
# في «تحقق المعنى في المصدرين»، وبطاقاتُ الاسترجاعِ في «المدخل العربي»، وبطاقاتُ
# الطبقتَينِ تسمّي النواةَ في سطرِ حكمِها.
# وملحقُ الحملةِ يكتبُ بنودَه مُزاحةً تحتَ بندٍ أعلى، فلا تبدأُ سطورُه بالشرطة.
# وهذا وحدَه كان يُخفي «تحقق المعنى في المصدرين: `اليد`» عن الأداةِ في مئاتِ
# البطاقات، فيسقطُ الحكمُ الصادرُ كأنّه بلا نظيرٍ عربيٍّ وهو مكتوبٌ فيه.
SUBFIELD = lambda n: re.compile(r"^\s*-\s*" + n + r"[^\n]*?[:：]\s*(.+)$", re.M)

RX_TICKED_AR = re.compile(r"[`«\"]\s*([ء-ي](?:[\-ـ\s][ء-ي]){1,3}|[ء-ي]{2,8})\s*[`»\"]")


def ticked_root(field: str) -> str:
    """المقابلُ محصورًا بعلامتَينِ **داخلَ** الحقل، لا في صدرِه وحدَه.

    سطرُ الحكمِ يكتبُه المؤلّفُ هكذا: `ROOT-TRACE بالمادة `صور`` و`**ROOT-TRACE
    (استكشاف)** بالمقابل `صور``. وكانَ يسقطُ لسببَين: `arabic_root` لا تقرأُ
    إلّا صدرَ الحقلِ فتصطدمُ بـROOT-TRACE، و`clean` تقشِطُ العلامةَ من الطرفِ
    فتُخفي المحصورَ عن بحثِها. وبهذا وحدَه سقطَ أكثرُ من ألفِ حكمٍ صادر.
    """
    for m in RX_TICKED_AR.finditer(str(field)):
        root = re.sub(r"\s+", " ", m.group(1)).strip(" ـ")
        if ok_root(root):
            return root
    return ""
COUNTERPART = [
    RX_ARABIC,
    SUBFIELD(r"تحقق المعنى في المصدر(?:ين|ي)"),
    SUBFIELD(r"المدخل العربي"),
    SUBFIELD(r"المصدر العربي القديم (?:الأول|الثاني)"),
    SUBFIELD(r"(?:الحسم|حكم طبقة النواة|حكم طبقة الجذر)"),
    # وسطرُ الحكمِ نفسُه يسمّي المقابلَ في كثيرٍ من البطاقات:
    # `**ROOT-TRACE (استكشاف)** بالمقابل `صور``. وهو آخرُ ما يُسأَلُ
    # لأنّه أعمُّ الحقولِ لفظًا، لا لأنّه أضعفُها سندًا.
    SUBFIELD(r"الحكم"),
]


def arabic_root(field: str, block: str) -> str:
    """النظيرُ العربيُّ كما كتبَه صاحبُ البطاقة. المحصورُ بين علامتَينِ أوثقُ،
    مثل `باء الجر `بـ` في وجه الإلصاق` فالمقصودُ فيها ما بينَ العلامتَين."""
    txt = clean(field)
    for m in re.finditer(r"[`«\"]\s*([ء-يـ]{1,7}(?:[\s\-ـ][ء-ي]){0,3})\s*[`»\"]", txt):
        root = re.sub(r"\s+", " ", m.group(1)).strip(" ـ") or m.group(1).strip()
        if ok_root(root):
            return root
    for _ in range(4):
        new = LEAD.sub("", txt)
        if new == txt:
            break
        txt = new
    cand = txt.split("«")[0].split("[")[0].strip(" .،؛:")
    # إمّا كلمةٌ واحدة، وإمّا نواةٌ مكتوبةٌ حروفًا مفرَّقةً مثل `س-ب`. ولا يُخلَطُ
    # البابانِ وإلّا التقطَ حرفَ جرٍّ تالٍ فصارَ `كلل ف`.
    m = (re.match(r"^([ء-ي](?:[\-ـ\s][ء-ي]){1,3})(?![ء-ي])", cand)
         or re.match(r"^([ء-ي]{2,8})(?![ء-ي])", cand))
    if m:
        root = re.sub(r"\s+", " ", m.group(1)).strip()
        if ok_root(root):
            return root
    return ""


def lexicon_quote(block: str) -> tuple[str, str]:
    """نصٌّ عربيٌّ منقولٌ من معجم، ولا يُنسَبُ إلى معجمٍ إلّا إن كان اسمُه ملاصقًا
    للنصِّ فعلًا. فالنسبةُ إلى أوّلِ اسمٍ في البطاقةِ تنسبُ إلى غيرِ قائل."""
    sc = RX_SCAN.search(block)
    zones = ([block[sc.start():sc.start() + 1800]] if sc else []) + [block]
    for zone in zones:
        for q in RX_QUOTE_AR.finditer(zone):
            text = clean(q.group(1))
            if len(ARABIC.findall(text)) < 6 or LATIN.search(text):
                continue
            before = zone[max(0, q.start() - 170):q.start()]
            lex = list(RX_LEX.finditer(before)) or list(
                RX_LEX.finditer(zone[q.end():q.end() + 90]))
            return text[:170], (lex[-1].group(1) if lex else "")
    return "", ""


SOURCEY = re.compile(r"السطر|اللقطة|المعرّ?ف|المصدر|kaikki|Kaikki|TLA|CAD|CD ", re.I)


def branch_sense(head_gloss: str, field: str, member: str = "") -> str:
    """معنى الكلمةِ كما في قاموسِ فرعِها. عنوانُ البطاقةِ أنظفُ من الحقلِ لأنّ
    الحقلَ يحملُ معه اسمَ اللقطةِ ورقمَ السطرِ ومعرّفَ العضو. وحقلُ العضوِ آخرُ
    ما يُسأَل، لأنّه يحملُ المعنى مع المعرّفِ فيحتاجُ قشرًا، لا لأنّه أضعفُ."""
    for raw in (head_gloss, field, member):
        if not raw:
            continue
        # يُبحَثُ عن المحصورِ بين علامتَينِ **قبل** التنظيف، لأنّ التنظيفَ يقشِطُ
        # علامةَ الإغلاقِ من الطرفِ فيُخفيها عن البحث
        s = re.sub(r"\s+", " ", re.sub(r"\[[^\]]*\]", "", str(raw))).strip()
        s = re.sub(r"^[^:：]{0,26}[:：]\s*", "", s) if SOURCEY.match(s) else s
        # حقلُ الأسرةِ يسبقُ معناها بمرساتِها وقسمِها: `פשר `pésher`، noun، «…»`
        inner = re.search(r"[«“]([^»”]{2,120})[»”]", s)
        s = clean(inner.group(1) if inner else s)
        s = s.split("»")[0].split("”")[0].split("[")[0]
        s = s.strip(" `*«»\"'.،؛:")
        if s and not SOURCEY.search(s) and len(s) > 1:
            return s[:78]
    return ""


def iter_cards(path: pathlib.Path):
    """مرّر بطاقةً مطبّعةً واحدةً، ولا تحمل ملف القراءة الكبير كله في الذاكرة."""
    block: list[str] | None = None
    with path.open(encoding="utf-8") as handle:
        for raw_line in handle:
            line = C.bare(raw_line)
            marker = C.CARD_SPLIT.match(line)
            if marker:
                if block is not None:
                    yield "".join(block)
                block = [line[marker.end():]]
            elif block is not None:
                block.append(line)
    if block is not None:
        yield "".join(block)


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    langs: dict[str, dict] = {}
    catalog: list[dict] = []
    # سببُ سقوطِ كلِّ حكمٍ صادرٍ لا يبلغُ الكتالوج، محسوبًا في مسارِ التنفيذِ
    # نفسِه لا في نصٍّ مكرَّرٍ يجوزُ أن يختلفَ عنه.
    drop: dict[str, int] = {"صورة": 0, "معنى": 0, "مقابل": 0, "صدر": 0}

    for path in sorted(READINGS.glob("*.md")):
        lang = path.stem
        if lang not in NAMES:
            continue
        entry = langs.setdefault(lang, {
            "key": lang, "ar": NAMES[lang][0], "en": NAMES[lang][1],
            "distance": DISTANCE.get(lang, 3),
            "root": 0, "nucleus": 0, "floor": 0, "pool": [], "examples": [],
        })
        for block in iter_cards(path):
            degrees = C.scan_card(block)
            if not degrees:
                continue
            # يُعَدُّ كما يعدُّ `count_links.py` بالضبط: كلُّ درجةٍ صادرةٍ تُحسَبُ
            # في طبقتِها، فالبطاقةُ الواحدةُ قد تحملُ درجتَينِ وهي صلتان. وإلّا
            # اختلفَ رقمُ الصفحةِ عن الرقمِ القانونيِّ وصارَ في المشروعِ عدّادان.
            for d in degrees:
                entry[C.layer(d)] += 1
            layer = "nucleus" if any("NUCLEUS" in d for d in degrees) else "root"

            head = block.split("\n", 1)[0]
            mh = RX_HEAD.match(head)
            mw, ms = RX_WORD.search(block), RX_SENSE.search(block)
            field = mw.group(1) if mw else ""
            # ثلاثةُ أشكالٍ للعنوانِ في الملفّات، وأنظفُها أوّلًا
            anchor = RX_ANCHOR.search(field) or RX_HEAD_FAM.match(head)
            tick = RX_HEAD_TICK.match(head)
            # **يُجرَّبُ كلُّ مصدرٍ حتّى يصحَّ واحد، لا يُؤخَذُ الأوّلُ ويُترَكُ
            # الباقي.** فعنوانٌ مثل `بطاقة: بلا رومنة منشورة «to be merciful»`
            # لا صورةَ فيه أصلًا، وصورتُه في حقلِ الكلمة، وكان الصفُّ يُنشَرُ
            # وكلمتُه «بلا». والخطُّ العربيُّ لا يُقبَلُ صورةً لفرعٍ غيرِ عربيِّ
            # الخطِّ إلّا حيثُ تُصرِّحُ البطاقةُ أنّها نقلَته بحروفٍ عربيّة.
            arabic_script_ok = "بحروف عربية" in block or "بحروف عربيّة" in block
            word = spoken = ""
            for cand in (anchor.group(1) if anchor else None,
                         mh.group(1) if mh else None,
                         tick.group(1) if tick else None,
                         field):
                if not cand:
                    continue
                w, sp = split_word(cand)
                if not w or len(w) > 26 or ":" in w:
                    continue
                if ARABIC.search(w) and not arabic_script_ok:
                    continue
                word, spoken = w, sp
                break
            if not word:
                drop["صورة"] += 1
                continue
            if not spoken and not LATIN.search(word):
                # نطقُ الأسرةِ مكتوبٌ بعدَ مرساتِها بين علامتَين
                mt = re.search(re.escape(word) + r"\s*`([^`]{1,18})`", block)
                if mt and LATIN.search(mt.group(1)):
                    spoken = fold(mt.group(1))
            # بطاقاتُ الأسرةِ لا تُفرِدُ حقلًا للمعنى، بل تكتبُه في حقلِ العضوِ
            # بين علامتَين: `לבושא `بلا رومنة`، noun، «clothing, garment»`.
            # وكان 701 حكمًا آراميًّا وعبريًّا يسقطُ لأنّ الحقلَ لم يُسأَل.
            sense = branch_sense(mh.group(2) if mh else "",
                                 ms.group(1) if ms else "", field)
            # **ولا يُشتَرَطُ معنى القاموسِ لبقاءِ الصفّ.** الصفُّ حجّةٌ بصورةِ
            # الفرعِ ومقابلِها ومسارِ الصوتِ والمدار، وغيابُ سطرِ المعنى نقصُ
            # عرضٍ لا نقضُ حكم، وكان يطرحُ 314 حكمًا صادرًا بلا سبب.
            if not sense:
                drop["معنى"] += 1
            root = ""
            for rx in COUNTERPART:
                m = rx.search(block)
                if not m:
                    continue
                root = arabic_root(m.group(1), block) or ticked_root(m.group(1))
                if root:
                    break
            if not root:
                mp0 = RX_PATH.search(block)
                ar = RX_ARROW_AR.search(mp0.group(1)) if mp0 else None
                if ar and ok_root(ar.group(1).strip()):
                    root = re.sub(r"\s+", " ", ar.group(1)).strip()
            if not root:
                drop["مقابل"] += 1
                continue
            quote, lex = lexicon_quote(block)
            mp, mo = RX_PATH.search(block), RX_ORBIT.search(block)
            entry["pool"].append({
                "word": word, "say": spoken, "sense": sense, "arabic": root,
                "quote": quote, "lexicon": lex, "layer": layer,
                "degree": sorted(degrees)[0],
                "path": clean(mp.group(1))[:150] if mp else "",
                "orbit": clean(mo.group(1))[:150] if mo else "",
                "rank": (2 if quote and lex else 1 if quote else 0),
            })

    rows = [e for e in langs.values() if e["root"] + e["nucleus"] > 0]
    for e in rows:
        tot = e["root"] + e["nucleus"]
        e["total"] = tot
        e["nucleus_share"] = round(100 * e["nucleus"] / tot, 1) if tot else 0.0
        seen, picked = set(), []
        # الأثمنُ أوّلًا: ما حملَ نصًّا معجميًّا مسمًّى. ثمّ تُوازَنُ الطبقتان.
        for want_layer in ("nucleus", "root", None):
            for x in sorted(e["pool"], key=lambda x: -x["rank"]):
                if len(picked) >= WANT:
                    break
                if want_layer and x["layer"] != want_layer:
                    continue
                key = (x["word"], x["arabic"])
                if key in seen:
                    continue
                if want_layer and sum(1 for p in picked if p["layer"] == want_layer) >= WANT // 2:
                    continue
                seen.add(key)
                picked.append(x)
        for x in picked:
            x.pop("rank", None)
        e["examples"] = picked
        # **البِركةُ كانت تُرمى وفيها العملُ كلُّه.** كان يُستخرَجُ كلُّ صفٍّ ثمّ
        # يُحتفَظُ بثمانيةٍ في اللسانِ ويُطرَحُ الباقي، فكانَ الموقعُ يعرضُ عدًّا
        # ومئةً وثلاثينَ مثالًا من 3,747 حكمًا صادرًا. وهي بطاقاتُنا نحن، لا نقلَ
        # فيها عن معجمٍ منشور، فمكانُها الموقعُ لا القرصُ وحدَه.
        catalog.extend(dict(x, lang=e["key"], ar=e["ar"], distance=e["distance"])
                       for x in e.pop("pool", []))
    rows.sort(key=lambda e: (e["distance"], -e["total"]))
    for x in catalog:
        x.pop("rank", None)
    catalog.sort(key=lambda x: (x["distance"], x["lang"], x["arabic"]))

    payload = {
        "generated_by": "scripts/build_links_showcase.py",
        "note": "طبقةُ استكشاف. الأرقامُ من scripts/count_links.py وهو التعريفُ الوحيدُ للصلة.",
        "totals": {
            "root": sum(e["root"] for e in rows),
            "nucleus": sum(e["nucleus"] for e in rows),
            "languages": len(rows),
        },
        "languages": rows,
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")

    CATALOG.write_text(json.dumps({
        "generated_by": "scripts/build_links_showcase.py",
        "note": "طبقةُ استكشاف. كلُّ صفٍّ حكمٌ صادرٌ في بطاقةٍ من بطاقاتِنا، "
                "لا نقلَ فيه عن معجمٍ منشور. والعدُّ القانونيُّ في "
                "scripts/count_links.py وهو التعريفُ الوحيدُ للصلة.",
        "rows": len(catalog),
        "languages": {e["key"]: {"ar": e["ar"], "en": e["en"],
                                 "distance": e["distance"], "total": e["total"]}
                      for e in rows},
        "items": catalog,
    }, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    kept = len(catalog)
    # وبطاقةُ «بلا معنى» تبقى في الكتالوج، فلا تُحسَبُ في الساقطِ وإلّا انتفخَ
    # المقامُ وصارَ العرضُ أسوأَ ممّا هو، ورقمٌ خاطئٌ في غيرِ صالحِنا خطأٌ أيضًا.
    lost = drop["صورة"] + drop["مقابل"]
    print(f"الساقطُ عن الكتالوج: {lost:,} بطاقةً ذاتَ حكمٍ صادر  "
          + " · ".join(f"بلا {k}={v:,}" for k, v in drop.items() if v))
    print(f"البالغُ: {kept:,} من {kept + lost:,}  ({100 * kept / max(kept + lost, 1):.0f}%)")
    with_path = sum(1 for x in catalog if x["path"])
    with_orbit = sum(1 for x in catalog if x["orbit"])
    print(f"الكتالوج: {len(catalog):,} صفًّا "
          f"(مسارُ صوتٍ مكتوب {with_path:,} · مدارٌ مكتوب {with_orbit:,}) "
          f"← {CATALOG.relative_to(ROOT).as_posix()} "
          f"({CATALOG.stat().st_size/1048576:.1f} ميجا)\n")
    print(f"ألسنٌ فيها صلات: {len(rows)}")
    print(f"{'اللسان':22}{'جذر':>6}{'نواة':>6}{'حصّةُ النواة':>13}{'أمثلة':>7}{'بنصّ معجم':>11}")
    for e in rows:
        q = sum(1 for x in e["examples"] if x["quote"])
        print(f"{e['ar']:22}{e['root']:>6}{e['nucleus']:>6}"
              f"{e['nucleus_share']:>12.0f}%{len(e['examples']):>7}{q:>11}")
    print(f"\nكُتب: {OUT.relative_to(ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
