#!/usr/bin/env bash
# =============================================================================
# run.sh — Hermes Agent dev runner
# Usage: ./run.sh [dashboard|onboarding|desktop|web-dev]
# =============================================================================

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="$ROOT/.venv"
PYTHON="$VENV/bin/python"
HERMES="$VENV/bin/hermes"

# ── Warna ─────────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'

info()    { echo -e "${CYAN}→${NC} $*"; }
ok()      { echo -e "${GREEN}✓${NC} $*"; }
warn()    { echo -e "${YELLOW}⚠${NC}  $*"; }
die()     { echo -e "${RED}✗${NC} $*" >&2; exit 1; }
section() { echo -e "\n${BOLD}$*${NC}"; }

# ── Cek & setup Python env ────────────────────────────────────────────────────
ensure_python_env() {
    section "[ Python environment ]"

    # Cari uv
    UV=""
    for candidate in uv "$HOME/.local/bin/uv" "$HOME/.cargo/bin/uv"; do
        if command -v "$candidate" &>/dev/null 2>&1; then
            UV="$candidate"; break
        fi
    done

    if [ -z "$UV" ]; then
        warn "uv tidak ditemukan, install sekarang..."
        curl -LsSf https://astral.sh/uv/install.sh | sh
        export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
        UV="$HOME/.local/bin/uv"
    fi
    ok "uv: $($UV --version)"

    if [ ! -f "$PYTHON" ]; then
        info "Membuat virtualenv Python 3.11..."
        "$UV" venv "$VENV" --python 3.11
        ok "Virtualenv dibuat: $VENV"
    else
        ok "Virtualenv sudah ada: $VENV"
    fi

    if [ ! -f "$HERMES" ]; then
        info "Install hermes-agent dependencies (ini butuh beberapa menit)..."
        "$UV" pip install --python "$PYTHON" -e "$ROOT/.[all]"
        ok "Dependencies terinstall"
    else
        ok "hermes-agent sudah terinstall"
    fi
}

# ── Cek Node / npm ────────────────────────────────────────────────────────────
ensure_node() {
    if ! command -v node &>/dev/null; then
        die "Node.js tidak ditemukan. Install dari https://nodejs.org (v20+)"
    fi
    if ! command -v npm &>/dev/null; then
        die "npm tidak ditemukan."
    fi
    ok "Node: $(node --version), npm: $(npm --version)"
}

ensure_npm_root() {
    if [ ! -d "$ROOT/node_modules" ]; then
        info "Install npm workspace dependencies..."
        npm install --prefix "$ROOT"
        ok "npm root install selesai"
    else
        ok "node_modules sudah ada"
    fi
}

ensure_npm_workspace_web() {
    if [ ! -x "$ROOT/web/node_modules/.bin/vite" ]; then
        info "Install web workspace dependencies..."
        npm install --workspace web
        ok "web workspace install selesai"
    else
        ok "web workspace dependencies sudah ada"
    fi
}

ensure_npm_workspace_desktop() {
    if [ ! -d "$ROOT/apps/desktop/node_modules" ]; then
        info "Install desktop dependencies..."
        npm install --workspace apps/desktop
        ok "desktop workspace install selesai"
    else
        ok "desktop dependencies sudah ada"
    fi
}

# ── Mode: onboarding (setup wizard) ───────────────────────────────────────────
run_onboarding() {
    section "[ Onboarding / Setup Wizard ]"
    ensure_python_env
    info "Menjalankan hermes setup..."
    echo ""
    exec "$HERMES" setup
}

# ── Mode: dashboard ───────────────────────────────────────────────────────────
run_dashboard() {
    section "[ Web Dashboard ]"
    ensure_python_env

    PORT="${HERMES_DASHBOARD_PORT:-9119}"
    info "Menjalankan dashboard di http://localhost:$PORT ..."
    echo ""
    exec "$HERMES" dashboard --port "$PORT"
}

# ── Mode: web-dev (dashboard dengan hot-reload) ───────────────────────────────
run_web_dev() {
    section "[ Web Dashboard — Dev Mode (hot-reload) ]"
    ensure_python_env
    ensure_node
    ensure_npm_root
    ensure_npm_workspace_web

    # Build web UI jika belum ada
    WEB_DIST="$ROOT/hermes_cli/web_dist"
    if [ ! -d "$WEB_DIST" ] || [ -z "$(ls -A "$WEB_DIST" 2>/dev/null)" ]; then
        info "Build web UI dulu..."
        (cd "$ROOT/web" && npm run build)
    fi

    info "Jalankan backend di port 9119..."
    info "Jalankan Vite dev server di http://localhost:5173 (dengan hot-reload)"
    echo ""

    # Jalankan keduanya bersamaan
    trap 'kill 0' EXIT INT TERM

    "$HERMES" dashboard --port 9119 --no-open &
    BACKEND_PID=$!

    sleep 2  # tunggu backend siap

    (cd "$ROOT/web" && npm run dev) &
    FRONTEND_PID=$!

    echo ""
    ok "Backend  → http://localhost:9119"
    ok "Frontend → http://localhost:5173  (pakai ini untuk dev)"
    echo ""

    wait "$BACKEND_PID" "$FRONTEND_PID"
}

# ── Mode: desktop ─────────────────────────────────────────────────────────────
run_desktop() {
    section "[ Desktop App ]"
    ensure_python_env
    ensure_node
    ensure_npm_root
    ensure_npm_workspace_desktop

    info "Jalankan Electron desktop app (dev mode)..."
    echo ""

    export HERMES_DESKTOP_HERMES_ROOT="$ROOT"
    exec npm run dev --workspace apps/desktop
}

# ── Menu interaktif ───────────────────────────────────────────────────────────
show_menu() {
    echo ""
    echo -e "${BOLD}╔══════════════════════════════════════╗${NC}"
    echo -e "${BOLD}║     Hermes Agent — Dev Runner        ║${NC}"
    echo -e "${BOLD}╚══════════════════════════════════════╝${NC}"
    echo ""
    echo "  1) onboarding   — Setup wizard (pilih provider & API key)"
    echo "  2) dashboard    — Web dashboard (http://localhost:9119)"
    echo "  3) web-dev      — Dashboard + Vite hot-reload (dev)"
    echo "  4) desktop      — Electron desktop app (dev mode)"
    echo ""
    printf "Pilih mode [1-4]: "
    read -r choice
    case "$choice" in
        1|onboarding) run_onboarding ;;
        2|dashboard)  run_dashboard ;;
        3|web-dev)    run_web_dev ;;
        4|desktop)    run_desktop ;;
        *) die "Pilihan tidak valid: $choice" ;;
    esac
}

# ── Entry point ───────────────────────────────────────────────────────────────
cd "$ROOT"

case "${1:-}" in
    onboarding|setup) run_onboarding ;;
    dashboard)        run_dashboard ;;
    web-dev)          run_web_dev ;;
    desktop|gui)      run_desktop ;;
    "")               show_menu ;;
    *) die "Mode tidak dikenal: $1\nUsage: ./run.sh [onboarding|dashboard|web-dev|desktop]" ;;
esac
