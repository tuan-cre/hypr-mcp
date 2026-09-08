"""ydotool / wtype wrappers. Positioning stays in backend (movecursor)."""

import asyncio

from ..backend import hyprctl as _h
from ..errors import InputError, require_tool
from .proc import run

_DOWN = {"left": "0x40", "right": "0x41", "middle": "0x42"}
_UP = {"left": "0x80", "right": "0x81", "middle": "0x82"}
_MODS = {"CTRL", "SHIFT", "ALT", "SUPER", "MOD2", "MOD3", "MOD5"}


async def click(button: str = "left", double: bool = False) -> None:
    require_tool("ydotool")
    if button not in _DOWN:
        raise InputError(f"Unknown button: {button}. Use 'left', 'right', or 'middle'.")
    for i in range(2 if double else 1):
        await run("ydotool", "click", _DOWN[button])
        await asyncio.sleep(0.06)
        await run("ydotool", "click", _UP[button])
        await asyncio.sleep(0.05 + (0.05 if double and i == 0 else 0))


async def scroll(direction: str = "down", amount: int = 3) -> None:
    require_tool("ydotool")
    y = amount if direction == "down" else -amount
    await run("ydotool", "mousemove", "--wheel", "-x", "0", "-y", str(y))


async def drag(backend, sx: int, sy: int, ex: int, ey: int, button: str = "left") -> None:
    require_tool("ydotool")
    if button not in _DOWN:
        raise InputError(f"Unknown button: {button}")
    await backend.move_cursor(sx, sy)
    await asyncio.sleep(0.05)
    await run("ydotool", "click", _DOWN[button])
    await asyncio.sleep(0.05)
    await backend.move_cursor(ex, ey)
    await asyncio.sleep(0.05)
    await run("ydotool", "click", _UP[button])


async def type_text(text: str, delay_ms: int = 0) -> None:
    try:
        require_tool("wtype")
        cmd = ["wtype"] + (["-d", str(delay_ms)] if delay_ms > 0 else []) + ["--", text]
        await run(*cmd)
    except Exception as e:
        from ..errors import ToolNotFoundError
        if isinstance(e, ToolNotFoundError):
            raise InputError(
                "wtype is not installed — install it, or use paste_text() "
                "(clipboard + ctrl+v, no wtype needed) instead."
            ) from e
        raise


async def key_press(backend, keys: str, target: str | None = None) -> None:
    """Single key via wtype (reliable); combos via backend send_shortcut."""
    parts = keys.split("+")
    if len(parts) == 1:
        require_tool("wtype")
        if target:
            await backend.focus_window(target)
        await run("wtype", "-k", _h.shortcut_key(parts[0]))
        return
    key = _h.shortcut_key(parts[-1])
    mods = [p.upper() for p in parts[:-1]]
    bad = [m for m in mods if m not in _MODS]
    if bad:
        raise InputError(f"Unknown modifier(s): {bad}. Valid: {sorted(_MODS)}")
    await backend.send_shortcut(" ".join(mods), key, target)
