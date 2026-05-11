#!/usr/bin/env python3
"""VST Forge — generates a compilable JUCE VST project from a spec.json."""

import json, os, sys, shutil, textwrap
from pathlib import Path

FORGE_DIR = Path(__file__).parent
SKELETON = FORGE_DIR / "templates" / "skeleton"


def load_spec(path: str) -> dict:
    with open(path) as f:
        return json.load(f)


def const_name(name: str) -> str:
    """Kick -> KICK, Bass1 -> BASS1"""
    return name.upper().replace(" ", "_")


# ─── File Generators ──────────────────────────────────────────────────────────

def gen_cmake(spec: dict) -> str:
    p = spec["plugin"]
    sources = [
        "src/PluginProcessor.cpp",
        "src/PluginEditor.cpp",
        "src/core/ParamLayout.cpp",
        "src/core/VoiceBank.cpp",
    ]
    if spec["features"].get("sequencer"):
        sources.append("src/ui/StepGrid.cpp")

    src_lines = "\n".join(f"    {s}" for s in sources)
    return textwrap.dedent(f"""\
        cmake_minimum_required(VERSION 3.22)
        project({p['name']} VERSION {p['version']})

        set(CMAKE_CXX_STANDARD 17)
        set(CMAKE_CXX_STANDARD_REQUIRED ON)

        add_subdirectory(JUCE)

        juce_add_plugin({p['name']}
            COMPANY_NAME "{p['company']}"
            PLUGIN_MANUFACTURER_CODE {p['mfr_code']}
            PLUGIN_CODE {p['code']}
            FORMATS VST3 AU
            PRODUCT_NAME "{p['name']}"
            IS_SYNTH TRUE
            NEEDS_MIDI_INPUT TRUE
            NEEDS_MIDI_OUTPUT FALSE
            IS_MIDI_EFFECT FALSE
            EDITOR_WANTS_KEYBOARD_FOCUS FALSE
            COPY_PLUGIN_AFTER_BUILD TRUE
        )

        target_sources({p['name']} PRIVATE
        {src_lines}
        )

        target_include_directories({p['name']} PRIVATE src)

        target_compile_definitions({p['name']} PUBLIC
            JUCE_WEB_BROWSER=0
            JUCE_USE_CURL=0
            JUCE_VST3_CAN_REPLACE_VST2=0
            JUCE_DISPLAY_SPLASH_SCREEN=0
            JUCE_USE_OGGVORBIS=0
        )

        juce_generate_juce_header({p['name']})

        target_link_libraries({p['name']} PRIVATE
            juce::juce_audio_utils
            juce::juce_dsp
            PUBLIC
            juce::juce_recommended_config_flags
            juce::juce_recommended_lto_flags
            juce::juce_recommended_warning_flags
        )
    """)


def gen_bus_layout(spec: dict) -> str:
    prefix = spec["plugin"]["prefix"]
    channels = spec["channels"]
    drums = [c for c in channels if c["type"] == "drum"]
    pitched = [c for c in channels if c["type"] == "pitched"]

    lines = ["#pragma once", "#include <JuceHeader.h>", ""]
    lines.append(f"namespace {prefix}Bus")
    lines.append("{")
    for i, ch in enumerate(channels):
        lines.append(f"    constexpr int {const_name(ch['name'])} = {i};")
    lines.append(f"    constexpr int COUNT = {len(channels)};")
    lines.append("")
    names = ", ".join(f'"{ch["name"]}"' for ch in channels)
    lines.append(f"    constexpr const char* NAMES[] = {{ {names} }};")
    lines.append("}")
    lines.append("")
    lines.append("namespace MidiMap")
    lines.append("{")
    for ch in drums:
        lines.append(f"    constexpr int {const_name(ch['name'])} = {ch['midi']};")
    for i, ch in enumerate(pitched):
        lines.append(f"    constexpr int {const_name(ch['name'])}_CH = {ch['midi_ch']};")
    lines.append("}")
    lines.append("")
    return "\n".join(lines)


def gen_param_ids(spec: dict) -> str:
    channels = spec["channels"]
    voices = spec["voices"]
    n = len(channels)

    lines = ["#pragma once", "", "namespace ParamId", "{"]
    # vol/pan
    for kind in ["vol", "pan"]:
        vol_ids = ", ".join(f'"{kind}_{i}"' for i in range(n))
        lines.append(f"    inline const char* {kind}(int ch)")
        lines.append("    {")
        lines.append(f"        static const char* ids[] = {{ {vol_ids} }};")
        lines.append(f"        if (ch < 0 || ch > {n-1}) return ids[0];")
        lines.append("        return ids[ch];")
        lines.append("    }")
        lines.append("")

    for v in voices:
        vname = v["name"].lower()
        vupper = v["name"].upper()
        lines.append(f"    // {v['name']}")
        for p in v["params"]:
            lines.append(f'    constexpr const char* {vupper}_{p.upper()} = "{vname}_{p}";')
        lines.append("")

    # Global
    if spec["features"].get("swing"):
        lines.append('    constexpr const char* SWING = "swing";')
    # Master FX
    fx_list = spec["features"].get("master_fx", [])
    if "drive" in fx_list:
        lines.append('    constexpr const char* MASTER_DRIVE = "master_drive";')
    if "delay" in fx_list:
        lines.append('    constexpr const char* DELAY_TIME = "delay_time";')
        lines.append('    constexpr const char* DELAY_FB = "delay_fb";')
        lines.append('    constexpr const char* DELAY_MIX = "delay_mix";')
        lines.append('    constexpr const char* DELAY_SYNC = "delay_sync";')
    if spec["features"].get("sidechain"):
        pitched = [c for c in channels if c["type"] == "pitched"]
        for c in pitched:
            lines.append(f'    constexpr const char* SC_{const_name(c["name"])} = "sc_{c["name"].lower()}";')
        lines.append('    constexpr const char* SC_RELEASE = "sc_release";')

    lines.append("}")
    lines.append("")
    return "\n".join(lines)


