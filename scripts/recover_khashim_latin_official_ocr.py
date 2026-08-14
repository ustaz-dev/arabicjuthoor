# -*- coding: utf-8 -*-
"""استرد رؤوس «اللاتينية العربية» الباقية من المسح الرسمي الجديد.

لا يبدل هذا المسار إلا ``foreign`` في صف يحمل علامة السقوط المسجلة. يقابل
صفوف خشيم بمدخلات المسح الرسمي في ترتيب الكتاب، ولا يعيد استعمال مدخل جديد.
الرأس أو الجذر السليم في المسح السابق مرساة ترتيب، ثم يقبل صف العيب إذا
تطابق الجذر أو قام دليل دلالي قوي مستقل من المعنى والشرح.
"""
from __future__ import annotations

import argparse
import difflib
import json
import pathlib
import re
import sys
import unicodedata
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import harvest_khashim as H  # noqa: E402

DEFAULT_NEW = pathlib.Path(
    r"C:\Users\yassi\AI Projects\Resources\prior-art\ocr-khashim-latin-recovery-20260814\full.md"
)
DEFAULT_PAIRS = ROOT / "data" / "khashim-pairs.json"
DEFAULT_OUT = ROOT / "data" / "khashim-latin-official-ocr-recoveries.json"
FALLEN = "(سقطَ حرفُه في المسح)"
PAGE = re.compile(r"<!-- صفحة (\d+) -->")
ANSWER = re.compile(
    r"^[\s*·•]*(?:[ء-ي]{0,4}\s*)?العربية\s*[:：]\s*(.+)$"
)


def latin_fold(value: Any) -> str:
    value = unicodedata.normalize("NFKD", str(value or ""))
    value = value.encode("ascii", "ignore").decode("ascii").lower()
    return re.sub(r"[^a-z]", "", value)


def latin_head(line: str) -> tuple[str, str] | None:
    """رأس لاتيني في أول السطر، مستقلًا أو متبوعًا بمعناه."""
    line = line.strip().strip("`*_#")
    if not line:
        return None
    arabic = re.search(r"[\u0600-\u06ff]", line)
    if arabic:
        token = line[:arabic.start()].strip().rstrip(".;:")
        inline = line[arabic.start():].strip()
    else:
        plain = line.strip().rstrip(".;:")
        if " " in plain and not any(mark in plain for mark in ",()"):
            token, inline = plain.split(maxsplit=1)
        else:
            token, inline = plain, ""
    token = re.sub(r"\(\d+\)", "", token).strip()

    def shape_ok(value: str) -> bool:
        return bool(value) and all(
            char.isalpha() or char in "-'(),/ " for char in value
        )

    if not shape_ok(token) and " " in token:
        first, rest = token.split(maxsplit=1)
        token = first.strip(".,;:")
        inline = H.clean(f"{rest} {inline}")
    letters = [char for char in token if char.isalpha()]
    if len(letters) < 2:
        return None
    if not shape_ok(token):
        return None
    if any(
        ord(char) > 0x024F and not 0x1E00 <= ord(char) <= 0x1EFF
        for char in letters
    ):
        return None
    return token, inline


def parse_new(path: pathlib.Path) -> list[dict[str, Any]]:
    raw = path.read_text(encoding="utf-8").splitlines()
    lines: list[tuple[str, int, int]] = []
    page = 0
    for line_number, raw_line in enumerate(raw, 1):
        marker = PAGE.fullmatch(raw_line.strip())
        if marker:
            page = int(marker.group(1))
        lines.append((H.clean(raw_line), page, line_number))

    rows: list[dict[str, Any]] = []
    for index, (line, page, answer_line) in enumerate(lines):
        match = ANSWER.match(line)
        if not match or page < 39:
            continue
        arabic = H.clean(match.group(1))
        root_match = H.RX_ROOT.match(arabic)
        if not root_match:
            continue
        root = root_match.group(1)
        gloss = H.clean(arabic[root_match.end():])
        head = sense = ""
        head_line = 0
        for back in range(1, 13):
            if index - back < 0:
                break
            candidate, _, candidate_line = lines[index - back]
            if ANSWER.match(candidate):
                break
            parsed = latin_head(candidate)
            if not parsed:
                continue
            head, inline = parsed
            head_line = candidate_line
            between = [
                lines[position][0]
                for position in range(index - back + 1, index)
                if lines[position][0] and not ANSWER.match(lines[position][0])
            ]
            sense = H.clean(" ".join(([inline] if inline else []) + between))[:200]
            break
        if not head:
            continue
        rows.append({
            "foreign": head,
            "foreign_sense": sense,
            "arabic_root": root,
            "arabic_gloss": gloss,
            "page": page,
            "head_line": head_line,
            "answer_line": answer_line,
        })
    return rows


