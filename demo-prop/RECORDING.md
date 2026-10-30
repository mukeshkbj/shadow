# Recording the refund demo

The demo prop is a fake shop back office with made-up data. Open `demo-prop/index.html` in Chrome or Edge (double-click it; it needs no server).

## Settings
- **MP4 (H.264) with your microphone.** The Meta API accepts `video/mp4` only.
- 1280×720 or 1920×1080, 30 fps. Browser window only, zoom 110–125% so the text is readable.
- Windows: Xbox Game Bar (`Win + Alt + R`) records the active window as MP4 with mic, or use OBS (Output → Recording format: mp4).
- Aim for 3–5 minutes. Speak a little slower than normal and pause for a second between steps. That helps the timestamps.

## Take A — the main demo (Alex Morgan, ORD-10421, £612.40)
Say things in your own words; the **bold** parts matter because they're what Shadow should pick up.

1. *Inbox.* "I'm in the refunds inbox. **I always take the oldest one first**." — but **leave the sort on "Newest first"** and click the top request (Alex Morgan, the newest) anyway. (Deliberate conflict: Shadow should flag this step as Inferred.)
2. *Read the email.* "Customer says the lamp arrived broken, order ten-four-two-one."
3. *Look up the order.* Type `ORD-10421` in Orders, press Search. Say nothing about why.
4. *30-day check.* Point at Purchase date. "**If it's more than thirty days old we can only do store credit.** This one's fine, it's from the twelfth."
5. *Amount check.* Move the mouse between Order total and Refund amount and pause. **Say nothing.** (Shadow should mark this Inferred.)
6. *Approval.* Open Approver. "**Anything over five hundred pounds I send to my manager first, before I touch the payment.**" Pick Sam K.
7. *Issue.* Click **Issue refund**. "That goes back on their card in three to five days."
8. *Email.* Choose the **Refund confirmed** template, then Send. "Last thing, the confirmation email."

**Do not show or mention** (these should come back as open questions):
- what happens if the customer refuses store credit
- who approves when the manager is away
- partial refunds

## Take B — same workflow, different words (Chris Lee, ORD-09980)
Use this on Day 6 to show the output isn't hard-coded. Change the sort to **Oldest first** this time, look up `ORD-09980` (bought 30 Aug, outside 30 days), say "too old for a refund, so it's store credit", click **Offer store credit**, use the **Store credit offered** template.

## After recording
```
python scripts\probe.py recordings\take-a.mp4
```
Check the `t` values against the video. If most land within a few seconds of the real moment, use single-call mode. If not, the app slices the video into 30-second windows automatically (`SHADOW_WINDOW_SECONDS=30`).