def gen_param_layout(spec: dict) -> str:
    prefix = spec["plugin"]["prefix"]
    voices = spec["voices"]
    n = len(spec["channels"])

    lines = ['#include "ParamLayout.h"', '#include "ParamIds.h"', '#include "BusLayout.h"', ""]
    lines.append("namespace ParamLayout")
    lines.append("{")
    lines.append("")
    lines.append("juce::AudioProcessorValueTreeState::ParameterLayout create()")
    lines.append("{")
    lines.append("    juce::AudioProcessorValueTreeState::ParameterLayout layout;")
    lines.append("")
    lines.append("    auto addF = [&](const char* id, const char* name,")
    lines.append("                    float lo, float hi, float step, float def)")
    lines.append("    {")
    lines.append("        layout.add(std::make_unique<juce::AudioParameterFloat>(")
    lines.append("            juce::ParameterID{ id, 1 }, name,")
    lines.append("            juce::NormalisableRange<float>(lo, hi, step), def));")
    lines.append("    };")
    lines.append("")
    # Volume + Pan
    lines.append(f"    for (int ch = 0; ch < {prefix}Bus::COUNT; ++ch)")
    lines.append("        layout.add(std::make_unique<juce::AudioParameterFloat>(")
    lines.append(f"            juce::ParameterID{{ ParamId::vol(ch), 1 }},")
    lines.append(f'            juce::String({prefix}Bus::NAMES[ch]) + " Volume",')
    lines.append("            juce::NormalisableRange<float>(0.f, 1.f), 0.8f));")
    lines.append("")
    lines.append(f"    for (int ch = 0; ch < {prefix}Bus::COUNT; ++ch)")
    lines.append("        layout.add(std::make_unique<juce::AudioParameterFloat>(")
    lines.append(f"            juce::ParameterID{{ ParamId::pan(ch), 1 }},")
    lines.append(f'            juce::String({prefix}Bus::NAMES[ch]) + " Pan",')
    lines.append("            juce::NormalisableRange<float>(0.f, 1.f), 0.5f));")
    lines.append("")

    for v in voices:
        vupper = v["name"].upper()
        lines.append(f"    // {v['name']}")
        for p in v["params"]:
            pid = f"ParamId::{vupper}_{p.upper()}"
            disp = f'"{v["name"]} {p.capitalize()}"'
            lines.append(f"    addF({pid}, {disp}, 0.f, 1.f, 0.01f, 0.5f);")
        lines.append("")

    if spec["features"].get("swing"):
        lines.append('    addF(ParamId::SWING, "Swing", 0.f, 1.f, 0.01f, 0.f);')

    fx_list = spec["features"].get("master_fx", [])
    if "drive" in fx_list:
        lines.append('    addF(ParamId::MASTER_DRIVE, "Drive", 0.f, 1.f, 0.01f, 0.f);')
    if "delay" in fx_list:
        lines.append('    addF(ParamId::DELAY_TIME, "Delay Time", 0.01f, 1.f, 0.001f, 0.375f);')
        lines.append('    addF(ParamId::DELAY_FB, "Delay Feedback", 0.f, 0.90f, 0.01f, 0.40f);')
        lines.append('    addF(ParamId::DELAY_MIX, "Delay Mix", 0.f, 1.f, 0.01f, 0.f);')
        lines.append("    layout.add(std::make_unique<juce::AudioParameterInt>(")
        lines.append('        juce::ParameterID{ ParamId::DELAY_SYNC, 1 }, "Delay Sync", 0, 6, 0));')

    lines.append("")
    lines.append("    return layout;")
    lines.append("}")
    lines.append("")
    lines.append("} // namespace ParamLayout")
    lines.append("")
    return "\n".join(lines)


def gen_param_layout_h() -> str:
    return textwrap.dedent("""\
        #pragma once
        #include <JuceHeader.h>

        namespace ParamLayout {
            juce::AudioProcessorValueTreeState::ParameterLayout create();
        }
    """)


