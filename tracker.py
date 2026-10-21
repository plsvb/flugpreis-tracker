#!/usr/bin/env python3
"""Fragt Google Flüge nach Nonstop-Preisen FUE -> BER ab, loggt sie in prices.csv
und erzeugt chart.html mit der Preisentwicklung."""
import csv
import html
import json
import re
import urllib.request
from datetime import datetime
from pathlib import Path

BASE = Path(__file__).resolve().parent
CSV_FILE = BASE / "prices.csv"
CHART_FILE = BASE / "index.html"
DATES = ["2026-11-26", "2026-11-27", "2026-11-28", "2026-11-29", "2026-11-30"]
URL = ("https://www.google.com/travel/flights?q=Flights%20from%20FUE%20to%20BER%20on%20{d}"
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


def fetch(date):
    req = urllib.request.Request(URL.format(d=date), headers=HEADERS)
    with urllib.request.urlopen(req, timeout=60) as r:
        page = html.unescape(r.read().decode("utf-8", "replace"))
    flights = {}
    for price, airline, dep, arr in FLIGHT_RE.findall(page):
        flights[(airline.strip(), dep, arr)] = int(price.replace(".", ""))
    return flights


def log_prices():
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    new = not CSV_FILE.exists()
    with CSV_FILE.open("a", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["abgefragt", "flugdatum", "airline", "abflug", "ankunft", "preis_eur"])
        for date in DATES:
            try:
                flights = fetch(date)
            except Exception as e:
                print(f"{ts} {date}: Fehler {e}")
                continue
            for (airline, dep, arr), price in sorted(flights.items()):
                w.writerow([ts, date, airline, dep, arr, price])
            print(f"{ts} {date}: {len(flights)} Nonstop-Flüge")


def build_chart():
    series = {}
    with CSV_FILE.open() as f:
        for row in csv.DictReader(f):
            dt = datetime.strptime(row["flugdatum"], "%Y-%m-%d")
            d = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"][dt.weekday()] + dt.strftime(" %d.%m.")
            label = f'{d} {row["abflug"]} {row["airline"]}'
            series.setdefault(label, []).append({"x": row["abgefragt"], "y": int(row["preis_eur"])})
    CHART_FILE.write_text(TEMPLATE.replace("__DATA__", json.dumps(series, ensure_ascii=False))
                          .replace("__UPDATED__", datetime.now().strftime("%d.%m.%Y %H:%M")))


TEMPLATE = """<!doctype html>
<html lang="de"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="refresh" content="600">
<title>Flugpreise FUE → BER</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/chartjs-adapter-date-fns@3.0.0/dist/chartjs-adapter-date-fns.bundle.min.js"></script>
<style>
body{font-family:-apple-system,system-ui,sans-serif;margin:0;padding:24px;background:#fafafa;color:#222}
h1{font-size:20px;margin:0 0 4px} p{color:#666;margin:0 0 16px;font-size:14px}
.wrap{background:#fff;border-radius:12px;padding:16px;box-shadow:0 1px 3px #0001;height:70vh}
table{border-collapse:collapse;margin-top:20px;font-size:14px;background:#fff}
td,th{padding:6px 12px;border-bottom:1px solid #eee;text-align:left} td.n{text-align:right}
.down{color:#1a7f37}.up{color:#c62828}
</style></head><body>
<h1>Nonstop-Flüge Fuerteventura → Berlin (26.–30.11.2026)</h1>
<p>Stand: __UPDATED__ · Preise einfache Strecke, 1 Erwachsener, Quelle Google Flüge</p>
<div class="wrap"><canvas id="c"></canvas></div>
<table id="t"><tr><th>Flug</th><th>Aktuell</th><th>Start</th><th>Min</th><th>Max</th></tr></table>
<script>
const data = __DATA__;
const colors = ['#e6194b','#3cb44b','#4363d8','#f58231','#911eb4','#42d4f4','#f032e6','#9a6324','#000075','#808000'];
const ds = Object.entries(data).map(([k,v],i)=>({label:k,data:v.map(p=>({x:p.x.replace(' ','T'),y:p.y})),
  borderColor:colors[i%colors.length],backgroundColor:colors[i%colors.length],tension:.2,pointRadius:2}));
new Chart(document.getElementById('c'),{type:'line',data:{datasets:ds},options:{maintainAspectRatio:false,
  interaction:{mode:'nearest',intersect:false},
  scales:{x:{type:'time',time:{unit:'hour',displayFormats:{hour:'dd.MM. HH:mm'}}},y:{title:{display:true,text:'€'}}},
  plugins:{tooltip:{callbacks:{label:c=>c.dataset.label+': '+c.parsed.y+' €'}}}}});
const t=document.getElementById('t');
for(const [k,v] of Object.entries(data)){const ys=v.map(p=>p.y),cur=ys.at(-1),st=ys[0];
  const cls=cur<st?'down':cur>st?'up':'';
  t.insertAdjacentHTML('beforeend',`<tr><td>${k}</td><td class="n ${cls}">${cur} €</td><td class="n">${st} €</td><td class="n">${Math.min(...ys)} €</td><td class="n">${Math.max(...ys)} €</td></tr>`);}
</script></body></html>"""

if __name__ == "__main__":
    log_prices()
    build_chart()
