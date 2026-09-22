/* Resonanz - Scrollposition steuert das Überblenden der Bildkette.
   Kein Framework, keine Abhängigkeiten. */

(function () {
  "use strict";

  var daten = (window.RESONANZ && window.RESONANZ.stufen) || [];
  if (!daten.length) {
    console.error("Resonanz: img/stufen.js fehlt oder ist leer. Erst decay.py laufen lassen.");
    return;
  }

  var ANZAHL = daten.length;          // 11 Fassungen
  var LETZTE = ANZAHL - 1;            // 10 Übergänge
  var WEG_PRO_STUFE = 0.85;           // Bildschirmhoehen Scrollweg je Übergang

  var bahn    = document.getElementById("bahn");
  var buehne  = document.querySelector(".buehne");
  var stapel  = document.getElementById("stapel");
  var balken  = document.getElementById("balken");
  var skala   = document.getElementById("skala");
  var laden   = document.getElementById("laden");
  var ladenTx = document.getElementById("laden-text");
  var zahl    = document.getElementById("stufe-zahl");
  var messO   = document.getElementById("mess-orig");
  var messV   = document.getElementById("mess-vor");
  var leiste  = document.querySelector(".fortschritt");

  /* ---------------------------------------------------------------- Aufbau */

  var bilder = [];
  var ticks  = [];
  var geladen = 0;

  daten.forEach(function (stufe, i) {
    var img = new Image();
    img.src = "img/" + stufe.datei;
    img.alt = i === 0
      ? "Wohnraum, unveränderte Aufnahme"
      : "Wohnraum, Fassung " + i + " von " + LETZTE;
    img.decoding = "async";
    img.loading = "eager";
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
    ladenTx.textContent = "Bilder werden geladen " + geladen + " / " + ANZAHL;
    if (geladen >= ANZAHL) {
      laden.classList.add("fertig");
      setTimeout(function () { laden.hidden = true; }, 450);
      zeichnen();
    }
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

  bahnhoeheSetzen();
  zeichnen();
})();
