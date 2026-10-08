# cli/tests/test_output.py
import json
from du_cli import output

def test_summary_line():
    s = output.summary_line("2.5", "HIT", "abc")
    assert "2.5" in s and "HIT" in s and "abc" in s

def test_render_segments_json_txt_srt():
    segs = [{"speaker": 0, "start": 0.0, "end": 1.2, "text": "muraho"}]
    j = output.render_segments(segs, "json")
    assert json.loads(j) == segs
    t = output.render_segments(segs, "txt")
    assert "Speaker 0" in t and "muraho" in t
    s = output.render_segments(segs, "srt")
    assert "-->" in s and "muraho" in s
