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

from .spec import load_spec, DSPLIB, ARCHETYPE_MAP, route_archetype, FORGE_DIR
from .themes import gen_look_and_feel
from .gen_cmake import gen_cmake
from .gen_core import (gen_bus_layout, gen_param_ids, gen_param_layout,
                       gen_param_layout_h, gen_voice_stub,
                       gen_voicebank_h, gen_voicebank_cpp, gen_midi_router)
from .gen_audio import (gen_sequencer_h, gen_transport_sync_h,
                        gen_processor_h, gen_processor_cpp)
from .gen_ui import (gen_editor_h, gen_editor_cpp,
                     gen_param_panel_h, gen_stepgrid_h, gen_stepgrid_cpp)


def _gen_build_sh(name: str) -> str:
    """Generate a portable build.sh convenience script."""
    return f"""#!/usr/bin/env bash
set -euo pipefail

echo "=== Building {name} ==="

cmake -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build --config Release -j$(nproc 2>/dev/null || sysctl -n hw.ncpu 2>/dev/null || echo 2)

echo ""
echo "Build complete."
echo "VST3/AU plugin installed to default locations."
"""


def generate(spec_path: str, output_dir: str):
    """Main entry: spec.json -> full JUCE project."""
    spec = load_spec(spec_path)
    out = Path(output_dir)
    name = spec["plugin"]["name"]

    # F1: Validate voices/channels parity
    if len(spec["voices"]) != len(spec["channels"]):
        raise ValueError(
            f"voices/channels mismatch: {len(spec['voices'])} voices vs "
            f"{len(spec['channels'])} channels")

    print(f"VST Forge: generating {name} -> {out}")

    # F6: Clean output dir to avoid stale files from previous generations
    if out.exists():
        shutil.rmtree(out)

    for d in ["src", "src/core", "src/voices", "src/ui"]:
        (out / d).mkdir(parents=True, exist_ok=True)

    # Copy DspConstants.h to src/voices/ (voice headers include it relatively)
    shutil.copy(FORGE_DIR / "dsplib" / "DspConstants.h",
                out / "src" / "voices" / "DspConstants.h")

    # Master chain (optional)
    mastering = spec["features"].get("mastering")
    if mastering:
        (out / "src" / "fx").mkdir(parents=True, exist_ok=True)
        shutil.copy(FORGE_DIR / "dsplib" / "fx" / "master_chain.h",
                    out / "src" / "fx" / "MasterChain.h")
        # FX needs DspConstants too (master_chain.h includes it relatively)
        shutil.copy(FORGE_DIR / "dsplib" / "DspConstants.h",
                    out / "src" / "fx" / "DspConstants.h")
        print(f"  Master chain: {mastering}")

    # Generated files
    files = {
        "CMakeLists.txt": gen_cmake(spec),
        "build.sh": _gen_build_sh(name),  # F3: CLI build script
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
        arch_info = ARCHETYPE_MAP.get(archetype) if archetype else None
        dsp_file = DSPLIB / arch_info["file"] if arch_info else None

        if dsp_file and dsp_file.exists():
            content = dsp_file.read_text()
            arch_class = arch_info["class"]
            # F2: Full class rename (covers ctor, dtor, all references)
            if arch_class != cls:
                content = content.replace(arch_class, cls)
            files[f"src/voices/{cls}.h"] = content
            print(f"  {cls} <- dsplib/{archetype}")
        else:
            v_copy = dict(v)
            v_copy["type"] = c["type"]
            files[f"src/voices/{cls}.h"] = gen_voice_stub(v_copy)
            print(f"  {cls} <- stub")

    # F5: Write all files with error handling
    written = 0
    for path, content in files.items():
        fp = out / path
        try:
            fp.write_text(content)
            written += 1
            if not path.startswith("src/voices/"):
                print(f"  + {path}")
        except OSError as e:
            print(f"  ERROR writing {path}: {e}")

    # Make build.sh executable
    build_sh = out / "build.sh"
    if build_sh.exists():
        build_sh.chmod(0o755)

    total_loc = sum(len(c.splitlines()) for c in files.values())
    print(f"\nGenerated {written}/{len(files)} files, ~{total_loc} LOC")

