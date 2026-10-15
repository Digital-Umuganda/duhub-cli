"""du CLI entrypoint: configure, health, stt, tts, mt, diarize."""
from __future__ import annotations
from pathlib import Path as _Path
import typer
from du_cli import config, output
from du_cli.client import auth_headers, api_client, raise_for_api, CliError, MAX_UPLOAD_BYTES
from du_cli.output import render_segments as _render_segments

__version__ = "0.1.0"

def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"du {__version__}")
        raise typer.Exit()

app = typer.Typer(
    no_args_is_help=True,
    add_completion=False,
    help="DUhub CLI — STT, TTS, MT and diarization over your API key.",
    epilog="Keys live on the dashboard under API Keys; billing per second (audio) or word (text).",
)

@app.callback()
def _root(
    version: bool = typer.Option(
        False, "--version", callback=_version_callback, is_eager=True,
        help="Show version and exit.",
    ),
) -> None:
    pass

def _cfg(base_url: str | None, api_key: str | None) -> dict[str, str]:
    return config.load_config(base_url, api_key)

@app.command()
def configure(
    base_url: str | None = typer.Option(None, "--base-url"),
    api_key: str | None = typer.Option(None, "--api-key"),
    reset: bool = typer.Option(False, "--reset"),
) -> None:
    if reset:
        config.clear_config()
        typer.echo("cleared")
        return
    if not base_url and not api_key:
        cur = config.load_config()
        typer.echo(f"base_url={cur['base_url']}")
        typer.echo("api_key=" + ("set" if cur["api_key"] else "missing"))
        return
    p = config.save_config(base_url, api_key)
    typer.echo(f"saved {p}")

@app.command()
def health(
    detailed: bool = typer.Option(False, "--detailed"),
    json_out: bool = typer.Option(False, "--json", help="Machine-readable single-JSON output."),
    base_url: str | None = typer.Option(None, "--base-url"),
    api_key: str | None = typer.Option(None, "--api-key"),
) -> None:
    cfg = _cfg(base_url, api_key)
    path = "/health/detailed" if detailed else "/health"
    try:
        headers = auth_headers(cfg["api_key"]) if cfg["api_key"] else {}
        with api_client() as c:
            r = c.get(cfg["base_url"] + path, headers=headers)
        raise_for_api(r.status_code, r.text, path)
        output.present(
            r.text,
            {"units": "", "cache": "", "request_id": r.headers.get("x-request-id", "")},
            json_out, None,
        )
    except CliError as e:
        output.print_err(e.detail, e.hint, json_out)
        raise typer.Exit(1)

@app.command()
def stt(
    file: str = typer.Argument(..., help="Audio file (wav/flac/ogg, ≤30MB)"),
    o: str | None = typer.Option(None, "-o", "--output"),
    idempotency_key: str | None = typer.Option(None, "--idempotency-key"),
    json_out: bool = typer.Option(False, "--json", help="Machine-readable single-JSON output."),
) -> None:
    cfg = _cfg(None, None)
    p = _Path(file)
    if not p.exists():
        output.print_err(f"file not found: {file}", "check the path", json_out)
        raise typer.Exit(1)
    if p.stat().st_size > MAX_UPLOAD_BYTES:
        output.print_err("file exceeds 30 MB", "compress or split audio", json_out)
        raise typer.Exit(1)
    try:
        if not cfg["api_key"]:
            raise CliError(401, "missing API key", "run `du configure --api-key KEY`")
        with api_client() as c, p.open("rb") as fh:
            r = c.post(
                cfg["base_url"] + "/stt",
                headers=auth_headers(cfg["api_key"], idempotency_key),
                files={"file": (p.name, fh)},
            )
        raise_for_api(r.status_code, r.text, "/stt")
        output.present(
            r.text,
            {
                "units": r.headers.get("x-units", ""),
                "cache": r.headers.get("x-cache-status", ""),
                "request_id": r.headers.get("x-request-id", ""),
            },
            json_out, o,
        )
    except CliError as e:
        output.print_err(e.detail, e.hint, json_out)
        raise typer.Exit(1)

