//! The dashboard grid and its cards.

use rune::{Align, Cx, El, ScrollSpec, Tx, col, el, row, text};
use rune_kit::markdown::{Markdown, MarkdownStyle};

use crate::activity::time_ago;
use crate::chat;
use crate::state::{AGENT_CARDS, State, TODAY_PROMPT, Who};
use crate::style::*;

const GAP: f32 = 10.0;
const MIN_TILE: f32 = 160.0;

/// As many 160 pt tile columns as fit the agents row, stretched to fill it.
fn tile_width(cx: &Cx<State>) -> f32 {
    let w = cx.layout_size("agents-body").map(|s| s[0]).unwrap_or(540.0);
    let cols = ((w + GAP) / (MIN_TILE + GAP)).floor().max(1.0);
    ((w - GAP * (cols - 1.0)) / cols).floor()
}

/// The dashboard: Recent Activity on top, Today, then the agents as compact tiles.
pub fn grid(s: &State, cx: &mut Cx<State>) -> El {
    let w = tile_width(cx);
    let mut tiles = row().key("agents-body").role("list").label("Agents").w_full().flex_wrap().gap(GAP);
    for card in AGENT_CARDS {
        tiles = tiles.child(tile(s, card).w(w));
    }
    let agents = col().key("agents").w_full().gap(8.0)
        .child(row().w_full().center_y().gap(8.0)
            .child(text("◈").font(mono(11.0, 400.0, 0.0)).color(cyan()))
            .child(text("AGENTS").font(mono(10.0, 500.0, 2.0)).color(cyan()))
            .child(el().grow(1.0))
            .child(text("CLICK A TILE TO ASK").font(mono(8.5, 400.0, 1.5)).color(cyan_dim_text())))
        .child(tiles);
    let body = col().key("dash").w_full().gap(14.0)
        .child(activity(s))
        .child(today(s))
        .child(agents);
    col().key("grid").grow(1.0).min_w(0.0).h_full().min_h(0.0)
        .child(col().w_full().pt(2.0).px(2.0).pb(18.0).child(body))
        .scroll(ScrollSpec { stick_bottom: false })
}

fn card(key: &str, name: &str) -> El {
    // Hovering a card lifts its wash and lights a scan line along its top edge.
    let scan = el().key("scan").h(1.0).group_opacity(0.0, 1.0)
        .linear_gradient(std::f32::consts::FRAC_PI_2, [(0.0, rune::Color::TRANSPARENT), (0.5, cyan()), (1.0, rune::Color::TRANSPARENT)])
        .pin(Some(0.0), Some(0.0), Some(0.0), None);
    col().key(key.to_string()).role("group").label(name.to_string()).fill(cyan_tint("06")).border(1.0, border())
        .py(12.0).px(14.0).gap(8.0).min_w(0.0)
        .hover_group().hover(cyan_tint("06"))
        .child(scan)
}

fn title(icon: Option<&str>, name: &str, badge: Option<String>) -> El {
    let mut t = row().key("title").role("heading").label(name.to_string()).w_full().center_y().gap(8.0);
    if let Some(i) = icon {
        t = t.child(text(i.to_string()).font(mono(12.0, 400.0, 0.0)).color(cyan()));
    }
    t = t.child(text(name.to_uppercase()).font(mono(10.0, 500.0, 2.0)).color(cyan())).child(el().grow(1.0));
    if let Some(b) = badge {
        t = t.child(text(b).key("badge").font(mono(10.0, 400.0, 0.5)).color(cyan_dim_text()));
    }
    t
}

fn empty(line: &str) -> El {
    text(line.to_string()).key("empty").font(mono(11.0, 400.0, 0.0).lh(11.0 * 1.5)).color(cyan_dim_text()).wrap().w_full()
}

/// A small text button for card headers.
fn chip(key: &str, label: &str, busy: bool) -> El {
    let c = text(label.to_string()).key(key.to_string()).role("button").focusable(true)
        .font(mono(9.0, 500.0, 1.5)).color(cyan()).px(7.0).py(3.0).border(1.0, border());
    if busy { c.disabled(true).opacity(0.45) } else { c.hover(cyan_dim()).press_scale(0.95).cursor(rune::Cursor::Pointer) }
}

