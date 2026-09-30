// Minimal frontend: no framework, no build step.
// 1. GET /api/config fills the model picker and the profile panel.
// 2. Run opens an EventSource on /api/runs/stream; each message is either an agent
//    event (appended to the timeline), the final result, or an error.

const $ = (id) => document.getElementById(id);
const pct = (x, digits = 1) => `${(x * 100).toFixed(digits)}%`;
const usd = (x) => x.toLocaleString("en-US", { style: "currency", currency: "USD" });
const PALETTE = getComputedStyle(document.documentElement)
  .getPropertyValue("--palette").split(",").map((c) => c.trim());

// Build DOM with textContent only, so model output can never inject HTML.
function el(tag, attrs = {}, ...children) {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === "class") node.className = v;
    else if (k === "style") node.style.cssText = v;
    else node.setAttribute(k, v);
  }
  for (const c of children.flat()) {
    if (c == null) continue;
    node.append(c instanceof Node ? c : document.createTextNode(String(c)));
  }
  return node;
}

function prettyJson(text) {
  try { return JSON.stringify(JSON.parse(text), null, 2); } catch { return text; }
}

function setStatus(state, label = state) {
  const s = $("status");
  s.className = `status ${state}`;
  s.textContent = label;
}

// ---- config ---------------------------------------------------------------------------

async function loadConfig() {
  const res = await fetch("/api/config");
  const cfg = await res.json();

  const labels = { mock: "Mock (free, deterministic)", openai: "OpenAI" };
  $("provider").replaceChildren(
    ...cfg.providers.map((p) => el("option", { value: p }, labels[p] ?? p)),
  );
  if (!cfg.providers.includes("openai")) {
    $("provider").append(el("option", { disabled: "" }, "OpenAI (add key to .env)"));
  }

  const p = cfg.profile;
  $("setup-body").replaceChildren(
    el("div", {}, el("strong", {}, "Capital "), usd(p.capital_usd)),
    el("div", {}, el("strong", {}, "Holdings "), `${p.min_holdings}–${p.max_holdings}`),
    el("div", {}, el("strong", {}, "Max per stock "), pct(p.max_weight, 0)),
    el("div", {}, el("strong", {}, "Risk "), p.risk_tolerance),
    el("div", {}, el("strong", {}, "Horizon "), `${p.horizon_years}y`),
    el("div", { style: "flex-basis:100%" },
      el("strong", {}, `Candidates (${cfg.candidates.length}) `),
      el("div", { class: "chips" }, cfg.candidates.map((t) => el("span", { class: "chip" }, t))),
    ),
  );
}

// ---- timeline -------------------------------------------------------------------------

function addTimeline(kind, label, text, payload, quote = false) {
  const item = el("li", { class: kind },
    el("div", { class: "ev-head" }, el("span", { class: "ev-label" }, label)),
    text ? el("p", { class: `ev-text${quote ? " quote" : ""}` }, text) : null,
    payload ? el("details", { class: "payload" }, el("summary", {}, "details"), el("pre", {}, payload)) : null,
  );
  const list = $("timeline");
  list.append(item);
  list.scrollTop = list.scrollHeight; // follow new events inside the panel, not the page
}

function renderEvent(ev) {
  const d = ev.data;
  switch (ev.type) {
    case "agent_started":
      addTimeline("", "start", `${ev.agent} on ${d.provider}`);
      break;
    case "model_response":
      if (d.text) addTimeline("model", `turn ${d.turn} · model`, d.text, null, true);
      break;
    case "tool_call":
      addTimeline("tool", `turn ${d.turn} · calls`, d.tool, JSON.stringify(d.arguments, null, 2));
      break;
    case "tool_result":
      addTimeline(
        d.is_error ? "err" : "ok",
        `turn ${d.turn} · ${d.is_error ? "rejected" : "result"}`,
        d.is_error ? d.content.split("\n")[0] : `${d.tool} returned`,
        prettyJson(d.content),
      );
      break;
    case "agent_nudged":
      addTimeline("err", `turn ${d.turn} · nudge`, "Model answered in prose; reminded it to call a tool.");
      break;
    case "agent_submitted":
      addTimeline("ok", "submitted",
        `Accepted after ${d.turn} turns · ${d.usage.input_tokens.toLocaleString()} in / ${d.usage.output_tokens.toLocaleString()} out tokens`);
      break;
    case "agent_failed":
      addTimeline("err", "failed", d.reason);
      break;
  }
}

// ---- result ---------------------------------------------------------------------------

