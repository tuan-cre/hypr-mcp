"""Pre-0.55 backend: legacy bare-word dispatch syntax."""

from ..core.geometry import find_client
from ..errors import WindowNotFoundError
from . import common


class LegacyBackend:
    name = "legacy"

    async def query(self, command: str):
        return await common.query(command)

    async def focus_window(self, target: str) -> str:
        return await common.raw_dispatch(["focuswindow", target])

    async def close_window(self, target: str | None) -> str:
        return await common.raw_dispatch(["closewindow", target or ""])

    async def move_window(self, x, y, workspace, target) -> str:
        parts = []
        if x is not None and y is not None:
            await common.raw_dispatch(["movewindowpixel", f"exact {x} {y},{target or ''}"])
            parts.append(f"Moved to ({x},{y})")
        if workspace is not None:
            arg = f"{workspace},{target}" if target else workspace
            await common.raw_dispatch(["movetoworkspace", arg])
            parts.append(f"Moved to workspace {workspace}")
        return "; ".join(parts) or "No position or workspace specified — nothing to do."

    async def resize_window(self, width: int, height: int, target: str | None) -> str:
        if target:
            clients = await common.query("clients")
            from ..core.geometry import matches_selector
            if not any(matches_selector(c, target) for c in clients):
                raise WindowNotFoundError(f"No window found matching '{target}'")
        return await common.raw_dispatch(
            ["resizewindowpixel", f"exact {width} {height},{target or ''}"])

    async def toggle_fullscreen(self, mode: str) -> str:
        flag = "0" if mode == "fullscreen" else "1"
        return await common.raw_dispatch(["fullscreen", flag])

    async def toggle_floating(self, target: str | None) -> str:
        return await common.raw_dispatch(["togglefloating", target or ""])

    async def switch_workspace(self, workspace: str) -> str:
        return await common.raw_dispatch(["workspace", workspace])

    async def move_cursor(self, x: int, y: int) -> None:
        await common.raw_dispatch(["movecursor", f"{x} {y}"])

    async def send_shortcut(self, mods: str, key: str, target: str | None) -> str:
        arg = f"{mods}, {key}, {target or ''}"
        return await common.raw_dispatch(["sendshortcut", arg], attempts=5)

    async def launch(self, command: str) -> str:
        return await common.raw_dispatch(["exec", command])

    async def window_origin(self, selector: str) -> tuple[int, int]:
        clients = await common.query("clients")
        c = find_client(clients, selector)
        if c is None:
            raise WindowNotFoundError(f"No window found matching '{selector}'")
        return int(c["at"][0]), int(c["at"][1])