/// A compact CPU/RAM gauge for the top bar.
pub fn meter(name: &str, value: Option<f32>, high_at: f32, detail: String, with_bar: bool) -> El {
    let v = value.unwrap_or(0.0);
    let high = value.is_some_and(|v| v > high_at);
    let ink = if high { red() } else { cyan() };
    let label = value.map_or("--%".to_string(), |v| format!("{v:.0}%"));
    let fill = glow(
        el().key("fill").h_full().radius(2.0).fill(ink).w_frac(v.clamp(0.0, 100.0) / 100.0).motion(rune::Spring::new(0.6, 0.0)),
        ink,
        5.0,
    );
    // Over the limit, the bar throbs so it catches the eye.
    let fill = if high { fill.looping(rune::LoopSpec::opacity(1.0, 0.0, 0.55, 1.0)) } else { fill };
    let bar = row().key("bar").w(46.0).h(4.0).radius(2.0).fill(cyan_tint("15")).border(1.0, cyan_tint("22")).clip_rounded(2.0)
        .child(fill);
    let mut m = row().key(format!("stat-{}", name.to_lowercase())).role("meter").label(name.to_string())
        .range_value(f64::from(v), 0.0, 100.0).center_y().gap(6.0).help(detail)
        .child(text(name.to_string()).font(mono(9.0, 400.0, 1.0)).color(cyan_dim_text()));
    if with_bar {
        m = m.child(bar);
    }
    m
        .child(row().key("value").w(30.0).justify_end()
            .child(rolling(&format!("{}-roll", name.to_lowercase()), label, mono(9.5, if high { 500.0 } else { 400.0 }, 0.5), ink, value.map(f64::from))))
}

fn today(s: &State) -> El {
    let mut list = col().key("today-list").role("list").w_full();
    if s.today.is_empty() {
        // /today can't tell "no events" from "calendar not connected", so say both.
        list = list.child(empty("Nothing on the calendar. If that's wrong, the Google sign-in may have expired."));
    }
    for (i, thing) in s.today.iter().enumerate() {
        list = list.child(
            row().key(format!("thing-{i}")).role("listitem").w_full().h(11.0 * 1.8).center_y().px(4.0).radius(2.0)
                .hover(cyan_tint("10"))
                .transition(rune::Transition::offset(-6.0, 0.0).combined(rune::Transition::opacity()))
                .child(text(thing.time.clone()).font(mono(11.0, 400.0, 0.0)).color(cyan()).min_w(52.0))
                .child(text(thing.title.clone()).font(mono(11.0, 400.0, 0.0)).color(bright()).truncate().shrink()),
        );
    }
    let count = (!s.today.is_empty()).then(|| format!("{} TODAY", s.today.len()));
    let ask = chip("today-ask", "ASK JARVIS →", s.busy).label("Ask Jarvis about today").help(TODAY_PROMPT)
        .on_press_tx(|s: &mut State, tx: &mut Tx| chat::send(s, tx, TODAY_PROMPT.to_string()));
    let c = card("card-calendar", "Today's Things").w_full()
        .child(title(Some("▤"), "Today's Things", count).child(ask))
        .child(list);
    // Calendar has no tile: while the Calendar agent works, this card is the one that lights up.
    if s.busy && s.working_agent.as_deref() == Some("Calendar") {
        glow(c.border(1.0, cyan()).fill(cyan_tint("10")), cyan_tint("55"), 16.0)
            .looping(rune::LoopSpec::opacity(1.4, 0.0, 0.75, 1.0))
    } else {
        c
    }
}

