import respx
from httpx import Response
from typer.testing import CliRunner
from du_cli import main

runner = CliRunner()

def test_mt_validates_langs(monkeypatch):
    monkeypatch.setenv("DU_BASE_URL", "https://api.example")
    monkeypatch.setenv("DU_API_KEY", "k")
    r = runner.invoke(main.app, ["mt", "hello", "--src", "rw", "--tgt", "rw"])
    assert r.exit_code == 1

def test_mt_posts_json(monkeypatch):
    monkeypatch.setenv("DU_BASE_URL", "https://api.example")
    monkeypatch.setenv("DU_API_KEY", "k")
    with respx.mock:
        route = respx.post("https://api.example/mt").mock(return_value=Response(200, json={"translation": "hello"}))
        r = runner.invoke(main.app, ["mt", "muraho", "--src", "rw", "--tgt", "en"])
    assert r.exit_code == 0, r.output
    assert route.called

def test_diarize_srt_format(tmp_path, monkeypatch):
    monkeypatch.setenv("DU_BASE_URL", "https://api.example")
    monkeypatch.setenv("DU_API_KEY", "k")
    wav = tmp_path / "a.wav"
    wav.write_bytes(b"RIFF" + b"\x00" * 10)
    segs = [{"speaker": 0, "start": 0.0, "end": 1.2, "text": "muraho"}]
    with respx.mock:
        respx.post("https://api.example/diarize").mock(return_value=Response(200, json={"segments": segs}))
        r = runner.invoke(main.app, ["diarize", str(wav), "--format", "srt"])
    assert r.exit_code == 0, r.output
    assert "-->" in r.output

def test_diarize_404_hint(tmp_path, monkeypatch):
    monkeypatch.setenv("DU_BASE_URL", "https://api.example")
    monkeypatch.setenv("DU_API_KEY", "k")
    wav = tmp_path / "a.wav"
    wav.write_bytes(b"RIFF" + b"\x00" * 10)
    with respx.mock:
        respx.post("https://api.example/diarize").mock(return_value=Response(404, text="nope"))
        r = runner.invoke(main.app, ["diarize", str(wav)])
    assert r.exit_code == 1
    assert "not deployed yet" in (r.output or "") + (getattr(r, "stderr", None) or "")
