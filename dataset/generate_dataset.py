#!/usr/bin/env python3
"""Generate synthetic prompt→spec.json pairs for model training.

Produces a JSONL file where each line is:
  {"prompt": "...", "completion": "{...spec json...}"}

Usage:
  python3 dataset/generate_dataset.py --count 10000 --output dataset/train.jsonl
"""

import json, random, argparse, itertools
from pathlib import Path

# ── Knowledge Base (mirrors prompt2spec.py) ───────────────────────────────────

DRUMS = {
    "kick":  ["kick", "bassdrum", "bass drum", "bd"],
    "snare": ["snare", "sd", "snaredrum"],
    "hats":  ["hats", "hihat", "hi-hat", "hh", "cymbal"],
    "tom":   ["tom", "toms"],
    "perc":  ["perc", "percussion", "cowbell", "rimshot"],
    "clap":  ["clap", "handclap", "cp"],
}

PITCHED = {
    "bass_acid": ["bass", "acid", "acid bass", "bassline"],
    "lead":      ["lead", "synth lead", "mono lead", "solo"],
    "pad":       ["pad", "ambient", "chord pad", "atmosphere"],
    "pluck":     ["pluck", "guitar", "kalimba", "marimba"],
    "organ":     ["organ", "keys", "keyboard", "hammond"],
    "fm_synth":  ["FM synth", "bell", "metallic", "DX-style"],
    "noise":     ["noise", "texture", "riser", "wind"],
    "string":    ["string ensemble", "violin", "cello", "orchestral"],
    "brass":     ["brass", "horn", "trumpet", "stab"],
    "sub_bass":  ["sub bass", "808", "rumble", "deep bass"],
}

DRUM_PARAMS = {
    "kick":  ["tune","decay","punch","pitchenv","drive","sub"],
    "snare": ["tune","decay","snap","noise"],
    "hats":  ["decay","tone","body"],
    "tom":   ["tune","decay","pitchenv","attack"],
    "perc":  ["tune","decay","detune","drive"],
    "clap":  ["decay","tone","spread"],
}

PITCHED_PARAMS = {
    "bass_acid": ["cutoff","reso","envmod","decay","accent"],
    "lead":      ["cutoff","reso","pw","decay","envmod"],
    "pad":       ["cutoff","reso","attack","decay","detune"],
    "pluck":     ["decay","bright","body"],
    "organ":     ["decay","rotary"],
    "fm_synth":  ["ratio","index","decay","feedback"],
    "noise":     ["cutoff","reso","decay","color"],
    "string":    ["cutoff","reso","attack","release","detune"],
    "brass":     ["cutoff","reso","attack","decay","bright"],
    "sub_bass":  ["decay","sub","harmonics","drive"],
}

FX_LIST = ["delay", "reverb", "chorus", "compressor", "distortion", "phaser", "eq", "gate"]
FX_ALIASES = {
    "delay": ["delay", "echo", "ping-pong"],
    "reverb": ["reverb", "hall", "room", "plate reverb"],
    "chorus": ["chorus", "ensemble"],
    "compressor": ["compressor", "comp", "limiter"],
    "distortion": ["distortion", "overdrive", "fuzz", "saturation"],
    "phaser": ["phaser", "jet sweep"],
    "eq": ["EQ", "equalizer", "tone shaping"],
    "gate": ["gate", "noise gate", "expander"],
}

THEMES = ["midnight","void","obsidian","acid","neon","glow","strobe","matrix",
          "ember","solar","copper","candy","frost","chrome","arctic",
          "vapor","industrial","terminal","hologram","white","cream","blood","lavender"]

MASTERS = ["transparent","punch","wet","radio","distorted","wide"]

MASTER_ALIASES = {
    "transparent": ["transparent", "clean master", "polished", "mastered"],
    "punch":       ["punchy", "hard", "aggressive", "smack", "transient"],
    "wet":         ["wet", "lush", "spacey", "atmospheric"],
    "radio":       ["radio", "lo-fi", "lofi", "telephone", "vintage"],
    "distorted":   ["distorted", "dirty", "gritty", "crushed"],
    "wide":        ["wide", "stereo", "spatial", "3D", "immersive"],
}

# ── Prompt Templates ──────────────────────────────────────────────────────────

TEMPLATES = [
    # Simple
    "{name} with {voices}",
    "{voices} {ch_count} channel {genre}",
    "make me a {genre} plugin called {name} with {voices}",
    "I want a {genre} instrument: {voices}",
    # Detailed
    "{name} — {voices} with {fx} and {theme} theme",
    "build a {ch_count}-channel {genre} synth named {name} with {voices}, {fx}",
    "create {name}: {voices}, add {fx}, use {theme} colors",
    # Character
    "{genre} groovebox with {voices}, {master} mastering",
    "a {master} {genre} machine: {voices} + {fx}",
    "{name} — {ch_count} voices ({voices}), {fx}, {theme} UI, {master} master",
    # Terse
    "{voices} {fx} {theme}",
    "{name} {voices} {master}",
    # Natural
    "I need a {genre} plugin with {voices} and some {fx}",
    "looking for a {master} {genre} instrument with {voices}",
    "can you make a {genre} VST with {voices}? I want {fx} and {theme} look",
    "give me {voices} in a {theme} themed plugin called {name}",
]

GENRES = [
    "drum machine", "synth", "groovebox", "instrument", "beatmaker",
    "synthesizer", "music box", "sound generator", "VST", "plugin",
    "electronic", "techno", "house", "ambient", "industrial",
]