def gen_voice_stub(voice: dict) -> str:
    """Generate a minimal but functional voice .h file (deterministic skeleton)."""
    name = voice.get("class", f"{voice['name']}Voice")
    params = voice["params"]
    is_pitched = voice.get("type", "drum") == "pitched" or "cutoff" in params
    decay_param = "decay" if "decay" in params else params[-1]

    L = []
    L.append("#pragma once")
    L.append("#include <cmath>")
    L.append('#include "DspConstants.h"')
    L.append("")
    L.append(f"// TODO: Replace stub DSP with production-grade synthesis")
    L.append(f"class {name}")
    L.append("{")
    L.append("public:")
    L.append("    struct Params")
    L.append("    {")
    for p in params:
        L.append(f"        float {p} = 0.5f;")
    L.append("    };")
    L.append("")
    L.append("    void prepare(double sr) { sampleRate = sr; }")
    L.append("    void setParams(const Params& p) { params = p; }")
    L.append("")
    if is_pitched:
        L.append("    void trigger(int midiNote, float velocity = 1.0f)")
        L.append("    {")
        L.append("        phase = 0.0;")
        L.append("        targetFreq = 440.0 * std::pow(2.0, (midiNote - 69) / 12.0);")
        L.append("        vel = velocity;")
    else:
        L.append("    void trigger()")
        L.append("    {")
        L.append("        phase = 0.0;")
    L.append(f"        samplesRemaining = static_cast<int>(sampleRate * params.{decay_param} * 3.0);")
    L.append("        ampEnv = 1.0f;")
    L.append(f"        ampCoeff = static_cast<float>(std::exp(-1.0 / (params.{decay_param} * sampleRate)));")
    L.append("        active = true;")
    L.append("    }")
    if is_pitched:
        L.append("")
        L.append("    void noteOff() { releasing = true; }")
    L.append("")
    L.append("    bool isActive() const { return active && samplesRemaining > 0; }")
    L.append("")
    L.append("    float tick()")
    L.append("    {")
    L.append("        if (!active || samplesRemaining <= 0) { active = false; return 0.0f; }")
    L.append("        --samplesRemaining;")
    L.append("        ampEnv *= ampCoeff;")
    L.append("        if (ampEnv < 0.0001f) { active = false; return 0.0f; }")
    if is_pitched:
        L.append("        const double freq = targetFreq;")
    else:
        L.append("        const double freq = 220.0;")
    L.append("        phase += (Dsp::TWO_PI * freq) / sampleRate;")
    L.append("        if (phase >= Dsp::TWO_PI) phase -= Dsp::TWO_PI;")
    vel = " * vel" if is_pitched else ""
    L.append(f"        return fastSinD(phase) * ampEnv{vel};")
    L.append("    }")
    L.append("")
    L.append("private:")
    L.append("    Params params;")
    L.append("    double sampleRate = 44100.0;")
    L.append("    int samplesRemaining = 0;")
    L.append("    double phase = 0.0;")
    L.append("    float ampEnv = 0.0f, ampCoeff = 0.999f;")
    L.append("    bool active = false;")
    if is_pitched:
        L.append("    double targetFreq = 110.0;")
        L.append("    float vel = 1.0f;")
        L.append("    bool releasing = false;")
    L.append("};")
    L.append("")
    return "\n".join(L)


def gen_voicebank_h(spec: dict) -> str:
    prefix = spec["plugin"]["prefix"]
    channels = spec["channels"]
    voices = spec["voices"]
    drums = [v for v, c in zip(voices, channels) if c["type"] == "drum"]
    pitched = [v for v, c in zip(voices, channels) if c["type"] == "pitched"]

    includes = []
    seen = set()
    for v in voices:
        cls = v.get("class", f"{v['name']}Voice")
        if cls not in seen:
            includes.append(f'#include "../voices/{cls}.h"')
            seen.add(cls)

    inc_str = "\n".join(includes)
    drum_fields = "\n".join(
        f"    {v.get('class', v['name']+'Voice')} {v['name'].lower()};"
        for v in drums
    )
    pitched_cls = pitched[0].get("class", f"{pitched[0]['name']}Voice") if pitched else ""

    return textwrap.dedent(f"""\
        #pragma once
        #include <JuceHeader.h>
        #include <atomic>
        #include <array>
        {inc_str}
        #include "BusLayout.h"

        class VoiceBank
        {{
        public:
            explicit VoiceBank(juce::AudioProcessorValueTreeState& apvts);
            void prepare(double sampleRate);
            void consumeUiTriggers();
            void trigger(int ch, float vel = 1.0f);
            {"void triggerPitched(int idx, int midiNote, float vel = 1.0f);" if pitched else ""}
            {"void noteOffPitched(int idx);" if pitched else ""}
            void renderBus(int ch, float* L, float* R, int numSamples, float vol);
            bool isActive(int ch) const;
            void requestTrigger(int ch);

        private:
            juce::AudioProcessorValueTreeState& apvts;
            double storedSampleRate = 44100.0;
        {drum_fields}
            {"std::array<" + pitched_cls + ", " + str(len(pitched)) + "> pitched;" if pitched else ""}
            std::array<std::atomic<bool>, {prefix}Bus::COUNT> uiTriggers {{}};
            std::array<float, {prefix}Bus::COUNT> channelVelocity {{}};
            float raw(const char* id) const;
            JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR(VoiceBank)
        }};
    """)


