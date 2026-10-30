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

## Suchkriterien

Titel müssen zu einem dieser Bereiche passen (Gross-/Kleinschreibung egal, auch deutsche Titel): **DevOps/SRE**, **Linux/Sysadmin**, **Plattform/Infrastruktur/Kubernetes/Netzwerk**, **Cloud** (AWS/Azure/GCP), **Security/Cyber** (Security Engineer/Analyst, SOC, Pentest, DevSecOps, IAM, CISO) und **AI/ML** (nur Engineering-Rollen wie ML/AI/LLM/MLOps Engineer). Verkauf, Marketing, Recruiting, Wachdienst u.ä. werden aussortiert. Level (Junior/Mid/Senior) und Bereich werden aus dem Titel abgeleitet. Die Begriffe stehen in `RELEVANT` / `SEARCH_TERMS` in `app/fetcher.py`.

## Quellen

Ohne Key: swissdevjobs.ch, arbeitnow.com, remotive.com, remoteok.com, jobicy.com, weworkremotely.com, himalayas.app, workingnomads.com sowie die öffentlichen Karriereseiten (Greenhouse/Lever) einzelner Firmen wie GitLab, Cloudflare, Datadog, Canonical (Remote-Stellen aus aller Welt – USA, Kanada, Asien usw.; mit `REMOTE_SCOPE: europe` in `docker-compose.yml` nur Europa/weltweit). Bei den Karriereseiten werden nur Stellen mit Schweizer Standort oder Remote übernommen. Eigene Firmen trägst du mit `GREENHOUSE_BOARDS` / `LEVER_COMPANIES` in `docker-compose.yml` ein (Slug aus `boards.greenhouse.io/<slug>` bzw. `jobs.lever.co/<slug>`). Dazu kommen jobspresso.co und euremotejobs.com (Remote) und die Hacker-News-Threads „Who is hiring“ (Remote und Schweiz). Karriereseiten von Ashby, Workable, Recruitee, SmartRecruiters und Personio sind standardmässig aus: du trägst Firmen in `docker-compose.yml` ein (Beispiele dort als Kommentar), z.B. die Schweizer Firmen, bei denen du dich bewerben willst. Doppelte Stellen aus mehreren Quellen werden zusammengefasst.

Optional **Adzuna** (breiteste Schweizer Abdeckung): Key auf developer.adzuna.com holen (**kostenpflichtig**: nur 25 Test-Abrufe gratis, danach ca. £8/Monat – für den Tracker nicht nötig) und in eine Datei `.env` neben `docker-compose.yml` schreiben:

```
ADZUNA_APP_ID=...
ADZUNA_APP_KEY=...
```

Optional **Jooble** (`JOOBLE_KEY` in `.env`): Schweizer Stellen; den API-Zugang beantragst du auf jooble.org, prüfe vorher die Bedingungen und ob es kostenlos bleibt.

Danach `docker compose up -d`. Pro Quelle zeigt die Seite oben die Anzahl Stellen (⚠ = alle Abrufe fehlgeschlagen, ⚠? = einzelne, z.B. unbekannte Firmen-Slugs; Details in `docker compose logs app`).

Neue Quelle: Funktion in `app/fetcher.py` ergänzen und in `SOURCES` eintragen. Offline-Test der Normalisierung: `python3 -m app.fetcher`.