PLUGIN_NAMES = [
    "AcidBox", "NeuroSynth", "VoidDrum", "SubStation", "OrbitPad",
    "CrushLab", "NeonPulse", "FrostBite", "GlitchKit", "SolarWave",
    "BrassHammer", "HazeEngine", "DeepRoot", "QuantumBeat", "CrystalFM",
    "DustKick", "TubeForge", "MoonBass", "RiftSynth", "PulseBox",
    "NovaKit", "ThunderBeat", "ZenPad", "IronForge", "CosmicDrum",
    "SilkPad", "RazorLead", "VelvetKeys", "StormBox", "EchoCell",
    "PhantomSynth", "BlitzDrum", "OceanPad", "FireBell", "ShadowBass",
]


def random_voice_set():
    """Pick a random mix of drums + pitched voices."""
    n_drums = random.choice([0, 0, 1, 2, 3, 4])
    n_pitched = random.choice([0, 1, 1, 2, 2, 3])
    if n_drums == 0 and n_pitched == 0:
        n_pitched = 1
    drums = random.sample(list(DRUMS.keys()), min(n_drums, len(DRUMS)))
    pitched = random.sample(list(PITCHED.keys()), min(n_pitched, len(PITCHED)))
    return drums, pitched


def voices_to_text(drums, pitched):
    """Convert voice IDs to natural language."""
    parts = []
    for d in drums:
        parts.append(random.choice(DRUMS[d]))
    for p in pitched:
        parts.append(random.choice(PITCHED[p]))
    random.shuffle(parts)
    if len(parts) <= 3:
        return ", ".join(parts)
    else:
        return ", ".join(parts[:-1]) + " and " + parts[-1]


def random_fx():
    """Pick 0-4 random FX."""
    n = random.choice([0, 0, 1, 1, 2, 2, 3])
    return random.sample(FX_LIST, min(n, len(FX_LIST)))


def fx_to_text(fxs):
    """Convert FX IDs to natural language."""
    parts = [random.choice(FX_ALIASES[f]) for f in fxs]
    if not parts:
        return ""
    return ", ".join(parts)


def build_spec(name, drums, pitched, fxs, theme, master):
    """Build spec.json from components."""
    channels = []
    voices = []
    midi_note = 36
    midi_ch = 2

    for d in drums:
        ch_name = d.capitalize()
        channels.append({"name": ch_name, "type": "drum", "midi": midi_note})
        voices.append({"name": ch_name, "params": DRUM_PARAMS[d]})
        midi_note += 1

    for p in pitched:
        ch_name = p.replace("_", "").capitalize()
        if p == "bass_acid":
            ch_name = "Acid"
        elif p == "fm_synth":
            ch_name = "FmSynth"
        elif p == "sub_bass":
            ch_name = "SubBass"
        channels.append({"name": ch_name, "type": "pitched", "midi_ch": midi_ch})
        voices.append({"name": ch_name, "params": PITCHED_PARAMS[p]})
        midi_ch += 1

    prefix = name[:3].upper() if len(name) >= 3 else "PLG"
    code = name[:4] if len(name) >= 4 else "Plgn"

    features = {
        "sequencer": len(drums) > 0,
        "swing": False,
        "sidechain": False,
        "master_fx": fxs if fxs else []
    }
    if master:
        features["mastering"] = master

    spec = {
        "plugin": {
            "name": name,
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


def generate_sample():
    """Generate one (prompt, spec) pair."""
    name = random.choice(PLUGIN_NAMES)
    drums, pitched = random_voice_set()
    fxs = random_fx()
    theme = random.choice(THEMES)
    master = random.choice([None, None] + MASTERS)  # 25% chance of no master

    # Build prompt
    template = random.choice(TEMPLATES)
    voice_text = voices_to_text(drums, pitched)
    fx_text = fx_to_text(fxs)
    master_text = random.choice(MASTER_ALIASES.get(master, [""])) if master else ""
    genre = random.choice(GENRES)

    prompt = template.format(
        name=name,
        voices=voice_text,
        fx=fx_text if fx_text else "no effects",
        theme=theme,
        master=master_text if master_text else "clean",
        ch_count=len(drums) + len(pitched),
        genre=genre,
    )

    # Build spec
    spec = build_spec(name, drums, pitched, fxs, theme, master)

    return prompt.strip(), spec


def main():
    parser = argparse.ArgumentParser(description="Generate txt2vst training dataset")
    parser.add_argument("--count", type=int, default=10000, help="Number of samples")
    parser.add_argument("--output", type=str, default="dataset/train.jsonl", help="Output JSONL file")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    args = parser.parse_args()

    random.seed(args.seed)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)

    seen = set()
    samples = []
    attempts = 0

    while len(samples) < args.count and attempts < args.count * 5:
        attempts += 1
        prompt, spec = generate_sample()
        key = prompt.lower()
        if key in seen:
            continue
        seen.add(key)
        samples.append({
            "prompt": prompt,
            "completion": json.dumps(spec, separators=(",", ":"))
        })

    with open(out, "w") as f:
        for s in samples:
            f.write(json.dumps(s) + "\n")

    print(f"Generated {len(samples)} samples -> {out}")
    print(f"  Unique prompts: {len(seen)}")
    print(f"  File size: {out.stat().st_size / 1024:.0f} KB")


if __name__ == "__main__":
    main()