def gen_voicebank_cpp(spec: dict) -> str:
    prefix = spec["plugin"]["prefix"]
    channels = spec["channels"]
    voices = spec["voices"]
    drums = [(v, c) for v, c in zip(voices, channels) if c["type"] == "drum"]
    pitched = [(v, c) for v, c in zip(voices, channels) if c["type"] == "pitched"]

    # Constructor
    lines = ['#include "VoiceBank.h"', '#include "ParamIds.h"', ""]
    lines.append("VoiceBank::VoiceBank(juce::AudioProcessorValueTreeState& a) : apvts(a)")
    lines.append("{")
    lines.append("    for (auto& t : uiTriggers) t.store(false);")
    lines.append("    channelVelocity.fill(1.0f);")
    lines.append("}")
    lines.append("")

    # raw helper
    lines.append("float VoiceBank::raw(const char* id) const")
    lines.append("{ return apvts.getRawParameterValue(id)->load(); }")
    lines.append("")

    # prepare
    lines.append("void VoiceBank::prepare(double sr)")
    lines.append("{")
    lines.append("    storedSampleRate = sr;")
    for v, c in drums:
        lines.append(f"    {v['name'].lower()}.prepare(sr);")
    if pitched:
        lines.append("    for (auto& p : pitched) p.prepare(sr);")
    lines.append("}")
    lines.append("")

    # requestTrigger
    lines.append("void VoiceBank::requestTrigger(int ch)")
    lines.append("{")
    lines.append(f"    if (ch >= 0 && ch < {prefix}Bus::COUNT) uiTriggers[ch].store(true);")
    lines.append("}")
    lines.append("")

    # consumeUiTriggers
    lines.append("void VoiceBank::consumeUiTriggers()")
    lines.append("{")
    lines.append(f"    for (int i = 0; i < {len(drums)}; ++i)")
    lines.append("        if (uiTriggers[i].exchange(false)) trigger(i, 1.0f);")
    if pitched:
        lines.append(f"    for (int i = 0; i < {len(pitched)}; ++i)")
        lines.append(f"        if (uiTriggers[{prefix}Bus::{const_name(pitched[0][1]['name'])} + i].exchange(false))")
        lines.append("            triggerPitched(i, 48, 1.0f);")
    lines.append("}")
    lines.append("")

    # trigger (drums)
    lines.append("void VoiceBank::trigger(int ch, float vel)")
    lines.append("{")
    lines.append(f"    if (ch >= 0 && ch < {prefix}Bus::COUNT) channelVelocity[ch] = vel;")
    lines.append("    switch (ch) {")
    for v, c in drums:
        cn = const_name(c["name"])
        inst = v["name"].lower()
        vupper = v["name"].upper()
        param_reads = ", ".join(f"raw(ParamId::{vupper}_{p.upper()})" for p in v["params"])
        lines.append(f"        case {prefix}Bus::{cn}:")
        lines.append(f"            {inst}.setParams({{ {param_reads} }});")
        lines.append(f"            {inst}.trigger(); break;")
    lines.append("        default: break;")
    lines.append("    }")
    lines.append("}")
    lines.append("")

    # triggerPitched
    if pitched:
        lines.append("void VoiceBank::triggerPitched(int idx, int midiNote, float vel)")
        lines.append("{")
        lines.append(f"    if (idx < 0 || idx >= {len(pitched)}) return;")
        first_pitched_bus = const_name(pitched[0][1]["name"])
        lines.append(f"    channelVelocity[{prefix}Bus::{first_pitched_bus} + idx] = vel;")
        for i, (v, c) in enumerate(pitched):
            vupper = v["name"].upper()
            param_reads = ", ".join(f"raw(ParamId::{vupper}_{p.upper()})" for p in v["params"])
            cond = "if" if i == 0 else "else if"
            lines.append(f"    {cond} (idx == {i})")
            lines.append(f"        pitched[{i}].setParams({{ {param_reads} }});")
        lines.append("    pitched[idx].trigger(midiNote, vel);")
        lines.append("}")
        lines.append("")
        lines.append("void VoiceBank::noteOffPitched(int idx)")
        lines.append("{")
        lines.append(f"    if (idx >= 0 && idx < {len(pitched)}) pitched[idx].noteOff();")
        lines.append("}")
        lines.append("")

    # isActive
    lines.append("bool VoiceBank::isActive(int ch) const")
    lines.append("{")
    lines.append("    switch (ch) {")
    for v, c in drums:
        lines.append(f"        case {prefix}Bus::{const_name(c['name'])}: return {v['name'].lower()}.isActive();")
    for i, (v, c) in enumerate(pitched):
        lines.append(f"        case {prefix}Bus::{const_name(c['name'])}: return pitched[{i}].isActive();")
    lines.append("        default: return false;")
    lines.append("    }")
    lines.append("}")
    lines.append("")

    # renderBus
    lines.append("void VoiceBank::renderBus(int ch, float* L, float* R, int n, float vol)")
    lines.append("{")
    lines.append(f"    const float gain = vol * ((ch >= 0 && ch < {prefix}Bus::COUNT) ? channelVelocity[ch] : 1.0f);")
    lines.append("    if (!isActive(ch) || L == nullptr) return;")
    lines.append("    auto fill = [&](auto& v) { for (int i = 0; i < n; ++i) { float s = v.tick() * gain; L[i] = s; R[i] = s; } };")
    lines.append("    switch (ch) {")
    for v, c in drums:
        lines.append(f"        case {prefix}Bus::{const_name(c['name'])}: fill({v['name'].lower()}); break;")
    for i, (v, c) in enumerate(pitched):
        lines.append(f"        case {prefix}Bus::{const_name(c['name'])}: fill(pitched[{i}]); break;")
    lines.append("        default: break;")
    lines.append("    }")
    lines.append("}")
    lines.append("")
    return "\n".join(lines)


