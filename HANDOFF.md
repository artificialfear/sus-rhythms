# HANDOFF — Sus Rhythms (Raven Band Edition)

Repo: artificialfear/sus-rhythms. Live at https://artificialfear.github.io/sus-rhythms/ once Pages is on.

This is the web version of Mat's "Among Us Rhythm Game" slideshow, his social-deduction clapping game for Raven Band. It runs on the ViewBoard, and students check their secret role on their iPads.

## Files
- `index.html`: the whole app (HTML/CSS/JS). There is no build step.
- `lib/vexflow-bravura.js` (VexFlow 4.2.3) and `lib/qrcode.js` are copied from Grudgeball and bundled locally for the school network.
- `relay/`: the Apps Script relay for live iPad play (Code.gs + README with deploy steps).
- `tests/smoke.py`: Playwright smoke test. Run `python3 tests/smoke.py [--shots DIR]`. It covers the code/role logic fuzz, the counting labels, all default rhythms, a full game to a crew win and to an imposter win, undo, reload/resume, the editor, the student role page (lock, hold-to-reveal), and the ViewBoard CSS/JS limits.

## Decisions (Mat, 2026-11-20)
- **Roles:** secret code on iPads, which replaces the Brightspace messages. The board shows a 6-character code (`XXX-XXX`) plus a QR code linking to `?role=CODE`. A student enters the code and their number from the board list, then presses and holds to see their role.
- **Theme:** an original "raven crew in space" look. There's no Among Us art, characters or name anywhere (the repo is public). The game terms are kept: Imposter, Crewmate, Emergency Meeting, airlock, sus.
- **Rhythms:** real notation (VexFlow) with a count-in, a moving highlight for each time through, and an editor. Mat's 10 slide rhythms were transcribed as "Original 10", and 4 "Advanced" extras were added (dotted, syncopation, sixteenths, 3/4).
- **Account:** artificialfear.

## How it works
- **Game code:** 30 bits in a 32-symbol alphabet (`123456789ABCDEFGHJKMNPQRSTUVWXYZ`, with no 0/O/I/L): seed(15) | n(6) | k(4) | check(5). `imposters(seed,n,k)` is a seeded Fisher-Yates over 1..n, and the first k are the imposters. The student device needs no network or server. The 5-bit check catches about 97% of typos. Limits: up to 63 players and 15 imposters.
- **Peek protection is soft:** a device remembers the first number it checked for a code (`sus.lock.<CODE>`). Clearing site data or switching devices gets around it, and so does reading the JS. That's fine for a class game, but it isn't security.
- **Players:** the roster is a textarea for each class, plus "who's here today" chips. Only present students get numbers (in roster order), so absent kids can never be imposters. With no roster, the game uses numbers only.
- **Win check (after every meeting):** 0 imposters left = crew wins; crewmates left < `thr` = imposters win. The setup screen spells out what the threshold means for the current class size.
- **Meeting flow:** alarm → pick up to `sus` suspects (A–D) → defense timer → voting countdown (beeps for the last 5 s) → tally (+/−, or tap "Eject" directly). A tie or a Skip win means no one is ejected. The eject scene reveals the role if "Reveal role" is on.
- **Counting labels** follow Mat's system: the start count is full size; held counts are small and underlined; rests go in ( ). A note shows its held "&" only if it starts or ends on an "&", and its held "e"/"a" only if it starts or ends on one. See `countLabel()`; the smoke test checks the examples from raven-band-context.
- **Pattern syntax:** `w h q e s`, `.` = dotted, `r` = rest, `|` = optional barline (checked). Time signatures 2/4, 3/4 and 4/4 work. 6/8 isn't supported yet.
- The rhythm screen draws 2 measures per line to keep the notes large. The editor preview uses 4 per line.
- Sounds are all Web Audio synth (click, clap, siren, beeps, whoosh), so there are no audio files.
- ViewBoard-safe: no flex `gap`, `inset`, `aspect-ratio`, 4/8-digit hex, `?.` or `??` (the smoke test checks these).

