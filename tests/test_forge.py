#!/usr/bin/env python3
"""Comprehensive test suite for the txt2vst forge pipeline.

Covers: prompt2spec parser, spec validation, archetype routing,
theme generation, CMake generation, and full pipeline integration.

Run: python -m pytest tests/test_forge.py -v
"""

import json
import os
import subprocess
import tempfile
from pathlib import Path

import pytest

# ── Imports ──────────────────────────────────────────────────────────────────

from prompt2spec import parse_prompt
from forge.spec import load_spec, const_name, route_archetype, ARCHETYPE_MAP
from forge.themes import THEMES, get_theme, gen_look_and_feel
from forge.gen_cmake import gen_cmake
from forge.gen_core import (gen_param_ids, gen_param_layout, gen_bus_layout,
                            gen_voicebank_h, gen_voicebank_cpp, gen_voice_stub)
from forge.gen_ui import gen_stepgrid_h, gen_stepgrid_cpp, gen_editor_h
from forge.gen_audio import gen_processor_h, gen_processor_cpp
from forge import generate


# ── Helpers ──────────────────────────────────────────────────────────────────

def make_spec(prompt: str) -> dict:
    return parse_prompt(prompt)


def generate_to_tmp(prompt: str) -> tuple[Path, dict]:
    """Generate a full project in a temp dir, return (path, spec)."""
    spec = make_spec(prompt)
    tmp = tempfile.mkdtemp(prefix="txt2vst_test_")
    sp = os.path.join(tmp, "spec.json")
    with open(sp, "w") as f:
        json.dump(spec, f)
    out = os.path.join(tmp, "Out")
    generate(sp, out)
    return Path(out), spec


# ============================================================================
# PROMPT2SPEC PARSER
# ============================================================================

class TestParser:
    """Tests for the NLP prompt parser."""

    def test_basic_drums(self):
        spec = make_spec("kick snare hats")
        drums = [c for c in spec["channels"] if c["type"] == "drum"]
        assert len(drums) == 3

    def test_basic_pitched(self):
        spec = make_spec("bass lead pad")
        pitched = [c for c in spec["channels"] if c["type"] == "pitched"]
        assert len(pitched) == 3

    def test_all_16_archetypes(self):
        prompt = ("kick snare hats tom perc clap bass_acid lead pad pluck "
                  "organ fm_synth noise string brass sub_bass")
        spec = make_spec(prompt)
        assert len(spec["voices"]) == 16

    def test_channel_count(self):
        spec = make_spec("4 channel drum machine")
        assert len(spec["channels"]) == 4

    def test_sequencer_detection(self):
        spec = make_spec("groovebox with step sequencer")
        assert spec["features"]["sequencer"] is True

    def test_swing_detection(self):
        spec = make_spec("shuffle groove drum machine")
        assert spec["features"]["swing"] is True

    def test_sidechain_detection(self):
        spec = make_spec("sidechain pump bass synth")
        assert spec["features"]["sidechain"] is True

    def test_fx_detection(self):
        spec = make_spec("drum machine with delay reverb")
        fx = spec["features"]["master_fx"]
        assert "delay" in fx
        assert "reverb" in fx

    def test_theme_detection_explicit(self):
        spec = make_spec("synth with neon theme")
        assert spec["plugin"].get("theme") == "neon"

    def test_theme_fallback_midnight(self):
        spec = make_spec("kick snare")
        assert spec["plugin"].get("theme") is None  # midnight = default, not stored

    def test_mastering_detection(self):
        spec = make_spec("punchy mastering drum machine kick snare")
        assert spec["features"].get("mastering") == "punch"

    def test_ui_size_1280(self):
        spec = make_spec("kick")
        assert spec["plugin"]["ui"] == [1280, 760]

    def test_no_drive_fallback(self):
        """drive was a phantom FX that doesn't exist."""
        spec = make_spec("kick snare hats clap bass_acid pad")
        assert "drive" not in spec["features"]["master_fx"]

    # ── False-positive guards ────────────────────────────────────────────

    def test_ambient_no_wet_mastering(self):
        """'ambient' is a pad alias, not a mastering preset."""
        spec = make_spec("ambient pad synth")
        assert spec["features"].get("mastering") is None

    def test_radioactive_no_radio(self):
        """'radioactive' should NOT trigger radio mastering."""
        spec = make_spec("radioactive synth lead")
        assert spec["features"].get("mastering") is None

    def test_ensemble_no_chorus_fx(self):
        """'ensemble' is a string voice alias, not chorus FX."""
        spec = make_spec("ensemble strings pad")
        assert "chorus" not in spec["features"]["master_fx"]

    def test_sub_bass_not_bass_acid(self):
        """sub_bass should route to sub_bass, not bass_acid."""
        spec = make_spec("sub_bass")
        assert any(v["name"] == "Sub_bass" or "sub" in v["name"].lower()
                    for v in spec["voices"])

    # ── Code generation safety ───────────────────────────────────────────

    def test_numeric_prefix_sanitized(self):
        """'808 machine' must not produce prefix starting with digit."""
        spec = make_spec("808 machine bass")
        prefix = spec["plugin"]["prefix"]
        assert prefix[0].isalpha(), f"prefix starts with digit: {prefix}"

    def test_code_always_4_chars(self):
        for prompt in ["FM", "AB", "X", "kick"]:
            code = make_spec(prompt)["plugin"]["code"]
            assert len(code) == 4, f"'{prompt}' -> code='{code}' ({len(code)} chars)"

    def test_no_emoji_in_output(self):
        """CLI output should have no emoji."""
        spec = make_spec("kick snare hats")
        output = json.dumps(spec)
        # Check no high Unicode chars (emoji range)
        for ch in output:
            assert ord(ch) < 0x1F600 or ord(ch) > 0x1F9FF


