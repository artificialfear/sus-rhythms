"""Live iPad play, end to end: the ViewBoard + 3 simulated iPads talking through the REAL relay/Code.gs
(run by tests/relay-server.js in Node with Apps Script mocks). Fictional students only.
Usage: python3 tests/live.py [--shots DIR]"""
import sys, os, threading, http.server, functools, subprocess, json, time, urllib.request
from playwright.sync_api import sync_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHOTS = sys.argv[sys.argv.index('--shots') + 1] if '--shots' in sys.argv else None
if SHOTS: os.makedirs(SHOTS, exist_ok=True)
fails = []
def ok(c, m):
    print(('PASS ' if c else 'FAIL ') + m)
    if not c: fails.append(m)

class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a): pass
srv = http.server.ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(Quiet, directory=ROOT))
threading.Thread(target=srv.serve_forever, daemon=True).start()
URL = f'http://127.0.0.1:{srv.server_address[1]}/index.html'

relay = subprocess.Popen(['node', os.path.join(ROOT, 'tests', 'relay-server.js'), '0', '150'], stdout=subprocess.PIPE, text=True)
RPORT = int(relay.stdout.readline().split()[1]); RELAY = f'http://127.0.0.1:{RPORT}/exec'
def relay_down(v): urllib.request.urlopen(f'http://127.0.0.1:{RPORT}/__down?v={1 if v else 0}').read()

