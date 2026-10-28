#!/usr/bin/env python3
"""Fragt Google Flüge nach Nonstop-Preisen ab Fuerteventura (FUE) zu mehreren deutschen
Zielen ab, loggt sie in prices.csv und erzeugt index.html mit der Preisentwicklung."""
import csv
import html
import json
import re
import time
import urllib.request
from datetime import datetime
from pathlib import Path

BASE = Path(__file__).resolve().parent
CSV_FILE = BASE / "prices.csv"
CHART_FILE = BASE / "index.html"
HEADER = ["abgefragt", "ziel", "flugdatum", "airline", "abflug", "ankunft", "preis_eur"]
ZIELE = {
    "BER": "Berlin", "HAM": "Hamburg", "HAJ": "Hannover", "NUE": "Nürnberg",
    "CGN": "Köln/Bonn", "LEJ": "Leipzig", "MUC": "München",
}
DATES = ["2026-11-26", "2026-11-27", "2026-11-28", "2026-11-29", "2026-11-30"]
URL = ("https://www.google.com/travel/flights?q=Flights%20from%20FUE%20to%20{ziel}%20on%20{d}"
       "%20one%20way%20nonstop&hl=de&curr=EUR&gl=DE")
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/130.0 Safari/537.36",
    "Cookie": "SOCS=CAESEwgDEgk0ODE3Nzk3MjQaAmVuIAEaBgiA_LyaBg; CONSENT=YES+",
    "Accept-Language": "de-DE,de;q=0.9",
}
FLIGHT_RE = re.compile(
    r'aria-label="Ab ([\d.]+) Euro\..*?Nonstop-Flug mit ([^.]+)\. Abflug .*?, (\d{1,2}:\d{2}) '
    r'und Ankunft .*?, (\d{1,2}:\d{2})\.')


def fetch(ziel, date, attempts=2):
    """Google liefert nicht bei jedem Aufruf alle Flüge, daher mehrfach abfragen und vereinen."""
    flights = {}
    for i in range(attempts):
        if i:
            time.sleep(1)
        req = urllib.request.Request(URL.format(ziel=ziel, d=date), headers=HEADERS)
        with urllib.request.urlopen(req, timeout=60) as r:
            page = html.unescape(r.read().decode("utf-8", "replace"))
        for price, airline, dep, arr in FLIGHT_RE.findall(page):
            flights.setdefault((airline.strip(), dep, arr), int(price.replace(".", "")))
    return flights


def migrate_csv():
    """Alte Dateien ohne Spalte 'ziel' stammen aus der reinen Berlin-Abfrage."""
    if not CSV_FILE.exists():
        return
    with CSV_FILE.open(newline="") as f:
        rows = list(csv.reader(f))
    if not rows or "ziel" in rows[0]:
        return
    with CSV_FILE.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(HEADER)
        for r in rows[1:]:
            w.writerow([r[0], "BER"] + r[1:])


