#!/usr/bin/env python3
"""Holt echte IT-Stellen aus öffentlichen Quellen und (wird vom Server periodisch aufgerufen).

Quellen (alle ohne API-Key):
  - swissdevjobs.ch  (Schweiz)
  - arbeitnow.com    (DACH, nur Remote-Stellen im Ausland + Schweiz)
  - remotive.com, remoteok.com, jobicy.com, weworkremotely.com, himalayas.app  (Remote, nur Europa/Worldwide)
  - adzuna.com       (Schweiz, nur wenn ADZUNA_APP_ID und ADZUNA_APP_KEY gesetzt sind; kostenloser Key)

Nur Python-Standardbibliothek. `python3 -m app.fetcher` führt einen Offline-Selbsttest der
Normalisierung aus.
"""
import hashlib, json, os, re, sys, time
import urllib.request, urllib.parse
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from datetime import datetime, timezone, timedelta

MAX_AGE_DAYS = 45
MAX_JOBS = 400
UA = "Mozilla/5.0 (compatible; job-tracker/1.0; self-hosted)"

# name -> (lat, lng, country)
PLACES = {
    # Schweiz
    "Zürich": (47.3769, 8.5417, "CH"), "Bern": (46.9480, 7.4474, "CH"), "Basel": (47.5596, 7.5886, "CH"),
    "Genf": (46.2044, 6.1432, "CH"), "Lausanne": (46.5197, 6.6323, "CH"), "Luzern": (47.0502, 8.3093, "CH"),
    "Zug": (47.1724, 8.5170, "CH"), "Winterthur": (47.4988, 8.7237, "CH"), "St. Gallen": (47.4245, 9.3767, "CH"),
    "Lugano": (46.0037, 8.9511, "CH"), "Aarau": (47.3925, 8.0442, "CH"), "Olten": (47.3500, 7.9030, "CH"),
    "Baden": (47.4731, 8.3063, "CH"), "Schaffhausen": (47.6959, 8.6349, "CH"), "Chur": (46.8499, 9.5329, "CH"),
    "Fribourg": (46.8065, 7.1620, "CH"), "Neuchâtel": (46.9900, 6.9293, "CH"), "Sion": (46.2293, 7.3598, "CH"),
    "Biel": (47.1368, 7.2468, "CH"), "Thun": (46.7580, 7.6280, "CH"), "Frauenfeld": (47.5568, 8.8987, "CH"),
    "Wil": (47.4617, 9.0450, "CH"), "Rapperswil": (47.2266, 8.8224, "CH"), "Dübendorf": (47.3970, 8.6186, "CH"),
    "Opfikon": (47.4313, 8.5733, "CH"), "Wallisellen": (47.4153, 8.5958, "CH"), "Kloten": (47.4515, 8.5849, "CH"),
    "Schlieren": (47.3967, 8.4478, "CH"), "Cham": (47.1830, 8.4630, "CH"), "Solothurn": (47.2088, 7.5372, "CH"),
    "Bellinzona": (46.1946, 9.0244, "CH"), "Yverdon": (46.7785, 6.6410, "CH"), "Vevey": (46.4628, 6.8430, "CH"),
    "Pfäffikon": (47.2020, 8.7770, "CH"), "Liestal": (47.4841, 7.7345, "CH"), "Muttenz": (47.5223, 7.6460, "CH"),
    # Ausland
    "Berlin": (52.5200, 13.4050, "DE"), "München": (48.1351, 11.5820, "DE"), "Hamburg": (53.5511, 9.9937, "DE"),
    "Frankfurt": (50.1109, 8.6821, "DE"), "Köln": (50.9375, 6.9603, "DE"), "Stuttgart": (48.7758, 9.1829, "DE"),
    "Düsseldorf": (51.2277, 6.7735, "DE"), "Leipzig": (51.3397, 12.3731, "DE"), "Dresden": (51.0504, 13.7373, "DE"),
    "Hannover": (52.3759, 9.7320, "DE"), "Nürnberg": (49.4521, 11.0767, "DE"),
    "Amsterdam": (52.3676, 4.9041, "NL"), "Dublin": (53.3498, -6.2603, "IE"), "Wien": (48.2082, 16.3738, "AT"),
    "Lissabon": (38.7223, -9.1393, "PT"), "Madrid": (40.4168, -3.7038, "ES"), "Barcelona": (41.3874, 2.1686, "ES"),
    "Paris": (48.8566, 2.3522, "FR"), "London": (51.5074, -0.1278, "GB"), "Warschau": (52.2297, 21.0122, "PL"),
    "Prag": (50.0755, 14.4378, "CZ"), "Stockholm": (59.3293, 18.0686, "SE"), "Kopenhagen": (55.6761, 12.5683, "DK"),
}
ALIASES = {
    "zurich": "Zürich", "zuerich": "Zürich", "geneva": "Genf", "genève": "Genf", "geneve": "Genf",
    "lucerne": "Luzern", "munich": "München", "muenchen": "München", "cologne": "Köln", "koeln": "Köln",
    "vienna": "Wien", "lisbon": "Lissabon", "warsaw": "Warschau", "prague": "Prag", "copenhagen": "Kopenhagen",
    "berne": "Bern", "basel-stadt": "Basel", "st.gallen": "St. Gallen", "sankt gallen": "St. Gallen",
    "neuchatel": "Neuchâtel", "freiburg": "Fribourg", "dubendorf": "Dübendorf", "pfaffikon": "Pfäffikon",
    "dusseldorf": "Düsseldorf", "nuremberg": "Nürnberg", "nuernberg": "Nürnberg", "bienne": "Biel",
}
# Pseudo-Standorte, wenn nur Land / "Europa" bekannt ist
COUNTRY_PLACES = {
    "CH": ("Schweiz (ohne Ort)", 46.8, 8.2, "CH"), "DE": ("Deutschland (Remote)", 51.2, 10.4, "DE"),
    "AT": ("Österreich (Remote)", 47.5, 14.5, "AT"), "EU": ("Remote Europa", 50.0, 14.0, "EU"),
}
EUROPE_TOKENS = [
    "europe", "emea", "worldwide", "anywhere", "global", "switzerland", "germany", "austria", "netherlands",
    "ireland", "portugal", "spain", "france", "united kingdom", "uk", "italy", "poland", "czech", "sweden",
    "denmark", "belgium", "dach", "eu", "european", "world",
]

