#pragma once
#include <cmath>
#include <algorithm>
#include "DspConstants.h"

// ── Master Chain — Final bus processor with character presets ─────────────────
// Sits after all voices + FX. Never clips, never ruins. Always clamped to safe levels.
// Presets: bypass, transparent, punch, wet, radio, distorted, wide
// CPU: ~10-20 ops/sample depending on preset

struct MasterChain
{
    enum Preset {
        BYPASS = 0,
        TRANSPARENT,   // Gentle limiter + light glue compression
        PUNCH,         // Transient emphasis + saturation + presence EQ
        WET,           // Reverb shimmer + subtle chorus widening
        RADIO,         // HPF 300Hz + LPF 6kHz + hard compression + saturation
        DISTORTED,     // Tube-style saturation + tone sculpting
        WIDE,          // Mid/side widening above 300Hz
        NUM_PRESETS
    };

    void prepare(double sr)
    {
        sampleRate = sr;
        reset();
    }

    void setPreset(Preset p) { preset = p; }
    void setPreset(int p) { preset = static_cast<Preset>(std::max(0, std::min(p, (int)NUM_PRESETS - 1))); }

    void process(float* L, float* R, int numSamples)
    {
        if (preset == BYPASS) return;

        for (int i = 0; i < numSamples; ++i)
        {
            float l = L[i], r = R[i];

            switch (preset) {
                case TRANSPARENT: processTransparent(l, r); break;
                case PUNCH:       processPunch(l, r); break;
                case WET:         processWet(l, r); break;
                case RADIO:       processRadio(l, r); break;
                case DISTORTED:   processDistorted(l, r); break;
                case WIDE:        processWide(l, r); break;
                default: break;
            }

            // Final safety limiter — NEVER exceed +-1.0
            l = softLimit(l);
            r = softLimit(r);

            L[i] = l;
            R[i] = r;
        }
    }

private:
    Preset preset = BYPASS;
    double sampleRate = 44100.0;

    // ── Shared state ─────────────────────────────────────────────────────────

    // Compressor state
    float compEnv = 0.0f;

    // Filter states (stereo pairs)
    float hpL = 0.0f, hpR = 0.0f;     // highpass
    float lpL = 0.0f, lpR = 0.0f;     // lowpass
    float eqL = 0.0f, eqR = 0.0f;     // EQ band
    float lpL2 = 0.0f, lpR2 = 0.0f;   // second LP stage

    // Reverb state (simple Schroeder for wet preset)
    static constexpr int REV_SIZE = 4096;
    float revBufL[REV_SIZE] = {};
    float revBufR[REV_SIZE] = {};
    int revPos = 0;
    float revFb = 0.0f;

    // Chorus LFO
    double chorusPhase = 0.0;

    // Mid/side filter for WIDE
    float msHpL = 0.0f, msHpR = 0.0f;

    void reset()
    {
        compEnv = 0.0f;
        hpL = hpR = lpL = lpR = eqL = eqR = lpL2 = lpR2 = 0.0f;
        revPos = 0; revFb = 0.0f;
        chorusPhase = 0.0;
        msHpL = msHpR = 0.0f;
        for (auto& s : revBufL) s = 0.0f;
        for (auto& s : revBufR) s = 0.0f;
    }

    // ── Soft limiter (knee at 0.85, max 1.0) ─────────────────────────────────
    static float softLimit(float x)
    {
        const float knee = 0.85f;
        if (x > knee)       return knee + (1.0f - knee) * std::tanh((x - knee) / (1.0f - knee));
        else if (x < -knee) return -(knee + (1.0f - knee) * std::tanh((-x - knee) / (1.0f - knee)));
        return x;
    }

    // ── 1-pole filter helpers ────────────────────────────────────────────────
    static float lp1(float in, float& state, float coeff)
    {
        state += coeff * (in - state);
        return state;
    }

    static float hp1(float in, float& state, float coeff)
    {
        state += coeff * (in - state);
        return in - state;
    }

    // ── Glue compressor (feed-forward, RMS) ──────────────────────────────────
    float compress(float l, float r, float threshold, float ratio, float attack, float release, float makeup)
    {
        float peak = std::max(std::abs(l), std::abs(r));
        float target = (peak > threshold)
            ? threshold + (peak - threshold) / ratio
            : peak;
        float gain = (peak > 0.0001f) ? target / peak : 1.0f;
        gain *= makeup;

        float coeff = (gain < compEnv)
            ? std::exp(-1.0f / (attack * static_cast<float>(sampleRate)))
            : std::exp(-1.0f / (release * static_cast<float>(sampleRate)));
        compEnv = coeff * compEnv + (1.0f - coeff) * gain;

        return std::min(compEnv, 2.0f); // Safety cap on gain
    }

    // ── TRANSPARENT: gentle glue + brick-wall limiter ────────────────────────
    void processTransparent(float& l, float& r)
    {
        float g = compress(l, r, 0.5f, 2.0f, 0.01f, 0.15f, 1.2f);
        l *= g;
        r *= g;
    }