# ============================================================================
# SPEC VALIDATION
# ============================================================================

class TestSpecValidation:
    """Tests for spec.json loading and validation."""

    def test_missing_key_raises(self):
        with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as f:
            json.dump({"plugin": {}}, f)
            f.flush()
            with pytest.raises(ValueError, match="missing required key"):
                load_spec(f.name)
            os.unlink(f.name)

    def test_empty_channels_raises(self):
        spec = {"plugin": {}, "channels": [], "voices": [], "features": {}}
        with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as f:
            json.dump(spec, f)
            f.flush()
            with pytest.raises(ValueError, match="empty"):
                load_spec(f.name)
            os.unlink(f.name)

    def test_valid_spec_loads(self):
        spec = make_spec("kick snare")
        with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as f:
            json.dump(spec, f)
            f.flush()
            loaded = load_spec(f.name)
            assert loaded["plugin"]["name"]
            os.unlink(f.name)


# ============================================================================
# CONST NAME SANITIZATION
# ============================================================================

class TestConstName:

    def test_simple(self):
        assert const_name("Kick") == "KICK"

    def test_space(self):
        assert const_name("Bass 1") == "BASS_1"

    def test_hyphen(self):
        assert const_name("FM-Synth") == "FM_SYNTH"

    def test_dots(self):
        assert const_name("v2.0") == "V2_0"


# ============================================================================
# ARCHETYPE ROUTING
# ============================================================================

class TestArchetypeRouting:

    def test_all_16_archetypes_have_files(self):
        for arch_id, info in ARCHETYPE_MAP.items():
            assert "file" in info, f"{arch_id} missing 'file'"
            assert "class" in info, f"{arch_id} missing 'class'"

    def test_drum_routing_by_name(self):
        for name, expected in [("Kick", "kick"), ("Snare", "snare"),
                                ("Hats", "hats"), ("Tom", "tom"),
                                ("Clap", "clap"), ("Perc", "perc")]:
            r = route_archetype({"name": name, "params": ["tune", "decay"]},
                                {"type": "drum"})
            assert r == expected, f"{name} -> {r}"

    def test_pitched_routing_bass(self):
        r = route_archetype(
            {"name": "Acid", "params": ["cutoff", "reso", "envmod", "decay", "accent"]},
            {"type": "pitched"})
        assert r == "bass_acid"

    def test_pitched_routing_pad(self):
        r = route_archetype(
            {"name": "Pad", "params": ["cutoff", "reso", "attack", "release", "detune"]},
            {"type": "pitched"})
        assert r == "pad"

    def test_pitched_routing_lead(self):
        r = route_archetype(
            {"name": "Lead", "params": ["cutoff", "reso", "pw", "decay", "envmod"]},
            {"type": "pitched"})
        assert r == "lead"

    def test_pitched_routing_organ(self):
        r = route_archetype(
            {"name": "Organ", "params": ["decay", "rotary"]},
            {"type": "pitched"})
        assert r == "organ"

    def test_pitched_routing_fm(self):
        r = route_archetype(
            {"name": "FM", "params": ["ratio", "index", "decay", "feedback"]},
            {"type": "pitched"})
        assert r == "fm_synth"

    def test_pitched_routing_string(self):
        r = route_archetype(
            {"name": "String", "params": ["cutoff", "reso", "attack", "release", "detune"]},
            {"type": "pitched"})
        assert r == "pad"  # cutoff+reso+attack+release = pad by params

    def test_no_match_returns_none(self):
        r = route_archetype(
            {"name": "Unknown", "params": ["foo", "bar"]},
            {"type": "pitched"})
        assert r is None


