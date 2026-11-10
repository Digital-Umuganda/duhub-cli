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
    assert "not found" in (r.output or "") + (getattr(r, "stderr", None) or "")

def test_diarize_rejects_directory(tmp_path, monkeypatch):
    monkeypatch.setenv("DU_BASE_URL", "https://api.example")
    monkeypatch.setenv("DU_API_KEY", "k")
    r = runner.invoke(main.app, ["diarize", str(tmp_path)])
    assert r.exit_code == 1
    out = (r.output or "") + (getattr(r, "stderr", None) or "")
    assert "not a file" in out
    assert "Traceback" not in out

def test_diarize_malformed_segments_is_clean(tmp_path, monkeypatch):
    monkeypatch.setenv("DU_BASE_URL", "https://api.example")
    monkeypatch.setenv("DU_API_KEY", "k")
    wav = tmp_path / "a.wav"
    wav.write_bytes(b"RIFF" + b"\x00" * 10)
    with respx.mock:
        respx.post("https://api.example/diarize").mock(return_value=Response(200, json={"segments": "nope"}))
        r = runner.invoke(main.app, ["diarize", str(wav), "--format", "txt"])
    assert r.exit_code == 1
    out = (r.output or "") + (getattr(r, "stderr", None) or "")
    assert "invalid diarize response" in out
    assert "Traceback" not in out

def test_diarize_sends_idempotency_key(tmp_path, monkeypatch):
    monkeypatch.setenv("DU_BASE_URL", "https://api.example")
    monkeypatch.setenv("DU_API_KEY", "k")
    wav = tmp_path / "a.wav"
    wav.write_bytes(b"RIFF" + b"\x00" * 10)
    with respx.mock:
        route = respx.post("https://api.example/diarize").mock(
            return_value=Response(200, json={"segments": []})
        )
        r = runner.invoke(main.app, ["diarize", str(wav), "--idempotency-key", "idem-di"])
    assert r.exit_code == 0, r.output
    assert route.calls[0].request.headers["Idempotency-Key"] == "idem-di"

def test_mt_sends_idempotency_key(monkeypatch):
    monkeypatch.setenv("DU_BASE_URL", "https://api.example")
    monkeypatch.setenv("DU_API_KEY", "k")
    with respx.mock:
        route = respx.post("https://api.example/mt").mock(
            return_value=Response(200, json={"translation": "hello"})
        )
        r = runner.invoke(main.app, ["mt", "muraho", "--idempotency-key", "idem-mt"])
    assert r.exit_code == 0, r.output
    assert route.calls[0].request.headers["Idempotency-Key"] == "idem-mt"
