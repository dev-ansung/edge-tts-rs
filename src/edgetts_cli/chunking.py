from html import escape

_CONTROL_RANGES = ((0, 8), (11, 12), (14, 31))


def remove_incompatible_characters(text: str) -> str:
    chars = list(text)
    for i, ch in enumerate(chars):
        code = ord(ch)
        if any(lo <= code <= hi for lo, hi in _CONTROL_RANGES):
            chars[i] = " "
    return "".join(chars)


def split_text_by_byte_length(text: str, byte_length: int = 4096) -> list[str]:
    data = escape(remove_incompatible_characters(text)).encode("utf-8")
    out = []

    while len(data) > byte_length:
        split_at = data.rfind(b"\n", 0, byte_length)
        if split_at < 0:
            split_at = data.rfind(b" ", 0, byte_length)
        if split_at < 0:
            split_at = byte_length
            while split_at > 0:
                try:
                    data[:split_at].decode("utf-8")
                    break
                except UnicodeDecodeError:
                    split_at -= 1

        while split_at > 0 and b"&" in data[:split_at]:
            amp = data.rindex(b"&", 0, split_at)
            if data.find(b";", amp, split_at) != -1:
                break
            split_at = amp

        if split_at <= 0:
            raise ValueError("Unable to find safe split point.")

        chunk = data[:split_at].strip()
        if chunk:
            out.append(chunk.decode("utf-8"))
        data = data[split_at:]

    data = data.strip()
    if data:
        out.append(data.decode("utf-8"))

    return out
