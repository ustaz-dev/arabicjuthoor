# -*- coding: utf-8 -*-
"""حصادُ معاجمِ خشيم المقارِنة (2026-08-10، بأمرِ المؤلّف)

**مَن هو:** الليبيُّ **علي فهمي خشيم**، وكتبُه عناوينُها بنفسِها دعوانا:
«الأكّاديّةُ عربيّة» و«القبطيّةُ عربيّة» و«اللاتينيّةُ عربيّة» و«البرهانُ على
عروبةِ اللغةِ المصريّةِ القديمة» و«الوحدةُ والتنوّعُ في اللهجاتِ العروبيّةِ
القديمة». **وهي ألسنُنا بعينِها**: الأكّاديّةُ والقبطيّةُ والمصريّةُ واللاتينيّة.

**وبنيةُ كتبِه معجميّةٌ لا مقاليّة**، وهذا ما يجعلُها تُحصَدُ آليًّا:

    شمت : قدر، مصير. (من «شم»)
    ع : سمي. سمّى: عيّن، أي قرّر قدره ومصيره، خصّص.

    شزب : لبن.
    ع : شخب. الشّخب: ما خرج من الضرع من اللبن إذا احتُلب.

فالسطرُ الأوّلُ الكلمةُ الأجنبيّةُ بحروفٍ عربيّةٍ ومعناها، والسطرُ الذي يبدأُ
بـ`ع :` فيه **الجذرُ العربيُّ ونصُّ معجمِه**. والعلامةُ `ع` مرساةٌ ثابتةٌ في
الكتابِ كلِّه.

**وعقبتانِ في الاستخراجِ عولِجَتا:**

1. **النصُّ يخرجُ بترتيبٍ بصريٍّ معكوس** لأنّ ملفَّ المسحِ لا يحملُ ترتيبًا
   منطقيًّا: تخرجُ «والعبريين» هكذا «نييربعلاو». فتُقلَبُ حروفُ كلِّ كلمةٍ
   ويُقلَبُ ترتيبُ الكلماتِ في السطر.
2. **المسحُ الضوئيُّ عربيٌّ فقط**، فالحروفُ اللاتينيّةُ في كتابِ اللاتينيّةِ
   سقطَت كلَّها (صفرُ حرفٍ لاتينيٍّ في 234 صفحة). فيُحصَدُ ما كتبَه هو بالعربيّة،
   ويبقى نصُّ الكلمةِ الأجنبيّةِ بالحرفِ الأصليِّ نقصًا مسمًّى يُسَدُّ بمسحٍ ثانٍ.

**ولا حكمَ هنا على زوج.** أمرُ المؤلّف: «استعملْ أعمالَه، لا تحكمْ عليها، واحصدْ
أقصى ما يمكنُ من الصلات».

الاستعمال:
    python scripts/harvest_khashim.py
"""
from __future__ import annotations

import difflib
import json
import pathlib
import re
import sys
import unicodedata

ROOT = pathlib.Path(__file__).resolve().parent.parent
STORE = pathlib.Path.home() / "AI Projects" / "Resources" / "prior-art"
OUT = ROOT / "data" / "khashim-pairs.json"
SHEET = ROOT / "04-cross-linguistic" / "exploration" / "khashim-harvest.md"

BOOKS = {
    "khashim-akkadian": ("الأكّاديّة", "akkadian"),
    "khashim-coptic": ("القبطيّة", "coptic"),
    "khashim-latin": ("اللاتينيّة", "old-latin"),
    "khashim-dialects": ("اللهجاتُ العروبيّةُ القديمة", "semitic"),
}

AR = re.compile(r"[؀-ۿ]")
# **مرساتانِ لا واحدة**: في «الأكّاديّةُ عربيّة» يكتبُ `ع :` مختصرًا، وفي
# «اللاتينيّةُ عربيّة» يكتبُ `في العربية :` كاملةً ويُخرِجُها المسحُ ناقصةَ
# الصدرِ هكذا `د العربية :` و`بد العربية :`. فمن طلبَ العينَ المفردةَ وحدَها
# خرجَ من كتابِ اللاتينيّةِ بصفر.
RX_AR_LINE = re.compile(r"^\s*(?:ع|[ء-ي]{0,3}\s*العربية)\s*[:：]\s*(.+)$")
# الجذرُ أوّلُ كلمةٍ عربيّةٍ في السطر، وقد يليها شرحُها
RX_ROOT = re.compile(r"^([ء-ي]{2,6})\b")
# الكلمةُ الأجنبيّةُ ومعناها: `شمت : قدر، مصير`
RX_ENTRY = re.compile(r"^\s*([ء-ي][ء-يـ\s]{0,14}?)\s*[:：]\s*(.{2,90})$")
NOISE = ("انظر", "المرجع", "الصفحة", "الفصل", "الباب", "المصدر", "الهامش")


def unmirror(line: str) -> str:
    """يُعادُ السطرُ إلى ترتيبِه المنطقيّ. المسحُ يخرجُه بترتيبِ العينِ لا العقل."""
    if not AR.search(line):
        return line
    return " ".join(w[::-1] for w in line.split()[::-1])


def clean(s: str) -> str:
    s = unicodedata.normalize("NFC", s)
    s = re.sub(r"[ـ‌‏‫‬]", "", s)   # تطويلٌ وعلاماتُ اتّجاه
    s = re.sub(r"[«»\"'‘’]", "", s)
    return re.sub(r"\s+", " ", s).strip(" .,؛:،")


def mine(path: pathlib.Path, tongue_ar: str, tongue_key: str) -> list[dict]:
    import fitz                                             # noqa: PLC0415
    doc = fitz.open(path)
    lines: list[str] = []
    for page in doc:
        lines.extend(unmirror(x) for x in page.get_text().splitlines())

    pairs, seen = [], set()
    for i, line in enumerate(lines):
        m = RX_AR_LINE.match(line)
        if not m:
            continue
        ar_side = clean(m.group(1))
        rm = RX_ROOT.match(ar_side)
        if not rm:
            continue
        root = rm.group(1)
        gloss_ar = clean(ar_side[rm.end():])

        # المدخلُ الأجنبيُّ في السطورِ الثلاثةِ التي قبلَه، وأقربُها أولى
        foreign = foreign_sense = ""
        for back in range(1, 4):
            if i - back < 0:
                break
            prev = clean(lines[i - back])
            if not prev or RX_AR_LINE.match(lines[i - back]):
                continue
            em = RX_ENTRY.match(prev)
            if em and not any(n in prev for n in NOISE):
                foreign, foreign_sense = clean(em.group(1)), clean(em.group(2))
                break
        if not foreign:
            # **كتابُ اللاتينيّةِ لا يُخرِجُ رأسَ المدخل** لأنّ حرفَه لاتينيٌّ وقد
            # سقطَ في المسح، فيُؤخَذُ أقربُ سطرٍ عربيٍّ ذي معنًى بوصفِه شرحَ
            # المدخل. والزوجُ يُحفَظُ بنقصٍ مسمًّى لا يُطرَحُ لأجلِه.
            for back in range(1, 4):
                if i - back < 0:
                    break
                prev = clean(lines[i - back])
                if len(prev) >= 4 and AR.search(prev) and not RX_AR_LINE.match(lines[i - back]):
                    foreign_sense = prev[:90]
                    foreign = "(سقطَ حرفُه في المسح)"
                    break
        if not foreign or len(root) < 2:
            continue
        key = (foreign if "سقط" not in foreign else foreign_sense, root)
        if key in seen:
            continue
        seen.add(key)
        pairs.append({
            "tongue_ar": tongue_ar, "tongue": tongue_key,
            "foreign": foreign, "foreign_sense": foreign_sense,
            "arabic_root": root, "arabic_gloss": gloss_ar[:160],
            "source": path.stem,
        })
    return pairs


# ---------------------------------------------- المسحُ الضوئيُّ الجديدُ للكتب
# **لماذا مِعوَلٌ ثانٍ:** المسحُ القديمُ لكتابِ اللاتينيّةِ كان عربيًّا وحدَه فسقطَ
# منه كلُّ حرفٍ لاتينيّ (صفرٌ في 234 صفحة)، فلم يبقَ من المدخلِ إلّا جوابُه. وقد
# أُعيدَ مسحُه بإذنِ المؤلّفِ بمسحٍ يقرأُ الخطَّينِ، فصارَ المدخلُ كاملًا:
#
#     drappus
#     شف ، نسيج ، شاش ، خرقة .
#     * العربية : أذرب . جاء في (اللسان) تحت هذه المادة : ...
#
# فالمدخلُ سطرٌ لاتينيٌّ وحدَه، ويليه معناه بالعربيّة، ثمّ سطرُ الجوابِ الذي
# يبدأُ بنجمةٍ ثمّ «العربية :» ثمّ الجذرُ ونصُّ معجمِه.
RX_OCR_HEAD = re.compile(r"^\s*([A-Za-zĀ-ſ][A-Za-zĀ-ſ\-']{2,22})\s*$")
RX_OCR_ANSWER = re.compile(r"^[\s*·•]*(?:[ء-ي]{0,4}\s*)?العربية\s*[:：]\s*(.+)$")


def mine_ocr(md: pathlib.Path, tongue_ar: str, tongue_key: str) -> list[dict]:
    lines = [clean(x) for x in md.read_text(encoding="utf-8").splitlines()]
    pairs, seen = [], set()
    for i, line in enumerate(lines):
        m = RX_OCR_ANSWER.match(line)
        if not m:
            continue
        ar_side = clean(m.group(1))
        rm = RX_ROOT.match(ar_side)
        if not rm:
            continue
        root, gloss_ar = rm.group(1), clean(ar_side[rm.end():])

        # نص لسان العرب يمتد كثيرًا إلى الأسطر التالية بعد سطر «العربية: مادة»؛
        # لا يجوز اختزاله في ذيل السطر الأول، ولا سيما إذا كان الذيل فارغًا.
        gloss_parts = [gloss_ar] if gloss_ar else []
        for forward in range(1, 10):
            if i + forward >= len(lines):
                break
            continuation = lines[i + forward]
            if RX_OCR_ANSWER.match(continuation) or RX_OCR_HEAD.match(continuation):
                break
            if continuation and AR.search(continuation):
                gloss_parts.append(continuation)
        gloss_ar = clean(" ".join(gloss_parts))

        # المدخلُ اللاتينيُّ في عشرةِ سطورٍ قبلَه، وأقربُها أولى، ومعناه
        # أوّلُ سطرٍ عربيٍّ بعدَه مباشرةً
        foreign = foreign_sense = ""
        head_line = None
        for back in range(1, 11):
            if i - back < 0:
                break
            hm = RX_OCR_HEAD.match(lines[i - back])
            if hm:
                foreign = hm.group(1)
                head_line = i - back + 1
                for sense_line in range(i - back + 1, i):
                    candidate = lines[sense_line]
                    if candidate and AR.search(candidate) and not RX_OCR_ANSWER.match(candidate):
                        foreign_sense = candidate[:90]
                        break
                break
        if not foreign or len(root) < 2:
            continue
        key = (foreign, root)
        if key in seen:
            continue
        seen.add(key)
        pairs.append({
            "tongue_ar": tongue_ar, "tongue": tongue_key,
            "foreign": foreign, "foreign_sense": foreign_sense,
            "arabic_root": root, "arabic_gloss": gloss_ar[:600],
            "source": md.parent.name,
            "source_line": head_line,
        })
    return pairs


def _bare_ar(value: str) -> str:
    value = unicodedata.normalize("NFKC", value or "")
    value = re.sub(r"[\u064b-\u065fـ]", "", value).replace("ٱ", "ا")
    return re.sub(r"[^ء-ي]", "", value)


def _ocr_similarity(left: str, right: str) -> float:
    left, right = _bare_ar(left), _bare_ar(right)
    if not left or not right:
        return 0.0
    return difflib.SequenceMatcher(None, left, right, autojunk=False).ratio()


