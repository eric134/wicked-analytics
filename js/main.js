// Green = Broadway, gold = Wicked (2024), teal = Wicked: For Good (2025)
const GREEN      = "#6DC54A";
const GREEN_FILL = "rgba(109,197,74,0.12)";
const GOLD       = "#D4AF37";
const GOLD_FILL  = "rgba(212,175,55,0.12)";
const TEAL       = "#3BBFB0";
const TEAL_FILL  = "rgba(59,191,176,0.12)";
const RED_FILL   = "rgba(201,64,64,0.10)";
const MUTED      = "#555";

const GRID_COLOR  = "#1f1f1f";
const TICK_COLOR  = "#666";

const fmtDollar   = (n) => n == null ? "—" : "$" + Math.round(n).toLocaleString("en-US");
const fmtMillions = (n) => n == null ? "—" : "$" + (n / 1e6).toFixed(1) + "M";
const fmtDate     = (iso) => iso ? iso.split("T")[0] : "";

// Axis config gets reused across charts, so build it once here
function timeXAxis(unit) {
  return {
    type: "time",
    time: { unit },
    grid: { color: GRID_COLOR },
    ticks: { color: TICK_COLOR, maxRotation: 0 },
  };
}

function dollarYAxis() {
  return {
    grid: { color: GRID_COLOR },
    border: { dash: [4, 4] },
    ticks: { color: TICK_COLOR, callback: (v) => "$" + (v / 1e6).toFixed(1) + "M" },
  };
}

function countYAxis() {
  return {
    grid: { color: GRID_COLOR },
    border: { dash: [4, 4] },
    ticks: { color: TICK_COLOR },
  };
}

function renderStats() {
  const normal = BROADWAY_DATA.filter((r) => r.status === "normal");

  const peak = normal.reduce((a, b) => (b.weekly_gross > a.weekly_gross ? b : a));
  document.getElementById("stat-bway-peak").textContent      = fmtDollar(peak.weekly_gross);
  document.getElementById("stat-bway-peak-date").textContent = fmtDate(peak.week_ending);
  document.getElementById("stat-bway-weeks").textContent     = normal.length.toLocaleString();
  document.getElementById("stat-bway-seasons").textContent   =
    new Set(normal.map((r) => r.broadway_season)).size;

  document.getElementById("stat-m1-total").textContent   =
    fmtMillions(Math.max(...MOVIE1_DATA.map((r) => r.cumulative_gross)));
  document.getElementById("stat-m1-opening").textContent = fmtMillions(MOVIE1_DATA[0].daily_gross);

  // Part 2 may be empty on a fresh checkout before it's scraped
  if (MOVIE2_DATA.length > 0) {
    document.getElementById("stat-m2-total").textContent   =
      fmtMillions(Math.max(...MOVIE2_DATA.map((r) => r.cumulative_gross)));
    document.getElementById("stat-m2-opening").textContent = fmtMillions(MOVIE2_DATA[0].daily_gross);
  }

  // Newest date across all three datasets drives the footer stamp
  const dates = [
    ...MOVIE1_DATA.map((r) => r.date),
    ...MOVIE2_DATA.map((r) => r.date),
    ...BROADWAY_DATA.filter((r) => r.status === "normal").map((r) => r.week_ending),
  ].sort();
  document.getElementById("footer-updated").textContent =
    "Data through " + fmtDate(dates[dates.length - 1]);
}

function initBroadwayChart() {
  const labels = BROADWAY_DATA.map((r) => r.week_ending);
  const data   = BROADWAY_DATA.map((r) => r.status === "normal" ? r.weekly_gross : null);

  new Chart(document.getElementById("broadwayChart"), {
    type: "line",
    data: {
      labels,
      datasets: [{
        data,
        borderColor: GREEN,
        backgroundColor: GREEN_FILL,
        fill: true,
        tension: 0.3,
        pointRadius: 0,
        borderWidth: 1.5,
        spanGaps: false,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: "index", intersect: false },
      scales: { x: timeXAxis("year"), y: dollarYAxis() },
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            title: (ctx) => fmtDate(ctx[0].label),
            label: (ctx) => fmtDollar(ctx.parsed.y),
          },
        },
        annotation: {
          annotations: {
            covidBox: {
              type: "box",
              xMin: "2020-03-13",
              xMax: "2021-09-19",
              backgroundColor: RED_FILL,
              borderWidth: 0,
              label: {
                display: true,
                content: "COVID Shutdown",
                color: "#666",
                font: { size: 10 },
                position: { x: "center", y: "start" },
              },
            },
            film1Line: {
              type: "line",
              xMin: "2024-11-22",
              xMax: "2024-11-22",
              borderColor: GOLD,
              borderWidth: 1.5,
              borderDash: [5, 4],
              label: {
                display: true,
                content: "Wicked (2024)",
                color: GOLD,
                font: { size: 10 },
                position: "start",
                yAdjust: 8,
              },
            },
            film2Line: {
              type: "line",
              xMin: "2025-11-21",
              xMax: "2025-11-21",
              borderColor: TEAL,
              borderWidth: 1.5,
              borderDash: [5, 4],
              label: {
                display: true,
                content: "For Good (2025)",
                color: TEAL,
                font: { size: 10 },
                position: "start",
                yAdjust: 28,
              },
            },
          },
        },
      },
    },
  });
}

