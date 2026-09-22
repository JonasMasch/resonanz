#!/usr/bin/env python3
"""
Resonanz - Bildkette eines verklingenden Raums.

Erzeugt aus einem Eingabebild eine Kette von N Versionen. Jede Version
entsteht aus der VORHERIGEN (kumulativ), nicht aus dem Original. Pro Schritt
wird nur wenig verändert; die Summe der Schritte führt weit vom Original weg
- wie ein Echo, das mit jeder Reflexion etwas von sich verliert.

Pro Schritt werden fünf Operationen angewandt, alle mit einer Stärke, die
über die Kette leicht anwächst (ramp):
  1. Farbdrift    - Hue-Rotation, Sättigungsverlust, Kontrastabfall, Farbstich
  2. Blockversatz - einzelne Kachelblöcke rutschen um wenige Pixel
  3. Wellenwarp   - weiche sinusförmige Verschiebung des ganzen Bildes
  4. Unschärfe   - Gaußscher Weichzeichner, kleiner Radius
  5. Rauschen     - Film-artiges Korn, überwiegend luminanzbasiert

Aufruf:
    .venv/bin/python decay.py
    .venv/bin/python decay.py --input source.webp --steps 10 --seed 7
"""

import argparse
import json
import math
import shutil
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter


# --------------------------------------------------------------------------
# Hilfsfunktionen
# --------------------------------------------------------------------------

def ramp(t: float) -> float:
    """Stärkefaktor eines Schritts. t läuft von ~0 (Anfang) bis 1 (Ende).

    Beginnt bei 0.55 und wächst auf 1.0 - die spaeten Schritte greifen also
    etwas kräftiger zu als die fruehen, bleiben aber einzeln immer klein.
    """
    return 0.55 + 0.45 * t


def hue_rotate(arr: np.ndarray, degrees: float) -> np.ndarray:
    """Farbtondrehung über die klassische YIQ-Rotationsmatrix."""
    a = math.radians(degrees)
    c, s = math.cos(a), math.sin(a)
    m = np.array([
        [0.213 + c * 0.787 - s * 0.213, 0.715 - c * 0.715 - s * 0.715, 0.072 - c * 0.072 + s * 0.928],
        [0.213 - c * 0.213 + s * 0.143, 0.715 + c * 0.285 + s * 0.140, 0.072 - c * 0.072 - s * 0.283],
        [0.213 - c * 0.213 - s * 0.787, 0.715 - c * 0.715 + s * 0.715, 0.072 + c * 0.928 + s * 0.072],
    ], dtype=np.float32)
    return arr @ m.T


def luminance(arr: np.ndarray) -> np.ndarray:
    """Helligkeitskanal (Rec. 709), Form (h, w, 1)."""
    return (arr @ np.array([0.2126, 0.7152, 0.0722], dtype=np.float32))[..., None]


def sample_bilinear(arr: np.ndarray, src_x: np.ndarray, src_y: np.ndarray) -> np.ndarray:
    """Bilineares Abtasten an beliebigen Gleitkomma-Koordinaten."""
    h, w = arr.shape[:2]
    x = np.clip(src_x, 0, w - 1.001)
    y = np.clip(src_y, 0, h - 1.001)
    x0 = np.floor(x).astype(np.int32)
    y0 = np.floor(y).astype(np.int32)
    x1, y1 = x0 + 1, y0 + 1
    fx = (x - x0)[..., None]
    fy = (y - y0)[..., None]
    top = arr[y0, x0] * (1 - fx) + arr[y0, x1] * fx
    bot = arr[y1, x0] * (1 - fx) + arr[y1, x1] * fx
    return top * (1 - fy) + bot * fy


# --------------------------------------------------------------------------
# Die fünf Operationen
# --------------------------------------------------------------------------

def op_farbdrift(arr, s, rng):
    """Farbton dreht langsam weg, Sättigung und Kontrast fallen ab,
    das Bild legt sich auf einen kühlen Erinnerungston."""
    arr = hue_rotate(arr, degrees=-2.6 * s)

    lum = luminance(arr)
    arr = lum + (arr - lum) * (1.0 - 0.055 * s)          # Sättigung fällt

    mid = 0.5
    arr = mid + (arr - mid) * (1.0 - 0.022 * s)          # Kontrast fällt

    tint = np.array([0.455, 0.470, 0.510], dtype=np.float32)  # kühles Grau
    arr = arr * (1 - 0.018 * s) + tint * (0.018 * s)
    return arr