def gen_midi_router(spec: dict) -> str:
    prefix = spec["plugin"]["prefix"]
    channels = spec["channels"]
    drums = [c for c in channels if c["type"] == "drum"]
    pitched = [c for c in channels if c["type"] == "pitched"]

    lines = ["#pragma once", '#include <JuceHeader.h>', '#include "VoiceBank.h"', '#include "BusLayout.h"', ""]
    lines.append("struct MidiRouter")
    lines.append("{")
    lines.append("    static void process(const juce::MidiBuffer& midi, VoiceBank& voices)")
    lines.append("    {")
    lines.append("        for (const auto meta : midi)")
    lines.append("        {")
    lines.append("            const auto msg = meta.getMessage();")
    lines.append("            const int ch = msg.getChannel();")
    lines.append("            if (msg.isNoteOn(false))")
    lines.append("            {")
    lines.append("                const int note = msg.getNoteNumber();")
    lines.append("                const float vel = msg.getFloatVelocity();")
    # Drum switch
    if pitched:
        conds = " && ".join(f"ch != MidiMap::{const_name(c['name'])}_CH" for c in pitched)
        lines.append(f"                if ({conds})")
    lines.append("                {")
    lines.append("                    switch (note) {")
    for c in drums:
        cn = const_name(c["name"])
        lines.append(f"                        case MidiMap::{cn}: voices.trigger({prefix}Bus::{cn}, vel); break;")
    lines.append("                        default: break;")
    lines.append("                    }")
    lines.append("                }")
    for i, c in enumerate(pitched):
        cn = const_name(c["name"])
        lines.append(f"                if (ch == MidiMap::{cn}_CH) voices.triggerPitched({i}, note, vel);")
    lines.append("            }")
    if pitched:
        lines.append("            if (msg.isNoteOff())")
        lines.append("            {")
        for i, c in enumerate(pitched):
            cn = const_name(c["name"])
            lines.append(f"                if (ch == MidiMap::{cn}_CH) voices.noteOffPitched({i});")
        lines.append("            }")
    lines.append("        }")
    lines.append("    }")
    lines.append("};")
    lines.append("")
    return "\n".join(lines)


# ─── Archetype Router ─────────────────────────────────────────────────────────

DSPLIB = FORGE_DIR / "dsplib" / "voices"

# Maps voice characteristics to production DSP files
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
    "pluck":   "pluck.h",
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


# ─── Missing File Generators ─────────────────────────────────────────────────

def gen_sequencer_h(spec: dict) -> str:
    """Copy the Sequencer.h template with NUM_CHANNELS substituted."""
    tmpl = (SKELETON / "src" / "Sequencer.h.tmpl").read_text()
    return tmpl.replace("{{NUM_CHANNELS}}", str(len(spec["channels"])))


def gen_transport_sync_h(spec: dict) -> str:
    prefix = spec["plugin"]["prefix"]
    channels = spec["channels"]
    pitched = [(i, c) for i, c in enumerate(channels) if c["type"] == "pitched"]
    first_pi = pitched[0][0] if pitched else -1
    L = []
    L.append("#pragma once")
    L.append("#include <JuceHeader.h>")
    L.append("#include <array>")
    L.append("#include <cmath>")
    L.append('#include "VoiceBank.h"')
    L.append('#include "../Sequencer.h"')
    L.append("")
    L.append("struct TransportSync")
    L.append("{")
    L.append("    static void process(juce::AudioPlayHead* playHead,")
    L.append("                        Sequencer& seq, VoiceBank& voices,")
    L.append("                        std::array<int, Sequencer::NUM_CHANNELS>& lastSteps,")
    L.append("                        int64_t& prevBar, float swing)")
    L.append("    {")
    L.append("        if (!playHead) return;")
    L.append("        const auto pos = playHead->getPosition();")
    L.append("        if (!pos) return;")
    L.append("        const bool playing = pos->getIsPlaying();")
    L.append("        seq.isPlaying.store(playing, std::memory_order_release);")
    L.append("        if (!playing) {")
    L.append("            for (auto& s : seq.currentSteps) s.store(-1, std::memory_order_release);")
    L.append("            lastSteps.fill(-1); prevBar = -1; return;")
    L.append("        }")
    L.append("        const auto ppqOpt = pos->getPpqPosition();")
    L.append("        if (!ppqOpt) return;")
    L.append("        const double ppq = *ppqOpt < 0.0 ? 0.0 : *ppqOpt;")
    L.append("        const double swingFactor = 0.5 + static_cast<double>(swing) * 0.25;")
    L.append("        constexpr double ppqPerPair = 0.5;")
    L.append("        const auto pairIdx = static_cast<int64_t>(std::floor(ppq / ppqPerPair));")
    L.append("        const double posInPair = ppq - static_cast<double>(pairIdx) * ppqPerPair;")
    L.append("        const int64_t globalStep = (posInPair < swingFactor * ppqPerPair)")
    L.append("                                   ? pairIdx * 2 : pairIdx * 2 + 1;")
    L.append("        const int64_t currentBar = globalStep / 16;")
    L.append("        seq.currentBar.store(currentBar, std::memory_order_release);")
    L.append("        prevBar = currentBar;")
    L.append("        for (int ch = 0; ch < Sequencer::NUM_CHANNELS; ++ch) {")
    L.append("            const int len = seq.getPatternLength(ch);")
    L.append("            const int chStep = static_cast<int>(((globalStep % len) + len) % len);")
    L.append("            seq.currentSteps[ch].store(chStep, std::memory_order_release);")
    L.append("            if (chStep == lastSteps[ch]) continue;")
    L.append("            lastSteps[ch] = chStep;")
    L.append("            if (seq.getStep(ch, chStep)) {")
    L.append("                float vel = seq.getVelocity(ch, chStep) / 127.0f;")
    if pitched:
        L.append(f"                if (ch >= {first_pi}) {{")
        L.append(f"                    voices.triggerPitched(ch - {first_pi}, 48, vel);")
        L.append("                } else {")
        L.append("                    voices.trigger(ch, vel);")
        L.append("                }")
    else:
        L.append("                voices.trigger(ch, vel);")
    L.append("            }")
    if pitched:
        L.append(f"            else if (ch >= {first_pi} && voices.isActive(ch))")
        L.append(f"                voices.noteOffPitched(ch - {first_pi});")
    L.append("        }")
    L.append("    }")
    L.append("};")
    L.append("")
    return "\n".join(L)