// Shared by both films' daily charts; re-release days get a muted color
function initDailyChart(canvasId, movieData, primaryColor, reReleaseColor) {
  const colors = movieData.map((r) =>
    r.phase === "Re-Release" ? (reReleaseColor || MUTED) : primaryColor
  );

  new Chart(document.getElementById(canvasId), {
    type: "bar",
    data: {
      labels: movieData.map((r) => r.date),
      datasets: [{ data: movieData.map((r) => r.daily_gross), backgroundColor: colors, borderWidth: 0 }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: { x: { ...timeXAxis("month"), offset: true }, y: dollarYAxis() },
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            title: (ctx) => fmtDate(ctx[0].label),
            label: (ctx) =>
              fmtDollar(ctx.parsed.y) + "  (" + movieData[ctx.dataIndex].phase + ")",
          },
        },
      },
    },
  });
}

// Split the line by phase so the off-screen gap doesn't get bridged
function initTheaterChart(canvasId, movieData, primaryColor, primaryFill) {
  const initial   = movieData.filter((r) => r.phase === "Initial Release");
  const rerelease = movieData.filter((r) => r.phase === "Re-Release");

  const shared = { fill: true, tension: 0.3, pointRadius: 0, borderWidth: 1.5 };

  const datasets = [
    {
      ...shared,
      label: "Initial Release",
      data: initial.map((r) => ({ x: r.date, y: r.theaters })),
      borderColor: primaryColor,
      backgroundColor: primaryFill,
    },
  ];

  if (rerelease.length > 0) {
    datasets.push({
      ...shared,
      label: "Re-Release",
      data: rerelease.map((r) => ({ x: r.date, y: r.theaters })),
      borderColor: MUTED,
      backgroundColor: "rgba(85,85,85,0.10)",
    });
  }

  new Chart(document.getElementById(canvasId), {
    type: "line",
    data: { datasets },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: { x: timeXAxis("month"), y: countYAxis() },
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            title: (ctx) => fmtDate(ctx[0].label),
            label: (ctx) => ctx.parsed.y.toLocaleString() + " theaters",
          },
        },
      },
    },
  });
}

function initSeasonChart() {
  const normal = BROADWAY_DATA.filter((r) => r.status === "normal");

  const sums = {}, counts = {};
  for (const r of normal) {
    sums[r.broadway_season]   = (sums[r.broadway_season]   || 0) + r.weekly_gross;
    counts[r.broadway_season] = (counts[r.broadway_season] || 0) + 1;
  }

  const labels = Object.keys(sums).sort();
  const data   = labels.map((s) => sums[s] / counts[s]);
  const colors = labels.map((s) => {
    if (s === "2025-26") return TEAL;
    if (s === "2024-25") return GOLD;
    return GREEN;
  });

  new Chart(document.getElementById("seasonChart"), {
    type: "bar",
    data: {
      labels,
      datasets: [{ data, backgroundColor: colors, borderWidth: 0 }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        x: {
          grid: { color: GRID_COLOR },
          ticks: { color: TICK_COLOR, maxRotation: 45, font: { size: 10 } },
        },
        y: dollarYAxis(),
      },
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: { label: (ctx) => "Avg: " + fmtDollar(ctx.parsed.y) + " / week" },
        },
      },
    },
  });
}

window.addEventListener("DOMContentLoaded", () => {
  if (typeof BROADWAY_DATA === "undefined" || typeof MOVIE1_DATA === "undefined") {
    document.querySelector("main").innerHTML =
      '<p style="color:#666;padding:3rem;text-align:center">' +
      "Run <code>python python/generate_data_js.py</code> to generate js/data.js, then reload." +
      "</p>";
    return;
  }

  renderStats();
  initBroadwayChart();
  initDailyChart("movie1DailyChart", MOVIE1_DATA, GOLD,  MUTED);
  initDailyChart("movie2DailyChart", MOVIE2_DATA, TEAL,  null);
  initTheaterChart("theater1Chart",  MOVIE1_DATA, GOLD,  GOLD_FILL);
  initTheaterChart("theater2Chart",  MOVIE2_DATA, TEAL,  TEAL_FILL);
  initSeasonChart();
});
