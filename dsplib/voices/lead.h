#pragma once
#include <cmath>
#include "DspConstants.h"

// Lead synth: polyBLEP pulse with PWM, resonant SVF, portamento.
// CPU budget: ~15 ops/sample
struct LeadVoice
{
    struct Params
    {
        float cutoff  = 4000.0f; // Hz
        float reso    = 0.30f;   // 0-1
        float pw      = 0.50f;   // 0-1 pulse width
        float decay   = 0.50f;   // sec
        float envmod  = 0.30f;   // 0-1 filter env
    };

    void prepare(double sr) { sampleRate = sr; }
    void setParams(const Params& p) { params = p; }

    void trigger(int midiNote, float velocity = 1.0f)
    {
        targetFreq = 440.0 * std::pow(2.0, (midiNote - 69) / 12.0);
        vel = velocity;
        if (!active) { currentFreq = targetFreq; phase = 0.0; }
        ampEnv = 1.0f;
        filterEnv = 1.0f;
        ampCoeff = static_cast<float>(std::exp(-1.0 / (params.decay * 1.5 * sampleRate)));
        filterCoeff = static_cast<float>(std::exp(-1.0 / (params.decay * 0.5 * sampleRate)));
        releasing = false;
        active = true;
        samplesRemaining = static_cast<int>(sampleRate * params.decay * 4.0);
        glideAlpha = 1.0f - static_cast<float>(std::exp(-1.0 / (0.008 * sampleRate)));
        svfLp = svfBp = svfHp = 0.0f;
    }

    void noteOff() { releasing = true; relCoeff = static_cast<float>(std::exp(-1.0 / (0.05 * sampleRate))); }
    bool isActive() const { return active && samplesRemaining > 0; }

    float tick()
    {
        if (!active || samplesRemaining <= 0) { active = false; return 0.0f; }
        --samplesRemaining;

        if (releasing) { ampEnv *= relCoeff; if (ampEnv < 0.0001f) { active = false; return 0.0f; } }
        else { ampEnv *= ampCoeff; if (ampEnv < 0.005f) ampEnv = 0.005f; }
        filterEnv *= filterCoeff;

        currentFreq += (targetFreq - currentFreq) * static_cast<double>(glideAlpha);
        const double dt = currentFreq / sampleRate;
        phase += dt; if (phase >= 1.0) phase -= 1.0;

        // PolyBLEP pulse
        const float t = static_cast<float>(phase), fd = static_cast<float>(dt);
        float pulse = (phase < static_cast<double>(params.pw)) ? 1.0f : -1.0f;
        pulse += polyBLEP(t, fd);
        double pw2 = phase - static_cast<double>(params.pw);
        if (pw2 < 0.0) pw2 += 1.0;
        pulse -= polyBLEP(static_cast<float>(pw2), fd);

        // SVF filter
        float cutHz = params.cutoff + params.cutoff * params.envmod * filterEnv * 8.0f;
        cutHz = std::min(cutHz, static_cast<float>(sampleRate * 0.45f));
        float f = 2.0f * fastSin(Dsp::PI_F * cutHz / static_cast<float>(sampleRate));
        f = std::min(f, 0.9f); // Occam: cap SVF freq coeff for stability
        float q = 1.0f - std::min(params.reso, 0.90f);
        svfHp = pulse - svfLp - q * svfBp;
        svfBp += f * svfHp;
        svfLp += f * svfBp;
        // Clamp all states (Occam guardrail)
        svfBp = std::max(-2.0f, std::min(svfBp, 2.0f));
        svfLp = std::max(-2.0f, std::min(svfLp, 2.0f));

        return fastTanh(svfLp * ampEnv * vel * 0.7f) * 0.7f;
    }

private:
    Params params;
    double sampleRate = 44100.0, phase = 0.0;
    double currentFreq = 440.0, targetFreq = 440.0;
    float vel = 1.0f, ampEnv = 0.0f, filterEnv = 0.0f;
    float ampCoeff = 0.999f, filterCoeff = 0.999f, relCoeff = 0.999f, glideAlpha = 0.01f;
    float svfLp = 0.0f, svfBp = 0.0f, svfHp = 0.0f;
    int samplesRemaining = 0;
    bool releasing = false, active = false;

    static float polyBLEP(float t, float dt)
    {
        if (dt <= 0.0f) return 0.0f;
        if (t < dt) { float n = t / dt; return 2.0f * n - n * n - 1.0f; }
        if (t > 1.0f - dt) { float n = (t - 1.0f) / dt; return 2.0f * n + n * n + 1.0f; }
        return 0.0f;
    }
};
