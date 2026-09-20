"use strict";

const FOUR_PART = {
  criminal_actor_supported: {
    type: "noul",
    instructions: "Based only on `evidence`, is there support for an analytically identifiable criminal actor or criminal interest relevant to `candidate`?",
    criteria: { true: "Supported by the supplied evidence", false: "Not supported by the supplied evidence" },
  },
  legal_economy_object_supported: {
    type: "noul",
    instructions: "Based only on `evidence`, is there support for a firm, profession, asset, procurement process, market, sector, or governance arrangement in the legal economy?",
    criteria: { true: "Supported by the supplied evidence", false: "Not supported by the supplied evidence" },
  },
  sustained_relation_supported: {
    type: "noul",
    instructions: "Based only on `evidence`, is there support for sustained access, participation, influence, control, or organisational embeddedness by the criminal actor or interest in the legal-economy object?",
    criteria: { true: "A sustained infiltration relationship is supported", false: "A sustained infiltration relationship is not supported" },
  },
  substantive_analysis_supported: {
    type: "noul",
    instructions: "Based only on `evidence`, does the work substantively analyse the criminal actor/legal-economy relationship rather than merely mention it?",
    criteria: { true: "The relationship is substantively analysed", false: "The relationship is incidental, absent, or unsupported" },
  },
};

const FRAMEWORK = Object.fromEntries([
  ["aetiology", "causes, drivers, enabling conditions, or mechanisms producing infiltration"],
  ["diagnosis", "describing, identifying, characterising, or measuring existing infiltration"],
  ["screening", "detecting, predicting, flagging, or risk-scoring infiltration"],
  ["therapy", "interventions intended to remove, disrupt, remediate, or counter infiltration"],
  ["prognosis", "outcomes, trajectories, persistence, recurrence, or consequences following infiltration or intervention"],
  ["prevention", "measures intended to prevent infiltration before it occurs"],
].map(([key, description]) => [`framework_${key}_supported`, {
  type: "noul",
  instructions: `Based only on \`evidence\`, does the work make a substantive contribution to ${description}?`,
  criteria: { true: "Substantive contribution supported", false: "Not supported or merely incidental" },
}]));

const CANDIDATE_SCREENING = {
  version: "CILE-JEV-CANDIDATE-SCREENING-1",
  stateKind: "candidate_screening",
  questions: {
    scholarly_scope_supported: {
      type: "noul",
      instructions: "Based only on `candidate` and `evidence`, is this an academic or scholarly work within the review's document scope?",
      criteria: { true: "Scholarly work is supported", false: "Scholarly status is absent or contradicted" },
    },
    ...FOUR_PART,
    evidence_sufficient_for_screening: {
      type: "noul",
      instructions: "Is the supplied `evidence` sufficient to make a defensible four-part infiltration screening assessment without relying on unstated information?",
      criteria: { true: "Evidence is sufficient", false: "Evidence is insufficient or materially ambiguous" },
    },
    full_text_needed: {
      type: "noul",
      instructions: "Given the supplied `evidence`, is full text or materially richer source evidence needed before a defensible four-part screening assessment can be made?",
      criteria: { true: "Additional full-text or richer evidence is needed", false: "Current evidence is sufficient for screening" },
    },
    adjacent_phenomenon_only: {
      type: "noul",
      instructions: "Does the supplied `evidence` support only an adjacent phenomenon such as passive investment, one-off laundering, isolated corruption/collusion, professional facilitation, generic corporate crime, shell-company use, or organised-crime violence without a sustained legal-economy infiltration relationship?",
      criteria: { true: "Only an adjacent phenomenon is supported", false: "The evidence supports more than an adjacent-only phenomenon or is insufficient" },
    },
    ...FRAMEWORK,
  },
};

