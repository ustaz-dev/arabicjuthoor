from __future__ import annotations

import json
from dataclasses import dataclass
from itertools import combinations, product
from pathlib import Path

from .network import ARABIC, ShiftRule


ROOT = Path(__file__).resolve().parents[2]
HAMZA = {"أ": "ء", "إ": "ء", "آ": "ء"}

# The mouth-family anchor is explicitly separate from licensed shift rows.
# It retrieves possibilities only and is never reported as a historical law.
ANCHOR_MAP: dict[str, tuple[str, ...]] = {
    "b": ("ب",), "p": ("ب", "ف"), "ph": ("ف",), "f": ("ف",), "m": ("م",),
    "w": ("و",), "v": ("و", "ف"), "t": ("ت", "ط"), "th": ("ث",), "d": ("د", "ض"),
    "dh": ("ذ", "ظ"), "s": ("س", "ص"), "sh": ("ش",), "z": ("ز",), "n": ("ن",),
    "l": ("ل",), "r": ("ر",), "k": ("ك", "ق"), "g": ("ج", "ق", "ك"), "q": ("ق",),
    "kh": ("خ",), "gh": ("غ",), "hh": ("ح",), "h": ("ه", "ح"), "ayin": ("ع",),
    "qstop": ("ء",), "j": ("ج", "ي"), "y": ("ي",), "ch": ("ش", "ج"),
}

STATUS_RANK = {"licensed": 0, "manual-condition": 1, "scope-gap": 2}


