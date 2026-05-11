"""forge.gen_ui — UI generators (editor, stepgrid, param panel)."""

from .spec import const_name


def gen_editor_cpp(spec: dict) -> str:
    name = spec["plugin"]["name"]
    ui = spec["plugin"].get("ui", [1031, 625])
    L = []
    L.append(f'#include "PluginEditor.h"')
    L.append(f'#include "core/ParamIds.h"')
    L.append("")
    L.append(f"{name}Editor::{name}Editor({name}Processor& p)")
    L.append(f"    : AudioProcessorEditor(&p), processorRef(p),")
    L.append(f"      stepGrid(p.sequencer, p.voiceBank, p.apvts, p.currentBpm)")
    L.append("{")
    L.append(f"    setSize({ui[0]}, {ui[1]});")
    L.append("    setLookAndFeel(&spaceLnf);")
    L.append("    addAndMakeVisible(stepGrid);")
    L.append("}")
    L.append("")
    L.append(f"{name}Editor::~{name}Editor() {{ setLookAndFeel(nullptr); }}")
    L.append("")
    L.append(f"void {name}Editor::paint(juce::Graphics& g)")
    L.append("{")
    L.append("    g.fillAll(juce::Colour(0xff1a1a2e));")
    L.append("    g.setColour(juce::Colour(0xffe0e0e0));")
    L.append("    g.setFont(16.0f);")
    L.append(f'    g.drawText("{name}", 0, 0, getWidth(), TITLE_H, juce::Justification::centred);')
    L.append("}")
    L.append("")
    L.append(f"void {name}Editor::resized()")
    L.append("{")
    L.append("    stepGrid.setBounds(0, TITLE_H, getWidth(), getHeight() - TITLE_H);")
    L.append("}")
    L.append("")
    return "\n".join(L)


def gen_editor_h(spec: dict) -> str:
    name = spec["plugin"]["name"]
    L = []
    L.append("#pragma once")
    L.append("#include <JuceHeader.h>")
    L.append(f'#include "PluginProcessor.h"')
    L.append('#include "ui/SpaceLookAndFeel.h"')
    L.append('#include "ui/StepGrid.h"')
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
    L.append("    StepGrid stepGrid;")
    L.append(f"    JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR({name}Editor)")
    L.append("};")
    L.append("")
    return "\n".join(L)


def gen_param_panel_h() -> str:
    return '''#pragma once
#include <JuceHeader.h>

struct ParamKnobGroup
{
    static constexpr int MAX_PARAMS = 6;
    struct Entry {
        std::unique_ptr<juce::Slider> knob;
        std::unique_ptr<juce::AudioProcessorValueTreeState::SliderAttachment> attachment;
        juce::String label;
    };
    std::array<Entry, MAX_PARAMS> entries;
    int count = 0;

    void add(juce::AudioProcessorValueTreeState& apvts,
             const juce::String& paramId, const juce::String& label,
             juce::Component& parent)
    {
        if (count >= MAX_PARAMS) return;
        auto& e = entries[count++];
        e.label = label;
        e.knob = std::make_unique<juce::Slider>(
            juce::Slider::RotaryHorizontalVerticalDrag, juce::Slider::NoTextBox);
        e.knob->setTooltip(label);
        e.attachment = std::make_unique<juce::AudioProcessorValueTreeState::SliderAttachment>(
            apvts, paramId, *e.knob);
        parent.addAndMakeVisible(*e.knob);
    }
};
'''