const METADATA_ASSERTION = {
  version: "CILE-JEV-METADATA-ASSERTION-1",
  stateKind: "metadata_assertion",
  questions: {
    assertion_status: {
      type: "choice",
      instructions: "Using only `evidence`, classify whether the bibliographic `assertion` is supported.",
      criteria: {
        supported: "The assertion is directly supported by the supplied evidence.",
        contradicted: "The supplied evidence directly conflicts with the assertion.",
        insufficient_evidence: "The supplied evidence cannot responsibly establish or contradict the assertion.",
      },
    },
    material_metadata_conflict: {
      type: "noul",
      instructions: "Do the supplied evidence observations contain a material unresolved bibliographic conflict relevant to the assertion?",
      criteria: { true: "A material conflict is present", false: "No material conflict is present" },
    },
  },
};

const IDENTITY_RELATION = {
  version: "CILE-JEV-IDENTITY-RELATION-1",
  stateKind: "identity_relation",
  questions: {
    identity_relation: {
      type: "choice",
      instructions: "Using only `left`, `right`, and `evidence`, classify the relationship between the two bibliographic records. Do not infer identity from DOI equality alone and preserve manifestation/version distinctions.",
      criteria: {
        same_manifestation: "The records represent the same specific manifestation or version.",
        same_work_different_manifestation: "The records represent the same intellectual work but different manifestations or versions.",
        different_work: "The records represent different intellectual works.",
        insufficient_evidence: "The relationship cannot be established safely from the supplied evidence.",
      },
    },
    identity_conflict_present: {
      type: "noul",
      instructions: "Is there a material unresolved identity or manifestation conflict in the supplied evidence?",
      criteria: { true: "A material identity conflict is present", false: "No material identity conflict is present" },
    },
  },
};

const ENRICHMENT_QA = {
  version: "CILE-JEV-ENRICHMENT-QA-1",
  stateKind: "enrichment_qa",
  questions: {
    research_question_supported: { type: "noul", instructions: "Is the proposed research-question/contribution summary supported by `evidence`?" },
    infiltration_definition_supported: { type: "noul", instructions: "Is the proposed infiltration definition or operationalisation supported by `evidence`?" },
    study_summary_supported: { type: "noul", instructions: "Is the proposed study/population/geography/period summary supported by `evidence`?" },
    data_summary_supported: { type: "noul", instructions: "Is the proposed dataset/source summary supported by `evidence`?" },
    methods_summary_supported: { type: "noul", instructions: "Is the proposed design/method/identification/robustness summary supported by `evidence`?" },
    variables_summary_supported: { type: "noul", instructions: "Is the proposed variables/constructs summary supported by `evidence`?" },
    findings_summary_supported: { type: "noul", instructions: "Is the proposed findings/effect/uncertainty summary supported by `evidence`?" },
    limitations_summary_supported: { type: "noul", instructions: "Is the proposed limitations/caveats summary supported by `evidence`?" },
    framework_proposal_supported: { type: "noul", instructions: "Is the proposed six-class framework orientation supported by `evidence`?" },
    material_omission_present: {
      type: "noul",
      instructions: "Does the proposal omit material information that is present in `evidence` and necessary for an accurate structured assessment?",
    },
    claim_overstatement_present: {
      type: "noul",
      instructions: "Does any supplied proposal statement materially overstate what `evidence` supports?",
    },
    evidence_sufficient_for_assessment: {
      type: "noul",
      instructions: "Is the supplied evidence sufficient to support a structured assessment at the granularity represented in `proposal`?",
    },
  },
};

const JEV_QUESTION_SETS = Object.freeze({
  candidate_screening_v1: CANDIDATE_SCREENING,
  metadata_assertion_v1: METADATA_ASSERTION,
  identity_relation_v1: IDENTITY_RELATION,
  enrichment_qa_v1: ENRICHMENT_QA,
});

function getJevQuestionSet(id) {
  const set = JEV_QUESTION_SETS[id];
  if (!set) throw new Error(`unknown_jev_question_set:${id}`);
  return structuredClone(set);
}

export { JEV_QUESTION_SETS, getJevQuestionSet };
