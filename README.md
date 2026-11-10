# duhub-cli

Command-line client for [DUhub](https://beta.duhub.ai):
transcribe audio, synthesize speech, translate text, and diarize meetings —
all billed to your API key.

```bash
duhub stt rec.wav -o transcript.json
duhub tts "Muraho neza nshuti yanjye." -o out.wav
duhub mt "Muraho" --src rw --tgt en
duhub diarize meeting.wav --format srt -o speakers.srt
```

## Installation

Requires Python 3.11+.

Recommended (isolated CLI install):

```bash
pipx install duhub-cli
duhub --version
```

Plain pip, inside a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
pip install duhub-cli
duhub --version
```

Or install for your user only:

```bash
pip install --user duhub-cli
```

> On PEP 668 systems (Arch, recent Debian/Ubuntu), system-wide `pip`
> may refuse with `externally-managed-environment`. Use `pipx` or a
> virtual environment instead of forcing it.

From a git checkout:

```bash
pipx install git+https://github.com/Digital-Umuganda/duhub-cli.git
pip install git+https://github.com/Digital-Umuganda/duhub-cli.git   # plain pip
python -m du_cli.main --help                                       # without installing
```

> The installed command is `duhub` only, so it does not shadow the Unix
> `du` (disk usage). You can also invoke `python -m du_cli.main` without
> installing.

## Quickstart

1. Create an account on the
   [Dashboard](https://beta.duhub.ai) and copy an
   API key from **API Keys** (shown once — treat it like a password).
2. Save it:
   ```bash
   duhub configure --api-key du_live_xxxxxxxxxxxxxxxx
   ```
3. Check connectivity:
   ```bash
   duhub health
   duhub health --detailed
   ```
4. Transcribe something:
   ```bash
   duhub stt rec.wav
   ```

## Configuration

`duhub configure` stores settings in `~/.config/du/config.toml` (the
short directory name is kept for compatibility):

| Source | Priority | Example |
|--------|----------|---------|
| Environment | Highest (always wins) | `DU_API_KEY`, `DU_BASE_URL` |
| Config file | Middle | `duhub configure --api-key … --base-url …` |
| Built-in default | Lowest | base `https://du-api.dev.umuganda.digital` |

```bash
duhub configure                                   # show current state
duhub configure --api-key du_live_xxx             # set key
duhub configure --base-url http://localhost:8080  # point at local gateway
duhub configure --reset                           # delete the file
export DU_API_KEY=du_live_xxx DU_BASE_URL=https://du-api.dev.umuganda.digital
```

> Prefer `DU_API_KEY` env var over `--api-key` — flags land in shell history.

## Commands

Every command exits `0` on success, `1` on failure (`2` on CLI usage
errors) and prints a summary line (`units`, `cache`, `request-id`). The
API commands (`health`, `stt`, `tts`, `mt`, `diarize`) accept `--json`
for a single machine-readable object on stdout
(`{"data", "units", "cache", "request_id"}`). `-o` writes the raw
payload to a file instead of stdout.

Every billed command (`stt`, `tts`, `mt`, `diarize`) accepts
`--idempotency-key`, so a retry after a timeout or connection drop is
deduplicated by the gateway instead of being billed twice.

### `duhub health`

Liveness (`/health`) or full readiness (`--detailed`, checks STT/TTS/MT
backends — the one to try first when calls fail).

### `duhub stt` — speech to text

Upload audio (WAV/FLAC/OGG, ≤ 30 MB), get `{"text": "…"}`.
**Billed per audio second.**

```bash
duhub stt rec.wav -o transcript.json
duhub stt rec.wav --idempotency-key run-42 -o transcript.json
```

### `duhub tts` — text to speech

Synthesize Kinyarwanda speech to a 24 kHz mono WAV (`-o` is required —
audio never goes to stdout). **Billed per word.** `--text-file`
overrides `TEXT` when both are given.

```bash
duhub tts "Muraho neza nshuti yanjye." -o out.wav
duhub tts "Muraho neza nshuti yanjye." -o out.wav --idempotency-key run-42
```

### `duhub mt` — translation

Translate between Kinyarwanda (`rw`) and English (`en`).
**Billed per input word.**

```bash
duhub mt "Muraho" --src rw --tgt en
```

### `duhub diarize` — who spoke when

Upload audio, get speaker-labelled segments. `--format` renders the same
result as `json` (default), `txt`, or `srt`. **Billed per audio second.**

```bash
duhub diarize meeting.wav --format srt -o speakers.srt
```

> A `404` here usually means the configured gateway predates the
> `/diarize` route. Check `duhub health --detailed` and your `--base-url`.

## Scripting

`--json` prints exactly one JSON object — pipe-safe:

```bash
TEXT=$(duhub stt rec.wav --json | jq -r .data.text)

for f in clips/*.wav; do
  duhub stt "$f" -o "${f%.wav}.json" || echo "FAILED: $f" >&2
done
```

## Errors

API, input-file, and output-file failures are reported as `error` +
`hint` — no tracebacks:

| You see | Cause | Fix |
|---------|-------|-----|
| `invalid key` (401) | Missing/unknown/revoked key | Copy a fresh key from dashboard API Keys |
| `insufficient balance` (402) | Wallet empty | Top-up via dashboard Wallet |
| `organization pending review` (403) | Org not approved yet | Contact your org admin |
| `file exceeds 30 MB` | Upload guard | Compress or split the audio |
| `server busy (saturated)` (503) | GPU at concurrency cap | Wait `Retry-After` seconds, retry |
| `backend unreachable` (502) | Model container down | `duhub health --detailed` to see which |
| `cannot reach server` | Wrong `--base-url`, offline, timeout | Check URL and connectivity |

## Development

```bash
uv sync        # or: python -m venv .venv && .venv/bin/pip install -e .
uv run pytest
uv run duhub --help
```
