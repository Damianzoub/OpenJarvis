//! The window: sidebar, top bar, then the dashboard grid beside a permanent chat panel.

use rune::{Cx, El, Tx, col, el, row, text, text_input};

use crate::cards;
use crate::chat;
use crate::state::State;
use crate::style::*;

pub fn view(s: &State, cx: &mut Cx<State>) -> El {
    let body = row().w_full().h_full().fill(bg()).child(sidebar(s)).child(main(s, cx));
    if s.confirm_close {
        return el().w_full().h_full().child(body).child(confirm_close());
    }
    if s.shortcuts_open {
        return el().w_full().h_full().child(body).child(crate::shortcuts_ui::editor(s));
    }
    body
}

fn logo(s: &State, h: f32, pulse: bool) -> El {
    // 512×576 artwork, fitted inside a square box like `object-fit: contain`.
    let w = h * 512.0 / 576.0;
    let mark = el().key("logo-art").size(w, h);
    let mark = match &s.logo { Some(img) => mark.pixels(img.pixels()), None => mark };
    let mut holder = row().size(h, h).justify_center();
    if pulse {
        // `brand-mark-pulse`: a soft halo behind the mark that breathes every 3 s.
        let halo = el().key("logo-halo").size(h * 0.7, h * 0.7).radius(h * 0.35).fill(cyan_tint("18"))
            .shadow(0.0, h * 0.6, cyan_tint("66"))
            .looping(rune::LoopSpec::opacity(3.0, 0.0, 0.45, 1.0))
            .pin(Some(h * 0.15), Some(h * 0.15), None, None);
        holder = holder.child(halo);
    }
    holder.child(mark)
}

const NAV_ROW: f32 = 30.0;
const NAV_GAP: f32 = 2.0;

fn sidebar(s: &State) -> El {
    // The one place the brand lives now: the hero and the second footer are gone.
    let brand = row().key("brand").center_y().gap(10.0).pb(18.0).mb(14.0)
        .border_sides([0.0, 0.0, 1.0, 0.0], border())
        .child(logo(s, 30.0, true))
        .child(col().gap(2.0)
            .child(text("J.A.R.V.I.S.").font(mono(12.0, 500.0, 3.0)).color(cyan()))
            .child(text("PERSONAL AI").font(mono(9.0, 400.0, 2.0)).color(cyan_dim_text())));

    let new_chat = row().key("new-chat").role("button").label("New chat").focusable(true)
        .w_full().h(NAV_ROW).center_y().gap(8.0).px(8.0).mb(12.0).border(1.0, border())
        .hover(cyan_tint("12")).hover_group().press_scale(0.97).cursor(rune::Cursor::Pointer)
        .help(format!("New chat ({})", crate::keymap::display(&s.keymap.clear)))
        .child(text("+").font(mono(12.0, 500.0, 0.0)).color(cyan()))
        .child(text("NEW CHAT").font(mono(10.0, 500.0, 2.0)).color(cyan_dim_text()).group_color(cyan()))
        .on_press(|s: &mut State| {
            chat::stop(s);
            s.clear_conversation();
            s.input.focused = true;
        });

    let heading = text("CONVERSATIONS").font(mono(9.0, 500.0, 2.0)).color(cyan_dim_text()).opacity(0.7).pb(6.0);
    let mut list = col().key("conversations").role("list").label("Past conversations").w_full().gap(NAV_GAP);
    if s.conversations.list.is_empty() {
        list = list.child(text("Nothing yet. Your chats show up here.").font(mono(10.0, 400.0, 0.0)).color(cyan_dim_text()).opacity(0.6).px(8.0));
    }
    for c in &s.conversations.list {
        let active = c.id == s.session_id;
        let ink = if active { cyan() } else { cyan_dim_text() };
        let id = c.id.clone();
        let mut item = col().key(format!("conv-{}", c.id)).role("link").label(c.title.clone())
            .focusable(true).w_full().gap(2.0).px(8.0).py(5.0)
            .border_sides([0.0, 0.0, 0.0, 2.0], if active { cyan() } else { rune::Color::TRANSPARENT })
            .hover(cyan_tint("0a")).hover_group().press_scale(0.98).cursor(rune::Cursor::Pointer)
            .child(text(c.title.clone()).font(mono(10.5, 400.0, 0.0)).color(ink).group_color(cyan()).max_lines(1))
            .child(text(crate::activity::time_ago(c.updated)).font(mono(9.0, 400.0, 0.5)).color(cyan_dim_text()).opacity(0.6))
            .on_press_tx(move |s: &mut State, tx: &mut Tx| {
                chat::stop(s);
                s.open_conversation(&id);
                tx.scroll_to_bottom("messages-scroll");
            });
        if active {
            item = item.fill(cyan_tint("14"));
        }
        list = list.child(item);
    }
    let nav = col().key("nav").w_full().grow(1.0).min_h(0.0)
        .child(new_chat).child(heading)
        .child(col().key("conversations-scroll").w_full().grow(1.0).min_h(0.0).child(list).scroll(rune::ScrollSpec { stick_bottom: false }));

    let footer = text("DAMIANOS INDUSTRIES").key("nav-footer").font(mono(10.0, 400.0, 2.0)).color(cyan_dim_text())
        .opacity(0.6).pt(10.0).w_full().border_sides([1.0, 0.0, 0.0, 0.0], border());

    col().key("sidebar").w(190.0).h_full().fill(surface()).pt(20.0).px(14.0).pb(14.0)
        .border_sides([0.0, 1.0, 0.0, 0.0], border())
        .child(brand).child(nav).child(el().h(12.0)).child(crate::shortcuts_ui::sidebar_section(s)).child(footer)
        .child(corner(false).pin(Some(6.0), None, None, Some(6.0)))
}