def gen_stepgrid_h(spec: dict) -> str:
    prefix = spec["plugin"]["prefix"]
    channels = spec["channels"]
    pitched = [(i, c) for i, c in enumerate(channels) if c["type"] == "pitched"]
    n = len(channels)
    bass_extra = f"static constexpr int BASS_EXTRA = SUB_ROW_H * 2;" if pitched else ""
    L = []
    L.append("#pragma once")
    L.append("#include <JuceHeader.h>")
    L.append('#include "../Sequencer.h"')
    L.append('#include "../core/VoiceBank.h"')
    L.append('#include "ParamPanel.h"')
    L.append("")
    L.append("class StepGrid : public juce::Component, public juce::Timer")
    L.append("{")
    L.append("public:")
    L.append("    StepGrid(Sequencer& seq, VoiceBank& voices,")
    L.append("             juce::AudioProcessorValueTreeState& apvts,")
    L.append("             std::atomic<float>& bpm);")
    L.append("    ~StepGrid() override;")
    L.append("    void paint(juce::Graphics& g) override;")
    L.append("    void resized() override;")
    L.append("    void mouseDown(const juce::MouseEvent& e) override;")
    L.append("    void timerCallback() override;")
    L.append("")
    L.append(f"    static constexpr int NUM_CH = {n};")
    L.append("    static constexpr int VISIBLE_STEPS = 16;")
    L.append("    static constexpr int LABEL_W = 52;")
    L.append("    static constexpr int STEP_W = 34;")
    L.append("    static constexpr int STEP_H = 28;")
    L.append("    static constexpr int ROW_H = 48;")
    L.append("    static constexpr int PKNOB_SZ = 28;")
    L.append("    static constexpr int MAX_PKNOBS = 6;")
    L.append("    static constexpr int PKNOB_GAP = 2;")
    L.append("    static constexpr int PARAM_AREA_W = MAX_PKNOBS * (PKNOB_SZ + PKNOB_GAP);")
    L.append("    static constexpr int KNOB_W = 28;")
    L.append("    static constexpr int MS_BTN_W = 20;")
    L.append("    static constexpr int BTN_W = 28;")
    L.append("    static constexpr int HEADER_H = 24;")
    L.append("    static constexpr int PAD = 3;")
    L.append("    static constexpr int SUB_ROW_H = 16;")
    if pitched:
        L.append("    static constexpr int BASS_EXTRA = SUB_ROW_H * 2;")
    L.append("")
    L.append("    static int rowY(int ch) {")
    L.append("        int y = HEADER_H;")
    L.append("        for (int i = 0; i < ch; ++i) {")
    L.append("            y += ROW_H;")
    if pitched:
        L.append(f"            if (i >= {pitched[0][0]}) y += BASS_EXTRA;")
    L.append("        }")
    L.append("        return y;")
    L.append("    }")
    L.append("")
    L.append("private:")
    L.append("    Sequencer& sequencer;")
    L.append("    VoiceBank& voiceBank;")
    L.append("    std::atomic<float>& bpmRef;")
    L.append(f"    std::array<std::unique_ptr<juce::Slider>, {n}> volKnobs;")
    L.append(f"    std::array<std::unique_ptr<juce::AudioProcessorValueTreeState::SliderAttachment>, {n}> volAtt;")
    L.append(f"    std::array<std::unique_ptr<juce::Slider>, {n}> panKnobs;")
    L.append(f"    std::array<std::unique_ptr<juce::AudioProcessorValueTreeState::SliderAttachment>, {n}> panAtt;")
    L.append(f"    std::array<juce::TextButton, {n}> clrBtns, rndBtns, muteBtns;")
    L.append(f"    std::array<ParamKnobGroup, {n}> chParams;")
    L.append(f"    std::array<int, {n}> lastStep {{}};")
    L.append("    juce::Rectangle<int> stepRect(int ch, int vs) const;")
    L.append("    std::pair<int,int> hitTest(int x, int y) const;")
    L.append("    JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR(StepGrid)")
    L.append("};")
    L.append("")
    return "\n".join(L)


