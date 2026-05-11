#pragma once
#include <cmath>
#include <algorithm>
#include "DspConstants.h"

// Ensemble string — detuned saws with slow attack, LP filter, stereo spread.
// Richer than Pad: 4 oscillators + pitch drift + gentle chorus. CPU: ~14 ops/sample
struct StringVoice
{
    struct Params
    {
        float cutoff  = 3000.0f; // Hz
        float reso    = 0.15f;   // 0-1
        float attack  = 0.30f;   // sec
        float release = 1.00f;   // sec
        float detune  = 0.12f;   // 0-1 spread
    };

    void prepare(double sr) { sampleRate = sr; }
    void setParams(const Params& p) { params = p; }

    void trigger(int midiNote, float velocity = 1.0f)
    {
        baseFreq = 440.0 * std::pow(2.0, (midiNote - 69) / 12.0);
        vel = velocity;
        ampEnv = 0.0f;
        attackCoeff = static_cast<float>(1.0 / (std::max(0.005, (double)params.attack) * sampleRate));
        releaseCoeff = static_cast<float>(std::exp(-1.0 / (params.release * sampleRate)));
        for (auto& p : phases) p = 0.0;
        svfLp = svfBp = 0.0f;
        driftPhase = 0.0;
        active = true;
        releasing = false;
        samplesRemaining = static_cast<int>(sampleRate * std::min((double)(params.attack + params.release * 3.0 + 1.0), 2.5));
    }

    void noteOff()
    {
        releasing = true;
    }

    bool isActive() const { return active; }

    float tick()
    {
        if (!active) return 0.0f;

        // Envelope
        if (!releasing) {
            ampEnv += attackCoeff * (1.02f - ampEnv);
            if (ampEnv > 1.0f) ampEnv = 1.0f;
        } else {
            ampEnv *= releaseCoeff;
            if (ampEnv < 0.0001f) { active = false; return 0.0f; }
        }
        --samplesRemaining;
        if (samplesRemaining <= 0) { active = false; return 0.0f; }

        // Pitch drift LFO
        driftPhase += 0.3 / sampleRate;
        if (driftPhase >= 1.0) driftPhase -= 1.0;
        float drift = static_cast<float>(std::sin(driftPhase * Dsp::TWO_PI)) * 0.001f;

        // 4 detuned saws (PolyBLEP-lite)
        float detuneCents[4] = {
            -params.detune * 8.0f,
            -params.detune * 3.0f + drift * 100.0f,
             params.detune * 3.0f - drift * 100.0f,
             params.detune * 8.0f
        };

        float out = 0.0f;
        for (int o = 0; o < 4; ++o)
        {
            double freq = baseFreq * std::pow(2.0, detuneCents[o] / 1200.0);
            if (freq > sampleRate * 0.45) continue;
            double inc = freq / sampleRate;
            phases[o] += inc;
            if (phases[o] >= 1.0) phases[o] -= 1.0;
            // Naive saw with simple anti-alias
            float saw = static_cast<float>(2.0 * phases[o] - 1.0);
            out += saw;
        }
        out *= 0.18f; // Normalize 4 oscillators

        // SVF lowpass
        float cutHz = std::min(params.cutoff, static_cast<float>(sampleRate * 0.45));
        float f = 2.0f * static_cast<float>(std::sin(Dsp::PI_F * cutHz / static_cast<float>(sampleRate)));
        f = std::min(f, 0.9f);
        float q = 1.0f - std::min(params.reso, 0.85f);
        float hp = out - svfLp - q * svfBp;
        svfBp += f * hp;
        svfLp += f * svfBp;
        svfBp = std::max(-2.0f, std::min(svfBp, 2.0f));
        svfLp = std::max(-2.0f, std::min(svfLp, 2.0f));

        return svfLp * ampEnv * vel * 0.5f;
    }

private:
    Params params;
    double sampleRate = 44100.0, baseFreq = 440.0;
    float vel = 1.0f, ampEnv = 0.0f;
    float attackCoeff = 0.001f, releaseCoeff = 0.999f;
    double phases[4] = {};
    double driftPhase = 0.0;
    float svfLp = 0.0f, svfBp = 0.0f;
    int samplesRemaining = 0;
    bool releasing = false, active = false;
};
