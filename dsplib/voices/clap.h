#pragma once
#include <cmath>
#include "DspConstants.h"

// Handclap: multi-burst filtered noise with reverb tail.
// 4 micro-bursts spaced ~5ms apart, then a diffuse tail.
// CPU budget: ~8 ops/sample
class ClapVoice
{
public:
    struct Params
    {
        float decay  = 0.20f;   // sec (0.05-0.50)
        float tone   = 0.50f;   // 0-1 brightness
        float spread = 0.40f;   // 0-1 burst spacing
    };

    void prepare(double sr)
    {
        sampleRate = sr;
        bpAlpha = 1.0f - static_cast<float>(std::exp(-Dsp::TWO_PI * 1200.0 / sr));
    }

    void setParams(const Params& p) { params = p; }

    void trigger()
    {
        samplesRemaining = static_cast<int>(sampleRate * params.decay * 4.0);
        tailEnv = 1.0f;
        tailCoeff = static_cast<float>(std::exp(-1.0 / (params.decay * sampleRate)));
        burstIdx = 0;
        burstSample = 0;
        burstSpacing = static_cast<int>(sampleRate * (0.003 + params.spread * 0.008));
        burstLen = static_cast<int>(sampleRate * 0.002);
        bpState = 0.0f;
        ng.reset(77777);
        active = true;
    }

    bool isActive() const { return active && samplesRemaining > 0; }

    float tick()
    {
        if (!active || samplesRemaining <= 0) { active = false; return 0.0f; }
        --samplesRemaining;
        tailEnv *= tailCoeff;
        if (tailEnv < 0.0001f) { active = false; return 0.0f; }

        float burst = 0.0f;
        if (burstIdx < 4)
        {
            if (burstSample < burstLen)
                burst = ng.tick() * 0.8f;
            burstSample++;
            if (burstSample >= burstSpacing)
            {
                burstSample = 0;
                burstIdx++;
            }
        }

        float tail = ng.tick() * tailEnv * 0.4f;
        float raw = burst + tail;

        // Bandpass
        float alpha = bpAlpha * (0.5f + params.tone * 0.5f);
        bpState += alpha * (raw - bpState);
        float out = raw - bpState;
        // Clamp (Occam)
        if (out > 1.5f) out = 1.5f;
        if (out < -1.5f) out = -1.5f;

        return out * 0.5f;
    }

private:
    Params params;
    double sampleRate = 44100.0;
    int samplesRemaining = 0;
    float tailEnv = 0.0f, tailCoeff = 0.999f;
    int burstIdx = 0, burstSample = 0, burstSpacing = 200, burstLen = 80;
    float bpState = 0.0f, bpAlpha = 0.1f;
    bool active = false;
    NoiseGen ng { 77777 };
};