@app.command()
def tts(
    text: str = typer.Argument("", help="Text to synthesize"),
    o: str = typer.Option(..., "-o", "--output", help="Output wav path (required)"),
    text_file: str | None = typer.Option(None, "--text-file"),
    json_out: bool = typer.Option(False, "--json", help="Machine-readable single-JSON output."),
) -> None:
    cfg = _cfg(None, None)
    if text_file:
        try:
            text = _Path(text_file).read_text().strip()
        except (FileNotFoundError, IsADirectoryError, OSError, ValueError) as e:
            output.print_err(f"cannot read --text-file: {e}", "check the path", json_out)
            raise typer.Exit(1)
    if not text.strip():
        output.print_err("empty text", "provide TEXT or --text-file", json_out)
        raise typer.Exit(1)
    if not json_out:
        typer.echo(f"words={len(text.split())}")
    try:
        if not cfg["api_key"]:
            raise CliError(401, "missing API key", "run `du configure --api-key KEY`")
        with api_client() as c:
            r = c.post(
                cfg["base_url"] + "/tts",
                headers={**auth_headers(cfg["api_key"]), "Content-Type": "application/json"},
                json={"text": text},
            )
        raise_for_api(r.status_code, r.text, "/tts")
        _Path(o).write_bytes(r.content)
        output.print_ok({"units": r.headers.get("x-units", ""), "cache": r.headers.get("x-cache-status", ""), "request_id": r.headers.get("x-request-id", "")}, json_out)
    except CliError as e:
        output.print_err(e.detail, e.hint, json_out)
        raise typer.Exit(1)

@app.command()
def mt(
    text: str = typer.Argument(..., help="Text to translate"),
    src: str = typer.Option("rw", "--src"),
    tgt: str = typer.Option("en", "--tgt"),
    o: str | None = typer.Option(None, "-o", "--output"),
    json_out: bool = typer.Option(False, "--json", help="Machine-readable single-JSON output."),
) -> None:
    cfg = _cfg(None, None)
    if src not in ("rw", "en") or tgt not in ("rw", "en"):
        output.print_err(f"unsupported lang src={src} tgt={tgt}", "use --src rw|en --tgt rw|en", json_out)
        raise typer.Exit(1)
    if src == tgt:
        output.print_err("src==tgt", "source and target must differ", json_out)
        raise typer.Exit(1)
    if not text.strip():
        output.print_err("empty text", "provide TEXT", json_out)
        raise typer.Exit(1)
    try:
        if not cfg["api_key"]:
            raise CliError(401, "missing API key", "run `du configure --api-key KEY`")
        with api_client() as c:
            r = c.post(
                cfg["base_url"] + "/mt",
                headers={**auth_headers(cfg["api_key"]), "Content-Type": "application/json"},
                json={"text": text, "source_lang": src, "target_lang": tgt},
            )
        raise_for_api(r.status_code, r.text, "/mt")
        output.present(
            r.text,
            {
                "units": r.headers.get("x-units", ""),
                "cache": r.headers.get("x-cache-status", ""),
                "request_id": r.headers.get("x-request-id", ""),
            },
            json_out, o,
        )
    except CliError as e:
        output.print_err(e.detail, e.hint, json_out)
        raise typer.Exit(1)

@app.command()
def diarize(
    file: str = typer.Argument(..., help="Audio file (≤30MB)"),
    o: str | None = typer.Option(None, "-o", "--output"),
    fmt: str = typer.Option("json", "--format", help="json|txt|srt"),
    json_out: bool = typer.Option(False, "--json", help="Machine-readable single-JSON output."),
) -> None:
    cfg = _cfg(None, None)
    if fmt not in ("json", "txt", "srt"):
        output.print_err(f"bad format {fmt}", "use --format json|txt|srt", json_out)
        raise typer.Exit(1)
    p = _Path(file)
    if not p.exists():
        output.print_err(f"file not found: {file}", "check the path", json_out)
        raise typer.Exit(1)
    if p.stat().st_size > MAX_UPLOAD_BYTES:
        output.print_err("file exceeds 30 MB", "compress or split audio", json_out)
        raise typer.Exit(1)
    try:
        if not cfg["api_key"]:
            raise CliError(401, "missing API key", "run `du configure --api-key KEY`")
        with api_client() as c, p.open("rb") as fh:
            r = c.post(
                cfg["base_url"] + "/diarize",
                headers=auth_headers(cfg["api_key"]),
                files={"file": (p.name, fh)},
            )
        raise_for_api(r.status_code, r.text, "/diarize")
        try:
            segs = r.json().get("segments", [])
        except Exception:
            output.print_err("invalid diarize response", "try `du health --detailed`", json_out)
            raise typer.Exit(1)
        rendered = _render_segments(segs, fmt)
        output.present(
            rendered,
            {"units": r.headers.get("x-units", ""), "cache": "", "request_id": r.headers.get("x-request-id", "")},
            json_out, o,
        )
    except CliError as e:
        output.print_err(e.detail, e.hint, json_out)
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
