#pragma once
#include <cmath>
#include <algorithm>
#include "DspConstants.h"

// 3-band EQ — low shelf + parametric mid + high shelf.
// Clean, musical, no surprises. CPU: ~6 ops/sample
struct EqFX
{
    struct Params
    {
        float lowGain  = 0.50f;  // 0-1 maps to -12..+12 dB
        float midGain  = 0.50f;  // 0-1 maps to -12..+12 dB
        float midFreq  = 0.50f;  // 0-1 maps to 200..5000 Hz
        float highGain = 0.50f;  // 0-1 maps to -12..+12 dB
    };

    void prepare(double sr)
    {
        sampleRate = sr;
        for (auto& s : stateL) s = 0.0f;
        for (auto& s : stateR) s = 0.0f;
    }

    void setParams(const Params& p) { params = p; }

    void process(float* L, float* R, int numSamples)
    {
        // Convert params to dB
        const float lowDb  = (params.lowGain  - 0.5f) * 24.0f;
        const float midDb  = (params.midGain  - 0.5f) * 24.0f;
        const float highDb = (params.highGain - 0.5f) * 24.0f;
        const float midHz  = 200.0f + params.midFreq * 4800.0f;

        const float lowLin  = std::pow(10.0f, lowDb / 20.0f);
        const float midLin  = std::pow(10.0f, midDb / 20.0f);
        const float highLin = std::pow(10.0f, highDb / 20.0f);

        // Simple biquad-style processing via 1-pole crossovers
        const float sr = static_cast<float>(sampleRate);
        const float lowF  = 2.0f * std::sin(Dsp::PI_F * 250.0f / sr);
        const float highF = 2.0f * std::sin(Dsp::PI_F * 4000.0f / sr);
        const float midF  = 2.0f * std::sin(Dsp::PI_F * midHz / sr);

        for (int i = 0; i < numSamples; ++i)
        {
            // Left
            float inL = L[i];
            // Low shelf via 1-pole LP
            stateL[0] += lowF * (inL - stateL[0]);
            float lo = stateL[0];
            float rest = inL - lo;
            // High shelf via 1-pole HP
            stateL[1] += highF * (rest - stateL[1]);
            float mid = stateL[1];
            float hi = rest - mid;
            // Mid bell (simple gain around midFreq)
            stateL[2] += midF * (mid - stateL[2]);
            float midBand = stateL[2];
            float midRest = mid - midBand;

            L[i] = lo * lowLin + midBand * midLin + midRest + hi * highLin;
            L[i] = std::max(-1.5f, std::min(L[i], 1.5f));

            // Right (same topology)
            float inR = R[i];
            stateR[0] += lowF * (inR - stateR[0]);
            float loR = stateR[0];
            float restR = inR - loR;
            stateR[1] += highF * (restR - stateR[1]);
            float midR = stateR[1];
            float hiR = restR - midR;
            stateR[2] += midF * (midR - stateR[2]);
            float midBandR = stateR[2];
            float midRestR = midR - midBandR;

            R[i] = loR * lowLin + midBandR * midLin + midRestR + hiR * highLin;
            R[i] = std::max(-1.5f, std::min(R[i], 1.5f));
        }
    }

private:
    Params params;
    double sampleRate = 44100.0;
    float stateL[3] = {}, stateR[3] = {};
};
