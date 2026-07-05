# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Generate the Ankimatter app icon (Observatory theme) for macOS + iOS.

The mark is the app's own signature: the glowing atom from the manifold home
screen (a nucleus + three tilted electron orbits) in electric cyan on deep
space — the same tokens as the desktop/iOS themes (space #07080D, accent
#4CE0FF, violet #8A7CFF). No emoji, no clip-art: it's drawn from primitives and
super-sampled for clean edges, matching the "serious, physics-referential"
house style.

Outputs (idempotent — safe to re-run):
  qt/installer/app/resources/anki.icns              (macOS, via iconutil)
  mobile/SpeedrunApp/Resources/Assets.xcassets/AppIcon.appiconset/  (iOS 1024)

Run:  out/pyenv/bin/python speedrun/make_icon.py   (needs Pillow)
"""

from __future__ import annotations

import json
import math
import os
import random
import subprocess
import tempfile

from PIL import Image, ImageChops, ImageDraw, ImageFilter

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SPACE_INNER = (16, 20, 44)  # subtle violet-blue core glow (~#10142C)
SPACE_OUTER = (7, 8, 13)  # deepest space (#07080D)
CYAN = (76, 224, 255)  # --pg-accent
VIOLET = (138, 124, 255)  # --pg-accent-2
WHITE = (233, 246, 255)

SS = 4  # super-sample factor; render big, downscale for anti-aliasing


def _radial_bg(size: int) -> Image.Image:
    """Smooth radial space gradient, computed small then scaled up."""
    small = 96
    cx = cy = (small - 1) / 2
    maxd = math.hypot(cx, cy)
    img = Image.new("RGB", (small, small))
    px = img.load()
    assert px is not None
    for y in range(small):
        for x in range(small):
            t = (math.hypot(x - cx, y - cy) / maxd) ** 1.25
            t = min(1.0, t)
            px[x, y] = tuple(
                int(SPACE_INNER[i] * (1 - t) + SPACE_OUTER[i] * t) for i in range(3)
            )
    return img.resize((size, size), Image.BICUBIC)


def _add_stars(img: Image.Image, size: int) -> None:
    rnd = random.Random(7)
    d = ImageDraw.Draw(img, "RGBA")
    for _ in range(160):
        x, y = rnd.uniform(0, size), rnd.uniform(0, size)
        r = rnd.uniform(size * 0.0006, size * 0.0022)
        a = rnd.randint(20, 120)
        tint = CYAN if rnd.random() < 0.25 else WHITE
        d.ellipse([x - r, y - r, x + r, y + r], fill=tint + (a,))


def _orbit_layer(
    size: int, angle: float, electron: tuple[int, int, int]
) -> Image.Image:
    """One tilted elliptical orbit with an electron riding on it."""
    layer = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    cx = cy = size / 2
    rx, ry = size * 0.40, size * 0.152
    w = max(2, int(size * 0.0075))
    d.ellipse([cx - rx, cy - ry, cx + rx, cy + ry], outline=CYAN + (255,), width=w)
    # electron at the ellipse's right vertex (rotates with the layer)
    er = size * 0.028
    d.ellipse([cx + rx - er, cy - er, cx + rx + er, cy + er], fill=electron + (255,))
    return layer.rotate(angle, resample=Image.BICUBIC, center=(cx, cy))


def _atom_ink(size: int) -> Image.Image:
    ink = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    for angle, electron in ((0, CYAN), (60, VIOLET), (120, CYAN)):
        ink = Image.alpha_composite(ink, _orbit_layer(size, angle, electron))
    return ink


def _nucleus(size: int) -> Image.Image:
    """Bright cyan-white core with a soft bloom, as its own additive layer."""
    layer = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    cx = cy = size / 2
    core = size * 0.052
    d.ellipse([cx - core, cy - core, cx + core, cy + core], fill=WHITE + (255,))
    inner = size * 0.030
    d.ellipse(
        [cx - inner, cy - inner, cx + inner, cy + inner], fill=(255, 255, 255, 255)
    )
    return layer


def _screen_add(
    base: Image.Image, glow_rgba: Image.Image, scale: float = 1.0
) -> Image.Image:
    """Additively blend an emissive (glow) layer onto an RGB base."""
    glow_rgb = Image.new("RGB", base.size, (0, 0, 0))
    glow_rgb.paste(glow_rgba, (0, 0), glow_rgba)
    if scale != 1.0:
        glow_rgb = glow_rgb.point(lambda v: int(v * scale))
    return ImageChops.add(base, glow_rgb)


def _render_art(size: int) -> Image.Image:
    """The full square icon art (full-bleed), rendered at `size`."""
    big = size * SS
    bg = _radial_bg(big)
    _add_stars(bg, big)

    ink = _atom_ink(big)
    halo = ink.filter(ImageFilter.GaussianBlur(big * 0.016))
    glow = ink.filter(ImageFilter.GaussianBlur(big * 0.006))

    out = _screen_add(bg, halo, 0.85)
    out = _screen_add(out, glow, 1.0)
    out = out.convert("RGBA")
    out = Image.alpha_composite(out, ink)

    nuc = _nucleus(big)
    bloom = nuc.filter(ImageFilter.GaussianBlur(big * 0.045))
    out = _screen_add(out.convert("RGB"), bloom, 1.0).convert("RGBA")
    out = Image.alpha_composite(out, nuc)

    return out.resize((size, size), Image.LANCZOS)


def _squircle_mask(size: int, radius_frac: float = 0.2237) -> Image.Image:
    m = Image.new("L", (size * SS, size * SS), 0)
    d = ImageDraw.Draw(m)
    r = int(size * SS * radius_frac)
    d.rounded_rectangle([0, 0, size * SS - 1, size * SS - 1], radius=r, fill=255)
    return m.resize((size, size), Image.LANCZOS)


def _macos_icon(size: int) -> Image.Image:
    """macOS icons are squircles inset in a transparent canvas (Apple grid:
    ~824/1024 content). Render the art small, pad, mask to a squircle."""
    content = round(size * 0.805)
    art = _render_art(content)
    mask = _squircle_mask(content)
    art.putalpha(mask)
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    off = (size - content) // 2
    canvas.paste(art, (off, off), art)
    return canvas


def build_macos_icns() -> str:
    out_icns = os.path.join(REPO, "qt", "installer", "app", "resources", "anki.icns")
    sizes = [16, 32, 64, 128, 256, 512, 1024]
    with tempfile.TemporaryDirectory() as tmp:
        iconset = os.path.join(tmp, "anki.iconset")
        os.makedirs(iconset)
        for s in sizes:
            img = _macos_icon(s)
            if s <= 512:
                img.save(os.path.join(iconset, f"icon_{s}x{s}.png"))
            if s >= 32:
                half = s // 2
                img.save(os.path.join(iconset, f"icon_{half}x{half}@2x.png"))
        subprocess.run(["iconutil", "-c", "icns", iconset, "-o", out_icns], check=True)
    return out_icns


def build_ios_appicon() -> str:
    appiconset = os.path.join(
        REPO,
        "mobile",
        "SpeedrunApp",
        "Resources",
        "Assets.xcassets",
        "AppIcon.appiconset",
    )
    os.makedirs(appiconset, exist_ok=True)
    # Single 1024 icon (full-bleed; iOS applies the mask). Modern Xcode accepts
    # one "universal" 1024 image for all slots.
    icon = _render_art(1024).convert("RGB")
    icon.save(os.path.join(appiconset, "icon-1024.png"))
    contents = {
        "images": [
            {
                "filename": "icon-1024.png",
                "idiom": "universal",
                "platform": "ios",
                "size": "1024x1024",
            }
        ],
        "info": {"author": "xcode", "version": 1},
    }
    with open(os.path.join(appiconset, "Contents.json"), "w", encoding="utf-8") as f:
        json.dump(contents, f, indent=2)
    return appiconset


def main() -> None:
    icns = build_macos_icns()
    print(f"wrote {os.path.relpath(icns, REPO)}")
    ios = build_ios_appicon()
    print(f"wrote {os.path.relpath(ios, REPO)}/  (icon-1024.png + Contents.json)")
    # Also drop a preview PNG for eyeballing.
    preview = os.path.join(REPO, "out", "speedrun", "icon_preview.png")
    os.makedirs(os.path.dirname(preview), exist_ok=True)
    _render_art(512).convert("RGB").save(preview)
    print(f"preview: {os.path.relpath(preview, REPO)}")


if __name__ == "__main__":
    main()