def op_blockversatz(arr, s, rng, cols=18, rows=10, anteil=0.30):
    """Ein Teil der Kachelblöcke rutscht um wenige Pixel - das Bild
    erinnert sich stellenweise leicht falsch."""
    h, w = arr.shape[:2]
    out = arr.copy()
    max_shift = 1.0 + 4.0 * s
    bw, bh = w / cols, h / rows

    for cy in range(rows):
        for cx in range(cols):
            if rng.random() > anteil:
                continue
            x0, x1 = int(cx * bw), int((cx + 1) * bw)
            y0, y1 = int(cy * bh), int((cy + 1) * bh)
            dx = int(round(rng.uniform(-max_shift, max_shift)))
            dy = int(round(rng.uniform(-max_shift, max_shift) * 0.6))
            sx0, sx1 = np.clip([x0 + dx, x1 + dx], 0, w)
            sy0, sy1 = np.clip([y0 + dy, y1 + dy], 0, h)
            bw_i, bh_i = sx1 - sx0, sy1 - sy0
            if bw_i < 2 or bh_i < 2:
                continue
            block = arr[sy0:sy1, sx0:sx1]

            # weiche Kanten, damit keine harten Schnittlinien entstehen
            fx = np.minimum(np.arange(bw_i), np.arange(bw_i)[::-1]) / max(bw_i * 0.12, 1)
            fy = np.minimum(np.arange(bh_i), np.arange(bh_i)[::-1]) / max(bh_i * 0.12, 1)
            maske = np.clip(fy, 0, 1)[:, None] * np.clip(fx, 0, 1)[None, :]
            maske = maske[..., None] * 0.85

            ziel = out[y0:y0 + bh_i, x0:x0 + bw_i]
            out[y0:y0 + bh_i, x0:x0 + bw_i] = ziel * (1 - maske) + block * maske
    return out


def op_wellenwarp(arr, s, rng):
    """Weiche, großflächige Verschiebung - der Raum atmet aus der Form."""
    h, w = arr.shape[:2]
    yy, xx = np.meshgrid(np.arange(h, dtype=np.float32),
                         np.arange(w, dtype=np.float32), indexing="ij")

    amp_x = 0.8 + 2.6 * s
    amp_y = 0.5 + 1.7 * s
    lam_x = rng.uniform(h * 0.35, h * 0.9)
    lam_y = rng.uniform(w * 0.35, w * 0.9)
    ph_x = rng.uniform(0, 2 * math.pi)
    ph_y = rng.uniform(0, 2 * math.pi)

    dx = amp_x * np.sin(2 * math.pi * yy / lam_x + ph_x)
    dy = amp_y * np.sin(2 * math.pi * xx / lam_y + ph_y)

    # zusätzlich ein Hauch Zoom aus der Bildmitte heraus
    zoom = 1.0 + 0.0018 * s
    cx, cy = w / 2, h / 2
    return sample_bilinear(arr, cx + (xx + dx - cx) / zoom, cy + (yy + dy - cy) / zoom)


def op_unschaerfe(arr, s, rng):
    """Kleiner Gaußscher Radius - über die Kette summiert er sich."""
    radius = 0.30 + 0.60 * s
    img = Image.fromarray(np.clip(arr * 255, 0, 255).astype(np.uint8))
    img = img.filter(ImageFilter.GaussianBlur(radius=radius))
    return np.asarray(img, dtype=np.float32) / 255.0


def op_rauschen(arr, s, rng):
    """Korn: überwiegend Helligkeitsrauschen, ein Drittel Farbrauschen."""
    h, w = arr.shape[:2]
    sigma = (1.0 + 4.6 * s) / 255.0
    mono = rng.normal(0.0, sigma, size=(h, w, 1)).astype(np.float32)
    chroma = rng.normal(0.0, sigma, size=(h, w, 3)).astype(np.float32)
    return arr + mono * 0.7 + chroma * 0.3


