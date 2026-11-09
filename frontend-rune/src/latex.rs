//! LaTeX in replies. rune-kit's Markdown has no maths, so maths is found here and turned into
//! Unicode: inline `$…$` / `\(…\)` becomes text inside the Markdown, and display `$$…$$` /
//! `\[…\]` becomes its own block. Common notation only: no stacked fractions or 2-D layout.

/// A reply split into Markdown and display-maths blocks, in order.
#[derive(Debug, PartialEq)]
pub enum Seg {
    Markdown(String),
    Display(String),
}

pub fn split(src: &str) -> Vec<Seg> {
    let mut out = Vec::new();
    let mut md = String::new();
    let mut in_fence = false;
    let mut lines = src.split_inclusive('\n').peekable();
    let mut display: Option<(String, &str)> = None;
    while let Some(line) = lines.next() {
        if let Some((mut buf, close)) = display.take() {
            if let Some(end) = line.find(close) {
                buf.push_str(&line[..end]);
                out.push(Seg::Display(to_unicode(buf.trim())));
                let rest = &line[end + close.len()..];
                if !rest.trim().is_empty() { md.push_str(&inline(rest)); }
            } else {
                buf.push_str(line);
                display = Some((buf, close));
            }
            continue;
        }
        let t = line.trim_start();
        if t.starts_with("```") || t.starts_with("~~~") {
            in_fence = !in_fence;
            md.push_str(line);
            continue;
        }
        if in_fence {
            md.push_str(line);
            continue;
        }
        let opener = if t.starts_with("$$") { Some(("$$", "$$")) } else if t.starts_with("\\[") { Some(("\\[", "\\]")) } else { None };
        if let Some((open, close)) = opener {
            if !md.is_empty() { out.push(Seg::Markdown(std::mem::take(&mut md))); }
            let body = &t[open.len()..];
            if let Some(end) = body.find(close) {
                out.push(Seg::Display(to_unicode(body[..end].trim())));
                let rest = &body[end + close.len()..];
                if !rest.trim().is_empty() { md.push_str(&inline(rest)); }
            } else {
                display = Some((body.to_string(), close));
            }
            continue;
        }
        md.push_str(&inline(line));
    }
    if let Some((buf, _)) = display {
        out.push(Seg::Display(to_unicode(buf.trim())));
    }
    if !md.is_empty() { out.push(Seg::Markdown(md)); }
    out
}

/// Replaces inline maths in one line, leaving `code spans` and currency ("$5 and $10") alone.
fn inline(line: &str) -> String {
    let chars: Vec<char> = line.chars().collect();
    let mut out = String::new();
    let mut i = 0;
    while i < chars.len() {
        let c = chars[i];
        if c == '`' {
            let end = chars[i + 1..].iter().position(|&x| x == '`').map(|p| i + 1 + p);
            let stop = end.unwrap_or(chars.len() - 1);
            out.extend(&chars[i..=stop]);
            i = stop + 1;
            continue;
        }
        if c == '\\' && chars.get(i + 1) == Some(&'(') {
            if let Some(p) = find(&chars, i + 2, &['\\', ')']) {
                out.push_str(&emph(&to_unicode(&chars[i + 2..p].iter().collect::<String>())));
                i = p + 2;
                continue;
            }
        }
        if c == '$' && chars.get(i + 1).is_some_and(|n| !n.is_whitespace() && *n != '$') && (i == 0 || chars[i - 1] != '\\') {
            let close = (i + 1..chars.len()).find(|&j| {
                chars[j] == '$' && !chars[j - 1].is_whitespace() && chars[j - 1] != '\\'
                    && !chars.get(j + 1).is_some_and(|n| n.is_ascii_digit())
            });
            if let Some(j) = close {
                let body: String = chars[i + 1..j].iter().collect();
                if looks_like_math(&body) {
                    out.push_str(&emph(&to_unicode(&body)));
                    i = j + 1;
                    continue;
                }
            }
        }
        out.push(c);
        i += 1;
    }
    out
}

fn find(chars: &[char], from: usize, pat: &[char; 2]) -> Option<usize> {
    (from..chars.len().saturating_sub(1)).find(|&j| chars[j] == pat[0] && chars[j + 1] == pat[1])
}

