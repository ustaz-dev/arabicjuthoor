#!/usr/bin/env python3
"""Validate and append the three local Aramaic completion-reading shards.

The shard writers own separate scratch files.  This merger is mechanical: it
requires every currently unread lexical member exactly once in its assigned
range, rejects unknown family/member identifiers, and appends the reports to
the Aramaic reading ledger atomically.  It does not alter a judgment, refresh
the shared recovery ledger, or run the proof line.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
import re
import sqlite3
import unicodedata
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "cache" / "recovery_pipeline" / "aramaic-completion-audit.json"
DIRECT_SURFACE = (
    ROOT / "cache" / "recovery_pipeline" / "aramaic-direct-surface-fans.json"
)
DB = ROOT / "cache" / "recovery_pipeline" / "inventory-v5.sqlite"
READING = ROOT / "04-cross-linguistic" / "readings" / "aramaic.md"
SHARDS = (
    (0, 525, ROOT / "scratch" / "aramaic-completion-shard-a.md"),
    (525, 1050, ROOT / "scratch" / "aramaic-completion-shard-b.md"),
    (1050, 1573, ROOT / "scratch" / "aramaic-completion-shard-c.md"),
)
HEADING = re.compile(
    r"^### مراجعة عضوية:\s*`(aramaic:family:[0-9a-f]+)`.*$",
    re.MULTILINE,
)
CARD_HEADING = re.compile(r"^### بطاقة:.*$", re.MULTILINE)
LEVEL_THREE_HEADING = re.compile(r"^### .*$", re.MULTILINE)
ENTRY = re.compile(r"(kaikki_aramaic:[^`\s،؛\]\)\.]+)")
MEMBER_LINE = re.compile(
    r"^- العضو:\s*`(kaikki_aramaic:[^`]+)`(?P<body>.*)$",
    re.MULTILINE,
)
SELECTED_ROUTE = re.compile(
    r"المرشح والدرجة:\s*(?P<kind>root|hollow-root|nucleus)\s+"
    r"(?P<form>[^\s«؛|]+).*?؛\s*licensed؛\s*"
    r"(?P<rules>\[[^\]]*\])"
)
POSITIVE_RESULT = re.compile(r"(?:ROOT|NUCLEUS)-(?:TRACE|ECHO)")
GAP_RESULT = re.compile(
    r"النتيجة:\s*`?"
    r"(?P<status>OPEN-CANDIDATE|TOOL-GAP|LAW-GAP|SOURCE-GAP|"
    r"MORPHOLOGY-GAP)"
)
CONTAMINATION = re.compile(
    r"tokens truncated|Exit code:|Wall time:|Total output:|^\+###|"
    r"Script running with cell ID|^[+]\s*[-#]",
    re.MULTILINE,
)
ARABIC_INDIC_DIGITS = re.compile(r"[\u0660-\u0669\u06f0-\u06f9]")
LONG_DASH = re.compile(r"[—–]")
REQUIRED_POSITIVE_CARD_FIELDS = (
    "إصدارُ البروتوكول: RECOVERY-v2",
    "الكلمةُ في الفرع:",
    "أقدمُ صورةٍ مستعادة:",
    "الخطوةُ صفر",
    "درجةُ المقارنة:",
    "مسحُ المعاني العربيّة:",
    "المقابلُ من اللسان:",
    "مسارُ الصوت:",
    "المعنى من قاموس الفرع:",
    "المدار:",
    "المصفاة:",
    "فصلُ المتجانسات والاقتراض:",
    "مؤشر اليتم:",
    "إشعاع الأسرة في الفرع:",
    "إشعاع الأسرة في العربية:",
    "جسورُ الاسترداد المفحوصة:",
    "حالةُ الإغلاق:",
    "الحكم (استكشاف):",
    "ملاحظات:",
)
BEGIN = "<!-- ARAMAIC-COMPLETE-2026-07-23:BEGIN -->"
END = "<!-- ARAMAIC-COMPLETE-2026-07-23:END -->"


def sections(text: str) -> dict[str, str]:
    starts = list(HEADING.finditer(text))
    output: dict[str, str] = {}
    for index, match in enumerate(starts):
        end = starts[index + 1].start() if index + 1 < len(starts) else len(text)
        family_id = match.group(1)
        if family_id in output:
            raise ValueError(f"duplicate family review in shard: {family_id}")
        output[family_id] = text[match.start():end].rstrip()
    return output


def positive_cards(text: str) -> list[str]:
    headings = list(LEVEL_THREE_HEADING.finditer(text))
    output: list[str] = []
    for index, heading in enumerate(headings):
        if not heading.group(0).startswith("### بطاقة:"):
            continue
        end = headings[index + 1].start() if index + 1 < len(headings) else len(text)
        output.append(text[heading.start():end].rstrip())
    return output


def expected_for_range(families: list[dict], start: int, end: int) -> dict[str, set[str]]:
    expected: dict[str, set[str]] = {}
    for family in families[start:end]:
        if family["status"] in {"complete-organic", "complete-structural"}:
            continue
        members = {
            member["entry_id"]
            for member in family["members"]
            if member["role"] != "nonlexical" and not member["organic_read"]
        }
        if not members and family["lexical_member_count"] == 0:
            members = {member["entry_id"] for member in family["members"]}
        if members:
            expected[family["family_id"]] = members
    return expected


def validate() -> tuple[list[str], dict]:
    payload = json.loads(AUDIT.read_text(encoding="utf-8"))
    direct_payload = json.loads(DIRECT_SURFACE.read_text(encoding="utf-8"))
    direct_by_entry = {
        item["entry_id"]: item for item in direct_payload["records"]
    }
    with sqlite3.connect(DB) as connection:
        hollow_by_entry: dict[str, set[str]] = {}
        for entry_id, form in connection.execute(
            """
            SELECT c.entry_id, c.form
            FROM candidates c
            JOIN entries e ON e.entry_id=c.entry_id
            WHERE e.language='aramaic'
              AND c.kind='hollow-root'
              AND c.status='licensed'
            ORDER BY c.entry_id, c.form
            """
        ):
            hollow_by_entry.setdefault(entry_id, set()).add(form)
        licensed_routes: dict[tuple[str, str, str], set[tuple[str, ...]]] = {}
        for entry_id, kind, form, rules_json in connection.execute(
            """
            SELECT c.entry_id, c.kind, c.form, c.rule_ids_json
            FROM candidates c
            JOIN entries e ON e.entry_id=c.entry_id
            WHERE e.language='aramaic' AND c.status='licensed'
            """
        ):
            licensed_routes.setdefault((entry_id, kind, form), set()).add(
                tuple(json.loads(rules_json))
            )
        zero_step_by_entry = {
            entry_id: (headword, headword[:-1])
            for entry_id, headword in connection.execute(
                """
                SELECT entry_id, headword
                FROM entries
                WHERE language='aramaic'
                  AND pos IN ('noun', 'adj')
                  AND (
                    headword LIKE '%א'
                    OR headword LIKE '%𐡀'
                    OR headword LIKE '%ܐ'
                  )
                """
            )
        }
    families = payload["families"]
    blocks: list[str] = []
    counts = {
        "expected_families": 0,
        "reviewed_families": 0,
        "expected_members": 0,
        "reviewed_members": 0,
    }
    for start, end, path in SHARDS:
        if not path.exists():
            raise ValueError(f"missing shard: {path.relative_to(ROOT)}")
        text = path.read_text(encoding="utf-8")
        if unicodedata.normalize("NFC", text) != text:
            raise ValueError(f"{path.name}: text is not NFC-normalized")
        contamination = CONTAMINATION.search(text)
        if contamination:
            raise ValueError(
                f"{path.name}: contaminated generated output near "
                f"{contamination.group(0)!r}"
            )
        if LONG_DASH.search(text):
            raise ValueError(f"{path.name}: contains a prohibited long dash")
        if ARABIC_INDIC_DIGITS.search(text):
            raise ValueError(f"{path.name}: contains non-Western digits")
        found = sections(text)
        cards = positive_cards(text)
        expected = expected_for_range(families, start, end)
        missing_families = sorted(set(expected) - set(found))
        extra_families = sorted(set(found) - set(expected))
        if missing_families or extra_families:
            raise ValueError(
                f"{path.name}: family mismatch; "
                f"missing={missing_families[:10]}, extra={extra_families[:10]}"
            )
        for family_id, expected_members in expected.items():
            section = found[family_id]
            if "عدسة الاسترداد:" not in section or "عدسة التشكيك:" not in section:
                raise ValueError(
                    f"{path.name}:{family_id}: both review lenses are required"
                )
            if "حالة الأسرة:" not in section:
                raise ValueError(
                    f"{path.name}:{family_id}: missing explicit family state"
                )
            member_lines = list(MEMBER_LINE.finditer(section))
            member_counts = Counter(match.group(1) for match in member_lines)
            found_members = set(member_counts)
            missing_members = expected_members - found_members
            duplicate_members = sorted(
                member for member, count in member_counts.items() if count != 1
            )
            unknown_members = {
                member
                for member in found_members
                if member.startswith("kaikki_aramaic:")
                and member not in {
                    item["entry_id"]
                    for item in next(
                        family
                        for family in families
                        if family["family_id"] == family_id
                    )["members"]
                }
            }
            if missing_members or unknown_members or duplicate_members:
                raise ValueError(
                    f"{path.name}:{family_id}: member mismatch; "
                    f"missing={sorted(missing_members)}, "
                    f"unknown={sorted(unknown_members)}, "
                    f"duplicates={duplicate_members}"
                )
            lines_by_member = {
                match.group(1): match.group(0) for match in member_lines
            }
            for member in expected_members:
                member_line = lines_by_member[member]
                if "النتيجة:" not in member_line:
                    raise ValueError(
                        f"{path.name}:{family_id}:{member}: "
                        "missing explicit member result"
                    )
                gap = GAP_RESULT.search(member_line)
                if gap:
                    obstacle = re.compile(
                        r"^- عائق:\s*النوع="
                        + re.escape(gap.group("status"))
                        + r"؛\s*يتطلب=[^\n]+؛\s*العضو="
                        + re.escape(member)
                        + r"(?:؛|$)",
                        re.MULTILINE,
                    )
                    if not obstacle.search(section):
                        raise ValueError(
                            f"{path.name}:{family_id}:{member}: "
                            "missing structured member obstacle"
                        )
                selected = SELECTED_ROUTE.search(member_line)
                if selected and POSITIVE_RESULT.search(member_line):
                    stated_rules = tuple(json.loads(selected.group("rules")))
                    licensed = licensed_routes.get(
                        (
                            member,
                            selected.group("kind"),
                            selected.group("form"),
                        ),
                        set(),
                    )
                    if not licensed or stated_rules not in licensed:
                        raise ValueError(
                            f"{path.name}:{family_id}:{member}: "
                            "the stated positive route is not a licensed route"
                        )
                if POSITIVE_RESULT.search(member_line):
                    matching_cards = [card for card in cards if member in card]
                    if len(matching_cards) != 1:
                        raise ValueError(
                            f"{path.name}:{family_id}:{member}: "
                            "positive member must map to exactly one "
                            "RECOVERY-v2 card"
                        )
                    card = matching_cards[0]
                    missing_fields = [
                        field
                        for field in REQUIRED_POSITIVE_CARD_FIELDS
                        if field not in card
                    ]
                    if missing_fields:
                        raise ValueError(
                            f"{path.name}:{family_id}:{member}: "
                            f"positive card misses fields {missing_fields}"
                        )
                    if not re.search(
                        r"LEXICON-INTERNAL|ATTESTED-SHIFT|"
                        r"OBSERVATIONAL-HYPOTHESIS",
                        card,
                    ):
                        raise ValueError(
                            f"{path.name}:{family_id}:{member}: "
                            "positive card lacks a named semantic bridge"
                        )
                    oldest_line = next(
                        (
                            line
                            for line in card.splitlines()
                            if line.startswith("- أقدمُ صورةٍ مستعادة:")
                        ),
                        "",
                    )
                    if "SOURCE-GAP" not in oldest_line:
                        raise ValueError(
                            f"{path.name}:{family_id}:{member}: "
                            "the card must not present the Kaikki headword as "
                            "an independently reconstructed oldest form"
                        )
                    if member in zero_step_by_entry and (
                        "ARAM-ZERO-01" not in card
                        or "Rosenthal" not in card
                        or "Muraoka" not in card
                        or "Porten" not in card
                    ):
                        raise ValueError(
                            f"{path.name}:{family_id}:{member}: "
                            "positive card omits the signed emphatic-state step"
                        )
                direct = direct_by_entry.get(member)
                if direct and (
                    "السطح المباشر" not in member_line
                    or direct["direct_surface_root"] not in member_line
                ):
                    raise ValueError(
                        f"{path.name}:{family_id}:{member}: "
                        "direct-surface old-lexicon fan was not reviewed"
                    )
                if (
                    direct
                    and direct["registry_gap"]
                    and re.search(
                        r"المرشح والدرجة:\s*السطح المباشر.*"
                        r"فجوة سجل.*النتيجة:\s*"
                        r"(?:ROOT|NUCLEUS)-(?:TRACE|ECHO)",
                        member_line,
                    )
                ):
                    raise ValueError(
                        f"{path.name}:{family_id}:{member}: "
                        "a registry-gap surface candidate cannot carry a "
                        "positive verdict"
                    )
                hollow_forms = hollow_by_entry.get(member, set())
                if hollow_forms and (
                    not all(form in member_line for form in hollow_forms)
                    or (
                        "الأجوف" not in member_line
                        and "hollow-root" not in member_line
                    )
                ):
                    raise ValueError(
                        f"{path.name}:{family_id}:{member}: "
                        f"licensed hollow roots were not reviewed: "
                        f"{sorted(hollow_forms)}"
                    )
                zero_step = zero_step_by_entry.get(member)
                if zero_step and (
                    "ARAM-ZERO-01" not in member_line
                    or f"الصورة المؤكدة={zero_step[0]}" not in member_line
                    or f"الصورة المجردة={zero_step[1]}" not in member_line
                    or "Rosenthal" not in member_line
                    or "Muraoka" not in member_line
                    or "Porten" not in member_line
                ):
                    raise ValueError(
                        f"{path.name}:{family_id}:{member}: "
                        "signed emphatic-state zero step is incomplete"
                    )
        counts["expected_families"] += len(expected)
        counts["reviewed_families"] += len(found)
        counts["expected_members"] += sum(map(len, expected.values()))
        counts["reviewed_members"] += sum(
            len(expected[family_id]) for family_id in found
        )
        blocks.append("\n\n".join(found[family_id] for family_id in expected))
    return blocks, counts


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    body = READING.read_text(encoding="utf-8")
    if args.check and BEGIN in body:
        if body.count(BEGIN) != 1 or body.count(END) != 1:
            raise ValueError("Aramaic completion block markers are not unique")
        payload = json.loads(AUDIT.read_text(encoding="utf-8"))
        summary = payload["summary"]
        if summary["remaining_lexical_member_count"] != 0:
            raise ValueError(
                "final Aramaic reading still has unread lexical members"
            )
        incomplete = {
            status: count
            for status, count in summary["family_status_counts"].items()
            if status not in {"complete-organic", "complete-structural"}
        }
        if incomplete:
            raise ValueError(
                f"final Aramaic reading has incomplete families: {incomplete}"
            )
        print(json.dumps(summary, ensure_ascii=False))
        return 0
    blocks, counts = validate()
    if args.check:
        print(json.dumps(counts, ensure_ascii=False))
        return 0
    if BEGIN in body or END in body:
        raise ValueError("Aramaic completion block is already present")
    preface = f"""

