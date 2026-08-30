const statsElements = {
  empty: document.querySelector("#metrics-empty"),
  content: document.querySelector("#metrics-content"),
  error: document.querySelector("#metrics-error"),
  status: document.querySelector("#run-status"),
  chart: document.querySelector("#daily-chart"),
  chartNote: document.querySelector("#chart-note"),
  sourceBody: document.querySelector("#source-table-body"),
  dailyBody: document.querySelector("#daily-table-body"),
};

const numberFormat = new Intl.NumberFormat("it-IT");
const dateFormat = new Intl.DateTimeFormat("it-IT", {
  day: "2-digit",
  month: "2-digit",
  year: "numeric",
  timeZone: "UTC",
});

function makeStatsElement(tag, className, text) {
  const element = document.createElement(tag);
  if (className) element.className = className;
  if (text !== undefined && text !== null) element.textContent = text;
  return element;
}

function makeSvgElement(tag, attributes = {}, text) {
  const element = document.createElementNS("http://www.w3.org/2000/svg", tag);
  Object.entries(attributes).forEach(([name, value]) => element.setAttribute(name, String(value)));
  if (text !== undefined && text !== null) element.textContent = text;
  return element;
}

function displayNumber(value) {
  return value === null || value === undefined ? "—" : numberFormat.format(value);
}

function displayPercent(value) {
  return value === null || value === undefined
    ? "—"
    : new Intl.NumberFormat("it-IT", { style: "percent", maximumFractionDigits: 1 }).format(value);
}

function displayDate(value) {
  if (!value) return "—";
  return dateFormat.format(new Date(`${value}T00:00:00Z`));
}

function statusLabel(value) {
  return {
    completed: "completa",
    partial: "parziale",
    failed: "fallita",
  }[value] || value;
}

function setText(selector, value) {
  document.querySelector(selector).textContent = String(value);
}

function populateKpis(payload) {
  setText("#new-candidates-7", displayNumber(payload.summary.last7Days.newCandidates));
  setText("#all-time-candidates", displayNumber(payload.summary.allTime.newCandidates));
  setText("#unique-results-7", displayNumber(payload.summary.last7Days.uniqueResults));
  setText(
    "#source-completion-30",
    displayPercent(payload.summary.last30Days.sourceCompletionRate),
  );
  setText("#data-through", displayDate(payload.dataThrough));
}

function renderSourceTable(rows) {
  const rendered = rows.map((row) => {
    const tr = makeStatsElement("tr");
    const name = makeStatsElement("th", null, row.source);
    name.scope = "row";
    tr.append(
      name,
      makeStatsElement(
        "td",
        null,
        `${displayNumber(row.completedRuns)} / ${displayNumber(row.expectedRuns)}`,
      ),
      makeStatsElement("td", null, displayNumber(row.queriesCompleted)),
      makeStatsElement("td", null, displayNumber(row.occurrencesReturned)),
      makeStatsElement("td", null, displayNumber(row.uniqueResults)),
      makeStatsElement("td", null, displayNumber(row.candidateHits)),
      makeStatsElement("td", null, displayNumber(row.exclusiveCandidates)),
    );
    return tr;
  });
  statsElements.sourceBody.replaceChildren(...rendered);
}

function intakeCell(row) {
  return makeStatsElement("td", null, row.intakeIssueCreated ? "creata" : "nessuna");
}

function renderDailyTable(rows) {
  const rendered = [...rows]
    .slice(-30)
    .reverse()
    .map((row) => {
      const tr = makeStatsElement("tr");
      const date = makeStatsElement("th", null, displayDate(row.date));
      date.scope = "row";
      const status = makeStatsElement("span", `status-pill status-${row.status}`, statusLabel(row.status));
      const statusCell = makeStatsElement("td");
      statusCell.append(status);
      tr.append(
        date,
        statusCell,
        makeStatsElement("td", null, displayNumber(row.occurrencesReturned)),
        makeStatsElement("td", null, displayNumber(row.uniqueResults)),
        makeStatsElement("td", null, displayNumber(row.knownMatches)),
        makeStatsElement("td", "candidate-number", displayNumber(row.intakeCandidates)),
        makeStatsElement("td", null, displayPercent(row.candidateRate)),
        intakeCell(row),
      );
      return tr;
    });
  statsElements.dailyBody.replaceChildren(...rendered);
}

