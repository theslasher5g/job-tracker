import json, os, threading, time, uuid
from datetime import datetime, timezone
from flask import Flask, jsonify, request, send_from_directory
from psycopg.types.json import Jsonb

from . import db, fetcher

REFRESH_HOURS = float(os.environ.get("REFRESH_HOURS", "6"))
STALE_DAYS = 14  # Stellen, die seit so vielen Tagen nicht mehr auftauchen, werden entfernt (ausser getrackte)
STATUSES = {"saved", "applied", "interview", "offer", "rejected"}
CATS, LEVELS, MODES = {"DevOps", "Linux", "Plattform", "SysEng", "Security", "Cloud", "AI"}, {"Junior", "Mid", "Senior"}, {"onsite", "hybrid", "remote"}

app = Flask(__name__, static_folder="static", static_url_path="")
_lock = threading.Lock()


def get_meta():
    with db.conn() as c:
        row = c.execute("SELECT value FROM meta WHERE key='fetch'").fetchone()
    meta = row["value"] if row else {}
    meta["running"] = _lock.locked()
    return meta


def refresh():
    """Quellen abfragen und in die DB schreiben. Läuft höchstens einmal gleichzeitig."""
    if not _lock.acquire(blocking=False):
        return
    try:
        jobs, report = fetcher.fetch_all()
        with db.conn() as c:
            for j in jobs:
                c.execute(
                    """INSERT INTO jobs (id,title,company,city,lat,lng,country,cat,level,mode,salary,date,url,source)
                       VALUES (%(id)s,%(title)s,%(company)s,%(city)s,%(lat)s,%(lng)s,%(country)s,%(cat)s,%(level)s,
                               %(mode)s,%(salary)s,%(date)s,%(url)s,%(source)s)
                       ON CONFLICT (id) DO UPDATE SET title=EXCLUDED.title, company=EXCLUDED.company, city=EXCLUDED.city,
                         lat=EXCLUDED.lat, lng=EXCLUDED.lng, country=EXCLUDED.country, cat=EXCLUDED.cat,
                         level=EXCLUDED.level, mode=EXCLUDED.mode, salary=EXCLUDED.salary, date=EXCLUDED.date,
                         url=EXCLUDED.url, last_seen=now()""", j)
            if jobs:  # nur aufräumen, wenn der Abruf überhaupt etwas geliefert hat
                c.execute("""DELETE FROM jobs WHERE NOT custom AND last_seen < now() - make_interval(days => %s)
                             AND id NOT IN (SELECT job_id FROM status)""", (STALE_DAYS,))
            meta = {"at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "sources": report, "count": len(jobs)}
            c.execute("INSERT INTO meta VALUES ('fetch', %s) ON CONFLICT (key) DO UPDATE SET value=EXCLUDED.value", (Jsonb(meta),))
        print(f"refresh: {len(jobs)} Stellen {report}", flush=True)
    except Exception as e:  # noqa: BLE001
        print(f"refresh failed: {e}", flush=True)
    finally:
        _lock.release()


def scheduler():
    while True:
        try:
            at = get_meta().get("at")
            age = (datetime.now(timezone.utc) - datetime.fromisoformat(at)).total_seconds() / 3600 if at else 1e9
            if age >= REFRESH_HOURS:
                refresh()
        except Exception as e:  # noqa: BLE001
            print(f"scheduler: {e}", flush=True)
        time.sleep(300)


@app.get("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.get("/api/jobs")
def jobs():
    with db.conn() as c:
        rows = c.execute("""SELECT j.id,j.title,j.company,j.city,j.lat,j.lng,j.country,j.cat,j.level,j.mode,j.salary,
                                   j.date,j.url,j.source,j.custom,s.status
                            FROM jobs j LEFT JOIN status s ON s.job_id=j.id ORDER BY j.date DESC, j.first_seen DESC""").fetchall()
    return jsonify(jobs=rows, meta=get_meta())


@app.get("/api/places")
def places():
    return jsonify([{"name": n, "country": v[2]} for n, v in fetcher.PLACES.items()])


@app.put("/api/jobs/<job_id>/status")
def set_status(job_id):
    s = (request.get_json(silent=True) or {}).get("status", "")
    if s and s not in STATUSES:
        return jsonify(error="ungültiger Status"), 400
    with db.conn() as c:
        if not c.execute("SELECT 1 FROM jobs WHERE id=%s", (job_id,)).fetchone():
            return jsonify(error="nicht gefunden"), 404
        if s:
            c.execute("""INSERT INTO status (job_id,status) VALUES (%s,%s)
                         ON CONFLICT (job_id) DO UPDATE SET status=EXCLUDED.status, updated=now()""", (job_id, s))
        else:
            c.execute("DELETE FROM status WHERE job_id=%s", (job_id,))
    return jsonify(ok=True)


@app.post("/api/jobs")
def add_job():
    d = request.get_json(silent=True) or {}
    title, company = (d.get("title") or "").strip(), (d.get("company") or "").strip()
    loc = fetcher.place(d.get("city", ""))
    if not title or not company or not loc:
        return jsonify(error="Titel, Firma und eine bekannte Stadt sind nötig"), 400
    if d.get("cat") not in CATS or d.get("level") not in LEVELS or d.get("mode") not in MODES:
        return jsonify(error="ungültige Auswahl"), 400
    url = (d.get("url") or "").strip()
    if url and not url.startswith(("http://", "https://")):
        return jsonify(error="Link muss mit http(s):// beginnen"), 400
    job_id = "c" + uuid.uuid4().hex[:11]
    with db.conn() as c:
        c.execute("""INSERT INTO jobs (id,title,company,city,lat,lng,country,cat,level,mode,salary,date,url,source,custom)
                     VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'manuell',true)""",
                  (job_id, title, company, loc[0], loc[1], loc[2], loc[3], d["cat"], d["level"], d["mode"],
                   (d.get("salary") or "").strip(), datetime.now().date().isoformat(), url))
    return jsonify(id=job_id), 201


@app.delete("/api/jobs/<job_id>")
def delete_job(job_id):
    with db.conn() as c:
        r = c.execute("DELETE FROM jobs WHERE id=%s AND custom", (job_id,))
        c.execute("DELETE FROM status WHERE job_id=%s AND NOT EXISTS (SELECT 1 FROM jobs WHERE id=%s)", (job_id, job_id))
    return jsonify(ok=r.rowcount > 0), (200 if r.rowcount else 404)


@app.post("/api/refresh")
def refresh_now():
    if _lock.locked():
        return jsonify(running=True), 202
    threading.Thread(target=refresh, daemon=True).start()
    return jsonify(running=True), 202


db.init()
if os.environ.get("DISABLE_SCHEDULER") != "1":
    threading.Thread(target=scheduler, daemon=True).start()
