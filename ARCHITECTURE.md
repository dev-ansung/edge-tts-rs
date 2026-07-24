# Architecture

This is a clean-room client for the WebSocket protocol that powers Microsoft
Edge's "Read Aloud" feature. There's no public API for this - the browser
opens a WebSocket to `speech.platform.bing.com` and speaks a small
line-oriented protocol over it. This document describes what that protocol
looks like and why the client is built the way it is.

## Authentication: `Sec-MS-GEC`

Every request (both the voice list and the synthesis WebSocket) needs a
`Sec-MS-GEC` query parameter. It's derived, not issued: a SHA-256 hash of a
timestamp (rounded down to a 5-minute window, converted to Windows'
100-nanosecond-tick epoch) concatenated with a fixed trusted-client token
that ships in the Edge binary. See [`protocol.generate_sec_ms_gec`](src/edgetts_cli/protocol.py).

Because the token is derived from *your local clock* rounded to a 5-minute
window, if your clock is skewed from the server's by enough to land in a
different window, the request gets rejected with a 403. The client handles
this by reading the `Date` response header off the failed request,
computing the skew, and retrying once with a corrected clock
([`adjust_clock_skew_from_headers`](src/edgetts_cli/protocol.py)).

## Synthesis: WebSocket framing

The synthesis endpoint is a WebSocket, not a request/response HTTP call.
After connecting, the client sends two text frames:

1. A `speech.config` frame (JSON) declaring the desired output codec and
   whether word/sentence boundary metadata should be included.
2. An `ssml` frame containing the actual SSML payload, wrapped in a small
   header block (`X-RequestId`, `Content-Type`, `X-Timestamp`, `Path`)
   before the XML body.

The server then streams back a mix of:
- **Text frames** for metadata (`audio.metadata` - word/sentence boundary
  events; `turn.end` - marks the end of this synthesis turn).
- **Binary frames** for audio (`Path: audio`, with a small length-prefixed
  header before the raw MP3 bytes).

Both frame types share the same header-then-body shape, just over different
WebSocket message types (text vs. binary) with slightly different framing:
text frames use a `\r\n\r\n` separator; binary frames prefix a 2-byte
big-endian header length. See
[`protocol.get_headers_and_data`](src/edgetts_cli/protocol.py).

One framing subtlety: `get_headers_and_data` skips `header_length + 2` bytes
to reach the body, i.e. one `\r\n` past the header block. For binary frames,
the 2-byte prefix already accounts for this, so the body starts cleanly. For
text frames, `header_length` comes from `data.find(b"\r\n\r\n")` - the index
of the *first* `\r\n` of that separator - so the body ends up with one
leftover `\r\n` at the front. That's harmless in practice: text-frame bodies
are JSON, and `json.loads` ignores leading whitespace.

## Chunking long text

The service caps how much SSML you can send in one WebSocket turn (a
practical ~4096-byte UTF-8 budget observed empirically). Longer input gets
split into multiple turns over the same WebSocket session.

Splitting isn't just "cut at N bytes" - naive byte-boundary cuts can:
- **Split a UTF-8 multi-byte character** — the splitter walks backward from
  the target boundary until it lands on a valid UTF-8 decode point.
- **Split an HTML entity** (`&amp;` -> `&am` + `p;`) - since the text gets
  XML-escaped before chunking, the splitter also walks back past any
  incomplete `&...;` entity at the boundary.

See [`chunking.split_text_by_byte_length`](src/edgetts_cli/chunking.py).

## Offset compensation across chunks

Word/sentence boundary metadata comes back with offsets relative to *that
chunk's* audio stream, starting at zero each time. But callers want offsets
relative to the *whole* synthesized output. The client tracks cumulative
audio bytes emitted by prior chunks and converts that into an equivalent
time offset (given the fixed 24kHz/48kbit/mono output format), adding it to
each subsequent chunk's reported offsets. See the `offset_compensation`
bookkeeping in [`client.tts_stream`](src/edgetts_cli/client.py).

## What's tested vs. not

Everything above the network boundary - SSML construction, header
parsing, GEC token derivation, chunking/splitting - is deterministic and
covered by unit tests (`tests/`). The WebSocket/HTTP calls themselves
(`list_voices`, `tts_stream`) are not exercised in CI: they depend on an
undocumented third-party endpoint, and testing against it in CI would make
the build flaky against factors outside this repo's control. That's a
deliberate scope boundary, not an oversight.
