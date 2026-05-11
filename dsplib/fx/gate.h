#pragma once
#include <cmath>
#include <algorithm>
#include "DspConstants.h"

// Noise gate — envelope follower with threshold, attack, hold, release.
// Essential for cleaning up drum buses. CPU: ~3 ops/sample
struct GateFX
{
    struct Params
    {
        float threshold = 0.10f;  // 0-1 (linear amplitude)
        float attack    = 0.001f; // sec
        float hold      = 0.05f;  // sec
        float release   = 0.10f;  // sec
    };

    void prepare(double sr)
    {
        sampleRate = sr;
        env = 0.0f;
        gateGain = 0.0f;
        holdCounter = 0;
    }

    void setParams(const Params& p) { params = p; }

    void process(float* L, float* R, int numSamples)
    {
        const float attackCoeff = std::exp(-1.0f / (std::max(0.0001f, params.attack)
                                  * static_cast<float>(sampleRate)));
        const float releaseCoeff = std::exp(-1.0f / (std::max(0.01f, params.release)
                                   * static_cast<float>(sampleRate)));
        const int holdSamples = static_cast<int>(params.hold * sampleRate);

        for (int i = 0; i < numSamples; ++i)
        {
            float peak = std::max(std::abs(L[i]), std::abs(R[i]));

            // Envelope follower
            float coeff = (peak > env) ? (1.0f - attackCoeff) : (1.0f - releaseCoeff);
            env += coeff * (peak - env);

            // Gate logic
            if (env > params.threshold) {
                holdCounter = holdSamples;
                // Open gate fast
                gateGain += (1.0f - gateGain) * 0.1f;
            } else if (holdCounter > 0) {
                --holdCounter;
                // Hold open
            } else {
                // Close gate
                gateGain *= releaseCoeff;
            }

            gateGain = std::max(0.0f, std::min(gateGain, 1.0f));
            L[i] *= gateGain;
            R[i] *= gateGain;
        }
    }

private:
    Params params;
    double sampleRate = 44100.0;
    float env = 0.0f;
    float gateGain = 0.0f;
    int holdCounter = 0;
};
