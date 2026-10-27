const STATUS = { "": "Neu", saved: "Gemerkt", applied: "Beworben", interview: "Interview", offer: "Angebot", rejected: "Absage" };
const EUROPE = new Set(["CH", "DE", "AT", "EU", "GB", "NL", "IE", "PT", "ES", "FR", "PL", "CZ", "SE", "DK"]);
const CATS = ["DevOps", "Linux", "Plattform", "SysEng"];
const CAT_LABEL = { DevOps: "DevOps", Linux: "Linux", Plattform: "Plattform", SysEng: "System Engineer" };
const MODE_LABEL = { onsite: "Vor Ort", hybrid: "Hybrid", remote: "Remote" };

let jobs = [], meta = {};
const CITIES = {};
const api = async (path, method = "GET", body) => {
  const r = await fetch("/api" + path, { method, headers: body ? { "Content-Type": "application/json" } : {}, body: body && JSON.stringify(body) });
  const data = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(data.error || r.statusText);
  return data;
};
const f = { q: "", level: "", mode: "", where: "", status: "", cat: "", city: "" };

const $ = id => document.getElementById(id);
const esc = s => String(s).replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const allJobs = () => jobs;
const statusOf = j => j.status || "";
const searchUrl = j => j.url || `https://www.jobs.ch/de/stellenangebote/?term=${encodeURIComponent(j.title)}&location=${encodeURIComponent(j.city)}`;

function filtered(skip) {
  const q = f.q.trim().toLowerCase();
  return allJobs().filter(j => {
    const c = CITIES[j.city];
    if (q && !`${j.title} ${j.company} ${j.city}`.toLowerCase().includes(q)) return false;
    if (f.level && j.level !== f.level) return false;
    if (f.mode && j.mode !== f.mode) return false;
    if (f.where === "CH" && c.country !== "CH") return false;
    if (f.where === "ABROAD" && c.country === "CH") return false;
    if (f.where === "EUROPE" && !EUROPE.has(c.country)) return false;
    if (f.where === "WORLD" && EUROPE.has(c.country)) return false;
    if (f.status !== "" && statusOf(j) !== (f.status === "new" ? "" : f.status)) return false;
    if (skip !== "cat" && f.cat && j.cat !== f.cat) return false;
    if (skip !== "city" && f.city && j.city !== f.city) return false;
    return true;
  });
}

// ---------- map ----------
const map = L.map("map", { scrollWheelZoom: true });
L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
  maxZoom: 18, attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
}).addTo(map);
const markerLayer = L.layerGroup().addTo(map);
const CH_BOUNDS = [[45.7, 5.8], [47.9, 10.6]];
map.fitBounds(CH_BOUNDS);
$("zoomCH").onclick = () => map.fitBounds(CH_BOUNDS);
$("zoomEU").onclick = () => map.fitBounds([[36.5, -10], [55, 20]]);
$("zoomWorld").onclick = () => map.setView([25, 10], 2);

function drawMap(jobs) {
  markerLayer.clearLayers();
  const byCity = {};
  jobs.forEach(j => (byCity[j.city] ||= []).push(j));
  Object.entries(byCity).forEach(([city, js]) => {
    const c = CITIES[city];
    const swiss = c.country === "CH";
    const color = swiss ? "#d52b1e" : "#2b6cb0";
    const m = L.circleMarker([c.lat, c.lng], {
      radius: 8 + Math.sqrt(js.length) * 5, color: "#fff", weight: 2, fillColor: color, fillOpacity: .8
    }).addTo(markerLayer);
    m.bindTooltip(`<b>${esc(city)}</b> · ${js.length}`, { direction: "top" });
    m.bindPopup(`<b>${esc(city)}</b> (${js.length})<ul>${js.slice(0, 8).map(j => `<li>${esc(j.title)} – ${esc(j.company)}</li>`).join("")}</ul>${js.length > 8 ? "…" : ""}`);
    m.on("click", () => { f.city = f.city === city ? "" : city; render(); });
  });
}

