#pragma once
#include <cmath>
#include "DspConstants.h"

// Production hats: 6-oscillator ring mod metallic tone + bandpass noise.
// CPU budget: ~10 ops/sample
class HatsVoice
{
public:
    struct Params
    {
        float decay = 0.08f;  // sec (0.01-0.50)
        float tone  = 0.50f;  // 0-1 metallic vs noise
        float body  = 0.30f;  // 0-1 low-end weight
    };

    void prepare(double sr)
    {
        sampleRate = sr;
        samplesRemaining = 0;
        hpAlpha = 1.0f - static_cast<float>(std::exp(-Dsp::TWO_PI * 4000.0 / sr));
    }

    void setParams(const Params& p) { params = p; }

    void trigger()
    {
        for (auto& p : phases) p = 0.0;
        samplesRemaining = static_cast<int>(sampleRate * params.decay * 3.0);
        ampEnv = 1.0f;
        ampCoeff = static_cast<float>(std::exp(-1.0 / (params.decay * sampleRate)));
        hpState = 0.0f;
        ng.reset(99999);
        active = true;
    }

    bool isActive() const { return active && samplesRemaining > 0; }

    float tick()
    {
        if (!active || samplesRemaining <= 0) { active = false; return 0.0f; }
        --samplesRemaining;
        ampEnv *= ampCoeff;
        if (ampEnv < 0.0001f) { active = false; return 0.0f; }

        // 6 detuned square oscillators (metallic ring mod)
        static constexpr double freqs[6] = { 
            204.5, 263.5, 337.0, 432.5, 555.0, 712.5 
        };
        float metal = 0.0f;
        for (int i = 0; i < 6; ++i)
        {
            phases[i] += (Dsp::TWO_PI * freqs[i]) / sampleRate;
            if (phases[i] >= Dsp::TWO_PI) phases[i] -= Dsp::TWO_PI;
            metal += (phases[i] < Dsp::PI) ? 1.0f : -1.0f;
        }
        metal *= (1.0f / 6.0f);

        // Noise component
        float n = ng.tick();

        // Mix tone vs noise
        float mix = metal * params.tone + n * (1.0f - params.tone * 0.5f);

        // HP filter (remove low-end mud)
        float bodyMul = 1.0f - params.body * 0.7f;
        hpState += hpAlpha * bodyMul * (mix - hpState);
        float out = (mix - hpState) * ampEnv * 0.4f;

        // Add body (LP of metal)
        out += metal * ampEnv * params.body * 0.15f;

        return out;
    }

private:
    Params params;
    double sampleRate = 44100.0;
    int samplesRemaining = 0;
    double phases[6] = {};
    float ampEnv = 0.0f, ampCoeff = 0.999f;
    float hpState = 0.0f, hpAlpha = 0.1f;
    bool active = false;
    NoiseGen ng { 99999 };
};