/// One agent: click anywhere to send its preset prompt. Shows its last reply on one line,
/// or what it does if it hasn't answered yet.
fn tile(s: &State, (icon, name, agent, key, _line, button, prompt): (&str, &str, &str, &'static str, &str, &str, &'static str)) -> El {
    let latest = s.activity.latest(agent);
    let fresh = latest.is_some_and(|e| chrono::Utc::now().timestamp_millis() - e.timestamp < 60_000);
    let corner = match latest {
        Some(e) => text(time_ago(e.timestamp)).key("badge").font(mono(8.5, 400.0, 0.5)).color(cyan_dim_text()),
        None => text("→").key("arrow").font(mono(10.0, 500.0, 0.0)).color(cyan()).group_opacity(0.0, 1.0),
    };
    let line = match latest {
        Some(e) => text(e.summary.clone()).font(mono(10.0, 400.0, 0.0)).color(bright()),
        None => text(format!("› {button}")).font(mono(10.0, 400.0, 0.5)).color(cyan_dim_text()).group_color(cyan()),
    }.truncate().w_full();
    // The Weather tile shows live conditions instead of its last reply once they've loaded.
    let live = (agent == "Weather").then_some(s.weather.as_ref()).flatten();
    let (corner, line, label, help) = match live {
        Some(w) => {
            let (glyph, words) = w.describe();
            let now = row().key("weather-now").w_full().center_y().gap(6.0)
                .child(text(glyph).font(mono(12.0, 400.0, 0.0)).color(cyan()))
                .child(rolling("weather-temp", format!("{:.0}°", w.temp), mono(13.0, 500.0, 0.5), bright(), Some(f64::from(w.temp.round()))))
                .child(text(words).font(mono(9.5, 400.0, 0.3)).color(cyan_dim_text()).truncate().shrink());
            let place = text(format!("H{:.0}° L{:.0}°", w.high, w.low)).key("badge").font(mono(8.5, 400.0, 0.5)).color(cyan_dim_text());
            let summary = format!("{} {:.0}°, {words}", w.place, w.temp);
            let detail = format!(
                "{}: {:.0}°, feels like {:.0}° · humidity {:.0}% · wind {:.0} km/h — click to ask Jarvis",
                w.place, w.temp, w.feels, w.humidity, w.wind
            );
            (place, now, format!("Weather: {summary}"), detail)
        }
        None => (corner, line, format!("{name}: {button}"), prompt.to_string()),
    };
    let t = col().key(key).role("button").label(label).focusable(true)
        .h(64.0).py(10.0).px(12.0).gap(7.0).min_w(0.0)
        .fill(cyan_tint("06")).border(1.0, if fresh { cyan_tint("99") } else { border() })
        .help(help)
        .child(row().w_full().center_y().gap(8.0)
            .child(text(icon.to_string()).font(mono(12.0, 400.0, 0.0)).color(cyan()))
            .child(text(name.to_uppercase()).font(mono(10.0, 500.0, 1.5)).color(cyan()))
            .child(el().grow(1.0))
            .child(corner))
        .child(line);
    // The agent the backend routed the request to lights up and pulses while it works.
    let working = s.busy && s.working_agent.as_deref() == Some(agent);
    if working {
        return glow(
            t.disabled(true).border(1.0, cyan()).fill(cyan_tint("14"))
                .child(row().key("working").gap(6.0).center_y().pin(None, None, Some(10.0), Some(8.0))
                    .child(crate::view::pulse_dots(cyan()))
                    .child(text("WORKING").font(mono(8.0, 500.0, 1.5)).color(cyan()))),
            cyan_tint("55"),
            16.0,
        )
        .looping(rune::LoopSpec::opacity(1.4, 0.0, 0.75, 1.0));
    }
    let t = if s.busy {
        t.disabled(true).opacity(0.5)
    } else {
        t.hover(cyan_tint("10")).hover_group().press_scale(0.97).cursor(rune::Cursor::Pointer)
            .on_press_tx(move |s: &mut State, tx: &mut Tx| chat::send(s, tx, prompt.to_string()))
    };
    // A tile that just answered keeps a brighter frame for a minute.
    if fresh { glow(t, cyan_tint("33"), 12.0) } else { t }
}

