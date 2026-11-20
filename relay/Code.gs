/**
 * Sus Rhythms — live relay (Google Apps Script web app)
 *
 * Passes game phases from the ViewBoard to students' iPads, and nominations / votes /
 * Emergency Meeting requests from the iPads back to the board.
 *
 * Storage: CacheService only (in memory, gone within 6 hours). No spreadsheet, no Drive,
 * no email. Nothing about roles is ever sent here: each iPad works out its own role from
 * the game code, so the relay never knows who the imposters are.
 *
 * Deploy: Deploy > New deployment > Web app > Execute as: Me > Who has access: Anyone.
 * Later updates: Deploy > Manage deployments > pencil > Version: New version > Deploy
 * (keeps the same /exec URL).
 */

var TTL = 21600;          // 6 hours, the CacheService maximum
var SEEN_MS = 20000;      // an iPad counts as connected if it checked in within 20 s
var MAX_PLAYERS = 63;

function doGet(e) { return out_(handle_((e && e.parameter) || {})); }

function doPost(e) {
  var p = {};
  var q = (e && e.parameter) || {};
  for (var k in q) p[k] = q[k];
  if (e && e.postData && e.postData.contents) {
    try {
      var b = JSON.parse(e.postData.contents);
      for (var k2 in b) p[k2] = b[k2];
    } catch (err) {}
  }
  return out_(handle_(p));
}

function out_(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj)).setMimeType(ContentService.MimeType.JSON);
}

function handle_(p) {
  try {
    var a = String(p.a || 'ping');
    if (a === 'ping') return { ok: true, t: Date.now() };
    var r = String(p.r || '').toUpperCase().replace(/[^0-9A-Z]/g, '');
    if (r.length !== 6) return { err: 'code' };
    var C = CacheService.getScriptCache();
    switch (a) {
      case 'host':  return host_(C, r, p);
      case 'poll':  return poll_(C, r, p);
      case 'reset': return reset_(C, r, p);
      case 'join':  return join_(C, r, p);
      case 'state': return state_(C, r, p);
      case 'vote':  return vote_(C, r, p);
      case 'nom':   return nom_(C, r, p);
      case 'sos':   return sos_(C, r, p);
    }
    return { err: 'action' };
  } catch (err) {
    return { err: 'server', msg: String(err && err.message || err) };
  }
}

/* ---------- helpers ---------- */
function num_(x) { var n = parseInt(x, 10); return (n >= 1 && n <= MAX_PLAYERS) ? n : 0; }
function hostOk_(C, r, s) {
  s = String(s || '');
  if (s.length < 8) return false;
  var h = C.get('h:' + r);
  if (!h) { C.put('h:' + r, s, TTL); return true; }   // first board to talk owns this game code
  return h === s;
}
function room_(C, r) {
  var s = C.get('s:' + r);
  if (!s) return null;
  try { return JSON.parse(s); } catch (e) { return null; }
}
function claimOk_(C, r, no, dv) {
  return !!dv && C.get('c:' + r + ':' + no) === String(dv);
}
function alive_(st, no) { return !!st && st.alive && st.alive.indexOf(no) >= 0; }

/* ---------- board ---------- */
// Board publishes the whole (small) public game state.
function host_(C, r, p) {
  if (!hostOk_(C, r, p.s)) return { err: 'host' };
  var obj;
  try { obj = typeof p.d === 'string' ? JSON.parse(p.d) : (p.d || {}); } catch (e) { return { err: 'json' }; }
  obj._t = Date.now();   // relay clock, so iPads can run countdowns without trusting the board's clock
  var d = JSON.stringify(obj);
  if (d.length > 90000) return { err: 'big' };
  C.put('s:' + r, d, TTL);
  return { ok: true };
}

