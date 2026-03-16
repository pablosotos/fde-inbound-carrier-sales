from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from .call_log_service import read_all_logs

router = APIRouter()


def _aggregate(logs: list[dict]) -> dict:
    total = len(logs)
    if total == 0:
        return {
            "total_calls": 0,
            "deal_rate": 0,
            "avg_rate_delta": 0,
            "avg_neg_rounds": 0,
            "outcomes": {},
            "sentiments": {},
            "routes": [],
            "rate_comparison": [],
        }

    deals = [r for r in logs if str(r.get("deal_reached", "")).lower() == "true"]
    deal_rate = round(len(deals) / total * 100, 1)

    deltas = []
    for r in logs:
        try:
            deltas.append(float(r["rate_delta"]))
        except (ValueError, TypeError, KeyError):
            pass
    avg_delta = round(sum(deltas) / len(deltas), 0) if deltas else 0

    rounds = []
    for r in logs:
        try:
            rounds.append(float(r["neg_rounds"]))
        except (ValueError, TypeError, KeyError):
            pass
    avg_rounds = round(sum(rounds) / len(rounds), 1) if rounds else 0

    outcomes: dict[str, int] = {}
    for r in logs:
        o = r.get("call_outcome") or "unknown"
        outcomes[o] = outcomes.get(o, 0) + 1

    sentiments: dict[str, int] = {}
    for r in logs:
        s = r.get("carrier_sentiment") or "unknown"
        sentiments[s] = sentiments.get(s, 0) + 1

    route_counts: dict[str, int] = {}
    for r in logs:
        orig = r.get("origin", "?")
        dest = r.get("destination", "?")
        if orig and dest:
            key = f"{orig} → {dest}"
            route_counts[key] = route_counts.get(key, 0) + 1
    top_routes = sorted(route_counts.items(), key=lambda x: x[1], reverse=True)[:6]

    rate_comparison = []
    for r in logs:
        try:
            rate_comparison.append({
                "carrier": (r.get("carrier_name") or "?")[:20],
                "loadboard": float(r["loadboard_rate"]),
                "agreed": float(r["agreed_rate"]),
            })
        except (ValueError, TypeError, KeyError):
            pass

    return {
        "total_calls": total,
        "deal_rate": deal_rate,
        "avg_rate_delta": avg_delta,
        "avg_neg_rounds": avg_rounds,
        "outcomes": outcomes,
        "sentiments": sentiments,
        "routes": [{"route": k, "count": v} for k, v in top_routes],
        "rate_comparison": rate_comparison[-10:],
    }


@router.get("/dashboard/data")
def dashboard_data():
    logs = read_all_logs()
    return _aggregate(logs)


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard():
    return HTMLResponse(content=DASHBOARD_HTML)


DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>HappyRobot · Carrier Sales Dashboard</title>
<link href="https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=DM+Sans:wght@300;400;500;600;700&display=swap" rel="stylesheet"/>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
:root {
  --bg:      #f5f5f0;
  --surface: #ffffff;
  --surface2: #fafaf7;
  --border:  #e4e4dc;
  --border2: #d0d0c4;
  --green:   #16a34a;
  --green-l: #dcfce7;
  --red:     #dc2626;
  --red-l:   #fee2e2;
  --blue:    #2563eb;
  --blue-l:  #dbeafe;
  --purple:  #7c3aed;
  --purple-l:#ede9fe;
  --amber:   #d97706;
  --amber-l: #fef3c7;
  --text:    #1a1a18;
  --muted:   #78786e;
  --muted2:  #a8a89c;
  --mono:    'Space Mono', monospace;
  --sans:    'DM Sans', sans-serif;
  --radius:  10px;
  --shadow:  0 1px 3px rgba(0,0,0,.06), 0 1px 2px rgba(0,0,0,.04);
  --shadow-md: 0 4px 12px rgba(0,0,0,.08), 0 2px 4px rgba(0,0,0,.04);
}
body { background: var(--bg); color: var(--text); font-family: var(--sans); min-height: 100vh; }

