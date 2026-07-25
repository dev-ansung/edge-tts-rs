# edge-tts-rs

A from-scratch reimplementation of Microsoft Edge's online text-to-speech
service. It has no dependency on the `edge-tts` package; `aiohttp` and
`certifi` communicate directly with the same WebSocket endpoint used by the
Edge browser.

```bash
uvx --from git+https://github.com/dev-ansung/edge-tts-rs tts "Hello, world!"
```

No installation step or virtual environment setup is required. The command
writes a timestamped file (e.g. `tts_20260724_153000.mp3`) to the current
directory.

For users who prefer not to memorize flag names or voice identifiers, the
[interactive command builder](https://dev-ansung.github.io/edge-tts-rs/)
provides a UI for selecting a voice and tuning delivery parameters, then
generates the corresponding command.

## Usage

```bash
tts "Hello, world!"                                   # timestamped mp3 in cwd
tts "Hello" --voice en-US-GuyNeural                   # pick a voice
tts "Hello" --rate +20% --pitch +10Hz --volume=-10%   # tune delivery
tts "Hello" --output greeting.mp3                     # explicit output path
tts "Hello" --metadata boundaries.jsonl --boundary WordBoundary
tts --list-voices                                     # print all voices as JSON
tts --play "Hello, world!"                            # synthesize and play, no file saved
echo "Hello, world!" | tts                            # read text from piped stdin
```

Run `tts --help` for the full flag list.

## Why this exists

`edge-tts` (the popular PyPI package) already solves this problem well. This
project reimplements the same undocumented protocol from scratch as an
engineering exercise, covering derivation of the `Sec-MS-GEC` security token,
clock skew handling, SSML payload construction, and framing over the raw
WebSocket protocol used by Edge. See [ARCHITECTURE.md](ARCHITECTURE.md) for
the full writeup.

## Development

```bash
uv sync
uv run pytest
uv run ruff check .
uv run mypy src/
```

## Disclaimer

This is an unofficial client for an undocumented Microsoft endpoint. It is
not affiliated with, endorsed by, or supported by Microsoft, and may cease
to function if that endpoint changes without notice. Use at your own risk.

## License

MIT - see [LICENSE](LICENSE).
