#pragma once
#include <cmath>
#include <algorithm>
#include "DspConstants.h"

// Stereo phaser — 4-stage allpass with LFO. Classic sweeping effect.
// CPU: ~6 ops/sample
struct PhaserFX
{
    struct Params
    {
        float rate  = 0.50f;  // Hz
        float depth = 0.70f;  // 0-1
        float feedback = 0.40f; // 0-1
        float mix   = 0.50f;  // 0-1
    };

    void prepare(double sr)
    {
        sampleRate = sr;
        lfoPhase = 0.0;
        for (auto& s : apL) s = 0.0f;
        for (auto& s : apR) s = 0.0f;
        fbL = fbR = 0.0f;
    }

    void setParams(const Params& p) { params = p; }

    void process(float* L, float* R, int numSamples)
    {
        const float fb = std::min(params.feedback, 0.85f);
        const double lfoInc = params.rate / sampleRate;

        for (int i = 0; i < numSamples; ++i)
        {
            // LFO
            lfoPhase += lfoInc;
            if (lfoPhase >= 1.0) lfoPhase -= 1.0;
            float lfo = static_cast<float>(std::sin(lfoPhase * Dsp::TWO_PI));

            // Map LFO to allpass coefficient range
            float d = 0.2f + params.depth * 0.6f * (0.5f + 0.5f * lfo);
            d = std::max(0.01f, std::min(d, 0.99f));

            // Left channel - 4 allpass stages
            float inL = L[i] + fbL * fb;
            for (int s = 0; s < 4; ++s) {
                float tmp = inL - d * apL[s];
                inL = apL[s] + d * tmp;
                apL[s] = tmp;
            }
            fbL = std::max(-1.5f, std::min(inL, 1.5f));

            // Right channel - offset LFO phase
            float dR = 0.2f + params.depth * 0.6f * (0.5f - 0.5f * lfo);
            dR = std::max(0.01f, std::min(dR, 0.99f));
            float inR = R[i] + fbR * fb;
            for (int s = 0; s < 4; ++s) {
                float tmp = inR - dR * apR[s];
                inR = apR[s] + dR * tmp;
                apR[s] = tmp;
            }
            fbR = std::max(-1.5f, std::min(inR, 1.5f));

            L[i] = L[i] * (1.0f - params.mix) + inL * params.mix;
            R[i] = R[i] * (1.0f - params.mix) + inR * params.mix;
        }
    }

private:
    Params params;
    double sampleRate = 44100.0;
    double lfoPhase = 0.0;
    float apL[4] = {}, apR[4] = {};
    float fbL = 0.0f, fbR = 0.0f;
};
