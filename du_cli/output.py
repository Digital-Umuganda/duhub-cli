"""Human (Rich) vs machine (--json) output. No binary to stdout."""
from __future__ import annotations
import json
import sys
from pathlib import Path
from rich.console import Console

_console = Console()
_console_err = Console(stderr=True)

def summary_line(units: str | None, cache: str | None, request_id: str | None) -> str:
    parts = []
    if units is not None:
        parts.append(f"units={units}")
    if cache is not None:
        parts.append(f"cache={cache}")
    if request_id is not None:
        parts.append(f"request-id={request_id}")
    return " ".join(parts) if parts else "ok"

def render_segments(segments: list[dict], fmt: str) -> str:
    if fmt == "json":
        return json.dumps(segments, ensure_ascii=False, indent=2)
    if fmt == "txt":
        return "\n".join(f"[Speaker {s.get('speaker')}] {s.get('text', '')}" for s in segments)
    if fmt == "srt":
        def ts(x: float) -> str:
            h = int(x // 3600); m = int((x % 3600) // 60); sec = x % 60
            return f"{h:02d}:{m:02d}:{sec:06.3f}".replace(".", ",")
        lines = []
        for i, s in enumerate(segments, 1):
            lines.append(str(i))
            lines.append(f"{ts(float(s.get('start', 0)))} --> {ts(float(s.get('end', 0)))}")
            lines.append(f"[Speaker {s.get('speaker')}] {s.get('text', '')}")
            lines.append("")
        return "\n".join(lines)
    raise ValueError(f"unknown format: {fmt}")

def print_ok(summary: dict[str, str], as_json: bool) -> None:
    if as_json:
        print(json.dumps(summary, ensure_ascii=False))
    else:
        _console.print(f"[green]ok[/green] {summary_line(summary.get('units'), summary.get('cache'), summary.get('request_id'))}")

def print_err(error: str, hint: str, as_json: bool) -> None:
    if as_json:
        print(json.dumps({"error": error, "hint": hint}, ensure_ascii=False), file=sys.stderr)
    else:
        _console_err.print(f"[red]error:[/red] {error}\nhint: {hint}")

def present(text: str, summary: dict[str, str], as_json: bool, o: str | None) -> None:
    """One payload outlet: -o writes the raw file; stdout is a single JSON
    object under --json, else raw text plus the human ok-line."""
    if o:
        Path(o).write_text(text)
        print_ok(summary, as_json)
        return
    if as_json:
        try:
            data = json.loads(text)
        except ValueError:
            data = text
        print(json.dumps({"data": data, **summary}, ensure_ascii=False))
    else:
        print(text)
        print_ok(summary, False)
