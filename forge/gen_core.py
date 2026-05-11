"""forge.gen_core — Core infrastructure generators (params, voices, MIDI)."""

from .spec import const_name, SKELETON
import textwrap


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
