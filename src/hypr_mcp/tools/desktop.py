"""Window + workspace + monitor tools. Pure formatting, dispatch in backend."""

import asyncio


def register(mcp, get_backend, settings):
    @mcp.tool()
    async def list_monitors() -> str:
        """List monitors with resolution, position, active workspace."""
        b = await get_backend()
        out = []
        for m in await b.query("monitors"):
            out.append(
                f"- {m['name']}: {m['width']}x{m['height']}@{m['refreshRate']:.0f}Hz "
                f"at ({m['x']},{m['y']}), workspace {m['activeWorkspace']['name']}"
                f"{' [focused]' if m.get('focused') else ''}")
        return "\n".join(out)

    @mcp.tool()
    async def list_workspaces() -> str:
        """List active workspaces with window counts."""
        b = await get_backend()
        ws = sorted(await b.query("workspaces"), key=lambda w: w["id"])
        return "\n".join(
            f"- Workspace {w['name']} (id={w['id']}): "
            f"{w['windows']} window(s), monitor {w['monitor']}" for w in ws)

    @mcp.tool()
    async def switch_workspace(workspace: str) -> str:
        """Switch to a workspace by name/number (e.g. "1", "special:scratchpad")."""
        await (await get_backend()).switch_workspace(workspace)
        return f"Switched to workspace {workspace}"

    @mcp.tool()
    async def get_cursor_position() -> str:
        """Cursor position in absolute layout coordinates."""
        pos = await (await get_backend()).query("cursorpos")
        return f"Cursor at ({pos['x']}, {pos['y']})"

    @mcp.tool()
    async def list_windows(workspace: int | None = None, monitor: str | None = None) -> str:
        """List windows with class, title, size, position."""
        clients = await (await get_backend()).query("clients")
        if workspace is not None:
            clients = [c for c in clients if c["workspace"]["id"] == workspace]
        if monitor is not None:
            clients = [c for c in clients if c["monitor"] == monitor]
        if not clients:
            return "No windows found matching the filter."
        out = []
        for c in clients:
            focused = " [focused]" if c.get("focusHistoryID") == 0 else ""
            out.append(
                f"- [{c['class']}] \"{c['title']}\" — "
                f"{c['size'][0]}x{c['size'][1]} at ({c['at'][0]},{c['at'][1]}), "
                f"workspace {c['workspace']['name']}{focused}")
        return "\n".join(out)

    @mcp.tool()
    async def get_active_window() -> str:
        """Details about the focused window."""
        w = await (await get_backend()).query("activewindow")
        if not w or not w.get("class"):
            return "No window is currently focused."
        return (
            f"Active window: [{w['class']}] \"{w['title']}\"\n"
            f"Size: {w['size'][0]}x{w['size'][1]}, Position: ({w['at'][0]},{w['at'][1]})\n"
            f"Workspace: {w['workspace']['name']}, Monitor: {w['monitor']}\n"
            f"Floating: {w['floating']}, Fullscreen: {w['fullscreen']}")

    @mcp.tool()
    async def focus_window(target: str) -> str:
        """Focus a window by selector ("class:firefox", "title:Doc")."""
        await (await get_backend()).focus_window(target)
        return f"Focused window matching '{target}'"

    @mcp.tool()
    async def close_window(target: str | None = None) -> str:
        """Close a window (WM_CLOSE, apps may prompt to save)."""
        await (await get_backend()).close_window(target)
        return f"Closed window{f' matching {target!r}' if target else ' (active)'}"

    @mcp.tool()
    async def move_window(target: str | None = None, x: int | None = None,
                          y: int | None = None, workspace: str | None = None) -> str:
        """Move active/selected window to pixels and/or workspace."""
        return await (await get_backend()).move_window(x, y, workspace, target)

    @mcp.tool()
    async def resize_window(width: int, height: int, target: str | None = None) -> str:
        """Resize active/selected window to pixel dimensions."""
        await (await get_backend()).resize_window(width, height, target)
        return f"Resized to {width}x{height}"

    @mcp.tool()
    async def get_active_workspace() -> str:
        """Focused workspace with window count and monitor."""
        w = await (await get_backend()).query("activeworkspace")
        return (f"Active workspace: {w['name']} (id={w['id']}): "
                f"{w['windows']} window(s), monitor {w['monitor']}")

    @mcp.tool()
    async def toggle_special(name: str) -> str:
        """Toggle a special (scratchpad) workspace by name."""
        await (await get_backend()).toggle_special(name)
        return f"Toggled special workspace '{name}'"

    @mcp.tool()
    async def move_to_special(name: str, target: str | None = None) -> str:
        """Move active/selected window to special workspace `name`."""
        await (await get_backend()).move_to_special(name, target)
        return f"Moved{f' {target}' if target else ''} to special:{name}"

    @mcp.tool()
    async def toggle_fullscreen(mode: str = "fullscreen", action: str = "toggle") -> str:
        """Set fullscreen state. mode: "fullscreen"|"maximize", action: "set"|"unset"|"toggle"."""
        await (await get_backend()).toggle_fullscreen(mode, action)
        return f"{action.capitalize()}d {mode}"

    @mcp.tool()
    async def toggle_floating(target: str | None = None, action: str = "toggle") -> str:
        """Set floating state. action: "set"|"unset"|"toggle"."""
        await (await get_backend()).toggle_floating(target, action)
        return f"{action.capitalize()}d floating{f' for {target}' if target else ''}"

    @mcp.tool()
    async def launch_app(command: str) -> str:
        """Launch an app detached (no shell — no pipes/redirects; binary + args only)."""
        await (await get_backend()).launch(command)
        return f"Launched: {command}"

    @mcp.tool()
    async def clipboard_read(max_chars: int = 4000) -> str:
        """Read clipboard text (truncated to max_chars)."""
        from ..core import clipboard
        text = await clipboard.read()
        if len(text) > max_chars:
            return text[:max_chars] + f"\n...[truncated {len(text) - max_chars} chars]"
        return text

    @mcp.tool()
    async def clipboard_write(text: str) -> str:
        """Write text to clipboard."""
        from ..core import clipboard
        await clipboard.write(text)
        return f"Copied {len(text)} characters to clipboard"

    @mcp.tool()
    async def mouse_move(x: int, y: int) -> str:
        """Move cursor to absolute coordinates (pixel-accurate)."""
        await (await get_backend()).move_cursor(x, y)
        return f"Moved cursor to ({x}, {y})"

    @mcp.tool()
    async def mouse_click(button: str = "left", x: int | None = None,
                          y: int | None = None, double: bool = False,
                          window: str | None = None) -> str:
        """Click at coords or current pos. `window` focuses first (coords stay absolute)."""
        from ..core import input as inp
        b = await get_backend()
        if window:
            await b.focus_window(window)
            await asyncio.sleep(settings.focus_settle_s)
        if x is not None and y is not None:
            await b.move_cursor(x, y)
            await asyncio.sleep(settings.click_settle_s)
        await inp.click(button, double=double)
        pos = f" at ({x},{y})" if x is not None and y is not None else ""
        return f"{'Double-clicked' if double else 'Clicked'} {button}{pos}"

    @mcp.tool()
    async def mouse_scroll(direction: str = "down", amount: int = 3,
                           x: int | None = None, y: int | None = None) -> str:
        """Scroll wheel, optionally after moving to absolute coords."""
        from ..core import input as inp
        b = await get_backend()
        if x is not None and y is not None:
            await b.move_cursor(x, y)
        await inp.scroll(direction, amount)
        pos = f" at ({x},{y})" if x is not None and y is not None else ""
        return f"Scrolled {direction} {amount} steps{pos}"

    @mcp.tool()
    async def mouse_drag(start_x: int, start_y: int, end_x: int, end_y: int,
                         button: str = "left") -> str:
        """Drag in absolute coordinates."""
        from ..core import input as inp
        await inp.drag(await get_backend(), start_x, start_y, end_x, end_y, button)
        return f"Dragged {button} from ({start_x},{start_y}) to ({end_x},{end_y})"

    @mcp.tool()
    async def type_text(text: str, delay_ms: int = 0) -> str:
        """Type text via wtype."""
        from ..core import input as inp
        await inp.type_text(text, delay_ms=delay_ms)
        return f"Typed {len(text)} characters"

    @mcp.tool()
    async def key_press(keys: str, target: str | None = None) -> str:
        """Press combo ("ctrl+c") or single key ("Return"). Single source for shortcuts."""
        from ..core import input as inp
        await inp.key_press(await get_backend(), keys, target=target)
        return f"Pressed {keys}{f' on {target}' if target else ''}"

    @mcp.tool()
    async def paste_text(text: str, target: str | None = None) -> str:
        """Reliable path for unicode/long text: clipboard + ctrl+v (wtype chokes on these)."""
        from ..core import clipboard
        from ..core import input as inp
        b = await get_backend()
        await clipboard.write(text)
        if target:
            await b.focus_window(target)
            await asyncio.sleep(settings.focus_settle_s)
        await inp.key_press(b, "ctrl+v")
        return f"Pasted {len(text)} characters"
