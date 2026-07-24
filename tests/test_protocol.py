from edgetts_cli import protocol


def test_mkssml_wraps_text_in_expected_tags():
    ssml = protocol.mkssml("Hello", "en-US-AriaNeural", "+0%", "+0%", "+0Hz")
    assert "<voice name='en-US-AriaNeural'>" in ssml
    assert "<prosody pitch='+0Hz' rate='+0%' volume='+0%'>" in ssml
    assert "Hello" in ssml
    assert ssml.startswith("<speak")
    assert ssml.endswith("</speak>")


def test_mkssml_escapes_special_characters():
    ssml = protocol.mkssml("Tom & Jerry <3", "en-US-AriaNeural", "+0%", "+0%", "+0Hz")
    assert "Tom &amp; Jerry &lt;3" in ssml


def test_get_headers_and_data_parses_header_block():
    # header_length is the byte offset of the "\r\n\r\n" separator, matching
    # both call sites in client.py (data.find(b"\\r\\n\\r\\n") for text frames,
    # and the binary frame's declared header length).
    data = b"Path:audio\r\nContent-Type:audio/mpeg\r\n\r\nBINARYDATA"
    header_len = data.find(b"\r\n\r\n")
    headers, body = protocol.get_headers_and_data(data, header_len)
    assert headers[b"Path"] == b"audio"
    assert headers[b"Content-Type"] == b"audio/mpeg"
    # text-frame callers pass header_length from data.find(b"\r\n\r\n"), which
    # leaves a leading b"\r\n" on the body - see ARCHITECTURE.md for why.
    assert body == b"\r\nBINARYDATA"


def test_ssml_headers_plus_data_includes_request_id_and_ssml():
    result = protocol.ssml_headers_plus_data("req-123", "2026-07-24T00:00:00", "<speak/>")
    assert "X-RequestId:req-123" in result
    assert "Path:ssml" in result
    assert result.endswith("<speak/>")


def test_generate_sec_ms_gec_is_deterministic_within_five_minute_window(monkeypatch):
    fixed_time = 1_800_000_000.0
    monkeypatch.setattr(protocol.time, "time", lambda: fixed_time)
    protocol.CLOCK_SKEW_SECONDS = 0.0
    token_a = protocol.generate_sec_ms_gec()
    token_b = protocol.generate_sec_ms_gec()
    assert token_a == token_b
    assert len(token_a) == 64  # sha256 hex digest, uppercased
    assert token_a == token_a.upper()


def test_generate_sec_ms_gec_changes_across_five_minute_window(monkeypatch):
    protocol.CLOCK_SKEW_SECONDS = 0.0
    monkeypatch.setattr(protocol.time, "time", lambda: 1_800_000_000.0)
    token_a = protocol.generate_sec_ms_gec()
    monkeypatch.setattr(protocol.time, "time", lambda: 1_800_000_000.0 + 400)
    token_b = protocol.generate_sec_ms_gec()
    assert token_a != token_b


def test_parse_rfc2616_date_valid():
    ts = protocol.parse_rfc2616_date("Fri, 24 Jul 2026 12:00:00 GMT")
    assert ts is not None


def test_parse_rfc2616_date_invalid_returns_none():
    assert protocol.parse_rfc2616_date("not a date") is None


def test_generate_muid_is_32_hex_chars():
    muid = protocol.generate_muid()
    assert len(muid) == 32
    int(muid, 16)  # raises if not valid hex


def test_headers_with_muid_adds_cookie_without_mutating_input():
    base = {"User-Agent": "test"}
    result = protocol.headers_with_muid(base)
    assert "Cookie" in result
    assert "Cookie" not in base
    assert result["User-Agent"] == "test"
