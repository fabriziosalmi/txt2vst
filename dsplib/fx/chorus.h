#pragma once
#include <cmath>
#include <algorithm>
#include "DspConstants.h"

// Stereo chorus — dual LFO modulated delay lines with depth/rate control.
// CPU budget: ~8 ops/sample
struct ChorusFX
{
    struct Params
    {
        float rate  = 0.80f;  // Hz (0.1-5.0)
        float depth = 0.40f;  // 0-1
        float mix   = 0.35f;  // 0-1
    };

    void prepare(double sr)
    {
        sampleRate = sr;
        std::fill(bufL, bufL + BUF_SIZE, 0.0f);
        std::fill(bufR, bufR + BUF_SIZE, 0.0f);
        writePos = 0;
        lfoPhaseL = 0.0; lfoPhaseR = 0.25; // 90° offset for stereo
    }

    void setParams(const Params& p) { params = p; }

    void process(float* L, float* R, int numSamples)
    {
        const double lfoInc = params.rate / sampleRate;
        const float maxDelay = 0.015f * static_cast<float>(sampleRate); // 15ms max
        const float depthSamples = maxDelay * params.depth;
        const float centerDelay = 0.007f * static_cast<float>(sampleRate); // 7ms center
        const float mix = params.mix;
        const float dry = 1.0f - mix * 0.3f;

        for (int i = 0; i < numSamples; ++i)
        {
            bufL[writePos] = L[i];
            bufR[writePos] = R[i];

            // LFO
            float modL = static_cast<float>(std::sin(lfoPhaseL * Dsp::TWO_PI)) * depthSamples;
            float modR = static_cast<float>(std::sin(lfoPhaseR * Dsp::TWO_PI)) * depthSamples;
            lfoPhaseL += lfoInc; if (lfoPhaseL >= 1.0) lfoPhaseL -= 1.0;
            lfoPhaseR += lfoInc; if (lfoPhaseR >= 1.0) lfoPhaseR -= 1.0;

            // Interpolated read
            float delayL = centerDelay + modL;
            float delayR = centerDelay + modR;
            delayL = std::max(1.0f, std::min(delayL, static_cast<float>(BUF_SIZE - 2)));
            delayR = std::max(1.0f, std::min(delayR, static_cast<float>(BUF_SIZE - 2)));

            int idxL = static_cast<int>(delayL);
            float fracL = delayL - static_cast<float>(idxL);
            int rpL0 = (writePos - idxL + BUF_SIZE) % BUF_SIZE;
            int rpL1 = (rpL0 - 1 + BUF_SIZE) % BUF_SIZE;
            float wetL = bufL[rpL0] * (1.0f - fracL) + bufL[rpL1] * fracL;

            int idxR = static_cast<int>(delayR);
            float fracR = delayR - static_cast<float>(idxR);
            int rpR0 = (writePos - idxR + BUF_SIZE) % BUF_SIZE;
            int rpR1 = (rpR0 - 1 + BUF_SIZE) % BUF_SIZE;
            float wetR = bufR[rpR0] * (1.0f - fracR) + bufR[rpR1] * fracR;

            L[i] = L[i] * dry + wetL * mix;
            R[i] = R[i] * dry + wetR * mix;

            writePos = (writePos + 1) % BUF_SIZE;
        }
    }

private:
    Params params;
    double sampleRate = 44100.0;
    static constexpr int BUF_SIZE = 2048;
    float bufL[BUF_SIZE] = {}, bufR[BUF_SIZE] = {};
    int writePos = 0;
    double lfoPhaseL = 0.0, lfoPhaseR = 0.25;
};
