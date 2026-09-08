-- Additive access evidence only: no corpus reset, review activation or approval.
CREATE TABLE access_assessments_v2 (
  assessment_id TEXT NOT NULL PRIMARY KEY,
  review_id TEXT NOT NULL, candidate_id TEXT NOT NULL,
  evidence_id TEXT, full_text_url TEXT, version_type TEXT, host_type TEXT,
  license_uri TEXT, rights_basis TEXT NOT NULL, rights_evidence_url TEXT,
  access_status TEXT NOT NULL CHECK (access_status IN ('verified_open','restricted','unknown','revoked')),
  verification_method TEXT NOT NULL CHECK (verification_method IN ('anonymous_full_text_verified','access_observation')),
  verified_at TEXT NOT NULL, attributed_to TEXT NOT NULL,
  supersedes_id TEXT UNIQUE REFERENCES access_assessments_v2(assessment_id),
  FOREIGN KEY (review_id,candidate_id) REFERENCES review_candidates(review_id,candidate_id),
  FOREIGN KEY (review_id,evidence_id) REFERENCES evidence_sources(review_id,evidence_id),
  CHECK (access_status <> 'verified_open' OR (
    evidence_id IS NOT NULL AND full_text_url IS NOT NULL AND full_text_url LIKE 'https://%' AND length(full_text_url)>8
    AND rights_evidence_url IS NOT NULL AND rights_evidence_url LIKE 'https://%' AND length(rights_evidence_url)>8
    AND version_type IS NOT NULL AND version_type IN ('accepted','version_of_record')
    AND host_type IS NOT NULL AND host_type IN ('publisher','repository')
    AND length(trim(rights_basis))>0 AND verification_method='anonymous_full_text_verified'))
);
CREATE UNIQUE INDEX one_access_root ON access_assessments_v2(review_id,candidate_id) WHERE supersedes_id IS NULL;
CREATE TRIGGER access_assessments_v2_no_update BEFORE UPDATE ON access_assessments_v2 BEGIN SELECT RAISE(ABORT,'append_only:access_assessments_v2'); END;
CREATE TRIGGER access_assessments_v2_no_delete BEFORE DELETE ON access_assessments_v2 BEGIN SELECT RAISE(ABORT,'append_only:access_assessments_v2'); END;
CREATE TRIGGER access_same_candidate BEFORE INSERT ON access_assessments_v2
WHEN NEW.supersedes_id IS NOT NULL AND NOT EXISTS (
  SELECT 1 FROM access_assessments_v2 p WHERE p.assessment_id=NEW.supersedes_id AND p.review_id=NEW.review_id AND p.candidate_id=NEW.candidate_id)
BEGIN SELECT RAISE(ABORT,'access_supersession_scope_mismatch'); END;
CREATE TRIGGER access_requires_full_text BEFORE INSERT ON access_assessments_v2
WHEN NEW.access_status='verified_open' AND NOT EXISTS (
  SELECT 1 FROM evidence_sources e WHERE e.review_id=NEW.review_id AND e.candidate_id=NEW.candidate_id
  AND e.evidence_id=NEW.evidence_id AND e.evidence_kind='full_text' AND e.identity_state='verified'
  AND e.source_url=NEW.full_text_url AND length(trim(e.rights_basis))>0)
BEGIN SELECT RAISE(ABORT,'verified_full_text_source_required'); END;

CREATE VIEW v2_open_access_candidates AS
SELECT a.* FROM access_assessments_v2 a JOIN evidence_sources e USING(review_id,evidence_id)
WHERE a.access_status='verified_open' AND e.candidate_id=a.candidate_id
AND e.evidence_kind='full_text' AND e.identity_state='verified'
AND NOT EXISTS (SELECT 1 FROM access_assessments_v2 n WHERE n.supersedes_id=a.assessment_id);

CREATE TRIGGER oa_screening_gate BEFORE INSERT ON screening_decisions_v2
WHEN NEW.decision IN ('eligible_core','eligible_contextual') AND NOT EXISTS (
  SELECT 1 FROM v2_open_access_candidates a JOIN approval_receipts r ON r.receipt_id=NEW.receipt_id
  JOIN decision_proposals p ON p.proposal_id=r.proposal_id
  WHERE a.review_id=NEW.review_id AND a.candidate_id=NEW.candidate_id
  AND a.assessment_id=json_extract(p.payload_json,'$.access_assessment_id'))
BEGIN SELECT RAISE(ABORT,'current_open_access_assessment_required'); END;

CREATE TRIGGER oa_publication_gate BEFORE INSERT ON publication_approvals_v2
WHEN NEW.publication_status='published' AND NOT EXISTS (
  SELECT 1 FROM screening_decisions_v2 d JOIN v2_open_access_candidates a USING(review_id,candidate_id)
  WHERE d.decision_id=NEW.decision_id)
BEGIN SELECT RAISE(ABORT,'current_open_access_assessment_required'); END;