fn main(s: &State, cx: &mut Cx<State>) -> El {
    let split = row().key("split").w_full().grow(1.0).min_h(0.0).gap(18.0).pt(12.0)
        .child(cards::grid(s, cx))
        .child(chat_panel(s, cx));
    col().key("main").grow(1.0).h_full().min_w(0.0).fill(surface()).pt(16.0).px(20.0).pb(10.0)
        .child(topbar(s, cx))
        .child(el().h(1.0).w_full().opacity(0.35)
            .linear_gradient(std::f32::consts::FRAC_PI_2, [(0.0, rune::Color::TRANSPARENT), (0.5, cyan()), (1.0, rune::Color::TRANSPARENT)]))
        .child(split)
        .child(footer(s))
        .child(corner(true).pin(None, None, Some(6.0), Some(6.0)))
}

fn greeting(s: &State) -> &'static str {
    match s.clock.format("%H").to_string().parse::<u32>().unwrap_or(12) {
        5..=11 => "GOOD MORNING, SIR",
        12..=17 => "GOOD AFTERNOON, SIR",
        _ => "GOOD EVENING, SIR",
    }
}

/// A labelled light: on (cyan), off (hollow, dimmed) or live (red, pulsing).
fn indicator(key: &str, label: &str, state: Light, help: &str) -> El {
    let (ink, dot) = match state {
        Light::On => (cyan(), glow(el().size(7.0, 7.0).radius(3.5).fill(cyan()), cyan(), 6.0)),
        Light::Off => (cyan_dim_text(), el().size(7.0, 7.0).radius(3.5).border(1.0, cyan_dim_text())),
        Light::Down => (red(), el().size(7.0, 7.0).radius(3.5).fill(red())),
        Light::Live => (red(), glow(el().size(7.0, 7.0).radius(3.5).fill(red()), red(), 8.0)
            .looping(rune::LoopSpec::opacity(0.5, 0.0, 0.3, 1.0))),
    };
    row().key(key.to_string()).role("status").label(format!("{label}: {help}")).gap(6.0).center_y()
        .px(8.0).py(4.0).border(1.0, if matches!(state, Light::Off) { border() } else { ink.alpha(0.5) })
        .opacity(if matches!(state, Light::Off) { 0.7 } else { 1.0 })
        .help(help)
        .child(dot)
        .child(text(label.to_string()).font(mono(10.0, 500.0, 1.5)).color(ink))
}

#[derive(Clone, Copy)]
enum Light { On, Off, Down, Live }

