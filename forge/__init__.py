"""forge — Modular VST project generator.

Modules:
    spec        Spec loading, archetype routing
    themes      UI color themes + LookAndFeel
    gen_cmake   CMakeLists.txt
    gen_core    Bus layout, params, voice bank, MIDI router
    gen_audio   Sequencer, transport sync, processor
    gen_ui      Editor, StepGrid, ParamPanel
"""

import shutil
from pathlib import Path

from .spec import load_spec, SKELETON, DSPLIB, ARCHETYPE_MAP, route_archetype, FORGE_DIR
from .themes import gen_look_and_feel
from .gen_cmake import gen_cmake
from .gen_core import (gen_bus_layout, gen_param_ids, gen_param_layout,
                       gen_param_layout_h, gen_voice_stub,
                       gen_voicebank_h, gen_voicebank_cpp, gen_midi_router)
from .gen_audio import (gen_sequencer_h, gen_transport_sync_h,
                        gen_processor_h, gen_processor_cpp)
from .gen_ui import (gen_editor_h, gen_editor_cpp,
                     gen_param_panel_h, gen_stepgrid_h, gen_stepgrid_cpp)


def generate(spec_path: str, output_dir: str):
    """Main entry: spec.json → full JUCE project."""
    spec = load_spec(spec_path)
    out = Path(output_dir)
    name = spec["plugin"]["name"]

    print(f"🔨 VST Forge — generating {name} → {out}")

    for d in ["src", "src/core", "src/voices", "src/ui"]:
        (out / d).mkdir(parents=True, exist_ok=True)

    # Static files
    shutil.copy(FORGE_DIR / "dsplib" / "DspConstants.h",
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
        "src/ui/SpaceLookAndFeel.h": gen_look_and_feel(spec),
        "src/ui/ParamPanel.h": gen_param_panel_h(),
        "src/ui/StepGrid.h": gen_stepgrid_h(spec),
        "src/ui/StepGrid.cpp": gen_stepgrid_cpp(spec),
    }

    # Voices: production DSP from dsplib or stub fallback
    seen_classes = set()
    for v, c in zip(spec["voices"], spec["channels"]):
        cls = v.get("class", f"{v['name']}Voice")
        if cls in seen_classes:
            continue
        seen_classes.add(cls)

        archetype = route_archetype(v, c)
        dsp_file = DSPLIB / ARCHETYPE_MAP.get(archetype, "") if archetype else None

        if dsp_file and dsp_file.exists():
            content = dsp_file.read_text()
            arch_class = {"kick": "KickVoice", "snare": "SnareVoice",
                          "hats": "HatsVoice", "bass303": "BassVoice",
                          "tom": "TomVoice", "perc": "PercVoice",
                          "clap": "ClapVoice", "pad": "PadVoice",
                          "lead": "LeadVoice", "pluck": "PluckVoice",
                          "organ": "OrganVoice", "fm_synth": "FMSynthVoice",
                          "noise": "NoiseVoice", "string": "StringVoice",
                          "brass": "BrassVoice", "sub_bass": "SubBassVoice"}.get(archetype)
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
