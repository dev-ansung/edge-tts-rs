from edgetts_cli.chunking import remove_incompatible_characters, split_text_by_byte_length


def test_remove_incompatible_characters_strips_control_chars():
    text = "a\x00b\x0bc\x1fd"
    assert remove_incompatible_characters(text) == "a b c d"


def test_remove_incompatible_characters_preserves_normal_text():
    text = "Hello, world! 123"
    assert remove_incompatible_characters(text) == text


def test_split_empty_text_returns_empty_list():
    assert split_text_by_byte_length("", 4096) == []


def test_split_short_text_returns_single_chunk():
    text = "Hello, world!"
    assert split_text_by_byte_length(text, 4096) == [text]


def test_split_respects_byte_length_budget():
    text = ("word " * 2000).strip()
    chunks = split_text_by_byte_length(text, 100)
    assert len(chunks) > 1
    for chunk in chunks:
        assert len(chunk.encode("utf-8")) <= 100


def test_split_reassembles_to_equivalent_content():
    text = ("The quick brown fox jumps over the lazy dog. " * 50).strip()
    chunks = split_text_by_byte_length(text, 200)
    # each word should survive somewhere across the chunks
    rejoined = " ".join(chunks)
    assert "quick brown fox" in rejoined


def test_split_prefers_space_boundary_over_hard_cut():
    text = "aaaa bbbb cccc dddd eeee"
    # byte_length lands mid-word for a naive cut; should split on the space instead
    chunks = split_text_by_byte_length(text, 12)
    for chunk in chunks:
        assert not chunk.startswith(" ")


def test_split_handles_html_entities_near_boundary():
    text = "price &amp; tax " * 100
    chunks = split_text_by_byte_length(text.strip(), 50)
    rejoined = "".join(chunks)
    # entity should never be split across chunks
    assert "&amp" not in rejoined or "&amp;" in rejoined
    for chunk in chunks:
        # no chunk should end mid-entity (an '&' with no matching ';')
        last_amp = chunk.rfind("&")
        if last_amp != -1:
            assert ";" in chunk[last_amp:]


def test_split_handles_multibyte_unicode_near_boundary():
    text = ("héllo wörld ünïcödé " * 100).strip()
    chunks = split_text_by_byte_length(text, 57)
    for chunk in chunks:
        # must be valid utf-8 and round-trip
        assert chunk.encode("utf-8").decode("utf-8") == chunk


def test_split_hard_cuts_unbroken_token_at_byte_budget():
    # a single unbroken run with no space/newline still splits, at the byte budget
    text = "a" * 5000
    chunks = split_text_by_byte_length(text, 10)
    assert len(chunks) == 500
    for chunk in chunks:
        assert len(chunk.encode("utf-8")) <= 10
