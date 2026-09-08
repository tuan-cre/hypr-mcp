from hypr_mcp.backend.hyprctl import MIN_VERSION, lua_str, parse_version, shortcut_key
from hypr_mcp.core.geometry import Region, matches_selector


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


def test_region():
    r = Region.parse("100,200 800x600")
    assert (r.x, r.y, r.w, r.h) == (100, 200, 800, 600)
    assert r.to_grim() == "100,200 800x600"


def test_selector():
    assert matches_selector({"class": "Firefox", "title": "x"}, "class:firefox")
    assert matches_selector({"class": "X", "title": "My Document"}, "title:document")
    assert matches_selector({"class": "Kitty", "title": ""}, "kitty")
    assert not matches_selector({"class": "Kitty", "title": ""}, "firefox")
