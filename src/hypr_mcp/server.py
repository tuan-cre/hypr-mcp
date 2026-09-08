"""FastMCP wiring only. No hyprctl strings here — see backend/."""

from mcp.server.fastmcp import FastMCP

from .backend import require_backend
from .config import Settings
from .tools import desktop, vision


def create_server(settings: Settings | None = None) -> FastMCP:
    settings = settings or Settings.from_env()
    mcp = FastMCP(
        "hyprland",
        instructions=(
            "Desktop automation for Hyprland (Wayland). Screenshots, mouse/keyboard, "
            "window management, clipboard, app launching. "
            "Coordinates are always absolute screen pixels; never use raw image pixels."
        ),
    )
    backend: list = [None]

    async def get_backend():
        if backend[0] is None:
            backend[0] = await require_backend(settings)
        return backend[0]

    desktop.register(mcp, get_backend, settings)
    vision.register(mcp, get_backend, settings)
    return mcp


def main() -> None:
    create_server().run(transport="stdio")


if __name__ == "__main__":
    main()
