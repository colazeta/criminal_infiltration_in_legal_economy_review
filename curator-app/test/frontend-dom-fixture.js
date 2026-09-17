/* Minimal DOM test double. Software-only; never research or completion evidence.
   Moving a node must move it, not duplicate it. Select controls by identity,
   rather than a former visual position in the paper-sheet layout. */
export class Element {
  constructor(tag) {
    this.tag = this.tagName = tag;
    this.children = [];
    this.parentNode = null;
    this.attributes = {};
    this.listeners = {};
    this.value = '';
    this._text = '';
  }
  set textContent(value) {
    this._text = String(value ?? '');
    for (const node of this.children) node.parentNode = null;
    this.children = [];
  }
  get textContent() { return this._text + this.children.map(node => node.textContent).join(' '); }
  set innerHTML(_) { throw Error('HTML injection forbidden'); }
  remove() {
    if (!this.parentNode) return;
    const siblings = this.parentNode.children;
    siblings.splice(siblings.indexOf(this), 1);
    this.parentNode = null;
  }
  append(...nodes) {
    for (const node of nodes) {
      node.remove();
      node.parentNode = this;
      this.children.push(node);
      if (this.tag === 'select' && this.children.length === 1) this.value = node.value;
    }
  }
  insertBefore(node, reference) {
    if (node === reference) return node;
    if (reference !== null && reference.parentNode !== this) throw Error('Unknown reference node');
    node.remove();
    const index = reference === null ? this.children.length : this.children.indexOf(reference);
    node.parentNode = this;
    this.children.splice(index, 0, node);
    return node;
  }
  replaceChildren(...nodes) { this.textContent = ''; this.append(...nodes); }
  setAttribute(key, value) { this.attributes[key] = String(value); }
  getAttribute(key) { return this.attributes[key] ?? null; }
  addEventListener(event, listener) { (this.listeners[event] ||= []).push(listener); }
  fire(event) {
    const payload = {target: this, preventDefault() {}};
    for (const listener of this.listeners[event] || []) listener(payload);
    this['on' + event]?.(payload);
  }
  after(node) { this.following = node; }
  matches(selector) {
    if (selector.startsWith('#')) return this.id === selector.slice(1);
    if (selector.startsWith('.')) return String(this.className || '').split(/\s+/).includes(selector.slice(1));
    return this.tag === selector;
  }
  querySelectorAll(selector) {
    return this.children.flatMap(node => [...(node.matches(selector) ? [node] : []), ...node.querySelectorAll(selector)]);
  }
  querySelector(selector) { return this.querySelectorAll(selector)[0] || null; }
}
export function createDocument() {
  const roots = [];
  return {
    createElement(tag) { const node = new Element(tag); roots.push(node); return node; },
    querySelector(selector) { return roots.find(node => node.matches(selector)) || null; },
    getElementById(id) { return roots.find(node => node.id === id) || null; },
  };
}
