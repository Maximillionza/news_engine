// webapp/static/js/dashboard/test-dom-setup.js
//
// Side-effecting module: installs a minimal jsdom `document`/`window` as
// Node globals before any vendored lit-html module is imported.
//
// Why this exists: the design doc's testing strategy describes card.js's
// template smoke tests as needing "no DOM" because `html` tagged templates
// build a plain TemplateResult object without touching the DOM (only
// `render()` does). That's true of the tag function itself, but
// webapp/static/vendor/lit-html.js unconditionally reads the global
// `document` at MODULE-LOAD time (`r=document` before its TreeWalker
// setup), so merely importing card.js (which imports lit-html.js) throws
// `ReferenceError: document is not defined` under plain `node --test`
// with no DOM present at all. This file must be the first import in any
// test file that imports card.js/card-view-model.js's lit-html-dependent
// modules, so its synchronous top-level jsdom setup runs before
// lit-html.js's own top-level code does (ES module evaluation runs each
// import's module body, in import order, before the importing file's own
// subsequent statements — so this only works as the *first* import line).
import { JSDOM } from "jsdom";

if (typeof globalThis.document === "undefined") {
  const dom = new JSDOM("<!doctype html><html><body></body></html>");
  globalThis.window = dom.window;
  globalThis.document = dom.window.document;
}
