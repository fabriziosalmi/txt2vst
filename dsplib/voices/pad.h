#pragma once
#include <cmath>
#include "DspConstants.h"

// Pad synth: detuned saw + sub, LP filter, slow ADSR, stereo spread.
// For ambient/chord textures. Pitched voice.
// CPU budget: ~18 ops/sample
struct PadVoice
{
    struct Params
    {
        float cutoff  = 2000.0f; // Hz
        float reso    = 0.20f;   // 0-1
        float attack  = 0.30f;   // sec (0.01-2.0)
        float decay   = 1.50f;   // sec
        float detune  = 0.10f;   // 0-1
    };

    void prepare(double sr) { sampleRate = sr; }
    void setParams(const Params& p) { params = p; }

    void trigger(int midiNote, float velocity = 1.0f)
    {
        targetFreq = 440.0 * std::pow(2.0, (midiNote - 69) / 12.0);
        vel = velocity;
        phase1 = phase2 = subPhase = 0.0;
        ampEnv = 0.0f;
        stage = 0; // attack
        attackInc = 1.0f / static_cast<float>(std::max(1.0, params.attack * sampleRate));
        decayCoeff = static_cast<float>(std::exp(-1.0 / (params.decay * 0.15 * sampleRate)));
        lpState = 0.0f;
        releasing = false;
        active = true;
        samplesRemaining = static_cast<int>(std::min(sampleRate * (params.attack + params.decay * 3.5), sampleRate * 8.0));
    }

    void noteOff() { releasing = true; releaseCoeff = static_cast<float>(std::exp(-1.0 / (0.3 * sampleRate))); }
    bool isActive() const { return active && samplesRemaining > 0; }

    float tick()
    {
        if (!active || samplesRemaining <= 0) { active = false; return 0.0f; }
        --samplesRemaining;

        // ADSR
        if (releasing) {
            ampEnv *= releaseCoeff;
            if (ampEnv < 0.0001f) { active = false; return 0.0f; }
        } else if (stage == 0) {
            ampEnv += attackInc;
            if (ampEnv >= 1.0f) { ampEnv = 1.0f; stage = 1; }
        } else {
            ampEnv *= decayCoeff;
            if (ampEnv < 0.0001f) { active = false; return 0.0f; }
        }

        // Detuned saws
        const double dt = params.detune * 0.003;
        const double f1 = targetFreq * (1.0 - dt);
        const double f2 = targetFreq * (1.0 + dt);
        phase1 += f1 / sampleRate; if (phase1 >= 1.0) phase1 -= 1.0;
        phase2 += f2 / sampleRate; if (phase2 >= 1.0) phase2 -= 1.0;
        subPhase += (targetFreq * 0.5) / sampleRate; if (subPhase >= 1.0) subPhase -= 1.0;

        float saw1 = static_cast<float>(2.0 * phase1 - 1.0);
        float saw2 = static_cast<float>(2.0 * phase2 - 1.0);
        float sub = fastSin(static_cast<float>(subPhase) * Dsp::TWO_PI_F);

        float mix = (saw1 + saw2) * 0.35f + sub * 0.3f;

        // LP filter
        float cutHz = std::min(params.cutoff, static_cast<float>(sampleRate * 0.45));
        float alpha = 1.0f - static_cast<float>(std::exp(-Dsp::TWO_PI * cutHz / sampleRate));
        lpState += alpha * (mix - lpState);

        return lpState * ampEnv * vel * 0.6f;
    }

private:
    Params params;
    double sampleRate = 44100.0;
    double phase1 = 0.0, phase2 = 0.0, subPhase = 0.0;
    double targetFreq = 220.0;
    float vel = 1.0f, ampEnv = 0.0f;
    float attackInc = 0.001f, decayCoeff = 0.9999f, releaseCoeff = 0.999f;
    float lpState = 0.0f;
    int stage = 0, samplesRemaining = 0;
    bool releasing = false, active = false;
};