function kpi(label, value) {
  return el("div", { class: "kpi" }, el("div", { class: "label" }, label), el("div", { class: "value" }, value));
}

function renderResult(r) {
  const s = r.stats;
  const holdings = [...r.portfolio.holdings].sort((a, b) => b.target_weight - a.target_weight);
  const rationale = Object.fromEntries(r.proposal.positions.map((p) => [p.ticker.toUpperCase(), p.rationale]));
  const color = (i) => PALETTE[i % PALETTE.length];

  const rows = holdings.map((h) => el("tr", {},
    el("td", {}, el("strong", {}, h.ticker)),
    el("td", { class: "num" }, pct(h.target_weight)),
    el("td", { class: "num" }, h.shares),
    el("td", { class: "num" }, usd(h.price)),
    el("td", { class: "num" }, usd(h.value)),
    el("td", { class: "rationale" }, rationale[h.ticker] ?? ""),
  ));
  rows.push(el("tr", { class: "cash" },
    el("td", {}, "Cash"), el("td"), el("td"), el("td"),
    el("td", { class: "num" }, usd(r.portfolio.cash)),
    el("td", { class: "rationale" }, "Left over from buying whole shares"),
  ));

  $("result").replaceChildren(
    el("div", { class: "kpis" },
      kpi("Trailing return", pct(s.annual_return)),
      kpi("Volatility", pct(s.annual_volatility)),
      kpi("Max drawdown", pct(s.max_drawdown)),
      kpi("Sharpe", s.sharpe),
      kpi("Holdings", `${holdings.length} (eff. ${s.effective_holdings})`),
      kpi("Model cost", r.cost_usd == null ? "free" : `$${r.cost_usd.toFixed(4)}`),
    ),
    el("div", { class: "alloc-bar", role: "img", "aria-label": "Allocation by weight" },
      holdings.map((h, i) => el("span", {
        style: `flex:${h.target_weight};background:${color(i)}`,
        title: `${h.ticker} ${pct(h.target_weight)}`,
      })),
    ),
    el("div", { class: "legend" },
      holdings.map((h, i) => el("span", {}, el("i", { style: `background:${color(i)}` }), `${h.ticker} ${pct(h.target_weight)}`)),
    ),
    el("p", { class: "thesis" }, r.proposal.summary),
    el("div", { class: "table-wrap" }, el("table", {},
      el("thead", {}, el("tr", {},
        el("th", {}, "Ticker"), el("th", { class: "num" }, "Weight"), el("th", { class: "num" }, "Shares"),
        el("th", { class: "num" }, "Price"), el("th", { class: "num" }, "Value"), el("th", {}, "Rationale"),
      )),
      el("tbody", {}, rows),
    )),
    el("p", { class: "note muted" },
      `${r.provider} · ${r.turns} turns · Trailing-year stats are in-sample: the stocks were chosen on the same year they're measured on.`),
    r.data_source === "synthetic"
      ? el("p", { class: "note warn" }, "Synthetic prices: numbers are fake, for offline testing only.")
      : null,
  );
}

// ---- run ------------------------------------------------------------------------------

let source = null;

function run(event) {
  event.preventDefault();
  source?.close();
  $("timeline").replaceChildren();
  $("result").replaceChildren(el("p", { class: "empty muted" }, "Working…"));
  $("run").disabled = true;
  setStatus("running", "running…");

  const params = new URLSearchParams({ provider: $("provider").value, data: $("data").value });
  source = new EventSource(`/api/runs/stream?${params}`);

  const finish = (state, label) => {
    source.close();
    $("run").disabled = false;
    setStatus(state, label);
  };

  source.onmessage = (msg) => {
    const m = JSON.parse(msg.data);
    if (m.kind === "event") renderEvent(m);
    else if (m.kind === "result") { renderResult(m.result); finish("done", "done"); }
    else if (m.kind === "error") {
      $("result").replaceChildren(el("div", { class: "error-box" }, m.message));
      finish("error", "error");
    }
  };
  // The server closes the stream after the final message; only treat it as an error
  // if we never got a result.
  source.onerror = () => {
    if ($("run").disabled) {
      $("result").replaceChildren(el("div", { class: "error-box" }, "Lost connection to the backend. Is `committee serve` running?"));
      finish("error", "error");
    }
  };
}

$("run-form").addEventListener("submit", run);
loadConfig().catch(() => {
  $("setup-body").replaceChildren(el("div", { class: "error-box" }, "Backend not reachable."));
});
