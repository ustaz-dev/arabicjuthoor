#!/usr/bin/env python3
"""Measure whether the current Akkadian reading has a valid denominator.

The audit is structural and issues no linguistic verdict.  It compares the
curated reading cards with the pinned 6,820-headword inventory, its 4,769
families, and the explicit scope limits of the lexical overlay.
"""
from __future__ import annotations

import json
import re
import sqlite3
import sys
import tempfile
import unicodedata
from collections import Counter
from pathlib import Path

import build_status_snapshot as status


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


ROOT = Path(__file__).resolve().parents[1]
READING = ROOT / "04-cross-linguistic" / "readings" / "akkadian.md"
DB = ROOT / "cache" / "recovery_pipeline" / "inventory-v5.sqlite"
OVERLAY_PIN = (
    ROOT / "04-cross-linguistic" / "data" / "akkadian-lexical-overlay-pin.json"
)
CAD_PIN = (
    ROOT / "04-cross-linguistic" / "data" / "akkadian-cad-volume-pin.json"
)
CAD_P_EVALUATION = (
    ROOT / "04-cross-linguistic" / "data" / "cad-p-headword-evaluation.json"
)
CACHE = (
    ROOT
    / "cache"
    / "recovery_pipeline"
    / "akkadian-denominator-audit.json"
)
AUDIT = (
    ROOT
    / "05-audits"
    / "2026-07-27-akkadian-denominator-audit.md"
)
FAMILY_ID = re.compile(r"akkadian:family:[0-9a-f]+")
POSITIVE_PREFIXES = ("ROOT-", "NUCLEUS-", "FLOOR-")
NONLEXICAL_POS = {
    "mwe",
    "phrase",
    "suffix",
    "particle",
    "conj",
    "prep",
    "adp",
    "pron",
    "adv",
    "num",
}
BRANCH_LINE = re.compile(r"^- الكلمةُ في الفرع:\s*(.+)$", re.MULTILINE)
CODE_SPAN = re.compile(r"`([^`]+)`")


def normalized_surface(value: str) -> str:
    value = unicodedata.normalize("NFC", value).strip().lower()
    value = re.sub(r"\s+[A-Z](?:\s|$)", " ", value)
    return value.strip()


def card_surface_linkage_probe(
    connection: sqlite3.Connection,
    cards: list[str],
) -> Counter[str]:
    """Probe exact surface linkage without assigning a family to any card."""
    index: dict[str, set[str]] = {}
    rows = connection.execute(
        """
        SELECT e.headword,e.romanization,fm.family_id
        FROM entries e
        JOIN family_members fm ON fm.entry_id=e.entry_id
        WHERE e.language='akkadian'
        """
    ).fetchall()
    for headword, romanization, family_id in rows:
        for surface in (headword, romanization):
            if surface:
                index.setdefault(normalized_surface(surface), set()).add(
                    family_id
                )

    counts: Counter[str] = Counter()
    for card in cards:
        branch_match = BRANCH_LINE.search(card)
        spans = CODE_SPAN.findall(branch_match.group(1)) if branch_match else []
        families: set[str] = set()
        for span in spans:
            for part in re.split(
                r"[/،]|\s+و(?=[A-Za-zāâēīūṣṭḫšʾ])",
                span,
            ):
                part = part.strip().strip("().")
                families.update(index.get(normalized_surface(part), set()))
        if not families:
            counts["unmatched"] += 1
        elif len(families) == 1:
            counts["unique_family"] += 1
        else:
            counts["multiple_families"] += 1
    return counts


def atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        newline="\n",
        dir=path.parent,
        delete=False,
    ) as handle:
        handle.write(unicodedata.normalize("NFC", text))
        temporary = Path(handle.name)
    temporary.replace(path)


def family_examples(
    connection: sqlite3.Connection,
    headwords: tuple[str, ...],
) -> list[dict[str, str]]:
    placeholders = ",".join("?" for _ in headwords)
    rows = connection.execute(
        f"""
        SELECT e.entry_id,e.headword,e.gloss,fm.family_id
        FROM entries e
        JOIN family_members fm ON fm.entry_id=e.entry_id
        WHERE e.language='akkadian' AND e.headword IN ({placeholders})
        ORDER BY e.headword,e.entry_id
        """,
        headwords,
    ).fetchall()
    return [
        {
            "entry_id": row[0],
            "headword": row[1],
            "gloss": row[2],
            "family": row[3],
        }
        for row in rows
    ]