/// "$5 and $10" is money; "$x^2$", "$\pi$", "$a=b$" are maths.
fn looks_like_math(body: &str) -> bool {
    if body.chars().all(|c| c.is_ascii_digit() || c == '.' || c == ',') {
        return false;
    }
    body.contains(['\\', '^', '_', '=', '{', '+', '<', '>']) || body.chars().count() <= 3
}

/// Italic in Markdown, with Markdown's own characters escaped so `*` and `_` stay literal.
fn emph(s: &str) -> String {
    let escaped: String = s.chars().flat_map(|c| {
        if "*_`[]\\".contains(c) { vec!['\\', c] } else { vec![c] }
    }).collect();
    format!("*{escaped}*")
}

const SYMBOLS: &[(&str, &str)] = &[
    ("alpha", "α"), ("beta", "β"), ("gamma", "γ"), ("delta", "δ"), ("epsilon", "ε"), ("varepsilon", "ε"),
    ("zeta", "ζ"), ("eta", "η"), ("theta", "θ"), ("vartheta", "ϑ"), ("iota", "ι"), ("kappa", "κ"),
    ("lambda", "λ"), ("mu", "μ"), ("nu", "ν"), ("xi", "ξ"), ("pi", "π"), ("rho", "ρ"), ("sigma", "σ"),
    ("tau", "τ"), ("upsilon", "υ"), ("phi", "φ"), ("varphi", "φ"), ("chi", "χ"), ("psi", "ψ"), ("omega", "ω"),
    ("Gamma", "Γ"), ("Delta", "Δ"), ("Theta", "Θ"), ("Lambda", "Λ"), ("Xi", "Ξ"), ("Pi", "Π"),
    ("Sigma", "Σ"), ("Phi", "Φ"), ("Psi", "Ψ"), ("Omega", "Ω"),
    ("times", "×"), ("cdot", "·"), ("pm", "±"), ("mp", "∓"), ("div", "÷"), ("ast", "∗"),
    ("leq", "≤"), ("le", "≤"), ("geq", "≥"), ("ge", "≥"), ("neq", "≠"), ("ne", "≠"), ("approx", "≈"),
    ("equiv", "≡"), ("sim", "∼"), ("simeq", "≃"), ("propto", "∝"), ("ll", "≪"), ("gg", "≫"),
    ("infty", "∞"), ("partial", "∂"), ("nabla", "∇"), ("sum", "∑"), ("prod", "∏"), ("int", "∫"),
    ("iint", "∬"), ("oint", "∮"), ("to", "→"), ("rightarrow", "→"), ("leftarrow", "←"),
    ("Rightarrow", "⇒"), ("Leftarrow", "⇐"), ("leftrightarrow", "↔"), ("Leftrightarrow", "⇔"),
    ("iff", "⇔"), ("implies", "⟹"), ("mapsto", "↦"), ("in", "∈"), ("notin", "∉"), ("ni", "∋"),
    ("subset", "⊂"), ("subseteq", "⊆"), ("supset", "⊃"), ("supseteq", "⊇"), ("cup", "∪"), ("cap", "∩"),
    ("emptyset", "∅"), ("varnothing", "∅"), ("forall", "∀"), ("exists", "∃"), ("neg", "¬"),
    ("land", "∧"), ("wedge", "∧"), ("lor", "∨"), ("vee", "∨"), ("oplus", "⊕"), ("otimes", "⊗"),
    ("cdots", "⋯"), ("ldots", "…"), ("dots", "…"), ("vdots", "⋮"), ("circ", "∘"), ("degree", "°"),
    ("angle", "∠"), ("perp", "⊥"), ("parallel", "∥"), ("langle", "⟨"), ("rangle", "⟩"),
    ("lfloor", "⌊"), ("rfloor", "⌋"), ("lceil", "⌈"), ("rceil", "⌉"), ("hbar", "ℏ"), ("ell", "ℓ"),
    ("prime", "′"), ("star", "⋆"), ("dagger", "†"), ("checkmark", "✓"), ("therefore", "∴"), ("because", "∵"),
    ("quad", "  "), ("qquad", "    "), (",", " "), (";", " "), (":", " "), ("!", ""), (" ", " "),
    ("left", ""), ("right", ""), ("big", ""), ("Big", ""), ("displaystyle", ""), ("limits", ""),
    ("{", "{"), ("}", "}"), ("%", "%"), ("$", "$"), ("&", "&"), ("#", "#"), ("_", "_"), ("|", "‖"),
];

