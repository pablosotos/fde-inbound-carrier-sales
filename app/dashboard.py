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
<title>Carrier Sales · Ops Dashboard</title>
<link href="https://fonts.googleapis.com/css2?family=Space+Mono:ital,wght@0,400;0,700;1,400&family=DM+Sans:wght@300;400;500;700&display=swap" rel="stylesheet"/>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
:root {
  --bg:     #09090b;
  --s1:     #111115;
  --border: #27272e;
  --amber:  #f59e0b;
  --green:  #34d399;
  --red:    #f87171;
  --blue:   #60a5fa;
  --purple: #a78bfa;
  --text:   #e4e4eb;
  --muted:  #52525e;
  --mono:   'Space Mono', monospace;
  --sans:   'DM Sans', sans-serif;
}
body { background: var(--bg); color: var(--text); font-family: var(--sans); min-height: 100vh; overflow-x: hidden; }

header {
  position: sticky; top: 0; z-index: 50;
  display: flex; align-items: center; justify-content: space-between;
  padding: 0 36px; height: 60px;
  background: rgba(9,9,11,.9);
  backdrop-filter: blur(12px);
  border-bottom: 1px solid var(--border);
}
.brand { display: flex; align-items: center; gap: 12px; }
.hex {
  width: 28px; height: 28px; background: var(--amber); flex-shrink: 0;
  clip-path: polygon(50% 0%,100% 25%,100% 75%,50% 100%,0% 75%,0% 25%);
}
.brand-text { font-family: var(--mono); font-size: 11px; letter-spacing: .16em; text-transform: uppercase; color: var(--amber); line-height: 1.5; }
.brand-text small { display: block; color: var(--muted); font-size: 9px; }
#ts { font-family: var(--mono); font-size: 10px; color: var(--muted); }

main { padding: 32px 36px 64px; max-width: 1400px; margin: 0 auto; opacity: 0; transition: opacity .5s; }
main.show { opacity: 1; }

.kpi-row { display: grid; grid-template-columns: repeat(4,1fr); gap: 14px; margin-bottom: 22px; }
.kpi {
  background: var(--s1); border: 1px solid var(--border); border-radius: 6px;
  padding: 22px 22px 18px; position: relative; overflow: hidden;
  transition: border-color .2s, transform .2s; cursor: default;
}
.kpi:hover { border-color: var(--amber); transform: translateY(-2px); }
.kpi::after { content:''; position: absolute; top:0; left:0; right:0; height:2px; background: var(--amber); }
.kpi.g::after { background: var(--green); } .kpi.b::after { background: var(--blue); } .kpi.p::after { background: var(--purple); }
.kpi-label { font-family: var(--mono); font-size: 9px; letter-spacing: .18em; text-transform: uppercase; color: var(--muted); margin-bottom: 10px; }
.kpi-val { font-family: var(--mono); font-size: 40px; font-weight: 700; color: var(--amber); line-height: 1; }
.kpi.g .kpi-val { color: var(--green); } .kpi.b .kpi-val { color: var(--blue); } .kpi.p .kpi-val { color: var(--purple); }
.kpi-sub { font-size: 11px; color: var(--muted); margin-top: 8px; }

.grid-3 { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 14px; margin-bottom: 14px; }
.grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
.card { background: var(--s1); border: 1px solid var(--border); border-radius: 6px; padding: 22px; }
.card-title { font-family: var(--mono); font-size: 9px; letter-spacing: .18em; text-transform: uppercase; color: var(--muted); margin-bottom: 18px; }
.card canvas { max-height: 210px; }

.rtable { width: 100%; border-collapse: collapse; }
.rtable th { font-family: var(--mono); font-size: 9px; letter-spacing: .14em; text-transform: uppercase; color: var(--muted); font-weight: 400; text-align: left; padding-bottom: 10px; border-bottom: 1px solid var(--border); }
.rtable td { padding: 9px 0; border-bottom: 1px solid var(--border); font-size: 13px; vertical-align: middle; }
.rtable td:last-child { font-family: var(--mono); font-size: 12px; color: var(--amber); text-align: right; width: 40px; }
.bar-wrap { display: flex; align-items: center; gap: 10px; }
.mini-bar { height: 3px; background: var(--amber); border-radius: 99px; opacity: .5; min-width: 4px; }

