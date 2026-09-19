import {sqliteAdapter} from '../src/enrichment-store.js';
export function nativeAdapter(sqlite){
 return Object.assign(sqliteAdapter({
  sql:{exec(sql,...values){return {toArray:()=>sqlite.prepare(sql).all(...values)}}},
  transactionSync(fn){sqlite.exec('BEGIN');try{const result=fn();sqlite.exec('COMMIT');return result}catch(error){sqlite.exec('ROLLBACK');throw error}}
 }),{sqlite});
}
