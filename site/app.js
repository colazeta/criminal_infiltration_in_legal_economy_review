const state = {
  payload: null,
  query: "",
  topic: "all",
  year: "all",
  sort: "newest",
};

const elements = {
  list: document.querySelector("#paper-list"),
  empty: document.querySelector("#empty-state"),
  error: document.querySelector("#load-error"),
  count: document.querySelector("#result-count"),
  search: document.querySelector("#search-input"),
  topic: document.querySelector("#topic-filter"),
  year: document.querySelector("#year-filter"),
  sort: document.querySelector("#sort-order"),
  controls: document.querySelector("#archive-controls"),
};

function formatCode(value) {
  return (value || "")
    .replaceAll("_", " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function makeElement(tag, className, text) {
  const element = document.createElement(tag);
  if (className) element.className = className;
  if (text !== undefined && text !== null) element.textContent = text;
  return element;
}

function makeLink(label, href, className) {
  const link = makeElement("a", className, label);
  link.href = href;
  link.rel = "noreferrer";
  return link;
}

function paperCard(record) {
  const article = makeElement("article", "paper-card");
  const top = makeElement("div", "paper-card-top");
  const badges = makeElement("div", "badges");
  badges.append(
    makeElement("span", "badge badge-included", record.statusLabel),
    makeElement("span", "badge", record.topicLabel),
  );
  top.append(badges, makeElement("span", "record-id", record.id));

  const title = makeElement("h3");
  if (record.links?.doi) {
    title.append(makeLink(record.title, record.links.doi));
  } else {
    title.textContent = record.title;
  }

  const citation = makeElement("p", "citation");
  const citationParts = [
    record.authors,
    record.year,
    record.venue,
    record.volume && record.issue
      ? `${record.volume}(${record.issue})`
      : record.volume,
    record.pages,
  ].filter(Boolean);
  citation.textContent = citationParts.join(" · ");

  const details = makeElement("details", "record-details");
  const summary = makeElement("summary", null, "Why this record is included");
  const detailsGrid = makeElement("div", "details-grid");

  const relevance = makeElement("div");
  relevance.append(
    makeElement("h4", null, "Relevance note"),
    makeElement("p", null, record.reason || "No public relevance note available."),
  );

  const metadata = makeElement("dl");
  const rows = [
    ["Decision", formatCode(record.screeningDecision)],
    ["Screening stage", formatCode(record.screeningStage)],
    ["Scope fit", formatCode(record.scopeFit)],
    ["Document type", formatCode(record.documentType)],
    ["Publisher", record.publisher],
    ["Metadata confidence", formatCode(record.metadataConfidence)],
    ["DOI", record.doi],
  ];
  rows.forEach(([label, value]) => {
    if (!value) return;
    const wrapper = makeElement("div");
    wrapper.append(makeElement("dt", null, label), makeElement("dd", null, value));
    metadata.append(wrapper);
  });
  detailsGrid.append(relevance, metadata);
  details.append(summary, detailsGrid);

  const footer = makeElement("div", "paper-footer");
  footer.append(
    makeElement("span", null, `Source: ${record.sourceBasis || "canonical registry"}`),
  );
  if (record.links?.doi) {
    footer.append(makeLink("Open DOI ↗", record.links.doi, "paper-link"));
  }

  article.append(top, title, citation, details, footer);
  return article;
}

function filteredRecords() {
  if (!state.payload) return [];
  const query = state.query.trim().toLocaleLowerCase();
  const records = state.payload.records.filter((record) => {
    const haystack = [
      record.title,
      record.authors,
      record.venue,
      record.doi,
      record.topicLabel,
      record.reason,
    ]
      .join(" ")
      .toLocaleLowerCase();
    return (
      (!query || haystack.includes(query)) &&
      (state.topic === "all" || record.topicCode === state.topic) &&
      (state.year === "all" || String(record.year) === state.year)
    );
  });

  return records.sort((a, b) => {
    if (state.sort === "title") return a.title.localeCompare(b.title);
    const direction = state.sort === "oldest" ? 1 : -1;
    return ((a.year || 0) - (b.year || 0)) * direction || a.title.localeCompare(b.title);
  });
}

function render() {
  const records = filteredRecords();
  elements.list.replaceChildren(...records.map(paperCard));
  elements.list.setAttribute("aria-busy", "false");
  elements.count.textContent = `${records.length} publication${records.length === 1 ? "" : "s"} shown`;
  elements.empty.hidden = records.length !== 0;
}

function populateFilters(records) {
  const topics = [...new Map(records.map((record) => [record.topicCode, record.topicLabel]))]
    .filter(([code]) => code)
    .sort((a, b) => a[1].localeCompare(b[1]));
  topics.forEach(([code, label]) => {
    const option = makeElement("option", null, label);
    option.value = code;
    elements.topic.append(option);
  });

  const years = [...new Set(records.map((record) => record.year).filter(Boolean))].sort(
    (a, b) => b - a,
  );
  years.forEach((year) => {
    const option = makeElement("option", null, String(year));
    option.value = String(year);
    elements.year.append(option);
  });
}

function populateMetrics(payload) {
  const set = (selector, value) => {
    document.querySelector(selector).textContent = String(value);
  };
  set("#included-count", payload.counts.included);
  set("#editorial-count", payload.counts.editorialQueue);
  set("#archive-version", `v${payload.archiveVersion}`);
  set("#coverage-date", payload.searchCoverageThrough);
  set("#metadata-fix-count", payload.counts.metadataFix);
  set("#manual-review-count", payload.counts.manualReview);
  set("#abstract-review-count", payload.counts.abstractReview);
  set("#rejected-count", payload.counts.rejectedOmitted);
}

elements.search.addEventListener("input", (event) => {
  state.query = event.target.value;
  render();
});
elements.topic.addEventListener("change", (event) => {
  state.topic = event.target.value;
  render();
});
elements.year.addEventListener("change", (event) => {
  state.year = event.target.value;
  render();
});
elements.sort.addEventListener("change", (event) => {
  state.sort = event.target.value;
  render();
});
elements.controls.addEventListener("reset", () => {
  window.setTimeout(() => {
    state.query = "";
    state.topic = "all";
    state.year = "all";
    state.sort = "newest";
    render();
  });
});

fetch("./data/archive.json")
  .then((response) => {
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return response.json();
  })
  .then((payload) => {
    state.payload = payload;
    populateFilters(payload.records);
    populateMetrics(payload);
    render();
  })
  .catch(() => {
    elements.list.hidden = true;
    elements.error.hidden = false;
    elements.count.textContent = "Archive unavailable";
  });
