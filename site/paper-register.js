(() => {
  const list = document.querySelector("#registered-papers");
  const controls = document.querySelector("#register-controls");
  const count = document.querySelector("#register-count");
  if (!list || !controls || !count) return;

  const elements = {
    search: document.querySelector("#register-search"),
    year: document.querySelector("#register-year-filter"),
    author: document.querySelector("#register-author-filter"),
    venue: document.querySelector("#register-venue-filter"),
    review: document.querySelector("#register-review-filter"),
    access: document.querySelector("#register-access-filter"),
    sort: document.querySelector("#register-sort-order"),
  };

  const reviewLabels = {
    pending: "Da analizzare",
    needs_full_text: "Testo da esaminare",
    screened_eligible_core: "Valutato: core",
    screened_eligible_contextual: "Valutato: contestuale",
    screened_not_eligible: "Escluso",
    duplicate_confirmed: "Duplicato confermato",
    screened_not_academic: "Non accademico",
    screened_not_retrievable: "Non reperibile",
  };
  const accessLabels = {
    unknown: "Accesso da verificare",
    verification_pending: "Verifica accesso pendente",
    verified_open: "OA verificato",
    not_open: "Non open access",
  };

  const state = {
    query: "",
    year: "all",
    author: "all",
    venue: "all",
    review: "all",
    access: "all",
    sort: "newest",
  };
  let records = [];

  const el = (tag, text) => {
    const node = document.createElement(tag);
    node.textContent = text;
    return node;
  };

  function splitAuthors(value) {
    return String(value || "")
      .split(";")
      .map((author) => author.trim())
      .filter(Boolean);
  }

  function addOption(select, value, label) {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = label;
    select.append(option);
  }

  function populateFilters() {
    const years = [...new Set(records.map((record) => record.year).filter(Boolean))].sort((a, b) => b - a);
    years.forEach((year) => addOption(elements.year, String(year), String(year)));

    const authors = [...new Set(records.flatMap((record) => splitAuthors(record.authors)))].sort((a, b) => a.localeCompare(b, "it"));
    authors.forEach((author) => addOption(elements.author, author, author));

    const venues = [...new Set(records.map((record) => String(record.venue || "").trim()).filter(Boolean))].sort((a, b) => a.localeCompare(b, "it"));
    venues.forEach((venue) => addOption(elements.venue, venue, venue));

    const reviewStates = [...new Set(records.map((record) => record.reviewStatus).filter(Boolean))].sort();
    reviewStates.forEach((value) => addOption(elements.review, value, reviewLabels[value] || value));

    const accessStates = [...new Set(records.map((record) => record.accessStatus).filter(Boolean))].sort();
    accessStates.forEach((value) => addOption(elements.access, value, accessLabels[value] || value));
  }

  function filteredRecords() {
    const query = state.query.trim().toLocaleLowerCase("it");
    const found = records.filter((record) => {
      const haystack = [record.title, record.authors, record.doi, record.year, record.venue, record.topicCode]
        .join(" ")
        .toLocaleLowerCase("it");
      return (
        (!query || haystack.includes(query)) &&
        (state.year === "all" || String(record.year) === state.year) &&
        (state.author === "all" || splitAuthors(record.authors).includes(state.author)) &&
        (state.venue === "all" || String(record.venue || "").trim() === state.venue) &&
        (state.review === "all" || record.reviewStatus === state.review) &&
        (state.access === "all" || record.accessStatus === state.access)
      );
    });

    return found.sort((a, b) => {
      if (state.sort === "title") return String(a.title || "").localeCompare(String(b.title || ""), "it");
      const direction = state.sort === "oldest" ? 1 : -1;
      return ((Number(a.year) || 0) - (Number(b.year) || 0)) * direction || String(a.title || "").localeCompare(String(b.title || ""), "it");
    });
  }

  function render() {
    const found = filteredRecords();
    count.textContent = `${found.length} record visualizzati · ${records.length} registrati. Lavori da analizzare, non inclusioni scientifiche automatiche.`;
    list.replaceChildren();

    for (const record of found) {
      const row = document.createElement("tr");
      const citation = document.createElement("td");
      citation.append(
        el("strong", record.title),
        el("p", [record.authors, record.year, record.venue].filter(Boolean).join(" · ") || "Metadati da completare"),
      );
      const status = el("td", reviewLabels[record.reviewStatus] || "Da verificare");
      if (record.topicCode) status.append(el("p", `Etichetta: ${record.topicCode}`));
      status.append(el("p", record.metadataStatus === "metadata_verified" ? "Metadati verificati" : "Metadati da verificare"));
      const access = el("td", accessLabels[record.accessStatus] || "Accesso da verificare");
      const links = document.createElement("td");
      for (const [index, url] of (record.sourceLinks || []).entries()) {
        try {
          const parsed = new URL(url);
          if (!["https:", "http:"].includes(parsed.protocol) || parsed.username || parsed.password) continue;
          const anchor = el("a", `Fonte ${index + 1}`);
          anchor.href = url;
          anchor.rel = "noreferrer";
          links.append(anchor, document.createElement("br"));
        } catch (_) {
          continue;
        }
      }
      const review = el("a", "Analizza nel curatore");
      review.href = "./curate.html";
      links.append(review);
      row.append(citation, status, access, links);
      list.append(row);
    }

    if (!found.length) {
      const row = document.createElement("tr");
      const cell = el("td", records.length ? "Nessun record corrisponde ai filtri correnti." : "Nessun lavoro ancora registrato.");
      cell.colSpan = 4;
      row.append(cell);
      list.append(row);
    }
  }

  elements.search.addEventListener("input", (event) => { state.query = event.target.value; render(); });
  elements.year.addEventListener("change", (event) => { state.year = event.target.value; render(); });
  elements.author.addEventListener("change", (event) => { state.author = event.target.value; render(); });
  elements.venue.addEventListener("change", (event) => { state.venue = event.target.value; render(); });
  elements.review.addEventListener("change", (event) => { state.review = event.target.value; render(); });
  elements.access.addEventListener("change", (event) => { state.access = event.target.value; render(); });
  elements.sort.addEventListener("change", (event) => { state.sort = event.target.value; render(); });
  controls.addEventListener("reset", () => {
    window.setTimeout(() => {
      Object.assign(state, { query: "", year: "all", author: "all", venue: "all", review: "all", access: "all", sort: "newest" });
      render();
    });
  });

  fetch("./data/paper-register.json", { cache: "no-store" })
    .then((response) => {
      if (!response.ok) throw new Error("register unavailable");
      return response.json();
    })
    .then((payload) => {
      records = Array.isArray(payload.records) ? payload.records : [];
      populateFilters();
      render();
    })
    .catch(() => {
      count.textContent = "Il registro non è disponibile. Consultare il pannello del curatore o riprovare.";
      Object.values(elements).forEach((element) => { if (element) element.disabled = true; });
    });
})();
