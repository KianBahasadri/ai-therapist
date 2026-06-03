const state = {
  busy: false,
};

const els = {
  therapyRoom: document.querySelector("#therapy-room"),
  messages: document.querySelector("#messages"),
  form: document.querySelector("#chat-form"),
  input: document.querySelector("#message-input"),
  send: document.querySelector("#send-button"),
  themeToggle: document.querySelector("#theme-toggle"),
};

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `Request failed: ${response.status}`);
  }
  return response.json();
}

function setBusy(value) {
  state.busy = value;
  els.send.disabled = value;
  els.input.disabled = value;
}

function getTheme() {
  return document.documentElement.getAttribute("data-theme") === "dark" ? "dark" : "light";
}

function applyTheme(theme) {
  if (theme === "dark") {
    document.documentElement.setAttribute("data-theme", "dark");
    els.themeToggle.setAttribute("aria-label", "Switch to light mode");
  } else {
    document.documentElement.removeAttribute("data-theme");
    els.themeToggle.setAttribute("aria-label", "Switch to dark mode");
  }
  localStorage.setItem("theme", theme);
}

function toggleTheme() {
  applyTheme(getTheme() === "dark" ? "light" : "dark");
}

function initTheme() {
  const saved = localStorage.getItem("theme");
  if (saved === "dark" || saved === "light") {
    applyTheme(saved);
    return;
  }
  applyTheme(
    window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light",
  );
}

function showTherapyRoom() {
  els.therapyRoom.classList.remove("hidden");
  document.body.classList.add("in-chat");
  els.input.focus();
}

function renderMessages(messages) {
  els.messages.innerHTML = "";
  if (!messages.length) {
    const empty = document.createElement("div");
    empty.className = "empty";
    empty.textContent = "Take your time. I'm here when you're ready to talk.";
    els.messages.append(empty);
    return;
  }
  for (const message of messages) {
    const node = document.createElement("article");
    node.className = `message ${message.role}`;
    node.textContent = message.content;
    els.messages.append(node);
  }
  els.messages.scrollTop = els.messages.scrollHeight;
}

async function loadHistory() {
  const data = await api("/api/history");
  renderMessages(data.messages);
}

async function sendMessage(event) {
  event.preventDefault();
  if (state.busy) return;

  const content = els.input.value.trim();
  if (!content) return;

  els.input.value = "";
  const existing = [...els.messages.querySelectorAll(".message")].map((node) => ({
    role: node.classList.contains("user") ? "user" : "assistant",
    content: node.textContent,
  }));
  renderMessages([...existing, { role: "user", content }, { role: "assistant", content: "..." }]);

  try {
    setBusy(true);
    await api("/api/history/messages", {
      method: "POST",
      body: JSON.stringify({ content }),
    });
    await loadHistory();
  } catch (error) {
    alert(error.message);
  } finally {
    setBusy(false);
  }
}

function boot() {
  initTheme();
  els.themeToggle.addEventListener("click", toggleTheme);
  els.form.addEventListener("submit", sendMessage);
  els.input.addEventListener("keydown", (event) => {
    if (event.key !== "Enter" || event.shiftKey) return;
    if (event.ctrlKey || event.metaKey) {
      event.preventDefault();
      const { selectionStart, selectionEnd, value } = els.input;
      els.input.value = `${value.slice(0, selectionStart)}\n${value.slice(selectionEnd)}`;
      const cursor = selectionStart + 1;
      els.input.selectionStart = cursor;
      els.input.selectionEnd = cursor;
      return;
    }
    event.preventDefault();
    els.form.requestSubmit();
  });

  loadHistory()
    .then(showTherapyRoom)
    .catch((error) => {
      alert(error.message);
    });
}

boot();
