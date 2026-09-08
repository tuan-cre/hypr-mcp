"""wl-copy / wl-paste wrappers."""

from ..errors import require_tool
from .proc import run


async def read() -> str:
    require_tool("wl-paste")
    return (await run("wl-paste", "-n")).decode()


async def write(text: str) -> None:
    require_tool("wl-copy")
    await run("wl-copy", input_bytes=text.encode())
