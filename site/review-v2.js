"use strict";
(() => {
  const $ = (id) => document.getElementById(id);
  const criteria = [["criminal_actor", "Attore o interesse criminale"], ["legal_economy", "Oggetto nell’economia legale"], ["sustained_relation", "Relazione sostenuta"], ["substantive_analysis", "Analisi sostanziale"]];
  let candidates = [], current = null, generation = 0;
  function el(tag, value) { const node = document.createElement(tag); if (value !== undefined) node.textContent = value; return node; }
  function message(value) { $("v2-status").textContent = value; }
  async function api(path, body) {
    const token = sessionStorage.getItem("criminal-infiltration-curator-session") || "";
    const csrf = sessionStorage.getItem("criminal-infiltration-curator-csrf") || "";
    const controller = new AbortController(), timer = setTimeout(() => controller.abort(), 15000);
    try {
      const response = await fetch(`/api/v2/${path}`, { method: body ? "POST" : "GET", signal: controller.signal,
        headers: { Authorization: `Bearer ${token}`, "X-CSRF-Token": csrf, ...(body ? { "Content-Type": "application/json" } : {}) }, body: body ? JSON.stringify(body) : undefined });
      const payload = await response.json();
      if (!response.ok) throw Error(payload.error?.message || payload.error?.code || `HTTP ${response.status}`);
      return payload;
    } finally { clearTimeout(timer); }
  }
  const blockerLabels = { open_access_schema_not_applied: "Schema delle verifiche OA da applicare", review_protocol_mismatch: "Protocollo della review da allineare al perimetro OA", private_database_not_bound: "Database privato da collegare", private_evidence_store_not_bound: "Archivio privato delle evidenze da collegare", durable_queue_not_bound: "Coda durevole da collegare", exa_budget_readiness_required: "Disponibilità e budget Exa da verificare", approved_daily_query_manifest_required: "Manifesto delle query giornaliere da confermare", review_not_activated: "Avvio V2 subordinato a snapshot, ripristino e collaudo delle fonti", schema_not_applied: "Schema del database da applicare" };
  function list() {
    const query = $("v2-filter").value.toLowerCase();
    $("v2-candidates").replaceChildren(...candidates.filter((c) => c.title.toLowerCase().includes(query)).map((c) => {
      const button = el("button", c.title); button.addEventListener("click", () => open(c.candidate_id)); return button;
    }));
  }
  async function refresh() {
    const serial = ++generation;
    try {
      const state = await api("status"); if (serial !== generation) return;
      $("v2-scope").textContent = state.review?.review_id || "PREPARAZIONE · LEGACY CONSERVATO";
      if (!state.review) {
        const article = $("v2-detail"); article.replaceChildren(el("h1", "Ambiente V2 in preparazione"), el("p", "Il corpus corrente resta nel suo stato originale. I seed sono ancora proposte; questa schermata non attribuisce eleggibilità."));
        const blockers = el("ul"); state.blockers.forEach((code) => blockers.append(el("li", blockerLabels[code] || code))); article.append(blockers);
        message(`Ontologia ${state.ontology_version} · ${state.protocol_version} · Nessun reset eseguito`); return;
      }
      const proposalId = new URL(window.location.href).searchParams.get("proposal");
      if (proposalId) {
        const proposal = await api(`proposal?id=${encodeURIComponent(proposalId)}`);
        const article = $("v2-detail"); article.replaceChildren(el("h1", "Proposta scientifica immutabile"), el("code", proposal.payload_sha256));
        table(article, proposal.payload.criteria.map((c) => ({ criterio: c.criterion_id, esito: c.outcome, motivazione: c.rationale, passi: c.evidence_span_ids.join(", ") })), ["criterio", "esito", "motivazione", "passi"]);
        article.append(el("p", proposal.payload.rationale), el("p", `Proposta: ${proposal.payload.decision} · Autore: ${proposal.proposed_by} · ${proposal.created_at}`));
        const sourceButton = el("button", "APRI FONTI E SCHEDA DEL CANDIDATO"); sourceButton.addEventListener("click", () => open(proposal.payload.candidate_id)); article.append(sourceButton);
        message("Verifica questo hash nella PR; modifiche successive richiedono una nuova approvazione."); return;
      }
      const data = await api("candidates"); if (serial !== generation) return;
      candidates = data.candidates; list(); message(`${candidates.length} candidati V2 · Le proposte richiedono una PR scientifica approvata`);
      $("v2-detail").replaceChildren(el("h1", "Coda della review"), el("p", candidates.length ? "Seleziona un lavoro dalla coda." : "Nessun candidato ammesso alla lavorazione. I seed non vengono importati automaticamente."));
    } catch (error) {
      $("v2-detail").replaceChildren(el("h1", "Accesso alla console richiesto"), el("p", "Accedi dalla console curatoriale e riapri Review V2.")); message(error.message);
    }
  }
  async function open(id) {
    const serial = ++generation;
    try {
      const data = await api(`candidate?id=${encodeURIComponent(id)}`); if (serial !== generation) return;
      current = data; const article = $("v2-detail"); article.replaceChildren(el("h1", data.candidate.title));
      const tabs = el("div"); tabs.className = "v2-actions"; const pane = el("section");
      for (const [label, render] of [["PUBBLICAZIONE", bibliography], ["EVIDENZE", evidence], ["OPEN ACCESS", access], ["QUATTRO CRITERI", decision], ["CRONOLOGIA", history]]) {
        const button = el("button", label); button.addEventListener("click", () => { pane.replaceChildren(); render(pane, data); }); tabs.append(button);
      }
      article.append(tabs, pane); bibliography(pane, data); message(`${id} · Versione record ${data.candidate.record_version} · Identità: ${data.candidate.identity_state}`);
    } catch (error) { message(error.message); }
  }
  function table(pane, rows, fields) {
    const table = el("table"), header = el("tr"); fields.forEach((f) => header.append(el("th", f))); table.append(header);
    rows.forEach((row) => { const tr = el("tr"); fields.forEach((f) => tr.append(el("td", row[f] ?? "—"))); table.append(tr); }); pane.append(table);
  }
  function bibliography(pane, data) {
    pane.append(el("h2", "Identità bibliografica"));
    table(pane, [data.work || {}], ["work_id", "title", "work_type", "original_language"]);
    pane.append(el("h2", "Autori e contributi")); table(pane, data.contributions, ["position", "display_name", "role", "affiliation_id"]);
    pane.append(el("h2", "Versioni e pubblicazione")); table(pane, data.expressions, ["expression_id", "version_type", "publication_date", "venue_id", "volume", "issue", "page_start", "page_end"]);
  }
  function evidence(pane, data) {
    pane.append(el("h2", "Fonti conservate e passi citabili"));
    data.evidence.forEach((source) => {
      const button = el("button", `${source.evidence_kind} · ${source.identity_state}`);
      button.addEventListener("click", async () => { try { const value = await api(`evidence?id=${encodeURIComponent(source.evidence_id)}`); if (!pane.isConnected || current !== data) return; const text = el("p", value.text); text.className = "source-text"; pane.append(text); } catch (error) { message(error.message); } });
      pane.append(button, el("p", source.source_url), el("code", source.content_sha256));
    });
    table(pane, data.spans, ["span_id", "locator", "evidence_kind", "identity_state"]);
    if (!data.evidence.length) pane.append(el("p", "Nessuna fonte acquisita. Un collegamento al PDF non vale come testo verificato."));
  }
  function access(pane, data) {
    pane.append(el("h2", "Verifica del testo integrale open access"), el("p", "Registra la verifica solo dopo aver aperto la copia integrale senza autenticazione e controllato identità, versione e autorizzazione al deposito. L’accesso non approva l’eleggibilità."));
    table(pane, data.access_history || [], ["assessment_id", "access_status", "version_type", "host_type", "full_text_url", "rights_evidence_url", "verified_at"]);
    const form = el("form"), controls = {}; form.className = "v2-form";
    for (const [name, label, options] of [["access_status", "Esito dell’accesso", ["unknown", "verified_open", "restricted", "revoked"]], ["evidence_id", "ID del testo integrale conservato"], ["full_text_url", "URL della copia integrale"], ["version_type", "Versione verificata", ["accepted", "version_of_record"]], ["host_type", "Responsabile della copia", ["repository", "publisher"]], ["rights_evidence_url", "URL della dichiarazione di licenza o deposito"], ["license_uri", "URI della licenza, se dichiarata"], ["rights_basis", "Base documentata per accesso e uso"]]) {
      const labelNode = el("label", label), input = el(options ? "select" : "input");
      if (options) options.forEach((value) => { const option = el("option", value); option.value = value; input.append(option); });
      labelNode.append(input); form.append(labelNode); controls[name] = input;
    }
    const attestation = el("input"); attestation.type = "checkbox";
    const label = el("label", "Ho verificato personalmente accesso anonimo, testo completo, identità, versione e diritti della copia."); label.prepend(attestation); form.append(label);
    const button = el("button", "REGISTRA VERIFICA DI ACCESSO"); button.type = "submit"; form.append(button); pane.append(form);
    const assessmentId = crypto.randomUUID();
    form.addEventListener("submit", async (event) => {
      event.preventDefault(); button.disabled = true;
      try {
        if (current !== data) throw Error("Riapri la scheda corrente.");
        const payload = Object.fromEntries(Object.entries(controls).map(([key, control]) => [key, control.value.trim() || null]));
        if (payload.access_status === "verified_open" && !attestation.checked) throw Error("La verifica esplicita è necessaria per attestare open access.");
        Object.assign(payload, { assessment_id: assessmentId, candidate_id: data.candidate.candidate_id, expected_version: data.candidate.record_version, supersedes_id: data.access_history?.at(-1)?.assessment_id || null, verification_method: payload.access_status === "verified_open" ? "anonymous_full_text_verified" : "access_observation" });
        await api("access-assessments", payload); await open(data.candidate.candidate_id); message("Accesso registrato; nessuna decisione scientifica creata.");
      } catch (error) { message(error.message); button.disabled = false; }
    });
  }
  function history(pane, data) {
    pane.append(el("h2", "Decisioni umane e supersessioni")); table(pane, data.decisions, ["decision", "rationale", "human_login", "pr_number", "created_at", "supersedes_id"]);
  }
  function decision(pane, data) {
    pane.append(el("h2", "Proposta di screening"), el("p", "Per ogni criterio seleziona un esito, spiega il ragionamento e indica gli ID dei passi. Le note generate non costituiscono evidenza."));
    const form = el("form"); form.className = "v2-form";
    const controls = {};
    function field(name, label, values) {
      const wrapper = el("label", label), control = el(values ? "select" : "textarea"); control.name = name;
      if (values) values.forEach((v) => { const option = el("option", v); option.value = v; control.append(option); });
      wrapper.append(control); form.append(wrapper); controls[name] = control; return control;
    }
    criteria.forEach(([key, label]) => { field(`${key}-outcome`, label, ["UNCERTAIN", "YES", "NO"]); field(`${key}-rationale`, "Motivazione specifica"); field(`${key}-spans`, "ID dei passi, separati da virgola"); });
    field("decision", "Esito proposto", ["needs_full_text", ...(data.access ? ["eligible_core", "eligible_contextual"] : []), "not_eligible", "duplicate", "not_academic", "not_retrievable"]);
    if (!data.access) pane.append(el("p", "Inclusione sospesa: occorre una verifica corrente del testo integrale open access."));
    field("stage", "Livello di lettura", ["title_abstract", "full_text", "seed_validation"]); field("confidence", "Confidenza", ["low", "medium", "high"]);
    field("rationale", "Motivazione complessiva"); field("exclusion_reason", "Codice di esclusione, se applicabile"); field("duplicate_target", "ID del duplicato prevalente, se applicabile");
    const button = el("button", "SALVA PROPOSTA PER REVISIONE UMANA"); button.type = "submit"; form.append(button); pane.append(form);
    const proposalId = crypto.randomUUID();
    form.addEventListener("submit", async (event) => {
      event.preventDefault(); button.disabled = true;
      try {
        if (current !== data) throw Error("Il candidato è cambiato. Riapri la scheda.");
        const value = (key) => controls[key].value.trim();
        const payload = { proposal_id: proposalId, review_id: data.review.review_id, candidate_id: data.candidate.candidate_id, expected_version: data.candidate.record_version, protocol_version: data.review.protocol_version,
          decision: value("decision"), stage: value("stage"), confidence: value("confidence"), rationale: value("rationale"), exclusion_reason: value("exclusion_reason"), duplicate_target: value("duplicate_target"),
          access_assessment_id: data.access?.assessment_id || null,
          supersedes_id: data.decisions.at(-1)?.decision_id || null,
          criteria: criteria.map(([key]) => ({ criterion_id: key, outcome: value(`${key}-outcome`), rationale: value(`${key}-rationale`), evidence_span_ids: value(`${key}-spans`).split(",").map((s) => s.trim()).filter(Boolean) })) };
        const result = await api("proposals", payload);
        pane.append(el("p", "Proposta privata salvata. Nessuna decisione o pubblicazione applicata."), el("code", result.payload_sha256));
        const prepared = await api("prepare-pr", { proposal_id: result.proposal_id });
        const link = el("a", "APRI LA RICHIESTA DI REVISIONE"); link.href = prepared.issue_url; link.rel = "noreferrer"; pane.append(link);
        message("PR scientifica richiesta; nessuna decisione applicata senza revisione umana.");
      } catch (error) { message(error.message); button.disabled = false; }
    });
  }
  $("v2-refresh").addEventListener("click", refresh); $("v2-filter").addEventListener("input", list); refresh();
})();
