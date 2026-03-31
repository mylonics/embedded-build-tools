#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# Embedded Build Tools — One-line installer for Linux / macOS
#
# Downloads and extracts the correct pre-built release for your platform.
#
# Usage:
#   curl -fsSL https://github.com/mylonics/embedded-build-tools/releases/latest/download/install.sh | bash
#   curl -fsSL .../install.sh | bash -s -- --version v1.0.0 --dest ./my-tools
#
# Options:
#   --version <tag>   GitHub release tag to download (default: latest)
#   --dest <dir>      Destination directory (default: ./embedded-build-tools)
#   --help            Show this help
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

REPO="mylonics/embedded-build-tools"
VERSION="latest"
DEST="embedded-build-tools"

# ── Parse arguments ──────────────────────────────────────────────────────────

while [[ $# -gt 0 ]]; do
    case "$1" in
        --version|-v) VERSION="$2"; shift 2 ;;
        --dest|-d)    DEST="$2"; shift 2 ;;
        --help|-h)
            head -16 "$0" | tail -12
            exit 0
            ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

# ── Detect platform ─────────────────────────────────────────────────────────

detect_platform() {
    local os arch

    case "$(uname -s)" in
        Linux*)  os="linux" ;;
        Darwin*) os="darwin" ;;
        MINGW*|MSYS*|CYGWIN*) os="win32" ;;
        *) echo "Error: Unsupported OS: $(uname -s)" >&2; exit 1 ;;
    esac

    case "$(uname -m)" in
        x86_64|amd64)  arch="x64" ;;
        aarch64|arm64) arch="arm64" ;;
        *) echo "Error: Unsupported architecture: $(uname -m)" >&2; exit 1 ;;
    esac

    echo "${os}-${arch}"
}

PLATFORM="$(detect_platform)"

# ── Determine artifact name & URL ────────────────────────────────────────────

if [[ "$PLATFORM" == win32-* ]]; then
    ARTIFACT="embedded-build-tools-${PLATFORM}.zip"
else
    ARTIFACT="embedded-build-tools-${PLATFORM}.tar.gz"
fi

if [[ "$VERSION" == "latest" ]]; then
    URL="https://github.com/${REPO}/releases/latest/download/${ARTIFACT}"
else
    URL="https://github.com/${REPO}/releases/download/${VERSION}/${ARTIFACT}"
fi

# ── Download ─────────────────────────────────────────────────────────────────

echo "Platform:    ${PLATFORM}"
echo "Version:     ${VERSION}"
echo "Artifact:    ${ARTIFACT}"
echo "Destination: ${DEST}"
echo ""

TMPFILE="$(mktemp)"
trap 'rm -f "$TMPFILE"' EXIT

echo "Downloading ${URL}..."
if command -v curl &>/dev/null; then
    curl -fSL --progress-bar -o "$TMPFILE" "$URL"
elif command -v wget &>/dev/null; then
    wget -q --show-progress -O "$TMPFILE" "$URL"
else
    echo "Error: Neither curl nor wget found. Install one and try again." >&2
    exit 1
fi

# ── Extract ──────────────────────────────────────────────────────────────────

echo "Extracting to ${DEST}..."
mkdir -p "$DEST"

if [[ "$ARTIFACT" == *.zip ]]; then
    unzip -qo "$TMPFILE" -d "$DEST"
else
    tar xzf "$TMPFILE" -C "$DEST"
fi

# ── macOS: remove quarantine ─────────────────────────────────────────────────

if [[ "$(uname -s)" == "Darwin" ]]; then
    echo "Removing macOS quarantine attributes..."
    xattr -cr "$DEST" 2>/dev/null || true
fi

# ── Done ─────────────────────────────────────────────────────────────────────

echo ""
echo "✓ Embedded build tools installed to: ${DEST}"
echo ""
echo "Next steps:"
echo "  cd ${DEST}"
echo "  source env.sh"
echo ""
