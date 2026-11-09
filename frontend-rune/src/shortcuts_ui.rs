//! The Shortcuts block in the sidebar and the pop-up that rebinds them.

use rune::{El, KeyEvent, Tx, col, el, row, text};

use crate::keymap::{self, ACTIONS, Action, Keymap};
use crate::state::State;
use crate::style::*;
use crate::view::{button, pulse_dots};

fn kbd(label: &str, live: bool) -> El {
    row().px(4.0).py(1.0).radius(2.0).border(1.0, if live { cyan() } else { border() }).fill(cyan_tint(if live { "22" } else { "0a" }))
        .child(text(label.to_string()).font(mono(9.0, 400.0, 0.5)).color(cyan()))
}

/// Sidebar block between the nav list and TEST CALL, ruled above and below like the footer.
pub fn sidebar_section(s: &State) -> El {
    // Compact keycaps (⌃⇧K, ⎋) so a long chord still fits the 190 pt sidebar.
    let cap = |spec: &str| rune::Chord::parse(spec).map_or_else(|_| keymap::display(spec), |c| c.label());
    let cell = |name: &str, spec: &str| row().key(format!("sc-{}", name.to_lowercase())).gap(5.0).center_y().min_w(0.0).w(76.0)
        .child(kbd(&cap(spec), false))
        .child(text(name.to_string()).font(mono(9.0, 400.0, 0.5)).color(cyan_dim_text()));
    let k = &s.keymap;
    let grid = col().gap(5.0).w_full()
        .child(row().w_full().justify_between().child(cell("Send", "enter")).child(cell("Mic", &k.mic)))
        .child(row().w_full().justify_between().child(cell("Clear", &k.clear)).child(cell("Cancel", &k.cancel)));
    let header = row().w_full().center_y().gap(8.0)
        .child(text("⌨").font(mono(11.0, 400.0, 0.0)).color(cyan_dim_text()).group_color(cyan()))
        .child(text("SHORTCUTS").font(mono(10.0, 500.0, 2.0)).color(cyan_dim_text()).group_color(cyan()))
        .child(el().grow(1.0))
        .child(text("EDIT ✎").font(mono(9.0, 500.0, 1.0)).color(cyan()).group_opacity(0.0, 1.0));
    col().key("sidebar-shortcuts").role("button").label("Edit shortcuts").focusable(true)
        .w_full().gap(8.0).py(10.0).px(6.0).mb(12.0)
        .border_sides([1.0, 0.0, 1.0, 0.0], border())
        .hover(cyan_tint("0a")).hover_group().press_scale(0.98).cursor(rune::Cursor::Pointer)
        .help("Change your keyboard shortcuts")
        .child(header).child(grid)
        .on_press(|s: &mut State| {
            s.shortcuts_open = true;
            s.capturing = None;
            s.shortcut_msg = None;
        })
}

fn close(s: &mut State) {
    s.shortcuts_open = false;
    s.capturing = None;
    s.shortcut_msg = None;
}

fn editable_row(s: &State, action: Action, name: &str, what: &str) -> El {
    let live = s.capturing == Some(action);
    let binding = if live {
        row().key("capturing").gap(8.0).center_y()
            .child(pulse_dots(cyan()))
            .child(text("PRESS NEW KEYS").font(mono(9.0, 500.0, 1.5)).color(cyan())
                .looping(rune::LoopSpec::opacity(1.2, 0.0, 0.5, 1.0)))
    } else {
        kbd(&keymap::display(s.keymap.get(action)), false)
    };
    let change = if live {
        button(&format!("{name}-stop"), "STOP", false, cyan_dim_text()).h(24.0).px(8.0)
            .on_press(|s: &mut State| { s.capturing = None; s.shortcut_msg = None; })
    } else {
        button(&format!("{name}-change"), "CHANGE", false, cyan()).h(24.0).px(8.0)
            .on_press(move |s: &mut State| { s.capturing = Some(action); s.shortcut_msg = None; })
    };
    row().key(format!("row-{}", name.to_lowercase())).role("listitem").w_full().py(8.0).gap(10.0).center_y()
        .border_sides([0.0, 0.0, 1.0, 0.0], cyan_tint("10"))
        .fill(if live { cyan_tint("0c") } else { rune::Color::TRANSPARENT })
        .child(col().grow(1.0).min_w(0.0).gap(2.0)
            .child(text(name.to_uppercase()).font(mono(10.0, 500.0, 1.5)).color(cyan()))
            .child(text(what.to_string()).font(mono(9.5, 400.0, 0.0)).color(cyan_dim_text())))
        .child(binding)
        .child(change)
}

