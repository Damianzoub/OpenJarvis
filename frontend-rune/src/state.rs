//! App state: everything the view draws, and what the network thread feeds into it.

use std::sync::mpsc::{Receiver, Sender, channel};

use rune::TextEdit;

use crate::activity::Activity;
use crate::net::Event;

/// The nine agent cards: (icon, title, agent name, key, empty line, button, preset prompt).
/// Prompts are copied verbatim from `frontend/index.html`'s `data-prompt` attributes.
pub const AGENT_CARDS: [(&str, &str, &str, &str, &str, &str, &str); 9] = [
    ("✉", "Email", "Email", "card-email", "Ask Jarvis to check your inbox.", "Check inbox", "Check my inbox for anything important."),
    ("☁", "Weather", "Weather", "card-weather", "Ask Jarvis for the current forecast.", "Check weather", "What's the weather like right now?"),
    ("≡", "News", "News", "card-news", "Ask Jarvis for today's headlines.", "Get headlines", "Give me today's top headlines."),
    ("♫", "Music", "Music", "card-music", "Ask Jarvis what's playing.", "Check player", "What's currently playing?"),
    ("▣", "Files", "Filesystem", "card-files", "Ask Jarvis to search your files.", "Search files", "Search my Documents for recently modified files."),
    ("◈", "Knowledge", "Knowledge", "card-knowledge", "Ask Jarvis to search your notes.", "Search notes", "Search my notes for anything relevant to what we've been discussing."),
    ("◷", "Reminders", "Reminders", "card-reminders", "Ask Jarvis what's due.", "Check reminders", "What are my reminders?"),
    ("↑", "Growth", "Growth", "card-growth", "Ask Jarvis about your goals.", "Check goals", "What goals am I working on?"),
    ("¤", "Finance", "Finance", "card-finance", "Ask Jarvis about your budget.", "Check budget", "How much have I spent this month?"),
];

pub const TODAY_PROMPT: &str = "What's on my calendar today?";
pub const GREETING: &str = "Online and ready, sir. How can I assist you?";

#[derive(Clone, PartialEq)]
pub enum Who { User, Jarvis }

#[derive(Clone)]
pub struct Message {
    pub id: u64,
    pub from: Who,
    pub text: String,
    /// True while this is the in-flight reply (typing indicator, tool text).
    pub typing: bool,
}

#[derive(Default, Clone)]
pub struct Stats {
    pub cpu: f32,
    pub ram: f32,
    pub used_gb: f32,
    pub total_gb: f32,
}

/// Current conditions from Open-Meteo, for the Weather tile.
#[derive(Clone, Debug, PartialEq)]
pub struct Weather {
    pub place: String,
    pub temp: f32,
    pub feels: f32,
    pub code: u32,
    pub humidity: f32,
    pub wind: f32,
    pub high: f32,
    pub low: f32,
}

impl Weather {
    /// WMO weather code → (glyph, words), the same table `backend/tools/weather.py` uses.
    pub fn describe(&self) -> (&'static str, &'static str) {
        match self.code {
            0 => ("☀", "clear sky"),
            1 => ("☀", "mainly clear"),
            2 => ("⛅", "partly cloudy"),
            3 => ("☁", "overcast"),
            45 | 48 => ("≋", "fog"),
            51..=57 => ("☂", "drizzle"),
            61 | 80 => ("☂", "light rain"),
            63 | 81 => ("☂", "rain"),
            65..=67 | 82 => ("☂", "heavy rain"),
            71 | 77 | 85 => ("❄", "light snow"),
            73 | 75 | 86 => ("❄", "snow"),
            95..=99 => ("⚡", "thunderstorm"),
            _ => ("☁", "unknown"),
        }
    }
}

#[derive(Clone)]
pub struct Thing {
    pub time: String,
    pub title: String,
}

