# hypr-mcp

Let MCP clients drive Hyprland: screenshots, mouse, keyboard, windows,
workspaces, clipboard, launching apps, OCR.

Needs Hyprland 0.55 or newer. Older versions get a clear error instead of
weird behavior. Works with OpenCode, Claude Code, anything speaking MCP.

## Needs

Hyprland, Python 3.10+, pipx, plus (Arch names, adapt to your distro):

| Tool | For |
| --- | --- |
| `grim` | screenshots, OCR |
| `ydotool` (+ `ydotoold` running) | clicking, scroll, drag |
| `wtype` | typing, single keys |
| `wl-clipboard` | clipboard, pasting |
| `tesseract` + `tesseract-data-eng` | finding text on screen |

No `wtype`? `paste_text` (clipboard + ctrl+v) covers most typing.
No `tesseract`? Models with vision just look at screenshots directly.

## Install

```bash
curl -sSL https://raw.githubusercontent.com/tuan-cre/hypr-mcp/main/install.sh | bash
```

That handles system deps, `pipx install`, and Claude Code registration.
For OpenCode, add to `~/.config/opencode/opencode.jsonc`:

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

Or manually: `pipx install git+https://github.com/tuan-cre/hypr-mcp.git`

## Tools (31)

Seeing — `screenshot`, `screenshot_save`, `find_text_on_screen`,
`click_text`, `wait_text`.

Mouse — `mouse_move`, `mouse_click`, `mouse_scroll`, `mouse_drag`.

Keyboard — `type_text`, `key_press`, `paste_text`.

Windows — `list_windows`, `get_active_window`, `focus_window`,
`close_window`, `move_window`, `resize_window`, `toggle_fullscreen`,
`toggle_floating`.

Workspaces — `list_workspaces`, `get_active_workspace`,
`switch_workspace`, `toggle_special`, `move_to_special`.

Misc — `list_monitors`, `get_cursor_position`, `clipboard_read`,
`clipboard_write`, `launch_app`, `wait_window`.

Actions confirm themselves where possible (launch/focus/close wait for the
real event, not a sleep). No force-kill, no shell in `launch_app`,
clipboard reads are capped.

## Config

Env vars, all optional: `HYPR_MCP_MAX_WIDTH` (1440),
`HYPR_MCP_JPEG_QUALITY` (75), `HYPR_MCP_OCR_MIN_CONF` (30),
`HYPR_MCP_EVENT_TIMEOUT` (10s), `HYPR_MCP_LAUNCH_TIMEOUT` (30s).

## License

MIT
