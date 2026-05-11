"""forge.themes — UI theme presets and LookAndFeel generator."""

THEMES = {
    "midnight": {
        "bg": "0xff0d0d1a", "surface": "0xff1a1a2e", "header": "0xff2a2a3e",
        "accent": "0xff00c896", "text": "0xffe0e0e0", "muted": "0xff666688",
        "grid_a": "0xff1a1a2e", "grid_b": "0xff151528", "border": "0xff333355",
        "font": "Arial",
    },
    "acid": {
        "bg": "0xff0a0f0a", "surface": "0xff142014", "header": "0xff1e301e",
        "accent": "0xff39ff14", "text": "0xffc0ffc0", "muted": "0xff4a6a4a",
        "grid_a": "0xff162016", "grid_b": "0xff121c12", "border": "0xff2a4a2a",
        "font": "Courier New",
    },
    "ember": {
        "bg": "0xff140a08", "surface": "0xff261410", "header": "0xff3a201a",
        "accent": "0xffff6b35", "text": "0xffffe0d0", "muted": "0xff886655",
        "grid_a": "0xff281814", "grid_b": "0xff201210", "border": "0xff553322",
        "font": "Arial",
    },
    "frost": {
        "bg": "0xff080c14", "surface": "0xff101828", "header": "0xff1a2840",
        "accent": "0xff5ebaff", "text": "0xffd0e8ff", "muted": "0xff556688",
        "grid_a": "0xff121e30", "grid_b": "0xff0e1828", "border": "0xff223355",
        "font": "Arial",
    },
    "neon": {
        "bg": "0xff0a0010", "surface": "0xff180028", "header": "0xff250040",
        "accent": "0xffff00ff", "text": "0xffffe0ff", "muted": "0xff886688",
        "grid_a": "0xff1c0030", "grid_b": "0xff160028", "border": "0xff442266",
        "font": "Arial",
    },
    "vapor": {
        "bg": "0xff0a0818", "surface": "0xff1a1030", "header": "0xff2a1848",
        "accent": "0xffff71ce", "text": "0xffffe0f0", "muted": "0xff886688",
        "grid_a": "0xff1c1234", "grid_b": "0xff16102c", "border": "0xff442266",
        "font": "Arial",
    },
    "industrial": {
        "bg": "0xff0c0c0c", "surface": "0xff1a1a1a", "header": "0xff2a2a2a",
        "accent": "0xffff8800", "text": "0xffd0d0d0", "muted": "0xff666666",
        "grid_a": "0xff1e1e1e", "grid_b": "0xff181818", "border": "0xff3a3a3a",
        "font": "Courier New",
    },
    "solar": {
        "bg": "0xff100c04", "surface": "0xff201808", "header": "0xff302410",
        "accent": "0xffffc107", "text": "0xfffff0d0", "muted": "0xff887744",
        "grid_a": "0xff241c0c", "grid_b": "0xff1c1608", "border": "0xff554422",
        "font": "Arial",
    },
}


def get_theme(spec: dict) -> dict:
    """Resolve theme from spec. Accepts preset name or custom dict."""
    theme_raw = spec.get("plugin", {}).get("theme", "midnight")
    if isinstance(theme_raw, str):
        return THEMES.get(theme_raw, THEMES["midnight"])
    base = dict(THEMES["midnight"])
    base.update(theme_raw)
    return base


def gen_look_and_feel(spec: dict) -> str:
    theme = get_theme(spec)
    L = []
    L.append("#pragma once")
    L.append("#include <JuceHeader.h>")
    L.append("")
    L.append("class SpaceLookAndFeel : public juce::LookAndFeel_V4")
    L.append("{")
    L.append("public:")
    L.append(f'    SpaceLookAndFeel() {{ setDefaultSansSerifTypefaceName("{theme["font"]}"); }}')
    L.append("")
    L.append("    // Theme colors")
    L.append(f"    static constexpr juce::uint32 BG       = {theme['bg']};")
    L.append(f"    static constexpr juce::uint32 SURFACE  = {theme['surface']};")
    L.append(f"    static constexpr juce::uint32 HEADER   = {theme['header']};")
    L.append(f"    static constexpr juce::uint32 ACCENT   = {theme['accent']};")
    L.append(f"    static constexpr juce::uint32 TEXT     = {theme['text']};")
    L.append(f"    static constexpr juce::uint32 MUTED    = {theme['muted']};")
    L.append(f"    static constexpr juce::uint32 GRID_A   = {theme['grid_a']};")
    L.append(f"    static constexpr juce::uint32 GRID_B   = {theme['grid_b']};")
    L.append(f"    static constexpr juce::uint32 BORDER   = {theme['border']};")
    L.append("};")
    L.append("")
    return "\n".join(L)
