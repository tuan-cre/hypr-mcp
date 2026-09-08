---
name: hypr-desktop-driving
description: Drive the Hyprland desktop via hypr-mcp tools. Readiness ladder, OCR query shaping, app navigation, test hygiene. Load before any multi-step GUI task.
---

# Driving the desktop with hypr-mcp

## 1. Readiness ladder — never `sleep` then check

Pick the cheapest signal that actually confirms the state:

1. **Compositor events** (free, instant): `launch_app`, `focus_window`,
   `close_window`, `switch_workspace` already wait on socket2. Trust their
   return value; don't re-check after them.
2. **Window titles** (`wait_window`): page loads, slow startups, dialog
   appearance. Title matching is normalized (case/space/punct-insensitive),
   so `Master Duel` matches `masterduel`. Returns instantly on match.
3. **On-screen text** (`wait_text`, `disappear` flag): in-window state no
   compositor event covers — button flips (`UPDATE`→`PLAY`), page content,
   download completion. Polls OCR every 0.5s.

State checks go through `list_windows` (class, title, geometry, address,
focus flag in one call) — never shell `hyprctl ... | python3` one-liners.

## 2. OCR query shaping

- Query **short distinctive words**: `Master Duel`, not `Yu-Gi-Oh! Master
  Duel` (OCR mangles punctuation and long strings).
- Matching is normalized, but **one fused on-screen token needs a
  single-word query**: visible `hypr-mcp` matches `hypr`, not `hypr mcp`.
- **Stylized buttons are invisible to OCR** (colored CTA buttons, icon+text).
  Fall back to coordinates derived from a *fresh* `screenshot` mapping.
- Disambiguate repeats with `region` / `occurrence` before resorting to
  manual coords.
- **Never reuse cached coordinates**: windows move. Re-derive from the
  latest screenshot's mapping every time.

## 3. App navigation patterns

- **Browser URL bar**: `key_press(ctrl+l)` → `paste_text(url)` →
  `key_press(Return)` → `wait_window(title_contains=...)`. Pasting without
  focusing the omnibox first goes into page content and silently fails.
- **Slow starters** (Steam, Electron/CEF apps): pass an explicit large
  `timeout` to `launch_app` (default 30s). A timeout error with the process
  running means "still starting", not "failed" — follow with `wait_window`.
- **Multi-window apps**: `launch_app` returns on the *first* window (e.g.
  login splash). The main window arrives later — `wait_window` for it.

## 4. Test hygiene

- Verify mechanics against **fast apps only** (`foot`): launch → focus →
  close round-trips take ~0.1s. Never burn slow app launches on testing.
- Close every scratch window you open; leave the user's windows, workspace,
  and focus as you found them.
- Prefer window-scoped screenshots (`window:` selector) over full-desktop.

## 5. Self-update rule

Append findings that clear this bar, edit out ones that rotted:

- Survived live verification (not a one-off fluke).
- Would have saved a future session real turns.
- Portable across machines (machine-specific facts belong in the user's
  AGENTS.md, never here).
