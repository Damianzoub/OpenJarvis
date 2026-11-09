//! J.A.R.V.I.S. HUD, rendered natively by Rune. A port of `frontend/` (Tauri); the backend is unchanged.
//!
//! `cargo run --release` opens the window. Headless: `--snap out.png`, `--tree tree.json`,
//! `--script s.json`, `--list-scenes` (see PORTING.md).

mod activity;
mod cards;
mod chat;
mod conversations;
mod keymap;
mod latex;
mod net;
mod shortcuts_ui;
mod state;
mod style;
mod view;

use std::sync::OnceLock;
use std::time::Duration;

use rune::{AppSpec, Key, KeyEvent, MenuItem, Tx};

use crate::keymap::Action;

use crate::net::Event;
use crate::state::{Message, State, Stats, Thing, Who};

static HANDLE: OnceLock<rune::AppHandle<State>> = OnceLock::new();
const LOGO: &[u8] = include_bytes!("../assets/logo-mark.png");

fn headless() -> bool {
    rune::tooling::headless_run().is_some()
}

fn setup(s: &mut State, waker: rune::Waker) {
    s.waker = Some(waker.clone());
    let images = rune::ImageCache::new(waker.clone());
    let logo = images.load(LOGO);
    if headless() {
        let _ = logo.wait();
    }
    s.logo = Some(logo);
    s.images = Some(images);
    if std::env::var("JARVIS_NO_BACKEND").is_err() {
        net::start_pollers(s.tx.clone(), waker, s.inflight.clone(), headless());
    }
}

/// The banner's RETRY: ask `/system` and `/today` now instead of waiting for the next poll.
pub fn retry_backend(s: &mut State) {
    let Some(wake) = s.waker.clone() else { return };
    s.status = "RECONNECTING...".into();
    let (tx, inflight) = (s.tx.clone(), s.inflight.clone());
    std::thread::spawn(move || {
        net::fetch_stats(&tx, &wake, &inflight);
        net::fetch_today(&tx, &wake, &inflight);
    });
}

fn apply(s: &mut State, ev: Event) {
    match ev {
        Event::Stats(st) => {
            s.stats = Some(st);
            if !s.busy && matches!(s.status.as_str(), "BACKEND OFFLINE" | "RECONNECTING...") {
                s.status = "SYSTEM ONLINE".into();
                s.banner = None;
            }
        }
        Event::Today(things) => s.today = things,
        Event::Weather(w) => s.weather = Some(w),
        Event::Due(texts) => {
            for (i, text) in texts.iter().enumerate() {
                let n = rune_notify::Notification::new(format!("reminder-{}-{i}", chrono::Utc::now().timestamp()), "Reminder").body(text.clone());
                let _ = rune_notify::post(&n);
            }
        }
        Event::Offline => {
            if !s.busy {
                s.status = "BACKEND OFFLINE".into();
                s.banner = Some("Can't reach the backend — is it running?".into());
            }
        }
        Event::Chat(generation, c) => chat::apply(s, generation, c),
    }
}

fn poll(s: &mut State, _t: f64, tx: &mut Tx) -> bool {
    let mut changed = false;
    let now = chrono::Local::now();
    if !headless() && now.timestamp() != s.clock.timestamp() {
        s.clock = now;
        changed = true;
    }
    if !headless() {
        tx.wake_after(Duration::from_millis(1000 - u64::from(now.timestamp_subsec_millis().min(999))));
    }
    // Headless runs have a virtual clock, so wait for real answers before drawing the frame.
    // `chat_gen > 0`: a request really went out (a demo scene's "busy" has nothing to wait for).
    let streaming = s.busy && s.chat_gen.load(std::sync::atomic::Ordering::SeqCst) > 0;
    if headless() && (s.inflight.count() > 0 || streaming) {
        // How long a headless frame waits for the next real event (ms). Long by default so a
        // screenshot "after" a reply has it; tests of in-flight states (STOP) shorten it.
        let wait = std::env::var("JARVIS_HEADLESS_WAIT_MS").ok().and_then(|v| v.parse().ok()).unwrap_or(120_000);
        if let Ok(ev) = s.rx.recv_timeout(Duration::from_millis(wait)) {
            apply(s, ev);
            changed = true;
        }
    }
    while let Ok(ev) = s.rx.try_recv() {
        apply(s, ev);
        changed = true;
    }
    if s.copied.is_some_and(|(_, at)| at.elapsed() >= Duration::from_millis(1500)) {
        s.copied = None;
        changed = true;
    }
    changed
}

