from datetime import datetime

from edgetts_cli import cli


def test_default_output_path_is_timestamped(monkeypatch):
    class FixedDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(2026, 7, 24, 15, 30, 0)

    monkeypatch.setattr(cli, "datetime", FixedDatetime)
    assert cli.default_output_path() == "tts_20260724_153000.mp3"


def test_parser_accepts_text_positional():
    parser = cli.build_parser()
    args = parser.parse_args(["hello world"])
    assert args.text == "hello world"
    assert args.voice == cli.DEFAULT_VOICE
    assert args.rate == "+0%"
    assert args.volume == "+0%"
    assert args.pitch == "+0Hz"
    assert args.boundary == "SentenceBoundary"
    assert args.list_voices is False


def test_parser_allows_omitted_text_for_list_voices():
    parser = cli.build_parser()
    args = parser.parse_args(["--list-voices"])
    assert args.text is None
    assert args.list_voices is True


def test_parser_accepts_all_flags():
    parser = cli.build_parser()
    args = parser.parse_args(
        [
            "hi",
            "--voice", "en-US-GuyNeural",
            "--output", "out.mp3",
            "--rate", "+20%",
            "--volume=-10%",
            "--pitch", "+5Hz",
            "--boundary", "WordBoundary",
            "--metadata", "meta.jsonl",
            "--proxy", "http://localhost:8080",
        ]
    )
    assert args.voice == "en-US-GuyNeural"
    assert args.output == "out.mp3"
    assert args.rate == "+20%"
    assert args.volume == "-10%"
    assert args.pitch == "+5Hz"
    assert args.boundary == "WordBoundary"
    assert args.metadata == "meta.jsonl"
    assert args.proxy == "http://localhost:8080"


def test_main_errors_when_text_missing_and_not_listing_voices(capsys):
    try:
        cli.main([])
        assert False, "expected SystemExit"
    except SystemExit as e:
        assert e.code == 2
    captured = capsys.readouterr()
    assert "text" in captured.err
