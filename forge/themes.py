"""forge.themes — UI theme presets and LookAndFeel generator."""

THEMES = {
    # ── Dark ──────────────────────────────────────────────────────────────────
    "midnight": {
        "bg": "0xff0d0d1a", "surface": "0xff1a1a2e", "header": "0xff2a2a3e",
        "accent": "0xff00c896", "text": "0xffe0e0e0", "muted": "0xff666688",
        "grid_a": "0xff1a1a2e", "grid_b": "0xff151528", "border": "0xff333355",
        "font": "Arial",
    },
    "void": {
        "bg": "0xff050508", "surface": "0xff0a0a10", "header": "0xff121218",
        "accent": "0xff8888ff", "text": "0xffb0b0c0", "muted": "0xff444455",
        "grid_a": "0xff0c0c14", "grid_b": "0xff08080e", "border": "0xff222233",
        "font": "Arial",
    },
    "obsidian": {
        "bg": "0xff080808", "surface": "0xff141414", "header": "0xff1e1e1e",
        "accent": "0xffa0a0a0", "text": "0xffc8c8c8", "muted": "0xff585858",
        "grid_a": "0xff161616", "grid_b": "0xff101010", "border": "0xff2a2a2a",
        "font": "Helvetica Neue",
    },

    # ── Neon / Glow ───────────────────────────────────────────────────────────
    "acid": {
        "bg": "0xff0a0f0a", "surface": "0xff142014", "header": "0xff1e301e",
        "accent": "0xff39ff14", "text": "0xffc0ffc0", "muted": "0xff4a6a4a",
        "grid_a": "0xff162016", "grid_b": "0xff121c12", "border": "0xff2a4a2a",
        "font": "Courier New",
    },
    "neon": {
        "bg": "0xff0a0010", "surface": "0xff180028", "header": "0xff250040",
        "accent": "0xffff00ff", "text": "0xffffe0ff", "muted": "0xff886688",
        "grid_a": "0xff1c0030", "grid_b": "0xff160028", "border": "0xff442266",
        "font": "Arial",
    },
    "glow": {
        "bg": "0xff060612", "surface": "0xff0e0e22", "header": "0xff161636",
        "accent": "0xff00ffcc", "text": "0xffd0fff0", "muted": "0xff448866",
        "grid_a": "0xff101026", "grid_b": "0xff0c0c1e", "border": "0xff224444",
        "font": "Arial",
    },
    "strobe": {
        "bg": "0xff0a0a0a", "surface": "0xff151515", "header": "0xff202020",
        "accent": "0xffffff00", "text": "0xffffffd0", "muted": "0xff888844",
        "grid_a": "0xff181818", "grid_b": "0xff121212", "border": "0xff444400",
        "font": "Courier New",
    },
    "matrix": {
        "bg": "0xff000a00", "surface": "0xff001400", "header": "0xff002000",
        "accent": "0xff00ff41", "text": "0xff88ff88", "muted": "0xff226622",
        "grid_a": "0xff001800", "grid_b": "0xff001000", "border": "0xff003800",
        "font": "Courier New",
    },

    # ── Warm / Organic ────────────────────────────────────────────────────────
    "ember": {
        "bg": "0xff140a08", "surface": "0xff261410", "header": "0xff3a201a",
        "accent": "0xffff6b35", "text": "0xffffe0d0", "muted": "0xff886655",
        "grid_a": "0xff281814", "grid_b": "0xff201210", "border": "0xff553322",
        "font": "Arial",
    },
    "solar": {
        "bg": "0xff100c04", "surface": "0xff201808", "header": "0xff302410",
        "accent": "0xffffc107", "text": "0xfffff0d0", "muted": "0xff887744",
        "grid_a": "0xff241c0c", "grid_b": "0xff1c1608", "border": "0xff554422",
        "font": "Arial",
    },
    "copper": {
        "bg": "0xff0e0a08", "surface": "0xff1c1410", "header": "0xff2c2018",
        "accent": "0xffcc7744", "text": "0xffddc8b0", "muted": "0xff776655",
        "grid_a": "0xff1e1612", "grid_b": "0xff18120e", "border": "0xff443322",
        "font": "Georgia",
    },
    "candy": {
        "bg": "0xff120810", "surface": "0xff221018", "header": "0xff341828",
        "accent": "0xffff66aa", "text": "0xffffd0e8", "muted": "0xff885566",
        "grid_a": "0xff26141c", "grid_b": "0xff1e1016", "border": "0xff553344",
        "font": "Arial",
    },

    # ── Cold / Metallic ───────────────────────────────────────────────────────
    "frost": {
        "bg": "0xff080c14", "surface": "0xff101828", "header": "0xff1a2840",
        "accent": "0xff5ebaff", "text": "0xffd0e8ff", "muted": "0xff556688",
        "grid_a": "0xff121e30", "grid_b": "0xff0e1828", "border": "0xff223355",
        "font": "Arial",
    },
    "chrome": {
        "bg": "0xff0c0c10", "surface": "0xff18181e", "header": "0xff24242c",
        "accent": "0xffc0c0d0", "text": "0xffe8e8f0", "muted": "0xff707080",
        "grid_a": "0xff1c1c22", "grid_b": "0xff14141a", "border": "0xff38383e",
        "font": "Helvetica Neue",
    },
    "arctic": {
        "bg": "0xff040810", "surface": "0xff0a1420", "header": "0xff122030",
        "accent": "0xff88ddff", "text": "0xffc0e0ff", "muted": "0xff446688",
        "grid_a": "0xff0e1824", "grid_b": "0xff0a121c", "border": "0xff1a3355",
        "font": "Arial",
    },

    # ── Character / Retro ─────────────────────────────────────────────────────
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
    "terminal": {
        "bg": "0xff000000", "surface": "0xff0a0a0a", "header": "0xff141414",
        "accent": "0xff33ff33", "text": "0xff33ff33", "muted": "0xff116611",
        "grid_a": "0xff0e0e0e", "grid_b": "0xff080808", "border": "0xff1a3a1a",
        "font": "Courier New",
    },
    "hologram": {
        "bg": "0xff060818", "surface": "0xff0e1228", "header": "0xff161a38",
        "accent": "0xff44eeff", "text": "0xffc0f0ff", "muted": "0xff336688",
        "grid_a": "0xff10162c", "grid_b": "0xff0c1024", "border": "0xff224466",
        "font": "Arial",
    },

    # ── Bright / Contrasted ───────────────────────────────────────────────────
    "white": {
        "bg": "0xfff0f0f4", "surface": "0xffffffff", "header": "0xffe8e8ec",
        "accent": "0xff2266cc", "text": "0xff1a1a2e", "muted": "0xff888899",
        "grid_a": "0xfff4f4f8", "grid_b": "0xffeaeaee", "border": "0xffc8c8d0",
        "font": "Helvetica Neue",
    },
    "cream": {
        "bg": "0xfff5f0e8", "surface": "0xfffffaf4", "header": "0xffebe4d8",
        "accent": "0xff996633", "text": "0xff2a2218", "muted": "0xff998877",
        "grid_a": "0xfff8f2ea", "grid_b": "0xfff0e8e0", "border": "0xffd0c8b8",
        "font": "Georgia",
    },
    "blood": {
        "bg": "0xff100404", "surface": "0xff200a0a", "header": "0xff301010",
        "accent": "0xffff2222", "text": "0xffffc0c0", "muted": "0xff884444",
        "grid_a": "0xff240c0c", "grid_b": "0xff1c0808", "border": "0xff552222",
        "font": "Arial",
    },
    "lavender": {
        "bg": "0xff0c0810", "surface": "0xff181420", "header": "0xff241e30",
        "accent": "0xffaa88ff", "text": "0xffe0d8f0", "muted": "0xff776688",
        "grid_a": "0xff1c1624", "grid_b": "0xff14101c", "border": "0xff332855",
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