fn on_key(s: &mut State, ev: &KeyEvent, tx: &mut Tx) -> bool {
    // The shortcuts editor is recording: the key press becomes the new binding.
    if let Some(action) = s.capturing {
        shortcuts_ui::capture(s, action, ev, tx);
        return true;
    }
    if s.keymap.matches(Action::Clear, ev, tx) {
        s.clear_conversation();
        return true;
    }
    if s.keymap.matches(Action::Mic, ev, tx) {
        chat::toggle_mic(s);
        return true;
    }
    if s.keymap.matches(Action::Cancel, ev, tx) || ev.key == Key::Escape {
        if s.confirm_close {
            s.confirm_close = false;
            return true;
        }
        if s.shortcuts_open {
            s.shortcuts_open = false;
            return true;
        }
        if s.busy {
            chat::stop(s);
            return true;
        }
        if s.mic_on {
            chat::toggle_mic(s);
            return true;
        }
    }
    false
}

/// Rune can't veto a close, so closing hides the window (`keep_running`) and we bring it back
/// with the confirm dialog. Quitting the app (⌘Q) skips the dialog.
fn on_close(s: &mut State, _tx: &mut Tx) {
    if rune::quitting() {
        return;
    }
    s.confirm_close = true;
    if let Some(h) = HANDLE.get().cloned() {
        std::thread::spawn(move || h.open());
    }
}

fn toggle_window(_: &mut State, _: &mut Tx) {
    if let Some(h) = HANDLE.get() {
        if h.is_visible() { h.hide() } else { h.open() }
    }
}

fn scene_demo(s: &mut State) {
    s.stats = Some(Stats { cpu: 23.5, ram: 64.2, used_gb: 15.4, total_gb: 24.0 });
    s.weather = Some(crate::state::Weather { place: "Athens".into(), temp: 18.4, feels: 17.2, code: 2, humidity: 55.0, wind: 12.0, high: 21.0, low: 12.0 });
    s.today = vec![
        Thing { time: "18:30".into(), title: "Gym".into() },
        Thing { time: "20:00".into(), title: "Dinner".into() },
    ];
    s.messages.push(Message { id: 90, from: Who::User, text: "What's the weather like right now?".into(), typing: false });
    s.messages.push(Message {
        id: 91,
        from: Who::Jarvis,
        text: "It's **18°C** and clear in Athens.\n\n- Wind: 12 km/h\n- Humidity: 55%\n\n```python\nprint(\"hello\")\n```".into(),
        typing: false,
    });
    s.messages.push(Message { id: 92, from: Who::User, text: "Check my inbox".into(), typing: false });
    s.messages.push(Message { id: 93, from: Who::Jarvis, text: "Using read_emails...".into(), typing: true });
    s.next_id = 94;
    let full = "It's **18°C** and clear in Athens right now.\n\n- Wind: 12 km/h from the north\n- Humidity: 55%\n- Sunset at 17:12\n\nA light jacket is enough for this evening.";
    s.activity.entries.insert(0, crate::activity::Entry {
        agent: "Weather".into(),
        summary: crate::activity::summarize(full),
        timestamp: chrono::Utc::now().timestamp_millis(),
        full: full.into(),
    });
}

