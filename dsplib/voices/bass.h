#pragma once
#include <cmath>
#include "DspConstants.h"

// Production 303 bass: polyBLEP saw/square, 4-pole diode ladder filter,
// HP in feedback loop, asymmetric slide, gate click, DC blocker.
// CPU budget: ~25 ops/sample (most expensive voice — justified by complexity)
struct BassVoice
{
    struct Params
    {
        float cutoff  = 800.0f;  // Hz (20-20000)
        float reso    = 0.15f;   // 0-1
        float envmod  = 0.20f;   // 0-1
        float decay   = 0.30f;   // sec (0.01-1.0)
        float accent  = 0.00f;   // 0-1
    };

    void prepare(double sr)
    {
        sampleRate = sr;
        osRate = sr * 2.0;
        releaseCoeff = static_cast<float>(std::exp(-1.0 / (0.015 * sr)));
        smoothAlpha  = 1.0f - static_cast<float>(std::exp(-1.0 / (0.005 * sr)));
        glideAlphaUp   = 1.0f - static_cast<float>(std::exp(-1.0 / (0.012 * sr)));
        glideAlphaDown = 1.0f - static_cast<float>(std::exp(-1.0 / (0.035 * sr)));
        fbHpAlpha = 1.0f - static_cast<float>(std::exp(-Dsp::TWO_PI * 150.0 / osRate));
        for (auto& s : stage) s = 0.0f;
        fbHpState = 0.0f;
        dcBlock = dcPrev = prevOsc = 0.0f;
    }

    void setParams(const Params& p)
    {
        params = p;
        const double effDecay = std::max(0.01, static_cast<double>(p.decay) * (1.0 - p.accent * 0.35));
        filterEnvCoeff = static_cast<float>(std::exp(-1.0 / (effDecay * sampleRate)));
        ampDecayCoeff = static_cast<float>(std::exp(-1.0 / (std::max(0.05, static_cast<double>(p.decay) * 1.5) * sampleRate)));
    }

    void trigger(int midiNote, float velocity = 1.0f)
    {
        targetFreq = 440.0 * std::pow(2.0, (midiNote - 69) / 12.0);
        const bool wasActive = active;
        if (!wasActive) currentFreq = targetFreq;
        vel = velocity;
        if (!wasActive) { phase = 0.0; subPhase = 0.0; }

        if (wasActive)
            filterEnv = std::min(1.0f, filterEnv + 0.85f);
        else
            filterEnv = 1.0f;

        clickEnv = 1.0f;
        clickCoeff = static_cast<float>(std::exp(-1.0 / (0.0005 * sampleRate)));
        ampEnv = 1.0f;
        releasing = false;
        active = true;
        samplesRemaining = static_cast<int>(sampleRate * 2.5);
        if (!wasActive) { smoothCutoff = params.cutoff; smoothReso = params.reso; }
    }

    void noteOff() { releasing = true; }
    bool isActive() const { return active && samplesRemaining > 0; }

