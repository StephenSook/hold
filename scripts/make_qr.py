"""Render the install QR codes the README shows.

A QR code in a README is a claim that a URL works, and it is the one claim a reader cannot
check by looking. So the URLs live here, in one place, next to the code that draws them, and
the README embeds the output rather than a third-party image service. An external chart API
would put a link on the judge-facing page that we do not control and that can go dark.

Colours are the board and bone tokens, so the codes sit in the page like everything else.
Contrast between the two is 16.89:1, far above the 3:1 a scanner needs.

    uv run --with qrcode --with pillow --with opencv-python-headless --with numpy \
        python scripts/make_qr.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import cv2
import qrcode
from qrcode.constants import ERROR_CORRECT_M

BOARD = "#101010"
BONE = "#f4f1ec"

DOCS = Path(__file__).resolve().parent.parent / "docs" / "install"

TARGETS = {
    # The GitHub Release asset, not a build-service artifact URL. A hosted build artifact has a
    # retention clock measured in days and 404s while the repo, the CI and the deploy all stay
    # green, which is exactly the failure a QR code in a README cannot survive.
    "android-apk": "https://github.com/StephenSook/hold/releases/latest/download/hold.apk",
    "ios-testflight": "https://testflight.apple.com/join/guYBH8xE",
}


def render(name: str, url: str) -> Path:
    code = qrcode.QRCode(
        version=None,
        # Medium recovers about 15 percent, which is what a phone camera needs off a screen at an
        # angle. High would make the modules smaller for no gain at this URL length.
        error_correction=ERROR_CORRECT_M,
        box_size=10,
        border=3,
    )
    code.add_data(url)
    code.make(fit=True)
    # Dark modules on a light ground, which is the way round the format specifies. Drawing it
    # inverted, bone on board, looks better against the page and does not decode: it was tried
    # here first and neither code read back. Scanners are allowed to reject inverted codes and
    # in practice many do.
    image = code.make_image(fill_color=BOARD, back_color=BONE)
    DOCS.mkdir(parents=True, exist_ok=True)
    path = DOCS / f"{name}.png"
    image.save(path)
    return path


def main() -> int:
    if any("PLACEHOLDER" in url for url in TARGETS.values()):
        print("refusing to draw a QR code for a placeholder URL", file=sys.stderr)
        for name, url in TARGETS.items():
            if "PLACEHOLDER" in url:
                print(f"  {name}: {url}", file=sys.stderr)
        return 1
    failures = 0
    for name, url in TARGETS.items():
        path = render(name, url)
        # Read the code back. An unscannable QR looks exactly like a working one, and the first
        # pair drawn here did not decode at all: they were bone on board, and the format wants
        # dark modules on a light ground. Nothing but decoding the output would have caught it.
        decoded, _, _ = cv2.QRCodeDetector().detectAndDecode(cv2.imread(str(path)))
        if decoded != url:
            failures += 1
            print(f"  FAIL {path.name} decoded {decoded!r}, wanted {url!r}", file=sys.stderr)
        else:
            print(f"  {path.relative_to(DOCS.parent.parent)}  scans to {url}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
