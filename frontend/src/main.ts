import { marked } from 'marked';

marked.use({ breaks: true, gfm: true });

const messagesEl  = document.querySelector<HTMLDivElement>("#messages")!;
const formEl      = document.querySelector<HTMLFormElement>("#chat-form")!;
const inputEl     = document.querySelector<HTMLInputElement>("#chat-input")!;
const statusEl    = document.querySelector<HTMLSpanElement>("#status-text")!;
const bannerEl    = document.querySelector<HTMLDivElement>("#connection-banner")!;
const bannerTextEl = document.querySelector<HTMLSpanElement>("#connection-banner-text")!;
const micBtn      = document.querySelector<HTMLButtonElement>("#mic-btn")!;
const importBtn   = document.querySelector<HTMLButtonElement>("#import-btn")!;
const micDot      = document.querySelector<HTMLSpanElement>("#mic-dot")!;
const clockTime   = document.querySelector<HTMLElement>("#clock-time")!;
const clockDate   = document.querySelector<HTMLElement>("#clock-date")!;
const cpuFill     = document.querySelector<HTMLElement>("#cpu-fill")!;
const cpuVal      = document.querySelector<HTMLElement>("#cpu-val")!;
const ramFill     = document.querySelector<HTMLElement>("#ram-fill")!;
const ramVal      = document.querySelector<HTMLElement>("#ram-val")!;
const ramDetail   = document.querySelector<HTMLElement>("#ram-detail")!;
const sidebarEl      = document.querySelector<HTMLElement>("#sidebar-panel")!;
const sidebarToggle  = document.querySelector<HTMLButtonElement>("#sidebar-toggle")!;
const sidebarBackdrop = document.querySelector<HTMLButtonElement>("#sidebar-backdrop")!;
const tabMore        = document.querySelector<HTMLButtonElement>("#tab-more")!;

// ── Mobile sidebar drawer ────────────────────────────────────
// Both the topbar hamburger and the tab bar's "More" item open the same
// drawer, so both need their aria-expanded state kept in sync.
const drawerTriggers = [sidebarToggle, tabMore];

function closeSidebar() {
  sidebarEl.classList.remove("open");
  sidebarBackdrop.classList.remove("open");
  drawerTriggers.forEach((el) => el.setAttribute("aria-expanded", "false"));
}
function toggleSidebar() {
  const open = sidebarEl.classList.toggle("open");
  sidebarBackdrop.classList.toggle("open", open);
  drawerTriggers.forEach((el) => el.setAttribute("aria-expanded", String(open)));
}
sidebarToggle.addEventListener("click", toggleSidebar);
tabMore.addEventListener("click", toggleSidebar);
sidebarBackdrop.addEventListener("click", closeSidebar);

// Nav links close the mobile drawer after jumping to a dashboard card
document.querySelectorAll<HTMLAnchorElement>(".nav-item").forEach((link) => {
  link.addEventListener("click", () => {
    document.querySelectorAll<HTMLAnchorElement>(".nav-item").forEach((el) => el.classList.remove("active"));
    link.classList.add("active");
    if (sidebarEl.classList.contains("open")) closeSidebar();
  });
});

// Bottom tab bar — direct links set the active tab; they target the same
// anchors as the drawer's nav list, so they track their own active state.
document.querySelectorAll<HTMLAnchorElement>(".tab-item[data-tab]").forEach((tab) => {
  tab.addEventListener("click", () => {
    document.querySelectorAll<HTMLAnchorElement>(".tab-item[data-tab]").forEach((el) => el.classList.remove("active"));
    tab.classList.add("active");
  });
});

// ── Clock ──────────────────────────────────────────────────
const DAYS   = ["SUN","MON","TUE","WED","THU","FRI","SAT"];
const MONTHS = ["JAN","FEB","MAR","APR","MAY","JUN","JUL","AUG","SEP","OCT","NOV","DEC"];

function updateClock() {
  const now = new Date();
  const hh = String(now.getHours()).padStart(2, "0");
  const mm = String(now.getMinutes()).padStart(2, "0");
  const ss = String(now.getSeconds()).padStart(2, "0");
  clockTime.textContent = `${hh}:${mm}:${ss}`;
  clockDate.textContent = `${DAYS[now.getDay()]} ${String(now.getDate()).padStart(2,"0")} ${MONTHS[now.getMonth()]} ${now.getFullYear()}`;
}
updateClock();
setInterval(updateClock, 1000);

// ── System stats ───────────────────────────────────────────
async function fetchStats() {
  try {
    const res  = await fetch("http://localhost:8000/system");
    const data = await res.json();

    const cpu = data.cpu as number;
    cpuFill.style.width = `${cpu}%`;
    cpuFill.classList.toggle("high", cpu > 80);
    cpuVal.classList.toggle("high", cpu > 80);
    cpuVal.textContent  = `${cpu}%`;

    const ram = data.ram as number;
    ramFill.style.width = `${ram}%`;
    ramFill.classList.toggle("high", ram > 85);
    ramVal.classList.toggle("high", ram > 85);
    ramVal.textContent  = `${ram}%`;
    ramDetail.textContent = `${data.ram_used_gb}GB / ${data.ram_total_gb}GB`;
  } catch {
    // backend offline — keep displaying last value silently
  }
}
fetchStats();
setInterval(fetchStats, 3000);

