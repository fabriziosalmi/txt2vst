<div align="center">

# 🎹 txt2vst

### Text → VST in One Command

*Generate production-grade VST3/AU instruments from natural language.*

[![DSP Tests](https://img.shields.io/badge/DSP_tests-20%2F20-brightgreen?style=for-the-badge)](https://github.com/fabriziosalmi/txt2vst)
[![Archetypes](https://img.shields.io/badge/archetypes-10-blue?style=for-the-badge)](https://github.com/fabriziosalmi/txt2vst)
[![License](https://img.shields.io/badge/license-MIT-orange?style=for-the-badge)](LICENSE)

</div>

---

## ⚡ Quick Start

```bash
# From text to VST3 in 3 commands:
python3 prompt2spec.py "drum machine acid 4 channels" output/acid.spec.json
python3 forge.py output/acid.spec.json output/AcidBox
cd output/AcidBox && cmake -B build && cmake --build build
# → AcidBox.vst3 installed to ~/Library/Audio/Plug-Ins/VST3/
```

Or go full control with a JSON spec:

```bash
python3 forge.py templates/acidstation.spec.json output/AcidStation
```

---

## 🏗️ Architecture

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
                        ┌──────────────────────┬┴┬──────────────────────┐
                  PERCUSSIVE                   │  │              PITCHED
                  ──────────                   │  │              ───────
                  kick   → pitch sweep+sub     │  │   bass303 → ladder filter
                  snare  → body+noise          │  │   lead    → SVF+PWM
                  hats   → ring mod metallic   │  │   pad     → detuned saws
                  tom    → pitched body        │  │   pluck   → Karplus-Strong
                  perc   → FM synthesis        │  │
                  clap   → multi-burst noise   │  │
```

## 🎛️ 10 DSP Archetypes

Every voice is a **specialized vertical layer** with production-grade DSP, routed deterministically from the spec.

| Archetype | Engine | CPU/sample | Guardrails |
|-----------|--------|-----------|------------|
| **Kick** | Dual envelope + pitch sweep + sub + HP click + drive | 16ns (0.07%) | Peak < 1.3, anti-click ramp |
| **Snare** | Body tone + bandpass noise + snap transient | 9ns (0.04%) | BP filter clamp ±2.0 |
| **Hats** | 6-osc ring modulation + noise blend | 3ns (0.01%) | HP filtered, no mud |
| **Tom** | Pitched sine + exponential pitch sweep | 4ns (0.02%) | — |
| **Perc** | FM carrier/modulator + index envelope | 8ns (0.03%) | Carrier freq clamped to Nyquist |
| **Clap** | 4 micro-bursts + diffuse tail + bandpass | 4ns (0.02%) | Output clamp ±1.5 |
| **Bass303** | PolyBLEP + 4-pole diode ladder + DC blocker | 67ns (0.30%) | Cutoff < sr×0.45, reso < 0.98 |
| **Lead** | PolyBLEP pulse/PWM + SVF + portamento | 8ns (0.03%) | SVF f-coeff < 0.9, state clamp, tanh output |
| **Pad** | Detuned saws + sub + LP filter + ADSR | 8ns (0.03%) | Cutoff clamped, steep decay |
| **Pluck** | Karplus-Strong physical model + damping | 5ns (0.02%) | Feedback < 0.990 |

> **Total budget for 8 simultaneous voices: < 1% CPU** at 44.1kHz.

## 🛡️ Occam Guardrails

Every archetype passes a **6-point quality gate** at both default and extreme parameter values:

| # | Guardrail | Threshold | Purpose |
|---|-----------|-----------|---------|
| 1 | No NaN | 0 occurrences | Numerical stability |
| 2 | No Inf | 0 occurrences | Filter stability |
| 3 | Peak amplitude | < 1.5 | Headroom before clipping |
| 4 | DC offset | < 0.01 | No speaker damage |
| 5 | CPU usage | < 5% per voice | Real-time safety |
| 6 | Deactivation | Must stop | No infinite tails |

```bash
# Run the test suite
cd dsplib && g++ -std=c++17 -O2 -I voices -o test tests/test_voices.cpp && ./test
# → 20/20 passed 🎉
```

## 📋 Spec Format

```json
{
  "plugin": {
    "name": "AcidStation",
    "version": "0.1.0",
    "company": "txt2vst",
    "prefix": "ACS",
    "mfr_code": "Tx2v",
    "code": "AcSt"
  },
  "channels": [
    { "name": "Kick",  "type": "drum",    "midi": 36 },
    { "name": "Snare", "type": "drum",    "midi": 37 },
    { "name": "Hats",  "type": "drum",    "midi": 38 },
    { "name": "Acid",  "type": "pitched", "midi_ch": 2 }
  ],
  "voices": [
    { "name": "Kick",  "params": ["tune","decay","punch","pitchenv","drive","sub"] },
    { "name": "Acid",  "params": ["cutoff","reso","envmod","decay","accent"] }
  ],
  "features": {
    "sequencer": true,
    "swing": true,
    "sidechain": false,
    "master_fx": ["drive"]
  }
}
```

## 📁 Project Structure

```
txt2vst/
├── forge.py              # Main generator: spec.json → JUCE project
├── prompt2spec.py        # NLP parser: text → spec.json
├── dsplib/
│   ├── archetypes.h      # Archetype registry & router docs
│   ├── voices/           # 10 production DSP implementations
│   │   ├── kick.h        │ snare.h  │ hats.h
│   │   ├── tom.h         │ perc.h   │ clap.h
│   │   ├── bass.h        │ lead.h   │ pad.h
│   │   ├── pluck.h       │ DspConstants.h
│   └── tests/
│       └── test_voices.cpp  # 20-test Occam guardrail suite
├── templates/
│   ├── skeleton/         # JUCE project template files (.tmpl)
│   ├── acidstation.spec.json
│   └── oldschoolbox.spec.json
└── output/               # Generated projects (gitignored)
```

## 🔧 Requirements

- Python 3.10+
- CMake 3.22+
- C++17 compiler (Xcode/Clang on macOS)
- [JUCE](https://github.com/juce-framework/JUCE) framework (added as submodule in generated projects)

## 🗺️ Roadmap

- [x] Deterministic skeleton generator
- [x] 10 production DSP archetypes
- [x] Occam guardrail test suite (20/20)
- [x] Prompt → spec.json parser
- [x] Full pipeline: text → compiled VST3
- [ ] UI generator (StepGrid + knob panels from spec)
- [ ] LLM-powered prompt interpreter (GPT/Claude API)
- [ ] CI/CD: auto-build + notarize on push
- [ ] Web interface at [txt2vst.com](https://txt2vst.com)
- [ ] Additional archetypes: organ, brass, choir, sampler

---

<div align="center">

**Made with** 🎵 **by** [fabriziosalmi](https://github.com/fabriziosalmi)

*From text to sound — no friction, no limits.*

</div>
