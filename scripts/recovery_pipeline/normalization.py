from __future__ import annotations

import json
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any


PROFILE_DIR = Path(__file__).resolve().parents[2] / "04-cross-linguistic" / "normalization-profiles"


@dataclass(frozen=True)
class NormalizedForm:
    source: str
    folded: str
    tokens: tuple[str, ...]
    unknown: tuple[str, ...]
    ambiguities: tuple[str, ...]
    ignored_diacritics: tuple[str, ...]

    @property
    def skeleton(self) -> str:
        return "-".join(self.tokens)

    @property
    def ok(self) -> bool:
        return bool(self.tokens) and not self.unknown


def load_profile(language: str, profile_dir: Path = PROFILE_DIR) -> dict[str, Any]:
    path = profile_dir / f"{language}.json"
    if not path.exists():
        raise FileNotFoundError(f"No normalization profile for {language}: {path}")
    profile = json.loads(path.read_text(encoding="utf-8"))
    if profile.get("language") != language:
        raise ValueError(f"Profile language mismatch in {path}")
    return profile


def available_profiles(profile_dir: Path = PROFILE_DIR) -> list[str]:
    return sorted(p.stem for p in profile_dir.glob("*.json"))


def detect_language(text: str) -> str:
    characters = set(unicodedata.normalize("NFC", text or "").lower())
    for language in ("coptic", "ancient_greek", "egyptian"):
        if characters.intersection(load_profile(language).get("script_map", {})):
            return language
    return "generic"


def _fold(text: str, profile: dict[str, Any]) -> tuple[str, tuple[str, ...]]:
    script_map = profile.get("script_map", {})
    combining_map = profile.get("combining_map", {})
    folded: list[str] = []
    ignored: list[str] = []
    for ch in unicodedata.normalize("NFD", unicodedata.normalize("NFC", text).lower()):
        if unicodedata.combining(ch):
            mapped = combining_map.get(f"{ord(ch):04X}")
            if mapped is not None:
                folded.append(mapped)
            else:
                ignored.append(f"U+{ord(ch):04X}")
            continue
        folded.append(script_map.get(ch, ch))
    return unicodedata.normalize("NFC", "".join(folded)), tuple(sorted(set(ignored)))


def normalize(text: str, profile: dict[str, Any], *, strict: bool = True) -> NormalizedForm:
    folded, ignored_diacritics = _fold(text or "", profile)
    vowels = set(profile.get("vowels", []))
    ignored = set(profile.get("ignored_characters", []))
    multi = {key: tuple(value) for key, value in profile.get("multi_tokens", {}).items()}
    singles = set(profile.get("single_tokens", []))
    ordered_multi = sorted(multi, key=len, reverse=True)
    ambiguity_map = profile.get("ambiguous_sequences", {})
    ambiguities = tuple(
        f"{sequence}: {note}" for sequence, note in ambiguity_map.items() if sequence in text or sequence in folded
    )

    tokens: list[str] = []
    unknown: list[str] = []
    index = 0
    while index < len(folded):
        ch = folded[index]
        if ch in ignored or ch.isspace():
            index += 1
            continue
        matched = next((item for item in ordered_multi if folded.startswith(item, index)), None)
        if matched is not None:
            tokens.extend(multi[matched])
            index += len(matched)
            continue
        if ch in vowels:
            index += 1
            continue
        if ch in singles:
            tokens.append(ch)
            index += 1
            continue
        unknown.append(f"{ch} (U+{ord(ch):04X})")
        index += 1

    result = NormalizedForm(
        source=text or "",
        folded=folded,
        tokens=tuple(tokens),
        unknown=tuple(unknown),
        ambiguities=ambiguities,
        ignored_diacritics=ignored_diacritics,
    )
    if strict and result.unknown:
        raise ValueError(f"Unknown symbols for {profile['language']}: {', '.join(result.unknown)}")
    return result


def select_form(
    original: str,
    romanization: str,
    profile: dict[str, Any],
    *,
    strict: bool = True,
) -> tuple[NormalizedForm, NormalizedForm, NormalizedForm, str]:
    original_form = normalize(original, profile, strict=False)
    romanized_form = normalize(romanization, profile, strict=False) if romanization else NormalizedForm(
        source="", folded="", tokens=(), unknown=(), ambiguities=(), ignored_diacritics=()
    )
    choices = {"original": original_form, "romanization": romanized_form}
    selected_name = ""
    selected = original_form
    for name in profile.get("preferred_input", ["romanization", "original"]):
        candidate = choices.get(name)
        if candidate and candidate.ok:
            selected_name, selected = name, candidate
            break
    if not selected_name:
        clean_name = next((name for name in profile.get("preferred_input", []) if choices.get(name) and not choices[name].unknown), "")
        selected_name = clean_name or ("romanization" if romanization else "original")
        selected = choices[selected_name]
    if strict and (not selected.tokens or selected.unknown):
        reason = ", ".join(selected.unknown) if selected.unknown else "empty consonant skeleton"
        raise ValueError(f"Normalization failed for {profile['language']} {selected.source!r}: {reason}")
    return original_form, romanized_form, selected, selected_name