/* ── HEADER ── */
header {
  background: var(--surface);
  border-bottom: 1px solid var(--border);
  position: sticky; top: 0; z-index: 50;
  box-shadow: var(--shadow);
}
.header-inner {
  max-width: 1400px; margin: 0 auto;
  display: flex; align-items: center; justify-content: space-between;
  padding: 0 36px; height: 64px;
}
.logo-wrap { display: flex; align-items: center; gap: 16px; }
.logo-img { height: 28px; width: auto; }
.divider { width: 1px; height: 24px; background: var(--border2); }
.header-tag {
  font-family: var(--mono);
  font-size: 10px;
  letter-spacing: .14em;
  text-transform: uppercase;
  color: var(--muted);
}
.header-right { display: flex; align-items: center; gap: 16px; }
#ts {
  font-family: var(--mono); font-size: 10px; color: var(--muted2);
}
.refresh-btn {
  font-family: var(--mono); font-size: 10px; letter-spacing: .1em;
  text-transform: uppercase; color: var(--muted);
  background: var(--surface2); border: 1px solid var(--border2);
  border-radius: 6px; padding: 6px 12px; cursor: pointer;
  transition: all .15s;
}
.refresh-btn:hover { background: var(--bg); color: var(--text); border-color: var(--border2); }

/* ── LAYOUT ── */
main {
  max-width: 1400px; margin: 0 auto;
  padding: 32px 36px 64px;
  opacity: 0; transition: opacity .4s ease;
}
main.show { opacity: 1; }

/* ── KPI ROW ── */
.kpi-row { display: grid; grid-template-columns: repeat(4,1fr); gap: 16px; margin-bottom: 24px; }
.kpi {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 24px 24px 20px;
  box-shadow: var(--shadow);
  position: relative;
  transition: box-shadow .2s, transform .2s;
}
.kpi:hover { box-shadow: var(--shadow-md); transform: translateY(-1px); }
.kpi-icon {
  display: inline-flex; align-items: center; justify-content: center;
  width: 36px; height: 36px; border-radius: 8px;
  font-size: 16px; margin-bottom: 14px;
}
.kpi.amber .kpi-icon { background: var(--amber-l); }
.kpi.green .kpi-icon { background: var(--green-l); }
.kpi.blue  .kpi-icon { background: var(--blue-l); }
.kpi.purple .kpi-icon { background: var(--purple-l); }
.kpi-label {
  font-size: 12px; font-weight: 500;
  color: var(--muted); margin-bottom: 6px; letter-spacing: .01em;
}
.kpi-val {
  font-family: var(--mono); font-size: 36px; font-weight: 700;
  line-height: 1; letter-spacing: -.02em;
}
.kpi.amber  .kpi-val { color: var(--amber); }
.kpi.green  .kpi-val { color: var(--green); }
.kpi.blue   .kpi-val { color: var(--blue); }
.kpi.purple .kpi-val { color: var(--purple); }
.kpi-sub { font-size: 12px; color: var(--muted2); margin-top: 8px; }

/* ── GRIDS ── */
.grid-3 { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 16px; margin-bottom: 16px; }
.grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 24px;
  box-shadow: var(--shadow);
}
.card-title {
  font-size: 12px; font-weight: 600; letter-spacing: .03em;
  color: var(--muted); text-transform: uppercase;
  margin-bottom: 20px; padding-bottom: 12px;
  border-bottom: 1px solid var(--border);
}
.card canvas { max-height: 220px; }

/* ── ROUTES TABLE ── */
.rtable { width: 100%; border-collapse: collapse; }
.rtable th {
  font-size: 11px; font-weight: 600; color: var(--muted2);
  text-align: left; padding-bottom: 10px;
  border-bottom: 1px solid var(--border);
  text-transform: uppercase; letter-spacing: .06em;
}
.rtable td {
  padding: 10px 0; border-bottom: 1px solid var(--border);
  font-size: 13px; color: var(--text); vertical-align: middle;
}
.rtable td:last-child {
  font-family: var(--mono); font-size: 12px;
  font-weight: 700; color: var(--blue);
  text-align: right; width: 40px;
}
.bar-wrap { display: flex; align-items: center; gap: 10px; }
.mini-bar {
  height: 4px; background: var(--blue);
  border-radius: 99px; opacity: .3; min-width: 4px;
}

