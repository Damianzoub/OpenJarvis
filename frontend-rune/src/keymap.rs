//! Editable keyboard shortcuts: stored as chord strings ("ctrl+m"), matched with `rune::Chord`,
//! saved to a JSON file so they survive restarts.

use std::path::PathBuf;

use rune::{Chord, Key, KeyEvent, Tx};
use serde::{Deserialize, Serialize};

#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub enum Action { Mic, Clear, Cancel }

/// (action, name, what it does)
pub const ACTIONS: [(Action, &str, &str); 3] = [
    (Action::Mic, "Mic", "Toggle the mic"),
    (Action::Clear, "Clear", "Clear the conversation"),
    (Action::Cancel, "Cancel", "Close a pop-up or stop the mic"),
];

#[derive(Clone, PartialEq, Debug, Serialize, Deserialize)]
pub struct Keymap {
    pub mic: String,
    pub clear: String,
    pub cancel: String,
}

impl Default for Keymap {
    fn default() -> Self {
        Keymap { mic: "ctrl+m".into(), clear: "ctrl+l".into(), cancel: "escape".into() }
    }
}

fn store_path() -> Option<PathBuf> {
    if let Ok(p) = std::env::var("JARVIS_SHORTCUTS_FILE") {
        return Some(PathBuf::from(p));
    }
    dirs::data_dir().map(|d| d.join("OpenJarvis").join("shortcuts.json"))
}

impl Keymap {
    pub fn load() -> Keymap {
        store_path()
            .and_then(|p| std::fs::read_to_string(p).ok())
            .and_then(|raw| serde_json::from_str::<Keymap>(&raw).ok())
            .filter(|k| [&k.mic, &k.clear, &k.cancel].iter().all(|c| Chord::parse(c).is_ok()))
            .unwrap_or_default()
    }

    pub fn save(&self) {
        let Some(path) = store_path() else { return };
        if let Some(dir) = path.parent() {
            let _ = std::fs::create_dir_all(dir);
        }
        if let Ok(json) = serde_json::to_string_pretty(self) {
            let _ = std::fs::write(path, json);
        }
    }

    pub fn get(&self, a: Action) -> &str {
        match a { Action::Mic => &self.mic, Action::Clear => &self.clear, Action::Cancel => &self.cancel }
    }

    fn slot(&mut self, a: Action) -> &mut String {
        match a { Action::Mic => &mut self.mic, Action::Clear => &mut self.clear, Action::Cancel => &mut self.cancel }
    }

    pub fn matches(&self, a: Action, ev: &KeyEvent, tx: &Tx) -> bool {
        Chord::parse(self.get(a)).is_ok_and(|c| c.matches_tx(ev, tx))
    }

    /// Binds `chord` to `a`, or says why not (clash with another action).
    pub fn set(&mut self, a: Action, chord: String) -> Result<(), String> {
        if let Some((_, name, _)) = ACTIONS.iter().find(|(other, ..)| *other != a && self.get(*other) == chord) {
            return Err(format!("{} is already used by {name}", display(&chord)));
        }
        *self.slot(a) = chord;
        Ok(())
    }
}

/// "ctrl+shift+m" → "CTRL+SHIFT+M", "escape" → "ESC".
pub fn display(spec: &str) -> String {
    spec.split('+')
        .map(|p| match p {
            "escape" => "ESC".to_string(),
            "cmd" => "⌘".to_string(),
            "alt" => "OPT".to_string(),
            "space" => "SPACE".to_string(),
            "comma" => ",".to_string(),
            "plus" => "+".to_string(),
            other => other.to_uppercase(),
        })
        .collect::<Vec<_>>()
        .join("+")
}

/// Turns a key press into a chord string, or explains why it can't be a shortcut.
pub fn chord_from_event(ev: &KeyEvent, tx: &Tx) -> Result<String, String> {
    let named = |k: &Key| -> Option<&'static str> {
        Some(match k {
            Key::Escape => "escape",
            Key::Enter => "enter",
            Key::Up => "up",
            Key::Down => "down",
            Key::Left => "left",
            Key::Right => "right",
            Key::Home => "home",
            Key::End => "end",
            Key::PageUp => "pageup",
            Key::PageDown => "pagedown",
            Key::Delete => "delete",
            Key::Backspace => "backspace",
            _ => return None,
        })
    };
    let key = match &ev.key {
        Key::Function(n) => format!("f{n}"),
        Key::Tab => return Err("Tab moves focus, so it can't be a shortcut".into()),
        Key::Modifier { .. } => return Err("Press a key together with the modifiers".into()),
        k => match named(k) {
            Some(n) => n.to_string(),
            None => {
                let c = tx.key_base().or(match k {
                    Key::Command(c) => Some(*c),
                    Key::Text(t) => t.chars().next(),
                    _ => None,
                });
                match c.map(|c| c.to_ascii_lowercase()) {
                    Some(' ') => "space".into(),
                    Some('+') => "plus".into(),
                    Some(',') => "comma".into(),
                    Some(c) => c.to_string(),
                    None => return Err("That key can't be used".into()),
                }
            }
        },
    };
    let m = ev.mods;
    let cmd = cfg!(target_os = "macos") && (m.logo || (m.cmd && !m.ctrl));
    let has_modifier = m.ctrl || m.alt || cmd;
    let standalone = matches!(ev.key, Key::Function(_) | Key::Escape);
    if !has_modifier && !standalone {
        return Err("Add Ctrl, Option or ⌘ — a bare key would get typed instead".into());
    }
    let mut parts: Vec<&str> = Vec::new();
    if m.ctrl { parts.push("ctrl"); }
    if m.alt { parts.push("alt"); }
    if m.shift { parts.push("shift"); }
    if cmd { parts.push("cmd"); }
    let spec = format!("{}{}{key}", parts.join("+"), if parts.is_empty() { "" } else { "+" });
    if cmd && matches!(key.as_str(), "q" | "w" | "h" | "c" | "v" | "x" | "a" | "z" | "m" | "l") {
        return Err(format!("{} is taken by macOS or the Jarvis menu", display(&spec)));
    }
    Chord::parse(&spec).map(|_| spec).map_err(|e| e.to_string())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn a_clash_is_refused_and_leaves_the_old_binding() {
        let mut k = Keymap::default();
        assert!(k.set(Action::Mic, "ctrl+l".into()).is_err());
        assert_eq!(k.mic, "ctrl+m");
        assert!(k.set(Action::Mic, "ctrl+shift+v".into()).is_ok());
        assert_eq!(k.mic, "ctrl+shift+v");
    }

    #[test]
    fn display_reads_like_the_hud() {
        assert_eq!(display("ctrl+m"), "CTRL+M");
        assert_eq!(display("escape"), "ESC");
        assert_eq!(display("ctrl+shift+k"), "CTRL+SHIFT+K");
    }

    #[test]
    fn defaults_are_valid_chords() {
        let k = Keymap::default();
        for (a, ..) in ACTIONS {
            assert!(Chord::parse(k.get(a)).is_ok());
        }
    }
}