    float tick()
    {
        if (!active || samplesRemaining <= 0) { active = false; return 0.0f; }
        --samplesRemaining;

        if (releasing) {
            ampEnv *= releaseCoeff;
            if (ampEnv < 0.0001f) { active = false; samplesRemaining = 0; return 0.0f; }
        } else {
            ampEnv *= ampDecayCoeff;
            if (ampEnv < 0.001f) ampEnv = 0.001f;
        }

        // Asymmetric slide
        const float ga = (targetFreq > currentFreq) ? glideAlphaUp : glideAlphaDown;
        currentFreq += (targetFreq - currentFreq) * static_cast<double>(ga);

        // PolyBLEP oscillator
        const double dt = currentFreq / sampleRate;
        phase += dt; if (phase >= 1.0) phase -= 1.0;
        const float t = static_cast<float>(phase), fd = static_cast<float>(dt);

        float saw = 2.0f * t - 1.0f - polyBLEP(t, fd);
        double p2 = phase + 0.5; if (p2 >= 1.0) p2 -= 1.0;
        float sqr = (phase < 0.5) ? 1.0f : -1.0f;
        sqr += polyBLEP(t, fd) - polyBLEP(static_cast<float>(p2), fd);

        float osc = saw * (1.0f - waveMix) + sqr * waveMix;

        // Sub
        subPhase += dt * 0.5; if (subPhase >= 1.0) subPhase -= 1.0;
        osc += fastSin(static_cast<float>(subPhase) * Dsp::TWO_PI_F) * subMix;

        filterEnv *= filterEnvCoeff;

        smoothCutoff += smoothAlpha * (params.cutoff - smoothCutoff);
        smoothReso   += smoothAlpha * (params.reso   - smoothReso);

        const float accentBoost = 1.0f + params.accent * 4.0f;
        float modCutoff = smoothCutoff + smoothCutoff * params.envmod * filterEnv * accentBoost * 12.0f;
        // Occam guardrail: clamp cutoff to safe range
        modCutoff = std::max(20.0f, std::min(modCutoff, static_cast<float>(sampleRate * 0.45)));
        float modReso = std::min(smoothReso + params.accent * 0.25f, 0.98f); // cap reso < 1

        osc *= (1.0f + params.accent * 1.5f); // pre-drive

        // 2x oversampled ladder
        float mid = (prevOsc + osc) * 0.5f;
        float y1 = ladderTick(mid, modCutoff, modReso);
        float y2 = ladderTick(osc, modCutoff, modReso);
        float filtered = (y1 + y2) * 0.5f;
        prevOsc = osc;

        filtered = fastTanh(filtered * 1.2f);

        // DC blocker
        const float dc = filtered - dcPrev + 0.9975f * dcBlock;
        dcPrev = filtered; dcBlock = dc; filtered = dc;

        float click = 0.0f;
        if (clickEnv > 0.001f) { click = clickEnv * 0.08f; clickEnv *= clickCoeff; }

        return (filtered + click) * ampEnv * vel * (1.0f + params.accent * 0.7f) * 0.7f;
    }

    void setWaveMix(float w) { waveMix = w; }
    void setSubMix(float s) { subMix = s; }

private:
    Params params;
    double sampleRate = 44100.0, osRate = 88200.0;
    double phase = 0.0, subPhase = 0.0;
    double currentFreq = 110.0, targetFreq = 110.0;
    float vel = 1.0f, ampEnv = 0.0f, ampDecayCoeff = 0.9999f;
    float filterEnv = 0.0f, releaseCoeff = 0.9985f;
    float waveMix = 0.0f, subMix = 0.0f;
    float smoothCutoff = 800.0f, smoothReso = 0.15f, smoothAlpha = 0.01f;
    float glideAlphaUp = 0.03f, glideAlphaDown = 0.01f;
    float filterEnvCoeff = 0.999f;
    float prevOsc = 0.0f;
    float clickEnv = 0.0f, clickCoeff = 0.0f;
    float dcPrev = 0.0f, dcBlock = 0.0f;
    int samplesRemaining = 0;
    bool releasing = false, active = false;

    float stage[4] = {};
    float fbHpState = 0.0f, fbHpAlpha = 0.01f;

    float ladderTick(float input, float cutoffHz, float resonance)
    {
        const float wc = Dsp::TWO_PI_F * cutoffHz / static_cast<float>(osRate);
        const float g = wc / (1.0f + wc);
        const float resoComp = 4.5f + resonance * 0.5f;
        float fb = stage[3] * resonance * resoComp;
        fbHpState += fbHpAlpha * (fb - fbHpState);
        fb -= fbHpState;
        float u = input - fastTanh(fb);
        for (int i = 0; i < 4; ++i)
            stage[i] += g * (fastTanh(i == 0 ? u : stage[i-1]) - stage[i]);
        return stage[3];
    }

    static float polyBLEP(float t, float dt)
    {
        if (dt <= 0.0f) return 0.0f;
        if (t < dt) { const float n = t / dt; return 2.0f * n - n * n - 1.0f; }
        if (t > 1.0f - dt) { const float n = (t - 1.0f) / dt; return 2.0f * n + n * n + 1.0f; }
        return 0.0f;
    }
};