const WORDS: &[&str] = &[
    "sin", "cos", "tan", "cot", "sec", "csc", "arcsin", "arccos", "arctan", "sinh", "cosh", "tanh",
    "log", "ln", "lg", "exp", "lim", "max", "min", "sup", "inf", "det", "dim", "ker", "gcd", "deg", "arg", "Pr",
];

fn sup(c: char) -> Option<char> {
    let (from, to) = ("0123456789+-=()niaTbcdefghjklmoprstuvwxyz", "⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻⁼⁽⁾ⁿⁱᵃᵀᵇᶜᵈᵉᶠᵍʰʲᵏˡᵐᵒᵖʳˢᵗᵘᵛʷˣʸᶻ");
    from.chars().position(|x| x == c).and_then(|p| to.chars().nth(p))
}

fn sub(c: char) -> Option<char> {
    let (from, to) = ("0123456789+-=()aehijklmnoprstuvx", "₀₁₂₃₄₅₆₇₈₉₊₋₌₍₎ₐₑₕᵢⱼₖₗₘₙₒₚᵣₛₜᵤᵥₓ");
    from.chars().position(|x| x == c).and_then(|p| to.chars().nth(p))
}

/// LaTeX maths → readable Unicode.
pub fn to_unicode(src: &str) -> String {
    let chars: Vec<char> = src.chars().collect();
    let mut p = Parser { c: &chars, i: 0 };
    p.until(None).split_whitespace().collect::<Vec<_>>().join(" ").replace(" ,", ",")
}

struct Parser<'a> {
    c: &'a [char],
    i: usize,
}

impl Parser<'_> {
    fn peek(&self) -> Option<char> { self.c.get(self.i).copied() }

    /// Converts until `stop` (a closing brace) or the end.
    fn until(&mut self, stop: Option<char>) -> String {
        let mut out = String::new();
        while let Some(c) = self.peek() {
            if Some(c) == stop {
                self.i += 1;
                return out;
            }
            self.i += 1;
            match c {
                '\\' => out.push_str(&self.command()),
                '{' => out.push_str(&self.until(Some('}'))),
                '^' => { let g = self.group(); out.push_str(&script(&g, sup, '^')); }
                '_' => { let g = self.group(); out.push_str(&script(&g, sub, '_')); }
                '&' => out.push_str("  "),
                '~' => out.push(' '),
                c => out.push(c),
            }
        }
        out
    }

    /// One argument: `{…}`, a command, or a single character.
    fn group(&mut self) -> String {
        while self.peek() == Some(' ') { self.i += 1; }
        match self.peek() {
            Some('{') => { self.i += 1; self.until(Some('}')) }
            Some('\\') => { self.i += 1; self.command() }
            Some(c) => { self.i += 1; c.to_string() }
            None => String::new(),
        }
    }

    fn name(&mut self) -> String {
        let start = self.i;
        while self.peek().is_some_and(|c| c.is_ascii_alphabetic()) { self.i += 1; }
        if self.i == start {
            if let Some(c) = self.peek() { self.i += 1; return c.to_string(); }
        }
        self.c[start..self.i].iter().collect()
    }

    fn command(&mut self) -> String {
        let name = self.name();
        match name.as_str() {
            "frac" | "dfrac" | "tfrac" => {
                let (a, b) = (self.group(), self.group());
                let wrap = |s: &str| if s.chars().count() > 1 && s.contains([' ', '+', '-', '·', '×']) { format!("({s})") } else { s.to_string() };
                format!("{}⁄{}", wrap(&a), wrap(&b))
            }
            "sqrt" => {
                let mut root = String::new();
                if self.peek() == Some('[') {
                    self.i += 1;
                    while let Some(c) = self.peek() { self.i += 1; if c == ']' { break } root.push(c); }
                }
                let body = self.group();
                let prefix = match root.as_str() { "" => "√".to_string(), "3" => "∛".into(), "4" => "∜".into(), r => format!("{}√", script(r, sup, '^')) };
                if body.chars().count() > 1 { format!("{prefix}({body})") } else { format!("{prefix}{body}") }
            }
            "text" | "mathrm" | "mathbf" | "mathit" | "mathsf" | "mathtt" | "operatorname" | "textbf" | "textit" | "boldsymbol" => self.group(),
            "mathbb" => {
                let g = self.group();
                g.chars().map(|c| match c { 'R' => 'ℝ', 'N' => 'ℕ', 'Z' => 'ℤ', 'Q' => 'ℚ', 'C' => 'ℂ', 'P' => 'ℙ', o => o }).collect()
            }
            "vec" => format!("{}⃗", self.group()),
            "hat" => format!("{}̂", self.group()),
            "bar" | "overline" => format!("{}̄", self.group()),
            "dot" => format!("{}̇", self.group()),
            "begin" | "end" => { self.group(); String::new() }
            "\\" => "\n".into(),
            n if WORDS.contains(&n) => format!("{n} "),
            n => SYMBOLS.iter().find(|(k, _)| *k == n).map_or_else(|| n.to_string(), |(_, v)| v.to_string()),
        }
    }
}

