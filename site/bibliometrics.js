(() => {
  const pendingStatuses = new Set(["pending", "needs_full_text"]);
  const state = { archive: [], register: [], includePending: false };
  const $ = (selector) => document.querySelector(selector);
  const ui = {
    toggle: $("#include-pending-toggle"), scope: $("#bibliometric-scope-note"),
    total: $("#bibliometric-total"), authors: $("#bibliometric-authors"),
    venues: $("#bibliometric-venues"), years: $("#bibliometric-years"),
    annual: $("#publications-by-year-body"), journals: $("#top-journals-body"),
    journalEvolution: $("#journal-evolution"), authorRanking: $("#top-authors-body"),
    authorEvolution: $("#author-evolution"), quality: $("#bibliometric-quality-note"),
    empty: $("#bibliometric-empty"), content: $("#bibliometric-content"), error: $("#bibliometric-error"),
  };
  if (!ui.toggle) return;

  const format = new Intl.NumberFormat("it-IT", { maximumFractionDigits: 2 });
  const cell = (tag, value, className = "") => {
    const node = document.createElement(tag);
    if (className) node.className = className;
    node.textContent = value;
    return node;
  };
  const authorsOf = (record) => String(record.authors || "").split(";").map((value) => value.trim()).filter(Boolean);
  const venueOf = (record) => String(record.venue || "").trim();
  const pending = () => state.register.filter((record) => pendingStatuses.has(record.reviewStatus));
  const records = () => state.includePending ? state.archive.concat(pending()) : state.archive;

  function counts(values) {
    const result = new Map();
    values.filter((value) => value !== "" && value !== null && value !== undefined)
      .forEach((value) => result.set(value, (result.get(value) || 0) + 1));
    return result;
  }

  function rank(map, limit = 10) {
    return [...map.entries()].sort((a, b) => b[1] - a[1] || String(a[0]).localeCompare(String(b[0]), "it")).slice(0, limit);
  }

  function yearRange(data) {
    const observed = data.map((record) => Number(record.year)).filter(Number.isInteger);
    if (!observed.length) return [];
    const first = Math.min(...observed);
    const last = Math.max(...observed);
    return Array.from({ length: last - first + 1 }, (_, index) => first + index);
  }

  function renderAnnual(data) {
    ui.annual.replaceChildren();
    const byYear = counts(data.map((record) => Number.isInteger(Number(record.year)) ? Number(record.year) : null));
    const years = yearRange(data);
    const maximum = Math.max(1, ...byYear.values());
    let cumulative = 0;
    years.forEach((year) => {
      const value = byYear.get(year) || 0;
      cumulative += value;
      const row = document.createElement("tr");
      const barCell = document.createElement("td");
      const track = document.createElement("span");
      track.className = "bibliometric-bar-track";
      const fill = document.createElement("span");
      fill.className = "bibliometric-bar-fill";
      fill.style.width = `${(value / maximum) * 100}%`;
      track.append(fill);
      barCell.append(track);
      row.append(cell("th", String(year)), cell("td", String(value)), cell("td", String(cumulative)), barCell);
      ui.annual.append(row);
    });
  }

  function renderJournalRanking(data) {
    ui.journals.replaceChildren();
    const ranking = rank(counts(data.map(venueOf)));
    ranking.forEach(([venue, value], index) => {
      const row = document.createElement("tr");
      row.append(cell("td", String(index + 1)), cell("th", venue), cell("td", String(value)), cell("td", `${format.format((value / data.length) * 100)}%`));
      ui.journals.append(row);
    });
    if (!ranking.length) {
      const row = document.createElement("tr");
      const message = cell("td", "Nessun journal/sede disponibile nei metadata correnti.");
      message.colSpan = 4;
      row.append(message);
      ui.journals.append(row);
    }
    return ranking.map(([venue]) => venue);
  }

  function renderAuthorRanking(data) {
    ui.authorRanking.replaceChildren();
    const raw = new Map();
    const fractional = new Map();
    data.forEach((record) => {
      const authors = authorsOf(record);
      authors.forEach((author) => {
        raw.set(author, (raw.get(author) || 0) + 1);
        fractional.set(author, (fractional.get(author) || 0) + 1 / authors.length);
      });
    });
    const ranking = rank(raw);
    ranking.forEach(([author, value], index) => {
      const row = document.createElement("tr");
      row.append(cell("td", String(index + 1)), cell("th", author), cell("td", String(value)), cell("td", format.format(fractional.get(author) || 0)));
      ui.authorRanking.append(row);
    });
    if (!ranking.length) {
      const row = document.createElement("tr");
      const message = cell("td", "Nessun autore disponibile nei metadata correnti.");
      message.colSpan = 4;
      row.append(message);
      ui.authorRanking.append(row);
    }
    return ranking.map(([author]) => author);
  }

  function renderMatrix(host, data, entities, extractor, label) {
    host.replaceChildren();
    const years = yearRange(data);
    if (!entities.length || !years.length) {
      host.append(cell("p", `Dati insufficienti per l'evoluzione per ${label.toLowerCase()}.`));
      return;
    }
    const table = document.createElement("table");
    table.className = "bibliometric-matrix";
    const thead = document.createElement("thead");
    const header = document.createElement("tr");
    header.append(cell("th", label));
    years.forEach((year) => header.append(cell("th", String(year))));
    thead.append(header);
    table.append(thead);

    const body = document.createElement("tbody");
    const matrix = entities.map((entity) => {
      const byYear = new Map(years.map((year) => [year, 0]));
      data.forEach((record) => {
        const year = Number(record.year);
        if (byYear.has(year) && extractor(record).includes(entity)) byYear.set(year, byYear.get(year) + 1);
      });
      return [entity, byYear];
    });
    const maximum = Math.max(1, ...matrix.flatMap(([, byYear]) => [...byYear.values()]));
    matrix.forEach(([entity, byYear]) => {
      const row = document.createElement("tr");
      const name = cell("th", entity);
      name.scope = "row";
      row.append(name);
      years.forEach((year) => {
        const value = byYear.get(year) || 0;
        const valueCell = cell("td", String(value), "matrix-count");
        valueCell.dataset.level = value === 0 ? "0" : String(Math.max(1, Math.ceil((value / maximum) * 4)));
        valueCell.title = `${entity} · ${year}: ${value}`;
        row.append(valueCell);
      });
      body.append(row);
    });
    table.append(body);
    const scroll = document.createElement("div");
    scroll.className = "table-scroll";
    scroll.append(table);
    host.append(scroll);
  }

  function renderQuality(data) {
    const withYear = data.filter((record) => Number.isInteger(Number(record.year))).length;
    const withAuthors = data.filter((record) => authorsOf(record).length).length;
    const withVenue = data.filter((record) => venueOf(record)).length;
    const pct = (value) => data.length ? `${format.format((value / data.length) * 100)}%` : "—";
    ui.quality.textContent = `Copertura metadata nella vista: anno ${withYear}/${data.length} (${pct(withYear)}); autori ${withAuthors}/${data.length} (${pct(withAuthors)}); journal/sede ${withVenue}/${data.length} (${pct(withVenue)}). Le varianti nominali non vengono fuse automaticamente.`;
  }

  function render() {
    const data = records();
    const pendingCount = pending().length;
    const uniqueAuthors = new Set(data.flatMap(authorsOf));
    const uniqueVenues = new Set(data.map(venueOf).filter(Boolean));
    const years = yearRange(data);

    ui.total.textContent = String(data.length);
    ui.authors.textContent = String(uniqueAuthors.size);
    ui.venues.textContent = String(uniqueVenues.size);
    ui.years.textContent = years.length ? `${years[0]}–${years[years.length - 1]}` : "—";
    ui.scope.textContent = state.includePending
      ? `Vista esplorativa: corpus valutato + ${pendingCount} record ancora da analizzare. I metadata dei pending sono provvisori e la loro presenza non equivale a inclusione scientifica.`
      : `Vista predefinita: solo corpus valutato (${state.archive.length} record). Attiva il toggle per aggiungere i ${pendingCount} record ancora da analizzare.`;

    ui.empty.hidden = data.length !== 0;
    ui.content.hidden = data.length === 0;
    if (!data.length) return;

    renderAnnual(data);
    const journals = renderJournalRanking(data);
    renderMatrix(ui.journalEvolution, data, journals, (record) => venueOf(record) ? [venueOf(record)] : [], "Journal / sede");
    const authors = renderAuthorRanking(data);
    renderMatrix(ui.authorEvolution, data, authors, authorsOf, "Autore");
    renderQuality(data);
  }

  ui.toggle.addEventListener("change", (event) => {
    state.includePending = event.target.checked;
    render();
  });

  Promise.all([
    fetch("./data/archive.json", { cache: "no-store" }).then((response) => { if (!response.ok) throw new Error("archive unavailable"); return response.json(); }),
    fetch("./data/paper-register.json", { cache: "no-store" }).then((response) => { if (!response.ok) throw new Error("register unavailable"); return response.json(); }),
  ]).then(([archive, register]) => {
    state.archive = Array.isArray(archive.records) ? archive.records : [];
    state.register = Array.isArray(register.records) ? register.records : [];
    render();
  }).catch(() => {
    ui.error.hidden = false;
    ui.content.hidden = true;
    ui.empty.hidden = true;
  });
})();
