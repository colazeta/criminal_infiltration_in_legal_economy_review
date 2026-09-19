#!/usr/bin/env python3
"""Generate public schema documentation, never corpus or reviewer data."""
import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LABELS = {
    "enrichment_schedules": "Pianificazione oraria", "enrichment_iterations": "Iterazioni previste", "enrichment_iteration_attempts": "Tentativi delle iterazioni",
    "access_assessments_v2": "Verifiche open access", "reviews": "Review e protocollo", "scholarly_works": "Opera scientifica", "agents": "Autori e organizzazioni",
    "publication_venues": "Rivista, volume e collana", "expressions": "Versione della pubblicazione", "contributions": "Autori, ruoli e affiliazioni",
    "document_sections": "Sezioni del paper", "publication_declarations": "Dichiarazioni della pubblicazione", "manifestations": "Copie digitali e accesso",
    "bibliographic_identifiers": "DOI e altri identificatori", "metadata_assertions": "Metadati e fonti discordanti", "citation_relations": "Citazioni bibliografiche",
    "work_relations_v2": "Correzioni e relazioni fra opere", "review_candidates": "Candidati nella review", "legacy_references": "Riferimenti allo storico",
    "retrieval_attempts": "Tentativi di acquisizione", "evidence_sources": "Fonti di evidenza", "evidence_spans": "Passi e locator",
    "decision_proposals": "Proposte scientifiche", "approval_receipts": "Approvazioni umane", "screening_decisions_v2": "Decisioni di screening",
    "criterion_assessments": "Quattro criteri di eleggibilità", "coding_assertions_v2": "Codifica analitica", "assistant_observations": "Osservazioni dell’assistente",
    "publication_approvals_v2": "Pubblicazione sul sito", "search_days": "Calendario delle ricerche", "run_attempts": "Esecuzioni e recuperi",
    "query_executions": "Query e risultati misurati", "discovery_occurrences": "Occorrenze di discovery", "outbox": "Operazioni da consegnare",
    "operational_events": "Registro operativo", "legacy_snapshots": "Conservazione e ripristino",
}
BIBLIOGRAPHY = {"scholarly_works", "agents", "publication_venues", "expressions", "contributions", "document_sections", "publication_declarations", "manifestations", "bibliographic_identifiers", "metadata_assertions", "citation_relations", "work_relations_v2"}
DESCRIPTIONS = {
    "work_id": "Identità intellettuale dell’opera, indipendente dall’inclusione nella review.",
    "title": "Titolo attestato dalla fonte, senza completamenti inferiti.",
    "work_type": "Tipo documentale: articolo, capitolo, libro, working paper, preprint, atti, rapporto o tesi.",
    "original_language": "Lingua originale documentata; resta vuota quando non è nota.",
    "created_at": "Data e ora della registrazione, distinta dalla data di pubblicazione.",
    "expression_id": "Versione del contenuto: manoscritto accettato, versione editoriale, revisione o traduzione.",
    "version_type": "Stato editoriale della versione; non determina l’eleggibilità scientifica.",
    "version_label": "Denominazione della versione riportata dalla fonte.",
    "language": "Lingua di questa specifica versione del testo.",
    "publication_date": "Data di pubblicazione attestata, conservando la precisione disponibile.",
    "date_precision": "Anno, mese o giorno: non si inventano componenti mancanti della data.",
    "venue_id": "Rivista, libro collettaneo, collana, congresso o repository che contiene la versione.",
    "publisher_id": "Organizzazione responsabile della pubblicazione.",
    "volume": "Volume della rivista o serie come indicato nella citazione.",
    "issue": "Fascicolo, distinto dal volume.",
    "page_start": "Prima pagina, anche con numerazione romana o alfanumerica.",
    "page_end": "Ultima pagina; non viene calcolata se non è attestata.",
    "article_number": "Numero o identificatore editoriale dell’articolo, alternativo alla paginazione.",
    "edition": "Edizione della pubblicazione, distinta dal file scaricato.",
    "source_url": "Indirizzo della fonte da cui deriva l’informazione; non prova da solo l’acquisizione del testo.",
    "observed_at": "Momento in cui la fonte è stata osservata.",
    "agent_id": "Identità della persona, organizzazione o software; omonimie non fuse automaticamente.",
    "agent_type": "Persona, organizzazione oppure software, con responsabilità distinte.",
    "display_name": "Nome attestato completo per la visualizzazione.",
    "family_name": "Cognome o componente familiare del nome, solo se attestato.",
    "given_name": "Nome personale, senza espandere iniziali per inferenza.",
    "role": "Autore, curatore editoriale, traduttore, collaboratore o finanziatore.",
    "position": "Ordine dichiarato nella pubblicazione; l’ordine degli autori viene conservato.",
    "credit_role_uri": "Ruolo CRediT attestato dalla fonte, quando presente.",
    "affiliation_id": "Affiliazione dell’autore per questa specifica pubblicazione.",
    "scheme": "Sistema identificativo: DOI, ISBN, ISSN, ORCID, ROR, handle, arXiv, PMID o URL stabile.",
    "value": "Valore dell’identificatore; la sua uguaglianza non implica automaticamente identità fra opere.",
    "verification_status": "Proposto, verificato o contestato, con fonte conservata.",
    "manifestation_id": "Copia o rappresentazione digitale di una versione del contenuto.",
    "media_type": "Formato effettivamente osservato: per esempio PDF, HTML o testo.",
    "content_sha256": "Impronta dei byte conservati per riconoscere cambiamenti e verificare il ripristino.",
    "storage_key": "Riferimento interno al documento privato; non è un URL pubblico.",
    "license_uri": "Licenza dichiarata per questa copia, senza dedurla dalla sola accessibilità.",
    "rights_basis": "Base documentata per conservare e usare il materiale.",
    "access_status": "Accesso aperto verificato, limitato o ignoto.",
    "acquisition_status": "Solo collegamento, documento acquisito oppure acquisizione fallita.",
    "section_type": "Abstract, introduzione, contesto, metodi, risultati, discussione, conclusioni, limiti, riferimenti o appendice.",
    "heading": "Intestazione della sezione così come compare nel testo.",
    "locator": "Pagina, sezione o riferimento preciso che permette di ritrovare il passo.",
    "declaration_type": "Finanziamenti, conflitti di interesse, etica, disponibilità di dati/codice, rettifica o ritrattazione.",
    "statement": "Dichiarazione attribuita alla fonte; assenza e negazione esplicita restano diverse.",
    "field_uri": "Proprietà semantica cui si riferisce l’asserzione di metadato.",
    "value_json": "Valore attestato dalla fonte, compresi valori in conflitto con altre fonti.",
    "attributed_to": "Agente responsabile dell’asserzione o dell’attività.",
    "supersedes_id": "Registrazione precedente sostituita da questa, conservata nello storico.",
    "citing_work_id": "Opera che contiene il riferimento bibliografico.",
    "cited_work_id": "Opera citata: una similarità tematica non vale come citazione.",
    "review_id": "Namespace della review; impedisce di ereditare decisioni da un altro corpus.",
    "candidate_id": "Record candidato in questa review, senza eleggibilità implicita.",
    "record_version": "Versione usata per rifiutare modifiche o approvazioni su dati superati.",
    "criterion_id": "Uno dei quattro criteri separati del test di inclusione.",
    "outcome": "YES, NO oppure UNCERTAIN: la mancanza di testo non equivale a NO.",
    "rationale": "Motivazione specifica e attribuita della valutazione.",
    "evidence_span_ids_json": "Passi delle fonti che sostengono la valutazione.",
    "scheduled_date": "Giorno previsto nel calendario di Roma, distinto dal momento reale dell’esecuzione.",
    "occurrences_returned": "Risultati della singola query: null se non misurati, zero se realmente misurati e assenti.",
}


