import argparse
import asyncio
import json
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path

from .client import list_voices, synthesize_to_files
from .playback import play

DEFAULT_VOICE = "en-US-EmmaMultilingualNeural"


def default_output_path() -> str:
    return f"tts_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp3"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="tts",
        description="Synthesize speech using Microsoft Edge's online TTS service.",
    )
    parser.add_argument("text", nargs="?", help="Text to speak")
    parser.add_argument(
        "--voice", default=DEFAULT_VOICE, help=f"Voice name (default: {DEFAULT_VOICE})"
    )
    parser.add_argument("--output", help="Output mp3 path (default: tts_<timestamp>.mp3 in cwd)")
    parser.add_argument(
        "--play",
        action="store_true",
        help="Play the synthesized audio instead of saving it to a file",
    )
    parser.add_argument(
        "--rate", default="+0%",
        help="Speech rate adjustment (default: +0%%). For negative values use --rate=-10%%",
    )
    parser.add_argument(
        "--volume", default="+0%",
        help="Speech volume adjustment (default: +0%%). For negative values use --volume=-10%%",
    )
    parser.add_argument(
        "--pitch", default="+0Hz",
        help="Speech pitch adjustment (default: +0Hz). For negative values use --pitch=-5Hz",
    )
    parser.add_argument(
        "--boundary",
        choices=["SentenceBoundary", "WordBoundary"],
        default="SentenceBoundary",
        help="Metadata boundary granularity (default: SentenceBoundary)",
    )
    parser.add_argument("--metadata", help="Write boundary metadata as JSONL to this path")
    parser.add_argument("--proxy", help="Proxy URL to use for requests")
    parser.add_argument(
        "--list-voices",
        action="store_true",
        help="Print all available voices as JSON and exit",
    )
    return parser


async def run(args: argparse.Namespace) -> None:
    if args.list_voices:
        voices = await list_voices(proxy=args.proxy)
        print(json.dumps(voices, indent=2, ensure_ascii=False))
        return

    if args.play:
        with tempfile.TemporaryDirectory() as tmpdir:
            output = str(Path(tmpdir) / "tts_playback.mp3")
            synth_start = time.perf_counter()
            await synthesize_to_files(
                text=args.text,
                voice=args.voice,
                output=output,
                metadata_output=args.metadata,
                rate=args.rate,
                volume=args.volume,
                pitch=args.pitch,
                boundary=args.boundary,
                proxy=args.proxy,
            )
            synth_elapsed = time.perf_counter() - synth_start
            print(f"synthesized in {synth_elapsed:.2f}s", file=sys.stderr)

            playback_start = time.perf_counter()
            play(output)
            playback_elapsed = time.perf_counter() - playback_start
            print(f"played in {playback_elapsed:.2f}s", file=sys.stderr)
        return

    output = args.output or default_output_path()
    synth_start = time.perf_counter()
    await synthesize_to_files(
        text=args.text,
        voice=args.voice,
        output=output,
        metadata_output=args.metadata,
        rate=args.rate,
        volume=args.volume,
        pitch=args.pitch,
        boundary=args.boundary,
        proxy=args.proxy,
    )
    synth_elapsed = time.perf_counter() - synth_start
    print(f"synthesized in {synth_elapsed:.2f}s", file=sys.stderr)
    print(output)


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.list_voices and not args.text:
        parser.error("the following arguments are required: text (unless --list-voices is given)")
    if args.play and args.output:
        parser.error("--play and --output cannot be used together")

    try:
        asyncio.run(run(args))
    except Exception as e:  # noqa: BLE001 - surface a clean CLI error instead of a traceback
        print(f"error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
