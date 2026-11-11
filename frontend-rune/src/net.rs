//! Backend I/O, all off the UI thread. Workers send `Event`s down a channel and wake the
//! window; `poll` drains them into state. Every failure is soft: an `Offline` event, never a panic.

use std::io::{BufRead, BufReader};
use std::sync::Arc;
use std::sync::atomic::{AtomicU64, AtomicUsize, Ordering};
use std::sync::mpsc::Sender;
use std::time::Duration;

use serde::Deserialize;

use crate::state::{Stats, Thing, Weather};

pub fn backend() -> String {
    // Test switch: every request, chat included, goes nowhere.
    if std::env::var("JARVIS_NO_BACKEND").is_ok() {
        return "http://127.0.0.1:9".into();
    }
    std::env::var("JARVIS_BACKEND").unwrap_or_else(|_| "http://localhost:8000".into())
}

/// The Pipecat voice bot (`python -m voice.main`), a separate process from the backend.
pub fn voice_url() -> String {
    std::env::var("JARVIS_VOICE_URL").unwrap_or_else(|_| "http://localhost:7860".into())
}

pub enum Event {
    Stats(Stats),
    Today(Vec<Thing>),
    Weather(Weather),
    Due(Vec<String>),
    /// A poll failed: the backend is unreachable.
    Offline,
    /// Whether the voice bot's port answered at all (any HTTP status, not just 2xx).
    VoiceStatus(bool),
    /// A chat stream event, tagged with the request it belongs to (see `start_chat`).
    Chat(u64, ChatEvent),
}

#[derive(Debug, PartialEq)]
pub enum ChatEvent {
    Status(String),
    Tool { content: String, agent: Option<String> },
    /// The full reply so far (cumulative), which replaces the in-flight body.
    Text { content: String, agent: Option<String> },
    Done { agent: Option<String> },
    /// The request itself failed (connection refused, HTTP error, broken stream).
    Failed,
}

/// Requests in flight, so a headless run can wait for real answers before drawing.
#[derive(Clone, Default)]
pub struct Inflight(Arc<AtomicUsize>);

impl Inflight {
    pub fn count(&self) -> usize { self.0.load(Ordering::SeqCst) }
    fn start(&self) { self.0.fetch_add(1, Ordering::SeqCst); }
    fn end(&self) { self.0.fetch_sub(1, Ordering::SeqCst); }
}

fn agent() -> ureq::Agent {
    ureq::AgentBuilder::new().timeout_connect(Duration::from_secs(2)).build()
}

#[derive(Deserialize)]
struct SystemDto { cpu: f32, ram: f32, ram_used_gb: f32, ram_total_gb: f32 }

#[derive(Deserialize)]
struct ThingDto { time: String, title: String }

#[derive(Deserialize)]
struct DueDto { text: String }

fn get<T: for<'de> Deserialize<'de>>(path: &str) -> Option<T> {
    agent().get(&format!("{}{path}", backend())).timeout(Duration::from_secs(5)).call().ok()?.into_json().ok()
}

fn send(tx: &Sender<Event>, wake: &rune::Waker, inflight: &Inflight, ev: Event) {
    finish(tx, wake, inflight, Some(ev));
}

fn finish(tx: &Sender<Event>, wake: &rune::Waker, inflight: &Inflight, ev: Option<Event>) {
    if let Some(ev) = ev {
        let _ = tx.send(ev);
    }
    inflight.end();
    wake();
}

pub fn fetch_stats(tx: &Sender<Event>, wake: &rune::Waker, inflight: &Inflight) {
    inflight.start();
    let ev = match get::<SystemDto>("/system") {
        Some(d) => Event::Stats(Stats { cpu: d.cpu, ram: d.ram, used_gb: d.ram_used_gb, total_gb: d.ram_total_gb }),
        None => Event::Offline,
    };
    send(tx, wake, inflight, ev);
}

