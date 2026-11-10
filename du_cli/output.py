"""Human (Rich) vs machine (--json) output. No binary to stdout."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import typer
from rich.console import Console
from rich.markup import escape

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
            total_ms = round(float(x) * 1000)
            h, rem = divmod(total_ms, 3_600_000)
            m, rem = divmod(rem, 60_000)
            sec, ms = divmod(rem, 1000)
            return f"{h:02d}:{m:02d}:{sec:02d},{ms:03d}"
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
        _console_err.print(f"[red]error:[/red] {escape(error)}\nhint: {escape(hint)}")

def check_output_path(path: str, as_json: bool) -> None:
    """Fail early (before a billed API call) when the output path is unusable."""
    p = Path(path)
    try:
        if p.exists() and p.is_dir():
            raise IsADirectoryError(f"is a directory: {path}")
        parent = p.parent
        if not parent.exists():
            raise FileNotFoundError(f"parent directory does not exist: {parent}")
        if not parent.is_dir():
            raise NotADirectoryError(f"not a directory: {parent}")
    except OSError as e:
        print_err(f"cannot write {path}: {e}", "check the path and permissions", as_json)
        raise typer.Exit(1)

def _write(path: str, data: str | bytes, as_json: bool) -> None:
    check_output_path(path, as_json)
    try:
        p = Path(path)
        if isinstance(data, bytes):
            p.write_bytes(data)
        else:
            p.write_text(data, encoding="utf-8")
    except OSError as e:
        print_err(f"cannot write {path}: {e}", "check the path and permissions", as_json)
        raise typer.Exit(1)

def save_bytes(path: str, data: bytes, as_json: bool) -> None:
    """Write a binary payload (e.g. TTS wav) with a clean CLI error on failure."""
    _write(path, data, as_json)

def present(text: str, summary: dict[str, str], as_json: bool, o: str | None) -> None:
    """One payload outlet: -o writes the raw file; stdout is a single JSON
    object under --json, else raw text plus the human ok-line."""
    if o:
        _write(o, text, as_json)
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
