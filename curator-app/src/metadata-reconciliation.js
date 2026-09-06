"use strict";

import { cleanDoi, titleSimilarity } from "./scholarly-providers.js";

const FIELD_AUTHORITY = Object.freeze({
  doi: ["Crossref", "OpenCitations Meta", "DataCite", "OpenAlex", "Semantic Scholar", "DOAJ", "CORE", "Europe PMC", "Zenodo", "HAL", "arXiv"],
  title: ["Crossref", "OpenCitations Meta", "DataCite", "OpenAlex", "Semantic Scholar", "DOAJ", "CORE", "Europe PMC", "Zenodo", "HAL", "arXiv"],
  year: ["Crossref", "OpenCitations Meta", "DataCite", "OpenAlex", "Semantic Scholar", "DOAJ", "Europe PMC", "CORE", "Zenodo", "HAL", "arXiv"],
  authors: ["Crossref", "OpenAlex", "ORCID", "OpenCitations Meta", "Semantic Scholar", "DataCite", "Europe PMC", "DOAJ", "CORE", "HAL", "Zenodo", "arXiv"],
  venue: ["Crossref", "OpenAlex", "OpenCitations Meta", "Semantic Scholar", "Europe PMC", "DOAJ", "CORE", "HAL", "Zenodo", "arXiv"],
});

function cleanText(value, maximum = 3000) {
  return String(value || "").replace(/\s+/g, " ").trim().slice(0, maximum);
}

