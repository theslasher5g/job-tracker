// Beispieldaten – Stellen sind Platzhalter zum Ausprobieren, keine echten Inserate.
// Der "Suchen"-Link führt zur echten Live-Suche auf jobs.ch. Eigene Stellen kannst du in der App hinzufügen.
const CITIES = {
  "Zürich":   { lat: 47.3769, lng: 8.5417, country: "CH", region: "ZH" },
  "Bern":     { lat: 46.9480, lng: 7.4474, country: "CH", region: "BE" },
  "Basel":    { lat: 47.5596, lng: 7.5886, country: "CH", region: "BS" },
  "Genf":     { lat: 46.2044, lng: 6.1432, country: "CH", region: "GE" },
  "Lausanne": { lat: 46.5197, lng: 6.6323, country: "CH", region: "VD" },
  "Luzern":   { lat: 47.0502, lng: 8.3093, country: "CH", region: "LU" },
  "Zug":      { lat: 47.1724, lng: 8.5170, country: "CH", region: "ZG" },
  "Winterthur": { lat: 47.4988, lng: 8.7237, country: "CH", region: "ZH" },
  "St. Gallen": { lat: 47.4245, lng: 9.3767, country: "CH", region: "SG" },
  "Lugano":   { lat: 46.0037, lng: 8.9511, country: "CH", region: "TI" },
  "Aarau":    { lat: 47.3925, lng: 8.0442, country: "CH", region: "AG" },
  "Olten":    { lat: 47.3500, lng: 7.9030, country: "CH", region: "SO" },
  "Berlin":   { lat: 52.5200, lng: 13.4050, country: "DE", region: "Berlin" },
  "München":  { lat: 48.1351, lng: 11.5820, country: "DE", region: "Bayern" },
  "Amsterdam":{ lat: 52.3676, lng: 4.9041, country: "NL", region: "NH" },
  "Dublin":   { lat: 53.3498, lng: -6.2603, country: "IE", region: "Dublin" },
  "Wien":     { lat: 48.2082, lng: 16.3738, country: "AT", region: "Wien" },
  "Lissabon": { lat: 38.7223, lng: -9.1393, country: "PT", region: "Lisboa" }
};

