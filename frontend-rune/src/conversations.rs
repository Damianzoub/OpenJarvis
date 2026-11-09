//! Past conversations for the sidebar, saved to a JSON file next to `activity.json`.

use std::path::PathBuf;

use serde::{Deserialize, Serialize};

const MAX_CONVERSATIONS: usize = 50;

#[derive(Clone, Serialize, Deserialize)]
pub struct Conversation {
    /// The `session_id` it was sent with, so reopening it keeps talking to the same session.
    pub id: String,
    pub title: String,
    /// Milliseconds since the Unix epoch of the last finished reply.
    pub updated: i64,
    /// (role, text) turns, "user" or "assistant", as `State::history` holds them.
    pub turns: Vec<(String, String)>,
}

#[derive(Default)]
pub struct Conversations {
    /// Newest first.
    pub list: Vec<Conversation>,
    path: Option<PathBuf>,
}

fn store_path() -> Option<PathBuf> {
    if let Ok(p) = std::env::var("JARVIS_CONVERSATIONS_FILE") {
        return Some(PathBuf::from(p));
    }
    dirs::data_dir().map(|d| d.join("OpenJarvis").join("conversations.json"))
}

/// The first prompt, on one line and cut to fit the sidebar.
fn title(turns: &[(String, String)]) -> String {
    let first = turns.iter().find(|(role, _)| role == "user").map_or("", |(_, t)| t.as_str());
    let plain = first.split_whitespace().collect::<Vec<_>>().join(" ");
    if plain.chars().count() > 40 { format!("{}…", plain.chars().take(40).collect::<String>()) } else { plain }
}

impl Conversations {
    pub fn load() -> Conversations {
        let path = store_path();
        let list = path
            .as_ref()
            .and_then(|p| std::fs::read_to_string(p).ok())
            .and_then(|raw| serde_json::from_str(&raw).ok())
            .unwrap_or_default();
        Conversations { list, path }
    }

    /// Saves the conversation under `id` and moves it to the top.
    pub fn save(&mut self, id: &str, turns: &[(String, String)]) {
        if turns.is_empty() {
            return;
        }
        self.list.retain(|c| c.id != id);
        let c = Conversation { id: id.to_string(), title: title(turns), updated: chrono::Utc::now().timestamp_millis(), turns: turns.to_vec() };
        self.list.insert(0, c);
        self.list.truncate(MAX_CONVERSATIONS);
        self.write();
    }

    pub fn get(&self, id: &str) -> Option<&Conversation> {
        self.list.iter().find(|c| c.id == id)
    }

    fn write(&self) {
        let Some(path) = &self.path else { return };
        if let Some(dir) = path.parent() {
            let _ = std::fs::create_dir_all(dir);
        }
        if let Ok(json) = serde_json::to_string(&self.list) {
            let _ = std::fs::write(path, json);
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn saving_again_moves_it_to_the_top_without_duplicating() {
        let mut c = Conversations::default();
        let t = |q: &str| vec![("user".to_string(), q.to_string()), ("assistant".to_string(), "ok".to_string())];
        c.save("a", &t("first"));
        c.save("b", &t("second"));
        c.save("a", &t("first   one\nagain"));
        assert_eq!(c.list.len(), 2);
        assert_eq!(c.list[0].id, "a");
        assert_eq!(c.list[0].title, "first one again");
    }
}
