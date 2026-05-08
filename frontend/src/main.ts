const messagesEl  = document.querySelector<HTMLDivElement>("#messages")!;
const formEl      = document.querySelector<HTMLFormElement>("#chat-form")!;
const inputEl     = document.querySelector<HTMLInputElement>("#chat-input")!;
const statusEl    = document.querySelector<HTMLSpanElement>("#status-text")!;
const micBtn      = document.querySelector<HTMLButtonElement>("#mic-btn")!;
const micDot      = document.querySelector<HTMLSpanElement>("#mic-dot")!;
const clockTime   = document.querySelector<HTMLElement>("#clock-time")!;
const clockDate   = document.querySelector<HTMLElement>("#clock-date")!;
const cpuFill     = document.querySelector<HTMLElement>("#cpu-fill")!;
const cpuVal      = document.querySelector<HTMLElement>("#cpu-val")!;
const ramFill     = document.querySelector<HTMLElement>("#ram-fill")!;
const ramVal      = document.querySelector<HTMLElement>("#ram-val")!;
const ramDetail   = document.querySelector<HTMLElement>("#ram-detail")!;

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
    cpuVal.textContent  = `${cpu}%`;

    const ram = data.ram as number;
    ramFill.style.width = `${ram}%`;
    ramFill.classList.toggle("high", ram > 85);
    ramVal.textContent  = `${ram}%`;
    ramDetail.textContent = `${data.ram_used_gb}GB / ${data.ram_total_gb}GB`;
  } catch {
    // backend offline — keep displaying last value silently
  }
}
fetchStats();
setInterval(fetchStats, 3000);

// ── Keyboard shortcuts ─────────────────────────────────────
document.addEventListener("keydown", (e) => {
  if (e.ctrlKey && e.key === "l") {
    e.preventDefault();
    messagesEl.innerHTML = "";
    chatHistory.length=0;
  }
  if (e.ctrlKey && e.key === "m") {
    e.preventDefault();
    toggleMic();
  }
  if (e.key === "Escape" && isListening) {
    stopListening();
  }
});

// ── Chat helpers ───────────────────────────────────────────
function setStatus(text: string) { statusEl.textContent = text; }

function addMessage(text: string, sender: "user" | "jarvis"): HTMLElement {
  const div = document.createElement("div");
  div.className = `message ${sender}`;

  const label = document.createElement("span");
  label.className = "label";
  label.textContent = sender === "user" ? "YOU" : "JARVIS";

  const content = document.createElement("span");
  content.className = "text";
  content.textContent = text;

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
            } else if (data.type === "text") {
              reply = data.content;
              thinking.classList.remove("typing");
              thinking.querySelector<HTMLSpanElement>(".text")!.textContent = reply;
            } else if (data.type === "done") {
              chatHistory.push({ role: "assistant", content: reply });
              setStatus("SYSTEM ONLINE");
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
