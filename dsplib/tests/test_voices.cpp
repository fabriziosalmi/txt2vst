// VST Forge — DSP Test Harness (13 voice archetypes + 5 FX)
// Occam Guardrails: NaN/Inf, peak<1.5, DC<0.01, CPU<5%, deactivation, denormals
#include <cmath>
#include <cstdio>
#include <cstring>
#include <chrono>
#include <algorithm>

#include "../voices/kick.h"
#include "../voices/snare.h"
#include "../voices/hats.h"
#include "../voices/tom.h"
#include "../voices/perc.h"
#include "../voices/clap.h"
#include "../voices/bass.h"
#include "../voices/pad.h"
#include "../voices/lead.h"
#include "../voices/pluck.h"
#include "../voices/organ.h"
#include "../voices/fm_synth.h"
#include "../voices/noise.h"
#include "../fx/delay.h"
#include "../fx/reverb.h"
#include "../fx/chorus.h"
#include "../fx/compressor.h"
#include "../fx/distortion.h"

struct TestResult {
    const char* name; bool passed;
    float peakAmp, rmsLevel, dcOffset;
    int activeSamples; bool hasNaN, hasInf, hasDenormal;
    double nsPerSample, cpuPercent;
};

static constexpr double SR = 44100.0;
static constexpr int DUR = 44100 * 3;

static TestResult analyze(const char* name, const float* buf, int active, double ns) {
    TestResult r{}; r.name = name; r.passed = true;
    r.activeSamples = active; r.nsPerSample = ns;
    r.cpuPercent = (ns / (1e9 / SR)) * 100.0;
    r.peakAmp = 0.0f;
    for (int i = 0; i < DUR; ++i) r.peakAmp = std::max(r.peakAmp, std::abs(buf[i]));
    int rmsLen = std::min(DUR, (int)(SR * 0.5));
    double sq = 0; for (int i = 0; i < rmsLen; ++i) sq += (double)buf[i] * buf[i];
    r.rmsLevel = (float)std::sqrt(sq / rmsLen);
    double dc = 0; for (int i = DUR - 1000; i < DUR; ++i) dc += buf[i];
    r.dcOffset = (float)(dc / 1000.0);
    r.hasNaN = r.hasInf = r.hasDenormal = false;
    for (int i = 0; i < DUR; ++i) {
        if (std::isnan(buf[i])) r.hasNaN = true;
        if (std::isinf(buf[i])) r.hasInf = true;
        if (buf[i] != 0.0f && std::abs(buf[i]) < 1e-15f) r.hasDenormal = true;
    }
    if (r.hasNaN || r.hasInf || r.hasDenormal) r.passed = false;
    if (r.peakAmp > 1.5f || std::abs(r.dcOffset) > 0.01f) r.passed = false;
    if (r.cpuPercent > 5.0 || r.activeSamples > DUR - 100) r.passed = false;
    return r;
}

static TestResult analyzeFX(const char* name, const float* buf, double ns) {
    TestResult r{}; r.name = name; r.passed = true;
    r.activeSamples = 0; r.nsPerSample = ns;
    r.cpuPercent = (ns / (1e9 / SR)) * 100.0;
    r.peakAmp = 0.0f;
    for (int i = 0; i < DUR; ++i) r.peakAmp = std::max(r.peakAmp, std::abs(buf[i]));
    double dc = 0; for (int i = DUR - 1000; i < DUR; ++i) dc += buf[i];
    r.dcOffset = (float)(dc / 1000.0);
    r.hasNaN = r.hasInf = r.hasDenormal = false;
    for (int i = 0; i < DUR; ++i) {
        if (std::isnan(buf[i])) r.hasNaN = true;
        if (std::isinf(buf[i])) r.hasInf = true;
    }
    int rmsLen = std::min(DUR, (int)(SR * 0.5));
    double sq = 0; for (int i = 0; i < rmsLen; ++i) sq += (double)buf[i] * buf[i];
    r.rmsLevel = (float)std::sqrt(sq / rmsLen);
    if (r.hasNaN || r.hasInf) r.passed = false;
    if (r.peakAmp > 1.5f || std::abs(r.dcOffset) > 0.01f) r.passed = false;
    if (r.cpuPercent > 5.0) r.passed = false;
    return r;
}

