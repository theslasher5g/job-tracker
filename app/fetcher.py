#!/usr/bin/env python3
"""Holt echte IT-Stellen aus öffentlichen Quellen und (wird vom Server periodisch aufgerufen).

Quellen (alle ohne API-Key):
  - swissdevjobs.ch  (Schweiz)
  - arbeitnow.com    (DACH, nur Remote-Stellen im Ausland + Schweiz)
  - remotive.com, remoteok.com, jobicy.com, weworkremotely.com, himalayas.app  (Remote, nur Europa/Worldwide)
  - workingnomads.com (Remote), Hacker News "Who is hiring" (Remote + Schweiz)
  - optional: Ashby, Workable, Recruitee, SmartRecruiters, Personio (Karriereseiten einzelner Firmen, per Umgebungsvariable)
  - Greenhouse- und Lever-Karrierseiten einzelner Firmen (Schweizer Standorte + Remote, Liste per Umgebungsvariable erweiterbar)
  - adzuna.com       (Schweiz, nur wenn ADZUNA_APP_ID und ADZUNA_APP_KEY gesetzt sind; kostenloser Key)

Nur Python-Standardbibliothek. `python3 -m app.fetcher` führt einen Offline-Selbsttest der
Normalisierung aus.
"""
import hashlib, html, json, os, re, sys, time
import urllib.request, urllib.parse, urllib.error
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from datetime import datetime, timezone, timedelta

MAX_AGE_DAYS = 45
MAX_JOBS = 800
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
    "GB": ("Grossbritannien (Remote)", 54.0, -2.0, "GB"), "US": ("USA (Remote)", 39.8, -98.6, "US"),
    "CA": ("Kanada (Remote)", 56.0, -106.0, "CA"), "NA": ("Nordamerika (Remote)", 45.0, -100.0, "NA"),
    "SA": ("Lateinamerika (Remote)", -15.0, -60.0, "SA"), "IN": ("Indien (Remote)", 21.0, 78.0, "IN"),
    "AS": ("Asien (Remote)", 34.0, 100.0, "AS"), "AF": ("Afrika (Remote)", 5.0, 20.0, "AF"),
    "OC": ("Ozeanien (Remote)", -25.0, 134.0, "OC"), "WW": ("Weltweit (Remote)", 22.0, -35.0, "WW"),
}
EUROPE_CODES = {"CH", "DE", "AT", "EU", "GB", "NL", "IE", "PT", "ES", "FR", "PL", "CZ", "SE", "DK"}
# Reihenfolge = Priorität (näher an der Schweiz zuerst). Text -> Region
REGION_RULES = [
    ("CH", r"switzerland|schweiz|suisse|svizzera"), ("DE", r"germany|deutschland"), ("AT", r"austria|österreich"),
    ("GB", r"united kingdom|\buk\b|england|scotland|britain"),
    ("EU", r"europe|emea|\beu\b|dach|netherlands|ireland|portugal|spain|france|italy|poland|czech|sweden|denmark|"
           r"belgium|finland|norway|romania|hungary|greece|estonia|lithuania|latvia"),
    ("US", r"\busa\b|\bus\b|u\.s\.|united states|new york|san francisco|california|texas|austin|seattle|boston|chicago|florida"),
    ("CA", r"canada|toronto|vancouver"), ("NA", r"north america|americas"),
    ("SA", r"latam|latin america|south america|brazil|argentina|colombia|chile|mexico"),
    ("IN", r"india"),
    ("AS", r"asia|apac|singapore|japan|china|philippines|vietnam|pakistan|indonesia|thailand|malaysia|korea"),
    ("AF", r"africa|nigeria|kenya|egypt|morocco"), ("OC", r"australia|new zealand|oceania"),
]
# REMOTE_SCOPE=europe -> wie früher nur Europa/weltweit; Standard "world" -> alle Regionen
REMOTE_SCOPE = os.environ.get("REMOTE_SCOPE", "world").lower()