def main() -> int:
    reading_text = READING.read_text(encoding="utf-8")
    cards = status.reading_cards(reading_text)
    cross = Counter()
    for card in cards:
        blocker = status.live_blocker(card) or "BLANK"
        verdict = status.live_verdict(card) or "NONE"
        verdict_class = (
            "positive"
            if verdict.startswith(POSITIVE_PREFIXES)
            else "nonpositive"
        )
        cross[(blocker, verdict_class)] += 1

    overlay = json.loads(OVERLAY_PIN.read_text(encoding="utf-8"))
    cad_pin = json.loads(CAD_PIN.read_text(encoding="utf-8"))
    cad_evaluation = json.loads(
        CAD_P_EVALUATION.read_text(encoding="utf-8")
    )

    connection = sqlite3.connect(DB)
    try:
        inventory_entries, inventory_families = connection.execute(
            """
            SELECT COUNT(*),COUNT(DISTINCT fm.family_id)
            FROM entries e
            JOIN family_members fm ON fm.entry_id=e.entry_id
            WHERE e.language='akkadian'
            """
        ).fetchone()
        pos_counts = Counter(
            dict(
                connection.execute(
                    """
                    SELECT e.pos,COUNT(*)
                    FROM entries e
                    WHERE e.language='akkadian'
                    GROUP BY e.pos
                    """
                ).fetchall()
            )
        )
        pure_name_families = connection.execute(
            """
            SELECT COUNT(*)
            FROM (
              SELECT fm.family_id
              FROM family_members fm
              JOIN entries e ON e.entry_id=fm.entry_id
              WHERE e.language='akkadian'
              GROUP BY fm.family_id
              HAVING SUM(CASE WHEN e.pos='name' THEN 0 ELSE 1 END)=0
            )
            """
        ).fetchone()[0]
        placeholders = ",".join("?" for _ in NONLEXICAL_POS)
        pure_nonlexical_families = connection.execute(
            f"""
            SELECT COUNT(*)
            FROM (
              SELECT fm.family_id
              FROM family_members fm
              JOIN entries e ON e.entry_id=fm.entry_id
              WHERE e.language='akkadian'
              GROUP BY fm.family_id
              HAVING SUM(
                CASE WHEN e.pos IN ({placeholders}) THEN 0 ELSE 1 END
              )=0
            )
            """,
            tuple(sorted(NONLEXICAL_POS)),
        ).fetchone()[0]
        split_examples = family_examples(
            connection,
            (
                "alāku (v.)",
                "alākum",
                "imēru",
                "imērum",
                "râmu",
                "râmum",
            ),
        )
        surface_probe = card_surface_linkage_probe(connection, cards)
    finally:
        connection.close()

    card_family_ids = sorted(set(FAMILY_ID.findall(reading_text)))
    positives = sum(
        1
        for card in cards
        if status.live_verdict(card).startswith(POSITIVE_PREFIXES)
    )
    positive_with_blocker = sum(
        1
        for card in cards
        if status.live_verdict(card).startswith(POSITIVE_PREFIXES)
        and status.live_blocker(card)
    )
    positive_without_blocker = positives - positive_with_blocker
    terminal_closures = sum(
        1
        for card in cards
        if status.counted_outcome(card) in status.CLOSURE_VERDICTS
    )
    p_proxy = cad_evaluation[
        "cad_referenced_subset_operational_proxy"
    ]
    summary = {
        "reading_cards": len(cards),
        "cards_with_stable_family_id": sum(
            bool(FAMILY_ID.search(card)) for card in cards
        ),
        "distinct_family_ids_in_reading": len(card_family_ids),
        "positive_verdict_lines": positives,
        "positive_with_live_nonready_blocker": positive_with_blocker,
        "positive_without_structured_blocker": positive_without_blocker,
        "terminal_closures": terminal_closures,
        "inventory_entries": inventory_entries,
        "inventory_families": inventory_families,
        "inventory_unknown_pos_entries": pos_counts["unknown"],
        "pure_name_families_retrieval_only": pure_name_families,
        "pure_nonlexical_families_retrieval_only": pure_nonlexical_families,
        "overlay_claims_complete_published_lexicon": bool(
            overlay["claims"]["complete_published_lexicon"]
        ),
        "cad_local_pdf_volumes": cad_pin["volume_count"],
        "cad_p_generalization_gate": "BLOCKED",
        "cad_p_candidate_match_proxy": p_proxy[
            "matched_candidate_fraction_against_dal_id_proxy"
        ],
        "cad_p_dal_id_proxy_coverage": p_proxy["dal_id_proxy_coverage"],
        "eligible_denominator_families_now": 0,
        "surface_probe_unique_family": surface_probe["unique_family"],
        "surface_probe_multiple_families": surface_probe[
            "multiple_families"
        ],
        "surface_probe_unmatched": surface_probe["unmatched"],
    }
    expected = {
        "reading_cards": 128,
        "cards_with_stable_family_id": 0,
        "distinct_family_ids_in_reading": 0,
        "positive_verdict_lines": 67,
        "positive_with_live_nonready_blocker": 13,
        "positive_without_structured_blocker": 54,
        "terminal_closures": 0,
        "inventory_entries": 6820,
        "inventory_families": 4769,
        "inventory_unknown_pos_entries": 4783,
        "pure_name_families_retrieval_only": pure_name_families,
        "pure_nonlexical_families_retrieval_only": pure_nonlexical_families,
        "overlay_claims_complete_published_lexicon": False,
        "cad_local_pdf_volumes": 26,
        "cad_p_generalization_gate": "BLOCKED",
        "cad_p_candidate_match_proxy": p_proxy[
            "matched_candidate_fraction_against_dal_id_proxy"
        ],
        "cad_p_dal_id_proxy_coverage": p_proxy["dal_id_proxy_coverage"],
        "eligible_denominator_families_now": 0,
        "surface_probe_unique_family": 63,
        "surface_probe_multiple_families": 29,
        "surface_probe_unmatched": 36,
    }
    if summary != expected:
        raise ValueError(f"unexpected Akkadian denominator state: {summary}")

    payload = {
        "schema": "akkadian-denominator-audit-v1",
        "status": "STRUCTURAL-AUDIT-NO-VERDICTS",
        "summary": summary,
        "card_state_cross_tab": [
            {
                "blocker": blocker,
                "verdict_class": verdict_class,
                "cards": count,
            }
            for (blocker, verdict_class), count in sorted(cross.items())
        ],
        "morphological_split_examples": split_examples,
        "conclusion": {
            "current_reading_is_curated_candidate_set": True,
            "current_reading_is_complete_family_sample": False,
            "current_inventory_is_complete_cad_lexicon": False,
            "safe_use_in_yield_denominator": False,
            "required_before_denominator": [
                "stable family IDs on every reviewed card",
                "signed Akkadian morphology policy before collapsing case-final m",
                "complete or explicitly sampled family frame",
                "member-level links and closures recorded symmetrically",
                "CAD headword extraction must pass its visual gold gate",
            ],
        },
    }
    atomic_write(
        CACHE,
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
    )

    split_lines = [
        f"- `{row['headword']}` في `{row['family']}`."
        for row in split_examples
    ]
    atomic_write(
        AUDIT,
        "\n".join(
            [
                "# تدقيق مقام الأكّادية",
                "",
                "**التاريخ:** 2026-07-27",
                "",
                "## النتيجة",
                "",
                "ملف القراءة الأكّادية الحالي دفتر مرشحات منتقاة، لا عينة أسر مكتملة. لذلك نسبة الصلات فيه لا مقام لها، ولا يجوز إصلاحها بإنتاج سوالب من غياب البطاقة.",
                "",
                "## القياس البنيوي",
                "",
                f"- بطاقات القراءة الحقيقية: {summary['reading_cards']}.",
                f"- بطاقات تحمل معرف أسرة ثابتًا: {summary['cards_with_stable_family_id']}.",
                f"- سطور الحكم الموجب: {summary['positive_verdict_lines']}، منها {summary['positive_with_live_nonready_blocker']} تحمل عائقًا حيًا غير جاهز.",
                f"- إغلاقات نهائية: {summary['terminal_closures']}.",
                f"- مسبار الربط السطحي فقط: {summary['surface_probe_unique_family']} بطاقة تصل إلى أسرة واحدة، و{summary['surface_probe_multiple_families']} إلى أسر متعددة، و{summary['surface_probe_unmatched']} بلا تطابق سطحي.",
                f"- الجرد المثبت: {summary['inventory_entries']} رأسًا في {summary['inventory_families']} أسرة استرجاعية.",
                f"- مداخل صنفها غير معروف في اللقطة: {summary['inventory_unknown_pos_entries']}.",
                "- اتحاد المصادر نفسه يصرح بأنه لا يمثل المعجم الأكّادي المنشور كاملًا.",
                "",
                "## عائق الصرف قبل المقام",
                "",
                "صور اللمّة ذات ميم الحالة وصورها المنشورة بلا الميم موزعة الآن على أسر مختلفة، لأن قاعدة نزع الميم لم توقع. أمثلة الجرد:",
                "",
                *split_lines,
                "",
                "فلا تكون 4,769 أسرة مقامًا لغويًا نهائيًا قبل ورقة الصرف، ولا يجوز دمجها حدسًا.",
                "",
                "## CAD",
                "",
                f"- مجلدات PDF المحلية المثبتة: {summary['cad_local_pdf_volumes']}.",
                "- بوابة تعميم استخراج الرؤوس ما زالت محجوبة: قياس P المتاح وكيل تداخل مع DAL، لا دقة واستردادًا حقيقيين.",
                "- وجود PDFات محلية يزيل عائق الصورة، لكنه لا يزيل عائق بناء العينة الذهبية البصرية.",
                "",
                "## القرار التشغيلي",
                "",
                "1. تبقى الأكّادية خارج منحنى العائد.",
                "2. لا يحول أي غياب في دفتر المرشحات إلى `NO-TRACE` أو إغلاق.",
                "3. يبدأ الإصلاح من هوية الأسرة: معرف ثابت لكل بطاقة، ثم ورقة صرف موقعة، ثم إطار أسري كامل أو عينة مسجلة، ثم تسجيل الصلات والإغلاقات معًا.",
                "4. العدد المؤهل للمقام الآن صفر، لا لأن الأكّادية بلا صلات، بل لأن وحدة العد غير قابلة لإعادة البناء بعد.",
                "",
                "هذا محضر داخلي بنيوي، لا رقم فيه للنشر ولا تشغيل لخط البرهان.",
                "",
            ]
        ),
    )
    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
