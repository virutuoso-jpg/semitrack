Chart.defaults.color = "#6b8299";
Chart.defaults.borderColor = "#1e2a3a";
Chart.defaults.font.family = "Pretendard, Malgun Gothic, sans-serif";

const COLORS = {
  accent: "#39f2c6",
  accent2: "#4da3ff",
  warn: "#ffb454",
  danger: "#ff5d7a",
};

let currentStock = "삼성전자";
let foreignChart, institutionChart, exportChart, micronChart;

function showState(containerId, kind, message) {
  const el = document.getElementById(containerId);
  const canvas = el.querySelector("canvas");
  if (canvas) canvas.style.display = "none";
  let stateEl = el.querySelector(".state-msg");
  if (!stateEl) {
    stateEl = document.createElement("div");
    stateEl.className = `state-msg ${kind}`;
    el.appendChild(stateEl);
  }
  stateEl.className = `state-msg ${kind}`;
  stateEl.textContent = message;
}

function clearState(containerId) {
  const el = document.getElementById(containerId);
  const stateEl = el.querySelector(".state-msg");
  if (stateEl) stateEl.remove();
  const canvas = el.querySelector("canvas");
  if (canvas) canvas.style.display = "block";
}

async function fetchJson(url) {
  const res = await fetch(url);
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || "요청 실패");
  return data;
}

async function loadForeignInvestor(stock) {
  const id = "foreignInvestorBody";
  showState(id, "loading", "불러오는 중...");
  try {
    const rows = await fetchJson(`/api/foreign-investor?stock=${encodeURIComponent(stock)}`);
    clearState(id);
    const labels = rows.map((r) => r.date.slice(5));
    const foreign = rows.map((r) => r.foreign_net_qty);
    const institution = rows.map((r) => r.institution_net_qty);

    if (foreignChart) foreignChart.destroy();
    foreignChart = new Chart(document.getElementById("foreignInvestorChart"), {
      type: "line",
      data: {
        labels,
        datasets: [
          { label: "외국인 순매수(원)", data: foreign, borderColor: COLORS.accent, backgroundColor: "transparent", tension: 0.3 },
          { label: "기관 순매수(원)", data: institution, borderColor: COLORS.accent2, backgroundColor: "transparent", tension: 0.3 },
        ],
      },
      options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { labels: { boxWidth: 10, font: { size: 11 } } } } },
    });
  } catch (e) {
    showState(id, "error", e.message);
  }
}

async function loadInstitutionFlow(stock) {
  const id = "institutionFlowBody";
  showState(id, "loading", "불러오는 중...");
  try {
    const data = await fetchJson(`/api/institution-flow?stock=${encodeURIComponent(stock)}`);
    clearState(id);
    const types = Object.keys(data);
    const dates = types.length ? Object.keys(data[types[0]]) : [];
    const palette = [COLORS.accent, COLORS.accent2, COLORS.warn];

    if (institutionChart) institutionChart.destroy();
    institutionChart = new Chart(document.getElementById("institutionFlowChart"), {
      type: "bar",
      data: {
        labels: dates.map((d) => d.slice(5)),
        datasets: types.map((t, i) => ({
          label: t,
          data: dates.map((d) => data[t][d]),
          backgroundColor: palette[i % palette.length],
        })),
      },
      options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { labels: { boxWidth: 10, font: { size: 11 } } } } },
    });
  } catch (e) {
    showState(id, "error", e.message);
  }
}

async function loadFinancials(stock) {
  const revEl = document.getElementById("revenueValue");
  const opEl = document.getElementById("opProfitValue");
  const periodEl = document.getElementById("financialsPeriod");
  revEl.textContent = "…";
  opEl.textContent = "…";
  periodEl.textContent = "";
  try {
    const data = await fetchJson(`/api/quarterly-financials?stock=${encodeURIComponent(stock)}&year=2026&quarter=1`);
    const toEok = (n) => (n / 100000000).toLocaleString("ko-KR", { maximumFractionDigits: 0 }) + "억원";
    revEl.textContent = toEok(data.revenue);
    opEl.textContent = toEok(data.operating_profit);
    periodEl.textContent = `${data.year}년 ${data.quarter}분기 기준 (연결)`;
  } catch (e) {
    revEl.textContent = "-";
    opEl.textContent = "-";
    periodEl.textContent = e.message;
  }
}

