<div align="center">

# txt2vst

### Text to VST in One Command

*Generate VST3/AU instruments from natural language. 2.7B+ unique combinations.*

[![DSP Tests](https://img.shields.io/badge/Occam_tests-46%2F46-brightgreen?style=for-the-badge)](https://github.com/fabriziosalmi/txt2vst)
[![Archetypes](https://img.shields.io/badge/archetypes-16+8-blue?style=for-the-badge)](https://github.com/fabriziosalmi/txt2vst)
[![Themes](https://img.shields.io/badge/themes-23-purple?style=for-the-badge)](https://github.com/fabriziosalmi/txt2vst)
[![License](https://img.shields.io/badge/license-MIT-orange?style=for-the-badge)](LICENSE)

[**Website**](https://txt2vst.com) · [**HuggingFace Space**](https://huggingface.co/spaces/fabriziosalmi/txt2vst) · [**Dataset**](https://huggingface.co/datasets/fabriziosalmi/txt2vst)

</div>

---

## Quick Start

### Option A: Web (no install)

**[huggingface.co/spaces/fabriziosalmi/txt2vst](https://huggingface.co/spaces/fabriziosalmi/txt2vst)** — describe your plugin, download the project ZIP, build.

### Option B: CLI

```bash
# Natural language → spec → build
python3 prompt2spec.py "drum machine with kick snare hats and acid bass, neon theme, punchy mastering" my_plugin.spec.json
python3 forge.py my_plugin.spec.json output/MyPlugin
cd output/MyPlugin && cmake -B build && cmake --build build
# → MyPlugin.vst3 installed to ~/Library/Audio/Plug-Ins/VST3/
```

### Option C: One-click (from downloaded ZIP)

```bash
chmod +x build.sh && ./build.sh
# → Clones engine, generates source, builds, installs. Done.
```

---

## Architecture

```
 ┌─────────────┐     ┌─────────────┐     ┌──────────────┐     ┌──────────┐
 │  "acid drum  │────▶│ prompt2spec │────▶│   forge.py   │────▶│  VST3/AU │
 │   machine"  │     │  (NLP → JSON)│     │ (JSON → C++) │     │  plugin  │
 └─────────────┘     └─────────────┘     └──────────────┘     └──────────┘
                                                │
                                     ┌──────────┴──────────┐
                                     │   Archetype Router   │
                                     │  (deterministic DSP  │
                                     │   layer selection)   │
                                     └──────────┬──────────┘
                                                │
              ┌──────────────────────────────────┴──────────────────────────────┐
        PERCUSSIVE (6)                                             PITCHED (10)
        ──────────                                                 ──────────
        kick   → pitch sweep + sub                    bass_acid → ladder filter
        snare  → body + noise                         lead      → SVF + PWM
        hats   → ring mod metallic                    pad       → detuned saws
        tom    → pitched body                         pluck     → Karplus-Strong
        perc   → FM synthesis                         organ     → additive drawbar
        clap   → multi-burst noise                    fm_synth  → 2-op FM
                                                      noise     → filtered noise
                                                      string    → ensemble detune
                                                      brass     → resonant saw
                                                      sub_bass  → sine + harmonics
```

## 16 Voice Archetypes

| Archetype | Engine | Guardrails |
|-----------|--------|------------|
| **Kick** | Dual envelope + pitch sweep + sub + HP click + drive | Peak < 1.3, anti-click ramp |
| **Snare** | Body tone + bandpass noise + snap transient | BP filter clamp ±2.0 |
| **Hats** | 6-osc ring modulation + noise blend | HP filtered, no mud |
| **Tom** | Pitched sine + exponential pitch sweep | — |
| **Perc** | FM carrier/modulator + index envelope | Carrier freq clamped |
| **Clap** | 4 micro-bursts + diffuse tail + bandpass | Output clamp ±1.5 |
| **Bass Acid** | PolyBLEP + 4-pole diode ladder + DC blocker | Cutoff < sr×0.45, reso < 0.98 |
| **Lead** | PolyBLEP pulse/PWM + SVF + portamento | SVF f-coeff < 0.9, tanh output |
| **Pad** | Detuned saws + sub + LP filter + ADSR | Cutoff clamped, steep decay |
| **Pluck** | Karplus-Strong physical model + damping | Feedback < 0.990 |
| **Organ** | Additive drawbar + rotary | Harmonic clamp |
| **FM Synth** | 2-operator FM + feedback | Index clamped |
| **Noise** | Filtered noise + color | Resonance limit |
| **String** | Ensemble detune + LP | Detuned saw clamp |
| **Brass** | Resonant saw + transient | Attack clamp |
| **Sub Bass** | Sine + harmonics + drive | Sub level limit |

## 8 FX Processors

| FX | Engine |
|----|--------|
| **Delay** | Ping-pong, tempo-sync |
| **Reverb** | Schroeder reverb + damping |
| **Chorus** | Stereo LFO modulation |
| **Compressor** | RMS detector + gain reduction |
| **Distortion** | Waveshaper + tone control |
| **Phaser** | All-pass cascade + LFO |
| **EQ** | 3-band parametric |
| **Gate** | Noise gate + expander |

## 7 Mastering Presets

Selectable per-plugin mastering chain on the output bus:

| Preset | Character |
|--------|-----------|
| **Bypass** | Clean passthrough |
| **Transparent** | Gentle limiter, wide headroom |
| **Punch** | Transient emphasis, fast attack |
| **Wet** | Lush spatial, subtle verb |
| **Radio** | Lo-fi, band-limited |
| **Distorted** | Warm saturation, grit |
| **Wide** | Stereo widening above 300Hz |

## 23 UI Themes

Each generates a unique JUCE `LookAndFeel` — purely CSS-driven, zero DSP impact:

| Category | Themes |
|----------|--------|
| **Dark** | midnight, void, obsidian |
| **Neon** | acid, neon, glow, strobe, matrix |
| **Warm** | ember, solar, copper, candy |
| **Cold** | frost, chrome, arctic |
| **Retro** | vapor, industrial, terminal, hologram |
| **Bright** | white, cream, blood, lavender |

## Occam Guardrails

Every archetype passes a **6-point quality gate** at default and extreme parameter values:

| # | Guardrail | Threshold | Purpose |
|---|-----------|-----------|---------|
| 1 | No NaN | 0 occurrences | Numerical stability |
| 2 | No Inf | 0 occurrences | Filter stability |
| 3 | Peak amplitude | < 1.5 | Headroom before clipping |
| 4 | DC offset | < 0.01 | No speaker damage |
| 5 | CPU usage | < 5% per voice | Real-time safety |
| 6 | Deactivation | Must stop | No infinite tails |

```bash
cd dsplib && clang++ -std=c++17 -O2 -I . -o test_voices tests/test_voices.cpp && ./test_voices
# → 46/46 passed
```

## Combinatorial Space

| Metric | Count |
|--------|-------|
| Voice archetypes | 16 (6 drum + 10 pitched) |
| FX processors | 8 |
| UI themes | 23 |
| Mastering presets | 7 |
| **Sonically unique** | **117M+** |
| **Visually distinct** | **2.7B+** |

## Project Structure

```
txt2vst/
├── forge.py              # Main CLI: spec.json → JUCE project
├── prompt2spec.py        # NLP parser: text → spec.json
├── app.py                # HuggingFace Space (Gradio)
├── forge/                # Generator modules
│   ├── spec.py           # Archetype routing
│   ├── themes.py         # 23 UI theme definitions
│   ├── gen_cmake.py      # CMakeLists (FetchContent for JUCE)
│   ├── gen_core.py       # Bus layout, params, voice bank
│   ├── gen_audio.py      # Processor, sequencer, transport
│   └── gen_ui.py         # Editor, StepGrid, ParamPanel
├── dsplib/               # Production DSP implementations
│   ├── voices/           # 16 voice archetypes (C++ headers)
│   ├── fx/               # FX + mastering chain
│   └── tests/            # 46-test Occam guardrail suite
├── dataset/              # HuggingFace dataset (10K samples)
├── site/                 # Astro website (txt2vst.com)
└── templates/            # Spec examples + JUCE skeleton
```

## Requirements

- Python 3.10+
- CMake 3.22+
- C++17 compiler (Xcode/Clang on macOS, GCC 11+ on Linux)
- JUCE 8 (auto-fetched by CMake via FetchContent)

---

<div align="center">

**Made by** [fabriziosalmi](https://github.com/fabriziosalmi)

*From text to sound — no friction, no limits.*

</div>
