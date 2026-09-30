// Test-only Worker: never imported by src/worker.js or deployed to production.
import {DurableObject} from 'cloudflare:workers';
import {EnrichmentStoreCore} from '../src/enrichment-store.js';
import {sha256} from '../src/review-v2.js';

export class NativeEnrichmentTest extends DurableObject {
  constructor(ctx, env) { super(ctx, env); }
  async fetch(request) {
    const path = new URL(request.url).pathname;
    if (path === '/primitive') {
      const results = {};
      for (const [name, fn] of [
        ['transaction_object', () => this.ctx.storage.transaction(async tx => {
          await tx.get('native-probe'); await tx.put('native-probe', 1);
        })],
        ['transaction_storage', () => this.ctx.storage.transaction(async () => {
          await this.ctx.storage.get('native-probe'); await this.ctx.storage.put('native-probe', 2);
        })],
        ['transaction_sync_kv', () => this.ctx.storage.transactionSync(() => {
          this.ctx.storage.kv.get('native-probe'); this.ctx.storage.kv.put('native-probe', 3);
        })],
      ]) {
        try { await fn(); results[name] = {ok: true}; }
        catch (error) { results[name] = {ok: false, message: String(error.message)}; }
      }
      await this.ctx.storage.delete('native-probe');
      return Response.json(results);
    }
    this.core ||= new EnrichmentStoreCore(this.ctx, this.env);
    if (path === '/storage-roundtrip') {
      await this.core.requireReady();
      const text = 'Native SQLite evidence \u03b1\ud83d\ude00 '.repeat(4000);
      const bytes = new TextEncoder().encode(text);
      const digest = await sha256(text);
      await this.core.evidence.put('runtime-roundtrip', text);
      await this.core.documents.put(digest, bytes);
      const textRead = await (await this.core.evidence.get('runtime-roundtrip')).text();
      const binaryRead = await this.core.documents.get(digest);
      let conflict = false;
      try { await this.core.evidence.put('runtime-roundtrip', 'different'); }
      catch (error) { conflict = error.message === 'immutable_content_conflict'; }
      return Response.json({text: textRead === text, binary: new TextDecoder().decode(binaryRead) === text, conflict});
    }
    if (path === '/migration-reload') {
      await this.core.requireReady();
      this.core = new EnrichmentStoreCore(this.ctx, this.env);
      await this.core.requireReady();
      return Response.json({verified: (await this.core.verify()).verified});
    }
    return this.core.fetch(request);
  }
  alarm() { return this.core?.alarm(); }
}

export default {
  fetch(request, env) {
    return env.NATIVE_STORE.get(env.NATIVE_STORE.idFromName('native-test')).fetch(request);
  },
};
