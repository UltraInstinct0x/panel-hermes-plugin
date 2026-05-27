import random

from panel_hermes_plugin._sampler import TraceSampler


def test_deterministic_sampling_seeded():
    s1 = TraceSampler(sample_rate=0.5, rng=random.Random(42))
    s2 = TraceSampler(sample_rate=0.5, rng=random.Random(42))
    m = [{"role": "user", "content": "same"}]
    assert s1.should_sample_trace(m) == s2.should_sample_trace(m)


def test_error_always_sampled():
    sampler = TraceSampler(sample_rate=0.0)
    sampled, reason = sampler.should_sample_unit("x", {"error": True})
    assert sampled is True
    assert reason == "error"


def test_novelty_triggered_then_baseline():
    sampler = TraceSampler(sample_rate=0.0)
    m = [{"role": "user", "content": "novel prompt"}]
    first = sampler.should_sample_trace(m)
    second = sampler.should_sample_trace(m)
    assert first == (True, "novelty")
    assert second == (False, "baseline")
