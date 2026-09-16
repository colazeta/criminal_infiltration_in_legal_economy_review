/* Temporary fail-closed diagnostic wrapper for the private enrichment Durable Object.
   It exposes no private data: only a closed error code is written to Worker logs. */
import worker, {PaperEnrichmentStore as BasePaperEnrichmentStore} from './worker.js';
export {SubmissionCoordinator} from './worker.js';

const SAFE_STORE_ERRORS = new Set([
  'sqlite_storage_required',
  'migration_bundle_integrity',
  'additive_migration_required',
  'schedule_migration_integrity',
  'additive_schedule_migration_required',
  'adjudication_migration_integrity',
  'additive_adjudication_migration_required',
  'delivery_migration_integrity',
  'additive_delivery_migration_required',
  'storage_readback_failed',
]);

export function safeStoreErrorCode(error) {
  const code = typeof error?.message === 'string' ? error.message : '';
  return SAFE_STORE_ERRORS.has(code) ? code : 'store_internal_exception';
}

function recordStoreFailure(error, phase) {
  console.error(`enrichment_store_${phase}:${safeStoreErrorCode(error)}`);
}

export class PaperEnrichmentStore extends BasePaperEnrichmentStore {
  async fetch(request) {
    try {
      return await super.fetch(request);
    } catch (error) {
      recordStoreFailure(error, 'fetch_failure');
      return Response.json(
        {error_code: 'service_operation_failed'},
        {status: 500, headers: {'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff'}},
      );
    }
  }

  async alarm() {
    try {
      return await super.alarm();
    } catch (error) {
      recordStoreFailure(error, 'alarm_failure');
      throw error;
    }
  }
}

export default worker;