fn topbar(s: &State, cx: &mut Cx<State>) -> El {
    // Narrow windows drop the meter bars and the clock's seconds so the bar fits.
    let compact = cx.layout_size("main").is_some_and(|m| m[0] < 880.0);
    let time = s.clock.format(if compact { "%H:%M" } else { "%H:%M:%S" }).to_string();
    let date = s.clock.format("%A %d %B %Y").to_string().to_uppercase();
    let left = col().key("greeting").gap(3.0)
        .child(text(greeting(s)).font(mono(13.0, 500.0, 3.0)).color(cyan()))
        .child(text(date).key("clock-date").font(mono(10.0, 400.0, 1.0)).color(cyan_dim_text()));
    let api = match (&s.stats, &s.banner) {
        (_, Some(_)) => (Light::Down, "Backend unreachable"),
        (Some(_), None) => (Light::On, "Backend online"),
        (None, None) => (Light::Off, "Waiting for the backend"),
    };
    let ram_detail = s.stats.as_ref().map_or("Waiting for the backend".to_string(), |st| format!("RAM {}GB / {}GB", st.used_gb, st.total_gb));
    let meters = row().key("card-system").role("group").label("System").gap(14.0).center_y().px(10.0).py(5.0)
        .border(1.0, border())
        .child(cards::meter("CPU", s.stats.as_ref().map(|st| st.cpu), 80.0, "CPU load".into(), !compact))
        .child(cards::meter("RAM", s.stats.as_ref().map(|st| st.ram), 85.0, ram_detail, !compact));
    let lights = row().key("indicators").gap(8.0).center_y()
        .child(indicator("ind-api", "API", api.0, api.1))
        .child(indicator("ind-voice", "VOICE", if s.voice_up { Light::On } else { Light::Off },
            if s.voice_up { "Voice bot reachable — not wired into this app yet" } else { "Voice bot unreachable" }))
        .child(indicator("ind-mic", "MIC", if s.mic_on { Light::Live } else { Light::Off }, if s.mic_on { "Mic on (state only)" } else { "Mic off" }));
    row().key("topbar").w_full().center_y().gap(16.0).pb(12.0)
        .child(left)
        .child(el().grow(1.0))
        .child(meters)
        .child(lights)
        .child(row().key("clock-time").role("timer").label(time.clone()).w(if compact { 64.0 } else { 98.0 }).justify_end()
            .child(rolling("clock-roll", time, mono(18.0, 500.0, 2.0), cyan(), None)))
}

/// The conversation, always visible: header, messages, then banner, suggestions and input.
fn chat_panel(s: &State, cx: &mut Cx<State>) -> El {
    let split_w = cx.layout_size("split").map_or(1000.0, |sz| sz[0]);
    let w = (split_w * 0.44).clamp(380.0, 620.0).floor();
    let count = (s.messages.len() > 1).then(|| format!("{} MESSAGES", s.messages.len()));
    let clear = text("CLEAR").key("chat-clear").role("button").label("Clear the conversation").focusable(true)
        .font(mono(9.0, 500.0, 1.5)).color(cyan_dim_text()).px(6.0).py(2.0).border(1.0, border())
        .hover(cyan_tint("15")).press_scale(0.95).cursor(rune::Cursor::Pointer)
        .help(format!("Clear ({})", crate::keymap::display(&s.keymap.clear)))
        .on_press(|s: &mut State| s.clear_conversation());
    let mut header = row().key("chat-header").w_full().center_y().gap(8.0).pb(8.0)
        .border_sides([0.0, 0.0, 1.0, 0.0], border())
        .child(text(">_").font(mono(12.0, 500.0, 0.0)).color(cyan()))
        .child(text("CONVERSATION").font(mono(10.0, 500.0, 2.0)).color(cyan()))
        .child(el().grow(1.0));
    if let Some(c) = count {
        header = header.child(text(c).font(mono(9.0, 400.0, 1.0)).color(cyan_dim_text()));
    }
    header = header.child(clear);
    col().key("card-conversation").role("group").label("Conversation").w(w).h_full().min_h(0.0)
        .fill(cyan_tint("06")).border(1.0, border()).pt(12.0).px(14.0).pb(10.0)
        .child(header)
        .child(cards::messages(s))
        .child(banner(s))
        .child(composer(s))
}

