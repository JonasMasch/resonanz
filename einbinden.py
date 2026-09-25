#!/usr/bin/env python3
"""
Resonanz - gelieferte Bilder in die Website einbinden.

Nimmt einen Ordner mit den erzeugten Fassungen, bringt sie auf ein
einheitliches Format und schreibt sie als 01.webp … 10.webp nach img/,
zusammen mit manifest.json und stufen.js. Stufe 00 ist immer das Original.

Die Bilder werden nach Dateinamen sortiert - also so benennen, dass die
Reihenfolge stimmt (01, 02, … oder a, b, c).

    .venv/bin/python einbinden.py ~/Downloads/resonanz-bilder

Das Skript prüft mit, ob die Kette trägt: Es meldet abweichende
Seitenverhältnisse und Stufen, die zu weit von ihrer Vorgängerin
entfernt sind - das wäre im Überblenden als Sprung zu sehen.
"""

import argparse
import json
import shutil
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ENDUNGEN = {".webp", ".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp"}


def laden(pfad, groesse):
    """Bild oeffnen und auf die Referenzgroesse bringen (mittig beschneiden)."""
    im = Image.open(pfad).convert("RGB")
    zb, zh = groesse
    if im.size != groesse:
        # auf Zielhoehe/-breite skalieren, Ueberstand mittig abschneiden
        faktor = max(zb / im.width, zh / im.height)
        neu = (max(zb, round(im.width * faktor)), max(zh, round(im.height * faktor)))
        im = im.resize(neu, Image.LANCZOS)
        links = (im.width - zb) // 2
        oben = (im.height - zh) // 2
        im = im.crop((links, oben, links + zb, oben + zh))
    return im


def abstand(a, b):
    """Mittlere Abweichung pro Farbkanal in Stufen von 0 bis 255."""
    return float(np.abs(a.astype(np.float32) - b.astype(np.float32)).mean())


def main():
    p = argparse.ArgumentParser(description="Resonanz - Bilder einbinden")
    p.add_argument("ordner", help="Ordner mit den gelieferten Fassungen")
    p.add_argument("--original", default="source.webp", help="Stufe 00")
    p.add_argument("--outdir", default="img", help="Zielordner")
    p.add_argument("--max-width", type=int, default=1600, help="Breite deckeln")
    p.add_argument("--quality", type=int, default=84)
    args = p.parse_args()

    quelle = Path(args.ordner)
    if not quelle.is_dir():
        sys.exit(f"Kein Ordner: {quelle}")

    orig_pfad = Path(args.original).resolve()
    dateien = sorted(f for f in quelle.iterdir()
                     if f.suffix.lower() in ENDUNGEN and not f.name.startswith(".")
                     and f.resolve() != orig_pfad)
    if not dateien:
        sys.exit(f"Keine Bilder in {quelle}")

    # Referenzformat ist die erste Fassung, nicht das Original: sonst wuerde
    # eine abweichend grosse Vorlage die ganze Kette hoch- oder runterrechnen.
    referenz = Image.open(dateien[0])
    groesse = referenz.size
    if groesse[0] > args.max_width:
        groesse = (args.max_width, round(groesse[1] * args.max_width / groesse[0]))

    original = laden(args.original, groesse)
    print(f"Original: {Path(args.original).name}  →  Format der Kette: "
          f"{groesse[0]}×{groesse[1]}")
    print(f"Gefunden: {len(dateien)} Bilder in {quelle}\n")

    out = Path(args.outdir)
    out.mkdir(parents=True, exist_ok=True)

    # Stufe 00 - das Original
    original.save(out / "00.webp", "WEBP", quality=args.quality, method=6)
    vorher = np.asarray(original)
    erstes = vorher.copy()

    manifest = [{"stufe": 0, "datei": "00.webp", "herkunft": Path(args.original).name,
                 "abstand_zum_vorherigen": 0.0, "abstand_zum_original": 0.0}]

    print(f"{'Stufe':>5}  {'Datei':<9} {'d(vorher)':>10} {'d(Original)':>12}  Herkunft")
    print("-" * 68)
    print(f"{0:>5}  {'00.webp':<9} {0.0:>10.2f} {0.0:>12.2f}  {Path(args.original).name}")

    warnungen = []
    for i, f in enumerate(dateien, start=1):
        roh = Image.open(f)
        if abs(roh.width / roh.height - groesse[0] / groesse[1]) > 0.02:
            warnungen.append(f"{f.name}: Seitenverhältnis weicht ab "
                             f"({roh.width}×{roh.height}) — wird mittig beschnitten")

        im = laden(f, groesse)
        ziel = out / f"{i:02d}.webp"
        im.save(ziel, "WEBP", quality=args.quality, method=6)

        arr = np.asarray(im)
        d_v, d_o = abstand(arr, vorher), abstand(arr, erstes)
        if d_v > 28:
            warnungen.append(f"Stufe {i:02d}: großer Sprung zur Vorgängerin ({d_v:.1f}) — "
                             f"im Überblenden vermutlich als Ruck sichtbar")

        manifest.append({"stufe": i, "datei": ziel.name, "herkunft": f.name,
                         "abstand_zum_vorherigen": round(d_v, 2),
                         "abstand_zum_original": round(d_o, 2)})
        print(f"{i:>5}  {ziel.name:<9} {d_v:>10.2f} {d_o:>12.2f}  {f.name}")
        vorher = arr

    # ueberzaehlige Fassungen einer frueheren, laengeren Kette entfernen
    for alt in out.glob("[0-9][0-9].webp"):
        if int(alt.stem) > len(dateien):
            alt.unlink()
            print(f"      entfernt: {alt.name} (aus einer früheren Kette)")

    daten = {"quelle": Path(args.original).name,
             "ordner": out.as_posix(),
             "breite": groesse[0], "hoehe": groesse[1],
             "stufen": manifest}
    (out / "manifest.json").write_text(
        json.dumps(daten, indent=2, ensure_ascii=False), encoding="utf-8")
    (out / "stufen.js").write_text(
        "// automatisch erzeugt von einbinden.py - nicht von Hand ändern\n"
        "window.RESONANZ = " + json.dumps(daten, indent=2, ensure_ascii=False) + ";\n",
        encoding="utf-8")

    print(f"\n{len(dateien) + 1} Fassungen in {out}/ — die Website nutzt sie sofort.")
    if warnungen:
        print("\nHinweise:")
        for warnung in warnungen:
            print(f"  · {warnung}")


if __name__ == "__main__":
    main()