def gen_processor_h(spec: dict) -> str:
    prefix = spec["plugin"]["prefix"]
    name = spec["plugin"]["name"]
    L = []
    L.append("#pragma once")
    L.append("#include <JuceHeader.h>")
    L.append('#include "core/BusLayout.h"')
    L.append('#include "core/VoiceBank.h"')
    L.append('#include "core/ParamLayout.h"')
    L.append('#include "Sequencer.h"')
    L.append("")
    L.append(f"class {name}Processor : public juce::AudioProcessor")
    L.append("{")
    L.append("public:")
    L.append(f"    {name}Processor();")
    L.append(f"    ~{name}Processor() override = default;")
    L.append("    void prepareToPlay(double sampleRate, int samplesPerBlock) override;")
    L.append("    void releaseResources() override {}")
    L.append("    bool isBusesLayoutSupported(const BusesLayout&) const override;")
    L.append("    void processBlock(juce::AudioBuffer<float>&, juce::MidiBuffer&) override;")
    L.append("    juce::AudioProcessorEditor* createEditor() override;")
    L.append("    bool hasEditor() const override { return true; }")
    L.append('    const juce::String getName() const override { return JucePlugin_Name; }')
    L.append("    bool acceptsMidi() const override { return true; }")
    L.append("    bool producesMidi() const override { return false; }")
    L.append("    bool isMidiEffect() const override { return false; }")
    L.append("    double getTailLengthSeconds() const override { return 2.0; }")
    L.append("    int getNumPrograms() override { return 1; }")
    L.append("    int getCurrentProgram() override { return 0; }")
    L.append("    void setCurrentProgram(int) override {}")
    L.append('    const juce::String getProgramName(int) override { return {}; }')
    L.append("    void changeProgramName(int, const juce::String&) override {}")
    L.append("    void getStateInformation(juce::MemoryBlock&) override;")
    L.append("    void setStateInformation(const void*, int) override;")
    L.append("")
    L.append("    juce::AudioProcessorValueTreeState apvts;")
    L.append("    Sequencer sequencer;")
    L.append("    VoiceBank voiceBank;")
    L.append("    std::atomic<float> currentBpm { 120.0f };")
    L.append("private:")
    L.append(f"    std::array<int, Sequencer::NUM_CHANNELS> lastSteps;")
    L.append("    int64_t prevBar = -1;")
    L.append("    double currentSampleRate = 44100.0;")
    L.append(f"    struct CrossoverState {{ float lpL = 0.0f, lpR = 0.0f; }};")
    L.append(f"    std::array<CrossoverState, {prefix}Bus::COUNT> crossover {{}};")
    L.append("    float crossoverAlpha = 0.04f;")
    L.append(f"    JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR({name}Processor)")
    L.append("};")
    L.append("")
    return "\n".join(L)


def gen_editor_h(spec: dict) -> str:
    name = spec["plugin"]["name"]
    L = []
    L.append("#pragma once")
    L.append("#include <JuceHeader.h>")
    L.append(f'#include "PluginProcessor.h"')
    L.append('#include "ui/SpaceLookAndFeel.h"')
    L.append("")
    L.append(f"class {name}Editor : public juce::AudioProcessorEditor")
    L.append("{")
    L.append("public:")
    L.append(f"    explicit {name}Editor({name}Processor&);")
    L.append(f"    ~{name}Editor() override;")
    L.append("    void paint(juce::Graphics&) override;")
    L.append("    void resized() override;")
    L.append("private:")
    L.append("    static constexpr int TITLE_H = 28;")
    L.append(f"    {name}Processor& processorRef;")
    L.append("    SpaceLookAndFeel spaceLnf;")
    L.append(f"    JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR({name}Editor)")
    L.append("};")
    L.append("")
    return "\n".join(L)


