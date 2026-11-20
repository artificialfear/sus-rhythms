// Unit tests for relay/Code.gs. Run: node tests/relay.test.js
const { makeContext, call } = require('./relay-harness');
let fails = 0;
const ok = (c, m) => { console.log((c ? 'PASS ' : 'FAIL ') + m); if (!c) fails++; };

const X = makeContext();
const R = 'ABC123', S = 'secret-board-1', S2 = 'other-board-99';
const D = n => 'device-' + String(n).padStart(4, '0');

ok(call(X, { a: 'ping' }).ok, 'ping');
ok(call(X, { a: 'state', r: 'bad', p: 1, dv: D(1) }).err === 'code', 'bad code rejected');

// board claims the code; a second board (or a student guessing) can't take over
ok(call(X, { a: 'host' }, { r: R, s: S, d: { phase: 'lobby', alive: [1, 2, 3, 4, 5, 6], names: {} } }).ok, 'board publishes state');
ok(call(X, { a: 'host' }, { r: R, s: S2, d: { phase: 'end' } }).err === 'host', 'other board blocked');
ok(call(X, { a: 'poll', r: R, s: 'short', n: 6 }).err === 'host', 'short secret blocked');

// joining: one iPad per number
ok(call(X, { a: 'join', r: R, p: 1, dv: D(1) }).st.phase === 'lobby', 'join returns state');
ok(call(X, { a: 'join', r: R, p: 1, dv: D(9) }).err === 'taken', 'second iPad cannot take number 1');
ok(call(X, { a: 'state', r: R, p: 1, dv: D(9) }).err === 'claim', 'unclaimed device gets no state');
for (let i = 2; i <= 6; i++) call(X, { a: 'join', r: R, p: i, dv: D(i) });
let pl = call(X, { a: 'poll', r: R, s: S, n: 6 });
ok(pl.joined.length === 6 && pl.seen.length === 6, 'board sees 6 joined & connected');
ok(call(X, { a: 'reset', r: R, s: S, p: 1 }).ok && call(X, { a: 'join', r: R, p: 1, dv: D(9) }).ok, 'board reset lets number 1 rejoin on another iPad');
call(X, { a: 'reset', r: R, s: S, p: 1 }); call(X, { a: 'join', r: R, p: 1, dv: D(1) });

// emergency requests only during rhythm, once per game, alive only
ok(call(X, { a: 'sos', r: R, p: 2, dv: D(2) }).err === 'closed', 'no SOS in lobby');
call(X, { a: 'host' }, { r: R, s: S, d: { phase: 'rhythm', alive: [1, 2, 3, 4, 5], names: {} } });
ok(call(X, { a: 'sos', r: R, p: 2, dv: D(2) }).ok, 'SOS during rhythm');
ok(call(X, { a: 'sos', r: R, p: 2, dv: D(2) }).err === 'used', 'only one SOS per game');
ok(call(X, { a: 'sos', r: R, p: 6, dv: D(6) }).err === 'out', 'ejected player cannot SOS');
ok(call(X, { a: 'poll', r: R, s: S, n: 6 }).sos[2] > 0, 'board sees SOS from #2');

// nominations: alive, not self, changeable
call(X, { a: 'host' }, { r: R, s: S, d: { phase: 'nominate', mid: 'm1', alive: [1, 2, 3, 4, 5], names: {} } });
ok(call(X, { a: 'nom', r: R, p: 1, dv: D(1), m: 'm1', v: 1 }).err === 'choice', 'cannot nominate yourself');
ok(call(X, { a: 'nom', r: R, p: 1, dv: D(1), m: 'm1', v: 6 }).err === 'choice', 'cannot nominate an ejected player');
ok(call(X, { a: 'nom', r: R, p: 1, dv: D(1), m: 'm1', v: 3 }).ok, 'nominate');
ok(call(X, { a: 'nom', r: R, p: 1, dv: D(1), m: 'm1', v: 4 }).nom === 4, 'can change nomination');
ok(call(X, { a: 'nom', r: R, p: 2, dv: D(2), m: 'old', v: 4 }).err === 'closed', 'stale meeting id rejected');
call(X, { a: 'nom', r: R, p: 2, dv: D(2), m: 'm1', v: 4 });
ok(call(X, { a: 'nom', r: R, p: 6, dv: D(6), m: 'm1', v: 4 }).err === 'out', 'ejected cannot nominate');
pl = call(X, { a: 'poll', r: R, s: S, n: 6, m: 'm1' });
ok(pl.noms[1] === 4 && pl.noms[2] === 4, 'board sees nominations');
ok(call(X, { a: 'state', r: R, p: 1, dv: D(1) }).mine.nom === 4, 'iPad sees its own nomination');

// voting: suspects or skip, locked after first vote, only while open
ok(call(X, { a: 'vote', r: R, p: 1, dv: D(1), m: 'm1', v: 4 }).err === 'closed', 'no voting during nominations');
call(X, { a: 'host' }, { r: R, s: S, d: { phase: 'vote', mid: 'm1', sus: [3, 4], alive: [1, 2, 3, 4, 5], names: {} } });
ok(call(X, { a: 'vote', r: R, p: 1, dv: D(1), m: 'm1', v: 5 }).err === 'choice', 'non-suspect vote rejected');
ok(call(X, { a: 'vote', r: R, p: 1, dv: D(1), m: 'm1', v: 4 }).vote === '4', 'vote');
const again = call(X, { a: 'vote', r: R, p: 1, dv: D(1), m: 'm1', v: 'skip' });
ok(again.locked && again.vote === '4', 'vote is locked');
ok(call(X, { a: 'vote', r: R, p: 2, dv: D(2), m: 'm1', v: 'skip' }).ok, 'skip vote');
ok(call(X, { a: 'vote', r: R, p: 3, dv: D(3), m: 'm1', v: 4 }).ok, 'suspect can vote');
ok(call(X, { a: 'vote', r: R, p: 6, dv: D(6), m: 'm1', v: 4 }).err === 'out', 'ejected cannot vote');
ok(call(X, { a: 'vote', r: R, p: 4, dv: D(1), m: 'm1', v: 3 }).err === 'claim', "cannot vote with someone else's number");
pl = call(X, { a: 'poll', r: R, s: S, n: 6, m: 'm1' });
ok(JSON.stringify(pl.votes) === JSON.stringify({ 1: '4', 2: 'skip', 3: '4' }), 'board gets all votes');
call(X, { a: 'host' }, { r: R, s: S, d: { phase: 'tally', mid: 'm1', sus: [3, 4], alive: [1, 2, 3, 4, 5], names: {} } });
ok(call(X, { a: 'vote', r: R, p: 5, dv: D(5), m: 'm1', v: 3 }).err === 'closed', 'late vote rejected');

// size limits
ok(call(X, { a: 'host' }, { r: R, s: S, d: { pad: 'x'.repeat(95000) } }).err === 'big', 'oversized state rejected');
ok(call(X, { a: 'host' }, { r: R, s: S, d: '{bad json' }).err === 'json', 'bad JSON rejected');
call(X, { a: 'host' }, { r: R, s: S, d: { phase: 'rhythm', alive: [1] } });
ok(call(X, { a: 'state', r: R, p: 1, dv: D(1) }).st._t > 0, 'relay stamps its clock on the state');
ok(call(X, { a: 'state', r: R, p: 99, dv: D(1) }).err === 'num', 'bad number rejected');

console.log(fails ? `\n${fails} FAILED` : '\nALL PASSED');
process.exit(fails ? 1 : 0);
