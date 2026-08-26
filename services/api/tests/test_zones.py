from fitness_api.zones import assign_zone, suggest_hrmax, time_in_zones, splat_minutes


def test_assign_zone_otf_bands():
    # Half-open % cutovers: below if pct < 50; z1 if 50 <= pct < 61; etc.
    assert assign_zone(79, 160) == "below"  # 49.375%
    assert assign_zone(80, 160) == "z1"  # 50%
    assert assign_zone(81, 160) == "z1"  # 50.625%
    assert assign_zone(112, 160) == "z2"  # 70% — upper bound of z2 (61-70 inclusive)
    assert assign_zone(114, 160) == "z3"  # 71.25%
    assert assign_zone(147, 160) == "z4"  # 91.875% — upper bound of z4 (84-91 inclusive)
    assert assign_zone(148, 160) == "z5"  # 92.5% — 92% threshold = 147.2 bpm
    assert assign_zone(200, 160) == "z5"


def test_suggest_hrmax_percentile():
    samples = list(range(100, 181))  # 100..180
    assert suggest_hrmax(samples, 0.99) == 180


def test_time_in_zones_and_splat():
    # 0@100, 60@140, 120@150 with hrmax 160 → durations 60s, 60s
    series = [(0, 100), (60, 140), (120, 150)]
    t = time_in_zones(series, 160.0)
    assert t["z2"] == 60.0  # 100/160=62.5% → z2
    assert t["z4"] == 60.0  # 140/160=87.5% → z4
    assert splat_minutes(t) == 1.0