/// Reachability only, no audio: a non-2xx response (the bot has no route at `/`) still proves
/// the process is alive; only a connection failure counts as down.
pub fn fetch_voice_status(tx: &Sender<Event>, wake: &rune::Waker, inflight: &Inflight) {
    inflight.start();
    let up = matches!(agent().get(&voice_url()).timeout(Duration::from_secs(2)).call(), Ok(_) | Err(ureq::Error::Status(_, _)));
    send(tx, wake, inflight, Event::VoiceStatus(up));
}

pub fn fetch_today(tx: &Sender<Event>, wake: &rune::Waker, inflight: &Inflight) {
    inflight.start();
    // Only `/system` decides "offline"; a failed `/today` keeps the last list, as the Tauri HUD does.
    let ev = get::<Vec<ThingDto>>("/today").map(|v| Event::Today(v.into_iter().map(|t| Thing { time: t.time, title: t.title }).collect()));
    finish(tx, wake, inflight, ev);
}

pub fn fetch_due(tx: &Sender<Event>, wake: &rune::Waker, inflight: &Inflight) {
    inflight.start();
    let ev = get::<Vec<DueDto>>("/reminders/due").map(|v| Event::Due(v.into_iter().map(|d| d.text).collect()));
    finish(tx, wake, inflight, ev);
}

/// The city the Weather tile shows; Athens matches the calendar's time zone.
fn weather_city() -> String {
    std::env::var("JARVIS_WEATHER_CITY").unwrap_or_else(|_| "Athens".into())
}

#[derive(Deserialize)]
struct GeoDto { results: Option<Vec<GeoPlace>> }
#[derive(Deserialize)]
struct GeoPlace { latitude: f64, longitude: f64, name: String }
#[derive(Deserialize)]
struct ForecastDto { current: CurrentDto, daily: DailyDto }
#[derive(Deserialize)]
struct CurrentDto { temperature_2m: f32, apparent_temperature: f32, relative_humidity_2m: f32, wind_speed_10m: f32, weather_code: u32 }
#[derive(Deserialize)]
struct DailyDto { temperature_2m_max: Vec<f32>, temperature_2m_min: Vec<f32> }

/// Current conditions straight from Open-Meteo (free, no key), the service the backend's
/// weather tool uses. Weather is one of the cloud calls CLAUDE.md allows.
fn get_weather() -> Option<Weather> {
    if std::env::var("JARVIS_NO_BACKEND").is_ok() {
        return None;
    }
    let a = agent();
    let geo: GeoDto = a.get("https://geocoding-api.open-meteo.com/v1/search")
        .query("name", &weather_city()).query("count", "1")
        .timeout(Duration::from_secs(8)).call().ok()?.into_json().ok()?;
    let place = geo.results?.into_iter().next()?;
    let f: ForecastDto = a.get("https://api.open-meteo.com/v1/forecast")
        .query("latitude", &place.latitude.to_string())
        .query("longitude", &place.longitude.to_string())
        .query("current", "temperature_2m,apparent_temperature,relative_humidity_2m,wind_speed_10m,weather_code")
        .query("daily", "temperature_2m_max,temperature_2m_min")
        .query("timezone", "auto").query("forecast_days", "1")
        .timeout(Duration::from_secs(8)).call().ok()?.into_json().ok()?;
    Some(Weather {
        place: place.name,
        temp: f.current.temperature_2m,
        feels: f.current.apparent_temperature,
        code: f.current.weather_code,
        humidity: f.current.relative_humidity_2m,
        wind: f.current.wind_speed_10m,
        high: f.daily.temperature_2m_max.first().copied().unwrap_or(f.current.temperature_2m),
        low: f.daily.temperature_2m_min.first().copied().unwrap_or(f.current.temperature_2m),
    })
}

pub fn fetch_weather(tx: &Sender<Event>, wake: &rune::Waker, inflight: &Inflight) {
    inflight.start();
    finish(tx, wake, inflight, get_weather().map(Event::Weather));
}

