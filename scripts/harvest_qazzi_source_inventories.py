# -*- coding: utf-8 -*-
"""حصادُ مادّتَي تغريد عيدان حليوت في طبقتين مستقلتين (2026-08-15).

المصدران جنسٌ جديد، ووحدتهما واتجاههما غير وحدة المشروع واتجاه دعواه:

* بحث قوزي يجرد مدخلًا سريانيًا مع حزمة مقارنات سامية متعددة الأطراف،
  ويصنفها مشتركًا ساميًا أو ساميات أو سورث، لا أخذًا من العربية.
* بحث النبطية يبدأ بلفظ عربي نسبه معجم قديم إلى النبطية أو اختلف في أصله،
  أي إن اتجاه النسبة الغالب العربية أخذت من النبطية، وهو عكس دعوانا.

لذلك يكتب هذا السكربت سجلات مصدر، لا بطاقات حكم. لا تدخل السجلات عد الصلات،
ولا تنشئ مدارًا آليًا، ولا تورث حكمًا إلى بطاقة أخرى. ويحفظ كل سجل كامل
نص موضعه من رأسه إلى الرأس التالي؛ فلا يختزل المقارنة في أول سطر.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import pathlib
import re
import subprocess
import sys
import types
import unicodedata

ROOT = pathlib.Path(__file__).resolve().parent.parent
STORE = pathlib.Path.home() / "AI Projects" / "Resources" / "prior-art"
SEMITIC_MD = STORE / "ocr-taghreed-qazzi-semitic" / "full.md"
SEMITIC_PDF = STORE / "taghreed-eidan-semitic-words-syriac-dictionary-qazzi-2026.pdf"
NABATAEAN_MD = STORE / "ocr-taghreed-nabataean" / "full.md"
NABATAEAN_PDF = STORE / "taghreed-eidan-nabataean-words-semitic-comparison-2024.pdf"
OUT = ROOT / "data" / "qazzi-source-inventories.json"
SHEET = ROOT / "04-cross-linguistic" / "exploration" / "qazzi-source-inventories.md"

CONTROL_BASELINE = "1281ac5"
CONTROL = [
    ("baraqu", "برق", "Kamal 2008 p.78; printed research page 208"),
    ("harābu", "خرب", "Kamal 2008 p.160; printed research page 209"),
    ("kazābu", "كذب", "Kamal 2008 p.327; printed research page 209"),
    ("Ayalu", "أيل", "al-Jubouri 2010 p.36; printed research page 210"),
    ("labāšu", "لبس", "Kamal 2008 pp.344-345; printed research page 213"),
    ("qanu", "قني", "Sokoloff 1979 p.2365; printed research page 214"),
]

ENTRY = re.compile(r"^\(([^)]{1,45})\)\s*[:：]?")
ENTRY_CUES = re.compile(r"ورد|جاء|يدل|اللفظ|هو |هي |أورد|ذكر|يرى|نقل|اختلف|معنى")
AR = re.compile(r"[ء-ي]")
LATIN_FORM = re.compile(
    r"\(([A-Za-z][A-Za-zāēīōūâêîôûḫḥšṣṭḍẓʿʾḏṯġḳĀĒĪŌŪḪḤŠṢṬḌẒ]{1,18})\)"
)
LATIN_STOP = {
    "al", "saadi", "david", "taylor", "january", "no", "feb", "page",
    "p", "ph", "print", "issn", "electronic", "iraqi", "journal",
}
NOISE = (
    "العدد 20", "المجلة العراقية", "مجلة المستنصرية", "No.20", "Print ISSN",
    "Electronic ISSN", "Iraqi Journal of", "<!-- صفحة",
)

NABATAEAN_ROMANIZATION = {
    "الكلته": "al-kalta",
    "برخ": "barḫ",
    "ذهل": "dahl",
    "الكرخ": "al-karḫ",
    "شلح": "šalaḥ",
    "ازهر": "azhara",
    "الجذاذ": "al-juḏāḏ",
    "الجودي": "al-jūdī",
    "دخل": "daḫala",
    "القومس": "al-qūmis",
    "الحندقوق": "al-ḥandaqūq",
    "الخردي / الخرديه": "al-ḫurdī / al-ḫurdiyya",
    "الاشل": "al-ašall",
    "اللفت": "al-luft",
    "الشاهور": "al-šāhūr",
    "الشفان": "al-šaffān",
    "المهزرق": "al-muhazraq",
    "الكشمحه": "al-kašmaḥa",
    "الكشملح": "al-kašmalaḥ",
    "الهبور": "al-habūr",
}


def sha256(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest().upper()


def load_module(path: pathlib.Path, name: str) -> types.ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"تعذر تحميل {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def baseline_module() -> types.ModuleType:
    source = subprocess.run(
        ["git", "show", f"{CONTROL_BASELINE}:scripts/fan_any_script.py"],
        cwd=ROOT, check=True, capture_output=True, text=True, encoding="utf-8",
    ).stdout
    module = types.ModuleType("fan_any_script_qazzi_baseline")
    exec(compile(source, "fan_any_script_qazzi_baseline", "exec"), module.__dict__)
    return module


def fold_hamza(value: str) -> str:
    return value.translate(str.maketrans({"أ": "ء", "إ": "ء", "آ": "ء"}))


def run_control() -> dict:
    current = load_module(ROOT / "scripts" / "fan_any_script.py", "fan_any_script_qazzi")
    old = baseline_module()
    rows = []
    hits = 0
    for word, expected, evidence in CONTROL:
        fan = current.fan(word, "akkadian")
        target = fold_hamza(expected)
        got = next((item for item in fan if fold_hamza(item) == target), "")
        hits += bool(got)
        rows.append({
            "word": word,
            "script": "akkadian",
            "expected": expected,
            "external_evidence": evidence,
            "skeleton": current.skeleton(word, "akkadian"),
            "hit": got,
            "fan": fan,
        })
    if hits != len(CONTROL):
        raise AssertionError(f"ضابط قوزي أصاب {hits}/{len(CONTROL)}؛ يمنع إنشاء السجلات")

    regression = []
    for word in ("trūdō", "cornū", "tinniō", "separo", "abutor", "tergeo"):
        before = set(old.fan(word, "latin"))
        after = set(current.fan(word, "latin"))
        lost = sorted(before - after)
        if lost:
            raise AssertionError(f"فقدت المروحة مرشحات قديمة في {word}: {lost}")
        regression.append({
            "word": word,
            "baseline": CONTROL_BASELINE,
            "old_count": len(before),
            "new_count": len(after),
            "old_minus_new": lost,
            "new_minus_old": sorted(after - before),
        })
    return {"hits": hits, "size": len(CONTROL), "rows": rows, "regression": regression}


def bare_head(value: str) -> str:
    value = unicodedata.normalize("NFC", value)
    value = re.sub(r"[\u064b-\u065fـ]", "", value)
    value = value.translate(str.maketrans({"أ": "ا", "إ": "ا", "آ": "ا", "ة": "ه"}))
    return re.sub(r"\s+", " ", value).strip()


def is_noise(line: str) -> bool:
    stripped = line.strip()
    return (
        not stripped
        or stripped.isdigit()
        or stripped.startswith(NOISE)
        or stripped.startswith("# ")
        or stripped.startswith("## ")
        or stripped.startswith("### ")
        or stripped.startswith("#### ")
    )


def entry_start(line: str, *, semitic: bool) -> re.Match[str] | None:
    cleaned = line.replace("**", "").strip()
    match = ENTRY.match(cleaned)
    if not match or not AR.search(match.group(1)):
        return None
    if semitic and bare_head(match.group(1)) == "الساميات/ السورث":
        return None
    if not ENTRY_CUES.search(cleaned[match.end():match.end() + 180]):
        return None
    return match


def page_map(lines: list[str]) -> list[int]:
    page = 0
    out = []
    for line in lines:
        marker = re.match(r"<!-- صفحة (\d+) -->", line.strip())
        if marker:
            page = int(marker.group(1))
        out.append(page)
    return out


def extract(md: pathlib.Path, *, layer: str, semitic: bool) -> list[dict]:
    lines = md.read_text(encoding="utf-8").splitlines()
    pages = page_map(lines)
    starts: list[tuple[int, re.Match[str]]] = []
    for index, line in enumerate(lines):
        if line.strip() == "# الخاتمة:":
            break
        match = entry_start(line, semitic=semitic)
        if match:
            starts.append((index, match))

    records = []
    for ordinal, (start, match) in enumerate(starts, 1):
        end = starts[ordinal][0] if ordinal < len(starts) else next(
            (i for i in range(start + 1, len(lines)) if lines[i].strip() == "# الخاتمة:"),
            len(lines),
        )
        body_lines = [line.strip() for line in lines[start:end] if not is_noise(line)]
        text = "\n\n".join(body_lines)
        head = match.group(1).strip()
        forms = []
        for form in LATIN_FORM.findall(text):
            if form.casefold() in LATIN_STOP or form in forms:
                continue
            forms.append(form)
        used_pages = sorted({pages[i] for i in range(start, end) if pages[i]})

        if semitic:
            romanization = (
                "؛ ".join(forms)
                if forms
                else "لم تسلم رومنة لاتينية للرأس السرياني في OCR؛ الرسم المطبوع محفوظ في PDF"
            )
            direction = "مقارنة أو موروث سامي مشترك؛ لا اتجاه أخذ من العربية"
            unit = "مدخل سرياني مع حزمة مقارنات سامية متعددة الأطراف"
        else:
            key = bare_head(head)
            romanization = NABATAEAN_ROMANIZATION.get(key, "")
            if not romanization:
                raise AssertionError(f"لا رومنة لسجل النبطية: {head!r}، المفتاح {key!r}")
            direction = "العربية أخذت من النبطية أو لسان آخر، أو نسبة مختلف فيها؛ عكس دعوانا"
            unit = "خبر نسبة معجمي قديم حول لفظ عربي، مع مقارناته السامية"

        records.append({
            "record_id": f"{layer}-{ordinal:03d}",
            "layer": layer,
            "record_type": "SOURCE-INVENTORY",
            "project_verdict": "لا حكم؛ سجل مصدر مستقل",
            "excluded_from_link_count": True,
            "source_head_ocr": head,
            "romanization": romanization,
            "comparative_latin_forms": forms,
            "source_pages": used_pages,
            "source_line_span": f"{start + 1}-{end}",
            "source_unit": unit,
            "source_direction": direction,
            "source_text": text,
        })
    return records


def source_payload(layer: str, title: str, pdf: pathlib.Path, md: pathlib.Path,
                   job_id: str, records: list[dict], unit: str, direction: str) -> dict:
    return {
        "layer": layer,
        "title": title,
        "author": "تغريد عيدان حليوت",
        "source_pdf": str(pdf),
        "source_pdf_sha256": sha256(pdf),
        "ocr_text": str(md),
        "batch_job_id": job_id,
        "unit_of_measure": unit,
        "direction_of_claim": direction,
        "excluded_from_link_count": True,
        "records": len(records),
        "items": records,
    }


def write_sheet(payload: dict) -> None:
    lines = [
        "# جرد مادتي قوزي والنبطية عند تغريد عيدان حليوت",
        "",
        "**الطبقة:** سجلات مصدر مستقلة. **لا تدخل عد الصلات ولا تحمل حكمًا على دعوى المشروع.**",
        "",
        "وحدة المصدرين واتجاههما غير وحدتنا واتجاه دعوانا؛ لذلك حفظ النص كاملًا",
        "مع النسبة والرومنة المتاحة، ولم تقلب جهة السهم ولم تولد مدارات.",
    ]
    for source in payload["sources"]:
        lines += [
            "",
            f"## {source['title']}",
            "",
            f"- وحدة القياس: {source['unit_of_measure']}.",
            f"- اتجاه الأخذ: {source['direction_of_claim']}.",
            f"- العدد: {source['records']} سجلًا؛ كلها خارج عد الصلات.",
        ]
        for item in source["items"]:
            pages = ", ".join(str(page) for page in item["source_pages"])
            forms = "، ".join(f"`{form}`" for form in item["comparative_latin_forms"])
            lines += [
                "",
                f"### {item['record_id']}: {item['source_head_ocr']}",
                "",
                f"- الرومنة: `{item['romanization']}`.",
                f"- الصفحات في PDF: {pages or 'غير مثبتة'}؛ مدى أسطر OCR: {item['source_line_span']}.",
                f"- الصور اللاتينية المقارنة: {forms or 'لا صورة لاتينية سليمة في النص المستخرج'}.",
                f"- الاتجاه: {item['source_direction']}.",
                "- الحكم: لا حكم؛ سجل مصدر مستقل مستبعد من عد الصلات.",
                "",
                item["source_text"],
            ]
    SHEET.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    for path in (SEMITIC_MD, SEMITIC_PDF, NABATAEAN_MD, NABATAEAN_PDF):
        if not path.exists():
            raise SystemExit(f"لا ملف: {path}")

    control = run_control()
    semitic = extract(SEMITIC_MD, layer="qazzi-semitic-source-inventory", semitic=True)
    nabataean = extract(NABATAEAN_MD, layer="qazzi-nabataean-source-inventory", semitic=False)
    if len(semitic) != 30 or len(nabataean) != 20:
        raise AssertionError(
            f"تغير مقام الجرد: السامي={len(semitic)} بدل 30؛ النبطي={len(nabataean)} بدل 20"
        )

    sources = [
        source_payload(
            "qazzi-semitic-source-inventory",
            "ألفاظ سامية في المعجم السرياني المشكول تمامًا والمقارن ساميًا للدكتور يوسف فوزي قوزي",
            SEMITIC_PDF, SEMITIC_MD, "a630024f-936a-4998-b72b-ebfe050927dc", semitic,
            "مدخل سرياني مع حزمة مقارنات سامية متعددة الأطراف",
            "مقارنة أو موروث سامي مشترك؛ لا اتجاه أخذ من العربية",
        ),
        source_payload(
            "qazzi-nabataean-source-inventory",
            "الألفاظ النبطية في المعجمات العربية: دراسة مقارنة في ضوء اللغات السامية",
            NABATAEAN_PDF, NABATAEAN_MD, "9904aec0-aafe-40cc-8c1d-07d5fa790458", nabataean,
            "خبر نسبة معجمي قديم حول لفظ عربي، مع مقارناته السامية",
            "العربية أخذت من النبطية أو لسان آخر، أو نسبة مختلف فيها؛ عكس دعوانا",
        ),
    ]
    payload = {
        "generated_by": "scripts/harvest_qazzi_source_inventories.py",
        "generated_on": "2026-08-15",
        "layer_policy": "طبقتان مستقلتان مستبعدتان من عد الصلات؛ لا أحكام ولا مدارات مولدة",
        "control": control,
        "sources": sources,
        "totals": {"sources": 2, "records": len(semitic) + len(nabataean),
                   "semitic": len(semitic), "nabataean": len(nabataean)},
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=1),
                   encoding="utf-8", newline="\n")
    write_sheet(payload)
    print(f"ضابط قوزي: {control['hits']}/{control['size']}")
    print(f"السامي: {len(semitic)}؛ النبطي: {len(nabataean)}؛ المجموع: {len(semitic) + len(nabataean)}")
    print(f"كتب: {OUT.relative_to(ROOT).as_posix()}")
    print(f"كتب: {SHEET.relative_to(ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
