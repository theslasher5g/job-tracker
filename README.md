# IT Job Tracker Schweiz

Läuft lokal in Docker (Web-App + PostgreSQL). Holt automatisch echte Stellen für **System Engineer · Plattform · DevOps · Linux** (Junior bis Senior) – Schweiz und Remote im Ausland – und zeigt sie auf Karte, Diagrammen und in einer Liste.

## Starten

```bash
docker compose up -d --build
```

Dann `http://localhost:8080` öffnen. Der erste Abruf startet automatisch (ca. 1 Minute), danach alle 6 Stunden (`REFRESH_HOURS` in `docker-compose.yml`). Per Knopf „Jetzt aktualisieren“ geht es auch sofort.

- Stoppen: `docker compose down` (Daten bleiben im Volume `pgdata`; mit `-v` werden sie gelöscht)
- Logs: `docker compose logs -f app`
- Der Port ist nur auf `127.0.0.1` gebunden, es gibt keine Anmeldung.

## Funktionen

- Karte (Leaflet): Kreis anklicken filtert nach Stadt; Diagramme (Chart.js): Balken/Segmente anklicken filtert
- Filter nach Level, Vor Ort/Hybrid/Remote, Schweiz/Ausland, Bereich, Status
- Status pro Stelle (Gemerkt → Beworben → Interview → Angebot/Absage) und eigene Stellen, gespeichert in Postgres
- Stellen, die 14 Tage nicht mehr in den Quellen auftauchen, werden entfernt – ausser du hast sie getrackt oder selbst angelegt

## Quellen

swissdevjobs.ch, arbeitnow.com, remotive.com (öffentliche APIs, ohne Key). Neue Quellen: Funktion in `app/fetcher.py` ergänzen und in `SOURCES` eintragen. Offline-Test der Normalisierung: `python3 -m app.fetcher`.