OPERATIONEN = [
    ("farbdrift", op_farbdrift),
    ("blockversatz", op_blockversatz),
    ("wellenwarp", op_wellenwarp),
    ("unschaerfe", op_unschaerfe),
    ("rauschen", op_rauschen),
]


def schritt(arr: np.ndarray, s: float, rng) -> np.ndarray:
    for _, op in OPERATIONEN:
        arr = op(arr, s, rng)
    return np.clip(arr, 0.0, 1.0)


# --------------------------------------------------------------------------
# Hauptlauf
# --------------------------------------------------------------------------

def main():
    p = argparse.ArgumentParser(description="Resonanz - Bildkette erzeugen")
    p.add_argument("--input", default="source.webp", help="Ausgangsfoto")
    p.add_argument("--outdir", default="img", help="Zielordner")
    p.add_argument("--steps", type=int, default=10, help="Anzahl der Versionen")
    p.add_argument("--max-width", type=int, default=1600, help="Breite deckeln")
    p.add_argument("--quality", type=int, default=84, help="WebP-Qualitaet")
    p.add_argument("--seed", type=int, default=7, help="Zufallssaat (reproduzierbar)")
    args = p.parse_args()

    src = Path(args.input)
    out = Path(args.outdir)
    out.mkdir(parents=True, exist_ok=True)

    img = Image.open(src).convert("RGB")
    if img.width > args.max_width:
        hoehe = round(img.height * args.max_width / img.width)
        img = img.resize((args.max_width, hoehe), Image.LANCZOS)
    print(f"Quelle: {src}  {img.width}x{img.height}")

    # Stufe 0 - das unveränderte Original, nur fürs Web aufbereitet
    ziel0 = out / "00.webp"
    img.save(ziel0, "WEBP", quality=args.quality, method=6)
    arr = np.asarray(img, dtype=np.float32) / 255.0
    vorher = arr.copy()
    original = arr.copy()

    manifest = [{
        "stufe": 0,
        "datei": ziel0.name,
        "staerke": 0.0,
        "abstand_zum_vorherigen": 0.0,
        "abstand_zum_original": 0.0,
    }]

    print(f"\n{'Stufe':>5}  {'Datei':<9} {'Stärke':>8} {'d(vorher)':>10} {'d(Original)':>12}")
    print("-" * 50)
    print(f"{0:>5}  {'00.webp':<9} {0.0:>8.2f} {0.0:>10.2f} {0.0:>12.2f}")

    for i in range(1, args.steps + 1):
        t = i / args.steps
        s = ramp(t)
        rng = np.random.default_rng(args.seed + i * 1009)  # pro Stufe fest

        arr = schritt(arr, s, rng)

        datei = out / f"{i:02d}.webp"
        Image.fromarray((arr * 255 + 0.5).astype(np.uint8)).save(
            datei, "WEBP", quality=args.quality, method=6)

        d_vorher = float(np.abs(arr - vorher).mean() * 255)
        d_orig = float(np.abs(arr - original).mean() * 255)
        manifest.append({
            "stufe": i,
            "datei": datei.name,
            "staerke": round(s, 3),
            "abstand_zum_vorherigen": round(d_vorher, 2),
            "abstand_zum_original": round(d_orig, 2),
        })
        print(f"{i:>5}  {datei.name:<9} {s:>8.2f} {d_vorher:>10.2f} {d_orig:>12.2f}")
        vorher = arr.copy()

    daten = {"quelle": src.name, "stufen": manifest}
    (out / "manifest.json").write_text(
        json.dumps(daten, indent=2, ensure_ascii=False), encoding="utf-8")

    # Zusätzlich als JS-Datei, damit die Website auch ohne Server (file://)
    # an die Stufendaten kommt - fetch() wäre dort durch CORS blockiert.
    (out / "stufen.js").write_text(
        "// automatisch erzeugt von decay.py - nicht von Hand ändern\n"
        "window.RESONANZ = " + json.dumps(daten, indent=2, ensure_ascii=False) + ";\n",
        encoding="utf-8")

    print(f"\n{args.steps + 1} Bilder + manifest.json + stufen.js in {out}/")
    print("d = mittlere Abweichung pro Farbkanal in 0-255-Stufen.")


if __name__ == "__main__":
    main()
