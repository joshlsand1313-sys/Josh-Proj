from __future__ import annotations

import json

import jinja2
from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

from cloudtrail_report.jobs import store

app = FastAPI(title="CloudTrail Report", docs_url="/docs", redoc_url=None)

_jinja = jinja2.Environment(autoescape=True)
_jinja.filters["tojson"] = json.dumps

# Set by cli.py serve command before uvicorn starts.
_DEFAULT_PROFILE = ""
_DEFAULT_REGION = "us-east-2"


# ---------------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------------

_FORM_HTML = """\
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>CloudTrail Report</title>
  <style>
    *, *::before, *::after { box-sizing: border-box; }
    body { font-family: system-ui, sans-serif; max-width: 640px; margin: 48px auto;
           padding: 0 20px; color: #111; background: #fff; }
    h1 { font-size: 1.35rem; margin-bottom: 1.5rem; }
    fieldset { border: 1px solid #ddd; border-radius: 6px; padding: 14px 16px;
               margin-bottom: 14px; }
    legend { font-weight: 600; font-size: 0.82rem; text-transform: uppercase;
             letter-spacing: .04em; color: #555; padding: 0 6px; }
    label { display: block; font-size: 0.82rem; color: #555; margin-bottom: 3px; }
    input[type=text], input[type=number], input[type=date], select {
      width: 100%; padding: 6px 9px; border: 1px solid #ccc; border-radius: 4px;
      font-size: 0.9rem; margin-bottom: 10px; }
    input[type=text]:focus, input[type=number]:focus, input[type=date]:focus, select:focus {
      outline: 2px solid #2563eb; outline-offset: 1px; border-color: transparent; }
    .row { display: flex; gap: 10px; }
    .row > div { flex: 1; }
    .checks label { display: flex; align-items: center; gap: 8px;
                    font-size: 0.88rem; color: #333; margin-bottom: 8px; }
    .checks input[type=checkbox] { width: auto; margin: 0; }
    .tabs { display: flex; margin-bottom: 10px; }
    .tabs button {
      padding: 5px 14px; border: 1px solid #ccc; background: #f5f5f5;
      cursor: pointer; font-size: 0.85rem; transition: background .15s; }
    .tabs button.active { background: #2563eb; color: #fff; border-color: #2563eb; }
    .tabs button:first-child { border-radius: 4px 0 0 4px; }
    .tabs button:last-child  { border-radius: 0 4px 4px 0; }
    #range-panel { display: none; }
    button[type=submit] {
      width: 100%; padding: 11px; background: #2563eb; color: #fff; border: none;
      border-radius: 5px; font-size: 1rem; font-weight: 600; cursor: pointer; }
    button[type=submit]:hover { background: #1d4ed8; }
  </style>
</head>
<body>
  <h1>CloudTrail Audit Report</h1>
  <form method="post" action="/run">

    <fieldset>
      <legend>AWS</legend>
      <label>Profile <small>(leave blank to use ambient credentials / task role)</small></label>
      <input type="text" name="profile" value="{{ default_profile }}" placeholder="e.g. cloudtrail">
      <label>Primary Region</label>
      <input type="text" name="region" value="{{ default_region }}">
      <label>Extra Regions <small>(comma-separated, optional)</small></label>
      <input type="text" name="extra_regions" placeholder="e.g. us-west-2, eu-west-1">
    </fieldset>

    <fieldset>
      <legend>Time Window</legend>
      <div class="tabs">
        <button type="button" class="active" id="tab-days" onclick="setMode('days')">Last N days</button>
        <button type="button"                id="tab-range" onclick="setMode('range')">Date range</button>
      </div>
      <input type="hidden" name="time_mode" id="time_mode" value="days">
      <div id="days-panel">
        <label>Days of history (1–90)</label>
        <input type="number" name="days" value="30" min="1" max="90">
      </div>
      <div id="range-panel">
        <div class="row">
          <div>
            <label>Start (UTC, inclusive)</label>
            <input type="date" name="start">
          </div>
          <div>
            <label>End (UTC, inclusive)</label>
            <input type="date" name="end">
          </div>
        </div>
      </div>
    </fieldset>

    <fieldset>
      <legend>Filters <small>(all optional)</small></legend>
      <label>Event Source</label>
      <input type="text" name="event_source" placeholder="e.g. iam.amazonaws.com">
      <label>Username / Principal</label>
      <input type="text" name="username" placeholder="e.g. jsandoval">
      <label>Region (post-fetch filter)</label>
      <input type="text" name="filter_region" placeholder="e.g. us-west-2">
      <div class="checks">
        <label><input type="checkbox" name="read_only"   value="1"> Read-only events only</label>
        <label><input type="checkbox" name="errors_only" value="1"> Errors only</label>
      </div>
    </fieldset>

    <button type="submit">Run Report</button>
  </form>

  <script>
    function setMode(m) {
      document.getElementById('time_mode').value = m;
      document.getElementById('days-panel').style.display  = m === 'days'  ? '' : 'none';
      document.getElementById('range-panel').style.display = m === 'range' ? '' : 'none';
      document.getElementById('tab-days').classList.toggle('active',  m === 'days');
      document.getElementById('tab-range').classList.toggle('active', m === 'range');
    }
  </script>
</body>
</html>
"""