fn banner(s: &State) -> El {
    let Some(msg) = &s.banner else { return el().key("banner-none") };
    let retry = row().key("banner-retry").role("button").label("Retry").focusable(true)
        .px(10.0).py(3.0).border(1.0, red()).hover(red_tint("22")).press_scale(0.95).cursor(rune::Cursor::Pointer)
        .child(text("RETRY").font(mono(10.0, 500.0, 1.5)).color(red()))
        .on_press(|s: &mut State| crate::retry_backend(s));
    row().key("connection-banner").role("alert").label(msg.clone()).live_region(rune::LiveRegion::Assertive)
        .w_full().mt(8.0).px(10.0).py(6.0).gap(8.0).center_y()
        .border(1.0, red()).fill(red_tint("12"))
        .transition(rune::Transition::offset(0.0, 6.0).combined(rune::Transition::opacity()))
        .child(text("⚠").font(mono(11.0, 400.0, 0.0)).color(red()).looping(rune::LoopSpec::opacity(1.2, 0.0, 0.4, 1.0)))
        .child(text(msg.clone()).font(mono(11.0, 400.0, 0.5)).color(red()).wrap().grow(1.0).shrink())
        .child(retry)
}

pub fn button(key: &str, label: &str, filled: bool, ink: rune::Color) -> El {
    let b = row().key(key.to_string()).role("button").label(label.to_string()).focusable(true)
        .h(32.0).px(14.0).center_y().justify_center().border(1.0, ink)
        .press_scale(0.95).cursor(rune::Cursor::Pointer)
        .child(text(label.to_string()).font(mono(11.0, 500.0, 2.0)).color(if filled { bg() } else { ink }));
    if filled { glow(b.fill(ink), cyan_tint("55"), 10.0).hover(rune::Color::WHITE.alpha(0.18)) } else { b.hover(cyan_dim()) }
}

/// Three dots that pulse one after another: "working on it".
pub fn pulse_dots(ink: rune::Color) -> El {
    let dot = |i: usize| el().key(format!("pulse-{i}")).size(4.0, 4.0).radius(2.0).fill(ink)
        .looping(rune::LoopSpec::opacity(0.9, i as f64 * 0.15, 0.2, 1.0));
    row().key("pulse").gap(4.0).center_y().a11y_hidden().child(dot(0)).child(dot(1)).child(dot(2))
}

/// Quick prompts above the input while the conversation is fresh.
const SUGGESTIONS: [(&str, &str); 4] = [
    ("Today", crate::state::TODAY_PROMPT),
    ("Inbox", "Check my inbox for anything important."),
    ("Weather", "What's the weather like right now?"),
    ("Headlines", "Give me today's top headlines."),
];

fn suggestions(s: &State) -> El {
    if s.busy || s.messages.len() > 1 || !s.input.text.is_empty() {
        return el().key("suggestions-none");
    }
    let mut chips = row().key("suggestions").role("list").label("Suggestions").w_full().gap(6.0).pt(8.0).flex_wrap()
        .transition(rune::Transition::opacity());
    for (label, prompt) in SUGGESTIONS {
        chips = chips.child(
            row().key(format!("suggest-{}", label.to_lowercase())).role("button").label(prompt).focusable(true)
                .px(10.0).py(4.0).radius(10.0).border(1.0, border()).fill(cyan_tint("08"))
                .hover(cyan_dim()).press_scale(0.95).cursor(rune::Cursor::Pointer).hover_group()
                .help(prompt)
                .child(text(format!("› {label}")).font(mono(10.0, 400.0, 1.0)).color(cyan_dim_text()).group_color(cyan()))
                .on_press_tx(move |s: &mut State, tx: &mut Tx| chat::send(s, tx, prompt.to_string())),
        );
    }
    chips
}