#loader { position: fixed; inset: 0; z-index: 200; background: var(--bg); display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 18px; }
.spin { width: 36px; height: 36px; border: 2px solid var(--border); border-top-color: var(--amber); border-radius: 50%; animation: spin .7s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
#loader p { font-family: var(--mono); font-size: 10px; color: var(--muted); letter-spacing: .1em; }

@media (max-width: 960px) {
  .kpi-row { grid-template-columns: 1fr 1fr; }
  .grid-2, .grid-3 { grid-template-columns: 1fr; }
}
</style>
</head>
<body>

<div id="loader"><div class="spin"></div><p>Loading call data…</p></div>

<header>
  <div class="brand">
    <div class="hex"></div>
    <div class="brand-text">Swift Cargo Brokers<small>Carrier Sales · Operations</small></div>
  </div>
  <span id="ts">—</span>
</header>

<main id="main">
  <div class="kpi-row">
    <div class="kpi">
      <div class="kpi-label">Total Calls</div>
      <div class="kpi-val" id="k-total">—</div>
      <div class="kpi-sub">Inbound carrier calls</div>
    </div>
    <div class="kpi g">
      <div class="kpi-label">Close Rate</div>
      <div class="kpi-val" id="k-deal">—</div>
      <div class="kpi-sub">Loads successfully booked</div>
    </div>
    <div class="kpi b">
      <div class="kpi-label">Avg Rate Delta</div>
      <div class="kpi-val" id="k-delta">—</div>
      <div class="kpi-sub">Agreed vs. loadboard ($)</div>
    </div>
    <div class="kpi p">
      <div class="kpi-label">Avg Neg. Rounds</div>
      <div class="kpi-val" id="k-rounds">—</div>
      <div class="kpi-sub">Rounds to close a deal</div>
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
  load_booked:'#34d399', negotiation_failed:'#f87171',
  carrier_not_interested:'#fb923c', no_loads_available:'#60a5fa',
  invalid_carrier:'#a78bfa', callback_requested:'#facc15',
  general_inquiry:'#94a3b8', unknown:'#3f3f46'
};
const SENT_COLORS = { positive:'#34d399', neutral:'#60a5fa', negative:'#f87171', unknown:'#3f3f46' };
const FONT = { mono: "'Space Mono'", sans: "'DM Sans'" };

function donut(id, labels, values, colors) {
  new Chart(document.getElementById(id), {
    type: 'doughnut',
    data: { labels, datasets: [{ data: values, backgroundColor: colors, borderColor: '#09090b', borderWidth: 3, hoverOffset: 6 }] },
    options: { cutout: '68%', plugins: { legend: { position:'bottom', labels:{ color:'#94a3b8', font:{ family: FONT.sans, size:11 }, boxWidth:10, padding:12 } } } }
  });
}

function buildRoutes(routes) {
  const el = document.getElementById('routes-wrap');
  if (!routes.length) { el.innerHTML = '<p style="color:var(--muted);font-size:12px;margin-top:8px">No data yet</p>'; return; }
  const max = routes[0].count;
  el.innerHTML = `<table class="rtable">
    <thead><tr><th>Route</th><th style="text-align:right">Calls</th></tr></thead>
    <tbody>${routes.map(r => `<tr>
      <td><div class="bar-wrap"><div class="mini-bar" style="width:${Math.round(r.count/max*110)}px"></div>${r.route}</div></td>
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
  donut('c-outcome', outK, outK.map(k => d.outcomes[k]), outK.map(k => OUTCOME_COLORS[k] || '#52525e'));

  const sentK = Object.keys(d.sentiments);
  donut('c-sentiment', sentK, sentK.map(k => d.sentiments[k]), sentK.map(k => SENT_COLORS[k] || '#52525e'));

  buildRoutes(d.routes);

  const rc = d.rate_comparison;
  const axisOpts = {
    x: { ticks:{ color:'#52525e', font:{ family: FONT.mono, size:9 }, maxRotation:35, minRotation:20 }, grid:{ color:'#18181d' } },
    y: { ticks:{ color:'#52525e', font:{ family: FONT.mono, size:9 }, callback: v => '$'+v }, grid:{ color:'#27272e' } }
  };

  new Chart(document.getElementById('c-rates'), {
    type: 'bar',
    data: { labels: rc.map(r => r.carrier), datasets: [
      { label:'Loadboard Rate', data: rc.map(r=>r.loadboard), backgroundColor:'rgba(96,165,250,.55)', borderColor:'#60a5fa', borderWidth:1, borderRadius:3 },
      { label:'Agreed Rate',    data: rc.map(r=>r.agreed),    backgroundColor:'rgba(52,211,153,.55)', borderColor:'#34d399', borderWidth:1, borderRadius:3 }
    ]},
    options: { plugins:{ legend:{ labels:{ color:'#94a3b8', font:{ family: FONT.sans, size:12 }, boxWidth:12, padding:14 } } }, scales: axisOpts }
  });

  const deltas = rc.map(r => r.agreed - r.loadboard);
  new Chart(document.getElementById('c-delta'), {
    type: 'bar',
    data: { labels: rc.map(r => r.carrier), datasets: [{
      label:'Rate Delta ($)',
      data: deltas,
      backgroundColor: deltas.map(v => v>=0 ? 'rgba(245,158,11,.55)' : 'rgba(248,113,113,.55)'),
      borderColor:      deltas.map(v => v>=0 ? '#f59e0b' : '#f87171'),
      borderWidth:1, borderRadius:3
    }]},
    options: { plugins:{ legend:{ display:false } }, scales: axisOpts }
  });

  document.getElementById('loader').style.display = 'none';
  document.getElementById('main').classList.add('show');
}

load();
</script>
</body>
</html>"""