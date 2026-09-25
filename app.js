/* Resonanz - Scrollposition steuert das Überblenden der Bildkette.
   Kein Framework, keine Abhängigkeiten. */

(function () {
  "use strict";

  var quelle = window.RESONANZ || {};
  var daten = quelle.stufen || [];
  if (!daten.length) {
    console.error("Resonanz: stufen.js fehlt oder ist leer. Erst decay.py "
                  + "oder einbinden.py laufen lassen.");
    return;
  }

  // Welcher Ordner, welches Seitenverhältnis - beides steht in den Daten,
  // damit dieselbe app.js mehrere Ketten bedienen kann.
  var ORDNER = quelle.ordner || "img";
  if (quelle.breite && quelle.hoehe) {
    var wurzel = document.documentElement.style;
    wurzel.setProperty("--bildverhaeltnis", quelle.breite + " / " + quelle.hoehe);
    wurzel.setProperty("--seitenfaktor", (quelle.breite / quelle.hoehe).toFixed(4));
  }

  var ANZAHL = daten.length;          // Fassungen insgesamt
  var LETZTE = ANZAHL - 1;            // Übergänge

  // Scrollweg je Übergang in Bildschirmhöhen. Kurze Ketten dürfen sich pro
  // Stufe 0,85 Höhen nehmen; lange werden gestaucht, damit die Seite
  // insgesamt etwa vierzehn Höhen lang bleibt.
  var WEG_PRO_STUFE = Math.max(0.45, Math.min(0.85, 14 / LETZTE));

  // So viele Fassungen müssen geladen sein, bevor der Rahmen sich öffnet -
  // der Rest kommt im Hintergrund nach, während schon gescrollt wird.
  var VORLAUF = Math.min(3, ANZAHL);

  var bahn    = document.getElementById("bahn");
  var buehne  = document.querySelector(".buehne");
  var stapel  = document.getElementById("stapel");
  var balken  = document.getElementById("balken");
  var skala   = document.getElementById("skala");
  var laden   = document.getElementById("laden");
  var ladenTx = document.getElementById("laden-text");
  var zahl    = document.getElementById("stufe-zahl");
  var vonZahl = document.getElementById("stufe-von");
  var messO   = document.getElementById("mess-orig");
  var messV   = document.getElementById("mess-vor");
  var leiste  = document.querySelector(".fortschritt");

  /* ---------------------------------------------------------------- Aufbau */

  var bilder = [];
  var ticks  = [];
  var geladen = 0;

  daten.forEach(function (stufe, i) {
    var img = new Image();
    img.src = ORDNER + "/" + stufe.datei;
    img.alt = i === 0
      ? "Wohnraum, unveränderte Aufnahme"
      : "Wohnraum, Fassung " + i + " von " + LETZTE;
    img.decoding = "async";
    img.loading = "eager";
    img.fetchPriority = i < VORLAUF ? "high" : "low";
    img.draggable = false;
    img.style.zIndex = String(i);     // spätere Fassungen liegen oben
    img.style.opacity = i === 0 ? "1" : "0";

    img.addEventListener("load", fertigGemeldet);
    img.addEventListener("error", fertigGemeldet);

    stapel.appendChild(img);
    bilder.push(img);

    var li = document.createElement("li");
    skala.appendChild(li);
    ticks.push(li);
  });

  function fertigGemeldet() {
    geladen += 1;
    ladenTx.textContent = "Fassungen werden geladen " + geladen + " / " + ANZAHL;
    if (geladen === VORLAUF) {
      // nicht auf die ganze Kette warten - der Anfang genügt zum Loslegen
      laden.classList.add("fertig");
      setTimeout(function () { laden.hidden = true; }, 450);
    }
    if (geladen >= VORLAUF) zeichnen();
  }

  /* ---------------------------------------------------------------- Geometrie */

  function bahnhoeheSetzen() {
    var vh = buehne.offsetHeight || window.innerHeight;
    // Bühnenhöhe (ein Standbild am Anfang) + Weg für jeden Übergang
    bahn.style.height = Math.round(vh * (1 + LETZTE * WEG_PRO_STUFE)) + "px";
  }

  /* ---------------------------------------------------------------- Ablauf */

  function klemmen(x, min, max) { return x < min ? min : (x > max ? max : x); }

  // Weiche Ein-/Ausblendkante: jede Fassung bekommt einen kurzen Moment Ruhe,
  // bevor die nächste sie überschreibt.
  function weich(x) { return x * x * (3 - 2 * x); }

  var aktuelleStufe = -1;

  function zeichnen() {
    var oben   = bahn.getBoundingClientRect().top;
    var strecke = bahn.offsetHeight - buehne.offsetHeight;
    var anteil  = strecke > 0 ? klemmen(-oben / strecke, 0, 1) : 0;

    var p = anteil * LETZTE;             // Position in der Kette, 0 .. 10
    var i = Math.min(Math.floor(p), LETZTE);
    var rest = weich(klemmen(p - i, 0, 1));

    for (var k = 0; k < ANZAHL; k++) {
      var o = k <= i ? 1 : (k === i + 1 ? rest : 0);
      var s = o.toFixed(3);
      if (bilder[k].style.opacity !== s) bilder[k].style.opacity = s;
    }

    balken.style.width = (anteil * 100).toFixed(2) + "%";
    leiste.setAttribute("aria-valuenow", p.toFixed(1));

    // Beschriftung folgt der Fassung, die gerade oben liegt
    var sichtbar = rest > 0.5 ? Math.min(i + 1, LETZTE) : i;
    if (sichtbar !== aktuelleStufe) {
      aktuelleStufe = sichtbar;
      var d = daten[sichtbar];
      zahl.textContent = String(sichtbar).padStart(2, "0");
      messO.textContent = komma(d.abstand_zum_original);
      messV.textContent = komma(d.abstand_zum_vorherigen);
      ticks.forEach(function (li, n) {
        li.classList.toggle("erreicht", n < sichtbar);
        li.classList.toggle("aktiv", n === sichtbar);
      });
    }
  }

  function komma(n) { return Number(n).toFixed(2).replace(".", ","); }

  /* ---------------------------------------------------------------- Ereignisse */

  var wartet = false;

  function anstossen() {
    if (wartet) return;
    wartet = true;
    requestAnimationFrame(function () {
      wartet = false;
      zeichnen();
    });
  }

  window.addEventListener("scroll", anstossen, { passive: true });
  window.addEventListener("resize", function () {
    bahnhoeheSetzen();
    anstossen();
  });

  if (vonZahl) vonZahl.textContent = " / " + LETZTE;
  var quellName = document.getElementById("quelle-name");
  if (quellName && quelle.quelle) {
    quellName.textContent = quelle.quelle + " — " + quelle.breite + " × " + quelle.hoehe;
  }
  bahnhoeheSetzen();
  zeichnen();
})();
