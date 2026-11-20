# Changelog

## 1.2.0 — 2026-11-20
- **Play on iPads.** Students join with the game code and their number. Their iPad follows the game: the current rhythm, the Emergency Meeting, the suspects, the result, and who won.
- **Nominate on iPads.** At each meeting, everyone still in taps who's most sus. The top picks become the suspects automatically, and you can still swap anyone.
- **Vote on iPads.** Votes are locked once they're in (no changing). The board counts them, and you can add hand votes for students without an iPad.
- **Emergency Meeting button on iPads**, once per student per game. The board shows "Jade wants an Emergency Meeting" and you choose Start or Ignore.
- The lobby shows who has joined (✓). Tap a ✓ name to let that student rejoin from a different iPad.
- **Hand signals are the fallback.** If the iPads can't connect, the board says "iPads offline: use hands" and the game runs like before.
- Voting countdown default is now 15 seconds, and there's a new "Nomination time" setting (20 seconds).
- Needs the Sus Rhythms relay deployed once (see relay/README.md).

## 1.1.0 — 2026-11-20
- New **Load all blocks from Band Ninja** button in Setup. After a Google sign-in, it fills the 1st, 3rd, 4th, 6th and 7th Block rosters from the Band Ninja Tracker in one step. 3rd and 4th Block each get their own list.
- Names show as "First L." (first name + last initial), sorted A–Z. When two students would look the same, more of the last name is shown.
- Uses the same Google sign-in as Part Copier. It only reads the sheet and never changes it.

## 1.0.3 — 2026-11-20
- Home title is now centered on the page. It used to sit off to the right on wide screens.

## 1.0.2 — 2026-11-20
- Home title is now level (no tilt). The bounce animation is unchanged.

## 1.0.1 — 2026-11-20
- Bigger, stylized "Sus Rhythms" title on the home screen: 3D outlined letters that bounce across the word like a playhead. On narrow screens the two words stack.

## 1.0.0 — 2026-11-20
- First version of Sus Rhythms, the web version of the Among Us rhythm game.
- Students check their secret role on their iPads with a game code or QR code. Brightspace messages are no longer needed.
- Rhythms show as real notation with a count-in, a moving highlight, an optional metronome click and optional counting under the notes.
- Your 10 original rhythms are built in, plus 4 advanced ones. Add your own in the Rhythm editor.
- Emergency Meetings come with an alarm, suspect picker (A–D), defense timer, voting countdown, vote counter and airlock ejection.
- Wins are tracked automatically. Rules are adjustable for each class, plus an undo, resume after refresh, and a light/dark theme.