/// Recent Activity, at the top: one line per reply; click a line to read the whole reply.
fn activity(s: &State) -> El {
    let total = s.activity.entries.len();
    let limit = if s.activity_all { 10 } else { 3 };
    let mut list = col().key("activity-list").role("list").w_full();
    if total == 0 {
        list = list.child(empty("No activity yet. Click an agent below to start."));
    }
    for (i, e) in s.activity.entries.iter().take(limit).enumerate() {
        let id = e.timestamp;
        let open = s.open_activity == Some(id);
        let line = row().key(format!("activity-{i}")).role("button").label(format!("{} reply", e.agent)).focusable(true)
            .w_full().h(26.0).gap(10.0).center_y().px(4.0).radius(2.0)
            .fill(if open { cyan_tint("0c") } else { rune::Color::TRANSPARENT })
            .hover(cyan_tint("0c")).cursor(rune::Cursor::Pointer)
            .transition(rune::Transition::offset(0.0, -6.0).combined(rune::Transition::opacity()))
            .child(text(e.agent.to_uppercase()).font(mono(9.5, 500.0, 1.0)).color(cyan()).w(84.0))
            .child(text(e.summary.clone()).font(mono(10.5, 400.0, 0.0)).color(summary_text()).truncate().grow(1.0).shrink())
            .child(text(time_ago(e.timestamp)).font(mono(9.0, 400.0, 0.0)).color(cyan_dim_text()))
            .child(text(if open { "▴" } else { "▾" }).font(mono(9.0, 400.0, 0.0)).color(cyan_dim_text()))
            .on_press(move |s: &mut State| s.open_activity = if s.open_activity == Some(id) { None } else { Some(id) });
        list = list.child(line);
        if open {
            let full = if e.full.is_empty() { e.summary.as_str() } else { e.full.as_str() };
            list = list.child(
                col().key(format!("activity-full-{i}")).w_full().py(8.0).pl(98.0).pr(8.0)
                    .border_sides([0.0, 0.0, 1.0, 0.0], cyan_tint("10"))
                    .transition(rune::Transition::opacity())
                    .child(rich(full, &reply_style().body_font(mono(11.0, 400.0, 0.0).lh(11.0 * 1.55)))),
            );
        }
    }
    let mut header = title(Some("◷"), "Recent Activity", (total > 0).then(|| format!("{total}")));
    if total > 3 {
        header = header.child(chip("activity-more", if s.activity_all { "LESS" } else { "SHOW ALL" }, false)
            .on_press(|s: &mut State| s.activity_all = !s.activity_all));
    }
    card("card-activity", "Recent Activity").w_full().gap(6.0).child(header).child(list)
}

/// `.message.jarvis .text` in the HUD: Inter 13/1.75 in #ccd8ff, cyan links and markers.
fn reply_style() -> MarkdownStyle {
    MarkdownStyle::neutral(true)
        .body_font(REPLY)
        .text(bright())
        .muted(cyan_dim_text())
        .link(cyan())
        .table(border(), cyan_tint("12"))
        .table_header_text(cyan())
        .table_rules(cyan_tint("18"))
        .inline_code_bg(cyan_tint("15"))
        .code_block(bg(), border())
        .rule(border())
}

/// A reply: Markdown with inline maths turned into Unicode, and display maths as framed blocks.
pub fn rich(src: &str, style: &MarkdownStyle) -> El {
    let segs = crate::latex::split(src);
    if let [crate::latex::Seg::Markdown(md)] = segs.as_slice() {
        return Markdown::new(md).render(style);
    }
    let mut c = col().key("rich").w_full().gap(6.0);
    for (i, seg) in segs.into_iter().enumerate() {
        c = c.child(match seg {
            crate::latex::Seg::Markdown(md) => col().key(format!("md-{i}")).w_full().child(Markdown::new(&md).render(style)),
            crate::latex::Seg::Display(math) => row().key(format!("math-{i}")).role("math").label(math.clone())
                .w_full().justify_center().py(10.0).px(12.0).my(2.0)
                .fill(cyan_tint("08")).border_sides([0.0, 0.0, 0.0, 2.0], cyan_tint("88"))
                .child(text(math).font(rune::tok::TextStyle::new(16.0, 400.0).lh(16.0 * 1.6)).color(bright()).wrap().align(Align::Center)),
        });
    }
    c
}

