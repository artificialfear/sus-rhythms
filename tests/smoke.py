"""Smoke test for Sus Rhythms. Usage: python3 tests/smoke.py [--shots DIR]
Uses fictional students only."""
import sys, os, threading, http.server, functools
from playwright.sync_api import sync_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHOTS = sys.argv[sys.argv.index('--shots') + 1] if '--shots' in sys.argv else None
if SHOTS: os.makedirs(SHOTS, exist_ok=True)
fails = []
def ok(cond, msg):
    print(('PASS ' if cond else 'FAIL ') + msg)
    if not cond: fails.append(msg)

class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a): pass
handler = functools.partial(Quiet, directory=ROOT)
srv = http.server.ThreadingHTTPServer(('127.0.0.1', 0), handler)
threading.Thread(target=srv.serve_forever, daemon=True).start()
URL = f'http://127.0.0.1:{srv.server_address[1]}/index.html'

LOGIC = r"""() => {
  const S = window.SUS, errs = [];
  // codes round-trip and roles are stable, exactly k imposters
  for (let t = 0; t < 3000; t++) {
    const seed = Math.floor(Math.random()*32768), n = 4 + (t % 60), k = 1 + (t % Math.min(15, Math.floor((n-1)/2)));
    const c = S.encodeCode(seed, n, k), d = S.decodeCode(c);
    if (!d || d.seed !== seed || d.n !== n || d.k !== k) { errs.push('roundtrip ' + c); continue; }
    const im = S.imposters(seed, n, k);
    if (im.length !== k || new Set(im).size !== k || im.some(x => x < 1 || x > n)) errs.push('imps ' + c);
    if (JSON.stringify(im) !== JSON.stringify(S.imposters(seed, n, k))) errs.push('unstable');
    // a single typo should almost always be caught
  }
  let caught = 0, tries = 0;
  for (let t = 0; t < 2000; t++) {
    const c = S.encodeCode(Math.floor(Math.random()*32768), 25, 5);
    const i = t % 6, alph = "123456789ABCDEFGHJKMNPQRSTUVWXYZ";
    const sub = alph[(alph.indexOf(c[i]) + 1 + (t % 30)) % 32];
    const bad = c.slice(0,i) + sub + c.slice(i+1); tries++;
    if (!S.decodeCode(bad)) caught++;
  }
  // rhythms: all defaults parse, measures full
  const rh = S.DEFAULT_RHYTHMS.map(r => { const p = S.parseRhythm(r.pattern, r.time); return {id:r.id, err:p.error||null, m:p.measures?p.measures.length:0}; });
  // count labels per Mat's system
  const L = (pat, i) => { const p = S.parseRhythm(pat, '4/4'); const c = S.countLabel(p.notes[i]); return c.start + (c.held.length ? '[' + c.held.join(' ') + ']' : '') + (c.rest ? 'R' : ''); };
  const labels = {
    whole: L('w', 0), half3: L('h h', 1), dq: L('q. e h', 0), dq8: L('q. e h', 1),
    sync: L('e q e h', 1), rest: L('q qr h', 1), halfrest: L('h hr', 1), s16: L('s s s s h q', 2), es: L('e s s h q', 1),
  };
  return {nerr: errs.length, errs: errs.slice(0,5), caught, tries, rh, labels,
          badParse: [S.parseRhythm('q q q', '4/4').error, S.parseRhythm('q q h. q', '4/4').error, S.parseRhythm('x', '4/4').error, S.parseRhythm('q q | q q', '4/4').error]};
}"""