{BEGIN}

## إكمال المعجم الآرامي أسرةً أسرة، 2026-07-23، محلي للمراجعة الثالثة

### بيان النطاق: الخطوة 14

- المصدر: الجرد الحي للقطة Kaikki الآرامية المثبتة، نسخة الأسر الحالية، لا طابور قديم.
- المقام: كل أسرة حالية وكل عضو معجمي لم تثبت له قراءة دلالية عضوية قبل هذه الجولة.
- الوحدة: الأسرة للتغطية والعرض، والعضو أو سلسلة المعنى للحكم، ولا وراثة عبر المركبات أو المتجانسات.
- المنهج: الجذر الكامل، ثم الأجوف، ثم النواة، ثم المدار؛ مروحة عربية كاملة غير مقتطعة من مصدرين قديمين مستقلين حيث خرج جذر أو أجوف؛ ثم مصفاة القرض والعلم والصيغة؛ ثم عدستا الاسترداد والتشكيك.
- حالة الإيداع: كل حكم موجب في هذا الملحق محلي للمراجعة الثالثة. لا تحديث للسجل المركزي ولا تشغيل لخط البرهان.

"""
    appendix = preface + "\n\n".join(blocks) + f"\n\n{END}\n"
    temporary = READING.with_suffix(READING.suffix + ".tmp")
    temporary.write_text(body.rstrip() + appendix, encoding="utf-8")
    temporary.replace(READING)
    print(json.dumps(counts, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