def recover_latin_heads(rows: list[dict]) -> tuple[list[dict], dict[str, int]]:
    """ردّ رؤوس المسح العربي القديم إلى المسح الجديد بلا إعادة استعمال.

    الرصف عالمي رتيب: لا يطابق إلا الجذر العربي نفسه، ويرجّح داخل التكرار
    اتفاق نص لسان العرب ثم معنى المدخل. وبذلك لا يستطيع رأس متأخر أن يقفز فوق
    رأس سابق، ولا يستطيع صفان قديمان سرقة الرأس الجديد نفسه.
    """
    new = [row for row in rows if row.get("source") == "ocr-latin"]
    old_positions = [
        index for index, row in enumerate(rows)
        if row.get("source") == "khashim-latin"
    ]
    old = [rows[index] for index in old_positions]
    if (len(new), len(old)) != (515, 560):
        raise SystemExit(
            f"تغيّر جرد رصف اللاتينية: الجديد/القديم={len(new)}/{len(old)}"
        )

    n, m, gap = len(old), len(new), -2.0
    scores = [[0.0] * (m + 1) for _ in range(n + 1)]
    paths = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        scores[i][0], paths[i][0] = i * gap, 1
    for j in range(1, m + 1):
        scores[0][j], paths[0][j] = j * gap, 2
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            if _bare_ar(old[i - 1]["arabic_root"]) == _bare_ar(new[j - 1]["arabic_root"]):
                match = (
                    7.0
                    + 6.0 * _ocr_similarity(old[i - 1].get("arabic_gloss", ""),
                                             new[j - 1].get("arabic_gloss", ""))
                    + 4.0 * _ocr_similarity(old[i - 1].get("foreign_sense", ""),
                                             new[j - 1].get("foreign_sense", ""))
                )
            else:
                match = -8.0
            choices = (
                scores[i - 1][j - 1] + match,
                scores[i - 1][j] + gap,
                scores[i][j - 1] + gap,
            )
            choice = max(range(3), key=lambda key: choices[key])
            scores[i][j], paths[i][j] = choices[choice], choice

    aligned: list[tuple[int, int]] = []
    i, j = n, m
    while i or j:
        choice = paths[i][j]
        if i and j and choice == 0:
            if _bare_ar(old[i - 1]["arabic_root"]) == _bare_ar(new[j - 1]["arabic_root"]):
                aligned.append((i - 1, j - 1))
            i, j = i - 1, j - 1
        elif i and (not j or choice == 1):
            i -= 1
        else:
            j -= 1
    aligned.reverse()

    repaired = [dict(row) for row in rows]
    recovered = 0
    for old_index, new_index in aligned:
        old_row, new_row = old[old_index], new[new_index]
        if old_row.get("foreign") != "(سقطَ حرفُه في المسح)":
            continue
        target = repaired[old_positions[old_index]]
        target["foreign"] = new_row["foreign"]
        if new_row.get("foreign_sense"):
            target["foreign_sense"] = new_row["foreign_sense"]
        target["ocr_recovery"] = {
            "old_head": "(سقطَ حرفُه في المسح)",
            "old_foreign_sense": old_row.get("foreign_sense", ""),
            "matched_source": "Resources/prior-art/ocr-latin/full.md",
            "source_line": new_row.get("source_line"),
            "matched_new_row": new_index,
            "contract": "الجذر نفسه + رصف رتيب + ترجيح معنى المدخل ونص لسان العرب",
        }
        recovered += 1
    if recovered != 290:
        raise SystemExit(f"تغيّر عدد رؤوس اللاتينية المستردة: {recovered}، والمتوقع 290")
    return repaired, {
        "old_rows_with_fallen_head": 513,
        "heads_recovered": recovered,
        "heads_still_fallen": 513 - recovered,
    }



# ------------------------------------------- «الأكّاديّةُ عربيّة» بعدَ مسحِها الجديد
# **العطبُ الذي يُغلِقُه:** المسحُ القديمُ أسقطَ رأسَ المدخلِ في 242 صفًّا من 588
# (41%)، فكانت ورقةُ الأذُنِ تعرضُ على المؤلّفِ معنًى بلا كلمةٍ يقرؤُها. والمسحُ
# الجديدُ يُخرِجُ المدخلَ مشكولًا كاملًا:
#
#     بِرَاشُ : طَارَ .
#     ع : فَرَشَ . ومنها فَرَاشَةٌ: حشرةٌ تطير... وأفرشَ: ارتفعَ وأقلعَ، أي طار.
RX_AKK_ENTRY = re.compile(r"^\s*([ء-يًٌٍَُِّْـ][ء-يًٌٍَُِّْـ\s]{0,16}?)\s*[:：]\s*(.{2,90})$")


def mine_akkadian_ocr(md: pathlib.Path) -> list[dict]:
    lines = [clean(x) for x in md.read_text(encoding="utf-8").splitlines()]
    pairs, seen = [], set()
    for i, line in enumerate(lines):
        m = RX_AR_LINE.match(line)
        if not m:
            continue
        ar_side = clean(m.group(1))
        rm = RX_ROOT.match(bare_ar(ar_side))
        if not rm:
            continue
        root, gloss = rm.group(1), bare_ar(clean(ar_side))
        foreign = foreign_sense = ""
        for back in range(1, 4):
            if i - back < 0:
                break
            prev = clean(lines[i - back])
            if not prev or RX_AR_LINE.match(lines[i - back]):
                continue
            em = RX_AKK_ENTRY.match(prev)
            if em and not any(n in prev for n in NOISE):
                foreign = bare_ar(clean(em.group(1)))
                foreign_sense = bare_ar(clean(em.group(2)))
                break
        if not foreign or len(root) < 2:
            continue
        key = (foreign, root)
        if key in seen:
            continue
        seen.add(key)
        pairs.append({
            "tongue_ar": "الأكّاديّة", "tongue": "akkadian",
            "foreign": foreign, "foreign_sense": foreign_sense,
            "arabic_root": root, "arabic_gloss": gloss[:200],
            "source": "ocr-akkadian",
        })
    return pairs


OCR_BOOKS = {
    "ocr-latin": ("اللاتينيّة", "old-latin"),
}

# ------------------------------------------------------ «القبطيّةُ عربيّة» بعدَ مسحِها
# **بنيتُه هنا أقربُ ما رأيناه إلى بنيتِنا نحن**، فهو يكتبُ النواةَ الثنائيّةَ
# حروفًا مفرَّقةً في العنوان، ثمّ يردُّها إلى مادّتِها الثلاثيّةِ في المتن:
#
#     ## ب ح  وصل. جاء. حلّ بالمكان   poh
#     في معجم بدج (ص 244) تفيد 'ب ح' ومشتقاتها: بلوغ الغاية، الوصول، النهاية.
#     في مادة 'بحح' العربية (ثلاثي 'بح') : التبحج؛ التمكن في الحلول والمقام.
#
# فالعنوانُ يحملُ النواةَ والمعنى والكلمةَ القبطيّة، والمتنُ يحملُ الجذرَ الثلاثيَّ
# بنصِّ معجمِه. **وهذا لسانُنا الأعلى في نسبةِ النواة (85.6%)**، فبنيةُ كتابِه
# شاهدةٌ على ذلك من طريقٍ مستقلٍّ عنّا.
RX_COPT_HEAD = re.compile(r"^##+\s+(.{2,90}?)\s*$", re.M)
RX_COPT_LATIN = re.compile(r"([a-zàâäèéêëîïôöùûüō][a-zàâäèéêëîïôöùûüō,\s]{1,28})$")
RX_COPT_ROOT = re.compile(r"في\s*مادة\s*['\"‹«]?\s*([ء-ي]{2,6})")
RX_COPT_THREE = re.compile(r"ثلاثي\s*['\"‹«]?\s*([ء-ي]{2,4})")
RX_COPT_BINARY_AFTER = re.compile(
    r"ثنائي(?:ة)?\s*['\"‹«]?\s*([ء-ي]{2,3})(?![ء-ي])"
)
RX_COPT_BINARY_BEFORE = re.compile(
    r"['\"‹«]?\s*([ء-ي]{2,3})(?![ء-ي])\s*['\"›»]?\s*الثنائي"
)


def coptic_nucleus(body: str) -> str:
    """استخرج تسمية خشيم الثنائية، وقد تأتي قبل لفظ «الثنائي» أو بعده."""
    after = RX_COPT_BINARY_AFTER.search(body)
    before = RX_COPT_BINARY_BEFORE.search(body)
    # صيغة «الجذر الثنائي طب» ينبغي أن تعطي `طب` لا الكلمة السابقة `جذر`؛
    # لذلك تكون جهة ما بعد الصفة أولى، ولا نرجع إلى السابقة إلا عند «رم الثنائي».
    if after:
        return after.group(1)
    if before and before.group(1) != "جذر":
        return before.group(1)
    # يكتب خشيم أحيانًا الصيغة «ثلاثي بح» وهو يعني أن بح نواة بحح؛ لا يؤخذ
    # من هذا الباب إلا ما كان ثنائي الحروف فعلًا.
    three = RX_COPT_THREE.search(body)
    return three.group(1) if three and len(three.group(1)) == 2 else ""


def mine_coptic(md: pathlib.Path) -> list[dict]:
    text = md.read_text(encoding="utf-8")
    blocks = re.split(r"(?m)^##+\s+", text)[1:]
    pairs, seen = [], set()
    for block in blocks:
        head, _, body = block.partition("\n")
        head = clean(head)
        m = RX_COPT_LATIN.search(head)
        if not m:
            continue
        coptic = " ".join(m.group(1).split())
        gloss = clean(head[: m.start()])
        rm = RX_COPT_ROOT.search(body[:1400]) or RX_COPT_THREE.search(body[:1400])
        if not rm:
            continue
        root = rm.group(1)
        nucleus = coptic_nucleus(body[:1400])
        key = (coptic, root)
        if key in seen or len(root) < 2:
            continue
        seen.add(key)
        pairs.append({
            "tongue_ar": "القبطيّة", "tongue": "coptic",
            "foreign": coptic, "foreign_sense": gloss[:90],
            "arabic_root": root,
            "arabic_nucleus": nucleus,
            "arabic_gloss": clean(re.sub(r"\s+", " ", body[:220])),
            "source": "ocr-coptic",
        })
    return pairs

# ------------------------------------------------- «البرهانُ على عروبةِ المصريّة»
# **بنيتُه ثلاثيّةٌ لا ثنائيّة**، وهي أقربُ ما رأيناه إلى بطاقاتِنا:
#
#     skher-t 𓊖, defeat, overthrow.
#     سَخَرَتْ : هَزِيمَةٌ، قَلْبٌ.
#
#     ses-t 𓂋, Rec. 15, 152, a garment of some kind, bandlet.
#     * سست : نوع من الثياب، عصابة (شاش، شاشة).
#
# فالسطرُ الأوّلُ نطقُ الكلمةِ المصريّةِ ورمزُها ومعناها الإنجليزيُّ من بدج،
# والثاني مقابلُها العربيُّ ونصُّه. **ويُحفَظُ الرمزُ الهيروغليفيُّ نفسُه** لأنّه
# مرساةُ البطاقةِ عندَنا لا النطقُ وحدَه.
RX_EG_ENTRY = re.compile(
    r"^\s*([a-zāḏḥḫḳṣṭṯẖʿꜣꜥ][a-zāēīōūḏḥḫḳṣṭṯẖʿꜣꜥ0-9\-\.\s]{1,26}?)\s*"
    r"([\U00013000-\U0001342F]*)\s*,\s*(.{4,150})$")
RX_EG_ANSWER = re.compile(r"^[\s*·•]*([ء-ي][ء-يًٌٍَُِّْـ/\s]{0,20}?)\s*[:：]\s*(.{2,180})$")
RX_REFS = re.compile(r"\b(?:B\.?D\.?|U\.?|P\.?|N\.?|M\.?|T\.?|Rec\.?|IV|V|Peasant|Israel|"
                     r"Amen\.?|Ebers|Westc\.?|Hh\.?|Thes\.?|Mar\.?|Copt\.?)[\s\d,\.\(\)A-Za-z]{0,26}")
_TASHKEEL = dict.fromkeys(range(0x064B, 0x0653))


def bare_ar(s: str) -> str:
    return unicodedata.normalize("NFC", s).translate(_TASHKEEL).replace("ـ", "")


def mine_egyptian(md: pathlib.Path) -> list[dict]:
    lines = [x.strip() for x in md.read_text(encoding="utf-8").splitlines()]
    pairs, seen = [], set()
    for i, line in enumerate(lines):
        if AR.search(line):
            continue
        m = RX_EG_ENTRY.match(line)
        if not m:
            continue
        translit = clean(m.group(1))
        glyphs = m.group(2)
        english = clean(RX_REFS.sub("", m.group(3)))
        if len(translit) < 2 or len(english) < 4:
            continue
        # الجوابُ العربيُّ في السطرَينِ التاليَين
        for fwd in (1, 2, 3):
            if i + fwd >= len(lines):
                break
            am = RX_EG_ANSWER.match(lines[i + fwd])
            if not am:
                continue
            arabic = bare_ar(clean(am.group(1))).replace("/", "")
            gloss = bare_ar(clean(am.group(2)))
            if len(re.sub(r"[^ء-ي]", "", arabic)) < 2:
                break
            key = (translit, arabic)
            if key in seen:
                break
            seen.add(key)
            pairs.append({
                "tongue_ar": "المصريّةُ القديمة", "tongue": "egyptian",
                "foreign": translit, "glyphs": glyphs,
                "foreign_sense": english[:110],
                "arabic_root": arabic, "arabic_gloss": gloss[:180],
                "source": "ocr-egyptian2",
            })
            break
    return pairs


