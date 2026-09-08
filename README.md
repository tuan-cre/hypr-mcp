# hypr-mcp

MCP server for Hyprland desktop automation — screenshots, input, window management, OCR.

## Requirements

Requires Hyprland >= 0.55 (Lua `hl.dsp.*` dispatch). Older versions fail fast with a clear error.

Base: `hyprctl` (Hyprland itself), `grim`, `ydotool`
(+ `ydotoold` running), `wtype`, `wl-clipboard`, `tesseract` + `tesseract-data-eng`.
One install, works with vision and text-only models alike — no per-model setup.

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