/// x^{2} → x², x_{ij} → xᵢⱼ; anything without a Unicode form keeps ^(…) / _(…).
fn script(s: &str, map: fn(char) -> Option<char>, mark: char) -> String {
    let s = s.trim();
    match s.chars().map(map).collect::<Option<String>>() {
        Some(t) if !t.is_empty() => t,
        _ if s.chars().count() == 1 => format!("{mark}{s}"),
        _ => format!("{mark}({s})"),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn common_notation_becomes_unicode() {
        assert_eq!(to_unicode(r"\alpha^2 + \beta_i"), "α² + βᵢ");
        assert_eq!(to_unicode(r"\frac{1}{2}"), "1⁄2");
        assert_eq!(to_unicode(r"\frac{a+b}{c}"), "(a+b)⁄c");
        assert_eq!(to_unicode(r"\sqrt{x^2+y^2}"), "√(x²+y²)");
        assert_eq!(to_unicode(r"\sum_{i=1}^{n} i"), "∑ᵢ₌₁ⁿ i");
        assert_eq!(to_unicode(r"x \in \mathbb{R}, x \leq \infty"), "x ∈ ℝ, x ≤ ∞");
        assert_eq!(to_unicode(r"\sin\theta \cdot \text{rate}"), "sin θ · rate");
        assert_eq!(to_unicode(r"e^{i\pi} = -1"), "e^(iπ) = -1");
    }

    #[test]
    fn inline_maths_is_converted_but_money_is_not() {
        assert_eq!(inline(r"Area is $\pi r^2$ here"), "Area is *π r²* here");
        assert_eq!(inline("It costs $5 and $10 today"), "It costs $5 and $10 today");
        assert_eq!(inline(r"keep `$x^2$` as code"), r"keep `$x^2$` as code");
        assert_eq!(inline(r"also \(a_1\) works"), "also *a₁* works");
    }

    #[test]
    fn display_maths_becomes_its_own_block() {
        let segs = split("Energy:\n\n$$E = mc^2$$\n\nDone.");
        assert_eq!(segs, vec![
            Seg::Markdown("Energy:\n\n".into()),
            Seg::Display("E = mc²".into()),
            Seg::Markdown("\nDone.".into()),
        ]);
        let multi = split("\\[\n\\int_0^1 x\\,dx = \\frac{1}{2}\n\\]\n");
        assert_eq!(multi, vec![Seg::Display("∫₀¹ x dx = 1⁄2".into())]);
    }

    #[test]
    fn code_fences_are_left_alone() {
        let segs = split("```\n$$not maths$$\n```\n");
        assert_eq!(segs, vec![Seg::Markdown("```\n$$not maths$$\n```\n".into())]);
    }
}
