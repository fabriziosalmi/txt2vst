#pragma once
#include <cmath>
#include "DspConstants.h"

// FM percussion: carrier + modulator with FM index envelope.
// Covers cowbell, clave, woodblock, metallic perc.
// CPU budget: ~10 ops/sample
class PercVoice
{
public:
    struct Params
    {
        float tune   = 600.0f;   // Hz carrier (200-2000)
        float decay  = 0.10f;    // sec
        float detune = 0.40f;    // 0-1 modulator ratio offset
        float drive  = 0.30f;    // 0-1 FM depth
    };

    void prepare(double sr) { sampleRate = sr; }
    void setParams(const Params& p) { params = p; }

    void trigger()
    {
        carrierPhase = modPhase = 0.0;
        samplesRemaining = static_cast<int>(sampleRate * params.decay * 3.0);
        ampEnv = 1.0f;
        ampCoeff = static_cast<float>(std::exp(-1.0 / (params.decay * sampleRate)));
        fmEnv = 1.0f;
        fmCoeff = static_cast<float>(std::exp(-1.0 / (params.decay * 0.4 * sampleRate)));
        active = true;
    }

    bool isActive() const { return active && samplesRemaining > 0; }

    float tick()
    {
        if (!active || samplesRemaining <= 0) { active = false; return 0.0f; }
        --samplesRemaining;
        ampEnv *= ampCoeff;
        if (ampEnv < 0.0001f) { active = false; return 0.0f; }
        fmEnv *= fmCoeff;

        const double modRatio = 1.41 + static_cast<double>(params.detune) * 2.0;
        const double modFreq = params.tune * modRatio;
        modPhase += (Dsp::TWO_PI * modFreq) / sampleRate;
        if (modPhase >= Dsp::TWO_PI) modPhase -= Dsp::TWO_PI;
        const float fmDepth = params.drive * fmEnv * 6.0f;
        const float mod = fastSinD(modPhase) * fmDepth;

        const double carrierFreq = params.tune + static_cast<double>(mod) * params.tune;
        // Clamp carrier to safe range (Occam guardrail)
        const double clampedFreq = std::max(20.0, std::min(carrierFreq, sampleRate * 0.45));
        carrierPhase += (Dsp::TWO_PI * clampedFreq) / sampleRate;
        if (carrierPhase >= Dsp::TWO_PI) carrierPhase -= Dsp::TWO_PI;

        return fastSinD(carrierPhase) * ampEnv * 0.6f;
    }

private:
    Params params;
    double sampleRate = 44100.0;
    int samplesRemaining = 0;
    double carrierPhase = 0.0, modPhase = 0.0;
    float ampEnv = 0.0f, ampCoeff = 0.999f;
    float fmEnv = 0.0f, fmCoeff = 0.999f;
    bool active = false;
};
