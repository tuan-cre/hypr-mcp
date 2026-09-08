"""socket2 event bus. Replaces sleep-guessing with wait-and-confirm.

Hyprland broadcasts every state change on .socket2.sock as lines of
`EVENT>>DATA` (e.g. `openwindow>>564f504d28f0,1,foot,foot`).
One background reader task feeds waiters registered via wait_for().
"""

import asyncio
import os

from ..errors import HyprctlError


def socket_path() -> str:
    sig = os.environ.get("HYPRLAND_INSTANCE_SIGNATURE", "")
    base = os.environ.get("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}")
    return f"{base}/hypr/{sig}/.socket2.sock"


def norm_addr(addr: str) -> str:
    """Normalize a window address (socket omits the 0x prefix, hyprctl adds it)."""
    return addr.strip().lower().removeprefix("0x")


class EventBus:
    def __init__(self) -> None:
        self._waiters: list[tuple[str | None, object, asyncio.Future]] = []
        self._task: asyncio.Task | None = None

    async def ensure_started(self) -> None:
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._reader())

    async def wait_for(self, name: str, match=None, timeout: float = 10.0,
                       desc: str = "") -> str:
        """Wait for an event, return its data. Raise HyprctlError on timeout."""
        await self.ensure_started()
        loop = asyncio.get_running_loop()
        fut = loop.create_future()
        self._waiters.append((name, match or (lambda data: True), fut))
        try:
            return await asyncio.wait_for(fut, timeout)
        except asyncio.TimeoutError:
            raise HyprctlError(
                f"Timed out waiting for event '{name}'"
                f"{f' ({desc})' if desc else ''} after {timeout}s"
            ) from None
        finally:
            self._waiters = [w for w in self._waiters if w[2] is not fut]

    def _feed(self, name: str, data: str) -> None:
        for wname, match, fut in list(self._waiters):
            if fut.done():
                continue
            if wname is not None and wname != name:
                continue
            try:
                if match(data):
                    fut.set_result(data)
            except Exception:
                pass

    async def _reader(self) -> None:
        backoff = 0.5
        while True:
            try:
                reader, _ = await asyncio.open_unix_connection(socket_path())
                backoff = 0.5
                buf = b""
                while True:
                    chunk = await reader.readline()
                    if not chunk:
                        break
                    line = (buf + chunk).decode(errors="replace").strip()
                    buf = b""
                    if not line or ">>" not in line:
                        continue
                    name, data = line.split(">>", 1)
                    self._feed(name.strip(), data.strip())
            except (OSError, ConnectionError):
                pass
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 5.0)


_bus: EventBus | None = None


def get_bus() -> EventBus:
    global _bus
    if _bus is None:
        _bus = EventBus()
    return _bus