# -------------------------------- حصادُ الجُمَلِ الصريحةِ في بقيّةِ كتبِ خشيم
# «رحلةُ الكلماتِ الثانية» و«آلهةُ مصرَ العربيّةُ 2» كتابا فصولٍ لا معجمين؛
# وكذلك كتابُ الندوةِ مجموعةُ بحوثٍ لتسعةِ سابقين. فلا مرساةَ فيهما من قبيل
# `ع :`، ولكنّ صيغةَ النسبةِ صريحةٌ ومتكرّرةٌ:
#
#     في المصرية يسمّى اليوم «ه ر و» ... وهذه مقلوب العربية «وهر»
#     «ق ر» ... وهي العربية: قر
#
# نأخذُ الجملتَينِ ذواتَي الاسمِ القديمِ والمقابلِ العربيِّ ولا نحكمُ عليهما.
CLAIM_TONGUES = [
    (re.compile(r"المصري(?:ة|ه)(?:\s+القديم(?:ة|ه))?"), "المصريّةُ القديمة", "egyptian"),
    (re.compile(r"(?:الأكّادي(?:ة|ه)|الأكادي(?:ة|ه)|البابلي(?:ة|ه)|الآشوري(?:ة|ه))"),
     "الأكّاديّة", "akkadian"),
    (re.compile(r"القبطي(?:ة|ه)"), "القبطيّة", "coptic"),
    (re.compile(r"اللاتيني(?:ة|ه)"), "اللاتينيّة", "old-latin"),
    (re.compile(r"(?:اليوناني(?:ة|ه)|الإغريقي(?:ة|ه)|الاغريقي(?:ة|ه))"),
     "اليونانيّةُ القديمة", "ancient-greek"),
    (re.compile(r"السومري(?:ة|ه)"), "السومريّة", "sumerian"),
    (re.compile(r"(?:الكنعاني(?:ة|ه)|الفينيقي(?:ة|ه)|الأوغاريتي(?:ة|ه)|الاوغاريتي(?:ة|ه))"),
     "الكنعانيّة", "canaanite"),
    (re.compile(r"(?:السرياني(?:ة|ه)|الآرامي(?:ة|ه)|الارامي(?:ة|ه))"),
     "الآراميّة", "aramaic"),
    (re.compile(r"العبري(?:ة|ه)"), "العبريّة", "hebrew"),
    (re.compile(r"(?:السبئي(?:ة|ه)|المسندي(?:ة|ه)|الحميري(?:ة|ه))"),
     "العربيّةُ الجنوبيّةُ القديمة", "old-south-arabian"),
    (re.compile(r"(?:الليبي(?:ة|ه)\s+القديم(?:ة|ه)|الأمازيغي(?:ة|ه)|الامازيغي(?:ة|ه)|التماشق)"),
     "الليبيّةُ القديمة", "ancient-libyan"),
]
RX_CLAIM_MARKER = re.compile(
    r"(?:هي|هى|ذاتها|مقلوب|مكاف|يقابل|تقابل|نكاف|نقابل|يكاف|تكاف|يساو|تساو|"
    r"أصل|اصل|من|ب)\S{0,8}\s+العربي(?:ة|ه)|بالعربي(?:ة|ه)"
)
RX_GUILLEMET = re.compile(r"[«\[]\s*([^»\]\n]{1,36}?)\s*[»\]]")
RX_ARABIC_AFTER = re.compile(r"العربي(?:ة|ه)\s*[:：=]?\s*([ء-ي][ء-يًٌٍَُِّْـ\s/]{1,18})")
CLAIM_AR_NOISE = {
    "العربية", "الفصحى", "الفصيحة", "الفصبحة", "المصرية", "القديمة",
    "اصلا", "في", "من", "الى", "يطلق", "تطلق", "يشرح", "معنى", "وهي", "وهو",
}

CLAIM_BOOKS = {
    "ocr-khashim-journey2": ("علي فهمي خشيم", None),
    "ocr-khashim-gods2": ("علي فهمي خشيم", ("المصريّةُ القديمة", "egyptian")),
    "ocr-khashim-dialects": ("بحوثُ ندوةِ الوحدةِ والتنوّع", None),
}

