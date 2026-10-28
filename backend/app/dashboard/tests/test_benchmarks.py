from app.dashboard.benchmarks import compare_to_benchmark


def test_margin_within_range():
    result = compare_to_benchmark("Retail", 28.0)
    assert result.position == "within"
    assert result.benchmark_low_pct == 20.0
    assert result.benchmark_high_pct == 35.0


def test_margin_below_range():
    result = compare_to_benchmark("Retail", 10.0)
    assert result.position == "below"


def test_margin_above_range():
    result = compare_to_benchmark("Retail", 50.0)
    assert result.position == "above"


def test_unknown_industry_returns_none():
    assert compare_to_benchmark("Space Tourism", 28.0) is None
    assert compare_to_benchmark(None, 28.0) is None