_JOB_HTML = """\
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Report {{ job_id }}</title>
  <style>
    *, *::before, *::after { box-sizing: border-box; }
    body { font-family: system-ui, sans-serif; max-width: 960px; margin: 32px auto;
           padding: 0 20px; color: #111; background: #fff; }
    nav { font-size: 0.85rem; margin-bottom: 20px; }
    nav a { color: #2563eb; text-decoration: none; }
    nav a:hover { text-decoration: underline; }
    .status-bar { display: flex; align-items: center; gap: 10px; padding: 10px 14px;
                  border-radius: 6px; margin-bottom: 24px; font-size: 0.9rem; }
    .status-bar.pending, .status-bar.running {
      background: #eff6ff; color: #1d4ed8; border: 1px solid #bfdbfe; }
    .status-bar.done  { background: #f0fdf4; color: #15803d; border: 1px solid #bbf7d0; }
    .status-bar.error { background: #fef2f2; color: #dc2626; border: 1px solid #fecaca; }
    .spinner { flex-shrink: 0; width: 16px; height: 16px; border: 2px solid #93c5fd;
               border-top-color: #1d4ed8; border-radius: 50%;
               animation: spin .7s linear infinite; }
    @keyframes spin { to { transform: rotate(360deg); } }
    #report h1 { font-size: 1.4rem; }
    #report h2 { font-size: 1.05rem; margin-top: 2rem;
                 border-bottom: 1px solid #e5e7eb; padding-bottom: 5px; }
    #report table { border-collapse: collapse; width: 100%; margin-bottom: 1rem;
                    font-size: 0.85rem; }
    #report th, #report td { border: 1px solid #e5e7eb; padding: 5px 10px; text-align: left; }
    #report th { background: #f9fafb; font-weight: 600; }
    #report code { background: #f3f4f6; padding: 1px 5px; border-radius: 3px; font-size: .85em; }
    #report hr { border: none; border-top: 1px solid #e5e7eb; margin: 1.5rem 0; }
    .error-box { background: #fef2f2; color: #dc2626; padding: 12px 16px;
                 border-radius: 4px; font-size: 0.9rem; white-space: pre-wrap; }
  </style>
</head>
<body>
  <nav><a href="/">&#8592; New report</a></nav>

  <div class="status-bar {{ status }}" id="status-bar">
    {% if status in ("pending", "running") %}
      <div class="spinner"></div>
      <span id="status-text">
        {% if status == "pending" %}Queued — waiting to start…{% else %}Fetching events from AWS…{% endif %}
      </span>
    {% elif status == "done" %}
      <span>&#10003; Report ready</span>
    {% else %}
      <span>&#10007; Error</span>
    {% endif %}
  </div>

  <div id="report">
    {% if status == "error" %}
      <div class="error-box">{{ error }}</div>
    {% endif %}
  </div>

  <script src="https://cdnjs.cloudflare.com/ajax/libs/marked/9.1.6/marked.min.js"></script>
  <script>
    function renderReport(md) {
      document.getElementById('report').innerHTML = marked.parse(md);
    }
    {% if status == "done" and report_md %}
      renderReport({{ report_md_json | safe }});
    {% elif status in ("pending", "running") %}
      (function poll() {
        fetch('/job/{{ job_id }}/status')
          .then(r => r.json())
          .then(d => {
            if (d.status === 'done') {
              renderReport(d.report_md);
              const bar = document.getElementById('status-bar');
              bar.className = 'status-bar done';
              bar.innerHTML = '<span>&#10003; Report ready</span>';
            } else if (d.status === 'error') {
              const bar = document.getElementById('status-bar');
              bar.className = 'status-bar error';
              bar.innerHTML = '<span>&#10007; Error</span>';
              document.getElementById('report').innerHTML =
                '<div class="error-box">' + d.error + '</div>';
            } else {
              if (d.status === 'running') {
                const t = document.getElementById('status-text');
                if (t) {
                  let msg = 'Fetching events from AWS…';
                  if (d.events_so_far > 0) {
                    msg += ' (' + d.events_so_far.toLocaleString() + ' events, ' + d.pages_done + ' pages so far)';
                  }
                  t.textContent = msg;
                }
              }
              setTimeout(poll, 2000);
            }
          })
          .catch(() => setTimeout(poll, 3000));
      })();
    {% endif %}
  </script>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
async def form_page() -> HTMLResponse:
    template = _jinja.from_string(_FORM_HTML)
    return HTMLResponse(template.render(
        default_profile=_DEFAULT_PROFILE,
        default_region=_DEFAULT_REGION,
    ))


@app.post("/run")
async def run_report(
    profile:       str = Form(""),
    region:        str = Form("us-east-1"),
    time_mode:     str = Form("days"),
    days:          int = Form(30),
    start:         str = Form(""),
    end:           str = Form(""),
    extra_regions: str = Form(""),
    event_source:  str = Form(""),
    username:      str = Form(""),
    filter_region: str = Form(""),
    read_only:     str = Form(""),
    errors_only:   str = Form(""),
):
    params: dict = {
        "profile":       profile.strip() or None,
        "region":        region.strip() or "us-east-1",
        "extra_regions": extra_regions.strip(),
        "event_source":  event_source.strip(),
        "username":      username.strip(),
        "filter_region": filter_region.strip(),
        "read_only":     bool(read_only),
        "errors_only":   bool(errors_only),
    }
    if time_mode == "range" and start.strip() and end.strip():
        params["start"] = start.strip()
        params["end"]   = end.strip()
    else:
        params["days"] = max(1, min(90, days))

    job_id = store.submit(params)
    return RedirectResponse(f"/job/{job_id}", status_code=303)


@app.get("/job/{job_id}", response_class=HTMLResponse)
async def job_page(job_id: str) -> HTMLResponse:
    job = store.get(job_id)
    if job is None:
        return HTMLResponse("Job not found.", status_code=404)
    template = _jinja.from_string(_JOB_HTML)
    return HTMLResponse(template.render(
        job_id=job_id,
        status=job.status,
        report_md=job.report_md,
        report_md_json=json.dumps(job.report_md or ""),
        error=job.error or "",
    ))


@app.get("/job/{job_id}/status")
async def job_status(job_id: str):
    job = store.get(job_id)
    if job is None:
        return JSONResponse({"error": "not found"}, status_code=404)
    return {
        "status": job.status,
        "report_md": job.report_md,
        "error": job.error,
        "pages_done": job.pages_done,
        "events_so_far": job.events_so_far,
    }


@app.get("/health")
async def health():
    return {"status": "ok"}
