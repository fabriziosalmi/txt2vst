#pragma once
#include <cmath>
#include "DspConstants.h"

// Analog tom: pitched sine body with exponential pitch sweep + attack click.
// CPU budget: ~8 ops/sample
class TomVoice
{
public:
    struct Params
    {
        float tune     = 90.0f;   // Hz (50-200)
        float decay    = 0.30f;   // sec
        float pitchenv = 0.65f;   // 0-1
        float attack   = 0.20f;   // 0-1
    };

    void prepare(double sr) { sampleRate = sr; }
    void setParams(const Params& p) { params = p; }

    void trigger()
    {
        phase = 0.0;
        samplesRemaining = static_cast<int>(sampleRate * params.decay * 3.5);
        ampEnv = 1.0f;
        ampCoeff = static_cast<float>(std::exp(-1.0 / (params.decay * sampleRate)));
        pitchEnv = 1.0f;
        pitchCoeff = static_cast<float>(std::exp(-1.0 / (0.025 * sampleRate)));
        clickEnv = 1.0f;
        clickCoeff = static_cast<float>(std::exp(-1.0 / (0.001 * sampleRate)));
        active = true;
    }

    bool isActive() const { return active && samplesRemaining > 0; }

    float tick()
    {
        if (!active || samplesRemaining <= 0) { active = false; return 0.0f; }
        --samplesRemaining;
        ampEnv *= ampCoeff;
        if (ampEnv < 0.0001f) { active = false; return 0.0f; }
        pitchEnv *= pitchCoeff;
        const double freq = params.tune * (1.0 + pitchEnv * params.pitchenv * 3.0);
        phase += (Dsp::TWO_PI * freq) / sampleRate;
        if (phase >= Dsp::TWO_PI) phase -= Dsp::TWO_PI;
        float body = fastSinD(phase) * ampEnv;
        clickEnv *= clickCoeff;
        float click = clickEnv * params.attack * 0.6f;
        return (body * 0.7f + click * 0.3f);
    }

private:
    Params params;
    double sampleRate = 44100.0;
    int samplesRemaining = 0;
    double phase = 0.0;
    float ampEnv = 0.0f, ampCoeff = 0.999f;
    float pitchEnv = 0.0f, pitchCoeff = 0.999f;
    float clickEnv = 0.0f, clickCoeff = 0.999f;
    bool active = false;
};
