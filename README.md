# Resonanz

Zwei Bildketten, beide scrollgesteuert:

- **01 Verklingen** (`index.html`) — ein Wohnraum, fünfundzwanzig Mal durch
  Farbdrift, Versatz und Unschärfe gerechnet.
- **02 Umräumen** (`moebel.html`) — eine Almhütte, neun Mal umgebaut; die
  Fassungen sind extern erzeugt und über `einbinden.py` eingebunden.

## Aufbau

```
resonanz/
├── source.webp      Ausgangsfoto (1456 × 816)
├── decay.py         erzeugt die Bildkette
├── index.html       die Website
├── style.css
├── app.js
├── einbinden.py     bindet extern erzeugte Bilder als Kette ein
├── moebel.html      zweite Seite: die umgebaute Almhütte
├── eigene_Bilder/   Ausgangsmaterial der zweiten Kette
└── img/
    ├── 00.webp …    26 Fassungen der ersten Kette, 00 = unverändert
    ├── manifest.json  Stufen samt Messwerten
    ├── stufen.js      dasselbe als JS, damit file:// funktioniert
    └── moebel/      dieselben drei Dateien für die zweite Kette
```

## Bildkette neu erzeugen

```bash
python3 -m venv .venv
.venv/bin/python -m pip install Pillow numpy
.venv/bin/python decay.py --steps 25
```

Optionen: `--input`, `--outdir`, `--steps`, `--basis`, `--max-width`, `--quality`,
`--seed`. Der Lauf ist bei gleichem Seed reproduzierbar — und die Stärke hängt an
der absoluten Stufennummer, nicht an der Länge der Kette. Eine Kette lässt sich
deshalb verlängern, ohne dass sich die bereits erzeugten Stufen ändern.

Jede Stufe rechnet auf dem Ergebnis der vorherigen und wendet fünf Operationen an:
Farbdrift (Hue-Rotation, Sättigungs- und Kontrastverlust, kühler Stich),
Blockversatz einzelner Kacheln, weiche sinusförmige Verschiebung, Gaußsche
Unschärfe, Filmkorn. Die Stärke wächst bis zur Basisstufe (`--basis`, 10) auf 1,0
und danach nur noch gedämpft gegen 1,3 — ein Echo wird mit der Zeit schwächer,
nicht wilder.

Das Skript druckt zwei Abstände (mittlere Abweichung pro Farbkanal, 0–255):

| Stufe | zur vorherigen | zum Original |
|------:|---------------:|-------------:|
| 1     | 12,43          | 12,43        |
| 5     | 8,61           | 21,12        |
| 10    | 8,16           | 31,15        |
| 17    | 7,25           | 41,05        |
| 25    | 6,62           | 48,67        |

Der Schritt bleibt klein, der Weg wird lang.

## Eigene Bilder statt Rechenkette

Wer die Fassungen anderswo erzeugt (etwa um Möbel verschwinden zu lassen), bindet
sie so ein:

```bash
.venv/bin/python einbinden.py eigene_Bilder \
    --original eigene_Bilder/Raum_orginal.webp --outdir img/moebel
```

Das Skript sortiert nach Dateinamen, nimmt das Original aus der Stufenliste,
bringt alles auf das Format der ersten Fassung,
schreibt `01.webp` aufwärts samt `manifest.json` und `stufen.js` und warnt bei
abweichenden Seitenverhältnissen und bei Stufen, die zu weit von ihrer
Vorgängerin entfernt sind.

## Website ansehen

`index.html` im Browser öffnen — die Seite braucht keinen Server. Alternativ:

```bash
python3 -m http.server 8777
```

Die Fassungen liegen übereinander; die Scrollposition bestimmt, welche
sichtbar ist und wie weit die nächste schon eingeblendet ist (smoothstep, damit
jede Fassung einen Moment steht). Bewusst nicht immersiv: kein Vollbild, das
Bild sitzt in einem sichtbaren Rahmen mit Kopf- und Fußleiste, oben läuft ein
dünner Fortschrittsbalken, unten eine Skala aller Stufen. Die Seite richtet sich
nach der Anzahl der Bilder: Scrollweg, Skala und Beschriftung stellen sich selbst
ein, und der Rahmen öffnet sich, sobald die ersten drei Fassungen geladen sind.

Beide Seiten teilen sich `app.js` und `style.css`. Welcher Bildordner und welches
Seitenverhältnis gelten, steht in der jeweiligen `stufen.js` — die erste Kette ist
16:9, die zweite 4:3. Eine weitere Kette braucht deshalb nur einen Ordner, einen
`einbinden.py`-Lauf und eine Kopie von `moebel.html` mit geändertem Skriptpfad.
