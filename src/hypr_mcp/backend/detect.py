"""Backend autodetection. Cached: `hyprctl version` decides Lua vs legacy."""

import asyncio
import functools
import os
import shutil

from ..config import Settings
from . import common
from .legacy import LegacyBackend
from .lua import LuaBackend


def forced_backend() -> str | None:
    v = os.environ.get("HYPR_MCP_BACKEND", "").strip().lower()
    return v if v in ("lua", "legacy") else None


@functools.lru_cache(maxsize=1)
def _cached_is_lua(first_line: str) -> bool:
    return common.is_lua_version(first_line)


async def detect(settings: Settings | None = None):
    forced = forced_backend()
    if forced == "lua":
        return LuaBackend(settings)
    if forced == "legacy":
        return LegacyBackend()
    if shutil.which("hyprctl") is None:
        return LuaBackend(settings)  # default for error paths when hyprctl missing
    proc = await asyncio.create_subprocess_exec(
        "hyprctl", "version",
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    stdout, _ = await proc.communicate()
    first = stdout.decode().splitlines()[0] if stdout else ""
    if _cached_is_lua(first):
        return LuaBackend(settings)
    return LegacyBackend()
