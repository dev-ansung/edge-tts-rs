import json
from collections.abc import AsyncGenerator
from html import unescape

import aiohttp

from .chunking import split_text_by_byte_length
from .protocol import (
    SEC_MS_GEC_VERSION,
    SSL_CTX,
    VOICE_HEADERS,
    VOICE_LIST_URL,
    WSS_HEADERS,
    WSS_URL,
    adjust_clock_skew_from_headers,
    connect_id,
    date_to_string,
    generate_sec_ms_gec,
    get_headers_and_data,
    headers_with_muid,
    mkssml,
    ssml_headers_plus_data,
)


async def list_voices(proxy: str | None = None) -> list[dict]:
    async with aiohttp.ClientSession(trust_env=True) as session:
        url = (
            f"{VOICE_LIST_URL}"
            f"&Sec-MS-GEC={generate_sec_ms_gec()}"
            f"&Sec-MS-GEC-Version={SEC_MS_GEC_VERSION}"
        )
        try:
            async with session.get(
                url,
                headers=headers_with_muid(VOICE_HEADERS),
                proxy=proxy,
                ssl=SSL_CTX,
                raise_for_status=True,
            ) as resp:
                return json.loads(await resp.text())
        except aiohttp.ClientResponseError as e:
            if e.status != 403:
                raise
            adjust_clock_skew_from_headers(e.headers or {})
            async with session.get(
                url,
                headers=headers_with_muid(VOICE_HEADERS),
                proxy=proxy,
                ssl=SSL_CTX,
                raise_for_status=True,
            ) as resp:
                return json.loads(await resp.text())


async def tts_stream(
    text: str,
    voice: str,
    rate: str = "+0%",
    volume: str = "+0%",
    pitch: str = "+0Hz",
    boundary: str = "SentenceBoundary",
    proxy: str | None = None,
) -> AsyncGenerator[dict]:
    parts = split_text_by_byte_length(text, 4096)

    timeout = aiohttp.ClientTimeout(
        total=None,
        connect=None,
        sock_connect=10,
        sock_read=60,
    )

    async with aiohttp.ClientSession(trust_env=True, timeout=timeout) as session:
        offset_compensation = 0
        cumulative_audio_bytes = 0

        for part in parts:
            chunk_audio_bytes = 0
            url = (
                f"{WSS_URL}&ConnectionId={connect_id()}"
                f"&Sec-MS-GEC={generate_sec_ms_gec()}"
                f"&Sec-MS-GEC-Version={SEC_MS_GEC_VERSION}"
            )

            async def run_once():
                nonlocal chunk_audio_bytes, cumulative_audio_bytes, offset_compensation

                async with session.ws_connect(
                    url,
                    compress=15,
                    proxy=proxy,
                    headers=headers_with_muid(WSS_HEADERS),
                    ssl=SSL_CTX,
                ) as ws:
                    wd = "true" if boundary == "WordBoundary" else "false"
                    sq = "true" if boundary != "WordBoundary" else "false"

                    await ws.send_str(
                        f"X-Timestamp:{date_to_string()}\r\n"
                        "Content-Type:application/json; charset=utf-8\r\n"
                        "Path:speech.config\r\n\r\n"
                        '{"context":{"synthesis":{"audio":{"metadataoptions":{'
                        f'"sentenceBoundaryEnabled":"{sq}","wordBoundaryEnabled":"{wd}"'
                        "},"
                        '"outputFormat":"audio-24khz-48kbitrate-mono-mp3"'
                        "}}}}\r\n"
                    )

                    await ws.send_str(
                        ssml_headers_plus_data(
                            connect_id(),
                            date_to_string(),
                            mkssml(unescape(part), voice, rate, volume, pitch),
                        )
                    )

                    audio_received = False

                    async for msg in ws:
                        if msg.type == aiohttp.WSMsgType.TEXT:
                            encoded = msg.data.encode("utf-8")
                            header_end = encoded.find(b"\r\n\r\n")
                            headers, body = get_headers_and_data(encoded, header_end)
                            path = headers.get(b"Path")

                            if path == b"audio.metadata":
                                payload = json.loads(body)
                                for meta in payload["Metadata"]:
                                    meta_type = meta["Type"]
                                    if meta_type in ("WordBoundary", "SentenceBoundary"):
                                        yield {
                                            "type": meta_type,
                                            "offset": meta["Data"]["Offset"] + offset_compensation,
                                            "duration": meta["Data"]["Duration"],
                                            "text": unescape(meta["Data"]["text"]["Text"]),
                                        }
                            elif path == b"turn.end":
                                cumulative_audio_bytes += chunk_audio_bytes
                                offset_compensation = (
                                    cumulative_audio_bytes * 8 * 10_000_000 // 48_000
                                )
                                break

                        elif msg.type == aiohttp.WSMsgType.BINARY:
                            if len(msg.data) < 2:
                                raise RuntimeError("Binary message missing header length")

                            header_length = int.from_bytes(msg.data[:2], "big")
                            headers, body = get_headers_and_data(msg.data, header_length)

                            if headers.get(b"Path") != b"audio":
                                continue

                            content_type = headers.get(b"Content-Type")
                            if content_type is None:
                                if len(body) == 0:
                                    continue
                                raise RuntimeError(
                                    "Binary audio frame has data but no Content-Type"
                                )

                            if content_type != b"audio/mpeg":
                                raise RuntimeError(f"Unexpected content type: {content_type!r}")

                            if not body:
                                raise RuntimeError("Audio frame missing data")

                            audio_received = True
                            chunk_audio_bytes += len(body)
                            yield {"type": "audio", "data": body}

                        elif msg.type == aiohttp.WSMsgType.ERROR:
                            raise RuntimeError(f"WebSocket error: {msg.data}")

                    if not audio_received:
                        raise RuntimeError("No audio received")

            try:
                async for item in run_once():
                    yield item
            except aiohttp.ClientResponseError as e:
                if e.status != 403:
                    raise
                adjust_clock_skew_from_headers(e.headers or {})
                async for item in run_once():
                    yield item


async def synthesize_to_files(
    text: str,
    voice: str,
    output: str,
    metadata_output: str | None = None,
    rate: str = "+0%",
    volume: str = "+0%",
    pitch: str = "+0Hz",
    boundary: str = "SentenceBoundary",
    proxy: str | None = None,
) -> None:
    with open(output, "wb") as audio_fp:
        meta_fp = open(metadata_output, "w", encoding="utf-8") if metadata_output else None
        try:
            async for item in tts_stream(
                text=text,
                voice=voice,
                rate=rate,
                volume=volume,
                pitch=pitch,
                boundary=boundary,
                proxy=proxy,
            ):
                if item["type"] == "audio":
                    audio_fp.write(item["data"])
                else:
                    if meta_fp:
                        meta_fp.write(json.dumps(item, ensure_ascii=False) + "\n")
        finally:
            if meta_fp:
                meta_fp.close()