# «رحلةُ الكلماتِ الأولى» و«آلهةُ مصرَ العربيّةُ 1» ممسوحان بمسترال، لكنّ
# الفصلَينِ الطويلينِ يكثرُ فيهما ذكرُ أسماءِ الباحثين والكتب بين علامتَي
# تنصيص؛ لذلك كان الحاصدُ العامُّ يخلطُها بطرفَي الزوج. هذه مواضعُ النِّسَبِ
# الصريحةِ المفحوصةُ في المسح الأقوى، لا اختيارٌ بحسب قانونٍ ولا حكمٌ على دعوى.
# الصيغة: (المصدر، السطر، اسم اللسان، مفتاحه، اللفظ القديم، البدائل العربية).
EARLY_VOLUME_CLAIMS = [
    # رحلة الكلمات، الرحلة الأولى.
    ("ocr-khashim-journey1", 379, "اللاتينيّة", "old-latin", "dare", ("أدى", "يد")),
    ("ocr-khashim-journey1", 403, "المصريّةُ القديمة", "egyptian", "ع ر", ("عبر", "حمار")),
    ("ocr-khashim-journey1", 403, "المصريّةُ القديمة", "egyptian", "ب ر", ("بيت", "برت")),
    ("ocr-khashim-journey1", 403, "المصريّةُ القديمة", "egyptian", "دق", ("دقيق",)),
    ("ocr-khashim-journey1", 597, "اللاتينيّة", "old-latin", "PRC", ("فرج", "فرق")),
    ("ocr-khashim-journey1", 1201, "الليبيّةُ القديمة", "ancient-libyan", "أمن", ("ماء",)),
    ("ocr-khashim-journey1", 1208, "اليونانيّةُ القديمة", "ancient-greek", "Elyseus", ("إل",)),
    ("ocr-khashim-journey1", 1235, "اللاتينيّة", "old-latin", "Cornu Ammonis", ("قرن آمون",)),
    ("ocr-khashim-journey1", 1246, "المصريّةُ القديمة", "egyptian", "نطر", ("ناظر", "ناظور", "نطر")),
    ("ocr-khashim-journey1", 1246, "اليونانيّةُ القديمة", "ancient-greek", "nitron", ("نطرن",)),
    ("ocr-khashim-journey1", 1611, "المصريّةُ القديمة", "egyptian", "ب ن و", ("بان", "البين")),
    ("ocr-khashim-journey1", 1805, "المصريّةُ القديمة", "egyptian", "شنت", ("صون", "صونة")),
    ("ocr-khashim-journey1", 2099, "اللاتينيّة", "old-latin", "caput", ("قب",)),
    ("ocr-khashim-journey1", 2251, "اليونانيّةُ القديمة", "ancient-greek", "logos", ("لغي", "لغو", "لغة")),
    ("ocr-khashim-journey1", 2475, "اللاتينيّة", "old-latin", "Caesum", ("قصم", "قص")),
    ("ocr-khashim-journey1", 2475, "اللاتينيّة", "old-latin", "Caedo", ("قد",)),
    ("ocr-khashim-journey1", 2513, "اللاتينيّة", "old-latin", "SEPT", ("سبعت", "سبت", "سبع")),
    ("ocr-khashim-journey1", 2513, "المصريّةُ القديمة", "egyptian", "SFH", ("سبع",)),
    ("ocr-khashim-journey1", 3258, "المصريّةُ القديمة", "egyptian", "BNI't", ("بنة",)),
    ("ocr-khashim-journey1", 3258, "المصريّةُ القديمة", "egyptian", "BNI-IRY", ("الأري",)),
    ("ocr-khashim-journey1", 3258, "المصريّةُ القديمة", "egyptian", "BNI", ("بنين",)),
    ("ocr-khashim-journey1", 3324, "المصريّةُ القديمة", "egyptian", "SNTR", ("صندل",)),
    ("ocr-khashim-journey1", 3337, "اللاتينيّة", "old-latin", "ODOR", ("عطر",)),
    ("ocr-khashim-journey1", 3337, "اللاتينيّة", "old-latin", "ODOREM", ("عطر",)),
    ("ocr-khashim-journey1", 3393, "المصريّةُ القديمة", "egyptian", "نيث", ("عنات", "عناة")),
    ("ocr-khashim-journey1", 3393, "الكنعانيّة", "canaanite", "Anat", ("عنات", "عناة")),
    ("ocr-khashim-journey1", 3393, "اليونانيّةُ القديمة", "ancient-greek", "Attica", ("عتيقة",)),
    ("ocr-khashim-journey1", 3471, "الآراميّة", "aramaic", "مشيحا", ("مسيح", "مشياح")),
    ("ocr-khashim-journey1", 3620, "اللاتينيّة", "old-latin", "cupere", ("رغب",)),
    ("ocr-khashim-journey1", 3803, "اللاتينيّة", "old-latin", "giuppa", ("جبة",)),
    ("ocr-khashim-journey1", 4033, "الآراميّة", "aramaic", "أبراكاديرا", ("عبر", "دبر")),
    ("ocr-khashim-journey1", 4037, "اللاتينيّة", "old-latin", "Talisman", ("طلسم",)),
    ("ocr-khashim-journey1", 4103, "الإنكليزيّةُ القديمة", "old-english", "oste", ("حشد",)),
    ("ocr-khashim-journey1", 4440, "اللاتينيّة", "old-latin", "magister", ("مسيطر",)),
    ("ocr-khashim-journey1", 4734, "اللاتينيّة", "old-latin", "grandis", ("جرم", "قرن")),
    ("ocr-khashim-journey1", 4816, "اللاتينيّة", "old-latin", "amita", ("عمت", "عمة")),
    ("ocr-khashim-journey1", 4833, "اللاتينيّة", "old-latin", "ulu(s)", ("آل", "إيلة")),
    ("ocr-khashim-journey1", 4833, "اللاتينيّة", "old-latin", "avu", ("أبو",)),
    ("ocr-khashim-journey1", 4833, "اللاتينيّة", "old-latin", "avunculu(s)", ("آل الأب",)),
    ("ocr-khashim-journey1", 5235, "اليونانيّةُ القديمة", "ancient-greek", "polis", ("بلس", "بلد")),
    ("ocr-khashim-journey1", 5327, "اليونانيّةُ القديمة", "ancient-greek", "asto(s)", ("أست", "سته")),
    ("ocr-khashim-journey1", 5465, "اللاتينيّة", "old-latin", "fora", ("بر",)),
    ("ocr-khashim-journey1", 5567, "المصريّةُ القديمة", "egyptian", "WRG", ("ورق",)),
    ("ocr-khashim-journey1", 5567, "المصريّةُ القديمة", "egyptian", "WR", ("وري", "واري")),
    ("ocr-khashim-journey1", 5610, "اليونانيّةُ القديمة", "ancient-greek", "Typhon", ("طوفان",)),
    ("ocr-khashim-journey1", 5652, "الأكّاديّة", "akkadian", "agu", ("أخو", "أجو")),
    ("ocr-khashim-journey1", 5757, "اليونانيّةُ القديمة", "ancient-greek", "exo", ("أقصى",)),
    ("ocr-khashim-journey1", 5757, "اللاتينيّة", "old-latin", "ex", ("قصاء", "قص")),
    ("ocr-khashim-journey1", 5757, "اللاتينيّة", "old-latin", "exit", ("قصاة", "قصوة")),
    ("ocr-khashim-journey1", 6063, "اللاتينيّة", "old-latin", "Secretarium", ("سكر",)),
    ("ocr-khashim-journey1", 6066, "اللاتينيّة", "old-latin", "cor", ("غور", "قور")),
    ("ocr-khashim-journey1", 6463, "المصريّةُ القديمة", "egyptian", "P.t", ("باء",)),
    ("ocr-khashim-journey1", 6463, "المصريّةُ القديمة", "egyptian", "B.t", ("باء",)),
    ("ocr-khashim-journey1", 6463, "المصريّةُ القديمة", "egyptian", "Wa", ("وأى",)),
    ("ocr-khashim-journey1", 6476, "اليونانيّةُ القديمة", "ancient-greek", "hodo(s)", ("هذي", "هذى")),
    ("ocr-khashim-journey1", 6873, "اليونانيّةُ القديمة", "ancient-greek", "prikè", ("فرق",)),
    ("ocr-khashim-journey1", 6886, "الكنعانيّة", "canaanite", "phari", ("بر",)),
    ("ocr-khashim-journey1", 6886, "اللاتينيّة", "old-latin", "farina", ("بر",)),
    ("ocr-khashim-journey1", 6886, "اللاتينيّة", "old-latin", "fruga", ("بر",)),
    ("ocr-khashim-journey1", 6886, "اللاتينيّة", "old-latin", "Afer", ("عابر", "عفر")),
    ("ocr-khashim-journey1", 6886, "الكنعانيّة", "canaanite", "ف ر ق", ("فرق",)),
    ("ocr-khashim-journey1", 7253, "المصريّةُ القديمة", "egyptian", "hrw", ("وهر",)),
    ("ocr-khashim-journey1", 7253, "اليونانيّةُ القديمة", "ancient-greek", "hora", ("وهر",)),
    ("ocr-khashim-journey1", 7442, "المصريّةُ القديمة", "egyptian", "MKR", ("ماكر",)),
    ("ocr-khashim-journey1", 7442, "العربيّةُ الجنوبيّةُ القديمة", "old-south-arabian", "MKR", ("مكر",)),
    ("ocr-khashim-journey1", 7505, "اللاتينيّة", "old-latin", "capt", ("قض",)),
    ("ocr-khashim-journey1", 7770, "اليونانيّةُ القديمة", "ancient-greek", "Sériko(s)", ("سرق",)),
    ("ocr-khashim-journey1", 7846, "اليونانيّةُ القديمة", "ancient-greek", "Nilu(s)", ("النيل",)),
    ("ocr-khashim-journey1", 7846, "اللاتينيّة", "old-latin", "lin", ("نيل",)),
    ("ocr-khashim-journey1", 7846, "اللاتينيّة", "old-latin", "linea", ("نيل",)),
    ("ocr-khashim-journey1", 8069, "اللاتينيّة", "old-latin", "mantel", ("منديل",)),
    ("ocr-khashim-journey1", 9049, "اللاتينيّة", "old-latin", "fra-gula", ("بر", "غلة")),
    ("ocr-khashim-journey1", 9249, "اللاتينيّة", "old-latin", "cyprium", ("صفر",)),
    ("ocr-khashim-journey1", 12282, "السريانيّة", "aramaic", "skima", ("سقم", "قسم")),

    # آلهة مصر العربية، الجزء الأول.
    ("ocr-khashim-gods1", 122, "المصريّةُ القديمة", "egyptian", "sbh", ("سبح",)),
    ("ocr-khashim-gods1", 665, "المصريّةُ القديمة", "egyptian", "ر ث", ("رس",)),
    ("ocr-khashim-gods1", 777, "الإتروسكيّة", "etruscan", "Rasenna", ("رسن", "رصن", "رزن")),
    ("ocr-khashim-gods1", 1323, "المصريّةُ القديمة", "egyptian", "ن ب", ("هب",)),
    ("ocr-khashim-gods1", 1326, "المصريّةُ القديمة", "egyptian", "ت ن ب", ("طية نابية", "طية نبية", "نبط")),
    ("ocr-khashim-gods1", 1795, "اليونانيّةُ القديمة", "ancient-greek", "Yksows", ("هكسوس",)),
    ("ocr-khashim-gods1", 1799, "المصريّةُ القديمة", "egyptian", "Amu", ("أمم",)),
    ("ocr-khashim-gods1", 1799, "العِبريّة", "hebrew", "أوميم", ("أمم",)),
    ("ocr-khashim-gods1", 1808, "المصريّةُ القديمة", "egyptian", "ح ق", ("حق",)),
    ("ocr-khashim-gods1", 1808, "المصريّةُ القديمة", "egyptian", "ح أ ق", ("حلق", "حوق", "حيق")),
    ("ocr-khashim-gods1", 1818, "المصريّةُ القديمة", "egyptian", "Sōsawa", ("سيس",)),
    ("ocr-khashim-gods1", 1942, "المصريّةُ القديمة", "egyptian", "وع ر", ("حور", "حارة")),
    ("ocr-khashim-gods1", 1942, "اليونانيّةُ القديمة", "ancient-greek", "Avaris", ("حور",)),
    ("ocr-khashim-gods1", 1942, "اليونانيّةُ القديمة", "ancient-greek", "Auris", ("حور",)),
    ("ocr-khashim-gods1", 2101, "المصريّةُ القديمة", "egyptian", "ن ب", ("رب",)),
    ("ocr-khashim-gods1", 2101, "البابليّة", "akkadian", "نبو", ("رب",)),
    ("ocr-khashim-gods1", 2101, "المصريّةُ القديمة", "egyptian", "ن ب و ي", ("الربان",)),
    ("ocr-khashim-gods1", 2300, "المصريّةُ القديمة", "egyptian", "ب ر", ("بيت",)),
    ("ocr-khashim-gods1", 2300, "المصريّةُ القديمة", "egyptian", "ب ر ع", ("البيت الكبير", "القصر")),
    ("ocr-khashim-gods1", 2469, "الأكّاديّة", "akkadian", "eburu", ("بر",)),
    ("ocr-khashim-gods1", 2469, "السومريّة", "sumerian", "BURU", ("بر",)),
    ("ocr-khashim-gods1", 2470, "اللاتينيّة", "old-latin", "Frug", ("بر",)),
    ("ocr-khashim-gods1", 2648, "المصريّةُ القديمة", "egyptian", "م س", ("مشيمة",)),
    ("ocr-khashim-gods1", 2737, "المصريّةُ القديمة", "egyptian", "إ ب", ("لب",)),
    ("ocr-khashim-gods1", 2781, "المصريّةُ القديمة", "egyptian", "د س", ("ذات", "جثة")),
    ("ocr-khashim-gods1", 2808, "المصريّةُ القديمة", "egyptian", "أخ", ("أرخ",)),
    ("ocr-khashim-gods1", 2837, "المصريّةُ القديمة", "egyptian", "خ ف ت ي", ("خفت", "خفف")),
    ("ocr-khashim-gods1", 3156, "المصريّةُ القديمة", "egyptian", "gmi", ("جمع", "جمأ")),
    ("ocr-khashim-gods1", 3202, "المصريّةُ القديمة", "egyptian", "ح ع ب ي", ("حفي",)),
    ("ocr-khashim-gods1", 3341, "المصريّةُ القديمة", "egyptian", "s d", ("ساد", "سد")),
    ("ocr-khashim-gods1", 3346, "المصريّةُ القديمة", "egyptian", "s d(s)", ("سد",)),
    ("ocr-khashim-gods1", 3353, "المصريّةُ القديمة", "egyptian", "d t", ("ذات",)),
    ("ocr-khashim-gods1", 3607, "المصريّةُ القديمة", "egyptian", "sw", ("ضوء",)),
    ("ocr-khashim-gods1", 3607, "المصريّةُ القديمة", "egyptian", "n r w", ("روع", "رعى")),
    ("ocr-khashim-gods1", 3615, "المصريّةُ القديمة", "egyptian", "dn s", ("دنس", "ضنك")),
    ("ocr-khashim-gods1", 3690, "المصريّةُ القديمة", "egyptian", "qbb", ("قأب",)),
    ("ocr-khashim-gods1", 3981, "المصريّةُ القديمة", "egyptian", "Payt", ("بيت",)),
    ("ocr-khashim-gods1", 3981, "المصريّةُ القديمة", "egyptian", "Bayt", ("بيت",)),
    ("ocr-khashim-gods1", 3983, "اليونانيّةُ القديمة", "ancient-greek", "Beta", ("بيت",)),
    ("ocr-khashim-gods1", 3986, "المصريّةُ القديمة", "egyptian", "pa", ("باء", "فاء")),
    ("ocr-khashim-gods1", 4526, "المصريّةُ القديمة", "egyptian", "in(w)", ("إناء",)),
    ("ocr-khashim-gods1", 4528, "المصريّةُ القديمة", "egyptian", "n i w", ("إناء",)),
    ("ocr-khashim-gods1", 4624, "المصريّةُ القديمة", "egyptian", "wdi", ("يد", "أيد", "ودى", "أدى", "أودى")),
    ("ocr-khashim-gods1", 4625, "المصريّةُ القديمة", "egyptian", "ThTht", ("ثبت",)),
    ("ocr-khashim-gods1", 4639, "المصريّةُ القديمة", "egyptian", "dt", ("طوط",)),
    ("ocr-khashim-gods1", 4661, "الكنعانيّة", "canaanite", "طيط", ("طوط", "طاط")),
    ("ocr-khashim-gods1", 4662, "المصريّةُ القديمة", "egyptian", "d t", ("دود",)),
    ("ocr-khashim-gods1", 4668, "المصريّةُ القديمة", "egyptian", "djed", ("شدا", "دود")),
    ("ocr-khashim-gods1", 4743, "اليونانيّةُ القديمة", "ancient-greek", "alphabetus", ("ألف باء تاء",)),
    ("ocr-khashim-gods1", 4908, "المصريّةُ القديمة", "egyptian", "م س", ("ولد", "الوليد")),
    ("ocr-khashim-gods1", 4910, "المصريّةُ القديمة", "egyptian", "رع", ("رأى", "رعى")),
    ("ocr-khashim-gods1", 4911, "العربيّةُ الجنوبيّةُ القديمة", "old-south-arabian", "ذ", ("ذو",)),
    ("ocr-khashim-gods1", 5089, "المصريّةُ القديمة", "egyptian", "ن خ ت", ("نخط",)),
    ("ocr-khashim-gods1", 5286, "اللاتينيّة", "old-latin", "pupillu(s)", ("بؤبؤ",)),
    ("ocr-khashim-gods1", 5437, "المصريّةُ القديمة", "egyptian", "م ر", ("رام", "مرام")),
    ("ocr-khashim-gods1", 5440, "المصريّةُ القديمة", "egyptian", "إرى", ("رأى", "رائية")),
    ("ocr-khashim-gods1", 5441, "اليونانيّةُ القديمة", "ancient-greek", "mieirê(s)", ("مرام الرائية",)),
    ("ocr-khashim-gods1", 5465, "المصريّةُ القديمة", "egyptian", "س ب ك", ("سمك",)),
    ("ocr-khashim-gods1", 5562, "الأكّاديّة", "akkadian", "nāru", ("نهر",)),
    ("ocr-khashim-gods1", 5616, "المصريّةُ القديمة", "egyptian", "ود(ي)", ("وجأ", "ودي")),
    ("ocr-khashim-gods1", 5616, "المصريّةُ القديمة", "egyptian", "مو", ("ماء",)),
    ("ocr-khashim-gods1", 5632, "المصريّةُ القديمة", "egyptian", "سمر", ("سمير",)),
    ("ocr-khashim-gods1", 5635, "المصريّةُ القديمة", "egyptian", "شمو", ("شمس",)),
    ("ocr-khashim-gods1", 5690, "المصريّةُ القديمة", "egyptian", "snq", ("ثلج",)),
    ("ocr-khashim-gods1", 5698, "المصريّةُ القديمة", "egyptian", "س خ م", ("سخم",)),
    ("ocr-khashim-gods1", 5767, "المصريّةُ القديمة", "egyptian", "أ ب د", ("أبد",)),
    ("ocr-khashim-gods1", 5767, "اليونانيّةُ القديمة", "ancient-greek", "Abydos", ("أبد",)),
    ("ocr-khashim-gods1", 5934, "المصريّةُ القديمة", "egyptian", "ك م", ("كم", "سمرة")),
    ("ocr-khashim-gods1", 5957, "المصريّةُ القديمة", "egyptian", "ك م ت", ("كمت", "كميت")),
    ("ocr-khashim-gods1", 5970, "المصريّةُ القديمة", "egyptian", "ك م ت", ("كمة", "مكمة")),
    ("ocr-khashim-gods1", 6061, "المصريّةُ القديمة", "egyptian", "ت ر", ("تور", "تارة", "ترعة")),
    ("ocr-khashim-gods1", 6071, "اليونانيّةُ القديمة", "ancient-greek", "Neilos", ("هل", "نهر")),
    ("ocr-khashim-gods1", 6091, "المصريّةُ القديمة", "egyptian", "ن هر ت", ("نهر",)),
    ("ocr-khashim-gods1", 6137, "المصريّةُ القديمة", "egyptian", "دش ر", ("شقر",)),
    ("ocr-khashim-gods1", 6330, "المصريّةُ القديمة", "egyptian", "س ون", ("سوم",)),
    ("ocr-khashim-gods1", 6334, "المصريّةُ القديمة", "egyptian", "ن ب", ("ذهب", "هب")),
    ("ocr-khashim-gods1", 6351, "المصريّةُ القديمة", "egyptian", "تأ", ("طية",)),
    ("ocr-khashim-gods1", 6351, "المصريّةُ القديمة", "egyptian", "سني", ("سن", "سنن")),
    ("ocr-khashim-gods1", 6398, "المصريّةُ القديمة", "egyptian", "ح ت", ("حيط",)),
    ("ocr-khashim-gods1", 6398, "المصريّةُ القديمة", "egyptian", "نب", ("نب", "هب")),
    ("ocr-khashim-gods1", 6406, "المصريّةُ القديمة", "egyptian", "خ م ن", ("ثمن", "ثمان", "ثمانية")),
    ("ocr-khashim-gods1", 6406, "القبطيّة", "coptic", "شمن", ("ثمن", "ثمان", "ثمانية")),
    ("ocr-khashim-gods1", 6429, "المصريّةُ القديمة", "egyptian", "ح ر", ("حر",)),
    ("ocr-khashim-gods1", 6429, "المصريّةُ القديمة", "egyptian", "ور", ("وري",)),
    ("ocr-khashim-gods1", 6459, "المصريّةُ القديمة", "egyptian", "تأ", ("طية",)),
    ("ocr-khashim-gods1", 6461, "المصريّةُ القديمة", "egyptian", "دهنت", ("دهن",)),
    ("ocr-khashim-gods1", 6490, "المصريّةُ القديمة", "egyptian", "حوت", ("حوط", "حائط")),
    ("ocr-khashim-gods1", 6559, "المصريّةُ القديمة", "egyptian", "ش ن د ت", ("سنط",)),
    ("ocr-khashim-gods1", 6570, "المصريّةُ القديمة", "egyptian", "س ن ت", ("سنة",)),
    ("ocr-khashim-gods1", 6662, "المصريّةُ القديمة", "egyptian", "منت", ("يمنة",)),
    ("ocr-khashim-gods1", 6695, "الأكّاديّة", "akkadian", "šūtu", ("شوي",)),
    ("ocr-khashim-gods1", 6709, "المصريّةُ القديمة", "egyptian", "س ب د", ("سفد",)),
    ("ocr-khashim-gods1", 6709, "المصريّةُ القديمة", "egyptian", "س ب ك", ("سمك",)),
    ("ocr-khashim-gods1", 6775, "المصريّةُ القديمة", "egyptian", "ح ت", ("حوط", "حيط", "حائط")),
    ("ocr-khashim-gods1", 6775, "المصريّةُ القديمة", "egyptian", "وع ر ت", ("وعر", "وعرة")),
    ("ocr-khashim-gods1", 7050, "المصريّةُ القديمة", "egyptian", "ع ن ت", ("عنت",)),
    ("ocr-khashim-gods1", 7050, "الكنعانيّة", "canaanite", "عنت", ("عنت", "عنات")),
    ("ocr-khashim-gods1", 7050, "اليونانيّةُ القديمة", "ancient-greek", "Antaeus", ("عنت",)),
    ("ocr-khashim-gods1", 7522, "المصريّةُ القديمة", "egyptian", "أش", ("أس",)),
    ("ocr-khashim-gods1", 7758, "المصريّةُ القديمة", "egyptian", "إش ت", ("آس", "آسة")),
    ("ocr-khashim-gods1", 7796, "المصريّةُ القديمة", "egyptian", "ي ر ع ي ت", ("يراعية", "يرعية")),
    ("ocr-khashim-gods1", 7942, "المصريّةُ القديمة", "egyptian", "أمون", ("أمن",)),
    ("ocr-khashim-gods1", 8005, "المصريّةُ القديمة", "egyptian", "إن ب", ("أنف", "لف")),
    ("ocr-khashim-gods1", 8164, "المصريّةُ القديمة", "egyptian", "س", ("ذو", "ذا", "ذي")),
    ("ocr-khashim-gods1", 8164, "المصريّةُ القديمة", "egyptian", "إري", ("إرة",)),
    ("ocr-khashim-gods1", 8205, "الليبيّةُ القديمة", "ancient-libyan", "وس ر", ("وزر",)),
    ("ocr-khashim-gods1", 8208, "المصريّةُ القديمة", "egyptian", "وس ر", ("يسر",)),
    ("ocr-khashim-gods1", 8338, "المصريّةُ القديمة", "egyptian", "س ب د", ("سفد",)),
    ("ocr-khashim-gods1", 8375, "المصريّةُ القديمة", "egyptian", "أست", ("عز", "عزة")),
    ("ocr-khashim-gods1", 8395, "اليونانيّةُ القديمة", "ancient-greek", "Isis", ("العزى", "عز")),
    ("ocr-khashim-gods1", 8447, "المصريّةُ القديمة", "egyptian", "با", ("بال",)),
    ("ocr-khashim-gods1", 8459, "المصريّةُ القديمة", "egyptian", "ك ف ء", ("كفل",)),
    ("ocr-khashim-gods1", 8459, "المصريّةُ القديمة", "egyptian", "م ع ب ء", ("معبل",)),
    ("ocr-khashim-gods1", 8459, "المصريّةُ القديمة", "egyptian", "ب ه ء", ("بهل",)),
    ("ocr-khashim-gods1", 8470, "المصريّةُ القديمة", "egyptian", "ح ء", ("حول",)),
    ("ocr-khashim-gods1", 8470, "المصريّةُ القديمة", "egyptian", "ح ء و", ("حلاء", "حلاوى")),
    ("ocr-khashim-gods1", 8470, "المصريّةُ القديمة", "egyptian", "خ ء ع", ("خلع",)),
    ("ocr-khashim-gods1", 8473, "الأكّاديّة", "akkadian", "bāu", ("بغى",)),
    ("ocr-khashim-gods1", 8473, "الآراميّة", "aramaic", "tebʿa", ("تبع",)),
    ("ocr-khashim-gods1", 8473, "السريانيّة", "aramaic", "بعا", ("بغى",)),
    ("ocr-khashim-gods1", 8581, "المصريّةُ القديمة", "egyptian", "ب", ("فر",)),
    ("ocr-khashim-gods1", 8581, "الأكّاديّة", "akkadian", "باؤ", ("بغا",)),
    ("ocr-khashim-gods1", 8633, "المصريّةُ القديمة", "egyptian", "ع ن ح ر ت", ("عنان الحرية",)),
    ("ocr-khashim-gods1", 8633, "اليونانيّةُ القديمة", "ancient-greek", "Anhur", ("عنان الحرية",)),
    ("ocr-khashim-gods1", 8719, "المصريّةُ القديمة", "egyptian", "ب ت ح", ("فتاح",)),
    ("ocr-khashim-gods1", 8719, "القبطيّة", "coptic", "ptah", ("فتاح",)),
    ("ocr-khashim-gods1", 8882, "المصريّةُ القديمة", "egyptian", "ت أ ت ي", ("طاوي",)),
    ("ocr-khashim-gods1", 9019, "اليونانيّةُ القديمة", "ancient-greek", "Hama", ("عم",)),
    ("ocr-khashim-gods1", 9144, "المصريّةُ القديمة", "egyptian", "ه ب", ("هب", "هبهب")),
    ("ocr-khashim-gods1", 9144, "المصريّةُ القديمة", "egyptian", "هبني", ("أبن",)),
    ("ocr-khashim-gods1", 9144, "اليونانيّةُ القديمة", "ancient-greek", "ebenos", ("أبن", "أبنوس")),
    ("ocr-khashim-gods1", 9192, "اللاتينيّة", "old-latin", "ebanu", ("أبن",)),
    ("ocr-khashim-gods1", 9368, "المصريّةُ القديمة", "egyptian", "ك ن ن ي", ("جني",)),
    ("ocr-khashim-gods1", 9392, "المصريّةُ القديمة", "egyptian", "ح ب", ("حف",)),
    ("ocr-khashim-gods1", 9459, "الأكّاديّة", "akkadian", "apu", ("حفأ", "حلفاء")),
    ("ocr-khashim-gods1", 9536, "المصريّةُ القديمة", "egyptian", "ح ت", ("حيط",)),
    ("ocr-khashim-gods1", 9536, "المصريّةُ القديمة", "egyptian", "ح ر", ("حر", "حور")),
    ("ocr-khashim-gods1", 9536, "اليونانيّةُ القديمة", "ancient-greek", "Horus", ("حر", "حور")),
    ("ocr-khashim-gods1", 9548, "المصريّةُ القديمة", "egyptian", "ح ت", ("حوت",)),
    ("ocr-khashim-gods1", 9548, "المصريّةُ القديمة", "egyptian", "م ح و ت", ("حوت",)),
    ("ocr-khashim-gods1", 9548, "المصريّةُ القديمة", "egyptian", "م ح ي ت", ("حيتان", "أحوات", "حوتات")),
    ("ocr-khashim-gods1", 9594, "المصريّةُ القديمة", "egyptian", "ح ر", ("حوم",)),
    ("ocr-khashim-gods1", 9651, "المصريّةُ القديمة", "egyptian", "ش ع", ("شيء", "سيء")),
    ("ocr-khashim-gods1", 9655, "المصريّةُ القديمة", "egyptian", "حا", ("أرح",)),
    ("ocr-khashim-gods1", 9655, "الكنعانيّة", "canaanite", "رشف", ("رشف",)),
    ("ocr-khashim-gods1", 9674, "المصريّةُ القديمة", "egyptian", "ح ض", ("حضأ",)),
    ("ocr-khashim-gods1", 9674, "المصريّةُ القديمة", "egyptian", "ور", ("وري",)),
    ("ocr-khashim-gods1", 9723, "الكنعانيّة", "canaanite", "قاف", ("قرد", "قوف")),
    ("ocr-khashim-gods1", 9727, "المصريّةُ القديمة", "egyptian", "أ ب و", ("فيل", "فيلة")),
    ("ocr-khashim-gods1", 9807, "المصريّةُ القديمة", "egyptian", "ح ق ت", ("غفة", "مغفة")),
    ("ocr-khashim-gods1", 9853, "المصريّةُ القديمة", "egyptian", "ح ك ع", ("حكل",)),
    ("ocr-khashim-gods1", 10013, "المصريّةُ القديمة", "egyptian", "ك", ("جاه", "قوي")),
    ("ocr-khashim-gods1", 10016, "المصريّةُ القديمة", "egyptian", "ح م ك", ("حوجاه", "حوقوي")),
    ("ocr-khashim-gods1", 10205, "المصريّةُ القديمة", "egyptian", "خ ب ر", ("خلف", "خفر")),
    ("ocr-khashim-gods1", 10507, "المصريّةُ القديمة", "egyptian", "خ ن س و", ("خنس", "خانس")),
    ("ocr-khashim-gods1", 10549, "المصريّةُ القديمة", "egyptian", "ور", ("وري",)),
    ("ocr-khashim-gods1", 10601, "المصريّةُ القديمة", "egyptian", "دوء", ("دعاء", "ضوء")),
    ("ocr-khashim-gods1", 10601, "المصريّةُ القديمة", "egyptian", "دوء ت", ("ثوى", "طوى", "طواء", "طية")),
    ("ocr-khashim-gods1", 10754, "المصريّةُ القديمة", "egyptian", "س", ("ذو",)),
    ("ocr-khashim-gods1", 10754, "المصريّةُ القديمة", "egyptian", "س ت", ("ذو طية",)),
    ("ocr-khashim-gods1", 10754, "المصريّةُ القديمة", "egyptian", "إ ب ط", ("بط",)),
    ("ocr-khashim-gods1", 10754, "المصريّةُ القديمة", "egyptian", "ن ع و", ("نعام",)),
    ("ocr-khashim-gods1", 10757, "المصريّةُ القديمة", "egyptian", "س ن ح م", ("هب", "سلعام")),
    ("ocr-khashim-gods1", 10757, "المصريّةُ القديمة", "egyptian", "ز ن ح م", ("ذو هم", "ذو نهب")),
    ("ocr-khashim-gods1", 10758, "الأكّاديّة", "akkadian", "harēbu", ("خرب",)),
    ("ocr-khashim-gods1", 10758, "العربيّةُ الجنوبيّةُ القديمة", "old-south-arabian", "أ ر ب ي", ("خربي",)),
    ("ocr-khashim-gods1", 10758, "الأكّاديّة", "akkadian", "arbī", ("هرب", "غرب", "عرب")),
    ("ocr-khashim-gods1", 10832, "المصريّةُ القديمة", "egyptian", "م س ح", ("مسح",)),
    ("ocr-khashim-gods1", 10845, "المصريّةُ القديمة", "egyptian", "م س خ", ("مسح",)),
    ("ocr-khashim-gods1", 10845, "اليونانيّةُ القديمة", "ancient-greek", "Suchos", ("ساق", "سحق", "صك")),
    ("ocr-khashim-gods1", 11027, "الأكّاديّة", "akkadian", "šūtu", ("شوط",)),
    ("ocr-khashim-gods1", 11027, "المصريّةُ القديمة", "egyptian", "س وت", ("شوط", "سوط", "سطا", "ساط")),
    ("ocr-khashim-gods1", 11030, "العربيّةُ الجنوبيّةُ القديمة", "old-south-arabian", "وص ت", ("سوط", "سطو")),
    ("ocr-khashim-gods1", 11056, "المصريّةُ القديمة", "egyptian", "ش ت", ("شطء",)),
    ("ocr-khashim-gods1", 11056, "المصريّةُ القديمة", "egyptian", "ك ر ت", ("كرت",)),
    ("ocr-khashim-gods1", 11056, "المصريّةُ القديمة", "egyptian", "ق ر د ن", ("كرن", "كرنين", "كرزم", "كرزيم", "كرزن", "كرزين")),
    ("ocr-khashim-gods1", 11087, "البابليّة", "akkadian", "شيد", ("شيطان", "شيديم", "أسياد")),
    ("ocr-khashim-gods1", 11199, "المصريّةُ القديمة", "egyptian", "ق ر ق ن ت ي", ("قرع",)),
]

