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
            key = f"{orig} -> {dest}"
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


DASHBOARD_HTML = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>HappyRobot - Carrier Sales Dashboard</title>
<link href="https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=DM+Sans:wght@300;400;500;600;700&display=swap" rel="stylesheet"/>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
:root {
  --bg:       #f5f5f0;
  --surface:  #ffffff;
  --surface2: #fafaf7;
  --border:   #e4e4dc;
  --border2:  #d0d0c4;
  --green:    #16a34a;
  --green-l:  #dcfce7;
  --red:      #dc2626;
  --red-l:    #fee2e2;
  --blue:     #2563eb;
  --blue-l:   #dbeafe;
  --purple:   #7c3aed;
  --purple-l: #ede9fe;
  --amber:    #d97706;
  --amber-l:  #fef3c7;
  --text:     #1a1a18;
  --muted:    #78786e;
  --muted2:   #a8a89c;
  --radius:   10px;
  --shadow:   0 1px 3px rgba(0,0,0,.06), 0 1px 2px rgba(0,0,0,.04);
  --shadow-md:0 4px 12px rgba(0,0,0,.08), 0 2px 4px rgba(0,0,0,.04);
}
body { background: var(--bg); color: var(--text); font-family: "DM Sans", sans-serif; min-height: 100vh; }

/* HEADER */
header {
  background: var(--surface); border-bottom: 1px solid var(--border);
  position: sticky; top: 0; z-index: 50; box-shadow: var(--shadow);
}
.header-inner {
  max-width: 1400px; margin: 0 auto;
  display: flex; align-items: center; justify-content: space-between;
  padding: 0 36px; height: 64px;
}
.logo-wrap { display: flex; align-items: center; gap: 16px; }
.logo-img { height: 30px; width: auto; display: block; }
.divider { width: 1px; height: 24px; background: var(--border2); }
.header-tag { font-family: "Space Mono", monospace; font-size: 10px; letter-spacing: .14em; text-transform: uppercase; color: var(--muted); }
.header-right { display: flex; align-items: center; gap: 16px; }
#ts { font-family: "Space Mono", monospace; font-size: 10px; color: var(--muted2); }
.refresh-btn {
  font-family: "Space Mono", monospace; font-size: 10px; letter-spacing: .1em;
  text-transform: uppercase; color: var(--muted);
  background: var(--surface2); border: 1px solid var(--border2);
  border-radius: 6px; padding: 6px 12px; cursor: pointer; transition: all .15s;
}
.refresh-btn:hover { background: var(--bg); color: var(--text); }

/* MAIN */
main { max-width: 1400px; margin: 0 auto; padding: 32px 36px 64px; opacity: 0; transition: opacity .4s ease; }
main.show { opacity: 1; }

/* KPI */
.kpi-row { display: grid; grid-template-columns: repeat(4,1fr); gap: 16px; margin-bottom: 24px; }
.kpi {
  background: var(--surface); border: 1px solid var(--border);
  border-radius: var(--radius); padding: 24px 24px 20px;
  box-shadow: var(--shadow); transition: box-shadow .2s, transform .2s;
}
.kpi:hover { box-shadow: var(--shadow-md); transform: translateY(-1px); }
.kpi-icon {
  width: 36px; height: 36px; border-radius: 8px;
  margin-bottom: 14px; display: flex; align-items: center; justify-content: center;
}
.kpi-icon svg { width: 18px; height: 18px; }
.kpi.amber .kpi-icon { background: var(--amber-l); }
.kpi.green .kpi-icon { background: var(--green-l); }
.kpi.blue  .kpi-icon { background: var(--blue-l); }
.kpi.purple .kpi-icon { background: var(--purple-l); }
.kpi-label { font-size: 12px; font-weight: 500; color: var(--muted); margin-bottom: 6px; }
.kpi-val { font-family: "Space Mono", monospace; font-size: 36px; font-weight: 700; line-height: 1; }
.kpi.amber  .kpi-val { color: var(--amber); }
.kpi.green  .kpi-val { color: var(--green); }
.kpi.blue   .kpi-val { color: var(--blue); }
.kpi.purple .kpi-val { color: var(--purple); }
.kpi-sub { font-size: 12px; color: var(--muted2); margin-top: 8px; }

/* GRIDS */
.grid-3 { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 16px; margin-bottom: 16px; }
.grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.card { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius); padding: 24px; box-shadow: var(--shadow); }
.card-title {
  font-size: 12px; font-weight: 600; letter-spacing: .03em; color: var(--muted);
  text-transform: uppercase; margin-bottom: 20px; padding-bottom: 12px; border-bottom: 1px solid var(--border);
}
.card canvas { max-height: 220px; }