async function loadValuation(stock) {
  const perEl = document.getElementById("perValue");
  const pbrEl = document.getElementById("pbrValue");
  const epsEl = document.getElementById("epsValue");
  const bpsEl = document.getElementById("bpsValue");
  const frEl = document.getElementById("foreignRatioValue");
  [perEl, pbrEl, epsEl, bpsEl, frEl].forEach((el) => (el.textContent = "…"));
  try {
    const data = await fetchJson(`/api/valuation?stock=${encodeURIComponent(stock)}`);
    perEl.textContent = data.per.toFixed(2);
    pbrEl.textContent = data.pbr.toFixed(2);
    epsEl.textContent = Math.round(data.eps).toLocaleString() + "원";
    bpsEl.textContent = Math.round(data.bps).toLocaleString() + "원";
    frEl.textContent = data.foreign_holding_ratio.toFixed(2) + "%";
  } catch (e) {
    [perEl, pbrEl, epsEl, bpsEl, frEl].forEach((el) => (el.textContent = "-"));
  }
}

async function loadSoxIndex() {
  const valueEl = document.getElementById("soxValue");
  const changeEl = document.getElementById("soxChangeValue");
  try {
    const data = await fetchJson(`/api/sox-index`);
    valueEl.textContent = data.latest_close.toLocaleString();
    const sign = data.change_pct >= 0 ? "+" : "";
    changeEl.textContent = `${sign}${data.change_pct}%`;
    changeEl.className = "metric-value " + (data.change_pct >= 0 ? "up" : "down");
  } catch (e) {
    valueEl.textContent = "-";
    changeEl.textContent = e.message;
  }
}

async function loadMicronTrend() {
  const id = "micronBody";
  showState(id, "loading", "불러오는 중...");
  try {
    const rows = await fetchJson(`/api/micron-trend`);
    if (!rows.length) {
      showState(id, "empty", "데이터가 없습니다.");
      return;
    }
    clearState(id);
    if (micronChart) micronChart.destroy();
    micronChart = new Chart(document.getElementById("micronChart"), {
      type: "bar",
      data: {
        labels: rows.map((r) => r.period_end),
        datasets: [
          {
            label: "매출액($)",
            data: rows.map((r) => r.revenue_usd),
            backgroundColor: COLORS.accent2,
          },
        ],
      },
      options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } } },
    });
  } catch (e) {
    showState(id, "error", e.message);
  }
}

async function loadExportStats() {
  const id = "exportStatsBody";
  showState(id, "loading", "불러오는 중...");
  try {
    const rows = await fetchJson(`/api/export-stats`);
    if (!rows.length) {
      showState(id, "empty", "데이터가 없습니다.");
      return;
    }
    clearState(id);
    const labels = rows.map((r) => `${r.period} ${r.item}`);
    if (exportChart) exportChart.destroy();
    exportChart = new Chart(document.getElementById("exportStatsChart"), {
      type: "bar",
      data: {
        labels,
        datasets: [
          { label: "수출($)", data: rows.map((r) => r.export_usd), backgroundColor: COLORS.accent },
          { label: "수입($)", data: rows.map((r) => r.import_usd), backgroundColor: COLORS.danger },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        indexAxis: "y",
        plugins: { legend: { labels: { boxWidth: 10, font: { size: 11 } } } },
      },
    });
  } catch (e) {
    showState(id, "error", e.message);
  }
}

async function loadCapex() {
  const tbody = document.querySelector("#capexTable tbody");
  tbody.innerHTML = `<tr><td colspan="5" class="state-msg loading">불러오는 중...</td></tr>`;
  try {
    const rows = await fetchJson(`/api/hyperscaler-capex`);
    if (!rows.length) {
      tbody.innerHTML = `<tr><td colspan="5" class="state-msg empty">아직 입력된 데이터가 없습니다. 실적 발표 후 clients/hyperscaler_capex.py의 add_quarter()로 입력하세요.</td></tr>`;
      return;
    }
    tbody.innerHTML = rows
      .map(
        (r) => `<tr>
          <td>${r.company}</td>
          <td>${r.year} Q${r.quarter}</td>
          <td>${r.capex_usd_million?.toLocaleString() ?? "-"}</td>
          <td>${r.cloud_revenue_usd_million?.toLocaleString() ?? "-"}</td>
          <td>${r.ai_note ?? ""}</td>
        </tr>`
      )
      .join("");
  } catch (e) {
    tbody.innerHTML = `<tr><td colspan="5" class="state-msg error">${e.message}</td></tr>`;
  }
}

function loadStockScoped(stock) {
  loadForeignInvestor(stock);
  loadInstitutionFlow(stock);
  loadFinancials(stock);
  loadValuation(stock);
}

document.getElementById("stockToggle").addEventListener("click", (e) => {
  const btn = e.target.closest(".toggle-btn");
  if (!btn) return;
  document.querySelectorAll(".toggle-btn").forEach((b) => b.classList.remove("active"));
  btn.classList.add("active");
  currentStock = btn.dataset.stock;
  loadStockScoped(currentStock);
});

loadStockScoped(currentStock);
loadExportStats();
loadCapex();
loadSoxIndex();
loadMicronTrend();
