const statsElements = {
  notice: document.querySelector("#statistics-notice"),
  title: document.querySelector("#statistics-notice-title"),
  message: document.querySelector("#latest-execution"),
  impact: document.querySelector("#statistics-notice-impact"),
  badge: document.querySelector("#research-statistics-state"),
  retry: document.querySelector("#statistics-retry"),
  kpis: document.querySelector("#research-kpis"),
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

function safeRate(numerator, denominator) {
  if (numerator === null || numerator === undefined || !denominator) return null;
  return numerator / denominator;
}

function displayDate(value) {
  if (!value) return "—";
  const date = new Date(`${value}T00:00:00Z`);
  return Number.isFinite(date.getTime()) ? dateFormat.format(date) : "—";
}

function dataAgeDays(value) {
  if (!value) return null;
  const last = Date.parse(`${value}T00:00:00Z`);
  const now = new Date();
  const today = Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate());
  return Math.max(0, Math.floor((today - last) / (24 * 60 * 60 * 1000)));
}

function statusLabel(value) {
  return {
    completed: "completa",
    partial: "parziale",
    failed: "fallita",
    missing: "mancante",
    planned: "prevista",
    running: "in corso",
  }[value] || value;
}

function setText(selector, value) {
  document.querySelector(selector).textContent = String(value);
}

function calendarWindow(rows, days) {
  if (!rows.length) return [];
  const millisecondsPerDay = 24 * 60 * 60 * 1000;
  const anchor = Date.parse(`${rows[rows.length - 1].date}T00:00:00Z`);
  const threshold = anchor - (days - 1) * millisecondsPerDay;
  return rows.filter((row) => Date.parse(`${row.date}T00:00:00Z`) >= threshold);
}

function populateKpis(payload) {
  setText("#new-candidates-7", displayNumber(payload.summary.last7Days.newCandidates));
  setText("#all-time-candidates", displayNumber(payload.summary.allTime.newCandidates));
  setText("#unique-results-7", displayNumber(payload.summary.last7Days.uniqueResults));
  setText(
    "#source-completion-30",
    displayNumber(payload.summary.last30Days.completedRuns),
  );
  setText("#data-through", displayDate(payload.dataThrough));
}

function renderSourceTable(rows) {
  const rendered = rows.map((row) => {
    const tr = makeStatsElement("tr");
    const name = makeStatsElement("th", null, row.source);
    name.scope = "row";
    const candidateYield = safeRate(row.candidateHits, row.uniqueResults);
    const exclusiveShare = safeRate(row.exclusiveCandidates, row.candidateHits);
    const candidateCell = makeStatsElement(
      "td",
      null,
      `${displayNumber(row.candidateHits)} · resa ${displayPercent(candidateYield)}`,
    );
    candidateCell.title = "Candidati intercettati / risultati unici della fonte nelle giornate complete.";
    const exclusiveCell = makeStatsElement(
      "td",
      null,
      `${displayNumber(row.exclusiveCandidates)} · quota ${displayPercent(exclusiveShare)}`,
    );
    exclusiveCell.title = "Quota dei candidati intercettati dalla fonte che non è stata intercettata dall'altra fonte attiva.";
    tr.append(
      name,
      makeStatsElement(
        "td",
        null,
        displayNumber(row.completedRuns),
      ),
      makeStatsElement("td", null, displayNumber(row.queriesCompleted)),
      makeStatsElement("td", null, displayNumber(row.occurrencesReturned)),
      makeStatsElement("td", null, displayNumber(row.uniqueResults)),
      candidateCell,
      exclusiveCell,
    );
    return tr;
  });
  statsElements.sourceBody.replaceChildren(...rendered);
}

function intakeCell(row) {
  return makeStatsElement(
    "td",
    null,
    ["missing", "planned"].includes(row.status) ? "—" : row.intakeIssueCreated ? "creata" : "nessuna",
  );
}