_AI = (r"(\bai\b|\bml\b|machine learning|\bllm\b|genai|generative ai|mlops|\bki\b)")
RELEVANT = re.compile(
    # Infrastruktur / DevOps / Linux / Plattform
    r"devops|\bsre\b|site reliability|platform|plattform|linux|system ?engineer|systems? ?engineer|"
    r"system ?admin|sysadmin|systemadministrator|systemtechniker|systemingenieur|"
    r"infrastructure|infrastruktur|kubernetes|\bk8s\b|release engineer|automation engineer|ci/cd|network engineer|netzwerk|"
    # Cloud
    r"cloud|\baws\b|\bazure\b|\bgcp\b|"
    # Security
    r"security (engineer|analyst|architect|specialist|consultant|operations|administrator|officer)|cyber|infosec|"
    r"information security|it[- ]security|informationssicherheit|\bciso\b|pentest|penetration|devsecops|\bsoc\b|"
    r"\biam\b|appsec|sicherheitsingenieur|"
    # AI / ML (nur Engineering-Rollen)
    + _AI + r".{0,30}(engineer|ops|infrastructure|platform|architect|admin|developer|specialist)|"
    r"(engineer|architect|developer|ingenieur).{0,25}" + _AI, re.I)
NOT_RELEVANT = re.compile(r"sales|account (manager|executive)|recruit|marketing|designer|data scientist|frontend|front-end|"
                          r"\bpm\b|product manager|customer success|security (guard|officer\b.*(site|building))|physical security|"
                          r"wachmann|facility|hausmeister|sicherheitsmitarbeiter|cloud (sales|account|success)", re.I)


