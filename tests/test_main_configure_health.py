# cli/tests/test_main_configure_health.py
import respx
from httpx import Response
from typer.testing import CliRunner
from du_cli import main, config

runner = CliRunner()

def test_configure_writes_file(tmp_path, monkeypatch):
    f = tmp_path / "config.toml"
    monkeypatch.setattr(config, "CONFIG_PATH", f)
    r = runner.invoke(main.app, ["configure", "--base-url", "https://x.example", "--api-key", "k"])
    assert r.exit_code == 0, r.output
    assert "saved" in r.output.lower()

def test_health_ok(monkeypatch):
    monkeypatch.setenv("DU_BASE_URL", "https://api.example")
    monkeypatch.setenv("DU_API_KEY", "k")
    with respx.mock:
        respx.get("https://api.example/health").mock(return_value=Response(200, json={"status": "ok"}))
        r = runner.invoke(main.app, ["health"])
    assert r.exit_code == 0, r.output

def test_health_needs_no_api_key(tmp_path, monkeypatch):
    f = tmp_path / "config.toml"
    monkeypatch.setattr(config, "CONFIG_PATH", f)
    monkeypatch.setenv("DU_BASE_URL", "https://api.example")
    monkeypatch.delenv("DU_API_KEY", raising=False)
    with respx.mock:
        route = respx.get("https://api.example/health").mock(return_value=Response(200, json={"status": "ok"}))
        r = runner.invoke(main.app, ["health"])
    assert r.exit_code == 0, r.output
    assert route.called
    assert "x-api-key" not in route.calls[0].request.headers

def test_health_401_hint(monkeypatch):
    monkeypatch.setenv("DU_BASE_URL", "https://api.example")
    monkeypatch.setenv("DU_API_KEY", "bad")
    with respx.mock:
        respx.get("https://api.example/health").mock(return_value=Response(401, text="bad key"))
        r = runner.invoke(main.app, ["health"])
    assert r.exit_code == 1
    assert "du configure" in r.output + (r.stderr or "")

def test_version_and_health_json_single_object(monkeypatch):
    import json as _json
    r = runner.invoke(main.app, ["--version"])
    assert r.exit_code == 0
    assert r.output.strip() == f"du {main.__version__}"
    monkeypatch.setenv("DU_BASE_URL", "https://api.example")
    monkeypatch.setenv("DU_API_KEY", "k")
    with respx.mock:
        respx.get("https://api.example/health").mock(
            return_value=Response(200, json={"status": "ok"}, headers={"X-Request-ID": "h1"})
        )
        r = runner.invoke(main.app, ["health", "--json"])
    assert r.exit_code == 0, r.output
    assert _json.loads(r.output)["data"] == {"status": "ok"}

def test_offline_server_hint_no_traceback(monkeypatch):
    monkeypatch.setenv("DU_BASE_URL", "http://127.0.0.1:1")
    monkeypatch.setenv("DU_API_KEY", "k")
    r = runner.invoke(main.app, ["health"])
    assert r.exit_code == 1
    out = (r.output or "") + (getattr(r, "stderr", None) or "")
    assert "cannot reach server" in out
    assert "Traceback" not in out