template<typename V> TestResult testDrum(const char* n, V& v) {
    static float buf[DUR]; v.prepare(SR); v.trigger();
    int last = 0;
    for (int i = 0; i < DUR; ++i) { buf[i] = v.tick(); if (v.isActive()) last = i; }
    v.prepare(SR); static float d[44100];
    auto t0 = std::chrono::high_resolution_clock::now();
    for (int r = 0; r < 20; ++r) { v.trigger(); for (int i = 0; i < 44100; ++i) d[i] = v.tick(); }
    auto t1 = std::chrono::high_resolution_clock::now();
    return analyze(n, buf, last, std::chrono::duration<double,std::nano>(t1-t0).count()/(20*44100));
}

template<typename V> TestResult testPitched(const char* n, V& v) {
    static float buf[DUR]; v.prepare(SR); v.trigger(48, 1.0f);
    int last = 0;
    for (int i = 0; i < DUR; ++i) { buf[i] = v.tick(); if (v.isActive()) last = i; }
    v.prepare(SR); static float d[44100];
    auto t0 = std::chrono::high_resolution_clock::now();
    for (int r = 0; r < 20; ++r) { v.trigger(48,1.0f); for (int i = 0; i < 44100; ++i) d[i] = v.tick(); }
    auto t1 = std::chrono::high_resolution_clock::now();
    return analyze(n, buf, last, std::chrono::duration<double,std::nano>(t1-t0).count()/(20*44100));
}

static void pr(const TestResult& r) {
    printf("\n%s  %s\n", r.passed?"PASS ":"FAIL ", r.name);
    printf("  | Peak:%.4f RMS:%.4f DC:%.6f Active:%.2fs\n", r.peakAmp,r.rmsLevel,r.dcOffset,r.activeSamples/SR);
    printf("  | CPU:%.1fns (%.3f%%) NaN:%s Inf:%s Den:%s\n", r.nsPerSample,r.cpuPercent,
           r.hasNaN?"Y":"n",r.hasInf?"Y":"n",r.hasDenormal?"Y":"n");
}