// mode: onsite | hybrid | remote   level: Junior | Mid | Senior
// cat: DevOps | Linux | Plattform | SysEng
const JOBS = [
  { id: 1,  title: "Junior DevOps Engineer",            company: "Swisscom",           city: "Bern",       cat: "DevOps",    level: "Junior", mode: "hybrid", salary: "85–100k", date: "2026-10-20" },
  { id: 2,  title: "Linux System Engineer",             company: "Puzzle ITC",         city: "Bern",       cat: "Linux",     level: "Mid",    mode: "hybrid", salary: "100–120k", date: "2026-10-18" },
  { id: 3,  title: "Platform Engineer Kubernetes",      company: "UBS",                city: "Zürich",     cat: "Plattform", level: "Mid",    mode: "hybrid", salary: "115–140k", date: "2026-10-22" },
  { id: 4,  title: "Junior Systemtechniker Linux",      company: "Green.ch",           city: "Olten",      cat: "Linux",     level: "Junior", mode: "onsite", salary: "80–95k",  date: "2026-10-12" },
  { id: 5,  title: "Site Reliability Engineer",         company: "Google",             city: "Zürich",     cat: "DevOps",    level: "Senior", mode: "hybrid", salary: "150–190k", date: "2026-10-21" },
  { id: 6,  title: "DevOps Engineer (CI/CD)",           company: "Zühlke",             city: "Zürich",     cat: "DevOps",    level: "Mid",    mode: "hybrid", salary: "105–125k", date: "2026-10-15" },
  { id: 7,  title: "Systems Engineer Infrastructure",   company: "SBB",                city: "Bern",       cat: "SysEng",    level: "Mid",    mode: "hybrid", salary: "100–118k", date: "2026-10-10" },
  { id: 8,  title: "Junior Platform Engineer",          company: "Nexthink",           city: "Lausanne",   cat: "Plattform", level: "Junior", mode: "hybrid", salary: "90–105k", date: "2026-10-19" },
  { id: 9,  title: "Cloud Platform Engineer (AWS)",     company: "Swiss Re",           city: "Zürich",     cat: "Plattform", level: "Senior", mode: "hybrid", salary: "130–155k", date: "2026-10-17" },
  { id: 10, title: "Linux Administrator",               company: "Infomaniak",         city: "Genf",       cat: "Linux",     level: "Mid",    mode: "onsite", salary: "95–110k", date: "2026-10-08" },
  { id: 11, title: "DevOps Engineer",                   company: "Roche",              city: "Basel",      cat: "DevOps",    level: "Mid",    mode: "hybrid", salary: "110–130k", date: "2026-10-14" },
  { id: 12, title: "Junior Systems Engineer",           company: "Novartis",           city: "Basel",      cat: "SysEng",    level: "Junior", mode: "hybrid", salary: "88–102k", date: "2026-10-16" },
  { id: 13, title: "Platform Engineer (Terraform)",     company: "Adnovum",            city: "Zürich",     cat: "Plattform", level: "Mid",    mode: "hybrid", salary: "108–128k", date: "2026-10-09" },
  { id: 14, title: "Linux Systems Engineer",            company: "CERN",               city: "Genf",       cat: "Linux",     level: "Mid",    mode: "onsite", salary: "100–120k", date: "2026-10-05" },
  { id: 15, title: "DevOps / SRE Engineer",             company: "Crypto Valley Co.",  city: "Zug",        cat: "DevOps",    level: "Mid",    mode: "hybrid", salary: "115–140k", date: "2026-10-23" },
  { id: 16, title: "Junior Linux Engineer",             company: "Axpo",               city: "Aarau",      cat: "Linux",     level: "Junior", mode: "onsite", salary: "82–96k", date: "2026-10-11" },
  { id: 17, title: "System Engineer Microsoft/Linux",   company: "Luzerner Kantonalbank", city: "Luzern",  cat: "SysEng",    level: "Mid",    mode: "onsite", salary: "98–115k", date: "2026-10-07" },
  { id: 18, title: "Platform Engineer",                 company: "ABB",                city: "Winterthur", cat: "Plattform", level: "Mid",    mode: "hybrid", salary: "105–122k", date: "2026-10-13" },
  { id: 19, title: "DevOps Engineer Junior",            company: "Helvetia",           city: "St. Gallen", cat: "DevOps",    level: "Junior", mode: "hybrid", salary: "85–98k", date: "2026-10-06" },
  { id: 20, title: "Systemingenieur Linux/Automation",  company: "Swisscom",           city: "Lugano",     cat: "Linux",     level: "Mid",    mode: "onsite", salary: "95–110k", date: "2026-10-04" },
  { id: 21, title: "Senior Platform Engineer",          company: "Sunrise",            city: "Zürich",     cat: "Plattform", level: "Senior", mode: "hybrid", salary: "125–150k", date: "2026-10-24" },
  { id: 22, title: "DevOps Engineer (Remote EU)",       company: "GitLab",             city: "Berlin",     cat: "DevOps",    level: "Mid",    mode: "remote", salary: "85–110k €", date: "2026-10-22" },
  { id: 23, title: "Junior SRE (Remote)",               company: "Datadog",            city: "Dublin",     cat: "DevOps",    level: "Junior", mode: "remote", salary: "60–75k €", date: "2026-10-21" },
  { id: 24, title: "Linux Platform Engineer (Remote)",  company: "Canonical",          city: "Amsterdam",  cat: "Linux",     level: "Mid",    mode: "remote", salary: "80–105k €", date: "2026-10-19" },
  { id: 25, title: "Platform Engineer (Remote DACH)",   company: "Celonis",            city: "München",    cat: "Plattform", level: "Mid",    mode: "remote", salary: "85–105k €", date: "2026-10-18" },
  { id: 26, title: "Systems Engineer (Remote)",         company: "Bitpanda",           city: "Wien",       cat: "SysEng",    level: "Junior", mode: "remote", salary: "55–70k €", date: "2026-10-16" },
  { id: 27, title: "Junior DevOps (Remote Europe)",     company: "Talkdesk",           city: "Lissabon",   cat: "DevOps",    level: "Junior", mode: "remote", salary: "40–55k €", date: "2026-10-15" },
  { id: 28, title: "Linux Support Engineer",            company: "Proton",             city: "Genf",       cat: "Linux",     level: "Junior", mode: "remote", salary: "75–90k", date: "2026-10-23" }
];
