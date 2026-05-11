"""forge.spec — Spec loading, utilities, archetype routing."""

import json
from pathlib import Path

FORGE_DIR = Path(__file__).parent.parent
SKELETON = FORGE_DIR / "templates" / "skeleton"
DSPLIB = FORGE_DIR / "dsplib" / "voices"


def load_spec(path: str) -> dict:
    with open(path) as f:
        return json.load(f)


def const_name(name: str) -> str:
    """Kick -> KICK, Bass1 -> BASS1"""
    return name.upper().replace(" ", "_")


# ── Archetype Router ─────────────────────────────────────────────────────────

ARCHETYPE_MAP = {
    "kick":    "kick.h",
    "snare":   "snare.h",
    "hats":    "hats.h",
    "tom":     "tom.h",
    "perc":    "perc.h",
    "clap":    "clap.h",
    "bass303": "bass.h",
    "pad":     "pad.h",
    "lead":    "lead.h",
    "pluck":    "pluck.h",
    "organ":    "organ.h",
    "fm_synth": "fm_synth.h",
    "noise":    "noise.h",
    "string":   "string_voice.h",
    "brass":    "brass.h",
    "sub_bass": "sub_bass.h",
}


def route_archetype(voice: dict, channel: dict) -> str | None:
    """Deterministic router: voice spec → archetype ID."""
    params = voice["params"]
    name_lower = voice["name"].lower()
    if channel["type"] == "pitched":
        if "cutoff" in params and "reso" in params:
            if "attack" in params and voice.get("decay", 0) > 1.0: return "pad"
            if "pw" in params: return "lead"
            if "envmod" in params: return "bass303"
            return "bass303"
        if "bright" in params or "body" in params: return "pluck"
        if "attack" in params: return "pad"
        if "pad" in name_lower: return "pad"
        if "lead" in name_lower: return "lead"
        if "pluck" in name_lower: return "pluck"
        if "organ" in name_lower or "drawbar" in name_lower: return "organ"
        if "fm" in name_lower or "bell" in name_lower: return "fm_synth"
        if "noise" in name_lower or "texture" in name_lower: return "noise"
        if "string" in name_lower or "ensemble" in name_lower: return "string"
        if "brass" in name_lower or "horn" in name_lower or "stab" in name_lower: return "brass"
        if "sub" in name_lower: return "sub_bass"
        if "ratio" in params or "index" in params: return "fm_synth"
        if "rotary" in params: return "organ"
        if "harmonics" in params: return "sub_bass"
        if "release" in params and "detune" in params: return "string"
        return None
    # Drum routing by name first
    if "kick" in name_lower: return "kick"
    if "snare" in name_lower: return "snare"
    if "hat" in name_lower or "hh" in name_lower or "hihat" in name_lower: return "hats"
    if "tom" in name_lower: return "tom"
    if "clap" in name_lower or "cp" in name_lower: return "clap"
    if "perc" in name_lower or "cow" in name_lower or "clave" in name_lower: return "perc"
    # Fallback by param shape
    if "punch" in params or "sub" in params: return "kick"
    if "snap" in params and "noise" in params: return "snare"
    if "tone" in params and "body" in params: return "hats"
    if "pitchenv" in params: return "tom"
    if "detune" in params and "drive" in params: return "perc"
    if "spread" in params: return "clap"
    return None
