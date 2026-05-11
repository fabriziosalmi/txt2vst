// VST Forge — DSP Voice Test Harness
// Validates audio output quality and CPU performance.
//
// Occam Guardrails tested:
//  1. No NaN/Inf in output
//  2. Peak amplitude < 1.5 (headroom before clipping)
//  3. No DC offset > 0.01 after voice decay
//  4. CPU: < 5% single core per voice at 44.1kHz
//  5. Voice deactivates after decay (no infinite tails)
//  6. No denormals (< 1e-15)
//
// Usage: g++ -std=c++17 -O2 -o test_voices test_voices.cpp && ./test_voices

#include <cmath>
#include <cstdio>
#include <cstring>
#include <chrono>
#include <algorithm>
#include <numeric>

// Include production voices (DspConstants.h is in the same voices/ dir)
#include "../voices/kick.h"
#include "../voices/snare.h"
#include "../voices/hats.h"
#include "../voices/bass.h"

// ─── Test Framework ──────────────────────────────────────────────────────────

struct TestResult
{
    const char* name;
    bool passed;
    // Audio metrics
    float peakAmp;
    float rmsLevel;
    float dcOffset;      // mean of last 1000 samples (should be ~0)
    int   activeSamples; // how many samples before isActive() returns false
    bool  hasNaN;
    bool  hasInf;
    bool  hasDenormal;
    // CPU metrics
    double nsPerSample;
    double cpuPercent;   // estimated % of single core at 44.1kHz
};

static constexpr double SAMPLE_RATE = 44100.0;
static constexpr int    TEST_DURATION_SAMPLES = 44100 * 3; // 3 seconds
static constexpr int    WARMUP_TRIGGERS = 5;

// Shared analysis on a pre-rendered buffer
static TestResult analyzeBuffer(const char* name, const float* buffer, int activeSamples,
                                 double benchNsPerSample)
{
    TestResult r {};
    r.name = name;
    r.passed = true;
    r.activeSamples = activeSamples;
    r.nsPerSample = benchNsPerSample;
    r.cpuPercent = (benchNsPerSample / (1e9 / SAMPLE_RATE)) * 100.0;

    r.peakAmp = 0.0f;
    for (int i = 0; i < TEST_DURATION_SAMPLES; ++i)
        r.peakAmp = std::max(r.peakAmp, std::abs(buffer[i]));

    int rmsLen = std::min(TEST_DURATION_SAMPLES, (int)(SAMPLE_RATE * 0.5));
    double sumSq = 0.0;
    for (int i = 0; i < rmsLen; ++i)
        sumSq += static_cast<double>(buffer[i]) * buffer[i];
    r.rmsLevel = static_cast<float>(std::sqrt(sumSq / rmsLen));

    int dcStart = std::max(0, TEST_DURATION_SAMPLES - 1000);
    double dcSum = 0.0;
    for (int i = dcStart; i < TEST_DURATION_SAMPLES; ++i)
        dcSum += static_cast<double>(buffer[i]);
    r.dcOffset = static_cast<float>(dcSum / 1000.0);

    r.hasNaN = r.hasInf = r.hasDenormal = false;
    for (int i = 0; i < TEST_DURATION_SAMPLES; ++i)
    {
        if (std::isnan(buffer[i])) r.hasNaN = true;
        if (std::isinf(buffer[i])) r.hasInf = true;
        if (buffer[i] != 0.0f && std::abs(buffer[i]) < 1e-15f) r.hasDenormal = true;
    }

    if (r.hasNaN) r.passed = false;
    if (r.hasInf) r.passed = false;
    if (r.hasDenormal) r.passed = false;
    if (r.peakAmp > 1.5f) r.passed = false;
    if (std::abs(r.dcOffset) > 0.01f) r.passed = false;
    if (r.cpuPercent > 5.0) r.passed = false;
    if (r.activeSamples > TEST_DURATION_SAMPLES - 100) r.passed = false;

    return r;
}

template<typename Voice>
TestResult testDrumVoice(const char* name, Voice& voice)
{
    static float buffer[TEST_DURATION_SAMPLES];
    voice.prepare(SAMPLE_RATE);
    voice.trigger();
    int lastActive = 0;
    for (int i = 0; i < TEST_DURATION_SAMPLES; ++i)
    {
        buffer[i] = voice.tick();
        if (voice.isActive()) lastActive = i;
    }

    // CPU benchmark
    voice.prepare(SAMPLE_RATE);
    constexpr int BS = 44100, RUNS = 20;
    static float dummy[BS];
    auto t0 = std::chrono::high_resolution_clock::now();
    for (int r = 0; r < RUNS; ++r) { voice.trigger(); for (int i = 0; i < BS; ++i) dummy[i] = voice.tick(); }
    auto t1 = std::chrono::high_resolution_clock::now();
    double ns = std::chrono::duration<double, std::nano>(t1 - t0).count() / (RUNS * BS);

    return analyzeBuffer(name, buffer, lastActive, ns);
}

