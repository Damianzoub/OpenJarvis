//! Recent Activity, persisted to a JSON file in place of the Tauri HUD's `localStorage`.

use std::path::PathBuf;

use serde::{Deserialize, Serialize};

const MAX_ACTIVITY: usize = 30;

#[derive(Clone, Serialize, Deserialize)]
pub struct Entry {
    pub agent: String,
    pub summary: String,
    /// Milliseconds since the Unix epoch, as `Date.now()` stores it.
    pub timestamp: i64,
    /// The whole reply, so a card can expand to it (older files don't have it).
    #[serde(default)]
    pub full: String,
}

#[derive(Default)]
pub struct Activity {
    pub entries: Vec<Entry>,
    path: Option<PathBuf>,
}

fn store_path() -> Option<PathBuf> {
    if let Ok(p) = std::env::var("JARVIS_ACTIVITY_FILE") {
        return Some(PathBuf::from(p));
    }
    dirs::data_dir().map(|d| d.join("OpenJarvis").join("activity.json"))
}

impl Activity {
    pub fn load() -> Activity {
        let path = store_path();
        let mut entries: Vec<Entry> = path
            .as_ref()
            .and_then(|p| std::fs::read_to_string(p).ok())
            .and_then(|raw| serde_json::from_str(&raw).ok())
            .unwrap_or_default();
        // Summaries saved before the list-marker fix are rebuilt from the full reply.
        for e in &mut entries {
            if !e.full.is_empty() {
                e.summary = summarize(&e.full);
            }
        }
        Activity { entries, path }
    }

    pub fn record(&mut self, agent: &str, reply: &str) {
        let summary = summarize(reply);
        if summary.is_empty() {
            return;
        }
        let full: String = reply.chars().take(4000).collect();
        let entry = Entry { agent: agent.to_string(), summary, timestamp: chrono::Utc::now().timestamp_millis(), full };
        self.entries.insert(0, entry);
        self.entries.truncate(MAX_ACTIVITY);
        self.save();
    }

    fn save(&self) {
        let Some(path) = &self.path else { return };
        if let Some(dir) = path.parent() {
            let _ = std::fs::create_dir_all(dir);
        }
        if let Ok(json) = serde_json::to_string(&self.entries) {
            let _ = std::fs::write(path, json);
        }
    }

    /// The newest entry for an agent, which its card shows.
    pub fn latest(&self, agent: &str) -> Option<&Entry> {
        self.entries.iter().find(|e| e.agent == agent)
    }
}

/// A Markdown list marker at the start of a line ("- ", "* ", "+ ", "1. ", "2) "), removed so a
/// summary reads "Wind: 12 km/h · Humidity: 55%" instead of "- Wind: 12 km/h - Humidity: 55%".
fn strip_list_marker(line: &str) -> (&str, bool) {
    let t = line.trim_start();
    for m in ["- ", "* ", "+ "] {
        if let Some(rest) = t.strip_prefix(m) {
            return (rest, true);
        }
    }
    let digits = t.chars().take_while(|c| c.is_ascii_digit()).count();
    if digits > 0 {
        let rest = &t[digits..];
        if let Some(r) = rest.strip_prefix(". ").or_else(|| rest.strip_prefix(") ")) {
            return (r, true);
        }
    }
    (line, false)
}

/// `summarize` from `main.ts` (strip `#*`_>`, collapse whitespace, cut at 140 chars), plus list
/// markers removed and list items joined with " · ".
pub fn summarize(text: &str) -> String {
    let mut joined = String::new();
    for line in text.lines() {
        let (body, item) = strip_list_marker(line);
        if body.trim().is_empty() {
            continue;
        }
        if !joined.is_empty() {
            joined.push_str(if item { " · " } else { " " });
        }
        joined.push_str(body);
    }
    let stripped: String = joined.chars().filter(|c| !"#*`_>".contains(*c)).collect();
    let plain = stripped.split_whitespace().collect::<Vec<_>>().join(" ");
    if plain.chars().count() > 140 {
        format!("{}…", plain.chars().take(140).collect::<String>())
    } else {
        plain
    }
}

pub fn time_ago(timestamp_ms: i64) -> String {
    let mins = (chrono::Utc::now().timestamp_millis() - timestamp_ms) / 60_000;
    if mins < 1 {
        "just now".into()
    } else if mins < 60 {
        format!("{mins}m ago")
    } else if mins / 60 < 24 {
        format!("{}h ago", mins / 60)
    } else {
        format!("{}d ago", mins / 60 / 24)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn summarize_matches_the_tauri_hud() {
        assert_eq!(summarize("## Hello   **world**\n> quote"), "Hello world quote");
        let long = "a".repeat(200);
        assert_eq!(summarize(&long).chars().count(), 141);
    }

    #[test]
    fn list_markers_become_separators() {
        assert_eq!(
            summarize("It's 18°C in Athens.\n\n- Wind: 12 km/h\n- Humidity: 55%\n\nBring a jacket."),
            "It's 18°C in Athens. · Wind: 12 km/h · Humidity: 55% Bring a jacket."
        );
        assert_eq!(summarize("Steps:\n1. Open it\n2) Close it"), "Steps: · Open it · Close it");
        assert_eq!(summarize("* starred item"), "starred item");
        assert_eq!(summarize("2 + 2 = 4"), "2 + 2 = 4");
        assert_eq!(summarize("-5 degrees"), "-5 degrees");
    }
}
