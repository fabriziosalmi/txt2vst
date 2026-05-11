#pragma once
#include <cmath>
#include <algorithm>
#include "DspConstants.h"

// Stereo ping-pong delay with tempo sync, feedback, LP filter in feedback path.
// CPU budget: ~6 ops/sample
struct DelayFX
{
    struct Params
    {
        float time    = 0.375f;  // sec (or ratio if synced)
        float feedback = 0.40f;  // 0-0.90
        float mix     = 0.30f;   // 0-1
        float tone    = 0.60f;   // 0-1 (LP in feedback)
        bool  sync    = false;
    };

    void prepare(double sr)
    {
        sampleRate = sr;
        maxDelay = static_cast<int>(sr * 2.0); // 2s max
        if (maxDelay > BUF_SIZE) maxDelay = BUF_SIZE;
        std::fill(bufL, bufL + BUF_SIZE, 0.0f);
        std::fill(bufR, bufR + BUF_SIZE, 0.0f);
        writePos = 0;
        lpL = lpR = 0.0f;
    }

    void setParams(const Params& p) { params = p; }
    void setBpm(float bpm) { currentBpm = bpm; }

    void process(float* L, float* R, int numSamples)
    {
        float delaySec = params.time;
        if (params.sync && currentBpm > 0.0f)
            delaySec = (60.0f / currentBpm) * params.time * 4.0f; // time as beat fraction

        int delaySamples = static_cast<int>(delaySec * sampleRate);
        delaySamples = std::max(1, std::min(delaySamples, maxDelay - 1));

        const float fb = std::min(params.feedback, 0.90f); // Occam: hard cap
        const float mix = params.mix;
        const float dry = 1.0f - mix * 0.5f;
        const float lpAlpha = 0.1f + params.tone * 0.6f;

        for (int i = 0; i < numSamples; ++i)
        {
            int readPos = (writePos - delaySamples + BUF_SIZE) % BUF_SIZE;
            float delL = bufL[readPos];
            float delR = bufR[readPos];

            // LP in feedback
            lpL += lpAlpha * (delL - lpL);
            lpR += lpAlpha * (delR - lpR);

            // Ping-pong: cross-feed
            bufL[writePos] = L[i] + lpR * fb;
            bufR[writePos] = R[i] + lpL * fb;

            // Clamp (Occam)
            bufL[writePos] = std::max(-2.0f, std::min(bufL[writePos], 2.0f));
            bufR[writePos] = std::max(-2.0f, std::min(bufR[writePos], 2.0f));

            L[i] = L[i] * dry + delL * mix;
            R[i] = R[i] * dry + delR * mix;

            writePos = (writePos + 1) % BUF_SIZE;
        }
    }

private:
    Params params;
    double sampleRate = 44100.0;
    float currentBpm = 120.0f;
    static constexpr int BUF_SIZE = 88200; // 2s @ 44.1k
    float bufL[BUF_SIZE] = {};
    float bufR[BUF_SIZE] = {};
    int writePos = 0, maxDelay = BUF_SIZE;
    float lpL = 0.0f, lpR = 0.0f;
};