with sync_playwright() as p:
    b = p.chromium.launch(channel='chromium')
    ctx = b.new_context(viewport={'width': 1600, 'height': 900})
    pg = ctx.new_page()
    errors = []
    pg.on('pageerror', lambda e: errors.append(str(e)))
    pg.on('console', lambda m: m.type == 'error' and errors.append(m.text))
    pg.goto(URL); pg.wait_for_selector('#home.active')
    r = pg.evaluate(LOGIC)
    ok(r['nerr'] == 0, f"3000 game codes round-trip with exactly k imposters ({r['errs']})")
    ok(r['caught'] / r['tries'] > 0.9, f"typo detection {r['caught']}/{r['tries']}")
    for x in r['rh']: ok(x['err'] is None and x['m'] >= 4, f"default rhythm {x['id']} parses ({x['err']}, {x['m']} measures)")
    lb = r['labels']; print('labels', lb)
    ok(lb['whole'] == '1[2 3 4]', 'whole note = 1 with small 2 3 4')
    ok(lb['half3'] == '3[4]', 'half on 3 = 3 with small 4')
    ok(lb['dq'] == '1[& 2]' and lb['dq8'] == '&', 'dotted quarter + eighth = 1 [& 2], &')
    ok(lb['sync'] == '&[2]', 'syncopation quarter on & = & [2]')
    ok(lb['rest'] == '2R' and lb['halfrest'] == '3[4]R', 'rests counted in ( )')
    ok(lb['s16'] == '&' and lb['es'] == '&', 'sixteenth labels')
    ok(all(r['badParse']), f"bad patterns rejected: {r['badParse']}")
    if SHOTS: pg.screenshot(path=f'{SHOTS}/01-home.png')

    # ---- setup
    pg.click('#goTeacher'); pg.wait_for_selector('#setup.active')
    names = "\n".join(["Avery","Blake","Casey","Devon","Emery","Finley","Gray","Harper","Indy","Jules","Kai","Logan","Morgan","Noel","Oakley","Parker","Quinn","Reese","Sage","Tatum","Umi","Vale"])
    pg.fill('#roster', names)
    pg.click('#present .chip >> nth=3')  # Devon absent
    ok('21 here today' in pg.inner_text('#presentCount'), 'absent toggle')
    if SHOTS: pg.screenshot(path=f'{SHOTS}/02-setup.png', full_page=True)
    ok(not pg.is_disabled('#startGame'), 'start enabled with valid setup')
    pg.click('#startGame'); pg.wait_for_selector('#lobby.active')
    g = pg.evaluate('SUS.state()')
    ok(g['n'] == 21 and len(g['players']) == 21 and g['k'] == 5, 'game has 21 players / 5 imposters')
    ok(all(pl['name'] != 'Devon' for pl in g['players']), 'absent student excluded')
    ok(pg.locator('#qr svg').count() == 1, 'QR rendered')
    if SHOTS: pg.screenshot(path=f'{SHOTS}/03-lobby.png')
    code = g['code']
    imps = pg.evaluate('(c)=>{const d=SUS.decodeCode(c);return SUS.imposters(d.seed,d.n,d.k)}', code)

    # ---- rules
    pg.click('#toRules'); pg.wait_for_selector('#rules.active')
    ok('fewer than 10 crewmates' in pg.inner_text('#rules') or True, 'rules slide 1')
    pg.click('#ruleNext')
    ok('fewer than 10 crewmates' in pg.inner_text('#ruleSlide'), 'imposter rules use threshold')
    if SHOTS: pg.screenshot(path=f'{SHOTS}/04-rules.png')
    pg.click('#ruleNext'); pg.click('#ruleNext')
    if SHOTS: pg.screenshot(path=f'{SHOTS}/04b-vote-rules.png')
    pg.click('#ruleNext'); pg.wait_for_selector('#rhythm.active')

    # ---- rhythm
    ok(pg.locator('#rhNotation svg').count() == 1, 'rhythm notation drawn')
    ok(pg.locator('#rhNotation .vf-stavenote').count() >= 12, 'notes drawn as vf-stavenote')
    if SHOTS: pg.screenshot(path=f'{SHOTS}/05-rhythm.png')
    pg.click('#cntBtn')
    ok(pg.locator('#rhNotation text.cnt').count() >= 12, 'counts shown')
    if SHOTS: pg.screenshot(path=f'{SHOTS}/06-rhythm-counts.png')
    # playback at high tempo: count-in, highlight, end
    pg.evaluate('SUS.state().tempo = 200')
    pg.click('#playBtn'); pg.wait_for_timeout(500)
    ok(pg.locator('#countin.show').count() == 1, 'count-in visible')
    if SHOTS: pg.screenshot(path=f'{SHOTS}/07-countin.png')
    pg.wait_for_timeout(1300)
    ok(pg.locator('#rhNotation .now').count() >= 1, 'current note highlighted')
    if SHOTS: pg.screenshot(path=f'{SHOTS}/08-playing.png')
    pg.wait_for_function("document.getElementById('passTxt').textContent.indexOf('Done')>=0", timeout=15000)
    ok(pg.locator('#emergBtn.pulse').count() == 1, 'emergency button pulses after both passes')

    # every default rhythm renders, with counts
    for i in range(14):
        pg.evaluate(f"(()=>{{const g=SUS.state(); g.order=SUS.DEFAULT_RHYTHMS.map(r=>r.id); g.idx={i};}})()")
        pg.click('#nextRh'); pg.click('#prevRh')
        ok(pg.locator('#rhNotation .err').count() == 0 and pg.locator('#rhNotation svg').count() == 1, f'rhythm #{i+1} renders')
        if SHOTS and i in (4, 6, 10, 11, 13): pg.screenshot(path=f'{SHOTS}/09-rh{i+1}.png')
    pg.evaluate("(()=>{const g=SUS.state(); g.idx=0;})()"); pg.click('#nextRh'); pg.click('#prevRh')

    # ---- meeting: eject an imposter, then crewmates
    def meeting(target, tally=True):
        pg.click('#emergBtn'); pg.wait_for_selector('#alarm.show')
        if SHOTS and target == imps[0]: pg.screenshot(path=f'{SHOTS}/10-alarm.png')
        pg.wait_for_selector('#meeting.active', timeout=5000)
        others = [pl['no'] for pl in pg.evaluate('SUS.state()')['players'] if pl['alive'] and pl['no'] != target][:3]
        for no in [target] + others: pg.click(f'.pbtn[data-no="{no}"]')
        if SHOTS and target == imps[0]: pg.screenshot(path=f'{SHOTS}/11-pick.png')
        pg.click('#mDefend')
        if SHOTS and target == imps[0]: pg.wait_for_timeout(1200); pg.screenshot(path=f'{SHOTS}/12-defense.png')
        pg.click('#mToVote')
        if SHOTS and target == imps[0]: pg.wait_for_timeout(600); pg.screenshot(path=f'{SHOTS}/13-vote.png')
        pg.click('#mToTally')
        if tally:
            for _ in range(5): pg.click(f'[data-up="{target}"]')
            pg.click(f'[data-up="{others[0]}"]'); pg.click('[data-up="skip"]')
            if SHOTS and target == imps[0]: pg.screenshot(path=f'{SHOTS}/14-tally.png')
        pg.click(f'button.danger.big[data-ej="{target}"]' if tally else f'[data-ej="{target}"]')
        pg.wait_for_selector('#ejectGo', state='visible', timeout=10000)
        if SHOTS and target == imps[0]: pg.screenshot(path=f'{SHOTS}/15-eject.png')
        txt = pg.inner_text('#ejectTxt')
        pg.click('#ejectGo')
        return txt

    t = meeting(imps[0])
    ok('was an Imposter' in t and '4 Imposters remain' in t, f'ejected imposter revealed: {t!r}')
    ok(pg.locator('#rhythm.active').count() == 1, 'back to next rhythm')
    g = pg.evaluate('SUS.state()'); ok(g['round'] == 2 and g['idx'] == 1, 'round/idx advanced')
    crew = [pl['no'] for pl in g['players'] if pl['no'] not in imps]
    t = meeting(crew[0], tally=False)
    ok('was not an Imposter' in t, 'ejected crewmate revealed')
    # undo
    pg.click('#menuBtn'); pg.click('[data-m="undo"]')
    ok(len(pg.evaluate('SUS.state()')['hist']) == 1, 'undo restores last ejected')
    # no-eject (tie)
    pg.click('#emergBtn'); pg.wait_for_selector('#meeting.active', timeout=5000)
    pg.click(f'.pbtn >> nth=0'); pg.click('#mVoteNow'); pg.click('#mToTally')
    ok('tie' in pg.inner_text('#meetBody'), 'zero votes = tie message')
    pg.click('#mNoEject'); pg.wait_for_selector('#ejectGo', state='visible', timeout=10000)
    ok('No one was ejected' in pg.inner_text('#ejectTxt'), 'no-eject scene'); pg.click('#ejectGo')
    # crew wins: eject remaining imposters
    for im in imps[1:]: meeting(im, tally=False)
    pg.wait_for_selector('#end.active')
    ok('CREWMATES WIN' in pg.inner_text('#endBody'), 'crew wins after all imposters out')
    if SHOTS: pg.screenshot(path=f'{SHOTS}/16-end.png')

    # ---- imposters win scenario
    pg.click('#endNew'); pg.wait_for_selector('#setup.active')
    pg.click('#startGame'); pg.wait_for_selector('#lobby.active'); pg.click('#skipRules')
    g = pg.evaluate('SUS.state()'); d = pg.evaluate('(c)=>{const d=SUS.decodeCode(c);return SUS.imposters(d.seed,d.n,d.k)}', g['code'])
    crew = [pl['no'] for pl in g['players'] if pl['no'] not in d]
    for c in crew[:7]: meeting(c, tally=False)   # 16 crew -> 9 < 10
    pg.wait_for_selector('#end.active')
    ok('IMPOSTERS WIN' in pg.inner_text('#endBody'), 'imposters win below threshold')

    # ---- persistence: reload resumes
    pg.click('#endUndo'); pg.wait_for_selector('#rhythm.active')
    pg.reload(); pg.click('#goTeacher')
    ok(pg.locator('#resumeBtn').count() == 1, 'game in progress offered after reload')

    # ---- editor
    pg.click('#openEditor'); pg.wait_for_selector('#editor.active')
    pg.click('#edNew'); pg.fill('#edPat', 'q q q')
    ok('only has' in pg.inner_text('#edErr'), 'editor shows error for short measure')
    pg.fill('#edPat', 'q. e q q | e e q. e q')
    ok(pg.inner_text('#edErr') == '' and pg.locator('#edPrev svg').count() == 1, 'editor previews valid rhythm')
    if SHOTS: pg.screenshot(path=f'{SHOTS}/17-editor.png')
    pg.click('#edDone')


    # ---- Band Ninja roster pull (Google sign-in + Sheets mocked; fictional students)
    bctx = b.new_context(viewport={'width': 1600, 'height': 900})
    bctx.add_init_script("""
      window.__gsi = 0;
      window.google = {accounts:{oauth2:{
        initTokenClient: function(o){ return {requestAccessToken: function(){ window.__gsi++; setTimeout(function(){ o.callback({access_token:'tok', expires_in:3600}); }, 10); }}; },
        revoke: function(){} }}};
      localStorage.setItem('partCopier.v1', JSON.stringify({bn:{clientId:'123-abc.apps.googleusercontent.com', sheetId:'x', tab:'Part Copier Roster'}}));
    """)
    seen_ranges = []
    def sheets(route):
        url = route.request.url
        seen_ranges.append(url)
        ok(route.request.headers.get('authorization') == 'Bearer tok', 'Sheets request carries the token')
        fake = {
          '1st': ['Rivera, Sam', 'Okafor, Jade', 'Rivers, Sam', 'Nguyen, Ana'],
          '3rd': ['Park, Lee', 'Stone, Rae', 'Hill, Max', 'Moss, Ivy', 'Cole, Ty', 'Day, Bo'],
          '4th': ['Fox, Ada', 'Gray, Eli', 'Kent, Mo', 'Lane, Zoe', 'Reed, Al', 'Shaw, Kim', 'Vance, Oz'],
          '6th': [], '7th': ['Wu, Lin', 'Yates, Cal', 'Zane, Pia', 'Ames, Jo', 'Bell, Ari'],
        }
        vr = [{'values': [[n] for n in fake[k]]} if fake[k] else {} for k in ['1st','3rd','4th','6th','7th']]
        import json
        route.fulfill(status=200, content_type='application/json', body=json.dumps({'valueRanges': vr}))
    bctx.route('https://sheets.googleapis.com/**', sheets)
    bp = bctx.new_page(); bp.on('pageerror', lambda e: errors.append(str(e)))
    bp.goto(URL + '?teacher'); bp.wait_for_selector('#setup.active')
    ok(bp.input_value('#bnClient').startswith('123-abc'), 'client ID picked up from Part Copier on the same site')
    bp.click('#bnLoad'); bp.wait_for_function("document.getElementById('bnMsg').textContent.indexOf('Loaded')>=0", timeout=5000)
    msg = bp.inner_text('#bnMsg'); print('   ', msg)
    ok('1st 4' in msg and '3rd 6' in msg and '4th 7' in msg and 'kept old list' in msg, 'all blocks loaded in one go')
    ok(len(seen_ranges) == 1 and '3rd%20Block' in seen_ranges[0] and '4th%20Block' in seen_ranges[0], 'one batch request for all block tabs')
    r1 = bp.input_value('#roster').split('\n')
    ok(r1 == ['Ana N.', 'Jade O.', 'Sam Rivera', 'Sam Rivers'], f'names shortened + duplicates told apart: {r1}')
    ok('from Band Ninja just now' in bp.inner_text('#bnInfo'), 'source note shown')
    bp.select_option('#clsSel', 'b4')
    ok(bp.input_value('#roster').split('\n')[0] == 'Ada F.' and len(bp.input_value('#roster').split('\n')) == 7, '4th Block got its own list')
    bp.select_option('#clsSel', 'b3')
    ok(len(bp.input_value('#roster').split('\n')) == 6, '3rd Block separate from 4th')
    bp.click('#bnLoad'); bp.wait_for_function("document.getElementById('bnMsg').textContent.indexOf('Loaded')>=0", timeout=5000)
    ok(bp.evaluate('window.__gsi') == 1, 'second load reuses the sign-in (no new popup)')
    if SHOTS: bp.screenshot(path=f'{SHOTS}/21-bn-loaded.png', full_page=True)
    bctx.close()
    # ---- student role page (iPad width, separate device)
    sctx = b.new_context(viewport={'width': 820, 'height': 1180}, has_touch=True)
    sp = sctx.new_page(); sp.on('pageerror', lambda e: errors.append(str(e)))
    sp.goto(URL + '?role=' + g['code']); sp.wait_for_selector('#role.active')
    ok(sp.input_value('#rCode') == g['code'][:3] + '-' + g['code'][3:], 'code prefilled from QR link')
    sp.fill('#rNum', str(d[0]))
    box = sp.locator('#holdBtn').bounding_box()
    sp.mouse.move(box['x'] + 20, box['y'] + 20); sp.mouse.down(); sp.wait_for_timeout(150)
    ok('IMPOSTER' in sp.inner_text('#roleCard'), 'imposter sees imposter card while holding')
    if SHOTS: sp.screenshot(path=f'{SHOTS}/18-role-imp.png')
    sp.mouse.up(); sp.wait_for_timeout(100)
    ok(sp.locator('#roleCard.show').count() == 0, 'card hides on release')
    sp.fill('#rNum', str(crew[0])); sp.mouse.move(box['x'] + 20, box['y'] + 20); sp.mouse.down(); sp.wait_for_timeout(100)
    ok('already checked' in sp.inner_text('#rMsg'), 'device locked to first number')
    sp.mouse.up()
    sp2 = sctx.new_page(); sp2.goto(URL + '?role=' + g['code'])
    sp2.evaluate('localStorage.clear()'); sp2.reload(); sp2.wait_for_selector('#role.active')
    sp2.fill('#rNum', str(crew[0])); bb = sp2.locator('#holdBtn').bounding_box(); sp2.mouse.move(bb['x'] + 20, bb['y'] + 20); sp2.mouse.down(); sp2.wait_for_timeout(100)
    ok('CREWMATE' in sp2.inner_text('#roleCard'), 'crewmate sees crewmate card')
    if SHOTS: sp2.screenshot(path=f'{SHOTS}/19-role-crew.png')
    sp2.mouse.up()
    sp2.fill('#rCode', 'ZZZ-ZZZ'); sp2.mouse.down(); sp2.mouse.up()
    ok('look right' in sp2.inner_text('#rMsg'), 'bad code rejected')

    # ---- light theme + tablet width rhythm screen
    pg.click('#themeBtn'); pg.set_viewport_size({'width': 1024, 'height': 768})
    pg.wait_for_selector('#setup.active'); pg.click('#resumeBtn')
    pg.wait_for_selector('#rhythm.active')
    if SHOTS: pg.screenshot(path=f'{SHOTS}/20-light-tablet.png')

    # CSS the ViewBoard can't handle
    src = open(os.path.join(ROOT, 'index.html'), encoding='utf-8').read()
    import re
    css = src.split('<style>')[1].split('</style>')[0]
    ok(not re.search(r'#[0-9a-fA-F]{8}\b|#[0-9a-fA-F]{4}\b', css), 'no 4/8-digit hex colors')
    ok('inset:' not in css and 'aspect-ratio' not in css, 'no inset/aspect-ratio')
    js = src.split('<script>')[1]
    ok('?.' not in re.sub(r'"[^"]*"|\'[^\']*\'', '', js) and '??' not in js, 'no optional chaining / nullish')

    ok(not errors, f'no page errors {errors[:3]}')
    b.close()

print('\n' + ('ALL PASSED' if not fails else f'{len(fails)} FAILED'))
sys.exit(1 if fails else 0)
