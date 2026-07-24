# edge-tts-rs

A from-scratch reimplementation of Microsoft Edge's online text-to-speech
service. No dependency on the `edge-tts` package — just `aiohttp` and
`certifi` talking directly to the same WebSocket endpoint the Edge browser
uses.

```bash
uvx --from git+https://github.com/dev-ansung/edge-tts-rs tts "Hello, world!"
```

That's it. No install step, no virtualenv to manage. It drops
`tts_20260724_153000.mp3` (a timestamped filename) in your current directory.

Don't want to remember flag names or the exact voice identifiers? Use the
[interactive command builder](https://dev-ansung.github.io/edge-tts-rs/) to
pick a voice and tune the delivery, then copy the generated command.

## Usage

```bash
tts "Hello, world!"                                   # timestamped mp3 in cwd
tts "Hello" --voice en-US-GuyNeural                   # pick a voice
tts "Hello" --rate +20% --pitch +10Hz --volume=-10%   # tune delivery
tts "Hello" --output greeting.mp3                     # explicit output path
tts "Hello" --metadata boundaries.jsonl --boundary WordBoundary
tts --list-voices                                     # print all voices as JSON
```

Run `tts --help` for the full flag list.

## Why this exists

`edge-tts` (the popular PyPI package) already does this well. This project
reimplements the same undocumented protocol from scratch as an engineering
exercise: deriving the `Sec-MS-GEC` security token, handling clock skew,
building the SSML payload, and framing everything over the raw WebSocket
protocol Edge itself uses. See [ARCHITECTURE.md](ARCHITECTURE.md) for the
full writeup.

## Development

```bash
uv sync
uv run pytest
uv run ruff check .
uv run mypy src/
```

## Disclaimer

This is an unofficial client for an undocumented Microsoft endpoint. It is
not affiliated with, endorsed by, or supported by Microsoft, and it may stop
working at any time if that endpoint changes. Use at your own risk.

## License

MIT - see [LICENSE](LICENSE).
