#!/usr/bin/env python3
"""txt2vst prompt interpreter — natural language → spec.json"""

import json, re, sys
from pathlib import Path

# ── Archetype Knowledge Base ─────────────────────────────────────────────────
# Each archetype defines its default params, typical names, and channel type.

DRUM_ARCHETYPES = {
    "kick":  {"params": ["tune","decay","punch","pitchenv","drive","sub"],
              "aliases": ["kick","bd","bassdrum","bass drum"]},
    "snare": {"params": ["tune","decay","snap","noise"],
              "aliases": ["snare","sd","snaredrum"]},
    "hats":  {"params": ["decay","tone","body"],
              "aliases": ["hats","hihat","hi-hat","hh","hat","cymbal"]},
    "tom":   {"params": ["tune","decay","pitchenv","attack"],
              "aliases": ["tom","toms","lo tom","hi tom","mid tom"]},
    "perc":  {"params": ["tune","decay","detune","drive"],
              "aliases": ["perc","percussion","cowbell","clave","woodblock","rimshot","rim"]},
    "clap":  {"params": ["decay","tone","spread"],
              "aliases": ["clap","cp","handclap"]},
}

PITCHED_ARCHETYPES = {
    "bass303": {"params": ["cutoff","reso","envmod","decay","accent"],
                "aliases": ["bass","acid","303","bassline","acid bass"]},
    "lead":    {"params": ["cutoff","reso","pw","decay","envmod"],
                "aliases": ["lead","synth lead","mono lead","solo"]},
    "pad":     {"params": ["cutoff","reso","attack","decay","detune"],
                "aliases": ["pad","ambient","chord","string","strings","atmosphere"]},
    "pluck":   {"params": ["decay","bright","body"],
                "aliases": ["pluck","guitar","pizz","pizzicato","kalimba","marimba"]},
    "organ":   {"params": ["decay","rotary"],
                "aliases": ["organ","drawbar","hammond","keys","keyboard"]},
    "fm_synth":{"params": ["ratio","index","decay","feedback"],
                "aliases": ["fm","fm synth","dx7","metallic","bell","bells"]},
    "noise":   {"params": ["cutoff","reso","decay","color"],
                "aliases": ["noise","texture","riser","wind","ocean","ambient noise"]},
    "string":  {"params": ["cutoff","reso","attack","release","detune"],
                "aliases": ["string","strings","ensemble","violin","cello","orchestral"]},
    "brass":   {"params": ["cutoff","reso","attack","decay","bright"],
                "aliases": ["brass","horn","trumpet","stab","stabs","trombone"]},
    "sub_bass":{"params": ["decay","sub","harmonics","drive"],
                "aliases": ["sub","sub bass","subbass","808","808 bass","rumble"]},
}

FX_ARCHETYPES = {
    "delay":      {"params": ["time","feedback","mix","tone"],
                   "aliases": ["delay","echo","ping-pong","pingpong"]},
    "reverb":     {"params": ["decay","damping","mix","predelay"],
                   "aliases": ["reverb","verb","room","hall","plate"]},
    "chorus":     {"params": ["rate","depth","mix"],
                   "aliases": ["chorus","ensemble","detune"]},
    "compressor": {"params": ["threshold","ratio","attack","release","makeup"],
                   "aliases": ["compressor","comp","limiter","squash"]},
    "distortion": {"params": ["drive","tone","mix"],
                   "aliases": ["distortion","dist","overdrive","fuzz","saturation"]},
    "phaser":     {"params": ["rate","depth","feedback","mix"],
                   "aliases": ["phaser","phase","jet","sweep"]},
    "eq":         {"params": ["low","mid","mid_freq","high"],
                   "aliases": ["eq","equalizer","tone control"]},
    "gate":       {"params": ["threshold","attack","hold","release"],
                   "aliases": ["gate","noise gate","expander"]},
}

ALL_ARCHETYPES = {**DRUM_ARCHETYPES, **PITCHED_ARCHETYPES}

# ── Parser ───────────────────────────────────────────────────────────────────