# ============================================================================
# THEMES
# ============================================================================

class TestThemes:

    def test_theme_count(self):
        assert len(THEMES) == 23

    def test_all_themes_have_required_keys(self):
        required = {"bg", "surface", "header", "accent", "text",
                     "muted", "grid_a", "grid_b", "border", "font"}
        for name, theme in THEMES.items():
            missing = required - set(theme.keys())
            assert not missing, f"Theme '{name}' missing: {missing}"

    def test_all_colors_valid_hex(self):
        for name, theme in THEMES.items():
            for key in ["bg", "surface", "header", "accent", "text",
                        "muted", "grid_a", "grid_b", "border"]:
                val = theme[key]
                assert val.startswith("0xff"), f"{name}.{key}={val}"
                assert len(val) == 10, f"{name}.{key}={val} wrong length"

    def test_unknown_theme_fallback(self):
        theme = get_theme({"plugin": {"theme": "nonexistent"}})
        assert theme == THEMES["midnight"]

    def test_lookandfeel_has_setcolour(self):
        lnf = gen_look_and_feel({"plugin": {"name": "T", "theme": "neon"}})
        assert "setColour" in lnf
        assert "rotarySliderFillColourId" in lnf
        assert "buttonColourId" in lnf
        assert "TooltipWindow" in lnf

    def test_lookandfeel_has_constants(self):
        lnf = gen_look_and_feel({"plugin": {"name": "T", "theme": "acid"}})
        assert "ACCENT" in lnf
        assert "GRID_A" in lnf


# ============================================================================
# CMAKE GENERATION
# ============================================================================

class TestCMake:

    def test_fetchcontent_juce(self):
        spec = make_spec("kick snare")
        cmake = gen_cmake(spec)
        assert "FetchContent_Declare(JUCE" in cmake
        assert "8.0.4" in cmake

    def test_no_overloaded_virtual_warning(self):
        spec = make_spec("kick snare")
        cmake = gen_cmake(spec)
        assert "overloaded-virtual" not in cmake

    def test_compile_commands(self):
        spec = make_spec("kick snare")
        cmake = gen_cmake(spec)
        assert "CMAKE_EXPORT_COMPILE_COMMANDS" in cmake

    def test_plugin_code_in_cmake(self):
        spec = make_spec("kick snare")
        cmake = gen_cmake(spec)
        code = spec["plugin"]["code"]
        assert f"PLUGIN_CODE {code}" in cmake


# ============================================================================
# GENERATED CODE QUALITY
# ============================================================================

