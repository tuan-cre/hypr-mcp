# hypr-mcp

MCP server for Hyprland desktop automation — screenshots, input, window management, OCR.

Rewrite of `alderban107/hyprland-mcp` with dual-version backend support:

- `0.55+`: `hl.dsp.*` Lua dispatch
- pre-0.55: legacy bare-word dispatch (auto-detected via `hyprctl version`, override with `HYPR_MCP_BACKEND=lua|legacy`)

## Run

```bash
pipx install -e .
hypr-mcp
```

## Layout

```
src/hypr_mcp/
  server.py        # FastMCP wiring only
  config.py        # tunables (env: HYPR_MCP_MAX_WIDTH, HYPR_MCP_JPEG_QUALITY, ...)
  errors.py
  backend/         # protocol.py, common.py, legacy.py, lua.py, detect.py
  core/            # proc.py, geometry.py, grim.py, images.py, input.py, ocr.py, clipboard.py
  tools/           # desktop.py, vision.py (tool definitions)
tests/             # pure unit tests (no Hyprland needed)
```