def gen_processor_cpp(spec: dict) -> str:
    prefix = spec["plugin"]["prefix"]
    name = spec["plugin"]["name"]
    channels = spec["channels"]
    patterns = spec.get("default_patterns", [])
    L = []
    L.append(f'#include "PluginProcessor.h"')
    L.append(f'#include "PluginEditor.h"')
    L.append('#include "core/MidiRouter.h"')
    L.append('#include "core/TransportSync.h"')
    L.append('#include "core/ParamIds.h"')
    L.append('#include "voices/DspConstants.h"')
    L.append("")
    if patterns:
        pats = ", ".join(patterns)
        L.append(f"static constexpr uint64_t kDefaultPatterns[{len(channels)}] = {{ {pats} }};")
    L.append("")
    L.append(f"{name}Processor::{name}Processor()")
    L.append(f'    : AudioProcessor(BusesProperties().withOutput("Main", juce::AudioChannelSet::stereo(), true)),')
    L.append(f'      apvts(*this, nullptr, "STATE", ParamLayout::create()),')
    L.append(f"      voiceBank(apvts)")
    L.append("{")
    L.append("    lastSteps.fill(-1);")
    if patterns:
        L.append(f"    for (int ch = 0; ch < Sequencer::NUM_CHANNELS; ++ch)")
        L.append(f"        sequencer.setPattern(ch, kDefaultPatterns[ch]);")
    L.append("}")
    L.append("")
    L.append(f"bool {name}Processor::isBusesLayoutSupported(const BusesLayout& layouts) const")
    L.append("{ return layouts.outputBuses.size() == 1 && layouts.getMainOutputChannelSet() == juce::AudioChannelSet::stereo(); }")
    L.append("")
    L.append(f"void {name}Processor::prepareToPlay(double sampleRate, int)")
    L.append("{")
    L.append("    lastSteps.fill(-1); prevBar = -1;")
    L.append("    currentSampleRate = sampleRate;")
    L.append(f"    crossoverAlpha = 1.0f - static_cast<float>(std::exp(-Dsp::TWO_PI * 300.0 / sampleRate));")
    L.append("    voiceBank.prepare(sampleRate);")
    L.append(f"    for (auto& cs : crossover) {{ cs.lpL = 0.0f; cs.lpR = 0.0f; }}")
    L.append("}")
    L.append("")
    L.append(f"void {name}Processor::processBlock(juce::AudioBuffer<float>& buffer, juce::MidiBuffer& midi)")
    L.append("{")
    L.append("    juce::ScopedNoDenormals noDenormals;")
    L.append("    voiceBank.consumeUiTriggers();")
    L.append("    MidiRouter::process(midi, voiceBank);")
    if spec["features"].get("swing"):
        L.append("    const float swing = apvts.getRawParameterValue(ParamId::SWING)->load();")
    else:
        L.append("    const float swing = 0.0f;")
    L.append("    TransportSync::process(getPlayHead(), sequencer, voiceBank, lastSteps, prevBar, swing);")
    L.append("    if (auto* ph = getPlayHead())")
    L.append("        if (auto pos = ph->getPosition())")
    L.append("            if (auto bpm = pos->getBpm())")
    L.append("                currentBpm.store(static_cast<float>(*bpm), std::memory_order_relaxed);")
    L.append("    const int numSamples = buffer.getNumSamples();")
    L.append("    auto* mainL = buffer.getWritePointer(0);")
    L.append("    auto* mainR = buffer.getWritePointer(1);")
    L.append("    buffer.clear();")
    L.append("    constexpr int STACK_MAX = 2048;")
    L.append("    float tmpL[STACK_MAX], tmpR[STACK_MAX];")
    L.append("    for (int offset = 0; offset < numSamples; offset += STACK_MAX) {")
    L.append("    const int blockSize = std::min(numSamples - offset, STACK_MAX);")
    L.append(f"    for (int voice = 0; voice < {prefix}Bus::COUNT; ++voice) {{")
    L.append("        if (!voiceBank.isActive(voice) || !sequencer.isChannelAudible(voice)) continue;")
    L.append("        const float vol = apvts.getRawParameterValue(ParamId::vol(voice))->load();")
    L.append("        std::memset(tmpL, 0, static_cast<size_t>(blockSize) * sizeof(float));")
    L.append("        std::memset(tmpR, 0, static_cast<size_t>(blockSize) * sizeof(float));")
    L.append("        voiceBank.renderBus(voice, tmpL, tmpR, blockSize, vol);")
    L.append("        const float p = apvts.getRawParameterValue(ParamId::pan(voice))->load();")
    L.append("        const float panR = fastSin(p * Dsp::HALF_PI_F);")
    L.append("        const float panL = fastSin((1.0f - p) * Dsp::HALF_PI_F);")
    L.append("        for (int i = 0; i < blockSize; ++i) {")
    L.append("            const float s = tmpL[i];")
    L.append("            mainL[offset + i] += s * panL;")
    L.append("            mainR[offset + i] += s * panR;")
    L.append("        }")
    L.append("    }")
    L.append("    for (int i = 0; i < blockSize; ++i) {")
    L.append("        mainL[offset + i] = fastTanh(mainL[offset + i]);")
    L.append("        mainR[offset + i] = fastTanh(mainR[offset + i]);")
    L.append("    }")
    L.append("    } // offset loop")
    L.append("}")
    L.append("")
    L.append(f"juce::AudioProcessorEditor* {name}Processor::createEditor()")
    L.append(f"{{ return new {name}Editor(*this); }}")
    L.append("")
    L.append(f"void {name}Processor::getStateInformation(juce::MemoryBlock& destData)")
    L.append("{ auto state = apvts.copyState(); copyXmlToBinary(*state.createXml(), destData); }")
    L.append("")
    L.append(f"void {name}Processor::setStateInformation(const void* data, int sizeInBytes)")
    L.append("{")
    L.append("    auto xml = getXmlFromBinary(data, sizeInBytes);")
    L.append("    if (!xml || !xml->hasTagName(apvts.state.getType())) return;")
    L.append("    apvts.replaceState(juce::ValueTree::fromXml(*xml));")
    L.append("}")
    L.append("")
    L.append("juce::AudioProcessor* JUCE_CALLTYPE createPluginFilter()")
    L.append(f"{{ return new {name}Processor(); }}")
    L.append("")
    return "\n".join(L)


