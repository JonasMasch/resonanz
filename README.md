# Resonanz

Ein Innenraum, elf Mal weitergereicht. Scrollen bewegt die Kette.

## Aufbau

```
resonanz/
├── source.webp      Ausgangsfoto (1456 × 816)
├── decay.py         erzeugt die Bildkette
├── index.html       die Website
├── style.css
├── app.js
└── img/
    ├── 00.webp …    11 Fassungen, 00 = unverändert
    ├── manifest.json  Stufen samt Messwerten
    └── stufen.js      dasselbe als JS, damit file:// funktioniert
```

## Bildkette neu erzeugen

```bash
python3 -m venv .venv
.venv/bin/python -m pip install Pillow numpy
.venv/bin/python decay.py
```

Optionen: `--input`, `--outdir`, `--steps`, `--max-width`, `--quality`, `--seed`.
Der Lauf ist bei gleichem Seed reproduzierbar.

Jede Stufe rechnet auf dem Ergebnis der vorherigen und wendet fünf Operationen an:
Farbdrift (Hue-Rotation, Sättigungs- und Kontrastverlust, kühler Stich),
Blockversatz einzelner Kacheln, weiche sinusförmige Verschiebung, Gaußsche
Unschärfe, Filmkorn. Die Stärke wächst von 0,55 auf 1,0.

Das Skript druckt zwei Abstände (mittlere Abweichung pro Farbkanal, 0–255):

| Stufe | zur vorherigen | zum Original |
|------:|---------------:|-------------:|
| 1     | 12,43          | 12,43        |
| 5     | 8,61           | 21,12        |
| 10    | 8,16           | 31,15        |

Der Schritt bleibt klein, der Weg wird lang.

## Website ansehen

`index.html` im Browser öffnen — die Seite braucht keinen Server. Alternativ:

```bash
python3 -m http.server 8777
```

Die elf Fassungen liegen übereinander; die Scrollposition bestimmt, welche
sichtbar ist und wie weit die nächste schon eingeblendet ist (smoothstep, damit
jede Fassung einen Moment steht). Bewusst nicht immersiv: kein Vollbild, das
Bild sitzt in einem sichtbaren Rahmen mit Kopf- und Fußleiste, oben läuft ein
dünner Fortschrittsbalken, unten eine Skala der elf Stufen.
