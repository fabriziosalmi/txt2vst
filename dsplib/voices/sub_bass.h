#pragma once
#include <cmath>
#include "DspConstants.h"

// Sub bass — pure sine/triangle sub with harmonics control + saturation.
// Below 100Hz focus. Zero aliasing risk. CPU: ~4 ops/sample
struct SubBassVoice
{
    struct Params
    {
        float decay    = 0.80f;  // sec
        float sub      = 0.80f;  // 0-1 sub level (fundamental)
        float harmonics = 0.20f; // 0-1 add 2nd+3rd harmonics
        float drive    = 0.00f;  // 0-1 soft saturation
    };

    void prepare(double sr) { sampleRate = sr; }
    void setParams(const Params& p) { params = p; }

    void trigger(int midiNote, float velocity = 1.0f)
    {
        freq = 440.0 * std::pow(2.0, (midiNote - 69) / 12.0);
        // Clamp to sub range
        if (freq > 120.0) freq = 120.0;
        vel = velocity;
        ampEnv = 1.0f;
        ampCoeff = static_cast<float>(std::exp(-1.0 / (params.decay * sampleRate)));
        phase = 0.0;
        active = true;
        releasing = false;
        samplesRemaining = static_cast<int>(sampleRate * std::min((double)params.decay * 4.0, 2.5));
    }

    void noteOff()
    {
        releasing = true;
        relCoeff = static_cast<float>(std::exp(-1.0 / (0.1 * sampleRate)));
    }

    bool isActive() const { return active; }

    float tick()
    {
        if (!active) return 0.0f;
        --samplesRemaining;
        if (samplesRemaining <= 0) { active = false; return 0.0f; }

        if (releasing) {
            ampEnv *= relCoeff;
            if (ampEnv < 0.0001f) { active = false; return 0.0f; }
        } else {
            ampEnv *= ampCoeff;
            if (ampEnv < 0.0001f) { active = false; return 0.0f; }
        }

        phase += freq / sampleRate;
        if (phase >= 1.0) phase -= 1.0;

        float p = static_cast<float>(phase * Dsp::TWO_PI);

        // Fundamental (sine)
        float out = std::sin(p) * params.sub;

        // Harmonics: 2nd + 3rd
        float h = params.harmonics;
        if (h > 0.01f) {
            out += std::sin(p * 2.0f) * h * 0.5f;
            out += std::sin(p * 3.0f) * h * 0.25f;
        }

        // Soft saturation
        if (params.drive > 0.01f) {
            float d = 1.0f + params.drive * 4.0f;
            out = std::tanh(out * d) / d * (1.0f + params.drive * 0.5f);
        }

        return out * ampEnv * vel * 0.5f;
    }

private:
    Params params;
    double sampleRate = 44100.0, freq = 55.0;
    float vel = 1.0f, ampEnv = 0.0f;
    float ampCoeff = 0.999f, relCoeff = 0.999f;
    double phase = 0.0;
    int samplesRemaining = 0;
    bool releasing = false, active = false;
};
