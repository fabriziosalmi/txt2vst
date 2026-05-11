#pragma once
// DSP Archetype Registry — deterministic router from voice type to implementation.
//
// Architecture: vertical specialized layers + deterministic router
//
// spec.voice.type ──► Router ──► Archetype ──► Generated .h file
//
// Each archetype is a self-contained DSP model that:
//  1. Follows the Voice Interface Contract (prepare/setParams/trigger/tick)
//  2. Has a known CPU budget (ops/sample)
//  3. Has Occam guardrails (frequency clamps, amplitude limits, filter stability)
//
// Archetypes (vertical layers):
//  ┌──────────────────────────────────────────────────────────┐
//  │  PERCUSSIVE (drum)           │  PITCHED (synth/bass)     │
//  │  ─────────────────           │  ────────────────────     │
//  │  kick   — pitch sweep + sub  │  bass_acid — ladder filter  │
//  │  snare  — body + noise       │  pad     — (future)       │
//  │  hats   — ring mod metallic  │  lead    — (future)       │
//  │  tom    — pitched body       │  organ   — (future)       │
//  │  perc   — FM/noise hybrid    │  pluck   — (future)       │
//  │  clap   — (future)           │  string  — (future)       │
//  │  rim    — (future)           │                           │
//  └──────────────────────────────────────────────────────────┘
//
// Router decision tree:
//  voice.type == "drum"?
//    ├─ has "tune" param with range 30-150Hz?     → kick
//    ├─ has "noise" param + "snap"?               → snare
//    ├─ has "tone" param + decay < 0.15?          → hats
//    ├─ has "tune" + "pitchenv"?                  → tom
//    └─ default                                   → perc (FM/noise)
//  voice.type == "pitched"?
//    ├─ has "cutoff" + "reso"?                    → bass_acid
//    ├─ has "attack" + decay > 1.0?               → pad
//    └─ default                                   → bass_acid

#include <string>
#include <vector>

struct ArchetypeInfo
{
    const char* id;          // "kick", "snare", "hats", "tom", "perc", "bass_acid"
    const char* header;      // "kick.h"
    const char* className;   // "KickVoice"
    int cpuBudget;           // ops/sample estimate
    bool isPitched;
};

static const ArchetypeInfo ARCHETYPES[] = {
    { "kick",    "kick.h",    "KickVoice",  15, false },
    { "snare",   "snare.h",   "SnareVoice", 12, false },
    { "hats",    "hats.h",    "HatsVoice",  10, false },
    { "tom",     "tom.h",     "TomVoice",    8, false },
    { "perc",    "perc.h",    "PercVoice",   8, false },
    { "bass_acid", "bass.h",    "BassVoice",  25, true  },
};
static constexpr int NUM_ARCHETYPES = sizeof(ARCHETYPES) / sizeof(ARCHETYPES[0]);
