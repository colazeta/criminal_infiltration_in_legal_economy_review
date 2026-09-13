/* Public, non-decisional paper-sheet support. All external text uses textContent. */
(() => {
  "use strict";
  const bibliographyKeys = ["title", "authors", "year", "venue", "doi"];
  const kindLabels = {
    verified_abstract_source: "Sintesi dell’abstract — non testo originale",
    publisher_summary: "Sintesi della descrizione editoriale",
    full_text_intro: "Sintesi da introduzione o testo consultato",
    review_synopsis: "Sintesi preliminare — da verificare",
    metadata_warning: "Avvertenza sui metadati",
  };
  const accessLabels = { open: "Accesso aperto verificato alla fonte indicata", restricted: "Accesso limitato", unknown: "Accesso non determinato" };
  const retrievalLabels = {
    full_text: "Collegamento al testo individuato", open_access: "Localizzazione OA individuata",
    landing: "Pagina del paper individuata", doi_only: "Solo DOI", unresolved: "Da risolvere",
    source_only: "Solo collegamento alla fonte",
  };
  const el = (tag, value) => {
    const node = document.createElement(tag);
    if (value !== undefined && value !== null) node.textContent = String(value);
    return node;
  };
  function safeUrl(value) {
    try {
      if (typeof value !== "string" || !value || value.length > 2000 || /[\u0000-\u001f]/.test(value)) return "";
      const url = new URL(value);
      return url.protocol === "https:" && !url.username && !url.password ? url.href : "";
    } catch (_) { return ""; }
  }
  function link(parent, label, value) {
    const href = safeUrl(value);
    if (!href) return;
    const anchor = el("a", label);
    anchor.href = href;
    anchor.rel = "noreferrer";
    const line = el("p");
    line.append(anchor);
    parent.append(line);
  }
  function metadata(parent, entries) {
    const dl = el("dl");
    for (const [label, value] of entries) {
      if (value !== null && value !== undefined && value !== "") dl.append(el("dt", label), el("dd", value));
    }
    parent.append(dl);
  }
  function selectRecord(payload, record) {
    if (!payload || payload.schemaVersion !== 1 || !Array.isArray(payload.records)) throw new Error("invalid_support");
    const ids = new Set();
    for (const item of payload.records) {
      if (!item || typeof item.id !== "string" || ids.has(item.id)) throw new Error("invalid_support_identity");
      ids.add(item.id);
    }
    const found = payload.records.find((item) => item.id === record.id);
    if (!found || !found.bibliography || bibliographyKeys.some((key) => found.bibliography[key] !== record[key])) throw new Error("support_revision_mismatch");
    return found;
  }
  function render(parent, support, record) {
    parent.replaceChildren(el("h3", "Abstract e sintesi"));
    const aid = support.readingAid;
    const abstract = support.abstract;
    if (aid && Object.hasOwn(kindLabels, aid.kind) && aid.synopsis) {
      parent.append(el("h4", kindLabels[aid.kind]), el("p", aid.synopsis));
      metadata(parent, [["Fonte della sintesi", aid.sourceLabel], ["Sintesi verificata il", aid.checkedAt]]);
      link(parent, aid.kind === "verified_abstract_source" ? "Consulta la fonte dell’abstract" : "Consulta la fonte della sintesi", aid.sourceUrl);
    } else {
      parent.append(el("p", "Non è ancora disponibile una sintesi pubblicabile per questo record."));
    }
    if (abstract?.status === "available") {
      parent.append(el("p", "Disponibilità dell’abstract verificata. Il testo originale non è riprodotto in questa scheda; consulta la fonte. La sintesi, quando presente, resta distinta dall’abstract originale."));
      metadata(parent, [["Fonte dell’abstract", abstract.source], ["Disponibilità verificata il", abstract.checkedAt]]);
      link(parent, "Apri la fonte dell’abstract", abstract.sourceUrl);
    } else if (aid?.kind !== "verified_abstract_source") {
      parent.append(el("p", "La disponibilità dell’abstract originale non risulta verificata per questa scheda."));
    }
    const retrieval = support.retrieval;
    const access = support.access;
    parent.append(el("h3", "Metadati arricchiti e reperibilità"));
    if (!retrieval && !access) parent.append(el("p", "Nessun ulteriore metadato di reperibilità è ancora disponibile."));
    if (retrieval) {
      metadata(parent, [
        ["Reperibilità", retrievalLabels[retrieval.status] || retrieval.status],
        ["DOI individuato dal resolver", retrieval.resolvedDoi],
        ["Corrispondenza bibliografica", retrieval.matchConfidence],
        ["Metodo di corrispondenza", retrieval.matchMethod],
        ["Reperibilità verificata il", retrieval.checkedAt],
      ]);
      if (retrieval.resolvedDoi && record.doi && retrieval.resolvedDoi.toLowerCase() !== record.doi.toLowerCase()) {
        parent.append(el("p", "Il DOI individuato differisce da quello registrato: la riconciliazione resta da verificare. Nessun identificativo è stato sostituito automaticamente."));
      }
      const seen = new Set();
      for (const [label, value] of [
        ["Collegamento al testo — accesso verificato separatamente", retrieval.fullTextUrl],
        ["Localizzazione ad accesso aperto indicata dal resolver", retrieval.openAccessUrl],
        ["Pagina del paper", retrieval.landingUrl], ["DOI individuato", retrieval.doiUrl],
        ["Miglior collegamento disponibile", retrieval.bestUrl],
      ]) {
        const href = safeUrl(value);
        if (href && !seen.has(href)) { link(parent, label, href); seen.add(href); }
      }
    }
    if (access) {
      metadata(parent, [
        ["Ultima valutazione dell’accesso", accessLabels[access.status] || access.status],
        ["Tipo di verifica dell’accesso", access.kind], ["Fonte della verifica", access.source],
        ["Accesso verificato il", access.checkedAt],
      ]);
      link(parent, "Fonte della valutazione dell’accesso", access.url);
    }
    parent.append(el("p", "Un collegamento al testo non prova, da solo, l’accesso aperto. Sintesi e metadati arricchiti non costituiscono una valutazione scientifica del paper."));
    parent.setAttribute("aria-busy", "false");
  }
  async function load(parent, record, isCurrent = () => true) {
    if (!isCurrent()) return;
    parent.setAttribute("aria-busy", "true");
    parent.replaceChildren(el("h3", "Abstract e metadati arricchiti"), el("p", "Caricamento dei dati aggiornati…"));
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 12000);
    try {
      const response = await fetch("./paper-support.json", { cache: "no-store", signal: controller.signal });
      if (!response.ok) throw new Error("support_unavailable");
      const support = selectRecord(await response.json(), record);
      if (isCurrent()) render(parent, support, record);
    } catch (_) {
      if (isCurrent()) {
        parent.replaceChildren(el("h3", "Abstract e metadati arricchiti"), el("p", "Non è stato possibile verificare i dati aggiornati della scheda. Questo non significa che l’abstract sia assente. Ricarica la pagina e riapri la scheda."));
        parent.setAttribute("aria-busy", "false");
      }
    } finally { clearTimeout(timeout); }
  }
  globalThis.CILEPaperSheetSupport = { render, load, selectRecord, safeUrl };
})();