@dataclass(frozen=True)
class ArabicInventory:
    roots: dict[str, str]
    nuclei: dict[str, str]

    @classmethod
    def load(cls, root: Path = ROOT) -> "ArabicInventory":
        roots: dict[str, str] = {}
        with (root / "computational/data/layer_2_results_v2.jsonl").open("r", encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                row = json.loads(line)
                roots[row["tri_root"]] = row.get("jabal_axial", "")
        core = json.loads((root / "data/juthoor-core-levels.json").read_text(encoding="utf-8"))
        nuclei: dict[str, str] = {}
        for row in core["levels"]["level_2_binary_nuclei"]["nuclei"]:
            key = "".join(HAMZA.get(ch, ch) for ch in row["nucleus"].replace("-", "").replace(" ", ""))
            nuclei[key] = row.get("jabal_lexicon_reading_ar") or row.get("composed_reading_ar") or ""
        return cls(roots=roots, nuclei=nuclei)


@dataclass(frozen=True)
class SlotOption:
    arabic: str
    status: str
    rule_id: str
    rule_kind: str
    path: str
    route_flag: bool


@dataclass(frozen=True)
class CandidateHit:
    kind: str
    form: str
    reading: str
    positions: str
    status: str
    rule_ids: tuple[str, ...]
    path: str
    route_flag: bool


def _rule_status(rule: ShiftRule, language: str) -> str:
    if not rule.scope_allows(language):
        return "scope-gap"
    if rule.automation != "automatic":
        return "manual-condition"
    return "licensed"


def _cross_script_options(token: str, language: str, rules: list[ShiftRule]) -> list[SlotOption]:
    options: list[SlotOption] = []
    for rule in rules:
        if rule.kind != "cross-script":
            continue
        left_ar = tuple(item for item in rule.left_tokens if item in ARABIC)
        right_ar = tuple(item for item in rule.right_tokens if item in ARABIC)
        if left_ar and token in rule.right_tokens:
            # For a one-way Arabic -> branch row, observing the branch target may
            # retrieve the Arabic source. The reverse historical claim is not made.
            for arabic in left_ar:
                options.append(SlotOption(arabic, _rule_status(rule, language), rule.row_id,
                                          rule.kind, f"{rule.row_id}: {rule.shift}", rule.requires_route_flag))
        if rule.direction == "both" and right_ar and token in rule.left_tokens:
            for arabic in right_ar:
                options.append(SlotOption(arabic, _rule_status(rule, language), rule.row_id,
                                          rule.kind, f"{rule.row_id}: {rule.shift}", rule.requires_route_flag))
    return options


def _arabic_correspondence_options(base: SlotOption, language: str, rules: list[ShiftRule]) -> list[SlotOption]:
    options: list[SlotOption] = []
    for rule in rules:
        if rule.kind != "arabic-correspondence":
            continue
        if base.arabic in rule.left_tokens:
            targets = [item for item in rule.right_tokens if item in ARABIC]
        elif rule.direction == "both" and base.arabic in rule.right_tokens:
            targets = [item for item in rule.left_tokens if item in ARABIC]
        else:
            continue
        status = _rule_status(rule, language)
        if rule.direction != "both":
            status = "manual-condition" if status == "licensed" else status
        for target in targets:
            options.append(SlotOption(target, status, rule.row_id, rule.kind, f"{rule.row_id}: {rule.shift}",
                                      rule.requires_route_flag))
    return options


def slot_options(token: str, language: str, rules: list[ShiftRule]) -> tuple[SlotOption, ...]:
    anchors = (token,) if token in ARABIC else ANCHOR_MAP.get(token, ())
    base = [SlotOption(item, "licensed", "", "anchor", f"ANCHOR:{token}", False) for item in anchors]
    options = list(base) + _cross_script_options(token, language, rules)
    for item in base:
        options.extend(_arabic_correspondence_options(item, language, rules))
    best: dict[tuple[str, str], SlotOption] = {}
    for option in options:
        key = (option.arabic, option.rule_id)
        previous = best.get(key)
        if previous is None or STATUS_RANK[option.status] < STATUS_RANK[previous.status]:
            best[key] = option
    return tuple(sorted(best.values(), key=lambda item: (STATUS_RANK[item.status], item.arabic, item.rule_id)))


def _combine(options: tuple[tuple[SlotOption, ...], ...]):
    for combo in product(*options):
        rule_ids = tuple(sorted({item.rule_id for item in combo if item.rule_id}))
        # Direct branch correspondences may occur in several slots. Preserve
        # the older generator's stricter limit only for Arabic-internal shifts:
        # at most one such shifted slot per retrieval path.
        if sum(item.rule_kind == "arabic-correspondence" for item in combo) > 1:
            continue
        status = max((item.status for item in combo), key=lambda value: STATUS_RANK[value])
        yield combo, rule_ids, status


def generate_hits(
    tokens: tuple[str, ...],
    language: str,
    rules: list[ShiftRule],
    inventory: ArabicInventory,
) -> tuple[list[CandidateHit], tuple[str, ...]]:
    slots = tuple(slot_options(token, language, rules) for token in tokens)
    unmapped = tuple(token for token, options in zip(tokens, slots) if not options)
    if unmapped:
        return [], unmapped
    hits: list[CandidateHit] = []

    def add(kind: str, form: str, reading: str, positions: str, combo, rule_ids, status):
        hits.append(CandidateHit(
            kind=kind,
            form=form,
            reading=reading,
            positions=positions,
            status=status,
            rule_ids=rule_ids,
            path=" + ".join(item.path for item in combo),
            route_flag=any(item.route_flag for item in combo),
        ))

    if len(tokens) == 3:
        for combo, rule_ids, status in _combine(slots):
            form = "".join(item.arabic for item in combo)
            if form in inventory.roots:
                add("root", form, inventory.roots[form], "1-2-3", combo, rule_ids, status)

    for left, right in combinations(range(len(tokens)), 2):
        pair_slots = (slots[left], slots[right])
        for combo, rule_ids, status in _combine(pair_slots):
            form = "".join(item.arabic for item in combo)
            if form in inventory.nuclei:
                add("nucleus", form, inventory.nuclei[form], f"{left + 1}-{right + 1}", combo, rule_ids, status)

    if len(tokens) == 2:
        for combo, rule_ids, status in _combine(slots):
            edges = [item.arabic for item in combo]
            for middle in "اوي":
                form = edges[0] + middle + edges[1]
                if form in inventory.roots:
                    add("hollow-root", form, inventory.roots[form], "1-M-2", combo, rule_ids, status)

    unique: dict[tuple[object, ...], CandidateHit] = {}
    for hit in hits:
        key = (hit.kind, hit.form, hit.positions, hit.status, hit.rule_ids)
        unique.setdefault(key, hit)
    return sorted(unique.values(), key=lambda hit: (STATUS_RANK[hit.status], hit.kind, hit.form, hit.positions)), ()
