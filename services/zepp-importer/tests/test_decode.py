import pytest

from fitness.normalize.decode import decode_heart_rate


def test_decode_absolute_then_deltas():
    # 15s @ 98, +5s Δ0 → 98, +2s Δ-1 → 97
    assert decode_heart_rate("15,98;5,0;2,-1") == [(15, 98), (20, 98), (22, 97)]


def test_decode_empty():
    assert decode_heart_rate("") == []


def test_decode_keeps_zero_bpm():
    assert decode_heart_rate("1,80;1,-80") == [(1, 80), (2, 0)]


def test_decode_rejects_bad_segment():
    with pytest.raises(ValueError):
        decode_heart_rate("15,98;nope")
