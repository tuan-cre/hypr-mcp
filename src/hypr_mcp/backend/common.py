"""Shared hyprctl helpers: query, Lua quoting, key normalization, version parse."""

import asyncio
import json
import re

from ..errors import HyprctlError, require_tool

_KEY_ALIASES = {
    "Return": "return", "Enter": "return",
    "Escape": "escape", "Esc": "escape",
    "Space": "space", "Tab": "tab",
    "Backspace": "backspace", "Delete": "delete", "Del": "delete",
    "Insert": "insert", "Ins": "insert",
    "Home": "home", "End": "end",
    "Left": "left", "Right": "right", "Up": "up", "Down": "down",
    "PageUp": "page_up", "Page_Up": "page_up",
    "PageDown": "page_down", "Page_Down": "page_down",
}


def lua_str(s: str) -> str:
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def shortcut_key(key: str) -> str:
    if key in _KEY_ALIASES:
        return _KEY_ALIASES[key]
    if len(key) == 1:
        return key.lower()
    if re.fullmatch(r"F\d{1,2}", key):
        return key.lower()
    return key


def parse_version(first_line: str) -> tuple[int, int] | None:
    """'Hyprland 0.55.2 built from ...' -> (0, 55). None if unparseable."""
    m = re.search(r"Hyprland\s+(\d+)\.(\d+)", first_line)
    if not m:
        return None
    return int(m.group(1)), int(m.group(2))


def is_lua_version(first_line: str) -> bool:
    v = parse_version(first_line)
    return v is not None and v >= (0, 55)


async def query(command: str):
    require_tool("hyprctl")
    proc = await asyncio.create_subprocess_exec(
        "hyprctl", command, "-j",
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    if proc.returncode != 0:
        raise HyprctlError(f"hyprctl {command} failed: {stderr.decode().strip()}")
    try:
        return json.loads(stdout)
    except json.JSONDecodeError as e:
        raise HyprctlError(f"Failed to parse hyprctl {command} output: {e}") from e


async def raw_dispatch(args: list[str], attempts: int = 2) -> str:
    """Run `hyprctl dispatch ...`, retry on transient `error:` output."""
    require_tool("hyprctl")
    out = ""
    for attempt in range(attempts):
        proc = await asyncio.create_subprocess_exec(
            "hyprctl", "dispatch", *args,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        out = (stdout.decode() + stderr.decode()).strip()
        if proc.returncode == 0 and not out.lstrip().lower().startswith("error:"):
            return out
        if attempt < attempts - 1:
            await asyncio.sleep(0.2 * (attempt + 1))
    raise HyprctlError(f"hyprctl dispatch {' '.join(args)} failed: {out}")
