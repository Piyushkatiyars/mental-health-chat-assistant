const chatWindow = document.getElementById("chat-window");
const form = document.getElementById("chat-form");
const input = document.getElementById("message-input");
const newChatBtn = document.getElementById("new-chat-btn");
const historyList = document.getElementById("history-list");

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

function clearChatWindow() {
  chatWindow.innerHTML = "";
}

async function loadHistory() {
  try {
    const res = await fetch("/api/history");
    const data = await res.json();
    data.messages.forEach((m) => addMessage(m.role, m.content, { flagged: m.flagged }));
  } catch (err) {
    // fresh session, nothing to load
  }
}

// ---- Sidebar: list of past conversations ----

async function loadConversations(activeSessionId = null) {
  try {
    const res = await fetch("/api/conversations");
    const data = await res.json();
    renderConversationList(data.conversations, activeSessionId);
  } catch (err) {
    // ignore, sidebar just stays empty
  }
}

function renderConversationList(conversations, activeSessionId) {
  historyList.innerHTML = "";

  conversations.forEach((conv) => {
    const row = document.createElement("div");
    row.className = "history-row";

    const item = document.createElement("button");
    item.type = "button";
    item.className = "history-item";
    if (conv.session_id === activeSessionId) {
      item.classList.add("active");
    }
    item.textContent = conv.title || "New Chat";
    item.addEventListener("click", () => openConversation(conv.session_id));

    const deleteBtn = document.createElement("button");
    deleteBtn.type = "button";
    deleteBtn.className = "history-delete";
    deleteBtn.setAttribute("aria-label", "Delete conversation");
    deleteBtn.textContent = "\u00D7";
    deleteBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      deleteConversation(conv.session_id);
    });

    row.appendChild(item);
    row.appendChild(deleteBtn);
    historyList.appendChild(row);
  });
}

async function deleteConversation(sessionId) {
  const confirmed = window.confirm("Delete this conversation? This can't be undone.");
  if (!confirmed) return;

  try {
    const res = await fetch(`/api/conversations/${sessionId}`, { method: "DELETE" });
    const data = await res.json();

    if (data.new_session_id) {
      // The active conversation was deleted; the backend already started a fresh one.
      clearChatWindow();
      loadConversations(data.new_session_id);
    } else {
      loadConversations();
    }
  } catch (err) {
    // ignore
  }
}

async function openConversation(sessionId) {
  try {
    // Tell the backend to switch the current session to this conversation.
    await fetch(`/api/conversations/${sessionId}/open`, { method: "POST" });

    // Fetch that conversation's messages and render them.
    const res = await fetch(`/api/conversations/${sessionId}`);
    const data = await res.json();

    clearChatWindow();
    data.messages.forEach((m) => addMessage(m.role, m.content, { flagged: m.flagged }));

    loadConversations(sessionId);
  } catch (err) {
    // ignore
  }
}

// ---- New chat button ----

newChatBtn.addEventListener("click", async () => {
  try {
    const res = await fetch("/api/new-chat", { method: "POST" });
    const data = await res.json();

    clearChatWindow();
    loadConversations(data.session_id);
  } catch (err) {
    // ignore
  }
});

// ---- Sending a message ----

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
    loadConversations();
  } catch (err) {
    hideTyping();
    addMessage("assistant", "Something went wrong. Please try again.");
  }
});

// ---- Initial load ----

loadHistory();
loadConversations();
