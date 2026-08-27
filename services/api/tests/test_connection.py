from fitness_api.connection import (
    connection_public_view,
    load_connection,
    save_connection,
)


def test_load_missing_file_returns_empty(tmp_path):
    assert load_connection(tmp_path / "zepp.env").model_dump() == {
        "user_id": None,
        "app_token": None,
    }


def test_save_and_load_round_trip(tmp_path):
    path = tmp_path / "nested" / "zepp.env"
    save_connection(path, user_id="42", app_token="secret-token-9999", replace_token=True)
    loaded = load_connection(path)
    assert loaded.user_id == "42"
    assert loaded.app_token == "secret-token-9999"
    assert path.read_text(encoding="utf-8").startswith("ZEPP_")


def test_save_without_replace_keeps_existing_token(tmp_path):
    path = tmp_path / "zepp.env"
    save_connection(path, user_id="1", app_token="keep-me-1234", replace_token=True)
    save_connection(path, user_id="2", app_token=None, replace_token=False)
    loaded = load_connection(path)
    assert loaded.user_id == "2"
    assert loaded.app_token == "keep-me-1234"


def test_public_view_masks_token():
    from fitness_api.connection import ConnectionSecrets

    view = connection_public_view(
        ConnectionSecrets(user_id="9", app_token="abcdefghijklmnop")
    )
    assert view == {
        "user_id": "9",
        "token_set": True,
        "token_hint": "mnop",
    }
    assert "abcdef" not in str(view)


def test_public_view_when_token_missing():
    from fitness_api.connection import ConnectionSecrets

    assert connection_public_view(ConnectionSecrets()) == {
        "user_id": None,
        "token_set": False,
        "token_hint": None,
    }