// ── Live dashboard cards + activity feed ─────────────────────
const ACTIVITY_KEY = "jarvis_activity_log";
const MAX_ACTIVITY = 30;

type ActivityEntry = { agent: string; summary: string; timestamp: number };

function loadActivity(): ActivityEntry[] {
  try {
    const raw = localStorage.getItem(ACTIVITY_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

function saveActivity(entries: ActivityEntry[]) {
  try {
    localStorage.setItem(ACTIVITY_KEY, JSON.stringify(entries.slice(0, MAX_ACTIVITY)));
  } catch {
    // storage unavailable (private browsing, quota, etc.) — skip silently
  }
}

function escapeHtml(text: string): string {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

function summarize(text: string): string {
  const plain = text.replace(/[#*`_>]/g, "").replace(/\s+/g, " ").trim();
  return plain.length > 140 ? plain.slice(0, 140) + "…" : plain;
}

function timeAgo(timestamp: number): string {
  const mins = Math.floor((Date.now() - timestamp) / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
}

function applyEntryToCard(entry: ActivityEntry) {
  const card = document.querySelector<HTMLElement>(`.card[data-agent="${entry.agent}"]`);
  if (!card) return;
  const empty = card.querySelector<HTMLElement>(".card-empty");
  const badge = card.querySelector<HTMLElement>(".card-badge");
  if (empty) {
    empty.textContent = entry.summary;
    empty.classList.add("has-data");
  }
  if (badge) badge.textContent = timeAgo(entry.timestamp);
}

function renderActivity() {
  const list = document.querySelector<HTMLUListElement>("#activity-list")!;
  const entries = loadActivity();
  if (entries.length === 0) {
    list.innerHTML = `<li class="activity-empty">No activity yet.</li>`;
    return;
  }
  list.innerHTML = entries
    .slice(0, 8)
    .map((e) => `
      <li class="activity-row">
        <span class="activity-agent">${escapeHtml(e.agent)}</span>
        <span class="activity-summary">${escapeHtml(e.summary)}</span>
        <span class="activity-time">${timeAgo(e.timestamp)}</span>
      </li>`)
    .join("");
}

function recordActivity(agent: string, summary: string) {
  if (!summary) return;
  const entry: ActivityEntry = { agent, summary: summarize(summary), timestamp: Date.now() };
  const entries = loadActivity();
  entries.unshift(entry);
  saveActivity(entries);
  applyEntryToCard(entry);
  renderActivity();
}

function hydrateDashboard() {
  const entries = loadActivity();
  const seen = new Set<string>();
  for (const entry of entries) {
    if (seen.has(entry.agent)) continue;
    seen.add(entry.agent);
    applyEntryToCard(entry);
  }
  renderActivity();
}
hydrateDashboard();
setInterval(renderActivity, 60000); // keep "Xm ago" labels fresh

// ── Keyboard shortcuts ─────────────────────────────────────
function clearConversation() {
  messagesEl.innerHTML = "";
  chatHistory.length = 0;
}

document.addEventListener("keydown", (e) => {
  if (e.ctrlKey && e.key === "l") {
    e.preventDefault();
    clearConversation();
  }
  if (e.ctrlKey && e.key === "m") {
    e.preventDefault();
    toggleMic();
  }
  if (e.key === "Escape" && sidebarEl.classList.contains("open")) {
    closeSidebar();
  }
  if (e.key === "Escape" && isListening) {
    stopListening();
  }
});

// ── Native menu bar (Jarvis > Toggle Mic / Clear Conversation) ──
(async () => {
  const { listen } = await import("@tauri-apps/api/event");
  await listen("menu-toggle-mic", () => toggleMic());
  await listen("menu-clear-conversation", () => clearConversation());
})();

// ── Chat helpers ───────────────────────────────────────────
function setStatus(text: string) { statusEl.textContent = text; }

function setConnectionError(message: string | null) {
  if (message) {
    bannerTextEl.textContent = message;
    bannerEl.hidden = false;
  } else {
    bannerEl.hidden = true;
  }
}

function renderMarkdown(text: string): string {
  return marked.parse(text) as string;
}

function addMessage(text: string, sender: "user" | "jarvis"): HTMLElement {
  const div = document.createElement("div");
  div.className = `message ${sender}`;

  const label = document.createElement("span");
  label.className = "label";
  label.textContent = sender === "user" ? "YOU" : "JARVIS";

  const content = document.createElement("div");
  content.className = "text";

  if (sender === "jarvis" && text) {
    content.innerHTML = renderMarkdown(text);
  } else {
    content.textContent = text;
  }

  div.appendChild(label);
  div.appendChild(content);
  messagesEl.appendChild(div);
  messagesEl.scrollTop = messagesEl.scrollHeight;
  return div;
}

const chatHistory:{role:string,content:string}[] = [];

async function sendMessage(message: string) {
  chatHistory.push({ role: "user", content: message });
  addMessage(message, "user");
  inputEl.value = "";
  inputEl.disabled = true;

  const thinking = addMessage("", "jarvis");
  thinking.classList.add("typing");
  setStatus("PROCESSING...");
  setConnectionError(null);

  try {
    const res = await fetch("http://localhost:8000/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ messages: chatHistory }),
    });

    const reader = res.body!.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    let reply = "";
    let agentTag = "General";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const blocks = buffer.split("\n\n");
      buffer = blocks.pop() ?? "";
      for (const block of blocks) {
        for (const line of block.split("\n")) {
          if (!line.startsWith("data: ")) continue;
          try {
            const data = JSON.parse(line.slice(6));
            if (data.type === "status") {
              setStatus(data.content.toUpperCase());
            } else if (data.type === "tool") {
              thinking.querySelector<HTMLSpanElement>(".text")!.textContent = data.content;
              if (data.agent) agentTag = data.agent;
            } else if (data.type === "text") {
              reply = data.content;
              if (data.agent) agentTag = data.agent;
              thinking.classList.remove("typing");
              thinking.querySelector<HTMLDivElement>(".text")!.innerHTML = renderMarkdown(reply);
            } else if (data.type === "done") {
              if (data.agent) agentTag = data.agent;
              chatHistory.push({ role: "assistant", content: reply });
              setStatus("SYSTEM ONLINE");
              recordActivity(agentTag, reply);
            }
          } catch { /* skip malformed chunk */ }
        }
      }
    }
  } catch {
    thinking.classList.remove("typing");
    thinking.querySelector<HTMLSpanElement>(".text")!.textContent =
      "Connection failed. Is the backend running?";
    setStatus("BACKEND OFFLINE");
    setConnectionError("Can't reach the backend — is it running?");
    chatHistory.pop();
  } finally {
    inputEl.disabled = false;
    inputEl.focus();
    messagesEl.scrollTop = messagesEl.scrollHeight;
  }
}

formEl.addEventListener("submit", async (e) => {
  e.preventDefault();
  const message = inputEl.value.trim();
  if (message) await sendMessage(message);
});

// ── Import a file for Jarvis to check ───────────────────────
importBtn.addEventListener("click", async () => {
  try {
    const { open } = await import("@tauri-apps/plugin-dialog");
    const selected = await open({ multiple: false, directory: false });
    if (!selected || typeof selected !== "string") return;
    document.querySelector("#card-conversation")?.scrollIntoView({ behavior: "smooth", block: "start" });
    await sendMessage(`Please check this file: ${selected}`);
  } catch {
    setStatus("IMPORT UNAVAILABLE");
  }
});

// ── Dashboard quick actions ─────────────────────────────────
document.querySelectorAll<HTMLButtonElement>(".card-action[data-prompt]").forEach((btn) => {
  btn.addEventListener("click", async () => {
    const prompt = btn.dataset.prompt;
    if (!prompt) return;
    document.querySelector("#card-conversation")?.scrollIntoView({ behavior: "smooth", block: "start" });
    await sendMessage(prompt);
  });
});

// ── Voice input ────────────────────────────────────────────
const SpeechRecognitionCtor =
  (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;

let recognition: any = null;
let isListening = false;

if (!SpeechRecognitionCtor) {
  micBtn.classList.add("unavailable");
  micBtn.title = "Speech recognition not available in this browser";
} else {
  recognition = new SpeechRecognitionCtor();
  recognition.continuous      = false;
  recognition.interimResults  = false;
  recognition.lang            = "en-US";

  recognition.onresult = (event: any) => {
    const transcript = event.results[0][0].transcript.trim();
    stopListening();
    if (transcript) sendMessage(transcript);
  };

  recognition.onerror = () => {
    stopListening();
    setStatus("MIC ERROR");
  };

  recognition.onend = () => {
    if (isListening) stopListening();
  };
}

function startListening() {
  if (!recognition || isListening) return;
  isListening = true;
  micBtn.classList.add("listening");
  micBtn.textContent = "● REC";
  micDot.classList.add("listening");
  setStatus("LISTENING...");
  recognition.start();
}

function stopListening() {
  if (!isListening) return;
  isListening = false;
  micBtn.classList.remove("listening");
  micBtn.textContent = "MIC";
  micDot.classList.remove("listening");
  setStatus("SYSTEM ONLINE");
  try { recognition.stop(); } catch { /* already stopped */ }
}

function toggleMic() {
  if (!recognition) return;
  isListening ? stopListening() : startListening();
}

micBtn.addEventListener("click", toggleMic);

// ── Window close guard ─────────────────────────────────────
(async () => {
  const { getCurrentWindow } = await import("@tauri-apps/api/window");
  const appWindow = getCurrentWindow();
  await appWindow.onCloseRequested(async (event) => {
    event.preventDefault();
    const confirmed = confirm("Close Jarvis?");
    if (confirmed) {
      await appWindow.destroy();
    }
  });
})();
