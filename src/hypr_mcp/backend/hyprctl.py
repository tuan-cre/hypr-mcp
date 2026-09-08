"""Hyprland >=0.55 backend: hl.dsp.* Lua dispatch. Single code path."""

import asyncio
import json
import re
import shutil

from ..config import Settings
from ..core.geometry import find_client, matches_selector
from ..errors import HyprctlError, require_tool
from .events import get_bus, norm_addr

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
        low = out.lstrip().lower()
        # Hyprland reports e.g. "window not found" as warning: with rc=0 —
        # a silent no-op unless we treat it as failure.
        failed = low.startswith("error:") or (
            low.startswith("warning:") and "not found" in low)
        if proc.returncode == 0 and not failed:
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

    async def _resolve(self, target: str) -> str:
        """Resolve any selector to an exact address:0x... argument.

        The compositor's own title: matching differs from hyprctl JSON
        (initial vs current title), so our client-side match is
        authoritative — dispatching the raw selector could hit the
        wrong window.
        """
        from ..errors import WindowNotFoundError
        if target.startswith("address:"):
            return f"address:0x{norm_addr(target[8:])}"
        clients = await query("clients")
        c = find_client(clients, target)
        if c is None:
            raise WindowNotFoundError(f"No window found matching '{target}'")
        return f"address:0x{norm_addr(c['address'])}"

    async def query(self, command: str):
        return await query(command)

    async def _dispatch_and_wait(self, call: str, event: str, match=None,
                                 desc: str = "") -> tuple[str, str]:
        """Dispatch, then wait for the confirming socket2 event.

        The waiter registers BEFORE dispatching so fast events can't slip
        through. Returns (dispatch_output, event_data).
        """
        bus = get_bus()
        waiter = asyncio.create_task(
            bus.wait_for(event, match, timeout=self.settings.event_timeout_s, desc=desc))
        try:
            out = await self._lua(call)
        except Exception:
            waiter.cancel()
            raise
        return out, await waiter

    async def _active_matches(self, target: str) -> bool:
        active = await query("activewindow")
        return bool(active and active.get("class") and matches_selector(active, target))

    async def focus_window(self, target: str) -> str:
        # Waiter first, then re-check: focus may land between our first
        # check and the dispatch (e.g. a just-launched window), in which
        # case the compositor emits no event for the redundant dispatch.
        bus = get_bus()
        waiter = asyncio.create_task(bus.wait_for(
            "activewindowv2", timeout=self.settings.event_timeout_s,
            desc=f"focus {target}"))
        try:
            if await self._active_matches(target):
                waiter.cancel()
                return f"Already focused on '{target}'"
            win = await self._resolve(target)
            await self._lua(f"hl.dsp.focus({{window={lua_str(win)}}})")
            addr = await waiter
        except Exception:
            waiter.cancel()
            raise
        if not await self._active_matches(target):
            raise HyprctlError(f"Focus event arrived but active window is not '{target}'")
        return f"Focused window matching '{target}' (0x{norm_addr(addr)})"

    async def close_window(self, target: str | None) -> str:
        from ..errors import WindowNotFoundError
        if target:
            win = await self._resolve(target)
            addr = norm_addr(win.split(":", 1)[1])
            call = f"hl.dsp.window.close({{window={lua_str(win)}}})"
            match = lambda data: norm_addr(data.split(",")[0]) == addr  # noqa: E731
        else:
            active = await query("activewindow")
            if not active or not active.get("address"):
                raise WindowNotFoundError("No window is currently focused.")
            call = "hl.dsp.window.close()"
            match = None
        await self._dispatch_and_wait(
            call, "closewindow", match=match,
            desc=f"close {target or 'active window'}")
        return f"Closed window{f' matching {target!r}' if target else ' (active)'}"

    async def switch_workspace(self, workspace: str) -> str:
        # Same race as focus: registering the waiter first, then skipping
        # the dispatch when already there (no event fires for a no-op).
        bus = get_bus()
        waiter = asyncio.create_task(bus.wait_for(
            "workspace",
            match=lambda data: data == workspace or data.split(":")[-1] == workspace,
            timeout=self.settings.event_timeout_s,
            desc=f"switch to workspace {workspace}"))
        try:
            current = await query("activeworkspace")
            if str(current.get("name")) == workspace or str(current.get("id")) == workspace:
                waiter.cancel()
                return f"Already on workspace {workspace}"
            try:
                call = f"hl.dsp.focus({{workspace={int(workspace)}}})"
            except ValueError:
                call = f"hl.dsp.focus({{workspace={lua_str(workspace)}}})"
            await self._lua(call)
            await waiter
        except Exception:
            waiter.cancel()
            raise
        return f"Switched to workspace {workspace} (confirmed)"

    async def move_window(self, x, y, workspace, target) -> str:
        parts = []
        win = await self._resolve(target) if target else None
        if x is not None and y is not None:
            if win:
                await self._lua(f"hl.dsp.window.move({{x = {int(x)}, y = {int(y)}, window = {lua_str(win)}}})")
            else:
                await self._lua(f"hl.dsp.window.move({{x = {int(x)}, y = {int(y)}}})")
            parts.append(f"Moved to ({x},{y})")
        if workspace is not None:
            try:
                ws_expr = str(int(workspace))
            except ValueError:
                ws_expr = lua_str(workspace)
            if win:
                await self._lua(f"hl.dsp.window.move({{workspace={ws_expr}, window={lua_str(win)}}})")
            else:
                await self._lua(f"hl.dsp.window.move({{workspace={ws_expr}}})")
            parts.append(f"Moved to workspace {workspace}")
        return "; ".join(parts) or "No position or workspace specified — nothing to do."

    async def resize_window(self, width: int, height: int, target: str | None) -> str:
        if target:
            win = await self._resolve(target)
            want = norm_addr(win.split(":", 1)[1])
            clients = await query("clients")
            origin = next(
                ((int(c["at"][0]), int(c["at"][1]))
                 for c in clients if norm_addr(c.get("address", "")) == want),
                None)
            if origin is None:  # resolved a moment ago; window vanished since
                from ..errors import WindowNotFoundError
                raise WindowNotFoundError(f"No window found matching '{target}'")
            ox, oy = origin
            await self._lua(
                f"hl.dsp.window.resize({{w = {int(width)}, h = {int(height)}, "
                f"x = {ox}, y = {oy}, window = {lua_str(win)}}})")
        else:
            pos = await query("activewindow")
            ox, oy = int(pos["at"][0]), int(pos["at"][1])
            await self._lua(
                f"hl.dsp.window.resize({{w = {int(width)}, h = {int(height)}, x = {ox}, y = {oy}}})")
        return f"Resized to {width}x{height}"

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
            win = await self._resolve(target)
            await self._lua(
                f"hl.dsp.window.float({{action={lua_str(action)}, window={lua_str(win)}}})")
        else:
            await self._lua(f"hl.dsp.window.float({{action={lua_str(action)}}})")
        return f"Toggled floating{f' for {target}' if target else ''}"

    async def move_cursor(self, x: int, y: int) -> None:
        await self._lua(f"hl.dsp.cursor.move({{x = {int(x)}, y = {int(y)}}})")

    async def send_shortcut(self, mods: str, key: str, target: str | None) -> str:
        key = shortcut_key(key)
        fields = [f"mods = {lua_str(mods)}", f"key = {lua_str(key)}"]
        if target:
            fields.append(f"window = {lua_str(await self._resolve(target))}")
        return await self._lua(f"hl.dsp.send_shortcut({{{', '.join(fields)}}})")

    async def launch(self, command: str, expect_class: str | None = None) -> str:
        # exec_raw: no shell expansion (exec_cmd would run sh -c).
        # Wait for the window to actually open. The class guess (argv[0])
        # often differs from the real class (helium-browser -> helium),
        # so also accept the name before any '-'/' ' suffix.
        first = command.split()[0] if command.split() else ""
        hints = {h for h in (
            (expect_class or "").lower(), first.lower(),
            first.lower().split("-")[0], first.lower().split(" ")[0],
        ) if h}
        data = (await self._dispatch_and_wait(
            f"hl.dsp.exec_raw({lua_str(command)})",
            "openwindow",
            match=lambda d: d.split(",")[2].lower() in hints,
            desc=f"launch {command}"))[1]
        addr = norm_addr(data.split(",")[0])
        cls = data.split(",")[2] if "," in data else ""
        return f"Launched: {command} (window 0x{addr} [{cls}])"

    async def toggle_special(self, name: str) -> str:
        return await self._lua(f"hl.dsp.workspace.toggle_special({lua_str(name)})")

    async def move_to_special(self, name: str, target: str | None = None) -> str:
        ws = f"special:{name}"
        if target:
            win = await self._resolve(target)
            return await self._lua(
                f"hl.dsp.window.move({{workspace={lua_str(ws)}, window={lua_str(win)}}})")
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
