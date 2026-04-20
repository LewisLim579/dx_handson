from clipper.dedupe import already_sent, dedupe_keys, normalize_url, register_sent, title_date_hash
from clipper.models import ParsedItem


def test_normalize_url_strips_fragment():
    a = normalize_url("https://Example.com/path/?x=1#frag")
    b = normalize_url("https://example.com/path?x=1")
    assert a == b


def test_dedupe_register():
    item = ParsedItem(external_id="abc", title="t", link="https://news.example/a", published_at=None)
    keys = dedupe_keys(item)
    assert any(k.startswith("id:") for k in keys)
    sent: dict = {}
    register_sent(sent, item, {"k": 1})
    assert already_sent(sent, item)


def test_title_hash_stable():
    h1 = title_date_hash("제목", "2026-01-01")
    h2 = title_date_hash("제목", "2026-01-01")
    assert h1 == h2
