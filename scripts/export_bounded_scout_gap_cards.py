#!/usr/bin/env python3
"""Export non-verdict RECOVERY-v2 cards for a bounded Semitic scout."""
from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
import unicodedata
from collections import Counter
from pathlib import Path

from recovery_pipeline.inventory import DEFAULT_DB, connect
from search_arabic_root_senses import DEFAULT_RESOURCES, deduplicate, parquet_matches


ROOT = Path(__file__).resolve().parents[1]
PROFILES = {
    "phoenician": ROOT / "04-cross-linguistic" / "normalization-profiles" / "phoenician.json",
    "punic": ROOT / "04-cross-linguistic" / "normalization-profiles" / "punic.json",
}
LANGUAGE_AR = {"phoenician": "الفينيقية", "punic": "البونيقية"}


def clean(value: object, limit: int | None = None) -> str:
    text = unicodedata.normalize("NFC", str(value or ""))
    text = " ".join(text.replace("\u2013", "-").replace("\u2014", "-").split())
    if limit and len(text) > limit:
        return text[: limit - 1].rstrip() + "…"
    return text


def strength_order(connection: sqlite3.Connection, language: str) -> list[str]:
    return [
        row[0]
        for row in connection.execute(
            """
            WITH target AS (
              SELECT family_id FROM families WHERE language=?
            ), candidate_strength AS (
              SELECT fm.family_id,
                MAX(CASE WHEN c.kind='root' AND c.status='licensed' AND c.route_flag=0
                    THEN 1 ELSE 0 END) AS licensed_full_root,
                MIN(CASE WHEN c.kind='root' AND c.status='licensed' AND c.route_flag=0
                    THEN json_array_length(c.rule_ids_json) END) AS root_rule_count,
                MIN(CASE WHEN c.status='licensed' AND c.route_flag=0
                    THEN json_array_length(c.rule_ids_json) END) AS any_rule_count
              FROM target t JOIN family_members fm ON fm.family_id=t.family_id
              JOIN candidates c ON c.entry_id=fm.entry_id GROUP BY fm.family_id
            ), meaning_strength AS (
              SELECT fm.family_id,
                COUNT(DISTINCT CASE WHEN fm.role NOT IN ('form','nonlexical')
                    AND TRIM(e.gloss)<>'' THEN e.gloss END) AS gloss_count,
                COALESCE(SUM(CASE WHEN fm.role NOT IN ('form','nonlexical')
                    THEN LENGTH(TRIM(e.gloss)) ELSE 0 END),0) AS text_chars
              FROM target t JOIN family_members fm ON fm.family_id=t.family_id
              JOIN entries e ON e.entry_id=fm.entry_id GROUP BY fm.family_id
            )
            SELECT f.family_id FROM families f
            LEFT JOIN candidate_strength cs ON cs.family_id=f.family_id
            LEFT JOIN meaning_strength ms ON ms.family_id=f.family_id
            WHERE f.language=?
            ORDER BY COALESCE(cs.licensed_full_root,0) DESC,
              CASE WHEN COALESCE(cs.root_rule_count,cs.any_rule_count) IS NULL
                THEN 999 ELSE COALESCE(cs.root_rule_count,cs.any_rule_count) END,
              COALESCE(ms.gloss_count,0) DESC, COALESCE(ms.text_chars,0) DESC,
              f.family_id
            """,
            (language, language),
        )
    ]


def raw_rows(path: Path) -> dict[int, dict]:
    return {
        index: json.loads(line)
        for index, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1)
    }


def entry_line(entry_id: str) -> int | None:
    match = re.search(r":(\d+):", entry_id)
    return int(match.group(1)) if match else None


def first_reference(raw: dict) -> str:
    for sense in raw.get("senses", []):
        for example in sense.get("examples", []):
            if example.get("ref"):
                return clean(example["ref"], 420)
    return ""


def arabic_fan(forms: list[str], cache: dict[str, list[dict]]) -> str:
    if not forms:
        return "لم يخرج المسح الآلي جذرًا كاملًا أو أجوف مرخصًا بلا صف؛ حفظت النوى في خانة المقابل من غير حكم دلالي."
    parts = []
    for form in forms[:2]:
        if form not in cache:
            cache[form] = deduplicate(parquet_matches(DEFAULT_RESOURCES, form, 260))
        matches = cache[form]
        if not matches:
            parts.append(f"{form}: لا شاهد مستقل في فهرس المعاجم العربية المحلي.")
            continue
        shown = matches[:2]
        parts.append(
            f"{form}: "
            + "؛ ".join(
                f"{clean(item['source'])}: «{clean(item['definition'], 220)}»"
                for item in shown
            )
        )
    return " | ".join(parts)