fn composer(s: &State) -> El {
    let field = text_input(&s.input, mono(12.0, 400.0, 0.5)).key("chat-input").label("Command")
        .single_line().placeholder(if s.busy { "Jarvis is working..." } else { "Ask Jarvis..." }, cyan_dim_text())
        .help("Enter sends · ↑ / ↓ bring back earlier prompts")
        .color(cyan()).grow(1.0).min_w(0.0).px(6.0).py(4.0)
        .border_sides([0.0, 0.0, 1.0, 0.0], if s.input.focused { cyan() } else { cyan_tint("88") })
        .on_edit(|s: &mut State| &mut s.input)
        .on_input_key(|s: &mut State, ev: &rune::KeyEvent, tx: &mut Tx| {
            // The field sees keys before the window's shortcuts, so Cancel (Esc) stops a reply here.
            if s.busy && s.keymap.matches(crate::keymap::Action::Cancel, ev, tx) {
                chat::stop(s);
                return true;
            }
            match ev.key {
                rune::Key::Up => chat::recall(s, true),
                rune::Key::Down => chat::recall(s, false),
                _ => false,
            }
        })
        .on_submit(|s: &mut State, tx: &mut Tx| chat::submit(s, tx));

    // Voice isn't ported: MIC stays honest — dimmed, and its tooltip says why.
    let mic_ink = if s.mic_on { red() } else { cyan_dim_text() };
    let mic = button("mic-btn", if s.mic_on { "● LIVE" } else { "MIC" }, false, mic_ink).px(10.0)
        .checked(s.mic_on)
        .description("Voice is not available in the Rune build yet")
        .help(format!("Voice isn't ported to Rune yet — this only shows the mic state ({})", crate::keymap::display(&s.keymap.mic)))
        .on_press(|s: &mut State| chat::toggle_mic(s));
    let mic = if s.mic_on { glow(mic.fill(surface()), red_tint("aa"), 14.0) } else { mic.opacity(0.75) };

    let import = button("import-btn", "+", false, cyan()).px(11.0).label("Import a file")
        .help("Import a file for Jarvis to check")
        .on_press_tx(|_: &mut State, tx: &mut Tx| chat::import_file(tx));
    let send = if s.busy {
        // While a reply streams, SEND becomes STOP (Esc does the same).
        row().key("stop-btn").role("button").label("Stop the reply").focusable(true).h(32.0).px(10.0).gap(7.0)
            .center_y().justify_center().border(1.0, red()).fill(surface())
            .hover(red_tint("22")).press_scale(0.95).cursor(rune::Cursor::Pointer)
            .help(format!("Stop the reply ({})", crate::keymap::display(&s.keymap.cancel)))
            .child(el().size(8.0, 8.0).radius(1.0).fill(red()).looping(rune::LoopSpec::opacity(1.0, 0.0, 0.5, 1.0)))
            .child(text("STOP").font(mono(11.0, 500.0, 2.0)).color(red()))
            .on_press(|s: &mut State| chat::stop(s))
    } else {
        button("send-btn", "SEND", true, cyan()).px(12.0).on_press_tx(|s: &mut State, tx: &mut Tx| chat::submit(s, tx))
    };

    let prompt = text(">_").font(mono(14.0, 500.0, 0.0)).color(cyan());
    let prompt = if s.input.focused { prompt.looping(rune::LoopSpec::opacity(1.6, 0.0, 0.55, 1.0)) } else { prompt };
    col().key("composer").w_full()
        .child(suggestions(s))
        .child(row().key("input-row").w_full().center_y().gap(6.0).pt(10.0)
            .child(prompt)
            .child(import).child(field).child(mic).child(send))
}

fn footer(s: &State) -> El {
    let item = |key: &str, t: String| text(t).key(key.to_string()).font(mono(10.0, 400.0, 2.0)).color(cyan_dim_text());
    let status = item("status-text", s.status.clone()).role("status").live_region(rune::LiveRegion::Polite);
    let status = match s.status.as_str() {
        "SYSTEM ONLINE" => status.opacity(0.7),
        "BACKEND OFFLINE" => status.color(red()),
        _ => status.color(cyan()),
    };
    let mut left = row().key("status").gap(8.0).center_y();
    if s.busy {
        left = left.child(pulse_dots(cyan()));
    }
    left = left.child(status);
    row().key("hud-footer").w_full().justify_between().center_y().pt(8.0)
        .child(left)
        .child(item("footer-version", "V0.0.0".into()))
}

fn confirm_close() -> El {
    let yes = button("close-yes", "CLOSE", true, cyan()).on_press_tx(|_: &mut State, tx: &mut Tx| tx.quit());
    let no = button("close-no", "CANCEL", false, cyan()).on_press(|s: &mut State| s.confirm_close = false);
    let dialog = col().key("close-dialog").role("dialog").label("Close Jarvis?").gap(14.0).padding(20.0)
        .fill(surface()).border(1.0, cyan())
        .child(text("CLOSE JARVIS?").font(mono(12.0, 500.0, 3.0)).color(cyan()))
        .child(row().gap(10.0).child(no).child(yes))
        .modal(true, |s: &mut State| s.confirm_close = false);
    el().pin(Some(0.0), Some(0.0), Some(0.0), Some(0.0)).fill(rune::Color::BLACK.alpha(0.6))
        .center().child(dialog)
}
