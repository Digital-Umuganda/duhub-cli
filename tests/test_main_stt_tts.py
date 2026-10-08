# cli/tests/test_main_stt_tts.py
from pathlib import Path
import respx
from httpx import Response
from typer.testing import CliRunner
from du_cli import main

runner = CliRunner()

def test_stt_posts_file_and_writes_json(tmp_path, monkeypatch):
    monkeypatch.setenv("DU_BASE_URL", "https://api.example")
    monkeypatch.setenv("DU_API_KEY", "k")
    wav = tmp_path / "a.wav"
    wav.write_bytes(b"RIFF" + b"\x00" * 100)
    out = tmp_path / "t.json"
    with respx.mock:
        route = respx.post("https://api.example/stt").mock(
            return_value=Response(200, json={"text": "muraho"}, headers={"X-Units": "1.2", "X-Request-ID": "r1"})
        )
        r = runner.invoke(main.app, ["stt", str(wav), "-o", str(out)])
    assert r.exit_code == 0, r.output
    assert route.called
    assert "muraho" in out.read_text()

def test_tts_saves_wav(tmp_path, monkeypatch):
    monkeypatch.setenv("DU_BASE_URL", "https://api.example")
    monkeypatch.setenv("DU_API_KEY", "k")
    out = tmp_path / "o.wav"
    with respx.mock:
        respx.post("https://api.example/tts").mock(return_value=Response(200, content=b"WAVBYTES", headers={"X-Units": "3"}))
        r = runner.invoke(main.app, ["tts", "Muraho", "-o", str(out)])
    assert r.exit_code == 0, r.output
    assert out.read_bytes() == b"WAVBYTES"

def test_stt_rejects_missing_file(monkeypatch):
    monkeypatch.setenv("DU_BASE_URL", "https://api.example")
    monkeypatch.setenv("DU_API_KEY", "k")
    r = runner.invoke(main.app, ["stt", "/nope.wav"])
    assert r.exit_code == 1

def test_tts_missing_text_file_exits_1_no_traceback(tmp_path, monkeypatch):
    monkeypatch.setenv("DU_BASE_URL", "https://api.example")
    monkeypatch.setenv("DU_API_KEY", "k")
    r = runner.invoke(main.app, ["tts", "-o", str(tmp_path / "o.wav"), "--text-file", "/nope.txt"])
    assert r.exit_code == 1
    assert "Traceback" not in (r.output or "")

def test_stt_json_is_single_object(tmp_path, monkeypatch):
    import json as _json
    monkeypatch.setenv("DU_BASE_URL", "https://api.example")
    monkeypatch.setenv("DU_API_KEY", "k")
    wav = tmp_path / "a.wav"
    wav.write_bytes(b"RIFF" + b"\x00" * 10)
    with respx.mock:
        respx.post("https://api.example/stt").mock(
            return_value=Response(200, json={"text": "muraho"}, headers={"X-Units": "1.2"})
        )
        r = runner.invoke(main.app, ["stt", str(wav), "--json"])
    assert r.exit_code == 0, r.output
    body = _json.loads(r.output)
    assert body["data"] == {"text": "muraho"}
    assert body["units"] == "1.2"

def test_tts_text_file_overrides_positional(tmp_path, monkeypatch):
    monkeypatch.setenv("DU_BASE_URL", "https://api.example")
    monkeypatch.setenv("DU_API_KEY", "k")
    tf = tmp_path / "t.txt"
    tf.write_text("file text wins")
    out = tmp_path / "o.wav"
    with respx.mock:
        route = respx.post("https://api.example/tts").mock(return_value=Response(200, content=b"W"))
        r = runner.invoke(main.app, ["tts", "ignored", "-o", str(out), "--text-file", str(tf)])
    assert r.exit_code == 0, r.output
    assert route.called
    import json as _json
    assert _json.loads(route.calls[0].request.content) == {"text": "file text wins"}
