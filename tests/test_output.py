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

def test_render_segments_srt_rounds_at_minute_boundary():
    segs = [{"speaker": 0, "start": 59.9994, "end": 59.9999, "text": "x"}]
    s = output.render_segments(segs, "srt")
    assert "00:00:59,999 --> 00:01:00,000" in s

def test_print_err_escapes_rich_markup(capsys):
    output.print_err("[bold red]boom[/]", "hint", False)
    err = capsys.readouterr().err
    assert "[bold red]boom[/]" in err
    assert "\x1b[1;31m" not in err