/* ── LOADER ── */
#loader {
  position: fixed; inset: 0; z-index: 200;
  background: var(--bg);
  display: flex; flex-direction: column;
  align-items: center; justify-content: center; gap: 16px;
}
.spin {
  width: 32px; height: 32px;
  border: 2px solid var(--border2);
  border-top-color: var(--text);
  border-radius: 50%;
  animation: spin .7s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }
#loader p { font-size: 13px; color: var(--muted); }

@media (max-width: 960px) {
  .kpi-row { grid-template-columns: 1fr 1fr; }
  .grid-2, .grid-3 { grid-template-columns: 1fr; }
  .header-inner { padding: 0 20px; }
  main { padding: 20px 20px 48px; }
}
</style>
</head>
<body>

<div id="loader">
  <div class="spin"></div>
  <p>Loading carrier data…</p>
</div>

<header>
  <div class="header-inner">
    <div class="logo-wrap">
      <img class="logo-img" src="data:image/webp;base64,data:image/webp;base64,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" alt="HappyRobot"/>
      <div class="divider"></div>
      <span class="header-tag">Carrier Sales · Operations</span>
    </div>
    <div class="header-right">
      <span id="ts">—</span>
      <button class="refresh-btn" onclick="reload()">↻ Refresh</button>
    </div>
  </div>
</header>

<main id="main">
  <div class="kpi-row">
    <div class="kpi amber">
      <div class="kpi-icon">📞</div>
      <div class="kpi-label">Total Calls</div>
      <div class="kpi-val" id="k-total">—</div>
      <div class="kpi-sub">Inbound carrier calls logged</div>
    </div>
    <div class="kpi green">
      <div class="kpi-icon">✅</div>
      <div class="kpi-label">Close Rate</div>
      <div class="kpi-val" id="k-deal">—</div>
      <div class="kpi-sub">Loads successfully booked</div>
    </div>
    <div class="kpi blue">
      <div class="kpi-icon">💰</div>
      <div class="kpi-label">Avg Rate Delta</div>
      <div class="kpi-val" id="k-delta">—</div>
      <div class="kpi-sub">Agreed vs. loadboard rate</div>
    </div>
    <div class="kpi purple">
      <div class="kpi-icon">🔄</div>
      <div class="kpi-label">Avg Neg. Rounds</div>
      <div class="kpi-val" id="k-rounds">—</div>
      <div class="kpi-sub">Rounds needed to close</div>
    </div>
  </div>

  <div class="grid-3">
    <div class="card">
      <div class="card-title">Call Outcome Distribution</div>
      <canvas id="c-outcome"></canvas>
    </div>
    <div class="card">
      <div class="card-title">Carrier Sentiment</div>
      <canvas id="c-sentiment"></canvas>
    </div>
    <div class="card">
      <div class="card-title">Top Routes by Volume</div>
      <div id="routes-wrap"></div>
    </div>
  </div>

  <div class="grid-2">
    <div class="card">
      <div class="card-title">Loadboard Rate vs. Agreed Rate — last 10 calls</div>
      <canvas id="c-rates"></canvas>
    </div>
    <div class="card">
      <div class="card-title">Rate Delta per Call ($)</div>
      <canvas id="c-delta"></canvas>
    </div>
  </div>
</main>

<script>
const OUTCOME_COLORS = {
  load_booked:'#16a34a', negotiation_failed:'#dc2626',
  carrier_not_interested:'#ea580c', no_loads_available:'#2563eb',
  invalid_carrier:'#7c3aed', callback_requested:'#d97706',
  general_inquiry:'#94a3b8', unknown:'#cbd5e1'
};
const SENT_COLORS = { positive:'#16a34a', neutral:'#2563eb', negative:'#dc2626', unknown:'#cbd5e1' };