// Board reads who's connected, nominations, votes and Emergency requests.
function poll_(C, r, p) {
  if (!hostOk_(C, r, p.s)) return { err: 'host' };
  var n = Math.min(MAX_PLAYERS, parseInt(p.n, 10) || 0), m = String(p.m || '');
  var keys = [], i;
  for (i = 1; i <= n; i++) {
    keys.push('seen:' + r + ':' + i, 'sos:' + r + ':' + i, 'c:' + r + ':' + i);
    if (m) keys.push('v:' + r + ':' + m + ':' + i, 'nm:' + r + ':' + m + ':' + i);
  }
  var got = keys.length ? C.getAll(keys) : {}, now = Date.now();
  var res = { ok: true, t: now, seen: [], joined: [], sos: {}, votes: {}, noms: {} };
  for (i = 1; i <= n; i++) {
    var sn = got['seen:' + r + ':' + i];
    if (sn && now - Number(sn) < SEEN_MS) res.seen.push(i);
    if (got['c:' + r + ':' + i]) res.joined.push(i);
    var so = got['sos:' + r + ':' + i];
    if (so) res.sos[i] = Number(so);
    if (m) {
      var v = got['v:' + r + ':' + m + ':' + i];
      if (v) res.votes[i] = v;
      var nm = got['nm:' + r + ':' + m + ':' + i];
      if (nm) res.noms[i] = Number(nm);
    }
  }
  return res;
}

// Let a number join again from a different iPad.
function reset_(C, r, p) {
  if (!hostOk_(C, r, p.s)) return { err: 'host' };
  var no = num_(p.p);
  if (!no) return { err: 'num' };
  C.remove('c:' + r + ':' + no);
  return { ok: true };
}

/* ---------- iPads ---------- */
function join_(C, r, p) {
  var no = num_(p.p), dv = String(p.dv || '');
  if (!no || dv.length < 8) return { err: 'num' };
  var lock = LockService.getScriptLock();
  if (!lock.tryLock(5000)) return { err: 'busy' };
  try {
    var key = 'c:' + r + ':' + no, cur = C.get(key);
    if (cur && cur !== dv) return { err: 'taken' };
    C.put(key, dv, TTL);
  } finally {
    lock.releaseLock();
  }
  return state_(C, r, p);
}

function state_(C, r, p) {
  var no = num_(p.p);
  if (!no) return { err: 'num' };
  if (!claimOk_(C, r, no, p.dv)) return { err: 'claim' };
  C.put('seen:' + r + ':' + no, String(Date.now()), TTL);
  var st = room_(C, r);
  if (!st) return { ok: true, wait: true };
  var mine = { sos: !!C.get('sos:' + r + ':' + no) };
  if (st.mid) {
    mine.vote = C.get('v:' + r + ':' + st.mid + ':' + no) || '';
    var nm = C.get('nm:' + r + ':' + st.mid + ':' + no);
    mine.nom = nm ? Number(nm) : 0;
  }
  return { ok: true, st: st, mine: mine, t: Date.now() };
}

function vote_(C, r, p) {
  var no = num_(p.p);
  if (!no || !claimOk_(C, r, no, p.dv)) return { err: 'claim' };
  var st = room_(C, r);
  if (!st || st.phase !== 'vote' || String(p.m) !== String(st.mid)) return { err: 'closed' };
  if (!alive_(st, no)) return { err: 'out' };
  var v = String(p.v || '');
  if (v !== 'skip' && (st.sus || []).indexOf(num_(v)) < 0) return { err: 'choice' };
  var key = 'v:' + r + ':' + st.mid + ':' + no, cur = C.get(key);
  if (cur) return { ok: true, locked: true, vote: cur };   // no changing your vote
  C.put(key, v, TTL);
  return { ok: true, vote: v };
}

function nom_(C, r, p) {
  var no = num_(p.p);
  if (!no || !claimOk_(C, r, no, p.dv)) return { err: 'claim' };
  var st = room_(C, r);
  if (!st || st.phase !== 'nominate' || String(p.m) !== String(st.mid)) return { err: 'closed' };
  if (!alive_(st, no)) return { err: 'out' };
  var t = num_(p.v);
  if (!t || t === no || !alive_(st, t)) return { err: 'choice' };
  C.put('nm:' + r + ':' + st.mid + ':' + no, String(t), TTL);   // can change until nominations close
  return { ok: true, nom: t };
}

function sos_(C, r, p) {
  var no = num_(p.p);
  if (!no || !claimOk_(C, r, no, p.dv)) return { err: 'claim' };
  var st = room_(C, r);
  if (!st || st.phase !== 'rhythm') return { err: 'closed' };
  if (!alive_(st, no)) return { err: 'out' };
  var key = 'sos:' + r + ':' + no;
  if (C.get(key)) return { err: 'used' };   // one per student per game
  C.put(key, String(Date.now()), TTL);
  return { ok: true };
}
