"""Declarative Pluggable State Pack Loader & Validator for Pan-Bharat Civic Routing.

Allows Tamil Nadu (`tn`) to serve as the live verified showcase while onboarding any Indian
state (`ka`, `mh`, `up`, `in_central`, etc.) strictly via validated JSON configuration in
`state_packs/*.json` without changing core voice workflow or safety code.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

STATE_PACKS_DIR = Path(__file__).resolve().parent.parent / "state_packs"


class AmbiguousAreaSpec(BaseModel):
    trigger_pattern: str
    specific_tokens: list[str] = Field(default_factory=list)
    prompt_en: str
    prompt_ta: str | None = None


class PortalTarget(BaseModel):
    id: str
    name: str
    url: str
    helpline: str
    whatsapp: str | None = None
    email: str | None = None
    auth_gate: str


class LandmarkEntry(BaseModel):
    name: str
    district: str
    zone: str
    ward: str
    street: str
    road_id: str
    lat: float
    lon: float
    aliases: list[str] = Field(default_factory=list)
    default_service: str = "streetlight_eb"


class StatePack(BaseModel):
    state_code: str
    state_name: str
    languages: list[str]
    accents: list[str] = Field(default_factory=list)
    fallback_helpline: str
    fallback_email: str | None = None
    issue_lexicon: dict[str, list[str]]
    ambiguous_areas: dict[str, AmbiguousAreaSpec] = Field(default_factory=dict)
    portals: list[PortalTarget]
    landmarks: list[LandmarkEntry]


class StatePackRegistry:
    """Validates and indexes pluggable Bharat State Packs from disk."""

    def __init__(self, packs_dir: Path = STATE_PACKS_DIR) -> None:
        self.packs_dir = packs_dir
        self._packs: dict[str, StatePack] = {}
        self.reload()

    def reload(self) -> None:
        loaded: dict[str, StatePack] = {}
        if self.packs_dir.is_dir():
            for fp in sorted(self.packs_dir.glob("*.json")):
                raw = json.loads(fp.read_text(encoding="utf-8"))
                pack = StatePack.model_validate(raw)
                loaded[pack.state_code.lower()] = pack
        self._packs = loaded

    def list_summaries(self) -> list[dict[str, Any]]:
        return [
            {
                "state_code": p.state_code,
                "state_name": p.state_name,
                "languages": p.languages,
                "accents": p.accents,
                "portals_count": len(p.portals),
                "landmarks_count": len(p.landmarks),
                "fallback_helpline": p.fallback_helpline,
            }
            for p in self._packs.values()
        ]

    def get(self, state_code: str = "tn") -> StatePack:
        code = (state_code or "tn").lower()
        if code in self._packs:
            return self._packs[code]
        return next(iter(self._packs.values()))

    def match_landmark(self, text: str, state_code: str = "tn") -> LandmarkEntry | None:
        pack = self.get(state_code)
        low = text.lower()
        for lm in pack.landmarks:
            if any(alias.lower() in low for alias in lm.aliases):
                return lm
        return None

    def nearest_gps_landmark(self, lat: float, lon: float, state_code: str = "tn") -> tuple[LandmarkEntry, float]:
        pack = self.get(state_code)
        best_lm = pack.landmarks[0]
        best_dist = float("inf")
        for lm in pack.landmarks:
            d = (lm.lat - lat) ** 2 + (lm.lon - lon) ** 2
            if d < best_dist:
                best_dist = d
                best_lm = lm
        return best_lm, best_dist

    def check_ambiguous_area(self, text: str, state_code: str = "tn") -> tuple[str | None, AmbiguousAreaSpec | None]:
        pack = self.get(state_code)
        low = text.lower()
        for area_key, spec in pack.ambiguous_areas.items():
            if re.search(spec.trigger_pattern, low):
                has_specific = any(re.search(tok, low) for tok in spec.specific_tokens)
                if not has_specific:
                    return area_key, spec
        return None, None


REGISTRY = StatePackRegistry()
