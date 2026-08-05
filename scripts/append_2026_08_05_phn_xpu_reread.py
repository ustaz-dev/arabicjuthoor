# -*- coding: utf-8 -*-
"""يسجل إعادة القراءة الكاملة للقطتي phn وxpu في ملفيهما."""
from __future__ import annotations

import collections
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
READINGS = ROOT / "04-cross-linguistic" / "readings"
DATA = ROOT / "data" / "phn-xpu-full-reread.json"
MARKER = "<!-- PHN-XPU-FULL-REREAD-2026-08-05 -->"

CONFIG = {
    "phn": {
        "expected": 170,
        "source": ROOT / "Resources" / "phn" / "kaikki.org-phn-bounded-scout.jsonl",
        "reading": READINGS / "phoenician-punic-scout.md",
        "member_prefix": "kaikki_phoenician_bounded_2026_07_16",
    },
    "xpu": {
        "expected": 106,
        "source": ROOT / "Resources" / "xpu" / "kaikki.org-xpu-bounded-scout.jsonl",
        "reading": READINGS / "punic.md",
        "member_prefix": "kaikki_punic_bounded_2026_07_16",
    },
}


def rows(path: Path) -> tuple[bytes, list[dict]]:
    raw = path.read_bytes()
    parsed = [json.loads(line) for line in raw.decode("utf-8").splitlines()]
    return raw, parsed


def first_gloss(row: dict) -> str:
    for sense in row.get("senses", []) or []:
        values = sense.get("glosses") or sense.get("raw_glosses") or []
        if values:
            return str(values[0])
    return ""


def has_attestation(row: dict) -> bool:
    if row.get("attestations"):
        return True
    return any(
        sense.get("examples") or sense.get("quotations")
        for sense in row.get("senses", []) or []
    )


def homographs(parsed: list[dict]) -> list[dict]:
    grouped: dict[str, list[dict]] = collections.defaultdict(list)
    for line, row in enumerate(parsed, start=1):
        grouped[str(row.get("word") or "")].append({
            "line": line,
            "pos": str(row.get("pos") or ""),
            "gloss": first_gloss(row),
        })
    return [
        {"word": word, "members": members}
        for word, members in grouped.items() if len(members) > 1
    ]


def inspect(code: str, cfg: dict) -> dict:
    raw, parsed = rows(cfg["source"])
    if len(parsed) != cfg["expected"]:
        raise ValueError(f"{code}: {len(parsed)} != {cfg['expected']}")
    reading = cfg["reading"].read_text(encoding="utf-8")
    records: list[dict] = []
    missing: list[int] = []
    for line, row in enumerate(parsed, start=1):
        member_pattern = re.compile(re.escape(cfg["member_prefix"]) + rf":{line}:")
        if member_pattern.search(reading):
            represented_by = "member-card"
        elif str(row.get("word") or "") in reading:
            represented_by = "structural-isolation"
        else:
            represented_by = "missing"
            missing.append(line)
        records.append({
            "line": line,
            "word": str(row.get("word") or ""),
            "pos": str(row.get("pos") or ""),
            "gloss": first_gloss(row),
            "etymology": str(row.get("etymology_text") or ""),
            "attestation": has_attestation(row),
            "represented_by": represented_by,
        })
    if missing:
        raise ValueError(f"{code}: صفوف غير ممثلة {missing}")
    pos = collections.Counter(record["pos"] for record in records)
    return {
        "code": code,
        "source": cfg["source"].relative_to(ROOT).as_posix(),
        "reading": cfg["reading"].relative_to(ROOT).as_posix(),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "rows": len(records),
        "etymologies": sum(bool(record["etymology"]) for record in records),
        "without_etymology": sum(not record["etymology"] for record in records),
        "with_attestation": sum(record["attestation"] for record in records),
        "pos": dict(pos),
        "homographs": homographs(parsed),
        "from_phoenician": sum(
            bool(re.search(r"(?i)\bfrom (?:western )?phoenician\b", record["etymology"]))
            for record in records
        ),
        "records": records,
    }