const CHART_BASE = {
  plugins: { legend: { labels: { color:'#78786e', font:{ family:"'DM Sans'", size:12 }, boxWidth:12, padding:14 } } },
  scales: {
    x: { ticks:{ color:'#a8a89c', font:{ family:"'Space Mono'", size:9 }, maxRotation:35, minRotation:20 }, grid:{ color:'#e4e4dc' } },
    y: { ticks:{ color:'#a8a89c', font:{ family:"'Space Mono'", size:9 }, callback: v => '$'+v }, grid:{ color:'#e4e4dc' } }
  }
};

function donut(id, labels, values, colors) {
  new Chart(document.getElementById(id), {
    type: 'doughnut',
    data: { labels, datasets: [{ data:values, backgroundColor:colors, borderColor:'#ffffff', borderWidth:3, hoverOffset:6 }] },
    options: { cutout:'65%', plugins:{ legend:{ position:'bottom', labels:{ color:'#78786e', font:{ family:"'DM Sans'", size:11 }, boxWidth:10, padding:12 } } } }
  });
}

function buildRoutes(routes) {
  const el = document.getElementById('routes-wrap');
  if (!routes.length) { el.innerHTML = '<p style="color:var(--muted2);font-size:13px;margin-top:8px">No data yet</p>'; return; }
  const max = routes[0].count;
  el.innerHTML = `<table class="rtable">
    <thead><tr><th>Route</th><th style="text-align:right">Calls</th></tr></thead>
    <tbody>${routes.map(r => `<tr>
      <td><div class="bar-wrap"><div class="mini-bar" style="width:${Math.round(r.count/max*100)}px"></div>${r.route}</div></td>
      <td>${r.count}</td></tr>`).join('')}
    </tbody></table>`;
}

async function load() {
  const d = await fetch('/dashboard/data').then(r => r.json());

  document.getElementById('k-total').textContent  = d.total_calls;
  document.getElementById('k-deal').textContent   = d.deal_rate + '%';
  document.getElementById('k-delta').textContent  = (d.avg_rate_delta >= 0 ? '+' : '') + '$' + d.avg_rate_delta;
  document.getElementById('k-rounds').textContent = d.avg_neg_rounds;
  document.getElementById('ts').textContent       = 'Updated ' + new Date().toLocaleTimeString();

  const outK = Object.keys(d.outcomes);
  donut('c-outcome', outK, outK.map(k => d.outcomes[k]), outK.map(k => OUTCOME_COLORS[k] || '#cbd5e1'));

  const sentK = Object.keys(d.sentiments);
  donut('c-sentiment', sentK, sentK.map(k => d.sentiments[k]), sentK.map(k => SENT_COLORS[k] || '#cbd5e1'));

  buildRoutes(d.routes);

  const rc = d.rate_comparison;
  new Chart(document.getElementById('c-rates'), {
    type: 'bar',
    data: { labels: rc.map(r => r.carrier), datasets: [
      { label:'Loadboard Rate', data:rc.map(r=>r.loadboard), backgroundColor:'rgba(37,99,235,.15)', borderColor:'#2563eb', borderWidth:1.5, borderRadius:4 },
      { label:'Agreed Rate',    data:rc.map(r=>r.agreed),    backgroundColor:'rgba(22,163,74,.15)',  borderColor:'#16a34a', borderWidth:1.5, borderRadius:4 }
    ]},
    options: { ...CHART_BASE, plugins:{ legend:CHART_BASE.plugins.legend }, scales: CHART_BASE.scales }
  });

  const deltas = rc.map(r => r.agreed - r.loadboard);
  new Chart(document.getElementById('c-delta'), {
    type: 'bar',
    data: { labels: rc.map(r => r.carrier), datasets: [{
      label:'Rate Delta ($)',
      data: deltas,
      backgroundColor: deltas.map(v => v>=0 ? 'rgba(22,163,74,.15)'  : 'rgba(220,38,38,.15)'),
      borderColor:     deltas.map(v => v>=0 ? '#16a34a' : '#dc2626'),
      borderWidth:1.5, borderRadius:4
    }]},
    options: { ...CHART_BASE, plugins:{ legend:{ display:false } }, scales: CHART_BASE.scales }
  });

  document.getElementById('loader').style.display = 'none';
  document.getElementById('main').classList.add('show');
}

function reload() { location.reload(); }

load();
</script>
</body>
</html>"""