int main() {
    printf("=====================================================\n");
    printf("  txt2vst DSP Test Suite (13 voices + 5 FX)\n");
    printf("=====================================================\n");
    int ok=0,tot=0;
    auto run = [&](TestResult r){ pr(r); if(r.passed)ok++; tot++; };

    // Voice archetypes (20 tests)
    { KickVoice v; v.setParams({60,0.45f,0.4f,0.8f,0.3f,0.5f}); run(testDrum("Kick",v)); }
    { KickVoice v; v.setParams({40,0.8f,1,1,1,1}); run(testDrum("Kick(max)",v)); }
    { SnareVoice v; v.setParams({185,0.18f,0.5f,0.6f}); run(testDrum("Snare",v)); }
    { SnareVoice v; v.setParams({400,0.4f,1,1}); run(testDrum("Snare(max)",v)); }
    { HatsVoice v; v.setParams({0.08f,0.5f,0.3f}); run(testDrum("Hats",v)); }
    { HatsVoice v; v.setParams({0.5f,1,1}); run(testDrum("Hats(max)",v)); }
    { TomVoice v; v.setParams({90,0.3f,0.65f,0.2f}); run(testDrum("Tom",v)); }
    { TomVoice v; v.setParams({200,0.8f,1,1}); run(testDrum("Tom(max)",v)); }
    { PercVoice v; v.setParams({600,0.1f,0.4f,0.3f}); run(testDrum("Perc/FM",v)); }
    { PercVoice v; v.setParams({2000,0.5f,1,1}); run(testDrum("Perc(max)",v)); }
    { ClapVoice v; v.setParams({0.2f,0.5f,0.4f}); run(testDrum("Clap",v)); }
    { ClapVoice v; v.setParams({0.5f,1,1}); run(testDrum("Clap(max)",v)); }
    { BassVoice v; v.setParams({800,0.15f,0.2f,0.3f,0}); run(testPitched("Bass303",v)); }
    { BassVoice v; v.setParams({350,0.95f,0.9f,0.1f,1}); run(testPitched("Bass(acid)",v)); }
    { BassVoice v; v.setParams({20000,1,1,1,1}); run(testPitched("Bass(stress)",v)); }
    { PadVoice v; v.setParams({2000,0.2f,0.3f,1.5f,0.1f}); run(testPitched("Pad",v)); }
    { LeadVoice v; v.setParams({4000,0.3f,0.5f,0.5f,0.3f}); run(testPitched("Lead",v)); }
    { LeadVoice v; v.setParams({18000,0.95f,0.1f,0.1f,1}); run(testPitched("Lead(stress)",v)); }
    { PluckVoice v; v.setParams({0.8f,0.5f,0.3f}); run(testPitched("Pluck",v)); }
    { PluckVoice v; v.setParams({3.0f,1,1}); run(testPitched("Pluck(long)",v)); }

    // New voice archetypes (6 tests)
    { OrganVoice v; run(testPitched("Organ",v)); }
    { OrganVoice v; v.setParams({{1,1,1,1,1,1,1,1,1},0.01f,1.0f}); run(testPitched("Organ(full)",v)); }
    { FMSynthVoice v; run(testPitched("FMSynth",v)); }
    { FMSynthVoice v; v.setParams({7.0f,5.0f,0.1f,1.0f,0.8f}); run(testPitched("FM(stress)",v)); }
    { NoiseVoice v; run(testPitched("Noise",v)); }
    { NoiseVoice v; v.setParams({15000,0.9f,0.3f,0.0f}); run(testPitched("Noise(white)",v)); }

    // FX archetypes (5 tests)
    printf("\n  --- FX Archetypes ---");
    {
        static float bufL[DUR], bufR[DUR];
        for (int i = 0; i < DUR; ++i) {
            float env = (i < 4410) ? 1.0f : 0.0f;
            bufL[i] = bufR[i] = env * 0.5f * std::sin(2.0 * 3.14159265 * 440.0 * i / SR);
        }
        {
            float tL[DUR], tR[DUR]; std::copy(bufL, bufL+DUR, tL); std::copy(bufR, bufR+DUR, tR);
            DelayFX fx; fx.prepare(SR); fx.setParams({0.375f, 0.7f, 0.5f, 0.5f, false});
            auto t0=std::chrono::high_resolution_clock::now();
            fx.process(tL, tR, DUR);
            auto t1=std::chrono::high_resolution_clock::now();
            run(analyzeFX("FX:Delay", tL, std::chrono::duration<double,std::nano>(t1-t0).count()/DUR));
        }
        {
            float tL[DUR], tR[DUR]; std::copy(bufL, bufL+DUR, tL); std::copy(bufR, bufR+DUR, tR);
            ReverbFX fx; fx.prepare(SR); fx.setParams({0.8f, 0.5f, 0.4f, 0.02f});
            auto t0=std::chrono::high_resolution_clock::now();
            fx.process(tL, tR, DUR);
            auto t1=std::chrono::high_resolution_clock::now();
            run(analyzeFX("FX:Reverb", tL, std::chrono::duration<double,std::nano>(t1-t0).count()/DUR));
        }
        {
            float tL[DUR], tR[DUR]; std::copy(bufL, bufL+DUR, tL); std::copy(bufR, bufR+DUR, tR);
            ChorusFX fx; fx.prepare(SR); fx.setParams({1.5f, 0.8f, 0.5f});
            auto t0=std::chrono::high_resolution_clock::now();
            fx.process(tL, tR, DUR);
            auto t1=std::chrono::high_resolution_clock::now();
            run(analyzeFX("FX:Chorus", tL, std::chrono::duration<double,std::nano>(t1-t0).count()/DUR));
        }
        {
            float tL[DUR], tR[DUR]; std::copy(bufL, bufL+DUR, tL); std::copy(bufR, bufR+DUR, tR);
            CompressorFX fx; fx.prepare(SR); fx.setParams({0.3f, 0.7f, 0.005f, 0.05f, 0.5f});
            auto t0=std::chrono::high_resolution_clock::now();
            fx.process(tL, tR, DUR);
            auto t1=std::chrono::high_resolution_clock::now();
            run(analyzeFX("FX:Compressor", tL, std::chrono::duration<double,std::nano>(t1-t0).count()/DUR));
        }
        {
            float tL[DUR], tR[DUR]; std::copy(bufL, bufL+DUR, tL); std::copy(bufR, bufR+DUR, tR);
            DistortionFX fx; fx.prepare(SR); fx.setParams({0.8f, 0.5f, 0.7f});
            auto t0=std::chrono::high_resolution_clock::now();
            fx.process(tL, tR, DUR);
            auto t1=std::chrono::high_resolution_clock::now();
            run(analyzeFX("FX:Distortion", tL, std::chrono::duration<double,std::nano>(t1-t0).count()/DUR));
        }
    }

    printf("\n=====================================================\n");
    printf("  Results: %d/%d passed\n", ok, tot);
    printf("  %s\n", ok==tot?"All Occam guardrails satisfied!":"Violations detected!");
    printf("=====================================================\n\n");
    return ok==tot?0:1;
}
