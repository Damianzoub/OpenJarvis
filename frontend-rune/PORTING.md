# Porting the J.A.R.V.I.S. HUD from Tauri to Rune

Status: **ported**, except voice (see below). `frontend/` is unchanged and still the reference.

## Run it

```sh
cd frontend-rune
cargo run --release            # the window; talks to http://localhost:8000
```

| Variable | Effect |
|---|---|
| `JARVIS_BACKEND=http://host:port` | Another backend (tests used a second copy on :8001) |
| `JARVIS_NO_BACKEND=1` | Send every request nowhere (screenshots without touching the real backend) |
| `JARVIS_ACTIVITY_FILE=path` | Where Recent Activity is saved (default `~/Library/Application Support/OpenJarvis/activity.json`) |

## Pinned Rune

| | |
|---|---|
| Repo | https://github.com/anomalyco/rune, branch `dev` |
| Rev | `3ff3cc6152b9034a1d996e3a5575c51fab3b56b8` (2026-11-08) |
| Toolchain | Rust `1.99.1`, pinned in `rust-toolchain.toml` (Rune's own pin) |
| Crates | `rune` (+ `native-file-dialog`), `rune-kit` (+ `markdown`), `rune-theme-opencode` (fonts), `rune-notify` |

## How it was checked

Every stage was checked with a headless screenshot, an element-tree dump and a scripted run, not just a clean build. The scripts are in `scripts/`, and the screenshots in `shots/`.

```sh
B=target/release/jarvis-hud
$B --snap out.png --size 860x660            # screenshot
$B --tree tree.json                         # element tree + accessibility
$B --script scripts/stage3-chat.json --snap after.png --at mark:end
$B --list-scenes                            # demo, offline, mic, confirm-close
cargo test --release                        # SSE parsing, activity summaries
```

Headless runs use a virtual clock, so `poll` blocks for real network answers while a request is in flight (`net::Inflight`). That keeps screenshots of real backend replies deterministic.

| Stage | Evidence |
|---|---|
| 1 · Static shell | `shots/1-shell.png`; the tree has 12 nav links, 14 headings, the text input and the status line. `1-nav-mic.png`: a nav tap scrolls to Reminders and marks it active; Ctrl+M turns the mic dot red |
| 2 · `/system` polling | `2-stats-live.png`: real CPU/RAM from the running backend. `2-offline.png`: unreachable backend shows the banner and `BACKEND OFFLINE` |
| 3 · Streaming chat | `3-chat-live.png`: a real streamed reply rendered as a Markdown list; input cleared; Recent Activity updated. `3-chat-offline.png`: failed request, banner, user turn rolled back. `3-demo-markdown.png`: code block, bold, typing cursor |
| 4 · The rest | `4-card.png`: "Check weather" sent its preset prompt and the Weather card lit up. `4-end.png`: Ctrl+L cleared the chat; ⌘⇧J registered. `4-confirm-close.png`. `5-demo-dashboard.png`: Today's Things with entries |

## Capability table, final

| Capability | Tauri HUD | Rune port | Status |
|---|---|---|---|
| Window `J.A.R.V.I.S.`, 860×660, resizable | `tauri.conf.json` | `AppSpec`, min 640×480 | **Done** |
| Sidebar, top bar, hero, card grid, input row, footer | HTML + CSS | `view.rs`, `cards.rs`; the grid is a wrapped row that recomputes `auto-fill, minmax(190px, 1fr)` from its own width | **Done** |
| HUD colours, bracket corners, glows | `styles.css` | `style.rs` with the same hex tokens | **Done**; text glow (`text-shadow`) not reproduced, box glows are |
| Monospace font | Courier New | IBM Plex Mono (embedded, OFL) | **Done**, visibly different face |
| Clock, ticking | `setInterval` 1 s | `poll` + `tx.wake_after` to the next second | **Done** |
| `/system` every 3 s | `fetch` | worker thread + `ureq`, channel + waker | **Done** |
| `/today` every 60 s | `fetch` | same; a failure keeps the last list | **Done** |
| `/reminders/due` every 30 s → notification | plugin-notification | `rune-notify` | **Done**, but macOS only posts from a bundled `.app`; a bare `cargo run` skips it |
| Streaming `POST /chat` | `ReadableStream` | worker reads `data:` lines; `text` replaces (cumulative), malformed lines skipped | **Done** |
| Offline banner | `catch` | from a failed `/system` poll or a failed chat; never blocks | **Done** |
| History, rollback on failure, session id | arrays + `crypto.randomUUID` | `State::history`, `uuid` | **Done** |
| Markdown replies | `marked` | `rune-kit` Markdown, HUD colours, code highlighting | **Done**, and it now highlights code, which the Tauri HUD never did |
| Agent cards: badge, latest reply, preset prompt | DOM | `cards.rs`; prompts copied verbatim | **Done** |
| Recent Activity across restarts | `localStorage` | JSON file | **Done** |
| Import a file | plugin-dialog | `tx.open_file` | **Done** (sheet on macOS) |
| Enter / Ctrl+M / Ctrl+L / Esc | `keydown` | `on_submit`, `on_key` with `Chord` (literal Control, as before) | **Done** |
| Native menu Jarvis › Toggle Mic ⌘M, Clear ⌘L | Tauri menu + events | `App::menu_item` | **Done** |
| Global ⌘⇧J show/hide | global-shortcut plugin | `App::global_shortcut` | **Done** (missing from the task's list) |
| Confirm on close | `onCloseRequested` + `confirm()` | `keep_running` + reopen with an in-app modal | **Partial**: the window hides for a moment before the dialog shows; ⌘Q quits without asking |
| TEST CALL button | styling only, no handler | toggles its red "in call" look | **Same as today** |
| Voice call (MIC) | Pipecat client + WebRTC | none | **Not ported**: see below |
| Mobile drawer / tab bar | media queries | — | **Dropped on purpose** |

## What did not make it over, and why

1. **Voice.** Rune has no WebRTC, and the Pipecat browser client can't come along. MIC and Ctrl+M flip a visible state (red button, red dot), the status line says `VOICE NOT PORTED — MIC STATE ONLY`, and hovering MIC explains it. No call is faked. A real path is `webrtc-rs` + `cpal` + Opus talking to the same `/api/offer`: a project of its own.
2. **Text glow.** CSS `text-shadow` has no Rune equivalent on text; the wordmark, clock and labels are flat cyan.
3. **Courier New.** It can't be embedded, so IBM Plex Mono stands in.
4. **Exact close guard.** See "Confirm on close" above and issue 1 below.
5. **Side-by-side screenshots.** Chrome isn't installed here, so there's no headless render of the Tauri HUD to put next to these.

## Corrections to the task description

- `highlight.js` is in `package.json`, but `main.ts` never imports it.
- The task's list leaves out the native menu, the global ⌘⇧J shortcut and the session id; all are ported.
- The accents in `styles.css` are blue `#5b9dff` and red-orange `#ff4d00`, not cyan/amber; the port follows the CSS.
- The Tauri HUD never shows the banner for a failed poll; the task asks for it on any failure. The port shows it only when `/system` (the backend itself) is unreachable or a chat fails, so a 404 from one route doesn't claim the backend is down.

## Rune issues to file upstream

1. **No way to cancel a window close.** `App::on_close` runs before the close but can't veto it, so "unsaved changes?" or "close app?" dialogs need `keep_running` plus reopening the window, which flashes. Electron (`close` event `preventDefault`) and Tauri (`onCloseRequested`) both allow it. Ask: `Tx::cancel_close()` inside `on_close`, or `on_close` returning a bool.
2. **Shadows draw under the whole box.** `.shadow(..)` on an element with no fill (an outline button) tints its inside, where CSS `box-shadow` is clipped to outside the border box. A red glow on a transparent MIC button hid its label. The workaround is an opaque fill. Ask: document it, or add an outside-only option.
3. **`hex` isn't at the crate root.** `rune::Color`, `oklch` and `oklcha` are re-exported, but `hex` is only at `rune::color::hex`.
4. **Headless runs and real I/O.** The virtual clock races ahead of background threads, so a screenshot taken "after" a network reply may not contain it. Apps have to block in `poll` themselves. Ask: a documented pattern, or a tooling hook such as "wait until the app says it's idle".
5. **Script `type` takes time that isn't documented.** `type` becomes one key per character over several frames, so a `key: Enter` at a fixed time can land mid-word (it did: "say hel" was sent and the rest typed after). Ask: document the per-character interval, or let `type` finish before later events.

## Beyond the Tauri HUD (interactive pass)

Added after the port, all checked headlessly (`shots/6-*.png`, `scripts/ui-*.json`):

| What | How it behaves |
|---|---|
| Sidebar highlight | One marker springs to the active section instead of each row repainting; rows brighten on hover and shrink slightly on press |
| Hover and press everywhere | Buttons and chips tint on hover and press in; card buttons reveal a `→` and a tooltip with the exact prompt they send; cards light a scan line along their top edge |
| Fresh replies | An agent card that answered in the last minute keeps a brighter, glowing frame; its badge counts up ("just now", "3m ago") |
| Expand a card's reply | `▾ MORE` opens the full last reply as Markdown, `▴ LESS` closes it (Recent Activity now keeps the full text) |
| Recent Activity rows | Click one to jump to that agent's card with its reply opened |
| Suggestions | While the conversation is fresh, chips above the input send Today / Inbox / Weather / Headlines in one click |
| Input history | `↑` / `↓` walk through prompts sent this session; the `>_` prompt breathes while the field has focus |
| Busy state | While a reply streams, SEND becomes a disabled dots button, card buttons dim, the input says "Jarvis is working...", and the footer pulses |
| Thinking indicator | Three pulsing dots until the first text arrives, then the text with a blinking cursor |
| Copy a reply | Hover a Jarvis reply for `COPY`; it says `COPIED ✓` for 1.5 s |
| Messages and rows | New messages, Today rows and activity rows slide and fade in |
| Offline banner | The ⚠ blinks; `RETRY` checks `/system` and `/today` right away |
| Logo and stats | A soft halo breathes behind the hero logo; a CPU/RAM bar over its limit turns red and throbs |

## Shortcuts editor and maths

- **Shortcuts live in the sidebar**, between the nav list and TEST CALL, ruled above and below. Clicking the block opens a pop-up: `CHANGE` records the next key press, clashes and bare letters are refused with a reason, `RESET` restores the defaults, and changes save to `~/Library/Application Support/OpenJarvis/shortcuts.json` (`JARVIS_SHORTCUTS_FILE` overrides it). Send (Enter) and Show/Hide (⌘⇧J) are shown as fixed. Checked with `scripts/shortcuts-rebind.json` (`shots/7-*.png`).
- **LaTeX.** rune-kit's Markdown has no maths, so `src/latex.rs` converts it to Unicode first: inline `$…$` / `\(…\)` becomes italic text (`α² + 1⁄2`), display `$$…$$` / `\[…\]` becomes a framed block. Currency (`$5 and $10`) and code are left alone. There's no 2-D layout (stacked fractions, big operators with limits above and below); that would need a typesetting engine. Unit tests cover it; `shots/8-maths.png` shows it.

## Layout pass (chat-first)

`shots/9-*.png`. The window opens at 1200×760 (minimum 980×660).

- **Chat is always visible**: a panel on the right (44% of the width, 380–620 pt) holds the conversation, a CLEAR button, the offline banner, suggestions and the input. "Chat" in the sidebar now focuses the input.
- **Hero removed**: the top bar shows a greeting and the date on the left, and API / VOICE / MIC lights and a large clock on the right. API is cyan when `/system` answers, red when the backend is unreachable, hollow while waiting; VOICE is hollow with a tooltip saying it isn't ported.
- **Honest controls**: TEST CALL (no handler in either app) is gone; MIC is dimmed when off, with a tooltip saying it only shows state. Today's empty state says the Google sign-in may have expired, since `/today` can't tell "no events" from "not connected".
- **Fewer duplicates**: the brand lives only in the sidebar (logo with its breathing halo); the bottom bar is just the status line and the version.
- **Readability**: monospace text under 12 pt is one point larger than the CSS sizes; Markdown tables use HUD colours.

## Dashboard pass (tiles)

`shots/10-*.png`.

- **Agent tiles**: the nine agent cards are 64 pt tiles in a 3-column grid (2 below ~880 pt). Clicking anywhere on a tile sends its preset prompt; the tooltip shows the prompt. The second line is the agent's last reply, or what it does if it hasn't answered. A tile that answered in the last minute keeps a brighter frame.
- **Recent Activity on top**: one line per reply (last 3, `SHOW ALL` for 10); clicking a line expands its full reply as Markdown in place.
- **Today** is a compact card with `ASK JARVIS →` in its header.
- **System** is now two meters in the top bar (CPU, RAM; the tooltip on RAM shows GB used). Narrow windows drop the bars and the clock's seconds.
- **Sidebar** has five links: Dashboard, Chat, Activity, Today, Agents.

## Live weather on the Weather tile

- The app fetches current conditions from **Open-Meteo** every 10 minutes on the polling thread: the same free, keyless service `backend/tools/weather.py` uses, called directly so the backend stays unchanged. City: `JARVIS_WEATHER_CITY` (default Athens, matching the calendar's time zone).
- The tile shows glyph, temperature and conditions (`☁ 15° overcast`) with today's high/low in its corner; the tooltip adds feels-like, humidity and wind. Clicking it still asks the Weather agent. It works while the backend is down.
- Checked against Open-Meteo's own response (14.6°, code 3 = overcast → tile `15° overcast`); `shots/12-weather-*.png`. A cleaner long-term home is a backend `/weather` route reusing the tool, so the city and the code table live in one place.

## Reactivity pass

`shots/13-*.png`; checked against a scripted fake backend (same `/chat` event shape, fixed delays) so STOP and timing could be tested without the real one.

- **The working agent lights up**: as soon as the stream names the agent (`tool`/`text` events carry `agent`), its tile glows and shows `WORKING`; Calendar requests light the Today card.
- **Steps in the chat**: the in-flight reply lists what happened so far (Sent → Thinking... → → Weather agent → Using get_weather...), finished steps ticked, the current one pulsing, with a running seconds counter.
- **Measured timing**: each finished reply gets a footer like `WEATHER AGENT · 1.3 S`, or `· FIRST TEXT 6.1 S · DONE 8.4 S` when the two differ by more than half a second.
- **STOP / Esc**: while a reply streams SEND becomes STOP. Each request carries a generation number; STOP bumps it, the worker drops the connection at its next read, and anything that still arrives for the old request is ignored. The user turn is rolled back, as on a failure. Esc works from inside the input too (the field sees keys before the window's shortcuts).
- **Rolling numbers**: the clock, CPU/RAM values and the temperature use rune-kit's `RollingText`, so changed digits roll instead of jumping.
- **Reply notification**: when a reply finishes while the app isn't focused, `rune-notify` posts "Jarvis · <agent>" with the summary. Like reminders, this only shows from a bundled `.app`.
- Test-only: `JARVIS_HEADLESS_WAIT_MS` shortens how long a headless frame waits for a real event (default 120 s), so in-flight states can be captured.
