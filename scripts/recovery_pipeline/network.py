from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_NETWORK = ROOT / "04-cross-linguistic" / "shift-network-draft.md"
ROW_ID = re.compile(r"^[A-Z]+(?:-[A-Z]+)*-\d+$")
ARABIC = set("ءابتثجحخدذرزسشصضطظعغفقكلمنهوي")

LANGUAGE_MARKERS = {
    "العربي": "arabic",
    "عربي": "arabic",
    "الآرامي": "aramaic",
    "آرامي": "aramaic",
    "العبري": "hebrew",
    "عبري": "hebrew",
    "الأكّادي": "akkadian",
    "أكّادي": "akkadian",
    "الإيراني": "iranian",
    "إيراني": "iranian",
    "الهندي": "indo_aryan",
    "هندي": "indo_aryan",
    "اليوناني": "ancient_greek",
    "يوناني": "ancient_greek",
    "اللاتيني": "latin",
    "لاتيني": "latin",
    "الجرماني": "germanic",
    "جرماني": "germanic",
    "المصري": "egyptian",
    "مصري": "egyptian",
    "القبطي": "coptic",
    "قبطي": "coptic",
}

PROFILE_FAMILIES = {
    "ancient_greek": {"ancient_greek"},
    "coptic": {"coptic", "egyptian"},
    "egyptian": {"egyptian"},
    "latin": {"latin"},
    "aramaic": {"aramaic"},
    "hebrew": {"hebrew"},
    "akkadian": {"akkadian"},
    "persian": {"iranian"},
    "gothic": {"germanic"},
    "old_norse": {"germanic"},
    "old_english": {"germanic"},
}

TOKEN_FOLD = {"θ": "th", "š": "sh", "ḫ": "kh", "ḥ": "hh", "ġ": "gh", "ṣ": "s", "ṭ": "t", "ḍ": "d"}
MANUAL_CONDITION_MARKERS = ("قبل صامت", "حيث يشهد", "موقع أوّل", "موقع أول", "إذا لم", "مشروط")


@dataclass(frozen=True)
class ShiftRule:
    row_id: str
    shift: str
    direction_text: str
    articulation: str
    example: str
    documentation: str
    note: str
    left_tokens: tuple[str, ...]
    right_tokens: tuple[str, ...]
    kind: str
    direction: str
    scopes: tuple[str, ...]
    automation: str
    requires_route_flag: bool

    def scope_allows(self, language: str) -> bool:
        if not self.scopes:
            return True
        if self.scopes == ("arabic",) and "داخل العربي" in self.direction_text:
            return True
        families = PROFILE_FAMILIES.get(language, {language})
        return bool(families.intersection(self.scopes))


def _side_tokens(value: str) -> tuple[str, ...]:
    value = re.sub(r"\([^)]*\)", "", value)
    value = value.replace("*", "").replace("[", "").replace("]", "")
    parts = re.split(r"[/،,\s]+", value)
    tokens: list[str] = []
    for part in parts:
        part = part.strip(".؛;:").lower()
        if not part:
            continue
        if part in {"ø", "Ø"}:
            tokens.append("ø")
            continue
        if len(part) == 1 and part in ARABIC:
            tokens.append(part)
            continue
        folded = "".join(TOKEN_FOLD.get(char, char) for char in part)
        if re.fullmatch(r"[a-z]+", folded):
            tokens.append(folded)
    return tuple(dict.fromkeys(tokens))


def _scopes(direction: str) -> tuple[str, ...]:
    found = {tag for marker, tag in LANGUAGE_MARKERS.items() if marker in direction}
    return tuple(sorted(found))


def _kind(row_id: str, left: tuple[str, ...], right: tuple[str, ...]) -> str:
    if row_id.startswith("BR-"):
        return "branch-internal"
    left_ar = any(token in ARABIC for token in left)
    right_ar = any(token in ARABIC for token in right)
    if left_ar and right_ar:
        return "arabic-correspondence"
    if left_ar != right_ar:
        return "cross-script"
    if left and right:
        return "branch-correspondence"
    return "manual"


def compile_network(path: Path = DEFAULT_NETWORK) -> list[ShiftRule]:
    rules: list[ShiftRule] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) != 7 or not ROW_ID.fullmatch(cells[0]):
            continue
        row_id, shift, direction_text, articulation, example, documentation, note = cells
        if "↔" in shift:
            left_raw, right_raw = shift.split("↔", 1)
            left, right = _side_tokens(left_raw), _side_tokens(right_raw)
        else:
            left, right = (), ()
        kind = _kind(row_id, left, right)
        direction = "both" if "كلاهما" in direction_text else "forward" if "من " in direction_text and " إلى " in direction_text else "internal"
        combined = f"{direction_text} {note}"
        automation = "manual"
        if kind in {"arabic-correspondence", "cross-script"} and left and right:
            automation = "manual-condition" if any(marker in combined for marker in MANUAL_CONDITION_MARKERS) else "automatic"
        if kind in {"branch-internal", "branch-correspondence"}:
            automation = "manual-condition" if any(marker in combined for marker in MANUAL_CONDITION_MARKERS) else "manual"
        rules.append(
            ShiftRule(
                row_id=row_id,
                shift=shift,
                direction_text=direction_text,
                articulation=articulation,
                example=example,
                documentation=documentation,
                note=note,
                left_tokens=left,
                right_tokens=right,
                kind=kind,
                direction=direction,
                scopes=_scopes(direction_text),
                automation=automation,
                requires_route_flag="سند استعاري" in note or "اقتراض" in note,
            )
        )
    return rules


def rules_by_id(rules: Iterable[ShiftRule]) -> dict[str, ShiftRule]:
    return {rule.row_id: rule for rule in rules}


def network_report(rules: list[ShiftRule]) -> dict[str, object]:
    kinds: dict[str, int] = {}
    automation: dict[str, int] = {}
    for rule in rules:
        kinds[rule.kind] = kinds.get(rule.kind, 0) + 1
        automation[rule.automation] = automation.get(rule.automation, 0) + 1
    return {
        "rows": len(rules),
        "kinds": dict(sorted(kinds.items())),
        "automation": dict(sorted(automation.items())),
        "row_ids": [rule.row_id for rule in rules],
    }


def dump_network_json(rules: list[ShiftRule]) -> str:
    return json.dumps([asdict(rule) for rule in rules], ensure_ascii=False, indent=2)
