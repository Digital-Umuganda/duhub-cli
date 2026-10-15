# duhub-cli

Command-line client for [DUhub](https://beta.duhub.ai):
transcribe audio, synthesize speech, translate text, and diarize meetings —
all billed to your API key.

```bash
du stt rec.wav -o transcript.json
du tts "Muraho neza nshuti yanjye." -o out.wav
du mt "Muraho" --src rw --tgt en
du diarize meeting.wav --format srt -o speakers.srt
```

## Installation

Requires Python 3.11+.

```bash
pipx install duhub-cli
du --version
```

Alternatives:

```bash
pipx install git+https://github.com/Digital-Umuganda/duhub-cli.git
pip install git+https://github.com/Digital-Umuganda/duhub-cli.git   # plain pip
python -m du_cli.main --help                                     # without installing
```

> Note: `du` shadows the Unix `du` (disk usage) on your `PATH`. If that
> bothers you, invoke it as `python -m du_cli.main` instead.

## Quickstart

1. Create an account on the
   [Dashboard](https://beta.duhub.ai) and copy an
   API key from **API Keys** (shown once — treat it like a password).
2. Save it:
   ```bash
   du configure --api-key du_live_xxxxxxxxxxxxxxxx
   ```
3. Check connectivity:
   ```bash
   du health
   du health --detailed
   ```
4. Transcribe something:
   ```bash
   du stt rec.wav
   ```

## Configuration

`du configure` stores settings in `~/.config/du/config.toml`:

| Source | Priority | Example |
|--------|----------|---------|
| Environment | Highest (always wins) | `DU_API_KEY`, `DU_BASE_URL` |
| Config file | Middle | `du configure --api-key … --base-url …` |
| Built-in default | Lowest | base `https://du-api.dev.umuganda.digital` |

```bash
du configure                                # show current state
du configure --api-key du_live_xxx          # set key
du configure --base-url http://localhost:8080  # point at local gateway
du configure --reset                        # delete the file
export DU_API_KEY=du_live_xxx DU_BASE_URL=https://du-api.dev.umuganda.digital
```

> Prefer `DU_API_KEY` env var over `--api-key` — flags land in shell history.

## Commands

Every command exits `0` on success, `1` on failure (`2` on CLI usage
errors), prints a summary line (`units`, `cache`, `request-id`), and
accepts `--json` for a single machine-readable object on stdout
(`{"data", "units", "cache", "request_id"}`). `-o` writes the raw
payload to a file instead of stdout.

### `du health`

Liveness (`/health`) or full readiness (`--detailed`, checks STT/TTS/MT
backends — the one to try first when calls fail).

### `du stt` — speech to text

Upload audio (WAV/FLAC/OGG, ≤ 30 MB), get `{"text": "…"}`.
**Billed per audio second.**

```bash
du stt rec.wav -o transcript.json
du stt rec.wav --idempotency-key run-42 -o transcript.json
```

### `du tts` — text to speech

Synthesize Kinyarwanda speech to a 24 kHz mono WAV (`-o` is required —
audio never goes to stdout). **Billed per word.** `--text-file`
overrides `TEXT` when both are given.

```bash
du tts "Muraho neza nshuti yanjye." -o out.wav
```

### `du mt` — translation

Translate between Kinyarwanda (`rw`) and English (`en`).
**Billed per input word.**

```bash
du mt "Muraho" --src rw --tgt en
```

### `du diarize` — who spoke when

Upload audio, get speaker-labelled segments. `--format` renders the same
result as `json` (default), `txt`, or `srt`. **Billed per audio second.**

```bash
du diarize meeting.wav --format srt -o speakers.srt
```

> The gateway `/diarize` route rolls out separately from the CLI. If it is
> not deployed yet, the CLI says so plainly instead of dumping a 404.

## Scripting

`--json` prints exactly one JSON object — pipe-safe:

```bash
TEXT=$(du stt rec.wav --json | jq -r .data.text)

for f in clips/*.wav; do
  du stt "$f" -o "${f%.wav}.json" || echo "FAILED: $f" >&2
done
```

## Errors

The CLI never dumps tracebacks — every failure is `error` + `hint`:

| You see | Cause | Fix |
|---------|-------|-----|
| `invalid key` (401) | Missing/unknown/revoked key | Copy a fresh key from dashboard API Keys |
| `insufficient balance` (402) | Wallet empty | Top-up via dashboard Wallet |
| `organization pending review` (403) | Org not approved yet | Contact your org admin |
| `file exceeds 30 MB` | Upload guard | Compress or split the audio |
| `server busy (saturated)` (503) | GPU at concurrency cap | Wait `Retry-After` seconds, retry |
| `backend unreachable` (502) | Model container down | `du health --detailed` to see which |
| `cannot reach server` | Wrong `--base-url`, offline, timeout | Check URL and connectivity |

## Development

```bash
uv sync        # or: python -m venv .venv && .venv/bin/pip install -e .
uv run pytest
uv run du --help
```
