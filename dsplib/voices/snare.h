#pragma once
#include <cmath>
#include "DspConstants.h"

// Production snare: body tone + noise layer, snap transient, bandpass noise.
// CPU budget: ~12 ops/sample
class SnareVoice
{
public:
    struct Params
    {
        float tune  = 185.0f;  // Hz (100-400)
        float decay = 0.18f;   // sec (0.04-0.40)
        float snap  = 0.50f;   // 0-1 transient
        float noise = 0.60f;   // 0-1 noise mix
    };

    void prepare(double sr)
    {
        sampleRate = sr;
        samplesRemaining = 0;
        // Bandpass for noise: ~2kHz center, Q=2
        const double w0 = Dsp::TWO_PI * 2000.0 / sr;
        bpAlpha = static_cast<float>(std::sin(w0) / (2.0 * 2.0));
        bpCos   = static_cast<float>(std::cos(w0));
    }

    void setParams(const Params& p) { params = p; }

    void trigger()
    {
        phase = 0.0;
        samplesRemaining = static_cast<int>(sampleRate * params.decay * 4.0);
        bodyEnv = 1.0f;
        noiseEnv = 1.0f;
        snapEnv = 1.0f;
        bodyCoeff  = static_cast<float>(std::exp(-1.0 / (params.decay * 0.4 * sampleRate)));
        noiseCoeff = static_cast<float>(std::exp(-1.0 / (params.decay * 0.8 * sampleRate)));
        snapCoeff  = static_cast<float>(std::exp(-1.0 / (0.003 * sampleRate)));
        pitchEnv = 1.0f;
        pitchCoeff = static_cast<float>(std::exp(-1.0 / (0.010 * sampleRate)));
        ng.reset(54321);
        bpZ1 = bpZ2 = 0.0f;
        active = true;
    }

    bool isActive() const { return active && samplesRemaining > 0; }

    float tick()
    {
        if (!active || samplesRemaining <= 0) { active = false; return 0.0f; }
        --samplesRemaining;

        // Body: pitched sine with pitch sweep
        bodyEnv *= bodyCoeff;
        pitchEnv *= pitchCoeff;
        const double freq = params.tune * (1.0 + pitchEnv * 1.5);
        phase += (Dsp::TWO_PI * freq) / sampleRate;
        if (phase >= Dsp::TWO_PI) phase -= Dsp::TWO_PI;
        float body = fastSinD(phase) * bodyEnv * (1.0f - params.noise * 0.5f);

        // Noise: bandpass filtered white noise
        noiseEnv *= noiseCoeff;
        float raw = ng.tick();
        // Simple 2-pole bandpass
        float bp = bpAlpha * raw + bpAlpha * bpZ1 - (1.0f - bpAlpha) * bpZ2;
        // Clamp to prevent filter blowup (Occam guardrail)
        if (bp > 2.0f) bp = 2.0f;
        if (bp < -2.0f) bp = -2.0f;
        bpZ2 = bpZ1;
        bpZ1 = bp;
        float noiseOut = bp * noiseEnv * params.noise;

        // Snap transient
        snapEnv *= snapCoeff;
        float snap = ng.tick() * snapEnv * params.snap * 1.5f;

        float out = body * 0.5f + noiseOut * 0.5f + snap * 0.3f;
        if (bodyEnv < 0.0001f && noiseEnv < 0.0001f) active = false;
        return out;
    }

private:
    Params params;
    double sampleRate = 44100.0;
    int samplesRemaining = 0;
    double phase = 0.0;
    float bodyEnv = 0.0f, bodyCoeff = 0.999f;
    float noiseEnv = 0.0f, noiseCoeff = 0.999f;
    float snapEnv = 0.0f, snapCoeff = 0.999f;
    float pitchEnv = 0.0f, pitchCoeff = 0.999f;
    float bpAlpha = 0.1f, bpCos = 0.0f;
    float bpZ1 = 0.0f, bpZ2 = 0.0f;
    bool active = false;
    NoiseGen ng { 54321 };
};
