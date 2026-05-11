#pragma once
#include <cmath>
#include <algorithm>
#include "DspConstants.h"

// Algorithmic stereo reverb — Schroeder/Moorer topology.
// 4 comb filters + 2 allpass = lush tail. CPU: ~20 ops/sample.
struct ReverbFX
{
    struct Params
    {
        float decay  = 0.60f;  // 0-1 (maps to RT60 0.3-5s)
        float damping = 0.40f; // 0-1 (LP in comb feedback)
        float mix    = 0.25f;  // 0-1
        float predelay = 0.02f; // sec
    };

    void prepare(double sr)
    {
        sampleRate = sr;
        // Prime-length comb delays for density
        static const int combLens[4] = { 1557, 1617, 1491, 1422 };
        static const int apLens[2]   = { 225, 556 };
        for (int i = 0; i < 4; ++i) {
            combLen[i] = static_cast<int>(combLens[i] * sr / 44100.0);
            combLen[i] = std::min(combLen[i], COMB_MAX - 1);
            std::fill(combBuf[i], combBuf[i] + COMB_MAX, 0.0f);
            combIdx[i] = 0; combLP[i] = 0.0f;
        }
        for (int i = 0; i < 2; ++i) {
            apLen[i] = static_cast<int>(apLens[i] * sr / 44100.0);
            apLen[i] = std::min(apLen[i], AP_MAX - 1);
            std::fill(apBuf[i], apBuf[i] + AP_MAX, 0.0f);
            apIdx[i] = 0;
        }
        pdLen = static_cast<int>(0.05 * sr);
        std::fill(pdBuf, pdBuf + PD_MAX, 0.0f);
        pdIdx = 0;
    }

    void setParams(const Params& p) { params = p; }

    void process(float* L, float* R, int numSamples)
    {
        const float rt60 = 0.3f + params.decay * 4.7f;
        const float dampAlpha = 0.1f + params.damping * 0.7f;
        const float mix = params.mix;
        const float dry = 1.0f - mix * 0.3f;
        int pdSamples = std::min(static_cast<int>(params.predelay * sampleRate), pdLen - 1);
        if (pdSamples < 1) pdSamples = 1;

        for (int i = 0; i < numSamples; ++i)
        {
            float mono = (L[i] + R[i]) * 0.5f;

            // Pre-delay
            int pdRead = (pdIdx - pdSamples + PD_MAX) % PD_MAX;
            float pd = pdBuf[pdRead];
            pdBuf[pdIdx] = mono;
            pdIdx = (pdIdx + 1) % PD_MAX;

            // Parallel comb filters
            float wet = 0.0f;
            for (int c = 0; c < 4; ++c)
            {
                int rp = (combIdx[c] - combLen[c] + COMB_MAX) % COMB_MAX;
                float del = combBuf[c][rp];
                // LP damping
                combLP[c] += dampAlpha * (del - combLP[c]);
                float fbGain = std::pow(10.0f, -3.0f * static_cast<float>(combLen[c]) / (rt60 * static_cast<float>(sampleRate)));
                combBuf[c][combIdx[c]] = pd + combLP[c] * fbGain;
                // Clamp
                combBuf[c][combIdx[c]] = std::max(-2.0f, std::min(combBuf[c][combIdx[c]], 2.0f));
                combIdx[c] = (combIdx[c] + 1) % COMB_MAX;
                wet += del;
            }
            wet *= 0.25f;

            // Series allpass filters
            for (int a = 0; a < 2; ++a)
            {
                int rp = (apIdx[a] - apLen[a] + AP_MAX) % AP_MAX;
                float del = apBuf[a][rp];
                float out = -wet * 0.5f + del;
                apBuf[a][apIdx[a]] = wet + del * 0.5f;
                apIdx[a] = (apIdx[a] + 1) % AP_MAX;
                wet = out;
            }

            L[i] = L[i] * dry + wet * mix;
            R[i] = R[i] * dry + wet * mix * 0.95f; // Slight stereo offset
        }
    }

private:
    Params params;
    double sampleRate = 44100.0;
    static constexpr int COMB_MAX = 4096;
    static constexpr int AP_MAX = 1024;
    static constexpr int PD_MAX = 4410; // 100ms max
    float combBuf[4][COMB_MAX] = {};
    int combLen[4] = {}, combIdx[4] = {};
    float combLP[4] = {};
    float apBuf[2][AP_MAX] = {};
    int apLen[2] = {}, apIdx[2] = {};
    float pdBuf[PD_MAX] = {};
    int pdIdx = 0, pdLen = PD_MAX;
};
