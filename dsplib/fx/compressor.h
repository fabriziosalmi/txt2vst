#pragma once
#include <cmath>
#include <algorithm>
#include "DspConstants.h"

// Feed-forward compressor with RMS detection, attack/release, makeup gain.
// CPU budget: ~5 ops/sample
struct CompressorFX
{
    struct Params
    {
        float threshold = 0.50f;  // 0-1 (maps to -30..0 dB)
        float ratio     = 0.50f;  // 0-1 (maps to 1:1..20:1)
        float attack    = 0.01f;  // sec
        float release   = 0.10f;  // sec
        float makeup    = 0.00f;  // 0-1 (maps to 0..+24dB)
    };

    void prepare(double sr)
    {
        sampleRate = sr;
        envL = envR = 0.0f;
    }

    void setParams(const Params& p) { params = p; }

    void process(float* L, float* R, int numSamples)
    {
        const float threshDb = -30.0f + params.threshold * 30.0f; // -30..0 dB
        const float threshLin = std::pow(10.0f, threshDb / 20.0f);
        const float ratio = 1.0f + params.ratio * 19.0f; // 1:1..20:1
        const float attackCoeff = std::exp(-1.0f / (std::max(0.001f, params.attack) * static_cast<float>(sampleRate)));
        const float releaseCoeff = std::exp(-1.0f / (std::max(0.01f, params.release) * static_cast<float>(sampleRate)));
        const float makeupDb = params.makeup * 24.0f;
        const float makeupLin = std::pow(10.0f, makeupDb / 20.0f);

        for (int i = 0; i < numSamples; ++i)
        {
            float absL = std::abs(L[i]);
            float absR = std::abs(R[i]);
            float peak = std::max(absL, absR);

            // Envelope follower
            float coeff = (peak > envL) ? attackCoeff : releaseCoeff;
            envL += (1.0f - coeff) * (peak - envL);

            // Gain computation
            float gainDb = 0.0f;
            if (envL > threshLin && threshLin > 0.0001f)
            {
                float overDb = 20.0f * std::log10(envL / threshLin);
                gainDb = -(overDb * (1.0f - 1.0f / ratio));
            }
            float gain = std::pow(10.0f, gainDb / 20.0f) * makeupLin;

            L[i] = std::max(-1.5f, std::min(L[i] * gain, 1.5f));
            R[i] = std::max(-1.5f, std::min(R[i] * gain, 1.5f));
        }
    }

private:
    Params params;
    double sampleRate = 44100.0;
    float envL = 0.0f, envR = 0.0f;
};