# «التواصل دون انقطاع» كتابُ مقالاتٍ، فلا تنطبقُ عليه صيغةُ المعجم ولا مرساةُ
# الجملةِ الواحدة في `mine_claim_ocr`: كثيرٌ من الأزواج موزّعٌ على أسطرٍ
# متتابعة، وبعضُه قوائمُ أسماء. هذه قائمةُ المواضعِ الصريحة كما طُبعت، لا
# ترجيحٌ من الحاصد. وتُفصَل البدائلُ العربيّةُ في صفوفٍ كي لا يضيعَ واحدٌ منها.
# رقمُ السطرِ هو رقمُ DjVuTXT الرسميِّ في أرشيفِ الإنترنت.
CONTINUITY_CLAIMS = [
    (2792, "المصريّةُ القديمة", "egyptian", "آريا", ("حرية",)),
    (2792, "المصريّةُ القديمة", "egyptian", "حريا", ("حرية",)),
    (2794, "المصريّةُ القديمة", "egyptian", "كمت", ("كمت", "كميت")),
    (2797, "المصريّةُ القديمة", "egyptian", "تامرى", ("مر", "مروية")),
    (2802, "المصريّةُ القديمة", "egyptian", "ح ت", ("بيت", "حيط")),
    (2802, "المصريّةُ القديمة", "egyptian", "كا", ("جاه",)),
    (2802, "المصريّةُ القديمة", "egyptian", "بتاح", ("فتاح",)),
    (2805, "المصريّةُ القديمة", "egyptian", "مسترايا", ("مصر",)),
    (2807, "المصريّةُ القديمة", "egyptian", "نيلوس", ("النيل", "النهر", "نهل")),
    (2820, "الليبيّةُ القديمة", "ancient-libyan", "مشوش", ("مزاوغة",)),
    (2820, "الليبيّةُ القديمة", "ancient-libyan", "مخلوي", ("مغراوة",)),
    (2821, "الليبيّةُ القديمة", "ancient-libyan", "زاووكس", ("زواغة",)),
    (2821, "الليبيّةُ القديمة", "ancient-libyan", "غايتولي", ("جديلة", "جدالة")),
    (2822, "الليبيّةُ القديمة", "ancient-libyan", "نسامون", ("ناس أمون",)),
    (2837, "المصريّةُ القديمة", "egyptian", "عريبو", ("عرب", "أعراب")),
    (3164, "المصريّةُ القديمة", "egyptian", "ح ن", ("خان",)),
    (3164, "الأكّاديّة", "akkadian", "خ ن", ("خان",)),
    (3165, "الكنعانيّة", "canaanite", "بعل", ("بعل",)),
    (3201, "اللّاتينيّةُ القديمة", "old-latin", "سبتميوس", ("سبط",)),
    (3206, "اللّاتينيّةُ القديمة", "old-latin", "سيفروس", ("صوري",)),
    (3508, "الأكّاديّة", "akkadian", "أريبو", ("عرب",)),
    (3541, "اليونانيّةُ القديمة", "ancient-greek", "ليبو", ("عرب",)),
    (3541, "اليونانيّةُ القديمة", "ancient-greek", "لوبو", ("عرب",)),
    (3541, "المصريّةُ القديمة", "egyptian", "ريبو", ("عرب",)),
    (3542, "المصريّةُ القديمة", "egyptian", "عريبو", ("عرب",)),
    (3546, "المصريّةُ القديمة", "egyptian", "آمو", ("عمو", "أميون")),
    (3547, "العِبريّة", "hebrew", "أوميم", ("عمو", "أميون")),
    (3764, "الكنعانيّة", "canaanite", "قرت حدش", ("القرية الحديثة",)),
    (4117, "الأكّاديّة", "akkadian", "زقتو", ("زقطي",)),
    (4117, "الأكّاديّة", "akkadian", "شكتو", ("شوكة",)),
    (4123, "الأكّاديّة", "akkadian", "شوكتو", ("شوكة",)),
    (4124, "المصريّةُ القديمة", "egyptian", "س ب د", ("سفد", "سفود")),
    (4270, "الكنعانيّة", "canaanite", "قرت", ("قرية",)),
    (4518, "الأمازيغيّة", "amazigh", "م ز غ", ("مسك", "المك", "سمك")),
    (4519, "الأمازيغيّة", "amazigh", "م ش ك", ("مسك", "المك", "سمك")),
    (4522, "الأكّاديّة", "akkadian", "مشكو", ("مسك", "جلد")),
    (4552, "المصريّةُ القديمة", "egyptian", "ر ب و", ("عرب", "أعراب")),
    (4552, "المصريّةُ القديمة", "egyptian", "ع ر ب و", ("عرب", "أعراب")),
    (4875, "الأمازيغيّة", "amazigh", "سوف", ("سيف",)),
    (4879, "العربيّةُ الجنوبيّةُ القديمة", "old-south-arabian", "سف", ("سيف",)),
    (4900, "الأمازيغيّة", "amazigh", "م س", ("مز",)),
    (4904, "المصريّةُ القديمة", "egyptian", "س ن", ("هن",)),
    (4905, "العربيّةُ الجنوبيّةُ القديمة", "old-south-arabian", "س ن", ("هن",)),
    (4937, "المصريّةُ القديمة", "egyptian", "م س", ("مشى", "مسا")),
    (4939, "المصريّةُ القديمة", "egyptian", "ن س و", ("نشأ",)),
    (4946, "الأمازيغيّة", "amazigh", "أقليد", ("جلد", "سلط")),
    (4947, "الأمازيغيّة", "amazigh", "أجليط", ("جلد", "سلط")),
    (4947, "الأمازيغيّة", "amazigh", "أجليض", ("جلد", "سلط")),
    (4947, "الأمازيغيّة", "amazigh", "أتشليط", ("جلد", "سلط")),
    (4947, "الأمازيغيّة", "amazigh", "أجليد", ("جلد", "سلط")),
    (4948, "العربيّةُ الجنوبيّةُ القديمة", "old-south-arabian", "ي ل ط", ("سلط",)),
    (4950, "الكنعانيّة", "canaanite", "ج ل ت", ("جلد", "سلط")),
    (4978, "العِبريّة", "hebrew", "شليط", ("سلط",)),
    (5081, "المصريّةُ القديمة", "egyptian", "سفت", ("سبط",)),
    (5082, "الكنعانيّة", "canaanite", "ث ف ط", ("سبط",)),
    (5083, "العِبريّة", "hebrew", "شافاط", ("سبط",)),
    (5235, "المصريّةُ القديمة", "egyptian", "است", ("أست", "وست")),
    (5611, "المصريّةُ القديمة", "egyptian", "إزر", ("آزر", "أزير")),
    (6148, "الكنعانيّة", "canaanite", "بعل", ("بعل", "هبل")),
    (6151, "البابليّة", "babylonian", "عشتار", ("عشتر", "عثتر")),
    (6152, "الكنعانيّة", "canaanite", "عشترت", ("عشتر", "عثتر")),
    (6153, "العربيّةُ الجنوبيّةُ القديمة", "old-south-arabian", "عثتر", ("عشتر",)),
    (6153, "المصريّةُ القديمة", "egyptian", "منت", ("مناة",)),
    (6154, "المصريّةُ القديمة", "egyptian", "إمن", ("هامان", "آمين")),
    (6157, "الكنعانيّة", "canaanite", "حمن", ("هامان", "آمين")),
    (6160, "الكنعانيّة", "canaanite", "إل", ("ألل", "إله", "الله")),
    (6161, "الأكّاديّة", "akkadian", "إلو", ("ألل", "إله", "الله")),
    (6169, "الكنعانيّة", "canaanite", "إلت", ("اللات", "للا")),
    (6173, "المصريّةُ القديمة", "egyptian", "إز", ("العزى",)),
    (6175, "المصريّةُ القديمة", "egyptian", "حر", ("الحر",)),
    (6176, "الكنعانيّة", "canaanite", "حرن", ("الحر",)),
    (6176, "الكنعانيّة", "canaanite", "حورون", ("الحر",)),
    (6177, "الليبيّةُ القديمة", "ancient-libyan", "كرزل", ("كرز إل",)),
]

