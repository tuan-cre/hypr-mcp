from hypr_mcp.backend.hyprctl import MIN_VERSION, lua_str, parse_version, shortcut_key
from hypr_mcp.core.geometry import Region, matches_selector, norm_text
from hypr_mcp.core.ocr import find_text


def test_parse_version():
    assert parse_version("Hyprland 0.55.2 built from branch main") == (0, 55)
    assert parse_version("Hyprland 0.54.0 built from branch main") == (0, 54)
    assert parse_version("garbage") is None


def test_min_version_gate():
    assert parse_version("Hyprland 0.55.0 foo") >= MIN_VERSION
    assert parse_version("Hyprland 0.56.1 foo") >= MIN_VERSION
    assert parse_version("Hyprland 0.54.3 foo") < MIN_VERSION


def test_lua_str():
    assert lua_str('a"b\\c') == '"a\\"b\\\\c"'


def test_shortcut_key():
    assert shortcut_key("Return") == "return"
    assert shortcut_key("A") == "a"
    assert shortcut_key("F4") == "f4"
    assert shortcut_key("space") == "space"
    assert shortcut_key("/") == "slash"
    assert shortcut_key(".") == "period"
    assert shortcut_key("-") == "minus"


def test_region():
    r = Region.parse("100,200 800x600")
    assert (r.x, r.y, r.w, r.h) == (100, 200, 800, 600)
    assert r.to_grim() == "100,200 800x600"


def test_selector():
    assert matches_selector({"class": "Firefox", "title": "x"}, "class:firefox")
    assert matches_selector({"class": "X", "title": "My Document"}, "title:document")
    assert matches_selector({"class": "Kitty", "title": ""}, "kitty")
    assert not matches_selector({"class": "Kitty", "title": ""}, "firefox")


def test_norm_text():
    assert norm_text("Master Duel") == "masterduel"
    assert norm_text("Yu-Gi-Oh! Master Duel") == "yugiohmasterduel"
    assert norm_text("UPDATE") == "update"
    assert norm_text("!!!") == ""


def test_selector_normalized_title():
    assert matches_selector({"class": "X", "title": "masterduel"}, "title:Master Duel")
    assert matches_selector({"class": "X", "title": "Master Duel"}, "title:masterduel")
    assert matches_selector({"class": "X", "title": "Yu-Gi-Oh! Master Duel"}, "title:yugioh master duel")
    assert not matches_selector({"class": "X", "title": "Wuthering Waves"}, "title:Master Duel")
    assert not matches_selector({"class": "X", "title": "anything"}, "title:!!!")


def _box(text, conf=90):
    return {"text": text, "x": 0, "y": 0, "w": 10, "h": 10, "conf": conf}


def test_find_text_normalized():
    boxes = [_box("Master"), _box("Duel"), _box("Waves")]
    assert len(find_text(boxes, "master duel")) == 1
    assert find_text(boxes, "Master-Duel") == []  # one token can't span per-word boxes
    assert find_text([_box("Master-Duel")], "master duel") == []  # fused box: same reason
    assert find_text([_box("Master-Duel")], "Master-Duel") != []
    assert len(find_text(boxes, "MASTERDUEL")) == 0  # per-word boxes need both words
    assert find_text([_box("Update")], "UPDATE")
    assert find_text([_box("masterduel")], "Master Duel") == []  # fused box needs split words
    assert find_text([_box("masterduel")], "masterduel") != []
    assert find_text(boxes, "!!!") == []
