import hashlib
import secrets
import ssl
import time
import uuid
from collections.abc import Mapping
from datetime import UTC, datetime
from html import escape

import certifi

BASE_URL = "speech.platform.bing.com/consumer/speech/synthesize/readaloud"
TRUSTED_CLIENT_TOKEN = "6A5AA1D4EAFF4E9FB37E23D68491D6F4"
WSS_URL = f"wss://{BASE_URL}/edge/v1?TrustedClientToken={TRUSTED_CLIENT_TOKEN}"
VOICE_LIST_URL = (
    f"https://{BASE_URL}/voices/list?trustedclienttoken={TRUSTED_CLIENT_TOKEN}"
)

CHROMIUM_FULL_VERSION = "143.0.3650.75"
CHROMIUM_MAJOR_VERSION = CHROMIUM_FULL_VERSION.split(".", 1)[0]
SEC_MS_GEC_VERSION = f"1-{CHROMIUM_FULL_VERSION}"

BASE_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        f"Chrome/{CHROMIUM_MAJOR_VERSION}.0.0.0 Safari/537.36 "
        f"Edg/{CHROMIUM_MAJOR_VERSION}.0.0.0"
    ),
    "Accept-Encoding": "gzip, deflate, br, zstd",
    "Accept-Language": "en-US,en;q=0.9",
}

WSS_HEADERS = {
    "Pragma": "no-cache",
    "Cache-Control": "no-cache",
    "Origin": "chrome-extension://jdiccldimpdaibmpdkjnbmckianbfold",
    "Sec-WebSocket-Version": "13",
    **BASE_HEADERS,
}

VOICE_HEADERS = {
    "Authority": "speech.platform.bing.com",
    "Sec-CH-UA": (
        f'" Not;A Brand";v="99", "Microsoft Edge";v="{CHROMIUM_MAJOR_VERSION}", '
        f'"Chromium";v="{CHROMIUM_MAJOR_VERSION}"'
    ),
    "Sec-CH-UA-Mobile": "?0",
    "Accept": "*/*",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Dest": "empty",
    **BASE_HEADERS,
}

SSL_CTX = ssl.create_default_context(cafile=certifi.where())

WIN_EPOCH = 11644473600
CLOCK_SKEW_SECONDS = 0.0


def get_unix_timestamp() -> float:
    return time.time() + CLOCK_SKEW_SECONDS


def parse_rfc2616_date(date_str: str) -> float | None:
    try:
        return (
            datetime.strptime(date_str, "%a, %d %b %Y %H:%M:%S %Z")
            .replace(tzinfo=UTC)
            .timestamp()
        )
    except ValueError:
        return None


def adjust_clock_skew_from_headers(headers: Mapping[str, str] | None) -> None:
    global CLOCK_SKEW_SECONDS
    if not headers:
        raise RuntimeError("No response headers available for clock skew adjustment.")

    server_date = headers.get("Date")
    if not server_date:
        raise RuntimeError("No Date header available for clock skew adjustment.")

    parsed = parse_rfc2616_date(server_date)
    if parsed is None:
        raise RuntimeError(f"Could not parse server Date header: {server_date}")

    CLOCK_SKEW_SECONDS = parsed - time.time()


def generate_sec_ms_gec() -> str:
    ticks = get_unix_timestamp()
    ticks += WIN_EPOCH
    ticks -= ticks % 300
    ticks *= 10_000_000
    to_hash = f"{ticks:.0f}{TRUSTED_CLIENT_TOKEN}"
    return hashlib.sha256(to_hash.encode("ascii")).hexdigest().upper()


def generate_muid() -> str:
    return secrets.token_hex(16).upper()


def headers_with_muid(headers: dict[str, str]) -> dict[str, str]:
    result = dict(headers)
    result["Cookie"] = f"muid={generate_muid()};"
    return result


def connect_id() -> str:
    return uuid.uuid4().hex


def date_to_string() -> str:
    return time.strftime(
        "%a %b %d %Y %H:%M:%S GMT+0000 (Coordinated Universal Time)",
        time.gmtime(),
    )


def mkssml(text: str, voice: str, rate: str, volume: str, pitch: str) -> str:
    return (
        "<speak version='1.0' xmlns='http://www.w3.org/2001/10/synthesis' xml:lang='en-US'>"
        f"<voice name='{voice}'>"
        f"<prosody pitch='{pitch}' rate='{rate}' volume='{volume}'>"
        f"{escape(text)}"
        "</prosody>"
        "</voice>"
        "</speak>"
    )


def ssml_headers_plus_data(request_id: str, timestamp: str, ssml: str) -> str:
    return (
        f"X-RequestId:{request_id}\r\n"
        "Content-Type:application/ssml+xml\r\n"
        f"X-Timestamp:{timestamp}Z\r\n"
        "Path:ssml\r\n\r\n"
        f"{ssml}"
    )


def get_headers_and_data(data: bytes, header_length: int) -> tuple[dict[bytes, bytes], bytes]:
    headers = {}
    for line in data[:header_length].split(b"\r\n"):
        key, value = line.split(b":", 1)
        headers[key] = value
    return headers, data[header_length + 2 :]