/// The pollers: `/system` every 3 s, `/reminders/due` every 30 s, `/today` every 60 s,
/// and the weather every 10 minutes.
/// `once` runs a single round (headless runs).
pub fn start_pollers(tx: Sender<Event>, wake: rune::Waker, inflight: Inflight, once: bool) {
    std::thread::spawn(move || {
        let mut tick: u64 = 0;
        loop {
            fetch_stats(&tx, &wake, &inflight);
            fetch_voice_status(&tx, &wake, &inflight);
            if tick % 20 == 0 { fetch_today(&tx, &wake, &inflight); }
            if tick % 200 == 0 { fetch_weather(&tx, &wake, &inflight); }
            if tick % 10 == 0 && tick > 0 { fetch_due(&tx, &wake, &inflight); }
            if once { break; }
            std::thread::sleep(Duration::from_secs(3));
            tick += 1;
        }
    });
}

/// One parsed `data:` line of the `/chat` stream, or None for anything malformed.
pub fn parse_chat_line(line: &str) -> Option<ChatEvent> {
    let json: serde_json::Value = serde_json::from_str(line.strip_prefix("data: ")?).ok()?;
    let agent = json.get("agent").and_then(|a| a.as_str()).map(String::from);
    let content = || json.get("content").and_then(|c| c.as_str()).map(String::from);
    match json.get("type")?.as_str()? {
        "status" => Some(ChatEvent::Status(content()?)),
        "tool" => Some(ChatEvent::Tool { content: content()?, agent }),
        "text" => Some(ChatEvent::Text { content: content()?, agent }),
        "done" => Some(ChatEvent::Done { agent }),
        _ => None,
    }
}

/// Streams one `/chat` request on a worker thread.
/// Streams one `/chat` request on a worker thread. `generation` numbers the request; when
/// `current` moves past it (STOP, or a newer request) the worker drops the stream and its
/// remaining events are ignored, so a stopped reply never lands late.
pub fn start_chat(history: Vec<(String, String)>, session_id: String, tx: Sender<Event>, wake: rune::Waker, generation: u64, current: Arc<AtomicU64>) {
    std::thread::spawn(move || {
        let live = || current.load(Ordering::SeqCst) == generation;
        let messages: Vec<_> = history.iter().map(|(role, content)| serde_json::json!({"role": role, "content": content})).collect();
        let body = serde_json::json!({"messages": messages, "session_id": session_id});
        let resp = agent().post(&format!("{}/chat", backend())).send_json(body);
        let mut done = false;
        match resp {
            Ok(r) => {
                for line in BufReader::new(r.into_reader()).lines() {
                    if !live() {
                        return; // stopped: dropping the reader closes the connection
                    }
                    let Ok(line) = line else { break };
                    if let Some(ev) = parse_chat_line(&line) {
                        done |= matches!(ev, ChatEvent::Done { .. });
                        let _ = tx.send(Event::Chat(generation, ev));
                        wake();
                    }
                }
                if !done && live() {
                    let _ = tx.send(Event::Chat(generation, ChatEvent::Failed));
                }
            }
            Err(_) => { let _ = tx.send(Event::Chat(generation, ChatEvent::Failed)); }
        }
        wake();
    });
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn parses_each_event_type_and_skips_junk() {
        assert_eq!(parse_chat_line(r#"data: {"type":"status","content":"Thinking..."}"#), Some(ChatEvent::Status("Thinking...".into())));
        assert_eq!(
            parse_chat_line(r#"data: {"type":"text","content":"Hi","agent":"General"}"#),
            Some(ChatEvent::Text { content: "Hi".into(), agent: Some("General".into()) })
        );
        assert_eq!(parse_chat_line(r#"data: {"type":"done","agent":"Weather"}"#), Some(ChatEvent::Done { agent: Some("Weather".into()) }));
        assert_eq!(parse_chat_line("data: {not json"), None);
        assert_eq!(parse_chat_line(""), None);
        assert_eq!(parse_chat_line(r#"event: {"type":"done"}"#), None);
    }
}