/* ROUTES */
.rtable { width: 100%; border-collapse: collapse; }
.rtable th { font-size: 11px; font-weight: 600; color: var(--muted2); text-align: left; padding-bottom: 10px; border-bottom: 1px solid var(--border); text-transform: uppercase; letter-spacing: .06em; }
.rtable td { padding: 10px 0; border-bottom: 1px solid var(--border); font-size: 13px; vertical-align: middle; }
.rtable td:last-child { font-family: "Space Mono", monospace; font-size: 12px; font-weight: 700; color: var(--blue); text-align: right; width: 40px; }
.bar-wrap { display: flex; align-items: center; gap: 10px; }
.mini-bar { height: 4px; background: var(--blue); border-radius: 99px; opacity: .25; min-width: 4px; }

/* LOADER */
#loader { position: fixed; inset: 0; z-index: 200; background: var(--bg); display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 16px; }
.spin { width: 32px; height: 32px; border: 2px solid var(--border2); border-top-color: var(--text); border-radius: 50%; animation: spin .7s linear infinite; }
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

<div id="loader"><div class="spin"></div><p>Loading carrier data...</p></div>

<header>
  <div class="header-inner">
    <div class="logo-wrap">
      <img class="logo-img" src="/static/happy.png" alt="HappyRobot"/>
      <div class="divider"></div>
      <span class="header-tag">Swift Cargo Brokers &middot; Carrier Sales &middot; Operations</span>
    </div>
    <div class="header-right">
      <span id="ts"></span>
      <button class="refresh-btn" onclick="location.reload()">&#8635; Refresh</button>
    </div>
  </div>
</header>

<main id="main">
  <div class="kpi-row">

    <div class="kpi amber">
      <div class="kpi-icon">
        <svg viewBox="0 0 24 24" fill="none" stroke="#d97706" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M22 16.92v3a2 2 0 01-2.18 2 19.79 19.79 0 01-8.63-3.07A19.5 19.5 0 013.07 9.81 19.79 19.79 0 01.1 1.18 2 2 0 012.11 0h3a2 2 0 012 1.72 12.84 12.84 0 00.7 2.81 2 2 0 01-.45 2.11L6.09 7.91a16 16 0 006 6l1.27-1.27a2 2 0 012.11-.45 12.84 12.84 0 002.81.7A2 2 0 0122 14.92z"/>
        </svg>
      </div>
      <div class="kpi-label">Total Calls</div>
      <div class="kpi-val" id="k-total">-</div>
      <div class="kpi-sub">Inbound carrier calls logged</div>
    </div>

    <div class="kpi green">
      <div class="kpi-icon">
        <svg viewBox="0 0 24 24" fill="none" stroke="#16a34a" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <polyline points="20 6 9 17 4 12"/>
        </svg>
      </div>
      <div class="kpi-label">Close Rate</div>
      <div class="kpi-val" id="k-deal">-</div>
      <div class="kpi-sub">Loads successfully booked</div>
    </div>

    <div class="kpi blue">
      <div class="kpi-icon">
        <svg viewBox="0 0 24 24" fill="none" stroke="#2563eb" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <line x1="12" y1="1" x2="12" y2="23"/><path d="M17 5H9.5a3.5 3.5 0 000 7h5a3.5 3.5 0 010 7H6"/>
        </svg>
      </div>
      <div class="kpi-label">Avg Rate Delta</div>
      <div class="kpi-val" id="k-delta">-</div>
      <div class="kpi-sub">Agreed vs. loadboard rate</div>
    </div>

    <div class="kpi purple">
      <div class="kpi-icon">
        <svg viewBox="0 0 24 24" fill="none" stroke="#7c3aed" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <polyline points="17 1 21 5 17 9"/><path d="M3 11V9a4 4 0 014-4h14"/><polyline points="7 23 3 19 7 15"/><path d="M21 13v2a4 4 0 01-4 4H3"/>
        </svg>
      </div>
      <div class="kpi-label">Avg Neg. Rounds</div>
      <div class="kpi-val" id="k-rounds">-</div>
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
      <div class="card-title">Loadboard Rate vs. Agreed Rate &mdash; last 10 calls</div>
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
  load_booked:"#16a34a", negotiation_failed:"#dc2626",
  carrier_not_interested:"#ea580c", no_loads_available:"#2563eb",
  invalid_carrier:"#7c3aed", callback_requested:"#d97706",
  general_inquiry:"#94a3b8", unknown:"#cbd5e1"
};
const SENT_COLORS = { positive:"#16a34a", neutral:"#2563eb", negative:"#dc2626", unknown:"#cbd5e1" };
const AXIS = {
  x:{ ticks:{ color:"#a8a89c", font:{ family:"Space Mono", size:9 }, maxRotation:35, minRotation:20 }, grid:{ color:"#e4e4dc" } },
  y:{ ticks:{ color:"#a8a89c", font:{ family:"Space Mono", size:9 }, callback:v=>"$"+v }, grid:{ color:"#e4e4dc" } }
};
const LEG = { labels:{ color:"#78786e", font:{ family:"DM Sans", size:12 }, boxWidth:12, padding:14 } };