def gen_editor_cpp(spec: dict) -> str:
    prefix = spec["plugin"]["prefix"]
    name = spec["plugin"]["name"]
    ui = spec["plugin"].get("ui", [800, 500])
    L = []
    L.append(f'#include "PluginEditor.h"')
    L.append("")
    L.append(f"{name}Editor::{name}Editor({name}Processor& p)")
    L.append(f"    : AudioProcessorEditor(&p), processorRef(p)")
    L.append("{")
    L.append(f"    setSize({ui[0]}, {ui[1]});")
    L.append("    setLookAndFeel(&spaceLnf);")
    L.append("}")
    L.append("")
    L.append(f"{name}Editor::~{name}Editor() {{ setLookAndFeel(nullptr); }}")
    L.append("")
    L.append(f"void {name}Editor::paint(juce::Graphics& g)")
    L.append("{")
    L.append('    g.fillAll(juce::Colour(0xff1a1a2e));')
    L.append("    g.setColour(juce::Colours::white);")
    L.append("    g.setFont(18.0f);")
    L.append(f'    g.drawText("{name}", getLocalBounds().removeFromTop(TITLE_H), juce::Justification::centred);')
    L.append("}")
    L.append("")
    L.append(f"void {name}Editor::resized() {{}}")
    L.append("")
    return "\n".join(L)


def gen_look_and_feel() -> str:
    L = []
    L.append("#pragma once")
    L.append("#include <JuceHeader.h>")
    L.append("")
    L.append("class SpaceLookAndFeel : public juce::LookAndFeel_V4")
    L.append("{")
    L.append("public:")
    L.append("    SpaceLookAndFeel() { setDefaultSansSerifTypefaceName(\"Arial\"); }")
    L.append("};")
    L.append("")
    return "\n".join(L)


# ─── Main Generator ──────────────────────────────────────────────────────────

def generate(spec_path: str, output_dir: str):
    spec = load_spec(spec_path)
    out = Path(output_dir)
    name = spec["plugin"]["name"]

    print(f"🔨 VST Forge — generating {name} → {out}")

    for d in ["src", "src/core", "src/voices", "src/ui"]:
        (out / d).mkdir(parents=True, exist_ok=True)

    # Static files
    shutil.copy(SKELETON / "src" / "voices" / "DspConstants.h",
                out / "src" / "voices" / "DspConstants.h")

    # Generated files
    files = {
        "CMakeLists.txt": gen_cmake(spec),
        "src/core/BusLayout.h": gen_bus_layout(spec),
        "src/core/ParamIds.h": gen_param_ids(spec),
        "src/core/ParamLayout.h": gen_param_layout_h(),
        "src/core/ParamLayout.cpp": gen_param_layout(spec),
        "src/core/VoiceBank.h": gen_voicebank_h(spec),
        "src/core/VoiceBank.cpp": gen_voicebank_cpp(spec),
        "src/core/MidiRouter.h": gen_midi_router(spec),
        "src/core/TransportSync.h": gen_transport_sync_h(spec),
        "src/Sequencer.h": gen_sequencer_h(spec),
        "src/PluginProcessor.h": gen_processor_h(spec),
        "src/PluginProcessor.cpp": gen_processor_cpp(spec),
        "src/PluginEditor.h": gen_editor_h(spec),
        "src/PluginEditor.cpp": gen_editor_cpp(spec),
        "src/ui/SpaceLookAndFeel.h": gen_look_and_feel(),
    }
    if spec["features"].get("sequencer"):
        files["src/ui/StepGrid.cpp"] = "// StepGrid stub — TODO\n#include <JuceHeader.h>\n"

    # Voices: try production DSP from dsplib, fall back to stub
    seen_classes = set()
    for v, c in zip(spec["voices"], spec["channels"]):
        cls = v.get("class", f"{v['name']}Voice")
        if cls in seen_classes:
            continue
        seen_classes.add(cls)

        archetype = route_archetype(v, c)
        dsp_file = DSPLIB / ARCHETYPE_MAP.get(archetype, "") if archetype else None

        if dsp_file and dsp_file.exists():
            # Production DSP — copy and rename class
            content = dsp_file.read_text()
            # If class name differs from archetype, do a simple rename
            arch_class = {"kick": "KickVoice", "snare": "SnareVoice",
                          "hats": "HatsVoice", "bass303": "BassVoice",
                          "tom": "TomVoice", "perc": "PercVoice",
                          "clap": "ClapVoice", "pad": "PadVoice",
                          "lead": "LeadVoice", "pluck": "PluckVoice"}.get(archetype)
            if arch_class and arch_class != cls:
                content = content.replace(f"class {arch_class}", f"class {cls}")
                content = content.replace(f"struct {arch_class}", f"struct {cls}")
            files[f"src/voices/{cls}.h"] = content
            print(f"  🎯 {cls} ← dsplib/{archetype} (production)")
        else:
            v_copy = dict(v)
            v_copy["type"] = c["type"]
            files[f"src/voices/{cls}.h"] = gen_voice_stub(v_copy)
            print(f"  📝 {cls} ← stub (needs DSP implementation)")

    # Write all files
    for path, content in files.items():
        fp = out / path
        fp.write_text(content)
        if not path.startswith("src/voices/"):
            print(f"  ✅ {path}")

    total_loc = sum(len(c.splitlines()) for c in files.values())
    print(f"\n🎉 Generated {len(files)} files, ~{total_loc} LOC")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python forge.py <spec.json> <output_dir>")
        sys.exit(1)
    generate(sys.argv[1], sys.argv[2])
