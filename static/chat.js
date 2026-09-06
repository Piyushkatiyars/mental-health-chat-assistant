const chatWindow = document.getElementById("chat-window");
const form = document.getElementById("chat-form");
const input = document.getElementById("message-input");

function timeNow() {
  return new Date().toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
}

function addMessage(role, content, options = {}) {
  const { flagged = false, time = timeNow() } = options;

  const row = document.createElement("div");
  row.className = `msg-row ${role}`;

  const bubble = document.createElement("div");
  bubble.className = `msg ${role}${flagged ? " flagged" : ""}`;

  if (flagged) {
    const label = document.createElement("div");
    label.className = "flagged-label";
    label.textContent = "here's some support";
    bubble.appendChild(label);
  }

  const text = document.createElement("div");
  text.textContent = content;
  bubble.appendChild(text);

  const stamp = document.createElement("div");
  stamp.className = "msg-time";
  stamp.textContent = time;

  row.appendChild(bubble);
  row.appendChild(stamp);
  chatWindow.appendChild(row);
  chatWindow.scrollTop = chatWindow.scrollHeight;
}

function showTyping() {
  const row = document.createElement("div");
  row.className = "msg-row assistant";
  row.id = "typing-indicator";
  const bubble = document.createElement("div");
  bubble.className = "msg assistant typing";
  bubble.innerHTML = "<span></span><span></span><span></span>";
  row.appendChild(bubble);
  chatWindow.appendChild(row);
  chatWindow.scrollTop = chatWindow.scrollHeight;
}

function hideTyping() {
  const el = document.getElementById("typing-indicator");
  if (el) el.remove();
}

async function loadHistory() {
  try {
    const res = await fetch("/api/history");
    const data = await res.json();
    data.messages.forEach((m) => addMessage(m.role, m.content));
  } catch (err) {
    // fresh session, nothing to load
  }
}

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  const message = input.value.trim();
  if (!message) return;

  addMessage("user", message);
  input.value = "";
  showTyping();

  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message }),
    });
    const data = await res.json();
    hideTyping();
    addMessage("assistant", data.reply, { flagged: data.flagged });
  } catch (err) {
    hideTyping();
    addMessage("assistant", "Something went wrong. Please try again.");
  }
});

loadHistory();