function donut(id, labels, values, colors) {
  new Chart(document.getElementById(id), {
    type:"doughnut",
    data:{ labels, datasets:[{ data:values, backgroundColor:colors, borderColor:"#ffffff", borderWidth:3, hoverOffset:6 }] },
    options:{ cutout:"65%", plugins:{ legend:{ position:"bottom", labels:{ color:"#78786e", font:{ family:"DM Sans", size:11 }, boxWidth:10, padding:12 } } } }
  });
}

function buildRoutes(routes) {
  const el = document.getElementById("routes-wrap");
  if (!routes.length) { el.innerHTML = "<p style='color:#a8a89c;font-size:13px;margin-top:8px'>No data yet</p>"; return; }
  const max = routes[0].count;
  el.innerHTML = "<table class='rtable'><thead><tr><th>Route</th><th style='text-align:right'>Calls</th></tr></thead><tbody>"
    + routes.map(r => "<tr><td><div class='bar-wrap'><div class='mini-bar' style='width:"
      + Math.round(r.count/max*100) + "px'></div>" + r.route + "</div></td><td>" + r.count + "</td></tr>").join("")
    + "</tbody></table>";
}

async function load() {
  const d = await fetch("/dashboard/data").then(r => r.json());
  document.getElementById("k-total").textContent  = d.total_calls;
  document.getElementById("k-deal").textContent   = d.deal_rate + "%";
  document.getElementById("k-delta").textContent  = (d.avg_rate_delta >= 0 ? "+" : "") + "$" + d.avg_rate_delta;
  document.getElementById("k-rounds").textContent = d.avg_neg_rounds;
  document.getElementById("ts").textContent       = "Updated " + new Date().toLocaleTimeString();

  const outK = Object.keys(d.outcomes);
  donut("c-outcome", outK, outK.map(k=>d.outcomes[k]), outK.map(k=>OUTCOME_COLORS[k]||"#cbd5e1"));
  const sentK = Object.keys(d.sentiments);
  donut("c-sentiment", sentK, sentK.map(k=>d.sentiments[k]), sentK.map(k=>SENT_COLORS[k]||"#cbd5e1"));
  buildRoutes(d.routes);

  const rc = d.rate_comparison;
  new Chart(document.getElementById("c-rates"), {
    type:"bar",
    data:{ labels:rc.map(r=>r.carrier), datasets:[
      { label:"Loadboard Rate", data:rc.map(r=>r.loadboard), backgroundColor:"rgba(37,99,235,.12)", borderColor:"#2563eb", borderWidth:1.5, borderRadius:4 },
      { label:"Agreed Rate",    data:rc.map(r=>r.agreed),    backgroundColor:"rgba(22,163,74,.12)",  borderColor:"#16a34a", borderWidth:1.5, borderRadius:4 }
    ]},
    options:{ plugins:{ legend:LEG }, scales:AXIS }
  });

  const deltas = rc.map(r => r.agreed - r.loadboard);
  new Chart(document.getElementById("c-delta"), {
    type:"bar",
    data:{ labels:rc.map(r=>r.carrier), datasets:[{
      label:"Rate Delta ($)",
      data:deltas,
      backgroundColor:deltas.map(v=>v>=0?"rgba(22,163,74,.12)":"rgba(220,38,38,.12)"),
      borderColor:    deltas.map(v=>v>=0?"#16a34a":"#dc2626"),
      borderWidth:1.5, borderRadius:4
    }]},
    options:{ plugins:{ legend:{ display:false } }, scales:AXIS }
  });

  document.getElementById("loader").style.display = "none";
  document.getElementById("main").classList.add("show");
}

load();
</script>
</body>
</html>"""