// ---------- charts ----------
const css = n => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
let chCity, chCat;
function drawCharts() {
  const text = css("--muted"), line = css("--line");
  const cityCounts = {};
  filtered("city").forEach(j => cityCounts[j.city] = (cityCounts[j.city] || 0) + 1);
  const cities = Object.entries(cityCounts).sort((a, b) => b[1] - a[1]).slice(0, 15);
  const cityData = {
    labels: cities.map(c => c[0]),
    datasets: [{ data: cities.map(c => c[1]),
      backgroundColor: cities.map(c => c[0] === f.city ? css("--c4") : CITIES[c[0]].country === "CH" ? css("--c1") : css("--c2")) }]
  };
  if (chCity) { chCity.data = cityData; chCity.update(); } else {
    chCity = new Chart($("chCity"), { type: "bar", data: cityData, options: {
      indexAxis: "y", maintainAspectRatio: false, plugins: { legend: { display: false } },
      scales: { x: { ticks: { color: text, precision: 0 }, grid: { color: line } }, y: { ticks: { color: text, autoSkip: false }, grid: { display: false } } },
      onClick: (_, els) => { if (els.length) { const c = chCity.data.labels[els[0].index]; f.city = f.city === c ? "" : c; render(); } }
    } });
  }
  const catCounts = Object.fromEntries(CATS.map(c => [c, 0]));
  filtered("cat").forEach(j => catCounts[j.cat]++);
  const catData = {
    labels: CATS.map(c => CAT_LABEL[c]),
    datasets: [{ data: CATS.map(c => catCounts[c]), borderColor: css("--card"), borderWidth: 2,
      backgroundColor: [css("--c1"), css("--c2"), css("--c3"), css("--c4")] }]
  };
  if (chCat) { chCat.data = catData; chCat.update(); } else {
    chCat = new Chart($("chCat"), { type: "doughnut", data: catData, options: {
      maintainAspectRatio: false, plugins: { legend: { position: "right", labels: { color: text } } },
      onClick: (_, els) => { if (els.length) { const c = CATS[els[0].index]; f.cat = f.cat === c ? "" : c; render(); } }
    } });
  }
}

// ---------- list / stats ----------
function drawStats(jobs) {
  const all = allJobs(), ch = all.filter(j => CITIES[j.city].country === "CH").length;
  const cnt = s => all.filter(j => statusOf(j) === s).length;
  const items = [
    [jobs.length, "Treffer"], [ch, "In der Schweiz"], [all.length - ch, "Remote Ausland"],
    [all.filter(j => j.level === "Junior").length, "Junior-Stellen"],
    [cnt("applied"), "Beworben"], [cnt("interview"), "Interviews"], [cnt("offer"), "Angebote"]
  ];
  $("stats").innerHTML = items.map(([n, l]) => `<div class="stat"><b>${n}</b><span>${l}</span></div>`).join("");
}

function drawList(jobs) {
  $("listTitle").textContent = `Stellen (${jobs.length})`;
  const active = [f.city && `Stadt: ${f.city}`, f.cat && `Bereich: ${CAT_LABEL[f.cat]}`].filter(Boolean);
  $("activeFilter").textContent = active.join(" · ");
  const sorted = [...jobs].sort((a, b) => (b.date || "").localeCompare(a.date || ""));
  $("list").innerHTML = sorted.length ? sorted.map(j => {
    const st = statusOf(j), c = CITIES[j.city];
    return `<article class="job st-${st}">
      <h3>${esc(j.title)}</h3>
      <div class="meta">${esc(j.company)} · ${esc(j.city)}${c.country !== "CH" ? " (" + c.country + ")" : ""}${j.salary ? " · " + esc(j.salary) : ""}<br>${j.date ? esc(j.date) + " · " : ""}${esc(j.source)}</div>
      <div class="tags"><span class="tag ${j.level}">${j.level}</span><span class="tag ${j.mode}">${MODE_LABEL[j.mode]}</span><span class="tag">${CAT_LABEL[j.cat]}</span></div>
      <div class="jobfoot">
        <select data-id="${j.id}" aria-label="Status">${Object.entries(STATUS).map(([k, v]) => `<option value="${k}"${k === st ? " selected" : ""}>${v}</option>`).join("")}</select>
        <span>${j.custom ? `<button class="btn small" data-del="${j.id}">Löschen</button> ` : ""}<a href="${esc(searchUrl(j))}" target="_blank" rel="noopener">${j.url ? "Inserat" : "Suchen"} ↗</a></span>
      </div></article>`;
  }).join("") : `<p class="empty">${jobs.length ? "Keine Stellen für diese Filter." : meta.running ? "Erster Abruf läuft … (dauert ca. 1 Minute)" : "Noch keine Stellen. Klicke auf „Jetzt aktualisieren“."}</p>`;
}