fn message(s: &State, m: &crate::state::Message) -> El {
    let jarvis = m.from == Who::Jarvis;
    let ink = if jarvis { cyan() } else { red() };
    let label = text(if jarvis { "JARVIS" } else { "YOU" }).key("label").font(mono(9.0, 500.0, 1.5)).color(ink)
        .w(48.0).align(Align::End).pt(4.0);
    let body = if !jarvis {
        text(m.text.clone()).font(mono(12.0, 400.0, 0.0).lh(12.0 * 1.6)).color(user_text()).wrap()
    } else if m.typing {
        // The in-flight reply: each step the backend reports, done ones ticked, the current
        // one pulsing — instead of three dots for 10–20 s.
        let mut steps = col().key("steps").role("list").label("Progress").gap(4.0).py(2.0);
        let n = s.steps.len();
        for (i, st) in s.steps.iter().enumerate() {
            let current = i + 1 == n;
            let mark = if current { crate::view::pulse_dots(cyan()) } else { text("✓").font(mono(9.0, 400.0, 0.0)).color(cyan_dim_text()) };
            steps = steps.child(
                row().key(format!("step-{i}")).role("listitem").gap(8.0).center_y()
                    .transition(rune::Transition::offset(0.0, 4.0).combined(rune::Transition::opacity()))
                    .child(row().w(18.0).justify_center().child(mark))
                    .child(text(st.clone()).font(mono(10.0, 400.0, 0.5)).color(if current { cyan() } else { cyan_dim_text() })),
            );
        }
        let secs = s.started.map_or(0.0, |t| t.elapsed().as_secs_f32());
        steps.child(text(format!("{secs:.0} s")).key("step-time").font(mono(9.0, 400.0, 0.5)).color(cyan_dim_text()).pl(26.0))
    } else {
        let mut body = col().key("reply-body").w_full().gap(6.0).child(rich(&m.text, &reply_style()));
        if let Some(meta) = s.meta.get(&m.id) {
            body = body.child(text(meta.to_uppercase()).key("meta").font(mono(8.5, 400.0, 1.0)).color(cyan_dim_text())
                .transition(rune::Transition::opacity()));
        }
        body
    };
    let mut line = row().key(format!("msg-{}", m.id)).role("listitem").label(if jarvis { "Jarvis" } else { "You" })
        .w_full().gap(10.0).py(10.0).items_start().hover_group()
        .border_sides([0.0, 0.0, 1.0, 0.0], cyan_tint("08"))
        .transition(rune::Transition::offset(0.0, 8.0).combined(rune::Transition::opacity()))
        .child(label)
        .child(col().key("text").grow(1.0).shrink().min_w(0.0).max_w(580.0).child(body));
    if jarvis && !m.typing && !m.text.is_empty() {
        // COPY shows on hover; after a press it says COPIED for a moment.
        let copied = s.copied.is_some_and(|(id, _)| id == m.id);
        let id = m.id;
        let copy = row().key("copy").role("button").label("Copy reply").focusable(true)
            .px(6.0).py(2.0).border(1.0, if copied { cyan() } else { border() })
            .hover(cyan_dim()).press_scale(0.94).cursor(rune::Cursor::Pointer)
            .group_opacity(if copied { 1.0 } else { 0.0 }, 1.0)
            .child(text(if copied { "COPIED ✓" } else { "COPY" }).font(mono(9.0, 500.0, 1.5)).color(cyan()))
            .on_press_tx(move |s: &mut State, tx: &mut Tx| chat::copy_reply(s, tx, id));
        line = line.child(copy);
    }
    line
}

/// The message list the chat panel shows; it fills the panel and follows new messages.
pub fn messages(s: &State) -> El {
    let mut log = col().key("messages").role("log").label("Conversation").w_full().py(8.0);
    if s.messages.is_empty() {
        log = log.child(text("Conversation cleared. Type a command below.").key("cleared")
            .font(mono(11.0, 400.0, 1.0)).color(cyan_dim_text()).pt(8.0).transition(rune::Transition::opacity()));
    }
    for m in &s.messages {
        log = log.child(message(s, m));
    }
    col().key("messages-scroll").w_full().grow(1.0).min_h(0.0).child(log).scroll(ScrollSpec { stick_bottom: true })
}