def log_prices():
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    new = not CSV_FILE.exists()
    with CSV_FILE.open("a", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(HEADER)
        for ziel in ZIELE:
            for date in DATES:
                try:
                    flights = fetch(ziel, date)
                except Exception as e:
                    print(f"{ts} {ziel} {date}: Fehler {e}")
                    continue
                for (airline, dep, arr), price in sorted(flights.items()):
                    w.writerow([ts, ziel, date, airline, dep, arr, price])
                print(f"{ts} {ziel} {date}: {len(flights)} Nonstop-Flüge")
                time.sleep(1)


def build_chart():
    series = {z: {} for z in ZIELE}
    with CSV_FILE.open() as f:
        for row in csv.DictReader(f):
            dt = datetime.strptime(row["flugdatum"], "%Y-%m-%d")
            d = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"][dt.weekday()] + dt.strftime(" %d.%m.")
            label = f'{d} {row["abflug"]} {row["airline"]}'
            series.setdefault(row["ziel"], {}).setdefault(label, []).append(
                {"x": row["abgefragt"], "y": int(row["preis_eur"])})
    CHART_FILE.write_text(TEMPLATE.replace("__DATA__", json.dumps(series, ensure_ascii=False))
                          .replace("__NAMES__", json.dumps(ZIELE, ensure_ascii=False))
                          .replace("__UPDATED__", datetime.now().strftime("%d.%m.%Y %H:%M")))


TEMPLATE = """<!doctype html>
<html lang="de"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="refresh" content="600">
<title>Flugpreise ab FUE</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/chartjs-adapter-date-fns@3.0.0/dist/chartjs-adapter-date-fns.bundle.min.js"></script>
<style>
body{font-family:-apple-system,system-ui,sans-serif;margin:0;padding:24px;background:#fafafa;color:#222}
h1{font-size:20px;margin:0 0 4px} p{color:#666;margin:0 0 16px;font-size:14px}
.tabs{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:12px}
.tabs button{border:1px solid #ccc;background:#fff;border-radius:999px;padding:6px 14px;font-size:14px;cursor:pointer}
.tabs button.on{background:#222;color:#fff;border-color:#222}
.tabs button small{color:#888;margin-left:4px} .tabs button.on small{color:#bbb}
.wrap{background:#fff;border-radius:12px;padding:16px;box-shadow:0 1px 3px #0001;height:65vh}
.empty{display:flex;align-items:center;justify-content:center;color:#888}
table{border-collapse:collapse;margin-top:20px;font-size:14px;background:#fff}
td,th{padding:6px 12px;border-bottom:1px solid #eee;text-align:left} td.n{text-align:right}
.down{color:#1a7f37}.up{color:#c62828}
</style></head><body>
<h1>Nonstop-Flüge ab Fuerteventura (26.–30.11.2026)</h1>
<p>Stand: __UPDATED__ · Preise einfache Strecke, 1 Erwachsener, Quelle Google Flüge</p>
<div class="tabs" id="tabs"></div>
<div class="wrap" id="wrap"><canvas id="c"></canvas></div>
<table id="t"></table>
<script>
const data = __DATA__, names = __NAMES__;
const colors = ['#e6194b','#3cb44b','#4363d8','#f58231','#911eb4','#42d4f4','#f032e6','#9a6324','#000075','#808000','#469990','#dcbeff'];
const tabs = ['ALL', ...Object.keys(names)];
let chart, cur = 'ALL';
try { const s = localStorage.getItem('ziel'); if (tabs.includes(s)) cur = s; } catch (e) {}

// Übersicht: günstigster Preis je Ziel und Abfragezeitpunkt
function overview() {
  const out = {};
  for (const [z, fl] of Object.entries(data)) {
    const m = {};
    for (const pts of Object.values(fl)) for (const p of pts) m[p.x] = Math.min(m[p.x] ?? Infinity, p.y);
    const pts = Object.entries(m).sort().map(([x, y]) => ({x, y}));
    if (pts.length) out[names[z] + ' (' + z + ')'] = pts;
  }
  return out;
}
function cheapest(z) {
  let best = Infinity;
  for (const pts of Object.values(data[z] || {})) best = Math.min(best, pts.at(-1).y);
  return best;
}
function render() {
  try { localStorage.setItem('ziel', cur); } catch (e) {}
  document.getElementById('tabs').innerHTML = tabs.map(z => {
    const label = z === 'ALL' ? 'Übersicht' : names[z];
    const c = z === 'ALL' ? Infinity : cheapest(z);
    return `<button class="${z === cur ? 'on' : ''}" data-z="${z}">${label}${isFinite(c) ? `<small>ab ${c} €</small>` : ''}</button>`;
  }).join('');
  document.querySelectorAll('#tabs button').forEach(b => b.onclick = () => { cur = b.dataset.z; render(); });
  const series = cur === 'ALL' ? overview() : (data[cur] || {});
  if (chart) chart.destroy();
  const wrap = document.getElementById('wrap');
  if (!Object.keys(series).length) {
    wrap.className = 'wrap empty'; wrap.innerHTML = 'Keine Nonstop-Flüge gefunden';
  } else {
    wrap.className = 'wrap'; wrap.innerHTML = '<canvas id="c"></canvas>';
    const ds = Object.entries(series).map(([k, v], i) => ({label: k, data: v.map(p => ({x: p.x.replace(' ', 'T'), y: p.y})),
      borderColor: colors[i % colors.length], backgroundColor: colors[i % colors.length], tension: .2, pointRadius: 2}));
    chart = new Chart(document.getElementById('c'), {type: 'line', data: {datasets: ds}, options: {maintainAspectRatio: false,
      interaction: {mode: 'nearest', intersect: false},
      scales: {x: {type: 'time', time: {unit: 'hour', displayFormats: {hour: 'dd.MM. HH:mm'}}}, y: {title: {display: true, text: '€'}}},
      plugins: {tooltip: {callbacks: {label: c => c.dataset.label + ': ' + c.parsed.y + ' €'}}}}});
  }
  const t = document.getElementById('t');
  t.innerHTML = `<tr><th>${cur === 'ALL' ? 'Ziel (günstigster Flug)' : 'Flug'}</th><th>Aktuell</th><th>Start</th><th>Min</th><th>Max</th></tr>`;
  for (const [k, v] of Object.entries(series)) {
    const ys = v.map(p => p.y), now = ys.at(-1), st = ys[0];
    const cls = now < st ? 'down' : now > st ? 'up' : '';
    t.insertAdjacentHTML('beforeend', `<tr><td>${k}</td><td class="n ${cls}">${now} €</td><td class="n">${st} €</td><td class="n">${Math.min(...ys)} €</td><td class="n">${Math.max(...ys)} €</td></tr>`);
  }
}
render();
</script></body></html>"""

if __name__ == "__main__":
    migrate_csv()
    log_prices()
    build_chart()
