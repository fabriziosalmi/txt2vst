#pragma once
#include <cmath>
#include "DspConstants.h"

// Drawbar organ — 9 harmonics with individual gains, rotary speaker sim.
// CPU budget: ~12 ops/sample
struct OrganVoice
{
    struct Params
    {
        float bars[9] = {1.0f, 0.8f, 0.0f, 0.6f, 0.0f, 0.0f, 0.3f, 0.0f, 0.2f};
        float decay   = 0.05f; // key click decay
        float rotary  = 0.50f; // 0-1 rotary rate
    };

    void prepare(double sr) { sampleRate = sr; }
    void setParams(const Params& p) { params = p; }

    void trigger(int midiNote, float velocity = 1.0f)
    {
        baseFreq = 440.0 * std::pow(2.0, (midiNote - 69) / 12.0);
        vel = velocity;
        ampEnv = 1.0f;
        clickEnv = 1.0f;
        clickCoeff = static_cast<float>(std::exp(-1.0 / (params.decay * sampleRate)));
        for (auto& p : phases) p = 0.0;
        active = true;
        releasing = false;
        samplesRemaining = static_cast<int>(sampleRate * 2.5);
    }

    void noteOff()
    {
        releasing = true;
        relCoeff = static_cast<float>(std::exp(-1.0 / (0.02 * sampleRate)));
    }

    bool isActive() const { return active; }

    float tick()
    {
        if (!active) return 0.0f;

        if (releasing) {
            ampEnv *= relCoeff;
            if (ampEnv < 0.0001f) { active = false; return 0.0f; }
        }
        clickEnv *= clickCoeff;

        // 9 drawbar harmonics: 16', 5⅓', 8', 4', 2⅔', 2', 1⅗', 1⅓', 1'
        static const double ratios[9] = {0.5, 1.5, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 8.0};
        float out = 0.0f;
        for (int h = 0; h < 9; ++h)
        {
            if (params.bars[h] < 0.01f) continue;
            double freq = baseFreq * ratios[h];
            if (freq > sampleRate * 0.45) continue; // Nyquist guard
            phases[h] += freq / sampleRate;
            if (phases[h] >= 1.0) phases[h] -= 1.0;
            out += static_cast<float>(std::sin(phases[h] * Dsp::TWO_PI)) * params.bars[h];
        }
        out *= 0.15f; // Normalize 9 harmonics

        // Key click
        out += clickEnv * 0.3f * vel;

        // Simple rotary
        rotaryPhase += (0.5 + params.rotary * 6.0) / sampleRate;
        if (rotaryPhase >= 1.0) rotaryPhase -= 1.0;
        float rotMod = 1.0f + 0.08f * static_cast<float>(std::sin(rotaryPhase * Dsp::TWO_PI));

        --samplesRemaining;
        if (samplesRemaining <= 0) { active = false; return 0.0f; }

        return out * ampEnv * vel * rotMod;
    }

private:
    Params params;
    double sampleRate = 44100.0, baseFreq = 440.0;
    float vel = 1.0f, ampEnv = 1.0f, clickEnv = 0.0f;
    float clickCoeff = 0.999f, relCoeff = 0.999f;
    double phases[9] = {};
    double rotaryPhase = 0.0;
    int samplesRemaining = 0;
    bool releasing = false, active = false;
};
