// Read-only inspection through the installed CLI's actual workspace packager.
// No API, auth, session access, release creation or native execution.
import fs from 'node:fs';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
import {createHash} from 'node:crypto';
const workspace=path.resolve(process.argv[2]||'../control-plane');
const cliDist=path.resolve(process.argv[3]||path.join(process.env.APPDATA||'', 'npm/node_modules/@kora-platform/cli/dist'));
const {readWorkspaceTestEntries}=await import(pathToFileURL(path.join(cliDist,'files.js')));
const entries=await readWorkspaceTestEntries(workspace);
const selected=entries.filter(e=>e.path.startsWith('tests/')&&/\.ya?ml$/i.test(e.path));
const sha=s=>createHash('sha256').update(s).digest('hex');
for(const e of selected) {
 if(!/^["']?kind["']?:\s*["']?Test["']?\s*$/m.test(e.content))throw Error('Non-Test YAML: '+e.path);
}
if(selected.length!==154)throw Error(`Expected 154 bundled tests, found ${selected.length}`);
if(entries.some(e=>e.path.startsWith('history/')))throw Error('History leaked into selected bundle');
const required=['replay-A-starvation-insufficient-evidence.yaml','replay-B-starvation-insufficient-evidence.yaml',
 'replay-A-starvation-exact-24h.yaml','replay-B-starvation-exact-24h.yaml',
 'replay-A-starvation-exact-20.yaml','replay-B-starvation-exact-20.yaml'];
for(const file of required)if(!selected.some(e=>e.path===`tests/${file}`))throw Error('Missing test: '+file);
if(selected.some(e=>e.path.endsWith('-starvation-over-complete.yaml')))throw Error('Historical original selected');
const packageInfo=JSON.parse(fs.readFileSync(path.join(cliDist,'../package.json'),'utf8'));
const report={scope:'Offline packaging inspection, not native/server execution',cliVersion:packageInfo.version,
 workspace,suiteDirectory:path.join(workspace,'tests'),nameFilter:null,releaseSelector:null,
 packagedFiles:entries.length,selectedTestCount:selected.length,
 interpretation:'All 154 Test YAML files under this source bundle tests/. Sibling replay/history is not sent. Actual native execution count remains unverified.',
 loaderSha256:sha(fs.readFileSync(path.join(cliDist,'files.js'))),
 suiteCommandSha256:sha(fs.readFileSync(path.join(cliDist,'workflow-commands.js'))),
 tests:selected.map(e=>({path:e.path,sha256:sha(e.content)}))};
if(process.argv[4])fs.writeFileSync(process.argv[4],JSON.stringify(report,null,2)+'\n');
console.log(JSON.stringify({...report,tests:undefined},null,2));
