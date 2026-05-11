#pragma once
#include <cmath>
#include "DspConstants.h"

// Pluck synth: Karplus-Strong physical model with damping + brightness.
// CPU budget: ~6 ops/sample
struct PluckVoice
{
    struct Params
    {
        float decay  = 0.80f;    // sec (0.1-3.0)
        float bright = 0.50f;    // 0-1 LP in feedback
        float body   = 0.30f;    // 0-1 body resonance
    };

    void prepare(double sr) { sampleRate = sr; maxDelay = static_cast<int>(sr / 20.0); }
    void setParams(const Params& p) { params = p; }

    void trigger(int midiNote, float velocity = 1.0f)
    {
        const double freq = 440.0 * std::pow(2.0, (midiNote - 69) / 12.0);
        delayLen = static_cast<int>(sampleRate / freq);
        if (delayLen < 2) delayLen = 2;
        if (delayLen > maxDelay) delayLen = maxDelay;

        vel = velocity;
        // Fill delay line with burst of filtered noise (excitation)
        NoiseGen exc(midiNote * 31 + 42);
        float prev = 0.0f;
        for (int i = 0; i < delayLen; ++i)
        {
            float n = exc.tick() * vel;
            // Gentle LP on excitation
            prev = prev * 0.3f + n * 0.7f;
            buf[i] = prev;
        }
        writePos = 0;
        dampState = 0.0f;
        damping = 0.3f + (1.0f - params.bright) * 0.5f;
        feedbackGain = 1.0f - (1.0f / (params.decay * static_cast<float>(sampleRate) / static_cast<float>(delayLen)));
        feedbackGain = std::max(0.0f, std::min(feedbackGain, 0.990f)); // Occam: no self-osc
        active = true;
        samplesRemaining = static_cast<int>(std::min(sampleRate * params.decay * 2.5, sampleRate * 8.0));
    }

    void noteOff() { feedbackGain *= 0.5f; }
    bool isActive() const { return active && samplesRemaining > 0; }

    float tick()
    {
        if (!active || samplesRemaining <= 0) { active = false; return 0.0f; }
        --samplesRemaining;

        int readPos = (writePos + 1) % delayLen;
        float sample = buf[readPos];

        // LP damping in feedback
        dampState = dampState * damping + sample * (1.0f - damping);
        buf[writePos] = dampState * feedbackGain;

        // Body resonance (gentle LP)
        float bodyLp = sample * (1.0f - params.body * 0.4f) + dampState * params.body * 0.4f;

        writePos = (writePos + 1) % delayLen;

        if (std::abs(bodyLp) < 0.00001f && std::abs(dampState) < 0.00001f)
            active = false;

        return bodyLp * 0.7f;
    }

private:
    Params params;
    double sampleRate = 44100.0;
    static constexpr int BUF_SIZE = 4096;
    float buf[BUF_SIZE] = {};
    int delayLen = 100, writePos = 0, maxDelay = 2205;
    float dampState = 0.0f, damping = 0.5f, feedbackGain = 0.99f;
    float vel = 1.0f;
    int samplesRemaining = 0;
    bool active = false;
};
