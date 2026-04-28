const messagesEl = document.querySelector<HTMLDivElement>("#messages")!;
const formEl = document.querySelector<HTMLFormElement>("#chat-form")!;
const inputEl = document.querySelector<HTMLInputElement>("#chat-input")!;

function addMessage(text: string, sender: "user" | "jarvis") {
  const p = document.createElement("p");
  p.textContent = `${sender === "user" ? "You" : "Jarvis"}: ${text}`;
  messagesEl.appendChild(p);
}

formEl.addEventListener("submit", async (e) => {
  e.preventDefault();

  const message = inputEl.value.trim();
  if (!message) return;

  addMessage(message, "user");
  inputEl.value = "";

  const response = await fetch("http://localhost:8000/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message }),
  });

  const data = await response.json();
  addMessage(data.reply, "jarvis");
});
