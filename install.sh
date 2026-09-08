#!/usr/bin/env bash
# hypr-mcp installer.
# Usage: curl -sSL https://raw.githubusercontent.com/tuan-cre/hypr-mcp/main/install.sh | bash
set -euo pipefail

REPO="https://github.com/tuan-cre/hypr-mcp.git"
GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BOLD='\033[1m'; NC='\033[0m'
info() { echo -e "${GREEN}[✓]${NC} $1"; }
warn() { echo -e "${YELLOW}[!]${NC} $1"; }

echo -e "${BOLD}hypr-mcp installer${NC}"

# ── Hyprland + version gate ──────────────────────────────────────────
if ! command -v hyprctl &>/dev/null; then
    echo "hyprctl not found — this MCP server requires Hyprland >= 0.55."
    exit 1
fi
VER=$(hyprctl version 2>/dev/null | head -1)
info "Found: $VER"

# ── Package manager ──────────────────────────────────────────────────
PM_INSTALL=""
if command -v pacman &>/dev/null; then
    PM_INSTALL="sudo pacman -S --needed --noconfirm"
elif command -v apt-get &>/dev/null; then
    PM_INSTALL="sudo apt-get install -y"
elif command -v dnf &>/dev/null; then
    PM_INSTALL="sudo dnf install -y"
fi

pkg_for() {
    case "$1" in
        wl-copy|wl-paste) echo "wl-clipboard" ;;
        tesseract) [ "${PM_INSTALL%% *}" = "sudo" ] && echo "tesseract tesseract-data-eng" || echo "tesseract" ;;
        *) echo "$1" ;;
    esac
}

MISSING=()
for tool in grim ydotool wtype wl-copy tesseract; do
    command -v "$tool" &>/dev/null || MISSING+=("$tool")
done

if [ ${#MISSING[@]} -gt 0 ]; then
    warn "Missing: ${MISSING[*]}"
    if [ -n "$PM_INSTALL" ]; then
        read -rp "  Install them now? [Y/n] " ans
        ans="${ans:-y}"
        if [[ "$ans" =~ ^[Yy]$ ]]; then
            # shellcheck disable=SC2086
            $PM_INSTALL $(for t in "${MISSING[@]}"; do pkg_for "$t"; done | tr ' ' '\n' | sort -u | tr '\n' ' ')
            info "System deps installed (start ydotoold separately if needed)"
        fi
    else
        echo "  Install manually: grim ydotool wtype wl-clipboard tesseract"
    fi
else
    info "All system tools found"
fi

# ── pipx install ─────────────────────────────────────────────────────
command -v pipx &>/dev/null || { echo "pipx not found — install it first."; exit 1; }
export PATH="$HOME/.local/bin:$PATH"
if pipx list 2>/dev/null | grep -q "hypr-mcp"; then
    pipx reinstall hypr-mcp 2>/dev/null || { pipx uninstall hypr-mcp && pipx install "$REPO"; }
    info "hypr-mcp upgraded"
else
    pipx install "$REPO"
    info "hypr-mcp installed"
fi

# ── Register ─────────────────────────────────────────────────────────
if command -v claude &>/dev/null; then
    claude mcp add --transport stdio --scope user hyprland -- hypr-mcp || true
    info "Registered with Claude Code"
fi

echo
info "Done."
echo "  OpenCode: add {\"mcp\": {\"servers\": {\"hypr\": {\"type\": \"local\", \"command\": [\"hypr-mcp\"]}}}} to ~/.config/opencode/opencode.jsonc"
echo "  Verify: opencode2 mcp list"
