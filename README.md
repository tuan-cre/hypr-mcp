# hypr-mcp

MCP server for Hyprland desktop automation — screenshots, mouse/keyboard input,
window management, workspaces, clipboard, app launching, and OCR.

Built for Hyprland **>= 0.55** (Lua `hl.dsp.*` dispatch). Older versions fail
fast with a clear error instead of silently mis-dispatching. Works with
[OpenCode](https://opencode.ai), Claude Code, and any MCP client.

## Requirements

- Hyprland >= 0.55, Python 3.10+, `pipx`
- System tools (Arch names — adapt to your distro):

| Tool | Needed for |
| --- | --- |
| `hyprctl` (Hyprland itself) | everything |
| `grim` | screenshots, OCR |
| `ydotool` (+ `ydotoold` running) | mouse click / scroll / drag |
| `wtype` | `type_text`, single-key presses (games, terminals, password fields) |
| `wl-clipboard` | clipboard, `paste_text` |
| `tesseract` + `tesseract-data-eng` | OCR tools (`find_text_on_screen`, `click_text`) |

Typing works without `wtype` via `paste_text` (clipboard + ctrl+v).
Reading works without `tesseract` if your model has vision (it looks at
screenshots directly) — text-only models need it.

## Install

```bash
curl -sSL https://raw.githubusercontent.com/tuan-cre/hypr-mcp/main/install.sh | bash
```

This installs system deps (pacman/apt/dnf), installs `hypr-mcp` via pipx,
and registers it with Claude Code if present. For OpenCode, add to
`~/.config/opencode/opencode.jsonc`:

```jsonc
{
  "mcp": {
    "servers": {
      "hypr": {
        "type": "local",
        "command": ["hypr-mcp"],
      },
    },
  },
}
```

Manual install:

```bash
pipx install git+https://github.com/tuan-cre/hypr-mcp.git
```

Verify: `opencode2 mcp list` should show `✓ hypr connected`.

## Tools (29)

Screenshot & OCR — `screenshot` (inline JPEG + absolute-coordinate mapping),
`screenshot_save` (full-res PNG to disk, zero tokens), `find_text_on_screen`
(OCR → screen coords for `mouse_click`), `click_text` (find + click in one call).

Mouse — `mouse_move` (pixel-accurate via `hl.dsp.cursor.move`),
`mouse_click` (optional focus-first `window`), `mouse_scroll`, `mouse_drag`.

Keyboard — `type_text` (`wtype`), `key_press` (`"ctrl+c"`, `"Return"`, ...),
`paste_text` (clipboard + ctrl+v — the reliable path for unicode/long text).

Windows — `list_windows`, `get_active_window`, `focus_window`,
`close_window` (WM_CLOSE, apps may prompt), `move_window`, `resize_window`,
`toggle_fullscreen(mode, action)`, `toggle_floating(target, action)`
(`action` = `set`/`unset`/`toggle`).

Workspaces — `list_workspaces`, `get_active_workspace`, `switch_workspace`,
`toggle_special(name)`, `move_to_special(name)` (scratchpad).

Monitors — `list_monitors`, `get_cursor_position` (always absolute pixels).

Clipboard — `clipboard_read(max_chars=4000)`, `clipboard_write`.

Apps — `launch_app` (detached via `exec_raw` — no shell, binary + args only).

## Configuration

Env tunables: `HYPR_MCP_MAX_WIDTH` (default 1440), `HYPR_MCP_JPEG_QUALITY`
(default 75), `HYPR_MCP_OCR_MIN_CONF` (30), `HYPR_MCP_FOCUS_SETTLE` (0.3s),
`HYPR_MCP_CLICK_SETTLE` (0.2s).

## How it works

Every `screenshot` returns a coordinate mapping (`screen = image * k + origin`)
so the model never uses raw image pixels on multi-monitor layouts.
OCR auto-scopes to the active window and inverts dark themes before Tesseract.
Mouse positioning uses Hyprland's native `cursor.move` (no acceleration drift);
`ydotool` handles button events only.

## Layout

```
src/hypr_mcp/
  server.py   # MCPServer wiring only
  config.py   # env tunables
  backend/    # hyprctl.py — all hl.dsp.* strings + >=0.55 version gate
  core/       # proc, geometry, grim, images, input, ocr, clipboard
  tools/      # desktop.py, vision.py
```

## Safety

- No filesystem access — screen + input only.
- `close_window` sends WM_CLOSE (save dialogs work); no force-kill tool.
- `launch_app` uses `exec_raw`: no shell expansion, no pipes.
- `clipboard_read` is length-capped.

## License

MIT