SYMPOSIUM_AUTHORS = [
    (257, "محمد بهجت قبيسي"),
    (1162, "نائل حنون"),
    (2851, "عكاشة الدالي"),
    (3078, "لؤي محمود سعيد"),
    (4484, "أشرف محمد فتحي"),
    (4937, "سعيد بن عبدالله الدارودي"),
    (7234, "عبدالعزيز سعيد الصويعي"),
    (7489, "أحمد شحلان"),
    (8915, "محمد المختار العرباوي"),
]


def _claim_author(source: str, line: int, fallback: str) -> str:
    if source != "ocr-khashim-dialects":
        return fallback
    author = "علي فهمي خشيم"
    for start, name in SYMPOSIUM_AUTHORS:
        if line < start:
            break
        author = name
    return author


def _claim_token(value: str, *, arabic: bool = False) -> str:
    value = clean(value).strip("()[]{}=<>١٢٣٤٥٦٧٨٩٠0123456789")
    value = re.sub(r"\s+", " ", value).strip()
    if arabic:
        words = re.findall(r"[ء-ي]{2,6}", bare_ar(value))
        if not words or words[0] in CLAIM_AR_NOISE:
            return ""
        return words[0]
    if len(value) > 32 or len(value.split()) > 5:
        return ""
    return value if re.search(r"[ء-يA-Za-z]", value) else ""


def mine_claim_ocr(md: pathlib.Path, source: str, author: str,
                   default_tongue: tuple[str, str] | None) -> list[dict]:
    """يلتقطُ الزوجَ حيثُ سمّى النصُّ اللسانَ القديمَ والعربيّةَ في جملةٍ واحدة.

    يُحفَظُ سياقُ الجملةِ ورقمُ السطرِ لأنّ OCR أرشيفِ الإنترنتِ مؤقّتٌ، ولأنّ
    إعادةَ المسحِ بمسترال ستسمحُ لاحقًا بردِّ الرسمِ القديمِ إذا شوّهه المسحُ.
    """
    # لا نستعمل `clean` هنا لأنّه يطرحُ علامتَي « »، وهما مرساتا طرفَي الزوج.
    lines = [re.sub(r"\s+", " ", unicodedata.normalize("NFC", x)).strip()
             for x in md.read_text(encoding="utf-8").splitlines()]
    rows, seen = [], set()
    for i, line in enumerate(lines):
        if "العربي" not in line and not any(
                "العربي" in lines[j] for j in range(max(0, i - 1), min(len(lines), i + 2))):
            continue
        window = " ".join(lines[max(0, i - 1):min(len(lines), i + 2)])
        marker = RX_CLAIM_MARKER.search(window)
        if not marker:
            continue

        tongue = None
        distances = []
        for rx, tongue_ar, tongue_key in CLAIM_TONGUES:
            for tm in rx.finditer(window):
                distances.append((abs(tm.start() - marker.start()), tongue_ar, tongue_key))
        if distances:
            _, tongue_ar, tongue_key = min(distances)
            tongue = (tongue_ar, tongue_key)
        elif default_tongue:
            tongue = default_tongue
        if not tongue:
            continue

        quotes = list(RX_GUILLEMET.finditer(window))
        after_quotes = [q for q in quotes if marker.start() <= q.start() <= marker.end() + 90]
        if after_quotes:
            aq = min(after_quotes, key=lambda q: abs(q.start() - marker.end()))
            arabic = _claim_token(aq.group(1), arabic=True)
        else:
            am = RX_ARABIC_AFTER.search(window, max(0, marker.start() - 10))
            aq = am
            arabic = _claim_token(am.group(1), arabic=True) if am else ""
        if not arabic:
            continue

        others = [q for q in quotes if q is not aq and abs(q.start() - marker.start()) <= 190]
        if not others:
            continue
        before = [q for q in others if q.start() < marker.start()]
        fq = max(before, key=lambda q: q.start()) if before else min(
            others, key=lambda q: abs(q.start() - marker.end()))
        foreign = _claim_token(fq.group(1))
        if not foreign or foreign == arabic:
            continue
        key = (tongue[1], foreign, arabic, source)
        if key in seen:
            continue
        seen.add(key)
        context = window[:360]
        rows.append({
            "tongue_ar": tongue[0], "tongue": tongue[1],
            "foreign": foreign, "foreign_sense": context,
            "arabic_root": arabic, "arabic_gloss": context,
            "source": source, "source_line": i + 1,
            "author": _claim_author(source, i + 1, author),
            "harvest_kind": "نسبةٌ صريحةٌ في جملةِ المصدر",
            "ocr_source": "Internet Archive DjVuTXT؛ مؤقّتٌ حتّى يتجدّد مفتاحُ Mistral",
        })
    return rows


