from fitness_api.sports import sport_label


def test_sport_label_known_types():
    assert sport_label(1) == "Outdoor Running"
    assert sport_label(6) == "Walking"
    assert sport_label(9) == "Outdoor Cycling"
    assert sport_label(10) == "Indoor Cycling"
    assert sport_label(16) == "Freestyle"
    assert sport_label(22) == "Hiking"
    assert sport_label(24) == "Indoor Fitness"
    assert sport_label(40) == "Indoor Walk"


def test_sport_label_unknown_and_none():
    assert sport_label(99) == "Sport 99"
    assert sport_label(None) == "Unknown"
