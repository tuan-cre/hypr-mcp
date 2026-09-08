"""Async subprocess helper. Single place for all binary calls."""

import asyncio

from ..errors import HyprMCPError


async def run(*cmd: str, input_bytes: bytes | None = None) -> bytes:
    """Run a command, return stdout. Raise HyprMCPError on non-zero exit."""
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdin=asyncio.subprocess.PIPE if input_bytes is not None else None,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate(input=input_bytes)
    if proc.returncode != 0:
        raise HyprMCPError(f"{' '.join(cmd)} failed: {stderr.decode().strip()}")
    return stdout
