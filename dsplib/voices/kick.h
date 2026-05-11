#pragma once
#include <cmath>
#include "DspConstants.h"

// Production kick: dual-stage amp envelope (body+sub), exponential pitch sweep,
// sub-oscillator, HP-filtered click, asymmetric drive, output LP.
// CPU budget: ~15 ops/sample (target: <5% single core @ 44.1k)
class KickVoice
{
public:
    struct Params
    {
        float tune     = 60.0f;   // Hz (40-120)
        float decay    = 0.45f;   // sec (0.05-0.80)
        float punch    = 0.40f;   // 0-1 click intensity
        float pitchenv = 0.80f;   // 0-1 pitch sweep depth
        float drive    = 0.30f;   // 0-1 body distortion
        float sub      = 0.50f;   // 0-1 sub-octave mix
    };

    void prepare(double sr)
    {
        sampleRate = sr;
        phase = subPhase = 0.0;
        samplesRemaining = 0;
        pitchDecayCoeff = static_cast<float>(std::exp(-1.0 / (0.030 * sr)));
        clickHpAlpha = 1.0f - static_cast<float>(std::exp(-Dsp::TWO_PI * 3000.0 / sr));
        outLpAlpha = 1.0f - static_cast<float>(std::exp(-Dsp::TWO_PI * 12000.0 / sr));
        outLpState = 0.0f;
    }

    void setParams(const Params& p) { params = p; }

    void trigger()
    {
        durationSamples  = static_cast<int>(sampleRate * params.decay * 3.0);
        samplesRemaining = durationSamples;
        phase = subPhase = 0.0;
        pitchEnvState = 1.0f;
        noise.reset(12345);

        bodyEnv  = 1.0f;
        subEnv   = 1.0f;
        bodyDecayCoeff = static_cast<float>(std::exp(-1.0 / (params.decay * 0.35 * sampleRate)));
        subDecayCoeff  = static_cast<float>(std::exp(-1.0 / (params.decay * 1.2 * sampleRate)));

        clickEnv   = 1.0f;
        clickCoeff = static_cast<float>(std::exp(-1.0 / (0.002 * sampleRate)));
        clickHpState = 0.0f;

        attackSamples = static_cast<int>(sampleRate * 0.0003);
        attackCounter = 0;

        pitchEnvSlow = 1.0f;
        pitchSlowCoeff = static_cast<float>(std::exp(-1.0 / (0.080 * sampleRate)));
    }

    bool isActive() const { return samplesRemaining > 0; }

    float tick()
    {
        if (samplesRemaining <= 0) return 0.0f;
        --samplesRemaining;

        bodyEnv *= bodyDecayCoeff;
        subEnv  *= subDecayCoeff;

        pitchEnvState *= pitchDecayCoeff;
        pitchEnvSlow  *= pitchSlowCoeff;

        const float pitchSweep = pitchEnvState * 0.7f + pitchEnvSlow * 0.3f;
        const float extraPitch = params.tune * params.pitchenv * 5.0f;
        const double freq = static_cast<double>(params.tune + extraPitch * pitchSweep);

        const double phaseInc = (Dsp::TWO_PI * freq) / sampleRate;
        phase += phaseInc;
        if (phase >= Dsp::TWO_PI) phase -= Dsp::TWO_PI;
        float body = fastSinD(phase);

        // Drive
        if (params.drive > 0.001f)
        {
            const float driveGain = 1.0f + params.drive * 8.0f;
            body = fastTanh(body * driveGain);
            if (body > 0.0f) body *= (1.0f - params.drive * 0.15f);
            body *= 0.8f / (0.4f + params.drive * 0.4f);
        }
        body *= bodyEnv;

        // Sub
        subPhase += (Dsp::TWO_PI * freq * 0.5) / sampleRate;
        if (subPhase >= Dsp::TWO_PI) subPhase -= Dsp::TWO_PI;
        float subOsc = fastSinD(subPhase) * subEnv * params.sub;

        // Click
        float click = 0.0f;
        if (clickEnv > 0.0001f)
        {
            float raw = noise.tick() * clickEnv;
            clickHpState += clickHpAlpha * (raw - clickHpState);
            click = (raw - clickHpState) * params.punch * 1.5f;
            clickEnv *= clickCoeff;
        }

        float out = body * 0.65f + subOsc * 0.5f + click * 0.4f;

        // Output LP
        outLpState += outLpAlpha * (out - outLpState);
        out = outLpState;

        // Anti-click ramp
        if (attackCounter < attackSamples)
            out *= static_cast<float>(attackCounter++) / static_cast<float>(attackSamples);

        return out;
    }

private:
    Params  params;
    double  sampleRate = 44100.0;
    int     samplesRemaining = 0, durationSamples = 0;
    double  phase = 0.0, subPhase = 0.0;
    float   pitchEnvState = 1.0f, pitchDecayCoeff = 0.999f;
    float   pitchEnvSlow = 1.0f, pitchSlowCoeff = 0.9999f;
    float   bodyEnv = 0.0f, bodyDecayCoeff = 0.999f;
    float   subEnv = 0.0f, subDecayCoeff = 0.9999f;
    float   clickEnv = 0.0f, clickCoeff = 0.0f;
    float   clickHpState = 0.0f, clickHpAlpha = 0.01f;
    float   outLpState = 0.0f, outLpAlpha = 0.1f;
    NoiseGen noise { 12345 };
    int     attackSamples = 22, attackCounter = 22;
};