fn fixed_row(name: &str, what: &str, keys: &str) -> El {
    row().key(format!("row-{}", name.to_lowercase())).role("listitem").w_full().py(8.0).gap(10.0).center_y().opacity(0.75)
        .border_sides([0.0, 0.0, 1.0, 0.0], cyan_tint("10"))
        .child(col().grow(1.0).min_w(0.0).gap(2.0)
            .child(text(name.to_uppercase()).font(mono(10.0, 500.0, 1.5)).color(cyan_dim_text()))
            .child(text(what.to_string()).font(mono(9.5, 400.0, 0.0)).color(cyan_dim_text())))
        .child(kbd(keys, false))
        .child(text("FIXED").font(mono(8.5, 500.0, 1.5)).color(cyan_dim_text()).w(52.0))
}

/// The pop-up: rebinding rows, the fixed ones for reference, a message line, reset and done.
pub fn editor(s: &State) -> El {
    let mut list = col().key("shortcut-list").role("list").w_full();
    for (action, name, what) in ACTIONS {
        list = list.child(editable_row(s, action, name, what));
    }
    list = list
        .child(fixed_row("Send", "Send the command", "ENTER"))
        .child(fixed_row("Show / hide", "Summon the HUD from anywhere", "⌘+SHIFT+J"));

    let msg = match &s.shortcut_msg {
        Some((m, err)) => text(m.clone()).key("shortcut-msg").role("status").font(mono(9.5, 400.0, 0.5))
            .color(if *err { red() } else { cyan() }).wrap().w_full().transition(rune::Transition::opacity()),
        None => text(if s.capturing.is_some() { "Esc closes without changing anything." } else { "Changes save automatically." })
            .key("shortcut-msg").font(mono(9.5, 400.0, 0.5)).color(cyan_dim_text()),
    };
    let reset = button("shortcuts-reset", "RESET", false, cyan_dim_text()).on_press(|s: &mut State| {
        s.keymap = Keymap::default();
        s.keymap.save();
        s.capturing = None;
        s.shortcut_msg = Some(("Back to the defaults.".into(), false));
    });
    let done = button("shortcuts-done", "DONE", true, cyan()).on_press(close);
    let x = text("✕").key("shortcuts-x").role("button").label("Close").focusable(true)
        .font(mono(12.0, 400.0, 0.0)).color(cyan_dim_text()).px(6.0).hover(cyan_tint("15")).cursor(rune::Cursor::Pointer)
        .on_press(close);

    let dialog = col().key("shortcuts-dialog").role("dialog").label("Shortcuts").w(420.0).gap(12.0).padding(20.0)
        .fill(surface()).border(1.0, cyan()).shadow(0.0, 40.0, cyan_tint("33"))
        .transition(rune::Transition::scale(0.96).combined(rune::Transition::opacity()))
        .child(row().w_full().center_y().gap(8.0)
            .child(text("⌨").font(mono(13.0, 400.0, 0.0)).color(cyan()))
            .child(text("SHORTCUTS").font(mono(12.0, 500.0, 3.0)).color(cyan()))
            .child(el().grow(1.0)).child(x))
        .child(list)
        .child(msg)
        .child(row().w_full().gap(10.0).justify_end().child(reset).child(done))
        .modal(true, close);
    el().key("shortcuts-scrim").pin(Some(0.0), Some(0.0), Some(0.0), Some(0.0)).fill(rune::Color::BLACK.alpha(0.6))
        .transition(rune::Transition::opacity())
        .center().child(dialog)
}

/// While a row waits for keys, every key press goes here first.
pub fn capture(s: &mut State, action: Action, ev: &KeyEvent, tx: &Tx) {
    match keymap::chord_from_event(ev, tx) {
        Ok(spec) => match s.keymap.set(action, spec.clone()) {
            Ok(()) => {
                s.keymap.save();
                s.capturing = None;
                let name = ACTIONS.iter().find(|a| a.0 == action).map_or("", |a| a.1);
                s.shortcut_msg = Some((format!("{name} is now {}.", keymap::display(&spec)), false));
            }
            Err(e) => s.shortcut_msg = Some((e, true)),
        },
        Err(e) => s.shortcut_msg = Some((e, true)),
    }
}
