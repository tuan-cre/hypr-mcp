"""Hyprland >=0.55 backend: hl.dsp.* Lua dispatch. Single code path."""

import asyncio
import json
import re
import shutil

from ..config import Settings
from ..core.geometry import find_client, matches_selector
from ..errors import HyprctlError, require_tool

MIN_VERSION = (0, 55)

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
    m = re.search(r"Hyprland\s+(\d+)\.(\d+)", first_line)
    if not m:
        return None
    return int(m.group(1)), int(m.group(2))


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


async def _raw_dispatch(call: str, attempts: int = 2) -> str:
    require_tool("hyprctl")
    out = ""
    for attempt in range(attempts):
        proc = await asyncio.create_subprocess_exec(
            "hyprctl", "dispatch", call,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        out = (stdout.decode() + stderr.decode()).strip()
        if proc.returncode == 0 and not out.lstrip().lower().startswith("error:"):
            return out
        if attempt < attempts - 1:
            await asyncio.sleep(0.2 * (attempt + 1))
    raise HyprctlError(f"hyprctl dispatch '{call}' failed: {out}")


class HyprlandBackend:
    """All hyprctl strings live here. Requires Hyprland >= 0.55."""

    name = "lua"

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or Settings()

    async def _lua(self, call: str) -> str:
        attempts = (self.settings.send_shortcut_retries
                    if "send_shortcut" in call else self.settings.dispatch_retries)
        return await _raw_dispatch(call, attempts=attempts)

    async def focus_window(self, target: str) -> str:
        return await self._lua(f"hl.dsp.focus({{window={lua_str(target)}}})")

    async def close_window(self, target: str | None) -> str:
        if target:
            return await self._lua(f"hl.dsp.window.close({{window={lua_str(target)}}})")
        return await self._lua("hl.dsp.window.close()")

    async def move_window(self, x, y, workspace, target) -> str:
        parts = []
        if x is not None and y is not None:
            if target:
                await self._lua(f"hl.dsp.window.move({{x = {int(x)}, y = {int(y)}, window = {lua_str(target)}}})")
            else:
                await self._lua(f"hl.dsp.window.move({{x = {int(x)}, y = {int(y)}}})")
            parts.append(f"Moved to ({x},{y})")
        if workspace is not None:
            try:
                ws_expr = str(int(workspace))
            except ValueError:
                ws_expr = lua_str(workspace)
            if target:
                await self._lua(f"hl.dsp.window.move({{workspace={ws_expr}, window={lua_str(target)}}})")
            else:
                await self._lua(f"hl.dsp.window.move({{workspace={ws_expr}}})")
            parts.append(f"Moved to workspace {workspace}")
        return "; ".join(parts) or "No position or workspace specified — nothing to do."

    async def resize_window(self, width: int, height: int, target: str | None) -> str:
        if target:
            clients = await query("clients")
            origin = next(
                ((int(c["at"][0]), int(c["at"][1])) for c in clients if matches_selector(c, target)),
                None)
            if origin is None:
                from ..errors import WindowNotFoundError
                raise WindowNotFoundError(f"No window found matching '{target}'")
            ox, oy = origin
            return await self._lua(
                f"hl.dsp.window.resize({{w = {int(width)}, h = {int(height)}, "
                f"x = {ox}, y = {oy}, window = {lua_str(target)}}})")
        pos = await query("activewindow")
        ox, oy = int(pos["at"][0]), int(pos["at"][1])
        return await self._lua(
            f"hl.dsp.window.resize({{w = {int(width)}, h = {int(height)}, x = {ox}, y = {oy}}})")

    async def toggle_fullscreen(self, mode: str = "fullscreen", action: str = "toggle") -> str:
        if action not in ("set", "unset", "toggle"):
            from ..errors import HyprMCPError
            raise HyprMCPError(f"Bad action {action!r}, expected set|unset|toggle")
        if mode == "fullscreen":
            return await self._lua(f"hl.dsp.window.fullscreen({{action={lua_str(action)}}})")
        return await self._lua(
            f"hl.dsp.window.fullscreen({{mode=\"maximized\", action={lua_str(action)}}})")

    async def toggle_floating(self, target: str | None = None, action: str = "toggle") -> str:
        if action not in ("set", "unset", "toggle"):
            from ..errors import HyprMCPError
            raise HyprMCPError(f"Bad action {action!r}, expected set|unset|toggle")
        if target:
            return await self._lua(
                f"hl.dsp.window.float({{action={lua_str(action)}, window={lua_str(target)}}})")
        return await self._lua(f"hl.dsp.window.float({{action={lua_str(action)}}})")

    async def switch_workspace(self, workspace: str) -> str:
        try:
            return await self._lua(f"hl.dsp.focus({{workspace={int(workspace)}}})")
        except ValueError:
            return await self._lua(f"hl.dsp.focus({{workspace={lua_str(workspace)}}})")

    async def move_cursor(self, x: int, y: int) -> None:
        await self._lua(f"hl.dsp.cursor.move({{x = {int(x)}, y = {int(y)}}})")

    async def send_shortcut(self, mods: str, key: str, target: str | None) -> str:
        key = shortcut_key(key)
        fields = [f"mods = {lua_str(mods)}", f"key = {lua_str(key)}"]
        if target:
            fields.append(f"window = {lua_str(target)}")
        return await self._lua(f"hl.dsp.send_shortcut({{{', '.join(fields)}}})")

    async def launch(self, command: str) -> str:
        # exec_raw: no shell expansion (exec_cmd would run sh -c).
        return await self._lua(f"hl.dsp.exec_raw({lua_str(command)})")

    async def toggle_special(self, name: str) -> str:
        return await self._lua(f"hl.dsp.workspace.toggle_special({lua_str(name)})")

    async def move_to_special(self, name: str, target: str | None = None) -> str:
        ws = f"special:{name}"
        if target:
            return await self._lua(
                f"hl.dsp.window.move({{workspace={lua_str(ws)}, window={lua_str(target)}}})")
        return await self._lua(f"hl.dsp.window.move({{workspace={lua_str(ws)}}})")

    async def window_origin(self, selector: str) -> tuple[int, int]:
        clients = await query("clients")
        c = find_client(clients, selector)
        if c is None:
            from ..errors import WindowNotFoundError
            raise WindowNotFoundError(f"No window found matching '{selector}'")
        return int(c["at"][0]), int(c["at"][1])


async def require_backend(settings: Settings | None = None) -> HyprlandBackend:
    """Fail fast on Hyprland < 0.55 instead of mis-dispatching."""
    if shutil.which("hyprctl") is None:
        return HyprlandBackend(settings)
    proc = await asyncio.create_subprocess_exec(
        "hyprctl", "version",
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    stdout, _ = await proc.communicate()
    first = stdout.decode().splitlines()[0] if stdout else ""
    v = parse_version(first)
    if v is not None and v < MIN_VERSION:
        raise HyprctlError(
            f"hypr-mcp requires Hyprland >= 0.55 (Lua dispatch), found {v[0]}.{v[1]}. "
            f"Upgrade Hyprland or use the legacy hyprland-mcp.")
    return HyprlandBackend(settings)