function renderChart(rows) {
  const windowRows = rows.slice(-30);
  const completed = windowRows.filter((row) => row.status === "completed");
  statsElements.chart.replaceChildren();
  if (completed.length < 8) {
    statsElements.chart.append(
      makeStatsElement(
        "p",
        "chart-waiting",
        `Il grafico comparirà dopo 8 giornate complete. Per ora sono disponibili ${completed.length} giornate; i valori esatti sono nella tabella.`,
      ),
    );
    statsElements.chartNote.textContent =
      "La soglia evita di presentare come andamento una serie ancora troppo corta.";
    return;
  }

  const width = 920;
  const height = 360;
  const margin = { top: 28, right: 20, bottom: 54, left: 56 };
  const plotWidth = width - margin.left - margin.right;
  const plotHeight = height - margin.top - margin.bottom;
  const maximum = Math.max(1, ...completed.map((row) => row.uniqueResults || 0));
  const slot = plotWidth / windowRows.length;
  const uniqueWidth = Math.max(5, slot * 0.62);
  const candidateWidth = Math.max(3, slot * 0.28);
  const svg = makeSvgElement("svg", {
    viewBox: `0 0 ${width} ${height}`,
    role: "img",
    "aria-labelledby": "chart-svg-title chart-svg-description",
  });
  svg.append(
    makeSvgElement("title", { id: "chart-svg-title" }, "Risultati unici e nuovi candidati per giorno"),
    makeSvgElement(
      "desc",
      { id: "chart-svg-description" },
      "Barre larghe e vuote per i risultati unici; barre strette e piene per i candidati inviati alla revisione; una croce indica una giornata parziale o fallita.",
    ),
  );

  const tickCount = 4;
  for (let index = 0; index <= tickCount; index += 1) {
    const value = Math.round((maximum * index) / tickCount);
    const y = margin.top + plotHeight - (value / maximum) * plotHeight;
    svg.append(
      makeSvgElement("line", {
        x1: margin.left,
        x2: width - margin.right,
        y1: y,
        y2: y,
        class: "chart-grid-line",
      }),
      makeSvgElement(
        "text",
        { x: margin.left - 10, y: y + 4, class: "chart-axis-label", "text-anchor": "end" },
        numberFormat.format(value),
      ),
    );
  }

  const labelStep = Math.max(1, Math.ceil(windowRows.length / 7));
  windowRows.forEach((row, index) => {
    const centre = margin.left + slot * index + slot / 2;
    const group = makeSvgElement("g");
    if (row.status === "completed") {
      const uniqueHeight = ((row.uniqueResults || 0) / maximum) * plotHeight;
      const candidateHeight = ((row.intakeCandidates || 0) / maximum) * plotHeight;
      group.append(
        makeSvgElement(
          "title",
          {},
          `${displayDate(row.date)}: ${displayNumber(row.uniqueResults)} risultati unici, ${displayNumber(row.intakeCandidates)} nuovi candidati`,
        ),
        makeSvgElement("rect", {
          x: centre - uniqueWidth / 2,
          y: margin.top + plotHeight - uniqueHeight,
          width: uniqueWidth,
          height: uniqueHeight,
          class: "chart-bar-unique",
        }),
        makeSvgElement("rect", {
          x: centre - candidateWidth / 2,
          y: margin.top + plotHeight - candidateHeight,
          width: candidateWidth,
          height: candidateHeight,
          class: "chart-bar-candidate",
        }),
      );
    } else {
      group.append(
        makeSvgElement(
          "title",
          {},
          `${displayDate(row.date)}: esecuzione ${statusLabel(row.status)}, totali non misurabili`,
        ),
        makeSvgElement(
          "text",
          {
            x: centre,
            y: margin.top + plotHeight - 8,
            class: "chart-incomplete-mark",
            "text-anchor": "middle",
          },
          "×",
        ),
      );
    }
    if (index % labelStep === 0 || index === windowRows.length - 1) {
      group.append(
        makeSvgElement(
          "text",
          {
            x: centre,
            y: height - 25,
            class: "chart-axis-label",
            "text-anchor": "middle",
          },
          displayDate(row.date).slice(0, 5),
        ),
      );
    }
    svg.append(group);
  });
  statsElements.chart.append(svg);
  statsElements.chartNote.textContent =
    "Barre larghe: risultati unici. Barre strette: nuovi candidati. Le altezze condividono la stessa scala e partono da zero; le croci mantengono visibili le esecuzioni incomplete.";
}

function renderStatus(payload) {
  const last = payload.daily[payload.daily.length - 1];
  statsElements.status.className = `status-banner status-banner-${last.status}`;
  statsElements.status.textContent =
    `Ultima esecuzione: ${displayDate(last.date)}, ${statusLabel(last.status)}. ` +
    `${displayNumber(payload.summary.last30Days.completedRuns)} delle ` +
    `${displayNumber(payload.summary.last30Days.loggedRuns)} giornate registrate negli ultimi 30 giorni osservati sono complete.`;
}

fetch("./data/research-stats.json")
  .then((response) => {
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return response.json();
  })
  .then((payload) => {
    populateKpis(payload);
    if (!payload.daily.length) {
      statsElements.empty.hidden = false;
      return;
    }
    statsElements.content.hidden = false;
    renderStatus(payload);
    renderChart(payload.daily);
    renderSourceTable(payload.sources);
    renderDailyTable(payload.daily);
  })
  .catch(() => {
    statsElements.error.hidden = false;
  });
