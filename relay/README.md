# Sus Rhythms live relay

A tiny Google Apps Script web app that passes game phases from the ViewBoard to the iPads, and passes nominations, votes and Emergency Meeting requests back to the board.

- It only uses Apps Script's built-in short-term cache. Everything disappears within 6 hours. There's no spreadsheet, no Drive file and no email.
- It never knows who the imposters are. Each iPad works out its own role from the game code.
- It holds student names ("First L.") only while a game is running, so the iPads can show who to nominate and vote for.

## Deploy it once (about 3 minutes)

1. Go to **script.google.com** while signed in to your **personal Gmail** (the same account that runs the Band Ninja Dojo).
2. **New project** → rename it **Sus Rhythms Relay**.
3. Delete what's in `Code.gs`, paste in the whole of `relay/Code.gs` from this repo, and **Save**.
4. **Deploy → New deployment** → gear icon → **Web app**.
   - Description: `Sus Rhythms relay`
   - Execute as: **Me**
   - Who has access: **Anyone** (students aren't signed in to your account)
5. **Deploy**, and click through Google's permission prompts.
6. Copy the **Web app URL**. It ends in `/exec`.
7. Send that URL to Claude to build into the app, or paste it into **Setup → Live iPad connection → Save**, then **Test connection**.

## Updating it later
Paste the new `Code.gs` → **Deploy → Manage deployments** → pencil icon → Version: **New version** → **Deploy**. Don't use "New deployment", which would change the URL.

## Limits
Apps Script handles a class of about 30 iPads checking in every 2–4 seconds fine. If it ever slows down or errors, the board shows **"iPads offline: use hands"** and the game keeps going with hand signals.
