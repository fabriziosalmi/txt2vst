"""forge.spec — Spec loading, utilities, archetype routing."""

import json, re
from pathlib import Path

FORGE_DIR = Path(__file__).parent.parent
SKELETON = FORGE_DIR / "templates" / "skeleton"
DSPLIB = FORGE_DIR / "dsplib" / "voices"


def load_spec(path: str) -> dict:
    with open(path) as f:
        spec = json.load(f)
    for key in ("plugin", "channels", "voices", "features"):
        if key not in spec:
            raise ValueError(f"spec.json missing required key: '{key}'")
    if not spec["channels"]:
        raise ValueError("spec.json has empty 'channels'")
    return spec


def const_name(name: str) -> str:
    """Kick -> KICK, FM-Synth -> FM_SYNTH, Bass1 -> BASS1"""
    return re.sub(r'[^A-Z0-9]', '_', name.upper()).strip('_')


# ── Archetype Router ─────────────────────────────────────────────────────────

ARCHETYPE_MAP = {
    "kick":      {"file": "kick.h",         "class": "KickVoice"},
    "snare":     {"file": "snare.h",        "class": "SnareVoice"},
    "hats":      {"file": "hats.h",         "class": "HatsVoice"},
    "tom":       {"file": "tom.h",          "class": "TomVoice"},
    "perc":      {"file": "perc.h",         "class": "PercVoice"},
    "clap":      {"file": "clap.h",         "class": "ClapVoice"},
    "bass_acid": {"file": "bass.h",         "class": "BassVoice"},
    "pad":       {"file": "pad.h",          "class": "PadVoice"},
    "lead":      {"file": "lead.h",         "class": "LeadVoice"},
    "pluck":     {"file": "pluck.h",        "class": "PluckVoice"},
    "organ":     {"file": "organ.h",        "class": "OrganVoice"},
    "fm_synth":  {"file": "fm_synth.h",     "class": "FMSynthVoice"},
    "noise":     {"file": "noise.h",        "class": "NoiseVoice"},
    "string":    {"file": "string_voice.h", "class": "StringVoice"},
    "brass":     {"file": "brass.h",        "class": "BrassVoice"},
    "sub_bass":  {"file": "sub_bass.h",     "class": "SubBassVoice"},
}


def route_archetype(voice: dict, channel: dict) -> str | None:
    """Deterministic router: voice spec → archetype ID."""
    params = voice["params"]
    name_lower = voice["name"].lower()
    if channel["type"] == "pitched":
        if "cutoff" in params and "reso" in params:
            if "attack" in params and "release" in params: return "pad"
            if "pw" in params: return "lead"
            if "envmod" in params: return "bass_acid"
            return "bass_acid"
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