TestResult testBassVoice(const char* name, BassVoice& voice)
{
    static float buffer[TEST_DURATION_SAMPLES];
    voice.prepare(SAMPLE_RATE);
    voice.trigger(48, 1.0f);
    int lastActive = 0;
    for (int i = 0; i < TEST_DURATION_SAMPLES; ++i)
    {
        buffer[i] = voice.tick();
        if (voice.isActive()) lastActive = i;
    }

    voice.prepare(SAMPLE_RATE);
    constexpr int BS = 44100, RUNS = 20;
    static float dummy[BS];
    auto t0 = std::chrono::high_resolution_clock::now();
    for (int r = 0; r < RUNS; ++r) { voice.trigger(48, 1.0f); for (int i = 0; i < BS; ++i) dummy[i] = voice.tick(); }
    auto t1 = std::chrono::high_resolution_clock::now();
    double ns = std::chrono::duration<double, std::nano>(t1 - t0).count() / (RUNS * BS);

    return analyzeBuffer(name, buffer, lastActive, ns);
}

static void printResult(const TestResult& r)
{
    const char* status = r.passed ? "✅ PASS" : "❌ FAIL";
    printf("\n%s  %s\n", status, r.name);
    printf("  ├── Peak: %.4f  RMS: %.4f  DC: %.6f\n", r.peakAmp, r.rmsLevel, r.dcOffset);
    printf("  ├── Active: %d samples (%.2fs)\n", r.activeSamples, r.activeSamples / SAMPLE_RATE);
    printf("  ├── CPU: %.1f ns/sample  (%.3f%% @ 44.1kHz)\n", r.nsPerSample, r.cpuPercent);
    printf("  └── NaN:%s  Inf:%s  Denormal:%s\n",
           r.hasNaN ? "YES" : "no", r.hasInf ? "YES" : "no", r.hasDenormal ? "YES" : "no");

    // Guardrail details
    if (!r.passed)
    {
        printf("  ⚠️  FAILURES:");
        if (r.hasNaN)      printf(" [NaN detected]");
        if (r.hasInf)      printf(" [Inf detected]");
        if (r.hasDenormal) printf(" [Denormals]");
        if (r.peakAmp > 1.5f) printf(" [Peak>1.5: %.2f]", r.peakAmp);
        if (std::abs(r.dcOffset) > 0.01f) printf(" [DC offset: %.4f]", r.dcOffset);
        if (r.cpuPercent > 5.0) printf(" [CPU>5%%: %.1f%%]", r.cpuPercent);
        printf("\n");
    }
}

int main()
{
    printf("═══════════════════════════════════════════════════\n");
    printf("  VST Forge — DSP Voice Test Suite\n");
    printf("  Sample Rate: %.0f Hz\n", SAMPLE_RATE);
    printf("  Test Duration: %.1f sec\n", TEST_DURATION_SAMPLES / SAMPLE_RATE);
    printf("═══════════════════════════════════════════════════\n");

    int passed = 0, total = 0;

    // ── Test Kick ──
    {
        KickVoice kick;
        kick.setParams({ 60.0f, 0.45f, 0.40f, 0.80f, 0.30f, 0.50f });
        auto r = testDrumVoice("Kick (default)", kick);
        printResult(r);
        if (r.passed) passed++;
        total++;

        // Extreme params
        kick.setParams({ 40.0f, 0.80f, 1.0f, 1.0f, 1.0f, 1.0f });
        r = testDrumVoice("Kick (extreme)", kick);
        printResult(r);
        if (r.passed) passed++;
        total++;
    }

    // ── Test Snare ──
    {
        SnareVoice snare;
        snare.setParams({ 185.0f, 0.18f, 0.50f, 0.60f });
        auto r = testDrumVoice("Snare (default)", snare);
        printResult(r);
        if (r.passed) passed++;
        total++;

        snare.setParams({ 400.0f, 0.40f, 1.0f, 1.0f });
        r = testDrumVoice("Snare (extreme)", snare);
        printResult(r);
        if (r.passed) passed++;
        total++;
    }

    // ── Test Hats ──
    {
        HatsVoice hats;
        hats.setParams({ 0.08f, 0.50f, 0.30f });
        auto r = testDrumVoice("Hats (default)", hats);
        printResult(r);
        if (r.passed) passed++;
        total++;

        hats.setParams({ 0.50f, 1.0f, 1.0f });
        r = testDrumVoice("Hats (extreme)", hats);
        printResult(r);
        if (r.passed) passed++;
        total++;
    }

    // ── Test Bass ──
    {
        BassVoice bass;
        bass.setParams({ 800.0f, 0.15f, 0.20f, 0.30f, 0.00f });
        auto r = testBassVoice("Bass303 (default)", bass);
        printResult(r);
        if (r.passed) passed++;
        total++;

        bass.setParams({ 350.0f, 0.95f, 0.90f, 0.10f, 1.0f });
        r = testBassVoice("Bass303 (acid extreme)", bass);
        printResult(r);
        if (r.passed) passed++;
        total++;

        // Self-oscillation stress test
        bass.setParams({ 20000.0f, 1.0f, 1.0f, 1.0f, 1.0f });
        r = testBassVoice("Bass303 (self-osc stress)", bass);
        printResult(r);
        if (r.passed) passed++;
        total++;
    }

    // ── Summary ──
    printf("\n═══════════════════════════════════════════════════\n");
    printf("  Results: %d/%d passed\n", passed, total);
    if (passed == total)
        printf("  🎉 All Occam guardrails satisfied!\n");
    else
        printf("  ⚠️  %d guardrail violation(s) — investigate before shipping\n", total - passed);
    printf("═══════════════════════════════════════════════════\n\n");

    return (passed == total) ? 0 : 1;
}