def candidate_summary(rows: list[sqlite3.Row]) -> tuple[list[str], str, str]:
    preferred = [
        row for row in rows
        if row["status"] == "licensed"
        and not row["route_flag"]
        and row["kind"] in {"root", "hollow-root"}
    ]
    preferred.sort(
        key=lambda row: (
            0 if row["kind"] == "root" else 1,
            len(json.loads(row["rule_ids_json"])),
            row["form"],
        )
    )
    forms = []
    for row in preferred:
        if row["form"] not in forms:
            forms.append(row["form"])
    display_rows = preferred[:4]
    if not display_rows:
        display_rows = [
            row for row in rows
            if row["status"] == "licensed" and not row["route_flag"]
        ][:4]
    display = "؛ ".join(
        f"{row['kind']} {row['form']} «{clean(row['reading']) or 'بلا قراءة نصية'}»"
        + (
            " بلا صف"
            if not json.loads(row["rule_ids_json"])
            else " عبر " + ",".join(json.loads(row["rule_ids_json"]))
        )
        for row in display_rows
    ) or "لا مرشح مرخص."
    routes = sorted(
        {
            rule
            for row in rows
            for rule in json.loads(row["rule_ids_json"])
            if row["status"] == "licensed" and not row["route_flag"]
        }
    )
    return forms, display, ", ".join(routes) or "تطابقات ذاتية فقط في المخرجات المعروضة"


def family_payload(connection: sqlite3.Connection, family_id: str) -> tuple[sqlite3.Row, list[sqlite3.Row], list[sqlite3.Row]]:
    family = connection.execute(
        "SELECT * FROM families WHERE family_id=?", (family_id,)
    ).fetchone()
    members = connection.execute(
        "SELECT e.*, fm.role, fm.link_types_json FROM family_members fm "
        "JOIN entries e ON e.entry_id=fm.entry_id WHERE fm.family_id=? ORDER BY e.entry_id",
        (family_id,),
    ).fetchall()
    candidates = connection.execute(
        "SELECT c.kind,c.form,a.reading,c.status,c.rule_ids_json,c.route_flag "
        "FROM family_members fm JOIN candidates c ON c.entry_id=fm.entry_id "
        "LEFT JOIN arabic_forms a ON a.form=c.form AND a.kind=c.kind "
        "WHERE fm.family_id=? ORDER BY CASE c.status WHEN 'licensed' THEN 0 "
        "WHEN 'manual-condition' THEN 1 ELSE 2 END,c.kind,c.form",
        (family_id,),
    ).fetchall()
    return family, members, candidates


def is_isolated(members: list[sqlite3.Row]) -> bool:
    strata = {member["source_stratum"] for member in members}
    return bool(
        any(member["role"] == "nonlexical" for member in members)
        or strata <= {"proper-name"}
        or "reconstruction" in strata
    )


def blocker(family: sqlite3.Row, members: list[sqlite3.Row], raws: list[dict], forms: list[str]) -> tuple[str, str]:
    etymology = " ".join(clean(raw.get("etymology_text")) for raw in raws).lower()
    construction = family["construction"]
    if construction in {"mixed", "structural", "ambiguous-form", "orphan-form"} and family["member_count"] > 1:
        return (
            "MORPHOLOGY-GAP",
            "فصل أعضاء الأسرة صرفيًا ودلاليًا بمصدر منشور فردي قبل توريث أي حكم",
        )
    if any(marker in etymology for marker in ("borrowing", "borrowed from", "from akkadian", "from iranian")):
        return (
            "SOURCE-GAP",
            "تحقق منشور مستقل من اتجاه القرض وطبقته؛ يبقى المسار معزولًا والحكم غير صادر",
        )
    if not forms:
        return (
            "TOOL-GAP",
            "مرشح جذر كامل أو أجوف مرخص، أو قرار مؤلفي معلل بعد فحص النوى والمصدر الفردي",
        )
    return (
        "SOURCE-GAP",
        "إسناد معجمي أو نقشي منشور فردي فوق لقطة الاستطلاع قبل أي حكم نسب",
    )


