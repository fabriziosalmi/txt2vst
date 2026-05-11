# VST Forge — Generative VST Template System

> Extracted from the OldSchoolBox development history (32 commits, 2h45m build).
> Goal: generate a working JUCE VST3/AU from a JSON spec + a prompt.

## Architecture

```
vst-forge/
├── templates/
│   ├── skeleton/               ← Mustache-style .tmpl files
│   │   ├── CMakeLists.txt.tmpl
│   │   ├── src/
│   │   │   ├── PluginProcessor.h.tmpl
│   │   │   ├── PluginEditor.h.tmpl
│   │   │   ├── Sequencer.h.tmpl
│   │   │   ├── core/
│   │   │   │   ├── BusLayout.h.tmpl
│   │   │   │   ├── ParamIds.h.tmpl
│   │   │   │   ├── MidiRouter.h.tmpl
│   │   │   │   ├── TransportSync.h.tmpl
│   │   │   │   └── VoiceBank.h.tmpl
│   │   │   └── voices/
│   │   │       ├── DspConstants.h    ← Static (no template vars)
│   │   │       └── Voice.h.tmpl      ← Per-voice template
│   ├── oldschoolbox.spec.json  ← Reference spec (produces OldSchoolBox)
│   └── acidstation.spec.json   ← Example 4-channel acid box
└── docs/
    └── (this README)
```

## The Spec Format

A JSON file that defines everything about a VST:

| Field | Purpose |
|-------|---------|
| `plugin.*` | Name, company, codes, UI size |
| `channels[]` | Bus layout (name, type, MIDI mapping) |
| `voices[]` | DSP voice definitions with param specs |
| `features.*` | Sequencer, sidechain, master FX, swing |
| `default_patterns[]` | Initial groove bitmasks |

## Generation Pipeline

```
1. Parse spec.json
2. Generate static files:     DspConstants.h (copy)
3. Generate from channel spec: BusLayout.h, ParamIds.h, ParamLayout.cpp
4. Generate per-voice:         voices/XxxVoice.h × N
5. Generate from voice list:   VoiceBank.h/.cpp, MidiRouter.h
6. Generate from features:     Sequencer.h, TransportSync.h
7. Generate entry points:      PluginProcessor.h/.cpp, PluginEditor.h/.cpp
8. Generate build system:      CMakeLists.txt
9. Init JUCE submodule
10. Build: cmake -B build && cmake --build build --config Release
```

## Deterministic Build Phases (from timestamp analysis)

| Phase | Duration | Files Created |
|-------|----------|---------------|
| 0. Scaffold | ~10 min | git init, JUCE submodule, .gitignore, LICENSE |
| 1. Build System | ~2 min | CMakeLists.txt |
| 2. DSP Foundation | ~10 min | DspConstants.h + all voice .h files |
| 3. Core Engine | ~5 min | BusLayout, ParamIds, ParamLayout, VoiceBank, MidiRouter, Sequencer, TransportSync |
| 4. Entry Points | ~5 min | PluginProcessor, PluginEditor |
| 5. UI Components | ~10 min | StepGrid, SpaceLookAndFeel, ParamPanel |
| 6. Build + Test | ~3 min | cmake build |

## Voice Interface Contract

Every voice MUST implement:
```cpp
struct Params { float p1, p2, ...; };
void prepare(double sampleRate);
void setParams(const Params& p);
void trigger();          // drum
void trigger(int note);  // pitched
bool isActive() const;
float tick();            // returns 1 sample
```

## Next Steps

1. **Python generator**: Parse spec.json → render .tmpl files → output project
2. **DSP library**: Pre-built voice primitives (kick, snare, hat, bass, pad, lead)
3. **Prompt → Spec**: LLM that converts natural language to spec.json
4. **Prompt → VST**: Full pipeline: prompt → spec → skeleton → DSP fill → build