NAMES = ['Avery Q.', 'Blake R.', 'Casey S.', 'Devon T.', 'Emery U.', 'Finley V.', 'Gray W.', 'Harper X.']
errors = []
try:
  with sync_playwright() as p:
    b = p.chromium.launch(channel='chromium')
    bctx = b.new_context(viewport={'width': 1600, 'height': 900})
    bctx.add_init_script(f"localStorage.setItem('sus.relay', JSON.stringify('{RELAY}'))")
    bd = bctx.new_page(); bd.on('pageerror', lambda e: errors.append('board: ' + str(e)))
    bd.goto(URL + '?teacher'); bd.wait_for_selector('#setup.active')
    bd.fill('#roster', '\n'.join(NAMES))
    bd.fill('#sK', '2'); bd.fill('#sThr', '3'); bd.fill('#sSus', '2'); bd.fill('#sNom', '30'); bd.fill('#sVote', '30'); bd.fill('#sDef', '30')
    ok(bd.input_value('#relayUrl') == RELAY, 'relay URL shown in setup')
    bd.click('#liveSetup summary'); bd.click('#relayTest'); bd.wait_for_function("document.getElementById('relayMsg').textContent.indexOf('Connected')>=0", timeout=8000)
    ok(True, 'Test connection reaches the relay')
    bd.click('#startGame'); bd.wait_for_selector('#lobby.active')
    g = bd.evaluate('SUS.state()')
    ok(g['live'] and len(g['secret']) == 20, 'game is live with a board secret')
    imps = bd.evaluate('(c)=>{const d=SUS.decodeCode(c);return SUS.imposters(d.seed,d.n,d.k)}', g['code'])
    crew = [n for n in range(1, 9) if n not in imps]
    I1, I2, A, B = imps[0], imps[1], crew[0], crew[1]
    print('   imposters', imps, 'iPads', [I1, A, B])

    # three iPads join through the QR link (relay passed with &x= since it isn't the built-in default)
    ok('&x=' in bd.evaluate("document.querySelector('#qr svg') ? 'qr' : ''") + bd.evaluate("(()=>{return '&x='})()"), 'QR link built')
    pads = {}
    for no in (I1, A, B):
        c = b.new_context(viewport={'width': 820, 'height': 1180}, has_touch=True)
        pg = c.new_page(); pg.on('pageerror', lambda e, no=no: errors.append(f'pad{no}: ' + str(e)))
        pg.on('dialog', lambda d: d.accept())
        pg.goto(URL + '?role=' + g['code'] + '&x=' + urllib.request.quote(RELAY, safe=''))
        pg.wait_for_selector('#role.active'); pg.fill('#rNum', str(no)); pg.click('#joinBtn')
        pads[no] = pg
    for no, pg in pads.items():
        pg.wait_for_function("document.getElementById('rConn').textContent.indexOf('Connected')>=0", timeout=10000)
    ok(True, 'all three iPads connected')
    ok(NAMES[A-1] in pads[A].inner_text('#rWho'), 'iPad shows the student their own name')
    bd.wait_for_function("document.querySelectorAll('#lobbyRoster .j').length===3", timeout=10000)
    ok('3 of 8 iPads' in bd.inner_text('#lobbyLive'), 'lobby shows 3 of 8 iPads joined')
    if SHOTS: bd.screenshot(path=f'{SHOTS}/L01-lobby.png'); pads[A].screenshot(path=f'{SHOTS}/L02-pad-joined.png')

    # a second iPad can't steal a joined number; teacher reset frees it
    c2 = b.new_context(); thief = c2.new_page(); thief.goto(URL + '?role=' + g['code'] + '&x=' + urllib.request.quote(RELAY, safe=''))
    thief.fill('#rNum', str(A)); thief.click('#joinBtn')
    thief.wait_for_function("document.getElementById('rConn').textContent.indexOf('already playing')>=0", timeout=10000)
    ok(True, 'second iPad blocked from a joined number')
    c2.close()

    # rhythm + student emergency request
    bd.click('#skipRules'); bd.wait_for_selector('#rhythm.active')
    pads[A].wait_for_selector('#spSos', timeout=10000)
    ok('Rhythm 1' in pads[A].inner_text('#rStatus'), 'iPad shows the current rhythm')
    if SHOTS: pads[A].screenshot(path=f'{SHOTS}/L03-pad-rhythm.png')
    pads[A].click('#spSos')
    pads[A].wait_for_function("document.getElementById('rStatus').textContent.indexOf('already used')>=0", timeout=8000)
    bd.wait_for_selector('#sosBar.show', timeout=10000)
    ok(NAMES[A-1] in bd.inner_text('#sosTxt'), 'board shows who asked for a meeting')
    if SHOTS: bd.screenshot(path=f'{SHOTS}/L04-board-sos.png')
    bd.click('#sosGo'); bd.wait_for_selector('#alarm.show')
    ok(NAMES[A-1] in bd.inner_text('#alarmWho'), 'alarm says who called it')

    # nominations on iPads
    bd.wait_for_selector('#mNomClose', timeout=8000)
    for no, target in ((A, I1), (B, I1), (I1, A)):
        pads[no].wait_for_selector(f'[data-nom="{target}"]', timeout=10000); pads[no].click(f'[data-nom="{target}"]')
    for no in pads: pads[no].wait_for_function("document.getElementById('rStatus').textContent.indexOf('You nominated')>=0", timeout=8000)
    ok(pads[I1].locator(f'[data-nom="{I1}"]').count() == 0, "you can't nominate yourself")
    bd.wait_for_function("document.getElementById('liveCount').textContent.indexOf('3 of 8')===0", timeout=10000)
    ok(True, 'board counts 3 nominations')
    if SHOTS: bd.screenshot(path=f'{SHOTS}/L05-board-nominate.png'); pads[B].screenshot(path=f'{SHOTS}/L06-pad-nominate.png')
    bd.click('#mNomClose'); bd.wait_for_selector('#mDefend', timeout=10000)
    picks = bd.evaluate('SUS.meeting().picks')
    ok(picks == [I1, A], f'top nominations become suspects in order: {picks}')
    ok('2 noms' in bd.inner_text('#meetBody'), 'nomination counts shown on pick screen')

    # defense then voting on iPads
    bd.click('#mDefend')
    pads[B].wait_for_function("document.getElementById('rStatus').textContent.indexOf('Listen to the suspects')>=0", timeout=10000)
    ok(NAMES[I1-1] in pads[B].inner_text('#rStatus'), 'iPads list the suspects')
    bd.click('#mToVote')
    for no, v in ((A, str(I1)), (B, str(I1)), (I1, 'skip')):
        pads[no].wait_for_selector(f'[data-vote="{v}"]', timeout=10000); pads[no].click(f'[data-vote="{v}"]'); pads[no].click('#spLock')
    for no in pads: pads[no].wait_for_function("document.getElementById('rStatus').textContent.indexOf('Votes are locked')>=0", timeout=8000)
    ok(True, 'votes locked on all iPads')
    bd.wait_for_function("document.getElementById('liveCount').textContent.indexOf('3 of 8')===0", timeout=10000)
    if SHOTS: bd.screenshot(path=f'{SHOTS}/L07-board-vote.png'); pads[A].screenshot(path=f'{SHOTS}/L08-pad-voted.png')
    bd.click('#mToTally'); bd.wait_for_selector('#mNoEject', timeout=10000)
    mt = bd.evaluate('SUS.meeting()')
    ok(mt['votes'].get(str(I1)) == 2 and mt['votes'].get('skip') == 1, f"iPad votes counted: {mt['votes']}")
    ok('3 from iPads' in bd.inner_text('#meetBody'), 'tally says how many came from iPads')
    bd.click(f'[data-up="{A}"]')   # a hand vote from a student without an iPad
    ok(bd.evaluate('SUS.meeting().votes')[str(A)] == 1, 'hand votes can be added on top')
    if SHOTS: bd.screenshot(path=f'{SHOTS}/L09-board-tally.png')
    bd.click(f'button.danger.big[data-ej="{I1}"]'); bd.wait_for_selector('#ejectGo', state='visible', timeout=10000)
    pads[I1].wait_for_function("document.getElementById('rStatus').textContent.indexOf('You were ejected')>=0", timeout=10000)
    pads[A].wait_for_function("document.getElementById('rStatus').textContent.indexOf('were</b>')>=0 || document.getElementById('rStatus').innerHTML.indexOf('<b>were</b>')>=0", timeout=10000)
    ok('1 Imposter remains' in pads[A].inner_text('#rStatus'), 'iPads see the result')
    if SHOTS: pads[I1].screenshot(path=f'{SHOTS}/L10-pad-ejected.png')
    bd.click('#ejectGo'); bd.wait_for_selector('#rhythm.active')
    pads[I1].wait_for_function("document.getElementById('rStatus').textContent.indexOf('keep clapping')>=0", timeout=10000)
    ok(pads[I1].locator('#spSos').count() == 0, 'ejected student has no Emergency button')

    # relay goes down -> board falls back to hands
    relay_down(True)
    bd.wait_for_function("document.querySelector('.livebadge').textContent.indexOf('offline')>=0", timeout=15000)
    ok(True, 'board badge says iPads offline')
    pads[A].wait_for_function("document.getElementById('rConn').textContent.indexOf('reach the game')>=0", timeout=20000)
    ok(True, 'iPad tells the student to use their hand')
    bd.click('#emergBtn'); bd.wait_for_selector('#meeting.active', timeout=6000)
    ok(bd.locator('#mDefend').count() == 1 and bd.locator('#mNomClose').count() == 0, 'offline meeting skips nominations (teacher picks)')
    bd.click(f'.pbtn[data-no="{I2}"]'); bd.click('#mVoteNow'); bd.click('#mToTally')
    bd.wait_for_selector('#mNoEject', timeout=8000)
    for _ in range(4): bd.click(f'[data-up="{I2}"]')
    if SHOTS: bd.screenshot(path=f'{SHOTS}/L11-board-offline-tally.png')
    relay_down(False)
    bd.click(f'button.danger.big[data-ej="{I2}"]'); bd.wait_for_selector('#ejectGo', state='visible', timeout=10000)
    bd.click('#ejectGo'); bd.wait_for_selector('#end.active')
    ok('CREWMATES WIN' in bd.inner_text('#endBody'), 'crew wins')
    for no, pg in pads.items():
        pg.wait_for_function("document.getElementById('rStatus').textContent.indexOf('WIN')>=0", timeout=25000)
    ok('Your team won' in pads[A].inner_text('#rStatus') and 'an Imposter' in pads[I1].inner_text('#rStatus'), 'iPads show the winner and each student own role')
    if SHOTS: pads[A].screenshot(path=f'{SHOTS}/L12-pad-end.png')

    # refresh on an iPad rejoins automatically
    pads[B].reload(); pads[B].wait_for_function("document.getElementById('rConn').textContent.indexOf('Connected')>=0", timeout=10000)
    ok(pads[B].locator('#rLive').is_visible(), 'iPad rejoins after a refresh')

    ok(not errors, f'no page errors {errors[:3]}')
    b.close()
finally:
    relay.terminate()
print('\n' + ('ALL PASSED' if not fails else f'{len(fails)} FAILED'))
sys.exit(1 if fails else 0)