    // ── PUNCH: transient shaper + saturation + presence boost ────────────────
    void processPunch(float& l, float& r)
    {
        // Gentle compression for glue
        float g = compress(l, r, 0.4f, 3.0f, 0.002f, 0.08f, 1.4f);
        l *= g;
        r *= g;

        // Presence EQ: boost ~3kHz via bandpass
        float sr = static_cast<float>(sampleRate);
        float eqF = 2.0f * std::sin(Dsp::PI_F * 3000.0f / sr);
        eqL += eqF * (l - eqL);
        eqR += eqF * (r - eqR);
        float boostL = eqL * 0.3f;  // +3dB at presence
        float boostR = eqR * 0.3f;
        l += boostL;
        r += boostR;

        // Subtle tape saturation
        l = std::tanh(l * 1.2f) * 0.9f;
        r = std::tanh(r * 1.2f) * 0.9f;
    }

    // ── WET: short reverb + subtle chorus shimmer ────────────────────────────
    void processWet(float& l, float& r)
    {
        // Micro reverb (feedback delay)
        int tapA = (revPos + REV_SIZE - 1423) & (REV_SIZE - 1);
        int tapB = (revPos + REV_SIZE - 2731) & (REV_SIZE - 1);
        float wetL = revBufL[tapA] * 0.4f + revBufR[tapB] * 0.2f;
        float wetR = revBufR[tapA] * 0.4f + revBufL[tapB] * 0.2f;
        revBufL[revPos] = l + wetL * 0.35f;
        revBufR[revPos] = r + wetR * 0.35f;
        // Clamp feedback buffer
        revBufL[revPos] = std::max(-1.5f, std::min(revBufL[revPos], 1.5f));
        revBufR[revPos] = std::max(-1.5f, std::min(revBufR[revPos], 1.5f));
        revPos = (revPos + 1) & (REV_SIZE - 1);

        // Subtle chorus via LFO
        chorusPhase += 1.5 / sampleRate;
        if (chorusPhase >= 1.0) chorusPhase -= 1.0;
        float lfo = static_cast<float>(std::sin(chorusPhase * Dsp::TWO_PI));
        float spread = lfo * 0.0005f;

        l = l * 0.7f + wetL * 0.3f + spread * l;
        r = r * 0.7f + wetR * 0.3f - spread * r;
    }

    // ── RADIO: bandpass 300-6000Hz + aggressive compression + saturation ─────
    void processRadio(float& l, float& r)
    {
        float sr = static_cast<float>(sampleRate);
        // HPF at 300Hz
        float hpCoeff = 2.0f * std::sin(Dsp::PI_F * 300.0f / sr);
        l = hp1(l, hpL, hpCoeff);
        r = hp1(r, hpR, hpCoeff);

        // LPF at 6000Hz
        float lpCoeff = 2.0f * std::sin(Dsp::PI_F * 6000.0f / sr);
        l = lp1(l, lpL, lpCoeff);
        r = lp1(r, lpR, lpCoeff);

        // Second LP stage for steeper rolloff
        l = lp1(l, lpL2, lpCoeff);
        r = lp1(r, lpR2, lpCoeff);

        // Heavy compression
        float g = compress(l, r, 0.2f, 6.0f, 0.001f, 0.05f, 2.0f);
        l *= g;
        r *= g;

        // Warm saturation
        l = std::tanh(l * 1.8f) * 0.7f;
        r = std::tanh(r * 1.8f) * 0.7f;
    }

    // ── DISTORTED: tube-style soft clip + tone sculpting ─────────────────────
    void processDistorted(float& l, float& r)
    {
        float sr = static_cast<float>(sampleRate);

        // Pre-gain
        l *= 2.5f;
        r *= 2.5f;

        // Asymmetric soft clip (tube character)
        auto tubeClip = [](float x) -> float {
            if (x > 0.0f) return 1.0f - std::exp(-x);
            return -1.0f + std::exp(x);
        };
        l = tubeClip(l);
        r = tubeClip(r);

        // Tone shaping: cut harsh highs, warm low-mids
        float lpCoeff = 2.0f * std::sin(Dsp::PI_F * 8000.0f / sr);
        l = lp1(l, lpL, lpCoeff);
        r = lp1(r, lpR, lpCoeff);

        // Output level compensation
        l *= 0.65f;
        r *= 0.65f;
    }

    // ── WIDE: mid/side widening above 300Hz ──────────────────────────────────
    void processWide(float& l, float& r)
    {
        float sr = static_cast<float>(sampleRate);

        // Encode to mid/side
        float mid  = (l + r) * 0.5f;
        float side = (l - r) * 0.5f;

        // HPF the side signal at 300Hz (keep bass mono)
        float hpCoeff = 2.0f * std::sin(Dsp::PI_F * 300.0f / sr);
        float sideHi = hp1(side, msHpL, hpCoeff);
        float sideLo = side - sideHi;

        // Widen: boost side above 300Hz by ~3dB
        sideHi *= 1.4f;
        side = sideLo + sideHi;

        // Light glue compression on mid
        float g = compress(mid, mid, 0.5f, 2.0f, 0.01f, 0.1f, 1.15f);
        mid *= g;

        // Decode back to L/R
        l = mid + side;
        r = mid - side;
    }
};
