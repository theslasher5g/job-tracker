# IT Job Tracker Schweiz

Statische Website (kein Build nötig) zum Verfolgen von IT-Stellen: System Engineer, Plattform, DevOps, Linux – Junior bis Senior, Schweiz und Remote im Ausland.

- Interaktive Karte (Leaflet): Kreis anklicken filtert nach Stadt
- Diagramme (Chart.js): Balken/Segmente anklicken filtert
- Filter, Status-Tracking (Neu → Gemerkt → Beworben → Interview → Angebot/Absage), eigene Stellen, JSON Export/Import
- Daten liegen lokal im Browser (localStorage)

Starten: `python3 -m http.server 8000` und `http://localhost:8000` öffnen (oder `index.html` direkt).

`data.js` enthält **Beispielstellen**; "Suchen" verlinkt auf die Live-Suche von jobs.ch.
