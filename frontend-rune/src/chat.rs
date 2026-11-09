//! Chat behaviour, ported from `sendMessage` and friends in `frontend/src/main.ts`.

use std::sync::atomic::Ordering;
use std::time::Instant;

use rune::{FileDialogOptions, Tx};

use crate::net::{self, ChatEvent};
use crate::state::{State, Who};

pub fn submit(s: &mut State, tx: &mut Tx) {
    let message = s.input.text.trim().to_string();
    if message.is_empty() || s.busy {
        return;
    }
    s.input.clear();
    send(s, tx, message);
}

/// Pushes the user turn, opens the in-flight reply and starts the stream.
pub fn send(s: &mut State, tx: &mut Tx, message: String) {
    if s.busy {
        return;
    }
    s.history.push(("user".into(), message.clone()));
    if s.sent.last() != Some(&message) {
        s.sent.push(message.clone());
    }
    s.recall = None;
    s.push(Who::User, message, false);
    s.reply_id = Some(s.push(Who::Jarvis, "", true));
    s.busy = true;
    s.status = "PROCESSING...".into();
    s.banner = None;
    s.reply = String::new();
    s.reply_agent = "General".into();
    s.working_agent = None;
    s.steps = vec!["Sent".into()];
    s.started = Some(Instant::now());
    s.first_text = None;
    tx.scroll_to_bottom("messages-scroll");
    let generation = s.chat_gen.fetch_add(1, Ordering::SeqCst) + 1;
    if let Some(wake) = s.waker.clone() {
        net::start_chat(s.history.clone(), s.session_id.clone(), s.tx.clone(), wake, generation, s.chat_gen.clone());
    }
}

fn elapsed(s: &State) -> f32 {
    s.started.map_or(0.0, |t| t.elapsed().as_secs_f32())
}

fn step(s: &mut State, text: String) {
    if s.steps.last() != Some(&text) {
        s.steps.push(text);
    }
}

/// The backend named the agent: light its tile and say so in the steps, once.
fn routed(s: &mut State, agent: Option<String>) {
    if let Some(a) = agent {
        if s.working_agent.as_deref() != Some(a.as_str()) {
            step(s, format!("→ {a} agent"));
            s.working_agent = Some(a.clone());
        }
        s.reply_agent = a;
    }
}

/// STOP (or Esc): drop the stream, keep what arrived, and roll back the turn as a failure does.
pub fn stop(s: &mut State) {
    if !s.busy {
        return;
    }
    s.chat_gen.fetch_add(1, Ordering::SeqCst);
    let took = elapsed(s);
    if let Some(id) = s.reply_id {
        s.meta.insert(id, format!("stopped after {took:.1} s"));
    }
    if let Some(m) = reply_msg(s) {
        m.typing = false;
        if m.text.is_empty() || m.text.starts_with("Using ") {
            m.text = "Stopped.".into();
        }
    }
    s.history.pop();
    s.reply_id = None;
    s.working_agent = None;
    s.steps.clear();
    s.busy = false;
    s.status = "SYSTEM ONLINE".into();
}

fn reply_msg(s: &mut State) -> Option<&mut crate::state::Message> {
    let id = s.reply_id?;
    s.messages.iter_mut().find(|m| m.id == id)
}

pub fn apply(s: &mut State, generation: u64, ev: ChatEvent) {
    // Events from a stopped or older request are dropped.
    if generation != s.chat_gen.load(Ordering::SeqCst) || !s.busy {
        return;
    }
    match ev {
        ChatEvent::Status(text) => {
            s.status = text.to_uppercase();
            step(s, text);
        }
        ChatEvent::Tool { content, agent } => {
            routed(s, agent);
            step(s, content.clone());
            if let Some(m) = reply_msg(s) { m.text = content; }
        }
        ChatEvent::Text { content, agent } => {
            // Cumulative: the full reply so far replaces the body, never appends.
            routed(s, agent);
            if s.first_text.is_none() {
                s.first_text = Some(elapsed(s));
            }
            s.reply = content.clone();
            if let Some(m) = reply_msg(s) {
                m.text = content;
                m.typing = false;
            }
        }
        ChatEvent::Done { agent } => {
            routed(s, agent);
            let reply = std::mem::take(&mut s.reply);
            s.history.push(("assistant".into(), reply.clone()));
            s.conversations.save(&s.session_id, &s.history);
            let agent = s.reply_agent.clone();
            s.activity.record(&agent, &reply);
            // Measured, not estimated: time to the first text, and to the end.
            let total = elapsed(s);
            let meta = match s.first_text {
                Some(first) if total - first > 0.5 => format!("{agent} agent · first text {first:.1} s · done {total:.1} s"),
                _ => format!("{agent} agent · {total:.1} s"),
            };
            if let Some(id) = s.reply_id {
                s.meta.insert(id, meta);
            }
            if let Some(m) = reply_msg(s) { m.typing = false; }
            // Asked and looked away (⌘⇧J): say the answer is in.
            if !rune_notify::app_focused() && !reply.is_empty() {
                let n = rune_notify::Notification::new(format!("reply-{}", s.reply_id.unwrap_or(0)), format!("Jarvis · {agent}"))
                    .body(crate::activity::summarize(&reply));
                let _ = rune_notify::post(&n);
            }
            s.reply_id = None;
            s.working_agent = None;
            s.steps.clear();
            s.status = "SYSTEM ONLINE".into();
            s.busy = false;
        }
        ChatEvent::Failed => {
            if let Some(m) = reply_msg(s) {
                m.typing = false;
                m.text = "Connection failed. Is the backend running?".into();
            }
            s.reply_id = None;
            s.working_agent = None;
            s.steps.clear();
            s.status = "BACKEND OFFLINE".into();
            s.banner = Some("Can't reach the backend — is it running?".into());
            // Roll back the user's turn, as the Tauri HUD does.
            s.history.pop();
            s.busy = false;
        }
    }
}

/// ↑ / ↓ in the input walks back and forward through prompts sent this session, like a shell.
pub fn recall(s: &mut State, older: bool) -> bool {
    if s.sent.is_empty() {
        return false;
    }
    let last = s.sent.len() - 1;
    let next = match (s.recall, older) {
        (None, true) => Some(last),
        (None, false) => return false,
        (Some(i), true) => Some(i.saturating_sub(1)),
        (Some(i), false) if i < last => Some(i + 1),
        (Some(_), false) => None,
    };
    s.recall = next;
    s.input.replace_text(next.map_or(String::new(), |i| s.sent[i].clone()));
    true
}

pub fn copy_reply(s: &mut State, tx: &mut Tx, id: u64) {
    if let Some(m) = s.messages.iter().find(|m| m.id == id) {
        tx.copy(m.text.clone());
        s.copied = Some((id, std::time::Instant::now()));
        tx.wake_after(std::time::Duration::from_millis(1600));
    }
}

pub fn toggle_mic(s: &mut State) {
    s.mic_on = !s.mic_on;
    s.status = if s.mic_on { "VOICE NOT PORTED — MIC STATE ONLY".into() } else { "SYSTEM ONLINE".into() };
}

pub fn import_file(tx: &mut Tx) {
    let options = FileDialogOptions { title: "Import a file for Jarvis to check".into(), ..Default::default() };
    tx.open_file(options, |s: &mut State, result, tx| match result {
        Ok(Some(path)) => {
            send(s, tx, format!("Please check this file: {}", path.display()));
        }
        Ok(None) => {}
        Err(_) => s.status = "IMPORT UNAVAILABLE".into(),
    });
}