## Band Ninja roster pull (v1.1.0)
- Setup → "Load all blocks from Band Ninja": one Sheets `values:batchGet` for `'1st Block'!A2:A200`, 3rd, 4th, 6th and 7th (column A = "Last, First"). These are the per-block tabs of **Band Ninja Tracker 2026-2027** (`1SMjkABPZx4e1wHdsZ3aRcmyw17SfEYueodGK_UQICIw`, default sheet ID; the sheet is private, so the ID alone exposes nothing). No sheet changes were needed. Mat picked "add a block column", but the per-block tabs already split 3rd from 4th.
- Google Identity Services token client (loaded from accounts.google.com; it can't be bundled), scope `spreadsheets.readonly` only. Token in sessionStorage `sus.bnTok` (~1 h). Config in `sus.bn` {clientId, sheetId, consented}.
- Client ID: the same OAuth client as Part Copier (Cloud project "Part Copier"), which already authorizes the artificialfear.github.io origin. On a device that has used Part Copier, the ID is read from `localStorage['partCopier.v1'].bn.clientId` (same origin). Otherwise paste it once under "Band Ninja connection".
- `shortNames()`: "Last, First" → "First L."; any collisions extend the last name, letter by letter, up to the full name; exact duplicates get " (2)". Sorted A–Z.
- An empty tab keeps the old list. Absent marks are kept for names that are still on the roster. A hand edit clears the "came from Band Ninja" note.
- Test: smoke.py mocks `google.accounts.oauth2` and routes sheets.googleapis.com with fictional names.
- Unverified: whether the GIS sign-in popup works in the ViewBoard's browser. If it doesn't, load the rosters on a laptop and play there, or paste the names.

## Live iPad play (v1.2.0)
Mat's choices (2026-11-20): Apps Script relay; iPad nominations pick the suspects (top `sus` by count, teacher can swap); students request an Emergency Meeting (once per game) and the teacher approves; the board shows vote **counts only** (the board receives who-voted-what from the relay but never displays it).
- **Relay:** `relay/Code.gs`, a standalone Apps Script web app (Execute as Me, access Anyone) on Mat's personal Gmail. CacheService only (TTL 6 h). Keys: `h:CODE` board secret (first board to publish claims the code), `s:CODE` public state JSON (relay stamps `_t`), `c:CODE:N` device claim, `seen:CODE:N`, `v:CODE:MID:N` vote (locked once set), `nm:CODE:MID:N` nomination (changeable), `sos:CODE:N` (once per game). LockService is used only for joins. Actions: ping, host (POST), poll, reset, join, state, vote, nom, sos.
- **Not deployed yet:** `RELAY_URL` in index.html is empty. Until Mat sends the /exec URL, he can paste it under Setup → Live iPad connection (saved as `sus.relay`), and the QR link then carries it as `&x=`. Typed links only work once `RELAY_URL` is set.
- **Board:** `publish(phase)` posts the state on every phase change (lobby, rhythm, meeting, nominate, pick, defense, vote, tally, eject, end), one request in flight at a time with a retry. `pollLoop` polls every 3 s (1.5 s during nominate/vote) for `seen`/`joined`/`sos`/`votes`/`noms`. `liveReady()` = live, the last poll OK, and at least 1 iPad seen → the meeting starts with nominations; otherwise the teacher picks. After voting closes the board waits 1.2 s, polls once more, and `MT.dev` → `MT.votes` (hand +/− adds on top). A re-vote makes a new meeting id.
- **iPad:** the `SP` player object; `sus.player` remembers code+number for auto-rejoin after a refresh; `sus.dev` = device id. It polls every 2 s in meeting phases and 4 s otherwise (plus jitter), and countdowns use relay time (`res.t − st._t`). Two failed polls → "Can't reach the game… vote with your hand."
- **Tests:** `node tests/relay.test.js` (relay unit tests, Apps Script mocks in tests/relay-harness.js); `python3 tests/live.py` (board + 3 iPads through the real Code.gs via tests/relay-server.js, including relay outage → hand fallback → recovery); `python3 tests/smoke.py` (hands-only game).
- **Unverified on real hardware:** the Apps Script latency/quota with about 30 iPads, and the ViewBoard browser.

## Device storage (localStorage, per device)
`sus.classes` (rosters, absent list, rules, rhythm picks per class), `sus.cls`, `sus.rhythms`, `sus.game` (game in progress; resume from Setup), `sus.view`, `sus.theme`, `sus.sound`, `sus.lock.<CODE>` (student devices). Rhythms move between devices with Export/Import in the editor. Rosters stay on the ViewBoard only, and no student names are in the repo.

## Open items / ideas
- Mat hasn't confirmed the default "Advanced" rhythms or the 2-per-line layout.
- Teacher peek (Menu → hold to peek) shows the imposters on the board itself. A phone-only teacher view would need a separate teacher code.
- Imposters don't see who the other imposters are. That could be an option.
- Optional per-class win threshold scaling (e.g. "half the crew").
- 6/8 and triplets in the parser and counts.
