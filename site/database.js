/* DATABASE_BROWSER_V1 — public, read-only projection browser. */
(() => {
  "use strict";

  const RESEARCH_ENDPOINT = "https://criminal-infiltration-curator.colazeta-research.workers.dev/api/public-paper-research";
  const TABLES = [
    {
      id: "candidate_records",
      label: "candidate_records",
      kind: "STATIC",
      source: "./data/paper-register.json",
      columns: ["id", "title", "authors", "year", "venue", "doi", "metadataStatus", "reviewStatus", "accessStatus", "registeredAt"],
      load: async () => rowsFrom(await readJson("./data/paper-register.json"), "records"),
    },
    {
      id: "reading_support",
      label: "reading_support",
      kind: "STATIC",
      source: "./paper-support.json",
      columns: ["id", "bibliography.title", "abstract.status", "readingAid.kind", "retrieval.status", "access.status"],
      load: async () => rowsFrom(await readJson("./paper-support.json"), "records"),
    },
    {
      id: "research_index",
      label: "research_index",
      kind: "LIVE",
      source: "Worker / public index",
      columns: ["candidate.id", "candidate.title", "availability", "source_coverage", "generation_kind", "framework_status", "classes", "completion.status"],
      load: loadResearchIndex,
    },
    {
      id: "core_publications",
      label: "core_publications",
      kind: "STATIC",
      source: "./data/archive.json",
      columns: ["id", "title", "authors", "year", "venue", "doi", "topic", "screeningDecision", "status"],
      load: async () => rowsFrom(await readJson("./data/archive.json"), "records"),
    },
    {
      id: "broader_aml",
      label: "broader_aml",
      kind: "STATIC",
      source: "./data/secondary-collections.json",
      columns: ["id", "title", "authors", "year", "venue", "doi", "screeningDecision", "status"],
      load: async () => rowsFrom(await readJson("./data/secondary-collections.json"), "records"),
    },
    {
      id: "surveillance_daily",
      label: "surveillance_daily",
      kind: "AGG",
      source: "./data/research-stats.json",
      load: async () => rowsFrom(await readJson("./data/research-stats.json"), "daily"),
    },
    {
      id: "surveillance_snapshot",
      label: "surveillance_snapshot",
      kind: "AGG",
      source: "./data/research-stats.json",
      load: async () => [await readJson("./data/research-stats.json")],
    },
    {
      id: "curator_aggregate",
      label: "curator_aggregate",
      kind: "AGG",
      source: "./data/curator-stats.json",
      load: async () => [await readJson("./data/curator-stats.json")],
    },
    {
      id: "controlled_vocabularies",
      label: "controlled_vocabularies",
      kind: "STATIC",
      source: "./data/curator-options.json",
      columns: ["group", "code", "label", "description"],
      load: async () => optionRows(await readJson("./data/curator-options.json")),
    },
  ];

  const state = {
    tableId: TABLES[0].id,
    cache: new Map(),
    filtered: [],
    selected: null,
    query: "",
    sort: "source",
  };

  const byId = (id) => document.getElementById(id);
  const ui = {
    tableList: byId("database-table-list"),
    tableCount: byId("database-table-count"),
    rowCount: byId("database-row-count"),
    selectedCount: byId("database-selected-count"),
    researchCount: byId("database-research-count"),
    currentTable: byId("database-current-table"),
    currentSource: byId("database-current-source"),
    controls: byId("database-controls"),
    search: byId("database-search"),
    sort: byId("database-sort"),
    status: byId("database-status"),
    head: byId("database-head"),
    body: byId("database-body"),
    recordKey: byId("database-record-key"),
    recordJson: byId("database-record-json"),
    researchStatus: byId("database-research-status"),
    researchJson: byId("database-research-json"),
    loadResearch: byId("database-load-research"),
    openConsole: byId("database-open-console"),
    downloadJson: byId("database-download-json"),
    downloadCsv: byId("database-download-csv"),
  };

  function text(tag, value, className = "") {
    const node = document.createElement(tag);
    if (value !== undefined && value !== null) node.textContent = String(value);
    if (className) node.className = className;
    return node;
  }

  async function readJson(url) {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 12000);
    try {
      const response = await fetch(url, {
        cache: "no-store",
        credentials: "omit",
        signal: controller.signal,
      });
      if (!response.ok) throw new Error("HTTP " + response.status);
      return await response.json();
    } finally {
      clearTimeout(timeout);
    }
  }

  function rowsFrom(payload, key) {
    if (!payload || !Array.isArray(payload[key])) throw new Error("invalid public dataset");
    return payload[key];
  }

  function optionRows(payload) {
    if (!payload || typeof payload !== "object" || Array.isArray(payload)) throw new Error("invalid options payload");
    const rows = [];
    for (const [group, values] of Object.entries(payload)) {
      if (group === "schemaVersion" || !Array.isArray(values)) continue;
      for (const value of values) {
        if (!value || typeof value !== "object") continue;
        rows.push({ group, ...value });
      }
    }
    return rows;
  }

  async function loadResearchIndex() {
    const rows = [];
    let cursor = 0;
    let revision = null;
    for (;;) {
      const url = new URL(RESEARCH_ENDPOINT);
      url.searchParams.set("view", "index");
      url.searchParams.set("cursor", String(cursor));
      if (revision) url.searchParams.set("revision", revision);
      const page = await readJson(url.href);
      if (
        !page ||
        page.schema_version !== 1 ||
        page.projection_version !== "CILE-PUBLIC-INDEX-1" ||
        !Array.isArray(page.records) ||
        !Number.isSafeInteger(page.total) ||
        page.total < 0 ||
        page.total > 10000
      ) throw new Error("invalid public research index");
      if (revision && revision !== page.index_revision) throw new Error("public research index changed during read");
      revision = page.index_revision;
      rows.push(...page.records);
      if (page.next_cursor === null) break;
      if (!Number.isSafeInteger(page.next_cursor) || page.next_cursor <= cursor) throw new Error("invalid public research cursor");
      cursor = page.next_cursor;
    }
    if (rows.length !== new Set(rows.map((row) => row?.candidate?.id)).size) throw new Error("duplicate research candidate");
    return rows;
  }

  function valueAt(row, path) {
    let value = row;
    for (const key of path.split(".")) {
      if (value === null || value === undefined || typeof value !== "object") return null;
      value = value[key];
    }
    return value;
  }

  function displayValue(value) {
    if (value === null || value === undefined || value === "") return "—";
    if (Array.isArray(value)) return value.map((item) => typeof item === "object" ? JSON.stringify(item) : String(item)).join("; ");
    if (typeof value === "object") return JSON.stringify(value);
    return String(value);
  }

  function candidateId(row) {
    const direct = typeof row?.id === "string" && row.id.startsWith("CAND-") ? row.id : "";
    const nested = typeof row?.candidate?.id === "string" && row.candidate.id.startsWith("CAND-") ? row.candidate.id : "";
    return direct || nested || "";
  }

  function candidateTitle(row) {
    return row?.title || row?.bibliography?.title || row?.candidate?.title || "";
  }

  function rowKey(row, index) {
    return candidateId(row) || String(row?.id || row?.code || row?.date || row?.day || index + 1);
  }

  function dynamicColumns(rows) {
    const keys = [];
    for (const row of rows.slice(0, 25)) {
      if (!row || typeof row !== "object" || Array.isArray(row)) continue;
      for (const key of Object.keys(row)) {
        if (!keys.includes(key)) keys.push(key);
        if (keys.length >= 12) return keys;
      }
    }
    return keys.length ? keys : ["value"];
  }

  function searchable(row) {
    try { return JSON.stringify(row).toLocaleLowerCase("it"); }
    catch (_) { return String(row).toLocaleLowerCase("it"); }
  }

  function sortRows(rows) {
    const copy = rows.map((row, index) => ({ row, index }));
    const title = (row) => candidateTitle(row).toLocaleLowerCase("it");
    const id = (row) => candidateId(row) || String(row?.id || row?.code || "");
    const year = (row) => Number(row?.year ?? row?.bibliography?.year ?? row?.candidate?.year);
    if (state.sort === "id") copy.sort((a, b) => id(a.row).localeCompare(id(b.row)));
    if (state.sort === "title") copy.sort((a, b) => title(a.row).localeCompare(title(b.row)));
    if (state.sort === "year_desc") copy.sort((a, b) => (Number.isFinite(year(b.row)) ? year(b.row) : -Infinity) - (Number.isFinite(year(a.row)) ? year(a.row) : -Infinity));
    if (state.sort === "year_asc") copy.sort((a, b) => (Number.isFinite(year(a.row)) ? year(a.row) : Infinity) - (Number.isFinite(year(b.row)) ? year(b.row) : Infinity));
    return copy.map((item) => item.row);
  }

  function currentDefinition() {
    return TABLES.find((table) => table.id === state.tableId) || TABLES[0];
  }

  function setStatus(message) {
    ui.status.textContent = message;
  }

  function renderTableList() {
    ui.tableList.replaceChildren();
    for (const table of TABLES) {
      const button = text("button");
      button.type = "button";
      button.className = "database-table-button";
      button.dataset.tableId = table.id;
      button.setAttribute("aria-current", String(table.id === state.tableId));
      const label = text("span", table.label);
      const count = text("span", "—", "database-count");
      const cached = state.cache.get(table.id);
      if (cached) count.textContent = String(cached.length);
      count.dataset.countFor = table.id;
      button.append(label, count);
      button.addEventListener("click", () => selectTable(table.id));
      ui.tableList.append(button);
    }
  }

  function updateTableCounts() {
    for (const node of ui.tableList.querySelectorAll("[data-count-for]")) {
      const rows = state.cache.get(node.dataset.countFor);
      node.textContent = rows ? String(rows.length) : "—";
    }
    const research = state.cache.get("research_index");
    if (research) ui.researchCount.textContent = String(research.filter((row) => row?.availability === "available").length);
  }

  function clearInspector() {
    state.selected = null;
    ui.recordKey.textContent = "nessun record selezionato";
    ui.recordJson.textContent = "Seleziona una riga della tabella.";
    ui.researchStatus.textContent = "Seleziona un CandidateRecord e usa LOAD PUBLIC RESEARCH.";
    ui.researchJson.textContent = "—";
    ui.loadResearch.hidden = true;
    ui.openConsole.hidden = true;
  }

  function selectRow(row, key, tr) {
    state.selected = row;
    for (const item of ui.body.querySelectorAll("tr")) item.setAttribute("aria-selected", String(item === tr));
    ui.recordKey.textContent = key;
    ui.recordJson.textContent = JSON.stringify(row, null, 2);
    ui.researchJson.textContent = "—";
    const id = candidateId(row);
    ui.loadResearch.hidden = !id;
    ui.openConsole.hidden = !id;
    ui.researchStatus.textContent = id ? "Ricerca strutturata non ancora caricata per " + id + "." : "La riga selezionata non identifica un CandidateRecord.";
    if (id) {
      ui.openConsole.href = "https://criminal-infiltration-curator.colazeta-research.workers.dev/enrichment.html?candidate=" + encodeURIComponent(id);
      ui.openConsole.target = "_blank";
      ui.openConsole.rel = "noopener noreferrer";
    }
  }

  function renderRows() {
    const table = currentDefinition();
    const sourceRows = state.cache.get(table.id) || [];
    const query = state.query.trim().toLocaleLowerCase("it");
    const filtered = query ? sourceRows.filter((row) => searchable(row).includes(query)) : [...sourceRows];
    state.filtered = sortRows(filtered);
    ui.rowCount.textContent = String(sourceRows.length);
    ui.selectedCount.textContent = String(state.filtered.length);

    const columns = table.columns || dynamicColumns(sourceRows);
    const headerRow = text("tr");
    for (const column of columns) headerRow.append(text("th", column));
    ui.head.replaceChildren(headerRow);
    ui.body.replaceChildren();

    state.filtered.forEach((row, index) => {
      const tr = text("tr");
      tr.tabIndex = 0;
      tr.setAttribute("aria-selected", "false");
      const key = rowKey(row, index);
      for (const column of columns) {
        const value = column === "value" ? row : valueAt(row, column);
        const td = text("td", displayValue(value));
        if (/(^|\.)(id|doi|status|code|date|year)$/i.test(column)) td.classList.add("mono");
        td.title = displayValue(value);
        tr.append(td);
      }
      const choose = () => selectRow(row, key, tr);
      tr.addEventListener("click", choose);
      tr.addEventListener("dblclick", async () => {
        choose();
        if (candidateId(row)) await loadSelectedResearch();
      });
      tr.addEventListener("keydown", async (event) => {
        if (event.key === "Enter") {
          event.preventDefault();
          choose();
          if (candidateId(row)) await loadSelectedResearch();
        }
      });
      ui.body.append(tr);
    });

    clearInspector();
    setStatus("TABLE " + table.label + " · " + state.filtered.length + " / " + sourceRows.length + " righe visibili · doppio clic/Invio su un CandidateRecord per caricare la proiezione di ricerca.");
  }

  async function ensureTable(table) {
    if (state.cache.has(table.id)) return state.cache.get(table.id);
    setStatus("LOAD " + table.label + " FROM " + table.source + " …");
    const rows = await table.load();
    if (!Array.isArray(rows)) throw new Error("table loader did not return rows");
    state.cache.set(table.id, rows);
    updateTableCounts();
    return rows;
  }

  async function selectTable(id) {
    if (!TABLES.some((table) => table.id === id)) return;
    state.tableId = id;
    state.query = "";
    state.sort = "source";
    ui.search.value = "";
    ui.sort.value = "source";
    renderTableList();
    const table = currentDefinition();
    ui.currentTable.textContent = "TABLE: " + table.label;
    ui.currentSource.textContent = "SOURCE: " + table.source;
    clearInspector();
    try {
      await ensureTable(table);
      renderRows();
    } catch (error) {
      ui.head.replaceChildren();
      ui.body.replaceChildren();
      ui.rowCount.textContent = "—";
      ui.selectedCount.textContent = "—";
      setStatus("ERROR " + table.label + " · " + (error?.message || "public data unavailable") + ". Nessuna assenza viene interpretata come zero.");
    }
  }

  async function loadSelectedResearch() {
    const id = candidateId(state.selected);
    if (!id) return;
    ui.loadResearch.disabled = true;
    ui.researchStatus.textContent = "LOAD PUBLIC RESEARCH " + id + " …";
    ui.researchJson.textContent = "—";
    try {
      const url = new URL(RESEARCH_ENDPOINT);
      url.searchParams.set("id", id);
      const payload = await readJson(url.href);
      ui.researchJson.textContent = JSON.stringify(payload, null, 2);
      ui.researchStatus.textContent = "Proiezione pubblica caricata. availability=" + String(payload?.availability ?? "unknown") + ".";
    } catch (error) {
      ui.researchStatus.textContent = "Impossibile verificare la proiezione pubblica: " + (error?.message || "errore di trasporto") + ".";
    } finally {
      ui.loadResearch.disabled = false;
    }
  }

  function csvCell(value) {
    const raw = displayValue(value);
    return '"' + raw.replaceAll('"', '""') + '"';
  }

  function exportRows(format) {
    const table = currentDefinition();
    const rows = state.filtered;
    let body;
    let type;
    let extension;
    if (format === "json") {
      body = JSON.stringify(rows, null, 2);
      type = "application/json";
      extension = "json";
    } else {
      const columns = table.columns || dynamicColumns(rows);
      const lines = [columns.map(csvCell).join(",")];
      for (const row of rows) lines.push(columns.map((column) => csvCell(column === "value" ? row : valueAt(row, column))).join(","));
      body = lines.join("\n");
      type = "text/csv";
      extension = "csv";
    }
    const blob = new Blob([body], { type: type + ";charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = table.label + "." + extension;
    document.body.append(anchor);
    anchor.click();
    anchor.remove();
    URL.revokeObjectURL(url);
  }

  ui.controls.addEventListener("submit", (event) => event.preventDefault());
  ui.controls.addEventListener("reset", () => {
    setTimeout(() => {
      state.query = "";
      state.sort = "source";
      renderRows();
    });
  });
  ui.search.addEventListener("input", () => {
    state.query = ui.search.value;
    renderRows();
  });
  ui.sort.addEventListener("change", () => {
    state.sort = ui.sort.value;
    renderRows();
  });
  ui.loadResearch.addEventListener("click", loadSelectedResearch);
  ui.downloadJson.addEventListener("click", () => exportRows("json"));
  ui.downloadCsv.addEventListener("click", () => exportRows("csv"));

  ui.tableCount.textContent = String(TABLES.length);
  renderTableList();
  void selectTable(TABLES[0].id);
})();
