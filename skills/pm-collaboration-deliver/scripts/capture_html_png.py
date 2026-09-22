#!/usr/bin/env python3
"""Rasterize a local HTML file to PNG with a headless desktop browser.

This is the single rasterization step for all HTML-based visual assets in
pm-collaboration-deliver (flow diagrams, page interaction overviews, and
mobile screen prototypes). It locates an installed Chrome / Edge / Chromium
and captures an exact-size viewport screenshot:

    python3 scripts/capture_html_png.py \
        --html /abs/path/asset.html \
        --png /abs/path/asset.png \
        --width 1600 --height 900 --scale 2

Why not mermaid-cli / rsvg / ImageMagick / sharp: those toolchains are either
heavy (puppeteer downloads a browser), or not installed on most PM machines.
A desktop browser is already present on virtually every macOS / Windows /
Linux workstation, renders CJK fonts and modern CSS correctly, and needs no
network access.

Exit codes: 0 ok, 2 usage / render failure.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

BROWSER_CANDIDATES = [
    # macOS
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
    # Linux / PATH lookup
    "google-chrome",
    "google-chrome-stable",
    "chromium",
    "chromium-browser",
    "microsoft-edge",
    "chrome",
    # Windows (resolved via shutil.which only if on PATH)
    "chrome.exe",
    "msedge.exe",
]


def find_browser(override: str | None = None) -> str | None:
    if override:
        return override if Path(override).exists() or shutil.which(override) else None
    for candidate in BROWSER_CANDIDATES:
        if Path(candidate).exists():
            return candidate
        found = shutil.which(candidate)
        if found:
            return found
    return None


def capture(html_path: Path, png_path: Path, width: int, height: int,
            scale: float, browser: str, background: str = "#ffffff") -> None:
    """Screenshot the file with an exact viewport size.

    The HTML page is expected to size its own body to width x height CSS px.
    We add a settle delay via --virtual-time-budget so webfonts and layout
    finish before the capture.

    Note: desktop Chrome (observed on Chrome 151/macOS) sometimes stays alive
    after writing the screenshot instead of exiting. We therefore poll for a
    stable non-empty PNG and then terminate the browser, rather than waiting
    for a clean exit that may never come.
    """
    import time

    png_path.parent.mkdir(parents=True, exist_ok=True)
    if png_path.exists():
        png_path.unlink()
    with tempfile.TemporaryDirectory(prefix="capture-html-") as profile:
        cmd = [
            browser,
            "--headless",
            "--disable-gpu",
            "--no-first-run",
            "--no-default-browser-check",
            "--hide-scrollbars",
            f"--user-data-dir={profile}",
            f"--window-size={width},{height}",
            f"--force-device-scale-factor={scale:g}",
            f"--default-background-color={background.lstrip('#')}",
            "--virtual-time-budget=4000",
            f"--screenshot={png_path}",
            html_path.resolve().as_uri(),
        ]
        proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        deadline = time.time() + 90
        stable_size = -1
        stable_since = time.time()
        ok = False
        while time.time() < deadline:
            if png_path.is_file():
                size = png_path.stat().st_size
                if size > 0:
                    if size == stable_size and time.time() - stable_since > 1.5:
                        ok = True
                        break
                    if size != stable_size:
                        stable_size = size
                        stable_since = time.time()
            if proc.poll() is not None:
                ok = png_path.is_file() and png_path.stat().st_size > 0
                break
            time.sleep(0.4)
        proc.terminate()
        try:
            proc.wait(timeout=8)
        except subprocess.TimeoutExpired:
            proc.kill()
    if not ok:
        raise RuntimeError("browser did not produce a screenshot within 90s")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--html", required=True, type=Path)
    parser.add_argument("--png", required=True, type=Path)
    parser.add_argument("--width", required=True, type=int, help="viewport width in CSS px")
    parser.add_argument("--height", required=True, type=int, help="viewport height in CSS px")
    parser.add_argument("--scale", type=float, default=2.0,
                        help="device scale factor; 2 gives retina-crisp PNG (default: 2)")
    parser.add_argument("--browser", help="explicit browser binary path")
    parser.add_argument("--background", default="#ffffff")
    args = parser.parse_args()

    if not args.html.is_file():
        print(f"error: html file not found: {args.html}", file=sys.stderr)
        return 2
    browser = find_browser(args.browser)
    if not browser:
        print(
            "error: no Chrome / Edge / Chromium found; install one or pass --browser. "
            "Fallback: keep the SVG/HTML asset, or use the legacy render_wireframe_board.py chain.",
            file=sys.stderr,
        )
        return 2
    try:
        capture(args.html, args.png, args.width, args.height, args.scale,
                browser, args.background)
    except (RuntimeError, subprocess.TimeoutExpired) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({
        "png": str(args.png),
        "browser": browser,
        "css_size": [args.width, args.height],
        "pixel_size": [round(args.width * args.scale), round(args.height * args.scale)],
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