class TestGeneratedCode:

    def test_no_hitTest_in_stepgrid(self):
        spec = make_spec("kick snare hats bass")
        h = gen_stepgrid_h(spec)
        cpp = gen_stepgrid_cpp(spec)
        assert "hitTest" not in h
        assert "hitTest" not in cpp
        assert "cellAtPoint" in h
        assert "cellAtPoint" in cpp

    def test_std_array_not_vla(self):
        spec = make_spec("kick snare hats bass")
        cpp = gen_processor_cpp(spec)
        assert "std::array<float, STACK_MAX>" in cpp
        assert "float tmpL[STACK_MAX]" not in cpp

    def test_param_defaults_sensible(self):
        spec = make_spec("kick snare hats bass")
        layout = gen_param_layout(spec)
        # cutoff should default to 0.7, not 0.5
        assert "0.7f" in layout
        # reso should default to 0.25, not 0.5
        assert "0.25f" in layout

    def test_no_crossover_state(self):
        spec = make_spec("kick snare hats bass")
        h = gen_processor_h(spec)
        assert "CrossoverState" not in h

    def test_16_channel_colors(self):
        """All 16 voices should have distinct colors."""
        prompt = ("kick snare hats tom perc clap bass_acid lead pad pluck "
                  "organ fm_synth noise string brass sub_bass")
        spec = make_spec(prompt)
        cpp = gen_stepgrid_cpp(spec)
        # Count color entries
        assert cpp.count("0xff") >= 16


# ============================================================================
# FULL PIPELINE INTEGRATION
# ============================================================================

class TestPipeline:

    def test_basic_generation(self):
        out, spec = generate_to_tmp("kick snare hats acid bass")
        assert (out / "CMakeLists.txt").exists()
        assert (out / "build.sh").exists()
        assert (out / "src" / "PluginProcessor.cpp").exists()
        assert (out / "src" / "ui" / "StepGrid.cpp").exists()

    def test_build_sh_executable(self):
        out, _ = generate_to_tmp("kick snare")
        bs = out / "build.sh"
        assert bs.exists()
        assert os.access(bs, os.X_OK)

    def test_voices_channels_mismatch_raises(self):
        spec = make_spec("kick snare hats bass")
        spec["channels"] = spec["channels"][:2]  # force mismatch
        with tempfile.TemporaryDirectory() as tmp:
            sp = os.path.join(tmp, "spec.json")
            with open(sp, "w") as f:
                json.dump(spec, f)
            with pytest.raises(ValueError, match="mismatch"):
                generate(sp, os.path.join(tmp, "Out"))

    def test_stale_files_cleaned(self):
        out, _ = generate_to_tmp("kick snare")
        stale = out / "src" / "voices" / "StaleVoice.h"
        stale.write_text("stale")
        # Re-generate over same dir
        spec = make_spec("kick snare")
        with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as f:
            json.dump(spec, f)
            f.flush()
            generate(f.name, str(out))
            os.unlink(f.name)
        assert not stale.exists()

    def test_mastering_copies_master_chain(self):
        out, _ = generate_to_tmp("kick snare hats bass punchy mastering")
        assert (out / "src" / "fx" / "MasterChain.h").exists()
        assert (out / "src" / "fx" / "DspConstants.h").exists()

    def test_dsp_constants_in_voices(self):
        out, _ = generate_to_tmp("kick snare")
        assert (out / "src" / "voices" / "DspConstants.h").exists()

    def test_all_archetypes_route_to_dsplib(self):
        """Every archetype should use a real dsplib file, not a stub."""
        prompt = ("kick snare hats tom perc clap bass_acid lead pad pluck "
                  "organ fm_synth noise string brass sub_bass")
        out, spec = generate_to_tmp(prompt)
        voices_dir = out / "src" / "voices"
        voice_files = [f for f in voices_dir.iterdir()
                       if f.suffix == ".h" and f.name != "DspConstants.h"]
        assert len(voice_files) == 16, f"Expected 16 voices, got {len(voice_files)}"
        for vf in voice_files:
            content = vf.read_text()
            assert "Stub DSP" not in content, f"{vf.name} is a stub, not dsplib"

    def test_generated_file_count(self):
        out, _ = generate_to_tmp("kick snare hats bass")
        files = list(out.rglob("*"))
        cpp_files = [f for f in files if f.suffix in (".cpp", ".h")]
        assert len(cpp_files) >= 20  # ~22 typical

    def test_theme_applied_in_lookandfeel(self):
        out, _ = generate_to_tmp("kick snare neon theme")
        lnf = (out / "src" / "ui" / "SpaceLookAndFeel.h").read_text()
        assert "setColour" in lnf
        # Neon accent is 0xffff00ff
        assert "0xffff00ff" in lnf
