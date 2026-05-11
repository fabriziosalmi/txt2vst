#pragma once
#include <cmath>
#include <algorithm>
#include "DspConstants.h"

// Brass synth — pulse wave with resonant filter, attack swell, portamento-ready.
// Designed for stabs and swells. CPU: ~8 ops/sample
struct BrassVoice
{
    struct Params
    {
        float cutoff  = 2500.0f; // Hz
        float reso    = 0.40f;   // 0-1
        float attack  = 0.08f;   // sec (brassy swell)
        float decay   = 0.40f;   // sec
        float bright  = 0.60f;   // 0-1 pulse width modulation depth
    };

    void prepare(double sr) { sampleRate = sr; }
    void setParams(const Params& p) { params = p; }

    void trigger(int midiNote, float velocity = 1.0f)
    {
        freq = 440.0 * std::pow(2.0, (midiNote - 69) / 12.0);
        vel = velocity;
        ampEnv = 0.0f;
        filterEnv = 1.0f;
        attackCoeff = static_cast<float>(1.0 / (std::max(0.002, (double)params.attack) * sampleRate));
        decayCoeff = static_cast<float>(std::exp(-1.0 / (params.decay * sampleRate)));
        phase = 0.0;
        pwmPhase = 0.0;
        svfLp = svfBp = 0.0f;
        active = true;
        releasing = false;
        samplesRemaining = static_cast<int>(sampleRate * 2.5);
    }

    void noteOff()
    {
        releasing = true;
        relCoeff = static_cast<float>(std::exp(-1.0 / (0.08 * sampleRate)));
    }

    bool isActive() const { return active; }

    float tick()
    {
        if (!active) return 0.0f;
        --samplesRemaining;
        if (samplesRemaining <= 0) { active = false; return 0.0f; }

        // Attack swell
        if (!releasing) {
            ampEnv += attackCoeff * (1.02f - ampEnv);
            if (ampEnv > 1.0f) ampEnv = 1.0f;
        } else {
            ampEnv *= relCoeff;
            if (ampEnv < 0.0001f) { active = false; return 0.0f; }
        }

        // Filter envelope decay
        filterEnv *= decayCoeff;

        // PWM LFO
        pwmPhase += 3.5 / sampleRate;
        if (pwmPhase >= 1.0) pwmPhase -= 1.0;
        float pw = 0.5f + params.bright * 0.3f * static_cast<float>(std::sin(pwmPhase * Dsp::TWO_PI));

        // Pulse wave
        phase += freq / sampleRate;
        if (phase >= 1.0) phase -= 1.0;
        float pulse = (phase < pw) ? 1.0f : -1.0f;

        // Resonant LP filter with envelope
        float cutHz = params.cutoff * (0.3f + 0.7f * filterEnv * ampEnv);
        cutHz = std::min(cutHz, static_cast<float>(sampleRate * 0.45));
        cutHz = std::max(cutHz, 80.0f);
        float f = 2.0f * static_cast<float>(std::sin(Dsp::PI_F * cutHz / static_cast<float>(sampleRate)));
        f = std::min(f, 0.9f);
        float q = 1.0f - std::min(params.reso, 0.88f);
        float hp = pulse - svfLp - q * svfBp;
        svfBp += f * hp;
        svfLp += f * svfBp;
        svfBp = std::max(-2.0f, std::min(svfBp, 2.0f));
        svfLp = std::max(-2.0f, std::min(svfLp, 2.0f));

        // DC blocker (1-pole highpass at ~5Hz)
        float pre = svfLp * ampEnv * vel * 0.4f;
        float dcOut = pre - dcPrev + 0.9997f * dcState;
        dcPrev = pre;
        dcState = dcOut;

        return dcOut;
    }

private:
    Params params;
    double sampleRate = 44100.0, freq = 440.0;
    float vel = 1.0f, ampEnv = 0.0f, filterEnv = 0.0f;
    float attackCoeff = 0.001f, decayCoeff = 0.999f, relCoeff = 0.999f;
    double phase = 0.0, pwmPhase = 0.0;
    float svfLp = 0.0f, svfBp = 0.0f;
    float dcPrev = 0.0f, dcState = 0.0f;
    int samplesRemaining = 0;
    bool releasing = false, active = false;
};
