#pragma once
#include <cmath>
#include "DspConstants.h"

// 2-operator FM synth — carrier:modulator with ratio, index envelope.
// CPU budget: ~8 ops/sample
struct FMSynthVoice
{
    struct Params
    {
        float ratio   = 2.0f;   // mod:carrier frequency ratio
        float index   = 1.5f;   // FM depth
        float decay   = 0.50f;  // sec
        float indexEnv = 0.70f; // 0-1 index envelope depth
        float feedback = 0.0f;  // 0-1 modulator self-feedback
    };

    void prepare(double sr) { sampleRate = sr; }
    void setParams(const Params& p) { params = p; }

    void trigger(int midiNote, float velocity = 1.0f)
    {
        carrierFreq = 440.0 * std::pow(2.0, (midiNote - 69) / 12.0);
        vel = velocity;
        ampEnv = 1.0f;
        indexEnv = 1.0f;
        ampCoeff = static_cast<float>(std::exp(-1.0 / (params.decay * sampleRate)));
        indexCoeff = static_cast<float>(std::exp(-1.0 / (params.decay * 0.4 * sampleRate)));
        carrierPhase = modPhase = 0.0;
        modFB = 0.0f;
        active = true;
        releasing = false;
        samplesRemaining = static_cast<int>(sampleRate * params.decay * 4.0);
    }

    void noteOff()
    {
        releasing = true;
        relCoeff = static_cast<float>(std::exp(-1.0 / (0.05 * sampleRate)));
    }

    bool isActive() const { return active && samplesRemaining > 0; }

    float tick()
    {
        if (!active || samplesRemaining <= 0) { active = false; return 0.0f; }
        --samplesRemaining;

        if (releasing) {
            ampEnv *= relCoeff;
            if (ampEnv < 0.0001f) { active = false; return 0.0f; }
        } else {
            ampEnv *= ampCoeff;
            if (ampEnv < 0.001f) ampEnv = 0.001f;
        }
        indexEnv *= indexCoeff;

        double modFreq = carrierFreq * params.ratio;
        float currentIndex = params.index * (1.0f - params.indexEnv + params.indexEnv * indexEnv);

        // Modulator with self-feedback
        float fb = params.feedback * modFB;
        modPhase += modFreq / sampleRate;
        if (modPhase >= 1.0) modPhase -= 1.0;
        float modOut = static_cast<float>(std::sin(modPhase * Dsp::TWO_PI + fb));
        modFB = modOut;

        // Carrier
        carrierPhase += carrierFreq / sampleRate;
        if (carrierPhase >= 1.0) carrierPhase -= 1.0;
        float out = static_cast<float>(std::sin(carrierPhase * Dsp::TWO_PI + modOut * currentIndex));

        return out * ampEnv * vel * 0.5f;
    }

private:
    Params params;
    double sampleRate = 44100.0, carrierFreq = 440.0;
    double carrierPhase = 0.0, modPhase = 0.0;
    float vel = 1.0f, ampEnv = 0.0f, indexEnv = 0.0f;
    float ampCoeff = 0.999f, indexCoeff = 0.999f, relCoeff = 0.999f;
    float modFB = 0.0f;
    int samplesRemaining = 0;
    bool releasing = false, active = false;
};