def phn_append(info: dict) -> str:
    return f"""

{MARKER}

## إعادة قراءة `Resources/phn` كاملة، 2026-08-05

### محضر الصفوف والنتيجة

- قُرئت الأسطر 1 إلى {info['rows']} بلا عيّنة ولا قفز. بصمة SHA-256 هي `{info['sha256']}`.
- تمثيل الصفوف: 130 صفًا ببطاقة عضو صريحة، و40 صفًا في محاضر العزل البنيوي، وهي 22 حرفًا و18 علمًا. لا صف مفقود.
- البنية: 84 اسمًا، و22 حرفًا، و18 علمًا، و17 عددًا، و15 ضميرًا، و7 أفعال، و3 حروف جر، وصفتان، وأداة واحدة، وظرف واحد.
- يحمل {info['etymologies']} صفًا نص تأثيل، ويفتقده {info['without_etymology']} صفًا. ولا يحمل شاهدًا نصيًا أو نقشيًا فرديًا داخل بنية Kaikki إلا {info['with_attestation']} صفًا، ولذلك يبقى `SOURCE-GAP` نافذًا في سائر الصفوف.
- مجموعات التجانس التي لا يجوز توريث حكم بعضها إلى بعض: `𐤀𐤔` اسم «رجل» وضمير «من»، و`𐤀𐤕` للمذكر والمؤنث، و`𐤄𐤀` للمذكر والمؤنث، و`𐤄𐤌𐤕` للمذكر والمؤنث. اتفاق الرسم ليس وحدة عضو.
- مسارات الاتصال الصريحة أو المشبوهة بقيت معزولة: `𐤀𐤎` من المصرية، و`𐤀𐤋𐤔𐤉` من لغة محلية، و`𐤁𐤓𐤆𐤋` كلمة جوالة، و`𐤊𐤌𐤍` و`𐤔𐤔𐤌𐤍` في مسار أكادي. لا يتحول واحد منها إلى إرث.
- أقوى الشواهد المباشرة ذات الإسناد الفردي، `𐤒𐤁𐤓 ↔ قبر` و`𐤕𐤇𐤕 ↔ تحت`، موجودان أصلًا في هذا الملف بأحكامهما المحلية. لم تُعَدّ هذه القراءة حكمًا ثانيًا لهما، ولم يصدر حكم جديد من مجرد اكتمال الجرد.
- السجل الصفّي الكامل، وفيه الرسم والنوع والمعنى والتأثيل ووجه التمثيل لكل سطر، محفوظ في `data/phn-xpu-full-reread.json`.
"""


def xpu_append(info: dict) -> str:
    return f"""

{MARKER}

## إعادة قراءة `Resources/xpu` كاملة، 2026-08-05

### محضر الصفوف والنتيجة

- قُرئت الأسطر 1 إلى {info['rows']} بلا عيّنة ولا قفز. بصمة SHA-256 هي `{info['sha256']}`.
- انتظمت الأسطر في 100 أسرة: 94 صفًا ببطاقات عضو صريحة، و12 صفًا في محاضر العزل البنيوي، مع اشتراك 6 صفوف في أسر متجانسة أو بدائل. لا صف مفقود.
- البنية: 72 اسمًا، و12 عددًا، و9 أعلام، و8 ضمائر، و3 أفعال، وأداة تعريف واحدة، وحرف جر واحد.
- يحمل {info['etymologies']} صفًا نص تأثيل، ويفتقده {info['without_etymology']} صفًا، ويحمل {info['with_attestation']} صفًا فقط شاهدًا نصيًا أو نقشيًا فرديًا في بنية المصدر.
- يصرح {info['from_phoenician']} تأثيلًا بأن اللفظ من الفينيقية. هذه انتقالات داخل السلسلة الكنعانية، فلا تُعد 57 شاهدًا بونيًا مستقلًا فوق الشاهد الفينيقي في دعوى العمق.
- مجموعات التجانس الأربع مفصولة: `𐤔𐤋𐤌` «سلام» و«لهم»، و`𐤀𐤔` «رجل» و«من أو أين»، و`𐤀𐤕` أداة المفعول وضمير المخاطب، و`𐤔𐤓` «ثور» و«جذر». لا يرث عضو حكم جاره.
- طبقة النبات المغرية لا ترفع نفسها إلى شاهد مباشر: `𐤓𐤌𐤍 ↔ رمان` و`𐤕𐤐𐤇 ↔ تفاح` و`𐤀𐤂𐤆` تعميرات في سجل المصدر، و`𐤒𐤔𐤀 ↔ قثاء` باق على فجوة القانون، و`𐤂𐤆𐤓` قرض إيراني، و`𐤒𐤍𐤀` و`𐤊𐤌𐤍` في مسار أكادي.
- الأحكام المحلية القائمة في هذا الملف هي `𐤏𐤁𐤃 ↔ عبد` و`𐤋𐤁𐤍 ↔ لبن` و`𐤕𐤉𐤍 ↔ تين`. لم تُضاعفها إعادة القراءة، ولم يصدر حكم رابع من الجرد وحده.
- السجل الصفّي الكامل، وفيه الرسم والنوع والمعنى والتأثيل ووجه التمثيل لكل سطر، محفوظ في `data/phn-xpu-full-reread.json`.
"""


def main() -> int:
    infos = {code: inspect(code, cfg) for code, cfg in CONFIG.items()}
    payload = {
        "schema_version": "1.0",
        "date": "2026-08-05",
        "rule": "Every raw row was read; structural isolation is recorded, and no existing verdict is counted twice.",
        "sources": infos,
    }
    DATA.write_text(json.dumps(payload, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    appends = {
        "phn": phn_append(infos["phn"]),
        "xpu": xpu_append(infos["xpu"]),
    }
    for code, cfg in CONFIG.items():
        text = cfg["reading"].read_text(encoding="utf-8")
        if MARKER not in text:
            cfg["reading"].write_text(text.rstrip() + appends[code] + "\n", encoding="utf-8", newline="\n")
    print(
        f"phn={infos['phn']['rows']} rows; xpu={infos['xpu']['rows']} rows; "
        f"recorded={sum(info['rows'] for info in infos.values())}"
    )
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
