"""Hyprland 0.55+ backend: hl.dsp.* Lua dispatch syntax."""

from ..config import Settings
from ..core.geometry import find_client, matches_selector
from ..errors import WindowNotFoundError
from . import common


class LuaBackend:
    name = "lua"

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or Settings()

    async def query(self, command: str):
        return await common.query(command)

    async def _lua(self, call: str) -> str:
        attempts = self.settings.send_shortcut_retries if "send_shortcut" in call else self.settings.dispatch_retries
        return await common.raw_dispatch([call], attempts=attempts)

    async def focus_window(self, target: str) -> str:
        return await self._lua(f"hl.dsp.focus({{window={common.lua_str(target)}}})")

    async def close_window(self, target: str | None) -> str:
        if target:
            return await self._lua(f"hl.dsp.window.close({{window={common.lua_str(target)}}})")
        return await self._lua("hl.dsp.window.close()")

    async def move_window(self, x, y, workspace, target) -> str:
        parts = []
        if x is not None and y is not None:
            if target:
                await self._lua(f"hl.dsp.window.move({{x = {int(x)}, y = {int(y)}, window = {common.lua_str(target)}}})")
            else:
                await self._lua(f"hl.dsp.window.move({{x = {int(x)}, y = {int(y)}}})")
            parts.append(f"Moved to ({x},{y})")
        if workspace is not None:
            try:
                ws_expr = str(int(workspace))
            except ValueError:
                ws_expr = common.lua_str(workspace)
            if target:
                await self._lua(f"hl.dsp.window.move({{workspace={ws_expr}, window={common.lua_str(target)}}})")
            else:
                await self._lua(f"hl.dsp.window.move({{workspace={ws_expr}}})")
            parts.append(f"Moved to workspace {workspace}")
        return "; ".join(parts) or "No position or workspace specified — nothing to do."

    async def resize_window(self, width: int, height: int, target: str | None) -> str:
        # Lua resize needs an anchor position; use the window's current origin.
        if target:
            clients = await common.query("clients")
            origin = None
            for c in clients:
                if matches_selector(c, target):
                    origin = (int(c["at"][0]), int(c["at"][1]))
                    break
            if origin is None:
                raise WindowNotFoundError(f"No window found matching '{target}'")
            ox, oy = origin
            return await self._lua(
                f"hl.dsp.window.resize({{w = {int(width)}, h = {int(height)}, "
                f"x = {ox}, y = {oy}, window = {common.lua_str(target)}}})")
        pos = await common.query("activewindow")
        ox, oy = int(pos["at"][0]), int(pos["at"][1])
        return await self._lua(
            f"hl.dsp.window.resize({{w = {int(width)}, h = {int(height)}, x = {ox}, y = {oy}}})")

    async def toggle_fullscreen(self, mode: str) -> str:
        if mode == "fullscreen":
            return await self._lua("hl.dsp.window.fullscreen({action=\"toggle\"})")
        return await self._lua(
            "hl.dsp.window.fullscreen({mode=\"maximized\", action=\"toggle\"})")

    async def toggle_floating(self, target: str | None) -> str:
        if target:
            return await self._lua(
                f"hl.dsp.window.float({{action=\"toggle\", window={common.lua_str(target)}}})")
        return await self._lua("hl.dsp.window.float({action=\"toggle\"})")

    async def switch_workspace(self, workspace: str) -> str:
        try:
            return await self._lua(f"hl.dsp.focus({{workspace={int(workspace)}}})")
        except ValueError:
            return await self._lua(f"hl.dsp.focus({{workspace={common.lua_str(workspace)}}})")

    async def move_cursor(self, x: int, y: int) -> None:
        await self._lua(f"hl.dsp.cursor.move({{x = {int(x)}, y = {int(y)}}})")

    async def send_shortcut(self, mods: str, key: str, target: str | None) -> str:
        key = common.shortcut_key(key)
        fields = [f"mods = {common.lua_str(mods)}", f"key = {common.lua_str(key)}"]
        if target:
            fields.append(f"window = {common.lua_str(target)}")
        return await self._lua(f"hl.dsp.send_shortcut({{{', '.join(fields)}}})")

    async def launch(self, command: str) -> str:
        return await self._lua(f"hl.dsp.exec_cmd({common.lua_str(command)})")

    async def window_origin(self, selector: str) -> tuple[int, int]:
        clients = await common.query("clients")
        c = find_client(clients, selector)
        if c is None:
            raise WindowNotFoundError(f"No window found matching '{selector}'")
        return int(c["at"][0]), int(c["at"][1])