COUNTRY_NAMES = {"CH": ["switzerland", "schweiz", "suisse"], "DE": ["germany", "deutschland"], "AT": ["austria", "österreich"]}

RELEVANT = re.compile(
    r"devops|\bsre\b|site reliability|platform|plattform|linux|system ?engineer|systems? ?engineer|"
    r"system ?admin|sysadmin|systemadministrator|systemtechniker|systemingenieur|cloud engineer|"
    r"infrastructure|infrastruktur|kubernetes|\bk8s\b|release engineer|automation engineer|ci/cd", re.I)
NOT_RELEVANT = re.compile(r"sales|account manager|recruit|marketing|designer|data scientist|frontend|front-end|"
                          r"\bpm\b|product manager|customer success", re.I)


def get_text(url, tries=3):
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json, application/xml, */*"})
            with urllib.request.urlopen(req, timeout=40) as r:
                return r.read().decode("utf-8", "replace")
        except Exception as e:  # noqa: BLE001 - jede Quelle darf einzeln scheitern
            last = e
            time.sleep(2 * (i + 1))
    raise last


def as_json(fn):
    return lambda raw: fn(json.loads(raw))


def clean(s):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", str(s or ""))).strip()


def place(name):
    """Freitext-Ort -> (Name, lat, lng, Land) oder None."""
    n = clean(name)
    if not n:
        return None
    for part in re.split(r"[,/|(]| - ", n):
        key = part.strip()
        if not key:
            continue
        key = ALIASES.get(key.lower(), key)
        for cname, (lat, lng, c) in PLACES.items():
            if cname.lower() == key.lower():
                return cname, lat, lng, c
    return None


def classify(title):
    t = title.lower()
    if "linux" in t:
        cat = "Linux"
    elif re.search(r"devops|\bsre\b|reliability|ci/cd|release", t):
        cat = "DevOps"
    elif re.search(r"platform|plattform|cloud|kubernetes|k8s|infrastructure|infrastruktur", t):
        cat = "Plattform"
    else:
        cat = "SysEng"
    if re.search(r"junior|\bjr\b|trainee|praktik|entry|berufseinsteiger|apprentice|lernende|werkstudent", t):
        lvl = "Junior"
    elif re.search(r"senior|\bsr\b|lead|principal|staff|head of|architect", t):
        lvl = "Senior"
    else:
        lvl = "Mid"
    return cat, lvl


def parse_date(v):
    if v in (None, ""):
        return None
    try:
        if isinstance(v, (int, float)):
            return datetime.fromtimestamp(v / 1000 if v > 1e11 else v, timezone.utc)
        try:
            d = datetime.fromisoformat(str(v).replace("Z", "+00:00"))
        except ValueError:
            d = parsedate_to_datetime(str(v))
        return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return None


def make(source, title, company, loc, url, mode, salary, date):
    title, company = clean(title), clean(company)
    if not title or not url or not RELEVANT.search(title) or NOT_RELEVANT.search(title):
        return None
    cat, lvl = classify(title)
    return {
        "id": hashlib.sha1(url.encode()).hexdigest()[:12], "title": title, "company": company or "–",
        "city": loc[0], "lat": loc[1], "lng": loc[2], "country": loc[3], "cat": cat, "level": lvl,
        "mode": mode, "salary": salary or "", "date": date.date().isoformat() if date else "",
        "url": url, "source": source,
    }


# ---------- Quellen ----------
def from_swissdevjobs(data):
    items = data if isinstance(data, list) else data.get("jobs", [])
    out = []
    for j in items:
        title = j.get("name") or j.get("title")
        loc = place(j.get("actualCity") or j.get("cityCategory") or j.get("city") or "")
        if not loc:
            c = COUNTRY_PLACES["CH"]; loc = c
        slug = j.get("jobUrl") or j.get("_id")
        url = slug if str(slug).startswith("http") else f"https://swissdevjobs.ch/jobs/{slug}"
        wa = str(j.get("workArrangement") or j.get("remote") or "").lower()
        mode = "remote" if "remote" in wa and "hybrid" not in wa else "hybrid" if "hybrid" in wa else "onsite"
        lo, hi = j.get("annualSalaryFrom"), j.get("annualSalaryTo")
        salary = f"{round(lo/1000)}–{round(hi/1000)}k CHF" if lo and hi else ""
        out.append(make("swissdevjobs.ch", title, j.get("company"), loc, url, mode, salary,
                        parse_date(j.get("activeFrom") or j.get("createdAt") or j.get("publishedAt"))))
    return [x for x in out if x]


def from_arbeitnow(data):
    out = []
    for j in data.get("data", []):
        loc_txt = j.get("location") or ""
        loc = place(loc_txt)
        remote = bool(j.get("remote"))
        in_ch = loc and loc[3] == "CH"
        if not (remote or in_ch):
            continue  # Ausland nur, wenn remote
        if not loc:
            loc = COUNTRY_PLACES["EU"]
        out.append(make("arbeitnow.com", j.get("title"), j.get("company_name"), loc, j.get("url"),
                        "remote" if remote else "onsite", "", parse_date(j.get("created_at"))))
    return [x for x in out if x]


def europe_ok(where):
    """Remote-Stelle ist aus der Schweiz/Europa bewerbbar? Leer = weltweit."""
    where = clean(where).lower()
    if not where:
        return True
    if re.search(r"\b(usa|us|u\.s\.|canada|north america|latam|india|apac|asia|africa)\b only|^(usa|united states|canada|india)$", where):
        return False
    return any(re.search(rf"\b{re.escape(t)}\b", where) for t in EUROPE_TOKENS)


def remote_job(source, title, company, where, url, salary, date):
    if not europe_ok(where):
        return None
    w = clean(where).lower()
    code = next((c for c, names in COUNTRY_NAMES.items() if any(re.search(rf"\b{n}\b", w) for n in names)), None)
    loc = place(where) or COUNTRY_PLACES.get(code) or COUNTRY_PLACES["EU"]
    return make(source, title, company, loc, url, "remote", salary, date)


def money(lo, hi, cur=""):
    return f"{round(lo/1000)}–{round(hi/1000)}k {cur}".strip() if lo and hi else ""


def from_remotive(data):
    out = [remote_job("remotive.com", j.get("title"), j.get("company_name"), j.get("candidate_required_location"),
                      j.get("url"), clean(j.get("salary")), parse_date(j.get("publication_date")))
           for j in data.get("jobs", [])]
    return [x for x in out if x]


def from_remoteok(data):
    out = [remote_job("remoteok.com", j.get("position"), j.get("company"), j.get("location"), j.get("url"),
                      money(j.get("salary_min"), j.get("salary_max"), "USD"), parse_date(j.get("date")))
           for j in data if isinstance(j, dict) and j.get("position")]
    return [x for x in out if x]


def from_jobicy(data):
    out = []
    for j in data.get("jobs", []):
        geo = j.get("jobGeo")
        geo = ", ".join(geo) if isinstance(geo, list) else geo
        out.append(remote_job("jobicy.com", j.get("jobTitle"), j.get("companyName"), geo, j.get("url"),
                              money(j.get("annualSalaryMin"), j.get("annualSalaryMax"), j.get("salaryCurrency") or ""),
                              parse_date(j.get("pubDate"))))
    return [x for x in out if x]


def from_wwr(raw):
    out = []
    for it in ET.fromstring(raw).iter("item"):
        t = clean(it.findtext("title"))
        company, _, title = t.partition(": ")
        if not title:
            company, title = "", t
        out.append(remote_job("weworkremotely.com", title, company, it.findtext("region"), clean(it.findtext("link")),
                              "", parse_date(it.findtext("pubDate"))))
    return [x for x in out if x]


def from_himalayas(data):
    out = []
    for j in data.get("jobs", []):
        where = ", ".join(j.get("locationRestrictions") or [])
        out.append(remote_job("himalayas.app", j.get("title"), j.get("companyName"), where,
                              j.get("applicationLink") or j.get("guid"),
                              money(j.get("minSalary"), j.get("maxSalary"), j.get("currency") or ""),
                              parse_date(j.get("pubDate"))))
    return [x for x in out if x]


def from_adzuna(data):
    out = []
    for j in data.get("results", []):
        area = (j.get("location") or {}).get("area") or []
        loc = place(", ".join(reversed(area))) or place((j.get("location") or {}).get("display_name")) or COUNTRY_PLACES["CH"]
        out.append(make("adzuna.com", j.get("title"), (j.get("company") or {}).get("display_name"), loc,
                        j.get("redirect_url"), "onsite", money(j.get("salary_min"), j.get("salary_max"), "CHF"),
                        parse_date(j.get("created"))))
    return [x for x in out if x]


SOURCES = [
    ("swissdevjobs.ch", ["https://swissdevjobs.ch/api/jobsLight"], as_json(from_swissdevjobs)),
    ("arbeitnow.com", [f"https://www.arbeitnow.com/api/job-board-api?page={p}" for p in (1, 2, 3)], as_json(from_arbeitnow)),
    ("remotive.com", ["https://remotive.com/api/remote-jobs?category=devops&limit=100",
                      "https://remotive.com/api/remote-jobs?search=linux&limit=100",
                      "https://remotive.com/api/remote-jobs?search=platform%20engineer&limit=100"], as_json(from_remotive)),
    ("remoteok.com", ["https://remoteok.com/api"], as_json(from_remoteok)),
    ("jobicy.com", [f"https://jobicy.com/api/v2/remote-jobs?count=50&geo={g}&tag={t}"
                    for g in ("europe", "switzerland") for t in ("devops", "linux")], as_json(from_jobicy)),
    ("weworkremotely.com", ["https://weworkremotely.com/categories/remote-devops-sysadmin-jobs.rss"], from_wwr),
    ("himalayas.app", ["https://himalayas.app/jobs/api?limit=100"], as_json(from_himalayas)),
]
if os.environ.get("ADZUNA_APP_ID") and os.environ.get("ADZUNA_APP_KEY"):
    _q = urllib.parse.urlencode({"app_id": os.environ["ADZUNA_APP_ID"], "app_key": os.environ["ADZUNA_APP_KEY"],
                                 "results_per_page": 50, "max_days_old": MAX_AGE_DAYS})
    SOURCES.append(("adzuna.com", [f"https://api.adzuna.com/v1/api/jobs/ch/search/1?{_q}&what={urllib.parse.quote(w)}"
                                   for w in ("devops", "linux", "platform engineer", "system engineer", "site reliability")],
                    as_json(from_adzuna)))


def fetch_all():
    """Alle Quellen abfragen -> (Stellenliste, Bericht pro Quelle). Einzelne Quellen dürfen scheitern."""
    jobs, report = {}, {}
    for name, urls, fn in SOURCES:
        n, err = 0, None
        for u in urls:
            try:
                for job in fn(get_text(u)):
                    jobs.setdefault(job["id"], job); n += 1
            except Exception as e:  # noqa: BLE001
                err = f"{type(e).__name__}: {e}"
                print(f"[{name}] {u} -> {err}", file=sys.stderr)
        report[name] = {"jobs": n, **({"error": err} if err else {})}
    seen, unique = set(), []
    for j in jobs.values():  # gleiche Stelle bei mehreren Quellen nur einmal (erste Quelle gewinnt)
        k = (j["title"].lower(), j["company"].lower())
        if k not in seen:
            seen.add(k); unique.append(j)
    jobs = {j["id"]: j for j in unique}
    cutoff = (datetime.now(timezone.utc) - timedelta(days=MAX_AGE_DAYS)).date().isoformat()
    final = sorted((j for j in jobs.values() if not j["date"] or j["date"] >= cutoff),
                   key=lambda j: j["date"], reverse=True)[:MAX_JOBS]
    return final, report


def selftest():
    now = datetime.now(timezone.utc).isoformat()
    sdj = from_swissdevjobs([
        {"name": "Junior DevOps Engineer", "company": "ACME", "actualCity": "Zurich", "jobUrl": "acme-devops",
         "workArrangement": "Hybrid", "annualSalaryFrom": 90000, "annualSalaryTo": 105000, "activeFrom": now},
        {"name": "Sales Manager", "company": "X", "actualCity": "Bern", "jobUrl": "x"}])
    an = from_arbeitnow({"data": [
        {"title": "Platform Engineer (m/w/d)", "company_name": "Foo", "location": "Berlin", "remote": True,
         "url": "https://arbeitnow.com/a", "created_at": int(time.time())},
        {"title": "Linux Admin", "company_name": "Bar", "location": "Hamburg", "remote": False, "url": "https://arbeitnow.com/b"}]})
    rm = from_remotive({"jobs": [
        {"title": "Senior Site Reliability Engineer", "company_name": "R", "candidate_required_location": "Europe",
         "url": "https://remotive.com/r", "publication_date": now, "salary": "$100k"},
        {"title": "DevOps Engineer", "company_name": "S", "candidate_required_location": "USA Only", "url": "https://remotive.com/s"}]})
    assert len(sdj) == 1 and sdj[0]["city"] == "Zürich" and sdj[0]["level"] == "Junior" and sdj[0]["mode"] == "hybrid", sdj
    assert sdj[0]["salary"] == "90–105k CHF", sdj
    assert len(an) == 1 and an[0]["city"] == "Berlin" and an[0]["cat"] == "Plattform", an
    assert len(rm) == 1 and rm[0]["level"] == "Senior" and rm[0]["country"] == "EU", rm
    ro = from_remoteok([{"legal": "x"}, {"position": "Linux Systems Engineer", "company": "Z", "location": "Worldwide",
                         "url": "https://remoteok.com/z", "date": now, "salary_min": 80000, "salary_max": 100000},
                        {"position": "DevOps Engineer", "company": "Y", "location": "United States", "url": "https://remoteok.com/y"}])
    jo = from_jobicy({"jobs": [{"jobTitle": "Junior DevOps Engineer", "companyName": "J", "jobGeo": "Switzerland",
                                "url": "https://jobicy.com/j", "pubDate": "2026-10-20 10:00:00"}]})
    ww = from_wwr("<rss><channel><item><title>Acme: Senior Platform Engineer</title><region>Anywhere in the World</region>"
                  "<link>https://wwr/1</link><pubDate>Mon, 20 Oct 2026 10:00:00 +0000</pubDate></item></channel></rss>")
    hi = from_himalayas({"jobs": [{"title": "SRE", "companyName": "H", "locationRestrictions": ["Germany"],
                                   "applicationLink": "https://himalayas.app/h", "pubDate": int(time.time())}]})
    az = from_adzuna({"results": [{"title": "Linux Engineer", "company": {"display_name": "Ad"}, "redirect_url": "https://adz/1",
                                   "location": {"display_name": "Basel", "area": ["Switzerland", "Basel-Stadt", "Basel"]},
                                   "created": now, "salary_min": 90000, "salary_max": 110000}]})
    assert len(ro) == 1 and ro[0]["salary"] == "80–100k USD", ro
    assert len(jo) == 1 and jo[0]["level"] == "Junior" and jo[0]["date"] == "2026-10-20", jo
    assert len(ww) == 1 and ww[0]["company"] == "Acme" and ww[0]["level"] == "Senior" and ww[0]["date"] == "2026-10-20", ww
    assert len(hi) == 1 and hi[0]["city"].startswith("Deutschland"), hi
    assert len(az) == 1 and az[0]["city"] == "Basel" and az[0]["country"] == "CH", az
    print("selftest ok")


if __name__ == "__main__":
    selftest()
