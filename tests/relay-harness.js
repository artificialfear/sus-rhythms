// Loads relay/Code.gs in a Node vm with mocks that behave like the real Apps Script services.
// Used by relay.test.js (unit) and relay-server.js (local HTTP stand-in for the /exec URL).
const fs = require('fs'), path = require('path'), vm = require('vm');

function makeContext() {
  const store = new Map();   // key -> {v, exp}
  const now = () => Date.now();
  const live = k => { const e = store.get(k); if (!e) return null; if (e.exp < now()) { store.delete(k); return null; } return e.v; };
  const Cache = {
    get: k => live(String(k)),
    getAll: keys => { const o = {}; keys.forEach(k => { const v = live(String(k)); if (v !== null) o[k] = v; }); return o; },
    put: (k, v, ttl) => {
      if (typeof v !== 'string') throw new Error('Cache values must be strings');
      if (v.length > 100 * 1024) throw new Error('Argument too large');
      store.set(String(k), { v, exp: now() + Math.min(ttl || 600, 21600) * 1000 });
    },   // real put() returns void
    remove: k => { store.delete(String(k)); },
  };
  let locked = false;
  const ctx = {
    console,
    CacheService: { getScriptCache: () => Cache },
    LockService: { getScriptLock: () => ({ tryLock: () => { if (locked) return false; locked = true; return true; }, releaseLock: () => { locked = false; } }) },
    ContentService: {
      MimeType: { JSON: 'application/json' },
      createTextOutput: s => { const o = { _c: String(s), _m: 'text/plain', getContent() { return this._c; }, setMimeType(m) { this._m = m; return this; } }; return o; },
    },
  };
  vm.createContext(ctx);
  vm.runInContext(fs.readFileSync(path.join(__dirname, '..', 'relay', 'Code.gs'), 'utf8'), ctx, { filename: 'Code.gs' });
  ctx._store = store;
  return ctx;
}
const call = (ctx, params, body) => {
  const out = body ? ctx.doPost({ parameter: params, postData: { contents: JSON.stringify(body) } }) : ctx.doGet({ parameter: params });
  return JSON.parse(out.getContent());
};
module.exports = { makeContext, call };
