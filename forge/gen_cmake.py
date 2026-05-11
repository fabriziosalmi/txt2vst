"""forge.gen_cmake — CMakeLists.txt generator."""

import textwrap


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

        include(FetchContent)
        FetchContent_Declare(JUCE
            GIT_REPOSITORY https://github.com/juce-framework/JUCE.git
            GIT_TAG        8.0.4
            GIT_SHALLOW    TRUE
        )
        FetchContent_MakeAvailable(JUCE)

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