fn scene_maths(s: &mut State) {
    s.messages.push(Message { id: 90, from: Who::User, text: "Explain the quadratic formula".into(), typing: false });
    s.messages.push(Message {
        id: 91,
        from: Who::Jarvis,
        text: "## Quadratic formula\n\nFor $ax^2 + bx + c = 0$ with $a \\neq 0$:\n\n$$x = \\frac{-b \\pm \\sqrt{b^2 - 4ac}}{2a}$$\n\n| Discriminant | Roots |\n|---|---|\n| $b^2 - 4ac > 0$ | two real |\n| $b^2 - 4ac = 0$ | one real |\n| $b^2 - 4ac < 0$ | two complex |\n\nAlso: $\\sum_{i=1}^{n} i = \\frac{n(n+1)}{2}$, and it costs $5 to $10 — not maths.".into(),
        typing: false,
    });
    s.next_id = 92;
}

fn scene_busy(s: &mut State) {
    s.messages.push(Message { id: 90, from: Who::User, text: "What's on my calendar today?".into(), typing: false });
    s.messages.push(Message { id: 91, from: Who::Jarvis, text: String::new(), typing: true });
    s.reply_id = Some(91);
    s.next_id = 92;
    s.busy = true;
    s.status = "THINKING...".into();
    s.steps = vec!["Sent".into(), "Thinking...".into(), "→ Calendar agent".into(), "Using list_events...".into()];
    s.working_agent = Some("Calendar".into());
    s.started = Some(std::time::Instant::now() - std::time::Duration::from_secs(4));
}

fn scene_history(s: &mut State) {
    let now = chrono::Utc::now().timestamp_millis();
    let conv = |id: &str, q: &str, a: &str, mins: i64| crate::conversations::Conversation {
        id: id.into(),
        title: q.into(),
        updated: now - mins * 60_000,
        turns: vec![("user".into(), q.into()), ("assistant".into(), a.into())],
    };
    s.conversations.list = vec![
        conv("c1", "What's the weather like right now?", "It's **18°C** and clear in Athens.", 3),
        conv("c2", "Check my inbox for anything important.", "Two new emails, nothing urgent.", 95),
        conv("c3", "How much have I spent this month on food and going out?", "You spent €212 on food.", 60 * 26),
    ];
    s.open_conversation("c1");
}

fn scene_offline(s: &mut State) {
    s.status = "BACKEND OFFLINE".into();
    s.banner = Some("Can't reach the backend — is it running?".into());
}

fn main() {
    rune::prewarm_gpu();
    let spec = AppSpec::<State> {
        fonts: rune_theme_opencode::FONTS,
        families: rune_theme_opencode::FAMILIES,
        min_size: Some((980.0, 660.0)),
        scenes: &[
            ("demo", scene_demo),
            ("offline", scene_offline),
            ("busy", scene_busy),
            ("maths", scene_maths),
            ("shortcuts", |s| s.shortcuts_open = true),
            ("shortcuts-capture", |s| { s.shortcuts_open = true; s.capturing = Some(Action::Mic); }),
            ("mic", |s| chat::toggle_mic(s)),
            ("confirm-close", |s| s.confirm_close = true),
            ("history", scene_history),
        ],
        setup: Some(setup),
        poll: Some(poll),
        on_key: Some(on_key),
        ..AppSpec::new("J.A.R.V.I.S.", (1200.0, 760.0), State::new, view::view)
    };
    let shortcut = |chord: &str| chord.parse::<rune::Shortcut>().expect("valid shortcut");
    let app = rune::App::new(spec)
        .keep_running()
        .on_close(on_close)
        // Jarvis › Toggle Mic / Clear Conversation, as the Tauri menu has them (⌘M, ⌘L).
        .menu_item(MenuItem::new("Toggle Mic", |s: &mut State, _| chat::toggle_mic(s)).menu("Jarvis").key_equivalent(shortcut("mod+m")))
        .menu_item(MenuItem::new("Clear Conversation", |s: &mut State, _| s.clear_conversation()).menu("Jarvis").key_equivalent(shortcut("mod+l")))
        // ⌘⇧J from anywhere shows or hides the HUD, as the Tauri global shortcut does.
        .global_shortcut("mod+shift+j", toggle_window);
    let _ = HANDLE.set(app.handle());
    app.run();
}