def build():
    profile = json.loads((ROOT / "ontology/cile-review-profile.yaml").read_text())
    import sys
    sys.path.insert(0, str(ROOT))
    from scripts.architecture.catalogue import catalogue
    physical, trace = catalogue(ROOT)
    slots = {(row['table'], row['column']): row['slot'] for row in trace}
    entities = []
    for item in physical['tables']:
        table = item['table']
        fields = []
        for row in item['columns']:
            name = slots[(table, row['name'])]
            slot = profile['slots'].get(name, {'description': row['name'], 'slot_uri': name})
            nullable = not row['notnull'] and not (row['type'] == 'INTEGER' and row['pk'])
            fields.append({'name': row['name'], 'description': DESCRIPTIONS.get(row['name'], slot.get('description', row['name'])),
                           'type': row['type'], 'nullable': nullable, 'semantic': slot['slot_uri']})
        constraints = [f"{r['from']} → {r['table']}.{r['to']}" for r in item['foreign_keys']]
        triggers = {r['name'] for r in item['triggers']}
        entities.append({'table': table, 'label': LABELS.get(table, table), 'class': item['concept'],
                         'description': profile['classes'][item['concept']].get('description', item['concept']),
                         'group': 'bibliography' if table in BIBLIOGRAPHY else 'review', 'fields': fields,
                         'implementationStatus': item['implementation_status'],
                         'appendOnly': all(f'{table}_no_{a}' in triggers for a in ['update', 'delete']),
                         'constraints': constraints or ['Vincoli di dominio e integrità definiti dallo schema SQL versionato.']})
    return {"version": profile["version"], "entities": entities}


if __name__ == "__main__":
    output = ROOT / "site/vocab/review-v2-model.json"
    output.write_text(json.dumps(build(), ensure_ascii=False, indent=2) + "\n")
    print(f"Built {len(build()['entities'])} public ontology entity definitions; corpus data: 0.")
