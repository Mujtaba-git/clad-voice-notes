import pytest

from voicenotes.config import Settings, data_dir, load_settings, save_settings


def test_defaults_are_valid():
    s = Settings()
    s.validate()
    assert s.language == "auto"
    assert s.translator == "llm"


def test_roundtrip(tmp_path):
    p = tmp_path / "s.json"
    s = Settings(language="ur", vault_dir="/tmp/vault")
    save_settings(s, p)
    assert load_settings(p) == s


def test_missing_file_gives_defaults(tmp_path):
    assert load_settings(tmp_path / "none.json") == Settings()


def test_unknown_keys_in_file_are_ignored(tmp_path):
    p = tmp_path / "s.json"
    p.write_text('{"language": "en", "obsolete": 1}')
    assert load_settings(p).language == "en"


def test_updated_validates():
    with pytest.raises(ValueError):
        Settings().updated(language="fr")
    with pytest.raises(ValueError):
        Settings().updated(nope=1)
    assert Settings().updated(language="ur").language == "ur"


def test_notes_dir_uses_vault(tmp_path):
    s = Settings(vault_dir=str(tmp_path), notes_subfolder="Inbox")
    assert s.notes_dir() == tmp_path / "Inbox"


def test_data_dir_env_override(isolated_home):
    assert data_dir() == isolated_home