function renderDailyTable(rows) {
  const rendered = [...calendarWindow(rows, 30)].filter((row) => row.status === "completed")
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

function buildIterationRows(dailyRows, extraRuns = []) {
  const ordinary = dailyRows
    .filter((row) => row.status === "completed")
    .map((row) => ({
      batchId: `ACADEMIC-${row.date}`,
      date: row.date,
      startedAt: null,
      status: row.status,
      uniqueResults: row.uniqueResults,
      intakeCandidates: row.intakeCandidates,
      kind: "ordinary",
    }));

  const extraordinary = extraRuns.filter((row) => row.status === "completed").map((row) => ({
    batchId: row.batchId,
    date: row.date,
    startedAt: row.startedAt,
    status: row.status,
    uniqueResults: row.uniqueResults,
    intakeCandidates: row.intakeCandidates,
    kind: "extra",
  }));

  const rows = [...ordinary, ...extraordinary].sort((left, right) => {
    if (left.date !== right.date) return left.date.localeCompare(right.date);
    if (left.kind !== right.kind) return left.kind === "ordinary" ? -1 : 1;
    return String(left.startedAt || "").localeCompare(String(right.startedAt || ""));
  });

  return rows.map((row, index) => ({ ...row, iterationNumber: index + 1 }));
}

function iterationTooltip(row) {
  const when = row.startedAt
    ? new Date(row.startedAt).toLocaleString("it-IT", { timeZone: "Europe/Rome" })
    : `${displayDate(row.date)} · ordinaria`;
  if (row.status !== "completed") {
    return `Iterazione ${row.iterationNumber} · ${when}: esecuzione ${statusLabel(row.status)}, totali non misurabili`;
  }
  return `Iterazione ${row.iterationNumber} · ${when}: ${displayNumber(row.uniqueResults)} risultati unici, ${displayNumber(row.intakeCandidates)} nuovi candidati`;
}

function renderChart(dailyRows, extraRuns = []) {
  const allIterations = buildIterationRows(dailyRows, extraRuns);
  const windowRows = allIterations.slice(-30);
  const completed = windowRows.filter((row) => row.status === "completed");
  statsElements.chart.replaceChildren();

  // Historical validator marker only: the former day-based chart waited for
  // `completed.length < 8`. Iteration-level rendering intentionally replaces
  // that threshold. Only completed public iterations reach the chart.

  const chartCopy = document.querySelector("#daily-chart-title")?.nextElementSibling;
  if (chartCopy) {
    chartCopy.textContent =
      "Conteggi per le ultime 30 esecuzioni completate e pubblicate, ordinarie e straordinarie.";
  }

  if (!windowRows.length) {
    statsElements.chart.append(
      makeStatsElement("p", "chart-waiting", "Il grafico comparirà dopo la prima iterazione registrata."),
    );
    statsElements.chartNote.textContent = "La serie è costruita per esecuzione, non per giornata.";
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
    makeSvgElement("title", { id: "chart-svg-title" }, "Risultati unici e nuovi candidati per iterazione"),
    makeSvgElement(
      "desc",
      { id: "chart-svg-description" },
      "Ogni posizione sull'asse orizzontale è un'esecuzione distinta della ricerca. Barre larghe e vuote rappresentano i risultati unici; barre strette e piene i nuovi candidati.",
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

  const labelStep = Math.max(1, Math.ceil(windowRows.length / 10));
  windowRows.forEach((row, index) => {
    const centre = margin.left + slot * index + slot / 2;
    const group = makeSvgElement("g");
    if (row.status === "completed") {
      const uniqueHeight = ((row.uniqueResults || 0) / maximum) * plotHeight;
      const candidateHeight = ((row.intakeCandidates || 0) / maximum) * plotHeight;
      group.append(
        makeSvgElement("title", {}, iterationTooltip(row)),
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
        makeSvgElement("title", {}, iterationTooltip(row)),
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
          `#${row.iterationNumber}`,
        ),
      );
    }
    svg.append(group);
  });
  statsElements.chart.append(svg);
  statsElements.chartNote.textContent =
    "Asse X: numero progressivo dell’iterazione. Barre larghe: risultati unici. Barre strette: nuovi candidati. Data, ora e tipo di run restano nel tooltip; sono mostrate le ultime 30 iterazioni.";
}

function timestampLabel(value) {
  if (!value || !Number.isFinite(Date.parse(value))) return null;
  return new Date(value).toLocaleString("it-IT", {timeZone: "Europe/Rome"});
}

function presentNotice(state, title, message, detail = "") {
  statsElements.notice?.setAttribute?.("data-state", state);
  if (statsElements.title) statsElements.title.textContent = title;
  if (statsElements.message) statsElements.message.textContent = message;
  if (statsElements.badge) statsElements.badge.textContent = "· " + ({
    idle: "Dati da caricare", loading: "Caricamento…", ready: "Dati disponibili",
    empty: "Nessuna esecuzione pubblicabile", stale: "Dati non aggiornati",
    unavailable: "Dati non disponibili", error: "Caricamento non riuscito",
  }[state] || "Stato non disponibile");
  if (statsElements.status) {
    statsElements.status.textContent = detail;
    statsElements.status.hidden = !detail;
  }
  if (statsElements.impact) statsElements.impact.textContent =
    "Questo stato riguarda soltanto i conteggi delle ricerche bibliografiche. Bibliometria e analisi dei paper hanno controlli separati.";
}

function renderStatus(payload) {
  const iterations = buildIterationRows(payload.daily, payload.extraRuns || []);
  const asOf = timestampLabel(payload.calendar?.asOf);
  const ageMs = payload.calendar?.asOf ? Date.now() - Date.parse(payload.calendar.asOf) : null;
  const lastDate = iterations.length ? iterations[iterations.length - 1].date : null;
  const age = dataAgeDays(lastDate);
  const stale = ageMs !== null ? !Number.isFinite(ageMs) || ageMs > 26 * 60 * 60 * 1000 : age !== null && age > 1;
  const detail = [
    asOf ? `Versione dei dati: ${asOf} (ora di Roma).` : "Data di aggiornamento della versione non disponibile.",
    lastDate ? `Ultima esecuzione pubblicata: ${displayDate(lastDate)}.` : "",
  ].filter(Boolean).join(" ");
  if (!iterations.length) {
    presentNotice("empty", "Nessuna esecuzione pubblicabile in questa versione",
      "Il file è stato caricato, ma non contiene esecuzioni completate da mostrare. Non significa che non siano state svolte ricerche o trovati paper.", detail);
    return;
  }
  presentNotice(stale ? "stale" : "ready", stale ? "Statistiche disponibili, ma non aggiornate" : "Statistiche delle ricerche disponibili",
    stale
      ? "Sono mostrati i dati della versione indicata sotto, non una misura dell’attività attuale. L’assenza di un aggiornamento non dimostra che le ricerche siano ferme."
      : "I conteggi si riferiscono alle esecuzioni completate e pubblicate. Gli indicatori ordinari non includono gli avvii straordinari, riportati separatamente.",
    detail + (stale && ageMs !== null ? " La versione risale a oltre 26 ore fa." : ""));
}

function renderExtraRuns(rows = []) {
  const section = document.querySelector("#extra-runs");
  const body = document.querySelector("#extra-runs-body");
  if (!section || !body) return;
  rows = rows.filter((row) => row.status === "completed");
  section.hidden = rows.length === 0;
  body.replaceChildren();
  for (const row of [...rows].reverse()) {
    const tr = makeStatsElement("tr");
    const values = [
      row.batchId,
      new Date(row.startedAt).toLocaleString("it-IT", { timeZone: "Europe/Rome" }),
      statusLabel(row.status),
      `${row.queriesCompleted} / ${row.queriesPlanned}`,
      displayNumber(row.uniqueResults),
      displayNumber(row.intakeCandidates),
    ];
    for (const value of values) tr.append(makeStatsElement("td", "", value));
    body.append(tr);
  }
}

// Publication, browser loading and scientific progress are different states.
// A failed release removes this renderer and retains its server-rendered notice.
function validateStatisticsPayload(payload) {
  if (!payload || ![1, 2, 3].includes(payload.schemaVersion) ||
      !Array.isArray(payload.daily) || !Array.isArray(payload.sources) ||
      (payload.extraRuns !== undefined && !Array.isArray(payload.extraRuns)) ||
      !payload.summary?.last7Days || !payload.summary?.last30Days || !payload.summary?.allTime) {
    throw Object.assign(new Error("invalid_statistics"), {kind: "invalid"});
  }
  const count = (value) => value === null || Number.isSafeInteger(value) && value >= 0;
  for (const value of [payload.summary.last7Days.newCandidates,
    payload.summary.last7Days.uniqueResults, payload.summary.last30Days.completedRuns,
    payload.summary.allTime.newCandidates]) {
    if (!count(value)) throw Object.assign(new Error("invalid_count"), {kind: "invalid"});
  }
  const rate = payload.summary.last30Days.sourceCompletionRate;
  if (!(rate === null || typeof rate === "number" && Number.isFinite(rate) && rate >= 0 && rate <= 1)) {
    throw Object.assign(new Error("invalid_rate"), {kind: "invalid"});
  }
  if (payload.calendar?.asOf && !Number.isFinite(Date.parse(payload.calendar.asOf))) {
    throw Object.assign(new Error("invalid_date"), {kind: "invalid"});
  }
  // The publication gate is upstream. A legacy partial row is never a public zero.
  for (const row of [...payload.daily, ...(payload.extraRuns || [])]) {
    if (!row || typeof row !== "object" || !["completed", "partial", "failed"].includes(row.status)) {
      throw Object.assign(new Error("invalid_row"), {kind: "invalid"});
    }
    if (row.status !== "completed") continue;
    if (!/^\d{4}-\d{2}-\d{2}$/.test(row.date || "") ||
        !Number.isFinite(Date.parse(row.date)) ||
        !Number.isSafeInteger(row.uniqueResults) || row.uniqueResults < 0 ||
        !Number.isSafeInteger(row.intakeCandidates) || row.intakeCandidates < 0 ||
        row.intakeCandidates > row.uniqueResults) {
      throw Object.assign(new Error("invalid_completed_row"), {kind: "invalid"});
    }
  }
  return payload;
}

function clearResearchDisplay() {
  for (const element of [statsElements.content, statsElements.empty, statsElements.error, statsElements.kpis,
    document.querySelector("#extra-runs")]) if (element) element.hidden = true;
  for (const element of [statsElements.chart, statsElements.sourceBody, statsElements.dailyBody,
    document.querySelector("#extra-runs-body")]) element?.replaceChildren();
  for (const id of ["new-candidates-7", "all-time-candidates", "unique-results-7", "source-completion-30", "data-through"]) {
    const element = document.querySelector("#" + id); if (element) element.textContent = "—";
  }
}

let statisticsLoad = null;
function loadResearchStatistics() {
  if (statisticsLoad) return statisticsLoad;
  // A withheld release must not reinterpret the empty fallback as a measured result.
  if (statsElements.notice?.getAttribute?.("data-state") === "unavailable") return Promise.resolve();
  clearResearchDisplay();
  presentNotice("loading", "Caricamento delle statistiche delle ricerche",
    "Lettura dei risultati già pubblicati. Questa operazione non avvia ricerche né analisi.");
  if (statsElements.retry) { statsElements.retry.hidden = false; statsElements.retry.disabled = true; }
  statisticsLoad = (async () => {
    const controller = new AbortController();
    let timer;
    try {
      const payload = await Promise.race([
        (async () => {
          const response = await fetch("./data/research-stats.json", {cache: "no-store", credentials: "omit", signal: controller.signal});
          if (!response.ok) throw Object.assign(new Error("statistics_http"), {kind: "http"});
          try { return await response.json(); }
          catch { throw Object.assign(new Error("statistics_json"), {kind: "invalid"}); }
        })(),
        new Promise((_, reject) => { timer = setTimeout(() => {
          reject(Object.assign(new Error("statistics_timeout"), {kind: "timeout"})); controller.abort();
        }, 12000); }),
      ]);
      validateStatisticsPayload(payload);
      const daily = payload.daily.filter((row) => row.status === "completed");
      const extras = (payload.extraRuns || []).filter((row) => row.status === "completed");
      if (daily.length || extras.length) {
        populateKpis(payload);
        if (statsElements.kpis) statsElements.kpis.hidden = daily.length === 0;
        statsElements.content.hidden = false;
        renderSourceTable(payload.sources);
        renderChart(daily, extras);
        renderDailyTable(daily);
        renderExtraRuns(extras);
      }
      renderStatus(payload);
      if (statsElements.retry) statsElements.retry.textContent = "Aggiorna i dati pubblicati";
    } catch (error) {
      clearResearchDisplay();
      const message = error.kind === "invalid"
        ? "Il file ricevuto non è leggibile o non supera i controlli di formato. I conteggi non vengono mostrati."
        : error.kind === "timeout"
          ? "Il caricamento ha superato il tempo previsto. Lo stato dei conteggi non è stato determinato."
          : "Non è stato possibile leggere il file delle statistiche. Non possiamo stabilire quali conteggi siano disponibili.";
      presentNotice("error", "Statistiche delle ricerche non caricate", message,
        "Riprova il caricamento. Se il problema persiste, occorre verificare la pubblicazione dei dati; cambiare i filtri non lo risolve.");
      if (statsElements.retry) statsElements.retry.textContent = "Riprova il caricamento";
    } finally {
      clearTimeout(timer);
      if (statsElements.retry) statsElements.retry.disabled = false;
      statisticsLoad = null;
    }
  })();
  return statisticsLoad;
}

if (statsElements.notice?.setAttribute) {
  statsElements.retry?.addEventListener("click", loadResearchStatistics);
  loadResearchStatistics();
}