pub struct State {
    /// Past conversations, listed in the sidebar.
    pub conversations: crate::conversations::Conversations,
    pub clock: chrono::DateTime<chrono::Local>,
    pub stats: Option<Stats>,
    pub today: Vec<Thing>,
    pub weather: Option<Weather>,
    pub activity: Activity,
    pub messages: Vec<Message>,
    pub next_id: u64,
    /// Client-side chat history sent with each request, as the Tauri HUD keeps it.
    pub history: Vec<(String, String)>,
    pub session_id: String,
    pub input: TextEdit,
    pub busy: bool,
    /// The in-flight reply: its message, the text so far and the agent answering.
    pub reply_id: Option<u64>,
    pub reply: String,
    pub reply_agent: String,
    pub inflight: crate::net::Inflight,
    /// The current chat request's number; STOP bumps it so the old stream is dropped.
    pub chat_gen: std::sync::Arc<std::sync::atomic::AtomicU64>,
    /// The agent the backend routed the in-flight request to, once it says so.
    pub working_agent: Option<String>,
    /// What the in-flight reply has done so far ("Thinking...", "→ Weather agent", "Using …").
    pub steps: Vec<String>,
    /// When the request was sent, and how long until the first text showed.
    pub started: Option<std::time::Instant>,
    pub first_text: Option<f32>,
    /// A finished reply's footer, by message id: "Weather agent · first text 6.1 s · 8.4 s".
    pub meta: std::collections::HashMap<u64, String>,
    pub status: String,
    pub banner: Option<String>,
    pub mic_on: bool,
    pub confirm_close: bool,
    /// The reply whose COPY button was just pressed (shows "COPIED" briefly).
    pub copied: Option<(u64, std::time::Instant)>,
    /// The Recent Activity line opened to its full reply (by timestamp), and whether the
    /// list shows everything or the last three.
    pub open_activity: Option<i64>,
    pub activity_all: bool,
    /// Prompts sent this session, newest last, and where ↑/↓ is in them.
    pub sent: Vec<String>,
    pub recall: Option<usize>,
    /// Editable shortcuts, the pop-up that edits them, the action waiting for new keys, and
    /// the editor's last message (text, is_error).
    pub keymap: crate::keymap::Keymap,
    pub shortcuts_open: bool,
    pub capturing: Option<crate::keymap::Action>,
    pub shortcut_msg: Option<(String, bool)>,
    pub tx: Sender<Event>,
    pub rx: Receiver<Event>,
    pub waker: Option<rune::Waker>,
    pub logo: Option<rune::Image>,
    pub images: Option<rune::ImageCache>,
}

impl State {
    pub fn new() -> State {
        let (tx, rx) = channel();
        State {
            conversations: crate::conversations::Conversations::load(),
            clock: chrono::Local::now(),
            stats: None,
            today: Vec::new(),
            weather: None,
            activity: Activity::load(),
            messages: vec![Message { id: 0, from: Who::Jarvis, text: GREETING.into(), typing: false }],
            next_id: 1,
            history: Vec::new(),
            session_id: uuid::Uuid::new_v4().to_string(),
            input: TextEdit::new(""),
            busy: false,
            reply_id: None,
            reply: String::new(),
            reply_agent: "General".into(),
            inflight: crate::net::Inflight::default(),
            chat_gen: Default::default(),
            working_agent: None,
            steps: Vec::new(),
            started: None,
            first_text: None,
            meta: Default::default(),
            status: "SYSTEM ONLINE".into(),
            banner: None,
            mic_on: false,
            confirm_close: false,
            copied: None,
            open_activity: None,
            activity_all: false,
            sent: Vec::new(),
            recall: None,
            keymap: crate::keymap::Keymap::load(),
            shortcuts_open: false,
            capturing: None,
            shortcut_msg: None,
            tx,
            rx,
            waker: None,
            logo: None,
            images: None,
        }
    }

    pub fn push(&mut self, from: Who, text: impl Into<String>, typing: bool) -> u64 {
        let id = self.next_id;
        self.next_id += 1;
        self.messages.push(Message { id, from, text: text.into(), typing });
        id
    }

    pub fn clear_conversation(&mut self) {
        self.messages.clear();
        self.history.clear();
        self.session_id = uuid::Uuid::new_v4().to_string();
    }

    /// Brings a saved conversation back into the chat, under its old session id.
    pub fn open_conversation(&mut self, id: &str) {
        let Some(c) = self.conversations.get(id).cloned() else { return };
        self.messages.clear();
        for (role, text) in &c.turns {
            let from = if role == "user" { Who::User } else { Who::Jarvis };
            self.push(from, text.clone(), false);
        }
        self.history = c.turns;
        self.session_id = c.id;
        self.recall = None;
    }
}

#[cfg(test)]
mod tests {
    use super::Weather;

    #[test]
    fn weather_codes_read_like_the_backend_tool() {
        let w = |code| Weather { place: "Athens".into(), temp: 18.0, feels: 17.0, code, humidity: 50.0, wind: 10.0, high: 20.0, low: 10.0 };
        assert_eq!(w(0).describe(), ("☀", "clear sky"));
        assert_eq!(w(2).describe(), ("⛅", "partly cloudy"));
        assert_eq!(w(63).describe(), ("☂", "rain"));
        assert_eq!(w(95).describe(), ("⚡", "thunderstorm"));
        assert_eq!(w(1234).describe().1, "unknown");
    }
}
