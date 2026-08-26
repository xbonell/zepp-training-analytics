from datetime import date

from fitness_api.profile import Profile, load_profile, save_profile


def test_profile_round_trip(tmp_path):
    path = tmp_path / "nested" / "profile.json"
    profile = Profile(
        sex="female",
        birth_date=date(1990, 5, 17),
        resting_hr=52,
        hrmax_override=188,
        theme_preference="dark",
        display_timezone="Europe/Madrid",
    )

    save_profile(profile, path)

    assert load_profile(path) == profile
    assert path.read_text(encoding="utf-8").endswith("\n")


def test_profile_defaults_when_file_is_missing(tmp_path):
    assert load_profile(tmp_path / "missing.json") == Profile()
