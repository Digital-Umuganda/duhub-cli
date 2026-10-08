# cli/tests/test_config.py
from du_cli import config

def test_load_prefers_env_over_file(tmp_path, monkeypatch):
    f = tmp_path / "config.toml"
    f.write_text('base_url = "https://file.example"\napi_key = "file-key"\n')
    monkeypatch.setattr(config, "CONFIG_PATH", f)
    monkeypatch.setenv("DU_BASE_URL", "https://env.example")
    monkeypatch.setenv("DU_API_KEY", "env-key")
    got = config.load_config()
    assert got == {"base_url": "https://env.example", "api_key": "env-key"}

def test_load_default_base_and_save_roundtrip(tmp_path, monkeypatch):
    f = tmp_path / "config.toml"
    monkeypatch.setattr(config, "CONFIG_PATH", f)
    monkeypatch.delenv("DU_BASE_URL", raising=False)
    monkeypatch.delenv("DU_API_KEY", raising=False)
    config.save_config("https://file.example", "k1")
    got = config.load_config()
    assert got == {"base_url": "https://file.example", "api_key": "k1"}
    config.clear_config()
    assert not f.exists()
    got2 = config.load_config()
    assert got2["base_url"] == "https://du-api.dev.umuganda.digital"
    assert got2["api_key"] == ""

def test_corrupt_toml_falls_back_to_defaults(tmp_path, monkeypatch):
    f = tmp_path / "config.toml"
    f.write_text("base_url = [broken\n")
    monkeypatch.setattr(config, "CONFIG_PATH", f)
    monkeypatch.delenv("DU_BASE_URL", raising=False)
    monkeypatch.delenv("DU_API_KEY", raising=False)
    got = config.load_config()
    assert got == {"base_url": "https://du-api.dev.umuganda.digital", "api_key": ""}
