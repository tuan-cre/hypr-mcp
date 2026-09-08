"""grim wrapper. Returns (png_bytes, origin_x, origin_y)."""

from ..core.geometry import Region, find_client
from ..errors import ScreenshotError, require_tool
from .proc import run
from ..backend import hyprctl as _h


async def capture(monitor=None, window=None, region=None, include_cursor=False):
    require_tool("grim")
    cmd = ["grim", "-t", "png", "-l", "0"]
    ox, oy = 0, 0
    if include_cursor:
        cmd.append("-c")
    if window:
        clients = await _h.query("clients")
        c = find_client(clients, window)
        if c is None:
            raise ScreenshotError(f"No window found matching '{window}'")
        r = Region(int(c["at"][0]), int(c["at"][1]), int(c["size"][0]), int(c["size"][1]))
        cmd += ["-g", r.to_grim()]
        ox, oy = r.x, r.y
    elif region:
        r = Region.parse(region)
        cmd += ["-g", r.to_grim()]
        ox, oy = r.x, r.y
    elif monitor:
        cmd += ["-o", monitor]
        for m in await _h.query("monitors"):
            if m["name"] == monitor:
                ox, oy = int(m["x"]), int(m["y"])
                break
        else:
            raise ScreenshotError(f"Monitor '{monitor}' not found")
    cmd.append("-")
    out = await run(*cmd)
    if not out:
        raise ScreenshotError("grim produced no output")
    return out, ox, oy
