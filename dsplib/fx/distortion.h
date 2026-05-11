#pragma once
#include <cmath>
#include <algorithm>
#include "DspConstants.h"

// Tube-style distortion with pre-filter, asymmetric waveshaping, tone control.
// CPU budget: ~4 ops/sample
struct DistortionFX
{
    struct Params
    {
        float drive = 0.30f;  // 0-1
        float tone  = 0.50f;  // 0-1 (post LP)
        float mix   = 0.50f;  // 0-1
    };

    void prepare(double sr)
    {
        sampleRate = sr;
        lpL = lpR = 0.0f;
    }

    void setParams(const Params& p) { params = p; }

    void process(float* L, float* R, int numSamples)
    {
        const float gain = 1.0f + params.drive * 20.0f;
        const float mix = params.mix;
        const float dry = 1.0f - mix;
        const float toneAlpha = 0.05f + (1.0f - params.tone) * 0.4f;

        for (int i = 0; i < numSamples; ++i)
        {
            float dryL = L[i], dryR = R[i];

            // Drive
            float wL = L[i] * gain;
            float wR = R[i] * gain;

            // Asymmetric soft clip (tube-like)
            wL = (wL >= 0.0f) ? fastTanh(wL) : fastTanh(wL * 1.2f) * 0.9f;
            wR = (wR >= 0.0f) ? fastTanh(wR) : fastTanh(wR * 1.2f) * 0.9f;

            // Tone (LP filter)
            lpL += toneAlpha * (wL - lpL);
            lpR += toneAlpha * (wR - lpR);

            L[i] = dryL * dry + lpL * mix;
            R[i] = dryR * dry + lpR * mix;
        }
    }

private:
    Params params;
    double sampleRate = 44100.0;
    float lpL = 0.0f, lpR = 0.0f;
};
