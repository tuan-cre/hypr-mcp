"""Screenshot + OCR tools. Auto-scope to active window unless scope="full"."""

import asyncio


async def _capture(get_backend, settings, monitor=None, window=None, region=None,
                   scope="auto", include_cursor=False):
    from ..backend import hyprctl as _h
    from ..core import grim
    if scope == "full" or monitor or window or region:
        return await grim.capture(monitor, window, region, include_cursor)
    active = await _h.query("activewindow")
    if active and active.get("class"):
        x, y = active["at"]
        w, h = active["size"]
        return await grim.capture(region=f"{int(x)},{int(y)} {int(w)}x{int(h)}",
                                  include_cursor=include_cursor)
    return await grim.capture(include_cursor=include_cursor)


def register(mcp, get_backend, settings):
    @mcp.tool()
    async def screenshot(monitor: str | None = None, window: str | None = None,
                         region: str | None = None,
                         max_width: int | None = None, quality: int | None = None,
                         include_cursor: bool = False,
                         path: str | None = None):
        """Screenshot to inline JPEG + coordinate mapping (coords are absolute).

        Pass path to save full-res PNG to disk instead (no token cost) —
        for debugging OCR without an inline image.
        """
        import os
        from ..core import grim, images
        if path:
            png, ox, oy = await grim.capture(monitor, window, region, include_cursor)
            full = os.path.expanduser(path)
            os.makedirs(os.path.dirname(full) or ".", exist_ok=True)
            with open(full, "wb") as f:
                f.write(png)
            return f"Saved {len(png)} bytes to {full} (origin {ox},{oy})"
        mw = max_width or settings.screenshot_max_width
        q = quality or settings.screenshot_quality
        png, ox, oy = await grim.capture(monitor, window, region, include_cursor)
        nw, nh = images.native_size(png)
        image, scale = images.resize_and_compress(png, max_width=mw, quality=q)
        iw, ih = (int(nw * scale), int(nh * scale)) if scale != 1.0 else (nw, nh)
        return [image, images.coord_help(iw, ih, nw, nh, ox, oy, scale)]

    @mcp.tool()
    async def find_text_on_screen(target: str, monitor: str | None = None,
                                  window: str | None = None, region: str | None = None,
                                  scope: str = "auto") -> str:
        """OCR-search for text. Returns absolute coords for mouse_click."""
        from ..core import ocr
        png, ox, oy = await _capture(get_backend, settings, monitor, window, region, scope)
        matches = ocr.find_text(await asyncio.to_thread(ocr.extract_boxes, png, settings), target)
        if not matches:
            preview = (await asyncio.to_thread(ocr.extract_text, png, settings))[:500]
            return f"Text '{target}' not found.\n\nOCR detected text:\n{preview}"
        out = [f"Found {len(matches)} match(es) for '{target}':"]
        for m in matches:
            out.append(f"- \"{m['text']}\" at screen ({m['x']+ox+m['w']//2}, {m['y']+oy+m['h']//2}) "
                       f"[box: {m['x']+ox},{m['y']+oy} {m['w']}x{m['h']}, conf: {m['conf']}%]")
        return "\n".join(out)

    @mcp.tool()
    async def wait_text(target: str, window: str | None = None,
                        region: str | None = None, monitor: str | None = None,
                        timeout: float = 10.0, disappear: bool = False) -> str:
        """Wait for on-screen text to appear (or disappear). Replaces blind sleeps.

        Use for in-window state no compositor event covers: button flips
        (UPDATE→PLAY), page content, dialogs. Returns instantly on match.
        """
        b = await get_backend()
        return await b.wait_text(target, window, region, monitor, timeout, disappear)

    @mcp.tool()
    async def click_text(target: str, button: str = "left", double: bool = False,
                         monitor: str | None = None, window: str | None = None,
                         region: str | None = None, occurrence: int = 1,
                         scope: str = "auto") -> str:
        """OCR-find text and click it. Focusing `window` first if given."""
        from ..core import input as inp, ocr
        b = await get_backend()
        if window:
            await b.focus_window(window)
            await asyncio.sleep(settings.focus_settle_s)
        png, ox, oy = await _capture(get_backend, settings, monitor, window, region, scope)
        matches = ocr.find_text(await asyncio.to_thread(ocr.extract_boxes, png, settings), target)
        if not matches:
            preview = (await asyncio.to_thread(ocr.extract_text, png, settings))[:500]
            return f"Could not find '{target}' on screen.\n\nOCR detected text:\n{preview}"
        if occurrence > len(matches):
            return f"Only found {len(matches)} match(es) for '{target}', but occurrence={occurrence} requested."
        m = matches[occurrence - 1]
        sx, sy = m["x"] + ox + m["w"] // 2, m["y"] + oy + m["h"] // 2
        await b.move_cursor(sx, sy)
        await asyncio.sleep(settings.click_settle_s)
        await inp.click(button, double=double)
        return f"{'Double-clicked' if double else 'Clicked'} '{m['text']}' at ({sx}, {sy}) [conf: {m['conf']}%]"