def ar_bare(value: Any) -> str:
    return H._bare_ar(str(value or ""))


def similarity(left: Any, right: Any) -> float:
    a, b = ar_bare(left), ar_bare(right)
    if not a or not b:
        return 0.0
    return difflib.SequenceMatcher(None, a, b, autojunk=False).ratio()


def align(old: list[dict[str, Any]], new: list[dict[str, Any]]) -> list[tuple[int, int]]:
    n, m, gap = len(old), len(new), -2.5
    old_sense = [ar_bare(row.get("foreign_sense")) for row in old]
    old_gloss = [ar_bare(row.get("arabic_gloss")) for row in old]
    new_sense = [ar_bare(row.get("foreign_sense")) for row in new]
    new_gloss = [ar_bare(row.get("arabic_gloss")) for row in new]

    def ratio(a: str, b: str) -> float:
        if not a or not b:
            return 0.0
        return difflib.SequenceMatcher(None, a, b, autojunk=False).ratio()

    scores = [[0.0] * (m + 1) for _ in range(n + 1)]
    paths = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        scores[i][0], paths[i][0] = i * gap, 1
    for j in range(1, m + 1):
        scores[0][j], paths[0][j] = j * gap, 2
    for i in range(1, n + 1):
        old_row = old[i - 1]
        for j in range(1, m + 1):
            new_row = new[j - 1]
            head_exact = (
                old_row.get("foreign") != FALLEN
                and latin_fold(old_row.get("foreign")) == latin_fold(new_row.get("foreign"))
                and bool(latin_fold(new_row.get("foreign")))
            )
            root_exact = ar_bare(old_row.get("arabic_root")) == ar_bare(
                new_row.get("arabic_root")
            )
            sense = ratio(old_sense[i - 1], new_sense[j - 1])
            gloss = ratio(old_gloss[i - 1], new_gloss[j - 1])
            match_score = (
                (18.0 if head_exact else 0.0)
                + (8.0 if root_exact else 0.0)
                + 6.0 * sense
                + 4.0 * gloss
            )
            if not head_exact and not root_exact and max(sense, gloss) < 0.30:
                match_score = -9.0
            elif not head_exact and not root_exact:
                match_score -= 3.0
            choices = (
                scores[i - 1][j - 1] + match_score,
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
            aligned.append((i - 1, j - 1))
            i, j = i - 1, j - 1
        elif i and (not j or choice == 1):
            i -= 1
        else:
            j -= 1
    aligned.reverse()
    return aligned


def accepted(old: dict[str, Any], new: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    root_exact = ar_bare(old.get("arabic_root")) == ar_bare(new.get("arabic_root"))
    sense = similarity(old.get("foreign_sense"), new.get("foreign_sense"))
    gloss = similarity(old.get("arabic_gloss"), new.get("arabic_gloss"))
    strong_semantics = (
        sense >= 0.72
        or gloss >= 0.72
        or (sense >= 0.55 and gloss >= 0.25)
        or (gloss >= 0.55 and sense >= 0.25)
    )
    evidence = {
        "root_exact": root_exact,
        "old_root": old.get("arabic_root"),
        "new_root": new.get("arabic_root"),
        "sense_similarity": round(sense, 6),
        "arabic_gloss_similarity": round(gloss, 6),
        "new_foreign_sense": new.get("foreign_sense"),
        "new_arabic_gloss": new.get("arabic_gloss"),
        "acceptance": "exact-root-monotonic" if root_exact else "strong-independent-semantics",
    }
    return root_exact or strong_semantics, evidence


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--new", type=pathlib.Path, default=DEFAULT_NEW)
    parser.add_argument("--pairs", type=pathlib.Path, default=DEFAULT_PAIRS)
    parser.add_argument("--out", type=pathlib.Path, default=DEFAULT_OUT)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    payload = json.loads(args.pairs.read_text(encoding="utf-8"))
    old = [row for row in payload["rows"] if row.get("source") == "khashim-latin"]
    if len(old) != 560:
        raise SystemExit(f"تغير مقام صفوف اللاتينية: {len(old)}")
    fallen = [index for index, row in enumerate(old) if row.get("foreign") == FALLEN]
    if len(fallen) != 223:
        raise SystemExit(f"تغير مقام الرؤوس الباقية الساقطة: {len(fallen)}")
    new = parse_new(args.new)
    if len(new) != 702:
        raise SystemExit(f"تغير مقام مداخل المسح الرسمي: {len(new)}")

    recoveries: list[dict[str, Any]] = []
    aligned = align(old, new)
    for old_index, new_index in aligned:
        old_row, new_row = old[old_index], new[new_index]
        if old_row.get("foreign") != FALLEN:
            continue
        ok, evidence = accepted(old_row, new_row)
        if not ok:
            continue
        recoveries.append({
            "source_index": old_index,
            "source": "khashim-latin",
            "arabic_root": old_row.get("arabic_root"),
            "registered_scan_reasons": [
                "رأس المدخل اللاتيني مسجل بأنه سقط في المسح القديم"
            ],
            "fields": {
                "foreign": {"legacy": FALLEN, "recovered": new_row["foreign"]}
            },
            "old_location": {"source_index": old_index},
            "new_location": {
                "page": new_row["page"],
                "head_line": new_row["head_line"],
                "answer_line": new_row["answer_line"],
            },
            "matched_new_row": new_index,
            "alignment_evidence": evidence,
        })

    source_indices = [row["source_index"] for row in recoveries]
    new_indices = [row["matched_new_row"] for row in recoveries]
    if len(source_indices) != len(set(source_indices)) or len(new_indices) != len(set(new_indices)):
        raise SystemExit("أعيد استعمال صف قديم أو مدخل جديد")
    if source_indices != sorted(source_indices) or new_indices != sorted(new_indices):
        raise SystemExit("اختل ترتيب الاصطفاف الرتيب")
    exact = sum(row["alignment_evidence"]["root_exact"] for row in recoveries)
    semantic = len(recoveries) - exact
    if (len(recoveries), exact, semantic) != (150, 107, 43):
        raise SystemExit(
            f"تغير جرد الاسترداد: الكل/الجذر/الدلالة={len(recoveries)}/{exact}/{semantic}"
        )

    output = {
        "schema": "khashim-latin-official-ocr-recovery-v1",
        "generated_by": "scripts/recover_khashim_latin_official_ocr.py",
        "old_source": "data/khashim-pairs.json#source=khashim-latin",
        "new_source": str(args.new),
        "old_rows": len(old),
        "registered_fallen_heads": len(fallen),
        "new_candidates": len(new),
        "aligned_rows": len(aligned),
        "restored_unique_rows": len(recoveries),
        "restored_by_evidence": {"exact_root": exact, "strong_semantics": semantic},
        "still_fallen": len(fallen) - len(recoveries),
        "recoveries": recoveries,
    }
    print(json.dumps({
        "old_rows": len(old),
        "registered_fallen_heads": len(fallen),
        "new_candidates": len(new),
        "aligned_rows": len(aligned),
        "restored_unique_rows": len(recoveries),
        "restored_by_evidence": output["restored_by_evidence"],
        "still_fallen": output["still_fallen"],
    }, ensure_ascii=False, indent=1))
    if args.dry_run:
        return 0
    args.out.write_text(json.dumps(output, ensure_ascii=False, indent=1) + "\n",
                        encoding="utf-8", newline="\n")
    print(f"كتب: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
