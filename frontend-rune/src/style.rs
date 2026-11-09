//! The HUD's visual language, taken from `frontend/src/styles.css` (`:root` tokens).

use rune::tok::TextStyle;
use rune::{Color, El, el};

fn c(hex: &str) -> Color {
    rune::color::hex(hex).expect("valid hex colour")
}

pub fn cyan() -> Color { c("#5b9dff") }
pub fn cyan_dim() -> Color { c("#5b9dff33") }
pub fn cyan_dim_text() -> Color { c("#5a8fe0") }
pub fn cyan_tint(alpha_hex: &str) -> Color { c(&format!("#5b9dff{alpha_hex}")) }
pub fn red() -> Color { c("#ff4d00") }
pub fn red_tint(alpha_hex: &str) -> Color { c(&format!("#ff4d00{alpha_hex}")) }
pub fn bg() -> Color { c("#060a12") }
pub fn surface() -> Color { c("#0b1220") }
pub fn border() -> Color { c("#5b9dff33") }
pub fn bright() -> Color { c("#ccd8ff") }
pub fn user_text() -> Color { c("#ffcab0") }
pub fn summary_text() -> Color { c("#b8c7f0") }

/// The HUD's monospace (`--font`). IBM Plex Mono stands in for Courier New, which can't be embedded.
/// Small sizes get one extra point: the CSS sizes (9–11 px) were hard to read on a dark HUD.
pub const fn mono(size: f32, weight: f32, tracking: f32) -> TextStyle {
    let size = if size < 12.0 { size + 1.0 } else { size };
    TextStyle::new(size, weight).mono().tracking(tracking)
}

/// Jarvis replies use Inter, as `.message .text` does.
pub const REPLY: TextStyle = TextStyle::new(13.0, 400.0).lh(13.0 * 1.75);

/// The cyan glow most HUD elements carry (`--cyan-glow`).
pub fn glow(e: El, color: Color, blur: f32) -> El {
    e.shadow(0.0, blur, color)
}

/// One L-shaped bracket corner (`.corner.bl` / `.corner.br`), 14 pt square, 2 pt stroke.
pub fn corner(right: bool) -> El {
    let sides = if right { [0.0, 2.0, 2.0, 0.0] } else { [0.0, 0.0, 2.0, 2.0] };
    el().size(14.0, 14.0).border_sides(sides, cyan())
}

/// rune-kit's components need a kit; the opencode one carries the fonts this app embeds.
pub fn kit() -> &'static rune_kit::Kit {
    rune_theme_opencode::kit(true)
}

/// Text whose changed characters roll (digits count up and down) instead of jumping.
pub fn rolling(key: &str, text: String, font: TextStyle, color: Color, value: Option<f64>) -> El {
    let mut r = rune_kit::RollingText::new(key.to_string(), text).font(font).color(color).trailing();
    if let Some(v) = value {
        r = r.value(v);
    }
    r.build(kit())
}
