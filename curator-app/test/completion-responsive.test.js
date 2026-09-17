import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import {Element, createDocument} from './frontend-dom-fixture.js';

test('stage breakdown uses the existing mobile definition-list layout, not a wide archive table',()=>{
  const context=vm.createContext({document:createDocument(),URL});
  const source=fs.readFileSync(new URL('../../site/paper-sheet-research.js',import.meta.url),'utf8');
  vm.runInContext(source,context);
  const parent=new Element('section');
  context.CILEPaperResearch.renderProgress(parent,{availability:'not_assessed',research:null});
  const descendants=node=>[node,...node.children.flatMap(descendants)];
  const nodes=descendants(parent);
  assert.equal(nodes.filter(n=>n.tag==='dl').length,1);
  assert.equal(nodes.filter(n=>n.tag==='dt').length,6);
  assert.equal(nodes.filter(n=>n.tag==='dd').length,6);
  assert.equal(nodes.filter(n=>n.tag==='table').length,0);
  const css=fs.readFileSync(new URL('../../site/styles.css',import.meta.url),'utf8');
  assert.match(css,/@media \(max-width: 480px\).*\.paper-sheet-body dl \{ grid-template-columns: 1fr;/);
});