function normaliseText(value) {
  return cleanText(value, 3000)
    .normalize("NFKD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, " ")
    .trim();
}

function normaliseAuthors(value) {
  return normaliseText(value)
    .split(/\s*;\s*/)
    .map((part) => part.trim())
    .filter(Boolean)
    .sort()
    .join(";");
}

function providerWeight(field, provider) {
  const rank = FIELD_AUTHORITY[field]?.indexOf(provider) ?? -1;
  if (rank < 0) return 1;
  return Math.max(2, 12 - rank);
}

function observationValue(observation, field) {
  if (!observation) return "";
  if (field === "title") return cleanText(observation.matchedTitle || observation.title, 1000);
  if (field === "year") return observation.matchedYear || observation.year || "";
  if (field === "doi") return cleanDoi(observation.matchedDoi || observation.doi);
  return cleanText(observation[field], 3000);
}

function valueKey(field, value) {
  if (!value && value !== 0) return "";
  if (field === "doi") return cleanDoi(value).toLowerCase();
  if (field === "year") return String(Number(value) || "");
  if (field === "authors") return normaliseAuthors(value);
  return normaliseText(value);
}

function reconcileField(field, observations) {
  const groups = new Map();
  for (const observation of observations) {
    const value = observationValue(observation, field);
    const key = valueKey(field, value);
    if (!key) continue;
    if (!groups.has(key)) groups.set(key, { key, value, providers: [], score: 0, observations: [] });
    const group = groups.get(key);
    if (!group.providers.includes(observation.provider)) group.providers.push(observation.provider);
    group.score += providerWeight(field, observation.provider);
    group.observations.push(observation);
    if (cleanText(value).length > cleanText(group.value).length) group.value = value;
  }
  const ranked = [...groups.values()].sort((left, right) => right.score - left.score || right.providers.length - left.providers.length);
  if (!ranked.length) {
    return { value: "", status: "missing", confidence: "none", providers: [], alternatives: [] };
  }
  const best = ranked[0];
  const alternatives = ranked.slice(1).map((group) => ({
    value: group.value,
    providers: group.providers,
    score: group.score,
  }));
  let status = alternatives.length ? "conflict" : "verified";
  let confidence = best.providers.length >= 2 ? "high" : best.score >= 10 ? "high" : "medium";
  if (alternatives.length) {
    const second = alternatives[0];
    const decisive = best.score >= second.score * 1.75 && best.providers.length >= 2;
    if (decisive) {
      status = "resolved_conflict";
      confidence = "medium";
    } else {
      confidence = "low";
    }
  }
  return {
    value: field === "year" ? Number(best.value) || best.value : best.value,
    status,
    confidence,
    providers: best.providers,
    supportScore: best.score,
    alternatives,
  };
}

function uniqueManifestations(observations) {
  const rows = new Map();
  for (const observation of observations) {
    const doi = cleanDoi(observation?.matchedDoi || observation?.doi).toLowerCase();
    const sourceId = cleanText(observation?.sourceId, 500).toLowerCase();
    const key = doi ? `doi:${doi}` : sourceId || "";
    if (!key) continue;
    if (!rows.has(key)) {
      rows.set(key, {
        key,
        doi,
        sourceIds: [],
        providers: [],
        title: cleanText(observation?.matchedTitle || observation?.title, 1000),
        year: Number(observation?.matchedYear || observation?.year) || null,
        relations: [],
      });
    }
    const row = rows.get(key);
    if (sourceId && !row.sourceIds.includes(sourceId)) row.sourceIds.push(sourceId);
    if (observation.provider && !row.providers.includes(observation.provider)) row.providers.push(observation.provider);
    for (const relation of observation.relations || []) {
      if (relation && !row.relations.includes(relation)) row.relations.push(relation);
    }
  }
  return [...rows.values()];
}

function manifestationAssessment(observations, titleField, doiField) {
  const manifestations = uniqueManifestations(observations);
  const doiManifestations = manifestations.filter((row) => row.doi);
  let ambiguity = false;
  const reasons = [];
  if (doiField.status === "conflict" && doiManifestations.length > 1) {
    const highTitleAgreement = doiManifestations.every((row) => !row.title || !titleField.value || titleSimilarity(row.title, titleField.value) >= 0.84);
    if (highTitleAgreement) {
      ambiguity = true;
      reasons.push("multiple DOI manifestations share a strongly matching title");
    }
  }
  const relationSignals = manifestations.flatMap((row) => row.relations).filter((relation) => /version|isversion|preprint|published|alternate|related/i.test(relation));
  if (relationSignals.length) {
    ambiguity = true;
    reasons.push("provider relations indicate multiple versions or manifestations");
  }
  return { ambiguity, reasons, manifestations };
}

function reconcileMetadata({ requested = {}, observations = [] } = {}) {
  const cleanObservations = observations.filter((entry) => entry && entry.provider);
  const queueObservation = {
    provider: "Queue record",
    matchedTitle: cleanText(requested.title, 1000),
    matchedYear: Number(requested.year) || null,
    matchedDoi: cleanDoi(requested.doi),
    authors: cleanText(requested.authors, 3000),
    venue: cleanText(requested.venue, 1000),
  };
  if (queueObservation.matchedTitle) cleanObservations.unshift(queueObservation);

  const fields = {
    title: reconcileField("title", cleanObservations),
    doi: reconcileField("doi", cleanObservations),
    year: reconcileField("year", cleanObservations),
    authors: reconcileField("authors", cleanObservations),
    venue: reconcileField("venue", cleanObservations),
  };
  const manifestation = manifestationAssessment(cleanObservations, fields.title, fields.doi);
  const unresolvedConflicts = Object.entries(fields)
    .filter(([, result]) => result.status === "conflict")
    .map(([field]) => field);
  const missingIdentityFields = ["title", "year"]
    .filter((field) => fields[field].status === "missing");

  let identityState = "verified";
  if (manifestation.ambiguity) identityState = "manifestation_ambiguity";
  else if (unresolvedConflicts.some((field) => ["title", "doi", "year"].includes(field))) identityState = "conflict";
  else if (missingIdentityFields.length || fields.doi.status === "missing") identityState = "partial";

  return {
    schemaVersion: 1,
    identityState,
    screeningReady: !["manifestation_ambiguity", "conflict"].includes(identityState),
    fields,
    manifestation,
    unresolvedConflicts,
    providerCount: new Set(cleanObservations.map((entry) => entry.provider)).size,
    providers: [...new Set(cleanObservations.map((entry) => entry.provider))],
    note: "Preparatory field-level reconciliation only; it does not update canonical metadata or decide eligibility.",
  };
}

export { FIELD_AUTHORITY, reconcileMetadata };
