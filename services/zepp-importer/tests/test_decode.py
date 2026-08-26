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


def test_decode_collapses_duplicate_elapsed_keeping_last_bpm():
    # dt=0 and negative dt can revisit an elapsed_s; PK keeps last BPM
    assert decode_heart_rate("10,100;0,5;2,-1") == [(10, 105), (12, 104)]
    assert decode_heart_rate("5,90;3,1;-1,2;2,0") == [
        (5, 90),
        (7, 93),
        (8, 91),
        (9, 93),
    ]
