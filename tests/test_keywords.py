from clipper.keywords import collect_keywords_for_source, keyword_filter, merge_normalize_maps


def test_source_specific_merge():
    kw = {
        "global_keywords": ["에너지"],
        "normalize": {"데이터 센터": "데이터센터"},
        "source_specific_keywords": {"gasnews": ["LNG"]},
    }
    keys, norm = collect_keywords_for_source(kw, "gasnews", True)
    assert "에너지" in keys and "LNG" in keys
    keys2, _ = collect_keywords_for_source(kw, "gasnews", False)
    assert "LNG" not in keys2


def test_keyword_filter_alias():
    kw = ["데이터센터"]
    norm = merge_normalize_maps({"데이터 센터": "데이터센터"}, {})
    fr = keyword_filter("서울 데이터 센터 구축", kw, norm)
    assert fr.matched


def test_exclude():
    fr = keyword_filter("에너지 토론", ["에너지"], {}, exclude_keywords=["에너지"])
    assert not fr.matched
