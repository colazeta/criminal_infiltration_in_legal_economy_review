"use strict";

const amlState = {
  payload: null,
  query: "",
  year: "all",
  sort: "newest",
};

const amlElements = {
  list: document.querySelector("#aml-paper-list"),
  empty: document.querySelector("#aml-empty-state"),
  emptyTitle: document.querySelector("#aml-empty-title"),
  emptyCopy: document.querySelector("#aml-empty-copy"),
  error: document.querySelector("#aml-load-error"),
  count: document.querySelector("#aml-result-count"),
  search: document.querySelector("#aml-search-input"),
  year: document.querySelector("#aml-year-filter"),
  sort: document.querySelector("#aml-sort-order"),
  controls: document.querySelector("#aml-controls"),
};

function amlElement(tag, className, text) {
  const element = document.createElement(tag);
  if (className) element.className = className;
  if (text !== undefined && text !== null) element.textContent = text;
  return element;
}

function amlLink(label, href, className) {
  const link = amlElement("a", className, label);
  link.href = href;
  link.rel = "noreferrer";
  return link;
}

function amlFormatCode(value) {
  return String(value || "")
    .replaceAll("_", " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function amlPaperCard(record) {
  const article = amlElement("article", "paper-card secondary-paper-card");
  const top = amlElement("div", "paper-card-top");
  const badges = amlElement("div", "badges");
  badges.append(
    amlElement("span", "badge badge-secondary", record.statusLabel),
    amlElement("span", "badge", record.collectionLabel),
  );
  top.append(badges, amlElement("span", "record-id", record.id));

  const title = amlElement("h3");
  if (record.links?.doi) title.append(amlLink(record.title, record.links.doi));
  else title.textContent = record.title;

  const citation = amlElement("p", "citation");
  citation.textContent = [
    record.authors,
    record.year,
    record.venue,
    record.volume && record.issue ? `${record.volume}(${record.issue})` : record.volume,
    record.pages,
  ]
    .filter(Boolean)
    .join(" · ");

  const details = amlElement("details", "record-details");
  const summary = amlElement("summary", null, "Why this record is retained");
  const grid = amlElement("div", "details-grid");
  const relevance = amlElement("div");
  relevance.append(
    amlElement("h4", null, "Broader relevance note"),
    amlElement("p", null, record.reason),
  );
  const metadata = amlElement("dl");
  [
    ["Core decision", amlFormatCode(record.screeningDecision)],
    ["Core exclusion reason", record.exclusionReasonLabel],
    ["Screening stage", amlFormatCode(record.screeningStage)],
    ["Document type", amlFormatCode(record.documentType)],
    ["Publisher", record.publisher],
    ["Metadata confidence", amlFormatCode(record.metadataConfidence)],
    ["DOI", record.doi],
  ].forEach(([label, value]) => {
    if (!value) return;
    const row = amlElement("div");
    row.append(amlElement("dt", null, label), amlElement("dd", null, value));
    metadata.append(row);
  });
  grid.append(relevance, metadata);
  details.append(summary, grid);

  const footer = amlElement("div", "paper-footer");
  footer.append(amlElement("span", null, `Source: ${record.sourceBasis}`));
  if (record.links?.doi) footer.append(amlLink("Open DOI ↗", record.links.doi, "paper-link"));
  article.append(top, title, citation, details, footer);
  return article;
}

function amlFilteredRecords() {
  if (!amlState.payload) return [];
  const query = amlState.query.trim().toLocaleLowerCase();
  const records = amlState.payload.records.filter((record) => {
    const haystack = [
      record.title,
      record.authors,
      record.venue,
      record.doi,
      record.exclusionReasonLabel,
      record.reason,
    ]
      .join(" ")
      .toLocaleLowerCase();
    return (
      (!query || haystack.includes(query)) &&
      (amlState.year === "all" || String(record.year) === amlState.year)
    );
  });
  return records.sort((left, right) => {
    if (amlState.sort === "title") return left.title.localeCompare(right.title);
    const direction = amlState.sort === "oldest" ? 1 : -1;
    return (
      ((left.year || 0) - (right.year || 0)) * direction ||
      left.title.localeCompare(right.title)
    );
  });
}

function amlRender() {
  const records = amlFilteredRecords();
  const collectionIsEmpty = amlState.payload && amlState.payload.records.length === 0;
  amlElements.list.replaceChildren(...records.map(amlPaperCard));
  amlElements.list.setAttribute("aria-busy", "false");
  amlElements.count.textContent = `${records.length} related publication${records.length === 1 ? "" : "s"} shown`;
  amlElements.empty.hidden = records.length !== 0;
  if (records.length === 0 && collectionIsEmpty) {
    amlElements.emptyTitle.textContent = "No related records are currently public";
    amlElements.emptyCopy.textContent =
      "The collection structure is active, but no work has yet completed canonical verification and secondary publication approval.";
  } else if (records.length === 0) {
    amlElements.emptyTitle.textContent = "No related records match these filters";
    amlElements.emptyCopy.textContent = "Clear one or more filters to return to the full related collection.";
  }
}

function amlPopulateYears(records) {
  const years = [...new Set(records.map((record) => record.year).filter(Boolean))].sort(
    (left, right) => right - left,
  );
  years.forEach((year) => {
    const option = amlElement("option", null, year);
    option.value = String(year);
    amlElements.year.append(option);
  });
}

function amlWireControls() {
  amlElements.search.addEventListener("input", (event) => {
    amlState.query = event.target.value;
    amlRender();
  });
  amlElements.year.addEventListener("change", (event) => {
    amlState.year = event.target.value;
    amlRender();
  });
  amlElements.sort.addEventListener("change", (event) => {
    amlState.sort = event.target.value;
    amlRender();
  });
  amlElements.controls.addEventListener("reset", () => {
    requestAnimationFrame(() => {
      amlState.query = "";
      amlState.year = "all";
      amlState.sort = "newest";
      amlRender();
    });
  });
}

amlWireControls();

fetch("./data/secondary-collections.json")
  .then((response) => {
    if (!response.ok) throw new Error("Related collection request failed");
    return response.json();
  })
  .then((payload) => {
    amlState.payload = payload;
    document.querySelector("#aml-record-count").textContent = payload.counts.records;
    document.querySelector("#aml-collection-count").textContent = payload.collections.length;
    document.querySelector("#aml-archive-version").textContent = payload.archiveVersion;
    document.querySelector("#aml-coverage-date").textContent = payload.searchCoverageThrough;
    amlPopulateYears(payload.records);
    amlRender();
  })
  .catch(() => {
    amlElements.list.setAttribute("aria-busy", "false");
    amlElements.count.textContent = "Related collection unavailable";
    amlElements.error.hidden = false;
  });