def get_text(url, tries=3, body=None):
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json, application/xml, */*",
                                                       **({"Content-Type": "application/json"} if body else {})},
                                         data=body.encode() if body else None)
            with urllib.request.urlopen(req, timeout=40) as r:
                return r.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            last = e
            if e.code < 500 and e.code != 429:
                break  # 404 & Co. lohnen keinen zweiten Versuch
            time.sleep(2 * (i + 1))
        except Exception as e:  # noqa: BLE001 - jede Quelle darf einzeln scheitern
            last = e
            time.sleep(2 * (i + 1))
    raise last


def as_json(fn, with_url=False):
    """Quelle mit JSON-Antwort. with_url=True gibt zusätzlich die abgerufene URL weiter (für Firmen-Karriereseiten)."""
    return lambda raw, url: fn(json.loads(raw), url) if with_url else fn(json.loads(raw))


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
    if re.search(r"security|cyber|infosec|pentest|penetration|devsecops|\bsoc\b|\biam\b|appsec|\bciso\b|sicherheit", t):
        cat = "Security"
    elif re.search(_AI, t):
        cat = "AI"
    elif "linux" in t:
        cat = "Linux"
    elif re.search(r"devops|\bsre\b|reliability|ci/cd|release", t):
        cat = "DevOps"
    elif re.search(r"cloud|\baws\b|\bazure\b|\bgcp\b", t):
        cat = "Cloud"
    elif re.search(r"platform|plattform|kubernetes|k8s|infrastructure|infrastruktur|network|netzwerk", t):
        cat = "Plattform"
    else:
        cat = "SysEng"
    if re.search(r"junior|\bjr\b|trainee|praktik|\bintern(ship)?\b|entry|berufseinsteiger|apprentice|lernende|werkstudent", t):
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


def region_of(where):
    """Freitext einer Remote-Stelle -> Schlüssel in COUNTRY_PLACES. Leer/unbekannt = weltweit."""
    w = clean(where).lower()
    for code, rx in REGION_RULES:
        if re.search(rx, w):
            return code
    return "WW"


def remote_job(source, title, company, where, url, salary, date):
    code = region_of(where)
    if REMOTE_SCOPE == "europe" and code not in EUROPE_CODES and code != "WW":
        return None
    loc = place(where) or COUNTRY_PLACES[code]
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


def ats_job(source, title, company, where, url, date, remote=False):
    """Stelle einer Firmen-Karriereseite: behalten, wenn Schweizer Standort oder Remote."""
    w = clean(where)
    remote = remote or bool(re.search(r"remote|anywhere|distributed|work from home", w, re.I))
    loc = place(w)
    if not (loc and loc[3] == "CH") and re.search(REGION_RULES[0][1], w, re.I):
        loc = COUNTRY_PLACES["CH"]
    if loc and loc[3] == "CH":
        return make(source, title, company, loc, url, "remote" if remote else "hybrid", "", date)
    if remote:
        return remote_job(source, title, company, w, url, "", date)
    return None


def from_workingnomads(data):
    out = [remote_job("workingnomads.com", j.get("title"), j.get("company_name"), j.get("location"), j.get("url"), "",
                      parse_date(j.get("pub_date"))) for j in data if isinstance(j, dict)]
    return [x for x in out if x]


def from_greenhouse(data, url):
    slug = url.split("/boards/")[1].split("/")[0]
    out = [ats_job(f"greenhouse:{slug}", j.get("title"), j.get("company_name") or slug.replace("-", " ").title(),
                   (j.get("location") or {}).get("name"), j.get("absolute_url"),
                   parse_date(j.get("first_published") or j.get("updated_at"))) for j in data.get("jobs", [])]
    return [x for x in out if x]


def from_lever(data, url):
    slug = url.split("/postings/")[1].split("?")[0]
    out = []
    for j in data if isinstance(data, list) else []:
        c = j.get("categories") or {}
        where = " | ".join([c.get("location") or ""] + list(c.get("allLocations") or []))
        out.append(ats_job(f"lever:{slug}", j.get("text"), slug.replace("-", " ").title(), where, j.get("hostedUrl"),
                           parse_date(j.get("createdAt")), remote=(j.get("workplaceType") == "remote")))
    return [x for x in out if x]


COUNTRY_WORDS = {"ch": "Switzerland", "de": "Germany", "at": "Austria", "gb": "United Kingdom", "uk": "United Kingdom",
                 "us": "USA", "ca": "Canada", "in": "India", "au": "Australia", "br": "Brazil"}


def where_of(*parts):
    """Ort/Land-Felder zu einem Text zusammensetzen; zweibuchstabige Ländercodes werden ausgeschrieben."""
    return ", ".join(COUNTRY_WORDS.get(str(p).lower(), str(p)) for p in parts if p)


def slug_title(slug):
    return slug.replace("-", " ").replace("_", " ").title()


def find_swiss_place(text):
    for name, v in PLACES.items():
        if v[2] == "CH" and re.search(rf"(?<!\w){re.escape(name)}(?!\w)", text, re.I):
            return name, v[0], v[1], "CH"
    for alias, name in ALIASES.items():
        if PLACES[name][2] == "CH" and re.search(rf"(?<!\w){re.escape(alias)}(?!\w)", text, re.I):
            return (name,) + PLACES[name]
    return None


def from_ashby(data, url):
    slug = url.split("/job-board/")[1].split("?")[0]
    out = []
    for j in data.get("jobs", []):
        where = " | ".join([j.get("location") or ""] + [x.get("location", "") for x in j.get("secondaryLocations") or []])
        out.append(ats_job(f"ashby:{slug}", j.get("title"), slug_title(slug), where, j.get("jobUrl"),
                           parse_date(j.get("publishedAt")), remote=bool(j.get("isRemote"))))
    return [x for x in out if x]


def from_workable(data, url):
    slug = url.split("/accounts/")[1].split("?")[0]
    out = [ats_job(f"workable:{slug}", j.get("title"), data.get("name") or slug_title(slug),
                   where_of(j.get("city"), j.get("country")), j.get("url") or j.get("shortlink"),
                   parse_date(j.get("published_on") or j.get("created_at")), remote=bool(j.get("telecommuting")))
           for j in data.get("jobs", [])]
    return [x for x in out if x]


def from_recruitee(data, url):
    slug = url.split("//")[1].split(".recruitee.com")[0]
    out = [ats_job(f"recruitee:{slug}", j.get("title"), j.get("company_name") or slug_title(slug),
                   where_of(j.get("city"), j.get("country_code") or j.get("country")), j.get("careers_url"),
                   parse_date(j.get("published_at") or j.get("created_at")), remote=bool(j.get("remote")))
           for j in data.get("offers", [])]
    return [x for x in out if x]


def from_smartrecruiters(data, url):
    slug = url.split("/companies/")[1].split("/")[0]
    out = []
    for j in data.get("content", []):
        loc = j.get("location") or {}
        out.append(ats_job(f"smartrecruiters:{slug}", j.get("name"), (j.get("company") or {}).get("name") or slug_title(slug),
                           where_of(loc.get("city"), loc.get("country")), f"https://jobs.smartrecruiters.com/{slug}/{j.get('id')}",
                           parse_date(j.get("releasedDate")), remote=bool(loc.get("remote"))))
    return [x for x in out if x]


def from_personio(raw, url):
    slug = url.split("//")[1].split(".jobs.personio")[0]
    out = []
    for pos in ET.fromstring(raw).iter("position"):
        out.append(ats_job(f"personio:{slug}", pos.findtext("name"), slug_title(slug), pos.findtext("office"),
                           f"https://{slug}.jobs.personio.de/job/{pos.findtext('id')}", parse_date(pos.findtext("createdAt"))))
    return [x for x in out if x]


def from_hn(data):
    """Hacker News „Who is hiring“: erste Zeile eines Kommentars = 'Firma | Rolle | Ort | REMOTE'."""
    out = []
    for h in data.get("hits", []):
        text = html.unescape(re.split(r"<p>|\n", h.get("comment_text") or "", maxsplit=1)[0])
        line = clean(text)
        parts = [x.strip() for x in line.split("|")]
        if len(parts) < 3 or len(line) > 400:
            continue
        title = next((x for x in parts[1:] if RELEVANT.search(x)), None)
        if not title:
            continue
        url = f"https://news.ycombinator.com/item?id={h.get('objectID')}"
        date = parse_date(h.get("created_at"))
        remote = bool(re.search(r"remote", line, re.I))
        loc = find_swiss_place(line)
        if loc:
            out.append(make("news.ycombinator.com", title[:120], parts[0][:80], loc, url, "remote" if remote else "hybrid", "", date))
        elif remote:
            out.append(remote_job("news.ycombinator.com", title[:120], parts[0][:80], line, url, "", date))
    return [x for x in out if x]


def from_wpjobs(raw, url):
    """WP-Job-Manager-RSS (jobspresso.co, euremotejobs.com): <job_listing:location>/<job_listing:company>."""
    host = url.split("//")[1].split("/")[0].replace("www.", "")
    out = []
    for it in ET.fromstring(raw).iter("item"):
        ext = {c.tag.rsplit("}", 1)[-1]: (c.text or "") for c in it if "}" in c.tag}
        out.append(remote_job(host, it.findtext("title"), ext.get("company"), ext.get("location"),
                              clean(it.findtext("link")), "", parse_date(it.findtext("pubDate"))))
    return [x for x in out if x]


def from_jooble(data, url):
    out = []
    for j in data.get("jobs", []):
        loc = place(j.get("location")) or find_swiss_place(clean(j.get("location"))) or COUNTRY_PLACES["CH"]
        out.append(make("jooble.org", j.get("title"), j.get("company"), loc, j.get("link"), "onsite", clean(j.get("salary")),
                        parse_date(j.get("updated"))))
    return [x for x in out if x]


def _slugs(env, default=""):
    return [x.strip() for x in os.environ.get(env, default).split(",") if x.strip()]


# Öffentliche Karriereseiten (ohne Key). Eigene Firmen: GREENHOUSE_BOARDS / LEVER_COMPANIES (kommagetrennt, Slug aus der URL
# boards.greenhouse.io/<slug> bzw. jobs.lever.co/<slug>). Unbekannte Slugs werden einfach übersprungen.
GREENHOUSE_DEFAULT = "gitlab,cloudflare,datadog,mongodb,elastic,canonical,grafanalabs,okta,digitalocean,dropbox,databricks,pagerduty,scandit,nexthink,proton"
LEVER_DEFAULT = "palantir,veeam,sonarsource"
GREENHOUSE = [x.strip() for x in os.environ.get("GREENHOUSE_BOARDS", GREENHOUSE_DEFAULT).split(",") if x.strip()]
LEVER = [x.strip() for x in os.environ.get("LEVER_COMPANIES", LEVER_DEFAULT).split(",") if x.strip()]


# Suchbegriffe für Quellen mit Stichwortsuche
SEARCH_TERMS = ("devops", "linux", "platform engineer", "site reliability", "infrastructure", "cloud engineer",
                "security engineer", "cybersecurity", "machine learning engineer", "ai engineer", "sysadmin")

SOURCES = [
    ("swissdevjobs.ch", ["https://swissdevjobs.ch/api/jobsLight"], as_json(from_swissdevjobs)),
    ("arbeitnow.com", [f"https://www.arbeitnow.com/api/job-board-api?page={p}" for p in (1, 2, 3)], as_json(from_arbeitnow)),
    ("remotive.com", ["https://remotive.com/api/remote-jobs?category=devops&limit=100"]
     + [f"https://remotive.com/api/remote-jobs?search={urllib.parse.quote(q)}&limit=100" for q in SEARCH_TERMS], as_json(from_remotive)),
    ("remoteok.com", ["https://remoteok.com/api"] + [f"https://remoteok.com/api?tag={t}" for t in
                                                    ("devops", "sysadmin", "security", "cloud", "infosec", "machine-learning", "aws")], as_json(from_remoteok)),
    ("jobicy.com", [f"https://jobicy.com/api/v2/remote-jobs?count=50&geo={g}&tag={urllib.parse.quote(t)}"
                    for g in ("europe", "switzerland") for t in SEARCH_TERMS], as_json(from_jobicy)),
    ("weworkremotely.com", ["https://weworkremotely.com/categories/remote-devops-sysadmin-jobs.rss"], lambda raw, url: from_wwr(raw)),
    ("himalayas.app", ["https://himalayas.app/jobs/api?limit=100"]
     + [f"https://himalayas.app/jobs/api/search?q={urllib.parse.quote(q)}&sort=recent" for q in SEARCH_TERMS], as_json(from_himalayas)),
    ("jobspresso.co / euremotejobs.com", [f"https://{h}/?feed=job_feed&search_keywords={urllib.parse.quote(q)}"
                                          for h in ("jobspresso.co", "euremotejobs.com") for q in SEARCH_TERMS], lambda raw, url: from_wpjobs(raw, url)),
    ("workingnomads.com", ["https://www.workingnomads.com/api/exposed_jobs/"], as_json(from_workingnomads)),
    ("greenhouse", [f"https://boards-api.greenhouse.io/v1/boards/{b}/jobs" for b in GREENHOUSE], as_json(from_greenhouse, True)),
    ("lever", [f"https://api.lever.co/v0/postings/{c}?mode=json" for c in LEVER], as_json(from_lever, True)),
]
_HN_Q = SEARCH_TERMS + ("systems engineer", "devsecops")
SOURCES.append(("hackernews", ["https://hn.algolia.com/api/v1/search_by_date?tags=comment&hitsPerPage=100&query="
                               + urllib.parse.quote(q) + "&numericFilters=created_at_i>{since}" for q in _HN_Q], as_json(from_hn)))
# Weitere Karriereseiten-Systeme: standardmässig leer, per Umgebungsvariable (kommagetrennt) aktivieren
for _name, _env, _fmt, _fn in [
    ("ashby", "ASHBY_BOARDS", "https://api.ashbyhq.com/posting-api/job-board/{}", as_json(from_ashby, True)),
    ("workable", "WORKABLE_ACCOUNTS", "https://apply.workable.com/api/v1/widget/accounts/{}", as_json(from_workable, True)),
    ("recruitee", "RECRUITEE_COMPANIES", "https://{}.recruitee.com/api/offers/", as_json(from_recruitee, True)),
    ("smartrecruiters", "SMARTRECRUITERS_COMPANIES", "https://api.smartrecruiters.com/v1/companies/{}/postings?limit=100",
     as_json(from_smartrecruiters, True)),
    ("personio", "PERSONIO_COMPANIES", "https://{}.jobs.personio.de/xml", lambda raw, url: from_personio(raw, url)),
]:
    if _slugs(_env):
        SOURCES.append((_name, [_fmt.format(x) for x in _slugs(_env)], _fn))
if os.environ.get("JOOBLE_KEY"):
    SOURCES.append(("jooble.org", [(f"https://jooble.org/api/{os.environ['JOOBLE_KEY']}", json.dumps({"keywords": q, "location": "Switzerland"}))
                                   for q in ("devops", "linux", "system engineer", "security engineer", "cloud engineer", "platform engineer",
                                             "infrastructure engineer", "machine learning engineer")], as_json(from_jooble, True)))
if os.environ.get("ADZUNA_APP_ID") and os.environ.get("ADZUNA_APP_KEY"):
    _q = urllib.parse.urlencode({"app_id": os.environ["ADZUNA_APP_ID"], "app_key": os.environ["ADZUNA_APP_KEY"],
                                 "results_per_page": 50, "max_days_old": MAX_AGE_DAYS})
    SOURCES.append(("adzuna.com", [f"https://api.adzuna.com/v1/api/jobs/ch/search/1?{_q}&what={urllib.parse.quote(w)}"
                                   for w in ("devops", "linux", "platform engineer", "system engineer", "site reliability", "security engineer", "cloud engineer", "machine learning engineer")],
                    as_json(from_adzuna)))


def fetch_all():
    """Alle Quellen abfragen -> (Stellenliste, Bericht pro Quelle). Einzelne Quellen dürfen scheitern."""
    jobs, report = {}, {}
    for name, urls, fn in SOURCES:
        n, errs = 0, []
        for u in urls:
            u, body = u if isinstance(u, tuple) else (u, None)
            try:
                for job in fn(get_text(u.replace("{since}", str(int(time.time()) - 35 * 86400)), body=body), u):
                    jobs.setdefault(job["id"], job); n += 1
            except Exception as e:  # noqa: BLE001
                errs.append(f"{type(e).__name__}: {e}")
                print(f"[{name}] {u.split('?')[0]} -> {errs[-1]}", file=sys.stderr)
        rep = {"jobs": n}
        if errs:  # "error" = alle Abrufe fehlgeschlagen, "warn" = nur einzelne (z.B. unbekannte Firmen-Slugs)
            rep["error" if len(errs) == len(urls) else "warn"] = f"{len(errs)}/{len(urls)} fehlgeschlagen, zuletzt: {errs[-1]}"
        report[name] = rep
    seen, unique = set(), []
    for j in jobs.values():  # gleiche Stelle bei mehreren Quellen nur einmal (erste Quelle gewinnt)
        k = (j["title"].lower(), j["company"].lower())
        if k not in seen:
            seen.add(k); unique.append(j)
    jobs = {j["id"]: j for j in unique}
    cutoff = (datetime.now(timezone.utc) - timedelta(days=MAX_AGE_DAYS)).date().isoformat()
    fresh = sorted((j for j in jobs.values() if not j["date"] or j["date"] >= cutoff),
                   key=lambda j: j["date"], reverse=True)
    swiss = [j for j in fresh if j["country"] == "CH"]  # Schweizer Stellen werden nie wegen des Limits abgeschnitten
    final = swiss + [j for j in fresh if j["country"] != "CH"][:max(0, MAX_JOBS - len(swiss))]
    final.sort(key=lambda j: j["date"], reverse=True)
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
    assert [j["country"] for j in rm] == ["EU", "US"] and rm[0]["level"] == "Senior", rm
    ro = from_remoteok([{"legal": "x"}, {"position": "Linux Systems Engineer", "company": "Z", "location": "Worldwide",
                         "url": "https://remoteok.com/z", "date": now, "salary_min": 80000, "salary_max": 100000},
                        {"position": "DevOps Engineer", "company": "Y", "location": "United States", "url": "https://remoteok.com/y"}])
    assert [j["country"] for j in ro] == ["WW", "US"], ro
    jo = from_jobicy({"jobs": [{"jobTitle": "Junior DevOps Engineer", "companyName": "J", "jobGeo": "Switzerland",
                                "url": "https://jobicy.com/j", "pubDate": "2026-10-20 10:00:00"}]})
    ww = from_wwr("<rss><channel><item><title>Acme: Senior Platform Engineer</title><region>Anywhere in the World</region>"
                  "<link>https://wwr/1</link><pubDate>Mon, 20 Oct 2026 10:00:00 +0000</pubDate></item></channel></rss>")
    hi = from_himalayas({"jobs": [{"title": "SRE", "companyName": "H", "locationRestrictions": ["Germany"],
                                   "applicationLink": "https://himalayas.app/h", "pubDate": int(time.time())}]})
    az = from_adzuna({"results": [{"title": "Linux Engineer", "company": {"display_name": "Ad"}, "redirect_url": "https://adz/1",
                                   "location": {"display_name": "Basel", "area": ["Switzerland", "Basel-Stadt", "Basel"]},
                                   "created": now, "salary_min": 90000, "salary_max": 110000}]})
    assert len(ro) == 2 and ro[0]["salary"] == "80–100k USD", ro
    assert len(jo) == 1 and jo[0]["level"] == "Junior" and jo[0]["date"] == "2026-10-20", jo
    assert len(ww) == 1 and ww[0]["company"] == "Acme" and ww[0]["level"] == "Senior" and ww[0]["date"] == "2026-10-20", ww
    assert len(hi) == 1 and hi[0]["city"].startswith("Deutschland"), hi
    assert len(az) == 1 and az[0]["city"] == "Basel" and az[0]["country"] == "CH", az
    wn = from_workingnomads([{"title": "DevOps Engineer", "company_name": "WN", "location": "Anywhere", "url": "https://wn/1", "pub_date": now}])
    gh = from_greenhouse({"jobs": [
        {"title": "Site Reliability Engineer", "company_name": "GL", "location": {"name": "Zurich, Switzerland"}, "absolute_url": "https://gh/1", "updated_at": now},
        {"title": "Platform Engineer", "company_name": "GL", "location": {"name": "Remote - EMEA"}, "absolute_url": "https://gh/2", "updated_at": now},
        {"title": "Linux Engineer", "company_name": "GL", "location": {"name": "San Francisco"}, "absolute_url": "https://gh/3", "updated_at": now}]},
        "https://boards-api.greenhouse.io/v1/boards/gitlab/jobs")
    lv = from_lever([{"text": "DevOps Engineer", "hostedUrl": "https://lv/1", "createdAt": int(time.time() * 1000),
                      "categories": {"location": "Bern", "allLocations": ["Bern"]}, "workplaceType": "hybrid"},
                     {"text": "Linux Admin", "hostedUrl": "https://lv/2", "categories": {"location": "London"}}],
                    "https://api.lever.co/v0/postings/palantir?mode=json")
    assert len(wn) == 1 and wn[0]["country"] == "WW", wn
    assert [(j["country"], j["mode"]) for j in gh] == [("CH", "hybrid"), ("EU", "remote")], gh
    assert len(lv) == 1 and lv[0]["city"] == "Bern" and lv[0]["company"] == "Palantir", lv
    hn = from_hn({"hits": [
        {"objectID": "1", "created_at": now, "comment_text": "Acme | DevOps Engineer | Zurich, Switzerland | ONSITE<p>We do things"},
        {"objectID": "2", "created_at": now, "comment_text": "Foo &amp; Co | Senior Platform Engineer | REMOTE (US only) | Full-time<p>x"},
        {"objectID": "3", "created_at": now, "comment_text": "Looks like a normal comment about devops but no pipes"}]})
    assert [(j["company"], j["city"], j["mode"]) for j in hn] == [("Acme", "Zürich", "hybrid"), ("Foo & Co", "USA (Remote)", "remote")], hn
    ash = from_ashby({"jobs": [{"title": "Platform Engineer", "location": "Zurich", "isRemote": False, "jobUrl": "https://ashby/1", "publishedAt": now}]},
                     "https://api.ashbyhq.com/posting-api/job-board/acme")
    wk = from_workable({"name": "WK", "jobs": [{"title": "Linux Engineer", "city": "Basel", "country": "CH", "url": "https://wk/1", "published_on": "2026-10-20"}]},
                       "https://apply.workable.com/api/v1/widget/accounts/wk")
    rc = from_recruitee({"offers": [{"title": "DevOps Engineer", "company_name": "RC", "city": "Bern", "country_code": "CH", "careers_url": "https://rc/1", "created_at": now}]},
                        "https://rc.recruitee.com/api/offers/")
    sr = from_smartrecruiters({"content": [{"id": "9", "name": "Systems Engineer", "releasedDate": now, "location": {"city": "Genf", "country": "ch"}}]},
                              "https://api.smartrecruiters.com/v1/companies/Acme/postings?limit=100")
    pe = from_personio("<workzag-jobs><position><id>5</id><office>Luzern</office><name>Linux Systemadministrator</name><createdAt>2026-10-20T10:00:00+00:00</createdAt></position></workzag-jobs>",
                       "https://pe.jobs.personio.de/xml")
    assert [j["city"] for j in ash + wk + rc + sr + pe] == ["Zürich", "Basel", "Bern", "Genf", "Luzern"], (ash, wk, rc, sr, pe)
    assert sr[0]["url"] == "https://jobs.smartrecruiters.com/Acme/9" and pe[0]["url"].endswith("/job/5"), (sr, pe)
    wp = from_wpjobs("<rss xmlns:job_listing='https://wpjobmanager.com'><channel><item><title>Cloud Security Engineer</title>"
                     "<link>https://euremotejobs.com/job/1</link><pubDate>Mon, 20 Oct 2026 10:00:00 +0000</pubDate>"
                     "<job_listing:location>Europe</job_listing:location><job_listing:company>EU Co</job_listing:company></item></channel></rss>",
                     "https://euremotejobs.com/?feed=job_feed")
    jb = from_jooble({"jobs": [{"title": "Linux Administrator", "location": "Winterthur", "company": "Jo", "link": "https://jooble/1",
                                "updated": now, "salary": "100k"}]}, "https://jooble.org/api/KEY")
    assert wp[0]["category" if False else "cat"] == "Security" and wp[0]["company"] == "EU Co" and wp[0]["country"] == "EU", wp
    assert jb[0]["city"] == "Winterthur" and jb[0]["cat"] == "Linux", jb
    for t, c in [("Cyber Security Analyst", "Security"), ("Machine Learning Engineer", "AI"), ("Cloud Engineer (AWS)", "Cloud"),
                 ("Senior Infrastructure Engineer", "Plattform"), ("Linux Administrator", "Linux"), ("DevSecOps Engineer", "Security")]:
        assert classify(t)[0] == c and RELEVANT.search(t), (t, classify(t))
    for t in ("Security Guard", "Cloud Sales Manager", "Frontend Engineer", "Marketing AI Specialist"):
        assert not RELEVANT.search(t) or NOT_RELEVANT.search(t), t
    for txt, code in [("", "WW"), ("Worldwide", "WW"), ("USA Only", "US"), ("Canada", "CA"), ("Brazil, Argentina", "SA"),
                      ("Asia", "AS"), ("Europe, USA", "EU"), ("Switzerland", "CH"), ("Remote - India", "IN"), ("Australia", "OC")]:
        assert region_of(txt) == code, (txt, region_of(txt))
    print("selftest ok")


if __name__ == "__main__":
    selftest()