function render() {
  const jobs = filtered();
  document.querySelectorAll(".chip").forEach(b => b.classList.toggle("on", b.dataset.cat === f.cat));
  drawStats(jobs); drawMap(jobs); drawCharts(); drawList(jobs);
}

// ---------- wiring ----------
$("catChips").innerHTML = CATS.map(c => `<button class="chip" data-cat="${c}">${CAT_LABEL[c]}</button>`).join("");
$("catChips").onclick = e => { const c = e.target.dataset.cat; if (c) { f.cat = f.cat === c ? "" : c; render(); } };
$("fStatus").insertAdjacentHTML("beforeend", `<option value="new">Neu</option>` + Object.entries(STATUS).filter(([k]) => k).map(([k, v]) => `<option value="${k}">${v}</option>`).join(""));
[["q", "q"], ["fLevel", "level"], ["fMode", "mode"], ["fWhere", "where"], ["fStatus", "status"]].forEach(([id, key]) =>
  $(id).addEventListener("input", e => { f[key] = e.target.value; render(); }));
$("btnReset").onclick = () => {
  Object.keys(f).forEach(k => f[k] = "");
  ["q", "fLevel", "fMode", "fWhere", "fStatus"].forEach(id => $(id).value = "");
  render();
};
$("list").addEventListener("change", async e => {
  const id = e.target.dataset.id;
  if (!id) return;
  try { await api(`/jobs/${id}/status`, "PUT", { status: e.target.value }); } catch (err) { alert(err.message); }
  await load();
});
$("list").addEventListener("click", async e => {
  const id = e.target.dataset.del;
  if (!id || !confirm("Stelle löschen?")) return;
  try { await api(`/jobs/${id}`, "DELETE"); } catch (err) { alert(err.message); }
  await load();
});

api("/places").then(p => {
  $("addCity").innerHTML = p.map(c => `<option value="${esc(c.name)}">${esc(c.name)} (${c.country})</option>`).join("");
});
$("btnAdd").onclick = () => $("dlg").showModal();
$("addForm").addEventListener("submit", async e => {
  if (e.submitter?.value !== "ok") return;
  try { await api("/jobs", "POST", Object.fromEntries(new FormData(e.target))); e.target.reset(); await load(); }
  catch (err) { alert(err.message); }
});

$("btnExport").onclick = () => {
  const blob = new Blob([JSON.stringify(jobs, null, 2)], { type: "application/json" });
  const a = Object.assign(document.createElement("a"), { href: URL.createObjectURL(blob), download: "job-tracker.json" });
  a.click(); URL.revokeObjectURL(a.href);
};

let poll;
$("btnRefresh").onclick = async () => {
  await api("/refresh", "POST").catch(() => {});
  meta.running = true; drawMeta();
  clearInterval(poll);
  poll = setInterval(async () => { await load(); if (!meta.running) clearInterval(poll); }, 3000);
};

function drawMeta() {
  const src = Object.entries(meta.sources || {}).map(([n, s]) => `${n}: ${s.jobs}${s.error ? " ⚠" : s.warn ? " ⚠?" : ""}`).join(" · ");
  $("btnRefresh").disabled = !!meta.running;
  $("meta").textContent = meta.running ? "Aktualisiere Stellen …"
    : meta.at ? `Zuletzt aktualisiert: ${new Date(meta.at).toLocaleString("de-CH")} — ${src}` : "";
}

async function load() {
  const d = await api("/jobs");
  jobs = d.jobs; meta = d.meta;
  jobs.forEach(j => CITIES[j.city] = { lat: j.lat, lng: j.lng, country: j.country });
  drawMeta(); render();
}
load().then(() => { if (meta.running || !jobs.length) $("btnRefresh").onclick(); });