# «هؤلاء الأباطرة وألقابهم العربية» يضمّ ملحقًا مستقلًّا صرّح خشيم في
# صدره ببنيته: اللفظ اليوناني، فمعناه، فالمقابل العربي. والملحق مرقّم من
# 1 إلى 145؛ لذا لا نمرّره على حاصد الجمل العام الذي يلتقط حواشي عارضة.
# هذه البدائل هي الطرف العربي كما طُبع، مفصولةً صفوفًا كي لا يضيع بديل.
EMPERORS_GREEK_ARABIC = {
    1: ("أكمة", "قمة"), 2: ("قدس",), 3: ("أحس", "إحساس"),
    4: ("عرق", "عريق"), 5: ("جن", "جنين", "كون"), 6: ("جنس",),
    7: ("جن", "جنين", "كون"), 8: ("قرص",),
    9: ("دن", "ديان", "دين", "دينونة"),
    10: ("فو", "فوة", "فاة", "تفوه"), 11: ("أرى", "الأري"),
    12: ("أرر", "أر", "يؤر"), 13: ("سطر", "أسطورة"), 14: ("كعب",),
    15: ("لغة", "لغا", "يلغو", "لغو"), 16: ("هدى",),
    17: ("مرج", "مزيح", "مزج"), 18: ("ميس", "ماس", "يميس"),
    19: ("سخر", "سخرية"), 20: ("سمة",), 21: ("ست", "سته", "استوى"),
    22: ("سمة", "شمة"), 23: ("شيمة",), 24: ("صفو", "صفاء"),
    25: ("طيرة",), 26: ("تقن",), 27: ("ثيب", "ثياب"), 28: ("طرف",),
    29: ("طبع",), 30: ("فو", "فاه", "يفوه", "تفوه", "فم"),
    31: ("قرن",), 32: ("أكر", "أكار", "مؤاكرة"), 33: ("أير", "هير"),
    34: ("نام", "أتم"), 35: ("عشتر", "عشتار", "عشتروت", "عشرت", "عشر"),
    36: ("قا", "قع", "قي", "قواء"), 37: ("زفير", "زفر"), 38: ("هالة",),
    39: ("حمارة",), 40: ("طلس", "أطلس"), 41: ("هدى",),
    42: ("أفر", "فور", "فاز", "يفور"), 43: ("خضر", "خضرم", "خضم"),
    44: ("صون", "صين", "صوان", "صينة", "صائن", "شنن"), 45: ("زق",),
    46: ("دسق", "ديسق"), 47: ("زن", "زنار"), 48: ("تقي", "تقية", "اتقاء"),
    49: ("قن", "قنا", "قانون"), 50: ("بلط", "بلاط", "بلاطة"),
    51: ("صقل", "مصقل", "مصقلة"), 52: ("ثوى", "مشوى"),
    53: ("شلامة", "شملة", "شمالة"), 54: ("خل", "حمض", "حامض"),
    55: ("ألق", "تألق", "انتلق"), 56: ("غرا", "غراء"),
    57: ("مرجان", "مرجانة"), 58: ("نظر", "ناظر"), 59: ("عنتر",),
    60: ("عرق", "عريق"), 61: ("خنة", "كنة", "جنة", "قنة"),
    62: ("دم", "أدم", "آدم", "أودم"), 63: ("دن", "ديان"),
    64: ("خلب", "خالب", "خلاب", "خانِب", "خناب"), 65: ("كرت", "كارت"),
    66: ("فطر", "فاطر", "أب"), 67: ("بلس", "بلد"), 68: ("فاه", "فم"),
    69: ("وري", "وار", "ورش", "ورشان"), 70: ("درع", "دراعة"),
    71: ("قرص",), 72: ("سيف",), 73: ("جبل", "جبيل"), 74: ("جرم",),
    75: ("ضو", "ضوء", "ضياء"), 76: ("حور", "حوري", "حواري", "حواريون"),
    77: ("مث", "مثل", "أمثولة"), 78: ("جبل", "جبيل"),
    79: ("همهم", "أمن", "أمين", "همن", "هامين"), 80: ("وهر",),
    81: ("قطم",), 82: ("قفن", "قفل"), 83: ("غر", "غرة", "جارية"),
    84: ("قرن",), 85: ("كيس", "كيسة"), 86: ("مخ",), 87: ("نير",),
    88: ("ورأ", "وراء"), 89: ("باء", "يبوء", "فاء", "يفيء", "آب"),
    90: ("برد", "برداء"), 91: ("تم",), 92: ("فيل", "ألفو"),
    93: ("ثور",), 94: ("جمل",), 95: ("غراب", "قرأ", "خار"),
    96: ("إلق",), 97: ("إلق",), 98: ("فعو", "أفعى", "أفعو", "فو", "أفى", "أفو"),
    99: ("عقرب",), 100: ("ثور",), 101: ("نمر",), 102: ("نعم", "نعمان"),
    103: ("ثوم",), 104: ("قلم",), 105: ("نرجس", "نهر", "ليلك"),
    106: ("نيل", "نيلي"), 107: ("مخ",), 108: ("رس",), 109: ("ورد",),
    110: ("ليف",), 111: ("فلفل",), 112: ("جود", "جيد", "أجاد", "أجود"),
    113: ("حج", "حاج"), 114: ("جلي",),
    115: ("وقر", "وقور", "موقر", "أجر", "ياجور", "يأجور"),
    116: ("عند", "عناد", "عنت", "تعنت", "عنيد"), 117: ("سوي", "سواء", "مساو"),
    118: ("كون", "كائن", "تكون", "كن"), 119: ("خلا", "يخلو", "خلو"),
    120: ("قرس", "قارس", "قر"), 121: ("ملس", "أملس", "ملق", "أملق", "ملد"),
    122: ("مق",), 123: ("نخر",), 124: ("بلي", "بال"),
    125: ("بلط", "بلاط"), 126: ("يبين", "بان"), 127: ("ورد",),
    128: ("ألق", "تألق", "انتلق"), 129: ("قاني", "قنا", "جون"),
    130: ("جمع", "جامع"), 131: ("جلف", "قلف"), 132: ("جرف", "قرف"),
    133: ("غلف",), 134: ("كون", "كين"), 135: ("كم", "غمم", "إغماء"),
    136: ("كرت",), 137: ("متر",), 138: ("شق", "شج", "جز", "قص", "شقّص"),
    139: ("بين", "أبان"), 140: ("وله", "ولع", "ولوع", "ولي", "وليّ"),
    141: ("فسد",), 142: ("على", "عن"), 143: ("عند", "عناد", "تعنت"),
    144: ("بارى", "يباري"), 145: ("ثني", "اثنان", "صنو"),
}

EMPERORS_GREEK_FOREIGN_OVERRIDES = {
    70: ("thorax", "thyreo-s"),
    88: ("ura", "oura"),
    89: ("pou-s", "podo-s"),
    129: ("kuan-os", "xanth-os"),
}


def mine_emperors_greek_glossary(md: pathlib.Path) -> list[dict]:
    """احصد الملحق اليوناني المرقّم كاملًا، مع بدائله العربية المطبوعة."""
    lines = md.read_text(encoding="utf-8").splitlines()
    head_rx = re.compile(r"^\s*(\d{1,3})\s*-\s*(.*?)\s*:\s*(.*)$")
    start = next(i for i, line in enumerate(lines) if line.strip() == "## مفردات عامة")
    end = next(i for i, line in enumerate(lines[start + 1:], start + 1)
               if line.strip().startswith("# العربية وأسماء الأعداد"))
    heads: list[tuple[int, int, str, str]] = []
    for i in range(start, end):
        line = lines[i]
        match = head_rx.match(line)
        if match and 1 <= int(match.group(1)) <= 145:
            heads.append((i, int(match.group(1)), clean(match.group(2)), clean(match.group(3))))
    numbers = [number for _, number, _, _ in heads]
    if numbers != list(range(1, 146)):
        raise SystemExit(f"اختلّ ترقيمُ ملحقِ الأباطرة: {numbers[:8]} ... {numbers[-8:]}")
    if set(EMPERORS_GREEK_ARABIC) != set(range(1, 146)):
        raise SystemExit("اختلّ فهرسُ بدائلِ ملحقِ الأباطرة")

    rows = []
    for pos, (i, number, foreign_head, meaning) in enumerate(heads):
        end = heads[pos + 1][0] if pos + 1 < len(heads) else i + 20
        context = clean(" ".join(lines[i:min(end, i + 16)]))[:900]
        foreign_forms = EMPERORS_GREEK_FOREIGN_OVERRIDES.get(number, (foreign_head,))
        for foreign in foreign_forms:
            for arabic in EMPERORS_GREEK_ARABIC[number]:
                rows.append({
                    "tongue_ar": "اليونانيّةُ القديمة", "tongue": "ancient-greek",
                    "foreign": foreign, "foreign_sense": meaning,
                    "arabic_root": arabic, "arabic_gloss": context,
                    "source": "ocr-khashim-emperors-greek-glossary",
                    "source_line": i + 1, "source_entry": number,
                    "author": "علي فهمي خشيم",
                    "harvest_kind": "مدخلٌ مرقّمٌ في ملحقِ المفردات اليونانيّة",
                    "ocr_source": "مسحُ Mistral المفحوص؛ اللفظُ والمقابلُ مطبوعان في المصدر",
                })
    return rows


def mine_continuity_claims(md: pathlib.Path) -> list[dict]:
    """يحصدُ مواضعَ «التواصل دون انقطاع» المفحوصةَ سطرًا سطرًا.

    لا يُستنبَطُ طرفٌ هنا من تشابهِ رسمٍ؛ القائمةُ أعلاهُ فهرسُ نسبٍ صريحةٍ
    في المصدر. ويُحفَظُ السياقُ المحيطُ بها لتبقى العودةُ إلى الصورةِ ممكنةً.
    """
    lines = md.read_text(encoding="utf-8").splitlines()
    rows, seen = [], set()
    for line_no, tongue_ar, tongue_key, foreign, arabic_forms in CONTINUITY_CLAIMS:
        if line_no < 1 or line_no > len(lines):
            raise SystemExit(
                f"خرجَ سطرُ التواصل من النص: {line_no} (الأسطر={len(lines)})"
            )
        context = clean(" ".join(
            lines[max(0, line_no - 3):min(len(lines), line_no + 2)]
        ))[:600]
        for arabic in arabic_forms:
            key = (tongue_key, foreign, arabic)
            if key in seen:
                continue
            seen.add(key)
            rows.append({
                "tongue_ar": tongue_ar, "tongue": tongue_key,
                "foreign": foreign, "foreign_sense": context,
                "arabic_root": arabic, "arabic_gloss": context,
                "source": "ocr-khashim-continuity", "source_line": line_no,
                "author": "علي فهمي خشيم",
                "harvest_kind": "موضعٌ صريحٌ مفحوصٌ في نصِّ المصدر",
                "ocr_source": (
                    "Internet Archive DjVuTXT؛ مؤقّتٌ حتّى يتجدّد مفتاحُ Mistral"
                ),
            })
    return rows


def mine_early_volume_claims() -> list[dict]:
    """يحصدُ فهرسَ المواضعِ المفحوصةِ في المجلّدينِ الأوّلين."""
    cache: dict[str, list[str]] = {}
    rows, seen = [], set()
    for source, line_no, tongue_ar, tongue_key, foreign, arabic_forms in EARLY_VOLUME_CLAIMS:
        if source not in cache:
            md = STORE / source / "full.md"
            if not md.exists():
                raise SystemExit(f"غابَ مسحُ المجلّدِ المبكّر: {md}")
            cache[source] = md.read_text(encoding="utf-8").splitlines()
        lines = cache[source]
        if line_no < 1 or line_no > len(lines):
            raise SystemExit(
                f"خرجَ سطرُ المجلّدِ المبكّر من النص: {source}:{line_no} "
                f"(الأسطر={len(lines)})"
            )
        context = clean(" ".join(
            lines[max(0, line_no - 3):min(len(lines), line_no + 2)]
        ))[:700]
        for arabic in arabic_forms:
            key = (source, tongue_key, foreign, arabic)
            if key in seen:
                continue
            seen.add(key)
            rows.append({
                "tongue_ar": tongue_ar, "tongue": tongue_key,
                "foreign": foreign, "foreign_sense": context,
                "arabic_root": arabic, "arabic_gloss": context,
                "source": source, "source_line": line_no,
                "author": "علي فهمي خشيم",
                "harvest_kind": "موضعٌ صريحٌ مفحوصٌ في نصِّ المصدر",
                "ocr_source": "Mistral OCR؛ قابلَه DjVuTXT الرسميُّ في أرشيفِ الإنترنت",
            })
    return rows


RX_DAWUDI_PAIR = re.compile(
    r"^\s*(?:[-–]|[٠-٩0-9]+\s*[-–])\s*"
    r"([ء-يًٌٍَُِّْـ][ء-يًٌٍَُِّْـ\s]{1,24}?)\s*[-–]\s*"
    r"([ء-يًٌٍَُِّْـ][ء-يًٌٍَُِّْـ\s]{1,24}?)\s*[:：]"
)


