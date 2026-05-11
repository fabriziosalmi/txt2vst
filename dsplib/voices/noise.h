#pragma once
#include <cmath>
#include <algorithm>
#include "DspConstants.h"

// Shaped noise generator — filtered white/pink noise with resonant filter.
// Good for risers, textures, wind, ocean. CPU: ~6 ops/sample
struct NoiseVoice
{
    struct Params
    {
        float cutoff = 2000.0f;  // Hz
        float reso   = 0.30f;    // 0-1
        float decay  = 1.00f;    // sec
        float color  = 0.50f;    // 0=white, 1=pink-ish
    };

    void prepare(double sr) { sampleRate = sr; }
    void setParams(const Params& p) { params = p; }

    void trigger(int /*midiNote*/ = 60, float velocity = 1.0f)
    {
        vel = velocity;
        ampEnv = 1.0f;
        ampCoeff = static_cast<float>(std::exp(-1.0 / (params.decay * 0.3 * sampleRate)));
        svfLp = svfBp = 0.0f;
        pinkState[0] = pinkState[1] = pinkState[2] = 0.0f;
        rngState = 123456789u ^ static_cast<uint32_t>(velocity * 1000.0f);
        active = true;
        releasing = false;
        samplesRemaining = static_cast<int>(std::min(sampleRate * params.decay * 3.0, sampleRate * 8.0));
    }

    void noteOff()
    {
        releasing = true;
        relCoeff = static_cast<float>(std::exp(-1.0 / (0.1 * sampleRate)));
    }

    bool isActive() const { return active && samplesRemaining > 0; }

    float tick()
    {
        if (!active || samplesRemaining <= 0) { active = false; return 0.0f; }
        --samplesRemaining;

        if (releasing) {
            ampEnv *= relCoeff;
            if (ampEnv < 0.0001f) { active = false; return 0.0f; }
        } else {
            ampEnv *= ampCoeff;
            if (ampEnv < 0.0001f) { active = false; return 0.0f; }
        }

        // White noise (xorshift)
        rngState ^= rngState << 13;
        rngState ^= rngState >> 17;
        rngState ^= rngState << 5;
        float white = (static_cast<float>(rngState) / 2147483648.0f) - 1.0f;

        // Pink-ish filtering (Paul Kellet approximation)
        pinkState[0] = 0.99886f * pinkState[0] + white * 0.0555179f;
        pinkState[1] = 0.99332f * pinkState[1] + white * 0.0750759f;
        pinkState[2] = 0.96900f * pinkState[2] + white * 0.1538520f;
        float pink = (pinkState[0] + pinkState[1] + pinkState[2] + white * 0.5362f) * 0.25f;

        float noise = white * (1.0f - params.color) + pink * params.color;

        // SVF filter
        float cutHz = std::min(params.cutoff * ampEnv * 2.0f + 100.0f,
                               static_cast<float>(sampleRate * 0.45));
        float f = 2.0f * fastSin(Dsp::PI_F * cutHz / static_cast<float>(sampleRate));
        f = std::min(f, 0.9f);
        float q = 1.0f - std::min(params.reso, 0.90f);
        float hp = noise - svfLp - q * svfBp;
        svfBp += f * hp;
        svfLp += f * svfBp;
        svfBp = std::max(-2.0f, std::min(svfBp, 2.0f));
        svfLp = std::max(-2.0f, std::min(svfLp, 2.0f));

        return svfLp * ampEnv * vel * 0.5f;
    }

private:
    Params params;
    double sampleRate = 44100.0;
    float vel = 1.0f, ampEnv = 0.0f;
    float ampCoeff = 0.999f, relCoeff = 0.999f;
    float svfLp = 0.0f, svfBp = 0.0f;
    float pinkState[3] = {};
    uint32_t rngState = 123456789;
    int samplesRemaining = 0;
    bool releasing = false, active = false;
};
