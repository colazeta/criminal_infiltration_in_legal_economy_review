"use strict";
(() => {
  let model, selected, group = "all";
  const $ = (id) => document.getElementById(id);
  function el(tag, value) { const node = document.createElement(tag); if (value !== undefined) node.textContent = value; return node; }
  function renderDetail(name) {
    selected = name;
    const concept = model.entities.find((e) => e.table === name), article = $("concept-detail");
    article.replaceChildren(el("h1", concept.label), el("p", concept.description), el("code", `${concept.class} · ${concept.table}`));
    const note = el("p", concept.appendOnly ? "Cronologia immutabile: le correzioni aggiungono una nuova registrazione; lo storico resta leggibile." : "Entità bibliografica od operativa. Nessuna eleggibilità deriva dalla sola presenza del record.");
    note.className = "notice"; article.append(note);
    const table = el("table"), head = el("thead"), hr = el("tr");
    ["ATTRIBUTO", "SIGNIFICATO", "TIPO", "CORRISPONDENZA"].forEach((title) => hr.append(el("th", title)));
    head.append(hr); table.append(head); const body = el("tbody");
    for (const field of concept.fields) {
      const row = el("tr"), nameCell = el("td"); nameCell.append(el("code", field.name));
      row.append(nameCell, el("td", field.description), el("td", `${field.type}${field.nullable ? " · facoltativo" : " · richiesto"}`), el("td", field.semantic)); body.append(row);
    }
    table.append(body); article.append(table, el("h2", "Vincoli"));
    const list = el("ul"); concept.constraints.forEach((rule) => list.append(el("li", rule))); article.append(list);
    $("concept-list").querySelectorAll("button").forEach((button) => button.setAttribute("aria-current", String(button.dataset.table === name)));
  }
  function renderList() {
    const query = $("concept-filter").value.toLowerCase();
    const matches = model.entities.filter((e) => (group === "all" || e.group === group) && `${e.label} ${e.class} ${e.fields.map((f) => f.name).join(" ")}`.toLowerCase().includes(query));
    $("concept-list").replaceChildren(...matches.map((e) => { const button = el("button", e.label); button.dataset.table = e.table; button.setAttribute("aria-current", String(e.table === selected)); button.addEventListener("click", () => renderDetail(e.table)); return button; }));
    $("model-status").textContent = `${matches.length} entità visualizzate · ${model.entities.length} entità totali · Contratto ${model.version} · Definizioni, senza dati del corpus`;
  }
  fetch("./vocab/review-v2-model.json").then((r) => { if (!r.ok) throw Error(); return r.json(); }).then((value) => {
    model = value; renderList(); renderDetail("scholarly_works");
    $("concept-filter").addEventListener("input", renderList);
    document.querySelectorAll("[data-group]").forEach((button) => button.addEventListener("click", () => { group = button.dataset.group; document.querySelectorAll("[data-group]").forEach((b) => b.setAttribute("aria-pressed", String(b === button))); renderList(); }));
  }).catch(() => { $("model-status").textContent = "Contratto non disponibile. Ricaricare la pagina."; });
})();