def parse_prompt(text: str) -> dict:
    """Parse a natural language prompt into a spec.json-compatible dict."""
    text_lower = text.lower().strip()

    # Extract plugin name (look for quoted names or generate from description)
    name_match = re.search(r'"([^"]+)"', text)
    if name_match:
        plugin_name = name_match.group(1).replace(" ", "")
    else:
        # Generate name from key words
        words = [re.sub(r'[^a-z0-9]', '', w) for w in text_lower.split() if len(w) > 3 and w not in
                 {"with","from","that","this","have","want","make","build","create",
                  "drum","machine","synth","instrument","channel","channels","canali","canale"}]
        words = [w for w in words if w]  # remove empties
        plugin_name = "".join(w.capitalize() for w in words[:2]) or "MyPlugin"

    # Detect number of channels
    ch_match = re.search(r'(\d+)\s*(?:ch|chan|channel|canali|voci|voices|instruments)', text_lower)
    target_channels = int(ch_match.group(1)) if ch_match else None

    # Detect which archetypes are mentioned
    detected_drums = []
    detected_pitched = []

    for arch_id, info in DRUM_ARCHETYPES.items():
        for alias in info["aliases"]:
            if alias in text_lower:
                detected_drums.append(arch_id)
                break

    for arch_id, info in PITCHED_ARCHETYPES.items():
        for alias in info["aliases"]:
            if alias in text_lower:
                detected_pitched.append(arch_id)
                break

    # If nothing detected, infer from keywords
    if not detected_drums and not detected_pitched:
        if any(w in text_lower for w in ["drum", "beat", "rhythm", "groove", "groovebox"]):
            detected_drums = ["kick", "snare", "hats", "clap"]
        elif any(w in text_lower for w in ["synth", "synthesizer", "keys"]):
            detected_pitched = ["bass303", "lead", "pad"]
        else:
            detected_drums = ["kick", "snare", "hats"]
            detected_pitched = ["bass303"]

    # Adjust to target channel count if specified
    all_voices = detected_drums + detected_pitched
    if target_channels:
        while len(all_voices) < target_channels:
            # Fill with common extras
            extras = ["tom", "perc", "clap", "pad", "lead", "pluck"]
            for e in extras:
                if e not in all_voices and len(all_voices) < target_channels:
                    all_voices.append(e)
            if len(all_voices) < target_channels:
                break
        all_voices = all_voices[:target_channels]
        detected_drums = [v for v in all_voices if v in DRUM_ARCHETYPES]
        detected_pitched = [v for v in all_voices if v in PITCHED_ARCHETYPES]

    # Detect features
    has_sequencer = any(w in text_lower for w in ["sequencer","step","pattern","groovebox","drum machine"])
    has_swing = any(w in text_lower for w in ["swing","shuffle","groove"])
    has_sidechain = any(w in text_lower for w in ["sidechain","ducker","pump"])

    # Detect FX
    detected_fx = []
    for fx_id, info in FX_ARCHETYPES.items():
        for alias in info["aliases"]:
            if alias in text_lower:
                detected_fx.append(fx_id)
                break

    # Detect theme
    theme = "midnight"  # default
    for t in ["acid","ember","frost","neon","vapor","industrial","solar","midnight"]:
        if t in text_lower:
            theme = t
            break

    # Detect mastering preset
    mastering = None
    mastering_aliases = {
        "punch":       ["punch", "punchy", "hard", "aggressive", "smack"],
        "wet":         ["wet", "lush", "atmospheric", "spacey", "ambient"],
        "radio":       ["radio", "lo-fi", "lofi", "telephone", "lo fi"],
        "distorted":   ["distorted", "dirty", "gritty", "crushed", "saturated"],
        "wide":        ["wide", "stereo", "spatial", "3d", "immersive"],
        "transparent": ["transparent", "clean master", "mastered", "mastering", "glue", "polished"],
    }
    for preset, aliases in mastering_aliases.items():
        for alias in aliases:
            if alias in text_lower:
                mastering = preset
                break
        if mastering:
            break

    # Build spec
    channels = []
    voices = []
    midi_note = 36  # Start at C2 for drums

    for arch_id in detected_drums:
        info = DRUM_ARCHETYPES[arch_id]
        ch_name = arch_id.capitalize()
        channels.append({"name": ch_name, "type": "drum", "midi": midi_note})
        voices.append({"name": ch_name, "params": info["params"]})
        midi_note += 1

    midi_ch = 2  # MIDI channel for pitched voices
    for arch_id in detected_pitched:
        info = PITCHED_ARCHETYPES[arch_id]
        ch_name = arch_id.capitalize() if arch_id != "bass303" else "Acid"
        channels.append({"name": ch_name, "type": "pitched", "midi_ch": midi_ch})
        voices.append({"name": ch_name, "params": info["params"]})
        midi_ch += 1

    # Generate 4-char codes
    prefix = plugin_name[:3].upper() if len(plugin_name) >= 3 else "PLG"
    code = (plugin_name[:4].capitalize() if len(plugin_name) >= 4 else "Plgn")

    features = {
        "sequencer": has_sequencer or len(detected_drums) > 0,
        "swing": has_swing,
        "sidechain": has_sidechain,
        "master_fx": detected_fx if detected_fx else (["drive"] if len(all_voices) > 2 else [])
    }
    if mastering:
        features["mastering"] = mastering

    spec = {
        "plugin": {
            "name": plugin_name,
            "version": "0.1.0",
            "company": "txt2vst",
            "prefix": prefix,
            "mfr_code": "Tx2v",
            "code": code,
            "ui": [1031, 625]
        },
        "channels": channels,
        "voices": voices,
        "features": features
    }

    if theme != "midnight":
        spec["plugin"]["theme"] = theme

    return spec


def prompt_to_spec(prompt: str, output_path: str | None = None) -> dict:
    """Main entry: prompt → spec dict (+ optional file output)."""
    spec = parse_prompt(prompt)

    if output_path:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(spec, f, indent=2)

    return spec


def main():
    if len(sys.argv) < 2:
        print("Usage: python prompt2spec.py <prompt> [output.spec.json]")
        print('Example: python prompt2spec.py "drum machine acid 4 canali"')
        sys.exit(1)

    prompt = sys.argv[1]
    output = sys.argv[2] if len(sys.argv) > 2 else None

    spec = prompt_to_spec(prompt, output)
    print(json.dumps(spec, indent=2))

    # Summary
    drums = [c for c in spec["channels"] if c["type"] == "drum"]
    pitched = [c for c in spec["channels"] if c["type"] == "pitched"]
    print(f"\n🎯 {spec['plugin']['name']}: {len(drums)} drums + {len(pitched)} pitched = {len(spec['channels'])} channels")
    print(f"   Features: seq={spec['features']['sequencer']} swing={spec['features']['swing']} sc={spec['features']['sidechain']}")


if __name__ == "__main__":
    main()