def mine_dawudi_list(md: pathlib.Path) -> list[dict]:
    """قائمةُ سعيد الدارودي: اللفظُ الأمازيغيُّ ثمّ مقابلُه العربيُّ في سطرٍ ثابت."""
    lines = md.read_text(encoding="utf-8").splitlines()
    rows, seen = [], set()
    # حدودُ بحثِه مطبوعةٌ في الكتاب: من العنوان عند السطر 4937 إلى البحث التالي.
    for line_no in range(4937, min(7234, len(lines) + 1)):
        line = unicodedata.normalize("NFC", lines[line_no - 1])
        match = RX_DAWUDI_PAIR.match(line)
        if not match:
            continue
        foreign = clean(match.group(1))
        arabic = _claim_token(match.group(2), arabic=True)
        if not foreign or not arabic:
            continue
        key = (foreign, arabic)
        if key in seen:
            continue
        seen.add(key)
        context = clean(" ".join(lines[line_no - 1:min(line_no + 2, len(lines))]))[:360]
        rows.append({
            "tongue_ar": "الأمازيغيّة", "tongue": "amazigh",
            "foreign": foreign, "foreign_sense": context,
            "arabic_root": arabic, "arabic_gloss": context,
            "source": "ocr-khashim-dialects", "source_line": line_no,
            "author": "سعيد بن عبدالله الدارودي",
            "harvest_kind": "قائمةٌ ثنائيّةُ العمودِ في بحثِ المصدر",
            "ocr_source": "Internet Archive DjVuTXT؛ مؤقّتٌ حتّى يتجدّد مفتاحُ Mistral",
        })
    return rows


def mine_ember_arabic_marked_lines(md: pathlib.Path) -> list[dict]:
    """احفظ كلَّ سطرٍ علَّمه إمبر صراحةً بالطرف العربيِّ «عر:».

    نسخةُ مكتبة الإسكندريّة الرسميّة ذاتُ نصٍّ مستخرجٍ مقروء، لكنَّ صفَّها
    متعدِّدَ الأعمدة خلط أحيانًا الرسمَ المصريَّ والمقابلَ العربيَّ في سطرٍ
    واحد، وأحيانًا شطرهما بين سطرين. لذلك لا نفرضُ فاصلًا آليًّا قد يبدِّل
    طرفَي الزوج؛ بل نحفظُ الجردَ الموسومَ كلَّه، سطرًا ورقمًا، من غير إسقاط.
    """
    lines = md.read_text(encoding="utf-8").splitlines()
    rows = []
    for line_no, raw in enumerate(lines, 1):
        normalized = unicodedata.normalize("NFKC", raw)
        normalized = re.sub(r"[ـ\u200e\u200f\u202a-\u202e]", "", normalized)
        normalized = re.sub(r"\s+", " ", normalized).strip()
        if not re.match(r"^عر\s*[:：]", normalized):
            continue
        rows.append({
            "source_line": line_no,
            "printed_line": normalized,
            "ancient_tongue": "المصريّةُ القديمة، ومعها المقابلاتُ العروبيّةُ التي سمّاها المؤلّف",
            "author": "آرون إمبر",
            "editor": "فريدا بنك",
            "translator_commentator": "علي فهمي خشيم",
            "source": "ocr-khashim-egyptian-arabic-language",
            "harvest_kind": "سطرٌ موسومٌ صراحةً بـ«عر:» في معجمِ المصدر",
            "ocr_source": "Internet Archive DjVuTXT الرسمي؛ حُفظ السطرُ كاملًا لأنَّ الأعمدةَ مختلطة",
        })
    if len(rows) != 623:
        raise SystemExit(
            f"تغيّر جردُ أسطرِ إمبر الموسومة: {len(rows)}، والمتوقَّع 623"
        )
    return rows


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    if not STORE.exists():
        print(f"لا ذخيرةَ في {STORE}")
        return 1

    rows: list[dict] = []
    ember_lines: list[dict] = []
    print(f"{'الكتاب':24}{'أزواج':>8}")
    for folder, (ar, key) in OCR_BOOKS.items():
        md = STORE / folder / "full.md"
        if not md.exists():
            continue
        got = mine_ocr(md, ar, key)
        rows.extend(got)
        print(f"  {folder:24}{len(got):>8}   (مسحٌ جديد)")
    akk = STORE / "ocr-akkadian" / "full.md"
    if akk.exists():
        got = mine_akkadian_ocr(akk)
        rows.extend(got)
        print(f"  {'ocr-akkadian':24}{len(got):>8}   (مسحٌ جديد)")
    cop = STORE / "ocr-coptic" / "full.md"
    if cop.exists():
        got = mine_coptic(cop)
        rows.extend(got)
        print(f"  {'ocr-coptic':24}{len(got):>8}   (مسحٌ جديد)")
    eg = STORE / "ocr-egyptian2" / "full.md"
    if eg.exists():
        got = mine_egyptian(eg)
        rows.extend(got)
        print(f"  {'ocr-egyptian2':24}{len(got):>8}   (مسحٌ جديد)")
    for folder, (author, default_tongue) in CLAIM_BOOKS.items():
        md = STORE / folder / "full.md"
        if not md.exists():
            continue
        got = mine_claim_ocr(md, folder, author, default_tongue)
        rows.extend(got)
        print(f"  {folder:24}{len(got):>8}   (نِسَبٌ صريحة)")
        if folder == "ocr-khashim-dialects":
            listed = mine_dawudi_list(md)
            rows.extend(listed)
            print(f"  {'dialects-dawudi-list':24}{len(listed):>8}   (قائمةٌ صريحة)")
    early = mine_early_volume_claims()
    rows.extend(early)
    print(f"  {'early-volume-claims':24}{len(early):>8}   (مواضعُ مفحوصة)")
    continuity = STORE / "ocr-khashim-continuity" / "full.md"
    if continuity.exists():
        got = mine_continuity_claims(continuity)
        rows.extend(got)
        print(f"  {'ocr-khashim-continuity':24}{len(got):>8}   (مواضعُ مفحوصة)")
    emperors = STORE / "ocr-khashim-emperors" / "full.md"
    if emperors.exists():
        got = mine_emperors_greek_glossary(emperors)
        rows.extend(got)
        print(f"  {'emperors-greek-glossary':24}{len(got):>8}   (145 مدخلًا مرقّمًا)")
    ember = STORE / "ocr-khashim-egyptian-arabic-language" / "full.md"
    if ember.exists():
        ember_lines = mine_ember_arabic_marked_lines(ember)
        print(f"  {'ember-arabic-lines':24}{len(ember_lines):>8}   (جردٌ موسومٌ خام)")
    for stem, (ar, key) in BOOKS.items():
        p = STORE / f"{stem}.pdf"
        if not p.exists():
            print(f"  {stem:24}{'غائب':>8}")
            continue
        got = mine(p, ar, key)
        rows.extend(got)
        print(f"  {stem:24}{len(got):>8}")

    rows, latin_recovery = recover_latin_heads(rows)

    OUT.write_text(json.dumps({
        "generated_by": "scripts/harvest_khashim.py",
        "layer": "استكشاف",
        "author": "علي فهمي خشيم، ومعه باحثو ندوة الوحدة والتنوّع",
        "order": "استعملْ أعمالَه، لا تحكمْ عليها، واحصدْ أقصى ما يمكنُ من الصلات",
        "note": ("أزواجٌ اقترحَها خشيم في معاجمِه المقارِنة. **مرشَّحاتٌ لا أحكام.** "
                 "والكلمةُ الأجنبيّةُ بحروفٍ عربيّةٍ كما كتبَها هو، لأنّ المسحَ الضوئيَّ "
                 "عربيٌّ فقط فسقطَ الحرفُ الأصليُّ، وهو نقصٌ مسمًّى يُسَدُّ بمسحٍ ثانٍ."),
        "pairs": len(rows),
        "latin_head_recovery": latin_recovery,
        "additional_attributed_inventories": {
            "aaron_ember_egypto_semitic": {
                "title": "المصريّةُ القديمةُ لغةٌ عروبيّة",
                "author": "آرون إمبر",
                "editor": "فريدا بنك",
                "translator_commentator": "علي فهمي خشيم",
                "items": len(ember_lines),
                "counting_rule": "كلُّ سطرٍ في النصِّ الرسميِّ المستخرج يبدأ صراحةً بالوسم «عر:»",
                "note": (
                    "هذا جردٌ خامٌ مستقلٌّ عن عدّاد الأزواج المنظَّمة؛ حُفظت الأسطرُ "
                    "كاملةً لأنَّ استخراجَ الأعمدة خلط أحيانًا الرسمَ المصريَّ بالطرف العربي."
                ),
                "rows": ember_lines,
            }
        },
        "rows": rows,
    }, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")

    by_tongue: dict[str, int] = {}
    for r in rows:
        by_tongue[r["tongue_ar"]] = by_tongue.get(r["tongue_ar"], 0) + 1
    lines = [
        "# حَصادُ مَعاجِمِ خَشيم المُقارِنة",
        "",
        "**الطَّبَقة:** استِكشاف. **مُرَشَّحاتٌ لا أحكام.**",
        "",
        "علي فهمي خشيم، وكُتُبُه: «الأكّادِيّةُ عَرَبِيّة» و«القِبطِيّةُ عَرَبِيّة»",
        "و«اللّاتينِيّةُ عَرَبِيّة» و«الوَحدةُ والتَّنَوُّعُ في اللَّهَجاتِ العَروبِيّةِ القَديمة».",
        "وزِيدَت «رِحلةُ الكَلِماتِ الثّانِيَة» و«آلِهَةُ مِصرَ العَرَبِيَّة 2»،",
        "ومَقالَاتُ تِسعَةِ باحِثينَ في كِتابِ النَّدوة؛ وكلُّ صَفٍّ مَنسوبٌ إلى صاحِبِه.",
        "وبِنيةُ كُتُبِه مُعجَمِيّةٌ، فالسَّطرُ الأوّلُ الكَلِمةُ الأجنَبِيّةُ ومَعناها،",
        "ويَليه سَطرٌ يَبدَأُ بـ`ع :` فيه الجَذرُ العَرَبِيُّ ونَصُّ مُعجَمِه.",
        "",
        "**الكَلِمةُ الأجنَبِيّةُ هنا بحُروفٍ عَرَبِيّةٍ كما كَتَبَها هو**، لأنّ المَسحَ",
        "الضَّوئِيَّ للكُتُبِ عَرَبِيٌّ فقط فسَقَطَ الحَرفُ الأصلِيّ. وهذا نَقصٌ مُسَمًّى.",
        "",
        f"**العَدَد: {len(rows)} زَوجًا.**  " + " · ".join(f"{k}: {v}" for k, v in by_tongue.items()),
        "",
        "| اللِّسان | الكَلِمةُ عندَه | مَعناها | الجَذرُ العَرَبِيّ | نَصُّه |",
        "|---|---|---|---|---|",
    ]
    for r in rows:
        lines.append(f"| {r['tongue_ar']} | `{r['foreign']}` | {r['foreign_sense'][:44]} | "
                     f"**{r['arabic_root']}** | {r['arabic_gloss'][:70]} |")
    if ember_lines:
        lines += [
            "",
            "## جَردُ آرون إِمبر المَوسومُ بـ«عَر:»",
            "",
            "في نُسخةِ «المِصرِيَّةُ القَديمةُ لُغةٌ عَروبِيَّة» الرَّسميَّةِ حُفِظَ كُلُّ",
            "سَطرٍ بَدَأَهُ المُؤَلِّفُ بِوَسمِ الطَّرَفِ العَرَبِيِّ `عر:`. النَّصُّ",
            "المُستَخرَجُ خَلَطَ بَعضَ الأَعمِدَة؛ فَلا يَفرِضُ الحاصِدُ فَصلًا آليًّا",
            "بَينَ الرَّسمِ المِصرِيِّ والطَّرَفِ العَرَبِيّ، ولا يَطرَحُ سَطرًا لِذَلِك.",
            "نِسبَةُ التَّأليفِ لآرون إِمبر، والتَّحريرِ لِفريدا بِنك، والتَّرجَمَةِ",
            "والتَّعليقِ لِعلي فَهمي خَشيم.",
            "",
            f"**العَدَد: {len(ember_lines)} سَطرًا مَوسومًا.**",
            "",
            "| سَطرُ المَصدَر | سَطرُ المُقابَلَةِ كَما استُخرِج |",
            "|---:|---|",
        ]
        for item in ember_lines:
            printed = item["printed_line"].replace("|", "\\|")
            lines.append(f"| {item['source_line']} | `{printed}` |")
    lines += ["", "---", "",
              "*English abstract.* Pairs harvested from Ali Fahmi Khashim's comparative",
              "dictionaries, whose titles state the thesis directly: Akkadian is Arabic, Coptic is",
              "Arabic, Latin is Arabic. The harvest also includes Journey of Words II, Gods of",
              "Arabic Egypt II, and nine attributed papers in the Unity and Diversity symposium.",
              "His dictionary entries are lexicographic, so each foreign headword and",
              "its sense is followed by a line marked with the Arabic letter ain giving the Arabic",
              "root and its lexical text. These are candidates, not verdicts. The foreign words",
              "appear in Arabic transcription because the available scans were OCRed for Arabic",
              "only and dropped every Latin character; that is a named gap, not a choice."]
    SHEET.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print(f"\nالمجموع: {len(rows)} زوجًا")
    print(f"كُتب: {OUT.relative_to(ROOT).as_posix()}")
    print(f"كُتب: {SHEET.relative_to(ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