def gen_stepgrid_cpp(spec: dict) -> str:
    prefix = spec["plugin"]["prefix"]
    channels = spec["channels"]
    voices = spec["voices"]
    n = len(channels)
    pitched_indices = [i for i, c in enumerate(channels) if c["type"] == "pitched"]
    first_pi = pitched_indices[0] if pitched_indices else n

    # Channel colors
    colors = ["0xff00c896","0xffe8b838","0xff6ec6ff","0xffff6b6b",
              "0xffa855f7","0xffff9f43","0xff2ed573","0xffff6348"]

    L = []
    L.append('#include "StepGrid.h"')
    L.append('#include "../core/ParamIds.h"')
    L.append('#include "../core/BusLayout.h"')
    L.append("")
    # Channel names array
    names = ", ".join(f'"{c["name"]}"' for c in channels)
    L.append(f'static const char* CH_NAMES[] = {{ {names} }};')
    cols = ", ".join(colors[:n])
    L.append(f"static const juce::uint32 CH_COLS[] = {{ {cols} }};")
    L.append("")

    # Constructor
    L.append("StepGrid::StepGrid(Sequencer& seq, VoiceBank& voices,")
    L.append("                   juce::AudioProcessorValueTreeState& apvts,")
    L.append("                   std::atomic<float>& bpm)")
    L.append("    : sequencer(seq), voiceBank(voices), bpmRef(bpm)")
    L.append("{")
    L.append("    lastStep.fill(-1);")
    L.append(f"    for (int ch = 0; ch < {n}; ++ch) {{")
    L.append("        volKnobs[ch] = std::make_unique<juce::Slider>(")
    L.append("            juce::Slider::RotaryHorizontalVerticalDrag, juce::Slider::NoTextBox);")
    L.append("        volAtt[ch] = std::make_unique<juce::AudioProcessorValueTreeState::SliderAttachment>(")
    L.append("            apvts, ParamId::vol(ch), *volKnobs[ch]);")
    L.append("        addAndMakeVisible(*volKnobs[ch]);")
    L.append("")
    L.append("        panKnobs[ch] = std::make_unique<juce::Slider>(")
    L.append("            juce::Slider::RotaryHorizontalVerticalDrag, juce::Slider::NoTextBox);")
    L.append("        panAtt[ch] = std::make_unique<juce::AudioProcessorValueTreeState::SliderAttachment>(")
    L.append("            apvts, ParamId::pan(ch), *panKnobs[ch]);")
    L.append("        addAndMakeVisible(*panKnobs[ch]);")
    L.append("")
    L.append('        clrBtns[ch].setButtonText("CLR");')
    L.append("        clrBtns[ch].onClick = [this, ch] { sequencer.clearChannel(ch); repaint(); };")
    L.append("        addAndMakeVisible(clrBtns[ch]);")
    L.append("")
    L.append('        rndBtns[ch].setButtonText("RND");')
    L.append("        rndBtns[ch].onClick = [this, ch] { sequencer.randomizeChannel(ch); repaint(); };")
    L.append("        addAndMakeVisible(rndBtns[ch]);")
    L.append("")
    L.append('        muteBtns[ch].setButtonText("M");')
    L.append("        muteBtns[ch].setClickingTogglesState(true);")
    L.append("        muteBtns[ch].onClick = [this, ch] {")
    L.append("            sequencer.mute[ch].store(muteBtns[ch].getToggleState()); };")
    L.append("        addAndMakeVisible(muteBtns[ch]);")
    L.append("    }")
    L.append("")

    # Add per-channel parameter knobs
    for i, v in enumerate(voices):
        vupper = v["name"].upper()
        for p in v["params"]:
            pid = f"ParamId::{vupper}_{p.upper()}"
            label = f'"{p}"'
            L.append(f"    chParams[{i}].add(apvts, {pid}, {label}, *this);")

    L.append("")
    L.append("    startTimerHz(20);")
    L.append("}")
    L.append("")
    L.append("StepGrid::~StepGrid() { stopTimer(); }")
    L.append("")

    # stepRect
    L.append("juce::Rectangle<int> StepGrid::stepRect(int ch, int vs) const")
    L.append("{")
    L.append("    int x = PAD + LABEL_W + vs * STEP_W;")
    L.append("    int y = rowY(ch) + (ROW_H - STEP_H) / 2;")
    L.append("    return { x, y, STEP_W - 1, STEP_H - 1 };")
    L.append("}")
    L.append("")

    # hitTest
    L.append("std::pair<int,int> StepGrid::hitTest(int x, int y) const")
    L.append("{")
    L.append(f"    for (int ch = 0; ch < {n}; ++ch) {{")
    L.append("        int ry = rowY(ch);")
    L.append("        if (y >= ry && y < ry + ROW_H) {")
    L.append("            int sx = x - PAD - LABEL_W;")
    L.append("            if (sx >= 0 && sx < VISIBLE_STEPS * STEP_W)")
    L.append("                return { ch, sx / STEP_W };")
    L.append("        }")
    L.append("    }")
    L.append("    return { -1, -1 };")
    L.append("}")
    L.append("")

    # mouseDown
    L.append("void StepGrid::mouseDown(const juce::MouseEvent& e)")
    L.append("{")
    L.append("    auto [ch, step] = hitTest(e.x, e.y);")
    L.append("    if (ch < 0) return;")
    L.append("    sequencer.toggleStep(ch, step);")
    L.append("    if (sequencer.getStep(ch, step)) voiceBank.requestTrigger(ch);")
    L.append("    repaint();")
    L.append("}")
    L.append("")

    # timerCallback
    L.append("void StepGrid::timerCallback()")
    L.append("{")
    L.append("    bool dirty = false;")
    L.append(f"    for (int ch = 0; ch < {n}; ++ch) {{")
    L.append("        int s = sequencer.currentSteps[ch].load(std::memory_order_relaxed);")
    L.append("        if (s != lastStep[ch]) { lastStep[ch] = s; dirty = true; }")
    L.append("    }")
    L.append("    if (dirty) repaint();")
    L.append("}")
    L.append("")

    # resized
    L.append("void StepGrid::resized()")
    L.append("{")
    L.append(f"    for (int ch = 0; ch < {n}; ++ch) {{")
    L.append("        int ry = rowY(ch);")
    L.append("        int x = PAD + LABEL_W + VISIBLE_STEPS * STEP_W + PAD;")
    L.append("        // Param knobs")
    L.append("        for (int k = 0; k < chParams[ch].count; ++k) {")
    L.append("            chParams[ch].entries[k].knob->setBounds(")
    L.append("                x + k * (PKNOB_SZ + PKNOB_GAP), ry + (ROW_H - PKNOB_SZ)/2,")
    L.append("                PKNOB_SZ, PKNOB_SZ);")
    L.append("        }")
    L.append("        int rx = x + PARAM_AREA_W + PAD;")
    L.append("        volKnobs[ch]->setBounds(rx, ry + (ROW_H-KNOB_W)/2, KNOB_W, KNOB_W);")
    L.append("        rx += KNOB_W + PAD;")
    L.append("        panKnobs[ch]->setBounds(rx, ry + (ROW_H-KNOB_W)/2, KNOB_W, KNOB_W);")
    L.append("        rx += KNOB_W + PAD;")
    L.append("        muteBtns[ch].setBounds(rx, ry + 4, MS_BTN_W, ROW_H/2 - 4);")
    L.append("        rx += MS_BTN_W + PAD;")
    L.append("        clrBtns[ch].setBounds(rx, ry + 2, BTN_W, ROW_H/2 - 2);")
    L.append("        rndBtns[ch].setBounds(rx, ry + ROW_H/2, BTN_W, ROW_H/2 - 2);")
    L.append("    }")
    L.append("}")
    L.append("")

    # paint
    L.append("void StepGrid::paint(juce::Graphics& g)")
    L.append("{")
    L.append("    g.fillAll(juce::Colour(0xff0d0d1a));")
    L.append("")
    L.append("    // Header")
    L.append("    g.setColour(juce::Colour(0xff2a2a3e));")
    L.append("    g.fillRect(0, 0, getWidth(), HEADER_H);")
    L.append("    g.setColour(juce::Colour(0xffaaaaaa));")
    L.append("    g.setFont(11.0f);")
    L.append("    for (int s = 0; s < VISIBLE_STEPS; ++s) {")
    L.append("        int x = PAD + LABEL_W + s * STEP_W;")
    L.append('        g.drawText(juce::String(s+1), x, 2, STEP_W, HEADER_H - 4, juce::Justification::centred);')
    L.append("    }")
    L.append("    float bpm = bpmRef.load(std::memory_order_relaxed);")
    L.append('    g.drawText(juce::String(bpm, 1) + " BPM", getWidth() - 100, 2, 96, HEADER_H - 4,')
    L.append("               juce::Justification::centredRight);")
    L.append("")

    # Draw rows
    L.append(f"    for (int ch = 0; ch < {n}; ++ch) {{")
    L.append("        int ry = rowY(ch);")
    L.append("        juce::Colour chCol(CH_COLS[ch]);")
    L.append("")
    L.append("        // Channel color strip")
    L.append("        g.setColour(chCol.withAlpha(0.15f));")
    L.append("        g.fillRect(0, ry, PAD + 2, ROW_H);")
    L.append("")
    L.append("        // Label")
    L.append("        g.setColour(chCol);")
    L.append("        g.setFont(12.0f);")
    L.append("        g.drawText(CH_NAMES[ch], PAD + 4, ry, LABEL_W - 8, ROW_H, juce::Justification::centredLeft);")
    L.append("")
    L.append("        // Steps")
    L.append("        int curStep = sequencer.currentSteps[ch].load(std::memory_order_relaxed);")
    L.append("        for (int s = 0; s < VISIBLE_STEPS; ++s) {")
    L.append("            auto r = stepRect(ch, s);")
    L.append("            bool on = sequencer.getStep(ch, s);")
    L.append("            bool playing = (s == curStep) && sequencer.isPlaying.load();")
    L.append("")
    L.append("            // Beat grouping background")
    L.append("            if (s % 4 < 2)")
    L.append("                g.setColour(juce::Colour(0xff1a1a2e));")
    L.append("            else")
    L.append("                g.setColour(juce::Colour(0xff151528));")
    L.append("            g.fillRect(r);")
    L.append("")
    L.append("            if (on) {")
    L.append("                g.setColour(playing ? chCol : chCol.withAlpha(0.7f));")
    L.append("                g.fillRoundedRectangle(r.toFloat().reduced(2), 3.0f);")
    L.append("            }")
    L.append("            if (playing && !on) {")
    L.append("                g.setColour(juce::Colours::white.withAlpha(0.15f));")
    L.append("                g.fillRect(r);")
    L.append("            }")
    L.append("")
    L.append("            // Cell border")
    L.append("            g.setColour(juce::Colour(0xff333355));")
    L.append("            g.drawRect(r);")
    L.append("        }")
    L.append("")
    L.append("        // Param knob labels")
    L.append("        g.setFont(8.0f);")
    L.append("        g.setColour(juce::Colour(0xff888888));")
    L.append("        int px = PAD + LABEL_W + VISIBLE_STEPS * STEP_W + PAD;")
    L.append("        for (int k = 0; k < chParams[ch].count; ++k) {")
    L.append("            g.drawText(chParams[ch].entries[k].label,")
    L.append("                       px + k * (PKNOB_SZ + PKNOB_GAP), ry + ROW_H - 12,")
    L.append("                       PKNOB_SZ, 10, juce::Justification::centred);")
    L.append("        }")
    L.append("")
    L.append("        // Row separator")
    L.append("        g.setColour(juce::Colour(0xff222244));")
    L.append("        g.drawHorizontalLine(ry + ROW_H - 1, 0.0f, static_cast<float>(getWidth()));")
    L.append("    }")
    L.append("}")
    L.append("")
    return "\n".join(L)