def render(language: str, connection: sqlite3.Connection, source_path: Path) -> str:
    raws_by_line = raw_rows(source_path)
    order = strength_order(connection, language)
    families = [family_payload(connection, family_id) for family_id in order]
    isolated = [item for item in families if is_isolated(item[1])]
    lexical = [item for item in families if not is_isolated(item[1])]
    fan_cache: dict[str, list[dict]] = {}
    lines = [
        f"# قراءة الاستطلاع {LANGUAGE_AR[language]}: سجل فجوات بلا حكم",
        "",
        "تخضع هذه القراءة حرفيًا لـ[ميثاق الاستكشاف](../exploration-charter.md)، ولا يصدر منها حكم نسب ما دام عائق المصدر أو الأداة أو القانون قائمًا.",
        "",
        "- إصدارُ البروتوكول: `RECOVERY-v2`.",
        "- مسحُ المعاني العربيّة: إلزامي لكل بطاقة معجمية.",
        "- فصلُ المتجانسات والاقتراض: إلزامي لكل بطاقة معجمية.",
        "- جسورُ الاسترداد المفحوصة: الكامل والأجوف والنواة والمروحة والتثليث حيث ينطبق.",
        "- حالةُ الإغلاق: عائق منظم أو إغلاق صريح.",
        "",
        "<!-- RECOVERY-PROTOCOL-v2 -->",
        "",
        "> **حالة السجل:** يغطي لقطة Kaikki المحدودة المثبتة، لا معجم اللغة التاريخي كاملًا. كل بطاقة هنا `الحكم: غير صادر`، ولا تشغّل خط البرهان ولا توقع صفًا ولا تعدل أداة مجمدة.",
        "",
        "## بيان النطاق: الخطوة 14",
        "",
        f"- **الفرع واللقطة:** {LANGUAGE_AR[language]} من `{source_path.relative_to(ROOT).as_posix()}` وفق ورقة التثبيت.",
        "- **وحدة السحب:** الأسرة بكل أعضائها، بترتيب القوة الاسترجاعي: الجذر الكامل المرخص أولًا، ثم قلة الصفوف، ثم غنى نص المعنى.",
        f"- **الحد:** جميع أسر اللقطة: {len(order)} أسرة. عزل سجل النطاق {len(isolated)} أسرة غير داخلة في المعجم العام، وبقيت {len(lexical)} أسرة معجمية ببطاقات كاملة أدناه.",
        "- **قيد الشمول:** الإتمام هنا إتمام هذه اللقطة المحدودة فقط. تبقى `SOURCE-GAP` نافذة على ادعاء إتمام معجم اللغة.",
        "- **قاعدة الحكم:** لا تصدر هذه الطبقة حكم نسب. المرشح القوي يسمى ويظل موقوفًا على المصدر الفردي أو العائق المحدد.",
        "",
        "## محاضر العزل البنيوي",
        "",
        "| الأسرة | الرأس | الطبقة | المحضر | الحكم |",
        "|---|---|---|---|---|",
    ]
    for family, members, _ in isolated:
        strata = ", ".join(sorted({member["source_stratum"] for member in members}))
        if any(member["role"] == "nonlexical" for member in members):
            disposition = "عنصر غير معجمي"
        elif "reconstruction" in strata:
            disposition = "تعمير معزول حتى يثبت شاهده"
        else:
            disposition = "علم معزول من المعجم العام"
        lines.append(
            f"| `{family['family_id']}` | {clean(family['anchor_headword'])} | `{strata}` | {disposition} | غير صادر |"
        )
    lines += ["", "## البطاقات المعجمية بترتيب القوة", ""]
    for family, members, candidates in lexical:
        raw_items = [
            raws_by_line.get(entry_line(member["entry_id"]) or -1, {})
            for member in members
        ]
        forms, candidate_text, rules = candidate_summary(candidates)
        gap, required = blocker(family, members, raw_items, forms)
        member_text = "؛ ".join(
            f"{clean(member['headword'])} `{clean(member['romanization'])}` «{clean(member['gloss'])}»"
            for member in members
        )
        refs = [first_reference(raw) for raw in raw_items]
        refs = [ref for ref in refs if ref]
        etymologies = [
            clean(raw.get("etymology_text"), 360)
            for raw in raw_items if raw.get("etymology_text")
        ]
        source_lines = [
            str(entry_line(member["entry_id"])) for member in members
            if entry_line(member["entry_id"]) is not None
        ]
        roles = Counter(member["role"] for member in members)
        strata = sorted({member["source_stratum"] for member in members})
        loan_hint = any(member["loan_hint"] for member in members)
        lines += [
            f"### بطاقة: `{family['family_id']}`، {clean(family['anchor_headword'])}",
            f"- عائق: النوع={gap}؛ يتطلب={required}",
            "- إصدارُ البروتوكول: RECOVERY-v2 (2026-07-14)",
            f"- الكلمةُ في الفرع: {member_text}. قيد كل عضو: «{clean(members[0]['source_scope_note'])}»",
            "- أقدمُ صورةٍ مستعادة: لم تستعد البطاقة صورة من عندها؛ تحفظ الرسم المثبت"
            + (f"، وشاهده المسمى: {refs[0]}" if refs else "، ولا يحمل السطر شاهدًا فرديًا مسمى")
            + f" [Kaikki bounded scout، السطر أو الأسطر {', '.join(source_lines)}]",
            f"- الخطوةُ صفر (التعرية بصرف الفرع): لا تعرية آلية؛ بناء الأسرة `{family['construction']}` وأدوارها {dict(roles)} تحفظ كما في المصدر، ولا تختزل الصورة إلا برابط مسمى",
            "- درجةُ المقارنة: الجذر الكامل أولًا، ثم الجذر الأجوف حيث أخرجه الفهرس، ثم النواة",
            f"- مسحُ المعاني العربيّة: {arabic_fan(forms, fan_cache)}",
            f"- المقابلُ من اللسان: {candidate_text}",
            f"- مسارُ الصوت: الصفوف المرخصة الظاهرة في مخرجات الأسرة: {rules}. لا يحول وجودها إلى حكم، ولا تطبق الصفوف ذات شرط المسار آليًا",
            f"- المعنى من قاموس الفرع: {'؛ '.join('«'+clean(member['gloss'])+'»' for member in members)}",
            "- المدار: تحفظ المطابقة المباشرة أو الاحتمال الدلالي للعرض فقط؛ لا يسمى انتقال مداري حكمًا قبل المصدر الفردي والمراجعة",
            "- المصفاة: "
            + ("وسم الجرد احتمال قرض؛ " if loan_hint else "")
            + (
                "نص الاشتقاق في اللقطة: " + " | ".join(etymologies)
                if etymologies else "لا يحمل السطر نص اشتقاق، وغيابه لا يثبت الأصالة"
            ),
            f"- فصلُ المتجانسات والاقتراض: تضم الأسرة {len(members)} عضوًا؛ تحفظ المعاني والأدوار منفصلة، ولا يرث عضو حكم عضو آخر بلا فحص. طبقة المصدر: {', '.join(strata)}",
            "- مؤشر اليتم: "
            + (
                "الأسرة تحمل رابط صورة أو بديل ظاهرًا، ويظل حق نقض كل عضو قائمًا"
                if family["form_count"] else "لا صورة صرفية يتيمة ظاهرة في الأسرة"
            ),
            f"- جسورُ الاسترداد المفحوصة: كامل وأجوف ونواة عبر {len(candidates)} مسارًا مولدًا؛ مروحة المعاجم العربية للمرشحين الأقوى؛ نص الاشتقاق؛ شاهد المصدر؛ القرض؛ المتجانسات؛ أعضاء الأسرة",
            f"- حالةُ الإغلاق: {gap}",
            "- الحكم (استكشاف): غير صادر.",
            f"- ملاحظات: عدسة الاسترداد سمت أقوى المخرجات ولم تسقط المرشح عند نقص المصدر. عدسة التشكيك راجعت طبقة المصدر والاشتقاق وأعضاء الأسرة، ومنعت إصدار حكم من لقطة استطلاع محدودة. العائق المحدد أعلاه هو وحده طريق إعادة الفتح.",
            "",
        ]
    lines += [
        "## ختام الموجة",
        "",
        f"اكتمل المرور البنيوي والبطاقي على كل أسر لقطة {LANGUAGE_AR[language]} المحدودة. لم يصدر حكم نسب في هذا السجل، ولم يشغل خط البرهان. محاضر العزل والفجوات قابلة للإيداع بعد البوابات، ويبقى قيد عدم تمثيل المعجم التاريخي كاملًا نافذًا.",
        "",
    ]
    return unicodedata.normalize("NFC", "\n".join(lines))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--language", choices=sorted(PROFILES), required=True)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    profile = json.loads(PROFILES[args.language].read_text(encoding="utf-8"))
    source_path = ROOT / profile["source"]["path"]
    connection = connect(args.db, create=False)
    connection.row_factory = sqlite3.Row
    try:
        rendered = render(args.language, connection, source_path)
    finally:
        connection.close()
    if args.check:
        if not args.output.exists() or args.output.read_text(encoding="utf-8") != rendered:
            print(f"FAIL: stale bounded scout gap cards: {args.output}")
            return 1
        print(f"bounded scout gap cards: CLEAN ({args.language})")
        return 0
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(rendered, encoding="utf-8")
    print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
